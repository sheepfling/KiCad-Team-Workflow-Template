# Grounding, power and high-frequency analysis

Use these checks in priority order: grounding connectivity, startup/steady-state
power, then high-frequency circuit response. Each board owns independent limits
and reviewed models. The tools never infer a ground pin, current rating, model
approval or an acceptable waveform from an observed export.

## Quickstart

Start in a registered board's repository with the Python environment from
[setup](START_HERE.md). Discover its ID with `kicad-team template list --format text`.
Replace `my-board` and model paths below with that board's actual values.

1. Create a connected starter:

   ```sh
   kicad-team electrical --project my-board --init
   ```

   This creates `tests/electrical.json` in the project island and connects it from
   `tests/contract.json`. Existing electrical requirements are never overwritten.
   All three sections start as `pending`; verification fails until each is completed.
   The simulator version starts as `UNREVIEWED`. If already selected by the engineer,
   pass `--ngspice-version 47` to record that exact choice during initialization.

2. Author requirements in priority order: ground pins, power, then high frequency.
   Use the [complete synthetic example](../../templates/electrical/README.md) to learn
   the fields. Keep reviewed decks and includes under the project's `tests/electrical/`.
   Set each applicable section to `required`; use `not_applicable` only with an
   engineering reason. Leaving a section pending cannot yield a partial pass.
   For a deliberate grounding-only scope, explicitly justify why the other two
   sections do not apply. Grounding-only analysis does not require ngspice.

3. Capture the files for model review:

   ```sh
   kicad-team electrical --project my-board --capture-inputs \
     --model projects/my-board/tests/electrical/startup.cir \
     --model projects/my-board/tests/electrical/signal.cir
   ```

   The command prints a fresh `build/electrical-inputs/` receipt and file counts.
   Repeat `--model` for every deck and include. Without `--model`, it captures the
   model inventory already named in the contract. `inputs.json` contains actual
   design/model SHA-256 values with status `UNREVIEWED`. Review the circuit mapping
   and assumptions, then copy `source_sha256` and the applicable `model_sha256`
   entries into each case. Capture never edits approved hashes or engineering limits.

4. Check readiness and run the complete verification:

   ```sh
   kicad-team template doctor --electrical --project-id my-board --format text
   kicad-team verify --project my-board --depth electrical
   ```

   Doctor checks the contract, bindings, exact KiCad runner and exact host ngspice
   version. It runs no circuit. Use `--ngspice /path/to/ngspice` on both commands
   when the selected simulator is outside `PATH`; `--runner container` selects
   pinned KiCad while the simulator still runs on the host. Fix the first reported
   prerequisite before running verification.

Text output summarizes status and prints the receipt path. `kicad-team electrical`
adds `--detail full` for every check; `--format json` always preserves all findings.
For scripting, setup exits `0` with `CREATED`, input capture exits `0` with
`UNREVIEWED`, and analysis exits `0` only with `PASS`. These setup statuses are not
analysis results. Analysis failure exits `1`; invocation/setup errors exit `2`.

## Commands and scope

| Command                                                                                   | Evidence produced                                                                                                 |
| ----------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| `kicad-team electrical --project <id> --init`                                             | Connected pending contract; no invented requirements                                                              |
| `kicad-team electrical --project <id> --capture-inputs`                                   | UNREVIEWED hashes for design and already-declared models; no contract edits                                       |
| `kicad-team template doctor --electrical --project-id <id> --format text`                 | Contract, native runner and host simulator readiness; no simulation                                               |
| `kicad-team verify --project <id>`                                                        | Portable requirements, reviewed model/source bindings and simultaneous power budgets; no circuit simulation       |
| `kicad-team verify --project <id> --depth native`                                         | The portable lane plus ERC/DRC and configured grounding checks on the actual exported netlist                     |
| `kicad-team verify --project <id> --depth electrical --ngspice /path/to/ngspice`          | Native verification followed by every configured power and high-frequency simulation                              |
| `kicad-team electrical --project <id> --format json`                                      | Focused electrical run with an exact-version native netlist capture and an ngspice run; this does not run ERC/DRC |
| `kicad-team electrical --project <id> --native-summary build/<receipt>/<id>/summary.json` | Reuse an existing netlist only after checking its project, toolchain, source hashes and artifact hashes           |
| `kicad-team ci --electrical --project <id>`                                               | Separate electrical CI gate; the usual project/product/tag selectors apply                                        |

