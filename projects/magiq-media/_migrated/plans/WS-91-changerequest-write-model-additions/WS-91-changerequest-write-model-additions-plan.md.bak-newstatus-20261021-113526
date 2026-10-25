---
id: MM-131
type: plan
project: magiq-media
workstream: WS-91-changerequest-write-model-additions
repo: magiq-media
tags: [magiq-media, change-requests, write-model, commands, domain-events, aggregate, lifecycle, participants, redact]
consumes: []
blocked-by-external: []
status: active
branches: []
created: 2026-10-16
depends-on: '-'
breaking-change: Internal
source: alignment-sweep-2026-10-15 cell ChangeRequest × write-model
---

# WS-91 — ChangeRequest write-model: 6 new events + 6 new commands

**Target repo:** `magiq-media`

## Problem

Catalog slice names 10 ChangeRequest domain events; code has 4. Missing (6):

| event | needed by |
|---|---|
| `ChangeRequestResolved` | MM-129 (`media.changerequest.resolved`) + MM-130 (`POST /resolve`) |
| `ChangeRequestAbandoned` | MM-129 (`media.changerequest.abandoned`) + MM-130 (`POST /abandon`); also raised by MediaItem-archived/withdrawn cross-aggregate consumers (MM-129) |
| `ChangeRequestReopened` | MM-129 (`media.changerequest.reopened`) + MM-130 (`POST /reopen`) |
| `ChangeRequestParticipantAdded` | MM-130 (`POST /participants`) |
| `ChangeRequestParticipantRemoved` | MM-130 (`DELETE /participants/{memberId}`) |
| `ReviewCommentRedacted` | MM-130 (`POST /comments/{id}/redact`) |

Backing commands (6):

| Command | Aggregate method | Primary event |
|---|---|---|
| `ResolveChangeRequestCommand` | `ChangeRequest.Resolve` | `ChangeRequestResolved` |
| `AbandonChangeRequestCommand` | `ChangeRequest.Abandon` | `ChangeRequestAbandoned` |
| `ReopenChangeRequestCommand` | `ChangeRequest.Reopen` | `ChangeRequestReopened` |
| `AddChangeRequestParticipantCommand` | `ChangeRequest.AddParticipant` | `ChangeRequestParticipantAdded` |
| `RemoveChangeRequestParticipantCommand` | `ChangeRequest.RemoveParticipant` | `ChangeRequestParticipantRemoved` |
| `RedactChangeRequestCommentCommand` | `ChangeRequest.RedactComment` | `ReviewCommentRedacted` |

Plus create command: code has `AddCommentEndpoint` etc. but `CreateChangeRequest` / `OpenChangeRequest` command existence should be confirmed at Phase 0 — if absent, MM-130's create route also needs this plan.

## Aggregate state additions

- `ChangeRequest.Status` — `Open | Resolved | Abandoned` state transitions.
- `ChangeRequest.Participants` — set of participant member ids (capped at `MaxParticipantsPerRequest = 100` per MM-128).
- `ChangeRequest.Comments` count tracked for cap enforcement (`MaxCommentsPerRequest = 1000` per MM-128).
- `ChangeRequestSnapshot` revision bump per WS-57.

## Classification — internal

Wire visibility captured by MM-128 (error codes), MM-129 (integration events), MM-130 (routes).

## Scope boundary

- **Aggregate + commands + events only.**
- HTTP = MM-130. Integration events = MM-129. Error codes = MM-128.
- Cross-aggregate `AbandonChangeRequestCommand` dispatcher (consuming MediaItem archived/withdrawn) = MM-129's handler side.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-91 (plan MM-131). Add 6 new ChangeRequest domain events + 6 new commands + aggregate methods + Status/Participants state + snapshot bump. Internal — route layer MM-130, integration events MM-129, error codes MM-128.

## Phase 0 — Scope confirmation

- [ ] Code audit: 4 of 10 events present (sanity)
- [ ] Confirm whether `CreateChangeRequestCommand` / `OpenChangeRequestCommand` exists — if absent, add under this plan
- [ ] MM-128 reachable (`ChangeRequestErrorCodes`)

