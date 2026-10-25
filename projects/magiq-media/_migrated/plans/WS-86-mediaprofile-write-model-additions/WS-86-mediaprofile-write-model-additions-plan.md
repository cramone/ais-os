---
id: MM-126
type: plan
project: magiq-media
workstream: WS-86-mediaprofile-write-model-additions
repo: magiq-media
tags: [magiq-media, catalog, mediaprofile, write-model, commands, domain-events, aggregate, draft-rename, change-request-policy, abandon, revision-break]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-16
depends-on: '-'
breaking-change: Process wire additive (MediaProfileAbandoned integration event half folded in from MediaProfile × integration-events cell on 2026-10-18 re-diff)
source: alignment-sweep-2026-10-15 cell MediaProfile × write-model
---

# WS-86 — MediaProfile write-model: 4 new events + 3 new commands + 1 integration-event wire half (abandoned)

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

## Classification — mostly internal + 1 wire half (abandoned)

Wire-visible facets for 3 of 4 events captured by MM-125 (routes) + MM-124 (error codes); this plan is the backing write-model for those. **One wire half folded in:** `media.profile.abandoned` integration event (contract record + `MediaProfileDomainEventMapper` overload) — surfaced in 2026-10-18 Arnica review re-diff of MediaProfile × integration-events cell (originally marked `clean` because catalog lacked the abandoned row at draft time). Rather than open a separate 1-type integration-events plan, the mapping half rides with its backing domain event here.

Catalog slice for integration-events after Arnica patch:

| spec type | source domain event | status |
|---|---|---|
| `media.profile.published` | `MediaProfilePublished` | published |
| `media.profile.deprecated` | `MediaProfileDeprecated` | published |
| `media.profile.abandoned` | `MediaProfileAbandoned` | **missing — folded into this plan** |

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
- `MediaProfileAbandonedIntegrationEvent` record under `Catalog.Contracts/Events/MediaProfiles/` with `[MessageType("media.profile.abandoned")]` and payload `{ TenantId, MediaProfileId, AbandonedAt, EventVersion }`
- `MediaProfileDomainEventMapper` adds `IDomainEventMapper<MediaProfileAbandoned>` + `Map(MediaProfileAbandoned e)` yielding the integration event

## Scope boundary

- **Aggregate + commands + events + 1 integration-event wire half (abandoned).** HTTP = MM-125. Error codes = MM-124. Other integration-event types (published, deprecated) are already published; this plan adds the third (abandoned) via mapper overload + contract record.
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

## Phase 3b — Abandoned integration event + mapper

- [ ] `MediaProfileAbandonedIntegrationEvent` record under `Catalog.Contracts/Events/MediaProfiles/` with `[MessageType("media.profile.abandoned")]` + payload `{ TenantId, MediaProfileId, AbandonedAt, EventVersion }`
- [ ] `MediaProfileDomainEventMapper` adds `IDomainEventMapper<MediaProfileAbandoned>` + `Map(MediaProfileAbandoned e)` yielding the integration event
- [ ] **CDK coordination precondition:** every existing subscription on `media-integration-events` migrated to `FilterPolicyScope: MessageBody` (per `docs/breaking-changes.md § Cross-cutting ordering constraint`). Cross-cutting prerequisite; deploy must land + propagate before any body-only publication fires
- [ ] cdk-magiq-media filter-policy entry for Catalog subscriber on `media.profile.abandoned` (mediaprofile.write-model.md names Catalog as consumer — cache miss falls through to snapshot + stream load; marks profile abandoned on consumer indexes)

## Phase 4 — Tests

- [ ] Unit per aggregate method: pre-state + command → expected event(s)
- [ ] Unit per handler: refuses per guard precedence
- [ ] Unit: abandon releases name reservation
- [ ] Integration: rename draft → name-reservation collision refuses `MediaProfileNameConflict 409` (MM-124)
- [ ] Integration: abandon → draft disappears + name released
- [ ] Unit: `Map(MediaProfileAbandoned)` yields `MediaProfileAbandonedIntegrationEvent` with `[MessageType("media.profile.abandoned")]` + spec payload
- [ ] Integration: `AbandonMediaProfileCommand` → `media.profile.abandoned` on `media-integration-events`

## Phase 5 — Ship

- [ ] PR to `develop`

## Phase 6 — Close

- [ ] CLAUDE.md § KDPW: bullet removed
- [ ] INTEGRATION-BACKLOG.md: MM-126 → § Shipped
- [ ] spec-divergence/INDEX.md: WS-86 close row

## Session log

- 2026-10-16: plan drafted (alignment-sweep-2026-10-15 cell MediaProfile × write-model; status candidate; mirror of MM-111/MM-116/MM-122 pattern)
- 2026-10-18: re-diffed under Arnica review fix for finding #8 (catalog Phase 1 regression). Folded in `media.profile.abandoned` integration-event wire half from MediaProfile × integration-events cell (originally marked `clean` because catalog lacked the row at draft time). Scope now carries 1 new integration-event record + 1 new mapper overload + CDK filter-policy entry for Catalog consumer. Classification bumped from `Internal` to `Process wire additive` on `media.profile.abandoned`. 4 write-model events + 3 commands unchanged.
