# Independent project folders

Create each deliverable under `projects/<id>/` with one `project.json`, a `kicad/`
folder, local `docs/` and `tests/contract.json`. Use the same pattern for PCB,
schematic, wiring and harness-interface work; the kind is recorded in the manifest.

Run
`python -B -m tools.template new-project --project-id battery-board --kind pcb --toolchain kicad-10.0.5`
from the repository root to create a development scaffold. Save the real design and complete the
inventory/contract before checking it. Discovery adds its CI lane.

Firmware, custom Python tests and release records are optional. Keep outputs under this project's
ignored `build/`. See the [folder standard](../docs/workflow/REPOSITORY_STRUCTURE.md),
[test guide](../tests/README.md) and [worked examples](../examples/README.md).