`kicad-team electrical` accepts `--runner auto|local|container` for netlist capture.
Its `--ngspice` argument selects the simulator executable, whose exact version must
match the contract. Container selection applies to KiCad; ngspice runs on the host.
Install the approved ngspice version on that runner before requesting the electrical
gate. Ordinary portable CI does not require a simulator. A requested electrical
run with no contract or no required runner exits nonzero, never a simulated pass.
Without include selectors, `kicad-team ci --electrical` requests every discovered board;
select a project or tag when only part of the repository has electrical contracts.

## Add a board contract

1. Complete the independent components/nets in `tests/contract.json`. An electrical
   analysis requires an authoritative schematic (`pcb` or `schematic` kind).
2. Run `kicad-team electrical --project <id> --init` to add the sidecar and its pointer.
   The pointer is relative to the project island; initialization preserves the
   existing native expectations and refuses to replace electrical requirements.
3. Author `tests/electrical.json` with `schema_version: "1"`, the exact `project_id`,
   `ngspice_version`, and all three sections: `grounding`, `power`, `high_frequency`.
   Each section begins with `mode: "pending"` and a completion `reason`. Replace
   it with `mode: "required"` and the fields below, or `mode: "not_applicable"`
   with a substantive engineering `reason`. Pending sections block verification.
4. Keep model decks and their dependencies with the project, for example under
   `tests/electrical/`. Model and design hash keys are repository-relative, unlike
   the contract pointer. Shared models must also be explicitly declared shared inputs.
5. Run the selected portable, native and electrical checks. Inspect the retained
   waveforms and findings, then review the limits and model scope with the engineer.

