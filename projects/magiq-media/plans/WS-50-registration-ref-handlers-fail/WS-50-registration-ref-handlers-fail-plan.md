---
id: MM-056
type: plan
project: magiq-media
workstream: WS-50-registration-ref-handlers-fail
repo: magiq-media
tags: [magiq-media, registration, handlers, error-handling]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — pure magiq-media; origin is docs/dependency-gaps/spec-divergence/INDEX.md#WS-50.
---

# WS-50 — Registration-reference handlers return `Failed()` on persistent failure

**Target repo:** `magiq-media`
**User policy gate:** no magiq-media change until all external deps ship.

Current: handlers log + ack on persistent failure. Spec: return `Failed()` so SQS retries + eventual DLQ. `MediaItem.RegistrationRefs` can fall behind Registration otherwise.

## Session invocation

> Picking up WS-50 (plan MM-056). Grep registration-reference handlers (`RegistrationDispatched`, `RegistrationCancelled`, etc.). Replace log-and-ack with `Failed()` on persistent errors; preserve ack-and-log for terminal domain errors.

## Phase 0 — Scope confirmation
- [ ] Enumerate registration-reference handlers on `MediaItem.RegistrationRefs`
- [ ] Identify log-and-ack sites

## Phase 1 — Replace log-and-ack
- [ ] Transient failure (persistence, event-store, downstream) → `Failed()` (SQS redelivery + DLQ)
- [ ] Terminal domain failure → ack + log (unchanged — nothing more to try)

## Phase 2 — Tests
- [ ] Unit: transient failure → `Failed()`
- [ ] Unit: terminal domain failure → ack + log
- [ ] Integration: DLQ growth signals reconciliation failure

## Phase 3 — Ship
- [ ] PR to `develop`

## Phase 4 — Close
- [ ] spec-divergence/INDEX.md: WS-50 → § Shipped
- [ ] Remove `Registration-reference handlers log and ack persistent failure` bullet from `CLAUDE.md`

## Session log
- 2026-10-08: plan drafted (blocked by user policy)
