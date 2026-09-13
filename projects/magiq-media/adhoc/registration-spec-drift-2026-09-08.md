# Registration — Spec ↔ Repo Drift Report

_magiq-media · 2026-09-08 · Chase Ramone_

**This is a standalone report, not a `review-cycle` review.** It has no `MM-` id and is not indexed in
`reviews/README.md`. If any block of it is taken forward, that block becomes a review in its own
workstream folder and this file becomes its evidence.

---

## Scope

| | |
|---|---|
| **Spec** | `D:\source\github\sprbrk-standard\mgq-magiq-media\docs\spec\contexts\Registration\` — 6 files, 2,201 lines |
| **Code** | `src\modules\Registration\` — 8 projects, 96 `.cs` files (excl. `obj`/`bin`) |
| **Also read** | `src\hosts\` (Api, QueryApi, EventConsumers, Projectors.*), `docs\spec\shared\error-catalog.md § Registration`, `aspnetcore-platform` projection/schema internals, Catalog's Registration consumers |
| **Aggregate** | `Registration` — the only one in this context |

**Out of scope:** edge (`actor_type = "System"`) authorization, which the spec itself defers to the
separate auth plan (MM-028/MM-029); `cdk-magiq-media` table/queue provisioning, which was not opened.

**Method.** Code first, spec second; every claim below was checked against the source rather than
against a sibling document. Platform behaviour (`DefaultProjectionSchema`, `ProjectionKey`,
`AddProjectionSchema`) was read in `aspnetcore-platform` rather than assumed.

---

## Headline

**26 findings. 5 High.**

| | Count | What it means |
|---|---:|---|
| **Spec wrong, code right** | 17 | Documentation drift. The system behaves correctly. |
| **Code wrong or unspecified behaviour** | 4 | § 1 — REG-1 through REG-4. |
| **Undecided / needs a call** | 5 | Spec and code disagree and it is not obvious which should move. |

**This module is in noticeably better shape than Catalog.** The R-1…R-19 corrections of 2026-08-22/25
clearly landed: the six integration-event contracts match field-for-field including the trailing
`EventVersion`; the OpenSearch mapping matches the read-model spec property-for-property; all eighteen
`errorCode` values in `RegistrationErrorCodes` match `error-catalog.md § Registration` exactly; the
seven-member `RegistrationStatus`, the `PendingConfirmation` rename, the `Reference`/`SubmissionReference`
split, `DispatchDetails`, `AttachedAt`, `ResolvedAt`, the `media-registrations` index name, `search_after`
pagination, owner scoping on search, and the two inverted capability checks are all exactly as specified.

**The drift that remains clusters in three places:**

1. **Persistence key shapes and table names** (§ 2) — the read-model spec's DynamoDB tables are described
   in a shape the platform does not produce, and the write-side reference model is documented under a
   table name that does not exist. This is the block most likely to mislead someone building a
   migration, a rebuild verb, or a CDK table definition.
2. **`registration.scenarios.md`** (§ 4) — R-4, R-5 and R-6 were written against an API that no longer
   exists and use enum values that were never real. R-1/R-2/R-3 are close to accurate. Same pattern
   Catalog showed: `*.scenarios.md` is the least trustworthy file in the tree.
3. **Cross-context consequences the spec does not mention** (REG-1, REG-2) — Catalog's reaction to
   `RegistrationRejected` is documented nowhere in the Registration spec and looks wrong.

---

# 1. Code-side defects and unspecified behaviour

Four findings where the code, not the spec, is likely what should move.

### REG-1 · **High** · A rejected registration loses its MediaItem link permanently

`Catalog.WriteModel/IntegrationEvents/Consuming/Handlers/RegistrationRejectedEventHandler.cs:33`
dispatches `RemoveRegistrationRefCommand` on `RegistrationRejectedIntegrationEvent`, which unlinks the
registration from the MediaItem and decrements the `active-registrations` counter
(`RemoveRegistrationRefHandler.cs:32`).

But `Rejected` is **not terminal** — the spec's own state machine has `Rejected → Resubmitted →
Submitted → PendingConfirmation → Confirmed`. Only `RegistrationInitiated` adds the ref
(`RegistrationInitiatedEventHandler`), and nothing consumes `RegistrationResubmittedIntegrationEvent`
or `RegistrationSubmittedIntegrationEvent` — confirmed by the subscription list in
`src/hosts/EventConsumers/ConsumerRegistrations.cs:140-142`, which subscribes to exactly three
Registration events: initiated, cancelled, rejected.

So after one reject → resubmit → confirm cycle, the MediaItem carries no registration reference and its
active-registration counter is one lower than reality — which also means a Folder containing it can be
archived while a live registration exists against it (`ArchiveFolderHandler.cs:69`).

`context-overview.md:76` describes `RegistrationRejectedIntegrationEvent` only as "Notifications alert
with rejection reason". The Catalog side-effect is not documented in the Registration spec at all.

**The call to make:** either Catalog should not unlink on reject (only on cancel), or resubmit must
re-add the ref. The first looks correct — a rejection is a retry point, not an ending.

### REG-2 · **High** · `GET /v1/registrations?mediaItemId=` is tenant-scoped only, not owner-scoped

`ListRegistrationsByOwnerQuery` filters on `OwnerId` from the execution context
(`ListRegistrationsEndpoint.cs`, `_ =>` branch) — correct, and what R-8 fixed for search. The
`mediaItemId` branch does not: `ListRegistrationsByMediaItemQuery.Matches` filters on `TenantId` and
`MediaItemId` only, and its GSI partition key is `TENANT#{t}#ITEM#{mediaItemId}#REGISTRATIONS`.

