# Shared KiCad libraries

This directory is intentionally empty in the synthetic pilot. It exists to make the project/library boundary explicit.

Create one named directory for each controlled reusable library, such as `libraries/power-connectors/`. Keep symbols, footprints, models, provenance, licensing, and a changelog together. Register it in `catalog/libraries.json`. Before a board uses it, add the catalog ID to that board's `library_ids`, the directory to `shared_source_roots`, and every file under it to `shared_inputs` in `projects/<id>/project.json` so CI hashes and reviews it. The board's own KiCad library tables use `${KIPRJMOD}` paths to reach the shared directory.

Do not move a project-local asset here merely because it looks reusable. First establish ownership, compatibility, versioning, and the impact on each consuming board.
