"""Testes da integração da classe EQ."""

from __future__ import annotations

import unittest

from tools.commands.effect_catalog import (
    EQ_CLASS_ID,
    EQ_MODELS,
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


class EqIntegrationTests(unittest.TestCase):
    """Valida os cinco modelos confirmados da classe EQ."""

    def test_eq_class_id_and_menu(self) -> None:
        self.assertEqual(EQ_CLASS_ID, 0x07)
        self.assertEqual(
            find_effect_class("EQ").class_id,
            0x07,
        )
        self.assertEqual(
            find_effect_class("8").name,
            "EQ",
        )

    def test_eq_catalog_has_five_models(self) -> None:
        self.assertEqual(len(EQ_MODELS), 5)

    def test_eq_model_mapping(self) -> None:
        self.assertEqual(
            tuple(
                (model.name, model.model_id)
                for model in EQ_MODELS
            ),
            (
                ("GUITAR EQ 1", 0x35),
                ("GUITAR EQ 2", 0x36),
                ("BASS EQ 1", 0x39),
                ("BASS EQ 2", 0x3A),
                ("CALIF EQ", 0x3C),
            ),
        )

    def test_all_eq_models_use_selector_01(self) -> None:
        self.assertEqual(
            {
                model.secondary_selector
                for model in EQ_MODELS
            },
            {0x01},
        )

    def test_all_eq_same_class_checksums(self) -> None:
        expected = (0x3F, 0x40, 0x43, 0x44, 0x46)

        for model, checksum in zip(
            EQ_MODELS,
            expected,
            strict=True,
        ):
            with self.subTest(model=model.name):
                packet = bytes(
                    build_set_effect_model_message(
                        slot_number=11,
                        class_id=EQ_CLASS_ID,
                        model_id=model.model_id,
                        secondary_selector=(
                            model.secondary_selector
                        ),
                    ).bin()
                )

                self.assertEqual(
                    packet[MODEL_FLAG_INDEX],
                    0x00,
                )
                self.assertEqual(
                    packet[MODEL_SELECTOR_INDEX],
                    0x01,
                )
                self.assertEqual(
                    packet[MODEL_CHECKSUM_INDEX],
                    checksum,
                )

    def test_add_guitar_eq_1_slot_12(self) -> None:
        model = EQ_MODELS[0]
        packet = full_message_bytes(
            build_add_effect_message(
                slot_number=12,
                class_id=EQ_CLASS_ID,
                model_id=model.model_id,
                secondary_selector=(
                    model.secondary_selector
                ),
            )
        )

        self.assertEqual(
            packet[EFFECT_INSTANCE_FLAG_INDEX],
            0x00,
        )
        self.assertEqual(
            packet[SECONDARY_SELECTOR_INDEX],
            0x01,
        )
        self.assertEqual(
            packet[CHECKSUM_INDEX],
            0x5F,
        )

    def test_add_calif_eq_slot_12(self) -> None:
        model = EQ_MODELS[-1]
        packet = full_message_bytes(
            build_add_effect_message(
                slot_number=12,
                class_id=EQ_CLASS_ID,
                model_id=model.model_id,
                secondary_selector=(
                    model.secondary_selector
                ),
            )
        )

        self.assertEqual(
            packet[CHECKSUM_INDEX],
            0x66,
        )

    def test_replace_guitar_eq_1_slot_11(self) -> None:
        model = EQ_MODELS[0]
        packet = full_message_bytes(
            build_replace_effect_message(
                slot_number=11,
                class_id=EQ_CLASS_ID,
                model_id=model.model_id,
                secondary_selector=(
                    model.secondary_selector
                ),
            )
        )

        self.assertEqual(
            packet[CHECKSUM_INDEX],
            0x4A,
        )

    def test_find_eq_models(self) -> None:
        eq_class = find_effect_class("EQ")

        self.assertEqual(
            find_effect_model(eq_class, "1").name,
            "GUITAR EQ 1",
        )
        self.assertEqual(
            find_effect_model(
                eq_class,
                "CALIF EQ",
            ).model_id,
            0x3C,
        )


if __name__ == "__main__":
    unittest.main()