Any authenticated user in the tenant can therefore enumerate every registration on any media item —
including other users' authority reference numbers — by passing a `mediaItemId`. That is precisely the
hole R-8 closed on `/search` and that `registration.api.md:53-57` describes as closed.

`registration.api.md:50` documents only the no-filter mode's scoping and says nothing about the
`mediaItemId` mode, so the spec neither authorises nor forbids this. Given the stated posture on the
other two read paths, this reads as an oversight rather than a decision — but it is a decision someone
should make explicitly, because per-item listing may be intended to be shared.

### REG-3 · Medium · The reference model writes `IsArchived` and nothing reads it

`MediaItemReference` (`Registrations.WriteModel/.../ReferenceModels/MediaItemReference.cs:25`) carries
`IsArchived`, set to `true` by `MediaItemRegistrationIndexProjector.cs:65` on
`MediaItemArchivedIntegrationEvent`. No handler reads it — `MediaItemRegistrationContextService`
projects only `IsPublished`, `HasRegistrationCapability`, `HasProcessingCapability` and `MediaProfileId`
into `MediaItemRegistrationContext`.

It is harmless today because the same projector also sets `IsPublished = false`, and every guard tests
`IsPublished`. But it is the same shape as the `HasProcessingCapability` defect R-4 fixed: a field
carried for a check nobody wired up. Either drop it or document what it is for. The spec's reference
model table (`registration.write-model.md:362-368`) does not list it.

### REG-4 · Low · Three response records are declared and never sent

`SubmitRegistrationResponse`, `ResubmitRegistrationResponse` and `CancelRegistrationResponse` are the
declared `TResponse` of their endpoints, but all three handlers call `SendNoContentAsync`. The types are
unreachable. The spec is right (`204 No Content`, no body); the code should drop the dead records so
the endpoint signature stops advertising a body that never ships.

---

# 2. Persistence — keys, table names and shapes

The largest and most consequential block. All of these are **spec wrong, code right**, but the spec is
wrong in a way that would mislead a migration or a CDK change.

