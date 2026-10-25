---
id: MM-151
type: plan
project: magiq-media
workstream: WS-111-registration-read-model
repo: magiq-media
tags: [magiq-media, registration, read-model, gsi, status-ordinal, dynamodb, opensearch]
consumes: []
blocked-by-external: []
status: active
branches: []
created: 2026-10-16
depends-on: 'WS-55 (read-model-metadata seed), Registration × write-model, MM-150'
breaking-change: API wire
source: alignment-sweep-2026-10-15 cell Registration × read-model
---

# WS-111 — Registration read-model: `RegistrationByStatusIndex` GSI + Status ordinal→name migration

**Target repo:** `magiq-media`
**Depends on:** WS-55, Registration × write-model, MM-150

## Problem

Spec names 3 tables + 3 GSIs. Code has 3 tables + 2 GSIs; one GSI missing. Status wire representation also diverges per CLAUDE.md KDPW.

Covered (5 of 6):

| row | code |
|---|---|
| `media-registration` detail | `RegistrationDetailReadModel` ✓ |
| `media-registrations` summary | `RegistrationSummaryReadModel` ✓ |
| `media-registration-item-ref` (consumer index) | `MediaItemRegistrationIndexProjector` ✓ |
| `RegistrationByMediaItemIndex` GSI | `RegistrationByMediaItemIndexSchema` ✓ |
| `RegistrationByOwnerIndex` GSI | `RegistrationByOwnerIndexSchema` ✓ |

Missing (1):

| row | spec |
|---|---|
| `RegistrationByStatusIndex` GSI on `media-registrations` | `TENANT#{TenantId}#STATUS#{Status}#REGISTRATIONS` / `{StatusChangedAt}#{RegistrationId}` — overdue scanner source |

Status wire representation divergence (per CLAUDE.md KDPW):

- `media-registrations` + `media-registration` rows carry `Status` as the enum **ordinal**.
- Spec writes it as the **member name** under property-scoped `JsonStringEnumConverter`.
- Event-store numeric form on `RegistrationCancelled.PreviousStatus` is unchanged — only read-model + search index move.
- OpenSearch `media-registrations` document mirrors the DynamoDB shape.

## What the spec requires

- CDK: add GSI to `media-registrations` with partition `TENANT#{TenantId}#STATUS#{Status}#REGISTRATIONS`, sort `{StatusChangedAt}#{RegistrationId}`, KEYS_ONLY.
- `IProjectionIndexSchema<RegistrationSummaryReadModel>` registration + projector populates partition/sort on each status change.
- `MaintenanceScanner` registration-response-overdue pass reads this GSI (CLAUDE.md names the scanner).
- Read-model `Status` column written as member name (property-scoped `JsonStringEnumConverter`); OpenSearch document mirrors.
- Migration: rebuild both tables + OpenSearch document under new `schemaVersion` via `projections rebuild-index` (`WS-37` scope), then cutover.

## Wire-visibility

- Breaking (narrow) — `Status` wire format shifts from ordinal integer to member-name string on `GET /v1/registrations` / `GET /v1/registrations/{id}` / `GET /v1/registrations/search` responses. Clients must parse the string form.
- Internal — GSI add is additive on the stored shape; scanner wiring consumes it.

## Scope boundary

- CDK GSI add + schema registration + projector population.
- Status ordinal→name migration via `projections rebuild-index` per tenant under new schemaVersion.
- `MaintenanceScanner` overdue pass → separate workstream (scanner consumes the new GSI; wiring not in this plan).
- `MediaItem.RegistrationRefs` reconciliation (CLAUDE.md KDPW "registration-reference handlers log and ack persistent failure") → separate workstream (consumer-side resilience).

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-111 (plan MM-151). WS-55 seed infra must be in place. Status representation shift coordinates with search index rebuild.

## Phase 0 — Scope confirmation

- [ ] WS-55 seed shipped
- [ ] Registration × write-model shipped (status transitions emit `StatusChangedAt`)

## Phase 1 — `RegistrationByStatusIndex` GSI

- [ ] CDK: GSI on `media-registrations` partition `TENANT#{TenantId}#STATUS#{Status}#REGISTRATIONS`, sort `{StatusChangedAt}#{RegistrationId}`, KEYS_ONLY
- [ ] `IProjectionIndexSchema<RegistrationSummaryReadModel>` schema registration
- [ ] `RegistrationSummaryProjector` populates GSI partition/sort on every status change

## Phase 2 — Status representation

- [ ] `RegistrationSummaryReadModel.Status` + `RegistrationDetailReadModel.Status` serialize as member name (`JsonStringEnumConverter` property-scoped)
- [ ] Reader API responses echo string form
- [ ] OpenSearch `media-registrations` document mirror — mapping update + alias flip

## Phase 3 — Migration

- [ ] Bump `read-model-metadata.media-registrations.schemaVersion` + `.media-registration.schemaVersion`
- [ ] `projections rebuild-index --index media-registrations --tenant <tenant>` per tenant (WS-37 verb)
- [ ] OpenSearch reindex into new alias; flip alias at cutover

## Phase 4 — Tests

- [ ] Projector: status transition → GSI row written + updated `StatusChangedAt`
- [ ] Integration: `GET /v1/registrations/{id}` + list + search return `Status` as string
- [ ] Integration: GSI query returns registrations by status + chronological order
- [ ] Migration test: pre-cutover reads tolerate both forms (compatibility window)

## Phase 5 — Communicate change

- [ ] Breaking-changes.md entry — API wire breaking (Status wire format shift) + internal (GSI add)

## Phase 6 — Ship

- [ ] PR to `develop` (magiq-media) + `spec/initial-alignment` (cdk-magiq-media)

## Phase 7 — Close

- [ ] CLAUDE.md § KDPW: Registration read-model Status + registration-reference handler bullets reviewed; keep separate reconciliation KDPW
- [ ] INTEGRATION-BACKLOG.md: MM-151 → § Shipped
- [ ] spec-divergence/INDEX.md: WS-111 close row

## Session log

- 2026-10-16: plan drafted (alignment-sweep-2026-10-15 cell Registration × read-model; 1 missing GSI `RegistrationByStatusIndex` + Status wire-format shift ordinal→member-name; 5 of 6 covered)
