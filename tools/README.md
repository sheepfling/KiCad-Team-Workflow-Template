# Repository tools

Run every CLI from the repository root as `python -B -m tools.<command>`.
For one board, start with `tools.verify --project <id>`; add `--depth native`
after editing KiCad source. `tools.ci` runs the shared or hosted gate and exposes
lower-level selected lanes. See the [command guide](../docs/workflow/CHECKS_AND_CI.md).
Use `python -B -m tools.template list --format text` to find registered project,
product, tag and toolchain IDs before selecting a lane. Its `readiness` field only
reports whether declared inputs are present; run checks to validate a design.
For one engineer's board, `tools.verify --project <id>` runs the selected
portable lane and keeps a fresh ignored receipt; add `--depth native` to choose
the exact local KiCad CLI or the project's pinned Docker image automatically.
Use `tools.ci --kicad` when direct native-lane control is needed.
Use `--project <id>` for one island, `--product <id>` for a registered product's
members, or `--tag <tag>` for a manifest cohort. These include selectors form
a union; `--exclude-tag <tag>` removes matches. The selected portable lane
runs applicable project/product checks; the unselected lane runs the full
shared regression and quality gate. `tools.ci --matrix` and `tools.ci --kicad`
accept the same selectors for native work. Run
`python -B -m tools.impact --base <ref> --head <ref>` to preview changed-file
PR scope and why projects were chosen. For a manual hosted run, use
`tools.impact --select-project <id>`, `--select-product <id>` or
`--select-tag <tag>` to preview one focused selection; `--full` previews the
default full run.
For a legacy directory with several projects, `tools.template scan-imports`
previews each candidate without copying it. JSON retains per-file hashes and
exclusion reasons; import one accepted project at a time.
The CLIs use `argparse`; a Typer dependency is not required for human output.
Choose text for a concise terminal view and JSON for the complete typed result:

| User-facing command | Human view | Agent/script view |
| --- | --- | --- |
| `tools.electrical --project <id>` | Brief status, failed checks and receipt; `--detail full` expands it | `--format json` |
| `tools.electrical --project <id> --init` / `--capture-inputs` | Create pending requirements / capture UNREVIEWED hashes for review | `--format json`; success is setup only |
| `tools.template doctor --electrical --project-id <id>` | `--format text` checks contract, native runner and exact simulator | JSON by default |
| `tools.verify --project <id>` | Brief text by default; `--detail full` expands repair findings | `--format json` |
| `tools.template diagnose` | Brief text by default; `--detail full` expands it | `--format json` |
| `tools.template list` | `--format text` shows selections and next commands | JSON by default; typed inventory |
| `tools.template rescue --project-id <id>` | Brief local repair view, always unverified; `--detail full` expands it | `--format json` with `UNVERIFIED_GLOBAL` and no CI/release eligibility |
| `tools.governance_audit` | `--format text` shows observed GitHub controls and next actions | JSON by default; `UNKNOWN` stays explicit |
| `tools.contract_coach` | Short UNREVIEWED contract comparison; `--detail full` expands it | `--format json` |
| `tools.visualize --project <id>` | 3D model audit and export paths; `--init-model-map` drafts explicit assignments, `--map-models` previews source edits and `--apply` writes reviewed edits | `--format json` |
| Other `tools.template` commands; `tools.ci`, `tools.hardware`, `tools.sourcing`, `tools.metrics` | `--format text` | JSON by default |
| `tools.release prepare` | Text by default | `--format json` or `--json` |
| Other `tools.release` commands | `--format text` | JSON by default |

The lower-level runner modules in the table below remain JSON-first adapters.
Do not scrape human text in automation; check the exit status and parse stdout JSON.
Agents with shell access can call these CLIs directly. An MCP server is optional
integration work, not a prerequisite for repository policy.

| Module | Responsibility |
| --- | --- |
| `electrical`, `hwrepo/electrical.py`, `hwrepo/electrical_runner.py`, `hwrepo/spice.py` | Check reviewed ground-pin coverage, power budgets and source-bound ngspice power/frequency cases; see [electrical analysis](../docs/workflow/ELECTRICAL_ANALYSIS.md) |
| `hwrepo/electrical_setup.py`, `hwrepo/electrical_doctor.py` | Initialize pending requirements without overwriting them, capture review hashes and preflight exact simulator readiness |
| `verify` | One-board portable/native/electrical run, exact runner choice, and a fresh logged repair receipt |
| `ci`, `ci_matrix`, `check_all` | Coordinate the portable gate, registry-driven matrix and native lanes |
| `impact`, `hwrepo/impact.py` | Plan affected PR project lanes from changed paths; broaden ambiguous/shared-tool changes to full scope |
| `native_deps` | Prepare Linux wheels for the pinned container's Python, without requiring pip inside the image |
| `validate`, `check_toolchain`, `fault_probe` | Adapt the pinned KiCad CLI, preserve source hashes and test deliberate native defects |
| `contract_coach`, `hwrepo/contract_coach.py` | Capture or inspect a source-bound netlist using exact local KiCad or the digest-pinned Docker image, compare it with independently authored expectations and retain ignored review evidence |
| `visualize`, `hwrepo/model_inventory.py`, `hwrepo/model_population.py`, `hwrepo/three_d.py` | Check PCB 3D references, explicitly map reviewed source models onto unassigned footprints, and generate ignored board images, STEP and GLB with the selected exact KiCad runner; see the [3D workflow](../docs/workflow/THREE_D_WORKFLOW.md) |
| `lint_registry`, `docs_policy` | Expose registry and Markdown policy |
| `hardware` | Check products, generate ignored review views/schemas, create and verify snapshots |
| `template`, `release`, `sourcing`, `metrics` | Expose environment and project diagnostics, adoption, release readiness, supplier snapshots and current policy metrics |
| `governance_audit`, `hwrepo/hosted_governance.py` | Read GitHub branch controls and CODEOWNERS without changing hosted settings |
| `hwrepo/models.py`, `hwrepo/contracts.py` | Own typed serialized contracts and file/path adapters |
| `hwrepo/discovery.py`, `hwrepo/project_tests.py`, `hwrepo/scaffold.py`, `hwrepo/importing.py` | Resolve local manifests, run isolated island test suites and create or import project islands |
| `hwrepo/doctor.py`, `hwrepo/adoption.py` | Check local prerequisites and run one-command fresh-fork adoption |
| Other `hwrepo/` modules | Implement named policy and generation services behind the CLIs |

Add substantial rules to the appropriate service and behavioral coverage to
[tests](../tests/README.md). New projects and variants are records, not new scripts.
Outputs belong in ignored locations and must never rewrite native design source.
