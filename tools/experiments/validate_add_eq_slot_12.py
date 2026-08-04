"""Valida a criação direta da classe EQ no slot interno 12.

Modelos testados:
- GUITAR EQ 1: classe 0x07, modelo 0x35, seletor 0x01;
- CALIF EQ: classe 0x07, modelo 0x3C, seletor 0x01.

A classe EQ usa a flag estrutural comum 0x00.

Pré-condição:
- o slot interno 12 precisa estar ausente.
"""

from __future__ import annotations

from dataclasses import dataclass

import mido


OUTPUT_PORT = "Matribox II Pro Subdevice 1"

CHECKSUM_INDEX = 7
SOURCE_SLOT_HIGH_INDEX = 39
SOURCE_SLOT_LOW_INDEX = 40
DESTINATION_SLOT_HIGH_INDEX = 41
DESTINATION_SLOT_LOW_INDEX = 42
CLASS_HIGH_INDEX = 43
CLASS_LOW_INDEX = 44
MODEL_HIGH_INDEX = 45
MODEL_LOW_INDEX = 46
EFFECT_INSTANCE_FLAG_INDEX = 49
SECONDARY_SELECTOR_INDEX = 52

SLOT_NUMBER = 12
PROTOCOL_SLOT = SLOT_NUMBER - 1

EMPTY_SLOT_ID = 0xFF
EQ_CLASS_ID = 0x07
EQ_INSTANCE_FLAG = 0x00
EQ_SECONDARY_SELECTOR = 0x01

ADD_TEMPLATE_HEX = (
    "f021254d5000005a12170000000001000000000100000f"
    "000000000000010c00010000000400010f0f000a0001"
    "0109000000000001010100000000f7"
)

REMOVE_TEMPLATE_HEX = (
    "f021254d5000004e12170000000001000000000100000f"
    "000000000000010c0001000000040001000a0f0f0000"
    "0000000000000000010100000000f7"
)


@dataclass(frozen=True)
class EqModel:
    name: str
    model_id: int
    expected_checksum: int


GUITAR_EQ_1 = EqModel(
    name="GUITAR EQ 1",
    model_id=0x35,
    expected_checksum=0x5F,
)

CALIF_EQ = EqModel(
    name="CALIF EQ",
    model_id=0x3C,
    expected_checksum=0x66,
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
    payload_start = 10
    payload_end = payload_start + (message[9] * 2)

    return sum(
        message[payload_start:payload_end]
    ) & 0x7F


def build_add_eq_message(
    eq_model: EqModel,
) -> mido.Message:
    full_message = list(
        bytes.fromhex(
            ADD_TEMPLATE_HEX
        )
    )

    if len(full_message) != 60:
        raise RuntimeError(
            "O pacote-base de criação não possui 60 bytes."
        )

    empty_high, empty_low = split_into_nibbles(
        EMPTY_SLOT_ID
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

    full_message[SOURCE_SLOT_HIGH_INDEX] = empty_high
    full_message[SOURCE_SLOT_LOW_INDEX] = empty_low
    full_message[DESTINATION_SLOT_HIGH_INDEX] = slot_high
    full_message[DESTINATION_SLOT_LOW_INDEX] = slot_low
    full_message[CLASS_HIGH_INDEX] = class_high
    full_message[CLASS_LOW_INDEX] = class_low
    full_message[MODEL_HIGH_INDEX] = model_high
    full_message[MODEL_LOW_INDEX] = model_low
    full_message[EFFECT_INSTANCE_FLAG_INDEX] = (
        EQ_INSTANCE_FLAG
    )
    full_message[SECONDARY_SELECTOR_INDEX] = (
        EQ_SECONDARY_SELECTOR
    )

    full_message[CHECKSUM_INDEX] = calculate_checksum(
        full_message
    )

    if full_message[CHECKSUM_INDEX] != eq_model.expected_checksum:
        raise RuntimeError(
            f"Checksum inesperado para {eq_model.name}: "
            f"0x{full_message[CHECKSUM_INDEX]:02X}. "
            f"Esperado: 0x{eq_model.expected_checksum:02X}."
        )

    return mido.Message(
        "sysex",
        data=full_message[1:-1],
    )


def build_remove_slot_12_message() -> mido.Message:
    full_message = list(
        bytes.fromhex(
            REMOVE_TEMPLATE_HEX
        )
    )

    if len(full_message) != 60:
        raise RuntimeError(
            "O pacote-base de remoção não possui 60 bytes."
        )

    slot_high, slot_low = split_into_nibbles(
        PROTOCOL_SLOT
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

    if full_message[CHECKSUM_INDEX] != 0x4F:
        raise RuntimeError(
            "Checksum inesperado para remoção: "
            f"0x{full_message[CHECKSUM_INDEX]:02X}."
        )

    return mido.Message(
        "sysex",
        data=full_message[1:-1],
    )


def print_packet(
    label: str,
    message: mido.Message,
) -> None:
    packet = bytes(
        message.bin()
    )

    print(
        f"\n{label}"
    )
    print(
        f"Tamanho: {len(packet)} bytes"
    )
    print(
        f"Flag: 0x{packet[EFFECT_INSTANCE_FLAG_INDEX]:02X}"
    )
    print(
        f"Seletor: 0x{packet[SECONDARY_SELECTOR_INDEX]:02X}"
    )
    print(
        f"Checksum: 0x{packet[CHECKSUM_INDEX]:02X}"
    )
    print(
        packet.hex()
    )


def send_message(
    output,
    label: str,
    message: mido.Message,
) -> None:
    print_packet(
        label,
        message,
    )

    output.send(
        message
    )

    print(
        "Comando enviado. Observe a pedaleira e o aplicativo."
    )


def main() -> None:
    try:
        print(
            "Teste de criação EQ no slot interno 12"
        )
        print(
            "1. Adicionar GUITAR EQ 1"
        )
        print(
            "2. Remover o slot 12"
        )
        print(
            "3. Adicionar CALIF EQ"
        )
        print(
            "P. Imprimir os pacotes sem enviar"
        )

        option = input(
            "\nEscolha: "
        ).strip().lower()

        if option == "p":
            print_packet(
                "GUITAR EQ 1",
                build_add_eq_message(
                    GUITAR_EQ_1
                ),
            )
            print_packet(
                "CALIF EQ",
                build_add_eq_message(
                    CALIF_EQ
                ),
            )
            print_packet(
                "Remoção",
                build_remove_slot_12_message(),
            )
            return

        with mido.open_output(
            OUTPUT_PORT
        ) as output:
            if option == "1":
                send_message(
                    output,
                    "Adicionar GUITAR EQ 1",
                    build_add_eq_message(
                        GUITAR_EQ_1
                    ),
                )

            elif option == "2":
                send_message(
                    output,
                    "Remover o slot 12",
                    build_remove_slot_12_message(),
                )

            elif option == "3":
                send_message(
                    output,
                    "Adicionar CALIF EQ",
                    build_add_eq_message(
                        CALIF_EQ
                    ),
                )

            else:
                raise ValueError(
                    "Escolha 1, 2, 3 ou P."
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