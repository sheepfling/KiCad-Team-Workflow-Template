# KiCad team workflow template

> [!IMPORTANT]
> **Examples are training fixtures, not starter projects.** Do real board work under
> `projects/<id>/` and integration work under `products/<id>/`. Use `examples/` only for a
> deliberate rehearsal or to maintain the regression fixtures. Example circuits, part identities,
> requirements and mechanical notes do not approve a real design, purchase, fit or manufacture.

A light template for independently developed boards, with engineering guidance and
installed [KiCad Tooling](https://github.com/sheepfling/KiCad-Tooling) for CLI and MCP automation.
Each project keeps its KiCad source, documentation, test expectations and release
records together. A battery board and a PWM board can be checked and released
independently; an optional product describes how they work together.

The tooling coaches a team through onboarding, triage, verification, BOM preparation,
plots and 3D review evidence. Its checks report their scope and findings; they do not
approve electrical design, part selection, physical fit, purchasing or manufacturing.

```text
projects/<id>/
  README.md
  project.json
  kicad/
  docs/
  tests/contract.json
  tests/test_*.py       # optional custom checks
  firmware/            # optional companion source
  releases/            # optional authored release records and frozen BOMs
  build/               # ignored exports and test evidence
```

Use [the documentation map](docs/README.md) to choose where information belongs,
[the folder standard](docs/workflow/REPOSITORY_STRUCTURE.md) for ownership and boundaries,
[Start here](docs/workflow/START_HERE.md) for adoption, [First board](docs/workflow/FIRST_BOARD.md)
for the shortest working path, and [the contributor guide](docs/workflow/CONTRIBUTOR_GUIDE.md) for
branches, review and handoff. The [worked examples](examples/README.md) use this same layout and
provide small, explicit training fixtures for workflow rehearsal. For grounding, startup/steady
power and high-frequency circuit checks, follow the
[electrical quickstart](docs/workflow/ELECTRICAL_ANALYSIS.md#quickstart): initialize pending
requirements, capture review inputs, check tools, then verify. Use
`kicad-team electrical-charts --receipt <analysis-receipt>` to export CSV, PNG and SVG from saved
simulations using the pinned environment below.

See also the [quick reference](docs/workflow/QUICK_REFERENCE.md),
[mechanical handoff](docs/workflow/MECHANICAL_HANDOFF.md), [metrics](docs/workflow/METRICS.md) and
[Markdown policy](docs/workflow/MARKDOWN_POLICY.md). The
[three-repository split](docs/workflow/TOOLING_SPLIT.md) explains the ownership of
project files, reusable Python tooling, and populated acceptance projects. The
[scaffold changelog](CHANGELOG.md) records workflow versions; these are separate from each board's
revision.

The original scaffold uses 0BSD; adopters choose their own project terms. For a
private company repository, use [bootstrap](docs/workflow/TEMPLATE_ADOPTION.md#bootstrap)
to start without upstream Git history or its root license, then choose company
terms before the first commit. See [licensing and adoption](docs/workflow/LICENSING.md).

## First-run setup

Install Git and Python 3.11+. From the repository root, create an environment and install
this project's exact tooling pin. On macOS/Linux:

```sh
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-tooling.txt
```

On Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-tooling.txt
```

If activation is unavailable, use `.venv/bin/python` and `.venv/bin/kicad-team` directly,
or `.venv\Scripts\python.exe` and `.venv\Scripts\kicad-team.exe` on Windows.
The requirements file installs the public tooling repository at a reviewed Git commit,
including project checks, MCP, charts and CAD conversion support. No PyPI publication is required.
The template itself is not a Python package. Verify the installation and initialize your fork:

```sh
kicad-team --version
kicad-team template doctor --format text
kicad-team template adopt --project-id my-hardware --format text
kicad-team template list --format text
```

Portable checks do not need KiCad after the Python environment is installed.
Native checks require the exact version selected by the project's `toolchain_id`
in `catalog/toolchains.json`; use the exact local installation or its pinned Docker image.
Initialization keeps examples as independent test fixtures, clears their live
catalog entries, and names your repository. Repeating it preserves your work.
`adopt` runs that transactional initialization and the complete portable gate in one
command. Use `init` separately when you need to review each step or before a new
bootstrap copy has Git history.
An empty fork passes scaffold checks and reports that no hardware was validated.

For agents that connect through MCP, the same installation provides `kicad-team-mcp`;
follow [the local MCP setup and board walkthrough](docs/workflow/MCP.md). It exposes
discovery, import triage, source/evidence reads and repair previews. Separate startup
flags enable project creation, reviewed edits, checks and exports through engineering
review packaging. Source commits still use normal Git.

## Start a board

```sh
kicad-team template new-project --project-id battery-board --kind pcb --toolchain kicad-10.0.5 --format text
kicad-team template new-project --project-id pwm-board --kind pcb --toolchain kicad-10.0.5 --format text
```

The command creates the folder, manifest, notes and test-contract skeleton. Create and save the
actual KiCad design in its `kicad/` folder, then complete its source inventory and electrical
expectations. An incomplete scaffold intentionally fails checks. It never copies a training circuit
into your design or overwrites a project. Discovery automatically adds each
`projects/*/project.json` to CI. Keep projects directly under `projects/`; discovery does not
recurse into a physical tree of nested projects. Use manifest tags for a flexible cohort and a
registered product for a named group of related deliverables. Before native work, run
`kicad-team template doctor --native --project-id battery-board --format text`. This checks
the board's catalogued toolchain and the runner that `kicad-team verify` will use.

For an existing design, use the [import workflow](docs/workflow/IMPORT_WORKFLOW.md).
Exercise imports in a temporary copy and retain each run through its PR or CI artifacts.
For a directory of candidate designs, `kicad-team template scan-imports` previews
every project without copying it; inspect the full JSON before importing each
accepted island.

## Checks

```sh
# One selected board with a fresh ignored receipt and repair guidance
kicad-team verify --project battery-board
# Include exact native KiCad checks after source changes
kicad-team verify --project battery-board --depth native
# Every project in a registered product, or every project carrying a tag
# The names below refer to the uninitialized template rehearsal examples.
kicad-team ci --product status-indicator-system --format text
kicad-team ci --tag status-led --format text
# Shared policy and tools, every project, all unit and project tests
kicad-team ci --format text
# Preview automatic native CI lanes
kicad-team ci --matrix --format text
# Lower-level pinned native check; supply a fresh output path yourself
kicad-team ci --kicad --project battery-board --output projects/battery-board/build/review-001 --format text
# Shared tooling tests alone
```

Use selected checks while developing a board. `--project`, `--product` and
`--tag` can be repeated and include the union of their matches; `--exclude-tag`
then removes matching projects. With only `--exclude-tag`, the starting set is
all discovered projects. The full command is appropriate for changes to shared
policy, tooling pins or catalogs and for a deliberate repository-wide rehearsal.
Pull requests use changed paths to run affected project and native lanes;
changes to tooling pins or an unrecognized path trigger the full gate. Main
pushes exercise the full gate. From GitHub Actions, run **KiCad template acceptance**
with the default `full` focus for a complete rehearsal, or choose `project`,
`product` or `tag` and supply its ID or tag to check just that group. An optional
`exclude_tag` narrows a focused manual run. A focused pass covers its declared
scope, while a release still has its own acceptance process.

See [checks and CI](docs/workflow/CHECKS_AND_CI.md) and
[extending tests](docs/workflow/PROJECT_TESTS.md). `kicad-team verify` defaults to a short text
result and writes the full typed JSON, stage log, portable result, and any native/diagnostic reports
in a unique ignored `build/diagnostics/` directory. Use `--format json` for agents and scripts,
`--detail full` for every repair finding, or `--runner local|container` to choose one exact native
runner; `auto` prefers a matching local CLI and otherwise uses the project's digest-pinned Docker
image. When a board fails, `kicad-team template diagnose --project-id battery-board` shows the
observed issue, a repair action and the relevant [diagnostic guide](docs/workflow/DIAGNOSTICS.md).
If an unrelated malformed manifest blocks that command,
`kicad-team template rescue --project-id battery-board` provides a local read-only repair view. It
always reports `UNVERIFIED_GLOBAL` and exits nonzero; repair discovery and rerun the normal gates
before relying on any result. Use `--detail full` for every finding or `--format json` for scripts;
each run saves a logged receipt under ignored `build/diagnostics/`. Coding agents can start with
[AGENTS.md](AGENTS.md) or [CLAUDE.md](CLAUDE.md). In an uninitialized template checkout, select
`arduino-uno-status-led`, `raspberry-pi-status-led` or `controller` for a bundled rehearsal.
Initialization removes these examples from live discovery; acceptance checks still use their
independent fixture catalogs. Close KiCad before native checks.

## BOMs and releases

For a new user's parts workflow, start with your registered project ID and
open the local assistant:

```sh
kicad-team template list --format text
kicad-team parts --project battery-board --assist
```

Replace `battery-board` with an ID from the first command. The assistant can fetch an exact LCSC
part, show paired STEP/WRL alignment views, add its reviewed project-local CAD, find 3D models for
placed footprints, and prepare part choices and order files. The STEP comparison needs Docker
running; other native board checks need Docker or a matching local KiCad CLI. Follow the
[first-part walkthrough](docs/workflow/CAD_SOURCING.md) for button-by-button instructions and
recovery steps. Update the PCB in KiCad when a selected footprint needs replacing. The plain command
without `--assist` creates an offline BOM and purchasing checklist. Follow
[choose parts and prepare an order](docs/workflow/PARTS_TO_ORDER.md) for saved preferences, model
synchronization and DigiKey upload. The training catalog has no production choices; add reviewed
part/CAD records before using the picker for a real board.

Commit authored design and BOM inputs. Generate working BOMs and review exports;
retain exact approved outputs when releasing or manufacturing. Authored assembly
lists and frozen release BOMs can be tracked. A generated file is not automatically
disposable, and a BOM should have one authoritative editing location. See the
[BOM policy](docs/workflow/BOM_POLICY.md), [release storage](docs/workflow/RELEASE_STORAGE.md) and
[versioning](docs/workflow/VERSIONING.md).

After committing reviewed source, prepare a standalone candidate with Docker running:

```sh
kicad-team release prepare --project battery-board --release-id battery-review-001
kicad-team release package --manifest build/releases/battery-review-001/manifest.json --output build/battery-review-001.zip
kicad-team release restore --archive build/battery-review-001.zip --destination ../battery-review-restored
```

Preparation runs portable tests and the pinned KiCad container. Packaging verifies the evidence and
performs a restore before completing. The default is an engineering review candidate; production
requires the controls in [release readiness](docs/workflow/RELEASE_READINESS.md).

## Shared areas

- [Projects](projects/README.md) own board-local work; [products](products/README.md)
  own optional integration records and tests.
- [Catalogs](catalog/README.md) own reusable identities, toolchains and discovery roots.
- [Libraries](libraries/README.md) contain declared shared CAD dependencies.
- Installed [tooling](https://github.com/sheepfling/KiCad-Tooling),
  [project tests](docs/workflow/PROJECT_TESTS.md) and [templates](templates/README.md)
  check and demonstrate the common workflow.
- [Generated shared views](generated/README.md) and [schemas](schemas/README.md)
  are optional local exports, ignored except for their guidance files.

The [authority model](docs/workflow/AUTHORITY_MODEL.md) distinguishes source, fixtures and release
evidence. [Assurance profiles](docs/workflow/ASSURANCE_PROFILES.md) distinguish training,
development and production. Complete [hosted governance](docs/workflow/GITHUB_GOVERNANCE.md) before
production adoption. [Template upgrades](docs/workflow/TEMPLATE_ADOPTION.md) record layout
migrations.
