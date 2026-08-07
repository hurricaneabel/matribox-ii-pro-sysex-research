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
CATALOG_VERSION = 15
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
        "identification_status": "validated_with_chain_effect_context",
        "message_match": {
            "parameter_selector": 0,
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
        "effect_identity_source": "current_chain",
        "parameter_selector": 0,
        "evidence": "docs/phases/MBOOST_GAIN_VALIDATION_PHASE22.md",
    },
}

COMP1_PARAMETER_SEEDS: tuple[dict[str, Any], ...] = (
    {
        "key": "sustain",
        "name": "SUSTAIN",
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
            "identification_status": "validated_with_chain_effect_context",
            "message_match": {
                "parameter_selector": 0,
                "parameter_marker": 1,
                "parameter_type": 1,
            },
        },
        "validation": {
            "offline": True,
            "physical": True,
            "read_only": True,
            "range_validated": [0, 100],
            "internal_slots_observed": [1, 2],
            "effect_identity_source": "current_chain",
            "parameter_selector": 0,
            "multiple_parameters": True,
            "physical_fixture_count": 22,
            "evidence": "docs/phases/DYN_COMP1_PARAMETERS_PHASE24.md",
        },
    },
    {
        "key": "volume",
        "name": "VOLUME",
        "display_order": 2,
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
            "identification_status": "validated_with_chain_effect_context",
            "message_match": {
                "parameter_selector": 1,
                "parameter_marker": 1,
                "parameter_type": 1,
            },
        },
        "validation": {
            "offline": True,
            "physical": True,
            "read_only": True,
            "range_validated": [0, 100],
            "internal_slots_observed": [1, 2],
            "effect_identity_source": "current_chain",
            "parameter_selector": 1,
            "multiple_parameters": True,
            "physical_fixture_count": 22,
            "evidence": "docs/phases/DYN_COMP1_PARAMETERS_PHASE24.md",
        },
    },
)


COMP2_PARAMETER_SEEDS: tuple[dict[str, Any], ...] = (
    {
        "key": "sustain",
        "name": "SUSTAIN",
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
            "identification_status": "validated_with_chain_effect_context",
            "message_match": {
                "parameter_selector": 0,
                "parameter_marker": 1,
                "parameter_type": 1,
            },
        },
        "validation": {
            "offline": True,
            "physical": True,
            "read_only": True,
            "range_validated": [0, 100],
            "internal_slots_observed": [1, 2],
            "effect_identity_source": "current_chain",
            "parameter_selector": 0,
            "multiple_parameters": True,
            "physical_fixture_count": 49,
            "evidence": "docs/phases/DYN_COMP2_PARAMETERS_PHASE27.md",
            "monitor_integration_physical_validation": "pending",
        },
    },
    {
        "key": "attack",
        "name": "ATTACK",
        "display_order": 2,
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
            "identification_status": "validated_with_chain_effect_context",
            "message_match": {
                "parameter_selector": 1,
                "parameter_marker": 1,
                "parameter_type": 1,
            },
        },
        "validation": {
            "offline": True,
            "physical": True,
            "read_only": True,
            "range_validated": [0, 100],
            "internal_slots_observed": [1, 2],
            "effect_identity_source": "current_chain",
            "parameter_selector": 1,
            "multiple_parameters": True,
            "physical_fixture_count": 49,
            "evidence": "docs/phases/DYN_COMP2_PARAMETERS_PHASE27.md",
            "monitor_integration_physical_validation": "pending",
        },
    },
    {
        "key": "volume",
        "name": "VOLUME",
        "display_order": 3,
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
            "identification_status": "validated_with_chain_effect_context",
            "message_match": {
                "parameter_selector": 2,
                "parameter_marker": 1,
                "parameter_type": 1,
            },
        },
        "validation": {
            "offline": True,
            "physical": True,
            "read_only": True,
            "range_validated": [0, 100],
            "internal_slots_observed": [1, 2],
            "effect_identity_source": "current_chain",
            "parameter_selector": 2,
            "multiple_parameters": True,
            "physical_fixture_count": 49,
            "evidence": "docs/phases/DYN_COMP2_PARAMETERS_PHASE27.md",
            "monitor_integration_physical_validation": "pending",
        },
    },
    {
        "key": "clipping",
        "name": "CLIPPING",
        "display_order": 4,
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
            "identification_status": "validated_with_chain_effect_context",
            "message_match": {
                "parameter_selector": 3,
                "parameter_marker": 1,
                "parameter_type": 1,
            },
        },
        "validation": {
            "offline": True,
            "physical": True,
            "read_only": True,
            "range_validated": [0, 100],
            "internal_slots_observed": [1, 2],
            "effect_identity_source": "current_chain",
            "parameter_selector": 3,
            "multiple_parameters": True,
            "physical_fixture_count": 49,
            "evidence": "docs/phases/DYN_COMP2_PARAMETERS_PHASE27.md",
            "monitor_integration_physical_validation": "pending",
        },
    },
)


