# Collection — Aggregate Architecture Review (Specification vs Repository)

_Context: **Catalog** (bounded context) — magiq-media_
_Aggregate: **Collection**_
_Reviewer role: Principal Domain Architect (DDD / CQRS / Event Sourcing / API) and Senior Software Engineer_
_Date: 2026-07-19_
_Scope: `docs/spec/contexts/Catalog/aggregates/Collection/**` (api, read-model, scenarios, write-model) + shared conventions (api-conventions, error-catalog, security-scenarios, bulk-operations, media-types), `docs/adrs/catalog-domain-invariants.md`, `docs/spec/contexts/Catalog/context-overview.md` vs `src/modules/Catalog/**` Collection slice: `Catalog.Domain/Aggregates/Collections/**`, `Catalog.Domain/ValueObjects/{CollectionId,Tag,MediaProfileId}.cs`, `Catalog.Domain/Repositories/ICollectionRepository.cs`, `Catalog.Contracts/Events/Collections/**`, `Catalog.WriteModel/Commands/Collections/**`, `Catalog.WriteModel/IntegrationEvents/{Publishing/Mappers/CollectionDomainEventMapper,Consuming/Handlers/CollectionArchivedEventHandler}.cs`, `Catalog.WriteModel/Services/Collections/**`, `Catalog.WriteModel.Endpoints/V1/{Collections/**,CatalogEndpoint.cs}`, `Catalog.WriteModel.Infrastructure/{Repositories/CollectionRepository,Services/Collections/CollectionArchiveFanOutWorker,ServiceCollectionExtensions}.cs`, `Catalog.ReadModel/{Projectors,ReadModels,Queries}/Collections/**`, `Catalog.ReadModel.Endpoints/V1/{Collections/**,CatalogEndpoint.cs}`, `Catalog.ReadModel.Infrastructure/{Queries/Schemas/Collections/**,ServiceCollectionExtensions}.cs`_

