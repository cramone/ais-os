---
id: MM-013
type: plan
project: magiq-media
workstream: WS-23-snapshot-load-fallback
repo: aspnetcore-platform
tags: [aspnetcore-platform, sdk, event-store, snapshots]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — origin is docs/dependency-gaps/platform-capabilities/INDEX.md#WS-23 (no gap file; row-tracked); no separate review document. Evidence and proposed design live in aspnetcore-platform `snapshot-load-resilience-findings.md` (repo root, added 2026-09-02 in 7d4c36b8 on feature/guid-projection-rotation — not yet on main).
---

# WS-23 — Snapshot load falls back to full replay

**Target repo:** `aspnetcore-platform` — `D:\source\github\magiqsoftware\aspnetcore-platform`
**Depends on:** none
**Unblocks:** resilience to an unreadable snapshot row — today one bad row takes an aggregate offline permanently, for every command and query, until someone deletes the row by hand
**Findings:** `aspnetcore-platform/snapshot-load-resilience-findings.md` — §-references below point there

**Spec** (`docs/spec/shared/event-store-and-messaging.md` § A snapshot that cannot be read falls back to full replay):
a snapshot that cannot be **fetched or restored** falls back to full replay — warning logged, snapshot
discarded, aggregate rebuilt from events — and the stale snapshot is deleted so the next
`ShouldCreateSnapshot` writes a fresh one. Snapshot save failure is already survivable.

**Today:** `EventStoreRepository.GetByIdAsync` takes the snapshot branch for any `ISupportSnapshots`
aggregate with no fallback; any fetch/restore throw (or `Restore()` returning null) hits the outer
catch-all and becomes `PersistenceFailure("Failed to load aggregate.")`. The full-replay path below it is
unreachable once a snapshot row exists (findings §2). Blast radius in magiq-media: `Collection`, `Folder`,
`MediaItem`, `MediaProfile`, `ChangeRequest` (§5).

## Design decisions

Settled here unless marked **Decision**. Rationale lives in the plan, not the spec.

- **D1 — Catch scope: broad, minus cancellation.** Wrap fetch + restore in
  `catch (Exception ex) when (ex is not OperationCanceledException)`.
  *Replaces the earlier narrow list (`AmazonDynamoDBException` + `JsonException`/`InvalidDataException`).*
  That list contradicts the spec ("cannot be fetched **or** restored") and misses the failures that
  actually occur:
  - `TypeLoadException` / `FileNotFoundException` / `FileLoadException` from
    `Type.GetType(item.TypeName, throwOnError: true)` — the type-moved / assembly-renamed case, findings test 1
  - `AmazonS3Exception` from `ResolvePayloadAsync` — the SDK serializer can S3-offload a snapshot payload
  - `NotSupportedException` / `ArgumentException` from `JsonSerializer.Deserialize`
  Cancellation is excluded because a cancelled request is not a bad snapshot and must not evict it.
- **D2 — Guard only fetch + restore.** `LoadAfterAsync` sits **outside** the new catch — an event-store
  failure is real and keeps propagating to the existing outer catch (`PersistenceFailure`). A full-replay
  failure after fallback is likewise a hard `PersistenceFailure` (§6.1).
- **D3 — Evict on every fallback, fetch failures included.** The spec says discard on both. Consequence:
  a transient `GetItem` throttle evicts a snapshot that was valid. That's acceptable — the next
  `ShouldCreateSnapshot` rewrites it, and `SaveAsync`'s conditional write
  (`attribute_not_exists(Version) OR Version < :Version`) prevents a torn or stale row (§6.5).
  Not a spec question.
- **D4 — Eviction is identity-keyed, awaited, non-throwing, and runs before the replay.**
  - **Identity-keyed:** `ISnapshotStore.DeleteAsync(TAggregate)` needs the restored aggregate, which is
    exactly what is missing when restore fails (§4). That needs a new overload keyed by
    `(tenantId, aggregateId)` (§6.2).
  - **Awaited, not async:** *Replaces the earlier "async-delete after successful load".* Fire-and-forget
    work is unreliable in Lambda (the execution environment freezes after the response). The findings
    evict inline before replay; the cost is one `DeleteItem` on an already-degraded path.
  - **Non-throwing:** `TryEvictSnapshotAsync` logs and swallows. A failed eviction must not turn a
    degraded read back into the outage.
