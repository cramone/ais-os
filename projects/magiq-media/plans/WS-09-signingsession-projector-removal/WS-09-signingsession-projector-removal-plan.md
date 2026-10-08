---
id: MM-074
type: plan
project: magiq-media
workstream: WS-09-signingsession-projector-removal
repo: magiq-media
tags: [magiq-media, document-signing, saga, projection]
consumes: []
blocked-by-external: [MM-031]
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — pure magiq-media; origin is docs/dependency-gaps/saga-orchestration/INDEX.md#WS-09.
---

# WS-09 — `SigningSessionSummaryProjector` removal (phase timers as Wait states)

**Target repo:** `magiq-media`
**Depends on:** MM-031 (WS-04 — document-signing state machine with Wait states)
**User policy gate:** no magiq-media change until all external deps ship.

Signing phase timers move from projector-driven ticks to Step Functions Wait states inside `magiq-media-document-signing`.

## Session invocation

> Picking up WS-09 (plan MM-074). Depends on MM-031. Remove `SigningSessionSummaryProjector` phase-timer logic. Phase advancement driven by Step Functions Wait state. Confirm no projector read is broken.

## Phase 0 — Scope confirmation
- [ ] Confirm MM-031 shipped (document-signing state machine with Wait states)
- [ ] Current `SigningSessionSummaryProjector` phase-timer behaviour

## Phase 1 — Remove phase-timer logic
- [ ] Delete timer-tick code from projector
- [ ] Preserve summary projection for read-model (if any)

## Phase 2 — Step Functions Wait wiring
- [ ] Document-signing state machine Wait states correctly dispatch phase-advance commands

## Phase 3 — Tests
- [ ] Unit: projector no longer schedules timers
- [ ] Integration: phase advances through Step Functions execution

## Phase 4 — Ship
- [ ] PR to `develop`

## Phase 5 — Close
- [ ] saga-orchestration/INDEX.md: WS-09 → § Shipped
- [ ] Remove `SigningSessionSummaryProjector not implemented` bullet from `CLAUDE.md`

## Session log
- 2026-10-08: plan drafted (blocked on MM-031 + user policy)
