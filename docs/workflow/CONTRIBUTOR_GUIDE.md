# KiCad + Git contributor guide

This is the normal assignment → current main → work branch → KiCad edit/check →
save/commit/push → PR → independent review → accepted merge → sync/handoff route
for a repository created from this template. The commands are concrete; adapt the
project identity and branch names to the adopted repository.

## 01 / Get set up once

Install Git, Python 3.11+ and the repository's approved KiCad build. Follow the
[Python environment setup](../../README.md#first-run-setup) before running checks. Clone your repository, keeping the complete project and its adjacent libraries together. Replace `REPOSITORY_URL` and `REVIEW_BRANCH` below with the repository and branch assigned for the work. Confirm the default branch and the example's availability with the maintainer.

```sh
git clone "REPOSITORY_URL" kicad-project
cd kicad-project
git fetch origin
git switch --track "origin/REVIEW_BRANCH"
```

For a first rehearsal, open `examples/projects/controller/kicad/controller.kicad_pro`. Do not change an unrecognized library path or discard a load warning to continue. The worked fixture is for learning the workflow; adopted engineering work belongs under `projects/`.

## 02 / Start a change

Obtain the project assignment first. Assignment and handoff are team procedures; configure hosted protections and ownership for the adopted repository. Close KiCad and account for all uncommitted changes before switching branches.

After the initial adoption change has been accepted:

```sh
git switch main
git pull --ff-only origin main
git switch -c work/controller-ISSUE-description
```

Never use reset/clean or force push as a routine way to make those commands succeed. When continuing tomorrow, return to the existing branch and existing PR. Pulling that branch does not incorporate newer `main` automatically.

## 03 / Edit and check in KiCad

Start with a non-electrical drawing-text change. Keep the whole schematic/PCB/library set coherent; saving a schematic does not automatically update the PCB. Run ERC and DRC and investigate every finding. The supplied fixture has no accepted exclusions.

Save and close KiCad before running the reproducible checker from the repository root:

```sh
python -B -m tools.ci --kicad --project controller --output build/review-001
```

Replace `controller` with the assigned project ID in an adopted repository.
Choose a new evidence directory each time. A missing tool, unexpected version, new board scope, dependency problem or electrical/parity finding is a failure, not permission to skip the check. The independent netlist contract deliberately detects fixture connectivity/value changes; changing that contract is itself reviewable engineering work.

## 04 / Save, share and request review

Save changes in KiCad; inspect `git status` and `git diff`; stage only intended source. Generated reports, personal preferences and lock files are not source changes. A commit records a local checkpoint. Push publishes it. Neither is approval.

```sh
git status --short
git add projects/<project-id>
git diff --cached
git commit -m "Describe the intended engineering change"
git push -u origin HEAD
```

Open a PR to `main`, state the board assignment, and explain the change. Inspect the Actions review artifact and exact checked commit. Fix issues on the same branch; new commits need renewed checks and review. Do not self-approve or treat the absence of required branch rules as approval to merge.

## 05 / Review, merge and hand off

A different qualified person reviews the drawings, report findings, source/settings changes and exact candidate. The integrator merges only after the configured acceptance requirements are met. The template supplies records and checks; the adopted repository must still configure independent review, protected-main enforcement and contributor permissions.

After an accepted merge, close KiCad, preserve unfinished work, switch to `main`, and pull with `--ff-only`. Reopen the project and hand back the assignment. Disposition old PRs explicitly before assigning the same board to someone else.

## 06 / Stop and recover safely

For a wrong branch, conflict, unexpected version, missing dependency or unexplained file rewrite, stop and preserve the current work. Give the maintainer the branch, commit, status output, error and intended change. Do not blindly choose "ours" or "theirs" for a CAD conflict. An automatic text merge does not establish electrical correctness.

## 07 / Release and practice

Passing a repository check does not by itself authorize ordering or operating hardware. CI artifacts are review evidence, not immutable approved releases. Complete the desktop rehearsal, contributor permission tests, independent review and the adopted repository's release process before calling a design production-ready.
