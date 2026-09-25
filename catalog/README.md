# Shared repository catalogs

`projects.json` configures shared catalog locations and enabled discovery roots.
Projects themselves are discovered from `projects/*/project.json` and, when enabled,
`examples/projects/*/project.json`. Adding a board needs no central record edit.

`products.json` indexes optional `products/<id>/product.json` records and their
project dependencies. `parts.json`, `interfaces.json` and `libraries.json` own shared
identities; `toolchains.json` pins tool versions/images; `release-policies.json` owns
release assurance floors. `team-policy.json` configures review separation and exact
required status checks. Do not store generated BOMs here.

The initial settings enable the reference examples. Before adding real work, run
`tools.template init --project-id my-hardware` to initialize empty live catalogs.
Keep `examples/` for regression tests. `examples/catalog/`
contains independent reference catalog inputs used by those tests.

[tool-surfaces.json](tool-surfaces.json) tracks public CLI/MCP declarations and
intentional capability gaps. Follow the [surface inventory guide](../docs/workflow/TOOL_SURFACES.md)
when either interface changes; the unit-test gate rejects untracked drift.
