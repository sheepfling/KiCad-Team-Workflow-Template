# Connect an agent through MCP

The optional local MCP server carries a board through discovery, import, diagnosis,
reviewed source repair, checks, exports and an engineering review package. It calls
the same repository services as the command-line tools and returns their typed
reports. Start with the result's status, findings and next actions; a completed MCP
call can contain a failing engineering or environment result.

## Install and connect

Use a trusted checkout and the [Python environment setup](../../README.md#first-run-setup).
From that checkout, install the optional dependency:

```sh
python -m pip install -e '.[mcp]'
```

Install `.[dev]` when enabling checks or developing the adapter; it includes the
pinned MCP SDK and repository quality tools. The base installation keeps MCP
optional. Clients with shell access can also use the CLIs directly.

Configure the client to launch the checkout's virtual-environment interpreter.
For a client accepting `mcpServers`, replace both absolute paths in this example:

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

Native container work also needs `docker` on the server process's `PATH` and a
running Docker service. Desktop clients may inherit a different environment from
your terminal. Configure the client's launch environment to include the actual
Docker executable directory when necessary, then reconnect and rerun `doctor`.
On a standard macOS Docker Desktop installation, that directory may be
`/Applications/Docker.app/Contents/Resources/bin`; verify it on the host.
For a linked Git worktree, native verification and release/export runners also
mount its shared Git metadata read-only, preserving the selected worktree's commit
and index. Docker must be able to read both the worktree and that metadata directory.

The transport is local stdio. There is no HTTP listener or hosted account to set
up. Start a separate configuration for each checkout. The repository root, import
roots and enabled capabilities are fixed at startup; reconnect after changing them.

## Choose the enabled capabilities

Add the relevant flags to the startup `args` array. Each flag enables a distinct
operation; enabling project creation does not enable edits to an existing design.

| Startup capability | Tools enabled | Files or execution affected |
| --- | --- | --- |
| Default | Discovery, guidance, source/artifact reads, import scanning and preview, edit preview, saved contract inspection, rescue and import diagnosis, release/package verification | Reads bounded repository data. Rescue and import diagnosis create ignored diagnostic receipts. Package verification temporarily restores the archive. |
| `--allow-writes` | `new_project`, `import_project` | Creates a new project island; refuses an existing destination. |
| `--allow-edits` | `apply_project_edit` | Replaces one explicitly selected text occurrence in an allowed existing project source file after a matching SHA-256 check. |
| `--allow-checks` | `check_project`, `diagnose_project`, `capture_contract`, `check_scope` | Executes repository checks and creates ignored receipts. Native work also runs KiCad or Docker. |
| `--allow-exports` | `generate_views`, `package_release`, `restore_package` | Creates generated review views and new package/restore outputs in the checkout's ignored build area. |
| Both `--allow-checks` and `--allow-exports` | `export_project`, `prepare_review` | Executes checks/native tooling and creates fresh exports or an engineering review candidate. |

Checks execute trusted repository code, including project and product tests.
Native work may download the pinned container image and Python dependencies.
The server provides fixed operations and output locations; a tool call cannot
choose another checkout or an arbitrary shell command or executable.

The server does not commit Git changes, sign approvals, create source tags, publish
packages or authorize manufacture. Use normal Git for reviewed source commits and
the team's release process for approvals and retained storage.

## Discover the board and its guidance

1. List the client's discovered tools to confirm that the expected capability
   flags took effect.
2. Call `list_projects` to find actual project, product, tag and toolchain IDs.
   Inspect status and assurance profile. `training_fixture` examples are
   rehearsals; an initialized fork may have no live projects yet.
3. Call `get_project` with a discovered `project_id` to inspect its manifest and
   independent test contract. Call `doctor` for local prerequisites, then request
   native readiness for the selected board before native work.
4. Read `first-board`, `diagnostics` or `import-workflow` through `read_document`.

Discovery's `INPUTS_PRESENT` state describes file presence. It does not establish
that a board passes checks. Doctor describes prerequisites, and an import preview
describes eligible source files; neither establishes electrical correctness.

| Tool | Arguments and use |
| --- | --- |
| `list_projects` | No arguments. List project, product, tag and toolchain inventory. |
| `get_project` | `project_id`. Return the selected inventory row, manifest and test contract. |
| `doctor` | Optional `project_id`, `toolchain_id` and `runner`; `native` defaults to `false`. Inspect setup and native runner readiness. |
| `read_document` | `name`. Read a named workflow guide. |
| `new_project` | `project_id`, `kind`, `toolchain_id`. Create an incomplete development scaffold with `--allow-writes`. |

Project kinds are `pcb`, `pcb_only`, `schematic`, `system_wiring` and
`harness_interface`; see [project kinds](PROJECT_KINDS.md). A scaffold needs actual
CAD source and independently reviewed expectations before its checks can pass.

Workflow documents are also resources at `kicad://docs/{name}`, for example
`kicad://docs/first-board`. Available names are `start-here`, `first-board`,
`diagnostics`, `import-workflow`, `contributor-guide`, `checks-and-ci`, `mcp`,
`bom-policy`, `release-readiness`, `release-storage`, `project-kinds`, `libraries`,
`authority-model` and `assurance-profiles`.

## Scan, preview and import existing designs

| Tool | Arguments and use |
| --- | --- |
| `scan_imports` | `source_directory`, `toolchain_id`. Inventory a directory of candidate designs without copying them. |
| `preview_import` | `source`, `project_id`, `toolchain_id`. Preview one saved `.kicad_pro` file, its hashes and exclusions. |
| `diagnose_import` | `source`, `project_id`, `toolchain_id`. Turn the import preview into a repair queue and keep an ignored diagnostic receipt. |
| `import_project` | `source`, `project_id`, `toolchain_id`. Copy the reviewed source into a new project with `--allow-writes`. |

Import paths start at the configured checkout. Absolute import paths can also name
an explicitly enabled external source directory; add its parent at startup:

```text
--import-root /absolute/path/to/legacy-designs
```

Repeat the flag for additional directories. These roots permit import reads; copied
output still belongs under the configured checkout's `projects/` directory. Use a
design folder as the root rather than the whole home directory. Linked paths and
parent traversal are rejected. The importer inventories eligible siblings in the
selected source file's directory as well as the `.kicad_pro` itself.

Review every suggested project ID, exclusion and source hash. Repair missing
sheets and nonportable paths in the original design, then rerun the preview.
Import one accepted design at a time and inspect the new island's `docs/import.json`.
An import preserves source; it does not invent electrical requirements or approve
the copied design. See the [import workflow](IMPORT_WORKFLOW.md).

## Inspect evidence and repair source

Use `list_artifacts` to find retained outputs and `read_artifact` to read their
metadata or bounded text.

| Tool | Arguments and use |
| --- | --- |
| `list_artifacts` | `directory` defaults to `build`; `offset` to `0`, `limit` to `100`. List one directory page. |
| `read_artifact` | `path`; `offset` defaults to `0`, `limit` to `20000`. Read an artifact chunk or metadata. |
| `read_project_file` | `project_id`, `path`; the same text `offset` and `limit` defaults. Read allowed authored source. |
| `preview_project_edit` | `project_id`, `path`, `expected_sha256`, `old_text`, `new_text`. Preview one exact replacement. |
| `apply_project_edit` | The same arguments as the reviewed preview. Apply with `--allow-edits`. |

Artifact paths are relative to the checkout and limited
to managed `build/` areas, including a selected island's `build/`. Restored checkouts
under `build/restores/` are excluded from artifact browsing. Listings cover one
directory level; use pagination and select a returned subdirectory to explore it.

Use `read_project_file` for the selected board's authored source. Its `path`, and
the edit tools' `path`, are relative to the project island: for example,
`kicad/board.kicad_sch`, `project.json` or `tests/contract.json`. Source reads include
supported KiCad text files, library tables, the manifest, contract, island README
and Markdown under `docs/`. They do not read arbitrary desktop files.

Reads return a SHA-256 digest and at most 20,000 characters of supported UTF-8
content per request. Binary or unsupported artifact types return metadata. Use
`offset` and `limit` to page through text and check whether more remains before
treating it as complete. The returned path is checkout-relative, so preserve the
original island-relative path when making a subsequent source edit.

`preview_project_edit` takes `project_id`, `path`, `expected_sha256`, `old_text` and
`new_text`. Supply the digest from the source read and an exact, uniquely occurring
piece of the current text. The preview produces a diff without writing. Review the
diff, then use `apply_project_edit` with the same arguments when `--allow-edits` is
enabled. An outdated digest or a non-unique match fails; reread and preview again.

Close KiCad before editing. The server serializes its own operations and uses an
atomic replacement, but it cannot lock out a separate editor changing the file
between reads and writes. Read the result back and rerun the relevant checks.
Edits are limited to allowed project text sources; generated artifacts, release
records and executable files are excluded. Use the normal editing/review workflow
for changes outside that scope. An accepted replacement is a source edit, not proof
that the resulting circuit or CAD syntax is correct.

Keep engineering authority explicit: repair the authored CAD path, declaration or
independently established requirement. Do not copy observed output into
`tests/contract.json` solely to make a check pass, invent part identities or waive
ERC/DRC findings. Follow [libraries](LIBRARIES.md) for CAD dependency repairs and
[BOM policy](BOM_POLICY.md) for BOM authority.

## Diagnose and check

| Tool | Arguments and use |
| --- | --- |
| `rescue_project` | `project_id`. Inspect one island when malformed peer metadata blocks normal discovery; keep an ignored receipt. Always `UNVERIFIED_GLOBAL`, with no CI or release eligibility. |
| `diagnose_project` | `project_id`; optional `native_report` and `bom`. Run selected portable checks and combine current source/native/BOM findings. Requires `--allow-checks`. |
| `check_project` | `project_id`; `depth` defaults to `portable`, `runner` to `auto`. Run selected portable or native verification and retain the receipt. Requires `--allow-checks`. |
| `check_scope` | Optional `project_ids`, `product_ids`, `tags`, `exclude_tags` lists. Run the selected portable gate, or the full gate without selectors. Requires `--allow-checks`. |
| `inspect_contract` | `project_id`, `native_summary`. Inspect saved source-bound native evidence without capturing again. Observations remain `UNREVIEWED`. |
| `capture_contract` | `project_id`; optional `runner`. Capture native evidence to help independently author the contract. Requires `--allow-checks`. |

Native `runner` choices are `auto`, `local` and `container`. `auto` selects an exact
local KiCad CLI when available, otherwise the project's pinned image. A local or
container runner requires native depth for `check_project` and `native: true` for
`doctor`. Doctor can inspect a toolchain before a project exists; a supplied project
and toolchain must agree. Scope include selectors form a union, then `exclude_tags`
removes matches; with only exclusions, selection starts from all projects.
Native failures retain runner and command evidence. Portable checks do not establish native acceptance.

Read `events.log`, the full diagnostic report and captured portable/native outputs
from the returned `run_directory`. When that directory is absolute, remove the
configured `--root` prefix for an artifact tool's checkout-relative path.
`rescue_project` is a repair aid while global discovery is broken; fix the manifest and rerun normal checks before relying on a
pass. Shared tooling or policy changes require the full gate. See
[diagnostics](DIAGNOSTICS.md) and [checks and CI](CHECKS_AND_CI.md).

For BOM diagnosis, supply the native assembly BOM and its corresponding project
native report from the same source revision. The binder checks source identity,
native artifact evidence and assembly population. A free-standing CSV or an old
report cannot establish the current board's BOM validity. Inspect the purchasing
BOM separately for the controlled manufacturer, MPN and revision join.

## Export and prepare an engineering review

Commit the reviewed source through normal Git and leave the checkout clean before
export or release preparation. Close KiCad. Add reviewed `release_exports` settings
to the project manifest before that commit; layer, origin and placement settings
are design-specific. Exact runner readiness and a complete source/contract remain
prerequisites. See [release readiness](RELEASE_READINESS.md).

| Tool | Arguments and use |
| --- | --- |
| `generate_views` | `view_id`; optional `project_ids`, `product_ids`, `tags`, `exclude_tags` lists. Generate product/variant BOMs, harness schedules and electrical/system review views with `--allow-exports`. |
| `export_project` | `project_id`, `export_id`; optional `runner`. Create native and purchasing BOMs and applicable Gerber, drill and placement exports. Requires checks and exports capabilities. |
| `prepare_review` | `project_id`, `release_id`; optional `runner`. Prepare an `engineering_review` candidate from clean committed source. Requires checks and exports capabilities. |
| `check_release` | `manifest`. Verify the candidate's source and retained evidence. |
| `package_release` | `manifest`, `package_id`. Verify and package the candidate, including its source Git bundle; requires `--allow-exports`. |
| `verify_package` | `archive`. Check inventory and hashes and perform a temporary restore without executing restored project scripts. |
| `restore_package` | `archive`, `restore_id`. Restore into a fresh managed directory and verify retained evidence; requires `--allow-exports`. |

`generate_views` projects existing authored product and variant records into review
outputs without running native KiCad. Its BOMs and harness/system views complement
the native assembly and purchasing BOMs; they do not replace source-bound native
validation. It writes `build/views/<view_id>` and returns its directory and files.

Use new IDs for new attempts; existing output destinations are not overwritten.
Managed destinations are `build/exports/<export_id>`, `build/releases/<release_id>`,
`build/packages/<package_id>.zip` and `build/restores/<restore_id>`. The export report
is `build/exports/<export_id>/files/exports.json`; the parent directory retains the
native runner's command evidence. Contract captures use `build/contract-coach/`; diagnostic runs use `build/diagnostics/`.
Manifest, archive, BOM and saved native-report inputs are checkout-relative paths.
Use returned paths for later artifact reads, diagnosis, manifest checks and
packaging. Some reports preserve the CLI's absolute path fields; remove the
configured `--root` prefix before supplying those paths to another MCP tool. For
example, `/checkout/build/diagnostics/run-001` becomes
`build/diagnostics/run-001` when `--root` is `/checkout`. Keep the rest of the path
unchanged. The review manifest is `build/releases/<release_id>/manifest.json`.
Review generated layers, holes, placement origin and rotation, component population
and BOM identity before relying on the outputs.

`prepare_review` does not expose prototype, pilot or production approval. A passing
manifest/package check proves its declared evidence and integrity scope. It does
not create approvals, authorize a build or establish electrical correctness.
Packaging retains reachable source Git history; review that history before sharing
outside the team. Record the returned package digest when choosing
[durable release storage](RELEASE_STORAGE.md).

## Walk a board from import to review

Use discovered IDs and returned paths throughout this sequence. Enable checks, writes, edits and exports for this complete workflow,
and authorize only the needed external import directory.

1. Call `list_projects` and `scan_imports`. Pick one source, a new `project_id` and
   its approved toolchain. Call `preview_import` and `diagnose_import`; read the
   receipt and resolve missing sheets, paths and exclusions before `import_project`.
2. Call `get_project` for the imported board, then `doctor` with native readiness
   requested. Complete its independently reviewed design inputs and contract.
3. Call `diagnose_project` and read the first blocking finding. Use
   `list_artifacts` and `read_artifact` to inspect the receipt's exact error and
   `read_project_file` to inspect the authoritative source it names.
4. For an explicit source repair, copy the returned SHA-256 and select one exact
   text occurrence. Call `preview_project_edit`, review its diff and call
   `apply_project_edit` with the same digest and replacement. Read back the source.
5. Call `check_project`; use native depth after CAD changes. If the contract is
   incomplete, use `capture_contract` or `inspect_contract` as an UNREVIEWED
   inventory, then obtain independent expectations. Rerun checks after each repair.
6. Run the appropriate `check_scope`. For a product or harness, use `generate_views`
   with a fresh `view_id` and the intended selection to review its variant BOMs and
   wiring/system projections. Review the diff and commit authored source through
   normal Git. Keep generated receipts and exports ignored; MCP does not create
   this source commit.
7. Call `export_project` with a fresh `export_id`. Read the retained native command
   results and inspect the actual exports. Call `diagnose_project` again with the
   exported native assembly BOM as `bom` and the still-current project summary from
   step 5's native check as `native_report`. Exporting does not create that validation
   summary. Rerun native checks first if source changed, then address source-bound
   BOM findings before proceeding.
8. Call `prepare_review` with a fresh `release_id`, then `check_release` with its
   manifest path. Inspect the candidate's actual frozen outputs and findings.
9. Call `package_release`, `verify_package` and, for a retained restoration,
   `restore_package`. Keep the package digest and verification evidence with the
   team's review/storage decision. Independent workstation and physical acceptance
   remain separate evidence.

## Troubleshoot the connection

- If launch fails, check the absolute interpreter path and install `.[mcp]` into
  that interpreter's environment. Run `python -B -m tools.mcp --help` there.
- If the board inventory is wrong, inspect `--root` and the checkout's branch, then
  reconnect. Do not infer live board IDs from example names in this guide.
- If an operation is absent, inspect the startup flags. Export and review preparation
  need both checks and exports enabled. Flags control discovery and availability.
- If an import source is outside the permitted roots, add its specific parent with
  `--import-root` and reconnect. Artifact/source readers remain checkout-scoped.
- If an edit rejects its digest or match, reread the source and prepare a new preview.
- If preparation rejects dirty or stale evidence, review and commit the actual source,
  then make a fresh run. Preserve failed receipts and follow their repair guidance.
