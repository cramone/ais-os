# API contract gaps — for the magiq-media API team

Surfaced while validating the MAGIQ Media UI mockups against `swagger.json`
(OpenAPI 3.0.0, MAGIQ Media API v1, 104 paths, 160 schemas). Date: 2026-08-12.

These are things the **UI needs to render designed screens** that the contract doesn't
currently define. Each is a real screen already designed (see `screenshots/`), so the UX
intent is settled — what's needed is the API surface to back it. Ordered by UI impact.

Legend: **Screen** = which mockup depends on it. **Blocks** = what the UI can't do without it.

---

## GAP-1 · MediaItem detail response is unschema'd 🔴 highest impact
- **Screen:** 06-mediaitem-detail (the richest screen in the app)
- **Observed:** `GET /v1/items/{itemId}` exists, but its `200` response has **no schema** in the OpenAPI export. `MediaItemSummaryModel` is the only item read model present.
- **Missing fields** (0 occurrences anywhere in the contract): `metadata` (current + draft changeset), `assets` (by role — `{assetId, roleName, assetStatus, order}`), `activeMediaChangeRequestId`, `activeSigningSessionId`, `registrationIds`, `conformanceGaps` (`[{GapType, Identifier}]`), `checkedOutBy` / `checkedOutAt`.
- **Blocks:** assets-by-role panel, current-vs-draft metadata diff, conformance-gap banner, related CR/signing/registration links — i.e. most of the detail page.
- **Ask:** publish the detail response schema for `GET /v1/items/{itemId}`. The read-model spec (`spec/contexts/Catalog/.../mediaitem.read-model.md`, `media-item` table) already describes these fields — just needs to be in the OpenAPI.

## GAP-2 · Checkout / lock state is not exposed anywhere 🔴
- **Screens:** 01-app-shell, 03-library-browse-list, 05-mobile-shell, 06-mediaitem-detail
- **Observed:** zero occurrences of `checkoutStatus` / `checkedOut` / lock in **any** schema, summary or detail.
- **Blocks:** the checkout lock indicator on list/grid rows and the "Checked out" chip + "checked out by / at" on the detail header. Checkout drives write-access affordances across the app.
- **Ask:** expose checkout state on the read models — at minimum `checkoutStatus` (`Available | CheckedOut`) on `MediaItemSummaryModel` (for list badges) and `checkedOutBy` / `checkedOutAt` on the detail response (GAP-1).

## GAP-3 · DocumentSigning has no API 🔴
- **Screen:** 10-signing-session
- **Observed:** 0 signing paths, 0 signing schemas. (Consistent with the backend note that the `DocumentSigningSession` aggregate does not yet exist.)
- **Blocks:** the entire signing screen — envelope lifecycle, sequential signer routing, SecuredSigning webhook activity, checkout-lock-held state.
- **Ask:** when DocumentSigning is built, expose: initiate signing session, get session by id (status `Initiated | EnvelopeCreated | EnvelopeSent | Completed | SignedAssetRecorded | Voided | Cancelled | TimedOut`, `signers[] {email, routingOrder, status}`, `envelopeId`, `signedAssetId`), cancel session, and the `activeSigningSessionId` link on the MediaItem (GAP-1).

## GAP-4 · Audit log has no API 🟠
- **Screen:** 18-audit-log (already marked design-ahead-of-spec — gap ADM-4)
- **Observed:** 0 audit paths.
- **Blocks:** the audit/activity viewer (actor, action, target, time, category filters, export).
- **Ask:** a queryable, tenant-scoped audit event read model + list endpoint (filter by actor / category / date range; cursor-paginated). Proposed event shape is in `screenshots/_build/screens/18-audit-log.html`.

