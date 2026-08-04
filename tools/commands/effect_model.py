"""Troca de modelo dentro da mesma classe usando o comando 0x16.

Para trocar entre classes diferentes, use o comando 0x17 por meio de
``build_replace_effect_message``.
"""

from __future__ import annotations

import mido

from tools.commands.effect_chain import (
    resolve_effect_instance_flag,
    split_into_nibbles,
    validate_effect_ids,
    validate_slot,
)


CHECKSUM_INDEX = 7
COMMAND_TYPE_INDEX = 9

SLOT_HIGH_INDEX = 39
SLOT_LOW_INDEX = 40
CLASS_HIGH_INDEX = 41
CLASS_LOW_INDEX = 42
MODEL_HIGH_INDEX = 43
MODEL_LOW_INDEX = 44
EFFECT_INSTANCE_FLAG_INDEX = 47
SECONDARY_SELECTOR_INDEX = 50

# Alias preservado para compatibilidade com os testes anteriores.
CLASS_MIRROR_INDEX = SECONDARY_SELECTOR_INDEX

EXPECTED_MESSAGE_LENGTH = 58
EXPECTED_COMMAND_TYPE = 0x16

MODEL_TEMPLATE_HEX = (
    "f021254d5000003512160000000001000000000100000e"
    "000000000000010b0002000000040001000a0003000000"
    "0000000003010100000000f7"
)


def calculate_checksum(message: list[int]) -> int:
    """Calcula o checksum do comando 0x16."""
    if len(message) != EXPECTED_MESSAGE_LENGTH:
        raise ValueError(
            "O comando de modelo deve possuir "
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


def build_set_effect_model_message(
    slot_number: int,
    class_id: int,
    model_id: int,
    secondary_selector: int | None = None,
) -> mido.Message:
    """Troca o modelo mantendo a classe indicada."""
    validate_slot(
        slot_number
    )
    validate_effect_ids(
        class_id,
        model_id,
        secondary_selector,
    )

    full_message = list(
        bytes.fromhex(
            MODEL_TEMPLATE_HEX
        )
    )

    if len(full_message) != EXPECTED_MESSAGE_LENGTH:
        raise RuntimeError(
            "Tamanho inesperado do pacote-base."
        )

    if full_message[COMMAND_TYPE_INDEX] != EXPECTED_COMMAND_TYPE:
        raise RuntimeError(
            "Tipo de comando inesperado."
        )

    slot_high, slot_low = split_into_nibbles(
        slot_number - 1
    )
    class_high, class_low = split_into_nibbles(
        class_id
    )
    model_high, model_low = split_into_nibbles(
        model_id
    )

    if secondary_selector is None:
        secondary_selector = class_id

    full_message[SLOT_HIGH_INDEX] = slot_high
    full_message[SLOT_LOW_INDEX] = slot_low
    full_message[CLASS_HIGH_INDEX] = class_high
    full_message[CLASS_LOW_INDEX] = class_low
    full_message[MODEL_HIGH_INDEX] = model_high
    full_message[MODEL_LOW_INDEX] = model_low
    full_message[EFFECT_INSTANCE_FLAG_INDEX] = (
        resolve_effect_instance_flag(
            class_id
        )
    )
    full_message[SECONDARY_SELECTOR_INDEX] = secondary_selector

    full_message[CHECKSUM_INDEX] = calculate_checksum(
        full_message
    )

    return mido.Message(
        "sysex",
        data=full_message[1:-1],
    )
