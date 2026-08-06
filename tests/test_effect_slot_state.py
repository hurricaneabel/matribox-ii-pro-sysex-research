from __future__ import annotations

from pathlib import Path
import unittest

from tools.commands.effect_slot_state import (
    CHECKSUM_INDEX,
    SLOT_LOW_INDEX,
    STATE_LOW_INDEX,
    EffectSlotStateProtocolError,
    parse_effect_slot_state_response,
)


FIXTURES = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "effect_slot_state"
)


class EffectSlotStatePhysicalCaptureTests(unittest.TestCase):
    def test_all_five_slots_and_both_states(self) -> None:
        for human_slot in range(1, 6):
            for state_name, expected_enabled in (
                ("OFF", False),
                ("ON", True),
            ):
                with self.subTest(
                    slot=human_slot,
                    state=state_name,
                ):
                    event = parse_effect_slot_state_response(
                        (
                            FIXTURES
                            / f"S{human_slot}_{state_name}.bin"
                        ).read_bytes()
                    )

                    self.assertIsNotNone(event)
                    assert event is not None

                    self.assertEqual(event.human_slot, human_slot)
                    self.assertEqual(event.enabled, expected_enabled)

    def test_checksum_variation_is_preserved_but_not_rejected(self) -> None:
        message = bytearray((FIXTURES / "S1_ON.bin").read_bytes())
        message[CHECKSUM_INDEX] = 0x01

        event = parse_effect_slot_state_response(message)

        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event.observed_checksum, 0x01)
        self.assertTrue(event.enabled)

    def test_auxiliary_54_byte_response_is_ignored(self) -> None:
        self.assertIsNone(
            parse_effect_slot_state_response(
                (FIXTURES / "AUXILIARY_54.bin").read_bytes()
            )
        )


class EffectSlotStateValidationTests(unittest.TestCase):
    def test_invalid_slot_is_rejected(self) -> None:
        message = bytearray((FIXTURES / "S1_ON.bin").read_bytes())
        message[SLOT_LOW_INDEX] = 0x0C

        with self.assertRaises(EffectSlotStateProtocolError):
            parse_effect_slot_state_response(message)

    def test_invalid_state_is_rejected(self) -> None:
        message = bytearray((FIXTURES / "S1_ON.bin").read_bytes())
        message[STATE_LOW_INDEX] = 0x02

        with self.assertRaises(EffectSlotStateProtocolError):
            parse_effect_slot_state_response(message)

    def test_unrelated_same_size_message_is_ignored(self) -> None:
        message = bytearray((FIXTURES / "S1_ON.bin").read_bytes())
        message[30] = 0x0C

        self.assertIsNone(parse_effect_slot_state_response(message))


if __name__ == "__main__":
    unittest.main()
