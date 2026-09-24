"""Turn existing import, portable, and native findings into repair guidance."""
from __future__ import annotations

import csv
import shlex
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

from .contracts import read_model, repo_path
from .discovery import load_config, load_registry
from .importing import import_project
from .models import (
    DiagnosticFinding,
    DiagnosticReport,
    PartsCatalog,
    PartStatus,
    PcbValidationContract,
    ProjectKind,
    ProjectManifest,
    ValidationSummary,
)
from .selection import ProjectSelector, resolve_project_ids

IMPORT_GUIDE = "docs/workflow/IMPORT_WORKFLOW.md"
CHECKS_GUIDE = "docs/workflow/CHECKS_AND_CI.md"
FIRST_BOARD_GUIDE = "docs/workflow/FIRST_BOARD.md"
BOM_GUIDE = "docs/workflow/BOM_POLICY.md"


def finding(
    severity: str, code: str, location: str, observed: str, action: str, guide: str
) -> DiagnosticFinding:
    return DiagnosticFinding.model_validate({
        "severity": severity, "code": code, "location": location,
        "observed": observed, "action": action, "guide": guide,
    })


def report(
    project_id: str, scope: str, findings: list[DiagnosticFinding], next_command: str
) -> DiagnosticReport:
    return DiagnosticReport.model_validate({
        "project_id": project_id,
        "scope": scope,
        "status": "NEEDS_WORK" if any(row.severity == "BLOCKING" for row in findings) else "PASS",
        "findings": tuple(findings),
        "next_command": next_command,
    })


def import_guidance(message: str) -> str:
    if "outside the selected project directory" in message or "is not in the subpath of" in message:
        return (
            "Move the referenced sheet and its dependencies into this project, update its "
            "Sheetfile path in KiCad, then preview the import again. Do not silently drop the sheet."
        )
    if "Missing schematic sheet" in message:
        return (
            "Find the intended sheet, correct its Sheetfile spelling and case in KiCad, "
            "and verify the file is present before retrying."
        )
    if "Nonportable repository path" in message or "Case-colliding" in message:
        return (
            "Rename the source path to a portable, unique spelling and update every KiCad "
            "reference to it before retrying."
        )
    if "variable" in message:
        return (
            "Resolve the sheet path to a reviewed project-local dependency, update Sheetfile "
            "in KiCad, and preview again."
        )
    return "Repair the named source or project selection, then rerun the dry-run import."


def diagnose_import(root: Path, source: Path, project_id: str, toolchain_id: str) -> DiagnosticReport:
    """Preview an import and group omissions without copying the candidate project."""
    preview = import_project(root, source, project_id, toolchain_id, dry_run=True)
    findings = [
        finding("BLOCKING", "IMPORT", source.as_posix(), issue,
                import_guidance(issue), IMPORT_GUIDE)
        for issue in preview.issues
    ]
    if preview.excluded:
        counts = Counter(preview.excluded.values())
        observed = "; ".join(f"{count} {reason}" for reason, count in sorted(counts.items()))
        findings.append(finding(
            "REVIEW", "IMPORT_EXCLUSIONS", source.parent.as_posix(), observed,
            "Review each exclusion in the import receipt after copying. Migrate any needed authored "
            "asset explicitly; leave working exports and local state out of Git.", IMPORT_GUIDE,
        ))
    command = (
        "python -B -m tools.template "
        + ("diagnose" if preview.status == "FAIL" else "import-project")
        + f" --source {shlex.quote(str(source))} --project-id {shlex.quote(project_id)} "
        + f"--toolchain {shlex.quote(toolchain_id)}"
    )
    return report(project_id, "import", findings, command)


