# GitHub governance and role separation

Repository files can document and gate the expected policy, but only GitHub can
enforce branch protection and permissions. Before a project is promoted to the
`production` assurance profile, create `projects/<project-id>/releases/governance.json` from
`templates/github-governance.example.json` and replace every placeholder.

The production lint requires a protected branch, exact required check names, branch
protection evidence and release authority. `catalog/team-policy.json` defines the
minimum actor count, independent-review requirement and required status checks.
The default needs two people: an author and an independent reviewer; either may
integrate. Teams can adopt stricter separation or an explicitly reviewed solo policy
by changing that file and its rationale. Case differences cannot create extra actors.

## Configure in GitHub

For the default branch, configure and verify:

1. Pull requests are required; direct pushes and force-pushes are blocked.
2. At least one independent approval is required, stale approvals are dismissed when
   new commits arrive, and the branch is up to date before merge.
3. The exact KiCad CI checks named in the governance record are required.
4. Code-owner review is required after `.github/CODEOWNERS` is populated with real
   users or teams. This repository intentionally ships only `CODEOWNERS.example`
   because it must not invent the team's identities.
5. Only named maintainers may merge; release tags and release artifacts follow the
   separately recorded release authority.

Record the GitHub settings URL, API output reference, or approved screenshot in the
governance record's `branch_protection_evidence`. Test the actual configured roles
and independent-review rule. Also rehearse a rejected check,
conflict handoff, access revocation, and release restore before relying on it.

## Inspect hosted controls without changing them

From an adopted repository with GitHub CLI access, run:

```sh
python -B -m tools.governance_audit --format text
python -B -m tools.governance_audit --repo OWNER/REPO --record projects/board/releases/governance.json --format json
```

The first command detects the current GitHub repository. Use `--repo` to inspect
an explicit remote and `--record` to compare its default branch and exact required
checks with a project governance record. The command only issues read requests and
does not write an evidence file or change GitHub settings. JSON is the default
for agents; `--format text` groups controls and next actions for an engineer.

The report distinguishes `PASS` (observed), `NEEDS_SETUP` (an observed gap), and
`UNKNOWN` (the API or human evidence is insufficient). Exit codes are 0, 1, and 2,
respectively. `hosted_controls_status` isolates the settings check. The overall
`status` stays `UNKNOWN` when settings pass because this command cannot verify
real team permissions or review rehearsals. A 404 from the legacy branch-protection
endpoint is `UNKNOWN` because the token may lack Administration:read; active
[branch rules](https://docs.github.com/en/rest/repos/rules#get-rules-for-a-branch)
can still prove specific controls. The audit checks CODEOWNERS in the supported
[locations](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners),
and requires a clean [GitHub CODEOWNERS error report](https://docs.github.com/en/rest/repos/repos#list-codeowners-errors)
for the default branch before the file check can pass. A malformed entry is
`NEEDS_SETUP`; an unavailable error report is `UNKNOWN`. A declared handle alone
does not establish write access or a valid review drill. When a governance record
is supplied, its authors, reviewers, and integrators must each be populated;
missing roles are `NEEDS_SETUP` even if other roles list enough distinct people.
Confirm bypass exceptions, merge permissions, rejected checks, access revocation,
and release restore with real actors before production adoption.

## Tool access

Use `gh auth status` before trying to read or alter repository settings. A valid token
with repository-administration scope and the actual reviewer/team identities are
required to apply this policy; they are intentionally outside this template.
The read-only audit can inspect active rules with metadata read access, while the
legacy [branch-protection endpoint](https://docs.github.com/en/rest/branches/branch-protection#get-branch-protection)
requires Administration:read. Missing API access is reported as `UNKNOWN`.
