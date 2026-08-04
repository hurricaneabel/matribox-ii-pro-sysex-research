"""Testes da integração da classe IR."""

from __future__ import annotations

import unittest

from tools.commands.effect_catalog import (
    CAB_CLASS_ID,
    IR_CLASS_ID,
    IR_MODELS,
    find_effect_class,
    find_effect_model,
)
from tools.commands.effect_chain import (
    CHECKSUM_INDEX,
    EFFECT_INSTANCE_FLAG_INDEX,
    SECONDARY_SELECTOR_INDEX,
    build_add_effect_message,
    build_replace_effect_message,
    full_message_bytes,
)
from tools.commands.effect_model import (
    CHECKSUM_INDEX as MODEL_CHECKSUM_INDEX,
    EFFECT_INSTANCE_FLAG_INDEX as MODEL_FLAG_INDEX,
    SECONDARY_SELECTOR_INDEX as MODEL_SELECTOR_INDEX,
    build_set_effect_model_message,
)


class IrIntegrationTests(unittest.TestCase):
    """Valida os 20 slots IR e a flag estrutural específica."""

    def test_ir_class_id_and_menu(self) -> None:
        self.assertEqual(
            IR_CLASS_ID,
            0x06,
        )
        self.assertEqual(
            find_effect_class("IR").class_id,
            0x06,
        )
        self.assertEqual(
            find_effect_class("7").name,
            "IR",
        )

    def test_ir_catalog_has_20_slots(self) -> None:
        self.assertEqual(
            len(IR_MODELS),
            20,
        )

    def test_ir_model_ids_are_sequential(self) -> None:
        self.assertEqual(
            [
                model.model_id
                for model in IR_MODELS
            ],
            list(
                range(0x00, 0x14)
            ),
        )
        self.assertEqual(
            find_effect_model(
                find_effect_class("IR"),
                "20",
            ).model_id,
            0x13,
        )

    def test_all_irs_use_selector_0a(self) -> None:
        self.assertEqual(
            {
                model.secondary_selector
                for model in IR_MODELS
            },
            {0x0A},
        )

    def test_replace_cab_with_ir1_slot_11(self) -> None:
        packet = full_message_bytes(
            build_replace_effect_message(
                slot_number=11,
                class_id=IR_CLASS_ID,
                model_id=0x00,
                secondary_selector=0x0A,
            )
        )

        self.assertEqual(
            packet[EFFECT_INSTANCE_FLAG_INDEX],
            0x01,
        )
        self.assertEqual(
            packet[SECONDARY_SELECTOR_INDEX],
            0x0A,
        )
        self.assertEqual(
            packet[CHECKSUM_INDEX],
            0x4B,
        )

    def test_replace_ir_with_cab_clears_flag(self) -> None:
        packet = full_message_bytes(
            build_replace_effect_message(
                slot_number=11,
                class_id=CAB_CLASS_ID,
                model_id=0x00,
                secondary_selector=0x0A,
            )
        )

        self.assertEqual(
            packet[EFFECT_INSTANCE_FLAG_INDEX],
            0x00,
        )
        self.assertEqual(
            packet[CHECKSUM_INDEX],
            0x49,
        )

    def test_add_ir1_slot_12(self) -> None:
        packet = full_message_bytes(
            build_add_effect_message(
                slot_number=12,
                class_id=IR_CLASS_ID,
                model_id=0x00,
                secondary_selector=0x0A,
            )
        )

        self.assertEqual(
            packet[EFFECT_INSTANCE_FLAG_INDEX],
            0x01,
        )
        self.assertEqual(
            packet[SECONDARY_SELECTOR_INDEX],
            0x0A,
        )
        self.assertEqual(
            packet[CHECKSUM_INDEX],
            0x60,
        )

    def test_add_ir20_slot_12(self) -> None:
        packet = full_message_bytes(
            build_add_effect_message(
                slot_number=12,
                class_id=IR_CLASS_ID,
                model_id=0x13,
                secondary_selector=0x0A,
            )
        )

        self.assertEqual(
            packet[EFFECT_INSTANCE_FLAG_INDEX],
            0x01,
        )
        self.assertEqual(
            packet[CHECKSUM_INDEX],
            0x64,
        )

    def test_ir1_same_class_slot_11(self) -> None:
        packet = bytes(
            build_set_effect_model_message(
                slot_number=11,
                class_id=IR_CLASS_ID,
                model_id=0x00,
                secondary_selector=0x0A,
            ).bin()
        )

        self.assertEqual(
            packet[MODEL_FLAG_INDEX],
            0x01,
        )
        self.assertEqual(
            packet[MODEL_SELECTOR_INDEX],
            0x0A,
        )
        self.assertEqual(
            packet[MODEL_CHECKSUM_INDEX],
            0x40,
        )

    def test_all_ir_same_class_checksums(self) -> None:
        expected_checksums = {
            "IR 1": 0x40,
            "IR 2": 0x41,
            "IR 3": 0x42,
            "IR 4": 0x43,
            "IR 5": 0x44,
            "IR 6": 0x45,
            "IR 7": 0x46,
            "IR 8": 0x47,
            "IR 9": 0x48,
            "IR 10": 0x49,
            "IR 11": 0x4A,
            "IR 12": 0x4B,
            "IR 13": 0x4C,
            "IR 14": 0x4D,
            "IR 15": 0x4E,
            "IR 16": 0x4F,
            "IR 17": 0x41,
            "IR 18": 0x42,
            "IR 19": 0x43,
            "IR 20": 0x44,
        }

        for model in IR_MODELS:
            with self.subTest(
                model=model.name
            ):
                packet = bytes(
                    build_set_effect_model_message(
                        slot_number=11,
                        class_id=IR_CLASS_ID,
                        model_id=model.model_id,
                        secondary_selector=model.secondary_selector,
                    ).bin()
                )

                self.assertEqual(
                    packet[MODEL_FLAG_INDEX],
                    0x01,
                )
                self.assertEqual(
                    packet[MODEL_SELECTOR_INDEX],
                    0x0A,
                )
                self.assertEqual(
                    packet[MODEL_CHECKSUM_INDEX],
                    expected_checksums[model.name],
                )


if __name__ == "__main__":
    unittest.main()
