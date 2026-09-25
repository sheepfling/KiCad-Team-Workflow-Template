# Choose parts and prepare an order

Use `tools.parts` to turn a saved schematic into a parts checklist, a grouped BOM
and, once its purchasing details are complete, a DigiKey upload file. Start with
one board; save its build quantity and spare preferences so the next run needs only
the project ID. The command reads design source and writes a fresh ignored receipt.
It does not edit the schematic, choose substitutes, place components or submit an
order.

## First run

Complete the [Python setup](../../README.md#first-run-setup) and register your board
through [First board](FIRST_BOARD.md) or the [import workflow](IMPORT_WORKFLOW.md).
Run these commands from the repository root, replacing `my-board` with an ID listed
by the first command:

```sh
python -B -m tools.template list --format text
python -B -m tools.parts --project my-board
```

The command uses the exact local KiCad CLI or the project's digest-pinned Docker
image to capture native evidence. It prints the receipt path. Open its `index.html`
in a browser for a searchable parts table and guidance for missing details. The page
works offline; DigiKey search links make a network request only when you follow
them. Searches use the recorded manufacturer and MPN, or your explicitly saved
DigiKey SKU, without selecting a substitute.

If a runner is unavailable, run the project preflight:

```sh
python -B -m tools.template doctor --native --project-id my-board --format text
```

Use `--runner local --cli /path/to/kicad-cli` to select an exact local executable,
or `--runner container` to require Docker. `--runner auto` is the default. A
version mismatch needs the approved toolchain or a reviewed toolchain migration.

In an uninitialized template checkout, try the training fixture:

```sh
python -B -m tools.parts --project raspberry-pi-status-led --boards 3 --spare-minimum 2
```

Its placeholder parts intentionally block the order file. Use its checklist to learn
the flow; do not turn training records into purchasing approvals. An adopted
repository disables example discovery, so use your own registered board there.

## Fill in the missing details

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
   field for each fitted symbol. Bulk editing lets you handle repeated parts
   together. The ID connects the schematic to the catalog; the catalog owns the
   manufacturer and MPN used by this tool.
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

Create a preferences file once, then edit and review it:

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
pieces of each grouped part. The board count must be a positive integer; spare settings are nonnegative
integers. For example, ten boards with two identical resistors each need twenty
resistors. With ten percent spares and a minimum of three, the order quantity is
23: twenty fitted pieces plus the larger of two percentage spares or three minimum
spares. The two spare allowances are not added together.

`digikey_skus` maps an internal part ID to an exact, reviewed DigiKey SKU. Add an
entry only after checking that SKU's manufacturer, MPN and packaging. An absent
entry uses the catalog MPN in the upload file and leaves supplier matching for
review. This file records your choice; it is not a live supplier verification.

The command automatically reads `docs/purchasing.json` within the selected project
island if it exists. Use `--preferences path/to/purchasing.json` for a different
saved file. Command options override that run's saved numbers without rewriting
the preferences:

```sh
python -B -m tools.parts --project my-board --boards 10 --spare-percent 10 --spare-minimum 3
```

For a guarded command-line update, use `--save-preferences`. It writes the same
fixed `docs/purchasing.json` as MCP and returns its SHA-256 in JSON output. First
creation needs no digest; an existing file requires its current `--expected-sha256`.
Supply a reviewed alternative file with `--preferences` to change supplier SKUs;
quantity options override its numbers. An outdated digest fails before writing.

```sh
python -B -m tools.parts --project my-board --save-preferences --boards 10 --format json
python -B -m tools.parts --project my-board --save-preferences --boards 12 --expected-sha256 CURRENT_FILE_SHA256 --format json
```

Reviewed project preferences can be committed as authored input. Keep temporary
experiments under ignored `build/` and pass their file with `--preferences`.

For fewer repeated edits in future designs, put the reviewed `PART_ID` and footprint
in your controlled symbol library, following the [library policy](LIBRARIES.md).
KiCad also supports project field-name templates in Schematic Setup, which can add
an empty `PART_ID` field automatically. User-wide templates live in Preferences.
These conveniences still require a real part selection; they do not validate it.
See [KiCad field-name templates](https://docs.kicad.org/10.0/en/eeschema/eeschema.html#field-name-templates).
Keep stock, price and lead-time observations in sourcing evidence rather than
embedding them as permanent library facts. Approved alternatives are recorded for
review; `tools.parts` never chooses one automatically.

## Review and upload

Each run creates a fresh receipt under ignored `build/parts/`. Use `--output` with
a fresh path under ignored `build/` to choose its location. The useful files are:

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

Upload `digikey.csv` to DigiKey myLists and map these columns:

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
describes its assembly multiplier and attrition features. This workflow generates
an upload file locally; it has no live account connection and does not confirm that
DigiKey accepted an upload. No add-on installation is required.

For a retained build or release, follow the [BOM policy](BOM_POLICY.md) and
[release workflow](RELEASE_READINESS.md). A working order checklist is not the
frozen, approved release BOM.

## Reuse evidence or automate

To reuse an existing native result, point to its project summary:

```sh
python -B -m tools.parts --project my-board --native-summary build/native/my-board/summary.json --format json
```

Replace the example path with the actual summary from your receipt. The tool
validates project identity, source hashes and native netlist evidence before using
it. Changed source requires a new capture. `--format json` is the agent/script
interface; parse its structured result instead of scraping terminal text. A review
returns exit code `0` when ready for order review and `1` when parts or evidence
need attention; invalid command arguments return `2`. A purchasing checklist does
not replace `tools.verify`, ERC/DRC review or the full shared gate after catalog or
tooling changes.

## Use the MCP workflow

The optional [local MCP adapter](MCP.md) exposes the same purchasing service.
Discover the selected board with `list_projects` and read this guide through
`read_document` using `parts-to-order`, or `kicad://docs/parts-to-order`.
`inspect_tool_surfaces` shows which CLI operations have MCP tools, their capability
gates and explicit reasons for CLI-only operations; its catalog is also available
through `python -B -m tools.surface`.

Call `prepare_parts` with `project_id` and a new `view_id`. Enable
`--allow-exports` and supply a checkout-relative `native_summary` to reuse saved
source-bound evidence without native execution. Keep `runner` at `auto` when
reusing a summary. If no summary is supplied, also enable `--allow-checks` for fresh
capture; choose `auto`, `local` or `container`. MCP always uses the fixed approved
runner selection and stores the new receipt at `build/parts/<view_id>`.

Optional `boards`, `spare_percent` and `spare_minimum` override the current run.
The default preferences file remains the selected project's
`docs/purchasing.json`. An alternate `preferences` path must be checkout-relative
and under that project's `docs/` as JSON, or a managed `build/` artifact. Use
`read_artifact` for the report and CSV files; open the generated `index.html` in a
browser to use its search and review links.

Enable `--allow-edits` for `save_parts_preferences`. Pass the selected `project_id`
and a typed `preferences` object in the format above. The tool writes only the
fixed `docs/purchasing.json` path in that island. Omit `expected_sha256` for its
first creation. For an update, read `docs/purchasing.json` with `read_project_file`,
review the saved values and pass the returned digest as `expected_sha256`.
Stale updates fail; the response includes the saved typed preferences and verified
readback digest. The ordinary preview/apply text-edit tools enforce the same
preferences schema.

A completed purchasing checklist keeps `purchase_authorized: false` and
`build_authorized: false`. It retains the native validation status separately, so
purchasing metadata may be ready while electrical validation still fails. The MCP
tools prepare local review files; they do not contact a supplier or place an order.
