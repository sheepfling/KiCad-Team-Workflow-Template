# Repository tools

Run every CLI from the repository root as `python -B -m tools.<command>`.
`tools.ci` is the common local and hosted entry point. See the [command guide](../docs/workflow/CHECKS_AND_CI.md).
Use `python -B -m tools.template list --format text` to find registered project,
product, tag and toolchain IDs before selecting a lane. Its `readiness` field only
reports whether declared inputs are present; run checks to validate a design.
Use `--project <id>` for one island, `--product <id>` for a registered product's
members, or `--tag <tag>` for a manifest cohort. These include selectors form
a union; `--exclude-tag <tag>` removes matches. The selected portable lane
runs applicable project/product checks; the unselected lane runs the full
shared regression and quality gate. `tools.ci --matrix` and `tools.ci --kicad`
accept the same selectors for native work. Run
`python -B -m tools.impact --base <ref> --head <ref>` to preview changed-file
PR scope and why projects were chosen. For a manual hosted run, use
`tools.impact --select-project <id>`, `--select-product <id>` or
`--select-tag <tag>` to preview one focused selection; `--full` previews the
default full run.
The CLIs use `argparse`; a Typer dependency is not required for human output.
Choose text for a concise terminal view and JSON for the complete typed result:

| User-facing command | Human view | Agent/script view |
| --- | --- | --- |
| `tools.template diagnose` | Brief text by default; `--detail full` expands it | `--format json` |
| `tools.template list` | `--format text` shows selections and next commands | JSON by default; typed inventory |
| `tools.template rescue --project-id <id>` | Brief local repair view, always unverified; `--detail full` expands it | `--format json` with `UNVERIFIED_GLOBAL` and no CI/release eligibility |
| Other `tools.template` commands; `tools.ci`, `tools.hardware`, `tools.sourcing`, `tools.metrics` | `--format text` | JSON by default |
| `tools.release prepare` | Text by default | `--format json` or `--json` |
| Other `tools.release` commands | `--format text` | JSON by default |

The lower-level runner modules in the table below remain JSON-first adapters.
Do not scrape human text in automation; check the exit status and parse stdout JSON.
Agents with shell access can call these CLIs directly. An MCP server is optional
integration work, not a prerequisite for repository policy.

| Module | Responsibility |
| --- | --- |
| `ci`, `ci_matrix`, `check_all` | Coordinate the portable gate, registry-driven matrix and native lanes |
| `impact`, `hwrepo/impact.py` | Plan affected PR project lanes from changed paths; broaden ambiguous/shared-tool changes to full scope |
| `native_deps` | Prepare Linux wheels for the pinned container's Python, without requiring pip inside the image |
| `validate`, `check_toolchain`, `fault_probe` | Adapt the pinned KiCad CLI, preserve source hashes and test deliberate native defects |
| `lint_registry`, `docs_policy` | Expose registry and Markdown policy |
| `hardware` | Check products, generate ignored review views/schemas, create and verify snapshots |
| `template`, `release`, `sourcing`, `metrics` | Expose environment and project diagnostics, adoption, release readiness, supplier snapshots and current policy metrics |
| `hwrepo/models.py`, `hwrepo/contracts.py` | Own typed serialized contracts and file/path adapters |
| `hwrepo/discovery.py`, `hwrepo/project_tests.py`, `hwrepo/scaffold.py`, `hwrepo/importing.py` | Resolve local manifests, run isolated island test suites and create or import project islands |
| `hwrepo/doctor.py`, `hwrepo/adoption.py` | Check local prerequisites and run one-command fresh-fork adoption |
| Other `hwrepo/` modules | Implement named policy and generation services behind the CLIs |

Add substantial rules to the appropriate service and behavioral coverage to
[tests](../tests/README.md). New projects and variants are records, not new scripts.
Outputs belong in ignored locations and must never rewrite native design source.
