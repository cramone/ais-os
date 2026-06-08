# Postman Collection — Gap Analysis
_Compared against: `Magiq-Media-API.postman_collection.json` (176 requests, 7 scenario flows)_
_Spec baseline: `spec/contexts/**/business-scenarios.md` and scenario files_
_Date: 2026-06-03_

---

## Summary

The collection has solid coverage of the happy-path API surface but has three categories of problems:

1. **ChangeRequest API is wrong** — the collection models CR as having a full review lifecycle (assign reviewer, approve, reject, withdraw) which directly contradicts the spec. These operations belong on `MediaItem` only.
2. **Missing `POST /change-requests`** — the endpoint to create a comment thread (CRC-1) is absent entirely.
3. **~25 spec scenarios have no corresponding flow** in the business scenario section, leaving large areas untested end-to-end.
4. **DocumentSigning context entirely absent** (acknowledged deferred — recorded here for completeness).

---

## 1. API Contract Mismatches (Spec vs Collection)

### 1.1 ChangeRequest endpoints that shouldn't exist

Per spec, `MediaChangeRequest` is a comment thread only — no lifecycle status, no reviewer roster. Review decisions live on `MediaItem`.

| Endpoint in Collection | Problem |
|---|---|
| `POST /change-requests/:changeRequestId/reviewers/:reviewerId` | Not in spec — reviewers are specified at MediaItem publish time |
| `DELETE /change-requests/:changeRequestId/reviewers/:reviewerId` | Not in spec |
| `POST /change-requests/:changeRequestId/approve` | Not in spec — approve is `POST /catalog/items/:itemId/approve` |
| `POST /change-requests/:changeRequestId/reject` | Not in spec — reject is `POST /catalog/items/:itemId/reject` |
| `POST /change-requests/:changeRequestId/withdraw` | Not in spec — withdraw is `POST /catalog/items/:itemId/withdraw` |

Scenario 4 and Scenario 6 in the collection call `/change-requests/.../approve` **and then** `/catalog/items/.../approve` — the double-approval pattern is not in the spec. The single `POST /catalog/items/:itemId/approve` is the authoritative path.

### 1.2 Missing endpoint

| Missing Endpoint | Spec Reference | Description |
|---|---|---|
| `POST /change-requests` | CRC-1 | Create a comment thread for a review session |

The collection has `GET /change-requests/:changeRequestId` (read) and all comment sub-resource endpoints, but the create call is absent.

### 1.3 Checkout body gap (CR-First)

The `POST /catalog/items/:itemId/checkout` spec requires `withChangeRequest` (bool) and `reviewerIds` (array) in the request body for CR-first checkout scenarios (C-7 through C-10). The collection's existing checkout call likely omits these fields — no CR-first scenario flows exist to exercise this path.

---

## 2. Missing Business Scenario Flows

These are spec-defined scenarios with no corresponding flow in the Postman business scenarios section.

### AssetManagement

| Scenario | What's missing |
|---|---|
| A-2 — Standalone Upload (drag-and-drop, no mediaItemId) | Separate scenario flow with no `mediaItemId` in initiate body, then assign to role later |
| AM-5 — Virus Scan Failure | System-driven, but a verification flow showing `GET /assets/:id` returning `InfectionDetected` |
| AM-6/AM-7 — Archive then Hard Delete | Two-step flow: archive → verify → delete |

### Catalog — Collections & Folders

| Scenario | What's missing |
|---|---|
| C-1 — Set Up a Collection Structure | No scenario showing `POST /catalog/collections` → `POST /catalog/collections/:id/folders` hierarchy setup |
| C-3 — Archive a Collection | No scenario for `POST /catalog/collections/:id/archive` |
| MW-3 — First Folder Assignment | No scenario for `PUT /catalog/items/:itemId/folder` (first assignment from unassigned pool) |
| MW-7 — Browse Unassigned Pool | No scenario for `GET /catalog/items?unassigned=true` |

### Catalog — MediaItem Lifecycle

| Scenario | What's missing |
|---|---|
| C-4 — Publish with Rejection (one reviewer rejects) | Reject path → back to Draft → re-publish cycle |
| C-5 — Cross-Collection Move | `PUT /catalog/items/:itemId/folder` across collections |
| C-6 — Withdraw While Pending Approval | `POST /catalog/items/:itemId/withdraw` from `PendingApproval` |
| C-7 — CR-First Solo Checkout | Checkout with `withChangeRequest: false` on a no-policy profile |
| C-8 — CR-First Checkout with CR | Checkout with `withChangeRequest: true, reviewerIds: [...]` |
| C-9 — ForceRelease Auto-Abandons CR | ForceRelease with active CR — verifies CR abandoned |
| C-10 — Profile Requires CR, Rejected at Checkout | `withChangeRequest: false` rejected when `ReviewPolicy = RequiredForPublish` |
| MW-1 — Published → Withdraw → Re-publish | `withdraw` on a Published item, re-publish produces v2 |
| MW-2 — Direct Archive | `POST /catalog/items/:itemId/archive` from Draft/Published |
| MW-6 — Metadata Validation Failure at Publish | `publish` with incomplete metadata returns 422; verify all field errors returned |
| BULK-2 — Bulk Metadata Update | `POST /catalog/items/bulk/metadata` with mix of successes and per-item errors |
| MI-1 — Version Increment with Asset Pipeline | Full replace-asset + republish flow producing v2 |
| MI-2 — Review Rejection then Approval | Two submit cycles; second produces v1 |
| BR-1 — Begin Revision + Publish | `begin-revision` on Published item, edit, republish as v2 |
| BR-2 — Begin Revision + Discard | `begin-revision` then `discard-revision` — verify version unchanged |

