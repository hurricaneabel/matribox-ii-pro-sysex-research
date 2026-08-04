"""Adiciona um efeito FREQ ou DRV a um slot vazio."""

from __future__ import annotations

import mido

from tools.commands.effect_catalog import (
    EFFECT_CLASSES,
    find_effect_class,
    find_effect_model,
)
from tools.commands.effect_chain import (
    CHECKSUM_INDEX,
    build_add_effect_message,
    full_message_bytes,
)


OUTPUT_PORT = "Matribox II Pro Subdevice 1"


def print_classes() -> None:
    """Exibe as classes atualmente mapeadas."""
    print(
        "Classes:"
    )

    for effect_class in EFFECT_CLASSES:
        print(
            f"{effect_class.menu_number}. "
            f"{effect_class.name} "
            f"(0x{effect_class.class_id:02X})"
        )


def print_models(effect_class) -> None:
    """Exibe os modelos da classe escolhida."""
    print(
        f"\nModelos {effect_class.name}:"
    )

    for model in effect_class.models:
        print(
            f"{model.menu_number:2}. "
            f"{model.name} "
            f"(0x{model.model_id:02X})"
        )


def main() -> None:
    """Solicita slot, classe e modelo e envia a criação."""
    try:
        print(
            "Adicionar efeito à cadeia visual"
        )
        print(
            "ATENÇÃO: escolha somente um slot que esteja ausente."
        )
        print()

        slot_number = int(
            input(
                "Slot interno vazio, de 1 a 12: "
            ).strip()
        )

        print_classes()

        class_value = input(
            "\nEscolha a classe pelo número, nome ou ID: "
        )
        effect_class = find_effect_class(
            class_value
        )

        print_models(
            effect_class
        )

        model_value = input(
            "\nEscolha o modelo pelo número, nome ou ID: "
        )
        model = find_effect_model(
            effect_class,
            model_value,
        )

        confirmation = input(
            "\nDigite ADICIONAR para confirmar: "
        ).strip()

        if confirmation != "ADICIONAR":
            print(
                "Operação cancelada."
            )
            return

        message = build_add_effect_message(
            slot_number=slot_number,
            class_id=effect_class.class_id,
            model_id=model.model_id,
        )
        packet = full_message_bytes(
            message
        )

        print(
            "\nComando:"
        )
        print(
            f"slot: {slot_number}"
        )
        print(
            f"classe: {effect_class.name} "
            f"(0x{effect_class.class_id:02X})"
        )
        print(
            f"modelo: {model.name} "
            f"(0x{model.model_id:02X})"
        )
        print(
            f"checksum: 0x{packet[CHECKSUM_INDEX]:02X}"
        )

        with mido.open_output(
            OUTPUT_PORT
        ) as output:
            output.send(
                message
            )

        print(
            "\nEfeito adicionado à cadeia visual."
        )

    except (
        OSError,
        RuntimeError,
        ValueError,
    ) as error:
        print(
            f"\nErro: {error}"
        )


if __name__ == "__main__":
    main()
