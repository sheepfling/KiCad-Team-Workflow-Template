# Project and product tests

Install the [pinned environment](../../README.md#first-run-setup) first. Checks run the
installed tooling against this checkout and its independently authored engineering records.

```sh
# A board's checks and dependent product suites
kicad-team ci --project raspberry-pi-status-led
# All boards in a product, or a tagged cohort
kicad-team ci --product status-indicator-system
kicad-team ci --tag status-led
# Full project repository policy, docs, generation and all island suites
kicad-team ci
```

## Independent engineering expectations

Project `tests/contract.json` records expected nets/components or view relationships,
compared with actual native exports. These are durable source records owned by the board's
engineer. Never copy observed output into a contract merely to make a check pass.
When authoring a schematic-backed contract, use
`kicad-team contract-coach --project-id <id> --capture` to inventory observed KiCad
components and nets. The inventory is **UNREVIEWED**; compare it with the requirements and
schematic before independently writing expectations. MCP uses `capture_contract` for the same step.

The default `--runner auto` selects exact local KiCad or the digest-pinned Docker image.
The coach retains runner and command evidence under ignored `build/` and can inspect a hashed
native summary with `--native-summary`. It never changes or approves the test contract.

## Add a board or product check

Optional project `tests/test_*.py` files cover board-specific software or policy requirements.
The Raspberry Pi example's
[firmware test](../../examples/projects/raspberry-pi-status-led/tests/test_firmware.py)
checks its actual GPIO choice and blink timing with a fake GPIO adapter.
Product `tests/test_*.py` files cover integration requirements and run when a participating board
is selected. A selected lane also runs the applicable product policy and fresh generation checks.
Use the full command after changing catalogs or repository-wide policy.

Add a `unittest.TestCase` in a `test_*.py` file. Each island runs in a separate process with the
project repository root as its working directory, so module names cannot collide across boards.
Use `__file__` to locate island files and the installed `kicad_tooling` package for shared helpers.
Nested test directories need `__init__.py` for discovery. Tests must not depend on hardware,
network access or files on an engineer's desktop. Keep temporary outputs in the island's ignored
build area or a private temporary directory; suites can run concurrently.
Native and physical checks belong in their separately declared workflows.

`--project`, `--product` and `--tag` select a union; `--exclude-tag` removes projects afterward.
Tags live in each `project.json`; product membership lives in `catalog/products.json`.
See [checks and CI](CHECKS_AND_CI.md) for PR scope, partial shards and hosted execution.

| Change            | Useful coverage                                                                  |
| ----------------- | -------------------------------------------------------------------------------- |
| Requirement       | Independent expected result plus a mutation rejected for the intended reason     |
| Manifest/contract | Valid strict parse, wrong or unknown fields, unsafe paths and duplicate identity |
| Project generator | Expected values, deterministic ordering and stale/tampered evidence rejection    |
| Custom test       | A controlled failure demonstrably fails that project's gate                      |

## Shared tooling regression boundary

The installable CLI/MCP implementation and its regression suite live in
[KiCad Tooling](https://github.com/sheepfling/KiCad-Tooling), not in this template's root.
That repository runs implementation tests, CLI/MCP behavioral comparisons, Ruff and Pyright.
A template `kicad-team ci` run validates the project repository; it does not rerun the package's
source regression suite. Updating the tooling pin needs a reviewed acceptance run against the
project, including affected native workflows. See the [split and upgrade guide](TOOLING_SPLIT.md).

The retained [worked examples](../../examples/README.md) keep their manifests, independent
contracts, source and engineering notes together. They are training inputs, not approved designs.
[Electrical deck examples](../../templates/electrical/README.md) likewise do not establish
physical grounding, thermal behavior or RF acceptance. Preserve their fixture disclaimers.
