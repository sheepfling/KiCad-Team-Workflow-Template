"""Typed, strict records for repository inputs, policy outputs and generated views."""
from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from enum import Enum
from typing import Annotated, Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

Identifier = Annotated[
    str,
    StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]*$", min_length=1),
]
Reference = Annotated[
    str,
    StringConstraints(pattern=r"^[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*$", min_length=1),
]
Digest = Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{64}$")]
GitCommit = Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{40}$")]
RepositoryPath = Annotated[str, StringConstraints(min_length=1)]
NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
NetName = Annotated[str, StringConstraints(min_length=1)]
TemplateVersion = Annotated[str, StringConstraints(pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$")]
PositiveCount = Annotated[int, Field(gt=0)]
NonNegativeCount = Annotated[int, Field(ge=0)]
PositiveMeasure = Annotated[float, Field(gt=0)]


class StrictModel(BaseModel):
    """Immutable model with exact fields and no coercion at serialized-data boundaries."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        validate_assignment=True,
        populate_by_name=True,
    )


class Assurance(str, Enum):
    UNKNOWN = "unknown"
    ASSUMED = "assumed"
    INFERRED = "inferred"
    OBSERVED = "observed"
    MANUFACTURER_DOCUMENTED = "manufacturer_documented"
    VERIFIED = "verified"
    NOT_APPLICABLE = "not_applicable"


class PartStatus(str, Enum):
    TRAINING = "not_for_manufacture"
    APPROVED = "approved"


class PartRecord(StrictModel):
    id: Identifier
    revision: Identifier
    description: NonEmptyText
    part_class: NonEmptyText
    unit: Literal["each"]
    manufacturer: NonEmptyText
    mpn: NonEmptyText
    datasheet_url: NonEmptyText
    lifecycle: NonEmptyText
    status: PartStatus
    approved_alternates: tuple[Identifier, ...] = ()


class PartsCatalog(StrictModel):
    schema_version: NonEmptyText
    parts: tuple[PartRecord, ...]


class InterfacePin(StrictModel):
    number: NonEmptyText
    signal: NonEmptyText
    direction: NonEmptyText
    voltage_domain: NonEmptyText
    mating: NonEmptyText
    orientation: NonEmptyText
    mechanical_clearance: NonEmptyText


class InterfaceRecord(StrictModel):
    id: Identifier
    revision: NonEmptyText
    pins: tuple[InterfacePin, ...]


class InterfacesCatalog(StrictModel):
    schema_version: NonEmptyText
    interfaces: tuple[InterfaceRecord, ...]


class LibraryRecord(StrictModel):
    id: Identifier
    version: NonEmptyText
    path: RepositoryPath
    owner: NonEmptyText
    status: NonEmptyText
    provenance_path: RepositoryPath
    provenance_sha256: Digest
    licensing_path: RepositoryPath
    licensing_sha256: Digest


class LibrariesCatalog(StrictModel):
    schema_version: NonEmptyText
    libraries: tuple[LibraryRecord, ...]


class LibrarySbom(StrictModel):
    schema_version: Literal["1"] = "1"
    build_authorized: Literal[False] = False
    libraries: tuple[LibraryRecord, ...]


class ToolchainRecord(StrictModel):
    id: Identifier
    kicad_version: NonEmptyText
    image: NonEmptyText
    desktop_edit_policy: NonEmptyText
    installer_source: NonEmptyText
    migration_policy: NonEmptyText


class ToolchainsCatalog(StrictModel):
    schema_version: NonEmptyText
    toolchains: tuple[ToolchainRecord, ...]


class ComponentIdentity(StrictModel):
    required: bool
    part_ids: tuple[Identifier, ...]


class ProjectKind(str, Enum):
    """The engineering deliverable represented by one native KiCad project."""

    PCB = "pcb"
    PCB_ONLY = "pcb_only"
    SCHEMATIC = "schematic"
    SYSTEM_WIRING = "system_wiring"
    HARNESS_INTERFACE = "harness_interface"

    @property
    def domain_name(self) -> str:
        """Return the human-facing directory name for this design kind."""
        return {
            ProjectKind.PCB: "pcb",
            ProjectKind.PCB_ONLY: "pcb-only",
            ProjectKind.SCHEMATIC: "schematic",
            ProjectKind.SYSTEM_WIRING: "system-wiring",
            ProjectKind.HARNESS_INTERFACE: "harness-interface",
        }[self]

    @property
    def design_root(self) -> str:
        """Return the canonical root for adopted-repository project sources."""
        return "projects"

    @property
    def example_root(self) -> str:
        """Return the fixture root used by this template's reference projects."""
        return f"examples/{self.design_root}"

    @property
    def accepted_roots(self) -> tuple[str, str]:
        """Return canonical and template-fixture roots accepted by repository policy."""
        return (self.design_root, self.example_root)


class ProjectRecord(StrictModel):
    id: Identifier
    kind: ProjectKind
    status: Literal["training_fixture", "engineering", "release_candidate"]
    assurance_profile: Literal["training", "development", "production"]
    config: RepositoryPath
    project: RepositoryPath
    component_identity: ComponentIdentity
    tags: tuple[Identifier, ...] = ()
    interfaces: tuple[Identifier, ...] = ()
    library_ids: tuple[Identifier, ...] = ()
    mechanical_handoff: RepositoryPath | None = None
    governance_record: RepositoryPath | None = None


class CatalogPaths(StrictModel):
    parts: RepositoryPath
    interfaces: RepositoryPath
    libraries: RepositoryPath
    toolchains: RepositoryPath
    release_policies: RepositoryPath


class ProjectRegistry(StrictModel):
    schema_version: NonEmptyText
    catalogs: CatalogPaths
    projects: tuple[ProjectRecord, ...]


class ComponentContract(StrictModel):
    value: NonEmptyText
    footprint: str
    part_id: Identifier | None = None


class IgnoredChecks(StrictModel):
    erc: tuple[Identifier, ...]
    drc: tuple[Identifier, ...]


class PcbValidationContract(StrictModel):
    """Native checks and independent electrical contract for a board deliverable."""

    kind: Literal[ProjectKind.PCB]
    components: Mapping[Identifier, ComponentContract]
    nets: Mapping[NetName, tuple[Reference, ...]]
    expected_ignored_checks: IgnoredChecks


class PcbOnlyValidationContract(StrictModel):
    """Native board-layout checks where no authoritative schematic is available."""

    kind: Literal[ProjectKind.PCB_ONLY]
    expected_ignored_checks: IgnoredChecks


class SchematicValidationContract(StrictModel):
    """Native checks for a schematic-only deliverable with no manufactured PCB."""

    kind: Literal[ProjectKind.SCHEMATIC]
    components: Mapping[Identifier, ComponentContract] = Field(default_factory=dict)
    nets: Mapping[NetName, tuple[Reference, ...]] = Field(default_factory=dict)
    expected_ignored_checks: IgnoredChecks


class ProductTraceabilityValidationContract(StrictModel):
    """Shared typed authority for KiCad product, wiring, and harness review views."""

    product_id: Identifier
    connection_ids: tuple[Identifier, ...]
    terminal_ids: tuple[Identifier, ...]
    harness_ids: tuple[Identifier, ...]
    expected_ignored_checks: IgnoredChecks

    def require_complete_unique_coverage(self, *extra: tuple[str, tuple[str, ...]]) -> None:
        for label, values in (
            ("connection_ids", self.connection_ids),
            ("terminal_ids", self.terminal_ids),
            ("harness_ids", self.harness_ids),
            *extra,
        ):
            if not values:
                raise ValueError(f"{label} must not be empty for a product traceability view")
            if len(set(values)) != len(values):
                raise ValueError(f"{label} must not contain duplicates")


class SystemWiringValidationContract(ProductTraceabilityValidationContract):
    """Trace a whole-system KiCad view to every typed product relationship."""

    kind: Literal[ProjectKind.SYSTEM_WIRING]
    mechanical_handoff_ids: tuple[Identifier, ...]

    @model_validator(mode="after")
    def complete_unique_coverage(self) -> SystemWiringValidationContract:
        self.require_complete_unique_coverage(
            ("mechanical_handoff_ids", self.mechanical_handoff_ids)
        )
        return self


class HarnessInterfaceValidationContract(ProductTraceabilityValidationContract):
    """Trace a harness-interface sheet to only its owned electrical conductors."""

    kind: Literal[ProjectKind.HARNESS_INTERFACE]

    @model_validator(mode="after")
    def complete_unique_coverage(self) -> HarnessInterfaceValidationContract:
        self.require_complete_unique_coverage()
        return self


ProjectValidationContract = Annotated[
    PcbValidationContract
    | PcbOnlyValidationContract
    | SchematicValidationContract
    | SystemWiringValidationContract
    | HarnessInterfaceValidationContract,
    Field(discriminator="kind"),
]


class ProjectConfig(StrictModel):
    schema_version: NonEmptyText
    kind: ProjectKind
    assurance_profile: Literal["training", "development", "production"]
    not_for_manufacture: bool
    project_id: Identifier
    component_identity: ComponentIdentity
    toolchain_id: Identifier
    kicad_version: NonEmptyText
    image: NonEmptyText
    project: RepositoryPath
    source_roots: tuple[RepositoryPath, ...]
    required_inputs: tuple[RepositoryPath, ...]
    validation: ProjectValidationContract

    @model_validator(mode="after")
    def matching_project_kind(self) -> ProjectConfig:
        if self.kind is not self.validation.kind:
            raise ValueError("project kind must match validation contract kind")
        return self


class ProjectDiscovery(StrictModel):
    """Repository-wide dependencies and roots; project records live with boards."""

    schema_version: Literal["1"] = "1"
    catalogs: CatalogPaths
    project_roots: tuple[RepositoryPath, ...]

    @model_validator(mode="after")
    def live_projects_are_always_discovered(self) -> ProjectDiscovery:
        if "projects" not in self.project_roots or len(set(self.project_roots)) != len(self.project_roots):
            raise ValueError("Discovery must include projects exactly once; examples/projects is optional")
        return self


class ReleaseExportSettings(StrictModel):
    """Manufacturer-facing settings reviewed with each board's source."""

    gerber_layers: Annotated[tuple[NonEmptyText, ...], Field(min_length=1)]
    coordinate_origin: Literal["absolute", "plot"] = "absolute"
    position_units: Literal["mm", "in"] = "mm"


class ProjectManifest(StrictModel):
    """Authored project-local inputs. Shared paths are explicitly repository-relative."""

    schema_version: Literal["1"] = "1"
    id: Identifier
    kind: ProjectKind
    status: Literal["training_fixture", "engineering", "release_candidate"]
    assurance_profile: Literal["training", "development", "production"]
    toolchain_id: Identifier
    project: RepositoryPath
    source_roots: tuple[RepositoryPath, ...]
    required_inputs: tuple[RepositoryPath, ...]
    checks: RepositoryPath = "tests/contract.json"
    shared_source_roots: tuple[RepositoryPath, ...] = ()
    shared_inputs: tuple[RepositoryPath, ...] = ()
    component_identity: ComponentIdentity
    tags: tuple[Identifier, ...] = ()
    interfaces: tuple[Identifier, ...] = ()
    library_ids: tuple[Identifier, ...] = ()
    mechanical_handoff: RepositoryPath | None = None
    governance_record: RepositoryPath | None = None
    release_exports: ReleaseExportSettings | None = None


class ProjectTestContract(StrictModel):
    schema_version: Literal["1"] = "1"
    validation: ProjectValidationContract


class ProjectScaffoldReport(StrictModel):
    status: Literal["PASS", "FAIL"]
    directory: str
    issues: tuple[str, ...] = ()
    next_step: str = "Create the native KiCad design, then complete the test contract and run tools.ci."


class ProjectImportReport(StrictModel):
    """Import receipt; copying source is separate from accepting its engineering checks."""

    status: Literal["PASS", "FAIL"]
    directory: str
    source_project: str
    dry_run: bool
    copied_sha256: Mapping[RepositoryPath, Digest] = Field(default_factory=dict)
    excluded: Mapping[RepositoryPath, str] = Field(default_factory=dict)
    issues: tuple[str, ...] = ()
    review_required: Literal[True] = True
    next_step: str = "Review dependencies, populate independent test expectations, then run tools.ci. Import does not approve the design."


class ProductIndexEntry(StrictModel):
    id: Identifier
    path: RepositoryPath
    project_ids: tuple[Identifier, ...]


class ProductIndex(StrictModel):
    schema_version: Literal["1"]
    products: tuple[ProductIndexEntry, ...]

    @model_validator(mode="after")
    def unique_product_ids(self) -> ProductIndex:
        ids = [product.id.casefold() for product in self.products]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate product IDs in catalog/products.json")
        return self


class AssemblyKind(str, Enum):
    PURCHASED = "purchased"
    BUILT = "built"
    PHANTOM = "phantom"


class AssemblyMember(StrictModel):
    ref: Identifier
    item: Reference
    quantity: PositiveCount


class Assembly(StrictModel):
    id: Identifier
    revision: Identifier
    kind: AssemblyKind
    members: tuple[AssemblyMember, ...]
    purchase_part: Reference | None = None
    project_id: Identifier | None = None


class TerminalKind(str, Enum):
    ELECTRICAL = "electrical"
    MECHANICAL = "mechanical"
    LOGICAL = "logical"


class Terminal(StrictModel):
    id: Identifier
    instance: Reference
    pin: Identifier
    kind: TerminalKind
    exclusive: bool
    interface_id: Identifier | None = None
    interface_pin: NonEmptyText | None = None


class ConnectionKind(str, Enum):
    ELECTRICAL = "electrical"
    FUNCTIONAL = "functional"
    MECHANICAL = "mechanical"
    PROTOCOL = "protocol"


class Connection(StrictModel):
    id: Identifier
    kind: ConnectionKind
    from_terminal: Identifier = Field(alias="from")
    to_terminal: Identifier = Field(alias="to")
    variants: tuple[Identifier, ...]
    assurance: Assurance
    evidence: tuple[Identifier, ...]
    harness: Identifier | None = None


class Variant(StrictModel):
    id: Identifier
    revision: Identifier
    exclude: tuple[Reference, ...]


class EvidenceKind(str, Enum):
    DESIGN_NOTE = "design_note"
    OBSERVATION = "observation"
    DATASHEET = "datasheet"
    TEST_REPORT = "test_report"


class Evidence(StrictModel):
    id: Identifier
    kind: EvidenceKind
    path: RepositoryPath
    sha256: Digest
    claims: tuple[Identifier, ...]


class Harness(StrictModel):
    id: Identifier
    revision: Identifier
    instance: Reference
    length_mm: PositiveMeasure
    conductor_area_mm2: PositiveMeasure
    assurance: Assurance
    evidence: tuple[Identifier, ...]


class MechanicalHandoff(StrictModel):
    id: Identifier
    instances: tuple[Reference, ...]
    units: Literal["mm"]
    datum: NonEmptyText
    drawing: RepositoryPath
    assurance: Assurance
    evidence: tuple[Identifier, ...]
    open_items: tuple[NonEmptyText, ...]


class ProductRecord(StrictModel):
    schema_version: Literal["1"]
    id: Identifier
    revision: Identifier
    maturity: Literal["training", "engineering_review", "prototype", "pilot", "production"]
    root_assembly: Identifier
    assemblies: tuple[Assembly, ...]
    terminals: tuple[Terminal, ...]
    connections: tuple[Connection, ...]
    variants: tuple[Variant, ...]
    evidence: tuple[Evidence, ...]
    harnesses: tuple[Harness, ...]
    mechanical: tuple[MechanicalHandoff, ...]
    blocking_issues: tuple[NonEmptyText, ...]


class PolicyIssue(StrictModel):
    code: NonEmptyText
    location: NonEmptyText
    message: NonEmptyText


class ProductPolicyReport(StrictModel):
    schema_version: Literal["1"] = "1"
    lane: Literal["PRODUCT_POLICY"] = "PRODUCT_POLICY"
    build_authorized: Literal[False] = False
    status: Literal["PASS", "FAIL"]
    products: tuple[Identifier, ...]
    open_items: Mapping[Identifier, tuple[NonEmptyText, ...]]
    issues: tuple[PolicyIssue, ...]


class Occurrence(StrictModel):
    item: Reference
    quantity: PositiveCount


class BomRow(StrictModel):
    part_id: Identifier
    revision: Identifier
    quantity: PositiveCount
    unit: Literal["each"]
    instances: NonEmptyText
    manufacturer: NonEmptyText
    mpn: NonEmptyText
    disposition: Literal["NOT FOR MANUFACTURE"]


class HarnessScheduleRow(StrictModel):
    """One non-procurement harness schedule row for a selected product variant."""

    harness_id: Identifier
    revision: Identifier
    instance: Reference
    length_mm: PositiveMeasure
    conductor_area_mm2: PositiveMeasure
    electrical_connection_ids: tuple[Identifier, ...]
    endpoint_terminal_ids: tuple[Identifier, ...]
    assurance: Assurance
    evidence: tuple[Identifier, ...]
    disposition: Literal["NOT FOR MANUFACTURE"]


class HarnessSchedule(StrictModel):
    schema_version: Literal["1"] = "1"
    product: Identifier
    revision: Identifier
    variant: Identifier
    variant_revision: Identifier
    build_authorized: Literal[False] = False
    rows: tuple[HarnessScheduleRow, ...]


class ElectricalConnectionView(StrictModel):
    id: Identifier
    from_terminal: Terminal = Field(alias="from")
    to_terminal: Terminal = Field(alias="to")
    harness: Identifier | None = None
    assurance: Assurance
    evidence: tuple[Identifier, ...]


class ElectricalView(StrictModel):
    schema_version: Literal["1"] = "1"
    product: Identifier
    revision: Identifier
    variant: Identifier
    variant_revision: Identifier
    build_authorized: Literal[False] = False
    connections: tuple[ElectricalConnectionView, ...]


class SystemConnectionView(StrictModel):
    id: Identifier
    kind: ConnectionKind
    from_terminal: Terminal = Field(alias="from")
    to_terminal: Terminal = Field(alias="to")
    harness: Identifier | None = None
    assurance: Assurance
    evidence: tuple[Identifier, ...]


class SystemView(StrictModel):
    schema_version: Literal["1"] = "1"
    product: Identifier
    revision: Identifier
    variant: Identifier
    variant_revision: Identifier
    build_authorized: Literal[False] = False
    connections: tuple[SystemConnectionView, ...]


class SnapshotManifest(StrictModel):
    schema_version: Literal["1"] = "1"
    kind: Literal["engineering_review_snapshot"] = "engineering_review_snapshot"
    build_authorized: Literal[False] = False
    commit: NonEmptyText
    working_tree_clean: bool
    git_status: str
    python_version: NonEmptyText
    policy_version: NonEmptyText
    products: tuple[Identifier, ...]
    checks: Mapping[Identifier, NonEmptyText]
    sources_sha256: Mapping[RepositoryPath, Digest]
    artifacts_sha256: Mapping[RepositoryPath, Digest]


class NetlistIdentityReport(StrictModel):
    status: Literal["PASS", "NOT_APPLICABLE"]
    assemblies: tuple[Identifier, ...] = ()
    components: int = 0
    reason: NonEmptyText | None = None


class SnapshotVerification(StrictModel):
    status: Literal["PASS"]
    artifacts: PositiveCount
    build_authorized: Literal[False] = False
    scope: Literal["artifact_integrity_only_not_authenticity_or_source_reconstruction"]


class ReleaseClass(str, Enum):
    ENGINEERING_REVIEW = "engineering_review"
    PROTOTYPE = "prototype"
    PILOT = "pilot"
    PRODUCTION = "production"


class ReleaseAssurancePolicy(StrictModel):
    release_class: ReleaseClass
    minimum_assurance: Assurance


class ReleasePoliciesCatalog(StrictModel):
    schema_version: Literal["1"] = "1"
    policies: tuple[ReleaseAssurancePolicy, ...]


class ReleaseStatus(str, Enum):
    CANDIDATE = "candidate"
    APPROVED = "approved"


class DeviationStatus(str, Enum):
    OPEN = "open"
    APPROVED = "approved"
    CLOSED = "closed"


class ReleaseVariant(StrictModel):
    product: Identifier
    product_revision: Identifier
    variant: Identifier
    variant_revision: Identifier


class ReleaseLibrary(StrictModel):
    id: Identifier
    version: NonEmptyText
    provenance_sha256: Digest
    licensing_sha256: Digest


class ReleaseInterface(StrictModel):
    id: Identifier
    revision: NonEmptyText


class ReleaseArtifactKind(str, Enum):
    REVIEW_RECORD = "review_record"
    BOM = "bom"
    SCHEMATIC_EXPORT = "schematic_export"
    PCB_EXPORT = "pcb_export"
    HARNESS_EXPORT = "harness_export"
    VALIDATION_REPORT = "validation_report"
    FABRICATION_PACKAGE = "fabrication_package"
    ASSEMBLY_PACKAGE = "assembly_package"


class ReleaseArtifact(StrictModel):
    id: Identifier
    kind: ReleaseArtifactKind
    path: RepositoryPath
    sha256: Digest
    intended_use: NonEmptyText


class ReleaseDeviation(StrictModel):
    id: Identifier
    scope: tuple[Identifier, ...]
    owner: NonEmptyText
    reason: NonEmptyText
    status: DeviationStatus
    expires: date
    evidence: tuple[Identifier, ...]


class ReleaseApproval(StrictModel):
    electrical_reviewer: NonEmptyText
    mechanical_reviewer: NonEmptyText | None = None
    integrator: NonEmptyText
    release_authority: NonEmptyText | None = None
    approved_at: date
    evidence: tuple[Identifier, ...]


class SourceState(StrictModel):
    """Observed Git identity and source bytes, never a caller-supplied assertion."""

    commit: GitCommit | None = None
    clean: bool = False
    files_sha256: Mapping[RepositoryPath, Digest] = Field(default_factory=dict)


class EvidenceFile(StrictModel):
    path: RepositoryPath
    sha256: Digest


class ReleaseEvidence(StrictModel):
    portable: EvidenceFile
    native: Mapping[Identifier, EvidenceFile]
    exports: Mapping[Identifier, EvidenceFile] = Field(default_factory=dict)


class ReleaseManifest(StrictModel):
    schema_version: Literal["1"] = "1"
    release_id: Identifier
    release_class: ReleaseClass
    status: ReleaseStatus
    source_commit: GitCommit
    source_tag: NonEmptyText | None = None
    toolchain_id: Identifier
    projects: tuple[Identifier, ...] = ()
    variants: tuple[ReleaseVariant, ...] = ()
    libraries: tuple[ReleaseLibrary, ...]
    interfaces: tuple[ReleaseInterface, ...]
    checks: Mapping[Identifier, Literal["PASS", "NOT_APPLICABLE"]] = Field(default_factory=dict)
    evidence: ReleaseEvidence | None = None
    artifacts: tuple[ReleaseArtifact, ...]
    deviations: tuple[ReleaseDeviation, ...] = ()
    approval: ReleaseApproval | None = None


class ReleaseReadinessReport(StrictModel):
    schema_version: Literal["1"] = "1"
    lane: Literal["RELEASE_READINESS"] = "RELEASE_READINESS"
    build_authorized: Literal[False] = False
    release_id: Identifier
    release_class: ReleaseClass
    status: Literal["PASS", "FAIL"]
    issues: tuple[PolicyIssue, ...]


class RepositoryPolicyReport(StrictModel):
    lane: Literal["REPOSITORY_POLICY"] = "REPOSITORY_POLICY"
    status: Literal["PASS", "FAIL"]
    issues: tuple[NonEmptyText, ...]


class GenerationReport(StrictModel):
    status: Literal["PASS", "FAIL"]
    issues: tuple[NonEmptyText, ...]


class GovernanceRecord(StrictModel):
    schema_version: Literal["1"] = "1"
    branch: NonEmptyText
    required_status_checks: tuple[NonEmptyText, ...]
    authors: tuple[NonEmptyText, ...]
    reviewers: tuple[NonEmptyText, ...]
    integrators: tuple[NonEmptyText, ...]
    release_authorities: tuple[NonEmptyText, ...]
    branch_protection_evidence: tuple[NonEmptyText, ...]
    branch_protection_verified_at: NonEmptyText


class TeamPolicy(StrictModel):
    """Reviewed team choices, kept separately from project-specific assignments."""

    schema_version: Literal["1"] = "1"
    minimum_actors: Annotated[int, Field(ge=1)] = 2
    independent_review: bool = True
    required_status_checks: Annotated[tuple[NonEmptyText, ...], Field(min_length=1)] = ("Template acceptance",)
    rationale: NonEmptyText


class GovernanceLintReport(StrictModel):
    schema_version: Literal["1"] = "1"
    lane: Literal["STATIC_GOVERNANCE_LINT"] = "STATIC_GOVERNANCE_LINT"
    projects: tuple[Identifier, ...]
    issues: tuple[NonEmptyText, ...]
    status: Literal["PASS", "FAIL"]


class ToolchainAssessment(StrictModel):
    toolchain_id: Identifier
    expected_version: NonEmptyText
    observed_version: NonEmptyText | None
    desktop_editing_allowed: bool
    status: Literal["PASS", "FAIL"]
    next_action: NonEmptyText


class MatrixEntry(StrictModel):
    project: Identifier
    image: NonEmptyText
    kicad_version: NonEmptyText
    fault_probes: bool = False


class CiMatrix(StrictModel):
    include: tuple[MatrixEntry, ...]


class ImpactPlan(StrictModel):
    """Fail-closed scope for a changed-path development check."""

    schema_version: Literal["1"] = "1"
    scope: Literal["docs", "focused", "full"]
    projects: tuple[Identifier, ...]
    changed_paths: tuple[str, ...]
    reasons: tuple[NonEmptyText, ...]
    docs_changed: bool = False


class CommandEvidence(StrictModel):
    argv: tuple[NonEmptyText, ...]
    started_utc: NonEmptyText
    returncode: int
    stdout: str = ""
    stderr: str = ""
    error: str | None = None


class ReleaseExportReport(StrictModel):
    schema_version: Literal["1"] = "1"
    project_id: Identifier
    source: SourceState
    toolchain_id: Identifier
    settings: ReleaseExportSettings
    commands: Mapping[Identifier, CommandEvidence]
    artifacts_sha256: Mapping[RepositoryPath, Digest]
    status: Literal["PASS", "FAIL"]


class ReleasePackageIndex(StrictModel):
    schema_version: Literal["1"] = "1"
    source_commit: GitCommit
    manifest: RepositoryPath
    files_sha256: Mapping[RepositoryPath, Digest]


class ReleasePackageReport(StrictModel):
    status: Literal["PASS", "FAIL"]
    source_commit: GitCommit
    package: str
    package_sha256: Digest
    manifest: RepositoryPath
    build_authorized: Literal[False] = False


class DocumentationException(StrictModel):
    """A reviewed, path-scoped and time-bounded documentation-policy waiver."""

    id: Identifier
    code: Identifier
    path: RepositoryPath
    reason: NonEmptyText
    expires: date


class DocumentationPolicy(StrictModel):
    """Repository-owned Markdown graph roots and narrow policy exceptions."""

    schema_version: Literal["1"] = "1"
    roots: tuple[RepositoryPath, ...]
    documentation_namespaces: tuple[RepositoryPath, ...] = ()
    exceptions: tuple[DocumentationException, ...] = ()


class DocumentationIssue(StrictModel):
    code: Identifier
    path: RepositoryPath
    line: PositiveCount
    message: NonEmptyText


class DocumentationPolicyReport(StrictModel):
    schema_version: Literal["1"] = "1"
    lane: Literal["MARKDOWN_REPOSITORY_POLICY"] = "MARKDOWN_REPOSITORY_POLICY"
    roots: tuple[RepositoryPath, ...]
    documents: NonNegativeCount
    issues: tuple[DocumentationIssue, ...]
    status: Literal["PASS", "FAIL"]


class TemplateContract(StrictModel):
    """Versioned, portable inventory for a repository template implementation."""

    schema_version: Literal["1"] = "1"
    template_version: TemplateVersion
    required_paths: tuple[RepositoryPath, ...]
    adoption_guide: RepositoryPath
    upgrades_catalog: RepositoryPath


class TemplateUpgrade(StrictModel):
    id: Identifier
    from_version: TemplateVersion
    to_version: TemplateVersion
    breaking: bool
    steps: tuple[NonEmptyText, ...]


class TemplateUpgradesCatalog(StrictModel):
    schema_version: Literal["1"] = "1"
    upgrades: tuple[TemplateUpgrade, ...]


class TemplateAdoptionRecord(StrictModel):
    schema_version: Literal["1"] = "1"
    template_version: TemplateVersion
    project_id: Identifier
    status: Literal["needs_adoption", "initialized"] = "needs_adoption"


class TemplateInitReport(StrictModel):
    status: Literal["PASS", "FAIL"]
    project_id: str
    changed: tuple[RepositoryPath, ...] = ()
    removed: tuple[RepositoryPath, ...] = ()
    issues: tuple[PolicyIssue, ...] = ()


class TemplateAdoptReport(StrictModel):
    """One-command fork initialization and portable acceptance result."""

    schema_version: Literal["1"] = "1"
    lane: Literal["TEMPLATE_ADOPTION"] = "TEMPLATE_ADOPTION"
    build_authorized: Literal[False] = False
    project_id: Identifier
    preflight: Literal["PASS", "FAIL"]
    initialization: Literal["PASS", "FAIL", "NOT_RUN"]
    portable: Literal["PASS", "FAIL", "NOT_RUN"]
    status: Literal["PASS", "FAIL"]
    changed: tuple[RepositoryPath, ...] = ()
    removed: tuple[RepositoryPath, ...] = ()
    issues: tuple[NonEmptyText, ...] = ()
    next_actions: tuple[NonEmptyText, ...] = ()


class EnvironmentCheck(StrictModel):
    id: Identifier
    required: bool
    status: Literal["PASS", "FAIL", "OPTIONAL"]
    expected: NonEmptyText
    observed: NonEmptyText | None = None
    next_action: NonEmptyText


class TemplateDoctorReport(StrictModel):
    """Local prerequisites and native-runner readiness without changing the repository."""

    schema_version: Literal["1"] = "1"
    lane: Literal["TEMPLATE_DOCTOR"] = "TEMPLATE_DOCTOR"
    build_authorized: Literal[False] = False
    native_requested: bool
    checks: tuple[EnvironmentCheck, ...]
    status: Literal["PASS", "FAIL"]
    next_actions: tuple[NonEmptyText, ...] = ()


class InventoryProject(StrictModel):
    """Declared island and whether its authored inputs are present for a check."""

    id: Identifier
    kind: ProjectKind
    status: Literal["training_fixture", "engineering", "release_candidate"]
    assurance_profile: Literal["training", "development", "production"]
    manifest: RepositoryPath
    project: RepositoryPath
    toolchain_id: Identifier
    tags: tuple[Identifier, ...]
    products: tuple[Identifier, ...]
    readiness: Literal["INPUTS_PRESENT", "NEEDS_INPUTS"]
    missing_inputs: tuple[RepositoryPath, ...] = ()
    next_command: NonEmptyText


class InventoryGroup(StrictModel):
    """One product or tag and its selected project IDs."""

    id: Identifier
    project_ids: tuple[Identifier, ...]


class InventoryToolchain(StrictModel):
    id: Identifier
    kicad_version: NonEmptyText


class TemplateInventoryReport(StrictModel):
    """Read-only discovery; input presence is not validation or release approval."""

    schema_version: Literal["1"] = "1"
    lane: Literal["TEMPLATE_INVENTORY"] = "TEMPLATE_INVENTORY"
    build_authorized: Literal[False] = False
    status: Literal["PASS", "FAIL"]
    projects: tuple[InventoryProject, ...] = ()
    products: tuple[InventoryGroup, ...] = ()
    tags: tuple[InventoryGroup, ...] = ()
    toolchains: tuple[InventoryToolchain, ...] = ()
    issues: tuple[PolicyIssue, ...] = ()
    next_actions: tuple[NonEmptyText, ...] = ()


class DiagnosticFinding(StrictModel):
    """One observed failure or review task with a concrete repair path."""

    severity: Literal["BLOCKING", "REVIEW"]
    code: NonEmptyText
    location: NonEmptyText
    observed: NonEmptyText
    action: NonEmptyText
    guide: RepositoryPath


class DiagnosticReport(StrictModel):
    """A local coaching view; success never constitutes engineering approval."""

    schema_version: Literal["1"] = "1"
    lane: Literal["PROJECT_DIAGNOSTICS"] = "PROJECT_DIAGNOSTICS"
    build_authorized: Literal[False] = False
    project_id: NonEmptyText
    scope: Literal["import", "project"]
    status: Literal["PASS", "NEEDS_WORK"]
    findings: tuple[DiagnosticFinding, ...]
    next_command: NonEmptyText
    run_directory: str | None = None


class LocalRescueReport(StrictModel):
    """Partial, read-only island inspection that cannot satisfy repository gates."""

    schema_version: Literal["1"] = "1"
    lane: Literal["LOCAL_PROJECT_RESCUE"] = "LOCAL_PROJECT_RESCUE"
    status: Literal["UNVERIFIED_GLOBAL"] = "UNVERIFIED_GLOBAL"
    build_authorized: Literal[False] = False
    ci_eligible: Literal[False] = False
    release_eligible: Literal[False] = False
    project_id: NonEmptyText
    selected_manifest: RepositoryPath | None = None
    local_inspection: Literal["CLEAR", "NEEDS_REPAIR"]
    findings: tuple[DiagnosticFinding, ...] = ()
    omitted_checks: tuple[NonEmptyText, ...]
    next_command: NonEmptyText
    run_directory: NonEmptyText


class TemplatePreflightReport(StrictModel):
    schema_version: Literal["1"] = "1"
    lane: Literal["TEMPLATE_PREFLIGHT"] = "TEMPLATE_PREFLIGHT"
    build_authorized: Literal[False] = False
    template_version: TemplateVersion | None = None
    status: Literal["PASS", "FAIL"]
    issues: tuple[PolicyIssue, ...]


class TemplateBootstrapReport(StrictModel):
    schema_version: Literal["1"] = "1"
    lane: Literal["TEMPLATE_BOOTSTRAP"] = "TEMPLATE_BOOTSTRAP"
    build_authorized: Literal[False] = False
    template_version: TemplateVersion | None = None
    destination: NonEmptyText
    status: Literal["PASS", "FAIL"]
    issues: tuple[PolicyIssue, ...]
    removed: tuple[RepositoryPath, ...] = ()


class TemplateUpgradePlan(StrictModel):
    schema_version: Literal["1"] = "1"
    lane: Literal["TEMPLATE_UPGRADE_PLAN"] = "TEMPLATE_UPGRADE_PLAN"
    build_authorized: Literal[False] = False
    current_version: TemplateVersion | None = None
    target_version: NonEmptyText
    status: Literal["PASS", "FAIL"]
    upgrades: tuple[TemplateUpgrade, ...]
    issues: tuple[PolicyIssue, ...]


class SupplierOffer(StrictModel):
    id: Identifier
    part_id: Identifier
    supplier: NonEmptyText
    supplier_sku: NonEmptyText
    source_url: NonEmptyText
    region: NonEmptyText
    currency: Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}$")]
    quantity_break: PositiveCount
    unit_price_minor: NonNegativeCount
    availability: NonEmptyText
    lead_time_days: NonNegativeCount | None = None


class SourcingSnapshot(StrictModel):
    schema_version: Literal["1"] = "1"
    snapshot_id: Identifier
    source_commit: GitCommit
    observed_at: AwareDatetime
    offers: tuple[SupplierOffer, ...]


class SourcingSnapshotReport(StrictModel):
    schema_version: Literal["1"] = "1"
    lane: Literal["SOURCING_SNAPSHOT"] = "SOURCING_SNAPSHOT"
    build_authorized: Literal[False] = False
    snapshot_id: Identifier
    offers: NonNegativeCount
    status: Literal["PASS", "FAIL"]
    issues: tuple[PolicyIssue, ...]


class CheckMetric(StrictModel):
    name: Identifier
    status: Literal["PASS", "FAIL"]
    findings: NonNegativeCount


class DeviationMetrics(StrictModel):
    total: NonNegativeCount
    approved: NonNegativeCount
    open: NonNegativeCount
    closed: NonNegativeCount
    expired: NonNegativeCount


class TemplateMetricsReport(StrictModel):
    schema_version: Literal["1"] = "1"
    lane: Literal["TEMPLATE_METRICS"] = "TEMPLATE_METRICS"
    build_authorized: Literal[False] = False
    checks: tuple[CheckMetric, ...]
    stale_evidence: NonNegativeCount
    deviations: DeviationMetrics


class CheckEvidence(StrictModel):
    status: Literal["PASS", "FAIL", "NOT_RUN"]
    returncode: int | None = None
    error: NonEmptyText | None = None
    findings: int | None = None
    expected_ignored_checks: tuple[Identifier, ...] = ()
    files: tuple[RepositoryPath, ...] = ()
    source_hashes: Mapping[RepositoryPath, Digest] = Field(default_factory=dict)
    identity_status: Literal["PASS", "NOT_APPLICABLE"] | None = None
    observed_version: NonEmptyText | None = None
    image: NonEmptyText | None = None


class NetlistContract(StrictModel):
    components: Mapping[Identifier, ComponentContract]
    nets: Mapping[NetName, tuple[Reference, ...]]


class ValidationSummary(StrictModel):
    schema_version: Literal["1"] = "1"
    lane: Literal["KICAD_CLI"] = "KICAD_CLI"
    timestamp_utc: NonEmptyText
    checked_commit: NonEmptyText
    source: SourceState | None = None
    project_id: Identifier | None = None
    pr_head_commit: str | None = None
    assurance_profile: Literal["training", "development", "production"] | None = None
    not_for_manufacture: bool | None = None
    project_kind: ProjectKind | None = None
    checks: Mapping[Identifier, CheckEvidence]
    status: Literal["PASS", "FAIL"]
    artifacts_sha256: Mapping[RepositoryPath, Digest]


class ProjectCheckSummary(StrictModel):
    id: Identifier
    status: Literal["PASS", "FAIL"]
    summary: RepositoryPath


class CheckAllSummary(StrictModel):
    schema_version: Literal["1"] = "1"
    lane: Literal["KICAD_CLI_ALL_PROJECTS"] = "KICAD_CLI_ALL_PROJECTS"
    governance: GovernanceLintReport
    repository: RepositoryPolicyReport
    product_policy: ProductPolicyReport
    projects: tuple[ProjectCheckSummary, ...]
    status: Literal["PASS", "FAIL"]


class FaultProbeCase(StrictModel):
    id: Identifier
    status: Literal["PASS", "FAIL"]
    expected_failing_check: Identifier
    observed_status: Literal["PASS", "FAIL", "NOT_RUN"] | None = None
    observed_returncode: int | None = None


class FaultProbeReport(StrictModel):
    lane: Literal["KICAD_CLI"] = "KICAD_CLI"
    not_for_manufacture: Literal[True] = True
    cases: tuple[FaultProbeCase, ...]
    status: Literal["PASS", "FAIL"]


class UnitTestReport(StrictModel):
    status: Literal["PASS", "FAIL"]
    returncode: int


class SkippedCheck(StrictModel):
    status: Literal["NOT_RUN"] = "NOT_RUN"
    reason: NonEmptyText


class FailedCheck(StrictModel):
    status: Literal["FAIL"] = "FAIL"
    error: NonEmptyText


class ProjectTestsReport(StrictModel):
    status: Literal["PASS", "FAIL"]
    commands: Mapping[Identifier, CommandEvidence]


class StaticPipelineReport(StrictModel):
    status: Literal["PASS", "FAIL"]
    source: SourceState | None = None
    scope: Literal["static_only"] = "static_only"
    build_authorized: Literal[False] = False
    registry: GovernanceLintReport
    repository: RepositoryPolicyReport
    documentation: DocumentationPolicyReport
    product: ProductPolicyReport
    generation: GenerationReport
    ruff: CommandEvidence
    pyright: CommandEvidence
    unit_tests: CommandEvidence
    project_tests: ProjectTestsReport


class ProjectStaticPipelineReport(StrictModel):
    """Fast local policy result for explicitly selected design projects."""

    status: Literal["PASS", "FAIL"]
    scope: Literal["project_static"] = "project_static"
    build_authorized: Literal[False] = False
    projects: tuple[Identifier, ...]
    registry: GovernanceLintReport
    repository: RepositoryPolicyReport
    product: ProductPolicyReport
    generation: GenerationReport
    project_tests: ProjectTestsReport
