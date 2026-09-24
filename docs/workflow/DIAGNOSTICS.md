# Diagnose and repair a project

Use the same sequence for a new board, an imported legacy board, or a failed CI job.
Work on a branch, keep the original design, and change one source problem at a time.
The diagnostic command pairs observed failures with a repair action and a durable
guide. It does not edit KiCad files, waive checks, or approve the electrical design.
Run it from the repository root with the installed Python environment. A failure
exit (`1`) means the board needs work; `2` means the diagnostic command itself
could not finish. Both are different from an electrical judgment.

Every invocation creates a new ignored `build/diagnostics/<project>-.../` receipt.
Terminal output shows a short repair queue, grouping repeated findings by cause;
the receipt preserves every location. Its files are:

| File | When to open it |
| --- | --- |
| `events.log` | See which stage started, completed, or stopped, with elapsed time. |
| `diagnosis.txt` / `diagnosis.json` | Read the repair queue or every finding and exact file location. |
| `import-preview.json` or `portable.json` | Inspect the underlying import inventory or selected CI result, including failing project-test stdout/stderr. |
| `native-summary.json` | Check the native report identity and each recorded KiCad check. The original native output directory holds `erc.json`, `drc.json` and `*.command.json`. |
| `error.txt` | Read the complete Python traceback when the coach itself stops unexpectedly. |

The receipt also includes `run.json` with Python/platform identity, timing, and
run status. No KiCad source files are copied into it. It remains outside Git under
`build/`. Use `--log-dir /path/to/new/directory` to select a fresh external
location; an in-repository custom location must also be under ignored `build/`.
For a crash, start with `events.log`, then `error.txt`; retain both when asking a
tool maintainer for help. If the log cannot be created, fix `build/` permissions or
use `--log-dir` outside the checkout.

Choose the amount of output you need without changing the checks:

| View | Command option | Use it for |
| --- | --- | --- |
| Short repair queue | default or `--detail brief` | First pass: repeated causes are grouped, with up to three example locations per group. |
| Every finding in text | `--detail full` | A larger terminal dump with every location, observation, repair action and guide. The same text is saved as `diagnosis.txt`. |
| Complete structured data | `--format json` | Scripts or agents that need stable fields and every finding. The same data is saved as `diagnosis.json` on every run. |

The options work with either import preview or an existing project. JSON
already contains all findings, so it does not take `--detail`. Progress
messages go to stderr; stdout stays suitable for saving or parsing. A large
board may have hundreds of instances of one cause: start with the short queue,
then inspect the full receipt to find all locations. Do not paste a huge dump
into project documentation.

For a tool failure, read `events.log` to find the last stage and `error.txt`
for the traceback. Include those files, the command, and `run.json` when
reporting a coach bug. The stage log identifies whether import preview,
portable checks, native-report inspection or BOM inspection stopped.

## Before importing

```sh
python -B -m tools.template doctor --format text
python -B -m tools.template diagnose --source "/path/to/board.kicad_pro" --project-id battery-board --toolchain kicad-10.0.5
```

The second command previews the same import inventory as `import-project --dry-run`.
It reports missing/escaping sheets and nonportable source paths as blockers, and
groups excluded files by reason for review. Fix a `Sheetfile` reference in the source project
and rerun the preview. If a sheet lives outside the selected project directory,
move it and its dependencies into the project or plan a separately declared shared
library. Never make an import pass by silently omitting a sheet. After a clean
preview, run [the actual import](IMPORT_WORKFLOW.md) and inspect `docs/import.json`
inside the new island.

## After creating or importing a project

```sh
python -B -m tools.template diagnose --project-id battery-board
python -B -m tools.verify --project battery-board
```

`diagnose` runs the selected portable policy and project test lane. Its `NEEDS_WORK`
result names the failed input and next action. A `PASS` means only that this local
diagnostic scope has no blockers; it does not replace the full CI gate or native
KiCad. Add `--depth native` to `tools.verify` after KiCad source changes. Use
`--format json` when a script needs stable fields.

If an unrelated malformed project manifest prevents normal discovery, use the
local rescue command to inspect one direct island while repairing the registry:

```sh
python -B -m tools.template rescue --project-id battery-board
python -B -m tools.template rescue --project-id battery-board --detail full
python -B -m tools.template rescue --project-id battery-board --format json
```

