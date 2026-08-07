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

    raw_choices = document.get("choices")
    normalized_choices: dict[int, str] = {}
    if value_type == "enum":
        if not isinstance(raw_choices, list) or not raw_choices:
            raise _fail(path, "parâmetro enum deve declarar choices não vazias")
        labels: set[str] = set()
        for choice in raw_choices:
            if not isinstance(choice, dict):
                raise _fail(path, "cada item de choices deve ser objeto")
            wire_value = choice.get("value")
            label = choice.get("label")
            if isinstance(wire_value, bool) or not isinstance(wire_value, int):
                raise _fail(path, "choices.value deve ser inteiro")
            if not isinstance(label, str) or not label.strip():
                raise _fail(path, "choices.label deve ser texto não vazio")
            if wire_value in normalized_choices:
                raise _fail(path, f"choices possui valor duplicado: {wire_value}")
            if label in labels:
                raise _fail(path, f"choices possui label duplicado: {label!r}")
            normalized_choices[wire_value] = label
            labels.add(label)
        if minimum is None or maximum is None or step is None:
            raise _fail(path, "parâmetro enum deve declarar range numérico")
        tolerance = 1e-9
        for wire_value in normalized_choices:
            if wire_value < minimum or wire_value > maximum:
                raise _fail(path, f"choice {wire_value} fora do range declarado")
            steps = (float(wire_value) - float(minimum)) / float(step)
            if abs(steps - round(steps)) > tolerance:
                raise _fail(path, f"choice {wire_value} não respeita range.step")
    elif raw_choices is not None:
        raise _fail(path, "campo choices é permitido somente para value_type enum")
    choices = MappingProxyType(normalized_choices)

    raw_display = document.get("display", {})
    if not isinstance(raw_display, dict):
        raise _fail(path, "campo 'display' deve ser objeto")
    normalized_display: dict[str, Any] = {}
    if raw_display:
        kind = raw_display.get("kind")
        if kind != "duration_milliseconds":
            raise _fail(path, f"display.kind não suportado: {kind!r}")
        seconds_threshold = raw_display.get("seconds_threshold", 1000)
        seconds_decimals = raw_display.get("seconds_decimals", 1)
        decimal_separator = raw_display.get("decimal_separator", ",")
        if (
            isinstance(seconds_threshold, bool)
            or not isinstance(seconds_threshold, (int, float))
            or seconds_threshold <= 0
        ):
            raise _fail(path, "display.seconds_threshold deve ser número positivo")
        if (
            isinstance(seconds_decimals, bool)
            or not isinstance(seconds_decimals, int)
            or not 0 <= seconds_decimals <= 6
        ):
            raise _fail(path, "display.seconds_decimals deve ser inteiro entre 0 e 6")
        if decimal_separator not in {".", ","}:
            raise _fail(path, "display.decimal_separator deve ser '.' ou ','")
        normalized_display = {
            "kind": kind,
            "seconds_threshold": seconds_threshold,
            "seconds_decimals": seconds_decimals,
            "decimal_separator": decimal_separator,
        }
    display = MappingProxyType(normalized_display)

    raw_value_domain = document.get("value_domain", {})
    if not isinstance(raw_value_domain, dict):
        raise _fail(path, "campo 'value_domain' deve ser objeto")
    normalized_value_domain: dict[str, Any] = {}
    if raw_value_domain:
        controller_parameter = raw_value_domain.get("controller_parameter")
        if not isinstance(controller_parameter, str) or not controller_parameter.strip():
            raise _fail(path, "value_domain.controller_parameter deve ser texto não vazio")
        if controller_parameter == key:
            raise _fail(path, "value_domain não pode depender do próprio parâmetro")
        reset_on_change = raw_value_domain.get("reset_on_controller_change", True)
        if not isinstance(reset_on_change, bool):
            raise _fail(path, "value_domain.reset_on_controller_change deve ser booleano")
        raw_states = raw_value_domain.get("states")
        if not isinstance(raw_states, list) or not raw_states:
            raise _fail(path, "value_domain.states deve ser lista não vazia")
        normalized_states: list[dict[str, Any]] = []
        controller_values: set[tuple[type, Any]] = set()
        for state in raw_states:
            if not isinstance(state, dict):
                raise _fail(path, "cada estado de value_domain deve ser objeto")
            controller_value = state.get("controller_value")
            if isinstance(controller_value, (dict, list)) or controller_value is None:
                raise _fail(path, "value_domain.states.controller_value inválido")
            identity = (type(controller_value), controller_value)
            if identity in controller_values:
                raise _fail(path, "value_domain possui controller_value duplicado")
            controller_values.add(identity)
            default_value = state.get("default_value")
            if isinstance(default_value, bool) or not isinstance(default_value, (int, float)):
                raise _fail(path, "value_domain.states.default_value deve ser número")
            if minimum is not None and default_value < minimum:
                raise _fail(path, "value_domain default abaixo do range")
            if maximum is not None and default_value > maximum:
                raise _fail(path, "value_domain default acima do range")
            presentation = state.get("presentation")
            if not isinstance(presentation, dict):
                raise _fail(path, "value_domain.states.presentation deve ser objeto")
            kind = presentation.get("kind")
            normalized_presentation: dict[str, Any] = {"kind": kind}
            if kind == "numeric":
                pass
            elif kind == "enum":
                raw_domain_choices = presentation.get("choices")
                if not isinstance(raw_domain_choices, list) or not raw_domain_choices:
                    raise _fail(path, "presentation enum deve declarar choices")
                choices_list: list[dict[str, Any]] = []
                seen_values: set[int] = set()
                seen_labels: set[str] = set()
                for choice in raw_domain_choices:
                    if not isinstance(choice, dict):
                        raise _fail(path, "choice de value_domain deve ser objeto")
                    wire_value = choice.get("value")
                    label = choice.get("label")
                    if isinstance(wire_value, bool) or not isinstance(wire_value, int):
                        raise _fail(path, "choice value de value_domain deve ser inteiro")
                    if not isinstance(label, str) or not label.strip():
                        raise _fail(path, "choice label de value_domain inválido")
                    if wire_value in seen_values or label in seen_labels:
                        raise _fail(path, "choices duplicadas em value_domain")
                    seen_values.add(wire_value); seen_labels.add(label)
                    choices_list.append({"value": wire_value, "label": label})
                if int(default_value) not in seen_values:
                    raise _fail(path, "default enum de value_domain não está nas choices")
                normalized_presentation["choices"] = choices_list
            else:
                raise _fail(path, f"presentation.kind de value_domain não suportado: {kind!r}")
            normalized_states.append({
                "controller_value": controller_value,
                "default_value": default_value,
                "presentation": normalized_presentation,
            })
        normalized_value_domain = {
            "controller_parameter": controller_parameter,
            "reset_on_controller_change": reset_on_change,
            "states": normalized_states,
        }
    value_domain = MappingProxyType(normalized_value_domain)

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
        choices=choices,
        display=display,
        value_domain=value_domain,
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
    parameter_by_key = {parameter.key: parameter for parameter in parameters}
    for parameter in parameters:
        controller_key = parameter.value_domain.get("controller_parameter") if parameter.value_domain else None
        if controller_key is not None and controller_key not in parameter_by_key:
            raise _fail(
                path,
                f"value_domain de {parameter.key} referencia controlador inexistente: {controller_key}",
            )
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


