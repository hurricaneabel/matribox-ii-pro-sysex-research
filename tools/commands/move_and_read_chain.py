"""Move um efeito e lê da Matribox a nova ordem visual da cadeia."""

from __future__ import annotations

import time

import mido

from tools.commands.move_effect_position import build_move_message


INPUT_PORT = "Matribox II Pro Subdevice 0"
OUTPUT_PORT = "Matribox II Pro Subdevice 1"

RESPONSE_TIMEOUT_SECONDS = 5.0

CHAIN_RESPONSE_LENGTH = 140
CHAIN_ORDER_START_INDEX = 42
CHAIN_SLOT_COUNT = 12
CHAIN_SLOT_SIZE = 2

SYSEX_HEADER = [
    0xF0,
    0x21,
    0x25,
    0x4D,
    0x50,
]


def parse_chain_order(
    message: mido.Message,
) -> list[int] | None:
    """
    Interpreta a resposta SysEx que contém a ordem visual da cadeia.

    Retorna uma lista com os slots internos usando numeração humana:

        [1, 2, 3, ..., 12]

    Ou retorna None quando a mensagem não for a resposta esperada.
    """
    if message.type != "sysex":
        return None

    # msg.bin() devolve a mensagem completa, incluindo F0 e F7.
    full_message = list(message.bin())

    if len(full_message) != CHAIN_RESPONSE_LENGTH:
        return None

    if full_message[:5] != SYSEX_HEADER:
        return None

    # Nas respostas de ordem capturadas:
    #
    # índice 8 = 00
    # índice 9 = 3F
    if full_message[8] != 0x00:
        return None

    if full_message[9] != 0x3F:
        return None

    internal_slots: list[int] = []

    for visual_index in range(CHAIN_SLOT_COUNT):
        value_index = (
            CHAIN_ORDER_START_INDEX
            + visual_index * CHAIN_SLOT_SIZE
        )

        internal_id = full_message[value_index]
        second_byte = full_message[value_index + 1]

        # Nas respostas capturadas, cada entrada apareceu como:
        #
        # 00 00
        # 01 00
        # 02 00
        # ...
        #
        # O segundo byte permaneceu zero.
        if second_byte != 0x00:
            print(
                "Aviso: formato inesperado na posição",
                visual_index + 1,
            )

        # O protocolo começa em zero.
        # Nosso programa apresenta os slots começando em um.
        internal_slot = internal_id + 1

        internal_slots.append(internal_slot)

    return internal_slots


def print_chain_order(internal_slots: list[int]) -> None:
    """Mostra qual slot interno está em cada posição visual."""
    print("\nOrdem recebida da Matribox:\n")

    for visual_position, internal_slot in enumerate(
        internal_slots,
        start=1,
    ):
        print(
            f"Posição visual {visual_position:2} "
            f"→ slot interno {internal_slot:2}"
        )

    print("\nLista resumida:")

    print(internal_slots)


def clear_pending_messages(
    input_port: mido.ports.BaseInput,
) -> None:
    """Remove mensagens antigas que já estavam aguardando na entrada."""
    while input_port.poll() is not None:
        pass


def wait_for_chain_response(
    input_port: mido.ports.BaseInput,
) -> list[int] | None:
    """Aguarda a resposta da Matribox durante alguns segundos."""
    deadline = time.monotonic() + RESPONSE_TIMEOUT_SECONDS

    while time.monotonic() < deadline:
        received_message = input_port.poll()

        if received_message is None:
            time.sleep(0.01)
            continue

        if received_message.type != "sysex":
            continue

        full_message = list(received_message.bin())

        print(
            "SysEx recebido:",
            len(full_message),
            "bytes",
        )

        chain_order = parse_chain_order(
            received_message
        )

        if chain_order is not None:
            return chain_order

    return None


def main() -> None:
    """Envia um movimento e lê a ordem devolvida pela Matribox."""
    try:
        source_position = int(
            input(
                "Digite a posição visual de origem (1 até 12): "
            ).strip()
        )

        destination_position = int(
            input(
                "Digite a posição visual de destino (1 até 12): "
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

        # A entrada precisa estar aberta antes do envio.
        # Assim não perdemos a resposta imediata da Matribox.
        with (
            mido.open_input(INPUT_PORT) as input_port,
            mido.open_output(OUTPUT_PORT) as output_port,
        ):
            clear_pending_messages(input_port)

            print("\nEnviando movimento...")

            output_port.send(move_message)

            print(
                "Movimento enviado. "
                "Aguardando resposta da Matribox..."
            )

            chain_order = wait_for_chain_response(
                input_port
            )

        if chain_order is None:
            print(
                "\nA Matribox não enviou uma resposta de ordem "
                "reconhecida dentro do tempo limite."
            )
            return

        print_chain_order(chain_order)

    except ValueError as error:
        print("Erro:", error)

    except OSError as error:
        print(
            "Erro ao abrir uma porta MIDI:",
            error,
        )


if __name__ == "__main__":
    main()