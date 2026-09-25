"""Explicit, source-preserving assignment of reviewed PCB 3D model files."""
from __future__ import annotations

import difflib
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Literal

from pydantic import Field

from .contracts import read_model, repo_path
from .diagnostic_journal import DiagnosticJournal
from .discovery import load_config, load_registry
from .model_inventory import (
    _atoms,  # pyright: ignore[reportPrivateUsage]
    _children,  # pyright: ignore[reportPrivateUsage]
    inspect_models,
)
from .models import Digest, Identifier, ProjectKind, ProjectManifest, RepositoryPath, StrictModel

AUTHORABLE_SUFFIXES = frozenset({".step", ".stp", ".igs", ".iges", ".wrl"})


class ModelMapAssignment(StrictModel):
    reference: str = Field(min_length=1)
    model: str
    candidate_assets: tuple[RepositoryPath, ...] = ()


class ModelMap(StrictModel):
    schema_version: Literal["1"] = "1"
    project_id: Identifier
    board_sha256: Digest
    manifest_sha256: Digest
    assignments: tuple[ModelMapAssignment, ...] = Field(min_length=1)


class ModelPopulationReport(StrictModel):
    schema_version: Literal["1"] = "1"
    status: Literal["DRAFT", "PLAN", "APPLIED", "FAIL", "ERROR"]
    project_id: Identifier
    run_directory: str
    board: RepositoryPath | None = None
    manifest: RepositoryPath | None = None
    board_sha256: Digest | None = None
    manifest_sha256: Digest | None = None
    draft_map: str | None = None
    model_sha256: dict[RepositoryPath, Digest] = Field(default_factory=dict)
    board_diff: str = ""
    manifest_diff: str = ""
    review_notice: str = (
        "A mapped path does not verify package identity, dimensions, orientation, "
        "offset or enclosure fit; inspect the generated geometry in KiCad."
    )
    next_commands: tuple[str, ...] = ()
    error: str | None = None


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _diff(before: str, after: str, name: str) -> str:
    return "".join(difflib.unified_diff(
        before.splitlines(keepends=True), after.splitlines(keepends=True),
        fromfile=f"a/{name}", tofile=f"b/{name}",
    ))


def _model_path(root: Path, manifest_dir: Path, board_dir: Path,
                manifest: ProjectManifest, name: str) -> tuple[Path, str, str, str]:
    if Path(name).suffix.casefold() not in AUTHORABLE_SUFFIXES:
        raise ValueError(
            f"{name}: assign STEP/STP/IGS/IGES/WRL source; IDF and exports are not viewable model inputs"
        )
    if "$" in name:
        raise ValueError(f"{name}: model filenames must not contain KiCad variable syntax")
    path = repo_path(root, name)
    if not path.is_file():
        raise ValueError(f"{name}: reviewed model file is missing")
    local_roots = tuple(repo_path(manifest_dir, item) for item in manifest.source_roots)
    shared_roots = tuple(repo_path(root, item) for item in manifest.shared_source_roots)
    local = any(path.is_relative_to(source) for source in local_roots)
    shared = any(path.is_relative_to(source) for source in shared_roots)
    if local == shared:
        raise ValueError(
            f"{name}: model must belong to exactly one declared project-local or shared source root"
        )
    inventory_field = "required_inputs" if local else "shared_inputs"
    inventory_name = (path.relative_to(manifest_dir).as_posix() if local else name)
    relative = Path(os.path.relpath(path, board_dir)).as_posix()
    return path, inventory_field, inventory_name, "${KIPRJMOD}/" + relative


