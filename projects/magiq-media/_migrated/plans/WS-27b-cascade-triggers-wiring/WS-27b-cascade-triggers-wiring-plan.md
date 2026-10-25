---
id: MM-046
type: plan
project: magiq-media
workstream: WS-27b-cascade-triggers-wiring
repo: magiq-media
tags: [magiq-media, fan-out, sqs, cascade]
consumes: []
blocked-by-external: [MM-026]
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — magiq-media integration half of WS-27.
---

# WS-27b — Fan-out worker subscribes to `media-cascade-triggers`; remove self-re-send

**Target repo:** `magiq-media`
**Depends on:** MM-026 (WS-27a infra — queue + reserved concurrency)
**User policy gate:** no magiq-media code change until all external deps ship.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-27b (plan MM-046). Infra (MM-026) ships `media-cascade-triggers`.
>
> Fan-out worker consumer binds to `media-cascade-triggers` instead of self-re-sending to `media-cross-module-events`. Remove self-send code path. Bind `Media:Catalog:FanOut:MaxDispatchPerTenantPerInvocation` setting.
>
> PR to `develop`.

## Phase 0 — Scope confirmation
- [ ] Confirm MM-026 shipped (queue + concurrency set in each env)
- [ ] Locate fan-out worker self-re-send code path

## Phase 1 — Consumer binding
- [ ] `CollectionArchiveFanOutWorker` + `FolderArchiveFanOutWorker` bind to `media-cascade-triggers`
- [ ] Remove `media-cross-module-events` self-send
- [ ] Preserve filter semantics (per-tenant dispatch budget)

## Phase 2 — Per-tenant fairness
- [ ] `Media:Catalog:FanOut:MaxDispatchPerTenantPerInvocation` bound
- [ ] Verify fair-queue routing from platform

## Phase 3 — Tests
- [ ] Unit: cascade event triggers fan-out worker consumer
- [ ] Unit: no self-send path on cascade
- [ ] Integration: multi-tenant cascade respects per-tenant budget

## Phase 4 — Ship
- [ ] PR to `develop`

## Phase 5 — Close
- [ ] platform-capabilities/INDEX.md: WS-27 → § Shipped
- [ ] INTEGRATION-BACKLOG: WS-27b → § Shipped
- [ ] Remove `Concurrency isolation and fan-out fairness` bullet from `CLAUDE.md`

## Session log
- 2026-10-08: plan drafted (blocked on MM-026 + user policy)
