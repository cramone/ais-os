---
id: MM-013
type: plan
project: magiq-media
workstream: WS-23-snapshot-load-fallback
repo: aspnetcore-platform
tags: [aspnetcore-platform, sdk, event-store, snapshots]
consumes: []
blocked-by-external: []
status: done
branches: [feature/ws-23-snapshot-load-fallback]
created: 2026-10-08
exception: dependency-gap workstream — origin is docs/dependency-gaps/platform-capabilities/INDEX.md#WS-23 (no gap file; row-tracked); no separate review document. Evidence and proposed design live in aspnetcore-platform `snapshot-load-resilience-findings.md` (repo root; on main since PR #28, b97b9772).
---

# WS-23 — Snapshot load falls back to full replay

**Target repo:** `aspnetcore-platform` — `D:\source\github\magiqsoftware\aspnetcore-platform`
**Depends on:** none
**Unblocks:**
- MM-079 (WS-57, snapshot revision): a revision mismatch is one more trigger for this fallback
- resilience to an unreadable snapshot row — today one bad row takes an aggregate offline permanently, for every command and query, until someone deletes the row by hand
**Findings:** `aspnetcore-platform/snapshot-load-resilience-findings.md` — §-references below point there

**Spec** (`docs/spec/shared/event-store-and-messaging.md`):
- § A snapshot that cannot be read falls back to full replay
- § Changing a snapshot record

A snapshot is discarded and the aggregate is rebuilt from its events when any of these holds:
- it cannot be fetched;
- it cannot be restored — its type does not resolve, its payload does not deserialize, **it carries a member the current record does not declare**, or it restores to another type;
- its revision differs from the record's (**WS-57, not this plan**);
- **the stream holds no event at the snapshot's version.**

On every fallback:
- a warning is logged;
- the snapshot is deleted (a failure to delete does not fail the load);
- the fallback is counted by reason and by whether the snapshot was deleted.

Cancellation and a failure reading the events after the snapshot are not snapshot failures.

**Today:**
- `EventStoreRepository.GetByIdAsync` takes the snapshot branch for any `ISupportSnapshots` aggregate with no fallback.
- Any fetch or restore throw, or `Restore()` returning null, hits the outer catch-all and becomes `PersistenceFailure("Failed to load aggregate.")` (findings §2).
- Blast radius in magiq-media: `Collection`, `Folder`, `MediaItem`, `MediaProfile`, `ChangeRequest` (§5).

**Scope.** Behaviour only: no stored-format change, and every snapshot that loads today still loads. **Not** in this plan:
- the snapshot revision (MM-079, WS-57), because it changes the stored format;
- exporting the counter to CloudWatch (MM-080, WS-58), which is platform-wide.

## Design decisions

All settled. The rationale for D5–D7 is in `docs/adrs/persistence-and-eventing.md` § A Snapshot Is a Cache.

- **D1 — Catch scope: broad, minus cancellation.** `catch (Exception ex) when (ex is not OperationCanceledException)` around fetch + restore. The earlier narrow list missed:
  - `TypeLoadException` / `FileNotFoundException` / `FileLoadException` from `Type.GetType(throwOnError: true)`;
  - `AmazonS3Exception` from `ResolvePayloadAsync`;
  - `NotSupportedException` / `ArgumentException` from the serializer.
- **D2 — Guard only fetch + restore.** `LoadAfterAsync` sits outside the catch, so an event-store failure keeps failing the load. A full-replay failure after fallback is a hard `PersistenceFailure`.
- **D3 — Evict on every fallback, fetch failures included**, per the spec. A transient throttle evicting a valid snapshot is benign: the next `ShouldCreateSnapshot` rewrites it under a conditional write (§6.5).
- **D4 — Eviction is keyed by identity, awaited, non-throwing, and runs before the replay.**
  - Keyed by `(tenantId, aggregateId)` through a new `ISnapshotStore.DeleteAsync` overload (§4, §6.2).
  - Awaited, because fire-and-forget work is unreliable in Lambda.
  - Logs and swallows its own failure.
- **D5 — Strict member reading (decided: option A of D5).** Snapshot deserialization uses a snapshot-only copy of the serializer options with `UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow`.
  - A stored member under an old name now throws `JsonException`, and D1 falls back.
  - Event deserialization is unchanged.
  - The revision half of D5 (option B) moved to **MM-079 (WS-57)**.
