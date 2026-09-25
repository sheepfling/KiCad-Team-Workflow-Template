# Shared generated views

`kicad-team hardware generate` exports the shared library inventory here and
published schemas under `schemas/`. These working exports are ignored; only this
guidance is tracked. Product variant views are generated inside each product's own
`build/` folder. The portable gate verifies fresh generation in a temporary directory.

Use a new `kicad-team hardware snapshot --output build/review-001` directory
for a retained review package and `kicad-team hardware verify-snapshot --output build/review-001`
to verify its bytes. See the [BOM policy](../docs/workflow/BOM_POLICY.md) for the distinction
between authored inputs, working exports and frozen released outputs.
