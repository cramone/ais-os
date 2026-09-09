# Catalog — Code Defects and Open Decisions

_magiq-media · 2026-09-07 · Chase Ramone_

**What this file is.** The residue of the Catalog spec ↔ repo drift review after the spec rewrite. The
~95 findings where the **spec** was wrong are gone — corrected in place on 2026-09-07. What remains is the
two categories the spec cannot fix by describing them:

- **§ 1 — Code defects (D-1…D-15).** The spec is right and the code is wrong.
- **§ 2 — Open decisions (U-1…U-6).** Spec and code disagree and it is not obvious which should move.

**Every row is marked in the spec.** Each carries its `file:line` so the marker and the work stay together
— the spec tells a reader the behaviour is defective, this file tells you what to do about it.

**Evidence** for every row is in [`catalog-spec-drift-2026-09-07.md`](./catalog-spec-drift-2026-09-07.md),
which keeps the full `file:line` citations on both sides.

**Scope note.** Bulk import (`BulkFolderImportJob`, `BulkMediaImportJob`) stayed out — that is
MM-036/MM-037. Authorization is D-15 and belongs to the Catalog authorization workstream, not here.

---

## 1. Code defects

Ordered by what I'd fix first. Severity is the drift review's.

### 1.1 Silent data loss and wrong results

#### D-1 · `MediaItemAssignedToFolder` never enters `FolderMediaItemsIndex` · **High**

**The archive cascade cannot see items assigned after creation.** `FolderMediaItemsIndex` is written on
`MediaItemCreated` (folder-scoped) and `MediaItemMoved` only. First assignment emits a third event,
`MediaItemAssignedToFolder`, for which **no write-side index projector exists**.

Such an item is invisible to `ArchiveFanOutCascade` — not archived, not counted, not in `Failures` — so
`report.IsComplete` returns true and the folder archives anyway. The same index backs the registration
pre-flight, so **a retention-locked item assigned after creation also passes that guard**.

| | |
|---|---|
| **Fix** | Add a `FolderMediaItemsIndex` projector for `MediaItemAssignedToFolder`, mirroring `FolderMediaItemsIndexMoveAddedProjector`. Register it alongside the other three. Add a negative test — assert the item *is* dispatched an archive command |
| **Code** | `Catalog.WriteModel.Infrastructure/Indexes/Projectors/Folders/`, registered in `ServiceCollectionExtensions.cs:363-368` |
| **Marked in spec** | `sagas/archive-fan-out.md:201` · `folder.scenarios.md:84` · `mediaitem.scenarios.md:387` · `collection.scenarios.md:133` |

**Note the spec's own claim that the index is add-only is false** — the remove-side projectors exist and
are registered. That claim was retired in the rewrite; the gap is on the *add* side, and only for first
assignment.

#### D-2 · `GET /v1/folders/{folderId}/children` returns archived children · **High**

The exclusion is implemented as `ListChildrenInFolderQuery.Matches`, and **`Matches` is evaluated only by
`InMemoryProjectionStore`** — confirmed in the platform SDK at
`Magiq.Platform.Projections.Abstractions/Stores/IIndexQuery.cs:20-24`. `DynamoDbProjectionStore` builds a
key condition with no filter expression and never calls it. Meanwhile `FolderChildByNameIndexSchema` writes
its keys unconditionally, so archived rows keep their index entries.

**The unit test passes because it runs against the in-memory store** — the one store that honours `Matches`.

| | |
|---|---|
| **Fix** | Make `FolderChildByNameIndexSchema` sparse on `Status != "Archived"`, returning nullable keys — mirror `PublicCollectionByNameIndexSchema`, which gets the equivalent case right. Cover it with a test that does not use the in-memory store |
| **Then** | Grep the codebase for other `IIndexQuery.Matches` implementations carrying filter logic. This pattern is not confined to Catalog, and every instance is a silent filter that does nothing in production |
| **Marked in spec** | `folder.read-model.md:150` · `folder.api.md:607` |

#### D-3 · Setting a default profile rewrites the collection's `CreatedAt` · **High**

