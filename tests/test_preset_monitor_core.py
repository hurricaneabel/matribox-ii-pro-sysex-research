"""Testes do núcleo offline do monitor de presets."""

from __future__ import annotations

import unittest
from pathlib import Path

from tools.commands.preset_monitor_core import (
    GLOBAL_METADATA_QUERY,
    SESSION_HANDSHAKE,
    PresetMonitorCore,
    build_global_metadata_query,
    build_monitor_startup_plan,
    format_monitor_snapshot,
)
from tools.commands.preset_state import (
    build_current_preset_query,
    build_select_preset,
    calculate_protocol_checksum,
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

STRUCTURAL_BASELINE_FILE = (
    PROJECT_ROOT
    / "tests"
    / "fixtures"
    / "structural_effect_state"
    / "phase15"
    / "BASELINE.bin"
)


def encode_fragment_message(
    block: bytes,
    offset: int,
    length: int = FRAGMENT_PAYLOAD_SIZE,
) -> bytes:
    payload = block[offset:offset + length]
    total_size = len(block)

    encoded = bytearray()

    for value in payload:
        encoded.extend(
            (
                (value >> 4) & 0x0F,
                value & 0x0F,
            )
        )

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
            total_size & 0x7F,
            (total_size >> 7) & 0x7F,
            offset & 0x7F,
            (offset >> 7) & 0x7F,
        )
    ) + bytes(encoded) + bytes((0xF7,))


def make_fixture_messages(
    block: bytes,
) -> list[bytes]:
    return [
        encode_fragment_message(
            block,
            offset,
        )
        for offset in range(
            0,
            len(block),
            FRAGMENT_PAYLOAD_SIZE,
        )
    ]


def make_incoming_preset_event(
    label: str,
) -> bytes:
    message = bytearray(
        build_select_preset(label)
    )

    message[8] = 0x00

    return bytes(message)


class StartupPlanTests(unittest.TestCase):
    def test_handshake_matches_validated_capture(self) -> None:
        self.assertEqual(
            SESSION_HANDSHAKE,
            bytes.fromhex(
                "F0 21 25 7E 47 50 2D 32 "
                "11 12 00 00 00 F7"
            ),
        )

    def test_global_query_matches_validated_capture(self) -> None:
        self.assertEqual(
            build_global_metadata_query(),
            GLOBAL_METADATA_QUERY,
        )

    def test_global_query_checksum_is_1d(self) -> None:
        query = build_global_metadata_query()

        self.assertEqual(query[7], 0x1D)
        self.assertEqual(
            calculate_protocol_checksum(query),
            0x1D,
        )

    def test_global_and_current_queries_are_distinct(self) -> None:
        global_query = build_global_metadata_query()
        current_query = build_current_preset_query()

        self.assertNotEqual(
            global_query,
            current_query,
        )
        self.assertEqual(
            global_query[31:33],
            bytes.fromhex("00 00"),
        )
        self.assertEqual(
            current_query[31:33],
            bytes.fromhex("00 01"),
        )

    def test_startup_plan_preserves_order_and_timing(self) -> None:
        plan = build_monitor_startup_plan()

        self.assertEqual(
            plan.handshake_repetitions,
            4,
        )
        self.assertEqual(
            plan.handshake_interval_seconds,
            0.2,
        )
        self.assertEqual(
            plan.stabilization_seconds,
            0.5,
        )
        self.assertEqual(
            len(plan.ordered_messages),
            6,
        )
        self.assertEqual(
            plan.ordered_messages[:4],
            (SESSION_HANDSHAKE,) * 4,
        )
        self.assertEqual(
            plan.ordered_messages[-2],
            build_global_metadata_query(),
        )
        self.assertEqual(
            plan.ordered_messages[-1],
            build_current_preset_query(),
        )


class PresetMonitorCoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = FIXTURE_FILE.read_bytes()
        cls.fragments = make_fixture_messages(
            cls.fixture
        )

    def test_fixture_reconstructs_from_18_fragments(self) -> None:
        self.assertEqual(
            len(self.fragments),
            18,
        )

        core = PresetMonitorCore()
        updates = core.feed_many(
            self.fragments
        )

        self.assertTrue(
            updates[-1].metadata_loaded
        )
        self.assertTrue(
            core.metadata_ready
        )
        self.assertEqual(
            core.fragment_count,
            18,
        )
        self.assertEqual(
            core.global_block,
            self.fixture,
        )

    def test_event_before_metadata_becomes_enriched_later(self) -> None:
        core = PresetMonitorCore()

        event_update = core.feed(
            make_incoming_preset_event("45B")
        )

        self.assertIsNotNone(
            event_update.preset_event
        )
        self.assertIsNone(
            event_update.snapshot
        )
        self.assertTrue(
            core.current_preset_known
        )
        self.assertFalse(
            core.ready
        )

        updates = core.feed_many(
            reversed(self.fragments)
        )
        final = updates[-1]

        self.assertTrue(
            final.metadata_loaded
        )
        self.assertTrue(
            final.snapshot_changed
        )
        self.assertIsNotNone(
            final.snapshot
        )
        assert final.snapshot is not None

        self.assertEqual(
            final.snapshot.label,
            "45B",
        )
        self.assertEqual(
            final.snapshot.name,
            "NOME123456789",
        )
        self.assertEqual(
            final.snapshot.filter_tag,
            "TAG45A123",
        )
        self.assertTrue(
            core.ready
        )

    def test_metadata_before_event_becomes_ready_on_event(self) -> None:
        core = PresetMonitorCore()
        core.feed_many(
            self.fragments
        )

        self.assertTrue(
            core.metadata_ready
        )
        self.assertFalse(
            core.current_preset_known
        )
        self.assertIsNone(
            core.snapshot
        )

        update = core.feed(
            make_incoming_preset_event("45A")
        )

        self.assertTrue(
            update.snapshot_changed
        )
        self.assertIsNotNone(
            update.snapshot
        )
        assert update.snapshot is not None

        self.assertEqual(
            update.snapshot.label,
            "45A",
        )
        self.assertEqual(
            update.snapshot.name,
            "Matribox II PRO",
        )
        self.assertEqual(
            update.snapshot.filter_tag,
            "JKLMNOPQR",
        )

    def test_switching_preset_updates_enriched_snapshot(self) -> None:
        core = PresetMonitorCore()
        core.feed_many(
            self.fragments
        )
        core.feed(
            make_incoming_preset_event("45B")
        )

        update = core.feed(
            make_incoming_preset_event("45C")
        )

        self.assertTrue(
            update.snapshot_changed
        )
        self.assertIsNotNone(
            update.snapshot
        )
        assert update.snapshot is not None

        self.assertEqual(
            update.snapshot.label,
            "45C",
        )
        self.assertEqual(
            update.snapshot.name,
            "Matribox II PRO",
        )
        self.assertEqual(
            update.snapshot.filter_tag,
            "UVWXYZ789",
        )

    def test_duplicate_current_event_does_not_report_change(self) -> None:
        core = PresetMonitorCore()
        core.feed_many(
            self.fragments
        )

        first = core.feed(
            make_incoming_preset_event("45B")
        )
        second = core.feed(
            make_incoming_preset_event("45B")
        )

        self.assertTrue(
            first.snapshot_changed
        )
        self.assertFalse(
            second.snapshot_changed
        )
        self.assertEqual(
            first.snapshot,
            second.snapshot,
        )

    def test_fragment_progress_is_available(self) -> None:
        core = PresetMonitorCore()

        update = core.feed(
            self.fragments[0]
        )

        self.assertTrue(
            update.collector_update.accepted
        )
        self.assertEqual(
            core.fragment_count,
            1,
        )
        self.assertEqual(
            core.metadata_progress,
            (
                FRAGMENT_PAYLOAD_SIZE,
                len(self.fixture),
            ),
        )

    def test_unrelated_message_is_ignored(self) -> None:
        core = PresetMonitorCore()

        update = core.feed(
            bytes.fromhex("F0 01 02 F7")
        )

        self.assertFalse(
            update.handled
        )
        self.assertIsNone(
            update.preset_event
        )
        self.assertFalse(
            update.collector_update.accepted
        )
        self.assertIsNone(
            update.snapshot
        )

    def test_loading_same_global_block_twice_is_idempotent(self) -> None:
        core = PresetMonitorCore()

        self.assertTrue(
            core.load_global_block(
                self.fixture
            )
        )
        self.assertFalse(
            core.load_global_block(
                self.fixture
            )
        )

    def test_reset_discards_entire_session(self) -> None:
        core = PresetMonitorCore()
        core.feed_many(
            self.fragments
        )
        core.feed(
            make_incoming_preset_event("45B")
        )

        self.assertTrue(
            core.ready
        )

        core.reset()

        self.assertFalse(
            core.metadata_ready
        )
        self.assertFalse(
            core.current_preset_known
        )
        self.assertFalse(
            core.ready
        )
        self.assertIsNone(
            core.snapshot
        )
        self.assertIsNone(
            core.metadata_progress
        )
        self.assertEqual(
            core.fragment_count,
            0,
        )

    def test_formats_expected_terminal_output(self) -> None:
        core = PresetMonitorCore()
        core.load_global_block(
            self.fixture
        )
        update = core.feed(
            make_incoming_preset_event("45B")
        )

        self.assertIsNotNone(
            update.snapshot
        )
        assert update.snapshot is not None

        self.assertEqual(
            format_monitor_snapshot(
                update.snapshot
            ),
            (
                "Preset atual: 45B\n"
                "Nome: NOME123456789\n"
                "Etiqueta: TAG45A123\n"
                "Efeitos: aguardando resposta estrutural."
            ),
        )


    def test_structural_response_enriches_snapshot_with_effect_names(self) -> None:
        core = PresetMonitorCore()
        core.load_global_block(
            self.fixture
        )
        core.feed(
            make_incoming_preset_event("45B")
        )

        update = core.feed(
            STRUCTURAL_BASELINE_FILE.read_bytes()
        )

        self.assertTrue(update.handled)
        self.assertTrue(update.chain_changed)
        self.assertTrue(update.snapshot_changed)
        self.assertIsNotNone(update.snapshot)
        assert update.snapshot is not None

        self.assertTrue(update.snapshot.effects_ready)
        self.assertEqual(
            tuple(
                (
                    effect.class_name,
                    effect.model_name,
                    effect.enabled,
                )
                for effect in update.snapshot.effects
            ),
            (
                ("DYN", "GATE 3", True),
                ("AMP", "TWD DELUXE", True),
                ("DRV", "Skreamer", True),
                ("MOD", "E-CHORUS", True),
                ("DLY", "WARM", True),
            ),
        )

        formatted = format_monitor_snapshot(
            update.snapshot
        )

        self.assertIn(
            "1. DYN / GATE 3 — ligado",
            formatted,
        )
        self.assertIn(
            "5. DLY / WARM — ligado",
            formatted,
        )

    def test_new_preset_event_discards_previous_chain(self) -> None:
        core = PresetMonitorCore()
        core.load_global_block(
            self.fixture
        )
        core.feed(
            make_incoming_preset_event("45B")
        )
        core.feed(
            STRUCTURAL_BASELINE_FILE.read_bytes()
        )

        update = core.feed(
            make_incoming_preset_event("45C")
        )

        self.assertIsNotNone(update.snapshot)
        assert update.snapshot is not None
        self.assertFalse(update.snapshot.effects_ready)
        self.assertEqual(update.snapshot.effects, ())
        self.assertFalse(core.chain_ready)



if __name__ == "__main__":
    unittest.main()
