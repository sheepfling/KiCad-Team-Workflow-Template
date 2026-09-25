# status-indicator-harness-interface

Training harness_interface project — NOT FOR MANUFACTURE.

- [Project manifest](project.json): identity, toolchain, local inventory and shared dependencies.
- [Design notes](docs/design.md): purpose and interface assumptions.
- [Native project](kicad/status-indicator-harness-interface.kicad_pro): open with the exact selected
  KiCad version.
- [Test contract](tests/contract.json): independent native expectations.

From the repository root, run `kicad-team ci --project status-indicator-harness-interface`. Optional
Python tests in this folder run automatically. Native checks use
`kicad-team ci --kicad --project status-indicator-harness-interface --output examples/projects/status-indicator-harness-interface/build/review-001`.
Use a fresh output path each attempt. Keep generated evidence in ignored `build/`.
