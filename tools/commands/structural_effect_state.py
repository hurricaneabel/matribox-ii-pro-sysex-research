"""Decodificação estável do estado estrutural dos efeitos da Matribox II Pro.

As respostas estruturais completas possuem três camadas:

1. mensagem SysEx com bytes codificados em nibbles;
2. contêiner ``01 00 00 10`` com fluxo comprimido LZO1X;
3. payload descomprimido de 89 bytes.

O layout descomprimido foi validado nas 34 capturas físicas das Fases 14 e 15:

- bytes 4–15: ordem visual, usando IDs internos e ``0xFF`` como vazio;
- bytes 16–27: classe por slot interno;
- bytes 28–75: 12 registros de quatro bytes;
- bytes 76–87: estado ligado/desligado por slot interno;
- byte 88: marcador do slot associado à última resposta, ou ``0xFF``.

Cada registro de efeito contém:

``modelo, auxiliar 1, auxiliar 2, seletor secundário``.

Este módulo não abre portas MIDI nem envia comandos. ``chain_order.py`` usa
este decodificador como fonte única do layout estrutural descomprimido.
"""

from __future__ import annotations

import ctypes
import ctypes.util
from dataclasses import dataclass
from typing import Callable, Final


MATRIBOX_HEADER: Final = bytes.fromhex("F0 21 25 4D 50")
CONTAINER_SIGNATURE: Final = bytes.fromhex("01 00 00 10")

DIRECTION_INDEX: Final = 8
LENGTH_UNITS_INDEX: Final = 9
DIRECTION_INCOMING: Final = 0x00
MESSAGE_OVERHEAD: Final = 14

NIBBLE_CONTAINER_START_INDEX: Final = 13
CONTAINER_HEADER_SIZE: Final = 8
DECOMPRESSED_PAYLOAD_SIZE: Final = 89
MAX_DECOMPRESSED_PAYLOAD_SIZE: Final = 4_096

MAX_INTERNAL_SLOTS: Final = 12
EMPTY_SLOT_ID: Final = 0xFF

PAYLOAD_PREFIX: Final = bytes.fromhex("00 00 04 01")
ORDER_START_INDEX: Final = 4
CLASS_START_INDEX: Final = 16
EFFECT_RECORDS_START_INDEX: Final = 28
EFFECT_RECORD_SIZE: Final = 4
BYPASS_START_INDEX: Final = 76
RESPONSE_SLOT_MARKER_INDEX: Final = 88

MODEL_OFFSET: Final = 0
AUXILIARY_1_OFFSET: Final = 1
AUXILIARY_2_OFFSET: Final = 2
SECONDARY_SELECTOR_OFFSET: Final = 3


class StructuralEffectStateError(ValueError):
    """Erro de validação ou descompressão do estado estrutural."""


@dataclass(frozen=True, slots=True)
class StructuralEffectRecord:
    """Registro estrutural de um slot interno."""

    internal_slot_id: int
    active: bool
    class_id: int | None
    model_id: int | None
    auxiliary_1: int
    auxiliary_2: int
    secondary_selector: int | None
    enabled: bool | None

    @property
    def human_slot(self) -> int:
        """Slot apresentado ao usuário, numerado de 1 a 12."""

        return self.internal_slot_id + 1


@dataclass(frozen=True, slots=True)
class StructuralEffectState:
    """Estado estrutural completamente descomprimido."""

    internal_slot_ids: tuple[int, ...]
    records: tuple[StructuralEffectRecord, ...]
    response_slot_marker: int | None
    compressed_size: int
    decompressor_backend: str
    raw_message: bytes
    decoded_container: bytes
    decompressed_payload: bytes

    @property
    def human_slots(self) -> tuple[int, ...]:
        """Ordem visual apresentada com slots humanos."""

        return tuple(
            internal_slot_id + 1
            for internal_slot_id in self.internal_slot_ids
        )

    @property
    def effect_count(self) -> int:
        """Quantidade de efeitos ativos na cadeia."""

        return len(self.internal_slot_ids)

    @property
    def active_records(self) -> tuple[StructuralEffectRecord, ...]:
        """Registros ativos na ordem dos slots internos."""

        return tuple(
            record
            for record in self.records
            if record.active
        )

    @property
    def visual_records(self) -> tuple[StructuralEffectRecord, ...]:
        """Registros ativos na ordem visual da cadeia."""

        return tuple(
            self.records[internal_slot_id]
            for internal_slot_id in self.internal_slot_ids
        )

    def record_for_internal_slot(
        self,
        internal_slot: int,
    ) -> StructuralEffectRecord:
        """Retorna o registro de um slot humano entre 1 e 12."""

        if not 1 <= internal_slot <= MAX_INTERNAL_SLOTS:
            raise IndexError("Slot interno fora do intervalo.")

        return self.records[internal_slot - 1]


