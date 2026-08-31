---
id: MM-002
type: plan
project: magiq-media
workstream: projection-tables
consumes: [MM-003]
depends-on: []
blocked-by-external: []
status: parked
todo-id: e9fa6eb2-3337-5f33-9ea8-9290013e2b3e
branches: [magiq-media#165, magiq-media@68b943a8, aspnetcore-platform#27, cdk-magiq-media#57, cdk-magiq-media@c49fb9f]
ado: -
created: 2026-07-24
exception: legacy filename — predates the "plan is named after its primary review" rule. Kept as-is; MM-003 is the link.
---

# Migration Plan — Schema-Versioned, CDK-Owned Projection Tables

> **Phase A shipped.** Verified against source 2026-08-31 by MM-003 — every § 11 *Definition of done*
> item traces to code across `magiq-media`, `cdk-magiq-media` and `aspnetcore-platform`. Nothing has
> been compiled or run; see MM-003 § Scope.
>
> **Parked on Phase B only** (§ 3.6, § 4.7 — version-aware projectors). Deferred by the decision in
> `docs/adrs/persistence-and-eventing.md`: Phase B waits for the first breaking read-model change
> that needs a zero read/write window. That trigger is not monitored — MM-003 PT-2.

**Status:** ~~Proposed~~ — Phase A implemented (see the note above). Supersedes the runtime-versioned
(`_v{n}`) design in MM-001, `Archive/hot-swappable-projection-rotation-plan.md`. Nothing was deployed
to a real environment when this was written, so it was a **greenfield redesign, not a live-data
migration** — we replaced the mechanism; there was no `_v{n}` data in production to carry over.

**Repos touched:** `aspnetcore-platform` (platform SDK), `magiq-media` (app + operator tool),
`cdk-magiq-media` (infra). Plus README, spec, ADR, and runbook updates.

---

## 1. Why we are changing it

The current design names the rebuild target `{base}_v{n}`, creates and drops those tables **at
runtime** from the operator tool, and tracks `n` as a **runtime integer** in the metadata table.
Consequences we want to remove:

- CDK cannot own the `_v{n}` tables (it does not know `n`), so it uses a broad `table/media-*` IAM
  wildcard and the physical tables drift from IaC.
- The operator tool needs DynamoDB **control-plane** rights (`CreateTable`/`DeleteTable`) and has to
  toggle deletion protection.
- `n` is runtime state that must be reconciled; there is `drop-old` housekeeping.

## 2. The target design (one paragraph)

Each physical projection table carries a **schema version** in its name — `media-collections-v4`.
That version is a **source-controlled constant per logical table**, bumped by developers only on a
breaking read-model change. CDK reads the constant and **owns** the table (create, retain
current+previous, delete old). The app reads the same constant to know its **target**. The rotation
metadata only records which version is **live**. Live projection always writes the **active**
version's shape into the **active** table; the rebuild builds the **target** version's table from the
event log; the flip is atomic. For breaking changes, the previous projector version is retained for
the transition (parallel-change / expand-contract) so the live table is never polluted and rollback
stays clean. Additive changes need none of that.

---

## 3. Core concepts (lock these first)

### 3.1 Physical naming
`physical = {prefix}{base}{suffix}-v{schemaVersion}` — e.g. `media-collections-v4`. Prefix/suffix
still come from `DynamoDbOptions`. Format lives in `ProjectionRotationOptions` (replaces
`TableNameSuffixFormat="_v{0}"` with a `VersionNameFormat="-v{0}"`). Rotation key stays the
**TableId** (logical table); co-located read models on one TableId share a version and rotate together.

### 3.2 Schema version — single source of truth
The version is declared where the projection is registered, e.g.
`AddProjectionSchema<CollectionSummaryReadModel, CollectionSummarySchema>("media-collections", schemaVersion: 4)`.
That is the app's source of truth. CDK needs the same value **plus the physical key/GSI schema** to
create the table, so we export it (§3.3).

### 3.3 Projection schema export (app → CDK contract)
CDK must create tables with the correct PK/SK/GSIs, which today live only in code
(`IProjectionIndexSchema`). Introduce a **generated, committed manifest** that both sides read:

`magiq-media/projection-tables.manifest.json` (checked in), shape:
```json
{
  "tables": [
    { "tableId": "media-collections", "schemaVersion": 4,
      "partitionKey": "PK", "sortKey": "SK",
      "gsis": [ { "name": "GSI1", "partitionKey": "GSI1PK", "sortKey": "GSI1SK", "projection": "ALL" } ] }
  ]
}
```
- A small dotnet build tool (`magiq-media/src/tools/ProjectionManifest`) reflects over the registered
  projection schemas + index schemas and writes this file. Run in CI (or a `dotnet run` pre-synth
  step); a unit test fails the build if the committed manifest is stale vs code.
- CDK reads it at synth to declare tables. **Code stays the source of truth for GSIs; CDK consumes a
  generated artifact.**
- *(Open decision A — see §9. Alternative: hand-maintain the table defs in CDK TS with a drift test.)*

### 3.4 Metadata model (new shape)
`ReadModelTableMetadata(string TableId, string ActiveVersion, string? PreviousVersion,
string? PendingVersion, bool ReplayInProgress, DateTimeOffset LastRotatedAt)`.
- Replaces `ActiveTableName`/`PreviousTableName`/`PendingTableName`/`int Version` with **version
  strings**. Physical names are derived, never stored.
- No runtime counter: the rebuild **target** is an input (the deployed version), not `Version + 1`.

### 3.5 Resolver precedence (updated)
`ProjectionTableNameResolver.Resolve`:
1. Replay override (rebuild in progress → **pending** version's table).
2. Snapshot **active** version → `{base}-v{active}`.
3. No metadata row (bootstrap) → **deployed** version from the registration constant → `{base}-v{deployed}`.

The resolver needs a `TableId → deployedVersion` map built at startup from the registrations.

### 3.6 Version-aware projection (the zero-window mechanism)
Rule: **live projection follows the ACTIVE version; the rebuild builds the TARGET version.**
- Live event → run the **active** version's projector(s) → write the active table. (During a
  transition the active version is still the old one, so the old projector keeps the old table
  correct.)
- Rebuild (tool) → run the **target** version's projector(s) → write the target table (via the
  existing write-redirect).
