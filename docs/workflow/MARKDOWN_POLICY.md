# Markdown documentation policy

Markdown has three independent checks. Install the pinned development tools once with
`python -m pip install -e '.[dev]'`, then run these read-only commands from the repository root:

```sh
rumdl check . --no-cache
python -B -m mdrepo check .
python -B -m tools.docs_policy
```

The full `python -B -m tools.ci` gate runs all three. A documentation-only hosted run and a
focused run with changed Markdown also run all three. `rumdl` checks document format, `mdrepo`
checks repository links and document reachability, and `tools.docs_policy` checks this
repository's typed documentation ownership and engineering rules. The tools do not follow
external URLs or claim that linked vendor content is current.

## Formatting and links

`[tool.rumdl]` in `pyproject.toml` sets a 100-column prose limit, ordered-list numbering,
and aligned tables. Code blocks and tables are exempt from the prose line limit because
commands and tabular evidence can be longer without a safe line break. `rumdl` can reflow
prose and fix table alignment; run `rumdl check --fix .` when a formatting finding appears,
then review the diff and rerun the read-only checks.

`[tool.mdrepo]` checks portable repository-bound paths, exact on-disk case, durable targets,
and reachability from its declared roots. `rumdl` and `tools.docs_policy` check missing local
targets and heading fragments, so `mdrepo` leaves its overlapping missing-target check off.
The GitHub issue and PR templates are excluded from these two tools because they are GitHub
form content rather than conventional documents; `tools.docs_policy` also excludes them.
No broad source-document exclusion is configured.

## Roots and narrow exceptions

`catalog/documentation-policy.json` is the typed, versioned ownership record. It lists
repository entry points and allowed `docs/` namespaces. The `mdrepo` root list in
`pyproject.toml` includes those entry points plus the independently owned example project
and product READMEs. When adding a new independent project or product, update that list
alongside its README. Otherwise link the document from an existing root. Keep the two
root lists aligned.

`tools.docs_policy` applies these local rule IDs:

- `MD001` and `MD002`: no tabs or trailing whitespace.
- `MD003` through `MD005`: one H1, no skipped heading levels, and balanced fences.
- `DOC101` through `DOC103`: local links stay in the repository, use exact case, resolve
  to files, and name real heading fragments.
- `DOC104` and `DOC105`: all source documents are reachable from the configured roots.
- `DOC106`: shared Markdown belongs under an approved `docs/` namespace.

These `MD` codes identify this repository's existing checker, not `rumdl` rule numbers.
Its exception needs one code, one path, a reason, and an expiry date. Expired or unused
exceptions fail. Do not use an exception to hide broken links, case differences, or
unreviewed documentation. `mdrepo` has its own structured exception mechanism; any
exception there should be equally narrow and reviewable.