- **D5 — Member renames are invisible today. Decision (Chase).** `JOptions.Default` sets no
  `UnmappedMemberHandling`, so a renamed snapshot member deserializes to `default` with **no exception**:
  - fallback never triggers
  - the aggregate loads in a wrong state, silently

  The spec forbids renames (§ Snapshot records are effectively frozen), but also says renames "cost
  latency, never availability", and findings test 2 asserts rename → replay. Both hold only if
  deserialization is strict. Options:
  - **(a) Recommended.** Deserialize snapshots — snapshots only, not events — with a copy of the options
    set to `UnmappedMemberHandling = Disallow`. A stored member under an old name then throws
    `JsonException`, and D1 falls back. This does not detect a member that was removed from the stored
    payload; that stays covered by the defaulted-member rule and its architecture test.
  - **(b)** Keep the current options, drop findings test 2, and rely on the frozen-record rule plus code
    review.
- **D6 — Snapshot ahead of its stream (§6.3). Decision (Chase).** Default **out of scope**. Detecting it
  needs the stream head version, and `LoadAfterAsync` returning no events does not tell an up-to-date
  snapshot apart from one that is ahead, so it costs an extra read on every snapshot load. Record the
  outcome in § Session log either way.
- **D7 — Fallback metric. Decision (Chase).** No `System.Diagnostics.Metrics.Meter` exists anywhere in
  `src/platform` today. Options:
  - **(a) Recommended.** Add `Meter("Magiq.Platform.EventSourcing")` with counter `snapshot.fallback`,
    tagged `aggregate_type`, `reason` (`fetch` | `restore` | `type_mismatch`) and `evicted`
    (`true` | `false`). OpenTelemetry is already in the platform's Observability layer.
  - **(b)** Rely on the structured warning log plus a CloudWatch metric filter in `cdk-magiq-media`.
- **D8 — `ISnapshotStore` is a public extension point** (`UseSnapshotStore<T>`). Adding an interface
  member breaks any out-of-repo implementer. In-repo there are two (`DynamoDbSnapshotStore`,
  `InMemorySnapshotStore`). Accept the break and bump `Magiq.Platform.EventSourcing.Abstractions`;
  call it out in the release note.
- **Superseded finding:** §5 holds a `RecordType` snapshot "on hold pending this fix". The spec has since
  ruled *"A snapshot is not added to an aggregate to solve stream growth."* This fix does **not** reopen
  that question.

## Session invocation

Open a new Claude Code session and `cd` into `D:\source\github\magiqsoftware\aspnetcore-platform`. Paste:

> Picking up WS-23 (plan MM-013). Plan at `Z:\claudia\magiq\projects\magiq-media\plans\WS-23-snapshot-load-fallback\WS-23-snapshot-load-fallback-plan.md`; evidence and design in `snapshot-load-resilience-findings.md` at the repo root.
>
> Implement findings §6.1 + §6.2 as amended by the plan's Design decisions: broad catch around snapshot fetch + restore excluding `OperationCanceledException`; `LoadAfterAsync` outside the catch; awaited non-throwing eviction via a new identity-keyed `ISnapshotStore.DeleteAsync` overload; fall through to full replay. Apply D5/D6/D7 as recorded in the plan's session log — stop and ask if they are not yet decided.
>
> Read `aspnetcore-platform/CLAUDE.md`. Branch off `main`. One PR to `aspnetcore-platform/main`.

## Phase 0 — Scope confirmation
- [ ] Chase decides D5, D6, D7 — record in § Session log
- [ ] Re-verify findings §2 line references against current `main` (findings dated 2026-09-02)
- [x] ~~Locate `EventStoreRepository.GetByIdAsync` + snapshot fetch path~~ — findings §2 call-chain table
- [x] ~~Confirm current path returns `PersistenceFailure` on snapshot read/restore failure~~ — findings §2
- [x] ~~Check for a batch load path with the same pattern~~ — none; `snapshotStore.GetByIdAsync` has exactly one caller (findings §7)
- [x] ~~`EventStoreRepository` has a logger~~ — `ILogger<EventStoreRepository<TAggregate, TId>>` already injected

## Phase 1 — Identity-keyed snapshot eviction (findings §4, §6.2)
- [ ] `ISnapshotStore.DeleteAsync<TAggregate, TId>(string? tenantId, TId aggregateId, CancellationToken)` overload, same constraints as the existing one
- [ ] `DynamoDbSnapshotStore`: `DeleteItemAsync` against the existing `PartitionKeys(tenantId, aggregateType, aggregateId)` key — no new key derivation
- [ ] `InMemorySnapshotStore`: matching overload
- [ ] Leave the existing aggregate-keyed `DeleteAsync` in place

