---
id: MM-076
type: plan
project: magiq-media
workstream: WS-07-documentsigning-activity-lambdas
repo: magiq-media
tags: [magiq-media, document-signing, saga, step-functions]
consumes: []
blocked-by-external: [MM-031, MM-010]
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — pure magiq-media; origin is docs/dependency-gaps/saga-orchestration/INDEX.md#WS-07.
---

# WS-07 — `SagaOrchestrator.DocumentSigning` as activity Lambdas

**Target repo:** `magiq-media`
**Depends on:** MM-031 (WS-04 state machines), MM-010 (WS-05 SDK task-client)
**User policy gate:** no magiq-media change until all external deps ship.

Today `SagaOrchestrator.DocumentSigning` holds `SecuredSigningWebhookHandler` + `SigningSessionInitiatedHandler` as ordinary Lambda handlers. Spec: under Step Functions pivot they become activity Lambdas; webhook invokes `SendTaskSuccess` with signed outcome.

## Session invocation

> Picking up WS-07 (plan MM-076). Depends on MM-031 + MM-010. Refactor `SecuredSigningWebhookHandler` + `SigningSessionInitiatedHandler` as Step Functions activity Lambdas using `IStepFunctionsTaskClient`. Document-signing state machine (MM-031) waits on task-tokens issued at each phase.

## Phase 0 — Scope confirmation
- [ ] Confirm MM-031 + MM-010 shipped
- [ ] Current handlers in `SagaOrchestrator.DocumentSigning`

## Phase 1 — Webhook handler as activity
- [ ] `SecuredSigningWebhookHandler` loads task-token from signing-session state
- [ ] Calls `SendTaskSuccess` with signed-outcome payload
- [ ] On signing failure: `SendTaskFailure`

## Phase 2 — Initiated handler as activity
- [ ] `SigningSessionInitiatedHandler` runs as activity target
- [ ] Returns via `SendTaskSuccess` once Secured-Signing session created

## Phase 3 — Task-token correlation
- [ ] Store task-token per signing session (or on envelope-lookup table)
- [ ] Clean up on completion

## Phase 4 — Tests
- [ ] Unit: webhook handler calls SendTaskSuccess with correct payload
- [ ] Unit: initiated handler returns via SendTaskSuccess
- [ ] Integration: full signing flow through state machine

## Phase 5 — Ship
- [ ] PR to `develop`

## Phase 6 — Close
- [ ] saga-orchestration/INDEX.md: WS-07 → § Shipped
- [ ] Remove `SagaOrchestrator.DocumentSigning not deployed` bullet from `CLAUDE.md`

## Session log
- 2026-10-08: plan drafted (blocked on MM-031 + MM-010 + user policy)
