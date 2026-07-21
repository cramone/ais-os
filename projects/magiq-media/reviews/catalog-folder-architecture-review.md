# Folder — Aggregate Architecture Review (Specification vs Repository)

_Context: **Catalog** (bounded context) — magiq-media_
_Aggregate: **Folder**_
_Reviewer role: Principal Domain Architect (DDD / CQRS / Event Sourcing / API) and Senior Software Engineer_
_Date: 2026-07-19_
_Scope: `docs/spec/contexts/Catalog/aggregates/Folder/**` (api, read-model, write-model) + shared conventions (api-conventions, error-catalog, security-scenarios, bulk-operations, media-types), `docs/adrs/catalog-domain-invariants.md` (ADR-006), `docs/spec/contexts/Catalog/{context-overview,business-scenarios}.md` vs `src/modules/Catalog/**` Folder slice: `Catalog.Domain/Aggregates/Folders/**` (aggregate, 9 events + marker, snapshot, VOs), `Catalog.Domain/ValueObjects/{FolderId,PathNormalizer,MetadataFieldType,Attributor}.cs`, `Catalog.Domain/Repositories/IFolderRepository.cs`, `Catalog.Contracts/Events/Folders/**`, `Catalog.WriteModel/Commands/Folders/**` (11 command folders incl. 2 bulk), `Catalog.WriteModel/Services/Folders/**`, `Catalog.WriteModel/IntegrationEvents/Publishing/Mappers/FolderDomainEventMapper.cs`, `Catalog.WriteModel.Infrastructure/{Locking/**, Services/Folders/FolderArchiveFanOutWorker, Repositories/FolderRepository, Indexes/Projectors/Folders/**, Indexes/ReferenceModels/Folders/**}`, `Catalog.WriteModel.Endpoints/V1/Folders/**`, `Catalog.ReadModel/{Projectors,ReadModels,Queries}/Folders/**`, `Catalog.ReadModel.Endpoints/V1/Folders/**`_

