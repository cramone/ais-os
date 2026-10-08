---
id: MM-011
type: plan
project: magiq-media
workstream: WS-19-idempotency-replay-headers
repo: aspnetcore-platform
tags: [aspnetcore-platform, sdk, idempotency, http]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — origin is docs/dependency-gaps/platform-capabilities/F070-idempotency-replay-headers.md and INDEX.md#WS-19; no separate review document.
---

# WS-19 — Idempotency replay-header allowlist

**Target repo:** `aspnetcore-platform` — `D:\source\github\magiqsoftware\aspnetcore-platform`
**Depends on:** none
**Unblocks:** complete `draft-ietf-httpapi-idempotency-key-header-07` conformance (pairs with MM-012 for Pending TTL)

Delivers F070. Current `Magiq.AspNetCore.Idempotency` stores status + body only, discards response headers. Spec requires replaying `ETag`, `Magiq-Aggregate-ETag`, `Magiq-Schema-Budget-Remaining` on cached response.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\magiqsoftware\aspnetcore-platform`. Paste:

> Picking up WS-19 (plan MM-011). Plan at `Z:\claudia\magiq\projects\magiq-media\plans\WS-19-idempotency-replay-headers\WS-19-idempotency-replay-headers-plan.md`. Gap file: `D:\source\github\sprbrk-standard\mgq-magiq-media\docs\dependency-gaps\platform-capabilities\F070-idempotency-replay-headers.md`.
>
> Add `IdempotencyOptions.ReplayHeaders` list. Store allowlisted response headers on completion write; replay on cache hit. Default list: `ETag`, `Magiq-Aggregate-ETag`, `Magiq-Schema-Budget-Remaining`.
>
> Read `aspnetcore-platform/CLAUDE.md`. PR to `aspnetcore-platform/main`.

## Phase 0 — Scope confirmation
- [ ] Read F070 § Required-shape + `docs/spec/shared/api-conventions.md` idempotency section
- [ ] Locate `Magiq.AspNetCore.Idempotency` middleware; identify response-write pipeline
- [ ] Confirm current middleware stores status + body only, discards headers

## Phase 1 — Header allowlist
- [ ] Add `IdempotencyOptions.ReplayHeaders` configurable list; default: `ETag`, `Magiq-Aggregate-ETag`, `Magiq-Schema-Budget-Remaining`
- [ ] Store allowlisted response headers in idempotency record at completion
- [ ] Record schema: existing fields + `Dictionary<string, string[]> Headers`

## Phase 2 — Replay on cache hit
- [ ] On idempotency-key match + completed record: write stored status + body + allowlisted headers
- [ ] Order: headers before `WriteAsync` body (ASP.NET constraint)

## Phase 3 — Tests
- [ ] Unit: first call stores allowlisted headers only; non-allowlisted not stored
- [ ] Unit: replay emits identical allowlisted headers + body
- [ ] Unit: `Idempotent-Replayed: true` + original headers in same response

## Phase 4 — Package + ship
- [ ] Bump `Magiq.AspNetCore.*` version; push internal NuGet
- [ ] PR to `aspnetcore-platform/main`

## Phase 5 — Close
- [ ] F070: shipped
- [ ] platform-capabilities/INDEX.md: WS-19 → § Shipped

## Session log
- 2026-10-08: plan drafted
