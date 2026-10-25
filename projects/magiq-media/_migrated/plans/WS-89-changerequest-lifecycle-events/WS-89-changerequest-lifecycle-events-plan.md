---
id: MM-129
type: plan
project: magiq-media
workstream: WS-89-changerequest-lifecycle-events
repo: magiq-media
tags: [magiq-media, change-requests, integration-events, lifecycle, resolved, abandoned, reopened]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-16
depends-on: 'ChangeRequest × write-model plan'
breaking-change: Process wire
source: alignment-sweep-2026-10-15 cell ChangeRequest × integration-events
---

# WS-89 — ChangeRequest missing integration events (3 lifecycle types)

**Target repo:** `magiq-media`
**Depends on:** ChangeRequest × write-model cell plan (provides `ChangeRequestResolved`, `ChangeRequestAbandoned`, `ChangeRequestReopened` domain events + backing commands/handlers)

## Problem

Spec names 4 ChangeRequest integration types. Code publishes 1. Missing 3 (all lifecycle):

| spec type | source domain event | status |
|---|---|---|
| `media.changerequest.created` | `ChangeRequestCreated` | published |
| `media.changerequest.resolved` | `ChangeRequestResolved` | **missing** |
| `media.changerequest.abandoned` | `ChangeRequestAbandoned` | **missing — spec: raised when item archived/withdrawn while review open** |
| `media.changerequest.reopened` | `ChangeRequestReopened` | **missing** |

Underlying domain events absent for all three. Backing commands/handlers (`ResolveChangeRequest`, `AbandonChangeRequest`, `ReopenChangeRequest`) presumed absent — write-model cell plan audits + builds.

## Consumer impact

Per catalog consumer list:
- `media.changerequest.resolved` → Notifications; Catalog (closes reference)
- `media.changerequest.abandoned` → Notifications; Catalog (closes reference). **Raised when owning MediaItem is archived or withdrawn while review open** — not caller-initiated.
- `media.changerequest.reopened` → Notifications; Catalog (reopens reference)

Without these events: ChangeRequest aggregate transitions but no SNS leaves module; Catalog's `ChangeRequestLifecycleEventHandler` (CLAUDE.md KDPW notes it's unbuilt) has nothing to consume; Notifications never fires on resolve/abandon/reopen.

## Scope boundary

- **Integration-event layer only.** Backing domain events + commands + aggregate methods = ChangeRequest × write-model cell plan.
- Does not build Catalog's `ChangeRequestLifecycleEventHandler` consumer — that's a Catalog write-model concern (KDPW § Intra-BC handlers not built — covered by WS-42 per CLAUDE.md).

## What the spec requires

- `ChangeRequestResolvedIntegrationEvent` + `ChangeRequestAbandonedIntegrationEvent` + `ChangeRequestReopenedIntegrationEvent` records under `ChangeRequests.Contracts/Events/` with `[MessageType]` matching spec kebab.
- `ChangeRequestDomainEventMapper` extends: `IDomainEventMapper<ChangeRequestResolved>`, `IDomainEventMapper<ChangeRequestAbandoned>`, `IDomainEventMapper<ChangeRequestReopened>` + mapper methods yielding corresponding integration events.
- `ChangeRequestAbandoned` emission driven by **MediaItem lifecycle events** (`media.item.archived`, `media.item.withdrawn`): ChangeRequests consumes those and dispatches `AbandonChangeRequestCommand` for every open CR on that MediaItem. The handler site that fires this cross-aggregate command lands in ChangeRequests' consuming side.

## Wire-visibility

Process wire — additive. 3 new types; CDK filter policies update.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-89 (plan MM-129). ChangeRequest × write-model cell plan must ship first (ChangeRequestResolved/Abandoned/Reopened domain events + commands). Add 3 integration events + 3 mapper overloads + cross-aggregate `AbandonChangeRequestCommand` dispatcher consuming media.item.archived/withdrawn.

## Phase 0 — Scope confirmation

- [ ] ChangeRequest × write-model plan shipped (3 domain events + backing commands)
- [ ] Confirm `ChangeRequestDomainEventMapper` currently handles 1 overload (sanity)
- [ ] WS-42 state (ChangeRequestLifecycleEventHandler on Catalog side)

## Phase 1 — Integration event records

- [ ] `ChangeRequestResolvedIntegrationEvent` with `[MessageType("media.changerequest.resolved")]`
- [ ] `ChangeRequestAbandonedIntegrationEvent` with `[MessageType("media.changerequest.abandoned")]`
- [ ] `ChangeRequestReopenedIntegrationEvent` with `[MessageType("media.changerequest.reopened")]`

## Phase 2 — Mapper overloads

- [ ] `ChangeRequestDomainEventMapper` adds `IDomainEventMapper<ChangeRequestResolved>` + mapper
- [ ] Adds `IDomainEventMapper<ChangeRequestAbandoned>` + mapper
- [ ] Adds `IDomainEventMapper<ChangeRequestReopened>` + mapper

## Phase 3 — Abandon-on-item-lifecycle consuming handlers

- [ ] `MediaItemArchivedChangeRequestAbandonHandler` consuming `media.item.archived` — for every open CR on the archived MediaItem, dispatch `AbandonChangeRequestCommand`
- [ ] `MediaItemWithdrawnChangeRequestAbandonHandler` consuming `media.item.withdrawn` (MM-119) — same pattern
- [ ] Both read tenant from `executionContext.TenantId` (per F079), not `e.TenantId`
- [ ] Idempotent on duplicate SQS delivery

## Phase 4 — CDK coordination

- [ ] `cdk-magiq-media` subscriber filter policies for 3 new types
- [ ] Confirm ChangeRequests module subscribes to `media.item.archived` + `media.item.withdrawn` on `media-cross-module-events` SQS queue

## Phase 5 — Tests

- [ ] Unit per mapper overload: `[MessageType]` + payload per spec
- [ ] Integration: resolve a CR → `media.changerequest.resolved`
- [ ] Integration: archive owning MediaItem → `AbandonChangeRequestCommand` dispatched → `media.changerequest.abandoned` for each open CR
- [ ] Integration: reopen a CR → `media.changerequest.reopened`

## Phase 6 — Communicate change

- [ ] Breaking-changes.md entry — process wire additive
- [ ] Coordinate with Notifications + Catalog BC owners

## Phase 7 — Ship

- [ ] PR to `develop`

## Phase 8 — Close

- [ ] CLAUDE.md § KDPW: bullet removed
- [ ] INTEGRATION-BACKLOG.md: MM-129 → § Shipped
- [ ] spec-divergence/INDEX.md: WS-89 close row

## Session log

- 2026-10-16: plan drafted (alignment-sweep-2026-10-15 cell ChangeRequest × integration-events; status candidate; publication half of lifecycle flow whose write-model builds under next cell)
