# Repository tools

Run every CLI from the repository root as `python -B -m tools.<command>`.
`tools.ci` is the common local and hosted entry point. See the [command guide](../docs/workflow/CHECKS_AND_CI.md).

| Module | Responsibility |
| --- | --- |
| `ci`, `ci_matrix`, `check_all` | Coordinate the portable gate, registry-driven matrix and native lanes |
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
