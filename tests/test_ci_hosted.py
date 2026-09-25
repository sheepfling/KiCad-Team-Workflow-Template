"""Behavioral checks for reusable hosted planning, shards and retained failures."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from tests.support import initialize_git, reference_root
from tools.ci_hosted import (
    HostedLog,
    gate_result,
    matrix_lane,
    plan_lane,
    plan_scope,
    portable_lane,
)
from tools.hwrepo.sharding import ProjectShard, shard_projects


class HostedCiTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="hosted-ci-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "repository"
        shutil.copytree(reference_root(), self.root,
                        ignore=shutil.ignore_patterns(".git", "build", "__pycache__"))

    def test_shards_partition_a_tag_and_never_claim_full_acceptance(self) -> None:
        projects = ("z", "a", "c", "b", "d", "e")
        shards = [shard_projects(projects, f"{index}/3") for index in (1, 2, 3)]
        self.assertEqual(tuple(sorted(project for shard in shards for project in shard)),
                         tuple(sorted(projects)))
        self.assertTrue(all(len(shard) == 2 for shard in shards))
        plan = plan_scope(self.root, event="local", base=None, focus="tag",
                          value="training", exclude_tag=None, shard="1/2")
        self.assertEqual(plan.scope, "focused")
        self.assertEqual(len(plan.projects), 3)
        self.assertIn("Partial project shard 1/2", plan.reasons)
        full_shard = plan_scope(self.root, event="local", base=None, focus="full",
                                value=None, exclude_tag=None, shard="1/2")
        self.assertEqual(full_shard.scope, "focused")
        self.assertEqual(len(full_shard.projects), 3)

    def test_bad_or_empty_shards_fail_before_checks(self) -> None:
        for value in ("0/2", "1/0", "3/2", "1:2", "", "2/3"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                ProjectShard.parse(value).select(("controller",))
        with self.assertRaisesRegex(ValueError, "base branch"):
            plan_scope(self.root, event="local", base=None, focus="branch",
                       value=None, exclude_tag=None, shard=None)

    def test_branch_focus_uses_the_same_git_impact_scope(self) -> None:
        initialize_git(self.root)
        def git(*args: str) -> str:
            return subprocess.run(("git", "-C", str(self.root), *args), check=True,
                                  capture_output=True, text=True).stdout.strip()
        git("-c", "user.name=Test fixture", "-c", "user.email=fixture@example.invalid",
            "commit", "-qm", "Initial source")
        base = git("rev-parse", "HEAD")
        board = self.root / "examples/projects/controller/kicad/controller.kicad_pcb"
        board.write_bytes(board.read_bytes() + b"\n")
        git("add", "--all")
        git("-c", "user.name=Test fixture", "-c", "user.email=fixture@example.invalid",
            "commit", "-qm", "Board change")
        plan = plan_scope(self.root, event="local", base=None, focus="branch",
                          value=base, exclude_tag=None, shard=None)
        self.assertEqual(plan.scope, "focused")
        self.assertEqual(plan.projects, ("controller",))
        pr_plan = plan_scope(self.root, event="pull_request", base=base, focus="full",
                             value=None, exclude_tag=None, shard=None)
        self.assertEqual(pr_plan, plan)
        pr_shard = plan_scope(self.root, event="pull_request", base=base, focus="full",
                              value=None, exclude_tag=None, shard="1/1")
        self.assertEqual(pr_shard.projects, plan.projects)
        self.assertIn("Partial project shard 1/1", pr_shard.reasons)

    def test_hosted_plan_and_native_matrix_outputs_agree_on_the_shard(self) -> None:
        destination = self.root / "github-output.txt"
        destination.write_text("", encoding="utf-8")
        args = argparse.Namespace(
            event="local", base="", focus="tag", value="training",
            exclude_tag="", shard="2/2", head="HEAD",
        )
        with patch.dict(os.environ, {"GITHUB_OUTPUT": str(destination)}):
            plan_lane(self.root, args, HostedLog(self.root, "plan"))
            plan = json.loads((self.root / "build/impact.json").read_text())
            matrix_lane(self.root, tuple(plan["projects"]), HostedLog(self.root, "matrix"))
        outputs = dict(line.split("=", 1) for line in destination.read_text().splitlines())
        selected = set(plan["projects"])
        self.assertEqual(outputs["scope"], "focused")
        self.assertEqual(set(outputs["projects"].split()), selected)
        self.assertEqual(json.loads(outputs["portable-matrix"])["os"], ["ubuntu-24.04"])
        self.assertEqual(outputs["has-projects"], "true")
        self.assertEqual(
            {entry["project"] for entry in json.loads(outputs["matrix"])["include"]},
            selected,
        )

    def test_focused_portable_lane_keeps_command_and_phase_logs(self) -> None:
        initialize_git(self.root)
        subprocess.run(("git", "-C", str(self.root), "-c", "user.name=Test fixture",
                        "-c", "user.email=fixture@example.invalid", "commit", "-qm",
                        "Synthetic source"), check=True, capture_output=True)
        log = HostedLog(self.root, "portable")
        portable_lane(self.root, "focused", ("controller",), False, 2, log)
        log.finish()
        report = json.loads((self.root / "build/portable/portable.json").read_text())
        self.assertEqual(report["projects"], ["controller"])
        self.assertEqual(report["status"], "PASS")
        events = [json.loads(line) for line in log.events.read_text().splitlines()]
        self.assertTrue(any(item["stage"] == "portable-focused" and item["status"] == "PASS"
                            for item in events))
        self.assertTrue((log.directory / "portable-focused.stderr.log").is_file())

    def test_failed_command_retains_stdout_stderr_and_exit_code(self) -> None:
        log = HostedLog(self.root, "failure-probe")
        with redirect_stderr(StringIO()) as live, self.assertRaisesRegex(RuntimeError, "failed \\(7\\)"):
            log.run("probe", (sys.executable, "-c",
                              'import sys; print("out"); print("err", file=sys.stderr); sys.exit(7)'),
                    cwd=self.root)
        self.assertIn("out", (log.directory / "probe.stdout.log").read_text())
        self.assertIn("err", (log.directory / "probe.stderr.log").read_text())
        self.assertIn("out", live.getvalue())
        self.assertIn('"exit_code": 7', log.events.read_text())

    def test_final_gate_requires_rehearsal_only_for_complete_live_scope(self) -> None:
        gate_result("success", "focused", "success", "success", "success", "true", "skipped")
        gate_result("success", "full", "success", "success", "success", "true", "success")
        with self.assertRaises(ValueError):
            gate_result("success", "full", "success", "success", "success", "true", "skipped")
        with self.assertRaises(ValueError):
            gate_result("success", "focused", "success", "success", "skipped", "true", "skipped")


if __name__ == "__main__":
    unittest.main()
