"""Regressões da abertura dos parâmetros da classe IR (Fase 72)."""

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


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "ir_parameters"


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
                auxiliary_2=0x10,
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


class IrPhase72Tests(unittest.TestCase):
    def test_all_twenty_irs_use_the_shared_physically_validated_schema(self) -> None:
        catalog = load_effect_catalog()
        ir = catalog.class_by_key("ir")
        self.assertEqual(len(ir.models), 20)
        self.assertTrue(all(effect.parameters for effect in ir.models))
        self.assertTrue(
            all(effect.parameter_catalog_status == "physically_validated" for effect in ir.models)
        )
        self.assertEqual(
            [effect.key for effect in ir.models if effect.parameters[0].validation["physical"]],
            [effect.key for effect in ir.models],
        )
        for effect in ir.models:
            with self.subTest(effect=effect.key):
                self.assertEqual(
                    tuple(parameter.key for parameter in effect.parameters),
                    ("volume", "low_cut", "high_cut"),
                )
                self.assertEqual(
                    tuple(parameter.message_match["parameter_selector"] for parameter in effect.parameters),
                    (1, 5, 6),
                )
                self.assertTrue(
                    all(parameter.value_codec == "float32_nibbles_v1" for parameter in effect.parameters)
                )
                self.assertEqual(effect.parameters[1].display["sentinels"][0]["value"], 19)
                self.assertEqual(effect.parameters[2].display["sentinels"][0]["value"], 20001)
                self.assertEqual(
                    effect.parameters[0].validation["monitor_integration_physical_validation"],
                    "approved",
                )
                self.assertEqual(
                    effect.parameters[0].validation["monitor_validation_result"],
                    "all_20_models_parameter_values_exact_to_device",
                )

        with tempfile.TemporaryDirectory() as temporary_directory:
            export_root = Path(temporary_directory) / "catalog"
            export_catalog(EFFECT_CLASSES, export_root)
            for filename in ("001_ir_1.json", "010_ir_10.json", "020_ir_20.json"):
                exported = json.loads(
                    (export_root / "effects" / "ir" / filename).read_text(encoding="utf-8")
                )
                current = json.loads(
                    (Path("catalog") / "effects" / "ir" / filename).read_text(encoding="utf-8")
                )
                self.assertEqual(exported["parameters"], current["parameters"])
                self.assertEqual(
                    exported["parameter_catalog_status"], current["parameter_catalog_status"]
                )

    def test_physical_ir_frames_preserve_full_float32_and_off_sentinels(self) -> None:
        manifest = json.loads((FIXTURE_ROOT / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["result"], "ir1_ir20_confirm_shared_cab_style_float32_schema")
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

    def test_saved_dump_hydrates_ir1_and_ir20_values_and_off_labels(self) -> None:
        chain = make_chain((0, "ir.ir_1"), (1, "ir.ir_20"))
        custom = decode_saved_parameter_events(
            make_dump({
                (0, 1): 37,
                (0, 5): 637,
                (0, 6): 15371,
                (1, 1): 28,
                (1, 5): 953,
                (1, 6): 13267,
            }),
            chain,
        )
        state = EffectParameterState()
        for event in custom:
            state.apply(event, origin="saved_preset_dump")
        snapshots = build_effect_snapshots(chain, state)
        self.assertEqual(
            tuple(parameter.display_value for parameter in snapshots[0].parameters),
            ("37", "637 Hz", "15371 Hz"),
        )
        self.assertEqual(
            tuple(parameter.display_value for parameter in snapshots[1].parameters),
            ("28", "953 Hz", "13267 Hz"),
        )

        off_chain = make_chain((0, "ir.ir_1"))
        off_events = decode_saved_parameter_events(
            make_dump({(0, 1): 50, (0, 5): 19, (0, 6): 20001}),
            off_chain,
        )
        off_state = EffectParameterState()
        for event in off_events:
            off_state.apply(event, origin="saved_preset_dump")
        off_snapshot = build_effect_snapshots(off_chain, off_state)[0]
        self.assertEqual(
            tuple(parameter.display_value for parameter in off_snapshot.parameters),
            ("50", "OFF", "OFF"),
        )


if __name__ == "__main__":
    unittest.main()
