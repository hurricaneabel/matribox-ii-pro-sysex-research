"""Testes da integração da classe WAH."""

from __future__ import annotations

import unittest

from tools.commands.effect_catalog import (
    WAH_CLASS_ID,
    WAH_MODELS,
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


class WahIntegrationTests(unittest.TestCase):
    """Valida IDs, seletores e checksums da classe WAH."""

    def test_wah_class_id(self) -> None:
        self.assertEqual(
            WAH_CLASS_ID,
            0x02,
        )
        self.assertEqual(
            find_effect_class("WAH").class_id,
            0x02,
        )
        self.assertEqual(
            find_effect_class("4").name,
            "WAH",
        )

    def test_wah_model_catalog(self) -> None:
        observed = {
            model.name: (
                model.model_id,
                model.secondary_selector,
            )
            for model in WAH_MODELS
        }

        self.assertEqual(
            observed,
            {
                "VOKS WAH": (0x01, 0x05),
                "CRY WAH": (0x08, 0x05),
                "RACK WAH": (0x0A, 0x05),
                "BASS WAH": (0x07, 0x05),
                "TOUCH WAH": (0x0F, 0x01),
                "AUTO WAH": (0x15, 0x01),
            },
        )

    def test_wah_lookup(self) -> None:
        wah_class = find_effect_class(
            "WAH"
        )

        self.assertEqual(
            find_effect_model(
                wah_class,
                "5",
            ).name,
            "TOUCH WAH",
        )
        self.assertEqual(
            find_effect_model(
                wah_class,
                "auto wah",
            ).model_id,
            0x15,
        )

    def test_add_voks_wah_slot_12(self) -> None:
        packet = full_message_bytes(
            build_add_effect_message(
                slot_number=12,
                class_id=WAH_CLASS_ID,
                model_id=0x01,
                secondary_selector=0x05,
            )
        )

        self.assertEqual(
            packet[CLASS_HIGH_INDEX:CLASS_LOW_INDEX + 1],
            bytes((0x00, 0x02)),
        )
        self.assertEqual(
            packet[MODEL_HIGH_INDEX:MODEL_LOW_INDEX + 1],
            bytes((0x00, 0x01)),
        )
        self.assertEqual(
            packet[SECONDARY_SELECTOR_INDEX],
            0x05,
        )
        self.assertEqual(
            packet[CHECKSUM_INDEX],
            0x57,
        )

    def test_add_touch_wah_slot_12(self) -> None:
        packet = full_message_bytes(
            build_add_effect_message(
                slot_number=12,
                class_id=WAH_CLASS_ID,
                model_id=0x0F,
                secondary_selector=0x01,
            )
        )

        self.assertEqual(
            packet[SECONDARY_SELECTOR_INDEX],
            0x01,
        )
        self.assertEqual(
            packet[CHECKSUM_INDEX],
            0x61,
        )

    def test_replace_freq_with_voks_wah_slot_11(self) -> None:
        packet = full_message_bytes(
            build_replace_effect_message(
                slot_number=11,
                class_id=WAH_CLASS_ID,
                model_id=0x01,
                secondary_selector=0x05,
            )
        )

        self.assertEqual(
            packet[CLASS_HIGH_INDEX:CLASS_LOW_INDEX + 1],
            bytes((0x00, 0x02)),
        )
        self.assertEqual(
            packet[MODEL_HIGH_INDEX:MODEL_LOW_INDEX + 1],
            bytes((0x00, 0x01)),
        )
        self.assertEqual(
            packet[SECONDARY_SELECTOR_INDEX],
            0x05,
        )
        self.assertEqual(
            packet[CHECKSUM_INDEX],
            0x42,
        )

    def test_all_wah_same_class_checksums(self) -> None:
        expected_checksums = {
            "VOKS WAH": 0x37,
            "CRY WAH": 0x3E,
            "RACK WAH": 0x40,
            "BASS WAH": 0x3D,
            "TOUCH WAH": 0x41,
            "AUTO WAH": 0x38,
        }

        for model in WAH_MODELS:
            with self.subTest(
                model=model.name
            ):
                packet = bytes(
                    build_set_effect_model_message(
                        slot_number=11,
                        class_id=WAH_CLASS_ID,
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

    def test_wah_catalog_size(self) -> None:
        self.assertEqual(
            len(WAH_MODELS),
            6,
        )


if __name__ == "__main__":
    unittest.main()
