"""Mapeia onde o volume aparece no dump do preset 45B.

Fluxo controlado:
1. inicializa a sessão;
2. seleciona e confirma o preset 45B;
3. grava volume 49;
4. lê o dump A;
5. grava volume 50;
6. lê o dump B;
7. compara as seções estruturais;
8. restaura o volume 49.
"""

from __future__ import annotations

import difflib
import hashlib
import time
from pathlib import Path

import mido

from tools.analysis.analyze_preset_sections import parse_sections
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
    is_dump_complete,
    select_preset_with_confirmation,
    send_session_handshake,
)
from tools.commands.set_volume import build_volume_message


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DUMPS_DIRECTORY = PROJECT_ROOT / "data" / "dumps"

BASE_VOLUME = 49
TARGET_VOLUME = 51

WRITE_SETTLE_SECONDS = 1.0
DELAY_BETWEEN_STEPS_SECONDS = 0.5

DUMP_A_TEXT_FILE = (
    DUMPS_DIRECTORY
    / "preset_45B_volume_49.txt"
)
DUMP_A_BINARY_FILE = (
    DUMPS_DIRECTORY
    / "preset_45B_volume_49.bin"
)

DUMP_B_TEXT_FILE = (
    DUMPS_DIRECTORY
    / "preset_45B_volume_51.txt"
)
DUMP_B_BINARY_FILE = (
    DUMPS_DIRECTORY
    / "preset_45B_volume_51.bin"
)

REPORT_FILE = (
    DUMPS_DIRECTORY
    / "preset_45B_volume_49_to_51_report.txt"
)


def sha256(data: bytes) -> str:
    """Calcula o SHA-256 em letras maiúsculas."""
    return hashlib.sha256(data).hexdigest().upper()


def format_hex(data: bytes) -> str:
    """Formata bytes em hexadecimal."""
    return " ".join(
        f"{byte:02X}"
        for byte in data
    )


def save_raw_messages(
    messages: list[bytes],
    output_file: Path,
) -> None:
    """Salva fragmentos SysEx em formato textual."""
    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_file.open(
        "w",
        encoding="utf-8",
    ) as destination:
        for index, message in enumerate(
            messages,
            start=1,
        ):
            destination.write(
                f"Mensagem {index} - "
                f"{len(message)} bytes\n"
            )

            destination.write(
                " ".join(
                    f"{byte:02X}"
                    for byte in message
                )
            )

            destination.write("\n\n")


def request_dump(
    input_port,
    output_port,
    read_request: mido.Message,
    label: str,
    text_file: Path,
    binary_file: Path,
) -> bytes:
    """Solicita, valida, reconstrói e salva um dump."""
    removed = clear_pending_messages(
        input_port
    )

    if removed:
        print(
            f"Mensagens removidas antes da leitura {label}:",
            removed,
        )

    print(
        f"\nEnviando pedido da leitura {label}..."
    )

    output_port.send(
        read_request
    )

    print(
        f"Aguardando o dump da leitura {label}..."
    )

    messages = collect_dump_responses(
        input_port
    )

    if not messages:
        raise RuntimeError(
            f"Nenhum fragmento foi recebido "
            f"na leitura {label}."
        )

    if not is_dump_complete(
        messages
    ):
        raise RuntimeError(
            f"O dump da leitura {label} "
            "está incompleto."
        )

    reconstructed_data, fragment_summary = (
        reconstruct_dump(
            messages
        )
    )

    save_raw_messages(
        messages,
        text_file,
    )

    binary_file.write_bytes(
        reconstructed_data
    )

    print(
        f"\nLeitura {label} concluída."
    )

    print(
        "Tamanho reconstruído:",
        len(reconstructed_data),
        "bytes",
    )

    for offset, decoded_length in fragment_summary:
        print(
            f"Fragmento: offset {offset}, "
            f"{decoded_length} bytes"
        )

    print(
        "SHA-256:",
        sha256(
            reconstructed_data
        ),
    )

    return reconstructed_data


def write_volume(
    input_port,
    output_port,
    volume: int,
) -> None:
    """Envia o comando de volume e aguarda a pedaleira aplicar."""
    removed = clear_pending_messages(
        input_port
    )

    if removed:
        print(
            "Mensagens antigas removidas "
            "antes da escrita:",
            removed,
        )

    print(
        f"\nGravando volume {volume}..."
    )

    message = build_volume_message(
        volume
    )

    output_port.send(
        message
    )

    time.sleep(
        WRITE_SETTLE_SECONDS
    )

    removed = clear_pending_messages(
        input_port
    )

    if removed:
        print(
            "Mensagens recebidas após a escrita:",
            removed,
        )

    print(
        f"Volume {volume} aplicado."
    )


