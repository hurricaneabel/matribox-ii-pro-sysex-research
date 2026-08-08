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
CATALOG_VERSION = 59
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


AUTO_WAH_PARAMETER_SEEDS: tuple[dict[str, Any], ...] = (
    {
        "key": "depth",
        "name": "DEPTH",
        "display_order": 1,
        "value_type": "integer",
        "range": {"minimum": 0, "maximum": 100, "step": 1},
        "unit": None,
        "protocol": {
            "profile": "effect_parameter_response_1c_v1",
            "value_codec": "upper_float32_nibbles_v1",
            "identification_status": "validated_with_chain_effect_context",
            "message_match": {"parameter_selector": 0, "parameter_marker": 1, "parameter_type": 1},
        },
        "validation": {
            "offline": True, "physical": True, "read_only": True,
            "range_validated": [0, 100], "internal_slots_observed": [1],
            "effect_identity_source": "current_chain", "parameter_selector": 0,
            "saved_dump_default": 50,
            "evidence": "docs/phases/WAH_AUTO_WAH_SYNC_RATE_PARAMETERS_PHASE47.md",
            "monitor_integration_physical_validation": "approved",
        },
    },
    {
        "key": "rate",
        "name": "RATE",
        "display_order": 2,
        "value_type": "number",
        "range": {"minimum": 0, "maximum": 10, "step": 0.1},
        "unit": None,
        "value_domain": {
            "controller_parameter": "sync",
            "reset_on_controller_change": True,
            "states": [
                {
                    "controller_value": False,
                    "default_value": 0.5,
                    "presentation": {"kind": "numeric", "unit": "Hz", "decimals": 1},
                },
                {
                    "controller_value": True,
                    "default_value": 4,
                    "presentation": {
                        "kind": "enum",
                        "choices": [
                            {"value": 0, "label": "1/1"},
                            {"value": 1, "label": "1/2"},
                            {"value": 2, "label": "1/2D"},
                            {"value": 3, "label": "1/2T"},
                            {"value": 4, "label": "1/4"},
                            {"value": 5, "label": "1/4D"},
                            {"value": 6, "label": "1/4T"},
                            {"value": 7, "label": "1/8"},
                            {"value": 8, "label": "1/8D"},
                            {"value": 9, "label": "1/8T"},
                            {"value": 10, "label": "1/16"},
                        ],
                    },
                },
            ],
        },
        "protocol": {
            "profile": "effect_parameter_response_1c_v1",
            "value_codec": "float32_nibbles_v1",
            "identification_status": "validated_with_chain_effect_context",
            "message_match": {"parameter_selector": 1, "parameter_marker": 1, "parameter_type": 1},
        },
        "validation": {
            "offline": True, "physical": True, "read_only": True,
            "range_validated": [0.1, 10.0], "step_validated": 0.1,
            "internal_slots_observed": [1], "effect_identity_source": "current_chain",
            "parameter_selector": 1, "conditional_domain_controller": "sync",
            "sync_off_default": 0.5, "sync_on_default_wire_value": 4,
            "sync_on_default_label": "1/4", "saved_dump_float32": True,
            "evidence": "docs/phases/WAH_AUTO_WAH_SYNC_RATE_PARAMETERS_PHASE47.md",
            "monitor_integration_physical_validation": "approved",
        },
    },
    *(
        {
            "key": key, "name": name, "display_order": order,
            "value_type": "integer", "range": {"minimum": 0, "maximum": 100, "step": 1},
            "unit": None,
            "protocol": {
                "profile": "effect_parameter_response_1c_v1",
                "value_codec": "upper_float32_nibbles_v1",
                "identification_status": "validated_with_chain_effect_context",
                "message_match": {"parameter_selector": selector, "parameter_marker": 1, "parameter_type": 1},
            },
            "validation": {
                "offline": True, "physical": True, "read_only": True,
                "range_validated": [0, 100], "internal_slots_observed": [1],
                "effect_identity_source": "current_chain", "parameter_selector": selector,
                "saved_dump_default": default,
                "evidence": "docs/phases/WAH_AUTO_WAH_SYNC_RATE_PARAMETERS_PHASE47.md",
                "monitor_integration_physical_validation": "approved",
            },
        }
        for key, name, order, selector, default in (
            ("volume", "VOLUME", 3, 2, 50),
            ("low", "LOW", 4, 3, 25),
            ("q", "Q", 5, 4, 70),
            ("high", "HIGH", 6, 5, 60),
        )
    ),
    {
        "key": "sync", "name": "SYNC", "display_order": 7,
        "value_type": "boolean", "range": {"minimum": 0, "maximum": 1, "step": 1},
        "unit": None,
        "protocol": {
            "profile": "effect_parameter_response_1c_v1",
            "value_codec": "upper_float32_nibbles_v1",
            "identification_status": "validated_with_chain_effect_context",
            "message_match": {"parameter_selector": 6, "parameter_marker": 1, "parameter_type": 1},
        },
        "validation": {
            "offline": True, "physical": True, "read_only": True,
            "internal_slots_observed": [1], "effect_identity_source": "current_chain",
            "parameter_selector": 6, "saved_dump_default": 1,
            "boolean_encoding": {"false": 0, "true": 1},
            "evidence": "docs/phases/WAH_AUTO_WAH_SYNC_RATE_PARAMETERS_PHASE47.md",
            "monitor_integration_physical_validation": "approved",
        },
    },
)


SKREAMER_PARAMETER_SEEDS: tuple[dict[str, Any], ...] = tuple(
    {
        "key": key,
        "name": name,
        "display_order": order,
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
            "internal_slots_observed": [1],
            "effect_identity_source": "current_chain",
            "parameter_selector": selector,
            "saved_dump_default": default,
            "physical_fixture_count": 4,
            "evidence": "docs/phases/DRV_SKREAMER_PARAMETERS_PHASE48.md",
            "monitor_integration_physical_validation": "approved",
        },
    }
    for key, name, order, selector, default in (
        ("gain", "GAIN", 1, 0, 40),
        ("tone", "TONE", 2, 1, 70),
        ("volume", "VOLUME", 3, 2, 50),
    )
)


SKREAMER9_PARAMETER_SEEDS: tuple[dict[str, Any], ...] = tuple(
    {
        "key": key,
        "name": name,
        "display_order": order,
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
            "effect_identity_source": "current_chain",
            "parameter_selector": selector,
            "inference_sources": ["drv.skreamer"],
            "evidence": "docs/phases/DRV_SKREAMER9_INFERRED_PARAMETERS_PHASE49.md",
            "monitor_integration_physical_validation": "approved",
            "physical_validation_without_pcapng": True,
        },
    }
    for key, name, order, selector in (
        ("gain", "GAIN", 1, 0),
        ("tone", "TONE", 2, 1),
        ("volume", "VOLUME", 3, 2),
    )
)


BUTTER_OD_PARAMETER_SEEDS: tuple[dict[str, Any], ...] = tuple(
    {
        "key": key,
        "name": name,
        "display_order": order,
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
            "internal_slots_observed": [1],
            "effect_identity_source": "current_chain",
            "parameter_selector": selector,
            "saved_dump_default": default,
            "physical_combined_capture": True,
            "evidence": "docs/phases/DRV_BUTTER_OD_PARAMETERS_PHASE50.md",
            "monitor_integration_physical_validation": "approved",
        },
    }
    for key, name, order, selector, default in (
        ("gain", "GAIN", 1, 0, 40),
        ("volume", "VOLUME", 2, 1, 70),
    )
)


def _validated_drv_gain_tone_volume_seeds(
    *,
    effect_key: str,
    defaults: tuple[int, int, int],
) -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "key": key,
            "name": name,
            "display_order": order,
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
                "internal_slots_observed": [4, 5, 10, 11],
                "effect_identity_source": "current_chain",
                "parameter_selector": selector,
                "saved_dump_default": default,
                "saved_dump_default_source": "user_reported_official_ui",
                "inference_sources": ["drv.skreamer", "drv.skreamer9"],
                "evidence": "docs/phases/DRV_WARM_SUPER_OD_INFERRED_PARAMETERS_PHASE51.md",
                "monitor_integration_physical_validation": "approved",
                "inference_target": effect_key,
            },
        }
        for (key, name, order, selector), default in zip(
            (
                ("gain", "GAIN", 1, 0),
                ("tone", "TONE", 2, 1),
                ("volume", "VOLUME", 3, 2),
            ),
            defaults,
            strict=True,
        )
    )


WARM_OD_PARAMETER_SEEDS = _validated_drv_gain_tone_volume_seeds(
    effect_key="drv.warm_od",
    defaults=(40, 50, 50),
)


SUPER_OD_PARAMETER_SEEDS = _validated_drv_gain_tone_volume_seeds(
    effect_key="drv.super_od",
    defaults=(50, 50, 50),
)


BLUES_OD_PARAMETER_SEEDS: tuple[dict[str, Any], ...] = tuple(
    {
        "key": key,
        "name": name,
        "display_order": order,
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
            "internal_slots_observed": [4, 10],
            "effect_identity_source": "current_chain",
            "parameter_selector": selector,
            "saved_dump_default": default,
            "saved_dump_default_source": "user_reported_official_ui",
            "inference_sources": [
                "drv.skreamer",
                "drv.skreamer9",
                "drv.warm_od",
                "drv.super_od",
            ],
            "evidence": "docs/phases/DRV_BLUES_FULL_OD_PARAMETERS_PHASE52.md",
            "monitor_integration_physical_validation": "approved",
            "inference_target": "drv.blues_od",
        },
    }
    for key, name, order, selector, default in (
        ("gain", "GAIN", 1, 0, 40),
        ("tone", "TONE", 2, 1, 60),
        ("volume", "VOLUME", 3, 2, 50),
    )
)


FULL_OD_PARAMETER_SEEDS: tuple[dict[str, Any], ...] = (
    *(
        {
            "key": key,
            "name": name,
            "display_order": order,
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
                "internal_slots_observed": [1, 5, 11],
                "effect_identity_source": "current_chain",
                "parameter_selector": selector,
                "saved_dump_value": saved_value,
                "saved_dump_default": default,
                "saved_dump_default_source": "user_reported_official_ui",
                "evidence": "docs/phases/DRV_BLUES_FULL_OD_PARAMETERS_PHASE52.md",
                "monitor_integration_physical_validation": "approved",
            },
        }
        for key, name, order, selector, default, saved_value in (
            ("gain", "GAIN", 1, 0, 40, 21),
            ("tone", "TONE", 2, 1, 60, 43),
            ("volume", "VOLUME", 3, 2, 50, 65),
        )
    ),
    {
        "key": "mode",
        "name": "MODE",
        "display_order": 4,
        "value_type": "enum",
        "range": {"minimum": 0, "maximum": 1, "step": 1},
        "choices": [
            {"value": 0, "label": "LP"},
            {"value": 1, "label": "HP"},
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
            "enum_wire_values_validated": [0, 1],
            "internal_slots_observed": [1, 5, 11],
            "effect_identity_source": "current_chain",
            "parameter_selector": 3,
            "saved_dump_value": 1,
            "saved_dump_default": 1,
            "saved_dump_default_label": "HP",
            "evidence": "docs/phases/DRV_BLUES_FULL_OD_PARAMETERS_PHASE52.md",
            "monitor_integration_physical_validation": "approved",
        },
    },
)


BREAKER_OD_PARAMETER_SEEDS: tuple[dict[str, Any], ...] = tuple(
    {
        "key": key,
        "name": name,
        "display_order": order,
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
            "internal_slots_observed": [4, 10],
            "effect_identity_source": "current_chain",
            "parameter_selector": selector,
            "saved_dump_default": default,
            "saved_dump_default_source": "user_reported_official_ui",
            "inference_sources": ["drv.blues_od", "drv.full_od"],
            "manual_mismatch": "firmware_ui_has_gain_tone_volume",
            "evidence": "docs/phases/DRV_BREAKER_GERDEN_OD_PARAMETERS_PHASE53.md",
            "monitor_integration_physical_validation": "approved",
            "inference_target": "drv.breaker_od",
        },
    }
    for key, name, order, selector, default in (
        ("gain", "GAIN", 1, 0, 60),
        ("tone", "TONE", 2, 1, 50),
        ("volume", "VOLUME", 3, 2, 50),
    )
)


GERDEN_OD_PARAMETER_SEEDS: tuple[dict[str, Any], ...] = tuple(
    {
        "key": key,
        "name": name,
        "display_order": order,
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
            "internal_slots_observed": [1, 5, 11],
            "effect_identity_source": "current_chain",
            "parameter_selector": selector,
            "saved_dump_value": saved_value,
            "saved_dump_default": default,
            "saved_dump_default_source": "user_reported_official_ui",
            "evidence": "docs/phases/DRV_BREAKER_GERDEN_OD_PARAMETERS_PHASE53.md",
            "monitor_integration_physical_validation": "approved",
        },
    }
    for key, name, order, selector, default, saved_value in (
        ("gain", "GAIN", 1, 0, 40, 21),
        ("tone", "TONE", 2, 1, 30, 43),
        ("volume", "VOLUME", 3, 2, 50, 65),
        ("voice", "VOICE", 4, 3, 60, 87),
    )
)


TIMMY_OD_PARAMETER_SEEDS: tuple[dict[str, Any], ...] = (
    *(
        {
            "key": key,
            "name": name,
            "display_order": order,
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
                "internal_slots_observed": [1],
                "effect_identity_source": "current_chain",
                "parameter_selector": selector,
                "saved_dump_value": saved_value,
                "saved_dump_default": default,
                "saved_dump_default_source": "user_reported_official_ui",
                "evidence": "docs/phases/DRV_TIMMY_MASTER_SOLAR_PARAMETERS_PHASE54.md",
                "monitor_integration_physical_validation": "approved",
            },
        }
        for key, name, order, selector, default, saved_value in (
            ("gain", "GAIN", 1, 0, 40, 21),
            ("volume", "VOLUME", 2, 1, 50, 43),
            ("bass", "BASS", 3, 2, 50, 65),
            ("treble", "TREBLE", 4, 3, 50, 87),
        )
    ),
    {
        "key": "mode",
        "name": "MODE",
        "display_order": 5,
        "value_type": "enum",
        "range": {"minimum": 0, "maximum": 2, "step": 1},
        "choices": [
            {"value": 0, "label": "I"},
            {"value": 1, "label": "II"},
            {"value": 2, "label": "III"},
        ],
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
            "enum_wire_values_validated": [0, 1, 2],
            "internal_slots_observed": [1],
            "effect_identity_source": "current_chain",
            "parameter_selector": 4,
            "saved_dump_value": 1,
            "saved_dump_default": 1,
            "saved_dump_default_label": "II",
            "evidence": "docs/phases/DRV_TIMMY_MASTER_SOLAR_PARAMETERS_PHASE54.md",
            "monitor_integration_physical_validation": "approved",
        },
    },
)


MASTER_OD_PARAMETER_SEEDS: tuple[dict[str, Any], ...] = tuple(
    {
        "key": key,
        "name": name,
        "display_order": order,
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
            "saved_dump_value": saved_value,
            "saved_dump_default": default,
            "saved_dump_default_source": "user_reported_official_ui",
            "manual_mismatch": "firmware_ui_has_five_band_controls",
            "evidence": "docs/phases/DRV_TIMMY_MASTER_SOLAR_PARAMETERS_PHASE54.md",
            "monitor_integration_physical_validation": "approved",
        },
    }
    for key, name, order, selector, saved_value in (
        ("gain", "GAIN", 1, 0, 21),
        ("volume", "VOLUME", 2, 1, 43),
        ("bass", "BASS", 3, 2, 65),
        ("middle", "MIDDLE", 4, 3, 87),
        ("treble", "TREBLE", 5, 4, 32),
    )
    for default in (40 if selector == 0 else 50,)
)


SOLAR_FUZZ_PARAMETER_SEEDS: tuple[dict[str, Any], ...] = tuple(
    {
        "key": key,
        "name": name,
        "display_order": order,
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
            "internal_slots_observed": [1, 3],
            "effect_identity_source": "current_chain",
            "parameter_selector": selector,
            "saved_dump_value": saved_value,
            "saved_dump_default": 50,
            "saved_dump_default_source": "user_reported_official_ui",
            "saved_dump_residual_selectors_ignored": [2, 3, 4],
            "evidence": "docs/phases/DRV_TIMMY_MASTER_SOLAR_PARAMETERS_PHASE54.md",
            "monitor_integration_physical_validation": "approved",
        },
    }
    for key, name, order, selector, saved_value in (
        ("fuzz", "FUZZ", 1, 0, 21),
        ("volume", "VOLUME", 2, 1, 65),
    )
)


