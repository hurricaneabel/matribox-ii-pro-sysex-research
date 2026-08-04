"""Builders para adicionar e remover efeitos da cadeia visual.

O comando SysEx 0x17 foi validado fisicamente nos seguintes casos:

- remover Filter do slot interno 11;
- adicionar Filter e Octaver ao slot interno 11;
- adicionar e remover Filter no slot interno 12.

Slots de interface usam 1 a 12. No protocolo, os slots usam 0 a 11.
O valor 0xFF, codificado como 0F 0F, representa uma posição vazia.
"""

from __future__ import annotations

from dataclasses import dataclass

import mido


CHECKSUM_INDEX = 7
COMMAND_TYPE_INDEX = 9

SOURCE_SLOT_HIGH_INDEX = 39
SOURCE_SLOT_LOW_INDEX = 40
DESTINATION_SLOT_HIGH_INDEX = 41
DESTINATION_SLOT_LOW_INDEX = 42

ENABLED_HIGH_INDEX = 43
ENABLED_LOW_INDEX = 44
MODEL_HIGH_INDEX = 45
MODEL_LOW_INDEX = 46

MIN_SLOT = 1
MAX_SLOT = 12
EMPTY_SLOT_ID = 0xFF

EXPECTED_MESSAGE_LENGTH = 60
EXPECTED_COMMAND_TYPE = 0x17

REMOVE_TEMPLATE_HEX = "f021254d5000004e12170000000001000000000100000f000000000000010c0001000000040001000a0f0f00000000000000000000010100000000f7"
ADD_TEMPLATE_HEX = "f021254d5000005a12170000000001000000000100000f000000000000010c00010000000400010f0f000a00010109000000000001010100000000f7"


@dataclass(frozen=True)
class EffectModel:
    menu_number: int
    name: str
    model_id: int


FREQ_MODELS = (
    EffectModel(1, "Filter", 0x19),
    EffectModel(2, "Octaver", 0x21),
    EffectModel(3, "Dual Melody", 0x23),
    EffectModel(4, "Pitch", 0x24),
    EffectModel(5, "Harmony D", 0x4E),
    EffectModel(6, "Pitch S", 0x55),
    EffectModel(7, "Ring Mod", 0x2F),
    EffectModel(8, "Tape Mod", 0x33),
)


def split_into_nibbles(value: int) -> tuple[int, int]:
    if not 0 <= value <= 0xFF:
        raise ValueError(
            "O valor deve estar entre 0x00 e 0xFF."
        )

    return (
        (value >> 4) & 0x0F,
        value & 0x0F,
    )


def validate_slot(slot_number: int) -> None:
    if not MIN_SLOT <= slot_number <= MAX_SLOT:
        raise ValueError(
            f"O slot deve estar entre {MIN_SLOT} e {MAX_SLOT}."
        )


def calculate_checksum(message: list[int]) -> int:
    if len(message) != EXPECTED_MESSAGE_LENGTH:
        raise ValueError(
            "O comando de cadeia deve possuir "
            f"{EXPECTED_MESSAGE_LENGTH} bytes."
        )

    payload_start = 10
    payload_end = payload_start + (message[9] * 2)

    if payload_end > len(message) - 1:
        raise ValueError(
            "O tamanho declarado ultrapassa o fim da mensagem."
        )

    return sum(
        message[payload_start:payload_end]
    ) & 0x7F


def validate_message(message: list[int]) -> None:
    if len(message) != EXPECTED_MESSAGE_LENGTH:
        raise RuntimeError(
            "O pacote deveria possuir "
            f"{EXPECTED_MESSAGE_LENGTH} bytes, mas possui "
            f"{len(message)}."
        )

    if message[0] != 0xF0 or message[-1] != 0xF7:
        raise RuntimeError(
            "Delimitadores SysEx inválidos."
        )

    if message[COMMAND_TYPE_INDEX] != EXPECTED_COMMAND_TYPE:
        raise RuntimeError(
            "Tipo de comando inesperado: "
            f"0x{message[COMMAND_TYPE_INDEX]:02X}."
        )


def find_freq_model(value: str) -> EffectModel:
    normalized = value.strip().lower()

    for model in FREQ_MODELS:
        accepted_values = {
            str(model.menu_number),
            model.name.lower(),
            f"{model.model_id:02x}",
            f"0x{model.model_id:02x}",
        }

        if normalized in accepted_values:
            return model

    raise ValueError(
        "Modelo FREQ não encontrado."
    )


def build_add_effect_message(
    slot_number: int,
    model_id: int,
) -> mido.Message:
    validate_slot(
        slot_number
    )

    if not 0 <= model_id <= 0xFF:
        raise ValueError(
            "O ID do modelo deve estar entre 0x00 e 0xFF."
        )

    full_message = list(
        bytes.fromhex(
            ADD_TEMPLATE_HEX
        )
    )

    validate_message(
        full_message
    )

    empty_high, empty_low = split_into_nibbles(
        EMPTY_SLOT_ID
    )
    slot_high, slot_low = split_into_nibbles(
        slot_number - 1
    )
    model_high, model_low = split_into_nibbles(
        model_id
    )

    full_message[SOURCE_SLOT_HIGH_INDEX] = empty_high
    full_message[SOURCE_SLOT_LOW_INDEX] = empty_low
    full_message[DESTINATION_SLOT_HIGH_INDEX] = slot_high
    full_message[DESTINATION_SLOT_LOW_INDEX] = slot_low
    full_message[ENABLED_HIGH_INDEX] = 0x00
    full_message[ENABLED_LOW_INDEX] = 0x01
    full_message[MODEL_HIGH_INDEX] = model_high
    full_message[MODEL_LOW_INDEX] = model_low

    full_message[CHECKSUM_INDEX] = calculate_checksum(
        full_message
    )

    return mido.Message(
        "sysex",
        data=full_message[1:-1],
    )


def build_remove_effect_message(
    slot_number: int,
) -> mido.Message:
    validate_slot(
        slot_number
    )

    full_message = list(
        bytes.fromhex(
            REMOVE_TEMPLATE_HEX
        )
    )

    validate_message(
        full_message
    )

    slot_high, slot_low = split_into_nibbles(
        slot_number - 1
    )
    empty_high, empty_low = split_into_nibbles(
        EMPTY_SLOT_ID
    )

    full_message[SOURCE_SLOT_HIGH_INDEX] = slot_high
    full_message[SOURCE_SLOT_LOW_INDEX] = slot_low
    full_message[DESTINATION_SLOT_HIGH_INDEX] = empty_high
    full_message[DESTINATION_SLOT_LOW_INDEX] = empty_low

    full_message[CHECKSUM_INDEX] = calculate_checksum(
        full_message
    )

    return mido.Message(
        "sysex",
        data=full_message[1:-1],
    )


def full_message_bytes(message: mido.Message) -> bytes:
    return bytes(
        message.bin()
    )