def calculate_declared_message_length(
    message: bytes | bytearray,
) -> int:
    """Calcula o tamanho total declarado no índice 9."""

    if len(message) <= LENGTH_UNITS_INDEX:
        raise StructuralEffectStateError(
            "Mensagem curta demais para declarar o comprimento."
        )

    return MESSAGE_OVERHEAD + message[LENGTH_UNITS_INDEX] * 2


def _decode_nibble_container(raw_message: bytes) -> bytes:
    """Junta os pares de nibbles que formam o contêiner LZO1X."""

    encoded = raw_message[NIBBLE_CONTAINER_START_INDEX:-1]

    if len(encoded) % 2:
        raise StructuralEffectStateError(
            "A região codificada possui quantidade ímpar de nibbles."
        )

    decoded = bytearray()

    for index in range(0, len(encoded), 2):
        high_nibble = encoded[index]
        low_nibble = encoded[index + 1]

        if high_nibble > 0x0F or low_nibble > 0x0F:
            raise StructuralEffectStateError(
                "A região do contêiner contém um byte que não é nibble."
            )

        decoded.append((high_nibble << 4) | low_nibble)

    return bytes(decoded)


def _decompress_with_lzokay(
    compressed: bytes,
    expected_size: int,
) -> bytes:
    """Descomprime LZO1X usando o pacote já exigido pelo projeto."""

    import lzokay  # type: ignore[import-not-found]

    return bytes(lzokay.decompress(compressed, expected_size))


def _decompress_with_system_lzo(
    compressed: bytes,
    expected_size: int,
) -> bytes:
    """Fallback para ambientes que disponibilizam ``liblzo2``."""

    library_name = ctypes.util.find_library("lzo2")

    if library_name is None:
        raise RuntimeError("A biblioteca liblzo2 não foi localizada.")

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

    source = (ctypes.c_ubyte * len(compressed)).from_buffer_copy(compressed)
    destination = (ctypes.c_ubyte * expected_size)()
    destination_size = ctypes.c_size_t(expected_size)

    result = function(
        source,
        len(compressed),
        destination,
        ctypes.byref(destination_size),
        None,
    )

    if result != 0:
        raise StructuralEffectStateError(
            "A liblzo2 recusou o fluxo LZO1X "
            f"com código {result}."
        )

    return bytes(destination[: destination_size.value])


def _resolve_decompressor() -> tuple[
    str,
    Callable[[bytes, int], bytes],
]:
    """Seleciona lzokay e usa liblzo2 apenas como fallback."""

    try:
        import lzokay  # type: ignore[import-not-found]  # noqa: F401
    except ImportError:
        if ctypes.util.find_library("lzo2") is None:
            raise StructuralEffectStateError(
                "Nenhum descompressor LZO1X foi encontrado. "
                "Instale as dependências do requirements.txt."
            )

        return "liblzo2", _decompress_with_system_lzo

    return "lzokay", _decompress_with_lzokay


def decompress_lzo1x(
    compressed: bytes,
    *,
    maximum_output_size: int = MAX_DECOMPRESSED_PAYLOAD_SIZE,
) -> tuple[bytes, str]:
    """Descomprime um fluxo LZO1X usando o backend disponível.

    A função é compartilhada pelas respostas estruturais imediatas e pelos
    dumps completos de preset. O tamanho máximo limita a alocação sem exigir
    que o chamador conheça previamente o tamanho exato descomprimido.
    """

    if maximum_output_size <= 0:
        raise ValueError("O tamanho máximo de saída deve ser positivo.")

    backend_name, decompressor = _resolve_decompressor()

    try:
        decompressed = decompressor(
            bytes(compressed),
            maximum_output_size,
        )
    except StructuralEffectStateError:
        raise
    except Exception as error:
        raise StructuralEffectStateError(
            "O descompressor recusou o fluxo LZO1X."
        ) from error

    return bytes(decompressed), backend_name


