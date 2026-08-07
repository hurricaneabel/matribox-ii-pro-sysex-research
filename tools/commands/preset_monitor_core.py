"""Núcleo offline do monitor de presets da Matribox II Pro.

Este módulo coordena os componentes estáveis já validados:

- ``preset_state.py``: consulta e eventos do preset atual;
- ``global_metadata_collector.py``: reconstrução dos fragmentos globais;
- ``global_preset_metadata.py``: nomes e etiquetas dos 240 presets;
- ``chain_order.py``: ordem, classe, modelo, seletor e bypass dos efeitos;
- ``tools.parameters``: eventos e valores de parâmetros definidos no JSON.

Ele trabalha exclusivamente com bytes. Não abre portas MIDI, não usa mido,
não dorme entre mensagens e não envia nada para a pedaleira.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Iterable

from tools.commands.chain_order import (
    ChainOrderProtocolError,
    ChainOrderState,
    parse_chain_order_response,
)
from tools.commands.effect_catalog import EFFECT_CLASSES
from tools.commands.effect_slot_state import (
    EffectSlotStateEvent,
    EffectSlotStateProtocolError,
    parse_effect_slot_state_response,
)
from tools.commands.global_metadata_collector import (
    CollectorUpdate,
    GlobalMetadataCollector,
)
from tools.commands.global_preset_metadata import (
    GlobalPresetMetadata,
    PresetMetadata,
    decode_global_preset_metadata,
)
from tools.parameters.decoder import (
    EffectParameterEvent,
    EffectParameterProtocolError,
    parse_effect_parameter_signal,
    resolve_effect_parameter_signal,
)
from tools.catalog.models import ParameterDefinition
from tools.parameters.state import EffectParameterState, ResolvedParameterValue
from tools.commands.preset_state import (
    PresetEvent,
    build_current_preset_query,
    calculate_protocol_checksum,
    parse_preset_event,
)
from tools.commands.preset_dump_state import (
    PresetDumpStateError,
    decode_chain_state_from_decompressed_preset_dump,
    decompress_preset_dump,
)
from tools.parameters.preset_dump import (
    PresetParameterDumpError,
    decode_saved_parameter_events,
)


SESSION_HANDSHAKE: Final = bytes.fromhex(
    "F0 21 25 7E 47 50 2D 32 "
    "11 12 00 00 00 F7"
)

GLOBAL_METADATA_QUERY: Final = bytes.fromhex(
    "F0 21 25 4D 50 00 00 1D 11 10 "
    "00 00 00 00 01 00 00 00 00 01 "
    "00 00 08 00 00 00 00 00 00 01 "
    "05 00 00 00 00 00 0A 00 01 01 "
    "01 00 00 00 00 F7"
)

HANDSHAKE_REPETITIONS: Final = 4
HANDSHAKE_INTERVAL_SECONDS: Final = 0.2
SESSION_STABILIZATION_SECONDS: Final = 0.5


@dataclass(frozen=True, slots=True)
class MonitorStartupPlan:
    """Mensagens e tempos que a camada MIDI deverá executar."""

    handshake_message: bytes
    handshake_repetitions: int
    handshake_interval_seconds: float
    stabilization_seconds: float
    global_metadata_query: bytes
    current_preset_query: bytes

    @property
    def ordered_messages(self) -> tuple[bytes, ...]:
        """Retorna a ordem lógica, sem representar os intervalos de tempo."""

        return (
            *(
                self.handshake_message
                for _ in range(self.handshake_repetitions)
            ),
            self.global_metadata_query,
            self.current_preset_query,
        )


@dataclass(frozen=True, slots=True)
class PresetParameterSnapshot:
    """Valor conhecido de um parâmetro catalogado do efeito."""

    key: str
    name: str
    value: int | float | bool | str | None
    unit: str | None = None
    display_text: str | None = None
    value_origin: str | None = None

    @property
    def ready(self) -> bool:
        return self.value is not None

    @property
    def display_value(self) -> str:
        if self.value is None:
            return "aguardando alteração"
        if self.display_text is not None:
            return self.display_text
        if isinstance(self.value, bool):
            value_text = "ligado" if self.value else "desligado"
        else:
            value_text = str(self.value)
        return f"{value_text} {self.unit}" if self.unit else value_text


@dataclass(frozen=True, slots=True)
class PresetEffectSnapshot:
    """Efeito resolvido para exibição no monitor."""

    visual_position: int
    internal_slot: int
    class_id: int
    class_name: str
    model_id: int
    model_name: str
    secondary_selector: int
    enabled: bool
    effect_key: str = ""
    parameters: tuple[PresetParameterSnapshot, ...] = ()


@dataclass(frozen=True, slots=True)
class PresetMonitorSnapshot:
    """Visão enriquecida do preset atual."""

    index: int
    label: str
    preset_id: int
    name: str
    filter_tag: str
    effects: tuple[PresetEffectSnapshot, ...] = ()
    effects_ready: bool = False

    @classmethod
    def from_metadata(
        cls,
        metadata: PresetMetadata,
        chain_state: ChainOrderState | None = None,
        parameter_state: EffectParameterState | None = None,
    ) -> "PresetMonitorSnapshot":
        effects = (
            build_effect_snapshots(chain_state, parameter_state)
            if chain_state is not None
            else ()
        )

        return cls(
            index=metadata.index,
            label=metadata.label,
            preset_id=metadata.preset_id,
            name=metadata.name,
            filter_tag=metadata.filter_tag,
            effects=effects,
            effects_ready=chain_state is not None,
        )


@dataclass(frozen=True, slots=True)
class PresetMonitorUpdate:
    """Resultado produzido ao alimentar uma mensagem no núcleo."""

    handled: bool
    preset_event: PresetEvent | None
    collector_update: CollectorUpdate
    metadata_loaded: bool
    snapshot: PresetMonitorSnapshot | None
    snapshot_changed: bool
    chain_state: ChainOrderState | None = None
    chain_changed: bool = False
    bypass_event: EffectSlotStateEvent | None = None
    parameter_event: EffectParameterEvent | None = None


def build_global_metadata_query() -> bytes:
    """Retorna a consulta global capturada durante a inicialização."""

    query = GLOBAL_METADATA_QUERY

    if len(query) != 46:
        raise AssertionError(
            "A consulta global perdeu o tamanho validado de 46 bytes."
        )

    if query[8] != 0x11 or query[9] != 0x10:
        raise AssertionError(
            "Direção ou comando da consulta global foi alterado."
        )

    calculated = calculate_protocol_checksum(query)

    if query[7] != 0x1D or calculated != query[7]:
        raise AssertionError(
            "Checksum da consulta global não corresponde a 0x1D."
        )

    return query


def build_monitor_startup_plan() -> MonitorStartupPlan:
    """Cria o plano puro que será executado pela camada MIDI."""

    return MonitorStartupPlan(
        handshake_message=SESSION_HANDSHAKE,
        handshake_repetitions=HANDSHAKE_REPETITIONS,
        handshake_interval_seconds=HANDSHAKE_INTERVAL_SECONDS,
        stabilization_seconds=SESSION_STABILIZATION_SECONDS,
        global_metadata_query=build_global_metadata_query(),
        current_preset_query=build_current_preset_query(),
    )


def _find_effect_class(class_id: int):
    return next(
        (
            effect_class
            for effect_class in EFFECT_CLASSES
            if effect_class.class_id == class_id
        ),
        None,
    )


def _resolve_effect_definition(
    class_id: int,
    model_id: int,
    secondary_selector: int,
):
    effect_class = _find_effect_class(class_id)

    if effect_class is None:
        return None, None

    exact_matches = tuple(
        model
        for model in effect_class.models
        if (
            model.model_id == model_id
            and model.secondary_selector == secondary_selector
        )
    )

    if len(exact_matches) == 1:
        return effect_class, exact_matches[0]

    model_matches = tuple(
        model for model in effect_class.models if model.model_id == model_id
    )
    if len(model_matches) == 1:
        return effect_class, model_matches[0]

    return effect_class, None


def _resolve_effect_names(
    class_id: int,
    model_id: int,
    secondary_selector: int,
) -> tuple[str, str]:
    effect_class, effect = _resolve_effect_definition(
        class_id, model_id, secondary_selector
    )
    if effect_class is None:
        return (f"CLASSE 0x{class_id:02X}", f"MODELO 0x{model_id:02X}")
    return (
        effect_class.name,
        effect.name if effect is not None else f"MODELO 0x{model_id:02X}",
    )


def _format_domain_value(
    parameter: ParameterDefinition,
    resolved: ResolvedParameterValue,
    event: EffectParameterEvent | None,
) -> str | None:
    if resolved.value is None:
        return None
    if resolved.domain_ambiguous:
        controller = parameter.value_domain.get("controller_parameter", "controlador")
        return f"aguardando {str(controller).upper()}"
    state = resolved.domain_state
    if state is not None:
        presentation = state.get("presentation", {})
        if isinstance(presentation, dict):
            kind = presentation.get("kind")
            if kind == "enum":
                choices = presentation.get("choices", [])
                if isinstance(choices, list):
                    for choice in choices:
                        if isinstance(choice, dict) and choice.get("value") == resolved.value:
                            label = choice.get("label")
                            if isinstance(label, str):
                                return label
            elif kind == "numeric":
                value = resolved.value
                if isinstance(value, float) and value.is_integer():
                    return str(int(value))
                return str(value)
    if event is not None:
        return event.display_value
    value = resolved.value
    if isinstance(value, bool):
        return "ligado" if value else "desligado"
    value_text = str(int(value)) if isinstance(value, float) and value.is_integer() else str(value)
    return f"{value_text} {parameter.unit}" if parameter.unit else value_text


def build_effect_snapshots(
    chain_state: ChainOrderState,
    parameter_state: EffectParameterState | None = None,
) -> tuple[PresetEffectSnapshot, ...]:
    """Converte registros estruturais e parâmetros para a apresentação."""

    snapshots: list[PresetEffectSnapshot] = []

    for visual_position, record in enumerate(
        chain_state.visual_effect_records,
        start=1,
    ):
        if (
            record.class_id is None
            or record.model_id is None
            or record.secondary_selector is None
            or record.enabled is None
        ):
            continue

        _, effect = _resolve_effect_definition(
            record.class_id,
            record.model_id,
            record.secondary_selector,
        )
        class_name, model_name = _resolve_effect_names(
            record.class_id,
            record.model_id,
            record.secondary_selector,
        )

        parameter_snapshots: list[PresetParameterSnapshot] = []
        if effect is not None:
            for parameter in effect.parameters:
                event = (
                    parameter_state.event_for(
                        record.internal_slot_id,
                        effect.key,
                        parameter.key,
                    )
                    if parameter_state is not None
                    else None
                )
                resolved = (
                    parameter_state.resolve_parameter(
                        record.internal_slot_id,
                        effect.key,
                        parameter,
                    )
                    if parameter_state is not None
                    else ResolvedParameterValue(value=None, origin=None)
                )
                parameter_snapshots.append(
                    PresetParameterSnapshot(
                        key=parameter.key,
                        name=parameter.name,
                        value=resolved.value,
                        unit=parameter.unit,
                        display_text=_format_domain_value(parameter, resolved, event),
                        value_origin=resolved.origin,
                    )
                )

        snapshots.append(
            PresetEffectSnapshot(
                visual_position=visual_position,
                internal_slot=record.human_slot,
                class_id=record.class_id,
                class_name=class_name,
                model_id=record.model_id,
                model_name=model_name,
                secondary_selector=record.secondary_selector,
                enabled=record.enabled,
                effect_key=effect.key if effect is not None else "",
                parameters=tuple(parameter_snapshots),
            )
        )

    return tuple(snapshots)


def format_monitor_snapshot(
    snapshot: PresetMonitorSnapshot,
) -> str:
    """Formata preset, nome, etiqueta e cadeia para o terminal."""

    visible_name = snapshot.name or "(sem nome)"
    visible_filter = snapshot.filter_tag or "(vazia)"

    lines = [
        f"Preset atual: {snapshot.label}",
        f"Nome: {visible_name}",
        f"Etiqueta: {visible_filter}",
    ]

    if not snapshot.effects_ready:
        lines.append("Efeitos: aguardando resposta estrutural.")
        return "\n".join(lines)

    lines.append("Efeitos:")

    if not snapshot.effects:
        lines.append("  (cadeia vazia)")
        return "\n".join(lines)

    for effect in snapshot.effects:
        state_text = "ligado" if effect.enabled else "desligado"
        lines.append(
            f"  {effect.visual_position}. "
            f"{effect.class_name} / {effect.model_name} "
            f"— {state_text}"
        )
        for parameter in effect.parameters:
            lines.append(
                f"     {parameter.name}: {parameter.display_value}"
            )

    return "\n".join(lines)


class PresetMonitorCore:
    """Estado coordenado do monitor, sem qualquer dependência de MIDI."""

    def __init__(
        self,
        collector: GlobalMetadataCollector | None = None,
    ) -> None:
        self.collector = (
            collector
            if collector is not None
            else GlobalMetadataCollector()
        )

        self.metadata: GlobalPresetMetadata | None = None
        self.current_event: PresetEvent | None = None
        self.current_chain: ChainOrderState | None = None
        self.global_block: bytes | None = None
        self._last_snapshot: PresetMonitorSnapshot | None = None
        self._pending_bypass_by_internal_slot: dict[int, bool] = {}
        self.parameter_state = EffectParameterState()

    @property
    def metadata_ready(self) -> bool:
        return self.metadata is not None

    @property
    def current_preset_known(self) -> bool:
        return self.current_event is not None

    @property
    def chain_ready(self) -> bool:
        return self.current_chain is not None

    @property
    def ready(self) -> bool:
        """Nome/tag e endereço estão prontos; a cadeia pode chegar depois."""

        return self.metadata_ready and self.current_preset_known

    @property
    def snapshot(self) -> PresetMonitorSnapshot | None:
        """Cruza o evento atual com metadados e eventual cadeia estrutural."""

        if self.metadata is None or self.current_event is None:
            return None

        metadata = self.metadata.by_index(self.current_event.index)

        return PresetMonitorSnapshot.from_metadata(
            metadata,
            self.current_chain,
            self.parameter_state,
        )

    @property
    def fragment_count(self) -> int:
        assembly = self.collector.best_assembly()

        if assembly is None:
            return 0

        return assembly.fragment_count

    @property
    def metadata_progress(self) -> tuple[int, int] | None:
        """Retorna bytes cobertos e tamanho total da melhor montagem."""

        assembly = self.collector.best_assembly()

        if assembly is None:
            return None

        return (
            assembly.covered_bytes,
            assembly.total_size,
        )

    def reset(self) -> None:
        """Descarta completamente o estado da sessão."""

        self.collector.reset()
        self.metadata = None
        self.current_event = None
        self.current_chain = None
        self.global_block = None
        self._last_snapshot = None
        self._pending_bypass_by_internal_slot.clear()
        self.parameter_state.clear()

    def load_global_block(
        self,
        global_block: bytes,
    ) -> bool:
        """Carrega diretamente um bloco reconstruído.

        Retorna True apenas quando o conteúdo é novo para esta sessão.
        """

        raw_block = bytes(global_block)

        if raw_block == self.global_block:
            return False

        decoded = decode_global_preset_metadata(raw_block)

        self.global_block = raw_block
        self.metadata = decoded

        return True

    def _merge_pending_bypass(
        self,
        chain_state: ChainOrderState,
    ) -> ChainOrderState:
        """Aplica mudanças recebidas enquanto a cadeia ainda era carregada."""

        resolved_state = chain_state

        for internal_slot_id, enabled in (
            self._pending_bypass_by_internal_slot.items()
        ):
            resolved_state = resolved_state.with_internal_slot_enabled(
                internal_slot_id + 1,
                enabled,
            )

        self._pending_bypass_by_internal_slot.clear()
        return resolved_state

    def _effect_keys_by_internal_slot(
        self,
        chain_state: ChainOrderState,
    ) -> dict[int, str]:
        result: dict[int, str] = {}
        for internal_slot_id in chain_state.internal_slot_ids:
            record = chain_state.effect_records_by_internal_slot[internal_slot_id]
            if (
                record.class_id is None
                or record.model_id is None
                or record.secondary_selector is None
            ):
                continue
            _, effect = _resolve_effect_definition(
                record.class_id,
                record.model_id,
                record.secondary_selector,
            )
            if effect is not None:
                result[internal_slot_id] = effect.key
        return result

    def _resolve_parameter_signal_for_current_chain(
        self,
        raw_message: bytes,
    ) -> EffectParameterEvent | None:
        """Resolve o parâmetro pelo efeito realmente presente no slot.

        Capturas de M-BOOST e COMP1 provaram que a mensagem ``0x1C`` não traz
        um ``model_id`` confiável. Por isso, a cadeia estrutural é a fonte de
        identidade do efeito e o pacote fornece apenas slot, seletor e valor.
        """

        if self.current_chain is None:
            return None

        signal = parse_effect_parameter_signal(raw_message)
        if signal is None:
            return None
        if signal.internal_slot_id not in self.current_chain.internal_slot_ids:
            return None

        record = self.current_chain.effect_records_by_internal_slot[
            signal.internal_slot_id
        ]
        if (
            record.class_id is None
            or record.model_id is None
            or record.secondary_selector is None
        ):
            return None

        _, effect = _resolve_effect_definition(
            record.class_id,
            record.model_id,
            record.secondary_selector,
        )
        if effect is None:
            return None

        return resolve_effect_parameter_signal(signal, effect.key)

    def apply_chain_state(
        self,
        chain_state: ChainOrderState,
    ) -> tuple[PresetMonitorSnapshot | None, bool]:
        """Aplica uma cadeia obtida por resposta imediata ou dump de preset."""

        previous_snapshot = self._last_snapshot
        self.current_chain = self._merge_pending_bypass(chain_state)
        self.parameter_state.retain_effects(
            self._effect_keys_by_internal_slot(self.current_chain)
        )
        current_snapshot = self.snapshot
        snapshot_changed = (
            current_snapshot is not None
            and current_snapshot != previous_snapshot
        )

        if current_snapshot is not None:
            self._last_snapshot = current_snapshot

        return current_snapshot, snapshot_changed

    def hydrate_saved_parameters(
        self,
        decompressed_dump: bytes | bytearray,
    ) -> int:
        """Carrega valores persistidos para a cadeia atual sem enviar SysEx."""

        if self.current_chain is None:
            raise ValueError("A cadeia deve ser aplicada antes dos parâmetros.")
        events = decode_saved_parameter_events(
            decompressed_dump,
            self.current_chain,
            self.parameter_state.catalog,
        )
        applied = 0
        for event in events:
            if self.parameter_state.origin_for(
                event.internal_slot_id,
                event.effect_key,
                event.parameter_key,
            ) == "observed_usb":
                continue
            self.parameter_state.apply(
                event,
                origin="saved_preset_dump",
            )
            applied += 1
        return applied

    def apply_preset_dump(
        self,
        preset_dump: bytes | bytearray,
    ) -> ChainOrderState:
        """Aplica cadeia, bypass e parâmetros do mesmo dump ``0x10``."""

        raw_container = bytes(preset_dump)
        decompressed, backend = decompress_preset_dump(raw_container)
        chain_state = decode_chain_state_from_decompressed_preset_dump(
            decompressed,
            raw_container=raw_container,
            decompressor_backend=backend,
        )
        self.apply_chain_state(chain_state)
        try:
            self.hydrate_saved_parameters(decompressed)
        except PresetParameterDumpError as error:
            raise PresetDumpStateError(str(error)) from error
        current_snapshot = self.snapshot
        if current_snapshot is not None:
            self._last_snapshot = current_snapshot
        return chain_state

    def feed(
        self,
        message: bytes | bytearray,
    ) -> PresetMonitorUpdate:
        """Processa uma mensagem recebida e atualiza o estado coordenado."""

        raw_message = bytes(message)
        previous_snapshot = self._last_snapshot
        previous_chain = self.current_chain

        preset_event = parse_preset_event(raw_message)

        if preset_event is not None:
            preset_changed = (
                self.current_event is None
                or self.current_event.index != preset_event.index
            )

            self.current_event = preset_event

            if preset_changed:
                # Nunca exibe a cadeia do preset anterior junto do endereço novo.
                self.current_chain = None
                self._pending_bypass_by_internal_slot.clear()
                self.parameter_state.clear()

        try:
            parameter_event = self._resolve_parameter_signal_for_current_chain(
                raw_message
            )
        except EffectParameterProtocolError:
            parameter_event = None

        if parameter_event is not None:
            self.parameter_state.apply(parameter_event)

        try:
            bypass_event = parse_effect_slot_state_response(raw_message)
        except EffectSlotStateProtocolError:
            # Uma resposta reconhecida, mas inválida, não deve derrubar a sessão.
            bypass_event = None

        if bypass_event is not None:
            if self.current_chain is None:
                # O dump pode estar em andamento. O evento mais recente deve
                # prevalecer quando a cadeia completa chegar.
                self._pending_bypass_by_internal_slot[
                    bypass_event.internal_slot_id
                ] = bypass_event.enabled
            else:
                self.current_chain = (
                    self.current_chain.with_internal_slot_enabled(
                        bypass_event.human_slot,
                        bypass_event.enabled,
                    )
                )

        try:
            chain_state = parse_chain_order_response(raw_message)
        except ChainOrderProtocolError:
            # Mensagens auxiliares não devem derrubar o monitor ao vivo.
            chain_state = None

        if chain_state is not None:
            self.current_chain = self._merge_pending_bypass(chain_state)
            self.parameter_state.retain_effects(
                self._effect_keys_by_internal_slot(self.current_chain)
            )
            chain_state = self.current_chain

        collector_update = self.collector.feed(raw_message)
        metadata_loaded = False

        if collector_update.global_block is not None:
            metadata_loaded = self.load_global_block(
                collector_update.global_block
            )

        current_snapshot = self.snapshot
        snapshot_changed = (
            current_snapshot is not None
            and current_snapshot != previous_snapshot
        )

        if current_snapshot is not None:
            self._last_snapshot = current_snapshot

        chain_changed = self.current_chain != previous_chain

        handled = (
            preset_event is not None
            or parameter_event is not None
            or bypass_event is not None
            or chain_state is not None
            or collector_update.accepted
            or metadata_loaded
        )

        return PresetMonitorUpdate(
            handled=handled,
            preset_event=preset_event,
            collector_update=collector_update,
            metadata_loaded=metadata_loaded,
            snapshot=current_snapshot,
            snapshot_changed=snapshot_changed,
            chain_state=chain_state,
            chain_changed=chain_changed,
            bypass_event=bypass_event,
            parameter_event=parameter_event,
        )

    def feed_many(
        self,
        messages: Iterable[bytes | bytearray],
    ) -> tuple[PresetMonitorUpdate, ...]:
        """Processa uma sequência preservando todas as atualizações."""

        return tuple(
            self.feed(message)
            for message in messages
        )
