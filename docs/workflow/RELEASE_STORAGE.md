# Durable release storage

Git stores design intent. GitHub Actions artifacts are short-lived review evidence.
The approved standalone ZIP produced by `kicad-team release package` is the restorable
manufacturing record and belongs in access-controlled, durable storage selected by
the adopting team.

For every prototype, pilot or production package, retain a receipt containing:

- project or product variant, release ID and release class;
- source commit and annotated source tag;
- package filename, immutable storage URI and emitted `package_sha256`;
- uploader and release authority identities with timestamps;
- retention duration, deletion authority and any legal or customer requirement;
- the date and result of an independent download, verify and restore rehearsal.

Use a write-once or version-locked object when the storage platform supports it.
Restrict replacement and deletion separately from ordinary download access, keep
audit logs, and require multi-factor authentication for release authorities. A mutable
shared drive path or a CI artifact URL alone does not satisfy this role.

After upload, download the stored bytes into a new temporary location and run:

```sh
kicad-team release verify --archive /path/to/downloaded-release.zip
kicad-team release restore --archive /path/to/downloaded-release.zip --destination ../independent-restore
```

Compare the reported `package_sha256` with the approved receipt. Perform this from a
second workstation or controlled runner before relying on the archive for recovery.
Keep the authored receipt under the island's `releases/` directory when organizational
policy permits; otherwise record its controlled-system identifier there.
