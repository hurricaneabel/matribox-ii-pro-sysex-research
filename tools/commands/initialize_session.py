"""Testa a mensagem de inicialização da sessão da Matribox II Pro."""

from __future__ import annotations

import time

import mido


OUTPUT_PORT = "Matribox II Pro Subdevice 1"

HANDSHAKE_REPETITIONS = 4
HANDSHAKE_INTERVAL_SECONDS = 0.2


# Primeira mensagem enviada pelo editor oficial durante a inicialização.
SESSION_HANDSHAKE_HEX = (
    "f021257e47502d321112000000f7"
)


def create_sysex_message(
    hex_message: str,
) -> mido.Message:
    """Converte uma mensagem hexadecimal completa em SysEx do Mido."""
    full_message = bytes.fromhex(
        hex_message
    )

    if full_message[0] != 0xF0:
        raise ValueError(
            "A mensagem não começa com F0."
        )

    if full_message[-1] != 0xF7:
        raise ValueError(
            "A mensagem não termina com F7."
        )

    # O Mido adiciona F0 e F7 automaticamente.
    return mido.Message(
        "sysex",
        data=full_message[1:-1],
    )


def main() -> None:
    """Envia quatro vezes a inicialização observada no editor oficial."""
    handshake_message = create_sysex_message(
        SESSION_HANDSHAKE_HEX
    )

    try:
        with mido.open_output(
            OUTPUT_PORT
        ) as output_port:
            for attempt in range(
                1,
                HANDSHAKE_REPETITIONS + 1,
            ):
                output_port.send(
                    handshake_message
                )

                print(
                    "Inicialização enviada:",
                    f"{attempt}/{HANDSHAKE_REPETITIONS}",
                )

                if attempt < HANDSHAKE_REPETITIONS:
                    time.sleep(
                        HANDSHAKE_INTERVAL_SECONDS
                    )

        print(
            "\nSequência de inicialização concluída."
        )

    except OSError as error:
        print(
            "Erro ao abrir a porta MIDI:",
            error,
        )


if __name__ == "__main__":
    main()