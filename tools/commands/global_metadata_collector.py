"""Reconstrução incremental do bloco global de metadados.

A Matribox II Pro envia respostas grandes como mensagens SysEx fragmentadas.
Cada fragmento informa:

- tamanho total nos bytes 9 e 10, em base 128;
- offset nos bytes 11 e 12, em base 128;
- conteúdo a partir do byte 13, codificado em pares de nibbles.

Este módulo recebe apenas bytes já entregues pela porta MIDI. Ele não abre
portas, não envia mensagens e não depende de mido.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Iterable

from tools.commands.global_preset_metadata import OUTER_SIGNATURE


MATRIBOX_HEADER: Final = bytes.fromhex("F0 21 25 4D 50")
INCOMING_DIRECTION: Final = 0x00

DIRECTION_INDEX: Final = 8
TOTAL_LOW_INDEX: Final = 9
TOTAL_HIGH_INDEX: Final = 10
OFFSET_LOW_INDEX: Final = 11
OFFSET_HIGH_INDEX: Final = 12
PAYLOAD_START_INDEX: Final = 13

MINIMUM_GLOBAL_BLOCK_SIZE: Final = 1_000
MAXIMUM_PROTOCOL_BLOCK_SIZE: Final = 0x3FFF


class FragmentAssemblyError(ValueError):
    """Erro ao montar um bloco fragmentado."""


class FragmentConflictError(FragmentAssemblyError):
    """Dois fragmentos atribuíram valores diferentes ao mesmo byte."""


class IncompleteBlockError(FragmentAssemblyError):
    """O bloco foi solicitado antes de todos os bytes chegarem."""


@dataclass(frozen=True, slots=True)
class GlobalMetadataFragment:
    """Fragmento SysEx já convertido de nibbles para bytes."""

    total_size: int
    offset: int
    payload: bytes
    raw_message: bytes

    @property
    def end_offset(self) -> int:
        return self.offset + len(self.payload)


@dataclass(frozen=True, slots=True)
class CollectorUpdate:
    """Resultado de uma chamada ao coletor incremental."""

    fragment: GlobalMetadataFragment | None
    accepted: bool
    new_bytes: int
    covered_bytes: int
    total_size: int | None
    complete: bool
    global_block: bytes | None


def decode_nibble_pairs(encoded: bytes) -> bytes | None:
    """Converte pares de nibbles em bytes; retorna None se forem inválidos."""
    if not encoded or len(encoded) % 2 != 0:
        return None

    if any(value > 0x0F for value in encoded):
        return None

    return bytes(
        (encoded[index] << 4) | encoded[index + 1]
        for index in range(0, len(encoded), 2)
    )


def decode_global_metadata_fragment(
    message: bytes | bytearray,
) -> GlobalMetadataFragment | None:
    """Reconhece e decodifica um fragmento recebido da Matribox."""
    raw = bytes(message)

    if len(raw) < PAYLOAD_START_INDEX + 3:
        return None

    if raw[:5] != MATRIBOX_HEADER or raw[-1] != 0xF7:
        return None

    if raw[DIRECTION_INDEX] != INCOMING_DIRECTION:
        return None

    address_bytes = raw[TOTAL_LOW_INDEX:OFFSET_HIGH_INDEX + 1]
    if any(value > 0x7F for value in address_bytes):
        return None

    total_size = raw[TOTAL_LOW_INDEX] + (raw[TOTAL_HIGH_INDEX] << 7)
    offset = raw[OFFSET_LOW_INDEX] + (raw[OFFSET_HIGH_INDEX] << 7)

    if not 0 < total_size <= MAXIMUM_PROTOCOL_BLOCK_SIZE:
        return None

    payload = decode_nibble_pairs(raw[PAYLOAD_START_INDEX:-1])
    if payload is None:
        return None

    if offset >= total_size or offset + len(payload) > total_size:
        return None

    return GlobalMetadataFragment(
        total_size=total_size,
        offset=offset,
        payload=payload,
        raw_message=raw,
    )


def find_missing_ranges(coverage: bytes | bytearray) -> tuple[tuple[int, int], ...]:
    """Retorna intervalos ausentes como pares [início, fim exclusivo)."""
    missing: list[tuple[int, int]] = []
    start: int | None = None

    for index in range(len(coverage) + 1):
        absent = index < len(coverage) and coverage[index] == 0

        if absent and start is None:
            start = index
            continue

        if not absent and start is not None:
            missing.append((start, index))
            start = None

    return tuple(missing)


def is_valid_global_container(container: bytes) -> bool:
    """Valida somente a moldura externa, sem executar LZO1X."""
    if len(container) < 8 or container[:4] != OUTER_SIGNATURE:
        return False

    declared_size = int.from_bytes(container[4:8], "little")
    return declared_size == len(container) - 8


class FragmentAssembly:
    """Monta um bloco de tamanho fixo e detecta lacunas ou conflitos."""

    def __init__(self, total_size: int) -> None:
        if not 0 < total_size <= MAXIMUM_PROTOCOL_BLOCK_SIZE:
            raise ValueError(f"Tamanho total inválido: {total_size}.")

        self.total_size = total_size
        self._data = bytearray(total_size)
        self._coverage = bytearray(total_size)
        self._covered_bytes = 0
        self._fragments: dict[tuple[int, bytes], GlobalMetadataFragment] = {}

    @property
    def covered_bytes(self) -> int:
        return self._covered_bytes

    @property
    def complete(self) -> bool:
        return self._covered_bytes == self.total_size

    @property
    def fragment_count(self) -> int:
        return len(self._fragments)

    @property
    def coverage(self) -> bytes:
        return bytes(self._coverage)

    @property
    def partial_data(self) -> bytes:
        return bytes(self._data)

    @property
    def missing_ranges(self) -> tuple[tuple[int, int], ...]:
        return find_missing_ranges(self._coverage)

    def add(self, fragment: GlobalMetadataFragment) -> int:
        """Adiciona um fragmento e retorna quantos bytes eram novos."""
        if fragment.total_size != self.total_size:
            raise FragmentAssemblyError(
                "O fragmento pertence a outro tamanho total: "
                f"{fragment.total_size}; esperado={self.total_size}."
            )

        if fragment.end_offset > self.total_size:
            raise FragmentAssemblyError("O fragmento ultrapassa o bloco.")

        for relative_index, value in enumerate(fragment.payload):
            absolute_index = fragment.offset + relative_index

            if self._coverage[absolute_index]:
                if self._data[absolute_index] != value:
                    raise FragmentConflictError(
                        "Conflito no offset absoluto "
                        f"{absolute_index}: "
                        f"existente=0x{self._data[absolute_index]:02X}, "
                        f"novo=0x{value:02X}."
                    )

        new_bytes = 0

        for relative_index, value in enumerate(fragment.payload):
            absolute_index = fragment.offset + relative_index

            if not self._coverage[absolute_index]:
                self._data[absolute_index] = value
                self._coverage[absolute_index] = 1
                self._covered_bytes += 1
                new_bytes += 1

        self._fragments.setdefault(
            (fragment.offset, fragment.payload),
            fragment,
        )

        return new_bytes

    def require_complete_block(self) -> bytes:
        """Retorna o bloco completo ou informa os intervalos ausentes."""
        if not self.complete:
            raise IncompleteBlockError(
                "Bloco incompleto: "
                f"{self.covered_bytes}/{self.total_size} bytes; "
                f"lacunas={self.missing_ranges}."
            )

        return bytes(self._data)


class GlobalMetadataCollector:
    """Agrupa fragmentos recebidos e entrega o contêiner global completo."""

    def __init__(
        self,
        minimum_block_size: int = MINIMUM_GLOBAL_BLOCK_SIZE,
    ) -> None:
        if not 1 <= minimum_block_size <= MAXIMUM_PROTOCOL_BLOCK_SIZE:
            raise ValueError("Limite mínimo de bloco inválido.")

        self.minimum_block_size = minimum_block_size
        self._assemblies: dict[int, FragmentAssembly] = {}

    @property
    def assemblies(self) -> tuple[FragmentAssembly, ...]:
        return tuple(
            self._assemblies[size]
            for size in sorted(self._assemblies)
        )

    def reset(self) -> None:
        self._assemblies.clear()

    def feed(self, message: bytes | bytearray) -> CollectorUpdate:
        """Processa uma mensagem e informa o progresso da reconstrução."""
        fragment = decode_global_metadata_fragment(message)

        if fragment is None or fragment.total_size < self.minimum_block_size:
            return CollectorUpdate(
                fragment=fragment,
                accepted=False,
                new_bytes=0,
                covered_bytes=0,
                total_size=(fragment.total_size if fragment else None),
                complete=False,
                global_block=None,
            )

        assembly = self._assemblies.setdefault(
            fragment.total_size,
            FragmentAssembly(fragment.total_size),
        )

        new_bytes = assembly.add(fragment)
        global_block: bytes | None = None

        if assembly.complete:
            candidate = assembly.require_complete_block()
            if is_valid_global_container(candidate):
                global_block = candidate

        return CollectorUpdate(
            fragment=fragment,
            accepted=True,
            new_bytes=new_bytes,
            covered_bytes=assembly.covered_bytes,
            total_size=assembly.total_size,
            complete=assembly.complete,
            global_block=global_block,
        )

    def feed_many(
        self,
        messages: Iterable[bytes | bytearray],
    ) -> bytes | None:
        """Processa várias mensagens e retorna o primeiro bloco global completo."""
        for message in messages:
            update = self.feed(message)
            if update.global_block is not None:
                return update.global_block

        return None

    def best_assembly(self) -> FragmentAssembly | None:
        """Retorna a montagem com maior cobertura observada."""
        if not self._assemblies:
            return None

        return max(
            self._assemblies.values(),
            key=lambda assembly: (
                assembly.covered_bytes / assembly.total_size,
                assembly.covered_bytes,
                assembly.total_size,
            ),
        )
