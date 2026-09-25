# Authority model

Each project owns its design, manifest, documentation and test expectations together.
Shared catalogs own reusable identities and toolchain pins. Products own cross-project
assembly and integration facts. Shared tools validate these records and generate views.

| Record                                       | Authority                                                                    |
| -------------------------------------------- | ---------------------------------------------------------------------------- |
| Native KiCad source                          | Electrical design and physical board geometry                                |
| Project-local `project.json`                 | Identity, kind, selected toolchain, dependency inventory and check locations |
| Project-local `tests/contract.json`          | Independent expected nets, components or relationship coverage               |
| Product-local `product.json`                 | Assemblies, variants, relationships and their evidence                       |
| Shared catalogs                              | Controlled parts, interfaces, libraries and toolchain definitions            |
| Authored project/product docs and BOM inputs | Requirements, rationale and assembly facts not derived elsewhere             |
| Generated working views                      | Review projections of the authoritative records                              |
| Frozen release BOMs and packages             | Exact outputs retained for a specific approved revision                      |

Source and evidence are classified by purpose, not merely by whether a program created
the file. See the [BOM policy](BOM_POLICY.md). Generated working exports default to
ignored folders. Authored BOMs and frozen release CSVs may be committed.

The examples use the same folder pattern as adopted projects but remain training
fixtures. Retain them for isolated tooling tests; disable their live registration
through discovery settings when appropriate. Production approval still requires
real review, evidence and hosted controls. See the [folder standard](REPOSITORY_STRUCTURE.md).
