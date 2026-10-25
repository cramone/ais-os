---
id: MM-110
type: plan
project: magiq-media
workstream: WS-70-archive-cascades-table
repo: magiq-media
tags: [magiq-media, catalog, collection, folder, read-model, archive-cascade, cascade-report, step-functions]
consumes: []
blocked-by-external: [MM-031]
status: new
branches: []
created: 2026-10-15
depends-on: MM-031, MM-108
breaking-change: Internal
source: alignment-sweep-2026-10-15 cell Collection × read-model
---

# WS-70 — `media-catalog-archive-cascades` table (shared Collection + Folder cascade report)

**Target repo:** `magiq-media`
**Depends on:** MM-031 (CDK state machines shipped), MM-108 (Collection archive cascade integration events — this is the write-side; cascade workers populate rows this table defines)

## Problem

`docs/spec/contexts/Catalog/aggregates/Collection/collection.read-model.md` + `.../Folder/folder.read-model.md` name a shared cascade-report table `media-catalog-archive-cascades`:

| Field | Value |
|---|---|
| Table | `media-catalog-archive-cascades` |
| PK | `TENANT#{TenantId}#CASCADE#{RootId}` where `RootId` is the originating Collection or Folder id |
| SK | `SUMMARY` \| `FOLDER#{FolderId}` \| `ITEM#{MediaItemId}` |
| Owner | Catalog write side — the archive-cascade state machine's Distributed-Map step terminators write per-node rows; the summary row is finalised by the terminator step |

Repo-wide grep returns **zero** hits for `media-catalog-archive-cascades`, `ArchiveCascade`, or `CascadeReport` in `src/`. The table is not provisioned, no schema registered, no projector, no reader.

The spec's `CascadeReportNotFound` error (409 — in `CollectionErrorCodes` under MM-107 / WS-67) refuses unarchive when no persisted report exists for the collection. Without this table, the error has no table to query against.

MM-109's `GET /v1/collections/{collectionId}/archive-status` + `/unarchive-status` endpoints read from this table (the running state query goes to Step Functions `DescribeExecution`; the terminal state and per-node outcomes come from the cascade report rows).

The table is shared between Collection and Folder: Collection cascade writes `CASCADE#{CollectionId}`; Folder cascade writes `CASCADE#{FolderId}`. Same table, same key schema.

## What the spec requires

- CDK provisions `media-catalog-archive-cascades` table.
- Schema registered in `src/modules/Catalog/Catalog.WriteModel.Infrastructure/` (write side writes it) + `.ReadModel.Infrastructure/` (status endpoints read it).
- SK shapes:
  - `SUMMARY` — one per cascade root with `{ TotalNodes, SucceededCount, FailedCount, StartedAt, CompletedAt?, Status: Running|Succeeded|PartiallySucceeded|Failed }`.
  - `FOLDER#{FolderId}` — one per folder visited by the cascade with per-node outcome.
  - `ITEM#{MediaItemId}` — one per item visited by the cascade.
- Written by cascade terminator Lambda(s) targeted from `magiq-media-collection-archive-cascade` + `magiq-media-folder-archive-cascade` state machines (MM-031).
- Read by `GET /archive-status` + `/unarchive-status` endpoints (MM-109; Folder equivalent plan).
- Lifecycle: entries retained per spec (likely TTL on completion + N days — pin to spec row if named; else propose a default and note).

## Scope boundary

This plan is the **table + schema + writer stub + reader shape**. It does not:

- Build the cascade state-machine step terminator Lambdas (those are the host-side companions to MM-031 / WS-04 and belong to the write-model cell plans for Collection and Folder respectively).
- Wire `GET /archive-status` / `/unarchive-status` reader endpoints (that's MM-109 for Collection; Folder's http-routes cell for Folder).
- Carry the `CascadeReportNotFound` error wiring (that's MM-107 / WS-67 for Collection; Folder's error-codes cell for Folder).

Scope: CDK table + repo-side schema registration + minimal `ICascadeReportWriter` + `ICascadeReportReader` so downstream plans have slots to inject.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Also open `D:\source\github\sprbrk-standard\mgq-magiq-media-infra`. Paste:

> Picking up WS-70 (plan MM-110). Depends on MM-031 (CDK state machines shipped). Add `media-catalog-archive-cascades` DynamoDB table in cdk-magiq-media; register schema in magiq-media Catalog.{WriteModel,ReadModel}.Infrastructure; add `ICascadeReportWriter` + `ICascadeReportReader` interfaces + Dynamo-backed implementations.

## Phase 0 — Scope confirmation

- [ ] MM-031 shipped (`magiq-media-collection-archive-cascade` + `magiq-media-folder-archive-cascade` state machines on `spec/initial-alignment`)
- [ ] Repo-wide grep confirms table absent (sanity)
- [ ] Confirm no existing cascade-report writer / reader (sanity)

## Phase 1 — CDK (cdk-magiq-media)

- [ ] Add `media-catalog-archive-cascades` DynamoDB table to per-env stack
- [ ] PK `S` + SK `S`; billing-mode PAY_PER_REQUEST; point-in-time recovery on; TTL attribute `ExpiresAt`
- [ ] IAM — grant cascade state-machine role write; grant `Api` + `QueryApi` read
- [ ] Add table to deploy manifest + `read-model-metadata` seed set (MM-078 WS-55 pattern)

## Phase 2 — magiq-media schema registration

- [ ] `CascadeReportSchema` under `Catalog.WriteModel.Infrastructure/Projections/Schemas/` with three SK discriminators (`SUMMARY`, `FOLDER#`, `ITEM#`)
- [ ] Register in Catalog's `AddCatalogWriteModel` / `AddCatalogReadModel` DI
- [ ] Validate `read-model-metadata` row seeded by WS-55 deploy

## Phase 3 — Writer + reader surfaces

- [ ] `ICascadeReportWriter` interface — `WriteSummaryAsync(TenantId, rootId, summary, ct)`, `WriteNodeAsync(TenantId, rootId, nodeKind, nodeId, outcome, ct)`
- [ ] Dynamo-backed implementation
- [ ] `ICascadeReportReader` interface — `GetSummaryAsync(TenantId, rootId, ct)`, `ListNodeOutcomesAsync(TenantId, rootId, pageParams, ct)`
- [ ] Dynamo-backed implementation

## Phase 4 — Tests

- [ ] Integration: round-trip write/read on each SK discriminator
- [ ] Integration: tenant-prefix enforcement
- [ ] Integration: TTL expiry smoke (table has `ExpiresAt` attribute set)

## Phase 5 — Ship

- [ ] PR to `develop` on magiq-media
- [ ] PR to `develop` on cdk-magiq-media
- [ ] Coordinate merge order: CDK first (table provisioned per env), then host (schema registered + writer/reader bound)

## Phase 6 — Close

- [ ] CLAUDE.md § KDPW: bullet removed
- [ ] INTEGRATION-BACKLOG.md: MM-110 → § Shipped
- [ ] spec-divergence/INDEX.md: WS-70 close row

## Session log

- 2026-10-15: plan drafted (alignment-sweep-2026-10-15 cell Collection × read-model; status candidate; shared concern with Folder — Folder read-model cell will cite this plan rather than duplicate it)
