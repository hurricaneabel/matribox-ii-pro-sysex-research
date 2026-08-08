"""Regressões finais da família MOD com dois RATE/SYNC (Fase 76)."""

from __future__ import annotations

import json
from pathlib import Path
import struct
import tempfile
import unittest

from tools.commands.chain_order import ChainOrderState
from tools.commands.effect_catalog import CATALOG, EFFECT_CLASSES
from tools.commands.preset_monitor_core import build_effect_snapshots
from tools.commands.structural_effect_state import StructuralEffectRecord
from tools.migrations.export_effect_catalog_to_json import export_catalog
from tools.parameters import parse_effect_parameter_response
from tools.parameters.state import EffectParameterState


EXPECTED = {
    "mod.trem_jet": (
        ("flg_depth", 0),
        ("flg_rate", 1),
        ("feedback", 2),
        ("trm_depth", 3),
        ("trm_rate", 4),
        ("flg_sync", 5),
        ("trm_sync", 6),
    ),
    "mod.pan_phaser": (
        ("phs_depth", 0),
        ("phs_rate", 1),
        ("pan_depth", 2),
        ("pan_rate", 3),
        ("phs_sync", 4),
        ("pan_sync", 5),
    ),
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


class ModDualSyncFamilyTests(unittest.TestCase):
    def test_final_schema_and_defaults(self) -> None:
        for effect_key, expected in EXPECTED.items():
            with self.subTest(effect=effect_key):
                effect = CATALOG.effect_by_key(effect_key)
                self.assertEqual(effect.parameter_catalog_status, "physically_validated")
                self.assertEqual(
                    tuple((p.key, p.message_match["parameter_selector"]) for p in effect.parameters),
                    expected,
                )
                for parameter in effect.parameters:
                    self.assertTrue(parameter.validation["physical"])
                    self.assertEqual(parameter.validation["monitor_integration_physical_validation"], "approved")
                    self.assertEqual(parameter.value_codec, "float32_nibbles_v1")

    def test_each_sync_resets_only_its_own_rate(self) -> None:
        cases = {
            "mod.trem_jet": {
                "rates": ((1, "flg_rate"), (4, "trm_rate")),
                "syncs": ((5, "flg_sync", "flg_rate"), (6, "trm_sync", "trm_rate")),
            },
            "mod.pan_phaser": {
                "rates": ((1, "phs_rate"), (3, "pan_rate")),
                "syncs": ((4, "phs_sync", "phs_rate"), (5, "pan_sync", "pan_rate")),
            },
        }
        for effect_key, case in cases.items():
            with self.subTest(effect=effect_key):
                state = EffectParameterState(CATALOG)
                chain = make_chain(effect_key)
                for selector, _key in case["rates"]:
                    event = parse_effect_parameter_response(make_parameter_message(selector, 3.7), effect_key=effect_key)
                    self.assertIsNotNone(event)
                    state.apply(event)
                snap = build_effect_snapshots(chain, state)[0]
                by_key = {p.key: p.display_value for p in snap.parameters}
                for _selector, key in case["rates"]:
                    self.assertEqual(by_key[key], "3.7 Hz")

                first_sync_selector, first_sync_key, first_rate_key = case["syncs"][0]
                event = parse_effect_parameter_response(make_parameter_message(first_sync_selector, 1), effect_key=effect_key)
                self.assertIsNotNone(event)
                state.apply(event)
                snap = build_effect_snapshots(chain, state)[0]
                by_key = {p.key: p.display_value for p in snap.parameters}
                self.assertEqual(by_key[first_sync_key], "ligado")
                self.assertEqual(by_key[first_rate_key], "1/4")
                other_rate_key = case["rates"][1][1]
                self.assertEqual(by_key[other_rate_key], "3.7 Hz")

                second_sync_selector, second_sync_key, second_rate_key = case["syncs"][1]
                event = parse_effect_parameter_response(make_parameter_message(second_sync_selector, 1), effect_key=effect_key)
                self.assertIsNotNone(event)
                state.apply(event)
                snap = build_effect_snapshots(chain, state)[0]
                by_key = {p.key: p.display_value for p in snap.parameters}
                self.assertEqual(by_key[second_sync_key], "ligado")
                self.assertEqual(by_key[second_rate_key], "1/4")

    def test_exporter_reproduces_final_dual_sync_and_phase75_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            export_root = Path(temporary_directory) / "catalog"
            export_catalog(EFFECT_CLASSES, export_root)
            top = json.loads((export_root / "catalog.json").read_text(encoding="utf-8"))
            self.assertEqual(top["catalog_version"], 59)
            for key in EXPECTED:
                effect = CATALOG.effect_by_key(key)
                name = f"{effect.menu_number:03d}_{key.split('.', 1)[1]}.json"
                exported = json.loads((export_root / "effects/mod" / name).read_text(encoding="utf-8"))
                current = json.loads((Path("catalog/effects/mod") / name).read_text(encoding="utf-8"))
                self.assertEqual(exported["parameters"], current["parameters"])
                self.assertEqual(exported["parameter_catalog_status"], "physically_validated")
                self.assertTrue(all(p["validation"]["physical"] for p in exported["parameters"]))
            for key in ("mod.flanger", "mod.flanger_n", "mod.bass_jet"):
                effect = CATALOG.effect_by_key(key)
                name = f"{effect.menu_number:03d}_{key.split('.', 1)[1]}.json"
                exported = json.loads((export_root / "effects/mod" / name).read_text(encoding="utf-8"))
                self.assertEqual(exported["parameter_catalog_status"], "physically_validated")
                self.assertTrue(all(p["validation"]["physical"] for p in exported["parameters"]))


if __name__ == "__main__":
    unittest.main()