## Phase 2 — Load path falls back (findings §6.1; D1, D2, D4)
- [ ] `EventStoreRepository.TryLoadFromSnapshotAsync` — fetch + restore inside `catch (Exception ex) when (ex is not OperationCanceledException)`
- [ ] `Restore()` returning null / wrong type → warning (`type_mismatch`) + evict + replay
- [ ] `LoadAfterAsync` outside the catch
- [ ] `TryEvictSnapshotAsync` — awaited, logs and swallows its own failure
- [ ] `GetByIdAsync` rewired: snapshot result if non-null, else `aggregateRootFactory.Create` + `eventStore.LoadAsync`
- [ ] Warning logs carry `AggregateType`, `AggregateId`, `TenantId`, and the snapshot version when one was read
- [ ] Preserve `GetByIdAsync` return contract (`null` on `EventStreamNotFoundException`)

## Phase 3 — Strict snapshot deserialization (D5 — only if (a))
- [ ] `EventStreamItemSerializer.DeserializeSnapshotAsync` uses a snapshot-only copy of `_jsonOptions` with `UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow`
- [ ] Event deserialization unchanged

## Phase 4 — Fallback metric (D7)
- [ ] Per the decision: `Meter` + `snapshot.fallback` counter, or document the log-based metric filter for `cdk-magiq-media`

## Phase 5 — Adjacent items from the findings
- [ ] Preserve `EventStoreRepository.DeleteAsync` order — snapshot first, then events — and comment why at the site (§6.4)
- [ ] Settle the stale `IDomainEventRegistry` doc comment claiming "backward-compatible snapshot type resolution" — snapshots call `Type.GetType` directly (§3)
- [ ] Apply D6 outcome (or confirm out of scope)

## Phase 6 — Tests (extend `tests/Magiq.AspNetCore.Tests/EventSourcing/SnapshotTests.cs`, `BankAccount` + `BankAccountSnapshot`)
Every existing snapshot test reads back the snapshot it wrote — coverage must store an **incompatible** snapshot (findings §9).
- [ ] Stored `TypeName` resolves to no loadable type → loads via replay at the correct version; snapshot row gone
- [ ] Stored payload with a member renamed vs the current record → loads via replay *(only if D5 = (a); otherwise delete this case)*
- [ ] `Restore()` returns the wrong type → loads via replay; evicted
- [ ] Snapshot `GetByIdAsync` throws (DynamoDB exception) → loads via replay; evicted
- [ ] Eviction throws → load still succeeds (degraded, not failed)
- [ ] `LoadAfterAsync` throws → still propagates as `PersistenceFailure`; not swallowed
- [ ] Full replay fails after fallback → `PersistenceFailure`
- [ ] Cancelled token during snapshot fetch → `OperationCanceledException` propagates; snapshot **not** evicted
- [ ] Happy path unchanged: valid snapshot used, `LoadAsync` not called, nothing evicted
- [ ] No snapshot (fresh aggregate) → unchanged
- [ ] `InMemorySnapshotStore` and `DynamoDbSnapshotStore` identity-keyed delete removes the row

## Phase 7 — Package + ship
- [ ] Bump `Magiq.Platform.EventSourcing`, `Magiq.Platform.EventSourcing.Abstractions` (interface change — D8), `Magiq.Platform.EventSourcing.DynamoDb`
- [ ] Release note (findings §10): consumers seeing `PersistenceFailure` on a known-bad aggregate will see it recover; manual snapshot-row cleanup scripts can be retired; out-of-repo `ISnapshotStore` implementers must add the overload
- [ ] PR to `aspnetcore-platform/main`

## Phase 8 — Close
- [ ] platform-capabilities/INDEX.md: WS-23 → § Shipped
- [ ] magiq-media repo `CLAUDE.md`: remove the **Snapshot load has no fallback** bullet from § Known deferred/partial work (after magiq-media consumes the package)
- [ ] Tick findings §8 checklist in `snapshot-load-resilience-findings.md`, or delete the doc once the PR carries its content

## Session log
- 2026-10-08: plan drafted
- 2026-10-08: folded in `snapshot-load-resilience-findings.md` (aspnetcore-platform, 7d4c36b8). Changed: catch scope narrow → broad-minus-cancellation (D1 — the narrow list missed `Type.GetType`, S3 and serializer failures and contradicted the spec); eviction async-after-load → awaited-before-replay (D4 — Lambda); added identity-keyed `DeleteAsync` overload (Phase 1 — the plan's delete step was unimplementable without it); added D5 (renames are silent under current JSON options), D6, D7, D8; added §6.4 order guard and §3 doc-comment fix; expanded tests to findings §9 plus cancellation and fetch-failure cases. Noted findings §5's RecordType-snapshot hold is superseded by spec.
