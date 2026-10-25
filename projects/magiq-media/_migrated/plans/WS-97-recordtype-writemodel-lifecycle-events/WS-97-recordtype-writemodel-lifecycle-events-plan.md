---
id: MM-137
type: plan
project: magiq-media
workstream: WS-97-recordtype-writemodel-lifecycle-events
repo: magiq-media
tags: [magiq-media, metadata, recordtype, write-model, clone, deprecate, reinstate, supersession, abandon, snapshot]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-16
depends-on: 'MM-133 (error codes constants), WS-53 (capabilities removal), WS-57 (snapshot revision)'
breaking-change: Internal
source: alignment-sweep-2026-10-15 cell RecordType × write-model
---

# WS-97 — RecordType write-model: 4 lifecycle events + 5 commands + status ordinals

**Target repo:** `magiq-media`
**Depends on:** MM-133 (error codes constants), WS-53 (capabilities removal), WS-57 (snapshot revision)

## Problem

Spec names 18 RecordType domain events. Code emits 15 (minus 1 removed by WS-53 → 14 clean after WS-53).

Missing (4):

| event | emitted by | integration-event consumer |
|---|---|---|
| `RecordTypeVersionDeprecated` | `DeprecateRecordTypeVersionCommand` | `media.recordtype.version-deprecated` (MM-134) |
| `RecordTypeReinstated` | `ReinstateRecordTypeCommand` | `media.recordtype.reinstated` (MM-134) |
| `RecordTypeSupersessionRecorded` | `RecordRecordTypeSupersessionCommand` | `media.recordtype.supersession-recorded` (MM-134) |
| `RecordTypeAbandoned` | `AbandonRecordTypeCommand` | — (internal only; `MM-133 RecordTypeAlreadyPublished 422` refuses abandon post-publish) |

Missing commands (5):

| command | route (MM-135) | aggregate method |
|---|---|---|
| `CloneRecordTypeCommand` | `POST /clone` | `RecordType.Clone(sourceId, newId, actor)` factory; emits `RecordTypeCreated` + replays fields from source |
| `DeprecateRecordTypeVersionCommand` | `POST /versions/{version}/deprecate` | `RecordType.DeprecateVersion(version)`; emits `RecordTypeVersionDeprecated` |
| `ReinstateRecordTypeCommand` | `POST /reinstate` | `RecordType.Reinstate()`; refuses `RecordTypeNotDeprecated 422`; emits `RecordTypeReinstated` |
| `RecordRecordTypeSupersessionCommand` | `POST /supersession` | `RecordType.RecordSupersession(supersededBy)`; emits `RecordTypeSupersessionRecorded` |
| `AbandonRecordTypeCommand` | `POST /abandon` | `RecordType.Abandon()`; refuses `RecordTypeAlreadyPublished 422`; emits `RecordTypeAbandoned` |

Non-event work:

| concern | action |
|---|---|
| `RecordTypeStatus` ordinals | pin explicitly: `Draft=1`, `Published=2`, `Deprecated=3`, `Abandoned=4` (add Abandoned); match stored shape rules in CLAUDE.md |
| Capabilities removal | WS-53 drops `RecordTypeDraft.Capabilities`, add/remove methods, `AddCapabilityToRecordTypeCommand`, `RemoveCapabilityFromRecordTypeCommand`; stored events keep member and load ignores it |
| Field replace / deprecate path renames | MM-135 route-only; commands + aggregate methods unchanged |
| `RecordTypeSnapshot` revision bump | per WS-57 — new status ordinals + `SupersededBy` state slot needs `[Snapshot(Revision = 2)]`; mismatch discarded + rebuilt |
| `RecordTypeDeprecated@2` upcaster | if existing stream shape adds `DeprecatedAt`/`Reason` members, upcaster per WS-28 |

## What the spec requires

- `DeprecateRecordTypeVersionCommand` — targets specific published version, refuses `RecordTypeVersionNotPublished 422` + `RecordTypeVersionAlreadyDeprecated 422` + `RecordTypeVersionNotFound 404` (MM-133 codes), emits `RecordTypeVersionDeprecated { RecordTypeId, Version, DeprecatedAt, Reason? }`.
- `ReinstateRecordTypeCommand` — targets whole aggregate, refuses `RecordTypeNotDeprecated 422` (only deprecated → reinstated), emits `RecordTypeReinstated { RecordTypeId, ReinstatedAt, Reason? }`.
- `RecordRecordTypeSupersessionCommand` — captures that this RecordType was superseded by another; emits `RecordTypeSupersessionRecorded { RecordTypeId, SupersededByRecordTypeId, RecordedAt }`; sets `SupersededBy` state slot (read by `GET /versions/latest` MM-135).
- `AbandonRecordTypeCommand` — draft-only; refuses `RecordTypeAlreadyPublished 422` (abandon post-publish is `DeprecateRecordType` scope); emits `RecordTypeAbandoned { RecordTypeId, AbandonedAt }`.
- `CloneRecordTypeCommand` — mints new aggregate from source; new `RecordTypeId` caller-supplied (idempotency token); emits `RecordTypeCreated` with source's field definitions replayed; refuses `RecordTypeIdAlreadyExists 409` on duplicate id.
- `RecordType.Status` enum: `Draft=1`, `Published=2`, `Deprecated=3`, `Abandoned=4` — pinned ordinals per CLAUDE.md stored-shape rule.
- `RecordType.SupersededBy` state (nullable `RecordTypeId`) — set by `RecordTypeSupersessionRecorded`, read by `GET /versions/latest` + history projector (MM-136).

