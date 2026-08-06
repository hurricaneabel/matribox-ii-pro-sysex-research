"""Move um efeito e lê a ordem visual devolvida pela Matribox.

O comando inicializa a sessão antes do movimento. Isso é necessário para que
a pedaleira envie a resposta estrutural completa, além do evento curto de
alteração do preset.
"""

from __future__ import annotations

import time

import mido

from tools.commands.chain_order import (
    ChainOrderProtocolError,
    ChainOrderState,
    parse_chain_order_response,
)
from tools.commands.move_effect_position import (
    build_move_message,
)
from tools.commands.preset_state import (
    parse_preset_event,
)
from tools.commands.request_preset_dump import (
    SESSION_STABILIZATION_SECONDS,
    clear_pending_messages,
    send_session_handshake,
)


INPUT_PORT = "Matribox II Pro Subdevice 0"
OUTPUT_PORT = "Matribox II Pro Subdevice 1"

RESPONSE_TIMEOUT_SECONDS = 5.0
POLL_INTERVAL_SECONDS = 0.01


def print_chain_order(
    state: ChainOrderState,
) -> None:
    """Mostra a relação entre posição visual e slot interno."""

    print("\nOrdem recebida da Matribox:\n")

    for visual_position, internal_slot in enumerate(
        state.human_slots,
        start=1,
    ):
        print(
            f"Posição visual {visual_position:2} "
            f"→ slot interno {internal_slot:2}"
        )

    print("\nLista resumida:")
    print(list(state.human_slots))

    print(
        "\nResposta estrutural:",
        len(state.raw_message),
        "bytes",
    )
    print(
        "Unidades de comprimento declaradas:",
        f"0x{state.declared_length_units:02X}",
    )


def wait_for_chain_response(
    input_port,
) -> ChainOrderState | None:
    """Aguarda a resposta estrutural variável da cadeia."""

    deadline = (
        time.monotonic()
        + RESPONSE_TIMEOUT_SECONDS
    )

    while time.monotonic() < deadline:
        received_message = input_port.poll()

        if received_message is None:
            time.sleep(POLL_INTERVAL_SECONDS)
            continue

        if received_message.type != "sysex":
            continue

        full_message = bytes(
            received_message.bin()
        )

        print(
            "SysEx recebido:",
            len(full_message),
            "bytes",
        )

        try:
            state = parse_chain_order_response(
                full_message
            )
        except ChainOrderProtocolError as error:
            print(
                "Resposta estrutural inválida:",
                error,
            )
            continue

        if state is not None:
            return state

        event = parse_preset_event(
            full_message
        )

        if event is not None:
            print(
                "Evento intermediário de preset:",
                event.label,
            )

    return None


def main() -> None:
    """Inicializa a sessão, move e mostra a nova ordem."""

    try:
        source_position = int(
            input(
                "Digite a posição visual de origem "
                "(1 até 12): "
            ).strip()
        )

        destination_position = int(
            input(
                "Digite a posição visual de destino "
                "(1 até 12): "
            ).strip()
        )

        move_message = build_move_message(
            source_position=source_position,
            destination_position=destination_position,
        )

        confirmation = input(
            f"Confirmar movimento de {source_position} "
            f"para {destination_position}? Digite S: "
        ).strip().upper()

        if confirmation != "S":
            print("Movimento cancelado.")
            return

        with (
            mido.open_input(
                INPUT_PORT
            ) as input_port,
            mido.open_output(
                OUTPUT_PORT
            ) as output_port,
        ):
            clear_pending_messages(
                input_port
            )

            send_session_handshake(
                output_port
            )

            print(
                "\nAguardando a sessão estabilizar..."
            )
            time.sleep(
                SESSION_STABILIZATION_SECONDS
            )

            removed = clear_pending_messages(
                input_port
            )

            if removed:
                print(
                    "Mensagens da inicialização removidas:",
                    removed,
                )

            print("\nEnviando movimento...")

            output_port.send(
                move_message
            )

            print(
                "Movimento enviado. "
                "Aguardando a ordem atualizada..."
            )

            state = wait_for_chain_response(
                input_port
            )

        if state is None:
            print(
                "\nA Matribox não enviou uma resposta "
                "estrutural reconhecida dentro do tempo limite."
            )
            return

        print_chain_order(
            state
        )

    except ValueError as error:
        print("Erro:", error)

    except OSError as error:
        print(
            "Erro ao abrir uma porta MIDI:",
            error,
        )

    except KeyboardInterrupt:
        print(
            "\nOperação cancelada pelo usuário."
        )


if __name__ == "__main__":
    main()
