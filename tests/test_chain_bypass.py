from __future__ import annotations

from pathlib import Path
import unittest

from tools.commands.chain_order import (
    BYPASS_DISABLED_VALUE,
    BYPASS_ENABLED_VALUE,
    BYPASS_START_INDEX,
    ChainOrderProtocolError,
    parse_chain_order_response,
)


FIXTURES = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "chain_bypass"
)


EXPECTED_BITS = {
    "BASE_ALL_ON_structural.bin": "11111",
    "S1_OFF_structural.bin": "01111",
    "S2_OFF_structural.bin": "10111",
    "S3_OFF_structural.bin": "11011",
    "S4_OFF_structural.bin": "11101",
    "S5_OFF_structural.bin": "11110",
    "COMBO_S2_S4_OFF_structural.bin": "10101",
    "ALL_OFF_structural.bin": "00000",
    "FINAL_ALL_ON_structural.bin": "11111",
}


def read_fixture(
    name: str,
) -> bytes:
    return (
        FIXTURES
        / name
    ).read_bytes()


class ChainBypassPhysicalCaptureTests(
    unittest.TestCase
):
    def test_all_physical_captures_match_expected_bits(
        self,
    ) -> None:
        for name, expected_bits in EXPECTED_BITS.items():
            with self.subTest(
                capture=name
            ):
                state = parse_chain_order_response(
                    read_fixture(
                        name
                    )
                )

                self.assertIsNotNone(
                    state
                )

                assert state is not None

                observed_bits = "".join(
                    "1"
                    if enabled
                    else "0"
                    for enabled in (
                        state.visual_enabled_states
                    )
                )

                self.assertEqual(
                    observed_bits,
                    expected_bits,
                )

                self.assertTrue(
                    state.has_complete_bypass_state
                )

                self.assertEqual(
                    state.human_slots,
                    (
                        1,
                        2,
                        3,
                        4,
                        5,
                    ),
                )

    def test_internal_slot_lookup(
        self,
    ) -> None:
        state = parse_chain_order_response(
            read_fixture(
                "COMBO_S2_S4_OFF_structural.bin"
            )
        )

        self.assertIsNotNone(
            state
        )

        assert state is not None

        self.assertTrue(
            state.enabled_for_internal_slot(
                1
            )
        )

        self.assertFalse(
            state.enabled_for_internal_slot(
                2
            )
        )

        self.assertTrue(
            state.enabled_for_internal_slot(
                3
            )
        )

        self.assertFalse(
            state.enabled_for_internal_slot(
                4
            )
        )

        self.assertTrue(
            state.enabled_for_internal_slot(
                5
            )
        )

        self.assertIsNone(
            state.enabled_for_internal_slot(
                6
            )
        )

    def test_visual_lookup_uses_current_order(
        self,
    ) -> None:
        state = parse_chain_order_response(
            read_fixture(
                "S5_OFF_SWAPPED_structural.bin"
            )
        )

        self.assertIsNotNone(
            state
        )

        assert state is not None

        self.assertEqual(
            state.human_slots,
            (
                1,
                2,
                3,
                5,
                4,
            ),
        )

        self.assertEqual(
            state.visual_enabled_states,
            (
                True,
                True,
                True,
                False,
                True,
            ),
        )

        self.assertFalse(
            state.enabled_at_visual_position(
                4
            )
        )

        self.assertTrue(
            state.enabled_at_visual_position(
                5
            )
        )

    def test_invalid_active_bypass_value_is_rejected(
        self,
    ) -> None:
        message = bytearray(
            read_fixture(
                "BASE_ALL_ON_structural.bin"
            )
        )

        message[
            BYPASS_START_INDEX
        ] = 0x01

        message[
            BYPASS_START_INDEX + 1
        ] = 0x01

        with self.assertRaises(
            ChainOrderProtocolError
        ):
            parse_chain_order_response(
                message
            )

    def test_confirmed_encoded_values(
        self,
    ) -> None:
        self.assertEqual(
            BYPASS_ENABLED_VALUE,
            0x10,
        )

        self.assertEqual(
            BYPASS_DISABLED_VALUE,
            0x00,
        )

    def test_lookup_range_validation(
        self,
    ) -> None:
        state = parse_chain_order_response(
            read_fixture(
                "BASE_ALL_ON_structural.bin"
            )
        )

        self.assertIsNotNone(
            state
        )

        assert state is not None

        with self.assertRaises(
            IndexError
        ):
            state.enabled_for_internal_slot(
                0
            )

        with self.assertRaises(
            IndexError
        ):
            state.enabled_for_internal_slot(
                13
            )

        with self.assertRaises(
            IndexError
        ):
            state.enabled_at_visual_position(
                0
            )

        with self.assertRaises(
            IndexError
        ):
            state.enabled_at_visual_position(
                6
            )


if __name__ == "__main__":
    unittest.main()
