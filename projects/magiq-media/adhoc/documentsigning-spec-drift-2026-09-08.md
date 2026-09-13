# DocumentSigning — Spec ↔ Repo Drift Report

_magiq-media · 2026-09-08 · Chase Ramone_

**This is a standalone report, not a `review-cycle` review.** It has no `MM-` id and is not indexed in
`reviews/README.md`. If any block of it is taken forward, that block becomes a review in its own
workstream folder and this file becomes its evidence.

---

## Scope

| | |
|---|---|
| **Spec** | `D:\source\github\sprbrk-standard\mgq-magiq-media\docs\spec\contexts\DocumentSigning\` — 7 files, 1,561 lines |
| **Code** | `src\modules\DocumentSigning\` — 5 projects, 23 `.cs` files (excl. `obj`/`bin`) · `src\hosts\SagaOrchestrator.DocumentSigning\` — 4 `.cs` files |
| **Also read** | `src\modules\Catalog` (`MediaItem`, its events, `Capability`, `Link`/`UnlinkSigningSession`), `src\hosts\Api` (`DomainEventPublishingMiddleware`), `src\hosts\Projectors.ReadModel`, `src\hosts\TimeoutScanner`, `projection-tables.manifest.json`, `Magiq.Media.sln`, `docs\spec\shared\` (error-catalog, operations, event-store-and-messaging, authorization-matrix, glossary), `docs\spec\architecture\`, `cdk-magiq-media` (`magiq-media-stack.ts`, `sqs-queues.ts`, `read-models.ts`), `aspnetcore-platform` (`IReadModel`, `IVersionedProjection`) |
| **Aggregate** | `DocumentSigningSession` — the only one in this context, and **it does not exist as a class** |

**Method.** Code first, spec second. Every claim below was checked against source rather than against a
sibling document — including the claims the spec makes *about* the code, several of which are themselves
now stale in the optimistic direction. Platform semantics (`IVersionedProjection`, `IReadModel`) were read
in `aspnetcore-platform`. Provisioning was read in `cdk-magiq-media`, not inferred from the spec's own
"not provisioned" notes.

---

## Headline

**40 findings. 12 High.**

| | Count | What it means |
|---|---:|---|
| **Spec wrong, code right** | 22 | Documentation drift against code that exists. |
| **Code wrong or unspecified behaviour** | 9 | § 1 — SIGN-1 through SIGN-9. |
| **Spec ↔ spec contradictions** | 9 | Two spec files disagree; no code exists to arbitrate. |

**The spec and the code are not two views of one design — they are two different designs.** The spec
describes an aggregate-centric module: a `DocumentSigningSession` event-sourced root with nine commands,
handler-side preconditions, an owner, a completion token, and a saga that manages a checkout lock. What
was actually built is the *opposite shape* — nine standalone domain events with no emitter, a detail
projector, two read models, two unimplemented ACL query interfaces, and an anti-corruption adapter host
that is not a saga. Every aggregate-shaped assertion in `documentsigningsession.write-model.md` is
therefore not merely unimplemented but **unimplementable against the events as written**: the events omit
`OwnerId` and `CompletionToken`, which four separate spec invariants depend on.

**`sagas/documentsigningsaga.md` is the exception and it is excellent.** It was written against the code
on 2026-08-25, separates "what the code settles" from "what is open" section by section, and every claim
in it that I re-checked still holds. It has **one** stale claim (SIGN-25 below is not it — see § 3). The
other five files are pre-code design records that have been patched with dated correction notes but never
swept, and they are the source of 31 of the 40 findings. This is the same split Processing and Catalog
showed: **the saga file is the best document in the tree and the scenarios file is the worst.**

**Three findings are behavioural and would ship as defects the day the module is picked up:**

1. **`SigningSessionDetailProjector` never advances `ProjectedVersion`** (SIGN-1). Only the creation
   handler sets it. All eight update handlers use `current with { … }` and omit it, pinning the fence at
   the creation event's version forever. `ProjectedVersion` is the platform's *only* idempotency guard
   (`IVersionedProjection`) and the DynamoDB store's conditional-write predicate. `MediaItemDetailProjector`
   sets it on every upsert; this one does not.
2. **The domain's identifier value objects are `string`-wrapped structs with implicit `string` conversion**
   (SIGN-2) — not `Id<T>`. That is a direct violation of platform constraint 8, and it creates a *second*
   `SigningSessionId` type incompatible with Catalog's, which is the one that actually has to receive it
   through `LinkSigningSessionCommand`.
3. **The `SigningCompleted` event cannot carry the value its own invariant validates** (SIGN-10).
   `CompletionToken` appears in the invariant table, the method signature, the command, the API body, the
   glossary and DS-1's key invariants. It appears in no code, and the event record has no field for it.

**The remaining drift clusters in four places:**

1. **Four identity concepts the spec uses do not exist** (§ 2) — `OwnerId`, `UserId`, the four
   `MediaItemCheckout*` events, and `MediaItemSigningSessionLinked`/`Unlinked`. The real vocabulary is
   `InitiatedBy`, `MemberId`, `EditSessionOpened`/`EditSessionClosed(Reason)`, and
   `SigningSessionLinked`/`Unlinked`. The whole authorization model in `documentsigningsession.api.md`
   rests on `session.OwnerId`, which no event carries and no read model stores.
2. **`documentsigningsession.write-model.md` specifies two mutually exclusive architectures for the same
   two reference models** (SIGN-16) — § Consumed Integration Events says direct-query ACL with "no local
   projection or event subscription", and § Reference Models, further down the same file, documents
   DocumentSigning-owned projectors subscribing to Catalog events off `media-projector`.
3. **Names disagree three ways across files for the same three things** (§ 5) — the adapter's inbound
   queue, the webhook route, and the table used for webhook `TenantId` resolution.
4. **`error-catalog.md` has no DocumentSigning section at all** (SIGN-37), though the catalog's own
   preamble says it does. Six error codes exist only inside DocumentSigning's own spec files.

**What is genuinely built and correct** — worth stating, because three of the spec's own status notes now
understate it: the nine domain events (well-formed, `[DomainEvent]`-attributed, `ITenantScoped`);
`SigningSessionDetailProjector` (complete across all nine events, correctly keyed, with a named-argument
comment recording a real past tenant-transposition bug); both read-model records; `Capability.Signing`
(the ninth enum member, shipped); and Catalog's `LinkSigningSession`/`UnlinkSigningSession` commands,
handlers and events (registered, tested). Roughly a third of the design exists. **None of it is
reachable** — no host calls `AddDocumentSigningReadModelProjectors()`, `DomainEventPublishingMiddleware`
excludes `ISigningDomainEvent`, no signing table is in `projection-tables.manifest.json` or in CDK, and
CDK declares no Lambda for `SagaOrchestrator.DocumentSigning`.

---

# 1. Code-side defects and unspecified behaviour

Nine findings where the code, not the spec, is likely what should move. All are latent — nothing runs —
but SIGN-1 and SIGN-2 become live defects the moment the module is wired, and both are cheaper to fix now.

### SIGN-1 · **High** · `SigningSessionDetailProjector` never advances `ProjectedVersion`

`ApplyAsync(SigningSessionInitiated …)` constructs the model with `ProjectedVersion: e.AggregateVersion`.
The other **eight** handlers all take the `current with { … }` path and none of them touches
`ProjectedVersion`:

```csharp
// SigningEnvelopeCreated — representative of all eight
: UpsertAsync(current with { EnvelopeId = e.EnvelopeId, Status = SigningSessionStatus.EnvelopeCreated, UpdatedAt = e.OccurredAt });
```

`IVersionedProjection.ProjectedVersion` is documented in the platform as *"compared against the incoming
event version by the projection dispatcher to skip duplicate events, and by the DynamoDB store to guard
conditional writes."* Pinned at version 1 forever, the record either accepts every redelivery unguarded or
is rejected by the conditional write on every subsequent event — which of the two depends on the store's
comparison, and neither is correct.

**The house pattern is one line away.** `MediaItemDetailProjector` (`Catalog.ReadModel`, lines 125 and 133)
writes `ProjectedVersion = e.AggregateVersion` inside every `with` expression, including the two
signing-session handlers. Copy that.

**Fix:** add `ProjectedVersion = e.AggregateVersion` to all eight `with` expressions.

---

### SIGN-2 · **High** · Identifier value objects are `string` structs with implicit conversion, not `Id<T>`

All four ids in `DocumentSigning.Domain/ValueObjects/` have this shape:

```csharp
public readonly record struct SigningSessionId(string Value)
{
    public static implicit operator string(SigningSessionId signingSessionId) => signingSessionId.Value;
}
```

`MediaItemId`, `MediaProfileId` and `MemberId` are identical. Three problems, in ascending order of cost:

1. **Platform constraint 8 says `Id<T>` backed by `Medo.Uuid7`** — *"Always use `Id<T>` subclasses, never
   raw `Guid` or `string` for entity or aggregate identifiers."* Nothing here validates a UUID at all, let
   alone v7, so the write-model spec's *"UUID v7 string, immutable"* is unenforced by construction.
2. **The implicit `string` operator defeats the point of the type.** A `MediaItemId` and a `MemberId` are
   mutually assignable through `string` in any expression that expects one. The projector's own
   named-argument comment records exactly this class of bug already having happened once — *"a positional
   call previously transposed them — every projected row stored the signing session id in the tenant
   field"* — and the implicit operator is the reason a transposition compiled.
3. **This is a second, incompatible `SigningSessionId`.** Catalog has its own in
   `Catalog.Domain/Aggregates/MediaItems/ValueObjects/`, constructed via `SigningSessionId.From(...)`.
   `LinkSigningSessionCommand` takes Catalog's. Whatever eventually dispatches it from DocumentSigning has
   to cross that boundary, and today the only conversion available is the implicit-`string` one.

**Fix:** convert the four to `Id<T>` before anything is built on them. This is the cheapest it will ever
be — nothing constructs them yet.

---

### SIGN-3 · Medium · `CheckoutStatus` is a duplicated vocabulary with no owner

`DocumentSigning.Domain/ValueObjects/CheckoutStatus.cs` declares `{ Available, CheckedOut }`. Catalog does
not have this enum: `MediaItemDetailReadModel` carries `string CheckoutStatus = "Available"` as a
projected column, derived from the `EditSession*` event family. So DocumentSigning has minted a domain
enum for a concept another context owns and expresses differently, and the spec's `CheckoutState` record
does not include the field at all (SIGN-19).

Two of the three copies have to go. The vocabulary belongs to Catalog, on the same reasoning as the
2026-09-04 `Capability` ruling.

---

### SIGN-4 · Medium · `MediaProfileSummary.Capabilities` is `IList<string>`

```csharp
public sealed record MediaProfileSummary(MediaProfileId MediaProfileId, IList<string> Capabilities);
```

The spec says `IReadOnlySet<string>`, and the spec is right. This is an ACL boundary handing out a mutable
collection, and the only operation performed on it — `Capabilities.Contains("Signing")` — is O(n) on a
list. Purely cosmetic today; free to fix.

---

### SIGN-5 · Medium · A projection schema is registered for a table nothing writes

`AddSharedInfrastructure` registers **two** schemas:

```csharp
builder.AddProjectionSchema<SigningSessionDetailReadModel>("media-signing-session-detail", schemaVersion: 1);
builder.AddProjectionSchema<SigningSessionSummaryReadModel>("media-signing-sessions", schemaVersion: 1);
```

`SigningSessionSummaryProjector` does not exist — the same file's `todo` comment says so. So the summary
schema is registered without a writer, inside a method (`AddDocumentSigningReadModelProjectors`) that
**no host calls**, for a module whose events `DomainEventPublishingMiddleware` drops before they reach the
bus. Three layers of dead wiring stacked on each other, and the innermost one is the only one that would
throw a schema mismatch if the outer two were ever fixed in the wrong order.

---

### SIGN-6 · Low · `SigningSessionSummaryReadModel.OwnerId` cannot be populated

```csharp
public sealed record SigningSessionSummaryReadModel(string TenantId, string Id, string MediaItemId, string OwnerId, …);
```

No signing domain event carries an owner. `SigningSessionInitiated` carries `InitiatedBy: MemberId` and
nothing else identity-shaped. A summary projector written against these events would have no value to put
in the field. Same defect in the specified `media-signing-envelope-lookup.OwnerId` (SIGN-23). See SIGN-12
for the design question underneath.

---

### SIGN-7 · Low · The adapter csproj comment names the wrong lookup table — X-11.13 still open

`SagaOrchestrator.DocumentSigning.csproj`:

```xml
<!-- DocumentSigning read model: SigningSessionProjector read models used
     for webhook TenantId resolution via media-signing-sessions lookup table -->
