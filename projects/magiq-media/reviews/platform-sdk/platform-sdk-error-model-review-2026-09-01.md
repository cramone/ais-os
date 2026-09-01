---
id: MM-039
type: review
project: magiq-media
workstream: platform-sdk
raised-by: [MM-022]
status: findings-agreed
outcome: pending
todo-id: -
created: 2026-09-01
---

> **Split out of `plans/spec-drift-review/spec-repo-drift-review.md` § N.2 on 2026-09-01.** It had been
> an appendix to a drift checklist since 2026-08-21 — no id, no status, invisible to the board, and
> impossible to plan or archive. Nothing here is closed or restated; the section moved verbatim and was
> then refreshed against the repos. `status: findings-agreed` because these findings have been agreed
> for weeks; what they have never had is a home.

# Platform SDK — five gaps the consuming app works around

_Everything here belongs in **`aspnetcore-platform`**, not `magiq-media`. Each is something more than one
bounded context needs and the platform does not provide, so each has been worked around locally._

_Re-counted against both repos 2026-09-01. **Three of the section's own numbers were stale**, all in the
direction it predicted — see § What changed on the split._

---

## What changed on the split — read this before the prompt

**1. The duplication count was three; it is five.** N.2.2 argued *"three copies is the point at which
this stops being a workaround and starts being a convention"* and forecast *"ChangeRequests and
DocumentSigning will each want a fourth and a fifth."* The forecast came true and the argument was never
updated. Counted 2026-09-01 — **five byte-identical `DomainErrorCodes.cs` files**:

- `Catalog/Catalog.Domain/Errors/DomainErrorCodes.cs`
- `Metadata/Metadata.Domain/Errors/DomainErrorCodes.cs`
- `Registration/Registrations.Domain/Errors/DomainErrorCodes.cs`
- `AssetManagement/AssetManagement.Domain/Errors/DomainErrorCodes.cs`
- `ChangeRequests/ChangeRequests.Domain/Errors/DomainErrorCodes.cs`

MM-022's archive tracked the drift in passing (*"Four copies … Five, now"*) without anyone amending the
section making the case. **The prompt below still reads as a forecast; it is a description.**

**2. The prompt covers three of the five gaps.** It was written when § N.2 had three. **N.2.4** and
**N.2.5** were added later and have no prompt text — do not treat "copy from here down" as complete.

**3. The real blocker is a missing project reference, and the section never names it.** N.2.3 correctly
identifies that `IProblemDetailsFactory` takes no `IDomainError`. It does not say why the overload cannot
simply be added: **no ASP.NET-side SDK project references `Magiq.Platform.WriteModel.Domain`**, so the
HTTP layer cannot name `IDomainError` at all. A repo-wide grep of `src/aspnetcore` for
`IDomainError`/`WriteModel` returns zero. `Magiq.AspNetCore.Platform.Abstractions.csproj` has no such
reference either. **That edge is a layering decision, and it is the actual gate on Change 3.**

> **Decided 2026-09-01 (Chase): a new `Magiq.AspNetCore.FastEndpoints.Errors` package**, referencing both
> the HTTP side and `WriteModel.Domain`, rather than widening `Platform.Abstractions`. Same end result
> without making every consumer of Abstractions depend on the write-model domain. **Apply Change 3 there,
> not in `Platform.Abstractions`.**

**4. What is already on the shelf.** FastEndpoints and FluentValidation are both already referenced by
SDK projects, `IProblemDetailsFactory` is already resolvable from the FastEndpoints plugin, and the
plugin already assigns `config.Errors.ResponseBuilder` inline at `Startup.cs:45-50`. The app's
`ErrorCodeResponseConfigurator` is a **superset of those six lines**, so the end state is folding the
enrichment into that existing default — at which point both `Api` and `QueryApi` get it with **zero
registration**, and the app-local class and its `AddFastEndpointsConfigurator` call are deleted.

**5. Closing this closes app findings.** **X-10.3** (`QueryApi` cannot emit an `errorCode` at all)
resolves as a side effect — it is the same gap seen from the consuming end. The five `DomainErrorCodes.cs`
copies are deleted. `WithMetadata`, which is platform API today, starts reaching clients at all.

---

Everything below belongs in **`aspnetcore-platform`**, not in `magiq-media`. Each is something more than
one bounded context needs and the platform does not provide, so each has been worked around locally —
twice already, and ChangeRequests and DocumentSigning will each want a third copy.

_Was three; **N.2.4** was added 2026-08-23. Unlike the first three it has no local workaround, which is
why it changed what CR-11 could implement._

