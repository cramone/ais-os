---
id: MM-100
type: plan
project: magiq-media
workstream: WS-60-sdk-errorcode-slot
repo: mgq-dotnet-platform
tags: [sdk, error-contract, problemdetails, rfc9457, cross-cutting]
consumes: []
blocked-by-external: []
status: done
outcome: shipped
branches: [feature/chase/MM-100-phase0-confirm-shape, feature/chase/MM-100-phase1-sdk-primitive, feature/chase/MM-100-phase2-problemdetails-emission, feature/chase/MM-100-phase3-error-middleware, feature/chase/MM-100-phase4-tests, feature/chase/MM-100-phase5-ship]
created: 2026-10-15
closed: 2026-10-20
depends-on: -
breaking-change: API wire
source: alignment-sweep-2026-10-15 cell Asset×error-codes (cross-cutting prerequisite — reused by every aggregate's error-codes cell)
ado: {project: Media, epicId: 35363}
shipped-in: mgq-dotnet-platform 1.2.0.0
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

## Phase 0 — Confirm shape · AB#35364
- [ ] Confirm `[JsonExtensionData]` on `ProblemDetails.Extensions` lets `errorCode` serialise inline at root (verify ASP.NET Core 8 behaviour) · AB#35371
- [ ] Confirm `DomainError` is a `record` — fluent `with` works · AB#35372

## Phase 1 — SDK primitive · AB#35365
- [ ] `DomainError.ErrorCode` init-only; factory overloads · AB#35373
- [ ] `WithErrorCode(code)` + `WithExtension(key, value)` fluent methods · AB#35374
- [ ] Unit tests: `with`-copy preserves prior members; null `ErrorCode` serialises as absent · AB#35375

## Phase 2 — ProblemDetails emission · AB#35366
- [ ] `DefaultProblemDetailsFactory.CreateProblem(..., errorCode, extensions)` overload · AB#35376
- [ ] `Type` + `Title` + root `errorCode` emission under per-env base URI · AB#35377
- [ ] Validation problem: unchanged (`errors` dict shape stays per § Validation Error Shape) · AB#35378
- [ ] `MagiqWebPlatformOptions.ErrorTypeBaseUri` + `ValidationTypeBaseUri` with defaults · AB#35379

## Phase 3 — Error-handling middleware · AB#35367
- [ ] SDK provides `DomainErrorProblemDetailsMapper` resolving `DomainError.ErrorCode` + `Extensions` + `ErrorType.StatusCode` into one `ProblemDetails` · AB#35380
- [ ] FastEndpoints integration — global exception handler consults mapper · AB#35381
- [ ] Idempotency replay (WS-19/20) stores + replays `errorCode` + extensions unchanged · AB#35382

## Phase 4 — Tests · AB#35369
- [ ] 400 ValidationFailed — `errors` dict + `errorCode: "ValidationFailed"` + inline root · AB#35383
- [ ] 409 ConcurrencyConflict — `errorCode` at root, no `errors` dict · AB#35384
- [ ] 422 with extension (`conflictingRecordTypeId`) — root carries member · AB#35385
- [ ] 404 NotFound — platform code emits bare `404` without specific code (per spec cross-cutting row) · AB#35386
- [ ] Idempotency replay — stored `errorCode` + extensions round-trip · AB#35387

## Phase 5 — Ship · AB#35370
- [ ] PR + release notes flag the ProblemDetails shape change (narrow) · AB#35388
- [ ] `mgq-dotnet-platform` package bump · AB#35389

## Acceptance criteria

- `DomainError` carries `ErrorCode` string + supports fluent `WithExtension`
- `ProblemDetails` emits `errorCode` at root, `type: https://errors.magiqmedia.com/domain/<kebab>`, `title` humanised from the code
- Existing error paths unchanged for callers who do not opt into `errorCode`

## Breaking-change note

Wire-visible: any client that treats `type: https://httpstatuses.com/<n>` as stable will see the URI change the first time a Magiq app ships a coded error. The spec URI (`https://errors.magiqmedia.com/...`) is the one clients must learn to accept.

## Session log

- 2026-10-15: plan drafted by alignment sweep (Asset×error-codes cell). `status: candidate` pending triage.
- 2026-10-19: triaged to `active` + pushed to ADO board `Media` via `ado-create-from-plan` skill test cycle. Epic #35363 created with 6 Features (#35364/35365/35366/35367/35369/35370) + 19 User Stories (#35371..#35389) under Area `Media`, Iteration `MAGIQ Media 42`. All items tagged `plan-id:MM-100; workstream:WS-60`. Links verified via Strategy A (create-with-full-fields + wit_work_items_link batch).
- 2026-10-20: shipped. Phase 0 scope-confirmation closed; Phase 1 SDK primitive merged PR #55; Phase 2 ProblemDetails emission merged PR #55 (70cb59eb); Phase 3 error-handling middleware merged PR #56 (ccfc9a04); Phase 4 tests merged PR #57 (3cc68c01); Phase 5 ship merged PR #58 (5932b165) — package `mgq-dotnet-platform` bumped to `1.2.0.0`, CHANGELOG.md added at repo root flagging the ProblemDetails shape change. Epic MM-100 Done; plan-complete.
- 2026-10-21: 21 downstream MM-plans unblocked — `blocked-by-external: [MM-100]` cleared on MM-101, MM-106, MM-107, MM-112, MM-113, MM-117, MM-118, MM-123, MM-124, MM-127, MM-128, MM-132, MM-133, MM-138, MM-139, MM-144, MM-145, MM-148, MM-153, MM-154, MM-158. Each may consume SDK `DomainError.ErrorCode` + `ProblemDetails` emission + `DomainErrorProblemDetailsMapper` at `MagiqPlatformVersion = 1.2.0.0` via `Directory.Packages.props`.

## Closing out

Plan `done`, outcome `shipped`. Branches committed to (all merged to `main`): `feature/chase/MM-100-phase0-confirm-shape`, `feature/chase/MM-100-phase1-sdk-primitive`, `feature/chase/MM-100-phase2-problemdetails-emission`, `feature/chase/MM-100-phase3-error-middleware`, `feature/chase/MM-100-phase4-tests`, `feature/chase/MM-100-phase5-ship`. Pair with its originating review archived under `_archive/` when the magiq-media archive sweep next runs.