COMP3_PARAMETER_SEEDS: tuple[dict[str, Any], ...] = (
    {
        "key": "threshold",
        "name": "THRESHOLD",
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
            "identification_status": "validated_with_chain_effect_context",
            "message_match": {
                "parameter_selector": 0,
                "parameter_marker": 1,
                "parameter_type": 1,
            },
        },
        "validation": {
            "offline": True,
            "physical": True,
            "read_only": True,
            "range_validated": [0, 100],
            "internal_slots_observed": [1, 2],
            "effect_identity_source": "current_chain",
            "parameter_selector": 0,
            "multiple_parameters": True,
            "physical_fixture_count": 84,
            "evidence": "docs/phases/DYN_COMP3_PARAMETERS_PHASE28.md",
            "monitor_integration_physical_validation": "pending",
        },
    },
    {
        "key": "ratio",
        "name": "RATIO",
        "display_order": 2,
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
            "identification_status": "validated_with_chain_effect_context",
            "message_match": {
                "parameter_selector": 1,
                "parameter_marker": 1,
                "parameter_type": 1,
            },
        },
        "validation": {
            "offline": True,
            "physical": True,
            "read_only": True,
            "range_validated": [0, 100],
            "internal_slots_observed": [1, 2],
            "effect_identity_source": "current_chain",
            "parameter_selector": 1,
            "multiple_parameters": True,
            "physical_fixture_count": 84,
            "evidence": "docs/phases/DYN_COMP3_PARAMETERS_PHASE28.md",
            "monitor_integration_physical_validation": "pending",
        },
    },
    {
        "key": "volume",
        "name": "VOLUME",
        "display_order": 3,
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
            "identification_status": "validated_with_chain_effect_context",
            "message_match": {
                "parameter_selector": 2,
                "parameter_marker": 1,
                "parameter_type": 1,
            },
        },
        "validation": {
            "offline": True,
            "physical": True,
            "read_only": True,
            "range_validated": [0, 100],
            "internal_slots_observed": [1, 2],
            "effect_identity_source": "current_chain",
            "parameter_selector": 2,
            "multiple_parameters": True,
            "physical_fixture_count": 84,
            "evidence": "docs/phases/DYN_COMP3_PARAMETERS_PHASE28.md",
            "monitor_integration_physical_validation": "pending",
        },
    },
    {
        "key": "attack",
        "name": "ATTACK",
        "display_order": 4,
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
            "identification_status": "validated_with_chain_effect_context",
            "message_match": {
                "parameter_selector": 3,
                "parameter_marker": 1,
                "parameter_type": 1,
            },
        },
        "validation": {
            "offline": True,
            "physical": True,
            "read_only": True,
            "range_validated": [0, 100],
            "internal_slots_observed": [1, 2],
            "effect_identity_source": "current_chain",
            "parameter_selector": 3,
            "multiple_parameters": True,
            "physical_fixture_count": 84,
            "evidence": "docs/phases/DYN_COMP3_PARAMETERS_PHASE28.md",
            "monitor_integration_physical_validation": "pending",
        },
    },
    {
        "key": "release",
        "name": "RELEASE",
        "display_order": 5,
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
            "identification_status": "validated_with_chain_effect_context",
            "message_match": {
                "parameter_selector": 4,
                "parameter_marker": 1,
                "parameter_type": 1,
            },
        },
        "validation": {
            "offline": True,
            "physical": True,
            "read_only": True,
            "range_validated": [0, 100],
            "internal_slots_observed": [1, 2],
            "effect_identity_source": "current_chain",
            "parameter_selector": 4,
            "multiple_parameters": True,
            "physical_fixture_count": 84,
            "evidence": "docs/phases/DYN_COMP3_PARAMETERS_PHASE28.md",
            "monitor_integration_physical_validation": "pending",
        },
    },
    {
        "key": "tone",
        "name": "TONE",
        "display_order": 6,
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
            "identification_status": "validated_with_chain_effect_context",
            "message_match": {
                "parameter_selector": 5,
                "parameter_marker": 1,
                "parameter_type": 1,
            },
        },
        "validation": {
            "offline": True,
            "physical": True,
            "read_only": True,
            "range_validated": [0, 100],
            "internal_slots_observed": [1, 2],
            "effect_identity_source": "current_chain",
            "parameter_selector": 5,
            "multiple_parameters": True,
            "physical_fixture_count": 84,
            "evidence": "docs/phases/DYN_COMP3_PARAMETERS_PHASE28.md",
            "monitor_integration_physical_validation": "pending",
        },
    },
    {
        "key": "blend",
        "name": "BLEND",
        "display_order": 7,
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
            "identification_status": "validated_with_chain_effect_context",
            "message_match": {
                "parameter_selector": 6,
                "parameter_marker": 1,
                "parameter_type": 1,
            },
        },
        "validation": {
            "offline": True,
            "physical": True,
            "read_only": True,
            "range_validated": [0, 100],
            "internal_slots_observed": [1, 2],
            "effect_identity_source": "current_chain",
            "parameter_selector": 6,
            "multiple_parameters": True,
            "physical_fixture_count": 84,
            "evidence": "docs/phases/DYN_COMP3_PARAMETERS_PHASE28.md",
            "monitor_integration_physical_validation": "pending",
        },
    }
)




def _four_control_boost_parameter_seeds(
    *,
    evidence: str,
) -> tuple[dict[str, Any], ...]:
    """Cria os quatro controles contínuos compartilhados pelos boosts DYN."""

    return tuple(
        {
            "key": key,
            "name": name,
            "display_order": display_order,
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
                "identification_status": "validated_with_chain_effect_context",
                "message_match": {
                    "parameter_selector": selector,
                    "parameter_marker": 1,
                    "parameter_type": 1,
                },
            },
            "validation": {
                "offline": True,
                "physical": True,
                "read_only": True,
                "range_validated": [0, 100],
                "internal_slots_observed": [1, 2],
                "effect_identity_source": "current_chain",
                "parameter_selector": selector,
                "multiple_parameters": True,
                "physical_fixture_count": 32,
                "evidence": evidence,
                "monitor_integration_physical_validation": "pending",
            },
        }
        for display_order, (key, name, selector) in enumerate(
            (
                ("gain", "GAIN", 0),
                ("volume", "VOLUME", 1),
                ("bass", "BASS", 2),
                ("treble", "TREBLE", 3),
            ),
            start=1,
        )
    )


