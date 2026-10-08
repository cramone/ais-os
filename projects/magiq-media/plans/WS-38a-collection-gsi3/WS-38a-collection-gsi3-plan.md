---
id: MM-009
type: plan
project: magiq-media
workstream: WS-38a-collection-gsi3
repo: cdk-magiq-media
tags: [cdk-magiq-media, infra, dynamodb, gsi]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — origin is docs/dependency-gaps/stored-shapes/INDEX.md#WS-38 (no gap file; row-tracked); no separate review document.
---

# WS-38a — `CollectionByDefaultProfileIndex` GSI3 on `media-collections` (infra half)

**Target repo:** `cdk-magiq-media` — `D:\source\github\sprbrk-standard\mgq-magiq-media-infra`
**Depends on:** none
**Unblocks:** MM-045 (WS-38b — populate GSI3PK + MediaProfileDeprecatedEventHandler read)

Spec: `GSI3PK = TENANT#{TenantId}#PROFILE#{MediaProfileId}#COLLECTIONS`. Enables `MediaProfileDeprecatedEventHandler` to look up affected collections by profile id.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media-infra`. Paste:

> Picking up WS-38a (plan MM-009). Plan at `Z:\claudia\magiq\projects\magiq-media\plans\WS-38a-collection-gsi3\WS-38a-collection-gsi3-plan.md`.
>
> Add GSI3 to `media-collections` CDK table construct. PK `GSI3PK` (String), SK `GSI3SK` (String). Verify projection type in `D:\source\github\sprbrk-standard\mgq-magiq-media\docs\spec\catalog\collection.*`. On-demand capacity.
>
> Per-env rollout: GSI creation on an existing table is a long-running op; dev first, confirm active, then promote. Deploy to dev; verify via AWS console.

## Phase 0 — Scope confirmation
- [ ] Confirm current `media-collections` CDK table construct
- [ ] Enumerate existing GSIs (confirm GSI3 slot available)

## Phase 1 — GSI3 provisioning
- [ ] Add `GSI3` to `media-collections` CDK construct
- [ ] Partition key: `GSI3PK` (String), Sort key: `GSI3SK` (String)
- [ ] Projection: verify in spec (`KEYS_ONLY` likely)
- [ ] On-demand capacity

## Phase 2 — Per-env rollout
- [ ] Config flag: `enableCollectionGsi3`
- [ ] Dev first, confirm active, then qa/staging/prod

## Phase 3 — Deploy
- [ ] Deploy to `dev`
- [ ] Verify GSI active (AWS console / CLI)
- [ ] Confirm no table throughput impact

## Phase 4 — Close
- [ ] stored-shapes/INDEX.md: WS-38 split — `WS-38a shipped`, `WS-38b open`
- [ ] INTEGRATION-BACKLOG: MM-045 (WS-38b) ready

## Session log
- 2026-10-08: plan drafted
