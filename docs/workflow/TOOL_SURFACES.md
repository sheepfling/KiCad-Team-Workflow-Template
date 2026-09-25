# CLI and MCP capability coverage

The CLI and [MCP adapter](MCP.md) use the same repository services, but their
public capabilities are not identical. The checked inventory records intentional
restrictions and catches unreviewed additions, removals and parameter-name changes:

```sh
python -B -m tools.surface --format text
python -B -m tools.surface --format json --require-live-mcp
```

MCP clients call `inspect_tool_surfaces()` or read `kicad://docs/tool-surfaces`.
Inspection only reads source, the catalog and registered tool metadata. It never
runs a registered tool, starts KiCad or creates a receipt.

## Read the result

The durable source is [catalog/tool-surfaces.json](../../catalog/tool-surfaces.json).
Each capability lists its CLI endpoints, MCP tools, a reason and any known gaps:

| Alignment | Meaning |
| --- | --- |
| `aligned` | Both surfaces cover the capability; no known semantic parameter gap is recorded. |
| `partial` | Both expose related work, with explicit differences listed in `gaps`. |
| `cli_only` | A CLI capability has no dedicated MCP counterpart. |
| `mcp_only` | An MCP capability has no dedicated repository CLI counterpart. |

`PASS` means every discovered endpoint is tracked and the checked declarations
match the catalog. It does **not** mean every capability is aligned. Read
`capabilities[].alignment`, `reason` and `gaps` to see which surface leads. This
report never grants build, purchasing, electrical or release authority.

The inventory describes the full MCP surface with every startup capability
flag enabled. Your connected server can expose fewer tools because its
[permissions](MCP.md#choose-the-enabled-capabilities) are narrower. Fixed checkout roots,
structured MCP output and CLI text/JSON formatting are ordinary adapter
conventions; a capability's gaps call out meaningful workflow restrictions such
as absent commands, narrower selection, fixed output locations or no arbitrary
executable override.

Typical differences include CLI-only adoption and upgrade operations, repository
metrics and hosted-governance checks; MCP-only bounded artifact/source readers
and reviewed text edits; and partial native, release, 3D and purchasing workflows.
For purchasing, `prepare_parts` shares the CLI parts service and
`save_parts_preferences` adds a hash-checked edit path. Both keep purchase and
build authorization false. The catalog gives the current exact parameter gaps.

## What is checked

The scanner reads first-party Python modules under `tools/`, including nested
modules, and discovers entry points from `main` functions, `__main__` modules and
standard main guards. It records argparse option names, positional command
choices, subparser names and aliases. Unsupported dynamic names or command
choices fail discovery rather than disappear from the inventory.

MCP registrations and parameter names are scanned without importing the SDK.
When the optional pinned MCP dependency is installed, the report also constructs
the running adapter with all capabilities enabled and compares its **actual
registered** tool names and input-parameter names with the source declarations.
No tool is called. `mcp_verification=LIVE` records that comparison; `STATIC_ONLY`
means the SDK is absent. Use `--require-live-mcp` in development or CI to reject
that fallback. `UNAVAILABLE` is a failure to perform required/live verification,
not proof that the surfaces match.

The tests run the real checkout catalog against the full live registration and
exercise new CLI modules, subcommands and switches, MCP names and parameters,
stale mappings, invalid classifications and the SDK-free path. They run in the
normal unit-test gate, so a new public declaration cannot pass unnoticed.

This is a declaration and coverage check. It does not infer behavior equality,
compare argument defaults/types or nested input schemas, or prove that two
implementations produce equivalent results. Argparse options are recorded per
module, not per subcommand. Keep service and protocol tests for behavior and
review semantic/default/permission changes even when the inventory passes.

## Change either surface

1. Implement the service and desired CLI or MCP adapter; keep their behavioral
   tests with the change.
2. Run `tools.surface`. For each reported new or changed declaration, review the
   other surface before updating the pinned snapshot in the catalog.
3. Update the capability mapping. Use `partial` with a concrete gap when one
   surface leads; use `cli_only` or `mcp_only` with an intentional reason when
   there is no counterpart. Do not label a restricted workflow `aligned` merely
   to clear a drift error.
4. Rerun with `--require-live-mcp`, then the normal full
   [checks](CHECKS_AND_CI.md). Keep the catalog and implementation in the same
   change so the next contributor can tell intentional differences from drift.

The report does not rewrite its catalog. Snapshot changes require a reviewed
source edit; generated reports can remain local or in CI artifacts.
