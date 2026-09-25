# Checks and CI

The same shared runner checks project islands locally and in hosted CI.
If a selected project fails, use the [diagnostic command](DIAGNOSTICS.md) to pair
portable, native and BOM findings with specific repair steps.
Add `--format text` to `tools.ci` for a short terminal summary or keep its default
JSON for complete structured results and CI. `tools.template diagnose` defaults
to a short repair queue; `--detail full` expands it, and `--format json` emits
the complete typed diagnostic report. Other `tools.template` commands default
to JSON and accept `--format text` for a human summary. Exit status remains
nonzero on a failed check in either format.

| Check scope | What runs |
| --- | --- |
| `python -B -m tools.verify --project <id>` | Selected portable project checks; fresh ignored receipt and repair guidance |
| `python -B -m tools.verify --project <id> --depth native` | Selected portable checks followed by native validation with an exact local CLI or the project's digest-pinned Docker image |
| `python -B -m tools.ci` | Live discovery/registry, dependency/source hygiene, product policy, fresh generation, Markdown, Ruff, strict tool types, shared unit tests and every project/product Python suite |
| `python -B -m tools.ci --project <id>` | Selected project inputs, shared dependency policy, products declaring that project, fresh applicable views and its project/dependent-product Python suites |
| `python -B -m tools.ci --product <id>` | All projects registered as members of that product, plus their applicable product tests and policy checks |
| `python -B -m tools.ci --tag <tag>` | Projects carrying that manifest tag and their applicable product tests and policy checks |
| `python -B -m tools.ci --matrix` | One native lane per discovered manifest, using its catalogued toolchain |
| `python -B -m tools.ci --kicad --project <id> --output <new-path>` | Native checks for the selected board, after registry, dependency/source hygiene and product preflight |

Portable checks do not execute KiCad. The selected portable lane omits shared-tool
unit tests, Ruff, Pyright and repository-wide Markdown policy; use the full command
when changing shared tooling or policy. Native checks do not replace Python suites
or physical engineering tests.

For required ground-pin connectivity, startup/steady-state budgets and ngspice
waveform checks, follow [electrical analysis](ELECTRICAL_ANALYSIS.md).
`tools.verify --project <id> --depth electrical` runs native checks followed by the
configured simulations. `tools.ci --electrical` exposes the separate electrical gate.

## Daily commands

```sh
python -B -m tools.verify --project raspberry-pi-status-led
python -B -m tools.verify --project raspberry-pi-status-led --depth native
python -B -m tools.verify --project raspberry-pi-status-led --depth native --runner container
python -B -m tools.ci --project raspberry-pi-status-led --format text
python -B -m tools.ci --product status-indicator-system --format text
python -B -m tools.ci --tag status-led --format text
python -B -m tools.ci --tag status-led --exclude-tag legacy --format text
python -B -m tools.ci --exclude-tag legacy --format text
python -B -m tools.ci --format text
python -B -m tools.ci --jobs 4 --output build/portable-review --format text
python -B -m tools.ci --matrix --format text
python -B -m tools.ci --matrix --product status-indicator-system --format text
python -B -m tools.ci --kicad --project controller --output examples/projects/controller/build/review-001 --format text
python -B -m tools.hardware generate --format text
python -B -m tools.template doctor --format text
python -B -m tools.template doctor --native --project-id raspberry-pi-status-led --format text
python -B -m tools.template preflight --format text
python -B -m tools.docs_policy
```

`--project`, `--product` and `--tag` may each be repeated. They select the union
of IDs, registered product members and manifest tags; `--exclude-tag` removes
matching projects afterward. For example, `--tag power --exclude-tag legacy`
checks non-legacy power boards in an adopted repository. With only `--exclude-tag`,
the starting set is all discovered projects. Unknown IDs/products/tags or a selection
matching no projects fail. No selector means the full set. Tags belong in each
`project.json`; product membership belongs in `catalog/products.json`. Custom
project/product tests run in separate Python processes; add `test_*.py` files
without editing the workflow.
`--jobs <n>` runs up to that many independent project/product Python suites at
once, with deterministic per-island results. The default is one for local runs;
hosted portable jobs use four. Project tests must keep their temporary work in
their own island or a private temporary directory rather than a shared path.
See [test extension](../../tests/README.md).

