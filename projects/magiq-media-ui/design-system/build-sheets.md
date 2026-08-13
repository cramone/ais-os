# Per-screen build sheets — MAGIQ Media UI

Turns each of the 19 mockups into a buildable spec. Date: 2026-08-12.
Endpoints are real (`swagger.json`) unless marked 🔴 **GAP** (see `Gaps/api-contract-gaps.md`).
Components reference `component-props.ts`. Conventions: TanStack Router (file routes, typed params),
TanStack Query (per-feature key factories, mutations invalidate — never patch), Zustand for ephemeral
UI only, cursor pagination (no totals), model all four ingestion states, tenant from JWT (no tenant in URL).

**State tiers:** SRV = TanStack Query · URL = router search params · CLI = Zustand.

---

## 1 · App shell  → `__root` / `_app` layout route
- **Components:** TopBar, NavRail, ProcessingToast, breadcrumb, content `<Outlet/>`.
- **SRV:** nav badge counts (uploads, change-requests) — prefetch on layout mount. Tenant + user from auth context (JWT claims), not an endpoint.
- **CLI:** rail collapsed bool; command-palette open.
- **States:** processing live-region wired app-wide.
- **Notes:** shell renders on every authed route; single 401→refresh→retry interceptor lives here.

## 2 · Tenant switch  → menu in TopBar (no route)
- **Action:** `POST` magiq-auth token endpoint with target `tenant_id` (silent, D-006) → new access token in memory.
- **On switch:** `queryClient.clear()` (all caches tenant-scoped) → reset tenant-scoped Zustand → `router.navigate('/library')` → announce.
- **CLI:** in-flight upload queue → if non-empty, show upload-guard dialog before switch.
- **GAP:** none (auth side). Selector shown only if >1 tenant.

## 3 · Library browse (list)  → `/library/folders/$folderId`
- **SRV:** `GET /v1/folders/{folderId}/items` → `mediaKeys.byFolder(folderId, {status, sort})`; collection/folder tree `GET /v1/folders?...` (`GetFolderHierarchyQuery`) → `folderKeys.tree(collectionId)`.
- **URL:** `status`, `sortBy`, `sortOrder`, `view=list`, `pageToken`.
- **Rows:** MediaItemSummaryModel (title, status, currentVersionNumber, owner, publishedAt, conformanceStatus). 🔴 **GAP-2** checkout lock flag — no field yet.
- **States:** empty folder, load-error, virtualize >100 rows (TanStack Virtual).
- **Nav:** row → screen 6. Upload button → screen 4.

## 4 · Upload flow  → global UploadQueue (Zustand, outside router)
- **Action:** `POST /v1/assets/uploads` → `{id, uploadUrl, expiresAt}` → client PUT to S3 direct. ≥100MB → `POST /v1/assets/uploads/multipart` (initiate) + part URLs + complete.
- **CLI:** upload queue store (survives nav; per-chunk retry/resume).
- **SRV:** post-upload poll asset status with backoff → `assetKeys.detail(id)`; stop on unmount/tab-blur.
- **States:** client % (real) vs server Validating→Processing→Active|Failed (polled). Failure per category: virus=terminal, UploadExpired=re-upload, ProcessingError=retry.
- **Target:** MediaItem or Unassigned pool (standalone — skips pipeline until assign, S12).

## 5 · Mobile shell  → responsive variant of screen 1
- **Same data as 1.** Drawer nav + bottom tab bar (5 max) + upload FAB. Tenant switcher in drawer.
- **Breakpoint:** <768 → mobile; reload-safe device gate.

