---
id: MM-047
type: plan
project: magiq-media
workstream: WS-36b-projection-lag-metric
repo: magiq-media
tags: [magiq-media, projections, metrics, observability]
consumes: []
blocked-by-external: [MM-027]
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — magiq-media integration half of WS-36.
---

# WS-36b — Emit `MagiqMedia/Projections/Lag` metric from projectors

**Target repo:** `magiq-media`
**Depends on:** MM-027 (WS-36a infra — dashboard + alarms)
**User policy gate:** no magiq-media code change until all external deps ship.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-36b (plan MM-047). Infra (MM-027) ships dashboard + alarms waiting on metric.
>
> `Projectors.ReadModel` + `Projectors.Search` emit `MagiqMedia/Projections/Lag` on each successful apply, dimensions `aggregate_type`, `projector`, unit seconds (now - event timestamp).
>
> PR to `develop`.

## Phase 0 — Scope confirmation
- [ ] Confirm MM-027 shipped (dashboard renders empty)
- [ ] Metric contract: `MagiqMedia/Projections/Lag`, dimensions `aggregate_type`, `projector`

## Phase 1 — Emit from `Projectors.ReadModel`
- [ ] On each successful event apply: emit metric with `aggregate_type` + `projector = ReadModel`
- [ ] Value: `(DateTime.UtcNow - event.OccurredAt).TotalSeconds`

## Phase 2 — Emit from `Projectors.Search`
- [ ] Same metric, `projector = Search`

## Phase 3 — Tests
- [ ] Unit: metric emitted on successful apply
- [ ] Unit: dimensions correct
- [ ] Integration: dashboard shows data after deploy

## Phase 4 — Ship
- [ ] PR to `develop`

## Phase 5 — Close
- [ ] projections/INDEX.md: WS-36 → § Shipped
- [ ] INTEGRATION-BACKLOG: WS-36b → § Shipped
- [ ] Remove `Projection lag unmeasured` bullet from `CLAUDE.md`

## Session log
- 2026-10-08: plan drafted (blocked on MM-027 + user policy)
