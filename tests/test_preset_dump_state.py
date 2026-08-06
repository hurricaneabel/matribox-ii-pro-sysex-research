"""Testes do caminho não destrutivo de leitura da cadeia pelo dump."""

from __future__ import annotations

import unittest
from pathlib import Path

import mido

from tools.commands.preset_dump_state import (
    PRESET_DUMP_QUERY_TEMPLATE,
    PresetDumpCollector,
    PresetDumpStateError,
    build_preset_dump_query,
    decode_chain_state_from_preset_dump,
    decompress_preset_dump,
    extract_structural_payload_from_preset_dump,
)
from tools.commands.preset_state import calculate_protocol_checksum


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIRECTORY = (
    PROJECT_ROOT / "tests" / "fixtures" / "preset_dump_chain"
)


def encode_dump_fragment(
    block: bytes,
    offset: int,
    length: int = 100,
) -> bytes:
    payload = block[offset:offset + length]
    encoded = bytearray()

    for value in payload:
        encoded.extend(((value >> 4) & 0x0F, value & 0x0F))

    return bytes(
        (
            0xF0,
            0x21,
            0x25,
            0x4D,
            0x50,
            0x00,
            0x00,
            0x00,
            0x00,
            len(block) & 0x7F,
            (len(block) >> 7) & 0x7F,
            offset & 0x7F,
            (offset >> 7) & 0x7F,
        )
    ) + bytes(encoded) + bytes((0xF7,))


def make_dump_fragments(block: bytes) -> list[bytes]:
    return [
        encode_dump_fragment(block, offset)
        for offset in range(0, len(block), 100)
    ]


class PresetDumpQueryTests(unittest.TestCase):
    def test_45b_matches_validated_template(self) -> None:
        self.assertEqual(
            build_preset_dump_query("45B"),
            PRESET_DUMP_QUERY_TEMPLATE,
        )

    def test_56a_uses_expected_address_and_checksum(self) -> None:
        query = build_preset_dump_query("56A")

        self.assertEqual(query[31:33], bytes((0x0D, 0x0C)))
        self.assertEqual(
            query[7],
            calculate_protocol_checksum(query),
        )


class PresetDumpCollectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = (
            FIXTURE_DIRECTORY / "56A_GATE3_ON.bin"
        ).read_bytes()
        cls.fragments = make_dump_fragments(cls.fixture)

    def test_reconstructs_out_of_order_fragments(self) -> None:
        collector = PresetDumpCollector()
        result = collector.feed_many(reversed(self.fragments))

        self.assertEqual(result, self.fixture)

    def test_duplicate_fragment_adds_no_new_bytes(self) -> None:
        collector = PresetDumpCollector()
        first = collector.feed(self.fragments[0])
        duplicate = collector.feed(self.fragments[0])

        self.assertGreater(first.new_bytes, 0)
        self.assertEqual(duplicate.new_bytes, 0)

    def test_ignores_global_sized_fragment(self) -> None:
        large_block = bytes.fromhex("01 00 00 10") + bytes(3168)
        fragment = encode_dump_fragment(large_block, 0)
        update = PresetDumpCollector().feed(fragment)

        self.assertFalse(update.accepted)


class PresetDumpChainDecodeTests(unittest.TestCase):
    def read(self, name: str) -> bytes:
        return (FIXTURE_DIRECTORY / name).read_bytes()

    def test_gate3_on_exposes_complete_saved_chain(self) -> None:
        state = decode_chain_state_from_preset_dump(
            self.read("56A_GATE3_ON.bin")
        )

        self.assertEqual(state.human_slots, (1, 2, 3, 4, 5))
        self.assertEqual(
            tuple(
                (
                    record.class_id,
                    record.model_id,
                    record.secondary_selector,
                    record.enabled,
                )
                for record in state.visual_effect_records
            ),
            (
                (0x00, 0x21, 0x00, True),
                (0x04, 0x01, 0x07, True),
                (0x03, 0x00, 0x03, True),
                (0x08, 0x01, 0x04, True),
                (0x09, 0x01, 0x0B, True),
            ),
        )

    def test_gate3_off_is_read_from_dump_bypass_field(self) -> None:
        state = decode_chain_state_from_preset_dump(
            self.read("56A_GATE3_OFF.bin")
        )

        self.assertFalse(state.enabled_for_internal_slot(1))
        self.assertEqual(
            state.model_for_internal_slot(1),
            0x21,
        )

    def test_filter_replacement_is_read_without_structural_write(self) -> None:
        state = decode_chain_state_from_preset_dump(
            self.read("56A_FILTER_ON.bin")
        )
        record = state.record_for_internal_slot(1)

        self.assertEqual(record.class_id, 0x01)
        self.assertEqual(record.model_id, 0x19)
        self.assertEqual(record.secondary_selector, 0x01)
        self.assertTrue(record.enabled)

    def test_decompressed_dump_and_structural_payload_sizes(self) -> None:
        decompressed, _backend = decompress_preset_dump(
            self.read("56A_GATE3_ON.bin")
        )
        structural = extract_structural_payload_from_preset_dump(
            decompressed
        )

        self.assertEqual(len(decompressed), 1211)
        self.assertEqual(len(structural), 89)
        self.assertEqual(structural[:4], bytes.fromhex("00 00 04 01"))

    def test_invalid_container_is_rejected(self) -> None:
        invalid = bytearray(self.read("56A_GATE3_ON.bin"))
        invalid[0] = 0x01

        with self.assertRaises(PresetDumpStateError):
            decode_chain_state_from_preset_dump(invalid)


if __name__ == "__main__":
    unittest.main()
