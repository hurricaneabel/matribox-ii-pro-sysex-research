"""Testes offline da leitura ao vivo da cadeia por dump de preset."""

from __future__ import annotations

import unittest
from pathlib import Path

import mido

from tools.commands.preset_dump_state import build_preset_dump_query
from tools.commands.preset_monitor_core import PresetMonitorCore
from tools.commands.preset_monitor_live import (
    create_mido_sysex,
    read_preset_chain_state,
)
from tools.commands.preset_state import build_select_preset


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GLOBAL_FIXTURE = (
    PROJECT_ROOT
    / "data"
    / "fixtures"
    / "global_metadata"
    / "preset_metadata_45abc.bin"
)
PRESET_FIXTURE = (
    PROJECT_ROOT
    / "tests"
    / "fixtures"
    / "preset_dump_chain"
    / "56A_GATE3_ON.bin"
)


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


class FakeInputPort:
    def __init__(self, messages=()) -> None:
        self.messages = list(messages)

    def poll(self):
        if not self.messages:
            return None

        return self.messages.pop(0)


class FakeOutputPort:
    def __init__(self, on_send=None) -> None:
        self.messages = []
        self.on_send = on_send

    def send(self, message) -> None:
        self.messages.append(message)

        if self.on_send is not None:
            self.on_send(len(self.messages), message)


def make_incoming_preset_event(label: str) -> mido.Message:
    packet = bytearray(build_select_preset(label))
    packet[8] = 0x00
    return create_mido_sysex(packet)


def encode_dump_fragment(
    block: bytes,
    offset: int,
    length: int = 100,
) -> mido.Message:
    payload = block[offset:offset + length]
    encoded = bytearray()

    for value in payload:
        encoded.extend(((value >> 4) & 0x0F, value & 0x0F))

    packet = bytes(
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

    return create_mido_sysex(packet)


def make_dump_fragments(block: bytes) -> list[mido.Message]:
    return [
        encode_dump_fragment(block, offset)
        for offset in range(0, len(block), 100)
    ]


def make_ready_core(label: str = "56A") -> PresetMonitorCore:
    core = PresetMonitorCore()
    core.load_global_block(GLOBAL_FIXTURE.read_bytes())
    core.feed(bytes(make_incoming_preset_event(label).bin()))
    return core


class PresetChainLiveReadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.preset_dump = PRESET_FIXTURE.read_bytes()
        cls.fragments = make_dump_fragments(cls.preset_dump)

    def test_reads_and_applies_chain_without_effect_write(self) -> None:
        core = make_ready_core()
        input_port = FakeInputPort(self.fragments)
        output_port = FakeOutputPort()
        clock = FakeClock()

        result = read_preset_chain_state(
            input_port,
            output_port,
            core,
            "56A",
            load_delay_seconds=0,
            timeout_seconds=1.0,
            poll_interval_seconds=0.01,
            monotonic=clock.monotonic,
            sleeper=clock.sleep,
        )

        self.assertTrue(result.complete)
        self.assertEqual(result.query_retries, 0)
        self.assertEqual(len(output_port.messages), 1)
        self.assertEqual(
            bytes(output_port.messages[0].bin()),
            build_preset_dump_query("56A"),
        )
        self.assertIsNotNone(core.snapshot)
        assert core.snapshot is not None
        self.assertTrue(core.snapshot.effects_ready)
        self.assertEqual(len(core.snapshot.effects), 5)
        self.assertEqual(core.snapshot.effects[0].model_name, "GATE 3")

    def test_retry_completes_one_missing_fragment(self) -> None:
        core = make_ready_core()
        missing_index = 2
        input_port = FakeInputPort(
            [
                fragment
                for index, fragment in enumerate(self.fragments)
                if index != missing_index
            ]
        )

        def on_send(send_count, _message) -> None:
            if send_count == 2:
                input_port.messages.append(self.fragments[missing_index])

        output_port = FakeOutputPort(on_send=on_send)
        clock = FakeClock()

        result = read_preset_chain_state(
            input_port,
            output_port,
            core,
            "56A",
            load_delay_seconds=0,
            timeout_seconds=0.03,
            max_query_retries=1,
            poll_interval_seconds=0.01,
            monotonic=clock.monotonic,
            sleeper=clock.sleep,
        )

        self.assertTrue(result.complete)
        self.assertEqual(result.query_retries, 1)
        self.assertEqual(len(output_port.messages), 2)

    def test_new_preset_interrupts_stale_dump(self) -> None:
        core = make_ready_core("56A")
        input_port = FakeInputPort(
            [make_incoming_preset_event("56B"), *self.fragments]
        )
        output_port = FakeOutputPort()
        clock = FakeClock()

        result = read_preset_chain_state(
            input_port,
            output_port,
            core,
            "56A",
            load_delay_seconds=0,
            timeout_seconds=1.0,
            monotonic=clock.monotonic,
            sleeper=clock.sleep,
        )

        self.assertTrue(result.interrupted)
        self.assertEqual(core.current_event.label, "56B")
        self.assertIsNone(core.current_chain)

    def test_dump_request_is_read_only_protocol_command(self) -> None:
        query = build_preset_dump_query("56A")

        self.assertEqual(query[8], 0x11)
        self.assertEqual(query[9], 0x10)
        self.assertEqual(query[31:33], bytes((0x0D, 0x0C)))


if __name__ == "__main__":
    unittest.main()
