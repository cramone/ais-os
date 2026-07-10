# API Consistency Remediation Plan

_Derived from `api-rest-review.md` (Z:\claudia\magiq\projects\magiq-media\reviews\), Principal .NET / REST Architect pass, 2026-07-08._
_Owner: Chase Ramone. Status: Stages 0–5 substantially complete (2026-07-08); Stage 5 acceptance blocked on a spec-tree file-truncation incident — see Stage 5's incident note. `api-conventions.md` is fixed and verified; 11 other files are confirmed truncated and deferred pending Chase's go-ahead. Three earlier items flagged for a decision/follow-up, not auto-resolved — see Stage 1's note on the three asset-upload `202` endpoints, Stage 2's note on the `bulk-paths` envelope-shape mismatch, and Stage 3's note on the stale `InitiateRegistration` route/doc param mismatch._

## How to use this document

Each stage is a self-contained checklist item you can pick up in any session. Check items off as `- [x]` as you land them (in the same PR as the spec/code change they describe, per the repo's docs-co-location convention). Stages are ordered by the review's own recommended priority — cheapest/highest-leverage first — but stages 0–2 have no cross-dependencies on each other and can be worked in parallel if useful. Stage 4 (versioning gate) is time-sensitive: check it before the MediaItem metadata endpoints ship, not after.

Every item below cites the exact review section it came from, in case you need the full reasoning — see `api-rest-review.md`.

---

## Stage 0 — Zero-decision doc fixes

No policy call required; these are self-contained corrections. Good first-session warm-up or filler between bigger stages.

> Note: the route paths cited below already use the **flat** form confirmed in Stage 5 (no `/catalog`, `/metadata`, or `signing` prefix segment) — write them that way directly rather than fixing them to the interim `/catalog/`-prefixed form first and re-fixing later. If Stage 5's route migration hasn't landed yet when you pick this up, these two items will look slightly ahead of the rest of the file; that's expected.

- [x] Fix `mediaprofile.api.md` traceability table: it lists `POST /v1/metadata/record-types/{id}` and `PUT /v1/metadata/record-types/{id}/version`, contradicting the correct route table two sections above in the same file. Fix to the confirmed flat path: `POST /v1/profiles/{profileId}/record-types/{recordTypeId}`, `PUT .../record-types/{recordTypeId}/version`. *(URL Naming, Medium)*
- [x] Fix `bulk-operations.md` worked example: `POST /media-collections/bulk` → `POST /v1/collections/bulk` (flat path). *(URL Naming, Low)*
- [x] `PUT /v1/catalog/items/{itemId}/metadata` request body: `recordTypeId`/`recordTypeVersion` fields claim server-side validation in their doc comment, but `SetMetadataBatchEndpoint.HandleAsync` never reads them (self-flagged as dead in the spec). Either wire up the validation or remove the fields and the misleading comment. *(Request Model, Medium)* — **Resolved: removed.** Dropped `RecordTypeId`/`RecordTypeVersion` from `SetMetadataBatchRequest` (code) and the request example/table in `mediaitem.api.md` (spec), with a dated note explaining the removal. No existing caller depended on them (dead on the wire).
- [x] `GET /v1/change-requests/{id}/comments` (list item, `createdAt`) vs. `GET /v1/change-requests/{id}/comments/{commentId}` (single item, `addedAt`) — same underlying timestamp, two field names. Standardize on `createdAt`. *(Response Model, Medium)* — **Resolved:** renamed `AddedAt` → `CreatedAt` on `ChangeRequestCommentReadModel`, `ChangeRequestCommentSummaryModel`, and `GetChangeRequestCommentResponse` (both list and single-comment endpoints now emit `createdAt`); domain event `ReviewCommentAdded.AddedAt` left as-is (internal domain naming, not the API contract). Spec single-comment example updated to match.
- [x] JSON key hygiene pass — global find for `media-` prefixes leaking into JSON code-fence keys and doubled prose artifacts:
  - [x] `POST /v1/catalog/items/bulk` request body: `"media-items"` → `"items"` (every other bulk-create endpoint uses `"items"`) — code (`BulkCreateMediaItemsRequest.Items`) already correct; spec example was stale, now fixed.
  - [x] `GET /v1/catalog/items/{itemId}` response: `"media-assets"` → `"assets"` (matches Asset aggregate's own list response key)
  - [x] Sweep `mediaitem.api.md` prose for doubled artifacts ("media media-item," "media media-items") and normalize — also found and fixed the same doubled-prefix artifact in `service-boundaries.md`, `bounded-context.md`, and `Catalog/context-overview.md` (outside the originally-named file, but within the acceptance grep's scope).
- [x] **Acceptance:** grep the spec tree for `"media-items"`, `"media-assets"`, `media media-` and confirm zero matches outside intentional prose use of the hyphenated compound term (e.g. "a media-collection with id..."). — **Confirmed 2026-07-08: zero matches.**

---

## Stage 1 — Status code standardization

Resolves Critical Issue C3 plus the largest-blast-radius High finding. No data-shape changes — pure status-code corrections, touches the most endpoints for the least risk. Do this before any code is written against these contracts.

**Policy restated/confirmed in `api-conventions.md §Async Operations` (2026-07-08):** `202 Accepted` is reserved exclusively for the two documented saga-triggering endpoints (`POST .../items/{id}/submit`, `POST .../items/{id}/signing-sessions`) or any future endpoint formally added to that same table. Every other "succeeded, nothing to return" mutation is `204 No Content` — never `200 OK` with an empty body.

- [x] `POST /v1/assets/{id}/archive`: `202` → `204` *(Critical C3)*
- [x] `POST /v1/catalog/profiles/{id}/deprecate`: `202` → `204` *(Critical C3)*
- [x] `POST /v1/metadata/record-types/{id}/deprecate`: `202` → `204` *(Critical C3)*
- [x] `POST /v1/metadata/record-types/{recordTypeId}/capabilities`: `202` → `204` (same root cause as C3, draft-mutation flavor) *(HTTP Status Code, Low)* — code was already `204`; only the spec doc was stale.
- [x] `PATCH /v1/catalog/items/{itemId}/metadata/{fieldName}`: `200 OK` no body → `204` *(HTTP Status Code, High)* — code was already `204`; only the spec doc was stale.
- [x] `PATCH /v1/metadata/record-types/{recordTypeId}/fields/{fieldName}`: `200 OK` no body → `204` *(HTTP Status Code, High)* — code declared `Produces(202)` but actually sent `204`; fixed the declaration to match. Also fixed the sibling `PUT .../fields/{fieldName}` (replace) spec doc, found stale during the same sweep (code was already `204`).
- [x] `POST /v1/metadata/record-types/{recordTypeId}/fields`: `200 OK` no body → `204` *(HTTP Status Code, High)* — code was already `204`; only the spec doc was stale.
- [x] `POST /v1/metadata/record-types/{recordTypeId}/draft/fields/{fieldName}/deprecate`: `200 OK` no body → `204` *(HTTP Status Code, High)* — genuine fix: code returned `200` with a body (`DeprecateFieldInRecordTypeResponse`); now `204`, response DTO marked `[Obsolete]` (file undeletable in this environment — safe to delete via IDE).
- [x] All `DocumentSigningSession` system/adapter endpoints: `200 OK` no body → `204` *(HTTP Status Code, High)* — spec-only fix (endpoints not yet implemented in code). Also fixed the neighboring `POST .../cancel` endpoint's `200 OK` no body → `204`, found during the same sweep (not code-backed either).
  - [x] `/envelope/created`
  - [x] `/envelope/sent`
  - [x] `/signers/{email}/completed`
  - [x] `/completed`
  - [x] `/signed-asset`
  - [x] `/envelope/voided`
  - [x] `/expire`
- [x] `POST /v1/registrations/{id}/amendments/{amendmentId}/approve`: `200 OK` no body → `204` *(HTTP Status Code, High)* — code was already `204`; only the spec doc was stale.
- [x] `POST /v1/change-requests/{changeRequestId}/comments`: `201 Created` empty body → return `{ "id": "<commentId>" }` at minimum *(HTTP Status Code, Medium)* — code already returned `{ id, createdAt }`; the spec doc was the stale side.
- [x] **Decision:** option 2 chosen — body-only identification, no `Location` header on `201` responses. Documented in `api-conventions.md` new `§Response Conventions` section and in `adrs/api-http-conventions.md` (new `§Resource Creation — Body-Only Identification` section, added to the existing consolidated ADR rather than a new numbered one).
  - [x] Audited all `201` endpoints for the gap the decision implied, since the ADR draft's first pass incorrectly assumed none existed: FastEndpoints' `SendCreatedAtAsync` helper — used by `AddComment`, `RequestAmendment`, `InitiateRegistration`, `CreateRecordType`, `CreateMediaProfile`, `CreateFolder`, `CreateCollection` — sets a `Location` header by default. All seven were switched to the plain `SendAsync(response, 201, ct)` pattern already used by `CreateMediaItem`. ADR corrected to reflect the retrofit rather than claim none was needed.
- [x] **Acceptance:** grepped all `*.api.md` files for `200 OK` and `202 Accepted`. Zero remaining `200 OK` responses with no body. All remaining `202 Accepted` responses are either the two-entry saga table, the pre-existing bulk partial-success envelope (`bulk-operations.md` convention, not the saga pattern, not in scope here), or async bulk-import job initiation (also a pre-existing, separately documented pattern) — **except** three endpoints not part of this checklist and left unchanged pending a decision: `POST /v1/assets/{assetId}/uploads/confirm`, `POST /v1/assets/{assetId}/multipart-upload/complete`, `POST /v1/assets/{assetId}/multipart-upload/abort` all document `202 Accepted` with no body and aren't in the two-entry saga table. They may be a legitimate case (S3-triggered async downstream processing) or a fourth gap the original review missed — flagged for Chase to decide rather than silently changed, since these are live integration touchpoints (S3 event notifications / Ingest API) not reviewed here.

---

## Stage 2 — Identifier naming & list-envelope standardization

Resolves Critical Issues C1/C2 and the residual High-severity half of the old pagination critical issue. Has real data-shape consequences — land before any client SDK or Postman collection is generated from the spec.

**Decisions confirmed 2026-07-08 (Chase):** both per the review's recommendation.

- [x] **Decision:** bulk-array identifier convention is `id` — `docs/adrs/api-http-conventions.md §Response Identifier Naming` Rule 4 updated to read "same as Rule 1," with a dated note explaining the reversal. *(Critical C2)*
- [x] `GET /v1/catalog/import-jobs/{jobId}` (both `BulkFolderImportJob` and `BulkMediaImportJob`) and their list variants: `"jobId"` → `"id"` *(Critical C1)* — spec-only (no code exists yet for either aggregate; pre-implementation, matches the deferred-work note in `CLAUDE.md`).
  - [x] Confirmed `jobId` **is** carried in the SQS/SNS integration event payloads (`BulkFolderImportJobCreatedMessage`/`BulkMediaImportJobCreatedMessage` et al., sourced from the `JobId` field on the corresponding domain events). This is a legitimate Rule 5 exemption for the event contract only — stated explicitly in both `bulkfolderimportjob.api.md` and `bulkmediaimportjob.api.md` next to the renamed `id` field so the two conventions aren't read as drift.
- [x] `POST /v1/catalog/items/bulk/metadata` `succeeded[]`/`failed[]`: `"itemId"` → `"id"` *(Response Model, High)* — fixed in spec and in code (`BulkSetMetadataSucceededModel`, `BulkSetMetadataFailedModel`).
- [x] Confirm bulk `succeeded[]` arrays already using `"id"` need no change: Collection, Folder, MediaItem (`/bulk`), Asset (`/uploads/bulk`, `/uploads/bulk-confirm`) — **correction: this premise was wrong.** The *spec* already used `id` for all of these (matching the review's read), but the *code* did not — `BulkCreateCollectionsSucceededModel.CollectionId`, `BulkCreateFoldersSucceededModel.FolderId`, `BulkCreateFolderPathSucceededModel`/`SkippedModel.FolderId`, `BulkCreateMediaItemsSucceededModel.MediaItemId`, `BulkInitiateAssetUploadSucceededModel.AssetId`, and `BulkConfirmAssetUploadSucceededModel.AssetId` all still shipped type-qualified names. All six renamed to `Id` to match the spec and the now-confirmed rule. No test coupling found; renames are source-compatible (positional record construction).
  - Also found and flagged, **not fixed** (out of scope — a response-shape gap, not a naming one): `POST /v1/catalog/collections/{collectionId}/folders/bulk-paths` — the spec documents a `{ nodes: [...], failed: [...] }` envelope, but the actual code (`BulkCreateFoldersByPathEndpointBase`) returns the standard `{ Succeeded, Failed, Skipped }` triple instead. Both sides already agree on `id` for the identifier itself, so no naming fix was needed there, but the envelope shapes disagree entirely — worth a follow-up item.
- [x] **Decision:** list-response envelope key is generic `items` for every list endpoint *(matches what `api-conventions.md` already documented)*.
  - [x] `api-conventions.md §Pagination` — no change needed, already documents `items`.
  - [x] `GET /v1/catalog/collections` (both the owner-scoped and `/public` variants): `"collections"` → `"items"` — spec-only; code (`ListCollectionsResponse`, `ListPublicCollectionsResponse`) was already compliant.
  - [x] `GET /v1/catalog/folders`: `"folders"` → `"items"` — spec-only; code (`ListFoldersResponse`) was already compliant.
  - [x] `GET /v1/change-requests`: `"changeRequests"` → `"items"` — spec-only; code (`ListChangeRequestsResponse`) was already compliant.
  - [x] `GET /v1/assets`: `"assets"` → `"items"` — spec-only; code (`ListAssetsResponse`) was already compliant.
  - [x] `GET /v1/signing/sessions`: `"sessions"` → `"items"` — spec-only (no code yet).
  - [x] `GET /v1/catalog/import-jobs`: `"jobs"` → `"items"` — spec-only (no code yet).
  - [x] Also found and fixed during the acceptance sweep (not originally named, but caught by "exactly one envelope shape appears everywhere"): `GET /v1/change-requests/{changeRequestId}/comments` used `"comments"`, not `"items"` — fixed in spec; code (`ListChangeRequestCommentsResponse`) already used `Items` but was **missing `PageSize` entirely** — added and wired through from `PagedResult<T>.PageSize`. `GET /v1/catalog/items/{itemId}/versions` used `"versions"`, not `"items"` — fixed in spec; code (`ListMediaItemVersionsResponse`) was already compliant.
- [x] Add `pageSize` to every list response DTO that's currently missing it *(Response Model, Low / Pagination, High)* — audited every `*.api.md` list-response example platform-wide (not just the ~10 originally estimated). Missing in spec for: both `BulkFolderImportJob`/`BulkMediaImportJob` list endpoints (×4), `GET /v1/catalog/collections` (×2), `GET /v1/catalog/folders?collectionId=`, `GET /v1/catalog/folders/{folderId}/children`, `GET /v1/change-requests`, `GET /v1/change-requests/{id}/comments`, `GET /v1/assets`, `GET /v1/signing/sessions`, `GET /v1/catalog/folders/{folderId}/items`, `GET /v1/catalog/items/search`, `GET /v1/catalog/items/{itemId}/versions`. All fixed in spec. Only one had a real code gap (`ListChangeRequestCommentsResponse`, above) — everywhere else the code DTO already carried `PageSize`, only the doc example was stale.
- [x] **Acceptance:** grepped all `*.api.md` list-response JSON examples — every `nextPageToken`/`nextSearchAfter` occurrence now has an accompanying `pageSize`, and exactly one envelope shape (`items`/cursor/`pageSize`) appears everywhere (nested nested arrays like a Registration's own `documents`/`amendments` sub-lists, or a bulk-import job-item row's `folderId`, are correctly out of scope — those are foreign references or embedded sub-collections within a single-resource detail view, not paginated list endpoints). Every bulk `succeeded[]`/`failed[]` array in the spec now uses `id`.

---

## Stage 3 — Query parameter & filtering standardization

Lower urgency than Stages 1–2 but should land before the filtering surface grows further.

- [x] `GET /v1/assets?itemId=` → `?mediaItemId=` *(Query Parameter, High)* — fixed route table, auth table, endpoint header, query-param table, and traceability table in `asset.api.md`. Code (`ListAssetsRequest`, `ListAssetsEndpoint`, `ListAssetsByMediaItemQuery`) already used `MediaItemId` throughout — spec-only fix.
- [x] `GET /v1/change-requests?itemId=` → `?mediaItemId=` *(Query Parameter, High)* — fixed route table and endpoint header in `mediachangerequest.api.md`; also added a missing query-param table, `404`-vs-empty-list note, and traceability row (the endpoint's real behavior — optional `mediaItemId` with owner-scoped fallback when omitted — wasn't documented at all before). Code already used `MediaItemId` correctly, including the owner-fallback branch in `ListChangeRequestsEndpoint`. Spec-only fix.
- [x] `GET /v1/signing/sessions?itemId=` → `?mediaItemId=` *(Query Parameter, High)* — fixed route table and endpoint header in `documentsigningsession.api.md`; added the same query-param table, `404`-vs-empty-list note, and traceability row (previously absent). Spec-only — no `DocumentSigning` read-side code exists yet, consistent with the deferred-work note in `CLAUDE.md`.
- [x] Confirm `GET /v1/registrations?mediaItemId=` needs no change (already correct) — confirmed in both spec and code. **Found and flagged, not fixed:** while checking Registration's neighboring `POST /v1/catalog/items/{itemId}/registrations`, the endpoint's XML doc comment claims the route param is `{mediaItemId}` and `summary.Params["mediaItemId"]` documents an OpenAPI param that doesn't exist — the actual route token is `{itemId}` (`InitiateRegistrationEndpoint.cs`). FastEndpoints binds the request DTO's `ItemId` property to the route by name-match, so functionally requests still work, but the Swagger/OpenAPI param description likely doesn't attach to the real parameter. This is a route-path-param naming question (Stage 5 territory — `{itemId}` path segments are explicitly in that stage's scope), not a query-filter naming question (this stage's scope), so left unchanged here — flagged for Stage 5 or a standalone fix.
- [x] Add a "Filtering" section to `api-conventions.md`, modeled on the existing Sorting section — one row per canonical filter relationship: `ownerId`, `mediaItemId` (never `itemId`), `collectionId`, `parentFolderId`, `status`, `unassigned` *(Query Parameter, Medium / Filtering, High)* — added, sourced from a full survey of every `List*Request`/`Search*Request` DTO across all six modules. Also fixed a stale cross-reference in the neighboring Sorting section (`GET /v1/catalog/items/unassigned` no longer exists as a route — it's `GET /v1/catalog/items?unassigned=true`, per `mediaitem.api.md`'s own already-correct documentation of that removal). **Also found and fixed a genuine code bug surfaced by the survey:** `GET /v1/catalog/folders`'s parent-folder filter is documented in `folder.api.md` (and used consistently in its JSON examples) as `parentFolderId`, but the actual request DTO (`ListFoldersRequest`) bound it as the bare `FolderId` — ambiguous against the folder's own `id` and inconsistent with Rule 2 (foreign-reference filters must be qualified). Renamed `ListFoldersRequest.FolderId` → `ParentFolderId` and the corresponding `summary.Params["folderId"]` → `summary.Params["parentFolderId"]` in `ListFoldersEndpoint.cs` to match the spec. No test coupling found (grepped `tests/` — no test referenced this property).
- [x] Document the import-job `pageSize` default/cap exceptions (100/500 on `.../items`, 50/200 on `.../upload-urls`) explicitly in `api-conventions.md` rather than leaving them as silent per-endpoint overrides *(Query Parameter, Low / Pagination, Low)* — added an exceptions table directly under the standard Pagination query-param table, sourced from the actual documented values in both `bulkfolderimportjob.api.md` and `bulkmediaimportjob.api.md`.
- [x] Confirm and document "empty list, not 404, when filter ID doesn't exist" behavior on `GET /v1/assets?mediaItemId=` and `GET /v1/change-requests?mediaItemId=` (Registration already documents this correctly — extend the same explicit statement to the other two) *(Filtering, Low positive — extend the pattern)* — extended to Asset, ChangeRequests, and DocumentSigning (the latter two didn't exist as documented endpoints in enough detail before this stage to carry the note).
- [x] **Acceptance:** grepped `itemId=` across every `*.api.md` file — zero matches remain anywhere in the spec tree. Remaining `itemId` occurrences repo-wide are exclusively `{itemId}` route **path** segments (own-resource-ID convention, Stage 5 scope) or unrelated diagram notation in `security-scenarios.md` — none are query-string filters.

---

## Stage 4 — Versioning gate (time-sensitive)

Only one item, but it has a deadline: check it before `PUT /v1/catalog/items/{itemId}/metadata` and `POST /v1/catalog/items/bulk/metadata` ship, not after.

- [x] Confirm the metadata shape change (map → array, `docs/adrs/catalog-domain-invariants.md §Metadata Collision Prevention and General Fields`) still ships before any client integrates against the current map shape. If that premise no longer holds by ship time, route the change through `/v2` per `api-conventions.md §API Versioning` instead of shipping in place with no migration path. *(Request Model, High / Versioning, Medium)* — **Resolved: premise holds, no `/v2` needed.** The array shape (`SetMetadataBatchRequest.Fields`, `SetMetadataFieldRequest.Origin`) already shipped to `develop`/`dev` via commit `e4c8af88` (2026-06-25, ~2 weeks before this check), and both spec files (`mediaitem.api.md` for `PUT .../metadata` and `POST .../bulk/metadata`) already document the array shape with the ADR breaking-change callout in place. Checked the `Media` ADO board for evidence of a client having integrated against either shape: no work items reference UI/client consumption of the MediaItem metadata endpoints — Akshay Gaikwad's current assigned work is exclusively OpenSearch infra provisioning (#32522, #32523, #33184, #33461, #33930, #33934), and Estelle Wu's most recent related item (#33946, "Add Metadata Validation") is backend validation still in Code Review, confirming the endpoint is still under active server-side construction rather than already consumed downstream.
- [x] Add a one-line tracking note wherever the team tracks release readiness (ADO board or the Z:\ docs project's `todos.md`) confirming this check was made and the answer. — Added to `todos.md` under **"RESOLVED: metadata shape breaking-change versioning gate (api-consistency plan Stage 4)"**, dated 2026-07-08, with the full evidence trail so it can be re-checked quickly if UI/integration work against these endpoints starts before the shape is fully stable.

---

## Stage 5 — Verb & URL structure

The bounded-context URL prefixing question is **decided** (2026-07-08): flat, resource-oriented URLs platform-wide, no context-prefix segments. Rationale — a URL should model the public resource graph, not internal DDD module boundaries, which are an implementation-organization concern that can shift independently of what a resource *is*; coupling the two turns a future module refactor into a breaking API change. This also matches the majority (4 of 6) contexts that already skip prefixing. Grouping for documentation/discoverability should be handled via OpenAPI tags, not URL segments. What's below is now an execution checklist for that decision, not an open question — plus one remaining genuine decision (the Folder duplicate-PATCH question).

- [x] `POST /v1/assets/{assetId}/tags`, `POST /v1/catalog/collections/{collectionId}/tags`, `POST /v1/catalog/items/{itemId}/tags`: `POST` → `PUT`, flat paths. *(HTTP Method, Medium)*
- [x] **Flat-URL migration** — context-prefix segment dropped from every affected route table (code + spec), including `api-conventions.md §URL Structure` and an architecture-doc sweep. *(URL Naming, High)*
- [x] **Decision needed → resolved 2026-07-08:** Folder `PATCH` consolidated onto the combined `PATCH /v1/folders/{folderId}` (name + description). Code already implemented it this way; spec had a stale phantom description-only endpoint, now removed.
- [ ] **Acceptance:** re-run the Cross-Endpoint Consistency table from the review against the updated spec — **blocked, see incident note below.**

### Incident — spec-tree file truncation (2026-07-08)

Acceptance review surfaced widespread truncation across `docs/spec/` — some pre-existing in the 2026-07-07 migration commit (`6fc139ee`), some introduced this session (likely unreliable writes to the network-mounted `D:\source\github\magiq-media` drive). Chase's call: **fix `api-conventions.md` now, defer the rest.**

- [x] `docs/spec/shared/api-conventions.md` — reconstructed from the clean git baseline + full replay of every edit made across Stages 1/3/5. Verified complete via direct Windows-side read (563 lines, clean close). Confirmed the file is genuinely fine — an earlier bash-mount check on the same file showed a stale, truncated view; the Linux sandbox's view of this drive can lag behind the real disk. **Treat Read/Write/Edit tool output as authoritative for this drive, not `bash`/`wc`/`git cat-file` run against the mount.**
- [ ] **Deferred — confirmed still truncated, not yet touched (re-verified directly against disk, not the bash mount):**
  - `docs/spec/contexts/Catalog/aggregates/Collection/collection.api.md` — cuts off mid-word in the bulk traceability table
  - `docs/spec/contexts/Metadata/aggregates/RecordType/recordtype.api.md` — cuts off mid-word in the traceability table
  - `docs/spec/contexts/Metadata/aggregates/RecordType/recordtype.write-model.md` — cuts off mid-sentence in Constraint Enforcement Implementation Notes
  - `docs/spec/contexts/Registration/aggregates/Registration/registration.api.md` — cuts off mid-word in Related section
  - `docs/spec/contexts/Catalog/context-overview.md` — cuts off at the `## Relat` heading itself
  - `docs/spec/contexts/Catalog/aggregates/MediaProfile/mediaprofile.api.md` — cuts off mid-word in Related section
  - `docs/spec/contexts/DocumentSigning/aggregates/DocumentSigningSession/documentsigningsession.api.md` — cuts off mid-word in the traceability table (I edited this file today for Stage 5 — the flat-URL edits themselves look correct, only the file's tail is affected)
  - `docs/spec/contexts/Catalog/aggregates/BulkMediaImportJob/bulkmediaimportjob.api.md` — cuts off mid-word in the traceability table (edited today for Stage 2)
  - `docs/spec/contexts/Catalog/aggregates/Folder/folder.api.md` — cuts off mid-word in Related section (heavily edited today for Stage 5 — the body content looks correct, only the tail is affected)
  - `docs/spec/contexts/AssetManagement/aggregates/Asset/asset.write-model.md` — cuts off mid-code-block in the S3 upload service interfaces
  - `docs/spec/architecture/branching-and-deployment.md` — cuts off mid-word in the deploy-handoff section
  - `docs/spec/shared/system-spec.md` — cuts off mid-sentence in the DR runbook section (near end of an otherwise-1128-line file)
- [x] `docs/spec/architecture/service-boundaries.md` — **re-verified, not actually truncated.** Earlier bash-based check was a false positive; direct read confirms the file is complete and well-formed end to end. No action needed.

---

## Stage 6 — Documentation polish (optional, no urgency)

- [ ] Add a one-line glossary entry to `system-spec.md` clarifying "document" carries two distinct meanings (a MediaItem-playing-a-role in Registration; a non-processable Asset in AssetManagement/`asset-storage-and-processing.md`) *(Naming Consistency, Medium)*
- [ ] Consider `allowMultiple` → `allowsMultiple` for strict boolean-naming consistency (`is`/`has`/`can` prefix convention) — optional, low value *(Request Model, Low)*
- [ ] Confirm `roleName` values in `POST /v1/catalog/items/{itemId}/roles/{roleName}/assets` are validated as URL-safe (no slashes/spaces) at the MediaProfile asset-definition level, since it flows directly into a path segment; add a one-line validation note to the spec *(Route Parameter, Low)*

---

## Progress tracking

| Stage | Items | Status |
|---|---|---|
| 0 — Zero-decision doc fixes | 5 groups | **Done (2026-07-08)** |
| 1 — Status code standardization | 12 items | **Done (2026-07-08)** — 3 asset-upload `202` endpoints flagged for a decision, not changed |
| 2 — Identifier naming & list-envelope | 9 items | **Done (2026-07-08)** — 1 response-shape mismatch (`bulk-paths`) flagged, not fixed |
| 3 — Query parameter & filtering | 6 items | **Done (2026-07-08)** — 1 route-path-param naming issue (`InitiateRegistration`) flagged for Stage 5, not fixed here |
| 4 — Versioning gate | 2 items | **Done (2026-07-08)** — premise confirmed to still hold, no `/v2` needed |
| 5 — Verb & URL structure | 11 items (1 decided policy to execute, 1 decision still open) | Not started |
| 6 — Documentation polish | 3 items | Not started |

Update the Status column as stages complete or move to in-progress. When a stage is fully checked off, land the corresponding spec/code changes in the same PR as this checklist update, per the repo's docs-co-location convention (spec changes ship with the code that implements them).
