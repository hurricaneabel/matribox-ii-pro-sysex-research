"""Testes da integração da classe AMP."""

from __future__ import annotations

import unittest

from tools.commands.effect_catalog import (
    AMP_CLASS_ID,
    AMP_MODELS,
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


class AmpIntegrationTests(unittest.TestCase):
    """Valida o catálogo e os pacotes confirmados da classe AMP."""

    def test_amp_class_id_and_menu(self) -> None:
        self.assertEqual(
            AMP_CLASS_ID,
            0x04,
        )
        self.assertEqual(
            find_effect_class("AMP").class_id,
            0x04,
        )
        self.assertEqual(
            find_effect_class("5").name,
            "AMP",
        )

    def test_amp_catalog_has_63_models(self) -> None:
        self.assertEqual(
            len(AMP_MODELS),
            63,
        )

    def test_amp_first_and_last_models(self) -> None:
        self.assertEqual(
            (
                AMP_MODELS[0].name,
                AMP_MODELS[0].model_id,
                AMP_MODELS[0].secondary_selector,
            ),
            ("TWD DELUXE", 0x01, 0x07),
        )
        self.assertEqual(
            (
                AMP_MODELS[-1].name,
                AMP_MODELS[-1].model_id,
                AMP_MODELS[-1].secondary_selector,
            ),
            ("AC PREAMP 2", 0x7B, 0x08),
        )

    def test_amp_lookup_by_menu_and_name(self) -> None:
        amp_class = find_effect_class(
            "AMP"
        )

        self.assertEqual(
            find_effect_model(
                amp_class,
                "47",
            ).name,
            "CALIF DUAL V",
        )
        self.assertEqual(
            find_effect_model(
                amp_class,
                "a bassft",
            ).menu_number,
            60,
        )

    def test_duplicate_amp_model_id_is_ambiguous(self) -> None:
        amp_class = find_effect_class(
            "AMP"
        )

        with self.assertRaises(
            ValueError
        ):
            find_effect_model(
                amp_class,
                "0x75",
            )

    def test_voks_bass_and_a_bassft_are_distinct(self) -> None:
        voks_bass = AMP_MODELS[57]
        a_bassft = AMP_MODELS[59]

        self.assertEqual(
            voks_bass.model_id,
            a_bassft.model_id,
        )
        self.assertNotEqual(
            voks_bass.secondary_selector,
            a_bassft.secondary_selector,
        )

    def test_replace_freq_with_twd_deluxe_slot_11(self) -> None:
        packet = full_message_bytes(
            build_replace_effect_message(
                slot_number=11,
                class_id=AMP_CLASS_ID,
                model_id=0x01,
                secondary_selector=0x07,
            )
        )

        self.assertEqual(
            packet[CLASS_HIGH_INDEX:CLASS_LOW_INDEX + 1],
            bytes((0x00, 0x04)),
        )
        self.assertEqual(
            packet[MODEL_HIGH_INDEX:MODEL_LOW_INDEX + 1],
            bytes((0x00, 0x01)),
        )
        self.assertEqual(
            packet[SECONDARY_SELECTOR_INDEX],
            0x07,
        )
        self.assertEqual(
            packet[CHECKSUM_INDEX],
            0x46,
        )

    def test_add_voks_bass_slot_12(self) -> None:
        packet = full_message_bytes(
            build_add_effect_message(
                slot_number=12,
                class_id=AMP_CLASS_ID,
                model_id=0x75,
                secondary_selector=0x07,
            )
        )

        self.assertEqual(
            packet[SECONDARY_SELECTOR_INDEX],
            0x07,
        )
        self.assertEqual(
            packet[CHECKSUM_INDEX],
            0x66,
        )

    def test_add_a_bassft_slot_12(self) -> None:
        packet = full_message_bytes(
            build_add_effect_message(
                slot_number=12,
                class_id=AMP_CLASS_ID,
                model_id=0x75,
                secondary_selector=0x08,
            )
        )

        self.assertEqual(
            packet[SECONDARY_SELECTOR_INDEX],
            0x08,
        )
        self.assertEqual(
            packet[CHECKSUM_INDEX],
            0x67,
        )

    def test_all_amp_same_class_checksums(self) -> None:
        expected_checksums = {
            "TWD DELUXE": 0x3B,
            "B-MAN N": 0x3D,
            "B-MAN BRI": 0x40,
            "DARK DOUBLE": 0x3E,
            "DARK DELUXE": 0x3F,
            "SUPERO 2 CL": 0x49,
            "SUPERO 2 OD": 0x44,
            "VOKS 15TB": 0x3B,
            "VOKS 30N": 0x3C,
            "VOKS 30TB": 0x43,
            "JAZZ 120": 0x3F,
            "SUPERB CL": 0x40,
            "SUPERB OD": 0x46,
            "CALIF STAR CL": 0x44,
            "CALIF STAR OD": 0x48,
            "BOG SV CL": 0x45,
            "BOG SV OD": 0x4A,
            "BOG XT BLUE": 0x41,
            "BOG XT RED": 0x4E,
            "DOCTOR CL": 0x46,
            "DOCTOR OD": 0x47,
            "DRAGON CL": 0x4A,
            "DRAGON CL B": 0x4C,
            "DRAGON OD": 0x4D,
            "SOL 100 CL": 0x3F,
            "SOL 100 OD": 0x45,
            "SOL 100 LD": 0x48,
            "BRIT 45": 0x46,
            "BRIT 45+": 0x47,
            "BRIT 45JP": 0x48,
            "BRIT 50": 0x49,
            "BRIT 50+": 0x4A,
            "BRIT 50JP": 0x4B,
            "BRIT SLP": 0x3D,
            "BRIT 800": 0x42,
            "BRIT 900": 0x4C,
            "FLYMAN 1": 0x3E,
            "FLYMAN 2": 0x3F,
            "FLYMAN+ 1": 0x4C,
            "FLYMAN+ 2": 0x4D,
            "CALIF IIC+ 1": 0x46,
            "CALIF IIC+ 2": 0x47,
            "CALIF IIC+ 3": 0x48,
            "CALIF IV LD 1": 0x44,
            "CALIF IV LD 2": 0x45,
            "CALIF IV LD 3": 0x46,
            "CALIF DUAL V": 0x48,
            "CALIF DUAL M": 0x49,
            "TANGER R100": 0x42,
            "HALEN 51": 0x49,
            "ENG 120": 0x4E,
            "ENG 120+": 0x40,
            "DIZZY VH": 0x45,
            "DIZZY VH S": 0x46,
            "DIZZY VH+": 0x4A,
            "DIZZY VH+ S": 0x4B,
            "A BASSVT": 0x44,
            "VOKS BASS": 0x46,
            "CALI BASS": 0x48,
            "A BASSFT": 0x47,
            "F-2BASS": 0x48,
            "AC PREAMP": 0x4C,
            "AC PREAMP 2": 0x4D,
        }

        for model in AMP_MODELS:
            with self.subTest(
                model=model.name
            ):
                packet = bytes(
                    build_set_effect_model_message(
                        slot_number=11,
                        class_id=AMP_CLASS_ID,
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
