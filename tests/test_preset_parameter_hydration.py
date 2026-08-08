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
from tools.parameters.codecs import ParameterCodecError, normalize_parameter_value
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
    def test_auto_wah_accepts_every_float32_tenth_from_point_one_to_ten(self) -> None:
        rate = CATALOG.effect_by_key("wah.auto_wah").parameters[1]
        for tenths in range(1, 101):
            expected = tenths / 10
            physical_float32 = struct.unpack(
                "<f", struct.pack("<f", expected)
            )[0]
            with self.subTest(rate=expected, physical_float32=physical_float32):
                normalized = normalize_parameter_value(physical_float32, rate)
                self.assertAlmostEqual(float(normalized), expected, places=7)

        with self.assertRaises(ParameterCodecError):
            normalize_parameter_value(4.25, rate)

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

    def test_tape_mod_hydrates_four_values_and_ignores_residual_selector(self) -> None:
        events = decode_saved_parameter_events(
            make_dump({
                (0, 0): 21,
                (0, 1): 43,
                (0, 2): 65,
                (0, 3): 87,
                (0, 4): 10,
            }),
            make_chain((0, "freq.tape_mod")),
        )
        self.assertEqual(
            tuple((event.parameter_key, event.value) for event in events),
            (
                ("saturation", 21),
                ("mix", 43),
                ("volume", 65),
                ("high_cut", 87),
            ),
        )

        state = EffectParameterState()
        for event in events:
            state.apply(event, origin="saved_preset_dump")
        snapshot = build_effect_snapshots(
            make_chain((0, "freq.tape_mod")), state
        )[0]
        self.assertEqual(
            tuple(parameter.display_value for parameter in snapshot.parameters),
            ("21", "43", "65", "87"),
        )

    def test_voks_wah_hydrates_four_values_and_ignores_residual_selectors(self) -> None:
        events = decode_saved_parameter_events(
            make_dump({
                (0, 0): 21,
                (0, 1): 43,
                (0, 2): 65,
                (0, 3): 87,
                (0, 4): 100,
                (0, 5): 100,
                (0, 6): 1,
            }),
            make_chain((0, "wah.voks_wah")),
        )
        self.assertEqual(
            tuple((event.parameter_key, event.value) for event in events),
            (
                ("range", 21),
                ("q", 43),
                ("volume", 65),
                ("position", 87),
            ),
        )

        state = EffectParameterState()
        for event in events:
            state.apply(event, origin="saved_preset_dump")
        snapshot = build_effect_snapshots(
            make_chain((0, "wah.voks_wah")), state
        )[0]
        self.assertEqual(
            tuple(parameter.display_value for parameter in snapshot.parameters),
            ("21", "43", "65", "87"),
        )

    def test_cry_wah_hydrates_four_values_and_ignores_residual_selectors(self) -> None:
        events = decode_saved_parameter_events(
            make_dump({
                (0, 0): 22,
                (0, 1): 44,
                (0, 2): 66,
                (0, 3): 88,
                (0, 4): 100,
                (0, 5): 100,
                (0, 6): 1,
            }),
            make_chain((0, "wah.cry_wah")),
        )
        self.assertEqual(
            tuple((event.parameter_key, event.value) for event in events),
            (
                ("range", 22),
                ("q", 44),
                ("volume", 66),
                ("position", 88),
            ),
        )

        state = EffectParameterState()
        for event in events:
            state.apply(event, origin="saved_preset_dump")
        snapshot = build_effect_snapshots(
            make_chain((0, "wah.cry_wah")), state
        )[0]
        self.assertEqual(
            tuple(parameter.display_value for parameter in snapshot.parameters),
            ("22", "44", "66", "88"),
        )

    def test_rack_wah_hydrates_eq_and_ignores_residual_selectors(self) -> None:
        events = decode_saved_parameter_events(
            make_dump({
                (0, 0): 21,
                (0, 1): 43,
                (0, 2): 65,
                (0, 3): 87,
                (0, 4): 0,
                (0, 5): 100,
                (0, 6): 1,
            }),
            make_chain((0, "wah.rack_wah")),
        )
        self.assertEqual(
            tuple((event.parameter_key, event.value) for event in events),
            (
                ("range", 21),
                ("q", 43),
                ("volume", 65),
                ("position", 87),
                ("eq", False),
            ),
        )

        state = EffectParameterState()
        for event in events:
            state.apply(event, origin="saved_preset_dump")
        snapshot = build_effect_snapshots(
            make_chain((0, "wah.rack_wah")), state
        )[0]
        self.assertEqual(
            tuple(parameter.display_value for parameter in snapshot.parameters),
            ("21", "43", "65", "87", "desligado"),
        )

    def test_inferred_bass_wah_hydrates_only_four_cataloged_selectors(self) -> None:
        events = decode_saved_parameter_events(
            make_dump({
                (0, 0): 31,
                (0, 1): 42,
                (0, 2): 53,
                (0, 3): 64,
                (0, 4): 100,
                (0, 5): 100,
                (0, 6): 1,
            }),
            make_chain((0, "wah.bass_wah")),
        )
        self.assertEqual(
            tuple((event.parameter_key, event.value) for event in events),
            (("range", 31), ("q", 42), ("volume", 53), ("position", 64)),
        )

    def test_touch_wah_hydrates_named_mode_and_ignores_residual_selectors(self) -> None:
        events = decode_saved_parameter_events(
            make_dump({
                (0, 0): 21,
                (0, 1): 43,
                (0, 2): 65,
                (0, 3): 87,
                (0, 4): 1,
                (0, 5): 100,
                (0, 6): 1,
            }),
            make_chain((0, "wah.touch_wah")),
        )
        self.assertEqual(
            tuple((event.parameter_key, event.value) for event in events),
            (
                ("sense", 21),
                ("range", 43),
                ("q", 65),
                ("mix", 87),
                ("mode", "BASS"),
            ),
        )

    def test_auto_wah_hydrates_sync_on_rate_domain(self) -> None:
        chain = make_chain((0, "wah.auto_wah"))
        events = decode_saved_parameter_events(
            make_dump({
                (0, 0): 22, (0, 1): 8, (0, 2): 44, (0, 3): 66,
                (0, 4): 88, (0, 5): 33, (0, 6): 1,
            }),
            chain,
        )
        self.assertEqual(
            tuple((event.parameter_key, event.value) for event in events),
            (
                ("sync", True), ("depth", 22), ("rate", 8),
                ("volume", 44), ("low", 66), ("q", 88), ("high", 33),
            ),
        )
        state = EffectParameterState()
        for event in events:
            state.apply(event, origin="saved_preset_dump")
        by_key = {
            parameter.key: parameter
            for parameter in build_effect_snapshots(chain, state)[0].parameters
        }
        self.assertEqual(by_key["rate"].display_value, "1/8D")

    def test_auto_wah_hydrates_decimal_rate_with_sync_off(self) -> None:
        chain = make_chain((0, "wah.auto_wah"))
        events = decode_saved_parameter_events(
            make_dump({
                (0, 0): 21, (0, 1): 3.7, (0, 2): 43, (0, 3): 65,
                (0, 4): 87, (0, 5): 32, (0, 6): 0,
            }),
            chain,
        )
        state = EffectParameterState()
        for event in events:
            state.apply(event, origin="saved_preset_dump")
        by_key = {
            parameter.key: parameter
            for parameter in build_effect_snapshots(chain, state)[0].parameters
        }
        self.assertAlmostEqual(float(by_key["rate"].value), 3.7, places=5)
        self.assertEqual(by_key["rate"].display_value, "3.7 Hz")
        self.assertEqual(by_key["sync"].value, False)

    def test_skreamer_hydrates_only_three_cataloged_values(self) -> None:
        events = decode_saved_parameter_events(
            make_dump({
                (0, 0): 21,
                (0, 1): 43,
                (0, 2): 65,
                (0, 3): 99,
            }),
            make_chain((0, "drv.skreamer")),
        )
        self.assertEqual(
            tuple((event.parameter_key, event.value) for event in events),
            (("gain", 21), ("tone", 43), ("volume", 65)),
        )

    def test_inferred_skreamer9_hydrates_the_shared_three_value_layout(self) -> None:
        events = decode_saved_parameter_events(
            make_dump({(0, 0): 31, (0, 1): 52, (0, 2): 73, (0, 3): 99}),
            make_chain((0, "drv.skreamer9")),
        )
        self.assertEqual(
            tuple((event.parameter_key, event.value) for event in events),
            (("gain", 31), ("tone", 52), ("volume", 73)),
        )

    def test_butter_od_ignores_residual_saved_selector_two(self) -> None:
        events = decode_saved_parameter_events(
            make_dump({(0, 0): 21, (0, 1): 65, (0, 2): 50}),
            make_chain((0, "drv.butter_od")),
        )
        self.assertEqual(
            tuple((event.parameter_key, event.value) for event in events),
            (("gain", 21), ("volume", 65)),
        )

    def test_inferred_warm_and_super_od_hydrate_three_shared_selectors(self) -> None:
        for effect_key in ("drv.warm_od", "drv.super_od"):
            with self.subTest(effect=effect_key):
                events = decode_saved_parameter_events(
                    make_dump({(0, 0): 23, (0, 1): 45, (0, 2): 67}),
                    make_chain((0, effect_key)),
                )
                self.assertEqual(
                    tuple((event.parameter_key, event.value) for event in events),
                    (("gain", 23), ("tone", 45), ("volume", 67)),
                )

    def test_blues_od_hydrates_three_inferred_selectors(self) -> None:
        events = decode_saved_parameter_events(
            make_dump({(0, 0): 21, (0, 1): 43, (0, 2): 65}),
            make_chain((0, "drv.blues_od")),
        )
        self.assertEqual(
            tuple((event.parameter_key, event.value) for event in events),
            (("gain", 21), ("tone", 43), ("volume", 65)),
        )

    def test_full_od_hydrates_three_controls_and_hp_mode(self) -> None:
        events = decode_saved_parameter_events(
            make_dump({(0, 0): 21, (0, 1): 43, (0, 2): 65, (0, 3): 1}),
            make_chain((0, "drv.full_od")),
        )
        self.assertEqual(
            tuple((event.parameter_key, event.value) for event in events),
            (("gain", 21), ("tone", 43), ("volume", 65), ("mode", "HP")),
        )

    def test_breaker_od_hydrates_three_inferred_selectors(self) -> None:
        events = decode_saved_parameter_events(
            make_dump({(0, 0): 22, (0, 1): 44, (0, 2): 66}),
            make_chain((0, "drv.breaker_od")),
        )
        self.assertEqual(
            tuple((event.parameter_key, event.value) for event in events),
            (("gain", 22), ("tone", 44), ("volume", 66)),
        )

    def test_gerden_od_hydrates_voice_as_fourth_selector(self) -> None:
        events = decode_saved_parameter_events(
            make_dump({(0, 0): 21, (0, 1): 43, (0, 2): 65, (0, 3): 87}),
            make_chain((0, "drv.gerden_od")),
        )
        self.assertEqual(
            tuple((event.parameter_key, event.value) for event in events),
            (("gain", 21), ("tone", 43), ("volume", 65), ("voice", 87)),
        )

    def test_timmy_od_hydrates_mode_ii_as_enum(self) -> None:
        events = decode_saved_parameter_events(
            make_dump({(0, 0): 21, (0, 1): 43, (0, 2): 65, (0, 3): 87, (0, 4): 1}),
            make_chain((0, "drv.timmy_od")),
        )
        self.assertEqual(
            tuple((event.parameter_key, event.value) for event in events),
            (("gain", 21), ("volume", 43), ("bass", 65), ("treble", 87), ("mode", "II")),
        )

    def test_master_od_hydrates_five_numeric_selectors(self) -> None:
        events = decode_saved_parameter_events(
            make_dump({(0, 0): 21, (0, 1): 43, (0, 2): 65, (0, 3): 87, (0, 4): 32}),
            make_chain((0, "drv.master_od")),
        )
        self.assertEqual(
            tuple((event.parameter_key, event.value) for event in events),
            (("gain", 21), ("volume", 43), ("bass", 65), ("middle", 87), ("treble", 32)),
        )

    def test_solar_fuzz_ignores_saved_residual_selectors(self) -> None:
        events = decode_saved_parameter_events(
            make_dump({(0, 0): 21, (0, 1): 65, (0, 2): 100, (0, 3): 100, (0, 4): 100}),
            make_chain((0, "drv.solar_fuzz")),
        )
        self.assertEqual(
            tuple((event.parameter_key, event.value) for event in events),
            (("fuzz", 21), ("volume", 65)),
        )

    def test_phase55_inferred_effects_hydrate_expected_selectors(self) -> None:
        cases = (
            ("drv.fuzz_cream", {(0, 0): 21, (0, 1): 43, (0, 2): 65}, (("sustain", 21), ("tone", 43), ("volume", 65))),
            ("drv.red_fuzz", {(0, 0): 22, (0, 1): 66}, (("fuzz", 22), ("volume", 66))),
            ("drv.jp_dist", {(0, 0): 23, (0, 1): 45, (0, 2): 67}, (("gain", 23), ("tone", 45), ("volume", 67))),
        )
        for effect_key, values, expected in cases:
            with self.subTest(effect=effect_key):
                events = decode_saved_parameter_events(
                    make_dump(values),
                    make_chain((0, effect_key)),
                )
                self.assertEqual(
                    tuple((event.parameter_key, event.value) for event in events),
                    expected,
                )

    def test_phase56_inferred_effects_hydrate_expected_selectors(self) -> None:
        cases = (
            ("drv.dark_mouse", {(0, 0): 21, (0, 1): 43, (0, 2): 65}, (("gain", 21), ("filter", 43), ("volume", 65))),
            ("drv.plexi_dist", {(0, 0): 11, (0, 1): 22, (0, 2): 33, (0, 3): 44, (0, 4): 55}, (("gain", 11), ("volume", 22), ("bass", 33), ("middle", 44), ("treble", 55))),
            ("drv.master_dist", {(0, 0): 12, (0, 1): 23, (0, 2): 34, (0, 3): 45, (0, 4): 56}, (("gain", 12), ("volume", 23), ("bass", 34), ("contour", 45), ("treble", 56))),
        )
        for effect_key, values, expected in cases:
            with self.subTest(effect=effect_key):
                events = decode_saved_parameter_events(
                    make_dump(values),
                    make_chain((0, effect_key)),
                )
                self.assertEqual(
                    tuple((event.parameter_key, event.value) for event in events),
                    expected,
                )

    def test_phase57_inferred_effects_hydrate_expected_selectors(self) -> None:
        cases = (
            ("drv.dist_plus", {(0, 0): 21, (0, 1): 65}, (("gain", 21), ("volume", 65))),
            ("drv.shark", {(0, 0): 22, (0, 1): 44, (0, 2): 66}, (("gain", 22), ("tone", 44), ("volume", 66))),
            ("drv.strive", {(0, 0): 23, (0, 1): 45, (0, 2): 67, (0, 3): 0}, (("gain", 23), ("tone", 45), ("volume", 67), ("mode", "I"))),
        )
        for effect_key, values, expected in cases:
            with self.subTest(effect=effect_key):
                events = decode_saved_parameter_events(
                    make_dump(values),
                    make_chain((0, effect_key)),
                )
                self.assertEqual(
                    tuple((event.parameter_key, event.value) for event in events),
                    expected,
                )

    def test_phase58_inferred_effects_hydrate_expected_selectors(self) -> None:
        cases = (
            (
                "drv.sardar_dist",
                {(0, 0): 21, (0, 1): 32, (0, 2): 43, (0, 3): 54, (0, 4): 65, (0, 5): 76},
                (("gain", 21), ("volume", 32), ("bass", 43), ("treble", 54), ("presence", 65), ("tight", 76)),
            ),
            (
                "drv.bass_od",
                {(0, 0): 22, (0, 1): 33, (0, 2): 44, (0, 3): 1, (0, 4): 66},
                (("gain", 22), ("tone", 33), ("volume", 44), ("mode", "SCOOP"), ("blend", 66)),
            ),
            (
                "drv.bass_dist",
                {(0, 0): 23, (0, 1): 34, (0, 2): 45, (0, 3): 56, (0, 4): 67},
                (("gain", 23), ("blend", 34), ("volume", 45), ("bass", 56), ("treble", 67)),
            ),
        )
        for effect_key, values, expected in cases:
            with self.subTest(effect=effect_key):
                events = decode_saved_parameter_events(make_dump(values), make_chain((0, effect_key)))
                self.assertEqual(tuple((event.parameter_key, event.value) for event in events), expected)

    def test_phase59_amp_effects_hydrate_expected_selectors_and_ignore_residuals(self) -> None:
        cases = (
            (
                "amp.twd_deluxe",
                {(0, 0): 21, (0, 1): 43, (0, 2): 65, (0, 3): 50, (0, 4): 50, (0, 5): 50},
                (("gain", 21), ("tone", 43), ("volume", 65)),
            ),
            (
                "amp.b_man_n",
                {(0, 0): 21, (0, 1): 32, (0, 2): 43, (0, 3): 54, (0, 4): 65, (0, 5): 76},
                (("gain", 21), ("presence", 32), ("volume", 43), ("bass", 54), ("middle", 65), ("treble", 76)),
            ),
            (
                "amp.b_man_bri",
                {(0, 0): 23, (0, 1): 34, (0, 2): 45, (0, 3): 56, (0, 4): 67, (0, 5): 78},
                (("gain", 23), ("presence", 34), ("volume", 45), ("bass", 56), ("middle", 67), ("treble", 78)),
            ),
        )
        for effect_key, values, expected in cases:
            with self.subTest(effect=effect_key):
                events = decode_saved_parameter_events(make_dump(values), make_chain((0, effect_key)))
                self.assertEqual(tuple((event.parameter_key, event.value) for event in events), expected)

    def test_phase61_amp_validated_hydrate_expected_selectors(self) -> None:
        cases = (
            (
                "amp.supero_2_od",
                {(0, 0): 11, (0, 1): 17, (0, 2): 23, (0, 3): 29, (0, 4): 31},
                (("gain_1", 11), ("tone_1", 17), ("gain_2", 23), ("tone_2", 29), ("volume", 31)),
            ),
            (
                "amp.voks_15tb",
                {(0, 0): 44, (0, 1): 52, (0, 2): 61, (0, 3): 68, (0, 4): 74},
                (("gain", 44), ("tone_cut", 52), ("volume", 61), ("bass", 68), ("treble", 74)),
            ),
            (
                "amp.voks_30n",
                {(0, 0): 83, (0, 1): 91, (0, 2): 97, (0, 3): 1},
                (("gain", 83), ("tone_cut", 91), ("volume", 97), ("bright", True)),
            ),
        )
        for effect_key, values, expected in cases:
            with self.subTest(effect=effect_key):
                events = decode_saved_parameter_events(make_dump(values), make_chain((0, effect_key)))
                self.assertEqual(tuple((event.parameter_key, event.value) for event in events), expected)

    def test_phase62_validated_amps_hydrate_expected_selectors(self) -> None:
        cases = (
            (
                "amp.voks_30tb",
                {(0, 0): 12, (0, 1): 18, (0, 2): 24, (0, 3): 29, (0, 4): 35, (0, 5): 1},
                (("gain", 12), ("tone_cut", 18), ("volume", 24), ("bass", 29), ("treble", 35), ("char", "HOT")),
            ),
            (
                "amp.jazz_120",
                {(0, 0): 46, (0, 1): 53, (0, 2): 61, (0, 3): 68, (0, 4): 1},
                (("gain", 46), ("bass", 53), ("middle", 61), ("treble", 68), ("bright", True)),
            ),
            (
                "amp.superb_cl",
                {(0, 0): 82, (0, 1): 87, (0, 2): 91, (0, 3): 94, (0, 4): 97, (0, 5): 100},
                (("gain", 82), ("presence", 87), ("volume", 91), ("bass", 94), ("middle", 97), ("treble", 100)),
            ),
        )
        for effect_key, values, expected in cases:
            with self.subTest(effect=effect_key):
                events = decode_saved_parameter_events(make_dump(values), make_chain((0, effect_key)))
                self.assertEqual(tuple((event.parameter_key, event.value) for event in events), expected)

    def test_phase63_validated_amps_hydrate_expected_selectors(self) -> None:
        cases = (
            (
                "amp.superb_od",
                {(0, 0): 11, (0, 1): 17, (0, 2): 23, (0, 3): 29, (0, 4): 34, (0, 5): 38},
                (("gain", 11), ("presence", 17), ("volume", 23), ("bass", 29), ("middle", 34), ("treble", 38)),
            ),
            (
                "amp.calif_star_cl",
                {(0, 0): 44, (0, 1): 51, (0, 2): 57, (0, 3): 63, (0, 4): 68, (0, 5): 74},
                (("gain", 44), ("presence", 51), ("volume", 57), ("bass", 63), ("middle", 68), ("treble", 74)),
            ),
            (
                "amp.calif_star_od",
                {(0, 0): 81, (0, 1): 86, (0, 2): 90, (0, 3): 93, (0, 4): 96, (0, 5): 98, (0, 6): 100},
                (("input", 81), ("gain", 86), ("presence", 90), ("volume", 93), ("bass", 96), ("middle", 98), ("treble", 100)),
            ),
        )
        for effect_key, values, expected in cases:
            with self.subTest(effect=effect_key):
                events = decode_saved_parameter_events(make_dump(values), make_chain((0, effect_key)))
                self.assertEqual(tuple((event.parameter_key, event.value) for event in events), expected)

    def test_phase64_validated_bog_amps_hydrate_expected_selectors(self) -> None:
        cases = (
            (
                "amp.bog_sv_cl",
                {(0, 0): 11, (0, 1): 17, (0, 2): 23, (0, 3): 29, (0, 4): 35, (0, 5): 1},
                (("gain", 11), ("presence", 17), ("volume", 23), ("bass", 29), ("treble", 35), ("bright", True)),
            ),
            (
                "amp.bog_sv_od",
                {(0, 0): 44, (0, 1): 51, (0, 2): 58, (0, 3): 64, (0, 4): 69, (0, 5): 74},
                (("gain", 44), ("presence", 51), ("volume", 58), ("bass", 64), ("middle", 69), ("treble", 74)),
            ),
            (
                "amp.bog_xt_blue",
                {(0, 0): 82, (0, 1): 87, (0, 2): 91, (0, 3): 94, (0, 4): 97, (0, 5): 100},
                (("gain", 82), ("presence", 87), ("volume", 91), ("bass", 94), ("middle", 97), ("treble", 100)),
            ),
        )
        for effect_key, values, expected in cases:
            with self.subTest(effect=effect_key):
                events = decode_saved_parameter_events(make_dump(values), make_chain((0, effect_key)))
                self.assertEqual(tuple((event.parameter_key, event.value) for event in events), expected)

    def test_phase65_validated_amps_hydrate_expected_selectors(self) -> None:
        cases = (
            (
                "amp.bog_xt_red",
                {(0, 0): 5, (0, 1): 10, (0, 2): 15, (0, 3): 20, (0, 4): 25, (0, 5): 30},
                (("gain", 5), ("presence", 10), ("volume", 15), ("bass", 20), ("middle", 25), ("treble", 30)),
            ),
            (
                "amp.doctor_cl",
                {(0, 0): 32, (0, 1): 37, (0, 2): 42, (0, 3): 47, (0, 4): 52, (0, 5): 57},
                (("gain", 32), ("tone_cut", 37), ("volume", 42), ("bass", 47), ("middle", 52), ("treble", 57)),
            ),
            (
                "amp.doctor_od",
                {(0, 0): 34, (0, 1): 39, (0, 2): 44, (0, 3): 49, (0, 4): 54, (0, 5): 59},
                (("gain", 34), ("tone_cut", 39), ("volume", 44), ("bass", 49), ("middle", 54), ("treble", 59)),
            ),
            (
                "amp.dragon_cl",
                {(0, 0): 61, (0, 1): 66, (0, 2): 71, (0, 3): 76, (0, 4): 81},
                (("gain", 61), ("volume", 66), ("bass", 71), ("middle", 76), ("treble", 81)),
            ),
            (
                "amp.dragon_cl_b",
                {(0, 0): 63, (0, 1): 68, (0, 2): 73, (0, 3): 78, (0, 4): 83},
                (("gain", 63), ("volume", 68), ("bass", 73), ("middle", 78), ("treble", 83)),
            ),
            (
                "amp.dragon_od",
                {(0, 0): 65, (0, 1): 70, (0, 2): 75, (0, 3): 80, (0, 4): 85},
                (("gain", 65), ("volume", 70), ("bass", 75), ("middle", 80), ("treble", 85)),
            ),
            (
                "amp.sol_100_cl",
                {(0, 0): 72, (0, 1): 78, (0, 2): 84, (0, 3): 90, (0, 4): 96, (0, 5): 100},
                (("gain", 72), ("presence", 78), ("volume", 84), ("bass", 90), ("middle", 96), ("treble", 100)),
            ),
            (
                "amp.sol_100_od",
                {(0, 0): 91, (0, 1): 83, (0, 2): 75, (0, 3): 67, (0, 4): 59, (0, 5): 51},
                (("gain", 91), ("presence", 83), ("volume", 75), ("bass", 67), ("middle", 59), ("treble", 51)),
            ),
        )
        for effect_key, values, expected in cases:
            with self.subTest(effect=effect_key):
                events = decode_saved_parameter_events(make_dump(values), make_chain((0, effect_key)))
                self.assertEqual(tuple((event.parameter_key, event.value) for event in events), expected)


    def test_phase66_candidate_amps_hydrate_expected_selectors(self) -> None:
        cases = (
            ("amp.sol_100_ld", {(0, 0): 3, (0, 1): 7, (0, 2): 11, (0, 3): 15, (0, 4): 19, (0, 5): 23}, (("gain", 3), ("presence", 7), ("volume", 11), ("bass", 15), ("middle", 19), ("treble", 23))),
            ("amp.brit_45", {(0, 0): 27, (0, 1): 31, (0, 2): 35, (0, 3): 39, (0, 4): 43, (0, 5): 47}, (("gain", 27), ("presence", 31), ("volume", 35), ("bass", 39), ("middle", 43), ("treble", 47))),
            ("amp.brit_45_plus", {(0, 0): 51, (0, 1): 55, (0, 2): 59, (0, 3): 63, (0, 4): 67, (0, 5): 71}, (("gain", 51), ("presence", 55), ("volume", 59), ("bass", 63), ("middle", 67), ("treble", 71))),
            ("amp.brit_45jp", {(0, 0): 4, (0, 1): 14, (0, 2): 24, (0, 3): 34, (0, 4): 44, (0, 5): 54, (0, 6): 64}, (("gain_1", 4), ("presence", 14), ("volume", 24), ("bass", 34), ("middle", 44), ("treble", 54), ("gain_2", 64))),
            ("amp.brit_50", {(0, 0): 28, (0, 1): 38, (0, 2): 48, (0, 3): 58, (0, 4): 68, (0, 5): 78}, (("gain", 28), ("presence", 38), ("volume", 48), ("bass", 58), ("middle", 68), ("treble", 78))),
            ("amp.brit_50_plus", {(0, 0): 33, (0, 1): 43, (0, 2): 53, (0, 3): 63, (0, 4): 73, (0, 5): 83}, (("gain", 33), ("presence", 43), ("volume", 53), ("bass", 63), ("middle", 73), ("treble", 83))),
            ("amp.brit_50jp", {(0, 0): 36, (0, 1): 46, (0, 2): 56, (0, 3): 66, (0, 4): 76, (0, 5): 86, (0, 6): 96}, (("gain_1", 36), ("presence", 46), ("volume", 56), ("bass", 66), ("middle", 76), ("treble", 86), ("gain_2", 96))),
            ("amp.brit_slp", {(0, 0): 61, (0, 1): 69, (0, 2): 77, (0, 3): 85, (0, 4): 93, (0, 5): 100}, (("gain", 61), ("presence", 69), ("volume", 77), ("bass", 85), ("middle", 93), ("treble", 100))),
            ("amp.brit_800", {(0, 0): 8, (0, 1): 18, (0, 2): 28, (0, 3): 38, (0, 4): 48, (0, 5): 58}, (("gain", 8), ("presence", 18), ("volume", 28), ("bass", 38), ("middle", 48), ("treble", 58))),
        )
        for effect_key, values, expected in cases:
            with self.subTest(effect=effect_key):
                events = decode_saved_parameter_events(make_dump(values), make_chain((0, effect_key)))
                self.assertEqual(tuple((event.parameter_key, event.value) for event in events), expected)

    def test_phase67_candidate_amps_hydrate_expected_selectors(self) -> None:
        cases = (
            ("amp.brit_900", (3, 9, 14, 20, 25, 32)),
            ("amp.flyman_1", (11, 18, 26, 34, 42, 50)),
            ("amp.flyman_2", (17, 27, 37, 47, 57, 67)),
            ("amp.flyman_plus_1", (23, 33, 43, 53, 63, 73)),
            ("amp.flyman_plus_2", (29, 39, 49, 59, 69, 79)),
            ("amp.calif_iic_plus_1", (35, 45, 55, 65, 75, 85)),
            ("amp.calif_iic_plus_2", (41, 51, 61, 71, 81, 91)),
            ("amp.calif_iic_plus_3", (47, 57, 67, 77, 87, 97)),
            ("amp.calif_iv_ld_1", (62, 73, 82, 88, 94, 100)),
        )
        keys = ("gain", "presence", "volume", "bass", "middle", "treble")
        for effect_key, observed in cases:
            with self.subTest(effect=effect_key):
                values = {(0, selector): value for selector, value in enumerate(observed)}
                events = decode_saved_parameter_events(make_dump(values), make_chain((0, effect_key)))
                self.assertEqual(
                    tuple((event.parameter_key, event.value) for event in events),
                    tuple(zip(keys, observed, strict=True)),
                )

    def test_phase68_amp_hydration_including_halen_selector_gap(self) -> None:
        standard_cases = (
            ("amp.calif_iv_ld_2", (3, 11, 19, 27, 35, 43), ("gain", "presence", "volume", "bass", "middle", "treble")),
            ("amp.calif_iv_ld_3", (8, 18, 28, 38, 48, 58), ("gain", "presence", "volume", "bass", "middle", "treble")),
            ("amp.calif_dual_v", (13, 23, 33, 43, 53, 63), ("gain", "presence", "volume", "bass", "middle", "treble")),
            ("amp.calif_dual_m", (17, 29, 41, 53, 65, 77), ("gain", "presence", "volume", "bass", "middle", "treble")),
            ("amp.tanger_r100", (21, 34, 47, 60, 73), ("gain", "volume", "bass", "middle", "treble")),
            ("amp.eng_120", (31, 45, 59, 73, 87, 100), ("gain", "presence", "volume", "bass", "middle", "treble")),
            ("amp.eng_120_plus", (36, 48, 60, 72, 84, 96), ("gain", "presence", "volume", "bass", "middle", "treble")),
            ("amp.dizzy_vh", (42, 53, 64, 75, 86, 97), ("gain", "presence", "volume", "bass", "middle", "treble")),
        )
        for effect_key, observed, keys in standard_cases:
            with self.subTest(effect=effect_key):
                values = {(0, selector): value for selector, value in enumerate(observed)}
                events = decode_saved_parameter_events(make_dump(values), make_chain((0, effect_key)))
                self.assertEqual(
                    tuple((event.parameter_key, event.value) for event in events),
                    tuple(zip(keys, observed, strict=True)),
                )

        halen_values = {
            (0, 0): 26,
            (0, 1): 39,
            (0, 2): 52,
            (0, 3): 65,
            (0, 4): 78,
            (0, 5): 0,   # selector oculto/não catalogado observado no teste físico
            (0, 6): 91,
        }
        halen_events = decode_saved_parameter_events(
            make_dump(halen_values),
            make_chain((0, "amp.halen_51")),
        )
        self.assertEqual(
            tuple((event.parameter_key, event.value) for event in halen_events),
            (("gain", 26), ("volume", 39), ("bass", 52), ("middle", 65), ("treble", 78), ("presence", 91)),
        )


    def test_phase69_final_amp_models_hydrate_expected_selectors(self) -> None:
        standard_cases = (
            ("amp.dizzy_vh_s", (11, 22, 33, 44, 55, 66), ("gain", "presence", "volume", "bass", "middle", "treble")),
            ("amp.dizzy_vh_plus", (17, 27, 37, 47, 57, 67), ("gain", "presence", "volume", "bass", "middle", "treble")),
            ("amp.dizzy_vh_plus_s", (23, 33, 43, 53, 63, 73), ("gain", "presence", "volume", "bass", "middle", "treble")),
            ("amp.voks_bass", (31, 51, 71), ("volume", "bass", "treble")),
            ("amp.cali_bass", (13, 29, 47, 65, 83), ("gain", "volume", "bass", "middle", "treble")),
            ("amp.a_bassft", (19, 49, 79), ("volume", "bass", "treble")),
            ("amp.ac_preamp", (12, 24, 36, 48, 60, 72), ("volume", "tone", "balance", "eq_freq", "eq_q", "eq_gain")),
            ("amp.ac_preamp_2", (18, 30, 42, 54, 66, 78), ("volume", "tone", "balance", "eq_freq", "eq_q", "eq_gain")),
        )
        for effect_key, observed, keys in standard_cases:
            with self.subTest(effect=effect_key):
                values = {(0, selector): value for selector, value in enumerate(observed)}
                events = decode_saved_parameter_events(make_dump(values), make_chain((0, effect_key)))
                self.assertEqual(
                    tuple((event.parameter_key, event.value) for event in events),
                    tuple(zip(keys, observed, strict=True)),
                )

        bassvt_events = decode_saved_parameter_events(
            make_dump({(0, 0): 9, (0, 1): 21, (0, 2): 35, (0, 3): 3, (0, 4): 77, (0, 5): 91}),
            make_chain((0, "amp.a_bassvt")),
        )
        self.assertEqual(
            tuple((event.parameter_key, event.value) for event in bassvt_events),
            (("gain", 9), ("bass", 21), ("middle", 35), ("midrange", "1.6KHZ"), ("treble", 77), ("volume", 91)),
        )

        f2_events = decode_saved_parameter_events(
            make_dump({(0, 0): 26, (0, 1): 1, (0, 2): 48, (0, 3): 69, (0, 4): 88}),
            make_chain((0, "amp.f_2bass")),
        )
        self.assertEqual(
            tuple((event.parameter_key, event.value) for event in f2_events),
            (("volume", 26), ("bright", True), ("bass", 48), ("middle", 69), ("treble", 88)),
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
