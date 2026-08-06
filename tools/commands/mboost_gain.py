"""Leitura pura do parâmetro GAIN do DYN / M-BOOST.

As capturas USB/Wireshark confirmaram respostas SysEx de 70 bytes para o
comando ``0x1C``. A mensagem contém:

- slot interno zero-based nos índices 39–40;
- classe DYN nos índices 41–42;
- modelo M-BOOST (``0x14``) nos índices 21–22;
- GAIN nos índices 59–62;
- valor codificado como os 16 bits superiores de um ``float32`` little-endian,
  separados em quatro nibbles.

Este módulo somente interpreta bytes. Ele não abre portas MIDI e não envia
alterações para a pedaleira.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import struct
from typing import Final


MATRIBOX_HEADER: Final = bytes.fromhex("F0 21 25 4D 50")
EXPECTED_MESSAGE_LENGTH: Final = 70
CHECKSUM_INDEX: Final = 7
DIRECTION_INDEX: Final = 8
COMMAND_INDEX: Final = 9
DIRECTION_INCOMING: Final = 0x00
COMMAND_PARAMETER: Final = 0x1C

MODEL_HIGH_INDEX: Final = 21
MODEL_LOW_INDEX: Final = 22
SLOT_HIGH_INDEX: Final = 39
SLOT_LOW_INDEX: Final = 40
CLASS_HIGH_INDEX: Final = 41
CLASS_LOW_INDEX: Final = 42
VALUE_START_INDEX: Final = 59
VALUE_END_INDEX: Final = 63
PARAMETER_MARKER_INDEX: Final = 63
PARAMETER_TYPE_INDEX: Final = 64

DYN_CLASS_ID: Final = 0x00
MBOOST_MODEL_ID: Final = 0x14
MBOOST_SECONDARY_SELECTOR: Final = 0x00
GAIN_MINIMUM: Final = 0
GAIN_MAXIMUM: Final = 100
MAX_INTERNAL_SLOTS: Final = 12

# Resposta física recebida para M-BOOST no slot interno 2 e GAIN = 0.
# Checksum, slot e valor são variáveis. Todos os demais bytes permaneceram
# idênticos nas quatro capturas controladas usadas nesta fase.
_INCOMING_TEMPLATE: Final = bytes.fromhex(
    "F0 21 25 4D 50 00 00 77 00 1C "
    "00 00 00 00 01 00 00 00 00 01 "
    "00 01 04 00 00 00 00 00 00 02 "
    "01 00 01 00 00 00 05 00 01 00 "
    "01 00 00 00 00 00 00 00 00 00 "
    "00 00 00 00 00 00 00 00 00 00 "
    "00 00 00 01 01 00 00 00 00 F7"
)

_VARIABLE_INDICES: Final = frozenset(
    {
        CHECKSUM_INDEX,
        SLOT_HIGH_INDEX,
        SLOT_LOW_INDEX,
        *range(VALUE_START_INDEX, VALUE_END_INDEX),
    }
)


class MBoostGainProtocolError(ValueError):
    """Erro em uma mensagem reconhecida de M-BOOST / GAIN."""


@dataclass(frozen=True, slots=True)
class MBoostGainEvent:
    """Alteração recebida do parâmetro GAIN do M-BOOST."""

    internal_slot_id: int
    gain: int
    encoded_gain: bytes
    observed_checksum: int
    raw_message: bytes

    @property
    def human_slot(self) -> int:
        """Slot interno apresentado ao usuário, de 1 a 12."""

        return self.internal_slot_id + 1


def _decode_nibble_pair(
    high_nibble: int,
    low_nibble: int,
    *,
    field_name: str,
) -> int:
    for label, value in (
        ("alto", high_nibble),
        ("baixo", low_nibble),
    ):
        if not 0 <= value <= 0x0F:
            raise MBoostGainProtocolError(
                f"Nibble {label} inválido em {field_name}: "
                f"0x{value:02X}."
            )

    return (high_nibble << 4) | low_nibble


def decode_gain_nibbles(encoded_gain: bytes | bytearray) -> int:
    """Decodifica os quatro nibbles do GAIN para um inteiro de 0 a 100."""

    encoded = bytes(encoded_gain)

    if len(encoded) != 4:
        raise MBoostGainProtocolError(
            "O GAIN codificado deve possuir quatro nibbles."
        )

    upper_byte_1 = _decode_nibble_pair(
        encoded[0],
        encoded[1],
        field_name="GAIN byte 1",
    )
    upper_byte_2 = _decode_nibble_pair(
        encoded[2],
        encoded[3],
        field_name="GAIN byte 2",
    )

    decoded = struct.unpack(
        "<f",
        bytes((0x00, 0x00, upper_byte_1, upper_byte_2)),
    )[0]

    if not math.isfinite(decoded):
        raise MBoostGainProtocolError(
            "O GAIN decodificado não é um número finito."
        )

    rounded = round(decoded)

    if abs(decoded - rounded) > 1e-6:
        raise MBoostGainProtocolError(
            f"O GAIN decodificado não é inteiro: {decoded}."
        )

    if not GAIN_MINIMUM <= rounded <= GAIN_MAXIMUM:
        raise MBoostGainProtocolError(
            "GAIN fora da faixa confirmada de 0 a 100: "
            f"{rounded}."
        )

    return int(rounded)


def _matches_fixed_template(raw_message: bytes) -> bool:
    return all(
        index in _VARIABLE_INDICES
        or byte == _INCOMING_TEMPLATE[index]
        for index, byte in enumerate(raw_message)
    )


def parse_mboost_gain_response(
    message: bytes | bytearray,
) -> MBoostGainEvent | None:
    """Interpreta uma resposta imediata de M-BOOST / GAIN.

    Retorna ``None`` para mensagens de outro tipo. Quando a estrutura de
    M-BOOST / GAIN é reconhecida, mas slot ou valor são inválidos, levanta
    :class:`MBoostGainProtocolError`.
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

    if raw_message[COMMAND_INDEX] != COMMAND_PARAMETER:
        return None

    if not _matches_fixed_template(raw_message):
        return None

    model_id = _decode_nibble_pair(
        raw_message[MODEL_HIGH_INDEX],
        raw_message[MODEL_LOW_INDEX],
        field_name="modelo",
    )
    class_id = _decode_nibble_pair(
        raw_message[CLASS_HIGH_INDEX],
        raw_message[CLASS_LOW_INDEX],
        field_name="classe",
    )

    if class_id != DYN_CLASS_ID or model_id != MBOOST_MODEL_ID:
        return None

    if (
        raw_message[PARAMETER_MARKER_INDEX] != 0x01
        or raw_message[PARAMETER_TYPE_INDEX] != 0x01
    ):
        return None

    internal_slot_id = _decode_nibble_pair(
        raw_message[SLOT_HIGH_INDEX],
        raw_message[SLOT_LOW_INDEX],
        field_name="slot interno",
    )

    if not 0 <= internal_slot_id < MAX_INTERNAL_SLOTS:
        raise MBoostGainProtocolError(
            "Slot interno fora do intervalo de 1 a 12: "
            f"{internal_slot_id + 1}."
        )

    encoded_gain = raw_message[VALUE_START_INDEX:VALUE_END_INDEX]
    gain = decode_gain_nibbles(encoded_gain)

    return MBoostGainEvent(
        internal_slot_id=internal_slot_id,
        gain=gain,
        encoded_gain=encoded_gain,
        observed_checksum=raw_message[CHECKSUM_INDEX],
        raw_message=raw_message,
    )