Native output directories and review snapshots are write-once. Use a fresh path each
attempt and close KiCad first. PCB projects receive ERC, DRC/parity, netlist identity
and schematic/PCB SVG checks. PCB-only projects receive DRC and a PCB SVG only; they
remain not for manufacture until an authoritative schematic makes full electrical
validation possible. Schematic projects receive ERC and schematic SVG; wiring and
harness views also receive their typed relationship coverage checks.
All native kinds protect declared source hashes.
`tools.verify` creates a fresh path under ignored
`build/diagnostics/<project>-.../`. Its default terminal view is brief; use
`--detail full` for every diagnosed finding or `--format json` for a typed agent
result. The receipt contains `events.log`, `run.json`, `verification.json`,
`portable.json`, optional `doctor.json`, and native reports and raw command
stdout/stderr. Native failures also create `diagnosis.txt` and `diagnosis.json`
when a project report is available. A runner or package-setup failure retains
`dependency-command.json` or `native-command.json` with an actionable next step.
An optional `--output build/<new-name>` chooses a fresh ignored receipt path.

## Adding and sharing projects

Create `projects/<id>/project.json` and its local source/contract files, or use
`tools.template new-project` or the [import command](IMPORT_WORKFLOW.md). Do not edit a list of CI lanes. `catalog/projects.json`
selects discovery roots and shared catalogs; each manifest owns its metadata.
Unregistered native files, duplicate IDs and misplaced project folders fail.

Each shared-library consumer declares the exact shared files it needs. A change
to a declared shared asset selects its consumers for hosted project and native
checks. Run the full command when intentionally rehearsing every consumer.
Discovery is one level below each configured project root: `projects/<id>/` and,
before adoption, `examples/projects/<id>/`. A nested path such as
`projects/power/battery-board/` is not a project island. Use tags for cohorts or
a product record for cross-board integration instead of a second directory level.

## Which scope to run

The quick local loop is `tools.verify --project <id>`; add `--depth native`
when native inputs change. `--runner auto` uses an installed exact-version CLI
first, then the project's digest-pinned Docker image. `--runner local` or
`--runner container` makes that choice explicit.
`tools.template doctor --native --project-id <id> --runner <choice>` checks the
same runner readiness. An explicit `--runner local|container` requires
`--native`; portable doctor checks alone cannot establish native readiness.
The lower-level `tools.ci --kicad` remains useful in CI
or when you manage the
evidence path yourself; it does not choose Docker automatically. A tag or
product selects a larger group without naming each member.
When passing `--cli ./path/to/kicad-cli`, the relative path is resolved from
the directory where you invoke the command, even if `--root` points to another
repository directory. An executable name without a slash is found on `PATH`.
`tools.ci --matrix --project <id>` previews just the selected native job.
Use `tools.ci` without a selector for a full portable rehearsal, especially
after changing shared tooling, catalog policy, or release behavior.

`tools.impact --base <ref> --head <ref> --format text` previews the PR scope
from changed Git paths; use `--format json` for an agent or script. It reports
which projects are selected and why. Direct project changes select that island,
product changes select its member projects, and declared shared-library changes
select their consumers. Ambiguous or shared-tool changes escalate to full scope.
An engineer can therefore verify a board without rerunning unrelated historical
projects on each edit, while still seeing when a change has broad impact.

To preview a manual focused run, use
`python -B -m tools.impact --select-project battery-board --format text`,
`--select-product <product-id>` or `--select-tag <tag>`. Add
`--exclude-tag <tag>` to remove a cohort; an empty or unknown selection fails.
`python -B -m tools.impact --full --format text` previews full acceptance. The
impact CLI prints a typed JSON plan by default for automation. Each manual
selector chooses one project, product or tag; the local `tools.ci` command can
combine multiple selectors when needed.

## Hosted execution

