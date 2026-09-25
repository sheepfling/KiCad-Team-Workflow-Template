# Find and import CAD for an exact part

Use the parts assistant to fetch an exact LCSC part, check its converted symbol,
footprint and paired 3D model, and add the library to your project. The current
provider is EasyEDA through the pinned community converter
[easyeda2kicad 1.0.1](https://pypi.org/project/easyeda2kicad/1.0.1/). No provider
account is required. This connection uses community web endpoints; availability
and CAD coverage are not a vendor service guarantee.

## One-time setup and everyday use

From the repository's Python environment, install the optional CAD importer:

```sh
python -m pip install -e '.[cad]'
python -B -m tools.parts --project my-board --assist
```

Replace `my-board` with your registered project ID. In **Find CAD for a part**:

1. Enter the exact LCSC number, such as `C2040`. If you know the manufacturer part
   number, enter it too; a mismatch blocks the fetch.
2. Select **Find CAD**. Review the provider-reported manufacturer, MPN, package,
   pin/pad checks, model limits and proposed files.
3. If the provider supplied STEP, select **Check STEP alignment**. Open the
   paired WRL/STEP views and compare the body, contacts, pin-one mark, height
   and pad placement. The gallery includes a disposable STEP assembly; it does
   not install STEP or approve mechanical fit.
4. Save and close the design in KiCad before **Add CAD to this project**. The
   importer adds the local libraries, their table entries and the project input
   inventory. It does not replace existing schematic symbols, pads or nets.
5. Reopen the project. Press **A** in KiCad's schematic editor and choose the exact
   symbol shown by the assistant. Its footprint is already assigned. **Update PCB
   from Schematic (F8)** brings that footprint to the board. Use KiCad to position
   and route it, then inspect the actual 3D view.

For a previously placed generic symbol, choose its intended manufacturer part and
review pin functions before replacing it. Equal pin numbers alone do not prove
that two symbols are electrically interchangeable. Imported CAD does not create an
approved purchasing catalog record; the existing [part review](PARTS_TO_ORDER.md)
and [BOM policy](BOM_POLICY.md) remain applicable.

## What the tool checks

The fetch checks the exact supplier ID against both provider identity fields and,
when supplied, the expected MPN. The converted symbol must retain that identity.
The importer checks file hashes, native CAD structure, symbol pin numbers against
numbered footprint pads, the paired model reference and project-relative paths.
Duplicate or ambiguous definitions, missing geometry and unsafe or changed files
block the import. These are consistency checks, not manufacturer pinout or
physical-fit approval.

The converter runs against frozen component and model source files with its
network access disabled. Its version and installed source hash are recorded.
Converted assets are cached by their source content; a normal repeat lookup checks
and reuses the same snapshot. A preview is bound to the current project and the
exact bundle bytes. Applying it does not contact the provider. An old preview or
changed source requires a fresh review, and existing library entries are preserved.

The current converter does not apply its WRL placement adjustment to STEP geometry.
The import therefore includes the paired **WRL visualization model** and keeps STEP
out of the installed library, preventing KiCad from silently substituting it.
Use **Check STEP alignment** to generate paired top, turned, bottom and angled
views from the exact cached WRL and raw STEP in the project's digest-pinned KiCad
version. It also exports a disposable board assembly and verifies that component
geometry appears in the STEP file. Open the gallery and inspect the model relative
to the pads; the command reports `REVIEW`, never automatic alignment approval.
The source footprint and the installed project library remain unchanged. A valid
export cannot prove manufacturer dimensions or physical fit. Docker and the pinned
KiCad image are required. See the
[converter implementation](https://github.com/uPesy/easyeda2kicad.py/blob/v1.0.1/easyeda2kicad/kicad/export_kicad_3d_model.py).

Source and licensing information travels with the library. The converter's software
license does not establish rights to every supplier CAD asset; no shared-library
or manufacturing approval is granted by import. Follow the [library policy](LIBRARIES.md)
when promoting project-local assets to a shared library.

## Agent use through MCP

Connect to this checkout using [the MCP setup](MCP.md). Enable exports to call
`source_cad(project_id, view_id, supplier_id, expected_mpn)`; the response contains
the exact frozen source and an import preview. A new provider fetch additionally
requires `--allow-downloads` at server startup. Without that flag, an intact
verified cached bundle remains available and a missing bundle returns `BLOCKED`.

Read the retained `cad-import.diff` and `cad-import-plan.json`. Use
`apply_cad_import(project_id, view_id, plan, expected_sha256)` with edits enabled
after reviewing the plan's SHA-256. `preview_cad_import` can make a fresh plan from
a saved `cad-source.json`. `check_step_alignment` accepts the same exact supplier
ID and can reuse a saved source report; it needs checks and exports and produces
paired views with the pinned KiCad image. Its `REVIEW` result requires visual
inspection. None of these tools chooses an electrical substitute or installs raw
STEP as the approved footprint model.

## Scripted use and recovery

```sh
python -B -m tools.parts --project my-board --check-step C2040 --expected-mpn RP2040
python -B -m tools.parts --project my-board --source-cad C2040 --expected-mpn RP2040 --format json
python -B -m tools.parts --project my-board --import-cad build/parts/REVIEW/cad-import-plan.json --apply --format json
```

Open `index.html` in the receipt printed by `--check-step`; inspect every paired
view and the disposable assembly before deciding whether the STEP model can be
used for mechanical work. `--check-step` has a nonzero exit if the exact source,
STEP file, pinned KiCad run or output evidence is unavailable.

Use the exact `plan_path` returned by `--source-cad`. Receipts and the immutable
cache stay under ignored `build/`; applied CAD becomes declared project-local
source. Add `--refresh-cad` to `--source-cad` or `--check-step` only when
intentionally requesting a fresh provider snapshot. It preserves older snapshots and still requires a new
preview before import.

If the provider is unavailable, an existing intact cache can still be used. A
missing or incompatible converter gives a setup command. A corrupt cache, identity
mismatch, absent model or pin mismatch stays blocked with a concrete finding;
the tool does not substitute a similarly named part or fabricate a model. Save the
receipt when reporting an issue. After importing, run
`python -B -m tools.verify --project my-board`; after using the part in a design,
run the selected native check and inspect the new BOM/3D outputs.

Other provider options and their connection state are recorded in the
[provider map](PARTS_PROVIDERS.md).
