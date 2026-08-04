"""Reconstrói um dump binário a partir de fragmentos SysEx da Matribox."""

from __future__ import annotations

import argparse
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DUMPS_DIRECTORY = PROJECT_ROOT / "data" / "dumps"

DEFAULT_INPUT_FILE = (
    DUMPS_DIRECTORY
    / "preset_dump_received.txt"
)

MATRIBOX_HEADER = bytes.fromhex(
    "F0 21 25 4D 50"
)


def resolve_input_path(
    supplied_path: str,
) -> Path:
    """Localiza o arquivo informado no caminho atual ou em data/dumps."""
    direct_path = Path(
        supplied_path
    )

    if direct_path.is_file():
        return direct_path.resolve()

    dumps_path = (
        DUMPS_DIRECTORY
        / supplied_path
    )

    if dumps_path.is_file():
        return dumps_path.resolve()

    raise FileNotFoundError(
        f"Arquivo não encontrado: {supplied_path}"
    )


def parse_hex_line(
    line: str,
) -> bytes | None:
    """Converte uma linha contendo uma mensagem SysEx em bytes."""
    cleaned_line = line.strip()

    if not cleaned_line.upper().startswith(
        "F0 "
    ):
        return None

    tokens = cleaned_line.split()

    try:
        message = bytes(
            int(token, 16)
            for token in tokens
        )
    except ValueError:
        return None

    if not message:
        return None

    if message[0] != 0xF0:
        return None

    if message[-1] != 0xF7:
        return None

    return message


def read_sysex_messages(
    input_file: Path,
) -> list[bytes]:
    """Extrai todas as mensagens SysEx completas do arquivo de texto."""
    messages: list[bytes] = []

    with input_file.open(
        "r",
        encoding="utf-8",
    ) as source_file:
        for line in source_file:
            message = parse_hex_line(
                line
            )

            if message is not None:
                messages.append(
                    message
                )

    if not messages:
        raise ValueError(
            "Nenhuma mensagem SysEx completa foi encontrada."
        )

    return messages


def decode_nibbles(
    encoded_data: bytes,
) -> bytes:
    """Une pares de nibbles em bytes normais."""
    if len(encoded_data) % 2 != 0:
        raise ValueError(
            "A quantidade de nibbles não é par."
        )

    decoded_data = bytearray()

    for index in range(
        0,
        len(encoded_data),
        2,
    ):
        high_nibble = encoded_data[index]
        low_nibble = encoded_data[index + 1]

        if high_nibble > 0x0F:
            raise ValueError(
                f"Nibble alto inválido: {high_nibble:02X}"
            )

        if low_nibble > 0x0F:
            raise ValueError(
                f"Nibble baixo inválido: {low_nibble:02X}"
            )

        decoded_byte = (
            high_nibble << 4
        ) | low_nibble

        decoded_data.append(
            decoded_byte
        )

    return bytes(
        decoded_data
    )


def decode_fragment(
    message: bytes,
) -> tuple[int, int, bytes]:
    """
    Decodifica um fragmento.

    Retorna:
    - tamanho total do preset;
    - offset do fragmento;
    - conteúdo decodificado.
    """
    if len(message) < 14:
        raise ValueError(
            "Mensagem curta demais para ser um fragmento."
        )

    if not message.startswith(
        MATRIBOX_HEADER
    ):
        raise ValueError(
            "Cabeçalho da Matribox não encontrado."
        )

    if message[-1] != 0xF7:
        raise ValueError(
            "Mensagem não termina com F7."
        )

    total_size = (
        message[9]
        + (message[10] << 7)
    )

    fragment_offset = (
        message[11]
        + (message[12] << 7)
    )

    encoded_payload = message[
        13:-1
    ]

    decoded_payload = decode_nibbles(
        encoded_payload
    )

    return (
        total_size,
        fragment_offset,
        decoded_payload,
    )


