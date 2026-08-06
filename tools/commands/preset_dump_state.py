"""Leitura da cadeia de efeitos a partir do dump completo de um preset.

A Matribox não envia espontaneamente a resposta estrutural completa quando o
usuário apenas troca de preset. O editor oficial solicita um dump específico do
preset. Esse dump possui duas camadas:

1. fragmentos SysEx codificados em pares de nibbles;
2. contêiner LZO1X ``00 00 00 10``;
3. payload descomprimido fixo de 1.211 bytes.

O payload de 1.211 bytes contém os mesmos campos estruturais validados nas
Fases 14–18:

- bytes 185–260: prefixo, ordem, classes e registros de efeito;
- bytes 993–1004: bypass dos doze slots.

Este módulo constrói a consulta, monta os fragmentos e devolve um
``ChainOrderState`` sem movimentar, substituir ou salvar qualquer efeito.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Iterable

from tools.commands.chain_order import (
    ChainOrderState,
    chain_order_state_from_structural_state,
)
from tools.commands.global_metadata_collector import (
    FragmentAssembly,
    FragmentConflictError,
    GlobalMetadataFragment,
    decode_global_metadata_fragment,
)
from tools.commands.preset_state import (
    CHECKSUM_INDEX,
    calculate_protocol_checksum,
    encode_preset_index,
    normalize_preset,
)
from tools.commands.structural_effect_state import (
    StructuralEffectStateError,
    decompress_lzo1x,
    parse_decompressed_structural_payload,
)


PRESET_DUMP_QUERY_TEMPLATE: Final = bytes.fromhex(
    "F0 21 25 4D 50 00 00 1D 11 10 "
    "00 00 00 00 00 00 00 00 00 01 "
    "00 00 08 00 00 00 00 00 00 01 "
    "05 0B 01 00 00 00 00 00 00 01 "
    "01 00 00 00 00 F7"
)

DUMP_QUERY_HIGH_INDEX: Final = 31
DUMP_QUERY_LOW_INDEX: Final = 32
EXPECTED_DUMP_QUERY_LENGTH: Final = 46

PRESET_DUMP_SIGNATURE: Final = bytes.fromhex("00 00 00 10")
PRESET_DUMP_HEADER_SIZE: Final = 8
MINIMUM_PRESET_DUMP_SIZE: Final = 100
MAXIMUM_PRESET_DUMP_SIZE: Final = 2_048
PRESET_DUMP_DECOMPRESSED_SIZE: Final = 1_211
MAXIMUM_PRESET_DUMP_DECOMPRESSED_SIZE: Final = 4_096

STRUCTURAL_HEAD_OFFSET: Final = 185
STRUCTURAL_HEAD_SIZE: Final = 76
STRUCTURAL_BYPASS_OFFSET: Final = 993
STRUCTURAL_BYPASS_SIZE: Final = 12
STRUCTURAL_RESPONSE_MARKER: Final = 0xFF


class PresetDumpStateError(ValueError):
    """Erro na consulta, montagem ou leitura estrutural do dump."""


@dataclass(frozen=True, slots=True)
class PresetDumpCollectorUpdate:
    """Resultado incremental da montagem de um dump de preset."""

    fragment: GlobalMetadataFragment | None
    accepted: bool
    new_bytes: int
    covered_bytes: int
    total_size: int | None
    complete: bool
    preset_dump: bytes | None


def build_preset_dump_query(
    preset: str | int,
) -> bytes:
    """Monta o pedido de dump validado para qualquer preset 01A–60D."""

    preset_index, _label = normalize_preset(preset)
    high_nibble, low_nibble = encode_preset_index(preset_index)

    query = bytearray(PRESET_DUMP_QUERY_TEMPLATE)
    query[DUMP_QUERY_HIGH_INDEX] = high_nibble
    query[DUMP_QUERY_LOW_INDEX] = low_nibble
    query[CHECKSUM_INDEX] = 0
    query[CHECKSUM_INDEX] = calculate_protocol_checksum(query)

    if len(query) != EXPECTED_DUMP_QUERY_LENGTH:
        raise AssertionError("A consulta de dump perdeu o tamanho validado.")

    return bytes(query)


def is_valid_preset_dump_container(container: bytes) -> bool:
    """Valida a moldura externa comprimida do dump de preset."""

    if len(container) < PRESET_DUMP_HEADER_SIZE:
        return False

    if container[:4] != PRESET_DUMP_SIGNATURE:
        return False

    declared_size = int.from_bytes(container[4:8], "little")
    return declared_size == len(container) - PRESET_DUMP_HEADER_SIZE


class PresetDumpCollector:
    """Monta somente respostas fragmentadas de dumps individuais."""

    def __init__(self) -> None:
        self._assembly: FragmentAssembly | None = None

    @property
    def assembly(self) -> FragmentAssembly | None:
        return self._assembly

    def reset(self) -> None:
        self._assembly = None

    def feed(
        self,
        message: bytes | bytearray,
    ) -> PresetDumpCollectorUpdate:
        fragment = decode_global_metadata_fragment(message)

        if (
            fragment is None
            or not MINIMUM_PRESET_DUMP_SIZE
            <= fragment.total_size
            <= MAXIMUM_PRESET_DUMP_SIZE
        ):
            return PresetDumpCollectorUpdate(
                fragment=fragment,
                accepted=False,
                new_bytes=0,
                covered_bytes=(
                    self._assembly.covered_bytes
                    if self._assembly is not None
                    else 0
                ),
                total_size=(
                    self._assembly.total_size
                    if self._assembly is not None
                    else None
                ),
                complete=False,
                preset_dump=None,
            )

        if self._assembly is None:
            self._assembly = FragmentAssembly(fragment.total_size)

        if fragment.total_size != self._assembly.total_size:
            return PresetDumpCollectorUpdate(
                fragment=fragment,
                accepted=False,
                new_bytes=0,
                covered_bytes=self._assembly.covered_bytes,
                total_size=self._assembly.total_size,
                complete=self._assembly.complete,
                preset_dump=None,
            )

        try:
            new_bytes = self._assembly.add(fragment)
        except FragmentConflictError as error:
            raise PresetDumpStateError(str(error)) from error

        preset_dump: bytes | None = None

        if self._assembly.complete:
            candidate = self._assembly.require_complete_block()

            if is_valid_preset_dump_container(candidate):
                preset_dump = candidate
            else:
                raise PresetDumpStateError(
                    "O bloco montado não possui a moldura de dump esperada."
                )

        return PresetDumpCollectorUpdate(
            fragment=fragment,
            accepted=True,
            new_bytes=new_bytes,
            covered_bytes=self._assembly.covered_bytes,
            total_size=self._assembly.total_size,
            complete=self._assembly.complete,
            preset_dump=preset_dump,
        )

    def feed_many(
        self,
        messages: Iterable[bytes | bytearray],
    ) -> bytes | None:
        for message in messages:
            update = self.feed(message)

            if update.preset_dump is not None:
                return update.preset_dump

        return None


def decompress_preset_dump(
    container: bytes | bytearray,
) -> tuple[bytes, str]:
    """Descomprime e valida o payload fixo de 1.211 bytes."""

    raw_container = bytes(container)

    if not is_valid_preset_dump_container(raw_container):
        raise PresetDumpStateError(
            "Contêiner de dump inválido ou tamanho comprimido divergente."
        )

    compressed = raw_container[PRESET_DUMP_HEADER_SIZE:]

    try:
        decompressed, backend_name = decompress_lzo1x(
            compressed,
            maximum_output_size=(
                MAXIMUM_PRESET_DUMP_DECOMPRESSED_SIZE
            ),
        )
    except StructuralEffectStateError as error:
        raise PresetDumpStateError(str(error)) from error

    if len(decompressed) != PRESET_DUMP_DECOMPRESSED_SIZE:
        raise PresetDumpStateError(
            "Tamanho descomprimido inesperado para o preset: "
            f"{len(decompressed)}; "
            f"esperado={PRESET_DUMP_DECOMPRESSED_SIZE}."
        )

    return decompressed, backend_name


def extract_structural_payload_from_preset_dump(
    decompressed_dump: bytes | bytearray,
) -> bytes:
    """Reconstrói o payload estrutural comum de 89 bytes."""

    raw_dump = bytes(decompressed_dump)

    if len(raw_dump) != PRESET_DUMP_DECOMPRESSED_SIZE:
        raise PresetDumpStateError(
            "O dump descomprimido não possui 1.211 bytes."
        )

    structural_head = raw_dump[
        STRUCTURAL_HEAD_OFFSET:
        STRUCTURAL_HEAD_OFFSET + STRUCTURAL_HEAD_SIZE
    ]
    bypass = raw_dump[
        STRUCTURAL_BYPASS_OFFSET:
        STRUCTURAL_BYPASS_OFFSET + STRUCTURAL_BYPASS_SIZE
    ]

    if len(structural_head) != STRUCTURAL_HEAD_SIZE:
        raise PresetDumpStateError("Cabeçalho estrutural incompleto no dump.")

    if len(bypass) != STRUCTURAL_BYPASS_SIZE:
        raise PresetDumpStateError("Campo de bypass incompleto no dump.")

    return structural_head + bypass + bytes((STRUCTURAL_RESPONSE_MARKER,))


def decode_chain_state_from_preset_dump(
    container: bytes | bytearray,
) -> ChainOrderState:
    """Extrai ordem, efeitos e bypass do dump completo de um preset."""

    raw_container = bytes(container)
    decompressed_dump, backend_name = decompress_preset_dump(raw_container)
    structural_payload = extract_structural_payload_from_preset_dump(
        decompressed_dump
    )

    try:
        structural_state = parse_decompressed_structural_payload(
            structural_payload,
            raw_message=raw_container,
            decoded_container=raw_container,
            compressed_size=len(raw_container) - PRESET_DUMP_HEADER_SIZE,
            decompressor_backend=backend_name,
            # Alguns presets preservam dados ocultos em slots fora da ordem.
            strict_inactive_slots=False,
        )
    except StructuralEffectStateError as error:
        raise PresetDumpStateError(str(error)) from error

    return chain_order_state_from_structural_state(
        structural_state,
        raw_message=raw_container,
    )
