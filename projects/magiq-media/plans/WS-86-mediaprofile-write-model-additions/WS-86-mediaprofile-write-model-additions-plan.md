---
id: MM-126
type: plan
project: magiq-media
workstream: WS-86-mediaprofile-write-model-additions
repo: magiq-media
tags: [magiq-media, catalog, mediaprofile, write-model, commands, domain-events, aggregate, draft-rename, change-request-policy, abandon, revision-break]
consumes: []
blocked-by-external: []
status: active
branches: []
created: 2026-10-16
depends-on: '-'
breaking-change: Internal
source: alignment-sweep-2026-10-15 cell MediaProfile × write-model
---

# WS-86 — MediaProfile write-model: 4 new events + 3 new commands

**Target repo:** `magiq-media`

## Problem

Catalog slice names 21 MediaProfile domain events; code has 17. Missing (4):

| event | needed by |
|---|---|
| `MediaProfileDraftRenamed` | MM-125 (`PUT /draft/name`) |
| `MediaProfileChangeRequestPolicySet` | MM-125 (`PUT /change-request-policy`) |
| `MediaProfileRevisionBreakDetected` | MM-124 publish-validation (`RevisionBreaksExistingItems 422` refusal marker, or published-anyway-with-override marker) |
| `MediaProfileAbandoned` | MM-125 (`POST /abandon`) |

Backing commands + aggregate methods (3 — RevisionBreak is emitted during publish, no new command):

| Command | Aggregate method | Primary event |
|---|---|---|
| `RenameMediaProfileDraftCommand` | `MediaProfile.RenameDraft(name, DateTimeOffset)` | `MediaProfileDraftRenamed` |
| `SetChangeRequestPolicyCommand` | `MediaProfile.SetChangeRequestPolicy(policy, DateTimeOffset)` | `MediaProfileChangeRequestPolicySet` |
| `AbandonMediaProfileCommand` | `MediaProfile.Abandon(DateTimeOffset)` | `MediaProfileAbandoned` |

`MediaProfileRevisionBreakDetected` is emitted inside the publish aggregate method when the draft breaks existing items — either as a validation marker refused back to the handler as `RevisionBreaksExistingItems` or as a published-anyway signal when override is specified. Behaviour aligns with spec `mediaprofile.write-model.md § Publish`.

## Classification — internal

Wire-visible facets captured by MM-125 (routes) + MM-124 (error codes). This plan is the backing write-model.

## What the spec requires

- 4 new `[DomainEvent]`-registered records under `Catalog.Domain/Aggregates/MediaProfiles/Events/`
- 3 new command records + handlers under `Catalog.WriteModel/Commands/MediaProfiles/`
- 3 new aggregate methods on `MediaProfile` + `When<>` subscriptions + `Apply` method bodies
- `MediaProfile.ChangeRequestPolicy` state carrying `NotRequired | OptionalForEdit | RequiredForEdit`
- `MediaProfile.Status` state transition to `Abandoned` on `MediaProfileAbandoned`
- `MediaProfileSnapshot` gains any new state (`ChangeRequestPolicy`, `Status` extension) + revision bump per WS-57
- `RenameDraft` refuses `MediaProfileNameConflict 409` on duplicate (via name reservation), `MediaProfileNotFound 404` on absent, `PlatformProfileImmutable 403` on Platform-origin (WS-47)
- `Abandon` refuses on non-draft state; releases name reservation on success
- `MediaProfileCreated` carries `[DomainEvent(Version = 1)]` (spec says v1 explicitly — WS-28 upcaster covers v1→v2 if needed)
- `MediaProfilePublished` carries `[DomainEvent(Version = 2)]` (per CLAUDE.md KDPW event-schema list)

## Scope boundary

- **Aggregate + commands + events only.** HTTP = MM-125. Error codes = MM-124.
- Does not build `MediaProfileSnapshotField` expansion — WS-46 covers.
- Does not build capability-field-group registry / scheme-selection — WS-54.
- Platform-origin refusal remains WS-47's responsibility; this plan dispatches to it when state check hits.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-86 (plan MM-126). Add 4 new MediaProfile domain events + 3 new commands + aggregate methods. Internal — route layer MM-125 + error codes MM-124 capture wire.

## Phase 0 — Scope confirmation

- [ ] Code audit: 17 of 21 events present (sanity)
- [ ] MM-124 shipped (`MediaProfileErrorCodes` reachable)
- [ ] Confirm `MediaProfilePublished` version bump (WS-28) plan state

## Phase 1 — Domain events

- [ ] `MediaProfileDraftRenamed` — `{ TenantId, MediaProfileId, PreviousName, Name, RenamedAt }`
- [ ] `MediaProfileChangeRequestPolicySet` — `{ TenantId, MediaProfileId, PreviousPolicy?, Policy, SetAt }`
- [ ] `MediaProfileRevisionBreakDetected` — `{ TenantId, MediaProfileId, Version, Reasons: IReadOnlyList<string>, DetectedAt }`
- [ ] `MediaProfileAbandoned` — `{ TenantId, MediaProfileId, AbandonedAt }`
- [ ] Each `[DomainEvent]`-registered

## Phase 2 — Aggregate methods on `MediaProfile`

- [ ] `RenameDraft(name, DateTimeOffset)` — refuses non-draft + name collision; emits `MediaProfileDraftRenamed`
- [ ] `SetChangeRequestPolicy(policy, DateTimeOffset)` — no-op if unchanged; emits `MediaProfileChangeRequestPolicySet`
- [ ] `Abandon(DateTimeOffset)` — refuses on non-draft state; emits `MediaProfileAbandoned` + releases name reservation
- [ ] Publish aggregate method: on revision-break detection, emits `MediaProfileRevisionBreakDetected` + refuses with `RevisionBreaksExistingItems 422` (MM-124) unless override specified
- [ ] `When<>` + `Apply` for each new event
- [ ] `MediaProfileSnapshot` carries `ChangeRequestPolicy` + revision bump per WS-57

## Phase 3 — Commands + handlers

- [ ] `RenameMediaProfileDraftCommand` + handler
- [ ] `SetChangeRequestPolicyCommand` + handler
- [ ] `AbandonMediaProfileCommand` + handler
- [ ] Each: guard precedence per `api-conventions.md § Refusal precedence`

## Phase 4 — Tests

- [ ] Unit per aggregate method: pre-state + command → expected event(s)
- [ ] Unit per handler: refuses per guard precedence
- [ ] Unit: abandon releases name reservation
- [ ] Integration: rename draft → name-reservation collision refuses `MediaProfileNameConflict 409` (MM-124)
- [ ] Integration: abandon → draft disappears + name released

## Phase 5 — Ship

- [ ] PR to `develop`

## Phase 6 — Close

- [ ] CLAUDE.md § KDPW: bullet removed
- [ ] INTEGRATION-BACKLOG.md: MM-126 → § Shipped
- [ ] spec-divergence/INDEX.md: WS-86 close row

## Session log

- 2026-10-16: plan drafted (alignment-sweep-2026-10-15 cell MediaProfile × write-model; status candidate; mirror of MM-111/MM-116/MM-122 pattern)
