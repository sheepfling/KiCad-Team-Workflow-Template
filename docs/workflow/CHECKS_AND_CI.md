# Checks and CI

The same shared runner checks project islands locally and in hosted CI.
If a selected project fails, use the [diagnostic command](DIAGNOSTICS.md) to pair
portable, native and BOM findings with specific repair steps.
Add `--format text` to `kicad-team ci` for a short terminal summary or keep its default
JSON for complete structured results and CI. `kicad-team template diagnose` defaults
to a short repair queue; `--detail full` expands it, and `--format json` emits
the complete typed diagnostic report. Other `kicad-team template` commands default
to JSON and accept `--format text` for a human summary. Exit status remains
nonzero on a failed check in either format.

| Check scope                                                | What runs                                                                                                                                                  |
| ---------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `kicad-team verify --project <id>`                         | Selected portable project checks; fresh ignored receipt and repair guidance                                                                                |
| `kicad-team verify --project <id> --depth native`          | Selected portable checks followed by native validation with an exact local CLI or the project's digest-pinned Docker image                                 |
| `kicad-team ci`                                            | Live discovery/registry, dependency/source hygiene, product policy, fresh generation, Markdown and every project/product Python suite                      |
| `kicad-team ci --project <id>`                             | Selected project inputs, shared dependency policy, products declaring that project, fresh applicable views and its project/dependent-product Python suites |
| `kicad-team ci --product <id>`                             | All projects registered as members of that product, plus their applicable product tests and policy checks                                                  |
| `kicad-team ci --tag <tag>`                                | Projects carrying that manifest tag and their applicable product tests and policy checks                                                                   |
| `kicad-team ci --matrix`                                   | One native lane per discovered manifest, using its catalogued toolchain                                                                                    |
| `kicad-team ci --kicad --project <id> --output <new-path>` | Native checks for the selected board, after registry, dependency/source hygiene and product preflight                                                      |

Portable checks do not execute KiCad. Selected lanes omit repository-wide Markdown policy;
use the full command when changing catalogs, requirements pins or repository-wide policy.
Shared implementation regressions, Ruff, Pyright and CLI/MCP behavioral comparisons run in
the tooling repository. Project checks consume that installed package. Native checks do not
replace project Python suites or physical engineering tests.

For required ground-pin connectivity, startup/steady-state budgets and ngspice
waveform checks, follow [electrical analysis](ELECTRICAL_ANALYSIS.md).
`kicad-team verify --project <id> --depth electrical` runs native checks followed by the
configured simulations. `kicad-team ci --electrical` exposes the separate electrical gate.

## Daily commands

