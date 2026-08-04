"""Lê duas vezes o mesmo preset após uma seleção confirmada."""

from __future__ import annotations

import hashlib
import time
from pathlib import Path

import mido

from tools.analysis.decode_preset_dump import reconstruct_dump
from tools.commands.request_preset_dump import (
    INPUT_PORT,
    OUTPUT_PORT,
    PRESET_LOAD_DELAY_SECONDS,
    PRESET_READ_REQUEST_HEX,
    SELECT_PRESET_45B_HEX,
    SESSION_STABILIZATION_SECONDS,
    clear_pending_messages,
    collect_dump_responses,
    create_sysex_message,
    get_dump_fragment_info,
    is_dump_complete,
    select_preset_with_confirmation,
    send_session_handshake,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DUMPS_DIRECTORY = PROJECT_ROOT / "data" / "dumps"

READ_A_TEXT_FILE = DUMPS_DIRECTORY / "preset_45B_confirmed_same_session_A.txt"
READ_A_BINARY_FILE = DUMPS_DIRECTORY / "preset_45B_confirmed_same_session_A.bin"

READ_B_TEXT_FILE = DUMPS_DIRECTORY / "preset_45B_confirmed_same_session_B.txt"
READ_B_BINARY_FILE = DUMPS_DIRECTORY / "preset_45B_confirmed_same_session_B.bin"

DELAY_BETWEEN_READS_SECONDS = 2.0


def save_raw_messages(
    messages: list[bytes],
    output_file: Path,
) -> None:
    """Salva os fragmentos SysEx em formato textual."""
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with output_file.open("w", encoding="utf-8") as destination:
        for index, message in enumerate(messages, start=1):
            fragment_info = get_dump_fragment_info(message)

            destination.write(
                f"Mensagem {index} - {len(message)} bytes\n"
            )

            if fragment_info is not None:
                total_size, offset, decoded_length = fragment_info

                destination.write(
                    f"Tamanho total: {total_size}\n"
                    f"Offset: {offset}\n"
                    f"Bytes decodificados: {decoded_length}\n"
                )

            destination.write(
                " ".join(f"{byte:02X}" for byte in message)
            )
            destination.write("\n\n")


def calculate_sha256(data: bytes) -> str:
    """Calcula o hash SHA-256."""
    return hashlib.sha256(data).hexdigest().upper()


def request_dump(
    input_port,
    output_port,
    read_request: mido.Message,
    label: str,
    text_file: Path,
    binary_file: Path,
) -> bytes:
    """Solicita, valida, reconstrói e salva um dump."""
    removed = clear_pending_messages(input_port)

    if removed:
        print(
            f"Mensagens antigas removidas antes da leitura {label}:",
            removed,
        )

    print(f"\nEnviando pedido da leitura {label}...")
    output_port.send(read_request)

    print(f"Aguardando o dump da leitura {label}...")
    messages = collect_dump_responses(input_port)

    if not messages:
        raise RuntimeError(
            f"Nenhum fragmento foi recebido na leitura {label}."
        )

    if not is_dump_complete(messages):
        raise RuntimeError(
            f"O dump da leitura {label} está incompleto."
        )

    reconstructed_data, fragment_summary = reconstruct_dump(messages)

    save_raw_messages(messages, text_file)
    binary_file.write_bytes(reconstructed_data)

    print(f"\nLeitura {label} concluída.")
    print("Tamanho reconstruído:", len(reconstructed_data), "bytes")

    for offset, decoded_length in fragment_summary:
        print(
            f"Fragmento: offset {offset}, "
            f"{decoded_length} bytes"
        )

    print("SHA-256:", calculate_sha256(reconstructed_data))
    print("Arquivo textual:", text_file)
    print("Arquivo binário:", binary_file)

    return reconstructed_data


def main() -> None:
    """Seleciona o 45B uma vez e o lê duas vezes na mesma sessão."""
    input(
        "Deixe o preset 45A selecionado e pressione "
        "Enter para iniciar o teste..."
    )

    select_preset = create_sysex_message(SELECT_PRESET_45B_HEX)
    read_request = create_sysex_message(PRESET_READ_REQUEST_HEX)

    try:
        with (
            mido.open_input(INPUT_PORT) as input_port,
            mido.open_output(OUTPUT_PORT) as output_port,
        ):
            clear_pending_messages(input_port)

            send_session_handshake(output_port)

            print("\nAguardando a sessão estabilizar...")
            time.sleep(SESSION_STABILIZATION_SECONDS)

            clear_pending_messages(input_port)

            confirmation_received = select_preset_with_confirmation(
                input_port,
                output_port,
                select_preset,
            )

            if not confirmation_received:
                print(
                    "\nTeste cancelado: não foi possível "
                    "confirmar a seleção do preset 45B."
                )
                return

            print("\nAguardando o preset terminar de carregar...")
            time.sleep(PRESET_LOAD_DELAY_SECONDS)

            first_dump = request_dump(
                input_port,
                output_port,
                read_request,
                "A",
                READ_A_TEXT_FILE,
                READ_A_BINARY_FILE,
            )

            print(
                "\nMantendo exatamente a mesma sessão "
                "e o mesmo preset..."
            )
            time.sleep(DELAY_BETWEEN_READS_SECONDS)

            second_dump = request_dump(
                input_port,
                output_port,
                read_request,
                "B",
                READ_B_TEXT_FILE,
                READ_B_BINARY_FILE,
            )

        first_hash = calculate_sha256(first_dump)
        second_hash = calculate_sha256(second_dump)

        print("\nRESULTADO FINAL")
        print("Tamanho A:", len(first_dump), "bytes")
        print("Tamanho B:", len(second_dump), "bytes")
        print("Hash A:", first_hash)
        print("Hash B:", second_hash)

        if first_dump == second_dump:
            print("\nRESULTADO: os dois dumps são idênticos.")
        else:
            print("\nRESULTADO: os dois dumps são diferentes.")

    except (OSError, RuntimeError, ValueError) as error:
        print("\nErro durante o teste:", error)
    except KeyboardInterrupt:
        print("\nTeste cancelado pelo usuário.")


if __name__ == "__main__":
    main()