## N.2.1 There is no generic `Conflict` factory

_The `N.2.x` numbering is kept deliberately: MM-022's archive and several correction notes cite these ids, and renaming them would orphan those references._

`ErrorType.Business` has `ResourceExists` (409), `ResourceNotFound` (404), `InvalidOperation` (422) and
`ValidationFailed` (400). There is **nothing for a state conflict** — a refusal that is a genuine 409 but
is not "this thing already exists".

`DomainError.EntityAlreadyExists` is the only 409-mapped `Business` error, and its `Title` is
`"Entity Error"`, which reads wrong on "the record type has no open draft". So both places that needed a
409 routed around it through `DomainError.FromErrorCode(409, "Conflict", message)`, which maps
`HttpStatusCode.Conflict` back onto the same `ResourceExists` ErrorType. It works, and it is a workaround
with an explanatory comment attached in two repositories' worth of aggregate code:

- `magiq-media/src/modules/AssetManagement/AssetManagement.Domain/Aggregates/Asset.cs` — private
  `Conflict(string)` helper
- `magiq-media/src/modules/Metadata/Metadata.Domain/Aggregates/DomainErrors.cs` — public
  `Conflict(string)` helper, carrying Chase's own `// todo: move this to platform.`
- `magiq-media/src/modules/Registration/Registrations.Domain/Aggregates/DomainErrors.cs` — third copy,
  added 2026-08-22 (R-13)

## N.2.2 `DomainError` has no error-code concept

`DomainError` carries an `ErrorType`, which fixes the HTTP status and says nothing about *which* rule
refused. The platform documents `extensions.errorCode` as the convention — every error catalog in
`magiq-media/docs/spec/shared/error-catalog.md` is written in those terms — and provides no way to set
one. `WithMetadata(key, value)` exists and is close, but there is no agreed key and no reader.

Catalog, Metadata and Registration therefore each ship a **byte-identical** `DomainErrorCodes` static
class with `WithCode(this DomainError, string)` and `CodeOrNull(this IDomainError)` extensions, because
a module cannot reference another module's Domain project:

- `magiq-media/src/modules/Catalog/Catalog.Domain/Errors/DomainErrorCodes.cs`
- `magiq-media/src/modules/Metadata/Metadata.Domain/Errors/DomainErrorCodes.cs`
- `magiq-media/src/modules/Registration/Registrations.Domain/Errors/DomainErrorCodes.cs` — added
  2026-08-22 (R-13)

**Three copies is the point at which this stops being a workaround and starts being a convention.**
ChangeRequests and DocumentSigning will each want a fourth and a fifth.

## N.2.3 `IProblemDetailsFactory` cannot see a `DomainError` at all

This is the deepest of the three and the reason the first two only half-work.

`Magiq.AspNetCore.Platform.Errors.IProblemDetailsFactory` exposes `CreateProblem(context, statusCode,
title, detail, type)` and `CreateValidationProblem(...)`. **Neither takes an `IDomainError`**, so
`DomainError.Extensions` — where `WithMetadata` and the local `WithCode` both put their data — never
reaches the response. `DefaultProblemDetailsFactory.AddCommonExtensions` writes `traceId`,
`correlationId` and `timestamp` and nothing else.

Consequence in the app: after tagging every Metadata refusal with a code, the endpoints still cannot use
the platform path. They have to reach for FastEndpoints' own
`AddError(message, errorCode)` and read the code back off the error themselves:

```csharp
// magiq-media/src/modules/Metadata/Metadata.WriteModel.Endpoints/V1/MetadataEndpoint.cs
AddError(error.ErrorMessage, error.CodeOrNull());
await SendErrorsAsync((int)error.ErrorType.HttpStatusCode, cancellationToken);
```

So the `errorCode` contract is carried by the *web framework plugin*, not by the platform's own error
pipeline, and anything not using FastEndpoints would silently drop it. `WithMetadata` — which is platform
API — is on the same footing: `RecordTypeAliasNotUnique` attaches `alias` and
`UnrecognisedCapabilityType` attaches `capabilityType`, and **neither reaches the client today**.

## N.2.4 An index query cannot filter — `Matches` is dead against DynamoDB

_Found 2026-08-23 during CR-11._

`IIndexQuery<T>.Matches(T projection)` is an abstract predicate every query in the repo implements, and
every one of them reads like a filter:

```csharp
// ListChangeRequestsByOwnerQuery
public override bool Matches(ChangeRequestSummaryReadModel rm)
{
    return rm.TenantId == TenantId && rm.OwnerId == OwnerId;
}
```

