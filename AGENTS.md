# Working in this KiCad repository

Track the [quality gates](docs/workflow/QUALITY_GATES.md) for each board. Report missing,
not-run and review-needed stages explicitly; a portable PASS does not establish electrical,
purchasing or release readiness. Read MCP domain statuses even when the protocol call succeeds.

This file is for coding agents and engineers using an agent. Start with the
[workflow guide](docs/workflow/START_HERE.md) and the
[diagnostic guide](docs/workflow/DIAGNOSTICS.md). Use Python 3.11 syntax.
This checkout owns engineering source, requirements, catalogs and project-local tests.
The CLI and MCP implementation comes from the public
[KiCad Tooling repository](https://github.com/sheepfling/KiCad-Tooling), pinned in
`requirements-tooling.txt`. Follow the [setup](README.md#first-run-setup); do not recreate a
`tools/` package here. Shared tooling changes belong in that separate repository.
See [tooling ownership and upgrades](docs/workflow/TOOLING_SPLIT.md).
Shared GitHub jobs also belong in Tooling. Keep only pinned reusable-workflow callers,
triggers and project selection controls here; review workflow and Python pins together.
For Python automation, use the installed `kicad_tooling` modules through
`python -I -m kicad_tooling.<module>`. Project paths select data, never imports.
Do not patch `PYTHONPATH` or `sys.path` to locate a sibling tooling checkout;
install it normally or editably in the active environment.

## Coach the engineer through a first project

Establish the board ID, intended function, electrical owner and mechanical reviewer.
Record supplied requirements, interfaces, limits and unresolved decisions in the island's
`docs/`. Ask the responsible engineer for missing nets, part identities, voltage/current
limits, connector pinouts, tolerances or approvals. Never derive an expected contract solely
from the design's observed output or invent a requirement to make a check pass.

For a new board, follow [First board](docs/workflow/FIRST_BOARD.md); for existing source, follow
[Import workflow](docs/workflow/IMPORT_WORKFLOW.md). Explain the first blocking group in plain
language and point to its source. Electrical review establishes connectivity, component selection
and operating limits. Mechanical review establishes units, origin, mounting, enclosure clearance and
tolerance assumptions. Use the [mechanical handoff](docs/workflow/MECHANICAL_HANDOFF.md) and
[3D workflow](docs/workflow/THREE_D_WORKFLOW.md) together; a rendered model or passing export does
not prove physical fit. Keep pending decisions explicit until the responsible person reviews them.

## Use the installed MCP loop

Start `kicad-team-mcp --root /absolute/path/to/checkout` through the agent client's
[local MCP configuration](docs/workflow/MCP.md). The server binds one checkout at startup.
Use the CLI when shell integration is appropriate; both surfaces call the same installed services.

1. Call `list_projects`, `get_project` and `doctor` to establish identity, requirements and
   prerequisites. Read `start-here`, `first-board` and `diagnostics` with `read_document`.
2. For imports, call `scan_imports`, `preview_import` and `diagnose_import` before
   `import_project`. Creating an island requires `--allow-writes`; it is an incomplete scaffold.
3. Use `diagnose_project` and `read_artifact` to inspect retained findings. Read authored source
   with `read_project_file`. Preview a specific edit with `preview_project_edit` using the returned
   SHA-256; apply the reviewed change with `apply_project_edit` and `--allow-edits`.
4. Call `check_project` after a repair, with `depth: "native"` after KiCad source changes.
   Use `check_scope` for product/tag selections or a full project gate. Checks execute trusted
   project tests and require `--allow-checks`. `capture_contract` inventories **UNREVIEWED**
   observations for comparison with independently supplied requirements.
5. For mechanical review, call `inspect_3d_models`, then `init_model_map` or
   `preview_model_population` and a reviewed `apply_model_population` when needed.
   `export_3d` requires checks and exports; preserve `models.status: REVIEW` until reviewed.
   Parts work uses `prepare_parts`; purchasing or model output is review evidence, not approval.
6. Commit reviewed source through normal Git before `export_project` or `prepare_review`.
   Those operations require both `--allow-checks` and `--allow-exports`; packaging does not
   approve a design or place an order. Downloads and supplier submissions have separate flags.

Report status, selected scope, source commit/hashes, receipt path and remaining engineering
questions. An MCP response can contain a failed check; inspect its report rather than treating
transport success as validation. With unavailable capabilities, show the required startup flag
and use the authorized workflow without weakening policy.

## Find the right source

- Confirm the branch, checkout status and project ID before editing. Each
  `projects/<id>/` island owns its KiCad source, requirements, docs and tests.
  Run `kicad-team template list --format json` to discover registered
  project, product, tag and toolchain IDs. Its input-presence state is not a
  validation result; run `kicad-team verify --project <id>` for the
  selected board.
  Shared project policy lives under `catalog/`; board expectations and optional executable
  tests remain in each island. See [project tests](docs/workflow/PROJECT_TESTS.md) and the
  [scripting standard](docs/workflow/SCRIPTING_STANDARD.md).
- For an existing design, preview the import before copying it. Use the command below:

  ```sh
  kicad-team template diagnose \
    --source <path-to-.kicad_pro> --project-id <id> --toolchain <id>
  ```

  Read the import inventory and repair missing sheets or nonportable paths in the original source.
  Then follow the [import workflow](docs/workflow/IMPORT_WORKFLOW.md). For a directory with several
  candidates, first run
  `kicad-team template scan-imports --source-dir <directory> --toolchain <id> --format json`.
  Review suggested IDs and every exclusion; the command is read-only and does not establish design
  completeness or electrical correctness.
- For a non-KiCad PCB file, run `kicad-team template convert-pcb
  --source <file> --project-id <id> --toolchain <id> --format json`. Review the
  ignored receipt's `kicad-import-report.json`, converted board geometry and
  native import preview with the exact KiCad toolchain. Only then run its
  `next_command` to create a `pcb_only` island; this does not convert a schematic.
- For a registered board, run
  `kicad-team template diagnose --project-id <id>` before changing
  policy or tests. The default output groups repeated causes; `--detail full`
  prints every finding. Agents and scripts should parse `--format json` stdout,
  not the human text: the versioned report includes `status`, `findings`,
  `next_command` and `run_directory`. Each run also writes a fresh ignored
  `build/diagnostics/` receipt.
- If an unrelated malformed manifest blocks normal selected discovery, run
  `kicad-team template rescue --project-id <id>` for a read-only local
  repair view. It always reports `UNVERIFIED_GLOBAL` and exits nonzero, even if
  the selected island looks clear. Never cite it as CI or release evidence;
  repair global discovery and rerun normal diagnosis and the full gate.
- For a new schematic-backed board with an empty component/net contract, run
  `kicad-team contract-coach --project-id <id> --capture --format json`
  with the exact local KiCad CLI or the digest-pinned Docker image (`--runner auto`
  selects one). For an existing native report, use
  `--native-summary <project-summary.json>` instead. This read-only coach checks
  project identity, source hashes and netlist artifact evidence; its components
  and nets are explicitly `UNREVIEWED`. It never edits `tests/contract.json` or
  establishes electrical coverage. Keep optional receipts under ignored `build/`.
- For a PCB's 3D handoff, run
  `kicad-team visualize --project <id> --check-models --format json`
  to inspect placed-footprint model coverage and candidate repository assets.
  For unassigned footprints, use `--init-model-map build/model-map.json` to
  create a hash-bound draft, enter explicit reviewed source-model paths, then
  use `--map-models build/model-map.json` to inspect the board/manifest diff
  before `--apply`. Repair existing assignments in KiCad. Then run
  `kicad-team visualize --project <id>` to produce top/angled
  PNGs, STEP and GLB in a fresh ignored receipt. A successful export can still
  have `models.status=REVIEW`; inspect the actual geometry and follow the
  [3D workflow](docs/workflow/THREE_D_WORKFLOW.md). The manual **KiCad 3D preview**
  Action provides a focused hosted run without slowing routine PR lanes.
  For a named KiCad component population, pass `--assembly-variant <name>`;
  the name must already be declared in the project's `.kicad_pro`.
- For an exact sourced part's STEP model, run
  `kicad-team parts --project <id> --check-step <LCSC_ID>` or use **Check
  STEP alignment** after **Find CAD** in the parts assistant. Review the paired
  native WRL/STEP views and disposable STEP assembly in the ignored receipt.
  `REVIEW` means visual inspection is required; the command does not install
  STEP or prove manufacturer dimensions or physical fit. Follow the
  [CAD sourcing workflow](docs/workflow/CAD_SOURCING.md).
- For component selection, run `kicad-team parts --project <id> --picker`.
  Choose only reviewed catalog CAD bindings; `--selection <download>` previews
  diffs and writes a locked selection for `--selection <locked> --apply`.
  Missing/different PCB footprints require KiCad F8 and then `--sync-models`;
  repair existing different model assignments in KiCad. The plain `--project`
  command reads source to create a purchasing checklist and conditional DigiKey
  CSV. Never invent part identities, equivalents or catalog approvals. Keep
  receipts under ignored `build/`, recheck native source after applying, and follow
  [parts to order](docs/workflow/PARTS_TO_ORDER.md). Purchasing metadata readiness
  does not establish live stock, price, electrical or physical approval.
- For grounding, power and high-frequency requirements, follow the
  [electrical analysis workflow](docs/workflow/ELECTRICAL_ANALYSIS.md). Author independent
  limits and model bindings, then use `kicad-team verify --project <id> --depth electrical`.
  Do not refresh model/source hashes without reviewing the circuit-to-model mapping.

## Diagnose, repair, verify

1. Read the first blocking group and its source location. If the cause is
   unclear, inspect `events.log` and the raw `import-preview.json` or
   `portable.json` in the receipt. For a coach crash, inspect `error.txt` and
   `run.json`; for a native failure, inspect the native `*.command.json` and
   ERC/DRC outputs.
2. Repair the authoritative source: KiCad files, declared assets, catalog
   records, or independently reviewed test expectations. Do not edit an export
   or copy observed output into the contract just to pass a check. Do not
   invent nets, part identities or ERC/DRC waivers. Surface missing electrical
   requirements to the responsible engineer. For CAD paths, follow the
   [shared-library policy](docs/workflow/LIBRARIES.md); never borrow an
   undeclared asset from another project's private directory.
3. After each source fix, run `kicad-team verify --project <id>`.
   Add `--depth native` after KiCad source changes. It chooses an exact local
   CLI or the project's pinned Docker image and saves a new ignored receipt;
   `--format json` is the agent interface and `--detail full` expands human
   findings. Run `kicad-team template doctor --native --project-id <id>` if the
   runner cannot start. For a product, use `kicad-team ci --product <id>`; for a
   named cohort, use `kicad-team ci --tag <tag>`. Multiple include selectors form a union, and
   `--exclude-tag <tag>` removes projects afterward. Run the full
   `kicad-team ci` gate after changing shared tools, catalogs or policy,
   and for a deliberate repository-wide rehearsal. After native KiCad inputs
   change, recheck affected BOMs and exports from the new receipt. Run
   `kicad-team impact --base <ref> --head <ref> --format json`
   to inspect planned PR scope in a script or agent.
   For a manual hosted lane, run **KiCad template acceptance** in Actions with
   `focus=project` and `value=<id>` (or select `product`, `tag`, or `branch` with
   a base ref such as `origin/main`). The default `focus=full` rehearses every
   lane. Optional `shard=INDEX/COUNT` selects a partial project shard, never
   complete release evidence. Preview it with `kicad-team impact --select-tag <tag>`
   `--shard INDEX/COUNT`; run its portable tests with the same selectors on
   `kicad-team ci` or MCP `check_scope`. Stage logs live under ignored `build/ci-hosted/`.
4. Report the project ID, branch and commit, changed source, commands and
   results, receipt path, and any unresolved engineering decision. Keep run
   evidence in ignored `build/`, CI artifacts, or the issue/PR. Keep durable
   board decisions in `projects/<id>/docs/`.

For release exports, `release_exports.assembly_variant` selects a board's
standalone KiCad population, and a product variant's `board_variants` map may
override it. The release gate checks that the native fitted BOM references and
`PART_ID`s match the selected product population. Review the generated
schematic/PCB PDFs, JSON board statistics and any requested supplier formats in
the ignored export receipt before approving manufacturing files.

Never commit imported practice projects, local KiCad state or generated working
outputs. Follow the [source and output policy](docs/workflow/REPOSITORY_HYGIENE.md)
and [BOM policy](docs/workflow/BOM_POLICY.md). A passing check verifies its
declared scope; it does not approve an electrical design or manufacturing release.
For an adopted GitHub repository, run the optional read-only
`kicad-team governance-audit --format json` to inspect hosted branch
controls. Preserve `UNKNOWN` for inaccessible APIs and unverified real-team
permissions; follow the [GitHub governance guide](docs/workflow/GITHUB_GOVERNANCE.md)
for the human review and access rehearsals.
By default, discovery is one level below each configured root, such as `projects/<id>/`.
Use tags or registered products to group independent islands. Intentional nested layouts require
the installed tooling’s declared `project_depth` and configuration adapter; follow the
[layout guidance](docs/workflow/TOOLING_SPLIT.md#configuration-and-package-versions) instead
of assuming an arbitrary nested folder will be discovered.

When changing a CLI command, option or MCP tool, work in the tooling repository and update its
packaged `kicad_tooling/tool-surfaces.json` plus the shared implementation and behavioral tests.
Run `kicad-team surface --require-live-mcp` against this project for installed-interface inspection.
Read [tool surfaces](docs/workflow/TOOL_SURFACES.md) for required core parity and explicit
administrative/adapter exceptions. Surface inspection never runs those tests; tooling CI does.
The template's `kicad-team ci` checks project policy, docs, generation and project/product suites.
Neither gate grants design approval.

## Electrical evidence during handoff

Normal hosted native CI runs every declared electrical contract. Release preparation must retain
passing electrical evidence for those contracts; check/package/verify/restore revalidate source,
models, requirements, logs and waveforms. Build releases require explicit electrical applicability
for schematic-backed boards. Do not remove a contract or mark sections not applicable merely to
pass. For engineering review without a contract, preserve NOT_CONFIGURED in the handoff. Physical
review and approved part selection remain human decisions; follow the quality-gate checklist.
