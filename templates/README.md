# Copyable project and workflow records

The easiest start is
`kicad-team template new-project --project-id battery-board --kind pcb --toolchain kicad-10.0.5`.
The scaffold contains no circuit. Create the real KiCad design and complete its contract.

For manual creation, copy the appropriate `*-project-config.example.json` to
`projects/<id>/project.json` and the matching `project-tests/<kind>.json` to
`projects/<id>/tests/contract.json`. Replace placeholders, set local native paths,
and declare actual required inputs. The PCB, PCB-only, schematic, wiring and harness
templates all use the same island layout. Use `pcb_only` only while a board has no
authoritative schematic: it stays not for manufacture, validates board DRC/layout,
and cannot supply a product assembly BOM or non-review release. The production template
adds explicit release controls.

PCB and PCB-only development contracts start with no ignored DRC checks. KiCad 10.0.5
may mark several checks ignored in a new project's Board Setup. Enable those checks in
KiCad before the first native run; do not copy default ignores into the contract to
make a development board pass. A complete PCB project also starts with no ignored ERC
checks: enable KiCad's default `single_global_label`, `four_way_junction`,
`simulation_model_issue` and `footprint_filter` checks in Schematic Setup. PCB-only
projects have no schematic or ERC lane.

Manifest source paths are project-relative. Only `shared_source_roots` and
`shared_inputs` are repository-relative. Toolchain version and image are resolved
from `toolchain_id`, so they are not duplicated in project files.

Catalog examples describe shared identities. [Mechanical handoff](mechanical-handoff.production.md)
and governance examples become board-local reviewed records. The typed release-manifest
example illustrates the checker schema. Use `kicad-team release prepare` to populate
real source, dependency and evidence hashes automatically; placeholders cannot pass.
`OPTIONAL_NO_AUTO_MERGE.gitattributes` is an opt-in policy fragment for teams that
want every KiCad file conflict to require deliberate file-level resolution. Review
and append it to the root `.gitattributes` only when that matches the team's process.

The template contract and upgrade catalog describe supported adoption steps. See
[template adoption](../docs/workflow/TEMPLATE_ADOPTION.md),
[BOM policy](../docs/workflow/BOM_POLICY.md), [sourcing](../docs/workflow/IDENTITY_AND_SOURCING.md)
and [library policy](../docs/workflow/LIBRARIES.md).

For electrical checks, `kicad-team electrical --project <id> --init` connects a pending
sidecar without inventing limits. The [electrical examples](electrical/README.md)
provide a complete synthetic JSON contract and circuit decks for learning the
schema. Review real board requirements and capture hashes before using them.
