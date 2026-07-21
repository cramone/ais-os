# MediaItem — Aggregate Architecture Review (Specification vs Repository)

_Context: **Catalog** (bounded context) — magiq-media_
_Aggregate: **MediaItem**_
_Reviewer role: Principal Domain Architect (DDD / CQRS / Event Sourcing / API) and Senior Software Engineer_
_Date: 2026-07-19_
_Scope: `docs/spec/contexts/Catalog/aggregates/MediaItem/**` (api, write-model, read-model, scenarios, checkout-cr-saga) + shared conventions (api-conventions, error-catalog, security-scenarios, bulk-operations, media-types), `docs/adrs/catalog-domain-invariants.md`, `docs/spec/contexts/Catalog/context-overview.md` vs `src/modules/Catalog/**` MediaItem slice: `Catalog.Domain/Aggregates/MediaItems/**` (aggregate, 29 events, snapshots, VOs), `Catalog.Domain/ValueObjects/**` (shared VOs referenced), `Catalog.WriteModel/Commands/MediaItems/**` (29 command+handler folders incl. `Shared/MetadataFieldOriginResolver`, `ApprovedAssetSnapshotFactory`), `Catalog.WriteModel/IntegrationEvents/{Publishing/Mappers/MediaItemDomainEventMapper, Consuming/Handlers/{MediaProfilePublishedConformanceFanout, RegistrationInitiated, RegistrationCancelled, RegistrationRejected, RecordTypePublished, RecordTypeDeprecated}}`, `Catalog.WriteModel.Endpoints/V1/MediaItems/**`, `Catalog.ReadModel/{Projectors,ReadModels,Queries}/MediaItems/**`, `Catalog.ReadModel.Endpoints/V1/MediaItems/**`_

> **Method:** ~97 production `.cs` files across the MediaItem slice were read and compared against the five MediaItem spec files, the shared conventions/error-catalog/security-scenarios, and `catalog-domain-invariants.md` (ADR-006/010/013). The full aggregate, every command handler, all six read-model projectors, the integration mapper, the registration/conformance consumers, and the endpoints/DTOs were read in full; tiny VO/DTO records were skimmed for shape. Asset / MediaProfile / Folder / Registration / DocumentSigning code was consulted only where MediaItem references it directly (asset-role assignment, the profile snapshot on create, registration refs, signing-session link, folder derivation). Findings that hinge on unread `Magiq.Platform` base behaviour (`CommandHandler` error-code→HTTP mapping, `TransactionBehavior`/`ITransactionScope` commit semantics, `PagerParameters` cap, `QueryIndexAsync` GSI selection, `ProjectionHandlerBase` `MissingCurrent`/`ProjectedVersion` monotonicity) are flagged as such. Cross-references to the completed **Collection** review (`/tmp/catalog-collection-architecture-review.md`) and the **AssetManagement** module review are used for shared cross-cutting findings rather than re-deriving rationale.

---

## 1. Summary

`MediaItem` is the richest aggregate in the Catalog context — the core cataloguing unit that governs a full draft → review → publish → revision → version lifecycle, inline reviewer approval, folder assignment/move with derived `CollectionId`, asset-role assignment/replace/unassign, registration references, signing-session links, per-version snapshots, GDPR version purge, and conformance drift tracking against its pinned `MediaProfile`. The aggregate itself (`MediaItem.cs`, 1063 lines) is genuinely sophisticated and, in several respects, the **strongest** part of the slice: every domain event carries a passed-in timestamp (no wall-clock in event emission — contrast AssetManagement A-D2), the metadata origin-resolution (ADR-013) is faithfully implemented and shared between single/batch writes, the review-session value object is clean, and reviewer identity is correctly bound to `IExecutionContext.Actor.Id` at the endpoint (so a reviewer can only vote as themselves — not spoofable).

Structurally the slice is complete: 29 domain events all wired in `When<>`, a snapshot, command-per-folder handlers, a domain→integration mapper, six read-model projectors, and seven query/endpoint pairs. Several things the AssetManagement review flagged as defects are done correctly here (passed-in timestamps; consumers observe the `Result` before ACK; detail projector has near-total event coverage; bulk-create checks folder-archived and profile-published).

However, the aggregate is **not production-ready**. The review surfaced **2 Critical** and a large cluster of **High** issues in six themes:

1. **Authorization is absent end-to-end.** No endpoint declares a policy; no handler performs the PERM-1 owner check; mutating commands don't carry an owner-comparison identity. Any authenticated tenant user can read, mutate, archive, delete, and — most seriously — **permanently purge published versions** of any other owner's item. The `PurgeMediaItemVersion` endpoint documents "System/admin only" but enforces nothing.
2. **The ADR-006 `active-items` hierarchy counter is never maintained.** `Create`/`Assign`/`Move`/`Archive` handlers do not touch the `active-items` uniqueness counter that `ArchiveFolderHandler` reads to block archiving a non-empty folder — the exact "can't-self-heal hierarchy corruption" ADR-006 exists to prevent.
3. **The Asset↔MediaItem binding is one-sided and lossy.** Handlers never dispatch `AttachAssetToMediaItemCommand`/`DetachAssetFromMediaItemCommand`, and no integration event exists for `AssetUnassignedFromRole`/`AssetReplacedInRole` — AssetManagement never learns of unassign/replace.
4. **Read-model integrity gaps.** The summary projector never sets `CollectionId` on assign (and leaves it stale on move), appends tags instead of replacing, and stamps `CurrentVersionNumber = 1` on a fresh draft; the version-summary projector ignores purge; the version list returns the v0 draft sentinel row.
5. **Metadata "full replace" is actually a merge.** `PUT /items/{id}/metadata` and the bulk variant claim complete-replacement semantics (R-23) but the aggregate and detail projector merge into the existing draft.
6. **The error/validation/transaction contract is unmet.** Generic `InvalidOperation` everywhere (no catalog codes, no RFC 9457 `errorCode`), no validators, reviewer-not-in-session returns 422 instead of 403, and name-reservation writes are non-transactional dual writes.

As with Collection, the aggregate core is the strongest part; nearly every Critical/High defect lives in the **handler / projector / integration orchestration layer** around it.

---

## 2. Aggregate Analysis

### `MediaItem` (Aggregate Root) — `Catalog.Domain/Aggregates/MediaItems/MediaItem.cs`

`EventSourced<MediaItem, MediaItemId, MediaItemSnapshot>`, `ITenantScoped`, `[AggregateType("media.item")]`. Single aggregate; no child entities (review-session, asset-reference, conformance-gap, metadata are value objects — correct). Healthy VO surface: `MediaItemId`, `Title`, `MediaItemStatus`, `MediaAssetReference`, `MetadataChangeset`, `MetadataFieldOrigin`, `MediaProfileSnapshot`/`MediaProfileSnapshotField`, `ReviewSession`/`ReviewerAssignment`/`ReviewerDecision`/`ReviewSessionId`, `ConformanceGap`/`ConformanceStatus`, `SigningSessionId`, `ChangeRequestId`, `RegistrationId`, `Attributor`.

**Key state (all `private set`):** `TenantId` (first field of `MediaItemCreated`, set once), `FolderId?`, `CollectionId?`, `OwnerId`, `MediaProfileId`, `Title`, `Description?`, `Status`, `Metadata` (`Current`+`Draft?`), `Assets`, `RegistrationIds`, `Tags`, `CurrentVersionNumber`, `ActiveSigningSessionId?`, `ConformanceStatus`/`ConformanceGaps`, `SnapshotFields`, `SnapshotRecordTypeVersions`, `Author?`, `RecordDate?`, `_activeReview` (rebuilt from replay, not persisted). `IsArchived => ArchivedAt.HasValue`.

**Invariants enforced in the aggregate (correct):**
- Publish guards: no active signing session, `Status ∈ {Draft, Revising}`, all required `SnapshotFields` present in effective draft (`MediaItem.cs:465-516`).
- Metadata origin resolution (`ResolveFieldKey`, `:1014-1038`) faithfully implements ADR-013 (exact → bare-by-`UnqualifiedName`; 0=Unknown, 1=resolve, ≥2=Ambiguous; General rejected if name reserved bare-or-qualified). Immutable-field guard (`:547-550, 590-593`).
- `SetMetadataBatch` validates every entry before emitting (`:536-555`) — atomic, no partial writes.
- `AssignToFolder` one-way (`FolderId == null` guard, `:251-254`); `Move` requires assigned + different target (`:322-336`).
- `Delete` requires `IsArchived` (`:277-280`); `PurgeVersion` guards `versionNumber ≥ 1`, `!= CurrentVersionNumber`, non-empty reason, allowed when archived (`:344-374`).
- Reviewer decision guards: `PendingApproval`, reviewer in session, not already decided (`:162-204, 378-413`).
- **Event timestamps are all passed in** — deterministic under replay. This is the correct pattern (contrast AssetManagement A-D2). The one `DateTimeOffset.UtcNow` (`TakeSnapshot`, `:633`) is benign snapshot metadata, not replayed event data.

