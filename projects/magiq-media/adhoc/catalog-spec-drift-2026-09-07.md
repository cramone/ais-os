# Catalog — Spec ↔ Repo Drift Review

_magiq-media · 2026-09-07 · Chase Ramone_

**This is a standalone report, not a `review-cycle` review.** It has no `MM-` id and is not indexed in
`reviews/README.md`. If any block of it is taken forward, that block becomes a review in its own
workstream folder and this file becomes its evidence.

---

## Scope

| | |
|---|---|
| **Spec** | `D:\source\github\sprbrk-standard\mgq-magiq-media\docs\spec\contexts\Catalog\` — 21 files, ~9,970 lines |
| **Code** | `src\modules\Catalog\` — 9 projects, 831 `.cs` files; plus `src\hosts\`, `src\shared\` where a claim crossed out |
| **Also read** | `aspnetcore-platform` and `cdk-magiq-media` where a claim crossed a repo boundary |
| **Aggregates** | Collection, Folder, MediaItem, MediaProfile — the four implemented |
| **Also** | `context-overview.md`, `business-scenarios.md`, `sagas\archive-fan-out.md` |

**Out of scope, deliberately:**

- **`BulkFolderImportJob` / `BulkMediaImportJob`** — these belong to the `bulk-import` workstream
  (**MM-036**, **MM-037**), where the open question is build-or-withdraw, not fix. Two findings below
  (FLD-10, CTX-9) touch their *references from in-scope files*; the aggregates themselves are untouched.
- **Authentication and edge authorization** — deferred to MM-028/MM-029 since 2026-08-21. One finding
  (MP-22) reports a *documentation* claim about an implemented guard, not an auth gap.

**Method.** Four independent passes, one per aggregate group, each deriving findings from code first and
citing `file:line` on both sides. Every High finding with a code-side defect was then re-opened and
verified by hand against the source before landing here — that list is § 1, and each row says so. The
standing rule from MM-022 applied throughout: **verify against code, never against a sibling document.**

---

## Headline

**121 findings. 42 High.** The distribution is the story:

| | Count | What it means |
|---|---:|---|
| **Spec wrong, code right** | ~95 | Documentation drift. Real, but the system behaves correctly. |
| **Code wrong** | **14** | Defects. § 1. |
| **Undecided** | ~12 | Spec and code disagree and it is not obvious which should move. |

**The four spec files are not equally trustworthy.** `*.scenarios.md` and `context-overview.md` carry
the most stale claims by a wide margin — they were written early, describe mechanisms that have since
been rebuilt (the archive cascade, the review/publish flow, checkout-as-edit-session), and have not been
swept. `*.api.md` and `*.write-model.md` are much closer to the code. **Several files contradict
themselves**, having been half-corrected in an earlier pass: `folder.write-model.md` states in bold that
no Folder command carries an `ExpectedVersion` and then lists two that do (FLD-9);
`mediaprofile.write-model.md` says the compiled capability union is the `Processing` gate in one section
and that no guard reads it two sections later (MP-15).

**Two systemic patterns worth naming**, because they will keep producing findings until they are fixed
at the source rather than one row at a time:

1. **Corrections land on one aggregate and not its siblings.** Collection and Folder are near-identical
   in shape and repeatedly diverge because a fix was applied to one file only — the `EventId`/`Id`
   read-model rename (COL-10), the server-generated-id correction (FLD-8), the bulk `202`→`200` change
   (COL-5). Each is individually trivial; collectively they are the single largest source of drift in
   this module.
2. **`Matches` predicates read as filters and are not.** FLD-7 is a live data-correctness bug caused by
   this, and it passes its own unit test because the test uses the one store that honours `Matches`.
   Worth a codebase-wide grep beyond Catalog.

---

# 1. Code-side defects

**Every row here was verified by hand against the source, not taken on a pass's word.** These are the
findings that cost something if left alone. Ordered by what I'd fix first.

## 1.1 Silent data loss and wrong results

### D-1 · `MediaItemAssignedToFolder` never enters `FolderMediaItemsIndex` — the archive cascade cannot see the item · **High**

`FolderMediaItemsIndex` is the index the entire archive cascade traverses. It is written on exactly two
add paths, and first-assignment is not one of them:

- `FolderMediaItemsIndexProjector.cs:12-26` handles `MediaItemCreated` only, and `ResolveKey` returns
  `null` when `e.FolderId` is null — an item created in the unassigned pool is never added.
- `FolderMediaItemsIndexMoveAddedProjector.cs:12-26` handles `MediaItemMoved` only.

But the aggregate emits **two different events**. `MediaItem.AssignToFolder` (`MediaItem.cs:646-654`)
emits `MediaItemAssignedToFolder`, gated to first assignment only; `MediaItem.Move`
(`MediaItem.cs:738-751`) emits `MediaItemMoved` and refuses unless the item is *already* assigned.
Grepping `MediaItemAssignedToFolder` across the module finds handlers in three **read-model** projectors
and the integration-event mapper — and no write-side index projector at all.

**Consequence.** An item created unassigned and later assigned to a folder is invisible to
`ArchiveFanOutCascade.RunAsync`, which sources every item from this index
(`ArchiveFanOutCascade.cs:131-149`). It is not refused, not counted, and not in `Failures` — so
`report.IsComplete` returns `true` and `ArchiveFolderHandler.cs:83-93` archives the root folder anyway.
The guarantee `archive-fan-out.md:74-77` now states as real — *"an archived folder's subtree is fully
archived"* — does not hold. The same index backs the pre-flight registration guard
(`FolderArchiveFanOutWorker.cs:59-88`), so a **retention-locked item assigned post-creation also passes
it**. For a compliance-grade records platform that is the sharp end of this finding.

This is business scenario MW-3 ("First Folder Assignment from Unassigned Pool") intersecting FLD-1.

> **Fix:** add a `FolderMediaItemsIndex` projector for `MediaItemAssignedToFolder` mirroring
> `FolderMediaItemsIndexMoveAddedProjector`, plus a negative test. Soften the guarantee wording in
> `archive-fan-out.md` until it ships.

### D-2 · `GET /v1/folders/{folderId}/children` returns archived children in production · **High**

The spec states the exclusion twice (`folder.api.md:372-373`, `folder.read-model.md:144,237`). The code
implements it in `ListChildrenInFolderQuery.Matches`
(`Catalog.ReadModel/Queries/Folders/ListChildrenInFolder/ListChildrenInFolderQuery.cs:17-22`) — and
**`Matches` is only ever evaluated by the in-memory store.** Confirmed in the platform SDK:
`Magiq.Platform.Projections.Abstractions/Stores/IIndexQuery.cs:20-24` says so in as many words, and the
only call site is `InMemoryProjectionStore.cs:231`. `DynamoDbProjectionStore` builds a
`KeyConditionExpression` with no `FilterExpression` and never calls it.

Meanwhile `FolderChildByNameIndexSchema.cs:39-49` writes the GSI keys unconditionally (non-nullable
return), and `FolderChildSummaryProjector.cs:83-88` only sets `Status = "Archived"` rather than removing
the row. So archived folders and items are returned to every real caller.

**The contrast is instructive.** `PublicCollectionByNameIndexSchema.cs:38-52` returns `AttributeValue?`
and omits the keys when the row shouldn't be indexed — which is why the equivalent Collection filter
genuinely works. The two schemas were written differently.

**The test masks it.** `ListChildrenInFolderHandlerTests.cs:153-167` asserts the exclusion against an
`InMemoryProjectionStore` — the one store that honours `Matches`. It passes, and always will.

> **Fix:** make `FolderChildByNameIndexSchema` sparse on `Status != "Archived"`, mirroring the
> public-collection schema. Cover it with a test that does not use the in-memory store. Then grep the
> codebase for other `Matches` implementations carrying filter logic — this pattern is not confined to
> Catalog.

### D-3 · Setting a default profile silently rewrites the collection's `CreatedAt` · **High**

`CollectionSummaryProjector.cs:46-49`:

```csharp
return current is null ? MissingCurrentAsync() : UpsertAsync(current with {
    CreatedAt = e.OccurredAt, UpdatedAt = e.OccurredAt, ProjectedVersion = e.AggregateVersion });
