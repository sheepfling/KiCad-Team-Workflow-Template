# KiCad + Git quick reference

Get the project assignment. Close KiCad before changing branches. Preserve existing
work. Fetch/pull current main, then create one issue-linked work branch. Use the
branch and project path recorded by the adopted repository; do not guess when the
assignment or starting state is unclear.

Open the `.kicad_pro`, not a detached schematic copy. Edit, synchronize schematic/PCB as needed, run checks, and save. Review the changed source. Commit locally, push, and open a PR. These are four separate actions.

Continue tomorrow on the same branch/PR. Pulling that branch does not automatically merge main. Do not reset, clean, or force-push to resolve uncertainty.

Inspect the Actions review artifact and checked commit. A green run is not a
substitute for independent approval or configured branch protection. Another
qualified person reviews; the integrator accepts; then close KiCad, update local
main and hand back the assignment.

On conflict, missing libraries, new tool versions or unexpected changes: stop, preserve work and ask the maintainer with branch, SHA, status and error. Never guess ours/theirs.

For a failed board check, run `python -B -m tools.template diagnose --project-id <project-id>`.
Start with its short repair queue; use `--detail full` for every finding or
`--format json` for an agent or script. Open the printed `build/diagnostics/`
receipt for stage logs and raw results. Follow [diagnose and repair](DIAGNOSTICS.md)
before changing source or test expectations.

Run `python -B -m tools.ci --project <project-id> --format text` for the selected
board's portable checks. Use `--product <product-id>` for all members of a
registered product or `--tag <tag>` for a manifest-tagged cohort;
`--exclude-tag <tag>` removes matching boards. These selectors can be repeated
and combined. Use `python -B -m tools.ci --format text` for the full shared gate
after common tooling or policy changes. PR CI scopes project changes to affected
boards; main pushes run full checks. In GitHub Actions, **KiCad template acceptance**
defaults to `full` when manually run; choose `project`, `product` or `tag` and
enter its ID or tag to run only that group's hosted portable/native lanes.
Omit `--format text`
for structured JSON in scripts. With its exact catalogued
KiCad installed, run `python -B -m tools.ci --kicad --project <project-id> --output build/review-001 --format text`
using a fresh output name each time. The template exercises KiCad 10.0.0 and 10.0.5.
Preview changed-file scope with `python -B -m tools.impact --base <ref> --head <ref> --format text`.
Keep each island at `projects/<id>/`: nested project directories are not discovered.
Use Python 3.11+ and preserve every declared local/shared library dependency.