AC_BOOST_PARAMETER_SEEDS = _four_control_boost_parameter_seeds(
    evidence="docs/phases/DYN_AC_BB_BOOST_PARAMETERS_PHASE29.md",
)
BB_BOOST_PARAMETER_SEEDS = _four_control_boost_parameter_seeds(
    evidence="docs/phases/DYN_AC_BB_BOOST_PARAMETERS_PHASE29.md",
)
RC_BOOST_PARAMETER_SEEDS = _four_control_boost_parameter_seeds(
    evidence="docs/phases/DYN_RC_FAT_BOOST_GATE2_PARAMETERS_PHASE30.md",
)


def _phase30_parameter_seed(
    *,
    key: str,
    name: str,
    display_order: int,
    selector: int,
    value_type: str,
    fixture_count: int,
) -> dict[str, Any]:
    boolean = value_type == "boolean"
    validation: dict[str, Any] = {
        "offline": True,
        "physical": True,
        "read_only": True,
        "internal_slots_observed": [1, 2],
        "effect_identity_source": "current_chain",
        "parameter_selector": selector,
        "multiple_parameters": True,
        "physical_fixture_count": fixture_count,
        "evidence": "docs/phases/DYN_RC_FAT_BOOST_GATE2_PARAMETERS_PHASE30.md",
        "monitor_integration_physical_validation": "pending",
    }
    if boolean:
        validation["boolean_encoding"] = {"false": 0, "true": 1}
    else:
        validation["range_validated"] = [0, 100]
    return {
        "key": key,
        "name": name,
        "display_order": display_order,
        "value_type": value_type,
        "range": {
            "minimum": 0,
            "maximum": 1 if boolean else 100,
            "step": 1,
        },
        "unit": None,
        "protocol": {
            "profile": "effect_parameter_response_1c_v1",
            "value_codec": "upper_float32_nibbles_v1",
            "identification_status": "validated_with_chain_effect_context",
            "message_match": {
                "parameter_selector": selector,
                "parameter_marker": 1,
                "parameter_type": 1,
            },
        },
        "validation": validation,
    }


FAT_BOOST_PARAMETER_SEEDS: tuple[dict[str, Any], ...] = tuple(
    _phase30_parameter_seed(
        key=key,
        name=name,
        display_order=display_order,
        selector=selector,
        value_type=value_type,
        fixture_count=28,
    )
    for display_order, (key, name, selector, value_type) in enumerate(
        (
            ("bass", "BASS", 0, "integer"),
            ("treble", "TREBLE", 1, "integer"),
            ("volume", "VOLUME", 2, "integer"),
            ("low_cut", "LOW CUT", 3, "boolean"),
        ),
        start=1,
    )
)

GATE2_PARAMETER_SEEDS: tuple[dict[str, Any], ...] = tuple(
    _phase30_parameter_seed(
        key=key,
        name=name,
        display_order=display_order,
        selector=selector,
        value_type="integer",
        fixture_count=23,
    )
    for display_order, (key, name, selector) in enumerate(
        (
            ("threshold", "THRESHOLD", 0),
            ("attack", "ATTACK", 1),
            ("release", "RELEASE", 2),
        ),
        start=1,
    )
)


AC_SIM_PARAMETER_SEEDS: tuple[dict[str, Any], ...] = (
    *(
        {
            "key": key,
            "name": name,
            "display_order": display_order,
            "value_type": "integer",
            "range": {"minimum": 0, "maximum": 100, "step": 1},
            "unit": None,
            "protocol": {
                "profile": "effect_parameter_response_1c_v1",
                "value_codec": "upper_float32_nibbles_v1",
                "identification_status": "validated_with_chain_effect_context",
                "message_match": {
                    "parameter_selector": selector,
                    "parameter_marker": 1,
                    "parameter_type": 1,
                },
            },
            "validation": {
                "offline": True,
                "physical": True,
                "read_only": True,
                "range_validated": [0, 100],
                "internal_slots_observed": [1, 2],
                "effect_identity_source": "current_chain",
                "parameter_selector": selector,
                "multiple_parameters": True,
                "physical_fixture_count": 30,
                "evidence": "docs/phases/DYN_AC_SIM_ENUM_PARAMETERS_PHASE31.md",
                "monitor_integration_physical_validation": "pending",
            },
        }
        for display_order, (key, name, selector) in enumerate(
            (("body", "BODY", 0), ("top", "TOP", 1), ("volume", "VOLUME", 2)),
            start=1,
        )
    ),
    {
        "key": "mode",
        "name": "MODE",
        "display_order": 4,
        "value_type": "enum",
        "range": {"minimum": 0, "maximum": 3, "step": 1},
        "choices": [
            {"value": 0, "label": "STANDARD"},
            {"value": 1, "label": "JUMBO"},
            {"value": 2, "label": "ENHANCED"},
            {"value": 3, "label": "PIEZO"},
        ],
        "unit": None,
        "protocol": {
            "profile": "effect_parameter_response_1c_v1",
            "value_codec": "upper_float32_nibbles_v1",
            "identification_status": "validated_with_chain_effect_context",
            "message_match": {
                "parameter_selector": 3,
                "parameter_marker": 1,
                "parameter_type": 1,
            },
        },
        "validation": {
            "offline": True,
            "physical": True,
            "read_only": True,
            "enum_wire_values_validated": [0, 1, 2, 3],
            "internal_slots_observed": [1, 2],
            "effect_identity_source": "current_chain",
            "parameter_selector": 3,
            "multiple_parameters": True,
            "physical_fixture_count": 30,
            "evidence": "docs/phases/DYN_AC_SIM_ENUM_PARAMETERS_PHASE31.md",
            "monitor_integration_physical_validation": "pending",
        },
    },
)