`CollectionSummaryProjector`'s `CollectionDefaultProfileSet` handler writes
`current with { CreatedAt = e.OccurredAt, UpdatedAt = e.OccurredAt, … }`. Every sibling handler in the
class touches `UpdatedAt` only. `GET /v1/collections` reads this model, so the creation date a user sees
changes when an unrelated field is set.

| | |
|---|---|
| **Fix** | Drop `CreatedAt = e.OccurredAt`. Then decide whether the handler should exist at all — `CollectionSummaryReadModel` has no `DefaultMediaProfileId` field, so the spec says this event should not reach the summary projector |
| **Code** | `Catalog.ReadModel/Projectors/Collections/CollectionSummaryProjector.cs:46-49` |
| **Test gap** | `CollectionSummaryProjectorTests` covers the other six events and not this one |
| **Marked in spec** | `collection.read-model.md:103` |

#### D-4 · Conformance changes are under-reported, two ways · **High**

**D-4a — count comparison.** `MediaItem.cs:1198-1201`:
`if (newStatus == ConformanceStatus && ConformanceGaps.Count == newGaps.Count) return Unit.Value;`
Two gaps replaced by two *different* gaps — what a profile re-publish that swaps which required role is
missing produces — emits nothing. Both read models keep the stale gaps permanently.

**D-4b — all-or-nothing resolution.** `MediaItem.cs:1646-1666` emits only `if (remaining.Count == 0)`.
Resolving 3 of 4 gaps emits nothing and the read model keeps showing the resolved gap.

| | |
|---|---|
| **Fix** | Compare set *contents* rather than `Count` in `UpdateConformanceStatus`; emit whenever `remaining.Count != ConformanceGaps.Count` in `TryResolveConformanceGaps`, carrying `remaining` |
| **Marked in spec** | `mediaitem.write-model.md:375` |

#### D-5 · `MediaProfileDetailProjector` never refreshes `Name`/`Description` on publish · **High**

Publishing a renamed draft is explicitly supported — the handler checks name availability on rename and
the aggregate applies the new name. But the detail projector's `MediaProfilePublished` branch sets status,
version, asset definitions, record type refs, all four policies, capabilities, compiled fields and draft —
**and not `Name` or `Description`.** The summary projector does set them.

After a rename-on-publish: `GET /v1/profiles/{id}` returns the old name, the two read models disagree, and
the `MediaProfileByNameIndex` sort key stays derived from the stale value.

| | |
|---|---|
| **Fix** | Add `Name` and `Description` to the publish branch |
| **Code** | `Catalog.ReadModel/Projectors/MediaProfiles/MediaProfileDetailProjector.cs:95-120` |
| **Open question** | Whether the GSI1SK self-corrects on the next upsert — see § 3 |
| **Marked in spec** | `mediaprofile.read-model.md:160` · `mediaprofile.api.md:534` |

### 1.2 Missing guards

#### D-6 · `UpdateAssetDefinition` renames a role with no uniqueness check · **High**

`UpdateAssetDefinitionCommand` carries `NewRoleName`, publicly exposed on the request DTO, and
`MediaProfile.cs:628-636` applies the rename with **no check that the new name is unused** — while
`AddAssetDefinition` does check, at `MediaProfile.cs:132-135`. Role-name uniqueness within a draft is a
stated invariant.

Renaming one role onto another's name produces two definitions sharing a `RoleName` in the same draft,
which then compiles into the published snapshot.

| | |
|---|---|
| **Fix** | Guard the rename in `MediaProfile.UpdateAssetDefinition` |
| **Also** | The rename capability itself was undocumented; the rewritten spec now describes it |
| **Marked in spec** | `mediaprofile.write-model.md:311` · `mediaprofile.api.md:182` |

#### D-7 · No publish-time reviewer guard exists anywhere · **High**

The spec states `ReviewerIsInitiator` as an invariant and documents the `422`. `MediaItem.cs:912-915`
claims in a comment that the handler enforces `MinimumReviewersRequired`, `ReviewerIsInitiator` and
reviewer uniqueness under `ReviewPolicy = RequiredForPublish`.

