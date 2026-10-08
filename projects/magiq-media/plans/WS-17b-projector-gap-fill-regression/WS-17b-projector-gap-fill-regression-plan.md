---
id: MM-037
type: plan
project: magiq-media
workstream: WS-17b-projector-gap-fill-regression
repo: magiq-media
tags: [magiq-media, projections, tests]
consumes: []
blocked-by-external: [MM-019]
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — magiq-media integration half of WS-17 F022; regression-test only.
---

# WS-17b — Projector gap-fill regression tests

**Target repo:** `magiq-media`
**Depends on:** MM-019 (WS-17a SDK)
**User policy gate:** no magiq-media code change until all external deps ship.

SDK gap-fill is transparent to projectors. This workstream adds regression tests at the magiq-media integration layer to guarantee no projector relies on strict sequential dispatch.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-17b (plan MM-037). SDK (MM-019) ships gap-fill. Add integration tests exercising out-of-order delivery to each projector (`Projectors.ReadModel`, `Projectors.Search`).
>
> PR to `develop`.

## Phase 0 — Scope confirmation
- [ ] Confirm MM-019 shipped
- [ ] Enumerate projectors in magiq-media

## Phase 1 — Integration tests
- [ ] Inject out-of-order events (v3 before v2) to each projector
- [ ] Assert read model matches sequential-order outcome after gap-fill
- [ ] Assert metric `projector_gap_fill_count` emitted

## Phase 2 — Ship
- [ ] PR to `develop`

## Phase 3 — Close
- [ ] F022: shipped (full)
- [ ] INTEGRATION-BACKLOG: WS-17b → § Shipped
- [ ] Remove `Projector stream-tail gap-fill` bullet from `CLAUDE.md`

## Session log
- 2026-10-08: plan drafted (blocked on MM-019 + user policy)
