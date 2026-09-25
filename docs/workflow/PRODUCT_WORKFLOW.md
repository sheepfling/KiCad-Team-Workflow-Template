# Product, harness and electrical–mechanical workflow

This document defines how projects, product records, BOMs, harness interfaces,
and mechanical handoffs fit together. The bundled product record is a reference
dataset; an adopted repository replaces it with its own reviewed product records.

## Start with the working example

`examples/products/status-indicator-system/product.json` adds a system layer around the existing
Arduino and Raspberry Pi status-LED boards. It has a phantom system, two built
board assemblies, one purchased cable assembly, an enclosure, three variants,
typed terminals/relationships, and an explicitly unresolved mechanical handoff.
It does not contain a Raspberry Pi or Arduino host board BOM, an approved mating
cable, or a complete physical product. The host GPIOs must not be wired together.

| Fact | Authoritative location | Checked/generated view |
| --- | --- | --- |
| Internal part identity, manufacturer, MPN, part revision | `catalog/parts.json` | Product memberships, KiCad `PART_ID`, review BOM |
| PCB electrical connectivity, symbol reference, footprint, PCB geometry | `projects/<id>/kicad/` | Native netlist, ERC/DRC, reference contract |
| Schematic-only electrical intent and interface review | `projects/<id>/kicad/` | ERC and schematic SVG; no board/netlist/BOM claim |
| System blockout/wiring review view | `projects/<id>/kicad/` plus typed `products/<id>/product.json` relationship records | Complete relation/terminal/harness/mechanical traceability, ERC, and schematic SVG; a diagram line alone is not electrical truth |
| Harness-interface review view and schedule | `projects/<id>/kicad/` plus typed `products/<id>/product.json` harness records | Exact electrical conductor/endpoint/harness traceability; generated JSON/CSV schedule for review |
| Assembly membership and quantity | `products/<id>/product.json` | Expanded variant BOM |
| Harness terminals and construction assumptions | Product terminals/harness records in this v1 example | Electrical connection JSON; future harness renderer consumes these IDs |
| Functional, protocol and mechanical relationships | Typed product connections | Generated semantic system view; never exported as electrical continuity |
| Datum, units, drawing reference, unresolved fit questions | Product mechanical record plus controlled drawing | Reference/units checks; physical fit still reviewed by engineers |
| Evidence scope and immutable content identity | Product evidence records plus repository files | Claim/type/reference/SHA-256 checks |
| Human approval and protected-branch enforcement | Actual review and hosting controls | Not established by text fields or this product checker |

Do not introduce a second part catalog under `products/`. An external PLM/PDM
adapter can later own the same stable identities; choose one authority explicitly.
Part revision, assembly revision, variant revision, Git commit and serialized unit
identity are different things. Unit/as-built records belong in a separate controlled
system when builds scale; a tag identifies design intent, not a manufactured unit.

## Daily loop — same Python commands on every OS

From the repository root:

```sh
python -B -m tools.ci
python -B -m tools.verify --project arduino-uno-status-led
python -B -m tools.hardware generate
python -B -m tools.ci
python -B -m tools.verify --project arduino-uno-status-led --depth native
python -B -m tools.ci --kicad --output build/review-001
```

The first command runs registry/discovery/path/link/local-state policy, product
validation, fresh isolated generation and unit/mutation tests. It explicitly
reports `static_only` and KiCad `NOT_RUN`. `tools.verify --project <id>` checks
the selected board plus its declared dependencies, retains a fresh ignored
receipt, and gives repair guidance. Add `--depth native` for exact KiCad checks
of that board. The final lower-level `tools.ci --kicad` command deliberately
checks every discovered native project; use a new evidence directory for it.
Close KiCad before checking source. Native checks use an exact local CLI or the
project's digest-pinned container image.
No command stashes, resets, commits, pushes, merges, buys parts or changes permissions.

`generate` writes only ignored review views and schema exports. To retain a complete
current inventory, use a new snapshot directory or download the CI artifact.
CI checks fresh generation without requiring cached exports in the checkout.

The helper uses Python 3.11+, Pydantic 2.13.5 and SnakeMD 2.4.1, pinned in
pyproject.toml; snakemd-stubs 2.4.1.0 covers generated Markdown under strict
Pyright. The hosted matrix targets Python 3.11 on Windows, Linux and macOS. JSON
avoids an extra YAML loader in the pinned KiCad container. Every repository JSON record is
decoded once at the file boundary, rejects duplicate keys/non-finite numbers, then
becomes a strict immutable Pydantic model. Extra fields, wrong types and unsupported
versions fail before engineering policy runs. Published schemas are generated from
those Pydantic models and exported on demand. See [the scripting standard](SCRIPTING_STANDARD.md).

Ruff 0.16.1 and strict Pyright 1.1.411 are pinned quality gates. Dependency hash
locking and migration commands remain adoption work, not claims of completed
quality gates.