def difference_positions(
    first: bytes,
    second: bytes,
) -> list[int]:
    """Retorna as posições diferentes de seções com mesmo tamanho."""
    if len(first) != len(second):
        raise ValueError(
            "As seções comparadas possuem tamanhos diferentes."
        )

    return [
        index
        for index, (
            first_value,
            second_value,
        ) in enumerate(
            zip(
                first,
                second,
                strict=True,
            )
        )
        if first_value != second_value
    ]


def build_equal_length_section_report(
    section_name: str,
    first: bytes,
    second: bytes,
    first_absolute_start: int,
    second_absolute_start: int,
) -> list[str]:
    """Descreve diferenças de uma seção com tamanho fixo."""
    differences = difference_positions(
        first,
        second,
    )

    lines = [
        "",
        section_name,
        "-" * 78,
        f"Tamanho: {len(first)} bytes",
        f"Diferenças: {len(differences)}",
    ]

    if not differences:
        lines.append(
            "Resultado: seção idêntica."
        )

        return lines

    for relative_index in differences:
        lines.append(
            f"Índice relativo 0x{relative_index:04X} | "
            f"A absoluto 0x{first_absolute_start + relative_index:04X} | "
            f"B absoluto 0x{second_absolute_start + relative_index:04X}: "
            f"{first[relative_index]:02X} -> "
            f"{second[relative_index]:02X}"
        )

    return lines


def build_variable_section_report(
    first: bytes,
    second: bytes,
) -> list[str]:
    """Alinha e descreve a seção de tamanho variável."""
    matcher = difflib.SequenceMatcher(
        None,
        first,
        second,
        autojunk=False,
    )

    opcodes = matcher.get_opcodes()

    lines = [
        "",
        "SEÇÃO VARIÁVEL",
        "-" * 78,
        f"Tamanho A: {len(first)} bytes",
        f"Tamanho B: {len(second)} bytes",
        f"Conteúdo A: {format_hex(first)}",
        f"Conteúdo B: {format_hex(second)}",
        "",
        "Blocos alinhados:",
    ]

    for tag, a_start, a_end, b_start, b_end in opcodes:
        if tag == "equal":
            continue

        lines.append(
            f"- {tag.upper()}: "
            f"A[0x{a_start:02X}:0x{a_end:02X}] "
            f"({format_hex(first[a_start:a_end]) or '--'}) "
            f"-> "
            f"B[0x{b_start:02X}:0x{b_end:02X}] "
            f"({format_hex(second[b_start:b_end]) or '--'})"
        )

    if all(
        tag == "equal"
        for tag, *_ in opcodes
    ):
        lines.append(
            "- nenhuma diferença"
        )

    return lines


def create_report(
    dump_a: bytes,
    dump_b: bytes,
) -> str:
    """Compara todas as seções estruturais dos dois dumps."""
    sections_a = parse_sections(
        dump_a
    )
    sections_b = parse_sections(
        dump_b
    )

    prefix_a = bytes(
        sections_a["prefix"]
    )
    prefix_b = bytes(
        sections_b["prefix"]
    )

    variable_a = bytes(
        sections_a["variable"]
    )
    variable_b = bytes(
        sections_b["variable"]
    )

    core_a = bytes(
        sections_a["core"]
    )
    core_b = bytes(
        sections_b["core"]
    )

    volatile_a = bytes(
        sections_a["volatile"]
    )
    volatile_b = bytes(
        sections_b["volatile"]
    )

    suffix_a = bytes(
        sections_a["suffix"]
    )
    suffix_b = bytes(
        sections_b["suffix"]
    )

    core_start_a = int(
        sections_a["core_start"]
    )
    core_start_b = int(
        sections_b["core_start"]
    )

    volatile_start_a = (
        core_start_a
        + len(core_a)
    )
    volatile_start_b = (
        core_start_b
        + len(core_b)
    )

    suffix_start_a = (
        volatile_start_a
        + len(volatile_a)
    )
    suffix_start_b = (
        volatile_start_b
        + len(volatile_b)
    )

    lines = [
        "MAPEAMENTO DO VOLUME NO DUMP DO PRESET 45B",
        "=" * 78,
        "",
        f"Volume A: {BASE_VOLUME}",
        f"Volume B: {TARGET_VOLUME}",
        f"Tamanho A: {len(dump_a)} bytes",
        f"Tamanho B: {len(dump_b)} bytes",
        f"SHA-256 A: {sha256(dump_a)}",
        f"SHA-256 B: {sha256(dump_b)}",
        "",
        (
            "Campo de tamanho A dump[4]: "
            f"0x{dump_a[4]:02X}"
        ),
        (
            "Campo de tamanho B dump[4]: "
            f"0x{dump_b[4]:02X}"
        ),
        (
            "Início do núcleo A: "
            f"0x{core_start_a:04X}"
        ),
        (
            "Início do núcleo B: "
            f"0x{core_start_b:04X}"
        ),
    ]

    lines.extend(
        build_equal_length_section_report(
            "PREFIXO FIXO",
            prefix_a,
            prefix_b,
            0,
            0,
        )
    )

    lines.extend(
        build_variable_section_report(
            variable_a,
            variable_b,
        )
    )

    lines.extend(
        build_equal_length_section_report(
            "NÚCLEO DE 177 BYTES",
            core_a,
            core_b,
            core_start_a,
            core_start_b,
        )
    )

    lines.extend(
        build_equal_length_section_report(
            "BLOCO VOLÁTIL DE 5 BYTES",
            volatile_a,
            volatile_b,
            volatile_start_a,
            volatile_start_b,
        )
    )

    lines.extend(
        build_equal_length_section_report(
            "SUFIXO DE 27 BYTES",
            suffix_a,
            suffix_b,
            suffix_start_a,
            suffix_start_b,
        )
    )

    core_differences = difference_positions(
        core_a,
        core_b,
    )

    lines.extend(
        [
            "",
            "=" * 78,
            "CONCLUSÃO AUTOMÁTICA",
        ]
    )

    if len(core_differences) == 1:
        index = core_differences[0]

        lines.append(
            "Foi encontrada exatamente uma alteração "
            "no núcleo de 177 bytes."
        )

        lines.append(
            f"Candidato principal ao volume: "
            f"núcleo[0x{index:04X}], "
            f"{core_a[index]:02X} -> "
            f"{core_b[index]:02X}."
        )

    elif core_differences:
        lines.append(
            f"Foram encontradas {len(core_differences)} "
            "alterações no núcleo."
        )

        lines.append(
            "Será necessário repetir o teste ou cruzar "
            "com outro par de volumes."
        )

    else:
        lines.append(
            "O núcleo de 177 bytes não mudou."
        )

        lines.append(
            "O volume está em outra seção ou o comando "
            "não foi refletido neste tipo de dump."
        )

    lines.append("")

    return "\n".join(
        lines
    )


