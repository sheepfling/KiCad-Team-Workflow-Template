# Connect an agent through MCP

The optional local MCP server lets an agent discover boards, inspect prerequisites,
read workflow guidance and preview an import through named tools. It uses the same
repository services as the command-line tools. Agents with shell access can still
use those CLIs directly; the MCP adapter provides a smaller, discoverable interface.

## Install and connect

Use a trusted checkout and the [Python environment setup](../../README.md#first-run-setup).
From that checkout, install the optional dependency:

```sh
python -m pip install -e '.[mcp]'
```

Install `.[dev]` instead when enabling checks or developing the adapter; it includes
the pinned MCP SDK and the repository's quality tools. The base installation keeps
MCP optional.

Configure the client to launch the checkout's virtual-environment interpreter.
A client that accepts an `mcpServers` configuration can use this example after
replacing both absolute paths:

```json
{
  "mcpServers": {
    "kicad-workflow": {
      "command": "/absolute/path/to/checkout/.venv/bin/python",
      "args": [
        "-B", "-m", "tools.mcp",
        "--root", "/absolute/path/to/checkout"
      ]
    }
  }
}
```

On Windows, use the absolute `.venv\Scripts\python.exe` path and escape each
backslash in JSON. The editable installation makes `tools.mcp` importable without
setting the client's working directory. Keep the interpreter and `--root` pointed
at the same checkout, especially when using several worktrees.

The transport is local stdio: the client starts the process and communicates over
its input and output streams. There is no HTTP listener or hosted account to set
up. Start a separate server configuration for each checkout. The repository root,
import roots and enabled capabilities are fixed at startup; a tool call cannot
switch to another checkout or supply an arbitrary shell command, executable or
output directory.

## Confirm the connection

1. Reconnect the client and list the server's tools. The default set is
   `list_projects`, `get_project`, `doctor`, `read_document` and `preview_import`.
2. Call `list_projects` to identify actual project IDs, registered products,
   tags and toolchains. Inspect each project's status and assurance profile:
   `training_fixture` examples are rehearsals, while adopted work lives under
   `projects/`. An initialized fork may have no live projects yet.
3. Call `doctor` with no arguments for workstation prerequisites. Then select an
   ID returned by discovery and call `get_project` and `doctor` with that
   `project_id`. Set `native` to `true` to inspect the project's native runner.
4. Read `first-board` or `diagnostics` through `read_document` for the next step.

Discovery's `INPUTS_PRESENT` state describes file presence. It does not establish
that a board passes checks. A successful doctor result describes prerequisites;
it does not establish electrical correctness or release approval.

## Available tools

| Tool | Arguments | Purpose |
| --- | --- | --- |
| `list_projects` | None | Return the typed project, product, tag and toolchain inventory. |
| `get_project` | `project_id` | Inspect one registered project and its declared configuration. |
| `doctor` | Optional `project_id`; `native` defaults to `false` | Inspect prerequisites without running project tests. |
| `read_document` | `name` from the document list below | Read repository workflow guidance. |
| `preview_import` | `source`, `project_id`, `toolchain_id` | Preview copied files, source hashes and exclusions without creating a project. |
| `check_project` | `project_id`; `depth` is `portable` or `native`; `runner` is `auto`, `local` or `container` | Available with `--allow-checks`; run the selected verification lane and retain a receipt. Defaults are `portable` and `auto`. |
| `new_project` | `project_id`, `kind`, `toolchain_id` | Available with `--allow-writes`; create an incomplete development scaffold. |
| `import_project` | `source`, `project_id`, `toolchain_id` | Available with `--allow-writes`; copy a reviewed source project into a new island. |

Discover IDs before supplying them. Project kinds are `pcb`, `pcb_only`,
`schematic`, `system_wiring` and `harness_interface`; see [project kinds](PROJECT_KINDS.md).
The write tools retain the existing scaffold/import validation and refuse an
existing destination. They do not edit CAD designs or create electrical test
expectations. Complete the actual source and independently reviewed contract
before expecting the new project to pass.

The document names are `start-here`, `first-board`, `diagnostics`,
`import-workflow`, `contributor-guide`, `checks-and-ci` and `mcp`. Each is also
available as a resource at `kicad://docs/{name}`, for example
`kicad://docs/first-board`. This is a fixed list of workflow documents, not a
reader for arbitrary files.

## Enable checks and project creation

Add `--allow-checks` to the server's startup `args` only for a checkout whose code
you trust. `check_project` executes repository project/product tests and writes a
fresh ignored `build/diagnostics/` receipt using [tools.verify](CHECKS_AND_CI.md).
It is an execution-capable tool, not a read-only inspection. Native depth also
runs the exact selected KiCad CLI or the catalogued Docker image. `auto` prefers
an exact local CLI and otherwise selects the container; native checks may download
container images and Python dependencies. Close KiCad before a native run. Use the returned `run_directory` to find complete reports and logs.

Add `--allow-writes` to expose `new_project` and `import_project`. This flag is
independent of `--allow-checks`: enabling one does not enable the other. Writes
stay within the configured checkout. The server does not expose adoption,
release preparation, approval, publishing or arbitrary source editing.

## Preview and import existing designs

`source` selects a saved `.kicad_pro` file. By default it must be inside the
configured checkout. Relative source paths start at that checkout, not the client's
working directory. Linked paths and parent traversal are rejected. The importer
also inventories the source file's directory and its eligible sibling files.
To read an external design, add its parent directory as an
absolute startup argument:

```text
--import-root /absolute/path/to/legacy-designs
```

Repeat `--import-root` for additional source directories. These roots permit
source reads; imported output still belongs under the configured checkout's
`projects/` directory. Reconnect the client after changing startup arguments.
Do not use a whole home directory as an import root when a design folder suffices.

Call `preview_import` first and review every exclusion and source hash. Repair
missing dependencies and nonportable paths in the original design, then rerun the
preview. With `--allow-writes`, call `import_project` for the accepted source and
inspect the resulting island and `docs/import.json`. Follow the
[import workflow](IMPORT_WORKFLOW.md) for source completeness and electrical review.

## Troubleshoot the connection

- If the client cannot launch the server, check the absolute interpreter path and
  install `.[mcp]` into that interpreter's environment. Run
  `python -B -m tools.mcp --help` there to check the installed entry point.
- If projects do not match the intended assignment, inspect `--root` and the
  selected checkout's branch, then reconnect. Do not infer live board IDs from
  the example names in documentation.
- If `check_project` or the write tools are absent, inspect the startup flags.
  Capability flags control both discovery and availability.
- If an import source is outside the permitted roots, add its specific directory
  with `--import-root` and reconnect before previewing it again.
- For a failed check, preserve its receipt and follow the
  [diagnostic guide](DIAGNOSTICS.md). Repair the authoritative source; a passing
  MCP result has the same scope and limits as the corresponding CLI result.
