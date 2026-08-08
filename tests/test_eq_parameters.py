"""Regressões finais dos parâmetros da classe EQ (Fase 73)."""

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
from tools.parameters.preset_dump import (
    PRESET_PARAMETER_BLOCK_END,
    PRESET_PARAMETER_BLOCK_OFFSET,
    PRESET_PARAMETER_SLOT_SIZE,
    decode_saved_parameter_events,
)
from tools.parameters.state import EffectParameterState


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "eq_parameters"


EXPECTED = {
    "eq.guitar_eq_1": (
        ("band_125_hz", "125 Hz"),
        ("band_400_hz", "400 Hz"),
        ("band_800_hz", "800 Hz"),
        ("band_1_6_khz", "1.6 kHz"),
        ("band_4_khz", "4 kHz"),
    ),
    "eq.guitar_eq_2": (
        ("band_100_hz", "100 Hz"),
        ("band_500_hz", "500 Hz"),
        ("band_1_khz", "1 kHz"),
        ("band_3_khz", "3 kHz"),
        ("band_6_khz", "6 kHz"),
    ),
    "eq.bass_eq_1": (
        ("band_33_hz", "33 Hz"),
        ("band_150_hz", "150 Hz"),
        ("band_600_hz", "600 Hz"),
        ("band_2_khz", "2 kHz"),
        ("band_8_khz", "8 kHz"),
    ),
    "eq.bass_eq_2": (
        ("band_50_hz", "50 Hz"),
        ("band_120_hz", "120 Hz"),
        ("band_400_hz", "400 Hz"),
        ("band_800_hz", "800 Hz"),
        ("band_4_5_khz", "4.5 kHz"),
    ),
    "eq.calif_eq": (
        ("band_80_hz", "80 Hz"),
        ("band_240_hz", "240 Hz"),
        ("band_750_hz", "750 Hz"),
        ("band_2_2_khz", "2.2 kHz"),
        ("band_6_6_khz", "6.6 kHz"),
    ),
}


def make_chain(*effects: tuple[int, str]) -> ChainOrderState:
    active = {slot: key for slot, key in effects}
    records = []
    enabled = [None] * 12
    for slot_id in range(12):
        effect_key = active.get(slot_id)
        if effect_key is None:
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
            continue
        effect = CATALOG.effect_by_key(effect_key)
        effect_class = CATALOG.class_by_key(effect.class_key)
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
    return ChainOrderState(
        internal_slot_ids=tuple(slot for slot, _ in effects),
        observed_checksum=0,
        declared_length_units=0,
        raw_message=b"",
        enabled_by_internal_slot=tuple(enabled),
        effect_records_by_internal_slot=tuple(records),
    )


def make_dump(values: dict[tuple[int, int], float]) -> bytes:
    payload = bytearray(PRESET_PARAMETER_BLOCK_END)
    for (slot_id, selector), value in values.items():
        offset = PRESET_PARAMETER_BLOCK_OFFSET + slot_id * PRESET_PARAMETER_SLOT_SIZE + selector * 4
        payload[offset:offset + 4] = struct.pack("<f", value)
    return bytes(payload)


