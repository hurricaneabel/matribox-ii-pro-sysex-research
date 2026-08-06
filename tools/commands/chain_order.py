"""Leitura estável do estado estrutural da cadeia da Matribox II Pro.

As respostas completas usam um contêiner LZO1X codificado em nibbles. Depois
da descompressão, o payload possui 89 bytes e contém, em posições fixas:

- ordem visual dos slots internos;
- classe por slot interno;
- modelo, campos auxiliares e seletor secundário por slot;
- estado ligado/desligado por slot interno;
- marcador do slot associado à resposta.

A API histórica de ordem e bypass é preservada. Classe, modelo e seletor foram
acrescentados por meio dos registros estruturais dos doze slots.

Este módulo trabalha somente com bytes. Ele não abre portas MIDI.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Final

from tools.commands.structural_effect_state import (
    BYPASS_START_INDEX as PAYLOAD_BYPASS_START_INDEX,
    MAX_INTERNAL_SLOTS,
    StructuralEffectRecord,
    StructuralEffectState,
    StructuralEffectStateError,
    parse_structural_effect_state,
)


MATRIBOX_HEADER: Final = bytes.fromhex(
    "F0 21 25 4D 50"
)

DIRECTION_INDEX: Final = 8
LENGTH_UNITS_INDEX: Final = 9
DIRECTION_INCOMING: Final = 0x00

MESSAGE_OVERHEAD: Final = 14
MIN_CHAIN_RESPONSE_LENGTH: Final = 60
EMPTY_SLOT_ID: Final = 0xFF

# Constantes históricas preservadas para compatibilidade com imports antigos.
# O parser estável não depende mais desses índices brutos, pois usa o payload
# LZO1X descomprimido.
ORDER_START_INDEX: Final = 39
ENCODED_SLOT_SIZE: Final = 2
BYPASS_START_INDEX: Final = 136
BYPASS_ENCODED_SLOT_SIZE: Final = 2
BYPASS_ENABLED_VALUE: Final = 0x10
BYPASS_DISABLED_VALUE: Final = 0x00
VALIDATED_BYPASS_INTERNAL_SLOTS: Final = MAX_INTERNAL_SLOTS

_EMPTY_RECORDS: Final = ()


class ChainOrderProtocolError(ValueError):
    """Erro em uma resposta estrutural de cadeia reconhecida."""


@dataclass(frozen=True, slots=True)
class ChainOrderState:
    """Ordem visual e estado estrutural resolvidos para os slots internos."""

    internal_slot_ids: tuple[int, ...]
    observed_checksum: int
    declared_length_units: int
    raw_message: bytes
    enabled_by_internal_slot: tuple[
        bool | None,
        ...,
    ] = (
        None,
    ) * MAX_INTERNAL_SLOTS
    effect_records_by_internal_slot: tuple[
        StructuralEffectRecord,
        ...,
    ] = _EMPTY_RECORDS
    response_slot_marker: int | None = None
    decompressed_payload: bytes | None = None

    @property
    def human_slots(self) -> tuple[int, ...]:
        """Slots internos apresentados em base um."""

        return tuple(
            internal_id + 1
            for internal_id in self.internal_slot_ids
        )

    @property
    def effect_count(self) -> int:
        """Quantidade de efeitos ativos na cadeia."""

        return len(self.internal_slot_ids)

    @property
    def declared_message_length(self) -> int:
        """Comprimento total calculado pelo campo do índice 9."""

        return (
            MESSAGE_OVERHEAD
            + self.declared_length_units * 2
        )

    @property
    def visual_enabled_states(
        self,
    ) -> tuple[
        bool | None,
        ...,
    ]:
        """Estados de bypass apresentados na ordem visual atual."""

        return tuple(
            self.enabled_by_internal_slot[internal_id]
            for internal_id in self.internal_slot_ids
        )

    @property
    def has_complete_bypass_state(self) -> bool:
        """Informa se todos os efeitos ativos possuem bypass resolvido."""

        return all(
            self.enabled_by_internal_slot[internal_id]
            is not None
            for internal_id in self.internal_slot_ids
        )

    @property
    def class_ids_by_internal_slot(
        self,
    ) -> tuple[int | None, ...]:
        """Classes dos doze slots internos."""

        return tuple(
            record.class_id
            for record in self.effect_records_by_internal_slot
        )

    @property
    def model_ids_by_internal_slot(
        self,
    ) -> tuple[int | None, ...]:
        """Modelos dos doze slots internos."""

        return tuple(
            record.model_id
            for record in self.effect_records_by_internal_slot
        )

    @property
    def secondary_selectors_by_internal_slot(
        self,
    ) -> tuple[int | None, ...]:
        """Seletores secundários dos doze slots internos."""

        return tuple(
            record.secondary_selector
            for record in self.effect_records_by_internal_slot
        )

    @property
    def visual_effect_records(
        self,
    ) -> tuple[StructuralEffectRecord, ...]:
        """Registros dos efeitos na ordem visual atual."""

        if not self.effect_records_by_internal_slot:
            return ()

        return tuple(
            self.effect_records_by_internal_slot[internal_id]
            for internal_id in self.internal_slot_ids
        )

    def slot_at_visual_position(
        self,
        visual_position: int,
    ) -> int:
        """Retorna o slot humano de uma posição visual."""

        self._validate_visual_position(visual_position)
        return self.human_slots[visual_position - 1]

    def enabled_for_internal_slot(
        self,
        internal_slot: int,
    ) -> bool | None:
        """Retorna o bypass de um slot humano interno.

        ``True`` significa efeito ligado, ``False`` significa bypass e
        ``None`` significa slot inativo.
        """

        internal_id = self._human_slot_to_internal_id(internal_slot)
        return self.enabled_by_internal_slot[internal_id]

    def enabled_at_visual_position(
        self,
        visual_position: int,
    ) -> bool | None:
        """Retorna o bypass do efeito em uma posição visual."""

        internal_id = self._internal_id_at_visual_position(
            visual_position
        )
        return self.enabled_by_internal_slot[internal_id]

    def with_internal_slot_enabled(
        self,
        internal_slot: int,
        enabled: bool,
    ) -> "ChainOrderState":
        """Retorna uma cópia com o bypass de um slot ativo atualizado.

        A resposta imediata de bypass informa o slot interno, não a posição
        visual. A atualização preserva a ordem atual e mantém sincronizados
        o vetor histórico de estados, o registro estrutural e o payload
        descomprimido quando ele está disponível.
        """

        internal_id = self._human_slot_to_internal_id(internal_slot)

        if internal_id not in self.internal_slot_ids:
            return self

        enabled_value = bool(enabled)
        enabled_states = list(self.enabled_by_internal_slot)

        if enabled_states[internal_id] is enabled_value:
            return self

        enabled_states[internal_id] = enabled_value
        records = self.effect_records_by_internal_slot

        if records:
            mutable_records = list(records)
            mutable_records[internal_id] = replace(
                mutable_records[internal_id],
                enabled=enabled_value,
            )
            records = tuple(mutable_records)

        payload = self.decompressed_payload

        if (
            payload is not None
            and len(payload) > PAYLOAD_BYPASS_START_INDEX + internal_id
        ):
            mutable_payload = bytearray(payload)
            mutable_payload[
                PAYLOAD_BYPASS_START_INDEX + internal_id
            ] = 0x01 if enabled_value else 0x00
            payload = bytes(mutable_payload)

        return replace(
            self,
            enabled_by_internal_slot=tuple(enabled_states),
            effect_records_by_internal_slot=records,
            response_slot_marker=internal_id,
            decompressed_payload=payload,
        )

    def record_for_internal_slot(
        self,
        internal_slot: int,
    ) -> StructuralEffectRecord:
        """Retorna classe, modelo e seletor de um slot humano."""

        internal_id = self._human_slot_to_internal_id(internal_slot)

        if not self.effect_records_by_internal_slot:
            raise LookupError(
                "Esta instância não possui registros estruturais."
            )

        return self.effect_records_by_internal_slot[internal_id]

    def record_at_visual_position(
        self,
        visual_position: int,
    ) -> StructuralEffectRecord:
        """Retorna o registro do efeito em uma posição visual."""

        internal_id = self._internal_id_at_visual_position(
            visual_position
        )

        if not self.effect_records_by_internal_slot:
            raise LookupError(
                "Esta instância não possui registros estruturais."
            )

        return self.effect_records_by_internal_slot[internal_id]

    def class_for_internal_slot(
        self,
        internal_slot: int,
    ) -> int | None:
        """Retorna a classe de um slot humano."""

        return self.record_for_internal_slot(internal_slot).class_id

    def model_for_internal_slot(
        self,
        internal_slot: int,
    ) -> int | None:
        """Retorna o modelo de um slot humano."""

        return self.record_for_internal_slot(internal_slot).model_id

    def secondary_selector_for_internal_slot(
        self,
        internal_slot: int,
    ) -> int | None:
        """Retorna o seletor secundário de um slot humano."""

        return self.record_for_internal_slot(
            internal_slot
        ).secondary_selector

    def _human_slot_to_internal_id(
        self,
        internal_slot: int,
    ) -> int:
        if not 1 <= internal_slot <= MAX_INTERNAL_SLOTS:
            raise IndexError("Slot interno fora do intervalo.")

        return internal_slot - 1

    def _validate_visual_position(
        self,
        visual_position: int,
    ) -> None:
        if not 1 <= visual_position <= self.effect_count:
            raise IndexError("Posição visual fora do intervalo.")

    def _internal_id_at_visual_position(
        self,
        visual_position: int,
    ) -> int:
        self._validate_visual_position(visual_position)
        return self.internal_slot_ids[visual_position - 1]


def decode_nibble_pair(
    high_nibble: int,
    low_nibble: int,
) -> int:
    """Combina dois nibbles em um byte.

    A função permanece pública por compatibilidade com consumidores antigos.
    """

    if not 0 <= high_nibble <= 0x0F:
        raise ChainOrderProtocolError(
            "Nibble alto inválido: "
            f"0x{high_nibble:02X}."
        )

    if not 0 <= low_nibble <= 0x0F:
        raise ChainOrderProtocolError(
            "Nibble baixo inválido: "
            f"0x{low_nibble:02X}."
        )

    return (high_nibble << 4) | low_nibble


def calculate_declared_message_length(
    message: bytes | bytearray,
) -> int:
    """Calcula o comprimento total declarado no índice 9."""

    if len(message) <= LENGTH_UNITS_INDEX:
        raise ChainOrderProtocolError(
            "Mensagem curta demais para declarar o comprimento."
        )

    return MESSAGE_OVERHEAD + message[LENGTH_UNITS_INDEX] * 2


def chain_order_state_from_structural_state(
    structural_state: StructuralEffectState,
    *,
    observed_checksum: int = 0,
    declared_length_units: int = 0,
    raw_message: bytes | None = None,
) -> ChainOrderState:
    """Converte o estado estrutural comum para a API histórica de cadeia."""

    enabled_by_internal_slot = tuple(
        record.enabled
        for record in structural_state.records
    )

    return ChainOrderState(
        internal_slot_ids=structural_state.internal_slot_ids,
        observed_checksum=observed_checksum,
        declared_length_units=declared_length_units,
        raw_message=(
            structural_state.raw_message
            if raw_message is None
            else bytes(raw_message)
        ),
        enabled_by_internal_slot=enabled_by_internal_slot,
        effect_records_by_internal_slot=structural_state.records,
        response_slot_marker=structural_state.response_slot_marker,
        decompressed_payload=structural_state.decompressed_payload,
    )


def parse_chain_order_response(
    message: bytes | bytearray,
) -> ChainOrderState | None:
    """Interpreta ordem, classe, modelo, seletor e bypass.

    Retorna ``None`` quando a mensagem não possui a estrutura externa
    confirmada. Depois de reconhecer o contêiner estrutural, inconsistências
    internas geram ``ChainOrderProtocolError``.
    """

    raw_message = bytes(message)

    try:
        structural_state = parse_structural_effect_state(raw_message)
    except StructuralEffectStateError as error:
        raise ChainOrderProtocolError(str(error)) from error

    if structural_state is None:
        return None

    return chain_order_state_from_structural_state(
        structural_state,
        observed_checksum=raw_message[7],
        declared_length_units=raw_message[LENGTH_UNITS_INDEX],
        raw_message=raw_message,
    )


def apply_visual_move(
    current_order: tuple[int, ...],
    source_position: int,
    destination_position: int,
) -> tuple[int, ...]:
    """Aplica localmente um movimento visual."""

    effect_count = len(current_order)

    if not 1 <= source_position <= effect_count:
        raise ValueError("Origem fora do intervalo.")

    if not 1 <= destination_position <= effect_count:
        raise ValueError("Destino fora do intervalo.")

    if source_position == destination_position:
        raise ValueError("Origem e destino não podem ser iguais.")

    reordered = list(current_order)
    moved_slot = reordered.pop(source_position - 1)
    reordered.insert(destination_position - 1, moved_slot)

    return tuple(reordered)
