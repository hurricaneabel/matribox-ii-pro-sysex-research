"""Valida os cinco modelos da classe EQ no slot interno 11.

Mapeamento confirmado por captura:

1. GUITAR EQ 1 = modelo 0x35
2. GUITAR EQ 2 = modelo 0x36
3. BASS EQ 1   = modelo 0x39
4. BASS EQ 2   = modelo 0x3A
5. CALIF EQ    = modelo 0x3C

Todos usam classe 0x07 e seletor secundário 0x01.
"""

from __future__ import annotations

from dataclasses import dataclass
import time

import mido


OUTPUT_PORT = "Matribox II Pro Subdevice 1"

CHECKSUM_INDEX = 7
SLOT_HIGH_INDEX = 39
SLOT_LOW_INDEX = 40
CLASS_HIGH_INDEX = 41
CLASS_LOW_INDEX = 42
MODEL_HIGH_INDEX = 43
MODEL_LOW_INDEX = 44
EFFECT_INSTANCE_FLAG_INDEX = 47
SECONDARY_SELECTOR_INDEX = 50

EXPECTED_MESSAGE_LENGTH = 58
EXPECTED_COMMAND_TYPE = 0x16

SLOT_NUMBER = 11
PROTOCOL_SLOT = SLOT_NUMBER - 1

EQ_CLASS_ID = 0x07
EQ_INSTANCE_FLAG = 0x00
STEP_DELAY_SECONDS = 2.0

GUITAR_EQ_1_TEMPLATE_HEX = "f021254d5000003f12160000000001000000000100000e000000000000010b0002000000040001000a00070305000000000001010100000000f7"


@dataclass(frozen=True)
class EqModel:
    menu_number: int
    name: str
    model_id: int
    secondary_selector: int
    expected_checksum: int


EQ_MODELS = (
    EqModel(1, "GUITAR EQ 1", 0x35, 0x01, 0x3F),
    EqModel(2, "GUITAR EQ 2", 0x36, 0x01, 0x40),
    EqModel(3, "BASS EQ 1", 0x39, 0x01, 0x43),
    EqModel(4, "BASS EQ 2", 0x3A, 0x01, 0x44),
    EqModel(5, "CALIF EQ", 0x3C, 0x01, 0x46),
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


def calculate_checksum(message: list[int]) -> int:
    if len(message) != EXPECTED_MESSAGE_LENGTH:
        raise ValueError(
            "A mensagem deve possuir "
            f"{EXPECTED_MESSAGE_LENGTH} bytes."
        )

    payload_start = 10
    payload_end = payload_start + (message[9] * 2)

    return sum(
        message[payload_start:payload_end]
    ) & 0x7F


def build_eq_message(
    eq_model: EqModel,
) -> mido.Message:
    full_message = list(
        bytes.fromhex(
            GUITAR_EQ_1_TEMPLATE_HEX
        )
    )

    if len(full_message) != EXPECTED_MESSAGE_LENGTH:
        raise RuntimeError(
            "Tamanho inesperado do pacote-base."
        )

    if full_message[9] != EXPECTED_COMMAND_TYPE:
        raise RuntimeError(
            "Tipo de comando inesperado."
        )

    slot_high, slot_low = split_into_nibbles(
        PROTOCOL_SLOT
    )
    class_high, class_low = split_into_nibbles(
        EQ_CLASS_ID
    )
    model_high, model_low = split_into_nibbles(
        eq_model.model_id
    )

    full_message[SLOT_HIGH_INDEX] = slot_high
    full_message[SLOT_LOW_INDEX] = slot_low
    full_message[CLASS_HIGH_INDEX] = class_high
    full_message[CLASS_LOW_INDEX] = class_low
    full_message[MODEL_HIGH_INDEX] = model_high
    full_message[MODEL_LOW_INDEX] = model_low
    full_message[EFFECT_INSTANCE_FLAG_INDEX] = (
        EQ_INSTANCE_FLAG
    )
    full_message[SECONDARY_SELECTOR_INDEX] = (
        eq_model.secondary_selector
    )

    full_message[CHECKSUM_INDEX] = calculate_checksum(
        full_message
    )

    if full_message[CHECKSUM_INDEX] != eq_model.expected_checksum:
        raise RuntimeError(
            f"Checksum de {eq_model.name} inesperado: "
            f"0x{full_message[CHECKSUM_INDEX]:02X}. "
            f"Esperado: 0x{eq_model.expected_checksum:02X}."
        )

    return mido.Message(
        "sysex",
        data=full_message[1:-1],
    )


def print_models() -> None:
    print(
        "EQ — cinco modelos confirmados:"
    )

    for eq_model in EQ_MODELS:
        print(
            f"{eq_model.menu_number}. "
            f"{eq_model.name:<12} "
            f"modelo 0x{eq_model.model_id:02X} "
            f"seletor 0x{eq_model.secondary_selector:02X} "
            f"checksum 0x{eq_model.expected_checksum:02X}"
        )


def send_eq_model(
    output,
    eq_model: EqModel,
) -> None:
    message = build_eq_message(
        eq_model
    )
    packet = bytes(
        message.bin()
    )

    print(
        f"\n{eq_model.name}"
    )
    print(
        f"modelo: 0x{eq_model.model_id:02X}"
    )
    print(
        f"flag: 0x{packet[EFFECT_INSTANCE_FLAG_INDEX]:02X}"
    )
    print(
        f"seletor secundário: "
        f"0x{packet[SECONDARY_SELECTOR_INDEX]:02X}"
    )
    print(
        f"checksum: 0x{packet[CHECKSUM_INDEX]:02X}"
    )

    output.send(
        message
    )


def run_all_models(output) -> None:
    print(
        "\nIniciando o teste automático dos cinco EQs."
    )

    for eq_model in EQ_MODELS[1:]:
        send_eq_model(
            output,
            eq_model,
        )
        time.sleep(
            STEP_DELAY_SECONDS
        )

    send_eq_model(
        output,
        EQ_MODELS[0],
    )

    print(
        "\nSequência concluída. "
        "Estado final: GUITAR EQ 1."
    )


def main() -> None:
    try:
        print(
            "Validação EQ — slot interno 11"
        )
        print(
            "Comece com o slot 11 em GUITAR EQ 1."
        )
        print()

        print_models()

        print(
            "\nDigite um número de 1 a 5 para testar individualmente."
        )
        print(
            "Digite A para percorrer todos automaticamente."
        )

        option = input(
            "\nEscolha: "
        ).strip().lower()

        with mido.open_output(
            OUTPUT_PORT
        ) as output:
            if option == "a":
                run_all_models(
                    output
                )
                return

            menu_number = int(
                option
            )

            eq_model = next(
                (
                    item
                    for item in EQ_MODELS
                    if item.menu_number == menu_number
                ),
                None,
            )

            if eq_model is None:
                raise ValueError(
                    "Escolha um número entre 1 e 5."
                )

            send_eq_model(
                output,
                eq_model,
            )

            print(
                "\nComando enviado."
            )

    except (
        OSError,
        RuntimeError,
        ValueError,
    ) as error:
        print(
            f"\nErro: {error}"
        )

    except KeyboardInterrupt:
        print(
            "\nTeste interrompido."
        )


if __name__ == "__main__":
    main()