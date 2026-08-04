"""Valida criação e remoção das classes confirmadas no slot 12."""

from __future__ import annotations

import time

import mido

from tools.commands.effect_catalog import EFFECT_CLASSES
from tools.commands.effect_chain import (
    CHECKSUM_INDEX,
    build_add_effect_message,
    build_remove_effect_message,
    full_message_bytes,
)


OUTPUT_PORT = "Matribox II Pro Subdevice 1"
SLOT_NUMBER = 12
STEP_DELAY_SECONDS = 2.5


def send_anchor(output, effect_class) -> None:
    model = effect_class.models[0]
    message = build_add_effect_message(
        slot_number=SLOT_NUMBER,
        class_id=effect_class.class_id,
        model_id=model.model_id,
        secondary_selector=model.secondary_selector,
    )
    packet = full_message_bytes(message)

    print(
        f"\nAdicionar {effect_class.name} / {model.name} "
        f"— checksum 0x{packet[CHECKSUM_INDEX]:02X}"
    )
    output.send(message)


def remove_slot(output) -> None:
    message = build_remove_effect_message(SLOT_NUMBER)
    packet = full_message_bytes(message)
    print(
        f"\nRemover slot 12 "
        f"— checksum 0x{packet[CHECKSUM_INDEX]:02X}"
    )
    output.send(message)


def main() -> None:
    try:
        print("Comece com o slot interno 12 ausente.")
        print("A. Testar todas as classes")

        for effect_class in EFFECT_CLASSES:
            print(
                f"{effect_class.menu_number}. "
                f"{effect_class.name} / "
                f"{effect_class.models[0].name}"
            )

        option = input("\nEscolha: ").strip().casefold()

        with mido.open_output(OUTPUT_PORT) as output:
            if option == "a":
                for effect_class in EFFECT_CLASSES:
                    send_anchor(output, effect_class)
                    time.sleep(STEP_DELAY_SECONDS)
                    remove_slot(output)
                    time.sleep(STEP_DELAY_SECONDS)

                print("\nEstado final: slot 12 ausente.")
                return

            menu_number = int(option)
            effect_class = next(
                (
                    item
                    for item in EFFECT_CLASSES
                    if item.menu_number == menu_number
                ),
                None,
            )

            if effect_class is None:
                raise ValueError("Classe fora do menu.")

            send_anchor(output, effect_class)

    except (OSError, RuntimeError, ValueError) as error:
        print(f"\nErro: {error}")
    except KeyboardInterrupt:
        print("\nTeste interrompido.")


if __name__ == "__main__":
    main()