Rescue reads the configured project roots, the selected `project.json`, its
contract and toolchain, and its declared source inventory and CAD references.
It does not parse peer manifests, run project Python tests or KiCad, or establish
global catalog, product, CI, or release validity. Every result says
`UNVERIFIED_GLOBAL`, `ci_eligible: false`, and `release_eligible: false`; even a
locally clear result exits `1`. A fresh ignored receipt keeps `diagnosis.json`,
`diagnosis.txt`, stage logs and the selected parsed inputs. Use `--detail full`
for every local finding or `--format json` for an agent. Repair the peer manifest,
then return to normal `diagnose` and the full CI gate. Rescue never replaces
those fail-closed checks.

Start with the first blocking group in the terminal, repair one cause, then run
the displayed next command. Do not copy observed KiCad output into an independent
test contract just to make a red check green. `REVIEW` rows can remain after the
portable lane passes, but they must be resolved before the activity they name
(such as purchasing or manufacturing).

| Finding | Engineer's repair |
| --- | --- |
| `IMPORT` missing matching design or sheet | Select a complete saved project, repair the sheet reference in KiCad, or use the explicit PCB-only lane for a real board-only source. Do not make up a missing schematic. |
| `IMPORT` nonportable/case-colliding/linked path | Rename the source and its references to an exact portable spelling, or bring the real asset into a declared local/shared library. Preview again before copying. |
| `IMPORT_EXCLUSIONS` | Open `import-preview.json` to see every excluded path. Regenerate exports, leave caches behind, review restricted authored assets separately, and import sibling/nested designs as separate islands. |
| `CAD_PATH` installed KiCad library path | Replace the operating-system installation prefix with the pinned versioned KiCad library variable and verify the named library exists. Do not copy the whole standard library into the project. |
| `CAD_PATH` private machine path | Bring the actual custom asset into the project or a declared shared library, then update the KiCad reference to a portable path. |
| `CAD_PATH` old variable | Use the correct library variable for the pinned KiCad version, or a reviewed project-local asset via `KIPRJMOD`; verify the target exists. |
| `CAD_PATH` missing, embedded or case-mismatched target | Correct exact spelling/case or add the intended asset and verify it opens in KiCad. Do not add a dummy file. |
| `TRACKED_GENERATED_OUTPUT`, `TRACKED_LOCAL_STATE`, `TRACKED_UNMANAGED_ARTIFACT` | Keep generated exports and local state under ignored `build/`; remove already tracked copies from the Git index with `git rm --cached -- <path>` after confirming their source of truth. Review any authored document or image placement before moving it. |
| `UNREGISTERED_DESIGN` | Give a separate native design its own registered island; do not hide it in another project's input inventory. |
| `EMPTY_COMPONENT_CONTRACT` | Run `tools.contract_coach --project-id <id> --capture` to inventory UNREVIEWED components and nets with exact local KiCad or the catalogued digest-pinned Docker image. Compare them with requirements, then write independent expectations in `tests/contract.json`. |
| `EMPTY_NET_CONTRACT` | Review the empty net expectation; author real expected connectivity or record that the design is intentionally net-free. |
| `PROJECT_TEST` | Read the failing assertion and requirement, repair the design or test fixture, then rerun the selected lane. |
| `PART_ID_SCOPE` or `EXPORT_SETTINGS` | Complete these reviewed records before purchasing or manufacturing work; a portable pass does not imply release readiness. |
| `PCB_ONLY_SCOPE` | Keep board capture in development. Add an authoritative schematic before electrical or manufacturing claims. |

When `PROJECT_TEST` names `discovery`, check that the island has discoverable
`test_*.py` files, package markers in nested test folders, and valid imports.
The selected gate detects a newly added failing test automatically; do not edit a
central list of test lanes. For a missing asset, first inspect the named KiCad
source location and the corresponding file path. Do not suppress the policy check.

## Repair loop for people and agents

1. Select the board ID and run the smallest relevant diagnosis: import preview
   before copying, or the selected project lane after copying. Keep the receipt
   path from the terminal.
2. Work through `BLOCKING` groups first. Open the named source location and
   underlying `import-preview.json`, `portable.json`, or native report when the
   short explanation is insufficient. Use `--detail full` or `diagnosis.json`
   to find the remaining instances of a repeated cause.