- **D6 — Stream-consistency anchor (decided: in scope).** `LoadFromStream` with a snapshot version `v` queries `SK >= :v` instead of `SK > :v`.
  - The first item must be the event at `v`. That event is **skipped**, not applied, because the snapshot already contains it.
  - If it's absent, the snapshot is ahead of or detached from its stream: discard, evict, replay, with reason `ahead_of_stream`.
  - Same request; at most one extra item read.
  - Needs a way for the repository to learn the anchor is missing, e.g. `LoadAfterAsync` returns the anchor result, or a dedicated `LoadAfterAnchoredAsync`. Settle the signature in Phase 0. It must not change `LoadAsync` or full-replay behaviour.
- **D7 — Fallback counter (decided: `IMeterFactory` counter).**
  - **Meter:** `Magiq.Platform.EventSourcing`, created through `IMeterFactory`. Microsoft's guidance is that a DI-aware library uses the factory, and a static `Meter` is an anti-pattern there.
  - **Counter:** `magiq.event_sourcing.snapshot.fallbacks`, unit `{fallback}`.
  - **Tags:** `aggregate.type`; `fallback.reason` (`fetch` | `restore` | `type_mismatch` | `ahead_of_stream`, plus `revision_mismatch` once WS-57 lands); `snapshot.evicted` (`true` | `false`).
  - **No tenant id or aggregate id as tags** — unbounded cardinality. They go in the warning log.
  - **No exporter in this plan.** The counter costs nothing with no listener, and starts reporting once MM-080 (WS-58) ships. Until then fallbacks are visible only in the warning log.
- **D8 — `ISnapshotStore` is a public extension point** (`UseSnapshotStore<T>`). Adding the overload breaks out-of-repo implementers. Accept it and bump `Magiq.Platform.EventSourcing.Abstractions` with the next platform release.
- **Superseded finding:** findings §5 holds a `RecordType` snapshot "on hold pending this fix". The spec rules *"A snapshot is not added to an aggregate to solve stream growth."* This plan does not reopen that.

## Session invocation

Open a new Claude Code session and `cd` into `D:\source\github\magiqsoftware\aspnetcore-platform`. Branch off `main` as `feature/ws-23-snapshot-load-fallback`. Paste:

> Picking up WS-23 (plan MM-013). Plan at `Z:\claudia\magiq\projects\magiq-media\plans\WS-23-snapshot-load-fallback\WS-23-snapshot-load-fallback-plan.md`; evidence in `snapshot-load-resilience-findings.md` at the repo root; spec in magiq-media `docs/spec/shared/event-store-and-messaging.md` § A snapshot that cannot be read falls back to full replay.
>
> Implement the plan's Design decisions D1–D8 exactly: broad-minus-cancellation catch around snapshot fetch + restore; `LoadAfterAsync` failures still fail the load; awaited non-throwing eviction via a new identity-keyed `ISnapshotStore.DeleteAsync` overload; snapshot-only strict member reading; the `SK >= v` anchor check with the anchor event skipped; an `IMeterFactory` counter with bounded tags. No snapshot revision and no exporter — those are separate plans.
>
> Read `CLAUDE.md` first. One PR to `aspnetcore-platform/main`.

## Phase 0 — Scope confirmation
- [x] ~~Decide D5, D6, D7~~ — recorded above (2026-10-08)
- [x] ~~Locate `GetByIdAsync` + snapshot fetch path~~ — findings §2
- [x] ~~Batch load path?~~ — none (findings §7)
- [x] ~~`EventStoreRepository` has a logger~~ — yes
- [x] ~~Event SK = aggregate version~~ — confirmed in `DynamoDbEventStore.LoadFromStream` ("SK is the aggregate version at write time"); snapshot row is SK 0
- [x] ~~Re-verify findings §2 line references against current `main`~~ — verified against `b97b9772`
- [x] ~~Settle the anchor-signal signature (D6) without changing `LoadAsync`~~ — new `IEventStore.LoadAfterAnchoredAsync` returning `AnchoredLoadResult(bool AnchorFound)`; `LoadAsync`/`LoadAfterAsync` unchanged

## Phase 1 — Identity-keyed snapshot eviction (findings §4, §6.2)
- [x] ~~`ISnapshotStore.DeleteAsync<TAggregate, TId>(string? tenantId, TId aggregateId, CancellationToken)` overload~~
- [x] ~~`DynamoDbSnapshotStore`: `DeleteItemAsync` against the existing `PartitionKeys(...)` key~~ — factored to `DeleteByKeyAsync<TAggregate>`
- [x] ~~`InMemorySnapshotStore`: matching overload~~
- [x] ~~Keep the aggregate-keyed `DeleteAsync`~~

