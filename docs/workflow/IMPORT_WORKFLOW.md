# Importing an existing KiCad project

Import one deliverable into a project island. For a workflow rehearsal, use a
separate temporary copy of the candidate repository; keep the external designs
untracked there. Run the commands from the candidate repository with its Python
development environment installed.

## Keep a reusable practice library

For repeated experiments, keep a local `KiCad-Rehearsal/` folder outside both the
project template and tooling repositories. Use `DUMP/` for original incoming
archives, `sources/` for extracted snapshots and their provenance, `runs/` for
disposable initialized project copies, and `reports/` for findings. Preserve
licenses and source hashes. Do not edit the downloaded originals or commit
practice projects to the template.

Install the template's tooling pin into a normal Python environment. A developer
testing a tooling update can use a separately installed wheel; record its version
and hash so that the tested code is clear. The acquisition kit's older `tools.*`
commands belong to the combined repository and should not be used with this split
template. Use `kicad-team` or `python -I -m kicad_tooling` from the installed package.

Point `--root` at the disposable project copy and `--source-dir` or `--source` at
the extracted snapshot. MCP uses the same arrangement: start `kicad-team-mcp`
with `--root /path/to/disposable-project` and
`--import-root /path/to/extracted-snapshot`. Add `--allow-writes` for import,
`--allow-checks` for verification and `--allow-exports` for parts and 3D evidence.
The rehearsal library itself is not an MCP project root.

Record import, portability, electrical checks, plots, parts and 3D results
separately. A copied project can pass portability checks while diagnosis still
asks for independent electrical requirements. Missing part identities block a
purchasing BOM; missing models limit an otherwise successful 3D export. Keep those
findings visible instead of turning a successful import into a design approval.

The tooling repository owns the reusable corpus runner and its regression tests.
Each run should identify both repository revisions, the installed tooling version,
the selected source pins and the fresh receipt locations. Use a new run directory
when comparing tooling versions so earlier evidence stays intact.

## Convert a foreign PCB before native import

For a non-KiCad board file supported by KiCad's `pcb import` command (PADS,
Altium, Eagle, CADSTAR, Fabmaster, P-CAD or SolidWorks), convert it into an
ignored, per-run review receipt with the exact catalogued KiCad version:

```sh
kicad-team template convert-pcb --source "/path/to/vendor-board.brd" --project-id battery-board --toolchain kicad-10.0.5 --input-format auto --format text
```

Use `--format json` for a typed receipt containing the source hash, runner,
command evidence, converted-board hash, native import preview and next command.
`--runner auto` selects an exact local CLI or the digest-pinned Docker image;
`--runner local --cli /path/to/kicad-cli` and `--runner container` are explicit
choices. Inspect `events.log`, `convert-command.json` and the raw
`kicad-import-report.json` in the reported `build/diagnostics/` directory if
conversion fails. The source remains untouched. A successful conversion creates
only `stage/<id>.kicad_pcb` and `stage/<id>.kicad_pro` in that ignored receipt;
it does not add a project island.

Open the converted board in the same KiCad version. Compare copper and mechanical
layers, board outline, net names, footprints, dimensions and the import report
against the original and reference outputs. Resolve any importer warnings or
layer-mapping ambiguity with the responsible engineer. Then run the receipt's
`next_command`, which uses the normal native importer and creates a `pcb_only`
development island. This CLI converts a PCB only; it does not convert a schematic
or establish schematic parity, electrical truth or manufacturing readiness.

For a directory containing several designs, first inventory it without copying:

```sh
kicad-team template scan-imports --source-dir "/path/to/old boards" --toolchain kicad-10.0.5 --format text
```

The text view lists each `.kicad_pro`, suggested island ID, project kind, copied
and excluded counts, and its next import command. Use `--format json` for every
file hash, exclusion reason and failure. The scanner previews each design through
the normal one-project importer, skips local-state directories and leaves both
source and repository untouched. Review suggested IDs, collisions and exclusions;
run each accepted import separately. A clean inventory does not prove an archive
is complete or a circuit is correct.

```sh
kicad-team template diagnose --source "/path/to/Old board.kicad_pro" --project-id battery-board --toolchain kicad-10.0.5 --format text
kicad-team template import-project --source "/path/to/Old board.kicad_pro" --project-id battery-board --toolchain kicad-10.0.5 --format text
kicad-team template diagnose --project-id battery-board
kicad-team verify --project battery-board
```