### REG-5 · **High** · The write-side reference model table is `media-registration-item-ref`, not `media-item-registration-refs`

`registration.write-model.md` names the table `media-item-registration-refs` in three places (§ Consumed
Integration Events, § Reference Models heading, and the § Reference Models prose). The registration is:

```csharp
builder.AddProjectionSchema<MediaItemReference>("media-registration-item-ref", "MEDIA_ITEM", schemaVersion: null);
```
`Registrations.WriteModel.Infrastructure/ServiceCollectionExtensions.cs:112`

Note also `schemaVersion: null` — every other projection in the module declares `1`. Whether that is
deliberate (this is a reference model, not a read model) is worth confirming against the CDK
projection-table manifest, since the physical name is `{tableName}-v{schemaVersion}`.

The spec's field table is also incomplete: the record carries `TenantId`, `IsArchived` and
`ProjectedVersion` beyond the five documented fields (REG-3).

### REG-6 · **High** · Neither read-model table uses the documented partition key

`registration.read-model.md` gives both tables `PK = TENANT#{TenantId}#{RegistrationId}`. Reading
`DefaultProjectionSchema.BuildPartitionKey` / `BuildSortKey` in `aspnetcore-platform` against the actual
registrations:

| | Registered as | Key built with | Actual PK | Actual SK |
|---|---|---|---|---|
| Detail | `("media-registration", "REGISTRATION")` | `ProjectionKey(tenantId, "DETAIL", registrationId)` | `TENANT#{t}#REGISTRATION#{regId}` | `DETAIL` |
| Summary | `RegistrationSummarySchema("REGISTRATIONS")` | `ProjectionKey(tenantId, registrationId)` | `TENANT#{t}#REGISTRATIONS` | `SUMMARY#{regId}` |

Sources: `Registrations.ReadModel.Infrastructure/ServiceCollectionExtensions.cs:68-69`;
`RegistrationDetailReadModel.cs:66`; `RegistrationSummaryReadModel.cs:37`;
`RegistrationSummarySchema.cs:11`.

Two things follow, and the second is worth its own decision:

- The spec's "discriminator `DETAIL`" is right, but the schema identifier that actually appears in the
  PK is `REGISTRATION` — a third name for the same thing, alongside the table name `media-registration`.
- **Every summary row for a tenant lives in one partition.** The summary schema passes no group key, so
  `TENANT#{t}#REGISTRATIONS` is a single partition per tenant with `SUMMARY#{regId}` sort keys. That is a
  deliberate-looking design (it is what makes a tenant-wide list a single query), but it is neither
  documented nor bounded, and it contradicts the repo `CLAUDE.md` convention line
  "DynamoDB PK on every table: `TENANT#{TenantId}#{EntityId}`". For a compliance-grade tenant with
  years of filings this is the partition that grows without limit.

### REG-7 · Medium · The read-model tables are not column-shaped

Both spec tables list flat columns (`TenantId`, `RegistrationId`, `MediaItemId`, `Status`, …). The
platform's `DefaultProjectionSchema.MapToDynamoDbItem` writes the whole model as one JSON string under a
`Data` attribute, plus `PK`, `SK` and `ProjectedVersion` — and, for the summary, the four GSI key
attributes written by the index schemas. Nothing else is a real DynamoDB attribute.

This matters wherever someone reasons about attribute-level updates, sparse indexes or projections: none
of the documented "fields" can be indexed or conditionally updated as written.

### REG-8 · Low · The summary table still lists `EventId` and `RegistrationId`

`registration.read-model.md:31` lists `EventId` in the summary table; line 91 of the same file states
"`EventId` is not a field on either read model and has been dropped from both tables here." The table was
not actually edited. Same table names the identifier `RegistrationId` (line 20) where the model — and the
C# block later in the same document — says `Id`.

