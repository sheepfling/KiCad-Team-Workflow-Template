# Template, tooling, and populated acceptance projects

The workflow uses three repositories with distinct ownership and update schedules:

| Repository                                                   | Durable content                                                                                           |
| ------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------- |
| This template                                                | Project layout, agent guidance, engineering workflow docs, starter catalogs and project-local contracts   |
| [KiCad Tooling](https://github.com/sheepfling/KiCad-Tooling) | Installable Python CLI/MCP services, typed models, schemas, shared checks and behavioral regression tests |
| Populated acceptance repository                              | Representative KiCad designs and end-to-end acceptance against a pinned tooling build                     |

A real project repository starts from this template and owns its KiCad source,
reviewed requirements, catalog identities, project tests, approvals and release records.
Installed tooling reads those records from the selected checkout. Its installation directory
is never the project root. CLI and MCP use the same installed services and selected project data.

The populated acceptance repository is a separate template-derived checkout under the owner's
account and may be private. It exercises real import, diagnosis, native validation, BOM/parts,
3D handoff, releases and CI selection. Small synthetic unit fixtures belong with tooling;
a team's project collection does not. Using GitHub's **Use this template** action creates an
independent repository. An ordinary fork of a public repository is public.

## Installed tooling cutover

This template no longer carries the shared Python package or root tooling regression suite. It keeps
engineering notes, project/product contracts, optional island tests, template records and thin
hosted workflow callers. Shared GitHub job definitions live in Tooling alongside Python.
`pyproject.toml` holds documentation-tool configuration; it does not make this checkout an
installable Python package.

Follow the [first-run setup](../../README.md#first-run-setup):

```sh
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-tooling.txt
kicad-team --version
kicad-team template list --format text
kicad-team ci --format text
```

Use the Windows activation instructions in that setup on Windows.
`requirements-tooling.txt` selects an exact public Git commit, including the `project`, `mcp`,
`charts` and `cad` extras. This is a source pin, not a PyPI release; no package publication is
needed. Native jobs install the same tooling build used to plan their checks.
A successful portable result leaves native and physical validation separate.

The template gate checks repository policy, documentation, fresh generated views and project/
product tests. Shared implementation regressions, CLI/MCP behavior comparisons and package lint/
type checks run in the tooling repository. Retain native and end-to-end acceptance receipts in
ignored `build/`, CI artifacts or the populated acceptance repository; do not add them to this
template.

## Shared GitHub workflows

The four files in `.github/workflows/` retain triggers, manual selection menus and immutable calls
to Tooling's reusable workflows. They contain no runner setup, package installation, verification
commands or artifact logic. Tooling owns those jobs and the Python services behind them; see the
[reusable CI contract](https://github.com/sheepfling/KiCad-Tooling/blob/main/docs/PROJECT_CI.md).

Every job checks out **this project's source** and installs this project's
`requirements-tooling.txt`. Results and failure logs stay in this repository's Actions run.
No secrets need to be passed to the public workflow. Private adopters must permit these public
reusable workflows in their Actions settings.

Review both pins when upgrading: each caller's `uses: ...@<commit>` selects GitHub orchestration,
while `requirements-tooling.txt` selects installed Python. An orchestration-only update can keep
a compatible Python pin. Update them through a project PR and rerun acceptance; the package can
later use an exact PyPI version without changing this arrangement.

GitHub can qualify the final check name with the caller job name. During migration, inspect the
new passing check and update branch protection plus `catalog/team-policy.json` together. Retain
the old required check until the new gate passes. Portable checks cover Linux/macOS and Windows
entry points; hosted native KiCad and simulator lanes run on Linux. Focus, tags and shards still
use the installed Python planner, and logs remain under ignored `build/ci-hosted/`.

## Develop tooling beside a project

For a coordinated tooling change, check out the public tooling repository beside this project
as `../KiCad-Tooling`, then activate this project's environment and install it editably:

```sh
python -m pip install -e '../KiCad-Tooling[project,mcp,charts,cad]'
kicad-team template list --root . --format text
kicad-team ci --format text
```

For Python automation, use `python -I -m kicad_tooling.<module>` with the active
environment's interpreter. Normal imports come from that installation. `--root` selects
project data; it never changes Python's import paths. Do not inject `PYTHONPATH`,
modify `sys.path`, or depend on the sibling checkout's location after installation.

The editable installation is local development state, not a replacement for the committed pin.
Run the tooling repository's own development checks there and the affected project/native workflows
here. Restore the reviewed requirements installation before testing the pinned acceptance path.
For agents, `kicad-team-mcp --root /absolute/path/to/project` binds the same installed build to
one checkout; see [MCP setup](MCP.md) for capabilities and engineering-review boundaries.

## Update an adopted repository

For a repository carrying the earlier in-tree implementation, make the cutover on a review branch:

1. Preserve `projects/`, `products/`, libraries, catalog identities, engineering notes and all
   project/product contracts and tests. Keep authored approvals and frozen release records intact.
2. Add the reviewed `requirements-tooling.txt` pin and install it in a new environment. Convert
   `python -m tools.<module>` calls to `kicad-team <hyphenated-command>` or
   `python -I -B -m kicad_tooling.<module>` in automation. Keep `--root` bound to project data.
3. Update hosted workflows and agent setup, then remove shared `tools/`, root implementation
   regression tests and template Python package metadata. Move any actual project-specific test
   into its owning island before removing an old shared test directory.
4. Run discovery, full portable policy, affected native workflows and CLI/MCP acceptance using the
   installed build. Inspect imports, BOMs, 3D exports and release restore evidence as applicable. A
   command's presence or a successful wheel install alone does not establish this acceptance.
5. Review source identity and results, then merge the project pin and template changes together.

Subsequent tooling updates change the exact pin through a pull request that runs project acceptance.
This lets private projects receive fixes without copying Python source or silently changing the
rules used for earlier evidence. Template contract versions, tooling versions and KiCad toolchain
pins remain distinct.

## Configuration and package versions

The template layout is the default. An optional declarative `kicad-tooling.toml` can relocate
catalogs, scaffold inputs, workflow guides and project-creation paths. Discovery can opt into
bounded nesting while retaining unique IDs and source ownership. CLI and MCP share that
configuration; see the tooling
[configuration guide](https://github.com/sheepfling/KiCad-Tooling/blob/main/docs/CONFIGURATION.md).
The default remains one island directly below `projects/`; tags and products group independent
boards.

Package versions come from Git tags through `setuptools-scm`; `kicad-team --version` reports the
installed metadata version. New KiCad major versions require an explicit compatibility declaration
and native acceptance before adoption. Package build checks and project acceptance do not publish
packages, approve hardware or establish team permissions.