## Scope boundary

- Aggregate + commands + handlers + events + snapshot.
- Error codes → MM-133.
- Integration event mappers + contract records → MM-134.
- HTTP endpoints → MM-135.
- History read-model + GSI → MM-136.
- Capabilities removal → WS-53.
- Upcasters → WS-28.
- No wire — covered by MM-134 (SNS) + MM-135 (HTTP).

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-97 (plan MM-137). WS-53 (capabilities removal) must ship first. MM-133/134/135/136 land alongside this plan — WS-97 is the write-model core that unblocks all four.

## Phase 0 — Scope confirmation

- [ ] WS-53 shipped (capabilities removal)
- [ ] MM-133 constants class reachable (for `RecordTypeNotDeprecated`, `RecordTypeAlreadyPublished`, `RecordTypeIdAlreadyExists`, `RecordTypeVersionNotPublished`, `RecordTypeVersionAlreadyDeprecated`, `RecordTypeVersionNotFound`)
- [ ] WS-57 snapshot revision mechanism available

## Phase 1 — Domain events

- [ ] `RecordTypeVersionDeprecated { RecordTypeId, Version, DeprecatedAt, Reason? }` + `[DomainEvent]` ordinals pinned
- [ ] `RecordTypeReinstated { RecordTypeId, ReinstatedAt, Reason? }`
- [ ] `RecordTypeSupersessionRecorded { RecordTypeId, SupersededByRecordTypeId, RecordedAt }`
- [ ] `RecordTypeAbandoned { RecordTypeId, AbandonedAt }`

## Phase 2 — Aggregate methods + state

- [ ] `RecordType.Status` enum carries `Abandoned=4` with explicit ordinals on all four
- [ ] `RecordType.SupersededBy: RecordTypeId?` state slot + `Apply(RecordTypeSupersessionRecorded)`
- [ ] `RecordType.DeprecateVersion(version)` guards: version exists + published + not already deprecated
- [ ] `RecordType.Reinstate()` guards: status == Deprecated
- [ ] `RecordType.RecordSupersession(supersededBy)` guards: not self-supersession, supersededBy not already superseded by this
- [ ] `RecordType.Abandon()` guards: status == Draft (never published)
- [ ] `RecordType.Clone(sourceId, newId, actor)` factory: minted new aggregate, source fields replayed, status = Draft

## Phase 3 — Commands + handlers

- [ ] `DeprecateRecordTypeVersionCommand` + handler
- [ ] `ReinstateRecordTypeCommand` + handler
- [ ] `RecordRecordTypeSupersessionCommand` + handler
- [ ] `AbandonRecordTypeCommand` + handler (releases name reservation after save)
- [ ] `CloneRecordTypeCommand` + handler (reads source via `RecordTypeRepository.GetByIdAsync` + reserves name under new id)

## Phase 4 — Snapshot revision

- [ ] `RecordTypeSnapshot` carries `Status` + `SupersededBy` + revised `[Snapshot(Revision = 2)]`
- [ ] Stored revision-1 snapshots discarded + rebuilt (WS-57 mechanism)

## Phase 5 — Tests

- [ ] Unit: each new aggregate method — happy path + guard precedence
- [ ] Unit: `Clone` seeds source fields
- [ ] Unit: `Abandon` refuses post-publish (`RecordTypeAlreadyPublished`)
- [ ] Unit: `Reinstate` refuses non-deprecated (`RecordTypeNotDeprecated`)
- [ ] Integration: command → event → repository → projector (via MM-136 history projector consumes new events)

## Phase 6 — Communicate change

- [ ] CLAUDE.md § KDPW: bullet removed
- [ ] No `breaking-changes.md` entry — wire visibility captured by MM-134 + MM-135

## Phase 7 — Ship

- [ ] PR to `develop`

## Phase 8 — Close

- [ ] INTEGRATION-BACKLOG.md: MM-137 → § Shipped
- [ ] spec-divergence/INDEX.md: WS-97 close row

## Session log

- 2026-10-16: plan drafted (alignment-sweep-2026-10-15 cell RecordType × write-model; status candidate; depends on MM-133/134/135/136 + WS-53 + WS-57)
