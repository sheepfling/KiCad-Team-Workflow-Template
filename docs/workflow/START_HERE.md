# Start here — adopting the KiCad workflow

Use the [folder standard](REPOSITORY_STRUCTURE.md) and [authority model](AUTHORITY_MODEL.md)
to understand what belongs with each board and what is shared.

## Start development

1. For private company work, start with [bootstrap](TEMPLATE_ADOPTION.md#bootstrap)
   and choose [company licensing terms](LICENSING.md) before the first commit.
   For a public fork or existing copy, complete the [Python setup](../../README.md#first-run-setup).
   Run `python -B -m tools.template doctor --format text`, then
   `python -B -m tools.template adopt --project-id my-hardware --format text`. The adoption command
   initializes the fresh fork and runs the full portable gate.
2. For an optional [reference-project rehearsal](../../examples/README.md), use a separate
   uninitialized template checkout: initialization disables live example discovery.
   Check Git status before and after opening it in the exact catalogued KiCad version.
3. Create an adopted project with `tools.template new-project`, choosing its ID, kind
   and toolchain. It starts in `development`, visibly NOT FOR MANUFACTURE.
4. Save its real source under `projects/<id>/kicad/`. Complete `project.json` and
   `tests/contract.json`; keep board requirements and decisions in its local docs.
5. Use a short-lived branch, run the selected and full gates, and review source and
   exported evidence. A new island's README is discovered automatically by docs policy.

When an import or check fails, follow [diagnose and repair](DIAGNOSTICS.md) for a
project-local finding, concrete next action and the relevant source of authority.

No product model or production governance record is needed to start a standalone
board. Add shared libraries through explicit dependencies. Add a product only when
cross-board assembly, wiring or integration requirements need their own record.

Initialization enables only `projects` in the live discovery configuration, empties
reference product/part/interface/library catalogs, and keeps toolchain and policy
defaults. It preserves `examples/` for independent shared-tool regression tests.
It refuses to replace customized catalogs or existing designs. Run it before imports;
after initialization, repeating it is a no-op for the same repository identity.
First-time initialization removes only the exact root template license; custom
company licenses and nested notices are preserved.

## Before production

Record actual decisions and evidence before changing a project to `production`:

| Decision | Record |
| --- | --- |
| Repository and branch controls | Default branch, required checks and hosted enforcement |
| Engineering ownership | Electrical/mechanical reviewers and integrator |
| Toolchain and libraries | Approved versions, installer sources, dependencies and owners |
| Mechanical handoff | Board-local reviewed interface and fit records |
| Release authority | Approval roles, exact frozen BOM/package location and retention |
| Recovery and handoff | Tag, artifact hashes, restore procedure and responsible owner |

Use the [production profile](ASSURANCE_PROFILES.md), [GitHub governance](GITHUB_GOVERNANCE.md)
and [release workflow](VERSIONING.md). Do not fill real-world approvals with template
placeholders. Development checks do not establish manufacturing readiness.

Before native editing, run `python -m tools.check_toolchain --toolchain <toolchain-id>`.
A cross-platform preflight for either Docker or an exact local KiCad CLI is
`python -B -m tools.template doctor --native --toolchain <toolchain-id>`.
A different installed version requires the approved build or a dedicated toolchain
migration. The controller fixture uses 10.0.0; the other reference projects use 10.0.5.

For a fresh local copy or a deliberate version update, see
[template bootstrap and migrations](TEMPLATE_ADOPTION.md).