def _board_edits(source: str, assignments: ModelMap,
                 model_references: dict[str, str]) -> str:
    roots = _children(source, 0, len(source))
    if len(roots) != 1 or _atoms(source, roots[0])[:1] != ("kicad_pcb",):
        raise ValueError("Expected exactly one kicad_pcb root expression")
    nodes = _children(source, roots[0].start + 1, roots[0].end - 1)
    wanted = {item.reference for item in assignments.assignments}
    found: dict[str, tuple[int, str]] = {}
    for node in nodes:
        header = _atoms(source, node)
        if not header or header[0] not in {"footprint", "module"}:
            continue
        reference = ""
        models = 0
        for child in _children(source, node.start + 1, node.end - 1):
            atoms = _atoms(source, child)
            if len(atoms) > 2 and (
                atoms[:2] == ("property", "Reference")
                or (atoms[:2] == ("fp_text", "reference") and not reference)
            ):
                reference = atoms[2]
            elif atoms and atoms[0] == "model":
                models += 1
        if reference not in wanted:
            continue
        if reference in found:
            raise ValueError(f"Duplicate placed footprint reference {reference!r}; cannot assign safely")
        if models:
            raise ValueError(
                f"{reference}: footprint already has a model assignment; edit it in KiCad instead"
            )
        reference_path = model_references[reference]
        expression = (
            f'(model "{reference_path}" (offset (xyz 0 0 0)) '
            '(scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))'
        )
        # Insert at the containing footprint's closing parenthesis. Leave all
        # existing KiCad source bytes and their ordering untouched.
        close = node.end - 1
        line_start = source.rfind("\n", 0, close) + 1
        before_close = source[line_start:close]
        if before_close.strip():
            opening_line = source.rfind("\n", 0, node.start) + 1
            opening_indent = source[opening_line:node.start]
            if opening_indent.strip():
                opening_indent = ""
            insertion = f"\n{opening_indent}  {expression}\n{opening_indent}"
        else:
            insertion = f"  {expression}\n{before_close}"
        found[reference] = (close, insertion)
    missing = sorted(wanted - set(found))
    if missing:
        raise ValueError(f"No unique placed footprint for reference(s): {', '.join(missing)}")
    updated = source
    for position, insertion in sorted(found.values(), reverse=True):
        updated = updated[:position] + insertion + updated[position:]
    # A malformed insertion must never become authoritative source.
    roots = _children(updated, 0, len(updated))
    if len(roots) != 1 or _atoms(updated, roots[0])[:1] != ("kicad_pcb",):
        raise ValueError("The proposed board edit did not retain a kicad_pcb root")
    return updated


def _new_manifest(source: str, manifest: ProjectManifest,
                  additions: dict[str, set[str]]) -> str:
    raw = json.loads(source)
    for field in ("required_inputs", "shared_inputs"):
        added = additions[field]
        if not added:
            continue
        previous = getattr(manifest, field)
        raw[field] = sorted(set(previous) | added)
    updated = json.dumps(raw, indent=2, ensure_ascii=False) + "\n"
    ProjectManifest.model_validate_json(updated, strict=True)
    return updated


def _replace_bytes(path: Path, value: bytes) -> None:
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.model-map-", dir=path.parent)
    staged = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(staged, path.stat().st_mode)
        os.replace(staged, path)
    finally:
        staged.unlink(missing_ok=True)


def render_population_text(report: ModelPopulationReport) -> str:
    lines = [
        f"3D model population: {report.status}",
        f"Project: {report.project_id}",
        f"Receipt: {report.run_directory}",
    ]
    if report.board:
        lines.append(f"Board: {report.board}")
    if report.manifest:
        lines.append(f"Manifest: {report.manifest}")
    if report.draft_map:
        lines.append(f"Draft map: {report.draft_map}")
    if report.status == "DRAFT":
        lines.append("Choose reviewed model paths; remove footprints that do not need models.")
    if report.status == "PLAN":
        lines.append("Review board.diff and manifest.diff, then repeat with --apply.")
    lines.append(report.review_notice)
    if report.error:
        lines.append(f"Finding: {report.error}")
    for command in report.next_commands:
        lines.append(f"Next: {command}")
    return "\n".join(lines)