The authoritative schema is `ElectricalAnalysisContract` in
[models.py](https://github.com/sheepfling/KiCad-Tooling/blob/codex/tooling-split/kicad_tooling/hwrepo/models.py).
`kicad-team hardware generate` exports its machine-readable schema to ignored
`schemas/electrical-analysis-v1.schema.json`. The
[standalone examples](../../templates/electrical/README.md) contain a complete worked JSON contract
and SPICE decks, with intentionally invalid placeholder hashes. These demonstrate the tools; they
are not design requirements for an adopted board. Do not copy their limits or ground-net choices
into a real design.

## Priority 1: grounding

A required section contains `basis`, `domains` and optional `exempt_components`.
Each domain declares its exact `net` and complete `pins`, using `Reference.Pin`
notation. Use normalized net names without the leading slash, consistent with the
existing native contract. Hierarchical names retain their internal slashes.

The checker rejects missing pins, unexpected pins on the ground net, a pin appearing
on another net, unknown components, conflicting exemptions, and components that have
neither ground-pin coverage nor an explicit exemption reason. Separate analog,
digital, chassis and protective-earth domains remain separate declarations. Never
merge them or exempt a component solely to make the check pass.

Coverage means an engineer enumerated the necessary pins. It cannot discover an
omitted ground pin from a datasheet. ERC/DRC and schematic parity remain mandatory
native checks. Return-plane continuity, via placement, high-current return routes,
net-tie/bond implementation and physical earth continuity still require layout and
hardware review. A schematic label alone does not establish any of those properties.

## Priority 2: power

A required section contains `rails`, `startup` and `steady_state`.
Each rail records `id`, `basis`, `voltage_v`, `continuous_limit_a`, `peak_limit_a`,
`peak_duration_limit_s` and `loads`. Each load records `id`, `basis`, `steady_a`,
`startup_a` and `startup_s`. Limits must represent the reviewed, derated weakest
supply/connector/wire/trace/protection path, including the intended ambient conditions.

Budgets sum all simultaneous steady loads and sum each load's greater startup or
steady demand. If that peak exceeds the continuous limit, the longest startup
must fit the declared peak-duration limit. This is conservative simultaneous-start
budgeting; sequencing, repeated starts, protection curves, thermal accumulation and
shared upstream supplies require appropriate additional cases and engineering analysis.
Calculated watts use the declared nominal rail voltage and do not establish thermal margin.

Both startup and steady state need transient simulations. Every startup case must
measure peak current; every steady-state case must measure average current and
power. Add voltage sag, overshoot and other limits as measurements. The steady-state
window is explicitly chosen by the engineer; the tool does not prove that the
circuit has settled. Include source impedance, input ramps, bulk capacitance, load
steps, regulator behavior and the applicable component tolerances in reviewed models.

## Priority 3: high frequency

A required section contains `basis`, `frequency_hz`, `rise_time_s`, `sweeps` and
`waveforms`. Use AC sweeps for modeled gain/phase response and transient cases for
edge behavior, ringing and overshoot. SPICE voltage/current sources in the deck can
supply pulse, sinusoidal and other stimuli; the waveform artifact records the result.

The transient maximum step must provide at least ten samples per declared rise time
and twenty per nominal cycle, with a run of at least two cycles. These are minimum
sampling guards, not a convergence proof. Review tighter steps, wider sweeps and
corner cases where needed. Use transmission-line, parasitic and appropriate device
models for the effects being assessed. A schematic RC model does not evaluate PCB
stackup, extracted coupling, plane return paths, antenna behavior or EMC compliance.
This implementation does not perform field solving or PCB parasitic extraction.

## Simulation cases and measurements

Every case includes:

- `id`, `basis`, `deck` and `analysis` (`tran` or `ac`). Case IDs must be unique.
- `source_sha256`: the exact current declared design inventory and SHA-256 hashes.
- `model_sha256`: the deck and every included model file with reviewed SHA-256 hashes.
- `measures`: independently authored acceptance checks, never fitted to observed output.

A transient case adds `step_s` and `stop_s`; the runner caps the internal step too.
An AC case adds `start_hz`, `stop_hz` and `points_per_decade` (at least ten).
Each measurement has an `id`, `expression`, `statistic` (`min`, `max`, `avg`, `rms`,
`pp`), `unit`, `start`, `stop`, and at least one of `minimum` or `maximum`.
Window units are seconds for transient analysis and hertz for AC analysis.
Measurement units are declared by the engineer; dimensional correctness of arbitrary
SPICE expressions is not inferred. Examples:

| Meaning                                 | Expression            | Statistic      | Unit |
| --------------------------------------- | --------------------- | -------------- | ---- |
| Current drawn from voltage source Vrail | `-i(vrail)`           | `max` or `avg` | `A`  |
| Power supplied at node supply           | `-v(supply)*i(vrail)` | `avg`          | `W`  |
| Minimum rail voltage                    | `v(out)`              | `min`          | `V`  |
| Transfer gain                           | `db(v(out)/v(in))`    | `min` or `max` | `dB` |
| Peak output voltage                     | `v(out)`              | `max`          | `V`  |

The source-current sign convention must match the model. AC sources must have the
appropriate small-signal amplitude. Expressions use a restricted single-line SPICE
syntax; unsupported node names may need a reviewed alias in the simulation model.

Decks are reviewed model-only inputs: the first line is the SPICE title; ordinary
elements and `.model`, `.subckt`, `.ends`, `.param`, `.func`, `.global`, `.ic`,
`.nodeset`, `.option`/`.options`, `.temp`, `.include`/`.inc` are supported.
A final `.end` is optional. Includes use portable paths relative to the including
file, cannot traverse to a parent directory, and must be listed in `model_sha256`.
The runner expands them into one retained deck. `.lib` sections, embedded `.control`
blocks and analysis directives are rejected; extract the reviewed model section or
move analysis settings into the contract. This restricted adapter is not a general
sandbox for executing untrusted third-party models.

Binding a deck to design hashes is an explicit review record, not an automatic
proof that the deck faithfully represents that design. Review the circuit-to-model
mapping, excluded components, tolerances and assumptions in `basis` and local docs.
When a design/model changes, review that mapping and update the hashes intentionally.
The tool refuses stale hashes and does not rewrite them to make a run pass.

## Charts and structured data from a saved run

The [pinned environment](../../README.md#first-run-setup) includes chart support. Matplotlib uses
a noninteractive
[Agg/SVG backend](https://matplotlib.org/stable/users/explain/figure/backends.html), so the same
command works on a desktop or in hosted CI. After an analysis run, pass its printed receipt
directory (or its `electrical.json`) to:

```sh
kicad-team electrical-charts --receipt build/electrical/<id>-<run> --format text
```

This reads the saved requirements and ASCII ngspice waveforms. It verifies their
recorded SHA-256 hashes and writes a **new** ignored `build/electrical-charts/`
receipt with one PNG, SVG and full precision CSV per simulation case. CSV columns
include time or frequency, every retained signal, and both real and imaginary AC
components. Charts show the declared measurement windows and limits; the AC case
also shows phase when a trace represents a clear voltage/current ratio. The
receipt includes `grounding.csv` for declared pin coverage, `power.csv` for the
rail budgets, and `charts.json` tying the generated files to the input report.
Run `--format json` for a typed script interface. The export invokes neither
KiCad nor ngspice, and it does not modify the analysis receipt. A failed
simulation may leave some cases without waveforms; the chart report calls them
`SKIPPED` and returns a partial status. A changed or unrecorded waveform is a
failure, not chart input.

For a saved focused suite from `kicad-team ci --electrical`, use
`kicad-team electrical-charts --suite build/electrical-suite.json`; it exports every
project to a single new chart suite receipt. The manual **Electrical analysis**
GitHub Action runs this step automatically and retains the charts with the
analysis evidence. Charts visualize the declared circuit model and limits; they
do not establish physical grounding, thermal or RF acceptance.

## Hosted electrical check

The manual GitHub Actions workflow **Electrical analysis** accepts a registered
`project_id`, `ngspice_version` and the reviewed `ngspice_sha256` of that version's
source archive. The defaults are version `47` and its recorded archive checksum.
The simulator version must match the board contract; when changing versions,
review and update the checksum as a pair. The workflow checks portable requirements,
builds ngspice from the checksum-verified official source archive, runs electrical
and native readiness checks, then calls `kicad-team ci --electrical --project <id>`.
It retains reports, waveforms, charts, CSV data and simulator build logs even after failure.

This focused workflow checks declared grounding and circuit models. Run the normal
**KiCad template acceptance** native lane for ERC/DRC as well, or use
`kicad-team verify --depth electrical` locally to combine both. The manual electrical
workflow does not add a required branch-protection check or change ordinary PR
runs. Adopt those enforcement decisions through the repository's review process.

## Receipts and acceptance

Each focused run creates fresh ignored `build/electrical/` evidence containing
`electrical.json`, `electrical.txt`, the requirements snapshot, native netlist
evidence, simulator version/command receipts, generated decks and ASCII
`waveforms.raw` files. Combined verification keeps these in its existing diagnostic
receipt. Reports bind all inputs and retained artifacts with SHA-256 hashes.
A timeout, version mismatch, missing/non-finite measurement, simulator error,
truncated waveform or uncovered measurement window fails the requested analysis.
Failed cases retain their command output; subsequent independent cases still run.

Portable PASS means requirements and budgets checked. Native PASS includes the
configured schematic-ground check. Only electrical PASS means every requested
simulation ran and met its declared limits. Existing manufacturing/release approval
still needs the project's engineering evidence review; electrical receipts are not
added automatically to a release package or made a new release-policy prerequisite.
Use the combined electrical command as an explicit review/CI gate where required,
and retain its receipt with the board review. Bench startup, sustained thermal load,
high-frequency measurements and physical grounding acceptance remain separate work.

The simulator behavior is documented in the
[ngspice manual](https://ngspice.sourceforge.io/docs.html) and the
[KiCad simulator guide](https://docs.kicad.org/10.0/en/eeschema/eeschema.html#simulator).

The local MCP adapter exposes `export_electrical_charts(view_id, receipt)` and
`export_electrical_chart_suite(view_id, suite)` for the same saved analysis receipts.
Both require exports capability and write fresh ignored outputs. Install the pinned
`charts` extra for waveform plots; CSV tables keep the original numeric precision.
The chart status preserves missing or failed simulation evidence.
