# Template metrics

The metrics command reports the repository's current policy condition in a typed,
machine-readable form. It counts findings from registry, repository, documentation,
product and generated-output checks; separately exposes changed evidence hashes; and
counts the status/expiry of deviations from an optional release manifest.

```sh
kicad-team ci --metrics
kicad-team ci --metrics --manifest release/<release-id>.json
```

The report is read-only and non-authorizing. It is a snapshot, not a historical CI
database, PLM/PDM record, source of manufacturing truth, or unit/as-built tracker.
An adopting organization should aggregate retained CI reports and its approved
operational systems if it needs trends, SLAs, serial-number traceability, or release
exception aging across repositories.
