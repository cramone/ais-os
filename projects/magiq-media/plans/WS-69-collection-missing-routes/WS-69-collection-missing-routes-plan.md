---
id: MM-109
type: plan
project: magiq-media
workstream: WS-69-collection-missing-routes
repo: magiq-media
tags: [magiq-media, catalog, collection, http, routes, async-operations, 202, long-running]
consumes: []
blocked-by-external: [MM-031]
status: active
branches: []
created: 2026-10-15
depends-on: MM-031, MM-108
breaking-change: API wire
source: alignment-sweep-2026-10-15 cell Collection × http-routes
---

# WS-69 — Collection missing routes + archive/unarchive 202-async + PUT /tags deprecate

**Target repo:** `magiq-media`
**Depends on:** MM-031 (CDK `collection-archive-cascade` state machine shipped), MM-108 (`CollectionArchiveStarted` + `CollectionUnarchiveStarted` + `CollectionUnarchived` + `CollectionArchiveIncomplete` domain + integration events)

## Problem

`docs/spec/contexts/Catalog/aggregates/Collection/collection.api.md` (catalog slice) names 12 Collection HTTP routes. Code wires 9. Three missing + one shape divergence:

| spec route | status |
|---|---|
| POST `/v1/collections` | wired |
| POST `/v1/collections/bulk` | wired |
| PATCH `/v1/collections/{collectionId}` | wired |
| PUT `/v1/collections/{collectionId}/default-profile` | wired |
| DELETE `/v1/collections/{collectionId}/default-profile` | **missing** |
| POST `/v1/collections/{collectionId}/tags/add` | **missing** (code has PUT whole-replace) |
| POST `/v1/collections/{collectionId}/tags/remove` | **missing** |
| POST `/v1/collections/{collectionId}/archive` | wired **but synchronous**; spec: `202 Accepted` + `Location: /v1/collections/{collectionId}/archive-status` |
| POST `/v1/collections/{collectionId}/unarchive` | **missing** |
| GET `/v1/collections/{collectionId}` | wired |
| GET `/v1/collections` | wired |
| GET `/v1/collections/public` | wired |

Code's `PUT /v1/collections/{collectionId}/tags` whole-replaces the tag list; spec splits into additive `POST tags/add` + `POST tags/remove`. Mirrors the Asset `PUT /tags` → `POST tags/add` + `POST tags/remove` divergence shipped under MM-103 / WS-63.

Code's `POST /v1/collections/{collectionId}/archive` dispatches `ArchiveCollectionCommand` inline → `CollectionArchived` fires immediately. Spec: route accepts the command, returns `202 Accepted` + `Location: /v1/collections/{collectionId}/archive-status`, cascade runs on `magiq-media-collection-archive-cascade` state machine (MM-031 CDK), terminator fires `CollectionArchived` or `CollectionArchiveIncomplete` (MM-108).

Code has no `unarchive` route at all. Spec: `POST /v1/collections/{collectionId}/unarchive` → `202 Accepted` + `Location: /v1/collections/{collectionId}/unarchive-status`, same cascade state machine (unarchive branch).

Status endpoints `GET /v1/collections/{collectionId}/archive-status` + `/unarchive-status` are the companion `202 Accepted` resource per `api-conventions.md § Async Operations — 202 Accepted` — they are specified by the long-running convention and land with this plan.

## What the spec requires

