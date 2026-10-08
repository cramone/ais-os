---
id: MM-065
type: plan
project: magiq-media
workstream: WS-53-recordtype-capabilities-removal
repo: magiq-media
tags: [magiq-media, metadata, record-type, event-schema, migration]
consumes: []
blocked-by-external: [MM-041]
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — pure magiq-media; origin is docs/dependency-gaps/spec-divergence/INDEX.md#WS-53.
---

# WS-53 — `RecordType` capabilities removal

**Target repo:** `magiq-media`
**Depends on:** MM-041 (WS-28b — upcasters)
**User policy gate:** no magiq-media change until all external deps ship.

Spec: RecordType has no capabilities (capabilities live on `MediaProfile` only). Code still carries `RecordTypeDraft.Capabilities`, add/remove, `RecordTypePublished.Capabilities`, `RecordTypePublishedIntegrationEvent`, `RecordTypeVersionReference`. Stored events keep member; load ignores it (upcaster strips).

## Session invocation

> Picking up WS-53 (plan MM-065). Depends on MM-041. Remove capability members + add-remove methods from RecordType aggregate + draft. Preserve event schema compat via upcaster that strips the member on load. Audit downstream integration-event consumers.

## Phase 0 — Scope confirmation
- [ ] Confirm MM-041 shipped
- [ ] Grep `RecordTypeDraft.Capabilities`, `RecordTypePublished.Capabilities`, `RecordTypeVersionReference`
- [ ] Enumerate consumers of `RecordTypePublishedIntegrationEvent`

## Phase 1 — Aggregate cleanup
- [ ] Remove `Capabilities` from `RecordTypeDraft`
- [ ] Remove add/remove methods
- [ ] Remove `Capabilities` from `RecordTypePublished` + integration event
- [ ] Remove `RecordTypeVersionReference` (if dead)

## Phase 2 — Upcaster
- [ ] `RecordTypePublished@1 → @2`: strip `Capabilities`
- [ ] Any stored event carrying `Capabilities` loads cleanly

## Phase 3 — Downstream
- [ ] Audit consumers of integration event — ensure no reliance on `Capabilities`

## Phase 4 — Tests
- [ ] Unit: old event loads via upcaster
- [ ] Unit: new write omits member
- [ ] Integration: downstream consumer unchanged

## Phase 5 — Ship
- [ ] PR to `develop`

## Phase 6 — Close
- [ ] spec-divergence/INDEX.md: WS-53 → § Shipped
- [ ] Remove `RecordType still carries capabilities` bullet from `CLAUDE.md`

## Session log
- 2026-10-08: plan drafted (blocked on MM-041 + user policy)
