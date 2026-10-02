# archive/

Local cold storage for legacy repos that are being **held, not migrated**, while we confirm whether anything depends on them.

## Layout

Two archive methods. Record which one was used in each repo's `ARCHIVE.md`.

**Full mirror** (default: history, multiple branches or LFS) — `scripts/archive-ado-repo.sh`
```
archive/<source-key>/<repo>/
  mirror.git/              bare mirror: all branches, tags and history
  <repo>.bundle            single-file portable copy (git bundle --all)
  <repo>.bundle.sha256     integrity checksum
  src/                     read-only checkout of the default branch
  archive-manifest.txt     generated: source URL, HEAD SHA, branches, tags, date
  ARCHIVE.md               notes: contents, dependency status, decision trail
```

**Zip snapshot** (single branch, history not needed) — ADO UI download
```
archive/<source-key>/<repo>/
  <repo>-<branch>.zip      snapshot of the branch tip
  ARCHIVE.md               must record the HEAD commit SHA and date, plus the zip's SHA-256
```

`<source-key>` matches the `source` value in `spec/repo-register.csv` (`infoxpert-ado`, `magiq-vs-ado`, `magiq-ado`, `github`).

## Rules

- Never overwrite an existing archive.
- Don't edit code in `src/` or in extracted zips. Anything that gets revived is copied into a new `mgq-` repo in the enterprise, never developed here.
- The register row stays `disposition=pending` until we've checked for consumers. Deleting at source needs Chase's written confirmation (triage rule 5).
- To restore a mirror: `git clone <repo>.bundle <dir>` or `git clone mirror.git <dir>`. To restore a zip: extract it and `git init` a new `mgq-` repo (there's no history to bring over).
