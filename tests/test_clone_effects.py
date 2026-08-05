"""Testes da integração das dez posições da classe CLONE."""

from __future__ import annotations

import unittest

from tools.commands.effect_catalog import (
    CLONE_CLASS_ID,
    CLONE_MODELS,
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


class CloneIntegrationTests(unittest.TestCase):
    """Valida as dez posições CLONE capturadas e testadas fisicamente."""

    EXPECTED_MODELS = tuple(
        (f"CLONE {menu_number}", model_id, 0x0F)
        for menu_number, model_id in enumerate(range(0x00, 0x0A), start=1)
    )

    EXPECTED_SAME_CLASS_CHECKSUMS = tuple(range(0x49, 0x53))

    def test_clone_class_id_and_menu(self) -> None:
        self.assertEqual(CLONE_CLASS_ID, 0x0B)
        self.assertEqual(find_effect_class("CLONE").class_id, 0x0B)
        self.assertEqual(find_effect_class("12").name, "CLONE")

    def test_clone_catalog_has_10_positions(self) -> None:
        self.assertEqual(len(CLONE_MODELS), 10)

    def test_clone_mapping_and_order(self) -> None:
        self.assertEqual(
            tuple(
                (model.name, model.model_id, model.secondary_selector)
                for model in CLONE_MODELS
            ),
            self.EXPECTED_MODELS,
        )

    def test_clone_menu_numbers_are_sequential(self) -> None:
        self.assertEqual(
            tuple(model.menu_number for model in CLONE_MODELS),
            tuple(range(1, 11)),
        )

    def test_clone_model_ids_are_sequential(self) -> None:
        self.assertEqual(
            tuple(model.model_id for model in CLONE_MODELS),
            tuple(range(0x00, 0x0A)),
        )

    def test_all_clone_positions_use_selector_0f(self) -> None:
        self.assertEqual(
            {model.secondary_selector for model in CLONE_MODELS},
            {0x0F},
        )

    def test_all_clone_same_class_checksums(self) -> None:
        for model, checksum in zip(
            CLONE_MODELS,
            self.EXPECTED_SAME_CLASS_CHECKSUMS,
            strict=True,
        ):
            with self.subTest(model=model.name):
                packet = bytes(
                    build_set_effect_model_message(
                        slot_number=11,
                        class_id=CLONE_CLASS_ID,
                        model_id=model.model_id,
                        secondary_selector=model.secondary_selector,
                    ).bin()
                )
                self.assertEqual(packet[MODEL_FLAG_INDEX], 0x00)
                self.assertEqual(packet[MODEL_SELECTOR_INDEX], 0x0F)
                self.assertEqual(packet[MODEL_CHECKSUM_INDEX], checksum)

    def test_replace_clone_1_slot_11_matches_capture(self) -> None:
        model = CLONE_MODELS[0]
        packet = full_message_bytes(
            build_replace_effect_message(
                slot_number=11,
                class_id=CLONE_CLASS_ID,
                model_id=model.model_id,
                secondary_selector=model.secondary_selector,
            )
        )
        self.assertEqual(packet[EFFECT_INSTANCE_FLAG_INDEX], 0x00)
        self.assertEqual(packet[SECONDARY_SELECTOR_INDEX], 0x0F)
        self.assertEqual(packet[CHECKSUM_INDEX], 0x54)

    def test_add_clone_1_and_clone_10_slot_12(self) -> None:
        expected = {
            "CLONE 1": 0x69,
            "CLONE 10": 0x72,
        }

        for name, checksum in expected.items():
            with self.subTest(position=name):
                model = find_effect_model(find_effect_class("CLONE"), name)
                packet = full_message_bytes(
                    build_add_effect_message(
                        slot_number=12,
                        class_id=CLONE_CLASS_ID,
                        model_id=model.model_id,
                        secondary_selector=model.secondary_selector,
                    )
                )
                self.assertEqual(packet[EFFECT_INSTANCE_FLAG_INDEX], 0x00)
                self.assertEqual(packet[SECONDARY_SELECTOR_INDEX], 0x0F)
                self.assertEqual(packet[CHECKSUM_INDEX], checksum)

    def test_find_clone_positions(self) -> None:
        clone_class = find_effect_class("CLONE")
        self.assertEqual(find_effect_model(clone_class, "1").name, "CLONE 1")
        self.assertEqual(find_effect_model(clone_class, "CLONE 10").model_id, 0x09)
        self.assertEqual(find_effect_model(clone_class, "0x05").name, "CLONE 6")


if __name__ == "__main__":
    unittest.main()
