# Choose parts and prepare an order

Open one local page to resolve the models paired with your existing PCB footprints,
choose reviewed catalog parts, and prepare an order file:

```sh
python -B -m tools.parts --project my-board --assist
```

The assistant scans automatically, shows each component and the proposed source
diff, and lets you add matched models with one button. It uses the assigned
`library:footprint` identity, the installed KiCad libraries, and the footprint's
own model references and transforms. When the footprint is absent locally, it
fetches the exact project's KiCad release from the official libraries. Downloads
are cached; model files, the source footprint snapshot, license and provenance are copied into the project and
added to its input inventory automatically. No account or model-map JSON is needed
for this path. Save and close the board in KiCad before applying source changes.

Before adding a model, the tool compares numbered pad positions, size, rotation
and drills against the source footprint, including rotated and bottom-side parts.
It preserves every placed footprint's location, pads and routing. Different pad
geometry, an altered existing model transform, missing CAD or unsupported custom
pads remain visible as **Needs review**. It can apply the independent matched
components while keeping these exceptions unresolved. A matching library pair is
alignment evidence, not manufacturer package or physical-fit approval. Native
3D inspection is still required before a manufacturing handoff.

The same page offers reviewed part choices and quantity controls, previews source
edits, applies them, and creates BOM/DigiKey CSV downloads. After **Prepare order**,
click **Send BOM to DigiKey** to get a myLists review link without API keys. This
sends the prepared BOM only on that click and does not make a purchase. Source
changes after a preview invalidate that plan; rescanning is enough.
The server listens only on localhost and stops with Ctrl-C. Use `--no-browser`
when you prefer to open the printed address yourself.

