---
id: MM-100
type: plan
project: magiq-media
workstream: WS-60-sdk-errorcode-slot
repo: mgq-dotnet-platform
tags: [sdk, error-contract, problemdetails, rfc9457, cross-cutting]
consumes: []
blocked-by-external: []
status: active
branches: []
created: 2026-10-15
depends-on: -
breaking-change: API wire
source: alignment-sweep-2026-10-15 cell Asset×error-codes (cross-cutting prerequisite — reused by every aggregate's error-codes cell)
---

# WS-60 — SDK: `errorCode` on `DomainError` + `ProblemDetails` emission

**Target repo:** `mgq-dotnet-platform`
**Depends on:** none
**Cross-cutting prerequisite** for every magiq-media module's error-code wiring.

## Problem

Spec [`error-catalog.md`](../../../../../../source/github/sprbrk-standard/mgq-magiq-media/docs/spec/shared/error-catalog.md) states every write endpoint returns an RFC 9457 `ProblemDetails` carrying `errorCode` at the root (via `[JsonExtensionData]` inline serialisation per RFC 9457 § 3.2). `type` is `https://errors.magiqmedia.com/domain/<kebab-code>`. `title` is derived from `errorCode`.

SDK today:
- `DomainError` carries `Title`, `ErrorMessage`, `ErrorType`, `Exception?`, `Errors?`, `Extensions?` — **no `ErrorCode` string field**
- `DefaultProblemDetailsFactory.CreateProblem` emits only `traceId`, `correlationId`, `timestamp` on `Extensions`; `type` is `https://httpstatuses.com/{status}`; `title` is caller-supplied
- No `errorCode` reaches the wire from any Magiq app

Clients cannot branch on `body.errorCode` because the member is absent.

## Scope

**SDK slot only.** No module-specific codes land here — those are per-aggregate plans (WS-61 Asset, Collection cell will draft WS-62, etc).

### Add

1. `DomainError.ErrorCode` string init-only property. Default `null`. Factory methods (`InvalidOperation`, `ConcurrencyViolation`, `EntityAlreadyExists`, …) optionally take `errorCode`.
2. Fluent builder: `DomainError.WithErrorCode(string)` / `DomainError.WithExtension(key, value)` returning new record (record `with` syntax).
3. `IProblemDetailsFactory.CreateProblem` overload (or extend existing) accepting `errorCode` + extension dictionary. Emits:
   - `problem.Extensions["errorCode"] = errorCode` (serialises inline at root per RFC 9457 § 3.2)
   - `problem.Type = $"https://errors.magiqmedia.com/domain/{KebabCase(errorCode)}"` when `errorCode` present
   - `problem.Title = HumanizeFromPascal(errorCode)` when `errorCode` present and caller supplied no title
4. `MagiqWebPlatformBuilder` option: `ErrorTypeBaseUri` (default `https://errors.magiqmedia.com/domain/`), `ValidationTypeBaseUri` (default `https://errors.magiqmedia.com/validation/`). Allows per-env override.
5. `DomainError → ProblemDetails` middleware (FastEndpoints global error handler or SDK plug-in) that reads `DomainError.ErrorCode` + `Extensions` and populates the ProblemDetails root. Status code resolution from `DomainError.ErrorType.StatusCode`.
6. `errorCode`-carrying `DomainError` round-trips through idempotency replay (WS-19/20 envelope already stores `errorCode` — verify unchanged).

### Keep untouched

- Existing `DomainError.Title` / `ErrorMessage` — complementary, not replaced.
- `DomainError.Extensions` dict — supports `conflictingRecordTypeId`, `fieldErrors`, `candidates`, etc.

## Phase 0 — Confirm shape
- [ ] Confirm `[JsonExtensionData]` on `ProblemDetails.Extensions` lets `errorCode` serialise inline at root (verify ASP.NET Core 8 behaviour)
- [ ] Confirm `DomainError` is a `record` — fluent `with` works

## Phase 1 — SDK primitive
- [ ] `DomainError.ErrorCode` init-only; factory overloads
- [ ] `WithErrorCode(code)` + `WithExtension(key, value)` fluent methods
- [ ] Unit tests: `with`-copy preserves prior members; null `ErrorCode` serialises as absent

## Phase 2 — ProblemDetails emission
- [ ] `DefaultProblemDetailsFactory.CreateProblem(..., errorCode, extensions)` overload
- [ ] `Type` + `Title` + root `errorCode` emission under per-env base URI
- [ ] Validation problem: unchanged (`errors` dict shape stays per § Validation Error Shape)
- [ ] `MagiqWebPlatformOptions.ErrorTypeBaseUri` + `ValidationTypeBaseUri` with defaults

## Phase 3 — Error-handling middleware
- [ ] SDK provides `DomainErrorProblemDetailsMapper` resolving `DomainError.ErrorCode` + `Extensions` + `ErrorType.StatusCode` into one `ProblemDetails`
- [ ] FastEndpoints integration — global exception handler consults mapper
- [ ] Idempotency replay (WS-19/20) stores + replays `errorCode` + extensions unchanged

## Phase 4 — Tests
- [ ] 400 ValidationFailed — `errors` dict + `errorCode: "ValidationFailed"` + inline root
- [ ] 409 ConcurrencyConflict — `errorCode` at root, no `errors` dict
- [ ] 422 with extension (`conflictingRecordTypeId`) — root carries member
- [ ] 404 NotFound — platform code emits bare `404` without specific code (per spec cross-cutting row)
- [ ] Idempotency replay — stored `errorCode` + extensions round-trip

## Phase 5 — Ship
- [ ] PR + release notes flag the ProblemDetails shape change (narrow)
- [ ] `mgq-dotnet-platform` package bump

## Acceptance criteria

- `DomainError` carries `ErrorCode` string + supports fluent `WithExtension`
- `ProblemDetails` emits `errorCode` at root, `type: https://errors.magiqmedia.com/domain/<kebab>`, `title` humanised from the code
- Existing error paths unchanged for callers who do not opt into `errorCode`

## Breaking-change note

Wire-visible: any client that treats `type: https://httpstatuses.com/<n>` as stable will see the URI change the first time a Magiq app ships a coded error. The spec URI (`https://errors.magiqmedia.com/...`) is the one clients must learn to accept.

## Session log

- 2026-10-15: plan drafted by alignment sweep (Asset×error-codes cell). `status: candidate` pending triage.
