"""Regressões finais da família MOD enum/bias (Fase 77)."""

from __future__ import annotations

import json
from pathlib import Path
import struct
import tempfile
import unittest

from tools.catalog import load_effect_catalog
from tools.commands.chain_order import ChainOrderState
from tools.commands.effect_catalog import CATALOG, EFFECT_CLASSES
from tools.commands.preset_monitor_core import build_effect_snapshots
from tools.commands.structural_effect_state import StructuralEffectRecord
from tools.migrations.export_effect_catalog_to_json import export_catalog
from tools.parameters import parse_effect_parameter_response
from tools.parameters.state import EffectParameterState


EXPECTED = {
    "mod.phaser_st": (("color", 0), ("rate", 1), ("sync", 2)),
    "mod.u_vibe": (("depth", 0), ("rate", 1), ("volume", 2), ("mode", 3), ("sync", 4)),
    "mod.bias_trem": (("depth", 0), ("rate", 1), ("volume", 2), ("sync", 3), ("bias", 4)),
}


def make_chain(effect_key: str) -> ChainOrderState:
    effect = CATALOG.effect_by_key(effect_key)
    effect_class = CATALOG.class_by_key(effect.class_key)
    records = []
    enabled = [None] * 12
    for slot_id in range(12):
        if slot_id == 0:
            enabled[slot_id] = True
            records.append(
                StructuralEffectRecord(
                    internal_slot_id=slot_id,
                    active=True,
                    class_id=effect_class.class_id,
                    model_id=effect.model_id,
                    auxiliary_1=0,
                    auxiliary_2=0,
                    secondary_selector=effect.secondary_selector,
                    enabled=True,
                )
            )
        else:
            records.append(
                StructuralEffectRecord(
                    internal_slot_id=slot_id,
                    active=False,
                    class_id=None,
                    model_id=None,
                    auxiliary_1=0,
                    auxiliary_2=0,
                    secondary_selector=None,
                    enabled=None,
                )
            )
    return ChainOrderState(
        internal_slot_ids=(0,),
        observed_checksum=0,
        declared_length_units=0,
        raw_message=b"",
        enabled_by_internal_slot=tuple(enabled),
        effect_records_by_internal_slot=tuple(records),
    )


def make_parameter_message(selector: int, value: float) -> bytes:
    template = bytearray(
        (Path("tests/fixtures/eq_parameters") / "guitar_eq1_volume_083.bin").read_bytes()
    )
    template[48] = selector
    raw = struct.pack("<f", float(value))
    nibbles: list[int] = []
    for byte in raw:
        nibbles.extend((byte >> 4, byte & 0x0F))
    template[55:63] = bytes(nibbles)
    return bytes(template)


