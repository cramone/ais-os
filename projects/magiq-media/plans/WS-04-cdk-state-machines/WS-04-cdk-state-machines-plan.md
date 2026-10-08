---
id: MM-031
type: plan
project: magiq-media
workstream: WS-04-cdk-state-machines
repo: cdk-magiq-media
tags: [cdk-magiq-media, infra, step-functions, saga, eventbridge]
consumes: []
blocked-by-external: [MM-010]
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — origin is docs/dependency-gaps/saga-orchestration/INDEX.md#WS-04 (no gap file; row-tracked); no separate review document.
---

# WS-04 — CDK state machines + EventBridge rules + IAM + CloudWatch alarms

**Target repo:** `cdk-magiq-media` — `D:\source\github\sprbrk-standard\mgq-magiq-media-infra`
**Depends on:** MM-010 (WS-05 — SDK task-client)
**Unblocks:** MM-073 (WS-11), MM-074 (WS-09), MM-075 (WS-08), MM-076 (WS-07)

Four state machines per ADR `docs/adrs/saga-orchestration-engine.md`.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media-infra`. Confirm MM-010 (WS-05) shipped. Paste:

> Picking up WS-04 (plan MM-031). Plan at `Z:\claudia\magiq\projects\magiq-media\plans\WS-04-cdk-state-machines\WS-04-cdk-state-machines-plan.md`. ADR: `D:\source\github\sprbrk-standard\mgq-magiq-media\docs\adrs\saga-orchestration-engine.md`.
>
> Depends on WS-05 (MM-010) shipped. Provision four Standard workflows: `magiq-media-asset-ingestion`, `magiq-media-document-signing`, `magiq-media-collection-archive-cascade`, `magiq-media-folder-archive-cascade`. Each with activity-Lambda targets (host-side refactors in later `-b` plans), EventBridge rule for infection branch, IAM roles with least-privilege, CloudWatch alarms (`ExecutionsFailed`, `ExecutionsAborted`, `ExecutionsTimedOut`), dashboard `media-sagas`.
>
> Deploy to dev; verify state machines + rules + roles exist; smoke-test wiring.

## Phase 0 — Scope confirmation
- [ ] Read ADR § State machine definitions for each of the four
- [ ] Confirm MM-010 (WS-05) shipped
- [ ] Enumerate current activity Lambda constructs

## Phase 1 — `magiq-media-asset-ingestion`
- [ ] Standard workflow CDK construct per ADR
- [ ] States: Receive upload → Confirm → Validate → `WaitForValidation` (Task-Token) → Confirm/Fail → Register asset reference
- [ ] Activity Lambda targets (host-side later)
- [ ] Execution-name convention per MM-010 helper

## Phase 2 — `magiq-media-document-signing`
- [ ] Standard workflow with phase timers as Wait states (replaces `SigningSessionSummaryProjector` phase timers — WS-09)
- [ ] Activity targets for webhook handler + initiated handler

## Phase 3 — `magiq-media-collection-archive-cascade`
- [ ] Distributed Map iterating folder subtree
- [ ] Per-item activity: archive folder / archive media item
- [ ] Error handling per spec

## Phase 4 — `magiq-media-folder-archive-cascade`
- [ ] Distributed Map (no size cap)
- [ ] Activity: archive folder node
- [ ] Un-archive counterpart (inverse activity)

## Phase 5 — EventBridge rules
- [ ] `AssetInfectionDetectedIntegrationEvent` → `SendTaskFailure` on `magiq-media-asset-ingestion` `WaitForValidation` task-token (activity Lambda in WS-08)
- [ ] Any other spec-defined cross-saga routes

## Phase 6 — IAM
- [ ] State machine execution roles: minimal `lambda:InvokeFunction` on activity ARNs
- [ ] Lambda execution roles: `states:SendTaskSuccess/Failure/Heartbeat` on each state-machine ARN
- [ ] EventBridge rule target role

## Phase 7 — CloudWatch
- [ ] Per SM alarms: `ExecutionsFailed`, `ExecutionsAborted`, `ExecutionsTimedOut`
- [ ] Dashboard: `media-sagas` with row per SM

## Phase 8 — Deploy
- [ ] Deploy to `dev`
- [ ] Verify state machines + rules + roles
- [ ] Smoke test: start execution manually

## Phase 9 — Close
- [ ] saga-orchestration/INDEX.md: WS-04 → § Shipped
- [ ] INTEGRATION-BACKLOG: MM-073, MM-074, MM-075, MM-076 — `Dep status: shipped (MM-010 + MM-031); Integration status: ready`

## Session log
- 2026-10-08: plan drafted (blocked on MM-010 ship)
