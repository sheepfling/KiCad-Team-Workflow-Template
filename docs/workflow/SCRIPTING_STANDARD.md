# Python scripting standard

This repository uses Python as a small engineering-policy toolchain, not as an
unstructured collection of file manipulation scripts.

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

1. Define serialized contracts in tools/hwrepo/models.py, including schema version,
   closed enums, identifiers, units and nullability.
2. Decode with read_model(path, Model), never json.loads() in application code. It
   rejects duplicate keys and non-finite values before Pydantic validates shape.
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
Run `python -B -m tools.hardware generate` for local exports; CI regenerates in a
temporary directory and tests deterministic output without requiring committed copies.

## Script layout

- tools/hwrepo/models.py — versioned serialized contracts and typed report/view
  records.
- tools/hwrepo/contracts.py — file-JSON boundary and portable repository paths.
- tools/hwrepo/product.py — cross-record product policy.
- tools/hwrepo/generation.py — deterministic typed projections.
- tools/hwrepo/repository.py — portability and discovery adapters.
- tools/hwrepo/documentation.py — typed Markdown layout and repository-documentation graph policy.
- tools/hwrepo/markdown.py — typed SnakeMD builders for workflow-created Markdown.
- tools/*.py — narrow CLI/KiCad adapters, invoked from the repository root as
  `python -m tools.<command>`. Direct execution (`python tools/<command>.py`) is
  unsupported because it changes Python's import root.
  New substantial policy belongs under
  hwrepo/, not in an argument-parsing script.

The `-m` module boundary is mandatory for every repository CLI. On a POSIX host
whose interpreter is named `python3`, `python3 -m tools.<command>` is equivalent;
the executable name may vary by host, but a script path may not replace the
module invocation. CI must call the central `tools.ci` module rather than
invoking a lower-level tool by file path.

## Tests and quality gates

Every contract change needs a valid model parse/round-trip test; rejected wrong
type, unknown field and unsupported-version tests; a semantic negative fixture for
every engineering rule; deterministic/stale-output tests for each generator; and a
direct-entry-point test proving a policy check cannot be bypassed.

Run `python -B -m tools.ci`; it invokes Markdown documentation policy, Ruff, Pyright
and behavior tests before reporting the portable policy result. `python -m tools.ci
--matrix`, `python -m tools.ci --kicad` and `python -m tools.ci --fault-probes`
are the corresponding GitHub pipeline modes. The pinned runtime and development set
includes Pydantic 2.13.5, SnakeMD 2.4.1, snakemd-stubs 2.4.1.0, Ruff 0.16.1 and
Pyright 1.1.411; hosted CI
installs those exact versions for the full Linux/macOS lanes. Linux also checks
Windows-targeted types; the Windows lane installs the runtime package and runs
focused portability smoke tests. Native KiCad remains a separate, pinned-toolchain lane.

Pydantic does not establish electrical correctness, source provenance, an approved
supplier record, physical fit or a human sign-off. It makes the software boundary
explicit so those checks cannot quietly operate on malformed data.
