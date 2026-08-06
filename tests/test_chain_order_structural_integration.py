from __future__ import annotations

import json
from pathlib import Path
import unittest

from tools.commands.chain_order import (
    parse_chain_order_response,
)
from tools.commands.structural_effect_state import (
    DECOMPRESSED_PAYLOAD_SIZE,
)


FIXTURES_ROOT = (
    Path(__file__).parent
    / "fixtures"
    / "structural_effect_state"
)

ORIGINAL_EFFECTS = {
    1: (0x00, 0x21, 0x00),
    2: (0x04, 0x01, 0x07),
    3: (0x03, 0x00, 0x03),
    4: (0x08, 0x01, 0x04),
    5: (0x09, 0x01, 0x0B),
}


class ChainOrderStructuralIntegrationTests(unittest.TestCase):
    def test_all_phase14_and_phase15_captures_use_stable_parser(
        self,
    ) -> None:
        capture_count = 0

        for phase_name in ("phase14", "phase15"):
            phase_root = FIXTURES_ROOT / phase_name
            manifest = json.loads(
                (phase_root / "manifest.json").read_text(
                    encoding="utf-8"
                )
            )

            for capture in manifest["captures"]:
                capture_count += 1
                label = capture["label"]
                message = (phase_root / capture["file"]).read_bytes()

                with self.subTest(phase=phase_name, label=label):
                    state = parse_chain_order_response(message)

                    self.assertIsNotNone(state)
                    assert state is not None

                    self.assertEqual(
                        state.human_slots,
                        tuple(capture["order"]),
                    )
                    self.assertEqual(state.effect_count, 5)
                    self.assertEqual(
                        len(state.decompressed_payload or b""),
                        DECOMPRESSED_PAYLOAD_SIZE,
                    )
                    self.assertTrue(state.has_complete_bypass_state)
                    self.assertEqual(
                        state.visual_enabled_states,
                        (True, True, True, True, True),
                    )

        self.assertEqual(capture_count, 34)

    def test_baseline_exposes_class_model_and_selector(self) -> None:
        message = (
            FIXTURES_ROOT
            / "phase15"
            / "BASELINE.bin"
        ).read_bytes()
        state = parse_chain_order_response(message)

        self.assertIsNotNone(state)
        assert state is not None

        for human_slot, expected in ORIGINAL_EFFECTS.items():
            with self.subTest(human_slot=human_slot):
                record = state.record_for_internal_slot(human_slot)
                expected_class, expected_model, expected_selector = expected

                self.assertEqual(record.class_id, expected_class)
                self.assertEqual(record.model_id, expected_model)
                self.assertEqual(
                    record.secondary_selector,
                    expected_selector,
                )
                self.assertIs(record.enabled, True)

    def test_phase15_duplicate_amp_id_is_disambiguated_by_selector(
        self,
    ) -> None:
        phase_root = FIXTURES_ROOT / "phase15"
        selector_7 = parse_chain_order_response(
            (phase_root / "S4_AMP_SEL7.bin").read_bytes()
        )
        selector_8 = parse_chain_order_response(
            (phase_root / "S4_AMP_SEL8.bin").read_bytes()
        )

        self.assertIsNotNone(selector_7)
        self.assertIsNotNone(selector_8)
        assert selector_7 is not None
        assert selector_8 is not None

        record_7 = selector_7.record_for_internal_slot(4)
        record_8 = selector_8.record_for_internal_slot(4)

        self.assertEqual(record_7.class_id, 0x04)
        self.assertEqual(record_8.class_id, 0x04)
        self.assertEqual(record_7.model_id, 0x75)
        self.assertEqual(record_8.model_id, 0x75)
        self.assertEqual(record_7.secondary_selector, 0x07)
        self.assertEqual(record_8.secondary_selector, 0x08)

    def test_dly_mag_is_exposed_in_slot_five(self) -> None:
        message = (
            FIXTURES_ROOT
            / "phase15"
            / "S5_DLY_MAG.bin"
        ).read_bytes()
        state = parse_chain_order_response(message)

        self.assertIsNotNone(state)
        assert state is not None

        record = state.record_for_internal_slot(5)

        self.assertEqual(record.class_id, 0x09)
        self.assertEqual(record.model_id, 0x02)
        self.assertEqual(record.secondary_selector, 0x0B)
        self.assertEqual(state.response_slot_marker, 4)

    def test_visual_records_follow_current_order(self) -> None:
        message = (
            FIXTURES_ROOT
            / "phase14"
            / "S4_SAME_ALT.bin"
        ).read_bytes()
        state = parse_chain_order_response(message)

        self.assertIsNotNone(state)
        assert state is not None

        self.assertEqual(
            tuple(record.human_slot for record in state.visual_effect_records),
            state.human_slots,
        )
        self.assertEqual(
            state.record_at_visual_position(1).human_slot,
            state.human_slots[0],
        )

    def test_auxiliary_response_remains_ignored(self) -> None:
        message = (
            FIXTURES_ROOT
            / "AUXILIARY_128.bin"
        ).read_bytes()

        self.assertIsNone(parse_chain_order_response(message))


if __name__ == "__main__":
    unittest.main()
