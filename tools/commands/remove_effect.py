"""Remove um slot existente da cadeia visual."""

from __future__ import annotations

import mido

from tools.commands.effect_chain import (
    CHECKSUM_INDEX,
    build_remove_effect_message,
    full_message_bytes,
)


OUTPUT_PORT = "Matribox II Pro Subdevice 1"


def main() -> None:
    try:
        print(
            "Remover efeito da cadeia visual"
        )
        print(
            "ATENÇÃO: escolha somente um slot que esteja presente."
        )
        print()

        slot_number = int(
            input(
                "Slot interno existente, de 1 a 12: "
            ).strip()
        )

        confirmation = input(
            f"\nDigite REMOVER para excluir o slot "
            f"{slot_number} da cadeia: "
        ).strip()

        if confirmation != "REMOVER":
            print(
                "Operação cancelada."
            )
            return

        message = build_remove_effect_message(
            slot_number=slot_number
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
            f"checksum: 0x{packet[CHECKSUM_INDEX]:02X}"
        )

        with mido.open_output(
            OUTPUT_PORT
        ) as output:
            output.send(
                message
            )

        print(
            "\nEfeito removido da cadeia visual."
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