```

Both `.cs` files in the same project say `media-signing-envelope-lookup`, and `SigningSessionProjector` is
not a class — the real one is `SigningSessionDetailProjector`. Recorded as X-11.13 on 2026-08-25;
unchanged. Two wrong names in one four-line comment.

---

### SIGN-8 · Low · `SigningSessionInitiatedHandler` throws where its own doc says return `Failed()`

The class remarks say: *"On failure: return `MessageProcessStatus.Failed()` so the message is retried up
to `maxReceiveCount` before being routed to `media-signing-dlq`."* The body throws
`NotImplementedException`. An unhandled exception out of an `IMessageHandler` is not the same disposition
as `Failed()`, and the saga file's DLQ section (**X-11.6**) records that the existing handler layers
swallow exceptions and ack the message — so a stub that throws is the more dangerous of the two shapes to
leave lying around. Return `Failed()` from the stub.

---

### SIGN-9 · Low · The adapter host registers no command dispatcher

`Function.cs` composes DI with `AddAWSService<IAmazonDynamoDB>()`, `AddDynamoDb()`,
`AddSecuredSigningAdapterServices()` and `AddAWSMessageBus(...)`. Nothing registers `ICommandDispatcher`
or `IApplicationBus`, though `Magiq.Platform.WriteModel.Application` is referenced in the csproj and every
TODO in both handlers ends in "dispatch command X". The first implementation attempt will fail to resolve
at the point it needs to dispatch. Worth a line in the host's own doc comment now.

---

# 2. `documentsigningsession.write-model.md` ↔ the domain code

Twelve findings. This is the file with the largest gap, and the gap is not "unimplemented" — it is that
the events which *do* exist cannot support what the file specifies.

### SIGN-10 · **High** · `SigningCompleted` carries no `CompletionToken` — four spec assertions rest on it

`CompletionToken` appears in six places across the spec:

| Where | What it says |
|---|---|
| write-model § Invariants | `` `CompletionToken` must be valid `` → `InvalidCompletionToken` |
| write-model § Methods | `RecordSigningCompleted(completionToken, now)` — "Validates token" |
| write-model § Commands | `RecordSigningCompletedCommand(SigningSessionId, CompletionToken)` |
| write-model § Domain Events | `SigningCompleted` key payload: `CompletionToken`, `CompletedAt` |
| api.md | `POST /v1/sessions/{sessionId}/completed` → `{ "completionToken": "tok_..." }` |
| scenarios DS-1 § Key invariants | "`CompletionToken` is validated aggregate-side in `RecordSigningCompleted`" |
| glossary.md:44 | "A token validated by the `RecordSigningCompleted` aggregate guard" |

The event as built:

```csharp
public sealed record SigningCompleted(
    TenantId TenantId, SigningSessionId SigningSessionId, DateTimeOffset OccurredAt) : DomainEvent, ISigningDomainEvent;
