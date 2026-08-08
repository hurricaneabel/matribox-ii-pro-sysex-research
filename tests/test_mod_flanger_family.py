"""Regressões finais da família FLANGER MOD (Fase 75)."""

from __future__ import annotations

import json
from pathlib import Path
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


ALL = {"mod.flanger", "mod.flanger_n", "mod.bass_jet"}
EXPECTED_KEYS = ("depth", "rate", "pre_delay", "feedback", "sync")
EXPECTED_SELECTORS = (0, 1, 2, 3, 4)


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
    import struct

    raw = struct.pack("<f", float(value))
    nibbles: list[int] = []
    for byte in raw:
        nibbles.extend((byte >> 4, byte & 0x0F))
    template[55:63] = bytes(nibbles)
    return bytes(template)


class ModFlangerFamilyPhase75Tests(unittest.TestCase):
    def test_three_models_have_physically_validated_shared_schema_and_global_counts(self) -> None:
        catalog = load_effect_catalog()
        mod = catalog.class_by_key("mod")
        candidates = {effect.key: effect for effect in mod.models if effect.key in ALL}
        self.assertEqual(set(candidates), ALL)
        self.assertEqual(sum(len(effect.parameters) for effect in candidates.values()), 15)

        for key, effect in candidates.items():
            with self.subTest(effect=key):
                self.assertEqual(effect.parameter_catalog_status, "physically_validated")
                self.assertEqual(tuple(parameter.key for parameter in effect.parameters), EXPECTED_KEYS)
                self.assertEqual(
                    tuple(parameter.message_match["parameter_selector"] for parameter in effect.parameters),
                    EXPECTED_SELECTORS,
                )
                self.assertEqual(
                    tuple(parameter.validation["saved_dump_default"] for parameter in effect.parameters if parameter.key != "rate"),
                    (50, 50, 50, 0),
                )
                for parameter in effect.parameters:
                    self.assertTrue(parameter.validation["physical"])
                    self.assertEqual(parameter.validation["monitor_integration_physical_validation"], "approved")
                    self.assertFalse(parameter.validation["candidate_requires_live_validation"])

                rate = effect.parameters[1]
                self.assertEqual(rate.value_codec, "float32_nibbles_v1")
                self.assertEqual(rate.validation["range_validated"], [0.1, 10.0])
                self.assertTrue(rate.value_domain["reset_on_controller_change"])
                self.assertEqual(rate.value_domain["states"][0]["default_value"], 0.5)
                self.assertEqual(rate.value_domain["states"][1]["default_value"], 4)

        statuses: dict[str, int] = {}
        parameter_count = 0
        for effect_class in catalog.classes:
            for effect in effect_class.models:
                statuses[effect.parameter_catalog_status] = statuses.get(effect.parameter_catalog_status, 0) + 1
                parameter_count += len(effect.parameters)
        self.assertEqual(catalog.catalog_version, 59)
        self.assertEqual(statuses, {"physically_validated": 224, "pending": 43})
        self.assertEqual(parameter_count, 922)

    def test_live_monitor_mapping_and_sync_domain_work_for_each_candidate(self) -> None:
        values = ((0, 77), (1, 3.7), (2, 23), (3, 81))
        for effect_key in sorted(ALL):
            with self.subTest(effect=effect_key):
                chain = make_chain(effect_key)
                state = EffectParameterState()
                for selector, value in values:
                    event = parse_effect_parameter_response(
                        make_parameter_message(selector, value), effect_key=effect_key
                    )
                    self.assertIsNotNone(event)
                    state.apply(event)

                snapshot = build_effect_snapshots(chain, state)[0]
                self.assertEqual(
                    tuple(parameter.display_value for parameter in snapshot.parameters),
                    ("77", "3.7 Hz", "23", "81", "aguardando alteração"),
                )

                sync_on = parse_effect_parameter_response(
                    make_parameter_message(4, 1), effect_key=effect_key
                )
                self.assertIsNotNone(sync_on)
                state.apply(sync_on)
                snapshot = build_effect_snapshots(chain, state)[0]
                self.assertEqual(snapshot.parameters[1].display_value, "1/4")
                self.assertEqual(snapshot.parameters[4].display_value, "ligado")

                rate_8 = parse_effect_parameter_response(
                    make_parameter_message(1, 8), effect_key=effect_key
                )
                self.assertIsNotNone(rate_8)
                state.apply(rate_8)
                self.assertEqual(build_effect_snapshots(chain, state)[0].parameters[1].display_value, "1/8d")

                sync_off = parse_effect_parameter_response(
                    make_parameter_message(4, 0), effect_key=effect_key
                )
                self.assertIsNotNone(sync_off)
                state.apply(sync_off)
                self.assertEqual(build_effect_snapshots(chain, state)[0].parameters[1].display_value, "0.5 Hz")

    def test_exporter_reproduces_three_physically_validated_jsons(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            export_root = Path(temporary_directory) / "catalog"
            export_catalog(EFFECT_CLASSES, export_root)
            self.assertEqual(json.loads((export_root / "catalog.json").read_text(encoding="utf-8"))["catalog_version"], 59)
            for key in sorted(ALL):
                current_effect = CATALOG.effect_by_key(key)
                source = Path("catalog/effects/mod") / f"{current_effect.menu_number:03d}_{key.split('.', 1)[1]}.json"
                exported_path = export_root / "effects" / "mod" / source.name
                exported = json.loads(exported_path.read_text(encoding="utf-8"))
                current = json.loads(source.read_text(encoding="utf-8"))
                self.assertEqual(exported["parameters"], current["parameters"])
                self.assertEqual(exported["parameter_catalog_status"], "physically_validated")
                self.assertEqual(exported["parameter_catalog_status"], current["parameter_catalog_status"])


if __name__ == "__main__":
    unittest.main()
