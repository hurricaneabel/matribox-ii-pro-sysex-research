"""Codecs genéricos de valores descritos pelo catálogo JSON.

Este módulo converte somente os bytes já isolados de um parâmetro. Ele não
conhece portas MIDI, slots, efeitos ou interface gráfica.
"""

from __future__ import annotations

import math
import struct
from typing import TypeAlias

from tools.catalog.models import ParameterDefinition, ValueCodec


ParameterValue: TypeAlias = int | float | bool | str


class ParameterCodecError(ValueError):
    """Valor codificado incompatível com o codec ou parâmetro catalogado."""


def _decode_nibble_pair(high_nibble: int, low_nibble: int, *, label: str) -> int:
    for part_name, value in (("alto", high_nibble), ("baixo", low_nibble)):
        if not 0 <= value <= 0x0F:
            raise ParameterCodecError(
                f"Nibble {part_name} inválido em {label}: 0x{value:02X}."
            )
    return (high_nibble << 4) | low_nibble


def _validate_numeric_value(
    value: int | float,
    parameter: ParameterDefinition,
) -> int | float:
    normalized: int | float = value

    if parameter.value_type == "integer":
        rounded = round(float(value))
        tolerance = 1e-6
        if abs(float(value) - rounded) > tolerance:
            raise ParameterCodecError(
                f"{parameter.name} deveria ser inteiro, mas resultou em {value}."
            )
        normalized = int(rounded)
    elif parameter.value_type != "number":
        raise ParameterCodecError(
            f"Codec numérico não pode produzir value_type={parameter.value_type!r}."
        )

    if parameter.minimum is not None and normalized < parameter.minimum:
        raise ParameterCodecError(
            f"{parameter.name} abaixo do mínimo {parameter.minimum}: {normalized}."
        )
    if parameter.maximum is not None and normalized > parameter.maximum:
        raise ParameterCodecError(
            f"{parameter.name} acima do máximo {parameter.maximum}: {normalized}."
        )

    if parameter.step is not None and parameter.minimum is not None:
        steps = (float(normalized) - float(parameter.minimum)) / float(parameter.step)
        if abs(steps - round(steps)) > 1e-6:
            raise ParameterCodecError(
                f"{parameter.name} não respeita o passo {parameter.step}: {normalized}."
            )

    return normalized


def decode_upper_float32_nibbles(
    encoded_value: bytes | bytearray,
    parameter: ParameterDefinition,
    codec: ValueCodec,
) -> int | float:
    """Decodifica os 16 bits superiores de float32 enviados em quatro nibbles."""

    encoded = bytes(encoded_value)
    document = codec.document
    expected_length = document.get("encoded_length")

    if expected_length != 4 or len(encoded) != expected_length:
        raise ParameterCodecError(
            f"O codec {codec.key} exige quatro nibbles; recebidos {len(encoded)}."
        )

    configuration = document.get("configuration", {})
    if not isinstance(configuration, dict):
        raise ParameterCodecError(f"Configuração inválida do codec {codec.key}.")

    lower_bytes = configuration.get("lower_bytes", [0, 0])
    if lower_bytes != [0, 0]:
        raise ParameterCodecError(
            f"O codec {codec.key} possui lower_bytes ainda não suportados."
        )
    if configuration.get("byte_order") != "little_endian":
        raise ParameterCodecError(
            f"O codec {codec.key} possui byte_order ainda não suportada."
        )
    if configuration.get("nibble_order") != "high_then_low_per_byte":
        raise ParameterCodecError(
            f"O codec {codec.key} possui nibble_order ainda não suportada."
        )

    upper_byte_1 = _decode_nibble_pair(encoded[0], encoded[1], label="valor byte 1")
    upper_byte_2 = _decode_nibble_pair(encoded[2], encoded[3], label="valor byte 2")
    decoded = struct.unpack(
        "<f",
        bytes((0x00, 0x00, upper_byte_1, upper_byte_2)),
    )[0]

    if configuration.get("require_finite", True) and not math.isfinite(decoded):
        raise ParameterCodecError("O valor decodificado não é finito.")

    return _validate_numeric_value(decoded, parameter)


def decode_parameter_value(
    encoded_value: bytes | bytearray,
    parameter: ParameterDefinition,
    codec: ValueCodec,
) -> ParameterValue:
    """Executa o codec apontado pelo parâmetro no catálogo."""

    kind = codec.document.get("kind")

    if kind == "float32_upper_16_bits_as_nibbles":
        return decode_upper_float32_nibbles(encoded_value, parameter, codec)

    raise ParameterCodecError(
        f"Codec ainda não implementado: {codec.key} ({kind!r})."
    )