- Breaking change ⇒ retain the previous projector implementation for the transition (expand-contract);
  retire it after cutover + cleanup.
- Additive change ⇒ one projector version, no special handling.

This is **Phase B** (§7) — the biggest change. Phase A ships the naming/CDK/metadata changes first.

### 3.7 Lifecycle across a breaking change (worked flow)
1. Dev changes a projection + bumps `schemaVersion 4 → 5`; regenerates the manifest; retains the v4
   projector alongside v5. Merge.
2. **Deploy.** CDK sees v5, creates empty `media-collections-v5`, keeps `media-collections-v4`.
   App is now v5 code but metadata active = v4, so it serves and live-projects into v4 (with the v4
   projector). Nothing breaks.
3. **Rotate** (operator). Tool reads deployed=v5, active=v4 ⇒ target v5. Set `PendingVersion=v5`,
   `ReplayInProgress=true`. Replay full history per tenant into `-v5` with the v5 projector; verify
   counts; flip (`Active=v5, Previous=v4`); snapshot refresh; post-flip reconcile.
4. **Cleanup** after soak: drop `media-collections-v4` (CDK retention on next deploy, or one exact-ARN
   `DeleteTable` from the tool — Open decision C).
5. **Rollback** (pre-cleanup): flip `Active` back to v4 — clean, because v4 was maintained in the v4
   shape throughout.

---

## 4. Changes — aspnetcore-platform (`src/platform/Domain/Magiq.Platform.Projections.Stores.DynamoDb`)

### 4.1 Metadata (`Replay/Metadata/`)
- `ReadModelTableMetadata.cs` → new record shape (§3.4).
- `Stores/ReadModelTableMetadataStore.cs` + interface → operations become version-oriented:
  `InitializeAsync(tableId, initialVersion)`, `BeginReplayAsync(tableId, targetVersion)` (guard
  `ReplayInProgress=false`; set `PendingVersion`, no counter), `CompleteReplayAsync` (Active←Pending,
  Previous←old Active, clear Pending — same RHS-eval-against-old-values trick, now on version
  attributes), `AbortReplayAsync`, `RollbackAsync` (swap Active/Previous versions), `GetAsync`,
  `GetAllAsync`. Keep the atomic conditional-write guards.

### 4.2 Options (`Replay/ProjectionRotationOptions.cs`)
- Replace `TableNameSuffixFormat="_v{0}"` with `VersionNameFormat="-v{0}"`. Keep `SnapshotTtl`.

