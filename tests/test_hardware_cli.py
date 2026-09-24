"""Hardware CLI keeps stable JSON while offering a concise review-first terminal view."""
from __future__ import annotations

import json
import sys
import unittest
from io import StringIO
from unittest.mock import patch

from tools.hardware import main
from tools.hwrepo.models import (
    PolicyIssue,
    ProductPolicyReport,
    SnapshotManifest,
    SnapshotVerification,
)


class HardwareCliTests(unittest.TestCase):
    def test_check_default_json_stays_complete(self) -> None:
        report = ProductPolicyReport(
            status="PASS", products=("battery-system",),
            open_items={"battery-system": ("Review mating connector.",)}, issues=(),
        )
        expected = report.model_dump(mode="json")
        expected["generation_drift"] = ()
        for extra in ([], ["--format", "json"]):
            with (
                self.subTest(extra=extra),
                patch("tools.hardware.check", return_value=report),
                patch("tools.hardware.check_generation", return_value=()),
                patch.object(sys, "argv", ["tools.hardware", "check", *extra]),
                patch("sys.stdout", new_callable=StringIO) as output,
            ):
                self.assertEqual(main(), 0)
                self.assertEqual(output.getvalue(), json.dumps(expected, indent=2) + "\n")

    def test_check_text_names_policy_issue_review_item_and_next_action(self) -> None:
        report = ProductPolicyReport(
            status="FAIL", products=("battery-system",),
            open_items={"battery-system": ("Review mating connector.",)},
            issues=(PolicyIssue(
                code="MISSING_PART", location="catalog/parts.json",
                message="Part identity is absent",
            ),),
        )
        with (
            patch("tools.hardware.check", return_value=report),
            patch.object(sys, "argv", ["tools.hardware", "check", "--format", "text"]),
            patch("sys.stdout", new_callable=StringIO) as output,
        ):
            self.assertEqual(main(), 1)
        text = output.getvalue()
        self.assertIn("Hardware policy: FAIL", text)
        self.assertIn("battery-system: Review mating connector.", text)
        self.assertIn("MISSING_PART at catalog/parts.json: Part identity is absent", text)
        self.assertIn("Next: Repair the named policy issues", text)
        self.assertIn("--format json", text)

    def test_check_text_explains_generation_drift(self) -> None:
        report = ProductPolicyReport(status="PASS", products=(), open_items={}, issues=())
        with (
            patch("tools.hardware.check", return_value=report),
            patch("tools.hardware.check_generation", return_value=("STALE_OUTPUT: old.json",)),
            patch.object(sys, "argv", ["tools.hardware", "check", "--format", "text"]),
            patch("sys.stdout", new_callable=StringIO) as output,
        ):
            self.assertEqual(main(), 1)
        self.assertIn("generation drift: 1", output.getvalue())
        self.assertIn("STALE_OUTPUT: old.json", output.getvalue())
        self.assertIn("Next: Regenerate review views", output.getvalue())

    def test_generate_text_summarizes_files_and_error_action(self) -> None:
        with (
            patch("tools.hardware.generate", return_value=("generated/one.json", "schemas/two.json")),
            patch.object(sys, "argv", ["tools.hardware", "generate", "--format", "text"]),
            patch("sys.stdout", new_callable=StringIO) as output,
        ):
            self.assertEqual(main(), 0)
        self.assertIn("Hardware generation: PASS", output.getvalue())
        self.assertIn("Generated: 2 file(s)", output.getvalue())
        with (
            patch("tools.hardware.generate", side_effect=ValueError("missing source")),
            patch.object(sys, "argv", ["tools.hardware", "generate", "--format", "text"]),
            patch("sys.stdout", new_callable=StringIO) as output,
        ):
            self.assertEqual(main(), 1)
        self.assertIn("Error: missing source", output.getvalue())
        self.assertIn("Next: Repair the named input or tool error", output.getvalue())

    def test_snapshot_and_verification_text_state_review_scope(self) -> None:
        manifest = SnapshotManifest(
            commit="abc123", working_tree_clean=False, git_status="M README.md",
            python_version="3.11", policy_version="1.3.2", products=("battery-system",),
            checks={"product_policy": "PASS", "kicad": "NOT_RUN"},
            sources_sha256={}, artifacts_sha256={},
        )
        with (
            patch("tools.hardware.snapshot", return_value=manifest),
            patch.object(sys, "argv", ["tools.hardware", "snapshot", "--output", "build/review-1", "--format", "text"]),
            patch("sys.stdout", new_callable=StringIO) as output,
        ):
            self.assertEqual(main(), 0)
        text = output.getvalue()
        self.assertIn("Hardware snapshot: PASS", text)
        self.assertIn("Output: build/review-1", text)
        self.assertIn("Working tree clean: False", text)
        self.assertIn("kicad: NOT_RUN", text)
        self.assertIn("Build authorized: no", text)

        verification = SnapshotVerification(
            status="PASS", artifacts=2,
            scope="artifact_integrity_only_not_authenticity_or_source_reconstruction",
        )
        with (
            patch("tools.hardware.verify_snapshot", return_value=verification),
            patch.object(sys, "argv", ["tools.hardware", "verify-snapshot", "--output", "build/review-1", "--format", "text"]),
            patch("sys.stdout", new_callable=StringIO) as output,
        ):
            self.assertEqual(main(), 0)
        self.assertIn("Verified artifacts: 2", output.getvalue())
        self.assertIn("artifact integrity only", output.getvalue())


if __name__ == "__main__":
    unittest.main()