```

`CollectionDefaultProfileSet` overwrites `CreatedAt`. Every sibling handler in the same file correctly
touches `UpdatedAt` only. `GET /v1/collections` reads this model, so the creation date a user sees
changes when an unrelated field is set.

The spec is right and specific: `collection.read-model.md:86` says this event updates
`DefaultMediaProfileId` on the **detail table only** — the summary model has no such field, so arguably
this projector should not subscribe to the event at all. No test covers this event on this projector
(`CollectionSummaryProjectorTests.cs` has cases for the other six).

> **Fix:** drop `CreatedAt = e.OccurredAt`. Decide whether the handler should exist.

### D-4 · Conformance gaps: a changed gap set and a partial resolution both emit nothing · **High** (two defects, one area)

**D-4a — count comparison.** `MediaItem.cs:1198-1201`:

```csharp
if (newStatus == ConformanceStatus && ConformanceGaps.Count == newGaps.Count) { return Unit.Value; }
```

Two gaps replaced by two *different* gaps — exactly what a profile re-publish that swaps which required
role is missing produces — emits nothing. `ConformanceGaps` on both read models stays permanently stale.
`mediaitem.write-model.md:464` requires emission when "the status **or gap set** has changed".

**D-4b — all-or-nothing resolution.** `MediaItem.cs:1646-1666` computes `remaining`, then emits only
`if (remaining.Count == 0)`. Resolving 3 of 4 gaps emits nothing and the read model keeps showing the
resolved gap. `mediaitem.write-model.md:468` requires emission when **any** gap is satisfied, carrying
the remaining list.

> **Fix:** compare set contents rather than `Count` in `UpdateConformanceStatus`; emit whenever
> `remaining.Count != ConformanceGaps.Count` in `TryResolveConformanceGaps`.

### D-5 · `MediaProfileDetailProjector` never refreshes `Name`/`Description` on publish · **High**

Publishing a renamed draft is explicitly supported — `PublishMediaProfileHandler.cs:43-47,93-103` checks
name availability on rename, and `MediaProfile.cs:866-867` applies the new name. But the Detail
projector's `MediaProfilePublished` branch (`MediaProfileDetailProjector.cs:95-120`) sets status,
version, asset definitions, record type refs, all four policies, capabilities, compiled fields and draft
— **and not `Name` or `Description`.** `MediaProfileSummaryProjector.cs:73` does set them.

**Consequence.** After a rename-on-publish, `GET /v1/profiles/{id}` and `GET /v1/profiles` return the old
name, the two read models disagree, and the `MediaProfileByNameIndex` GSI1SK stays keyed on the stale
name (`MediaProfileByNameIndexSchema.cs:45-48`).

> **Fix:** add `Name` and `Description` to the publish branch. See § 4 for the open question about
> whether the GSI1SK self-corrects.

## 1.2 Missing guards

### D-6 · `UpdateAssetDefinition` renames a role with no uniqueness check · **High**

`UpdateAssetDefinitionCommand.cs:12` carries `RoleName NewRoleName`, publicly exposed on the request DTO
(`UpdateAssetDefinitionRequest.cs:63`). `MediaProfile.cs:628-636` applies
`existing with { RoleName = newRoleName, … }` with **no** check that the new name is unused —
while `AddAssetDefinition` does check, at `MediaProfile.cs:132-135`. Role-name uniqueness within a draft
is a stated invariant (`mediaprofile.write-model.md:35`).

Renaming one role onto another's name produces two definitions with the same `RoleName` in the same
draft, which then compiles into the published snapshot.

> **Fix:** guard the rename in `MediaProfile.UpdateAssetDefinition`. Document the rename — the write
> model and API spec both describe `UpdateAssetDefinition` as not renaming at all.

### D-7 · No reviewer guard on publish exists anywhere · **High**

`mediaitem.write-model.md:33` states the invariant "Reviewer cannot be the user who published →
`ReviewerIsInitiator`"; `mediaitem.api.md:497` documents the `422`. `MediaItem.cs:912-915` claims in a
comment that the handler enforces `MinimumReviewersRequired`, `ReviewerIsInitiator` and reviewer
uniqueness under `ReviewPolicy = RequiredForPublish`.

`PublishMediaItemHandler.cs:12-94` does none of it: profile-usability, required-role and asset-Active
checks only. It never reads `profile.ReviewPolicy`, never compares `command.RequestingUser` against
`command.InitialReviewers`, and never de-duplicates. `MediaItem.RequestPublication`
(`MediaItem.cs:916-1005`) has no reviewer checks either. `ReviewerIsInitiator` appears in `src/` in
exactly two places — both comments (`MediaItem.cs:914`,
`AssignMediaItemToFolderHandler.cs:90`) — and in no error-code constant.

A user can publish an item and list themselves as its sole reviewer.

> **Fix:** implement the three checks in `PublishMediaItemHandler` with coded errors, or delete the
> invariant row, the documented `422` and both comments. **Do not leave it as a comment describing a
> guard that isn't there** — that is what made this expensive to find.

### D-8 · The `Url` field-type format rule is documented as live and implemented nowhere · **High**

`mediaitem.write-model.md:616-631` states that a value on a field whose `FieldType` is `Url` must be an
absolute `http`/`https` URI of at most 2048 characters, "enforced on every value". The section carries
no unbuilt banner.

`MetadataConstraintValidator.cs:57-74` runs six checks — `Length`, `Pattern`, `Range`, `DateRange`,
`AllowedValues`, `SelectionCount`. **`field.FieldType` is never read anywhere in the file.** A `Url`
field accepts `"not a url"`.

> **Fix:** add a `ValidateUrlFormat` gated on `FieldType == "Url"`, or banner the section as unbuilt.

## 1.3 Data collected and discarded

### D-9 · Withdraw requires a `reason` and throws it away · **High**

`WithdrawMediaItemRequest.cs` declares `public string Reason { get; set; } = null!;` — required on the
wire. `WithdrawMediaItemEndpoint.cs:47` threads it into the command. The handler forwards to
`MediaItem.Withdraw(requestedBy, withdrawnAt)`, which **takes no reason** and emits
`new MediaItemWithdrawn(..., string.Empty, ...)` at `MediaItem.cs:1292`.

The caller is compelled to supply a withdrawal reason that is never stored, never appears on the event,
and never reaches `MediaItemWithdrawnIntegrationEvent`. On a records platform, a discarded audit reason
is worse than no field at all.

> **Fix:** thread `reason` through `Withdraw` onto the event, or drop it from the request DTO. Then add
> a `POST /withdraw` section to `mediaitem.api.md`, which has none.

### D-10 · Cascade descendants lose the caller's `ArchivedDate` · **Medium**

`ArchiveFolderNodeCommand.cs:31-35` carries an optional business date which flows to `Folder.Archive`
and onto `FolderArchived`. `ArchiveFolderHandler.cs:91-93` passes `command.ArchivedDate` for the root;
`ArchiveFanOutCascade.cs:273` dispatches with three arguments, so **every descendant gets `null`**.

This contradicts `ArchiveFolderNodeHandler.cs:15-17`'s own stated reason for existing — "the two paths
must archive a folder identically". Note it is currently masked by D-11: no caller can set the field.

> **Fix:** thread `ArchivedDate` through `RunAsync`.

### D-11 · `archivedDate` and `closedDate` have no wire path · **High** / **Medium**

`ArchiveFolderEndpoint.cs:5` is a `CatalogEndpointWithoutRequest` — no request DTO at all — and line 40
builds the command leaving `ArchivedDate` at its `null` default. **`archivedDate` is `null` on every
folder in the system.** `folder.api.md:416` says it is "supplied by the caller on `POST /archive`";
`folder.scenarios.md:75` correctly says the endpoint never supplies one. The two spec files disagree and
the api file is the wrong one.

Same shape for `closedDate`: `CloseFolderEndpoint.cs:5,40` is request-less, the command parameter exists
(`CloseFolderCommand.cs:8`) but only `Folder.Create` can populate the field — while the endpoint's own
OpenAPI summary (`CloseFolderEndpoint.cs:25-26`) advertises "an optional business-supplied closed date",
which is unreachable.

> **Fix:** decide whether these are real business fields. If yes, add the request bodies. If no, strike
> them from the write model and fix the misleading endpoint summary. Either way `folder.api.md:416` is
> wrong today.

## 1.4 Smaller code-side items

### D-12 · A live route silently sets the opposite review policy · **High**

Not strictly a code defect — but the failure mode is severe enough to belong here.
`mediaprofile.api.md:231` and `mediaprofile.scenarios.md:59` both document the body of
`PUT /v1/profiles/{profileId}/review-policy` as `{ "reviewPolicy": "RequiredForPublish" }`. The bound
DTO is `SetReviewPolicyRequest.Policy` (`SetReviewPolicyRequest.cs:7`), and `ReviewPolicy`'s first enum
member is `None` (`ReviewPolicy.cs:5`).

A client following the spec sends an unmatched property, `Policy` binds to `None`, **the call sets the
opposite of what was asked and returns `204`.** Nothing validates it. Two sibling routes have the same
name mismatch with milder outcomes — `acceptedContentTypes`→`AllowedMediaCategories` (422) and
`version`→`NewVersion` (404). See MP-11.

> **Fix:** correct the spec. Separately, consider whether an unmatched-property binding failure should be
> a `400` platform-wide — this class of bug is silent by construction.

### D-13 · `RejectMediaItemCommand`/`Handler` is an unreachable duplicate · **Medium**

`RejectMediaItemCommand.cs` / `RejectMediaItemHandler.cs:9-24` are a verbatim duplicate of
`RejectReviewCommand`/`RejectReviewHandler`, both calling `mediaItem.RejectReview(...)`.
`RejectMediaItemEndpoint.cs:48` dispatches `RejectReviewCommand`, so the duplicate has no caller. Only
`RejectReviewCommand` is in the spec. **Fix:** delete it.

### D-14 · `AddAssetDefinition` auto-default reads the published list, not the draft · **Medium**

`AddAssetDefinitionHandler.cs:34` forces `IsDefault = true` on the first asset definition added — but
tests emptiness against `profile.AssetDefinitions` (**published**) rather than
`profile.Draft.AssetDefinitions`. So on a revision draft of a published profile the auto-default never
fires, and on an initial draft it fires on *every* add until the first publish.

Alongside it, `:50-79` (`TransformOriginalForBackwardCompatability`) force-defaults the role literally
named `"original"` on the profile named `"All Media"` for an Enterprise-driver client — gated on two
string comparisons, and documented nowhere. **Fix:** correct the draft-vs-published read; document the
auto-default rule; put the back-compat transform behind something more durable.

---

# 2. Undecided — spec and code disagree, direction not obvious

These need a call before anyone edits either side.

### U-1 · Metadata batch write: merge or replace? · **High**

`mediaitem.api.md:294` carries a ⚠️ banner: *"Full replace semantics (R-23): This is a complete
replacement of `Metadata.Draft`. Entries omitted from the `fields` array are cleared"*, repeated at
`:1131` for bulk and `mediaitem.scenarios.md:474`.

`MediaItem.cs:1402-1413` seeds a dictionary from the existing draft and assigns only the supplied
entries. **Nothing clears omitted keys.** Neither `SetMetadataBatchHandler` nor `MediaItem.SetMetadataBatch`
clears either.

Compounding it: `SetMetadataBatchHandler.cs:74-82` `continue`s past a `JsonValueKind.Null` entry on a
non-required field — neither written nor cleared — and returns `204`. So **there is currently no way to
remove a metadata key through the API at all**, and a client following the spec will silently keep
values it believes it deleted.

> Replace is the documented contract and the more defensible one, but implementing it is a behaviour
> change with an event-replay consequence. Worth a decision, not a quiet edit.

### U-2 · Unassign asset returns `200` with a body; spec says `204` · **High**

`mediaitem.api.md:429` documents `204 No Content` for
`DELETE /v1/items/{itemId}/roles/{roleName}/assets/{assetId}`.
`UnassignAssetFromRoleEndpoint.cs:64` sends `SendOkAsync(new UnassignAssetFromRoleResponse(...))`. It is
**the only MediaItem write endpoint that does this** — every sibling uses `SendNoContentAsync`. Pick one;
if the body stays, document the shape.

### U-3 · Deprecated RecordType fields: emitted or excluded? · **High**

`mediaprofile.write-model.md:136` records a 2026-09-07 ruling — deprecated fields "**are emitted,
carrying `IsDeprecated: true`, and are counted toward collisions**" — with 35 lines of justification
resting on `MediaProfileSnapshotField.IsDeprecated`.

`MediaProfileDomainService.cs:118` does `.Where(f => !f.IsDeprecated)`, dropping them before candidates
are collected. And **the carrier does not exist**: neither `CompiledMetadataField` nor
`MediaProfileSnapshotField` has an `IsDeprecated` member, so the MediaItem guards the ruling says read it
(`:146-149`) are reading a field that has never existed. The source data *is* available —
`RecordTypeFieldDetailDto.IsDeprecated` is on the reference DTO.

This is the root of **MI-2** too: six `MediaProfileSnapshotField` members the MediaItem write model
depends on (`IsDeprecated`, `IsSearchable`, `DisplayName`, `Description`, `Group`, `Order`) don't exist,
and consequently the deprecation guards at `MediaItem.cs:936-947`, `:1043-1050` and `:1094-1103` are
absent. **RecordType's `DeprecateFieldInRecordType` valve currently releases nothing.**

> Either implement (add the member in both places, drop the `.Where`) or downgrade § to
> designed-not-shipped. Today it reads as current behaviour and is not.

### U-4 · Compiled-template ordering and `Group` sectioning · **High**

`mediaprofile.write-model.md:208-232` states a normative 2026-09-07 rule about sectioning on
`(RecordTypeId, Group)` and rendering in pin order. Neither `Group` nor `Order` crosses the context
boundary — `RecordTypeFieldDetailDto` carries neither and `CompiledMetadataField` has neither member.
`CompileTemplateAsync` (`MediaProfileDomainService.cs:148-180`) emits fields in `GroupBy(BareName)`
first-appearance order with no sectioning or sorting at all. Same shape as U-3: implement, or mark it
designed.

### U-5 · Can an archived collection still be mutated? · **Medium**

`collection.write-model.md:64-70` correctly warns that `ApplyTags`, `SetDefaultMediaProfile`,
`SetVisibility` and `UpdateDescription` carry no archived check — verified at `Collection.cs:86-90`,
`:147-167`, `:193-201`, and none of the four handlers adds one. So an archived collection can be made
`Public`. The spec flags the question and nobody has answered it.

### U-6 · Declared-set vs compiled-union capabilities · **Medium**

`mediaprofile.write-model.md:326-343` states a 2026-09-04 ruling (Chase) that
`MediaProfileSnapshot.Capabilities` carries `MediaProfile.Capabilities`, not the compiled union, and that
"no guard reads" the union. `CompiledMetadataTemplate.ToSnapshot()` (`:108-112`) does the opposite, and
`PublishMediaProfileHandler.cs:75-77` short-circuits to an empty capability list when no RecordType is
pinned — so a capabilities-only profile declaring `Processing` ships an empty set. The same file
contradicts itself: `:236-248` says the union **is** the `Processing` gate and is read.
`mediaprofile.design-decisions.md:94-132` settles it in favour of "it is read".

---

# 3. Spec-side corrections

~95 findings where the code is right and the document is wrong. Grouped so a remediation pass can take
one file at a time. Full evidence for each is in the per-aggregate detail; the `file:line` on both sides
was captured for every row.

## 3.1 Collection — 15 findings

| Id | Sev | Finding |
|---|---|---|
| COL-1 | High | `CollectionArchived` error code documented at `collection.api.md:119-123` and `write-model.md:21` **does not exist**. Code raises `CollectionAlreadyArchived` (`CollectionErrorCodes.cs:12-22`). `error-catalog.md:272` already records this correctly — the two aggregate files are the outliers. |
| COL-2 | High | Archive documented as **read-model-only, no write-side cascade** (`write-model.md:13,168,172-176`). It is a real write-side cascade dispatching `ArchiveMediaItemCommand`/`ArchiveFolderNodeCommand` per descendant (`ArchiveFanOutCascade.cs:101-141`). `CollectionItemsIndex` and the `media-fan-out` queue exist nowhere. Contradicts `sagas/archive-fan-out.md` **and** the code. |
| COL-5 | High | Bulk create documented as `202 Accepted` with a 100-item cap (`api.md:296,332,352`). Code returns `201`/`200` (`BulkCreateCollectionsEndpoint.cs:112`) with a cap of **200**. **See § 5 — this is residue from MM-022's C-3.** |
| COL-7 | High | `GET /v1/collections/public` documented as cross-owner and **anonymous** (`api.md:253`). It is tenant-scoped and authenticated — `ListPublicCollectionsEndpoint.cs:41` passes `TenantId`, the GSI partition is `TENANT#{t}#COLLECTIONS#PUBLIC`, and there is no `AllowAnonymous` anywhere in `src/`. |
| COL-3 | Med | Fan-out documented as enqueued by the projectors. It is triggered by `CollectionArchivedEventHandler.cs:21-35`; no `CollectionArchiveFanOutJob` type exists. |
| COL-6 | Med | `api.md:318` says collection ids are server-generated only; `write-model.md:44` says optional per item. Code accepts caller ids (`BulkCreateCollectionsEndpoint.cs:62-80`). |
| COL-8 | Med | Public listing silently excludes **archived** collections (`PublicCollectionByNameIndexSchema.cs:49-52`); documented as sparse on `Visibility=Public` only. |
| COL-9 | Med | `CreateCollectionCommand` documented as returning `CollectionId`; returns `Unit`. |
| COL-10 | Med | Both read models documented with `CollectionId` and `EventId` fields. Code has `Id` and no `EventId`. **Folder's spec already made this correction; Collection's was not swept.** |
| COL-15 | Med | `PATCH /v1/collections/{id}` is three sequential commands with **no rollback** (`PatchCollectionEndpoint.cs:78-106`); documented as a single partial update. `PatchFolderEndpoint.cs:62-80` is identical. |
| COL-11,12,13 | Low | Reader method mis-documented; `CollectionArchived` payload field is `OccurredAt` not `ArchivedAt`; documented error sets omit `404`/`422`. |
| COL-14 | Med | → U-5. |

