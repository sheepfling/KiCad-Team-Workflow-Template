"""Fast diagnostics and one-command adoption behavior."""
from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tests.support import initialize_git, reference_root
from tools.hwrepo.adoption import adopt
from tools.hwrepo.contracts import write_model
from tools.hwrepo.doctor import doctor
from tools.hwrepo.models import TemplateAdoptionRecord


class AdoptionUsabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="kicad-adoption-usability-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "repository"
        shutil.copytree(reference_root(), self.root, ignore=shutil.ignore_patterns(".git"))
        initialize_git(self.root)

    @staticmethod
    def command_output(argv: tuple[str, ...]) -> str | None:
        if "--version" in argv:
            return "git version 2.51.0"
        if "rev-parse" in argv:
            return "true"
        if "version" in argv:
            return "27.5.1"
        return None

    def test_doctor_passes_portable_setup_without_optional_native_tools(self) -> None:
        def which(name: str) -> str | None:
            return "/usr/bin/git" if name == "git" else None

        with (
            patch("tools.hwrepo.doctor.sys.version_info", (3, 11, 1)),
            patch("tools.hwrepo.doctor.shutil.which", side_effect=which),
            patch("tools.hwrepo.doctor.command_output", side_effect=self.command_output),
        ):
            report = doctor(self.root)
        self.assertEqual(report.status, "PASS")
        self.assertEqual({row.id: row.status for row in report.checks}["docker"], "OPTIONAL")
        self.assertEqual(report.next_actions, ())

    def test_native_doctor_accepts_docker_or_exact_local_kicad(self) -> None:
        with (
            patch("tools.hwrepo.doctor.sys.version_info", (3, 11, 1)),
            patch("tools.hwrepo.doctor.shutil.which", return_value="/tool"),
            patch("tools.hwrepo.doctor.command_output", side_effect=self.command_output),
        ):
            docker_report = doctor(self.root, native=True, toolchain_id="kicad-10.0.5")
        self.assertEqual(docker_report.status, "PASS")

        def which(name: str) -> str | None:
            return "/usr/bin/git" if name == "git" else None

        with (
            patch("tools.hwrepo.doctor.sys.version_info", (3, 11, 1)),
            patch("tools.hwrepo.doctor.shutil.which", side_effect=which),
            patch("tools.hwrepo.doctor.command_output", side_effect=self.command_output),
            patch("tools.hwrepo.doctor.observed_version", return_value="10.0.5"),
        ):
            local_report = doctor(self.root, native=True, toolchain_id="kicad-10.0.5")
        self.assertEqual(local_report.status, "PASS")

    def test_native_doctor_fails_without_a_runner_and_python_minimum_is_enforced(self) -> None:
        with (
            patch("tools.hwrepo.doctor.sys.version_info", (3, 10, 9)),
            patch("tools.hwrepo.doctor.shutil.which", return_value=None),
        ):
            report = doctor(self.root, native=True)
        failures = {row.id for row in report.checks if row.status == "FAIL"}
        self.assertEqual(report.status, "FAIL")
        self.assertEqual(failures, {
            "python", "git", "git-repository", "native-target", "native-runner",
        })

    def test_native_doctor_rejects_a_toolchain_other_than_the_selected_project(self) -> None:
        with (
            patch("tools.hwrepo.doctor.sys.version_info", (3, 11, 1)),
            patch("tools.hwrepo.doctor.shutil.which", return_value="/tool"),
            patch("tools.hwrepo.doctor.command_output", side_effect=self.command_output),
            patch("tools.hwrepo.doctor.observed_version", return_value="10.0.0"),
        ):
            report = doctor(
                self.root, native=True, project_id="arduino-uno-status-led",
                toolchain_id="kicad-10.0.0",
            )
        self.assertEqual(report.status, "FAIL")
        failed = {check.id for check in report.checks if check.status == "FAIL"}
        self.assertIn("project", failed)
        self.assertIn("native-runner", failed)

    def test_adopt_initializes_once_and_runs_complete_portable_acceptance(self) -> None:
        with (
            patch("tools.hwrepo.doctor.sys.version_info", (3, 11, 1)),
            patch("tools.hwrepo.doctor.shutil.which", return_value="/usr/bin/git"),
            patch("tools.hwrepo.doctor.command_output", side_effect=self.command_output),
            patch("tools.ci.static_pipeline", return_value=SimpleNamespace(status="PASS")) as pipeline,
        ):
            report = adopt(self.root, "company-hardware")
        self.assertEqual(report.status, "PASS", report.issues)
        self.assertEqual(report.initialization, "PASS")
        self.assertEqual(report.portable, "PASS")
        self.assertIn("template-adoption.json", report.changed)
        pipeline.assert_called_once_with(self.root.resolve(), None)

    def test_adopt_stops_before_initialization_when_preflight_fails(self) -> None:
        (self.root / "tools/ci.py").unlink()
        with patch("tools.hwrepo.adoption.initialize") as initialize:
            report = adopt(self.root, "company-hardware")
        self.assertEqual(report.status, "FAIL")
        self.assertEqual(report.initialization, "NOT_RUN")
        initialize.assert_not_called()

    def test_adopt_directs_an_outdated_initialized_fork_to_upgrade_plan(self) -> None:
        write_model(
            self.root / "template-adoption.json",
            TemplateAdoptionRecord(
                template_version="1.0.0", project_id="company-hardware", status="initialized"
            ),
        )
        with (
            patch("tools.hwrepo.doctor.sys.version_info", (3, 11, 1)),
            patch("tools.hwrepo.doctor.shutil.which", return_value="/usr/bin/git"),
            patch("tools.hwrepo.doctor.command_output", side_effect=self.command_output),
        ):
            report = adopt(self.root, "company-hardware")
        self.assertEqual(report.status, "FAIL")
        self.assertEqual(report.initialization, "FAIL")
        self.assertIn("TEMPLATE_UPGRADE", report.issues[0])
        self.assertIn("upgrade-plan --target-version 1.3.2", report.next_actions[0])

    def test_adopt_reports_a_newer_record_without_recommending_a_downgrade(self) -> None:
        write_model(
            self.root / "template-adoption.json",
            TemplateAdoptionRecord(
                template_version="1.3.3", project_id="company-hardware", status="initialized"
            ),
        )
        with (
            patch("tools.hwrepo.doctor.sys.version_info", (3, 11, 1)),
            patch("tools.hwrepo.doctor.shutil.which", return_value="/usr/bin/git"),
            patch("tools.hwrepo.doctor.command_output", side_effect=self.command_output),
        ):
            report = adopt(self.root, "company-hardware")
        self.assertEqual(report.status, "FAIL")
        self.assertEqual(report.initialization, "FAIL")
        self.assertIn("TEMPLATE_VERSION_AHEAD", report.issues[0])
        self.assertIn("downgrades are not supported", report.next_actions[0])
        self.assertNotIn("upgrade-plan", report.next_actions[0])

    def test_doctor_trusts_the_inspected_worktree_for_git_status(self) -> None:
        with (
            patch("tools.hwrepo.doctor.sys.version_info", (3, 11, 1)),
            patch("tools.hwrepo.doctor.shutil.which", return_value="/usr/bin/git"),
            patch("tools.hwrepo.doctor.command_output", side_effect=self.command_output) as command,
        ):
            report = doctor(self.root)
        self.assertEqual(report.status, "PASS")
        probe = next(call.args[0] for call in command.call_args_list if "rev-parse" in call.args[0])
        self.assertIn(f"safe.directory={self.root.resolve().as_posix()}", probe)

    def test_doctor_reports_a_timed_out_kicad_probe_without_a_traceback(self) -> None:
        def which(name: str) -> str | None:
            return "/usr/bin/git" if name == "git" else None

        with (
            patch("tools.hwrepo.doctor.sys.version_info", (3, 11, 1)),
            patch("tools.hwrepo.doctor.shutil.which", side_effect=which),
            patch("tools.hwrepo.doctor.command_output", side_effect=self.command_output),
            patch(
                "tools.hwrepo.doctor.observed_version",
                side_effect=subprocess.TimeoutExpired("kicad-cli", 30),
            ),
        ):
            report = doctor(self.root, native=True, toolchain_id="kicad-10.0.5")
        self.assertEqual(report.status, "FAIL")
        failed = {check.id for check in report.checks if check.status == "FAIL"}
        self.assertIn("native-runner", failed)
        self.assertNotIn("toolchain", failed)


if __name__ == "__main__":
    unittest.main()