def populate_models(root: Path, project_id: str, map_path: Path, *,
                    apply: bool = False, output: Path | None = None) -> ModelPopulationReport:
    """Plan or apply only explicit, hash-bound model references and inventory entries."""
    root = root.resolve()
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", project_id) is None:
        raise ValueError("Project ID must use letters, digits, periods, underscores or hyphens")
    if output is not None:
        output = (root / output).resolve() if not output.is_absolute() else output.resolve()
        if not output.is_relative_to(root / "build"):
            raise ValueError("3D output must be under this repository's ignored build/")
    journal = DiagnosticJournal(root, project_id, output, label="model-map")
    board_name: str | None = None
    manifest_name: str | None = None
    board_digest: str | None = None
    manifest_digest: str | None = None
    model_hashes: dict[str, str] = {}
    board_diff = ""
    manifest_diff = ""
    try:
        with journal.stage("map-and-project"):
            spec = read_model(map_path if map_path.is_absolute() else root / map_path, ModelMap)
            if spec.project_id != project_id:
                raise ValueError(
                    f"Map project {spec.project_id!r} differs from selected project {project_id!r}"
                )
            refs = [item.reference for item in spec.assignments]
            if len(refs) != len(set(refs)):
                raise ValueError("Map has duplicate footprint references")
            record = next((item for item in load_registry(root).projects if item.id == project_id), None)
            if record is None:
                raise ValueError(f"Unknown project {project_id!r}; run tools.template list")
            if record.kind not in {ProjectKind.PCB, ProjectKind.PCB_ONLY}:
                raise ValueError(f"Project {project_id} has no PCB")
            manifest_name = record.config
            manifest_path = repo_path(root, manifest_name)
            manifest = read_model(manifest_path, ProjectManifest)
            board_path = repo_path(root, record.project).with_suffix(".kicad_pcb")
            board_name = board_path.relative_to(root).as_posix()
            if not board_path.is_file():
                raise ValueError(f"PCB source is missing: {board_name}")
            board_before = board_path.read_bytes()
            manifest_before = manifest_path.read_bytes()
            board_digest = _digest(board_before)
            manifest_digest = _digest(manifest_before)
            if spec.board_sha256 != board_digest:
                raise ValueError(
                    f"Board changed since map review: expected {spec.board_sha256}, got {board_digest}"
                )
            if spec.manifest_sha256 != manifest_digest:
                raise ValueError(
                    "Project manifest changed since map review; create and review a fresh map"
                )
        with journal.stage("source-plan"):
            additions: dict[str, set[str]] = {"required_inputs": set(), "shared_inputs": set()}
            references: dict[str, str] = {}
            for item in spec.assignments:
                if not item.model:
                    raise ValueError(
                        f"{item.reference}: choose a reviewed model path or remove this "
                        "unneeded assignment from the draft map"
                    )
                path, field, inventory_name, reference = _model_path(
                    root, manifest_path.parent, board_path.parent, manifest, item.model,
                )
                additions[field].add(inventory_name)
                references[item.reference] = reference
                model_hashes[item.model] = _digest(path.read_bytes())
            source = board_before.decode("utf-8")
            manifest_source = manifest_before.decode("utf-8")
            board_after = _board_edits(source, spec, references).encode("utf-8")
            manifest_after = _new_manifest(manifest_source, manifest, additions).encode("utf-8")
            board_diff = _diff(source, board_after.decode("utf-8"), board_name)
            manifest_diff = _diff(manifest_source, manifest_after.decode("utf-8"), manifest_name)
            (journal.directory / "board.diff").write_text(board_diff, encoding="utf-8")
            (journal.directory / "manifest.diff").write_text(manifest_diff, encoding="utf-8")
        status: Literal["DRAFT", "PLAN", "APPLIED", "FAIL", "ERROR"] = "PLAN"
        if apply:
            with journal.stage("apply"):
                if _digest(board_path.read_bytes()) != board_digest:
                    raise ValueError("Board changed after planning; no edits applied")
                if _digest(manifest_path.read_bytes()) != manifest_digest:
                    raise ValueError("Manifest changed after planning; no edits applied")
                for name, digest in model_hashes.items():
                    if _digest(repo_path(root, name).read_bytes()) != digest:
                        raise ValueError(f"Model source changed after planning: {name}")
                try:
                    _replace_bytes(board_path, board_after)
                    _replace_bytes(manifest_path, manifest_after)
                except OSError:
                    if _digest(board_path.read_bytes()) == _digest(board_after):
                        _replace_bytes(board_path, board_before)
                    raise
                status = "APPLIED"
        next_commands = (
            f"python -B -m tools.verify --project {project_id} --depth native",
            f"python -B -m tools.visualize --project {project_id} --check-models",
            f"python -B -m tools.visualize --project {project_id}",
        ) if apply else (
            (
                f"python -B -m tools.visualize --project {project_id} --map-models "
                f"{map_path} --apply"
            ),
        )
        result = ModelPopulationReport(
            status=status, project_id=project_id, run_directory=str(journal.directory),
            board=board_name, manifest=manifest_name, board_sha256=board_digest,
            manifest_sha256=manifest_digest, model_sha256=model_hashes,
            board_diff=board_diff, manifest_diff=manifest_diff,
            next_commands=next_commands,
        )
    except (OSError, ValueError, UnicodeError) as exc:
        result = ModelPopulationReport(
            status="FAIL", project_id=project_id, run_directory=str(journal.directory),
            board=board_name, manifest=manifest_name, board_sha256=board_digest,
            manifest_sha256=manifest_digest, model_sha256=model_hashes,
            board_diff=board_diff, manifest_diff=manifest_diff, error=str(exc),
        )
    except Exception as exc:  # noqa: BLE001 - retain a tooling-fault receipt for agent diagnosis
        journal.fail(exc)
        result = ModelPopulationReport(
            status="ERROR", project_id=project_id, run_directory=str(journal.directory),
            board=board_name, manifest=manifest_name, board_sha256=board_digest,
            manifest_sha256=manifest_digest, model_sha256=model_hashes,
            board_diff=board_diff, manifest_diff=manifest_diff, error=str(exc),
        )
    journal.finish_named("model-population", result, render_population_text(result), result.status)
    return result


