# Repository structure and ownership

Organize by independently maintained deliverable. A project is a repeatable folder
containing its source, manifest, documentation and tests. The project kind is metadata
in `project.json`; it does not add another directory level.

| Location                 | Owner and purpose                      | Tracked content                                                                              |
| ------------------------ | -------------------------------------- | -------------------------------------------------------------------------------------------- |
| `projects/<id>/`         | Board or deliverable owner             | Native design, local libraries, manifest, docs, tests, optional firmware and release records |
| `products/<id>/`         | System integrator                      | `product.json`, integration docs/tests and release records linking project IDs               |
| `docs/workflow/`         | Scaffold maintainers                   | Durable reusable workflow, policy and adoption guidance                                      |
| `docs/team/`             | Adopting team                          | Durable organization-wide decisions and process                                              |
| `catalog/`               | Library, electrical and process owners | Shared identities, approved toolchains, product index and project discovery roots            |
| `libraries/<id>/`        | Library owners                         | Shared symbols, footprints, models and provenance/licensing                                  |
| `templates/`             | Process maintainers                    | Copyable manifests, test contracts, handoff and governance records                           |
| `examples/`              | Template maintainers                   | Small training designs with their source, contracts and engineering notes                    |
| `.github/`               | Repository maintainers                 | Shared workflows and review forms                                                            |
| `generated/`, `schemas/` | Tooling                                | Only their guidance files; derived shared exports are ignored                                |
| Any `build/`             | The generating run                     | Nothing tracked; local generated views, native exports and test evidence                     |

The installed [tooling package](https://github.com/sheepfling/KiCad-Tooling) owns shared
runners, typed models and implementation regression tests. `requirements-tooling.txt` pins
that package; this template is not itself a Python package.

## Documentation ownership

The [documentation map](../README.md) is the single entry point for repository-wide
documentation. Scaffold guidance lives in `docs/workflow/`, which keeps upstream
template changes separate from adopter content. Organization-wide documentation
lives in `docs/team/`. Add team subfolders only when they contain real documents,
and link those pages from `docs/team/README.md`.

Keep board documentation in `projects/<id>/docs/` and product integration material
in `products/<id>/docs/`. This repeatable island pattern lets a board remain useful
on its own and prevents the repository-wide docs tree from becoming a second project
catalog. Dated run reports, trial results and investigation logs belong in issues,
pull requests, CI artifacts or ignored `build/` directories. Approved release
evidence follows the [release-storage policy](RELEASE_STORAGE.md).

## Inside a project

```text
projects/battery-board/
  README.md
  project.json
  kicad/battery-board.kicad_pro
  kicad/battery-board.kicad_sch
  kicad/battery-board.kicad_pcb
  docs/
  tests/contract.json
  tests/test_*.py
  firmware/                 # when relevant
  releases/                 # when a release exists
  build/                    # generated when needed
```

Only PCB projects require `.kicad_pcb`. Other [project kinds](PROJECT_KINDS.md)
use the same folder pattern. Add optional folders when needed, not as empty ceremony.
Local library tables sit beside the KiCad project; board-local assets belong there too.

`project.json` owns project identity, kind, development/production status, the selected
toolchain, source inventory, reusable dependency IDs and the test-contract path.
Its `project`, `source_roots`, `required_inputs`, `checks`, `mechanical_handoff` and
`governance_record` paths are relative to its own directory. `shared_source_roots`
and `shared_inputs` are explicitly repository-relative and must match registered
library IDs. Manifest paths reject absolute paths, parent traversal and symlinks.
KiCad library tables may use `${KIPRJMOD}/../` to reach an inventoried shared
library inside this repository; see the [library policy](LIBRARIES.md).

`tests/contract.json` owns independent expected nets/components or view traceability.
The native validator compares the actual design against it. Optional `test_*.py` files
add board-specific software or policy checks. Design notes and bring-up instructions
belong in `docs/`; governance evidence can live in `releases/governance.json`.

## Discovery and dependencies

`catalog/projects.json` contains shared catalog locations and enabled `project_roots`.
It does not duplicate project records. The runner discovers `*/project.json` directly
under each enabled root, validates directory/ID agreement and rejects duplicate IDs.
A forgotten native design without a manifest also fails discovery. Each island README
is automatically a documentation root, so adding a board does not require a central
documentation-link edit; its other Markdown pages still need links from that README.

Use `projects` for adopted work. `examples/projects` can remain enabled for rehearsal;
disable it in the live discovery settings when the examples should no longer create
native CI lanes. Keep the examples as explicit training and acceptance inputs.

A manifest chooses one toolchain ID; exact version and image come from the shared
catalog. Shared libraries are explicit dependencies. Copying an island alone does
not copy its shared dependencies or the tooling. Before distributing a board outside
this repository, include or pin those inputs and preserve their provenance.

## Products and parallel work

A battery board and PWM board do not need a product record to stand alone. Add one
when assembly membership, wiring, variants or cross-board requirements need an owner.
Keep that product's `product.json`, docs and tests in one folder and register it in
`catalog/products.json`. Product cross-references use repository-relative paths and
stable project IDs. Product directories may also contain test and release JSON files.

Project tests verify board-specific requirements; product tests verify integration.
The full project gate runs both. Shared tooling regressions run in the tooling repository.
See [project tests](PROJECT_TESTS.md). A selected-project
check includes that board and products whose index lists its ID. Each custom suite
runs in a separate process, so identical test module names in two boards do not collide.

Two engineers can work on different islands on separate branches. Changes to a shared
library require checking every declared consumer; the PR impact planner selects
those consumers. Main pushes and default manual CI run the full gate across all
projects; manual dispatch can select a focused project, product or tag.
Coordinate edits to the same native schematic or board through the
[project workflow](PROJECT_WORKFLOW.md). A shared repository does not provide a CAD lock.
