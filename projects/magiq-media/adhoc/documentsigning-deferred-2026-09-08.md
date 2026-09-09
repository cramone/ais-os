# DocumentSigning — Deferred: Code Defects and Open Decisions

_magiq-media · 2026-09-08 · Chase Ramone_

**Companion to `documentsigning-spec-drift-2026-09-08.md`.** That report found 40 items across the
DocumentSigning spec and code. The **22 "spec wrong, code right"** items and the **9 spec-internal
contradictions** were applied to the spec on 2026-09-08 and are closed. This file carries what is left:
**the code defects, and the decisions the spec could not make for itself.**

Every entry names the spec section that marks it, so a fix and its spec text move together. The spec uses
two markers: ⚠ **Not implemented** (the code does not provide this) and ⚠ **Code gap** (code exists but
cannot support what the section specifies). Every ⚠ **Code gap** in the tree has an entry here.

**This is a standalone report, not a `review-cycle` review.** No `MM-` id, not indexed in
`reviews/README.md`. The `document-signing` workstream (MM-038, parked) is where this goes if taken
forward.

---

## What the spec rewrite changed

| | Count | Disposition |
|---|---:|---|
| Spec wrong, code right | 22 | **Closed** — spec rewritten to the code |
| Spec ↔ spec contradictions | 9 | **Closed** — one answer chosen per contradiction; four required a call, listed in § 2 |
| Code wrong | 9 | **Open** — § 1 below |
| Found during the rewrite | 2 | **Open** — § 1, SIGN-41 and SIGN-42 |
| Decisions taken to write a coherent draft | 4 | **Ratify or reverse** — § 2 |
| Still undecided | 3 | § 3 |

Seven spec files rewritten: 1,561 → 1,433 lines, with the missing pieces added rather than trimmed.
Three shared files edited in place (`error-catalog.md`, `glossary.md`, `operations.md`). All 89 files
under `docs/spec` pass `check-spec-truncation.py`; the DocumentSigning tree passes
`check-spec-sections.py` with zero warnings and zero rename backlog.

---

# 1. Code defects

Eleven. None is live today — nothing in this module runs — but the first four become defects the moment
the module is wired, and all four are cheaper to fix before anything is built on them.

### SIGN-1 · **High** · `SigningSessionDetailProjector` never advances `ProjectedVersion`

**Where:** `src/modules/DocumentSigning/DocumentSigning.ReadModel/Projectors/SigningSessionDetailProjector.cs`
**Marked in:** `documentsigningsession.read-model.md` § Projection Handlers

Only `ApplyAsync(SigningSessionInitiated …)` sets `ProjectedVersion`. The other eight handlers take the
`current with { … }` path and omit it, pinning the fence at the creation event's version forever.
`ProjectedVersion` is the platform's only idempotency guard (`IVersionedProjection`) and the DynamoDB
store's conditional-write predicate, so under at-least-once delivery every post-creation event is either
replayed unguarded or rejected outright.

**Fix:** add `ProjectedVersion = e.AggregateVersion` to all eight `with` expressions.
`MediaItemDetailProjector` (`Catalog.ReadModel`, lines 125 and 133) is the pattern.

---

### SIGN-2 · **High** · The four identifier value objects are not `Id<T>`

**Where:** `DocumentSigning.Domain/ValueObjects/{SigningSessionId,MediaItemId,MediaProfileId,MemberId}.cs`
**Marked in:** `documentsigningsession.write-model.md` § Value Objects

```csharp
public readonly record struct SigningSessionId(string Value)
{
    public static implicit operator string(SigningSessionId signingSessionId) => signingSessionId.Value;
}
```

Three consequences: platform constraint 8 requires `Id<T>` backed by `Medo.Uuid7`; the implicit `string`
operator makes any two of the four mutually assignable, which is why the projector's tenant/session
transposition once compiled; and this is a *second* `SigningSessionId`, incompatible with Catalog's — the
type that must receive it through `LinkSigningSessionCommand`.

**Fix:** convert all four to `Id<T>`. Nothing constructs them yet, so this is the cheapest it will ever be.

---

### SIGN-3 · Medium · `CheckoutStatus` duplicates a vocabulary Catalog owns

**Where:** `DocumentSigning.Domain/ValueObjects/CheckoutStatus.cs`
**Marked in:** `documentsigningsession.write-model.md` § Value Objects

