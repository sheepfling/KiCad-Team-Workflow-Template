"""Bounded parts-review exports and reviewed purchasing preference edits for MCP."""
from __future__ import annotations

from pathlib import Path

from . import contract_coach, mcp_files, parts_workflow
from .contracts import parse_model_text, repo_path
from .doctor import NativeRunner
from .mcp_workflow import artifact_file, fresh_output, native_summary_path, selected_project
from .models import McpPurchasingPreferencesResult, PurchasingPreferences, PurchasingReport


def preferences_file(root: Path, project_id: str, value: str | None) -> Path | None:
    """Use only selected-island authored preferences or bounded temporary artifacts."""
    project = selected_project(root, project_id)
    docs = repo_path(root, (Path(project.config).parent / "docs").as_posix())
    if value is None:
        default = repo_path(root, (docs / "purchasing.json").relative_to(root).as_posix())
        if default.exists() and not default.is_file():
            raise ValueError("Purchasing preferences must be a regular JSON file")
        return None
    path = repo_path(root, value)
    if not path.is_relative_to(docs):
        path = artifact_file(root, value)
    if path.suffix != ".json" or not path.is_file():
        raise ValueError("Select a preferences JSON in this project's docs/ or build artifacts")
    return path


def prepare_parts(
    root: Path, project_id: str, view_id: str, native_summary: str | None = None,
    preferences: str | None = None, boards: int | None = None,
    spare_percent: int | None = None, spare_minimum: int | None = None,
    runner: NativeRunner = "auto", *, allow_checks: bool = False,
) -> PurchasingReport:
    """Create the CLI's source-bound checklist and conditional order CSV in fresh output."""
    selected_project(root, project_id)
    if native_summary is None and not allow_checks:
        raise ValueError("Fresh parts capture requires --allow-checks as well as --allow-exports; "
                         "otherwise supply a saved native_summary")
    if runner not in {"auto", "local", "container"}:
        raise ValueError(f"Unknown native runner: {runner}")
    if native_summary is not None and runner != "auto":
        raise ValueError("runner applies only to fresh capture, not saved native_summary")
    summary = None if native_summary is None else native_summary_path(root, native_summary)
    requested = preferences_file(root, project_id, preferences)
    output = fresh_output(root, "parts", view_id)
    output.mkdir(parents=True, exist_ok=False)
    native_runner = (
        contract_coach.LocalNetlistRunner("kicad-cli") if runner == "local"
        else contract_coach.ContainerNetlistRunner() if runner == "container"
        else contract_coach.AutoNetlistRunner("kicad-cli")
    )
    report = parts_workflow.prepare(
        root, project_id, output, native_runner, summary, requested,
        boards, spare_percent, spare_minimum,
    )
    parts_workflow.save_report(output, report)
    return report


def save_parts_preferences(
    root: Path, project_id: str, preferences: PurchasingPreferences,
    expected_sha256: str | None = None,
) -> McpPurchasingPreferencesResult:
    """Save explicit preferences at the fixed authored path; updates need a current hash."""
    text = preferences.model_dump_json(indent=2) + "\n"
    if len(text) > mcp_files.MAX_CHUNK:
        raise ValueError("Preferences exceed the supported edit size")
    project = selected_project(root, project_id)
    relative = (Path(project.config).parent / "docs/purchasing.json").as_posix()
    path = repo_path(root, relative)
    before = None
    if path.exists():
        if expected_sha256 is None:
            raise ValueError("Existing preferences require expected_sha256 from read_project_file")
        previous = mcp_files.read_project_file(root, project_id, "docs/purchasing.json")
        if previous.text is None or previous.truncated:
            raise ValueError("Preferences exceed the supported edit size")
        if previous.sha256 != expected_sha256:
            raise ValueError("Source hash mismatch; read the current preferences and review again")
        before = previous.sha256
        if previous.text != text:
            mcp_files.apply_project_edit(
                root, project_id, "docs/purchasing.json", expected_sha256, previous.text, text,
            )
        status = "UPDATED"
    else:
        if expected_sha256 is not None:
            raise ValueError("Preferences no longer exist; review a new creation without a digest")
        parts_workflow.init_preferences(root, project_id, path, preferences)
        status = "CREATED"
    content = mcp_files.read_project_file(root, project_id, "docs/purchasing.json")
    if content.text is None or content.truncated:
        raise ValueError("Preferences readback exceeded the supported size")
    saved = parse_model_text(content.text, PurchasingPreferences)
    if saved != preferences:
        raise ValueError("Preferences changed during readback; reread before continuing")
    return McpPurchasingPreferencesResult(
        project_id=project_id, path=relative, status=status, before_sha256=before,
        after_sha256=content.sha256, readback_sha256=content.sha256, preferences=saved,
    )
