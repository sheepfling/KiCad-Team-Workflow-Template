# Diagnose and repair a project

Use the same sequence for a new board, an imported legacy board, or a failed CI job.
Work on a branch, keep the original design, and change one source problem at a time.
The diagnostic command pairs observed failures with a repair action and a durable
guide. It does not edit KiCad files, waive checks, or approve the electrical design.

## Before importing

```sh
python -B -m tools.template doctor
python -B -m tools.template diagnose --source "/path/to/board.kicad_pro" --project-id battery-board --toolchain kicad-10.0.5
```

The second command previews the same import inventory as `import-project --dry-run`.
It reports missing/escaping sheets and nonportable source paths as blockers, and
groups excluded files for review. Fix a `Sheetfile` reference in the source project
and rerun the preview. If a sheet lives outside the selected project directory,
move it and its dependencies into the project or plan a separately declared shared
library. Never make an import pass by silently omitting a sheet. After a clean
preview, run [the actual import](IMPORT_WORKFLOW.md) and inspect `docs/import.json`
inside the new island.

## After creating or importing a project

```sh
python -B -m tools.template diagnose --project-id battery-board
python -B -m tools.ci --project battery-board
```

`diagnose` runs the selected portable policy and project test lane. Its `NEEDS_WORK`
result names the failed input and next action. A `PASS` means only that this local
diagnostic scope has no blockers; it does not replace the full CI gate or native
KiCad. Use `--format json` when a script needs stable fields.

| Finding | Engineer's repair |
| --- | --- |
| `CAD_PATH` machine-local path | Bring the actual asset into the project or a declared shared library, then update the KiCad reference to a portable path. |
| `CAD_PATH` old variable | Use the correct library variable for the pinned KiCad version, or a reviewed project-local asset via `KIPRJMOD`; verify the target exists. |
| `CAD_PATH` missing or case-mismatched target | Correct exact spelling/case or add the intended asset. Do not add a dummy file. |
| `EMPTY_COMPONENT_CONTRACT` | Write independently reviewed expected components and nets in `tests/contract.json`; compare with the native export without treating the export as authority. |
| `PROJECT_TEST` | Read the failing assertion and requirement, repair the design or test fixture, then rerun the selected lane. |
| `PART_ID_SCOPE` or `EXPORT_SETTINGS` | Complete these reviewed records before purchasing or manufacturing work; a portable pass does not imply release readiness. |
| `PCB_ONLY_SCOPE` | Keep board capture in development. Add an authoritative schematic before electrical or manufacturing claims. |

## After a native check

Run the exact toolchain and keep each native output directory distinct. Point the
coach at the **project** summary beneath that output:

```sh
python -B -m tools.ci --kicad --project battery-board --output projects/battery-board/build/review-001
python -B -m tools.template diagnose --project-id battery-board --native-report projects/battery-board/build/review-001/battery-board/summary.json
```

If the declared design files changed since that report, the coach marks it stale;
rerun native validation before acting on its old findings.

For a failed ERC or DRC check, open the referenced `erc.json` or `drc.json` and
resolve each violation, unconnected item, parity finding, or exclusion. If the
disabled-check inventory changed, enable the named checks in KiCad's Schematic
Setup or Board Setup and resolve the new findings. Do not copy disabled defaults into
a development contract to obtain a pass. A netlist mismatch requires a reviewed
decision about the circuit and the independent contract; neither should be changed
automatically to match the other. See [checks and CI](CHECKS_AND_CI.md) and
[test authority](../../tests/README.md).

## Before a purchasing BOM or release export

After a native schematic BOM export, check its controlled part identities:

```sh
python -B -m tools.template diagnose --project-id battery-board --native-report projects/battery-board/build/review-001/battery-board/summary.json --bom build/release-candidate/assembly/bom.csv
```

The matching native report binds the BOM rows to this project's source and netlist.
The coach lists fitted references with missing or unknown `PART_ID` values and
flags training-only catalog records. Assign identities in the schematic and review
their records in `catalog/parts.json`; regenerate the BOM instead of editing its
CSV. A clean identity check is one prerequisite, not sourcing or release approval.
Use the [BOM policy](BOM_POLICY.md) and [release readiness](RELEASE_READINESS.md)
before freezing or distributing manufacturing outputs.
