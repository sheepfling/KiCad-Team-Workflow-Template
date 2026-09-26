# Generated JSON Schemas

The authoritative contracts are Pydantic models in the installed tooling
[models module](https://github.com/sheepfling/KiCad-Tooling/blob/main/kicad_tooling/hwrepo/models.py).
Run `kicad-team hardware generate` to export the published input and release
schemas here for editors or non-Python consumers. These JSON files are ignored and
are also available as portable CI artifacts. Only this README is tracked.

Change the model and its contract tests in the tooling repository, not an exported schema.
The portable gate regenerates independently in a temporary directory, so a fresh
clone does not need these files. Internal reports remain typed Python models without
separate published schema artifacts.
