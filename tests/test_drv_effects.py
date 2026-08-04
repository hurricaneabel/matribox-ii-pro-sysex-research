"""Testes da integração das classes FREQ e DRV."""

from __future__ import annotations

import unittest

from tools.commands.effect_catalog import (
    DRV_CLASS_ID,
    DRV_MODELS,
    FREQ_CLASS_ID,
    FREQ_MODELS,
    find_effect_class,
    find_effect_model,
)
from tools.commands.effect_chain import (
    CHECKSUM_INDEX,
    CLASS_HIGH_INDEX,
    CLASS_LOW_INDEX,
    CLASS_MIRROR_INDEX,
    DESTINATION_SLOT_HIGH_INDEX,
    DESTINATION_SLOT_LOW_INDEX,
    MODEL_HIGH_INDEX,
    MODEL_LOW_INDEX,
    SOURCE_SLOT_HIGH_INDEX,
    SOURCE_SLOT_LOW_INDEX,
    build_add_effect_message,
    build_replace_effect_message,
    full_message_bytes,
)
from tools.commands.effect_model import (
    CHECKSUM_INDEX as MODEL_CHECKSUM_INDEX,
    CLASS_HIGH_INDEX as MODEL_CLASS_HIGH_INDEX,
    CLASS_LOW_INDEX as MODEL_CLASS_LOW_INDEX,
    CLASS_MIRROR_INDEX as MODEL_CLASS_MIRROR_INDEX,
    MODEL_HIGH_INDEX as MODEL_ID_HIGH_INDEX,
    MODEL_LOW_INDEX as MODEL_ID_LOW_INDEX,
    build_set_effect_model_message,
)


