# magiq-media — Use Cases

> Single index of all use cases documented in the spec. References point to source scenario files.
> See **[Gap Report](#gap-report--production-readiness)** at the bottom for what's missing.

---

## Actors

| Actor | Description |
|---|---|
| **User** | Authenticated tenant user — uploads, edits, reviews |
| **Owner** | User who owns a specific resource (MediaItem, Asset, etc.) |
| **Reviewer** | User nominated to review a change request |
| **Admin** | Tenant administrator — elevated permissions (force-release, archive overrides) |
| **System** | Internal service actor — saga orchestration, processing workers |
| **External Adapter** | External authority integration (e.g. copyright registration confirmation) |

---

## Asset Management

Source: `spec/contexts/AssetManagement/business-scenarios.md`

| ID | Use Case | Actors | Key Aggregates |
|---|---|---|---|
| A-1 | Upload and process a media asset (presigned URL → S3 → pipeline) | User | Asset, AssetIngestionSaga |
| A-2 | Drag-and-drop upload — standalone asset before MediaItem exists | User | Asset, AssetIngestionSaga |
| A-3 | Processing pipeline failure — detect, surface error, allow retry | System, User | Asset, AssetIngestionSaga |
| AM-4 | Large file upload via multipart S3 upload | User | Asset, AssetIngestionSaga |
| AM-5 | Virus scan failure — asset infected, quarantine and notify | System, User | Asset, AssetIngestionSaga |
| AM-6 | User-initiated asset archive | Owner | Asset |
| AM-7 | Asset hard delete | Admin | Asset |
| DL-1 | Download original asset via presigned URL | User (any tenant) | Asset |
| DL-2 | Download asset rendition via presigned URL | User (any tenant) | Asset |
| DL-3 | Expired download URL — S3 returns 403, client re-requests | User | Asset |

---

## Catalog — Browse & Query

Source: `spec/contexts/Catalog/aggregates/Collection/collection.api.md`, `spec/contexts/Catalog/aggregates/MediaItem/mediaitem.api.md`

| ID | Use Case | Actors | Key Aggregates |
|---|---|---|---|
| BRW-1 | List MediaItems in folder (paginated) — `GET /v1/catalog/folders/{folderId}/items` | User | MediaItem |
| BRW-2 | List collections (paginated) — `GET /v1/catalog/collections` | User | Collection |
| BRW-3 | Get MediaItem detail — `GET /v1/catalog/items/{itemId}` | User | MediaItem |
| BRW-4 | Get MediaItem version history — `GET /v1/catalog/items/{itemId}/versions` | User | MediaItem |

---

## Catalog — Collections & Folders

Source: `spec/contexts/Catalog/business-scenarios.md`

| ID | Use Case | Actors | Key Aggregates |
|---|---|---|---|
| C-1 | Set up a collection structure (create collection + folders) | User | Collection, Folder |
| C-3 | Archive a collection (cascades to child items) | Admin | Collection, MediaItem |

---

## Catalog — MediaItem Lifecycle

Source: `spec/contexts/Catalog/business-scenarios.md`

| ID | Use Case | Actors | Key Aggregates |
|---|---|---|---|
| C-2 | Publish a MediaItem with no review policy | Owner | MediaItem |
| C-4 | Edit lock — checkout without signing | Owner | MediaItem |
| C-5 | Cross-collection MediaItem move | Owner | MediaItem, Folder |
| C-6 | Checkout conflict — concurrent edit attempt, admin force-release | User, Admin | MediaItem |
| C-7 | CR-first checkout — solo, no review required | Owner | MediaItem |
| C-8 | CR-first checkout — with change request and reviewer approval | Owner, Reviewer | MediaItem, MediaChangeRequest |
| C-9 | CR-first checkout — force-release auto-abandons CR | Admin | MediaItem, MediaChangeRequest |
| C-10 | CR-first checkout — profile requires CR (rejected at checkout without one) | Owner | MediaItem |
| MW-1 | MediaItem withdrawal (revert published item) | Owner | MediaItem |
| MW-2 | MediaItem direct archive (individual) | Owner | MediaItem |
| MW-3 | First folder assignment from unassigned pool | Owner | MediaItem, Folder |
| MW-4 | User-initiated checkout abandon | Owner | MediaItem |
| MW-6 | Metadata validation failure at submit for review | Owner | MediaItem |
| MW-7 | Browse unassigned pool | User | MediaItem |
| MW-8 | Checkout of archived MediaItem — rejected at domain guard | Owner | MediaItem |
| BULK-2 | Bulk metadata update across MediaItems — shared fields applied to up to 100 items, per-item error handling | Owner | MediaItem |
| MI-1 | Simple version increment with asset pipeline | Owner, System | MediaItem, Asset |
| MI-2 | Change request rejection then approval — full version lifecycle | Owner, Reviewer, System | MediaItem, Asset, MediaChangeRequest |

---

## Catalog — MediaProfile

Source: `spec/contexts/Catalog/business-scenarios.md`

| ID | Use Case | Actors | Key Aggregates |
|---|---|---|---|
| MP-1 | Create and publish a MediaProfile | Admin | MediaProfile |
| MP-2 | Re-pin a MediaProfile to a new RecordType version | Admin | MediaProfile |
| MP-3 | Deprecate a MediaProfile — blocks new assignments, frees name, cleans up default asset index | Admin | MediaProfile |

---

## Change Requests

Source: `spec/contexts/ChangeRequests/business-scenarios.md`

| ID | Use Case | Actors | Key Aggregates |
|---|---|---|---|
| CR-1 | Review-gated publish — rejection and resubmission cycle | Owner, Reviewer | MediaChangeRequest, MediaItem |
| CR-2 | Auto-resolution via reviewer withdrawal | Reviewer, System | MediaChangeRequest |
| CR-3 | Reviewer management — reassignment mid-review | Admin, Reviewer | MediaChangeRequest |
| CR-4 | CR-first checkout — full approval cycle (two reviewers) | Owner, Reviewer | MediaChangeRequest, MediaItem |
| CR-5 | CR-first checkout — force-release compensation | Admin, System | MediaChangeRequest, MediaItem |
| CRC-1 | Add threaded comment to change request; soft-delete own comment | Owner, Reviewer | MediaChangeRequest |
| CRC-2 | Reviewer comments before approving — independent actions on SubmissionBound CR | Owner, Reviewer | MediaChangeRequest |
| CRT-1 | Review timeout — scanner rejects stale CR after 30 days, MediaItem returns to Draft | System | MediaChangeRequest, MediaItem |

---

## Metadata (RecordType)

Source: `spec/contexts/Metadata/business-scenarios.md`

| ID | Use Case | Actors | Key Aggregates |
|---|---|---|---|
| M-1 | Create and publish a RecordType schema | Admin | RecordType |
| M-2 | Evolve a RecordType field (type change — new version) | Admin | RecordType |
| M-3 | Deprecate a RecordType — blocks new MediaProfile attachments, existing pins unaffected | Admin | RecordType |
| M-4 | Bulk metadata update on a MediaItem (atomic multi-field set, per-item) | Owner | MediaItem |

---

## Document Signing

Source: `spec/contexts/DocumentSigning/business-scenarios.md`

| ID | Use Case | Actors | Key Aggregates |
|---|---|---|---|
| DS-1 | Happy path — contract signed and MediaItem published | Owner, Signer | DocumentSigningSession, MediaItem |
| DS-2 | Envelope voided — compensation path | System, Admin | DocumentSigningSession, MediaItem |
| DS-3 | Stale lock — force-release via signing session timeout | System | DocumentSigningSession, MediaItem |

---

## Registration

Source: `spec/contexts/Registration/business-scenarios.md`

| ID | Use Case | Actors | Key Aggregates |
|---|---|---|---|
| R-1 | Electronic registration — full lifecycle (initiate → submit → confirm) | Owner, External Adapter | Registration, MediaItem |
| R-2 | Registration rejection and resubmission | Owner, External Adapter | Registration |
| R-3 | Post-confirmation document addition (amendment) | Owner | Registration |
| R-4 | Registration rejected — MediaItem not yet Published (initiate and attach paths) | Owner | Registration, MediaItem |
| R-5 | Registration cancellation — any status except Confirmed | Owner | Registration |
| R-6 | Multi-item registration — primary document + multiple supporting documents | Owner | Registration, MediaItem |

---

---

# Gap Report — Production Readiness

Use cases needed before production. Grouped by domain and severity.

---

## 🔴 Critical — Blockers

These gaps mean flows will fail or be unverifiable in production.

### Auth & Identity (no scenarios exist)

| Gap ID | Use Case | Why Critical |
|---|---|---|
| AUTH-1 | Token acquisition — user login, JWT issued | Every API call requires auth; no scenario tests token path |
| AUTH-2 | Expired token rejected (401) | Token validation is a security boundary; must be exercised |
| AUTH-3 | Insufficient permissions rejected (403) | Authorization guard must be tested per-operation |
| AUTH-4 | Cross-tenant access denied | Tenant isolation is a compliance requirement for government customers |
| AUTH-5 | Service account / API key auth | System actors (sagas, workers) use system tokens; no scenario covers this |

### Search (no scenarios exist)

| Gap ID | Use Case | Why Critical |
|---|---|---|
| SH-1 | Full-text search across MediaItems | Primary discovery path for users |
| SH-2 | Faceted filter (status, content type, date range) | Required for regulated content browsing |
| SH-3 | Tag-based query (multi-tag AND/OR) | Metadata-driven access pattern used by integrations |
| SH-4 | Owner-scoped search (user sees only their items) | Privacy/isolation requirement |

---

## 🟠 High — Required Before GA

Missing these means untested production paths or support incidents.

### Catalog — Browse & Query ✅ Resolved

All 4 were already implemented and spec'd before this gap report was written. Endpoints, handlers, query objects, and response contracts all exist. Added to use-case index above.

### Bulk Operations

| Gap ID     | Use Case                              | Why Needed                                                                                                  |
| ---------- | ------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| BULK-1     | Bulk archive MediaItems               | Operational need — admins process batches                                                                   |

### Document Signing — Signer Paths

| Gap ID | Use Case | Why Needed |
|---|---|---|
| DS-4 | Signer declines (not voided by admin) | Decline is a distinct signer action; compensation differs from DS-2 |
| DS-5 | Multi-signer workflow (sequential or parallel) | Contracts often require multiple signers |

---

## 🟡 Medium — Required Before Production Confidence

Missing these creates operational blind spots or compliance risk.

### Admin / Tenant Operations (no scenarios exist)

| Gap ID | Use Case | Why Needed |
|---|---|---|
| ADM-1 | Tenant provisioning | First-run setup; no scenario documents the expected state |
| ADM-2 | User role assignment | RBAC is the permission model; role management unspecified |
| ADM-3 | Storage quota check / enforcement | Regulated environments have storage limits |
| ADM-4 | Audit log — query activity history | Compliance requirement for government customers |

### Error Paths

| Gap ID    | Use Case                                            | Why Needed                                                            |
| --------- | --------------------------------------------------- | --------------------------------------------------------------------- |
| ERR-1     | Upload with invalid file type (rejected by profile) | Validation boundary must be exercised                                 |


---

## Summary

| Severity | Count | Domains affected |
|---|---|---|
| 🔴 Critical | 9 | Auth, Search |
| 🟠 High | 3 | BULK-1, Signing (DS-4, DS-5) |
| 🟡 Medium | 5 | Admin, ERR-1 |
| **Total gaps** | **17** | |

**Highest-leverage next work:** AUTH-1–5 and SH-1–4 — no auth scenarios and no search scenarios means two entire system layers are unspecified against production behaviour.