EBOOST_PARAMETER_SEEDS: tuple[dict[str, Any], ...] = (
    {
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
            "identification_status": "validated_with_chain_effect_context",
            "message_match": {
                "parameter_selector": 0,
                "parameter_marker": 1,
                "parameter_type": 1,
            },
        },
        "validation": {
            "offline": True,
            "physical": True,
            "read_only": True,
            "range_validated": [0, 100],
            "internal_slots_observed": [1, 2],
            "effect_identity_source": "current_chain",
            "parameter_selector": 0,
            "multiple_parameters": True,
            "physical_fixture_count": 19,
            "evidence": "docs/phases/DYN_EBOOST_PARAMETERS_PHASE25.md",
            "monitor_integration_physical_validation": "pending",
        },
    },
    {
        "key": "plus_3db",
        "name": "+3dB",
        "display_order": 2,
        "value_type": "boolean",
        "range": {
            "minimum": 0,
            "maximum": 1,
            "step": 1,
        },
        "unit": None,
        "protocol": {
            "profile": "effect_parameter_response_1c_v1",
            "value_codec": "upper_float32_nibbles_v1",
            "identification_status": "validated_with_chain_effect_context",
            "message_match": {
                "parameter_selector": 1,
                "parameter_marker": 1,
                "parameter_type": 1,
            },
        },
        "validation": {
            "offline": True,
            "physical": True,
            "read_only": True,
            "internal_slots_observed": [1, 2],
            "effect_identity_source": "current_chain",
            "parameter_selector": 1,
            "multiple_parameters": True,
            "physical_fixture_count": 19,
            "boolean_encoding": {"false": 0, "true": 1},
            "evidence": "docs/phases/DYN_EBOOST_PARAMETERS_PHASE25.md",
            "monitor_integration_physical_validation": "pending",
        },
    },
    {
        "key": "bright",
        "name": "BRIGHT",
        "display_order": 3,
        "value_type": "boolean",
        "range": {
            "minimum": 0,
            "maximum": 1,
            "step": 1,
        },
        "unit": None,
        "protocol": {
            "profile": "effect_parameter_response_1c_v1",
            "value_codec": "upper_float32_nibbles_v1",
            "identification_status": "validated_with_chain_effect_context",
            "message_match": {
                "parameter_selector": 2,
                "parameter_marker": 1,
                "parameter_type": 1,
            },
        },
        "validation": {
            "offline": True,
            "physical": True,
            "read_only": True,
            "internal_slots_observed": [1, 2],
            "effect_identity_source": "current_chain",
            "parameter_selector": 2,
            "multiple_parameters": True,
            "physical_fixture_count": 19,
            "boolean_encoding": {"false": 0, "true": 1},
            "evidence": "docs/phases/DYN_EBOOST_PARAMETERS_PHASE25.md",
            "monitor_integration_physical_validation": "pending",
        },
    },
)


AC_WOODY_PARAMETER_SEEDS: tuple[dict[str, Any], ...] = (
    {
        "key": "shape",
        "name": "SHAPE",
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
            "identification_status": "validated_with_chain_effect_context",
            "message_match": {
                "parameter_selector": 0,
                "parameter_marker": 1,
                "parameter_type": 1,
            },
        },
        "validation": {
            "offline": True,
            "physical": True,
            "read_only": True,
            "range_validated": [0, 100],
            "internal_slots_observed": [1, 2],
            "effect_identity_source": "current_chain",
            "parameter_selector": 0,
            "single_parameter": True,
            "physical_fixture_count": 11,
            "evidence": "docs/phases/DYN_AC_WOODY_GATE1_PARAMETERS_PHASE26.md",
            "monitor_integration_physical_validation": "pending",
        },
    },
)


GATE1_PARAMETER_SEEDS: tuple[dict[str, Any], ...] = (
    {
        "key": "threshold",
        "name": "THRESHOLD",
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
            "identification_status": "validated_with_chain_effect_context",
            "message_match": {
                "parameter_selector": 0,
                "parameter_marker": 1,
                "parameter_type": 1,
            },
        },
        "validation": {
            "offline": True,
            "physical": True,
            "read_only": True,
            "range_validated": [0, 100],
            "internal_slots_observed": [1, 2],
            "effect_identity_source": "current_chain",
            "parameter_selector": 0,
            "single_parameter": True,
            "physical_fixture_count": 11,
            "evidence": "docs/phases/DYN_AC_WOODY_GATE1_PARAMETERS_PHASE26.md",
            "monitor_integration_physical_validation": "pending",
        },
    },
)


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