def _inferred_drive_numeric_seeds(
    *,
    effect_key: str,
    controls: tuple[tuple[str, str, int], ...],
    defaults: tuple[int, ...],
    inference_sources: tuple[str, ...],
    physical: bool = False,
    internal_slots_observed: tuple[int, ...] = (),
    evidence: str = "docs/phases/DRV_FUZZ_RED_JP_INFERRED_PARAMETERS_PHASE55.md",
) -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "key": key,
            "name": name,
            "display_order": order,
            "value_type": "integer",
            "range": {"minimum": 0, "maximum": 100, "step": 1},
            "unit": None,
            "protocol": {
                "profile": "effect_parameter_response_1c_v1",
                "value_codec": "upper_float32_nibbles_v1",
                "identification_status": (
                    "validated_with_chain_effect_context"
                    if physical
                    else "inferred_from_validated_family_layout"
                ),
                "message_match": {
                    "parameter_selector": selector,
                    "parameter_marker": 1,
                    "parameter_type": 1,
                },
            },
            "validation": {
                "offline": True,
                "physical": physical,
                "read_only": True,
                ("range_validated" if physical else "range_inferred"): [0, 100],
                **(
                    {"internal_slots_observed": list(internal_slots_observed)}
                    if physical
                    else {}
                ),
                "effect_identity_source": "current_chain",
                "parameter_selector": selector,
                "saved_dump_default": default,
                "saved_dump_default_source": "user_reported_official_ui",
                "inference_sources": list(inference_sources),
                "evidence": evidence,
                "monitor_integration_physical_validation": (
                    "approved" if physical else "pending"
                ),
                "inference_target": effect_key,
            },
        }
        for (key, name, selector), default, order in zip(
            controls,
            defaults,
            range(1, len(controls) + 1),
            strict=True,
        )
    )


FUZZ_CREAM_PARAMETER_SEEDS = _inferred_drive_numeric_seeds(
    effect_key="drv.fuzz_cream",
    controls=(("sustain", "SUSTAIN", 0), ("tone", "TONE", 1), ("volume", "VOLUME", 2)),
    defaults=(40, 50, 50),
    inference_sources=("drv.skreamer", "drv.blues_od", "drv.breaker_od"),
    physical=True,
    internal_slots_observed=(1,),
)


RED_FUZZ_PARAMETER_SEEDS = _inferred_drive_numeric_seeds(
    effect_key="drv.red_fuzz",
    controls=(("fuzz", "FUZZ", 0), ("volume", "VOLUME", 1)),
    defaults=(50, 50),
    inference_sources=("drv.solar_fuzz",),
    physical=True,
    internal_slots_observed=(2,),
)


JP_DIST_PARAMETER_SEEDS = _inferred_drive_numeric_seeds(
    effect_key="drv.jp_dist",
    controls=(("gain", "GAIN", 0), ("tone", "TONE", 1), ("volume", "VOLUME", 2)),
    defaults=(50, 50, 50),
    inference_sources=("drv.skreamer", "drv.blues_od", "drv.breaker_od"),
    physical=True,
    internal_slots_observed=(3,),
)


DARK_MOUSE_PARAMETER_SEEDS = _inferred_drive_numeric_seeds(
    effect_key="drv.dark_mouse",
    controls=(("gain", "GAIN", 0), ("filter", "FILTER", 1), ("volume", "VOLUME", 2)),
    defaults=(50, 50, 50),
    inference_sources=("drv.jp_dist", "drv.breaker_od"),
    evidence="docs/phases/DRV_DARK_PLEXI_MASTER_DIST_INFERRED_PARAMETERS_PHASE56.md",
    physical=True,
    internal_slots_observed=(1,),
)


PLEXI_DIST_PARAMETER_SEEDS = _inferred_drive_numeric_seeds(
    effect_key="drv.plexi_dist",
    controls=(
        ("gain", "GAIN", 0),
        ("volume", "VOLUME", 1),
        ("bass", "BASS", 2),
        ("middle", "MIDDLE", 3),
        ("treble", "TREBLE", 4),
    ),
    defaults=(50, 50, 50, 50, 50),
    inference_sources=("drv.master_od",),
    evidence="docs/phases/DRV_DARK_PLEXI_MASTER_DIST_INFERRED_PARAMETERS_PHASE56.md",
    physical=True,
    internal_slots_observed=(2,),
)


MASTER_DIST_PARAMETER_SEEDS = _inferred_drive_numeric_seeds(
    effect_key="drv.master_dist",
    controls=(
        ("gain", "GAIN", 0),
        ("volume", "VOLUME", 1),
        ("bass", "BASS", 2),
        ("contour", "CONTOUR", 3),
        ("treble", "TREBLE", 4),
    ),
    defaults=(50, 50, 50, 50, 50),
    inference_sources=("drv.master_od", "drv.plexi_dist"),
    evidence="docs/phases/DRV_DARK_PLEXI_MASTER_DIST_INFERRED_PARAMETERS_PHASE56.md",
    physical=True,
    internal_slots_observed=(3,),
)


DIST_PLUS_PARAMETER_SEEDS = _inferred_drive_numeric_seeds(
    effect_key="drv.dist_plus",
    controls=(("gain", "GAIN", 0), ("volume", "VOLUME", 1)),
    defaults=(50, 50),
    inference_sources=("drv.butter_od",),
    evidence="docs/phases/DRV_DIST_SHARK_STRIVE_INFERRED_PARAMETERS_PHASE57.md",
    physical=True,
    internal_slots_observed=(1,),
)


SHARK_PARAMETER_SEEDS = _inferred_drive_numeric_seeds(
    effect_key="drv.shark",
    controls=(("gain", "GAIN", 0), ("tone", "TONE", 1), ("volume", "VOLUME", 2)),
    defaults=(50, 50, 50),
    inference_sources=("drv.jp_dist", "drv.breaker_od"),
    evidence="docs/phases/DRV_DIST_SHARK_STRIVE_INFERRED_PARAMETERS_PHASE57.md",
    physical=True,
    internal_slots_observed=(2,),
)


STRIVE_PARAMETER_SEEDS: tuple[dict[str, Any], ...] = (
    *_inferred_drive_numeric_seeds(
        effect_key="drv.strive",
        controls=(("gain", "GAIN", 0), ("tone", "TONE", 1), ("volume", "VOLUME", 2)),
        defaults=(50, 50, 50),
        inference_sources=("drv.full_od", "drv.jp_dist"),
        evidence="docs/phases/DRV_DIST_SHARK_STRIVE_INFERRED_PARAMETERS_PHASE57.md",
        physical=True,
        internal_slots_observed=(3,),
    ),
    {
        "key": "mode",
        "name": "MODE",
        "display_order": 4,
        "value_type": "enum",
        "range": {"minimum": 0, "maximum": 2, "step": 1},
        "choices": [
            {"value": 0, "label": "I"},
            {"value": 1, "label": "II"},
            {"value": 2, "label": "III"},
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
            "enum_wire_values_validated": [0, 1, 2],
            "internal_slots_observed": [3],
            "effect_identity_source": "current_chain",
            "parameter_selector": 3,
            "saved_dump_default": 0,
            "saved_dump_default_label": "I",
            "saved_dump_default_source": "user_reported_official_ui",
            "inference_sources": ["drv.timmy_od", "drv.full_od"],
            "evidence": "docs/phases/DRV_DIST_SHARK_STRIVE_INFERRED_PARAMETERS_PHASE57.md",
            "monitor_integration_physical_validation": "approved",
            "inference_target": "drv.strive",
        },
    },
)


SARDAR_DIST_PARAMETER_SEEDS = _inferred_drive_numeric_seeds(
    effect_key="drv.sardar_dist",
    controls=(
        ("gain", "GAIN", 0),
        ("volume", "VOLUME", 1),
        ("bass", "BASS", 2),
        ("treble", "TREBLE", 3),
        ("presence", "PRESENCE", 4),
        ("tight", "TIGHT", 5),
    ),
    defaults=(50, 50, 50, 50, 50, 50),
    inference_sources=("drv.plexi_dist", "drv.master_dist"),
    evidence="docs/phases/DRV_SARDAR_BASS_OD_DIST_INFERRED_PARAMETERS_PHASE58.md",
    physical=True,
    internal_slots_observed=(1, 4),
)


BASS_OD_PARAMETER_SEEDS: tuple[dict[str, Any], ...] = (
    *_inferred_drive_numeric_seeds(
        effect_key="drv.bass_od",
        controls=(("gain", "GAIN", 0), ("tone", "TONE", 1), ("volume", "VOLUME", 2)),
        defaults=(50, 50, 50),
        inference_sources=("drv.strive", "drv.full_od"),
        evidence="docs/phases/DRV_SARDAR_BASS_OD_DIST_INFERRED_PARAMETERS_PHASE58.md",
        physical=True,
        internal_slots_observed=(2, 5),
    ),
    {
        "key": "mode",
        "name": "MODE",
        "display_order": 4,
        "value_type": "enum",
        "range": {"minimum": 0, "maximum": 2, "step": 1},
        "choices": [
            {"value": 0, "label": "NORMAL"},
            {"value": 1, "label": "SCOOP"},
            {"value": 2, "label": "EDGE"},
        ],
        "unit": None,
        "protocol": {
            "profile": "effect_parameter_response_1c_v1",
            "value_codec": "upper_float32_nibbles_v1",
            "identification_status": "validated_with_chain_effect_context",
            "message_match": {"parameter_selector": 3, "parameter_marker": 1, "parameter_type": 1},
        },
        "validation": {
            "offline": True,
            "physical": True,
            "read_only": True,
            "enum_wire_values_validated": [0, 1, 2],
            "internal_slots_observed": [2, 5],
            "effect_identity_source": "current_chain",
            "parameter_selector": 3,
            "saved_dump_default": 0,
            "saved_dump_default_label": "NORMAL",
            "saved_dump_default_source": "user_reported_official_ui",
            "inference_sources": ["drv.strive", "drv.timmy_od"],
            "evidence": "docs/phases/DRV_SARDAR_BASS_OD_DIST_INFERRED_PARAMETERS_PHASE58.md",
            "monitor_integration_physical_validation": "approved",
            "inference_target": "drv.bass_od",
        },
    },
    *(
        {**seed, "display_order": 5}
        for seed in _inferred_drive_numeric_seeds(
            effect_key="drv.bass_od",
            controls=(("blend", "BLEND", 4),),
            defaults=(50,),
            inference_sources=("drv.bass_dist",),
            evidence="docs/phases/DRV_SARDAR_BASS_OD_DIST_INFERRED_PARAMETERS_PHASE58.md",
            physical=True,
            internal_slots_observed=(2, 5),
        )
    ),
)


BASS_DIST_PARAMETER_SEEDS = _inferred_drive_numeric_seeds(
    effect_key="drv.bass_dist",
    controls=(
        ("gain", "GAIN", 0),
        ("blend", "BLEND", 1),
        ("volume", "VOLUME", 2),
        ("bass", "BASS", 3),
        ("treble", "TREBLE", 4),
    ),
    defaults=(50, 50, 50, 50, 50),
    inference_sources=("drv.master_dist", "drv.bass_od"),
    evidence="docs/phases/DRV_SARDAR_BASS_OD_DIST_INFERRED_PARAMETERS_PHASE58.md",
    physical=True,
    internal_slots_observed=(3, 6),
)


def _validated_amp_numeric_seeds(
    *,
    controls: tuple[tuple[str, str, int], ...],
    defaults: tuple[int, ...],
    saved_values: tuple[int, ...],
    evidence: str,
) -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "key": key,
            "name": name,
            "display_order": order,
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
                "internal_slots_observed": [1],
                "effect_identity_source": "current_chain",
                "parameter_selector": selector,
                "saved_dump_value": saved_value,
                "saved_dump_default": default,
                "saved_dump_default_source": "user_reported_and_capture_confirmed",
                "evidence": evidence,
                "monitor_integration_physical_validation": "approved",
            },
        }
        for (key, name, selector), default, saved_value, order in zip(
            controls,
            defaults,
            saved_values,
            range(1, len(controls) + 1),
            strict=True,
        )
    )


TWD_DELUXE_PARAMETER_SEEDS = _validated_amp_numeric_seeds(
    controls=(("gain", "GAIN", 0), ("tone", "TONE", 1), ("volume", "VOLUME", 2)),
    defaults=(30, 50, 50),
    saved_values=(21, 43, 65),
    evidence="docs/phases/AMP_TWD_BMAN_PARAMETERS_PHASE59.md",
)


B_MAN_N_PARAMETER_SEEDS = _validated_amp_numeric_seeds(
    controls=(
        ("gain", "GAIN", 0),
        ("presence", "PRESENCE", 1),
        ("volume", "VOLUME", 2),
        ("bass", "BASS", 3),
        ("middle", "MIDDLE", 4),
        ("treble", "TREBLE", 5),
    ),
    defaults=(30, 50, 50, 50, 50, 50),
    saved_values=(21, 32, 43, 54, 65, 76),
    evidence="docs/phases/AMP_TWD_BMAN_PARAMETERS_PHASE59.md",
)


B_MAN_BRI_PARAMETER_SEEDS = _validated_amp_numeric_seeds(
    controls=(
        ("gain", "GAIN", 0),
        ("presence", "PRESENCE", 1),
        ("volume", "VOLUME", 2),
        ("bass", "BASS", 3),
        ("middle", "MIDDLE", 4),
        ("treble", "TREBLE", 5),
    ),
    defaults=(35, 50, 50, 50, 50, 50),
    saved_values=(23, 34, 45, 56, 67, 78),
    evidence="docs/phases/AMP_TWD_BMAN_PARAMETERS_PHASE59.md",
)


