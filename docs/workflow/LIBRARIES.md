# Library policy

Use two kinds of libraries deliberately.

| Type          | Location                                               | Use when                                                  | Versioning rule                                                                                                                                                              |
| ------------- | ------------------------------------------------------ | --------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Project-local | `projects/<project-id>/kicad/` beside the `.kicad_pro` | The symbol, footprint, or model belongs only to one board | Commit it with the project change that depends on it.                                                                                                                        |
| Shared        | `libraries/<library-id>/`                              | More than one project needs the same controlled asset     | Add its catalog ID to each consumer's `library_ids`, its directory to `shared_source_roots`, every source file to `shared_inputs`, and its revision to any release manifest. |

`controller` demonstrates a project-local library: `Pilot.kicad_sym` and `Pilot.pretty` sit beside
its project file, and its `sym-lib-table` / `fp-lib-table` use `${KIPRJMOD}`. Keep those paths
relative. Do not rely on a user's global KiCad tables, Downloads folder, or an absolute
home-directory path.

For shared assets, use one named library directory per approved library and keep its symbols,
footprints, 3D models, licensing/provenance notes, and changelog together. The library catalog must
name repository-relative provenance and licensing records and pin the SHA-256 of each. The static
gate fails if either record is missing or changes without its catalog hash changing. A library
revision that changes an existing footprint is an engineering change: it needs a PR, review of
affected boards, and an explicit release-manifest entry.

## Two projects using one library

Keep each board as its own `projects/<id>/` island. Put reusable CAD assets in
`libraries/common/`, register that directory as one record in
`catalog/libraries.json`, and use that record's ID in both board manifests. In
each `project.json`, the shared fields use repository-relative paths:

```json
{
  "library_ids": ["library-common"],
  "shared_source_roots": ["libraries/common"],
  "shared_inputs": [
    "libraries/common/LICENSE.md",
    "libraries/common/PROVENANCE.md",
    "libraries/common/common.kicad_sym",
    "libraries/common/common.pretty/Connector.kicad_mod"
  ]
}
```

This is a partial manifest example; list **every** file under the shared root
in `shared_inputs`, including its README or changelog if present. The inventory
gate catches additions and deletions. In each board's project-local
`kicad/sym-lib-table`, a project at `projects/battery-board/kicad/` can use
`${KIPRJMOD}/../../../libraries/common/common.kicad_sym`; its
`kicad/fp-lib-table` can use
`${KIPRJMOD}/../../../libraries/common/common.pretty`. The three `..` segments
move from the KiCad project directory to the repository root. Keep the tables
with each board so a fresh checkout does not require a user's global library
configuration. The portable check resolves these references, requires the
targets to exist and be inventoried by that board, and rejects an undeclared
reference into another project's private directory. Manifest paths themselves
never contain `..`.

If an asset currently lives inside `projects/pwm-board/kicad/`, promote the
reusable asset into `libraries/<id>/` and update both boards' tables and
manifests. A board is a deliverable, not a shared-library root. Run the full
CI gate after a shared-library change so every consuming project is checked.
The importer copies only the selected project directory; it does not copy or
rewrite sibling dependencies. After importing such a project, make this
migration before expecting the portable or native checks to pass.

`PROVENANCE.md` records whether the asset was authored here, generated, copied from a
vendor source, or derived from a third party; it names the source, revision/date,
scope and review limits. `LICENSE.md` (or an equivalently named licensing record)
states the applicable distribution/use terms and any notice obligations. A hash only
binds the reviewed record bytes. It does not establish that a source is truthful,
complete or legally sufficient; obtain the relevant engineering and licensing review
before marking a shared library approved.

The controller configuration intentionally hashes only `examples/projects/controller/kicad` because
it is a project-local synthetic fixture. The Arduino and Raspberry Pi examples demonstrate the
shared-library rule: each manifest declares `examples/libraries/status-led` in
`shared_source_roots`, its complete file list in `shared_inputs`, and its catalog ID in
`library_ids`. The checker fails closed if any declared library input appears, disappears, or
changes outside review.

`generated/library-sbom-v1.json` is the deterministic inventory of controlled shared CAD libraries,
including each ID, version, path, owner/status and provenance/licensing record hashes. It is
regenerated with `python -B -m tools.hardware generate` and exported as ignored output; the shared
CI gate checks fresh generation. It does not assert that a library's legal review or physical
footprint qualification is complete.
