# Template bootstrap and upgrades

The template contract in `templates/template-contract.json` names the portable
files required for a reusable starting point. Verify it before copying the template:

```sh
python -B -m tools.template preflight
```

## Bootstrap

For a GitHub fork or template copy, install the Python dependencies, then run:

```sh
python -B -m tools.template init --project-id my-hardware
python -B -m tools.ci
```

For a fresh GitHub fork or template-generated repository, the equivalent guided path is:

```sh
python -B -m tools.template doctor
python -B -m tools.template adopt --project-id my-hardware
```

`adopt` runs preflight, the same transactional initialization, and the complete
portable gate. It is safe to repeat for the same repository identity. It does not
create a project, commit, remote, license choice or manufacturing approval.

This creates an empty live workspace with automatic discovery, preserves reference
fixtures, and records the repository identity and template version. It validates all
changes before writing, refuses customized catalogs/designs, and is repeatable after
successful initialization. Empty CI means the scaffold passed; no hardware passed.
Initialization also removes the exact root template license from the current
workspace. It preserves custom licenses, nested notices and existing Git history.

To create a new local copy from a **clean, committed** template source, choose a
new, nonexistent directory outside the source template:

```sh
python -B -m tools.template bootstrap --destination ../my-hardware-repo --project-id my-board
```

The command copies the controlled template into a staging directory and atomically places it only
after writing `template-adoption.json` and removing the known root template `LICENSE`. It copies
only Git-tracked source and excludes generated exports and local state; ignored downloads and
untracked files cannot be copied. It never overwrites a destination, initializes a remote, creates a
commit, changes repository permissions, opens KiCad or modifies a design. Bootstrap copies the
synthetic examples as regression inputs. Retain them while replacing their live catalog entries with
adopted source; see the
[folder standard](REPOSITORY_STRUCTURE.md).

Run `tools.template init --project-id my-board` inside that copy. The adopting
maintainer must then initialize/attach the correct Git remote, complete
[Start here](START_HERE.md), select the approved KiCad version, configure hosted
governance and commit the adoption record. A generated `template-adoption.json` only
records the chosen project identity and the source template version; it is not a
release or approval record.

For company work, add your organization's chosen root license or notice **before**
that first commit. Bootstrap creates no `.git` directory, so no earlier template
commit or root-license version enters the company's history. A custom root license
already present in the source is preserved, as are all nested and third-party
notices. See [licensing and adoption](LICENSING.md) for the precise cleanup boundary.

## Upgrade plan

Every template change that needs adopter action adds one forward migration record to
`templates/template-upgrades.json`. Ask the helper for the unique reviewed path:

```sh
python -B -m tools.template upgrade-plan --target-version <target-version>
```

The helper only returns ordered typed steps. It refuses downgrades, missing paths and
ambiguous migration routes; it does not rewrite KiCad, JSON, documentation or Git
history. Review the proposed steps on a branch, run the full local and native gates,
then apply the adopting repository's normal review and release process.

For initialized forks it reads the starting version from `template-adoption.json`,
so updating upstream tools and the template contract does not erase which migrations
you still need. Keep that adoption version unchanged until the migration passes
review. Without an adoption record, the current template contract supplies the start.

## Version 0.2.0 source-only migration

The upgrade catalog includes the reviewed steps from 0.1.0 to 0.2.0. Apply the new
upgrade catalog to the older copy while its template contract still records 0.1.0,
then ask `python -B -m tools.template upgrade-plan --target-version 0.2.0` for the plan.
Update the contract and adoption record when the migration is reviewed. On a current
0.2.0 copy, requesting 0.2.0 correctly returns an empty plan.

This migration removes committed reproducible exports, retains reference test inputs
independently from the live catalogs, and centralizes dependency installation. See
the [folder standard](REPOSITORY_STRUCTURE.md).

## Version 0.3.0 project islands

Version 0.3.0 moves project configs, docs, tests and optional firmware into each
project folder. `catalog/projects.json` now configures discovery roots rather than
listing projects. Local manifests select a shared toolchain by ID. Product records
move into their own folders, and generated product views move to their local `build/`.

