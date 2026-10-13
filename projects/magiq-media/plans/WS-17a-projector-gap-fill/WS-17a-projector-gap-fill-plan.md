---
id: MM-019
type: plan
project: magiq-media
workstream: WS-17a-projector-gap-fill
repo: aspnetcore-platform
tags: [aspnetcore-platform, sdk, projections, ordering]
consumes: []
blocked-by-external: []
status: shipped
branches: [feature/chase/MM-019-WS-17a-projector-gap-fill]
pr: https://github.com/magiqsoftware/aspnetcore-platform/pull/38
merge-sha: 3eb18200
shipped: 2026-10-12
created: 2026-10-08
exception: dependency-gap workstream — origin is docs/dependency-gaps/platform-capabilities/F022-projector-gap-fill-read.md and INDEX.md#WS-17; no separate review document.
---

# WS-17a — Projector stream-tail gap-fill read

**Target repo:** `aspnetcore-platform` — `D:\source\github\magiqsoftware\aspnetcore-platform`
**Depends on:** none
**Unblocks:** MM-037 (WS-17b — regression tests on magiq-media)

Delivers F022. Today `ProjectionDispatcher` only compares `ProjectedVersion` — a v5 arriving after v6 is silently dropped. Spec: on gap, read stream tail and apply in order.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\magiqsoftware\aspnetcore-platform`. Paste:

> Picking up WS-17a (plan MM-019). Plan at `Z:\claudia\magiq\projects\magiq-media\plans\WS-17a-projector-gap-fill\WS-17a-projector-gap-fill-plan.md`. Gap: `D:\source\github\sprbrk-standard\mgq-magiq-media\docs\dependency-gaps\platform-capabilities\F022-projector-gap-fill-read.md`.
>
> On gap `N > P + 1`: read stream `(P, N]` with `ConsistentRead = true`, apply events sequentially, advance `ProjectedVersion` after each. Apply failure mid-batch: do not advance past failure. Multi-facet rows keep per-facet `SourceVersion`.
>
> PR to `aspnetcore-platform/main`.

## Phase 0 — Scope confirmation
- [ ] Read F022 § Required-shape + § Detection signals
- [ ] Locate `ProjectionDispatcher`, `IReadModel.ProjectedVersion`, `IEventStore.ReadStreamAsync`
- [ ] Confirm current implementation silently skips

## Phase 1 — Gap detection
- [ ] Load current `ProjectedVersion = P`; receive event `v=N`
- [ ] `N == P + 1` → apply as today
- [ ] `N > P + 1` → gap path (phase 2)
- [ ] `N <= P` → duplicate (idempotent skip)

## Phase 2 — Gap-fill read
- [ ] Read stream versions `(P, N]` from event store (`ConsistentRead = true`)
- [ ] Apply each sequentially; update `ProjectedVersion` after each successful apply
- [ ] Mid-batch failure: do not advance past failure; surface so SQS retries

## Phase 3 — Multi-facet-row handling
- [ ] Multi-facet rows keep existing `SourceVersion`-per-facet convention
- [ ] Gap-fill reads events once, dispatches to each facet handler

## Phase 4 — Instrumentation
- [ ] Metric `projector_gap_fill_count` with `aggregate_type`, `gap_size`
- [ ] Log at Information: "gap-fill applied events v{P+1}..v{N} for {aggregate_type}/{id}"

## Phase 5 — Tests
- [ ] Unit: adjacent event (v=P+1) → direct apply (no gap-fill)
- [ ] Unit: gap of 1 → reads v=P+1, applies both
- [ ] Unit: gap of 5 → reads 5, applies in order
- [ ] Unit: apply failure on event 3 of 5 → `ProjectedVersion` stops at 2
- [ ] Unit: duplicate (v<=P) → skip

## Phase 6 — Package + ship
- [ ] Bump `Magiq.Platform.*` version
- [ ] PR to `aspnetcore-platform/main`

## Phase 7 — Close
- [ ] F022: `status: shipped (SDK portion)`
- [ ] platform-capabilities/INDEX.md: WS-17 split — `WS-17a shipped`, `WS-17b open`
- [ ] INTEGRATION-BACKLOG: MM-037 (WS-17b) ready

## Session log
- 2026-10-08: plan drafted.
- 2026-10-12: scoped (b) — ship gap-fill on BOTH single + batch dispatch paths rather than only single, because the F022 defect scenario (batchSize=10 SQS delivery, inter-batch reorder) lives in the batch path. Shipping only single would close the test case and leave production broken.
  - `IEventStore.ReadStreamSegmentAsync(tenantId, aggregateType, aggregateId, fromExclusive, toInclusive)` added as mandatory interface member. DynamoDb impl queries SK BETWEEN :from+1 AND :to, ConsistentRead=true, filters by `IVersionedDomainEvent.AggregateVersion` for rows that bundle events straddling the boundary. InMemory impl filters append log. Three test-stub `IEventStore` impls in SnapshotTests updated. Breaking for any out-of-repo impls.
  - `AggregateStreamIdentity` record + `IGapFillAwareProjectionHandler<TEvent, TModel>` opt-in interface in Projections.Abstractions. Handlers that don't implement keep fence-only behaviour — non-breaking to existing projectors.
  - `ProjectionDispatcher` gains mandatory `IEventStore` + `ProjectionDispatcherMetrics` deps. `GapFillAsync` helper runs on both `DispatchAsync` and before the first event of each per-key group in `DispatchBatchAsync`. Each gap event is persisted individually so a mid-gap failure leaves `ProjectedVersion` at the last successful apply and bubbles `ProjectionException` for SQS retry. Non-`TEvent` events in the stream advance nothing (per spec). Fence still refuses duplicate apply when a concurrent dispatcher closed the same gap.
  - `projector.gap_fill_events` counter on `Magiq.Platform.Projections` meter, tagged `aggregate.type` + `model.type`. `AddProjections` wires `services.AddMetrics()` + singleton `ProjectionDispatcherMetrics`.
  - Multi-facet `IProjector<TRow>` reshape (spec item: per-facet `SourceVersion` slots) explicitly out of scope. Spec's "SourceVersion per facet convention" stays handler-level. Deferred as its own workstream when it bites in practice.
  - 8 new unit tests green locally; full solution build clean; 61 all-WS regression tests pass together.
- 2026-10-12: PR #38 merged to `aspnetcore-platform/main` as `3eb18200`. F022 → `status: sdk-shipped` with remainder noted. platform-capabilities/INDEX.md WS-17 split: WS-17a shipped row, WS-17b flipped to `ready`. INTEGRATION-BACKLOG MM-019 moved to § Shipped; MM-037 (WS-17b) flipped `new` → `ready`. Readiness summary bumped 62→61 `new`, 5→6 `ready`, 10→11 `shipped`.