def init_model_map(root: Path, project_id: str, destination: Path, *,
                   output: Path | None = None) -> ModelPopulationReport:
    """Write an ignored, unapproved map draft with hashes and candidate hints."""
    root = root.resolve()
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", project_id) is None:
        raise ValueError("Project ID must use letters, digits, periods, underscores or hyphens")
    destination = (root / destination).resolve() if not destination.is_absolute() else destination.resolve()
    if not destination.is_relative_to(root / "build") or destination.suffix != ".json":
        raise ValueError("Draft model map must be a JSON file under this repository's ignored build/")
    if output is not None:
        output = (root / output).resolve() if not output.is_absolute() else output.resolve()
        if not output.is_relative_to(root / "build"):
            raise ValueError("3D output must be under this repository's ignored build/")
    journal = DiagnosticJournal(root, project_id, output, label="model-map")
    board_name: str | None = None
    manifest_name: str | None = None
    board_digest: str | None = None
    manifest_digest: str | None = None
    try:
        with journal.stage("draft-map"):
            record = next((item for item in load_registry(root).projects if item.id == project_id), None)
            if record is None or record.kind not in {ProjectKind.PCB, ProjectKind.PCB_ONLY}:
                raise ValueError(f"Select a registered PCB or PCB-only project: {project_id}")
            manifest_name = record.config
            manifest_path = repo_path(root, manifest_name)
            board_path = repo_path(root, record.project).with_suffix(".kicad_pcb")
            board_name = board_path.relative_to(root).as_posix()
            if not board_path.is_file():
                raise ValueError(f"PCB source is missing: {board_name}")
            board_digest = _digest(board_path.read_bytes())
            manifest_digest = _digest(manifest_path.read_bytes())
            inventory = inspect_models(root, load_config(root, manifest_name))
            unassigned = tuple(item for item in inventory.footprints if not item.models)
            if not unassigned:
                raise ValueError("This board has no unassigned footprints to draft")
            refs = [item.reference for item in unassigned]
            if len(refs) != len(set(refs)) or any(ref.startswith("<unknown") for ref in refs):
                raise ValueError("Board has duplicate or unreadable references; repair it in KiCad")
            payload = {
                "schema_version": "1", "project_id": project_id,
                "board_sha256": board_digest, "manifest_sha256": manifest_digest,
                "assignments": [
                    {
                        "reference": item.reference, "model": "",
                        "candidate_assets": list(item.candidate_assets),
                    }
                    for item in unassigned
                ],
            }
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("x", encoding="utf-8") as stream:
                json.dump(payload, stream, indent=2)
                stream.write("\n")
            journal.event("draft-map", "SAVED", str(destination))
        result = ModelPopulationReport(
            status="DRAFT", project_id=project_id, run_directory=str(journal.directory),
            board=board_name, manifest=manifest_name, board_sha256=board_digest,
            manifest_sha256=manifest_digest, draft_map=str(destination),
            next_commands=(
                "Choose exact reviewed model files for desired references in the draft map.",
                f"python -B -m tools.visualize --project {project_id} --map-models {destination}",
            ),
        )
    except (OSError, ValueError, UnicodeError) as exc:
        result = ModelPopulationReport(
            status="FAIL", project_id=project_id, run_directory=str(journal.directory),
            board=board_name, manifest=manifest_name, board_sha256=board_digest,
            manifest_sha256=manifest_digest, error=str(exc),
        )
    except Exception as exc:  # noqa: BLE001 - retain a tooling-fault receipt for agent diagnosis
        journal.fail(exc)
        result = ModelPopulationReport(
            status="ERROR", project_id=project_id, run_directory=str(journal.directory),
            board=board_name, manifest=manifest_name, board_sha256=board_digest,
            manifest_sha256=manifest_digest, error=str(exc),
        )
    journal.finish_named("model-population", result, render_population_text(result), result.status)
    return result