**Aggregate-level defects (detailed in §12–13):**
- **MI-D1 (High, correctness).** `Withdraw()` only blocks `Archived` (`:740-748`); it permits `Draft`, `Revising`, `Published`, `PendingApproval`. The write-model/scenarios restrict withdraw to `Published`/`PendingApproval` (MW-1: "Withdraw on Draft or Archived returns 422"). Withdrawing a `Revising` item flips `Status → Draft` while a live published version and `CurrentVersionNumber > 0` remain — an inconsistent state; withdrawing a `Draft` is a spurious no-op event.
- **MI-D2 (Medium, correctness).** Immediate publish (no reviewers) emits **both** `MediaItemPublicationRequested` (with empty `ReviewerIds`) **and** `MediaItemApproved` (`RequestPublication`, `:498-513`). The scenario C-2 and traceability table show only `MediaItemApproved` for the no-reviewer path. The spurious `MediaItemPublicationRequested` is mapped to an integration event (§10 MI-M3).
- **MI-D3 (Medium, correctness).** `UpdateConformanceStatus` no-op guard compares only gap **count** (`newStatus == ConformanceStatus && ConformanceGaps.Count == newGaps.Count`, `:684`). A gap-set change with the same cardinality (one gap swapped for another) is treated as a no-op → stale `ConformanceGaps`. Separately, `TryResolveConformanceGaps` (`:1042-1062`) only emits when **all** gaps resolve (`remaining.Count == 0`); the write-model §Conformance Auto-Resolution says it should emit whenever *any* gap is satisfied, updating the remaining list — so partial resolution leaves already-satisfied gaps showing in the read model until the last one is filled.
- **MI-D4 (Low, generic errors).** Every guard returns `DomainError.InvalidOperation` (422) or `ValidationFailure`. None returns the catalog-coded errors the API advertises (`DuplicateTitle`/`MediaItemAlreadyExists`→409, `MediaProfileNotPublished`→422, `NotAssignedReviewer`→403, `ReviewerAlreadyDecided`→422, `RoleAssignmentNotFound`→404, `MediaItemCheckedOut`). `MediaItemDomainErrors` defines named factories for the three metadata errors but they all funnel through `InvalidOperation` (ADR-013 acknowledges this).
- **MI-D5 (Low, payload).** Several events carry fields the spec payloads omit: `MediaItemArchived`/`MediaItemDeleted` carry `MediaProfileId`; `MediaItemMoved` carries `Title`; `MediaItemWithdrawn` carries `requestedBy` + an always-empty `string.Empty` reason (`:747`).

---

## 3. Lifecycle Analysis

### State machine (reconstructed from `MediaItem.cs` guards + `Apply` handlers)

```text
                 Create(profileId, title, folderId?)         [handler: profile Published, folder exists]
                              │
                              ▼
                    ┌──────────────────┐
                    │      Draft       │◄────────────────────────────┐
                    │ (Metadata.Draft, │                             │
                    │  edits allowed)  │   UpdateTitle/Description    │
                    └───────┬──────────┘   SetMetadata* / Tag         │
                            │              AssignAsset/Unassign/Replace│  (all guard Draft|Revising)
             Publish(reviewerIds=[])       LinkSigningSession          │
                    │           │                                      │
     Publish(reviewerIds≠[])    │ (immediate; emits PublicationRequested + Approved) 
                    ▼           ▼                                      │
        ┌────────────────┐   ┌────────────┐                           │
        │ PendingApproval│   │ Published  │──BeginRevision──►┌──────────┴──┐
        │ (ReviewSession)│   │(vN live)   │                  │  Revising    │
        └──┬──────────┬──┘   └──┬──────┬──┘                  │(edits→Draft; │
    all approve   any reject    │      │                     │ vN still live)│
           │          │      Withdraw  │                     └──┬───────────┘
           ▼          ▼         │       └──Withdraw──┐   DiscardRevision │  Publish
      MediaItemApproved  MediaItemRejected           │        │          │  (→ v+1)
        (→Published,      (→Draft,                    ▼        ▼          ▼
         v+1, snapshot)    ReviewSession cleared)   Draft   Published   PendingApproval/Published
           │                                                              
           ▼          Withdraw (PendingApproval→Draft)                    
        Published                                                          
                                                                          
   Draft | Published | PendingApproval ──Archive──► Archived ──Delete(guard: Archived)──► Deleted [terminal]
                                        (terminal)                              (row removed by projector)

   Any published vN (n≥1, n≠current) ──PurgeVersion──► version row deleted (no status change)
   ⚠ Checkout sub-state (CheckedOut / CheckoutChangeRequestId / MediaItemCheckoutReviewSaga):
     spec = "Design — not yet implemented"; NO code path sets CheckoutStatus (§15).
```

**Terminal states:** `Archived` (then `Deleted`). **Reversible:** `Revising ⇄ Published` (via Discard). **Cross-collection move** re-derives `CollectionId`.

### Lifecycle issues
- **MI-Life1 (High) — Withdraw is not lifecycle-guarded (MI-D1).** `Draft`/`Revising` are reachable into `Withdraw`, corrupting the revision sub-state or emitting spurious events. The projectors dutifully set `Status = Draft`, so a `Revising` item silently loses its revision status while its published version stays live.
- **MI-Life2 (Medium) — Checkout lifecycle is entirely absent.** The read model, API GET response, and error catalog all reference `CheckoutStatus`/`CheckedOutBy`/`ActiveMediaChangeRequestId`/`MediaItemCheckedOut`/`MediaItemNotCheckedOut`, and the `MediaItemProjector` spec table lists `MediaItemCheckedOut`/`CheckedIn`/`ForceReleaseCheckout` handlers — none exist in code. The `mediaitem.checkout-cr-saga.md` is explicitly "Design — not yet implemented." `CheckoutStatus` is a static "Available" default that no write path ever changes (§15). No `MediaItemReviewSaga`/`MediaItemCheckoutReviewSaga`/`TimeoutScanner` participation exists for MediaItem — review is driven inline by `ApproveReviewHandler`/`RejectReviewHandler`, which is fine and matches scenarios, but means there is **no timeout/compensation** for a `PendingApproval` item whose reviewers never respond (indefinite hang).
- **MI-Life3 (Medium) — `Archived` read-model rows are removed only via `Delete`; there is no recovery/unarchive.** Consistent with spec (no unarchive in v1), but combined with the Collection archive fan-out that hard-archives child MediaItems (Collection COL-C2), a MediaItem can be driven to `Archived` irreversibly as a side effect of collection archive.

---

## 4. Commands

29 command/handler pairs. `⚠` marks a command with at least one finding (detailed in §12–15).

