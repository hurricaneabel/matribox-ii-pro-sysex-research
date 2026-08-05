"""Valida os quatro blocos especiais no slot interno 11.

Blocos confirmados por captura USB/Wireshark:

- FX LOOP: classe 0x0C, modelo 0x00
- SND:     classe 0x0D, modelo 0x01
- RTN:     classe 0x0E, modelo 0x02
- VOL:     classe 0x0F, modelo 0x03

Todos usam:

- comando estrutural 0x17;
- flag estrutural 0x00;
- seletor secundário 0x06.
"""

from __future__ import annotations

from dataclasses import dataclass
import time

import mido

from tools.commands.effect_chain import (
    CHECKSUM_INDEX,
    EFFECT_INSTANCE_FLAG_INDEX,
    SECONDARY_SELECTOR_INDEX,
    build_replace_effect_message,
    full_message_bytes,
)


OUTPUT_PORT = "Matribox II Pro Subdevice 1"

SLOT_NUMBER = 11
STEP_DELAY_SECONDS = 2.0

CLASS_HIGH_INDEX = 43
CLASS_LOW_INDEX = 44
MODEL_HIGH_INDEX = 45
MODEL_LOW_INDEX = 46

SPECIAL_FLAG = 0x00
SPECIAL_SELECTOR = 0x06


@dataclass(frozen=True)
class SpecialBlock:
    menu_number: int
    name: str
    class_id: int
    model_id: int
    expected_checksum: int


SPECIAL_BLOCKS = (
    SpecialBlock(1, "FX LOOP", 0x0C, 0x00, 0x4C),
    SpecialBlock(2, "SND", 0x0D, 0x01, 0x4E),
    SpecialBlock(3, "RTN", 0x0E, 0x02, 0x50),
    SpecialBlock(4, "VOL", 0x0F, 0x03, 0x52),
)


def split_into_nibbles(value: int) -> bytes:
    if not 0 <= value <= 0xFF:
        raise ValueError("O valor deve estar entre 0x00 e 0xFF.")

    return bytes(((value >> 4) & 0x0F, value & 0x0F))


def build_special_block_message(special_block: SpecialBlock) -> mido.Message:
    message = build_replace_effect_message(
        slot_number=SLOT_NUMBER,
        class_id=special_block.class_id,
        model_id=special_block.model_id,
        secondary_selector=SPECIAL_SELECTOR,
    )
    packet = full_message_bytes(message)

    if packet[CHECKSUM_INDEX] != special_block.expected_checksum:
        raise RuntimeError(
            f"Checksum inesperado em {special_block.name}: "
            f"calculado 0x{packet[CHECKSUM_INDEX]:02X}, "
            f"esperado 0x{special_block.expected_checksum:02X}."
        )

    return message


def validate_block(special_block: SpecialBlock) -> None:
    packet = full_message_bytes(build_special_block_message(special_block))

    if packet[CLASS_HIGH_INDEX:CLASS_LOW_INDEX + 1] != split_into_nibbles(
        special_block.class_id
    ):
        raise RuntimeError(f"Classe incorreta em {special_block.name}.")

    if packet[MODEL_HIGH_INDEX:MODEL_LOW_INDEX + 1] != split_into_nibbles(
        special_block.model_id
    ):
        raise RuntimeError(f"Modelo incorreto em {special_block.name}.")

    if packet[EFFECT_INSTANCE_FLAG_INDEX] != SPECIAL_FLAG:
        raise RuntimeError(f"Flag incorreta em {special_block.name}.")

    if packet[SECONDARY_SELECTOR_INDEX] != SPECIAL_SELECTOR:
        raise RuntimeError(f"Seletor incorreto em {special_block.name}.")


def validate_all_packets() -> None:
    for special_block in SPECIAL_BLOCKS:
        validate_block(special_block)

    print(
        "\nValidação local concluída: "
        "os quatro pacotes reproduzem os campos e checksums capturados."
    )


def print_blocks() -> None:
    print("Blocos especiais confirmados:")

    for special_block in SPECIAL_BLOCKS:
        print(
            f"{special_block.menu_number}. "
            f"{special_block.name:<7} "
            f"classe 0x{special_block.class_id:02X} "
            f"modelo 0x{special_block.model_id:02X} "
            f"seletor 0x{SPECIAL_SELECTOR:02X} "
            f"checksum 0x{special_block.expected_checksum:02X}"
        )


def send_block(output: mido.ports.BaseOutput, special_block: SpecialBlock) -> None:
    message = build_special_block_message(special_block)
    packet = full_message_bytes(message)

    print(f"\n{special_block.name}")
    print(f"classe: 0x{special_block.class_id:02X}")
    print(f"modelo: 0x{special_block.model_id:02X}")
    print(f"flag: 0x{packet[EFFECT_INSTANCE_FLAG_INDEX]:02X}")
    print(f"seletor secundário: 0x{packet[SECONDARY_SELECTOR_INDEX]:02X}")
    print(f"checksum: 0x{packet[CHECKSUM_INDEX]:02X}")

    output.send(message)


def run_all_blocks(output: mido.ports.BaseOutput) -> None:
    print("\nIniciando o teste automático dos quatro blocos especiais.")

    for special_block in SPECIAL_BLOCKS:
        send_block(output, special_block)
        time.sleep(STEP_DELAY_SECONDS)

    send_block(output, SPECIAL_BLOCKS[2])
    print("\nSequência concluída. Estado final: RTN.")


def main() -> None:
    try:
        print("Validação de FX LOOP, SND, RTN e VOL — slot 11")
        print("O slot 11 pode começar em RTN.")
        print()
        print_blocks()
        print("\nDigite um número de 1 a 4 para testar individualmente.")
        print("Digite A para percorrer todos automaticamente.")
        print("Digite V para validar os pacotes sem enviar à pedaleira.")

        option = input("\nEscolha: ").strip().lower()

        if option == "v":
            validate_all_packets()
            return

        with mido.open_output(OUTPUT_PORT) as output:
            if option == "a":
                run_all_blocks(output)
                return

            menu_number = int(option)
            special_block = next(
                (item for item in SPECIAL_BLOCKS if item.menu_number == menu_number),
                None,
            )

            if special_block is None:
                raise ValueError("Escolha um número entre 1 e 4.")

            send_block(output, special_block)
            print("\nComando enviado.")

    except (OSError, RuntimeError, ValueError) as error:
        print(f"\nErro: {error}")
    except KeyboardInterrupt:
        print("\nTeste interrompido.")


if __name__ == "__main__":
    main()
