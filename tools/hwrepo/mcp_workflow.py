"""Bounded MCP workflow adapters over diagnostic, native and release services."""
from __future__ import annotations

import sys
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from pydantic import TypeAdapter

from ..check_toolchain import cli_executable
from ..ci import static_pipeline
from ..verify import run_command
from . import contract_coach, diagnostics, generation, packaging, releasing, rescue
from .contracts import read_model, repo_path, write_model
from .diagnostic_journal import DiagnosticJournal
from .discovery import load_config, load_registry
from .doctor import NativeRunner, doctor
from .evidence import source_state
from .exports import verify_exports
from .mcp_files import artifact_path
from .models import (
    ContractCoachReport,
    DiagnosticReport,
    Identifier,
    LocalRescueReport,
    McpGenerationReport,
    McpScopeReport,
    ProjectManifest,
    ProjectRecord,
    ReleaseClass,
    ReleaseExportReport,
    ReleaseManifest,
    ReleasePackageReport,
    ReleaseReadinessReport,
    ReleaseStatus,
)
from .release import check as release_check
from .selection import ProjectSelector, resolve_project_ids

_IDENTIFIER: TypeAdapter[str] = TypeAdapter(Identifier)


def identifier(value: str) -> str:
    """Validate a single path component using the repository's identifier contract."""
    return _IDENTIFIER.validate_python(value, strict=True)


def selected_project(root: Path, project_id: str) -> ProjectRecord:
    identifier(project_id)
    project = next((item for item in load_registry(root).projects if item.id == project_id), None)
    if project is None:
        raise ValueError(f"Unknown project ID: {project_id}. Call list_projects first.")
    return project


def artifact_file(root: Path, value: str) -> Path:
    path = artifact_path(root, value)
    if not path.is_file():
        raise ValueError(f"Select an existing generated artifact file: {value}")
    return path


def _native_summary(root: Path, value: str) -> Path:
    """Constrain both the summary and sibling evidence read by existing coaches."""
    path = artifact_path(root, value)
    if path.is_dir():
        path = artifact_file(root, (path / "summary.json").relative_to(root).as_posix())
    elif not path.is_file():
        raise ValueError(f"Select an existing native summary: {value}")
    for name in ("erc.json", "drc.json", "netlist.xml", "netlist.command.json"):
        artifact_path(root, (path.parent / name).relative_to(root).as_posix())
    return path


@contextmanager
def journal(root: Path, project_id: str) -> Generator[DiagnosticJournal, None, None]:
    """Validate receipt containment before creating a journal and retain failures."""
    repo_path(root, "build/diagnostics")
    receipt = DiagnosticJournal(root, project_id)
    try:
        yield receipt
    except (Exception, KeyboardInterrupt) as exc:
        receipt.fail(exc)
        raise


def diagnose_import(
    root: Path, source: Path, project_id: str, toolchain_id: str,
) -> DiagnosticReport:
    """Diagnose an already-authorized import source and retain the preview receipt."""
    with journal(root, project_id) as receipt:
        result = diagnostics.diagnose_import(root, source, project_id, toolchain_id, receipt)
        result = result.model_copy(update={"run_directory": str(receipt.directory)})
        receipt.finish(result, diagnostics.format_text(result, "full"), result.status)
        return result


def diagnose_project(
    root: Path, project_id: str, native_report: str | None = None, bom: str | None = None,
) -> DiagnosticReport:
    """Run selected diagnosis; optional native/BOM inputs must be ignored artifacts."""
    if bom is not None and native_report is None:
        raise ValueError("BOM diagnosis requires the selected project's native_report")
    native = None if native_report is None else _native_summary(root, native_report)
    bom_path = None if bom is None else artifact_file(root, bom)
    with journal(root, project_id) as receipt:
        result = diagnostics.diagnose_project(root, project_id, native, bom_path, receipt)
        result = result.model_copy(update={"run_directory": str(receipt.directory)})
        receipt.finish(result, diagnostics.format_text(result, "full"), result.status)
        return result


def rescue_project(root: Path, project_id: str) -> LocalRescueReport:
    """Retain a local repair view without converting UNVERIFIED_GLOBAL into a pass."""
    with journal(root, project_id) as receipt:
        result = rescue.rescue_project(root, project_id, receipt)
        receipt.finish(result, rescue.format_rescue(result, "full"), result.status)
        return result