| Command | Handler | Trigger | Notes |
|---|---|---|---|
| CreateMediaItemCommand | CreateMediaItemHandler | API | ⚠ no owner check; **no folder-archived check**; **no `active-items` counter**; reserve-then-save non-atomic |
| BulkCreateMediaItemsCommand | BulkCreateMediaItemsHandler | API | ⚠ no owner check; no `active-items` counter; reserve-many-then-save non-atomic (checks archived/published ✔) |
| AssignMediaItemToFolderCommand | AssignMediaItemToFolderHandler | API | ⚠ no owner check; **no folder-archived check**; **no `active-items` counter**; reserve-then-save non-atomic |
| MoveMediaItemCommand | MoveMediaItemHandler | API | ⚠ no owner check; no folder-archived check; **no `active-items` inc/dec** (comment concedes it); swap-then-save non-atomic |
| UpdateMediaItemTitleCommand | UpdateMediaItemTitleHandler | API (PATCH) | ⚠ no owner check; swap-then-save non-atomic |
| UpdateMediaItemDescriptionCommand | UpdateMediaItemDescriptionHandler | API (PATCH) | ⚠ no owner check |
| SetMetadataFieldCommand | SetMetadataFieldHandler | API | ⚠ no owner check; General type-map limited to bool/number/string |
| SetMetadataBatchCommand | SetMetadataBatchHandler | API | ⚠ no owner check; **merge not full-replace** (MI-H3) |
| BulkSetMetadataCommand | BulkSetMetadataHandler | API | ⚠ no owner check; merge not full-replace; multi-aggregate |
| AssignAssetToRoleCommand | AssignAssetToRoleHandler | API | ⚠ **no `AttachAssetToMediaItem` dispatch**; auto-submit as SystemActor |
| UnassignAssetFromRoleCommand | UnassignAssetFromRoleHandler | API | ⚠ **no `DetachAssetFromMediaItem` dispatch**; no integration event |
| ReplaceAssetInRoleCommand | ReplaceAssetInRoleHandler | API | ⚠ **no Detach/Attach dispatch**; no integration event |
| TagMediaItemCommand | TagMediaItemHandler | API | ⚠ no owner check; no archived/status guard in aggregate `Tag()` |
| PublishMediaItemCommand | PublishMediaItemHandler | API + internal (auto-submit) | ⚠ no owner check; immediate path emits spurious PublicationRequested (MI-D2) |
| ApproveReviewCommand | ApproveReviewHandler | API (reviewer) | ⚠ not-in-session → 422 not 403; no System actor-type gate (see PERM-2 note) |
| RejectReviewCommand | RejectReviewHandler | API (reviewer) | ⚠ same error-mapping gap |
| RejectMediaItemCommand | RejectMediaItemHandler | — | ⚠ **duplicate** of RejectReview; dead command surface |
| BeginRevisionCommand | BeginRevisionHandler | API | ok (guard Published) |
| DiscardRevisionCommand | DiscardRevisionHandler | API | ok (guard Revising) |
| WithdrawMediaItemCommand | WithdrawMediaItemHandler | API | ⚠ aggregate under-guards status (MI-D1) |
| ArchiveMediaItemCommand | ArchiveMediaItemHandler | API + fan-out | ⚠ no owner check; **release-before-save** non-atomic; **no `active-items` decrement** |
| DeleteMediaItemCommand | DeleteMediaItemHandler | API | ⚠ no owner check (guard Archived ✔) |
| PurgeMediaItemVersionCommand | PurgeMediaItemVersionHandler | API | ⚠ **no System/owner check** (MI-C2) |
| AddRegistrationRefCommand | AddRegistrationRefHandler | System (consumer) | counter inc after save (non-atomic, ADR-accepted) |
| RemoveRegistrationRefCommand | RemoveRegistrationRefHandler | System (consumer) | counter dec after save |
| LinkSigningSessionCommand | LinkSigningSessionHandler | System (saga) | ok |
| UnlinkSigningSessionCommand | UnlinkSigningSessionHandler | System (saga) | ok |
| UpdateMediaItemConformanceStatusCommand | UpdateMediaItemConformanceStatusHandler | System-internal | ⚠ count-only no-op guard (MI-D3); note: fanout bypasses this command and saves directly |

**Cross-cutting command issues:**
- **No mutating command carries an owner-comparison identity that any handler checks.** `Create` carries `OwnerId` (= caller, correct at creation); `Publish`/`SetMetadata*`/`Withdraw`/`BeginRevision` carry `RequestingUser`; `Approve`/`Reject` carry `ReviewerId` (= `Actor.Id`, bound at the endpoint). But **no handler compares the caller to `mediaItem.OwnerId`** — PERM-1 is impossible downstream (§12 MI-C1).
- **Handlers return generic errors** (`InvalidOperation`, `ResourceNotFound`, `EntityAlreadyExists`) — no catalog codes / `errorCode` (§12 MI-M9).
- **Duplicate command:** `RejectMediaItemCommand`/`Handler` and `RejectReviewCommand`/`Handler` both call `mediaItem.RejectReview(...)`; only `/reject` maps to `RejectReviewCommand`. `RejectMediaItem*` is dead (§12 MI-L1).

---

## 5. Queries