`PublishMediaItemHandler.cs:12-94` does none of it — profile-usability, required-role and asset-Active
checks only. It never reads `profile.ReviewPolicy`, never compares `command.RequestingUser` against
`command.InitialReviewers`, and never de-duplicates. `RequestPublication` has no reviewer checks either.
`ReviewerIsInitiator` appears in `src/` in exactly two places, both comments, and in no error-code
constant.

**A user can publish an item and list themselves as its sole reviewer.**

| | |
|---|---|
| **Fix** | Implement the three checks in `PublishMediaItemHandler` with coded errors, **or** delete the invariant row, the documented `422` and both comments |
| **Do not** | Leave it as a comment describing a guard that isn't there — that is what made this expensive to find |
| **Marked in spec** | `mediaitem.write-model.md:103` · `mediaitem.api.md:419` · `mediaitem.scenarios.md:145` |

#### D-8 · The `Url` field-type format rule is documented as live and implemented nowhere · **High**

The spec states that a value on a field whose `FieldType` is `Url` must be an absolute `http`/`https` URI
of at most 2048 characters, "enforced on every value". The section carried no unbuilt banner.

`MetadataConstraintValidator.cs:57-74` runs six checks — `Length`, `Pattern`, `Range`, `DateRange`,
`AllowedValues`, `SelectionCount`. **`field.FieldType` is never read anywhere in the file.** A `Url` field
accepts `"not a url"`.

| | |
|---|---|
| **Fix** | Add a `ValidateUrlFormat` gated on `FieldType == "Url"`. The rule is conjunctive with any `MinLength`/`MaxLength`/`RegexPattern` |
| **Marked in spec** | `mediaitem.write-model.md:438` · `mediaitem.scenarios.md:440` |

### 1.3 Data collected and discarded

#### D-9 · Withdraw requires a `reason` and throws it away · **High**

`WithdrawMediaItemRequest.Reason` is declared non-nullable — required on the wire — and the endpoint
threads it into the command. The handler forwards to `MediaItem.Withdraw(requestedBy, withdrawnAt)`, which
**takes no reason**, and emits `MediaItemWithdrawn(..., string.Empty, ...)` at `MediaItem.cs:1292`.

The caller is compelled to supply a withdrawal reason that is never stored, never appears on the event, and
never reaches `MediaItemWithdrawnIntegrationEvent`. **On a records platform a discarded audit reason is
worse than no field at all.**

| | |
|---|---|
| **Fix** | Thread `reason` through `Withdraw` onto the event and the integration event, **or** drop it from the request DTO and the command |
| **Marked in spec** | `mediaitem.write-model.md:361` and `:545` · `mediaitem.api.md:467` · `mediaitem.scenarios.md:255` |

#### D-10 · Cascade descendants lose the caller's `ArchivedDate` · **Medium**

`ArchiveFolderNodeCommand` carries an optional business date which flows to `Folder.Archive` and onto
`FolderArchived`. `ArchiveFolderHandler.cs:91-93` passes `command.ArchivedDate` for the root;
`ArchiveFanOutCascade.cs:273` dispatches with three arguments, so **every descendant gets `null`**.

This contradicts `ArchiveFolderNodeHandler.cs:15-17`'s own stated reason for existing — that both paths
archive a folder identically.

| | |
|---|---|
| **Fix** | Thread `ArchivedDate` through `RunAsync` |
| **Blocked by** | D-11 — currently masked, because no caller can set the field at all |
| **Marked in spec** | `sagas/archive-fan-out.md:108` · `folder.scenarios.md:79` |

#### D-11 · `archivedDate` and `closedDate` have no wire path · **High** / **Medium**

`ArchiveFolderEndpoint.cs:5` is a `CatalogEndpointWithoutRequest` — no request DTO at all — and line 40
builds the command leaving `ArchivedDate` at its null default. **`archivedDate` is `null` on every folder
in the system.**

Same shape for `closedDate`: `CloseFolderEndpoint.cs:5,40` is request-less, the command parameter exists
but only `Folder.Create` can populate the field — while the endpoint's own OpenAPI summary at
`CloseFolderEndpoint.cs:25-26` advertises "an optional business-supplied closed date", which is
unreachable.

