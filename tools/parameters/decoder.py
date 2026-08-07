"""Motor genérico de respostas de parâmetros da Matribox.

A mensagem ``0x1C`` informa o slot interno, o seletor do parâmetro e o valor,
mas as capturas de M-BOOST e COMP1 provaram que os bytes 21–22 não são o
``model_id`` do efeito: ambos usam o mesmo endereço ``01 04``. Portanto, a
identidade do efeito deve vir da cadeia estrutural atual.

Este módulo separa duas etapas:

1. :class:`EffectParameterSignal` interpreta somente o envelope do protocolo;
2. a resolução recebe a chave do efeito existente naquele slot e consulta o
   catálogo JSON para identificar e decodificar o parâmetro correto.

O módulo é somente leitura e não envia SysEx.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from tools.catalog import EffectCatalog, EffectModel, ParameterDefinition, load_effect_catalog
from tools.catalog.models import ProtocolProfile, ValueCodec
from tools.parameters.codecs import (
    ParameterCodecError,
    ParameterValue,
    decode_parameter_value,
    select_codec_encoded_value,
)


MATRIBOX_HEADER = bytes.fromhex("F0 21 25 4D 50")


class EffectParameterProtocolError(ValueError):
    """Mensagem reconhecida como parâmetro, mas estruturalmente inválida."""


@dataclass(frozen=True, slots=True)
class EffectParameterSignal:
    """Envelope de parâmetro ainda não associado a um efeito específico."""

    internal_slot_id: int
    class_id: int | None
    parameter_address: int | None
    parameter_selector: int | None
    encoded_value: bytes
    observed_checksum: int
    protocol_profile: str
    raw_message: bytes

    @property
    def human_slot(self) -> int:
        return self.internal_slot_id + 1


@dataclass(frozen=True, slots=True)
class EffectParameterEvent:
    """Evento de parâmetro resolvido contra o efeito real da cadeia."""

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
    display: Mapping[str, Any]
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
        if self.display.get("kind") == "duration_milliseconds":
            milliseconds = float(self.value)
            threshold = float(self.display.get("seconds_threshold", 1000))
            if milliseconds < threshold:
                if milliseconds.is_integer():
                    return f"{int(milliseconds)} ms"
                return f"{milliseconds:g} ms"
            decimals = int(self.display.get("seconds_decimals", 1))
            value_text = f"{milliseconds / 1000:.{decimals}f}"
            if self.display.get("decimal_separator", ",") == ",":
                value_text = value_text.replace(".", ",")
            return f"{value_text} s"
        if isinstance(self.value, bool):
            value_text = "ligado" if self.value else "desligado"
        else:
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


def _optional_field_document(
    profile: ProtocolProfile,
    field_name: str,
) -> Mapping[str, Any] | None:
    fields = profile.document.get("fields")
    if not isinstance(fields, dict):
        raise EffectParameterProtocolError(
            f"Perfil {profile.key} não possui objeto fields válido."
        )
    field = fields.get(field_name)
    if field is None:
        return None
    if not isinstance(field, dict):
        raise EffectParameterProtocolError(
            f"Perfil {profile.key} possui campo {field_name!r} inválido."
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


def _decode_optional_nibble_pair(
    raw_message: bytes,
    profile: ProtocolProfile,
    field_name: str,
) -> int | None:
    if _optional_field_document(profile, field_name) is None:
        return None
    return _decode_nibble_pair(raw_message, profile, field_name)


def _read_optional_indexed_field(
    raw_message: bytes,
    profile: ProtocolProfile,
    field_name: str,
) -> int | None:
    field = _optional_field_document(profile, field_name)
    if field is None:
        return None
    index = field.get("index")
    if isinstance(index, bool) or not isinstance(index, int):
        raise EffectParameterProtocolError(
            f"Campo {field_name!r} do perfil {profile.key} não possui index inteiro."
        )
    try:
        return raw_message[index]
    except IndexError as error:
        raise EffectParameterProtocolError(
            f"Campo {field_name!r} excede a mensagem do perfil {profile.key}."
        ) from error


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
    encoded = raw_message[start:end]
    if field.get("encoding") == "nibble_sequence":
        for index, value in enumerate(encoded, start=start):
            if not 0 <= value <= 0x0F:
                raise EffectParameterProtocolError(
                    f"Nibble inválido em value[{index}]: 0x{value:02X}."
                )
    return encoded


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
    """Decodifica o envelope e resolve o parâmetro usando o contexto da cadeia."""

    def __init__(self, catalog: EffectCatalog | None = None) -> None:
        self.catalog = catalog if catalog is not None else load_effect_catalog()
        self._profiles = self.catalog.protocol_profiles
        self._profiles_by_key = {profile.key: profile for profile in self._profiles}
        self._codecs = {codec.key: codec for codec in self.catalog.value_codecs}

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

    def parse_signal(
        self,
        message: bytes | bytearray,
    ) -> EffectParameterSignal | None:
        raw_message = bytes(message)
        for profile in self._profiles:
            if not self._profile_matches_envelope(raw_message, profile):
                continue

            internal_slot_id = _decode_nibble_pair(
                raw_message,
                profile,
                "internal_slot",
            )
            slot_field = _field_document(profile, "internal_slot")
            minimum_slot = slot_field.get("minimum", 0)
            maximum_slot = slot_field.get("maximum", 11)
            if not minimum_slot <= internal_slot_id <= maximum_slot:
                raise EffectParameterProtocolError(
                    f"Slot interno fora da faixa do perfil {profile.key}: "
                    f"{internal_slot_id + 1}."
                )

            checksum_index = _field_index(profile, "checksum")
            return EffectParameterSignal(
                internal_slot_id=internal_slot_id,
                class_id=_decode_optional_nibble_pair(
                    raw_message,
                    profile,
                    "class_id",
                ),
                parameter_address=_decode_optional_nibble_pair(
                    raw_message,
                    profile,
                    "parameter_address",
                ),
                parameter_selector=_read_optional_indexed_field(
                    raw_message,
                    profile,
                    "parameter_selector",
                ),
                encoded_value=_extract_value(raw_message, profile),
                observed_checksum=raw_message[checksum_index],
                protocol_profile=profile.key,
                raw_message=raw_message,
            )
        return None

    def _candidate_parameters_for_effect(
        self,
        signal: EffectParameterSignal,
        effect: EffectModel,
    ) -> tuple[ParameterDefinition, ...]:
        profile = self._profiles_by_key.get(signal.protocol_profile)
        if profile is None:
            raise EffectParameterProtocolError(
                f"Perfil ausente durante a resolução: {signal.protocol_profile}."
            )
        return tuple(
            parameter
            for parameter in effect.parameters
            if self._parameter_matches(signal.raw_message, profile, parameter)
        )

    def resolve_signal(
        self,
        signal: EffectParameterSignal,
        effect_key: str,
    ) -> EffectParameterEvent | None:
        try:
            effect = self.catalog.effect_by_key(effect_key)
            effect_class = self.catalog.class_by_key(effect.class_key)
        except KeyError:
            return None

        # O campo historicamente chamado ``class_id`` no envelope 0x1C não
        # identifica a classe estrutural: as capturas FREQ/FILTER mantêm 0x00
        # exatamente como DYN. A identidade confiável continua vindo da cadeia.
        candidates = self._candidate_parameters_for_effect(signal, effect)
        if not candidates:
            return None
        if len(candidates) > 1:
            labels = ", ".join(
                f"{effect.key}.{parameter.key}" for parameter in candidates
            )
            raise EffectParameterProtocolError(
                "Mensagem de parâmetro ambígua dentro do efeito: " + labels
            )

        parameter = candidates[0]
        codec = self._codecs.get(parameter.value_codec or "")
        if codec is None:
            raise EffectParameterProtocolError(
                f"Codec não encontrado para {effect.key}.{parameter.key}."
            )

        try:
            codec_encoded_value = select_codec_encoded_value(
                signal.encoded_value,
                codec,
            )
            value = decode_parameter_value(codec_encoded_value, parameter, codec)
        except ParameterCodecError as error:
            raise EffectParameterProtocolError(str(error)) from error

        return EffectParameterEvent(
            internal_slot_id=signal.internal_slot_id,
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
            encoded_value=codec_encoded_value,
            observed_checksum=signal.observed_checksum,
            protocol_profile=signal.protocol_profile,
            value_codec=codec.key,
            raw_message=signal.raw_message,
        )

    def parse(
        self,
        message: bytes | bytearray,
        *,
        effect_key: str | None = None,
    ) -> EffectParameterEvent | None:
        """Decodifica com contexto explícito ou exige identificação não ambígua.

        A aplicação ao vivo deve sempre fornecer ``effect_key`` obtido da cadeia
        atual. A resolução global sem contexto é mantida apenas para análises e
        falha explicitamente quando mais de um efeito aceita a mesma mensagem.
        """

        signal = self.parse_signal(message)
        if signal is None:
            return None
        if effect_key is not None:
            return self.resolve_signal(signal, effect_key)

        resolved: list[EffectParameterEvent] = []
        for effect_class in self.catalog.classes:
            for effect in effect_class.models:
                event = self.resolve_signal(signal, effect.key)
                if event is not None:
                    resolved.append(event)

        if not resolved:
            return None
        if len(resolved) > 1:
            labels = ", ".join(
                f"{event.effect_key}.{event.parameter_key}" for event in resolved
            )
            raise EffectParameterProtocolError(
                "A mensagem exige contexto da cadeia para identificar o efeito: "
                + labels
            )
        return resolved[0]


_DEFAULT_DECODER: EffectParameterDecoder | None = None


def get_default_parameter_decoder() -> EffectParameterDecoder:
    global _DEFAULT_DECODER
    if _DEFAULT_DECODER is None:
        _DEFAULT_DECODER = EffectParameterDecoder()
    return _DEFAULT_DECODER


def parse_effect_parameter_signal(
    message: bytes | bytearray,
) -> EffectParameterSignal | None:
    """Interpreta o envelope sem presumir qual efeito ocupa o slot."""

    return get_default_parameter_decoder().parse_signal(message)


def resolve_effect_parameter_signal(
    signal: EffectParameterSignal,
    effect_key: str,
) -> EffectParameterEvent | None:
    """Resolve um sinal usando a identidade estrutural do efeito no slot."""

    return get_default_parameter_decoder().resolve_signal(signal, effect_key)


def parse_effect_parameter_response(
    message: bytes | bytearray,
    *,
    effect_key: str | None = None,
) -> EffectParameterEvent | None:
    """Atalho compatível para decodificação com contexto opcional."""

    return get_default_parameter_decoder().parse(message, effect_key=effect_key)