`{ Available, CheckedOut }`. Catalog has no such enum — it projects a `string CheckoutStatus` on
`MediaItemDetailReadModel`, derived from the `EditSession*` family. The enum is unused by this model and
the spec's `CheckoutState` no longer carries it.

**Fix:** delete the enum and the `CheckoutStatus` member from `CheckoutState`.

---

### SIGN-4 · Medium · `MediaProfileSummary.Capabilities` is `IList<string>`

**Where:** `DocumentSigning.WriteModel/Services/MediaProfileSummary.cs`
**Marked in:** `documentsigningsession.write-model.md` § Write Model Service Interfaces

An anti-corruption boundary handing out a mutable collection, with an O(n) membership test for the only
operation performed on it.

**Fix:** `IReadOnlySet<string>`, as the spec now declares.

---

### SIGN-5 · Medium · A projection schema is registered for a table with no writer

**Where:** `DocumentSigning.ReadModel.Infrastructure/ServiceCollectionExtensions.cs`
**Marked in:** `documentsigningsession.read-model.md` § Read Models and § Projection Handlers

`AddProjectionSchema<SigningSessionSummaryReadModel>("media-signing-sessions", 1)` is registered;
`SigningSessionSummaryProjector` does not exist. The registration sits inside a method no host calls, for
a module whose events the publishing middleware drops. Three layers of dead wiring — the innermost throws
a schema mismatch if the outer two are ever fixed in the wrong order.

**Fix:** either build the summary projector or drop the schema registration until it exists.

---

### SIGN-6 · Medium · `SigningSessionSummaryReadModel.OwnerId` cannot be populated

**Where:** `DocumentSigning.ReadModel/ReadModels/DocumentSigningSessions/SigningSessionSummaryReadModel.cs`
**Marked in:** `documentsigningsession.read-model.md` § Read Model Types

No signing event carries an owner. The spec's record shape omits the field deliberately; the code still
declares it. Resolution depends on **Decision 2** (§ 2): if `OwnerId` is added to
`SigningSessionInitiated`, keep the field and add it to the detail model too; if not, delete it.

---

### SIGN-7 · Low · The adapter csproj comment names the wrong lookup table and a non-existent class

**Where:** `src/hosts/SagaOrchestrator.DocumentSigning/SagaOrchestrator.DocumentSigning.csproj`

```xml
<!-- DocumentSigning read model: SigningSessionProjector read models used
     for webhook TenantId resolution via media-signing-sessions lookup table -->
```

Two wrong names in four lines. The class is `SigningSessionDetailProjector`; the table is
`media-signing-envelope-lookup`, and `media-signing-sessions` **cannot** serve the lookup — it is keyed
`TENANT#{TenantId}#{SigningSessionId}` and cannot be queried by `EnvelopeId`. The `.cs` files in the same
project already say the right thing.

**Fix:** correct the comment. The spec side of this is closed.

---

### SIGN-8 · Low · `SigningSessionInitiatedHandler` throws where its own doc says return `Failed()`

**Where:** `src/hosts/SagaOrchestrator.DocumentSigning/Handlers/SigningSessionInitiatedHandler.cs`
**Marked in:** `documentsigningsaga.md` § DLQ & Poison Policy (as the target shape)

The class remarks specify `MessageProcessStatus.Failed()` on failure; the body throws
`NotImplementedException`. The five `AssetIngestion` saga handlers all catch and return `Failed()` — that
is the house shape, and a stub that throws is the more dangerous one to leave lying around.

**Fix:** return `Failed()` from the stub.

---

### SIGN-9 · Low · The adapter host registers no command dispatcher

**Where:** `src/hosts/SagaOrchestrator.DocumentSigning/Function.cs`

DI is composed with `AddAWSService<IAmazonDynamoDB>()`, `AddDynamoDb()`,
`AddSecuredSigningAdapterServices()` and `AddAWSMessageBus(...)`. Nothing registers `ICommandDispatcher`
or `IApplicationBus`, though `Magiq.Platform.WriteModel.Application` is referenced and every TODO in both
handlers ends in "dispatch command X". The first implementation attempt fails to resolve.

**Fix:** register the dispatcher, or note the omission at the composition site.

---

### SIGN-41 · Medium · The saga has no member identity to release a checkout with

**Where:** `Catalog.Domain/Aggregates/MediaItems/MediaItem.cs` — `ForceReleaseCheckout(MemberId releasedBy, DateTimeOffset releasedAt)`
**Marked in:** `documentsigningsaga.md` § Compensation · `documentsigningsession.scenarios.md` DS-1 step 11

