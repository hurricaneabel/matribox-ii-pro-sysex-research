"""Seleciona o preset 45B e solicita seu dump à Matribox II Pro."""

from __future__ import annotations

import time
from pathlib import Path

import mido


INPUT_PORT = "Matribox II Pro Subdevice 0"
OUTPUT_PORT = "Matribox II Pro Subdevice 1"

SELECTION_TIMEOUT_SECONDS = 2.0
DUMP_TIMEOUT_SECONDS = 5.0


# Localiza automaticamente a raiz do projeto:
#
# matribox-sysex/
# ├── data/
# │   └── dumps/
# └── tools/
#     └── commands/
#         └── request_preset_dump.py
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DUMPS_DIRECTORY = PROJECT_ROOT / "data" / "dumps"

DUMP_OUTPUT_FILE = (
    DUMPS_DIRECTORY
    / "preset_dump_received.txt"
)


# Comando real capturado ao selecionar o preset 45B.
SELECT_PRESET_45B_HEX = (
    "f021254d5000003212140000000001000000000100000c0000000000000109"
    "00010000000a00010b01000000000000010100000000f7"
)


# Pedido real enviado pelo editor depois da confirmação do preset 45B.
PRESET_READ_REQUEST_HEX = (
    "f021254d5000001d111000000000000000000001000008000000000000"
    "01050b01000000000000010100000000f7"
)


def create_sysex_message(
    hex_message: str,
) -> mido.Message:
    """Converte um pacote hexadecimal completo em mensagem Mido."""
    full_message = bytes.fromhex(hex_message)

    if full_message[0] != 0xF0:
        raise ValueError(
            "A mensagem não começa com F0."
        )

    if full_message[-1] != 0xF7:
        raise ValueError(
            "A mensagem não termina com F7."
        )

    # O Mido acrescenta F0 e F7 automaticamente.
    return mido.Message(
        "sysex",
        data=full_message[1:-1],
    )


def format_sysex(
    message: mido.Message,
) -> str:
    """Transforma uma mensagem SysEx em texto hexadecimal."""
    return " ".join(
        f"{byte:02X}"
        for byte in message.bin()
    )


def clear_pending_messages(
    input_port,
) -> None:
    """Remove mensagens antigas que estavam aguardando na entrada."""
    while input_port.poll() is not None:
        pass


def wait_for_preset_confirmation(
    input_port,
) -> mido.Message | None:
    """Aguarda a confirmação enviada após selecionar o preset."""
    deadline = (
        time.monotonic()
        + SELECTION_TIMEOUT_SECONDS
    )

    while time.monotonic() < deadline:
        message = input_port.poll()

        if message is None:
            time.sleep(0.01)
            continue

        if message.type != "sysex":
            continue

        full_message = list(
            message.bin()
        )

        print(
            "\nSysEx recebido após selecionar o preset:",
            len(full_message),
            "bytes",
        )

        print(
            format_sysex(message)
        )

        # A confirmação observada nas capturas possui 54 bytes.
        if len(full_message) == 54:
            return message

    return None


def collect_dump_responses(
    input_port,
) -> list[bytes]:
    """Reúne as respostas SysEx enviadas após o pedido de leitura."""
    received_messages: list[bytes] = []

    deadline = (
        time.monotonic()
        + DUMP_TIMEOUT_SECONDS
    )

    while time.monotonic() < deadline:
        message = input_port.poll()

        if message is None:
            time.sleep(0.01)
            continue

        if message.type != "sysex":
            continue

        full_message = bytes(
            message.bin()
        )

        received_messages.append(
            full_message
        )

        print(
            "\nSysEx do dump recebido:",
            len(full_message),
            "bytes",
        )

        print(
            " ".join(
                f"{byte:02X}"
                for byte in full_message
            )
        )

    return received_messages


def save_received_messages(
    received_messages: list[bytes],
) -> None:
    """Salva as mensagens recebidas na pasta data/dumps."""
    DUMPS_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    with DUMP_OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
    ) as output_file:
        for index, message in enumerate(
            received_messages,
            start=1,
        ):
            output_file.write(
                f"Mensagem {index} - "
                f"{len(message)} bytes\n"
            )

            output_file.write(
                " ".join(
                    f"{byte:02X}"
                    for byte in message
                )
            )

            output_file.write(
                "\n\n"
            )


def main() -> None:
    """Seleciona o 45B, aguarda confirmação e solicita o dump."""
    select_preset_message = (
        create_sysex_message(
            SELECT_PRESET_45B_HEX
        )
    )

    read_request_message = (
        create_sysex_message(
            PRESET_READ_REQUEST_HEX
        )
    )

    try:
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

            input(
                "Deixe o preset 45A selecionado e pressione "
                "Enter para o programa selecionar o 45B..."
            )

            print(
                "\nEnviando comando para selecionar "
                "o preset 45B..."
            )

            output_port.send(
                select_preset_message
            )

            confirmation = (
                wait_for_preset_confirmation(
                    input_port
                )
            )

            if confirmation is None:
                print(
                    "\nAviso: nenhuma confirmação "
                    "de 54 bytes foi recebida."
                )
            else:
                print(
                    "\nConfirmação da seleção "
                    "do preset recebida."
                )

            # Pequena pausa baseada no intervalo observado
            # na comunicação do editor oficial.
            time.sleep(0.2)

            print(
                "\nEnviando pedido de leitura "
                "do preset..."
            )

            output_port.send(
                read_request_message
            )

            print(
                "Aguardando o dump da Matribox..."
            )

            received_messages = (
                collect_dump_responses(
                    input_port
                )
            )

        save_received_messages(
            received_messages
        )

        print(
            "\nQuantidade de mensagens "
            "do dump recebidas:",
            len(received_messages),
        )

        print(
            "Resultado salvo em:",
            DUMP_OUTPUT_FILE,
        )

        if not received_messages:
            print(
                "\nA sequência completa também "
                "não gerou resposta."
            )

    except OSError as error:
        print(
            "Erro ao abrir uma porta MIDI:",
            error,
        )


if __name__ == "__main__":
    main()