"""Unit tests for the single CI entry point that GitHub invokes."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
import unittest
from datetime import UTC, datetime
from io import StringIO
from unittest.mock import patch

from tests.support import reference_root
from tools.ci import main, project_static_pipeline, run_command, static_pipeline
from tools.hwrepo.models import CommandEvidence

ROOT = reference_root()


def evidence(returncode: int) -> CommandEvidence:
    return CommandEvidence(
        argv=("quality-tool",),
        started_utc=datetime.now(UTC).isoformat(),
        returncode=returncode,
    )


class CiDriverTests(unittest.TestCase):
    def test_missing_quality_tool_is_a_typed_failure(self) -> None:
        result = run_command(ROOT, "intentionally-absent-quality-tool")
        self.assertEqual(result.returncode, 127)
        self.assertIsNotNone(result.error)

    def test_static_pipeline_requires_every_quality_command(self) -> None:
        with patch("tools.ci.run_command", side_effect=(evidence(0), evidence(0), evidence(1))):
            result = static_pipeline(ROOT, None)
        self.assertEqual(result.registry.status, "PASS")
        self.assertEqual(result.documentation.status, "PASS")
        self.assertEqual(result.unit_tests.returncode, 1)
        self.assertEqual(result.status, "FAIL")

    def test_project_pipeline_skips_repository_wide_python_quality_commands(self) -> None:
        with patch("tools.ci.run_command") as command:
            result = project_static_pipeline(ROOT, ("controller",))
        command.assert_not_called()
        self.assertEqual(result.scope, "project_static")
        self.assertEqual(result.projects, ("controller",))
        self.assertEqual(result.status, "PASS")

    def test_module_entrypoint_scopes_a_local_project_check(self) -> None:
        result = subprocess.run(
            [sys.executable, "-B", "-m", "tools.ci", "--project", "controller"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["scope"], "project_static")
        self.assertNotIn("ruff", report)

    def test_module_entrypoint_selects_projects_by_metadata_tag(self) -> None:
        result = subprocess.run(
            [sys.executable, "-B", "-m", "tools.ci", "--tag", "status-led"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(
            report["projects"],
            ['arduino-uno-status-led', 'raspberry-pi-status-led', 'status-indicator-harness-interface', 'status-indicator-wiring'],
        )

    def test_matrix_mode_is_one_json_line_for_github_output(self) -> None:
        with (
            patch.object(sys, "argv", ["ci.py", "--matrix"]),
            patch("sys.stdout", new_callable=StringIO) as output,
        ):
            self.assertEqual(main(), 0)
        self.assertEqual(len(output.getvalue().splitlines()), 1)

    def test_module_entrypoint_resolves_the_package_without_path_injection(self) -> None:
        result = subprocess.run(
            [sys.executable, "-B", "-m", "tools.ci", "--matrix"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("include", json.loads(result.stdout))

    def test_metrics_mode_uses_the_central_ci_driver(self) -> None:
        with (
            patch.object(sys, "argv", ["ci.py", "--metrics"]),
            patch("sys.stdout", new_callable=StringIO) as output,
        ):
            self.assertEqual(main(), 0)
        self.assertEqual(json.loads(output.getvalue())["lane"], "TEMPLATE_METRICS")

    def test_native_workflow_passes_the_selected_project_and_uses_declared_dependencies(self) -> None:
        workflow = (ROOT / ".github/workflows/kicad-template.yml").read_text(encoding="utf-8")
        native = workflow.split("- name: Check declared KiCad project", 1)[1].split("- name:", 1)[0]
        self.assertIn("-e PROJECT_ID", native)
        self.assertIn('--project "$PROJECT_ID"', native)
        self.assertIn("-e PYTHONPATH=/work/build/policy-deps", native)
        self.assertNotIn("pip install", native)
        self.assertIn('tools.native_deps --image "$KICAD_IMAGE"', workflow)
        self.assertNotIn("pydantic==", workflow)
        self.assertNotIn("ruff==", workflow)
        self.assertIn("needs: [project-matrix, python-tests, kicad, release-rehearsal]", workflow)

    def test_hosted_native_and_release_work_do_not_wait_for_windows(self) -> None:
        workflow = (ROOT / ".github/workflows/kicad-template.yml").read_text(encoding="utf-8")
        native = workflow.split("  kicad:\n", 1)[1].split("  release-rehearsal:\n", 1)[0]
        release = workflow.split("  release-rehearsal:\n", 1)[1].split("  engineering-gate:\n", 1)[0]
        self.assertIn("needs: [project-matrix]", native)
        self.assertIn("needs: [kicad]", release)
        self.assertNotIn("python-tests", native)
        self.assertNotIn("python-tests", release)

    def test_workflow_delegates_policy_work_to_the_driver(self) -> None:
        workflow = (ROOT / ".github/workflows/kicad-template.yml").read_text(
            encoding="utf-8"
        )
        self.assertNotRegex(
            workflow,
            r"\bpython(?:3)?\s+(?!-m\b)[^\n]*tools[/\\][^\n]*\.py",
        )
        for command in ("tools/ci_matrix.py", "tools/check_all.py", "tools/fault_probe.py"):
            self.assertNotIn(command, workflow)
        self.assertNotIn("tools/ci.py", workflow)
        for mode in ("tools.ci --matrix", "tools.ci --kicad", "tools.ci --fault-probes"):
            self.assertIn(mode, workflow)

    def test_dependency_updates_are_bounded_and_cover_python_and_actions(self) -> None:
        policy = (ROOT / ".github/dependabot.yml").read_text(encoding="utf-8")
        self.assertIn("package-ecosystem: pip", policy)
        self.assertIn("package-ecosystem: github-actions", policy)
        self.assertEqual(policy.count("interval: monthly"), 2)
        self.assertEqual(policy.count("open-pull-requests-limit: 3"), 2)

    @unittest.skipIf(os.name == "nt", "The hosted acceptance gate runs in Ubuntu Bash")
    def test_final_hosted_gate_rejects_incomplete_results(self) -> None:
        workflow = (ROOT / ".github/workflows/kicad-template.yml").read_text(
            encoding="utf-8"
        )
        gate = workflow.split("  engineering-gate:\n", 1)[1]
        script = textwrap.dedent(gate.split("        run: |\n", 1)[1])
        populated = {
            "UNIT_RESULT": "success", "MATRIX_RESULT": "success",
            "KICAD_RESULT": "success", "RELEASE_RESULT": "success",
            "HAS_PROJECTS": "true",
        }
        empty = {**populated, "HAS_PROJECTS": "false", "KICAD_RESULT": "skipped",
                 "RELEASE_RESULT": "skipped"}
        for baseline in (populated, empty):
            cases = [(baseline, True)]
            for field in baseline:
                values = (("", "unknown") if field == "HAS_PROJECTS" else
                          ("success", "failure", "skipped", "cancelled", ""))
                cases.extend(({**baseline, field: value}, False)
                             for value in values if value != baseline[field])
            for results, expected in cases:
                with self.subTest(results=results):
                    result = subprocess.run(
                        ["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", script],
                        env={**os.environ, **results}, capture_output=True, text=True,
                        check=False,
                    )
                    self.assertEqual(result.returncode == 0, expected, result.stderr)


if __name__ == "__main__":
    unittest.main()