def _validated_phase60_amp_seeds(
    *,
    controls: tuple[tuple[str, str, int, str], ...],
    defaults: tuple[int, ...],
    observed_values: tuple[int, ...],
) -> tuple[dict[str, Any], ...]:
    evidence = "docs/phases/AMP_DARK_SUPERO_CANDIDATES_PHASE60.md"
    seeds: list[dict[str, Any]] = []
    for order, ((key, name, selector, value_type), default, observed_value) in enumerate(
        zip(controls, defaults, observed_values, strict=True),
        start=1,
    ):
        is_boolean = value_type == "boolean"
        validation: dict[str, Any] = {
            "offline": True,
            "physical": True,
            "read_only": True,
            "effect_identity_source": "current_chain",
            "parameter_selector": selector,
            "saved_dump_value": observed_value,
            "saved_dump_default": default,
            "saved_dump_default_source": "user_reported_official_ui",
            "selector_mapping_source": "physically_validated_from_official_ui_order",
            "evidence": evidence,
            "monitor_integration_physical_validation": "approved",
            "physical_validation_without_pcapng": True,
        }
        if is_boolean:
            validation["boolean_encoding"] = {"false": 0, "true": 1}
        else:
            validation["range_validated"] = [0, 100]
        seeds.append(
            {
                "key": key,
                "name": name,
                "display_order": order,
                "value_type": value_type,
                "range": {
                    "minimum": 0,
                    "maximum": 1 if is_boolean else 100,
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
        )
    return tuple(seeds)


DARK_DOUBLE_PARAMETER_SEEDS = _validated_phase60_amp_seeds(
    controls=(
        ("gain", "GAIN", 0, "integer"),
        ("volume", "VOLUME", 1, "integer"),
        ("bass", "BASS", 2, "integer"),
        ("middle", "MIDDLE", 3, "integer"),
        ("treble", "TREBLE", 4, "integer"),
        ("bright", "BRIGHT", 5, "boolean"),
    ),
    defaults=(35, 50, 50, 40, 60, 1),
    observed_values=(19, 20, 19, 17, 9, 1),
)

DARK_DELUXE_PARAMETER_SEEDS = _validated_phase60_amp_seeds(
    controls=(
        ("gain", "GAIN", 0, "integer"),
        ("volume", "VOLUME", 1, "integer"),
        ("bass", "BASS", 2, "integer"),
        ("treble", "TREBLE", 3, "integer"),
    ),
    defaults=(30, 50, 50, 50),
    observed_values=(65, 69, 74, 71),
)

SUPERO_2_CL_PARAMETER_SEEDS = _validated_phase60_amp_seeds(
    controls=(
        ("gain", "GAIN", 0, "integer"),
        ("tone", "TONE", 1, "integer"),
        ("volume", "VOLUME", 2, "integer"),
    ),
    defaults=(30, 50, 50),
    observed_values=(87, 75, 94),
)


def _validated_phase61_amp_seeds(
    *,
    controls: tuple[tuple[str, str, int, str], ...],
    defaults: tuple[int, ...],
    observed_values: tuple[int, ...],
) -> tuple[dict[str, Any], ...]:
    evidence = "docs/phases/AMP_SUPERO_VOKS_CANDIDATES_PHASE61.md"
    seeds: list[dict[str, Any]] = []
    for order, ((key, name, selector, value_type), default, observed_value) in enumerate(
        zip(controls, defaults, observed_values, strict=True),
        start=1,
    ):
        is_boolean = value_type == "boolean"
        validation: dict[str, Any] = {
            "offline": True,
            "physical": True,
            "read_only": True,
            "effect_identity_source": "current_chain",
            "parameter_selector": selector,
            "saved_dump_value": observed_value,
            "saved_dump_default": default,
            "saved_dump_default_source": "user_reported_official_ui",
            "selector_mapping_source": "physically_validated_from_official_ui_order",
            "evidence": evidence,
            "monitor_integration_physical_validation": "approved",
            "physical_validation_without_pcapng": True,
        }
        if is_boolean:
            validation["boolean_encoding"] = {"false": 0, "true": 1}
        else:
            validation["range_validated"] = [0, 100]
        seeds.append(
            {
                "key": key,
                "name": name,
                "display_order": order,
                "value_type": value_type,
                "range": {
                    "minimum": 0,
                    "maximum": 1 if is_boolean else 100,
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
        )
    return tuple(seeds)


SUPERO_2_OD_PARAMETER_SEEDS = _validated_phase61_amp_seeds(
    controls=(
        ("gain_1", "GAIN 1", 0, "integer"),
        ("tone_1", "TONE 1", 1, "integer"),
        ("gain_2", "GAIN 2", 2, "integer"),
        ("tone_2", "TONE 2", 3, "integer"),
        ("volume", "VOLUME", 4, "integer"),
    ),
    defaults=(50, 50, 50, 50, 50),
    observed_values=(21, 34, 9, 8, 23),
)

VOKS_15TB_PARAMETER_SEEDS = _validated_phase61_amp_seeds(
    controls=(
        ("gain", "GAIN", 0, "integer"),
        ("tone_cut", "TONE CUT", 1, "integer"),
        ("volume", "VOLUME", 2, "integer"),
        ("bass", "BASS", 3, "integer"),
        ("treble", "TREBLE", 4, "integer"),
    ),
    defaults=(30, 60, 50, 50, 50),
    observed_values=(48, 58, 66, 69, 66),
)

VOKS_30N_PARAMETER_SEEDS = _validated_phase61_amp_seeds(
    controls=(
        ("gain", "GAIN", 0, "integer"),
        ("tone_cut", "TONE CUT", 1, "integer"),
        ("volume", "VOLUME", 2, "integer"),
        ("bright", "BRIGHT", 3, "boolean"),
    ),
    defaults=(30, 50, 50, 0),
    observed_values=(91, 90, 97, 1),
)


def _validated_phase62_amp_seeds(
    *,
    controls: tuple[tuple[str, str, int, str], ...],
    defaults: tuple[int, ...],
    observed_values: tuple[int, ...],
    enum_choices: dict[str, tuple[tuple[int, str], ...]] | None = None,
) -> tuple[dict[str, Any], ...]:
    evidence = "docs/phases/AMP_VOKS_JAZZ_SUPERB_CANDIDATES_PHASE62.md"
    enum_choices = enum_choices or {}
    seeds: list[dict[str, Any]] = []
    for order, ((key, name, selector, value_type), default, observed_value) in enumerate(
        zip(controls, defaults, observed_values, strict=True),
        start=1,
    ):
        is_boolean = value_type == "boolean"
        is_enum = value_type == "enum"
        choices = enum_choices.get(key, ())
        validation: dict[str, Any] = {
            "offline": True,
            "physical": True,
            "read_only": True,
            "effect_identity_source": "current_chain",
            "parameter_selector": selector,
            "saved_dump_value": observed_value,
            "saved_dump_default": default,
            "saved_dump_default_source": "user_reported_official_ui",
            "selector_mapping_source": "physically_validated_from_official_ui_order",
            "evidence": evidence,
            "monitor_integration_physical_validation": "approved",
            "physical_validation_without_pcapng": True,
        }
        if is_boolean:
            validation["boolean_encoding"] = {"false": 0, "true": 1}
        elif is_enum:
            validation["enum_wire_values_validated"] = [value for value, _ in choices]
        else:
            validation["range_validated"] = [0, 100]
        parameter: dict[str, Any] = {
            "key": key,
            "name": name,
            "display_order": order,
            "value_type": value_type,
            "range": {
                "minimum": 0,
                "maximum": 1 if (is_boolean or is_enum) else 100,
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
        if is_enum:
            parameter["choices"] = [
                {"value": value, "label": label} for value, label in choices
            ]
        seeds.append(parameter)
    return tuple(seeds)


VOKS_30TB_PARAMETER_SEEDS = _validated_phase62_amp_seeds(
    controls=(
        ("gain", "GAIN", 0, "integer"),
        ("tone_cut", "TONE CUT", 1, "integer"),
        ("volume", "VOLUME", 2, "integer"),
        ("bass", "BASS", 3, "integer"),
        ("treble", "TREBLE", 4, "integer"),
        ("char", "CHAR", 5, "enum"),
    ),
    defaults=(30, 50, 50, 50, 50, 0),
    observed_values=(2, 4, 3, 4, 4, 1),
    enum_choices={"char": ((0, "COOL"), (1, "HOT"))},
)

JAZZ_120_PARAMETER_SEEDS = _validated_phase62_amp_seeds(
    controls=(
        ("gain", "GAIN", 0, "integer"),
        ("bass", "BASS", 1, "integer"),
        ("middle", "MIDDLE", 2, "integer"),
        ("treble", "TREBLE", 3, "integer"),
        ("bright", "BRIGHT", 4, "boolean"),
    ),
    defaults=(50, 50, 50, 50, 0),
    observed_values=(39, 55, 43, 55, 1),
)

SUPERB_CL_PARAMETER_SEEDS = _validated_phase62_amp_seeds(
    controls=(
        ("gain", "GAIN", 0, "integer"),
        ("presence", "PRESENCE", 1, "integer"),
        ("volume", "VOLUME", 2, "integer"),
        ("bass", "BASS", 3, "integer"),
        ("middle", "MIDDLE", 4, "integer"),
        ("treble", "TREBLE", 5, "integer"),
    ),
    defaults=(35, 50, 50, 50, 50, 50),
    observed_values=(66, 74, 82, 88, 94, 100),
)


def _validated_phase63_amp_seeds(
    *,
    controls: tuple[tuple[str, str, int], ...],
    defaults: tuple[int, ...],
    observed_values: tuple[int, ...],
) -> tuple[dict[str, Any], ...]:
    evidence = "docs/phases/AMP_SUPERB_CALIF_CANDIDATES_PHASE63.md"
    seeds: list[dict[str, Any]] = []
    for order, ((key, name, selector), default, observed_value) in enumerate(
        zip(controls, defaults, observed_values, strict=True),
        start=1,
    ):
        seeds.append(
            {
                "key": key,
                "name": name,
                "display_order": order,
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
                    "effect_identity_source": "current_chain",
                    "parameter_selector": selector,
                    "saved_dump_value": observed_value,
                    "saved_dump_default": default,
                    "saved_dump_default_source": "user_reported_official_ui",
                    "selector_mapping_source": "physically_validated_from_official_ui_order",
                    "evidence": evidence,
                    "monitor_integration_physical_validation": "approved",
                    "physical_validation_without_pcapng": True,
                    "range_validated": [0, 100],
                },
            }
        )
    return tuple(seeds)


SUPERB_OD_PARAMETER_SEEDS = _validated_phase63_amp_seeds(
    controls=(
        ("gain", "GAIN", 0),
        ("presence", "PRESENCE", 1),
        ("volume", "VOLUME", 2),
        ("bass", "BASS", 3),
        ("middle", "MIDDLE", 4),
        ("treble", "TREBLE", 5),
    ),
    defaults=(50, 50, 50, 50, 50, 50),
    observed_values=(3, 5, 7, 1, 4, 6),
)

CALIF_STAR_CL_PARAMETER_SEEDS = _validated_phase63_amp_seeds(
    controls=(
        ("gain", "GAIN", 0),
        ("presence", "PRESENCE", 1),
        ("volume", "VOLUME", 2),
        ("bass", "BASS", 3),
        ("middle", "MIDDLE", 4),
        ("treble", "TREBLE", 5),
    ),
    defaults=(40, 50, 50, 50, 50, 50),
    observed_values=(33, 41, 54, 62, 45, 62),
)

CALIF_STAR_OD_PARAMETER_SEEDS = _validated_phase63_amp_seeds(
    controls=(
        ("input", "INPUT", 0),
        ("gain", "GAIN", 1),
        ("presence", "PRESENCE", 2),
        ("volume", "VOLUME", 3),
        ("bass", "BASS", 4),
        ("middle", "MIDDLE", 5),
        ("treble", "TREBLE", 6),
    ),
    defaults=(50, 50, 50, 50, 50, 50, 50),
    observed_values=(94, 93, 79, 90, 97, 88, 100),
)


def _validated_phase64_amp_seeds(
    *,
    controls: tuple[tuple[str, str, int, str], ...],
    defaults: tuple[int, ...],
    observed_values: tuple[int, ...],
) -> tuple[dict[str, Any], ...]:
    evidence = "docs/phases/AMP_BOG_CANDIDATES_PHASE64.md"
    seeds: list[dict[str, Any]] = []
    for order, ((key, name, selector, value_type), default, observed_value) in enumerate(
        zip(controls, defaults, observed_values, strict=True),
        start=1,
    ):
        is_boolean = value_type == "boolean"
        validation: dict[str, Any] = {
            "offline": True,
            "physical": True,
            "read_only": True,
            "effect_identity_source": "current_chain",
            "parameter_selector": selector,
            "saved_dump_value": observed_value,
            "saved_dump_default": default,
            "saved_dump_default_source": "user_reported_official_ui",
            "selector_mapping_source": "physically_validated_from_official_ui_order",
            "evidence": evidence,
            "monitor_integration_physical_validation": "approved",
            "physical_validation_without_pcapng": True,
        }
        if is_boolean:
            validation["boolean_encoding"] = {"false": 0, "true": 1}
        else:
            validation["range_validated"] = [0, 100]
        seeds.append({
            "key": key, "name": name, "display_order": order,
            "value_type": value_type,
            "range": {"minimum": 0, "maximum": 1 if is_boolean else 100, "step": 1},
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
        })
    return tuple(seeds)


BOG_SV_CL_PARAMETER_SEEDS = _validated_phase64_amp_seeds(
    controls=(("gain", "GAIN", 0, "integer"), ("presence", "PRESENCE", 1, "integer"), ("volume", "VOLUME", 2, "integer"), ("bass", "BASS", 3, "integer"), ("treble", "TREBLE", 4, "integer"), ("bright", "BRIGHT", 5, "boolean")),
    defaults=(30, 50, 50, 50, 50, 0),
    observed_values=(8, 12, 18, 13, 20, 1),
)

BOG_SV_OD_PARAMETER_SEEDS = _validated_phase64_amp_seeds(
    controls=(("gain", "GAIN", 0, "integer"), ("presence", "PRESENCE", 1, "integer"), ("volume", "VOLUME", 2, "integer"), ("bass", "BASS", 3, "integer"), ("middle", "MIDDLE", 4, "integer"), ("treble", "TREBLE", 5, "integer")),
    defaults=(30, 50, 50, 50, 50, 50),
    observed_values=(23, 37, 60, 57, 43, 57),
)

BOG_XT_BLUE_PARAMETER_SEEDS = _validated_phase64_amp_seeds(
    controls=(("gain", "GAIN", 0, "integer"), ("presence", "PRESENCE", 1, "integer"), ("volume", "VOLUME", 2, "integer"), ("bass", "BASS", 3, "integer"), ("middle", "MIDDLE", 4, "integer"), ("treble", "TREBLE", 5, "integer")),
    defaults=(30, 50, 50, 50, 50, 50),
    observed_values=(62, 73, 82, 88, 94, 100),
)


def _validated_phase65_amp_seeds(
    *,
    controls: tuple[tuple[str, str, int], ...],
    defaults: tuple[int, ...],
    observed_values: tuple[int, ...],
) -> tuple[dict[str, Any], ...]:
    seeds: list[dict[str, Any]] = []
    for order, ((key, name, selector), default, observed) in enumerate(
        zip(controls, defaults, observed_values, strict=True), start=1
    ):
        seeds.append({
            "key": key, "name": name, "display_order": order,
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
                "effect_identity_source": "current_chain",
                "parameter_selector": selector,
                "saved_dump_value": observed,
                "saved_dump_default": default,
                "saved_dump_default_source": "user_reported_official_ui",
                "selector_mapping_source": "physically_validated_from_official_ui_order",
                "evidence": "user_physical_validation_phase65_monitor_live",
                "monitor_integration_physical_validation": "approved",
                "physical_validation_without_pcapng": True,
                "range_validated": [0, 100],
            },
        })
    return tuple(seeds)


BOG_XT_RED_PARAMETER_SEEDS = _validated_phase65_amp_seeds(
    controls=(("gain", "GAIN", 0), ("presence", "PRESENCE", 1), ("volume", "VOLUME", 2), ("bass", "BASS", 3), ("middle", "MIDDLE", 4), ("treble", "TREBLE", 5)),
    defaults=(50, 50, 50, 50, 50, 50),
    observed_values=(3, 9, 14, 20, 25, 32),
)
DOCTOR_CL_PARAMETER_SEEDS = _validated_phase65_amp_seeds(
    controls=(("gain", "GAIN", 0), ("tone_cut", "TONE CUT", 1), ("volume", "VOLUME", 2), ("bass", "BASS", 3), ("middle", "MIDDLE", 4), ("treble", "TREBLE", 5)),
    defaults=(35, 50, 50, 50, 50, 50),
    observed_values=(27, 41, 31, 43, 32, 42),
)
DOCTOR_OD_PARAMETER_SEEDS = _validated_phase65_amp_seeds(
    controls=(("gain", "GAIN", 0), ("tone_cut", "TONE CUT", 1), ("volume", "VOLUME", 2), ("bass", "BASS", 3), ("middle", "MIDDLE", 4), ("treble", "TREBLE", 5)),
    defaults=(35, 50, 50, 50, 50, 50),
    observed_values=(37, 58, 64, 71, 68, 81),
)
DRAGON_CL_PARAMETER_SEEDS = _validated_phase65_amp_seeds(
    controls=(("gain", "GAIN", 0), ("volume", "VOLUME", 1), ("bass", "BASS", 2), ("middle", "MIDDLE", 3), ("treble", "TREBLE", 4)),
    defaults=(35, 50, 50, 50, 50),
    observed_values=(7, 11, 14, 10, 15),
)
DRAGON_CL_B_PARAMETER_SEEDS = _validated_phase65_amp_seeds(
    controls=(("gain", "GAIN", 0), ("volume", "VOLUME", 1), ("bass", "BASS", 2), ("middle", "MIDDLE", 3), ("treble", "TREBLE", 4)),
    defaults=(20, 50, 50, 50, 50),
    observed_values=(41, 58, 62, 44, 68),
)
DRAGON_OD_PARAMETER_SEEDS = _validated_phase65_amp_seeds(
    controls=(("gain", "GAIN", 0), ("volume", "VOLUME", 1), ("bass", "BASS", 2), ("middle", "MIDDLE", 3), ("treble", "TREBLE", 4)),
    defaults=(30, 50, 50, 50, 50),
    observed_values=(65, 76, 85, 89, 99),
)
SOL_100_CL_PARAMETER_SEEDS = _validated_phase65_amp_seeds(
    controls=(("gain", "GAIN", 0), ("presence", "PRESENCE", 1), ("volume", "VOLUME", 2), ("bass", "BASS", 3), ("middle", "MIDDLE", 4), ("treble", "TREBLE", 5)),
    defaults=(30, 50, 50, 50, 50, 50),
    observed_values=(41, 60, 40, 59, 41, 67),
)
SOL_100_OD_PARAMETER_SEEDS = _validated_phase65_amp_seeds(
    controls=(("gain", "GAIN", 0), ("presence", "PRESENCE", 1), ("volume", "VOLUME", 2), ("bass", "BASS", 3), ("middle", "MIDDLE", 4), ("treble", "TREBLE", 5)),
    defaults=(50, 50, 50, 50, 50, 50),
    observed_values=(80, 69, 89, 77, 90, 99),
)


def _validated_phase66_amp_seeds(
    *,
    controls: tuple[tuple[str, str, int], ...],
    defaults: tuple[int, ...],
    observed_values: tuple[int, ...],
) -> tuple[dict[str, Any], ...]:
    seeds: list[dict[str, Any]] = []
    for order, ((key, name, selector), default, observed) in enumerate(
        zip(controls, defaults, observed_values, strict=True), start=1
    ):
        seeds.append({
            "key": key, "name": name, "display_order": order,
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
                "effect_identity_source": "current_chain",
                "parameter_selector": selector,
                "saved_dump_default": default,
                "saved_dump_default_source": "user_reported_official_ui",
                "selector_mapping_source": "physically_validated_from_official_ui_order",
                "evidence": "user_physical_validation_phase66_monitor_live",
                "monitor_integration_physical_validation": "approved",
                "saved_dump_value": observed,
                "physical_validation_without_pcapng": True,
                "range_validated": [0, 100],
            },
        })
    return tuple(seeds)


SOL_100_LD_PARAMETER_SEEDS = _validated_phase66_amp_seeds(
    controls=(("gain", "GAIN", 0), ("presence", "PRESENCE", 1), ("volume", "VOLUME", 2), ("bass", "BASS", 3), ("middle", "MIDDLE", 4), ("treble", "TREBLE", 5)),
    defaults=(50, 50, 50, 50, 50, 50),
    observed_values=(3, 0, 7, 0, 8, 0),
)
BRIT_45_PARAMETER_SEEDS = _validated_phase66_amp_seeds(
    controls=(("gain", "GAIN", 0), ("presence", "PRESENCE", 1), ("volume", "VOLUME", 2), ("bass", "BASS", 3), ("middle", "MIDDLE", 4), ("treble", "TREBLE", 5)),
    defaults=(25, 65, 50, 45, 50, 65),
    observed_values=(4, 9, 13, 19, 29, 49),
)
BRIT_45_PLUS_PARAMETER_SEEDS = _validated_phase66_amp_seeds(
    controls=(("gain", "GAIN", 0), ("presence", "PRESENCE", 1), ("volume", "VOLUME", 2), ("bass", "BASS", 3), ("middle", "MIDDLE", 4), ("treble", "TREBLE", 5)),
    defaults=(45, 50, 50, 50, 50, 50),
    observed_values=(10, 24, 39, 49, 28, 46),
)
BRIT_45JP_PARAMETER_SEEDS = _validated_phase66_amp_seeds(
    controls=(("gain_1", "GAIN 1", 0), ("presence", "PRESENCE", 1), ("volume", "VOLUME", 2), ("bass", "BASS", 3), ("middle", "MIDDLE", 4), ("treble", "TREBLE", 5), ("gain_2", "GAIN 2", 6)),
    defaults=(50, 50, 50, 50, 50, 50, 50),
    observed_values=(15, 23, 21, 13, 24, 31, 37),
)
BRIT_50_PARAMETER_SEEDS = _validated_phase66_amp_seeds(
    controls=(("gain", "GAIN", 0), ("presence", "PRESENCE", 1), ("volume", "VOLUME", 2), ("bass", "BASS", 3), ("middle", "MIDDLE", 4), ("treble", "TREBLE", 5)),
    defaults=(40, 50, 50, 50, 50, 50),
    observed_values=(85, 78, 85, 87, 94, 100),
)
BRIT_50_PLUS_PARAMETER_SEEDS = _validated_phase66_amp_seeds(
    controls=(("gain", "GAIN", 0), ("presence", "PRESENCE", 1), ("volume", "VOLUME", 2), ("bass", "BASS", 3), ("middle", "MIDDLE", 4), ("treble", "TREBLE", 5)),
    defaults=(40, 50, 50, 50, 50, 50),
    observed_values=(8, 0, 12, 100, 48, 66),
)
BRIT_50JP_PARAMETER_SEEDS = _validated_phase66_amp_seeds(
    controls=(("gain_1", "GAIN 1", 0), ("presence", "PRESENCE", 1), ("volume", "VOLUME", 2), ("bass", "BASS", 3), ("middle", "MIDDLE", 4), ("treble", "TREBLE", 5), ("gain_2", "GAIN 2", 6)),
    defaults=(40, 50, 50, 50, 50, 50, 50),
    observed_values=(3, 82, 29, 71, 34, 61, 37),
)
BRIT_SLP_PARAMETER_SEEDS = _validated_phase66_amp_seeds(
    controls=(("gain", "GAIN", 0), ("presence", "PRESENCE", 1), ("volume", "VOLUME", 2), ("bass", "BASS", 3), ("middle", "MIDDLE", 4), ("treble", "TREBLE", 5)),
    defaults=(50, 50, 50, 50, 50, 50),
    observed_values=(75, 28, 73, 37, 35, 93),
)
BRIT_800_PARAMETER_SEEDS = _validated_phase66_amp_seeds(
    controls=(("gain", "GAIN", 0), ("presence", "PRESENCE", 1), ("volume", "VOLUME", 2), ("bass", "BASS", 3), ("middle", "MIDDLE", 4), ("treble", "TREBLE", 5)),
    defaults=(50, 50, 50, 50, 50, 50),
    observed_values=(100, 63, 39, 86, 48, 73),
)



def _validated_phase67_amp_seeds(
    *,
    defaults: tuple[int, int, int, int, int, int],
    observed_values: tuple[int, int, int, int, int, int],
) -> tuple[dict[str, Any], ...]:
    controls = (
        ("gain", "GAIN", 0),
        ("presence", "PRESENCE", 1),
        ("volume", "VOLUME", 2),
        ("bass", "BASS", 3),
        ("middle", "MIDDLE", 4),
        ("treble", "TREBLE", 5),
    )
    seeds: list[dict[str, Any]] = []
    for order, ((key, name, selector), default, observed) in enumerate(
        zip(controls, defaults, observed_values, strict=True), start=1
    ):
        seeds.append({
            "key": key, "name": name, "display_order": order,
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
                "effect_identity_source": "current_chain",
                "parameter_selector": selector,
                "saved_dump_default": default,
                "saved_dump_default_source": "user_reported_official_ui",
                "selector_mapping_source": "physically_validated_from_official_ui_order",
                "evidence": "user_physical_validation_phase67_monitor_live",
                "monitor_integration_physical_validation": "approved",
                "saved_dump_value": observed,
                "physical_validation_without_pcapng": True,
                "range_validated": [0, 100],
            },
        })
    return tuple(seeds)


BRIT_900_PARAMETER_SEEDS = _validated_phase67_amp_seeds(defaults=(50, 50, 50, 50, 50, 50), observed_values=(0, 8, 100, 6, 17, 40))
FLYMAN_1_PARAMETER_SEEDS = _validated_phase67_amp_seeds(defaults=(50, 50, 50, 50, 50, 50), observed_values=(8, 19, 100, 29, 54, 21))
FLYMAN_2_PARAMETER_SEEDS = _validated_phase67_amp_seeds(defaults=(50, 50, 50, 50, 50, 50), observed_values=(70, 36, 73, 0, 55, 100))
FLYMAN_PLUS_1_PARAMETER_SEEDS = _validated_phase67_amp_seeds(defaults=(50, 50, 50, 50, 50, 50), observed_values=(0, 82, 15, 100, 38, 65))
FLYMAN_PLUS_2_PARAMETER_SEEDS = _validated_phase67_amp_seeds(defaults=(50, 50, 50, 50, 50, 50), observed_values=(100, 0, 71, 33, 100, 67))
CALIF_IIC_PLUS_1_PARAMETER_SEEDS = _validated_phase67_amp_seeds(defaults=(50, 50, 50, 50, 50, 50), observed_values=(0, 100, 31, 66, 42, 86))
CALIF_IIC_PLUS_2_PARAMETER_SEEDS = _validated_phase67_amp_seeds(defaults=(50, 50, 50, 50, 50, 50), observed_values=(100, 42, 0, 38, 87, 61))
CALIF_IIC_PLUS_3_PARAMETER_SEEDS = _validated_phase67_amp_seeds(defaults=(50, 50, 50, 50, 50, 50), observed_values=(8, 89, 40, 67, 46, 100))
CALIF_IV_LD_1_PARAMETER_SEEDS = _validated_phase67_amp_seeds(defaults=(50, 50, 50, 50, 50, 50), observed_values=(0, 85, 33, 76, 42, 100))


def _phase68_amp_seeds(
    *,
    controls: tuple[tuple[str, str, int], ...],
    defaults: tuple[int, ...],
    observed_values: tuple[int, ...] | None = None,
) -> tuple[dict[str, Any], ...]:
    if observed_values is not None and len(observed_values) != len(controls):
        raise ValueError("observed_values deve corresponder aos controles da fase 68")

    validated = observed_values is not None
    seeds: list[dict[str, Any]] = []
    for index, (order, ((key, name, selector), default)) in enumerate(
        enumerate(zip(controls, defaults, strict=True), start=1)
    ):
        validation: dict[str, Any] = {
            "offline": True,
            "physical": validated,
            "read_only": True,
            "effect_identity_source": "current_chain",
            "parameter_selector": selector,
            "saved_dump_default": default,
            "saved_dump_default_source": "user_reported_official_ui",
            "selector_mapping_source": (
                "physically_validated_from_monitor_live"
                if validated
                else "candidate_from_user_reported_official_ui_order"
            ),
            "evidence": (
                "user_physical_validation_phase68_monitor_live"
                if validated
                else "user_reported_official_ui_phase68"
            ),
            "monitor_integration_physical_validation": (
                "approved" if validated else "pending"
            ),
            "range_inferred": [0, 100],
        }
        identification_status = "candidate_from_user_reported_official_ui_order"
        if validated:
            validation.update({
                "saved_dump_value": observed_values[index],
                "physical_validation_without_pcapng": True,
                "range_validated": [0, 100],
            })
            identification_status = "validated_with_chain_effect_context"

        seeds.append({
            "key": key,
            "name": name,
            "display_order": order,
            "value_type": "integer",
            "range": {"minimum": 0, "maximum": 100, "step": 1},
            "unit": None,
            "protocol": {
                "profile": "effect_parameter_response_1c_v1",
                "value_codec": "upper_float32_nibbles_v1",
                "identification_status": identification_status,
                "message_match": {
                    "parameter_selector": selector,
                    "parameter_marker": 1,
                    "parameter_type": 1,
                },
            },
            "validation": validation,
        })
    return tuple(seeds)


_PHASE68_STANDARD_CONTROLS = (
    ("gain", "GAIN", 0),
    ("presence", "PRESENCE", 1),
    ("volume", "VOLUME", 2),
    ("bass", "BASS", 3),
    ("middle", "MIDDLE", 4),
    ("treble", "TREBLE", 5),
)
CALIF_IV_LD_2_PARAMETER_SEEDS = _phase68_amp_seeds(
    controls=_PHASE68_STANDARD_CONTROLS,
    defaults=(50, 50, 50, 50, 50, 50),
    observed_values=(3, 9, 33, 100, 0, 77),
)
CALIF_IV_LD_3_PARAMETER_SEEDS = _phase68_amp_seeds(
    controls=_PHASE68_STANDARD_CONTROLS,
    defaults=(50, 50, 50, 50, 50, 50),
    observed_values=(0, 100, 30, 70, 42, 74),
)
CALIF_DUAL_V_PARAMETER_SEEDS = _phase68_amp_seeds(
    controls=_PHASE68_STANDARD_CONTROLS,
    defaults=(50, 50, 50, 50, 50, 50),
    observed_values=(8, 34, 0, 100, 83, 21),
)
CALIF_DUAL_M_PARAMETER_SEEDS = _phase68_amp_seeds(
    controls=_PHASE68_STANDARD_CONTROLS,
    defaults=(50, 50, 50, 50, 50, 50),
    observed_values=(73, 0, 33, 67, 100, 42),
)
TANGER_R100_PARAMETER_SEEDS = _phase68_amp_seeds(
    controls=(("gain", "GAIN", 0), ("volume", "VOLUME", 1), ("bass", "BASS", 2), ("middle", "MIDDLE", 3), ("treble", "TREBLE", 4)),
    defaults=(50, 50, 50, 50, 50),
    observed_values=(0, 100, 0, 100, 17),
)
HALEN_51_PARAMETER_SEEDS = _phase68_amp_seeds(
    controls=(("gain", "GAIN", 0), ("volume", "VOLUME", 1), ("bass", "BASS", 2), ("middle", "MIDDLE", 3), ("treble", "TREBLE", 4), ("presence", "PRESENCE", 6)),
    defaults=(50, 50, 50, 50, 50, 50),
    observed_values=(46, 53, 61, 71, 79, 48),
)
ENG_120_PARAMETER_SEEDS = _phase68_amp_seeds(
    controls=_PHASE68_STANDARD_CONTROLS,
    defaults=(50, 50, 50, 50, 50, 50),
    observed_values=(15, 2, 4, 9, 100, 0),
)
ENG_120_PLUS_PARAMETER_SEEDS = _phase68_amp_seeds(
    controls=_PHASE68_STANDARD_CONTROLS,
    defaults=(50, 50, 50, 50, 50, 50),
    observed_values=(20, 94, 44, 74, 99, 8),
)
DIZZY_VH_PARAMETER_SEEDS = _phase68_amp_seeds(
    controls=_PHASE68_STANDARD_CONTROLS,
    defaults=(50, 50, 50, 50, 50, 50),
    observed_values=(17, 95, 35, 93, 56, 89),
)


def _phase69_amp_seeds(
    *,
    controls: tuple[tuple[str, str, int, str], ...],
    defaults: tuple[int, ...],
    observed_values: tuple[int, ...],
    enum_choices: dict[str, tuple[tuple[int, str], ...]] | None = None,
) -> tuple[dict[str, Any], ...]:
    enum_choices = enum_choices or {}
    if len(observed_values) != len(controls):
        raise ValueError("observed_values deve corresponder aos controles da fase 69")

    seeds: list[dict[str, Any]] = []
    for index, (order, ((key, name, selector, value_type), default)) in enumerate(
        enumerate(zip(controls, defaults, strict=True), start=1)
    ):
        is_boolean = value_type == "boolean"
        is_enum = value_type == "enum"
        choices = enum_choices.get(key, ())
        maximum = len(choices) - 1 if is_enum else (1 if is_boolean else 100)
        validation: dict[str, Any] = {
            "offline": True,
            "physical": True,
            "read_only": True,
            "effect_identity_source": "current_chain",
            "parameter_selector": selector,
            "saved_dump_default": default,
            "saved_dump_default_source": "user_reported_official_ui",
            "selector_mapping_source": "physically_validated_from_monitor_live",
            "evidence": "docs/phases/AMP_CLASS_CONSOLIDATION_PHASE69.md",
            "monitor_integration_physical_validation": "approved",
            "saved_dump_value": observed_values[index],
            "physical_validation_without_pcapng": True,
        }
        if is_boolean:
            validation["boolean_encoding"] = {"false": 0, "true": 1}
        elif is_enum:
            validation["enum_wire_values_validated"] = [value for value, _ in choices]
        else:
            validation["range_inferred"] = [0, 100]
            validation["range_validated"] = [0, 100]

        parameter: dict[str, Any] = {
            "key": key,
            "name": name,
            "display_order": order,
            "value_type": value_type,
            "range": {"minimum": 0, "maximum": maximum, "step": 1},
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
        if is_enum:
            parameter["choices"] = [
                {"value": value, "label": label} for value, label in choices
            ]
        seeds.append(parameter)
    return tuple(seeds)


_PHASE69_STANDARD_CONTROLS = (
    ("gain", "GAIN", 0, "integer"),
    ("presence", "PRESENCE", 1, "integer"),
    ("volume", "VOLUME", 2, "integer"),
    ("bass", "BASS", 3, "integer"),
    ("middle", "MIDDLE", 4, "integer"),
    ("treble", "TREBLE", 5, "integer"),
)
DIZZY_VH_S_PARAMETER_SEEDS = _phase69_amp_seeds(
    controls=_PHASE69_STANDARD_CONTROLS,
    defaults=(50, 50, 50, 50, 50, 50),
    observed_values=(0, 100, 23, 77, 40, 65),
)
DIZZY_VH_PLUS_PARAMETER_SEEDS = _phase69_amp_seeds(
    controls=_PHASE69_STANDARD_CONTROLS,
    defaults=(50, 50, 50, 50, 50, 50),
    observed_values=(100, 0, 12, 88, 27, 66),
)
DIZZY_VH_PLUS_S_PARAMETER_SEEDS = _phase69_amp_seeds(
    controls=_PHASE69_STANDARD_CONTROLS,
    defaults=(50, 50, 50, 50, 50, 50),
    observed_values=(74, 34, 100, 0, 37, 57),
)
A_BASSVT_PARAMETER_SEEDS = _phase69_amp_seeds(
    controls=(
        ("gain", "GAIN", 0, "integer"),
        ("bass", "BASS", 1, "integer"),
        ("middle", "MIDDLE", 2, "integer"),
        ("midrange", "MIDRANGE", 3, "enum"),
        ("treble", "TREBLE", 4, "integer"),
        ("volume", "VOLUME", 5, "integer"),
    ),
    defaults=(50, 50, 50, 1, 50, 50),
    observed_values=(11, 92, 40, 3, 99, 1),
    enum_choices={
        "midrange": ((0, "220HZ"), (1, "450HZ"), (2, "800HZ"), (3, "1.6KHZ"), (4, "3KHZ")),
    },
)
VOKS_BASS_PARAMETER_SEEDS = _phase69_amp_seeds(
    controls=(("volume", "VOLUME", 0, "integer"), ("bass", "BASS", 1, "integer"), ("treble", "TREBLE", 2, "integer")),
    defaults=(50, 50, 50),
    observed_values=(10, 93, 43),
)
CALI_BASS_PARAMETER_SEEDS = _phase69_amp_seeds(
    controls=(("gain", "GAIN", 0, "integer"), ("volume", "VOLUME", 1, "integer"), ("bass", "BASS", 2, "integer"), ("middle", "MIDDLE", 3, "integer"), ("treble", "TREBLE", 4, "integer")),
    defaults=(50, 50, 50, 50, 50),
    observed_values=(0, 100, 29, 88, 64),
)
A_BASSFT_PARAMETER_SEEDS = _phase69_amp_seeds(
    controls=(("volume", "VOLUME", 0, "integer"), ("bass", "BASS", 1, "integer"), ("treble", "TREBLE", 2, "integer")),
    defaults=(50, 50, 50),
    observed_values=(100, 38, 0),
)
F_2BASS_PARAMETER_SEEDS = _phase69_amp_seeds(
    controls=(("volume", "VOLUME", 0, "integer"), ("bright", "BRIGHT", 1, "boolean"), ("bass", "BASS", 2, "integer"), ("middle", "MIDDLE", 3, "integer"), ("treble", "TREBLE", 4, "integer")),
    defaults=(50, 0, 50, 50, 50),
    observed_values=(13, 0, 97, 77, 30),
)
_AC_PREAMP_CONTROLS = (
    ("volume", "VOLUME", 0, "integer"),
    ("tone", "TONE", 1, "integer"),
    ("balance", "BALANCE", 2, "integer"),
    ("eq_freq", "EQ FREQ", 3, "integer"),
    ("eq_q", "EQ Q", 4, "integer"),
    ("eq_gain", "EQ GAIN", 5, "integer"),
)
AC_PREAMP_PARAMETER_SEEDS = _phase69_amp_seeds(
    controls=_AC_PREAMP_CONTROLS,
    defaults=(50, 50, 50, 50, 50, 50),
    observed_values=(0, 100, 15, 98, 38, 94),
)
AC_PREAMP_2_PARAMETER_SEEDS = _phase69_amp_seeds(
    controls=_AC_PREAMP_CONTROLS,
    defaults=(50, 50, 50, 50, 50, 50),
    observed_values=(100, 78, 65, 0, 94, 29),
)


def _validated_phase70_cab_seeds(
    *,
    saved_values: tuple[int, int, int],
    evidence_source: str,
) -> tuple[dict[str, Any], ...]:
    """Parâmetros CAB confirmados por dump salvo + eventos 0x1C físicos."""

    controls = (
        ("volume", "VOLUME", 1, 0, 100, None, None),
        ("low_cut", "LOW CUT", 5, 19, 2000, "Hz", (19, "OFF")),
        ("high_cut", "HIGH CUT", 6, 2000, 20001, "Hz", (20001, "OFF")),
    )
    defaults = (50, 19, 20001)
    result: list[dict[str, Any]] = []
    for order, ((key, name, selector, minimum, maximum, unit, sentinel), default, saved) in enumerate(
        zip(controls, defaults, saved_values), start=1
    ):
        parameter: dict[str, Any] = {
            "key": key,
            "name": name,
            "display_order": order,
            "value_type": "integer",
            "range": {
                "minimum": minimum,
                "maximum": maximum,
                "step": 1,
            },
            "unit": unit,
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
                "offline": True,
                "physical": True,
                "read_only": True,
                "effect_identity_source": "current_chain",
                "parameter_selector": selector,
                "saved_dump_default": default,
                "saved_dump_default_source": "user_reported_official_ui",
                "saved_dump_value": saved,
                "selector_mapping_source": "pcapng_saved_dump_and_live_1c",
                "full_float32_required": True,
                "evidence": "docs/phases/CAB_SUPERO_DOUBLE_BASS_PARAMETERS_PHASE70.md",
                "capture_source": evidence_source,
                "monitor_integration_physical_validation": "approved",
                "monitor_validation_source": "user_live_monitor_phase70",
                "monitor_validation_result": "hydration_and_live_values_exact_to_device",
                "range_validated": [minimum, maximum],
            },
        }
        if sentinel is not None:
            parameter["display"] = {
                "kind": "numeric_with_sentinels",
                "sentinels": [
                    {"value": sentinel[0], "label": sentinel[1]}
                ],
            }
            parameter["validation"]["off_wire_value"] = sentinel[0]
        result.append(parameter)
    return tuple(result)


SUPERO_1X6_PARAMETER_SEEDS = _validated_phase70_cab_seeds(
    saved_values=(37, 630, 15500),
    evidence_source="CAB01_SUPERO_1X6_01..05 captures",
)
DOUBLE_BASS_PARAMETER_SEEDS = _validated_phase70_cab_seeds(
    saved_values=(28, 956, 13262),
    evidence_source="CAB02_DOUBLE_BASS_01..02 captures",
)


def _validated_phase71_cab_shared_schema_seeds() -> tuple[dict[str, Any], ...]:
    """Schema compartilhado CAB aprovado fisicamente em todos os modelos."""

    controls = (
        ("volume", "VOLUME", 1, 0, 100, None, None),
        ("low_cut", "LOW CUT", 5, 19, 2000, "Hz", (19, "OFF")),
        ("high_cut", "HIGH CUT", 6, 2000, 20001, "Hz", (20001, "OFF")),
    )
    defaults = (50, 19, 20001)
    result: list[dict[str, Any]] = []
    for order, (key, name, selector, minimum, maximum, unit, sentinel) in enumerate(controls, start=1):
        parameter: dict[str, Any] = {
            "key": key,
            "name": name,
            "display_order": order,
            "value_type": "integer",
            "range": {
                "minimum": minimum,
                "maximum": maximum,
                "step": 1,
            },
            "unit": unit,
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
                "offline": True,
                "physical": True,
                "read_only": True,
                "effect_identity_source": "current_chain",
                "parameter_selector": selector,
                "saved_dump_default": defaults[order - 1],
                "saved_dump_default_source": "user_reported_official_ui",
                "selector_mapping_source": "phase70_shared_schema_confirmed_across_all_cabs_phase71",
                "full_float32_required": True,
                "evidence": "docs/phases/CAB_CLASS_CONSOLIDATION_PHASE71.md",
                "monitor_integration_physical_validation": "approved",
                "monitor_validation_source": "user_live_monitor_all_cabs_phase71",
                "monitor_validation_result": "all_models_parameter_changes_and_float_values_exact_to_device",
                "range_validated": [minimum, maximum],
            },
        }
        if sentinel is not None:
            parameter["display"] = {
                "kind": "numeric_with_sentinels",
                "sentinels": [
                    {"value": sentinel[0], "label": sentinel[1]}
                ],
            }
            parameter["validation"]["off_wire_value"] = sentinel[0]
        result.append(parameter)
    return tuple(result)


CAB_SHARED_PARAMETER_SEEDS = _validated_phase71_cab_shared_schema_seeds()


def _validated_phase72_ir_shared_schema_seeds() -> tuple[dict[str, Any], ...]:
    """Schema compartilhado IR aprovado fisicamente em todos os 20 modelos."""

    controls = (
        ("volume", "VOLUME", 1, 0, 100, None, None),
        ("low_cut", "LOW CUT", 5, 19, 2000, "Hz", (19, "OFF")),
        ("high_cut", "HIGH CUT", 6, 2000, 20001, "Hz", (20001, "OFF")),
    )
    defaults = (50, 19, 20001)
    result: list[dict[str, Any]] = []
    for order, (key, name, selector, minimum, maximum, unit, sentinel) in enumerate(controls, start=1):
        parameter: dict[str, Any] = {
            "key": key,
            "name": name,
            "display_order": order,
            "value_type": "integer",
            "range": {"minimum": minimum, "maximum": maximum, "step": 1},
            "unit": unit,
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
                "offline": True,
                "physical": True,
                "read_only": True,
                "effect_identity_source": "current_chain",
                "parameter_selector": selector,
                "saved_dump_default": defaults[order - 1],
                "saved_dump_default_source": "user_reported_official_ui",
                "selector_mapping_source": "phase72_ir1_ir20_pcap_and_all_ir_live_validation",
                "full_float32_required": True,
                "evidence": "docs/phases/IR_CLASS_CONSOLIDATION_PHASE72.md",
                "monitor_integration_physical_validation": "approved",
                "monitor_validation_source": "user_live_monitor_all_irs_phase72_with_log",
                "monitor_validation_result": "all_20_models_parameter_values_exact_to_device",
                "range_validated": [minimum, maximum],
            },
        }
        if sentinel is not None:
            parameter["display"] = {
                "kind": "numeric_with_sentinels",
                "sentinels": [{"value": sentinel[0], "label": sentinel[1]}],
            }
            parameter["validation"]["off_wire_value"] = sentinel[0]
        result.append(parameter)
    return tuple(result)


