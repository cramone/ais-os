---
id: MM-003
type: review
project: magiq-media
workstream: projection-tables
raised-by: []
status: done
outcome: plan
todo-id: a85d40df-3c91-5a96-b00d-94438dd9d1ba
created: 2026-08-31
exception: retrospective backfill — the plan it consumes (MM-002) predates the cycle, so this review was written after the work rather than before it. No paste-ready prompt file exists; no session was ever run from it.
---

# Projection tables — schema-versioned rotation, verified

A **retrospective** review. It does not argue new work. It records what was actually built against
what MM-002 specified, so the workstream can enter the review cycle with a status that survives the
next session.

Written because `plans/README.md` carried MM-002 as **Parked — "written and ready; not being worked,
and nothing blocks it"**. That was wrong by roughly a month. Phase A had shipped.

## Scope

Verified 2026-08-31 against three repos:

| Repo | Ref read |
|---|---|
| `magiq-media` | `feature/change-requests` (2026-08-27, pushed, **unmerged**) |
| `cdk-magiq-media` | `feature/change-requests` (2026-08-24) |
| `aspnetcore-platform` | `main` (2026-07-28) |

Checked: every item in MM-002 § 11 *Definition of done*, plus §§ 3.1–3.5 core concepts and the §7
phase split.

**Not checked:** whether any of it runs. Nothing was compiled or executed — no .NET SDK in the
session, the same caveat the `authorization/`, `archive-cascade/` and `event-reliability/`
workstreams all carry. The manifest tool's own introducing commit is titled *"added projection
manifest untested"*. Verification here is **source-level only**.

Also not checked: the `develop` ↔ `feature/change-requests` gap (PT-4).

## Findings

### PT-1 — Phase A is complete. Severity: Low (record-keeping, not a defect)

Every § 11 item traces to source:

| DoD item | Evidence |
|---|---|
| `{base}-v{schemaVersion}` physical naming | `Magiq.Platform.Projections.Stores.DynamoDb/Replay/ProjectionRotationOptions.cs:24` — `VersionNameFormat = "-v{0}"`, replacing `TableNameSuffixFormat = "_v{0}"` |
| Metadata holds version strings, no runtime counter | `Replay/Metadata/ReadModelTableMetadata.cs:22` — record shape matches MM-002 § 3.4 field for field |
| Resolver precedence by version | `Schema/ProjectionTableNameResolver.cs:70` |
| CDK owns tables, built from a committed manifest | `cdk-magiq-media/lib/constructs/dynamodb/read-models.ts` and `write-indexes.ts` both read `projection-tables.manifest.json` |
| Manifest committed at app repo root | `magiq-media/projection-tables.manifest.json` |
| Manifest generated from code, with a CI drift gate | `src/tools/ProjectionManifest/` — `ManifestGenerator`, `ManifestDriftCheck`; tests `ManifestDriftCheckTests.cs`, `ManifestDriftGateTests.cs` |
| Operator tool holds no `CreateTable` | `git grep 'CreateTable\|table/media-\*'` over tracked cdk `.ts` returns **zero hits**. The broad control-plane wildcard MM-002 § 1 set out to remove is gone |
| `rotate` / `rollback` / `cleanup` | `src/tools/ProjectionReplay/Program.cs:75`, `RotationRunner.CleanupAsync` |
| Runbook | `src/tools/ProjectionReplay/RUNBOOK.md` — deploy → rotate → verify → flip → cleanup, plus additive-vs-breaking guidance and the bump-to-force escape hatch |
| ADR rewritten | `docs/adrs/persistence-and-eventing.md` § *Schema-Versioned Projection Table Rotation* — names this plan file directly and records the supersession of the `_v{n}` design |

Two design details went further than MM-002 asked, both worth knowing:

- **Write-side reference/index projections are excluded by design**, registered with
  `schemaVersion: null`, carrying no `-v{n}` suffix and provisioned unversioned by CDK's
  `write-indexes` construct. MM-002 § 3.1 implied every table versions; the built system opts in
  per table.
- **`previousVersions` in the manifest is hand-carried history, not generated.** The generator reads
  the committed manifest, carries existing history forward untouched and appends the outgoing shape
  when the registered version moves past it. Two operational consequences are recorded in
  `src/tools/ProjectionManifest/README.md`: the generator **must** run on the commit that performs
  the bump, and entries are never pruned automatically.

