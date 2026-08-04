"""Valida substituição das classes confirmadas no slot 11."""

from __future__ import annotations

import time

import mido

from tools.commands.effect_catalog import (
    EFFECT_CLASSES,
    FREQ_CLASS_ID,
)
from tools.commands.effect_chain import (
    CHECKSUM_INDEX,
    DESTINATION_SLOT_HIGH_INDEX,
    DESTINATION_SLOT_LOW_INDEX,
    SOURCE_SLOT_HIGH_INDEX,
    SOURCE_SLOT_LOW_INDEX,
    build_replace_effect_message,
    full_message_bytes,
)


OUTPUT_PORT = "Matribox II Pro Subdevice 1"
SLOT_NUMBER = 11
STEP_DELAY_SECONDS = 2.5


def send_anchor(output, effect_class) -> None:
    model = effect_class.models[0]
    message = build_replace_effect_message(
        slot_number=SLOT_NUMBER,
        class_id=effect_class.class_id,
        model_id=model.model_id,
        secondary_selector=model.secondary_selector,
    )
    packet = full_message_bytes(message)

    source = (
        packet[SOURCE_SLOT_HIGH_INDEX],
        packet[SOURCE_SLOT_LOW_INDEX],
    )
    destination = (
        packet[DESTINATION_SLOT_HIGH_INDEX],
        packet[DESTINATION_SLOT_LOW_INDEX],
    )

    if source != destination:
        raise RuntimeError(
            "Origem e destino precisam ser iguais."
        )

    print(
        f"\nSubstituir por {effect_class.name} / "
        f"{model.name} — checksum "
        f"0x{packet[CHECKSUM_INDEX]:02X}"
    )
    output.send(message)


def main() -> None:
    try:
        print("O slot interno 11 precisa existir.")
        print("A. Testar todas as classes e restaurar FREQ")

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

                freq_class = next(
                    item
                    for item in EFFECT_CLASSES
                    if item.class_id == FREQ_CLASS_ID
                )
                send_anchor(output, freq_class)
                print("\nEstado final: FREQ / Filter.")
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
