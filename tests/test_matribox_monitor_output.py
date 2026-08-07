"""Testes offline dos modos de saída do monitor principal."""

from __future__ import annotations

from datetime import datetime
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
import unittest

from tools.commands.matribox_monitor import (
    ALTERNATE_SCREEN_ENTER_SEQUENCE,
    ALTERNATE_SCREEN_EXIT_SEQUENCE,
    CLEAR_SCREEN_SEQUENCE,
    CLEAR_TO_END_SEQUENCE,
    CURSOR_HOME_SEQUENCE,
    HIDE_CURSOR_SEQUENCE,
    SHOW_CURSOR_SEQUENCE,
    enter_live_screen,
    exit_live_screen,
    format_compact_log_entries,
    format_live_screen,
    parse_arguments,
    redraw_screen,
    write_compact_log_entries,
)
from tools.commands.preset_monitor_core import PresetMonitorSnapshot


class MonitorArgumentTests(unittest.TestCase):
    def test_default_mode_remains_append_only_without_log(self) -> None:
        arguments = parse_arguments([])

        self.assertFalse(arguments.live)
        self.assertIsNone(arguments.log)

    def test_live_mode_accepts_compact_log_path(self) -> None:
        arguments = parse_arguments(["--live", "--log", "monitor.txt"])

        self.assertTrue(arguments.live)
        self.assertEqual(arguments.log, Path("monitor.txt"))


class LiveScreenTests(unittest.TestCase):
    def setUp(self) -> None:
        self.snapshot = PresetMonitorSnapshot(
            index=0,
            label="56B",
            preset_id=0,
            name="Matribox II PRO",
            filter_tag="",
            effects=(),
            effects_ready=True,
        )

    def test_live_screen_uses_alternate_buffer_without_primary_scrollback(self) -> None:
        stream = StringIO()

        enter_live_screen(stream=stream)
        exit_live_screen(stream=stream)

        self.assertEqual(
            stream.getvalue(),
            (
                ALTERNATE_SCREEN_ENTER_SEQUENCE
                + HIDE_CURSOR_SEQUENCE
                + SHOW_CURSOR_SEQUENCE
                + ALTERNATE_SCREEN_EXIT_SEQUENCE
            ),
        )

    def test_redraw_screen_reuses_same_buffer_without_appending_newline(self) -> None:
        stream = StringIO()

        redraw_screen("painel", stream=stream)

        self.assertEqual(
            stream.getvalue(),
            f"{CLEAR_SCREEN_SEQUENCE}{CURSOR_HOME_SEQUENCE}painel",
        )


    def test_redraw_screen_clears_previous_frame_before_writing(self) -> None:
        stream = StringIO()

        redraw_screen("linha muito longa", stream=stream)
        redraw_screen("curta", stream=stream)

        self.assertEqual(
            stream.getvalue(),
            (
                f"{CLEAR_SCREEN_SEQUENCE}{CURSOR_HOME_SEQUENCE}"
                "linha muito longa"
                f"{CLEAR_SCREEN_SEQUENCE}{CURSOR_HOME_SEQUENCE}"
                "curta"
            ),
        )

    def test_live_screen_contains_snapshot_and_log_destination(self) -> None:
        text = format_live_screen(
            self.snapshot,
            input_port_name="Entrada MIDI",
            output_port_name="Saida MIDI",
            log_path=Path("monitor.txt"),
        )

        self.assertIn("Preset atual: 56B", text)
        self.assertIn("Nome: Matribox II PRO", text)
        self.assertIn("Modo: painel ao vivo (--live)", text)
        self.assertIn("Log: monitor.txt", text)
        self.assertIn("Pressione Ctrl+C para encerrar.", text)


class CompactLogTests(unittest.TestCase):
    def test_parameter_event_matches_compact_human_readable_format(self) -> None:
        update = SimpleNamespace(
            preset_event=None,
            parameter_event=SimpleNamespace(
                human_slot=9,
                effect_name="Dual Melody",
                parameter_name="LOW PITCH",
                display_value="-12",
            ),
            bypass_event=None,
            chain_changed=False,
            snapshot=None,
        )

        self.assertEqual(
            format_compact_log_entries(update),
            ("slot=9 Dual Melody LOW PITCH -12",),
        )

    def test_bypass_event_resolves_effect_name_from_snapshot(self) -> None:
        snapshot = SimpleNamespace(
            effects=(
                SimpleNamespace(
                    internal_slot=4,
                    model_name="Dual Melody",
                ),
            )
        )
        update = SimpleNamespace(
            preset_event=None,
            parameter_event=None,
            bypass_event=SimpleNamespace(
                human_slot=4,
                enabled=True,
            ),
            chain_changed=True,
            snapshot=snapshot,
        )

        self.assertEqual(
            format_compact_log_entries(update),
            ("slot=4 Dual Melody BYPASS ligado",),
        )

    def test_structural_change_without_more_specific_event_is_logged(self) -> None:
        update = SimpleNamespace(
            preset_event=None,
            parameter_event=None,
            bypass_event=None,
            chain_changed=True,
            snapshot=None,
        )

        self.assertEqual(
            format_compact_log_entries(update),
            ("chain=updated",),
        )

    def test_writer_adds_timestamp_and_flushes_events(self) -> None:
        stream = StringIO()
        update = SimpleNamespace(
            preset_event=None,
            parameter_event=SimpleNamespace(
                human_slot=9,
                effect_name="Dual Melody",
                parameter_name="LOW PITCH",
                display_value="-11",
            ),
            bypass_event=None,
            chain_changed=False,
            snapshot=None,
        )

        write_compact_log_entries(
            stream,
            update,
            now=lambda: datetime(2026, 8, 7, 4, 15, 21),
        )

        self.assertEqual(
            stream.getvalue(),
            "04:15:21 slot=9 Dual Melody LOW PITCH -11\n",
        )


if __name__ == "__main__":
    unittest.main()