**GSIs are correct.** `RegistrationByMediaItemIndex` / `RegistrationByOwnerIndex`, the `GSI1PK`/`GSI1SK`
/ `GSI2PK`/`GSI2SK` attribute names, the `TENANT#{t}#ITEM#{id}#REGISTRATIONS` /
`TENANT#{t}#OWNER#{id}#REGISTRATIONS` partition values and the `{InitiatedAt:O}#{Id}` sort key all match
the two index schemas exactly.

---

# 3. Write model — aggregate, commands, handlers

### REG-9 · Medium · `ApproveAmendment` / `RejectAmendment` require `Status = Confirmed`, and the invariant table omits it

`Registration.cs:155` and `:317` both check `Status != RegistrationStatus.Confirmed` **first**, before the
amendment is even looked up, returning `InvalidStatusTransition` (422). The write model's invariant table
(`registration.write-model.md:46-47`) lists only "the amendment must exist" and "must be `Pending`".

`registration.api.md:427` gets this right for `/approve` (`422 InvalidStatusTransition (Status ≠
Confirmed)`), so the two files disagree. Ordering matters to a client: approving an amendment on a
cancelled registration returns `InvalidStatusTransition`, not `AmendmentNotFound`.

### REG-10 · Medium · The five `[System]` command signatures in § Commands are stale

| Spec | Actual |
|---|---|
| `ConfirmRegistrationCommand(RegistrationId, Reference)` | `(TenantId, RegistrationId, Reference, RequestingUser, ConfirmedAt)` |
| `RejectRegistrationCommand(RegistrationId, RejectionReason)` | `(TenantId, RegistrationId, **Reason**, RequestingUser, RejectedAt)` |
| `ApproveAmendmentCommand(RegistrationId, AmendmentId, DecisionNotes?)` | `(TenantId, RegistrationId, AmendmentId, DecisionNotes, ApprovedAt)` |
| `RejectAmendmentCommand(RegistrationId, AmendmentId, DecisionNotes?)` | `(TenantId, RegistrationId, AmendmentId, DecisionNotes, RejectedAt)` |

All five carry `TenantId` and a server-stamped timestamp. The command field is `Reason`
(`RejectRegistrationCommand.cs:10`); `rejectionReason` is the HTTP request field only — which the spec
says elsewhere and then contradicts here. The six owner-driven command signatures all match.

### REG-11 · Medium · § Methods omits every timestamp parameter

`Cancel()`, `Resubmit()`, `Reject(reason)`, `ApproveAmendment(amendmentId, decisionNotes?)` and
`RejectAmendment(amendmentId, decisionNotes?)` all take a trailing `DateTimeOffset` in code.
`RequestAmendment` is missing two parameters in the spec — actual signature is
`RequestAmendment(amendmentId, requestedBy, mediaItemId, itemType, notes, amendedAt)`, and both
`requestedBy` and `notes` are documented elsewhere in the same file.

Since every one of these timestamps is stamped from the execution context at the endpoint (the R-11
rule), the spec's parameterless forms actively obscure the thing R-11 established.

### REG-12 · Medium · `RegistrationAuthority` normalisation: the spec contradicts itself, and the code sides against two of the three

`InitiateRegistrationCommandHandler.cs:58` calls
`CultureInfo.InvariantCulture.TextInfo.ToTitleCase(command.RegistrationAuthority.Trim())`.

.NET's `ToTitleCase` treats a fully-uppercase word as an acronym and leaves it unchanged. So
`"US Copyright Office"` is stored as **`"US Copyright Office"`**, not `"Us Copyright Office"`.

- `registration.write-model.md:340` and `registration.api.md:84` both publish `"Us Copyright Office"`.
- `registration.scenarios.md:57` says the opposite: "acronyms like 'US' are preserved (not lowercased
  before title-casing)."

The scenarios file is the one that matches the code. Nothing tests this — a `grep` for `ToTitleCase` and
`Copyright Office` across `tests/` finds no assertion on the normalisation. **Worth one unit test to pin
whichever behaviour is intended before deciding which document moves**, since the value is stored and
indexed as-normalised and a controlled vocabulary is deferred.

