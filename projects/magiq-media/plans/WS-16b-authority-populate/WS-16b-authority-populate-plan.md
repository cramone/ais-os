---
id: MM-036
type: plan
project: magiq-media
workstream: WS-16b-authority-populate
repo: magiq-media
tags: [magiq-media, authority, retention, legal-hold, audit]
consumes: []
blocked-by-external: [MM-018]
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — magiq-media integration half of WS-16 F094.
---

# WS-16b — Populate `Authority` on retention / legal-hold / archival / court-order flows

**Target repo:** `magiq-media`
**Depends on:** MM-018 (WS-16a SDK)
**User policy gate:** no magiq-media code change until all external deps ship.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-16b (plan MM-036). SDK (MM-018) ships `Authority` on `MessageMetadata` + envelope + propagation.
>
> Populate `Authority` on relevant integration events: retention actions (schedule id), legal-hold (hold id), archival decisions, court-order processing. Confirm consuming handlers propagate (SDK auto-copies). Audit test fixtures to assert `Authority` present end-to-end.
>
> PR to `develop`.

## Phase 0 — Scope confirmation
- [ ] Confirm MM-018 shipped
- [ ] Enumerate authority-bearing flows in `docs/spec/`: retention, legal-hold, archival, court-order, ExternalRetentionEventPinned
- [ ] Enumerate integration events in each flow

## Phase 1 — Command → event populate
- [ ] Retention commands populate `Authority = (RetentionSchedule, scheduleId)`
- [ ] Legal-hold commands populate `Authority = (LegalHold, holdId)`
- [ ] Archival-decision commands populate `Authority = (ArchivalDecision, decisionRef)`
- [ ] Court-order commands populate `Authority = (CourtOrder, orderRef, narrative)`
- [ ] ExternalRetentionEventPinned populates `Authority = (ExternalEvent, kind, authority-string)`

## Phase 2 — Propagation audit
- [ ] For each flow: trace command → event → outbox → SNS → consumer → downstream event; confirm Authority preserved
- [ ] Any manual event raise within handler: ensure Authority inherits from context

## Phase 3 — Tests
- [ ] Unit: command carries Authority → raised event's envelope has it
- [ ] Integration: downstream handler consumes authority-event → its raised event has same Authority

## Phase 4 — Ship
- [ ] PR to `develop`

## Phase 5 — Close
- [ ] F094: shipped (full)
- [ ] INTEGRATION-BACKLOG: WS-16b → § Shipped
- [ ] Remove `Authority on MessageMetadata` bullet from `CLAUDE.md`

## Session log
- 2026-10-08: plan drafted (blocked on MM-018 + user policy)
