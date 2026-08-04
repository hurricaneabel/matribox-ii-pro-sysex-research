"""Adiciona um modelo FREQ a um slot vazio da cadeia visual."""

from __future__ import annotations

import mido

from tools.commands.effect_chain import (
    CHECKSUM_INDEX,
    FREQ_MODELS,
    build_add_effect_message,
    find_freq_model,
    full_message_bytes,
)


OUTPUT_PORT = "Matribox II Pro Subdevice 1"


def main() -> None:
    try:
        print(
            "Adicionar efeito FREQ à cadeia visual"
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

        print(
            "\nModelos FREQ:"
        )

        for model in FREQ_MODELS:
            print(
                f"{model.menu_number}. "
                f"{model.name} "
                f"(0x{model.model_id:02X})"
            )

        model_value = input(
            "\nEscolha pelo número, nome ou ID: "
        )
        model = find_freq_model(
            model_value
        )

        confirmation = input(
            "\nO efeito será criado LIGADO. "
            "Digite ADICIONAR para confirmar: "
        ).strip()

        if confirmation != "ADICIONAR":
            print(
                "Operação cancelada."
            )
            return

        message = build_add_effect_message(
            slot_number=slot_number,
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
            f"modelo: {model.name} "
            f"(0x{model.model_id:02X})"
        )
        print(
            "estado inicial: ligado"
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
