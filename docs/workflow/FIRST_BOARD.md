# First board

This is the shortest path from a fresh fork to a checked project island. Use
[Start here](START_HERE.md) when adopting company licensing or production controls.

1. Install Python 3.11+, create a virtual environment and install `.[dev]` as shown
   in the [root setup](../../README.md#first-run-setup).
2. Check the workstation and initialize the fresh repository:

   ```sh
   python -B -m tools.template doctor
   python -B -m tools.template adopt --project-id my-hardware
   ```

3. Create the first standalone board and check native-runner availability:

   ```sh
   python -B -m tools.template new-project --project-id battery-board --kind pcb --toolchain kicad-10.0.5
   python -B -m tools.template doctor --native --toolchain kicad-10.0.5
   ```

4. Create and save the design under `projects/battery-board/kicad/`. Complete its
   `project.json`, `tests/contract.json` and design notes; the generated skeleton is
   intentionally incomplete and fails until it describes the real board. Development
   and production contracts allow no ignored ERC or DRC checks. For a `pcb` project,
   KiCad 10.0.5 may initially ignore `single_global_label`, `four_way_junction`,
   `simulation_model_issue` and `footprint_filter`; enable them through Schematic
   Setup before the first native run. KiCad may also initially ignore
   `missing_courtyard`, `track_not_centered_on_via`, `tuning_profile_track_geometries`,
   `footprint_filters_mismatch` and `footprint_type_mismatch`; enable them through
   Board Setup before the first native run. Do not copy any defaults into the contract
   to make a development board pass. A `pcb_only` project has no schematic or ERC
   lane, so it needs the Board Setup changes only.

   A legacy `.kicad_pcb` with no matching schematic can instead use `--kind pcb_only`
   or the import command. That is a not-for-manufacture capture lane with DRC/layout
   checks; add an authoritative schematic and migrate it to `pcb` before product or
   manufacturing work.
5. Run the fast island check, then the pinned native check:

   ```sh
   python -B -m tools.ci --project battery-board
   python -B -m tools.ci --kicad --project battery-board --output projects/battery-board/build/review-001
   ```

   If a check fails, run `python -B -m tools.template diagnose --project-id battery-board`
   and follow [the repair guide](DIAGNOSTICS.md). Add the native
   project's `summary.json` with `--native-report` to explain ERC, DRC and contract
   failures.

6. Commit only authored source, push a short-lived branch and open a pull request.
   Review the exact Actions commit and retained evidence before merging.

The first passing check establishes a development baseline. Promotion to a prototype,
pilot or production release requires [release readiness](RELEASE_READINESS.md), real
reviewers and durable [release storage](RELEASE_STORAGE.md).