GATE3_PARAMETER_SEEDS: tuple[dict[str, Any], ...] = (
    {
        "key": "threshold",
        "name": "THRESHOLD",
        "display_order": 1,
        "value_type": "integer",
        "range": {"minimum": 0, "maximum": 100, "step": 1},
        "unit": None,
        "protocol": {
            "profile": "effect_parameter_response_1c_v1",
            "value_codec": "float32_nibbles_v1",
            "identification_status": "validated_with_chain_effect_context",
            "message_match": {
                "parameter_selector": 0,
                "parameter_marker": 1,
                "parameter_type": 1,
            },
        },
        "validation": {
            "offline": True, "physical": True, "read_only": True,
            "range_validated": [0, 100],
            "internal_slots_observed": [1, 2],
            "effect_identity_source": "current_chain",
            "parameter_selector": 0, "multiple_parameters": True,
            "physical_fixture_count": 58,
            "evidence": "docs/phases/DYN_GATE3_TIME_PARAMETERS_PHASE32.md",
            "monitor_integration_physical_validation": "pending",
        },
    },
    {
        "key": "ratio",
        "name": "RATIO",
        "display_order": 2,
        "value_type": "integer",
        "range": {"minimum": 0, "maximum": 100, "step": 1},
        "unit": None,
        "protocol": {
            "profile": "effect_parameter_response_1c_v1",
            "value_codec": "float32_nibbles_v1",
            "identification_status": "validated_with_chain_effect_context",
            "message_match": {
                "parameter_selector": 1,
                "parameter_marker": 1,
                "parameter_type": 1,
            },
        },
        "validation": {
            "offline": True, "physical": True, "read_only": True,
            "range_validated": [0, 100],
            "internal_slots_observed": [1, 2],
            "effect_identity_source": "current_chain",
            "parameter_selector": 1, "multiple_parameters": True,
            "physical_fixture_count": 58,
            "evidence": "docs/phases/DYN_GATE3_TIME_PARAMETERS_PHASE32.md",
            "monitor_integration_physical_validation": "pending",
        },
    },
    *(
        {
            "key": key,
            "name": name,
            "display_order": order,
            "value_type": "integer",
            "range": {"minimum": minimum, "maximum": maximum, "step": 1},
            "unit": "ms",
            "display": {
                "kind": "duration_milliseconds",
                "seconds_threshold": 1000,
                "seconds_decimals": 1,
                "decimal_separator": ",",
            },
            "protocol": {
                "profile": "effect_parameter_response_1c_v1",
                "value_codec": "float32_nibbles_v1",
                "identification_status": "validated_with_chain_effect_context",
                "message_match": {
                    "parameter_selector": selector,
                    "parameter_marker": 1,
                    "parameter_type": 1,
                },
            },
            "validation": {
                "offline": True, "physical": True, "read_only": True,
                "range_validated": [minimum, maximum],
                "internal_slots_observed": [1, 2],
                "effect_identity_source": "current_chain",
                "parameter_selector": selector, "multiple_parameters": True,
                "physical_fixture_count": 58,
                "evidence": "docs/phases/DYN_GATE3_TIME_PARAMETERS_PHASE32.md",
                "monitor_integration_physical_validation": "pending",
            },
        }
        for key, name, order, selector, minimum, maximum in (
            ("attack", "ATTACK", 3, 2, 1, 500),
            ("release", "RELEASE", 4, 3, 10, 10000),
            ("hold", "HOLD", 5, 4, 0, 1000),
        )
    ),
)



OCTAVER_PARAMETER_SEEDS: tuple[dict[str, Any], ...] = tuple(
    {
        "key": key,
        "name": name,
        "display_order": display_order,
        "value_type": "integer",
        "range": {"minimum": 0, "maximum": 100, "step": 1},
        "unit": None,
        "protocol": {
            "profile": "effect_parameter_response_1c_v1",
            "value_codec": "upper_float32_nibbles_v1",
            "identification_status": "validated_with_chain_effect_context",
            "message_match": {
                "parameter_selector": selector,
                "parameter_marker": 1,
                "parameter_type": 1,
            },
        },
        "validation": {
            "offline": True,
            "physical": True,
            "read_only": True,
            "range_validated": [0, 100],
            "internal_slots_observed": [1, 2],
            "effect_identity_source": "current_chain",
            "parameter_selector": selector,
            "multiple_parameters": True,
            "physical_fixture_count": 24,
            "evidence": "docs/phases/FREQ_OCTAVER_PARAMETERS_PHASE34.md",
            "monitor_integration_physical_validation": "pending",
        },
    }
    for display_order, (key, name, selector) in enumerate(
        (
            ("low_oct", "LOW OCT", 0),
            ("high_oct", "HIGH OCT", 1),
            ("dry", "DRY", 2),
        ),
        start=1,
    )
)


DUAL_MELODY_PARAMETER_SEEDS: tuple[dict[str, Any], ...] = tuple(
    {
        "key": key,
        "name": name,
        "display_order": display_order,
        "value_type": "integer",
        "range": {"minimum": minimum, "maximum": maximum, "step": 1},
        "unit": None,
        "protocol": {
            "profile": "effect_parameter_response_1c_v1",
            "value_codec": "upper_float32_nibbles_v1",
            "identification_status": "validated_with_chain_effect_context",
            "message_match": {
                "parameter_selector": selector,
                "parameter_marker": 1,
                "parameter_type": 1,
            },
        },
        "validation": {
            "offline": True,
            "physical": True,
            "read_only": True,
            "range_validated": [minimum, maximum],
            "internal_slots_observed": [1, 2],
            "effect_identity_source": "current_chain",
            "parameter_selector": selector,
            "multiple_parameters": True,
            "physical_fixture_count": 40,
            "evidence": "docs/phases/FREQ_DUAL_MELODY_SIGNED_PARAMETERS_PHASE35.md",
            "monitor_integration_physical_validation": "pending",
            **(
                {
                    "signed_numeric_encoding": "native_float32_negative",
                    "signed_values_physically_observed": [-24, -23, -14, -13, -12, -1],
                }
                if key == "low_pitch"
                else {}
            ),
        },
    }
    for display_order, (key, name, selector, minimum, maximum) in enumerate(
        (
            ("high_pitch", "HIGH PITCH", 0, 0, 24),
            ("low_pitch", "LOW PITCH", 1, -24, 0),
            ("dry", "DRY", 2, 0, 100),
            ("hi_vol", "HI VOL", 4, 0, 100),
            ("low_vol", "LOW VOL", 5, 0, 100),
        ),
        start=1,
    )
)


