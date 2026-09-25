# Scaffold changelog

These versions describe the reusable workflow, independently of board and product revisions. See
[versioning](docs/workflow/VERSIONING.md) and [adoption](docs/workflow/TEMPLATE_ADOPTION.md).

## Unreleased

- Add a project diagnostic command that coaches import, portable CI, native KiCad
  and purchasing-BOM repairs without editing design source.
- Include CAD dependency line numbers in portable policy findings.

## 1.3.2 — 2026-09-11

- Include every project declared for a selected product in release evidence checks.
- Make every textual value in generated review and purchasing BOM CSVs safe to open in
  spreadsheet software.
- Require initialized adopters on an older template version to use `upgrade-plan`
  rather than reporting a fresh-fork adoption pass.
- Make doctor safe for shared worktrees and turn a timed-out KiCad version probe into
  a typed diagnostic.
- Reject component-identity claims for PCB-only islands and complete the first-board
  ERC/DRC setup and dependency-maintenance guidance.
- Support Python 3.11 throughout the policy tools, strict type checks and hosted CI.

Existing 1.3.1 adopters should follow the 1.3.1-to-1.3.2 migration before updating
their adoption record.

## 1.3.1 — 2026-09-11

- Clarify the first-board step required to enable KiCad 10.0.5's default ignored DRC
  checks before native validation of a development board.
- Preserve the strict rule that development and production contracts cannot suppress
  ERC or DRC checks.

Existing 1.3.0 adopters should review their board-level KiCad DRC settings before
following the 1.3.0-to-1.3.1 migration.

## 1.3.0 — 2026-09-11

- Add a typed `pcb_only` project kind for importing a `.kicad_pcb` that lacks a
  matching authoritative schematic.
- Preserve and inventory the board, run board DRC and render checks, while excluding
  ERC, schematic parity and netlist/component assertions that cannot be supported.
- Keep PCB-only islands not for manufacture and block their use in product assemblies
  and non-review releases until they are migrated to a complete `pcb` project.

Existing 1.2.1 adopters can retain all complete projects. Apply the templates and
policy tools, use the PCB-only lane only for board capture/review, and follow the
1.2.1-to-1.3.0 migration before updating their adoption record.

## 1.2.1 — 2026-09-11

- Update Pydantic to 2.13.5.
- Stop declaring Pydantic's unused transitive dependencies as direct project pins.
  This lets Pydantic select its published compatible core and prevents separate,
  incompatible dependency-update pull requests.

Existing 1.2.0 adopters can update the shared tools and recreate their policy
environment, then follow the 1.2.0-to-1.2.1 migration before updating their
adoption record.

## 1.2.0 — 2026-09-10

- Replace hand-built project, import and release-review Markdown with shared typed
  SnakeMD document builders.
- Pin SnakeMD 2.4.1 at runtime and snakemd-stubs 2.4.1.0 for strict static analysis.
- Add deterministic generator contracts for links, native paths, lists, inline code
  and final-newline behavior.
- Separate scaffold guidance under `docs/workflow/` from adopter-owned material under
  `docs/team/`, with a single documentation map at `docs/README.md`.
- Remove dated audit, rehearsal and acceptance reports from the distributable source;
  their evidence belongs to pull requests, CI artifacts and releases.
- Enforce the documentation namespaces in the typed Markdown policy and move its
  configuration to `catalog/`.

Existing 1.1.0 adopters can preserve all project and catalog records. Apply the
updated Python tools and dependency pins, move reusable scaffold guides to
`docs/workflow/`, place organization-wide docs under `docs/team/`, update local
links, and follow the 1.1.0-to-1.2.0 migration.

## 1.1.0 — 2026-09-09

- Establish one shared Python minimum locally, in package metadata and in CI.
- Add a read-only environment doctor and a one-command fresh-fork adoption path.
- Print the complete release archive SHA-256 after package and restore verification.
- Add a concrete first-board path and durable release-storage checklist.
- Schedule bounded monthly Python and GitHub Actions dependency-update pull requests.
- Move checkout and artifact upload to their Node 24 action releases while retaining
  immutable commit-SHA pins.
- Correct the 1.0 publication record and surface the repository's remaining hosted
  governance responsibilities.

Existing 1.0.0 adopters can preserve their project layout and live catalogs. Follow
the short 1.0.0-to-1.1.0 migration to update the policy environment and tools.

## 1.0.0 — 2026-09-08

The reviewed baseline is published as the annotated `v1.0.0` tag at
`37632266cb8b45631297e3ff7f6d1adb04cd41f2`. The post-merge
[hosted acceptance run](https://github.com/sheepfling/KiCAD-Test/actions/runs/34266735257)
passed all portable, pinned KiCad, failure-probe and release/restore jobs.

- Repeatable project islands keep each deliverable's source, docs, tests and optional
  firmware together. Discovery adds projects and native CI lanes automatically.
- Fresh initialization creates empty live catalogs while retaining independent
  regression examples. Bootstrap and import use staged copies and preserve source.
- Working BOMs, schemas, native exports and reports are generated into ignored
  output locations. Authored BOM inputs and frozen release records have explicit owners.
- Shared, project and product suites run through one portable entry point. CI covers
  Windows, macOS and Linux, pinned KiCad checks, deliberate faults and release restore.
- Standalone releases bind source commits, component identities, native outputs and
  retained evidence. Packages carry source history and verify an independent restore.
- Team controls are configurable. Actual reviewers, hosting enforcement and
  manufacturing approvals remain the adopting team's responsibility.
- The original scaffold is available under 0BSD. Bootstrap removes only the known
  root notice before a company's first commit; custom and nested licenses survive.

Existing 0.3.0 adopters follow the forward migration without replacing live projects
or company licensing. Earlier versions follow the intervening plans. Keep the old
adoption version until review and verification finish.
