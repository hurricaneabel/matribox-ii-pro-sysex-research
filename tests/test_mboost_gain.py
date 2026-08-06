from __future__ import annotations

from pathlib import Path
import json
import struct
import unittest

from tools.commands.mboost_gain import (
    COMMAND_INDEX,
    EXPECTED_MESSAGE_LENGTH,
    PARAMETER_ADDRESS_HIGH_INDEX,
    PARAMETER_ADDRESS_LOW_INDEX,
    MBoostGainProtocolError,
    SLOT_HIGH_INDEX,
    SLOT_LOW_INDEX,
    VALUE_END_INDEX,
    VALUE_START_INDEX,
    decode_gain_nibbles,
    parse_mboost_gain_response,
)


FIXTURE_ROOT = (
    Path(__file__).parent
    / "fixtures"
    / "mboost_gain"
)


def encode_gain_for_test(gain: int) -> bytes:
    raw = struct.pack("<f", float(gain))
    return bytes(
        (
            (raw[2] >> 4) & 0x0F,
            raw[2] & 0x0F,
            (raw[3] >> 4) & 0x0F,
            raw[3] & 0x0F,
        )
    )


class MBoostGainPhysicalCaptureTests(unittest.TestCase):
    def test_all_physical_fixtures_decode_slot_and_gain(self) -> None:
        fixtures = sorted(FIXTURE_ROOT.glob("*.bin"))
        self.assertEqual(len(fixtures), 27)

        for fixture in fixtures:
            with self.subTest(fixture=fixture.name):
                message = fixture.read_bytes()
                event = parse_mboost_gain_response(message)

                self.assertIsNotNone(event)
                assert event is not None

                expected_slot = 1 if fixture.name.startswith("slot1_") else 2
                expected_gain = int(fixture.stem.rsplit("_", 1)[1])

                self.assertEqual(len(message), EXPECTED_MESSAGE_LENGTH)
                self.assertEqual(event.human_slot, expected_slot)
                self.assertEqual(event.gain, expected_gain)
                self.assertEqual(
                    event.encoded_gain,
                    encode_gain_for_test(expected_gain),
                )

    def test_reordering_does_not_change_internal_slot(self) -> None:
        before = parse_mboost_gain_response(
            (FIXTURE_ROOT / "slot2_skreamer_gain_050.bin").read_bytes()
        )
        after = parse_mboost_gain_response(
            (FIXTURE_ROOT / "slot2_reordered_gain_050.bin").read_bytes()
        )

        self.assertIsNotNone(before)
        self.assertIsNotNone(after)
        assert before is not None and after is not None

        self.assertEqual(before.human_slot, 2)
        self.assertEqual(after.human_slot, 2)
        self.assertEqual(before.gain, 50)
        self.assertEqual(after.gain, 50)
        self.assertEqual(before.encoded_gain, after.encoded_gain)


class MBoostGainTwelveSlotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.template = bytearray(
            (FIXTURE_ROOT / "slot1_gain_050.bin").read_bytes()
        )

    def test_parser_accepts_zero_based_addresses_for_all_twelve_slots(self) -> None:
        for human_slot in range(1, 13):
            with self.subTest(human_slot=human_slot):
                internal_slot_id = human_slot - 1
                message = bytearray(self.template)
                message[SLOT_HIGH_INDEX] = (internal_slot_id >> 4) & 0x0F
                message[SLOT_LOW_INDEX] = internal_slot_id & 0x0F

                event = parse_mboost_gain_response(message)

                self.assertIsNotNone(event)
                assert event is not None
                self.assertEqual(event.human_slot, human_slot)
                self.assertEqual(event.gain, 50)

    def test_slot_thirteen_is_rejected(self) -> None:
        message = bytearray(self.template)
        message[SLOT_HIGH_INDEX] = 0x00
        message[SLOT_LOW_INDEX] = 0x0C

        with self.assertRaises(MBoostGainProtocolError):
            parse_mboost_gain_response(message)


class MBoostGainValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.message = bytearray(
            (FIXTURE_ROOT / "slot1_gain_050.bin").read_bytes()
        )

    def test_known_gain_encodings(self) -> None:
        for gain in (0, 1, 2, 10, 25, 50, 75, 99, 100):
            with self.subTest(gain=gain):
                encoded = encode_gain_for_test(gain)
                self.assertEqual(decode_gain_nibbles(encoded), gain)

    def test_other_command_is_ignored(self) -> None:
        self.message[COMMAND_INDEX] = 0x1B
        self.assertIsNone(parse_mboost_gain_response(self.message))

    def test_other_parameter_address_is_ignored(self) -> None:
        self.message[PARAMETER_ADDRESS_HIGH_INDEX] = 0x01
        self.message[PARAMETER_ADDRESS_LOW_INDEX] = 0x05
        self.assertIsNone(parse_mboost_gain_response(self.message))

    def test_out_of_range_gain_is_rejected(self) -> None:
        self.message[VALUE_START_INDEX:VALUE_END_INDEX] = (
            encode_gain_for_test(101)
        )

        with self.assertRaises(MBoostGainProtocolError):
            parse_mboost_gain_response(self.message)

    def test_non_nibble_value_is_rejected(self) -> None:
        self.message[VALUE_START_INDEX] = 0x10

        with self.assertRaises(MBoostGainProtocolError):
            parse_mboost_gain_response(self.message)


class MBoostGainEvidenceManifestTests(unittest.TestCase):
    def test_manifest_preserves_sources_and_approved_live_validation(self) -> None:
        manifest = json.loads(
            (FIXTURE_ROOT / "manifest.json").read_text(encoding="utf-8")
        )

        self.assertEqual(manifest["schema_version"], 1)
        self.assertEqual(manifest["physical_binary_fixtures"], 27)
        self.assertEqual(len(manifest["controlled_capture_sources"]), 4)
        self.assertEqual(
            manifest["live_validation"]["internal_slots_observed"],
            [2, 8, 10, 12],
        )
        self.assertTrue(manifest["live_validation"]["multiple_instances"])
        self.assertTrue(manifest["live_validation"]["read_only"])
        self.assertTrue(
            (
                FIXTURE_ROOT
                / manifest["live_validation"]["evidence_log"]
            ).is_file()
        )


if __name__ == "__main__":
    unittest.main()
