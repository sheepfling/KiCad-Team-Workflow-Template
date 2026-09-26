# Python scripting standard

The installed tooling uses Python 3.11+ for typed engineering policy. Shared implementation
changes belong in [KiCad Tooling](https://github.com/sheepfling/KiCad-Tooling); this template keeps
project/product records and optional local tests. Follow [project test guidance](PROJECT_TESTS.md)
for board-owned Python and these boundary rules when extending shared tooling.

## Boundary rule

Raw JSON, YAML, CSV, XML, environment variables, command output and CLI arguments
exist only at adapters: hwrepo.contracts, KiCad/XML report readers, subprocess
wrappers and CLI entry points. An adapter parses once, validates immediately and
returns a named, strongly typed object. Core functions accept and return Pydantic
models, dataclasses, enums, scalar value objects, or explicitly typed collections
of those objects.

Any, object, dict[str, Any], unparameterized dict, and untyped lists are not allowed
in policy, generation, validation or business-rule code. A typed
Mapping[Identifier, PartRecord] is acceptable when a map is the natural
representation; a mapping whose values are unknown JSON is not. Do not pass a raw
document through multiple functions so each caller can rediscover its shape.

Pydantic records use strict mode, frozen models and extra=forbid. They reject
coercion and silently added fields. Fields whose JSON name is reserved by Python
use a typed Python name plus an explicit serialization alias.

## Model and serialization rules

1. Define serialized contracts in kicad_tooling/hwrepo/models.py, including schema version,
   closed enums, identifiers, units and nullability.
2. Decode files with read_model(path, Model), or network response text with
   parse_model(document, Model), never json.loads() in application code. Both
   reject duplicate keys and non-finite values before Pydantic validates shape.
3. Serialize only validated models via model_dump_json(by_alias=True) or typed
   output helpers. Generated JSON schemas come from the Pydantic model, not a
   second handwritten schema evaluator.
4. Keep structural validation in models; keep cross-record engineering rules in
   named validators operating on typed models. A model validator must not guess a
   pinout, unit, part, footprint, supplier fact or approval.
5. Use immutable tuples for repository-record sequences. If an index is useful,
   build Mapping[Identifier, Model] once at the service boundary; do not mutate a
   parsed list or a model dictionary in place.
6. Treat KiCad report/XML formats as third-party adapter formats. Convert the
   minimal fields used by policy into typed adapter records before applying rules.

Published schema policy: export JSON Schema only for durable input, configuration,
or release contracts that non-Python consumers may validate. Models are the tracked
authority. Schemas and generated JSON/CSV review projections are ignored outputs.
Run `kicad-team hardware generate` for local exports; CI regenerates in a
temporary directory and tests deterministic output without requiring committed copies.

## Installed entry points and source layout

Use the installed dispatcher from the project checkout:

```sh
kicad-team template list --format text
kicad-team verify --project <id>
kicad-team ci
```

Automation may use `python -I -B -m kicad_tooling.<module>`, for example
`python -I -B -m kicad_tooling.ci`. The dispatcher accepts hyphenated command names such as
`contract-coach`, while Python module names use underscores (`contract_coach`).
Use `-I` for installed-module automation so checkout files and ambient `PYTHONPATH` cannot replace
the pinned installation. Apply isolation to workflow bootstrap modules such as pip and venv too.
Do not execute a package's `.py` file directly; use the normally installed module entry point.
Pass `--root /absolute/project/path` when the current directory is not the project checkout.
MCP uses `kicad-team-mcp --root /absolute/project/path` and fixes that root at startup.

The tooling repository owns `kicad_tooling/hwrepo/models.py` for versioned records, `contracts.py`
for typed JSON and paths, and named policy/generation/validation services under
`kicad_tooling/hwrepo/`. Its top-level `kicad_tooling/*.py` files are narrow CLI adapters.
Substantial engineering policy belongs in a shared service, not argument parsing. Project
repositories consume those services through a reviewed tooling pin; they do not carry copies.

## Tests and quality gates

Every contract change needs a valid model parse/round-trip test; rejected wrong
type, unknown field and unsupported-version tests; a semantic negative fixture for
every engineering rule; deterministic/stale-output tests for each generator; and a
direct-entry-point test proving a policy check cannot be bypassed.

Run `kicad-team ci` in the project repository for live discovery, source/dependency policy,
fresh generation, Markdown checks and project/product suites. Its Markdown checks include the
local typed policy plus pinned `rumdl` and `mdrepo`. `kicad-team ci --matrix`,
`kicad-team ci --kicad` and `kicad-team ci --fault-probes` expose the corresponding project lanes.
Native KiCad remains a separate pinned-toolchain check.

Run shared implementation tests, CLI/MCP behavioral comparisons, Ruff and strict Pyright in the
tooling repository using its development setup. Dependency pins belong to that package;
`requirements-tooling.txt` selects the installed build and project-facing extras here.
A passing project gate is evidence for this project's scope, not a rerun of package regressions.

Pydantic does not establish electrical correctness, source provenance, an approved
supplier record, physical fit or a human sign-off. It makes the software boundary
explicit so those checks cannot quietly operate on malformed data.
