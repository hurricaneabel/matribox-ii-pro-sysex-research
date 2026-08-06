"""Leitura estável do estado estrutural da cadeia da Matribox II Pro.

Descobertas confirmadas fisicamente:

- a resposta estrutural varia de tamanho conforme a cadeia;
- o byte 9 declara o comprimento em unidades de dois bytes;
- comprimento total = 14 + (byte 9 * 2);
- direção recebida no índice 8: 0x00;
- a ordem visual começa no índice absoluto 39;
- cada slot interno é codificado em dois nibbles;
- 0F 0F representa 0xFF e encerra a lista;
- identificadores internos usam base zero;
- nas respostas de 168 bytes, o bypass dos slots internos 1–5 ocupa
  os índices 136–145;
- cada estado de bypass usa dois nibbles;
- 01 00 representa ligado e 00 00 representa desligado;
- o campo de bypass é indexado pelo slot interno, não pela posição visual.

O layout de bypass foi validado fisicamente nos slots internos 1–5.
Para slots internos 6–12, o estado permanece ``None`` até validação física.

Este módulo não abre portas MIDI.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


MATRIBOX_HEADER: Final = bytes.fromhex(
    "F0 21 25 4D 50"
)

DIRECTION_INDEX: Final = 8
LENGTH_UNITS_INDEX: Final = 9
DIRECTION_INCOMING: Final = 0x00

MESSAGE_OVERHEAD: Final = 14
MIN_CHAIN_RESPONSE_LENGTH: Final = 60

ORDER_START_INDEX: Final = 39
MAX_INTERNAL_SLOTS: Final = 12
ENCODED_SLOT_SIZE: Final = 2
EMPTY_SLOT_ID: Final = 0xFF

BYPASS_START_INDEX: Final = 136
BYPASS_ENCODED_SLOT_SIZE: Final = 2
BYPASS_ENABLED_VALUE: Final = 0x10
BYPASS_DISABLED_VALUE: Final = 0x00
VALIDATED_BYPASS_INTERNAL_SLOTS: Final = 5


class ChainOrderProtocolError(ValueError):
    """Erro em uma resposta estrutural de cadeia reconhecida."""


@dataclass(frozen=True, slots=True)
class ChainOrderState:
    """Ordem visual e bypass resolvidos para slots internos."""

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

    @property
    def human_slots(self) -> tuple[int, ...]:
        """Slots internos apresentados em base um."""

        return tuple(
            internal_id + 1
            for internal_id in self.internal_slot_ids
        )

    @property
    def effect_count(self) -> int:
        """Quantidade de efeitos na cadeia."""

        return len(
            self.internal_slot_ids
        )

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
            self.enabled_by_internal_slot[
                internal_id
            ]
            for internal_id in self.internal_slot_ids
        )

    @property
    def has_complete_bypass_state(
        self,
    ) -> bool:
        """Informa se todos os efeitos ativos possuem bypass resolvido."""

        return all(
            self.enabled_by_internal_slot[
                internal_id
            ]
            is not None
            for internal_id in self.internal_slot_ids
        )

    def slot_at_visual_position(
        self,
        visual_position: int,
    ) -> int:
        """Retorna o slot humano de uma posição visual."""

        if not 1 <= visual_position <= self.effect_count:
            raise IndexError(
                "Posição visual fora do intervalo."
            )

        return self.human_slots[
            visual_position - 1
        ]

    def enabled_for_internal_slot(
        self,
        internal_slot: int,
    ) -> bool | None:
        """Retorna o bypass de um slot humano interno.

        ``True`` significa efeito ligado, ``False`` significa bypass e
        ``None`` significa slot inativo ou campo ainda não validado.
        """

        if not 1 <= internal_slot <= MAX_INTERNAL_SLOTS:
            raise IndexError(
                "Slot interno fora do intervalo."
            )

        return self.enabled_by_internal_slot[
            internal_slot - 1
        ]

    def enabled_at_visual_position(
        self,
        visual_position: int,
    ) -> bool | None:
        """Retorna o bypass do efeito em uma posição visual."""

        if not 1 <= visual_position <= self.effect_count:
            raise IndexError(
                "Posição visual fora do intervalo."
            )

        internal_id = self.internal_slot_ids[
            visual_position - 1
        ]

        return self.enabled_by_internal_slot[
            internal_id
        ]


def decode_nibble_pair(
    high_nibble: int,
    low_nibble: int,
) -> int:
    """Combina dois nibbles em um byte."""

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

    return (
        (high_nibble << 4)
        | low_nibble
    )


def calculate_declared_message_length(
    message: bytes | bytearray,
) -> int:
    """Calcula o comprimento total declarado no índice 9."""

    if len(message) <= LENGTH_UNITS_INDEX:
        raise ChainOrderProtocolError(
            "Mensagem curta demais para declarar o comprimento."
        )

    return (
        MESSAGE_OVERHEAD
        + message[LENGTH_UNITS_INDEX] * 2
    )


def _has_chain_state_structure(
    message: bytes,
) -> bool:
    """Valida os campos estruturais comuns às respostas de cadeia."""

    if len(message) < MIN_CHAIN_RESPONSE_LENGTH:
        return False

    if message[:5] != MATRIBOX_HEADER:
        return False

    if message[-1] != 0xF7:
        return False

    if message[DIRECTION_INDEX] != DIRECTION_INCOMING:
        return False

    return (
        calculate_declared_message_length(
            message
        )
        == len(message)
    )


def _parse_internal_slot_ids(
    raw_message: bytes,
) -> tuple[int, ...]:
    """Decodifica a ordem visual dos slots internos."""

    required_end = (
        ORDER_START_INDEX
        + MAX_INTERNAL_SLOTS * ENCODED_SLOT_SIZE
    )

    if len(raw_message) <= required_end:
        raise ChainOrderProtocolError(
            "Resposta curta demais para a lista de ordem."
        )

    internal_slot_ids: list[int] = []
    seen_slots: set[int] = set()
    terminator_found = False

    for visual_index in range(
        MAX_INTERNAL_SLOTS
    ):
        pair_index = (
            ORDER_START_INDEX
            + visual_index * ENCODED_SLOT_SIZE
        )

        internal_id = decode_nibble_pair(
            raw_message[pair_index],
            raw_message[pair_index + 1],
        )

        if internal_id == EMPTY_SLOT_ID:
            terminator_found = True
            break

        if not 0 <= internal_id < MAX_INTERNAL_SLOTS:
            raise ChainOrderProtocolError(
                "Slot interno fora do intervalo: "
                f"{internal_id}."
            )

        if internal_id in seen_slots:
            raise ChainOrderProtocolError(
                "Slot interno repetido: "
                f"{internal_id + 1}."
            )

        seen_slots.add(
            internal_id
        )
        internal_slot_ids.append(
            internal_id
        )

    if (
        len(internal_slot_ids) < MAX_INTERNAL_SLOTS
        and not terminator_found
    ):
        raise ChainOrderProtocolError(
            "Lista parcial sem terminador 0xFF."
        )

    return tuple(
        internal_slot_ids
    )


def _parse_enabled_by_internal_slot(
    raw_message: bytes,
    internal_slot_ids: tuple[int, ...],
) -> tuple[
    bool | None,
    ...,
]:
    """Decodifica o bypass validado dos slots internos 1–5."""

    enabled_states: list[
        bool | None
    ] = [
        None,
    ] * MAX_INTERNAL_SLOTS

    required_end = (
        BYPASS_START_INDEX
        + (
            VALIDATED_BYPASS_INTERNAL_SLOTS
            * BYPASS_ENCODED_SLOT_SIZE
        )
    )

    if len(raw_message) < required_end:
        return tuple(
            enabled_states
        )

    for internal_id in internal_slot_ids:
        if (
            internal_id
            >= VALIDATED_BYPASS_INTERNAL_SLOTS
        ):
            continue

        pair_index = (
            BYPASS_START_INDEX
            + (
                internal_id
                * BYPASS_ENCODED_SLOT_SIZE
            )
        )

        encoded_state = decode_nibble_pair(
            raw_message[pair_index],
            raw_message[pair_index + 1],
        )

        if encoded_state == BYPASS_ENABLED_VALUE:
            enabled_states[
                internal_id
            ] = True
            continue

        if encoded_state == BYPASS_DISABLED_VALUE:
            enabled_states[
                internal_id
            ] = False
            continue

        raise ChainOrderProtocolError(
            "Estado de bypass inválido para o slot interno "
            f"{internal_id + 1}: "
            f"0x{encoded_state:02X}."
        )

    return tuple(
        enabled_states
    )


def parse_chain_order_response(
    message: bytes | bytearray,
) -> ChainOrderState | None:
    """Interpreta ordem visual e bypass de uma resposta estrutural.

    Retorna ``None`` quando a mensagem não possui a estrutura geral
    confirmada. Depois de reconhecer essa estrutura, valores inválidos
    geram ``ChainOrderProtocolError``.
    """

    raw_message = bytes(
        message
    )

    if not _has_chain_state_structure(
        raw_message
    ):
        return None

    try:
        internal_slot_ids = (
            _parse_internal_slot_ids(
                raw_message
            )
        )
    except ChainOrderProtocolError as error:
        if (
            "Resposta curta demais"
            in str(error)
        ):
            return None

        raise

    enabled_by_internal_slot = (
        _parse_enabled_by_internal_slot(
            raw_message,
            internal_slot_ids,
        )
    )

    return ChainOrderState(
        internal_slot_ids=internal_slot_ids,
        observed_checksum=raw_message[7],
        declared_length_units=raw_message[
            LENGTH_UNITS_INDEX
        ],
        raw_message=raw_message,
        enabled_by_internal_slot=(
            enabled_by_internal_slot
        ),
    )


def apply_visual_move(
    current_order: tuple[int, ...],
    source_position: int,
    destination_position: int,
) -> tuple[int, ...]:
    """Aplica localmente um movimento visual."""

    effect_count = len(
        current_order
    )

    if not 1 <= source_position <= effect_count:
        raise ValueError(
            "Origem fora do intervalo."
        )

    if not 1 <= destination_position <= effect_count:
        raise ValueError(
            "Destino fora do intervalo."
        )

    if source_position == destination_position:
        raise ValueError(
            "Origem e destino não podem ser iguais."
        )

    reordered = list(
        current_order
    )

    moved_slot = reordered.pop(
        source_position - 1
    )

    reordered.insert(
        destination_position - 1,
        moved_slot,
    )

    return tuple(
        reordered
    )
