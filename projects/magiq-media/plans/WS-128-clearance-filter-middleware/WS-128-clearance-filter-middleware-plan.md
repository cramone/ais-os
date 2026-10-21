---
id: MM-167
type: plan
project: magiq-media
workstream: WS-128-clearance-filter-middleware
repo: magiq-media
tags: [magiq-media, classification, clearance, middleware, security, pspf, psr, 403, cross-cutting]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-19
depends-on: MM-100, MM-030, MM-159
breaking-change: API wire
source: alignment-sweep-2026-10-15 cell Cross-cutting×middleware
---

# WS-128 — Classification-clearance filter middleware + `InsufficientClearance 403` emission

**Target repo:** `magiq-media` (reaching into SDK if primitive required)
**Spec source:** [`classification-schemes.md`](../../../../../../source/github/sprbrk-standard/mgq-magiq-media/docs/spec/shared/classification-schemes.md) · [`api-conventions.md § Refusal precedence`](../../../../../../source/github/sprbrk-standard/mgq-magiq-media/docs/spec/shared/api-conventions.md#refusal-precedence--state-before-the-resource-predicate) · [`error-catalog.md § Classification`](../../../../../../source/github/sprbrk-standard/mgq-magiq-media/docs/spec/shared/error-catalog.md)
**Depends on:** MM-100 (SDK `errorCode` slot), MM-030 (`Media:Catalog:ClassificationScheme` tenant setting + AU PSPF/NZ PSR schemes shipped under WS-54), MM-159 (`CrossCuttingErrorCodes.InsufficientClearance` constant)

## Problem

Spec [`classification-schemes.md`](../../../../../../source/github/sprbrk-standard/mgq-magiq-media/docs/spec/shared/classification-schemes.md) states: a caller presenting a token without the required clearance for a record's marking is refused `InsufficientClearance 403`; the record's existence is not disclosed per refusal-precedence rule. Clearance claims are issued by `magiq-auth` as role claims (e.g. `clearance:top-secret`, `clearance:unclassified`).

Code today: zero `ClassificationScheme`/`clearance` hits across `src/` + `mgq-dotnet-platform/src/platform/`. Record markings not resolved; caller clearance not consulted on read/write. Classification scheme setting (MM-030 WS-54) ships AU PSPF + NZ PSR scheme values but has no consumer middleware.

## Scope

### Clearance claim read

- `IActor.Clearances` IReadOnlyCollection<string> — SDK addition on `IActor` sourced from JWT `clearance` role sub-claim or `clearances: [...]` top-level claim (spec-authoritative choice confirmed Phase 0)
- Normalisation: scheme-prefixed (`pspf:top-secret`, `psr:restricted`), with tenant-selected scheme implicit

### Record marking resolution

- `IRecordMarkingResolver<T>` SDK primitive — per-aggregate implementation returns record's current marking from read-model row or stream state
- Default implementation on `MediaItem` + `Collection` + `Folder` resolving marking from `media-item`/`media-collection`/`media-folder` detail row's `ClassificationMarking` member (added to projection by this plan; stream state is capability-field metadata per MM-030 WS-54 field-group spec)

### Clearance filter middleware

- `ClearanceFilterMiddleware` runs **after permission check + resource existence**, before resource predicate (per refusal precedence § state before predicate — slot: state 4 of 5 in [`api-conventions.md § Refusal precedence`](../../../../../../source/github/sprbrk-standard/mgq-magiq-media/docs/spec/shared/api-conventions.md#refusal-precedence--state-before-the-resource-predicate))
- Reads caller's `IActor.Clearances` against resolved marking per tenant's selected scheme (`Media:Catalog:ClassificationScheme`)
- Insufficient clearance → `InsufficientClearance 403` with `errorCode` + no body disclosure of record state/metadata
- Reads also filtered: `GET /v1/items/{itemId}` returns `404 NotFound` (not 403) when caller clearance below marking + record present — refusal precedence slot 2 (exists) folds into non-disclosure

### Per-aggregate uptake

- MediaItem + Collection + Folder detail routes
- Reads: 404 non-disclosure for below-clearance (overrides spec's `InsufficientClearance 403` on read endpoints? Decide Phase 0 — spec says "the resource's existence is not disclosed per refusal precedence", which argues for 404 on reads to preserve non-disclosure)
- Writes: 403 `InsufficientClearance` with no state leak

### What this plan does NOT ship

- magiq-auth `clearance` claim issuance (upstream — pre-requisite exists in magiq-auth per `magiq-auth-role-claims-requirements.md`)
- Per-tenant scheme switching (fixed on provisioning — scheme change = tenant migration)
- Audit log of refusal (lands with WS-124 audit-trail export MM-163)

## Phase 0 — Scope confirmation
- [ ] Read `classification-schemes.md` + `api-conventions.md § Refusal precedence` + `magiq-auth-role-claims-requirements.md` end-to-end
- [ ] Decide `IActor.Clearances` source (JWT role sub-claim vs top-level `clearances` claim)
- [ ] Decide read-path 403 vs 404 (non-disclosure)
- [ ] Confirm MM-030 scheme setting shipped + reachable via `IOptionsSnapshot<ClassificationSchemeOptions>`

## Phase 1 — SDK + ClassificationMarking state
- [ ] `IActor.Clearances` member + JWT parsing
- [ ] `IRecordMarkingResolver<T>` primitive + default implementations
- [ ] `ClassificationMarking` capability-field addition (consumes MM-030 schema)

## Phase 2 — Clearance filter middleware
- [ ] `ClearanceFilterMiddleware` in `Api` + `QueryApi` host pipelines
- [ ] Refusal-precedence slot 4 ordering (permission → exists → state → **clearance** → resource predicate)
- [ ] Non-disclosure on reads (404 for below-clearance)
- [ ] Per-scheme clearance comparison (PSPF/PSR dominance lattices from MM-030)

## Phase 3 — Projection additions
- [ ] `media-item`/`media-collection`/`media-folder` detail rows carry `ClassificationMarking` member
- [ ] Projectors read marking from aggregate's `IsClassified`/`Marking` state (introduces MediaItem/Collection/Folder write-model slot — co-ship or defer behind feature flag)

## Phase 4 — Integration tests
- [ ] Caller with insufficient clearance on read: 404
- [ ] Caller with insufficient clearance on write: 403 InsufficientClearance
- [ ] Caller with sufficient clearance: existing refusal catalog unchanged

## Phase 5 — Compliance mapping
- [ ] `docs/compliance/au-pspf-classification.md` + `nz-psr-classification.md` cite spec + ADR anchors

## Breaking change

**API wire — additive refusal path.** New 403/404 refusal on reads + writes when caller clearance below record marking. Narrow — only materialises for tenants adopting PSPF/PSR classification. Breaking-changes.md entry under § Expected — API wire — additive (narrow). Clients opt in by provisioning clearance claims through `magiq-auth`.

## Session log

| Date | Progress |
|---|---|
| 2026-10-19 | Drafted from alignment-sweep Cross-cutting × middleware cell |