class DriveIntegrationTests(unittest.TestCase):
    """Valida IDs, classes, pacotes e checksums capturados."""

    def test_drive_model_ids(self) -> None:
        self.assertEqual(
            {
                model.name: model.model_id
                for model in DRV_MODELS
            },
            {
                "Skreamer": 0x00,
                "Skreamer9": 0x01,
                "Butter OD": 0x02,
                "Warm OD": 0x04,
                "Super OD": 0x06,
                "Blues OD": 0x09,
                "Full OD": 0x0A,
                "Breaker OD": 0x0E,
                "Gerden OD": 0x10,
                "Timmy OD": 0x1E,
                "Master OD": 0x0F,
                "Solar Fuzz": 0x26,
                "Fuzz Cream": 0x22,
                "Red Fuzz": 0x24,
                "JP Dist": 0x2A,
                "Dark Mouse": 0x2B,
                "Plexi Dist": 0x2D,
                "Master Dist": 0x2E,
                "Dist Plus": 0x29,
                "Shark": 0x30,
                "Strive": 0x32,
                "Sardar Dist": 0x52,
                "Bass OD": 0x3F,
                "Bass Dist": 0x40,
            },
        )

    def test_class_lookup(self) -> None:
        self.assertEqual(
            find_effect_class("freq").class_id,
            FREQ_CLASS_ID,
        )
        self.assertEqual(
            find_effect_class("2").class_id,
            DRV_CLASS_ID,
        )
        self.assertEqual(
            find_effect_class("0x03").name,
            "DRV",
        )

    def test_drive_model_lookup(self) -> None:
        drive_class = find_effect_class(
            "DRV"
        )

        self.assertEqual(
            find_effect_model(
                drive_class,
                "22",
            ).name,
            "Sardar Dist",
        )
        self.assertEqual(
            find_effect_model(
                drive_class,
                "0x40",
            ).name,
            "Bass Dist",
        )

    def test_add_drive_skreamer_slot_12(self) -> None:
        packet = full_message_bytes(
            build_add_effect_message(
                slot_number=12,
                class_id=DRV_CLASS_ID,
                model_id=0x00,
            )
        )

        self.assertEqual(
            packet[
                SOURCE_SLOT_HIGH_INDEX:
                SOURCE_SLOT_LOW_INDEX + 1
            ],
            bytes((0x0F, 0x0F)),
        )
        self.assertEqual(
            packet[
                DESTINATION_SLOT_HIGH_INDEX:
                DESTINATION_SLOT_LOW_INDEX + 1
            ],
            bytes((0x00, 0x0B)),
        )
        self.assertEqual(
            packet[
                CLASS_HIGH_INDEX:
                CLASS_LOW_INDEX + 1
            ],
            bytes((0x00, 0x03)),
        )
        self.assertEqual(
            packet[
                MODEL_HIGH_INDEX:
                MODEL_LOW_INDEX + 1
            ],
            bytes((0x00, 0x00)),
        )
        self.assertEqual(
            packet[CLASS_MIRROR_INDEX],
            0x03,
        )
        self.assertEqual(
            packet[CHECKSUM_INDEX],
            0x55,
        )

    def test_add_drive_sardar_slot_12(self) -> None:
        packet = full_message_bytes(
            build_add_effect_message(
                slot_number=12,
                class_id=DRV_CLASS_ID,
                model_id=0x52,
            )
        )

        self.assertEqual(
            packet[
                MODEL_HIGH_INDEX:
                MODEL_LOW_INDEX + 1
            ],
            bytes((0x05, 0x02)),
        )
        self.assertEqual(
            packet[CHECKSUM_INDEX],
            0x5C,
        )

    def test_replace_filter_with_skreamer_slot_11(self) -> None:
        packet = full_message_bytes(
            build_replace_effect_message(
                slot_number=11,
                class_id=DRV_CLASS_ID,
                model_id=0x00,
            )
        )

        self.assertEqual(
            packet[
                SOURCE_SLOT_HIGH_INDEX:
                SOURCE_SLOT_LOW_INDEX + 1
            ],
            bytes((0x00, 0x0A)),
        )
        self.assertEqual(
            packet[
                DESTINATION_SLOT_HIGH_INDEX:
                DESTINATION_SLOT_LOW_INDEX + 1
            ],
            bytes((0x00, 0x0A)),
        )
        self.assertEqual(
            packet[
                CLASS_HIGH_INDEX:
                CLASS_LOW_INDEX + 1
            ],
            bytes((0x00, 0x03)),
        )
        self.assertEqual(
            packet[CLASS_MIRROR_INDEX],
            0x03,
        )
        self.assertEqual(
            packet[CHECKSUM_INDEX],
            0x40,
        )

    def test_replace_skreamer_with_filter_slot_11(self) -> None:
        packet = full_message_bytes(
            build_replace_effect_message(
                slot_number=11,
                class_id=FREQ_CLASS_ID,
                model_id=0x19,
            )
        )

        self.assertEqual(
            packet[
                CLASS_HIGH_INDEX:
                CLASS_LOW_INDEX + 1
            ],
            bytes((0x00, 0x01)),
        )
        self.assertEqual(
            packet[
                MODEL_HIGH_INDEX:
                MODEL_LOW_INDEX + 1
            ],
            bytes((0x01, 0x09)),
        )
        self.assertEqual(
            packet[CLASS_MIRROR_INDEX],
            0x01,
        )
        self.assertEqual(
            packet[CHECKSUM_INDEX],
            0x46,
        )

    def test_same_class_drive_skreamer_slot_11(self) -> None:
        packet = bytes(
            build_set_effect_model_message(
                slot_number=11,
                class_id=DRV_CLASS_ID,
                model_id=0x00,
            ).bin()
        )

        self.assertEqual(
            packet[
                MODEL_CLASS_HIGH_INDEX:
                MODEL_CLASS_LOW_INDEX + 1
            ],
            bytes((0x00, 0x03)),
        )
        self.assertEqual(
            packet[
                MODEL_ID_HIGH_INDEX:
                MODEL_ID_LOW_INDEX + 1
            ],
            bytes((0x00, 0x00)),
        )
        self.assertEqual(
            packet[MODEL_CLASS_MIRROR_INDEX],
            0x03,
        )
        self.assertEqual(
            packet[MODEL_CHECKSUM_INDEX],
            0x35,
        )

    def test_same_class_freq_filter_slot_1(self) -> None:
        packet = bytes(
            build_set_effect_model_message(
                slot_number=1,
                class_id=FREQ_CLASS_ID,
                model_id=0x19,
            ).bin()
        )

        self.assertEqual(
            packet[MODEL_CHECKSUM_INDEX],
            0x31,
        )

    def test_all_drive_same_class_checksums(self) -> None:
        expected_checksums = {
            "Skreamer": 0x35,
            "Skreamer9": 0x36,
            "Butter OD": 0x37,
            "Warm OD": 0x39,
            "Super OD": 0x3B,
            "Blues OD": 0x3E,
            "Full OD": 0x3F,
            "Breaker OD": 0x43,
            "Gerden OD": 0x36,
            "Timmy OD": 0x44,
            "Master OD": 0x44,
            "Solar Fuzz": 0x3D,
            "Fuzz Cream": 0x39,
            "Red Fuzz": 0x3B,
            "JP Dist": 0x41,
            "Dark Mouse": 0x42,
            "Plexi Dist": 0x44,
            "Master Dist": 0x45,
            "Dist Plus": 0x40,
            "Shark": 0x38,
            "Strive": 0x3A,
            "Sardar Dist": 0x3C,
            "Bass OD": 0x47,
            "Bass Dist": 0x39,
        }

        for model in DRV_MODELS:
            with self.subTest(
                model=model.name
            ):
                packet = bytes(
                    build_set_effect_model_message(
                        slot_number=11,
                        class_id=DRV_CLASS_ID,
                        model_id=model.model_id,
                    ).bin()
                )

                self.assertEqual(
                    packet[MODEL_CHECKSUM_INDEX],
                    expected_checksums[model.name],
                )

    def test_catalog_sizes(self) -> None:
        self.assertEqual(
            len(FREQ_MODELS),
            8,
        )
        self.assertEqual(
            len(DRV_MODELS),
            24,
        )


if __name__ == "__main__":
    unittest.main()
