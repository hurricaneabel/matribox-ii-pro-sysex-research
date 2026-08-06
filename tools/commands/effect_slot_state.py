"""Leitura da resposta imediata de liga/desliga de um efeito.

A Matribox II Pro envia uma resposta SysEx de 62 bytes quando o estado de
bypass de um slot interno muda. Essa resposta não contém a cadeia completa;
ela informa apenas:

- o slot interno afetado;
- o novo estado, ``0`` para desligado e ``1`` para ligado.

O checksum observado nessas respostas varia entre capturas equivalentes, por
isso ele é preservado para diagnóstico, mas não é usado como critério de
aceitação. Todos os demais bytes fixos são confrontados com a estrutura
capturada fisicamente nos cinco primeiros slots.

Este módulo trabalha somente com bytes e não abre portas MIDI.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


MATRIBOX_HEADER: Final = bytes.fromhex("F0 21 25 4D 50")
DIRECTION_INCOMING: Final = 0x00
DIRECTION_INDEX: Final = 8
LENGTH_UNITS_INDEX: Final = 9
EXPECTED_LENGTH_UNITS: Final = 0x18
MESSAGE_OVERHEAD: Final = 14
EXPECTED_MESSAGE_LENGTH: Final = (
    MESSAGE_OVERHEAD + EXPECTED_LENGTH_UNITS * 2
)

CHECKSUM_INDEX: Final = 7
SLOT_HIGH_INDEX: Final = 39
SLOT_LOW_INDEX: Final = 40
STATE_HIGH_INDEX: Final = 47
STATE_LOW_INDEX: Final = 48
MAX_INTERNAL_SLOTS: Final = 12

# Resposta física capturada para o slot interno 1 desligado. Os índices de
# checksum, slot e estado são variáveis; todo o restante identifica o tipo de
# mensagem com segurança suficiente para não confundi-lo com outros SysEx.
_RESPONSE_TEMPLATE: Final = bytes.fromhex(
    "F0 21 25 4D 50 00 00 53 00 18 "
    "00 00 00 00 01 00 00 00 00 01 00 01 00 00 00 00 00 00 00 01 "
    "0D 00 02 00 00 00 05 00 01 00 00 00 00 00 00 00 00 00 00 00 "
    "00 00 00 00 00 01 01 00 00 00 00 F7"
)

_VARIABLE_INDICES: Final = frozenset(
    {
        CHECKSUM_INDEX,
        SLOT_HIGH_INDEX,
        SLOT_LOW_INDEX,
        STATE_HIGH_INDEX,
        STATE_LOW_INDEX,
    }
)


class EffectSlotStateProtocolError(ValueError):
    """Erro em uma resposta reconhecida de estado de slot."""


@dataclass(frozen=True, slots=True)
class EffectSlotStateEvent:
    """Mudança imediata do bypass de um slot interno."""

    internal_slot_id: int
    enabled: bool
    observed_checksum: int
    raw_message: bytes

    @property
    def human_slot(self) -> int:
        """Slot apresentado ao usuário, numerado de 1 a 12."""

        return self.internal_slot_id + 1


def _decode_nibble_pair(
    high_nibble: int,
    low_nibble: int,
    *,
    field_name: str,
) -> int:
    if not 0 <= high_nibble <= 0x0F:
        raise EffectSlotStateProtocolError(
            f"Nibble alto inválido em {field_name}: "
            f"0x{high_nibble:02X}."
        )

    if not 0 <= low_nibble <= 0x0F:
        raise EffectSlotStateProtocolError(
            f"Nibble baixo inválido em {field_name}: "
            f"0x{low_nibble:02X}."
        )

    return (high_nibble << 4) | low_nibble


def _matches_fixed_template(raw_message: bytes) -> bool:
    return all(
        index in _VARIABLE_INDICES
        or value == _RESPONSE_TEMPLATE[index]
        for index, value in enumerate(raw_message)
    )


def parse_effect_slot_state_response(
    message: bytes | bytearray,
) -> EffectSlotStateEvent | None:
    """Interpreta uma resposta imediata de liga/desliga.

    Retorna ``None`` para mensagens de outro tipo. Quando a estrutura é
    reconhecida, mas os campos variáveis são inválidos, levanta
    :class:`EffectSlotStateProtocolError`.
    """

    raw_message = bytes(message)

    if len(raw_message) != EXPECTED_MESSAGE_LENGTH:
        return None

    if raw_message[: len(MATRIBOX_HEADER)] != MATRIBOX_HEADER:
        return None

    if raw_message[-1] != 0xF7:
        return None

    if raw_message[DIRECTION_INDEX] != DIRECTION_INCOMING:
        return None

    if raw_message[LENGTH_UNITS_INDEX] != EXPECTED_LENGTH_UNITS:
        return None

    if not _matches_fixed_template(raw_message):
        return None

    internal_slot_id = _decode_nibble_pair(
        raw_message[SLOT_HIGH_INDEX],
        raw_message[SLOT_LOW_INDEX],
        field_name="slot interno",
    )

    if not 0 <= internal_slot_id < MAX_INTERNAL_SLOTS:
        raise EffectSlotStateProtocolError(
            "Slot interno fora do intervalo na resposta de bypass: "
            f"{internal_slot_id + 1}."
        )

    state_value = _decode_nibble_pair(
        raw_message[STATE_HIGH_INDEX],
        raw_message[STATE_LOW_INDEX],
        field_name="estado",
    )

    if state_value not in (0x00, 0x01):
        raise EffectSlotStateProtocolError(
            "Estado de bypass inválido: "
            f"0x{state_value:02X}."
        )

    return EffectSlotStateEvent(
        internal_slot_id=internal_slot_id,
        enabled=bool(state_value),
        observed_checksum=raw_message[CHECKSUM_INDEX],
        raw_message=raw_message,
    )