```

No token. **Zero occurrences of `CompletionToken` in either repo's `.cs` files.** So the invariant guards a
value nothing can supply and nothing can persist.

**This needs a decision, not a correction** (see § 8). Either the token is a *transport* concern — the
adapter proves the webhook is authentic via HMAC, and a second token inside the domain is redundant — in
which case it comes out of the aggregate spec, the command, the API body, the error catalog and the
glossary in one pass; or it is a genuine domain value, in which case the event gains the field. The HMAC
path already exists in the design and does the same job, which argues for the first.

---

### SIGN-11 · **High** · Six of the nine documented event payloads have wrong field names

Checked record by record against `DocumentSigning.Domain/Aggregates/Events/`:

| Event | Spec § Domain Events | Code | Verdict |
|---|---|---|---|
| `SigningSessionInitiated` | `TenantId`, `SigningSessionId`, `MediaItemId`, **`OwnerId`**, `InitiatedBy: UserId`, **`InitialSigners[]`**, `InitiatedAt` | `TenantId`, `SigningSessionId`, `MediaItemId`, `InitiatedBy: MemberId`, `Signers`, `InitiatedAt` | ✗ no `OwnerId`; `InitialSigners`→`Signers`; `UserId`→`MemberId` |
| `SigningEnvelopeCreated` | `EnvelopeId`, **`CreatedAt`** | `EnvelopeId`, `OccurredAt` | ✗ |
| `SigningEnvelopeSent` | **`SentAt`** | `OccurredAt` | ✗ |
| `SignerCompleted` | `SignerEmail`, `CompletedAt` | `SignerEmail`, `CompletedAt` | ✓ |
| `SigningCompleted` | **`CompletionToken`**, **`CompletedAt`** | *(none)*, `OccurredAt` | ✗ — see SIGN-10 |
| `SignedAssetRecorded` | **`AssetId`** | `SignedAssetId: string` | ✗ name and type |
| `SigningEnvelopeVoided` | **`Reason`**, `VoidedAt` | `VoidReason`, `VoidedAt` | ✗ |
| `SigningSessionCancelled` | **`CancelledBy`**, **`Reason`**, `CancelledAt` | *(none)*, `CancellationReason`, `CancelledAt` | ✗ — no `CancelledBy` |
| `SigningSessionTimedOut` | `TimedOutAt` | `TimedOutAt` | ✓ |

`SigningSessionCancelled` losing `CancelledBy` matters beyond naming: § Methods specifies
`CancelSession(cancelledBy, reason, now)` and api.md's authorization row is
`caller.owner_id == session.OwnerId`. Neither the actor who cancelled nor the owner survives into the event
stream, so a cancellation is unattributable after the fact — in a module built for regulated records.

**These nine records are the one part of the module that is complete and well-formed.** The spec table
should be rewritten to them, not the reverse — except where an omission is substantive (`CancelledBy`,
`OwnerId`, `CompletionToken`), which is § 8.

---

### SIGN-12 · **High** · `OwnerId` does not exist anywhere in DocumentSigning, and the authorization model needs it

`OwnerId` appears in the write-model § Properties table, the `Initiate(...)` factory signature,
`InitiateSigningSessionCommand`, the `SigningSessionInitiated` payload, **both** read-model record shapes,
the `media-signing-envelope-lookup` field table, the api.md `GET` response body, and three of the five
rows in api.md § Authorization:

```
| `POST /v1/sessions/{id}/cancel` | `caller.owner_id == session.OwnerId` + `Status ∈ {…}` |
| Read endpoints                  | `caller.owner_id == session.OwnerId`                |
```

In code there is exactly one identity on a signing session: `InitiatedBy: MemberId`, set on
`SigningSessionInitiated` and projected onto `SigningSessionDetailReadModel`. The detail read model has
**no owner field at all**. So the entire read-side and cancel-side authorization model, as specified, has
nothing to evaluate against.

Two coherent resolutions, and they are not equivalent — a signing session initiated by a delegate on an
owner's behalf is a real scenario in this domain:

- **Collapse to `InitiatedBy`.** Authorization becomes `caller.MemberId == session.InitiatedBy`. Cheapest;
  matches the events as built; loses the delegate case.
- **Add `OwnerId` to `SigningSessionInitiated`.** Matches the spec and Catalog's `MediaItem.OwnerId`
  precedent; requires the event to change, which is free today and expensive later.

Pick one before anything constructs these events. § 8.

---

### SIGN-13 · **High** · `UserId` is not a type in either repository

The spec uses `UserId` for `InitiatedBy` in § Properties, in the `Initiate(...)` signature, in the
`CheckoutState` record, and in the `media-items` reference-model field table. **`UserId` has zero
declarations across `magiq-media/src` and `aspnetcore-platform/src`.**

The actor type in this solution is `MemberId`:

- `MediaItem.CheckIn(MemberId actor, DateTimeOffset checkedInAt)`, `AbandonCheckout(MemberId actor, …)`,
  `ForceReleaseCheckout(MemberId releasedBy, …)`, `RenewCheckout(MemberId actor, …)`
- `EditSessionClosed(… MemberId? ClosedBy …)`
- DocumentSigning's own `SigningSessionInitiated(… MemberId InitiatedBy …)` and
  `CheckoutState(… MemberId? CheckedOutBy …)`

Global replace `UserId` → `MemberId` throughout the DocumentSigning tree.

---

### SIGN-14 · **High** · The four Catalog checkout events named throughout this spec do not exist

`MediaItemCheckedOut`, `MediaItemCheckedIn`, `MediaItemCheckoutAbandoned` and
`MediaItemCheckoutForceReleased` appear in write-model § Reference Models and in all three scenarios
(steps and mermaid). Catalog's `Aggregates/MediaItems/Events/` contains none of them. The real family is:

| Real event | Carries |
|---|---|
| `EditSessionOpened` | checkout begins |
| `EditSessionClosed` | `EditSessionCloseReason Reason`, `MemberId? ClosedBy`, `MediaItemStatus RestoredStatus` |
| `EditSessionRenewed` | lease extension |
| `EditSessionReopened` | — |

**It is one event with a six-member discriminator, not four events**: `EditSessionCloseReason` =
`CheckedIn(0) · Submitted(1) · Abandoned(2) · ForceReleased(3) · Expired(4) · Superseded(5)`. The
*commands* the spec names (`CheckOutMediaItem`, `CheckInMediaItem`, `AbandonCheckout`,
`ForceReleaseCheckout`, `ExpireCheckout`, `RenewCheckout`) all exist under exactly those names — it is only
the event vocabulary that is invented.

This has a consequence beyond naming: any DocumentSigning-side projector subscribing to "checkout ended"
must switch on `EditSessionClosed.Reason`, not select among four event types. The § Reference Models
subscription table (SIGN-16) is built on the wrong shape.

---

### SIGN-15 · **High** · `MediaItemSigningSessionLinked`/`Unlinked` → the real names are `SigningSessionLinked`/`Unlinked`

Catalog's events are `SigningSessionLinked(TenantId, MediaItemId, SigningSessionId, LinkedAt)` and
`SigningSessionUnlinked(TenantId, MediaItemId, SigningSessionId, UnlinkedAt)`. The `MediaItem`-prefixed
names appear in write-model § Reference Models, § Published Integration Events, and every one of the three
scenarios' steps and mermaid diagrams — **eleven occurrences**.

`sagas/documentsigningsaga.md` already flags this (*"The spec has called these
`MediaItemSigningSessionLinked`/`Unlinked`. Wrong names."*). The flag was never propagated to the files
that carry the wrong names.

---

### SIGN-16 · **High** · § Reference Models contradicts § Consumed Integration Events — same file, 60 lines apart

§ Consumed Integration Events:

> The `IMediaItemQueryService` and `IMediaProfileQueryService` reference models … are backed by **direct
> DynamoDB queries** on Catalog's `media-items` and `media-profiles` tables (ACL pattern) — **no local
> projection or event subscription is maintained.**

§ Reference Models, for both of those same two tables:

> **Subscribed integration events (projector owned by DocumentSigning, consuming Catalog via
> `media-projector` SQS queue):**

followed by full event→write tables for five MediaItem events and two MediaProfile events.

These are opposite architectures: one context reading another's table directly, versus one context
maintaining its own projection off the other's event stream. Neither is built — both interfaces have no
implementation anywhere — so the file is currently specifying two designs and mandating neither.

**The ACL/direct-query half is the one to keep**, on three grounds:

1. It is what the interface signatures already assume: `GetCheckoutStateAsync(tenantId, mediaItemId, ct)`
   is a point lookup, not a projection reader.
2. **The data is already there.** `MediaItemDetailReadModel` carries `MediaProfileId`, `CheckedOutBy`,
   `CheckoutStatus` and `ActiveSigningSessionId` — every field `CheckoutState` needs — so a direct read is
   implementable today without a single new projector.
3. The projector half is built on event names that do not exist (SIGN-14, SIGN-15), so it has never been
   checked against Catalog at all.

Delete the two subscription tables; keep the field tables, retitled as the read shape.

---

### SIGN-17 · Medium · Value-object names: `SignerSpec`/`Signer`/`SignerStatus` vs `SignerInfo`/`SignerDto`/`SignatureStatus`

| Spec § Value Objects | Code | Where |
|---|---|---|
| `SignerSpec` `{ Email, RoutingOrder }` | `SignerInfo(string Email, int RoutingOrder)` | `Domain/Aggregates/Events/` |
| `Signer` `{ Email, RoutingOrder, Status }` | `SignerDto(string Email, int RoutingOrder, SignatureStatus Status)` | `ReadModel/ReadModels/DocumentSigningSessions/` |
| `SignerStatus` `Pending \| Completed` | `SignatureStatus { Pending, Completed }` | `Domain/ValueObjects/` |
| `SigningSessionStatus` (8 members) | `SigningSessionStatus` (8 members, same order) | `Domain/ValueObjects/` ✓ |

The concepts match one-for-one; only the names differ, and the code's names are the ones in the solution.
Note the split the spec does not capture: `SignerInfo` is the *event* shape (write side, no status) and
`SignerDto` is the *read-model* shape (with status) — which is a sound separation worth documenting rather
than renaming away.

---

### SIGN-18 · Low · Four value objects that exist are absent from the spec's table

`MediaItemId`, `MediaProfileId`, `MemberId` and `CheckoutStatus` are all declared in
`DocumentSigning.Domain/ValueObjects/` and none appears in § Value Objects. `CheckoutStatus` in particular
should not be silently added — see SIGN-3; it should be removed from the code instead.

---

### SIGN-19 · Medium · `CheckoutState` has a field the spec omits and an actor type the spec gets wrong

```csharp
// code
sealed record CheckoutState(MediaItemId, MediaProfileId, CheckoutStatus CheckoutStatus, MemberId? CheckedOutBy, SigningSessionId? ActiveSigningSessionId);
// spec
sealed record CheckoutState(MediaItemId, MediaProfileId, UserId? CheckedOutBy, SigningSessionId? ActiveSigningSessionId);
```

Two differences: the extra `CheckoutStatus` (SIGN-3) and `UserId` (SIGN-13). The spec's own commentary —
*"`CheckedOutBy` must equal `command.InitiatedBy`, null means not checked out at all"* — makes
`CheckoutStatus` redundant by construction, which is an argument for deleting the field rather than
documenting it.

---

### SIGN-20 · Medium · The `Signing` capability row understates what shipped, and the duplicate registry is still live

§ Invariants row 3 reads: *"⚠ **design only; nothing reads `Signing` today** (2026-08-25, W23)"*. That is
true about *reads* and misleading about existence. `Catalog.Domain/Aggregates/MediaProfiles/ValueObjects/Capability.cs`
ships nine members, and the ninth is:

```csharp
/// <summary>
/// Formal document signing lifecycle is available; required for `DocumentSigningSession` initiation
/// </summary>
Signing
```

The file's own 2026-09-02 correction note already establishes this against the stale source comment
below it; the invariant row above was not updated to match. Reword to *"the member ships; no code reads
it — the handler that would is unbuilt."*

Separately, and still open against the 2026-09-04 single-source ruling:
`Metadata.WriteModel.Infrastructure/Services/CapabilityRegistry.cs:339` still declares
`public const string Signing = "Signing";`. That is the competing copy the ruling says goes away with the
RecordType field-contributor removal. Not DocumentSigning's to fix, but it is the second copy of
DocumentSigning's own gate value.

---

### SIGN-21 · Low · The `signing_` stream prefix has no source in code

The write-model header declares `_Stream prefix: `signing_`_`. No stream-prefix concept exists in either
repo. The convention actually in use is `[AggregateType("media.<name>")]` on the aggregate class — and
since no DocumentSigning aggregate exists, no such attribute exists either. Same finding as PROC-8 for
Processing; the header line is boilerplate carried across context files.

---

# 3. `documentsigningsession.read-model.md` ↔ the read-model code

Four findings. This is the most accurate of the five design files — the three-table split, the reasoning
for isolating `media-signing-envelope-lookup`, and the `SigningSessionDetailProjector` description are all
correct. The drift is in the record shapes and in one status marker outside the file.

### SIGN-22 · Medium · Both documented record shapes differ from the code

**Summary:**

| Spec | Code |
|---|---|
| `string SessionId` | `string Id` |
| `string Status` | `SigningSessionStatus Status` (enum) |
| `string OwnerId` | `string OwnerId` — present, unpopulable (SIGN-6) |

**Detail:**

| Spec | Code |
|---|---|
| `string SigningSessionId` | `string Id` |
| `string OwnerId` | **absent** |
| `string Status` | `SigningSessionStatus Status` (enum) |
| `SignerDto(…, string Status)` | `SignerDto(…, SignatureStatus Status)` (enum) |

The `Id` naming is not arbitrary — `ProjectionKey<T>(tenantId, signingSessionId)` and the platform's
`IReadModel` convention are what produce it, and Catalog's read models follow the same shape. The spec's
`SessionId`/`SigningSessionId` should move.

Typing `Status` as the enum rather than `string` is also the code being right: the spec's own § Embedded
Types block then declares both enums immediately below the records that use `string`, which is
self-contradicting within twenty lines.

---

### SIGN-23 · Medium · `media-signing-envelope-lookup.OwnerId` cannot be written by the projector that is specified to write it

The table's field list includes `OwnerId`, and the section specifies the row is *"Write-once on
`SigningEnvelopeCreated`"*. `SigningEnvelopeCreated(TenantId, SigningSessionId, EnvelopeId, OccurredAt)`
carries no owner and no initiator. A `SigningEnvelopeLookupProjector` handling only that event has nothing
to put in the column.

Either drop `OwnerId` from the lookup table — the webhook path needs `TenantId` and `SigningSessionId`
and nothing else, which is the section's own stated purpose — or resolve SIGN-12 in a way that puts an
identity on the creation event and have the lookup projector handle `SigningSessionInitiated` too, which
breaks its "single handler" property. **Dropping the column is the better answer**; a security-path lookup
should carry the minimum.

---

### SIGN-24 · Low · § Consistency undercounts both the tables and the reasons

The section says *"the two tables are absent from `projection-tables.manifest.json` and never
provisioned."* Verified: **three** tables are specified (`media-signing-session-detail`,
`media-signing-sessions`, `media-signing-envelope-lookup`) and all three are absent from the manifest —
which contains 24 `tableId` entries, none of them signing — and absent from
`cdk-magiq-media/lib/constructs/dynamodb/read-models.ts`.

The section names three reasons the model is unpopulated. There are four; the missing one is that
`SigningSessionSummaryProjector` and `SigningEnvelopeLookupProjector` do not exist at all, so two of the
three tables would have no writer even if everything else were wired. Otherwise this section is the most
accurate paragraph in the tree and should be the model for the rest.

---

### SIGN-25 · Medium · `operations.md` lists `SigningSessionDetailProjector` without the deferred marker

`docs/spec/shared/operations.md`, projector inventory:

```
| `SigningSessionDetailProjector`  | DocumentSigning | media-signing-session-detail  |
| `SigningEnvelopeLookupProjector` | DocumentSigning | media-signing-envelope-lookup | 🔴 Deferred — webhook TenantId lookup
| `SigningSessionSummaryProjector` | DocumentSigning | media-signing-sessions        | 🔴 Deferred — DocumentSigning module not yet complete
```

The first row carries no status against two neighbours that do, which reads as "this one runs". It does
not: `AddDocumentSigningReadModelProjectors()` has **no caller** — `Projectors.ReadModel/ServiceCollectionExtensions.cs`
registers AssetManagement, Catalog, ChangeRequests, Metadata, Processing and Registration and stops. The
class being complete is not the same as it being live. Add a marker distinguishing *"exists, registered
nowhere"* from *"does not exist"* — they are different states and this module has both.

---

# 4. `documentsigningsession.api.md` ↔ the served surface

Five findings. The file's own recovered-tail note (2026-08-25) already says the routes are not served;
what follows is the scope of that, plus the internal inconsistencies the note did not cover.

### SIGN-26 · **High** · None of the eleven routes is served, and nothing would route to them if they were

Confirmed on three independent axes:

1. **No `.Endpoints` project.** `Magiq.Media.sln` lists five DocumentSigning projects: `Contracts`,
   `Domain`, `WriteModel`, `ReadModel`, `ReadModel.Infrastructure`. Every other module has
   `*.WriteModel.Endpoints` and/or `*.ReadModel.Endpoints`. DocumentSigning has neither, so `Api` — which
   references every `*.Endpoints` project and applies no assembly filter — has nothing to discover.
2. **No API Gateway route.** `cdk-magiq-media/lib/magiq-media-stack.ts` declares Lambdas for
   `ProcessingWorker`, `SagaOrchestrator`, `TimeoutScanner` and the API hosts. **There is no
   `SagaOrchestrator.DocumentSigning` Lambda**, so the `WebhookHandler` entry point in `Function.cs` has
   no trigger and no route.
3. **No commands to dispatch.** Zero of the nine command types in § Commands exist (SIGN-33).

The file's recovered-tail note says this for the traceability table. It applies to the whole file.

---

### SIGN-27 · Medium · Three incompatible session-route shapes across three files

| Source | Initiate | Get by id |
|---|---|---|
| `api.md` § Route Structure | `POST /v1/items/{itemId}/signing-sessions` | `GET /v1/sessions/{sessionId}` |
| `api.md` § Traceability (last row) | — | `GET /v1/signing/sessions/{id}` |
| `context-overview.md` · `scenarios.md` | `POST /media-items/{id}/media-signing-sessions` | `GET /media-signing-sessions/{sessionId}` |

Three prefixes (`/v1/items`, `/v1/sessions`, `/v1/signing/sessions`, `/media-items`,
`/media-signing-sessions`), and the api.md file disagrees with itself between its § Route Structure and
its own traceability table. Nothing arbitrates, because nothing is served.

Note also that `GET /v1/sessions/{sessionId}` is an unscoped resource name for a system whose other read
routes are all under a resource — `/v1/sessions` colliding with any future non-signing session concept is
avoidable now and not later.

---

### SIGN-28 · Medium · Three incompatible webhook routes

| Source | Route |
|---|---|
| `context-overview.md` (×3 occurrences) | `POST /integrations/secured-signing/webhook` |
| `api.md` | `POST /v1/integrations/secured-signing/webhooks` — annotated *"(pluralised, /v1/ prefix)"* |
| `scenarios.md` DS-1 | `POST /webhooks/secured-signing` |

api.md's parenthetical shows someone noticed the divergence and recorded it as a property of the route
rather than fixing the other two files. Pick one; the api.md form is the one that matches
`api-conventions.md`.

---

### SIGN-29 · Medium · Initiate returns `202` in api.md and `201` in scenarios

api.md specifies **`202 Accepted`** with a `Location` header and `{"id", "expectedStatus":
"EnvelopeCreated"}`. scenarios.md DS-1 says *"Capture `sessionId` from the … response (`201 Created` body)"*,
and its mermaid has `CH-->>Client: 201`.

`202` is right for this shape — the envelope is created asynchronously by the adapter and the resource is
not in its expected state when the call returns — but the Postman polling table in DS-1 is written against
the `201`, so fixing one without the other leaves the test guidance wrong.

---

### SIGN-30 · Medium · The traceability table invents a GSI the read-model spec explicitly rejects, and drops a projector

Two problems in one table:

- Row `POST /envelope/created` → *"`media-signing-session-detail` → EnvelopeId, **EnvelopeIdIndex**"*.
  `read-model.md` rules this out in terms: *"a GSI on the summary table would be eventually consistent and
  unsuitable for a security decision"* — which is why `media-signing-envelope-lookup` exists as a separate
  table. No `EnvelopeIdIndex` exists in code, in the manifest, or in CDK.
- **Every** projection cell names `media-signing-session-detail` only. `read-model.md` specifies that
  `SigningSessionSummaryProjector` maintains `media-signing-sessions` off the same nine events. The table
  understates the fan-out by one projector and one table throughout.

---

# 5. Spec ↔ spec — contradictions with no code to arbitrate

Six findings where two spec files disagree and nothing built can settle it. These are the cheapest to fix
and the most expensive to leave: whoever picks the module up will implement whichever file they opened.

### SIGN-31 · Medium · Which table resolves webhook `TenantId` — two answers, in two files, plus a third in the csproj

| Source | Answer |
|---|---|
| `read-model.md`, `context-overview.md` | `media-signing-envelope-lookup`, PK = `EnvelopeId`, strongly-consistent `GetItem` |
| `write-model.md` § `IExecutionContext` Source by Entry-Point | `` `media-signing-sessions[EnvelopeId].TenantId` `` |
| `write-model.md` § Consumed Integration Events | `` `media-signing-sessions[EnvelopeId]` lookup table `` |
| `scenarios.md` DS-2 mermaid note | *"Resolve TenantId from media-signing-sessions[EnvelopeId]"* |
| `SagaOrchestrator.DocumentSigning.csproj` comment | `media-signing-sessions` |
| `SecuredSigningWebhookHandler.cs` · `Function.cs` · `SecuredSigningRegistrations.cs` | `media-signing-envelope-lookup` |

Four votes each way. `media-signing-sessions` is keyed `TENANT#{TenantId}#{SigningSessionId}` — it
**cannot** be queried by `EnvelopeId` without exactly the GSI `read-model.md` rejects, so the four
`media-signing-sessions` references are not just a naming variant, they specify an impossible lookup.
`media-signing-envelope-lookup` wins on the merits and on the code comments. Recorded as X-11.13; the
spec-side half of it has never been swept.