def _validate_profile_document(document: Mapping[str, Any], path: Path) -> None:
    direction = _require_string(document, "direction", path)
    if direction not in {"incoming", "outgoing", "bidirectional"}:
        raise _fail(path, f"direction inválida: {direction}")

    message_length = _require_integer(
        document, "message_length", path, minimum=1
    )
    _require_integer(document, "command", path, minimum=0, maximum=0x7F)

    fields = document.get("fields")
    if not isinstance(fields, dict):
        raise _fail(path, "campo 'fields' deve ser objeto")

    required_fields = {
        "checksum",
        "direction",
        "command",
        "internal_slot",
        "value",
    }
    missing = sorted(required_fields.difference(fields))
    if missing:
        raise _fail(path, "campos obrigatórios ausentes: " + ", ".join(missing))

    for field_name, field in fields.items():
        if not isinstance(field_name, str) or not field_name:
            raise _fail(path, "fields possui chave inválida")
        if not isinstance(field, dict):
            raise _fail(path, f"fields.{field_name} deve ser objeto")
        if "index" in field:
            index = field["index"]
            if isinstance(index, bool) or not isinstance(index, int):
                raise _fail(path, f"fields.{field_name}.index deve ser inteiro")
            if not 0 <= index < message_length:
                raise _fail(path, f"fields.{field_name}.index fora da mensagem")
        if "indices" in field:
            indices = field["indices"]
            if (
                not isinstance(indices, list)
                or len(indices) != 2
                or any(isinstance(item, bool) or not isinstance(item, int) for item in indices)
                or any(not 0 <= item < message_length for item in indices)
            ):
                raise _fail(path, f"fields.{field_name}.indices inválido")
        if "start_index" in field or "end_index_exclusive" in field:
            start = field.get("start_index")
            end = field.get("end_index_exclusive")
            if (
                isinstance(start, bool)
                or not isinstance(start, int)
                or isinstance(end, bool)
                or not isinstance(end, int)
                or not 0 <= start < end <= message_length
            ):
                raise _fail(path, f"faixa de fields.{field_name} inválida")

    segments = document.get("fixed_segments", [])
    if not isinstance(segments, list):
        raise _fail(path, "fixed_segments deve ser lista")
    occupied: set[int] = set()
    for segment in segments:
        if not isinstance(segment, dict):
            raise _fail(path, "fixed_segments contém item inválido")
        start = segment.get("start_index")
        values = segment.get("bytes")
        if isinstance(start, bool) or not isinstance(start, int):
            raise _fail(path, "fixed_segments.start_index deve ser inteiro")
        if (
            not isinstance(values, list)
            or not values
            or any(
                isinstance(value, bool)
                or not isinstance(value, int)
                or not 0 <= value <= 0xFF
                for value in values
            )
        ):
            raise _fail(path, "fixed_segments.bytes inválido")
        indices = set(range(start, start + len(values)))
        if start < 0 or start + len(values) > message_length:
            raise _fail(path, "fixed_segments excede message_length")
        if occupied.intersection(indices):
            raise _fail(path, "fixed_segments possui sobreposição")
        occupied.update(indices)


