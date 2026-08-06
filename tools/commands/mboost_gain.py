"""Compatibilidade para o validador histórico de DYN / M-BOOST / GAIN.

Desde a Fase 23B, a interpretação real é executada pelo motor genérico em
``tools.parameters`` com definições vindas do catálogo JSON. Este módulo
preserva nomes, constantes e o evento usados pela Fase 22.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from tools.commands.effect_catalog import CATALOG
from tools.parameters.codecs import ParameterCodecError, decode_parameter_value
from tools.parameters.decoder import (
    EffectParameterProtocolError,
    parse_effect_parameter_response,
)


MATRIBOX_HEADER: Final = bytes.fromhex("F0 21 25 4D 50")
EXPECTED_MESSAGE_LENGTH: Final = 70
CHECKSUM_INDEX: Final = 7
DIRECTION_INDEX: Final = 8
COMMAND_INDEX: Final = 9
DIRECTION_INCOMING: Final = 0x00
COMMAND_PARAMETER: Final = 0x1C

MODEL_HIGH_INDEX: Final = 21
MODEL_LOW_INDEX: Final = 22
SLOT_HIGH_INDEX: Final = 39
SLOT_LOW_INDEX: Final = 40
CLASS_HIGH_INDEX: Final = 41
CLASS_LOW_INDEX: Final = 42
VALUE_START_INDEX: Final = 59
VALUE_END_INDEX: Final = 63
PARAMETER_MARKER_INDEX: Final = 63
PARAMETER_TYPE_INDEX: Final = 64

DYN_CLASS_ID: Final = 0x00
MBOOST_MODEL_ID: Final = 0x14
MBOOST_SECONDARY_SELECTOR: Final = 0x00
GAIN_MINIMUM: Final = 0
GAIN_MAXIMUM: Final = 100
MAX_INTERNAL_SLOTS: Final = 12


class MBoostGainProtocolError(ValueError):
    """Erro compatível da Fase 22 para uma mensagem de M-BOOST / GAIN."""


@dataclass(frozen=True, slots=True)
class MBoostGainEvent:
    """Alteração recebida do parâmetro GAIN do M-BOOST."""

    internal_slot_id: int
    gain: int
    encoded_gain: bytes
    observed_checksum: int
    raw_message: bytes

    @property
    def human_slot(self) -> int:
        return self.internal_slot_id + 1


def _gain_definition():
    effect = CATALOG.effect_by_key("dyn.m_boost")
    parameter = next(item for item in effect.parameters if item.key == "gain")
    codec = CATALOG.value_codec_by_key(parameter.value_codec or "")
    return parameter, codec


def decode_gain_nibbles(encoded_gain: bytes | bytearray) -> int:
    """Decodifica o GAIN usando o codec apontado pelo JSON do M-BOOST."""

    parameter, codec = _gain_definition()
    try:
        value = decode_parameter_value(encoded_gain, parameter, codec)
    except ParameterCodecError as error:
        raise MBoostGainProtocolError(str(error)) from error

    if not isinstance(value, int):
        raise MBoostGainProtocolError(
            f"O GAIN catalogado deveria resultar em inteiro, não {type(value).__name__}."
        )
    return value


def parse_mboost_gain_response(
    message: bytes | bytearray,
) -> MBoostGainEvent | None:
    """Adapta o evento genérico para a API histórica do M-BOOST."""

    try:
        event = parse_effect_parameter_response(message)
    except EffectParameterProtocolError as error:
        raise MBoostGainProtocolError(str(error)) from error

    if event is None:
        return None
    if event.effect_key != "dyn.m_boost" or event.parameter_key != "gain":
        return None
    if not isinstance(event.value, int):
        raise MBoostGainProtocolError("O GAIN decodificado não é inteiro.")

    return MBoostGainEvent(
        internal_slot_id=event.internal_slot_id,
        gain=event.value,
        encoded_gain=event.encoded_value,
        observed_checksum=event.observed_checksum,
        raw_message=event.raw_message,
    )