def _decompress_container(
    decoded_container: bytes,
) -> tuple[bytes, int, str]:
    """Valida o contêiner e devolve o payload de 89 bytes."""

    if len(decoded_container) < CONTAINER_HEADER_SIZE:
        raise StructuralEffectStateError(
            "Contêiner curto demais para possuir cabeçalho."
        )

    if decoded_container[:4] != CONTAINER_SIGNATURE:
        raise StructuralEffectStateError(
            "Assinatura inesperada do contêiner estrutural: "
            f"{decoded_container[:4].hex(' ')}."
        )

    compressed_size = int.from_bytes(
        decoded_container[4:8],
        byteorder="little",
        signed=False,
    )
    compressed = decoded_container[CONTAINER_HEADER_SIZE:]

    if compressed_size != len(compressed):
        raise StructuralEffectStateError(
            "Tamanho comprimido inconsistente: "
            f"declarado={compressed_size}, real={len(compressed)}."
        )

    decompressed, backend_name = decompress_lzo1x(
        compressed,
        maximum_output_size=MAX_DECOMPRESSED_PAYLOAD_SIZE,
    )

    return decompressed, compressed_size, backend_name


def _parse_order(payload: bytes) -> tuple[int, ...]:
    """Decodifica a ordem visual dos slots internos."""

    encoded_order = payload[
        ORDER_START_INDEX : ORDER_START_INDEX + MAX_INTERNAL_SLOTS
    ]
    internal_slot_ids: list[int] = []
    seen_slots: set[int] = set()
    empty_seen = False

    for value in encoded_order:
        if value == EMPTY_SLOT_ID:
            empty_seen = True
            continue

        if empty_seen:
            raise StructuralEffectStateError(
                "A ordem possui um slot depois do primeiro marcador vazio."
            )

        if not 0 <= value < MAX_INTERNAL_SLOTS:
            raise StructuralEffectStateError(
                f"Slot interno fora do intervalo na ordem: {value}."
            )

        if value in seen_slots:
            raise StructuralEffectStateError(
                f"Slot interno repetido na ordem: {value + 1}."
            )

        seen_slots.add(value)
        internal_slot_ids.append(value)

    return tuple(internal_slot_ids)


def _parse_records(
    payload: bytes,
    internal_slot_ids: tuple[int, ...],
    *,
    strict_inactive_slots: bool = True,
) -> tuple[StructuralEffectRecord, ...]:
    """Reconstrói classe, modelo, seletor e bypass dos 12 slots.

    Respostas estruturais imediatas limpam classes dos slots inativos. Dumps
    completos podem preservar dados ocultos em slots fora da ordem visual;
    nesses casos, ``strict_inactive_slots=False`` ignora esses resíduos.
    """

    active_slot_ids = set(internal_slot_ids)
    class_ids = payload[
        CLASS_START_INDEX : CLASS_START_INDEX + MAX_INTERNAL_SLOTS
    ]
    bypass_values = payload[
        BYPASS_START_INDEX : BYPASS_START_INDEX + MAX_INTERNAL_SLOTS
    ]
    records: list[StructuralEffectRecord] = []

    for internal_slot_id in range(MAX_INTERNAL_SLOTS):
        active = internal_slot_id in active_slot_ids
        class_value = class_ids[internal_slot_id]
        bypass_value = bypass_values[internal_slot_id]
        record_start = (
            EFFECT_RECORDS_START_INDEX
            + internal_slot_id * EFFECT_RECORD_SIZE
        )
        raw_record = payload[
            record_start : record_start + EFFECT_RECORD_SIZE
        ]

        if bypass_value not in (0x00, 0x01):
            raise StructuralEffectStateError(
                "Estado de bypass inválido para o slot interno "
                f"{internal_slot_id + 1}: 0x{bypass_value:02X}."
            )

        if active:
            if class_value == EMPTY_SLOT_ID:
                raise StructuralEffectStateError(
                    "Slot ativo sem classe no slot interno "
                    f"{internal_slot_id + 1}."
                )

            class_id: int | None = class_value
            model_id: int | None = raw_record[MODEL_OFFSET]
            secondary_selector: int | None = raw_record[
                SECONDARY_SELECTOR_OFFSET
            ]
            enabled: bool | None = bool(bypass_value)
        else:
            if strict_inactive_slots and class_value != EMPTY_SLOT_ID:
                raise StructuralEffectStateError(
                    "Slot inativo com classe preenchida no slot interno "
                    f"{internal_slot_id + 1}: 0x{class_value:02X}."
                )

            class_id = None
            model_id = None
            secondary_selector = None
            enabled = None

        records.append(
            StructuralEffectRecord(
                internal_slot_id=internal_slot_id,
                active=active,
                class_id=class_id,
                model_id=model_id,
                auxiliary_1=raw_record[AUXILIARY_1_OFFSET],
                auxiliary_2=raw_record[AUXILIARY_2_OFFSET],
                secondary_selector=secondary_selector,
                enabled=enabled,
            )
        )

    return tuple(records)


