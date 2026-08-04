"""Testes de regressão para descobertas confirmadas do protocolo SysEx."""

from __future__ import annotations

import unittest
from pathlib import Path

from tools.analysis.verify_volume_anchor import locate_volume
from tools.commands.request_preset_dump import (
    is_preset_45b_confirmation,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURES_DIRECTORY = (
    PROJECT_ROOT
    / "data"
    / "fixtures"
    / "volume"
)

VOLUME_49_FILE = (
    FIXTURES_DIRECTORY
    / "preset_volume_49.bin"
)

VOLUME_51_FILE = (
    FIXTURES_DIRECTORY
    / "preset_volume_51.bin"
)


CONFIRMATION_45B_CHECKSUM_32 = bytes.fromhex(
    "F0 21 25 4D 50 00 00 32 00 14 00 00 00 00 "
    "01 00 00 00 00 01 00 00 0C 00 00 00 00 00 "
    "00 01 09 00 01 00 00 00 0A 00 01 0B 01 00 "
    "00 00 00 00 00 01 01 00 00 00 00 F7"
)

CONFIRMATION_45B_CHECKSUM_53 = bytes.fromhex(
    "F0 21 25 4D 50 00 00 53 00 14 00 00 00 00 "
    "01 00 00 00 00 01 00 00 0C 00 00 00 00 00 "
    "00 01 09 00 01 00 00 00 0A 00 01 0B 01 00 "
    "00 00 00 00 00 01 01 00 00 00 00 F7"
)


class VolumeDumpAnchorTests(unittest.TestCase):
    """Valida o campo de volume nas amostras binárias confirmadas."""

    def test_fixture_files_exist(self) -> None:
        self.assertTrue(VOLUME_49_FILE.is_file())
        self.assertTrue(VOLUME_51_FILE.is_file())

    def test_extracts_volume_49(self) -> None:
        index, volume = locate_volume(
            VOLUME_49_FILE.read_bytes()
        )

        self.assertEqual(volume, 49)
        self.assertEqual(index, 0x00E1)

    def test_extracts_volume_51(self) -> None:
        index, volume = locate_volume(
            VOLUME_51_FILE.read_bytes()
        )

        self.assertEqual(volume, 51)
        self.assertEqual(index, 0x00DF)

    def test_volume_position_is_not_absolute(self) -> None:
        index_49, _ = locate_volume(
            VOLUME_49_FILE.read_bytes()
        )
        index_51, _ = locate_volume(
            VOLUME_51_FILE.read_bytes()
        )

        self.assertNotEqual(index_49, index_51)


class PresetConfirmationTests(unittest.TestCase):
    """Valida o reconhecimento da confirmação do preset 45B."""

    def test_accepts_confirmation_with_checksum_32(self) -> None:
        self.assertTrue(
            is_preset_45b_confirmation(
                CONFIRMATION_45B_CHECKSUM_32
            )
        )

    def test_accepts_confirmation_with_checksum_53(self) -> None:
        self.assertTrue(
            is_preset_45b_confirmation(
                CONFIRMATION_45B_CHECKSUM_53
            )
        )

    def test_rejects_invalid_confirmation(self) -> None:
        invalid_message = bytearray(
            CONFIRMATION_45B_CHECKSUM_32
        )
        invalid_message[30] = 0x08

        self.assertFalse(
            is_preset_45b_confirmation(
                bytes(invalid_message)
            )
        )


if __name__ == "__main__":
    unittest.main()