### REG-13 · Low · Type and name mismatches on the aggregate

- `Registration.MediaProfileId` is `string` (`Registration.cs:59`); the spec's property table says
  `MediaProfileId`. The event and the factory parameter *are* the value object — it is unwrapped on
  `Apply`.
- The amendment value object is `Amendment` (`ValueObjects/Amendment.cs:3`); the spec calls it
  `RegistrationAmendment` throughout, including the § Properties row `IReadOnlyList<RegistrationAmendment>`.
- § Properties lists `InitiatedAt`. There is no such property — `RegistrationInitiated.InitiatedAt` is
  assigned to the platform base's `CreatedAt`.
- `RequestAmendmentCommand.cs:10` comments `AmendmentId` as "Caller-generated UUIDv7". It is
  server-generated at the endpoint (`RequestAmendmentEndpoint`, `AmendmentId.New()`), exactly as R-10
  requires. The comment is a leftover and should go — it is the kind of thing the next reader trusts.

### REG-14 · Low · Handler/command naming: `AttachItemToRegistration` vs `AttachMediaItemToRegistration`

The spec uses both. `context-overview.md:50` and `registration.write-model.md:324` say
`AttachItemToRegistration` / `AttachItemToRegistrationHandler`; the same write-model file's pre-condition
table says `AttachMediaItemToRegistrationHandler`. Only the longer form exists. The *namespace* is
`Commands.AttachItemToRegistration`, which is presumably where the short form came from.

Also worth noting: `Commands/ApproveAmmendment/` — two m's — is misspelled in both the folder and the
namespace (`Magiq.Media.Registrations.Commands.ApproveAmmendment`). Cosmetic, but it is a public
namespace.

---

# 4. `registration.scenarios.md` — R-4, R-5 and R-6 are stale

R-1, R-2 and R-3 track the code closely. The three later scenarios do not, and they were clearly written
before the route and enum decisions that are now settled everywhere else.

### REG-15 · **High** · R-4 and R-6 use a route and a `registrationType` that do not exist

Both call `POST /v1/registrations` with `{ "mediaItemId": ..., "registrationType": "Copyright" }`
(lines 256-259, 359-361). The route is `POST /v1/items/{itemId}/registrations`, the media item comes from
the path, and `RegistrationType` has exactly two members: `Electronic` and `Physical`. R-6 additionally
sends `"jurisdiction": "AU"`, a field that appears in no request, command, event or read model anywhere
in the module.

Anyone reading the scenarios to understand the initiate contract would get all three wrong.

### REG-16 · Medium · R-6's `itemType` value is not a member of the enum

`"SupportingDocument"` (lines 368, 378). `RegistrationItemType` is
`ApplicationForm | SupportingEvidence | ConfirmationReceipt | Other`. The API spec has this right.

### REG-17 · Medium · R-6 attributes state to `RegistrationInitiated` that it does not carry

`RegistrationInitiated { Items: [{ doc-primary, Primary }] }` (line 363) and
`RegistrationSubmitted { Items: [...] }` (line 387). Neither event carries an `Items` collection —
items arrive only via `RegistrationItemAttached`, and there is no `Primary` item type. The 201 body is
also given as `{ "registrationId": "reg-01" }`; the response record is
`InitiateRegistrationResponse(Id, MediaItemId, Timestamp)`, so the field is `id`.

### REG-18 · Low · Response codes in the scenarios are `200` where the endpoints return `204`

R-1, R-2, R-3 and R-6 show `→ 200` (and `CH-->>Client: 200` in the mermaid diagrams) for attach, submit,
resubmit, record-submission and confirm. All five call `SendNoContentAsync`. `registration.api.md` is
correct throughout.

