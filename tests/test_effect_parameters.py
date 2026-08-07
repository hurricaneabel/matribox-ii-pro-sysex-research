"""Testes do motor genérico de parâmetros e sua integração ao monitor."""

from __future__ import annotations

from pathlib import Path
import json
import unittest

from tools.commands.chain_order import ChainOrderState
from tools.commands.effect_catalog import CATALOG
from tools.commands.global_preset_metadata import GlobalPresetMetadata, PresetMetadata
from tools.commands.preset_monitor_core import PresetMonitorCore, format_monitor_snapshot
from tools.commands.preset_state import PresetEvent, build_select_preset
from tools.commands.structural_effect_state import StructuralEffectRecord
from tools.parameters import (
    EffectParameterProtocolError,
    EffectParameterState,
    parse_effect_parameter_response,
    parse_effect_parameter_signal,
    resolve_effect_parameter_signal,
)


MBOOST_FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "mboost_gain"
COMP1_FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "comp1_parameters"
COMP2_FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "comp2_parameters"
COMP3_FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "comp3_parameters"
AC_BOOST_FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "ac_boost_parameters"
BB_BOOST_FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "bb_boost_parameters"
RC_BOOST_FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "rc_boost_parameters"
FAT_BOOST_FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "fat_boost_parameters"
GATE2_FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "gate2_parameters"
GATE3_FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "gate3_parameters"
AC_SIM_FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "ac_sim_parameters"
EBOOST_FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "e_boost_parameters"
AC_WOODY_FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "ac_woody_parameters"
GATE1_FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "gate1_parameters"
FILTER_FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "filter_parameters"
OCTAVER_FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "octaver_parameters"
DUAL_MELODY_FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "dual_melody_parameters"


def make_chain(*, internal_slot_id: int, effect_key: str) -> ChainOrderState:
    effect = CATALOG.effect_by_key(effect_key)
    effect_class = CATALOG.class_by_key(effect.class_key)
    records = []
    enabled = [None] * 12

    for slot_id in range(12):
        active = slot_id == internal_slot_id
        records.append(
            StructuralEffectRecord(
                internal_slot_id=slot_id,
                active=active,
                class_id=effect_class.class_id if active else None,
                model_id=effect.model_id if active else None,
                auxiliary_1=0,
                auxiliary_2=0,
                secondary_selector=effect.secondary_selector if active else None,
                enabled=True if active else None,
            )
        )
        if active:
            enabled[slot_id] = True

    return ChainOrderState(
        internal_slot_ids=(internal_slot_id,),
        observed_checksum=0,
        declared_length_units=0,
        raw_message=b"",
        enabled_by_internal_slot=tuple(enabled),
        effect_records_by_internal_slot=tuple(records),
    )


