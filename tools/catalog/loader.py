"""Carregamento e validação do catálogo JSON multiplataforma."""

from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
import re
from types import MappingProxyType
from typing import Any, Iterable, Mapping

from tools.catalog.errors import CatalogValidationError
from tools.catalog.models import (
    EffectCatalog,
    EffectClass,
    EffectModel,
    ParameterDefinition,
    ProtocolProfile,
    ValueCodec,
)


SUPPORTED_SCHEMA_VERSION = 1
KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
EFFECT_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]*\.[a-z0-9_]+$")
PARAMETER_STATUSES = frozenset(
    {"pending", "partially_cataloged", "physically_validated"}
)
VALUE_TYPES = frozenset({"integer", "number", "boolean", "enum", "string"})
DEFAULT_CATALOG_ROOT = Path(__file__).resolve().parents[2] / "catalog"


def _fail(path: Path, message: str) -> CatalogValidationError:
    return CatalogValidationError(f"{path}: {message}")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise _fail(path, "arquivo não encontrado") from error
    except json.JSONDecodeError as error:
        raise _fail(
            path,
            f"JSON inválido na linha {error.lineno}, coluna {error.colno}",
        ) from error

    if not isinstance(parsed, dict):
        raise _fail(path, "a raiz deve ser um objeto JSON")
    return parsed


def _require_string(document: Mapping[str, Any], key: str, path: Path) -> str:
    value = document.get(key)
    if not isinstance(value, str) or not value.strip():
        raise _fail(path, f"campo obrigatório '{key}' deve ser texto não vazio")
    return value


def _require_key(
    document: Mapping[str, Any],
    key: str,
    path: Path,
    *,
    effect_key: bool = False,
) -> str:
    value = _require_string(document, key, path)
    pattern = EFFECT_KEY_PATTERN if effect_key else KEY_PATTERN
    if pattern.fullmatch(value) is None:
        raise _fail(path, f"campo '{key}' possui chave inválida: {value!r}")
    return value