def parse_decompressed_structural_payload(
    payload: bytes | bytearray,
    *,
    raw_message: bytes = b"",
    decoded_container: bytes = b"",
    compressed_size: int = 0,
    decompressor_backend: str = "already-decompressed",
    strict_inactive_slots: bool = True,
) -> StructuralEffectState:
    """Interpreta diretamente o payload estrutural fixo de 89 bytes."""

    raw_payload = bytes(payload)

    if len(raw_payload) != DECOMPRESSED_PAYLOAD_SIZE:
        raise StructuralEffectStateError(
            "Tamanho estrutural descomprimido inesperado: "
            f"{len(raw_payload)}; esperado={DECOMPRESSED_PAYLOAD_SIZE}."
        )

    if raw_payload[:4] != PAYLOAD_PREFIX:
        raise StructuralEffectStateError(
            "Prefixo estrutural inesperado: "
            f"{raw_payload[:4].hex(' ')}."
        )

    internal_slot_ids = _parse_order(raw_payload)
    records = _parse_records(
        raw_payload,
        internal_slot_ids,
        strict_inactive_slots=strict_inactive_slots,
    )

    marker_value = raw_payload[RESPONSE_SLOT_MARKER_INDEX]

    if marker_value == EMPTY_SLOT_ID:
        response_slot_marker: int | None = None
    elif 0 <= marker_value < MAX_INTERNAL_SLOTS:
        response_slot_marker = marker_value
    else:
        raise StructuralEffectStateError(
            "Marcador de resposta fora do intervalo: "
            f"0x{marker_value:02X}."
        )

    return StructuralEffectState(
        internal_slot_ids=internal_slot_ids,
        records=records,
        response_slot_marker=response_slot_marker,
        compressed_size=compressed_size,
        decompressor_backend=decompressor_backend,
        raw_message=bytes(raw_message),
        decoded_container=bytes(decoded_container),
        decompressed_payload=raw_payload,
    )


def parse_structural_effect_state(
    message: bytes | bytearray,
) -> StructuralEffectState | None:
    """Interpreta uma resposta estrutural completa de efeitos.

    Retorna ``None`` quando a mensagem não possui a estrutura externa esperada.
    Depois de reconhecer a estrutura, inconsistências internas geram
    ``StructuralEffectStateError``.
    """

    raw_message = bytes(message)

    if len(raw_message) < MESSAGE_OVERHEAD:
        return None

    if raw_message[:5] != MATRIBOX_HEADER:
        return None

    if raw_message[-1] != 0xF7:
        return None

    if raw_message[DIRECTION_INDEX] != DIRECTION_INCOMING:
        return None

    if calculate_declared_message_length(raw_message) != len(raw_message):
        return None

    if raw_message[10:13] != b"\x00\x00\x00":
        return None

    decoded_container = _decode_nibble_container(raw_message)

    # Eventos e respostas auxiliares podem compartilhar o mesmo envelope
    # externo, mas usam outra assinatura interna. Eles não são erros de cadeia.
    if decoded_container[:4] != CONTAINER_SIGNATURE:
        return None

    payload, compressed_size, backend_name = _decompress_container(
        decoded_container
    )

    if len(payload) != DECOMPRESSED_PAYLOAD_SIZE:
        return None

    if payload[:4] != PAYLOAD_PREFIX:
        return None

    return parse_decompressed_structural_payload(
        payload,
        raw_message=raw_message,
        decoded_container=decoded_container,
        compressed_size=compressed_size,
        decompressor_backend=backend_name,
        strict_inactive_slots=True,
    )
