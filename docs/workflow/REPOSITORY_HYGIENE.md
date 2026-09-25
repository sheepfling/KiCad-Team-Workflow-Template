# Repository hygiene and accidental-file safety

This repository is a reviewable source record, not a shared Downloads folder. Its
ignore rules are designed for contributors who may work primarily through KiCad,
Windows Explorer or an Office application rather than Git commands.

## Two layers of protection

`.gitignore` prevents ordinary `git add` from selecting personal/editor state,
temporary files, Office files, media, archives and installers. The repository policy
also rejects those files if someone uses a force-add command or a graphical client
overrides the ignore list. A policy failure is reported as either
`TRACKED_LOCAL_STATE`, `TRACKED_UNMANAGED_ARTIFACT` or `TRACKED_GENERATED_OUTPUT`.

Ignored files remain on the contributor's computer; the rule does not delete them.
Do not use a force-add option to bypass it. If an ignored file appears to be needed,
stop and propose a reviewed policy change rather than making a local exception.

## External reference bundles

Downloaded handoff bundles and planning packets are temporary reference material.
Keep their archives outside the repository, unpack or inspect them in a separate
working location, and do not commit the archive or an extracted vendor-style copy.
When a reference materially informs a decision, record only its source, received
date and SHA-256 in a reviewed Markdown or structured record. This preserves the
audit trail without turning a binary bundle into repository history.

## What is intentionally ignored

- Operating-system metadata, recycle/trash folders, thumbnails and file-manager
  leftovers from Windows, macOS and Linux.
- KiCad locks, local preferences, autosaves, caches and backup directories.
- Editor/workspace settings, temporary/recovery files and local test/build output.
- Word, Excel, PowerPoint, LibreOffice, Apple iWork, OneNote and mail-client files.
- Audio, video, archives, downloaded installers and disk images; images outside
  the authored-documentation location described below.

## What remains eligible for review

KiCad source, project-local libraries, Python, Markdown and authored JSON/YAML records remain
tracked source. Reproducible BOMs, review views, native manufacturing exports and model-derived
schemas are ignored and rejected if force-added. Only the README files in `generated/` and
`schemas/` are source. Keep other derived files under `build/`; their extension alone cannot always
distinguish an input from an export. PDF, STEP/STP and DXF are not globally ignored because a real
mechanical handoff may need a reviewed drawing or model. When they are used, give them a stable
repository path, declare or link them from the relevant project/handoff record, and review their
source, revision and hash.

Keep authored PNG, SVG, JPEG, WebP and GIF figures under `docs/assets/`, either at
the root or within a project/product island. Link them from the relevant document.
Generated schematic/PCB figures belong in `build/`, including during releases.
License, notice and copying Markdown files retain their upstream formatting and do
not need a synthetic heading or navigation link; their local links are still checked.

Before requesting review, close KiCad and inspect `git status --short`. Stage only
the intended source and evidence records. Unexpected files are a stop condition:
leave them untracked/ignored or move them outside the repository; do not discard
them merely to make status look clean.
