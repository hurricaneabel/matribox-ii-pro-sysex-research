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
) -> int | float | bool | str:
    numeric_value = float(value)
    tolerance = 1e-6

    if parameter.value_type == "integer":
        rounded = round(numeric_value)
        if abs(numeric_value - rounded) > tolerance:
            raise ParameterCodecError(
                f"{parameter.name} deveria ser inteiro, mas resultou em {value}."
            )
        normalized: int | float | bool | str = int(rounded)
        comparable_value: int | float = int(rounded)
    elif parameter.value_type == "number":
        normalized = value
        comparable_value = numeric_value
    elif parameter.value_type == "boolean":
        rounded = round(numeric_value)
        if abs(numeric_value - rounded) > tolerance or rounded not in (0, 1):
            raise ParameterCodecError(
                f"{parameter.name} deveria ser booleano 0/1, mas resultou em {value}."
            )
        normalized = bool(rounded)
        comparable_value = int(rounded)
    elif parameter.value_type == "enum":
        rounded = round(numeric_value)
        if abs(numeric_value - rounded) > tolerance:
            raise ParameterCodecError(
                f"{parameter.name} deveria ser enum inteiro, mas resultou em {value}."
            )
        comparable_value = int(rounded)
        try:
            normalized = parameter.choices[comparable_value]
        except KeyError as error:
            raise ParameterCodecError(
                f"{parameter.name} recebeu opção não catalogada: {comparable_value}."
            ) from error
    else:
        raise ParameterCodecError(
            f"Codec numérico não pode produzir value_type={parameter.value_type!r}."
        )

    if parameter.minimum is not None and comparable_value < parameter.minimum:
        raise ParameterCodecError(
            f"{parameter.name} abaixo do mínimo {parameter.minimum}: {comparable_value}."
        )
    if parameter.maximum is not None and comparable_value > parameter.maximum:
        raise ParameterCodecError(
            f"{parameter.name} acima do máximo {parameter.maximum}: {comparable_value}."
        )

    if parameter.step is not None and parameter.minimum is not None:
        minimum = float(parameter.minimum)
        step = float(parameter.step)
        steps = (float(comparable_value) - minimum) / step
        nearest_step = round(steps)
        snapped_value = minimum + nearest_step * step
        # Valores decimais transmitidos como float32 carregam o ruído binário
        # normal do formato (por exemplo, 4.2 chega como 4.199999809265137).
        # Compare no domínio do valor, com tolerância relativa apropriada ao
        # float32, em vez de exigir que a divisão pelo passo seja quase exata.
        step_tolerance = max(
            tolerance,
            abs(float(comparable_value)) * 1e-6,
            abs(step) * 1e-5,
        )
        if abs(float(comparable_value) - snapped_value) > step_tolerance:
            raise ParameterCodecError(
                f"{parameter.name} não respeita o passo {parameter.step}: "
                f"{comparable_value}."
            )
        if parameter.value_type == "number":
            normalized = snapped_value

    return normalized


def normalize_parameter_value(
    value: int | float,
    parameter: ParameterDefinition,
) -> ParameterValue:
    """Normaliza um valor numérico já decodificado conforme o catálogo."""

    return _validate_numeric_value(value, parameter)


def select_codec_encoded_value(
    encoded_value: bytes | bytearray,
    codec: ValueCodec,
) -> bytes:
    """Seleciona do payload do perfil os nibbles consumidos pelo codec.

    O perfil 0x1C expõe os oito nibbles físicos do float32. Codecs antigos
    podem declarar ``configuration.input_slice`` para continuar consumindo
    apenas a parte historicamente validada. Chamadas diretas que já fornecem
    exatamente ``encoded_length`` permanecem compatíveis.
    """

    encoded = bytes(encoded_value)
    expected_length = codec.document.get("encoded_length")
    if isinstance(expected_length, bool) or not isinstance(expected_length, int):
        raise ParameterCodecError(f"encoded_length inválido no codec {codec.key}.")
    if len(encoded) == expected_length:
        return encoded

    configuration = codec.document.get("configuration", {})
    if not isinstance(configuration, dict):
        raise ParameterCodecError(f"Configuração inválida do codec {codec.key}.")
    input_slice = configuration.get("input_slice")
    if (
        not isinstance(input_slice, list)
        or len(input_slice) != 2
        or any(isinstance(item, bool) or not isinstance(item, int) for item in input_slice)
    ):
        raise ParameterCodecError(
            f"O codec {codec.key} exige {expected_length} nibbles; recebidos {len(encoded)}."
        )
    start, end = input_slice
    if not 0 <= start < end <= len(encoded) or end - start != expected_length:
        raise ParameterCodecError(
            f"input_slice inválido no codec {codec.key}: {input_slice!r}."
        )
    return encoded[start:end]


def decode_full_float32_nibbles(
    encoded_value: bytes | bytearray,
    parameter: ParameterDefinition,
    codec: ValueCodec,
) -> ParameterValue:
    """Decodifica os quatro bytes completos de float32 enviados em oito nibbles."""

    encoded = bytes(encoded_value)
    expected_length = codec.document.get("encoded_length")
    if expected_length != 8 or len(encoded) != expected_length:
        raise ParameterCodecError(
            f"O codec {codec.key} exige oito nibbles; recebidos {len(encoded)}."
        )

    configuration = codec.document.get("configuration", {})
    if not isinstance(configuration, dict):
        raise ParameterCodecError(f"Configuração inválida do codec {codec.key}.")
    if configuration.get("byte_order") != "little_endian":
        raise ParameterCodecError(
            f"O codec {codec.key} possui byte_order ainda não suportada."
        )
    if configuration.get("nibble_order") != "high_then_low_per_byte":
        raise ParameterCodecError(
            f"O codec {codec.key} possui nibble_order ainda não suportada."
        )

    decoded_bytes = bytes(
        _decode_nibble_pair(encoded[index], encoded[index + 1], label=f"valor byte {index // 2}")
        for index in range(0, 8, 2)
    )
    decoded = struct.unpack("<f", decoded_bytes)[0]
    if configuration.get("require_finite", True) and not math.isfinite(decoded):
        raise ParameterCodecError("O valor decodificado não é finito.")
    return _validate_numeric_value(decoded, parameter)


def decode_upper_float32_nibbles(
    encoded_value: bytes | bytearray,
    parameter: ParameterDefinition,
    codec: ValueCodec,
) -> ParameterValue:
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
    selected_value = select_codec_encoded_value(encoded_value, codec)

    if kind == "float32_upper_16_bits_as_nibbles":
        return decode_upper_float32_nibbles(selected_value, parameter, codec)
    if kind == "float32_as_nibbles":
        return decode_full_float32_nibbles(selected_value, parameter, codec)

    raise ParameterCodecError(
        f"Codec ainda não implementado: {codec.key} ({kind!r})."
    )
