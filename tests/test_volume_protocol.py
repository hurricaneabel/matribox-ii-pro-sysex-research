import unittest

from tools.commands.set_volume import (
    CHECKSUM_INDEX,
    MESSAGE_TEMPLATE,
    VOLUME_HIGH_INDEX,
    VOLUME_LOW_INDEX,
    build_volume_message,
    calculate_checksum,
    split_into_nibbles,
)


class TestVolumeProtocol(unittest.TestCase):
    """Testes do protocolo SysEx usado no Preset Volume."""

    def test_split_volume_49_into_nibbles(self):
        high, low = split_into_nibbles(49)

        self.assertEqual(high, 0x03)
        self.assertEqual(low, 0x01)

    def test_split_volume_75_into_nibbles(self):
        high, low = split_into_nibbles(75)

        self.assertEqual(high, 0x04)
        self.assertEqual(low, 0x0B)

    def test_split_volume_100_into_nibbles(self):
        high, low = split_into_nibbles(100)

        self.assertEqual(high, 0x06)
        self.assertEqual(low, 0x04)

    def test_checksum_for_volume_75(self):
        message = MESSAGE_TEMPLATE.copy()

        high, low = split_into_nibbles(75)

        message[VOLUME_HIGH_INDEX] = high
        message[VOLUME_LOW_INDEX] = low

        checksum = calculate_checksum(message)

        self.assertEqual(checksum, 0x32)

    def test_build_volume_message(self):
        message = build_volume_message(49)

        self.assertEqual(message.type, "sysex")

        # O Mido remove F0 e F7 do campo data.
        self.assertEqual(message.data[VOLUME_HIGH_INDEX - 1], 0x03)
        self.assertEqual(message.data[VOLUME_LOW_INDEX - 1], 0x01)

        calculated_checksum = message.data[CHECKSUM_INDEX - 1]

        self.assertEqual(calculated_checksum, 0x27)

    def test_reject_volume_below_zero(self):
        with self.assertRaises(ValueError):
            build_volume_message(-1)

    def test_reject_volume_above_100(self):
        with self.assertRaises(ValueError):
            build_volume_message(101)


if __name__ == "__main__":
    unittest.main()