class EqPhase73Tests(unittest.TestCase):
    def test_all_five_eqs_are_physically_validated_with_expected_schema_defaults_and_ranges(self) -> None:
        catalog = load_effect_catalog()
        eq = catalog.class_by_key("eq")
        self.assertEqual(len(eq.models), 5)
        self.assertTrue(all(effect.parameter_catalog_status == "physically_validated" for effect in eq.models))

        for effect in eq.models:
            with self.subTest(effect=effect.key):
                bands = EXPECTED[effect.key]
                include_volume = effect.key != "eq.calif_eq"
                expected_keys = tuple(key for key, _ in bands) + (("volume",) if include_volume else ())
                expected_names = tuple(name for _, name in bands) + (("VOLUME",) if include_volume else ())
                self.assertEqual(tuple(parameter.key for parameter in effect.parameters), expected_keys)
                self.assertEqual(tuple(parameter.name for parameter in effect.parameters), expected_names)
                self.assertEqual(
                    tuple(parameter.message_match["parameter_selector"] for parameter in effect.parameters),
                    tuple(range(6 if include_volume else 5)),
                )
                for parameter in effect.parameters[:5]:
                    self.assertEqual((parameter.minimum, parameter.maximum, parameter.step), (-50, 50, 1))
                    self.assertEqual(parameter.validation["saved_dump_default"], 0)
                    self.assertEqual(parameter.value_codec, "float32_nibbles_v1")
                    self.assertTrue(parameter.validation["physical"])
                    self.assertEqual(parameter.validation["monitor_integration_physical_validation"], "approved")
                    self.assertEqual(parameter.validation["monitor_validation_source"], "user_live_monitor_all_eqs_phase73_with_log")
                if include_volume:
                    volume = effect.parameters[5]
                    self.assertEqual((volume.minimum, volume.maximum, volume.step), (0, 100, 1))
                    self.assertEqual(volume.validation["saved_dump_default"], 50)
                    self.assertTrue(volume.validation["physical"])
                    self.assertEqual(volume.validation["monitor_integration_physical_validation"], "approved")
                else:
                    self.assertNotIn("volume", tuple(parameter.key for parameter in effect.parameters))

        with tempfile.TemporaryDirectory() as temporary_directory:
            export_root = Path(temporary_directory) / "catalog"
            export_catalog(EFFECT_CLASSES, export_root)
            for filename in (
                "001_guitar_eq_1.json",
                "002_guitar_eq_2.json",
                "003_bass_eq_1.json",
                "004_bass_eq_2.json",
                "005_calif_eq.json",
            ):
                exported = json.loads((export_root / "effects" / "eq" / filename).read_text(encoding="utf-8"))
                current = json.loads((Path("catalog") / "effects" / "eq" / filename).read_text(encoding="utf-8"))
                self.assertEqual(exported, current)

    def test_physical_anchor_frames_decode_negative_positive_and_volume_values(self) -> None:
        manifest = json.loads((FIXTURE_ROOT / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["result"], "guitar_eq_1_and_calif_eq_confirm_float32_selector_schemas")
        self.assertEqual(len(manifest["fixtures"]), 11)
        for item in manifest["fixtures"]:
            with self.subTest(file=item["file"]):
                event = parse_effect_parameter_response(
                    (FIXTURE_ROOT / item["file"]).read_bytes(),
                    effect_key=item["effect"],
                )
                self.assertIsNotNone(event)
                assert event is not None
                self.assertEqual(event.parameter_key, item["parameter"])
                self.assertEqual(event.value, item["value"])
                self.assertEqual(event.value_codec, "float32_nibbles_v1")
                self.assertEqual(len(event.encoded_value), 8)

    def test_saved_dump_hydrates_guitar_eq1_and_ignores_calif_selector5_residue(self) -> None:
        chain = make_chain((0, "eq.guitar_eq_1"), (1, "eq.calif_eq"))
        events = decode_saved_parameter_events(
            make_dump({
                (0, 0): -37,
                (0, 1): -19,
                (0, 2): 7,
                (0, 3): 26,
                (0, 4): 43,
                (0, 5): 73,
                (1, 0): 0,
                (1, 1): 0,
                (1, 2): 0,
                (1, 3): 0,
                (1, 4): 0,
                (1, 5): 50,
            }),
            chain,
        )
        state = EffectParameterState()
        for event in events:
            state.apply(event, origin="saved_preset_dump")
        snapshots = build_effect_snapshots(chain, state)
        self.assertEqual(
            tuple(parameter.display_value for parameter in snapshots[0].parameters),
            ("-37", "-19", "7", "26", "43", "73"),
        )
        self.assertEqual(
            tuple(parameter.display_value for parameter in snapshots[1].parameters),
            ("0", "0", "0", "0", "0"),
        )
        self.assertEqual(tuple(parameter.key for parameter in snapshots[1].parameters), tuple(key for key, _ in EXPECTED["eq.calif_eq"]))


if __name__ == "__main__":
    unittest.main()
