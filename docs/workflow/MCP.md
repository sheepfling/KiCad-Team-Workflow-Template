# Connect an agent through MCP

The optional local MCP server carries a board through discovery, import, diagnosis,
reviewed source repair, checks, exports and an engineering review package. It calls
the same repository services as the command-line tools and returns their typed
reports. Start with the result's status, findings and next actions; a completed MCP
call can contain a failing engineering or environment result.

## Install and connect

Use a trusted checkout and the [Python environment setup](../../README.md#first-run-setup).
From that checkout, install the optional dependency:

```sh
python -m pip install -e '.[mcp]'
```

Install `.[dev]` when enabling checks or developing the adapter; it includes the
pinned MCP SDK, chart renderer and repository quality tools. Install `.[charts]`
for electrical chart export in a smaller runtime. Exact-part community CAD lookup
needs `.[cad]` when a new bundle must be converted; saved intact bundles can be
reviewed without that optional converter. The base installation keeps MCP
optional. Clients with shell access can also use the CLIs directly.

Configure the client to launch the checkout's virtual-environment interpreter.
For a client accepting `mcpServers`, replace both absolute paths in this example:

```json
{
  "mcpServers": {
    "kicad-workflow": {
      "command": "/absolute/path/to/checkout/.venv/bin/python",
      "args": [
        "-B", "-m", "tools.mcp",
        "--root", "/absolute/path/to/checkout"
      ]
    }
  }
}
```

On Windows, use the absolute `.venv\Scripts\python.exe` path and escape each
backslash in JSON. The editable installation makes `tools.mcp` importable without
setting the client's working directory. Keep the interpreter and `--root` pointed
at the same checkout, especially when using several worktrees.

Native container work also needs `docker` on the server process's `PATH` and a
running Docker service. Desktop clients may inherit a different environment from
your terminal. Configure the client's launch environment to include the actual
Docker executable directory when necessary, then reconnect and rerun `doctor`.
On a standard macOS Docker Desktop installation, that directory may be
`/Applications/Docker.app/Contents/Resources/bin`; verify it on the host.
For a linked Git worktree, native verification and release/export runners also
mount its shared Git metadata read-only, preserving the selected worktree's commit
and index. Docker must be able to read both the worktree and that metadata directory.

The transport is local stdio. There is no HTTP listener or hosted account to set
up. Start a separate configuration for each checkout. The repository root, import
roots and enabled capabilities are fixed at startup; reconnect after changing them.

## Choose the enabled capabilities

Add the relevant flags to the startup `args` array. Each flag enables a distinct
operation; enabling project creation does not enable edits to an existing design.

| Startup capability | Tools enabled | Files or execution affected |
| --- | --- | --- |
| Default | Discovery, tool-surface inventory, impact planning, sourcing inspection, guidance, source/artifact reads, import scanning and preview, edit preview, saved contract inspection, model-population preview, rescue and import diagnosis, release/package verification | Reads bounded repository data. Model-population preview, rescue and import diagnosis create ignored diagnostic receipts. Package verification temporarily restores the archive. |
| `--allow-writes` | `new_project`, `import_project` | Creates a new project island; refuses an existing destination. |
| `--allow-edits` | `apply_project_edit`, `apply_model_population`, `save_parts_preferences`, `init_electrical`, `apply_part_selection`, `apply_auto_cad`, `apply_cad_import` | Creates pending electrical requirements or applies reviewed source/preferences changes with stale-write protection. |
| `--allow-checks` | `check_project`, `diagnose_project`, `capture_contract`, `check_scope`, `check_native_scope`, `analyze_electrical`, `check_electrical_scope` | Executes repository checks and creates ignored receipts. Native work also runs KiCad or Docker. |
| `--allow-exports` | `generate_views`, `init_model_map`, `prepare_parts`, `package_release`, `restore_package`, `capture_electrical_inputs`, `prepare_part_picker`, `preview_part_selection`, `preview_model_sync`, `preview_auto_cad`, `source_cad`, `preview_cad_import`, `prepare_supplier_handoff`, `export_electrical_charts`, `export_electrical_chart_suite` | Creates generated review views, model-map drafts, purchasing receipts from saved evidence and new package/restore outputs in the checkout's ignored build area. Fresh parts capture also requires checks. |
| Both `--allow-checks` and `--allow-exports` | `export_project`, `export_3d`, `prepare_review`, `prepare_review_scope`, `convert_pcb`, `check_step_alignment` | Executes checks/native tooling and creates fresh exports, 3D views or an engineering review candidate. |
| `--allow-downloads` | Allows official CAD fetches in `preview_auto_cad` / `apply_auto_cad` and exact-part community-provider fetches in `source_cad` / `check_step_alignment` | Without this additional flag, intact cached assets may be reused, but missing downloads remain unresolved. A tool argument cannot enable network access. |
| `--allow-supplier-submissions` | `submit_supplier_handoff` | Sends one reviewed BOM to DigiKey for matching and returns a review link; never places an order. |

Checks execute trusted repository code, including project and product tests.
Native work may download the pinned container image and Python dependencies.
The server provides fixed operations and output locations; a tool call cannot
choose another checkout or an arbitrary shell command or executable.

The server does not commit Git changes, sign approvals, create source tags, publish
packages or authorize manufacture. Use normal Git for reviewed source commits and
the team's release process for approvals and retained storage.

## Discover the board and its guidance

1. List the client's discovered tools to confirm that the expected capability
   flags took effect.
2. Call `list_projects` to find actual project, product, tag and toolchain IDs.
   Inspect status and assurance profile. `training_fixture` examples are
   rehearsals; an initialized fork may have no live projects yet.
3. Call `get_project` with a discovered `project_id` to inspect its manifest and
   independent test contract. Call `doctor` for local prerequisites, then request
   native readiness for the selected board before native work.
4. Read `first-board`, `diagnostics` or `import-workflow` through `read_document`.

Use `inspect_tool_surfaces` to compare the shared CLI and MCP operation catalog;
`python -B -m tools.surface` exposes the same inventory from a terminal. The catalog
requires core workflow parity and behavioral test references, tracks administrative
exceptions separately, and catches declaration drift. Inspection reports
`behavior_verification: NOT_RUN`; the full CI gate runs the comparisons. Read
`tool-surfaces` for the policy and its limits.

Discovery's `INPUTS_PRESENT` state describes file presence. It does not establish
that a board passes checks. Doctor describes prerequisites, and an import preview
describes eligible source files; neither establishes electrical correctness.

| Tool | Arguments and use |
| --- | --- |
| `list_projects` | No arguments. List project, product, tag and toolchain inventory. |
| `inspect_tool_surfaces` | No arguments. Inspect the CLI/MCP operation catalog, capability gates and recorded reasons for CLI-only operations. |
| `get_project` | `project_id`. Return the selected inventory row, manifest and test contract. |
| `doctor` | Optional `project_id`, `toolchain_id` and `runner`; `native` and `electrical` default to `false`. Electrical readiness checks native setup and the fixed host ngspice against the selected contract. |
| `read_document` | `name`. Read a named workflow guide. |
| `new_project` | `project_id`, `kind`, `toolchain_id`. Create an incomplete development scaffold with `--allow-writes`. |

Project kinds are `pcb`, `pcb_only`, `schematic`, `system_wiring` and
`harness_interface`; see [project kinds](PROJECT_KINDS.md). A scaffold needs actual
CAD source and independently reviewed expectations before its checks can pass.

Workflow documents are also resources at `kicad://docs/{name}`, for example
`kicad://docs/first-board`. Available names are `start-here`, `first-board`,
`diagnostics`, `import-workflow`, `contributor-guide`, `checks-and-ci`, `mcp`,
`bom-policy`, `release-readiness`, `release-storage`, `project-kinds`, `libraries`,
`authority-model`, `assurance-profiles`, `three-d-workflow`, `parts-to-order`,
`tool-surfaces`, `electrical-analysis` and `cad-sourcing`.

## Scan, preview and import existing designs

| Tool | Arguments and use |
| --- | --- |
| `scan_imports` | `source_directory`, `toolchain_id`. Inventory a directory of candidate designs without copying them. |
| `preview_import` | `source`, `project_id`, `toolchain_id`. Preview one saved `.kicad_pro` file, its hashes and exclusions. |
| `diagnose_import` | `source`, `project_id`, `toolchain_id`. Turn the import preview into a repair queue and keep an ignored diagnostic receipt. |
| `import_project` | `source`, `project_id`, `toolchain_id`. Copy the reviewed source into a new project with `--allow-writes`. |

Import paths start at the configured checkout. Absolute import paths can also name
an explicitly enabled external source directory; add its parent at startup:

```text
--import-root /absolute/path/to/legacy-designs
```

Repeat the flag for additional directories. These roots permit import reads; copied
output still belongs under the configured checkout's `projects/` directory. Use a
design folder as the root rather than the whole home directory. Linked paths and
parent traversal are rejected. The importer inventories eligible siblings in the
selected source file's directory as well as the `.kicad_pro` itself.

Review every suggested project ID, exclusion and source hash. Repair missing
sheets and nonportable paths in the original design, then rerun the preview.
Import one accepted design at a time and inspect the new island's `docs/import.json`.
An import preserves source; it does not invent electrical requirements or approve
the copied design. See the [import workflow](IMPORT_WORKFLOW.md).

## Inspect evidence and repair source

Use `list_artifacts` to find retained outputs and `read_artifact` to read their
metadata or bounded text.

| Tool | Arguments and use |
| --- | --- |
| `list_artifacts` | `directory` defaults to `build`; `offset` to `0`, `limit` to `100`. List one directory page. |
| `read_artifact` | `path`; `offset` defaults to `0`, `limit` to `20000`. Read an artifact chunk or metadata. |
| `read_project_file` | `project_id`, `path`; the same text `offset` and `limit` defaults. Read allowed authored source. |
| `preview_project_edit` | `project_id`, `path`, `expected_sha256`, `old_text`, `new_text`. Preview one exact replacement. |
| `apply_project_edit` | The same arguments as the reviewed preview. Apply with `--allow-edits`. |

Artifact paths are relative to the checkout and limited
to managed `build/` areas, including a selected island's `build/`. Restored checkouts
under `build/restores/` are excluded from artifact browsing. Listings cover one
directory level; use pagination and select a returned subdirectory to explore it.

Use `read_project_file` for the selected board's authored source. Its `path`, and
the edit tools' `path`, are relative to the project island: for example,
`kicad/board.kicad_sch`, `project.json` or `tests/contract.json`. Source reads include
supported KiCad text files, library tables, the manifest, contract, island README
and Markdown under `docs/`. Electrical source access includes the typed sidecar and project-owned `.cir` model text; shared models remain outside project editing authority. They do not read arbitrary desktop files.

Reads return a SHA-256 digest and at most 20,000 characters of supported UTF-8
content per request. Binary or unsupported artifact types return metadata. Use
`offset` and `limit` to page through text and check whether more remains before
treating it as complete. The returned path is checkout-relative, so preserve the
original island-relative path when making a subsequent source edit.

`preview_project_edit` takes `project_id`, `path`, `expected_sha256`, `old_text` and
`new_text`. Supply the digest from the source read and an exact, uniquely occurring
piece of the current text. The preview produces a diff without writing. Review the
diff, then use `apply_project_edit` with the same arguments when `--allow-edits` is
enabled. An outdated digest or a non-unique match fails; reread and preview again.

Close KiCad before editing. The server serializes its own operations and uses an
atomic replacement, but it cannot lock out a separate editor changing the file
between reads and writes. Read the result back and rerun the relevant checks.
Edits are limited to allowed project text sources; generated artifacts, release
records and executable files are excluded. Use the normal editing/review workflow
for changes outside that scope. An accepted replacement is a source edit, not proof
that the resulting circuit or CAD syntax is correct.

Keep engineering authority explicit: repair the authored CAD path, declaration or
independently established requirement. Do not copy observed output into
`tests/contract.json` solely to make a check pass, invent part identities or waive
ERC/DRC findings. Follow [libraries](LIBRARIES.md) for CAD dependency repairs and
[BOM policy](BOM_POLICY.md) for BOM authority.

## Plan the affected checks

`plan_impact` matches the CLI's impact modes without running project tests or native
tools. Supply exactly one mode:

- `base` with optional `head` (default `HEAD`) for a Git commit comparison.
- `paths` for a list of changed repository-relative names, including deleted files.
- `full: true` for full scope.
- One of `select_project`, `select_tag` or `select_product` for a manual selection.
  Optional `exclude_tag` removes matches from that manual selection.

Git references resolve to commits before comparison. Unknown ownership and unsafe
changed paths conservatively select full scope, matching `python -B -m tools.impact`.
The result records selected projects, changed paths, documentation impact and the
reasons for its scope. Use it to choose a subsequent check; a plan contains no
validation or release evidence.

## Diagnose and check

| Tool | Arguments and use |
| --- | --- |
| `rescue_project` | `project_id`. Inspect one island when malformed peer metadata blocks normal discovery; keep an ignored receipt. Always `UNVERIFIED_GLOBAL`, with no CI or release eligibility. |
| `diagnose_project` | `project_id`; optional `native_report` and `bom`. Run selected portable checks and combine current source/native/BOM findings. Requires `--allow-checks`. |
| `check_project` | `project_id`; `depth` defaults to `portable`, `runner` to `auto`. Run selected portable, native or electrical verification and retain the receipt. Requires `--allow-checks`. |
| `check_scope` | Optional `project_ids`, `product_ids`, `tags`, `exclude_tags` lists. Run the selected portable gate, or the full gate without selectors. Requires `--allow-checks`. |
| `check_native_scope` | `view_id`; optional `project_ids`, `product_ids`, `tags`, `exclude_tags` lists. Run the grouped native CLI lane with the fixed local `kicad-cli` and retain a fresh receipt. Requires `--allow-checks`. |
| `inspect_contract` | `project_id`, `native_summary`. Inspect saved source-bound native evidence without capturing again. Observations remain `UNREVIEWED`. |
| `capture_contract` | `project_id`; optional `runner`. Capture native evidence to help independently author the contract. Requires `--allow-checks`. |

Native `runner` choices are `auto`, `local` and `container`. `auto` selects an exact
local KiCad CLI when available, otherwise the project's pinned image. A local or
container runner requires native or electrical depth for `check_project` and `native: true` or `electrical: true` for
`doctor`. Doctor can inspect a toolchain before a project exists; a supplied project
and toolchain must agree. Scope include selectors form a union, then `exclude_tags`
removes matches; with only exclusions, selection starts from all projects.
The grouped `check_native_scope` operation matches `tools.ci --kicad`; use
`check_project` for per-project automatic or container runner selection.
Native failures retain runner and command evidence. Portable checks do not establish native acceptance.

Read `events.log`, the full diagnostic report and captured portable/native outputs
from the returned `run_directory`. When that directory is absolute, remove the
configured `--root` prefix for an artifact tool's checkout-relative path.
`rescue_project` is a repair aid while global discovery is broken; fix the manifest and rerun normal checks before relying on a
pass. Shared tooling or policy changes require the full gate. See
[diagnostics](DIAGNOSTICS.md) and [checks and CI](CHECKS_AND_CI.md).

For BOM diagnosis, supply the native assembly BOM and its corresponding project
native report from the same source revision. The binder checks source identity,
native artifact evidence and assembly population. A free-standing CSV or an old
report cannot establish the current board's BOM validity. Inspect the purchasing
BOM separately for the controlled manufacturer, MPN and revision join.

## Inspect and export board 3D models

| Tool | Arguments and use |
| --- | --- |
| `inspect_3d_models` | `project_id`. Read placed-footprint model assignments, missing or broken references and declared candidate assets. Available by default; creates no files and runs no native tools. |
| `init_model_map` | `project_id`, `view_id`. Create a source-bound draft for unassigned footprints under `build/model-maps/<view_id>` with `--allow-exports`. |
| `preview_model_population` | `project_id`, `board_sha256`, `assignments`. Retain a plan for explicit reference/model pairs without editing source. Available by default. |
| `apply_model_population` | `project_id`, `plan`. Apply a reviewed `model-population.json` plan and its saved model map with `--allow-edits`. |
| `export_3d` | `project_id`, `view_id`; optional `runner` defaults to `auto`, and `assembly_variant` selects a declared KiCad population. Generate top/angled PNG, STEP and GLB files using exact local KiCad or the pinned container. Requires both checks and exports capabilities. |

Select a `pcb` or `pcb_only` project. Begin with `inspect_3d_models`, review its
findings, and follow [the 3D workflow](THREE_D_WORKFLOW.md) to populate the board's
3D model assignments. A matching candidate filename does not prove package identity
or dimensions. Author and review the physical model separately; these tools do not
create geometry or select a package for you.

For a starting inventory, call `init_model_map` with a new `view_id`. Its
`model-map.json` lists every unassigned footprint, blank model choices, candidate
asset hints and the board/manifest hashes. The same directory retains the
`model-population.json` report and diagnostic logs. `DRAFT` is an unapproved starting
point: it changes no source, selects no physical model and does not run KiCad.
Read the draft through `read_artifact`, review the candidates independently and
pass the desired explicit assignments to `preview_model_population`.

For an explicit assignment, read the board with `read_project_file` and pass its
SHA-256 to `preview_model_population` with assignments such as
`[{"reference": "J1", "model": "projects/my-board/kicad/models/header.step"}]`.
Each model is an existing checkout-relative STEP, STP, IGS, IGES or WRL file under a
declared project-local or shared source root. The service rejects footprints that
already have a model. It inserts only the requested model references and adds their
source paths to the manifest's required/shared inventory. New assignments use unit
scale with zero offset and rotation; package fit and transforms need visual review.

The preview creates a fresh `build/diagnostics/` receipt with `model-map.json`,
`locked-model-map.json`, `model-population.json`, `board.diff` and `manifest.diff`. Review both diffs. Close
KiCad, then call `apply_model_population` with the checkout-relative
`model-population.json` path. Apply rereads the digest-locked map and rejects changed board,
manifest or model hashes, a changed map, or differing planned edits. It retains a
new receipt and verifies the source readback. A `PLAN` or `APPLIED` result still has
`checks_required: true` and `build_authorized: false`. Inspect the authored board,
rerun portable/native checks and review scale, rotation, offset and board side in
KiCad. Existing assignments and transform adjustments remain manual source edits.

Named `assembly_variant` values for 3D and fabrication exports must already exist
in the selected KiCad project. Product release variants use reviewed board-to-KiCad
population mappings. Supplier formats come from authored export settings; export
receipts preserve the selected population and all required artifact hashes.

Call `export_3d` with a fresh `view_id` after saving the source. Its controlled
receipt is `build/3d/<view_id>` and contains `visualization.json`, `models.json`,
command logs, `top.png`, `angled.png`, `board.step` and `board.glb` when all exports
succeed. Existing destinations are refused, and a source change during the run
invalidates the result. Use `list_artifacts` and `read_artifact` to inspect retained
reports; binary and unsupported artifact types return metadata. Open the files in
an image viewer or mechanical CAD application to inspect their actual geometry.

Keep the report's two outcomes distinct: export `status: PASS` means the expected
files were produced from the recorded source, while `models.status: REVIEW` means
model coverage still needs review. Static model `READY` verifies references and
coverage, not fit or geometry. Missing stock libraries, hidden models and absent
bodies can leave an incomplete assembly view even after a successful export.
Inspection and export preserve authored source. Only the explicitly enabled
`apply_model_population` step attaches the reviewed model references.

## Convert an existing foreign board

`convert_pcb(source, project_id, toolchain_id, input_format="auto", runner="auto")`
uses the same guarded conversion service as `tools.template convert-pcb`. It needs
checks and exports capabilities. `source` must be within the checkout or a startup
`--import-root`. Supported format selections are `auto`, `pads`, `altium`, `eagle`,
`cadstar`, `fabmaster`, `pcad` and `solidworks`.

The ignored receipt retains original and converted hashes, native import findings
and an ordinary import preview. A conversion can fail even when the native program
exits successfully; read its status and warnings. Review geometry before calling
`import_project` on the converted source. Conversion neither registers an island
nor claims schematic/electrical completeness. See [import workflow](IMPORT_WORKFLOW.md).

## Configure and run electrical analysis

| Tool | Arguments and use |
| --- | --- |
| `init_electrical` | `project_id`; optional `ngspice_version` defaults to `UNREVIEWED`. Creates pending requirements without replacing an existing contract. Requires edits. |
| `capture_electrical_inputs` | `project_id`, `view_id`; optional repository-relative `models` list. Captures unreviewed source/model hashes in ignored build output. Requires exports. |
| `analyze_electrical` | `project_id`, `view_id`; optional source-bound `native_summary` and `runner`. Runs declared grounding, power and frequency analysis with fixed KiCad/ngspice commands. Requires checks. |
| `check_electrical_scope` | Optional `project_ids`, `product_ids`, `tags`, `exclude_tags`. Uses the same union/exclusion selection as `tools.ci --electrical`. Requires checks. |
| `export_electrical_charts` | `view_id`, saved `receipt` directory or `electrical.json`. Exports PNG/SVG and full precision CSV from retained waveforms; requires exports and the pinned charts extra. |
| `export_electrical_chart_suite` | `view_id`, saved electrical `suite` JSON. Exports each project from the retained suite; requires exports and the pinned charts extra when waveforms exist. |

Start with the [electrical guide](ELECTRICAL_ANALYSIS.md). Review requirements and
model assumptions independently; captured hashes remain `UNREVIEWED`. Use
`read_project_file` and hash-checked edit previews for the typed electrical sidecar
and project-owned model files. Then call `doctor` with `electrical: true` and
`check_project` with `depth: "electrical"`, or run analysis using a saved native
summary. `NOT_CONFIGURED`, pending requirements and failed checks remain visible.
Simulation results do not prove real ground paths, physical startup, RF/EMC or
manufacturing acceptance.

The two chart tools run the same saved-receipt service as `tools.electrical_charts`.
They reread the analysis report and its recorded hashes, keep partial or failed
waveforms visible, and write a fresh `build/electrical-charts/<view_id>` receipt.
Use `read_artifact` for the CSV and report, then open PNG/SVG charts for visual
review. A chart does not rerun a simulation or create new electrical evidence.

## Review parts and paired CAD changes

| Tool | Arguments and use |
| --- | --- |
| `prepare_part_picker` | `project_id`, `view_id`; optional `native_summary` and `runner`. Writes eligible reviewed catalog choices; fresh capture also needs checks. |
| `preview_part_selection` | `project_id`, `view_id`, retained `picker_report`, and an `assignments` list of explicit `reference`/`part_id` pairs. Writes diffs and a locked map. |
| `apply_part_selection` | `project_id`, `view_id`, retained `selection_map`, `expected_sha256`. Applies the exact reviewed map and current source. Requires edits. |
| `preview_model_sync` | `project_id`, `view_id`. Replans model assignments after the engineer updates PCB footprints in KiCad. |
| `preview_auto_cad` | `project_id`, `view_id`. Plans paired CAD imports, preserving source hashes and geometry assumptions. Missing official assets need host downloads capability. |
| `apply_auto_cad` | `project_id`, `view_id`, retained `plan`, `expected_sha256`. Applies exact reviewed CAD changes; requires edits, plus downloads if fetching missing assets. |
| `source_cad` | `project_id`, `view_id`, exact LCSC `supplier_id`; optional `expected_mpn` and `refresh`. Freezes a provider bundle and previews project-local import. Requires exports; a new fetch additionally needs downloads. |
| `preview_cad_import` | `project_id`, `view_id`, saved `source_report` (`cad-source.json`). Rechecks the bundle and writes an import diff and plan; requires exports. |
| `apply_cad_import` | `project_id`, `view_id`, saved `plan` (`cad-import-plan.json`), `expected_sha256`. Applies exactly the reviewed plan bytes if the source and cached assets still match; requires edits. |
| `check_step_alignment` | `project_id`, `view_id`, exact `supplier_id`; optional `expected_mpn`, `refresh`, saved `source_report`. Renders paired WRL/STEP views with pinned KiCad; requires checks and exports, plus downloads for a new lookup. |

The exact-part path follows [CAD sourcing](CAD_SOURCING.md): enter a supplier ID,
check the reported manufacturer and MPN, inspect `cad-import.diff`, then apply the
returned plan with its artifact SHA-256. Source reports and plans stay under
`build/cad-sourcing/` or `build/cad-imports/`. `source_cad` and
`check_step_alignment` can reuse an intact cached part with downloads disabled;
`refresh` requests a new fetch and needs the download capability. STEP review
returns `REVIEW` until the paired views and actual package fit are inspected.

The preview tools require exports. Inspect retained diffs and read the locked
artifact's SHA-256 before applying. CAD filenames and paired geometry do not verify
part identity, dimensions or electrical interchangeability. Rerun native checks and
inspect the actual board after source edits. The CLI's browser assistant is a
presentation adapter; MCP exposes these bounded underlying operations without
starting a browser server that could bypass its capability flags.

## Prepare and explicitly submit a supplier review

`prepare_supplier_handoff(project_id, view_id, parts_report)` reads a current,
source-bound purchasing report and writes the exact DigiKey payload, input hashes
and handoff digest under ignored `build/supplier-handoffs/`. It requires exports and
does not contact the supplier. Read this artifact before deciding to submit it.

`submit_supplier_handoff(handoff, expected_sha256)` exists only when the host starts
with `--allow-supplier-submissions`. It sends reviewed part identifiers, quantities,
references and manufacturer notes to DigiKey for matching. The digest binds the
entire reviewed plan; source and evidence must still match. An attempt receipt is
created before the POST. Repeated calls do not resubmit, including an uncertain
response. `UNCERTAIN` means delivery could not be confirmed; inspect the supplier
before preparing a new submission. A returned review link is not an order.

The CLI has matching `tools.parts --prepare-handoff REPORT` and
`--submit-handoff PLAN --expected-sha256 SHA --allow-supplier-submissions` modes.
The existing offline BOM/CSV workflow remains usable without supplier submission.

## Prepare a parts list and remember purchasing preferences

| Tool | Arguments and use |
| --- | --- |
| `prepare_parts` | `project_id`, `view_id`; optional `native_summary`, `preferences`, `boards`, `spare_percent`, `spare_minimum` and `runner`. Prepare a local purchasing checklist and order-review CSVs with `--allow-exports`. Fresh native capture also requires `--allow-checks`. |
| `save_parts_preferences` | `project_id`, typed `preferences`; optional `expected_sha256`. Save the selected island's fixed `docs/purchasing.json` with `--allow-edits`. |

Start with [parts to order](PARTS_TO_ORDER.md). Supply an existing source-bound
`native_summary` from a native receipt to prepare without executing KiCad; keep
`runner` at its default `auto` in this mode. Without a summary, enable both checks
and exports so the tool can capture a fresh netlist using `auto`, `local` or
`container`. A tool call cannot select an executable or arbitrary output directory.

Use a fresh `view_id`. Outputs stay under `build/parts/<view_id>`: `index.html`,
`report.json`, `report.txt`, `bom.csv` and, only when metadata is complete,
`digikey.csv`. Read the JSON and CSV through artifact tools and open the HTML file
in a browser for the searchable checklist. Summary and alternate preference paths
are checkout-relative. Preferences may come from the selected island's `docs/`
JSON files or managed `build/` artifacts; another project's authored preferences and
linked paths are rejected. With no alternate, the service reads the selected project's
`docs/purchasing.json` if present. Quantity arguments override only that run.

For example, supply this typed `preferences` argument:

```json
{
  "schema_version": "1",
  "boards": 10,
  "spare_percent": 10,
  "spare_minimum": 3,
  "digikey_skus": {}
}
```

Omit `expected_sha256` only when creating a new preferences file. Before updating
an existing file, use `read_project_file` with `path: "docs/purchasing.json"`,
review the current preferences and supply its SHA-256. The result returns the
saved preferences and matching write/readback hashes. The text edit tools also
validate the purchasing schema. Reviewed DigiKey SKUs are explicit choices;
this workflow never selects substitutes, queries live availability or places orders.

`READY_FOR_ORDER_REVIEW` establishes purchasing metadata completeness. Its
`purchase_authorized` and `build_authorized` remain false, and an independent native
validation failure stays visible as `native_status: FAIL`. Repair `NEEDS_PARTS`
findings at the catalog, declared component IDs and KiCad fields; `BLOCKED` evidence
requires fresh capture or an input repair. Review supplier matches, packaging,
stock and price separately before uploading an order file. See the parts guide
for board-count/spare calculations and the DigiKey upload settings.

## Inspect a recorded sourcing snapshot

`inspect_sourcing_snapshot` accepts `path`, a checkout-relative artifact containing
manually captured sourcing-snapshot JSON under managed `build/`. It uses the same
typed file format and validation as `python -B -m tools.sourcing --snapshot ...`.
The default tool reads only that snapshot and the repository catalog; it does not
contact suppliers or create files.

The report preserves `PASS` or `FAIL`, offer counts and actionable findings for
unknown parts or duplicate offers. Missing or malformed saved JSON returns the
CLI's `SOURCING_LOAD` failure report. Out-of-scope and linked paths are rejected.
A pass describes recorded offer identities and catalog references; it does not
verify that stock or prices remain current, approve a component or authorize a
purchase or build. Use the [BOM policy](BOM_POLICY.md) to keep sourcing observations
separate from catalog identity and release evidence.

## Export and prepare an engineering review

Commit the reviewed source through normal Git and leave the checkout clean before
export or release preparation. Close KiCad. Add reviewed `release_exports` settings
to the project manifest before that commit; layer, origin and placement settings
are design-specific. Exact runner readiness and a complete source/contract remain
prerequisites. See [release readiness](RELEASE_READINESS.md).

| Tool | Arguments and use |
| --- | --- |
| `generate_views` | `view_id`; optional `project_ids`, `product_ids`, `tags`, `exclude_tags` lists. Generate product/variant BOMs, harness schedules and electrical/system review views with `--allow-exports`. |
| `export_project` | `project_id`, `export_id`; optional `runner` and declared `assembly_variant`. Create native and purchasing BOMs and applicable Gerber, drill and placement exports. Requires checks and exports capabilities. |
| `prepare_review` | `project_id`, `release_id`; optional `runner`. Prepare an `engineering_review` candidate for one board from clean committed source. Requires checks and exports capabilities. |
| `prepare_review_scope` | `release_id`, optional `project_ids` and `variants` lists, `portable` artifact path and `runner`. Prepare the shared CLI's multi-project/product-variant engineering review scope. Requires checks and exports capabilities. |
| `check_release` | `manifest`. Verify the candidate's source and retained evidence. |
| `package_release` | `manifest`, `package_id`. Verify and package the candidate, including its source Git bundle; requires `--allow-exports`. |
| `verify_package` | `archive`. Check inventory and hashes and perform a temporary restore without executing restored project scripts. |
| `restore_package` | `archive`, `restore_id`. Restore into a fresh managed directory and verify retained evidence; requires `--allow-exports`. |

`generate_views` projects existing authored product and variant records into review
outputs without running native KiCad. Its BOMs and harness/system views complement
the native assembly and purchasing BOMs; they do not replace source-bound native
validation. It writes `build/views/<view_id>` and returns its directory and files.

Use new IDs for new attempts; existing output destinations are not overwritten.
Managed destinations are `build/exports/<export_id>`, `build/releases/<release_id>`,
`build/packages/<package_id>.zip` and `build/restores/<restore_id>`. The export report
is `build/exports/<export_id>/files/exports.json`; the parent directory retains the
native runner's command evidence. Contract captures use `build/contract-coach/`; diagnostic runs use `build/diagnostics/`.
Manifest, archive, BOM and saved native-report inputs are checkout-relative paths.
Use returned paths for later artifact reads, diagnosis, manifest checks and
packaging. Some reports preserve the CLI's absolute path fields; remove the
configured `--root` prefix before supplying those paths to another MCP tool. For
example, `/checkout/build/diagnostics/run-001` becomes
`build/diagnostics/run-001` when `--root` is `/checkout`. Keep the rest of the path
unchanged. The review manifest is `build/releases/<release_id>/manifest.json`.
Review generated layers, holes, placement origin and rotation, component population
and BOM identity before relying on the outputs.

`prepare_review_scope` accepts explicit project IDs and exact `PRODUCT:VARIANT`
selectors. A selected scope must share one toolchain and use clean committed
source. Optional `portable` names retained portable evidence; `runner` is `auto`,
`local` or `container`. The service uses the same scope resolution as the release
CLI. `prepare_review` remains the single-board shortcut. Both operations produce
only an `engineering_review` candidate; neither accepts approval records or
prototype, pilot or production authorization.

A passing manifest/package check proves its declared evidence and integrity scope. It does
not create approvals, authorize a build or establish electrical correctness.
Packaging retains reachable source Git history; review that history before sharing
outside the team. Record the returned package digest when choosing
[durable release storage](RELEASE_STORAGE.md).

## Walk a board from import to review

Use discovered IDs and returned paths throughout this sequence. Enable checks, writes, edits and exports for this complete workflow,
and authorize only the needed external import directory.

1. Call `list_projects` and `scan_imports`. Pick one source, a new `project_id` and
   its approved toolchain. Call `preview_import` and `diagnose_import`; read the
   receipt and resolve missing sheets, paths and exclusions before `import_project`.
2. Call `get_project` for the imported board, then `doctor` with native readiness
   requested. Complete its independently reviewed design inputs and contract.
3. Call `diagnose_project` and read the first blocking finding. Use
   `list_artifacts` and `read_artifact` to inspect the receipt's exact error and
   `read_project_file` to inspect the authoritative source it names.
4. For an explicit source repair, copy the returned SHA-256 and select one exact
   text occurrence. Call `preview_project_edit`, review its diff and call
   `apply_project_edit` with the same digest and replacement. Read back the source.
5. Call `check_project`; use native depth after CAD changes. If the contract is
   incomplete, use `capture_contract` or `inspect_contract` as an UNREVIEWED
   inventory, then obtain independent expectations. Rerun checks after each repair.
6. Run the appropriate `check_scope`. For a product or harness, use `generate_views`
   with a fresh `view_id` and the intended selection to review its variant BOMs and
   wiring/system projections. Review the diff and commit authored source through
   normal Git. For PCB mechanical review, call `inspect_3d_models`, complete reviewed
   model assignments through preview/apply or KiCad, rerun checks after source changes,
   and use `export_3d` with a fresh `view_id`; inspect its actual
   geometry and model-coverage findings. Use `prepare_parts` for purchasing metadata
   review, retaining electrical and sourcing findings as separate decisions. Keep
   generated receipts and exports ignored; MCP does not create this source commit.
7. Call `export_project` with a fresh `export_id`. Read the retained native command
   results and inspect the actual exports. Call `diagnose_project` again with the
   exported native assembly BOM as `bom` and the still-current project summary from
   step 5's native check as `native_report`. Exporting does not create that validation
   summary. Rerun native checks first if source changed, then address source-bound
   BOM findings before proceeding.
8. Call `prepare_review` with a fresh `release_id`, then `check_release` with its
   manifest path. Inspect the candidate's actual frozen outputs and findings.
9. Call `package_release`, `verify_package` and, for a retained restoration,
   `restore_package`. Keep the package digest and verification evidence with the
   team's review/storage decision. Independent workstation and physical acceptance
   remain separate evidence.

## Troubleshoot the connection

- If launch fails, check the absolute interpreter path and install `.[mcp]` into
  that interpreter's environment. Run `python -B -m tools.mcp --help` there.
- If the board inventory is wrong, inspect `--root` and the checkout's branch, then
  reconnect. Do not infer live board IDs from example names in this guide.
- If an operation is absent, inspect the startup flags. Export and review preparation
  need both checks and exports enabled. Flags control discovery and availability.
- If an import source is outside the permitted roots, add its specific parent with
  `--import-root` and reconnect. Artifact/source readers remain checkout-scoped.
- If an edit rejects its digest or match, reread the source and prepare a new preview.
- If preparation rejects dirty or stale evidence, review and commit the actual source,
  then make a fresh run. Preserve failed receipts and follow their repair guidance.
