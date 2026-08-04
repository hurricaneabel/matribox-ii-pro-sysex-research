"""Comandos para criar, remover e substituir efeitos na cadeia visual.

O comando SysEx 0x17 foi validado fisicamente para criar FREQ, DRV e DYN em
slots ausentes, remover slots existentes e substituir efeitos entre classes.

Slots apresentados ao usuário usam 1 a 12. O protocolo usa 0 a 11.
O valor 0xFF, codificado como 0F 0F, representa uma posição vazia.
"""

from __future__ import annotations

import mido

from tools.commands.effect_catalog import (
    DRV_CLASS_ID,
    DRV_MODELS,
    DYN_CLASS_ID,
    DYN_MODELS,
    EFFECT_CLASSES,
    FREQ_CLASS_ID,
    FREQ_MODELS,
    EffectClass,
    EffectModel,
    find_effect_class,
    find_effect_model,
)


CHECKSUM_INDEX = 7
COMMAND_TYPE_INDEX = 9

SOURCE_SLOT_HIGH_INDEX = 39
SOURCE_SLOT_LOW_INDEX = 40
DESTINATION_SLOT_HIGH_INDEX = 41
DESTINATION_SLOT_LOW_INDEX = 42

CLASS_HIGH_INDEX = 43
CLASS_LOW_INDEX = 44
MODEL_HIGH_INDEX = 45
MODEL_LOW_INDEX = 46
SECONDARY_SELECTOR_INDEX = 52

# Alias preservado para compatibilidade com os testes e imports anteriores.
CLASS_MIRROR_INDEX = SECONDARY_SELECTOR_INDEX
ENABLED_HIGH_INDEX = CLASS_HIGH_INDEX
ENABLED_LOW_INDEX = CLASS_LOW_INDEX

MIN_SLOT = 1
MAX_SLOT = 12
EMPTY_SLOT_ID = 0xFF

EXPECTED_MESSAGE_LENGTH = 60
EXPECTED_COMMAND_TYPE = 0x17

REMOVE_TEMPLATE_HEX = (
    "f021254d5000004e12170000000001000000000100000f00"
    "0000000000010c0001000000040001000a0f0f0000000000"
    "0000000000010100000000f7"
)

ADD_TEMPLATE_HEX = (
    "f021254d5000005a12170000000001000000000100000f00"
    "0000000000010c00010000000400010f0f000a0001010900"
    "0000000001010100000000f7"
)


def split_into_nibbles(value: int) -> tuple[int, int]:
    """Separa um byte em nibble alto e nibble baixo."""
    if not 0 <= value <= 0xFF:
        raise ValueError(
            "O valor deve estar entre 0x00 e 0xFF."
        )

    return (
        (value >> 4) & 0x0F,
        value & 0x0F,
    )


def validate_slot(slot_number: int) -> None:
    """Valida o slot apresentado ao usuário."""
    if not MIN_SLOT <= slot_number <= MAX_SLOT:
        raise ValueError(
            f"O slot deve estar entre {MIN_SLOT} e {MAX_SLOT}."
        )


def validate_effect_ids(
    class_id: int,
    model_id: int,
    secondary_selector: int | None = None,
) -> None:
    """Valida IDs de classe, modelo e seletor secundário."""
    for field_name, value in (
        ("classe", class_id),
        ("modelo", model_id),
    ):
        if not 0 <= value <= 0xFF:
            raise ValueError(
                f"O ID de {field_name} deve estar entre 0x00 e 0xFF."
            )

    if secondary_selector is not None and not 0 <= secondary_selector <= 0x7F:
        raise ValueError(
            "O seletor secundário deve estar entre 0x00 e 0x7F."
        )


def calculate_checksum(message: list[int]) -> int:
    """Calcula o checksum observado nos comandos de escrita."""
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
    """Valida a estrutura comum do comando 0x17."""
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
    """Mantém compatibilidade com o comando FREQ anterior."""
    freq_class = next(
        item
        for item in EFFECT_CLASSES
        if item.class_id == FREQ_CLASS_ID
    )

    return find_effect_model(
        freq_class,
        value,
    )


def _resolve_secondary_selector(
    class_id: int,
    secondary_selector: int | None,
) -> int:
    """Mantém compatibilidade: FREQ e DRV usavam o ID da classe."""
    if secondary_selector is None:
        return class_id

    return secondary_selector


def _set_effect_fields(
    full_message: list[int],
    class_id: int,
    model_id: int,
    secondary_selector: int | None,
) -> None:
    """Aplica classe, modelo e seletor secundário ao pacote."""
    resolved_selector = _resolve_secondary_selector(
        class_id,
        secondary_selector,
    )

    class_high, class_low = split_into_nibbles(
        class_id
    )
    model_high, model_low = split_into_nibbles(
        model_id
    )

    full_message[CLASS_HIGH_INDEX] = class_high
    full_message[CLASS_LOW_INDEX] = class_low
    full_message[MODEL_HIGH_INDEX] = model_high
    full_message[MODEL_LOW_INDEX] = model_low
    full_message[SECONDARY_SELECTOR_INDEX] = resolved_selector


def build_add_effect_message(
    slot_number: int,
    model_id: int,
    class_id: int = FREQ_CLASS_ID,
    secondary_selector: int | None = None,
) -> mido.Message:
    """Cria um efeito em um slot ausente da cadeia visual."""
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

    full_message[SOURCE_SLOT_HIGH_INDEX] = empty_high
    full_message[SOURCE_SLOT_LOW_INDEX] = empty_low
    full_message[DESTINATION_SLOT_HIGH_INDEX] = slot_high
    full_message[DESTINATION_SLOT_LOW_INDEX] = slot_low

    _set_effect_fields(
        full_message,
        class_id,
        model_id,
        secondary_selector,
    )

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
    """Remove um slot existente da cadeia visual."""
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


def build_replace_effect_message(
    slot_number: int,
    class_id: int,
    model_id: int,
    secondary_selector: int | None = None,
) -> mido.Message:
    """Substitui classe e modelo mantendo o mesmo slot visual."""
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
            ADD_TEMPLATE_HEX
        )
    )

    validate_message(
        full_message
    )

    slot_high, slot_low = split_into_nibbles(
        slot_number - 1
    )

    full_message[SOURCE_SLOT_HIGH_INDEX] = slot_high
    full_message[SOURCE_SLOT_LOW_INDEX] = slot_low
    full_message[DESTINATION_SLOT_HIGH_INDEX] = slot_high
    full_message[DESTINATION_SLOT_LOW_INDEX] = slot_low

    _set_effect_fields(
        full_message,
        class_id,
        model_id,
        secondary_selector,
    )

    full_message[CHECKSUM_INDEX] = calculate_checksum(
        full_message
    )

    return mido.Message(
        "sysex",
        data=full_message[1:-1],
    )


def full_message_bytes(message: mido.Message) -> bytes:
    """Retorna a mensagem incluindo F0 e F7."""
    return bytes(
        message.bin()
    )
