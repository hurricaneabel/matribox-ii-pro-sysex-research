"""Leitura estável da tabela global de presets da Matribox II Pro.

O bloco global recebido durante a inicialização contém um contêiner LZO1X.
Após a descompressão, ele possui 7.444 bytes e contém:

- 240 identificadores de preset, com 4 bytes cada;
- 240 nomes de preset, com 17 bytes cada;
- 240 etiquetas/filtros, com 10 bytes cada.

Este módulo não abre portas MIDI e não envia comandos à pedaleira.
"""

from __future__ import annotations

import ctypes
import ctypes.util
from dataclasses import dataclass
from pathlib import Path
import re
import struct
from typing import Callable, Iterator


OUTER_SIGNATURE = bytes.fromhex("01 00 00 10")
OUTER_HEADER_SIZE = 8

INNER_SIGNATURE = bytes.fromhex("00 00 0A 01")
DECOMPRESSED_SIZE = 7_444

PRESET_COUNT = 240
PRESETS_PER_BANK = 4
PRESET_LETTERS = "ABCD"

PRESET_ID_SIZE = 4
PRESET_NAME_SIZE = 17
PRESET_FILTER_TAG_SIZE = 10

PRESET_IDS_OFFSET = 4
PRESET_NAMES_OFFSET = (
    PRESET_IDS_OFFSET
    + PRESET_COUNT * PRESET_ID_SIZE
)
PRESET_FILTER_TAGS_OFFSET = (
    PRESET_NAMES_OFFSET
    + PRESET_COUNT * PRESET_NAME_SIZE
)
EXPECTED_END_OFFSET = (
    PRESET_FILTER_TAGS_OFFSET
    + PRESET_COUNT * PRESET_FILTER_TAG_SIZE
)

_PRESET_LABEL_PATTERN = re.compile(
    r"^(?P<bank>\d{1,2})(?P<letter>[ABCDabcd])$"
)


class GlobalPresetMetadataError(ValueError):
    """Erro de validação ou decodificação do bloco global."""


@dataclass(frozen=True, slots=True)
class PresetMetadata:
    """Metadados de um único preset."""

    index: int
    label: str
    preset_id: int
    name: str
    filter_tag: str
    raw_name: bytes
    raw_filter_tag: bytes


@dataclass(frozen=True, slots=True)
class GlobalPresetMetadata:
    """Tabela imutável contendo os 240 presets."""

    presets: tuple[PresetMetadata, ...]
    decompressor_backend: str

    def __post_init__(self) -> None:
        if len(self.presets) != PRESET_COUNT:
            raise GlobalPresetMetadataError(
                "A tabela deve conter exatamente "
                f"{PRESET_COUNT} presets."
            )

    def by_index(self, index: int) -> PresetMetadata:
        """Retorna um preset pelo índice absoluto de 0 a 239."""
        if not 0 <= index < PRESET_COUNT:
            raise IndexError(
                f"Índice de preset fora do intervalo: {index}."
            )

        return self.presets[index]

    def by_label(self, label: str) -> PresetMetadata:
        """Retorna um preset pelo rótulo, como 01A ou 45B."""
        return self.by_index(
            preset_label_to_index(label)
        )

    def __iter__(self) -> Iterator[PresetMetadata]:
        return iter(self.presets)


def preset_index_to_label(index: int) -> str:
    """Converte índice absoluto para banco/letra."""
    if not 0 <= index < PRESET_COUNT:
        raise ValueError(
            f"Índice de preset fora do intervalo: {index}."
        )

    bank = index // PRESETS_PER_BANK + 1
    letter = PRESET_LETTERS[
        index % PRESETS_PER_BANK
    ]

    return f"{bank:02d}{letter}"


def preset_label_to_index(label: str) -> int:
    """Converte banco/letra para índice absoluto."""
    match = _PRESET_LABEL_PATTERN.fullmatch(
        label.strip()
    )

    if match is None:
        raise ValueError(
            "Preset inválido. Use o formato 01A até 60D."
        )

    bank = int(match.group("bank"))
    letter = match.group("letter").upper()

    if not 1 <= bank <= 60:
        raise ValueError(
            "Banco fora do intervalo de 01 a 60."
        )

    return (
        (bank - 1) * PRESETS_PER_BANK
        + PRESET_LETTERS.index(letter)
    )