```sh
kicad-team verify --project raspberry-pi-status-led
kicad-team verify --project raspberry-pi-status-led --depth native
kicad-team verify --project raspberry-pi-status-led --depth native --runner container
kicad-team ci --project raspberry-pi-status-led --format text
kicad-team ci --product status-indicator-system --format text
kicad-team ci --tag status-led --format text
kicad-team ci --tag legacy --format text
kicad-team ci --tag training --shard 1/3 --jobs 4 --format text
kicad-team ci --tag status-led --exclude-tag legacy --format text
kicad-team ci --exclude-tag legacy --format text
kicad-team ci --format text
kicad-team ci --jobs 4 --output build/portable-review --format text
kicad-team ci --matrix --format text
kicad-team ci --matrix --product status-indicator-system --format text
kicad-team ci --kicad --project controller --output examples/projects/controller/build/review-001 --format text
kicad-team hardware generate --format text
kicad-team template doctor --format text
kicad-team template doctor --native --project-id raspberry-pi-status-led --format text
kicad-team template preflight --format text
kicad-team docs-policy
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
`--shard INDEX/COUNT` divides the selected project IDs into one-based, sorted
round-robin shards. For example, `--tag training --shard 1/3` runs the first third
of the training project cohort; `--tag legacy` runs the legacy cohort directly.
A shard is always a partial focused result, including when no tag is supplied.
It never claims full acceptance or release coverage. Every shard must contain a
project; invalid or empty selections fail. Run every shard and then the full
gate before using complete repository evidence. The same `shard` option is
available in `kicad-team impact`, MCP `plan_impact` and MCP `check_scope`.

`--jobs <n>` runs up to that many independent project/product Python suites at
once, with deterministic per-island results. The default is one for local runs;
hosted portable jobs use four. Project tests must keep their temporary work in
their own island or a private temporary directory rather than a shared path.
See [test extension](PROJECT_TESTS.md).

Native output directories and review snapshots are write-once. Use a fresh path each
attempt and close KiCad first. PCB projects receive ERC, DRC/parity, netlist identity
and schematic/PCB SVG checks. PCB-only projects receive DRC and a PCB SVG only; they
remain not for manufacture until an authoritative schematic makes full electrical
validation possible. Schematic projects receive ERC and schematic SVG; wiring and
harness views also receive their typed relationship coverage checks.
All native kinds protect declared source hashes.
`kicad-team verify` creates a fresh path under ignored
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
`kicad-team template new-project` or the [import command](IMPORT_WORKFLOW.md). Do not edit a list of
CI lanes. `catalog/projects.json` selects discovery roots and shared catalogs; each manifest owns
its metadata. Unregistered native files, duplicate IDs and misplaced project folders fail.

Each shared-library consumer declares the exact shared files it needs. A change
to a declared shared asset selects its consumers for hosted project and native
checks. Run the full command when intentionally rehearsing every consumer.
Discovery is one level below each configured project root: `projects/<id>/` and,
before adoption, `examples/projects/<id>/`. A nested path such as
`projects/power/battery-board/` is not a project island. Use tags for cohorts or
a product record for cross-board integration instead of a second directory level.

## Which scope to run

The quick local loop is `kicad-team verify --project <id>`; add `--depth native`
when native inputs change. `--runner auto` uses an installed exact-version CLI
first, then the project's digest-pinned Docker image. `--runner local` or
`--runner container` makes that choice explicit.
`kicad-team template doctor --native --project-id <id> --runner <choice>` checks the
same runner readiness. An explicit `--runner local|container` requires
`--native`; portable doctor checks alone cannot establish native readiness.
The lower-level `kicad-team ci --kicad` remains useful in CI
or when you manage the
evidence path yourself; it does not choose Docker automatically. A tag or
product selects a larger group without naming each member.
When passing `--cli ./path/to/kicad-cli`, the relative path is resolved from
the directory where you invoke the command, even if `--root` points to another
repository directory. An executable name without a slash is found on `PATH`.
`kicad-team ci --matrix --project <id>` previews just the selected native job.
Use `kicad-team ci` without a selector for a full portable rehearsal, especially
after changing shared tooling, catalog policy, or release behavior.

`kicad-team impact --base <ref> --head <ref> --format text` previews the PR scope
from changed Git paths; use `--format json` for an agent or script. It reports
which projects are selected and why. Direct project changes select that island,
product changes select its member projects, and declared shared-library changes
select their consumers. Ambiguous or shared-tool changes escalate to full scope.
An engineer can therefore verify a board without rerunning unrelated historical
projects on each edit, while still seeing when a change has broad impact.

To preview a manual focused run, use
`kicad-team impact --select-project battery-board --format text`,
`--select-product <product-id>` or `--select-tag <tag>`. Add
`--exclude-tag <tag>` to remove a cohort or `--shard INDEX/COUNT` to preview one
partial shard; an empty or unknown selection fails.
`kicad-team impact --full --format text` previews full acceptance. The
impact CLI prints a typed JSON plan by default for automation. Each manual
selector chooses one project, product or tag; the local `kicad-team ci` command can
combine multiple selectors when needed.

## Hosted execution

Actions installs the reviewed tooling pin from `requirements-tooling.txt`. Pull requests that
change only project/product inputs run selected portable checks on Ubuntu and native validation
for affected projects in their digest-pinned KiCad images. A focused PR that also changes Markdown
runs documentation policy; documentation-only PRs run that policy. Markdown referenced by a project
or product contract is an engineering input and selects affected native lanes even under `docs/`.
Shared catalogs, dependency pins, workflow configuration and unrecognized paths receive full
portable coverage on Linux/macOS, Windows project-policy checks and all applicable native lanes.
Pushes to main always receive the full scope. The separate tooling repository owns package
regressions and type/lint checks.

In Actions, open **KiCad template acceptance** and choose **Run workflow**. The `focus` input
is `full` by default. For a focused run choose `project`, `product` or `tag`, set `value` to its
ID/tag, and optionally set `exclude_tag` or a partial `shard` such as `1/3`. Choose `branch` with
`value=origin/main` to compare the selected branch with that base. Shards are partial runs and
never establish full acceptance. Focused runs use Ubuntu portable checks and selected native
lanes; full runs add all portable platform lanes and the release/restore rehearsal.

The final acceptance check requires the jobs scheduled for its declared scope. A skipped native
lane is acceptable only when no project is in scope. Full runs with projects also require a
standalone release/restore rehearsal: a disposable reference checkout is committed, checked and
exported with pinned KiCad, prepared as an engineering-review candidate, packaged and restored.
This does not approve hardware. The controller's native fault probes run only for its known
reference path when that project is selected.

Native jobs run alongside portable platform jobs after impact planning. The release rehearsal
follows native jobs. Manual runs have distinct concurrency groups, so they do not cancel main
acceptance or another engineer's manual run. More projects increase full-run cost; focused checks
select affected islands and dependents. Native parallelism depends on hosted runner capacity.
Portable jobs cache downloads by requirements pin, Python and OS while still installing and
checking every run. Project suites use four bounded workers in hosted portable runs.

The Actions YAML declares scheduling, runner choice and artifact uploads; installed
`kicad-team ci-hosted` owns planning, lane commands, native setup, release rehearsal and final
outcome rules. It writes stage events and separate command output under ignored
`build/ci-hosted/<lane>/`, including failed and documentation-only runs. Windows inventories the
installed CLI and checks project policy; it does not duplicate the tooling package's regression
suite. Run the same plan locally:

```sh
kicad-team ci-hosted plan --focus tag --value legacy
kicad-team ci-hosted plan --focus branch --value origin/main
```

`kicad-team ci --tag legacy` or `kicad-team ci --project <id>` executes project checks directly;
MCP `check_scope` shares project/tag/shard selection and bounded `jobs` concurrency.
Update tooling pins through review and rerun affected portable/native acceptance. Configure
hosted dependency updates around the committed requirements and workflow files; an updated pin
or configured workflow is not evidence that a hosted run has passed.

An initialized fork with no projects emits an empty matrix. The final check still
requires applicable policy success and states that no hardware was validated.
Unknown project selectors and broken discovery still fail. A docs-only PR has
no native matrix; its impact plan explains that decision.

Full CI uploads shared schema/library exports, product-local generated views, native review
evidence, portable reports and the rehearsed package. Focused CI retains selected portable and
native review evidence. Reports record the observed source commit and file hashes. Dirty local
reports remain useful for development but cannot supply release evidence. Configure artifact
retention and required branch checks during [adoption](START_HERE.md); a configured workflow is not
evidence of a hosted run. When `kicad-team ci --output <new-directory>` is used, `events.jsonl` and
`run.json` appear as phases start, and each completed phase gets its own JSON report before the
final `portable.json` is written. The same stage progress appears in terminal and Actions logs. A
missing `portable.json` means the gate did not finish; partial phase evidence is for diagnosis only,
never release acceptance.

## Replaying a native CI lane locally

The one-command route is
`kicad-team verify --project <id> --depth native --runner container`.
It resolves the exact image from that project's
catalog record, prepares container-compatible wheels, runs only that board, and
retains the attempted commands in a fresh ignored receipt. Run `--runner local`
when the exact declared KiCad CLI is installed. A failed doctor names a missing
Docker daemon or version mismatch before native work starts. The manual commands
below remain available for reproducing individual CI setup stages.

Linked Git worktrees are supported: the Python validation and release/export
runners mount shared Git metadata read-only and retain the worktree's own commit
and index. Docker needs access to both the worktree and its shared Git directory.

The official pinned images do not include pip. `kicad-team native-deps` probes the image's
Python version, creates a standard native virtual environment, and uses host pip to prepare
compatible Linux x86 dependencies in its site-packages alongside the installed tooling.
The image itself remains unchanged; no project directory is added to Python's import path.
Install the repository's Python environment first, then use the image string from
`catalog/toolchains.json` for the selected project. On a macOS/Linux Docker host:

```sh
# Set KICAD_IMAGE to the exact image selected by the project's toolchain.
kicad-team native-deps --image "$KICAD_IMAGE" --output build/policy-deps
docker run --rm --platform linux/amd64 --user "$(id -u):$(id -g)" --entrypoint sh \
  -e HOME=/tmp/kicad-template -e PYTHONDONTWRITEBYTECODE=1 \
  -v "$PWD:/work" -w /work "$KICAD_IMAGE" \
  -ec '/work/build/policy-deps/bin/python -I -B -m kicad_tooling.ci --kicad --project battery-board --output build/review-001'
```

Use a new dependency directory for a different image/runtime and a fresh evidence
directory for each native attempt. The native CI job uses this same setup. The
x86 image can run under Docker emulation on Apple Silicon; native Windows execution
of these shell examples is not provided. CI keeps dependency wheels out of review
artifacts. Its hosted job scheduling, permissions and upload remain separate from a
local container rehearsal.
