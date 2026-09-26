# Examples — training and regression fixtures

> [!CAUTION]
> These files teach the workflow and exercise automated checks. They are not starter projects,
> approved designs, part selections, fit evidence or manufacturing data. For real work in an
> adopted repository, create a board under `projects/<id>/`; use
> [First board](../docs/workflow/FIRST_BOARD.md) or the
> [Import workflow](../docs/workflow/IMPORT_WORKFLOW.md). Do not rename a fixture to make it a
> real project.

The folder structure is the pattern to repeat under `projects/<id>/`. The sample requirements,
contracts, product links and model notes belong to these rehearsals only. A passing example check
verifies its declared fixture scope; it does not approve a real board or product.

Use the folder guides before browsing each collection: [project fixtures](projects/README.md),
[product fixtures](products/README.md), [regression catalogs](catalog/README.md) and the
[training library](libraries/README.md).

| Project                                                                    | Demonstration                                             |
| -------------------------------------------------------------------------- | --------------------------------------------------------- |
| [Controller](projects/controller/README.md)                                | Minimal PCB fixture and native negative probes            |
| [Arduino status LED](projects/arduino-uno-status-led/README.md)            | PCB, host interface, shared library and local firmware    |
| [Raspberry Pi status LED](projects/raspberry-pi-status-led/README.md)      | PCB plus automatically executed board-local firmware test |
| [Passive signal reference](projects/passive-signal-reference/README.md)    | Schematic-only project                                    |
| [System wiring](projects/status-indicator-wiring/README.md)                | Whole-product relationship view                           |
| [Harness interface](projects/status-indicator-harness-interface/README.md) | Conductor and endpoint coverage                           |

The [reference product](products/status-indicator-system/README.md) joins several projects without
taking ownership of their source. The [shared training library](libraries/status-led/README.md) is a
declared dependency. `examples/catalog/` contains isolated regression catalog inputs; the live
discovery settings and product index remain in root `catalog/`.

Keep these fixtures for training and acceptance rehearsal. Disable `examples/projects` in the live
`project_roots` and remove reference product-index entries when they should no longer
create live/native checks. Do not turn a fixture into production source by renaming it.
