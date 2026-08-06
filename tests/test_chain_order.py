from __future__ import annotations

import unittest

from tools.commands.chain_order import (
    ChainOrderProtocolError,
    apply_visual_move,
    calculate_declared_message_length,
    parse_chain_order_response,
)


INVERTED_132 = bytes.fromhex(
    "f0 21 25 4d 50 00 00 3e 00 3b 00 00 00 00 01 00 00 00 00 01 00 03 03 00 00 00 00 00 00 00 04 00 00 00 00 00 04 00 01 00 01 00 00 0f 0f 02 07 00 02 00 00 00 00 00 04 02 07 02 08 00 00 00 07 0f 0f 02 01 00 00 00 00 00 00 00 01 00 00 00 00 00 07 00 00 02 00 00 03 00 00 00 00 00 0d 00 00 00 00 00 00 00 01 00 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 0f 0f 01 01 00 00 00 00 f7"
)

NORMAL_132 = bytes.fromhex(
    "f0 21 25 4d 50 00 00 3b 00 3b 00 00 00 00 01 00 00 00 00 01 00 03 03 00 00 00 00 00 00 00 04 00 00 00 00 00 04 00 01 00 00 00 01 0f 0f 02 07 00 02 00 00 00 00 00 04 02 07 02 08 00 00 00 07 0f 0f 02 01 00 00 00 00 00 00 00 01 00 00 00 00 00 07 00 00 02 00 00 03 00 00 00 00 00 0d 00 00 00 00 00 00 00 01 00 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 0f 0f 01 01 00 00 00 00 f7"
)

M1_172 = bytes.fromhex(
    "f0 21 25 4d 50 00 00 7e 00 4f 00 00 00 00 01 00 00 00 00 01 00 04 07 00 00 00 00 00 00 00 07 00 00 00 00 00 04 00 01 00 01 00 02 00 03 00 04 00 00 0f 0f 0a 00 00 00 00 02 00 00 00 04 00 03 00 08 00 09 0a 08 00 01 00 0b 0f 0f 02 01 00 00 00 00 00 00 00 01 00 00 00 00 00 07 00 00 00 00 00 00 00 03 00 01 06 00 00 05 00 01 00 00 00 00 00 0b 00 00 03 02 00 00 00 00 00 00 00 02 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 01 00 01 00 01 00 01 00 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 0f 0f 01 01 00 00 00 00 f7"
)

M2_172 = bytes.fromhex(
    "f0 21 25 4d 50 00 00 7e 00 4f 00 00 00 00 01 00 00 00 00 01 00 04 07 00 00 00 00 00 00 00 07 00 00 00 00 00 04 00 01 00 03 00 01 00 02 00 04 00 00 0f 0f 0a 00 00 00 00 02 00 00 00 04 00 03 00 08 00 09 0a 08 00 01 00 0b 0f 0f 02 01 00 00 00 00 00 00 00 01 00 00 00 00 00 07 00 00 00 00 00 00 00 03 00 01 06 00 00 05 00 01 00 00 00 00 00 0b 00 00 03 02 00 00 00 00 00 00 00 02 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 01 00 01 00 01 00 01 00 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 0f 0f 01 01 00 00 00 00 f7"
)

M3_172 = bytes.fromhex(
    "f0 21 25 4d 50 00 00 7e 00 4f 00 00 00 00 01 00 00 00 00 01 00 04 07 00 00 00 00 00 00 00 07 00 00 00 00 00 04 00 01 00 03 00 00 00 01 00 02 00 04 0f 0f 0a 00 00 00 00 02 00 00 00 04 00 03 00 08 00 09 0a 08 00 01 00 0b 0f 0f 02 01 00 00 00 00 00 00 00 01 00 00 00 00 00 07 00 00 00 00 00 00 00 03 00 01 06 00 00 05 00 01 00 00 00 00 00 0b 00 00 03 02 00 00 00 00 00 00 00 02 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 01 00 01 00 01 00 01 00 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 0f 0f 01 01 00 00 00 00 f7"
)

R1_168 = bytes.fromhex(
    "f0 21 25 4d 50 00 00 5f 00 4d 00 00 00 00 01 00 00 00 00 01 00 04 05 00 00 00 00 00 00 00 07 00 00 00 00 00 04 00 01 00 00 00 03 00 01 00 02 00 04 0f 0f 0a 00 00 00 00 02 00 00 00 04 00 03 00 08 00 09 0a 08 00 01 00 0b 0f 0f 02 01 00 00 00 00 00 00 00 01 00 00 00 00 00 07 00 00 00 00 00 00 00 03 00 01 08 03 00 05 00 00 00 0b 00 00 03 02 00 00 00 00 00 00 00 02 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 01 00 01 00 01 00 01 00 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 0f 0f 01 01 00 00 00 00 f7"
)

R2_168 = bytes.fromhex(
    "f0 21 25 4d 50 00 00 5f 00 4d 00 00 00 00 01 00 00 00 00 01 00 04 05 00 00 00 00 00 00 00 07 00 00 00 00 00 04 00 01 00 00 00 01 00 02 00 03 00 04 0f 0f 0a 00 00 00 00 02 00 00 00 04 00 03 00 08 00 09 0a 08 00 01 00 0b 0f 0f 02 01 00 00 00 00 00 00 00 01 00 00 00 00 00 07 00 00 00 00 00 00 00 03 00 01 08 03 00 05 00 00 00 0b 00 00 03 02 00 00 00 00 00 00 00 02 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 01 00 01 00 01 00 01 00 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 0f 0f 01 01 00 00 00 00 f7"
)


