"""Testes offline da hidratação de parâmetros salvos no dump ``0x10``."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import struct
import unittest

from tools.commands.chain_order import ChainOrderState
from tools.commands.effect_catalog import CATALOG
from tools.commands.preset_monitor_core import PresetMonitorCore, build_effect_snapshots
from tools.commands.structural_effect_state import StructuralEffectRecord
from tools.parameters.preset_dump import (
    PRESET_PARAMETER_BLOCK_END,
    PRESET_PARAMETER_BLOCK_OFFSET,
    PRESET_PARAMETER_SLOT_SIZE,
    PresetParameterDumpError,
    decode_saved_parameter_events,
)
from tools.parameters.state import EffectParameterState


def make_chain(*effects: tuple[int, str]) -> ChainOrderState:
    active = {slot: key for slot, key in effects}
    records = []
    enabled = [None] * 12
    for slot_id in range(12):
        effect_key = active.get(slot_id)
        if effect_key is None:
            records.append(
                StructuralEffectRecord(
                    internal_slot_id=slot_id,
                    active=False,
                    class_id=None,
                    model_id=None,
                    auxiliary_1=0,
                    auxiliary_2=0,
                    secondary_selector=None,
                    enabled=None,
                )
            )
            continue
        effect = CATALOG.effect_by_key(effect_key)
        effect_class = CATALOG.class_by_key(effect.class_key)
        enabled[slot_id] = True
        records.append(
            StructuralEffectRecord(
                internal_slot_id=slot_id,
                active=True,
                class_id=effect_class.class_id,
                model_id=effect.model_id,
                auxiliary_1=0,
                auxiliary_2=0,
                secondary_selector=effect.secondary_selector,
                enabled=True,
            )
        )
    return ChainOrderState(
        internal_slot_ids=tuple(slot for slot, _key in effects),
        observed_checksum=0,
        declared_length_units=0,
        raw_message=b"",
        enabled_by_internal_slot=tuple(enabled),
        effect_records_by_internal_slot=tuple(records),
    )


def make_dump(values: dict[tuple[int, int], float]) -> bytes:
    payload = bytearray(PRESET_PARAMETER_BLOCK_END)
    for (slot_id, selector), value in values.items():
        offset = (
            PRESET_PARAMETER_BLOCK_OFFSET
            + slot_id * PRESET_PARAMETER_SLOT_SIZE
            + selector * 4
        )
        payload[offset:offset + 4] = struct.pack("<f", value)
    return bytes(payload)


class SavedParameterDumpDecoderTests(unittest.TestCase):
    def test_same_selector_uses_sixty_byte_stride_between_slots(self) -> None:
        chain = make_chain((0, "dyn.m_boost"), (1, "dyn.m_boost"))
        events = decode_saved_parameter_events(
            make_dump({(0, 0): 21, (1, 0): 73}),
            chain,
        )
        self.assertEqual(
            tuple((event.internal_slot_id, event.value) for event in events),
            ((0, 21), (1, 73)),
        )

    def test_comp1_uses_consecutive_parameter_selectors(self) -> None:
        events = decode_saved_parameter_events(
            make_dump({(0, 0): 31, (0, 1): 67}),
            make_chain((0, "dyn.comp1")),
        )
        self.assertEqual(
            tuple((event.parameter_key, event.value) for event in events),
            (("sustain", 31), ("volume", 67)),
        )

    def test_dual_melody_preserves_selector_gap_and_negative_value(self) -> None:
        events = decode_saved_parameter_events(
            make_dump({
                (0, 0): 7,
                (0, 1): -12,
                (0, 2): 43,
                (0, 3): 85,
                (0, 4): 61,
                (0, 5): 79,
            }),
            make_chain((0, "freq.dual_melody")),
        )
        self.assertEqual(
            tuple((event.parameter_key, event.value) for event in events),
            (
                ("high_pitch", 7),
                ("low_pitch", -12),
                ("dry", 43),
                ("hi_vol", 61),
                ("low_vol", 79),
            ),
        )

    def test_pitch_hydrates_five_consecutive_values_and_signed_low_pitch(self) -> None:
        events = decode_saved_parameter_events(
            make_dump({
                (0, 0): 3,
                (0, 1): -9,
                (0, 2): 21,
                (0, 3): 43,
                (0, 4): 65,
            }),
            make_chain((0, "freq.pitch")),
        )
        self.assertEqual(
            tuple((event.parameter_key, event.value) for event in events),
            (
                ("high_pitch", 3),
                ("low_pitch", -9),
                ("wet", 21),
                ("dry", 43),
                ("range", 65),
            ),
        )

    def test_harmony_d_hydrates_enums_and_skips_selector_five(self) -> None:
        events = decode_saved_parameter_events(
            make_dump({
                (0, 0): 23,
                (0, 1): 3,
                (0, 2): 3,
                (0, 3): 3,
                (0, 4): 11,
                (0, 5): 99,
                (0, 6): 0,
            }),
            make_chain((0, "freq.harmony_d")),
        )
        self.assertEqual(
            tuple((event.parameter_key, event.value) for event in events),
            (
                ("mix", 23),
                ("key", "D#"),
                ("mode", "DORIAN"),
                ("interval_1", "-5TH"),
                ("interval_2", "+6TH"),
                ("smooth", False),
            ),
        )

        state = EffectParameterState()
        for event in events:
            state.apply(event, origin="saved_preset_dump")
        snapshot = build_effect_snapshots(
            make_chain((0, "freq.harmony_d")), state
        )[0]
        self.assertEqual(
            tuple(parameter.display_value for parameter in snapshot.parameters),
            ("23", "D#", "DORIAN", "-5TH", "+6TH", "desligado"),
        )

    def test_pitch_s_hydrates_only_four_cataloged_selectors(self) -> None:
        events = decode_saved_parameter_events(
            make_dump({
                (0, 0): 1,
                (0, 1): 21,
                (0, 2): 43,
                (0, 3): 65,
                (0, 4): 10,
            }),
            make_chain((0, "freq.pitch_s")),
        )
        self.assertEqual(
            tuple((event.parameter_key, event.value) for event in events),
            (
                ("range", "-1 OCT"),
                ("position", 21),
                ("mix", 43),
                ("level", 65),
            ),
        )

        state = EffectParameterState()
        for event in events:
            state.apply(event, origin="saved_preset_dump")
        snapshot = build_effect_snapshots(
            make_chain((0, "freq.pitch_s")), state
        )[0]
        self.assertEqual(
            tuple(parameter.display_value for parameter in snapshot.parameters),
            ("-1 OCT", "21", "43", "65"),
        )

    def test_ring_mod_hydrates_signed_fine_and_ignores_residual_selector(self) -> None:
        events = decode_saved_parameter_events(
            make_dump({
                (0, 0): 21,
                (0, 1): 43,
                (0, 2): -17,
                (0, 3): 65,
                (0, 4): 10,
            }),
            make_chain((0, "freq.ring_mod")),
        )
        self.assertEqual(
            tuple((event.parameter_key, event.value) for event in events),
            (("mix", 21), ("freq", 43), ("fine", -17), ("tone", 65)),
        )

        state = EffectParameterState()
        for event in events:
            state.apply(event, origin="saved_preset_dump")
        snapshot = build_effect_snapshots(
            make_chain((0, "freq.ring_mod")), state
        )[0]
        self.assertEqual(
            tuple(parameter.display_value for parameter in snapshot.parameters),
            ("21", "43", "-17", "65"),
        )

    def test_invalid_saved_value_is_ignored_individually(self) -> None:
        events = decode_saved_parameter_events(
            make_dump({(0, 0): 31.5, (0, 1): 67}),
            make_chain((0, "dyn.comp1")),
        )
        self.assertEqual(
            tuple(event.parameter_key for event in events),
            ("volume",),
        )

    def test_short_dump_is_rejected(self) -> None:
        with self.assertRaises(PresetParameterDumpError):
            decode_saved_parameter_events(
                bytes(PRESET_PARAMETER_BLOCK_END - 1),
                make_chain((0, "dyn.m_boost")),
            )


class SavedParameterStateTests(unittest.TestCase):
    def test_filter_controller_is_applied_before_saved_rate(self) -> None:
        chain = make_chain((0, "freq.filter"))
        events = decode_saved_parameter_events(
            make_dump({
                (0, 0): 11,
                (0, 1): 22,
                (0, 2): 33,
                (0, 3): 44,
                (0, 4): 8,
                (0, 5): 1,
            }),
            chain,
        )
        state = EffectParameterState()
        for event in events:
            state.apply(event, origin="saved_preset_dump")

        snapshot = build_effect_snapshots(chain, state)[0]
        by_key = {parameter.key: parameter for parameter in snapshot.parameters}
        self.assertEqual(
            (by_key["rate"].value, by_key["rate"].display_value),
            (8, "1/8d"),
        )
        self.assertEqual(by_key["rate"].value_origin, "saved_preset_dump")
        self.assertEqual(by_key["sync"].value, True)

    def test_live_sync_change_invalidates_saved_rate(self) -> None:
        chain = make_chain((0, "freq.filter"))
        events = decode_saved_parameter_events(
            make_dump({(0, 4): 8, (0, 5): 1}),
            chain,
        )
        state = EffectParameterState()
        for event in events:
            state.apply(event, origin="saved_preset_dump")
        sync = next(event for event in events if event.parameter_key == "sync")
        state.apply(replace(sync, value=False), origin="observed_usb")

        snapshot = build_effect_snapshots(chain, state)[0]
        by_key = {parameter.key: parameter for parameter in snapshot.parameters}
        self.assertEqual(
            (
                by_key["rate"].value,
                by_key["rate"].display_value,
                by_key["rate"].value_origin,
            ),
            (10, "10", "derived_device_rule"),
        )
        self.assertEqual(by_key["sync"].value_origin, "observed_usb")

    def test_saved_dump_does_not_override_live_parameter(self) -> None:
        chain = make_chain((0, "dyn.m_boost"))
        saved = decode_saved_parameter_events(
            make_dump({(0, 0): 21}), chain
        )[0]
        core = PresetMonitorCore()
        core.apply_chain_state(chain)
        core.parameter_state.apply(
            replace(saved, value=73),
            origin="observed_usb",
        )

        core.hydrate_saved_parameters(make_dump({(0, 0): 21}))
        resolved = core.parameter_state.resolve_parameter(
            0,
            "dyn.m_boost",
            CATALOG.effect_by_key("dyn.m_boost").parameters[0],
        )
        self.assertEqual((resolved.value, resolved.origin), (73, "observed_usb"))

    def test_saved_controller_does_not_invalidate_live_dependent(self) -> None:
        chain = make_chain((0, "freq.filter"))
        events = decode_saved_parameter_events(
            make_dump({(0, 4): 8, (0, 5): 1}), chain
        )
        rate = next(event for event in events if event.parameter_key == "rate")
        core = PresetMonitorCore()
        core.apply_chain_state(chain)
        core.parameter_state.apply(
            replace(rate, value=9),
            origin="observed_usb",
        )

        core.hydrate_saved_parameters(make_dump({(0, 4): 8, (0, 5): 1}))
        resolved = core.parameter_state.resolve_parameter(
            0,
            "freq.filter",
            CATALOG.effect_by_key("freq.filter").parameters[4],
        )
        self.assertEqual((resolved.value, resolved.origin), (9, "observed_usb"))

    def test_core_hydrates_after_chain_is_applied(self) -> None:
        chain = make_chain((0, "dyn.comp1"))
        core = PresetMonitorCore()
        core.apply_chain_state(chain)
        count = core.hydrate_saved_parameters(
            make_dump({(0, 0): 31, (0, 1): 67})
        )

        self.assertEqual(count, 2)
        sustain = core.parameter_state.resolve_parameter(
            0,
            "dyn.comp1",
            CATALOG.effect_by_key("dyn.comp1").parameters[0],
        )
        self.assertEqual((sustain.value, sustain.origin), (31, "saved_preset_dump"))

    def test_complete_physical_dump_hydrates_gate3(self) -> None:
        fixture = (
            Path(__file__).parent
            / "fixtures"
            / "preset_dump_chain"
            / "56A_GATE3_ON.bin"
        )
        core = PresetMonitorCore()
        chain = core.apply_preset_dump(fixture.read_bytes())

        self.assertEqual(chain.internal_slot_ids, (0, 1, 2, 3, 4))
        events = core.parameter_state.as_mapping()[0]
        self.assertEqual(
            {key: event.value for key, event in events.items()},
            {
                "threshold": 20,
                "ratio": 20,
                "attack": 20,
                "release": 200,
                "hold": 500,
            },
        )
        gate3 = CATALOG.effect_by_key("dyn.gate_3")
        for parameter in gate3.parameters:
            resolved = core.parameter_state.resolve_parameter(
                0, gate3.key, parameter
            )
            self.assertEqual(resolved.origin, "saved_preset_dump")


if __name__ == "__main__":
    unittest.main()