def main() -> None:
    """Executa o teste controlado de volume 49 para 50."""
    input(
        "Deixe o preset 45A selecionado e pressione "
        "Enter para iniciar o mapeamento do volume..."
    )

    select_preset = create_sysex_message(
        SELECT_PRESET_45B_HEX
    )

    read_request = create_sysex_message(
        PRESET_READ_REQUEST_HEX
    )

    volume_was_changed = False

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

            send_session_handshake(
                output_port
            )

            print(
                "\nAguardando a sessão estabilizar..."
            )

            time.sleep(
                SESSION_STABILIZATION_SECONDS
            )

            clear_pending_messages(
                input_port
            )

            confirmed = select_preset_with_confirmation(
                input_port,
                output_port,
                select_preset,
            )

            if not confirmed:
                print(
                    "\nTeste cancelado: não foi possível "
                    "confirmar o preset 45B."
                )

                return

            print(
                "\nAguardando o preset terminar "
                "de carregar..."
            )

            time.sleep(
                PRESET_LOAD_DELAY_SECONDS
            )

            try:
                write_volume(
                    input_port,
                    output_port,
                    BASE_VOLUME,
                )

                volume_was_changed = True

                time.sleep(
                    DELAY_BETWEEN_STEPS_SECONDS
                )

                dump_a = request_dump(
                    input_port,
                    output_port,
                    read_request,
                    f"A — volume {BASE_VOLUME}",
                    DUMP_A_TEXT_FILE,
                    DUMP_A_BINARY_FILE,
                )

                time.sleep(
                    DELAY_BETWEEN_STEPS_SECONDS
                )

                write_volume(
                    input_port,
                    output_port,
                    TARGET_VOLUME,
                )

                time.sleep(
                    DELAY_BETWEEN_STEPS_SECONDS
                )

                dump_b = request_dump(
                    input_port,
                    output_port,
                    read_request,
                    f"B — volume {TARGET_VOLUME}",
                    DUMP_B_TEXT_FILE,
                    DUMP_B_BINARY_FILE,
                )

                report = create_report(
                    dump_a,
                    dump_b,
                )

                REPORT_FILE.write_text(
                    report,
                    encoding="utf-8",
                )

                print(
                    "\n",
                    report,
                    sep="",
                )

                print(
                    "Relatório salvo em:",
                    REPORT_FILE,
                )

            finally:
                if volume_was_changed:
                    print(
                        f"\nRestaurando o volume "
                        f"{BASE_VOLUME}..."
                    )

                    output_port.send(
                        build_volume_message(
                            BASE_VOLUME
                        )
                    )

                    time.sleep(
                        WRITE_SETTLE_SECONDS
                    )

                    print(
                        f"Volume restaurado para "
                        f"{BASE_VOLUME}."
                    )

    except (
        OSError,
        RuntimeError,
        ValueError,
    ) as error:
        print(
            "\nErro durante o teste:",
            error,
        )

    except KeyboardInterrupt:
        print(
            "\nTeste cancelado pelo usuário."
        )


if __name__ == "__main__":
    main()