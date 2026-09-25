# Project workflow

## Before opening KiCad

1. Confirm the project assignment, branch, and exact approved KiCad version. The template catalog
   currently includes exact KiCad 10.0.0 and 10.0.5 pins; run
   `python -m tools.check_toolchain --toolchain <toolchain-id>`. A failure means do not save or
   convert.
2. Close KiCad before switching branches. Record `git status --short` and preserve every existing
   change.
3. If the tree is not clean, continue on that branch or ask the maintainer. Never use `reset`,
   `clean`, a force push, or a discard prompt to make a branch operation succeed.

## During an edit

- Open the `.kicad_pro`, not a copied schematic or PCB file.
- Keep the schematic, PCB, project settings, project-local libraries, and library tables coherent.
- Treat a library, rule, project-format, or mechanical-interface change as reviewable engineering
  work, not incidental cleanup.
- Run ERC and DRC, inspect every warning/exclusion, and keep generated review evidence outside
  tracked source.

## Before review or handoff

1. Save intentionally, close KiCad, then inspect `git status` and `git diff`.
2. Stage only intended source. `.kicad_prl`, locks, caches, backups, Office files and media are not
   source; [repository hygiene](REPOSITORY_HYGIENE.md) explains the two-layer guard.
3. Push the branch and open a PR that identifies the assignment, KiCad version, source/library
   changes, and affected interfaces.
4. A different qualified reviewer checks the exact commit and artifacts. A green run is evidence,
   not approval, a lock, or manufacturing authorization.

## Unexpected rewrite or version warning

Stop when a project opens with a new KiCad build, a conversion warning, or unexplained source
rewrite. Preserve the worktree and report the branch, commit, KiCad version, `git status`, and diff.
Perform migration in a dedicated PR; do not combine it with board edits.