PITCH_PARAMETER_SEEDS: tuple[dict[str, Any], ...] = tuple(
    {
        "key": key,
        "name": name,
        "display_order": display_order,
        "value_type": "integer",
        "range": {"minimum": minimum, "maximum": maximum, "step": 1},
        "unit": None,
        "protocol": {
            "profile": "effect_parameter_response_1c_v1",
            "value_codec": "upper_float32_nibbles_v1",
            "identification_status": "validated_with_chain_effect_context",
            "message_match": {
                "parameter_selector": selector,
                "parameter_marker": 1,
                "parameter_type": 1,
            },
        },
        "validation": {
            "offline": True,
            "physical": True,
            "read_only": True,
            "range_validated": [minimum, maximum],
            "internal_slots_observed": [1],
            "effect_identity_source": "current_chain",
            "parameter_selector": selector,
            "multiple_parameters": True,
            "physical_saved_dump_count": 4,
            "saved_dump_defaults": default,
            "evidence": "docs/phases/FREQ_PITCH_SAVED_PARAMETERS_PHASE37.md",
            "monitor_integration_physical_validation": "pending",
            **(
                {
                    "signed_numeric_encoding": "native_float32_negative",
                    "signed_values_physically_observed": [-12, -9, -8, 0],
                }
                if key == "low_pitch"
                else {}
            ),
        },
    }
    for display_order, (key, name, selector, minimum, maximum, default) in enumerate(
        (
            ("high_pitch", "HI PITCH", 0, 0, 12, 12),
            ("low_pitch", "LOW PITCH", 1, -12, 0, 0),
            ("wet", "WET", 2, 0, 100, 50),
            ("dry", "DRY", 3, 0, 100, 50),
            ("range", "RANGE", 4, 0, 100, 50),
        ),
        start=1,
    )
)


HARMONY_D_KEY_CHOICES = (
    "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B",
)
HARMONY_D_MODE_CHOICES = (
    "MAJOR", "MINOR", "H. MINOR", "DORIAN", "PHRYGIAN", "LYDIAN",
    "MIXOLYDIAN", "LOCRIAN",
)
HARMONY_D_INTERVAL_CHOICES = (
    "-OCT", "-7TH", "-6TH", "-5TH", "-4TH", "-3RD", "-2ND",
    "+2ND", "+3RD", "+4TH", "+5TH", "+6TH", "+7TH", "+OCT",
)


HARMONY_D_PARAMETER_SEEDS: tuple[dict[str, Any], ...] = (
    {
        "key": "mix",
        "name": "MIX",
        "display_order": 1,
        "value_type": "integer",
        "range": {"minimum": 0, "maximum": 100, "step": 1},
        "unit": None,
        "protocol": {
            "profile": "effect_parameter_response_1c_v1",
            "value_codec": "upper_float32_nibbles_v1",
            "identification_status": "validated_with_chain_effect_context",
            "message_match": {
                "parameter_selector": 0,
                "parameter_marker": 1,
                "parameter_type": 1,
            },
        },
        "validation": {
            "offline": True,
            "physical": True,
            "read_only": True,
            "range_validated": [0, 100],
            "internal_slots_observed": [1],
            "effect_identity_source": "current_chain",
            "parameter_selector": 0,
            "multiple_parameters": True,
            "saved_dump_default": 50,
            "physical_saved_dump_count": 3,
            "physical_live_response_count": 4,
            "evidence": "docs/phases/FREQ_HARMONY_D_ENUM_PARAMETERS_PHASE38.md",
            "monitor_integration_physical_validation": "pending",
        },
    },
    *(
        {
            "key": key,
            "name": name,
            "display_order": order,
            "value_type": "enum",
            "range": {"minimum": 0, "maximum": len(labels) - 1, "step": 1},
            "choices": [
                {"value": value, "label": label}
                for value, label in enumerate(labels)
            ],
            "unit": None,
            "protocol": {
                "profile": "effect_parameter_response_1c_v1",
                "value_codec": "upper_float32_nibbles_v1",
                "identification_status": "validated_with_chain_effect_context",
                "message_match": {
                    "parameter_selector": selector,
                    "parameter_marker": 1,
                    "parameter_type": 1,
                },
            },
            "validation": {
                "offline": True,
                "physical": True,
                "read_only": True,
                "enum_wire_values_validated": list(range(len(labels))),
                "internal_slots_observed": [1],
                "effect_identity_source": "current_chain",
                "parameter_selector": selector,
                "multiple_parameters": True,
                "saved_dump_default": default,
                "physical_saved_dump_count": 3,
                "physical_live_sweep": True,
                "evidence": "docs/phases/FREQ_HARMONY_D_ENUM_PARAMETERS_PHASE38.md",
                "monitor_integration_physical_validation": "pending",
            },
        }
        for key, name, order, selector, labels, default in (
            ("key", "KEY", 2, 1, HARMONY_D_KEY_CHOICES, 0),
            ("mode", "MODE", 3, 2, HARMONY_D_MODE_CHOICES, 0),
            ("interval_1", "INTERVAL 1", 4, 3, HARMONY_D_INTERVAL_CHOICES, 8),
            ("interval_2", "INTERVAL 2", 5, 4, HARMONY_D_INTERVAL_CHOICES, 10),
        )
    ),
    {
        "key": "smooth",
        "name": "SMOOTH",
        "display_order": 6,
        "value_type": "boolean",
        "range": {"minimum": 0, "maximum": 1, "step": 1},
        "unit": None,
        "protocol": {
            "profile": "effect_parameter_response_1c_v1",
            "value_codec": "upper_float32_nibbles_v1",
            "identification_status": "validated_with_chain_effect_context",
            "message_match": {
                "parameter_selector": 6,
                "parameter_marker": 1,
                "parameter_type": 1,
            },
        },
        "validation": {
            "offline": True,
            "physical": True,
            "read_only": True,
            "internal_slots_observed": [1],
            "effect_identity_source": "current_chain",
            "parameter_selector": 6,
            "incoming_selector_gap": 5,
            "multiple_parameters": True,
            "saved_dump_default": False,
            "boolean_encoding": {"false": 0, "true": 1},
            "physical_saved_dump_count": 3,
            "physical_live_response_count": 2,
            "evidence": "docs/phases/FREQ_HARMONY_D_ENUM_PARAMETERS_PHASE38.md",
            "monitor_integration_physical_validation": "pending",
        },
    },
)