def repository_guidance(issue: str) -> DiagnosticFinding:
    if issue.startswith("CAD_PATH: "):
        location, _, observed = issue.removeprefix("CAD_PATH: ").partition(": ")
        if "machine-local dependency" in observed:
            action = (
                "Move the actual asset into this project or a declared shared library, update "
                "the KiCad reference to a portable path, and verify it opens on another machine."
            )
        elif "undocumented path variable" in observed or "invalid versioned" in observed:
            action = (
                "Replace the legacy variable with the correct pinned KiCad library variable, "
                "or use a reviewed project-local asset via KIPRJMOD. Verify the target exists."
            )
        elif "case mismatch" in observed:
            action = (
                "Make the reference spelling match the file and every parent directory exactly; "
                "rerun the check on a case-sensitive host."
            )
        elif "missing dependency" in observed or "missing embedded model" in observed:
            action = (
                "Find and include the intended asset or correct the reference. Do not create "
                "a placeholder model solely to satisfy this check."
            )
        else:
            action = "Correct the named KiCad dependency and rerun the selected portable check."
        return finding("BLOCKING", "CAD_PATH", location or "KiCad source",
                       observed or issue, action, IMPORT_GUIDE)
    code, _, detail = issue.partition(": ")
    if code in {"TRACKED_GENERATED_OUTPUT", "TRACKED_LOCAL_STATE"}:
        action = (
            "Remove this generated/local file from the Git index, keep any needed local copy, "
            "and confirm the ignore rule and clean CI run."
        )
    elif code == "UNREGISTERED_DESIGN":
        action = "Register or import this separate native project as its own island."
    else:
        action = "Inspect the named repository input and correct the source or declaration."
    return finding("BLOCKING", code or "REPOSITORY", detail or "repository", issue,
                   action, CHECKS_GUIDE)


def portable_findings(root: Path, project_id: str) -> list[DiagnosticFinding]:
    """Run the same selected portable lane as CI, then explain its constituent failures."""
    from ..ci import project_static_pipeline

    result = project_static_pipeline(root, (project_id,))
    findings = [
        finding("BLOCKING", "REGISTRY", "project/catalog", issue,
                "Correct the named project manifest, inventory, or catalog record; rerun the "
                "selected check. Do not relax the contract to hide a source problem.", CHECKS_GUIDE)
        for issue in result.registry.issues
    ]
    findings.extend(repository_guidance(issue) for issue in result.repository.issues)
    findings.extend(
        finding("BLOCKING", issue.code, issue.location, issue.message,
                "Correct the authored product/catalog relationship, then regenerate and rerun "
                "the selected check.", "docs/workflow/PRODUCT_WORKFLOW.md")
        for issue in result.product.issues
    )
    findings.extend(
        finding("BLOCKING", "GENERATION", "generated view", issue,
                "Review the source records, regenerate ignored views with "
                "'python -B -m tools.hardware generate', then rerun the check.", CHECKS_GUIDE)
        for issue in result.generation.issues
    )
    for name, command in result.project_tests.commands.items():
        if command.returncode == 0:
            continue
        detail = command.error or "\n".join(command.stderr.strip().splitlines()[-3:])
        findings.append(finding(
            "BLOCKING", "PROJECT_TEST", name, detail or f"exit {command.returncode}",
            "Open the failing test and its assertion, repair the design or test fixture from "
            "the requirement, then rerun the selected CI lane.", "tests/README.md",
        ))
    registry = load_registry(root)
    project = next(item for item in registry.projects if item.id == project_id)
    manifest_path = repo_path(root, project.config)
    manifest = read_model(manifest_path, ProjectManifest)
    config = load_config(root, project.config)
    contract_path = repo_path(manifest_path.parent, manifest.checks).relative_to(root).as_posix()
    if config.kind is ProjectKind.PCB_ONLY:
        findings.append(finding(
            "REVIEW", "PCB_ONLY_SCOPE", project.config,
            "Board-only validation has no schematic, ERC, netlist, or native assembly BOM.",
            "Capture the board with DRC, then create or adopt an authoritative schematic "
            "before product or manufacturing release.", IMPORT_GUIDE,
        ))
    elif config.kind is ProjectKind.PCB and isinstance(config.validation, PcbValidationContract):
        if not config.validation.components:
            findings.append(finding(
                "BLOCKING", "EMPTY_COMPONENT_CONTRACT", contract_path,
                "The independent component contract is empty.",
                "Have an engineer author and review expected references, values, footprints "
                f"and nets in {contract_path} from design requirements; do not copy the "
                "export merely to make the check pass.", FIRST_BOARD_GUIDE,
            ))
        if not manifest.component_identity.required:
            findings.append(finding(
                "REVIEW", "PART_ID_SCOPE", project.config,
                "Controlled component identity is not yet required for this project.",
                "Assign stable PART_ID fields and reviewed catalog records before generating "
                "a purchasing BOM or preparing a release.", BOM_GUIDE,
            ))
        if manifest.release_exports is None:
            findings.append(finding(
                "REVIEW", "EXPORT_SETTINGS", project.config,
                "No release export settings are declared.",
                "Review layer, drill-origin and placement settings, then declare "
                "release_exports before a manufacturing export.",
                "docs/workflow/RELEASE_READINESS.md",
            ))
    return findings


