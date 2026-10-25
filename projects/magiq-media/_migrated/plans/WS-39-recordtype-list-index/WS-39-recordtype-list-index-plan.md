---
id: MM-051
type: plan
project: magiq-media
workstream: WS-39-recordtype-list-index
repo: magiq-media
tags: [magiq-media, metadata, dynamodb, index]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — pure magiq-media; origin is docs/dependency-gaps/stored-shapes/INDEX.md#WS-39.
---

# WS-39 — `RecordTypeListIndex` registration

**Target repo:** `magiq-media`
**User policy gate:** no magiq-media change until all external deps ship.

Spec defines an id-ordered index on `media-record-types`.

## Session invocation

> Picking up WS-39 (plan MM-051). Register `RecordTypeListIndex` on `media-record-types` DynamoDB table. Spec: id-ordered. Check if CDK provisioning needed (coordinate with cdk-magiq-media if so).

## Phase 0 — Scope confirmation
- [ ] Read `docs/spec/metadata/recordtype.*` on list index shape
- [ ] Confirm shape (likely LSI or GSI; verify)
- [ ] Check if infra already provisioned or needs CDK change

## Phase 1 — Index registration
- [ ] Register index in projection write path
- [ ] Populate index keys on `media-record-types` writes

## Phase 2 — Query path
- [ ] `GET /v1/record-types` (list) uses the id-ordered index

## Phase 3 — Tests
- [ ] Unit: writes populate index keys
- [ ] Integration: list endpoint returns id-ordered

## Phase 4 — Ship
- [ ] PR to `develop`

## Phase 5 — Close
- [ ] stored-shapes/INDEX.md: WS-39 → § Shipped
- [ ] Remove `RecordTypeListIndex` bullet from `CLAUDE.md`

## Session log
- 2026-10-08: plan drafted (blocked by user policy)