3. Fix the authoritative input, not the generated report. Mechanical repairs
   include correcting a known filename or case mismatch, restoring a missing
   declared asset from its source, and repairing test discovery. Inspect the
   diff before proceeding.
4. Treat circuit topology, pins, part substitutions, net expectations,
   ERC/DRC exclusions and release decisions as engineering choices. Compare
   them with requirements and ask the responsible engineer when evidence is
   missing; an agent must not invent an electrical expectation or waive a
   check to obtain a green result.
5. Rerun diagnosis and the selected CI lane after each source fix. Use the full
   CI gate after shared tooling or policy changes; PR CI also checks the affected
   scope. After KiCad source changes, regenerate native results in a fresh output
   directory and recheck any derived BOM or export.

For handoff, report the project ID, branch/commit, command, receipt directory,
finding code and source location, repair made, checks rerun, and any unresolved
engineering decision. Keep evidence in ignored `build/`, a CI artifact, or the
issue/PR; keep durable design decisions in that project's `docs/`.

## After a native check

Run `python -B -m tools.verify --project battery-board --depth native` for
selected portable and native validation with a fresh ignored receipt. It picks
an exact local KiCad CLI when installed, otherwise the board's digest-pinned
Docker image. Use `--runner local` or `--runner container` for an explicit
choice; `--format json` gives agents the typed result, and `--detail full` shows
every repair finding. Its receipt keeps `events.log`, `verification.json`, the
raw runner commands, and the native project summary. If no native report could
be produced, inspect `dependency-command.json` or `native-command.json` for
the setup failure; `error.txt` identifies a tool crash.

The lower-level command remains available when manually replaying a CI lane.
Keep each native output directory distinct and point the coach at the **project**
summary beneath that output:

```sh
python -B -m tools.ci --kicad --project battery-board --output projects/battery-board/build/review-001 --format text
python -B -m tools.template diagnose --project-id battery-board --native-report projects/battery-board/build/review-001/battery-board/summary.json
```

If the declared design files changed since that report, the coach marks it stale;
rerun native validation before acting on its old findings.
The native output directory is write-once. Use a new path for each attempt; then
pass that attempt's project `summary.json` to the coach. If KiCad failed before it
wrote a normal report, open `*.command.json` for the exact argv, stdout, stderr,
and return code. If the coach itself failed, open its `error.txt` and `events.log`.

For a failed ERC or DRC check, open the referenced `erc.json` or `drc.json` and
resolve each violation, unconnected item, parity finding, or exclusion. If the
disabled-check inventory changed, enable the named checks in KiCad's Schematic
Setup or Board Setup and resolve the new findings. Do not copy disabled defaults into
a development contract to obtain a pass. A netlist mismatch requires a reviewed
decision about the circuit and the independent contract; neither should be changed
automatically to match the other. `tools.contract_coach --project-id <id>
--native-summary <project-summary.json> --detail full` verifies the native netlist
hash and current declared design hashes, then shows every observed component and
net beside a concise difference list. JSON output retains both full inventories
for agents. A failed native contract comparison may still provide usable
UNREVIEWED observations when the KiCad export itself succeeded; it does not turn
the failed validation green. See [checks and CI](CHECKS_AND_CI.md) and
[test authority](../../tests/README.md).

For an empty electrical contract, `tools.contract_coach --project-id <id> --capture`
exports an observed netlist before native validation can pass. The default
`--runner auto` tries an exact local KiCad CLI, then the digest-pinned Docker
image. `--runner local --cli <path>` and `--runner container` select one path.
If capture fails, open `version.command.json` or `netlist.command.json` in the
reported ignored receipt; an auto fallback also retains `local_version.command.json`
and `container_version.command.json`. The `--format json` report records the
selected runner and every command, including stdout, stderr, return code and
launch error. The coach never writes or approves `tests/contract.json`.

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

An incomplete download or timed-out corpus snapshot is an input-integrity problem,
not a design failure. Reacquire and verify the complete source before import; do
not infer missing schematics or dependencies from a partial backup. The import
receipt records copied file hashes and exclusions, but it cannot certify the
upstream archive's completeness.