def _decode_zero_terminated_ascii(
    record: bytes,
    field_name: str,
    preset_label: str,
) -> str:
    visible = record.split(
        b"\x00",
        1,
    )[0]

    try:
        text = visible.decode("ascii")
    except UnicodeDecodeError as error:
        raise GlobalPresetMetadataError(
            f"{field_name} do preset {preset_label} "
            "não contém ASCII válido."
        ) from error

    if any(
        not 0x20 <= value <= 0x7E
        for value in visible
    ):
        raise GlobalPresetMetadataError(
            f"{field_name} do preset {preset_label} "
            "contém caractere de controle inesperado."
        )

    return text


def _decompress_with_lzokay(
    compressed: bytes,
    expected_size: int,
) -> bytes:
    try:
        import lzokay  # type: ignore[import-not-found]
    except ImportError as error:
        raise RuntimeError(
            "O pacote lzokay não está instalado."
        ) from error

    try:
        output = lzokay.decompress(
            compressed,
            expected_size,
        )
    except Exception as error:
        raise GlobalPresetMetadataError(
            "O lzokay recusou o fluxo LZO1X."
        ) from error

    return bytes(output)


def _decompress_with_system_lzo(
    compressed: bytes,
    expected_size: int,
) -> bytes:
    library_name = ctypes.util.find_library("lzo2")

    if library_name is None:
        raise RuntimeError(
            "A biblioteca liblzo2 não foi localizada."
        )

    library = ctypes.CDLL(library_name)
    function = library.lzo1x_decompress_safe

    function.argtypes = [
        ctypes.c_void_p,
        ctypes.c_size_t,
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_size_t),
        ctypes.c_void_p,
    ]
    function.restype = ctypes.c_int

    source_buffer = (
        ctypes.c_ubyte * len(compressed)
    ).from_buffer_copy(compressed)

    output_buffer = (
        ctypes.c_ubyte * expected_size
    )()

    output_length = ctypes.c_size_t(
        expected_size
    )

    result = function(
        source_buffer,
        len(compressed),
        output_buffer,
        ctypes.byref(output_length),
        None,
    )

    if result != 0:
        raise GlobalPresetMetadataError(
            "A liblzo2 recusou o fluxo LZO1X: "
            f"código {result}."
        )

    return bytes(
        output_buffer[:output_length.value]
    )


def _resolve_decompressor() -> tuple[
    str,
    Callable[[bytes, int], bytes],
]:
    try:
        import lzokay  # type: ignore[import-not-found]  # noqa: F401
    except ImportError:
        if ctypes.util.find_library("lzo2") is not None:
            return (
                "liblzo2",
                _decompress_with_system_lzo,
            )

        raise RuntimeError(
            "Nenhum descompressor LZO1X foi encontrado. "
            "Instale lzokay==1.1.8."
        )

    return (
        "lzokay",
        _decompress_with_lzokay,
    )


def decompress_global_block(
    container: bytes,
) -> tuple[bytes, str]:
    """Valida e descomprime o contêiner global."""
    if len(container) < OUTER_HEADER_SIZE:
        raise GlobalPresetMetadataError(
            "Bloco global curto demais."
        )

    signature = container[:4]

    if signature != OUTER_SIGNATURE:
        raise GlobalPresetMetadataError(
            "Assinatura externa inesperada: "
            f"{signature.hex(' ')}."
        )

    declared_compressed_size = struct.unpack_from(
        "<I",
        container,
        4,
    )[0]

    compressed = container[OUTER_HEADER_SIZE:]

    if declared_compressed_size != len(compressed):
        raise GlobalPresetMetadataError(
            "Tamanho comprimido divergente: "
            f"declarado={declared_compressed_size}, "
            f"real={len(compressed)}."
        )

    backend_name, decompressor = (
        _resolve_decompressor()
    )

    decompressed = decompressor(
        compressed,
        DECOMPRESSED_SIZE,
    )

    if len(decompressed) != DECOMPRESSED_SIZE:
        raise GlobalPresetMetadataError(
            "Tamanho descomprimido inesperado: "
            f"{len(decompressed)}; "
            f"esperado={DECOMPRESSED_SIZE}."
        )

    return (
        decompressed,
        backend_name,
    )