def _require_integer(
    document: Mapping[str, Any],
    key: str,
    path: Path,
    *,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    value = document.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise _fail(path, f"campo obrigatório '{key}' deve ser inteiro")
    if minimum is not None and value < minimum:
        raise _fail(path, f"campo '{key}' deve ser >= {minimum}")
    if maximum is not None and value > maximum:
        raise _fail(path, f"campo '{key}' deve ser <= {maximum}")
    return value


def _require_version(document: Mapping[str, Any], path: Path) -> int:
    version = _require_integer(document, "schema_version", path, minimum=1)
    if version != SUPPORTED_SCHEMA_VERSION:
        raise _fail(
            path,
            "schema_version não suportada: "
            f"{version}; esperado {SUPPORTED_SCHEMA_VERSION}",
        )
    return version


def _as_mapping(value: Any, *, path: Path, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise _fail(path, f"campo '{field_name}' deve ser objeto")
    return MappingProxyType(dict(value))


def _as_string_tuple(value: Any, *, path: Path, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise _fail(path, f"campo '{field_name}' deve ser lista")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise _fail(path, f"campo '{field_name}' contém item inválido")
        result.append(item)
    if len(result) != len(set(result)):
        raise _fail(path, f"campo '{field_name}' contém duplicatas")
    return tuple(result)


def _parse_parameter(document: Mapping[str, Any], path: Path) -> ParameterDefinition:
    key = _require_key(document, "key", path)
    name = _require_string(document, "name", path)
    display_order = _require_integer(document, "display_order", path, minimum=1)
    value_type = _require_string(document, "value_type", path)
    if value_type not in VALUE_TYPES:
        raise _fail(path, f"value_type não suportado: {value_type}")

    range_document = document.get("range")
    minimum: int | float | None = None
    maximum: int | float | None = None
    step: int | float | None = None
    if range_document is not None:
        if not isinstance(range_document, dict):
            raise _fail(path, "campo 'range' deve ser objeto")
        minimum = range_document.get("minimum")
        maximum = range_document.get("maximum")
        step = range_document.get("step")
        for field_name, value in (
            ("minimum", minimum),
            ("maximum", maximum),
            ("step", step),
        ):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise _fail(path, f"range.{field_name} deve ser número")
        assert minimum is not None and maximum is not None and step is not None
        if minimum > maximum:
            raise _fail(path, "range.minimum não pode exceder range.maximum")
        if step <= 0:
            raise _fail(path, "range.step deve ser positivo")

    unit = document.get("unit")
    if unit is not None and not isinstance(unit, str):
        raise _fail(path, "campo 'unit' deve ser texto ou null")

    protocol = document.get("protocol")
    protocol_profile: str | None = None
    value_codec: str | None = None
    message_match: Mapping[str, int] = MappingProxyType({})
    identification_status = "pending"
    if protocol is not None:
        if not isinstance(protocol, dict):
            raise _fail(path, "campo 'protocol' deve ser objeto")
        protocol_profile = _require_key(protocol, "profile", path)
        value_codec = _require_key(protocol, "value_codec", path)
        identification_status = _require_string(
            protocol,
            "identification_status",
            path,
        )
        raw_match = protocol.get("message_match", {})
        if not isinstance(raw_match, dict):
            raise _fail(path, "protocol.message_match deve ser objeto")
        normalized_match: dict[str, int] = {}
        for match_key, match_value in raw_match.items():
            if not isinstance(match_key, str) or not match_key:
                raise _fail(path, "protocol.message_match possui chave inválida")
            if isinstance(match_value, bool) or not isinstance(match_value, int):
                raise _fail(
                    path,
                    f"protocol.message_match.{match_key} deve ser inteiro",
                )
            normalized_match[match_key] = match_value
        message_match = MappingProxyType(normalized_match)

    validation = document.get("validation", {})
    validation_mapping = _as_mapping(
        validation,
        path=path,
        field_name="validation",
    )

    return ParameterDefinition(
        key=key,
        name=name,
        display_order=display_order,
        value_type=value_type,
        minimum=minimum,
        maximum=maximum,
        step=step,
        unit=unit,
        protocol_profile=protocol_profile,
        value_codec=value_codec,
        message_match=message_match,
        identification_status=identification_status,
        validation=validation_mapping,
    )


def _parse_effect(
    path: Path,
    *,
    expected_class_key: str,
) -> EffectModel:
    document = _read_json(path)
    _require_version(document, path)

    class_key = _require_key(document, "class_key", path)
    if class_key != expected_class_key:
        raise _fail(
            path,
            f"class_key '{class_key}' não corresponde a '{expected_class_key}'",
        )

    parameters_value = document.get("parameters")
    if not isinstance(parameters_value, list):
        raise _fail(path, "campo 'parameters' deve ser lista")
    parameters = tuple(
        _parse_parameter(parameter, path)
        for parameter in parameters_value
        if isinstance(parameter, dict)
    )
    if len(parameters) != len(parameters_value):
        raise _fail(path, "campo 'parameters' contém item que não é objeto")

    parameter_keys = [parameter.key for parameter in parameters]
    parameter_orders = [parameter.display_order for parameter in parameters]
    if len(parameter_keys) != len(set(parameter_keys)):
        raise _fail(path, "há chaves de parâmetros duplicadas")
    if len(parameter_orders) != len(set(parameter_orders)):
        raise _fail(path, "há ordens de parâmetros duplicadas")
    if sorted(parameter_orders) != list(range(1, len(parameter_orders) + 1)):
        raise _fail(path, "display_order dos parâmetros deve ser contínuo a partir de 1")

    capabilities = _as_string_tuple(
        document.get("capabilities", []),
        path=path,
        field_name="capabilities",
    )
    for capability in capabilities:
        if KEY_PATTERN.fullmatch(capability) is None:
            raise _fail(path, f"capability inválida: {capability}")

    status = _require_string(document, "parameter_catalog_status", path)
    if status not in PARAMETER_STATUSES:
        raise _fail(path, f"parameter_catalog_status inválido: {status}")
    if parameters and "parameters" not in capabilities:
        raise _fail(path, "efeito com parâmetros deve declarar capability 'parameters'")
    if status == "pending" and parameters:
        raise _fail(path, "efeito pending não pode possuir parâmetros")
    if status != "pending" and not parameters:
        raise _fail(path, "efeito catalogado deve possuir parâmetros")

    effect_key = _require_key(document, "key", path, effect_key=True)
    if not effect_key.startswith(f"{class_key}."):
        raise _fail(path, f"key '{effect_key}' não pertence à classe '{class_key}'")

    return EffectModel(
        menu_number=_require_integer(document, "menu_number", path, minimum=1),
        name=_require_string(document, "name", path),
        model_id=_require_integer(document, "model_id", path, minimum=0, maximum=0x7F),
        secondary_selector=_require_integer(
            document,
            "secondary_selector",
            path,
            minimum=0,
            maximum=0x7F,
        ),
        key=effect_key,
        class_key=class_key,
        capabilities=capabilities,
        parameter_catalog_status=status,
        parameters=tuple(sorted(parameters, key=lambda item: item.display_order)),
    )


def _validate_unique(values: Iterable[Any], *, label: str, path: Path) -> None:
    values_tuple = tuple(values)
    if len(values_tuple) != len(set(values_tuple)):
        raise _fail(path, f"{label} duplicado")


def _parse_class_index(root: Path, index_path: Path) -> EffectClass:
    document = _read_json(index_path)
    _require_version(document, index_path)
    class_key = _require_key(document, "key", index_path)

    effect_files_value = document.get("effect_files")
    if not isinstance(effect_files_value, list) or not effect_files_value:
        raise _fail(index_path, "campo 'effect_files' deve ser lista não vazia")

    effect_files: list[str] = []
    for value in effect_files_value:
        if not isinstance(value, str) or not value.endswith(".json"):
            raise _fail(index_path, "effect_files contém caminho inválido")
        if "\\" in value or Path(value).is_absolute() or ".." in Path(value).parts:
            raise _fail(index_path, "effect_files deve usar caminho relativo portátil")
        effect_files.append(value)
    _validate_unique(effect_files, label="arquivo de efeito", path=index_path)

    models = tuple(
        _parse_effect(index_path.parent / effect_file, expected_class_key=class_key)
        for effect_file in effect_files
    )
    models = tuple(sorted(models, key=lambda item: item.menu_number))

    _validate_unique(
        (model.menu_number for model in models),
        label="menu_number de efeito",
        path=index_path,
    )
    if [model.menu_number for model in models] != list(range(1, len(models) + 1)):
        raise _fail(index_path, "menu_number dos efeitos deve ser contínuo a partir de 1")
    _validate_unique(
        (model.key for model in models),
        label="key de efeito",
        path=index_path,
    )
    _validate_unique(
        ((model.model_id, model.secondary_selector) for model in models),
        label="identidade modelo/seletor",
        path=index_path,
    )

    return EffectClass(
        menu_number=_require_integer(document, "menu_number", index_path, minimum=1),
        name=_require_string(document, "name", index_path),
        class_id=_require_integer(document, "class_id", index_path, minimum=0, maximum=0x7F),
        models=models,
        key=class_key,
    )


def _parse_named_documents(
    root: Path,
    paths_value: Any,
    *,
    field_name: str,
    kind: type[ProtocolProfile] | type[ValueCodec],
) -> tuple[ProtocolProfile, ...] | tuple[ValueCodec, ...]:
    if not isinstance(paths_value, list):
        raise _fail(root / "catalog.json", f"campo '{field_name}' deve ser lista")

    result: list[ProtocolProfile | ValueCodec] = []
    for relative in paths_value:
        if not isinstance(relative, str) or "\\" in relative:
            raise _fail(root / "catalog.json", f"{field_name} contém caminho inválido")
        relative_path = Path(relative)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise _fail(root / "catalog.json", f"{field_name} contém caminho não portátil")
        path = root / relative_path
        document = _read_json(path)
        _require_version(document, path)
        key = _require_key(document, "key", path)
        result.append(kind(key=key, document=MappingProxyType(document)))

    _validate_unique(
        (item.key for item in result),
        label=f"key em {field_name}",
        path=root / "catalog.json",
    )
    return tuple(result)  # type: ignore[return-value]


@lru_cache(maxsize=8)
def _load_effect_catalog_cached(root_string: str) -> EffectCatalog:
    root = Path(root_string)
    manifest_path = root / "catalog.json"
    manifest = _read_json(manifest_path)
    schema_version = _require_version(manifest, manifest_path)
    catalog_version = _require_integer(
        manifest,
        "catalog_version",
        manifest_path,
        minimum=1,
    )

    device_value = manifest.get("device")
    if not isinstance(device_value, dict):
        raise _fail(manifest_path, "campo 'device' deve ser objeto")
    device = MappingProxyType(
        {
            "manufacturer": _require_string(device_value, "manufacturer", manifest_path),
            "model": _require_string(device_value, "model", manifest_path),
        }
    )

    class_indexes_value = manifest.get("class_indexes")
    if not isinstance(class_indexes_value, list) or not class_indexes_value:
        raise _fail(manifest_path, "campo 'class_indexes' deve ser lista não vazia")

    classes: list[EffectClass] = []
    for relative in class_indexes_value:
        if not isinstance(relative, str) or "\\" in relative:
            raise _fail(manifest_path, "class_indexes contém caminho inválido")
        relative_path = Path(relative)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise _fail(manifest_path, "class_indexes contém caminho não portátil")
        classes.append(_parse_class_index(root, root / relative_path))

    classes_tuple = tuple(sorted(classes, key=lambda item: item.menu_number))
    _validate_unique(
        (item.menu_number for item in classes_tuple),
        label="menu_number de classe",
        path=manifest_path,
    )
    if [item.menu_number for item in classes_tuple] != list(
        range(1, len(classes_tuple) + 1)
    ):
        raise _fail(manifest_path, "menu_number das classes deve ser contínuo a partir de 1")
    _validate_unique(
        (item.key for item in classes_tuple),
        label="key de classe",
        path=manifest_path,
    )
    _validate_unique(
        (item.class_id for item in classes_tuple),
        label="class_id",
        path=manifest_path,
    )
    _validate_unique(
        (model.key for item in classes_tuple for model in item.models),
        label="key global de efeito",
        path=manifest_path,
    )

    protocol_profiles = _parse_named_documents(
        root,
        manifest.get("protocol_profiles", []),
        field_name="protocol_profiles",
        kind=ProtocolProfile,
    )
    value_codecs = _parse_named_documents(
        root,
        manifest.get("value_codecs", []),
        field_name="value_codecs",
        kind=ValueCodec,
    )

    profile_keys = {profile.key for profile in protocol_profiles}
    codec_keys = {codec.key for codec in value_codecs}
    for effect_class in classes_tuple:
        for effect in effect_class.models:
            for parameter in effect.parameters:
                if parameter.protocol_profile not in profile_keys:
                    raise _fail(
                        manifest_path,
                        f"parâmetro {effect.key}.{parameter.key} referencia perfil inexistente",
                    )
                if parameter.value_codec not in codec_keys:
                    raise _fail(
                        manifest_path,
                        f"parâmetro {effect.key}.{parameter.key} referencia codec inexistente",
                    )

    return EffectCatalog(
        schema_version=schema_version,
        catalog_version=catalog_version,
        device=device,
        classes=classes_tuple,
        protocol_profiles=protocol_profiles,
        value_codecs=value_codecs,
        root_path=str(root.resolve()),
    )


def load_effect_catalog(root: str | Path | None = None) -> EffectCatalog:
    """Carrega e valida o catálogo, usando cache por diretório absoluto."""

    selected_root = Path(root) if root is not None else DEFAULT_CATALOG_ROOT
    return _load_effect_catalog_cached(str(selected_root.resolve()))


def clear_catalog_cache() -> None:
    """Limpa o cache para testes e ferramentas de migração."""

    _load_effect_catalog_cached.cache_clear()
