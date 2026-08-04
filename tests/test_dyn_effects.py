"""Testes da integração da classe DYN."""

from __future__ import annotations

import unittest

from tools.commands.effect_catalog import (
    DYN_CLASS_ID,
    DYN_MODELS,
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
    full_message_bytes,
)
from tools.commands.effect_model import (
    CHECKSUM_INDEX as MODEL_CHECKSUM_INDEX,
    SECONDARY_SELECTOR_INDEX as MODEL_SELECTOR_INDEX,
    build_set_effect_model_message,
)


class DynIntegrationTests(unittest.TestCase):
    """Valida IDs, seletores e checksums da classe DYN."""

    def test_dyn_class_id(self) -> None:
        self.assertEqual(
            DYN_CLASS_ID,
            0x00,
        )
        self.assertEqual(
            find_effect_class("DYN").class_id,
            0x00,
        )
        self.assertEqual(
            find_effect_class("3").name,
            "DYN",
        )

    def test_dyn_model_catalog(self) -> None:
        observed = {
            model.name: (
                model.model_id,
                model.secondary_selector,
            )
            for model in DYN_MODELS
        }

        self.assertEqual(
            observed,
            {
                "COMP1": (0x00, 0x00),
                "COMP2": (0x01, 0x00),
                "COMP3": (0x03, 0x00),
                "M-BOOST": (0x14, 0x00),
                "E-BOOST": (0x1A, 0x00),
                "AC-BOOST": (0x0A, 0x00),
                "BB-BOOST": (0x0B, 0x00),
                "RC-BOOST": (0x0C, 0x00),
                "FAT BOOST": (0x19, 0x00),
                "AC WOODY": (0x00, 0x01),
                "AC SIM": (0x01, 0x01),
                "GATE 1": (0x1B, 0x00),
                "GATE 2": (0x1D, 0x00),
                "GATE 3": (0x21, 0x00),
            },
        )

    def test_dyn_lookup_by_menu_and_name(self) -> None:
        dyn_class = find_effect_class(
            "DYN"
        )

        self.assertEqual(
            find_effect_model(
                dyn_class,
                "10",
            ).name,
            "AC WOODY",
        )
        self.assertEqual(
            find_effect_model(
                dyn_class,
                "gate 3",
            ).model_id,
            0x21,
        )

    def test_ambiguous_dyn_model_id_is_rejected(self) -> None:
        dyn_class = find_effect_class(
            "DYN"
        )

        with self.assertRaises(
            ValueError
        ):
            find_effect_model(
                dyn_class,
                "0x00",
            )

    def test_add_comp1_slot_12(self) -> None:
        packet = full_message_bytes(
            build_add_effect_message(
                slot_number=12,
                class_id=DYN_CLASS_ID,
                model_id=0x00,
                secondary_selector=0x00,
            )
        )

        self.assertEqual(
            packet[CLASS_HIGH_INDEX:CLASS_LOW_INDEX + 1],
            bytes((0x00, 0x00)),
        )
        self.assertEqual(
            packet[MODEL_HIGH_INDEX:MODEL_LOW_INDEX + 1],
            bytes((0x00, 0x00)),
        )
        self.assertEqual(
            packet[SECONDARY_SELECTOR_INDEX],
            0x00,
        )
        self.assertEqual(
            packet[CHECKSUM_INDEX],
            0x4F,
        )

    def test_add_ac_woody_slot_12(self) -> None:
        packet = full_message_bytes(
            build_add_effect_message(
                slot_number=12,
                class_id=DYN_CLASS_ID,
                model_id=0x00,
                secondary_selector=0x01,
            )
        )

        self.assertEqual(
            packet[SECONDARY_SELECTOR_INDEX],
            0x01,
        )
        self.assertEqual(
            packet[CHECKSUM_INDEX],
            0x50,
        )

    def test_comp1_and_ac_woody_are_distinct(self) -> None:
        comp1 = full_message_bytes(
            build_add_effect_message(
                slot_number=12,
                class_id=DYN_CLASS_ID,
                model_id=0x00,
                secondary_selector=0x00,
            )
        )
        ac_woody = full_message_bytes(
            build_add_effect_message(
                slot_number=12,
                class_id=DYN_CLASS_ID,
                model_id=0x00,
                secondary_selector=0x01,
            )
        )

        self.assertNotEqual(
            comp1,
            ac_woody,
        )
        self.assertEqual(
            comp1[MODEL_HIGH_INDEX:MODEL_LOW_INDEX + 1],
            ac_woody[MODEL_HIGH_INDEX:MODEL_LOW_INDEX + 1],
        )

    def test_all_dyn_same_class_checksums(self) -> None:
        expected_checksums = {
            "COMP1": 0x2F,
            "COMP2": 0x30,
            "COMP3": 0x32,
            "M-BOOST": 0x34,
            "E-BOOST": 0x3A,
            "AC-BOOST": 0x39,
            "BB-BOOST": 0x3A,
            "RC-BOOST": 0x3B,
            "FAT BOOST": 0x39,
            "AC WOODY": 0x30,
            "AC SIM": 0x31,
            "GATE 1": 0x3B,
            "GATE 2": 0x3D,
            "GATE 3": 0x32,
        }

        for model in DYN_MODELS:
            with self.subTest(
                model=model.name
            ):
                packet = bytes(
                    build_set_effect_model_message(
                        slot_number=11,
                        class_id=DYN_CLASS_ID,
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

    def test_default_selector_remains_compatible(self) -> None:
        packet = bytes(
            build_set_effect_model_message(
                slot_number=11,
                class_id=DYN_CLASS_ID,
                model_id=0x00,
            ).bin()
        )

        self.assertEqual(
            packet[MODEL_SELECTOR_INDEX],
            0x00,
        )
        self.assertEqual(
            packet[MODEL_CHECKSUM_INDEX],
            0x2F,
        )

    def test_dyn_catalog_size(self) -> None:
        self.assertEqual(
            len(DYN_MODELS),
            14,
        )


if __name__ == "__main__":
    unittest.main()
