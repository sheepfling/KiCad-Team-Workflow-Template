"""Optional MCP adapter over the existing, typed repository workflow services."""
from __future__ import annotations

from collections.abc import Callable, Generator, Mapping
from contextlib import contextmanager
from pathlib import Path
from subprocess import SubprocessError
from threading import Lock
from typing import Literal
from zipfile import BadZipFile

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ResourceError, ToolError
from mcp.types import ToolAnnotations

from ..verify import Depth, verify
from . import mcp_files as files
from . import mcp_workflow as workflow
from .contracts import read_model, repo_path
from .doctor import NativeRunner
from .doctor import doctor as inspect_environment
from .import_inventory import scan_imports as scan_designs
from .importing import import_project as import_design
from .inventory import inventory
from .models import (
    ContractCoachReport,
    DiagnosticReport,
    ImportInventoryReport,
    LocalRescueReport,
    McpArtifactList,
    McpEditPreview,
    McpEditResult,
    McpFileContent,
    McpGenerationReport,
    McpProjectReport,
    McpScopeReport,
    ProjectImportReport,
    ProjectKind,
    ProjectManifest,
    ProjectScaffoldReport,
    ProjectTestContract,
    ProjectVerificationReport,
    ReleaseExportReport,
    ReleaseManifest,
    ReleasePackageReport,
    ReleaseReadinessReport,
    TemplateDoctorReport,
    TemplateInventoryReport,
)
from .scaffold import new_project as scaffold_project

DocumentName = Literal[
    "start-here", "first-board", "diagnostics", "import-workflow",
    "contributor-guide", "checks-and-ci", "mcp", "bom-policy", "release-readiness",
    "release-storage", "project-kinds", "libraries", "authority-model", "assurance-profiles",
]
DOCUMENTS: Mapping[DocumentName, str] = {
    "start-here": "docs/workflow/START_HERE.md",
    "first-board": "docs/workflow/FIRST_BOARD.md",
    "diagnostics": "docs/workflow/DIAGNOSTICS.md",
    "import-workflow": "docs/workflow/IMPORT_WORKFLOW.md",
    "contributor-guide": "docs/workflow/CONTRIBUTOR_GUIDE.md",
    "checks-and-ci": "docs/workflow/CHECKS_AND_CI.md",
    "mcp": "docs/workflow/MCP.md",
    "bom-policy": "docs/workflow/BOM_POLICY.md",
    "release-readiness": "docs/workflow/RELEASE_READINESS.md",
    "release-storage": "docs/workflow/RELEASE_STORAGE.md",
    "project-kinds": "docs/workflow/PROJECT_KINDS.md",
    "libraries": "docs/workflow/LIBRARIES.md",
    "authority-model": "docs/workflow/AUTHORITY_MODEL.md",
    "assurance-profiles": "docs/workflow/ASSURANCE_PROFILES.md",
}
READ_ONLY = ToolAnnotations(
    read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False,
)
CREATE_ONLY = ToolAnnotations(
    read_only_hint=False, destructive_hint=False, idempotent_hint=False, open_world_hint=False,
)
EDIT = ToolAnnotations(
    read_only_hint=False, destructive_hint=True, idempotent_hint=False, open_world_hint=False,
)
EXECUTION = ToolAnnotations(
    read_only_hint=False, destructive_hint=True, idempotent_hint=False, open_world_hint=True,
)


def import_path(
    root: Path, source: str, scopes: tuple[Path, ...], *, directory: bool = False,
) -> Path:
    """Authorize a source before the importer resolves its parent or reads siblings."""
    candidate = Path(source).expanduser()
    if ".." in candidate.parts:
        raise ValueError("Import source must not contain parent traversal")
    candidate = candidate if candidate.is_absolute() else root / candidate
    for scope in scopes:
        if candidate.is_relative_to(scope):
            relative = candidate.relative_to(scope).as_posix()
            path = scope.resolve() if relative == "." else repo_path(scope, relative)
            if directory:
                if not path.is_dir():
                    raise ValueError("Select an existing import source directory")
            elif path.suffix != ".kicad_pro" or not path.is_file():
                raise ValueError("Select an existing .kicad_pro file, not a directory")
            return path
    raise ValueError("Import source is outside the checkout and configured --import-root directories")


@contextmanager
def service_operation(operation: Lock) -> Generator[None, None, None]:
    """Preserve actionable service/input errors in the MCP tool response."""
    with operation:
        try:
            yield
        except (OSError, ValueError, BadZipFile, SubprocessError) as exc:
            raise ToolError(str(exc)) from exc


