# First board

This is the shortest path from a fresh fork to a checked project island. Use
[Start here](START_HERE.md) when adopting company licensing or production controls.

1. Install Python 3.11+, create a virtual environment and install `.[dev]` as shown
   in the [root setup](../../README.md#first-run-setup).
2. Check the workstation and initialize the fresh repository:

   ```sh
   python -B -m tools.template doctor --format text
   python -B -m tools.template adopt --project-id my-hardware --format text
   ```

3. Create the first standalone board and check native-runner availability:

   ```sh
   python -B -m tools.template list --format text
   python -B -m tools.template new-project --project-id battery-board --kind pcb --toolchain kicad-10.0.5 --format text
   python -B -m tools.template doctor --native --toolchain kicad-10.0.5 --format text
   ```

   `list` reports the available toolchain IDs before creation. After saving the
   board, its `INPUTS_PRESENT` state means only that declared files were found;
   it is not an electrical or manufacturing approval.

4. Create and save the design under `projects/battery-board/kicad/`. Complete its
   `project.json` and design notes. Before authoring electrical expectations, use
   the exact catalogued KiCad toolchain to capture an **UNREVIEWED** netlist inventory:

   ```sh
   python -B -m tools.contract_coach --project-id battery-board --capture --format text
   ```

   The command creates a fresh ignored `build/contract-coach/` receipt. `--runner auto`
   (the default) uses the exact local KiCad CLI when available, otherwise the
   catalogued digest-pinned Docker image. Use `--runner local --cli /path/to/kicad-cli`
   to insist on a local installation or `--runner container` to insist on Docker.
   The receipt retains all version probes, the export command with stdout/stderr,
   source hashes, netlist and full text/JSON inventory. The container mounts
   authored source read-only and writes only the ignored receipt.
   Compare observed components, pins, nets and `PART_ID` values with requirements
   and the schematic. Then independently author `tests/contract.json`; the coach
   never writes it. An empty authored contract does not block this capture.

   The generated skeleton is intentionally incomplete and fails until it
   describes the real board. Development
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
   python -B -m tools.template list --format text
   python -B -m tools.ci --project battery-board --format text
   python -B -m tools.ci --kicad --project battery-board --output projects/battery-board/build/review-001 --format text
   ```

   If a check fails, run `python -B -m tools.template diagnose --project-id battery-board`
   and follow [the repair guide](DIAGNOSTICS.md). Add the native
   project's `summary.json` with `--native-report` to explain ERC, DRC and contract
   failures. To compare an existing native netlist with the authored contract,
   use:

   ```sh
   python -B -m tools.contract_coach --project-id battery-board --native-summary projects/battery-board/build/review-001/battery-board/summary.json --format text
   ```

   That command verifies the selected project, netlist artifact and current design
   hashes before showing differences. Add `--detail full`, `--format json`, or a
   new `--output build/contract-coach/review-001` receipt when more detail is needed.

6. Commit only authored source, push a short-lived branch and open a pull request.
   Review the exact Actions commit and retained evidence before merging.

The first passing check establishes a development baseline. Promotion to a prototype,
pilot or production release requires [release readiness](RELEASE_READINESS.md), real
reviewers and durable [release storage](RELEASE_STORAGE.md).
