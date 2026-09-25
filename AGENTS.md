# Working in this KiCad repository

This file is for coding agents and engineers using an agent. Start with the
[workflow guide](docs/workflow/START_HERE.md) and the
[diagnostic guide](docs/workflow/DIAGNOSTICS.md). Use Python 3.11 syntax.
The optional [local MCP adapter](docs/workflow/MCP.md) exposes the same services
for clients without shell integration. Discover projects before selecting an ID.
Checks execute repository tests and require `--allow-checks`; separate startup
flags enable new islands, reviewed text edits and export/package outputs. Follow
the guide's import-to-review loop, preview explicit edits against the read SHA-256,
and commit reviewed source through normal Git before export preparation.

## Find the right source

- Confirm the branch, checkout status and project ID before editing. Each
  `projects/<id>/` island owns its KiCad source, requirements, docs and tests.
  Run `python -B -m tools.template list --format json` to discover registered
  project, product, tag and toolchain IDs. Its input-presence state is not a
  validation result; run `python -B -m tools.verify --project <id>` for the
  selected board.
  Shared policy and automation live under `tools/`, `catalog/` and `tests/`.
  For shared tooling changes, use the [tool map](tools/README.md),
  [test guide](tests/README.md) and [scripting standard](docs/workflow/SCRIPTING_STANDARD.md).
- For an existing design, preview the import before copying it. Use
  `python -B -m tools.template diagnose --source <path-to-.kicad_pro> --project-id <id> --toolchain <id>`.
  Read the import inventory and repair missing sheets or nonportable paths in
  the original source. Then follow the [import workflow](docs/workflow/IMPORT_WORKFLOW.md).
  For a directory with several candidates, first run
  `python -B -m tools.template scan-imports --source-dir <directory> --toolchain <id> --format json`.
  Review suggested IDs and every exclusion; the command is read-only and does
  not establish design completeness or electrical correctness.
- For a registered board, run
  `python -B -m tools.template diagnose --project-id <id>` before changing
  policy or tests. The default output groups repeated causes; `--detail full`
  prints every finding. Agents and scripts should parse `--format json` stdout,
  not the human text: the versioned report includes `status`, `findings`,
  `next_command` and `run_directory`. Each run also writes a fresh ignored
  `build/diagnostics/` receipt.
- If an unrelated malformed manifest blocks normal selected discovery, run
  `python -B -m tools.template rescue --project-id <id>` for a read-only local
  repair view. It always reports `UNVERIFIED_GLOBAL` and exits nonzero, even if
  the selected island looks clear. Never cite it as CI or release evidence;
  repair global discovery and rerun normal diagnosis and the full gate.
- For a new schematic-backed board with an empty component/net contract, run
  `python -B -m tools.contract_coach --project-id <id> --capture --format json`
  with the exact local KiCad CLI or the digest-pinned Docker image (`--runner auto`
  selects one). For an existing native report, use
  `--native-summary <project-summary.json>` instead. This read-only coach checks
  project identity, source hashes and netlist artifact evidence; its components
  and nets are explicitly `UNREVIEWED`. It never edits `tests/contract.json` or
  establishes electrical coverage. Keep optional receipts under ignored `build/`.
- For a PCB's 3D handoff, run
  `python -B -m tools.visualize --project <id> --check-models --format json`
  to inspect placed-footprint model coverage and candidate repository assets.
  For unassigned footprints, use `--init-model-map build/model-map.json` to
  create a hash-bound draft, enter explicit reviewed source-model paths, then
  use `--map-models build/model-map.json` to inspect the board/manifest diff
  before `--apply`. Repair existing assignments in KiCad. Then run
  `python -B -m tools.visualize --project <id>` to produce top/angled
  PNGs, STEP and GLB in a fresh ignored receipt. A successful export can still
  have `models.status=REVIEW`; inspect the actual geometry and follow the
  [3D workflow](docs/workflow/THREE_D_WORKFLOW.md). The manual **KiCad 3D preview**
  Action provides a focused hosted run without slowing routine PR lanes.

- For component selection or purchasing preparation, run
  `python -B -m tools.parts --project <id> --format json` to capture exact native
  evidence and produce a parts checklist. Use `--native-summary` for existing
  source-bound evidence, or `--init-preferences <path>` to create editable defaults
  without capture. Project `docs/purchasing.json` records board/spare preferences
  and explicitly reviewed DigiKey SKUs. Repair catalog identities, declared
  `component_identity.part_ids`, KiCad `PART_ID` fields and footprints at their
  sources. Do not invent purchasing identities or approve training placeholders.
  `READY_FOR_ORDER_REVIEW` means metadata is complete, not live stock, price,
  electrical, physical or release approval. Keep receipts under ignored `build/`
  and follow [parts to order](docs/workflow/PARTS_TO_ORDER.md).

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
3. After each source fix, run `python -B -m tools.verify --project <id>`.
   Add `--depth native` after KiCad source changes. It chooses an exact local
   CLI or the project's pinned Docker image and saves a new ignored receipt;
   `--format json` is the agent interface and `--detail full` expands human
   findings. Run `tools.template doctor --native --project-id <id>` if the
   runner cannot start. For a product, use `tools.ci --product <id>`; for a
   named cohort, use `tools.ci --tag <tag>`. Multiple include selectors form a union, and
   `--exclude-tag <tag>` removes projects afterward. Run the full
   `python -B -m tools.ci` gate after changing shared tools, catalogs or policy,
   and for a deliberate repository-wide rehearsal. After native KiCad inputs
   change, recheck affected BOMs and exports from the new receipt. Run
   `python -B -m tools.impact --base <ref> --head <ref> --format json`
   to inspect planned PR scope in a script or agent.
   For a manual hosted lane, run **KiCad template acceptance** in Actions with
   `focus=project` and `value=<id>` (or select `product` or `tag`). The default
   `focus=full` rehearses every lane; an optional `exclude_tag` narrows only a
   focused run. Preview the manual scope with `tools.impact --select-project <id>`.
4. Report the project ID, branch and commit, changed source, commands and
   results, receipt path, and any unresolved engineering decision. Keep run
   evidence in ignored `build/`, CI artifacts, or the issue/PR. Keep durable
   board decisions in `projects/<id>/docs/`.

Never commit imported practice projects, local KiCad state or generated working
outputs. Follow the [source and output policy](docs/workflow/REPOSITORY_HYGIENE.md)
and [BOM policy](docs/workflow/BOM_POLICY.md). A passing check verifies its
declared scope; it does not approve an electrical design or manufacturing release.
For an adopted GitHub repository, run the optional read-only
`python -B -m tools.governance_audit --format json` to inspect hosted branch
controls. Preserve `UNKNOWN` for inaccessible APIs and unverified real-team
permissions; follow the [GitHub governance guide](docs/workflow/GITHUB_GOVERNANCE.md)
for the human review and access rehearsals.
Project discovery is one level below each configured root, such as
`projects/<id>/`; nested project folders are not discovered. Use tags or
registered products to group independent islands.

When changing a CLI command, option or MCP tool, update the reviewed coverage in
`catalog/tool-surfaces.json` and run `python -B -m tools.surface --require-live-mcp`.
Read [tool surfaces](docs/workflow/TOOL_SURFACES.md) for required core parity and
explicit administrative/adapter exceptions. Core gaps fail even when documented;
update both interfaces and their referenced behavioral tests. Surface inspection
never runs those tests; the full tools.ci gate does. Neither grants design approval.