IR_SHARED_PARAMETER_SEEDS = _validated_phase72_ir_shared_schema_seeds()


def _validated_phase73_eq_parameter_seeds(
    effect_key: str,
    bands: tuple[tuple[str, str], ...],
    *,
    include_volume: bool,
    pcap_anchor: bool,
) -> tuple[dict[str, Any], ...]:
    """Schema EQ aprovado fisicamente nos cinco modelos da classe."""

    parameters: list[dict[str, Any]] = []
    for order, (key, name) in enumerate(bands, start=1):
        selector = order - 1
        validation: dict[str, Any] = {
            "offline": True,
            "physical": True,
            "read_only": True,
            "effect_identity_source": "current_chain",
            "parameter_selector": selector,
            "saved_dump_default": 0,
            "saved_dump_default_source": "user_reported_official_ui",
            "selector_mapping_source": (
                "phase73_guitar_eq1_calif_eq_pcap"
                if pcap_anchor
                else "phase73_guitar_eq1_anchor_plus_all_eq_live_validation"
            ),
            "full_float32_required": True,
            "evidence": "docs/phases/EQ_CLASS_CONSOLIDATION_PHASE73.md",
            "monitor_integration_physical_validation": "approved",
            "monitor_validation_source": "user_live_monitor_all_eqs_phase73_with_log",
            "monitor_validation_result": "all_5_models_parameter_values_exact_to_device",
            "range_source": "user_reported_official_ui_and_phase73_anchor_sweeps",
            "range_validated": [-50, 50],
        }
        if pcap_anchor:
            validation["pcap_anchor"] = True
            validation["pcap_range_observed"] = [-50, 50]
        parameters.append(
            {
                "key": key,
                "name": name,
                "display_order": order,
                "value_type": "integer",
                "range": {"minimum": -50, "maximum": 50, "step": 1},
                "unit": None,
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
                "validation": validation,
            }
        )

    if include_volume:
        parameters.append(
            {
                "key": "volume",
                "name": "VOLUME",
                "display_order": 6,
                "value_type": "integer",
                "range": {"minimum": 0, "maximum": 100, "step": 1},
                "unit": None,
                "protocol": {
                    "profile": "effect_parameter_response_1c_v1",
                    "value_codec": "float32_nibbles_v1",
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
                    "effect_identity_source": "current_chain",
                    "parameter_selector": 5,
                    "saved_dump_default": 50,
                    "saved_dump_default_source": "user_reported_official_ui",
                    "selector_mapping_source": (
                        "phase73_guitar_eq1_pcap"
                        if pcap_anchor
                        else "phase73_guitar_eq1_anchor_plus_all_eq_live_validation"
                    ),
                    "full_float32_required": True,
                    "evidence": "docs/phases/EQ_CLASS_CONSOLIDATION_PHASE73.md",
                    "monitor_integration_physical_validation": "approved",
                    "monitor_validation_source": "user_live_monitor_all_eqs_phase73_with_log",
                    "monitor_validation_result": "all_5_models_parameter_values_exact_to_device",
                    "range_source": "user_reported_official_ui_and_phase73_guitar_eq1_sweep",
                    "range_validated": [0, 100],
                    **({"pcap_anchor": True, "pcap_range_observed": [0, 100]} if pcap_anchor else {}),
                },
            }
        )
    return tuple(parameters)


