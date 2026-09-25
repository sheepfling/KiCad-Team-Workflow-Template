# Template, tooling, and populated acceptance projects

The KiCad workflow is being separated into three repositories with different
owners and update schedules:

| Repository                                                   | Durable content                                                                              |
| ------------------------------------------------------------ | -------------------------------------------------------------------------------------------- |
| This template                                                | Project layout, agent guidance, workflow docs, starter catalogs, and project-local contracts |
| [KiCad Tooling](https://github.com/sheepfling/KiCad-Tooling) | Installable Python CLI/MCP services, schemas, checks, and package releases                   |
| Populated acceptance repository                              | Representative KiCad designs and end-to-end checks against a pinned tooling build            |

A real project repository starts from this template and owns its KiCad source,
reviewed requirements, catalog identities, project tests, approvals, and release
records. Tooling reads those records from the project checkout. It must not use
its own installation directory as the project root.

The populated acceptance repository is a separate template-derived checkout
under the owner's account. It can be private. It holds the larger collection of
representative boards used to exercise import, triage, diagnosis, native checks,
BOM and parts workflows, 3D handoff, releases, CLI/MCP parity, and CI selection.
Small synthetic unit fixtures belong with tooling; the project universe does not.
Using GitHub's **Use this template** action creates an independent repository.
An ordinary fork of a public repository is public.

## Current migration state

The tooling repository has a first installable package and its own CLI/MCP
declaration inventory. The installed wheel has passed inventory, surface, and
portable verification checks against this template from another directory.
This template still carries `tools/` and the original root regression tests.
Its CI and documented commands continue to use that in-tree implementation
until the remaining package, native runner, regression, and hosted acceptance
checks pass. The tooling package is not on PyPI and no project should rely on
an unpublished package name yet.

For a local trial from this template checkout, install the sibling tooling
checkout in a disposable virtual environment, then run the installed command:

```sh
python3.11 -m venv build/tooling-trial/venv
build/tooling-trial/venv/bin/python -m pip install -e ../KiCad-Tooling
build/tooling-trial/venv/bin/kicad-team template list --format text
build/tooling-trial/venv/bin/kicad-team verify --project controller --format text
```

Run those commands from the project root or pass `--root` explicitly. The trial
environment is local state and is not a project dependency pin. Keep using
the [current first-run setup](../../README.md#first-run-setup) for the live gate.

## Cutover gate

Before removing the in-tree Python package, move its behavioral regression
suite to tooling, have the native container install that same package, and run
the installed CLI and MCP against the populated acceptance repository. The
template CI can then install a pinned tooling release and keep only project
checks plus thin hosted orchestration. Update all agent and onboarding commands
in the same cutover, then remove the in-tree Python implementation and its
package metadata. Preserve the `catalog/` and project-owned records here.

Version the tooling release separately from the template contract. Once the
package is published, update a project's exact tooling pin through a pull
request that runs its focused and full acceptance lanes. This lets private
project repositories receive fixes without copying Python source or silently
changing the rules used for an earlier check.