## 6 · MediaItem detail  → `/library/items/$itemId`
- **SRV:** `GET /v1/items/{itemId}` 🔴 **GAP-1** (detail response unschema'd — metadata, assets, activeCR/Signing, registrationIds, conformanceGaps all missing); versions `GET /v1/items/{itemId}/versions` → `mediaKeys.versions(itemId)`.
- **Mutations:** publish/withdraw/begin-revision/discard-revision/archive/reject/approve (`POST /v1/items/{id}/…`), metadata `PATCH /v1/items/{id}/metadata[/{fieldName}]`, assets `POST|DELETE /v1/items/{id}/roles/{roleName}/assets`, tags, folder move. Each → invalidate `mediaKeys.detail(id)` + list.
- **States:** under-review banner (blocks owner writes), processing assets, conformance gap, checkout (🔴 GAP-2).
- **Related:** CR (screen 7), signing (🔴 GAP-3), registrations (screen 9).

## 7 · Change Request review  → `/change-requests/$changeRequestId`
- **SRV:** `GET /v1/change-requests/{id}` (inline; 🔴 **GAP-6** reviewers not in schema); comments `GET /v1/change-requests/{id}/comments` → `changeRequestKeys.comments(id)` (ChangeRequestCommentSummaryModel — threaded via parentCommentId).
- **Mutations:** decisions on the MediaItem — `POST /v1/items/{id}/approve` · `/reject` (reason required); comments `POST|PATCH|DELETE /v1/change-requests/{id}/comments[/{commentId}]`.
- **States:** review-active, reviewer tally, self-review guard (PERM-3), reject-reason inline.

## 8 · Search (faceted)  → `/search`
- **SRV:** `GET /v1/items/search?q=&status=&folderId=&collectionId=` (OpenSearch, `search_after` cursor) → `searchKeys.query(params)`.
- **URL:** `q`, facets (status, profile, owner, date, tags + AND/OR), cursor. Debounce 300ms; cancel in-flight on change.
- **States:** eventual-consistency banner, `<mark>` highlight, no-results (+did-you-mean), relevance score.
- **Facets:** derive from indexed keyword fields; counts from response aggregations.

## 9 · Registration lifecycle  → `/registrations/$registrationId`
- **SRV:** `GET /v1/registrations/{id}` (inline) → `registrationKeys.detail(id)`; list `GET /v1/registrations`.
- **Mutations (owner):** initiate `POST /v1/registrations` `{registrationAuthority, registrationType}`, submit, attach item, resubmit, cancel. System transitions (record-submission/confirm/reject) arrive via polling/events.
- **Enums:** status Initiated→Submitted→PendingConfirmation→Confirmed|Rejected(→Resubmitted)|Cancelled; RegistrationItemType (ApplicationForm/SupportingEvidence/…); RegistrationType (Electronic/Physical).
- **States:** stepper w/ owner↔authority actors, reference on confirm, cancel gated.

## 10 · Signing session  → `/signing/$sessionId`  🔴 GAP-3 (no API)
- **When built:** GET session (status Initiated→…→SignedAssetRecorded|Voided|Cancelled|TimedOut, signers[] {email, routingOrder, status}, envelopeId, signedAssetId), initiate, cancel. Activity from SecuredSigning webhooks.
- **States:** envelope stepper, sequential signer routing, checkout-lock-held, cancel-gated-after-send.
- **For now:** static/design-only until DocumentSigning API exists.

## 11 · Admin — Record types  → `/admin/record-types/$recordTypeId`
- **SRV:** `GET /v1/record-types/{id}` → `recordTypeKeys.detail(id)`; list `GET /v1/record-types`.
- **Mutations:** create/publish draft, add/update/replace/remove field, set aliases, deprecate (16 record-type paths). Field model = AddRecordTypeFieldModel (fieldName, fieldType, isRequired, isSearchable, isImmutable, sourceCapability, constraints).
- **States:** Published-vN + editing-draft badge, FieldType immutable (Replace to change), 100-field cap, capability-contributed locked.

## 12 · Admin — Media profiles  → `/admin/profiles/$profileId`
- **SRV:** `GET /v1/profiles/{id}` → `profileKeys.detail(id)`; list `GET /v1/profiles` (18 paths).
- **Mutations:** create/new-revision/publish/deprecate, attach record-type + pin version, set default, add/reorder asset definitions, set review/checkout policy.
- **Enums:** status Draft|Published|Deprecated; Capability (9 — 3 shown active); ReviewPolicy (None|RequiredForPublish); CheckoutPolicy (None|RequiredForEdit).

## 13 · Login (OIDC PKCE)  → `/login` (public)
- **Action:** generate PKCE verifier/challenge → redirect to magiq-auth authorize → callback `/auth/callback` exchanges code (with verifier) → access token in memory, refresh in httpOnly cookie. Nothing in localStorage.
- **No API of ours** — all magiq-auth. Post-login → intended route or `/library`.

## 14 · 403 permission-denied  → error boundary (not a route)
- **Trigger:** 403 from any query/mutation → render this, do NOT redirect to login (403≠401).
- **Data:** ProblemDetails (errorCode Forbidden, resourceOwner). Actions: back to library, request access.

## 15 · Empty / error states  → shared StateCard, used everywhere
- **Not a screen** — the reusable states each feature composes. Bind tone to query state (isLoading skeleton / isError retry / empty / processing). error+processing → aria-live.

## 16 · Collection/Folder manage  → `/collections/$collectionId/manage`
- **SRV:** `GET /v1/collections/{id}` → `collectionKeys.detail(id)`; folder tree.
- **Mutations:** `PATCH /v1/collections/{id}` (name/description/**visibility** Private|Unlisted|Public), set default-profile, tags, `POST /v1/collections/{id}/archive` (cascade; active-registrations block). Folders: create/rename/move/archive (16 folder paths).
- **States:** archive danger-zone confirm.

## 17 · Bulk operations  → selection layer + result panel (no dedicated route)
- **URL/CLI:** selection set (URL for shareable, CLI for large). Max 100/batch.
- **Mutations:** `POST /v1/items/bulk` (create), `PUT /v1/items/bulk/metadata`. Params: onError (ContinueOnError|FailFast), onDuplicate (Skip|Reject|**AutoSuffix**).
- **Response:** {succeeded, failed, skipped}; per-item BulkCreateMediaItemsFailedModel {index, title, errorCode, message, suggestedName}. 201 all-ok / 202 partial.
- **States:** navy bulk action bar, partial-success tallies, per-item errors.

## 18 · Audit log  → `/admin/audit`  🔴 GAP-4 (no API)
- **When built:** queryable tenant-scoped event read model (actor/action/target/time/category), cursor-paged, export.
- **For now:** design-only; flagged in-UI as ahead-of-spec.

## 19 · Notifications  → panel in TopBar (+ optional `/notifications`)
- **SRV:** notifications list (endpoint TBD — event-sourced; likely a read model) → `notificationKeys.list()`; unread count feeds shell bell.
- **Types:** virus-blocked, review-assigned, review-approved/published, processing-failed, signing-completed, registration-confirmed, checkout-force-released.
- **States:** grouped by day, read/unread, deep links, mark-all-read, aria-live.

---

## Coverage screens 20–28 (added 2026-08-12)

- **20 · Create MediaItem** → `/library/new` (or modal). `POST /v1/items` `{profileId, title, folderId?, author?, recordDate?, description?}` or `POST /v1/folders/{id}/items`. profileId required + immutable-after-create warning. On success → item detail (6).
- **21 · Version compare** → `/library/items/$itemId/versions/$n`. `GET /items/{id}/versions` + `/versions/{n}` → `mediaKeys.versions(id)`. Metadata + asset diff (changed/added/unchanged). Linked from CR review (7) "what changed".
- **22 · Move item** → dialog. `PUT /v1/items/{id}/folder` `{folderId}` (AssignOrMoveMediaItemFolderRequest — unified assign+move). Folder/collection tree picker. Invalidate source+dest folder lists.
- **23 · Publish** → dialog. `POST /v1/items/{id}/publish` `{reviewerIds}`. Empty → publish now; with ids → PendingApproval (creates CR). Profile ReviewPolicy=RequiredForPublish forces ≥1 reviewer. Self-review guard.
- **24 · Create Collection/Folder** → `/collections/new`. `POST /v1/collections` `{name, description, visibility}` (Private|Unlisted|Public); folder = `POST /v1/folders` `{name, parentFolderId, openedDate?, closedDate?, originator?}`.
- **25 · Confirm dialogs** → shared `ConfirmDialog` (BannerProps-like). Variants: withdraw, archive (cascade), discard-revision, force-release. Destructive = danger button. Wraps the lifecycle POSTs.
- **26 · Checkout conflict** → state of item detail (6) when `checkedOutBy ≠ me`. 🔴 GAP-2 (no checkout field). Read-only + notify-owner + admin force-release (audited).
- **27 · Signing exceptions** → states of signing (10). 🔴 GAP-3. Voided (compensation, lock released) + Declined (new session to retry).
- **28 · Registration rejected** → state of registration (9). `GET /v1/registrations/{id}` status=Rejected. Rejection reason + `POST` resubmit (Rejected→Resubmitted). Replace-document action.

## Query-key factories (author in `lib/query/keys.ts`)
```
mediaKeys        = { all, byFolder(fid,params), list(params), detail(id), versions(id), search(params) }
collectionKeys   = { all, list, detail(id) }
folderKeys       = { tree(collectionId), children(parentId) }
registrationKeys = { all, list, detail(id) }
changeRequestKeys= { detail(id), comments(id) }
profileKeys      = { all, list, detail(id) }
recordTypeKeys   = { all, list, detail(id) }
assetKeys        = { detail(id) }
searchKeys       = { query(params) }
notificationKeys = { list, unreadCount }
```
Never inline arrays. Mutations invalidate the affected factory keys; never hand-patch server state.

## Build order (suggested)
1. Shell (1) + Login (13) + 403 (14) + StateCard (15) — the frame + auth + error surfaces.
2. Library list (3) + Item detail (6, pending GAP-1) + Upload (4) — the core loop.
3. Search (8), Collections (16), Admin record-types/profiles (11/12).
4. CR review (7), Registration (9), Bulk (17), Notifications (19), Mobile (5).
5. Signing (10) + Audit (18) — after their APIs land (GAP-3, GAP-4).