EQ_PARAMETER_SEEDS: dict[str, tuple[dict[str, Any], ...]] = {
    "eq.guitar_eq_1": _validated_phase73_eq_parameter_seeds(
        "eq.guitar_eq_1",
        (
            ("band_125_hz", "125 Hz"),
            ("band_400_hz", "400 Hz"),
            ("band_800_hz", "800 Hz"),
            ("band_1_6_khz", "1.6 kHz"),
            ("band_4_khz", "4 kHz"),
        ),
        include_volume=True,
        pcap_anchor=True,
    ),
    "eq.guitar_eq_2": _validated_phase73_eq_parameter_seeds(
        "eq.guitar_eq_2",
        (
            ("band_100_hz", "100 Hz"),
            ("band_500_hz", "500 Hz"),
            ("band_1_khz", "1 kHz"),
            ("band_3_khz", "3 kHz"),
            ("band_6_khz", "6 kHz"),
        ),
        include_volume=True,
        pcap_anchor=False,
    ),
    "eq.bass_eq_1": _validated_phase73_eq_parameter_seeds(
        "eq.bass_eq_1",
        (
            ("band_33_hz", "33 Hz"),
            ("band_150_hz", "150 Hz"),
            ("band_600_hz", "600 Hz"),
            ("band_2_khz", "2 kHz"),
            ("band_8_khz", "8 kHz"),
        ),
        include_volume=True,
        pcap_anchor=False,
    ),
    "eq.bass_eq_2": _validated_phase73_eq_parameter_seeds(
        "eq.bass_eq_2",
        (
            ("band_50_hz", "50 Hz"),
            ("band_120_hz", "120 Hz"),
            ("band_400_hz", "400 Hz"),
            ("band_800_hz", "800 Hz"),
            ("band_4_5_khz", "4.5 kHz"),
        ),
        include_volume=True,
        pcap_anchor=False,
    ),
    "eq.calif_eq": _validated_phase73_eq_parameter_seeds(
        "eq.calif_eq",
        (
            ("band_80_hz", "80 Hz"),
            ("band_240_hz", "240 Hz"),
            ("band_750_hz", "750 Hz"),
            ("band_2_2_khz", "2.2 kHz"),
            ("band_6_6_khz", "6.6 kHz"),
        ),
        include_volume=False,
        pcap_anchor=True,
    ),
}


MOD_SYNC_RATE_CHOICES: tuple[tuple[int, str], ...] = (
    (0, "1/1"), (1, "1/2"), (2, "1/2d"), (3, "1/2t"),
    (4, "1/4"), (5, "1/4d"), (6, "1/4t"), (7, "1/8"),
    (8, "1/8d"), (9, "1/8t"), (10, "1/16"),
)


def _phase74_mod_base_validation(selector: int, *, anchor: bool) -> dict[str, Any]:
    validation: dict[str, Any] = {
        "offline": True,
        "physical": True,
        "read_only": True,
        "effect_identity_source": "current_chain",
        "parameter_selector": selector,
        "evidence": "docs/phases/MOD_RATE_SYNC_FAMILY_CONSOLIDATION_PHASE74.md",
        "monitor_integration_physical_validation": "approved",
        "monitor_validation_source": "user_live_monitor_mod_rate_sync_family_phase74_with_log",
        "monitor_validation_result": "all_11_models_parameter_values_exact_to_device",
        "candidate_family": "phase74_e_chorus_rate_sync_family",
    }
    if anchor:
        validation.update({
            "pcap_anchor": True,
            "selector_mapping_source": "phase74_e_chorus_default_custom_sweep_pcap",
        })
    else:
        validation.update({
            "selector_mapping_source": "phase74_e_chorus_anchor_plus_user_reported_identical_or_subset_ui_schema_then_live_validated",
            "candidate_requires_live_validation": False,
        })
    return validation


def _phase74_mod_integer_parameter(
    key: str,
    name: str,
    order: int,
    selector: int,
    *,
    default: int = 50,
    anchor: bool,
) -> dict[str, Any]:
    validation = _phase74_mod_base_validation(selector, anchor=anchor)
    validation.update({
        "saved_dump_default": default,
        "saved_dump_default_source": "phase74_e_chorus_pcap" if anchor else "user_reported_official_ui",
        "range_source": "phase74_e_chorus_sweep_and_user_reported_official_ui" if anchor else "user_reported_official_ui",
        "range_validated": [0, 100],
        "full_float32_required": True,
    })
    return {
        "key": key,
        "name": name,
        "display_order": order,
        "value_type": "integer",
        "range": {"minimum": 0, "maximum": 100, "step": 1},
        "unit": None,
        "protocol": {
            "profile": "effect_parameter_response_1c_v1",
            "value_codec": "float32_nibbles_v1",
            "identification_status": "validated_with_chain_effect_context",
            "message_match": {"parameter_selector": selector, "parameter_marker": 1, "parameter_type": 1},
        },
        "validation": validation,
    }