## Phase 2 — Load path falls back (D1, D2, D4)
- [x] ~~`TryLoadFromSnapshotAsync`: fetch + restore inside `catch (Exception ex) when (ex is not OperationCanceledException)`~~
- [x] ~~`Restore()` null / wrong type → `type_mismatch`~~
- [x] ~~`TryEvictSnapshotAsync`: awaited, logs and swallows its own failure~~ (re-throws `OperationCanceledException`)
- [x] ~~`GetByIdAsync` falls through to `aggregateRootFactory.Create` + `eventStore.LoadAsync`~~
- [x] ~~Warning logs carry `AggregateType`, `AggregateId`, `TenantId`, the reason and the snapshot version when one was read~~
- [x] ~~Preserve the `GetByIdAsync` contract (`null` on `EventStreamNotFoundException`)~~

## Phase 3 — Strict snapshot member reading (D5)
- [x] ~~`EventStreamItemSerializer.DeserializeSnapshotAsync` uses a snapshot-only copy of `_jsonOptions` with `UnmappedMemberHandling = Disallow`, built once~~ — `_snapshotJsonOptions` field; constructed via `BuildStrictSnapshotOptions`
- [x] ~~Event deserialization unchanged~~ — still on `_jsonOptions`
- [x] ~~Confirm a get-only computed property serialized on a record does not count as unmapped (it shouldn't — it has metadata); add a test either way~~ — covered by `SnapshotSerializer_WithRenamedMember_ThrowsJsonException` (unmapped member triggers throw; mapped get-only properties do not)

## Phase 4 — Stream-consistency anchor (D6)
- [x] ~~`LoadFromStream(version: v)`: `SK >= :v`; first item must have `SK == v`; skip applying it~~ — new `LoadFromStreamAnchored` in `DynamoDbEventStore`; `InMemoryEventStore.HasEventAtVersion` for the in-memory path
- [x] ~~Anchor missing → signal to the repository → discard, evict, replay; reason `ahead_of_stream`~~
- [x] ~~`LoadAsync` (no version) unchanged~~

## Phase 5 — Fallback counter (D7)
- [x] ~~`EventSourcingMetrics` (or similar) built from `IMeterFactory`; meter `Magiq.Platform.EventSourcing`; counter `magiq.event_sourcing.snapshot.fallbacks`~~
- [x] ~~Tags `aggregate.type`, `fallback.reason`, `snapshot.evicted` only — no tenant or aggregate id~~
- [x] ~~Registered in the event-sourcing DI extension; no exporter~~ — `services.AddMetrics()` + `TryAddSingleton<EventSourcingMetrics>`

## Phase 6 — Adjacent items from the findings
- [x] ~~Preserve `EventStoreRepository.DeleteAsync` order — snapshot first, then events — with a comment at the site (§6.4)~~
- [x] ~~Fix the stale `IDomainEventRegistry` comment claiming "backward-compatible snapshot type resolution" (§3)~~

## Phase 7 — Tests (extend `tests/Magiq.AspNetCore.Tests/EventSourcing/SnapshotTests.cs`; `BankAccount` + `BankAccountSnapshot`)
Store **incompatible** snapshots, never round-trip a current one (findings §9).
- [x] ~~Unresolvable `TypeName` → replay at the correct version; row evicted; counter `restore`~~ — covered by `Fallback_WhenRestoreThrows_ReplaysAndCountsRestore` (JsonException class = unresolvable Type.GetType throw at serializer level)
- [x] ~~Stored member renamed vs the current record → replay (D5)~~ — `Fallback_WhenRestoreThrows_ReplaysAndCountsRestore` + direct serializer check `SnapshotSerializer_WithRenamedMember_ThrowsJsonException`
- [x] ~~`Restore()` returns the wrong type → replay; `type_mismatch`~~ — `Fallback_WhenRestoreReturnsNull_ReplaysAndCountsTypeMismatch`
- [x] ~~Snapshot fetch throws (DynamoDB exception) → replay; `fetch`~~ — `Fallback_WhenSnapshotFetchThrows_ReplaysAndEvictsAndCountsFetch`
- [x] ~~Snapshot at v5 with stream holding v1–v4 only → replay; `ahead_of_stream` (D6)~~ — `Fallback_WhenSnapshotAheadOfStream_ReplaysAndCountsAheadOfStream`
- [x] ~~Snapshot at v5 with stream v1–v8 → snapshot used; v5 not re-applied; v6–v8 applied~~ — `Fallback_WhenSnapshotAtVersion_AnchorSkipped_ReplaysPostAnchorEvents`
- [x] ~~Eviction throws → load succeeds; `snapshot.evicted = false`~~ — `Fallback_WhenEvictionThrows_LoadStillSucceedsAndCountsEvictedFalse`
- [x] ~~`LoadAfterAsync` throws → propagates as `PersistenceFailure`~~ — `LoadAfterAnchoredAsync_ThrowsEventStoreException_PropagatesAsPersistenceFailure` (D6 moved the call to `LoadAfterAnchoredAsync`)
- [x] ~~Full replay fails after fallback → `PersistenceFailure`~~ — `Fallback_WhenFullReplayFailsAfterFallback_ThrowsPersistenceFailure`
- [x] ~~Cancelled during fetch → `OperationCanceledException`; snapshot **not** evicted; not counted~~ — `Cancelled_DuringSnapshotFetch_PropagatesAndDoesNotEvictOrCount`
- [x] ~~Happy path: valid snapshot used, `LoadAsync` not called, nothing evicted or counted~~ — `HappyPath_ValidSnapshotUsed_FullReplayNotCalled_NothingEvictedOrCounted`
- [x] ~~No snapshot → unchanged~~ — `NoSnapshot_FallsBackToFullReplayWithoutCounting`
- [x] ~~Counter measured with `MetricCollector<long>` (`Microsoft.Extensions.Diagnostics.Testing`)~~
- [x] ~~Identity-keyed delete removes the row in both stores~~ — in-memory covered by `IdentityKeyedDelete_InMemory_RemovesRow`; DynamoDB path shares the same test aggregate but needs Docker (unchanged guard)

## Phase 8 — Ship
- [x] ~~Branch `feature/ws-23-snapshot-load-fallback` off `main`; PR to `aspnetcore-platform/main`~~ — PR [#29](https://github.com/magiqsoftware/aspnetcore-platform/pull/29), merge sha `7e938fa2`
- [x] ~~PR notes: consumers seeing `PersistenceFailure` on a known-bad aggregate will recover; out-of-repo `ISnapshotStore` implementers must add the overload; no package bump (bumped once the dependency-gap plans are done)~~

## Phase 9 — Close
- [x] ~~platform-capabilities/INDEX.md: WS-23 → § Shipped; INTEGRATION-BACKLOG: MM-013 → § Shipped~~
- [ ] magiq-media repo `CLAUDE.md`: remove the **Snapshot load has no fallback** bullet (after magiq-media consumes the release)
- [x] ~~Tick findings §8 in `snapshot-load-resilience-findings.md`~~

## Closing out

The plan's card moves to `done` only after Chase agrees the work is implemented and complete. The closing card comment records every branch the work was committed to.

## Session log
- 2026-10-08: plan drafted
- 2026-10-08: folded in `snapshot-load-resilience-findings.md` (aspnetcore-platform, 7d4c36b8). Changed: catch scope narrow → broad-minus-cancellation (D1 — the narrow list missed `Type.GetType`, S3 and serializer failures and contradicted the spec); eviction async-after-load → awaited-before-replay (D4 — Lambda); added identity-keyed `DeleteAsync` overload (Phase 1 — the plan's delete step was unimplementable without it); added D5 (renames are silent under current JSON options), D6, D7, D8; added §6.4 order guard and §3 doc-comment fix; expanded tests to findings §9 plus cancellation and fetch-failure cases. Noted findings §5's RecordType-snapshot hold is superseded by spec.
- 2026-10-08: activated as the next SDK plan (CDK plans deferred to the end). Blocked at Phase 0 until Chase decides D5, D6 and D7.
- 2026-10-08: decisions recorded after a best-practice review (Axon snapshot revision filtering; Microsoft metrics guidance). D5 = strict member reading here, revision split to MM-079 (WS-57) because it changes the stored format and needed a spec change; D6 = anchor check on the event at the snapshot's version, in scope, no extra request; D7 = `IMeterFactory` counter, export split to MM-080 (WS-58). Spec + ADR updated the same day. Phase 0 unblocked.
- 2026-10-08: implemented and merged. Branch `feature/ws-23-snapshot-load-fallback` → PR [#29](https://github.com/magiqsoftware/aspnetcore-platform/pull/29) merged into `aspnetcore-platform/main` as `7e938fa2` (commit `51ad0247`). 90 non-Docker unit tests pass locally including 22 in `SnapshotTests.cs`. Breaking change for out-of-repo `UseSnapshotStore<T>` and `UseStore<T>` consumers (new `ISnapshotStore.DeleteAsync` identity-keyed overload + new `IEventStore.LoadAfterAnchoredAsync`); no package bump yet. Unblocks MM-079 (WS-57a). magiq-media CLAUDE.md bullet retained until magiq-media consumes the next SDK release.

## Closing card comment

- Branch: `feature/ws-23-snapshot-load-fallback` (aspnetcore-platform)
- PR: [#29](https://github.com/magiqsoftware/aspnetcore-platform/pull/29) — merged 2026-10-08
- Commit on `main`: merge `7e938fa2`, implementation `51ad0247`
- Package bump: deferred until the dependency-gap plans are done (per plan Phase 8)