def reconstruct_dump(
    messages: list[bytes],
) -> tuple[bytes, list[tuple[int, int]]]:
    """Reconstrói o dump completo usando os offsets dos fragmentos."""
    fragments: list[
        tuple[int, int, bytes]
    ] = []

    for message in messages:
        fragments.append(
            decode_fragment(
                message
            )
        )

    expected_total = fragments[0][0]

    for total_size, _, _ in fragments:
        if total_size != expected_total:
            raise ValueError(
                "Os fragmentos declaram tamanhos totais diferentes."
            )

    reconstructed_data = bytearray(
        expected_total
    )

    coverage = [
        False
        for _ in range(
            expected_total
        )
    ]

    fragment_summary: list[
        tuple[int, int]
    ] = []

    for _, offset, payload in sorted(
        fragments,
        key=lambda fragment: fragment[1],
    ):
        fragment_end = (
            offset
            + len(payload)
        )

        if fragment_end > expected_total:
            raise ValueError(
                "Um fragmento ultrapassa o tamanho total declarado."
            )

        for local_index, value in enumerate(
            payload
        ):
            absolute_index = (
                offset
                + local_index
            )

            if (
                coverage[absolute_index]
                and reconstructed_data[absolute_index]
                != value
            ):
                raise ValueError(
                    "Fragmentos sobrepostos possuem valores diferentes "
                    f"no índice {absolute_index}."
                )

            reconstructed_data[absolute_index] = value
            coverage[absolute_index] = True

        fragment_summary.append(
            (
                offset,
                len(payload),
            )
        )

    missing_positions = [
        index
        for index, covered in enumerate(
            coverage
        )
        if not covered
    ]

    if missing_positions:
        raise ValueError(
            "O dump está incompleto. "
            f"Faltam {len(missing_positions)} bytes. "
            f"Primeiro índice ausente: {missing_positions[0]}."
        )

    return (
        bytes(reconstructed_data),
        fragment_summary,
    )


def format_hex_dump(
    data: bytes,
) -> str:
    """Cria uma visualização hexadecimal com 16 bytes por linha."""
    lines: list[str] = []

    for offset in range(
        0,
        len(data),
        16,
    ):
        chunk = data[
            offset:offset + 16
        ]

        hexadecimal = " ".join(
            f"{byte:02X}"
            for byte in chunk
        )

        ascii_text = "".join(
            chr(byte)
            if 32 <= byte <= 126
            else "."
            for byte in chunk
        )

        lines.append(
            f"{offset:04X}: "
            f"{hexadecimal:<47} "
            f"{ascii_text}"
        )

    return "\n".join(
        lines
    )


def save_outputs(
    input_file: Path,
    reconstructed_data: bytes,
) -> tuple[Path, Path]:
    """Salva o arquivo binário e sua visualização hexadecimal."""
    output_binary_file = input_file.with_suffix(
        ".bin"
    )

    output_hex_file = input_file.with_suffix(
        ".hex"
    )

    output_binary_file.write_bytes(
        reconstructed_data
    )

    output_hex_file.write_text(
        format_hex_dump(
            reconstructed_data
        )
        + "\n",
        encoding="utf-8",
    )

    return (
        output_binary_file,
        output_hex_file,
    )


def create_argument_parser() -> argparse.ArgumentParser:
    """Cria os argumentos da linha de comando."""
    parser = argparse.ArgumentParser(
        description=(
            "Reconstrói um dump binário da Matribox "
            "a partir de fragmentos SysEx."
        )
    )

    parser.add_argument(
        "input_file",
        nargs="?",
        default=str(
            DEFAULT_INPUT_FILE
        ),
        help=(
            "Arquivo TXT completo ou nome de um arquivo "
            "existente dentro de data/dumps."
        ),
    )

    return parser


def main() -> None:
    """Executa a reconstrução do dump."""
    parser = create_argument_parser()
    arguments = parser.parse_args()

    try:
        input_file = resolve_input_path(
            arguments.input_file
        )

        messages = read_sysex_messages(
            input_file
        )

        reconstructed_data, fragment_summary = (
            reconstruct_dump(
                messages
            )
        )

        binary_file, hex_file = save_outputs(
            input_file,
            reconstructed_data,
        )

        print(
            "Arquivo de entrada:",
            input_file,
        )

        print(
            "Mensagens SysEx encontradas:",
            len(messages),
        )

        for index, (
            offset,
            decoded_length,
        ) in enumerate(
            fragment_summary,
            start=1,
        ):
            print(
                f"Fragmento {index}: "
                f"offset {offset}, "
                f"{decoded_length} bytes"
            )

        print(
            "Tamanho reconstruído:",
            len(reconstructed_data),
            "bytes",
        )

        print(
            "Arquivo binário:",
            binary_file,
        )

        print(
            "Arquivo hexadecimal:",
            hex_file,
        )

    except (
        FileNotFoundError,
        ValueError,
        OSError,
    ) as error:
        raise SystemExit(
            f"Erro: {error}"
        ) from error


if __name__ == "__main__":
    main()