def _phase74_mod_rate_parameter(order: int, selector: int, *, anchor: bool) -> dict[str, Any]:
    validation = _phase74_mod_base_validation(selector, anchor=anchor)
    validation.update({
        "conditional_domain_controller": "sync",
        "sync_off_default": 0.5,
        "sync_on_default_wire_value": 4,
        "sync_on_default_label": "1/4",
        "reset_on_sync_change_confirmed_by_user": True,
        "sync_transition_default_source": "user_physical_confirmation_phase74",
        "range_source": "phase74_e_chorus_sweep_and_user_reported_official_ui" if anchor else "user_reported_identical_rate_sync_ui_schema",
        "range_validated": [0.1, 10.0],
        "step_validated": 0.1,
        "full_float32_required": True,
    })
    return {
        "key": "rate",
        "name": "RATE",
        "display_order": order,
        "value_type": "number",
        # 0 is required by the shared wire domain for SYNC=ON (1/1).
        "range": {"minimum": 0, "maximum": 10, "step": 0.1},
        "unit": "Hz",
        "value_domain": {
            "controller_parameter": "sync",
            "reset_on_controller_change": True,
            "states": [
                {
                    "controller_value": False,
                    "default_value": 0.5,
                    "presentation": {"kind": "numeric", "unit": "Hz", "decimals": 1},
                },
                {
                    "controller_value": True,
                    "default_value": 4,
                    "presentation": {
                        "kind": "enum",
                        "choices": [
                            {"value": value, "label": label}
                            for value, label in MOD_SYNC_RATE_CHOICES
                        ],
                    },
                },
            ],
        },
        "protocol": {
            "profile": "effect_parameter_response_1c_v1",
            "value_codec": "float32_nibbles_v1",
            "identification_status": "validated_with_chain_effect_context",
            "message_match": {"parameter_selector": selector, "parameter_marker": 1, "parameter_type": 1},
        },
        "validation": validation,
    }


def _phase74_mod_sync_parameter(order: int, selector: int, *, anchor: bool) -> dict[str, Any]:
    validation = _phase74_mod_base_validation(selector, anchor=anchor)
    validation.update({
        "saved_dump_default": 0,
        "saved_dump_default_source": "phase74_e_chorus_pcap" if anchor else "user_reported_official_ui",
        "boolean_encoding": {"false": 0, "true": 1},
        "full_float32_required": True,
    })
    return {
        "key": "sync",
        "name": "SYNC",
        "display_order": order,
        "value_type": "boolean",
        "range": {"minimum": 0, "maximum": 1, "step": 1},
        "unit": None,
        "protocol": {
            "profile": "effect_parameter_response_1c_v1",
            "value_codec": "float32_nibbles_v1",
            "identification_status": "validated_with_chain_effect_context",
            "message_match": {"parameter_selector": selector, "parameter_marker": 1, "parameter_type": 1},
        },
        "validation": validation,
    }


def _phase74_mod_family_parameters(kind: str, *, anchor: bool) -> tuple[dict[str, Any], ...]:
    if kind == "full":
        return (
            _phase74_mod_integer_parameter("depth", "DEPTH", 1, 0, anchor=anchor),
            _phase74_mod_rate_parameter(2, 1, anchor=anchor),
            _phase74_mod_integer_parameter("volume", "VOLUME", 3, 2, anchor=anchor),
            _phase74_mod_sync_parameter(4, 3, anchor=anchor),
        )
    if kind == "compact":
        return (
            _phase74_mod_integer_parameter("depth", "DEPTH", 1, 0, anchor=anchor),
            _phase74_mod_rate_parameter(2, 1, anchor=anchor),
            _phase74_mod_sync_parameter(3, 2, anchor=anchor),
        )
    if kind == "rate_sync":
        return (
            _phase74_mod_rate_parameter(1, 0, anchor=anchor),
            _phase74_mod_sync_parameter(2, 1, anchor=anchor),
        )
    raise ValueError(f"Família MOD desconhecida: {kind}")


MOD_PHASE74_FAMILY_PARAMETER_SEEDS: dict[str, tuple[dict[str, Any], ...]] = {
    "mod.e_chorus": _phase74_mod_family_parameters("full", anchor=True),
    "mod.b_chorus": _phase74_mod_family_parameters("full", anchor=False),
    "mod.vibrato": _phase74_mod_family_parameters("full", anchor=False),
    "mod.ce_roto": _phase74_mod_family_parameters("full", anchor=False),
    "mod.sine_trem": _phase74_mod_family_parameters("full", anchor=False),
    "mod.triangule_trem": _phase74_mod_family_parameters("full", anchor=False),
    "mod.bbd_roto": _phase74_mod_family_parameters("compact", anchor=False),
    "mod.bbd_phaser": _phase74_mod_family_parameters("compact", anchor=False),
    "mod.vibe": _phase74_mod_family_parameters("compact", anchor=False),
    "mod.tremolo": _phase74_mod_family_parameters("compact", anchor=False),
    "mod.phaser": _phase74_mod_family_parameters("rate_sync", anchor=False),
}



def _phase75_mod_flanger_base_validation(selector: int) -> dict[str, Any]:
    return {
        "offline": True,
        "physical": True,
        "read_only": True,
        "effect_identity_source": "current_chain",
        "parameter_selector": selector,
        "evidence": "docs/phases/MOD_FLANGER_FAMILY_CONSOLIDATION_PHASE75.md",
        "monitor_integration_physical_validation": "approved",
        "monitor_validation_source": "user_live_monitor_mod_flanger_family_phase75_with_log",
        "monitor_validation_result": "all_3_models_parameter_values_exact_to_device",
        "candidate_family": "phase75_mod_flanger_family",
        "candidate_requires_live_validation": False,
        "selector_mapping_source": "user_reported_identical_flanger_family_ui_order_plus_phase74_rate_sync_anchor",
    }


def _phase75_mod_flanger_integer_parameter(
    key: str,
    name: str,
    order: int,
    selector: int,
) -> dict[str, Any]:
    validation = _phase75_mod_flanger_base_validation(selector)
    validation.update({
        "saved_dump_default": 50,
        "saved_dump_default_source": "user_reported_official_ui",
        "range_source": "user_reported_official_ui",
        "range_validated": [0, 100],
        "full_float32_required": True,
    })
    return {
        "key": key,
        "name": name,
        "display_order": order,
        "value_type": "integer",
        "range": {"minimum": 0, "maximum": 100, "step": 1},
        "unit": None,
        "protocol": {
            "profile": "effect_parameter_response_1c_v1",
            "value_codec": "float32_nibbles_v1",
            "identification_status": "validated_with_chain_effect_context",
            "message_match": {"parameter_selector": selector, "parameter_marker": 1, "parameter_type": 1},
        },
        "validation": validation,
    }


def _phase75_mod_flanger_rate_parameter() -> dict[str, Any]:
    validation = _phase75_mod_flanger_base_validation(1)
    validation.update({
        "conditional_domain_controller": "sync",
        "sync_off_default": 0.5,
        "sync_on_default_wire_value": 4,
        "sync_on_default_label": "1/4",
        "reset_on_sync_change_confirmed_by_user": True,
        "sync_transition_default_source": "user_physical_confirmation_phase74_and_user_reported_shared_mod_rate_sync_behavior",
        "range_source": "phase74_e_chorus_rate_sync_anchor_plus_user_reported_identical_mod_rate_schema",
        "range_validated": [0.1, 10.0],
        "step_validated": 0.1,
        "full_float32_required": True,
    })
    return {
        "key": "rate",
        "name": "RATE",
        "display_order": 2,
        "value_type": "number",
        "range": {"minimum": 0, "maximum": 10, "step": 0.1},
        "unit": "Hz",
        "value_domain": {
            "controller_parameter": "sync",
            "reset_on_controller_change": True,
            "states": [
                {
                    "controller_value": False,
                    "default_value": 0.5,
                    "presentation": {"kind": "numeric", "unit": "Hz", "decimals": 1},
                },
                {
                    "controller_value": True,
                    "default_value": 4,
                    "presentation": {
                        "kind": "enum",
                        "choices": [
                            {"value": value, "label": label}
                            for value, label in MOD_SYNC_RATE_CHOICES
                        ],
                    },
                },
            ],
        },
        "protocol": {
            "profile": "effect_parameter_response_1c_v1",
            "value_codec": "float32_nibbles_v1",
            "identification_status": "validated_with_chain_effect_context",
            "message_match": {"parameter_selector": 1, "parameter_marker": 1, "parameter_type": 1},
        },
        "validation": validation,
    }


def _phase75_mod_flanger_sync_parameter() -> dict[str, Any]:
    validation = _phase75_mod_flanger_base_validation(4)
    validation.update({
        "saved_dump_default": 0,
        "saved_dump_default_source": "user_reported_official_ui",
        "boolean_encoding": {"false": 0, "true": 1},
        "full_float32_required": True,
    })
    return {
        "key": "sync",
        "name": "SYNC",
        "display_order": 5,
        "value_type": "boolean",
        "range": {"minimum": 0, "maximum": 1, "step": 1},
        "unit": None,
        "protocol": {
            "profile": "effect_parameter_response_1c_v1",
            "value_codec": "float32_nibbles_v1",
            "identification_status": "validated_with_chain_effect_context",
            "message_match": {"parameter_selector": 4, "parameter_marker": 1, "parameter_type": 1},
        },
        "validation": validation,
    }


def _phase75_mod_flanger_family_parameters() -> tuple[dict[str, Any], ...]:
    return (
        _phase75_mod_flanger_integer_parameter("depth", "DEPTH", 1, 0),
        _phase75_mod_flanger_rate_parameter(),
        _phase75_mod_flanger_integer_parameter("pre_delay", "PRE DELAY", 3, 2),
        _phase75_mod_flanger_integer_parameter("feedback", "FEEDBACK", 4, 3),
        _phase75_mod_flanger_sync_parameter(),
    )


MOD_PHASE75_FLANGER_FAMILY_PARAMETER_SEEDS: dict[str, tuple[dict[str, Any], ...]] = {
    "mod.flanger": _phase75_mod_flanger_family_parameters(),
    "mod.flanger_n": _phase75_mod_flanger_family_parameters(),
    "mod.bass_jet": _phase75_mod_flanger_family_parameters(),
}


def _phase76_mod_dual_sync_base_validation(selector: int) -> dict[str, Any]:
    return {
        "offline": True,
        "physical": True,
        "read_only": True,
        "effect_identity_source": "current_chain",
        "parameter_selector": selector,
        "evidence": "docs/phases/MOD_DUAL_SYNC_FAMILY_CONSOLIDATION_PHASE76.md",
        "monitor_integration_physical_validation": "approved",
        "candidate_family": "phase76_mod_dual_sync_family",
        "candidate_requires_live_validation": False,
        "selector_mapping_source": "user_reported_ui_order_plus_phase74_validated_rate_sync_schema",
        "full_float32_required": True,
        "monitor_validation_source": "user_live_monitor_mod_dual_sync_phase76_with_log",
        "monitor_validation_result": "trem_jet_and_pan_phaser_all_values_exact_to_device",
    }


def _phase76_mod_integer_parameter(key: str, name: str, order: int, selector: int) -> dict[str, Any]:
    validation = _phase76_mod_dual_sync_base_validation(selector)
    validation.update({
        "saved_dump_default": 50,
        "saved_dump_default_source": "user_reported_official_ui",
        "range_source": "user_reported_official_ui",
        "range_validated": [0, 100],
    })
    return {
        "key": key,
        "name": name,
        "display_order": order,
        "value_type": "integer",
        "range": {"minimum": 0, "maximum": 100, "step": 1},
        "unit": None,
        "protocol": {
            "profile": "effect_parameter_response_1c_v1",
            "value_codec": "float32_nibbles_v1",
            "identification_status": "validated_with_chain_effect_context",
            "message_match": {"parameter_selector": selector, "parameter_marker": 1, "parameter_type": 1},
        },
        "validation": validation,
    }


def _phase76_mod_rate_parameter(
    key: str,
    name: str,
    order: int,
    selector: int,
    controller_key: str,
) -> dict[str, Any]:
    validation = _phase76_mod_dual_sync_base_validation(selector)
    validation.update({
        "conditional_domain_controller": controller_key,
        "sync_off_default": 0.5,
        "sync_on_default_wire_value": 4,
        "sync_on_default_label": "1/4",
        "reset_on_sync_change_confirmed_by_user": True,
        "sync_transition_default_source": "user_physical_confirmation_phase74_and_user_reported_shared_mod_rate_sync_behavior",
        "range_source": "phase74_e_chorus_rate_sync_anchor_plus_user_reported_identical_mod_rate_schema",
        "range_validated": [0.1, 10.0],
        "step_validated": 0.1,
    })
    return {
        "key": key,
        "name": name,
        "display_order": order,
        "value_type": "number",
        "range": {"minimum": 0, "maximum": 10, "step": 0.1},
        "unit": "Hz",
        "value_domain": {
            "controller_parameter": controller_key,
            "reset_on_controller_change": True,
            "states": [
                {
                    "controller_value": False,
                    "default_value": 0.5,
                    "presentation": {"kind": "numeric", "unit": "Hz", "decimals": 1},
                },
                {
                    "controller_value": True,
                    "default_value": 4,
                    "presentation": {
                        "kind": "enum",
                        "choices": [
                            {"value": value, "label": label}
                            for value, label in MOD_SYNC_RATE_CHOICES
                        ],
                    },
                },
            ],
        },
        "protocol": {
            "profile": "effect_parameter_response_1c_v1",
            "value_codec": "float32_nibbles_v1",
            "identification_status": "validated_with_chain_effect_context",
            "message_match": {"parameter_selector": selector, "parameter_marker": 1, "parameter_type": 1},
        },
        "validation": validation,
    }


def _phase76_mod_sync_parameter(key: str, name: str, order: int, selector: int) -> dict[str, Any]:
    validation = _phase76_mod_dual_sync_base_validation(selector)
    validation.update({
        "saved_dump_default": 0,
        "saved_dump_default_source": "user_reported_official_ui",
        "boolean_encoding": {"false": 0, "true": 1},
    })
    return {
        "key": key,
        "name": name,
        "display_order": order,
        "value_type": "boolean",
        "range": {"minimum": 0, "maximum": 1, "step": 1},
        "unit": None,
        "protocol": {
            "profile": "effect_parameter_response_1c_v1",
            "value_codec": "float32_nibbles_v1",
            "identification_status": "validated_with_chain_effect_context",
            "message_match": {"parameter_selector": selector, "parameter_marker": 1, "parameter_type": 1},
        },
        "validation": validation,
    }


def _phase76_trem_jet_parameters() -> tuple[dict[str, Any], ...]:
    return (
        _phase76_mod_integer_parameter("flg_depth", "FLG DEPTH", 1, 0),
        _phase76_mod_rate_parameter("flg_rate", "FLG RATE", 2, 1, "flg_sync"),
        _phase76_mod_integer_parameter("feedback", "FEEDBACK", 3, 2),
        _phase76_mod_integer_parameter("trm_depth", "TRM DEPTH", 4, 3),
        _phase76_mod_rate_parameter("trm_rate", "TRM RATE", 5, 4, "trm_sync"),
        _phase76_mod_sync_parameter("flg_sync", "FLG SYNC", 6, 5),
        _phase76_mod_sync_parameter("trm_sync", "TRM SYNC", 7, 6),
    )


def _phase76_pan_phaser_parameters() -> tuple[dict[str, Any], ...]:
    return (
        _phase76_mod_integer_parameter("phs_depth", "PHS DEPTH", 1, 0),
        _phase76_mod_rate_parameter("phs_rate", "PHS RATE", 2, 1, "phs_sync"),
        _phase76_mod_integer_parameter("pan_depth", "PAN DEPTH", 3, 2),
        _phase76_mod_rate_parameter("pan_rate", "PAN RATE", 4, 3, "pan_sync"),
        _phase76_mod_sync_parameter("phs_sync", "PHS SYNC", 5, 4),
        _phase76_mod_sync_parameter("pan_sync", "PAN SYNC", 6, 5),
    )


MOD_PHASE76_DUAL_SYNC_PARAMETER_SEEDS: dict[str, tuple[dict[str, Any], ...]] = {
    "mod.trem_jet": _phase76_trem_jet_parameters(),
    "mod.pan_phaser": _phase76_pan_phaser_parameters(),
}