**It never runs in production.** The only caller is
`InMemoryProjectionStore.QueryIndexAsync` (`Stores/InMemoryProjectionStore.cs:231`).
`DynamoDbProjectionStore.QueryIndexAsync` builds a `QueryRequest` from the partition key and the
optional `IndexSortKeyCondition`, sets **no** `FilterExpression`, and returns whatever the index gives
back — `Matches` is not consulted anywhere in that method.

Two consequences, and the second is the dangerous one:

1. **Any predicate a query expresses only in `Matches` is a no-op against DynamoDB.** Today that is
   harmless, because every `Matches` in this repo restates what the partition key already guarantees.
   It is harmless by luck, not by design.
2. **The in-memory store and the DynamoDB store disagree.** A test against the in-memory store proves a
   filter works; the same query in `dev` returns unfiltered rows. Anyone who adds a genuine filter to a
   `Matches` — the natural thing to do, given the signature — gets a green test suite and a wrong API.

This is what stopped CR-11 implementing the specced `Status?` filter. With no `FilterExpression`
support, the only place a filter can live is the sort key, and putting `Status` there costs
chronological ordering across statuses.

**What the platform needs:** either a `FilterExpression` hook on `IProjectionIndexSchema` (or
`IIndexQuery`) that the DynamoDB store translates and applies, or — if filtering is deliberately not
supported — `Matches` should be removed from the interface so it cannot be mistaken for one. The
current state is worse than either: an interface member that looks like a filter, behaves like one in
tests, and is ignored in production.

Note that a DynamoDB `FilterExpression` is applied *after* the read, so it does not reduce RCU and it
interacts badly with pagination — a page can come back nearly empty while `LastEvaluatedKey` is still
set. Whoever implements this should decide how the pager reports that, rather than leaving each caller
to discover it.

## N.2.5 `IReadModelReader` cannot list one parent's children

_Found 2026-08-23 during CR-20._

`IProjectionStore<T>` has two `ListAsync` overloads — tenant-wide, and **group-scoped**:

```csharp
Task<PagedResult<T>> ListAsync(string tenantId, string groupKey, PagerParameters pager, CancellationToken ct);
```

The group overload is the one that answers "all comments on this change request", "all versions of this
item" — the single most common read shape in the platform. `IReadModelReader<T>`, which is what query
handlers are told to inject ("Inject this interface into query handlers only"), exposes only the
tenant-wide overload and `QueryIndexAsync`.

So a handler that needs a parent's children has three options, and all three are bad:

1. Inject `IProjectionStore<T>` directly, against the interface's own guidance. This is what
   `ListChangeRequestCommentsHandler` now does — the only handler in the repo that does.
2. Build a GSI that duplicates what the base table's partition key already answers, paying a
   `schemaVersion` bump and a full-history projection rebuild for it.
3. Call `QueryIndexAsync` and hope — which is what the ChangeRequests comment handler did, against an
   index schema that was never registered, so it threw on every request (CR-20).

**What the platform needs:** the group-scoped `ListAsync` promoted onto `IReadModelReader<T>` and
`ReadModelReader<T>`, forwarding to the store exactly as the tenant-wide one does. It is a four-line
change with no behavioural risk, and it removes the only reason a query handler currently reaches past
the reader.

## Prompt for the `aspnetcore-platform` repo

> Copy from here down.

---

**Context.** Two bounded contexts in the consuming app (`magiq-media`) have independently worked around
three gaps in the platform's error handling. Both workarounds are now duplicated verbatim, and two more
modules are about to need a third copy. The goal is to move the concepts into the platform and delete the
local copies.

**Change 1 — add a state-conflict error type and factory.**

In `src/platform/Domain/Magiq.Platform.WriteModel.Domain/Errors/ErrorType.cs`, add to
`ErrorType.Business`:

```csharp
public static readonly ErrorType Conflict = new Impl(nameof(Conflict), 410, HttpStatusCode.Conflict);
```

Pick an unused `value` — `ResourceExists` is 409, `ResourceNotFound` 404, `InvalidOperation` 422,
`ValidationFailed` 400, and the `Concurrency` pair are both 409, so the numeric `value` is not a status
code and must simply be unique. Do **not** change `ErrorType.FromCode`'s existing
`HttpStatusCode.Conflict => Business.ResourceExists` mapping without checking callers — changing it is a
behaviour change for anyone using `FromErrorCode(409, ...)` today, and at least two call sites do.

In `DomainError.cs`, add a factory beside `EntityAlreadyExists`:

