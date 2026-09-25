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
Start with `tools.parts --project <id> --assist` for one local page that resolves
paired CAD automatically, reviews source changes, chooses parts and produces order
files. `--auto-models` exposes automatic CAD previews to scripts.
For file-based component selection, use `tools.parts --project <id> --picker` to choose
reviewed catalog parts in a local page. `--selection <download>` previews changes;
`--selection <locked-file> --apply` applies them. Use `--sync-models` after KiCad's
PCB update when footprints needed replacing or adding. The plain
`tools.parts --project <id>` command reads source to make an offline checklist,
grouped BOM and conditional DigiKey upload CSV. Follow the
[parts-to-order guide](../docs/workflow/PARTS_TO_ORDER.md); receipts stay in ignored
`build/parts/`, and ordering remains a separate human action.
For catalog-derived BOMs, harness schedules and review views, run
`tools.hardware generate`. It accepts the same repeatable `--project`, `--product`,
`--tag` and `--exclude-tag` selectors as MCP `generate_views`. Includes form a
union before exclusions; selected projects bring their dependent product views.
Add `--output build/views/my-review` to retain a fresh projection directory.
The directory must be new; in-checkout destinations must be below `build/`.
Without `--output`, generation retains the existing schema, shared-view and
product `build/` locations. These projections do not authorize manufacture.
For a non-KiCad board, `tools.template convert-pcb` uses an exact KiCad runner
to make an ignored conversion receipt and native import preview. Review the
converted geometry and KiCad report before running its separate `import-project`
command; see the [import workflow](../docs/workflow/IMPORT_WORKFLOW.md).
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
| `tools.template convert-pcb --source <file> --project-id <id> --toolchain <id>` | Conversion status, receipt and review steps | `--format json` with source/output hashes, commands and import preview |
| `tools.governance_audit` | `--format text` shows observed GitHub controls and next actions | JSON by default; `UNKNOWN` stays explicit |
| `tools.contract_coach` | Short UNREVIEWED contract comparison; `--detail full` expands it | `--format json` |
| `tools.parts --project <id>` | Text and HTML checklist; `--picker` offers reviewed parts, `--selection` previews, `--apply` writes the locked edits | `--format json` |
| `tools.visualize --project <id>` | 3D model audit and export paths; `--init-model-map` drafts explicit assignments, `--map-models` previews source edits and `--apply` writes reviewed edits | `--format json` |
| Other `tools.template` commands; `tools.ci`, `tools.hardware`, `tools.sourcing`, `tools.metrics` | `--format text` | JSON by default |
| `tools.release prepare` | Text by default | `--format json` or `--json` |
| Other `tools.release` commands | `--format text` | JSON by default |

The lower-level runner modules in the table below remain JSON-first adapters.
Do not scrape human text in automation; check the exit status and parse stdout JSON.
Agents with shell access can call these CLIs directly. The optional local
[MCP server](../docs/workflow/MCP.md) exposes discovery, import triage, bounded
source/evidence reads and repair previews. Startup flags separately enable project
creation/import, reviewed source edits, checks and exports. The same services carry
an imported board through diagnosis, native exports and an engineering review
package; reviewed source commits still use normal Git.

| Module | Responsibility |
| --- | --- |
| `surface`, `hwrepo/surface.py` | Compare CLI/MCP workflow coverage and fail on undocumented interface drift; see [tool surfaces](../docs/workflow/TOOL_SURFACES.md) |
| `mcp` | Optional local stdio workflow adapter: fixed checkout, diagnosis, reviewed edits, checks, exports and engineering review packaging with separate startup capabilities |
| `electrical`, `hwrepo/electrical.py`, `hwrepo/electrical_runner.py`, `hwrepo/spice.py` | Check reviewed ground-pin coverage, power budgets and source-bound ngspice power/frequency cases; see [electrical analysis](../docs/workflow/ELECTRICAL_ANALYSIS.md) |
| `hwrepo/electrical_setup.py`, `hwrepo/electrical_doctor.py` | Initialize pending requirements without overwriting them, capture review hashes and preflight exact simulator readiness |
| `verify` | One-board portable/native/electrical run, exact runner choice, and a fresh logged repair receipt |
| `parts`, `hwrepo/part_picker.py`, `hwrepo/parts_workflow.py`, `hwrepo/purchasing.py` | Source-bound part selection and reviewed source updates, purchasing preferences, board/spare quantities and conditional DigiKey upload files |
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
| `hwrepo/mcp_server.py`, `hwrepo/mcp_files.py`, `hwrepo/mcp_workflow.py` | Register fixed MCP capabilities, bound source/artifact access and explicit edits, and adapt the diagnosis/export/review services |
| `hwrepo/models.py`, `hwrepo/contracts.py` | Own typed serialized contracts and file/path adapters |
| `hwrepo/discovery.py`, `hwrepo/project_tests.py`, `hwrepo/scaffold.py`, `hwrepo/importing.py`, `hwrepo/foreign_pcb.py` | Resolve local manifests, run isolated island test suites, create/import islands and stage foreign boards for review |
| `hwrepo/digikey_handoff.py` | Explicit, account-free myLists BOM handoff with a validated review link and no automatic POST retries |
| `hwrepo/doctor.py`, `hwrepo/adoption.py` | Check local prerequisites and run one-command fresh-fork adoption |
| Other `hwrepo/` modules | Implement named policy and generation services behind the CLIs |

Add substantial rules to the appropriate service and behavioral coverage to
[tests](../tests/README.md). New projects and variants are records, not new scripts.
Outputs belong in ignored locations. Native-source changes use an explicit,
hash-bound preview/apply workflow; generated review files are never edited back
into the design.
