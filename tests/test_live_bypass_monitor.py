from __future__ import annotations

from pathlib import Path
import unittest

from tools.commands.chain_order import parse_chain_order_response
from tools.commands.global_preset_metadata import (
    GlobalPresetMetadata,
    PresetMetadata,
    preset_index_to_label,
)
from tools.commands.preset_monitor_core import (
    PresetMonitorCore,
    PresetMonitorSnapshot,
    format_monitor_snapshot,
)
from tools.commands.preset_state import PresetEvent


FIXTURES = Path(__file__).resolve().parent / "fixtures"
BASELINE = (
    FIXTURES
    / "structural_effect_state"
    / "phase15"
    / "BASELINE.bin"
)
SWAPPED = FIXTURES / "chain_bypass" / "S5_OFF_SWAPPED_structural.bin"
BYPASS = FIXTURES / "effect_slot_state"


def read_chain(path: Path):
    state = parse_chain_order_response(path.read_bytes())
    assert state is not None
    return state


class LiveBypassMonitorTests(unittest.TestCase):
    def test_bypass_response_updates_current_chain_immediately(self) -> None:
        core = PresetMonitorCore()
        core.current_chain = read_chain(BASELINE)

        update = core.feed((BYPASS / "S3_OFF.bin").read_bytes())

        self.assertIsNotNone(update.bypass_event)
        self.assertTrue(update.chain_changed)
        self.assertIsNone(update.chain_state)
        assert core.current_chain is not None
        self.assertFalse(core.current_chain.enabled_for_internal_slot(3))
        self.assertEqual(core.current_chain.human_slots, (1, 2, 3, 4, 5))

    def test_repeated_same_state_does_not_redraw(self) -> None:
        core = PresetMonitorCore()
        core.current_chain = read_chain(BASELINE)

        first = core.feed((BYPASS / "S2_OFF.bin").read_bytes())
        second = core.feed((BYPASS / "S2_OFF.bin").read_bytes())

        self.assertTrue(first.chain_changed)
        self.assertFalse(second.chain_changed)

    def test_internal_slot_update_respects_swapped_visual_order(self) -> None:
        core = PresetMonitorCore()
        core.current_chain = read_chain(SWAPPED)

        update = core.feed((BYPASS / "S5_ON.bin").read_bytes())

        self.assertTrue(update.chain_changed)
        assert core.current_chain is not None
        self.assertEqual(core.current_chain.human_slots, (1, 2, 3, 5, 4))
        self.assertTrue(core.current_chain.enabled_at_visual_position(4))

    def test_event_received_during_dump_overrides_loaded_chain(self) -> None:
        core = PresetMonitorCore()

        update = core.feed((BYPASS / "S1_OFF.bin").read_bytes())
        self.assertIsNotNone(update.bypass_event)
        self.assertIsNone(core.current_chain)

        core.apply_chain_state(read_chain(BASELINE))

        assert core.current_chain is not None
        self.assertFalse(core.current_chain.enabled_for_internal_slot(1))

    def test_monitor_snapshot_is_redrawn_on_bypass_event(self) -> None:
        core = PresetMonitorCore()
        presets = tuple(
            PresetMetadata(
                index=index,
                label=preset_index_to_label(index),
                preset_id=index,
                name=f"Preset {index}",
                filter_tag="Rock",
                raw_name=b"",
                raw_filter_tag=b"",
            )
            for index in range(240)
        )
        core.metadata = GlobalPresetMetadata(
            presets=presets,
            decompressor_backend="test",
        )
        core.current_event = PresetEvent(
            index=0,
            label="01A",
            observed_checksum=0,
            calculated_checksum=0,
            raw_message=b"",
        )
        core.apply_chain_state(read_chain(BASELINE))

        update = core.feed((BYPASS / "S1_OFF.bin").read_bytes())

        self.assertTrue(update.snapshot_changed)
        self.assertIsNotNone(update.snapshot)
        assert update.snapshot is not None
        self.assertFalse(update.snapshot.effects[0].enabled)

    def test_formatted_snapshot_changes_only_the_state_text(self) -> None:
        chain = read_chain(BASELINE).with_internal_slot_enabled(1, False)
        metadata = PresetMetadata(
            index=0,
            label="01A",
            preset_id=0,
            name="Teste",
            filter_tag="Rock",
            raw_name=b"Teste",
            raw_filter_tag=b"Rock",
        )
        snapshot = PresetMonitorSnapshot.from_metadata(metadata, chain)

        formatted = format_monitor_snapshot(snapshot)

        self.assertIn("1. DYN / GATE 3 — desligado", formatted)
        self.assertIn("2. AMP / TWD DELUXE — ligado", formatted)


if __name__ == "__main__":
    unittest.main()
