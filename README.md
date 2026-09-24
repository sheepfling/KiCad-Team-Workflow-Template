# KiCad team workflow template

A forkable repository for independently developed boards with shared automation.
Each project keeps its KiCad source, documentation, test expectations and release
records together. A battery board and a PWM board can be checked and released
independently; an optional product describes how they work together.

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
[Start here](docs/workflow/START_HERE.md) for adoption, [First board](docs/workflow/FIRST_BOARD.md) for
the shortest working path, and [the contributor guide](docs/workflow/CONTRIBUTOR_GUIDE.md)
for branches, review and handoff. The [worked examples](examples/README.md) use this
same layout and provide regression fixtures for the shared tools.
See also the [quick reference](docs/workflow/QUICK_REFERENCE.md),
[mechanical handoff](docs/workflow/MECHANICAL_HANDOFF.md), [metrics](docs/workflow/METRICS.md)
and [Markdown policy](docs/workflow/MARKDOWN_POLICY.md). The [scaffold changelog](CHANGELOG.md)
records workflow versions; these are separate from each board's revision.

The original scaffold uses 0BSD; adopters choose their own project terms. For a
private company repository, use [bootstrap](docs/workflow/TEMPLATE_ADOPTION.md#bootstrap)
to start without upstream Git history or its root license, then choose company
terms before the first commit. See [licensing and adoption](docs/workflow/LICENSING.md).

## First-run setup

Install Git and Python 3.11+ (`python3` may be the executable name on macOS/Linux).
From the repository root:

```sh
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e '.[dev]'
# Once in your fork, before adding designs:
python -B -m tools.template doctor --format text
python -B -m tools.template adopt --project-id my-hardware --format text
python -B -m tools.template list --format text
```

If activation is unavailable, invoke `.venv/bin/python` or
`.venv\Scripts\python.exe` directly. Portable checks do not need KiCad after
Python dependencies are installed. Native checks require the exact version selected
by the project's `toolchain_id` in `catalog/toolchains.json`.
Initialization keeps examples as independent test fixtures, clears their live
catalog entries, and names your repository. Repeating it preserves your work.
`adopt` runs that transactional initialization and the complete portable gate in one
command. Use `init` separately when you need to review each step or before a new
bootstrap copy has Git history.
An empty fork passes scaffold checks and reports that no hardware was validated.

## Start a board

```sh
python -B -m tools.template new-project --project-id battery-board --kind pcb --toolchain kicad-10.0.5 --format text
python -B -m tools.template new-project --project-id pwm-board --kind pcb --toolchain kicad-10.0.5 --format text
```

The command creates the folder, manifest, notes and test-contract skeleton. Create
and save the actual KiCad design in its `kicad/` folder, then complete its source
inventory and electrical expectations. An incomplete scaffold intentionally fails
checks. It never copies a training circuit into your design or overwrites a project.
Discovery automatically adds each `projects/*/project.json` to CI.
Keep projects directly under `projects/`; discovery does not recurse into a
physical tree of nested projects. Use manifest tags for a flexible cohort and a
registered product for a named group of related deliverables.
Before native work, run `python -B -m tools.template doctor --native --toolchain kicad-10.0.5 --format text`.

For an existing design, use the [import workflow](docs/workflow/IMPORT_WORKFLOW.md).
Exercise imports in a temporary copy and retain each run through its PR or CI artifacts.

## Checks

```sh
# Selected board, its dependencies and applicable board/product tests
python -B -m tools.ci --project battery-board --format text
# Every project in a registered product, or every project carrying a tag
# The names below refer to the uninitialized template rehearsal examples.
python -B -m tools.ci --product status-indicator-system --format text
python -B -m tools.ci --tag status-led --format text
# Shared policy and tools, every project, all unit and project tests
python -B -m tools.ci --format text
# Preview automatic native CI lanes
python -B -m tools.ci --matrix --format text
# Pinned native check; use a fresh output path each attempt
python -B -m tools.ci --kicad --project battery-board --output projects/battery-board/build/review-001 --format text
# Shared tooling tests alone
python -B -m unittest discover -s tests -v
```

Use selected checks while developing a board. `--project`, `--product` and
`--tag` can be repeated and include the union of their matches; `--exclude-tag`
then removes matching projects. With only `--exclude-tag`, the starting set is
all discovered projects. The full command is appropriate for changes to shared
policy, tools or catalogs and for a deliberate repository-wide rehearsal.
Pull requests use changed paths to run affected project and native lanes;
changes to shared tooling or an unrecognized path trigger the full gate. Main
pushes exercise the full gate. From GitHub Actions, run **KiCad template acceptance**
with the default `full` focus for a complete rehearsal, or choose `project`,
`product` or `tag` and supply its ID or tag to check just that group. An optional
`exclude_tag` narrows a focused manual run. A focused pass covers its declared
scope, while a release still has its own acceptance process.

See [checks and CI](docs/workflow/CHECKS_AND_CI.md) and [extending tests](tests/README.md).
When a board fails, `python -B -m tools.template diagnose --project-id battery-board`
shows the observed issue, a repair action and the relevant [diagnostic guide](docs/workflow/DIAGNOSTICS.md).
Use `--detail full` for every finding or `--format json` for scripts; each run
saves a logged receipt under ignored `build/diagnostics/`. Coding agents can
start with [AGENTS.md](AGENTS.md) or [CLAUDE.md](CLAUDE.md).
In an uninitialized template checkout, select `arduino-uno-status-led`,
`raspberry-pi-status-led` or `controller` for a bundled rehearsal. Initialization
removes these examples from live discovery; shared-tool tests still use their
independent fixture catalogs. Close KiCad before native checks.

## BOMs and releases

Commit authored design and BOM inputs. Generate working BOMs and review exports;
retain exact approved outputs when releasing or manufacturing. Authored assembly
lists and frozen release BOMs can be tracked. A generated file is not automatically
disposable, and a BOM should have one authoritative editing location. See the
[BOM policy](docs/workflow/BOM_POLICY.md), [release storage](docs/workflow/RELEASE_STORAGE.md) and
[versioning](docs/workflow/VERSIONING.md).

After committing reviewed source, prepare a standalone candidate with Docker running:

```sh
python -B -m tools.release prepare --project battery-board --release-id battery-review-001
python -B -m tools.release package --manifest build/releases/battery-review-001/manifest.json --output build/battery-review-001.zip
python -B -m tools.release restore --archive build/battery-review-001.zip --destination ../battery-review-restored
```

Preparation runs portable tests and the pinned KiCad container. Packaging verifies
the evidence and performs a restore before completing. The default is an engineering
review candidate; production requires the controls in [release readiness](docs/workflow/RELEASE_READINESS.md).

## Shared areas

- [Projects](projects/README.md) own board-local work; [products](products/README.md)
  own optional integration records and tests.
- [Catalogs](catalog/README.md) own reusable identities, toolchains and discovery roots.
- [Libraries](libraries/README.md) contain declared shared CAD dependencies.
- [Tools](tools/README.md), [tests](tests/README.md) and [templates](templates/README.md)
  implement and demonstrate the common workflow.
- [Generated shared views](generated/README.md) and [schemas](schemas/README.md)
  are optional local exports, ignored except for their guidance files.

The [authority model](docs/workflow/AUTHORITY_MODEL.md) distinguishes source, fixtures and
release evidence. [Assurance profiles](docs/workflow/ASSURANCE_PROFILES.md) distinguish
training, development and production. Complete [hosted governance](docs/workflow/GITHUB_GOVERNANCE.md)
before production adoption. [Template upgrades](docs/workflow/TEMPLATE_ADOPTION.md) record
layout migrations.