def _validate_codec_document(document: Mapping[str, Any], path: Path) -> None:
    _require_string(document, "kind", path)
    _require_integer(document, "encoded_length", path, minimum=1)
    _require_string(document, "description", path)
    configuration = document.get("configuration", {})
    if not isinstance(configuration, dict):
        raise _fail(path, "configuration deve ser objeto")


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
        if kind is ProtocolProfile:
            _validate_profile_document(document, path)
        elif kind is ValueCodec:
            _validate_codec_document(document, path)
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

    profiles_by_key = {profile.key: profile for profile in protocol_profiles}
    codecs_by_key = {codec.key: codec for codec in value_codecs}
    for effect_class in classes_tuple:
        for effect in effect_class.models:
            for parameter in effect.parameters:
                profile = profiles_by_key.get(parameter.protocol_profile or "")
                if profile is None:
                    raise _fail(
                        manifest_path,
                        f"parâmetro {effect.key}.{parameter.key} referencia perfil inexistente",
                    )
                codec = codecs_by_key.get(parameter.value_codec or "")
                if codec is None:
                    raise _fail(
                        manifest_path,
                        f"parâmetro {effect.key}.{parameter.key} referencia codec inexistente",
                    )

                fields = profile.document.get("fields", {})
                for match_key in parameter.message_match:
                    if match_key not in fields:
                        raise _fail(
                            manifest_path,
                            f"parâmetro {effect.key}.{parameter.key} usa message_match inexistente: {match_key}",
                        )

                value_field = fields.get("value", {})
                start = value_field.get("start_index")
                end = value_field.get("end_index_exclusive")
                encoded_length = codec.document.get("encoded_length")
                if isinstance(start, int) and isinstance(end, int):
                    payload_length = end - start
                    configuration = codec.document.get("configuration", {})
                    input_slice = (
                        configuration.get("input_slice")
                        if isinstance(configuration, dict)
                        else None
                    )
                    if input_slice is None:
                        compatible = payload_length == encoded_length
                    else:
                        compatible = (
                            isinstance(input_slice, list)
                            and len(input_slice) == 2
                            and all(
                                not isinstance(item, bool) and isinstance(item, int)
                                for item in input_slice
                            )
                            and 0 <= input_slice[0] < input_slice[1] <= payload_length
                            and input_slice[1] - input_slice[0] == encoded_length
                        )
                    if not compatible:
                        raise _fail(
                            manifest_path,
                            f"parâmetro {effect.key}.{parameter.key} possui codec com tamanho incompatível",
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