def native_findings(path: Path, project_id: str, root: Path | None = None) -> list[DiagnosticFinding]:
    summary_path = path / "summary.json" if path.is_dir() else path
    try:
        summary = read_model(summary_path, ValidationSummary)
    except (OSError, ValueError) as exc:
        return [finding(
            "BLOCKING", "NATIVE_REPORT", str(summary_path), str(exc),
            "Select this project's native summary.json from a fresh KiCad check.", CHECKS_GUIDE,
        )]
    if summary.project_id != project_id:
        return [finding(
            "BLOCKING", "NATIVE_REPORT", str(summary_path),
            f"Report project is {summary.project_id!r}, expected {project_id!r}.",
            "Use the report from the selected project and exact checked source.", CHECKS_GUIDE,
        )]
    findings: list[DiagnosticFinding] = []
    if root is not None:
        scope = summary.checks.get("source_scope")
        if scope is not None and scope.source_hashes:
            from ..validate import hashes

            try:
                registry = load_registry(root)
                project = next(item for item in registry.projects if item.id == project_id)
                config = load_config(root, project.config)
                current = hashes(root, config.source_roots)
                if current != scope.source_hashes:
                    findings.append(finding(
                        "BLOCKING", "STALE_NATIVE_REPORT", str(summary_path),
                        "The declared design files differ from those checked in this native report.",
                        "Run a fresh native check against the current source before using its "
                        "ERC, DRC or netlist findings to guide repairs.", CHECKS_GUIDE,
                    ))
            except (OSError, ValueError, StopIteration) as exc:
                findings.append(finding(
                    "BLOCKING", "NATIVE_SOURCE", str(summary_path), str(exc),
                    "Repair project discovery or the declared source inventory, then rerun "
                    "native validation.", CHECKS_GUIDE,
                ))
    for name, check in summary.checks.items():
        if check.status == "PASS":
            continue
        observed = check.error or f"{name} status is {check.status}"
        if name in {"erc", "drc"}:
            if "Disabled-check inventory changed" in observed:
                action = (
                    "In KiCad Schematic Setup (ERC) or Board Setup (DRC), enable the named "
                    "disabled checks, then resolve resulting findings. Do not change the "
                    "development contract to mirror disabled defaults."
                )
            else:
                action = (
                    f"Inspect {summary_path.parent / (name + '.json')} for each violation, "
                    "unconnected item, parity error or exclusion; correct the design and rerun "
                    "into a fresh output directory."
                )
            guide = IMPORT_GUIDE
        elif name == "netlist":
            action = (
                "Compare the native export with independently reviewed component and net "
                "expectations in tests/contract.json. Fix the design or correct a reviewed "
                "requirement; do not blindly copy observed nets into the contract."
            )
            guide = "tests/README.md"
        elif name in {"preflight", "toolchain", "source_scope"}:
            action = (
                "Run 'python -B -m tools.template doctor --native --toolchain <id>', "
                "check the manifest's exact KiCad version and required inputs, then rerun."
            )
            guide = CHECKS_GUIDE
        elif name == "source_unchanged":
            action = "Close KiCad, preserve the changed source, and rerun from a stable source state."
            guide = CHECKS_GUIDE
        else:
            action = "Inspect the named command evidence and correct the source or export setting."
            guide = CHECKS_GUIDE
        location = summary_path.parent / f"{name}.json" if name in {"erc", "drc"} else summary_path
        findings.append(finding("BLOCKING", "NATIVE_" + name.upper(),
                                str(location), observed, action, guide))
    return findings