| | |
|---|---|
| **Decide** | Are these real business fields? If yes, add the request bodies. If no, strike them from the write model and fix the misleading endpoint summary |
| **Related** | A specified-but-unbuilt rule makes `closedDate` **required** on close (`400 ClosedDateRequired`, and not in the future), as the clock source for a `Closure` retention trigger. Shipping that is a breaking change to a call that currently succeeds with no body |
| **Marked in spec** | `folder.write-model.md:49` · `folder.api.md:373`, `:389`, `:561` |

### 1.4 Smaller items

#### D-12 · A live route silently sets the opposite review policy · **High**

Not strictly a code defect, but the failure mode belongs here. The spec documented the body of
`PUT /v1/profiles/{profileId}/review-policy` as `{ "reviewPolicy": ... }`; the bound DTO is
`SetReviewPolicyRequest.Policy`, and `ReviewPolicy`'s first enum member is `None`.

A client following the spec sends an unmatched property, `Policy` binds to `None`, **the call sets the
opposite of what was asked and returns `204`.** Nothing validates it.

Two sibling routes have the same mismatch with milder outcomes — `acceptedContentTypes` →
`AllowedMediaCategories` (`422`) and `version` → `NewVersion` (`404`).

| | |
|---|---|
| **Done** | The spec is corrected — all three field names now match the DTOs |
| **Consider** | Whether an unmatched-property binding failure should be a `400` platform-wide. This class of bug is silent by construction, and the spec being right is the only thing currently preventing it |
| **Marked in spec** | `mediaprofile.api.md:296` · `mediaprofile.scenarios.md:89` |

#### D-13 · `RejectMediaItemCommand`/`Handler` is an unreachable duplicate · **Medium**

A verbatim duplicate of `RejectReviewCommand`/`Handler`, both calling `mediaItem.RejectReview(...)`.
`RejectMediaItemEndpoint.cs:48` dispatches `RejectReviewCommand`, so the duplicate has no caller.

**Fix:** delete it. **Marked in spec:** `mediaitem.write-model.md:365`.

#### D-14 · `AddAssetDefinition`'s auto-default reads the published list, not the draft · **Medium**

`AddAssetDefinitionHandler.cs:34` forces `IsDefault = true` on the first asset definition added — but tests
emptiness against `profile.AssetDefinitions` (**published**) rather than `profile.Draft.AssetDefinitions`.
On a revision draft of a published profile the auto-default never fires; on an initial draft it fires on
*every* add until the first publish.

Alongside it, `:50-79` force-defaults the role literally named `"original"` on the profile named
`"All Media"` for an Enterprise-driver client — gated on two string comparisons, documented nowhere until
this rewrite.

| | |
|---|---|
| **Fix** | Correct the draft-vs-published read; put the back-compat transform behind something more durable than two string comparisons |
| **Marked in spec** | `mediaprofile.write-model.md:315` |

#### D-15 · No ownership authorization anywhere in Catalog · **High** — *owned elsewhere*

No Collection, Folder, MediaItem or MediaProfile command performs an ownership check at any layer — not an
endpoint policy, not a handler guard, not an aggregate refusal. Any authenticated tenant member can act on
any other member's resources, **including `ArchiveFolder`, which cascades across a whole subtree**.

The five MediaProfile governance routes are the only guarded commands, via
`ProfileGovernanceAuthorization` → `TenantAdministratorRequired`. That code has no row in
`error-catalog.md`.

Publish, archive and withdraw also skip the edit-session guard, so **any member can drive an item's
lifecycle while another user holds it checked out**, closing their session underneath them. Folder
assignment and move are guarded by nothing at all — not status, not archive state, not checkout.

| | |
|---|---|
| **Owner** | The Catalog authorization workstream. **Not this file's to plan** — recorded because the rewritten spec now states the intended contract and marks it unenforced, so the two must not drift again |
| **Marked in spec** | `collection.api.md:61` · `folder.api.md:79` · `mediaitem.api.md:89` |

---

## 2. Open decisions

These need a call before anyone edits either side. The spec states current behaviour and marks the
question; it does not pre-empt the answer.

### U-1 · Metadata batch write — merge or replace? · **High**

