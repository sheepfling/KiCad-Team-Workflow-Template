# passive-signal-reference

Training schematic project — NOT FOR MANUFACTURE.

- [Project manifest](project.json): identity, toolchain, local inventory and shared dependencies.
- [Design notes](docs/design.md): purpose and interface assumptions.
- [Native project](kicad/passive-signal-reference.kicad_pro): open with the exact selected KiCad
  version.
- [Test contract](tests/contract.json): independent native expectations.

From the repository root, run `python -B -m tools.ci --project passive-signal-reference`. Optional
Python tests in this folder run automatically. Native checks use
`python -B -m tools.ci --kicad --project passive-signal-reference --output examples/projects/passive-signal-reference/build/review-001`.
Use a fresh output path each attempt. Keep generated evidence in ignored `build/`.