Use `tools.template new-project` for new islands. Existing adopters can load the
updated upgrade catalog while retaining their old contract version to inspect the
0.2.0-to-0.3.0 plan. Follow the [folder standard](REPOSITORY_STRUCTURE.md) and
[BOM policy](BOM_POLICY.md), then update adoption metadata after review.

## Version 1.0.0 workflow migration

The 0.3.0-to-1.0.0 plan adds fresh-fork initialization, configurable team policy, per-reference
component identities, root-license cleanup and the evidence-backed release/restore path. The 1.0.0
contract records 1.0.0. A new 1.0.0 copy needs no migration; an existing adopter keeps its earlier
version in `template-adoption.json` and uses `upgrade-plan --target-version 1.0.0` with the updated
tools and catalog. The planner then returns the intervening steps. Existing adopters keep their live
project and catalog records; initialization is for fresh forks.

Review each board's identity expectations and export settings, then regenerate
release evidence from a clean source commit. Retain historical approved packages as
they are; do not rewrite their reports to look like new-format evidence. Change the
adoption version only after the migration and hosted checks are reviewed. The version
tag is created after acceptance, not by the migration helper.

## Version 1.1.0 usability migration

Version 1.1.0 establishes one shared local and hosted Python baseline, adds
the environment doctor and fresh-fork adoption command, and reports the final release
archive SHA-256. It does not move existing projects or catalogs. Existing adopters
keep `template-adoption.json` at 1.0.0 while applying and reviewing the updated tools,
then run `upgrade-plan --target-version 1.1.0`, portable CI and applicable native lanes.
Update the adoption version only after those checks pass.

## Version 1.2.0 documentation and Markdown migration

Version 1.2.0 moves project scaffolds, imported-project notes and release-review
records to shared typed SnakeMD builders. It also moves scaffold-owned guidance to
`docs/workflow/` and reserves `docs/team/` for organization-wide adopter material.
Board and product docs remain in their islands. Reinstall the pinned dependencies,
apply the updated tools and tests, move existing repository-wide adopter docs into
`docs/team/`, and update local links. Then run
`upgrade-plan --target-version 1.2.0`, portable CI and applicable native lanes.
Inspect generated workflow documents and the documentation graph before updating
the adoption version.

## Version 1.2.1 dependency maintenance migration

Version 1.2.1 updates Pydantic and removes unused direct declarations of its
transitive packages. Recreate the policy environment from `pyproject.toml`, then
run `upgrade-plan --target-version 1.2.1`, portable CI and applicable native lanes.
Pydantic selects the compatible `pydantic-core` distribution; do not add that or
other Pydantic transitive packages as direct pins unless repository source imports
them directly.

## Version 1.3.0 PCB-only import migration

Version 1.3.0 adds the `pcb_only` project kind for board sources that have no matching
schematic. Apply the templates, typed policy tools and documentation, then use the
new kind only for not-for-manufacture training or development work. It runs board DRC
and rendering, but has no ERC, schematic-parity, netlist identity, product assembly
or non-review release authority. Keep existing complete boards as `pcb`; reconstruct
or adopt a schematic before changing a PCB-only island into a manufacturing-capable
board. Run `upgrade-plan --target-version 1.3.0`, portable CI and applicable native
lanes before updating the adoption version.

## Version 1.3.1 board ERC and DRC settings migration

Version 1.3.1 clarifies that development and production contracts must retain no
ignored ERC or DRC checks. Apply the updated documentation and tools, then inspect
each board's KiCad settings before its next native run. For complete PCB projects,
enable KiCad 10.0.5's default ignored ERC checks in Schematic Setup and default
ignored DRC checks in Board Setup. PCB-only projects have no schematic/ ERC lane and
need the DRC changes only. Move genuinely experimental work to a reviewed training
fixture; do not copy defaults into a development contract merely to make CI pass. Run
`upgrade-plan --target-version 1.3.1`, portable CI and the applicable native lanes
before updating the adoption version.

## Version 1.3.2 corrective migration

Version 1.3.2 fixes release project scoping, spreadsheet-safe CSV rendering and
adoption/version diagnostics. It also rejects a component-identity claim on a PCB-only
island because that lane has no authoritative schematic or netlist. Apply the updated
tools and documentation, review product release evidence for every declared
product-view project, then run `upgrade-plan --target-version 1.3.2`, portable CI and
the applicable native lanes before updating the adoption version.