## 3.2 Folder — 15 findings

| Id | Sev | Finding |
|---|---|---|
| FLD-1 | High | `folder.scenarios.md:110-131` describes the **pre-2026-08-27 cascade**: re-entrant `ArchiveFolderHandler`, swallowed failures, "the target folder is archived anyway, and the caller gets `204`". All three are now false — the cascade dispatches non-re-entrant `ArchiveFolderNodeCommand`, and `ArchiveFolderHandler.cs:75-79` refuses the whole archive with `422 FolderArchiveIncomplete`. |
| FLD-5 | High | → D-11. |
| FLD-2 | Med | Two live `ArchiveFolder` refusals documented in no Folder spec file: `422 FolderSubtreeTooLargeToArchive` (>500 descendants, `ArchiveFolderHandler.cs:48-55`) and `422 FolderArchiveIncomplete`. Both are in `error-catalog.md:291-292`. The write model also calls the cascade "non-blocking"; it is blocking. |
| FLD-3 | Med | `ArchiveFolderNodeCommand`/`Handler` undocumented — and it is where `nameReservationService.ReleaseAsync` now lives (`:42`), which the spec still attributes to `ArchiveFolderHandler`. |
| FLD-4 | Med | `IFolderArchiveFanOutWorker` signature stale — returns `Task<ArchiveFanOutReport>`, not `Task`, and has a third member. The return value is load-bearing (`ArchiveFolderHandler.cs:75` gates on `report.IsComplete`). |
| FLD-8 | Med | `FolderId` documented as **caller-generated**; `CreateFolderEndpoint.cs:45` calls `FolderId.New()`. **Collection went through this exact correction; Folder did not.** |
| FLD-9 | Med | Commands table lists `ExpectedVersion` on two commands while the same file states in bold at `:32-38` that no Folder command carries one. Neither does. |
| FLD-11 | Med | `Tag` listed as a Folder value object. `Folder` has no tags — no property, method, command, event or endpoint. |
| FLD-6 | Med | → D-11. |
| FLD-10 | Med | `POST /v1/collections/{collectionId}/folders/import` presented as live at `folder.api.md:29,662-665`. No match for `folders/import` anywhere in `src/`. **Owned by MM-036** — listed here only because the *reference from `folder.api.md`* reads as shipped and carries no banner. |
| FLD-12,13,14,15 | Low | Projector metadata fields named after retired ones (contradicting the same file at `:79-81`); Properties table omits `ArchivedDate`/`Description`/`Originator`; stale cross-reference to a code comment rewritten 2026-09-01; documented scope key `media-collection:{id}` is `collection:{id}` in `ScopeKeys.cs:56` — matters, it's a literal partition value. |
| FLD-7 | High | → D-2. |

