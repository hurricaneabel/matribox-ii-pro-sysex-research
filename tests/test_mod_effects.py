"""Testes da integração da classe MOD."""

from __future__ import annotations

import unittest

from tools.commands.effect_catalog import (
    MOD_CLASS_ID,
    MOD_MODELS,
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


class ModIntegrationTests(unittest.TestCase):
    """Valida os 23 modelos MOD capturados e testados fisicamente."""

    EXPECTED_MODELS = (
        ("E-CHORUS", 0x01, 0x04),
        ("D-CHORUS", 0x02, 0x04),
        ("B-CHORUS", 0x08, 0x04),
        ("M-CHORUS", 0x0F, 0x04),
        ("FLANGER", 0x11, 0x04),
        ("FLANGER N", 0x13, 0x04),
        ("TREM JET", 0x14, 0x04),
        ("BASS JET", 0x12, 0x04),
        ("VIBRATO", 0x17, 0x04),
        ("BBD ROTO", 0x15, 0x04),
        ("CE-ROTO", 0x16, 0x04),
        ("PHASER", 0x19, 0x04),
        ("BBD PHASER", 0x1A, 0x04),
        ("PHASER ST", 0x1B, 0x04),
        ("PAN PHASER", 0x1E, 0x04),
        ("VIBE", 0x1F, 0x04),
        ("U-VIBE", 0x20, 0x04),
        ("TREMOLO", 0x21, 0x04),
        ("SINE TREM", 0x26, 0x04),
        ("TRIANGULE TREM", 0x27, 0x04),
        ("BIAS TREM", 0x28, 0x04),
        ("DETUNE", 0x29, 0x01),
        ("LOFI BIT", 0x2E, 0x01),
    )

    EXPECTED_SAME_CLASS_CHECKSUMS = (
        0x3C,
        0x3D,
        0x43,
        0x4A,
        0x3D,
        0x3F,
        0x40,
        0x3E,
        0x43,
        0x41,
        0x42,
        0x45,
        0x46,
        0x47,
        0x4A,
        0x4B,
        0x3D,
        0x3E,
        0x43,
        0x44,
        0x45,
        0x43,
        0x48,
    )

    def test_mod_class_id_and_menu(self) -> None:
        self.assertEqual(MOD_CLASS_ID, 0x08)
        self.assertEqual(
            find_effect_class("MOD").class_id,
            0x08,
        )
        self.assertEqual(
            find_effect_class("9").name,
            "MOD",
        )

    def test_mod_catalog_has_23_models(self) -> None:
        self.assertEqual(len(MOD_MODELS), 23)

    def test_mod_model_mapping_and_order(self) -> None:
        self.assertEqual(
            tuple(
                (
                    model.name,
                    model.model_id,
                    model.secondary_selector,
                )
                for model in MOD_MODELS
            ),
            self.EXPECTED_MODELS,
        )

    def test_mod_menu_numbers_are_sequential(self) -> None:
        self.assertEqual(
            tuple(model.menu_number for model in MOD_MODELS),
            tuple(range(1, 24)),
        )

    def test_mod_selector_groups(self) -> None:
        self.assertEqual(
            {
                model.secondary_selector
                for model in MOD_MODELS[:21]
            },
            {0x04},
        )
        self.assertEqual(
            tuple(
                model.secondary_selector
                for model in MOD_MODELS[21:]
            ),
            (0x01, 0x01),
        )

    def test_all_mod_same_class_checksums(self) -> None:
        for model, checksum in zip(
            MOD_MODELS,
            self.EXPECTED_SAME_CLASS_CHECKSUMS,
            strict=True,
        ):
            with self.subTest(model=model.name):
                packet = bytes(
                    build_set_effect_model_message(
                        slot_number=11,
                        class_id=MOD_CLASS_ID,
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
                    model.secondary_selector,
                )
                self.assertEqual(
                    packet[MODEL_CHECKSUM_INDEX],
                    checksum,
                )

    def test_replace_e_chorus_slot_11_matches_capture(self) -> None:
        model = MOD_MODELS[0]
        packet = full_message_bytes(
            build_replace_effect_message(
                slot_number=11,
                class_id=MOD_CLASS_ID,
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
            0x04,
        )
        self.assertEqual(
            packet[CHECKSUM_INDEX],
            0x47,
        )

    def test_add_e_chorus_slot_12(self) -> None:
        model = MOD_MODELS[0]
        packet = full_message_bytes(
            build_add_effect_message(
                slot_number=12,
                class_id=MOD_CLASS_ID,
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
            0x04,
        )
        self.assertEqual(
            packet[CHECKSUM_INDEX],
            0x5C,
        )

    def test_add_detune_and_lofi_bit_use_selector_01(self) -> None:
        expected = (
            ("DETUNE", 0x63),
            ("LOFI BIT", 0x68),
        )

        mod_class = find_effect_class("MOD")

        for name, checksum in expected:
            with self.subTest(model=name):
                model = find_effect_model(
                    mod_class,
                    name,
                )
                packet = full_message_bytes(
                    build_add_effect_message(
                        slot_number=12,
                        class_id=MOD_CLASS_ID,
                        model_id=model.model_id,
                        secondary_selector=(
                            model.secondary_selector
                        ),
                    )
                )

                self.assertEqual(
                    packet[SECONDARY_SELECTOR_INDEX],
                    0x01,
                )
                self.assertEqual(
                    packet[CHECKSUM_INDEX],
                    checksum,
                )

    def test_find_mod_models(self) -> None:
        mod_class = find_effect_class("MOD")

        self.assertEqual(
            find_effect_model(mod_class, "1").name,
            "E-CHORUS",
        )
        self.assertEqual(
            find_effect_model(
                mod_class,
                "TRIANGULE TREM",
            ).model_id,
            0x27,
        )
        self.assertEqual(
            find_effect_model(
                mod_class,
                "0x2e",
            ).name,
            "LOFI BIT",
        )


if __name__ == "__main__":
    unittest.main()
