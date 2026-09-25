# Importing an existing KiCad project

Import one deliverable into a project island. For a workflow rehearsal, use a
separate temporary copy of the candidate repository; keep the external designs
untracked there. Run the commands from the candidate repository with its Python
development environment installed.

For a directory containing several designs, first inventory it without copying:

```sh
python -B -m tools.template scan-imports --source-dir "/path/to/old boards" --toolchain kicad-10.0.5 --format text
```

The text view lists each `.kicad_pro`, suggested island ID, project kind, copied
and excluded counts, and its next import command. Use `--format json` for every
file hash, exclusion reason and failure. The scanner previews each design through
the normal one-project importer, skips local-state directories and leaves both
source and repository untouched. Review suggested IDs, collisions and exclusions;
run each accepted import separately. A clean inventory does not prove an archive
is complete or a circuit is correct.

```sh
python -B -m tools.template diagnose --source "/path/to/Old board.kicad_pro" --project-id battery-board --toolchain kicad-10.0.5 --format text
python -B -m tools.template import-project --source "/path/to/Old board.kicad_pro" --project-id battery-board --toolchain kicad-10.0.5 --format text
python -B -m tools.template diagnose --project-id battery-board
python -B -m tools.verify --project battery-board
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
that need executable assertions; see [test extension](../../tests/README.md).

After authoring those expectations, run the selected board through its exact
native toolchain. `tools.verify` retains an ignored receipt and gives repair
guidance when a check fails:

```sh
python -B -m tools.verify --project battery-board --depth native
```

Use `python -B -m tools.ci --matrix --format text` only to preview the native
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
green. Simulation-only examples can require a different engineering policy or a
future simulation lane; importing model files does not execute a SPICE simulation.

Use [checks and CI](CHECKS_AND_CI.md) for pinned-container execution. Keep rehearsal
receipts and reports in the temporary workspace or CI artifacts; promote only stable
requirements and decisions into the project or team documentation.
