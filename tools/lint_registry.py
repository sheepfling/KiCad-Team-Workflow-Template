"""Fail-closed static lint for declared KiCad projects and controlled catalogs."""
from __future__ import annotations

import argparse
import hashlib
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Protocol, TypeVar

from .hwrepo.contracts import read_model, repo_path, write_model
from .hwrepo.discovery import load_config, load_registry, settings
from .hwrepo.models import (
    GovernanceLintReport,
    GovernanceRecord,
    InterfacesCatalog,
    LibrariesCatalog,
    PartsCatalog,
    PartStatus,
    PcbValidationContract,
    ProjectKind,
    ProjectManifest,
    ReleaseClass,
    ReleasePoliciesCatalog,
    SchematicValidationContract,
    TeamPolicy,
    ToolchainsCatalog,
)
from .validate import hashes


class Identified(Protocol):
    id: str


Record = TypeVar("Record", bound=Identified)


def records_by_id(
    records: Iterable[Record], label: str, issues: list[str]
) -> dict[str, Record]:
    result: dict[str, Record] = {}
    casefolded: set[str] = set()
    for record in records:
        if record.id.casefold() in casefolded:
            issues.append(f"{label}: duplicate id {record.id!r}")
        casefolded.add(record.id.casefold())
        result[record.id] = record
    return result


def reviewed_value(value: str) -> bool:
    """Reject empty and template/training placeholders in production records."""
    if not value.strip():
        return False
    normalized: str = value.casefold().replace("-", " ").replace("_", " ")
    return not any(marker in normalized for marker in ("replace with", "unspecified", "do not purchase", "training", "example.invalid", "unknown", "your name", "todo"))


def lint_governance_record(
    root: Path, value: str | None, identifier: str, issues: list[str]
) -> None:
    """Require a real multi-role GitHub governance record for production projects."""
    if value is None:
        issues.append(f"project {identifier}: governance record is missing")
        return
    try:
        path = repo_path(root, value)
    except ValueError as exc:
        issues.append(f"project {identifier}: governance record: {exc}")
        return
    if not path.is_file():
        issues.append(f"project {identifier}: governance record is missing")
        return
    try:
        record = read_model(path, GovernanceRecord)
        policy = read_model(root / "catalog/team-policy.json", TeamPolicy)
    except (OSError, ValueError) as exc:
        issues.append(f"project {identifier}: invalid governance record: {exc}")
        return
    if not reviewed_value(record.branch):
        issues.append(f"project {identifier}: governance record needs a protected branch")
    if not record.required_status_checks or any(
        not reviewed_value(check) for check in record.required_status_checks
    ):
        issues.append(f"project {identifier}: governance record needs reviewed required_status_checks")
    people: set[str] = set()
    for field, assigned in (
        ("authors", record.authors),
        ("reviewers", record.reviewers),
        ("integrators", record.integrators),
    ):
        if not assigned or any(not reviewed_value(person) for person in assigned):
            issues.append(f"project {identifier}: governance record needs reviewed {field}")
            continue
        people.update(person.casefold() for person in assigned)
    if len(people) < policy.minimum_actors:
        issues.append(f"project {identifier}: governance record needs {policy.minimum_actors} distinct actors")
    if policy.independent_review and (
        {person.casefold() for person in record.authors}
        & {person.casefold() for person in record.reviewers}
    ):
        issues.append(f"project {identifier}: reviewers must be independent of authors")
    if not set(policy.required_status_checks) <= set(record.required_status_checks):
        issues.append(f"project {identifier}: governance record omits team-required status checks")
    for field, assigned in (
        ("release_authorities", record.release_authorities),
        ("branch_protection_evidence", record.branch_protection_evidence),
        ("branch_protection_verified_at", (record.branch_protection_verified_at,)),
    ):
        valid = bool(assigned) and all(reviewed_value(item) for item in assigned)
        if not valid:
            issues.append(f"project {identifier}: governance record needs reviewed {field}")