> **Method:** **63 production `.cs` files** in the Folder slice were read in full — the aggregate (9 events, snapshot, `FolderName`/`FolderStatus`), all 11 command+handler pairs (incl. `BulkCreateFolders`, `BulkCreateFoldersByPath`), the creation-lock service + table + migration, the archive fan-out worker, the folder repository, all 8 write-side index projectors (child-folders, media-items ×4 incl. move-added/-removed/-archived, registration-count) and their 3 reference models, all 3 read projectors (detail/summary/child-summary), the read models, the 4 query handlers, the domain→integration mapper + 4 integration-event contracts, and the write/read endpoints + DTOs — compared against `folder.write-model.md`, `folder.read-model.md`, `folder.api.md`, the shared conventions/error-catalog, and ADR-006. Collection / MediaItem / Registration code was consulted only where Folder references it directly (root-folder keying by `CollectionId`, the archive fan-out's `ArchiveFolderCommand`/`ArchiveMediaItemCommand` re-dispatch, the media-items & registration counters). Findings hinging on unread `Magiq.Platform` base behaviour (`CommandHandler` error-code→HTTP mapping, `ProjectionHandlerBase` `MissingCurrent`/`ProjectedVersion` monotonicity, `PagerParameters` cap, `INameReservationService` transactionality) are flagged as such. Cross-references to the completed **Collection** (`/tmp/catalog-collection-architecture-review.md`) and **MediaItem** (`/tmp/catalog-mediaitem-architecture-review.md`) reviews are used for shared cross-cutting findings rather than re-deriving rationale.

---

## 1. Aggregate Summary

`Folder` is the hierarchy aggregate of the Catalog context — a container that belongs to exactly one `Collection`, carries an optional parent `Folder`, a free-form `MetadataChangeset` (draft/commit), an owner denormalised from the Collection, open/close business dates, and archive state. It deliberately holds **no** child-folder or media-item ID lists (membership lives on the child read models and on write-side reference indexes). Its event stream is flat: create → rename / move / describe / metadata-set / metadata-commit / close → archive.

Structurally the slice is the **largest and most machinery-heavy** aggregate reviewed: `EventSourced<Folder, FolderId, FolderSnapshot>` + `ITenantScoped`, `[AggregateType("media.folder")]`, 9 domain events all wired in `When<>`, a snapshot, command-per-folder handlers (including two genuinely sophisticated bulk paths with topological-sort/wave scheduling and `mkdir -p` tree dedup), a per-collection DynamoDB **creation lock**, an **archive fan-out worker**, three read projectors with **complete event coverage**, and a fleet of **eight write-side reference-index projectors** (child-folders, four media-items variants, registration-count). Several things prior reviews flagged as defects are done **correctly** here: `TenantId`/actor/timestamps are sourced from `IExecutionContext` (never the body), event timestamps are passed in (deterministic replay — no wall-clock in event emission), the detail projector has essentially total coverage and is idempotent, and the metadata field endpoint correctly returns 400 on unknown `fieldType` and 422 on type-mismatch.

However, the aggregate is **not production-ready**. The review surfaced **3 Critical** and a large cluster of **High** issues in six themes:

1. **Authorization is absent end-to-end, and folder ownership is derived from the caller.** No endpoint declares a policy; no handler performs the PERM-1 owner check; `CreateFolder` sets `OwnerId = caller` (not denormalised from the Collection) and never even loads the Collection — so any authenticated tenant user can create folders in any owner's collection, and rename/move/archive/close any folder.
2. **Move has no cycle guard and no immutability guard.** Moving a folder into its own descendant creates a hierarchy cycle (only self-move is blocked); the endpoint Swagger and spec both claim a circular-reference guard that does not exist. Cross-collection moves are accepted and `collectionId` is taken from the request body.
3. **Archive is an irreversible, failure-swallowing, self-recursive cascade.** The fan-out re-dispatches `ArchiveFolderCommand` per descendant (re-entering the same handler and re-walking the whole subtree), archives descendants **before** the root's own guard, swallows every child failure, and enumerates the subtree from eventually-consistent indexes — so partial/incomplete archives are silent with no DLQ.
4. **Reference-index/counter coverage gaps corrupt the hierarchy invariants.** The media-items index never handles `MediaItemAssignedToFolder`; a whole parallel `FolderRegistrationIndex` is maintained but unused by the archive gate; the registration gate itself contradicts ADR-006.
5. **The over-engineered creation lock** adds a per-collection serialization bottleneck, an undocumented 503, a 1-minute TTL that can expire mid-bulk, and a migration that never enables DynamoDB TTL — all to guard uniqueness that the atomic reservation registry already guarantees.
6. **The error/validation/atomicity contract is unmet.** Generic `InvalidOperation` everywhere (no `FolderAlreadyArchived`/`FolderAlreadyClosed`/`DepthExceeded`/`CircularFolderReference` codes, no RFC 9457 `errorCode`), no validators (malformed IDs → 500), `TenantId` leaks in the GET response, and every reservation/counter write is a non-transactional dual write.

As with Collection and MediaItem, the aggregate core is sound; nearly every Critical/High defect lives in the **handler / fan-out / lock / projector orchestration layer** around it.

---

## 2. Aggregate Analysis

### `Folder` (Aggregate Root) — `Catalog.Domain/Aggregates/Folders/Folder.cs`

`EventSourced<Folder, FolderId, FolderSnapshot>`, `ITenantScoped`, `[AggregateType("media.folder")]`. Single aggregate; no child entities (correct — child/membership relations are read-model/reference-index-only). Healthy VO surface: `FolderId`, `FolderName` (`ValueOf<string>`, regex-validated), `FolderStatus` (enum), `CollectionId`, `MemberId` (`OwnerId`), `MetadataChangeset`/`MetadataValue`, `Attributor`, `TenantId`.

**Key state:** `TenantId` (first field of `FolderCreated`, set once), `CollectionId` (immutable), `ParentFolderId?`, `Name`, `Description?`, `OwnerId`, `Status` (`Active`|`Archived`), `Metadata` (`Current`+`Draft?`), `OpenedDate?`, `ClosedDate?`, `ClosedAt?`, `ArchivedDate?`, `Originator?`. `IsArchived => Status == Archived`; `IsClosed => ClosedAt.HasValue`.

**Invariants enforced in the aggregate (correct):**
- `Archive()` blocks re-archive (`IsArchived` guard, `Folder.cs:112`); `Close()` blocks re-close (`IsClosed` guard, `:129`); `CommitMetadata()` blocks when archived and when no draft exists (`:141-149`).
- `SetMetadataField`/`SetMetadataBatch` block when archived (`:190-193, 207-210`).
- Event timestamps are all passed in (`archivedAt`, `renamedAt`, `movedAt`, `committedAt`, `updatedAt`) and applied deterministically — **no wall-clock in event emission** (contrast AssetManagement A-D2). The one `DateTimeOffset.UtcNow` (`TakeSnapshot`, `:237`) is benign snapshot metadata.
- `TenantId` is the first field of `FolderCreated` and set once in `Apply` (`:288`); `CollectionId` is never mutated by any `Apply` (immutable, correct).

**Aggregate-level defects (detailed in §12–13):**
- **FOL-D1 (High, correctness).** `Rename()` and `Move()` have **no `IsArchived` guard** (`Folder.cs:173-181, 161-169`). The write-model invariant table (`folder.write-model.md:56-57`) requires "Not archived" for both `Rename` and `Move`. An archived folder can be renamed and re-parented indefinitely — "terminal" is not terminal, and the rename/move still publish integration events for a dead node (§10). `UpdateDescription()` (`:244-252`) likewise has no archived guard.
- **FOL-D2 (Medium, dead/confusing branch).** `Move(collectionId, newParentFolderId, movedAt)` emits `FolderMoved` when `CollectionId != collectionId` (`:163-166`), but `Apply(FolderMoved)` never changes `CollectionId` (`:317-321`), and the emitted event carries the *old* `CollectionId`. The collection-change branch is unreachable-into-state — it only exists to let a handler pass a mismatched collection id, which the aggregate silently ignores while still emitting an event. Cross-collection immutability (`FolderCollectionImmutable`, spec `:19`) is neither enforced nor needed here — it should be a guard, not a no-op branch.
- **FOL-D3 (Low, generic errors).** Every guard returns `DomainError.InvalidOperation` (422) with a prose message: `Archive` → `"Folder is already archived."` (not `FolderAlreadyArchived`), `Close` → `"Folder is already closed."` (not `FolderAlreadyClosed`), `CommitMetadata` → `"No pending metadata draft…"`. The `folder.api.md` error bodies explicitly advertise `errorCode: "FolderAlreadyArchived"` / `"FolderAlreadyClosed"` (`:136-141, 159-166`) — unreachable in code (§12 FOL-M1).
- **FOL-D4 (Low, stale comments).** The `Archive()` doc-comment (`:103-109`) describes a "no active (non-archived) child folders" check and an "isAccessible = false … via FolderItemsIndex GSI" fan-out that do not match the implemented behaviour (active-**registrations** blocking gate + write-side aggregate cascade). It also references a `FolderHierarchyService`/`FolderDomainService` that does not exist. `Move()`'s comment references `IFolderHierarchyService` circular/cross-collection checks that are never wired (§12 FOL-C2).

---

## 3. Lifecycle Analysis

`FolderStatus` has only `Active` and `Archived`. **"Closed" is not a status** — it is an orthogonal boolean derived from `ClosedAt`, so a closed folder remains `Status == Active`. There is no `Reopen`/`Unarchive`.

### State machine (reconstructed from `Folder.cs` guards + `Apply` handlers)

```text
        CreateFolder  ── under per-collection creation lock ──►  [Tier-1 name check]
        (handler: parent exists, depth≤10, name unique)          [depth counter ≤10]
                              │                                   [Tier-2 ReserveAsync]
                              ▼
                    ┌────────────────────────────┐
                    │           Active            │   Rename ⚠(no archived guard, FOL-D1)
                    │   (Status = Active)         │   Move   ⚠(no archived/cycle/x-collection guard)
                    │                             │◄── UpdateDescription ⚠(no archived guard)
                    │   ClosedAt = null           │   SetMetadataField / SetMetadataBatch ✔(archived-guarded)
                    │                             │   CommitMetadata ✔(archived-guarded, needs draft)
                    └───────┬──────────────┬──────┘
             Close()        │              │  Archive()  (guard: not already archived;
        (guard: not closed) │              │             handler: no active registrations in subtree)
                            ▼              ▼
                ┌───────────────────┐   ┌────────────────────────────────┐
                │ Active + Closed   │   │           Archived             │
                │ (ClosedAt set;    │   │  Status=Archived, ArchivedDate │
                │  Status STILL     │   │  [terminal]                    │
                │  Active — still   │   │  ⚠ still Renamable/Movable/     │
                │  fully mutable,   │   │     Describable (FOL-D1)        │
                │  incl. Archive)   │   │  ⚠ descendants archived by      │
                └───────────────────┘   │     fan-out BEFORE this guard   │
                            │           │     (FOL-H6), failures swallowed│
                            └──────────►│     (FOL-C3)                    │
                                        └────────────────────────────────┘
                                          ╳ No Unarchive / Reopen command (permanent dead-end)
```

### Lifecycle issues
- **FOL-Life1 (High) — `Archived` is a leaky terminal state (FOL-D1).** Rename/Move/UpdateDescription have no archived guard, so a client keeps mutating an archived folder and those mutations still publish `FolderRenamed`/`FolderMoved` integration events downstream to Search/Discovery, resurrecting a dead node.
- **FOL-Life2 (Medium) — No unarchive/reopen path.** Archive is terminal (spec-consistent, no `UnarchiveFolder` in v1) but the archive cascade hard-archives every descendant *aggregate* (§12 FOL-C3), so — as with Collection COL-C2 — there is no route back for the folder or its subtree even if one were added.
- **FOL-Life3 (Low) — `Close` is orthogonal and under-constrained.** `Close()` guards only `IsClosed`, not `IsArchived`, so an archived folder can still be "closed"; and because closed is not a status, a closed folder remains fully mutable (rename/move/metadata/archive all still apply). Whether close should freeze anything is undefined by the spec — flag for a product decision.

---

## 4. Commands

11 command/handler pairs. `⚠` marks a command with at least one finding (detailed in §12–15).

| Command | Handler | Trigger | Notes |
|---|---|---|---|
| CreateFolderCommand | CreateFolderHandler | API `POST /collections/{id}/folders` | ⚠ owner=caller (not from Collection); **no Collection existence/archived check**; **no archived-parent check**; reserve→increment→save non-atomic; 503 on lock |
| RenameFolderCommand | RenameFolderHandler | API `PATCH` (name) | ⚠ no owner check; no archived guard (FOL-D1); swap-before-save non-atomic; no ExpectedVersion |
| MoveFolderCommand | MoveFolderHandler | API `PUT /parent` | ⚠ **no cycle/descendant guard (FOL-C2)**; **cross-collection accepted, `collectionId` from body (FOL-H1)**; **subtree depth/counters ignored (FOL-H2)**; no archived guard; move-before-save non-atomic |
| ArchiveFolderCommand | ArchiveFolderHandler | API `POST /archive` **+ fan-out re-entry** | ⚠ **cascade-before-guard (FOL-H6)**; **release-before-save**; owner check absent; registration gate contradicts ADR-006 (FOL-M2) |
| CloseFolderCommand | CloseFolderHandler | API `POST /close` | ⚠ no owner check; allowed on archived folder; generic error |
| UpdateFolderDescriptionCommand | UpdateFolderDescriptionHandler | API `PATCH` (description) | ⚠ no owner check; no archived guard |
| SetFolderMetadataFieldCommand | SetFolderMetadataFieldHandler | API | ⚠ no owner check; type-resolve → 422 ✔ |
| SetFolderMetadataBatchCommand | SetFolderMetadataBatchHandler | API | ⚠ no owner check; validates all-before-emit ✔ (atomic) |
| CommitFolderMetadataCommand | CommitFolderMetadataHandler | API | ⚠ no owner check; guards archived+draft ✔ |
| BulkCreateFoldersCommand | BulkCreateFoldersHandler | API `POST /bulk` | ⚠ **non-existent external parent silently created (FOL-H8)**; reserve-many→save non-atomic; owner=caller; 503 on lock |
| BulkCreateFoldersByPathCommand | BulkCreateFoldersByPathHandler | API `POST /bulk-paths` | ⚠ **silently auto-creates Collections (FOL-M9)**; non-atomic; owner=caller; 503 on lock |

**Cross-cutting command issues:**
- **No mutating command carries an owner-comparison identity that any handler checks.** `Create`/`Bulk` carry `OwnerId` but it is set to the caller by the endpoint (not the Collection owner — §12 FOL-C1); `Rename`/`Move`/`Archive`/`Close`/metadata commands carry no actor at all. PERM-1 is impossible downstream.
- **No command carries `ExpectedVersion`.** The write-model invariant table (`folder.write-model.md:25`) says "`ExpectedVersion` must match current `Version` → `ConcurrencyConflict`" for **all** mutating commands, and the spec `RenameFolderCommand`/`MoveFolderCommand`/`ArchiveFolderCommand` signatures list `ExpectedVersion` (`:88-90`). None of the code commands carry it → no client-supplied optimistic-concurrency precondition (§12 FOL-M-conc).
- **Handlers return generic errors** (`InvalidOperation`, `EntityAlreadyExists`, `ResourceNotFound`, `ExternalServiceUnavailable`) — no catalog codes / `errorCode` (§12 FOL-M1).
- Command set maps 1:1 to aggregate methods; no duplicate/redundant commands. The `SetMetadataBatch` validate-all-before-emit and the metadata type-resolution are good.

---

## 5. Queries

4 read paths — `GetFolderById`, `ListFolders` (by collection+parent), `GetFolderHierarchy` (whole collection, flat), `ListChildrenInFolder` (unified child folders + media items).

| Query | Paging | Auth / Scope | Notes |
|---|---|---|---|
| GetFolderByIdQuery | n/a | ⚠ none | returns any tenant folder regardless of owner/collection-visibility; response leaks `TenantId` (§8) |
| ListFoldersQuery | cursor (ADR-014 ✔) | ⚠ none | `Matches` = `TenantId + CollectionId` only — no owner scoping; returns archived folders (no status filter) |
| GetFolderHierarchyQuery | n/a (all-on-pages loop) | ⚠ none | pages the whole collection into memory (`FromCursor(cursor,1000)` loop, `GetFolderHierarchyHandler:24-29`); returns full `FolderSummaryReadModel` rows though spec says "shallow: IDs + names only"; `nameContains` filter not applied in the handler |
| ListChildrenInFolderQuery | cursor (ADR-014 ✔) | ⚠ none | `Matches` excludes `Status == "Archived"` ✔; no owner scoping |

**Query issues:**
- **CQRS boundary is clean** — handlers return read-model DTOs via `IReadModelReader`; no aggregates/event payloads cross the boundary; cursor-only pagination, no total count (ADR-014 ✔). Good.
- **No owner/visibility scoping** on any query (§12 FOL-C1). Folders inherit their owner from the Collection, and the spec does not define folder-level visibility as sharply as Collection, so this is a lower-emphasis instance of the shared read-auth gap — but `GetFolderById`/`ListFolders` still return any tenant folder unconditionally, and the hierarchy/children endpoints advertise `403` that no code path emits.
- **`GetFolderHierarchy` is unbounded** — it accumulates every folder in the collection into one in-memory `List` in a single Lambda invocation. For a large tenant collection this is a memory/timeout risk; the "shallow id+name" shape the spec promises is not honoured (full summary rows are returned).
- **`ListFolders` returns archived folders** (no `IsArchived` filter) — the API list example shows `isArchived` per row, so this may be intentional, but there is no way to exclude them.

---

## 6. API Endpoints

Spec (`folder.api.md`) vs implementation (routes registered in the endpoint classes; base `CatalogEndpoint`):

| Spec route | Verb | Impl? | Impl status | Spec status | Note |
|---|---|---|---|---|---|
| /v1/collections/{collectionId}/folders | POST | ✔ | 201/400/401/403/404/409/422/**503** | 201/400/401/404/409/422 | ⚠ extra 503 (lock); no Collection existence/owner check; owner=caller (FOL-C1) |
| /v1/collections/{collectionId}/folders/bulk | POST | ✔ | 201/202/**422**/**503** | 201/202/400 | ⚠ in-batch cycle → 422 (spec 400); non-existent ext. parent silently created (FOL-H8) |
| /v1/collections/{collectionId}/folders/bulk-paths | POST | ✔ | 201/202/**503** | 201/202/400 | ⚠ silently auto-creates Collections (FOL-M9) |
| /v1/collections/{collectionId}/folders/import | POST | ✖ **missing** | — | 202 | async import (BulkFolderImportJob) not implemented — deferred per CLAUDE.md |
| /v1/collections/{collectionId}/folders/hierarchy | GET | ✔ | 200 | 200 | ⚠ unbounded; `nameContains` not applied |
| /v1/folders/{folderId} | PATCH | ✔ | 204/400/404/409/422 | 204/400/404/409 | ⚠ non-atomic 2-command (rename+description, FOL-M7) |
| /v1/folders/{folderId}/parent | PUT | ✔ | 204/…/409/422 | 204/422 | ⚠ no cycle guard (FOL-C2); cross-collection + body `collectionId` (FOL-H1) |
| /v1/folders/{folderId}/archive | POST | ✔ | 204/401/403/404/422 | 204/404/422 | ⚠ cascade swallows failures (FOL-C3) |
| /v1/folders/{folderId}/close | POST | ✔ | 204/404/422 | 204/404/422 | ok (generic error code) |
| /v1/folders/{folderId}/metadata/{fieldName} | PATCH | ✔ | 204/400/404/422 | 204/400/404/422 | ✔ 400 on unknown fieldType, 422 on type-mismatch |
| /v1/folders/{folderId}/metadata | PUT | ✔ | 204/400/404/422 | 204/400/404/422 | ✔ validate-all-before-emit |
| /v1/folders/{folderId}/metadata/commit | POST | ✔ | 204/404/422 | 204/404/422 | ok |
| /v1/folders/{folderId} | GET | ✔ | 200 | 200 | ⚠ leaks `TenantId` (§8) |
| /v1/folders/{folderId}/children | GET | ✔ | 200 | 200 | ok (excludes archived) |
| /v1/folders?collectionId=&parentFolderId= | GET | ✔ | 200 | 200 | ⚠ no owner scoping; includes archived |

**Endpoint issues:**
- **No endpoint declares authorization** — grep of all Folder endpoints + `CatalogEndpoint` base finds zero `Roles/Policies/Permissions/RequireActorType/AllowAnonymous/PreProcessor`. Every endpoint's Swagger advertises a `403` no code path can emit. (§12 FOL-C1)
- **RFC 9457 `errorCode` never emitted** — endpoints call `SendDomainErrorAsync(error)`; the shared `CatalogEndpoint` bases emit `AddError(message)`+`SendErrorsAsync(status)` with no `extensions.errorCode`, and the read base flattens to `NotFound→404 / _→500` (established in the Collection/MediaItem reviews; the same bases are used here). The explicit `FolderAlreadyArchived`/`FolderAlreadyClosed` error bodies in `folder.api.md` are unreachable. (§12 FOL-M1)
- **Extra/undocumented 503** on the three create endpoints (creation-lock unavailable) — not in `folder.api.md`'s error lists (§12 FOL-M5). At least the create endpoint documents it in its own Swagger.
- **Verb/route/version:** all *registered* routes match the spec and every endpoint is `Version(1)`. Only `/import` (async job) is missing (deferred). `TenantId`/actor/`OccurredAt` correctly sourced from `IExecutionContext` (genuine positive).

---

## 7. Request DTO Review

| DTO | Findings |
|---|---|
| CreateFolderRequest | `Name`/`CollectionId = null!`; no validator → omitted `name`/`collectionId` NRE at `FolderName.From`/`CollectionId.From`; malformed `parentFolderId` → `FolderId.From`→`Guid.Parse` throws → 500 |
| MoveFolderRequest | `CollectionId = null!` **and settable from the request body** — the move's collection id is client-supplied, not derived from the folder (FOL-H1); omitted → `CollectionId.From(null)` → 500 |
| PatchFolderRequest (+ Converter) | Custom converter tracks `NameSet`/`DescriptionSet` for true partial semantics — **good design**; endpoint enforces "≥1 field" and "name not null" → 400 ✔; no length validation |
| SetFolderMetadataFieldRequest / SetFolderMetadataBatchRequest | endpoint validates `fieldType` enum → 400 ✔; `value` is raw `JsonElement`, type-checked in the handler → 422 ✔ |
| BulkCreateFoldersRequest / BulkCreateFoldersByPathRequest | per-item/per-path; batch-size 200 cap enforcement not observed in handler/endpoint (spec `MaxFoldersPerRequest = 200`) |

**Cross-cutting:**
- **No FluentValidation validators anywhere** in the slice. `FolderId.From`/`CollectionId.From` (`Guid.Parse`) and `FolderName.From` (`ValueOf` throws) throw on malformed input → unhandled → **500** where the spec expects 400/404/422 (§12 FOL-M8). The two endpoint-level checks (fieldType enum → 400; PATCH "≥1 field" → 400) are the only input validation present.
- **`FolderName` regex** (`^[^<>:"/\\|?*\x00-\x1F]{1,255}(?<!\.)$`) permits **leading/trailing whitespace** (no trim) and is a non-static instance `Regex` per VO; the bulk dedup normalises with `Trim().ToLowerInvariant()` while Tier-1 `GetTakenNamesAsync` uses `Normalized()` (lower-only, no trim) — `"Foo"` vs `"Foo "` can both reserve via the single-create path (§13, FOL-L6/L8).

---

## 8. Response DTO Review

| DTO | Findings |
|---|---|
| CreateFolderResponse | `(Id, Name, Description, CollectionId, ParentFolderId, CreatedAt, OpenedDate, ClosedDate)` — matches spec 201 body ✔ |
| GetFolderByIdResponse | **leaks internal `TenantId`** (`:7, :29`); adds `ArchivedDate`, `Originator`, `MetadataAttributor` beyond the spec GET body (`folder.api.md:288-308`) |
| FolderSummaryModel / FolderChildSummaryModel (list items) | shapes broadly match the api list examples; child summary carries `childType`/`status` per spec |
| ArchiveFolderResponse / CloseFolderResponse / CommitFolderMetadataResponse | **defined but never sent** — the endpoints return 204 no-body (dead DTOs, FOL-L5), mirroring Collection COL-L2 |

**Cross-cutting:**
- **`TenantId` leakage** in `GetFolderByIdResponse` — a multi-tenancy boundary value that must never round-trip to clients (§12 FOL-M6), identical to Collection COL-M4 / MediaItem MI-M10.
- Identifier naming is otherwise consistent (`id`, `collectionId`, `parentFolderId`).

---

## 9. Domain Events & Projection Coverage

9 domain events, all registered in `Folder`'s `When<>` block (`Folder.cs:24-32`). Publisher = `Folder` aggregate.

**Projection coverage — read projectors AND write-side reference-index projectors (verified against every projector):**

| Domain event | Detail (`media-folder-detail`) | Summary (`media-folders`) | ChildSummary (`child-items`) | Child-Folders idx (`FolderFoldersIndex`) | Media-Items idx (`FolderMediaItemsIndex`) |
|---|---|---|---|---|---|
| `FolderCreated` | ✔ INSERT | ✔ INSERT | ✔ INSERT | ✔ Upsert-merge (add child) | — (n/a) |
| `FolderRenamed` | ✔ Name | ✔ Name | ✔ Name | — | — |
| `FolderMoved` | ✔ Parent+Coll | ✔ Parent+Coll | ✔ re-parent | ✔ MoveAdded(new)/MoveRemoved(old) | — |
| `FolderDescriptionUpdated` | ✔ Description | ✔ UpdatedAt | — (correct) | — | — |
| `FolderArchived` | ✔ IsArchived | ✔ IsArchived | ✔ Status=Archived | ✔ SetRemove | — |
| `FolderClosed` | ✔ ClosedAt/Date | ✔ ClosedAt/Date | — (spec: intentional) | — | — |
| `FolderMetadataFieldSet` | ✔ Draft | — (n/a) | — | — | — |
| `FolderMetadataBatchSet` | ✔ Draft(merge) | — | — | — | — |
| `FolderMetadataCommitted` | ✔ Current/clear | — | — | — | — |
| _MediaItem events →_ `MediaItemCreated` | — | — | ✔ INSERT | — | ✔ SetAdd |
| `MediaItemAssignedToFolder` | — | — | ✔ re-parent | — | ✖ **NOT handled (FOL-H3)** |
| `MediaItemMoved` | — | — | ✔ re-parent | — | ✔ MoveAdded/MoveRemoved |
| `MediaItemArchived` | — | — | ✔ Status=Archived | — | ✔ SetRemove |
| `MediaItemDeleted` | — | — | ✔ DELETE | — | ✖ not handled (stale entry) |
| _Registration events →_ `RegistrationInitiated/Cancelled/Rejected` | — | — | — | — | `FolderRegistrationIndex` ✔ inc/dec — **but unused by the archive gate (FOL-M3)** |

**Read-projector strengths (genuine):**
- The **`FolderDetailProjector` has complete coverage** of all 9 folder events, is idempotent (`ProjectedVersion = e.AggregateVersion` on every write), and uses `MissingCurrentAsync()` for out-of-order safety. The best-built projector in the slice.
- Timestamps are all passed-in; no wall-clock. No version-domain mixing observed in the read projectors.
- `FolderChildSummaryProjector` keys rows by child id with `ParentFolderId` as the (re-partitioning) attribute, so folder/media-item moves correctly update the parent attribute; `FolderClosed` is intentionally not projected to the child list (matches `folder.read-model.md:107`).

**Coverage/mixing defects (detailed in §12):**
- **FOL-H3** — `FolderMediaItemsIndexProjector` handles `MediaItemCreated`/`MediaItemMoved`/`MediaItemArchived` but **not `MediaItemAssignedToFolder`** — an item created unassigned and later assigned to a folder is never added to the index, so the archive fan-out never archives it and the registration gate never sees its registrations.
- **FOL-M3** — `FolderRegistrationIndex`/`RegistrationCountIndexProjector` maintain a per-item registration count from Registration events, but `HasActiveRegistrationsAsync` reads the **`IUniquenessCounterService`** counter (`ScopeKeys.MediaItemRegistrations`/`CounterKeys.ActiveRegistrations`) instead — the index is dead relative to the gate, and the two counts can diverge.
- The child-folders index projector's version-fence subtlety (all creates have `AggregateVersion = 1`, so it uses upsert-merge for `FolderCreated` and `SetRemove` for `FolderArchived`) is correctly documented and handled — a good defensive note.

---

## 10. Integration Events

### Published (mapper `FolderDomainEventMapper.cs`)

4 mappings — `FolderArchived/Created/Moved/Renamed` → matching `*IntegrationEvent` (`MessageType("media.folder.*")`), each carrying `TenantId`, `FolderId`, `EventVersion = e.AggregateVersion`. `FolderClosed`, `FolderDescriptionUpdated`, and all metadata events are intentionally **not** published — matches the write-model published-events table (`folder.write-model.md:116-123`). Correct set.

| Issue | Severity | Detail |
|---|---|---|
| FOL-FP1 | Low (doc) | Code record names are `*IntegrationEvent` with `EventVersion` and per-event timestamps (`CreatedAt`/`MovedAt`/`ArchivedAt`); context-overview contracts (`context-overview.md:289-339`) call them `*Message` with `OccurredAt`/`ArchivedAt` and no `EventVersion`. Reconcile before the wiki publish (mirrors Collection COL-FP1). `FolderArchivedIntegrationEvent` also omits the `ParentFolderId` the domain event carries (tolerable — consumers need only the id). |
| FOL-FP2 | Low | `FolderRenamed`/`FolderMoved` are published even when raised on an *archived* folder (FOL-D1) — downstream Search/Discovery receive mutation events for a "dead" node. |

### Consumed

The Folder write model **consumes no integration events** (matches `folder.write-model.md:127-129`). However, the **archive fan-out** (`FolderArchiveFanOutWorker`) is an *intra-context command dispatcher*, not an integration-event consumer, and it exhibits the same failure-swallowing pathology the Collection fan-out consumer did:

| Issue | Severity | Detail |
|---|---|---|
| FOL-FC1 | **Critical** | `DispatchArchiveFolderAsync`/`DispatchArchiveMediaItemAsync` (`FolderArchiveFanOutWorker.cs:156-176`) only **log a warning** on `!result.IsSuccess`; `Task.WhenAll` "succeeds", `ArchiveFolderHandler` archives the root and returns 204 → partial/incomplete archive with **no DLQ, no retry, no propagation**. A checked-out or concurrently-mutated descendant silently survives under an archived parent (§12 FOL-C3). |
| FOL-FC2 | High | The worker **re-dispatches `ArchiveFolderCommand` per descendant folder**, which re-enters `ArchiveFolderHandler` → `ArchiveDescendantsAsync` → re-walks and re-archives that descendant's entire subtree. Combined with the parent's own leaf-first Phase-3 loop, this is O(depth × subtree) redundant command dispatch + registration re-checks, with unbounded `Task.WhenAll` parallelism → command-dispatch storm / Lambda timeout on deep/wide trees (§12 FOL-H7). |
| FOL-FC3 | Med | Subtree enumeration (`FolderFoldersIndex`, `FolderMediaItemsIndex`) reads **eventually-consistent** reference projections; the registration gate reads them too. A recently-created child folder/item not yet projected is missed → archive proceeds over an incomplete subtree and the "blocking" registration check can miss an item (§12 FOL-M4). ADR-006 chose strongly-consistent counters precisely to avoid this class of race. |
| FOL-FC-pos | — | **Correct:** the fan-out sources `tenantId` from the handler's `IExecutionContext`-derived command, not a payload body. |

---

## 11. Specification vs Repository Differences

| Item | Specification | Repository | Severity | Recommendation |
|---|---|---|---|---|
| Ownership guard (PERM-1) | All Folder write/read commands enforce `actor.Id == OwnerId` (`security-scenarios.md:67`) | Not enforced; commands lack actor identity; queries unscoped | Critical | Thread & enforce actor identity; 403 |
| Folder owner derivation | `OwnerId` "Denormalised from Collection at creation time" (`folder.write-model.md:38`) | `CreateFolderEndpoint` sets `OwnerId = context.Actor.Id`; Collection never loaded | Critical | Load Collection; copy its `OwnerId`; verify caller may write to it |
| Collection existence on create | `404 (collectionId … not found)` (`folder.api.md:74`) | Handler never loads/validates the Collection | High | Load + 404 on missing; reject archived collection |
| Move cycle guard | "No circular parent chains" → `CircularFolderReference` (`folder.write-model.md:21`); endpoint Swagger claims "target parent is a descendant → 409" | Only `newParent == self` checked; **no descendant/cycle check exists** | Critical | Walk ancestor chain of target (or subtree of source); reject cycles |
| Cross-collection move | `CollectionId` immutable → `FolderCollectionImmutable` (`folder.write-model.md:19`) | `collectionId` accepted from request body; `newParent.CollectionId` never compared; aggregate silently ignores | High | Reject any move whose target parent's collection ≠ folder's; do not accept collection id from body |
| Move depth | "depth ≤ 10; no circular chain" for `MoveFolder` (`folder.write-model.md:57`) | Only the moved folder's own new depth checked; **subtree height ignored**; descendant depth counters not recomputed | High | Validate max-subtree-depth on move; recompute descendant depth counters |
| Media-items index on assign | assign must reflect item under folder | `FolderMediaItemsIndexProjector` misses `MediaItemAssignedToFolder` | High | Add `MediaItemAssignedToFolder` handler |
| Archive cascade failures | (implied) reliable cascade | Fan-out swallows child failures; no DLQ | Critical | Propagate failures (throw → SQS retry/DLQ); bound parallelism; stop re-dispatching per level |
| Rename/Move on archived | "Not archived" precondition (`folder.write-model.md:56-57`) | Aggregate `Rename`/`Move`/`UpdateDescription` lack `IsArchived` guard | High | Add `IsArchived` guard to all three |
| Registration blocking gate | `FolderHasActiveRegistrations` **blocks** ArchiveFolder (`folder.write-model.md:24`) | ADR-006 says registrations are a **non-blocking warning** and "does not gate archive" (`catalog-domain-invariants.md:41`) | Medium | Reconcile spec-vs-ADR contradiction; if blocking is intended, revise ADR-006 |
| Registration source of truth | ADR-006: warning "backed by `RegistrationCountIndexProjector`" | Gate reads `IUniquenessCounterService` counter; index is unused | Medium | Pick one source; delete the dead one |
| Reservation ↔ event atomicity | Two-tier `TransactWriteItems` reservation committed with the write | Reserve/swap/move/release awaited separately; Archive **releases before save**; Create **reserves+increments before save** | High | Ambient transaction, or guard→event→reservation with idempotent/compensating ops |
| ExpectedVersion / concurrency | `ExpectedVersion` on Rename/Move/Archive → `ConcurrencyConflict` (`:25,88-90`) | No command carries `ExpectedVersion` | Medium | Thread `ExpectedVersion` (If-Match) into commands |
| Bulk non-existent parent | `ParentNotFound` per-item error (`folder.api.md:408`) | External parent that doesn't resolve → item silently created at depth 1 | High | Fail the item with `ParentNotFound` |
| bulk-paths collection auto-create | spec shows `rootFolderId`; no mention of creating collections | Handler auto-creates Private Collections from the first path segment | Medium | Document + gate, or reject when collection unknown |
| Error contract | RFC 9457 + `errorCode`; catalog codes (`error-catalog.md:76-83`) | Generic `InvalidOperation`/`EntityAlreadyExists`; no `errorCode` | Medium | Emit `errorCode`; map `FolderAlreadyArchived`/`FolderAlreadyClosed`/`DepthExceeded`/`CircularFolderReference`/`DuplicateName`/`FolderNotEmpty` |
| Creation lock | (not in spec error lists) | Adds per-collection lock + 503; 1-min TTL; TTL not enabled in migration | Medium | Reconsider necessity (registry is atomic); document 503; enable DynamoDB TTL |
| Validators | 400/422 for malformed input | None; `Guid.Parse`/VO throw → 500 | Medium | Add FluentValidation validators |
| `TenantId` in GET response | not in GET body (`folder.api.md:288-308`) | `GetFolderByIdResponse` includes `TenantId` | Medium | Remove `TenantId` from the response |
| PATCH atomicity | single partial update → 204 | 2 independent commands (rename, description) | Medium | Single command or ambient transaction |
| Bulk in-batch cycle status | request-level failure → 400 (`bulk-operations.md:31`) | Returns `InvalidOperation` → 422 | Low | Map to 400 |
| Integration record names | `*Message`, `OccurredAt`, no `EventVersion` | `*IntegrationEvent`, per-event timestamps, `EventVersion` | Low (doc) | Reconcile context-overview contracts to code |

---

## 12. Bugs

### Critical

**FOL-C1 — No authorization on any endpoint/handler/query, and folder ownership is taken from the caller (intra-tenant tampering + create-in-any-collection).**
Verified: zero auth attributes across all Folder endpoints and the `CatalogEndpoint` bases; no mutating handler compares the caller to `folder.OwnerId`; `GetFolderByIdHandler`/`ListFoldersHandler`/hierarchy/children handlers apply no owner or collection-visibility scoping. Worse, `CreateFolderEndpoint.HandleAsync` (`:63`) sets `OwnerId = MemberId.From(context.Actor.Id)` — the folder's owner becomes the *caller*, not the Collection owner the spec mandates ("Denormalised from Collection," `folder.write-model.md:38`) — and `CreateFolderHandler` **never loads the Collection at all**, so it cannot check existence, archival, or that the caller may write to it.
*Why it's a problem:* the ownership boundary is the primary intra-tenant control on a multi-tenant regulated-records platform, and here it is both unenforced and mis-derived. *Impact:* any authenticated tenant user can create folders inside **any** owner's collection (becoming their owner), and rename/move/archive/close/re-metadata **any** folder in the tenant; the `404` for a missing collection is unreachable. *Recommendation:* thread the actor into every command; load the Collection on create, copy its `OwnerId`, and enforce `actor.Id == collection.OwnerId` (or a write grant); enforce `actor.Id == folder.OwnerId` on mutations and owner-or-visibility on reads; return `NotResourceOwner`/`Forbidden` → 403 with `errorCode`.

**FOL-C2 — `MoveFolder` has no circular-reference / descendant guard → moving a folder into its own descendant creates a hierarchy cycle.**
`MoveFolderHandler.ExecuteAsync` (`:35-47`) checks only `NewParentFolderId == FolderId` (self-move). There is **no** check that the target parent is a descendant of the folder being moved, and the referenced `IFolderHierarchyService.CanMoveAsync` (spec `folder.write-model.md:105`) / `FolderHierarchyService` (aggregate comment) **does not exist**. Yet `MoveFolderEndpoint`'s own Swagger summary (`:33-35`) states "if the target parent is itself a descendant of the folder being moved, 409 is returned."
*Why it's a problem:* moving `A` under `A/B/C` detaches the `A`-subtree into a cycle; `GetFolderHierarchy` (which builds the tree in memory from `parentFolderId` links) and the archive BFS will loop or produce an orphaned, unreachable subtree — an unrecoverable hierarchy corruption. *Impact:* silent, client-triggerable hierarchy corruption; the documented invariant (`CircularFolderReference`, `folder.write-model.md:21`) and the endpoint's own 409 promise are both fiction. *Recommendation:* before emitting `FolderMoved`, walk the ancestor chain of the target parent (or the subtree of the source) and reject with `CircularFolderReference` → 422 if the source appears.

**FOL-C3 — Archive cascade swallows every descendant failure and archives descendants before the root guard → silent, partial, irreversible archives.**
`ArchiveFolderHandler` (`:34-55`) calls `fanOutWorker.HasActiveRegistrationsAsync` then `ArchiveDescendantsAsync` (which irreversibly archives all subtree media items and folders) **before** `folder.Archive()` (the `IsArchived` guard) and before the root's `SaveAsync`. `DispatchArchiveFolderAsync`/`DispatchArchiveMediaItemAsync` (`FolderArchiveFanOutWorker.cs:156-176`) only **log a warning** on failure; `Task.WhenAll` still completes, the handler archives the root and returns 204.
*Why it's a problem:* a descendant that legitimately refuses to archive (e.g. a checked-out MediaItem → `MediaItemCheckedOut`, a concurrency conflict, an out-of-order message) is silently skipped while its parent is marked archived — leaving active, now-orphaned regulated records under an "archived" folder, with no DLQ, no retry, and no error to the caller. Re-issuing archive on an already-archived folder re-runs the entire irreversible cascade before the guard rejects (§FOL-H6). *Impact:* silent partial archives, hierarchy-invariant corruption, irreversible mutation of regulated records. *Recommendation:* evaluate the root guard first; make descendant archival observe `Result` and throw retryable failures to SQS/DLQ; bound parallelism; make the whole cascade idempotent and re-drivable.

### High

**FOL-H1 — Cross-collection move accepted; `collectionId` sourced from the request body.**
`MoveFolderRequest.CollectionId` is a settable property bound from the body, and `MoveFolderEndpoint` passes it straight into `MoveFolderCommand` (`:51,56-57`). `MoveFolderHandler` uses `command.CollectionId ?? folder.CollectionId` for the reservation scope keys and passes it to `folder.Move`, and **never compares `newParent.CollectionId` to `folder.CollectionId`**. So a caller can (a) move a folder under a parent in a *different* collection, and (b) supply an arbitrary `collectionId` that re-scopes the name reservation to another collection's root. The spec makes `CollectionId` immutable (`FolderCollectionImmutable`); the aggregate's `Move` silently ignores a collection change but still emits `FolderMoved`. *Impact:* cross-collection hierarchy corruption + reservation/aggregate scope divergence. *Recommendation:* drop `collectionId` from the move contract (derive from the folder); reject any target parent whose collection differs, with `FolderCollectionImmutable` → 422.

**FOL-H2 — Move validates only the moved folder's own new depth; subtree height and descendant depth counters are ignored.**
`MoveFolderHandler` (`:49-60`) computes `newDepth = newParentDepth + 1` for the folder itself and rejects `> 10`, but never accounts for the height of the folder's **subtree**, and adjusts only the moved folder's own `Depth` counter by a delta (`:90-111`) — **descendant depth counters are never recomputed**. *Impact:* a subtree can be pushed past the 10-level limit undetected; and every descendant's depth counter becomes stale, so later `CreateFolder`/`MoveFolder` depth checks under those descendants read wrong values (wrongly admit or reject). *Recommendation:* validate `newDepth + subtreeHeight ≤ 10` on move; recompute (or delta-apply) the depth counters for the entire moved subtree.

**FOL-H3 — `FolderMediaItemsIndexProjector` never handles `MediaItemAssignedToFolder` → post-creation assignments are invisible to the archive cascade and registration gate.**
The projector handles `MediaItemCreated` (with folder), `MediaItemMoved`, and `MediaItemArchived`, but **not** `MediaItemAssignedToFolder` (the first-assignment-from-unassigned-pool event, distinct from `MediaItemMoved`). An item created unassigned and later assigned to a folder is never added to `FolderMediaItemsIndex`. *Impact:* the archive fan-out (which enumerates items via this index) never archives such items → active items orphaned under an archived folder; and `HasActiveRegistrationsAsync` never sees their registrations → the "blocking" registration gate is bypassed for them. *Recommendation:* add a `MediaItemAssignedToFolder` handler (SetAdd to the new folder), and handle `MediaItemDeleted` to remove stale entries.

**FOL-H4 — Archived folders remain renamable / movable / re-describable (no `IsArchived` guard).**
`Folder.Rename`/`Move`/`UpdateDescription` (`:161-181, 244-252`) have no `IsArchived` guard, and no handler compensates. Spec: Rename and Move require "Not archived" (`folder.write-model.md:56-57`). *Impact:* the archived terminal state is not terminal; clients keep mutating archived folders and those mutations publish `FolderRenamed`/`FolderMoved` integration events to Search/Discovery (FOL-FP2). *Recommendation:* add the `IsArchived` guard (returning a coded error) to Rename/Move/UpdateDescription.

**FOL-H5 — Name-reservation / depth-counter and event append are non-transactional dual writes across every handler.**
`CreateFolderHandler` reserves (`:90`) then increments the depth counter (`:97`) then `SaveAsync` (`:99`) — if save fails, the name is reserved and a depth counter exists for a folder that doesn't; `ArchiveFolderHandler` **releases the reservation before `SaveAsync`** (`:54-55`) — if save fails, the name is freed while the folder stays active; `MoveFolderHandler` moves the reservation and adjusts counters before save (`:82-113`); `RenameFolderHandler` swaps before save (`:53-60`); both bulk handlers reserve-many then save-many **outside the lock** (`BulkCreateFoldersHandler:307-338`, `BulkCreateFoldersByPathHandler:355-368`). *Impact:* reservation/aggregate/counter divergence on any partial failure — orphaned names/counters, or a live folder whose name is claimable by another (identical to Collection COL-H6 / MediaItem MI-H4). *Recommendation:* adopt an ambient transaction, or order guard→event-persisted→reservation with idempotent/compensating reservation+counter ops.

**FOL-H6 — Archive runs the irreversible descendant cascade before the root's own guard.**
Within `ArchiveFolderHandler`, `ArchiveDescendantsAsync` (`:40`) executes before `folder.Archive()` (`:48`). Re-issuing archive on an already-archived folder therefore re-runs the entire subtree cascade (re-dispatching archive commands for every descendant) before the aggregate guard returns `"Folder is already archived."` *Impact:* wasted, irreversible re-work and a widened race window; combined with FOL-C3/FOL-FC2 the redundant dispatches compound. *Recommendation:* load and guard the root first (idempotent short-circuit if already archived), then cascade, then persist.

**FOL-H7 — Self-recursive fan-out with unbounded parallelism → command-dispatch storm.**
`ArchiveDescendantsAsync` dispatches `ArchiveFolderCommand` per descendant folder (`FolderArchiveFanOutWorker.cs:69,156-165`), each re-entering `ArchiveFolderHandler` → `ArchiveDescendantsAsync` for that descendant's whole subtree; media-item archives across the entire subtree are fired into a single unbounded `Task.WhenAll` (`:39-58`). *Impact:* on a deep/wide tree this is O(depth × subtree) redundant command dispatches, registration re-checks, and name-reservation releases per level → Lambda timeout / throttling / cost blow-up. *Recommendation:* have the worker archive descendant *aggregates* directly (single pass, leaf-first) without re-dispatching the full `ArchiveFolderCommand`; bound `MaxDegreeOfParallelism`; checkpoint per level.

**FOL-H8 — Bulk create silently accepts a non-existent external parent (creates an orphan at depth 1).**
`BulkCreateFoldersHandler` resolves external parent depths into `existingParentMap` only for parents that load (`:50-58`); an item whose external `ParentFolderId` does not exist gets no map entry, so wave classification leaves `parentDepth = 0` → `depth = 1` and the folder is **created anyway** pointing at a missing parent (`:255-278`). The spec defines a per-item `ParentNotFound` error (`folder.api.md:408`) that is never produced. *Impact:* orphaned folders referencing non-existent parents; corrupted hierarchy. *Recommendation:* record `ParentNotFound` for items whose external parent didn't resolve; also reject archived external parents.

### Medium

- **FOL-M1** — Generic errors, no `errorCode`: already-archived/already-closed/no-draft/active-registrations/depth/name-taken all funnel through `InvalidOperation`/`EntityAlreadyExists`; the endpoints emit no RFC 9457 `extensions.errorCode`. `folder.api.md` explicitly documents `FolderAlreadyArchived`/`FolderAlreadyClosed` bodies and the error catalog lists `FolderNotEmpty`/`CircularFolderReference`/`DepthExceeded`/`ParentCreationFailed` — none reachable. (Base-class mapping is in unread `Magiq.Platform`; the absence of any `errorCode` plumbing here is the finding.)
- **FOL-M2** — The archive registration gate **contradicts ADR-006**. `folder.write-model.md:24` makes `FolderHasActiveRegistrations` a *blocking* precondition; ADR-006 (`catalog-domain-invariants.md:41`) states registrations are tracked "only to surface a **non-blocking warning** … it does not gate archive … gating Catalog's folder archive on Registration state would couple the two contexts." The code blocks (§ArchiveFolderHandler:34-37), coupling Catalog archive to Registration state. Reconcile spec-vs-ADR.
- **FOL-M3** — Divergent/dead registration tracking. `FolderRegistrationIndex` + `RegistrationCountIndexProjector` maintain a per-item `ActiveRegistrationCount` from `RegistrationInitiated/Cancelled/Rejected`, but `HasActiveRegistrationsAsync` reads the `IUniquenessCounterService` counter (`ScopeKeys.MediaItemRegistrations`/`CounterKeys.ActiveRegistrations`) instead. The index is unused by the gate (contradicting ADR-006's claim it backs the warning); two counters over the same fact can drift.
- **FOL-M4** — The registration gate and the archive cascade enumerate the subtree from **eventually-consistent** reference indexes (`FolderFoldersIndex`/`FolderMediaItemsIndex`); a not-yet-projected child folder/item is missed, so a "blocking" gate can pass over an item with active registrations and the cascade can skip a live child. ADR-006 chose strongly-consistent counters precisely to close this race.
- **FOL-M5** — Creation-lock over-engineering + operational hazards. The per-collection lock serialises **all** single-folder creates in a collection (throughput bottleneck) though Tier-2 `ReserveAsync` is already atomic — the lock is a performance optimisation for bulk, not a correctness requirement. It introduces `FolderCreationLockUnavailableException` → **503 not in `folder.api.md`**; a 1-minute TTL (`DynamoDbFolderCreationLockService.cs:18`) that can **expire mid-bulk** (voiding the "atomic read+write" guarantee for exactly the large batches it targets); `FolderLockTableMigration` **never enables DynamoDB TTL** on `ExpiresAt`, so the release-catch comment "TTL will expire the lock entry automatically" is misleading and a crash orphans the lock (blocking the whole collection) until the next acquire's `#ttl < :now` overwrite.
- **FOL-M6** — `GetFolderByIdResponse` leaks internal `TenantId` (and adds `Originator`/`ArchivedDate`/`MetadataAttributor` beyond the spec GET body). Multi-tenancy boundary value — remove.
- **FOL-M7** — `PATCH /folders/{id}` is a non-atomic 2-command sequence (`RenameFolderCommand` then `UpdateFolderDescriptionCommand`, `PatchFolderEndpoint:69-87`). If the description command fails after the rename commits, the client sees an error while the rename persisted; two separate optimistic writes double the conflict surface.
- **FOL-M8** — No request validators. `FolderId.From`/`CollectionId.From` (`Guid.Parse`) and `FolderName.From` (`ValueOf` throws) → 500 on malformed input; `MoveFolderRequest.CollectionId`/`CreateFolderRequest.Name = null!` NRE if omitted → 500 where 400/404/422 is expected.
- **FOL-M9** — `BulkCreateFoldersByPath` silently **creates Collections** (Private visibility) from the first path segment when `collectionId` is omitted (`:112-158`), bypassing the Collection-create endpoint and its guards; an orphan collection remains if a later folder `SaveManyAsync` fails. Undocumented in `folder.api.md`.
- **FOL-M-conc** — No command carries `ExpectedVersion`, contradicting the write-model invariant (`ExpectedVersion` → `ConcurrencyConflict`, `:25`) and the spec command signatures (`:88-90`). No client-supplied concurrency precondition is possible; only event-store version applies.

### Low

- **FOL-L1** — Integration-event record naming/timestamp/`EventVersion` divergence from context-overview `*Message` contracts (FOL-FP1).
- **FOL-L2** — `Folder.Move` accepts a `collectionId` and emits `FolderMoved` when it differs, though `Apply` never changes the collection — a confusing dead branch (FOL-D2).
- **FOL-L3** — `BulkCreateFoldersHandler.ComputeSuggestedName` and `TryAutoSuffix` are byte-identical duplicated methods (`:345-371`).
- **FOL-L4** — Stale aggregate doc-comments on `Archive`/`Move` reference a non-existent `FolderHierarchyService`/`FolderDomainService`, an `isAccessible` GSI fan-out, and a "no active child folders" gate that don't match the implemented active-registrations/write-side cascade (FOL-D4).
- **FOL-L5** — `ArchiveFolderResponse`/`CloseFolderResponse`/`CommitFolderMetadataResponse` are defined but never sent (endpoints return 204 no-body) — dead DTOs.
- **FOL-L6** — `FolderName` regex permits leading/trailing whitespace (no trim) and uses a non-static instance `Regex`; `"Foo"` vs `"Foo "` distinguishable via single-create (bulk trims, single-create does not).
- **FOL-L7** — `GetFolderHierarchy` loads the whole collection into memory and returns full summary rows (spec: "shallow: IDs + names only"); the `nameContains` filter is not applied in the handler.
- **FOL-L8** — Bulk within-batch dedup normalises with `Trim().ToLowerInvariant()` while Tier-1 `GetTakenNamesAsync` uses `Normalized()` (lower-only, no trim) — trim inconsistency between the two dedup passes.

---

## 13. Design Flaws

1. **Archive is an irreversible, self-recursive, failure-swallowing write-side cascade over child aggregates** (FOL-C3/FOL-H6/FOL-H7/FOL-FC1-2). For a regulated-records platform this is the single biggest architectural defect: it permanently archives descendants as a side effect, re-enters itself per level, hides every child failure, has no DLQ, and — with no unarchive — is unrecoverable. The fan-out should archive aggregates in one bounded, checkpointed, failure-propagating pass (or, as Collection's spec argues, be a read-model-only accessibility flag).
2. **Two independent parents of truth for "is this item under this folder" and "does this item have active registrations," both eventually consistent, one of them dead.** `FolderMediaItemsIndex` misses assignment (FOL-H3); `FolderRegistrationIndex` is maintained but unused (FOL-M3); the gate reads a strongly-consistent counter while the *subtree membership* it iterates is eventually consistent (FOL-M4). The invariant the whole archive gate exists to protect is porous.
3. **A distributed creation lock guards uniqueness that the atomic reservation registry already guarantees** (FOL-M5). It buys bulk-throughput smoothing at the cost of a per-collection serialization bottleneck for single creates, a new 503 failure mode, a TTL that expires under the very load it targets, and a migration that never enables TTL. This is unnecessary complexity layered on top of the correct primitive.
4. **Move is under-specified in code**: no cycle guard (FOL-C2), no cross-collection guard with a body-supplied collection id (FOL-H1), no subtree depth/counter maintenance (FOL-H2). The hierarchy invariants the aggregate exists to protect are enforced nowhere.
5. **Non-transactional reservation/counter dual writes are pervasive and inconsistently ordered** (FOL-H5) — every create/rename/move/archive/bulk is a partial-failure window.
6. **The error/validation/auth contract is bypassed at the boundary** — generic `InvalidOperation` collapses the catalog's coded 409/422 vocabulary, no validators means malformed input 500s, and no authorization layer means the 403s the Swagger advertises are unreachable.

---

## 14. Design Gaps

- **No authorization layer** (endpoints or handlers) and **owner derived from the caller** — the largest gap.
- **No move-cycle / cross-collection / subtree-depth enforcement** — the hierarchy invariants are unguarded.
- **No `MediaItemAssignedToFolder` handling** in the media-items reference index.
- **No failure propagation / DLQ / bounded parallelism / checkpointing** in the archive fan-out; **no single-pass** cascade (it re-dispatches itself).
- **No archived guard** on Rename/Move/UpdateDescription; **no unarchive/reopen** path.
- **No request-validation layer** (no FluentValidation) → malformed IDs/names 500.
- **No RFC 9457 `errorCode` emission**; no coded `FolderAlreadyArchived`/`FolderAlreadyClosed`/`DepthExceeded`/`CircularFolderReference`/`ParentNotFound`/`DuplicateName`.
- **No transactional reservation+counter+event write** (ambient transaction).
- **No `ExpectedVersion`/If-Match** concurrency precondition.
- **No collection existence/archival check** on create; **no `ParentNotFound`** on bulk.
- **No async `/folders/import`** endpoint (deferred, BulkFolderImportJob).
- **DynamoDB TTL not enabled** on the lock table despite the code relying on it.

---

## 15. Missing Features

- **Ownership enforcement** on every write and read (commands lack a checked actor; owner mis-derived from caller).
- **Collection load + owner/archival validation** on folder create.
- **Move-cycle guard**, **cross-collection rejection**, and **subtree depth/counter recomputation**.
- **`MediaItemAssignedToFolder` (and `MediaItemDeleted`) handlers** in `FolderMediaItemsIndexProjector`.
- **Failure-propagating, bounded, single-pass archive cascade** with DLQ.
- **`IsArchived` guard** on Rename/Move/UpdateDescription; an **`UnarchiveFolder`** path if reversibility is desired.
- **`ParentNotFound`** per-item error in bulk create; **batch-size (200) cap** enforcement.
- **FluentValidation validators** (ID well-formedness, name length/trim, page-size cap).
- **Coded domain errors** (`FolderAlreadyArchived`, `FolderAlreadyClosed`, `DepthExceeded`, `CircularFolderReference`, `FolderCollectionImmutable`, `DuplicateName`, `ParentNotFound`) mapped to `errorCode` + RFC 9457.
- **`ExpectedVersion`** threading for optimistic concurrency.
- **Async `/folders/import`** endpoint (deferred).

---

## 16. Recommendations (prioritised)

### 1 — Correctness
- **R1 (Critical).** Add the move cycle guard (walk target-parent ancestry / source subtree) → `CircularFolderReference` 422; reject cross-collection moves and stop accepting `collectionId` from the body; validate subtree depth and recompute descendant depth counters on move (FOL-C2/H1/H2).
- **R2 (Critical).** Rebuild the archive cascade: guard the root first; archive descendant aggregates in one bounded, checkpointed pass without re-dispatching `ArchiveFolderCommand`; observe every `Result` and throw retryable failures to SQS/DLQ (FOL-C3/H6/H7/FC1-2).

### 2 — Security
- **R3 (Critical).** Implement PERM-1: load the Collection on create, derive `OwnerId` from it, and enforce write access; thread the actor into all commands; enforce `actor.Id == folder.OwnerId` on mutations and owner-or-visibility on reads; return 403 with `errorCode` (FOL-C1).

### 3 — Data Integrity
- **R4 (High).** Add `MediaItemAssignedToFolder`/`MediaItemDeleted` handlers to `FolderMediaItemsIndexProjector`; make the registration gate read a strongly-consistent source and delete the dead `FolderRegistrationIndex` (or wire it in) (FOL-H3/M3/M4).
- **R5 (High).** Adopt the ambient-transaction (or guard→event→reservation) pattern so reservation/counter and event append commit atomically; fix release-before-save / reserve-before-save ordering (FOL-H5).
- **R6 (High).** Add the `IsArchived` guard to Rename/Move/UpdateDescription (FOL-H4); fail bulk items with `ParentNotFound` (FOL-H8).

### 4 — Domain / Spec Reconciliation
- **R7 (Medium).** Reconcile the registration-blocking contradiction between `folder.write-model.md` and ADR-006 (FOL-M2); return coded `DomainError`s (`FolderAlreadyArchived`/`FolderAlreadyClosed`/`DepthExceeded`/`CircularFolderReference`) and emit RFC 9457 `errorCode` (FOL-M1/D3).
- **R8 (Medium).** Thread `ExpectedVersion` into Rename/Move/Archive per the invariant table (FOL-M-conc).

### 5 — Simplification
- **R9 (Medium).** Re-evaluate the creation lock: given atomic `ReserveAsync`, prefer reservation-conflict retries over a per-collection lock for single creates; if the lock stays, document the 503, enable DynamoDB TTL in the migration, and add lock renewal so it can't expire mid-bulk (FOL-M5).

### 6 — API / Validation
- **R10 (Medium).** Add FluentValidation validators (ID well-formedness, name length/trim, page-size cap) so malformed input returns 400/422 not 500 (FOL-M8); remove `TenantId` from `GetFolderByIdResponse` (FOL-M6); make PATCH atomic (FOL-M7); document/gate the bulk-paths collection auto-create (FOL-M9); map in-batch cycle to 400 and bound the hierarchy query.

### 7 — Maintainability
- **R11 (Low).** Delete dead response DTOs and the duplicated suffix methods; fix the stale aggregate comments; reconcile `*IntegrationEvent`/`*Message` naming before the wiki publish; trim `FolderName` consistently (FOL-L1-8).

---

### Top 5 before production
1. **FOL-C1 / R3** — no authorization anywhere, and folder ownership is taken from the caller with the Collection never loaded → any tenant user creates folders in any collection and mutates/archives any folder.
2. **FOL-C3 / R2** — the archive cascade swallows every descendant failure, archives before the guard, and recurses into itself → silent, partial, irreversible archives of regulated records with no DLQ.
3. **FOL-C2 / R1** — `MoveFolder` has no cycle guard (only self-move) → a client can move a folder into its own descendant and corrupt the hierarchy; the documented 409 guard doesn't exist.
4. **FOL-H1 / FOL-H2 / R1** — cross-collection move accepted with a body-supplied `collectionId`, and subtree depth/counters ignored → immutability broken and depth invariant corrupted.
5. **FOL-H3 / FOL-H5 / R4-R5** — the media-items index misses `MediaItemAssignedToFolder` (assigned items escape the archive gate) and every reservation/counter write is a non-atomic dual write.