---

### SIGN-32 · Medium · Three names for the queue that feeds the adapter

| Source | Queue |
|---|---|
| `context-overview.md` § SecuredSigning Adapter | `signing-requests` |
| `event-store-and-messaging.md` (fan-out table + tree) · `Function.cs` doc comment | `media-signing`, DLQ `media-signing-dlq`, 300s visibility, maxReceive 3 |
| `system-architecture.md` | `media-signing` **and** a separate `media-document-signing` on the integration-event side |
| `cdk-magiq-media/lib/constructs/messaging/sqs-queues.ts:76` | `media-document-signing` — **as a comment**: *"DocumentSigningSaga integration-event path; add when feature is ready"* |

None is provisioned. `media-signing` is the one with a full specification behind it (visibility timeout,
redrive policy, retention) and the one the host's own doc comment uses; `signing-requests` appears once
and should go. Whether `media-document-signing` is a second queue or the same one renamed is unresolved —
`system-architecture.md` treats them as distinct, X-1.2 and X-1.5 separately.

---

### SIGN-33 · Medium · Four adapter command names in code comments, four in the spec, one overlap, zero exist

| Provider callback | `SecuredSigningWebhookHandler` remarks | `write-model.md` § Commands |
|---|---|---|
| `EnvelopeSent` | `SigningEnvelopeSentCommand` | `RecordEnvelopeSentCommand` |
| `SignerCompleted` | `RecordSignerCompletedCommand` | `RecordSignerCompletedCommand` ✓ |
| `EnvelopeCompleted` | `CompleteSigningSessionCommand` | `RecordSigningCompletedCommand` |
| `EnvelopeVoided` | `VoidSigningEnvelopeCommand` | `RecordEnvelopeVoidedCommand` |

