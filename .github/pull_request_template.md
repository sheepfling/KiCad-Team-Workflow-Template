## Change classification

- [ ] Template/process guidance
- [ ] Tooling or CI
- [ ] Reference example
- [ ] Adopted engineering project

Project kind (`pcb`, `pcb_only`, `schematic`, `system_wiring`, or `harness_interface`):
Assurance profile (`training`, `development`, or `production`):

Assignment / issue:
Intended change:
Source, library, rule, exclusion or expected-netlist changes:
KiCad version and project-format status:
Mechanical interfaces affected:

## Evidence

Checked commit and Actions run:
Review artifact and visual comparison:
Known failures or untested behavior:
Release/tag impact and manifest update:

## Independent review

Reviewer and disposition (not the author):

For a toolchain or project-format migration, use a dedicated PR. Do not mix it
with electrical, PCB-layout, library, or mechanical-interface changes.

A green run is evidence for review; it is not a board lock, branch protection or
manufacturing approval. Keep an explicit `NOT FOR MANUFACTURE` marker on training
fixtures and their review views.
