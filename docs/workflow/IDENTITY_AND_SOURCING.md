# Identity, pinouts, BOMs, and sourcing

KiCad holds electrical design facts; controlled catalogs hold business and supply-chain facts. Link
them with stable identifiers rather than copying volatile information into drawing text.

## Stable identities

Every production-bound component needs an internal part ID, revision, description,
class, manufacturer, MPN, datasheet URL, lifecycle state, approved-alternate policy,
approved status, and linked library asset. Store it in `catalog/parts.json`; put the
internal ID and MPN in KiCad fields. A changed MPN, footprint, lifecycle state, or
approved alternate is an engineering-review change.

The examples use the neutral KiCad fields `PART_ID` and `INTERFACE_ID` to reference
the part and interface catalogs. These names are shared between schematic symbols
and PCB footprints and carry no employer or vendor prefix. Manufacturer, MPN, and
supplier values describe a selected part; they do not determine the catalog schema.

Every external connector needs an interface ID and revision in
`catalog/interfaces.json`. Its pin list records pin number, signal, direction,
voltage/domain, mating connector/source, connector side/view and mechanical-clearance
authority. A product terminal that names an interface must name one exact declared
pin, and a harness conductor must terminate at a controlled interface endpoint. The
check can therefore fail a PR when a declared pinout or harness binding drifts; it
does not infer a pinout from a drawing.

Every reusable library needs an ID, version, owner, status, repository path, and
SHA-256-bound provenance and licensing records in `catalog/libraries.json`. A board
lists the library IDs it consumes; its release manifest records the exact revision.
Project-local assets remain with their board and are protected by that board's source
inventory.

## BOM and price policy

Generate a BOM from the tagged KiCad source and enrich it from the approved part
catalog. Store a sourcing snapshot beside the release—not as a permanent `Price`
field in a schematic. Each snapshot must state supplier, supplier SKU, quantity
break, currency, region, lead time/stock observation, timestamp, and source link or
export reference.

Price and availability are observations, not immutable design facts. The release identity is the Git
tag plus the manifest, BOM, toolchain version, library revisions, and evidence hashes.

When a controlled observation is needed, start from
`templates/sourcing-snapshot.example.json` and validate it without network access:

```sh
python -B -m tools.sourcing --snapshot release/<snapshot-id>.json
```

The snapshot binds every offer to an existing internal part ID and makes its observed
currency, integer minor-unit price, quantity break, supplier SKU, source URL, region,
availability, timestamp and optional lead time explicit. It does not fetch a live
price, validate an external page, select a supplier, approve a substitute, or grant
procurement authority.

## Fixture boundary

The controller project is a synthetic fixture, so its catalog entries are intentionally empty and
its registry marks component identity as not required. The Arduino and Raspberry Pi examples
exercise the field and catalog links, but their part records deliberately say `UNSPECIFIED` and
`do not purchase`; they are not approved sourceable parts.

A real engineering project must use the `production` assurance profile, set
`component_identity.required` to `true`, declare approved part IDs, link each shared
library/interface, and replace every training record with reviewed manufacturer, MPN,
datasheet, lifecycle, and approval data. The static gate now rejects production
projects that leave any of those controls incomplete.
