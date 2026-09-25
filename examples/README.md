# Reference project islands

These are maintained training and regression inputs, separate from adopted work.
Their folder structure is the pattern to repeat under `projects/<id>/`.

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

Keep these fixtures for shared-tool tests. Disable `examples/projects` in the live
`project_roots` and remove reference product-index entries when they should no longer
create live/native checks. Do not turn a fixture into production source by renaming it.
