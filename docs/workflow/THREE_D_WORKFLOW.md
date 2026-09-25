# 3D views and mechanical exports

Use a 3D view to inspect board orientation, component placement and the model
coverage of a PCB. Generate review images and mechanical exchange files from the
same committed KiCad source as the electrical checks. They are outputs, not a
second editable copy of the design.

For a named KiCad assembly population, add `--assembly-variant 'Pilot A'` to
`tools.visualize --project <id>`. The name must be declared in the project's
`.kicad_pro`; the top/angled images and STEP/GLB commands then use the same
population selection and record it in the JSON receipt. Review the fitted model
set against the native BOM and placement file before a mechanical handoff.

## Populate a board's 3D models

1. Choose a model that matches the reviewed component package. A missing model
   can leave a correctly placed footprint looking like a bare pad in a render.
   Check the package identity and dimensions; do not select a convenient model
   merely because it makes the picture look complete. For a model used only by
   this board, put the source model under
   `projects/<id>/kicad/models/`; the board will reference it with a path such
   as `${KIPRJMOD}/models/connector.step`. For a model reused by several boards,
   put it under a registered `libraries/<library-id>/` directory and declare
   that library in each consumer's `project.json`. Before mapping a newly added
   shared model, add its repository-relative path to `shared_inputs` in every
   **other** consumer's manifest. The map command adds it to the selected
   board's manifest. If another consumer is missing it, the plan and apply
   both stop and name each manifest and exact path to add. Run the full
   `python -B -m tools.ci` gate after the shared-library change. The
   [library policy](LIBRARIES.md) gives the shared-dependency and provenance
   requirements.
2. Use the draft-map flow below to assign explicit model paths to placed
   footprints. The command adds each chosen file to the board's `required_inputs`
   or `shared_inputs` list and previews the exact source changes before applying.
3. Run the selected native check and generate a new view:

   ```sh
   python -B -m tools.visualize --project battery-board --check-models --format text
   python -B -m tools.verify --project battery-board --depth native
   ```

   The model check inspects references and inventory without running a 3D export.
   Its JSON report lists matching, declared in-repository model assets as candidates
   for unassigned footprints. Verify package identity and dimensions before
   attaching one in KiCad; a filename match is only a suggestion.
   A VRML-only assignment is flagged for STEP review because the mechanical
   export needs a same-name STEP/IGES model to represent that component.
   An IDF-only assignment is also flagged: IDF can serve a separate mechanical
   handoff, but it does not provide a body for these 3D views and exports.
   It cannot prove that a model has the correct dimensions or even that the
   intended component is represented. If a path is missing or machine-specific,
   fix the authored footprint/board reference and manifest; do not patch an
   exported picture. Use `tools.template diagnose --project-id battery-board`
   for the broader project repair queue.

You can also make an assignment or adjust its scale, rotation and offset directly
in the registered `.kicad_pro` with the exact catalogued KiCad version. Use PCB
Editor's footprint **3D Models** settings, save, and close KiCad before running
the checks. For this manual route, add the model file to `project.json`
`required_inputs` (or the complete shared-library declarations) yourself. The
map command refuses to overwrite an existing assignment.

If you already have an approved model file under this project's declared source
root or a declared shared-library root, the CLI can populate an unassigned
placed footprint without hand-editing its PCB text or `project.json`. Start with
an ignored draft map; the tool fills in the current board and manifest hashes,
all unassigned references, and any candidate paths it found:

```sh
python -B -m tools.visualize --project battery-board --init-model-map build/model-map.json
```

Edit the draft map to keep only the references that need a model, and enter each
reviewed path. The draft starts with empty model paths and cannot be applied as
is. Its shape is:

```json
{
  "schema_version": "1",
  "project_id": "battery-board",
  "board_sha256": "<generated 64-character SHA-256>",
  "manifest_sha256": "<generated 64-character SHA-256>",
  "assignments": [
    {
      "reference": "J1",
      "model": "projects/battery-board/kicad/models/connector.step",
      "candidate_assets": []
    }
  ]
}
```

Use the actual reference and repository-relative source model path. The command
does not copy, download or select a model based on a matching filename. Keep a
vendor model's origin and redistribution rights review with the source decision.
The tool accepts STEP/STP/IGS/IGES/WRL, but rejects IDF for this view workflow.

