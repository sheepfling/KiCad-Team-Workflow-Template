# Find and import CAD for an exact part

Use the parts assistant to fetch an exact LCSC part, check its converted symbol,
footprint and paired 3D model, and add the library to your project. The current
provider is EasyEDA through the pinned community converter
[easyeda2kicad 1.0.1](https://pypi.org/project/easyeda2kicad/1.0.1/). No provider
account is required. This connection uses community web endpoints; availability
and CAD coverage are not a vendor service guarantee.

## First part: run the assistant

Complete [first-run Python setup](../../README.md#first-run-setup) from the
repository root. The `cad` extra is required; the README's `.[dev,cad]` command
installs it. You also need a registered board. Find its exact ID with:

```sh
python -B -m tools.template list --format text
```

If that command lists no projects, [create a board](FIRST_BOARD.md) or
[import an existing design](IMPORT_WORKFLOW.md) first. Replace `my-board` below
with the listed ID. Start the local page with one command:

```sh
python -B -m tools.parts --project my-board --assist
```

The page opens in your browser. If it does not, open the loopback URL printed
by the command. Keep the terminal open while using it. The STEP
comparison also needs Docker Desktop or Docker Engine running; check the daemon
with `docker info`. The first comparison may download the project's pinned KiCad
image. CAD lookup and library import can run without Docker; other native
board checks may need Docker or an exact local KiCad CLI.

In **Find CAD for a part**:

1. Enter an exact LCSC number, such as `C2040`. If you know the manufacturer's
   part number, enter it too. **Find CAD** checks the supplier identity, pin/pad
   consistency and proposed project files.
2. Read the reported manufacturer, MPN, package and source limits. A mismatch or
   incomplete CAD stays blocked. A ready review enables the next two buttons.
3. Select **Check STEP alignment** when the provider has a STEP file. The page
   shows paired WRL/STEP top, turned, bottom and angled views on the same
   disposable footprint. Compare body, contacts, pin-one mark, height and pad
   placement; open the full-page comparison for larger views and its disposable
   STEP assembly. `REVIEW` means your visual check is still needed.
4. Save and close the design in KiCad, then select **Add CAD to this project**.
   This adds project-local libraries and table entries. It does not replace
   existing schematic symbols, pads or nets.
5. Reopen the project. Press **A** in KiCad's schematic editor, choose the exact
   imported symbol, and wire it. **Update PCB from Schematic (F8)** brings its
   assigned footprint to the board. Position and route it, inspect the actual
   board in KiCad's 3D viewer, and run the selected native check.

If STEP is unavailable, its comparison reports `BLOCKED`; a complete WRL library
can still be imported for visualization. The tool never installs an unreviewed
STEP model or approves mechanical fit. Follow the [3D board workflow](THREE_D_WORKFLOW.md)
for the placed-board handoff.

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

Connect to this checkout using the [first-part MCP setup](MCP.md#first-part-through-mcp).
Enable exports to call
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

## Command-line use and recovery

For a source-bound STEP comparison without opening the assistant:

```sh
python -B -m tools.parts --project my-board --check-step C2040 --expected-mpn RP2040
```

The command prints the fresh ignored `build/parts/` receipt and its `index.html`
gallery. It exits nonzero if the exact source, STEP file, pinned KiCad run or
output evidence is unavailable. Use `--format json` for a typed report with
source hashes, command evidence, artifact hashes and explicit false values
for `alignment_verified` and `physical_fit_verified`.

To preview a project-library import from a terminal, run:

```sh
python -B -m tools.parts --project my-board --source-cad C2040 --expected-mpn RP2040
```

Read its exact source diff and run the `Then:` command it prints to apply the
locked plan. Do not type an example plan path or edit the generated plan. The
normal lookup reuses an intact frozen cache when available. Use `--refresh-cad`
with `--source-cad` or `--check-step` only when intentionally requesting a fresh
provider snapshot; it preserves older snapshots and requires another review.

| If you see                                 | Next step                                                                                                                   |
| ------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------- |
| No project ID in `tools.template list`     | Create or import a board; this command needs a registered island.                                                           |
| `Find CAD` reports a converter setup issue | Activate the repository Python environment and install `.[dev,cad]` from the root.                                          |
| Exact LCSC/MPN mismatch or missing model   | Check the chosen part number against its manufacturer data. The tool will not substitute another part or invent geometry.   |
| STEP review reports no source STEP         | Use the WRL model for visualization if its library plan is ready; obtain a reviewed STEP model before a mechanical handoff. |
| Pinned KiCad command fails                 | Run `docker info`, start Docker if needed, and open the named `*.command.json` in the printed receipt.                      |
| A source or cache changed after review     | Find the exact part again, inspect the new report, and repeat the review.                                                   |

After importing, run `python -B -m tools.verify --project my-board --depth native`.
Run it again after placing the part on the PCB, and inspect the actual board's
new BOM and 3D outputs. Keep run receipts under ignored `build/` and
durable design decisions under the project's `docs/` directory.

Other provider options and their connection state are recorded in the
[provider map](PARTS_PROVIDERS.md).
