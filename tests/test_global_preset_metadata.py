"""Testes de regressão para a tabela global de presets."""

from __future__ import annotations

import unittest
from pathlib import Path

from tools.commands.global_preset_metadata import (
    GlobalPresetMetadataError,
    decode_global_preset_metadata,
    decode_global_preset_metadata_file,
    preset_index_to_label,
    preset_label_to_index,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_FILE = (
    PROJECT_ROOT
    / "data"
    / "fixtures"
    / "global_metadata"
    / "preset_metadata_45abc.bin"
)


class PresetAddressTests(unittest.TestCase):
    """Valida a conversão entre índice absoluto e banco/letra."""

    def test_known_addresses(self) -> None:
        self.assertEqual(
            preset_label_to_index("01A"),
            0,
        )
        self.assertEqual(
            preset_label_to_index("45A"),
            176,
        )
        self.assertEqual(
            preset_label_to_index("45B"),
            177,
        )
        self.assertEqual(
            preset_label_to_index("45C"),
            178,
        )
        self.assertEqual(
            preset_label_to_index("60D"),
            239,
        )

    def test_round_trip_for_all_presets(self) -> None:
        for index in range(240):
            label = preset_index_to_label(index)
            self.assertEqual(
                preset_label_to_index(label),
                index,
            )

    def test_rejects_invalid_label(self) -> None:
        with self.assertRaises(ValueError):
            preset_label_to_index("61A")


class GlobalPresetMetadataTests(unittest.TestCase):
    """Valida o layout real confirmado nas capturas."""

    @classmethod
    def setUpClass(cls) -> None:
        if not FIXTURE_FILE.is_file():
            raise AssertionError(
                f"Fixture ausente: {FIXTURE_FILE}"
            )

        cls.table = (
            decode_global_preset_metadata_file(
                FIXTURE_FILE
            )
        )

    def test_reads_all_240_presets(self) -> None:
        self.assertEqual(
            len(self.table.presets),
            240,
        )

    def test_reads_validated_45a_metadata(self) -> None:
        preset = self.table.by_label("45A")

        self.assertEqual(
            preset.index,
            176,
        )
        self.assertEqual(
            preset.name,
            "Matribox II PRO",
        )
        self.assertEqual(
            preset.filter_tag,
            "JKLMNOPQR",
        )

    def test_reads_validated_45b_metadata(self) -> None:
        preset = self.table.by_label("45B")

        self.assertEqual(
            preset.index,
            177,
        )
        self.assertEqual(
            preset.name,
            "NOME123456789",
        )
        self.assertEqual(
            preset.filter_tag,
            "TAG45A123",
        )

    def test_reads_validated_45c_metadata(self) -> None:
        preset = self.table.by_label("45C")

        self.assertEqual(
            preset.index,
            178,
        )
        self.assertEqual(
            preset.name,
            "Matribox II PRO",
        )
        self.assertEqual(
            preset.filter_tag,
            "UVWXYZ789",
        )

    def test_rejects_invalid_outer_signature(self) -> None:
        invalid = bytearray(
            FIXTURE_FILE.read_bytes()
        )
        invalid[0] = 0x7F

        with self.assertRaises(
            GlobalPresetMetadataError
        ):
            decode_global_preset_metadata(
                bytes(invalid)
            )

    def test_rejects_invalid_declared_size(self) -> None:
        invalid = bytearray(
            FIXTURE_FILE.read_bytes()
        )
        invalid[4:8] = (1).to_bytes(
            4,
            "little",
        )

        with self.assertRaises(
            GlobalPresetMetadataError
        ):
            decode_global_preset_metadata(
                bytes(invalid)
            )


if __name__ == "__main__":
    unittest.main()
