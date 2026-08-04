"""Compara dumps binários de presets da Matribox II Pro."""

from __future__ import annotations

from itertools import combinations
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DUMPS_DIRECTORY = PROJECT_ROOT / "data" / "dumps"

DUMP_FILES = (
    DUMPS_DIRECTORY / "preset_45B_original.bin",
    DUMPS_DIRECTORY / "preset_45B_11_effects_initialized.bin",
    DUMPS_DIRECTORY / "preset_45B_combined_run_292bytes.bin",
    DUMPS_DIRECTORY / "preset_45B_single_session_286bytes.bin",
)

REPORT_FILE = (
    DUMPS_DIRECTORY
    / "preset_45B_comparison_report.txt"
)


def load_dumps() -> dict[Path, bytes]:
    """Carrega todos os dumps configurados."""
    dumps: dict[Path, bytes] = {}

    for file_path in DUMP_FILES:
        if not file_path.is_file():
            raise FileNotFoundError(
                f"Arquivo não encontrado: {file_path}"
            )

        dumps[file_path] = file_path.read_bytes()

    return dumps


def find_first_difference(
    first_data: bytes,
    second_data: bytes,
) -> int | None:
    """Retorna o primeiro índice diferente entre dois dumps."""
    overlap_size = min(
        len(first_data),
        len(second_data),
    )

    for index in range(overlap_size):
        if first_data[index] != second_data[index]:
            return index

    if len(first_data) != len(second_data):
        return overlap_size

    return None


def find_common_prefix_length(
    dump_values: list[bytes],
) -> int:
    """Calcula quantos bytes iniciais são iguais em todos os dumps."""
    shortest_size = min(
        len(data)
        for data in dump_values
    )

    for index in range(shortest_size):
        values = {
            data[index]
            for data in dump_values
        }

        if len(values) != 1:
            return index

    return shortest_size


def find_difference_ranges(
    reference_data: bytes,
    compared_data: bytes,
) -> list[tuple[int, int]]:
    """Agrupa posições diferentes em intervalos contínuos."""
    maximum_size = max(
        len(reference_data),
        len(compared_data),
    )

    difference_indexes: list[int] = []

    for index in range(maximum_size):
        reference_value = (
            reference_data[index]
            if index < len(reference_data)
            else None
        )

        compared_value = (
            compared_data[index]
            if index < len(compared_data)
            else None
        )

        if reference_value != compared_value:
            difference_indexes.append(
                index
            )

    if not difference_indexes:
        return []

    ranges: list[tuple[int, int]] = []

    range_start = difference_indexes[0]
    previous_index = difference_indexes[0]

    for index in difference_indexes[1:]:
        if index != previous_index + 1:
            ranges.append(
                (
                    range_start,
                    previous_index,
                )
            )

            range_start = index

        previous_index = index

    ranges.append(
        (
            range_start,
            previous_index,
        )
    )

    return ranges


def format_value(
    data: bytes,
    index: int,
) -> str:
    """Formata um byte ou indica ausência naquele índice."""
    if index >= len(data):
        return "--"

    return f"{data[index]:02X}"


def create_pair_report(
    first_path: Path,
    first_data: bytes,
    second_path: Path,
    second_data: bytes,
) -> list[str]:
    """Cria o relatório comparativo de um par de dumps."""
    overlap_size = min(
        len(first_data),
        len(second_data),
    )

    different_positions = [
        index
        for index in range(overlap_size)
        if first_data[index] != second_data[index]
    ]

    equal_positions = (
        overlap_size
        - len(different_positions)
    )

    first_difference = find_first_difference(
        first_data,
        second_data,
    )

    difference_ranges = find_difference_ranges(
        first_data,
        second_data,
    )

    lines = [
        "",
        "=" * 78,
        f"{first_path.name}",
        "versus",
        f"{second_path.name}",
        "-" * 78,
        f"Tamanho do primeiro: {len(first_data)} bytes",
        f"Tamanho do segundo: {len(second_data)} bytes",
        f"Área sobreposta: {overlap_size} bytes",
        f"Bytes iguais na área sobreposta: {equal_positions}",
        (
            "Bytes diferentes na área sobreposta: "
            f"{len(different_positions)}"
        ),
    ]

    if first_difference is None:
        lines.append(
            "Primeira diferença: nenhuma"
        )
    else:
        lines.append(
            "Primeira diferença: "
            f"índice decimal {first_difference}, "
            f"hexadecimal 0x{first_difference:04X}"
        )

        lines.append(
            "Valores nessa posição: "
            f"{format_value(first_data, first_difference)} "
            f"versus "
            f"{format_value(second_data, first_difference)}"
        )

    lines.append(
        "Intervalos diferentes:"
    )

    if not difference_ranges:
        lines.append(
            "  nenhum"
        )
    else:
        for start, end in difference_ranges:
            length = (
                end
                - start
                + 1
            )

            lines.append(
                f"  0x{start:04X} até 0x{end:04X} "
                f"({length} bytes)"
            )

    return lines


def create_report(
    dumps: dict[Path, bytes],
) -> str:
    """Monta o relatório completo."""
    dump_items = list(
        dumps.items()
    )

    common_prefix_length = (
        find_common_prefix_length(
            [
                data
                for _, data in dump_items
            ]
        )
    )

    lines = [
        "COMPARAÇÃO DOS DUMPS DO PRESET 45B",
        "=" * 78,
        "",
        "Arquivos analisados:",
    ]

    for file_path, data in dump_items:
        lines.append(
            f"- {file_path.name}: {len(data)} bytes"
        )

    lines.extend(
        [
            "",
            (
                "Prefixo idêntico entre todos os dumps: "
                f"{common_prefix_length} bytes"
            ),
            (
                "Primeiro índice potencialmente variável: "
                f"0x{common_prefix_length:04X}"
            ),
        ]
    )

    for (
        first_path,
        first_data,
    ), (
        second_path,
        second_data,
    ) in combinations(
        dump_items,
        2,
    ):
        lines.extend(
            create_pair_report(
                first_path,
                first_data,
                second_path,
                second_data,
            )
        )

    lines.extend(
        [
            "",
            "=" * 78,
            "Observação:",
            (
                "Diferenças de tamanho ou conteúdo ainda não provam "
                "qual campo representa efeitos, parâmetros ou ordem visual."
            ),
            (
                "Este relatório apenas identifica onde os dumps "
                "permanecem iguais e onde começam a divergir."
            ),
            "",
        ]
    )

    return "\n".join(
        lines
    )


def main() -> None:
    """Executa a comparação e salva o relatório."""
    try:
        dumps = load_dumps()

        report = create_report(
            dumps
        )

        REPORT_FILE.write_text(
            report,
            encoding="utf-8",
        )

        print(
            report
        )

        print(
            "Relatório salvo em:",
            REPORT_FILE,
        )

    except (
        FileNotFoundError,
        OSError,
    ) as error:
        raise SystemExit(
            f"Erro: {error}"
        ) from error


if __name__ == "__main__":
    main()