## 3.3 MediaItem — 41 findings

**`mediaitem.read-model.md` is no longer truncated** — it ends cleanly at `:502` with a recovered-tail
provenance note at `:476`. The 2026-07 truncation is closed. **`MediaItemReviewSaga` is absent, not
partial** — no such file exists under `src/`; the only copies are in stale agent worktrees. This matches
`mediaitem.write-model.md:1181-1183` ("removed on 2026-06-02"). **`MEMORY.md` should be updated** — it
still lists it as "partial — missing closing handlers".

**Code-side:** D-4, D-7, D-8, D-9, D-13 · **Undecided:** U-1, U-2, U-3.

| Id | Sev | Finding |
|---|---|---|
| MI-9 | High | Scenarios document a publish response that no longer exists — `200 {status, versionNumber}` and a `202` reviewers path with `commentThreadId` (`scenarios.md:71,104,116,124,344,545,561,592`). Code returns `200 PublishMediaItemResponse(Status, ChangeRequestId)` on **both** paths. `mediaitem.api.md:485-492` already carries the correction; the scenarios file was not swept. |
| MI-10 | High | `IsAccessible` documented as "derived from Collection.IsArchived — set by `CollectionArchiveFanOutWorker`". Its only writer is `AssetAccessibilitySummaryProjector.cs:19-33`, on asset infection/deletion. It means "every assigned asset is still accessible" and has nothing to do with collection archival. Both aggregates' code says so in comments. |
| MI-11 | High | MW-1 states Withdraw-from-`Draft` is a `422`; the only guard is `if (Status == Archived)` (`MediaItem.cs:1257-1295`), and from `Draft` it emits `MediaItemWithdrawn` **and supersedes any open edit session** — a silent lock release on a no-op. Contradicts `write-model.md:315`, which is right. |
| MI-6 | High | `decisionComment` on approve doesn't exist in the aggregate method, the command, or the endpoint (which takes no body). `api.md:900` says "Request: none" — api.md and write-model.md disagree. |
| MI-13 | Med | **Nine domain events carry payload fields the spec's table omits** — including `MediaItemApproved.PublishedMetadata`, which the spec calls `ApprovedMetadataSnapshot`. That rename is the one most likely to mislead a projector author. |
| MI-14 | Med | Four emitted, registered, consumed events missing from the Domain Events table entirely: `MediaItemRevisionStarted`, `MediaItemRevisionDiscarded`, `ReviewerApproved`, `ReviewerRejected`. |
| MI-15,16 | Med | Event names wrong: `MediaItemSigningSessionLinked`/`Unlinked` are `SigningSessionLinked`/`Unlinked` (and `[DomainEvent]` makes that the **persisted discriminator**). The projection table names six events that do not exist — `MediaItemRevertedToDraft`, `MediaItemCheckedOut/In`, `AbandonCheckout`, `ForceReleaseCheckout` — the real ones are the four `EditSession*` events. |
| MI-17 | Med | Two of six projectors undocumented, including `MediaItemVersionSummaryProjector`, which backs `GET /items/{id}/versions`. The spec never mentions that **v0 working-draft rows** live in `media-item-versions` and are returned by the versions list. |
| MI-18 | Med | Read-model record shapes drift on names and membership across all three models — `MediaItemId` vs `Id`, seven undocumented members on the detail model, and a documented `MediaItemVersionReadModel` type that doesn't exist. |
| MI-19 | Med | Two live routes absent from `api.md`: `PUT /items/{id}/roles/{role}/assets` and `DELETE /items/{id}/versions/{n}` (whose required `reason` body is undocumented). The Route Structure block also omits all six checkout routes and both bulk routes. |
| MI-20 | Med | `AssetAssignedToRoleIntegrationEvent` is published (`MediaItemDomainEventMapper.cs:3`) and absent from the integration-event table — an undocumented cross-module contract. |
| MI-22 | Med | `PublishMediaItemHandler` loads the **aggregate** and gates on `IsUsableByExistingItems()`, not `GetPublishedAsync` as documented. Consequence — a *Deprecated* profile still permits publishing existing items — is documented nowhere. Same divergence in `AssignAssetToRole` and `ReplaceAssetInRole` handlers. |
| MI-23 | Med | `ApproveReviewHandler.cs:34-37` **refuses approval when any asset contains a virus.** The spec calls this call "enrichment — non-blocking". An undocumented, uncoded refusal on a reviewer-facing endpoint. |
| MI-24 | Med | Auto-submit fires from three handlers, not one — also `AssignAssetToRoleHandler.cs:91-100` and `SetMetadataBatchHandler.cs:111-118`, both as `owner_system`. **A metadata write can take an item `Draft → Published`.** |
| MI-25 | Med | Seven error codes in the invariants table have no constant and never reach the wire; the refusals are bare `InvalidOperation`. `api.md:284` documents this correctly — write-model.md doesn't. |
| MI-21,26,28,29,30 | Med | "Eleven commands run through the guard" — there are eight (and it then lists eight). `BareName` is `UnqualifiedName`. Four aggregate method signatures drift, including an `AssignAssetToRole` guard the spec and a code comment both place on the aggregate when it lives in the handler. `Delete` is idempotent (returns before the archived check). `ReviewSession`/`MediaProfileSnapshot` shapes drift. |
| MI-31,32 | Med | A `null` metadata value is silently skipped, not cleared (→ U-1). `attributedTo`/`attributedDate` are accepted on both metadata endpoints and documented on neither wire contract. |
| MI-33 | Med | Five scenario invariants contradict code or their own file — including a stale bullet at `:438` ("metadata writes are not validated") directly contradicting steps 1-2 of the same scenario, and `:497`'s claim that `ReviewPolicy` was removed (it exists; nothing in the publish path reads it — see D-7). |
| MI-34 | Med | The `active-items` folder counter does not exist. Only `active-registrations` does, which the spec also documents — correctly. |
| MI-35…41 | Low | Stale banner on an already-implemented `201`; two projector and one index name wrong; `ReviewerDecisionRecorded` is `ReviewerApproved`; `POST` vs `PUT` for replace; two code comments rotted (`MediaItemVersionSummaryReadModel.Status` lists three statuses that aren't `MediaItemStatus` members; `RegexOptions.NonBacktracking` contradicts the implementation). |

## 3.4 MediaProfile — 25 findings

**Code-side:** D-5, D-6, D-14 · **Undecided:** U-3, U-4, U-6, D-12.

| Id | Sev | Finding |
|---|---|---|
| MP-6 | High | **`mediaprofile.defaults.md` disagrees with `DefaultMediaProfiles.cs` on almost every checkable field.** Six profiles documented, **seven** seeded (undocumented `All Media`). Every profile's primary role is documented as `primary`; **all seven are `original`** in code. All six display names wrong. `:227` states "there is no default-*role* flag on `AssetDefinition`" — `IsDefault` exists and is set `true` on every seeded primary. `AutoSubmitOnComplete: true` on all seven, mentioned nowhere. The code is annotated as authoritative at `DefaultMediaProfiles.cs:25`. |
| MP-1 | High | `MetadataTemplateCompiled` domain event **does not exist** — zero hits in `src/` and `tests/`. The spec makes it "the sole mutation point for `CompiledTemplate`" (`:73,426,451`). The real carrier is `MediaProfilePublished.PublishedSnapshot.CompiledTemplate`. A code comment at `CompiledMetadataTemplate.cs:73` repeats the false claim. |
| MP-9 | High | `PinnedRecordTypes` / `pinsRecordType` marked **"✅ Carriers added 2026-09-07"** in two files. Nothing was built: the member is not on `MediaProfileDetailReadModel`, `ListMediaProfilesQuery` has no pin parameters, and the projector writes no such member. |
| MP-7 | High | `MediaProfilePublishedIntegrationEvent` documented as carrying "the full `MediaProfilePublishedSnapshot`". It is a flattened subset with **no** `AssetDefinitions`, `RecordTypeRefs`, `CompiledTemplate`, `LeaseDurationMinutes`, `ChangeRequestPolicy` or `AutoSubmitOnComplete`. A downstream needing asset definitions must re-read the profile. |
| MP-8 | High | Nine invariant error codes documented; **three exist** (`MediaProfileErrorCodes.cs:17-38`). Every guard those rows describe returns an untagged `InvalidOperation`. `error-catalog.md:381-384` states the true position — the two spec files contradict each other. |
| MP-2 | High | Publish accepts a **capabilities-only** draft (`MediaProfile.cs:337-345`); spec and API refusal text both say asset-def-or-record-type. The endpoint's own OpenAPI summary already says all three. |
| MP-11 | High | → D-12 (three request field-name mismatches; the review-policy one silently inverts the setting). |
| MP-12 | Med | The reference-model tables named in the write model are **the wrong tables** — Catalog reads its own `media-catalog-record-type-index` and `media-catalog-asset-ref`, not Metadata's `media-record-types` or `media-assets`. `scenarios.md:16-26` corrected this 2026-09-02 and calls the latter "a cross-context table read that Catalog does not do, and may not". `write-model.md` was not swept. |
| MP-13 | Med | `IMediaProfileService` **does not exist** — zero occurrences. The spec declares the interface, tabulates its usage and gives a full implementation. Name checks go through the platform `INameReservationService`. The handler *shapes* the spec describes are accurate; only the interface is fictional. |
| MP-20 | Med | Seeding: no `SeedDefaultProfilesConsumer`, no `TenantProvisioned` handler, no `src/functions/` directory, and no deterministic `Idempotency-Key` — `SeedDefaultProfilesService.cs:88` mints a fresh `MediaProfileId.New()` per run. Idempotency comes solely from the name-reservation check. |
| MP-14 | Med | Governance field groups (`:353-380`) — a normative section with **no implementation**: no registry call in `CompileTemplateAsync`, no `SourceCapability` on `CompiledMetadataField`, no `MandatoryRecordkeepingCoreMissing`, and `ICapabilityRegistry` still lives in Metadata. `design-decisions.md:35-38` correctly labels it "Designed". |
| MP-16 | Med | Undocumented cap of **3 pinned RecordTypes** (`MediaProfile.cs:185-188`), surfaced in the OpenAPI summary but in no spec file. |
| MP-17 | Med | Five event payloads differ from the documented ones — including `AssetDefinitionsReordered` carrying `(RoleName, DisplayOrder)` pairs where the spec says a name array, and `AssetDefinitionDefaultSet` carrying an `AssetId` the whole handler pre-condition depends on. |
| MP-18 | Med | The deprecated-**version** guard and `supersededBy` are not implemented — `IsDeprecatedAsync` takes no version and resolves the RecordType-level key. `api.md:193-195` frames this as future; `write-model.md:521` states it as current. |
| MP-19 | Med | → D-14. |
| MP-15 | Med | → U-6. |
| MP-21 | Low | `MediaProfile.cs:260` promises `DomainError.CannotDiscardInitialDraft`; the code returns a plain `InvalidOperation`. Same class as MP-8, on the code side. |
| MP-22 | Low | `api.md:54` says **no** MediaProfile command has an authorization check. Five governance handlers now call `ProfileGovernanceAuthorization` returning `TenantAdministratorRequired` — which has **no row in `error-catalog.md`**. The `403` example shows `NotResourceOwner`, which that route cannot emit. *(Reported as documentation drift about an implemented guard, not an auth gap.)* |
| MP-23,24,25 | Low | Scenario states `202` for deprecate (code: `204`) and a `409 MediaProfileDeprecated` that doesn't exist. `AllowsConcurrentEdit` omitted from the `CompiledMetadataField` table though two other files treat it as contract-bearing; `CompiledMetadataTemplate` omits four members and the `MaxFileSizeBytes` computed at publish. Four command names differ; two dead response types remain; three code comments cite a "media-documents bucket" that doesn't exist. |

## 3.5 Context overview, saga, business scenarios — 25 findings

**`context-overview.md` is the least reliable file in the Catalog tree.** Nineteen findings, nine High,
and the failures are structural rather than cosmetic — whole event contracts, whole missing inbound
relationships.

| Id | Sev | Finding |
|---|---|---|
| CTX-7 | High | **The "Consumed Integration Events" section covers 3 of the 15 registered consumers.** Missing: all six Asset* events, `RegistrationCancelled`, `RegistrationRejected`, both RecordType events, and `MediaProfilePublished`→conformance fan-out. **AssetManagement→Catalog is an entire missing inbound relationship**, and so is Catalog→Catalog conformance fan-out. |
| CTX-1…5 | High | Every documented integration-event contract is wrong. Four published MediaItem events undocumented entirely; **every** contract omits the trailing `EventVersion` and five rename the timestamp field (a different JSON property on the wire); `MediaItemApproved` declares a `Title` that doesn't exist and omits three real fields; `MediaItemSubmittedForReview` has **5 of 8 documented fields that don't exist**; both MediaProfile contracts miss 4-5 fields each. |
| CTX-9 | High | `BulkFolderImportJob`/`BulkMediaImportJob` described in the **present tense with implementation detail** ("splits into chunks of 200", "issues pre-signed upload URLs"), no caveat. Zero occurrences in `src/`. `business-scenarios.md:44-45` already marks them "⚠ intent only, not built" — the two files contradict each other. **Fix belongs on the overview side; the aggregates are MM-036/MM-037's.** |
| CTX-12 | High | Coupling rule names `MediaItem.ActiveMediaChangeRequestId` — **zero occurrences** in `src/` or `tests/`. The change-request link is not a field on the aggregate; it's the `ChangeRequestReference` write-side index, which the same document describes correctly 100 lines later. |
| CTX-15 | High | The MediaItem event-flow block names **five domain events that do not exist** (`MediaItemRevertedToDraft`, `MediaItemCheckedOut`/`In`, `MediaItemCheckoutAbandoned`/`ForceReleased`). Checkout is modelled as an edit session. |
| CTX-6,8 | Med | `MediaItemCreated` enrichment credited to `IMediaItemProfileQueryService` — **zero occurrences**; it's a straight read off the event's own snapshot. Three consumer class names wrong, including `CollectionArchiveFanOutJob` — the name `archive-fan-out.md` would be searched by, which finds nothing. |
| CTX-10,11 | Med | "Five platform-level profiles are seeded" — seven are (see MP-6); every seeded profile carries `VersionControl`, which the Governance column never mentions. The "Owns" table **lists one table twice and omits fourteen** — including `media-catalog-folder-folders-index`, on which the fan-out spec's whole reachability argument turns. |
| CTX-13,14,16 | Med | `RegistrationIds` documented as append-only; `Apply(RegistrationRefRemoved)` removes (`MediaItem.cs:1580`). MediaProfile pin validation reads **Catalog's own index**, not Metadata's table — the difference between a synchronous cross-context read and an eventually-consistent local one. Lifecycle line names `Withdrawn` as a status (it isn't — `MediaItemWithdrawn` carries `RestoredStatus`) and omits `Revising`. |
| CTX-17 | Med | Every "Downstream" row names a context and events with **no subscriber** — Search/Discovery, Billing, Notifications. The SNS allowlist carries only `media.collection.archived`, and `ConsumerRegistrations.cs:148-150` states the non-subscription deliberately. As written, someone could code a filter policy against them. |
| CTX-18 | Med | `DocumentSigningSaga` "manages checkout lock during signing" — it exists only inside a doc-comment. Consistent with the repo's known-deferred list; mark it. |
| CTX-19 | Low | Collection/Folder/MediaProfile flow blocks omit real events — the whole MediaProfile draft-mutation set among them. |
| **SAGA-1** | **High** | **X-11.41 is wrong.** The spec (`:264-265`, `:379`) and a code comment (`ArchiveFanOutCascade.cs:45-46`) both claim `FolderMediaItemsIndex` is add-only, so the cascade archives items already moved out. **Two remove-side projectors exist and are registered** (`ServiceCollectionExtensions.cs:367-368`). The "moved out" case is handled. **Retire the finding** — and see D-1 for the defect that is actually there. |
| SAGA-2 | High | → D-1. |
| SAGA-3 | Med | Two sections still describe the **pre-X-11.15** re-entrant mechanism. Since X-11.15 the collection path never enters `FolderArchiveFanOutWorker`; the refusal now comes from a per-item guard at `ArchiveFanOutCascade.cs:306-325`. The file says this correctly 100 lines earlier — it contradicts itself. X-11.17's *conclusion* still holds. |
| SAGA-4 | Med | The folder path walks the subtree **three times**, not twice — `CountDescendantFoldersAsync` runs a full traversal and throws it away. All three are on the 29-second budget the spec is worried about. Plus D-10. |
| BIZ-1,2 | Low | The two "not built" rows are correct and are the only place that says so (→ CTX-9). Three index titles stale — one meaningfully: "MI-2 **Change Request** Rejection then Approval" points back at the CR-gated model removed 2026-06-02. |

**Verified correct, recorded so it isn't re-litigated:** the archive spec's central claim (these are
*not* sagas — no state row, no `ISagaRepository`, nothing archive-related in `SagaRegistrations`); the
three-phase mechanism, 16-permit semaphore, leaf-first ordering, ancestor suppression,
`ArchiveFanOutReport`, `errorCode`-based already-archived classification, the 500-folder pre-flight cap,
`ArchiveFolderNodeCommand`'s de-re-entrancy and "not HTTP-reachable" claim, the log lines, the named test
files, and the X-11.19 environment split — all check out. So do the `media.item.*` naming correction, the
Metadata row, the ChangeRequests row, the whole `ChangeRequestReference` block, folder max depth 10, and
all internal links. On MediaProfile: all 22 routes with exact verbs and templates; every status code
including the single-clock-read publish response; the nine-member `Capability` enum; the entire collision
resolution algorithm; all four read models, tables and projectors; `CompiledMetadataTemplateMapper`'s
eight fields; and the name-reservation compensation shapes.

---

# 4. Reconciliation with MM-022, MM-036, MM-037

MM-022's Catalog section (C.1–C.5) is `Done` and archived; C.6 split to `bulk-import` on 2026-09-01.
This pass was run independently and then checked against those closed rows.

**No closed row has regressed.** Two moved in the right direction and one left residue.

| MM-022 row | State now | Note |
|---|---|---|
| **CO-4** — "handler performs **no** published-profile check" | **Fixed in code since.** `CreateCollectionCommandHandler.cs:27-45` now checks existence and `IsPublished()`, returning `MediaProfileNotFound`/`MediaProfileNotPublished` — with a comment citing CO-4 by name. | Stayed closed; code side improved. My COL-13 (documented error set omits `404`/`422`) is the *spec* half that was never updated to match. |
| **MP-1** — compiled fields never projected | **Stayed closed.** `CompiledMetadataTemplateMapper` projects them onto both detail and version-detail rows. | Confirmed. |
| **MI-10** — `AllowsConcurrentEdit` not discoverable | **Stayed closed.** Present at `CompiledMetadataField.cs:40` and on the read model. | Confirmed. |
| **C-3** — "five Catalog endpoints return 202; code follows `bulk-operations.md`" | **Code changed after this row closed.** Both bulk endpoints now return `201`/`200` with an explicit comment: *"processed by the time this returns, so 202 would be untrue."* | ⚠ **`folder.api.md` was swept to `200`; `collection.api.md:332` still says `202`.** That is COL-5 — residue from the C-3 fix, and a textbook instance of the sibling-divergence pattern in the headline. |
| **C-2** — authz | Untouched, correctly. | ⊘ deferred to MM-028/MM-029. MP-22 is documentation about an implemented guard, not an auth finding. |
| **F-6 / C.6** — bulk import | Untouched. | FLD-10 and CTX-9 report only the *references* from in-scope files, which carry no unbuilt banner. Both fixes are one-line banners; **the aggregates remain MM-036/MM-037's**. |
| **MI-7** — OpenSearch strict-mapping `MediaItemId` vs `Id` | Marked closed; **not re-verified here.** | See § 5 — the full field-by-field diff of `MediaItemsIndexMapping` against `MediaItemDetailReadModel` was out of module scope and is worth its own pass, given `dynamic: "strict"`. |

**One correction for `MEMORY.md`:** it lists `MediaItemReviewSaga` as "partial — missing closing
handlers". It is **absent**, removed 2026-06-02 per `mediaitem.write-model.md:1181-1183`; the only copies
on disk are in stale agent worktrees. The repo `CLAUDE.md` carries the same stale claim.

---

# 5. Could not verify

Listed rather than guessed at, per the MM-022 rule.

1. **`MediaItemsIndexMapping` field-by-field against `MediaItemDetailReadModel`.** Outside the module
   tree. Given `dynamic: "strict"` and that the read model carries `Id`, `MetadataAttributor`,
   `EditSessionEditors` and others, this deserves its own pass — it is the same defect class as the
   closed MI-7.
2. **Whether `MediaItemDetailProjector` writes to OpenSearch.** `mediaitem.read-model.md:246` and the
   class comment say yes; the class contains no OpenSearch client. `:183-184` says indexing is done by
   `MediaItemSearchIndexSchema` in the `Projectors.Search` host. The two spec statements are consistent;
   which describes the running path was not confirmed.
3. **Whether `MediaProfileByNameIndex` GSI1SK is rewritten on a name change.** Bears on D-5 — if the
   platform rewrites index attributes on every upsert, the stale key follows from D-5; if not, it is a
   second defect. Needs the projection-store write path in `aspnetcore-platform`.
4. **Whether the archive cascade is synchronous in production.** The X-11.19 split (folder in-request,
   collection async over SQS on prod) is an environment claim depending on `EventConsumers` host wiring.
5. **Whether the seven default profiles are seeded at tenant provisioning or only via the operator CLI.**
   `SeedDefaultProfilesService` exists; its call sites were not traced into a provisioning pipeline.
   Bears on MP-20.
6. **Whether the `primary`→`original` seeded role rename was deliberate.** The code is annotated
   authoritative and `AddAssetDefinitionHandler.cs:59-65` hard-codes `"original"` for back-compat, which
   suggests yes — but no decision record was found. **Confirm before editing `defaults.md`** (MP-6b).
7. **`GET /v1/folders` with `collectionId` omitted** — `ListFoldersEndpoint.cs:52` calls
   `CollectionId.From` with no null check and the endpoint summary wrongly says the parameter is
   optional. Whether that is a `400` or a `500` needs `Id<T>.From`'s null behaviour plus FastEndpoints'
   binding failure path.
8. **Integration-test coverage.** `tests/integration/modules/Catalog/` could not be enumerated —
   repeated `find` calls timed out on the network mount. All test citations above are unit tests.
9. **CDK-side GSI provisioning.** Index names and key shapes were verified against
   `Catalog.ReadModel.Infrastructure/Queries/Schemas/**` only.
10. **Platform-internal behaviour** — `Idempotency-Key` middleware insertion, `ProjectedVersion` dedup
    short-circuiting, `INameReservationService` `ConsistentRead`. Unchanged from MM-022 § K.

---

# 6. If this goes anywhere

**§ 1 is the part that costs something.** D-1 (cascade blindness, including the retention-lock bypass)
and D-2 (archived children returned) are the two I would not leave sitting. Both are silent, both have
tests that pass, and both are data-correctness rather than contract-shape.

**The spec-side volume is real but it is not 95 separate jobs.** It is roughly six file sweeps —
`collection.*`, `folder.scenarios.md`, `mediaitem.scenarios.md`, `mediaprofile.defaults.md`,
`mediaprofile.write-model.md`, `context-overview.md` — each of which accounts for a cluster. Sequencing
by file rather than by finding would collapse most of it.

**One process note.** Several findings exist because a correction was applied to one aggregate and not
its sibling, or to one section and not the one contradicting it 100 lines away. A remediation pass that
greps for the *claim* rather than editing the *row* would close more per unit of effort — and would stop
this file's successor from reporting the same shape again in six weeks.

> **Editing reminder:** per repo `CLAUDE.md`, edit files under `docs/spec/` **in place, section by
> section**. Do not regenerate a file top to bottom — that is what truncated 18 files in 2026-08. Run
> `python3 .github/scripts/check-spec-truncation.py --root docs/spec` before pushing.
