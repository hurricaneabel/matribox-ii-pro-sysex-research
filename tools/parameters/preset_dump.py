"""Hidratação somente leitura de parâmetros salvos no dump ``0x10``.

Capturas físicas confirmaram um bloco fixo de 720 bytes no payload
descomprimido: doze slots internos de 60 bytes, com quinze valores ``float32``
little-endian por slot. A posição dentro do slot é o ``parameter_selector`` do
catálogo, inclusive quando existem lacunas entre seletores.
"""

from __future__ import annotations

import math
import struct
from typing import Final

from tools.catalog import EffectCatalog, load_effect_catalog
from tools.commands.chain_order import ChainOrderState
from tools.parameters.codecs import ParameterCodecError, normalize_parameter_value
from tools.parameters.decoder import EffectParameterEvent


PRESET_PARAMETER_BLOCK_OFFSET: Final = 273
PRESET_PARAMETER_SLOT_SIZE: Final = 60
PRESET_PARAMETER_VALUE_SIZE: Final = 4
PRESET_PARAMETER_VALUES_PER_SLOT: Final = 15
PRESET_PARAMETER_SLOT_COUNT: Final = 12
PRESET_PARAMETER_BLOCK_SIZE: Final = (
    PRESET_PARAMETER_SLOT_SIZE * PRESET_PARAMETER_SLOT_COUNT
)
PRESET_PARAMETER_BLOCK_END: Final = (
    PRESET_PARAMETER_BLOCK_OFFSET + PRESET_PARAMETER_BLOCK_SIZE
)


class PresetParameterDumpError(ValueError):
    """Dump descomprimido incompatível com o layout físico confirmado."""


def _effect_for_record(catalog: EffectCatalog, record):
    if (
        record.class_id is None
        or record.model_id is None
        or record.secondary_selector is None
    ):
        return None, None
    try:
        effect_class = catalog.class_by_id(record.class_id)
    except KeyError:
        return None, None
    exact = tuple(
        effect
        for effect in effect_class.models
        if effect.model_id == record.model_id
        and effect.secondary_selector == record.secondary_selector
    )
    if len(exact) == 1:
        return effect_class, exact[0]
    by_model = tuple(
        effect for effect in effect_class.models
        if effect.model_id == record.model_id
    )
    if len(by_model) == 1:
        return effect_class, by_model[0]
    return effect_class, None


def _selector(parameter) -> int | None:
    selector = parameter.message_match.get("parameter_selector")
    if (
        isinstance(selector, bool)
        or not isinstance(selector, int)
        or not 0 <= selector < PRESET_PARAMETER_VALUES_PER_SLOT
    ):
        return None
    return selector


def decode_saved_parameter_events(
    decompressed_dump: bytes | bytearray,
    chain_state: ChainOrderState,
    catalog: EffectCatalog | None = None,
) -> tuple[EffectParameterEvent, ...]:
    """Decodifica parâmetros catalogados dos slots ativos da cadeia.

    Valores não finitos, fora do domínio catalogado ou seletores inválidos são
    ignorados individualmente. Isso evita promover bytes antigos de um slot
    reutilizado como estado atual de um efeito diferente.
    """

    raw_dump = bytes(decompressed_dump)
    if len(raw_dump) < PRESET_PARAMETER_BLOCK_END:
        raise PresetParameterDumpError(
            "O dump não contém o bloco completo de parâmetros salvos."
        )

    resolved_catalog = catalog if catalog is not None else load_effect_catalog()
    events: list[EffectParameterEvent] = []
    for internal_slot_id in chain_state.internal_slot_ids:
        if not 0 <= internal_slot_id < PRESET_PARAMETER_SLOT_COUNT:
            continue
        record = chain_state.effect_records_by_internal_slot[internal_slot_id]
        effect_class, effect = _effect_for_record(
            resolved_catalog,
            record,
        )
        if effect_class is None or effect is None:
            continue

        controllers = {
            parameter.value_domain.get("controller_parameter")
            for parameter in effect.parameters
            if parameter.value_domain
        }
        ordered_parameters = sorted(
            effect.parameters,
            key=lambda parameter: (
                parameter.key not in controllers,
                parameter.display_order,
            ),
        )

        slot_base = (
            PRESET_PARAMETER_BLOCK_OFFSET
            + internal_slot_id * PRESET_PARAMETER_SLOT_SIZE
        )
        for parameter in ordered_parameters:
            selector = _selector(parameter)
            if selector is None:
                continue
            value_offset = slot_base + selector * PRESET_PARAMETER_VALUE_SIZE
            encoded_value = raw_dump[
                value_offset:value_offset + PRESET_PARAMETER_VALUE_SIZE
            ]
            decoded = struct.unpack("<f", encoded_value)[0]
            if not math.isfinite(decoded):
                continue
            try:
                value = normalize_parameter_value(decoded, parameter)
            except ParameterCodecError:
                continue
            events.append(
                EffectParameterEvent(
                    internal_slot_id=internal_slot_id,
                    class_id=effect_class.class_id,
                    class_key=effect_class.key,
                    class_name=effect_class.name,
                    model_id=effect.model_id,
                    effect_key=effect.key,
                    effect_name=effect.name,
                    parameter_key=parameter.key,
                    parameter_name=parameter.name,
                    value=value,
                    unit=parameter.unit,
                    display=parameter.display,
                    encoded_value=encoded_value,
                    observed_checksum=0,
                    protocol_profile="preset_dump_float32_v1",
                    value_codec="float32_little_endian_v1",
                    raw_message=b"",
                )
            )
    return tuple(events)
