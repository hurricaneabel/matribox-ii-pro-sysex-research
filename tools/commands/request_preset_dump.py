"""Inicializa a sessão, seleciona o preset 45B e solicita seu dump."""

from __future__ import annotations

import time
from pathlib import Path

import mido


INPUT_PORT = "Matribox II Pro Subdevice 0"
OUTPUT_PORT = "Matribox II Pro Subdevice 1"

HANDSHAKE_REPETITIONS = 4
HANDSHAKE_INTERVAL_SECONDS = 0.2
SESSION_STABILIZATION_SECONDS = 1.5
SELECTION_RETRY_COUNT = 3
SELECTION_RETRY_DELAY_SECONDS = 0.5

SELECTION_TIMEOUT_SECONDS = 2.0
PRESET_LOAD_DELAY_SECONDS = 2.0

DUMP_TIMEOUT_SECONDS = 8.0
POLL_INTERVAL_SECONDS = 0.01

# Evita que uma confirmação de 54 bytes seja confundida com um dump.
MIN_PRESET_DUMP_SIZE = 200
MAX_PRESET_DUMP_SIZE = 4096

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DUMPS_DIRECTORY = PROJECT_ROOT / "data" / "dumps"
DUMP_OUTPUT_FILE = DUMPS_DIRECTORY / "preset_dump_received.txt"

# Mensagem enviada quatro vezes pelo editor oficial ao iniciar a sessão.
SESSION_HANDSHAKE_HEX = "f021257e47502d321112000000f7"

# Comando capturado ao selecionar o preset 45B.
SELECT_PRESET_45B_HEX = (
    "f021254d5000003212140000000001000000000100000c0000000000000109"
    "00010000000a00010b01000000000000010100000000f7"
)

# Pedido capturado para ler o preset.
PRESET_READ_REQUEST_HEX = (
    "f021254d5000001d111000000000000000000001000008000000000000"
    "01050b01000000000000010100000000f7"
)


def create_sysex_message(hex_message: str) -> mido.Message:
    """Converte um pacote hexadecimal completo em mensagem Mido."""
    full_message = bytes.fromhex(hex_message)

    if len(full_message) < 2:
        raise ValueError("A mensagem SysEx está vazia ou incompleta.")
    if full_message[0] != 0xF0:
        raise ValueError("A mensagem não começa com F0.")
    if full_message[-1] != 0xF7:
        raise ValueError("A mensagem não termina com F7.")

    # O Mido acrescenta F0 e F7 automaticamente.
    return mido.Message("sysex", data=full_message[1:-1])


def format_sysex(message: mido.Message) -> str:
    """Transforma uma mensagem SysEx em texto hexadecimal."""
    return " ".join(f"{byte:02X}" for byte in message.bin())


def clear_pending_messages(input_port) -> int:
    """Remove mensagens antigas que aguardavam na entrada."""
    removed = 0

    while input_port.poll() is not None:
        removed += 1

    return removed


def send_session_handshake(output_port) -> None:
    """Envia a sequência que habilita respostas da Matribox."""
    handshake = create_sysex_message(SESSION_HANDSHAKE_HEX)

    print("\nInicializando a sessão com a Matribox...")

    for attempt in range(1, HANDSHAKE_REPETITIONS + 1):
        output_port.send(handshake)

        print(
            "Inicialização enviada:",
            f"{attempt}/{HANDSHAKE_REPETITIONS}",
        )

        if attempt < HANDSHAKE_REPETITIONS:
            time.sleep(HANDSHAKE_INTERVAL_SECONDS)

    print("Sequência de inicialização concluída.")


def is_preset_45b_confirmation(
    full_message: bytes,
) -> bool:
    """Reconhece a confirmação observada após selecionar o 45B."""
    return (
        len(full_message) == 54
        and full_message[:5]
        == bytes.fromhex("F0 21 25 4D 50")
        and full_message[-1] == 0xF7
        and full_message[8] == 0x00
        and full_message[9] == 0x14
        and full_message[22] == 0x0C
        and full_message[30] == 0x09
        and full_message[36] == 0x0A
        and full_message[39] == 0x0B
    )


