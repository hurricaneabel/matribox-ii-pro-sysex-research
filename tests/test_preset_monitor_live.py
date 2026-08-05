"""Testes offline do adaptador MIDI do monitor."""

from __future__ import annotations

import unittest
from pathlib import Path

import mido

from tools.commands.preset_monitor_core import (
    PresetMonitorCore,
    build_monitor_startup_plan,
)
from tools.commands.preset_monitor_live import (
    DEFAULT_GLOBAL_QUERY_RETRIES,
    DEFAULT_GLOBAL_RETRY_INTERVAL_SECONDS,
    StartupTimeoutError,
    clear_pending_messages,
    create_mido_sysex,
    describe_startup_progress,
    iter_monitor_updates,
    process_mido_message,
    send_global_metadata_query,
    send_startup_sequence,
    wait_for_initial_snapshot,
)
from tools.commands.preset_state import (
    build_select_preset,
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


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


class FakeInputPort:
    def __init__(self, messages=()) -> None:
        self.messages = list(messages)

    def poll(self):
        if not self.messages:
            return None

        return self.messages.pop(0)


class FakeOutputPort:
    def __init__(self) -> None:
        self.messages = []

    def send(self, message) -> None:
        self.messages.append(message)


def encode_fragment_message(
    block: bytes,
    offset: int,
    length: int = FRAGMENT_PAYLOAD_SIZE,
) -> mido.Message:
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

    full = bytes(
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

    return create_mido_sysex(full)


def make_fixture_messages(
    block: bytes,
) -> list[mido.Message]:
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
) -> mido.Message:
    full = bytearray(
        build_select_preset(label)
    )
    full[8] = 0x00

    return create_mido_sysex(
        full
    )


class SysexConversionTests(unittest.TestCase):
    def test_round_trip_full_sysex(self) -> None:
        full = bytes.fromhex(
            "F0 21 25 7E 47 50 2D 32 "
            "11 12 00 00 00 F7"
        )

        message = create_mido_sysex(
            full
        )

        self.assertEqual(
            bytes(message.bin()),
            full,
        )

    def test_rejects_missing_f0(self) -> None:
        with self.assertRaises(ValueError):
            create_mido_sysex(
                bytes.fromhex("21 25 F7")
            )

    def test_rejects_missing_f7(self) -> None:
        with self.assertRaises(ValueError):
            create_mido_sysex(
                bytes.fromhex("F0 21 25")
            )


class StartupTransmissionTests(unittest.TestCase):
    def test_sends_four_handshakes_and_two_queries(self) -> None:
        output = FakeOutputPort()
        clock = FakeClock()
        calls: list[tuple[int, int]] = []

        summary = send_startup_sequence(
            output,
            sleeper=clock.sleep,
            on_handshake=lambda current, total: calls.append(
                (current, total)
            ),
        )

        plan = build_monitor_startup_plan()

        self.assertEqual(
            len(output.messages),
            6,
        )
        self.assertEqual(
            tuple(
                bytes(message.bin())
                for message in output.messages
            ),
            plan.ordered_messages,
        )
        self.assertEqual(
            clock.sleeps,
            [0.2, 0.2, 0.2, 0.5],
        )
        self.assertEqual(
            calls,
            [
                (1, 4),
                (2, 4),
                (3, 4),
                (4, 4),
            ],
        )
        self.assertEqual(
            summary.handshake_count,
            4,
        )
        self.assertTrue(
            summary.global_query_sent
        )
        self.assertTrue(
            summary.current_preset_query_sent
        )

    def test_clears_all_pending_messages(self) -> None:
        input_port = FakeInputPort(
            [
                mido.Message("note_on"),
                mido.Message("clock"),
                mido.Message("sysex", data=(1, 2)),
            ]
        )

        self.assertEqual(
            clear_pending_messages(
                input_port
            ),
            3,
        )
        self.assertIsNone(
            input_port.poll()
        )

    def test_sends_global_query_alone(self) -> None:
        output = FakeOutputPort()

        send_global_metadata_query(
            output
        )

        plan = build_monitor_startup_plan()

        self.assertEqual(
            len(output.messages),
            1,
        )
        self.assertEqual(
            bytes(output.messages[0].bin()),
            plan.global_metadata_query,
        )


class MessageProcessingTests(unittest.TestCase):
    def test_ignores_non_sysex(self) -> None:
        core = PresetMonitorCore()

        self.assertIsNone(
            process_mido_message(
                core,
                mido.Message("note_on"),
            )
        )

    def test_processes_preset_event(self) -> None:
        core = PresetMonitorCore()

        update = process_mido_message(
            core,
            make_incoming_preset_event(
                "45B"
            ),
        )

        self.assertIsNotNone(update)
        assert update is not None
        self.assertIsNotNone(
            update.preset_event
        )
        self.assertEqual(
            core.current_event.label,
            "45B",
        )


class InitialSnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = FIXTURE_FILE.read_bytes()
        cls.fragments = make_fixture_messages(
            cls.fixture
        )

    def test_waits_for_event_then_metadata(self) -> None:
        core = PresetMonitorCore()
        clock = FakeClock()
        input_port = FakeInputPort(
            [
                make_incoming_preset_event(
                    "45B"
                ),
                *reversed(self.fragments),
            ]
        )

        result = wait_for_initial_snapshot(
            input_port,
            core,
            timeout_seconds=2.0,
            monotonic=clock.monotonic,
            sleeper=clock.sleep,
        )

        self.assertEqual(
            result.snapshot.label,
            "45B",
        )
        self.assertEqual(
            result.snapshot.name,
            "NOME123456789",
        )
        self.assertEqual(
            result.snapshot.filter_tag,
            "TAG45A123",
        )
        self.assertEqual(
            result.fragment_count,
            18,
        )
        self.assertEqual(
            result.global_block_size,
            len(self.fixture),
        )
        self.assertEqual(
            result.metadata_count,
            240,
        )

    def test_waits_for_metadata_then_event(self) -> None:
        core = PresetMonitorCore()
        clock = FakeClock()
        input_port = FakeInputPort(
            [
                *self.fragments,
                make_incoming_preset_event(
                    "45C"
                ),
            ]
        )

        result = wait_for_initial_snapshot(
            input_port,
            core,
            timeout_seconds=2.0,
            monotonic=clock.monotonic,
            sleeper=clock.sleep,
        )

        self.assertEqual(
            result.snapshot.label,
            "45C",
        )
        self.assertEqual(
            result.snapshot.filter_tag,
            "UVWXYZ789",
        )

    def test_reports_each_processed_update(self) -> None:
        core = PresetMonitorCore()
        clock = FakeClock()
        input_port = FakeInputPort(
            [
                make_incoming_preset_event(
                    "45A"
                ),
                *self.fragments,
            ]
        )
        updates = []

        wait_for_initial_snapshot(
            input_port,
            core,
            timeout_seconds=2.0,
            monotonic=clock.monotonic,
            sleeper=clock.sleep,
            on_update=updates.append,
        )

        self.assertEqual(
            len(updates),
            19,
        )

    def test_timeout_contains_diagnostic(self) -> None:
        core = PresetMonitorCore()
        clock = FakeClock()
        input_port = FakeInputPort()

        with self.assertRaises(
            StartupTimeoutError
        ) as context:
            wait_for_initial_snapshot(
                input_port,
                core,
                timeout_seconds=0.05,
                poll_interval_seconds=0.01,
                monotonic=clock.monotonic,
                sleeper=clock.sleep,
            )

        message = str(context.exception)

        self.assertIn(
            "metadados=não",
            message,
        )
        self.assertIn(
            "preset=não",
            message,
        )
        self.assertIn(
            "fragmentos=0",
            message,
        )

    def test_progress_description_after_one_fragment(self) -> None:
        core = PresetMonitorCore()
        process_mido_message(
            core,
            self.fragments[0],
        )

        description = describe_startup_progress(
            core
        )

        self.assertIn(
            "fragmentos=1",
            description,
        )
        self.assertIn(
            "185/3172 bytes",
            description,
        )


class GlobalQueryRetryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = FIXTURE_FILE.read_bytes()
        cls.fragments = make_fixture_messages(
            cls.fixture
        )

    def test_default_retry_settings_are_positive(self) -> None:
        self.assertGreater(
            DEFAULT_GLOBAL_RETRY_INTERVAL_SECONDS,
            0,
        )
        self.assertGreater(
            DEFAULT_GLOBAL_QUERY_RETRIES,
            0,
        )

    def test_retry_fills_one_missing_full_fragment(self) -> None:
        core = PresetMonitorCore()
        clock = FakeClock()

        missing_index = 16

        input_port = FakeInputPort(
            [
                make_incoming_preset_event(
                    "45B"
                ),
                *(
                    fragment
                    for index, fragment in enumerate(
                        self.fragments
                    )
                    if index != missing_index
                ),
            ]
        )

        retry_calls = []
        retry_reports = []

        def retry_global() -> None:
            retry_calls.append(1)
            input_port.messages.append(
                self.fragments[missing_index]
            )

        result = wait_for_initial_snapshot(
            input_port,
            core,
            timeout_seconds=1.0,
            poll_interval_seconds=0.01,
            monotonic=clock.monotonic,
            sleeper=clock.sleep,
            retry_global_query=retry_global,
            global_retry_interval_seconds=0.03,
            max_global_query_retries=1,
            on_global_retry=lambda attempt, total, diagnostic: (
                retry_reports.append(
                    (attempt, total, diagnostic)
                )
            ),
        )

        self.assertEqual(
            len(retry_calls),
            1,
        )
        self.assertEqual(
            result.global_query_retries,
            1,
        )
        self.assertEqual(
            result.snapshot.label,
            "45B",
        )
        self.assertEqual(
            result.fragment_count,
            18,
        )
        self.assertEqual(
            retry_reports[0][0:2],
            (1, 1),
        )
        self.assertIn(
            "2987/3172 bytes",
            retry_reports[0][2],
        )

    def test_complete_first_response_does_not_retry(self) -> None:
        core = PresetMonitorCore()
        clock = FakeClock()
        input_port = FakeInputPort(
            [
                *self.fragments,
                make_incoming_preset_event(
                    "45A"
                ),
            ]
        )
        retry_calls = []

        result = wait_for_initial_snapshot(
            input_port,
            core,
            timeout_seconds=1.0,
            monotonic=clock.monotonic,
            sleeper=clock.sleep,
            retry_global_query=lambda: retry_calls.append(1),
            global_retry_interval_seconds=0.03,
            max_global_query_retries=2,
        )

        self.assertEqual(
            retry_calls,
            [],
        )
        self.assertEqual(
            result.global_query_retries,
            0,
        )

    def test_retry_limit_is_respected(self) -> None:
        core = PresetMonitorCore()
        clock = FakeClock()
        input_port = FakeInputPort()
        retry_calls = []

        with self.assertRaises(
            StartupTimeoutError
        ) as context:
            wait_for_initial_snapshot(
                input_port,
                core,
                timeout_seconds=0.11,
                poll_interval_seconds=0.01,
                monotonic=clock.monotonic,
                sleeper=clock.sleep,
                retry_global_query=lambda: retry_calls.append(1),
                global_retry_interval_seconds=0.03,
                max_global_query_retries=2,
            )

        self.assertEqual(
            len(retry_calls),
            2,
        )
        self.assertIn(
            "reenvios globais=2",
            str(context.exception),
        )

    def test_progress_diagnostic_includes_missing_ranges(self) -> None:
        core = PresetMonitorCore()

        for index, fragment in enumerate(
            self.fragments
        ):
            if index != 16:
                process_mido_message(
                    core,
                    fragment,
                )

        description = describe_startup_progress(
            core
        )

        self.assertIn(
            "2987/3172 bytes",
            description,
        )
        self.assertIn(
            "lacunas=",
            description,
        )


class ContinuousMonitoringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = FIXTURE_FILE.read_bytes()

    def test_iterator_yields_preset_change(self) -> None:
        core = PresetMonitorCore()
        core.load_global_block(
            self.fixture
        )

        input_port = FakeInputPort(
            [
                mido.Message("note_on"),
                make_incoming_preset_event(
                    "45A"
                ),
                make_incoming_preset_event(
                    "45C"
                ),
            ]
        )

        updates = iter_monitor_updates(
            input_port,
            core,
            sleeper=lambda _seconds: None,
        )

        first = next(updates)
        second = next(updates)

        self.assertEqual(
            first.snapshot.label,
            "45A",
        )
        self.assertEqual(
            second.snapshot.label,
            "45C",
        )
        self.assertTrue(
            second.snapshot_changed
        )


if __name__ == "__main__":
    unittest.main()
