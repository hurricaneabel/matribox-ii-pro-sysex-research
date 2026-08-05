"""Testes da integração da classe RVB."""

from __future__ import annotations

import unittest

from tools.commands.effect_catalog import (
    RVB_CLASS_ID,
    RVB_MODELS,
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


class RvbIntegrationTests(unittest.TestCase):
    """Valida os 12 modelos RVB capturados e testados fisicamente."""

    EXPECTED_MODELS = (
        ("STUDIO", 0x0B, 0x0C),
        ("CLUB", 0x0C, 0x0C),
        ("ROOM", 0x00, 0x0C),
        ("HALL", 0x01, 0x0C),
        ("CHURCH", 0x02, 0x0C),
        ("PLATE", 0x03, 0x0C),
        ("SPRING", 0x04, 0x0C),
        ("SKY", 0x06, 0x0C),
        ("SEA", 0x07, 0x0C),
        ("MOD REVERB", 0x08, 0x0C),
        ("SHIMMER", 0x09, 0x0C),
        ("HAZE", 0x15, 0x0C),
    )

    EXPECTED_SAME_CLASS_CHECKSUMS = (
        0x50, 0x51, 0x45, 0x46, 0x47, 0x48,
        0x49, 0x4B, 0x4C, 0x4D, 0x4E, 0x4B,
    )

    def test_rvb_class_id_and_menu(self) -> None:
        self.assertEqual(RVB_CLASS_ID, 0x0A)
        self.assertEqual(find_effect_class("RVB").class_id, 0x0A)
        self.assertEqual(find_effect_class("11").name, "RVB")

    def test_rvb_catalog_has_12_models(self) -> None:
        self.assertEqual(len(RVB_MODELS), 12)

    def test_rvb_model_mapping_and_order(self) -> None:
        self.assertEqual(
            tuple(
                (model.name, model.model_id, model.secondary_selector)
                for model in RVB_MODELS
            ),
            self.EXPECTED_MODELS,
        )

    def test_rvb_menu_numbers_are_sequential(self) -> None:
        self.assertEqual(
            tuple(model.menu_number for model in RVB_MODELS),
            tuple(range(1, 13)),
        )

    def test_all_rvb_models_use_selector_0c(self) -> None:
        self.assertEqual(
            {model.secondary_selector for model in RVB_MODELS},
            {0x0C},
        )

    def test_all_rvb_same_class_checksums(self) -> None:
        for model, checksum in zip(
            RVB_MODELS,
            self.EXPECTED_SAME_CLASS_CHECKSUMS,
            strict=True,
        ):
            with self.subTest(model=model.name):
                packet = bytes(
                    build_set_effect_model_message(
                        slot_number=11,
                        class_id=RVB_CLASS_ID,
                        model_id=model.model_id,
                        secondary_selector=model.secondary_selector,
                    ).bin()
                )
                self.assertEqual(packet[MODEL_FLAG_INDEX], 0x00)
                self.assertEqual(packet[MODEL_SELECTOR_INDEX], 0x0C)
                self.assertEqual(packet[MODEL_CHECKSUM_INDEX], checksum)

    def test_replace_studio_slot_11_matches_capture(self) -> None:
        model = RVB_MODELS[0]
        packet = full_message_bytes(
            build_replace_effect_message(
                slot_number=11,
                class_id=RVB_CLASS_ID,
                model_id=model.model_id,
                secondary_selector=model.secondary_selector,
            )
        )
        self.assertEqual(packet[EFFECT_INSTANCE_FLAG_INDEX], 0x00)
        self.assertEqual(packet[SECONDARY_SELECTOR_INDEX], 0x0C)
        self.assertEqual(packet[CHECKSUM_INDEX], 0x5B)

    def test_add_studio_slot_12(self) -> None:
        model = RVB_MODELS[0]
        packet = full_message_bytes(
            build_add_effect_message(
                slot_number=12,
                class_id=RVB_CLASS_ID,
                model_id=model.model_id,
                secondary_selector=model.secondary_selector,
            )
        )
        self.assertEqual(packet[EFFECT_INSTANCE_FLAG_INDEX], 0x00)
        self.assertEqual(packet[SECONDARY_SELECTOR_INDEX], 0x0C)
        self.assertEqual(packet[CHECKSUM_INDEX], 0x70)

    def test_add_room_and_haze_slot_12(self) -> None:
        rvb_class = find_effect_class("RVB")
        expected = {
            "ROOM": 0x65,
            "HAZE": 0x6B,
        }

        for name, checksum in expected.items():
            with self.subTest(model=name):
                model = find_effect_model(rvb_class, name)
                packet = full_message_bytes(
                    build_add_effect_message(
                        slot_number=12,
                        class_id=RVB_CLASS_ID,
                        model_id=model.model_id,
                        secondary_selector=model.secondary_selector,
                    )
                )
                self.assertEqual(packet[SECONDARY_SELECTOR_INDEX], 0x0C)
                self.assertEqual(packet[CHECKSUM_INDEX], checksum)

    def test_find_rvb_models(self) -> None:
        rvb_class = find_effect_class("RVB")
        self.assertEqual(find_effect_model(rvb_class, "1").name, "STUDIO")
        self.assertEqual(find_effect_model(rvb_class, "ROOM").model_id, 0x00)
        self.assertEqual(find_effect_model(rvb_class, "HAZE").model_id, 0x15)

if __name__ == "__main__":
    unittest.main()
