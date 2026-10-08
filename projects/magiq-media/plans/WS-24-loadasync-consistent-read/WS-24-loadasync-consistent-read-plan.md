---
id: MM-008
type: plan
project: magiq-media
workstream: WS-24-loadasync-consistent-read
repo: aspnetcore-platform
tags: [aspnetcore-platform, sdk, event-store, consistency]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — origin is docs/dependency-gaps/platform-capabilities/INDEX.md#WS-24 (no gap file; row-tracked); no separate review document.
---

# WS-24 — `EventStoreRepository.LoadAsync` with `ConsistentRead = true`

**Target repo:** `aspnetcore-platform` — `D:\source\github\magiqsoftware\aspnetcore-platform`
**Depends on:** none
**Unblocks:** safer read-your-write for name-reservation + aggregate loads

Spec requires strongly-consistent reads of the event-store. Today `LoadAsync` defaults `ConsistentRead = false`, so a probe on a just-committed aggregate can answer "does not exist" and produce a duplicate name.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\magiqsoftware\aspnetcore-platform`. Paste:

> Picking up WS-24 (plan MM-008). Plan at `Z:\claudia\magiq\projects\magiq-media\plans\WS-24-loadasync-consistent-read\WS-24-loadasync-consistent-read-plan.md`.
>
> Flip `ConsistentRead = true` on `EventStoreRepository.LoadAsync` and snapshot read. Grep for other `ConsistentRead = false` in event-store layer and audit each. Document 2× RCU cost impact in PR description.
>
> Read `aspnetcore-platform/CLAUDE.md`. One PR to `aspnetcore-platform/main`.

## Phase 0 — Scope confirmation
- [ ] Read `docs/spec/shared/event-store-and-messaging.md` § Read Consistency
- [ ] Grep `ConsistentRead` across `aspnetcore-platform` event-store layer
- [ ] Confirm `LoadAsync` is the only path currently defaulting to `false`

## Phase 1 — Flip `ConsistentRead = true`
- [ ] `EventStoreRepository.LoadAsync` sets `ConsistentRead = true` on `Query` / `GetItem` calls
- [ ] Snapshot load: `ConsistentRead = true`
- [ ] Preserve any legitimate not-required reads (projector-side scans — audit each)

## Phase 2 — Cost impact note
- [ ] Document 2× RCU cost in PR description
- [ ] Confirm no RCU throttling risk in staging / prod event-store table

## Phase 3 — Tests
- [ ] Integration: write-then-read within same request path returns the write
- [ ] Request parameters assert `ConsistentRead = true` (SDK test-double)

## Phase 4 — Package + ship
- [ ] Bump `Magiq.Platform.*` version
- [ ] PR to `aspnetcore-platform/main`

## Phase 5 — Close
- [ ] platform-capabilities/INDEX.md: WS-24 → § Shipped

## Session log
- 2026-10-08: plan drafted
