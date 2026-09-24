# Checks and CI

The same shared runner checks project islands locally and in hosted CI.
If a selected project fails, use the [diagnostic command](DIAGNOSTICS.md) to pair
portable, native and BOM findings with specific repair steps.

| Check scope | What runs |
| --- | --- |
| `python -B -m tools.ci` | Live discovery/registry, dependency/source hygiene, product policy, fresh generation, Markdown, Ruff, strict tool types, shared unit tests and every project/product Python suite |
| `python -B -m tools.ci --project <id>` | Selected project inputs, shared dependency policy, products declaring that project, fresh applicable views and its project/dependent-product Python suites |
| `python -B -m tools.ci --matrix` | One native lane per discovered manifest, using its catalogued toolchain |
| `python -B -m tools.ci --kicad --project <id> --output <new-path>` | Native checks for the selected board, after registry, dependency/source hygiene and product preflight |

Portable checks do not execute KiCad. A focused check does not replace the full gate
before review. Native checks do not replace Python suites or physical engineering tests.

## Daily commands

```sh
python -B -m tools.ci --project raspberry-pi-status-led
python -B -m tools.ci --tag status-led
python -B -m tools.ci --exclude-tag legacy
python -B -m tools.ci
python -B -m tools.ci --matrix
python -B -m tools.ci --kicad --project controller --output examples/projects/controller/build/review-001
python -B -m tools.hardware generate
python -B -m tools.template doctor
python -B -m tools.template doctor --native --toolchain kicad-10.0.5
python -B -m tools.template preflight
python -B -m tools.docs_policy
```

Repeated IDs/tags are OR selections; exclusions apply afterward. A selection matching
no projects fails. No selection means the full set. Custom project/product tests run
in separate Python processes; add `test_*.py` files without editing the workflow.
See [test extension](../../tests/README.md).

Native output directories and review snapshots are write-once. Use a fresh path each
attempt and close KiCad first. PCB projects receive ERC, DRC/parity, netlist identity
and schematic/PCB SVG checks. PCB-only projects receive DRC and a PCB SVG only; they
remain not for manufacture until an authoritative schematic makes full electrical
validation possible. Schematic projects receive ERC and schematic SVG; wiring and
harness views also receive their typed relationship coverage checks.
All native kinds protect declared source hashes.

## Adding and sharing projects

Create `projects/<id>/project.json` and its local source/contract files, or use
`tools.template new-project` or the [import command](IMPORT_WORKFLOW.md). Do not edit a list of CI lanes. `catalog/projects.json`
selects discovery roots and shared catalogs; each manifest owns its metadata.
Unregistered native files, duplicate IDs and misplaced project folders fail.

Each shared-library consumer declares the exact shared files it needs. The full gate
checks all consumers after a library change. Hosted native jobs likewise cover every
discovered project; changed-file optimization is not implemented.

## Hosted execution

Actions installs dependencies from `pyproject.toml`, runs the portable gate on
Windows/macOS/Linux, and runs native validation in each project's digest-pinned KiCad
image. The controller's native fault probes run only for its known reference path.
The template pins its direct runtime and development-tool dependencies in
`pyproject.toml`; each direct dependency selects its published compatible transitive
requirements. Update direct pins as a reviewed change and rerun the portable/native
acceptance lanes.
Dependabot opens bounded monthly Python and GitHub Actions update pull requests;
these receive the same review and complete acceptance workflow as other tool changes.
The final acceptance check requires the matrix, portable jobs, native jobs and a
standalone release/restore rehearsal to pass. The rehearsal commits a disposable
reference checkout, exports using pinned KiCad, prepares an engineering-review
manifest, packages it and verifies an actual restore. It does not approve hardware.

An initialized fork with no projects emits an empty matrix. Only that explicit
condition allows native/release jobs to be skipped; the final check still requires
portable policy success and states that no hardware was validated. Unknown project
selectors and broken discovery still fail.

CI uploads shared schema/library exports, product-local generated views, and native
review evidence, portable reports and the rehearsed package. Reports record the
observed source commit and file hashes. Dirty local reports remain useful for
development but cannot supply release evidence. Configure artifact retention and required branch checks during
[adoption](START_HERE.md); a configured workflow is not evidence of a hosted run.

## Replaying a native CI lane locally

The official pinned images do not include pip. `tools.native_deps` probes the image's
Python version and uses host pip to prepare compatible Linux x86 wheels from
`pyproject.toml` in an ignored directory. The image itself remains unchanged.
Install the repository's Python environment first, then use the image string from
`catalog/toolchains.json` for the selected project. On a macOS/Linux Docker host:

```sh
# Set KICAD_IMAGE to the exact image selected by the project's toolchain.
python -B -m tools.native_deps --image "$KICAD_IMAGE" --output build/policy-deps
docker run --rm --platform linux/amd64 --user "$(id -u):$(id -g)" --entrypoint sh \
  -e HOME=/tmp/kicad-template -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPATH=/work/build/policy-deps -v "$PWD:/work" -w /work "$KICAD_IMAGE" \
  -ec 'python3 -m tools.ci --kicad --project battery-board --output build/review-001'
```

Use a new dependency directory for a different image/runtime and a fresh evidence
directory for each native attempt. The native CI job uses this same setup. The
x86 image can run under Docker emulation on Apple Silicon; native Windows execution
of these shell examples is not provided. CI keeps dependency wheels out of review
artifacts. Its hosted job scheduling, permissions and upload remain separate from a
local container rehearsal.
