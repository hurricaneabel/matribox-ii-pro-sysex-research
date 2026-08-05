"""Testes da integração dos quatro blocos especiais da cadeia."""

from __future__ import annotations

import unittest

from tools.commands.effect_catalog import (
    EFFECT_CLASSES,
    FX_LOOP_CLASS_ID,
    FX_LOOP_MODELS,
    FX_RETURN_CLASS_ID,
    FX_RETURN_MODELS,
    FX_SEND_CLASS_ID,
    FX_SEND_MODELS,
    VOL_CLASS_ID,
    VOL_MODELS,
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


class SpecialBlockIntegrationTests(unittest.TestCase):
    """Valida FX LOOP, SND, RTN e VOL capturados e testados fisicamente."""

    EXPECTED_BLOCKS = (
        ("FX LOOP", FX_LOOP_CLASS_ID, "FX LOOP", 0x00, 0x4C, 0x61),
        ("FX SEND", FX_SEND_CLASS_ID, "SND", 0x01, 0x4E, 0x63),
        ("FX RETURN", FX_RETURN_CLASS_ID, "RTN", 0x02, 0x50, 0x65),
        ("VOL", VOL_CLASS_ID, "VOL", 0x03, 0x52, 0x67),
    )

    def test_special_class_ids(self) -> None:
        self.assertEqual(
            (
                FX_LOOP_CLASS_ID,
                FX_SEND_CLASS_ID,
                FX_RETURN_CLASS_ID,
                VOL_CLASS_ID,
            ),
            (0x0C, 0x0D, 0x0E, 0x0F),
        )

    def test_special_class_menu_positions(self) -> None:
        self.assertEqual(find_effect_class("13").name, "FX LOOP")
        self.assertEqual(find_effect_class("14").name, "FX SEND")
        self.assertEqual(find_effect_class("15").name, "FX RETURN")
        self.assertEqual(find_effect_class("16").name, "VOL")

    def test_each_special_class_has_one_model(self) -> None:
        self.assertEqual(
            tuple(
                len(models)
                for models in (
                    FX_LOOP_MODELS,
                    FX_SEND_MODELS,
                    FX_RETURN_MODELS,
                    VOL_MODELS,
                )
            ),
            (1, 1, 1, 1),
        )

    def test_special_model_mapping(self) -> None:
        self.assertEqual(
            tuple(
                (class_name, model_name, model_id)
                for class_name, _class_id, model_name, model_id, _replace, _add
                in self.EXPECTED_BLOCKS
            ),
            (
                ("FX LOOP", "FX LOOP", 0x00),
                ("FX SEND", "SND", 0x01),
                ("FX RETURN", "RTN", 0x02),
                ("VOL", "VOL", 0x03),
            ),
        )

    def test_all_special_models_use_selector_06(self) -> None:
        selectors = {
            model.secondary_selector
            for models in (
                FX_LOOP_MODELS,
                FX_SEND_MODELS,
                FX_RETURN_MODELS,
                VOL_MODELS,
            )
            for model in models
        }
        self.assertEqual(selectors, {0x06})

    def test_special_model_ids_follow_capture(self) -> None:
        self.assertEqual(
            (
                FX_LOOP_MODELS[0].model_id,
                FX_SEND_MODELS[0].model_id,
                FX_RETURN_MODELS[0].model_id,
                VOL_MODELS[0].model_id,
            ),
            (0x00, 0x01, 0x02, 0x03),
        )

    def test_replace_checksums_match_captures(self) -> None:
        for class_name, class_id, model_name, model_id, checksum, _add in (
            self.EXPECTED_BLOCKS
        ):
            with self.subTest(block=class_name):
                packet = full_message_bytes(
                    build_replace_effect_message(
                        slot_number=11,
                        class_id=class_id,
                        model_id=model_id,
                        secondary_selector=0x06,
                    )
                )
                self.assertEqual(packet[EFFECT_INSTANCE_FLAG_INDEX], 0x00)
                self.assertEqual(packet[SECONDARY_SELECTOR_INDEX], 0x06)
                self.assertEqual(packet[CHECKSUM_INDEX], checksum)
                self.assertEqual(
                    find_effect_model(find_effect_class(class_name), "1").name,
                    model_name,
                )

    def test_add_checksums_slot_12(self) -> None:
        for class_name, class_id, _model_name, model_id, _replace, checksum in (
            self.EXPECTED_BLOCKS
        ):
            with self.subTest(block=class_name):
                packet = full_message_bytes(
                    build_add_effect_message(
                        slot_number=12,
                        class_id=class_id,
                        model_id=model_id,
                        secondary_selector=0x06,
                    )
                )
                self.assertEqual(packet[EFFECT_INSTANCE_FLAG_INDEX], 0x00)
                self.assertEqual(packet[SECONDARY_SELECTOR_INDEX], 0x06)
                self.assertEqual(packet[CHECKSUM_INDEX], checksum)

    def test_lookup_by_class_and_model_names(self) -> None:
        self.assertEqual(find_effect_class("FX LOOP").class_id, 0x0C)
        self.assertEqual(find_effect_model(find_effect_class("FX SEND"), "SND").model_id, 0x01)
        self.assertEqual(find_effect_model(find_effect_class("FX RETURN"), "RTN").model_id, 0x02)
        self.assertEqual(find_effect_model(find_effect_class("VOL"), "VOL").model_id, 0x03)

    def test_catalog_totals_after_special_blocks(self) -> None:
        self.assertEqual(len(EFFECT_CLASSES), 16)
        self.assertEqual(sum(len(item.models) for item in EFFECT_CLASSES), 267)


if __name__ == "__main__":
    unittest.main()