```sh
python -B -m tools.visualize --project battery-board --map-models build/model-map.json
# Read board.diff and manifest.diff in the new ignored receipt, then use its locked map.
python -B -m tools.visualize --project battery-board --map-models build/diagnostics/<receipt>/locked-model-map.json --apply
python -B -m tools.verify --project battery-board --depth native
python -B -m tools.visualize --project battery-board
```

The first command is read-only and shows the exact proposed board and manifest
diff, both in its ignored receipt and in `--format json` stdout. It also writes a
`locked-model-map.json` containing SHA-256 hashes of the chosen model files.
The text report gives the exact next command; use that receipt's locked map with
`--apply`. The original draft cannot be applied. If a model file, board or manifest
changes after the plan, create and review a fresh plan. `--apply` requires
matching source hashes and a unique unassigned reference, then inserts the portable
`${KIPRJMOD}` path in that placed footprint and adds the asset to the proper
manifest input list. It refuses to replace any existing model assignment, so
reviewed offsets and rotation cannot be silently lost. Applying a path does **not** check
the model's package identity, dimensions, alignment, side or actual geometry;
inspect the PCB Editor 3D view and the exported images and STEP before accepting
the mechanical handoff. The tool uses neutral zero offset/rotation and unit scale,
so use PCB Editor for a model requiring a fit adjustment. KiCad's
[PCB Editor guide](https://docs.kicad.org/10.0/en/pcbnew/pcbnew.html) covers 3D
model settings; the [CLI guide](https://docs.kicad.org/10.0/en/cli/cli.html)
documents the native export commands.

The pinned KiCad installation may provide its own standard 3D model library.
Keep references to that library versioned, for example with its
`KICAD10_3DMODEL_DIR` variable for a KiCad 10 project. A model downloaded to a
personal folder is not a portable dependency. Check redistribution terms before
adding a vendor model to the repository.
The template's current digest-pinned KiCad 10.0.5 container does not include the
stock KiCad 3D-model library. A stock-library reference is therefore marked for
review, and a hosted export can omit that body. For reliable hosted views, add
reviewed project-local or declared shared model assets, or deliberately extend and
pin the native image with the approved model package.

## Generate views and exchange files

From the repository root, select one registered PCB project:

```sh
python -B -m tools.visualize --project battery-board --format text
python -B -m tools.visualize --project battery-board --runner container --output build/3d-review-001 --format json
```

The command uses an exact local KiCad CLI when available or the project's pinned Docker image
(`--runner auto`); `--runner local` or `--runner container` makes the choice explicit. The report
names the fresh ignored receipt and generated files. Use `--format text` for a short engineer-facing
account and `--format json` for the structured agent/script result. Add `--detail full` to expand
every model finding in text; JSON always contains the complete inventory. The export includes board
images for visual review, a STEP model for mechanical CAD and a GLB model for 3D viewing. Open the
files and inspect them; a successful command exit only means KiCad produced them.

For a hosted one-board run, open **Actions → KiCad 3D preview → Run workflow** and
enter the registered PCB project ID. That manual job uses the project's pinned
container and uploads its full receipt, including failure logs. Routine PR and
push CI stays focused on electrical and repository checks; 3D rendering does not
add time to every board lane.

The command does not modify the KiCad source. Keep its PNG, STEP and GLB files,
logs and model audit under ignored `build/` or retained CI/release evidence. Do
not force-add a generated view or exchange model to Git. A separately authored
mechanical model or drawing may be controlled source when its origin, revision
and ownership are recorded; see [repository hygiene](REPOSITORY_HYGIENE.md).

## Review what the export cannot decide

Compare top and angled views with the PCB and the actual component packages.
Look for missing or floating bodies, wrong-side parts, reversed connectors,
incorrect offsets, enclosure interference and unexpected board thickness.
Compare the STEP exchange with the reviewed coordinate origin and interface
record in the [mechanical handoff](MECHANICAL_HANDOFF.md). A generated model does
not certify a mating connector, tolerances, thermal clearance, enclosure fit or
fabrication readiness. Record decisions and measurements in the board's
`projects/<id>/docs/`; keep disposable renders and run logs in `build/`.

For a project with no assigned 3D models, the command can still render the PCB
and create exchange files. Treat that as an incomplete assembly view, not a
passing model-coverage claim. Add reviewed models where they matter to the
mechanical handoff, then regenerate from the updated source.