def prepare_core(chain: ChainOrderState) -> PresetMonitorCore:
    core = PresetMonitorCore()
    presets = tuple(
        PresetMetadata(
            index=index,
            label=f"{index + 1:03d}",
            preset_id=index,
            name="Teste",
            filter_tag="",
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
    core.apply_chain_state(chain)
    return core


class GenericParameterDecoderTests(unittest.TestCase):
    def test_all_physical_mboost_fixtures_are_catalog_driven(self) -> None:
        fixtures = sorted(MBOOST_FIXTURE_ROOT.glob("*.bin"))
        self.assertEqual(len(fixtures), 27)

        for fixture in fixtures:
            with self.subTest(fixture=fixture.name):
                event = parse_effect_parameter_response(
                    fixture.read_bytes(),
                    effect_key="dyn.m_boost",
                )
                self.assertIsNotNone(event)
                assert event is not None
                self.assertEqual(event.effect_key, "dyn.m_boost")
                self.assertEqual(event.parameter_key, "gain")
                self.assertEqual(event.protocol_profile, "effect_parameter_response_1c_v1")
                self.assertEqual(event.value_codec, "upper_float32_nibbles_v1")
                self.assertEqual(event.parameter_name, "GAIN")

    def test_all_physical_comp1_fixtures_resolve_by_effect_context(self) -> None:
        fixtures = sorted(COMP1_FIXTURE_ROOT.glob("*.bin"))
        self.assertEqual(len(fixtures), 22)

        for fixture in fixtures:
            with self.subTest(fixture=fixture.name):
                event = parse_effect_parameter_response(
                    fixture.read_bytes(),
                    effect_key="dyn.comp1",
                )
                self.assertIsNotNone(event)
                assert event is not None
                parts = fixture.stem.split("_")
                expected_slot = int(parts[0].removeprefix("slot"))
                expected_parameter = parts[1]
                expected_value = int(parts[2])
                self.assertEqual(event.human_slot, expected_slot)
                self.assertEqual(event.effect_key, "dyn.comp1")
                self.assertEqual(event.parameter_key, expected_parameter)
                self.assertEqual(event.value, expected_value)

    def test_all_physical_comp2_fixtures_resolve_four_parameters(self) -> None:
        fixtures = sorted(COMP2_FIXTURE_ROOT.glob("*.bin"))
        self.assertEqual(len(fixtures), 49)

        for fixture in fixtures:
            with self.subTest(fixture=fixture.name):
                event = parse_effect_parameter_response(
                    fixture.read_bytes(),
                    effect_key="dyn.comp2",
                )
                self.assertIsNotNone(event)
                assert event is not None
                parts = fixture.stem.split("_")
                expected_slot = int(parts[0].removeprefix("slot"))
                expected_parameter = parts[1]
                expected_value = int(parts[2])
                self.assertEqual(event.human_slot, expected_slot)
                self.assertEqual(event.effect_key, "dyn.comp2")
                self.assertEqual(event.parameter_key, expected_parameter)
                self.assertEqual(event.value, expected_value)


    def test_all_physical_comp3_fixtures_resolve_seven_parameters(self) -> None:
        fixtures = sorted(COMP3_FIXTURE_ROOT.glob("*.bin"))
        self.assertEqual(len(fixtures), 84)

        expected_parameters = {
            "threshold",
            "ratio",
            "volume",
            "attack",
            "release",
            "tone",
            "blend",
        }
        observed_parameters = set()
        for fixture in fixtures:
            with self.subTest(fixture=fixture.name):
                event = parse_effect_parameter_response(
                    fixture.read_bytes(),
                    effect_key="dyn.comp3",
                )
                self.assertIsNotNone(event)
                assert event is not None
                parts = fixture.stem.split("_")
                expected_slot = int(parts[0].removeprefix("slot"))
                expected_parameter = parts[1]
                expected_value = int(parts[2])
                observed_parameters.add(event.parameter_key)
                self.assertEqual(event.human_slot, expected_slot)
                self.assertEqual(event.effect_key, "dyn.comp3")
                self.assertEqual(event.parameter_key, expected_parameter)
                self.assertEqual(event.value, expected_value)

        self.assertEqual(observed_parameters, expected_parameters)

    def test_all_physical_ac_and_bb_boost_fixtures_resolve_four_parameters(self) -> None:
        expected_parameters = {"gain", "volume", "bass", "treble"}
        for fixture_root, effect_key in (
            (AC_BOOST_FIXTURE_ROOT, "dyn.ac_boost"),
            (BB_BOOST_FIXTURE_ROOT, "dyn.bb_boost"),
        ):
            fixtures = sorted(fixture_root.glob("*.bin"))
            self.assertEqual(len(fixtures), 32)
            observed_parameters = set()
            for fixture in fixtures:
                with self.subTest(effect=effect_key, fixture=fixture.name):
                    event = parse_effect_parameter_response(
                        fixture.read_bytes(),
                        effect_key=effect_key,
                    )
                    self.assertIsNotNone(event)
                    assert event is not None
                    parts = fixture.stem.split("_")
                    expected_slot = int(parts[0].removeprefix("slot"))
                    expected_parameter = parts[1]
                    expected_value = int(parts[2])
                    observed_parameters.add(event.parameter_key)
                    self.assertEqual(event.human_slot, expected_slot)
                    self.assertEqual(event.effect_key, effect_key)
                    self.assertEqual(event.parameter_key, expected_parameter)
                    self.assertEqual(event.value, expected_value)
            self.assertEqual(observed_parameters, expected_parameters)

    def test_phase30_physical_fixtures_resolve_by_effect_context(self) -> None:
        configurations = (
            (
                RC_BOOST_FIXTURE_ROOT,
                "dyn.rc_boost",
                32,
                {"gain", "volume", "bass", "treble"},
            ),
            (
                FAT_BOOST_FIXTURE_ROOT,
                "dyn.fat_boost",
                28,
                {"bass", "treble", "volume", "low_cut"},
            ),
            (
                GATE2_FIXTURE_ROOT,
                "dyn.gate_2",
                23,
                {"threshold", "attack", "release"},
            ),
        )
        for fixture_root, effect_key, fixture_count, expected_parameters in configurations:
            fixtures = sorted(fixture_root.glob("*.bin"))
            self.assertEqual(len(fixtures), fixture_count)
            observed_parameters = set()
            for fixture in fixtures:
                with self.subTest(effect=effect_key, fixture=fixture.name):
                    event = parse_effect_parameter_response(
                        fixture.read_bytes(),
                        effect_key=effect_key,
                    )
                    self.assertIsNotNone(event)
                    assert event is not None
                    parts = fixture.stem.split("_")
                    expected_slot = int(parts[0].removeprefix("slot"))
                    expected_token = parts[-1]
                    expected_parameter = "_".join(parts[1:-1])
                    observed_parameters.add(event.parameter_key)
                    self.assertEqual(event.human_slot, expected_slot)
                    self.assertEqual(event.effect_key, effect_key)
                    self.assertEqual(event.parameter_key, expected_parameter)
                    if expected_token in {"on", "off"}:
                        self.assertIs(event.value, expected_token == "on")
                    else:
                        self.assertEqual(event.value, int(expected_token))
            self.assertEqual(observed_parameters, expected_parameters)

    def test_all_physical_e_boost_fixtures_decode_by_effect_context(self) -> None:
        fixtures = sorted(EBOOST_FIXTURE_ROOT.glob("*.bin"))
        self.assertEqual(len(fixtures), 19)

        for fixture in fixtures:
            with self.subTest(fixture=fixture.name):
                event = parse_effect_parameter_response(
                    fixture.read_bytes(),
                    effect_key="dyn.e_boost",
                )
                self.assertIsNotNone(event)
                assert event is not None
                parts = fixture.stem.split("_")
                expected_slot = int(parts[0].removeprefix("slot"))
                expected_parameter = "_".join(parts[1:-1])
                expected_token = parts[-1]
                self.assertEqual(event.human_slot, expected_slot)
                self.assertEqual(event.effect_key, "dyn.e_boost")
                self.assertEqual(event.parameter_key, expected_parameter)
                if expected_token in {"on", "off"}:
                    self.assertIs(event.value, expected_token == "on")
                else:
                    self.assertEqual(event.value, int(expected_token))

    def test_all_physical_ac_woody_fixtures_decode_by_effect_context(self) -> None:
        fixtures = sorted(AC_WOODY_FIXTURE_ROOT.glob("*.bin"))
        self.assertEqual(len(fixtures), 11)

        for fixture in fixtures:
            with self.subTest(fixture=fixture.name):
                event = parse_effect_parameter_response(
                    fixture.read_bytes(),
                    effect_key="dyn.ac_woody",
                )
                self.assertIsNotNone(event)
                assert event is not None
                parts = fixture.stem.split("_")
                self.assertEqual(event.human_slot, int(parts[0].removeprefix("slot")))
                self.assertEqual(event.effect_key, "dyn.ac_woody")
                self.assertEqual(event.parameter_key, "shape")
                self.assertEqual(event.value, int(parts[-1]))

    def test_all_physical_gate1_fixtures_decode_by_effect_context(self) -> None:
        fixtures = sorted(GATE1_FIXTURE_ROOT.glob("*.bin"))
        self.assertEqual(len(fixtures), 11)

        for fixture in fixtures:
            with self.subTest(fixture=fixture.name):
                event = parse_effect_parameter_response(
                    fixture.read_bytes(),
                    effect_key="dyn.gate_1",
                )
                self.assertIsNotNone(event)
                assert event is not None
                parts = fixture.stem.split("_")
                self.assertEqual(event.human_slot, int(parts[0].removeprefix("slot")))
                self.assertEqual(event.effect_key, "dyn.gate_1")
                self.assertEqual(event.parameter_key, "threshold")
                self.assertEqual(event.value, int(parts[-1]))

    def test_e_boost_boolean_display_is_localized(self) -> None:
        on_event = parse_effect_parameter_response(
            (EBOOST_FIXTURE_ROOT / "slot1_plus_3db_on.bin").read_bytes(),
            effect_key="dyn.e_boost",
        )
        off_event = parse_effect_parameter_response(
            (EBOOST_FIXTURE_ROOT / "slot1_bright_off.bin").read_bytes(),
            effect_key="dyn.e_boost",
        )
        assert on_event is not None and off_event is not None
        self.assertIs(on_event.value, True)
        self.assertEqual(on_event.display_value, "ligado")
        self.assertIs(off_event.value, False)
        self.assertEqual(off_event.display_value, "desligado")

    def test_e_boost_boolean_rejects_numeric_value_two(self) -> None:
        message = bytearray(
            (EBOOST_FIXTURE_ROOT / "slot1_plus_3db_on.bin").read_bytes()
        )
        message[59:63] = bytes((0x00, 0x00, 0x04, 0x00))
        with self.assertRaises(EffectParameterProtocolError):
            parse_effect_parameter_response(message, effect_key="dyn.e_boost")

    def test_same_selector_zero_requires_chain_effect_context(self) -> None:
        message = (COMP1_FIXTURE_ROOT / "slot1_sustain_050.bin").read_bytes()

        with self.assertRaises(EffectParameterProtocolError):
            parse_effect_parameter_response(message)

        comp1 = parse_effect_parameter_response(message, effect_key="dyn.comp1")
        comp2 = parse_effect_parameter_response(message, effect_key="dyn.comp2")
        mboost = parse_effect_parameter_response(message, effect_key="dyn.m_boost")
        assert comp1 is not None and comp2 is not None and mboost is not None
        self.assertEqual(comp1.parameter_key, "sustain")
        self.assertEqual(comp2.parameter_key, "sustain")
        self.assertEqual(mboost.parameter_key, "gain")
        self.assertEqual(comp1.value, 50)
        self.assertEqual(comp2.value, 50)
        self.assertEqual(mboost.value, 50)

    def test_signal_exposes_slot_selector_and_shared_parameter_address(self) -> None:
        signal = parse_effect_parameter_signal(
            (COMP1_FIXTURE_ROOT / "slot2_volume_051.bin").read_bytes()
        )
        self.assertIsNotNone(signal)
        assert signal is not None
        self.assertEqual(signal.human_slot, 2)
        self.assertEqual(signal.class_id, 0)
        self.assertEqual(signal.parameter_address, 0x14)
        self.assertEqual(signal.parameter_selector, 1)

    def test_signal_can_be_resolved_after_chain_lookup(self) -> None:
        signal = parse_effect_parameter_signal(
            (COMP1_FIXTURE_ROOT / "slot2_sustain_051.bin").read_bytes()
        )
        assert signal is not None
        event = resolve_effect_parameter_signal(signal, "dyn.comp1")
        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event.parameter_key, "sustain")
        self.assertEqual(event.value, 51)
        self.assertEqual(event.model_id, 0)

    def test_fixed_segment_mismatch_is_ignored(self) -> None:
        message = bytearray((MBOOST_FIXTURE_ROOT / "slot1_gain_050.bin").read_bytes())
        message[30] ^= 0x01
        self.assertIsNone(parse_effect_parameter_signal(message))

    def test_invalid_cataloged_value_is_rejected_after_context_resolution(self) -> None:
        message = bytearray((MBOOST_FIXTURE_ROOT / "slot1_gain_100.bin").read_bytes())
        message[59:63] = bytes((0x0C, 0x0A, 0x04, 0x02))  # float superior de 101
        with self.assertRaises(EffectParameterProtocolError):
            parse_effect_parameter_response(message, effect_key="dyn.m_boost")

    def test_event_exposes_portable_human_fields(self) -> None:
        event = parse_effect_parameter_response(
            (MBOOST_FIXTURE_ROOT / "slot2_skreamer_gain_050.bin").read_bytes(),
            effect_key="dyn.m_boost",
        )
        assert event is not None
        self.assertEqual(event.human_slot, 2)
        self.assertEqual(event.class_key, "dyn")
        self.assertEqual(event.class_name, "DYN")
        self.assertEqual(event.effect_name, "M-BOOST")
        self.assertEqual(event.value, 50)
        self.assertEqual(event.display_value, "50")


class ParameterStateTests(unittest.TestCase):
    def test_multiple_instances_keep_independent_values(self) -> None:
        state = EffectParameterState()
        first = parse_effect_parameter_response(
            (MBOOST_FIXTURE_ROOT / "slot1_gain_050.bin").read_bytes(),
            effect_key="dyn.m_boost",
        )
        second = parse_effect_parameter_response(
            (MBOOST_FIXTURE_ROOT / "slot2_skreamer_gain_075.bin").read_bytes(),
            effect_key="dyn.m_boost",
        )
        assert first is not None and second is not None

        state.apply(first)
        state.apply(second)

        self.assertEqual(state.event_for(0, "dyn.m_boost", "gain").value, 50)
        self.assertEqual(state.event_for(1, "dyn.m_boost", "gain").value, 75)

    def test_multiple_parameters_in_same_effect_keep_independent_values(self) -> None:
        state = EffectParameterState()
        sustain = parse_effect_parameter_response(
            (COMP1_FIXTURE_ROOT / "slot2_sustain_051.bin").read_bytes(),
            effect_key="dyn.comp1",
        )
        volume = parse_effect_parameter_response(
            (COMP1_FIXTURE_ROOT / "slot2_volume_050.bin").read_bytes(),
            effect_key="dyn.comp1",
        )
        assert sustain is not None and volume is not None
        state.apply(sustain)
        state.apply(volume)
        self.assertEqual(state.event_for(1, "dyn.comp1", "sustain").value, 51)
        self.assertEqual(state.event_for(1, "dyn.comp1", "volume").value, 50)

    def test_comp2_four_parameters_keep_independent_values(self) -> None:
        state = EffectParameterState()
        expected = {
            "sustain": 51,
            "attack": 52,
            "volume": 53,
            "clipping": 54,
        }
        for parameter, value in expected.items():
            event = parse_effect_parameter_response(
                (COMP2_FIXTURE_ROOT / f"slot2_{parameter}_{value:03d}.bin").read_bytes(),
                effect_key="dyn.comp2",
            )
            assert event is not None
            state.apply(event)

        self.assertEqual(
            {
                parameter: state.event_for(1, "dyn.comp2", parameter).value
                for parameter in expected
            },
            expected,
        )


    def test_comp3_seven_parameters_keep_independent_values(self) -> None:
        state = EffectParameterState()
        expected = {
            "threshold": 51,
            "ratio": 52,
            "volume": 53,
            "attack": 54,
            "release": 55,
            "tone": 56,
            "blend": 57,
        }
        for parameter, value in expected.items():
            event = parse_effect_parameter_response(
                (COMP3_FIXTURE_ROOT / f"slot2_{parameter}_{value:03d}.bin").read_bytes(),
                effect_key="dyn.comp3",
            )
            assert event is not None
            state.apply(event)

        self.assertEqual(
            {
                parameter: state.event_for(1, "dyn.comp3", parameter).value
                for parameter in expected
            },
            expected,
        )

    def test_ac_and_bb_boost_parameters_keep_independent_values(self) -> None:
        expected = {
            "gain": 51,
            "volume": 52,
            "bass": 53,
            "treble": 54,
        }
        for fixture_root, effect_key in (
            (AC_BOOST_FIXTURE_ROOT, "dyn.ac_boost"),
            (BB_BOOST_FIXTURE_ROOT, "dyn.bb_boost"),
        ):
            with self.subTest(effect=effect_key):
                state = EffectParameterState()
                for parameter, value in expected.items():
                    event = parse_effect_parameter_response(
                        (
                            fixture_root
                            / f"slot2_{parameter}_{value:03d}.bin"
                        ).read_bytes(),
                        effect_key=effect_key,
                    )
                    assert event is not None
                    state.apply(event)

                self.assertEqual(
                    {
                        parameter: state.event_for(
                            1,
                            effect_key,
                            parameter,
                        ).value
                        for parameter in expected
                    },
                    expected,
                )

    def test_retain_effects_discards_stale_slot_value(self) -> None:
        state = EffectParameterState()
        event = parse_effect_parameter_response(
            (MBOOST_FIXTURE_ROOT / "slot1_gain_050.bin").read_bytes(),
            effect_key="dyn.m_boost",
        )
        assert event is not None
        state.apply(event)
        state.retain_effects({0: "drv.skreamer"})
        self.assertIsNone(state.event_for(0, "dyn.m_boost", "gain"))


class ParameterMonitorIntegrationTests(unittest.TestCase):
    def test_monitor_lists_cataloged_parameter_before_first_event(self) -> None:
        core = prepare_core(make_chain(internal_slot_id=1, effect_key="dyn.m_boost"))
        snapshot = core.snapshot
        assert snapshot is not None
        formatted = format_monitor_snapshot(snapshot)

        self.assertIn("DYN / M-BOOST — ligado", formatted)
        self.assertIn("GAIN: aguardando alteração", formatted)

    def test_monitor_lists_two_comp1_parameters_in_catalog_order(self) -> None:
        core = prepare_core(make_chain(internal_slot_id=0, effect_key="dyn.comp1"))
        snapshot = core.snapshot
        assert snapshot is not None
        self.assertEqual(
            tuple(parameter.name for parameter in snapshot.effects[0].parameters),
            ("SUSTAIN", "VOLUME"),
        )
        formatted = format_monitor_snapshot(snapshot)
        self.assertIn("SUSTAIN: aguardando alteração", formatted)
        self.assertIn("VOLUME: aguardando alteração", formatted)

    def test_monitor_lists_comp2_parameters_in_catalog_order(self) -> None:
        core = prepare_core(make_chain(internal_slot_id=0, effect_key="dyn.comp2"))
        snapshot = core.snapshot
        assert snapshot is not None
        self.assertEqual(
            tuple(parameter.name for parameter in snapshot.effects[0].parameters),
            ("SUSTAIN", "ATTACK", "VOLUME", "CLIPPING"),
        )
        formatted = format_monitor_snapshot(snapshot)
        for parameter_name in ("SUSTAIN", "ATTACK", "VOLUME", "CLIPPING"):
            self.assertIn(f"{parameter_name}: aguardando alteração", formatted)


    def test_monitor_lists_comp3_parameters_in_catalog_order(self) -> None:
        core = prepare_core(make_chain(internal_slot_id=0, effect_key="dyn.comp3"))
        snapshot = core.snapshot
        assert snapshot is not None
        expected_names = (
            "THRESHOLD",
            "RATIO",
            "VOLUME",
            "ATTACK",
            "RELEASE",
            "TONE",
            "BLEND",
        )
        self.assertEqual(
            tuple(parameter.name for parameter in snapshot.effects[0].parameters),
            expected_names,
        )
        formatted = format_monitor_snapshot(snapshot)
        for parameter_name in expected_names:
            self.assertIn(f"{parameter_name}: aguardando alteração", formatted)

    def test_monitor_lists_ac_and_bb_boost_parameters_in_catalog_order(self) -> None:
        expected_names = ("GAIN", "VOLUME", "BASS", "TREBLE")
        for effect_key in ("dyn.ac_boost", "dyn.bb_boost"):
            with self.subTest(effect=effect_key):
                core = prepare_core(
                    make_chain(internal_slot_id=0, effect_key=effect_key)
                )
                snapshot = core.snapshot
                assert snapshot is not None
                self.assertEqual(
                    tuple(
                        parameter.name
                        for parameter in snapshot.effects[0].parameters
                    ),
                    expected_names,
                )
                formatted = format_monitor_snapshot(snapshot)
                for parameter_name in expected_names:
                    self.assertIn(
                        f"{parameter_name}: aguardando alteração",
                        formatted,
                    )

    def test_monitor_lists_e_boost_parameters_in_catalog_order(self) -> None:
        core = prepare_core(make_chain(internal_slot_id=0, effect_key="dyn.e_boost"))
        snapshot = core.snapshot
        assert snapshot is not None
        self.assertEqual(
            tuple(parameter.name for parameter in snapshot.effects[0].parameters),
            ("GAIN", "+3dB", "BRIGHT"),
        )
        formatted = format_monitor_snapshot(snapshot)
        self.assertIn("GAIN: aguardando alteração", formatted)
        self.assertIn("+3dB: aguardando alteração", formatted)
        self.assertIn("BRIGHT: aguardando alteração", formatted)

    def test_monitor_lists_ac_woody_shape(self) -> None:
        core = prepare_core(make_chain(internal_slot_id=0, effect_key="dyn.ac_woody"))
        snapshot = core.snapshot
        assert snapshot is not None
        self.assertEqual(
            tuple(parameter.name for parameter in snapshot.effects[0].parameters),
            ("SHAPE",),
        )
        self.assertIn("SHAPE: aguardando alteração", format_monitor_snapshot(snapshot))

    def test_monitor_lists_gate1_threshold(self) -> None:
        core = prepare_core(make_chain(internal_slot_id=0, effect_key="dyn.gate_1"))
        snapshot = core.snapshot
        assert snapshot is not None
        self.assertEqual(
            tuple(parameter.name for parameter in snapshot.effects[0].parameters),
            ("THRESHOLD",),
        )
        self.assertIn(
            "THRESHOLD: aguardando alteração",
            format_monitor_snapshot(snapshot),
        )

    def test_live_events_update_e_boost_parameters_independently(self) -> None:
        core = prepare_core(make_chain(internal_slot_id=1, effect_key="dyn.e_boost"))

        for filename in (
            "slot2_gain_051.bin",
            "slot2_plus_3db_on.bin",
            "slot2_bright_off.bin",
        ):
            update = core.feed((EBOOST_FIXTURE_ROOT / filename).read_bytes())
            self.assertIsNotNone(update.parameter_event)

        assert update.snapshot is not None
        parameters = update.snapshot.effects[0].parameters
        self.assertEqual(
            tuple(parameter.value for parameter in parameters),
            (51, True, False),
        )
        formatted = format_monitor_snapshot(update.snapshot)
        self.assertIn("GAIN: 51", formatted)
        self.assertIn("+3dB: ligado", formatted)
        self.assertIn("BRIGHT: desligado", formatted)

    def test_live_event_updates_ac_woody_shape(self) -> None:
        core = prepare_core(make_chain(internal_slot_id=1, effect_key="dyn.ac_woody"))
        update = core.feed(
            (AC_WOODY_FIXTURE_ROOT / "slot2_shape_051.bin").read_bytes()
        )
        self.assertIsNotNone(update.parameter_event)
        assert update.snapshot is not None
        self.assertEqual(update.snapshot.effects[0].parameters[0].value, 51)
        self.assertIn("SHAPE: 51", format_monitor_snapshot(update.snapshot))

    def test_live_event_updates_gate1_threshold(self) -> None:
        core = prepare_core(make_chain(internal_slot_id=1, effect_key="dyn.gate_1"))
        update = core.feed(
            (GATE1_FIXTURE_ROOT / "slot2_threshold_051.bin").read_bytes()
        )
        self.assertIsNotNone(update.parameter_event)
        assert update.snapshot is not None
        self.assertEqual(update.snapshot.effects[0].parameters[0].value, 51)
        self.assertIn("THRESHOLD: 51", format_monitor_snapshot(update.snapshot))

    def test_live_events_update_comp1_parameters_independently(self) -> None:
        core = prepare_core(make_chain(internal_slot_id=1, effect_key="dyn.comp1"))

        sustain_update = core.feed(
            (COMP1_FIXTURE_ROOT / "slot2_sustain_051.bin").read_bytes()
        )
        self.assertIsNotNone(sustain_update.parameter_event)
        assert sustain_update.snapshot is not None
        parameters = sustain_update.snapshot.effects[0].parameters
        self.assertEqual(parameters[0].value, 51)
        self.assertIsNone(parameters[1].value)

        volume_update = core.feed(
            (COMP1_FIXTURE_ROOT / "slot2_volume_050.bin").read_bytes()
        )
        self.assertIsNotNone(volume_update.parameter_event)
        assert volume_update.snapshot is not None
        parameters = volume_update.snapshot.effects[0].parameters
        self.assertEqual(parameters[0].value, 51)
        self.assertEqual(parameters[1].value, 50)
        formatted = format_monitor_snapshot(volume_update.snapshot)
        self.assertIn("SUSTAIN: 51", formatted)
        self.assertIn("VOLUME: 50", formatted)

    def test_live_events_update_comp2_parameters_independently(self) -> None:
        core = prepare_core(make_chain(internal_slot_id=1, effect_key="dyn.comp2"))
        sequence = (
            ("sustain", 51),
            ("attack", 52),
            ("volume", 53),
            ("clipping", 54),
        )
        for parameter, value in sequence:
            update = core.feed(
                (COMP2_FIXTURE_ROOT / f"slot2_{parameter}_{value:03d}.bin").read_bytes()
            )
            self.assertIsNotNone(update.parameter_event)

        assert update.snapshot is not None
        parameters = update.snapshot.effects[0].parameters
        self.assertEqual(
            tuple(parameter.value for parameter in parameters),
            (51, 52, 53, 54),
        )
        formatted = format_monitor_snapshot(update.snapshot)
        for name, value in (("SUSTAIN", 51), ("ATTACK", 52), ("VOLUME", 53), ("CLIPPING", 54)):
            self.assertIn(f"{name}: {value}", formatted)


    def test_live_events_update_comp3_parameters_independently(self) -> None:
        core = prepare_core(make_chain(internal_slot_id=1, effect_key="dyn.comp3"))
        sequence = (
            ("threshold", 51),
            ("ratio", 52),
            ("volume", 53),
            ("attack", 54),
            ("release", 55),
            ("tone", 56),
            ("blend", 57),
        )
        for parameter, value in sequence:
            update = core.feed(
                (COMP3_FIXTURE_ROOT / f"slot2_{parameter}_{value:03d}.bin").read_bytes()
            )
            self.assertIsNotNone(update.parameter_event)

        assert update.snapshot is not None
        parameters = update.snapshot.effects[0].parameters
        self.assertEqual(
            tuple(parameter.value for parameter in parameters),
            (51, 52, 53, 54, 55, 56, 57),
        )
        formatted = format_monitor_snapshot(update.snapshot)
        for name, value in (
            ("THRESHOLD", 51),
            ("RATIO", 52),
            ("VOLUME", 53),
            ("ATTACK", 54),
            ("RELEASE", 55),
            ("TONE", 56),
            ("BLEND", 57),
        ):
            self.assertIn(f"{name}: {value}", formatted)

    def test_live_events_update_ac_and_bb_boost_parameters_independently(self) -> None:
        sequence = (
            ("gain", 51),
            ("volume", 52),
            ("bass", 53),
            ("treble", 54),
        )
        for fixture_root, effect_key in (
            (AC_BOOST_FIXTURE_ROOT, "dyn.ac_boost"),
            (BB_BOOST_FIXTURE_ROOT, "dyn.bb_boost"),
        ):
            with self.subTest(effect=effect_key):
                core = prepare_core(
                    make_chain(internal_slot_id=1, effect_key=effect_key)
                )
                for parameter, value in sequence:
                    update = core.feed(
                        (
                            fixture_root
                            / f"slot2_{parameter}_{value:03d}.bin"
                        ).read_bytes()
                    )
                    self.assertIsNotNone(update.parameter_event)

                assert update.snapshot is not None
                parameters = update.snapshot.effects[0].parameters
                self.assertEqual(
                    tuple(parameter.value for parameter in parameters),
                    (51, 52, 53, 54),
                )
                formatted = format_monitor_snapshot(update.snapshot)
                for name, value in (
                    ("GAIN", 51),
                    ("VOLUME", 52),
                    ("BASS", 53),
                    ("TREBLE", 54),
                ):
                    self.assertIn(f"{name}: {value}", formatted)

    def test_live_events_update_phase30_effects_independently(self) -> None:
        cases = (
            (
                RC_BOOST_FIXTURE_ROOT,
                "dyn.rc_boost",
                (("gain", 51), ("volume", 52), ("bass", 53), ("treble", 54)),
                ("GAIN", "VOLUME", "BASS", "TREBLE"),
            ),
            (
                FAT_BOOST_FIXTURE_ROOT,
                "dyn.fat_boost",
                (("bass", 51), ("treble", 52), ("volume", 53), ("low_cut", True)),
                ("BASS", "TREBLE", "VOLUME", "LOW CUT"),
            ),
            (
                GATE2_FIXTURE_ROOT,
                "dyn.gate_2",
                (("threshold", 51), ("attack", 52), ("release", 53)),
                ("THRESHOLD", "ATTACK", "RELEASE"),
            ),
        )
        for fixture_root, effect_key, sequence, names in cases:
            with self.subTest(effect=effect_key):
                core = prepare_core(make_chain(internal_slot_id=0, effect_key=effect_key))
                for parameter, value in sequence:
                    token = "on" if value is True else f"{value:03d}"
                    update = core.feed(
                        (fixture_root / f"slot1_{parameter}_{token}.bin").read_bytes()
                    )
                    self.assertIsNotNone(update.parameter_event)
                assert update.snapshot is not None
                values = tuple(parameter.value for parameter in update.snapshot.effects[0].parameters)
                self.assertEqual(values, tuple(value for _, value in sequence))
                formatted = format_monitor_snapshot(update.snapshot)
                for name, value in zip(names, values):
                    display = "ligado" if value is True else str(value)
                    self.assertIn(f"{name}: {display}", formatted)

    def test_chain_context_resolves_selector_zero_as_mboost_gain(self) -> None:
        core = prepare_core(make_chain(internal_slot_id=0, effect_key="dyn.m_boost"))
        update = core.feed(
            (COMP1_FIXTURE_ROOT / "slot1_sustain_050.bin").read_bytes()
        )
        self.assertIsNotNone(update.parameter_event)
        assert update.parameter_event is not None
        self.assertEqual(update.parameter_event.effect_key, "dyn.m_boost")
        self.assertEqual(update.parameter_event.parameter_key, "gain")

    def test_event_for_other_effect_in_same_slot_is_ignored(self) -> None:
        pending_effect_key = next(
            model.key
            for effect_class in CATALOG.classes
            for model in effect_class.models
            if model.parameter_catalog_status == "pending"
        )
        core = prepare_core(
            make_chain(internal_slot_id=1, effect_key=pending_effect_key)
        )
        update = core.feed(
            (MBOOST_FIXTURE_ROOT / "slot2_skreamer_gain_050.bin").read_bytes()
        )

        self.assertIsNone(update.parameter_event)
        self.assertFalse(update.snapshot_changed)
        assert update.snapshot is not None
        self.assertEqual(update.snapshot.effects[0].parameters, ())

    def test_preset_change_clears_known_parameter_values(self) -> None:
        chain = make_chain(internal_slot_id=1, effect_key="dyn.comp1")
        core = prepare_core(chain)
        core.feed((COMP1_FIXTURE_ROOT / "slot2_sustain_051.bin").read_bytes())
        core.feed((COMP1_FIXTURE_ROOT / "slot2_volume_050.bin").read_bytes())

        preset_message = bytearray(build_select_preset("01B"))
        preset_message[8] = 0x00
        update = core.feed(preset_message)
        self.assertIsNotNone(update.preset_event)

        core.apply_chain_state(chain)
        snapshot = core.snapshot
        assert snapshot is not None
        self.assertTrue(
            all(parameter.value is None for parameter in snapshot.effects[0].parameters)
        )


class Comp1EvidenceManifestTests(unittest.TestCase):
    def test_manifest_preserves_capture_sources_and_protocol_finding(self) -> None:
        manifest = json.loads(
            (COMP1_FIXTURE_ROOT / "manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["physical_binary_fixtures"], 22)
        self.assertEqual(manifest["internal_slots_observed"], [1, 2])
        self.assertEqual(len(manifest["controlled_capture_sources"]), 3)
        self.assertEqual(
            manifest["protocol"]["effect_identity_source"],
            "current_chain",
        )
        self.assertEqual(
            manifest["protocol"]["observed_parameter_address"]["value"],
            [1, 4],
        )


class Comp2EvidenceManifestTests(unittest.TestCase):
    def test_manifest_preserves_four_parameters_and_accidental_value_five(self) -> None:
        manifest = json.loads(
            (COMP2_FIXTURE_ROOT / "manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["effect"]["key"], "dyn.comp2")
        self.assertEqual(manifest["physical_binary_fixtures"], 49)
        self.assertEqual(manifest["internal_slots_observed"], [1, 2])
        self.assertEqual(len(manifest["controlled_capture_sources"]), 6)
        self.assertEqual(
            tuple(parameter["selector"] for parameter in manifest["parameters"]),
            (0, 1, 2, 3),
        )
        clipping_values = {
            fixture["value"]
            for fixture in manifest["fixtures"]
            if fixture["parameter"] == "clipping"
        }
        self.assertIn(5, clipping_values)
        self.assertEqual(
            manifest["combination_capture_validation"]["result"],
            "independent_messages_per_parameter",
        )


class Comp3EvidenceManifestTests(unittest.TestCase):
    def test_manifest_preserves_seven_parameters_and_two_slots(self) -> None:
        manifest = json.loads(
            (COMP3_FIXTURE_ROOT / "manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["effect"]["key"], "dyn.comp3")
        self.assertEqual(manifest["physical_binary_fixtures"], 84)
        self.assertEqual(manifest["internal_slots_observed"], [1, 2])
        self.assertEqual(len(manifest["controlled_capture_sources"]), 9)
        self.assertEqual(
            tuple(parameter["selector"] for parameter in manifest["parameters"]),
            (0, 1, 2, 3, 4, 5, 6),
        )
        self.assertEqual(
            manifest["combination_capture_validation"]["result"],
            "independent_messages_per_parameter",
        )
        self.assertEqual(
            manifest["slot2_validation"]["result"],
            "same_selectors_and_codec_on_internal_slot_2",
        )


class BoostEvidenceManifestTests(unittest.TestCase):
    def test_ac_and_bb_boost_manifests_preserve_four_parameters_and_two_slots(self) -> None:
        for fixture_root, effect_key in (
            (AC_BOOST_FIXTURE_ROOT, "dyn.ac_boost"),
            (BB_BOOST_FIXTURE_ROOT, "dyn.bb_boost"),
        ):
            with self.subTest(effect=effect_key):
                manifest = json.loads(
                    (fixture_root / "manifest.json").read_text(encoding="utf-8")
                )
                self.assertEqual(manifest["effect"]["key"], effect_key)
                self.assertEqual(manifest["physical_binary_fixtures"], 32)
                self.assertEqual(manifest["internal_slots_observed"], [1, 2])
                self.assertEqual(len(manifest["controlled_capture_sources"]), 6)
                self.assertEqual(
                    tuple(
                        parameter["selector"]
                        for parameter in manifest["parameters"]
                    ),
                    (0, 1, 2, 3),
                )
                self.assertEqual(
                    manifest["combination_capture_validation"]["result"],
                    "independent_messages_per_parameter",
                )
                self.assertEqual(
                    manifest["slot2_validation"]["result"],
                    "same_selectors_and_codec_on_internal_slot_2",
                )


class Phase30EvidenceManifestTests(unittest.TestCase):
    def test_manifests_preserve_parameters_boolean_and_two_slots(self) -> None:
        cases = (
            (RC_BOOST_FIXTURE_ROOT, "dyn.rc_boost", 32, (0, 1, 2, 3)),
            (FAT_BOOST_FIXTURE_ROOT, "dyn.fat_boost", 28, (0, 1, 2, 3)),
            (GATE2_FIXTURE_ROOT, "dyn.gate_2", 23, (0, 1, 2)),
        )
        for fixture_root, effect_key, fixture_count, selectors in cases:
            with self.subTest(effect=effect_key):
                manifest = json.loads(
                    (fixture_root / "manifest.json").read_text(encoding="utf-8")
                )
                self.assertEqual(manifest["effect"]["key"], effect_key)
                self.assertEqual(manifest["physical_binary_fixtures"], fixture_count)
                self.assertEqual(manifest["internal_slots_observed"], [1, 2])
                self.assertEqual(
                    tuple(parameter["selector"] for parameter in manifest["parameters"]),
                    selectors,
                )
                self.assertEqual(
                    manifest["combination_capture_validation"]["result"],
                    "independent_messages_per_parameter",
                )
                self.assertEqual(
                    manifest["slot2_validation"]["result"],
                    "same_selectors_and_codec_on_internal_slot_2",
                )
        fat_manifest = json.loads(
            (FAT_BOOST_FIXTURE_ROOT / "manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            fat_manifest["protocol"]["boolean_encoding"]["semantic"],
            "numeric_0_or_1_using_shared_float_codec",
        )


class SimpleDynEvidenceManifestTests(unittest.TestCase):
    def test_ac_woody_and_gate1_manifests_preserve_two_slot_evidence(self) -> None:
        for fixture_root, effect_key, parameter_key in (
            (AC_WOODY_FIXTURE_ROOT, "dyn.ac_woody", "shape"),
            (GATE1_FIXTURE_ROOT, "dyn.gate_1", "threshold"),
        ):
            with self.subTest(effect=effect_key):
                manifest = json.loads(
                    (fixture_root / "manifest.json").read_text(encoding="utf-8")
                )
                self.assertEqual(manifest["effect"]["key"], effect_key)
                self.assertEqual(manifest["parameters"][0]["key"], parameter_key)
                self.assertEqual(manifest["physical_binary_fixtures"], 11)
                self.assertEqual(manifest["internal_slots_observed"], [1, 2])
                self.assertEqual(len(manifest["controlled_capture_sources"]), 2)
                self.assertEqual(
                    manifest["protocol"]["effect_identity_source"],
                    "current_chain",
                )


class EBoostEvidenceManifestTests(unittest.TestCase):
    def test_manifest_preserves_boolean_and_combination_evidence(self) -> None:
        manifest = json.loads(
            (EBOOST_FIXTURE_ROOT / "manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["physical_binary_fixtures"], 19)
        self.assertEqual(manifest["internal_slots_observed"], [1, 2])
        self.assertEqual(len(manifest["controlled_capture_sources"]), 5)
        self.assertEqual(
            manifest["protocol"]["boolean_encoding"]["semantic"],
            "numeric_0_or_1_using_shared_float_codec",
        )
        self.assertEqual(
            manifest["combination_capture_validation"]["result"],
            "independent_messages_per_parameter",
        )


class Gate3TimeParameterTests(unittest.TestCase):
    def test_all_physical_gate3_fixtures_decode_full_float32(self) -> None:
        fixtures = sorted(GATE3_FIXTURE_ROOT.glob("*.bin"))
        self.assertEqual(len(fixtures), 58)
        manifest = json.loads(
            (GATE3_FIXTURE_ROOT / "manifest.json").read_text(encoding="utf-8")
        )
        expected = {item["file"]: item for item in manifest["fixtures"]}
        observed_slots = set()
        observed_parameters = set()
        for fixture in fixtures:
            with self.subTest(fixture=fixture.name):
                event = parse_effect_parameter_response(
                    fixture.read_bytes(), effect_key="dyn.gate_3"
                )
                self.assertIsNotNone(event)
                assert event is not None
                item = expected[fixture.name]
                observed_slots.add(event.human_slot)
                observed_parameters.add(event.parameter_key)
                self.assertEqual(event.human_slot, item["slot"])
                self.assertEqual(event.parameter_key, item["parameter"])
                self.assertEqual(event.value, item["value"])
                self.assertEqual(event.value_codec, "float32_nibbles_v1")
                self.assertEqual(len(event.encoded_value), 8)
        self.assertEqual(observed_slots, {1, 2})
        self.assertEqual(
            observed_parameters,
            {"threshold", "ratio", "attack", "release", "hold"},
        )

    def test_release_preserves_lower_float_nibbles(self) -> None:
        for filename, expected in (
            ("slot1_release_05001.bin", 5001),
            ("slot2_release_05037.bin", 5037),
            ("slot2_release_06037.bin", 6037),
        ):
            with self.subTest(fixture=filename):
                event = parse_effect_parameter_response(
                    (GATE3_FIXTURE_ROOT / filename).read_bytes(),
                    effect_key="dyn.gate_3",
                )
                assert event is not None
                self.assertEqual(event.value, expected)

    def test_duration_display_switches_from_ms_to_seconds(self) -> None:
        cases = (
            ("slot1_release_00900.bin", "900 ms"),
            ("slot1_release_01000.bin", "1,0 s"),
            ("slot1_release_05000.bin", "5,0 s"),
            ("slot2_release_05037.bin", "5,0 s"),
            ("slot1_release_10000.bin", "10,0 s"),
            ("slot1_hold_00999.bin", "999 ms"),
            ("slot1_hold_01000.bin", "1,0 s"),
        )
        for filename, display in cases:
            with self.subTest(fixture=filename):
                event = parse_effect_parameter_response(
                    (GATE3_FIXTURE_ROOT / filename).read_bytes(),
                    effect_key="dyn.gate_3",
                )
                assert event is not None
                self.assertEqual(event.display_value, display)

    def test_monitor_lists_and_updates_gate3_in_catalog_order(self) -> None:
        core = prepare_core(make_chain(internal_slot_id=1, effect_key="dyn.gate_3"))
        snapshot = core.snapshot
        assert snapshot is not None
        self.assertEqual(
            tuple(parameter.name for parameter in snapshot.effects[0].parameters),
            ("THRESHOLD", "RATIO", "ATTACK", "RELEASE", "HOLD"),
        )
        for filename in (
            "slot2_threshold_00051.bin",
            "slot2_ratio_00051.bin",
            "slot2_attack_00300.bin",
            "slot2_release_05037.bin",
            "slot2_hold_00600.bin",
        ):
            update = core.feed((GATE3_FIXTURE_ROOT / filename).read_bytes())
            self.assertIsNotNone(update.parameter_event)
        assert update.snapshot is not None
        self.assertEqual(
            tuple(parameter.value for parameter in update.snapshot.effects[0].parameters),
            (51, 51, 300, 5037, 600),
        )
        formatted = format_monitor_snapshot(update.snapshot)
        self.assertIn("THRESHOLD: 51", formatted)
        self.assertIn("RATIO: 51", formatted)
        self.assertIn("ATTACK: 300 ms", formatted)
        self.assertIn("RELEASE: 5,0 s", formatted)
        self.assertIn("HOLD: 600 ms", formatted)

    def test_full_value_payload_rejects_non_nibble_lower_part(self) -> None:
        message = bytearray(
            (GATE3_FIXTURE_ROOT / "slot1_release_05001.bin").read_bytes()
        )
        message[56] = 0x10
        with self.assertRaises(EffectParameterProtocolError):
            parse_effect_parameter_response(message, effect_key="dyn.gate_3")


class Phase32EvidenceManifestTests(unittest.TestCase):
    def test_manifest_preserves_full_float_and_corrected_slot2_evidence(self) -> None:
        manifest = json.loads(
            (GATE3_FIXTURE_ROOT / "manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["physical_binary_fixtures"], 58)
        self.assertEqual(manifest["internal_slots_observed"], [1, 2])
        self.assertEqual(
            manifest["protocol"]["value_indices"],
            [55, 56, 57, 58, 59, 60, 61, 62],
        )
        self.assertEqual(
            manifest["corrected_slot2_validation"]["result"],
            "same_selectors_and_full_float32_codec_on_internal_slot_2",
        )
        self.assertTrue(
            any("5037" in note for note in manifest["capture_observations"])
        )


class AcSimEnumParameterTests(unittest.TestCase):
    def test_all_physical_ac_sim_fixtures_decode_by_effect_context(self) -> None:
        fixtures = sorted(AC_SIM_FIXTURE_ROOT.glob("*.bin"))
        self.assertEqual(len(fixtures), 30)
        manifest = json.loads(
            (AC_SIM_FIXTURE_ROOT / "manifest.json").read_text(encoding="utf-8")
        )
        expected = {item["file"]: item for item in manifest["fixtures"]}
        for fixture in fixtures:
            with self.subTest(fixture=fixture.name):
                event = parse_effect_parameter_response(
                    fixture.read_bytes(), effect_key="dyn.ac_sim"
                )
                self.assertIsNotNone(event)
                assert event is not None
                item = expected[fixture.name]
                self.assertEqual(event.human_slot, item["slot"])
                self.assertEqual(event.parameter_key, item["parameter"])
                self.assertEqual(event.value, item["value"])

    def test_mode_wire_values_decode_to_named_choices(self) -> None:
        expected = {
            "standard": "STANDARD",
            "jumbo": "JUMBO",
            "enhanced": "ENHANCED",
            "piezo": "PIEZO",
        }
        for suffix, label in expected.items():
            with self.subTest(mode=label):
                event = parse_effect_parameter_response(
                    (AC_SIM_FIXTURE_ROOT / f"slot1_mode_{suffix}.bin").read_bytes(),
                    effect_key="dyn.ac_sim",
                )
                assert event is not None
                self.assertEqual(event.value, label)
                self.assertEqual(event.display_value, label)

    def test_mode_rejects_uncataloged_wire_value(self) -> None:
        message = bytearray(
            (AC_SIM_FIXTURE_ROOT / "slot1_mode_piezo.bin").read_bytes()
        )
        # 4.0 encoded by the shared upper-float codec.
        message[59:63] = bytes((0x08, 0x00, 0x04, 0x00))
        with self.assertRaises(EffectParameterProtocolError):
            parse_effect_parameter_response(message, effect_key="dyn.ac_sim")

    def test_monitor_lists_and_updates_ac_sim_enum(self) -> None:
        core = prepare_core(make_chain(internal_slot_id=1, effect_key="dyn.ac_sim"))
        snapshot = core.snapshot
        assert snapshot is not None
        self.assertEqual(
            tuple(parameter.name for parameter in snapshot.effects[0].parameters),
            ("BODY", "TOP", "VOLUME", "MODE"),
        )
        for filename in (
            "slot2_body_051.bin",
            "slot2_top_052.bin",
            "slot2_volume_053.bin",
            "slot2_mode_enhanced.bin",
        ):
            update = core.feed((AC_SIM_FIXTURE_ROOT / filename).read_bytes())
            self.assertIsNotNone(update.parameter_event)
        assert update.snapshot is not None
        self.assertEqual(
            tuple(parameter.value for parameter in update.snapshot.effects[0].parameters),
            (51, 52, 53, "ENHANCED"),
        )
        formatted = format_monitor_snapshot(update.snapshot)
        self.assertIn("BODY: 51", formatted)
        self.assertIn("TOP: 52", formatted)
        self.assertIn("VOLUME: 53", formatted)
        self.assertIn("MODE: ENHANCED", formatted)


class Phase31EvidenceManifestTests(unittest.TestCase):
    def test_manifest_preserves_enum_order_and_two_slots(self) -> None:
        manifest = json.loads(
            (AC_SIM_FIXTURE_ROOT / "manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["effect"]["key"], "dyn.ac_sim")
        self.assertEqual(manifest["physical_binary_fixtures"], 30)
        self.assertEqual(manifest["internal_slots_observed"], [1, 2])
        self.assertEqual(len(manifest["controlled_capture_sources"]), 6)
        self.assertEqual(
            tuple(parameter["selector"] for parameter in manifest["parameters"]),
            (0, 1, 2, 3),
        )
        self.assertEqual(
            tuple(choice["label"] for choice in manifest["parameters"][3]["choices"]),
            ("STANDARD", "JUMBO", "ENHANCED", "PIEZO"),
        )
        self.assertEqual(
            manifest["mode_capture_validation"]["received_wire_values"],
            [0, 1, 2, 3, 0],
        )
        self.assertEqual(
            manifest["slot2_validation"]["result"],
            "same_selectors_codec_and_enum_mapping_on_internal_slot_2",
        )




class OctaverParameterTests(unittest.TestCase):
    def test_all_physical_octaver_fixtures_decode_by_chain_effect_context(self) -> None:
        fixtures = sorted(OCTAVER_FIXTURE_ROOT.glob("*.bin"))
        self.assertEqual(len(fixtures), 24)
        manifest = json.loads(
            (OCTAVER_FIXTURE_ROOT / "manifest.json").read_text(encoding="utf-8")
        )
        expected = {item["file"]: item for item in manifest["fixtures"]}
        observed_slots = set()
        observed_parameters = set()
        for fixture in fixtures:
            with self.subTest(fixture=fixture.name):
                event = parse_effect_parameter_response(
                    fixture.read_bytes(), effect_key="freq.octaver"
                )
                self.assertIsNotNone(event)
                assert event is not None
                item = expected[fixture.name]
                observed_slots.add(event.human_slot)
                observed_parameters.add(event.parameter_key)
                self.assertEqual(event.class_id, 1)
                self.assertEqual(event.class_key, "freq")
                self.assertEqual(event.human_slot, item["slot"])
                self.assertEqual(event.parameter_key, item["parameter"])
                self.assertEqual(event.value, item["value"])
        self.assertEqual(observed_slots, {1, 2})
        self.assertEqual(observed_parameters, {"low_oct", "high_oct", "dry"})

    def test_octaver_slot2_updates_three_independent_parameters(self) -> None:
        core = prepare_core(make_chain(internal_slot_id=1, effect_key="freq.octaver"))
        for filename in (
            "slot2_low_oct_061.bin",
            "slot2_high_oct_062.bin",
            "slot2_dry_063.bin",
        ):
            update = core.feed((OCTAVER_FIXTURE_ROOT / filename).read_bytes())
            self.assertIsNotNone(update.parameter_event)
        assert update.snapshot is not None
        effect = update.snapshot.effects[0]
        self.assertEqual(
            tuple(parameter.name for parameter in effect.parameters),
            ("LOW OCT", "HIGH OCT", "DRY"),
        )
        self.assertEqual(
            tuple(parameter.value for parameter in effect.parameters),
            (61, 62, 63),
        )
        formatted = format_monitor_snapshot(update.snapshot)
        self.assertIn("LOW OCT: 61", formatted)
        self.assertIn("HIGH OCT: 62", formatted)
        self.assertIn("DRY: 63", formatted)

    def test_octaver_manifest_preserves_corrected_slot2_evidence(self) -> None:
        manifest = json.loads(
            (OCTAVER_FIXTURE_ROOT / "manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["effect"]["key"], "freq.octaver")
        self.assertEqual(manifest["physical_binary_fixtures"], 24)
        self.assertEqual(manifest["internal_slots_observed"], [1, 2])
        self.assertEqual(
            tuple(parameter["selector"] for parameter in manifest["parameters"]),
            (0, 1, 2),
        )
        self.assertEqual(
            manifest["slot2_validation"]["result"],
            "same_selectors_and_codec_on_internal_slot_2",
        )
        self.assertEqual(
            manifest["excluded_capture_sources"][0]["source"],
            "octaver_short_dump.pcapng",
        )

class DualMelodyParameterTests(unittest.TestCase):
    def test_all_physical_dual_melody_fixtures_decode_signed_values_by_chain_context(self) -> None:
        fixtures = sorted(DUAL_MELODY_FIXTURE_ROOT.glob("*.bin"))
        self.assertEqual(len(fixtures), 40)
        manifest = json.loads(
            (DUAL_MELODY_FIXTURE_ROOT / "manifest.json").read_text(encoding="utf-8")
        )
        expected = {item["file"]: item for item in manifest["fixtures"]}
        observed_slots = set()
        observed_parameters = set()
        for fixture in fixtures:
            with self.subTest(fixture=fixture.name):
                event = parse_effect_parameter_response(
                    fixture.read_bytes(), effect_key="freq.dual_melody"
                )
                self.assertIsNotNone(event)
                assert event is not None
                item = expected[fixture.name]
                observed_slots.add(event.human_slot)
                observed_parameters.add(event.parameter_key)
                self.assertEqual(event.class_id, 1)
                self.assertEqual(event.class_key, "freq")
                self.assertEqual(event.human_slot, item["slot"])
                self.assertEqual(event.parameter_key, item["parameter"])
                self.assertEqual(event.value, item["value"])
        self.assertEqual(observed_slots, {1, 2})
        self.assertEqual(
            observed_parameters,
            {"high_pitch", "low_pitch", "dry", "hi_vol", "low_vol"},
        )

    def test_dual_melody_low_pitch_decodes_native_negative_float32(self) -> None:
        expected = {
            "slot1_low_pitch_m024.bin": -24,
            "slot1_low_pitch_m012.bin": -12,
            "slot1_low_pitch_m001.bin": -1,
            "slot1_low_pitch_000.bin": 0,
        }
        for filename, value in expected.items():
            with self.subTest(filename=filename):
                event = parse_effect_parameter_response(
                    (DUAL_MELODY_FIXTURE_ROOT / filename).read_bytes(),
                    effect_key="freq.dual_melody",
                )
                self.assertIsNotNone(event)
                assert event is not None
                self.assertEqual(event.parameter_key, "low_pitch")
                self.assertEqual(event.value, value)
                self.assertEqual(event.display_value, str(value))

    def test_dual_melody_slot2_updates_five_independent_parameters(self) -> None:
        core = prepare_core(
            make_chain(internal_slot_id=1, effect_key="freq.dual_melody")
        )
        for filename in (
            "slot2_high_pitch_014.bin",
            "slot2_low_pitch_m014.bin",
            "slot2_dry_061.bin",
            "slot2_hi_vol_062.bin",
            "slot2_low_vol_063.bin",
        ):
            update = core.feed((DUAL_MELODY_FIXTURE_ROOT / filename).read_bytes())
            self.assertIsNotNone(update.parameter_event)
        assert update.snapshot is not None
        effect = update.snapshot.effects[0]
        self.assertEqual(
            tuple(parameter.name for parameter in effect.parameters),
            ("HIGH PITCH", "LOW PITCH", "DRY", "HI VOL", "LOW VOL"),
        )
        self.assertEqual(
            tuple(parameter.value for parameter in effect.parameters),
            (14, -14, 61, 62, 63),
        )
        formatted = format_monitor_snapshot(update.snapshot)
        self.assertIn("HIGH PITCH: 14", formatted)
        self.assertIn("LOW PITCH: -14", formatted)
        self.assertIn("DRY: 61", formatted)
        self.assertIn("HI VOL: 62", formatted)
        self.assertIn("LOW VOL: 63", formatted)

    def test_dual_melody_manifest_preserves_signed_evidence_and_selector_gap(self) -> None:
        manifest = json.loads(
            (DUAL_MELODY_FIXTURE_ROOT / "manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["effect"]["key"], "freq.dual_melody")
        self.assertEqual(manifest["physical_binary_fixtures"], 40)
        self.assertEqual(manifest["internal_slots_observed"], [1, 2])
        self.assertEqual(
            tuple(parameter["selector"] for parameter in manifest["parameters"]),
            (0, 1, 2, 4, 5),
        )
        self.assertEqual(
            manifest["signed_value_validation"]["result"],
            "negative_display_values_are_native_signed_float32_values_not_zero_based_indices",
        )
        self.assertEqual(
            manifest["incoming_selector_gap"]["selector_3"],
            "not_observed_in_device_to_host_parameter_responses",
        )
        self.assertEqual(
            manifest["slot2_validation"]["result"],
            "same_incoming_selectors_and_signed_float_codec_on_internal_slot_2",
        )


class FilterConditionalRateParameterTests(unittest.TestCase):
    def test_all_physical_filter_fixtures_decode_by_chain_effect_context(self) -> None:
        fixtures = sorted(FILTER_FIXTURE_ROOT.glob("*.bin"))
        self.assertEqual(len(fixtures), 55)
        manifest = json.loads(
            (FILTER_FIXTURE_ROOT / "manifest.json").read_text(encoding="utf-8")
        )
        expected = {item["file"]: item for item in manifest["fixtures"]}
        observed_slots = set()
        observed_parameters = set()
        for fixture in fixtures:
            with self.subTest(fixture=fixture.name):
                signal = parse_effect_parameter_signal(fixture.read_bytes())
                self.assertIsNotNone(signal)
                assert signal is not None
                # O campo 41-42 permanece 0 em FREQ; a classe estrutural vem da cadeia.
                self.assertEqual(signal.class_id, 0)
                event = parse_effect_parameter_response(
                    fixture.read_bytes(), effect_key="freq.filter"
                )
                self.assertIsNotNone(event)
                assert event is not None
                item = expected[fixture.name]
                observed_slots.add(event.human_slot)
                observed_parameters.add(event.parameter_key)
                self.assertEqual(event.class_id, 1)
                self.assertEqual(event.class_key, "freq")
                self.assertEqual(event.human_slot, item["slot"])
                self.assertEqual(event.parameter_key, item["parameter"])
                self.assertEqual(event.value, item["value"])
        self.assertEqual(observed_slots, {1, 2})
        self.assertEqual(
            observed_parameters,
            {"step_1", "step_2", "step_3", "step_4", "rate", "sync"},
        )

    def test_filter_rate_defaults_are_derived_without_fabricating_usb_event(self) -> None:
        core = prepare_core(make_chain(internal_slot_id=0, effect_key="freq.filter"))
        root = FILTER_FIXTURE_ROOT

        update = core.feed((root / "slot1_rate_055.bin").read_bytes())
        assert update.snapshot is not None
        rate = update.snapshot.effects[0].parameters[4]
        self.assertEqual((rate.value, rate.display_value, rate.value_origin), (55, "55", "observed_usb"))

        update = core.feed((root / "slot1_sync_on.bin").read_bytes())
        self.assertIsNotNone(update.parameter_event)
        assert update.parameter_event is not None
        self.assertEqual(update.parameter_event.parameter_key, "sync")
        assert update.snapshot is not None
        rate = update.snapshot.effects[0].parameters[4]
        sync = update.snapshot.effects[0].parameters[5]
        self.assertEqual((rate.value, rate.display_value, rate.value_origin), (4, "1/4", "derived_device_rule"))
        self.assertEqual((sync.value, sync.display_value, sync.value_origin), (True, "ligado", "observed_usb"))
        self.assertIsNone(core.parameter_state.event_for(0, "freq.filter", "rate"))

        update = core.feed((root / "slot1_rate_005.bin").read_bytes())
        assert update.snapshot is not None
        rate = update.snapshot.effects[0].parameters[4]
        self.assertEqual((rate.value, rate.display_value, rate.value_origin), (5, "1/4d", "observed_usb"))

        update = core.feed((root / "slot1_sync_off.bin").read_bytes())
        assert update.snapshot is not None
        rate = update.snapshot.effects[0].parameters[4]
        self.assertEqual((rate.value, rate.display_value, rate.value_origin), (10, "10", "derived_device_rule"))
        self.assertIsNone(core.parameter_state.event_for(0, "freq.filter", "rate"))

    def test_filter_rate_waits_for_sync_when_wire_value_is_ambiguous(self) -> None:
        core = prepare_core(make_chain(internal_slot_id=0, effect_key="freq.filter"))
        update = core.feed((FILTER_FIXTURE_ROOT / "slot1_rate_005.bin").read_bytes())
        assert update.snapshot is not None
        rate = update.snapshot.effects[0].parameters[4]
        self.assertEqual(rate.value, 5)
        self.assertEqual(rate.display_value, "aguardando SYNC")
        self.assertEqual(rate.value_origin, "observed_usb")

    def test_filter_slot2_preserves_conditional_domain(self) -> None:
        core = prepare_core(make_chain(internal_slot_id=1, effect_key="freq.filter"))
        root = FILTER_FIXTURE_ROOT
        for filename in (
            "slot2_step1_061.bin",
            "slot2_step2_062.bin",
            "slot2_step3_063.bin",
            "slot2_step4_064.bin",
            "slot2_rate_065.bin",
        ):
            core.feed((root / filename).read_bytes())
        update = core.feed((root / "slot2_sync_on.bin").read_bytes())
        assert update.snapshot is not None
        self.assertEqual(
            tuple(parameter.display_value for parameter in update.snapshot.effects[0].parameters),
            ("61", "62", "63", "64", "1/4", "ligado"),
        )
        update = core.feed((root / "slot2_rate_005.bin").read_bytes())
        assert update.snapshot is not None
        self.assertEqual(update.snapshot.effects[0].parameters[4].display_value, "1/4d")
        update = core.feed((root / "slot2_sync_off.bin").read_bytes())
        assert update.snapshot is not None
        self.assertEqual(update.snapshot.effects[0].parameters[4].display_value, "10")

    def test_monitor_lists_filter_parameters_in_catalog_order(self) -> None:
        core = prepare_core(make_chain(internal_slot_id=0, effect_key="freq.filter"))
        snapshot = core.snapshot
        assert snapshot is not None
        self.assertEqual(
            tuple(parameter.name for parameter in snapshot.effects[0].parameters),
            ("STEP 1", "STEP 2", "STEP 3", "STEP 4", "RATE", "SYNC"),
        )


class Phase33FilterEvidenceManifestTests(unittest.TestCase):
    def test_manifest_preserves_two_domains_implicit_defaults_and_two_slots(self) -> None:
        manifest = json.loads(
            (FILTER_FIXTURE_ROOT / "manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["effect"]["key"], "freq.filter")
        self.assertEqual(manifest["effect"]["class_id"], 1)
        self.assertEqual(manifest["physical_binary_fixtures"], 55)
        self.assertEqual(manifest["internal_slots_observed"], [1, 2])
        self.assertEqual(len(manifest["controlled_capture_sources"]), 10)
        self.assertEqual(
            tuple(parameter["selector"] for parameter in manifest["parameters"]),
            (0, 1, 2, 3, 4, 5),
        )
        self.assertEqual(
            tuple(item["label"] for item in manifest["rate_sync_on_divisions"]["wire_mapping"]),
            ("1/1", "1/2", "1/2d", "1/2t", "1/4", "1/4d", "1/4t", "1/8", "1/8d", "1/8t", "1/16"),
        )
        transition = manifest["sync_default_transition_validation"]
        self.assertFalse(transition["rate_events_emitted_automatically"])
        self.assertEqual(transition["visual_device_behavior"]["sync_off_rate_default"], 10)
        self.assertEqual(transition["visual_device_behavior"]["sync_on_rate_default"], "1/4")
        self.assertEqual(
            manifest["protocol"]["parameter_envelope_class_field"]["semantic"],
            "opaque_not_structural_effect_class_id",
        )


if __name__ == "__main__":
    unittest.main()
