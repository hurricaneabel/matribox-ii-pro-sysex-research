import unittest

from set_effect_slot import (
    CHECKSUM_INDEX,
    SLOT_HIGH_INDEX,
    SLOT_LOW_INDEX,
    STATE_HIGH_INDEX,
    STATE_LOW_INDEX,
    build_effect_message,
    split_into_nibbles,
)


class TestEffectSlotProtocol(unittest.TestCase):
    """Testes do SysEx para ligar e desligar efeitos por posição."""

    def test_split_value_into_nibbles(self):
        high, low = split_into_nibbles(0x2F)

        self.assertEqual(high, 0x02)
        self.assertEqual(low, 0x0F)

    def test_position_1_enabled(self):
        message = build_effect_message(
            effect_position=1,
            enabled=True,
        )

        # O Mido remove F0 e F7.
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

    def test_position_2_disabled(self):
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

    def test_position_3_enabled(self):
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

    def test_reject_position_zero(self):
        with self.assertRaises(ValueError):
            build_effect_message(
                effect_position=0,
                enabled=True,
            )

    def test_reject_unconfirmed_position(self):
        with self.assertRaises(ValueError):
            build_effect_message(
                effect_position=4,
                enabled=True,
            )


if __name__ == "__main__":
    unittest.main()