def create_server(
    root: Path, *, allow_checks: bool = False, allow_writes: bool = False,
    import_roots: tuple[Path, ...] = (), allow_edits: bool = False, allow_exports: bool = False,
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
        "kicad-workflow", version="2", log_level="WARNING",
        instructions=(
            f"Use only this checkout: {root}. Start with list_projects and doctor. "
            "Inventory input presence and import previews are not design validation. "
            "Read the status and next actions in every report. Passing checks are not "
            "electrical approval or manufacturing authorization. Follow scan/preview/import, "
            "doctor, diagnose_project, read artifacts/source, preview and apply an explicit "
            "reviewed edit, then recheck. Commit reviewed source with normal Git before "
            "export_project or prepare_review. Diagnose BOMs with the matching native report. "
            "Use list_artifacts/read_artifact to inspect receipts; they use repository-relative "
            "paths. Execution, creation, editing and export capabilities are enabled separately "
            "at startup. Never invent electrical expectations, approvals, or waivers."
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

    def doctor(
        project_id: str | None = None, native: bool = False,
        toolchain_id: str | None = None, runner: NativeRunner = "auto",
    ) -> TemplateDoctorReport:
        """Inspect setup without running project tests; select a project for native readiness."""
        with service_operation(operation):
            return inspect_environment(
                root, native=native, project_id=project_id, toolchain_id=toolchain_id, runner=runner,
            )

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
            path = import_path(root, source, permitted_sources)
            return import_design(root, path, project_id, toolchain_id, dry_run=True)

    server.tool(annotations=READ_ONLY)(preview_import)

    def scan_imports(source_directory: str, toolchain_id: str) -> ImportInventoryReport:
        """Triage a permitted source directory into individual import previews; no files copied."""
        with service_operation(operation):
            path = import_path(root, source_directory, permitted_sources, directory=True)
            # The directory scanner must not resolve linked candidate files before authorization.
            for candidate in path.rglob("*.kicad_pro"):
                repo_path(path, candidate.relative_to(path).as_posix())
            return scan_designs(root, path, toolchain_id)

    server.tool(annotations=READ_ONLY)(scan_imports)

    def diagnose_import(source: str, project_id: str, toolchain_id: str) -> DiagnosticReport:
        """Triage one import into blockers, exclusions and repair guidance; save an ignored receipt."""
        with service_operation(operation):
            path = import_path(root, source, permitted_sources)
            return workflow.diagnose_import(root, path, project_id, toolchain_id)

    server.tool(annotations=CREATE_ONLY)(diagnose_import)

    def rescue_project(project_id: str) -> LocalRescueReport:
        """Inspect one island when global discovery is broken; always UNVERIFIED_GLOBAL.

        Saves an ignored receipt without running project tests. Repair discovery before
        normal diagnosis/checks; this result is never CI or release evidence.
        """
        with service_operation(operation):
            return workflow.rescue_project(root, project_id)

    server.tool(annotations=CREATE_ONLY)(rescue_project)

    def list_artifacts(
        directory: str = "build", offset: int = 0, limit: int = 100,
    ) -> McpArtifactList:
        """List a bounded page of retained artifacts in a repository-relative build directory."""
        with service_operation(operation):
            return files.list_artifacts(root, directory, offset, limit)

    server.tool(annotations=READ_ONLY)(list_artifacts)

    def read_artifact(path: str, offset: int = 0, limit: int = 20000) -> McpFileContent:
        """Read a bounded text chunk or binary metadata from an ignored build artifact.

        Use repository-relative paths from list_artifacts. Logs, reports, BOM CSVs and
        SVG source are available; this never executes or renders embedded content.
        """
        with service_operation(operation):
            return files.read_artifact(root, path, offset, limit)

    server.tool(annotations=READ_ONLY)(read_artifact)

    def read_project_file(
        project_id: str, path: str, offset: int = 0, limit: int = 20000,
    ) -> McpFileContent:
        """Read an authored text file relative to a registered project island for repair."""
        with service_operation(operation):
            return files.read_project_file(root, project_id, path, offset, limit)

    server.tool(annotations=READ_ONLY)(read_project_file)

    def preview_project_edit(
        project_id: str, path: str, expected_sha256: str, old_text: str, new_text: str,
    ) -> McpEditPreview:
        """Preview one exact reviewed source replacement against the last-read SHA256.

        Close KiCad, read the source, and inspect this diff before applying. This does
        not infer a circuit repair or validate electrical correctness. Match exactly once.
        """
        with service_operation(operation):
            return files.preview_project_edit(
                root, project_id, path, expected_sha256, old_text, new_text,
            )

    server.tool(annotations=READ_ONLY)(preview_project_edit)

    def inspect_contract(project_id: str, native_summary: str) -> ContractCoachReport:
        """Compare source-bound native observations with authored expectations; retain UNREVIEWED.

        native_summary is a repository-relative build artifact. This reads evidence;
        it does not execute KiCad or modify the independent test contract.
        """
        with service_operation(operation):
            return workflow.inspect_contract(root, project_id, native_summary)

    server.tool(annotations=READ_ONLY)(inspect_contract)

    def check_release(manifest: str) -> ReleaseReadinessReport:
        """Verify a retained release manifest and its source/evidence; creates no approval."""
        with service_operation(operation):
            return workflow.check_release(root, manifest)

    server.tool(annotations=READ_ONLY)(check_release)

    def verify_package(archive: str) -> ReleasePackageReport:
        """Verify an ignored ZIP through temporary restore without running restored project code."""
        with service_operation(operation):
            return workflow.verify_package(root, archive)

    server.tool(annotations=READ_ONLY)(verify_package)

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

        def diagnose_project(
            project_id: str, native_report: str | None = None, bom: str | None = None,
        ) -> DiagnosticReport:
            """Run project diagnosis with repair findings, optional native evidence and BOM review.

            Executes project/product tests and saves a receipt. Native report and BOM
            paths must be repository-relative build artifacts; BOM requires a matching
            native report. Stale or mismatched evidence must be repaired, not waived.
            """
            with service_operation(operation):
                return workflow.diagnose_project(root, project_id, native_report, bom)

        server.tool(annotations=EXECUTION)(diagnose_project)

        def capture_contract(
            project_id: str, runner: NativeRunner = "auto",
        ) -> ContractCoachReport:
            """Capture exact-toolchain netlist observations for review; never author expectations."""
            with service_operation(operation):
                return workflow.capture_contract(root, project_id, runner)

        server.tool(annotations=EXECUTION)(capture_contract)

        def check_scope(
            project_ids: list[str] | None = None, product_ids: list[str] | None = None,
            tags: list[str] | None = None, exclude_tags: list[str] | None = None,
        ) -> McpScopeReport:
            """Run selected project/product/tag checks or the full portable gate when unselected.

            Include selectors form a union; excluded tags subtract afterward. Executes
            repository tests. Use the full gate after shared tooling, catalog or policy edits.
            """
            with service_operation(operation):
                return workflow.check_scope(
                    root, tuple(project_ids or ()), tuple(product_ids or ()),
                    tuple(tags or ()), tuple(exclude_tags or ()),
                )

        server.tool(annotations=EXECUTION)(check_scope)

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
                path = import_path(root, source, permitted_sources)
                return import_design(root, path, project_id, toolchain_id)

        server.tool(annotations=CREATE_ONLY)(import_project)

    if allow_edits:
        def apply_project_edit(
            project_id: str, path: str, expected_sha256: str, old_text: str, new_text: str,
        ) -> McpEditResult:
            """Apply a reviewed preview's exact source replacement; reject stale or ambiguous input.

            Requires the same SHA256 and replacement as the reviewed preview. Close KiCad
            first. Re-diagnose/check afterward, including native checks after CAD changes.
            This is an explicit source edit and does not approve the electrical decision.
            """
            with service_operation(operation):
                return files.apply_project_edit(
                    root, project_id, path, expected_sha256, old_text, new_text,
                )

        server.tool(annotations=EDIT)(apply_project_edit)

    if allow_exports:
        def generate_views(
            view_id: str, project_ids: list[str] | None = None,
            product_ids: list[str] | None = None, tags: list[str] | None = None,
            exclude_tags: list[str] | None = None,
        ) -> McpGenerationReport:
            """Generate product BOMs, harness schedules and review views into fresh ignored output.

            Select projects/products/tags or leave unselected for all configured views.
            These catalog-derived projections are distinct from native assembly/purchasing BOMs.
            """
            with service_operation(operation):
                return workflow.generate_views(
                    root, view_id, tuple(project_ids or ()), tuple(product_ids or ()),
                    tuple(tags or ()), tuple(exclude_tags or ()),
                )

        server.tool(annotations=CREATE_ONLY)(generate_views)

        def package_release(manifest: str, package_id: str) -> ReleasePackageReport:
            """Verify and package retained release evidence into a fresh ignored ZIP; no publishing."""
            with service_operation(operation):
                return workflow.package_release(root, manifest, package_id)

        server.tool(annotations=CREATE_ONLY)(package_release)

        def restore_package(archive: str, restore_id: str) -> ReleasePackageReport:
            """Restore an ignored ZIP to a fresh ignored checkout, without executing its scripts."""
            with service_operation(operation):
                return workflow.restore_package(root, archive, restore_id)

        server.tool(annotations=CREATE_ONLY)(restore_package)

        if allow_checks:
            def export_project(
                project_id: str, export_id: str, runner: NativeRunner = "auto",
            ) -> ReleaseExportReport:
                """Export Gerbers, drills, placements and assembly/purchasing BOMs for review.

                Requires clean committed source, declared export settings and exact KiCad.
                Writes fresh ignored evidence only. Export success is not release approval.
                """
                with service_operation(operation):
                    return workflow.export_project(root, project_id, export_id, runner)

            server.tool(annotations=EXECUTION)(export_project)

            def prepare_review(
                project_id: str, release_id: str, runner: NativeRunner = "auto",
            ) -> ReleaseManifest:
                """Prepare an engineering_review candidate with portable/native/export evidence.

                Requires clean committed source and an exact runner. Never creates production
                approval, a tag, a purchase or a manufacturing authorization.
                """
                with service_operation(operation):
                    return workflow.prepare_review(root, project_id, release_id, runner)

            server.tool(annotations=EXECUTION)(prepare_review)

    return server
