---
id: MM-011
type: plan
project: magiq-media
workstream: WS-19-idempotency-replay-headers
repo: mgq-dotnet-platform
tags: [mgq-dotnet-platform, sdk, idempotency, http]
consumes: []
blocked-by-external: []
status: shipped
branches: [feature/chase/MM-011-MM-012-WS-19-20-idempotency-rewrite]
pr: https://github.com/sprbrk-standard/mgq-dotnet-platform/pull/35
merge-sha: 68706c06
shipped: 2026-10-12
shipped-jointly-with: MM-012 (WS-20-idempotency-pending-ttl)
created: 2026-10-08
exception: dependency-gap workstream — origin is docs/dependency-gaps/platform-capabilities/F070-idempotency-replay-headers.md and INDEX.md#WS-19; no separate review document.
---

# WS-19 — Idempotency replay-header allowlist

**Target repo:** `mgq-dotnet-platform` — `D:\source\github\sprbrk-standard\mgq-dotnet-platform`
**Depends on:** none
**Unblocks:** complete `draft-ietf-httpapi-idempotency-key-header-07` conformance (pairs with MM-012 for Pending TTL)

Delivers F070. Current `Magiq.AspNetCore.Idempotency` stores status + body only, discards response headers. Spec requires replaying `ETag`, `Magiq-Aggregate-ETag`, `Magiq-Schema-Budget-Remaining` on cached response.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-dotnet-platform`. Paste:

> Picking up WS-19 (plan MM-011). Plan at `Z:\claudia\magiq\projects\magiq-media\plans\WS-19-idempotency-replay-headers\WS-19-idempotency-replay-headers-plan.md`. Gap file: `D:\source\github\sprbrk-standard\mgq-magiq-media\docs\dependency-gaps\platform-capabilities\F070-idempotency-replay-headers.md`.
>
> Add `IdempotencyOptions.ReplayHeaders` list. Store allowlisted response headers on completion write; replay on cache hit. Default list: `ETag`, `Magiq-Aggregate-ETag`, `Magiq-Schema-Budget-Remaining`.
>
> Read `mgq-dotnet-platform/CLAUDE.md`. PR to `mgq-dotnet-platform/main`.

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
- [ ] PR to `mgq-dotnet-platform/main`

## Phase 5 — Close
- [ ] F070: shipped
- [ ] platform-capabilities/INDEX.md: WS-19 → § Shipped

## Session log
- 2026-10-08: plan drafted.
- 2026-10-12: scope audit (Phase 0) found gap-file premise wrong — middleware was a naive-reject guard, store schema was PK+ExpiresAt+Ttl only, no stored envelope, no Pending/Complete states, no fingerprint, no operation scope. CLAUDE.md confirms F070 + F072 share one middleware upgrade; scope expanded to joint rewrite with WS-20 per Chase. Delivered on branch `feature/chase/MM-011-MM-012-WS-19-20-idempotency-rewrite`:
  - `IIdempotencyStore` gains `TryAcquireAsync` / `CompleteAsync` / `ReleaseAsync` (breaking — old `ExistsAsync` / `MarkAsync` dropped). Supporting records in `Idempotency.Abstractions`: `IdempotencyScope`, `IdempotencyState`, `IdempotencyCompletedEnvelope`, `IdempotencyAcquireResult.{Acquired,Existing}`.
  - `DynamoDbIdempotencyStore` acquires via conditional `PutItem` (`attribute_not_exists OR (State=Pending AND PendingExpiresAt < now)`); promotes via `UpdateItem` under `State = Pending` guard; releases via `DeleteItem`. New attributes: State, Fingerprint, PendingExpiresAt, CompleteExpiresAt, StatusCode, ContentType, Body, ErrorCode, Headers.
  - Middleware wraps response stream, computes SHA-256 fingerprint over method + resolved path + query + body, resolves operation = method + route template via `GetEndpoint`, discriminates: fingerprint mismatch → 422 IdempotencyKeyReused; Existing(Pending) → 409 IdempotentRequestInProgress + Retry-After; Existing(Complete) → replay status + body + allowlisted headers; Acquired → run pipeline + classify (release on 401/429/5xx/409-ConcurrencyConflict, complete otherwise).
  - `IdempotencyOptions`: `PendingHorizon` (20min default), `ReplayHeaders` (default ETag, Magiq-Aggregate-ETag, Magiq-Schema-Budget-Remaining); existing `Window` becomes the completion TTL. Startup validates `PendingHorizon < Window`.
  - Host-side invariant `PendingHorizon > ApiLambdaTimeout + PipelineRetryBudget` not enforced in the plugin — SDK doesn't know host timeout. Documented in `IdempotencyOptions.PendingHorizon` XML doc.
  - 14 new unit tests (4 store + 10 middleware) green locally; `IsEnabled`/scope-key patterns handled with `CA1873` suppressed project-wide (sibling of repo-wide `CA1848`).
- 2026-10-12: PR #35 merged to `mgq-dotnet-platform/main` as `68706c06`. F070 + F072 flipped to shipped, platform-capabilities/INDEX.md WS-19 + WS-20 moved to § Shipped, INTEGRATION-BACKLOG MM-011 + MM-012 moved to § Shipped, readiness summary bumped 67→65 `new`, 6→8 `shipped`.
