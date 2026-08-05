"""Testes do protocolo estável de estado do preset."""

from __future__ import annotations

import unittest

from tools.commands.preset_state import (
    CURRENT_PRESET_QUERY,
    PresetStateProtocolError,
    build_current_preset_query,
    build_select_preset,
    calculate_protocol_checksum,
    decode_preset_address,
    encode_preset_index,
    is_preset_confirmation,
    normalize_preset,
    parse_preset_event,
)


SELECT_45B_CAPTURE = bytes.fromhex(
    "F0 21 25 4D 50 00 00 32 12 14 "
    "00 00 00 00 01 00 00 00 00 01 "
    "00 00 0C 00 00 00 00 00 00 01 "
    "09 00 01 00 00 00 0A 00 01 0B "
    "01 00 00 00 00 00 00 01 01 00 "
    "00 00 00 F7"
)

INCOMING_45B_CHECKSUM_32 = bytes.fromhex(
    "F0 21 25 4D 50 00 00 32 00 14 "
    "00 00 00 00 01 00 00 00 00 01 "
    "00 00 0C 00 00 00 00 00 00 01 "
    "09 00 01 00 00 00 0A 00 01 0B "
    "01 00 00 00 00 00 00 01 01 00 "
    "00 00 00 F7"
)

INCOMING_45B_CHECKSUM_53 = bytes.fromhex(
    "F0 21 25 4D 50 00 00 53 00 14 "
    "00 00 00 00 01 00 00 00 00 01 "
    "00 00 0C 00 00 00 00 00 00 01 "
    "09 00 01 00 00 00 0A 00 01 0B "
    "01 00 00 00 00 00 00 01 01 00 "
    "00 00 00 F7"
)


class PresetAddressTests(unittest.TestCase):
    """Valida a codificação do endereço de todos os presets."""

    def test_known_addresses(self) -> None:
        self.assertEqual(
            encode_preset_index(0),
            (0x00, 0x00),
        )
        self.assertEqual(
            encode_preset_index(173),
            (0x0A, 0x0D),
        )
        self.assertEqual(
            encode_preset_index(176),
            (0x0B, 0x00),
        )
        self.assertEqual(
            encode_preset_index(177),
            (0x0B, 0x01),
        )
        self.assertEqual(
            encode_preset_index(181),
            (0x0B, 0x05),
        )

    def test_round_trip_for_all_presets(self) -> None:
        for index in range(240):
            encoded = encode_preset_index(
                index
            )

            self.assertEqual(
                decode_preset_address(
                    *encoded
                ),
                index,
            )

    def test_rejects_non_nibble_address(self) -> None:
        with self.assertRaises(
            PresetStateProtocolError
        ):
            decode_preset_address(
                0x10,
                0x00,
            )

    def test_normalizes_label_and_index(self) -> None:
        self.assertEqual(
            normalize_preset("45B"),
            (177, "45B"),
        )
        self.assertEqual(
            normalize_preset(177),
            (177, "45B"),
        )


class CurrentPresetQueryTests(unittest.TestCase):
    """Valida a consulta 0x10 capturada do editor oficial."""

    def test_query_matches_capture(self) -> None:
        self.assertEqual(
            build_current_preset_query(),
            CURRENT_PRESET_QUERY,
        )

    def test_query_has_expected_length(self) -> None:
        self.assertEqual(
            len(build_current_preset_query()),
            46,
        )

    def test_query_checksum_is_1e(self) -> None:
        query = build_current_preset_query()

        self.assertEqual(
            query[7],
            0x1E,
        )
        self.assertEqual(
            calculate_protocol_checksum(
                query
            ),
            0x1E,
        )


class SelectPresetTests(unittest.TestCase):
    """Valida a construção dos comandos 0x14."""

    def test_45b_matches_exact_capture(self) -> None:
        self.assertEqual(
            build_select_preset("45B"),
            SELECT_45B_CAPTURE,
        )

    def test_validated_checksums(self) -> None:
        expected = {
            "01A": 0x26,
            "44B": 0x3D,
            "45A": 0x31,
            "45B": 0x32,
            "45C": 0x33,
            "45D": 0x34,
            "46A": 0x35,
            "46B": 0x36,
        }

        for label, checksum in expected.items():
            with self.subTest(
                preset=label
            ):
                message = (
                    build_select_preset(label)
                )

                self.assertEqual(
                    message[7],
                    checksum,
                )
                self.assertEqual(
                    calculate_protocol_checksum(
                        message
                    ),
                    checksum,
                )

    def test_45a_address_is_0b_00(self) -> None:
        message = build_select_preset(
            "45A"
        )

        self.assertEqual(
            message[39:41],
            bytes.fromhex("0B 00"),
        )


class PresetEventTests(unittest.TestCase):
    """Valida eventos espontâneos e confirmações recebidas."""

    def test_parses_incoming_45b(self) -> None:
        event = parse_preset_event(
            INCOMING_45B_CHECKSUM_32
        )

        self.assertIsNotNone(event)
        assert event is not None

        self.assertEqual(
            event.index,
            177,
        )
        self.assertEqual(
            event.label,
            "45B",
        )
        self.assertTrue(
            event.checksum_matches
        )

    def test_accepts_observed_checksum_53_variant(self) -> None:
        event = parse_preset_event(
            INCOMING_45B_CHECKSUM_53
        )

        self.assertIsNotNone(event)
        assert event is not None

        self.assertEqual(
            event.label,
            "45B",
        )
        self.assertFalse(
            event.checksum_matches
        )

    def test_confirms_only_requested_preset(self) -> None:
        self.assertTrue(
            is_preset_confirmation(
                INCOMING_45B_CHECKSUM_32,
                "45B",
            )
        )
        self.assertFalse(
            is_preset_confirmation(
                INCOMING_45B_CHECKSUM_32,
                "45A",
            )
        )

    def test_rejects_outgoing_command_as_event(self) -> None:
        self.assertIsNone(
            parse_preset_event(
                SELECT_45B_CAPTURE
            )
        )

    def test_rejects_wrong_command(self) -> None:
        invalid = bytearray(
            INCOMING_45B_CHECKSUM_32
        )
        invalid[9] = 0x15

        self.assertIsNone(
            parse_preset_event(
                invalid
            )
        )

    def test_rejects_invalid_address_nibble(self) -> None:
        invalid = bytearray(
            INCOMING_45B_CHECKSUM_32
        )
        invalid[39] = 0x10

        self.assertIsNone(
            parse_preset_event(
                invalid
            )
        )


if __name__ == "__main__":
    unittest.main()