### 4.3 Snapshot (`Replay/ActiveProjectionTableSnapshot.cs`)
- Map now holds `TableId → activeVersion` (string), and `TryGetActiveVersion`. Physical-name assembly
  moves to the resolver. Otherwise unchanged (TTL, single-flight, refresh).

### 4.4 Resolver (`Schema/ProjectionTableNameResolver.cs`)
- Build `TableId → deployedVersion` from registrations (needs the schema version on `IProjectionSchema`
  or a parallel registration). Implement precedence §3.5. Add a helper to assemble
  `{base}-v{version}` using `VersionNameFormat`. `ResolveStatic` becomes "deployed-version table".

### 4.5 Provisioner (`Replay/ProjectionTableProvisioner.cs`)
- **Retire runtime table creation** from the normal path (CDK owns creation). Keep the class only if
  we choose tool-driven creation as a fallback (Open decision C); otherwise delete it and drop its DI
  registration. `ProjectionsTableMigration` no longer creates projection tables (§4.8).

### 4.6 Orchestrator (`Replay/ProjectionRotationOrchestrator.cs`, `RotationOptions.cs`, `RotationReplayContext.cs`)
- `RotationOptions` gains `TargetVersion` (string) — the version to rebuild into (from the deployed
  constant). Remove counter logic and `BuildPendingName` (name now = `{base}-v{TargetVersion}`).
- `RotateAsync`: assert target table exists (it is CDK-owned; do **not** create it) → `BeginReplay`
  → replay/verify/flip/reconcile as today. Resume-if-in-progress keyed on `PendingVersion`.
- `RollbackAsync`/`AbortAsync`: keep; operate on versions.
- `DropRetiredTablesAsync` → **remove** (CDK cleanup) or replace with `DropPreviousVersionAsync(tableId)`
  that deletes exactly `{base}-v{Previous}` by name (Open decision C).
- `RotationReplayContext`: `PendingTableName` → `PendingVersion` (+ keep `RedirectToPending`).
- `IProjectionRotationVerifier`: unchanged (counts active-version table vs pending-version table).

### 4.7 Version-aware projection — **Phase B** (`Magiq.Platform.Projections`)
- Register projectors under a version (e.g. `IProjectionVersionRegistry: TableId → { version → projectors }`).
- Live dispatch (`ProjectionPipeline`) selects the **active** version's projectors (from the snapshot)
  and resolves writes to the active table.
- Replay coordinator runs the **target** version's projectors into the target table.
- Additive path: a single registered version behaves exactly as today.
- This is invasive; gate it behind Phase B and land Phase A first.

### 4.8 Migration + registration
- `ProjectionsTableMigration.cs`: stop creating projection tables and (decision) the metadata table —
  CDK owns both. Keep it only if we still want the app to self-provision in local/dev (Open decision D).
- `ProjectionsBuilderExtensions.cs` (`UseDynamoDbStore`/`AddProjectionRotation`): register the version
  map, deployed-version lookup, and drop the provisioner/migration registrations that move to CDK.
- `AddProjectionSchema<T>(name, schemaVersion)` overloads carry the version.

### 4.9 Platform README + tests
- `Magiq.Platform.Projections.Stores.DynamoDb/README.md`: rewrite the rotation section to the
  version-keyed model, the active-vs-target projection rule, and the CDK-ownership boundary.
- Update `tests/Magiq.AspNetCore.Tests/Projections/Rotation/*` — the store atomicity tests (version
  strings + guards), the orchestrator end-to-end (pre-created target table, flip by version, rollback),
  and resolver precedence. Remove drop-old tests (or repoint to drop-previous).

---

## 5. Changes — magiq-media

### 5.1 Projection registrations (`src/modules/*/**.ReadModel.Infrastructure/ServiceCollectionExtensions.cs`)
- Add `schemaVersion` to each `AddProjectionSchema<...>("media-...")`. Start every table at **v1**.
- For a future breaking change: add the new projector version and retain the old (Phase B).

### 5.2 Schema-export tool + manifest
- New `src/tools/ProjectionManifest` that emits `projection-tables.manifest.json` (§3.3).
- Commit the manifest; add a test that regenerates and diffs it (fails on drift).

### 5.3 Operator tool (`src/tools/ProjectionReplay`)
- `RotationRunner.RotateAsync`: derive the **target version** from the deployed registration constant
  for the table (not an invented number); pass `TargetVersion` in `RotationOptions`. Fail clearly if
  the target table does not exist (CDK must have created it).
