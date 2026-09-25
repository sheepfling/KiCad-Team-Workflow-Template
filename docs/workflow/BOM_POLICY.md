# BOM source, review and release policy

A BOM's purpose determines its storage. Keep one authoritative editing location for
each fact, and distinguish current generated views from exact released outputs.

| Record                                                                     | Default storage                                                                                       | Editing rule                                                              |
| -------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| Schematic component identity, population choices and approved alternatives | Git: KiCad, manifests or controlled catalog records                                                   | Edit the authoritative input                                              |
| Authored assembly list with cables, fasteners or purchased modules         | Git: project/product source                                                                           | Review as maintained design input                                         |
| Routine generated BOM, netlist, harness schedule or rendering              | Ignored project/product `build/`, or CI review artifact                                               | Regenerate; do not hand-edit                                              |
| Exact approved BOM for a release/build                                     | Retained release package; a small CSV may also be committed under the island's `releases/<revision>/` | Freeze it; a later change gets a new revision                             |
| Generated release manifest and artifact hashes                             | Retained release package, initially ignored `build/releases/<id>/`                                    | Bind source revision, toolchain, approvals and retained output identities |
| Authored approvals and release decisions                                   | Git: island `releases/`, or controlled release system                                                 | Reference the earlier source commit and retained package                  |

A Git tag alone does not preserve the exact generated BOM or manufacturing package.
Retain those bytes at release, rather than depending on future regeneration. CI review
artifacts expire and are not the long-term release archive. The adopting team chooses
its approved release storage and retention.

The template generates product variant views into the product's `build/`; native
KiCad validation generates review evidence at the requested ignored output location.
The library inventory and exported schemas are shared local outputs. All can be
regenerated without committing working copies.

Committing a working generated BOM can be reasonable when Git diffs are central to
review. That is an explicit policy extension: choose one deterministic generator and
add a CI comparison for the tracked view. The default workflow uses fresh CI artifacts;
it does not automatically verify arbitrary CSVs elsewhere as generated views.

Authored CSV BOM inputs and frozen release CSVs are already eligible for Git. Office files, native
fabrication exports and media outside authored docs/assets remain restricted by the current
[repository hygiene](REPOSITORY_HYGIENE.md) policy; adapting that boundary is a reviewed workflow
change, not a force-add workaround.

Standalone release preparation obtains fitted references from native KiCad and joins
their `PART_ID` values to the controlled catalog for a purchasing BOM. Manufacturer,
MPN and part revision come from that catalog. Assembly population comes from the
schematic's DNP/exclude-from-BOM settings; supplier quotes remain a separate sourcing
snapshot. See the complete [prepare/package/restore path](RELEASE_READINESS.md).

## Working purchasing checklist

Use [parts to order](PARTS_TO_ORDER.md) and `tools.parts --project <id>` for a fresh
source-bound checklist and grouped BOM under ignored `build/parts/`. It uses native
fitted references and declared catalog `PART_ID` records. The optional
`docs/purchasing.json` inside the project island is authored input: it records board
count, spare settings and reviewed DigiKey SKUs. Command-line overrides do not
rewrite it. Catalog manufacturer/MPN identity and schematic population remain
authoritative; a supplier SKU does not replace either.

The order CSV is emitted only when all fitted parts pass purchasing metadata
checks. Training placeholders, missing footprints and missing or unreviewed part
identities block it. DNP and exclude-from-BOM symbols remain visible without order
quantities. Spares are calculated per grouped part as the larger of the rounded-up
percentage of fitted pieces or the configured minimum; they are not cumulative.

`READY_FOR_ORDER_REVIEW` is a metadata result. Supplier matching, stock, price,
packaging, electrical suitability, physical fit and release approvals still require
their own evidence. Generated CSVs are working views; keep exact approved purchasing
and assembly outputs in the retained build/release package when freezing a revision.

## Reviewed part selection

The [parts picker](PARTS_TO_ORDER.md) applies explicit selections from approved
catalog CAD bindings. Its browser download is an intermediate proposal under
ignored `build/` or the user's downloads; it is not a second parts catalog or a
release approval. Preview binds the chosen catalog, model assets and design to a
locked selection. Only the explicit apply step changes authored schematic/PCB
fields, manifest part declarations and the default project purchasing preferences.
Review those source changes in Git; never commit disposable picker pages, selection
locks or diffs as design authority. Keep any durable engineering rationale with the
board's docs and the controlled catalog/library source.

The catalog owns manufacturer/MPN and the reviewed symbol, value, footprint and model binding. Apply
copies `PART_ID`, `Manufacturer`, `MPN` and `Datasheet` into the selected schematic and matching
placed PCB footprint; those fields mirror the reviewed catalog, not a new source of identity.
Schematic DNP and BOM exclusions still own population. An apply can copy the reviewed catalog
DigiKey SKU into `docs/purchasing.json` while preserving board and spare quantities. It retires a
replaced part declaration and saved SKU only after the last schematic use disappears; unrelated
declarations and overrides remain. Independent electrical expectations are never rewritten by
selection: review requirement changes before updating the contract and rerunning native checks.
Supplier availability and price remain separate dated observations. Regenerate the working BOM after
selection, KiCad PCB synchronization and verification; retain the exact approved outputs at release.
