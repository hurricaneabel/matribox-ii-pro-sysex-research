from __future__ import annotations

import unittest

from tools.commands.effect_chain import (
    ADD_TEMPLATE_HEX,
    CHECKSUM_INDEX,
    DESTINATION_SLOT_HIGH_INDEX,
    DESTINATION_SLOT_LOW_INDEX,
    ENABLED_HIGH_INDEX,
    ENABLED_LOW_INDEX,
    FREQ_MODELS,
    MODEL_HIGH_INDEX,
    MODEL_LOW_INDEX,
    REMOVE_TEMPLATE_HEX,
    SOURCE_SLOT_HIGH_INDEX,
    SOURCE_SLOT_LOW_INDEX,
    build_add_effect_message,
    build_remove_effect_message,
    calculate_checksum,
    find_freq_model,
    full_message_bytes,
)


class EffectChainTests(unittest.TestCase):
    def test_templates_have_60_bytes(self) -> None:
        self.assertEqual(
            len(bytes.fromhex(ADD_TEMPLATE_HEX)),
            60,
        )
        self.assertEqual(
            len(bytes.fromhex(REMOVE_TEMPLATE_HEX)),
            60,
        )

    def test_freq_model_ids(self) -> None:
        self.assertEqual(
            {
                model.name: model.model_id
                for model in FREQ_MODELS
            },
            {
                "Filter": 0x19,
                "Octaver": 0x21,
                "Dual Melody": 0x23,
                "Pitch": 0x24,
                "Harmony D": 0x4E,
                "Pitch S": 0x55,
                "Ring Mod": 0x2F,
                "Tape Mod": 0x33,
            },
        )

    def test_find_model(self) -> None:
        self.assertEqual(
            find_freq_model("2").model_id,
            0x21,
        )
        self.assertEqual(
            find_freq_model("filter").model_id,
            0x19,
        )
        self.assertEqual(
            find_freq_model("0x4e").name,
            "Harmony D",
        )

    def test_add_filter_slot_11(self) -> None:
        packet = full_message_bytes(
            build_add_effect_message(
                slot_number=11,
                model_id=0x19,
            )
        )

        self.assertEqual(
            packet[SOURCE_SLOT_HIGH_INDEX:SOURCE_SLOT_LOW_INDEX + 1],
            bytes((0x0F, 0x0F)),
        )
        self.assertEqual(
            packet[DESTINATION_SLOT_HIGH_INDEX:DESTINATION_SLOT_LOW_INDEX + 1],
            bytes((0x00, 0x0A)),
        )
        self.assertEqual(
            packet[ENABLED_HIGH_INDEX:ENABLED_LOW_INDEX + 1],
            bytes((0x00, 0x01)),
        )
        self.assertEqual(
            packet[MODEL_HIGH_INDEX:MODEL_LOW_INDEX + 1],
            bytes((0x01, 0x09)),
        )
        self.assertEqual(
            packet[CHECKSUM_INDEX],
            0x5A,
        )
        self.assertEqual(
            calculate_checksum(list(packet)),
            0x5A,
        )

    def test_add_octaver_slot_11(self) -> None:
        packet = full_message_bytes(
            build_add_effect_message(
                slot_number=11,
                model_id=0x21,
            )
        )

        self.assertEqual(
            packet[MODEL_HIGH_INDEX:MODEL_LOW_INDEX + 1],
            bytes((0x02, 0x01)),
        )
        self.assertEqual(
            packet[CHECKSUM_INDEX],
            0x53,
        )

    def test_add_filter_slot_12(self) -> None:
        packet = full_message_bytes(
            build_add_effect_message(
                slot_number=12,
                model_id=0x19,
            )
        )

        self.assertEqual(
            packet[DESTINATION_SLOT_HIGH_INDEX:DESTINATION_SLOT_LOW_INDEX + 1],
            bytes((0x00, 0x0B)),
        )
        self.assertEqual(
            packet[CHECKSUM_INDEX],
            0x5B,
        )

    def test_remove_slot_11(self) -> None:
        packet = full_message_bytes(
            build_remove_effect_message(
                slot_number=11
            )
        )

        self.assertEqual(
            packet[SOURCE_SLOT_HIGH_INDEX:SOURCE_SLOT_LOW_INDEX + 1],
            bytes((0x00, 0x0A)),
        )
        self.assertEqual(
            packet[DESTINATION_SLOT_HIGH_INDEX:DESTINATION_SLOT_LOW_INDEX + 1],
            bytes((0x0F, 0x0F)),
        )
        self.assertEqual(
            packet[CHECKSUM_INDEX],
            0x4E,
        )

    def test_remove_slot_12(self) -> None:
        packet = full_message_bytes(
            build_remove_effect_message(
                slot_number=12
            )
        )

        self.assertEqual(
            packet[SOURCE_SLOT_HIGH_INDEX:SOURCE_SLOT_LOW_INDEX + 1],
            bytes((0x00, 0x0B)),
        )
        self.assertEqual(
            packet[CHECKSUM_INDEX],
            0x4F,
        )

    def test_all_slots_encode_zero_based(self) -> None:
        for slot_number in range(1, 13):
            with self.subTest(
                slot_number=slot_number
            ):
                packet = full_message_bytes(
                    build_add_effect_message(
                        slot_number=slot_number,
                        model_id=0x19,
                    )
                )

                self.assertEqual(
                    packet[
                        DESTINATION_SLOT_HIGH_INDEX:
                        DESTINATION_SLOT_LOW_INDEX + 1
                    ],
                    bytes((0x00, slot_number - 1)),
                )

    def test_reject_invalid_slots(self) -> None:
        for slot_number in (0, 13):
            with self.subTest(
                slot_number=slot_number
            ):
                with self.assertRaises(
                    ValueError
                ):
                    build_add_effect_message(
                        slot_number=slot_number,
                        model_id=0x19,
                    )

                with self.assertRaises(
                    ValueError
                ):
                    build_remove_effect_message(
                        slot_number=slot_number
                    )


if __name__ == "__main__":
    unittest.main()