### REG-19 · Low · R-5 names the event field `PriorStatus`

Lines 311 and 323. The field is `PreviousStatus` (`RegistrationCancelled.cs`), and it is the one place
`RegistrationStatus` is persisted numerically — so the name matters more here than most.

### REG-20 · Low · R-3's diagram passes an `amendmentId` its own step text says is server-generated

Step 2 (line 200) states the id is server-generated and returned as `id` — correct. The mermaid diagram
seven lines later shows `RequestAmendment(amendmentId=amd-01, doc-03, ConfirmationReceipt)`.

### REG-21 · Low · R-4's error `detail` is not the message the handler emits

R-4 (line 290) gives `"MediaItem mi-draft-01 must be in Published status before it can be registered."`
The handlers emit `"Media item is not published. Only published media items can be registered."`
(initiate) and `"... can be attached to a registration."` (attach/amend). `registration.api.md:109` has
the correct string.

---

# 5. Context overview

### REG-22 · Medium · Registration does not own the active-registration counter

`context-overview.md:85-87` — "**Owns.** … the per-item active-registration counter that gates Folder
archive." It does not. The counter is Catalog's: incremented in
`Catalog.WriteModel/Commands/MediaItems/AddRegistrationRef/AddRegistrationRefHandler.cs:37`, decremented
in `RemoveRegistrationRefHandler.cs:32`, keyed `CounterKeys.ActiveRegistrations`, and read by
`ArchiveFolderHandler.cs:69`. Nothing in `src/modules/Registration/` touches it.

This matters because REG-1 is a consequence of exactly that ownership: Registration publishes events,
Catalog maintains the counter, and the two are not reasoning about the same lifecycle.

### REG-23 · Medium · Two documented downstream consumers do not exist in this repo

`context-overview.md:73-74` says the saga orchestrator consumes `RegistrationSubmittedIntegrationEvent`
to trigger external authority submission and `RegistrationResubmittedIntegrationEvent` to retry it.
Neither event is subscribed anywhere: `EventConsumers/ConsumerRegistrations.cs:140-142` subscribes to
initiated, cancelled and rejected only, and no saga references either type.

Both events are published and nothing consumes them. Whether that is "not built yet" or "not needed"
should be said in the spec — the § Service Boundaries block already carries a "Specified but not built"
paragraph, and this belongs in it. (The Compliance subscriber to `media.registration.confirmed` is
plausibly out-of-repo and was not checked.)

### REG-24 · Low · The consumer class and host names are wrong

`registration.write-model.md:320-324` names a single consumer `MediaItemRegistrationContextConsumer` in
host `Media.IntegrationEventConsumers.Lambda`. There are three handler classes —
`MediaItemRegistrationContext{Created,Approved,Archived}EventHandler` — plus the
`MediaItemRegistrationIndexProjector` they dispatch into, and the host is `EventConsumers` (the repo's
own `CLAUDE.md` host table has this right). No project named `Media.IntegrationEventConsumers.Lambda`
exists. The queue name `media-cross-module-events` is correct.

### REG-25 · Low · Amendment events are called "domain-internal only" while all eleven are published to SNS

`context-overview.md:79` and `registration.write-model.md:302`: the four amendment/item events "do not
cross module boundaries." True of *integration* events — the mapper handles exactly the six documented
types. But all eleven domain events are published to the `media-domain-events` topic
(`Api/Infrastructure/DomainEventPublisherRegistrations.cs:153-163`), which is how the projectors receive
them. The sentence is correct in intent and misleading as written; "not translated to an integration
event" would be exact.

### REG-26 · Low · `/amendments/{amendmentId}/reject` has no endpoint section in the API spec

It is in the route table (line 34) and the traceability table (line 670), but unlike `/approve` it gets
no request/response/errors block. The endpoint exists and mirrors approve exactly.

---

# 6. Verified correct — worth recording

So the next pass does not re-check them:

