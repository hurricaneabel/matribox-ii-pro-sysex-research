"""Testes da integração da classe DLY."""

from __future__ import annotations

import unittest

from tools.commands.effect_catalog import (
    DLY_CLASS_ID,
    DLY_MODELS,
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


class DlyIntegrationTests(unittest.TestCase):
    """Valida os 17 modelos DLY capturados e testados fisicamente."""

    EXPECTED_MODELS = (
        ("WARM", 0x01, 0x0B),
        ("PURE", 0x00, 0x0B),
        ("MAG", 0x02, 0x0B),
        ("TUBE", 0x0B, 0x0B),
        ("BBD", 0x1D, 0x0B),
        ("PING PONG", 0x04, 0x0B),
        ("SLAPBACK", 0x05, 0x0B),
        ("SWEEP", 0x06, 0x0B),
        ("RING", 0x09, 0x0B),
        ("MULTI TAPE", 0x0C, 0x0B),
        ("SWEET", 0x0D, 0x0B),
        ("999 ECHO", 0x12, 0x0B),
        ("RACK", 0x14, 0x0B),
        ("LO-FI", 0x26, 0x0B),
        ("REVERSE", 0x28, 0x0B),
        ("EKO D", 0x03, 0x0B),
        ("ICE DELAY", 0x2C, 0x0B),
    )

    EXPECTED_SAME_CLASS_CHECKSUMS = (
        0x44, 0x43, 0x45, 0x4E, 0x51, 0x47,
        0x48, 0x49, 0x4C, 0x4F, 0x50, 0x46,
        0x48, 0x4B, 0x4D, 0x46, 0x51,
    )

    def test_dly_class_id_and_menu(self) -> None:
        self.assertEqual(DLY_CLASS_ID, 0x09)
        self.assertEqual(find_effect_class("DLY").class_id, 0x09)
        self.assertEqual(find_effect_class("10").name, "DLY")

    def test_dly_catalog_has_17_models(self) -> None:
        self.assertEqual(len(DLY_MODELS), 17)

    def test_dly_model_mapping_and_order(self) -> None:
        self.assertEqual(
            tuple(
                (model.name, model.model_id, model.secondary_selector)
                for model in DLY_MODELS
            ),
            self.EXPECTED_MODELS,
        )

    def test_dly_menu_numbers_are_sequential(self) -> None:
        self.assertEqual(
            tuple(model.menu_number for model in DLY_MODELS),
            tuple(range(1, 18)),
        )

    def test_all_dly_models_use_selector_0b(self) -> None:
        self.assertEqual(
            {model.secondary_selector for model in DLY_MODELS},
            {0x0B},
        )

    def test_all_dly_same_class_checksums(self) -> None:
        for model, checksum in zip(
            DLY_MODELS,
            self.EXPECTED_SAME_CLASS_CHECKSUMS,
            strict=True,
        ):
            with self.subTest(model=model.name):
                packet = bytes(
                    build_set_effect_model_message(
                        slot_number=11,
                        class_id=DLY_CLASS_ID,
                        model_id=model.model_id,
                        secondary_selector=model.secondary_selector,
                    ).bin()
                )
                self.assertEqual(packet[MODEL_FLAG_INDEX], 0x00)
                self.assertEqual(packet[MODEL_SELECTOR_INDEX], 0x0B)
                self.assertEqual(packet[MODEL_CHECKSUM_INDEX], checksum)

    def test_replace_warm_slot_11_matches_capture(self) -> None:
        model = DLY_MODELS[0]
        packet = full_message_bytes(
            build_replace_effect_message(
                slot_number=11,
                class_id=DLY_CLASS_ID,
                model_id=model.model_id,
                secondary_selector=model.secondary_selector,
            )
        )
        self.assertEqual(packet[EFFECT_INSTANCE_FLAG_INDEX], 0x00)
        self.assertEqual(packet[SECONDARY_SELECTOR_INDEX], 0x0B)
        self.assertEqual(packet[CHECKSUM_INDEX], 0x4F)

    def test_add_warm_slot_12(self) -> None:
        model = DLY_MODELS[0]
        packet = full_message_bytes(
            build_add_effect_message(
                slot_number=12,
                class_id=DLY_CLASS_ID,
                model_id=model.model_id,
                secondary_selector=model.secondary_selector,
            )
        )
        self.assertEqual(packet[EFFECT_INSTANCE_FLAG_INDEX], 0x00)
        self.assertEqual(packet[SECONDARY_SELECTOR_INDEX], 0x0B)
        self.assertEqual(packet[CHECKSUM_INDEX], 0x64)

    def test_add_pure_slot_12(self) -> None:
        dly_class = find_effect_class("DLY")
        model = find_effect_model(dly_class, "PURE")
        packet = full_message_bytes(
            build_add_effect_message(
                slot_number=12,
                class_id=DLY_CLASS_ID,
                model_id=model.model_id,
                secondary_selector=model.secondary_selector,
            )
        )
        self.assertEqual(packet[SECONDARY_SELECTOR_INDEX], 0x0B)
        self.assertEqual(packet[CHECKSUM_INDEX], 0x63)

    def test_find_dly_models(self) -> None:
        dly_class = find_effect_class("DLY")
        self.assertEqual(find_effect_model(dly_class, "1").name, "WARM")
        self.assertEqual(find_effect_model(dly_class, "PURE").model_id, 0x00)
        self.assertEqual(
            find_effect_model(dly_class, "ICE DELAY").model_id,
            0x2C,
        )


if __name__ == "__main__":
    unittest.main()