def check_scope(
    root: Path, project_ids: tuple[str, ...] = (), product_ids: tuple[str, ...] = (),
    tags: tuple[str, ...] = (), exclude_tags: tuple[str, ...] = (),
) -> McpScopeReport:
    """Reuse union/exclusion selection; no selectors deliberately invokes the full gate."""
    selector = ProjectSelector(
        project_ids=project_ids, product_ids=product_ids, tags=tags, excluded_tags=exclude_tags,
    )
    selected = list(resolve_project_ids(root, selector)) if selector.active else None
    with journal(root, "scope") as receipt:
        with receipt.stage("portable"):
            result = static_pipeline(root, selected)
        report = McpScopeReport(
            status=result.status, run_directory=str(receipt.directory), report=result,
        )
        receipt.finish_named("scope", report, f"Scope check: {report.status}", report.status)
        return report


def inspect_contract(root: Path, project_id: str, native_summary: str) -> ContractCoachReport:
    """Read source-bound observations without writing independent test expectations."""
    return contract_coach.inspect_summary(root, project_id, _native_summary(root, native_summary))


def capture_contract(
    root: Path, project_id: str, runner: NativeRunner = "auto",
) -> ContractCoachReport:
    """Capture an UNREVIEWED netlist with fixed local or digest-pinned native runners."""
    selected_project(root, project_id)
    if runner not in {"auto", "local", "container"}:
        raise ValueError(f"Unknown native runner: {runner}")
    native_runner = (
        contract_coach.LocalNetlistRunner("kicad-cli") if runner == "local"
        else contract_coach.ContainerNetlistRunner() if runner == "container"
        else contract_coach.AutoNetlistRunner("kicad-cli")
    )
    output = contract_coach.receipt_directory(root, project_id, None)
    result = contract_coach.capture(root, project_id, output, native_runner)
    contract_coach.save_receipt(output, result)
    return result


def selected_cli(root: Path, project_id: str, runner: NativeRunner) -> str | None:
    """Use doctor selection and resolve the fixed local command; callers cannot supply one."""
    result = doctor(root, native=True, project_id=project_id, runner=runner)
    if result.status != "PASS":
        raise ValueError("Native prerequisites failed: " + "; ".join(result.next_actions))
    native = next((check.observed for check in result.checks if check.id == "native-runner"), None)
    if native == "container":
        return None
    if native != "local":
        raise ValueError("Doctor did not select an exact native runner")
    executable = cli_executable("kicad-cli")
    if executable is None:
        raise ValueError("The selected local KiCad executable is no longer available")
    return executable


def fresh_output(root: Path, directory: str, output_id: str, suffix: str = "") -> Path:
    path = repo_path(root, f"build/{directory}/{identifier(output_id)}{suffix}")
    if path.exists():
        raise ValueError(f"Output already exists; choose a fresh ID: {path.relative_to(root)}")
    return path


def clean_source(root: Path) -> None:
    source = source_state(root)
    if not source.clean or source.commit is None:
        raise ValueError("Commit the reviewed source first; exports require a clean checkout")


def captured_command(root: Path, argv: tuple[str, ...], log: Path, timeout: int) -> None:
    """Keep subprocess output out of the MCP protocol and preserve failure evidence."""
    repo_path(root, log.relative_to(root).as_posix())
    if log.exists():
        raise ValueError(f"Command receipt already exists: {log.relative_to(root)}")
    log.parent.mkdir(parents=True, exist_ok=True)
    command = run_command(root, argv, timeout=timeout)
    write_model(log, command)
    if command.returncode != 0 or command.error is not None:
        raise ValueError(f"Workflow command failed; inspect {log.relative_to(root)}")