*Found during the spec rewrite.* Every path out of a signing session ends in releasing the item's edit
session, and the saga holds no acting user. `ForceReleaseCheckout` requires a `MemberId` and there is no
correct value to supply. Three options, none obviously right:

- Pass the session's `InitiatedBy` — attributes a system act to a person who did not perform it
- Introduce a system `MemberId` — needs a convention that does not exist and shows up in audit output
- Give `MediaItem` a system-actor release overload — changes Catalog's aggregate for DocumentSigning's benefit

**Owner:** Catalog, not DocumentSigning. Settle before the compensation path is built.

---

### SIGN-42 · **High** · `DynamoDbSagaRepository` has no optimistic concurrency, and signing is the first case where it bites

**Where:** `src/shared/Media.Shared.Infrastructure/Sagas/DynamoDbSagaRepository.cs:53–73`
**Marked in:** `documentsigningsaga.md` § Idempotency

`SaveAsync` is an unconditional `PutItem`. The `Version` attribute is written as
`DateTimeOffset.UtcNow.ToUnixTimeMilliseconds()` and never read, so two concurrent handlers for the same
saga last-write-win.

Asset ingestion survives this because its events are naturally serial. **Signing is not serial:**
`SignerCompleted` callbacks for a multi-signer envelope arrive genuinely concurrently from the provider,
and webhooks are replayable and may arrive out of order. A conditional write on `Version` is a
prerequisite for a signing saga, not a follow-up.

**Owner:** shared infrastructure. This one blocks the saga.

---

> **Closed, verified 2026-09-08: X-11.6 is fixed.** The old saga file warned that both saga handler layers
> swallow exceptions and ack the message, making the `media-sagas` DLQ unreachable. All five
> `AssetIngestion` handlers now catch and return `MessageProcessStatus.Failed()`. The warning was not
> carried into the rewritten spec. Do not re-raise it.

---

# 2. Decisions taken to write a coherent draft — ratify or reverse

The spec could not be written as a first draft without settling four contradictions. Each call is recorded
here with its reasoning so it can be confirmed cheaply or reversed cheaply. **Three of the four change
event shapes, which stop being cheap the moment anything emits these events.**

### Decision 1 · `CompletionToken` was removed

**Landed in:** `documentsigningsession.write-model.md` (§ Domain Events, § Methods, § Commands),
`documentsigningsession.api.md` (`POST /{id}/completed` now has no body), `error-catalog.md`
(`InvalidCompletionToken` absent, with a note), `glossary.md` (entry retired)

`CompletionToken` appeared in six spec locations and zero code. `SigningCompleted` has no field for it, so
the invariant guarded a value nothing could supply or persist. The webhook's HMAC already authenticates
the callback, and completion is decidable from the aggregate's own signer state.

**To reverse:** add `CompletionToken` to `SigningCompleted`, restore `InvalidCompletionToken`, and say what
the token proves that HMAC does not.

---

### Decision 2 · The session identifies its actor as `InitiatedBy`, and `OwnerId` is marked as a gap

**Landed in:** `documentsigningsession.write-model.md` § Properties (⚠ Code gap),
`documentsigningsession.read-model.md` § Read Model Types (⚠ Code gap ×2),
`documentsigningsession.api.md` § Authorization (⚠ Code gap)

The spec now describes what the events carry — `InitiatedBy: MemberId` — and marks, in three places, that
the specified authorization rules have nothing to evaluate against. **This is the one decision the rewrite
deliberately did not make**, because the two answers are not equivalent:

| Option | Consequence |
|---|---|
| **Collapse to `InitiatedBy`** | Authorization becomes `caller.MemberId == session.InitiatedBy`. Cheapest, matches the events. Forecloses a delegate initiating on an owner's behalf — a real case in regulated records |
| **Add `OwnerId` to `SigningSessionInitiated`** | Matches `MediaItem.OwnerId` precedent, keeps delegation. Requires the event to change, and closes SIGN-6 |

**Recommendation: add `OwnerId`.** Also decide `CancelledBy` on `SigningSessionCancelled` at the same time
(§ 3, item 1) — both are event-shape changes and should land together.

---

### Decision 3 · The reference models are direct ACL reads, not DocumentSigning-owned projectors

