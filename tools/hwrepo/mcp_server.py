"""Optional MCP adapter over the existing, typed repository workflow services."""
from __future__ import annotations

from collections.abc import Callable, Generator, Mapping
from contextlib import contextmanager
from pathlib import Path
from threading import Lock
from typing import Literal

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ResourceError, ToolError
from mcp.types import ToolAnnotations

from ..verify import Depth, verify
from .contracts import read_model, repo_path
from .doctor import NativeRunner
from .doctor import doctor as inspect_environment
from .importing import import_project as import_design
from .inventory import inventory
from .models import (
    McpProjectReport,
    ProjectImportReport,
    ProjectKind,
    ProjectManifest,
    ProjectScaffoldReport,
    ProjectTestContract,
    ProjectVerificationReport,
    TemplateDoctorReport,
    TemplateInventoryReport,
)
from .scaffold import new_project as scaffold_project

DocumentName = Literal[
    "start-here", "first-board", "diagnostics", "import-workflow",
    "contributor-guide", "checks-and-ci", "mcp",
]
DOCUMENTS: Mapping[DocumentName, str] = {
    "start-here": "docs/workflow/START_HERE.md",
    "first-board": "docs/workflow/FIRST_BOARD.md",
    "diagnostics": "docs/workflow/DIAGNOSTICS.md",
    "import-workflow": "docs/workflow/IMPORT_WORKFLOW.md",
    "contributor-guide": "docs/workflow/CONTRIBUTOR_GUIDE.md",
    "checks-and-ci": "docs/workflow/CHECKS_AND_CI.md",
    "mcp": "docs/workflow/MCP.md",
}
READ_ONLY = ToolAnnotations(
    read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False,
)
CREATE_ONLY = ToolAnnotations(
    read_only_hint=False, destructive_hint=False, idempotent_hint=False, open_world_hint=False,
)
EXECUTION = ToolAnnotations(
    read_only_hint=False, destructive_hint=True, idempotent_hint=False, open_world_hint=True,
)


def import_source(root: Path, source: str, scopes: tuple[Path, ...]) -> Path:
    """Authorize a source before the importer resolves its parent or reads siblings."""
    candidate = Path(source).expanduser()
    if ".." in candidate.parts:
        raise ValueError("Import source must not contain parent traversal")
    candidate = candidate if candidate.is_absolute() else root / candidate
    for scope in scopes:
        if candidate.is_relative_to(scope):
            relative = candidate.relative_to(scope).as_posix()
            path = repo_path(scope, relative)
            if path.suffix != ".kicad_pro" or not path.is_file():
                raise ValueError("Select an existing .kicad_pro file, not a directory")
            return path
    raise ValueError("Import source is outside the checkout and configured --import-root directories")


@contextmanager
def service_operation(operation: Lock) -> Generator[None, None, None]:
    """Preserve actionable service/input errors in the MCP tool response."""
    with operation:
        try:
            yield
        except (OSError, ValueError) as exc:
            raise ToolError(str(exc)) from exc