def bom_findings(root: Path, path: Path) -> list[DiagnosticFinding]:
    """Explain native BOM identity gaps without changing a schematic or catalog."""
    try:
        registry = load_registry(root)
        parts = {
            part.id: part for part in read_model(
                repo_path(root, registry.catalogs.parts), PartsCatalog
            ).parts
        }
        with path.open(newline="", encoding="utf-8-sig") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != ["Reference", "Value", "Footprint", "PartID", "DNP"]:
                raise ValueError("Expected native BOM columns Reference, Value, Footprint, PartID, DNP")
            rows = list(reader)
        if not rows:
            raise ValueError("Native BOM has no fitted components")
        if any(None in row or not row["Reference"] or any(value is None for value in row.values())
               for row in rows):
            raise ValueError("Native BOM contains missing or extra cells")
    except (OSError, ValueError, csv.Error) as exc:
        return [finding("BLOCKING", "BOM_INPUT", str(path), str(exc),
                        "Select the native assembly/bom.csv from a successful schematic export.",
                        BOM_GUIDE)]
    missing = [row["Reference"] for row in rows if not row["PartID"]]
    unknown = [row["Reference"] for row in rows if row["PartID"] and row["PartID"] not in parts]
    training = [row["Reference"] for row in rows
                if row["PartID"] in parts and parts[row["PartID"]].status is PartStatus.TRAINING]
    findings: list[DiagnosticFinding] = []
    if missing or unknown:
        observed = f"{len(missing)} missing PART_ID; {len(unknown)} unknown catalog ID"
        examples = ", ".join((missing + unknown)[:8])
        findings.append(finding(
            "BLOCKING", "BOM_PART_ID", str(path), f"{observed}; references: {examples}",
            "Assign a stable PART_ID in the schematic for each fitted component and add "
            "reviewed records to catalog/parts.json. Regenerate the native BOM; never hand-edit "
            "the exported CSV.", BOM_GUIDE,
        ))
    if training:
        findings.append(finding(
            "REVIEW", "BOM_TRAINING_PART", str(path),
            f"{len(training)} references use not-for-manufacture catalog records.",
            "Replace training placeholders with reviewed sourceable parts before release.", BOM_GUIDE,
        ))
    return findings


