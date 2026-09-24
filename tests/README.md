# Shared tests and project-specific tests

Install the [development environment](../README.md#first-run-setup) first.

```sh
# Shared tooling regression suite
python -B -m unittest discover -s tests -v
# One shared module
python -B -m unittest tests.test_product -v
# A board's checks and dependent product suites
python -B -m tools.ci --project raspberry-pi-status-led
# All boards in a product, or a tagged cohort
python -B -m tools.ci --product status-indicator-system
python -B -m tools.ci --tag status-led
# Full repository and all test scopes
python -B -m tools.ci
```

Root `tests/` verifies the shared tools, using `tests.support.reference_root()` to
assemble isolated reference inputs. The live project's catalogs cannot silently
rewrite regression expectations. The CI driver separately validates the live tree.

Project `tests/contract.json` records independent expected nets/components or view
relationships, compared with actual native exports.
When first authoring a schematic-backed contract, use
`tools.contract_coach --project-id <id> --capture` to inventory observed KiCad
components and nets before writing expectations. The inventory is UNREVIEWED;
compare it with requirements and keep the contract independently authored.
The coach can also inspect a hashed native summary with `--native-summary`.
Optional project `test_*.py`
files cover board-specific requirements. The Raspberry Pi example's
[firmware test](../examples/projects/raspberry-pi-status-led/tests/test_firmware.py)
checks its actual GPIO choice and blink timing with a fake GPIO adapter.
Product `tests/test_*.py` files cover integration requirements and run when any
participating board is selected. A focused lane runs selected project suites and
their dependent product suites, along with the selected portable policy and
generation checks. It does not rerun the shared root unit suite or quality tools.
Use the full `tools.ci` command for changes to shared services and contracts.
`--project`, `--product` and `--tag` can be repeated to select their union;
`--exclude-tag` removes projects afterward. Tags live in each project's
`project.json`; registered product membership lives in `catalog/products.json`.
The [CI guide](../docs/workflow/CHECKS_AND_CI.md) explains how changed paths
select PR lanes, how to request a focused manual hosted run, and why main
pushes remain full.

Add a `unittest.TestCase` in a `test_*.py` file. Each island runs in a separate process
with the repository root as its working directory, so shared imports work and module
names cannot collide across boards. Use `__file__` to locate island files. Nested
test directories need `__init__.py` for unittest discovery. Tests must not depend on
hardware, network access or files on an engineer's desktop; native/physical checks
belong in their separately declared workflow.

| Change | Useful regression coverage |
| --- | --- |
| Policy rule | Valid case plus a mutation rejected with the intended reason |
| Manifest/contract | Strict parse, unknown/wrong fields, path escape and duplicate ID cases |
| Generator | Meaningful expected values, deterministic ordering, stale/missing/tampered output and invalid-input rejection |
| Discovery/runner | A new island appears automatically; a failing local test fails its gate |

Ruff checks the shared code/tests; strict Pyright checks shared tools. Project Python
suites execute automatically. New substantial shared services are also discovered by
the architecture test. See the [scripting standard](../docs/workflow/SCRIPTING_STANDARD.md).

Existing projects can use the [import workflow](../docs/workflow/IMPORT_WORKFLOW.md).
Temporary imported projects should exercise source and connectivity mutations in
their own local suites without adding run reports or imported source to the template.
