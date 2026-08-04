"""Analisa dois dumps do mesmo preset com alinhamento estrutural."""

from __future__ import annotations

import difflib
import hashlib
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DUMPS_DIRECTORY = PROJECT_ROOT / "data" / "dumps"

DUMP_A_FILE = (
    DUMPS_DIRECTORY
    / "preset_45B_confirmed_same_session_A.bin"
)

DUMP_B_FILE = (
    DUMPS_DIRECTORY
    / "preset_45B_confirmed_same_session_B.bin"
)

REPORT_FILE = (
    DUMPS_DIRECTORY
    / "preset_45B_confirmed_alignment_report.txt"
)

MAX_PREVIEW_BYTES = 32


def sha256(data: bytes) -> str:
    """Calcula SHA-256 em letras maiúsculas."""
    return hashlib.sha256(data).hexdigest().upper()


def common_prefix_length(first: bytes, second: bytes) -> int:
    """Conta os bytes iniciais idênticos."""
    limit = min(len(first), len(second))

    for index in range(limit):
        if first[index] != second[index]:
            return index

    return limit


def common_suffix_length(
    first: bytes,
    second: bytes,
    prefix_length: int,
) -> int:
    """Conta os bytes finais idênticos sem invadir o prefixo."""
    maximum = min(
        len(first) - prefix_length,
        len(second) - prefix_length,
    )

    for length in range(maximum):
        if first[-1 - length] != second[-1 - length]:
            return length

    return maximum


def hex_preview(data: bytes) -> str:
    """Formata uma pequena amostra hexadecimal."""
    if not data:
        return "(vazio)"

    preview = data[:MAX_PREVIEW_BYTES]
    text = " ".join(f"{byte:02X}" for byte in preview)

    if len(data) > MAX_PREVIEW_BYTES:
        text += f" ... (+{len(data) - MAX_PREVIEW_BYTES} bytes)"

    return text


def opcode_name(tag: str) -> str:
    """Traduz o tipo de operação do alinhamento."""
    names = {
        "equal": "IGUAL",
        "replace": "SUBSTITUIÇÃO",
        "delete": "REMOÇÃO EM B",
        "insert": "INSERÇÃO EM B",
    }
    return names.get(tag, tag.upper())


def build_report(first: bytes, second: bytes) -> str:
    """Cria um relatório usando alinhamento de sequência."""
    prefix = common_prefix_length(first, second)
    suffix = common_suffix_length(first, second, prefix)

    matcher = difflib.SequenceMatcher(
        None,
        first,
        second,
        autojunk=False,
    )

    opcodes = matcher.get_opcodes()
    unequal_opcodes = [
        opcode
        for opcode in opcodes
        if opcode[0] != "equal"
    ]

    matching_bytes = sum(
        first_end - first_start
        for tag, first_start, first_end, _, _ in opcodes
        if tag == "equal"
    )

    lines = [
        "ANÁLISE ESTRUTURAL DOS DUMPS CONFIRMADOS DO PRESET 45B",
        "=" * 78,
        "",
        f"Arquivo A: {DUMP_A_FILE.name}",
        f"Tamanho A: {len(first)} bytes",
        f"SHA-256 A: {sha256(first)}",
        "",
        f"Arquivo B: {DUMP_B_FILE.name}",
        f"Tamanho B: {len(second)} bytes",
        f"SHA-256 B: {sha256(second)}",
        "",
        f"Diferença de tamanho B - A: {len(second) - len(first)} bytes",
        f"Prefixo idêntico direto: {prefix} bytes",
        f"Sufixo idêntico direto: {suffix} bytes",
        f"Bytes alinhados como iguais: {matching_bytes}",
        f"Blocos variáveis encontrados: {len(unequal_opcodes)}",
        "",
    ]

    if len(first) > 4 and len(second) > 4:
        lines.extend(
            [
                "RELAÇÃO DO CAMPO NO ÍNDICE 0x0004",
                "-" * 78,
                f"A[0x0004] = 0x{first[4]:02X} = {first[4]}",
                f"B[0x0004] = 0x{second[4]:02X} = {second[4]}",
                f"264 + A[0x0004] = {264 + first[4]}",
                f"264 + B[0x0004] = {264 + second[4]}",
                "",
            ]
        )

    lines.extend(
        [
            "BLOCOS DO ALINHAMENTO",
            "-" * 78,
        ]
    )

    for number, (
        tag,
        first_start,
        first_end,
        second_start,
        second_end,
    ) in enumerate(opcodes, start=1):
        first_chunk = first[first_start:first_end]
        second_chunk = second[second_start:second_end]

        lines.append(
            f"{number:02d}. {opcode_name(tag)}"
        )
        lines.append(
            f"    A: 0x{first_start:04X} até "
            f"0x{first_end:04X} "
            f"({len(first_chunk)} bytes)"
        )
        lines.append(
            f"    B: 0x{second_start:04X} até "
            f"0x{second_end:04X} "
            f"({len(second_chunk)} bytes)"
        )

        if tag != "equal":
            lines.append(
                f"    A bytes: {hex_preview(first_chunk)}"
            )
            lines.append(
                f"    B bytes: {hex_preview(second_chunk)}"
            )

        lines.append("")

    lines.extend(
        [
            "=" * 78,
            "INTERPRETAÇÃO SEGURA",
            (
                "O relatório identifica inserções, remoções e substituições "
                "após alinhar os dois arquivos. Ele não atribui ainda "
                "significado aos campos."
            ),
            (
                "Se a maior parte dos dados aparecer em blocos IGUAIS, "
                "a variação está concentrada em poucas regiões. Se houver "
                "muitos blocos alternados, será necessário coletar várias "
                "leituras para separar campos estáveis de campos dinâmicos."
            ),
            "",
        ]
    )

    return "\n".join(lines)


def main() -> None:
    """Carrega os dumps, analisa e salva o relatório."""
    for file_path in (DUMP_A_FILE, DUMP_B_FILE):
        if not file_path.is_file():
            raise SystemExit(
                f"Arquivo não encontrado: {file_path}"
            )

    first = DUMP_A_FILE.read_bytes()
    second = DUMP_B_FILE.read_bytes()

    report = build_report(first, second)

    REPORT_FILE.write_text(
        report,
        encoding="utf-8",
    )

    print(report)
    print("Relatório salvo em:", REPORT_FILE)


if __name__ == "__main__":
    main()