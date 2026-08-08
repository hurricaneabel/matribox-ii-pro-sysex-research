"""Regressões da família MOD RATE/SYNC validada fisicamente (Fase 74)."""

from __future__ import annotations

import json
from pathlib import Path
import struct
import tempfile
import unittest

from tools.catalog import load_effect_catalog
from tools.commands.chain_order import ChainOrderState
from tools.commands.effect_catalog import CATALOG, EFFECT_CLASSES
from tools.commands.preset_monitor_core import build_effect_snapshots
from tools.commands.structural_effect_state import StructuralEffectRecord
from tools.migrations.export_effect_catalog_to_json import export_catalog
from tools.parameters import parse_effect_parameter_response
from tools.parameters.preset_dump import (
    PRESET_PARAMETER_BLOCK_END,
    PRESET_PARAMETER_BLOCK_OFFSET,
    PRESET_PARAMETER_SLOT_SIZE,
    decode_saved_parameter_events,
)
from tools.parameters.state import EffectParameterState


FULL = {
    "mod.e_chorus",
    "mod.b_chorus",
    "mod.vibrato",
    "mod.ce_roto",
    "mod.sine_trem",
    "mod.triangule_trem",
}
COMPACT = {
    "mod.bbd_roto",
    "mod.bbd_phaser",
    "mod.vibe",
    "mod.tremolo",
}
RATE_SYNC = {"mod.phaser"}
ALL = FULL | COMPACT | RATE_SYNC


def make_chain(effect_key: str) -> ChainOrderState:
    effect = CATALOG.effect_by_key(effect_key)
    effect_class = CATALOG.class_by_key(effect.class_key)
    records = []
    enabled = [None] * 12
    for slot_id in range(12):
        if slot_id == 0:
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
        else:
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
    return ChainOrderState(
        internal_slot_ids=(0,),
        observed_checksum=0,
        declared_length_units=0,
        raw_message=b"",
        enabled_by_internal_slot=tuple(enabled),
        effect_records_by_internal_slot=tuple(records),
    )


def make_dump(values: dict[int, float]) -> bytes:
    payload = bytearray(PRESET_PARAMETER_BLOCK_END)
    for selector, value in values.items():
        offset = PRESET_PARAMETER_BLOCK_OFFSET + selector * 4
        payload[offset:offset + 4] = struct.pack("<f", value)
    return bytes(payload)


def make_parameter_message(selector: int, value: float) -> bytes:
    """Reusa um envelope físico 0x1C e troca somente selector/value.

    O checksum do perfil é observado, não validado pelo decoder somente leitura.
    """

    template = bytearray(
        (Path("tests/fixtures/eq_parameters") / "guitar_eq1_volume_083.bin").read_bytes()
    )
    template[48] = selector
    raw = struct.pack("<f", float(value))
    nibbles: list[int] = []
    for byte in raw:
        nibbles.extend((byte >> 4, byte & 0x0F))
    template[55:63] = bytes(nibbles)
    return bytes(template)


