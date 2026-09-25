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

For a first part, run `python -B -m tools.template list --format text` to find
your board ID, then `python -B -m tools.parts --project <project-id> --assist`.
Use **Find CAD**, **Check STEP alignment**, and **Add CAD to this project** in that
order. The comparison needs Docker and still requires visual review. See the
[CAD first-part walkthrough](CAD_SOURCING.md) for setup and recovery.

For a failed board check, run `python -B -m tools.template diagnose --project-id <project-id>`.
Start with its short repair queue; use `--detail full` for every finding or
`--format json` for an agent or script. Open the printed `build/diagnostics/`
receipt for stage logs and raw results. Follow [diagnose and repair](DIAGNOSTICS.md)
before changing source or test expectations.

Run `python -B -m tools.verify --project <project-id>` for the selected board's
portable checks and a fresh ignored receipt; add `--depth native` after KiCad
source changes. Use `tools.ci --product <product-id>` for all members of a
registered product or `--tag <tag>` for a manifest-tagged cohort;
`--exclude-tag <tag>` removes matching boards. These selectors can be repeated
and combined. Use `python -B -m tools.ci --format text` for the full shared gate
after common tooling or policy changes. PR CI scopes project changes to affected
boards; main pushes run full checks. In GitHub Actions, **KiCad template acceptance**
defaults to `full` when manually run; choose `project`, `product` or `tag` and
enter its ID or tag to run only that group's hosted portable/native lanes.
Use `tools.verify --format json` for structured agent output. Its `--runner auto`
chooses an exact local CLI or the project's digest-pinned Docker image; use
`--runner local` or `--runner container` to force either route. The lower-level
`tools.ci --kicad` remains available when manually managing a fresh evidence
path. The template exercises KiCad 10.0.0 and 10.0.5.
Preview changed-file scope with `python -B -m tools.impact --base <ref> --head <ref> --format text`.
Keep each island at `projects/<id>/`: nested project directories are not discovered.
Use Python 3.11+ and preserve every declared local/shared library dependency.

## Grounding, power and high frequency

For a board with electrical requirements, use this setup-to-verification sequence:

```sh
python -B -m tools.electrical --project <id> --init
# Author requirements/models, then capture hashes for engineering review:
python -B -m tools.electrical --project <id> --capture-inputs --model <repo-relative-deck>
python -B -m tools.template doctor --electrical --project-id <id> --format text
python -B -m tools.verify --project <id> --depth electrical
```

Repeat `--model` for includes. Initial sections are pending and cannot pass;
captured hashes stay UNREVIEWED until the engineer reviews and records the mapping.
Use `--ngspice /path/to/ngspice` for a simulator outside `PATH`. For focused checks,
use `tools.electrical --project <id>` or `tools.ci --electrical --project <id> --format text`.
Text includes project identity and receipt; `--format json` contains every finding.
Create CSV, PNG and SVG from a saved receipt without rerunning the circuit:
`python -B -m tools.electrical_charts --receipt build/electrical/<id>-<run>`.
Install `.[charts]` once for Matplotlib. The manual **Electrical analysis** Action provides the hosted focused gate; normal
native acceptance still checks ERC/DRC. Follow the
[electrical quickstart and examples](ELECTRICAL_ANALYSIS.md#quickstart).