FILTER_PARAMETER_SEEDS: tuple[dict[str, Any], ...] = tuple([{'key': 'step_1',
  'name': 'STEP 1',
  'display_order': 1,
  'value_type': 'integer',
  'range': {'minimum': 0, 'maximum': 100, 'step': 1},
  'unit': None,
  'protocol': {'profile': 'effect_parameter_response_1c_v1',
               'value_codec': 'upper_float32_nibbles_v1',
               'identification_status': 'validated_with_chain_effect_context',
               'message_match': {'parameter_selector': 0,
                                 'parameter_marker': 1,
                                 'parameter_type': 1}},
  'validation': {'offline': True,
                 'physical': True,
                 'read_only': True,
                 'range_validated': [0, 100],
                 'internal_slots_observed': [1, 2],
                 'effect_identity_source': 'current_chain',
                 'parameter_selector': 0,
                 'multiple_parameters': True,
                 'physical_fixture_count': 55,
                 'evidence': 'docs/phases/FREQ_FILTER_PARAMETERS_PHASE33.md',
                 'monitor_integration_physical_validation': 'pending'}},
 {'key': 'step_2',
  'name': 'STEP 2',
  'display_order': 2,
  'value_type': 'integer',
  'range': {'minimum': 0, 'maximum': 100, 'step': 1},
  'unit': None,
  'protocol': {'profile': 'effect_parameter_response_1c_v1',
               'value_codec': 'upper_float32_nibbles_v1',
               'identification_status': 'validated_with_chain_effect_context',
               'message_match': {'parameter_selector': 1,
                                 'parameter_marker': 1,
                                 'parameter_type': 1}},
  'validation': {'offline': True,
                 'physical': True,
                 'read_only': True,
                 'range_validated': [0, 100],
                 'internal_slots_observed': [1, 2],
                 'effect_identity_source': 'current_chain',
                 'parameter_selector': 1,
                 'multiple_parameters': True,
                 'physical_fixture_count': 55,
                 'evidence': 'docs/phases/FREQ_FILTER_PARAMETERS_PHASE33.md',
                 'monitor_integration_physical_validation': 'pending'}},
 {'key': 'step_3',
  'name': 'STEP 3',
  'display_order': 3,
  'value_type': 'integer',
  'range': {'minimum': 0, 'maximum': 100, 'step': 1},
  'unit': None,
  'protocol': {'profile': 'effect_parameter_response_1c_v1',
               'value_codec': 'upper_float32_nibbles_v1',
               'identification_status': 'validated_with_chain_effect_context',
               'message_match': {'parameter_selector': 2,
                                 'parameter_marker': 1,
                                 'parameter_type': 1}},
  'validation': {'offline': True,
                 'physical': True,
                 'read_only': True,
                 'range_validated': [0, 100],
                 'internal_slots_observed': [1, 2],
                 'effect_identity_source': 'current_chain',
                 'parameter_selector': 2,
                 'multiple_parameters': True,
                 'physical_fixture_count': 55,
                 'evidence': 'docs/phases/FREQ_FILTER_PARAMETERS_PHASE33.md',
                 'monitor_integration_physical_validation': 'pending'}},
 {'key': 'step_4',
  'name': 'STEP 4',
  'display_order': 4,
  'value_type': 'integer',
  'range': {'minimum': 0, 'maximum': 100, 'step': 1},
  'unit': None,
  'protocol': {'profile': 'effect_parameter_response_1c_v1',
               'value_codec': 'upper_float32_nibbles_v1',
               'identification_status': 'validated_with_chain_effect_context',
               'message_match': {'parameter_selector': 3,
                                 'parameter_marker': 1,
                                 'parameter_type': 1}},
  'validation': {'offline': True,
                 'physical': True,
                 'read_only': True,
                 'range_validated': [0, 100],
                 'internal_slots_observed': [1, 2],
                 'effect_identity_source': 'current_chain',
                 'parameter_selector': 3,
                 'multiple_parameters': True,
                 'physical_fixture_count': 55,
                 'evidence': 'docs/phases/FREQ_FILTER_PARAMETERS_PHASE33.md',
                 'monitor_integration_physical_validation': 'pending'}},
 {'key': 'rate',
  'name': 'RATE',
  'display_order': 5,
  'value_type': 'integer',
  'range': {'minimum': 0, 'maximum': 100, 'step': 1},
  'unit': None,
  'value_domain': {'controller_parameter': 'sync',
                   'reset_on_controller_change': True,
                   'states': [{'controller_value': False,
                               'default_value': 10,
                               'presentation': {'kind': 'numeric'}},
                              {'controller_value': True,
                               'default_value': 4,
                               'presentation': {'kind': 'enum',
                                                'choices': [{'value': 0, 'label': '1/1'},
                                                            {'value': 1, 'label': '1/2'},
                                                            {'value': 2, 'label': '1/2d'},
                                                            {'value': 3, 'label': '1/2t'},
                                                            {'value': 4, 'label': '1/4'},
                                                            {'value': 5, 'label': '1/4d'},
                                                            {'value': 6, 'label': '1/4t'},
                                                            {'value': 7, 'label': '1/8'},
                                                            {'value': 8, 'label': '1/8d'},
                                                            {'value': 9, 'label': '1/8t'},
                                                            {'value': 10, 'label': '1/16'}]}}]},
  'protocol': {'profile': 'effect_parameter_response_1c_v1',
               'value_codec': 'upper_float32_nibbles_v1',
               'identification_status': 'validated_with_chain_effect_context',
               'message_match': {'parameter_selector': 4,
                                 'parameter_marker': 1,
                                 'parameter_type': 1}},
  'validation': {'offline': True,
                 'physical': True,
                 'read_only': True,
                 'range_validated': [0, 100],
                 'internal_slots_observed': [1, 2],
                 'effect_identity_source': 'current_chain',
                 'parameter_selector': 4,
                 'multiple_parameters': True,
                 'physical_fixture_count': 55,
                 'conditional_domain_controller': 'sync',
                 'sync_off_default': 10,
                 'sync_on_default_wire_value': 4,
                 'sync_on_default_label': '1/4',
                 'implicit_default_has_separate_usb_event': False,
                 'evidence': 'docs/phases/FREQ_FILTER_PARAMETERS_PHASE33.md',
                 'monitor_integration_physical_validation': 'pending'}},
 {'key': 'sync',
  'name': 'SYNC',
  'display_order': 6,
  'value_type': 'boolean',
  'range': {'minimum': 0, 'maximum': 1, 'step': 1},
  'unit': None,
  'protocol': {'profile': 'effect_parameter_response_1c_v1',
               'value_codec': 'upper_float32_nibbles_v1',
               'identification_status': 'validated_with_chain_effect_context',
               'message_match': {'parameter_selector': 5,
                                 'parameter_marker': 1,
                                 'parameter_type': 1}},
  'validation': {'offline': True,
                 'physical': True,
                 'read_only': True,
                 'internal_slots_observed': [1, 2],
                 'effect_identity_source': 'current_chain',
                 'parameter_selector': 5,
                 'multiple_parameters': True,
                 'physical_fixture_count': 55,
                 'boolean_encoding': {'false': 0, 'true': 1},
                 'evidence': 'docs/phases/FREQ_FILTER_PARAMETERS_PHASE33.md',
                 'monitor_integration_physical_validation': 'pending'}}])


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
    if parameter.choices:
        document["choices"] = [
            {"value": value, "label": label}
            for value, label in parameter.choices.items()
        ]
    if parameter.display:
        document["display"] = dict(parameter.display)
    if parameter.value_domain:
        document["value_domain"] = dict(parameter.value_domain)
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

    if effect_key == "freq.filter" and not parameters:
        parameters = list(FILTER_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "freq.octaver" and not parameters:
        parameters = list(OCTAVER_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "freq.dual_melody" and not parameters:
        parameters = list(DUAL_MELODY_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "freq.pitch" and not parameters:
        parameters = list(PITCH_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "freq.harmony_d" and not parameters:
        parameters = list(HARMONY_D_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "dyn.m_boost" and not parameters:
        parameters = [MBOOST_GAIN_SEED]
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "dyn.comp1" and not parameters:
        parameters = list(COMP1_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "dyn.comp2" and not parameters:
        parameters = list(COMP2_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "dyn.comp3" and not parameters:
        parameters = list(COMP3_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "dyn.ac_boost" and not parameters:
        parameters = list(AC_BOOST_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "dyn.bb_boost" and not parameters:
        parameters = list(BB_BOOST_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "dyn.rc_boost" and not parameters:
        parameters = list(RC_BOOST_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "dyn.fat_boost" and not parameters:
        parameters = list(FAT_BOOST_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "dyn.gate_2" and not parameters:
        parameters = list(GATE2_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "dyn.gate_3" and not parameters:
        parameters = list(GATE3_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "dyn.ac_sim" and not parameters:
        parameters = list(AC_SIM_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "dyn.e_boost" and not parameters:
        parameters = list(EBOOST_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "dyn.ac_woody" and not parameters:
        parameters = list(AC_WOODY_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "dyn.gate_1" and not parameters:
        parameters = list(GATE1_PARAMETER_SEEDS)
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
            "value_codecs/upper_float32_nibbles_v1.json",
            "value_codecs/float32_nibbles_v1.json",
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
