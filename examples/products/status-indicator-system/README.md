# Status indicator reference system

This optional product joins independently owned project islands. Its
[product record](product.json) owns assembly membership, variants, harnesses,
relationships and unresolved integration claims. Its [mechanical notes](docs/mechanical.md)
are training references, not fit approval.

The participating project IDs are declared in `catalog/products.json`. Add product
`tests/test_*.py` files here for integration-specific software checks; they run in the
full gate and when a participating board is selected. Working variant BOMs and views
are generated into this folder's ignored `build/` by `kicad-team hardware generate`.
