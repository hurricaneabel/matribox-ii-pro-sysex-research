"""Confirma o campo de volume por uma assinatura estável no dump."""

from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DUMPS_DIRECTORY = PROJECT_ROOT / "data" / "dumps"

DUMP_49_FILE = DUMPS_DIRECTORY / "preset_45B_volume_49.bin"
DUMP_51_FILE = DUMPS_DIRECTORY / "preset_45B_volume_51.bin"

# O byte de volume fica entre estas duas sequências.
VOLUME_PREFIX = bytes.fromhex(
    "FC EC 00 7C 43 AF 00"
)

VOLUME_SUFFIX = bytes.fromhex(
    "00 78 A2 01 10 5F 9C 00"
)


def locate_volume(data: bytes) -> tuple[int, int]:
    """Localiza um único campo de volume usando prefixo e sufixo."""
    matches: list[tuple[int, int]] = []

    search_start = 0

    while True:
        prefix_index = data.find(
            VOLUME_PREFIX,
            search_start,
        )

        if prefix_index == -1:
            break

        volume_index = (
            prefix_index
            + len(VOLUME_PREFIX)
        )

        suffix_start = volume_index + 1
        suffix_end = (
            suffix_start
            + len(VOLUME_SUFFIX)
        )

        if (
            suffix_end <= len(data)
            and data[suffix_start:suffix_end]
            == VOLUME_SUFFIX
        ):
            volume = data[volume_index]

            if 0 <= volume <= 100:
                matches.append(
                    (
                        volume_index,
                        volume,
                    )
                )

        search_start = prefix_index + 1

    if not matches:
        raise ValueError(
            "A assinatura do volume não foi encontrada."
        )

    if len(matches) > 1:
        indexes = ", ".join(
            f"0x{index:04X}"
            for index, _ in matches
        )

        raise ValueError(
            "Foram encontradas várias assinaturas "
            f"de volume: {indexes}."
        )

    return matches[0]


def inspect_dump(
    file_path: Path,
) -> tuple[int, int]:
    """Carrega um dump e mostra a posição e o valor do volume."""
    if not file_path.is_file():
        raise FileNotFoundError(
            f"Arquivo não encontrado: {file_path}"
        )

    data = file_path.read_bytes()
    volume_index, volume = locate_volume(
        data
    )

    print(
        f"Arquivo: {file_path.name}"
    )

    print(
        f"Tamanho: {len(data)} bytes"
    )

    print(
        "Índice absoluto do volume:",
        f"0x{volume_index:04X}",
    )

    print(
        "Valor hexadecimal:",
        f"0x{volume:02X}",
    )

    print(
        "Volume decimal:",
        volume,
    )

    print()

    return volume_index, volume


def main() -> None:
    """Confirma os volumes 49 e 51 nos dumps já coletados."""
    try:
        index_49, volume_49 = inspect_dump(
            DUMP_49_FILE
        )

        index_51, volume_51 = inspect_dump(
            DUMP_51_FILE
        )

        print(
            "RESULTADO"
        )

        print(
            "Deslocamento entre os índices:",
            index_51 - index_49,
        )

        print(
            "Diferença entre os volumes:",
            volume_51 - volume_49,
        )

        if volume_49 == 49 and volume_51 == 51:
            print(
                "Campo de volume confirmado pela assinatura."
            )
        else:
            print(
                "Os valores encontrados não correspondem "
                "aos volumes esperados."
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