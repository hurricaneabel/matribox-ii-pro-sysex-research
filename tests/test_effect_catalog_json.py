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
        self.assertEqual(self.catalog.catalog_version, 4)
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
                "dyn.e_boost",
                "dyn.ac_woody",
                "dyn.gate_1",
            }
        ]
        self.assertEqual(len(pending), 262)
        for model in pending:
            with self.subTest(effect=model.key):
                self.assertEqual(model.parameter_catalog_status, "pending")
                self.assertEqual(model.parameters, ())

    def test_protocol_profile_and_codec_are_resolved(self) -> None:
        profiles = {item.key: item for item in self.catalog.protocol_profiles}
        codecs = {item.key: item for item in self.catalog.value_codecs}
        profile = profiles["effect_parameter_response_1c_v1"].document
        codec = codecs["upper_float32_nibbles_v1"].document

        self.assertEqual(profile["command"], 0x1C)
        self.assertEqual(profile["message_length"], 70)
        self.assertEqual(profile["fields"]["internal_slot"]["indices"], [39, 40])
        self.assertEqual(profile["fields"]["parameter_selector"]["index"], 48)
        self.assertEqual(profile["fields"]["parameter_address"]["indices"], [21, 22])
        self.assertNotIn("model_id", profile["fields"])
        self.assertEqual(profile["fields"]["value"]["start_index"], 59)
        self.assertEqual(profile["fields"]["value"]["end_index_exclusive"], 63)
        self.assertEqual(codec["encoded_length"], 4)
        self.assertEqual(codec["configuration"]["lower_bytes"], [0, 0])

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
            exported_mboost = exported.effect_by_key("dyn.m_boost")
            exported_comp1 = exported.effect_by_key("dyn.comp1")
            exported_e_boost = exported.effect_by_key("dyn.e_boost")
            exported_ac_woody = exported.effect_by_key("dyn.ac_woody")
            exported_gate1 = exported.effect_by_key("dyn.gate_1")
            self.assertEqual(
                exported_mboost.parameters,
                self.catalog.effect_by_key("dyn.m_boost").parameters,
            )
            self.assertEqual(
                exported_comp1.parameters,
                self.catalog.effect_by_key("dyn.comp1").parameters,
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
