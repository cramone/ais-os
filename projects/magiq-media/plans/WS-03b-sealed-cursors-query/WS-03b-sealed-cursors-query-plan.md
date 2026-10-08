---
id: MM-038
type: plan
project: magiq-media
workstream: WS-03b-sealed-cursors-query
repo: magiq-media
tags: [magiq-media, pagination, queryapi, opensearch, security]
consumes: []
blocked-by-external: [MM-020]
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — magiq-media integration half of WS-03 F093.
---

# WS-03b — Wire sealed cursors into QueryApi endpoints + OpenSearch search-after

**Target repo:** `magiq-media`
**Depends on:** MM-020 (WS-03a SDK)
**User policy gate:** no magiq-media code change until all external deps ship.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-03b (plan MM-038). SDK (MM-020) ships `IPaginationCursorSealer`.
>
> Replace raw base64 `LastEvaluatedKey` + unsigned OpenSearch `sort` with sealed cursors. Every QueryApi list endpoint: seal on page emit (bound to tenant, route, params, issuedAt); unseal on next call; 400 `InvalidPageToken` on failure. Treat `nextPageToken` / `nextSearchAfter` as internal key material; never log.
>
> PR to `develop`.

## Phase 0 — Scope confirmation
- [ ] Confirm MM-020 shipped
- [ ] Enumerate every QueryApi list endpoint + OpenSearch search endpoint
- [ ] Audit for current base64 emission + log scrubbing

## Phase 1 — DynamoDB list endpoints
- [ ] Seal `LastEvaluatedKey` with `(tenantId, routeKey, paramsHash)` context
- [ ] Unseal incoming `pageToken`; 400 `InvalidPageToken` on failure

## Phase 2 — OpenSearch search endpoints
- [ ] Seal `sort` array similarly
- [ ] Unseal `searchAfter` on next call; 400 `InvalidPageToken` on failure

## Phase 3 — Logging
- [ ] Scrub `pageToken` / `nextPageToken` / `searchAfter` from Serilog destructure config
- [ ] No cursor in response bodies except on list/search endpoints

## Phase 4 — Tests
- [ ] Unit: seal/unseal happy path
- [ ] Unit: cross-tenant swap → 400
- [ ] Unit: route swap → 400
- [ ] Unit: tampered token → 400
- [ ] Integration: pagination round-trip on each endpoint

## Phase 5 — Ship
- [ ] PR to `develop`

## Phase 6 — Close
- [ ] F093: shipped (full)
- [ ] INTEGRATION-BACKLOG: WS-03b → § Shipped
- [ ] Remove `Pagination cursors are not server-sealed` bullet from `CLAUDE.md`

## Session log
- 2026-10-08: plan drafted (blocked on MM-020 + user policy)
