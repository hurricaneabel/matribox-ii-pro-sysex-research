"""Testes do motor genérico de parâmetros e sua integração ao monitor."""

from __future__ import annotations

from pathlib import Path
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
)


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "mboost_gain"


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
        fixtures = sorted(FIXTURE_ROOT.glob("*.bin"))
        self.assertEqual(len(fixtures), 27)

        for fixture in fixtures:
            with self.subTest(fixture=fixture.name):
                event = parse_effect_parameter_response(fixture.read_bytes())
                self.assertIsNotNone(event)
                assert event is not None
                self.assertEqual(event.effect_key, "dyn.m_boost")
                self.assertEqual(event.parameter_key, "gain")
                self.assertEqual(event.protocol_profile, "effect_parameter_response_1c_v1")
                self.assertEqual(event.value_codec, "upper_float32_nibbles_v1")
                self.assertEqual(event.parameter_name, "GAIN")

    def test_fixed_segment_mismatch_is_ignored(self) -> None:
        message = bytearray((FIXTURE_ROOT / "slot1_gain_050.bin").read_bytes())
        message[30] ^= 0x01
        self.assertIsNone(parse_effect_parameter_response(message))

    def test_invalid_cataloged_value_is_rejected(self) -> None:
        message = bytearray((FIXTURE_ROOT / "slot1_gain_100.bin").read_bytes())
        message[59:63] = bytes((0x0C, 0x0A, 0x04, 0x02))  # float superior de 101
        with self.assertRaises(EffectParameterProtocolError):
            parse_effect_parameter_response(message)

    def test_event_exposes_portable_human_fields(self) -> None:
        event = parse_effect_parameter_response(
            (FIXTURE_ROOT / "slot2_skreamer_gain_050.bin").read_bytes()
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
            (FIXTURE_ROOT / "slot1_gain_050.bin").read_bytes()
        )
        second = parse_effect_parameter_response(
            (FIXTURE_ROOT / "slot2_skreamer_gain_075.bin").read_bytes()
        )
        assert first is not None and second is not None

        state.apply(first)
        state.apply(second)

        self.assertEqual(state.event_for(0, "dyn.m_boost", "gain").value, 50)
        self.assertEqual(state.event_for(1, "dyn.m_boost", "gain").value, 75)

    def test_retain_effects_discards_stale_slot_value(self) -> None:
        state = EffectParameterState()
        event = parse_effect_parameter_response(
            (FIXTURE_ROOT / "slot1_gain_050.bin").read_bytes()
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

    def test_live_event_updates_gain_in_main_snapshot(self) -> None:
        core = prepare_core(make_chain(internal_slot_id=1, effect_key="dyn.m_boost"))
        update = core.feed(
            (FIXTURE_ROOT / "slot2_skreamer_gain_050.bin").read_bytes()
        )

        self.assertIsNotNone(update.parameter_event)
        self.assertTrue(update.snapshot_changed)
        assert update.snapshot is not None
        self.assertEqual(update.snapshot.effects[0].parameters[0].value, 50)
        self.assertIn("GAIN: 50", format_monitor_snapshot(update.snapshot))

    def test_event_for_other_effect_in_same_slot_is_ignored(self) -> None:
        core = prepare_core(make_chain(internal_slot_id=1, effect_key="drv.skreamer"))
        update = core.feed(
            (FIXTURE_ROOT / "slot2_skreamer_gain_050.bin").read_bytes()
        )

        self.assertIsNone(update.parameter_event)
        self.assertFalse(update.snapshot_changed)
        assert update.snapshot is not None
        self.assertEqual(update.snapshot.effects[0].parameters, ())

    def test_preset_change_clears_known_parameter_values(self) -> None:
        chain = make_chain(internal_slot_id=1, effect_key="dyn.m_boost")
        core = prepare_core(chain)
        core.feed((FIXTURE_ROOT / "slot2_skreamer_gain_050.bin").read_bytes())

        preset_message = bytearray(build_select_preset("01B"))
        preset_message[8] = 0x00
        update = core.feed(preset_message)
        self.assertIsNotNone(update.preset_event)

        core.apply_chain_state(chain)
        snapshot = core.snapshot
        assert snapshot is not None
        self.assertIsNone(snapshot.effects[0].parameters[0].value)


if __name__ == "__main__":
    unittest.main()