def wait_for_preset_confirmation(input_port) -> bool:
    """Aguarda a confirmação sem confundir outros SysEx."""
    deadline = time.monotonic() + SELECTION_TIMEOUT_SECONDS

    while time.monotonic() < deadline:
        message = input_port.poll()

        if message is None:
            time.sleep(POLL_INTERVAL_SECONDS)
            continue
        if message.type != "sysex":
            continue

        full_message = bytes(message.bin())

        print(
            "\nSysEx recebido após selecionar o preset:",
            len(full_message),
            "bytes",
        )
        print(format_sysex(message))

        if is_preset_45b_confirmation(full_message):
            return True

    return False

def select_preset_with_confirmation(
    input_port,
    output_port,
    select_preset_message: mido.Message,
) -> bool:
    """Seleciona o 45B e exige a confirmação antes da leitura."""
    for attempt in range(
        1,
        SELECTION_RETRY_COUNT + 1,
    ):
        removed = clear_pending_messages(
            input_port
        )

        if removed:
            print(
                "\nMensagens antigas removidas:",
                removed,
            )

        print(
            "\nSelecionando o preset 45B:",
            f"tentativa {attempt}/"
            f"{SELECTION_RETRY_COUNT}",
        )

        output_port.send(
            select_preset_message
        )

        if wait_for_preset_confirmation(
            input_port
        ):
            print(
                "\nConfirmação correta do "
                "preset 45B recebida."
            )

            return True

        print(
            "\nA confirmação não chegou "
            "nesta tentativa."
        )

        time.sleep(
            SELECTION_RETRY_DELAY_SECONDS
        )

    return False


def get_dump_fragment_info(
    full_message: bytes,
) -> tuple[int, int, int] | None:
    """
    Retorna tamanho total, offset e tamanho decodificado.

    Os dados começam no índice 13 e usam pares de nibbles.
    """
    if len(full_message) < 14:
        return None
    if full_message[:5] != bytes.fromhex("F0 21 25 4D 50"):
        return None
    if full_message[-1] != 0xF7:
        return None

    total_size = full_message[9] + (full_message[10] << 7)
    offset = full_message[11] + (full_message[12] << 7)

    if not MIN_PRESET_DUMP_SIZE <= total_size <= MAX_PRESET_DUMP_SIZE:
        return None

    encoded_payload = full_message[13:-1]

    if not encoded_payload:
        return None
    if len(encoded_payload) % 2 != 0:
        return None
    if any(value > 0x0F for value in encoded_payload):
        return None

    decoded_length = len(encoded_payload) // 2

    if offset >= total_size:
        return None
    if offset + decoded_length > total_size:
        return None

    return total_size, offset, decoded_length


def is_dump_complete(received_messages: list[bytes]) -> bool:
    """Verifica se todos os bytes declarados foram recebidos."""
    if not received_messages:
        return False

    first_info = get_dump_fragment_info(received_messages[0])
    if first_info is None:
        return False

    expected_total = first_info[0]
    coverage = bytearray(expected_total)

    for message in received_messages:
        info = get_dump_fragment_info(message)

        if info is None:
            continue

        total_size, offset, decoded_length = info

        if total_size != expected_total:
            continue

        coverage[offset : offset + decoded_length] = b"\x01" * decoded_length

    return all(coverage)


