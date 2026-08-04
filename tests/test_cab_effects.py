"""Testes da integração da classe CAB."""

from __future__ import annotations

import unittest

from tools.commands.effect_catalog import (
    CAB_CLASS_ID,
    CAB_MODELS,
    find_effect_class,
    find_effect_model,
)
from tools.commands.effect_chain import (
    CHECKSUM_INDEX,
    CLASS_HIGH_INDEX,
    CLASS_LOW_INDEX,
    MODEL_HIGH_INDEX,
    MODEL_LOW_INDEX,
    SECONDARY_SELECTOR_INDEX,
    build_add_effect_message,
    build_replace_effect_message,
    full_message_bytes,
)
from tools.commands.effect_model import (
    CHECKSUM_INDEX as MODEL_CHECKSUM_INDEX,
    SECONDARY_SELECTOR_INDEX as MODEL_SELECTOR_INDEX,
    build_set_effect_model_message,
)


class CabIntegrationTests(unittest.TestCase):
    """Valida o catálogo e os pacotes confirmados da classe CAB."""

    def test_cab_class_id_and_menu(self) -> None:
        self.assertEqual(
            CAB_CLASS_ID,
            0x05,
        )
        self.assertEqual(
            find_effect_class("CAB").class_id,
            0x05,
        )
        self.assertEqual(
            find_effect_class("6").name,
            "CAB",
        )

    def test_cab_catalog_has_61_models(self) -> None:
        self.assertEqual(
            len(CAB_MODELS),
            61,
        )

    def test_cab_first_and_last_models(self) -> None:
        self.assertEqual(
            (
                CAB_MODELS[0].name,
                CAB_MODELS[0].model_id,
                CAB_MODELS[0].secondary_selector,
            ),
            ("SUPERO 1X6", 0x00, 0x0A),
        )
        self.assertEqual(
            (
                CAB_MODELS[-1].name,
                CAB_MODELS[-1].model_id,
                CAB_MODELS[-1].secondary_selector,
            ),
            ("DOUBLE BASS", 0x45, 0x0A),
        )

    def test_cab_lookup_by_menu_and_name(self) -> None:
        cab_class = find_effect_class(
            "CAB"
        )

        self.assertEqual(
            find_effect_model(
                cab_class,
                "46",
            ).name,
            "CALIF 2X10",
        )
        self.assertEqual(
            find_effect_model(
                cab_class,
                "double bass",
            ).menu_number,
            61,
        )

    def test_cab_model_ids_are_unique(self) -> None:
        model_ids = [
            model.model_id
            for model in CAB_MODELS
        ]

        self.assertEqual(
            len(model_ids),
            len(set(model_ids)),
        )

    def test_all_cabs_use_selector_0a(self) -> None:
        self.assertEqual(
            {
                model.secondary_selector
                for model in CAB_MODELS
            },
            {0x0A},
        )

    def test_replace_amp_with_supero_slot_11(self) -> None:
        packet = full_message_bytes(
            build_replace_effect_message(
                slot_number=11,
                class_id=CAB_CLASS_ID,
                model_id=0x00,
                secondary_selector=0x0A,
            )
        )

        self.assertEqual(
            packet[CLASS_HIGH_INDEX:CLASS_LOW_INDEX + 1],
            bytes((0x00, 0x05)),
        )
        self.assertEqual(
            packet[MODEL_HIGH_INDEX:MODEL_LOW_INDEX + 1],
            bytes((0x00, 0x00)),
        )
        self.assertEqual(
            packet[SECONDARY_SELECTOR_INDEX],
            0x0A,
        )
        self.assertEqual(
            packet[CHECKSUM_INDEX],
            0x49,
        )

    def test_add_supero_slot_12(self) -> None:
        packet = full_message_bytes(
            build_add_effect_message(
                slot_number=12,
                class_id=CAB_CLASS_ID,
                model_id=0x00,
                secondary_selector=0x0A,
            )
        )

        self.assertEqual(
            packet[SECONDARY_SELECTOR_INDEX],
            0x0A,
        )
        self.assertEqual(
            packet[CHECKSUM_INDEX],
            0x5E,
        )

    def test_add_double_bass_slot_12(self) -> None:
        packet = full_message_bytes(
            build_add_effect_message(
                slot_number=12,
                class_id=CAB_CLASS_ID,
                model_id=0x45,
                secondary_selector=0x0A,
            )
        )

        self.assertEqual(
            packet[SECONDARY_SELECTOR_INDEX],
            0x0A,
        )
        self.assertEqual(
            packet[CHECKSUM_INDEX],
            0x67,
        )

    def test_all_cab_same_class_checksums(self) -> None:
        expected_checksums = {
            "SUPERO 1X6": 0x3E,
            "CHAP 1X8": 0x3F,
            "PRINCE 1X10": 0x40,
            "TWD 2X10": 0x43,
            "TWD LUX 1X12": 0x49,
            "DARK LUX 1X12": 0x41,
            "TWIN VERB 2X12": 0x41,
            "CUSTOM 2X12": 0x4A,
            "B-MAN 2X10": 0x45,
            "B-MAN 4X10": 0x4D,
            "JAZZ 2X12": 0x40,
            "BRIT 1X12": 0x4C,
            "BRIT GN 2X12": 0x42,
            "BRIT LD 4X12": 0x4E,
            "BRIT TD 4X12": 0x40,
            "BRIT MD 4X12": 0x41,
            "BRIT GN 4X12": 0x42,
            "BRIT 75 4X12": 0x41,
            "BRIT BK 4X12": 0x4B,
            "VOKS 1X12": 0x46,
            "VOKS 2X12": 0x4D,
            "BOG SV 1X12": 0x44,
            "CHIEF 2X12": 0x3F,
            "CALIF DUAL 4X12": 0x44,
            "CALIF STAR 1X12": 0x47,
            "CALIF STAR 2X12": 0x48,
            "CALIF 1X12": 0x4A,
            "SUPERO 2X12": 0x46,
            "SUPERB 2X12": 0x47,
            "BLUE 2X12": 0x4C,
            "HALEN 4X12": 0x43,
            "BOG 4X12": 0x45,
            "ENG 4X12": 0x46,
            "BOG UB 4X12": 0x47,
            "SOL 4X12": 0x48,
            "TANGER 4X12": 0x49,
            "WATT 4X12": 0x4A,
            "WAM 4X12": 0x4C,
            "HUMBLE 4X12": 0x4D,
            "DIZZY 4X12": 0x4E,
            "CALIF 4X12": 0x42,
            "DV 1X15": 0x43,
            "DV 4X10": 0x48,
            "WORK 1X15": 0x44,
            "WORK 4X10": 0x4A,
            "CALIF 2X10": 0x46,
            "MAK 2X10": 0x47,
            "A BASS 1X15": 0x45,
            "A BASS 4X10": 0x49,
            "A BASS 8X10": 0x4C,
            "HART 4X12": 0x4B,
            "D 1": 0x4D,
            "D 2": 0x4E,
            "OM": 0x4F,
            "JUMBO": 0x50,
            "BIRD": 0x42,
            "GA": 0x43,
            "CLASSICAL AC": 0x44,
            "MANDOLIN": 0x45,
            "FRETLESS BASS": 0x46,
            "DOUBLE BASS": 0x47,
        }

        for model in CAB_MODELS:
            with self.subTest(
                model=model.name
            ):
                packet = bytes(
                    build_set_effect_model_message(
                        slot_number=11,
                        class_id=CAB_CLASS_ID,
                        model_id=model.model_id,
                        secondary_selector=model.secondary_selector,
                    ).bin()
                )

                self.assertEqual(
                    packet[MODEL_SELECTOR_INDEX],
                    model.secondary_selector,
                )
                self.assertEqual(
                    packet[MODEL_CHECKSUM_INDEX],
                    expected_checksums[model.name],
                )


if __name__ == "__main__":
    unittest.main()