## Phase 1 — Domain events

- [ ] `ChangeRequestResolved` — `{ TenantId, ChangeRequestId, ResolvedBy, Reason?, ResolvedAt }`
- [ ] `ChangeRequestAbandoned` — `{ TenantId, ChangeRequestId, Trigger: UserInitiated | MediaItemArchived | MediaItemWithdrawn, AbandonedAt }`
- [ ] `ChangeRequestReopened` — `{ TenantId, ChangeRequestId, ReopenedBy, ReopenedAt }`
- [ ] `ChangeRequestParticipantAdded` — `{ TenantId, ChangeRequestId, ParticipantId, AddedBy, AddedAt }`
- [ ] `ChangeRequestParticipantRemoved` — `{ TenantId, ChangeRequestId, ParticipantId, RemovedBy, RemovedAt }`
- [ ] `ReviewCommentRedacted` — `{ TenantId, ChangeRequestId, CommentId, RedactedBy, RedactedAt }`
- [ ] Each `[DomainEvent]`-registered

## Phase 2 — Aggregate methods on `ChangeRequest`

- [ ] `Resolve(resolvedBy, reason?, DateTimeOffset)` — refuses `ChangeRequestNotOpen` if not Open; emits `ChangeRequestResolved`; transitions Status to Resolved
- [ ] `Abandon(trigger, DateTimeOffset)` — refuses `ChangeRequestNotOpen` if not Open; emits `ChangeRequestAbandoned`
- [ ] `Reopen(reopenedBy, DateTimeOffset)` — refuses `ChangeRequestNotReopenable` if currently Open (reopen on open) or neither-resolved-nor-abandoned
- [ ] `AddParticipant(id, DateTimeOffset)` — refuses `ParticipantAlreadyAdded` if already present, `TooManyParticipants` if cap reached; emits `ChangeRequestParticipantAdded`
- [ ] `RemoveParticipant(id, DateTimeOffset)` — refuses `ParticipantNotFound` if absent; emits `ChangeRequestParticipantRemoved`
- [ ] `RedactComment(commentId, redactedBy, DateTimeOffset)` — refuses `CommentNotFound` if absent, `CommentDeleted` if already deleted, `CommentRedacted` if already redacted; emits `ReviewCommentRedacted`
- [ ] `When<>` + `Apply` for each new event
- [ ] `ChangeRequestSnapshot` carries `Status` + `Participants` set + comment count; revision bump

## Phase 3 — Commands + handlers

- [ ] `ResolveChangeRequestCommand` + handler
- [ ] `AbandonChangeRequestCommand` + handler (callable from HTTP MM-130 and from MM-129 cross-aggregate consumers)
- [ ] `ReopenChangeRequestCommand` + handler
- [ ] `AddChangeRequestParticipantCommand` + handler
- [ ] `RemoveChangeRequestParticipantCommand` + handler
- [ ] `RedactChangeRequestCommentCommand` + handler
- [ ] If create command absent: `CreateChangeRequestCommand` / `OpenChangeRequestCommand` + handler per CLAUDE.md § Key conventions (caller-supplied id)

## Phase 4 — Tests

- [ ] Unit per aggregate method: pre-state + command → expected event(s)
- [ ] Unit per handler: guard precedence refuses per MM-128 codes
- [ ] Unit: participant cap 100 enforced
- [ ] Unit: `Reopen` requires Resolved or Abandoned (not Open)
- [ ] Integration: full lifecycle Open → Resolved → Reopen → Resolved

## Phase 5 — Ship

- [ ] PR to `develop`

## Phase 6 — Close

- [ ] CLAUDE.md § KDPW: bullet removed
- [ ] INTEGRATION-BACKLOG.md: MM-131 → § Shipped
- [ ] spec-divergence/INDEX.md: WS-91 close row

## Session log

- 2026-10-16: plan drafted (alignment-sweep-2026-10-15 cell ChangeRequest × write-model; status candidate; mirror of MM-111/MM-116/MM-122/MM-126 pattern)
