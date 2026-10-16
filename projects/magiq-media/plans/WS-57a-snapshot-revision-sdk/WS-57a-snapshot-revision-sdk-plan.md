---
id: MM-079
type: plan
project: magiq-media
workstream: WS-57a-snapshot-revision-sdk
repo: mgq-dotnet-platform
tags: [mgq-dotnet-platform, sdk, event-store, snapshots]
consumes: []
blocked-by-external: [MM-013]
status: shipped
branches: [feature/chase/MM-079-WS-57a-snapshot-revision-sdk]
pr: https://github.com/sprbrk-standard/mgq-dotnet-platform/pull/47
merge-sha: 8109ffdd
shipped: 2026-10-13
created: 2026-10-08
exception: dependency-gap workstream — origin is docs/dependency-gaps/platform-capabilities/INDEX.md#WS-57 (no gap file; row-tracked); split from MM-013 (WS-23) decision D5, option B.
---

# WS-57a — Snapshots carry a revision (SDK)

**Target repo:** `mgq-dotnet-platform` — `D:\source\github\sprbrk-standard\mgq-dotnet-platform`
**Depends on:** MM-013 (WS-23). A revision mismatch is one more trigger for WS-23's fallback, eviction and counter.
**Unblocks:** MM-081 (WS-57b) — magiq-media declares `ChangeRequestSnapshot` at revision 2

**Spec** (`docs/spec/shared/event-store-and-messaging.md`):
- § Snapshot storage: a `Revision` on the row, absent ⇒ 1.
- The comparison table: a revision declared as `[Snapshot(Revision = n)]`.
- § A snapshot that cannot be read: a stored revision that differs from the declared one discards the snapshot.
- § Changing a snapshot record: every change except a correctly defaulted addition increments the revision.

Rationale: `docs/adrs/persistence-and-eventing.md` § A Snapshot Is a Cache. Axon's `@Revision` + `RevisionSnapshotFilter` is the precedent.

**Today:** no snapshot revision exists. The only way to retire stale snapshots of a type is deleting their rows by hand in the release.

**This is a stored-format change:** a new attribute on every snapshot row. It is additive. Rows without it read as revision 1, so every snapshot that loads today still loads unless its record declares a higher revision.

## Design

- **`SnapshotAttribute`** (`[Snapshot(Revision = n)]`, `Revision >= 1`, default 1), in the abstractions assembly next to `ISnapshot`. A record without the attribute is revision 1.
- **Write:** `DynamoDbSnapshotStore.SaveAsync` stores the record's declared revision as a number attribute `Revision`. `InMemorySnapshotStore` keeps it alongside the snapshot.
- **Read:**
  - Resolve the type from `TypeName` as today, then read its declared revision.
  - The stored `Revision` (absent ⇒ 1) must equal it. On a mismatch, throw `SnapshotRevisionMismatchException` (stored, declared, type) **before** deserializing the payload.
  - WS-23's catch turns it into a fallback with reason `revision_mismatch`, plus eviction and the counter.
- **Revision lookup is cached per type**, since it runs on every snapshot load.
- **No upcaster and no migration.** Stale rows are discarded lazily on load.

## Session invocation

Open a new Claude Code session and `cd` into `D:\source\github\sprbrk-standard\mgq-dotnet-platform`. Confirm MM-013 (WS-23) is merged. Branch off `main` as `feature/ws-57a-snapshot-revision`. Paste:

> Picking up WS-57a (plan MM-079). Plan at `Z:\claudia\magiq\projects\magiq-media\plans\WS-57a-snapshot-revision-sdk\WS-57a-snapshot-revision-sdk-plan.md`. Spec: magiq-media `docs/spec/shared/event-store-and-messaging.md` § Snapshots.
>
> Add `[Snapshot(Revision = n)]` (default 1), store `Revision` on the snapshot row on save, compare stored (absent ⇒ 1) to declared on load before deserializing, and throw `SnapshotRevisionMismatchException` so WS-23's fallback discards, evicts and counts it with reason `revision_mismatch`. Read `CLAUDE.md` first. One PR to `mgq-dotnet-platform/main`.

## Phase 0 — Scope confirmation
- [ ] MM-013 (WS-23) merged: fallback, identity-keyed eviction, reason-tagged counter in place
- [ ] Read spec § Snapshot storage, § A snapshot that cannot be read, § Changing a snapshot record
- [ ] Locate where the snapshot `TypeName` is resolved (`EventStreamItemSerializer.DeserializeSnapshotAsync`) and where snapshot rows are written

## Phase 1 — Attribute + write path
- [ ] `SnapshotAttribute` (`Revision`, default 1, guard `>= 1`)
- [ ] Cached per-type revision lookup (absent attribute ⇒ 1)
- [ ] `DynamoDbSnapshotStore.SaveAsync` writes `Revision` (N)
- [ ] `InMemorySnapshotStore` stores the revision