def parse_decompressed_global_metadata(
    decompressed: bytes,
    *,
    validate_ids: bool = True,
    decompressor_backend: str = "already-decompressed",
) -> GlobalPresetMetadata:
    """Analisa os 7.444 bytes já descomprimidos."""
    if len(decompressed) != DECOMPRESSED_SIZE:
        raise GlobalPresetMetadataError(
            "Tamanho interno inesperado: "
            f"{len(decompressed)}; "
            f"esperado={DECOMPRESSED_SIZE}."
        )

    if decompressed[:4] != INNER_SIGNATURE:
        raise GlobalPresetMetadataError(
            "Assinatura interna inesperada: "
            f"{decompressed[:4].hex(' ')}."
        )

    if EXPECTED_END_OFFSET != len(decompressed):
        raise AssertionError(
            "As constantes do layout não fecham "
            "com o tamanho interno."
        )

    presets: list[PresetMetadata] = []

    for index in range(PRESET_COUNT):
        label = preset_index_to_label(index)

        preset_id_offset = (
            PRESET_IDS_OFFSET
            + index * PRESET_ID_SIZE
        )

        preset_id = struct.unpack_from(
            "<I",
            decompressed,
            preset_id_offset,
        )[0]

        expected_preset_id = index + 2

        if (
            validate_ids
            and preset_id != expected_preset_id
        ):
            raise GlobalPresetMetadataError(
                f"ID inesperado no preset {label}: "
                f"{preset_id}; "
                f"esperado={expected_preset_id}."
            )

        name_offset = (
            PRESET_NAMES_OFFSET
            + index * PRESET_NAME_SIZE
        )

        filter_tag_offset = (
            PRESET_FILTER_TAGS_OFFSET
            + index * PRESET_FILTER_TAG_SIZE
        )

        raw_name = decompressed[
            name_offset:
            name_offset + PRESET_NAME_SIZE
        ]

        raw_filter_tag = decompressed[
            filter_tag_offset:
            filter_tag_offset + PRESET_FILTER_TAG_SIZE
        ]

        name = _decode_zero_terminated_ascii(
            record=raw_name,
            field_name="Nome",
            preset_label=label,
        )

        filter_tag = _decode_zero_terminated_ascii(
            record=raw_filter_tag,
            field_name="Etiqueta",
            preset_label=label,
        )

        presets.append(
            PresetMetadata(
                index=index,
                label=label,
                preset_id=preset_id,
                name=name,
                filter_tag=filter_tag,
                raw_name=raw_name,
                raw_filter_tag=raw_filter_tag,
            )
        )

    return GlobalPresetMetadata(
        presets=tuple(presets),
        decompressor_backend=decompressor_backend,
    )


def decode_global_preset_metadata(
    container: bytes,
    *,
    validate_ids: bool = True,
) -> GlobalPresetMetadata:
    """Descomprime e analisa um bloco global completo."""
    decompressed, backend_name = (
        decompress_global_block(container)
    )

    return parse_decompressed_global_metadata(
        decompressed,
        validate_ids=validate_ids,
        decompressor_backend=backend_name,
    )


def decode_global_preset_metadata_file(
    path: str | Path,
    *,
    validate_ids: bool = True,
) -> GlobalPresetMetadata:
    """Lê um arquivo *_global.bin e retorna a tabela."""
    source = Path(path)

    try:
        container = source.read_bytes()
    except OSError as error:
        raise GlobalPresetMetadataError(
            f"Não foi possível ler: {source}."
        ) from error

    return decode_global_preset_metadata(
        container,
        validate_ids=validate_ids,
    )
