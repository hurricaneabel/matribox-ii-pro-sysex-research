from __future__ import annotations

import json
from pathlib import Path
import unittest

from tools.analysis.structural_effect_state import (
    CONTAINER_HEADER_SIZE,
    CONTAINER_SIGNATURE,
    DECOMPRESSED_PAYLOAD_SIZE,
    MAX_INTERNAL_SLOTS,
    StructuralEffectStateError,
    parse_structural_effect_state,
)

from tools.commands.preset_state import build_select_preset


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


class StructuralEffectStateCaptureTests(unittest.TestCase):
    def test_all_phase14_and_phase15_captures(self) -> None:
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
                    state = parse_structural_effect_state(message)

                    self.assertIsNotNone(state)
                    assert state is not None

                    self.assertEqual(len(message), capture["message_length"])
                    self.assertEqual(
                        state.decoded_container[:4],
                        CONTAINER_SIGNATURE,
                    )
                    self.assertEqual(
                        state.compressed_size,
                        len(state.decoded_container)
                        - CONTAINER_HEADER_SIZE,
                    )
                    self.assertEqual(
                        len(state.decompressed_payload),
                        DECOMPRESSED_PAYLOAD_SIZE,
                    )
                    self.assertEqual(
                        state.human_slots,
                        tuple(capture["order"]),
                    )
                    self.assertEqual(state.effect_count, 5)

                    expected_effects = dict(ORIGINAL_EFFECTS)
                    changed_model = capture.get("model")
                    changed_slot = capture.get("slot_number")

                    if changed_model is not None:
                        assert changed_slot is not None
                        expected_effects[changed_slot] = (
                            changed_model["class_id"],
                            changed_model["model_id"],
                            changed_model["secondary_selector"],
                        )

                    for human_slot in range(1, 6):
                        record = state.record_for_internal_slot(human_slot)
                        expected_class, expected_model, expected_selector = (
                            expected_effects[human_slot]
                        )

                        self.assertTrue(record.active)
                        self.assertEqual(record.class_id, expected_class)
                        self.assertEqual(record.model_id, expected_model)
                        self.assertEqual(record.auxiliary_1, 0x00)
                        self.assertEqual(record.auxiliary_2, 0x00)
                        self.assertEqual(
                            record.secondary_selector,
                            expected_selector,
                        )
                        self.assertIs(record.enabled, True)

                    for human_slot in range(6, MAX_INTERNAL_SLOTS + 1):
                        record = state.record_for_internal_slot(human_slot)

                        self.assertFalse(record.active)
                        self.assertIsNone(record.class_id)
                        self.assertIsNone(record.model_id)
                        self.assertEqual(record.auxiliary_1, 0x00)
                        self.assertEqual(record.auxiliary_2, 0x00)
                        self.assertIsNone(record.secondary_selector)
                        self.assertIsNone(record.enabled)

                    expected_marker = (
                        None
                        if changed_slot is None
                        else changed_slot - 1
                    )
                    self.assertEqual(
                        state.response_slot_marker,
                        expected_marker,
                    )

        self.assertEqual(capture_count, 34)

    def test_variable_compressed_sizes_share_one_payload_layout(self) -> None:
        phase15_root = FIXTURES_ROOT / "phase15"
        labels = (
            "S5_AMP_SEL7",
            "S5_AMP_SEL8",
            "S5_DLY_MAG",
        )
        states = []

        for label in labels:
            state = parse_structural_effect_state(
                (phase15_root / f"{label}.bin").read_bytes()
            )
            self.assertIsNotNone(state)
            assert state is not None
            states.append(state)

        self.assertEqual(
            tuple(state.compressed_size for state in states),
            (65, 71, 73),
        )
        self.assertEqual(
            {len(state.decompressed_payload) for state in states},
            {DECOMPRESSED_PAYLOAD_SIZE},
        )

    def test_auxiliary_128_byte_response_is_not_effect_state(self) -> None:
        message = (FIXTURES_ROOT / "AUXILIARY_128.bin").read_bytes()

        self.assertIsNone(parse_structural_effect_state(message))

    def test_preset_event_54_bytes_is_not_effect_state(self) -> None:
        message = bytearray(
            build_select_preset("56A")
        )
        message[8] = 0x00

        self.assertIsNone(
            parse_structural_effect_state(message)
        )


class StructuralEffectStateValidationTests(unittest.TestCase):
    def test_wrong_declared_sysex_length_returns_none(self) -> None:
        message = bytearray(
            (
                FIXTURES_ROOT
                / "phase15"
                / "BASELINE.bin"
            ).read_bytes()
        )
        message[9] -= 1

        self.assertIsNone(parse_structural_effect_state(message))

    def test_invalid_container_nibble_raises(self) -> None:
        message = bytearray(
            (
                FIXTURES_ROOT
                / "phase15"
                / "BASELINE.bin"
            ).read_bytes()
        )
        message[13] = 0x10

        with self.assertRaises(StructuralEffectStateError):
            parse_structural_effect_state(message)

    def test_invalid_compressed_size_raises(self) -> None:
        message = bytearray(
            (
                FIXTURES_ROOT
                / "phase15"
                / "BASELINE.bin"
            ).read_bytes()
        )

        # Índices 21–28 do SysEx codificam os quatro bytes little-endian
        # do tamanho comprimido dentro do contêiner.
        message[21] = 0x04
        message[22] = 0x04

        with self.assertRaises(StructuralEffectStateError):
            parse_structural_effect_state(message)


if __name__ == "__main__":
    unittest.main()
