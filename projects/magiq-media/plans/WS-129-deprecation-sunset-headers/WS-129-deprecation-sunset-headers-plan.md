---
id: MM-168
type: plan
project: magiq-media
workstream: WS-129-deprecation-sunset-headers
repo: mgq-dotnet-platform
tags: [sdk, mgq-dotnet-platform, deprecation, sunset, rfc8594, headers, versioning, cross-cutting]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-19
depends-on: -
breaking-change: API wire
source: alignment-sweep-2026-10-15 cell Cross-cutting×middleware
---

# WS-129 — `Deprecation` + `Sunset` response header emission (RFC 8594)

**Target repos:** `mgq-dotnet-platform` (SDK primitive) + magiq-media (per-route attribute uptake)
**Spec source:** [`api-conventions.md § Deprecation Policy`](../../../../../../source/github/sprbrk-standard/mgq-magiq-media/docs/spec/shared/api-conventions.md)
**Depends on:** none

## Problem

Spec [`api-conventions.md § Deprecation Policy`](../../../../../../source/github/sprbrk-standard/mgq-magiq-media/docs/spec/shared/api-conventions.md) names `Deprecation` + `Sunset` headers (RFC 8594) for routes being retired. Code today: zero `Deprecation`/`Sunset` header hits across `src/` + `mgq-dotnet-platform/src/platform/`. Multiple routes are already marked for deprecation in sweep-drafted plans:

- `DELETE /v1/items/{itemId}` (MM-120 — migrate to `POST /archive` + `POST /dispositions`)
- `PUT /v1/assets/{assetId}/tags` (MM-103 — split into `POST tags/add` + `POST tags/remove`)
- `PUT /v1/collections/{collectionId}/tags` (MM-109 — same split)
- `PUT /v1/items/{itemId}/tags` (potential — follows if applied uniformly)
- `DELETE /v1/profiles/{profileId}/record-types/{recordTypeId}` (MM-125 — migrate via re-pin + republish)
- `PUT /v1/record-types/{recordTypeId}/fields/{fieldName}` (MM-135 — rename to POST `/replace`)

None of these emit `Deprecation` or `Sunset` headers today. Clients cannot auto-detect deprecation; silent breakage on removal.

## Scope

### SDK primitive

- `[MagiqDeprecated(deprecatedOn: "2026-mm-dd", sunsetOn: "2027-mm-dd", successor: "POST /v1/items/{itemId}/archive")]` FastEndpoints route attribute
- SDK response-header middleware emits:
  - `Deprecation: @1793577600` (RFC 8594 Unix timestamp of deprecation announcement)
  - `Sunset: Fri, 01 Jan 2027 00:00:00 GMT` (RFC 8594 HTTP-date of planned removal)
  - `Link: </v1/items/{itemId}/archive>; rel="successor-version"` when `successor` member set
- Idempotent — header set once per response
- Headers also flow through idempotency-key replay path (per F070/WS-19) so cached responses carry the deprecation signal

### magiq-media uptake

- Apply attribute to the 6 identified deprecating routes in the plans listed above
- Dates per the owning plan's release schedule (default: deprecated-now + 180-day sunset)
- Successor route reference per each plan

### What this plan does NOT ship

- Hard removal of deprecated routes (owning plans retain removal step after sunset)
- Deprecation announcement scheduling / release-notes automation
- Operator dashboard tracking caller usage of deprecated routes (future ask)

## Phase 0 — Scope confirmation
- [ ] Read `api-conventions.md § Deprecation Policy` end-to-end
- [ ] Decide `Deprecation` value format (Unix timestamp `@1793577600` vs HTTP-date — RFC 8594 allows both; Unix preferred by some clients, HTTP-date symmetric with `Sunset`)
- [ ] Confirm 180-day sunset window default (coordinate with release cadence)
- [ ] Confirm per-release deprecation announcement workflow (release notes section + sweep's `breaking-changes.md` § Deprecated)

## Phase 1 — SDK primitive
- [ ] `[MagiqDeprecated]` attribute + response-header middleware
- [ ] FastEndpoints integration — pipeline sets headers on 2xx responses
- [ ] `Link: ...; rel="successor-version"` emission when successor supplied
- [ ] Idempotency-replay path preserves headers (WS-19 compatibility)

## Phase 2 — magiq-media uptake
- [ ] `[MagiqDeprecated]` on 6 identified routes (see § Scope)
- [ ] Dates per owning plan's release schedule
- [ ] Successor references point at spec-named replacement routes

## Phase 3 — Tests
- [ ] Unit test: attribute drives header emission on 200/201/202/204 responses
- [ ] Integration test: deprecated route returns Deprecation + Sunset + Link headers
- [ ] Idempotency-replay test: cached response preserves headers

## Phase 4 — Documentation
- [ ] `breaking-changes.md § Deprecated` section lists each route with dates
- [ ] CLAUDE.md § Key conventions names `[MagiqDeprecated]` attribute pattern

## Breaking change

**API wire — additive.** 3 new response headers (`Deprecation`, `Sunset`, `Link`) on deprecated routes only. Clients that read these auto-detect deprecation; those that don't see no change until sunset-driven removal lands (per owning plans). Breaking-changes.md entry under § Expected — API wire — additive. Downstream clients should learn to read `Deprecation` + `Sunset` to track retirement proactively.

## Session log

| Date | Progress |
|---|---|
| 2026-10-19 | Drafted from alignment-sweep Cross-cutting × middleware cell |
