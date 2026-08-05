"""Valida fisicamente os 17 modelos DLY confirmados no slot 11."""

from __future__ import annotations

import time

import mido

from tools.commands.effect_catalog import (
    DLY_CLASS_ID,
    DLY_MODELS,
)
from tools.commands.effect_model import (
    CHECKSUM_INDEX,
    EFFECT_INSTANCE_FLAG_INDEX,
    SECONDARY_SELECTOR_INDEX,
    build_set_effect_model_message,
)


OUTPUT_PORT = "Matribox II Pro Subdevice 1"
SLOT_NUMBER = 11
STEP_DELAY_SECONDS = 2.0

EXPECTED_CHECKSUMS = (
    0x44, 0x43, 0x45, 0x4E, 0x51, 0x47,
    0x48, 0x49, 0x4C, 0x4F, 0x50, 0x46,
    0x48, 0x4B, 0x4D, 0x46, 0x51,
)


def build_message(model_index: int) -> mido.Message:
    model = DLY_MODELS[model_index]
    message = build_set_effect_model_message(
        slot_number=SLOT_NUMBER,
        class_id=DLY_CLASS_ID,
        model_id=model.model_id,
        secondary_selector=model.secondary_selector,
    )
    packet = bytes(message.bin())

    if packet[EFFECT_INSTANCE_FLAG_INDEX] != 0x00:
        raise RuntimeError(f"Flag inesperada em {model.name}.")

    if packet[SECONDARY_SELECTOR_INDEX] != 0x0B:
        raise RuntimeError(f"Seletor inesperado em {model.name}.")

    expected_checksum = EXPECTED_CHECKSUMS[model_index]
    if packet[CHECKSUM_INDEX] != expected_checksum:
        raise RuntimeError(
            f"Checksum inesperado em {model.name}: "
            f"0x{packet[CHECKSUM_INDEX]:02X}; "
            f"esperado 0x{expected_checksum:02X}."
        )

    return message


def print_models() -> None:
    print("DLY — 17 modelos confirmados:")
    for index, (model, checksum) in enumerate(
        zip(DLY_MODELS, EXPECTED_CHECKSUMS, strict=True),
        start=1,
    ):
        print(
            f"{index:>2}. {model.name:<12} "
            f"modelo 0x{model.model_id:02X} "
            f"seletor 0x{model.secondary_selector:02X} "
            f"checksum 0x{checksum:02X}"
        )


def validate_locally() -> None:
    for index in range(len(DLY_MODELS)):
        build_message(index)
    print(
        "\nValidação local concluída: "
        "17 pacotes reproduzem os campos e checksums capturados."
    )


def send_model(output, model_index: int) -> None:
    model = DLY_MODELS[model_index]
    message = build_message(model_index)
    packet = bytes(message.bin())

    print(f"\n{model.name}")
    print(f"modelo: 0x{model.model_id:02X}")
    print(f"flag: 0x{packet[EFFECT_INSTANCE_FLAG_INDEX]:02X}")
    print(f"seletor secundário: 0x{packet[SECONDARY_SELECTOR_INDEX]:02X}")
    print(f"checksum: 0x{packet[CHECKSUM_INDEX]:02X}")
    output.send(message)


def run_all_models(output) -> None:
    print("\nIniciando o teste automático dos 17 DLYs.")

    for model_index in range(1, len(DLY_MODELS)):
        send_model(output, model_index)
        time.sleep(STEP_DELAY_SECONDS)

    send_model(output, 0)
    print("\nSequência concluída. Estado final: WARM.")


def main() -> None:
    try:
        print("Validação DLY — slot 11")
        print("Comece com o slot 11 em WARM.\n")
        print_models()
        print("\nDigite um número de 1 a 17 para testar individualmente.")
        print("Digite A para percorrer todos automaticamente.")
        print("Digite V para validar sem enviar à pedaleira.")

        option = input("\nEscolha: ").strip().lower()

        if option == "v":
            validate_locally()
            return

        with mido.open_output(OUTPUT_PORT) as output:
            if option == "a":
                run_all_models(output)
                return

            menu_number = int(option)
            if not 1 <= menu_number <= len(DLY_MODELS):
                raise ValueError("Escolha um número entre 1 e 17.")

            send_model(output, menu_number - 1)
            print("\nComando enviado.")

    except (OSError, RuntimeError, ValueError) as error:
        print(f"\nErro: {error}")
    except KeyboardInterrupt:
        print("\nTeste interrompido.")


if __name__ == "__main__":
    main()