class ChainOrderCaptureTests(unittest.TestCase):
    def assert_order(
        self,
        message: bytes,
        expected_internal_ids: tuple[int, ...],
        expected_human_slots: tuple[int, ...],
    ) -> None:
        state = parse_chain_order_response(
            message
        )

        self.assertIsNotNone(state)
        assert state is not None

        self.assertEqual(
            state.internal_slot_ids,
            expected_internal_ids,
        )
        self.assertEqual(
            state.human_slots,
            expected_human_slots,
        )
        self.assertEqual(
            state.effect_count,
            len(expected_internal_ids),
        )
        self.assertEqual(
            state.declared_message_length,
            len(message),
        )

    def test_parse_inverted_two_effect_capture(self) -> None:
        self.assert_order(
            INVERTED_132,
            (1, 0),
            (2, 1),
        )

    def test_parse_normal_two_effect_capture(self) -> None:
        self.assert_order(
            NORMAL_132,
            (0, 1),
            (1, 2),
        )

    def test_parse_m1_real_172_byte_capture(self) -> None:
        self.assert_order(
            M1_172,
            (1, 2, 3, 4, 0),
            (2, 3, 4, 5, 1),
        )

    def test_parse_m2_real_172_byte_capture(self) -> None:
        self.assert_order(
            M2_172,
            (3, 1, 2, 4, 0),
            (4, 2, 3, 5, 1),
        )

    def test_parse_m3_real_172_byte_capture(self) -> None:
        self.assert_order(
            M3_172,
            (3, 0, 1, 2, 4),
            (4, 1, 2, 3, 5),
        )

    def test_parse_r1_real_168_byte_capture(self) -> None:
        self.assert_order(
            R1_168,
            (0, 3, 1, 2, 4),
            (1, 4, 2, 3, 5),
        )

    def test_parse_r2_real_168_byte_capture(self) -> None:
        self.assert_order(
            R2_168,
            (0, 1, 2, 3, 4),
            (1, 2, 3, 4, 5),
        )

    def test_declared_lengths_match_all_real_captures(self) -> None:
        for message in (
            INVERTED_132,
            NORMAL_132,
            M1_172,
            M2_172,
            M3_172,
            R1_168,
            R2_168,
        ):
            with self.subTest(
                message_length=len(message)
            ):
                self.assertEqual(
                    calculate_declared_message_length(
                        message
                    ),
                    len(message),
                )

    def test_slot_at_visual_position(self) -> None:
        state = parse_chain_order_response(
            M1_172
        )

        self.assertIsNotNone(state)
        assert state is not None

        self.assertEqual(
            state.slot_at_visual_position(1),
            2,
        )
        self.assertEqual(
            state.slot_at_visual_position(5),
            1,
        )


class ChainOrderValidationTests(unittest.TestCase):
    def test_nonmatching_short_event_returns_none(self) -> None:
        event = bytearray(
            NORMAL_132[:54]
        )
        event[-1] = 0xF7

        self.assertIsNone(
            parse_chain_order_response(
                event
            )
        )

    def test_wrong_declared_length_returns_none(self) -> None:
        message = bytearray(
            NORMAL_132
        )
        message[9] = 0x3A

        self.assertIsNone(
            parse_chain_order_response(
                message
            )
        )

    def test_reject_invalid_nibble(self) -> None:
        message = bytearray(
            NORMAL_132
        )
        message[39] = 0x10

        with self.assertRaises(
            ChainOrderProtocolError
        ):
            parse_chain_order_response(
                message
            )

    def test_reject_duplicate_internal_slot(self) -> None:
        message = bytearray(
            NORMAL_132
        )
        message[39:45] = bytes(
            (
                0x00,
                0x00,
                0x00,
                0x00,
                0x0F,
                0x0F,
            )
        )

        with self.assertRaises(
            ChainOrderProtocolError
        ):
            parse_chain_order_response(
                message
            )

    def test_reject_internal_slot_above_twelve(self) -> None:
        message = bytearray(
            NORMAL_132
        )
        message[39:43] = bytes(
            (
                0x00,
                0x0C,
                0x0F,
                0x0F,
            )
        )

        with self.assertRaises(
            ChainOrderProtocolError
        ):
            parse_chain_order_response(
                message
            )

    def test_parse_twelve_slots_without_terminator(self) -> None:
        message = bytearray(
            NORMAL_132
        )

        encoded = bytearray()

        for internal_id in range(12):
            encoded.extend(
                (
                    0x00,
                    internal_id,
                )
            )

        message[39:63] = encoded

        state = parse_chain_order_response(
            message
        )

        self.assertIsNotNone(state)
        assert state is not None

        self.assertEqual(
            state.internal_slot_ids,
            tuple(range(12)),
        )
        self.assertEqual(
            state.human_slots,
            tuple(range(1, 13)),
        )


class VisualMoveTests(unittest.TestCase):
    def test_apply_visual_move(self) -> None:
        self.assertEqual(
            apply_visual_move(
                (0, 1, 2, 3, 4),
                1,
                5,
            ),
            (1, 2, 3, 4, 0),
        )

        self.assertEqual(
            apply_visual_move(
                (1, 2, 3, 4, 0),
                3,
                1,
            ),
            (3, 1, 2, 4, 0),
        )

    def test_reject_invalid_positions(self) -> None:
        for source, destination in (
            (0, 2),
            (1, 6),
            (2, 2),
        ):
            with self.subTest(
                source=source,
                destination=destination,
            ):
                with self.assertRaises(
                    ValueError
                ):
                    apply_visual_move(
                        (0, 1, 2, 3, 4),
                        source,
                        destination,
                    )


if __name__ == "__main__":
    unittest.main()
