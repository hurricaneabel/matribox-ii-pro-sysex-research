"""Motor genérico de respostas de parâmetros da Matribox.

A identificação de efeitos, parâmetros, campos e codecs vem integralmente do
catálogo JSON. Este módulo é somente leitura e não envia SysEx.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from tools.catalog import EffectCatalog, EffectModel, ParameterDefinition, load_effect_catalog
from tools.catalog.models import ProtocolProfile, ValueCodec
from tools.parameters.codecs import ParameterCodecError, ParameterValue, decode_parameter_value


MATRIBOX_HEADER = bytes.fromhex("F0 21 25 4D 50")
CHECKSUM_INDEX_FALLBACK = 7


class EffectParameterProtocolError(ValueError):
    """Mensagem reconhecida como parâmetro, mas estruturalmente inválida."""


@dataclass(frozen=True, slots=True)
class EffectParameterEvent:
    """Evento genérico de alteração de parâmetro recebido da pedaleira."""

    internal_slot_id: int
    class_id: int
    class_key: str
    class_name: str
    model_id: int
    effect_key: str
    effect_name: str
    parameter_key: str
    parameter_name: str
    value: ParameterValue
    unit: str | None
    encoded_value: bytes
    observed_checksum: int
    protocol_profile: str
    value_codec: str
    raw_message: bytes

    @property
    def human_slot(self) -> int:
        return self.internal_slot_id + 1

    @property
    def display_value(self) -> str:
        value_text = str(self.value)
        return f"{value_text} {self.unit}" if self.unit else value_text


def _field_document(profile: ProtocolProfile, field_name: str) -> Mapping[str, Any]:
    fields = profile.document.get("fields")
    if not isinstance(fields, dict):
        raise EffectParameterProtocolError(
            f"Perfil {profile.key} não possui objeto fields válido."
        )
    field = fields.get(field_name)
    if not isinstance(field, dict):
        raise EffectParameterProtocolError(
            f"Perfil {profile.key} não define o campo {field_name!r}."
        )
    return field


def _field_index(profile: ProtocolProfile, field_name: str) -> int:
    field = _field_document(profile, field_name)
    index = field.get("index")
    if isinstance(index, bool) or not isinstance(index, int):
        raise EffectParameterProtocolError(
            f"Campo {field_name!r} do perfil {profile.key} não possui index inteiro."
        )
    return index


def _field_indices(profile: ProtocolProfile, field_name: str) -> tuple[int, int]:
    field = _field_document(profile, field_name)
    indices = field.get("indices")
    if (
        not isinstance(indices, list)
        or len(indices) != 2
        or any(isinstance(item, bool) or not isinstance(item, int) for item in indices)
    ):
        raise EffectParameterProtocolError(
            f"Campo {field_name!r} do perfil {profile.key} não possui dois índices."
        )
    return indices[0], indices[1]


def _decode_nibble_pair(raw_message: bytes, profile: ProtocolProfile, field_name: str) -> int:
    high_index, low_index = _field_indices(profile, field_name)
    try:
        high = raw_message[high_index]
        low = raw_message[low_index]
    except IndexError as error:
        raise EffectParameterProtocolError(
            f"Campo {field_name!r} excede a mensagem do perfil {profile.key}."
        ) from error
    for label, value in (("alto", high), ("baixo", low)):
        if not 0 <= value <= 0x0F:
            raise EffectParameterProtocolError(
                f"Nibble {label} inválido em {field_name}: 0x{value:02X}."
            )
    return (high << 4) | low


def _extract_value(raw_message: bytes, profile: ProtocolProfile) -> bytes:
    field = _field_document(profile, "value")
    start = field.get("start_index")
    end = field.get("end_index_exclusive")
    if (
        isinstance(start, bool)
        or not isinstance(start, int)
        or isinstance(end, bool)
        or not isinstance(end, int)
        or not 0 <= start < end <= len(raw_message)
    ):
        raise EffectParameterProtocolError(
            f"Faixa de valor inválida no perfil {profile.key}."
        )
    return raw_message[start:end]


def _fixed_segments_match(raw_message: bytes, profile: ProtocolProfile) -> bool:
    segments = profile.document.get("fixed_segments", [])
    if not isinstance(segments, list):
        raise EffectParameterProtocolError(
            f"fixed_segments inválido no perfil {profile.key}."
        )
    for segment in segments:
        if not isinstance(segment, dict):
            raise EffectParameterProtocolError(
                f"Segmento fixo inválido no perfil {profile.key}."
            )
        start = segment.get("start_index")
        values = segment.get("bytes")
        if (
            isinstance(start, bool)
            or not isinstance(start, int)
            or not isinstance(values, list)
            or any(isinstance(value, bool) or not isinstance(value, int) for value in values)
        ):
            raise EffectParameterProtocolError(
                f"Segmento fixo malformado no perfil {profile.key}."
            )
        expected = bytes(values)
        if raw_message[start:start + len(expected)] != expected:
            return False
    return True


def _read_match_field(raw_message: bytes, profile: ProtocolProfile, field_name: str) -> int:
    index = _field_index(profile, field_name)
    try:
        return raw_message[index]
    except IndexError as error:
        raise EffectParameterProtocolError(
            f"Campo de identificação {field_name!r} excede a mensagem."
        ) from error


class EffectParameterDecoder:
    """Decodifica mensagens usando perfis, efeitos e codecs do catálogo."""

    def __init__(self, catalog: EffectCatalog | None = None) -> None:
        self.catalog = catalog if catalog is not None else load_effect_catalog()
        self._profiles = self.catalog.protocol_profiles
        self._codecs = {codec.key: codec for codec in self.catalog.value_codecs}
        self._classes_by_id = {item.class_id: item for item in self.catalog.classes}

    def _profile_matches_envelope(self, raw_message: bytes, profile: ProtocolProfile) -> bool:
        document = profile.document
        if document.get("direction") not in {"incoming", "bidirectional"}:
            return False
        if document.get("message_length") != len(raw_message):
            return False
        if raw_message[: len(MATRIBOX_HEADER)] != MATRIBOX_HEADER:
            return False
        if not raw_message or raw_message[-1] != 0xF7:
            return False

        direction_index = _field_index(profile, "direction")
        command_index = _field_index(profile, "command")
        direction_expected = _field_document(profile, "direction").get("expected")
        command_expected = _field_document(profile, "command").get(
            "expected",
            document.get("command"),
        )
        if raw_message[direction_index] != direction_expected:
            return False
        if raw_message[command_index] != command_expected:
            return False
        return _fixed_segments_match(raw_message, profile)

    @staticmethod
    def _parameter_matches(
        raw_message: bytes,
        profile: ProtocolProfile,
        parameter: ParameterDefinition,
    ) -> bool:
        if parameter.protocol_profile != profile.key:
            return False
        return all(
            _read_match_field(raw_message, profile, field_name) == expected
            for field_name, expected in parameter.message_match.items()
        )

    def _candidate_parameters(
        self,
        raw_message: bytes,
        profile: ProtocolProfile,
        effect_models: tuple[EffectModel, ...],
    ) -> tuple[tuple[EffectModel, ParameterDefinition], ...]:
        result: list[tuple[EffectModel, ParameterDefinition]] = []
        for effect in effect_models:
            for parameter in effect.parameters:
                if self._parameter_matches(raw_message, profile, parameter):
                    result.append((effect, parameter))
        return tuple(result)

    def _decode_with_profile(
        self,
        raw_message: bytes,
        profile: ProtocolProfile,
    ) -> EffectParameterEvent | None:
        internal_slot_id = _decode_nibble_pair(raw_message, profile, "internal_slot")
        slot_field = _field_document(profile, "internal_slot")
        minimum_slot = slot_field.get("minimum", 0)
        maximum_slot = slot_field.get("maximum", 11)
        if not minimum_slot <= internal_slot_id <= maximum_slot:
            raise EffectParameterProtocolError(
                f"Slot interno fora da faixa do perfil {profile.key}: {internal_slot_id + 1}."
            )

        class_id = _decode_nibble_pair(raw_message, profile, "class_id")
        model_id = _decode_nibble_pair(raw_message, profile, "model_id")
        effect_class = self._classes_by_id.get(class_id)
        if effect_class is None:
            return None

        effect_models = tuple(
            effect for effect in effect_class.models if effect.model_id == model_id
        )
        if not effect_models:
            return None

        candidates = self._candidate_parameters(raw_message, profile, effect_models)
        if not candidates:
            return None
        if len(candidates) > 1:
            labels = ", ".join(
                f"{effect.key}.{parameter.key}" for effect, parameter in candidates
            )
            raise EffectParameterProtocolError(
                "Mensagem de parâmetro ambígua no catálogo: " + labels
            )

        effect, parameter = candidates[0]
        codec = self._codecs.get(parameter.value_codec or "")
        if codec is None:
            raise EffectParameterProtocolError(
                f"Codec não encontrado para {effect.key}.{parameter.key}."
            )

        encoded_value = _extract_value(raw_message, profile)
        try:
            value = decode_parameter_value(encoded_value, parameter, codec)
        except ParameterCodecError as error:
            raise EffectParameterProtocolError(str(error)) from error

        checksum_index = _field_index(profile, "checksum")
        return EffectParameterEvent(
            internal_slot_id=internal_slot_id,
            class_id=class_id,
            class_key=effect_class.key,
            class_name=effect_class.name,
            model_id=model_id,
            effect_key=effect.key,
            effect_name=effect.name,
            parameter_key=parameter.key,
            parameter_name=parameter.name,
            value=value,
            unit=parameter.unit,
            encoded_value=encoded_value,
            observed_checksum=raw_message[checksum_index],
            protocol_profile=profile.key,
            value_codec=codec.key,
            raw_message=raw_message,
        )

    def parse(self, message: bytes | bytearray) -> EffectParameterEvent | None:
        raw_message = bytes(message)
        for profile in self._profiles:
            if self._profile_matches_envelope(raw_message, profile):
                return self._decode_with_profile(raw_message, profile)
        return None


_DEFAULT_DECODER: EffectParameterDecoder | None = None


def get_default_parameter_decoder() -> EffectParameterDecoder:
    global _DEFAULT_DECODER
    if _DEFAULT_DECODER is None:
        _DEFAULT_DECODER = EffectParameterDecoder()
    return _DEFAULT_DECODER


def parse_effect_parameter_response(
    message: bytes | bytearray,
) -> EffectParameterEvent | None:
    """Atalho para o decodificador do catálogo padrão."""

    return get_default_parameter_decoder().parse(message)