```csharp
/// <summary>
/// Creates a conflict error — the request conflicts with the current state of the target resource, and
/// the caller can resolve it and resubmit the identical request (RFC 9110 §15.5.10). Distinct from
/// <see cref="EntityAlreadyExists" />, which is specifically a duplicate.
/// </summary>
public static DomainError Conflict(string? message = null)
{
    return new DomainError("Conflict", MessageOrDefault(message, () => "Conflict."), ErrorType.Business.Conflict);
}
```

**Change 2 — give `DomainError` a first-class error code.**

Add to `DomainError.cs`, next to the existing `WithMetadata` instance method (currently around line 290):

```csharp
/// <summary>The extension key an error code is carried under, on the error and on the response.</summary>
public const string ErrorCodeExtensionKey = "errorCode";

/// <summary>Returns a copy of this error carrying a stable, machine-readable code.</summary>
public DomainError WithCode(string code) => WithMetadata(ErrorCodeExtensionKey, code);
```

And on `IDomainError` (or as an extension in `DomainErrorExtensions.cs`, which is the better home since
`IDomainError` should stay a pure contract):

```csharp
/// <summary>Reads the error code off an error, or null if it carries none.</summary>
public static string? CodeOrNull(this IDomainError error)
{
    if (error.Extensions is null || !error.Extensions.TryGetValue(DomainError.ErrorCodeExtensionKey, out var value))
    {
        return null;
    }

    return value as string;
}
```

Match the semantics of the existing local implementation exactly — it is already in production use:
`WithCode` returns a **copy** (`DomainError` is a record), preserves any existing extensions, and
overwrites the key if already present. Reference implementation:
`magiq-media/src/modules/Catalog/Catalog.Domain/Errors/DomainErrorCodes.cs`.

**Change 3 — let the problem-details pipeline see the error. This is the important one.**

`IProblemDetailsFactory` in `src/aspnetcore/Platform/Magiq.AspNetCore.Platform.Abstractions/Errors/`
has no overload that takes an `IDomainError`, so `DomainError.Extensions` never reaches the wire.
`errorCode`, and every `WithMetadata` value alongside it, is dropped by the platform today. Add:

```csharp
/// <summary>
/// Creates a problem details object from a domain error, carrying its extensions — including
/// <c>errorCode</c> — onto the response.
/// </summary>
ProblemDetails CreateProblem(HttpContext context, IDomainError error, string? type = null);
```

Implement it in `DefaultProblemDetailsFactory`: derive `Status` from `error.ErrorType.HttpStatusCode`,
`Title` from `error.Title`, `Detail` from `error.ErrorMessage`, then call the existing
`AddCommonExtensions` and copy every entry of `error.Extensions` into `problem.Extensions`.

Two rules for the copy, both of which matter:

- **Do not let a domain extension overwrite `traceId`, `correlationId` or `timestamp`.** Those are
  infrastructure identity; a domain error that happens to attach a key of the same name must not be able
  to forge them. Copy domain extensions **first**, then `AddCommonExtensions`, so the platform keys win.
- **Keep `errorCode` a plain string.** It is a contract clients branch on. If the value stored is not a
  string, omit it rather than serialising something unexpected.

**Also worth doing while in there:** `error.Errors` (the `IReadOnlyDictionary<string, string[]>`
field-level detail) should route to `CreateValidationProblem` when populated, so a `422` with field errors
comes out as a `ValidationProblemDetails` rather than losing the per-field breakdown. Check the current
behaviour before changing it — this may already be handled at the endpoint layer in consuming apps.

**Tests.** Cover: `WithCode` preserves pre-existing extensions and overwrites a repeated key;
`CodeOrNull` returns null for an untagged error and for a non-string value; `Conflict` maps to 409;
`CreateProblem(context, error)` puts `errorCode` under `extensions` and cannot be made to overwrite
`traceId`.

**Consuming-app follow-up** (do not do this in the platform repo — record it for `magiq-media`):
delete `Catalog.Domain/Errors/DomainErrorCodes.cs`, `Metadata.Domain/Errors/DomainErrorCodes.cs` and
`Registrations.Domain/Errors/DomainErrorCodes.cs`; drop the private `Conflict` helper on
`AssetManagement.Domain/Aggregates/Asset.cs` and the public ones on
`Metadata.Domain/Aggregates/DomainErrors.cs` and `Registrations.Domain/Aggregates/DomainErrors.cs`; and
switch all three modules' endpoint base classes from
`AddError(error.ErrorMessage, error.CodeOrNull())` to the new `CreateProblem(context, error)` path. The
`errorCode` values themselves are already published API contract — see
`magiq-media/docs/spec/shared/error-catalog.md` — so **no code string may change** in that cleanup.

---
