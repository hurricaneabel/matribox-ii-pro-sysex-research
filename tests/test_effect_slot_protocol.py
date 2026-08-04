import unittest

from tools.commands.set_effect_slot import (
    CHECKSUM_INDEX,
    SLOT_HIGH_INDEX,
    SLOT_LOW_INDEX,
    STATE_HIGH_INDEX,
    STATE_LOW_INDEX,
    build_effect_message,
    split_into_nibbles,
)


class TestEffectSlotProtocol(unittest.TestCase):
    """Testes do SysEx para controlar os slots internos de efeitos."""

    def test_split_value_into_nibbles(self):
        high, low = split_into_nibbles(0x2F)

        self.assertEqual(high, 0x02)
        self.assertEqual(low, 0x0F)

    def test_slot_1_enabled(self):
        message = build_effect_message(
            effect_position=1,
            enabled=True,
        )

        # O Mido remove F0 e F7 do campo data.
        self.assertEqual(
            message.data[SLOT_HIGH_INDEX - 1],
            0x00,
        )
        self.assertEqual(
            message.data[SLOT_LOW_INDEX - 1],
            0x00,
        )
        self.assertEqual(
            message.data[STATE_HIGH_INDEX - 1],
            0x00,
        )
        self.assertEqual(
            message.data[STATE_LOW_INDEX - 1],
            0x01,
        )
        self.assertEqual(
            message.data[CHECKSUM_INDEX - 1],
            0x1C,
        )

    def test_slot_2_disabled(self):
        message = build_effect_message(
            effect_position=2,
            enabled=False,
        )

        self.assertEqual(
            message.data[SLOT_HIGH_INDEX - 1],
            0x00,
        )
        self.assertEqual(
            message.data[SLOT_LOW_INDEX - 1],
            0x01,
        )
        self.assertEqual(
            message.data[STATE_HIGH_INDEX - 1],
            0x00,
        )
        self.assertEqual(
            message.data[STATE_LOW_INDEX - 1],
            0x00,
        )
        self.assertEqual(
            message.data[CHECKSUM_INDEX - 1],
            0x1C,
        )

    def test_slot_3_enabled(self):
        message = build_effect_message(
            effect_position=3,
            enabled=True,
        )

        self.assertEqual(
            message.data[SLOT_HIGH_INDEX - 1],
            0x00,
        )
        self.assertEqual(
            message.data[SLOT_LOW_INDEX - 1],
            0x02,
        )
        self.assertEqual(
            message.data[STATE_HIGH_INDEX - 1],
            0x00,
        )
        self.assertEqual(
            message.data[STATE_LOW_INDEX - 1],
            0x01,
        )
        self.assertEqual(
            message.data[CHECKSUM_INDEX - 1],
            0x1E,
        )

    def test_slot_4_disabled(self):
        message = build_effect_message(
            effect_position=4,
            enabled=False,
        )

        self.assertEqual(
            message.data[SLOT_HIGH_INDEX - 1],
            0x00,
        )
        self.assertEqual(
            message.data[SLOT_LOW_INDEX - 1],
            0x03,
        )
        self.assertEqual(
            message.data[STATE_HIGH_INDEX - 1],
            0x00,
        )
        self.assertEqual(
            message.data[STATE_LOW_INDEX - 1],
            0x00,
        )
        self.assertEqual(
            message.data[CHECKSUM_INDEX - 1],
            0x1E,
        )

    def test_slot_12_enabled(self):
        message = build_effect_message(
            effect_position=12,
            enabled=True,
        )

        # Slot 12 da interface = ID interno 11 = hexadecimal 0B.
        self.assertEqual(
            message.data[SLOT_HIGH_INDEX - 1],
            0x00,
        )
        self.assertEqual(
            message.data[SLOT_LOW_INDEX - 1],
            0x0B,
        )
        self.assertEqual(
            message.data[STATE_HIGH_INDEX - 1],
            0x00,
        )
        self.assertEqual(
            message.data[STATE_LOW_INDEX - 1],
            0x01,
        )
        self.assertEqual(
            message.data[CHECKSUM_INDEX - 1],
            0x27,
        )

    def test_reject_slot_zero(self):
        with self.assertRaises(ValueError):
            build_effect_message(
                effect_position=0,
                enabled=True,
            )

    def test_reject_slot_above_12(self):
        with self.assertRaises(ValueError):
            build_effect_message(
                effect_position=13,
                enabled=True,
            )


if __name__ == "__main__":
    unittest.main()