7 read paths — `GetMediaItemById`, `GetMediaItemVersion`, `ListMediaItemVersions`, `ListMediaItemsByFolder` (`ListMediaItemsQuery`), `ListAllMediaItems` (OpenSearch, powers `GET /items`), `SearchMediaItems` (OpenSearch). (`ListUnassignedMediaItemsQuery`/`ListMediaItemsByOwnerQuery` in the read-model spec are aspirational — folded into `ListAllMediaItems`'s `unassigned`/`ownerId` filters; the read-model spec flags the removed GSIs itself.)

| Query | Paging | Auth / Scope | Notes |
|---|---|---|---|
| GetMediaItemByIdQuery | n/a | ⚠ none | returns any tenant item regardless of owner/collection-visibility; response leaks `TenantId`/`OwnerId` |
| GetMediaItemVersionQuery | n/a | ⚠ none | historical version detail; no owner/visibility check |
| ListMediaItemVersionsQuery | cursor (ADR-014 ✔) | ⚠ none | ⚠ **returns v0 draft sentinel row** (no `VersionNumber ≥ 1` filter) |
| ListMediaItemsQuery (by folder) | cursor (ADR-014 ✔) | ⚠ none | ⚠ **`status` filter dropped**; includes archived + cross-owner items |
| ListAllMediaItemsQuery | search_after (ADR-014 ✔) | ⚠ optional `ownerId` only | tenant-filtered; owner is an optional filter, not enforced scoping; unknown `status` silently matches nothing |
| SearchMediaItemsQuery | from/size | ⚠ none | OpenSearch full-text (tenant filter) |

**Query issues:**
- **CQRS boundary is clean** — handlers return read-model DTOs via `IReadModelReader`/OpenSearch; no aggregates/event payloads cross the boundary; cursor/`search_after` pagination with no total count (ADR-014 ✔). `ListAllMediaItems` clamps `pageSize` 1–100, uses a sort-field allowlist, and escapes injected JSON — genuinely good.
- **No owner/visibility scoping** on `GetMediaItemById`, `GetMediaItemVersion`, `ListMediaItemsByFolder`, or `ListAllMediaItems`. The spec's read authorization ("owner or public Collection visibility") is not enforced anywhere (§12 MI-C1).
- **`ListMediaItemsByFolder` ignores the documented `status` filter** — `ListMediaItemsQuery` has no `Status` field and `Matches` is `TenantId + FolderId` only, so archived items and other owners' items appear (§12 MI-M8).
- **`ListMediaItemVersions` leaks the v0 draft row** — the `MediaItemCurrentDraftProjector` writes a `SK=0` sentinel row into the same `MediaItemVersionSummaryReadModel` table, and the query's `Matches` doesn't exclude it (§12 MI-M6).
- Soft-delete does not leak: `MediaItemDeleted` triggers `DeleteAsync()` in both projectors, so deleted rows disappear from reads. Good.

---

## 6. API Endpoints

Spec (`mediaitem.api.md`) vs implementation:

| Spec route | Verb | Impl? | Impl status | Spec status | Note |
|---|---|---|---|---|---|
| /v1/items | POST | ✔ | 201 | 201 | ok |
| /v1/items/bulk | POST | ✔ | 201/202 | 201/202 | envelope ok; 200-item cap enforcement unconfirmed (§7) |
| /v1/folders/{folderId}/items | POST | ✔ (CreateMediaItemInFolder) | 201 | 201 | ok |
| /v1/items/{id} | PATCH | ✔ | 204/400/404/409/422 | 204/… | ⚠ non-atomic 2-command (spec-sanctioned) |
| /v1/items/{id}/folder | PUT | ✔ (AssignOrMove) | 204 | 204 | ⚠ 422-means-already-assigned heuristic (ADR-011) |
| /v1/items/{id}/metadata/{fieldName} | PATCH | ✔ | 204/400/422 | 204/400/422 | origin→400 enforced ✔; merge not replace |
| /v1/items/{id}/metadata | PUT | ✔ | 204 | 204 | ⚠ **merge, not full-replace** (MI-H3) |
| /v1/items/{id}/roles/{role}/assets | POST | ✔ | 204 | 204 | ⚠ no Attach dispatch |
| /v1/items/{id}/roles/{role}/assets/{assetId} | DELETE | ✔ | 204 | 204 | ⚠ no Detach dispatch |
| /v1/items/{id}/tags | PUT | ✔ | 204 | 204 | ⚠ no owner check |
| /v1/items/{id}/publish | POST | ✔ | 202 | 202 (scenarios say 200) | spec-internal 200/202 drift |
| /v1/items/{id}/withdraw | POST | ✔ | 204 | 204 | ⚠ under-guarded (MI-D1) |
| /v1/items/{id}/begin-revision | POST | ✔ | 204 | 204 | ok |
| /v1/items/{id}/discard-revision | POST | ✔ | 204 | 204 | ok |
| /v1/items/{id}/archive | POST | ✔ | 204 | 204 | ⚠ non-atomic reservation release |
| /v1/items/{id} | DELETE | ✔ | 204 | 204 | ok (guard Archived) |
| /v1/items/{id}/approve | POST | ✔ | 204 | 204 | ⚠ 403 unreachable (422 instead) |
| /v1/items/{id}/reject | POST | ✔ | 204 | 204 | ⚠ 403 unreachable |
| /v1/items/{id}/versions/{n} | DELETE (purge) | ✔ | 204 | 204 | ⚠ **no System/owner enforcement** (MI-C2) |
| /v1/items/{id} | GET | ✔ | 200 | 200 | ⚠ no owner/visibility check; leaks `TenantId` |
| /v1/folders/{folderId}/items | GET | ✔ | 200 | 200 | ⚠ `status` filter dropped |
| /v1/items | GET | ✔ (ListAll) | 200 | 200 | ok (owner/status/unassigned filters) |
| /v1/items/search | GET | ✔ | 200 | 200 | ok |
| /v1/items/{id}/versions | GET | ✔ | 200 | 200 | ⚠ v0 draft row leaks |
| /v1/items/bulk/metadata | POST | ✔ | 200/207 | 200/207 | ok |

**Endpoint issues:**
- **No endpoint declares authorization** (grep of all endpoints + `CatalogEndpoint` base → zero `Roles/Policies/Permissions/RequireActorType/AllowAnonymous/PreProcessor`). Every endpoint's Swagger advertises 403 that no code path can emit; `PurgeMediaItemVersionEndpoint` even documents "Requires System or admin actor type" with no enforcement (§12 MI-C1/MI-C2).
- **RFC 9457 `errorCode` not emitted / read side flattens to 500** — same base-class behaviour as Collection (`SendDomainErrorAsync`/`SendQueryErrorAsync` without `extensions.errorCode`) (§12 MI-M9).
- **Reviewer identity is correctly `Actor.Id`** (`ApproveMediaItemEndpoint:46`, `RejectMediaItemEndpoint:48`) — a genuine positive; approve/reject cannot be cast on another reviewer's behalf.
- `AssignOrMoveMediaItemFolderEndpoint` treats *any* 422 from the assign command as "already assigned" and retries as a move (`:62-69`) — fragile if assign ever 422s for another reason.

---

## 7. Request DTO Review

| DTO | Findings |
|---|---|
| CreateMediaItemRequest | `Title = null!`-style; no validator → omitted/oversized `title` → 500 at `Title.From`; `ProfileId`/`FolderId` via `Guid.Parse` throw → 500 on malformed |
| CreateMediaItemInFolderRequest | same; folderId from route |
| UpdateMediaItemRequest | endpoint enforces "≥1 field or clearDescription" → 400 ✔ (good); no length validation of title/description |
| SetMetadataFieldRequest | endpoint validates `origin` enum → 400 ✔; `value` is raw `JsonElement` (unvalidated until handler) |
| SetMetadataBatchRequest / BulkSetMetadataRequest | array-of-entries shape matches ADR-013 ✔; per-entry `origin` required; no id/size validation |
| AssignAssetToRoleRequest / ReplaceAssetInRoleRequest | `assetId` via `Guid.Parse` → 500 on malformed |
| TagMediaItemRequest | tags default `[]` (safe); each `Tag.From` throws on invalid tag → whole request 500 |
| PublishMediaItemRequest | `reviewerIds` optional; `MemberId.From` on each — malformed → 500 |
| BulkCreateMediaItemsRequest / BulkCreateMediaItemModel | per-item; **200-item cap enforcement not observed** in handler/endpoint (spec: 400 if exceeded) |

**Cross-cutting:**
- **No FluentValidation validators anywhere** in the slice. `MediaItemId.From`/`FolderId.From`/`MediaProfileId.From`/`Title.From`/`Tag.From` call `Guid.Parse`/`ValueOf` constructors that **throw on malformed input → 500** where the spec expects 400/404/422 (§12 MI-M13). The two explicit endpoint checks (`origin` enum → 400; PATCH "≥1 field" → 400) are the only input validation present.
- **`pageSize` cap** relies on unverified `PagerParameters.FromCursor` (DynamoDB paths) and is clamped 1–100 explicitly in `ListAllMediaItems` (OpenSearch path).
- Field naming is internally consistent.

---

## 8. Response DTO Review

| DTO | Findings |
|---|---|
| CreateMediaItemResponse / …InFolderResponse | `(Id, Title, CreatedAt)` — matches spec 201 body ✔ |
| GetMediaItemByIdResponse | **leaks `TenantId`** (`:9, :39`) and exposes `OwnerId`; adds `HasAccessibleAssets`, `MetadataAttributor`, `RecordDate`, `Author`, `UpdatedAt` beyond the spec GET body; **omits `checkoutStatus`/`activeMediaChangeRequestId`** the spec body shows |
| MediaItemSummaryModel (list items) | **leaks `TenantId`** + `OwnerId` (`:6-8`); exposes `MediaProfileId`, `Tags`, `RecordDate`, `Author`, `ConformanceStatus`, `IsAccessible` beyond the spec summary shape `{id,title,status,currentVersionNumber,createdAt}` |
| PublishMediaItemResponse | `{expectedStatus, changeRequestId}` — matches spec ✔ |
| GetMediaItemVersionResponse / VersionArtifactModel | self-contained snapshot fields ✔ |
| ListMediaItemVersionsResponse | envelope ok; but v0 draft row leaks in (§6/§5) |

**Cross-cutting:**
- **`TenantId` leakage** in `GetMediaItemByIdResponse` and `MediaItemSummaryModel` — a multi-tenancy boundary value that must never round-trip to clients (§12 MI-M10), identical to Collection COL-M4.
- **`MediaItemSummaryReadModel` omits `CheckoutStatus`** (the read-model spec includes it) and the detail response omits `checkoutStatus`/`checkedOutBy`/`checkedOutAt`/`activeMediaChangeRequestId` — all consequences of checkout being unimplemented (§15).
- `CurrentVersionNumber` on summary rows is wrong for drafts (§12 MI-M2).

---

## 9. Domain Events

29 domain events, all registered in `MediaItem`'s `When<>` block. Publisher = `MediaItem` aggregate.

**Projection coverage (verified against all six projectors):**

| Domain event | Summary | Detail | VersionDetail | VersionSummary | CurrentDraft | CurrentDraftVerDetail | Notes |
|---|---|---|---|---|---|---|---|
| `MediaItemCreated` | ✔ INSERT | ✔ INSERT | — | — | ✔ v0 INSERT | ✔ | ⚠ Summary hardcodes `CurrentVersionNumber=1` (MI-M2) |
| `MediaItemAssignedToFolder` | ✔ FolderId | ✔ Folder+Coll | — | — | — | — | ⚠ **Summary omits `CollectionId`** (MI-H6) |
| `MediaItemMoved` | ✔ FolderId | ✔ Folder+Coll | — | — | — | — | ⚠ **Summary omits `CollectionId`** (MI-H6) |
| `MediaItemTitleUpdated` | ✔ | ✔ | — | — | ✔ | ✔ | ok |
| `MediaItemDescriptionUpdated` | — | ✔ | — | — | — | ✔ | correct (detail/draft only) |
| `MediaItemTagged` | ⚠ **APPEND** | ✔ replace | — | — | — | — | Summary duplicates tags (MI-M1) |
| `MediaItemMetadataFieldSet` | ✔ (ver bump) | ✔ Draft | — | — | — | ✔ | detail merges into draft |
| `MediaItemMetadataBatchSet` | ✔ (ver bump) | ✔ Draft (merge) | — | — | — | ✔ | ⚠ merge, not replace (MI-H3) |
| `AssetAssignedToRole` | ✔ (ver bump) | ✔ | — | — | — | — | ok |
| `AssetUnassignedFromRole` | ✔ (ver bump) | ✔ | — | — | — | — | ok |
| `AssetReplacedInRole` | — | ✔ (⚠ drops Order) | — | — | — | — | not on summary (fine); Low MI-L2 |
| `MediaItemPublicationRequested` | ✔ Pending | ✔ Pending | — | — | ✔ | — | ok |
| `MediaItemApproved` | ✔ Published | ✔ Published+snapshot | ✔ INSERT | ✔ INSERT | ✔ | ✔ | ok |
| `MediaItemRejected` | ✔ Draft | ✔ Draft | — | — | ✔ | — | ok |
| `MediaItemWithdrawn` | ✔ Draft | ✔ Draft | — | — | ✔ | — | ok |
| `MediaItemRevisionStarted` | ✔ Revising | ✔ Revising | — | — | ✔ | — | ok |
| `MediaItemRevisionDiscarded` | ✔ Published | ✔ Published | — | — | ✔ | — | ok |
| `MediaItemArchived` | ✔ Archived | ✔ Archived | — | — | ✔ | — | ok |
| `MediaItemDeleted` | ✔ DELETE | ✔ DELETE | — | — | ✔ DELETE | ✔ DELETE | ok |
| `RegistrationRefAdded/Removed` | ✔ (ver bump) | ✔ list | — | — | — | — | ok |
| `SigningSessionLinked/Unlinked` | ✔ (ver bump) | ✔ | — | — | — | — | ok |
| `MediaItemConformanceStatusChanged` | ✔ status | ✔ status+gaps | — | — | — | — | ok |
| `MediaItemVersionPurged` | — | — | ✔ DELETE | ⚠ **no handler** | — | ✔ | Version summary orphaned (MI-M7) |
| `ReviewerApproved` / `ReviewerRejected` | — | — | — | — | — | — | internal review-session events; not projected (correct — no read-model field) |

Other notes:
- **Timing correct** — no wall-clock in event emission (the `TakeSnapshot` `UtcNow` is snapshot metadata). A genuine strength.
- **Projection strength:** the **Detail** projector has essentially complete coverage; out-of-order safety via `MissingCurrentAsync()`; every upsert stamps `ProjectedVersion` (idempotent). This is the best-built projector in the review.
- **Undocumented extra projectors:** `MediaItemCurrentDraftProjector` + `MediaItemCurrentDraftVersionDetailProjector` maintain a `SK=0` "current draft" row not described in the read-model spec (spec gap, MI-L3) and the direct cause of the v0-in-version-list bug (MI-M6).

---

## 10. Integration Events

### Published (mapper `MediaItemDomainEventMapper.cs`)

9 mappings: `MediaItemCreated`, `MediaItemAssignedToFolder`, `MediaItemPublicationRequested`→`MediaItemSubmittedForReviewIntegrationEvent`, `MediaItemApproved`, `MediaItemRejected`, `MediaItemArchived`, `MediaItemDeleted`, `MediaItemVersionPurged`, and `AssetAssignedToRole` (extra S12 mapping). All 8 spec-listed published events are present. Each carries `TenantId` + `EventVersion = AggregateVersion`.

| Issue | Severity | Detail |
|---|---|---|
| MI-FP1 | Medium | **Spurious submit-for-review on immediate publish** — the immediate/no-reviewer path emits `MediaItemPublicationRequested` (MI-D2), which maps unconditionally to `MediaItemSubmittedForReviewIntegrationEvent` with an **empty reviewer list** → Notifications is told to alert reviewers (none), and any `MediaItemCheckoutReviewSaga`/notification consumer sees a submit immediately followed by an approve for a no-review publish. |
| MI-FP2 | High | **No integration event for `AssetUnassignedFromRole` or `AssetReplacedInRole`** — only `AssetAssignedToRole` is mapped. AssetManagement (which relies on `AssetAssignedToRoleIntegrationEvent` to (re)tag lifecycle tier / process-on-assign / attach) is **never told** when an asset is unassigned or swapped out of a role → the asset stays bound/mis-tagged (§13-3, MI-H2). |
| MI-FP3 | Low | `MediaItemArchivedIntegrationEvent` drops `FolderId`; spec says AssetManagement consumes archive to flip `IsArchived` on the capability ref (needs only the item id, so tolerable) but the domain event carries `FolderId` that is not forwarded. |
| MI-FP4 | Low (doc) | Code record names are `*IntegrationEvent`; context-overview/write-model contracts call several `*Message`. Reconcile before wiki publish (mirrors Collection COL-FP1). |

### Consumed (5 handlers that mutate MediaItem)

| Issue | Severity | Detail |
|---|---|---|
| MI-FC1 | High | **Registration consumers swallow command `Result`s with no DLQ.** `RegistrationInitiatedEventHandler`/`RegistrationCancelledEventHandler`/`RegistrationRejectedEventHandler` do `if (!result.IsSuccess) logger.LogError(...)` then return → message ACKed. For `RemoveRegistrationRef` the idempotent "ref absent" case is intentional (spec), but the handlers **cannot distinguish** it from a transient infra fault (DynamoDB throttle, concurrency) — a real failure is logged-and-lost, leaving the `RegistrationRefAdded`/counter unapplied and the folder-archive registration warning wrong. `AddRegistrationRef` failure (e.g. out-of-order before item materialises → `ResourceNotFound`) silently drops the ref **and** the `active-registrations` counter increment. |
| MI-FC2 | Medium | **`TenantId` sourced from payload body** (`new TenantId(e.TenantId)` / `TenantId.From(e.TenantId)`) in every consumer and the conformance fanout — the `IMessageHandlingContext` (SNS attribute) is unused, violating the "never from payload body" convention (mirrors AssetManagement F-C4). |
| MI-FC3 | Medium | **Conformance fanout is unbounded and non-checkpointed.** `MediaProfilePublishedConformanceFanoutHandler` loads + `UpdateConformanceStatus` + `SaveAsync` **per item in a serial loop** with no pagination beyond a >1000 warning (ADR-010 concedes pagination "not yet implemented"); a large profile → Lambda timeout, and any per-item `SaveAsync` throw aborts the whole loop with no checkpoint (re-run reprocesses from the top — mostly idempotent, except MI-D3's count-only no-op guard can re-emit / mis-skip). It also ignores the `Result` of `UpdateConformanceStatus`. |
| MI-FC-pos | — | **Correct:** all four command-dispatching consumers *do* inspect the `Result` (unlike AssetManagement F-C1's blind `return SendAsync`), and the idempotent no-op-on-absent-ref is a deliberate, documented choice. |

`RecordTypePublishedEventHandler`/`RecordTypeDeprecatedEventHandler` maintain a `RecordTypeVersionReference` projection for MediaProfile compile — they do not mutate MediaItem and are out of scope here.

---

## 11. Specification vs Repository Differences

| Item | Specification | Repository | Severity | Recommendation |
|---|---|---|---|---|
| Ownership guard (PERM-1) | All write/read commands enforce `caller.owner_id == mediaItem.OwnerId`; reads owner-or-public (`security-scenarios.md:67`, `mediaitem.api.md:52-57`) | Not enforced anywhere; handlers/queries never compare caller to `OwnerId` | Critical | Thread & enforce `Actor.Id == OwnerId`; owner-or-public on reads; 403 |
| Version purge auth | System/admin only (`mediaitem.write-model.md:195,280`; endpoint doc; PERM-2) | No actor-type/owner check on endpoint or handler | Critical | `RequireActorType("System")` + owner/admin gate |
| `active-items` counter | Inc by Create/Assign/Move(new); Dec by Archive/Move(old) (`catalog-domain-invariants.md:25`) | No handler touches the counter | High | Wire `IUniquenessCounterService` inc/dec into the four handlers |
| Asset binding | Assign dispatches `AttachAssetToMediaItem`; Unassign/Replace dispatch `Detach`/`Attach` (`mediaitem.write-model.md:265-267`) | No dispatch; assign relies on integration event; unassign/replace emit no event | High | Emit unassign/replace integration events (or dispatch Attach/Detach) |
| Metadata full-replace | `PUT /metadata` / bulk = complete replacement, omitted fields cleared (R-23, `mediaitem.api.md:251`) | Aggregate + detail projector **merge** into existing draft | High | Clear-then-set the draft in `SetMetadataBatch`/`Apply` |
| Reservation ↔ event atomicity | `Save` + reservation committed atomically by `TransactionBehavior` (`mediaitem.write-model.md:512`) | Sequential awaits; reserve/swap/release ordered around save (Archive releases *before* save) | High | Ambient `ITransactionScope`; guard/event before reservation |
| Folder-active precondition | Create/Assign/Move require non-archived folder (`mediaitem.write-model.md:289-295`) | Single Create/Assign/Move read `folder.CollectionId` without checking `IsArchived` (Bulk create checks it) | High | Add `IsArchived` guard to single Create/Assign/Move |
| Summary `CollectionId` | Assign/Move UPDATE FolderId **and** CollectionId (`mediaitem.read-model.md:145-146`) | Summary projector updates FolderId only | High | Set `CollectionId` on assign/move in summary projector |
| Withdraw states | Published/PendingApproval only (`mediaitem.scenarios.md` MW-1) | Aggregate blocks only Archived | Medium | Guard `Status ∈ {Published, PendingApproval}` |
| Summary Tags | Full replacement | Summary projector appends (`[..current.Tags, ..e.Tags]`) | Medium | Replace: `Tags = [..e.Tags]` |
| Summary CurrentVersionNumber | 0 until first publish (`mediaitem.read-model.md:28`) | Hardcoded `1` on create | Medium | Initialise to 0 |
| Version list contents | Approved versions only | Includes v0 draft sentinel row | Medium | Filter `VersionNumber ≥ 1` |
| Version purge projection | `media-item-versions` DELETE (`mediaitem.read-model.md:179`) | VersionDetail deletes; **VersionSummary has no purge handler** | Medium | Add `MediaItemVersionPurged` to VersionSummary projector |
| List-by-folder `status` filter | `ListMediaItemsByFolderQuery(…, Status?, …)` (`mediaitem.read-model.md:192`) | Query has no `Status`; returns archived + all owners | Medium | Add `Status`/owner filter |
| Immediate publish event | Only `MediaItemApproved` (C-2, traceability) | Also emits `MediaItemPublicationRequested` → SubmittedForReview | Medium | Suppress PublicationRequested on empty-reviewer path |
| Reviewer-not-in-session | 403 `NotAssignedReviewer` (C-7) | `InvalidOperation` → 422 | Medium | Coded `NotAssignedReviewer` → 403 |
| Error contract | RFC 9457 + `errorCode`; catalog codes | Generic `InvalidOperation`; no `errorCode` | Medium | Emit `errorCode`; map catalog codes |
| `TenantId` in responses | Not in GET/list body (`mediaitem.api.md:492-517`) | Present in detail + summary DTOs | Medium | Remove `TenantId`/`OwnerId` from response DTOs |
| Conformance auto-resolve | Emit whenever *any* gap satisfied (`write-model §Conformance Auto-Resolution`) | Emits only when all resolve; `UpdateConformanceStatus` no-op guard is count-only | Medium | Emit on partial resolution; compare gap *set* not count |
| Checkout lifecycle | `CheckoutStatus`, checkout saga, review saga (`read-model`, `checkout-cr-saga.md`) | Entirely unimplemented (saga is "Design"); `CheckoutStatus` never set; approve/reject inline (no timeout) | Medium (Missing) | Implement or formally defer; add review timeout |
| Publish status code | scenarios: 200; api.md: 202 | 202 | Low (doc) | Reconcile spec-internally |
| Read-model statuses | Projector table lists `MediaItemRevertedToDraft`, statuses `Withdrawn`/`Rejected` | No such event; enum has no `Withdrawn`/`Rejected` (code maps to `Draft`) | Low (doc) | Fix read-model spec |
| MI-1 scenario | "PUT metadata on a Published item… stays Published" | Aggregate blocks metadata unless Draft/Revising (BeginRevision required) | Low (doc) | Fix MI-1 to BeginRevision first (BR-1 is correct) |
| Event payloads | spec lists minimal payloads | Extra fields (`MediaProfileId` on Archived/Deleted, `Title` on Moved, `requestedBy`+empty reason on Withdrawn) | Low | Reconcile |
| Duplicate command | one reject path | `RejectMediaItemCommand`/`Handler` dead alongside `RejectReview*` | Low | Delete dead command |

---

## 12. Bugs

### Critical

**MI-C1 — No ownership/authorization on any endpoint, handler, or query (intra-tenant exfiltration + tampering).**
Verified: zero auth attributes across all MediaItem endpoints and the `CatalogEndpoint` base; no mutating handler compares the caller to `mediaItem.OwnerId`; `GetMediaItemByIdHandler`/`ListMediaItemsHandler`/`ListAllMediaItemsHandler`/version handlers apply no owner or collection-visibility scoping. `security-scenarios.md:30-84` (PERM-1) and `mediaitem.api.md:52-57` require `caller.owner_id == mediaItem.OwnerId` on writes and owner-or-public on reads.
*Why it's a problem:* the ownership boundary is the primary intra-tenant control on a multi-tenant, regulated-records platform. *Impact:* any authenticated tenant user can rename, re-tag, re-fold, edit metadata, assign/replace assets on, publish, withdraw, archive, **delete**, and **read/list** any other owner's media item. *Recommendation:* thread `Actor.Id` into every mutating command; enforce `actor.Id == mediaItem.OwnerId` in write handlers (System-dispatched exempt) and owner-or-public in read handlers; return `NotResourceOwner`/`Forbidden` → 403 with `errorCode`.

**MI-C2 — `PurgeMediaItemVersion` has no System/admin (or owner) authorization → any tenant user permanently purges any item's published versions.**
`PurgeMediaItemVersionEndpoint` (`:53-72`) and `PurgeMediaItemVersionHandler` (`:20-50`) perform no actor-type or owner check, despite the endpoint XML doc and `mediaitem.write-model.md:195,280` stating "System/admin only" and PERM-2 requiring `RequireActorType("System")`. The command permanently deletes the version snapshot row (`MediaItemVersionDetailProjector.DeleteAsync`) and publishes `MediaItemVersionPurgedIntegrationEvent`, which **releases every snapshotted asset from `VersionArtifact` protection** in AssetManagement — after which those S3 originals become deletable.
*Why it's a problem:* this is the platform's most destructive, irreversible operation (a GDPR/retention escape hatch) and it is callable by any authenticated tenant user who knows an item id and version number. *Impact:* irreversible destruction of regulated version records + loss of version-artifact S3 protection. *Recommendation:* enforce `actor.ActorType == "System"` (or an admin role) at the endpoint and re-check in the handler; return `SystemActorRequired` → 403.

### High

**MI-H1 — The ADR-006 `active-items` hierarchy counter is never maintained.**
`CreateMediaItemHandler`, `BulkCreateMediaItemsHandler`, `AssignMediaItemToFolderHandler`, and `MoveMediaItemHandler` never increment `active-items`; `ArchiveMediaItemHandler` never decrements it (it only releases the name reservation); `MoveMediaItemHandler:66` even has a comment "active-items counters are keyed by Folder scope" but does nothing. ADR-006 (`catalog-domain-invariants.md:25`) makes these handlers responsible for the counter that `ArchiveFolderHandler` reads via `CounterIsZeroAsync("active-items")` to block archiving a non-empty folder.
*Why it's a problem:* the counter stays at 0, so `ArchiveFolderHandler`'s "no active media items" guard always passes → a folder can be archived while it still contains active media items — the exact "hierarchy corruption that can't self-heal" ADR-006 was written to prevent. *Impact:* orphaned/inaccessible items under an archived folder; corrupted hierarchy invariants. *Recommendation:* wire `IUniquenessCounterService` inc/dec into Create/Bulk/Assign/Move(new folder) and Archive/Move(old folder), per the ADR table.

**MI-H2 — Asset↔MediaItem binding is one-sided; unassign/replace are never propagated.**
`AssignAssetToRoleHandler`, `UnassignAssetFromRoleHandler`, and `ReplaceAssetInRoleHandler` never dispatch `AttachAssetToMediaItemCommand`/`DetachAssetFromMediaItemCommand` (spec `mediaitem.write-model.md:265-267`); the mapper emits an integration event only for `AssetAssignedToRole`, none for `AssetUnassignedFromRole`/`AssetReplacedInRole` (§10 MI-FP2). So AssetManagement is told when an asset joins a role but **never** when it leaves or is swapped.
*Why it's a problem:* `Asset.MediaItemId`/role tagging drifts — an unassigned or replaced-out asset stays bound to a role it no longer fills; `Asset.Delete`/detach invariants and version-artifact reasoning on the AssetManagement side operate on stale associations (the mirror of AssetManagement H-1). *Impact:* undeletable/mis-tagged assets, stale process-on-assign, incorrect delete-lock state across the BC boundary. *Recommendation:* emit `AssetUnassignedFromRole`/`AssetReplacedInRole` integration events (and/or dispatch the Attach/Detach commands the spec prescribes).

**MI-H3 — `PUT /items/{id}/metadata` (and bulk) merge instead of full-replace.**
The API + ADR-013 (R-23) specify **complete replacement** — "entries omitted from the `fields` array are cleared." But `MediaItem.Apply(MediaItemMetadataBatchSet)` (`:845-855`) and `MediaItemDetailProjector` (`:220-237`) both *merge* the entries into `new Dictionary(Metadata.Draft ?? Metadata.Current)`, retaining omitted fields.
*Why it's a problem:* clients relying on documented full-replace semantics (e.g. to remove a field by omission) instead accumulate stale fields; the "read-current-then-resend-all" guidance in the spec is silently unnecessary and the removal path doesn't exist. *Impact:* metadata that cannot be cleared via the batch API; divergence from the documented contract. *Recommendation:* clear the draft (seed from `Current` only for provenance if needed) and set exactly the supplied entries in both the aggregate `Apply` and the detail projector; document whether General fields survive.

**MI-H4 — Name-reservation and event append are non-transactional dual writes.**
`CreateMediaItemHandler:82-95` reserves then saves (orphan reservation on save-fail); `AssignMediaItemToFolderHandler:64-71` reserves then saves; `MoveMediaItemHandler:59-68` swaps then saves; `UpdateMediaItemTitleHandler:55-63` swaps then saves; `ArchiveMediaItemHandler:45-48` **releases the reservation before `SaveAsync`** (if save fails, the title is freed while the item stays active). The spec's canonical handlers register `Save`+reservation with an ambient `ITransactionScope` committed by `TransactionBehavior` (`mediaitem.write-model.md:512`); the code uses manual sequential awaits.
*Why it's a problem:* every create/assign/move/rename/archive is a partial-failure window — orphaned titles, or a live item whose title is unreserved and claimable by another (identical to Collection COL-H6). *Impact:* reservation/aggregate divergence on any partial failure. *Recommendation:* adopt the ambient-transaction pattern; where unavailable, order guard→event-persisted→reservation and make the reservation op idempotent/compensating.

**MI-H5 — Registration integration consumers swallow failures with no DLQ (F-C1 analog).**
See §10 MI-FC1. `AddRegistrationRefHandler`/`RemoveRegistrationRefHandler` failures are logged and ACKed; the handlers cannot distinguish an idempotent "ref absent" from a transient infra fault, so genuine failures are lost — dropping a registration ref and its `active-registrations` counter change (which feeds folder-archive warnings). *Recommendation:* ACK only for the specific idempotent "ref not present" domain error; rethrow all other failures so SQS retries/DLQs.

**MI-H6 — Summary projector corrupts folder/collection/version/tag data.**
`MediaItemSummaryProjector`: (a) `MediaItemAssignedToFolder` sets only `FolderId`, never `CollectionId` (`:77-80`) → summary `CollectionId` is null after first assignment; `MediaItemMoved` sets only `FolderId` (`:71-74`) → `CollectionId` stale after a cross-collection move (spec `mediaitem.read-model.md:145-146` says update both). (b) `MediaItemTagged` **appends** (`:65-68`) rather than replacing → tags duplicate on every tag op. (c) `MediaItemCreated` stamps `CurrentVersionNumber = 1` for a fresh draft (`:47`), where the spec says 0-until-publish and the detail projector correctly uses 0.
*Why it's a problem:* any list/filter/query on the summary table by collection is broken; re-tagging balloons the tag set; list rows misreport version. *Impact:* corrupted list results and any downstream collection-scoped filtering. *Recommendation:* set `CollectionId` on assign/move, replace tags, initialise `CurrentVersionNumber = 0`.

**MI-H7 — Single Create/Assign/Move admit items into archived folders.**
`CreateMediaItemHandler:43-54`, `AssignMediaItemToFolderHandler:33-56`, and `MoveMediaItemHandler:36-51` fetch the folder and read `folder.CollectionId` **without checking `folder.IsArchived`** (spec pre-condition `GetActiveCollectionIdAsync` returns null on archived). `BulkCreateMediaItemsHandler` *does* check archived (`:51,109-114`) — an internal inconsistency.
*Why it's a problem:* a media item can be created in, assigned to, or moved into an archived folder, contradicting the hierarchy model and compounding MI-H1. *Impact:* items hidden under archived folders; inconsistent hierarchy. *Recommendation:* add the `IsArchived` guard to the three single-item handlers (as bulk already does).

### Medium

- **MI-M1** — Summary `MediaItemTagged` appends → duplicate tags (part of MI-H6).
- **MI-M2** — Summary `CurrentVersionNumber = 1` on create (part of MI-H6); list shows drafts at v1.
- **MI-M3** — Immediate publish emits spurious `MediaItemPublicationRequested` → `MediaItemSubmittedForReview` integration event with empty reviewers (MI-D2 / MI-FP1).
- **MI-M4** — `Withdraw` under-guarded (MI-D1): allowed from Draft/Revising; Revising→Draft loses revision context while published version stays live.
- **MI-M5** — Conformance staleness (MI-D3): partial gap resolution doesn't update the read-model gap list; `UpdateConformanceStatus` count-only no-op guard misses same-cardinality gap swaps.
- **MI-M6** — `ListMediaItemVersions` returns the v0 draft sentinel row (no `VersionNumber ≥ 1` filter); the `MediaItemCurrentDraftProjector` writes it into the same table.
- **MI-M7** — `MediaItemVersionSummaryProjector` has no `MediaItemVersionPurged` handler → a purged version still appears in `GET /items/{id}/versions` while `GET …/versions/{n}` 404s.
- **MI-M8** — `ListMediaItemsByFolder` ignores the documented `status` filter and returns archived + cross-owner items (query `Matches` = tenant+folder only).
- **MI-M9** — Generic errors, no RFC 9457 `errorCode`; reviewer-not-in-session → 422 (spec 403 `NotAssignedReviewer`); no `DuplicateTitle`/`MediaProfileNotPublished`/`RoleAssignmentNotFound`/`ReviewerAlreadyDecided` codes (read side additionally flattens to 500 per Collection base behaviour).
- **MI-M10** — `TenantId` (and `OwnerId`) leaked in `GetMediaItemByIdResponse` and `MediaItemSummaryModel`.
- **MI-M11** — Consumers source `TenantId` from the payload body, not `IMessageHandlingContext` (MI-FC2).
- **MI-M12** — Conformance fanout is unbounded/non-checkpointed → Lambda timeout for large profiles; per-item `SaveAsync` throw aborts the loop; `UpdateConformanceStatus` `Result` ignored (MI-FC3).
- **MI-M13** — No request validators → malformed ids/titles/tags/values throw in VO constructors → 500 where 400/404/422 expected; `SetMetadataField`/`Batch` General-origin `MapFieldType` only infers bool/number/string (arrays/dates unsupported for General fields).
- **MI-M14** — Auto-submit (`AssignAssetToRole`/`Unassign`/`SetMetadata*` when `AutoSubmitOnComplete`) dispatches `PublishMediaItemCommand` as `owner_system` with **empty reviewers** → immediate publish that bypasses any review requirement; bulk 200-item cap enforcement not observed.

### Low

- **MI-L1** — Duplicate command: `RejectMediaItemCommand`/`RejectMediaItemHandler` duplicate `RejectReview*`; dead surface.
- **MI-L2** — `AssetReplacedInRole` detail projector drops the slot's `Order` (`:322`).
- **MI-L3** — Undocumented `MediaItemCurrentDraftProjector`/`MediaItemCurrentDraftVersionDetailProjector` (v0 sentinel rows) absent from the read-model spec.
- **MI-L4** — `AssignOrMove` endpoint treats any 422 from assign as "already assigned" and retries as move — fragile.
- **MI-L5** — `TakeSnapshot` uses `DateTimeOffset.UtcNow` for the snapshot timestamp (benign — snapshots aren't replayed for event determinism; noted only for completeness). Event timing is otherwise exemplary.
- **MI-L6** — Extra event payload fields vs spec (`MediaProfileId` on Archived/Deleted, `Title` on Moved, `requestedBy`+empty reason on Withdrawn).
- **MI-L7** — Read-model spec references non-existent `MediaItemRevertedToDraft` event and `Withdrawn`/`Rejected` statuses (enum has neither; code maps both to `Draft`).
- **MI-L8** — Publish 200-vs-202 spec-internal drift; MI-1 scenario contradicts the Draft|Revising metadata guard (BR-1 is the correct pattern).

---

## 13. Design Flaws

1. **Authorization and validation are entirely absent layers.** No owner check, no actor-type gate on the System-only purge, no reviewer 403, no FluentValidation. The API cannot emit the 403/400 responses its own Swagger advertises, and the platform's most destructive operation is unguarded (MI-C1/MI-C2/MI-M13). This is the single biggest gap.

2. **Cross-aggregate invariants are enforced by side effects that were never wired.** The `active-items` counter (ADR-006, MI-H1) and the two-sided Asset binding (MI-H2) are both *specified* as handler-driven side effects, but the handlers omit them — so Folder archive and Asset lifecycle silently operate on incomplete information. Both are "the code forgot to do the cross-aggregate half."

3. **Non-transactional dual writes between the event store and the uniqueness registry are pervasive and inconsistently ordered** (MI-H4) — every create/assign/move/rename/archive is a partial-failure window; Archive uniquely releases *before* save. The spec's ambient-transaction design was not implemented (identical to Collection).

4. **The write model and the summary read model disagree about the same facts.** The summary projector drops `CollectionId`, appends tags, and mis-seeds `CurrentVersionNumber`, while the detail projector gets all three right (MI-H6) — two projectors over one event stream that produce contradictory rows.

5. **"Full replace" metadata is silently a merge** (MI-H3), and conformance resolution only fires on complete resolution (MI-D3) — the read model lags the true item state in both directions.

6. **Overloaded/duplicated events and commands leak intent.** Immediate publish emits a submit-for-review event (MI-D2/MI-M3); `RejectMediaItem*` duplicates `RejectReview*` (MI-L1); a `SK=0` "version" row is written into the versions table and then leaks into the versions API (MI-M6). The lifecycle surface is larger than the model needs.

---

## 14. Design Gaps

- **No authorization layer** (endpoints, handlers, or queries) — the largest gap; includes the System-only purge and reviewer-403.
- **No request-validation layer** (no FluentValidation) → malformed input 500s instead of 400/422.
- **No RFC 9457 `errorCode` emission**; read side flattens domain errors.
- **`active-items` counter maintenance absent** across Create/Assign/Move/Archive (ADR-006).
- **No unassign/replace propagation to AssetManagement**; no synchronous Attach/Detach dispatch.
- **No transactional reservation+event write** (ambient `ITransactionScope`).
- **No review timeout / compensation** — a `PendingApproval` item whose reviewers never act hangs indefinitely (no saga, no `TimeoutScanner`).
- **No checkout lifecycle** — `CheckoutStatus`/`CheckedOutBy`/`ActiveMediaChangeRequestId` never populated; `MediaItemCheckoutReviewSaga`/`MediaItemReviewSaga` unimplemented (spec is design-only).
- **No collection-visibility read filtering** and no owner-scoped list index.
- **No `status` filter on list-by-folder**; no `VersionNumber ≥ 1` filter on the version list.

## 15. Missing Features

- **Ownership enforcement** on every write and read; **System actor-type gate** on version purge; **reviewer 403** on approve/reject-by-non-reviewer.
- **`active-items` counter inc/dec** in Create/Bulk/Assign/Move/Archive.
- **`AssetUnassignedFromRole`/`AssetReplacedInRole` integration events** (or Attach/Detach command dispatch).
- **Full-replace metadata semantics** for `PUT /metadata` and bulk.
- **`MediaItemVersionPurged` handler on the version-summary projector**; **v0 exclusion** from the version list.
- **Checkout lifecycle + `MediaItemCheckoutReviewSaga` + review timeout/compensation** (or a formal deferral note).
- **FluentValidation validators** (id/title/tag/value well-formedness, bulk 200-item cap) and **RFC 9457 `errorCode`** with catalog codes.
- **Coded domain errors**: `DuplicateTitle`/`MediaItemAlreadyExists`→409, `MediaProfileNotPublished`→422, `NotAssignedReviewer`→403, `ReviewerAlreadyDecided`→422, `RoleAssignmentNotFound`→404, `SystemActorRequired`→403.
- **Summary-projector fixes** (CollectionId, tag-replace, version 0).

---

## 16. Recommendations (prioritised)

### 1 — Correctness
- **R1 (Critical).** Implement PERM-1: thread `Actor.Id` through every mutating command; enforce `actor.Id == mediaItem.OwnerId` in write handlers (System-dispatched exempt) and owner-or-public in read handlers; return 403 with `errorCode` (MI-C1).
- **R2 (Critical).** Gate `PurgeMediaItemVersion` on `actor_type == "System"` (or admin) at the endpoint and re-check in the handler (MI-C2).
- **R3 (High).** Wire `active-items` counter inc/dec into Create/Bulk/Assign/Move/Archive per ADR-006 (MI-H1); add the `IsArchived` folder guard to single Create/Assign/Move (MI-H7).

### 2 — Data Integrity
- **R4 (High).** Fix the summary projector: set `CollectionId` on assign/move, replace (not append) tags, initialise `CurrentVersionNumber = 0` (MI-H6). Add the `MediaItemVersionPurged` handler to the version-summary projector and filter v0 out of the version list (MI-M6/MI-M7).
- **R5 (High).** Make `SetMetadataBatch` / detail projection full-replace, not merge (MI-H3); emit conformance changes on partial resolution and compare the gap *set* (MI-D3/MI-M5).
- **R6 (High).** Emit `AssetUnassignedFromRole`/`AssetReplacedInRole` integration events (or dispatch Attach/Detach) so AssetManagement tracks role membership (MI-H2/MI-FP2).

### 3 — Reliability / Messaging
- **R7 (High).** Make registration consumers rethrow non-idempotent failures (ACK only "ref absent") for SQS retry/DLQ (MI-H5); source `TenantId` from `IMessageHandlingContext` (MI-M11); paginate/checkpoint the conformance fanout and observe its `Result` (MI-M12).

### 4 — Transactionality
- **R8 (High).** Adopt the ambient-transaction reservation pattern; fix Archive's release-before-save and the reserve/swap-then-save ordering (MI-H4).

### 5 — Domain Modelling
- **R9 (Medium).** Guard `Withdraw` to `Published`/`PendingApproval` (MI-D1); suppress the immediate-publish `MediaItemPublicationRequested` (MI-D2/MI-M3); delete the dead `RejectMediaItem*` command (MI-L1); return catalog-coded errors incl. `NotAssignedReviewer`→403 (MI-D4/MI-M9).

### 6 — Lifecycle
- **R10 (Medium).** Add a review timeout/compensation (saga or `TimeoutScanner`) for `PendingApproval`; implement or formally defer the checkout lifecycle and stop the read model/API advertising fields no code sets (MI-Life2/§15).

### 7 — API
- **R11 (Medium).** Add FluentValidation validators (id/title/tag/value, bulk 200-cap) so malformed input returns 400/422 not 500; emit RFC 9457 `errorCode`; stop read-side flattening (MI-M13/MI-M9).
- **R12 (Medium).** Remove `TenantId`/`OwnerId` from response DTOs (MI-M10); add the `status`/owner filter to list-by-folder (MI-M8).

### 8 — Domain Consistency
- **R13 (Medium).** Constrain auto-submit: don't publish with empty reviewers when the profile requires review (MI-M14).

### 9 — Maintainability
- **R14 (Low).** Document/reconcile the extra current-draft projectors, event payload extras, publish 200/202 drift, MI-1 scenario, and read-model spec's phantom statuses/events (MI-L3/L6/L7/L8) before the wiki publish.

### 10 — Performance/Scalability
- **R15 (Medium).** Move large-profile conformance fan-out to a paginated async job (ADR-010 acknowledges this); add an owner-scoped list index if owner-scoped listing becomes hot.

---

### Top 5 before production
1. **MI-C1 / R1** — ownership authorization is entirely absent; any tenant user can read/mutate/archive/delete any other owner's item.
2. **MI-C2 / R2** — `PurgeMediaItemVersion` (irreversible GDPR purge that releases VersionArtifact S3 protection) is callable by any authenticated user — no System/owner gate.
3. **MI-H1 / R3** — the ADR-006 `active-items` counter is never maintained, so a folder can be archived with active items (hierarchy corruption that can't self-heal), and single Create/Assign/Move admit items into archived folders.
4. **MI-H2 / R6** & **MI-H3 / R5** — Asset unassign/replace never reach AssetManagement (stale binding), and "full-replace" metadata silently merges.
5. **MI-H6 / R4** & **MI-H4 / R8** — summary projector corrupts CollectionId/tags/version, and name-reservation writes are non-atomic (orphaned/lost titles; Archive releases before save).
