# Prepare, verify and restore a release

A board can release independently. Select it with `--project`; select an optional
product variant with `--variant PRODUCT:VARIANT`. Each candidate uses one pinned
KiCad toolchain. Different toolchains produce separate candidates.

## Prepare from committed source

Install `requirements-tooling.txt`, start Docker, close KiCad, and commit the reviewed source. Then:

```sh
kicad-team release prepare --project battery-board --release-id battery-review-001
kicad-team release check --manifest build/releases/battery-review-001/manifest.json
```

The command runs portable policy, generation and project/product tests for exactly
the selected release projects and their declared shared/product dependencies, then
native checks in each project's pinned image. It does not spend time validating
unrelated legacy islands. Use `--cli /path/to/kicad-cli` to use an installed exact
version instead. The retained `portable.json` names its selected projects and
hashes the entire clean source commit, so it cannot be mistaken for a full gate.
Run `kicad-team ci --format text` and the hosted full CI gate separately
for repository-wide acceptance.

Every declared electrical contract also runs during preparation. Install the exact approved
ngspice on PATH, or pass `--ngspice /path/to/ngspice`. MCP uses the simulator available in its
startup environment. Missing, pending, failed or stale declared evidence blocks the candidate.
`review.md` lists each project's electrical coverage. Build releases require an explicit contract
for schematic-backed boards; a section may be not applicable only with a reviewed reason.
Engineering-review candidates without electrical contracts explicitly show NOT_CONFIGURED.

The candidate retains electrical requirements, generated decks, command logs and waveforms.
Check and restore re-evaluate the required measurements and waveform coverage, grounding against
the retained native netlist, and source/model hashes. This verifies recorded evidence without
rerunning the simulator or executing project scripts. Existing candidates with declared electrical
requirements but no retained electrical evidence must be prepared again from their source commit.

For a hosted rehearsal of one registered project, open **Actions → Selected release
candidate → Run workflow** and enter its registered project ID (see
`kicad-team template list --format text`). This manually triggered job
uses `kicad-team ci-hosted candidate --project <id> --release-id <fresh-id>` to
prepare, check, package and verify an `engineering_review` candidate from
the selected GitHub commit. It fetches full source history for the restorable
Git bundle and retains its ignored evidence as a 30-day CI
artifact. It adds no time to ordinary PR checks. Review the artifact and the
actual board outputs. An example project can exercise the template path before
adoption, but it is training-only. This rehearsal is not a manufacturing release or a
substitute for the team's separate approval and long-term storage decisions.

Use `--portable build/portable/portable.json` only to reuse a full passing report
or a passing release-scoped report covering **exactly** this selection from the
same clean commit. A plain `kicad-team ci --project` report has no release source
binding and is not reusable release evidence. Dirty, stale, missing, mismatched
or partial evidence fails.
Project discovery still parses every project manifest, so malformed metadata
anywhere must be repaired before any normal CI or release lane can run. A valid
but failing legacy board or test suite outside the selected release scope does
not block this board's preparation. Shared catalogs likewise retain global
schema, duplicate-ID and path-safety checks; an unused catalog record's
review-specific semantics cannot block an independent board.

Outputs and the generated manifest live in ignored `build/releases/<id>/`. A new
attempt needs a new ID; previous evidence is never overwritten. The default
`engineering_review` class is suitable for rehearsal and review, including the
synthetic fixtures. It does not approve a board for manufacture.

The verifier checks the actual commit, source-file hashes, source cleanliness, the exact
portable/native project scope, toolchain, report results, native artifact hashes and native
ERC/DRC/netlist content. A manifest containing only self-declared `PASS` labels fails. Integrity
checks detect missing or altered evidence; trusted CI and reviewed release publication establish who
produced and approved it.

Boards requiring component identity bind each reference's `part_id` in
`tests/contract.json`, in addition to value, footprint and nets. Native `PART_ID`
fields must match those expectations and the declared catalog IDs even when no
product references the board. Production electrical schematics also require a
component/net contract; diagram-only training views are not production evidence.

## Board fabrication and assembly exports

Add reviewed `release_exports` settings to the board's `project.json` before the
source commit. For a two-layer board, a starting point is:

```json
{
  "gerber_layers": ["F.Cu", "B.Cu", "F.Mask", "B.Mask", "F.Paste", "B.Paste", "F.SilkS", "B.SilkS", "Edge.Cuts"],
  "coordinate_origin": "absolute",
  "position_units": "mm"
}
```