The API spec carried a ⚠ banner: *"complete replacement of `Metadata.Draft`. Entries omitted from the
`fields` array are cleared."* `MediaItem.cs:1402-1413` seeds a dictionary from the existing draft and
assigns only the supplied entries. **Nothing clears omitted keys.**

Compounding it: `SetMetadataBatchHandler.cs:74-82` `continue`s past a `JsonValueKind.Null` entry on a
non-required field — neither written nor cleared — and returns `204`. **So there is currently no way to
remove a metadata key through the API at all**, and a client following the documented contract silently
keeps values it believes it deleted.

**Replace is the documented contract and the more defensible one**, but implementing it is a behaviour
change with an event-replay consequence. Worth a decision, not a quiet edit.

**Marked in spec:** `mediaitem.api.md:334`, `:547` · `mediaitem.scenarios.md:488`

### U-2 · Unassign asset — `200` with a body, or `204`? · **High**

`UnassignAssetFromRoleEndpoint.cs:64` sends `SendOkAsync(new UnassignAssetFromRoleResponse(...))`. It is
**the only MediaItem write endpoint that returns a body** — every sibling uses `SendNoContentAsync`. The
spec said `204`.

Pick one. If the body stays, it needs documenting as a deliberate exception; the rewritten spec currently
documents the `200` and flags it.

**Marked in spec:** `mediaitem.api.md:387`

### U-3 · Deprecated RecordType fields — emitted or excluded? · **High**

`mediaprofile.write-model.md` recorded a 2026-09-07 ruling: deprecated fields "**are emitted, carrying
`IsDeprecated: true`, and are counted toward collisions**", with 35 lines of justification resting on
`MediaProfileSnapshotField.IsDeprecated`.

`MediaProfileDomainService.cs:118` does `.Where(f => !f.IsDeprecated)`, dropping them before candidates are
collected. **And the carrier does not exist**: neither `CompiledMetadataField` nor
`MediaProfileSnapshotField` has an `IsDeprecated` member, so the MediaItem guards the ruling says read it
are reading a field that has never existed.

**This is the root of a second finding.** Six `MediaProfileSnapshotField` members the MediaItem write model
depends on don't exist — `IsDeprecated`, `IsSearchable`, `DisplayName`, `Description`, `Group`, `Order` —
so the deprecation guards at `MediaItem.cs:936-947`, `:1043-1050` and `:1094-1103` are absent.
**RecordType's `DeprecateFieldInRecordType` valve currently releases nothing.**

The source data *is* available: `RecordTypeFieldDetailDto.IsDeprecated` is on the reference DTO.

**Either** implement — add the member in both places, drop the `.Where` — **or** downgrade the section to
designed-not-shipped. It was reading as current behaviour and was not; the rewrite marks it unbuilt in the
interim.

**Marked in spec:** `mediaprofile.write-model.md:165` · `mediaitem.write-model.md:444`

### U-4 · Compiled-template ordering and `Group` sectioning · **High**

`mediaprofile.write-model.md` stated a normative rule about sectioning on `(RecordTypeId, Group)` and
rendering in pin order. **Neither `Group` nor `Order` crosses the context boundary** —
`RecordTypeFieldDetailDto` carries neither, `CompiledMetadataField` has neither member, and
`CompileTemplateAsync` emits fields in bare-name first-appearance order with no sectioning and no sorting.

Same shape as U-3: implement, or mark it designed. **A 100-field schema with no sectioning is unusable**,
which is the argument for implementing.

**Marked in spec:** `mediaprofile.write-model.md:168` · `mediaitem.write-model.md:152`

### U-5 · Can an archived collection still be mutated? · **Medium**

Only `Rename` and `Archive` guard on `IsArchived`. `ApplyTags`, `SetDefaultMediaProfile`, `SetVisibility`
and `UpdateDescription` carry no archived check, so **an archived collection can still be tagged,
re-profiled, re-described and made `Public`**.

The visibility case is the one that matters. Whether archive should freeze the aggregate is undecided —
the spec states current behaviour rather than an intended contract.

**Marked in spec:** `collection.write-model.md:87`

### U-6 · Declared-set vs compiled-union capabilities · **Medium**