class ModRateSyncFamilyPhase74Tests(unittest.TestCase):
    def test_eleven_models_have_expected_validated_schemas(self) -> None:
        catalog = load_effect_catalog()
        mod = catalog.class_by_key("mod")
        candidates = {effect.key: effect for effect in mod.models if effect.key in ALL}
        self.assertEqual(set(candidates), ALL)
        self.assertEqual(sum(len(effect.parameters) for effect in candidates.values()), 38)

        for key, effect in candidates.items():
            with self.subTest(effect=key):
                self.assertEqual(effect.parameter_catalog_status, "physically_validated")
                self.assertTrue(effect.parameters)
                if key in FULL:
                    self.assertEqual(
                        tuple(parameter.key for parameter in effect.parameters),
                        ("depth", "rate", "volume", "sync"),
                    )
                    self.assertEqual(
                        tuple(parameter.message_match["parameter_selector"] for parameter in effect.parameters),
                        (0, 1, 2, 3),
                    )
                elif key in COMPACT:
                    self.assertEqual(
                        tuple(parameter.key for parameter in effect.parameters),
                        ("depth", "rate", "sync"),
                    )
                    self.assertEqual(
                        tuple(parameter.message_match["parameter_selector"] for parameter in effect.parameters),
                        (0, 1, 2),
                    )
                else:
                    self.assertEqual(
                        tuple(parameter.key for parameter in effect.parameters),
                        ("rate", "sync"),
                    )
                    self.assertEqual(
                        tuple(parameter.message_match["parameter_selector"] for parameter in effect.parameters),
                        (0, 1),
                    )

                rate = next(parameter for parameter in effect.parameters if parameter.key == "rate")
                sync = next(parameter for parameter in effect.parameters if parameter.key == "sync")
                self.assertEqual(rate.value_codec, "float32_nibbles_v1")
                self.assertEqual(sync.value_codec, "float32_nibbles_v1")
                self.assertEqual(rate.validation["range_validated"], [0.1, 10.0])
                self.assertTrue(rate.value_domain["reset_on_controller_change"])
                states = rate.value_domain["states"]
                self.assertEqual(states[0]["default_value"], 0.5)
                self.assertEqual(states[1]["default_value"], 4)
                self.assertEqual(
                    [choice["label"] for choice in states[1]["presentation"]["choices"]],
                    ["1/1", "1/2", "1/2d", "1/2t", "1/4", "1/4d", "1/4t", "1/8", "1/8d", "1/8t", "1/16"],
                )

        for key in ALL:
            with self.subTest(physical=key):
                for parameter in candidates[key].parameters:
                    self.assertTrue(parameter.validation["physical"])
                    self.assertEqual(parameter.validation["monitor_integration_physical_validation"], "approved")
                    self.assertEqual(
                        parameter.validation["monitor_validation_result"],
                        "all_11_models_parameter_values_exact_to_device",
                    )

    def test_e_chorus_saved_dump_custom_values_and_selector4_residue(self) -> None:
        chain = make_chain("mod.e_chorus")
        events = decode_saved_parameter_events(
            make_dump({0: 37, 1: 3.7, 2: 73, 3: 0, 4: 50}),
            chain,
        )
        self.assertEqual(tuple(event.parameter_key for event in events), ("sync", "depth", "rate", "volume"))
        state = EffectParameterState()
        for event in events:
            state.apply(event, origin="saved_preset_dump")
        snapshot = build_effect_snapshots(chain, state)[0]
        self.assertEqual(
            tuple(parameter.display_value for parameter in snapshot.parameters),
            ("37", "3.7 Hz", "73", "desligado"),
        )
        self.assertNotIn("selector_4", tuple(parameter.key for parameter in snapshot.parameters))

    def test_sync_change_resets_rate_to_each_domain_default(self) -> None:
        chain = make_chain("mod.e_chorus")
        state = EffectParameterState()

        rate_37 = parse_effect_parameter_response(
            make_parameter_message(1, 3.7), effect_key="mod.e_chorus"
        )
        sync_on = parse_effect_parameter_response(
            make_parameter_message(3, 1), effect_key="mod.e_chorus"
        )
        rate_8 = parse_effect_parameter_response(
            make_parameter_message(1, 8), effect_key="mod.e_chorus"
        )
        sync_off = parse_effect_parameter_response(
            make_parameter_message(3, 0), effect_key="mod.e_chorus"
        )
        assert rate_37 is not None and sync_on is not None and rate_8 is not None and sync_off is not None

        state.apply(rate_37)
        self.assertEqual(build_effect_snapshots(chain, state)[0].parameters[1].display_value, "3.7 Hz")

        state.apply(sync_on)
        self.assertEqual(build_effect_snapshots(chain, state)[0].parameters[1].display_value, "1/4")

        state.apply(rate_8)
        self.assertEqual(build_effect_snapshots(chain, state)[0].parameters[1].display_value, "1/8d")

        state.apply(sync_off)
        self.assertEqual(build_effect_snapshots(chain, state)[0].parameters[1].display_value, "0.5 Hz")

    def test_exporter_reproduces_all_family_jsons(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            export_root = Path(temporary_directory) / "catalog"
            export_catalog(EFFECT_CLASSES, export_root)
            for key in sorted(ALL):
                current_effect = CATALOG.effect_by_key(key)
                source = Path("catalog/effects/mod") / f"{current_effect.menu_number:03d}_{key.split('.', 1)[1]}.json"
                exported_path = export_root / "effects" / "mod" / source.name
                exported = json.loads(exported_path.read_text(encoding="utf-8"))
                current = json.loads(source.read_text(encoding="utf-8"))
                self.assertEqual(exported["parameters"], current["parameters"])
                self.assertEqual(exported["parameter_catalog_status"], "physically_validated")
                self.assertEqual(exported["parameter_catalog_status"], current["parameter_catalog_status"])
                self.assertEqual(current_effect.parameter_catalog_status, "physically_validated")


if __name__ == "__main__":
    unittest.main()