def create_server(
    root: Path, *, allow_checks: bool = False, allow_writes: bool = False,
    import_roots: tuple[Path, ...] = (),
) -> MCPServer[None]:
    """Bind one server to a trusted checkout; tool calls cannot change its authority."""
    declared_root = root.expanduser().absolute()
    root = declared_root.resolve(strict=True)
    if not root.is_dir() or not repo_path(root, "catalog/projects.json").is_file():
        raise ValueError("MCP root must be a KiCad workflow checkout with catalog/projects.json")
    scopes = [declared_root, root]
    for path in import_roots:
        declared = path.expanduser().absolute()
        resolved = declared.resolve(strict=True)
        if not resolved.is_dir():
            raise ValueError(f"Import root must be an existing directory: {path}")
        scopes.extend((declared, resolved))
    permitted_sources = tuple(dict.fromkeys(scopes))
    # The SDK runs synchronous tools in worker threads. Serialize operations on this
    # checkout so discovery never observes a partially staged write from this server.
    operation = Lock()
    server: MCPServer[None] = MCPServer(
        "kicad-workflow", version="1", log_level="WARNING",
        instructions=(
            f"Use only this checkout: {root}. Start with list_projects and doctor. "
            "Inventory input presence and import previews are not design validation. "
            "Read the status and next actions in every report. Passing checks are not "
            "electrical approval or manufacturing authorization. Checks execute repository "
            "code and writes create project islands only when enabled at server startup."
        ),
    )

    def list_projects() -> TemplateInventoryReport:
        """Discover project IDs, products, tags and toolchains; presence is not validation."""
        with service_operation(operation):
            return inventory(root)

    server.tool(annotations=READ_ONLY)(list_projects)

    def get_project(project_id: str) -> McpProjectReport:
        """Read one registered project's inventory, manifest and authored test expectations."""
        with service_operation(operation):
            report = inventory(root)
            if report.status != "PASS":
                raise ValueError("Project discovery failed: " + "; ".join(
                    issue.message for issue in report.issues
                ))
            project = next((item for item in report.projects if item.id == project_id), None)
            if project is None:
                raise ValueError(f"Unknown project ID: {project_id}. Call list_projects first.")
            path = repo_path(root, project.manifest)
            manifest = read_model(path, ProjectManifest)
            contract_path = repo_path(path.parent, manifest.checks)
            contract = (read_model(contract_path, ProjectTestContract)
                        if contract_path.is_file() else None)
            return McpProjectReport(project=project, manifest=manifest, contract=contract)

    server.tool(annotations=READ_ONLY)(get_project)

    def doctor(project_id: str | None = None, native: bool = False) -> TemplateDoctorReport:
        """Inspect setup without running project tests; select a project for native readiness."""
        with service_operation(operation):
            return inspect_environment(root, native=native, project_id=project_id)

    server.tool(annotations=READ_ONLY)(doctor)

    def document(name: DocumentName) -> str:
        with operation:
            try:
                return repo_path(root, DOCUMENTS[name]).read_text(encoding="utf-8")
            except (OSError, ValueError) as exc:
                raise ResourceError(str(exc)) from exc

    def read_document(name: DocumentName) -> str:
        """Read a named workflow guide from this checkout, including connection instructions."""
        return document(name)

    server.tool(annotations=READ_ONLY)(read_document)

    def resource_reader(name: DocumentName) -> Callable[[], str]:
        def read() -> str:
            return document(name)
        return read

    for name in DOCUMENTS:
        server.resource(
            f"kicad://docs/{name}", name=name, mime_type="text/markdown",
            description=f"Repository workflow guide: {name}",
        )(resource_reader(name))

    def preview_import(source: str, project_id: str, toolchain_id: str) -> ProjectImportReport:
        """Preview one .kicad_pro import without writing. Relative sources use the checkout.

        Sources must be inside the checkout or an enabled import root. The importer
        inventories the source directory's siblings too. Review hashes and exclusions;
        a PASS preview does not validate the electrical design.
        """
        with service_operation(operation):
            path = import_source(root, source, permitted_sources)
            return import_design(root, path, project_id, toolchain_id, dry_run=True)

    server.tool(annotations=READ_ONLY)(preview_import)

    if allow_checks:
        def check_project(
            project_id: str, depth: Depth = "portable", runner: NativeRunner = "auto",
        ) -> ProjectVerificationReport:
            """Run trusted project tests and keep a fresh ignored verification receipt.

            This executes repository code, which may change files or contact services.
            Native depth uses exact local KiCad or pinned Docker and may download images
            and dependencies. Inspect status, diagnosis and run_directory in the report.
            """
            with service_operation(operation):
                if depth == "portable" and runner != "auto":
                    raise ValueError("A local or container runner requires native depth")
                # DiagnosticJournal creates this directory; reject links before it writes.
                repo_path(root, "build/diagnostics")
                return verify(root, project_id, depth=depth, runner=runner)

        server.tool(annotations=EXECUTION)(check_project)

    if allow_writes:
        def new_project(
            project_id: str, kind: ProjectKind, toolchain_id: str,
        ) -> ProjectScaffoldReport:
            """Create a new project skeleton without overwriting an existing island.

            Select kind and toolchain from the repository guidance and inventory. The
            skeleton is incomplete until an engineer supplies the design and expectations.
            """
            with service_operation(operation):
                return scaffold_project(root, project_id, kind, toolchain_id)

        server.tool(annotations=CREATE_ONLY)(new_project)

        def import_project(source: str, project_id: str, toolchain_id: str) -> ProjectImportReport:
            """Copy a previously reviewed import into a new project; preserve original source.

            Call preview_import first and review every exclusion. Source directory scope
            matches preview_import. This does not author electrical test expectations.
            """
            with service_operation(operation):
                path = import_source(root, source, permitted_sources)
                return import_design(root, path, project_id, toolchain_id)

        server.tool(annotations=CREATE_ONLY)(import_project)

    return server
