"""Reviewed, explicit model assignment plans preserve board source and inventory."""
from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tests.support import reference_root
from tools.hwrepo.contracts import read_model
from tools.hwrepo.discovery import load_config
from tools.hwrepo.model_inventory import inspect_models
from tools.hwrepo.model_population import ModelMap, ModelPopulationReport, populate_models
from tools.hwrepo.models import ProjectManifest

PROJECT = "arduino-uno-status-led"
ISLAND = f"examples/projects/{PROJECT}"
BOARD = f"{ISLAND}/kicad/{PROJECT}.kicad_pcb"
MANIFEST = f"{ISLAND}/project.json"
MODEL = f"{ISLAND}/kicad/models/Header_1x02.step"


class ModelPopulationTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="model-population-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve() / "repo"
        shutil.copytree(reference_root(), self.root, ignore=shutil.ignore_patterns(".git"))
        self.board = self.root / BOARD
        self.manifest = self.root / MANIFEST
        self.model = self.root / MODEL
        self.model.parent.mkdir(parents=True)
        self.model.write_bytes(b"ISO-10303-21;\nEND-ISO-10303-21;\n")
        self.map = self.root / "build/model-map.json"
        self.map.parent.mkdir(exist_ok=True)
        self.write_map()

    def write_map(self, *, reference: str = "J1", model: str = MODEL,
                  digest: str | None = None) -> None:
        data = {
            "schema_version": "1", "project_id": PROJECT,
            "board_sha256": digest or hashlib.sha256(self.board.read_bytes()).hexdigest(),
            "assignments": [{"reference": reference, "model": model}],
        }
        self.map.write_text(json.dumps(data), encoding="utf-8")

    def test_plan_then_apply_changes_only_board_and_manifest(self) -> None:
        original_board = self.board.read_bytes()
        original_manifest = self.manifest.read_bytes()
        plan = populate_models(self.root, PROJECT, self.map)
        self.assertEqual(plan.status, "PLAN", plan.error)
        self.assertEqual(ModelPopulationReport.model_validate_json(plan.model_dump_json()), plan)
        self.assertIn("${KIPRJMOD}/models/Header_1x02.step", plan.board_diff)
        self.assertIn("kicad/models/Header_1x02.step", plan.manifest_diff)
        self.assertEqual(self.board.read_bytes(), original_board)
        self.assertEqual(self.manifest.read_bytes(), original_manifest)
        self.assertTrue((Path(plan.run_directory) / "board.diff").is_file())
        self.assertTrue((Path(plan.run_directory) / "manifest.diff").is_file())
        self.assertEqual(ModelMap.model_validate_json(self.map.read_text()).project_id, PROJECT)

        applied = populate_models(self.root, PROJECT, self.map, apply=True)
        self.assertEqual(applied.status, "APPLIED", applied.error)
        self.assertEqual(applied.board_diff, plan.board_diff)
        self.assertEqual(applied.manifest_diff, plan.manifest_diff)
        changed_board = self.board.read_bytes()
        self.assertEqual(changed_board, original_board.replace(
            b'(layers "*.Cu" "*.Mask") (net 3 "/GND")))',
            b'(layers "*.Cu" "*.Mask") (net 3 "/GND"))\n'
            b'    (model "${KIPRJMOD}/models/Header_1x02.step" '
            b'(offset (xyz 0 0 0)) (scale (xyz 1 1 1)) '
            b'(rotate (xyz 0 0 0)))\n  )',
            1,
        ))
        manifest = read_model(self.manifest, ProjectManifest)
        self.assertIn("kicad/models/Header_1x02.step", manifest.required_inputs)
        inventory = inspect_models(self.root, load_config(self.root, MANIFEST))
        self.assertEqual(inventory.footprints[0].status, "READY", inventory.findings)
        self.assertEqual(inventory.footprints[0].models[0].source_path, MODEL)

    def test_stale_hash_and_existing_model_fail_without_writes(self) -> None:
        old_digest = hashlib.sha256(self.board.read_bytes()).hexdigest()
        self.board.write_bytes(self.board.read_bytes() + b"\n")
        initial = self.board.read_bytes()
        stale = populate_models(self.root, PROJECT, self.map)
        self.assertEqual(stale.status, "FAIL")
        self.assertIn("Board changed", stale.error or "")
        self.assertEqual(self.board.read_bytes(), initial)
        self.write_map(digest=hashlib.sha256(self.board.read_bytes()).hexdigest())
        first = populate_models(self.root, PROJECT, self.map, apply=True)
        self.assertEqual(first.status, "APPLIED", first.error)
        self.write_map()
        repeated = populate_models(self.root, PROJECT, self.map, apply=True)
        self.assertEqual(repeated.status, "FAIL")
        self.assertIn("already has", repeated.error or "")
        self.assertNotEqual(old_digest, hashlib.sha256(self.board.read_bytes()).hexdigest())

    def test_rejects_ambiguous_or_unapproved_model_sources(self) -> None:
        self.write_map(reference="X404")
        missing_ref = populate_models(self.root, PROJECT, self.map)
        self.assertEqual(missing_ref.status, "FAIL")
        self.assertIn("No unique placed footprint", missing_ref.error or "")
        self.write_map(model=f"{ISLAND}/kicad/models/missing.step")
        missing_file = populate_models(self.root, PROJECT, self.map)
        self.assertEqual(missing_file.status, "FAIL")
        self.assertIn("missing", missing_file.error or "")
        idf = self.model.with_suffix(".idf")
        idf.write_bytes(b"IDF")
        self.write_map(model=idf.relative_to(self.root).as_posix())
        invalid = populate_models(self.root, PROJECT, self.map)
        self.assertEqual(invalid.status, "FAIL")
        self.assertIn("STEP/STP", invalid.error or "")
        outside = self.root / "unregistered.step"
        outside.write_bytes(b"STEP")
        self.write_map(model="unregistered.step")
        unregistered = populate_models(self.root, PROJECT, self.map)
        self.assertEqual(unregistered.status, "FAIL")
        self.assertIn("declared", unregistered.error or "")

    def test_shared_model_is_added_to_shared_inventory(self) -> None:
        shared = self.root / "examples/libraries/status-led/Header_1x02.step"
        shared.write_bytes(b"STEP")
        self.write_map(model=shared.relative_to(self.root).as_posix())
        result = populate_models(self.root, PROJECT, self.map, apply=True)
        self.assertEqual(result.status, "APPLIED", result.error)
        manifest = read_model(self.manifest, ProjectManifest)
        self.assertIn("examples/libraries/status-led/Header_1x02.step", manifest.shared_inputs)
        self.assertIn(
            '${KIPRJMOD}/../../../libraries/status-led/Header_1x02.step',
            self.board.read_text(encoding="utf-8"),
        )


if __name__ == "__main__":
    unittest.main()
