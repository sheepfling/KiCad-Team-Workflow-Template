# Electrical contract examples

Start a real board with `kicad-team electrical --project <id> --init`.
It creates a project-specific contract with all three sections marked `pending`.
Complete those engineering decisions before expecting verification to pass.
See the [quickstart](../../docs/workflow/ELECTRICAL_ANALYSIS.md#quickstart).

[contract.example.json](contract.example.json) is a complete, schema-valid worked
example of grounding, startup/steady-state power and high-frequency measurements.
Its project ID, pins, ratings, windows and limits are synthetic. Its zero hashes
are deliberate placeholders: copying it cannot create passing board evidence.
Use it to understand the fields and copy only reviewed sections into your starter.

[startup.cir](startup.cir) illustrates a 5 V ramp charging a capacitor through
source resistance while supplying a resistive load. [signal.cir](signal.cir)
illustrates a 1 MHz pulse and AC stimulus into an RC network. They produce synthetic
responses and contain no actual PCB parasitic extraction or vendor device models.
The regression suite and simulator smoke runs use these same decks.

Place your real decks and dependencies under the project's `tests/electrical/`.
Capture design and model hash candidates without editing approved bindings:

```sh
kicad-team electrical --project my-board --capture-inputs --model projects/my-board/tests/electrical/startup.cir --model projects/my-board/tests/electrical/device.lib
```

Open the printed `inputs.json`. Review the circuit-to-model mapping and assumptions,
then copy its `source_sha256` and each case's applicable `model_sha256` entries into
the contract. Each deck's includes must be inventoried; unused entries are rejected.
If the contract already names the models, omit `--model` to capture their current
hashes for a new review. No capture command updates the approved contract.