class ModEnumBiasFamilyPhase77Tests(unittest.TestCase):
    def test_final_schemas_defaults_and_global_counts(self) -> None:
        catalog = load_effect_catalog()
        for effect_key, expected in EXPECTED.items():
            with self.subTest(effect=effect_key):
                effect = catalog.effect_by_key(effect_key)
                self.assertEqual(effect.parameter_catalog_status, "physically_validated")
                self.assertEqual(
                    tuple((p.key, p.message_match["parameter_selector"]) for p in effect.parameters),
                    expected,
                )
                for parameter in effect.parameters:
                    self.assertTrue(parameter.validation["physical"])
                    self.assertEqual(parameter.validation["monitor_integration_physical_validation"], "approved")
                    self.assertFalse(parameter.validation["candidate_requires_live_validation"])
                    self.assertEqual(parameter.value_codec, "float32_nibbles_v1")

        phaser = catalog.effect_by_key("mod.phaser_st")
        self.assertEqual(tuple(phaser.parameters[0].choices.values()), ("WARM", "SHARP"))
        self.assertEqual(phaser.parameters[0].validation["saved_dump_default"], 0)

        u_vibe = catalog.effect_by_key("mod.u_vibe")
        self.assertEqual(tuple(u_vibe.parameters[3].choices.values()), ("CHORUS", "VIBRATO"))
        self.assertEqual(u_vibe.parameters[3].validation["saved_dump_default"], 0)

        bias = catalog.effect_by_key("mod.bias_trem")
        self.assertEqual(bias.parameters[4].validation["saved_dump_default"], 50)
        self.assertEqual(bias.parameters[4].validation["range_validated"], [0, 100])

        statuses: dict[str, int] = {}
        parameter_count = 0
        for effect_class in catalog.classes:
            for effect in effect_class.models:
                statuses[effect.parameter_catalog_status] = statuses.get(effect.parameter_catalog_status, 0) + 1
                parameter_count += len(effect.parameters)
        self.assertEqual(catalog.catalog_version, 59)
        self.assertEqual(statuses, {"physically_validated": 224, "pending": 43})
        self.assertEqual(parameter_count, 922)

    def test_live_monitor_renders_validated_enums_and_sync_domain(self) -> None:
        cases = (
            ("mod.phaser_st", ((0, 1), (1, 3.7)), {"color": "SHARP", "rate": "3.7 Hz"}, 2),
            ("mod.u_vibe", ((0, 73), (1, 3.7), (2, 81), (3, 1)), {"depth": "73", "rate": "3.7 Hz", "volume": "81", "mode": "VIBRATO"}, 4),
            ("mod.bias_trem", ((0, 67), (1, 3.7), (2, 72), (4, 29)), {"depth": "67", "rate": "3.7 Hz", "volume": "72", "bias": "29"}, 3),
        )
        for effect_key, events, expected_values, sync_selector in cases:
            with self.subTest(effect=effect_key):
                state = EffectParameterState(CATALOG)
                chain = make_chain(effect_key)
                for selector, value in events:
                    event = parse_effect_parameter_response(make_parameter_message(selector, value), effect_key=effect_key)
                    self.assertIsNotNone(event)
                    state.apply(event)
                snapshot = build_effect_snapshots(chain, state)[0]
                by_key = {p.key: p.display_value for p in snapshot.parameters}
                for key, expected in expected_values.items():
                    self.assertEqual(by_key[key], expected)

                sync_on = parse_effect_parameter_response(make_parameter_message(sync_selector, 1), effect_key=effect_key)
                self.assertIsNotNone(sync_on)
                state.apply(sync_on)
                snapshot = build_effect_snapshots(chain, state)[0]
                by_key = {p.key: p.display_value for p in snapshot.parameters}
                self.assertEqual(by_key["sync"], "ligado")
                self.assertEqual(by_key["rate"], "1/4")

                rate_sync = parse_effect_parameter_response(make_parameter_message(1, 8), effect_key=effect_key)
                self.assertIsNotNone(rate_sync)
                state.apply(rate_sync)
                self.assertEqual(build_effect_snapshots(chain, state)[0].parameters[1].display_value, "1/8d")

                sync_off = parse_effect_parameter_response(make_parameter_message(sync_selector, 0), effect_key=effect_key)
                self.assertIsNotNone(sync_off)
                state.apply(sync_off)
                self.assertEqual(build_effect_snapshots(chain, state)[0].parameters[1].display_value, "0.5 Hz")

    def test_exporter_reproduces_three_final_jsons(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            export_root = Path(temporary_directory) / "catalog"
            export_catalog(EFFECT_CLASSES, export_root)
            self.assertEqual(json.loads((export_root / "catalog.json").read_text(encoding="utf-8"))["catalog_version"], 59)
            for key in EXPECTED:
                effect = CATALOG.effect_by_key(key)
                name = f"{effect.menu_number:03d}_{key.split('.', 1)[1]}.json"
                exported = json.loads((export_root / "effects/mod" / name).read_text(encoding="utf-8"))
                current = json.loads((Path("catalog/effects/mod") / name).read_text(encoding="utf-8"))
                self.assertEqual(exported["parameters"], current["parameters"])
                self.assertEqual(exported["parameter_catalog_status"], "physically_validated")
                self.assertTrue(all(p["validation"]["physical"] for p in exported["parameters"]))


if __name__ == "__main__":
    unittest.main()
