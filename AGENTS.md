# Working in this KiCad repository

This file is for coding agents and engineers using an agent. Start with the
[workflow guide](docs/workflow/START_HERE.md) and the
[diagnostic guide](docs/workflow/DIAGNOSTICS.md). Use Python 3.11 syntax.

## Find the right source

- Confirm the branch, checkout status and project ID before editing. Each
  `projects/<id>/` island owns its KiCad source, requirements, docs and tests.
  Shared policy and automation live under `tools/`, `catalog/` and `tests/`.
  For shared tooling changes, use the [tool map](tools/README.md),
  [test guide](tests/README.md) and [scripting standard](docs/workflow/SCRIPTING_STANDARD.md).
- For an existing design, preview the import before copying it. Use
  `python -B -m tools.template diagnose --source <path-to-.kicad_pro> --project-id <id> --toolchain <id>`.
  Read the import inventory and repair missing sheets or nonportable paths in
  the original source. Then follow the [import workflow](docs/workflow/IMPORT_WORKFLOW.md).
- For a registered board, run
  `python -B -m tools.template diagnose --project-id <id>` before changing
  policy or tests. The default output groups repeated causes; `--detail full`
  prints every finding. Agents and scripts should parse `--format json` stdout,
  not the human text: the versioned report includes `status`, `findings`,
  `next_command` and `run_directory`. Each run also writes a fresh ignored
  `build/diagnostics/` receipt.

## Diagnose, repair, verify

1. Read the first blocking group and its source location. If the cause is
   unclear, inspect `events.log` and the raw `import-preview.json` or
   `portable.json` in the receipt. For a coach crash, inspect `error.txt` and
   `run.json`; for a native failure, inspect the native `*.command.json` and
   ERC/DRC outputs.
2. Repair the authoritative source: KiCad files, declared assets, catalog
   records, or independently reviewed test expectations. Do not edit an export
   or copy observed output into the contract just to pass a check. Do not
   invent nets, part identities or ERC/DRC waivers. Surface missing electrical
   requirements to the responsible engineer. For CAD paths, follow the
   [shared-library policy](docs/workflow/LIBRARIES.md); never borrow an
   undeclared asset from another project's private directory.
3. After each source fix, rerun diagnosis and `python -B -m tools.ci --project <id>`.
   If related boards share a product, run `--product <id>`; for a named cohort,
   use `--tag <tag>`. Multiple include selectors form a union, and
   `--exclude-tag <tag>` removes projects afterward. Run the full
   `python -B -m tools.ci` gate after changing shared tools, catalogs or policy,
   and for a deliberate repository-wide rehearsal. If native KiCad inputs changed,
   rerun `--kicad --project <id>` with a fresh output directory and recheck
   affected BOMs and exports. Run `python -B -m tools.impact --base <ref> --head <ref> --format json`
   to inspect planned PR scope in a script or agent.
   For a manual hosted lane, run **KiCad template acceptance** in Actions with
   `focus=project` and `value=<id>` (or select `product` or `tag`). The default
   `focus=full` rehearses every lane; an optional `exclude_tag` narrows only a
   focused run. Preview the manual scope with `tools.impact --select-project <id>`.
4. Report the project ID, branch and commit, changed source, commands and
   results, receipt path, and any unresolved engineering decision. Keep run
   evidence in ignored `build/`, CI artifacts, or the issue/PR. Keep durable
   board decisions in `projects/<id>/docs/`.

Never commit imported practice projects, local KiCad state or generated working
outputs. Follow the [source and output policy](docs/workflow/REPOSITORY_HYGIENE.md)
and [BOM policy](docs/workflow/BOM_POLICY.md). A passing check verifies its
declared scope; it does not approve an electrical design or manufacturing release.
Project discovery is one level below each configured root, such as
`projects/<id>/`; nested project folders are not discovered. Use tags or
registered products to group independent islands.
