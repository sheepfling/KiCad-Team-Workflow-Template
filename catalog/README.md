# Shared repository catalogs

`projects.json` configures shared catalog locations and enabled discovery roots.
Projects themselves are discovered from `projects/*/project.json` and, when enabled,
`examples/projects/*/project.json`. Adding a board needs no central record edit.

`products.json` indexes optional `products/<id>/product.json` records and their
project dependencies. `parts.json`, `interfaces.json` and `libraries.json` own shared
identities; `toolchains.json` pins tool versions/images; `release-policies.json` owns
release assurance floors. `team-policy.json` configures review separation and exact
required status checks. Do not store generated BOMs here.

The initial settings enable the reference examples. Before adding real work, run
`tools.template init --project-id my-hardware` to initialize empty live catalogs.
Keep `examples/` for regression tests. `examples/catalog/`
contains independent reference catalog inputs used by those tests.

[tool-surfaces.json](tool-surfaces.json) tracks public CLI/MCP declarations and required core parity
and explicit administrative/adapter exceptions. Follow the
[surface inventory guide](../docs/workflow/TOOL_SURFACES.md) when either interface changes; the
unit-test gate rejects untracked drift.

## Reviewed CAD bindings for the parts picker

A part record may have an optional `cad` object. Existing identity-only records
remain valid for BOM review, but a picker choice needs a complete reviewed CAD
binding. Add real part records through engineering review; the training catalog is
not a preferred-parts library for purchasing.

| CAD field     | Meaning                                                                                  |
| ------------- | ---------------------------------------------------------------------------------------- |
| `symbol_id`   | Exact saved KiCad library symbol ID, such as `Device:R`                                  |
| `value`       | Exact saved symbol value; matching is case-sensitive and does not infer unit equivalence |
| `footprint`   | Reviewed qualified footprint ID in `library:name` form                                   |
| `model`       | Repository-relative path to the reviewed source 3D model                                 |
| `digikey_sku` | Optional exact reviewed DigiKey order code, including packaging when relevant            |

The enclosing part record must be `approved` and contain real manufacturer/MPN
identity. Record the selection rationale and check datasheet ratings, pin mapping,
package dimensions and footprint fit before approving it. The picker filters by
exact symbol ID and value; it does not determine electrical interchangeability.
Approved alternatives are not selected automatically. Selection copies the reviewed
manufacturer, MPN and datasheet into the chosen schematic symbol and matching PCB
footprint; the catalog remains the editing authority for those identities.

The footprint must resolve from its exact `library:name` ID through the project's
`fp-lib-table` to an inventoried `.kicad_mod` file in a declared local or shared
repository library. This first version does not use global-only installed KiCad
libraries. Copy the reviewed footprint into a controlled repository library,
record its provenance, and declare its table and source asset before using it.

The model must already be inventoried under the selected board's declared local
source roots or a declared shared library. Follow the
[library policy](../docs/workflow/LIBRARIES.md) for shared dependency inventories,
provenance and licensing. A filename or nearby file does not make a model an
approved dependency. Do not point a catalog entry at another board's private files
or a personal Downloads directory. A binding can be eligible for one project and
unavailable in another until that project declares the reviewed dependency.

Use the [parts-to-order workflow](../docs/workflow/PARTS_TO_ORDER.md) to capture a
picker, review downloaded choices, apply locked edits and prepare a BOM. Review
catalog changes with the full `python -B -m tools.ci` gate; applying a part to a board
also needs that board's native checks and actual geometry review.