def lint(
    root: Path, selected: list[str] | None = None
) -> GovernanceLintReport:
    """Lint all declared project inputs or an explicit project subset."""
    root = root.resolve()
    issues: list[str] = []
    requested = tuple(selected or ())
    try:
        registry = load_registry(root)
        read_model(root / "catalog/team-policy.json", TeamPolicy)
        parts = records_by_id(
            read_model(repo_path(root, registry.catalogs.parts), PartsCatalog).parts,
            "parts catalog",
            issues,
        )
        interfaces = records_by_id(
            read_model(
                repo_path(root, registry.catalogs.interfaces), InterfacesCatalog
            ).interfaces,
            "interface catalog",
            issues,
        )
        libraries = records_by_id(
            read_model(
                repo_path(root, registry.catalogs.libraries), LibrariesCatalog
            ).libraries,
            "library catalog",
            issues,
        )
        toolchains = records_by_id(
            read_model(
                repo_path(root, registry.catalogs.toolchains), ToolchainsCatalog
            ).toolchains,
            "toolchain catalog",
            issues,
        )
        release_policies = read_model(
            repo_path(root, registry.catalogs.release_policies), ReleasePoliciesCatalog
        ).policies
        projects = records_by_id(registry.projects, "project registry", issues)
    except (OSError, ValueError) as exc:
        return GovernanceLintReport(
            projects=requested,
            issues=(f"registry load: {exc}",),
            status="FAIL",
        )

    for interface in interfaces.values():
        if not interface.pins:
            issues.append(f"interface {interface.id}: needs a non-empty pins list")
        numbers = [pin.number for pin in interface.pins]
        if len(set(numbers)) != len(numbers):
            issues.append(f"interface {interface.id}: duplicate pin number")
    for part in parts.values():
        alternates = set(part.approved_alternates)
        if len(alternates) != len(part.approved_alternates):
            issues.append(f"part {part.id}: duplicate approved alternate")
        for alternate_id in alternates:
            alternate = parts.get(alternate_id)
            if alternate is None or alternate_id == part.id:
                issues.append(f"part {part.id}: unknown or self approved alternate {alternate_id}")
            elif part.status is PartStatus.APPROVED and alternate.status is not PartStatus.APPROVED:
                issues.append(
                    f"part {part.id}: approved alternate {alternate_id} must be approved"
                )
    for library in libraries.values():
        try:
            library_parts = Path(library.path).parts
            if not (
                (len(library_parts) == 2 and library_parts[0] == "libraries")
                or (len(library_parts) == 3 and library_parts[:2] == ("examples", "libraries"))
            ):
                issues.append(
                    f"library {library.id}: path must be a named directory under libraries/ "
                    "or examples/libraries/"
                )
            if not repo_path(root, library.path).is_dir():
                issues.append(
                    f"library {library.id}: declared path is missing: {library.path}"
                )
            for label, value, expected in (
                ("provenance", library.provenance_path, library.provenance_sha256),
                ("licensing", library.licensing_path, library.licensing_sha256),
            ):
                record = repo_path(root, value)
                if not record.is_file():
                    issues.append(f"library {library.id}: {label} record is missing: {value}")
                elif hashlib.sha256(record.read_bytes()).hexdigest() != expected:
                    issues.append(f"library {library.id}: {label} record hash does not match")
        except ValueError as exc:
            issues.append(f"library {library.id}: {exc}")
    for toolchain in toolchains.values():
        if not reviewed_value(toolchain.kicad_version):
            issues.append(f"toolchain {toolchain.id}: needs an exact KiCad version")
        if "@sha256:" not in toolchain.image:
            issues.append(f"toolchain {toolchain.id}: image must be digest-pinned")
    policy_classes = [policy.release_class for policy in release_policies]
    if len(set(policy_classes)) != len(policy_classes) or set(policy_classes) != set(ReleaseClass):
        issues.append("release policies: need exactly one minimum assurance for every release class")

    project_ids = tuple(projects) if selected is None else requested
    declared = {project.project for project in projects.values()}
    discovered = {
        path.relative_to(root).as_posix()
        for design_root in settings(root).project_roots
        for path in (root / design_root).rglob("*.kicad_pro")
        if (root / design_root).is_dir()
        and not any(part.endswith("-backups") for part in path.parts)
    }
    if declared != discovered:
        issues.append(
            f"project discovery: undeclared or missing project files {sorted(declared ^ discovered)}"
        )

    for identifier in project_ids:
        project = projects.get(identifier)
        if project is None:
            issues.append(f"project registry: unknown project {identifier!r}")
            continue
        if len({tag.casefold() for tag in project.tags}) != len(project.tags):
            issues.append(f"project {identifier}: duplicate metadata tag")
        try:
            project_file = repo_path(root, project.project)
            if not project_file.is_file():
                issues.append(f"project {identifier}: project file is missing")
            config = load_config(root, project.config)
            manifest = read_model(repo_path(root, project.config), ProjectManifest)
        except (OSError, ValueError) as exc:
            issues.append(f"project {identifier}: invalid project/configuration: {exc}")
            continue

        if config.project_id != project.id:
            issues.append(f"project {identifier}: config project_id must match registry id")
        if config.kind is not project.kind:
            issues.append(f"project {identifier}: config kind must match registry kind")
        project_path = Path(project.project).as_posix()
        if not any(
            project_path == design_root or project_path.startswith(f"{design_root}/")
            for design_root in project.kind.accepted_roots
        ):
            issues.append(
                f"project {identifier}: {project.kind.value} projects belong under "
                f"{project.kind.design_root}/ (fixtures may use {project.kind.example_root}/)"
            )
        if config.project != project.project:
            issues.append(f"project {identifier}: config project path must match registry")
        if config.assurance_profile != project.assurance_profile:
            issues.append(
                f"project {identifier}: config assurance_profile must match registry"
            )
        toolchain = toolchains.get(config.toolchain_id)
        if toolchain is None:
            issues.append(f"project {identifier}: config needs a declared toolchain_id")
        elif (
            config.kicad_version != toolchain.kicad_version
            or config.image != toolchain.image
        ):
            issues.append(
                f"project {identifier}: config toolchain must match declared toolchain {config.toolchain_id}"
            )

        if project.assurance_profile == "training":
            if project.status != "training_fixture" or not config.not_for_manufacture:
                issues.append(
                    f"project {identifier}: training profile must be a not_for_manufacture training_fixture"
                )
        elif project.assurance_profile == "development":
            if project.status != "engineering" or not config.not_for_manufacture:
                issues.append(f"project {identifier}: development must be unreleased engineering work")
            if config.validation.expected_ignored_checks.erc or config.validation.expected_ignored_checks.drc:
                issues.append(f"project {identifier}: development cannot disable ERC or DRC checks")
        elif project.assurance_profile == "production":
            if (
                project.status not in {"engineering", "release_candidate"}
                or config.not_for_manufacture
            ):
                issues.append(
                    f"project {identifier}: production profile must be an engineering or release_candidate project"
                )
            if (
                config.validation.expected_ignored_checks.erc
                or config.validation.expected_ignored_checks.drc
            ):
                issues.append(
                    f"project {identifier}: production profile cannot disable ERC or DRC checks"
                )
            if project.mechanical_handoff is None:
                issues.append(
                    f"project {identifier}: mechanical_handoff record is missing"
                )
            else:
                try:
                    if not repo_path(root, project.mechanical_handoff).is_file():
                        issues.append(
                            f"project {identifier}: mechanical handoff record is missing"
                        )
                except ValueError as exc:
                    issues.append(f"project {identifier}: mechanical_handoff: {exc}")
            lint_governance_record(root, project.governance_record, identifier, issues)

        if project.kind is ProjectKind.PCB_ONLY and (
            project.assurance_profile == "production" or not config.not_for_manufacture
        ):
            issues.append(
                f"project {identifier}: pcb_only must remain not_for_manufacture with a training or development profile"
            )

        try:
            source = hashes(root, list(config.source_roots))
            if set(source) != set(config.required_inputs):
                issues.append(
                    f"project {identifier}: input inventory (required_inputs) differs from source_roots: "
                    f"{sorted(set(source) ^ set(config.required_inputs))}"
                )
        except (OSError, ValueError) as exc:
            issues.append(f"project {identifier}: invalid source scope: {exc}")

        schematic = project_file.with_suffix(".kicad_sch")
        pcb = project_file.with_suffix(".kicad_pcb")
        if project.kind is ProjectKind.PCB:
            if not schematic.is_file():
                issues.append(f"project {identifier}: schematic source is missing")
            elif schematic.relative_to(root).as_posix() not in config.required_inputs:
                issues.append(f"project {identifier}: schematic source is not inventoried")
            if not pcb.is_file():
                issues.append(f"project {identifier}: PCB source is missing")
            elif pcb.relative_to(root).as_posix() not in config.required_inputs:
                issues.append(f"project {identifier}: PCB source is not inventoried")
        elif project.kind is ProjectKind.PCB_ONLY:
            if schematic.exists():
                issues.append(
                    f"project {identifier}: pcb_only must not contain a matching schematic source; use pcb instead"
                )
            if not pcb.is_file():
                issues.append(f"project {identifier}: PCB source is missing")
            elif pcb.relative_to(root).as_posix() not in config.required_inputs:
                issues.append(f"project {identifier}: PCB source is not inventoried")
        else:
            if not schematic.is_file():
                issues.append(f"project {identifier}: schematic source is missing")
            elif schematic.relative_to(root).as_posix() not in config.required_inputs:
                issues.append(f"project {identifier}: schematic source is not inventoried")
            if pcb.exists():
                issues.append(
                    f"project {identifier}: {project.kind.value} project must not contain a PCB source"
                )

        identity = project.component_identity
        if project.kind is ProjectKind.PCB_ONLY and identity.required:
            issues.append(
                f"project {identifier}: pcb_only cannot require component identity without an authoritative schematic"
            )
        if project.assurance_profile == "production" and project.kind in {ProjectKind.PCB, ProjectKind.SCHEMATIC} and not identity.required:
            issues.append(
                f"project {identifier}: production profile must require component identity"
            )
        if identity.required and not identity.part_ids:
            issues.append(
                f"project {identifier}: component identity is required but no part ids are declared"
            )
        if identity.required and isinstance(config.validation, (PcbValidationContract, SchematicValidationContract)):
            expected_ids = {component.part_id for component in config.validation.components.values()}
            if None in expected_ids or expected_ids != set(identity.part_ids):
                issues.append(f"project {identifier}: component contracts must bind each reference to its declared part_id")
        for part_id in identity.part_ids:
            part = parts.get(part_id)
            if part is None:
                issues.append(f"project {identifier}: unknown approved part {part_id!r}")
                continue
            if project.assurance_profile == "production":
                for field, value in (
                    ("manufacturer", part.manufacturer),
                    ("description", part.description),
                    ("part_class", part.part_class),
                    ("mpn", part.mpn),
                    ("datasheet_url", part.datasheet_url),
                    ("lifecycle", part.lifecycle),
                ):
                    if not reviewed_value(value):
                        issues.append(
                            f"project {identifier}: production part {part_id} needs reviewed {field}"
                        )
                if part.status is not PartStatus.APPROVED:
                    issues.append(
                        f"project {identifier}: production part {part_id} must have status approved"
                    )
        for interface_id in project.interfaces:
            if interface_id not in interfaces:
                issues.append(f"project {identifier}: unknown interface {interface_id!r}")
        for library_id in project.library_ids:
            library = libraries.get(library_id)
            if library is None:
                issues.append(f"project {identifier}: unknown library {library_id!r}")
            elif (
                project.assurance_profile == "production"
                and library.status != "approved"
            ):
                issues.append(
                    f"project {identifier}: production library {library_id} must have status approved"
                )
        expected_shared_roots = {
            libraries[library_id].path
            for library_id in project.library_ids if library_id in libraries
        }
        if set(manifest.shared_source_roots) != expected_shared_roots:
            issues.append(
                f"project {identifier}: shared_source_roots must match library_ids catalog paths: "
                f"{sorted(set(manifest.shared_source_roots) ^ expected_shared_roots)}"
            )

    return GovernanceLintReport(
        projects=project_ids,
        issues=tuple(issues),
        status="PASS" if not issues else "FAIL",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--project", action="append", dest="projects")
    parser.add_argument("--tag", action="append", dest="tags")
    parser.add_argument("--product", action="append", dest="products")
    parser.add_argument("--exclude-tag", action="append", dest="excluded_tags")
    parser.add_argument("--all", action="store_true", help="Lint every declared project (the default).")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    from .hwrepo.selection import ProjectSelector, resolve_project_ids

    selector = ProjectSelector(
        project_ids=tuple(args.projects or ()),
        tags=tuple(args.tags or ()),
        excluded_tags=tuple(args.excluded_tags or ()),
        product_ids=tuple(args.products or ()),
    )
    if args.all and selector.active:
        parser.error("--all cannot be combined with project selectors")
    try:
        selected = resolve_project_ids(args.root, selector) if selector.active else None
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    result = lint(args.root, None if args.all else None if selected is None else list(selected))
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        write_model(args.output, result)
    print(result.model_dump_json(indent=2))
    return 0 if result.status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
