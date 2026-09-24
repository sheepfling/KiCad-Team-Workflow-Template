"""MCP protocol, checkout boundaries and explicit execution/write capabilities."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mcp import Client, StdioServerParameters
from mcp.types import CallToolResult, TextContent
from pydantic import ValidationError

from tests.support import SOURCE_ROOT, initialize_git, reference_root
from tools.hwrepo.contracts import read_model
from tools.hwrepo.mcp_server import create_server
from tools.hwrepo.models import (
    McpProjectReport,
    ProjectManifest,
    ProjectTestContract,
    ProjectVerificationReport,
    TemplateInventoryReport,
)

READ_TOOLS = {"list_projects", "get_project", "doctor", "read_document", "preview_import"}
DOCUMENTS = {
    "start-here": "START_HERE.md",
    "first-board": "FIRST_BOARD.md",
    "diagnostics": "DIAGNOSTICS.md",
    "import-workflow": "IMPORT_WORKFLOW.md",
    "contributor-guide": "CONTRIBUTOR_GUIDE.md",
    "checks-and-ci": "CHECKS_AND_CI.md",
    "mcp": "MCP.md",
}


def snapshot(root: Path) -> dict[str, str]:
    """Capture authored files and directory creation, excluding mutable Git state."""
    result: dict[str, str] = {}
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if ".git" in relative.parts or "__pycache__" in relative.parts:
            continue
        if path.is_symlink():
            result[relative.as_posix()] = f"link:{path.readlink()}"
        elif path.is_file():
            result[relative.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        else:
            result[relative.as_posix()] = "directory"
    return result


class McpTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="kicad-mcp-")
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name).resolve()
        self.root = self.base / "repository"
        shutil.copytree(
            reference_root(), self.root,
            ignore=shutil.ignore_patterns(".git", "build", "__pycache__"),
        )
        initialize_git(self.root)
        self.source = self.base / "Incoming board"
        self.source.mkdir()
        self.project = self.source / "Incoming board.kicad_pro"
        self.project.write_text("{}", encoding="utf-8")
        self.project.with_suffix(".kicad_sch").write_text("(kicad_sch)", encoding="utf-8")
        self.project.with_suffix(".kicad_pcb").write_text("(kicad_pcb)", encoding="utf-8")

    def structured(self, result: CallToolResult):
        self.assertFalse(result.is_error, result.content)
        self.assertIsNotNone(result.structured_content)
        return result.structured_content

    @staticmethod
    def text(result: CallToolResult) -> str:
        return "\n".join(item.text for item in result.content if isinstance(item, TextContent))

    def import_arguments(self, source: Path | None = None) -> dict[str, str]:
        return {
            "source": str(source or self.project),
            "project_id": "incoming-board",
            "toolchain_id": "kicad-10.0.5",
        }

    async def test_handshake_discovery_and_structured_inventory(self) -> None:
        before = snapshot(self.root)
        async with Client(create_server(self.root), mode="legacy") as client:
            self.assertIsNotNone(client.server_info)
            self.assertTrue(client.protocol_version)
            listing = await client.list_tools()
            self.assertEqual({tool.name for tool in listing.tools}, READ_TOOLS)
            inventory_tool = next(tool for tool in listing.tools if tool.name == "list_projects")
            self.assertIsNotNone(inventory_tool.output_schema)
            data = self.structured(await client.call_tool("list_projects"))
            report = TemplateInventoryReport.model_validate_json(json.dumps(data))
            self.assertEqual(report.status, "PASS")
            self.assertFalse(report.build_authorized)
            controller = next(project for project in report.projects if project.id == "controller")
            self.assertEqual(controller.toolchain_id, "kicad-10.0.0")
            self.assertEqual(controller.readiness, "INPUTS_PRESENT")
            self.assertIn("kicad-10.0.5", {toolchain.id for toolchain in report.toolchains})
        self.assertEqual(snapshot(self.root), before)

    async def test_unregistered_execution_and_write_tools_cannot_be_called(self) -> None:
        before = snapshot(self.root)
        async with Client(create_server(self.root), mode="legacy") as client:
            for name, arguments in (
                ("check_project", {"project_id": "controller"}),
                ("new_project", {
                    "project_id": "new-board", "kind": "pcb", "toolchain_id": "kicad-10.0.5",
                }),
                ("import_project", self.import_arguments()),
            ):
                with self.subTest(tool=name):
                    result = await client.call_tool(name, arguments)
                    self.assertTrue(result.is_error)
                    self.assertIn("Unknown tool", self.text(result))
        self.assertEqual(snapshot(self.root), before)

    async def test_write_and_execution_capabilities_are_independent(self) -> None:
        for options, enabled in (
            ({"allow_checks": True}, {"check_project"}),
            ({"allow_writes": True}, {"new_project", "import_project"}),
        ):
            with self.subTest(options=options):
                async with Client(create_server(self.root, **options), mode="legacy") as client:
                    listing = await client.list_tools()
                    self.assertEqual({tool.name for tool in listing.tools}, READ_TOOLS | enabled)

    async def test_project_report_preserves_manifest_and_independent_contract(self) -> None:
        async with Client(create_server(self.root), mode="legacy") as client:
            data = self.structured(await client.call_tool("get_project", {
                "project_id": "controller",
            }))
            report = McpProjectReport.model_validate_json(json.dumps(data))
            self.assertEqual(report.schema_version, "1")
            self.assertFalse(report.build_authorized)
            self.assertEqual(report.project.id, "controller")
            self.assertEqual(report.project.toolchain_id, "kicad-10.0.0")
            self.assertEqual(
                McpProjectReport.model_validate_json(report.model_dump_json(by_alias=True)), report,
            )
            directory = self.root / "examples/projects/controller"
            self.assertEqual(data["manifest"], read_model(
                directory / "project.json", ProjectManifest,
            ).model_dump(mode="json", by_alias=True))
            self.assertEqual(data["contract"], read_model(
                directory / "tests/contract.json", ProjectTestContract,
            ).model_dump(mode="json", by_alias=True))
            for identifier in ("missing-board", "../README.md"):
                result = await client.call_tool("get_project", {"project_id": identifier})
                self.assertTrue(result.is_error, identifier)
                self.assertIn("Call list_projects", self.text(result))

    async def test_project_report_rejects_unsupported_version_extra_fields_and_wrong_types(self) -> None:
        async with Client(create_server(self.root), mode="legacy") as client:
            data = self.structured(await client.call_tool("get_project", {
                "project_id": "controller",
            }))
        for update, field in (
            ({"schema_version": "2"}, "schema_version"),
            ({"schema_version": 1}, "schema_version"),
            ({"unexpected": "not part of the contract"}, "unexpected"),
            ({"build_authorized": "false"}, "build_authorized"),
            ({"project": data["project"] | {"id": 123}}, "project.id"),
        ):
            with self.subTest(update=update):
                with self.assertRaises(ValidationError) as rejected:
                    McpProjectReport.model_validate_json(json.dumps(data | update))
                self.assertIn(field, str(rejected.exception))

    async def test_each_document_is_available_as_tool_and_resource(self) -> None:
        async with Client(create_server(self.root), mode="legacy") as client:
            resources = await client.list_resources()
            self.assertEqual(
                {str(resource.uri) for resource in resources.resources},
                {f"kicad://docs/{name}" for name in DOCUMENTS},
            )
            for name, filename in DOCUMENTS.items():
                with self.subTest(document=name):
                    expected = (self.root / "docs/workflow" / filename).read_text(encoding="utf-8")
                    result = await client.call_tool("read_document", {"name": name})
                    self.assertFalse(result.is_error, result.content)
                    self.assertEqual(self.text(result), expected)
                    resource = await client.read_resource(f"kicad://docs/{name}")
                    self.assertEqual(len(resource.contents), 1)
                    self.assertEqual(resource.contents[0].text, expected)
            denied = await client.call_tool("read_document", {"name": "../../README.md"})
            self.assertTrue(denied.is_error)

    async def test_doctor_returns_readiness_without_creating_check_receipts(self) -> None:
        before = snapshot(self.root)
        async with Client(create_server(self.root), mode="legacy") as client:
            # Native tools may be absent on a contributor's machine; that is an
            # environment finding, never an MCP success substituted for readiness.
            with patch("tools.hwrepo.doctor.shutil.which", return_value=None):
                data = self.structured(await client.call_tool("doctor", {
                    "project_id": "controller", "native": True,
                }))
            self.assertEqual(data["status"], "FAIL")
            self.assertFalse(data["build_authorized"])
            self.assertTrue(data["native_requested"])
            self.assertTrue(any(check["status"] == "FAIL" for check in data["checks"]))
        self.assertEqual(snapshot(self.root), before)

    async def test_external_preview_requires_startup_root_and_preserves_source_and_checkout(self) -> None:
        before_root, before_source = snapshot(self.root), snapshot(self.source)
        async with Client(create_server(self.root), mode="legacy") as client:
            denied = await client.call_tool("preview_import", self.import_arguments())
            self.assertTrue(denied.is_error, denied.content)
            self.assertIn("--import-root", self.text(denied))
        async with Client(
            create_server(self.root, import_roots=(self.source,)), mode="legacy",
        ) as client:
            data = self.structured(await client.call_tool("preview_import", self.import_arguments()))
            self.assertEqual(data["status"], "PASS", data["issues"])
            self.assertTrue(data["dry_run"])
            self.assertTrue(data["review_required"])
            self.assertIn(self.project.name, data["copied_sha256"])
            self.assertFalse((self.root / data["directory"]).exists())
        self.assertEqual(snapshot(self.root), before_root)
        self.assertEqual(snapshot(self.source), before_source)

    async def test_checkout_preview_accepts_source_without_enabling_writes(self) -> None:
        source = self.root / "incoming"
        shutil.copytree(self.source, source)
        before = snapshot(self.root)
        async with Client(create_server(self.root), mode="legacy") as client:
            data = self.structured(await client.call_tool(
                "preview_import", self.import_arguments(Path("incoming") / self.project.name),
            ))
            self.assertEqual(data["status"], "PASS", data["issues"])
            self.assertTrue(data["dry_run"])
        self.assertEqual(snapshot(self.root), before)

    async def test_import_symlink_and_parent_traversal_do_not_expand_authorized_roots(self) -> None:
        linked = self.root / "linked-input"
        try:
            linked.symlink_to(self.source, target_is_directory=True)
        except OSError:
            self.skipTest("Symlink creation unavailable")
        before = snapshot(self.root)
        async with Client(create_server(self.root), mode="legacy") as client:
            for source in (
                linked / self.project.name,
                self.root / ".." / self.source.name / self.project.name,
            ):
                with self.subTest(source=str(source)):
                    denied = await client.call_tool("preview_import", self.import_arguments(source))
                    self.assertTrue(denied.is_error, denied.content)
        self.assertEqual(snapshot(self.root), before)

    async def test_write_mode_scaffolds_without_overwriting_or_accepting_invalid_ids(self) -> None:
        arguments = {"project_id": "new-board", "kind": "pcb", "toolchain_id": "kicad-10.0.5"}
        async with Client(create_server(self.root, allow_writes=True), mode="legacy") as client:
            created = self.structured(await client.call_tool("new_project", arguments))
            self.assertEqual(created["status"], "PASS", created["issues"])
            island = self.root / created["directory"]
            manifest = read_model(island / "project.json", ProjectManifest)
            self.assertEqual(manifest.id, "new-board")
            self.assertEqual(manifest.assurance_profile, "development")
            self.assertFalse((island / manifest.project).exists())
            notes = island / "docs/README.md"
            notes.write_text("Preserve the contributor's design notes.\n", encoding="utf-8")
            before = snapshot(self.root)
            repeated = self.structured(await client.call_tool("new_project", arguments))
            self.assertEqual(repeated["status"], "FAIL")
            for update in (
                {"project_id": "../escape"},
                {"project_id": "unknown-toolchain", "toolchain_id": "unknown"},
                {"project_id": "invalid-kind", "kind": "other"},
            ):
                with self.subTest(update=update):
                    rejected = await client.call_tool("new_project", arguments | update)
                    self.assertTrue(
                        rejected.is_error or self.structured(rejected)["status"] == "FAIL",
                        rejected.content,
                    )
            self.assertEqual(snapshot(self.root), before)
            self.assertFalse((self.base / "escape").exists())

    async def test_authorized_import_copies_source_and_keeps_review_required(self) -> None:
        before_source = snapshot(self.source)
        async with Client(create_server(
            self.root, allow_writes=True, import_roots=(self.source,),
        ), mode="legacy") as client:
            data = self.structured(await client.call_tool("import_project", self.import_arguments()))
            self.assertEqual(data["status"], "PASS", data["issues"])
            self.assertFalse(data["dry_run"])
            self.assertTrue(data["review_required"])
            island = self.root / data["directory"]
            for name in before_source:
                self.assertEqual((island / "kicad" / name).read_bytes(), (self.source / name).read_bytes())
            listed = self.structured(await client.call_tool("list_projects"))
            self.assertIn("incoming-board", {project["id"] for project in listed["projects"]})
        self.assertEqual(snapshot(self.source), before_source)

    async def test_check_dispatch_preserves_failure_receipt_and_selected_runner(self) -> None:
        failed = ProjectVerificationReport(
            project_id="controller", depth="native", runner="container", status="FAIL",
            run_directory=str(self.root / "build/verification/controller-failed"),
            next_actions=("Repair the failed project test before reviewing this board.",),
        )
        async with Client(create_server(self.root, allow_checks=True), mode="legacy") as client:
            with patch("tools.hwrepo.mcp_server.verify", return_value=failed) as verify:
                data = self.structured(await client.call_tool("check_project", {
                    "project_id": "controller", "depth": "native", "runner": "container",
                }))
            self.assertEqual(data, failed.model_dump(mode="json"))
            verify.assert_called_once_with(self.root, "controller", depth="native", runner="container")
            with patch("tools.hwrepo.mcp_server.verify", return_value=failed) as verify:
                rejected = await client.call_tool("check_project", {
                    "project_id": "controller", "runner": "arbitrary-command",
                })
            self.assertTrue(rejected.is_error)
            verify.assert_not_called()

    async def test_portable_check_rejects_native_runners_before_execution(self) -> None:
        async with Client(create_server(self.root, allow_checks=True), mode="legacy") as client:
            for runner in ("local", "container"):
                for options in ({}, {"depth": "portable"}):
                    with self.subTest(runner=runner, options=options):
                        with patch("tools.hwrepo.mcp_server.verify") as verify:
                            rejected = await client.call_tool("check_project", {
                                "project_id": "controller", "runner": runner, **options,
                            })
                        self.assertTrue(rejected.is_error, rejected.content)
                        self.assertIn("requires native depth", self.text(rejected))
                        verify.assert_not_called()

    async def test_linked_receipt_directory_is_rejected_before_project_execution(self) -> None:
        external = self.base / "external-receipts"
        external.mkdir()
        for relative in ("build", "build/diagnostics"):
            with self.subTest(relative=relative):
                link = self.root / relative
                link.parent.mkdir(parents=True, exist_ok=True)
                try:
                    link.symlink_to(external, target_is_directory=True)
                except OSError:
                    self.skipTest("Symlink creation unavailable")
                try:
                    async with Client(
                        create_server(self.root, allow_checks=True), mode="legacy",
                    ) as client:
                        with patch("tools.hwrepo.mcp_server.verify") as verify:
                            result = await client.call_tool("check_project", {
                                "project_id": "controller",
                            })
                        self.assertTrue(result.is_error, result.content)
                        verify.assert_not_called()
                        self.assertEqual(list(external.iterdir()), [])
                finally:
                    link.unlink()

    async def test_stdio_cli_uses_explicit_checkout_from_unrelated_working_directory(self) -> None:
        caller = self.base / "caller"
        caller.mkdir()
        parameters = StdioServerParameters(
            command=sys.executable,
            args=["-B", "-m", "tools.mcp", "--root", str(self.root)],
            cwd=caller,
            env={"PYTHONPATH": str(SOURCE_ROOT), "PYTHONDONTWRITEBYTECODE": "1"},
        )
        async with Client(parameters, mode="legacy", read_timeout_seconds=20) as client:
            self.assertIsNotNone(client.server_info)
            data = self.structured(await client.call_tool("list_projects"))
            self.assertIn("controller", {project["id"] for project in data["projects"]})
            listing = await client.list_tools()
            self.assertEqual({tool.name for tool in listing.tools}, READ_TOOLS)
        self.assertEqual(list(caller.iterdir()), [])

    def test_cli_refuses_implicit_or_relative_checkout_selection(self) -> None:
        environment = os.environ | {"PYTHONPATH": str(SOURCE_ROOT), "PYTHONDONTWRITEBYTECODE": "1"}
        for arguments in ((), ("--root", "repository")):
            with self.subTest(arguments=arguments):
                result = subprocess.run(
                    (sys.executable, "-B", "-m", "tools.mcp", *arguments),
                    cwd=self.base, env=environment, capture_output=True, text=True,
                    input="", timeout=20, check=False,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")
                self.assertIn("root", result.stderr.lower())


if __name__ == "__main__":
    unittest.main()
