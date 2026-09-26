# raspberry-pi-status-led

Training pcb project — NOT FOR MANUFACTURE.

- [Project manifest](project.json): identity, toolchain, local inventory and shared dependencies.
- [Design notes](docs/design.md): purpose and interface assumptions.
- [Native project](kicad/raspberry-pi-status-led.kicad_pro): open with the exact selected KiCad
  version.
- [Test contract](tests/contract.json): independent native expectations.

From the repository root, run `kicad-team ci --project raspberry-pi-status-led`. Optional Python
tests in this folder run automatically. Native checks use
`kicad-team ci --kicad --project raspberry-pi-status-led --output examples/projects/raspberry-pi-status-led/build/review-001`.
Use a fresh output path each attempt. Keep generated evidence in ignored `build/`.