## Phase 2 — Read path
- [ ] Read the stored `Revision` (absent ⇒ 1); compare to the declared revision after type resolution and before payload deserialization
- [ ] Mismatch → `SnapshotRevisionMismatchException(storedRevision, declaredRevision, snapshotType)`
- [ ] WS-23 reason mapping: this exception → `revision_mismatch`

## Phase 3 — Tests
- [ ] Row without `Revision`, record without attribute → loads (revision 1 = 1)
- [ ] Row without `Revision`, record at `[Snapshot(Revision = 2)]` → replay; row evicted; counter `revision_mismatch`
- [ ] Row at 2, record at 2 → loads
- [ ] Save writes the declared revision; the next load uses the snapshot
- [ ] Payload is not deserialized on a mismatch (a deliberately undeserializable payload still yields `revision_mismatch`, not `restore`)
- [ ] `SnapshotAttribute` rejects `Revision < 1`

## Phase 4 — Ship
- [ ] PR to `mgq-dotnet-platform/main`; note the additive stored-format change and that consumers retire stale snapshots by bumping `[Snapshot(Revision = n)]`
- [ ] No package bump (bumped once the dependency-gap plans are done)

## Phase 5 — Close
- [ ] platform-capabilities/INDEX.md: WS-57 (SDK half) → § Shipped; INTEGRATION-BACKLOG: MM-079 → § Shipped

## Closing out

The plan's card moves to `done` only after Chase agrees the work is implemented and complete. The closing card comment records every branch the work was committed to.

## Session log
- 2026-10-08: plan drafted — split from WS-23 decision D5 (option B), because a stored-format change and its spec change should not hold up WS-23's behaviour-only fix. Spec and ADR written the same day.
- 2026-10-13: shipped on branch `feature/chase/MM-079-WS-57a-snapshot-revision-sdk`.
  - New types in `Magiq.Platform.EventSourcing.Abstractions/Snapshots/`: `SnapshotAttribute` (`[Snapshot(Revision = n)]`, default 1, guard `Revision >= 1`), `SnapshotRevision.GetDeclaredRevision(Type)` with a `ConcurrentDictionary<Type, int>` cache (absent attribute reads as 1), `SnapshotRevisionMismatchException(storedRevision, declaredRevision, snapshotType)`.
  - `DynamoDbEventStoreTableSchema.RevisionAttribute = "Revision"`. `DynamoDbSnapshotStore` single + batch `SaveAsync` adds `Revision = N{declared}` to the `UpdateExpression`. `GetByIdAsync` reads the stored value (absent ⇒ 1) and passes it to a new overload `EventStreamItemSerializer.DeserializeEventStreamItemStreamToSnapshotAsync(stream, int storedRevision, ct)`. The overload resolves the CLR type from `TypeName` first, then compares revisions; a mismatch throws **before** `ResolvePayloadAsync` or `JsonSerializer.Deserialize` runs, so a stale payload cannot smuggle itself into a `restore`-reason fallback.
  - `InMemorySnapshotStore` upgraded to carry a stored revision per entry; save captures the declared revision at save time, get compares it against the current declared revision. New public test seam `SaveAtStoredRevisionAsync(ISnapshot, int storedRevision, ct)` lets unit tests simulate a row written at an older revision than the record now declares (there is no serialization boundary otherwise).
  - `EventSourcingMetrics.ReasonRevisionMismatch = "revision_mismatch"`. `EventStoreRepository.ClassifyFallbackReason` routes `SnapshotRevisionMismatchException` to it, so WS-23's existing fallback-eviction-counter path handles it without any further changes.
  - 7 unit tests under `tests/Magiq.AspNetCore.Tests/EventSourcing/SnapshotRevisionTests.cs`: attribute rejects `Revision < 1`, lookup absent-attribute → 1, lookup honours declared revision on a `[Snapshot(2)]` test type, in-memory default round trip, in-memory stored-ahead-of-declared throws `SnapshotRevisionMismatchException`, repo revision-mismatch falls back to replay + evicts + counter tagged `revision_mismatch`, and the serializer throws before deserializing payload (deliberately undeserializable payload still yields `revision_mismatch`, not `restore`). Full non-Docker suite 207 pass; Docker-dependent fixtures unchanged.
  - No `Magiq.Platform.*` version bump — batched once the dependency-gap plans are done.
- 2026-10-13: PR #47 merged to `mgq-dotnet-platform/main` as `8109ffdd`. Tower MM-079 (WS-57a) flipped `new` → `done`; MM-081 (WS-57b — magiq-media declares `ChangeRequestSnapshot` at revision 2) tagged `ready`. `docs/dependency-gaps/platform-capabilities/INDEX.md` + `INTEGRATION-BACKLOG` not present in the Z:/claudia/magiq snapshot — closure recorded in Tower + this session log only.
