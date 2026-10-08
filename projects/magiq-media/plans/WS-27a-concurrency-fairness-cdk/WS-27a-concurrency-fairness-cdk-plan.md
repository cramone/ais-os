---
id: MM-026
type: plan
project: magiq-media
workstream: WS-27a-concurrency-fairness-cdk
repo: cdk-magiq-media
tags: [cdk-magiq-media, infra, lambda, sqs, concurrency]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — origin is docs/dependency-gaps/platform-capabilities/INDEX.md#WS-27 (no gap file; row-tracked); no separate review document.
---

# WS-27a — Reserved concurrency + fan-out fairness (infra half)

**Target repo:** `cdk-magiq-media` — `D:\source\github\sprbrk-standard\mgq-magiq-media-infra`
**Depends on:** none
**Unblocks:** MM-046 (WS-27b — magiq-media fan-out worker subscribes to `media-cascade-triggers`)

Delivers `docs/spec/shared/operations.md` § Concurrency and Fairness infra pieces.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media-infra`. Paste:

> Picking up WS-27a (plan MM-026). Plan at `Z:\claudia\magiq\projects\magiq-media\plans\WS-27a-concurrency-fairness-cdk\WS-27a-concurrency-fairness-cdk-plan.md`. Spec: `D:\source\github\sprbrk-standard\mgq-magiq-media\docs\spec\shared\operations.md` § Concurrency and Fairness.
>
> Set reserved concurrency on `Api` + `QueryApi` Lambdas (per-env). `ScalingConfig.MaximumConcurrency` on async event-source mappings (`Projectors.ReadModel`, `Projectors.Search`, `EventConsumers`, `ProcessingWorker`). Provision `media-cascade-triggers` SQS queue with SNS subscription to `media-integration-events` (filter policy `FilterPolicyScope: MessageBody` matching four cascade `type` values from spec).

## Phase 0 — Scope confirmation
- [ ] Read `docs/spec/shared/operations.md` § Concurrency and Fairness
- [ ] Enumerate current Lambda constructs
- [ ] Confirm no reserved concurrency / scaling-config set today

## Phase 1 — Reserved concurrency on APIs
- [ ] `Api` Lambda: `reservedConcurrentExecutions`
- [ ] `QueryApi` Lambda: `reservedConcurrentExecutions`
- [ ] Per-env override via config file

## Phase 2 — Scaling config on async event-source mappings
- [ ] `Projectors.ReadModel`, `Projectors.Search`, `EventConsumers`, `ProcessingWorker` SQS triggers → `ScalingConfig.MaximumConcurrency`
- [ ] Per-env values parameterized

## Phase 3 — `media-cascade-triggers` queue
- [ ] New SQS queue `media-cascade-triggers`
- [ ] SNS subscription to `media-integration-events` with filter policy on four cascade-driving `type` values
- [ ] `FilterPolicyScope: MessageBody`
- [ ] DLQ provisioned

## Phase 4 — IAM
- [ ] Fan-out worker consumer role: `sqs:ReceiveMessage` + delete on `media-cascade-triggers`
- [ ] Dropper of self-re-send happens on magiq-media side (WS-27b)

## Phase 5 — CloudWatch alarms
- [ ] Alarm on DLQ depth > 0
- [ ] Alarm on approximate age > threshold

## Phase 6 — Deploy
- [ ] Deploy to `dev`
- [ ] Verify queue + alarms exist; smoke test SNS filter

## Phase 7 — Close
- [ ] platform-capabilities/INDEX.md: WS-27 split — `WS-27a shipped`, `WS-27b open`
- [ ] INTEGRATION-BACKLOG: MM-046 (WS-27b) ready

## Session log
- 2026-10-08: plan drafted