> **Method:** every production `.cs` file in the Collection slice — **90 files** across Domain (aggregate, 7 events + marker, snapshot, 3 aggregate VOs, 2 shared VOs, repository interface), Contracts (5 integration events), WriteModel (8 command + handler pairs incl. bulk, mapper, consumer, fan-out interface), WriteModel.Endpoints (6 endpoint folders + base), WriteModel.Infrastructure (repository, fan-out worker, DI), ReadModel (2 projectors, 2 read models, 3 query+handler pairs), ReadModel.Endpoints (3 endpoint folders + summary contract + base), ReadModel.Infrastructure (3 schemas + DI) — was read in full and compared against the Collection write-model, read-model, api and scenarios specs plus the shared conventions and error catalog. Folder / MediaItem / MediaProfile code was consulted only where Collection references it directly (the default `MediaProfileId` published-guard, and the archive fan-out's `ArchiveFolderCommand`/`ArchiveMediaItemCommand` dispatch). Findings that hinge on unread `Magiq.Platform` base behaviour (`CommandHandler` error-code mapping, `PagerParameters` cap enforcement, projection-store GSI key removal on update) are flagged as such.

---

## 1. Module / Aggregate Summary

`Collection` is the top-level organisational namespace of the Catalog context — an owner-scoped container that governs visibility (`Private | Unlisted | Public`), tags, an optional default `MediaProfileId`, and archival for its entire Folder/MediaItem subtree. It is a deliberately *small* aggregate: it owns **no** references to child Folders or MediaItems (those relationships live entirely on the Folder/MediaItem read models), so its event stream is a flat lifecycle of create → rename/retag/re-describe/visibility/default-profile → archive.

Structurally the slice is clean and complete: `EventSourced<Collection, CollectionId, CollectionSnapshot>` + `ITenantScoped`, `[AggregateType("media.collection")]`, seven domain events all wired in `When<>`, a snapshot, command-per-folder handlers, a domain-event→integration-event mapper, two DynamoDB read models (`media-collections` summary, `media-collection` detail) fed by two projectors with **full event coverage**, three query handlers, and both GSIs (name index, sparse public index) registered. Several things the AssetManagement review flagged as defects are done **correctly** here: `TenantId`/actor are sourced from `IExecutionContext` (never the body), event timestamps are passed in from the endpoint (`context.GetUtcOffsetNow()`) rather than `DateTimeOffset.UtcNow` inside the aggregate, both projectors handle every event, the bulk endpoint enforces its 50/100 cap and returns the correct 201/202 envelope, and the public GSI is sparse-keyed so archived collections drop out of public discovery.

However, the aggregate is **not production-ready**. The review surfaced **2 Critical** and a cluster of **High** issues in four themes:

1. **Authorization is absent end-to-end.** No endpoint declares a policy and no handler performs the PERM-1 owner check. Mutating commands don't even carry an `ActorId`. Any authenticated tenant user can rename, retag, re-visibility, archive, read and **list** any other owner's collection — including reading *Private* collections they don't own.
2. **Archive is implemented as an irreversible write-side cascade — the exact opposite of the spec.** The write-model and C-3 scenario both mandate "write-side aggregates untouched, read-model-only, fully reversible." The code's fan-out worker instead dispatches `ArchiveFolderCommand`/`ArchiveMediaItemCommand`, hard-archiving every descendant aggregate, and swallows every failure.
3. **State-guard and read-model integrity gaps.** Archived collections remain fully mutable (only `Rename`/`Archive` guard `IsArchived`); the summary projector corrupts `CreatedAt` on `CollectionDefaultProfileSet`; `PATCH` is a non-atomic 3-command sequence.
4. **The error/validation/DTO contract is unmet.** Generic errors instead of catalog codes, no RFC 9457 `errorCode`, no validators (malformed IDs → 500), and `TenantId` leaks in both read DTOs.

The aggregate core is the strongest part; nearly every Critical/High defect lives in the **handler / projector / fan-out / endpoint orchestration layer** around it.

---

## 2. Aggregate Analysis

### `Collection` (Aggregate Root) — `Catalog.Domain/Aggregates/Collections/Collection.cs`

`EventSourced<Collection, CollectionId, CollectionSnapshot>`, `ITenantScoped`, `[AggregateType("media.collection")]`. Single aggregate; no child entities (correct — Folder/MediaItem membership is read-model-only, documented in the class summary).

**Value objects:** `CollectionId` (UUID v7, `IEntityId`), `CollectionName` (`ValueOf<string>`, regex-validated), `CollectionVisibility` (enum), `CollectionStatus` (enum), `MediaProfileId`, `Tag`, `MemberId` (as `OwnerId`), `TenantId`. Healthy VO surface — not anemic.

**Key state:** `TenantId` (first field of `CollectionCreated`, set once), `OwnerId` (immutable), `Name`, `Description?`, `Visibility`, `Tags`, `DefaultMediaProfileId?`, `ArchivedAt?`, `Status`, `CreatedAt`. `IsArchived => ArchivedAt.HasValue`.

**Invariants enforced in the aggregate (correct):**
- `Archive()` blocks re-archive (`IsArchived` guard, `Collection.cs:97`).
- `Rename()` blocks when archived (`Collection.cs:110`) and short-circuits on unchanged name.
- `UpdateDescription`/`SetVisibility`/`SetDefaultMediaProfile` all have idempotent no-op guards (`!=` before `Emit`).
- Event timestamps are all passed in (`archivedAt`, `renamedAt`, `updatedAt`, `appliedAt`) — deterministic under replay. **This is the correct pattern** (contrast AssetManagement A-D2).
- `TenantId` is the first field of `CollectionCreated` (`CollectionCreated.cs:10`), set once in `Apply`.

**Aggregate boundary assessment:** appropriate and minimal. Correctly does not own child references, uniqueness, or profile-published policy (handler/reference concerns).

**Aggregate-level defects (detailed in §12–13):**
- **COL-D1 (High, correctness).** `SetVisibility`, `UpdateDescription`, `ApplyTags` and `SetDefaultMediaProfile` have **no `IsArchived` guard** (`Collection.cs:85-89, 125-133, 137-145, 171-179`). Only `Rename` and `Archive` reject an archived collection. The API spec (`collection.api.md:105-114, 129`) says `PATCH` and `default-profile` return `422 CollectionArchived` on an archived collection — unreachable in code. An archived collection can be re-tagged, re-described, re-visibility'd and re-defaulted indefinitely.
- **COL-D2 (Low, redundancy).** `Create` emits `CollectionCreated` carrying `Description` **and then** a second `CollectionDescriptionUpdated(null, description)` when description is non-null (`Collection.cs:69-73`); `Apply(CollectionCreated)` already sets `Description` (`:213`). Description is set twice and projected twice. The write-model spec's `CollectionCreated` payload (`collection.write-model.md:60`) omits `Description` entirely — code adds it to the event *and* keeps the separate update event.
- **COL-D3 (Low, generic error).** `Archive()` returns `DomainError.InvalidOperation("Collection is already archived.")` (`Collection.cs:99`) rather than the catalog's `CollectionAlreadyArchived` code. Status (422) is right; the machine-discriminable `errorCode` is wrong (§12 COL-M2).
- **COL-D4 (Low).** `Rename`'s archived-rejection message is `"Collection is already archived."` — copy-pasted from `Archive`; should read "cannot rename an archived collection."

---

## 3. Lifecycle Analysis

### State machine (reconstructed from `Collection.cs` guards + `Apply` handlers)

```text
        Create(name, visibility, description?, defaultProfileId?)
                          │
                          ▼
                    ┌──────────┐   Rename ✔(guarded: not archived)
                    │  Active  │   UpdateDescription / SetVisibility / Tag / SetDefaultMediaProfile
                    │(Status=  │◄─── ⚠ NONE of these last four guard IsArchived (COL-D1)
                    │ Active)  │
                    └────┬─────┘
                         │ Archive()  (guard: not already archived)
                         ▼
                   ┌────────────┐
                   │  Archived  │  Status=Archived, ArchivedAt set
                   │ [terminal] │  ⚠ still accepts Tag/Description/Visibility/DefaultProfile (COL-D1)
                   └────────────┘
                         │
                         ╳  No UnarchiveCollection command in v1 (spec-acknowledged dead-end)
```

Fan-out (async, on `CollectionArchived` integration event) is **outside** the aggregate: spec says it flips `IsAccessible=false` on descendant *read models only*; code instead hard-archives descendant *aggregates* (§12 COL-C2).

**Terminal state:** `Archived` — but leaky (COL-D1) and permanently so (no unarchive).

### Lifecycle issues
- **COL-L-Life1 (High) — Archived is a leaky terminal state.** Because four mutators skip the guard (COL-D1), "terminal" is not terminal; a client can keep writing to an archived collection, and those writes still publish integration events (rename/tag/visibility) to downstream Search/Billing, resurrecting a supposedly-dead namespace.
- **COL-L-Life2 (Medium) — No removal/unarchive path.** `UnarchiveCollection` is explicitly deferred to a future version (`collection.scenarios.md:100`, write-model `:145`). Combined with COL-C2 (which *hard*-archives every child aggregate), the "fully reversible at the read layer" guarantee (`collection.write-model.md:11,145`) is doubly false: not only is there no unarchive, the children are irreversibly archived as aggregates.
- **COL-L-Life3 (Low) — `Create` double-writes description** (COL-D2): the create lifecycle emits two events for one logical state.

---

## 4. Commands

8 commands, all registered in `AddCatalogWriteModel` (`ServiceCollectionExtensions.cs:170-176, 233`) and all reachable from an endpoint. `⚠` marks a command with at least one finding.

| Command | Handler | Trigger | Notes |
|---|---|---|---|
| CreateCollectionCommand | CreateCollectionHandler | API `POST /collections` | ⚠ no default-profile `IsPublished` guard; non-atomic reserve-then-save; endpoint never supplies `DefaultMediaProfileId` |
| RenameCollectionCommand | RenameCollectionHandler | API `PATCH` (name) | ⚠ no owner check; non-atomic swap-then-save; part of non-atomic PATCH |
| UpdateCollectionDescriptionCommand | UpdateCollectionDescriptionHandler | API `PATCH` (description) | ⚠ no owner check; no archived guard (COL-D1) |
| SetCollectionVisibilityCommand | SetCollectionVisibilityHandler | API `PATCH` (visibility) | ⚠ no owner check; no archived guard (COL-D1) |
| SetDefaultMediaProfileCommand | SetDefaultMediaProfileHandler | API `PUT /default-profile` | ⚠ no owner check; no archived guard; no profile-owner check |
| TagCollectionCommand | TagCollectionHandler | API `PUT /tags` | ⚠ no owner check; no archived guard (COL-D1) |
| ArchiveCollectionCommand | ArchiveCollectionHandler | API `POST /archive` | ⚠ no owner check; releases name reservation **before** save (non-atomic); generic error |
| BulkCreateCollectionsCommand | BulkCreateCollectionsHandler | API `POST /bulk` | ⚠ no default-profile `IsPublished` guard; reserve-then-save non-atomic; VO throws abort whole batch |

Also dispatched **internally** by the fan-out worker (not Collection commands, but triggered by Collection archive): `ArchiveFolderCommand`, `ArchiveMediaItemCommand` (§12 COL-C2).

**Cross-cutting command issues:**
- **No mutating command carries the actor's identity.** `RenameCollectionCommand`, `ArchiveCollectionCommand`, `SetCollectionVisibilityCommand`, `TagCollectionCommand`, `UpdateCollectionDescriptionCommand`, `SetDefaultMediaProfileCommand` are `(TenantId, CollectionId, …, OccurredAt)`. Only `CreateCollectionCommand`/`BulkCreateCollectionsCommand` carry `OwnerId` (set = caller, correct for creation). PERM-1 is therefore impossible downstream (§12 COL-C1).
- **Handlers return generic errors** (`EntityAlreadyExists`, `ResourceNotFound`, `InvalidOperation`) rather than catalog codes (§12 COL-M2).
- Command set maps cleanly 1:1 to aggregate methods; no duplicate/redundant commands. `SetVisibility`/`UpdateDescription`/`SetDefaultMediaProfile` idempotent no-op guards are good.

---

## 5. Queries

3 queries — `GetCollectionByIdQuery`, `ListCollectionsQuery`, `ListPublicCollectionsQuery`. All registered (`ServiceCollectionExtensions.cs:114-116`).

| Query | Paging | Auth / Scope | Notes |
|---|---|---|---|
| GetCollectionByIdQuery | n/a | ⚠ none | returns any tenant collection regardless of owner/visibility — leaks Private (§12 COL-H2); response leaks `TenantId` |
| ListCollectionsQuery | cursor (ADR-014 ✔) | ⚠ none | ignores `ownerId`; `Matches` = all tenant rows → cross-owner + archived + private listed (§12 COL-H1); name-sorted, not `createdAt desc` |
| ListPublicCollectionsQuery | cursor (ADR-014 ✔) | tenant-scoped | requires auth + tenant-scoped, contradicting spec "no auth / across all owners"; sparse public GSI correctly excludes archived ✔ |

**Query issues:**
- **CQRS boundary is clean** — handlers return read-model DTOs via `IReadModelReader`; no aggregates/event payloads cross the boundary; cursor-only pagination, no total count (ADR-014 ✔). Good.
- **No owner scoping** on `GetCollectionById` or `ListCollections` (§12 COL-H1/H2). `ListCollectionsQuery.Matches` (`ListCollectionsQuery.cs:19-22`) returns every row where `rm.TenantId == TenantId` — no owner, no visibility, no archived filter.
- **`ListPublicCollections` diverges from spec** on auth and scope (§12 COL-M6) but its archived-exclusion is handled correctly by the sparse GSI (`PublicCollectionByNameIndexSchema.cs:49-52`) — a genuine positive.
- **`ListCollections` default sort is by name**, not the spec's `createdAt desc` (§12 COL-M5); `sortBy`/`sortOrder` are silently unsupported.

---

## 6. API Endpoints

Spec (`collection.api.md`) vs implementation (routes registered in the six endpoint classes; base `CatalogEndpoint`):

| Spec route | Verb | Impl? | Impl status | Spec status | Note |
|---|---|---|---|---|---|
| /v1/collections | POST | ✔ | 201 | 201 | ok; body omits `defaultMediaProfileId` (matches spec body) |
| /v1/collections/bulk | POST | ✔ | 201/202/400 | 201/202/400 | envelope + cap correct ✔ |
| /v1/collections/{id} | PATCH | ✔ | 204/400/404/409/422 | 204/…/422 | ⚠ non-atomic 3-command; 422-archived unreachable (COL-D1) |
| /v1/collections/{id}/default-profile | PUT | ✔ | 204/404/422 | 204/404/422 | ⚠ no profile-owner check; no archived guard |
| /v1/collections/{id}/tags | PUT | ✔ | 204 | 204 | ⚠ no archived guard; tags unvalidated → 500 |
| /v1/collections/{id}/archive | POST | ✔ | 204 | 204 | ⚠ 422 vs 409 doc contradiction; unused response DTO |
| /v1/collections/{id} | GET | ✔ | 200 | 200 | ⚠ no owner/visibility check; leaks `TenantId` |
| /v1/collections?ownerId= | GET | ✔ (partial) | 200 | 200 | ⚠ **`ownerId` param not implemented**; returns all tenant collections |
| /v1/collections/public | GET | ✔ | 200 (auth req.) | 200 (no auth) | ⚠ requires JWT + tenant-scoped vs spec "unauthenticated / all owners" |

**Endpoint issues:**
- **No endpoint declares authorization.** Grep of the six endpoints + both `CatalogEndpoint` bases finds zero `Roles/Policies/Permissions/RequireActorType/AllowAnonymous/PreProcessor`. Every endpoint's Swagger advertises a `403` that no code path can emit. (§12 COL-C1)
- **RFC 9457 `errorCode` never emitted.** Both bases do `AddError(error.ErrorMessage)` + `SendErrorsAsync((int)status)` (`WriteModel.Endpoints/V1/CatalogEndpoint.cs:20-24`); the read base additionally flattens `QueryErrorCode` to `NotFound→404 / Forbidden→403 / _→500` (`ReadModel.Endpoints/V1/CatalogEndpoint.cs:23-29`), discarding any domain `errorCode`. No `extensions.errorCode` is ever produced. (§12 COL-M2)
- **`GET /collections` ignores `ownerId`** — the endpoint request (`ListCollectionsRequest`) has only `PageSize`/`PageToken`; there is no owner filter and no owner scoping (§12 COL-H1).
- **`GET /collections/public` requires authentication** (uses `context.TenantId`, declares `401`) — directly contradicting the spec's "No authentication required" (`collection.api.md:229`) (§12 COL-M6).
- **Verb/route/version:** all registered routes match the spec and every endpoint is `Version(1)`. `Archive` endpoint summary text ("return 409") contradicts its own 422 response doc and the code (COL-L3).

---

## 7. Request DTO Review

| DTO | Findings |
|---|---|
| CreateCollectionRequest | `Name = null!` with no validator → omitted `name` NREs at `CollectionName.From(req.Name)` → 500; `Visibility` enum defaults silently to `Private (0)` if omitted; no `defaultMediaProfileId` field (so API create can't set a default — matches spec body but diverges from the richer command) |
| PatchCollectionRequest (+ Converter) | Custom converter tracks `*Set` flags for true partial semantics — **good design**; but `CollectionId` from route → `CollectionId.From` (`Guid.Parse`) throws → 500 on malformed id; no length/pattern validation of name/description |
| SetDefaultMediaProfileRequest | `CollectionId`/`ProfileId` both `null!`; `MediaProfileId.From(req.ProfileId)`/`CollectionId.From` throw → 500 on malformed |
| TagCollectionRequest | `Tags = []` default (so omission is safe, unlike AssetManagement's NRE) — **good**; but each `Tag.From(t)` throws on an invalid tag → whole request 500 instead of 422 |
| BulkCreateCollectionsRequest / BulkCreateCollectionModel | `Name = null!`; a single invalid name/`DefaultMediaProfileId` throws in the endpoint's `.Select(...)` mapping → the **entire batch 500s** instead of per-item `failed` (§12 COL-M3) |

**Cross-cutting:**
- **No FluentValidation validators anywhere** in the slice. Consequence: `CollectionId.From`/`MediaProfileId.From` call `Guid.Parse` and the `ValueOf` VOs throw `ValidationException` on malformed input → unhandled → **500** where the spec expects 400/404/422 (§12 COL-M3).
- **`pageSize` cap (100) not enforced locally** — relies on unverified platform `PagerParameters.FromCursor`.
- No unused request properties. Field naming is internally consistent (`collectionId`, `profileId`).

---

## 8. Response DTO Review

| DTO | Findings |
|---|---|
| CreateCollectionResponse | `(Id, Name, Description, Visibility, CreatedAt)` — matches spec 201 body ✔ |
| GetCollectionByIdResponse | **leaks internal `TenantId`** (`:6, :22`); adds `UpdatedAt` not in spec body; otherwise complete |
| CollectionSummaryModel (list items) | **leaks `TenantId`** (`:6, :21`); exposes `OwnerId`, `Tags`, `UpdatedAt`, `ArchivedAt` beyond the spec's summary shape `{id,name,visibility,isArchived,createdAt}` |
| ListCollectionsResponse / ListPublicCollectionsResponse | envelope `{Items, PageSize, NextPageToken}` matches api-conventions ✔ |
| BulkCreate* (Succeeded/Failed/Skipped/Response) | full `succeeded/failed/skipped` envelope with `index`/`name`/`errorCode`/`suggestedName` — matches shared bulk-operations ✔ |
| ArchiveCollectionResponse | **defined but never sent** (endpoint returns 204 no-body); field misspelled `ArchiveAt` (should `ArchivedAt`) — dead DTO (COL-L2) |

**Cross-cutting:**
- **`TenantId` leakage** in both `GetCollectionByIdResponse` and `CollectionSummaryModel` — a multi-tenancy boundary value that must never round-trip to clients (§12 COL-M4).
- Identifier naming is consistent (`Id` throughout the API surface); the read-model *record* field is `Id` while the read-model *spec* calls it `CollectionId` — cosmetic (COL-L7).

---

## 9. Domain Events

7 domain events, all registered in `Collection`'s constructor `When<>` block (`Collection.cs:27-33`) and all handled by both projectors. Publisher = `Collection` aggregate.

**Projection coverage (verified against both projectors — complete, a genuine strength):**

| Domain event | Summary proj. | Detail proj. | Notes |
|---|---|---|---|
| `CollectionCreated` | ✔ INSERT | ✔ INSERT | ok |
| `CollectionRenamed` | ✔ Name | ✔ Name | ok |
| `CollectionDescriptionUpdated` | ✔ (UpdatedAt only) | ✔ Description | summary has no Description field (correct — detail-only per read-model spec) |
| `CollectionVisibilityChanged` | ✔ Visibility | ✔ Visibility | ok |
| `CollectionDefaultProfileSet` | ⚠ **corrupts `CreatedAt`** | ✔ DefaultMediaProfileId | §12 COL-H4 |
| `CollectionTagged` | ✔ Tags | ✔ Tags | ok |
| `CollectionArchived` | ✔ IsArchived/ArchivedAt | ✔ IsArchived/ArchivedAt | ok |

Other domain-event notes:
- **Timing correct** — every event carries a passed-in timestamp; no wall-clock inside the aggregate.
- **Out-of-order safety** — non-create handlers return `MissingCurrentAsync()` when `current is null`, and all upserts stamp `ProjectedVersion = e.AggregateVersion` (idempotent under duplicate SQS delivery). Good.
- **Payload divergence:** `CollectionCreated` carries `Description` (COL-D2); the write-model spec omits it. No duplicate events.

---

## 10. Integration Events

### Published (mapper `CollectionDomainEventMapper.cs`)

5 mappings — `CollectionArchived/Created/Renamed/Tagged/VisibilityChanged` → matching `*IntegrationEvent` (`MessageType("media.collection.*")`), each carrying `TenantId`, `CollectionId`, `EventVersion = e.AggregateVersion`. `CollectionDescriptionUpdated` and `CollectionDefaultProfileSet` are intentionally **not** published — matches the write-model published-events table (`collection.write-model.md:119-126`). Registered via `AddDomainEventMappers<CollectionDomainEventMapper>` (`ServiceCollectionExtensions.cs:240`).

| Issue | Severity | Detail |
|---|---|---|
| COL-FP1 | Low (doc) | Code record names are `*IntegrationEvent`; context-overview contracts call them `*Message` (`context-overview.md:135-143, 225-283`). Timestamp fields are per-event-named (`CreatedAt`/`RenamedAt`/`TaggedAt`/`ChangedAt`/`ArchivedAt`) whereas the spec contracts use `OccurredAt` for most. Code adds `EventVersion` not present in the spec contracts. Reconcile before the wiki publish. |
| COL-FP2 | Low | `CollectionRenamed`/`Tagged`/`VisibilityChanged` are published even when raised on an *archived* collection (COL-D1) — downstream Search/Billing receive mutation events for a "dead" namespace. |

### Consumed (`CollectionArchivedEventHandler` → `CollectionArchiveFanOutWorker`)

The Collection write model self-consumes `CollectionArchivedIntegrationEvent` via the integration-event feed to drive descendant archival (registered `ServiceCollectionExtensions.cs:138`).

| Issue | Severity | Detail |
|---|---|---|
| COL-FC1 | **Critical** | The worker dispatches **write-side** `ArchiveFolderCommand`/`ArchiveMediaItemCommand` (`CollectionArchiveFanOutWorker.cs:105,116`), hard-archiving every descendant aggregate — the spec mandates read-model-only `IsAccessible=false`, "write-side aggregates untouched," "fully reversible" (`collection.write-model.md:11,143-145`; `collection.scenarios.md:92,101-105`). Irreversible for a regulated-records platform. (§12 COL-C2) |
| COL-FC2 | High | `DispatchArchiveFolderAsync`/`DispatchArchiveMediaItemAsync` **swallow failures** — a failed `ArchiveMediaItem` (e.g. a checked-out item → `MediaItemCheckedOut`) only logs a warning; `Task.WhenAll` "succeeds", the handler logs "complete", the message is ACKed → **partial archive, no DLQ, no retry** (`CollectionArchiveFanOutWorker.cs:108-111,118-121`). |
| COL-FC3 | Medium | Unbounded parallelism: all media-item archives across the whole subtree are fired into one `Task.WhenAll` (`:65-86`) with no `MaxDegreeOfParallelism` and no sharding/checkpointing, despite the write-model describing "sharded `CollectionItemsIndex` … one shard per Lambda invocation with checkpoint-per-page" (`collection.write-model.md:137,143`). Large collections → command-dispatch storm / Lambda timeout. |
| COL-FC-pos | — | **Correct:** the consumer sources `tenantId` from `IExecutionContext`, not the payload (`CollectionArchivedEventHandler.cs:27`) — the convention AssetManagement's consumers violated. |

---

## 11. Specification vs Repository Differences

| Item | Specification | Repository | Severity | Recommendation |
|---|---|---|---|---|
| Ownership guard (PERM-1) | All Collection write/read commands enforce `actor.Id == OwnerId` (`security-scenarios.md:67`; `collection.api.md:36-41`) | Not enforced anywhere; mutating commands lack `ActorId` | Critical | Thread `ActorId`, enforce in handlers + query handlers, emit 403 |
| Archive semantics | Read-model-only; write-side aggregates untouched; fully reversible (`collection.write-model.md:11,143-145`; `collection.scenarios.md:92,101-105`) | Fan-out hard-archives Folder + MediaItem aggregates via write commands | Critical | Replace with read-model `IsAccessible` fan-out; do not mutate child aggregates |
| List by owner | `GET /collections?ownerId=`; `caller.owner_id == ownerId` (`collection.api.md:40,216`) | No `ownerId` param; returns all tenant collections (all owners/visibilities) | High | Add owner filter + owner-scoped GSI; enforce caller==ownerId |
| Get authorization | Owner or public visibility (`collection.api.md:39`) | Returns any tenant collection incl. others' Private | High | Enforce owner-or-public in `GetCollectionByIdHandler` |
| Archived guard on mutations | PATCH/default-profile → 422 archived (`collection.api.md:101,105-114,129`) | Only Rename/Archive guard `IsArchived` | High | Add `IsArchived` guard to Visibility/Description/Tag/DefaultProfile |
| Summary projection of DefaultProfileSet | UPDATE detail table only (`collection.read-model.md:66`) | Summary projector overwrites `CreatedAt` | High | Return `Unchanged()` in summary projector |
| PATCH atomicity | Single partial update → 204 (`collection.api.md:86-99`) | 3 independent commands; partial-apply on mid-failure | High | Single command or ambient transaction across the 3 |
| Reservation ↔ event atomicity | `repository.Save` + `nameReservation.Reserve` committed atomically by TransactionBehavior (`collection.write-model.md:187-288`) | Awaited sequentially, non-transactional; reserve/swap/release ordered before/around save | High | Use ambient `ITransactionScope`; guard/event before side effect |
| Default-profile published guard | `CreateCollectionHandler`/`SetDefaultMediaProfileHandler` check `IsPublishedAsync` (`collection.write-model.md:88-91,204-206`) | Only `SetDefaultMediaProfileHandler` checks; Create + Bulk do **not** | Medium | Add published guard to Create + Bulk |
| Default-profile owner | Profile "owned by the same owner" (`collection.api.md:120`) | Handler checks published only, not owner | Medium | Add profile-owner check |
| Public listing auth/scope | Unauthenticated; across all owners (`collection.api.md:229`) | Requires JWT; tenant-scoped | Medium | Reconcile — decide anonymous vs authed (challenge spec: cross-tenant public browse is dubious on a compliance platform) |
| List default sort | `createdAt desc`, backed by createdAt GSI (`api-conventions.md:262`) | `CollectionByNameIndex` sorts by name; `sortBy`/`sortOrder` ignored | Medium | Add createdAt GSI or accept name-sort and fix the conventions doc |
| Error contract | RFC 9457 + `errorCode` extension; catalog codes (`error-catalog.md:64-71`) | Generic `AddError(message)`; no `errorCode`; `InvalidOperation`/`EntityAlreadyExists` | Medium | Emit `errorCode`; map `CollectionAlreadyArchived`/`CollectionAlreadyExists`/`CollectionNotFound` |
| Validators | 400/422 for malformed input | None; `Guid.Parse`/VO throw → 500 | Medium | Add FluentValidation validators |
| `TenantId` in responses | Not in GET/list body (`collection.api.md:200-224`) | Present in `GetCollectionByIdResponse` + `CollectionSummaryModel` | Medium | Remove `TenantId` from response DTOs |
| `CollectionCreated` payload | No `Description` (`collection.write-model.md:60`) | Event carries `Description` + separate update event | Low | Drop `Description` from the event or the redundant update event |
| Detail table name | `media-collection-detail` (`collection.read-model.md:30`) | `media-collection` (`ServiceCollectionExtensions.cs:145`) | Low | Reconcile table name |
| Canonical interfaces | `ICollectionQueryService`, `IMediaProfileReadModel` (`collection.write-model.md:97-106`) | Not present; `INameReservationService.IsNameAvailableAsync` + `IMediaProfileRepository` | Low (doc) | Update spec to the implemented interfaces |
| Integration record names | `*Message`, `OccurredAt`, no `EventVersion` | `*IntegrationEvent`, per-event timestamps, `EventVersion` | Low (doc) | Reconcile context-overview contracts to code |

---

## 12. Bugs

### Critical

**COL-C1 — No ownership authorization on any endpoint, handler, or query (intra-tenant data exfiltration + tampering).**
Verified: zero auth attributes across the six endpoints and both `CatalogEndpoint` bases; mutating commands (`RenameCollectionCommand`, `ArchiveCollectionCommand`, `SetCollectionVisibilityCommand`, `TagCollectionCommand`, `UpdateCollectionDescriptionCommand`, `SetDefaultMediaProfileCommand`) carry no `ActorId`; `GetCollectionByIdHandler`, `ListCollectionsHandler`, `ListPublicCollectionsHandler` apply no owner scoping. `security-scenarios.md:67` and `collection.api.md:34-41` require `caller.owner_id == collection.OwnerId` on writes and owner-or-public on reads.
*Why it's a problem:* the ownership boundary is the primary intra-tenant control on a multi-tenant, regulated-records platform. *Impact:* any authenticated tenant user can rename, retag, change visibility of, archive, read and list **any other owner's collection**, including reading collections marked `Private`. *Recommendation:* thread `ActorId` from `IExecutionContext` into every mutating command; enforce `actor.Id == collection.OwnerId` in the handlers (after load) and owner-or-public in `GetCollectionByIdHandler`; add an owner filter + `caller==ownerId` check to `ListCollections`; return `DomainError.Forbidden`/`NotResourceOwner` → 403 with `errorCode`.

**COL-C2 — Collection archive hard-archives every descendant Folder and MediaItem aggregate, contradicting the read-model-only / reversible spec (irreversible mutation of regulated records).**
`CollectionArchiveFanOutWorker.ArchiveSubtreeAsync` dispatches `ArchiveMediaItemCommand` (`:116`) and `ArchiveFolderCommand` (`:105`) for every item and folder in the subtree. The write-model (`collection.write-model.md:11,143-145`) and scenario C-3 (`collection.scenarios.md:92,101-105`) state unambiguously: "Archiving is write-side only — no cascade… propagates `isAccessible = false` to descendants asynchronously via **read model updates**," "Write-side aggregates (`Folder`, `MediaItem`) are not touched by archive," "Archiving is fully reversible at the read layer."
*Why it's a problem:* the code permanently archives child aggregates as a side effect of archiving their collection; with no `UnarchiveCollection` (and no way to un-archive the individually-emitted `FolderArchived`/`MediaItemArchived` events even if there were), the spec's reversibility guarantee is destroyed. It also couples Collection archive to the full MediaItem/Folder invariant surface (a checked-out or already-archived item makes the child command fail — silently, see COL-FC2). *Impact:* irreversible bulk lifecycle mutation of regulated records; divergence from the documented, downstream-relied-upon contract. *Recommendation:* replace the fan-out with a read-model projection that stamps `IsAccessible = false` on `media-items`/`media-item-detail`/OpenSearch (as the scenario diagram shows) and leaves the write-side event streams untouched; if a true write-side cascade is genuinely wanted, change the spec and add a compensating unarchive path first.

### High

**COL-H1 — `GET /collections` ignores `ownerId` and returns every collection in the tenant.**
`ListCollectionsRequest` has only `PageSize`/`PageToken`; `ListCollectionsQuery.Matches` returns all rows with `rm.TenantId == TenantId` (`ListCollectionsQuery.cs:19-22`) and `CollectionByNameIndexSchema` partitions on `TENANT#{tenant}#COLLECTIONS` (no owner). The spec's list is owner-scoped (`collection.api.md:40,216`). *Impact:* a user listing their collections receives every other owner's collections in the tenant, including `Private` ones. *Recommendation:* add an `ownerId` query param, an owner-scoped index (or post-filter), and enforce `caller==ownerId`.

**COL-H2 — `GET /collections/{id}` returns collections the caller neither owns nor can see publicly.**
`GetCollectionByIdHandler` fetches by tenant+id and returns the row unconditionally (`GetCollectionByIdHandler.cs:13-19`). Spec: "Owner or public visibility" (`collection.api.md:39`). *Impact:* any tenant user reads any collection's full detail (name, description, tags, default profile) including others' `Private` collections. *Recommendation:* after load, require `collection.OwnerId == actor.Id || collection.Visibility != Private` (Unlisted/Public readable), else 404/403.

**COL-H3 — Archived collections remain fully mutable (no `IsArchived` guard on four mutators).**
`SetVisibility`, `UpdateDescription`, `ApplyTags`, `SetDefaultMediaProfile` (`Collection.cs:85-89,125-133,137-145,171-179`) never check `IsArchived`. The API contract returns `422 CollectionArchived` for PATCH (`collection.api.md:101,105-114`) and default-profile (`:129`). *Impact:* the archived "terminal" state is not terminal; clients keep writing (and publishing rename/tag/visibility integration events) to archived collections; the 422 the API advertises is unreachable. *Recommendation:* add the `IsArchived` guard (returning `CollectionArchived`) to all four, consistent with `Rename`.

**COL-H4 — `CollectionSummaryProjector` corrupts `CreatedAt` when a default profile is set.**
`ApplyAsync(CollectionDefaultProfileSet, …)` in the summary projector does `current with { CreatedAt = e.OccurredAt, UpdatedAt = e.OccurredAt, … }` (`CollectionSummaryProjector.cs:46-49`). The summary read model has no `DefaultMediaProfileId` field (correct — read-model spec says detail-only, `collection.read-model.md:66`), so this handler should be a no-op, but it **overwrites the collection's `CreatedAt`** with the time the default profile was set. *Impact:* `GET /collections` list rows show a wrong `createdAt`, and any future createdAt-based ordering/pagination is corrupted for every collection that has had a default profile set. *Recommendation:* return `Unchanged()` (or omit the handler) for `CollectionDefaultProfileSet` in the summary projector.

**COL-H5 — `PATCH /collections/{id}` is a non-atomic sequence of up to three independent commands.**
`PatchCollectionEndpoint.HandleAsync` dispatches `RenameCollectionCommand`, then `UpdateCollectionDescriptionCommand`, then `SetCollectionVisibilityCommand` in sequence (`PatchCollectionEndpoint.cs:78-106`), each a separate aggregate load / event append / (for rename) name-reservation swap. If the 2nd or 3rd fails (concurrency conflict, validation), the earlier change is already persisted while the endpoint returns an error and the client believes the PATCH failed. Three separate optimistic-concurrency writes also triple the conflict surface. *Impact:* partial updates, inconsistent client view, 3× version churn per PATCH. *Recommendation:* introduce a single `UpdateCollectionCommand` that applies all three mutations in one aggregate load/append, or wrap the three dispatches in one ambient transaction.

**COL-H6 — Name-reservation and event append are non-transactional dual writes (orphaned/lost reservations on partial failure).**
The spec's canonical handlers register `repository.Save` and `nameReservation.Reserve/Swap/Release` in an ambient `ITransactionScope` committed atomically (`collection.write-model.md:213-220,255-257,281-283`). The code instead **awaits them separately**: `CreateCollectionHandler` awaits `ReserveAsync` then `SaveAsync` (`:37-46`) → if `SaveAsync` fails, the name is reserved with no collection (orphan, name permanently taken); `ArchiveCollectionHandler` awaits `ReleaseAsync` **before** `SaveAsync` (`:35-37`) → if `SaveAsync` fails the name is freed while the collection stays active/un-archived; `RenameCollectionHandler` awaits `SwapAsync` before `SaveAsync` (`:48-55`) → reservation points to the new name while the aggregate keeps the old. *Impact:* reservation/aggregate divergence on any partial failure — orphaned names, or a live collection whose name is unreserved and claimable by another. *Recommendation:* use the ambient-transaction pattern the spec documents; where not available, order guard→event persisted→reservation and make the reservation op idempotent/compensating.

### Medium

- **COL-M1** — `CreateCollectionHandler` and `BulkCreateCollectionsHandler` never verify a supplied `DefaultMediaProfileId` is `Published` (`CreateCollectionCommandHandler.cs`; `BulkCreateCollectionsHandler.cs:130-140`), contradicting the write-model pre-condition (`collection.write-model.md:88-89,204-206`). The single-create *endpoint* never supplies the field (so unreachable there), but bulk accepts `defaultMediaProfileId` per item (`BulkCreateCollectionModel.cs:13`) → an unpublished (or wrong-owner) profile is accepted. `SetDefaultMediaProfileHandler` checks published but not owner (spec `collection.api.md:120`).
- **COL-M2** — Generic errors, no `errorCode`: `Archive` → `InvalidOperation` (not `CollectionAlreadyArchived`), Create name-conflict → `EntityAlreadyExists` (not `CollectionAlreadyExists`), not-found → generic `ResourceNotFound`. Both endpoint bases emit `AddError(message)`+`SendErrorsAsync(status)` with no RFC 9457 `extensions.errorCode` (`WriteModel.Endpoints/V1/CatalogEndpoint.cs:20-24`, read base `:20-30`). (Base-class error-code mapping is in unread `Magiq.Platform`; the absence of any `errorCode` plumbing here is the finding.)
- **COL-M3** — No request validators. `CollectionId.From`/`MediaProfileId.From` (`Guid.Parse`) and the `ValueOf` VOs throw on malformed input → unhandled → 500 where 400/404/422 is expected. In bulk, one invalid name/`DefaultMediaProfileId` throws inside the endpoint's `.Select` mapping (`BulkCreateCollectionsEndpoint.cs:55-61`) and **500s the whole batch** instead of per-item `failed`.
- **COL-M4** — `TenantId` leaked to clients in `GetCollectionByIdResponse` (`:6,22`) and `CollectionSummaryModel` (`:6,21`); list/detail also expose fields beyond the spec summary shape.
- **COL-M5** — `ListCollections` is sorted by name (`CollectionByNameIndexSchema.WriteSortKeyValue` = `{name}#{id}`) and ignores `sortBy`/`sortOrder`; the spec default is `createdAt desc` "backed by media-collections GSI on createdAt" (`api-conventions.md:262`) — no such createdAt index exists.
- **COL-M6** — `GET /collections/public` requires a JWT (uses `context.TenantId`, advertises 401) and is tenant-scoped; spec says unauthenticated and across all owners (`collection.api.md:229`). (Challenge to spec: anonymous cross-tenant public browsing is questionable on a compliance platform — but code and spec must be reconciled either way.)

### Low

- **COL-L1** — `Create` double-writes description (COL-D2); `CollectionCreated` carries `Description` the spec payload omits.
- **COL-L2** — `ArchiveCollectionResponse` is defined but never sent (204 no-body); field misspelled `ArchiveAt`.
- **COL-L3** — `ArchiveCollectionEndpoint` summary says "already-archived… return 409" while the response doc + code + catalog say 422 (`ArchiveCollectionEndpoint.cs:32,38`).
- **COL-L4** — Integration-event record naming/timestamp/`EventVersion` divergence from the context-overview contracts (COL-FP1).
- **COL-L5** — Spec's `ICollectionQueryService`/`IMediaProfileReadModel` don't exist; replaced by `INameReservationService`/`IMediaProfileRepository`.
- **COL-L6** — `CollectionName` regex permits leading/trailing whitespace (no trim) and uses a non-static instance `Regex`; `Tag` rejects single-character tags (regex needs ≥2 chars) yet the length guard says `<= 48` while the regex allows up to 50 — minor inconsistencies.
- **COL-L7** — Read-model record field `Id` vs read-model spec `CollectionId`; detail table `media-collection` vs spec `media-collection-detail`.
- **COL-L8** — `pageSize` 100 cap and non-negative check not enforced at the endpoint (relies on unverified `PagerParameters`).

---

## 13. Design Flaws

1. **Archive is modelled twice, incompatibly.** The aggregate/read-model treat archive as a soft, read-layer, reversible flag; the fan-out worker treats it as an irreversible write-side cascade over child aggregates (COL-C2). These cannot both be true. For a regulated-records system this is the single biggest architectural defect — it silently converts a reversible visibility flag into permanent bulk mutation, and couples Collection archive to the entire Folder/MediaItem invariant surface.
2. **Non-transactional dual writes between the event store and the uniqueness registry are pervasive and inconsistently ordered** (COL-H6). Every create/rename/archive handler is a partial-failure window; the spec's ambient-transaction design was not implemented.
3. **`PATCH` is decomposed into independent commands** (COL-H5), trading atomic partial-update semantics for three separate transactions and concurrency windows.
4. **The fan-out consumer treats "child archive failed" and "already done" identically by swallowing the `Result`** (COL-FC2) — accidental idempotency that also erases genuine failures with no DLQ/observability.
5. **Authorization and validation are entirely absent layers** (COL-C1, COL-M3) — the API cannot emit the 403/400/422 responses its own Swagger advertises.
6. **The error contract is bypassed at the boundary** — generic `AddError(message)` with no `errorCode` collapses the catalog's machine-discriminable codes (COL-M2).

---

## 14. Design Gaps

- **No authorization layer** (endpoints or handlers) — the largest gap.
- **No request-validation layer** (no FluentValidation), so malformed IDs/names/tags 500 instead of 400/422.
- **No RFC 9457 `errorCode` emission** from the endpoint bases.
- **No owner filter** on `GET /collections` and no owner-scoped index.
- **No archived guard** on Visibility/Description/Tag/DefaultProfile mutations.
- **No published/owner guard** on default-profile at Create/Bulk.
- **No DLQ / retry / reload-before-retry** around the swallowed fan-out failures; **no sharding/checkpointing** despite the spec describing it.
- **No `UnarchiveCollection`** (spec-acknowledged) — made worse by COL-C2's irreversible child archival.
- **No createdAt-sorted list index** despite the api-conventions default.
- **No transactional reservation+event write** (ambient `ITransactionScope`).

---

## 15. Missing Features

- **Ownership enforcement** on every write and read (commands lack `ActorId`; queries lack owner scoping).
- **`ownerId` filter** on `GET /collections` (route documented, param not implemented).
- **Read-model-only archive fan-out** (`IsAccessible` propagation) to replace the write-side cascade.
- **Archived-state guard** on `SetVisibility`/`UpdateDescription`/`Tag`/`SetDefaultMediaProfile`.
- **Default-profile `IsPublished` + owner guard** in Create and Bulk.
- **FastEndpoints/FluentValidation validators** (ID well-formedness, name/description length, tag rules, `pageSize` cap, per-item bulk validation).
- **Coded domain errors** (`CollectionAlreadyArchived`, `CollectionAlreadyExists`, `CollectionNotFound`, `CollectionArchived`, `MediaProfileNotPublished`) mapped to `errorCode` + RFC 9457.
- **`UnarchiveCollection`** (spec-deferred, but required to honour the reversibility guarantee once COL-C2 is fixed).

---

## 16. Recommendations (prioritised)

### 1 — Correctness
- **R1 (Critical).** Rewrite the archive fan-out to update **read models only** (`IsAccessible=false` on `media-items`/`media-item-detail`/OpenSearch), leaving Folder/MediaItem event streams untouched, per `collection.scenarios.md` C-3 (COL-C2). Make the consumer observe/propagate failures (throw → SQS retry/DLQ) and bound parallelism / shard (COL-FC2/FC3).
- **R2 (High).** Make `PATCH` atomic — a single `UpdateCollectionCommand` (or one ambient transaction) (COL-H5); fix the summary projector to leave `CreatedAt` untouched on `CollectionDefaultProfileSet` (COL-H4).

### 2 — Data Integrity
- **R3 (High).** Adopt the spec's ambient-transaction reservation pattern so name reservation and event append commit atomically; fix the release-before-save / swap-before-save ordering (COL-H6).
- **R4 (High).** Add the `IsArchived` guard to Visibility/Description/Tag/DefaultProfile (COL-H3/COL-D1).

### 3 — Security
- **R5 (Critical).** Implement PERM-1: thread `ActorId` through every mutating command; enforce `actor.Id == OwnerId` in write handlers and owner-or-public in `GetCollectionById`; add `ownerId` scoping to `ListCollections`; return 403 with `errorCode` (COL-C1/H1/H2).
- **R6 (Medium).** Decide and align the `GET /collections/public` auth/scope contract (COL-M6); add the profile-owner check on default-profile (COL-M1).

### 4 — Domain Modelling
- **R7 (Medium).** Return catalog-coded `DomainError`s (`CollectionAlreadyArchived`/`CollectionAlreadyExists`/`CollectionNotFound`) and drop the redundant `Description` double-write (COL-D2/D3/M2).

### 5 — Lifecycle
- **R8 (Medium).** Add `UnarchiveCollection` (once R1 makes archive reversible again) to close the terminal dead-end (COL-L-Life2).

### 6 — API
- **R9 (High).** Emit RFC 9457 problem-details with `errorCode`; stop flattening read errors to 500; add FluentValidation validators so malformed IDs/tags return 400/422 not 500 (COL-M2/M3).
- **R10 (Medium).** Remove `TenantId` from `GetCollectionByIdResponse`/`CollectionSummaryModel`; add `ownerId` param; reconcile list default sort with the conventions doc (COL-M4/M5).

### 7 — Events
- **R11 (Low).** Reconcile the `*IntegrationEvent` record names / timestamp fields / `EventVersion` with the context-overview contracts before the wiki publish; suppress mutation events on archived collections once R4 lands (COL-FP1/FP2).

### 8 — Maintainability
- **R12 (Low).** Delete the unused `ArchiveCollectionResponse` (fix the `ArchiveAt` typo if retained); fix the Archive endpoint's 409-vs-422 doc contradiction; update the spec's `ICollectionQueryService`/`IMediaProfileReadModel`/`media-collection-detail` references to match code (COL-L2/L3/L5/L7).

### 9 — Performance
- **R13 (Medium).** Bound the fan-out worker's parallelism and add checkpoint-per-page/sharding as the spec describes (COL-FC3).

### 10 — Scalability
- **R14 (Medium).** Add an owner- and createdAt-scoped GSI for `ListCollections` so owner-scoped, createdAt-sorted paging is index-backed rather than a tenant-wide scan+filter (COL-H1/M5).

---

### Top 5 before production
1. **COL-C1 / R5** — ownership authorization is entirely absent; any tenant user can read/list/mutate/archive any other owner's collection, including reading Private ones.
2. **COL-C2 / R1** — archive hard-archives every child Folder/MediaItem aggregate (irreversible), the exact opposite of the read-model-only, reversible spec.
3. **COL-H4 / R2** — the summary projector overwrites `CreatedAt` on `CollectionDefaultProfileSet`, corrupting list ordering/data.
4. **COL-H3 / R4** & **COL-H6 / R3** — archived collections stay mutable, and reservation/event writes are non-atomic (orphaned/lost name reservations).
5. **COL-FC2 / R1** — the archive fan-out swallows every child-archive failure with no DLQ → silent partial archives.
