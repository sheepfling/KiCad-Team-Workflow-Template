# Versioning, tags, and releases

## Working versions

Use one branch and PR per logical change. Commit board source with the local library
revision and test contracts it needs. `catalog/toolchains.json` owns approved exact
KiCad versions. Run `kicad-team check-toolchain --toolchain <id>` before editing; a version
or project-format change belongs in a dedicated migration.

## Release versions

A standalone board owns its revision, for example `battery-board-v1.2.0`. A product
owns its integration revision and selected variants independently. The scaffold's
version describes workflow compatibility, not a board revision.

The [scaffold changelog](../../CHANGELOG.md) names each baseline and its adoption impact.
The template contract is versioned independently from the installed tooling package and its
legacy policy version. `kicad-team --version` reports the tooling package's SCM-derived version;
`requirements-tooling.txt` records the exact selected Git commit. Follow the
[tooling migration guide](TOOLING_SPLIT.md) when changing that pin.

Candidate metadata alone does not publish a release. An accepted template or tooling baseline
gets its own reviewed source tag in its owning repository after its acceptance checks. Retain
acceptance links and the source commit in release notes. Never move a published tag; corrections
receive a new version and applicable migration guidance.

Commit reviewed source first, prepare and review generated evidence, then create an
annotated tag pointing to that source commit. The generated manifest is written
afterward and names the commit; it is retained with the release package. This avoids
asking a committed manifest to contain its own commit hash. Later authored release
decisions may reference the earlier source revision.

Follow [release readiness](RELEASE_READINESS.md) for commands, approvals, artifact
requirements, production controls and the prepare/package/restore sequence. A Git
tag alone does not preserve the exact manufactured BOM or fabrication outputs.

## Restoring and handing off

Use `kicad-team release restore` into a new directory. It checks the archive inventory,
restores the source commit and verifies its retained evidence. Preserve the package
in the approved release storage; short-lived CI artifacts are review evidence.

For ongoing work, record the branch, last commit, open PR, outstanding findings,
unpushed work and responsible next person. Transfer explicit source changes rather
than copying a desktop folder over another engineer's checkout.