- `rollback`/`abort`: unchanged in spirit; operate on versions.
- `drop-old` → replace with `cleanup --table <name>` that drops the **previous** version's table by
  exact name (only if Open decision C = tool-driven cleanup); otherwise remove the command and document
  CDK-driven cleanup.
- `RotationHost.cs`: unchanged from the current fix (registers `ISchemaCommandRunner` +
  `ITableSchemaBuilder` directly). If runtime creation is fully removed, `ITableSchemaBuilder` is only
  needed for tool-driven delete — keep only what cleanup requires.
- `TableRotationRegistry.cs`: unchanged (table→aggregate map). Optionally surface each table's current
  schema version for `--dry-run` output.
- `Program.cs`: help/usage text updated for the new commands.

### 5.4 ADR + spec
- `docs/adrs/persistence-and-eventing.md` → rewrite the **Blue-Green Projection Table Rotation** section
  to the schema-versioned, CDK-owned, active-vs-target-projection design (replace the `_v{n}` narrative).
- `docs/spec/` (persistence / read-model conventions): document the schema-version constant, the
  manifest contract, the additive-vs-breaking decision, and the deploy→rotate→cleanup lifecycle.

### 5.5 Runbook (`src/tools/ProjectionReplay/RUNBOOK.md`)
- New operator flow: (1) confirm the deploy bumped the schema version and CDK created `-v{new}`;
  (2) `rotate --table <name> --confirm`; (3) verify live reads followed the flip; (4) `cleanup`
  after soak (or note CDK removes it next deploy). Update rollback + abort steps. Add the
  additive-vs-breaking guidance and the "bump-to-force" escape hatch for same-version corruption.

### 5.6 Integration test
- Update `tests/integration/modules/Catalog/Catalog.IntegrationTests/Rotation/CollectionRotationE2ETests.cs`
  to the new naming (`media-collections-v{n}`) and the CDK-provisioned model: the test must **create
  the target table itself** (standing in for CDK) before rotating, since the app no longer provisions
  it. Keep the "live list follows the flip and rollback" proof.

## 6. Changes — cdk-magiq-media

### 6.1 Projection tables from the manifest (`lib/constructs/dynamodb/`)
- New/updated construct reads `projection-tables.manifest.json` and declares each projection table as
  `{name}-v{schemaVersion}` (PK/SK + GSIs from the manifest), on-demand billing, CMK, PITR, deletion
  protection **on**.
- **Retention window:** declare the current version and (during a transition) the previous version.
  When the manifest advances and the previous is safe to drop, remove it from the stack so `cdk deploy`
  deletes it. Encode "keep current + previous" so a mid-transition deploy never deletes the live or
  rollback table. *(Open decision C covers whether cleanup is CDK-driven here or tool-driven.)*
- `read-model-metadata` table: keep (already added). Confirm it is CDK-owned and not app-created.

### 6.2 IAM (`lib/magiq-media-stack.ts`)
- **Remove** the `table/media-*` control-plane wildcard for the operator role. Grant the operator
  **data-plane** on the exact table ARNs (current + previous version + `read-model-metadata`) plus the
  CMK. Only keep `DeleteTable` (exact ARNs) if cleanup is tool-driven (Open decision C).
- Deployed hosts (`apiFn`, `queryApiFn`, workers): grant data-plane on the versioned table ARNs
  (current + previous). The `media-*` post-flip wildcard can be tightened to the specific versioned
  names now that they are known at synth.

---

## 7. Rollout phasing (recommended)

- **Phase A — schema-versioned tables + CDK ownership.** §3.1–3.5, §4.1–4.6, §4.8–4.9, §5.1–5.5, §6.
  Handle the deploy→flip window by policy: additive changes are safe; for a breaking change, keep the
  window short / rotate right after deploy, and accept best-effort rollback. This alone delivers the
  CDK-reuse and IAM-tightening wins. Ship and validate first.
- **Phase B — version-aware projectors (zero-window breaking changes).** §3.6, §4.7, §5.1 (retain old
  projector). Add when the first breaking change actually needs a clean window. Larger blast radius in
  the projection pipeline; do it as its own effort with dedicated tests.

## 8. Suggested PR sequence