def collect_dump_responses(input_port) -> list[bytes]:
    """Reúne somente fragmentos válidos do mesmo dump."""
    received: list[bytes] = []
    expected_total: int | None = None
    seen_fragments: dict[tuple[int, int], bytes] = {}

    deadline = time.monotonic() + DUMP_TIMEOUT_SECONDS

    while time.monotonic() < deadline:
        message = input_port.poll()

        if message is None:
            time.sleep(POLL_INTERVAL_SECONDS)
            continue
        if message.type != "sysex":
            continue

        full_message = bytes(message.bin())
        info = get_dump_fragment_info(full_message)

        if info is None:
            print(
                "\nSysEx ignorado durante a leitura:",
                len(full_message),
                "bytes",
            )
            continue

        total_size, offset, decoded_length = info

        if expected_total is None:
            expected_total = total_size

        if total_size != expected_total:
            print(
                "\nFragmento ignorado: tamanho total diferente.",
                f"Esperado {expected_total}, recebido {total_size}.",
            )
            continue

        fragment_key = (offset, decoded_length)
        previous_fragment = seen_fragments.get(fragment_key)

        if previous_fragment is not None:
            if previous_fragment == full_message:
                print(
                    "\nFragmento duplicado ignorado:",
                    f"offset {offset}.",
                )
            else:
                print(
                    "\nAviso: fragmento conflitante ignorado:",
                    f"offset {offset}.",
                )
            continue

        seen_fragments[fragment_key] = full_message
        received.append(full_message)

        print(
            "\nSysEx do dump recebido:",
            len(full_message),
            "bytes",
        )
        print("Tamanho total declarado:", total_size, "bytes")
        print("Offset do fragmento:", offset)
        print("Bytes decodificados no fragmento:", decoded_length)
        print(" ".join(f"{byte:02X}" for byte in full_message))

        if is_dump_complete(received):
            print(
                "\nTodos os bytes declarados "
                "do dump foram recebidos."
            )
            break

    return received


def save_received_messages(received_messages: list[bytes]) -> None:
    """Salva as mensagens recebidas em data/dumps."""
    DUMPS_DIRECTORY.mkdir(parents=True, exist_ok=True)

    with DUMP_OUTPUT_FILE.open("w", encoding="utf-8") as output_file:
        for index, message in enumerate(received_messages, start=1):
            info = get_dump_fragment_info(message)

            output_file.write(
                f"Mensagem {index} - {len(message)} bytes\n"
            )

            if info is not None:
                total_size, offset, decoded_length = info
                output_file.write(
                    f"Tamanho total: {total_size}\n"
                    f"Offset: {offset}\n"
                    f"Bytes decodificados: {decoded_length}\n"
                )

            output_file.write(
                " ".join(f"{byte:02X}" for byte in message)
            )
            output_file.write("\n\n")


def main() -> None:
    """Executa inicialização, seleção confirmada e leitura do preset."""
    input(
        "Deixe o preset 45A selecionado e pressione "
        "Enter para iniciar a leitura do 45B..."
    )

    select_preset = create_sysex_message(
        SELECT_PRESET_45B_HEX
    )

    read_request = create_sysex_message(
        PRESET_READ_REQUEST_HEX
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
            removed = clear_pending_messages(
                input_port
            )

            if removed:
                print(
                    "Mensagens antigas removidas:",
                    removed,
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

            confirmation_received = (
                select_preset_with_confirmation(
                    input_port,
                    output_port,
                    select_preset,
                )
            )

            if not confirmation_received:
                print(
                    "\nLeitura cancelada: não foi possível "
                    "confirmar a seleção do preset 45B."
                )

                return

            print(
                "\nAguardando o preset terminar "
                "de carregar..."
            )

            time.sleep(
                PRESET_LOAD_DELAY_SECONDS
            )

            removed = clear_pending_messages(
                input_port
            )

            if removed:
                print(
                    "Mensagens atrasadas removidas "
                    "antes da leitura:",
                    removed,
                )

            print(
                "\nEnviando pedido de leitura "
                "do preset..."
            )

            output_port.send(
                read_request
            )

            print(
                "Aguardando o dump da Matribox..."
            )

            received_messages = (
                collect_dump_responses(
                    input_port
                )
            )

        if not received_messages:
            print(
                "\nNenhum fragmento válido "
                "do dump foi recebido."
            )

            return

        save_received_messages(
            received_messages
        )

        print(
            "\nQuantidade de fragmentos recebidos:",
            len(received_messages),
        )

        print(
            "Dump completo:",
            "sim"
            if is_dump_complete(
                received_messages
            )
            else "não",
        )

        print(
            "Resultado salvo em:",
            DUMP_OUTPUT_FILE,
        )

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