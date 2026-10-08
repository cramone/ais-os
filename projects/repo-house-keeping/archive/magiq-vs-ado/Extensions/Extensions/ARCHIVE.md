# Extensions — magiq.visualstudio.com

| | |
|---|---|
| Register id | 1 |
| Source | https://magiq.visualstudio.com/_git/Extensions (**deleted 2026-10-01**) |
| Status | **Decommissioned at source.** This zip is now the only copy of the code. The package checks below are still open for the infoxpert feed |
| Archive method | Zip snapshot of `master`, the only branch. No git history kept (D-006) |
| Archive file | `Extensions.zip` (136,181 bytes) |
| Archived on | 2026-10-01 |
| HEAD commit | _Not recorded before deletion. Can be recovered by restoring the project from the ADO recycle bin (Organization settings → Projects → Recently deleted), which keeps projects for 28 days. Otherwise it's lost_ |
| SHA-256 | 02EE1B295599BF38AE9F7203E68433AA9447D8CE44270980ED7BF27CD3DCE058 (verified 2026-10-01) |
| Pipelines | None (confirmed by Chase 2026-10-01) |
| Package feed | None in the magiq org. Two matching package IDs are in the **infoxpert** NuGet feed, provenance unconfirmed (see below) |
| Targets | netstandard1.6 / net45 / net461. Middleware targets netstandard2.0. All out of support, so a revived project needs retargeting |

## Contents

| Area | Package / project | Consumers found | Notes |
|---|---|---|---|
| FluentXml | MAGIQ.Extensions.FluentXml | ? | In infoxpert feed. Provenance unconfirmed |
| FluentXml | MAGIQ.Extensions.FluentXml.Abstractions | ? | |
| Http | MAGIQ.Extensions.Http | ? | |
| Http | MAGIQ.Extensions.Http.Abstractions | ? | |
| Http | MAGIQ.Extensions.Http.Soap | ? | |
| Middleware | MAGIQ.Extensions.Middleware.Abstractions | ? | The zip has only `.Abstractions`. There is no `MAGIQ.Extensions.Middleware` project |
| Pagination | MAGIQ.Extensions.Pagination | ? | |
| Specifications | MAGIQ.Extensions.Specifications | ? | |
| Specifications | MAGIQ.Extensions.Specifications.Abstractions | ? | In infoxpert feed. Provenance unconfirmed |

**Confirming provenance:** none of the csproj files set `<Version>`, so packages built from this repo would be `1.0.0`. They'd also have `Authors=Chase Ramone` (Middleware: `MAGIQ Software`) and the target frameworks above. If the `.nuspec` inside the infoxpert feed packages matches, they came from this repo. A different version or author means they were built from some other source.

The machine-readable copy is `spec/package-dependencies.csv`. Update both together.

## Exit criteria

- **Delete at source:** every package shows 0 consumers once inventory is complete across all sources, and Chase confirms in writing.
- **Revive:** if any package has a consumer, put the code for that area into a new `mgq-` repo (seeded from the zip) and switch consumers to it.

## Checks still to do

- [x] Repo URL: https://magiq.visualstudio.com/_git/Extensions
- [x] Zip downloaded (`Extensions.zip`) and SHA-256 recorded and verified
- [ ] ~~Record the HEAD commit SHA and date~~. The source was deleted first. Restore it within 28 days if the SHA is needed, otherwise accept the loss
- [ ] Copy `Extensions.zip` and its SHA-256 to a second location (R-002, now urgent)
- [x] Source project deleted (2026-10-01, Chase)
- [ ] Delete the magiq.visualstudio.com org after the 30-day hold, on or after 2026-10-31, if no issues come up (D-008, reminder scheduled)
- [x] Package feed in magiq org: none
- [x] Pipelines in magiq org: none
- [x] infoxpert feed: `MAGIQ.Extensions.FluentXml` and `MAGIQ.Extensions.Specifications.Abstractions` found
- [ ] Confirm where those two infoxpert feed packages came from (compare their nuspec to this repo, as described above)
- [ ] Check the remaining feeds (MAGIQSoftware, nuget.org) for `MAGIQ.Extensions.*`
- [ ] Scan every inventoried repo for `MAGIQ.Extensions.` in `*.csproj`, `Directory.Packages.props` and `packages.config`

## Decision trail
- 2026-10-01: Treat as legacy. Archive locally and put on hold. Delete only if no consumers are found (D-005).
- 2026-10-01: The magiq org has no package feeds and only one branch (`master`). Archive as a zip snapshot instead of a git mirror (D-006).
- 2026-10-01: Zip downloaded and hash verified. No pipelines. Two package IDs found in the infoxpert NuGet feed, provenance not yet confirmed.
- 2026-10-01: Chase deleted the Extensions ADO project before the consumer scan was done (D-007). Low impact: the code is in the zip and the published packages live in the infoxpert feed, which isn't affected.
