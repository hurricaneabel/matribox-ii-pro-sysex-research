"""Reconstrói e decodifica o dump SysEx recebido da Matribox II Pro."""

from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DUMPS_DIRECTORY = PROJECT_ROOT / "data" / "dumps"

INPUT_FILE = DUMPS_DIRECTORY / "preset_dump_received.txt"

OUTPUT_BINARY_FILE = DUMPS_DIRECTORY / "preset_45B_original.bin"
OUTPUT_HEX_FILE = DUMPS_DIRECTORY / "preset_45B_original.hex"

HEADER = bytes(
    [
        0xF0,
        0x21,
        0x25,
        0x4D,
        0x50,
    ]
)


def read_messages_from_file(path: Path) -> list[bytes]:
    """Lê as mensagens hexadecimais salvas pelo script de captura."""
    if not path.exists():
        raise FileNotFoundError(
            f"O arquivo {path} não foi encontrado."
        )

    messages: list[bytes] = []
    current_bytes: list[int] = []

    for raw_line in path.read_text(
        encoding="utf-8"
    ).splitlines():
        line = raw_line.strip()

        if not line:
            if current_bytes:
                messages.append(bytes(current_bytes))
                current_bytes = []
            continue

        if line.startswith("Mensagem "):
            if current_bytes:
                messages.append(bytes(current_bytes))
                current_bytes = []
            continue

        try:
            current_bytes.extend(
                int(value, 16)
                for value in line.split()
            )
        except ValueError as error:
            raise ValueError(
                f"Linha hexadecimal inválida: {line}"
            ) from error

    if current_bytes:
        messages.append(bytes(current_bytes))

    return messages


def decode_nibbles(encoded_data: bytes) -> bytes:
    """Junta cada par de nibbles em um byte original."""
    if len(encoded_data) % 2 != 0:
        raise ValueError(
            "A quantidade de nibbles não é par."
        )

    decoded = bytearray()

    for index in range(0, len(encoded_data), 2):
        high_nibble = encoded_data[index]
        low_nibble = encoded_data[index + 1]

        if high_nibble > 0x0F or low_nibble > 0x0F:
            raise ValueError(
                "O conteúdo possui um valor que não é nibble."
            )

        decoded_byte = (
            high_nibble << 4
        ) | low_nibble

        decoded.append(decoded_byte)

    return bytes(decoded)


def decode_fragment(
    message: bytes,
) -> tuple[int, int, bytes]:
    """
    Decodifica um fragmento do dump.

    Retorna:
        tamanho total;
        offset do fragmento;
        conteúdo decodificado.
    """
    if len(message) < 14:
        raise ValueError(
            "Mensagem pequena demais para ser um fragmento."
        )

    if not message.startswith(HEADER):
        raise ValueError(
            "A mensagem não possui o cabeçalho esperado."
        )

    if message[-1] != 0xF7:
        raise ValueError(
            "A mensagem não termina com F7."
        )

    # Valores de 14 bits, divididos em dois bytes MIDI de 7 bits.
    total_size = message[9] + (
        message[10] << 7
    )

    fragment_offset = message[11] + (
        message[12] << 7
    )

    # Remove o cabeçalho de 13 bytes e o F7 final.
    encoded_payload = message[13:-1]

    decoded_payload = decode_nibbles(
        encoded_payload
    )

    return (
        total_size,
        fragment_offset,
        decoded_payload,
    )


def format_hex_dump(data: bytes) -> str:
    """Produz uma visualização hexadecimal com offsets."""
    lines: list[str] = []

    for offset in range(0, len(data), 16):
        row = data[offset:offset + 16]

        hexadecimal = " ".join(
            f"{byte:02X}"
            for byte in row
        )

        ascii_text = "".join(
            chr(byte)
            if 32 <= byte <= 126
            else "."
            for byte in row
        )

        lines.append(
            f"{offset:04X}  "
            f"{hexadecimal:<47}  "
            f"{ascii_text}"
        )

    return "\n".join(lines)


def reconstruct_dump(
    messages: list[bytes],
) -> bytes:
    """Posiciona cada fragmento no local correto do dump."""
    if not messages:
        raise ValueError(
            "Nenhuma mensagem foi encontrada."
        )

    decoded_fragments: list[
        tuple[int, bytes]
    ] = []

    expected_total_size: int | None = None

    for message_number, message in enumerate(
        messages,
        start=1,
    ):
        total_size, offset, decoded_payload = (
            decode_fragment(message)
        )

        if expected_total_size is None:
            expected_total_size = total_size

        if total_size != expected_total_size:
            raise ValueError(
                "Os fragmentos informam tamanhos totais diferentes."
            )

        print(
            f"Mensagem {message_number}:"
        )
        print(
            f"  SysEx completo: {len(message)} bytes"
        )
        print(
            f"  Tamanho total informado: {total_size} bytes"
        )
        print(
            f"  Offset: {offset}"
        )
        print(
            f"  Conteúdo decodificado: "
            f"{len(decoded_payload)} bytes"
        )

        decoded_fragments.append(
            (
                offset,
                decoded_payload,
            )
        )

    if expected_total_size is None:
        raise ValueError(
            "Não foi possível determinar o tamanho do dump."
        )

    reconstructed = bytearray(
        expected_total_size
    )

    received_positions = [
        False
    ] * expected_total_size

    for offset, payload in decoded_fragments:
        end_offset = offset + len(payload)

        if end_offset > expected_total_size:
            raise ValueError(
                "Um fragmento ultrapassa o tamanho total informado."
            )

        reconstructed[offset:end_offset] = payload

        for position in range(
            offset,
            end_offset,
        ):
            received_positions[position] = True

    missing_positions = [
        index
        for index, received in enumerate(
            received_positions
        )
        if not received
    ]

    if missing_positions:
        raise ValueError(
            "O dump está incompleto. "
            f"Faltam {len(missing_positions)} bytes."
        )

    return bytes(reconstructed)


def main() -> None:
    """Lê, decodifica, reconstrói e salva o dump."""
    try:
        messages = read_messages_from_file(
            INPUT_FILE
        )

        print(
            "Mensagens encontradas:",
            len(messages),
        )

        dump = reconstruct_dump(messages)

        OUTPUT_BINARY_FILE.write_bytes(dump)

        OUTPUT_HEX_FILE.write_text(
            format_hex_dump(dump),
            encoding="utf-8",
        )

        print(
            "\nDump reconstruído com sucesso:",
            len(dump),
            "bytes",
        )

        print(
            "Arquivo binário:",
            OUTPUT_BINARY_FILE,
        )

        print(
            "Visualização hexadecimal:",
            OUTPUT_HEX_FILE,
        )

    except (
        FileNotFoundError,
        ValueError,
    ) as error:
        print("Erro:", error)


if __name__ == "__main__":
    main()