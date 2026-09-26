# Know what has been checked

Use this checklist with the electrical owner and mechanical reviewer for every new or imported
board. Record decisions in `projects/<id>/docs/`; keep run receipts under ignored `build/`.
An imported project's files are observations, not independently approved requirements.

Each row needs an outcome: **passed with current evidence**, **failed**, **not run**,
**not configured**, **review needed**, or **not applicable with a reviewed reason**. A missing
contract is not a not-applicable decision. A passing earlier step never completes later steps.

## Follow the board through the gates

Replace `my-board` with the ID from `kicad-team template list`. Every CLI entry in the table
is prefixed with `kicad-team`. For MCP, read the structured status and findings, not just whether
the call succeeded.

| Gate                    | CLI entry                                                           | MCP entry                                                                                 | Evidence and review                                                                                                                                |
| ----------------------- | ------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| Import and dependencies | `template diagnose`, `template import-project`                      | `preview_import`, `import_project`                                                        | Review missing sheets, library paths, exclusions and copied source.                                                                                |
| Workstation             | `template doctor --native --project-id my-board`                    | `doctor`                                                                                  | Exact KiCad version or pinned container; add electrical preflight for ngspice.                                                                     |
| Connectivity            | `verify --project my-board --depth native`                          | `check_project(depth="native")`                                                           | ERC/DRC and netlist versus independently authored components, pins and nets. Empty expectations cannot establish coverage.                         |
| Grounding               | `verify --project my-board --depth electrical`                      | `check_project(depth="electrical")`                                                       | Declared ground domains and pin coverage. Review return paths, plane continuity, chassis/earth connections and layout separately.                  |
| Power draw              | Same electrical check                                               | Same electrical check                                                                     | Reviewed rail/load budgets, derated limits and steady-state current/power measurements. Include supply, connector, wiring and thermal assumptions. |
| Startup and transients  | Same electrical check                                               | Same electrical check                                                                     | Authored inrush, sag, overshoot and protection cases where relevant. Missing model effects or measurements remain unassessed.                      |
| Frequency and edges     | Same electrical check                                               | Same electrical check                                                                     | Reviewed AC/transient models and limits. PCB parasitics, coupling and EMC need appropriate models and engineering review.                          |
| Parts selection         | `parts --project my-board --assist`                                 | `prepare_part_picker`, `preview_part_selection`, `apply_part_selection`                   | Exact reviewed identity, ratings, package, pinout and approved alternatives. Catalog metadata is not live stock or price evidence.                 |
| CAD download            | `parts --project my-board --source-cad C2040 --expected-mpn RP2040` | `source_cad`, `preview_cad_import`, `apply_cad_import`                                    | Exact-part identity, source hashes, pins/pads and portable paths. Review manufacturer dimensions and pin functions.                                |
| Mechanical views        | `visualize --project my-board`; parts STEP comparison               | `export_3d`, `check_step_alignment`                                                       | Review board views and paired model alignment; an image/export PASS is not physical-fit approval.                                                  |
| BOM and quantities      | `parts --project my-board`                                          | `prepare_parts`                                                                           | Fitted population, PART_ID, exact MPN, build quantities and spares. Resolve NEEDS_PARTS/BLOCKED; review purchasing CSV before ordering.            |
| Revision and handoff    | `release prepare`, `check`, `package`, `verify`, `restore`          | `prepare_review`, `check_release`, `package_release`, `verify_package`, `restore_package` | Clean source commit, correct population, retained evidence and restore rehearsal. Production authority and Git tagging are explicit human steps.   |

Follow [parts to order](PARTS_TO_ORDER.md), [CAD sourcing](CAD_SOURCING.md),
[3D review](THREE_D_WORKFLOW.md) and [release readiness](RELEASE_READINESS.md) for complete
arguments and permission settings. The [surface map](TOOL_SURFACES.md) records CLI/MCP exceptions.

## Make electrical coverage deliberate

For a schematic-backed project, begin with:

```sh
kicad-team template diagnose --project-id my-board
kicad-team electrical --project my-board --init
```

The starter marks grounding, power and frequency sections `pending`. Have the electrical owner
author required checks or reasoned `not_applicable` decisions, simulator version, models and
limits. Do not fill these from a passing observed output. Capture candidate input hashes,
review their circuit-to-model mapping and follow [electrical analysis](ELECTRICAL_ANALYSIS.md).

```sh
kicad-team template doctor --electrical --project-id my-board
kicad-team verify --project my-board --depth electrical
```

The MCP path is `init_electrical`, `capture_electrical_inputs`, electrical `doctor`, then
`check_project` with `depth="electrical"`. Export charts from the saved electrical receipt
using `electrical-charts` or `export_electrical_charts`; a chart does not rerun or approve analysis.
Board-only imports need an authoritative schematic before this electrical setup.

## Read PASS within its scope

- **Portable:** repository policy, configured electrical requirement/model bindings and static
  budgets. It does not run KiCad or simulations.
- **Native:** adds KiCad ERC/DRC, authored connectivity and configured grounding checks. It does
  not run transient or AC simulations.
- **Electrical depth:** adds exact simulator preflight and all configured electrical cases to
  portable/native verification. A prior failure leaves later stages not run.
- **Focused electrical analysis:** runs declared electrical checks but does not itself run
  ERC/DRC. Use the combined verification above for a board review.
- **Parts ready:** purchasing metadata is complete for review. It does not confirm availability,
  substitutions, electrical suitability or manufacturing approval.

Diagnosis reports absent electrical requirements as a review task. Portable/native verification
can still pass its limited scope; it tells you full electrical analysis was not run. Once an
electrical contract is declared, pending sections and invalid bindings block policy checks.
Preserve failed, unconfigured and not-run results in the handoff.

## Revise without losing evidence

Use a short-lived branch and record why the board is changing. Review impacts on connectivity,
grounding, power, frequency, part identity, footprints, population and mechanical interfaces.
After source changes, rerun affected checks and regenerate BOM/plots/models from current evidence.
Changed source/model hashes require review before updating approved bindings. Keep the tooling
package version separate from board revision and product revision.

Follow [versioning](VERSIONING.md) to commit reviewed source, create an engineering-review
candidate, obtain applicable approvals, tag the exact source and retain/restore its package.
Never move a published tag or substitute an old BOM after a design or population change.

Normal hosted native acceptance runs every declared electrical contract. Release preparation
requires and retains that evidence; check, package, verify and restore revalidate its source,
requirements, simulator logs, decks and waveforms. A build release requires an electrical contract
for a schematic-backed board, with reviewed reasons for sections that do not apply. An
engineering-review candidate may retain NOT_CONFIGURED coverage, visibly recorded in review.md.
Physical validation, approved part choices and release authority still require their named owners.
