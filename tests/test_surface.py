"""Public declaration coverage must not silently drift between CLI and MCP."""
from __future__ import annotations

import builtins
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError

from tests.support import SOURCE_ROOT, reference_root
from tools.hwrepo.contracts import parse_model_text, read_model, write_model
from tools.hwrepo.models import (
    ToolMcpSnapshot,
    ToolSurfaceReport,
    ToolSurfacesCatalog,
)
from tools.hwrepo.surface import (
    CATALOG,
    discover_mcp,
    inspect_tool_surfaces,
)


class ToolSurfaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="kicad-surfaces-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        shutil.copytree(SOURCE_ROOT / "tools", self.root / "tools",
                        ignore=shutil.ignore_patterns("__pycache__"))
        (self.root / "catalog").mkdir()
        shutil.copy2(SOURCE_ROOT / CATALOG, self.root / CATALOG)

    def report(self) -> ToolSurfaceReport:
        with patch("tools.hwrepo.surface.find_spec", return_value=None):
            return inspect_tool_surfaces(self.root)

    def messages(self, report: ToolSurfaceReport, code: str) -> str:
        return "\n".join(issue.message for issue in report.issues if issue.code == code)

    def replace_source(self, path: str, old: str, new: str) -> None:
        source = self.root / path
        text = source.read_text(encoding="utf-8")
        self.assertIn(old, text)
        source.write_text(text.replace(old, new, 1), encoding="utf-8")

    def test_real_checkout_and_full_registration_are_tracked(self) -> None:
        report = inspect_tool_surfaces(SOURCE_ROOT, require_live_mcp=True)
        self.assertEqual(report.status, "PASS", report.model_dump_json(indent=2))
        self.assertEqual(report.mcp_verification, "LIVE")
        self.assertFalse(report.build_authorized)
        self.assertEqual({item.alignment for item in report.capabilities},
                         {"aligned", "partial", "cli_only", "mcp_only"})
        self.assertTrue({"prepare_parts", "save_parts_preferences", "inspect_tool_surfaces"}
                        <= {tool.name for tool in report.mcp})
        self.assertEqual(parse_model_text(report.model_dump_json(), ToolSurfaceReport), report)

    def test_shared_reference_fixture_retains_the_policy_catalog(self) -> None:
        root = reference_root()
        self.assertEqual(read_model(root / CATALOG, ToolSurfacesCatalog),
                         read_model(SOURCE_ROOT / CATALOG, ToolSurfacesCatalog))

    def test_base_runtime_never_imports_optional_mcp(self) -> None:
        original = builtins.__import__

        def deny_mcp(name, *args, **kwargs):
            if name == "mcp" or name.startswith("mcp."):
                raise AssertionError("Static coverage must not import the optional SDK")
            return original(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=deny_mcp):
            report = self.report()
        self.assertEqual(report.status, "PASS", report.issues)
        self.assertEqual(report.mcp_verification, "STATIC_ONLY")
        with patch("tools.hwrepo.surface.find_spec", return_value=None):
            required = inspect_tool_surfaces(self.root, require_live_mcp=True)
        self.assertEqual(required.status, "FAIL")
        self.assertEqual(required.mcp_verification, "UNAVAILABLE")
        self.assertIn("pinned dev or mcp extra", self.messages(required, "live_mcp_unavailable"))

    def test_new_cli_module_requires_snapshot_and_classification(self) -> None:
        (self.root / "tools/future.py").write_text(
            'def main():\n    return 0\n', encoding="utf-8",
        )
        report = self.report()
        self.assertEqual(report.status, "FAIL")
        self.assertIn("tools.future", self.messages(report, "untracked_surface"))
        self.assertIn("tools.future", self.messages(report, "unmapped_surface"))

    def test_new_subcommand_is_detected_on_an_existing_cli(self) -> None:
        self.replace_source("tools/hardware.py", '"verify-snapshot"))',
                            '"verify-snapshot", "publish"))')
        report = self.report()
        self.assertEqual(report.status, "FAIL")
        self.assertIn("publish", self.messages(report, "cli_signature_drift"))
        self.assertIn("tools.hardware publish", self.messages(report, "unmapped_surface"))

    def test_subparser_aliases_are_discovered(self) -> None:
        (self.root / "tools/future.py").write_text(
            'import argparse\ndef main():\n'
            '    parser = argparse.ArgumentParser()\n'
            '    commands = parser.add_subparsers()\n'
            '    command = commands.add_parser("export", aliases=("save",))\n'
            '    command.add_argument("--strict")\n', encoding="utf-8",
        )
        report = self.report()
        future = next(item for item in report.cli if item.module == "tools.future")
        self.assertEqual(future.commands, ("export", "save"))
        self.assertEqual(future.options, ("--strict",))
        self.assertIn("tools.future save", self.messages(report, "unmapped_surface"))

    def test_changed_cli_option_records_added_and_removed_names(self) -> None:
        self.replace_source("tools/verify.py", '"--detail"', '"--verbosity"')
        report = self.report()
        self.assertEqual(report.status, "FAIL")
        message = self.messages(report, "cli_signature_drift")
        self.assertIn("added ['--verbosity']", message)
        self.assertIn("removed ['--detail']", message)

    def test_new_mcp_tool_requires_snapshot_and_classification(self) -> None:
        self.replace_source(
            "tools/hwrepo/mcp_server.py", "    return server\n",
            '    def future_tool(project_id: str) -> str:\n'
            '        return project_id\n'
            '    server.tool()(future_tool)\n'
            '    return server\n',
        )
        report = self.report()
        self.assertEqual(report.status, "FAIL")
        self.assertIn("future_tool", self.messages(report, "untracked_surface"))
        self.assertIn("future_tool", self.messages(report, "unmapped_surface"))

    def test_mcp_parameter_and_removal_drift_are_detected(self) -> None:
        self.replace_source("tools/hwrepo/mcp_server.py", "def list_projects()",
                            "def list_projects(limit: int = 10)")
        self.replace_source("tools/hwrepo/mcp_server.py",
                            "    server.tool(annotations=READ_ONLY)(get_project)\n", "")
        report = self.report()
        self.assertEqual(report.status, "FAIL")
        self.assertIn("limit", self.messages(report, "mcp_signature_drift"))
        self.assertIn("get_project", self.messages(report, "stale_surface"))
        self.assertIn("get_project", self.messages(report, "stale_mapping"))

    def test_live_registration_disagreement_is_not_hidden_by_static_catalog(self) -> None:
        async def changed_registration(root: Path) -> tuple[ToolMcpSnapshot, ...]:
            return (*discover_mcp(root), ToolMcpSnapshot(name="runtime_only_tool"))

        with patch("tools.hwrepo.surface._live_mcp", side_effect=changed_registration):
            report = inspect_tool_surfaces(self.root, require_live_mcp=True)
        self.assertEqual(report.status, "FAIL")
        self.assertEqual(report.mcp_verification, "LIVE")
        self.assertIn("runtime_only_tool", self.messages(report, "mcp_registration_drift"))

    def test_unsupported_dynamic_declarations_fail_instead_of_disappearing(self) -> None:
        self.replace_source("tools/hardware.py",
                            '("check", "generate", "snapshot", "verify-snapshot")',
                            "commands_from_configuration")
        report = self.report()
        self.assertEqual(report.status, "FAIL")
        self.assertIn("literal strings", self.messages(report, "surface_discovery"))
        shutil.copy2(SOURCE_ROOT / "tools/hardware.py", self.root / "tools/hardware.py")
        self.replace_source("tools/hwrepo/mcp_server.py",
                            "server.tool(annotations=READ_ONLY)(get_project)",
                            "server.tool(annotations=READ_ONLY)(tool_from_configuration())")
        report = self.report()
        self.assertEqual(report.status, "FAIL")
        self.assertIn("unsupported MCP", self.messages(report, "surface_discovery"))

    def test_catalog_requires_complete_and_honest_classifications(self) -> None:
        catalog = read_model(self.root / CATALOG, ToolSurfacesCatalog)
        mappings = tuple(
            item.model_copy(update={"gaps": ()}) if item.id == "parts-preparation" else item
            for item in catalog.capabilities if item.id != "project-verification"
        )
        write_model(self.root / CATALOG, catalog.model_copy(update={"capabilities": mappings}))
        report = self.report()
        self.assertEqual(report.status, "FAIL")
        self.assertIn("parts-preparation", self.messages(report, "invalid_alignment"))
        self.assertIn("check_project", self.messages(report, "unmapped_surface"))

    def test_malformed_catalog_is_a_typed_failure(self) -> None:
        (self.root / CATALOG).write_text('{"schema_version":"future"}', encoding="utf-8")
        report = self.report()
        self.assertEqual(report.status, "FAIL")
        self.assertTrue(self.messages(report, "surface_discovery"))
        self.assertEqual(report.capabilities, ())

    def test_serialized_catalog_and_report_reject_unknown_fields_and_wrong_types(self) -> None:
        report = self.report()
        with self.assertRaises(ValidationError):
            parse_model_text(report.model_dump_json().replace('"build_authorized":false',
                                                              '"build_authorized":true'),
                             ToolSurfaceReport)
        catalog = read_model(self.root / CATALOG, ToolSurfacesCatalog)
        with self.assertRaises(ValidationError):
            parse_model_text(catalog.model_dump_json().replace('"schema_version":"1"',
                                                               '"schema_version":1'),
                             ToolSurfacesCatalog)
        with self.assertRaises(ValidationError):
            parse_model_text(catalog.model_dump_json()[:-1] + ',"unknown":true}',
                             ToolSurfacesCatalog)

    def test_cli_uses_explicit_root_from_an_unrelated_directory(self) -> None:
        result = subprocess.run(
            (sys.executable, "-B", "-m", "tools.surface", "--root", str(SOURCE_ROOT),
             "--format", "json", "--require-live-mcp"),
            cwd=self.root, env={**os.environ, "PYTHONPATH": str(SOURCE_ROOT)},
            text=True, capture_output=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = parse_model_text(result.stdout, ToolSurfaceReport)
        self.assertEqual(report.status, "PASS")
        self.assertEqual(report.mcp_verification, "LIVE")


if __name__ == "__main__":
    unittest.main()
