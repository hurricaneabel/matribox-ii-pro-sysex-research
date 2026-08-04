"""Altera um efeito existente usando o comando apropriado.

- mesma classe: comando 0x16;
- classe diferente: comando 0x17 com origem e destino iguais.
"""

from __future__ import annotations

import mido

from tools.commands.effect_catalog import (
    EFFECT_CLASSES,
    find_effect_class,
    find_effect_model,
)
from tools.commands.effect_chain import (
    CHECKSUM_INDEX as REPLACE_CHECKSUM_INDEX,
    build_replace_effect_message,
)
from tools.commands.effect_model import (
    CHECKSUM_INDEX as MODEL_CHECKSUM_INDEX,
    build_set_effect_model_message,
)


OUTPUT_PORT = "Matribox II Pro Subdevice 1"


def print_classes() -> None:
    """Exibe as classes atualmente mapeadas."""
    for effect_class in EFFECT_CLASSES:
        print(
            f"{effect_class.menu_number}. "
            f"{effect_class.name} "
            f"(0x{effect_class.class_id:02X})"
        )


def print_models(effect_class) -> None:
    """Exibe os modelos da classe escolhida."""
    for model in effect_class.models:
        print(
            f"{model.menu_number:2}. "
            f"{model.name} "
            f"(modelo 0x{model.model_id:02X}, "
            f"seletor 0x{model.secondary_selector:02X})"
        )


def main() -> None:
    """Solicita estado atual e destino para escolher 0x16 ou 0x17."""
    try:
        print(
            "Alterar efeito existente"
        )
        print()

        slot_number = int(
            input(
                "Slot interno existente, de 1 a 12: "
            ).strip()
        )

        print(
            "\nClasse atual:"
        )
        print_classes()

        current_class_value = input(
            "\nEscolha a classe atual: "
        )
        current_class = find_effect_class(
            current_class_value
        )

        print(
            "\nNova classe:"
        )
        print_classes()

        target_class_value = input(
            "\nEscolha a nova classe: "
        )
        target_class = find_effect_class(
            target_class_value
        )

        print(
            f"\nModelos {target_class.name}:"
        )
        print_models(
            target_class
        )

        model_value = input(
            "\nEscolha o novo modelo: "
        )
        target_model = find_effect_model(
            target_class,
            model_value,
        )

        confirmation = input(
            "\nDigite ALTERAR para confirmar: "
        ).strip()

        if confirmation != "ALTERAR":
            print(
                "Operação cancelada."
            )
            return

        if current_class.class_id == target_class.class_id:
            message = build_set_effect_model_message(
                slot_number=slot_number,
                class_id=target_class.class_id,
                model_id=target_model.model_id,
                secondary_selector=target_model.secondary_selector,
            )
            command_name = "0x16 — troca dentro da mesma classe"
            checksum_index = MODEL_CHECKSUM_INDEX

        else:
            message = build_replace_effect_message(
                slot_number=slot_number,
                class_id=target_class.class_id,
                model_id=target_model.model_id,
                secondary_selector=target_model.secondary_selector,
            )
            command_name = "0x17 — substituição entre classes"
            checksum_index = REPLACE_CHECKSUM_INDEX

        packet = bytes(
            message.bin()
        )

        print(
            "\nComando:"
        )
        print(
            f"slot: {slot_number}"
        )
        print(
            f"operação: {command_name}"
        )
        print(
            f"destino: {target_class.name} / {target_model.name}"
        )
        print(
            "seletor secundário: "
            f"0x{target_model.secondary_selector:02X}"
        )
        print(
            f"checksum: 0x{packet[checksum_index]:02X}"
        )

        with mido.open_output(
            OUTPUT_PORT
        ) as output:
            output.send(
                message
            )

        print(
            "\nEfeito alterado."
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