**aspnetcore-platform**
1. `feature/platform/schema-version-metadata` — new metadata model + store (version strings) + tests.
2. `feature/platform/schema-version-resolver` — options/snapshot/resolver naming by version + deployed-
   version lookup + tests.
3. `feature/platform/schema-version-orchestrator` — orchestrator targets a version, no runtime create,
   drop-old removed/replaced; README; tests.
4. *(Phase B, later)* `feature/platform/versioned-projectors` — version-aware dispatch + tests.

**magiq-media** (after platform packages publish; bump `MagiqPlatformVersion`)
5. `feature/chase/<ticket>-projection-schema-versions` — add `schemaVersion` to registrations; manifest
   tool + committed manifest + drift test.
6. `feature/chase/<ticket>-projection-replay-versioned` — tool/runner/runbook to the version model;
   integration test update; ADR + spec rewrite.

**cdk-magiq-media**
7. `feature/chase/<ticket>-projection-tables-cdk` — manifest-driven table construct, retention, IAM
   tighten.

## 9. Open decisions (confirm at kickoff, with recommendations)

- **A. Manifest source.** *Recommend:* generated-from-code manifest + drift test (code stays source of
  truth for GSIs). Alt: hand-maintained CDK defs + drift test.
- **B. Version granularity.** *Recommend:* per **TableId** (physical table). Co-located read models
  bump together — consistent with the rotation key.
- **C. Cleanup ownership.** *Recommend:* CDK-driven (remove previous from the stack next deploy →
  zero tool control-plane). Provide a tool-driven `cleanup` (single exact-ARN `DeleteTable`) as an
  operator convenience for faster reclaim.
- **D. Local/dev provisioning.** CDK does not run locally. *Recommend:* keep a thin app-side or
  tool-side "ensure tables" path (from the manifest) for local/dev and integration tests only, gated so
  it never runs in deployed environments.
- **E. Escape hatch for same-version corruption (no code change).** *Recommend:* "bump the version
  constant to force a fresh table." Add a transient standby only if this case proves common.
- **F. Phase B timing.** *Recommend:* ship Phase A now; schedule Phase B before the first breaking
  read-model change.

## 10. Testing strategy

- **Platform unit:** store atomicity on version attributes (begin/complete/abort/rollback guards);
  resolver precedence (override → active version → deployed version); snapshot TTL.
- **Platform integration (DynamoDB Local):** rebuild into a **pre-created** target-version table →
  flip → snapshot serves the new version → rollback restores previous. (No runtime create.)
- **magiq-media:** manifest drift test; `CollectionRotationE2ETests` updated to versioned names with the
  test creating the target table (CDK stand-in).
- **Phase B:** during a simulated transition, live writes keep the active (old) table correct while the
  rebuild fills the target; post-flip reconcile convergence; clean rollback after a breaking change.
- **CDK:** snapshot/assertion tests that the manifest yields the expected tables + retention + IAM ARNs.

## 11. Definition of done

- Projection tables are named `{base}-v{schemaVersion}`, created and retired by CDK from the committed
  manifest; the operator tool holds **no** `CreateTable` right (and no `DeleteTable` unless tool-driven
  cleanup is chosen).
- Metadata stores version strings; no runtime version counter.
- Operator can: bump a schema version → deploy (CDK makes `-v{new}`) → `rotate` → live reads follow the
  flip → `cleanup`/CDK removes `-v{old}`; `rollback` returns to the previous version cleanly.
- README, ADR, spec, and runbook describe the version-keyed model and the active-vs-target projection
  rule. (Phase B) breaking changes rebuild with zero window via retained previous-version projectors.

## 12. Reference — current implementation being replaced

- Platform: `.../Magiq.Platform.Projections.Stores.DynamoDb/Replay/*` (metadata, store, snapshot,
  resolver in `Schema/ProjectionTableNameResolver.cs`, provisioner, orchestrator, verifier, options),
  `ProjectionsTableMigration.cs`, `ProjectionsBuilderExtensions.cs`, `README.md`.
- magiq-media: `src/tools/ProjectionReplay/*` (Program/RotationHost/RotationRunner/TableRotationRegistry),
  module `*.ReadModel.Infrastructure` registrations, `docs/adrs/persistence-and-eventing.md`.
- cdk-magiq-media: `lib/constructs/dynamodb/platform-tables.construct.ts`, `lib/magiq-media-stack.ts`.
- Prior plan (versioned design): `plans/projection-tables/hot-swappable-projection-rotation-plan.md`.
