"""Modelos imutáveis carregados do catálogo JSON da Matribox."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping


def _empty_mapping() -> Mapping[str, Any]:
    return MappingProxyType({})


@dataclass(frozen=True, slots=True)
class ParameterDefinition:
    """Parâmetro humano e seu vínculo com o protocolo confirmado."""

    key: str
    name: str
    display_order: int
    value_type: str
    minimum: int | float | None = None
    maximum: int | float | None = None
    step: int | float | None = None
    unit: str | None = None
    choices: Mapping[int, str] = field(default_factory=_empty_mapping)
    display: Mapping[str, Any] = field(default_factory=_empty_mapping)
    protocol_profile: str | None = None
    value_codec: str | None = None
    message_match: Mapping[str, int] = field(default_factory=_empty_mapping)
    identification_status: str = "pending"
    validation: Mapping[str, Any] = field(default_factory=_empty_mapping)


@dataclass(frozen=True, slots=True)
class EffectModel:
    """Modelo pertencente a uma classe de efeitos.

    Os quatro primeiros campos preservam a API histórica usada pelos comandos
    e testes existentes. Os campos seguintes vêm do catálogo JSON e podem ser
    consumidos pela futura interface sem conhecer detalhes de SysEx.
    """

    menu_number: int
    name: str
    model_id: int
    secondary_selector: int
    key: str = ""
    class_key: str = ""
    capabilities: tuple[str, ...] = ()
    parameter_catalog_status: str = "pending"
    parameters: tuple[ParameterDefinition, ...] = ()


@dataclass(frozen=True, slots=True)
class EffectClass:
    """Classe de efeitos disponível nos comandos confirmados."""

    menu_number: int
    name: str
    class_id: int
    models: tuple[EffectModel, ...]
    key: str = ""


@dataclass(frozen=True, slots=True)
class ProtocolProfile:
    """Descrição portátil de um formato de mensagem SysEx."""

    key: str
    document: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class ValueCodec:
    """Descrição portátil de uma codificação de valor."""

    key: str
    document: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class EffectCatalog:
    """Catálogo completo carregado de arquivos JSON."""

    schema_version: int
    catalog_version: int
    device: Mapping[str, str]
    classes: tuple[EffectClass, ...]
    protocol_profiles: tuple[ProtocolProfile, ...]
    value_codecs: tuple[ValueCodec, ...]
    root_path: str

    @property
    def effect_count(self) -> int:
        return sum(len(effect_class.models) for effect_class in self.classes)

    def class_by_key(self, key: str) -> EffectClass:
        normalized = key.strip().lower()
        for effect_class in self.classes:
            if effect_class.key == normalized:
                return effect_class
        raise KeyError(key)

    def effect_by_key(self, key: str) -> EffectModel:
        normalized = key.strip().lower()
        for effect_class in self.classes:
            for effect in effect_class.models:
                if effect.key == normalized:
                    return effect
        raise KeyError(key)

    def class_by_id(self, class_id: int) -> EffectClass:
        for effect_class in self.classes:
            if effect_class.class_id == class_id:
                return effect_class
        raise KeyError(class_id)

    def protocol_profile_by_key(self, key: str) -> ProtocolProfile:
        normalized = key.strip().lower()
        for profile in self.protocol_profiles:
            if profile.key == normalized:
                return profile
        raise KeyError(key)

    def value_codec_by_key(self, key: str) -> ValueCodec:
        normalized = key.strip().lower()
        for codec in self.value_codecs:
            if codec.key == normalized:
                return codec
        raise KeyError(key)