Part identity and CAD availability are different. The catalog picker still needs
reviewed manufacturer/MPN records; an electrical value such as `1k` cannot identify
a unique purchasable component. The bundled training catalog deliberately has no
production approvals. Exact-MPN CAD retrieval from an external provider is not
connected in this implementation. DigiKey product lookup and CAD-provider APIs
require their own access setup; DigiKey's separate myLists BOM handoff does not
require an API key. See the [provider and endpoint map](PARTS_PROVIDERS.md) for the
implemented path, account-free options and proposed connections. The automatic
CAD path uses the already assigned footprint, not a guessed supplier package.
The [catalog guide](../../catalog/README.md#reviewed-cad-bindings-for-the-parts-picker)
explains reusable part bindings.

For scripts, `--auto-models --format json` creates the same source-bound preview;
`--cad-plan <printed-path> --apply` imports it. The older file-based picker commands
below remain available for automation and offline review.

## First run

Complete the [Python setup](../../README.md#first-run-setup) and register your board
through [First board](FIRST_BOARD.md) or the [import workflow](IMPORT_WORKFLOW.md).
Run these commands from the repository root, replacing `my-board` with an ID listed
by the first command:

```sh
python -B -m tools.template list --format text
python -B -m tools.parts --project my-board --picker
```

The command uses the exact local KiCad CLI or the project's digest-pinned Docker
image to capture native evidence. Open the printed picker page in your browser.
Choose an offered catalog part for each component you want to update; use
**Keep current / skip this component** for the others. Select **Download choices**
to save `<project-id>-parts-selection.json`. The page is local and static: choosing
an option or downloading the JSON does not change your KiCad files. Keep the
download path for the next command. The receipt's `selection-draft.json` is an empty
starting map; the browser download contains the choices you actually made.

A choice appears only when an approved, non-placeholder catalog record has a CAD
binding whose `symbol_id` and `value` exactly match the saved symbol. Its reviewed
model must be paired by its source footprint and be an inventoried repository asset under this project's declared local
or shared source roots. Its `library:name` footprint must resolve through the
project's `fp-lib-table` to a declared repository `.kicad_mod` asset. For this catalog-selection mode, installed global
KiCad libraries alone do not establish a reviewed repository binding: copy the reviewed
footprint into a controlled local/shared library and declare it before picking.
Existing same-path models retain user-authored transforms without establishing alignment.
Exact matching is a catalog filter; the engineer who adds the part still reviews
ratings, pin numbering, package and physical fit.

The first version supports uniquely identified, top-level, single-unit symbols
that belong on the board. Multi-unit and off-board components remain visible but
cannot be chosen. Hierarchical/reused sheets and ambiguous source identities block
the picker. Use the manual field workflow below for unsupported components or
designs. DNP and exclude-from-BOM symbols remain outside purchasing quantities.

If a runner is unavailable, run the project preflight:

```sh
python -B -m tools.template doctor --native --project-id my-board --format text
```

Use `--runner local --cli /path/to/kicad-cli` to select an exact local executable,
or `--runner container` to require Docker. `--runner auto` is the default. A
version mismatch needs the approved toolchain or a reviewed toolchain migration.

In an uninitialized template checkout, try the training fixture:

```sh
python -B -m tools.parts --project raspberry-pi-status-led --picker
```

Expect a catalog-needs-attention result: its placeholder parts are not purchasable
choices. Use the page to inspect what is missing; do not approve training records
just to populate a dropdown. An adopted repository disables example discovery, so
use your own registered board there.

## Preview and apply your choices

Save and close KiCad before changing source. Pass the downloaded selection to a
preview command, using its actual path:

```sh
python -B -m tools.parts --project my-board --selection /path/to/downloaded-selection.json
```

Read the proposed source diffs in the new receipt's `index.html` or `selection.diff`.
The preview creates `selection-locked.json`, bound to the exact source, catalog and
model files being reviewed. Use the locked path printed by that command when applying:

```sh
python -B -m tools.parts --project my-board --selection PASTE_LOCKED_SELECTION_PATH --apply
```

The unlocked browser download is a proposal and cannot be applied directly. If a
bound input changes after the preview, create a fresh picker (or a fresh model-sync
preview) and review again. Do not edit the lock or copy hashes from newer files to
bypass that check.

The reviewed apply step fills the selected schematic `PART_ID`, `Footprint`,
`Manufacturer`, `MPN` and `Datasheet` fields from the catalog. These are copies of
reviewed catalog values; the catalog remains authoritative. It also declares the
chosen part IDs in the project manifest and records reviewed DigiKey SKU choices
in the project's default `docs/purchasing.json`. An old part ID
is retired from the manifest, with its obsolete saved SKU override, only when no
schematic component still uses it, including excluded and unselected references.
Other declarations, overrides, board quantity and spare settings are preserved.
For a matching placed PCB footprint, it mirrors `PART_ID`, `Manufacturer`, `MPN`
and `Datasheet`, and adds the selected model where no model is assigned.
It does not place new footprints, route connections or replace a different existing
3D assignment. Repair an existing model assignment in KiCad, including its fit,
rotation and offset.

For boards bound into a product assembly, also review its independently authored
member part IDs before native verification. The picker does not rewrite product definitions.

## Update the board and finish the models

If a chosen footprint is missing from the PCB or differs from the placed footprint,
the apply result identifies the pending references. Open the exact registered
project in KiCad, use **Update PCB from Schematic (F8)**, review its changes, place
the new footprints, and save. Close KiCad, then preview model synchronization:

```sh
python -B -m tools.parts --project my-board --sync-models
```

This reads the current fitted schematic `PART_ID` selections and their reviewed CAD
bindings against the updated PCB. It produces a fresh preview and locked selection;
it does not choose models by filename. Inspect its diffs and apply the printed locked path:

```sh
python -B -m tools.parts --project my-board --selection PASTE_NEW_LOCKED_SELECTION_PATH --apply
```

If selected part IDs or footprints differ from the independently authored contract,
the report names that requirement review. Before native verification, review the
engineering intent in `tests/contract.json` (or the manifest's `checks` file) and
update expectations only when the reviewed requirements justify the change. The
picker never edits this contract; do not copy observed values into it merely to pass.

```sh
python -B -m tools.verify --project my-board --depth native
python -B -m tools.visualize --project my-board --check-models
```

Inspect the actual 3D geometry and adjust model transforms in KiCad where needed.
The [3D workflow](THREE_D_WORKFLOW.md) covers visual review and export. An applied
selection, a matched library ID or a successful model export does not validate
component dimensions, electrical suitability or assembly fit.

## Fill details manually when needed

Follow the report's references back to the source. A generic value such as `1k` or
`LED` is not enough to identify something to buy.

1. Select the exact component from the design requirements and its manufacturer
   datasheet. Review electrical ratings, package, pin numbering and footprint fit.
   Record the reviewed identity in `catalog/parts.json`: an internal `id`, revision,
   description, part class, unit, manufacturer, MPN, datasheet URL, lifecycle,
   status and any reviewed alternatives. Use `approved` only after that review.
   The [authority model](AUTHORITY_MODEL.md) explains which record owns each fact.
2. Add each selected internal ID to `component_identity.part_ids` in the board's
   `project.json`. In KiCad's **Symbol Fields Table**, fill the exact `PART_ID`
   field for each fitted symbol, and copy the reviewed catalog `Manufacturer`,
   `MPN` and `Datasheet` values exactly. Bulk editing lets you handle repeated parts
   together. The ID connects the schematic to the catalog; the catalog owns these
   identities, and approved-part native checks compare the manufacturer and MPN.
3. Assign a footprint to every fitted part, and review DNP (do not populate) and
   exclude-from-BOM attributes. Both exclusions remain visible in the checklist
   but contribute no order quantities. Save the schematic, then use **Update PCB
   from Schematic (F8)** to transfer footprints and connections to the PCB. Place
   and route the board in KiCad.
4. Run `python -B -m tools.verify --project my-board --depth native` after changing
   KiCad source. Review the resulting evidence, then rerun `tools.parts` for a
   fresh checklist. Repair source records instead of editing a generated CSV.

The [KiCad Schematic Editor manual](https://docs.kicad.org/10.0/en/eeschema/eeschema.html)
explains the Symbol Fields Table, footprint assignment and PCB update tools.

## Remember your choices

If the apply step created `docs/purchasing.json` in your project, edit and review
that file. Otherwise create it once:

```sh
python -B -m tools.parts --project my-board --init-preferences projects/my-board/docs/purchasing.json
```

This creates a new JSON file under the selected island's `docs/` without capturing
native evidence. It refuses to overwrite an existing file. With no saved preferences
or quantity options, its initial contents are:

```json
{
  "schema_version": "1",
  "boards": 1,
  "spare_percent": 0,
  "spare_minimum": 0,
  "digikey_skus": {}
}
```

Set `boards` to the number of boards to assemble. Set `spare_percent` to a whole
percentage from 0 through 100 and `spare_minimum` to the minimum number of extra
pieces of each grouped part. The board count must be a positive integer; spare
settings are nonnegative integers. For example, ten boards with two identical resistors each need twenty
resistors. With ten percent spares and a minimum of three, the order quantity is
23: twenty fitted pieces plus the larger of two percentage spares or three minimum
spares. The two spare allowances are not added together.

`digikey_skus` maps an internal part ID to an exact, reviewed DigiKey SKU. Add an
entry only after checking that SKU's manufacturer, MPN and packaging. An absent
entry uses the catalog MPN in the upload file and leaves supplier matching for
review. This file records your choice; it is not a live supplier verification.

The command automatically reads `docs/purchasing.json` within the selected project
island if it exists. Use `--preferences path/to/purchasing.json` for a different
saved file. Quantity and `--preferences` options belong to the order-review mode,
not `--picker`, `--selection` or `--sync-models`. Command options override that run's
saved numbers without rewriting the preferences:

```sh
python -B -m tools.parts --project my-board --boards 10 --spare-percent 10 --spare-minimum 3
```

Reviewed project preferences can be committed as authored input. Keep temporary
experiments under ignored `build/` and pass their file with `--preferences`.

For fewer repeated edits in future designs, put the reviewed `PART_ID`, footprint,
manufacturer, MPN and datasheet fields in your controlled symbol library, following the [library policy](LIBRARIES.md).
KiCad also supports project field-name templates in Schematic Setup, which can add
an empty `PART_ID` field automatically. User-wide templates live in Preferences.
These conveniences still require a real part selection; they do not validate it.
See [KiCad field-name templates](https://docs.kicad.org/10.0/en/eeschema/eeschema.html#field-name-templates).
Keep stock, price and lead-time observations in sourcing evidence rather than
embedding them as permanent library facts. Approved alternatives are recorded for
review; `tools.parts` never chooses one automatically.

## Review and upload

After applying choices and completing the KiCad review, prepare the purchasing
checklist. This command reads source and does not edit CAD:

```sh
python -B -m tools.parts --project my-board
```

Open its `index.html` for a searchable component checklist and DigiKey search
links. The page works offline; following a supplier link makes a network request.
Searches use the manufacturer and MPN, or an explicitly saved DigiKey SKU.
Each run creates a fresh receipt under ignored `build/parts/`. Use `--output` with
a fresh path under ignored `build/` to choose its location. Order-review files are:

| File | Purpose |
| --- | --- |
| `index.html` | Searchable checklist, missing-details guidance and DigiKey search links |
| `report.txt` / `report.json` | Human report and complete structured result |
| `bom.csv` | Grouped review BOM with excluded and unresolved references also visible |
| `digikey.csv` | Upload quantities, emitted only when every fitted part is ready for order review |

Each resolved BOM group lists its references together and includes its order total
once. Excluded and unresolved references appear without quantities, so a review BOM
with outstanding findings is incomplete for purchasing.

`READY_FOR_ORDER_REVIEW` means the metadata checks passed: fitted parts have
footprints and declared, reviewed catalog identities with manufacturer and MPN,
and the run has no blocking findings. It does not establish live stock, price,
packaging suitability, footprint fit, electrical approval or manufacturing release.
`NEEDS_PARTS` means the checklist has missing or unsuitable purchasing details;
`BLOCKED` means input or native evidence could not be used. A missing order file
means there is still a blocker; use the checklist to resolve it. DNP and excluded
symbols have no purchasing quantities.

In the local assistant (`--assist`), use **Prepare order**, then **Send BOM to
DigiKey**. The button sends the prepared part numbers, quantities, manufacturer/MPN,
references and notes to DigiKey and returns a review link. No API key or developer
account is required; sign in at DigiKey to save the list. Review the matches there
before adding anything to a cart. This handoff does not retrieve CAD or confirm
stock, price, packaging or a purchase.

A failed or uncertain submission is not retried automatically. Prepare a fresh
order before making an explicit new attempt. A saved single-use URL cannot cause
the assistant to resubmit the BOM automatically. If the service is unavailable,
use the CSV fallback. The [provider map](PARTS_PROVIDERS.md) links the official
request contract and explains the separate authenticated product-data APIs.

For the CSV fallback or a static command-line receipt, upload `digikey.csv` to
DigiKey myLists and map these columns:

| CSV column | myLists meaning |
| --- | --- |
| `Part Number` | Reviewed DigiKey SKU, or catalog manufacturer part number |
| `Quantity` | Total pieces for all requested boards, including the calculated spares |
| `Customer Reference` | Internal `PART_ID` for reconciling the list |

Set the myLists assembly multiplier to **1** and turn additional attrition off:
the exported quantities already include both board count and spares. Review every
matched item, especially MPN-only matches, along with manufacturer, package,
packaging, minimum order quantity, stock and current price before ordering.
[DigiKey's BOM guide](https://www.digikey.com/en/help-support/place-an-order/build-a-bom)
describes its assembly multiplier and attrition features. CSV generation remains
local and does not confirm that DigiKey accepted an upload. The browser handoff
reports its own response separately; it does not establish purchase or manufacturing
approval. No add-on installation is required.

For a retained build or release, follow the [BOM policy](BOM_POLICY.md) and
[release workflow](RELEASE_READINESS.md). A working order checklist is not the
frozen, approved release BOM.

## Reuse evidence or automate

Both the picker and the read-only purchasing checklist can reuse an existing
native result. Point to its project summary:

```sh
python -B -m tools.parts --project my-board --picker --native-summary build/native/my-board/summary.json --format json
python -B -m tools.parts --project my-board --native-summary build/native/my-board/summary.json --format json
```

Replace the example path with the actual summary from your receipt. The tool
validates project identity, source hashes and native netlist evidence before using
it. Changed source requires a new capture. `--format json` is the agent/script
interface; parse its structured result instead of scraping terminal text. The
read-only purchasing review returns exit code `0` when ready for order review and `1` when parts or evidence
need attention; invalid command arguments return `2`. A purchasing checklist does
not replace `tools.verify`, ERC/DRC review or the full shared gate after catalog or
tooling changes.
