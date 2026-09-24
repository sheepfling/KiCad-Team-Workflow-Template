"""Unit tests for the single CI entry point that GitHub invokes."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from tests.support import reference_root
from tools.ci import main, project_static_pipeline, run_command, static_pipeline
from tools.hwrepo.models import CommandEvidence, StaticPipelineReport

ROOT = reference_root()


def evidence(returncode: int) -> CommandEvidence:
    return CommandEvidence(
        argv=("quality-tool",),
        started_utc=datetime.now(UTC).isoformat(),
        returncode=returncode,
    )


class CiDriverTests(unittest.TestCase):
    def test_manual_focus_cannot_cancel_main_or_another_manual_run(self) -> None:
        workflow = (ROOT / ".github/workflows/kicad-template.yml").read_text(encoding="utf-8")
        self.assertIn(
            "group: kicad-template-${{ github.event_name }}-${{ github.event_name == 'workflow_dispatch' && github.run_id || github.ref }}",
            workflow,
        )

    def test_missing_quality_tool_is_a_typed_failure(self) -> None:
        result = run_command(ROOT, "intentionally-absent-quality-tool")
        self.assertEqual(result.returncode, 127)
        self.assertIsNotNone(result.error)

    def test_static_pipeline_requires_every_quality_command(self) -> None:
        with patch("tools.ci.run_command", side_effect=(evidence(0), evidence(0), evidence(1))):
            result = static_pipeline(ROOT, None)
        if not isinstance(result, StaticPipelineReport):
            self.fail("The unselected CI lane must return the full static report")
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

    def test_selected_project_can_print_a_short_human_summary(self) -> None:
        result = subprocess.run(
            [sys.executable, "-B", "-m", "tools.ci", "--project", "controller",
             "--format", "text"],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Portable check: PASS", result.stdout)
        self.assertIn("Projects: controller", result.stdout)
        self.assertIn("registry: PASS", result.stdout)

    def test_failed_project_text_points_to_the_diagnostic_command(self) -> None:
        with (
            patch.object(sys, "argv", [
                "ci.py", "--root", str(ROOT), "--project", "controller",
                "--format", "text",
            ]),
            patch("tools.ci.check_generation", return_value=("Outdated BOM view",)),
            patch("sys.stdout", new_callable=StringIO) as output,
        ):
            self.assertEqual(main(), 1)
        self.assertIn("generation: FAIL", output.getvalue())
        self.assertIn("Outdated BOM view", output.getvalue())
        self.assertIn(
            "python -B -m tools.template diagnose --project-id controller",
            output.getvalue(),
        )

    def test_portable_journal_retains_completed_phases_after_crash(self) -> None:
        with tempfile.TemporaryDirectory(prefix="portable-journal-") as temporary:
            output = Path(temporary) / "run"
            with (
                patch.object(sys, "argv", ["ci.py", "--root", str(ROOT), "--project", "controller",
                                         "--output", str(output)]),
                patch("tools.ci.check_repository", side_effect=RuntimeError("unexpected failure")),
                patch("sys.stdout", new_callable=StringIO),
                patch("sys.stderr", new_callable=StringIO),
                self.assertRaisesRegex(RuntimeError, "unexpected failure"),
            ):
                main()
            self.assertEqual(json.loads((output / "run.json").read_text())["status"], "ERROR")
            self.assertTrue((output / "registry.json").is_file())
            self.assertFalse((output / "portable.json").exists())
            events = [json.loads(line) for line in (output / "events.jsonl").read_text().splitlines()]
            self.assertTrue(any(event["stage"] == "repository" and event["status"] == "ERROR"
                                for event in events))

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

    def test_module_entrypoint_selects_an_indexed_product(self) -> None:
        result = subprocess.run(
            [sys.executable, "-B", "-m", "tools.ci", "--product", "status-indicator-system"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["scope"], "project_static")
        self.assertEqual(
            report["projects"],
            [
                "arduino-uno-status-led",
                "raspberry-pi-status-led",
                "status-indicator-harness-interface",
                "status-indicator-wiring",
            ],
        )

    def test_unknown_product_is_an_explicit_selection_error(self) -> None:
        result = subprocess.run(
            [sys.executable, "-B", "-m", "tools.ci", "--product", "unknown-product"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("unknown-product", result.stderr)

    def test_native_matrix_honors_product_and_excluded_tag(self) -> None:
        result = subprocess.run(
            [
                sys.executable, "-B", "-m", "tools.ci", "--matrix",
                "--product", "status-indicator-system", "--exclude-tag", "arduino",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            {entry["project"] for entry in json.loads(result.stdout)["include"]},
            {
                "raspberry-pi-status-led",
                "status-indicator-harness-interface",
                "status-indicator-wiring",
            },
        )

    def test_manual_impact_selectors_plan_only_requested_project_lanes(self) -> None:
        cases = (
            (("--select-project", "controller"), ["controller"]),
            (("--select-product", "status-indicator-system"), [
                "arduino-uno-status-led",
                "raspberry-pi-status-led",
                "status-indicator-harness-interface",
                "status-indicator-wiring",
            ]),
            (("--select-tag", "status-led", "--exclude-tag", "arduino"), [
                "raspberry-pi-status-led",
                "status-indicator-harness-interface",
                "status-indicator-wiring",
            ]),
        )
        for arguments, expected in cases:
            with self.subTest(arguments=arguments):
                result = subprocess.run(
                    [sys.executable, "-B", "-m", "tools.impact", *arguments],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                plan = json.loads(result.stdout)
                self.assertEqual(plan["scope"], "focused")
                self.assertEqual(plan["projects"], expected)
                self.assertEqual(plan["changed_paths"], [])

    def test_manual_impact_selection_rejects_missing_or_empty_scope(self) -> None:
        cases = (
            ("--select-project", "unknown-board"),
            ("--select-product", "unknown-product"),
            ("--select-tag", "unknown-tag"),
            ("--select-project", "controller", "--exclude-tag", "legacy"),
            ("--full", "--exclude-tag", "reference"),
        )
        for arguments in cases:
            with self.subTest(arguments=arguments):
                result = subprocess.run(
                    [sys.executable, "-B", "-m", "tools.impact", *arguments],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 2)
                self.assertTrue(result.stderr.strip())

    def test_matrix_mode_is_one_json_line_for_github_output(self) -> None:
        with (
            patch.object(sys, "argv", ["ci.py", "--matrix"]),
            patch("sys.stdout", new_callable=StringIO) as output,
        ):
            self.assertEqual(main(), 0)
        self.assertEqual(len(output.getvalue().splitlines()), 1)

    def test_metrics_text_reuses_the_read_only_summary(self) -> None:
        with (
            patch.object(sys, "argv", ["ci.py", "--root", str(ROOT), "--metrics", "--format", "text"]),
            patch("sys.stdout", new_callable=StringIO) as output,
        ):
            self.assertEqual(main(), 0)
        self.assertIn("Template metrics:", output.getvalue())
        self.assertIn("Build authorized: no", output.getvalue())

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
        self.assertIn("needs: [scope, project-matrix, python-tests, kicad, release-rehearsal]", workflow)

    def test_hosted_native_and_release_work_do_not_wait_for_windows(self) -> None:
        workflow = (ROOT / ".github/workflows/kicad-template.yml").read_text(encoding="utf-8")
        native = workflow.split("  kicad:\n", 1)[1].split("  release-rehearsal:\n", 1)[0]
        release = workflow.split("  release-rehearsal:\n", 1)[1].split("  engineering-gate:\n", 1)[0]
        self.assertIn("needs: [scope, project-matrix]", native)
        self.assertIn("needs: [scope, kicad]", release)
        self.assertNotIn("python-tests", native)
        self.assertNotIn("python-tests", release)

    def test_hosted_scope_runs_focused_prs_and_full_main_or_manual_checks(self) -> None:
        workflow = (ROOT / ".github/workflows/kicad-template.yml").read_text(encoding="utf-8")
        scope = workflow.split("  scope:\n", 1)[1].split("  project-matrix:\n", 1)[0]
        matrix = workflow.split("  project-matrix:\n", 1)[1].split("  python-tests:\n", 1)[0]
        portable = workflow.split("  python-tests:\n", 1)[1].split("  kicad:\n", 1)[0]
        release = workflow.split("  release-rehearsal:\n", 1)[1].split("  engineering-gate:\n", 1)[0]

        self.assertIn("fetch-depth: 0", scope)
        self.assertIn('if [ "$EVENT_NAME" = pull_request ]; then', scope)
        self.assertIn('tools.impact --base "$BASE_SHA" --head HEAD', scope)
        self.assertIn("tools.impact --full", scope)
        self.assertIn('["ubuntu-24.04", "windows-2022", "macos-14"]', scope)
        self.assertIn('if plan["scope"] == "full" else ["ubuntu-24.04"]', scope)
        self.assertIn("needs.scope.outputs.scope != 'docs'", matrix)
        self.assertIn('args+=(--project "$project")', matrix)
        self.assertIn('tools.ci --matrix "${args[@]}"', matrix)
        self.assertIn('fromJSON(needs.scope.outputs.portable-matrix)', portable)
        self.assertIn('python -B -m tools.docs_policy', portable)
        self.assertIn('python -B -m tools.ci "${args[@]}" --jobs 4 --output build/portable', portable)
        self.assertIn('python -B -m tools.ci --jobs 4 --output build/portable', portable)
        self.assertIn('timeout-minutes: 13', portable)
        self.assertIn('cache-dependency-path: pyproject.toml', portable)
        self.assertIn('if [ "$DOCS_CHANGED" = true ]; then python -B -m tools.docs_policy; fi', portable)
        self.assertIn("if: needs.scope.outputs.scope == 'full'", portable)
        self.assertIn("if: needs.scope.outputs.scope == 'full' && needs.kicad.result == 'success'", release)

    def test_manual_dispatch_wires_typed_focus_inputs_into_the_planner(self) -> None:
        workflow = (ROOT / ".github/workflows/kicad-template.yml").read_text(encoding="utf-8")
        dispatch = workflow.split("  workflow_dispatch:\n", 1)[1].split("  push:\n", 1)[0]
        scope = workflow.split("  scope:\n", 1)[1].split("  project-matrix:\n", 1)[0]
        self.assertIn("options: [full, project, product, tag]", dispatch)
        for field in ("focus", "value", "exclude_tag"):
            self.assertIn(f"      {field}:\n", dispatch)
        self.assertIn("DISPATCH_FOCUS: ${{ inputs.focus || 'full' }}", scope)
        self.assertIn("DISPATCH_VALUE: ${{ inputs.value || '' }}", scope)
        self.assertIn("DISPATCH_EXCLUDE_TAG: ${{ inputs.exclude_tag || '' }}", scope)
        self.assertIn('test -n "$DISPATCH_VALUE"', scope)
        for selector in ("project", "product", "tag"):
            self.assertIn(
                f'tools.impact --select-{selector} "$DISPATCH_VALUE" "${{args[@]}}"',
                scope,
            )
        self.assertIn('args+=(--exclude-tag "$DISPATCH_EXCLUDE_TAG")', scope)

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
        common = {"SCOPE_RESULT": "success", "UNIT_RESULT": "success"}
        baselines = (
            {**common, "CHECK_SCOPE": "docs", "MATRIX_RESULT": "skipped",
             "KICAD_RESULT": "skipped", "RELEASE_RESULT": "skipped", "HAS_PROJECTS": ""},
            {**common, "CHECK_SCOPE": "focused", "MATRIX_RESULT": "success",
             "KICAD_RESULT": "success", "RELEASE_RESULT": "skipped", "HAS_PROJECTS": "true"},
            {**common, "CHECK_SCOPE": "full", "MATRIX_RESULT": "success",
             "KICAD_RESULT": "success", "RELEASE_RESULT": "success", "HAS_PROJECTS": "true"},
            {**common, "CHECK_SCOPE": "full", "MATRIX_RESULT": "success",
             "KICAD_RESULT": "skipped", "RELEASE_RESULT": "skipped", "HAS_PROJECTS": "false"},
        )
        for baseline in baselines:
            cases = [(baseline, True)]
            required = ("SCOPE_RESULT", "UNIT_RESULT", "CHECK_SCOPE", "MATRIX_RESULT",
                        "KICAD_RESULT", "RELEASE_RESULT")
            if baseline["CHECK_SCOPE"] != "docs":
                required += ("HAS_PROJECTS",)
            for field in required:
                values = (("", "unknown", "true", "false") if field == "HAS_PROJECTS" else
                          ("success", "failure", "skipped", "cancelled", "") if field != "CHECK_SCOPE" else
                          ("docs", "focused", "full", "unknown", ""))
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
