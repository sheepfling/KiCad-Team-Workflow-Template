"""New-engineer repair guidance against real importer and policy results."""
from __future__ import annotations

import csv
import hashlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.support import initialize_git, reference_root
from tools.hwrepo.contracts import read_model, write_model
from tools.hwrepo.diagnostics import (
    bom_binding_findings,
    bom_findings,
    diagnose_import,
    diagnose_project,
    native_findings,
)
from tools.hwrepo.discovery import load_config
from tools.hwrepo.models import (
    CheckEvidence,
    PcbValidationContract,
    ProjectManifest,
    ProjectTestContract,
    ValidationSummary,
)
from tools.validate import hashes


class DiagnosticTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="kicad-diagnostics-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def test_import_coaches_missing_sheet_without_copying_source(self) -> None:
        source = self.root / "legacy"
        source.mkdir()
        project = source / "legacy.kicad_pro"
        project.write_text("{}")
        (source / "legacy.kicad_sch").write_text('(property "Sheetfile" "missing.kicad_sch")')
        report = diagnose_import(reference_root(), project, "legacy-board", "kicad-10.0.5")
        self.assertEqual(report.status, "NEEDS_WORK")
        self.assertIn("Sheetfile", report.findings[0].action)
        self.assertFalse((reference_root() / "projects/legacy-board").exists())

        (source / "legacy.kicad_sch").write_text("(kicad_sch)")
        (source / "legacy.kicad_pcb").write_text("(kicad_pcb)")
        (source / "old.gbr").write_text("working export")
        fixed = diagnose_import(reference_root(), project, "legacy-board", "kicad-10.0.5")
        self.assertEqual(fixed.status, "PASS")
        self.assertEqual(fixed.findings[0].severity, "REVIEW")
        self.assertIn("generated export", fixed.findings[0].observed)
        self.assertFalse((reference_root() / "projects/legacy-board").exists())

    def test_real_portable_failure_names_dependency_and_repair(self) -> None:
        repository = self.root / "repository"
        shutil.copytree(reference_root(), repository, ignore=shutil.ignore_patterns(".git"))
        initialize_git(repository)
        board = repository / "examples/projects/controller/kicad/controller.kicad_pcb"
        board.write_text(board.read_text() + '\n(model "/Users/someone/Desktop/part.step")\n')
        result = diagnose_project(repository, "controller")
        paths = [row for row in result.findings if row.code == "CAD_PATH"]
        self.assertEqual(result.status, "NEEDS_WORK")
        self.assertEqual(len(paths), 1)
        self.assertIn("controller.kicad_pcb", paths[0].location)
        self.assertRegex(paths[0].location, r"controller\.kicad_pcb:\d+$")
        self.assertIn("declared shared library", paths[0].action)
        self.assertIn("machine-local dependency", paths[0].observed)

        manifest_path = repository / "examples/projects/controller/project.json"
        manifest = read_model(manifest_path, ProjectManifest)
        contract = read_model(manifest_path.parent / manifest.checks, ProjectTestContract)
        self.assertIsInstance(contract.validation, PcbValidationContract)
        alternate = "tests/review-expectations.json"
        write_model(manifest_path.parent / alternate, contract.model_copy(update={
            "validation": contract.validation.model_copy(update={"components": {}, "nets": {}})
        }))
        write_model(manifest_path, manifest.model_copy(update={"checks": alternate}))
        relocated = diagnose_project(repository, "controller")
        empty = next(row for row in relocated.findings if row.code == "EMPTY_COMPONENT_CONTRACT")
        self.assertEqual(empty.location, f"examples/projects/controller/{alternate}")
        self.assertIn(empty.location, empty.action)

    def test_native_disabled_checks_and_bom_identifiers_have_distinct_actions(self) -> None:
        native = self.root / "native"
        native.mkdir()
        write_model(native / "summary.json", ValidationSummary(
            timestamp_utc="2026-09-24T00:00:00+00:00",
            checked_commit="LOCAL_UNBOUND",
            project_id="controller",
            checks={
                "source_scope": CheckEvidence(status="PASS", source_hashes={"fake": "0" * 64}),
                "erc": CheckEvidence(
                    status="FAIL", returncode=5,
                    error="Disabled-check inventory changed: ('single_global_label',)",
                ),
            },
            status="FAIL",
            artifacts_sha256={},
        ))
        issues = native_findings(native, "controller")
        self.assertEqual(len(issues), 1)
        self.assertIn("Schematic Setup", issues[0].action)
        self.assertIn("Do not change", issues[0].action)
        current_source = native_findings(native, "controller", reference_root())
        self.assertEqual(current_source[0].code, "STALE_NATIVE_REPORT")
        wrong = native_findings(native, "some-other-board")
        self.assertEqual(wrong[0].code, "NATIVE_REPORT")

        bom = self.root / "bom.csv"
        with bom.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerow(("Reference", "Value", "Footprint", "PartID", "DNP"))
            writer.writerow(("R1", "1k", "R_Axial", "", ""))
            writer.writerow(("J1", "Header", "PinHeader", "not-in-catalog", ""))
            writer.writerow(("D1", "LED", "LED_THT", "training-generic-led-red-5mm", ""))
        items = bom_findings(reference_root(), bom)
        self.assertEqual([item.code for item in items], ["BOM_PART_ID", "BOM_TRAINING_PART"])
        self.assertIn("R1", items[0].observed)
        self.assertIn("schematic", items[0].action)
        self.assertIn("not-for-manufacture", items[1].observed)
        bom.write_text("Reference,Value,Footprint,PartID,DNP\nR2,1k\n")
        self.assertEqual(bom_findings(reference_root(), bom)[0].code, "BOM_INPUT")

    def test_bom_must_match_selected_project_native_netlist(self) -> None:
        native = self.root / "native"
        native.mkdir()
        netlist = native / "netlist.xml"
        netlist.write_text(
            '<export><components><comp ref="R1"><value>1k</value>'
            '<footprint>R_Axial</footprint></comp>'
            '<comp ref="R2"><value>2k</value><footprint>R_Axial</footprint></comp>'
            '<comp ref="LOGO1"><value>Logo</value><footprint>Graphic</footprint>'
            '<property name="exclude_from_bom"/></comp>'
            '<comp ref="D1"><value>LED</value><footprint>LED_THT</footprint>'
            '<property name="dnp"/></comp></components><nets/></export>'
        )
        config = load_config(reference_root(), "examples/projects/controller/project.json")
        write_model(native / "summary.json", ValidationSummary(
            timestamp_utc="2026-09-24T00:00:00+00:00",
            checked_commit="LOCAL_UNBOUND",
            project_id="controller",
            checks={"source_scope": CheckEvidence(
                status="PASS", source_hashes=hashes(reference_root(), config.source_roots)
            )},
            status="PASS",
            artifacts_sha256={"netlist.xml": hashlib.sha256(netlist.read_bytes()).hexdigest()},
        ))
        bom = self.root / "other-board-bom.csv"
        bom.write_text("Reference,Value,Footprint,PartID,DNP\nR1,1k,R_Axial,,\nR2,2k,R_Axial,,\n")
        self.assertEqual(bom_binding_findings(reference_root(), "controller", bom, native), [])
        bom.write_text("Reference,Value,Footprint,PartID,DNP\nR1,1k,R_Axial,,\n")
        incomplete = bom_binding_findings(reference_root(), "controller", bom, native)
        self.assertIn("R2", incomplete[0].observed)
        bom.write_text("Reference,Value,Footprint,PartID,DNP\nC1,100nF,C_0603,,\n")
        mismatch = bom_binding_findings(reference_root(), "controller", bom, native)
        self.assertEqual(mismatch[0].code, "BOM_BINDING")
        self.assertIn("C1", mismatch[0].observed)
        self.assertEqual(bom_binding_findings(reference_root(), "controller", bom, None)[0].code,
                         "BOM_BINDING")

    def test_cli_explains_import_in_text_and_json(self) -> None:
        source = self.root / "legacy"
        source.mkdir()
        project = source / "legacy.kicad_pro"
        project.write_text("{}")
        (source / "legacy.kicad_sch").write_text('(property "Sheetfile" "lost.kicad_sch")')
        command = (
            sys.executable, "-B", "-m", "tools.template", "diagnose",
            "--root", str(reference_root()), "--source", str(project),
            "--project-id", "legacy-board", "--toolchain", "kicad-10.0.5",
        )
        text_result = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(text_result.returncode, 1)
        self.assertIn("Fix: Find the intended sheet", text_result.stdout)
        json_result = subprocess.run((*command, "--format", "json"),
                                     capture_output=True, text=True, check=False)
        self.assertEqual(json_result.returncode, 1)
        self.assertIn('"code": "IMPORT"', json_result.stdout)
        unused_flag = subprocess.run((sys.executable, "-B", "-m", "tools.template", "doctor",
                                      "--format", "text"), capture_output=True,
                                     text=True, check=False)
        self.assertEqual(unused_flag.returncode, 2)
        self.assertIn("require diagnose", unused_flag.stderr)
        unbound_bom = subprocess.run((sys.executable, "-B", "-m", "tools.template", "diagnose",
                                      "--project-id", "controller", "--bom", str(self.root / "bom.csv")),
                                     capture_output=True, text=True, check=False)
        self.assertEqual(unbound_bom.returncode, 2)
        self.assertIn("requires --native-report", unbound_bom.stderr)


if __name__ == "__main__":
    unittest.main()