def _phase77_mod_family_base_validation(selector: int) -> dict[str, Any]:
    return {
        "offline": True,
        "physical": True,
        "read_only": True,
        "effect_identity_source": "current_chain",
        "parameter_selector": selector,
        "evidence": "docs/phases/MOD_ENUM_BIAS_FAMILY_CONSOLIDATION_PHASE77.md",
        "monitor_integration_physical_validation": "approved",
        "candidate_family": "phase77_mod_enum_bias_family",
        "candidate_requires_live_validation": False,
        "selector_mapping_source": "user_reported_ui_order_plus_phase74_validated_rate_sync_schema",
        "full_float32_required": True,
        "monitor_validation_source": "user_live_monitor_mod_enum_bias_phase77_with_log",
        "monitor_validation_result": "phaser_st_u_vibe_bias_trem_all_values_exact_to_device",
    }


def _phase77_mod_integer_parameter(key: str, name: str, order: int, selector: int) -> dict[str, Any]:
    validation = _phase77_mod_family_base_validation(selector)
    validation.update({
        "saved_dump_default": 50,
        "saved_dump_default_source": "user_reported_official_ui",
        "range_source": "user_reported_official_ui",
        "range_validated": [0, 100],
    })
    return {
        "key": key,
        "name": name,
        "display_order": order,
        "value_type": "integer",
        "range": {"minimum": 0, "maximum": 100, "step": 1},
        "unit": None,
        "protocol": {
            "profile": "effect_parameter_response_1c_v1",
            "value_codec": "float32_nibbles_v1",
            "identification_status": "validated_with_chain_effect_context",
            "message_match": {"parameter_selector": selector, "parameter_marker": 1, "parameter_type": 1},
        },
        "validation": validation,
    }


def _phase77_mod_rate_parameter(order: int, selector: int, controller_key: str = "sync") -> dict[str, Any]:
    validation = _phase77_mod_family_base_validation(selector)
    validation.update({
        "conditional_domain_controller": controller_key,
        "sync_off_default": 0.5,
        "sync_on_default_wire_value": 4,
        "sync_on_default_label": "1/4",
        "reset_on_sync_change_confirmed_by_user": True,
        "sync_transition_default_source": "user_physical_confirmation_phase74_and_user_reported_shared_mod_rate_sync_behavior",
        "range_source": "phase74_e_chorus_rate_sync_anchor_plus_user_reported_identical_mod_rate_schema",
        "range_validated": [0.1, 10.0],
        "step_validated": 0.1,
    })
    return {
        "key": "rate",
        "name": "RATE",
        "display_order": order,
        "value_type": "number",
        "range": {"minimum": 0, "maximum": 10, "step": 0.1},
        "unit": "Hz",
        "value_domain": {
            "controller_parameter": controller_key,
            "reset_on_controller_change": True,
            "states": [
                {
                    "controller_value": False,
                    "default_value": 0.5,
                    "presentation": {"kind": "numeric", "unit": "Hz", "decimals": 1},
                },
                {
                    "controller_value": True,
                    "default_value": 4,
                    "presentation": {
                        "kind": "enum",
                        "choices": [
                            {"value": value, "label": label}
                            for value, label in MOD_SYNC_RATE_CHOICES
                        ],
                    },
                },
            ],
        },
        "protocol": {
            "profile": "effect_parameter_response_1c_v1",
            "value_codec": "float32_nibbles_v1",
            "identification_status": "validated_with_chain_effect_context",
            "message_match": {"parameter_selector": selector, "parameter_marker": 1, "parameter_type": 1},
        },
        "validation": validation,
    }


def _phase77_mod_sync_parameter(order: int, selector: int) -> dict[str, Any]:
    validation = _phase77_mod_family_base_validation(selector)
    validation.update({
        "saved_dump_default": 0,
        "saved_dump_default_source": "user_reported_official_ui",
        "boolean_encoding": {"false": 0, "true": 1},
    })
    return {
        "key": "sync",
        "name": "SYNC",
        "display_order": order,
        "value_type": "boolean",
        "range": {"minimum": 0, "maximum": 1, "step": 1},
        "unit": None,
        "protocol": {
            "profile": "effect_parameter_response_1c_v1",
            "value_codec": "float32_nibbles_v1",
            "identification_status": "validated_with_chain_effect_context",
            "message_match": {"parameter_selector": selector, "parameter_marker": 1, "parameter_type": 1},
        },
        "validation": validation,
    }


def _phase77_mod_enum_parameter(
    key: str,
    name: str,
    order: int,
    selector: int,
    choices: tuple[tuple[int, str], ...],
    default_value: int,
) -> dict[str, Any]:
    validation = _phase77_mod_family_base_validation(selector)
    validation.update({
        "saved_dump_default": default_value,
        "saved_dump_default_source": "user_reported_official_ui_and_natural_enum_order_candidate",
        "enum_mapping_source": "user_reported_ui_choices_natural_zero_based_candidate",
        "candidate_enum_mapping_requires_live_validation": False,
        "enum_mapping_validation_source": "user_live_monitor_mod_enum_bias_phase77_with_log",
    })
    return {
        "key": key,
        "name": name,
        "display_order": order,
        "value_type": "enum",
        "range": {"minimum": min(value for value, _label in choices), "maximum": max(value for value, _label in choices), "step": 1},
        "choices": [{"value": value, "label": label} for value, label in choices],
        "unit": None,
        "protocol": {
            "profile": "effect_parameter_response_1c_v1",
            "value_codec": "float32_nibbles_v1",
            "identification_status": "validated_with_chain_effect_context",
            "message_match": {"parameter_selector": selector, "parameter_marker": 1, "parameter_type": 1},
        },
        "validation": validation,
    }


def _phase77_phaser_st_parameters() -> tuple[dict[str, Any], ...]:
    return (
        _phase77_mod_enum_parameter("color", "COLOR", 1, 0, ((0, "WARM"), (1, "SHARP")), 0),
        _phase77_mod_rate_parameter(2, 1),
        _phase77_mod_sync_parameter(3, 2),
    )


def _phase77_u_vibe_parameters() -> tuple[dict[str, Any], ...]:
    return (
        _phase77_mod_integer_parameter("depth", "DEPTH", 1, 0),
        _phase77_mod_rate_parameter(2, 1),
        _phase77_mod_integer_parameter("volume", "VOLUME", 3, 2),
        _phase77_mod_enum_parameter("mode", "MODE", 4, 3, ((0, "CHORUS"), (1, "VIBRATO")), 0),
        _phase77_mod_sync_parameter(5, 4),
    )


def _phase77_bias_trem_parameters() -> tuple[dict[str, Any], ...]:
    return (
        _phase77_mod_integer_parameter("depth", "DEPTH", 1, 0),
        _phase77_mod_rate_parameter(2, 1),
        _phase77_mod_integer_parameter("volume", "VOLUME", 3, 2),
        _phase77_mod_sync_parameter(4, 3),
        _phase77_mod_integer_parameter("bias", "BIAS", 5, 4),
    )


MOD_PHASE77_ENUM_BIAS_PARAMETER_SEEDS: dict[str, tuple[dict[str, Any], ...]] = {
    "mod.phaser_st": _phase77_phaser_st_parameters(),
    "mod.u_vibe": _phase77_u_vibe_parameters(),
    "mod.bias_trem": _phase77_bias_trem_parameters(),
}



def _phase78_mod_final_base_validation(selector: int, source: str) -> dict[str, Any]:
    return {
        "offline": True,
        "physical": False,
        "read_only": True,
        "effect_identity_source": "current_chain",
        "parameter_selector": selector,
        "evidence": "docs/phases/MOD_FINAL_FOUR_CANDIDATES_PHASE78.md",
        "monitor_integration_physical_validation": "pending",
        "candidate_family": "phase78_mod_final_four",
        "candidate_requires_live_validation": True,
        "selector_mapping_source": source,
        "full_float32_required": True,
    }


def _phase78_mod_integer_parameter(key: str, name: str, order: int, selector: int, *, default: int = 50, minimum: int = 0, maximum: int = 100, unit: str | None = None, source: str = "user_reported_ui_order_and_established_numeric_schema") -> dict[str, Any]:
    validation = _phase78_mod_final_base_validation(selector, source)
    validation.update({
        "saved_dump_default": default,
        "saved_dump_default_source": "user_reported_official_ui",
        "range_source": "user_reported_official_ui_and_established_float32_numeric_schema",
        "range_validated": [minimum, maximum],
    })
    return {
        "key": key, "name": name, "display_order": order, "value_type": "integer",
        "range": {"minimum": minimum, "maximum": maximum, "step": 1}, "unit": unit,
        "protocol": {"profile": "effect_parameter_response_1c_v1", "value_codec": "float32_nibbles_v1", "identification_status": "validated_with_chain_effect_context", "message_match": {"parameter_selector": selector, "parameter_marker": 1, "parameter_type": 1}},
        "validation": validation,
    }


def _phase78_mod_rate_parameter(order: int, selector: int, controller_key: str = "sync") -> dict[str, Any]:
    validation = _phase78_mod_final_base_validation(selector, "user_reported_ui_order_plus_phase74_validated_rate_sync_schema")
    validation.update({
        "conditional_domain_controller": controller_key,
        "sync_off_default": 0.5,
        "sync_on_default_wire_value": 4,
        "sync_on_default_label": "1/4",
        "reset_on_sync_change_confirmed_by_user": True,
        "sync_transition_default_source": "user_physical_confirmation_phase74",
        "range_source": "phase74_e_chorus_rate_sync_anchor_plus_user_reported_shared_mod_rate_schema",
        "range_validated": [0.1, 10.0],
        "step_validated": 0.1,
    })
    return {
        "key": "rate", "name": "RATE", "display_order": order, "value_type": "number",
        "range": {"minimum": 0, "maximum": 10, "step": 0.1}, "unit": "Hz",
        "value_domain": {"controller_parameter": controller_key, "reset_on_controller_change": True, "states": [
            {"controller_value": False, "default_value": 0.5, "presentation": {"kind": "numeric", "unit": "Hz", "decimals": 1}},
            {"controller_value": True, "default_value": 4, "presentation": {"kind": "enum", "choices": [{"value": value, "label": label} for value, label in MOD_SYNC_RATE_CHOICES]}},
        ]},
        "protocol": {"profile": "effect_parameter_response_1c_v1", "value_codec": "float32_nibbles_v1", "identification_status": "validated_with_chain_effect_context", "message_match": {"parameter_selector": selector, "parameter_marker": 1, "parameter_type": 1}},
        "validation": validation,
    }


def _phase78_mod_sync_parameter(order: int, selector: int) -> dict[str, Any]:
    validation = _phase78_mod_final_base_validation(selector, "user_reported_ui_order_plus_phase74_validated_rate_sync_schema")
    validation.update({"saved_dump_default": 0, "saved_dump_default_source": "user_reported_official_ui", "boolean_encoding": {"false": 0, "true": 1}})
    return {
        "key": "sync", "name": "SYNC", "display_order": order, "value_type": "boolean",
        "range": {"minimum": 0, "maximum": 1, "step": 1}, "unit": None,
        "protocol": {"profile": "effect_parameter_response_1c_v1", "value_codec": "float32_nibbles_v1", "identification_status": "validated_with_chain_effect_context", "message_match": {"parameter_selector": selector, "parameter_marker": 1, "parameter_type": 1}},
        "validation": validation,
    }


def _phase78_mod_enum_parameter(key: str, name: str, order: int, selector: int, choices: tuple[tuple[int, str], ...], default_value: int, source: str) -> dict[str, Any]:
    validation = _phase78_mod_final_base_validation(selector, source)
    validation.update({
        "saved_dump_default": default_value,
        "saved_dump_default_source": "user_reported_official_ui",
        "enum_mapping_source": "user_reported_ui_values_candidate",
        "candidate_enum_mapping_requires_live_validation": False,
    })
    values = [value for value, _label in choices]
    return {
        "key": key, "name": name, "display_order": order, "value_type": "enum",
        "range": {"minimum": min(values), "maximum": max(values), "step": 1},
        "choices": [{"value": value, "label": label} for value, label in choices], "unit": None,
        "protocol": {"profile": "effect_parameter_response_1c_v1", "value_codec": "float32_nibbles_v1", "identification_status": "validated_with_chain_effect_context", "message_match": {"parameter_selector": selector, "parameter_marker": 1, "parameter_type": 1}},
        "validation": validation,
    }


def _phase78_d_chorus_parameters() -> tuple[dict[str, Any], ...]:
    parameters = list(_phase78_mod_enum_parameter(
        "mode", "MODE", 1, 0,
        ((0, "1"), (1, "2"), (2, "3"), (3, "4")),
        0,
        "user_live_monitor_phase78_confirms_zero_based_wire_to_one_based_ui",
    ) for _ in range(1))
    validation = parameters[0]["validation"]
    validation.update({
        "saved_dump_default": 0,
        "saved_dump_default_source": "user_physical_default_ui_1_plus_live_monitor_wire_0_observation",
        "ui_default_label": "1",
        "wire_default": 0,
        "enum_mapping_source": "user_live_monitor_phase78_off_by_one_sequence",
        "candidate_enum_mapping_requires_live_validation": False,
        "correction_reason": "device_ui_is_one_based_while_wire_enum_is_zero_based",
        "evidence": "docs/phases/MOD_CLASS_CONSOLIDATION_PHASE78.md",
        "monitor_validation_source": "user_live_retest_after_phase78_zero_based_fix",
        "monitor_validation_result": "d_chorus_wire_0_3_maps_exactly_to_ui_mode_1_4",
    })
    return tuple(parameters)


def _phase78_promote_live_validated(
    parameters: tuple[dict[str, Any], ...],
    result: str,
    source: str = "user_live_monitor_mod_phase78_final_four_with_log",
) -> tuple[dict[str, Any], ...]:
    promoted: list[dict[str, Any]] = []
    for parameter in parameters:
        item = json.loads(json.dumps(parameter))
        validation = item["validation"]
        validation.update({
            "physical": True,
            "evidence": "docs/phases/MOD_CLASS_CONSOLIDATION_PHASE78.md",
            "monitor_integration_physical_validation": "approved",
            "candidate_requires_live_validation": False,
            "monitor_validation_source": source,
            "monitor_validation_result": result,
        })
        promoted.append(item)
    return tuple(promoted)


def _phase78_m_chorus_parameters() -> tuple[dict[str, Any], ...]:
    return (
        _phase78_mod_integer_parameter("mix", "MIX", 1, 0),
        _phase78_mod_rate_parameter(2, 1),
        _phase78_mod_integer_parameter("filter", "FILTER", 3, 2),
        _phase78_mod_integer_parameter("depth_l", "DEPTH L", 4, 3),
        _phase78_mod_integer_parameter("depth_c", "DEPTH C", 5, 4),
        _phase78_mod_integer_parameter("depth_r", "DEPTH R", 6, 5),
        _phase78_mod_sync_parameter(7, 6),
    )


def _phase78_detune_parameters() -> tuple[dict[str, Any], ...]:
    return (
        _phase78_mod_integer_parameter("detune", "DETUNE", 1, 0, default=-25, minimum=-50, maximum=50, unit="cents", source="user_reported_ui_order_plus_phase73_validated_signed_float32_schema"),
        _phase78_mod_integer_parameter("wet", "WET", 2, 1),
        _phase78_mod_integer_parameter("dry", "DRY", 3, 2),
    )


def _phase78_lofi_bit_parameters() -> tuple[dict[str, Any], ...]:
    return (
        _phase78_mod_integer_parameter("mix", "MIX", 1, 0, default=50),
        _phase78_mod_integer_parameter("krush", "KRUSH", 2, 1, default=20),
        _phase78_mod_integer_parameter("bit", "BIT", 3, 2, default=20),
        _phase78_mod_integer_parameter("hi_cut", "HI CUT", 4, 3, default=50),
        _phase78_mod_integer_parameter("lo_cut", "LO CUT", 5, 4, default=50),
    )


MOD_PHASE78_FINAL_FOUR_PARAMETER_SEEDS: dict[str, tuple[dict[str, Any], ...]] = {
    "mod.d_chorus": _phase78_promote_live_validated(
        _phase78_d_chorus_parameters(),
        "d_chorus_wire_0_3_maps_exactly_to_ui_mode_1_4",
        "user_live_retest_after_phase78_zero_based_fix",
    ),
    "mod.m_chorus": _phase78_promote_live_validated(
        _phase78_m_chorus_parameters(),
        "m_chorus_all_seven_parameters_exact_to_device",
    ),
    "mod.detune": _phase78_promote_live_validated(
        _phase78_detune_parameters(),
        "detune_signed_range_wet_dry_exact_to_device",
    ),
    "mod.lofi_bit": _phase78_promote_live_validated(
        _phase78_lofi_bit_parameters(),
        "lofi_bit_all_five_parameters_exact_to_device",
    ),
}


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


PITCH_S_RANGE_CHOICES = (
    "-2 OCT", "-1 OCT", "+1 OCT", "+2 OCT", "+/-1 OCT", "+/-2 OCT",
)


