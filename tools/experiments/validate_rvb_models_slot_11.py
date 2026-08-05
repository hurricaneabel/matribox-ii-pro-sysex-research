"""Valida os 12 modelos confirmados da subclasse RVB no slot 11.

Mapeamento extraído de captura USB/Wireshark:
- classe RVB: 0x0A
- flag estrutural: 0x00
- seletor secundário: 0x0C em todos os modelos

A sequência automática considera o slot 11 inicialmente em STUDIO,
percorre os outros 11 modelos e termina novamente em STUDIO.
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

RVB_CLASS_ID = 0x0A
RVB_INSTANCE_FLAG = 0x00
RVB_SECONDARY_SELECTOR = 0x0C
STEP_DELAY_SECONDS = 2.0

# Pacote 0x16 capturado na volta final para STUDIO.
STUDIO_TEMPLATE_HEX = (
    "F021254D5000005012160000000001000000000100000E"
    "000000000000010B0002000000040001000A000A000B"
    "00000000000C010100000000F7"
)


@dataclass(frozen=True)
class RvbModel:
    menu_number: int
    name: str
    model_id: int
    expected_checksum: int


RVB_MODELS = (
    RvbModel(1, "STUDIO", 0x0B, 0x50),
    RvbModel(2, "CLUB", 0x0C, 0x51),
    RvbModel(3, "ROOM", 0x00, 0x45),
    RvbModel(4, "HALL", 0x01, 0x46),
    RvbModel(5, "CHURCH", 0x02, 0x47),
    RvbModel(6, "PLATE", 0x03, 0x48),
    RvbModel(7, "SPRING", 0x04, 0x49),
    RvbModel(8, "SKY", 0x06, 0x4B),
    RvbModel(9, "SEA", 0x07, 0x4C),
    RvbModel(10, "MOD REVERB", 0x08, 0x4D),
    RvbModel(11, "SHIMMER", 0x09, 0x4E),
    RvbModel(12, "HAZE", 0x15, 0x4B),
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


def build_rvb_message(rvb_model: RvbModel) -> mido.Message:
    full_message = list(bytes.fromhex(STUDIO_TEMPLATE_HEX))

    if len(full_message) != EXPECTED_MESSAGE_LENGTH:
        raise RuntimeError("Tamanho inesperado do pacote-base.")

    if full_message[9] != EXPECTED_COMMAND_TYPE:
        raise RuntimeError("Tipo de comando inesperado.")

    slot_high, slot_low = split_into_nibbles(PROTOCOL_SLOT)
    class_high, class_low = split_into_nibbles(RVB_CLASS_ID)
    model_high, model_low = split_into_nibbles(rvb_model.model_id)

    full_message[SLOT_HIGH_INDEX] = slot_high
    full_message[SLOT_LOW_INDEX] = slot_low
    full_message[CLASS_HIGH_INDEX] = class_high
    full_message[CLASS_LOW_INDEX] = class_low
    full_message[MODEL_HIGH_INDEX] = model_high
    full_message[MODEL_LOW_INDEX] = model_low
    full_message[EFFECT_INSTANCE_FLAG_INDEX] = RVB_INSTANCE_FLAG
    full_message[SECONDARY_SELECTOR_INDEX] = RVB_SECONDARY_SELECTOR

    full_message[CHECKSUM_INDEX] = calculate_checksum(full_message)

    if full_message[CHECKSUM_INDEX] != rvb_model.expected_checksum:
        raise RuntimeError(
            f"Checksum de {rvb_model.name} inesperado: "
            f"0x{full_message[CHECKSUM_INDEX]:02X}. "
            f"Esperado: 0x{rvb_model.expected_checksum:02X}."
        )

    return mido.Message(
        "sysex",
        data=full_message[1:-1],
    )


def validate_all_packets() -> None:
    for rvb_model in RVB_MODELS:
        packet = bytes(build_rvb_message(rvb_model).bin())

        if packet[SLOT_HIGH_INDEX:SLOT_LOW_INDEX + 1] != bytes(
            (0x00, 0x0A)
        ):
            raise RuntimeError(f"Slot incorreto em {rvb_model.name}.")

        if packet[CLASS_HIGH_INDEX:CLASS_LOW_INDEX + 1] != bytes(
            (0x00, 0x0A)
        ):
            raise RuntimeError(f"Classe incorreta em {rvb_model.name}.")

        if packet[EFFECT_INSTANCE_FLAG_INDEX] != RVB_INSTANCE_FLAG:
            raise RuntimeError(f"Flag incorreta em {rvb_model.name}.")

        if packet[SECONDARY_SELECTOR_INDEX] != RVB_SECONDARY_SELECTOR:
            raise RuntimeError(f"Seletor incorreto em {rvb_model.name}.")

    print(
        "\nValidação local concluída: "
        "12 pacotes reproduzem os campos e checksums capturados."
    )


def print_models() -> None:
    print("RVB — 12 modelos confirmados:")

    for rvb_model in RVB_MODELS:
        print(
            f"{rvb_model.menu_number:>2}. "
            f"{rvb_model.name:<10} "
            f"modelo 0x{rvb_model.model_id:02X} "
            f"seletor 0x{RVB_SECONDARY_SELECTOR:02X} "
            f"checksum 0x{rvb_model.expected_checksum:02X}"
        )


def send_rvb_model(output, rvb_model: RvbModel) -> None:
    message = build_rvb_message(rvb_model)
    packet = bytes(message.bin())

    print(f"\n{rvb_model.name}")
    print(f"modelo: 0x{rvb_model.model_id:02X}")
    print(f"flag: 0x{packet[EFFECT_INSTANCE_FLAG_INDEX]:02X}")
    print(
        "seletor secundário: "
        f"0x{packet[SECONDARY_SELECTOR_INDEX]:02X}"
    )
    print(f"checksum: 0x{packet[CHECKSUM_INDEX]:02X}")

    output.send(message)


def run_all_models(output) -> None:
    print("\nIniciando o teste automático dos 12 RVBs.")

    for rvb_model in RVB_MODELS[1:]:
        send_rvb_model(output, rvb_model)
        time.sleep(STEP_DELAY_SECONDS)

    send_rvb_model(output, RVB_MODELS[0])

    print("\nSequência concluída. Estado final: STUDIO.")


def main() -> None:
    try:
        print("Validação RVB — slot 11")
        print("Comece com o slot 11 em STUDIO.")
        print()

        print_models()

        print(
            "\nDigite um número de 1 a 12 "
            "para testar individualmente."
        )
        print("Digite A para percorrer todos automaticamente.")
        print(
            "Digite V para validar os pacotes "
            "sem enviar à pedaleira."
        )

        option = input("\nEscolha: ").strip().lower()

        if option == "v":
            validate_all_packets()
            return

        with mido.open_output(OUTPUT_PORT) as output:
            if option == "a":
                run_all_models(output)
                return

            menu_number = int(option)

            rvb_model = next(
                (
                    item
                    for item in RVB_MODELS
                    if item.menu_number == menu_number
                ),
                None,
            )

            if rvb_model is None:
                raise ValueError("Escolha um número entre 1 e 12.")

            send_rvb_model(output, rvb_model)
            print("\nComando enviado.")

    except (OSError, RuntimeError, ValueError) as error:
        print(f"\nErro: {error}")

    except KeyboardInterrupt:
        print("\nTeste interrompido.")


if __name__ == "__main__":
    main()
