"""Valida as dez posições confirmadas da classe CLONE no slot 11.

O nome real de cada posição é definido pelo arquivo NAM importado pelo
usuário. Enquanto o protocolo de importação e leitura dos nomes não for
documentado, elas são apresentadas como CLONE 1 até CLONE 10.

Mapeamento confirmado por captura USB/Wireshark e teste físico:
- classe CLONE: 0x0B
- modelos/posições: 0x00 até 0x09
- flag estrutural: 0x00
- seletor secundário: 0x0F
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

CLONE_CLASS_ID = 0x0B
CLONE_INSTANCE_FLAG = 0x00
CLONE_SECONDARY_SELECTOR = 0x0F
STEP_DELAY_SECONDS = 2.0

# Pacote capturado na volta final para CLONE 1.
CLONE_1_TEMPLATE_HEX = (
    "F021254D5000004912160000000001000000000100000E"
    "000000000000010B0002000000040001000A000B0000"
    "00000000000F010100000000F7"
)


@dataclass(frozen=True)
class CloneSlot:
    menu_number: int
    name: str
    model_id: int
    expected_checksum: int


CLONE_SLOTS = tuple(
    CloneSlot(
        menu_number=menu_number,
        name=f"CLONE {menu_number}",
        model_id=model_id,
        expected_checksum=0x49 + model_id,
    )
    for menu_number, model_id in enumerate(range(0x00, 0x0A), start=1)
)


def split_into_nibbles(value: int) -> tuple[int, int]:
    if not 0 <= value <= 0xFF:
        raise ValueError("O valor deve estar entre 0x00 e 0xFF.")

    return (
        (value >> 4) & 0x0F,
        value & 0x0F,
    )


def calculate_checksum(message: list[int]) -> int:
    if len(message) != EXPECTED_MESSAGE_LENGTH:
        raise ValueError(
            f"A mensagem deve possuir {EXPECTED_MESSAGE_LENGTH} bytes."
        )

    payload_start = 10
    payload_end = payload_start + (message[9] * 2)

    return sum(message[payload_start:payload_end]) & 0x7F


def build_clone_message(clone_slot: CloneSlot) -> mido.Message:
    full_message = list(bytes.fromhex(CLONE_1_TEMPLATE_HEX))

    if len(full_message) != EXPECTED_MESSAGE_LENGTH:
        raise RuntimeError("O pacote-base CLONE não possui 58 bytes.")

    if full_message[9] != EXPECTED_COMMAND_TYPE:
        raise RuntimeError("O pacote-base não utiliza o comando 0x16.")

    slot_high, slot_low = split_into_nibbles(PROTOCOL_SLOT)
    class_high, class_low = split_into_nibbles(CLONE_CLASS_ID)
    model_high, model_low = split_into_nibbles(clone_slot.model_id)

    full_message[SLOT_HIGH_INDEX] = slot_high
    full_message[SLOT_LOW_INDEX] = slot_low
    full_message[CLASS_HIGH_INDEX] = class_high
    full_message[CLASS_LOW_INDEX] = class_low
    full_message[MODEL_HIGH_INDEX] = model_high
    full_message[MODEL_LOW_INDEX] = model_low
    full_message[EFFECT_INSTANCE_FLAG_INDEX] = CLONE_INSTANCE_FLAG
    full_message[SECONDARY_SELECTOR_INDEX] = CLONE_SECONDARY_SELECTOR
    full_message[CHECKSUM_INDEX] = calculate_checksum(full_message)

    if full_message[CHECKSUM_INDEX] != clone_slot.expected_checksum:
        raise RuntimeError(
            f"Checksum inesperado em {clone_slot.name}: "
            f"calculado 0x{full_message[CHECKSUM_INDEX]:02X}, "
            f"esperado 0x{clone_slot.expected_checksum:02X}."
        )

    return mido.Message(
        "sysex",
        data=full_message[1:-1],
    )


def validate_all_packets() -> None:
    for clone_slot in CLONE_SLOTS:
        packet = bytes(build_clone_message(clone_slot).bin())

        if packet[SLOT_HIGH_INDEX:SLOT_LOW_INDEX + 1] != bytes((0x00, 0x0A)):
            raise RuntimeError(f"Slot incorreto em {clone_slot.name}.")

        if packet[CLASS_HIGH_INDEX:CLASS_LOW_INDEX + 1] != bytes((0x00, 0x0B)):
            raise RuntimeError(f"Classe incorreta em {clone_slot.name}.")

        if packet[EFFECT_INSTANCE_FLAG_INDEX] != CLONE_INSTANCE_FLAG:
            raise RuntimeError(f"Flag incorreta em {clone_slot.name}.")

        if packet[SECONDARY_SELECTOR_INDEX] != CLONE_SECONDARY_SELECTOR:
            raise RuntimeError(f"Seletor incorreto em {clone_slot.name}.")

    print(
        "\nValidação local concluída: "
        "as 10 posições reproduzem os campos e checksums da captura."
    )


def print_slots() -> None:
    print("CLONE — 10 posições confirmadas:")

    for clone_slot in CLONE_SLOTS:
        print(
            f"{clone_slot.menu_number:>2}. "
            f"{clone_slot.name:<8} "
            f"modelo 0x{clone_slot.model_id:02X} "
            f"seletor 0x{CLONE_SECONDARY_SELECTOR:02X} "
            f"checksum 0x{clone_slot.expected_checksum:02X}"
        )


def send_clone_slot(output, clone_slot: CloneSlot) -> None:
    message = build_clone_message(clone_slot)
    packet = bytes(message.bin())

    print(f"\n{clone_slot.name}")
    print(f"modelo: 0x{clone_slot.model_id:02X}")
    print(f"flag: 0x{packet[EFFECT_INSTANCE_FLAG_INDEX]:02X}")
    print(
        "seletor secundário: "
        f"0x{packet[SECONDARY_SELECTOR_INDEX]:02X}"
    )
    print(f"checksum: 0x{packet[CHECKSUM_INDEX]:02X}")

    output.send(message)


def run_all_slots(output) -> None:
    print("\nIniciando o teste automático das 10 posições CLONE.")

    for clone_slot in CLONE_SLOTS[1:]:
        send_clone_slot(output, clone_slot)
        time.sleep(STEP_DELAY_SECONDS)

    send_clone_slot(output, CLONE_SLOTS[0])

    print("\nSequência concluída. Estado final: CLONE 1.")


def main() -> None:
    try:
        print("Validação CLONE — slot 11")
        print("Comece com o slot 11 usando a primeira posição CLONE.")
        print()
        print_slots()

        print("\nDigite um número de 1 a 10 para testar individualmente.")
        print("Digite A para percorrer todas automaticamente.")
        print("Digite V para validar os pacotes sem enviar à pedaleira.")

        option = input("\nEscolha: ").strip().lower()

        if option == "v":
            validate_all_packets()
            return

        with mido.open_output(OUTPUT_PORT) as output:
            if option == "a":
                run_all_slots(output)
                return

            menu_number = int(option)
            clone_slot = next(
                (
                    item
                    for item in CLONE_SLOTS
                    if item.menu_number == menu_number
                ),
                None,
            )

            if clone_slot is None:
                raise ValueError("Escolha um número entre 1 e 10.")

            send_clone_slot(output, clone_slot)
            print("\nComando enviado.")

    except (OSError, RuntimeError, ValueError) as error:
        print(f"\nErro: {error}")

    except KeyboardInterrupt:
        print("\nTeste interrompido.")


if __name__ == "__main__":
    main()
