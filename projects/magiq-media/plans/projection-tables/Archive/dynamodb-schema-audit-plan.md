# DynamoDB Schema Audit & Correction Plan — CDK + Spec

**Status:** In progress. Started 2026-06-16. Catalog, AssetManagement, Registration, Metadata, ChangeRequests, Processing modules audited as of 2026-06-17 — DocumentSigning remains.
**Repos touched:** `cdk-magiq-media` (infra), `magiq-media` (app, read-only — source of truth), `aspnetcore-platform` (platform, read-only — source of truth), AIS-OS `spec/architecture/system-architecture.md` (docs).
**Why this exists:** The CDK and the spec both describe DynamoDB key schemas (PK/SK/GSI) that were found to be stale or wrong relative to the actual application code. Several rounds of this have already turned up real bugs (see "Already fixed" below). The remaining surface area — GSI/index schemas — has not been audited yet and is the same class of risk.
**Deploy note:** v1, no production data. All schema-changed tables can be recreated via full stack replace; no in-place migration needed. This removes the usual "DynamoDB can't add a sort key in place" blocker — fix forward, redeploy.

---

## How to verify one item (repeat for every row below)

1. **Read the schema class** in `magiq-media` (`*Schema.cs` under `Queries/Schemas/`, or the `AddProjectionSchema<T>(tableName, category)` call site if there's no custom schema class). This is ground truth for: PK attribute value pattern, SK attribute value pattern (and prefix, if any), and — for GSIs — `IndexName`, `PartitionKeySchema`, `SortKeySchema` attribute names.
2. **Read the CDK construct** in `cdk-magiq-media` (`write-indexes.construct.ts`, `read-models.construct.ts`, or `event-store.construct.ts`) for the matching table/GSI. Compare attribute names and types (not values — CDK doesn't encode value format, only attribute name + scalar type).
3. **Read the spec** in `spec/architecture/system-architecture.md` (DynamoDB tables section, ~line 380-500) for the matching row. Compare the documented PK/SK *value pattern* (this is where the spec actually claims something CDK doesn't — CDK only needs attribute names/types right; the spec needs to also describe the value shape correctly).
4. **Fix CDK** if attribute name/type is wrong. Fix **spec** if the documented value pattern is wrong. They're usually both wrong together but not always — keep them as separate fixes.
5. Check the box. Note anything surprising in the "Findings" line under that module.

---

## Already fixed (do not redo)

- [x] `media-events` (event store) — CDK SK attribute renamed `AggregateVersion` → `SK`. Spec already correct.
- [x] `idempotency-keys`, `tenants` — verified correct, no change.
- [x] 12 write-index tables in `write-indexes.construct.ts` — converted PK-only → PK+SK (`catalogFolderRegistrationIndex`, `catalogFolderFoldersIndex`, `catalogFolderItemsIndex`, `catalogMediaProfileIndex`, `catalogMediaItemProfileIndex`, `catalogAssetToMediaItemIndex`, `catalogAssetRef`, `catalogVersionAssetRef`, `assetItemRef`, `assetProfileDefaultRef`, `processingAssetIndex`, `registrationItemRef`).
- [x] 3 orphaned write-index tables flagged (not fixed — no registration found): `catalogFolderStatusIndex`, `catalogFolderActiveItemCountIndex`, `referenceModels`.
- [x] All 23 base read-model tables in `read-models.construct.ts` — converted PK-only → PK+SK via the shared `simple` helper.
- [x] `changeRequestComments` — CDK SK attribute renamed `CommentId` → `SK` (value semantics unchanged, just the physical attribute name).

## Known but NOT yet fixed (carry into the per-module sections below)

- ~~**Spec PK/SK value patterns are wrong for most read-model rows.**~~ **Resolved for Catalog, AssetManagement, Registration, Metadata, ChangeRequests** — all base tables + write-indexes corrected in spec (category-partitioned scheme, PK = `TENANT#{TenantId}#{CATEGORY}`, entity ID in SK, often with a type prefix). Still applies to Processing, DocumentSigning rows — not yet re-derived, spec still shows the old uniform-and-wrong pattern for those.
- **GSI/index schemas (`IProjectionIndexSchema<TProjection,TQuery>`) — Catalog (9), Registration (2), Metadata (2), ChangeRequests (2) are now fully audited**, all correct, zero discrepancies once two fictional GSIs (Registration's `StatusIndex`, Metadata's `OwnerIndex`) were found and removed. The remaining GSIs across Processing are still unaudited.
- ~~**Two possible naming mismatches spotted but not confirmed**~~ — both **cleared**: `MediaProfileByVersionIndexSchema` and `RecordTypeVersionByVersionIndexSchema` both have literal `IndexName` strings that match CDK exactly; only their C# class names differ cosmetically from the IndexName string/CDK construct name.
- ~~**Registration anomaly:**~~ **Investigated, escalated, not fixed (by design — out of CDK/spec scope).** `RecordTypeVersionDetailReadModel` is registered against `media-record-types` rather than `media-record-type-versions`. Confirmed via git history (`eba2790`) this was a deliberate choice, not a copy-paste slip, but it's a half-migrated design matching neither the `media-item-versions` (shared-table) nor `media-profile-version` (dedicated-table) precedent, and no row-level collision occurs (groupKey-based PK partitioning). Three resolution options written up and escalated to Chase/Karen in the Metadata findings below — no app-code change made.
- ~~**`media-item-versions` and `media-profile-versions` each host two registrations**~~ — **Resolved.** `media-item-versions`: no collision, distinct `SUMMARY#`/`DETAIL#` SK prefixes, matching categories — intentional shared-table design, left as-is. `media-profile-versions`: found Summary/Detail used mismatched categories (`PROFILE_VERSIONS` vs `PROFILE_VERSION`), writing to two orphaned PK partitions on one table — Chase confirmed the fix is a dedicated Detail table; added CDK `media-profile-version` and repointed the C# registration. See Catalog findings.
- **DocumentSigning uses the 1-arg `AddProjectionSchema<T>(tableName)` overload** (no `category` string) for both `media-signing-session` and `media-signing-sessions` — confirm what `DefaultProjectionSchema<T>`'s schema identifier defaults to in this case (likely `typeof(T).FullName`, which would make the PK segment the full CLR type name — worth confirming since it's a different shape than every other module). Still open — not yet audited.
- **New from Catalog pass:** CDK's `write-indexes.construct.ts` doc-comments for several Catalog write-index tables are stale relative to the verified PK patterns (attribute names/types themselves are correct, just the comments). Optional cleanup, not blocking.
- **New from Catalog pass:** `AssetToMediaItemIndex` and `AssetStateReference` use an inverted discriminator/groupKey convention (literal constant as SK, real entity ID folded into PK via groupKey) — correct but non-obvious; worth keeping in mind if touching these or similar reference-model classes in other modules.

---

## Module sections

Each section lists the base-table schema(s) and GSI schema(s) owned by that module, with a checkbox per verification step. Work top to bottom; a module is "done" only when every box in it is checked and any findings are written up (or escalated, for app-code bugs that aren't CDK/spec's to fix).

### Catalog (Collections, Folders, MediaItems, MediaProfiles)

Base table schemas:
- [x] `media-collection` (Detail) — verified: PK `TENANT#{TenantId}#COLLECTION`, SK = bare `CollectionId`.
- [x] `media-collections` (Summary, `CollectionSummarySchema`) — verified: PK `TENANT#{TenantId}#COLLECTIONS`, SK `SUMMARY#{CollectionId}`.
- [x] `media-folder` (Detail, category `FOLDER`) — verified: PK `TENANT#{TenantId}#FOLDER`, SK = bare `FolderId`.
- [x] `media-folders` (Summary, category `FOLDERS`, no custom schema — default SK = bare discriminator) — verified: PK `TENANT#{TenantId}#FOLDERS`, SK = bare `FolderId`.
- [x] `media-folder-children` (`FolderChildSummarySchema`) — verified: PK `TENANT#{TenantId}#CHILDREN`, SK `SUMMARY#{FolderId}`.
- [x] `media-item` (Detail, category `ITEM`) — verified: PK `TENANT#{TenantId}#ITEM`, SK = bare `MediaItemId`.
- [x] `media-items` (Summary, category `ITEMS`) — verified: PK `TENANT#{TenantId}#ITEMS`, SK = bare `MediaItemId`.
- [x] `media-item-versions` — **two registrations on one table**: `MediaItemVersionSummarySchema` (SK `SUMMARY#{discriminator}`) + `MediaItemVersionDetailSchema` (SK `DETAIL#{discriminator}`), both category `ITEM_VERSIONS`. **No collision** — confirmed, prefixes are distinct and categories match.
- [x] `media-profile` (Detail, category `PROFILE`) — verified: PK `TENANT#{TenantId}#PROFILE`, SK = bare `MediaProfileId`.
- [x] `media-profiles` (Summary, category `PROFILES`) — verified: PK `TENANT#{TenantId}#PROFILES`, SK = bare `MediaProfileId`.
- [x] `media-profile-versions` / `media-profile-version` — **fixed 2026-06-16 per Chase.** Was: two registrations on one table (`media-profile-versions`) with mismatched categories (`PROFILE_VERSIONS` vs `PROFILE_VERSION`), splitting Summary/Detail into orphaned partitions on the same table. Chase confirmed the intended design is a dedicated Detail table (mirroring `media-profile`/`media-profiles`), so: added new CDK table `media-profile-version` (`read-models.construct.ts` — new `profileVersion` property, added to `this.all`), and repointed `MediaProfileVersionDetailSchema`'s registration in `Catalog.ReadModel.Infrastructure/ServiceCollectionExtensions.cs` from `"media-profile-versions"` to `"media-profile-version"`. Summary keeps `media-profile-versions` unchanged.

GSI schemas:
- [x] `CollectionByNameIndexSchema` — verified correct against CDK + spec.
- [x] `PublicCollectionByNameIndexSchema` — `IndexName` "PublicCollectionByNameIndex", GSI2PK/GSI2SK. Matches CDK.
- [x] `FolderByParentAndNameIndexSchema` — `IndexName` "FolderByParentAndNameIndex", GSI1PK/GSI1SK. Matches CDK.
- [x] `FolderHierarchyIndexSchema` — `IndexName` "FolderHierarchyIndex", GSI2PK/GSI2SK. Matches CDK.
- [x] `FolderChildByNameIndexSchema` — `IndexName` "FolderChildByNameIndex", GSI1PK/GSI1SK. Matches CDK.
- [x] `MediaItemByFolderIndexSchema` — `IndexName` "MediaItemByFolderIndex", GSI1PK/GSI1SK, sparse. Matches CDK.
- [x] `MediaItemVersionByMediaItemIndexSchema` — `IndexName` "MediaItemVersionByMediaItemIndex", GSI1PK/GSI1SK. Matches CDK.
- [x] `MediaProfileByNameIndexSchema` — `IndexName` "MediaProfileByNameIndex", GSI1PK/GSI1SK, lives on the `media-profile` (Detail) table by design (documented in CDK — `ListMediaProfilesQuery` needs the `Description` field, which only Detail carries). Matches CDK, not a bug.
- [x] `MediaProfileByVersionIndexSchema` — literal `IndexName` is **"MediaProfilesByVersionIndex"** (differs from the C# class name, but matches CDK exactly). Plan's suspected mismatch is **cleared** — no fix needed.

Write-side index tables (already PK+SK structurally fixed in CDK — this pass is about value-pattern accuracy in the spec, since the spec's write-index table currently has no PK/SK columns at all):
- [x] `FolderRegistrationIndex` — PK `TENANT#{TenantId}#MEDIA_ITEM`, SK bare `MediaItemId`.
- [x] `FolderFoldersIndex` — PK `TENANT#{TenantId}#FOLDER`, SK bare `ParentId` (FolderId or CollectionId).
- [x] `FolderMediaItemsIndex` — PK `TENANT#{TenantId}#MEDIA_ITEM`, SK bare `FolderId`.
- [x] `MediaProfileIndex` — PK `TENANT#{TenantId}#MEDIA_PROFILE`, SK bare `MediaProfileId`.
- [x] `MediaItemProfileIndex` — PK `TENANT#{TenantId}#MEDIA_PROFILE`, SK bare `MediaProfileId`.
- [x] `AssetToMediaItemIndex` — PK `TENANT#{TenantId}#ASSET#{AssetId}`, SK constant `ASSET`. Discriminator/groupKey args are inverted from the "obvious" reading (literal `"ASSET"` is the discriminator/SK, `AssetId` is the groupKey folded into PK) — correct behavior, just non-obvious.
- [x] `RecordTypeVersionReference` — two key shapes on one table: version rows PK `TENANT#{TenantId}#RECORD_TYPE#{RecordTypeId}` / SK bare `{Version:D10}`; deprecation sentinel PK `TENANT#{TenantId}#RECORD_TYPE#DEPRECATED` / SK bare `RecordTypeId`. Intentional per code comments (tenant-wide dedup partition for deprecated record types vs per-record-type version history).
- [x] `AssetStateReference` — PK `TENANT#{TenantId}#ASSET#{AssetId}`, SK constant `STATE`. Same discriminator/groupKey inversion as `AssetToMediaItemIndex`.
- [x] `MediaItemVersionAssetReference` — PK `TENANT#{TenantId}#VERSION`, SK bare `{MediaItemId}#{VersionNumber}`.

**Findings (Catalog):**
1. Category-partitioned PK scheme confirmed across every base table and write-index in this module — spec now corrected (read-model table + write-index table, both in `system-architecture.md`).
2. `media-item-versions` collision concern from "Known but not yet fixed" is **resolved — no collision**: Summary/Detail share category `ITEM_VERSIONS` but use distinct `SUMMARY#`/`DETAIL#` SK prefixes.
3. **App-code bug found and fixed (with Chase's sign-off):** `media-profile-versions` Summary and Detail schemas were registered against the same physical table with mismatched category strings (`PROFILE_VERSIONS` vs `PROFILE_VERSION`), splitting Detail rows into an orphaned partition. Chase confirmed the correct design is a dedicated Detail table — added CDK table `media-profile-version` and repointed the Detail registration at it. See checklist entry above for the exact diff locations.
4. `MediaProfileByVersionIndexSchema` index-name mismatch suspicion is **cleared** — literal `IndexName` matches CDK exactly; only the C# class name differs cosmetically from the CDK construct name.
5. All 8 remaining GSI schemas verified against CDK `read-models.construct.ts` — **zero discrepancies** found (index names + GSI1/GSI2 attribute names all match).
6. Two write-index tables (`AssetToMediaItemIndex`, `AssetStateReference`) use an inverted discriminator/groupKey convention — a literal constant (`"ASSET"`/`"STATE"`) as the SK and the real entity ID as the PK groupKey. Functionally correct, just worth knowing before touching these classes again.
7. CDK's `write-indexes.construct.ts` has stale doc-comments above several Catalog table declarations (describing PK shapes that don't match the verified patterns above). Attribute names/types themselves are correct (`PK`/`SK`, both String) so no functional CDK fix is needed, but flagging for an optional comment cleanup pass.

### AssetManagement

Base table schemas:
- [x] `media-asset` (Detail, category `ASSET`) — verified: PK `TENANT#{TenantId}#ASSET#{AssetId}`, SK constant `DETAIL`. Spec fixed (was showing `TENANT#{TenantId}#{AssetId}` / `—`).
- [x] `media-assets` (Summary, `AssetSummarySchema`) — verified: PK `TENANT#{TenantId}#ASSETS`, SK `SUMMARY#{AssetId}`. Spec fixed.

GSI schemas:
- [x] `AssetByMediaItemIndexSchema` — `IndexName` "AssetByMediaItemIndex", `GSI1PK` only (sparse, no GSI1SK), value `TENANT#{TenantId}#ITEM#{MediaItemId}#ASSETS`. Matches CDK exactly. Added to spec (was missing entirely from the GSI list).

Write-side index tables:
- [x] `MediaItemCapabilityReference` (`media-asset-item-ref`) — verified: PK `TENANT#{TenantId}#MEDIA_ITEM#{MediaItemId}`, SK constant `CAPABILITY`. Spec fixed; CDK doc-comment corrected.
- [x] `AssetProfileDefaultReference` (`media-asset-profile-default-ref`) — verified: PK `TENANT#{TenantId}#PROFILE_DEFAULT#{AssetId}`, SK constant `PROFILE_DEFAULT`. Spec fixed (was `—`/`—`); CDK doc-comment corrected.

**Findings (AssetManagement):**
1. `media-asset` (Detail) uses the same "inverted" discriminator/groupKey convention already seen in Catalog's `AssetToMediaItemIndex`/`AssetStateReference`: the literal constant `"DETAIL"` is the SK, and the real `AssetId` is folded into the PK via groupKey (`TENANT#{TenantId}#ASSET#{AssetId}`). This is genuinely different from every other Detail table verified in Catalog (`media-collection`, `media-folder`, `media-item`), which put the category alone in PK and the bare entity id in SK. Confirmed via `AssetDetailReadModel.CreateProjectionKey` → `ProjectionKey(tenantId, "DETAIL", assetId)` and its real call sites in `AssetDetailProjector`/query handlers — not dead code, this is the live key shape.
2. `AssetProfileDefaultReference` registers the same literal string (`"PROFILE_DEFAULT"`) as both the registration category (PK segment) and the per-instance discriminator (SK) — coincidental reuse of one constant for two different roles, not a bug, but worth knowing before refactoring either.
3. CDK structurally correct for all 4 base/write-index tables (PK+SK String via the shared helpers) and the GSI (GSI1PK String, no sort key) — no CDK schema changes needed, only doc-comment text was stale (now fixed in `write-indexes.construct.ts`).
4. `system-spec.md` (separate from `system-architecture.md`, not in this plan's normal scope) already had a correct row for `media-asset-item-ref` and a *coincidentally* correct-looking but actually wrong row for `media-asset` (it omits the `ASSET#` category segment from the PK — shows `TENANT#{TenantId}#{AssetId}` instead of `TENANT#{TenantId}#ASSET#{AssetId}`), and is missing `media-asset-profile-default-ref` entirely. Not fixed as part of this pass (out of scope per the plan's spec target), but flagging since `system-spec.md` is referenced elsewhere as a source of truth and will mislead anyone reading it for AssetManagement.
5. `AssetByMediaItemIndexSchema.cs`'s own XML doc comment text says "Targets the `AssetsByMediaItemIndex` GSI" (extra "s") but the real `IndexName` string is `"AssetByMediaItemIndex"` — internal comment/code mismatch in app code, not touched (app code is read-only source of truth per this plan; flagging only).

### Registration

Base table schemas:
- [x] `media-registration` (Detail, category `REGISTRATION`) — verified: PK `TENANT#{TenantId}#REGISTRATION#{RegistrationId}`, SK constant `DETAIL`. Same inverted Detail convention as `media-asset` (AssetManagement). Spec fixed (was `TENANT#{TenantId}#{RegistrationId}` / `—`).
- [x] `media-registrations` (Summary, `RegistrationSummarySchema`) — verified: PK `TENANT#{TenantId}#REGISTRATIONS`, SK `SUMMARY#{RegistrationId}`. Spec fixed.

GSI schemas:
- [x] `RegistrationByMediaItemIndexSchema` — `IndexName` "RegistrationByMediaItemIndex", `GSI1PK`/`GSI1SK`. `GSI1PK` = `TENANT#{TenantId}#ITEM#{MediaItemId}#REGISTRATIONS`, `GSI1SK` = `{InitiatedAt:O}#{RegistrationId}`. Matches CDK exactly. Added to `system-architecture.md` (was missing — that file instead listed a fictional `StatusIndex` that doesn't exist in code or CDK; removed).
- [x] `RegistrationByOwnerIndexSchema` — `IndexName` "RegistrationByOwnerIndex", `GSI2PK`/`GSI2SK`. `GSI2PK` = `TENANT#{TenantId}#OWNER#{OwnerId}#REGISTRATIONS`, `GSI2SK` = `{InitiatedAt:O}#{RegistrationId}`. Matches CDK exactly. Added to spec.

Write-side index tables:
- [x] `MediaItemReference` (`media-registration-item-ref`) — verified: PK `TENANT#{TenantId}#MEDIA_ITEM#{MediaItemId}`, SK constant `STATE`. Spec fixed (was `—`/`—`); CDK doc-comment corrected.

**Findings (Registration):**
1. `media-registration` (Detail) confirmed using the same inverted discriminator/groupKey convention as `media-asset` (AssetManagement module): literal constant `"DETAIL"` as SK, real `RegistrationId` folded into PK via groupKey. This is now a recognized pattern across at least two modules' Detail tables (vs. Catalog's Detail tables, which put category alone in PK and bare entity id in SK) — worth keeping in mind as a real, intentional, recurring convention rather than a one-off.
2. `system-architecture.md`'s GSI section for `media-registrations` was wrong, not just stale — it named a `StatusIndex` (Status + SubmittedAt) that doesn't exist anywhere in the C# code or CDK. The two real GSIs (`RegistrationByMediaItemIndex`, `RegistrationByOwnerIndex`) were completely absent from that section despite being implemented and CDK-deployed. Replaced the fictional entry with the two real ones.
3. CDK structurally correct for both base tables (PK+SK via `simple()`) and both GSIs (GSI1PK/GSI1SK, GSI2PK/GSI2SK, both String) — no CDK schema changes needed, only the write-index doc comment was stale (now fixed).
4. `system-spec.md` (out of this plan's normal scope) is more accurate here than `system-architecture.md` was — its GSI table already had both real GSIs correct, and its `media-registration-item-ref` row was already exactly correct. But its `media-registration` (Detail) row PK is missing the `REGISTRATION#` category segment (shows `TENANT#{TenantId}#{RegistrationId}`, should be `TENANT#{TenantId}#REGISTRATION#{RegistrationId}`), and its `media-registrations` (Summary) row SK is shown as bare `{RegistrationId}` when the real SK is `SUMMARY#{RegistrationId}`. Flagging only, not fixed (same out-of-scope reasoning as the AssetManagement pass).
5. `RegistrationSummarySchema.cs`'s own XML doc comment mislabels itself as the "registration detail read model projection schema" when it's actually the Summary schema — app-code comment issue, not touched (app code read-only per this plan).

### Metadata

Base table schemas:
- [x] `media-record-type` (Detail, category `RECORD_TYPE`) — verified: PK `TENANT#{TenantId}#RECORD_TYPE#{RecordTypeId}`, SK constant `DETAIL`. Same inverted Detail convention as `media-asset`/`media-registration`. Spec fixed (was `TENANT#{TenantId}#{RecordTypeId}` / `—`).
- [x] `media-record-types` (Summary, `RecordTypeSummarySchema`) — verified: PK `TENANT#{TenantId}#RECORD_TYPES`, SK `SUMMARY#{RecordTypeId}`. Spec fixed.
- [x] `media-record-type-versions` (registered as `RecordTypeVersionSummaryReadModel`, category `RECORD_TYPE_VERSIONS`) — verified: PK `TENANT#{TenantId}#RECORD_TYPE_VERSIONS#{RecordTypeId}`, SK bare `{Version:D10}` (no custom schema class). Spec fixed (was `TENANT#{TenantId}#{RecordTypeId}` / `Version`).
- [x] `RecordTypeVersionDetailReadModel` / `RecordTypeVersionDetailSchema` — **investigated, not a copy-paste typo, but also not a clean intentional design — a half-migrated state.** Registered against `media-record-types` (PK `TENANT#{TenantId}#RECORD_TYPES#{Version:D10}`, SK `VERSION#{RecordTypeId}` — groupKey present, so it lands on its own per-version partition and does **not** collide with Summary rows on that table). Git history (`eba2790`, 2026-05-07): this table choice was made deliberately when `RecordTypeVersionDetailReadModel` was introduced to fix `GetRecordTypeVersionQuery` returning the wrong shape — same commit closed out a backlog note "review RecordTypeVersion summary and detail." But it matches neither established precedent: not co-located with its own Summary sibling on `media-record-type-versions` (the `media-item-versions` pattern), nor split into a dedicated table (the `media-profile-version` fix). The one spec doc that describes the original "everything shares `media-record-types`" design (`spec/contexts/Metadata/aggregates/RecordType/recordtype.read-model.md`) is itself stale — references a `RecordTypeVersionSnapshotReadModel` type removed in that same commit, predates the `media-record-type-versions` table split, and was never updated. **Escalating per the plan's instruction — this needs a Chase/Karen decision, not a guess:** (a) leave as-is and treat this finding + the CDK/spec notes as the durable record of intent, (b) move `RecordTypeVersionDetailReadModel` onto `media-record-type-versions` to mirror `media-item-versions`, or (c) give it a dedicated `media-record-type-version` table to mirror the `media-profile-version` fix. **No app-code change made** — out of this plan's scope regardless of which option is chosen. Documented the anomaly and all three options in `system-architecture.md` and added a CDK doc-comment cross-reference in `read-models.construct.ts`.

GSI schemas:
- [x] `RecordTypeByNameIndexSchema` — `IndexName` "RecordTypeByNameIndex", `GSI1PK`/`GSI1SK`. `GSI1PK` = `TENANT#{TenantId}#RECORD_TYPES`, `GSI1SK` = `{Name.ToLowerInvariant()}#{RecordTypeId}`. Matches CDK exactly. Spec's previous `OwnerIndex` (OwnerId + CreatedAt, with a literal `"owner_system"` value) does not exist in code or CDK — fictional, like Registration's `StatusIndex` — removed and replaced with the real GSI.
- [x] `RecordTypeVersionByVersionIndexSchema` — literal `IndexName` is **"RecordTypeVersionsByRecordTypeIndex"**, matching CDK exactly (the C# class name "ByVersion" vs the IndexName string "ByRecordTypeIndex" is a cosmetic naming inconsistency only — same pattern as `MediaProfileByVersionIndexSchema` in Catalog). `GSI1PK` = `TENANT#{TenantId}#RECORD_TYPE#{RecordTypeId}#VERSIONS`, `GSI1SK` = `VERSION#{Version:D10}`. Added to spec (was entirely missing).

**Findings (Metadata):**
1. **Headline finding — the `RecordTypeVersionDetailReadModel` anomaly is real but not a hard bug**: no row-level collision occurs (groupKey-based PK partitioning keeps Version-Detail rows separate from Summary rows on `media-record-types`), but it's a half-migrated design that doesn't match either of the two established Detail/Summary patterns elsewhere in the codebase (`media-item-versions` shared-table or `media-profile-version` dedicated-table). Escalated to Chase/Karen for a decision — see checklist entry above for the three options. Not silently fixed, per the plan's explicit instruction for this item.
2. Second fictional GSI found in `system-architecture.md`, same shape as Registration's `StatusIndex`: a documented `OwnerIndex` (OwnerId + CreatedAt, including a literal `"owner_system"` sentinel value) for `media-record-types` that doesn't exist in code or CDK at all. Removed and replaced with the real `RecordTypeByNameIndex`.
3. Both base-table PK/SK patterns (`media-record-type`, `media-record-types`, `media-record-type-versions`) were stale in the same uniform-and-wrong way as every other module before its audit — all three now corrected in spec.
4. CDK structurally correct for all three tables and both GSIs (PK/SK String via `simple()`, GSI1PK/GSI1SK String) — no CDK schema changes needed. Added a doc-comment cross-reference on `recordTypes`/`recordTypeVersions` in `read-models.construct.ts` pointing at the anomaly so it isn't lost to a future reader of the CDK alone.
5. `system-spec.md` and `system-architecture.md` both lacked any DynamoDB table/GSI inventory section for RecordType prior to this pass (zero matches on search) — only the per-aggregate doc `spec/contexts/Metadata/aggregates/RecordType/recordtype.read-model.md` had anything, and that doc is stale (references the removed `RecordTypeVersionSnapshotReadModel` type, predates the `media-record-type-versions` split). Flagging for awareness; not in scope to rewrite that doc as part of this plan.

### ChangeRequests

Base table schemas:
- [x] `media-change-request` (Detail, category `CHANGE_REQUEST`) — verified: registered via 2-arg `AddProjectionSchema<ChangeRequestDetailReadModel>("media-change-request", "CHANGE_REQUEST")`, no custom schema class. `ChangeRequestDetailReadModel.CreateProjectionKey` constructs `ProjectionKey(tenantId, "DETAIL", changeRequestId)` (discriminator, then groupKey) → PK `TENANT#{TenantId}#CHANGE_REQUEST#{ChangeRequestId}`, SK constant `DETAIL`. Same inverted Detail convention as `media-asset`/`media-registration`/`media-record-type`. Spec fixed (was `TENANT#{TenantId}#{ChangeRequestId}` / `—`).
- [x] `media-change-request-comments` (`ChangeRequestCommentSchema`) — verified: PK `TENANT#{TenantId}#CHANGE_REQUEST#{ChangeRequestId}` (groupKey form), SK `COMMENT#{CommentId}`. CDK attribute name already fixed; spec value pattern now corrected (was bare `CommentId` SK with no group-keyed PK).
- [x] `media-change-requests` (Summary, `ChangeRequestSummarySchema`) — verified: category `CHANGE_REQUESTS`, `CreateProjectionKey` passes no groupKey → PK `TENANT#{TenantId}#CHANGE_REQUESTS`, SK `SUMMARY#{ChangeRequestId}`. Matches the established Summary pattern across every other module. Spec fixed (was `TENANT#{TenantId}#{ChangeRequestId}` / `—`).

GSI schemas:
- [x] `ChangeRequestByMediaItemIndexSchema` — `IndexName` "ChangeRequestByMediaItemIndex", `GSI1PK` only (sparse, no `SortKeySchema` override). `GSI1PK` = `TENANT#{TenantId}#ITEM#{MediaItemId}#CHANGE_REQUESTS`. Matches CDK exactly. Added to spec.
- [x] `ChangeRequestByOwnerIndexSchema` — `IndexName` "ChangeRequestByOwnerIndex", `GSI2PK` only (sparse, no sort key). `GSI2PK` = `TENANT#{TenantId}#OWNER#{OwnerId}#CHANGE_REQUESTS`. Matches CDK exactly. Added to spec.

Write-side index tables: none — ChangeRequests has no entry in `write-indexes.construct.ts` (confirmed; only `read-models.construct.ts` declares its 3 tables). Nothing to verify here.

**Findings (ChangeRequests):**
1. `media-change-request` (Detail) confirmed using the same inverted discriminator/groupKey convention now seen in AssetManagement, Registration, and Metadata: literal constant `"DETAIL"` as SK, real `ChangeRequestId` folded into PK via groupKey. Fourth module to follow this pattern — solidifies it as the standard Detail-table convention rather than a per-module quirk.
2. `media-change-request-comments` PK/SK shape matches the plan's pre-stated expectation exactly (groupKey-form PK on `ChangeRequestId`, `COMMENT#{CommentId}` SK) — confirmed via `ChangeRequestCommentReadModel.CreateProjectionKey` and `ChangeRequestCommentSchema.BuildSortKey`. No surprises.
3. Both GSIs (`ChangeRequestByMediaItemIndex`, `ChangeRequestByOwnerIndex`) are partition-key-only (sparse, no `SortKeySchema` override) — by design per `IProjectionIndexSchemaWriter.SortKeySchema` defaulting to `null`, not a bug. Same "no sort key" shape as Catalog's `MediaItemByFolderIndex` and AssetManagement's `AssetByMediaItemIndex`. Unlike Registration's two GSIs (which both carry a `{InitiatedAt:O}#{Id}` sort key for reverse-chrono ordering), ChangeRequests' GSIs return query results in DynamoDB's default (unordered-within-partition) order — worth flagging if a future requirement needs chronological list-by-media-item or list-by-owner ordering, since that would require adding a sort key, which is a breaking schema change (table replace, not in-place).
4. CDK structurally correct for all 3 base tables (PK+SK String via `simple()`) and both GSIs (GSI1PK/GSI2PK String, no sort key on either) — no CDK schema changes needed for this module. CDK's own doc-comments here are already accurate (unlike the stale comments flagged in Catalog/AssetManagement/Registration's write-index tables) — no cleanup needed.
5. `ChangeRequestCommentReadModel.cs`'s own XML doc comment is wrong, not just stale: it claims PK `TENANT#{TenantId}#PROJECTION#ReviewCommentReadModel` / SK `{ChangeRequestId}#{CommentId}`, which matches neither the schema class's actual `BuildSortKey` override nor the `DefaultProjectionSchema` base behavior. Flagging only — app code comment, not touched (read-only source of truth per this plan).
6. No write-side reference-index table exists for ChangeRequests (none registered in `write-indexes.construct.ts`) — nothing to audit in that category for this module, unlike every other module audited so far.

### Processing

Base table schemas:
- [x] `media-processing-job` (Detail, category `PROCESSING_JOB`) — verified: PK `TENANT#{TenantId}#PROCESSING_JOB#{JobId}`, SK constant `DETAIL`. Same inverted Detail convention as `media-asset`/`media-registration`/`media-record-type`/`media-change-request`. Spec rows added (was missing entirely).
- [x] `media-processing-jobs` (Summary, `ProcessingJobSummarySchema`) — verified: PK `TENANT#{TenantId}#PROCESSING_JOBS`, SK `SUMMARY#{JobId}`. Matches established Summary pattern. Spec rows added.

GSI schemas:
- [x] `AssetByProcessingJobIndexSchema` — `IndexName` "AssetByProcessingJobIndex", lives on `media-processing-jobs`. `GSI1PK` = `TENANT#{TenantId}#ASSET#{AssetId}#JOBS`, `GSI1SK` = `{UpdatedAt:O}` (no trailing ID). Matches CDK exactly. Added to spec, with a collision-risk note (see findings).

Write-side index tables:
- [x] `AssetProcessingJobIndex` (`media-processing-asset-index`) — verified: PK `TENANT#{TenantId}#ASSET`, SK bare `{AssetId}` — no groupKey, every asset in a tenant shares one partition. CDK doc-comment corrected (was claiming a different PK shape with no SK); spec row corrected.

**Findings (Processing):**
1. `media-processing-job` (Detail) confirmed using the same inverted discriminator/groupKey convention now seen in AssetManagement, Registration, Metadata, and ChangeRequests: literal constant `"DETAIL"` as SK, real `JobId` folded into PK via groupKey. Fifth module to follow this pattern.
2. **`AssetProcessingJobIndex` write-index uses a genuinely different shape from every other write-index audited so far.** All prior write-indexes (`AssetToMediaItemIndex`, `AssetStateReference`, `MediaItemCapabilityReference`, etc.) fold the real entity ID into the PK via groupKey and use a literal constant as SK. This one does the opposite: no groupKey is supplied, so every asset in a tenant shares one partition (`TENANT#{TenantId}#ASSET`), and `AssetId` itself is the bare SK. Functionally fine (still unique per asset, just partition-then-sort instead of partition-per-asset), but breaks the pattern consistency the previous four modules established.
3. `AssetByProcessingJobIndexSchema`'s GSI1SK value (`{UpdatedAt:O}` alone, no trailing `{JobId}`) is a latent collision risk: two `ProcessingJobSummaryReadModel` rows for the same asset updated at the exact same timestamp would overwrite each other's GSI projection slot. App-code key-shape choice, not a CDK/spec error — flagged for awareness, not fixed. Compare Registration's two GSIs, which both append `#{RegistrationId}` for exactly this reason.
4. CDK structurally correct for both base tables (via `simple()`) and the one GSI (GSI1PK/GSI1SK String) — no functional CDK schema changes needed. Only the `processingAssetIndex` doc-comment was stale (now fixed).
5. `system-spec.md` (out of this plan's normal scope, flagged only) has the same staleness pattern seen elsewhere: `media-processing-job` row missing the `PROCESSING_JOB#` category segment, `media-processing-jobs` row showing SK as bare `{JobId}` instead of `SUMMARY#{JobId}`. Not fixed, consistent with precedent for other modules.
6. `ProcessingJobDetailReadModel.cs`'s own XML doc comment is wrong, not just stale: claims PK `TENANT#{TenantId}`, SK `JOB#{JobId}` on table `media-processing-jobs` (plural) — matches neither the real table (`media-processing-job`, singular) nor the actual schema behavior. App-code comment issue, not touched (read-only source of truth).
7. No `spec/contexts/Processing/` directory exists in AIS-OS (confirmed via search) — nothing to cross-check there, unlike Metadata's per-aggregate doc.

No app-code bugs found requiring Chase/Karen escalation in this module — items 2 and 3 above are pattern/risk awareness notes, not collisions or breakages like the `RecordTypeVersionDetailReadModel` case.

### DocumentSigning

Base table schemas:
- [ ] `media-signing-session` (Detail) — registered via 1-arg `AddProjectionSchema<T>(tableName)`, no category. Confirm what schema identifier `DefaultProjectionSchema<T>` falls back to (likely `typeof(T).FullName`) before documenting PK pattern.
- [ ] `media-signing-sessions` (Summary) — same 1-arg overload question.

GSI schemas: none registered yet — `SigningSessionSummaryProjector` is a known deferred gap (see project CLAUDE.md / brief.md). Don't invent a GSI for this; confirm still deferred each pass.

**Findings (DocumentSigning):** —

---

## Final pass (after all modules above are checked off)

- [ ] Rewrite the "Query-facing read models" table in `spec/architecture/system-architecture.md` (~lines 428-460) with verified PK/SK value patterns per row, replacing the current uniform-and-wrong `TENANT#{TenantId}#{EntityId}` / "—" pattern.
- [ ] Add PK/SK columns to the write-side reference index table in the spec (currently Purpose-only, no key-schema claim at all).
- [ ] Add a GSI table to the spec (or correct the existing one at ~lines 488-495) with verified index names + attribute names per the `IProjectionIndexSchema` audit above.
- [ ] Cross-check CDK's `addGlobalSecondaryIndex` calls against the same verified GSI data — fix any index name / attribute name / key-type mismatches found.
- [ ] Resolve the `RecordTypeVersionDetailReadModel` table-name anomaly (escalate to app-code fix if confirmed a bug, otherwise document the intentional sharing in spec).
- [ ] Resolve `media-item-versions` / `media-profile-versions` SK-collision question.
- [ ] Decide fate of the 3 orphaned write-index tables (`catalogFolderStatusIndex`, `catalogFolderActiveItemCountIndex`, `referenceModels`) — delete from CDK or confirm dead and document.
- [ ] Final full read-through of `system-architecture.md` DynamoDB section for internal consistency once all rows are corrected.
- [ ] Deploy: full stack replace (v1, no data) once CDK changes are merged.
