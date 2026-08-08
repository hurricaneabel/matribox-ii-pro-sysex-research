"""Testes da migração do catálogo Python para JSON multiplataforma."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile
import unittest

from tools.catalog import CatalogValidationError, load_effect_catalog
from tools.commands import effect_catalog as facade
from tools.migrations.export_effect_catalog_to_json import export_catalog


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CATALOG_ROOT = REPOSITORY_ROOT / "catalog"
SNAPSHOT_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "effect_catalog"
    / "legacy_catalog_snapshot.json"
)


def structural_snapshot(classes) -> dict[str, object]:
    return {
        "schema_version": 1,
        "class_count": len(classes),
        "effect_count": sum(len(item.models) for item in classes),
        "classes": [
            {
                "menu_number": item.menu_number,
                "name": item.name,
                "class_id": item.class_id,
                "models": [
                    {
                        "menu_number": model.menu_number,
                        "name": model.name,
                        "model_id": model.model_id,
                        "secondary_selector": model.secondary_selector,
                    }
                    for model in item.models
                ],
            }
            for item in classes
        ],
    }


class EffectCatalogJsonMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = load_effect_catalog()

    def test_catalog_has_all_legacy_classes_and_effects(self) -> None:
        self.assertEqual(self.catalog.catalog_version, 39)
        self.assertEqual(len(self.catalog.classes), 16)
        self.assertEqual(self.catalog.effect_count, 267)

    def test_json_catalog_is_identical_to_legacy_python_snapshot(self) -> None:
        expected = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(structural_snapshot(self.catalog.classes), expected)

    def test_every_effect_has_an_individual_json_file(self) -> None:
        effect_files = tuple((CATALOG_ROOT / "effects").glob("*/*.json"))
        effect_files = tuple(path for path in effect_files if path.name != "index.json")
        self.assertEqual(len(effect_files), 267)

    def test_all_catalog_paths_are_portable(self) -> None:
        manifest = json.loads(
            (CATALOG_ROOT / "catalog.json").read_text(encoding="utf-8")
        )
        referenced_paths = (
            manifest["class_indexes"]
            + manifest["protocol_profiles"]
            + manifest["value_codecs"]
        )
        for relative in referenced_paths:
            with self.subTest(relative=relative):
                self.assertNotIn("\\", relative)
                self.assertNotIn(":", relative)
                self.assertFalse(Path(relative).is_absolute())
                self.assertNotIn("..", Path(relative).parts)

    def test_mboost_gain_remains_physically_validated(self) -> None:
        mboost = self.catalog.effect_by_key("dyn.m_boost")
        self.assertEqual(mboost.name, "M-BOOST")
        self.assertEqual(mboost.model_id, 0x14)
        self.assertEqual(mboost.secondary_selector, 0x00)
        self.assertEqual(mboost.parameter_catalog_status, "physically_validated")
        self.assertEqual(mboost.capabilities, ("parameters",))
        self.assertEqual(len(mboost.parameters), 1)

        gain = mboost.parameters[0]
        self.assertEqual(gain.key, "gain")
        self.assertEqual((gain.minimum, gain.maximum, gain.step), (0, 100, 1))
        self.assertEqual(gain.protocol_profile, "effect_parameter_response_1c_v1")
        self.assertEqual(gain.value_codec, "upper_float32_nibbles_v1")
        self.assertEqual(
            dict(gain.message_match),
            {
                "parameter_selector": 0,
                "parameter_marker": 1,
                "parameter_type": 1,
            },
        )
        self.assertTrue(gain.validation["physical"])
        self.assertTrue(gain.validation["multiple_instances"])


    def test_comp1_has_two_physically_validated_parameters(self) -> None:
        comp1 = self.catalog.effect_by_key("dyn.comp1")
        self.assertEqual(comp1.name, "COMP1")
        self.assertEqual(comp1.model_id, 0x00)
        self.assertEqual(comp1.parameter_catalog_status, "physically_validated")
        self.assertEqual(comp1.capabilities, ("parameters",))
        self.assertEqual(
            tuple(parameter.key for parameter in comp1.parameters),
            ("sustain", "volume"),
        )
        self.assertEqual(
            tuple(dict(parameter.message_match)["parameter_selector"] for parameter in comp1.parameters),
            (0, 1),
        )
        for parameter in comp1.parameters:
            self.assertEqual(
                (parameter.minimum, parameter.maximum, parameter.step),
                (0, 100, 1),
            )
            self.assertEqual(
                parameter.identification_status,
                "validated_with_chain_effect_context",
            )

    def test_comp2_has_four_physically_validated_parameters(self) -> None:
        comp2 = self.catalog.effect_by_key("dyn.comp2")
        self.assertEqual(comp2.name, "COMP2")
        self.assertEqual(comp2.model_id, 0x01)
        self.assertEqual(comp2.secondary_selector, 0x00)
        self.assertEqual(comp2.parameter_catalog_status, "physically_validated")
        self.assertEqual(comp2.capabilities, ("parameters",))
        self.assertEqual(
            tuple(parameter.key for parameter in comp2.parameters),
            ("sustain", "attack", "volume", "clipping"),
        )
        self.assertEqual(
            tuple(
                dict(parameter.message_match)["parameter_selector"]
                for parameter in comp2.parameters
            ),
            (0, 1, 2, 3),
        )
        for parameter in comp2.parameters:
            self.assertEqual(parameter.value_type, "integer")
            self.assertEqual(
                (parameter.minimum, parameter.maximum, parameter.step),
                (0, 100, 1),
            )
            self.assertEqual(
                parameter.identification_status,
                "validated_with_chain_effect_context",
            )
            self.assertEqual(parameter.validation["physical_fixture_count"], 49)


    def test_comp3_has_seven_physically_validated_parameters(self) -> None:
        comp3 = self.catalog.effect_by_key("dyn.comp3")
        self.assertEqual(comp3.name, "COMP3")
        self.assertEqual(comp3.model_id, 0x03)
        self.assertEqual(comp3.secondary_selector, 0x00)
        self.assertEqual(comp3.parameter_catalog_status, "physically_validated")
        self.assertEqual(comp3.capabilities, ("parameters",))
        self.assertEqual(
            tuple(parameter.key for parameter in comp3.parameters),
            (
                "threshold",
                "ratio",
                "volume",
                "attack",
                "release",
                "tone",
                "blend",
            ),
        )
        self.assertEqual(
            tuple(
                dict(parameter.message_match)["parameter_selector"]
                for parameter in comp3.parameters
            ),
            (0, 1, 2, 3, 4, 5, 6),
        )
        for parameter in comp3.parameters:
            self.assertEqual(parameter.value_type, "integer")
            self.assertEqual(
                (parameter.minimum, parameter.maximum, parameter.step),
                (0, 100, 1),
            )
            self.assertEqual(
                parameter.identification_status,
                "validated_with_chain_effect_context",
            )
            self.assertEqual(parameter.validation["physical_fixture_count"], 84)

    def test_ac_and_bb_boost_have_four_physically_validated_parameters(self) -> None:
        for effect_key, name, model_id in (
            ("dyn.ac_boost", "AC-BOOST", 0x0A),
            ("dyn.bb_boost", "BB-BOOST", 0x0B),
        ):
            with self.subTest(effect=effect_key):
                effect = self.catalog.effect_by_key(effect_key)
                self.assertEqual(effect.name, name)
                self.assertEqual(effect.model_id, model_id)
                self.assertEqual(effect.secondary_selector, 0x00)
                self.assertEqual(
                    effect.parameter_catalog_status,
                    "physically_validated",
                )
                self.assertEqual(effect.capabilities, ("parameters",))
                self.assertEqual(
                    tuple(parameter.key for parameter in effect.parameters),
                    ("gain", "volume", "bass", "treble"),
                )
                self.assertEqual(
                    tuple(
                        dict(parameter.message_match)["parameter_selector"]
                        for parameter in effect.parameters
                    ),
                    (0, 1, 2, 3),
                )
                for parameter in effect.parameters:
                    self.assertEqual(parameter.value_type, "integer")
                    self.assertEqual(
                        (parameter.minimum, parameter.maximum, parameter.step),
                        (0, 100, 1),
                    )
                    self.assertEqual(
                        parameter.identification_status,
                        "validated_with_chain_effect_context",
                    )
                    self.assertEqual(
                        parameter.validation["physical_fixture_count"],
                        32,
                    )

    def test_rc_fat_boost_and_gate2_have_physically_validated_parameters(self) -> None:
        rc_boost = self.catalog.effect_by_key("dyn.rc_boost")
        self.assertEqual(rc_boost.name, "RC-BOOST")
        self.assertEqual(rc_boost.model_id, 0x0C)
        self.assertEqual(rc_boost.parameter_catalog_status, "physically_validated")
        self.assertEqual(
            tuple(parameter.key for parameter in rc_boost.parameters),
            ("gain", "volume", "bass", "treble"),
        )
        self.assertEqual(
            tuple(
                dict(parameter.message_match)["parameter_selector"]
                for parameter in rc_boost.parameters
            ),
            (0, 1, 2, 3),
        )
        for parameter in rc_boost.parameters:
            self.assertEqual(parameter.value_type, "integer")
            self.assertEqual(
                (parameter.minimum, parameter.maximum, parameter.step),
                (0, 100, 1),
            )
            self.assertEqual(parameter.validation["physical_fixture_count"], 32)

        fat_boost = self.catalog.effect_by_key("dyn.fat_boost")
        self.assertEqual(fat_boost.name, "FAT BOOST")
        self.assertEqual(fat_boost.model_id, 0x19)
        self.assertEqual(fat_boost.parameter_catalog_status, "physically_validated")
        self.assertEqual(
            tuple(parameter.key for parameter in fat_boost.parameters),
            ("bass", "treble", "volume", "low_cut"),
        )
        self.assertEqual(
            tuple(parameter.value_type for parameter in fat_boost.parameters),
            ("integer", "integer", "integer", "boolean"),
        )
        self.assertEqual(
            tuple(
                dict(parameter.message_match)["parameter_selector"]
                for parameter in fat_boost.parameters
            ),
            (0, 1, 2, 3),
        )
        for parameter in fat_boost.parameters:
            self.assertEqual(parameter.validation["physical_fixture_count"], 28)
        self.assertEqual(
            dict(fat_boost.parameters[3].validation)["boolean_encoding"],
            {"false": 0, "true": 1},
        )

        gate2 = self.catalog.effect_by_key("dyn.gate_2")
        self.assertEqual(gate2.name, "GATE 2")
        self.assertEqual(gate2.model_id, 0x1D)
        self.assertEqual(gate2.parameter_catalog_status, "physically_validated")
        self.assertEqual(
            tuple(parameter.key for parameter in gate2.parameters),
            ("threshold", "attack", "release"),
        )
        self.assertEqual(
            tuple(
                dict(parameter.message_match)["parameter_selector"]
                for parameter in gate2.parameters
            ),
            (0, 1, 2),
        )
        for parameter in gate2.parameters:
            self.assertEqual(parameter.value_type, "integer")
            self.assertEqual(
                (parameter.minimum, parameter.maximum, parameter.step),
                (0, 100, 1),
            )
            self.assertEqual(parameter.validation["physical_fixture_count"], 23)


    def test_gate3_has_full_float_and_time_parameters(self) -> None:
        gate3 = self.catalog.effect_by_key("dyn.gate_3")
        self.assertEqual(gate3.name, "GATE 3")
        self.assertEqual(gate3.model_id, 0x21)
        self.assertEqual(gate3.secondary_selector, 0x00)
        self.assertEqual(gate3.parameter_catalog_status, "physically_validated")
        self.assertEqual(gate3.capabilities, ("parameters",))
        self.assertEqual(
            tuple(parameter.key for parameter in gate3.parameters),
            ("threshold", "ratio", "attack", "release", "hold"),
        )
        self.assertEqual(
            tuple(dict(parameter.message_match)["parameter_selector"] for parameter in gate3.parameters),
            (0, 1, 2, 3, 4),
        )
        self.assertEqual(
            tuple((parameter.minimum, parameter.maximum, parameter.step) for parameter in gate3.parameters),
            ((0, 100, 1), (0, 100, 1), (1, 500, 1), (10, 10000, 1), (0, 1000, 1)),
        )
        for parameter in gate3.parameters:
            self.assertEqual(parameter.value_codec, "float32_nibbles_v1")
            self.assertEqual(parameter.validation["physical_fixture_count"], 58)
        for parameter in gate3.parameters[2:]:
            self.assertEqual(parameter.unit, "ms")
            self.assertEqual(parameter.display["kind"], "duration_milliseconds")
            self.assertEqual(parameter.display["seconds_threshold"], 1000)
            self.assertEqual(parameter.display["seconds_decimals"], 1)
            self.assertEqual(parameter.display["decimal_separator"], ",")

    def test_ac_sim_has_named_enum_mode(self) -> None:
        ac_sim = self.catalog.effect_by_key("dyn.ac_sim")
        self.assertEqual(ac_sim.name, "AC SIM")
        self.assertEqual(ac_sim.model_id, 0x01)
        self.assertEqual(ac_sim.secondary_selector, 0x01)
        self.assertEqual(ac_sim.parameter_catalog_status, "physically_validated")
        self.assertEqual(ac_sim.capabilities, ("parameters",))
        self.assertEqual(
            tuple(parameter.key for parameter in ac_sim.parameters),
            ("body", "top", "volume", "mode"),
        )
        self.assertEqual(
            tuple(parameter.value_type for parameter in ac_sim.parameters),
            ("integer", "integer", "integer", "enum"),
        )
        self.assertEqual(
            tuple(dict(parameter.message_match)["parameter_selector"] for parameter in ac_sim.parameters),
            (0, 1, 2, 3),
        )
        self.assertEqual(
            dict(ac_sim.parameters[3].choices),
            {0: "STANDARD", 1: "JUMBO", 2: "ENHANCED", 3: "PIEZO"},
        )
        self.assertEqual(
            (ac_sim.parameters[3].minimum, ac_sim.parameters[3].maximum, ac_sim.parameters[3].step),
            (0, 3, 1),
        )
        for parameter in ac_sim.parameters:
            self.assertEqual(parameter.validation["physical_fixture_count"], 30)

    def test_loader_rejects_enum_without_choices(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            copied = Path(temporary_directory) / "catalog"
            shutil.copytree(CATALOG_ROOT, copied)
            effect_path = copied / "effects" / "dyn" / "011_ac_sim.json"
            document = json.loads(effect_path.read_text(encoding="utf-8"))
            del document["parameters"][3]["choices"]
            effect_path.write_text(json.dumps(document), encoding="utf-8")
            with self.assertRaises(CatalogValidationError):
                load_effect_catalog(copied)

    def test_loader_rejects_duplicate_enum_wire_value(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            copied = Path(temporary_directory) / "catalog"
            shutil.copytree(CATALOG_ROOT, copied)
            effect_path = copied / "effects" / "dyn" / "011_ac_sim.json"
            document = json.loads(effect_path.read_text(encoding="utf-8"))
            document["parameters"][3]["choices"][3]["value"] = 2
            effect_path.write_text(json.dumps(document), encoding="utf-8")
            with self.assertRaises(CatalogValidationError):
                load_effect_catalog(copied)

    def test_e_boost_has_integer_and_boolean_parameters(self) -> None:
        e_boost = self.catalog.effect_by_key("dyn.e_boost")
        self.assertEqual(e_boost.name, "E-BOOST")
        self.assertEqual(e_boost.model_id, 0x1A)
        self.assertEqual(e_boost.parameter_catalog_status, "physically_validated")
        self.assertEqual(e_boost.capabilities, ("parameters",))
        self.assertEqual(
            tuple(parameter.key for parameter in e_boost.parameters),
            ("gain", "plus_3db", "bright"),
        )
        self.assertEqual(
            tuple(parameter.value_type for parameter in e_boost.parameters),
            ("integer", "boolean", "boolean"),
        )
        self.assertEqual(
            tuple(
                dict(parameter.message_match)["parameter_selector"]
                for parameter in e_boost.parameters
            ),
            (0, 1, 2),
        )
        self.assertEqual(
            (e_boost.parameters[0].minimum, e_boost.parameters[0].maximum),
            (0, 100),
        )
        for parameter in e_boost.parameters[1:]:
            self.assertEqual(
                (parameter.minimum, parameter.maximum, parameter.step),
                (0, 1, 1),
            )
            self.assertEqual(
                dict(parameter.validation)["boolean_encoding"],
                {"false": 0, "true": 1},
            )

    def test_ac_woody_and_gate1_have_single_validated_parameters(self) -> None:
        expected = (
            ("dyn.ac_woody", "AC WOODY", "shape", "SHAPE", 0x00, 0x01),
            ("dyn.gate_1", "GATE 1", "threshold", "THRESHOLD", 0x1B, 0x00),
        )
        for effect_key, name, parameter_key, parameter_name, model_id, selector in expected:
            with self.subTest(effect=effect_key):
                effect = self.catalog.effect_by_key(effect_key)
                self.assertEqual(effect.name, name)
                self.assertEqual(effect.model_id, model_id)
                self.assertEqual(effect.secondary_selector, selector)
                self.assertEqual(effect.parameter_catalog_status, "physically_validated")
                self.assertEqual(effect.capabilities, ("parameters",))
                self.assertEqual(len(effect.parameters), 1)
                parameter = effect.parameters[0]
                self.assertEqual(parameter.key, parameter_key)
                self.assertEqual(parameter.name, parameter_name)
                self.assertEqual(parameter.value_type, "integer")
                self.assertEqual(
                    (parameter.minimum, parameter.maximum, parameter.step),
                    (0, 100, 1),
                )
                self.assertEqual(
                    dict(parameter.message_match)["parameter_selector"],
                    0,
                )
                self.assertEqual(
                    parameter.identification_status,
                    "validated_with_chain_effect_context",
                )

    def test_uncataloged_effects_do_not_invent_parameters(self) -> None:
        pending = [
            model
            for effect_class in self.catalog.classes
            for model in effect_class.models
            if model.key not in {
                "dyn.m_boost",
                "dyn.comp1",
                "dyn.comp2",
                "dyn.comp3",
                "dyn.ac_boost",
                "dyn.bb_boost",
                "dyn.rc_boost",
                "dyn.fat_boost",
                "dyn.gate_2",
                "dyn.gate_3",
                "dyn.ac_sim",
                "dyn.e_boost",
                "dyn.ac_woody",
                "dyn.gate_1",
                "freq.filter",
                "freq.octaver",
                "freq.dual_melody",
                "freq.pitch",
                "freq.harmony_d",
                "freq.pitch_s",
                "freq.ring_mod",
                "freq.tape_mod",
                "wah.voks_wah",
                "wah.cry_wah",
                "wah.rack_wah",
                "wah.bass_wah",
                "wah.touch_wah",
                "wah.auto_wah",
                "drv.skreamer",
                "drv.skreamer9",
                "drv.butter_od",
                "drv.warm_od",
                "drv.super_od",
                "drv.blues_od",
                "drv.full_od",
                "drv.breaker_od",
                "drv.gerden_od",
                "drv.timmy_od",
                "drv.master_od",
                "drv.solar_fuzz",
                "drv.fuzz_cream",
                "drv.red_fuzz",
                "drv.jp_dist",
                "drv.dark_mouse",
                "drv.plexi_dist",
                "drv.master_dist",
                "drv.dist_plus",
                "drv.shark",
                "drv.strive",
                "drv.sardar_dist",
                "drv.bass_od",
                "drv.bass_dist",
            }
        ]
        self.assertEqual(len(pending), 215)
        for model in pending:
            with self.subTest(effect=model.key):
                self.assertEqual(model.parameter_catalog_status, "pending")
                self.assertEqual(model.parameters, ())

    def test_protocol_profile_and_codec_are_resolved(self) -> None:
        profiles = {item.key: item for item in self.catalog.protocol_profiles}
        codecs = {item.key: item for item in self.catalog.value_codecs}
        profile = profiles["effect_parameter_response_1c_v1"].document
        codec = codecs["upper_float32_nibbles_v1"].document
        full_codec = codecs["float32_nibbles_v1"].document

        self.assertEqual(profile["command"], 0x1C)
        self.assertEqual(profile["message_length"], 70)
        self.assertEqual(profile["fields"]["internal_slot"]["indices"], [39, 40])
        self.assertEqual(profile["fields"]["parameter_selector"]["index"], 48)
        self.assertEqual(profile["fields"]["parameter_address"]["indices"], [21, 22])
        self.assertNotIn("model_id", profile["fields"])
        self.assertEqual(profile["fields"]["value"]["start_index"], 55)
        self.assertEqual(profile["fields"]["value"]["end_index_exclusive"], 63)
        self.assertEqual(codec["encoded_length"], 4)
        self.assertEqual(codec["configuration"]["lower_bytes"], [0, 0])
        self.assertEqual(codec["configuration"]["input_slice"], [4, 8])
        self.assertEqual(full_codec["encoded_length"], 8)
        self.assertEqual(full_codec["kind"], "float32_as_nibbles")

    def test_octaver_has_three_validated_integer_parameters(self) -> None:
        effect = self.catalog.effect_by_key("freq.octaver")
        self.assertEqual(effect.parameter_catalog_status, "physically_validated")
        self.assertEqual(effect.capabilities, ("parameters",))
        self.assertEqual(
            tuple(parameter.key for parameter in effect.parameters),
            ("low_oct", "high_oct", "dry"),
        )
        self.assertEqual(
            tuple(dict(parameter.message_match)["parameter_selector"] for parameter in effect.parameters),
            (0, 1, 2),
        )
        for parameter in effect.parameters:
            self.assertEqual(parameter.value_type, "integer")
            self.assertEqual((parameter.minimum, parameter.maximum, parameter.step), (0, 100, 1))
            self.assertEqual(parameter.protocol_profile, "effect_parameter_response_1c_v1")
            self.assertEqual(parameter.value_codec, "upper_float32_nibbles_v1")

    def test_dual_melody_has_signed_low_pitch_and_physical_selector_gap(self) -> None:
        effect = self.catalog.effect_by_key("freq.dual_melody")
        self.assertEqual(effect.parameter_catalog_status, "physically_validated")
        self.assertEqual(effect.capabilities, ("parameters",))
        self.assertEqual(
            tuple(parameter.key for parameter in effect.parameters),
            ("high_pitch", "low_pitch", "dry", "hi_vol", "low_vol"),
        )
        self.assertEqual(
            tuple(
                dict(parameter.message_match)["parameter_selector"]
                for parameter in effect.parameters
            ),
            (0, 1, 2, 4, 5),
        )
        expected_ranges = ((0, 24, 1), (-24, 0, 1), (0, 100, 1), (0, 100, 1), (0, 100, 1))
        for parameter, expected_range in zip(effect.parameters, expected_ranges):
            self.assertEqual(parameter.value_type, "integer")
            self.assertEqual(
                (parameter.minimum, parameter.maximum, parameter.step),
                expected_range,
            )
            self.assertEqual(
                parameter.protocol_profile,
                "effect_parameter_response_1c_v1",
            )
            self.assertEqual(parameter.value_codec, "upper_float32_nibbles_v1")
        low_pitch = effect.parameters[1]
        self.assertEqual(
            low_pitch.validation["signed_numeric_encoding"],
            "native_float32_negative",
        )
        self.assertEqual(
            low_pitch.validation["signed_values_physically_observed"],
            [-24, -23, -14, -13, -12, -1],
        )

    def test_pitch_has_five_consecutive_saved_parameter_selectors(self) -> None:
        effect = self.catalog.effect_by_key("freq.pitch")
        self.assertEqual(effect.parameter_catalog_status, "physically_validated")
        self.assertEqual(effect.capabilities, ("parameters",))
        self.assertEqual(
            tuple(parameter.key for parameter in effect.parameters),
            ("high_pitch", "low_pitch", "wet", "dry", "range"),
        )
        self.assertEqual(
            tuple(
                dict(parameter.message_match)["parameter_selector"]
                for parameter in effect.parameters
            ),
            (0, 1, 2, 3, 4),
        )
        self.assertEqual(
            tuple(
                (parameter.minimum, parameter.maximum, parameter.step)
                for parameter in effect.parameters
            ),
            ((0, 12, 1), (-12, 0, 1), (0, 100, 1), (0, 100, 1), (0, 100, 1)),
        )
        self.assertEqual(
            tuple(parameter.validation["saved_dump_defaults"] for parameter in effect.parameters),
            (12, 0, 50, 50, 50),
        )
        self.assertEqual(
            effect.parameters[1].validation["signed_numeric_encoding"],
            "native_float32_negative",
        )

    def test_harmony_d_has_named_enums_and_physical_selector_gap(self) -> None:
        effect = self.catalog.effect_by_key("freq.harmony_d")
        self.assertEqual(effect.parameter_catalog_status, "physically_validated")
        self.assertEqual(effect.capabilities, ("parameters",))
        self.assertEqual(
            tuple(parameter.key for parameter in effect.parameters),
            ("mix", "key", "mode", "interval_1", "interval_2", "smooth"),
        )
        self.assertEqual(
            tuple(
                dict(parameter.message_match)["parameter_selector"]
                for parameter in effect.parameters
            ),
            (0, 1, 2, 3, 4, 6),
        )
        self.assertEqual(tuple(effect.parameters[1].choices.values()), (
            "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B",
        ))
        self.assertEqual(tuple(effect.parameters[2].choices.values()), (
            "MAJOR", "MINOR", "H. MINOR", "DORIAN", "PHRYGIAN", "LYDIAN",
            "MIXOLYDIAN", "LOCRIAN",
        ))
        expected_intervals = (
            "-OCT", "-7TH", "-6TH", "-5TH", "-4TH", "-3RD", "-2ND",
            "+2ND", "+3RD", "+4TH", "+5TH", "+6TH", "+7TH", "+OCT",
        )
        self.assertEqual(tuple(effect.parameters[3].choices.values()), expected_intervals)
        self.assertEqual(tuple(effect.parameters[4].choices.values()), expected_intervals)
        self.assertEqual(effect.parameters[5].value_type, "boolean")
        self.assertEqual(effect.parameters[5].validation["incoming_selector_gap"], 5)

    def test_pitch_s_has_named_range_and_three_numeric_parameters(self) -> None:
        effect = self.catalog.effect_by_key("freq.pitch_s")
        self.assertEqual(effect.parameter_catalog_status, "physically_validated")
        self.assertEqual(effect.capabilities, ("parameters",))
        self.assertEqual(
            tuple(parameter.key for parameter in effect.parameters),
            ("range", "position", "mix", "level"),
        )
        self.assertEqual(
            tuple(
                dict(parameter.message_match)["parameter_selector"]
                for parameter in effect.parameters
            ),
            (0, 1, 2, 3),
        )
        self.assertEqual(
            tuple(effect.parameters[0].choices.values()),
            ("-2 OCT", "-1 OCT", "+1 OCT", "+2 OCT", "+/-1 OCT", "+/-2 OCT"),
        )
        self.assertEqual(effect.parameters[0].validation["saved_dump_default"], 2)
        self.assertEqual(
            tuple(
                (parameter.minimum, parameter.maximum, parameter.step)
                for parameter in effect.parameters[1:]
            ),
            ((0, 100, 1), (0, 100, 1), (0, 100, 1)),
        )

    def test_ring_mod_has_signed_fine_and_four_consecutive_selectors(self) -> None:
        effect = self.catalog.effect_by_key("freq.ring_mod")
        self.assertEqual(effect.parameter_catalog_status, "physically_validated")
        self.assertEqual(effect.capabilities, ("parameters",))
        self.assertEqual(
            tuple(parameter.key for parameter in effect.parameters),
            ("mix", "freq", "fine", "tone"),
        )
        self.assertEqual(
            tuple(
                dict(parameter.message_match)["parameter_selector"]
                for parameter in effect.parameters
            ),
            (0, 1, 2, 3),
        )
        self.assertEqual(
            tuple(
                (parameter.minimum, parameter.maximum, parameter.step)
                for parameter in effect.parameters
            ),
            ((0, 100, 1), (0, 100, 1), (-50, 50, 1), (0, 100, 1)),
        )
        self.assertEqual(
            effect.parameters[2].validation["signed_numeric_encoding"],
            "native_float32_negative",
        )

    def test_tape_mod_has_four_validated_numeric_parameters(self) -> None:
        effect = self.catalog.effect_by_key("freq.tape_mod")
        self.assertEqual(effect.parameter_catalog_status, "physically_validated")
        self.assertEqual(effect.capabilities, ("parameters",))
        self.assertEqual(
            tuple(parameter.key for parameter in effect.parameters),
            ("saturation", "mix", "volume", "high_cut"),
        )
        self.assertEqual(
            tuple(
                dict(parameter.message_match)["parameter_selector"]
                for parameter in effect.parameters
            ),
            (0, 1, 2, 3),
        )
        for parameter in effect.parameters:
            self.assertEqual(
                (parameter.minimum, parameter.maximum, parameter.step),
                (0, 100, 1),
            )
            self.assertEqual(parameter.validation["saved_dump_default"], 50)

    def test_voks_wah_has_four_validated_numeric_parameters(self) -> None:
        effect = self.catalog.effect_by_key("wah.voks_wah")
        self.assertEqual(effect.parameter_catalog_status, "physically_validated")
        self.assertEqual(effect.capabilities, ("parameters",))
        self.assertEqual(effect.model_id, 0x01)
        self.assertEqual(effect.secondary_selector, 0x05)
        self.assertEqual(
            tuple(parameter.key for parameter in effect.parameters),
            ("range", "q", "volume", "position"),
        )
        self.assertEqual(
            tuple(
                dict(parameter.message_match)["parameter_selector"]
                for parameter in effect.parameters
            ),
            (0, 1, 2, 3),
        )
        for parameter in effect.parameters:
            self.assertEqual(
                (parameter.minimum, parameter.maximum, parameter.step),
                (0, 100, 1),
            )
            self.assertEqual(parameter.validation["saved_dump_default"], 50)

    def test_cry_wah_has_four_validated_numeric_parameters(self) -> None:
        effect = self.catalog.effect_by_key("wah.cry_wah")
        self.assertEqual(effect.parameter_catalog_status, "physically_validated")
        self.assertEqual(effect.capabilities, ("parameters",))
        self.assertEqual(effect.model_id, 0x08)
        self.assertEqual(effect.secondary_selector, 0x05)
        self.assertEqual(
            tuple(parameter.key for parameter in effect.parameters),
            ("range", "q", "volume", "position"),
        )
        self.assertEqual(
            tuple(
                dict(parameter.message_match)["parameter_selector"]
                for parameter in effect.parameters
            ),
            (0, 1, 2, 3),
        )
        for parameter in effect.parameters:
            self.assertEqual(
                (parameter.minimum, parameter.maximum, parameter.step),
                (0, 100, 1),
            )
            self.assertEqual(parameter.validation["saved_dump_default"], 50)

    def test_rack_wah_has_four_numeric_parameters_and_boolean_eq(self) -> None:
        effect = self.catalog.effect_by_key("wah.rack_wah")
        self.assertEqual(effect.parameter_catalog_status, "physically_validated")
        self.assertEqual(effect.capabilities, ("parameters",))
        self.assertEqual((effect.model_id, effect.secondary_selector), (0x0A, 0x05))
        self.assertEqual(
            tuple(parameter.key for parameter in effect.parameters),
            ("range", "q", "volume", "position", "eq"),
        )
        self.assertEqual(
            tuple(dict(parameter.message_match)["parameter_selector"] for parameter in effect.parameters),
            (0, 1, 2, 3, 4),
        )
        self.assertEqual(effect.parameters[4].value_type, "boolean")
        self.assertEqual(effect.parameters[4].validation["saved_dump_default"], 1)
        self.assertEqual(
            dict(effect.parameters[4].validation["boolean_encoding"]),
            {"false": 0, "true": 1},
        )

    def test_bass_wah_has_four_physically_validated_parameters(self) -> None:
        effect = self.catalog.effect_by_key("wah.bass_wah")
        self.assertEqual(effect.parameter_catalog_status, "physically_validated")
        self.assertEqual(effect.capabilities, ("parameters",))
        self.assertEqual((effect.model_id, effect.secondary_selector), (0x07, 0x05))
        self.assertEqual(
            tuple(parameter.key for parameter in effect.parameters),
            ("range", "q", "volume", "position"),
        )
        self.assertEqual(
            tuple(dict(parameter.message_match)["parameter_selector"] for parameter in effect.parameters),
            (0, 1, 2, 3),
        )
        for parameter in effect.parameters:
            self.assertTrue(parameter.validation["physical"])
            self.assertEqual(
                parameter.identification_status,
                "validated_with_chain_effect_context",
            )
            self.assertTrue(
                parameter.validation["physical_validation_without_pcapng"]
            )

    def test_touch_wah_has_four_numeric_parameters_and_named_mode(self) -> None:
        effect = self.catalog.effect_by_key("wah.touch_wah")
        self.assertEqual(effect.parameter_catalog_status, "physically_validated")
        self.assertEqual((effect.model_id, effect.secondary_selector), (0x0F, 0x01))
        self.assertEqual(
            tuple(parameter.key for parameter in effect.parameters),
            ("sense", "range", "q", "mix", "mode"),
        )
        self.assertEqual(
            tuple(dict(parameter.message_match)["parameter_selector"] for parameter in effect.parameters),
            (0, 1, 2, 3, 4),
        )
        mode = effect.parameters[4]
        self.assertEqual(mode.value_type, "enum")
        self.assertEqual(tuple(mode.choices.values()), ("GUITAR", "BASS"))
        self.assertEqual(mode.validation["saved_dump_default"], 0)
        for parameter in effect.parameters:
            self.assertEqual(
                parameter.validation["monitor_integration_physical_validation"],
                "approved",
            )

    def test_auto_wah_has_conditional_rate_domain(self) -> None:
        effect = self.catalog.effect_by_key("wah.auto_wah")
        self.assertEqual(effect.parameter_catalog_status, "physically_validated")
        self.assertEqual(effect.capabilities, ("parameters",))
        self.assertEqual((effect.model_id, effect.secondary_selector), (0x15, 0x01))
        self.assertEqual(
            tuple(parameter.key for parameter in effect.parameters),
            ("depth", "rate", "volume", "low", "q", "high", "sync"),
        )
        self.assertEqual(
            tuple(dict(parameter.message_match)["parameter_selector"] for parameter in effect.parameters),
            (0, 1, 2, 3, 4, 5, 6),
        )
        rate = effect.parameters[1]
        self.assertEqual(rate.value_type, "number")
        self.assertEqual((rate.minimum, rate.maximum, rate.step), (0, 10, 0.1))
        self.assertEqual(rate.value_codec, "float32_nibbles_v1")
        states = rate.value_domain["states"]
        self.assertEqual(states[0]["default_value"], 0.5)
        self.assertEqual(
            states[0]["presentation"],
            {"kind": "numeric", "unit": "Hz", "decimals": 1},
        )
        self.assertEqual(states[1]["default_value"], 4)
        self.assertEqual(
            tuple(choice["label"] for choice in states[1]["presentation"]["choices"]),
            ("1/1", "1/2", "1/2D", "1/2T", "1/4", "1/4D", "1/4T", "1/8", "1/8D", "1/8T", "1/16"),
        )
        self.assertEqual(effect.parameters[6].value_type, "boolean")
        self.assertEqual(effect.parameters[6].validation["saved_dump_default"], 1)
        for parameter in effect.parameters:
            self.assertEqual(
                parameter.validation["monitor_integration_physical_validation"],
                "approved",
            )

    def test_skreamer_has_three_saved_integer_parameters(self) -> None:
        effect = self.catalog.effect_by_key("drv.skreamer")
        self.assertEqual(effect.parameter_catalog_status, "physically_validated")
        self.assertEqual(effect.capabilities, ("parameters",))
        self.assertEqual((effect.model_id, effect.secondary_selector), (0x00, 0x03))
        self.assertEqual(
            tuple(parameter.key for parameter in effect.parameters),
            ("gain", "tone", "volume"),
        )
        self.assertEqual(
            tuple(dict(parameter.message_match)["parameter_selector"] for parameter in effect.parameters),
            (0, 1, 2),
        )
        self.assertEqual(
            tuple(parameter.validation["saved_dump_default"] for parameter in effect.parameters),
            (40, 70, 50),
        )
        for parameter in effect.parameters:
            self.assertEqual(parameter.value_type, "integer")
            self.assertEqual((parameter.minimum, parameter.maximum, parameter.step), (0, 100, 1))
            self.assertEqual(
                parameter.validation["monitor_integration_physical_validation"],
                "approved",
            )

    def test_skreamer9_validates_the_inferred_skreamer_layout(self) -> None:
        effect = self.catalog.effect_by_key("drv.skreamer9")
        self.assertEqual(effect.parameter_catalog_status, "physically_validated")
        self.assertEqual((effect.model_id, effect.secondary_selector), (0x01, 0x03))
        self.assertEqual(
            tuple(parameter.key for parameter in effect.parameters),
            ("gain", "tone", "volume"),
        )
        self.assertEqual(
            tuple(dict(parameter.message_match)["parameter_selector"] for parameter in effect.parameters),
            (0, 1, 2),
        )
        for parameter in effect.parameters:
            self.assertTrue(parameter.validation["physical"])
            self.assertEqual(parameter.validation["inference_sources"], ["drv.skreamer"])
            self.assertNotIn("saved_dump_default", parameter.validation)
            self.assertTrue(parameter.validation["physical_validation_without_pcapng"])
            self.assertEqual(
                parameter.validation["monitor_integration_physical_validation"],
                "approved",
            )

    def test_butter_od_has_two_parameters_and_ignores_saved_selector_two(self) -> None:
        effect = self.catalog.effect_by_key("drv.butter_od")
        self.assertEqual(effect.parameter_catalog_status, "physically_validated")
        self.assertEqual((effect.model_id, effect.secondary_selector), (0x02, 0x03))
        self.assertEqual(
            tuple(parameter.key for parameter in effect.parameters),
            ("gain", "volume"),
        )
        self.assertEqual(
            tuple(dict(parameter.message_match)["parameter_selector"] for parameter in effect.parameters),
            (0, 1),
        )
        self.assertEqual(
            tuple(parameter.validation["saved_dump_default"] for parameter in effect.parameters),
            (40, 70),
        )
        for parameter in effect.parameters:
            self.assertEqual(
                parameter.validation["monitor_integration_physical_validation"],
                "approved",
            )

    def test_warm_and_super_od_validate_the_three_control_drive_layout(self) -> None:
        cases = (
            ("drv.warm_od", 0x04, (40, 50, 50)),
            ("drv.super_od", 0x06, (50, 50, 50)),
        )
        for effect_key, model_id, defaults in cases:
            with self.subTest(effect=effect_key):
                effect = self.catalog.effect_by_key(effect_key)
                self.assertEqual(effect.parameter_catalog_status, "physically_validated")
                self.assertEqual((effect.model_id, effect.secondary_selector), (model_id, 0x03))
                self.assertEqual(
                    tuple(parameter.key for parameter in effect.parameters),
                    ("gain", "tone", "volume"),
                )
                self.assertEqual(
                    tuple(dict(parameter.message_match)["parameter_selector"] for parameter in effect.parameters),
                    (0, 1, 2),
                )
                self.assertEqual(
                    tuple(parameter.validation["saved_dump_default"] for parameter in effect.parameters),
                    defaults,
                )
                for parameter in effect.parameters:
                    self.assertTrue(parameter.validation["physical"])
                    self.assertEqual(
                        parameter.validation["monitor_integration_physical_validation"],
                        "approved",
                    )
                    self.assertEqual(
                        parameter.validation["internal_slots_observed"],
                        [4, 5, 10, 11],
                    )
                    self.assertEqual(
                        parameter.validation["saved_dump_default_source"],
                        "user_reported_official_ui",
                    )

    def test_blues_od_validates_three_control_layout_in_two_slots(self) -> None:
        effect = self.catalog.effect_by_key("drv.blues_od")
        self.assertEqual(effect.parameter_catalog_status, "physically_validated")
        self.assertEqual((effect.model_id, effect.secondary_selector), (0x09, 0x03))
        self.assertEqual(
            tuple(parameter.key for parameter in effect.parameters),
            ("gain", "tone", "volume"),
        )
        self.assertEqual(
            tuple(dict(parameter.message_match)["parameter_selector"] for parameter in effect.parameters),
            (0, 1, 2),
        )
        self.assertEqual(
            tuple(parameter.validation["saved_dump_default"] for parameter in effect.parameters),
            (40, 60, 50),
        )
        for parameter in effect.parameters:
            self.assertTrue(parameter.validation["physical"])
            self.assertEqual(
                parameter.validation["monitor_integration_physical_validation"],
                "approved",
            )
            self.assertEqual(parameter.validation["internal_slots_observed"], [4, 10])

    def test_full_od_validates_three_controls_and_hp_lp_mode(self) -> None:
        effect = self.catalog.effect_by_key("drv.full_od")
        self.assertEqual(effect.parameter_catalog_status, "physically_validated")
        self.assertEqual((effect.model_id, effect.secondary_selector), (0x0A, 0x03))
        self.assertEqual(
            tuple(parameter.key for parameter in effect.parameters),
            ("gain", "tone", "volume", "mode"),
        )
        self.assertEqual(
            tuple(dict(parameter.message_match)["parameter_selector"] for parameter in effect.parameters),
            (0, 1, 2, 3),
        )
        self.assertEqual(
            tuple(parameter.validation["saved_dump_value"] for parameter in effect.parameters),
            (21, 43, 65, 1),
        )
        self.assertEqual(
            tuple(effect.parameters[3].choices.items()),
            ((0, "LP"), (1, "HP")),
        )
        for parameter in effect.parameters:
            self.assertTrue(parameter.validation["physical"])
            self.assertEqual(
                parameter.validation["monitor_integration_physical_validation"],
                "approved",
            )
            self.assertEqual(parameter.validation["internal_slots_observed"], [1, 5, 11])

    def test_breaker_od_validates_firmware_three_control_layout(self) -> None:
        effect = self.catalog.effect_by_key("drv.breaker_od")
        self.assertEqual(effect.parameter_catalog_status, "physically_validated")
        self.assertEqual((effect.model_id, effect.secondary_selector), (0x0E, 0x03))
        self.assertEqual(
            tuple(parameter.key for parameter in effect.parameters),
            ("gain", "tone", "volume"),
        )
        self.assertEqual(
            tuple(dict(parameter.message_match)["parameter_selector"] for parameter in effect.parameters),
            (0, 1, 2),
        )
        self.assertEqual(
            tuple(parameter.validation["saved_dump_default"] for parameter in effect.parameters),
            (60, 50, 50),
        )
        for parameter in effect.parameters:
            self.assertTrue(parameter.validation["physical"])
            self.assertEqual(parameter.validation["internal_slots_observed"], [4, 10])
            self.assertEqual(
                parameter.validation["monitor_integration_physical_validation"],
                "approved",
            )
            self.assertEqual(
                parameter.validation["manual_mismatch"],
                "firmware_ui_has_gain_tone_volume",
            )

    def test_gerden_od_validates_voice_as_fourth_numeric_control(self) -> None:
        effect = self.catalog.effect_by_key("drv.gerden_od")
        self.assertEqual(effect.parameter_catalog_status, "physically_validated")
        self.assertEqual((effect.model_id, effect.secondary_selector), (0x10, 0x03))
        self.assertEqual(
            tuple(parameter.key for parameter in effect.parameters),
            ("gain", "tone", "volume", "voice"),
        )
        self.assertEqual(
            tuple(dict(parameter.message_match)["parameter_selector"] for parameter in effect.parameters),
            (0, 1, 2, 3),
        )
        self.assertEqual(
            tuple(parameter.validation["saved_dump_value"] for parameter in effect.parameters),
            (21, 43, 65, 87),
        )
        self.assertEqual(
            tuple(parameter.validation["saved_dump_default"] for parameter in effect.parameters),
            (40, 30, 50, 60),
        )
        for parameter in effect.parameters:
            self.assertTrue(parameter.validation["physical"])
            self.assertEqual(
                parameter.validation["monitor_integration_physical_validation"],
                "approved",
            )
            self.assertEqual(parameter.validation["internal_slots_observed"], [1, 5, 11])

    def test_timmy_od_validates_four_controls_and_three_way_mode(self) -> None:
        effect = self.catalog.effect_by_key("drv.timmy_od")
        self.assertEqual(effect.parameter_catalog_status, "physically_validated")
        self.assertEqual((effect.model_id, effect.secondary_selector), (0x1E, 0x03))
        self.assertEqual(
            tuple(parameter.key for parameter in effect.parameters),
            ("gain", "volume", "bass", "treble", "mode"),
        )
        self.assertEqual(
            tuple(dict(parameter.message_match)["parameter_selector"] for parameter in effect.parameters),
            (0, 1, 2, 3, 4),
        )
        self.assertEqual(tuple(effect.parameters[4].choices.items()), ((0, "I"), (1, "II"), (2, "III")))
        self.assertEqual(effect.parameters[4].validation["saved_dump_default_label"], "II")

    def test_master_od_validates_five_numeric_controls(self) -> None:
        effect = self.catalog.effect_by_key("drv.master_od")
        self.assertEqual(effect.parameter_catalog_status, "physically_validated")
        self.assertEqual((effect.model_id, effect.secondary_selector), (0x0F, 0x03))
        self.assertEqual(
            tuple(parameter.key for parameter in effect.parameters),
            ("gain", "volume", "bass", "middle", "treble"),
        )
        self.assertEqual(
            tuple(dict(parameter.message_match)["parameter_selector"] for parameter in effect.parameters),
            (0, 1, 2, 3, 4),
        )
        self.assertEqual(
            tuple(parameter.validation["saved_dump_value"] for parameter in effect.parameters),
            (21, 43, 65, 87, 32),
        )
        self.assertEqual(
            tuple(parameter.validation["saved_dump_default"] for parameter in effect.parameters),
            (40, 50, 50, 50, 50),
        )

    def test_solar_fuzz_validates_two_controls_and_ignores_residuals(self) -> None:
        effect = self.catalog.effect_by_key("drv.solar_fuzz")
        self.assertEqual(effect.parameter_catalog_status, "physically_validated")
        self.assertEqual((effect.model_id, effect.secondary_selector), (0x26, 0x03))
        self.assertEqual(
            tuple(parameter.key for parameter in effect.parameters),
            ("fuzz", "volume"),
        )
        self.assertEqual(
            tuple(dict(parameter.message_match)["parameter_selector"] for parameter in effect.parameters),
            (0, 1),
        )
        for parameter in effect.parameters:
            self.assertEqual(
                parameter.validation["saved_dump_residual_selectors_ignored"],
                [2, 3, 4],
            )

    def test_phase54_monitor_integrations_are_approved(self) -> None:
        for effect_key in ("drv.timmy_od", "drv.master_od", "drv.solar_fuzz"):
            with self.subTest(effect=effect_key):
                effect = self.catalog.effect_by_key(effect_key)
                for parameter in effect.parameters:
                    self.assertEqual(
                        parameter.validation["monitor_integration_physical_validation"],
                        "approved",
                    )

    def test_phase55_validates_three_known_drive_layouts(self) -> None:
        cases = (
            ("drv.fuzz_cream", 0x22, ("sustain", "tone", "volume"), (40, 50, 50)),
            ("drv.red_fuzz", 0x24, ("fuzz", "volume"), (50, 50)),
            ("drv.jp_dist", 0x2A, ("gain", "tone", "volume"), (50, 50, 50)),
        )
        for effect_key, model_id, keys, defaults in cases:
            with self.subTest(effect=effect_key):
                effect = self.catalog.effect_by_key(effect_key)
                self.assertEqual(effect.parameter_catalog_status, "physically_validated")
                self.assertEqual((effect.model_id, effect.secondary_selector), (model_id, 0x03))
                self.assertEqual(tuple(parameter.key for parameter in effect.parameters), keys)
                self.assertEqual(
                    tuple(dict(parameter.message_match)["parameter_selector"] for parameter in effect.parameters),
                    tuple(range(len(keys))),
                )
                self.assertEqual(
                    tuple(parameter.validation["saved_dump_default"] for parameter in effect.parameters),
                    defaults,
                )
                for parameter in effect.parameters:
                    self.assertTrue(parameter.validation["physical"])
                    self.assertEqual(
                        parameter.validation["monitor_integration_physical_validation"],
                        "approved",
                    )

    def test_phase56_validates_dark_plexi_and_master_dist_layouts(self) -> None:
        cases = (
            ("drv.dark_mouse", 0x2B, ("gain", "filter", "volume")),
            ("drv.plexi_dist", 0x2D, ("gain", "volume", "bass", "middle", "treble")),
            ("drv.master_dist", 0x2E, ("gain", "volume", "bass", "contour", "treble")),
        )
        for effect_key, model_id, keys in cases:
            with self.subTest(effect=effect_key):
                effect = self.catalog.effect_by_key(effect_key)
                self.assertEqual(effect.parameter_catalog_status, "physically_validated")
                self.assertEqual((effect.model_id, effect.secondary_selector), (model_id, 0x03))
                self.assertEqual(tuple(parameter.key for parameter in effect.parameters), keys)
                self.assertEqual(
                    tuple(dict(parameter.message_match)["parameter_selector"] for parameter in effect.parameters),
                    tuple(range(len(keys))),
                )
                for parameter in effect.parameters:
                    self.assertTrue(parameter.validation["physical"])
                    self.assertEqual(parameter.validation["saved_dump_default"], 50)
                    self.assertEqual(
                        parameter.validation["monitor_integration_physical_validation"],
                        "approved",
                    )

    def test_phase57_validates_dist_plus_shark_and_strive(self) -> None:
        cases = (
            ("drv.dist_plus", 0x29, ("gain", "volume")),
            ("drv.shark", 0x30, ("gain", "tone", "volume")),
            ("drv.strive", 0x32, ("gain", "tone", "volume", "mode")),
        )
        for effect_key, model_id, keys in cases:
            with self.subTest(effect=effect_key):
                effect = self.catalog.effect_by_key(effect_key)
                self.assertEqual(effect.parameter_catalog_status, "physically_validated")
                self.assertEqual((effect.model_id, effect.secondary_selector), (model_id, 0x03))
                self.assertEqual(tuple(parameter.key for parameter in effect.parameters), keys)
                self.assertEqual(
                    tuple(dict(parameter.message_match)["parameter_selector"] for parameter in effect.parameters),
                    tuple(range(len(keys))),
                )
                for parameter in effect.parameters:
                    self.assertTrue(parameter.validation["physical"])
                    self.assertEqual(
                        parameter.validation["monitor_integration_physical_validation"],
                        "approved",
                    )
        strive = self.catalog.effect_by_key("drv.strive")
        self.assertEqual(tuple(strive.parameters[3].choices.items()), ((0, "I"), (1, "II"), (2, "III")))
        self.assertEqual(strive.parameters[3].validation["saved_dump_default_label"], "I")

    def test_phase58_validates_sardar_bass_od_and_bass_dist(self) -> None:
        cases = (
            ("drv.sardar_dist", 0x52, ("gain", "volume", "bass", "treble", "presence", "tight")),
            ("drv.bass_od", 0x3F, ("gain", "tone", "volume", "mode", "blend")),
            ("drv.bass_dist", 0x40, ("gain", "blend", "volume", "bass", "treble")),
        )
        for effect_key, model_id, keys in cases:
            with self.subTest(effect=effect_key):
                effect = self.catalog.effect_by_key(effect_key)
                self.assertEqual(effect.parameter_catalog_status, "physically_validated")
                self.assertEqual((effect.model_id, effect.secondary_selector), (model_id, 0x03))
                self.assertEqual(tuple(parameter.key for parameter in effect.parameters), keys)
                self.assertEqual(
                    tuple(dict(parameter.message_match)["parameter_selector"] for parameter in effect.parameters),
                    tuple(range(len(keys))),
                )
                for parameter in effect.parameters:
                    self.assertTrue(parameter.validation["physical"])
                    self.assertEqual(parameter.validation["monitor_integration_physical_validation"], "approved")
        bass_od = self.catalog.effect_by_key("drv.bass_od")
        self.assertEqual(tuple(bass_od.parameters[3].choices.items()), ((0, "NORMAL"), (1, "SCOOP"), (2, "EDGE")))
        self.assertEqual(bass_od.parameters[3].validation["saved_dump_default_label"], "NORMAL")

    def test_filter_has_conditional_rate_domain(self) -> None:
        effect = self.catalog.effect_by_key("freq.filter")
        self.assertEqual(effect.parameter_catalog_status, "physically_validated")
        self.assertEqual(effect.capabilities, ("parameters",))
        self.assertEqual(
            tuple(parameter.key for parameter in effect.parameters),
            ("step_1", "step_2", "step_3", "step_4", "rate", "sync"),
        )
        self.assertEqual(
            tuple(dict(parameter.message_match)["parameter_selector"] for parameter in effect.parameters),
            (0, 1, 2, 3, 4, 5),
        )
        rate = effect.parameters[4]
        self.assertEqual(rate.value_type, "integer")
        self.assertEqual((rate.minimum, rate.maximum, rate.step), (0, 100, 1))
        domain = dict(rate.value_domain)
        self.assertEqual(domain["controller_parameter"], "sync")
        self.assertTrue(domain["reset_on_controller_change"])
        states = domain["states"]
        self.assertEqual(states[0]["controller_value"], False)
        self.assertEqual(states[0]["default_value"], 10)
        self.assertEqual(states[0]["presentation"]["kind"], "numeric")
        self.assertEqual(states[1]["controller_value"], True)
        self.assertEqual(states[1]["default_value"], 4)
        self.assertEqual(
            tuple(choice["label"] for choice in states[1]["presentation"]["choices"]),
            ("1/1", "1/2", "1/2d", "1/2t", "1/4", "1/4d", "1/4t", "1/8", "1/8d", "1/8t", "1/16"),
        )
        self.assertEqual(effect.parameters[5].value_type, "boolean")

    def test_parameter_envelope_class_field_is_not_structural_class_id(self) -> None:
        profile = self.catalog.protocol_profile_by_key("effect_parameter_response_1c_v1").document
        self.assertEqual(profile["fields"]["class_id"]["semantic_status"], "opaque_not_structural_effect_class_id")
        self.assertFalse(profile["validation"]["parameter_envelope_class_field_is_structural_class_id"])

    def test_historical_facade_is_backwards_compatible(self) -> None:
        self.assertIs(facade.EFFECT_CLASSES, self.catalog.classes)
        self.assertEqual(facade.DYN_CLASS_ID, 0x00)
        self.assertEqual(facade.FREQ_CLASS_ID, 0x01)
        self.assertEqual(facade.VOL_CLASS_ID, 0x0F)
        self.assertIs(facade.DYN_MODELS, self.catalog.class_by_key("dyn").models)
        self.assertEqual(facade.find_effect_class("dyn").name, "DYN")
        self.assertEqual(
            facade.find_effect_model(facade.find_effect_class("DYN"), "dyn.m_boost").name,
            "M-BOOST",
        )

    def test_exporter_reproduces_the_same_structural_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "catalog"
            output.mkdir()
            for directory in ("schemas", "protocol_profiles", "value_codecs"):
                shutil.copytree(CATALOG_ROOT / directory, output / directory)

            export_catalog(facade.EFFECT_CLASSES, output, force=True)
            exported = load_effect_catalog(output)
            self.assertEqual(
                structural_snapshot(exported.classes),
                structural_snapshot(self.catalog.classes),
            )
            exported_filter = exported.effect_by_key("freq.filter")
            exported_octaver = exported.effect_by_key("freq.octaver")
            exported_dual_melody = exported.effect_by_key("freq.dual_melody")
            exported_pitch = exported.effect_by_key("freq.pitch")
            exported_harmony_d = exported.effect_by_key("freq.harmony_d")
            exported_pitch_s = exported.effect_by_key("freq.pitch_s")
            exported_ring_mod = exported.effect_by_key("freq.ring_mod")
            exported_tape_mod = exported.effect_by_key("freq.tape_mod")
            exported_voks_wah = exported.effect_by_key("wah.voks_wah")
            exported_cry_wah = exported.effect_by_key("wah.cry_wah")
            exported_rack_wah = exported.effect_by_key("wah.rack_wah")
            exported_bass_wah = exported.effect_by_key("wah.bass_wah")
            exported_touch_wah = exported.effect_by_key("wah.touch_wah")
            exported_auto_wah = exported.effect_by_key("wah.auto_wah")
            exported_skreamer = exported.effect_by_key("drv.skreamer")
            exported_skreamer9 = exported.effect_by_key("drv.skreamer9")
            exported_butter_od = exported.effect_by_key("drv.butter_od")
            exported_warm_od = exported.effect_by_key("drv.warm_od")
            exported_super_od = exported.effect_by_key("drv.super_od")
            exported_mboost = exported.effect_by_key("dyn.m_boost")
            exported_comp1 = exported.effect_by_key("dyn.comp1")
            exported_comp2 = exported.effect_by_key("dyn.comp2")
            exported_comp3 = exported.effect_by_key("dyn.comp3")
            exported_ac_boost = exported.effect_by_key("dyn.ac_boost")
            exported_bb_boost = exported.effect_by_key("dyn.bb_boost")
            exported_rc_boost = exported.effect_by_key("dyn.rc_boost")
            exported_fat_boost = exported.effect_by_key("dyn.fat_boost")
            exported_gate2 = exported.effect_by_key("dyn.gate_2")
            exported_gate3 = exported.effect_by_key("dyn.gate_3")
            exported_e_boost = exported.effect_by_key("dyn.e_boost")
            exported_ac_woody = exported.effect_by_key("dyn.ac_woody")
            exported_gate1 = exported.effect_by_key("dyn.gate_1")
            self.assertEqual(
                exported_filter.parameters,
                self.catalog.effect_by_key("freq.filter").parameters,
            )
            self.assertEqual(
                exported_octaver.parameters,
                self.catalog.effect_by_key("freq.octaver").parameters,
            )
            self.assertEqual(
                exported_dual_melody.parameters,
                self.catalog.effect_by_key("freq.dual_melody").parameters,
            )
            self.assertEqual(
                exported_pitch.parameters,
                self.catalog.effect_by_key("freq.pitch").parameters,
            )
            self.assertEqual(
                exported_harmony_d.parameters,
                self.catalog.effect_by_key("freq.harmony_d").parameters,
            )
            self.assertEqual(
                exported_pitch_s.parameters,
                self.catalog.effect_by_key("freq.pitch_s").parameters,
            )
            self.assertEqual(
                exported_ring_mod.parameters,
                self.catalog.effect_by_key("freq.ring_mod").parameters,
            )
            self.assertEqual(
                exported_tape_mod.parameters,
                self.catalog.effect_by_key("freq.tape_mod").parameters,
            )
            self.assertEqual(
                exported_voks_wah.parameters,
                self.catalog.effect_by_key("wah.voks_wah").parameters,
            )
            self.assertEqual(
                exported_cry_wah.parameters,
                self.catalog.effect_by_key("wah.cry_wah").parameters,
            )
            self.assertEqual(
                exported_rack_wah.parameters,
                self.catalog.effect_by_key("wah.rack_wah").parameters,
            )
            self.assertEqual(
                exported_bass_wah.parameters,
                self.catalog.effect_by_key("wah.bass_wah").parameters,
            )
            self.assertEqual(
                exported_touch_wah.parameters,
                self.catalog.effect_by_key("wah.touch_wah").parameters,
            )
            self.assertEqual(
                exported_auto_wah.parameters,
                self.catalog.effect_by_key("wah.auto_wah").parameters,
            )
            self.assertEqual(
                exported_skreamer.parameters,
                self.catalog.effect_by_key("drv.skreamer").parameters,
            )
            self.assertEqual(
                exported_skreamer9.parameters,
                self.catalog.effect_by_key("drv.skreamer9").parameters,
            )
            self.assertEqual(
                exported_butter_od.parameters,
                self.catalog.effect_by_key("drv.butter_od").parameters,
            )
            self.assertEqual(
                exported_warm_od.parameters,
                self.catalog.effect_by_key("drv.warm_od").parameters,
            )
            self.assertEqual(
                exported_super_od.parameters,
                self.catalog.effect_by_key("drv.super_od").parameters,
            )
            self.assertEqual(
                exported_mboost.parameters,
                self.catalog.effect_by_key("dyn.m_boost").parameters,
            )
            self.assertEqual(
                exported_comp1.parameters,
                self.catalog.effect_by_key("dyn.comp1").parameters,
            )
            self.assertEqual(
                exported_comp2.parameters,
                self.catalog.effect_by_key("dyn.comp2").parameters,
            )
            self.assertEqual(
                exported_comp3.parameters,
                self.catalog.effect_by_key("dyn.comp3").parameters,
            )
            self.assertEqual(
                exported_ac_boost.parameters,
                self.catalog.effect_by_key("dyn.ac_boost").parameters,
            )
            self.assertEqual(
                exported_bb_boost.parameters,
                self.catalog.effect_by_key("dyn.bb_boost").parameters,
            )
            self.assertEqual(
                exported_rc_boost.parameters,
                self.catalog.effect_by_key("dyn.rc_boost").parameters,
            )
            self.assertEqual(
                exported_fat_boost.parameters,
                self.catalog.effect_by_key("dyn.fat_boost").parameters,
            )
            self.assertEqual(
                exported_gate2.parameters,
                self.catalog.effect_by_key("dyn.gate_2").parameters,
            )
            self.assertEqual(
                exported_gate3.parameters,
                self.catalog.effect_by_key("dyn.gate_3").parameters,
            )
            self.assertEqual(
                exported_e_boost.parameters,
                self.catalog.effect_by_key("dyn.e_boost").parameters,
            )
            self.assertEqual(
                exported_ac_woody.parameters,
                self.catalog.effect_by_key("dyn.ac_woody").parameters,
            )
            self.assertEqual(
                exported_gate1.parameters,
                self.catalog.effect_by_key("dyn.gate_1").parameters,
            )

    def test_loader_rejects_effect_key_from_another_class(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            copied = Path(temporary_directory) / "catalog"
            shutil.copytree(CATALOG_ROOT, copied)
            effect_path = copied / "effects" / "dyn" / "004_m_boost.json"
            document = json.loads(effect_path.read_text(encoding="utf-8"))
            document["key"] = "freq.m_boost"
            effect_path.write_text(json.dumps(document), encoding="utf-8")

            with self.assertRaises(CatalogValidationError):
                load_effect_catalog(copied)

    def test_loader_rejects_nonportable_class_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            shutil.copytree(CATALOG_ROOT, root / "catalog")
            copied = root / "catalog"
            manifest_path = copied / "catalog.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["class_indexes"][0] = "C:\\catalog\\freq.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            with self.assertRaises(CatalogValidationError):
                load_effect_catalog(copied)

    def test_loader_rejects_unknown_parameter_match_field(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            copied = Path(temporary_directory) / "catalog"
            shutil.copytree(CATALOG_ROOT, copied)
            effect_path = copied / "effects" / "dyn" / "004_m_boost.json"
            document = json.loads(effect_path.read_text(encoding="utf-8"))
            document["parameters"][0]["protocol"]["message_match"] = {
                "unknown_marker": 1
            }
            effect_path.write_text(json.dumps(document), encoding="utf-8")

            with self.assertRaises(CatalogValidationError):
                load_effect_catalog(copied)

    def test_loader_rejects_overlapping_fixed_segments(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            copied = Path(temporary_directory) / "catalog"
            shutil.copytree(CATALOG_ROOT, copied)
            profile_path = (
                copied
                / "protocol_profiles"
                / "effect_parameter_response_1c_v1.json"
            )
            document = json.loads(profile_path.read_text(encoding="utf-8"))
            document["fixed_segments"].append(
                {"start_index": 5, "bytes": [0]}
            )
            profile_path.write_text(json.dumps(document), encoding="utf-8")

            with self.assertRaises(CatalogValidationError):
                load_effect_catalog(copied)


class CatalogSchemaDocumentTests(unittest.TestCase):
    def test_schema_documents_use_draft_2020_12(self) -> None:
        schemas = sorted((CATALOG_ROOT / "schemas").glob("*.json"))
        self.assertEqual(len(schemas), 5)
        for schema in schemas:
            with self.subTest(schema=schema.name):
                document = json.loads(schema.read_text(encoding="utf-8"))
                self.assertEqual(
                    document["$schema"],
                    "https://json-schema.org/draft/2020-12/schema",
                )


if __name__ == "__main__":
    unittest.main()
