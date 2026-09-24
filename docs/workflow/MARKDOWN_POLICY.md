# Markdown documentation policy

Documentation is a reviewed engineering interface. The repository therefore checks
both individual Markdown documents and the local documentation graph. The checker
is deterministic and offline: it does not crawl vendor pages, datasheets, prices or
other external URLs.

## What the static gate enforces

`python -B -m tools.docs_policy` checks every repository Markdown source except
transient output and GitHub issue/PR templates. Those templates are GitHub form
content rather than conventional documents and have a separately scoped format.

- `MD001` and `MD002`: no tabs or trailing whitespace.
- `MD003` through `MD005`: one H1 per document, no skipped heading levels, and
  balanced fenced code blocks.
- `DOC101` through `DOC103`: local links must remain inside the repository, use
  exact on-disk case, resolve to a file, and name a real local heading fragment.
- `DOC104` and `DOC105`: configured documentation roots and all source documents
  must form a reachable documentation graph.
- `DOC106`: repository-wide Markdown must remain under a configured `docs/`
  namespace, apart from the `docs/README.md` entry point.

This combines the useful distinction between document linting and repository-link
policy: document layout is not a substitute for verifying links, anchors and
portable paths; graph validation is not a substitute for readable Markdown.

## Roots and narrow exceptions

`catalog/documentation-policy.json` is the typed, versioned policy record. It lists
the entry-point documents and the allowed repository-wide documentation namespaces.
The default namespaces are scaffold-owned `docs/workflow/` and adopter-owned
`docs/team/`. Add a new root only when it is intentionally an independent entry
point; otherwise link the document from an existing root.

An exception must be scoped to one policy code and one repository path, include a
reason and an expiry date. Expired or unused exceptions fail the same gate. Do not
use an exception to hide a broken link, an accidental path-case difference or
unreviewed documentation.

## CI ownership

The default `python -B -m tools.ci` static pipeline invokes this policy alongside
typed repository/product checks, Ruff, Pyright and unit tests. The docs-only
hosted lane calls `tools.docs_policy` directly; neither lane duplicates Markdown
rules in workflow YAML.
Run `python -B -m tools.docs_policy` while working only on documentation.
Documentation-only PRs run this policy; main and full manual CI runs include it
in the full static pipeline. A focused PR also runs it when Markdown changed.
