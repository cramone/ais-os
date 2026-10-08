---
id: MM-052
type: plan
project: magiq-media
workstream: WS-41-processingjob-ordinals
repo: magiq-media
tags: [magiq-media, processing, enum, ordinals]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — pure magiq-media; origin is docs/dependency-gaps/stored-shapes/INDEX.md#WS-41.
---

# WS-41 — `ProcessingJobStatus` + `ProcessingJobFailureCategory` ordinals pinned

**Target repo:** `magiq-media`
**User policy gate:** no magiq-media change until all external deps ship.

Spec `processingjob.write-model.md` pins ordinals explicitly. Code must emit events under those ordinals from day one.

## Session invocation

> Picking up WS-41 (plan MM-052). Pin `ProcessingJobStatus` + `ProcessingJobFailureCategory` enum ordinals to spec values. Confirm `JsonStringEnumConverter` NOT applied where ordinal is stored. Add compile-time assertion against spec.

## Phase 0 — Scope confirmation
- [ ] Read `docs/spec/processing/processingjob.write-model.md` § enum ordinals
- [ ] Current ordinal mapping in code

## Phase 1 — Pin ordinals
- [ ] `ProcessingJobStatus` members in spec order
- [ ] `ProcessingJobFailureCategory` members in spec order
- [ ] Explicit `= N` on each

## Phase 2 — Enforcement
- [ ] Unit test asserts each ordinal value matches spec
- [ ] Golden-file test against serialized event fixture

## Phase 3 — Ship
- [ ] PR to `develop`

## Phase 4 — Close
- [ ] stored-shapes/INDEX.md: WS-41 → § Shipped
- [ ] Remove `ProcessingJobStatus and ProcessingJobFailureCategory ordinals` bullet from `CLAUDE.md`

## Session log
- 2026-10-08: plan drafted (blocked by user policy)
