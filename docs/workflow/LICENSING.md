# Scaffold licensing and company adoption

The original KiCad workflow scaffold is published under the
[Zero-Clause BSD license (0BSD)](https://opensource.org/license/0bsd). This covers
the original tooling, documentation, configuration and synthetic reference assets.
It allows commercial and proprietary reuse without a requirement to retain the
license notice or publish modifications. Dependencies and assets obtained from
other sources keep their own terms.

This page describes the upstream scaffold. It does not select a license for an
adopting company's designs, firmware or other new work.

## Choose company terms before the first commit

Use [bootstrap](TEMPLATE_ADOPTION.md#bootstrap) for a new company repository.
It copies tracked source into a new folder, omits the known root template `LICENSE`,
and creates neither Git history nor a commit. Initialize the copied workspace, add
the company's chosen root terms if appropriate, and then create its first commit.
The company can choose proprietary terms; the tool does not invent those terms or
the company's legal identity.

A literal [GitHub fork](https://docs.github.com/en/pull-requests/reference/forks)
of a public repository stays public and retains upstream history.
[Use this template](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-repository-from-a-template)
can create a private repository, but GitHub immediately makes a commit of the copied
files. Bootstrap is the route to choose when even the first company commit should
contain the company's selected root notice. Initialization of a fork/template copy
can remove the current root template notice; it does not rewrite earlier commits.

## What cleanup removes

Both bootstrap and first-time initialization recognize only the exact bytes of the upstream root
`LICENSE`, using the fingerprint in
[the licensing helper](https://github.com/sheepfling/KiCad-Tooling/blob/codex/tooling-split/kicad_tooling/hwrepo/licensing.py).
Their reports include `"removed": ["LICENSE"]` when that file was removed from the new workspace.

A modified or replacement root license is preserved byte for byte. Nested licenses,
copyright notices and third-party terms are never scanned for removal. The bundled
license test fixture and training-library provenance describe those specific inputs;
they are not repository-wide licenses for the company's new work.

Repeated initialization is a no-op after successful adoption, including when the
team subsequently chooses its own 0BSD license. A failed initialization restores
the original files, including the root notice. Bootstrap leaves the source template
unchanged and never publishes a partially prepared destination.

## Future upgrades

Preserve the company's root license when applying upstream changes. Do not copy the
template's root notice over it. Keep required third-party notices and review the
[upgrade plan](TEMPLATE_ADOPTION.md#upgrade-plan). Company terms do not change the
upstream scaffold's availability under 0BSD.
