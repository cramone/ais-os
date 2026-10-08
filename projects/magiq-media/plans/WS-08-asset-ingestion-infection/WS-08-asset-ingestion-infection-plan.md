---
id: MM-075
type: plan
project: magiq-media
workstream: WS-08-asset-ingestion-infection
repo: magiq-media
tags: [magiq-media, asset-ingestion, saga, step-functions, eventbridge]
consumes: []
blocked-by-external: [MM-031, MM-010]
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — pure magiq-media; origin is docs/dependency-gaps/saga-orchestration/INDEX.md#WS-08.
---

# WS-08 — `magiq-media-asset-ingestion` infection branch

**Target repo:** `magiq-media` + `cdk-magiq-media`
**Depends on:** MM-031 (WS-04 state machines), MM-010 (WS-05 SDK task-client)
**User policy gate:** no magiq-media change until all external deps ship.

Spec: `AssetInfectionDetectedIntegrationEvent` → EventBridge → activity Lambda calls `SendTaskFailure` on `WaitForValidation` task-token → `FailAsInfection` compensation. Neither EventBridge rule nor activity Lambda built.

## Session invocation

> Picking up WS-08 (plan MM-075). Depends on MM-031 + MM-010. Build infection-handler activity Lambda using `IStepFunctionsTaskClient`. CDK adds EventBridge rule targeting the Lambda on `AssetInfectionDetectedIntegrationEvent`. Lambda extracts task-token from execution context + calls `SendTaskFailure`.

## Phase 0 — Scope confirmation
- [ ] Confirm MM-031 + MM-010 shipped
- [ ] Spec: `AssetInfectionDetectedIntegrationEvent` payload + `FailAsInfection` compensation state

## Phase 1 — Activity Lambda
- [ ] New Lambda `AssetInfectionActivity` in `magiq-media`
- [ ] Reads task-token stored on asset-ingestion saga state (correlation by `AssetId`)
- [ ] Calls `IStepFunctionsTaskClient.SendTaskFailureAsync(taskToken, "InfectionDetected", cause)`

## Phase 2 — CDK EventBridge rule (coordinate with `cdk-magiq-media` branch)
- [ ] Rule on `AssetInfectionDetectedIntegrationEvent` SNS → EventBridge → Lambda target
- [ ] IAM: Lambda role has `states:SendTaskFailure` on asset-ingestion state machine ARN

## Phase 3 — Correlation storage
- [ ] Store `TaskToken` per `AssetId` in a lookup table or saga-state DynamoDB row
- [ ] Clean up on happy-path completion

## Phase 4 — Tests
- [ ] Unit: Lambda extracts token + calls SendTaskFailure
- [ ] Integration: infection event → execution fails via compensation state

## Phase 5 — Ship
- [ ] PR to `develop` + CDK PR

## Phase 6 — Close
- [ ] saga-orchestration/INDEX.md: WS-08 → § Shipped
- [ ] Remove `magiq-media-asset-ingestion infection branch not built` bullet from `CLAUDE.md`

## Session log
- 2026-10-08: plan drafted (blocked on MM-031 + MM-010 + user policy)
