"""Testes dos modelos FREQ confirmados da Matribox II Pro."""

from __future__ import annotations

import unittest

from tools.commands.set_effect_model import (
    CHECKSUM_INDEX,
    FREQ_MODELS,
    MODEL_HIGH_INDEX,
    MODEL_LOW_INDEX,
    build_effect_model_message,
    calculate_checksum,
    find_model,
)


class EffectModelLookupTests(unittest.TestCase):
    """Valida nomes, menu e IDs dos modelos."""

    def test_all_confirmed_model_ids(self) -> None:
        expected = {
            "Filter": 0x19,
            "Octaver": 0x21,
            "Dual Melody": 0x23,
            "Pitch": 0x24,
            "Harmony D": 0x4E,
            "Pitch S": 0x55,
            "Ring Mod": 0x2F,
            "Tape Mod": 0x33,
        }

        actual = {
            model.name: model.model_id
            for model in FREQ_MODELS
        }

        self.assertEqual(
            actual,
            expected,
        )

    def test_accepts_menu_number(self) -> None:
        self.assertEqual(
            find_model("3").name,
            "Dual Melody",
        )

    def test_accepts_normalized_name(self) -> None:
        self.assertEqual(
            find_model("ring_mod").model_id,
            0x2F,
        )

    def test_accepts_hexadecimal_id(self) -> None:
        self.assertEqual(
            find_model("0x55").name,
            "Pitch S",
        )


class EffectModelPacketTests(unittest.TestCase):
    """Valida o pacote de 58 bytes e seus campos."""

    def test_builds_all_confirmed_models(self) -> None:
        for model in FREQ_MODELS:
            with self.subTest(
                model=model.name
            ):
                message = build_effect_model_message(
                    effect_position=1,
                    model_value=model.model_id,
                )

                full_message = bytes(
                    message.bin()
                )

                self.assertEqual(
                    len(full_message),
                    58,
                )

                self.assertEqual(
                    full_message[MODEL_HIGH_INDEX],
                    (model.model_id >> 4) & 0x0F,
                )

                self.assertEqual(
                    full_message[MODEL_LOW_INDEX],
                    model.model_id & 0x0F,
                )

                message_as_list = list(
                    full_message
                )

                self.assertEqual(
                    full_message[CHECKSUM_INDEX],
                    calculate_checksum(
                        message_as_list
                    ),
                )

    def test_filter_checksum_matches_capture(self) -> None:
        message = build_effect_model_message(
            effect_position=1,
            model_value="Filter",
        )

        full_message = bytes(
            message.bin()
        )

        self.assertEqual(
            full_message[CHECKSUM_INDEX],
            0x31,
        )

    def test_octaver_checksum_matches_working_command(self) -> None:
        message = build_effect_model_message(
            effect_position=1,
            model_value="Octaver",
        )

        full_message = bytes(
            message.bin()
        )

        self.assertEqual(
            full_message[CHECKSUM_INDEX],
            0x2A,
        )

    def test_rejects_unvalidated_slot(self) -> None:
        with self.assertRaises(
            ValueError
        ):
            build_effect_model_message(
                effect_position=2,
                model_value="Filter",
            )


if __name__ == "__main__":
    unittest.main()