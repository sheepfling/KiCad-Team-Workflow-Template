# Grounding, power and high-frequency analysis

Use these checks in priority order: grounding connectivity, startup/steady-state
power, then high-frequency circuit response. Each board owns independent limits
and reviewed models. The tools never infer a ground pin, current rating, model
approval or an acceptable waveform from an observed export.

## Commands and scope

| Command | Evidence produced |
| --- | --- |
| `python -B -m tools.verify --project <id>` | Portable requirements, reviewed model/source bindings and simultaneous power budgets; no circuit simulation |
| `python -B -m tools.verify --project <id> --depth native` | The portable lane plus ERC/DRC and configured grounding checks on the actual exported netlist |
| `python -B -m tools.verify --project <id> --depth electrical --ngspice /path/to/ngspice` | Native verification followed by every configured power and high-frequency simulation |
| `python -B -m tools.electrical --project <id> --format json` | Focused electrical run with an exact-version native netlist capture and an ngspice run; this does not run ERC/DRC |
| `python -B -m tools.electrical --project <id> --native-summary build/<receipt>/<id>/summary.json` | Reuse an existing netlist only after checking its project, toolchain, source hashes and artifact hashes |
| `python -B -m tools.ci --electrical --project <id>` | Separate electrical CI gate; the usual project/product/tag selectors apply |

`tools.electrical` accepts `--runner auto|local|container` for netlist capture.
Its `--ngspice` argument selects the simulator executable, whose exact version must
match the contract. Container selection applies to KiCad; ngspice runs on the host.
Install the approved ngspice version on that runner before requesting the electrical
gate. Ordinary portable CI does not require a simulator. A requested electrical
run with no contract or no required runner exits nonzero, never a simulated pass.
Without include selectors, `tools.ci --electrical` requests every discovered board;
select a project or tag when only part of the repository has electrical contracts.

## Add a board contract

1. Complete the independent components/nets in `tests/contract.json`. An electrical
   analysis requires an authoritative schematic (`pcb` or `schematic` kind).
2. Add `"electrical": "tests/electrical.json"` alongside `validation` in that file.
   This pointer is relative to the project island.
3. Author `tests/electrical.json` with `schema_version: "1"`, the exact `project_id`,
   `ngspice_version`, and all three sections: `grounding`, `power`, `high_frequency`.
   Each section has `mode: "required"` and the fields below, or
   `mode: "not_applicable"` with a substantive engineering `reason`.
4. Keep model decks and their dependencies with the project, for example under
   `tests/electrical/`. Model and design hash keys are repository-relative, unlike
   the contract pointer. Shared models must also be explicitly declared shared inputs.
5. Run the selected portable, native and electrical checks. Inspect the retained
   waveforms and findings, then review the limits and model scope with the engineer.

The authoritative schema is `ElectricalAnalysisContract` in
[models.py](../../tools/hwrepo/models.py). `python -B -m tools.hardware generate`
exports its machine-readable schema to ignored `schemas/electrical-analysis-v1.schema.json`.
The [synthetic fixture builder](../../tests/test_electrical.py) contains a complete
worked contract and [SPICE decks](../../tests/fixtures/electrical/startup.cir).
These demonstrate the tools; they are not design requirements for an adopted board.
Do not copy their limits or ground-net choices into a real design.

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

| Meaning | Expression | Statistic | Unit |
| --- | --- | --- | --- |
| Current drawn from voltage source Vrail | `-i(vrail)` | `max` or `avg` | `A` |
| Power supplied at node supply | `-v(supply)*i(vrail)` | `avg` | `W` |
| Minimum rail voltage | `v(out)` | `min` | `V` |
| Transfer gain | `db(v(out)/v(in))` | `min` or `max` | `dB` |
| Peak output voltage | `v(out)` | `max` | `V` |

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