- **All six integration event contracts** — field names, order, types and the trailing `long EventVersion`
  — match `Registrations.Contracts/Events/*.cs` exactly, including `RegistrationConfirmedIntegrationEvent
  .RegistrationReference` and the `CancelledAt` (integration) / `CanceledAt` (domain) spelling split.
- **`MessageType` names** — `media.registration.{initiated,submitted,resubmitted,confirmed,rejected,cancelled}`.
- **`RegistrationSubmissionRecorded` is not published** — no mapper handles it, as documented.
- **All eighteen `errorCode` values** in `RegistrationErrorCodes` match `error-catalog.md § Registration`
  one-for-one, with the documented HTTP mapping (404/409/422/403) matching the `DomainErrors` factories.
- **The OpenSearch mapping** in `QueryApi/OpenSearch/RegistrationsIndexMapping.cs` matches the
  read-model spec's field table property-for-property, including the `dynamic: "strict"` object mappings
  for `Items` and `Amendments` and the PascalCase naming.
- **The search DSL** — `TenantId.keyword` filter, `OwnerId` term filter for `User` actors,
  `multi_match` on `RegistrationAuthority^2 / Reference^3 / RegistrationType / Notes`, sort
  `(InitiatedAt desc, Id.keyword asc)`, `search_after` pagination — matches § Query Handlers.
- **Owner scoping** (R-3/R-8) is live and reads the actor from `ICommandHandlingContext` /
  `IExecutionContext`, never the payload; `RegistrationOwnership.CheckOwner` is applied to exactly the
  five owner-driven commands and none of the five `[System]` ones.
- **The two inverted capability checks** (R-4) are correct in both directions in all three handlers.
- **`ConfirmRegistrationCommand.Reference` is a raw string** validated in the handler before the value
  object is constructed (R-13 follow-up) — no 500 on a blank reference.
- **`pageSize` clamping** (20 default, 100 max) and `sortBy`/`sortOrder` resolution with a 400 on an
  unsupported value (R-14) are implemented in `RegistrationPaging` / `RegistrationSort`.
- **Host wiring** matches § Service Boundaries: write model in `Api` + `EventConsumers`, queries in
  `Api` + `QueryApi`, projectors in `Api` + `Projectors.ReadModel`, detail projector in
  `Projectors.Search`. Registration is indeed one of exactly two OpenSearch-projected read models.
- **`Idempotency-Key`** is handled by `Magiq.AspNetCore.Idempotency` middleware configured host-wide in
  `Api/Startup.cs:98`, so the per-endpoint "_Accepts `Idempotency-Key`_" notes hold.
- **The seven-member `RegistrationStatus`**, its ordinal stability comment, and the property-scoped
  `JsonStringEnumConverter` on both read models.

---

# Incidental — not spec drift

`tests/integration/modules/Registration/Registration.IntegrationTests/AhocTest.cs` is entirely commented
out and contains a **real bearer JWT for `chase.ramone@magiqsoftware.com`**, committed to the repo.
Expired (`exp` 1780568101 ≈ 2026-06-04), so not live, but it should not be in git history and the file
has no other content. Delete it.

---

## Suggested next steps

Nothing here is a review yet. If any of it is taken forward:

1. **REG-1 and REG-2 are the only two that change behaviour.** They are a natural pair — both are about
   what the Registration lifecycle means to the rest of the platform — and they belong together in an
   `registration-lifecycle` workstream, not in a documentation sweep.
2. **§ 2 (REG-5…REG-8) is a documentation fix with one embedded decision** — the single-partition summary
   table. The decision is worth splitting out; it may already be in scope for `projection-tables`
   (MM-003).
3. **§ 3, § 4 and § 5 are a single spec sweep** — roughly a day, mechanical, and best done in one PR
   against `docs/spec/contexts/Registration/` so the files stop disagreeing with each other. REG-12 is
   the only one needing a test first.