Plus `LinkSigningSessionCommand` in `SigningSessionInitiatedHandler`, which is Catalog's and does exist.
**None of the eight DocumentSigning command types exists in the repo.** The `Record*` family is the
consistent one and matches the event names; adopt it and correct the two host doc comments.

---

### SIGN-34 · Medium · Adapter or saga — two components claim `LinkSigningSession`

`SigningSessionInitiatedHandler` TODO, step 3:

```
// 3. Dispatch LinkSigningSessionCommand(tenantId, signingSessionId, envelopeId).
```

The spec says the **saga** does this, on `SigningEnvelopeCreated`: scenarios DS-1 step 4 (*"Saga dispatches
`LinkSigningSession(mediaItemId, sessionId)`"*), context-overview § Outbound (*"`SigningEnvelopeCreated` |
`DocumentSigningSaga` → dispatch `LinkSigningSession`"*), write-model § Saga Involved, and
`authorization-matrix.md:252` (*"`LinkSigningSession` | SagaOrchestrator.DocumentSigning **only**"*).

Two problems, one already recorded and one not:

- **Recorded (X-11.14):** the TODO's third argument passes an `envelopeId` into a parameter typed
  `SigningSessionId`. Noted at the `LinkSigningSessionHandler` site; not noted here, and this is where the
  wrong call would actually be written.
- **Not recorded:** the adapter is an anti-corruption layer, not a saga — `documentsigningsaga.md` makes
  that case well. An ACL dispatching a cross-context state-change command is the wrong seam. If the saga
  never gets built, this TODO becomes the de-facto design by default, which is the outcome to avoid.

Also note `authorization-matrix.md:254`: `UnlinkSigningSession` | **nothing — dead**. Per the
`LinkSigningSessionHandler` warning, **linking without unlinking makes a `MediaItem` permanently
un-checkoutable and un-publishable with no operator command to clear it.** Whichever component wins, it
ships both paths in the same change.

---

### SIGN-35 · Low · DS-1's test affordances do not exist

Three cited in the "Automated signing simulation options" block:

- `SECURED_SIGNING_TEST_MODE=true` — no occurrence in `src/`, in any `appsettings*.json`, or in CDK.
- `POST /test/media-sagas/{sagaId}/expire` — no such route; no test-only endpoint exists in any host.
- A SecuredSigning sandbox account — no `ISecuredSigningApiClient`, no base URL config, no secret in
  `app-secrets.ts`.

Written as instructions to a future tester in the present tense. Reframe as "would need to exist", or move
to the saga file's open-questions table where the same class of unbuilt-affordance is handled honestly.

---

### SIGN-36 · Low · DS-3's scanner name, and the thing behind the name

DS-3 calls it `SagaTimeoutScanner`. The project is `src/hosts/TimeoutScanner`; CDK registers it as
`'TimeoutScanner'` and exposes its metrics under the namespace `'SagaTimeoutScanner'` — so the name is not
invented, it is one of two, used inconsistently.

The substantive point is the one `documentsigningsaga.md` already makes and DS-3 does not:
`AssetIngestionTimeoutScanner` hard-codes `SagaType = "ASSET_INGESTION"` into every GSI query. **A signing
timeout is new code, not a config entry**, and DS-3 reads as though the existing scanner would simply pick
the saga up. Cross-reference the saga file's § Timeouts.

---

# 6. Cross-cutting — shared spec files

Four findings outside the DocumentSigning folder that this context depends on.

### SIGN-37 · **High** · `error-catalog.md` has no DocumentSigning section — but says it does

The catalog's preamble states:

> **Still aspirational:** every code in the **Processing and DocumentSigning sections**, and any row
> marked ⬜ below. … Those two modules each need the same one-line change to their endpoint base classes
> that Catalog has.

The file's headings are: Common · AssetManagement · Catalog—Collections · Catalog—Folders ·
Catalog—MediaItems · Catalog—MediaProfiles · Metadata—RecordTypes · ChangeRequests · Registration ·
Processing · Batch Operations. **There is no DocumentSigning section.** The preamble's remedy ("a one-line
change to their endpoint base classes") is also not applicable — DocumentSigning has no endpoint base
class because it has no `.Endpoints` project.

Draft section in **Appendix A.1**.

---

### SIGN-38 · **High** · Six error codes exist only inside DocumentSigning's own spec files

Grepped across `docs/spec/` and both repos' `.cs`:

| Code | In error-catalog? | In code? | Only appearance |
|---|---|---|---|
| `SigningSessionInProgress` | ✗ | ✗ | DS write-model (×3); listed at `mediaitem.write-model.md:100` as *"does not exist anywhere in the codebase"* |
| `CapabilityNotEnabled` | ✗ | ✗ | DS write-model (×3) |
| `SigningSessionNotCancellable` | ✗ | ✗ | DS write-model (×1) |
| `InvalidCompletionToken` | ✗ | ✗ | DS write-model (×2) — and see SIGN-10 |
| `SignersNotAllCompleted` | ✗ | ✗ | DS write-model (×1) |
| `HmacSignatureInvalid` | ✗ | ✗ | DS api.md (×1, in a response example) |

`MediaItemNotCheckedOut` **is** in the catalog, at 422 — but with a *different meaning*: Catalog defines it
as *"a session operation (`CheckIn`, `Abandon`, `Renew`, `ForceRelease`) was called on an item with no open
session."* DocumentSigning uses it for *"the caller is not the member holding the checkout."* Same code,
two conditions, two owners. That is worse than a missing code, because a client branching on it cannot
tell which happened.

**Naming, separately:** `CapabilityNotEnabled` breaks the one precedent in the tree. Registration's
equivalent gate is `RegistrationCapabilityNotEnabled` — module-prefixed, precisely because
`InvalidRegistrationItem` is its inverse and a bare name would be ambiguous. `SigningCapabilityNotEnabled`
is the consistent form.

---

### SIGN-39 · Low · `glossary.md` marks three built things as "Not built"

| Entry | Says | Actually |
|---|---|---|
| **Signer** | *"⚠ Not built"* | Built as `SignerDto(Email, RoutingOrder, Status)` — exactly the documented shape |
| **SignerSpec** | *"⚠ Not built"* | Built as `SignerInfo(Email, RoutingOrder)` — exactly the documented shape |
| **SigningSessionStatus** | *"⚠ Not built"* | Built, eight members, same names and same order |

Correct in the other direction: **DocumentSigningSession**, **DocumentSigningSaga** and **CompletionToken**
are all accurately marked. **EnvelopeId**'s *"⚠ Which table performs that lookup is contested"* is the
right call and is SIGN-31 — the glossary is the only file that admits the contest.

---

### SIGN-40 · Low · `business-scenarios.md` is a stale index

`_Last reviewed: 2026-07-07_` — two months before the corrections that landed in the file it indexes
(DS-2's 2026-08-25 W11 note; the scenarios file's own 2026-08-24 sweep). The index itself is accurate;
the date is misleading and the file is otherwise a pure redirect. Either restamp it or fold it into
`context-overview.md` — it carries 28 lines and one table.

---

# 7. Specified but absent — the build inventory

Not findings; the checklist of what the spec names and the repo does not contain. Verified by name against
`src/`, `Magiq.Media.sln`, `projection-tables.manifest.json` and `cdk-magiq-media/lib/`.

| Layer | Specified | Present |
|---|---|---|
| **Aggregate** | `DocumentSigningSession` (event-sourced root, 9 methods, 6 invariants) | ✗ — `Aggregates/` holds `Events/` and nothing else |
| **Commands** | 9: `InitiateSigningSession`, `RecordEnvelopeCreated`, `RecordEnvelopeSent`, `RecordSignerCompleted`, `RecordSigningCompleted`, `RecordSignedAsset`, `RecordEnvelopeVoided`, `CancelSigningSession`, `ExpireSigningSession` | ✗ — 0 of 9 |
| **Command handlers** | 9, plus 5 handler-side preconditions | ✗ — 0 |
| **Domain events** | 9 | ✅ **9 of 9** — the one complete layer |
| **Value objects** | `SigningSessionId`, `SignerSpec`, `Signer`, `SignerStatus`, `SigningSessionStatus` | ⚠ 5 of 5 by concept, 2 of 5 by name (SIGN-17), 0 of 4 ids as `Id<T>` (SIGN-2) |
| **Endpoints project** | 11 routes | ✗ — no `.Endpoints` project in the solution |
| **Queries** | `GetSigningSessionById`, `ListSigningSessionsByMediaItem`, `GetSigningSessionByEnvelopeId` | ✗ — `AddDocumentSigningReadModelQueries` has a `todo` and registers only the generic reader |
| **Read models** | 2 records | ✅ both — shapes drift (SIGN-22) |
| **Projectors** | `SigningSessionDetailProjector`, `SigningSessionSummaryProjector`, `SigningEnvelopeLookupProjector` | ⚠ 1 of 3 — complete, registered by no host |
| **Projection schemas** | 3 tables | ⚠ 2 registered in code, 1 of those has no writer (SIGN-5) |
| **DynamoDB tables** | `media-signing-session-detail`, `media-signing-sessions`, `media-signing-envelope-lookup` | ✗ — 0 in the manifest (24 entries, none signing), 0 in CDK `read-models.ts` |
| **Query services** | `IMediaItemQueryService`, `IMediaProfileQueryService` | ⚠ interfaces + 2 DTOs; **no implementation anywhere** |
| **Integration events** | none published, none consumed | ✅ correct — `DocumentSigning.Contracts` is csproj-only, and `WriteModel` has two empty `IntegrationEvents/` folders |
| **Event publishing** | signing events on `media-domain-events` | ✗ — `DomainEventPublishingMiddleware._supportedInterfaces` omits `ISigningDomainEvent` (explicit `todo`) |
| **Saga** | `DocumentSigningSaga` + state + status set | ✗ — see `documentsigningsaga.md`, which covers this properly |
| **Adapter host** | SecuredSigning ACL | ⚠ project exists, builds, ships an image every commit; both handlers are stubs (`NotImplementedException`, HTTP 501); **no Lambda in CDK** |
| **API client** | `ISecuredSigningApiClient` | ✗ — a commented-out `AddHttpClient` line |
| **Webhook** | HMAC-validated route + secret | ✗ — no route, no HMAC code, no secret in `app-secrets.ts` |
| **Queue** | `media-signing` + `media-signing-dlq` | ✗ — a comment in `sqs-queues.ts` naming a third variant |
| **Timeout scanner** | `DocumentSigningTimeoutScanner` + options + config section | ✗ — none; and the existing scanner hard-codes `ASSET_INGESTION` |
| **Catalog side** | `LinkSigningSession`, `UnlinkSigningSession`, `ActiveSigningSessionId`, `Capability.Signing` | ✅ **all present, registered, tested — and dispatched by nothing** (X-11.14) |

---

# 8. Needs a call — five decisions the spec cannot make for itself

These are not corrections. Each changes what gets built, and four of the five are cheapest to settle
*before* anything constructs the nine events.

| # | Decision | Why it can't wait | My read |
|---|---|---|---|
| 1 | **`CompletionToken` — domain value or transport artefact?** (SIGN-10) | It is an invariant with no field. If it stays, `SigningCompleted` gains a member; events are cheap to change now and versioned forever afterwards | **Drop it.** HMAC on the webhook already authenticates the callback; a second token inside the aggregate duplicates that check at a layer that cannot see the transport |
| 2 | **`OwnerId` or `InitiatedBy`?** (SIGN-12) | The whole read-side and cancel-side authorization model depends on the answer, and neither read model can serve the specified rule today | **Add `OwnerId` to `SigningSessionInitiated`.** A delegate initiating on an owner's behalf is a real case in regulated records, and collapsing to `InitiatedBy` forecloses it. Also unblocks SIGN-6 |
| 3 | **ACL direct-query or DocumentSigning-owned projectors?** (SIGN-16) | One file mandates both. Whoever implements picks by which section they read | **Direct query.** The interface signatures are point lookups, `MediaItemDetailReadModel` already carries all four fields, and the projector design is written against event names that don't exist |
| 4 | **Does `DocumentSigningSession` become a real aggregate?** | Open question 6 in `documentsigningsaga.md`. Everything in § 7 above scales off it — 9 commands and 9 handlers, or none | Out of scope for this report; it is the saga file's question and it is asked well there |
| 5 | **Adapter or saga dispatches `Link`/`UnlinkSigningSession`?** (SIGN-34) | A live TODO in the adapter already assumes "adapter", and it will become the design by default | **Saga**, per `authorization-matrix.md:252`. But **link and unlink ship together whichever way it goes** — the failure mode is a permanently locked `MediaItem` |

One more, smaller: `RoutingOrder` is carried on `SignerInfo` and read by nothing. Sequential vs parallel
signing changes what a timeout measures. `documentsigningsaga.md` open question 3 — noted here only
because the field exists in code, which makes it look decided.

---

# Appendix A — Draft spec text

Ready-to-paste replacements for the sections named. **Each is a single section**, because the repo's
`CLAUDE.md` prohibits regenerating a spec file top-to-bottom in one write — 18 files were truncated that
way, and two tails were never recovered. Paste section by section.

Every draft below assumes decisions 1 and 2 from § 8 (**drop `CompletionToken`; add `OwnerId`**). Where a
draft depends on a decision, the dependency is flagged inline so it can be reversed cheaply.

---

## A.1 · `docs/spec/shared/error-catalog.md` — new section

Insert between `## Processing` and `## Batch Operations`, matching the ✅/⚠/⬜ convention used above it.

```markdown
## DocumentSigning

> **Nothing in this section is raised.** The `DocumentSigningSession` aggregate does not exist, the module
> has no `.Endpoints` project, and no signing command type is declared. Every row is ⚠ — a designed
> refusal with a chosen code, recorded so the code is chosen once. Do not branch on any of them.

| | `errorCode` | HTTP | Condition | Caller Action |
|---|---|---|---|---|
| ⚠ | `MediaItemNotCheckedOutByCaller` | 422 | `InitiateSigningSession` — the item has no open edit session, or the session is held by another member. **Deliberately not `MediaItemNotCheckedOut`**, which Catalog already owns for a different condition (a session operation on an item with no open session). Two owners, one code, is the drift this name avoids | Check the item out, or ask the holder to |
| ⚠ | `SigningSessionInProgress` | 409 | `InitiateSigningSession` — `MediaItem.ActiveSigningSessionId` is non-null. Also named in `mediaitem.write-model.md` as a code that does not exist; this is its intended home | Wait for the active session to reach a terminal state, or cancel it |
| ⚠ | `SigningCapabilityNotEnabled` | 422 | `InitiateSigningSession` — the item's profile does not carry `Capability.Signing`. **Module-prefixed**, matching `RegistrationCapabilityNotEnabled`. The enum member ships; no code reads it yet | Add the capability to the profile, or sign a different item |
| ⚠ | `SigningSessionNotCancellable` | 409 | `CancelSigningSession` on a session outside `Initiated` / `EnvelopeCreated`. Carries root-level `currentStatus` | Inspect `currentStatus`; a terminal session cannot be cancelled — initiate a new one |
| ⚠ | `SignersNotAllCompleted` | 422 | `RecordSigningCompleted` while at least one `Signer.Status` is `Pending` | Do not retry; the provider callback is out of order or a `SignerCompleted` was lost |
| ⚠ | `HmacSignatureInvalid` | 401 | `POST /v1/integrations/secured-signing/webhooks` — `X-SecuredSigning-Signature` absent or not equal to the computed HMAC-SHA256 digest. The only unauthenticated route in the system | Do not retry with the same body; the shared secret is wrong or the payload was altered |
| ⚠ | `EnvelopeNotFound` | 404 | Webhook `TenantId` resolution — `GetItem(PK = EnvelopeId)` on `media-signing-envelope-lookup` returned nothing. **Never surfaced to the provider**: the webhook always answers `200` and the failure goes to the DLQ | — (operator-facing; see the runbook) |

> **`InvalidCompletionToken` is deliberately absent — decided 2026-09-08.** `SigningCompleted` carries no
> token, no `CompletionToken` exists in either repo, and the webhook's HMAC already authenticates the
> callback. The token was specified in six places and implemented in none; it is removed rather than
> re-specified. If a domain-level token is ever wanted, it needs a field on the event first.

> **`SystemActorRequired`, `NotResourceOwner`, `NotFound`, `ConcurrencyConflict`** are the cross-cutting
> codes for the seven system/adapter routes and the two owner-scoped ones. See § Common.
```

---

## A.2 · `documentsigningsession.write-model.md` § Domain Events — replacement

Replaces the table and its `†` footnote. Written to the nine records as they exist, with the two
substantive additions from § 8 marked.

```markdown
## Domain Events

All nine records exist in `DocumentSigning.Domain/Aggregates/Events/`, carry `[DomainEvent(nameof(...))]`,
and implement `ISigningDomainEvent : IDomainEvent, ITenantScoped`. **Nothing emits any of them** — there is
no aggregate — and `DomainEventPublishingMiddleware` excludes `ISigningDomainEvent`, so none reaches SNS.

| Event | Payload (in declaration order) | Status transition |
|---|---|---|
| `SigningSessionInitiated` | `TenantId`†, `SigningSessionId`, `MediaItemId`, `InitiatedBy: MemberId`, `Signers: IReadOnlyList<SignerInfo>`, `InitiatedAt` | → `Initiated` |
| `SigningEnvelopeCreated` | `TenantId`, `SigningSessionId`, `EnvelopeId: string`, `OccurredAt` | → `EnvelopeCreated` |
| `SigningEnvelopeSent` | `TenantId`, `SigningSessionId`, `OccurredAt` | → `EnvelopeSent` |
| `SignerCompleted` | `TenantId`, `SigningSessionId`, `SignerEmail: string`, `CompletedAt` | — (individual signer state) |
| `SigningCompleted` | `TenantId`, `SigningSessionId`, `OccurredAt` | → `Completed` |
| `SignedAssetRecorded` | `TenantId`, `SigningSessionId`, `SignedAssetId: string`, `RecordedAt` | → `SignedAssetRecorded` |
| `SigningEnvelopeVoided` | `TenantId`, `SigningSessionId`, `VoidReason: string`, `VoidedAt` | → `Voided` |
| `SigningSessionCancelled` | `TenantId`, `SigningSessionId`, `CancellationReason: string`, `CancelledAt` | → `Cancelled` |
| `SigningSessionTimedOut` | `TenantId`, `SigningSessionId`, `TimedOutAt` | → `TimedOut` |

† `TenantId` is the **first field** on every event, not only the creation event — the convention this
module already follows correctly.

> **Two fields the design needs and the records do not have** — both cheap now, versioned forever once
> anything emits these events:
>
> 1. **`OwnerId` on `SigningSessionInitiated`.** Every authorization rule in
>    [`documentsigningsession.api.md`](./documentsigningsession.api.md#authorization) is
>    `caller.owner_id == session.OwnerId`, and `InitiatedBy` is not the same thing — a delegate may
>    initiate on an owner's behalf. Without it the read model has no owner and the cancel and read rules
>    cannot be evaluated.
> 2. **`CancelledBy: MemberId` on `SigningSessionCancelled`.** `CancelSession(cancelledBy, …)` takes it and
>    the event drops it, so a cancellation is unattributable in the event stream. Not acceptable in a
>    module built for regulated records.
>
> **`CompletionToken` was removed from this table — decided 2026-09-08.** It appeared in six spec locations
> and no code; `SigningCompleted` has no field for it and the webhook HMAC already authenticates the
> callback. See [`error-catalog.md` § DocumentSigning](../../../../shared/error-catalog.md#documentsigning).
```

---

## A.3 · `documentsigningsession.write-model.md` § Value Objects — replacement

```markdown
## Value Objects

| Value object | Shape | Where | Status |
|---|---|---|---|
| `SigningSessionId` | wraps `string` | `Domain/ValueObjects/` | ⚠ **Not `Id<T>`.** A `readonly record struct` with an implicit `string` operator — violates the platform's strongly-typed-id rule and is a *second*, incompatible `SigningSessionId` alongside Catalog's. Convert before anything constructs one |
| `MediaItemId` · `MediaProfileId` · `MemberId` | wrap `string` | `Domain/ValueObjects/` | ⚠ same shape, same problem |
| `SignerInfo` | `{ Email: string, RoutingOrder: int }` | `Domain/Aggregates/Events/` | ✅ the **write/event** shape — no status. Previously specified as `SignerSpec` |
| `SignerDto` | `{ Email: string, RoutingOrder: int, Status: SignatureStatus }` | `ReadModel/ReadModels/DocumentSigningSessions/` | ✅ the **read-model** shape. Previously specified as `Signer` |
| `SignatureStatus` | `Pending \| Completed` | `Domain/ValueObjects/` | ✅ previously specified as `SignerStatus` |
| `SigningSessionStatus` | `Initiated \| EnvelopeCreated \| EnvelopeSent \| Completed \| SignedAssetRecorded \| Voided \| Cancelled \| TimedOut` | `Domain/ValueObjects/` | ✅ exists exactly as documented. **This is a read-model status**, consumed only by the projector — not a saga status. See [`documentsigningsaga.md` § State Table](../../sagas/documentsigningsaga.md) |
| `CheckoutStatus` | `Available \| CheckedOut` | `Domain/ValueObjects/` | ❌ **Should not exist here.** Catalog owns checkout vocabulary and expresses it as a projected `string` off the `EditSession*` events. Delete with the redundant field on `CheckoutState` |

> **The write/read split is deliberate and worth keeping.** `SignerInfo` carries no status because a
> signer's status is derived by the projector from `SignerCompleted`; only `SignerDto` holds it. Do not
> collapse the two.

> **`RoutingOrder` is carried and read by nothing.** Whether signers are sequential or parallel is open —
> it changes what a timeout measures. [`documentsigningsaga.md` open question 3](../../sagas/documentsigningsaga.md#open-questions-this-file-does-not-answer).
```

---

## A.4 · `documentsigningsession.write-model.md` § Reference Models — replacement

Replaces both subsections. **Deletes the two "Subscribed integration events" tables** (SIGN-16) and the
non-existent event names (SIGN-14, SIGN-15).

```markdown
## Reference Models

Two Catalog-owned read models, consulted by `InitiateSigningSessionHandler` through an anti-corruption
interface. **Direct point reads — DocumentSigning maintains no projection of Catalog data and subscribes
to no Catalog event.** *(Settled 2026-09-08. This section previously specified DocumentSigning-owned
projectors subscribing via `media-projector`, contradicting § Consumed Integration Events in this same
file. The projector design was also written against four Catalog event names that do not exist.)*

Neither interface has an implementation yet. Both are implementable today against fields Catalog already
projects.

### `media-item` (Catalog detail read model — checkout slice)

**Owned by:** Catalog · **Consumed via:** `IMediaItemQueryService.GetCheckoutStateAsync` ·
**Used by:** `InitiateSigningSessionHandler`, to check the checkout precondition without loading the
`MediaItem` aggregate across a context boundary.

| Field on `MediaItemDetailReadModel` | Type | Purpose |
|---|---|---|
| `MediaProfileId` | `string` | Passed to the subsequent `IMediaProfileQueryService` call |
| `CheckedOutBy` | `string?` | Must equal `command.InitiatedBy` — null or a different member → `MediaItemNotCheckedOutByCaller` |
| `ActiveSigningSessionId` | `string?` | Must be null — non-null → `SigningSessionInProgress` |

> `CheckoutStatus` is also projected, as a `string`. It is **redundant** for this check — `CheckedOutBy`
> being null already means "not checked out" — and `CheckoutState` should not carry it.

### `media-profile` (Catalog — capabilities slice)

**Owned by:** Catalog · **Consumed via:** `IMediaProfileQueryService.GetPublishedAsync` ·
**Used by:** `InitiateSigningSessionHandler`, after resolving `MediaProfileId`.

| Field | Type | Purpose |
|---|---|---|
| `MediaProfileId` | `string` | Lookup key |
| `Capabilities` | `IReadOnlySet<string>` | Must contain `"Signing"` — absence → `SigningCapabilityNotEnabled` |

> **Capabilities cross the boundary as strings, and that is correct** — DocumentSigning takes no hard
> dependency on `Catalog.Domain` for one membership test. What it must not do is keep its own list of the
> legal values: `Catalog.Domain.Capability` is the single source (ruling 2026-09-04). The Catalog-side
> implementation maps `CapabilitySet` to strings before returning. **Return an `IReadOnlySet<string>`, not
> the `IList<string>` the current DTO declares** — an ACL must not hand out a mutable collection.
>
> `GetPublishedAsync` returns null for a profile that is not `Published`, deprecated included.
```

---

## A.5 · `documentsigningsession.write-model.md` § `IExecutionContext` Source by Entry-Point — replacement

Corrects the webhook row only (SIGN-31); the other three rows are right.

```markdown
| Entry-point | Implementation | `TenantId` source |
|---|---|---|
| HTTP (FastEndpoints) | `HttpExecutionContext` | JWT `tenant_id` claim |
| SecuredSigning adapter (SQS-triggered) | `SqsExecutionContext` | SNS message attribute `TenantId` |
| Webhook `POST /v1/integrations/secured-signing/webhooks` | `SqsExecutionContext` (after lookup) | **`media-signing-envelope-lookup[EnvelopeId].TenantId`** — strongly-consistent `GetItem` after HMAC validation |
| Scheduler / expiry Lambda | `SqsExecutionContext` | SNS message attribute `TenantId` |

> **Corrected 2026-09-08.** The webhook row said `media-signing-sessions[EnvelopeId]`, as did § Consumed
> Integration Events, the adapter's csproj comment, and DS-2's mermaid note. That lookup is **impossible**:
> `media-signing-sessions` is keyed `TENANT#{TenantId}#{SigningSessionId}` and cannot be queried by
> `EnvelopeId` without exactly the GSI [`documentsigningsession.read-model.md`](./documentsigningsession.read-model.md)
> rejects for being eventually consistent on a security decision. `media-signing-envelope-lookup` is the
> only correct answer, and the adapter's own `.cs` comments already say so. X-11.13.
```

---

## A.6 · `documentsigningsession.read-model.md` § Read Model Types — replacement

~~~markdown
## Read Model Types

Both implement `IReadModel : IVersionedProjection` from `Magiq.Platform.ReadModel`. Both exist in
`DocumentSigning.ReadModel/ReadModels/DocumentSigningSessions/`.

### `SigningSessionSummaryReadModel` → `media-signing-sessions`

```csharp
sealed record SigningSessionSummaryReadModel(
    string TenantId,
    string Id,                          // the SigningSessionId — `Id` is the platform's ProjectionKey convention
    string MediaItemId,
    string OwnerId,                     // ⚠ unpopulable today — no signing event carries an owner
    SigningSessionStatus Status,        // enum, not string
    DateTimeOffset CreatedAt,
    DateTimeOffset? ResolvedAt,
    long ProjectedVersion) : IReadModel;
```

### `SigningSessionDetailReadModel` → `media-signing-session-detail`

```csharp
sealed record SigningSessionDetailReadModel(
    string TenantId,
    string Id,
    string MediaItemId,
    string InitiatedBy,                 // ⚠ no OwnerId field — see below
    SigningSessionStatus Status,
    string? EnvelopeId,
    List<SignerDto> Signers,
    string? SignedAssetId,
    string? VoidReason,
    string? CancellationReason,
    DateTimeOffset? ResolvedAt,
    DateTimeOffset CreatedAt,
    DateTimeOffset UpdatedAt,
    long ProjectedVersion) : IReadModel;

sealed record SignerDto(string Email, int RoutingOrder, SignatureStatus Status);
```

> **Corrected 2026-09-08.** This section previously showed `SessionId` / `SigningSessionId` for the key
> field and `string` for both status fields, then declared the two enums immediately below. `Id` is what
> `ProjectionKey<T>(tenantId, signingSessionId)` produces and what every other module's read model uses;
> the statuses are strongly typed in code and should be.

> **⚠ Neither model can serve the specified authorization rule.** `documentsigningsession.api.md` gates the
> read and cancel routes on `caller.owner_id == session.OwnerId`. The detail model has **no owner field**,
> and the summary model's `OwnerId` has no event to source it from. Resolving this means adding `OwnerId`
> to `SigningSessionInitiated` — see [`documentsigningsession.write-model.md` § Domain Events](./documentsigningsession.write-model.md#domain-events).
~~~

---

## A.7 · `documentsigningsession.read-model.md` § Projection Handlers — add to `SigningSessionDetailProjector`

```markdown
### `SigningSessionDetailProjector`

**Target:** `media-signing-session-detail`. **Exists and is complete** — handles all nine events, resolves
every key to `(TenantId, SigningSessionId)`, maintains `Signers[]`, `EnvelopeId`, `SignedAssetId`,
void/cancel reasons, `ResolvedAt` and `UpdatedAt`.

> **⚠ Code defect — `ProjectedVersion` is never advanced.** Only the `SigningSessionInitiated` handler
> sets it (`ProjectedVersion: e.AggregateVersion`); the other eight take the `current with { … }` path and
> omit it, pinning the fence at the creation event's version. `ProjectedVersion` is the platform's only
> idempotency guard and the DynamoDB store's conditional-write predicate, so under at-least-once delivery
> every post-creation event is mis-handled. `MediaItemDetailProjector` sets it inside every `with`
> expression; this one must too. Latent only because no host registers this projector.

> **The projector's named-argument style is load-bearing.** `TenantId` and `Id` are adjacent same-typed
> `string` parameters and a positional call once transposed them, writing the session id into the tenant
> field on every row. Keep the named arguments; the underlying fix is `Id<T>` on the value objects.
```

---

## A.8 · `documentsigningsession.api.md` § Route Structure — replacement

One canonical set (SIGN-27, SIGN-28). All other files adopt these.

~~~markdown
## Route Structure

```
POST   /v1/media-items/{mediaItemId}/signing-sessions   Initiate signing session (owner)
POST   /v1/signing-sessions/{sessionId}/cancel          Cancel session (owner)

GET    /v1/signing-sessions/{sessionId}                 Get session detail
GET    /v1/signing-sessions?mediaItemId=                List by MediaItem

# System / adapter endpoints — actor_type = "System" only:
POST   /v1/signing-sessions/{sessionId}/envelope/created
POST   /v1/signing-sessions/{sessionId}/envelope/sent
POST   /v1/signing-sessions/{sessionId}/signers/{email}/completed
POST   /v1/signing-sessions/{sessionId}/completed
POST   /v1/signing-sessions/{sessionId}/signed-asset
POST   /v1/signing-sessions/{sessionId}/envelope/voided
POST   /v1/signing-sessions/{sessionId}/expire

# Unauthenticated, HMAC-validated:
POST   /v1/integrations/secured-signing/webhooks
```

> **⚠ None of these is served.** The `DocumentSigning` module has no `.Endpoints` project — the solution
> contains `Contracts`, `Domain`, `WriteModel`, `ReadModel` and `ReadModel.Infrastructure` and nothing
> else — so `Api` has no endpoint class to discover. `cdk-magiq-media` declares no
> `SagaOrchestrator.DocumentSigning` Lambda and no API Gateway route, so the webhook has no trigger. Read
> this section as intent. **DDD-T7.**

> **Canonicalised 2026-09-08.** Five route shapes were in circulation across four files:
> `/v1/items/{id}/signing-sessions`, `/media-items/{id}/media-signing-sessions`, `/v1/sessions/{id}`,
> `/v1/signing/sessions/{id}`, and `/media-signing-sessions/{id}`; the webhook had three
> (`/integrations/secured-signing/webhook`, `.../webhooks`, `/webhooks/secured-signing`). The set above
> is the one to build. `/v1/sessions` was rejected as too generic a top-level resource.
~~~

---

## A.9 · `context-overview.md` § SecuredSigning Adapter — replacement

```markdown
## SecuredSigning Adapter

`src/hosts/SagaOrchestrator.DocumentSigning` — **the host is misnamed.** Nothing in it is a saga: no saga
state, no `ISagaRepository`, no `media-sagas` reference. Its own XML doc calls it *"the SecuredSigning
Adapter"* and its registration class is `SecuredSigningRegistrations`. It is an **anti-corruption
adapter**, and a saga, if built, is a second and separate thing.

Designed to be the sole integration point with SecuredSigning:

1. Consumes `SigningSessionInitiated` from the **`media-signing`** SQS queue (300s visibility, maxReceive 3,
   DLQ `media-signing-dlq`, 14-day retention — [`event-store-and-messaging.md`](../../shared/event-store-and-messaging.md))
2. Calls the SecuredSigning API to create an envelope → dispatches `RecordEnvelopeCreatedCommand`
3. Receives webhooks at `POST /v1/integrations/secured-signing/webhooks` — unauthenticated, HMAC-validated
4. Dispatches `RecordEnvelopeSentCommand`, `RecordSignerCompletedCommand`, `RecordSigningCompletedCommand`,
   `RecordEnvelopeVoidedCommand` as callbacks arrive
5. On completion: downloads the signed PDF, uploads it to S3 as a new Asset, dispatches
   `RecordSignedAssetCommand`

**Webhook `TenantId` resolution:** the route carries no JWT. After HMAC validation, `TenantId` and
`SigningSessionId` are resolved by a strongly-consistent `GetItem(PK = EnvelopeId)` against
**`media-signing-envelope-lookup`**, written once by `SigningEnvelopeLookupProjector` on
`SigningEnvelopeCreated`. This is the only place in the system where `TenantId` comes from a table rather
than from `IExecutionContext`, which is why it is an isolated table rather than a GSI.

> **⚠ Nothing here runs.** Both handlers are stubs — `SigningSessionInitiatedHandler` throws
> `NotImplementedException`, `SecuredSigningWebhookHandler` returns HTTP 501. `ISecuredSigningApiClient`
> does not exist. `media-signing` is not provisioned. **No Lambda in `cdk-magiq-media` deploys this host**,
> though CI builds and pushes its image on every commit. `SigningEnvelopeLookupProjector` does not exist.
>
> **Names corrected 2026-09-08:** the queue was given as `signing-requests` here and `media-signing`
> everywhere else; the commands were given as `RecordEnvelopeCreated` etc. here and as
> `SigningEnvelopeSentCommand` / `CompleteSigningSessionCommand` / `VoidSigningEnvelopeCommand` in the
> adapter's own doc comments — the `Record*Command` family is canonical; the webhook route was singular
> and unversioned.
```

---

## A.10 · Smaller corrections

| File | Section | Change |
|---|---|---|
| `context-overview.md` | § High-Level Event Flows | `POST /media-items/{id}/media-signing-sessions` → `POST /v1/media-items/{mediaItemId}/signing-sessions`; webhook route → `/v1/integrations/secured-signing/webhooks` (3 occurrences) |
| `context-overview.md` | § Service Boundaries | Drop the `signing_` stream prefix line — no such concept exists; the convention is `[AggregateType("media.<name>")]` |
| `context-overview.md` | § External Dependencies | `Catalog` row: `MediaItemSigningSessionLinked/Unlinked` → `SigningSessionLinked`/`SigningSessionUnlinked` |
| `documentsigningsession.write-model.md` | § Invariants | Row 3: *"design only; nothing reads `Signing` today"* → *"`Capability.Signing` ships as the ninth enum member; no code reads it, because the handler that would is unbuilt"* |
| `documentsigningsession.write-model.md` | § Invariants, § Methods, § Commands | Remove `CompletionToken` / `InvalidCompletionToken`; add `CancelledBy` to `CancelSession`; `UserId` → `MemberId` throughout |
| `documentsigningsession.write-model.md` | § Properties | `OwnerId: OwnerId` → `OwnerId: MemberId` (pending decision 2); `InitiatedBy: UserId` → `InitiatedBy: MemberId` |
| `documentsigningsession.read-model.md` | § Consistency | "the two tables" → "all three tables"; add the fourth reason (two of three projectors do not exist) |
| `documentsigningsession.read-model.md` | § `media-signing-envelope-lookup` | Drop the `OwnerId` column — no event can source it, and a security-path lookup should carry the minimum |
| `documentsigningsession.api.md` | § Traceability | Drop `EnvelopeIdIndex`; add the `media-signing-sessions` column for the summary projector; fix the last row's route |
| `documentsigningsession.api.md` | § Write Endpoints | Remove the `completionToken` body from `POST .../completed` |
| `documentsigningsession.scenarios.md` | DS-1, DS-2, DS-3 | `MediaItemCheckedOut/CheckedIn/CheckoutAbandoned/CheckoutForceReleased` → `EditSessionOpened` / `EditSessionClosed(Reason: CheckedIn \| Abandoned \| ForceReleased)`; `MediaItemSigningSessionLinked/Unlinked` → `SigningSessionLinked`/`Unlinked`; `201` → `202`; routes per A.8; reframe the three test affordances as unbuilt; cross-ref the saga file on `TimeoutScanner` |
| `glossary.md` | Signer · SignerSpec · SigningSessionStatus | Drop *"⚠ Not built"* — all three exist (as `SignerDto`, `SignerInfo`, `SigningSessionStatus`); record the renames |
| `operations.md` | Projector inventory | `SigningSessionDetailProjector` → 🟠 *Exists, registered by no host* — distinct from the two 🔴 *Does not exist* rows below it |
| `business-scenarios.md` | header | Restamp `_Last reviewed_`, or fold the 28-line index into `context-overview.md` |

---

## Suggested next steps

1. **Fix SIGN-1 and SIGN-2 in code now, before anything else.** Eight one-line additions
   (`ProjectedVersion = e.AggregateVersion`) and a value-object conversion to `Id<T>`. Both are free today
   and expensive after the first event is emitted. Neither needs the module to be picked up.
2. **Settle the five decisions in § 8** — particularly 1 (`CompletionToken`) and 2 (`OwnerId`), because
   both change the nine event records, which are currently the only part of this module that is finished.
   Event shapes are the last thing that can be changed cheaply.
3. **Apply Appendix A section by section**, never as a whole-file rewrite — `docs-guard.yml` will catch a
   truncated tail, but it will not recover one.
4. **Fold SIGN-31 through SIGN-34 in one pass.** They are four naming contradictions with a single cause:
   the spec and the host doc comments were written independently and neither was reconciled. Cheap
   together, and they are what will mislead whoever implements first.
5. **Do not open a plan from this file.** Per § Review → Plan, if this is taken forward it becomes a review
   in a `document-signing` workstream folder first — and MM-038 (parked) is already that workstream. This
   report is evidence for it, not a replacement.