This object is the value of `release_exports`, not a separate file. Specify inner
copper layers for multilayer boards. Preparation generates Gerbers, separate plated
and unplated Excellon drills, placement CSV, native BOM and a purchasing BOM joined
to controlled `PART_ID` records. It also writes schematic and multipage PCB PDFs
and a JSON board-statistics report under `review/` in the ignored release receipt.
`supplier_formats` is optional; add, for example, `"supplier_formats": ["odb"]`
only when a supplier needs ODB++, IPC-2581 or IPC-D-356. ODB++ and IPC-2581
are compressed archives. IPC-D-356
is a board test netlist, not a component-population output. Plot origin is applied
consistently to Gerbers, drills and placement. Review layers, holes, population,
rotation/origin conventions, PDF coverage and supplier requirements before
approving the outputs. The board statistics describe the physical board and do
not change with an assembly variant.

For a board with a named KiCad design variant, set `"assembly_variant": "Pilot A"`
in `release_exports` for a standalone release. The name must already exist in
the committed `.kicad_pro` schematic settings. KiCad can report success for an
unknown name while exporting the default population, so the exporter refuses
an undeclared name before running native commands. A product variant can select
a different population for one board by adding
`"board_variants": {"battery-board": "Pilot A"}` to that variant in `product.json`.
This mapping overrides the board's default for that release candidate. Product
`exclude` removes named occurrences, including whole boards or individual
components; `board_variants` selects native KiCad population within an included
board. Conflicting selections of the same board in one candidate fail and need
separate candidates. The selected KiCad name is recorded in `exports.json` and
checked in the release evidence. For a product release, the native fitted BOM's
references and `PART_ID`s must also match the product variant's included board
members. Represent a component that is not fitted in both the KiCad design
variant and the product variant's occurrence `exclude` list (for example
`"UNO.R1"`). A different component identity needs a separately reviewed
product/part schema choice; the exporter will not silently substitute a part.
Run `kicad-team release export --project battery-board
--output build/battery-export --assembly-variant 'Pilot A'` to exercise a single
board directly from clean committed source.

Exporter options follow the [KiCad 10 CLI](https://docs.kicad.org/10.0/en/cli/cli.html). Extend
typed settings and the exporter table in the tooling package’s `kicad_tooling/hwrepo/exports.py`,
then add a focused regression and native acceptance case. Shared checks, project unit tests and
product tests still run through the common pipeline.

## Approval and tag sequencing

1. Commit the complete reviewed source and contracts first.
2. Prepare the candidate from that clean commit. The manifest can now name its SHA.
3. Review the frozen outputs. For a build release, use `--release-class prototype`,
   `pilot` or `production` during preparation. Selected projects must be
   `release_candidate` with the `production` assurance profile. Optional products
   must also meet their class-specific maturity and assurance floor.
4. Complete the manifest's named approval and retained evidence references; set its
   status to `approved`. Record open questions as blockers, not fictional approvals.
5. Create an annotated source tag pointing to the earlier source commit and record
   its name in `source_tag`. Run `kicad-team release check` again.
6. Package and retain the exact approved bytes in your release storage.

The manifest is generated after the source commit. It does not belong in the commit
whose SHA it records. Authored approval decisions can be committed later under an
island's `releases/`, referencing that earlier source and retained package; package
verification uses a checkout of the source commit. Checks never create approvals,
release tags, purchases or manufacturing authorization.

Non-review releases require approvals, the annotated source tag, appropriate
artifacts, approved identity/governance and applicable product assurance. Production
PCB releases also require successful native fabrication/assembly export evidence.
Open, expired, unknown-scope or unevidenced deviations fail. A waiver never silently
raises an engineering claim's assurance level.
Deviation scope names selected project IDs or IDs within selected products. Its
evidence references retained manifest artifact IDs or selected product evidence IDs;
a standalone board can use an authored review record retained in its release package.

## Package and restore

```sh
kicad-team release package --manifest build/releases/battery-review-001/manifest.json --output build/battery-review-001.zip
kicad-team release verify --archive build/battery-review-001.zip
kicad-team release restore --archive build/battery-review-001.zip --destination ../battery-review-restored
```

Packaging first verifies the candidate, retains its source Git bundle and complete
evidence inventory, and tests an actual restore before completing. The bundle
contains source history reachable from the selected source commit and tag. Review
that history before distributing a package outside the team. The archive has no
dependency on the original checkout or a remote repository.

Restore creates a new directory, checks archive inventory and hashes, rejects unsafe
paths and links, checks out the exact source commit, and re-verifies retained release
evidence. It never overwrites an existing checkout or executes the restored project's
scripts. To reproduce checks, install its dependencies and rerun the documented
commands separately. CI rehearsal artifacts expire after 30 days; approved release
packages need the team's long-term immutable storage and retention policy. Package,
verify and restore output includes `package_sha256`; record that digest with the
storage URI and retention decision described in [release storage](RELEASE_STORAGE.md).
