"""Protocolo estável de leitura e seleção do preset atual.

Descobertas confirmadas na Matribox II Pro:

- consulta do preset atual: comando 0x10, 46 bytes;
- seleção e evento de preset: comando 0x14, 54 bytes;
- endereço do preset nos índices 39 e 40 como dois nibbles;
- índice absoluto: (bank - 1) * 4 + posição A/B/C/D;
- eventos espontâneos e confirmações chegam com direção 0x00;
- seleções enviadas usam direção 0x12.

Este módulo trabalha apenas com bytes. Ele não abre portas MIDI e não
envia mensagens à pedaleira.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from tools.commands.global_preset_metadata import (
    PRESET_COUNT,
    preset_index_to_label,
    preset_label_to_index,
)


MATRIBOX_HEADER: Final = bytes.fromhex(
    "F0 21 25 4D 50"
)

CURRENT_PRESET_QUERY: Final = bytes.fromhex(
    "F0 21 25 4D 50 00 00 1E 11 10 "
    "00 00 00 00 01 00 00 00 00 01 "
    "00 00 08 00 00 00 00 00 00 01 "
    "05 00 01 00 00 00 0A 00 01 01 "
    "01 00 00 00 00 F7"
)

_SELECT_PRESET_45B_CAPTURE: Final = bytes.fromhex(
    "F0 21 25 4D 50 00 00 32 12 14 "
    "00 00 00 00 01 00 00 00 00 01 "
    "00 00 0C 00 00 00 00 00 00 01 "
    "09 00 01 00 00 00 0A 00 01 0B "
    "01 00 00 00 00 00 00 01 01 00 "
    "00 00 00 F7"
)

EXPECTED_QUERY_LENGTH: Final = 46
EXPECTED_EVENT_LENGTH: Final = 54

CHECKSUM_INDEX: Final = 7
DIRECTION_INDEX: Final = 8
COMMAND_INDEX: Final = 9
ADDRESS_HIGH_INDEX: Final = 39
ADDRESS_LOW_INDEX: Final = 40

DIRECTION_INCOMING: Final = 0x00
DIRECTION_QUERY: Final = 0x11
DIRECTION_COMMAND: Final = 0x12

COMMAND_QUERY_CURRENT_PRESET: Final = 0x10
COMMAND_PRESET_EVENT: Final = 0x14


class PresetStateProtocolError(ValueError):
    """Erro de construção ou validação do protocolo de preset."""


@dataclass(frozen=True, slots=True)
class PresetEvent:
    """Evento recebido ao consultar ou trocar o preset."""

    index: int
    label: str
    observed_checksum: int
    calculated_checksum: int
    raw_message: bytes

    @property
    def checksum_matches(self) -> bool:
        """Indica se o checksum recebido coincide com o cálculo conhecido."""
        return self.observed_checksum == self.calculated_checksum


def calculate_protocol_checksum(message: bytes | bytearray) -> int:
    """Calcula o checksum observado nos comandos 0x10 e 0x14.

    O byte de comando também informa o tamanho da região somada em pares:
        checksum = sum(message[10:10 + command * 2]) & 0x7F
    """
    if len(message) <= COMMAND_INDEX:
        raise PresetStateProtocolError(
            "Mensagem curta demais para calcular o checksum."
        )

    command = message[COMMAND_INDEX]
    payload_end = 10 + command * 2

    if payload_end > len(message) - 1:
        raise PresetStateProtocolError(
            "A região declarada para o checksum excede a mensagem."
        )

    return sum(message[10:payload_end]) & 0x7F


def encode_preset_index(index: int) -> tuple[int, int]:
    """Codifica o índice absoluto em dois nibbles."""
    if not 0 <= index < PRESET_COUNT:
        raise ValueError(
            f"Índice de preset fora do intervalo: {index}."
        )

    return (
        (index >> 4) & 0x0F,
        index & 0x0F,
    )


def decode_preset_address(
    high_nibble: int,
    low_nibble: int,
) -> int:
    """Decodifica os dois nibbles do endereço do preset."""
    if not 0 <= high_nibble <= 0x0F:
        raise PresetStateProtocolError(
            f"Nibble alto inválido: 0x{high_nibble:02X}."
        )

    if not 0 <= low_nibble <= 0x0F:
        raise PresetStateProtocolError(
            f"Nibble baixo inválido: 0x{low_nibble:02X}."
        )

    index = (
        (high_nibble << 4)
        | low_nibble
    )

    if not 0 <= index < PRESET_COUNT:
        raise PresetStateProtocolError(
            f"Endereço aponta para índice inexistente: {index}."
        )

    return index


def normalize_preset(
    preset: str | int,
) -> tuple[int, str]:
    """Normaliza um rótulo ou índice para as duas representações."""
    if isinstance(preset, str):
        index = preset_label_to_index(preset)
    elif isinstance(preset, int) and not isinstance(preset, bool):
        index = preset

        if not 0 <= index < PRESET_COUNT:
            raise ValueError(
                f"Índice de preset fora do intervalo: {index}."
            )
    else:
        raise TypeError(
            "O preset deve ser um rótulo como '45B' "
            "ou um índice inteiro."
        )

    return (
        index,
        preset_index_to_label(index),
    )


def build_current_preset_query() -> bytes:
    """Retorna a consulta oficial validada do preset atual."""
    query = CURRENT_PRESET_QUERY

    if len(query) != EXPECTED_QUERY_LENGTH:
        raise AssertionError(
            "A consulta validada perdeu o tamanho esperado."
        )

    if (
        calculate_protocol_checksum(query)
        != query[CHECKSUM_INDEX]
    ):
        raise AssertionError(
            "A consulta validada possui checksum inconsistente."
        )

    return query


def build_select_preset(
    preset: str | int,
) -> bytes:
    """Monta o comando 0x14 que seleciona um preset."""
    index, _label = normalize_preset(preset)
    high_nibble, low_nibble = encode_preset_index(index)

    message = bytearray(
        _SELECT_PRESET_45B_CAPTURE
    )

    message[ADDRESS_HIGH_INDEX] = high_nibble
    message[ADDRESS_LOW_INDEX] = low_nibble
    message[CHECKSUM_INDEX] = 0

    message[CHECKSUM_INDEX] = (
        calculate_protocol_checksum(message)
    )

    return bytes(message)


def _has_preset_event_structure(
    message: bytes,
) -> bool:
    """Valida os campos estruturais conhecidos do evento 0x14."""
    return (
        len(message) == EXPECTED_EVENT_LENGTH
        and message[:5] == MATRIBOX_HEADER
        and message[-1] == 0xF7
        and message[DIRECTION_INDEX] == DIRECTION_INCOMING
        and message[COMMAND_INDEX] == COMMAND_PRESET_EVENT
        and message[22] == 0x0C
        and message[30] == 0x09
        and message[36] == 0x0A
    )


def parse_preset_event(
    message: bytes | bytearray,
) -> PresetEvent | None:
    """Interpreta uma resposta ou mudança espontânea de preset.

    O checksum recebido é registrado, mas não é usado para rejeitar o evento.
    Capturas reais mostraram confirmações estruturalmente idênticas com
    checksums diferentes.
    """
    raw_message = bytes(message)

    if not _has_preset_event_structure(
        raw_message
    ):
        return None

    try:
        index = decode_preset_address(
            raw_message[ADDRESS_HIGH_INDEX],
            raw_message[ADDRESS_LOW_INDEX],
        )
    except PresetStateProtocolError:
        return None

    return PresetEvent(
        index=index,
        label=preset_index_to_label(index),
        observed_checksum=raw_message[CHECKSUM_INDEX],
        calculated_checksum=calculate_protocol_checksum(
            raw_message
        ),
        raw_message=raw_message,
    )


def is_preset_confirmation(
    message: bytes | bytearray,
    expected_preset: str | int,
) -> bool:
    """Confirma se o evento recebido corresponde ao preset solicitado."""
    expected_index, _label = normalize_preset(
        expected_preset
    )

    event = parse_preset_event(message)

    return (
        event is not None
        and event.index == expected_index
    )
