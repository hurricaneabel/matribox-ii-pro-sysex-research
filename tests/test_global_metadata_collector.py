"""Testes da reconstrução incremental do bloco global."""

from __future__ import annotations

import unittest
from pathlib import Path

from tools.commands.global_metadata_collector import (
    FragmentAssembly,
    FragmentConflictError,
    GlobalMetadataCollector,
    GlobalMetadataFragment,
    IncompleteBlockError,
    decode_global_metadata_fragment,
    find_missing_ranges,
    is_valid_global_container,
)
from tools.commands.global_preset_metadata import (
    decode_global_preset_metadata,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_FILE = (
    PROJECT_ROOT
    / "data"
    / "fixtures"
    / "global_metadata"
    / "preset_metadata_45abc.bin"
)
FRAGMENT_PAYLOAD_SIZE = 185


def encode_fragment_message(
    block: bytes,
    offset: int,
    length: int = FRAGMENT_PAYLOAD_SIZE,
) -> bytes:
    payload = block[offset:offset + length]
    total_size = len(block)

    encoded = bytearray()
    for value in payload:
        encoded.extend(((value >> 4) & 0x0F, value & 0x0F))

    return bytes(
        (
            0xF0, 0x21, 0x25, 0x4D, 0x50,
            0x00, 0x00, 0x00, 0x00,
            total_size & 0x7F,
            (total_size >> 7) & 0x7F,
            offset & 0x7F,
            (offset >> 7) & 0x7F,
        )
    ) + bytes(encoded) + bytes((0xF7,))


def make_fixture_messages(block: bytes) -> list[bytes]:
    return [
        encode_fragment_message(block, offset)
        for offset in range(0, len(block), FRAGMENT_PAYLOAD_SIZE)
    ]


def make_fragment(
    total_size: int,
    offset: int,
    payload: bytes,
) -> GlobalMetadataFragment:
    return GlobalMetadataFragment(
        total_size=total_size,
        offset=offset,
        payload=payload,
        raw_message=b"",
    )


class FragmentDecoderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = FIXTURE_FILE.read_bytes()

    def test_decodes_real_fixture_slice(self) -> None:
        message = encode_fragment_message(self.fixture, 0)
        fragment = decode_global_metadata_fragment(message)

        self.assertIsNotNone(fragment)
        assert fragment is not None
        self.assertEqual(fragment.total_size, len(self.fixture))
        self.assertEqual(fragment.offset, 0)
        self.assertEqual(fragment.payload, self.fixture[:185])

    def test_rejects_wrong_header(self) -> None:
        message = bytearray(encode_fragment_message(self.fixture, 0))
        message[1] = 0x22
        self.assertIsNone(decode_global_metadata_fragment(message))

    def test_rejects_outgoing_direction(self) -> None:
        message = bytearray(encode_fragment_message(self.fixture, 0))
        message[8] = 0x12
        self.assertIsNone(decode_global_metadata_fragment(message))

    def test_rejects_odd_nibble_count(self) -> None:
        message = bytearray(encode_fragment_message(self.fixture, 0))
        del message[-2]
        self.assertIsNone(decode_global_metadata_fragment(message))

    def test_rejects_nibble_above_0f(self) -> None:
        message = bytearray(encode_fragment_message(self.fixture, 0))
        message[13] = 0x10
        self.assertIsNone(decode_global_metadata_fragment(message))


class FragmentAssemblyTests(unittest.TestCase):
    def test_tracks_coverage_and_missing_ranges(self) -> None:
        assembly = FragmentAssembly(10)
        assembly.add(make_fragment(10, 0, b"ABC"))
        assembly.add(make_fragment(10, 7, b"XYZ"))

        self.assertEqual(assembly.covered_bytes, 6)
        self.assertEqual(assembly.missing_ranges, ((3, 7),))
        self.assertFalse(assembly.complete)

    def test_duplicate_fragment_adds_no_new_bytes(self) -> None:
        assembly = FragmentAssembly(3)
        fragment = make_fragment(3, 0, b"ABC")

        self.assertEqual(assembly.add(fragment), 3)
        self.assertEqual(assembly.add(fragment), 0)
        self.assertEqual(assembly.fragment_count, 1)

    def test_rejects_conflicting_overlap(self) -> None:
        assembly = FragmentAssembly(4)
        assembly.add(make_fragment(4, 0, b"ABC"))

        with self.assertRaises(FragmentConflictError):
            assembly.add(make_fragment(4, 1, b"XZ"))

    def test_requires_complete_block(self) -> None:
        assembly = FragmentAssembly(4)
        assembly.add(make_fragment(4, 0, b"AB"))

        with self.assertRaises(IncompleteBlockError):
            assembly.require_complete_block()

    def test_missing_range_helper(self) -> None:
        self.assertEqual(
            find_missing_ranges(bytes((1, 0, 0, 1, 0))),
            ((1, 3), (4, 5)),
        )


class GlobalMetadataCollectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = FIXTURE_FILE.read_bytes()
        cls.messages = make_fixture_messages(cls.fixture)

    def test_fixture_uses_18_fragments(self) -> None:
        self.assertEqual(len(self.messages), 18)

    def test_reconstructs_fixture_out_of_order(self) -> None:
        collector = GlobalMetadataCollector()
        reconstructed = collector.feed_many(reversed(self.messages))
        self.assertEqual(reconstructed, self.fixture)

    def test_reconstructed_block_decodes_validated_metadata(self) -> None:
        collector = GlobalMetadataCollector()
        reconstructed = collector.feed_many(self.messages)

        self.assertIsNotNone(reconstructed)
        assert reconstructed is not None

        metadata = decode_global_preset_metadata(reconstructed)
        self.assertEqual(metadata.by_label("45A").filter_tag, "JKLMNOPQR")
        self.assertEqual(metadata.by_label("45B").name, "NOME123456789")
        self.assertEqual(metadata.by_label("45B").filter_tag, "TAG45A123")
        self.assertEqual(metadata.by_label("45C").filter_tag, "UVWXYZ789")

    def test_ignores_small_fragment_group(self) -> None:
        collector = GlobalMetadataCollector()
        small = bytes(288)
        update = collector.feed(encode_fragment_message(small, 0))

        self.assertFalse(update.accepted)
        self.assertEqual(update.total_size, 288)
        self.assertIsNone(update.global_block)

    def test_complete_non_global_block_is_not_returned(self) -> None:
        collector = GlobalMetadataCollector()
        unrelated = bytes(1_000)
        result = collector.feed_many(make_fixture_messages(unrelated))
        self.assertIsNone(result)

    def test_validates_outer_declared_size(self) -> None:
        self.assertTrue(is_valid_global_container(self.fixture))

        invalid = bytearray(self.fixture)
        invalid[4:8] = (1).to_bytes(4, "little")
        self.assertFalse(is_valid_global_container(bytes(invalid)))

    def test_reset_discards_progress(self) -> None:
        collector = GlobalMetadataCollector()
        collector.feed(self.messages[0])
        self.assertIsNotNone(collector.best_assembly())

        collector.reset()
        self.assertIsNone(collector.best_assembly())
        self.assertEqual(collector.assemblies, ())


if __name__ == "__main__":
    unittest.main()