PITCH_S_PARAMETER_SEEDS: tuple[dict[str, Any], ...] = (
    {
        "key": "range",
        "name": "RANGE",
        "display_order": 1,
        "value_type": "enum",
        "range": {"minimum": 0, "maximum": 5, "step": 1},
        "choices": [
            {"value": value, "label": label}
            for value, label in enumerate(PITCH_S_RANGE_CHOICES)
        ],
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
            "enum_wire_values_validated": [0, 1, 2, 3, 4, 5],
            "internal_slots_observed": [1],
            "effect_identity_source": "current_chain",
            "parameter_selector": 0,
            "multiple_parameters": True,
            "saved_dump_default": 2,
            "physical_saved_dump_count": 3,
            "physical_live_sweep": True,
            "evidence": "docs/phases/FREQ_PITCH_S_RANGE_PARAMETERS_PHASE39.md",
            "monitor_integration_physical_validation": "pending",
        },
    },
    *(
        {
            "key": key,
            "name": name,
            "display_order": order,
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
                "internal_slots_observed": [1],
                "effect_identity_source": "current_chain",
                "parameter_selector": selector,
                "multiple_parameters": True,
                "saved_dump_default": default,
                "physical_saved_dump_count": 3,
                "physical_live_sweep": True,
                "evidence": "docs/phases/FREQ_PITCH_S_RANGE_PARAMETERS_PHASE39.md",
                "monitor_integration_physical_validation": "pending",
            },
        }
        for key, name, order, selector, default in (
            ("position", "POSITION", 2, 1, 0),
            ("mix", "MIX", 3, 2, 100),
            ("level", "LEVEL", 4, 3, 100),
        )
    ),
)


RING_MOD_PARAMETER_SEEDS: tuple[dict[str, Any], ...] = tuple(
    {
        "key": key,
        "name": name,
        "display_order": order,
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
            "saved_dump_default": default,
            "physical_saved_dump_count": 3,
            "physical_live_sweep": True,
            "evidence": "docs/phases/FREQ_RING_MOD_SIGNED_PARAMETERS_PHASE40.md",
            "monitor_integration_physical_validation": "pending",
            **(
                {
                    "signed_numeric_encoding": "native_float32_negative",
                    "signed_values_physically_observed": [-49, -17, -16, -1],
                    "documented_domain_minimum": -50,
                }
                if key == "fine"
                else {}
            ),
        },
    }
    for key, name, order, selector, minimum, maximum, default in (
        ("mix", "MIX", 1, 0, 0, 100, 50),
        ("freq", "FREQ.", 2, 1, 0, 100, 50),
        ("fine", "FINE", 3, 2, -50, 50, 0),
        ("tone", "TONE", 4, 3, 0, 100, 50),
    )
)


TAPE_MOD_PARAMETER_SEEDS: tuple[dict[str, Any], ...] = tuple(
    {
        "key": key,
        "name": name,
        "display_order": order,
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
            "saved_dump_default": 50,
            "physical_saved_dump_count": 3,
            "physical_live_sweep": True,
            "second_slot_live_validation": True,
            "evidence": "docs/phases/FREQ_TAPE_MOD_PARAMETERS_PHASE41.md",
            "monitor_integration_physical_validation": "pending",
        },
    }
    for key, name, order, selector in (
        ("saturation", "SATURATION", 1, 0),
        ("mix", "MIX", 2, 1),
        ("volume", "VOLUME", 3, 2),
        ("high_cut", "HIGH CUT", 4, 3),
    )
)


VOKS_WAH_PARAMETER_SEEDS: tuple[dict[str, Any], ...] = tuple(
    {
        "key": key,
        "name": name,
        "display_order": order,
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
            "internal_slots_observed": [1],
            "effect_identity_source": "current_chain",
            "parameter_selector": selector,
            "multiple_parameters": True,
            "saved_dump_default": 50,
            "physical_saved_dump_count": 3,
            "physical_live_sweep": True,
            "evidence": "docs/phases/WAH_VOKS_WAH_PARAMETERS_PHASE42.md",
            "monitor_integration_physical_validation": "pending",
        },
    }
    for key, name, order, selector in (
        ("range", "RANGE", 1, 0),
        ("q", "Q", 2, 1),
        ("volume", "VOLUME", 3, 2),
        ("position", "POSITION", 4, 3),
    )
)


CRY_WAH_PARAMETER_SEEDS: tuple[dict[str, Any], ...] = tuple(
    {
        "key": key,
        "name": name,
        "display_order": order,
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
            "internal_slots_observed": [1],
            "effect_identity_source": "current_chain",
            "parameter_selector": selector,
            "multiple_parameters": True,
            "saved_dump_default": 50,
            "physical_saved_dump_count": 3,
            "physical_live_sweep": True,
            "evidence": "docs/phases/WAH_CRY_WAH_PARAMETERS_PHASE43.md",
            "monitor_integration_physical_validation": "pending",
        },
    }
    for key, name, order, selector in (
        ("range", "RANGE", 1, 0),
        ("q", "Q", 2, 1),
        ("volume", "VOLUME", 3, 2),
        ("position", "POSITION", 4, 3),
    )
)


RACK_WAH_PARAMETER_SEEDS: tuple[dict[str, Any], ...] = (
    *(
        {
            "key": key,
            "name": name,
            "display_order": order,
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
                "internal_slots_observed": [1],
                "effect_identity_source": "current_chain",
                "parameter_selector": selector,
                "multiple_parameters": True,
                "saved_dump_default": 50,
                "physical_combined_capture": True,
                "evidence": "docs/phases/WAH_RACK_WAH_EQ_PARAMETERS_PHASE44.md",
                "monitor_integration_physical_validation": "pending",
            },
        }
        for key, name, order, selector in (
            ("range", "RANGE", 1, 0),
            ("q", "Q", 2, 1),
            ("volume", "VOLUME", 3, 2),
            ("position", "POSITION", 4, 3),
        )
    ),
    {
        "key": "eq",
        "name": "EQ",
        "display_order": 5,
        "value_type": "boolean",
        "range": {"minimum": 0, "maximum": 1, "step": 1},
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
            "internal_slots_observed": [1],
            "effect_identity_source": "current_chain",
            "parameter_selector": 4,
            "multiple_parameters": True,
            "saved_dump_default": 1,
            "boolean_encoding": {"false": 0, "true": 1},
            "physical_combined_capture": True,
            "evidence": "docs/phases/WAH_RACK_WAH_EQ_PARAMETERS_PHASE44.md",
            "monitor_integration_physical_validation": "pending",
        },
    },
)


BASS_WAH_PARAMETER_SEEDS: tuple[dict[str, Any], ...] = tuple(
    {
        "key": key,
        "name": name,
        "display_order": order,
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
            "effect_identity_source": "current_chain",
            "parameter_selector": selector,
            "saved_dump_default": 50,
            "inference_sources": ["wah.voks_wah", "wah.cry_wah", "wah.rack_wah"],
            "evidence": "docs/phases/WAH_BASS_WAH_INFERRED_PARAMETERS_PHASE45.md",
            "monitor_integration_physical_validation": "approved",
            "physical_validation_without_pcapng": True,
        },
    }
    for key, name, order, selector in (
        ("range", "RANGE", 1, 0),
        ("q", "Q", 2, 1),
        ("volume", "VOLUME", 3, 2),
        ("position", "POSITION", 4, 3),
    )
)


TOUCH_WAH_PARAMETER_SEEDS: tuple[dict[str, Any], ...] = (
    *(
        {
            "key": key,
            "name": name,
            "display_order": order,
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
                "internal_slots_observed": [1],
                "effect_identity_source": "current_chain",
                "parameter_selector": selector,
                "saved_dump_default": 50,
                "physical_combined_capture": True,
                "evidence": "docs/phases/WAH_TOUCH_WAH_MODE_PARAMETERS_PHASE46.md",
                "monitor_integration_physical_validation": "approved",
            },
        }
        for key, name, order, selector in (
            ("sense", "SENSE", 1, 0),
            ("range", "RANGE", 2, 1),
            ("q", "Q", 3, 2),
            ("mix", "MIX", 4, 3),
        )
    ),
    {
        "key": "mode",
        "name": "MODE",
        "display_order": 5,
        "value_type": "enum",
        "range": {"minimum": 0, "maximum": 1, "step": 1},
        "choices": [
            {"value": 0, "label": "GUITAR"},
            {"value": 1, "label": "BASS"},
        ],
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
            "internal_slots_observed": [1],
            "effect_identity_source": "current_chain",
            "parameter_selector": 4,
            "saved_dump_default": 0,
            "physical_combined_capture": True,
            "evidence": "docs/phases/WAH_TOUCH_WAH_MODE_PARAMETERS_PHASE46.md",
            "monitor_integration_physical_validation": "approved",
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
    elif effect_key == "freq.pitch_s" and not parameters:
        parameters = list(PITCH_S_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "freq.ring_mod" and not parameters:
        parameters = list(RING_MOD_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "freq.tape_mod" and not parameters:
        parameters = list(TAPE_MOD_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "wah.voks_wah" and not parameters:
        parameters = list(VOKS_WAH_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "wah.cry_wah" and not parameters:
        parameters = list(CRY_WAH_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "wah.rack_wah" and not parameters:
        parameters = list(RACK_WAH_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "wah.bass_wah" and not parameters:
        parameters = list(BASS_WAH_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "wah.touch_wah":
        parameters = list(TOUCH_WAH_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "wah.auto_wah":
        parameters = list(AUTO_WAH_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "drv.skreamer":
        parameters = list(SKREAMER_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "drv.skreamer9":
        parameters = list(SKREAMER9_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "drv.butter_od":
        parameters = list(BUTTER_OD_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "drv.warm_od":
        parameters = list(WARM_OD_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "drv.super_od":
        parameters = list(SUPER_OD_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "drv.blues_od":
        parameters = list(BLUES_OD_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "drv.full_od":
        parameters = list(FULL_OD_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "drv.breaker_od":
        parameters = list(BREAKER_OD_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "drv.gerden_od":
        parameters = list(GERDEN_OD_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "drv.timmy_od":
        parameters = list(TIMMY_OD_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "drv.master_od":
        parameters = list(MASTER_OD_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "drv.solar_fuzz":
        parameters = list(SOLAR_FUZZ_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "drv.fuzz_cream":
        parameters = list(FUZZ_CREAM_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "drv.red_fuzz":
        parameters = list(RED_FUZZ_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "drv.jp_dist":
        parameters = list(JP_DIST_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "drv.dark_mouse":
        parameters = list(DARK_MOUSE_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "drv.plexi_dist":
        parameters = list(PLEXI_DIST_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "drv.master_dist":
        parameters = list(MASTER_DIST_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "drv.dist_plus":
        parameters = list(DIST_PLUS_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "drv.shark":
        parameters = list(SHARK_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "drv.strive":
        parameters = list(STRIVE_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "drv.sardar_dist":
        parameters = list(SARDAR_DIST_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "drv.bass_od":
        parameters = list(BASS_OD_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "drv.bass_dist":
        parameters = list(BASS_DIST_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.twd_deluxe":
        parameters = list(TWD_DELUXE_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.b_man_n":
        parameters = list(B_MAN_N_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.b_man_bri":
        parameters = list(B_MAN_BRI_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.dark_double":
        parameters = list(DARK_DOUBLE_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.dark_deluxe":
        parameters = list(DARK_DELUXE_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.supero_2_cl":
        parameters = list(SUPERO_2_CL_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.supero_2_od":
        parameters = list(SUPERO_2_OD_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.voks_15tb":
        parameters = list(VOKS_15TB_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.voks_30n":
        parameters = list(VOKS_30N_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.voks_30tb":
        parameters = list(VOKS_30TB_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.jazz_120":
        parameters = list(JAZZ_120_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.superb_cl":
        parameters = list(SUPERB_CL_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.superb_od":
        parameters = list(SUPERB_OD_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.calif_star_cl":
        parameters = list(CALIF_STAR_CL_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.calif_star_od":
        parameters = list(CALIF_STAR_OD_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.bog_sv_cl":
        parameters = list(BOG_SV_CL_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.bog_sv_od":
        parameters = list(BOG_SV_OD_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.bog_xt_blue":
        parameters = list(BOG_XT_BLUE_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.bog_xt_red":
        parameters = list(BOG_XT_RED_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.doctor_cl":
        parameters = list(DOCTOR_CL_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.doctor_od":
        parameters = list(DOCTOR_OD_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.dragon_cl":
        parameters = list(DRAGON_CL_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.dragon_cl_b":
        parameters = list(DRAGON_CL_B_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.dragon_od":
        parameters = list(DRAGON_OD_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.sol_100_cl":
        parameters = list(SOL_100_CL_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.sol_100_od":
        parameters = list(SOL_100_OD_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"

    elif effect_key == "amp.sol_100_ld":
        parameters = list(SOL_100_LD_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.brit_45":
        parameters = list(BRIT_45_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.brit_45_plus":
        parameters = list(BRIT_45_PLUS_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.brit_45jp":
        parameters = list(BRIT_45JP_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.brit_50":
        parameters = list(BRIT_50_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.brit_50_plus":
        parameters = list(BRIT_50_PLUS_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.brit_50jp":
        parameters = list(BRIT_50JP_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.brit_slp":
        parameters = list(BRIT_SLP_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.brit_800":
        parameters = list(BRIT_800_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.brit_900":
        parameters = list(BRIT_900_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.flyman_1":
        parameters = list(FLYMAN_1_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.flyman_2":
        parameters = list(FLYMAN_2_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.flyman_plus_1":
        parameters = list(FLYMAN_PLUS_1_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.flyman_plus_2":
        parameters = list(FLYMAN_PLUS_2_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.calif_iic_plus_1":
        parameters = list(CALIF_IIC_PLUS_1_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.calif_iic_plus_2":
        parameters = list(CALIF_IIC_PLUS_2_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.calif_iic_plus_3":
        parameters = list(CALIF_IIC_PLUS_3_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.calif_iv_ld_1":
        parameters = list(CALIF_IV_LD_1_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.calif_iv_ld_2":
        parameters = list(CALIF_IV_LD_2_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.calif_iv_ld_3":
        parameters = list(CALIF_IV_LD_3_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.calif_dual_v":
        parameters = list(CALIF_DUAL_V_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.calif_dual_m":
        parameters = list(CALIF_DUAL_M_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.tanger_r100":
        parameters = list(TANGER_R100_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.halen_51":
        parameters = list(HALEN_51_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.eng_120":
        parameters = list(ENG_120_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.eng_120_plus":
        parameters = list(ENG_120_PLUS_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.dizzy_vh":
        parameters = list(DIZZY_VH_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.dizzy_vh_s":
        parameters = list(DIZZY_VH_S_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.dizzy_vh_plus":
        parameters = list(DIZZY_VH_PLUS_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.dizzy_vh_plus_s":
        parameters = list(DIZZY_VH_PLUS_S_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.a_bassvt":
        parameters = list(A_BASSVT_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.voks_bass":
        parameters = list(VOKS_BASS_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.cali_bass":
        parameters = list(CALI_BASS_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.a_bassft":
        parameters = list(A_BASSFT_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.f_2bass":
        parameters = list(F_2BASS_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.ac_preamp":
        parameters = list(AC_PREAMP_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "amp.ac_preamp_2":
        parameters = list(AC_PREAMP_2_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "cab.supero_1x6":
        parameters = list(SUPERO_1X6_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key == "cab.double_bass":
        parameters = list(DOUBLE_BASS_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key.startswith("cab.") and not parameters:
        parameters = list(CAB_SHARED_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key.startswith("ir."):
        parameters = list(IR_SHARED_PARAMETER_SEEDS)
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key in EQ_PARAMETER_SEEDS:
        parameters = list(EQ_PARAMETER_SEEDS[effect_key])
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key in MOD_PHASE74_FAMILY_PARAMETER_SEEDS:
        parameters = list(MOD_PHASE74_FAMILY_PARAMETER_SEEDS[effect_key])
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key in MOD_PHASE75_FLANGER_FAMILY_PARAMETER_SEEDS:
        parameters = list(MOD_PHASE75_FLANGER_FAMILY_PARAMETER_SEEDS[effect_key])
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key in MOD_PHASE76_DUAL_SYNC_PARAMETER_SEEDS:
        parameters = list(MOD_PHASE76_DUAL_SYNC_PARAMETER_SEEDS[effect_key])
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key in MOD_PHASE77_ENUM_BIAS_PARAMETER_SEEDS:
        parameters = list(MOD_PHASE77_ENUM_BIAS_PARAMETER_SEEDS[effect_key])
        capabilities = ["parameters"]
        status = "physically_validated"
    elif effect_key in MOD_PHASE78_FINAL_FOUR_PARAMETER_SEEDS:
        parameters = list(MOD_PHASE78_FINAL_FOUR_PARAMETER_SEEDS[effect_key])
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