### PT-2 — Phase B is not built, and that is the recorded decision. Severity: Low

`git grep IProjectionVersionRegistry` over `aspnetcore-platform/src` returns nothing. Live dispatch
does not select projectors by active version, so a breaking read-model change still has a
non-zero read/write window between deploy and rotate.

This is deferred, not missed. `docs/adrs/persistence-and-eventing.md` states it plainly: Phase B is
deferred until the first breaking read-model change needs it, and Phase A ships the CDK-ownership
and IAM-tightening wins now. MM-002 § 7 and open decision F both recommend exactly this split.

**The deferral has a trigger, and the trigger is not monitored.** Nothing fails, warns, or blocks
when a developer bumps a `schemaVersion`. The first breaking change is the moment Phase B is needed,
and the system will not say so.

### PT-3 — `ProjectionTableProvisioner` survives. Severity: Low

`aspnetcore-platform/src/platform/Domain/Magiq.Platform.Projections.Stores.DynamoDb/Replay/ProjectionTableProvisioner.cs`
still exists. MM-002 § 4.5 said retire it from the normal path and delete it unless tool-driven
creation was kept as a fallback — MM-002 open decision D recommends keeping a thin provisioning
path for local/dev and integration tests only, gated so it never runs deployed.

So its presence is probably decision D landing as recommended rather than dead code. **Not
verified** — the gating was not read. Worth one look before anyone deletes it.

### PT-4 — The work is split across a merge boundary. Severity: Medium

Not a code defect; a "where is it" defect, and the reason this review exists.

- `develop` (last commit 2026-07-29) carries the manifest tool and the platform rotation work.
- `feature/change-requests` (2026-08-27, pushed to origin, **unmerged**) carries later refinements —
  `68b943a8` on the app side, `c49fb9f` on the cdk side.

Anyone reading `develop` alone sees a partial implementation. Anyone reading `plans/README.md` saw
"Parked, nothing deployed". Neither is the truth.

## Open Questions

1. **Answered:** does Phase B block calling Phase A shippable? No — the ADR records the phase split
   as a decision with a trigger, and Phase A delivers the CDK-ownership and IAM wins on its own.
2. **Answered:** is MM-001 (`hot-swappable-projection-rotation-plan.md`) still live? No. Superseded
   by MM-002, which shipped. Archived 2026-08-31, kept for the discovery and the rotation-unit
   decision.
3. **Answered:** should MM-002 be closed and archived? No. Phase B is real remaining scope with a
   named trigger. MM-002 is `parked` on Phase B, not `done`.

## Dependencies

None. MM-002 depends on no other document in this project.

External: the platform work landed in `aspnetcore-platform` (`main`, PR #27) and the app consumes it
via `MagiqPlatformVersion`. Not tracked as a `blocked-by-external` entry — the dependency is
satisfied, and we operate that repo.

## Recommended sequencing

1. **Merge `feature/change-requests`**, or record explicitly why it is being held. PT-4 is the only
   finding with a cost that grows.
2. **Run it.** `dotnet test` on `tests/tools/ProjectionManifest.Tests` and
   `tests/integration/modules/Catalog/Catalog.IntegrationTests/Rotation/`. Nothing here has been
   executed, and the manifest tool's own commit says untested. One green run converts this whole
   review from source-level to verified.
3. **Give PT-2's trigger a home.** A drift-gate style check that fails when a `schemaVersion` bumps
   without Phase B present would turn a documented intention into an enforced one. Small; the drift
   gate already has the hook.
4. **Confirm PT-3's gating**, then either delete the provisioner or document decision D as landed.

Phase B itself is not sequenced here. Its trigger — the first breaking read-model change — has not
fired.

## Related

- MM-002 — the plan this review consumes, `plans/projection-tables/schema-versioned-projection-tables-plan.md`
- MM-001 — the superseded runtime `_v{n}` design, `plans/projection-tables/Archive/hot-swappable-projection-rotation-plan.md`
- `docs/adrs/persistence-and-eventing.md` § Schema-Versioned Projection Table Rotation — the ADR
- `src/tools/ProjectionReplay/RUNBOOK.md` — operator steps
