"""Exporta o catálogo Python histórico para o formato JSON portátil.

Esta ferramenta existe para tornar a migração da Fase 23 reproduzível. Ela
preserva IDs, seletores, ordem de menu e parâmetros já presentes nos objetos
carregados. Por segurança, não sobrescreve um catálogo existente sem
``--force``.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import unicodedata
from typing import Any, Iterable

from tools.catalog.models import EffectClass, EffectModel, ParameterDefinition


SCHEMA_VERSION = 1
CATALOG_VERSION = 1
CLASS_INDEX_ORDER = (
    "freq",
    "drv",
    "dyn",
    "wah",
    "amp",
    "cab",
    "ir",
    "eq",
    "mod",
    "dly",
    "rvb",
    "clone",
    "fx_loop",
    "fx_send",
    "fx_return",
    "vol",
)


MBOOST_GAIN_SEED: dict[str, Any] = {
    "key": "gain",
    "name": "GAIN",
    "display_order": 1,
    "value_type": "integer",
    "range": {
        "minimum": 0,
        "maximum": 100,
        "step": 1,
    },
    "unit": None,
    "protocol": {
        "profile": "effect_parameter_response_1c_v1",
        "value_codec": "upper_float32_nibbles_v1",
        "identification_status": "validated_single_parameter_effect",
        "message_match": {
            "parameter_marker": 1,
            "parameter_type": 1,
        },
    },
    "validation": {
        "offline": True,
        "physical": True,
        "read_only": True,
        "range_validated": [0, 100],
        "internal_slots_observed": [2, 8, 10, 12],
        "all_twelve_slot_addresses_supported": True,
        "multiple_instances": True,
        "visual_reordering_independent": True,
        "physical_fixture_count": 27,
        "evidence": "docs/phases/MBOOST_GAIN_VALIDATION_PHASE22.md",
    },
}


def slugify(value: str) -> str:
    """Cria uma chave ASCII estável, preservando o significado de ``+``."""

    expanded = value.replace("+", " plus ").replace("&", " and ")
    ascii_value = unicodedata.normalize("NFKD", expanded).encode(
        "ascii",
        "ignore",
    ).decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", ascii_value).strip("_").lower()
    return slug or "unnamed"


def _write_json(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _parameter_document(parameter: ParameterDefinition) -> dict[str, Any]:
    document: dict[str, Any] = {
        "key": parameter.key,
        "name": parameter.name,
        "display_order": parameter.display_order,
        "value_type": parameter.value_type,
        "unit": parameter.unit,
    }
    if (
        parameter.minimum is not None
        and parameter.maximum is not None
        and parameter.step is not None
    ):
        document["range"] = {
            "minimum": parameter.minimum,
            "maximum": parameter.maximum,
            "step": parameter.step,
        }
    if parameter.protocol_profile is not None and parameter.value_codec is not None:
        document["protocol"] = {
            "profile": parameter.protocol_profile,
            "value_codec": parameter.value_codec,
            "identification_status": parameter.identification_status,
            "message_match": dict(parameter.message_match),
        }
    document["validation"] = dict(parameter.validation)
    return document


def _effect_document(
    effect_class: EffectClass,
    model: EffectModel,
    *,
    class_key: str,
) -> dict[str, Any]:
    effect_key = getattr(model, "key", "") or f"{class_key}.{slugify(model.name)}"
    parameters = [_parameter_document(item) for item in getattr(model, "parameters", ())]
    capabilities = list(getattr(model, "capabilities", ()))
    status = getattr(model, "parameter_catalog_status", "pending")

    if effect_key == "dyn.m_boost" and not parameters:
        parameters = [MBOOST_GAIN_SEED]
        capabilities = ["parameters"]
        status = "physically_validated"

    return {
        "$schema": "../../schemas/effect.schema.json",
        "schema_version": SCHEMA_VERSION,
        "key": effect_key,
        "class_key": class_key,
        "menu_number": model.menu_number,
        "name": model.name,
        "model_id": model.model_id,
        "secondary_selector": model.secondary_selector,
        "capabilities": capabilities,
        "parameter_catalog_status": status,
        "parameters": parameters,
    }


def export_catalog(
    classes: Iterable[EffectClass],
    output_root: Path,
    *,
    force: bool = False,
) -> None:
    """Escreve um catálogo determinístico a partir das classes fornecidas."""

    classes_tuple = tuple(sorted(classes, key=lambda item: item.menu_number))
    if output_root.exists():
        if not force:
            raise FileExistsError(
                f"O diretório já existe: {output_root}. Use --force para substituir."
            )
        # A exportação é dona apenas do manifesto e de ``effects/``. Schemas,
        # perfis e codecs são contratos versionados e não devem ser apagados.
        shutil.rmtree(output_root / "effects", ignore_errors=True)
        manifest_path = output_root / "catalog.json"
        if manifest_path.exists():
            manifest_path.unlink()
    else:
        output_root.mkdir(parents=True)

    class_indexes: list[str] = []
    used_class_keys: set[str] = set()
    used_effect_keys: set[str] = set()

    for effect_class in classes_tuple:
        class_key = getattr(effect_class, "key", "") or slugify(effect_class.name)
        if class_key in used_class_keys:
            raise ValueError(f"Chave de classe duplicada: {class_key}")
        used_class_keys.add(class_key)

        class_directory = output_root / "effects" / class_key
        effect_files: list[str] = []
        for model in sorted(effect_class.models, key=lambda item: item.menu_number):
            document = _effect_document(
                effect_class,
                model,
                class_key=class_key,
            )
            effect_key = document["key"]
            if effect_key in used_effect_keys:
                raise ValueError(f"Chave global de efeito duplicada: {effect_key}")
            used_effect_keys.add(effect_key)

            filename = f"{model.menu_number:03d}_{slugify(model.name)}.json"
            effect_files.append(filename)
            _write_json(class_directory / filename, document)

        index_document = {
            "$schema": "../../schemas/class-index.schema.json",
            "schema_version": SCHEMA_VERSION,
            "key": class_key,
            "menu_number": effect_class.menu_number,
            "name": effect_class.name,
            "class_id": effect_class.class_id,
            "effect_files": effect_files,
        }
        _write_json(class_directory / "index.json", index_document)
        class_indexes.append(f"effects/{class_key}/index.json")

    manifest = {
        "$schema": "schemas/catalog.schema.json",
        "schema_version": SCHEMA_VERSION,
        "catalog_version": CATALOG_VERSION,
        "device": {
            "manufacturer": "Sonicake",
            "model": "Matribox II Pro",
        },
        "class_indexes": class_indexes,
        "protocol_profiles": [
            "protocol_profiles/effect_parameter_response_1c_v1.json"
        ],
        "value_codecs": [
            "value_codecs/upper_float32_nibbles_v1.json"
        ],
    }
    _write_json(output_root / "catalog.json", manifest)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("catalog"),
        help="Diretório de saída (padrão: catalog)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Substitui o diretório de saída se ele já existir",
    )
    arguments = parser.parse_args()

    # Import tardio para permitir que este módulo seja testado com classes
    # fornecidas diretamente e para manter a ferramenta desacoplada do facade.
    from tools.commands.effect_catalog import EFFECT_CLASSES

    export_catalog(EFFECT_CLASSES, arguments.output, force=arguments.force)
    print(
        f"Catálogo exportado: {len(EFFECT_CLASSES)} classes, "
        f"{sum(len(item.models) for item in EFFECT_CLASSES)} efeitos."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
