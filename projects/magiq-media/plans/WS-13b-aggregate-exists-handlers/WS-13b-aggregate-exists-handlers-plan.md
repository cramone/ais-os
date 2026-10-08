---
id: MM-032
type: plan
project: magiq-media
workstream: WS-13b-aggregate-exists-handlers
repo: magiq-media
tags: [magiq-media, handlers, bulk, error-mapping]
consumes: []
blocked-by-external: [MM-007]
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — magiq-media integration half of WS-13; origin is docs/dependency-gaps/platform-capabilities/F020-duplicate-caller-id-exception.md; blocked by user policy (all external deps complete first).
---

# WS-13b — Map `AggregateAlreadyExistsException` → `409 IdAlreadyExists`

**Target repo:** `magiq-media` — `D:\source\github\sprbrk-standard\mgq-magiq-media`
**Depends on:** MM-007 (WS-13 SDK ship)
**User policy gate:** no magiq-media code change until all external deps ship.

Bulk handlers (e.g. `BulkCreateMediaItemsCommand`) currently catch `EventConcurrencyException` broadly. Spec: duplicate caller-supplied id is a distinct refusal (`409 IdAlreadyExists`), and bulk paths absorb it as "already created, skip."

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Confirm all external deps shipped. Paste:

> Picking up WS-13b (plan MM-032). Plan at `Z:\claudia\magiq\projects\magiq-media\plans\WS-13b-aggregate-exists-handlers\WS-13b-aggregate-exists-handlers-plan.md`. Depends on MM-007 (WS-13 SDK ship). User policy: no magiq-media change until all external deps shipped — confirm via `docs/dependency-gaps/INTEGRATION-BACKLOG.md`.
>
> SDK now throws `AggregateAlreadyExistsException` on duplicate caller-id. Map to `409 IdAlreadyExists` in `ProblemDetailsMapper`. Bulk handlers (`BulkCreateMediaItemsCommand`, any other bulk create) absorb as success for that item. Single-create endpoints: return 409.
>
> Read repo CLAUDE.md. PR to `develop` per GitFlow.

## Phase 0 — Scope confirmation
- [ ] Confirm MM-007 (WS-13) shipped; `AggregateAlreadyExistsException` available on SDK NuGet
- [ ] Confirm all other 24 external deps shipped (per INTEGRATION-BACKLOG.md)
- [ ] Enumerate bulk handlers + single-create handlers

## Phase 1 — ProblemDetails mapping
- [ ] `ProblemDetailsMapper`: `AggregateAlreadyExistsException` → `409 IdAlreadyExists`
- [ ] Include `TenantId`, `AggregateType`, `AggregateId` from exception payload in `extensions` fields

## Phase 2 — Bulk handler absorb
- [ ] Bulk handlers catch specifically → treat item as success (idempotent create)
- [ ] Preserve per-item result reporting (skipped vs created)

## Phase 3 — Tests
- [ ] Unit: duplicate caller-id on single-create → 409 with correct extensions
- [ ] Unit: duplicate caller-id in bulk → item marked success, overall batch succeeds
- [ ] Integration: bulk with mix of new + duplicate → correct per-item results

## Phase 4 — Ship
- [ ] PR to `develop`
- [ ] Update F020 to `shipped (full)` once this merges

## Phase 5 — Close
- [ ] F020 → `shipped (full — SDK + magiq-media)`
- [ ] INTEGRATION-BACKLOG: WS-13b → § Shipped
- [ ] Remove `AggregateAlreadyExistsException not raised` bullet from `CLAUDE.md` § Known deferred/partial work

## Session log
- 2026-10-08: plan drafted (blocked on all 25 external deps shipping + user policy)
