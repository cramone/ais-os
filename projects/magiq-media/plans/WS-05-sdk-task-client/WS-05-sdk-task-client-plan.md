---
id: MM-010
type: plan
project: magiq-media
workstream: WS-05-sdk-task-client
repo: aspnetcore-platform
tags: [aspnetcore-platform, sdk, step-functions, saga]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — origin is docs/dependency-gaps/saga-orchestration/INDEX.md#WS-05; no separate review document.
---

# WS-05 — SDK task-client helpers for Step Functions

**Target repo:** `aspnetcore-platform` — `D:\source\github\magiqsoftware\aspnetcore-platform`
**Depends on:** none
**Unblocks:** MM-031 (WS-04 CDK state machines), MM-075 (WS-08 infection branch activity), MM-076 (WS-07 DocumentSigning activity Lambdas)

ADR `docs/adrs/saga-orchestration-engine.md` requires platform SDK helpers for Step Functions callbacks.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\magiqsoftware\aspnetcore-platform`. Paste:

> Picking up WS-05 (plan MM-010). Plan at `Z:\claudia\magiq\projects\magiq-media\plans\WS-05-sdk-task-client\WS-05-sdk-task-client-plan.md`. Reference ADR: `D:\source\github\sprbrk-standard\mgq-magiq-media\docs\adrs\saga-orchestration-engine.md`.
>
> Deliver `IStepFunctionsTaskClient` with `SendTaskSuccessAsync` + `SendTaskFailureAsync`. Add optional `TaskToken` on `MessageMetadata`, serialize across SNS→SQS. Add `StepFunctionsExecutionName.For(tenantId, sagaType, sagaId)` helper enforcing SFN naming rules.
>
> Read `aspnetcore-platform/CLAUDE.md`. PR to `aspnetcore-platform/main`.

## Phase 0 — Scope confirmation
- [ ] Read ADR § Platform SDK requirements
- [ ] Read `aspnetcore-platform/CLAUDE.md`; identify messaging layer namespaces
- [ ] Confirm no existing `IStepFunctionsTaskClient` type

## Phase 1 — `IStepFunctionsTaskClient` + implementation
- [ ] Define `IStepFunctionsTaskClient` with `SendTaskSuccessAsync(taskToken, outputJson, ct)` + `SendTaskFailureAsync(taskToken, error, cause, ct)`
- [ ] AWS SDK implementation using `IAmazonStepFunctions`
- [ ] Register in `AddMagiqPlatformMessaging`

## Phase 2 — Task-token carry on `MessageMetadata`
- [ ] Add optional `TaskToken` property on `MessageMetadata`
- [ ] Serialize/deserialize across SNS → SQS envelope round-trip
- [ ] Carry on `IExecutionContext` for handler-side access

## Phase 3 — Execution-name helper
- [ ] `StepFunctionsExecutionName.For(tenantId, sagaType, sagaId)` → multi-tenant naming per ADR
- [ ] Reject invalid characters per AWS SFN naming rules

## Phase 4 — Tests + ship
- [ ] Unit: round-trip serialization, invalid execution-name refusal
- [ ] Integration with LocalStack SFN (if infra available)
- [ ] Bump `Magiq.Platform.*` package; push internal NuGet
- [ ] PR to `aspnetcore-platform/main`

## Phase 5 — Close
- [ ] saga-orchestration/INDEX.md: WS-05 → § Shipped
- [ ] Unblocks MM-031 (WS-04), MM-075 (WS-08), MM-076 (WS-07)

## Session log
- 2026-10-08: plan drafted