`mediaprofile.write-model.md` stated a 2026-09-04 ruling (yours) that `MediaProfileSnapshot.Capabilities`
carries `MediaProfile.Capabilities`, not the compiled union, and that "no guard reads" the union.

`CompiledMetadataTemplate.ToSnapshot()` does the opposite, and `PublishMediaProfileHandler.cs:75-77`
short-circuits to an empty capability list when no RecordType is pinned — so **a capabilities-only profile
declaring `Processing` ships an empty set and gets no processing.**

The file contradicted itself: one section said the union **is** the `Processing` gate and is read; another
said no guard reads it. `mediaprofile.design-decisions.md` settles it in favour of "it is read", and the
code agrees — so the rewrite states the union as current behaviour and marks the ruling as a fix candidate.

**Fix candidate:** `ToSnapshot()` emits the declared set. One line, and it makes the gate read what the
author declared. **Observable** for any profile relying on inheriting `Processing` from a pinned
RecordType, so it needs a `dev`/`qa` audit first.

**Marked in spec:** `mediaprofile.write-model.md:212`

---

## 3. Still unverified

Carried forward from the drift review. Each would need its own pass.

1. **`MediaItemsIndexMapping` field-by-field against `MediaItemDetailReadModel`.** Outside the module tree.
   Given `dynamic: "strict"` and that the read model carries `Id`, `MetadataAttributor`,
   `EditSessionEditors` and others, this deserves its own pass — it is the same defect class as MM-022's
   closed MI-7, which took the whole index down over a single field-name mismatch.
2. **Whether `MediaItemDetailProjector` writes to OpenSearch.** The read-model spec and the class comment
   say yes; the class contains no OpenSearch client. Which describes the running path was not confirmed.
3. **Whether `MediaProfileByNameIndex` GSI1SK is rewritten on a name change.** Bears on D-5 — if the
   platform rewrites index attributes on every upsert, the stale key follows from D-5; if not, it is a
   second defect.
4. **Whether the archive cascade is synchronous in production.** The environment split (folder in-request,
   collection async over SQS on prod) depends on `EventConsumers` host wiring.
5. **Whether the seven default profiles are seeded at tenant provisioning or only via the operator CLI.**
   `SeedDefaultProfilesService` exists; its call sites were not traced into a provisioning pipeline. The
   spec now states CLI-only.
6. **Whether the `primary` → `original` seeded role rename was deliberate.** The code is annotated
   authoritative and the handler hard-codes `"original"` for back-compat, which suggests yes — but no
   decision record was found. **The rewritten `defaults.md` documents `original`; confirm before relying
   on it.**
7. **`GET /v1/folders` with `collectionId` omitted** — `ListFoldersEndpoint.cs:52` calls
   `CollectionId.From` with no null check. Whether that is a `400` or a `500` needs `Id<T>.From`'s null
   behaviour plus FastEndpoints' binding failure path.
8. **Integration-test coverage.** `tests/integration/modules/Catalog/` could not be enumerated — repeated
   `find` calls timed out on the network mount. All test citations in the drift review are unit tests.
9. **CDK-side GSI provisioning.** Index names and key shapes were verified against the schema classes only.

---

## 4. Suggested order

**D-1 and D-2 first.** Both are silent, both have tests that pass, and both are data-correctness rather
than contract-shape. D-1 carries the retention-lock bypass, which is the sharpest thing in this file for a
compliance-grade platform.

**Then D-3, D-4, D-5** — three small projector fixes, all with the same shape: a handler writing a field it
shouldn't, or not writing one it should.

**Then the decisions.** U-3 and U-4 are the same shape and probably one piece of work — both need members
carried across the compile path, and both currently make a documented rule unreachable. U-1 is the one most
likely to be noticed by a client.

**D-15 is not yours to sequence here** — it belongs to the authorization workstream, and the only reason it
is in this file is that the spec now asserts an intended contract that code does not honour.

---

## Related

- [`catalog-spec-drift-2026-09-07.md`](./catalog-spec-drift-2026-09-07.md) — the full review, with
  `file:line` evidence on both sides for all 121 findings
- `D:\source\github\magiq-media\docs\spec\contexts\Catalog\` — the rewritten spec, where every row above is
  marked at the point it applies
