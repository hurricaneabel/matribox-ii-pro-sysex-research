"""Núcleo offline do monitor de presets da Matribox II Pro.

Este módulo coordena os componentes estáveis já validados:

- preset_state.py: consulta e eventos do preset atual;
- global_metadata_collector.py: reconstrução dos fragmentos;
- global_preset_metadata.py: nomes e etiquetas dos 240 presets.

Ele trabalha exclusivamente com bytes. Não abre portas MIDI, não usa mido,
não dorme entre mensagens e não envia nada para a pedaleira.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Iterable

from tools.commands.global_metadata_collector import (
    CollectorUpdate,
    GlobalMetadataCollector,
)
from tools.commands.global_preset_metadata import (
    GlobalPresetMetadata,
    PresetMetadata,
    decode_global_preset_metadata,
)
from tools.commands.preset_state import (
    PresetEvent,
    build_current_preset_query,
    calculate_protocol_checksum,
    parse_preset_event,
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
    """Mensagens e tempos que a futura camada MIDI deverá executar."""

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
class PresetMonitorSnapshot:
    """Visão enriquecida do preset atual."""

    index: int
    label: str
    preset_id: int
    name: str
    filter_tag: str

    @classmethod
    def from_metadata(
        cls,
        metadata: PresetMetadata,
    ) -> "PresetMonitorSnapshot":
        return cls(
            index=metadata.index,
            label=metadata.label,
            preset_id=metadata.preset_id,
            name=metadata.name,
            filter_tag=metadata.filter_tag,
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


def format_monitor_snapshot(
    snapshot: PresetMonitorSnapshot,
) -> str:
    """Formata o estado atual para exibição no terminal."""
    visible_name = snapshot.name or "(sem nome)"
    visible_filter = snapshot.filter_tag or "(vazia)"

    return "\n".join(
        (
            f"Preset atual: {snapshot.label}",
            f"Nome: {visible_name}",
            f"Etiqueta: {visible_filter}",
        )
    )


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
        self.global_block: bytes | None = None
        self._last_snapshot: PresetMonitorSnapshot | None = None

    @property
    def metadata_ready(self) -> bool:
        return self.metadata is not None

    @property
    def current_preset_known(self) -> bool:
        return self.current_event is not None

    @property
    def ready(self) -> bool:
        return (
            self.metadata_ready
            and self.current_preset_known
        )

    @property
    def snapshot(self) -> PresetMonitorSnapshot | None:
        """Cruza o evento atual com a tabela global, quando ambos existem."""
        if self.metadata is None or self.current_event is None:
            return None

        metadata = self.metadata.by_index(
            self.current_event.index
        )

        return PresetMonitorSnapshot.from_metadata(
            metadata
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
        self.global_block = None
        self._last_snapshot = None

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

        decoded = decode_global_preset_metadata(
            raw_block
        )

        self.global_block = raw_block
        self.metadata = decoded

        return True

    def feed(
        self,
        message: bytes | bytearray,
    ) -> PresetMonitorUpdate:
        """Processa uma mensagem recebida e atualiza o estado coordenado."""
        raw_message = bytes(message)
        previous_snapshot = self._last_snapshot

        preset_event = parse_preset_event(
            raw_message
        )

        if preset_event is not None:
            self.current_event = preset_event

        collector_update = self.collector.feed(
            raw_message
        )

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

        handled = (
            preset_event is not None
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