**Landed in:** `documentsigningsession.write-model.md` § Reference Models (the two "subscribed integration
events" tables are gone), § Consumed Integration Events, `context-overview.md` § Integration Event
Contracts

The old write-model specified both architectures, sixty lines apart. Direct reads won on three grounds:
the interface signatures are point lookups, not projection readers; `MediaItemDetailReadModel` already
projects all three fields `CheckoutState` needs, so it is implementable today with no new projector; and
the projector design was written against four Catalog event names that do not exist.

**To reverse:** you would be building a projector for data Catalog already projects.

---

### Decision 4 · The saga dispatches `LinkSigningSession`, not the adapter

**Landed in:** `documentsigningsaga.md` § Transition Table (⚠ Code gap),
`documentsigningsession.scenarios.md` DS-1 step 5

`authorization-matrix.md:252` already says `SagaOrchestrator.DocumentSigning` only. The adapter is an
anti-corruption layer; a cross-context state-change command dispatched from an ACL is the wrong seam. But
`SigningSessionInitiatedHandler` carries a live TODO to do exactly that, and if the saga is never built
that TODO becomes the design by default.

**Regardless of which side wins:** `authorization-matrix.md:254` records `UnlinkSigningSession` as
*nothing — dead*. Linking without unlinking makes a `MediaItem` permanently un-checkoutable and
un-publishable with no operator command able to clear it. **Both paths ship in the same change, or
neither.**

**Code follow-up either way:** the TODO passes an `envelopeId` into a parameter typed `SigningSessionId`
(X-11.14).

---

# 3. Still undecided

Three questions the spec asks and does not answer. Each is marked in the tree.

### 1 · Does `SigningSessionCancelled` carry `CancelledBy`?

**Marked in:** `documentsigningsession.write-model.md` § Domain Events (⚠ Code gap)

`CancelSigningSession` takes the acting member; the event discards it, so a cancellation is unattributable
in the event stream. In a module built for regulated records that reads as a defect rather than a choice.
Same class as Decision 2 and should be settled with it — both change the event records while they are
still free to change.

---

### 2 · Sequential or parallel signing — what does `SignerInfo.RoutingOrder` mean?

**Marked in:** `documentsigningsession.write-model.md` § Value Objects · `documentsigningsaga.md` § Timeouts

The field is carried on every `SigningSessionInitiated` and read by no code. It determines what a timeout
measures: a whole-envelope clock and a per-signer clock are different budgets, and under sequential
signing a stalled first signer is invisible to the second. The spec commits to **one budget** and says so;
if `RoutingOrder` means sequence, that commitment needs revisiting.

**Also unsettled:** the budget's value. No signing budget of any kind exists in the codebase — no config
section, no options class, no constant. The spec names the config key
(`Media:DocumentSigning:SigningTimeouts` → `SigningBudgetHours`) and deliberately names no value.

---

### 3 · Is `media-document-signing` a second queue, or `media-signing` under another name?

**Marked in:** nothing — this one lives outside the DocumentSigning tree

`system-architecture.md` treats them as distinct: `media-signing` off `media-domain-events`, and
`media-document-signing` off `media-integration-events`. `cdk-magiq-media/lib/constructs/messaging/sqs-queues.ts:76`
carries only the latter, as a comment. The DocumentSigning spec now uses `media-signing` throughout,
because it is the one with a full specification behind it — visibility timeout, redrive policy, retention
— and the one the adapter's own doc comment names.

But this context **publishes no integration events**, so an integration-event-side signing queue has
nothing to carry. Either `media-document-signing` is vestigial and should be struck from
`system-architecture.md` and the CDK comment, or something is intended to publish that nothing in the spec
describes.

---

# Suggested order

1. **SIGN-1 and SIGN-2 now.** Eight one-line additions and a value-object conversion. Neither needs the
   module picked up, and both get more expensive with every line built on them.
2. **Settle Decision 2 and § 3 item 1 together** — they are the two event-shape changes, and event shapes
   are the last thing that can be changed for free.
3. **SIGN-42 before any saga work.** A signing saga on a repository with no optimistic concurrency is a
   known-broken build, not a first iteration.
4. **SIGN-3, SIGN-4, SIGN-7, SIGN-8, SIGN-9 as one cleanup pass.** All five are small, all five are in
   code the spec now contradicts, and leaving them makes the spec look wrong to the next reader.
5. **Decision 4 and SIGN-41 before the compensation path.** Both are about who acts on Catalog's behalf,
   and neither is DocumentSigning's alone to answer.