Actions installs dependencies from `pyproject.toml`. Pull requests that change
only project/product inputs run selected portable checks on Ubuntu and native
validation only for affected projects in their digest-pinned KiCad images.
If a focused PR also edits Markdown, it runs the Markdown policy as well.
Documentation-only PRs run only that policy.
Markdown explicitly referenced by a project or product contract is an engineering
input and selects its affected native lanes even when it lives in `docs/`.
Changes to common tools, catalogs, workflow configuration or unrecognized paths receive full
portable coverage on Linux and macOS, a Windows smoke lane, and all native lanes.
The Linux full lane also type-checks the Windows target. Pushes to main
always receive that full scope. In GitHub Actions, open **KiCad template acceptance**
and choose **Run workflow** on the desired branch. The `focus` input defaults
to `full`. For a fast hosted check, choose `project`, `product` or `tag`, enter
its ID or tag in `value`, and optionally set `exclude_tag`. A focused manual
run uses Ubuntu portable checks and selected native lanes; a full manual run
uses Linux/macOS portable checks, Windows smoke, every native lane and the release
rehearsal. The controller's native fault probes run only for its known reference
path when that project is in scope.
Manual runs use distinct concurrency groups, so starting a focused check cannot
cancel a main-branch full acceptance run or another engineer's manual check.
The template pins its direct runtime and development-tool dependencies in
`pyproject.toml`; each direct dependency selects its published compatible transitive
requirements. Update direct pins as a reviewed change and rerun the portable/native
acceptance lanes.
Dependabot opens bounded monthly Python and GitHub Actions update pull requests;
these change common dependencies or workflow files and receive full acceptance.
The final acceptance check requires the jobs scheduled for its declared scope
to pass; a skipped native lane is acceptable only when no project is in scope.
Full runs with projects also require a standalone release/restore rehearsal. The rehearsal commits a disposable
reference checkout, exports using pinned KiCad, prepares an engineering-review
manifest, packages it and verifies an actual restore. It does not approve hardware.
Native jobs start after impact planning and run alongside the portable OS jobs;
the full-scope release rehearsal starts after native jobs, without waiting for
Windows. The Windows smoke installs the policy package, inventories projects through
the CLI, and exercises subprocess entry points, path validation, PowerShell quoting
and container command construction on a real Windows runner. It does not rerun the
shared unit suite, project suites, or generated exports. Linux and macOS run the
full portable gate; Linux also runs Pyright against the Windows target to catch
Windows-specific typing errors. Adding projects increases the cost of a full run.
A project-only PR adds
work for its affected projects and their dependents, not every historical board.
Native jobs can run concurrently subject to hosted runner capacity, so elapsed
time need not grow one-for-one with project count; total CI compute and queue
time can still grow.
Portable jobs use a pip download cache keyed by `pyproject.toml`, Python and
runner OS; installation and each job's planned checks still run on every job.
Their project
Python suites run with four bounded workers. Full portable jobs have a separate
pipeline step timeout so evidence upload can still run after a timed-out check.
The Windows smoke has its own shorter timeout and uploads its inventory and test log.

An initialized fork with no projects emits an empty matrix. The final check still
requires applicable policy success and states that no hardware was validated.
Unknown project selectors and broken discovery still fail. A docs-only PR has
no native matrix; its impact plan explains that decision.

Full CI uploads shared schema/library exports, product-local generated views,
native review evidence, portable reports and the rehearsed package. Focused
CI retains selected portable and native review evidence. Reports record the
observed source commit and file hashes. Dirty local reports remain useful for
development but cannot supply release evidence. Configure artifact retention and required branch checks during
[adoption](START_HERE.md); a configured workflow is not evidence of a hosted run.
When `tools.ci --output <new-directory>` is used, `events.jsonl` and `run.json`
appear as phases start, and each completed phase gets its own JSON report before
the final `portable.json` is written. The same stage progress appears in terminal
and Actions logs. A missing `portable.json` means the gate did not finish; partial
phase evidence is for diagnosis only, never release acceptance.

## Replaying a native CI lane locally

The one-command route is
`python -B -m tools.verify --project <id> --depth native --runner container`.
It resolves the exact image from that project's
catalog record, prepares container-compatible wheels, runs only that board, and
retains the attempted commands in a fresh ignored receipt. Run `--runner local`
when the exact declared KiCad CLI is installed. A failed doctor names a missing
Docker daemon or version mismatch before native work starts. The manual commands
below remain available for reproducing individual CI setup stages.

The official pinned images do not include pip. `tools.native_deps` probes the image's
Python version and uses host pip to prepare compatible Linux x86 wheels from
`pyproject.toml` in an ignored directory. The image itself remains unchanged.
Install the repository's Python environment first, then use the image string from
`catalog/toolchains.json` for the selected project. On a macOS/Linux Docker host:

```sh
# Set KICAD_IMAGE to the exact image selected by the project's toolchain.
python -B -m tools.native_deps --image "$KICAD_IMAGE" --output build/policy-deps
docker run --rm --platform linux/amd64 --user "$(id -u):$(id -g)" --entrypoint sh \
  -e HOME=/tmp/kicad-template -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPATH=/work/build/policy-deps -v "$PWD:/work" -w /work "$KICAD_IMAGE" \
  -ec 'python3 -m tools.ci --kicad --project battery-board --output build/review-001'
```

Use a new dependency directory for a different image/runtime and a fresh evidence
directory for each native attempt. The native CI job uses this same setup. The
x86 image can run under Docker emulation on Apple Silicon; native Windows execution
of these shell examples is not provided. CI keeps dependency wheels out of review
artifacts. Its hosted job scheduling, permissions and upload remain separate from a
local container rehearsal.