`--root` selects a different candidate repository. The source argument names the
specific `.kicad_pro`; its original filename does not have to match the new island ID.
Native files and local dependencies retain their names, directory relationships and
bytes under `projects/battery-board/kicad/`. Import leaves the originals untouched,
never overwrites an existing island and publishes the destination only after copying
and verifying its complete inventory.

The importer follows hierarchical `Sheetfile` references when a schematic exists,
includes local symbols, footprints, simulation models and other permitted supporting
files, and inventories all copied inputs. Separate sibling/nested projects get
separate imports. Symlinks, case conflicts and escaping or missing sheets fail with a
diagnostic. Dependencies outside the selected project directory need a separate,
explicit migration into local or declared shared storage.
The initial diagnostic is a read-only dry run with a fresh, ignored log and a
repair queue. Fix blockers and preview again before copying. See
[diagnose and repair](DIAGNOSTICS.md) for the log contents and each failure class.

Review `docs/import.json` before accepting the import. It records file hashes and
exclusions: local preferences/caches, working fabrication exports, separate designs
and artifacts restricted by repository policy. Excluded images or files may leave
upstream documentation links to repair. Authored CSV inputs are preserved; a CSV's
extension alone cannot tell us whether it is authored source or a generated BOM.
See [BOM policy](BOM_POLICY.md).

## Establish test authority

Import success means the copy completed. It does not mean the design passes checks.
The importer creates a **development** manifest and a test-contract skeleton without
inventing part IDs, approved suppliers or electrical requirements.

For a PCB with its matching schematic, fill in the independent component/net
expectations in `tests/contract.json`.
Native net names can include supply signs, buses and hierarchy; an unassigned
footprint can be represented but still receives KiCad's own checks. An empty PCB
contract cannot pass native validation. Add local `test_*.py` files for requirements
that need executable assertions; see [test extension](PROJECT_TESTS.md).

After authoring those expectations, run the selected board through its exact
native toolchain. `kicad-team verify` retains an ignored receipt and gives repair
guidance when a check fails:

```sh
kicad-team verify --project battery-board --depth native
```

Use `kicad-team ci --matrix --format text` only to preview the native
lanes that CI will schedule; it does not validate the board.

When the source has a `.kicad_pcb` but no matching `.kicad_sch`, import creates a
`pcb_only` island. It preserves and inventories the board, runs native DRC and a PCB
render, and marks the island development/not-for-manufacture. It intentionally does
not claim ERC, schematic parity, a netlist/component contract, product assembly BOM
coverage or manufacturing-release readiness. Treat it as a capture and review lane:
reconstruct or adopt an authoritative schematic, then migrate the island to `pcb`
before it becomes an electrical or production deliverable.

An exported netlist can seed an explicitly labelled observation snapshot for import
regression testing. It does not independently prove the circuit is correct. Keep
requirements such as connector pin assignments, supply constraints and firmware
behavior independently authored and reviewed. Deliberately break one requirement,
confirm the selected gate fails, restore it and confirm it passes.

## Resolve native findings

Run the exact toolchain selected by the manifest. Native validation checks repository
portability before invoking KiCad and writes evidence only to a fresh output path.
Old library variables, machine-specific paths and missing assets require reviewed
migration. Embedded 3D-model references are local to their containing native file;
static policy checks record presence, while native KiCad owns decoding.
After import, use the [3D workflow](THREE_D_WORKFLOW.md) to inventory assigned
models, make their paths portable and generate review views from the registered PCB.

Development/production contracts cannot whitelist disabled ERC/DRC checks. Existing
KiCad projects may have disabled defaults: enable the applicable checks, rerun and
resolve the findings. Do not change the assurance profile merely to make an import
green. Simulation-only examples can require a different engineering policy. Add the
[electrical analysis lane](ELECTRICAL_ANALYSIS.md) for reviewed simulation cases;
importing model files does not execute a SPICE simulation.

Use [checks and CI](CHECKS_AND_CI.md) for pinned-container execution. Keep rehearsal
receipts and reports in the temporary workspace or CI artifacts; promote only stable
requirements and decisions into the project or team documentation.