## GAP-5 · Domain status fields are unconstrained strings 🟡
- **Screens:** all status-bearing screens (03, 06, 07, 09, 10)
- **Observed:** MediaItem / ChangeRequest / Registration status fields are plain `string` in the contract (only `conformanceStatus` appears, and not as an enum). No `MediaItemStatus`, `ChangeRequestStatus`, `RegistrationStatus`, `ReviewerStatus`, `SignerStatus` enums exist.
- **Impact:** the client can't generate typed unions for status; the earlier read-model-vs-write-model status drift (Rejected/Withdrawn vs Draft|PendingApproval|Published|Revising|Archived) **can't be resolved from the contract**. UI currently hardcodes the write-model set.
- **Ask:** publish these as OpenAPI string enums so the generated client is typed and the canonical value set is unambiguous. Confirm the MediaItem set is `Draft | PendingApproval | Published | Revising | Archived`.

## GAP-6 · ChangeRequest reviewers not in any schema 🟡
- **Screen:** 07-change-request-review
- **Observed:** no `reviewers` field in any schema; the CR detail response is inline and minimal (id, mediaItemId, createdById, commentCount, createdAt). Only `ChangeRequestCommentSummaryModel` is fully defined.
- **Blocks:** the reviewer tally / decision panel (`reviewers[] {reviewerId, status, decidedAt}` with `ReviewerStatus`).
- **Ask:** include the reviewer list on the CR detail response (`GET /v1/change-requests/{id}`), currently inline/undocumented.

---

## GAP-7 · Users & roles (RBAC) has no API 🟠
- **Screen:** Admin › Users (nav item exists; no screen — no API to build against)
- **Observed:** zero user / member / role / permission endpoints in the contract.
- **Blocks:** user list, role assignment (ADM-2), the whole RBAC admin surface. Permission-gated UI
  across the app currently has no source for "what can this user do".
- **Ask:** user/member read + role-assignment endpoints (list members, get/set roles). Actor types are
  System/User/Guest per the auth model — expose the user's roles/permissions for the client to gate UI
  (server still enforces).

## GAP-8 · Tenant provisioning has no API 🟡
- **Screen:** Admin › tenant setup (ADM-1) — not designed (no API)
- **Observed:** no tenant endpoints. Tenant comes from the JWT; there's no first-run provisioning surface.
- **Ask:** tenant provisioning / settings endpoints if tenant admin is in scope for this UI (may live in a
  separate platform admin app — confirm ownership).

## GAP-9 · Storage quota not exposed 🟡
- **Screen:** quota view / enforcement (ADM-3) — not designed (no API)
- **Observed:** no quota endpoints. Upload guards reference `MaxFileSizeBytes` per profile but there's no
  tenant/storage quota read model.
- **Ask:** a storage-quota read endpoint (used, limit, per-tenant) so the UI can show usage and warn before
  enforcement. Regulated tenants have storage limits.

## Summary table

| Gap | Screen | Severity | One-line ask |
|---|---|---|---|
| 1 | MediaItem detail | 🔴 | Publish detail response schema (metadata, assets, related IDs, conformanceGaps) |
| 2 | Checkout/lock | 🔴 | Expose checkoutStatus on summary + checkedOutBy/At on detail |
| 3 | Signing | 🔴 | Build DocumentSigning API + session read model |
| 4 | Audit | 🟠 | Audit event read model + query endpoint |
| 5 | Status enums | 🟡 | Publish status fields as OpenAPI enums |
| 6 | CR reviewers | 🟡 | Add reviewers[] to CR detail response |
| 7 | Users/roles (RBAC) | 🟠 | Member + role-assignment endpoints |
| 8 | Tenant provisioning | 🟡 | Tenant admin endpoints (confirm ownership) |
| 9 | Storage quota | 🟡 | Per-tenant quota read endpoint |

## What's already solid (no action)
Field names + routes the UI uses are accurate where defined: `MediaItemSummaryModel`, the RecordType
field model (`sourceCapability`, `isImmutable`, constraints), bulk envelope + `BulkCreateMediaItemsFailedModel`,
`ChangeRequestCommentSummaryModel`, `InitiateAssetUploadResponse`, registration requests, and all
item/bulk/search/folder/collection/profile/record-type routes. Full detail in
`design-system/contract-validation.md`.