def bom_binding_findings(
    root: Path, project_id: str, bom: Path, native_report: Path | None
) -> list[DiagnosticFinding]:
    """Bind BOM rows to a hashed netlist from this project's current native run."""
    if native_report is None:
        return [finding(
            "BLOCKING", "BOM_BINDING", str(bom), "No project native report was supplied.",
            "Run native validation for this project and pass its project summary.json "
            "with --native-report alongside --bom.", BOM_GUIDE,
        )]
    summary_path = native_report / "summary.json" if native_report.is_dir() else native_report
    try:
        from ..validate import hashes, read_netlist
        from .evidence import digest

        summary = read_model(summary_path, ValidationSummary)
        if summary.project_id != project_id:
            raise ValueError(f"Native report belongs to {summary.project_id!r}, not {project_id!r}")
        registry = load_registry(root)
        project = next(item for item in registry.projects if item.id == project_id)
        config = load_config(root, project.config)
        scope = summary.checks.get("source_scope")
        if scope is None or not scope.source_hashes or hashes(root, config.source_roots) != scope.source_hashes:
            raise ValueError("Native report does not match the current declared design files")
        netlist_path = summary_path.parent / "netlist.xml"
        if summary.artifacts_sha256.get("netlist.xml") != digest(netlist_path):
            raise ValueError("Native netlist is missing or differs from the report inventory")
        netlist = read_netlist(netlist_path)
        tree = ET.parse(netlist_path).getroot()
        expected_references = {
            component.attrib["ref"]
            for component in tree.findall("./components/comp")
            if not {property_.get("name") for property_ in component.findall("property")}
            & {"exclude_from_bom", "dnp"}
        }
        with bom.open(newline="", encoding="utf-8-sig") as stream:
            rows = list(csv.DictReader(stream))
        if not rows:
            raise ValueError("Native BOM has no fitted references")
        references: list[str] = []
        for row in rows:
            reference = row.get("Reference")
            if not isinstance(reference, str) or not reference:
                raise ValueError("Native BOM has a missing reference")
            references.append(reference)
        if len(set(references)) != len(references):
            raise ValueError("Native BOM repeats a reference")
        if set(references) != expected_references:
            raise ValueError(
                "BOM fitted-reference coverage differs from this project's netlist; "
                f"missing={sorted(expected_references - set(references))[:8]}, "
                f"extra={sorted(set(references) - expected_references)[:8]}"
            )
        mismatched = [
            str(reference) for reference, row in zip(references, rows)
            if (component := netlist.components.get(str(reference))) is None
            or row.get("Value") != component.value
            or row.get("Footprint") != component.footprint
            or (row.get("PartID") or None) != component.part_id
        ]
        if mismatched:
            raise ValueError(
                "BOM rows differ from this project's native netlist: "
                + ", ".join(mismatched[:8])
            )
    except (OSError, ValueError, KeyError, TypeError, StopIteration, csv.Error, ET.ParseError) as exc:
        return [finding(
            "BLOCKING", "BOM_BINDING", str(bom), str(exc),
            "Select a fresh BOM from this project's schematic and its matching native "
            "summary. Do not relabel or hand-edit an export from another board.", BOM_GUIDE,
        )]
    return []


def diagnose_project(
    root: Path, project_id: str, native_report: Path | None = None,
    bom: Path | None = None,
) -> DiagnosticReport:
    """Give one project a portable check and optional native/BOM follow-up."""
    root = root.resolve()
    try:
        selected = resolve_project_ids(root, ProjectSelector(project_ids=(project_id,)))
        findings = portable_findings(root, selected[0])
    except (OSError, ValueError, TypeError) as exc:
        findings = [finding(
            "BLOCKING", "DISCOVERY", "catalog/projects.json", str(exc),
            "Repair project discovery or the selected project ID, then rerun diagnostics.",
            CHECKS_GUIDE,
        )]
    if native_report is not None:
        findings.extend(native_findings(native_report, project_id, root))
    if bom is not None:
        findings.extend(bom_binding_findings(root, project_id, bom, native_report))
        findings.extend(bom_findings(root, bom))
    return report(project_id, "project", findings,
                  f"python -B -m tools.ci --project {shlex.quote(project_id)}")


def format_text(result: DiagnosticReport) -> str:
    """A short human-readable view with every repair next to its observed finding."""
    lines = [f"{result.status}: {result.scope} diagnostics for {result.project_id}"]
    for row in result.findings:
        lines.extend((
            f"[{row.severity}] {row.code} — {row.location}",
            f"  Observed: {row.observed}",
            f"  Fix: {row.action}",
            f"  Guide: {row.guide}",
        ))
    if not result.findings:
        lines.append("No diagnosed problems in the selected scope.")
    lines.extend((f"Next: {result.next_command}",
                  "Diagnostic success does not approve the electrical design or a release."))
    return "\n".join(lines)
