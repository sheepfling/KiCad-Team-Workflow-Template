# CLI and MCP workflow parity

Core board workflows must be available through both the CLI and the [MCP adapter](MCP.md).
They use shared services and preserve the same validation, quantities, source changes,
artifacts and failure states. Paths, presentation and startup permissions are adapter
constraints. Those constraints do not count as missing workflow functionality.

```sh
kicad-team surface --format text
kicad-team surface --format json --require-live-mcp
kicad-team ci
```

MCP clients call `inspect_tool_surfaces()` or read `kicad://docs/tool-surfaces`.
Inspection reads the installed package declarations, packaged catalog and tool metadata.
It does not execute the referenced tests or start KiCad. Tooling repository CI runs the behavioral
comparisons; the template project gate validates this checkout’s policy and island tests.

## Core workflows and exceptions

The versioned
[packaged catalog](https://github.com/sheepfling/KiCad-Tooling/blob/main/kicad_tooling/tool-surfaces.json)
separates three scopes:

| Scope            | Acceptance requirement                                                                                                        |
| ---------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| `core`           | Both surfaces, no recorded functional gaps, and existing behavioral test references                                           |
| `administration` | Explicit reason for an operator/CI-only workflow, such as repository adoption, production governance or infrastructure probes |
| `adapter`        | Explicit reason for a transport or editor convenience, such as bounded file browsing or starting the MCP server               |

Core scope covers discovery, setup diagnosis, scaffolding/import, repair diagnosis,
portable and grouped native checks, contract inspection, model draft/population and
3D export, parts/preferences, supplier snapshots, impact planning, scoped review
views, native fabrication export, engineering-review preparation and package recovery.
Newly integrated core scope also includes foreign-board conversion, electrical
setup/input capture and analysis, saved electrical chart exports, reviewed part
selection, paired and exact sourced CAD imports, pinned STEP alignment review, and
explicit supplier handoff. Downloads and submissions have separate MCP startup
capabilities; these authority constraints are recorded without hiding functional gaps.
The CI and MCP scope surfaces share project/tag selection, partial shard semantics
and bounded project-test workers. `kicad-team ci-hosted` handles Actions orchestration
as an operator-only administrative surface; it does not create an MCP bypass for
Docker, release rehearsal or GitHub job scheduling. The required core IDs are
pinned in the policy code. Deleting a row or calling it
administrative cannot waive that requirement.

An administrative exception records the actual operation left to an operator.
For example, engineering-review preparation supports multiple boards and product
variants through both interfaces; prototype/production release classes retain
separate operator governance. Neither interface invents approval or authorizes a
purchase by producing a review file.

Each catalog row records:

- `alignment`: `aligned`, `partial`, `cli_only` or `mcp_only`, describing functionality.
- `gaps`: missing functional behavior. Any core gap fails the parity policy even
  when documented.
- `constraints`: permissions, fixed paths, output naming, runner configuration or
  presentation differences that preserve the supported workflow.
- `exception`: why an administrative or adapter operation has different coverage.
- `parity_tests`: exact test methods exercising the core behavior.

MCP describes the full available surface with all startup flags enabled. A
connected server can expose fewer tools according to its
[enabled capabilities](MCP.md#choose-the-enabled-capabilities). That is an explicit
permission boundary. A caller cannot widen it through tool arguments.

## Read the checks honestly

The report uses schema version `2` and separates its outcomes:

| Field                   | What a pass establishes                                                                                                                    |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `coverage_status`       | Discovered command/tool names and parameter names match the reviewed catalog                                                               |
| `parity_status`         | Required core rows have both interfaces, no functional gaps/exceptions, and recorded behavioral test references                            |
| `status`                | Both policy checks passed                                                                                                                  |
| `mcp_verification`      | `LIVE` compares actual full-server registration; `STATIC_ONLY` means the optional SDK was absent; `UNAVAILABLE` means live checking failed |
| `behavior_verification` | Always `NOT_RUN` in this inspection; tooling repository CI supplies behavioral test results                                                |

A source-checkout inspection also resolves referenced test methods in the tooling repository.
Installed wheels exclude those test sources and report them as `NOT_AVAILABLE` in the notes;
they do not resolve test references against the consuming project. In both modes,
`behavior_verification` remains `NOT_RUN`. Run tooling CI for behavioral evidence.

A catalog pass is a policy check, not a test execution result. Referenced tests
compare actual CLI JSON with real MCP protocol responses, including failed results,
source changes, quantities and exported files. Native unit fixtures are explicitly
synthetic. Real KiCad rehearsal receipts remain a separate integration check and
do not establish electrical or manufacturing approval.

The declaration scanner discovers Python entry points, argparse option names,
positional command choices, subcommands and aliases. MCP tool names and parameters
are scanned without the optional SDK, then compared to actual registration when
available. Unsupported dynamic declarations fail discovery. `--require-live-mcp`
rejects the SDK-free fallback.

Declaration checks do not infer behavior from names or compare every argument
type/default and nested input schema. Argparse options are recorded per module,
not per subcommand. Behavioral tests and review remain necessary when semantics,
permissions or schemas change without a declaration-name change.

## Change a workflow

1. Work in the tooling repository; change the shared service and both adapters for core
   functionality. Keep any runner, permission or output-path constraint explicit.
2. Add a CLI/MCP behavioral comparison for the change, including relevant failure
   states and written outputs; normalize only incidental receipt paths and timing.
3. Update reviewed interface snapshots and mappings in the catalog. Record a real
   gap honestly: the core parity gate should fail until it is resolved.
4. Run `kicad-team surface --require-live-mcp` and the tooling repository’s full development gate.
   Keep tests, catalog and implementation together. Update the project tooling pin through review
   and run project [acceptance checks](CHECKS_AND_CI.md), including affected native workflows.

The report never rewrites its catalog. Store generated reports in ignored `build/`
or CI artifacts; keep the reviewed policy and tests in source control.