### Catalog — MediaProfiles

| Scenario | What's missing |
|---|---|
| MP-2 — Re-pin to New RecordType Version | `PUT /catalog/profiles/:id/record-types/:recordTypeId/version` flow |
| MP-3 — Deprecate MediaProfile | `POST /catalog/profiles/:id/deprecate` flow |

### ChangeRequests

| Scenario | What's missing |
|---|---|
| CRC-1 — Create Comment Thread | `POST /change-requests` → link via `commentThreadId` in publish body |
| CRC-3 — Edit Own Comment | `PATCH /change-requests/:id/comments/:commentId` |
| CRC-4 — Delete Own Comment | `DELETE /change-requests/:id/comments/:commentId` |
| CRC-5 — Non-Author Edit (403) | Error scenario: PATCH by wrong user |
| CRC-6 — Reviewer Adds Comment | Comment by assigned reviewer (participant check) |
| CRC-7 — Non-Participant Adds Comment (403) | Error scenario: non-participant comment attempt |

### Registration

| Scenario | What's missing |
|---|---|
| R-3 — Post-Confirmation Amendment | `POST /registrations/:id/amendments` on a `Confirmed` registration → approve amendment |
| R-4 — Attach Unpublished MediaItem (409) | Error scenario: attach/initiate with `Draft` MediaItem returns 409 |
| R-5 — Registration Cancellation | `POST /registrations/:id/cancel` flow |
| R-6 — Multi-Item Registration | Initiate + multiple `POST /registrations/:id/documents` + submit |

### Metadata

| Scenario | What's missing |
|---|---|
| M-2 — Evolve RecordType Field (type change) | Create draft → replace field → publish new version |
| M-3 — Deprecate RecordType | `POST /metadata/record-types/:id/deprecate` flow |
| M-4 — Bulk Metadata Update | Cross-context flow: set metadata batch on MediaItem against a RecordType schema |

### DocumentSigning (deferred — recorded for completeness)

| Scenario | Status |
|---|---|
| DS-1 — Happy Path Signing | No endpoints in collection; `DocumentSigningSaga` deferred |
| DS-2 — Envelope Voided | No endpoints in collection |
| DS-3 — Stale Lock Timeout | No endpoints in collection |

Missing endpoints: `POST /media-items/{id}/media-signing-sessions`, `GET /media-signing-sessions/{id}`, webhook endpoints.

---

## 3. Existing Scenario Flows — Issues

| Scenario | Issue |
|---|---|
| Scenario 4 (Media Item Review) | Calls `POST /change-requests/:id/approve` before `POST /catalog/items/:id/approve` — double approval not in spec. Remove the CR approve step. |
| Scenario 6 (Change Request Review Flow) | Same — CR-side approve/reject should be removed; review is cast directly on MediaItem |
| Scenario 6 step 2 | `POST /change-requests/:id/reviewers/:reviewerId` — this endpoint doesn't exist in spec; reviewers are set in the publish body |

---

## 4. Coverage That's Good

The following spec scenarios are well-represented:

- **A-1**: Single upload → confirm → tag → verify ✓  
- **AM-4**: Multipart upload → complete (+ abort alternative) ✓  
- **MP-1**: MediaProfile create → asset definition → capabilities → review policy → publish ✓  
- **R-1**: Registration initiate → attach doc → submit → record submission → confirm ✓  
- **R-2**: Reject → resubmit cycle ✓  
- **M-1**: RecordType CRUD lifecycle (all individual endpoints covered) ✓  
- All CRUD endpoints for Collections, Folders, MediaItems, MediaProfiles, RecordTypes, Assets ✓  
- Version history endpoints (`GET /versions`, `GET /versions/:n`, `DELETE /versions/:n`) ✓  

---

## 5. Recommended Priority Order

1. **Fix ChangeRequest endpoint mismatches** — remove the 5 incorrect endpoints from the collection and fix Scenarios 4 and 6
2. **Add `POST /change-requests`** (CRC-1) — the comment thread create call
3. **Add CR-first checkout scenarios** (C-7 through C-10) — required for Q2 auth/security work
4. **Add registration gaps** (R-3, R-5, R-6) — these are production flows
5. **Add MediaItem lifecycle gaps** (C-4, MW-1, BR-1, BR-2, MI-1) — version management is core to the API
6. **Add error scenarios** (MW-6, R-4, CRC-5, CRC-7) — needed for contract testing
7. **DocumentSigning** — track with saga implementation
