"""Human summaries and machine JSON remain distinct CLI contracts."""
from __future__ import annotations

import json
import sys
import unittest
from io import StringIO
from unittest.mock import patch

from tools.hwrepo.cli_output import summary
from tools.hwrepo.models import (
    CheckAllSummary,
    EnvironmentCheck,
    GovernanceLintReport,
    ProductPolicyReport,
    ProjectCheckSummary,
    RepositoryPolicyReport,
    TemplateDoctorReport,
)
from tools.template import main as template_main


class CliOutputTests(unittest.TestCase):
    def test_native_summary_shows_failing_project_and_receipt(self) -> None:
        report = CheckAllSummary(
            governance=GovernanceLintReport(projects=("controller",), issues=(), status="PASS"),
            repository=RepositoryPolicyReport(status="PASS", issues=()),
            product_policy=ProductPolicyReport(
                status="PASS", products=(), open_items={}, issues=(),
            ),
            projects=(ProjectCheckSummary(
                id="controller", status="FAIL", summary="controller/summary.json",
            ),),
            status="FAIL",
        )
        output = summary("Native KiCad check", report)
        self.assertIn("controller: FAIL (controller/summary.json)", output)
        self.assertNotIn("{'id':", output)

    def test_doctor_text_coaches_while_default_stdout_remains_json(self) -> None:
        report = TemplateDoctorReport(
            native_requested=False,
            checks=(EnvironmentCheck(
                id="git", required=True, status="FAIL", expected="Git on PATH",
                observed=None, next_action="Install Git and retry.",
            ),),
            status="FAIL", next_actions=("Repair Git before adoption.",),
        )
        with (
            patch("tools.template.doctor", return_value=report),
            patch.object(sys, "argv", ["tools.template", "doctor", "--format", "text"]),
            patch("sys.stdout", new_callable=StringIO) as output,
        ):
            self.assertEqual(template_main(), 1)
        self.assertIn("Template doctor: FAIL", output.getvalue())
        self.assertIn("git: FAIL", output.getvalue())
        self.assertIn("Next: Install Git and retry.", output.getvalue())
        with (
            patch("tools.template.doctor", return_value=report),
            patch.object(sys, "argv", ["tools.template", "doctor"]),
            patch("sys.stdout", new_callable=StringIO) as output,
        ):
            self.assertEqual(template_main(), 1)
        self.assertEqual(json.loads(output.getvalue())["checks"][0]["id"], "git")


if __name__ == "__main__":
    unittest.main()