## Coordinate edits at the design-unit boundary

1. State the affected project/sheet, library, assembly, variant and mechanical
   interface in the issue/PR. Coordinate simultaneous edits to the same native file.
2. Electrical engineering owns nets, pin mapping, component electrical selection,
   footprints and PCB constraints. Mechanical engineering owns enclosure geometry,
   fit/stack-up, installation/service envelopes and tolerance analysis. Agree on
   the interface owner, units, origin and revision before exchanging models.
3. Change a shared library with provenance and a declared revision; run repository-
   wide checks because all consuming projects may be affected. Do not independently
   edit a generated BOM or duplicate the board into an untracked mechanical copy.
4. Compare the same-commit schematic/PCB exports and mechanical drawing/model.
   Review hole locations, connector orientation/mating clearance, component height,
   cable bend/strain relief, thermal paths, keepouts and tolerance stack.
5. Resolve conflicts by engineering intent; rerun checks after resolution. Never
   assume Git's text merge establishes correct electrical connectivity or geometry.
6. Have an independent engineer trace one procurement item, one electrical path,
   one mechanical interface and one variant back to source and evidence.

## Part selection, pinouts and sourcing

Use [identity and sourcing](IDENTITY_AND_SOURCING.md) for supplier/price records.
Manufacturer + exact MPN identify a purchased item; a supplier SKU is an offer,
not a replacement identity. Record currency, quantity break, unit, retrieval date,
stock/lead time and source URL separately from the approved engineering definition.
Prices are time-sensitive observations, never hard-coded design truth. There is
no price-fetching, live link availability or purchasing automation in this lane.

Obtain pinouts from a specific manufacturer document/revision or controlled test.
Record connector side/view, contact numbering, mating part and electrical limits.
Never promote a plausible diagram or generated symbol to verified evidence.
The native adapter checks each mapped symbol's actual exported `PART_ID`; approved
parts also require matching `Manufacturer` and `MPN`. Footprints/connectivity remain
checked against the fixture's native export contract. These checks detect drift,
not whether the selected physical part or footprint is actually correct.

## Assurance, variants and BOM semantics

`unknown`, `assumed`, `inferred`, `observed`, `manufacturer_documented`, `verified`
and `not_applicable` remain distinct. Observed/documented/verified claims require
respectively observation/datasheet/test-report records scoped to that claim and
matching file hashes. A hash detects changed bytes; it cannot establish that a
report is honest, sufficient, current or approved. Reviewers must judge that.

Built/phantom assemblies expand; a purchased assembly contributes its one catalog
purchase item, never both its internals and purchase item. Quantities multiply
through nesting. Parts group by catalog identity, whose revision is recorded.
Variants exclude occurrence paths; descendants disappear from their BOM, and an
active relation to an excluded endpoint or harness is an error. A functional
relation cannot name a harness and is never emitted into electrical rows.
For a built board that remains in the product, a variant may also map its
project ID to a named KiCad design variant with `board_variants`, for example
`"board_variants": {"battery-board": "Pilot A"}`. This selects a component
population when generating the board's release BOM, placement file and other
population-sensitive outputs. The KiCad name must be declared in that board's
`.kicad_pro`; product-level exclusions and board-level population are separate
choices. See [release exports](RELEASE_READINESS.md#board-fabrication-and-assembly-exports).
The matching generated system view retains every explicit relation kind so a
renderer cannot silently reinterpret functional or mechanical relationships as
electrical continuity.

v1 supports integer `each` quantities, up to 64 nesting levels / 10,000 expanded
instances, and one current revision per part ID. Repeated physical instances that
need terminal addressing must have separate occurrence refs. Fractional wire stock,
DNP/alternate-selection reason records beyond native KiCad variants, mixed revisions of one ID, shielding,
splices, cable drawings and automatic substitution need an explicit schema
extension plus good/bad fixtures; do not overload the existing fields.

## Review snapshots, not releases

```sh
python -B -m tools.hardware snapshot --output build/product-review-001
python -B -m tools.hardware verify-snapshot --output build/product-review-001
python -B -m tools.hardware check --release
```

A snapshot retains generated artifacts and a manifest: exact current commit,
dirty/untracked status, Python/helper versions, scoped source hashes and artifact
hashes. It truthfully marks KiCad, physical fit and human review `NOT_RUN`. It does
not copy all source, attest provenance, or prove reproduction from a clean tag.
Verification checks only retained artifact integrity/inventory, not authenticity.
The release command intentionally exits nonzero until a real release policy,
approval authority, clean-tag reconstruction and appropriate evidence gates exist.

Do not relabel the legacy `production` assurance profile as completed product
release support. Its local metadata requirements are prerequisites, not proof of
live hosting controls, mechanical acceptance or release authority.

Use [checks and CI](CHECKS_AND_CI.md) for executable acceptance and
[release readiness](RELEASE_READINESS.md) for production evidence boundaries.