def export_project(
    root: Path, project_id: str, export_id: str, runner: NativeRunner = "auto",
) -> ReleaseExportReport:
    """Export explicit PCB settings into a fresh ignored directory for review."""
    root = root.resolve()
    project = selected_project(root, project_id)
    manifest = read_model(repo_path(root, project.config), ProjectManifest)
    if manifest.release_exports is None or manifest.kind.value != "pcb":
        raise ValueError("PCB release exports require project.json release_exports settings")
    directory = fresh_output(root, "exports", export_id)
    output = repo_path(root, (directory / "files").relative_to(root).as_posix())
    clean_source(root)
    cli = selected_cli(root, project_id, runner)
    dependency_path = (fresh_output(root, "release-deps", "mcp-export-" + export_id)
                       if cli is None else None)
    directory.mkdir(parents=True, exist_ok=False)
    dependencies: Path | None = None
    if dependency_path is not None:
        dependencies = dependency_path.relative_to(root)
        config = load_config(root, project.config)
        captured_command(root, (
            sys.executable, "-B", "-m", "tools.native_deps", "--root", str(root),
            "--image", config.image, "--output", dependencies.as_posix(),
        ), directory / "dependencies.command.json", 600)
    releasing.run_native(root, project, output, cli, dependencies, export_only=True)
    return verify_exports(
        root, releasing.reference(root, output / "exports.json"), source_state(root),
        project_id, project.config,
    )


def prepare_review(
    root: Path, project_id: str, release_id: str, runner: NativeRunner = "auto",
) -> ReleaseManifest:
    """Prepare only an engineering-review candidate, never an approval or production class."""
    root = root.resolve()
    selected_project(root, project_id)
    output = fresh_output(root, "releases", release_id)
    fresh_output(root, "release-deps", release_id)
    clean_source(root)
    cli = selected_cli(root, project_id, runner)
    if cli is not None:
        return releasing.prepare(
            root, release_id, (project_id,), release_class=ReleaseClass.ENGINEERING_REVIEW, cli=cli,
        )
    source = source_state(root)
    # The existing container preparation invokes pip with inherited stdout. Capture
    # that existing CLI in a subprocess so progress cannot corrupt the stdio protocol.
    captured_command(root, (
        sys.executable, "-B", "-m", "tools.release", "prepare", "--root", str(root),
        "--project", project_id, "--release-id", release_id,
        "--release-class", "engineering_review", "--format", "json",
    ), output.parent / f"{output.name}.command.json", 1800)
    candidate = read_model(
        repo_path(root, (output / "manifest.json").relative_to(root).as_posix()), ReleaseManifest,
    )
    if (candidate.release_id != release_id or candidate.projects != (project_id,)
            or candidate.release_class is not ReleaseClass.ENGINEERING_REVIEW
            or candidate.status is not ReleaseStatus.CANDIDATE or candidate.approval is not None
            or candidate.source_commit != source.commit or source_state(root) != source):
        raise ValueError("Prepared candidate differs from the requested review or current source")
    return candidate


def check_release(root: Path, manifest: str) -> ReleaseReadinessReport:
    return release_check(root, read_model(artifact_file(root, manifest), ReleaseManifest))


def package_release(root: Path, manifest: str, package_id: str) -> ReleasePackageReport:
    path = artifact_file(root, manifest)
    output = fresh_output(root, "packages", package_id, ".zip")
    return packaging.package(root, path.relative_to(root).as_posix(), output)


def verify_package(root: Path, archive: str) -> ReleasePackageReport:
    return packaging.verify(artifact_file(root, archive))


def restore_package(root: Path, archive: str, restore_id: str) -> ReleasePackageReport:
    path = artifact_file(root, archive)
    output = fresh_output(root, "restores", restore_id)
    output.parent.mkdir(parents=True, exist_ok=True)
    return packaging.restore(path, output)


def generate_views(
    root: Path, view_id: str, project_ids: tuple[str, ...] = (),
    product_ids: tuple[str, ...] = (), tags: tuple[str, ...] = (),
    exclude_tags: tuple[str, ...] = (),
) -> McpGenerationReport:
    """Render validated product/BOM projections into a fresh ignored review directory."""
    selector = ProjectSelector(
        project_ids=project_ids, product_ids=product_ids, tags=tags, excluded_tags=exclude_tags,
    )
    selected = resolve_project_ids(root, selector) if selector.active else None
    output = fresh_output(root, "views", view_id)
    output.mkdir(parents=True, exist_ok=False)
    names = generation.generate(root, output=output, selected_project_ids=selected)
    return McpGenerationReport(
        status="PASS", directory=output.relative_to(root).as_posix(),
        files=tuple((output / name).relative_to(root).as_posix() for name in names),
    )
