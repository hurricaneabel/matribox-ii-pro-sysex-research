"""Regressões da classe CAB após a expansão do schema compartilhado (Fase 71)."""

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


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "cab_parameters"


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
        offset = (
            PRESET_PARAMETER_BLOCK_OFFSET
            + slot_id * PRESET_PARAMETER_SLOT_SIZE
            + selector * 4
        )
        payload[offset:offset + 4] = struct.pack("<f", value)
    return bytes(payload)


class CabPhase71Tests(unittest.TestCase):
    def test_all_61_cabs_share_parameter_schema_and_are_physically_validated(self) -> None:
        catalog = load_effect_catalog()
        cab = catalog.class_by_key("cab")
        self.assertEqual(len(cab.models), 61)
        self.assertTrue(all(effect.parameters for effect in cab.models))

        physically_validated = [effect.key for effect in cab.models if effect.parameter_catalog_status == "physically_validated"]
        partially_cataloged = [effect.key for effect in cab.models if effect.parameter_catalog_status == "partially_cataloged"]
        self.assertEqual(len(physically_validated), 61)
        self.assertEqual(partially_cataloged, [])

        for effect in cab.models:
            with self.subTest(effect=effect.key):
                self.assertEqual(effect.capabilities, ("parameters",))
                self.assertEqual(
                    tuple(parameter.key for parameter in effect.parameters),
                    ("volume", "low_cut", "high_cut"),
                )
                self.assertEqual(
                    tuple(parameter.message_match["parameter_selector"] for parameter in effect.parameters),
                    (1, 5, 6),
                )
                self.assertTrue(all(parameter.value_codec == "float32_nibbles_v1" for parameter in effect.parameters))
                self.assertEqual(effect.parameters[0].minimum, 0)
                self.assertEqual(effect.parameters[0].maximum, 100)
                self.assertEqual(effect.parameters[1].display["sentinels"][0]["value"], 19)
                self.assertEqual(effect.parameters[2].display["sentinels"][0]["value"], 20001)

        with tempfile.TemporaryDirectory() as temporary_directory:
            export_root = Path(temporary_directory) / "catalog"
            export_catalog(EFFECT_CLASSES, export_root)
            for filename in [
                "001_supero_1x6.json",
                "002_chap_1x8.json",
                "030_blue_2x12.json",
                "061_double_bass.json",
            ]:
                exported_document = json.loads((export_root / "effects" / "cab" / filename).read_text(encoding="utf-8"))
                current_document = json.loads((Path("catalog") / "effects" / "cab" / filename).read_text(encoding="utf-8"))
                self.assertEqual(exported_document["parameters"], current_document["parameters"])
                self.assertEqual(exported_document["parameter_catalog_status"], current_document["parameter_catalog_status"])

    def test_physical_cab_frames_preserve_full_float32_and_off_sentinels(self) -> None:
        manifest = json.loads((FIXTURE_ROOT / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["result"], "two_models_confirm_same_selectors_and_full_float32_codec")
        self.assertEqual(len(manifest["fixtures"]), 10)
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
                if item["value"] in (19, 20001):
                    self.assertEqual(event.display_value, "OFF")
                elif item["parameter"] in ("low_cut", "high_cut"):
                    self.assertEqual(event.display_value, f"{item['value']} Hz")

    def test_saved_dump_hydrates_custom_frequencies_and_off_labels(self) -> None:
        chain = make_chain((0, "cab.supero_1x6"), (1, "cab.double_bass"))
        custom = decode_saved_parameter_events(
            make_dump({
                (0, 1): 37,
                (0, 5): 630,
                (0, 6): 15500,
                (1, 1): 28,
                (1, 5): 956,
                (1, 6): 13262,
            }),
            chain,
        )
        state = EffectParameterState()
        for event in custom:
            state.apply(event, origin="saved_preset_dump")
        snapshots = build_effect_snapshots(chain, state)
        self.assertEqual(tuple(parameter.display_value for parameter in snapshots[0].parameters), ("37", "630 Hz", "15500 Hz"))
        self.assertEqual(tuple(parameter.display_value for parameter in snapshots[1].parameters), ("28", "956 Hz", "13262 Hz"))

        off_events = decode_saved_parameter_events(
            make_dump({(0, 1): 50, (0, 5): 19, (0, 6): 20001}),
            make_chain((0, "cab.supero_1x6")),
        )
        off_state = EffectParameterState()
        for event in off_events:
            off_state.apply(event, origin="saved_preset_dump")
        off_snapshot = build_effect_snapshots(make_chain((0, "cab.supero_1x6")), off_state)[0]
        self.assertEqual(tuple(parameter.display_value for parameter in off_snapshot.parameters), ("50", "OFF", "OFF"))

        inferred_events = decode_saved_parameter_events(
            make_dump({(0, 1): 83, (0, 5): 104, (0, 6): 17696}),
            make_chain((0, "cab.chap_1x8")),
        )
        inferred_state = EffectParameterState()
        for event in inferred_events:
            inferred_state.apply(event, origin="saved_preset_dump")
        inferred_snapshot = build_effect_snapshots(make_chain((0, "cab.chap_1x8")), inferred_state)[0]
        self.assertEqual(tuple(parameter.display_value for parameter in inferred_snapshot.parameters), ("83", "104 Hz", "17696 Hz"))


if __name__ == "__main__":
    unittest.main()
