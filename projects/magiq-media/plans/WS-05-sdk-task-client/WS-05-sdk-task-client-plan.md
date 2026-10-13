---
id: MM-010
type: plan
project: magiq-media
workstream: WS-05-sdk-task-client
repo: aspnetcore-platform
tags: [aspnetcore-platform, sdk, step-functions, saga]
consumes: []
blocked-by-external: []
status: shipped
branches: [feature/chase/MM-010-WS-05-sdk-task-client]
pr: https://github.com/magiqsoftware/aspnetcore-platform/pull/36
merge-sha: b89ef0e1
shipped: 2026-10-12
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
- 2026-10-08: plan drafted.
- 2026-10-12: shipped on branch `feature/chase/MM-010-WS-05-sdk-task-client`.
  - Phase 0 found ADR spelled execution name as `{tenantId}#{correlationId}` but Step Functions `StartExecution` refuses `#` (reserved along with other shell metacharacters). Separator swapped `#` → `_` across the four example rows + the summary sentence + added a short rationale paragraph in § Execution Name Carries the Tenant. ADR edit sits on branch `spec/initial-alignment` in `sprbrk-standard/mgq-magiq-media`; lands with Chase's existing spec-alignment stream.
  - New projects `Magiq.Platform.Messaging.StepFunctions{.Abstractions,}` built on `AWSSDK.StepFunctions 4.0.0.26` (compatible with `AWSSDK.Core 4.0.3.12`). Abstractions carry `IStepFunctionsTaskClient` + `StepFunctionsExecutionName`; the AWS project carries `StepFunctionsTaskClient` + `AddStepFunctionsTaskClient()`.
  - `StepFunctionsExecutionName.For(string tenantId, params string[] correlationParts)` composes `{tenantId}_{part0}_{part1}...`, validates per-segment against `^[0-9A-Za-z-._]+$` and bounds the composite to 80 chars (the AWS limit). The signature uses `correlationParts` rather than the plan's `(tenantId, sagaType, sagaId)` — the ADR puts saga type on the state machine, not the execution name, and all four saga types already compose multiple correlation segments (AssetIngestion is `{AssetId}_{AttemptNumber}`).
  - `MessageMetadata.TaskToken` added as init-only nullable property, not a positional constructor parameter — non-breaking. Round-trips through System.Text.Json automatically; absent token deserializes to null.
  - 22 new unit tests green locally; full solution build clean (0 errors, 4 warnings — pre-existing).
- 2026-10-12: PR #36 merged to `aspnetcore-platform/main` as `b89ef0e1`. saga-orchestration/INDEX.md WS-05 moved to § Shipped; WS-04 (CDK) flipped `open` → `ready`. INTEGRATION-BACKLOG MM-010 to § Shipped; MM-031 (WS-04) flipped `new` → `ready`. Readiness summary bumped 64→63 `new`, 3→4 `ready`, 8→9 `shipped`. MM-075 (WS-08) + MM-076 (WS-07) remain blocked pending MM-031.
