# Assurance profiles

The project manifest owns its assurance profile. Profiles describe the work's maturity;
production readiness is separate from creating a project folder.

| Profile       | Intended use                       | Requirements                                                                                                                    |
| ------------- | ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `training`    | Synthetic workflow fixtures        | Training status, NOT FOR MANUFACTURE, explicit accepted-check inventory                                                         |
| `development` | Real, unreleased engineering work  | Engineering status, NOT FOR MANUFACTURE, all applicable ERC/DRC rules enabled; release/governance paperwork is not required yet |
| `production`  | Reviewed production-level controls | Approved identities/libraries, mechanical handoff, governance record and no disabled applicable checks                          |

`tools.template new-project` starts in `development`. Native sources and independent
contracts must still be completed before checks pass. The profile does not permit
missing dependencies, malformed data or inconsistent electrical expectations.

For production, use the production manifest template and add the project's reviewed
`docs/mechanical.md` and `releases/governance.json` (or explicitly declared local paths).
Configure real hosted branch controls as described in [GitHub governance](GITHUB_GOVERNANCE.md).
Passing a production check still does not authorize ordering or manufacturing.

`catalog/release-policies.json` independently sets the assurance floor for retained
connection, harness and mechanical claims. See [release readiness](RELEASE_READINESS.md)
for product maturity, evidence, deviations, approvals and artifact hashes.