- `DELETE /v1/collections/{collectionId}/default-profile` endpoint → `ClearDefaultMediaProfileCommand` (or `SetDefaultMediaProfile(null)` depending on handler shape; align with Collection aggregate's chosen API).
- `POST /v1/collections/{collectionId}/tags/add` → `AddCollectionTagsCommand` (additive — tags listed).
- `POST /v1/collections/{collectionId}/tags/remove` → `RemoveCollectionTagsCommand` (additive — tags listed).
- `POST /v1/collections/{collectionId}/archive`: `202 Accepted` + `Location: /v1/collections/{collectionId}/archive-status`. Handler emits `CollectionArchiveStarted` (MM-108) + dispatches state-machine execution via `IStepFunctionsTaskClient` (WS-05 shipped).
- `POST /v1/collections/{collectionId}/unarchive`: `202 Accepted` + `Location: /v1/collections/{collectionId}/unarchive-status`. Handler emits `CollectionUnarchiveStarted` + dispatches execution.
- `GET /v1/collections/{collectionId}/archive-status` + `/unarchive-status`: status resource returning `status: running | succeeded | partially-succeeded | failed`.
- `PUT /v1/collections/{collectionId}/tags`: emit `Deprecation: true` + `Sunset: <date>` headers for one release; keep the whole-replace semantics during overlap; remove after sunset.

## Wire-visibility

- `POST /archive` return code: `204 No Content` → `202 Accepted` + `Location` header. Breaking for any client switching on return status.
- `POST /unarchive`: new route; additive.
- `POST /tags/add` + `POST /tags/remove`: new routes; additive.
- `DELETE /default-profile`: new route; additive.
- `PUT /tags`: deprecated — one release of headers before removal; existing callers get `Deprecation`/`Sunset` headers but still succeed.

Status endpoints `GET /archive-status` + `/unarchive-status`: new routes; additive.

## Scope boundary

- **Not in scope:** `UnarchiveCollection` + `ClearDefaultMediaProfile` + `AddCollectionTags` + `RemoveCollectionTags` **commands/handlers/aggregate methods** — those belong to the Collection × write-model cell. The endpoint layer in this plan dispatches commands whose write-model implementation lands in that plan. Sequence: write-model cell plan ships command implementations first, then this plan wires the routes.
- **Not in scope:** Collection error codes for cascade refusals — carried by MM-107 / WS-67 constants + handler wiring.
- **Not in scope:** Integration events for cascade terminators — MM-108 / WS-68.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-69 (plan MM-109). Dependencies: MM-031 (CDK), MM-108 (integration events), and Collection × write-model cell plan (unarchive/clear-default-profile/add-tag/remove-tag commands) must ship first. Add 4 missing routes, 2 async-status endpoints, convert archive to 202, deprecate PUT /tags.

## Phase 0 — Scope confirmation

- [ ] MM-031 shipped
- [ ] MM-108 shipped (integration events + domain events)
- [ ] Collection × write-model cell plan shipped (`UnarchiveCollection`, `ClearDefaultMediaProfile`, `AddCollectionTags`, `RemoveCollectionTags` handlers)
- [ ] Current `ArchiveCollectionEndpoint` returns 204 inline — confirm

## Phase 1 — Additive routes

- [ ] `DeleteDefaultMediaProfileEndpoint` at `DELETE /v1/collections/{collectionId}/default-profile`
- [ ] `AddCollectionTagsEndpoint` at `POST /v1/collections/{collectionId}/tags/add`
- [ ] `RemoveCollectionTagsEndpoint` at `POST /v1/collections/{collectionId}/tags/remove`
- [ ] `UnarchiveCollectionEndpoint` at `POST /v1/collections/{collectionId}/unarchive` — `202 Accepted` + `Location: /v1/collections/{collectionId}/unarchive-status`

## Phase 2 — Archive route refactor to 202

- [ ] `ArchiveCollectionEndpoint`: dispatch command → start execution → `202 Accepted` + `Location: /v1/collections/{collectionId}/archive-status`
- [ ] Remove inline synchronous response

## Phase 3 — Status endpoints

- [ ] `GetCollectionArchiveStatusEndpoint` at `GET /v1/collections/{collectionId}/archive-status` — queries `DescribeExecution` on `magiq-media-collection-archive-cascade`
- [ ] `GetCollectionUnarchiveStatusEndpoint` at `GET /v1/collections/{collectionId}/unarchive-status`
- [ ] Status payload per `api-conventions.md § Two cases worth stating explicitly`

## Phase 4 — Deprecate PUT /tags

- [ ] `TagCollectionEndpoint` keeps `PUT /v1/collections/{collectionId}/tags` route for one release
- [ ] Response emits `Deprecation: true` + `Sunset: <date>` headers
- [ ] Release notes name sunset date

## Phase 5 — Tests

- [ ] Integration: `POST /archive` → `202 Accepted` + `Location`; polling status endpoint returns `running` then terminal
- [ ] Integration: `POST /unarchive` symmetric
- [ ] Integration: `POST /tags/add` + `POST /tags/remove` additive
- [ ] Integration: `DELETE /default-profile` clears
- [ ] Integration: `PUT /tags` still works + emits `Deprecation` header

## Phase 6 — Communicate change

- [ ] Breaking-changes.md entries (added in this sweep's Phase 3)
- [ ] Coordinate with magiq-media-ui on `202` + `Location` on archive

## Phase 7 — Ship

- [ ] PR to `develop`

## Phase 8 — Close

- [ ] CLAUDE.md § KDPW: bullet removed
- [ ] INTEGRATION-BACKLOG.md: MM-109 → § Shipped
- [ ] spec-divergence/INDEX.md: WS-69 close row
- [ ] breaking-changes.md: entries move on release cut

## Session log

- 2026-10-15: plan drafted (alignment-sweep-2026-10-15 cell Collection × http-routes; status candidate; depends on MM-031 + MM-108 + Collection × write-model plan)
