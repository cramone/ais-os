# magiq-media — Use Cases

_Rebuilt 2026-09-15 directly from the spec tree._

Single index of every scenario documented in the spec. **The spec is the source of truth; this file is a
map to it.** Scenario bodies live in the repo at:

```
D:\source\github\sprbrk-standard\mgq-magiq-media\docs\spec\contexts\
```

All `Source:` paths below are relative to that folder.

> **Numbering is per-aggregate, not global.** `C-3` is *Archive a collection* on `Collection` **and**
> *Publish with reviewers — all approve* on `MediaItem`. Always cite an id together with its aggregate.

---

## Actors

Actor **types** are defined in `shared/multi-tenancy-and-auth.md` § Actor Types and carried on the JWT
`actor_type` claim:

| Actor type | Description |
|---|---|
| **User** | Authenticated individual. Primary actor for all normal domain operations. |
| **System** | Internal service or automated process. May invoke privileged commands (e.g. `ForceReleaseCheckout`). |
| **Guest** | No JWT. Read-only access to public endpoints, rate-limited by source IP. |

Roles used in scenario prose — these are descriptions of a User in context, not actor types:

| Role | Where it applies |
|---|---|
| **Owner** | `resource.OwnerId == actor.Id`, set at creation. Not a JWT claim. |
| **Reviewer** | A member named on `MediaItem.ReviewSession`. Votes approve/reject. |
| **Participant** | A member on a `ChangeRequest`'s participant set. Gates commenting. |
| **Administrator** | Elevated tenant member. Guards the five MediaProfile governance routes. |
| **Officer** | Registration only — the user who initiates a filing and becomes its owner. |
| **Adapter** | Registration only — the integration adapter; a `System` actor bridging the external authority. |
| **Authority** | Registration only — the external registering body. Never touches the platform directly. |

---

## Asset Management

Source: `AssetManagement/aggregates/Asset/asset.scenarios.md` · Index: `AssetManagement/business-scenarios.md`

| ID | Scenario | Key Aggregates |
|---|---|---|
| A-1 | Upload and process a media asset | Asset |
| A-2 | Drag-and-drop upload — standalone asset before MediaItem | Asset |
| A-3 | Processing pipeline failure recovery | Asset, AssetIngestionSaga |
| AM-4 | Large file upload (multipart) | Asset, AssetIngestionSaga |
| AM-5 | Virus scan failure (asset infection detected) | Asset, AssetIngestionSaga |
| AM-6 | User-initiated asset archive | Asset |
| AM-7 | Asset hard delete | Asset |
| DL-1 | Download original asset (presigned URL) | Asset |
| DL-2 | Download asset rendition (presigned URL) | Asset |
| DL-3 | Expired download URL — access denied by S3 | Asset |

---

## Catalog — Collection

Source: `Catalog/aggregates/Collection/collection.scenarios.md`

| ID | Scenario | Key Aggregates |
|---|---|---|
| C-1 | Set up a collection structure | Collection, Folder |
| C-3 | Archive a collection | Collection, Folder, MediaItem |

---

## Catalog — Folder

Source: `Catalog/aggregates/Folder/folder.scenarios.md`

| ID | Scenario | Key Aggregates |
|---|---|---|
| FLD-1 | Archive a folder subtree | Folder, MediaItem, Registration |
| FLD-2 | Move a subtree to another collection | Folder, MediaItem, Collection |

> FLD-1 is **synchronous inside one HTTP request** — no queue, no saga, no background worker. The
> pre-flight refuses a subtree of more than 500 descendant folders with `422
> FolderSubtreeTooLargeToArchive`.

---

## Catalog — MediaItem

Source: `Catalog/aggregates/MediaItem/mediaitem.scenarios.md`

| ID | Scenario | Key Aggregates |
|---|---|---|
| C-2 | Publish with no reviewers — immediate publish | MediaItem |
| C-3 | Publish with reviewers — all approve | MediaItem |
| C-4 | Publish with reviewers — one rejects | MediaItem |
| C-5 | Cross-collection move | MediaItem, Folder |
| C-6 | Withdraw while pending approval | MediaItem |
| C-7 | Reviewer not in session tries to vote | MediaItem |
| C-8 | Reviewer votes twice | MediaItem |
| MW-1 | Withdraw a published item | MediaItem |
| MW-2 | Archive an individual item | MediaItem |
| MW-3 | First folder assignment from the unassigned pool | MediaItem, Folder |
| MW-6 | Metadata validation failure | MediaItem |
| MW-7 | Browse the unassigned pool | MediaItem |
| BULK-2 | Bulk metadata update across items | MediaItem |
| MI-1 | Version increment with asset pipeline | MediaItem, Asset |
| MI-2 | Review rejection then approval | MediaItem, Asset, ChangeRequest |
| BR-1 | Begin revision and publish a new version | MediaItem |
| BR-2 | Begin revision and discard | MediaItem |

> **Review lives on `MediaItem.ReviewSession`, not on `ChangeRequest`.** Approve/reject decisions are
> made on the MediaItem; the ChangeRequest raised by a submission is a comment thread only. This is the
> single biggest change from the pre-2026-09 model — the old `CR-1..CR-5` and `CRT-1` scenarios are gone.

---

## Catalog — MediaProfile

Source: `Catalog/aggregates/MediaProfile/mediaprofile.scenarios.md`

| ID | Scenario | Key Aggregates |
|---|---|---|
| MP-1 | Create and publish a MediaProfile | MediaProfile |
| MP-2 | Re-pin a MediaProfile to a new RecordType version | MediaProfile |
| MP-3 | Deprecate a MediaProfile | MediaProfile |

---

## Catalog — Bulk Import ⚠ intent only, not built

Indexed in `Catalog/business-scenarios.md`; **the scenario files do not exist in the tree.**

| ID | Scenario | Key Aggregates |
|---|---|---|
| BFI-1..3 | Bulk folder import | BulkFolderImportJob |
| BMI-1..3 | Bulk media import | BulkMediaImportJob |

**Removed from the spec 2026-09-16** (`MM-001` Q2). Both aggregates were fully specified with no class,
no command, no projector, no queue, no table and no route behind them; the specified inventory is now
eleven aggregates. They are re-specified when they are genuinely designed. The inline bulk *endpoints* are
a different thing and are unaffected.

---

## Change Requests

Source: `ChangeRequests/aggregates/ChangeRequest/changerequest.scenarios.md`

| ID | Scenario | Key Aggregates |
|---|---|---|
| CRC-1 | Open a governance change request, then edit under it | ChangeRequest, MediaItem |
| CRC-1b | The comment thread raised by a submission | ChangeRequest, MediaItem |
| CRC-2 | Add a comment | ChangeRequest |
| CRC-3 | Edit own comment | ChangeRequest |
| CRC-4 | Delete own comment | ChangeRequest |
| CRC-5 | Non-author cannot edit another user's comment | ChangeRequest |
| CRC-6 | Reviewer (participant) adds comment — succeeds | ChangeRequest |
| CRC-7 | Non-participant tries to add comment — 403 Forbidden | ChangeRequest |

> **Two kinds share the aggregate**, distinguished on the wire by `kind`:
> **governance** (client-created via `POST /v1/change-requests`, has a `Title`, no `ReviewSessionId`) and
> **commentThread** (system-raised from `MediaItemPublicationRequested`, no title, carries
> `ReviewSessionId`). Only a governance request may be named on a checkout.

---

## Metadata — RecordType

Source: `Metadata/aggregates/RecordType/recordtype.scenarios.md`

| ID | Scenario | Key Aggregates |
|---|---|---|
| RT-1 | Create and publish a RecordType schema | RecordType |
| RT-2 | Evolve a field (rename and retype) | RecordType |
| RT-3 | Deprecate a RecordType | RecordType |
| RT-4 | Retire a bad version and roll back | RecordType |

> **Renumbered `M-n` → `RT-n` on 2026-09-04.** `M-n` means a *finding from the 2026-08-22 Metadata
> review* everywhere else in the tree; scenarios are `RT-n`. The old `M-4` bulk-metadata scenario moved
> to Catalog as `BULK-2`.

---

## Processing

Source: `Processing/aggregates/ProcessingJob/processingjob.scenarios.md`

| ID | Scenario | Key Aggregates |
|---|---|---|
| P-1 | Full pipeline — an image on a capable profile | ProcessingJob, Asset, AssetIngestionSaga |
| P-2 | Bypass — a document with no `Processing` capability | ProcessingJob, Asset, AssetIngestionSaga |
| P-3 | Processing timeout and its compensation | ProcessingJob, Asset, AssetIngestionSaga |

> ⚠ **P-1 does not run today.** `AssetProcessingWorker.ProcessAsync` has no caller and
> `RunProcessingPipelineAsync` throws `NotImplementedException`, so every capable asset stalls at
> `Running` until the 240-minute budget expires — the full pipeline currently terminates in a timeout,
> always. P-2 (bypass) is unaffected. See `adhoc/processing-code-defects-2026-09-08.md` § PROC-1.

---

## Document Signing

Source: `DocumentSigning/aggregates/DocumentSigningSession/documentsigningsession.scenarios.md`

| ID | Scenario | Key Aggregates |
|---|---|---|
| DS-1 | Happy path — contract signed and published | DocumentSigningSession, MediaItem |
| DS-2 | Envelope voided — compensation | DocumentSigningSession, MediaItem |
| DS-3 | Session expires — compensation | DocumentSigningSession, MediaItem |

> ⚠ **Nothing in this module runs.** No aggregate class, no summary projector, the publishing middleware
> drops its events, and `SagaOrchestrator.DocumentSigning` is built every commit but deployed by nothing.
> All three scenarios are specification, not behaviour. See `adhoc/documentsigning-deferred-2026-09-08.md`.

---

## Registration

Source: `Registration/aggregates/Registration/registration.scenarios.md`

| ID | Scenario | Key Aggregates |
|---|---|---|
| R-1 | Electronic registration, full lifecycle | Registration, MediaItem |
| R-2 | Rejection and resubmission | Registration |
| R-3 | Post-confirmation document addition (amendment) | Registration |
| R-4 | Refused — the media item is not published | Registration, MediaItem |
| R-5 | Cancellation before submission | Registration |
| R-6 | Several supporting documents | Registration, MediaItem |

> ⚠ **R-2 does not survive its own cycle.** A rejected registration loses its MediaItem link permanently
> — nothing consumes `RegistrationResubmitted` or `RegistrationSubmitted`, so after one
> reject → resubmit → confirm the item carries no reference to a legally binding filing, and its
> active-registration counter is one short. See `adhoc/registration-code-defects-2026-09-08.md` § D-1.

---

## Coverage

| Context | Scenarios | Notes |
|---|---:|---|
| AssetManagement | 10 | |
| Catalog — Collection | 2 | |
| Catalog — Folder | 2 | |
| Catalog — MediaItem | 17 | |
| Catalog — MediaProfile | 3 | |
| Catalog — Bulk Import | 0 | 6 indexed, **no files exist** |
| ChangeRequests | 8 | |
| Metadata — RecordType | 4 | |
| Processing | 3 | P-1 unreachable in code |
| DocumentSigning | 3 | module unwired |
| Registration | 6 | |
| **Documented total** | **58** | |

---

# Gap Report

What the spec does not cover, and what it covers but cannot reach. Severity is about production risk,
not effort.

---

## 🔴 Critical

### The spec tree has 69 links to files that no longer exist

Verified 2026-09-15: **69 mentions across 27 files** name spec files that are absent from `docs/`:

| Referenced | Status |
|---|---|
| `shared/error-catalog.md` | **missing** — cited by every context's error section |
| `shared/authorization-matrix.md` | **missing** — the authorization contract |
| `shared/security-scenarios.md` | **missing** — Catalog's index sends authorization-rejection scenarios here |
| `shared/saga-patterns.md` | **missing** — AssetManagement's index sends saga coordination here |
| `shared/operations.md` | **missing** |
| `Catalog/aggregates/BulkFolderImportJob/…`, `…/BulkMediaImportJob/…` | **missing** — 6 indexed scenarios |

The tree is **71 spec files** (counted 2026-09-15); the 2026-09-08 reports state the truncation guard
passed on **89**. Either the deletions
were deliberate and the referring files need their links fixed, or files were lost. **Settle this before
treating the spec as complete** — every "marked in spec" pointer in the `adhoc/` reports assumes the
error catalog and the authorization matrix are there.

### Authorization and identity — no scenarios

| Gap | Why critical |
|---|---|
| AUTH-1 | Token acquisition — user login, JWT issued |
| AUTH-2 | Expired token rejected (401) |
| AUTH-3 | Insufficient permissions rejected (403) |
| AUTH-4 | Cross-tenant access denied — a compliance requirement for government customers |
| AUTH-5 | `System` actor authentication — the `actor_type` claim is not enforced on the five `[System]` Registration endpoints, including `POST /confirm` |

`shared/multi-tenancy-and-auth.md` defines the claims and actor types. **No scenario exercises any of
them.** The only permission-denial scenarios in the whole tree are CRC-5 and CRC-7, both about comment
authorship.

This is not a documentation gap alone: 86 of 132 write commands have no authorization at all, and no
Catalog command performs an ownership check at any layer.

---

## 🟠 High

### Search — endpoints exist, scenarios do not

`GET /v1/items/search` and `GET /v1/registrations/search` are both in the API spec. Neither has a
scenario.

| Gap | Use case |
|---|---|
| SH-1 | Full-text search across MediaItems |
| SH-2 | Faceted filter (status, content type, date range) |
| SH-3 | Tag-based query (multi-tag AND/OR) |
| SH-4 | Owner-scoped search |

SH-4 is the sharp one: `GET /v1/registrations?mediaItemId=` is tenant-scoped rather than owner-scoped
today, so any tenant member can enumerate every filing against any item — including other officers'
authority reference numbers.

### Read and browse paths — no scenarios

Endpoints are specified across the `*.api.md` files (`GET /v1/items`, `/v1/folders/{id}/items`,
`/v1/collections`, `/v1/collections/public`, `/v1/profiles`, `/v1/record-types`, `/v1/assets`,
`/v1/change-requests`, `/v1/signing-sessions`, version history on both items and profiles). MW-7 is the
only scenario that walks a read path.

The Processing read path is worse than unscenarioed — **it has no reader at all**: `QueryApi` does not
reference Processing, and `ListProcessingJobsForAssetIdQuery` has no handler class, while its GSI is
maintained on every job event.

### Document Signing — signer paths

| Gap | Why needed |
|---|---|
| DS-4 | Signer declines (distinct from an admin void; compensation differs from DS-2) |
| DS-5 | Multi-signer workflow — `SignerInfo.RoutingOrder` is carried on every event and read by no code, so sequential vs parallel is undecided |

### Bulk operations

| Gap | Why needed |
|---|---|
| BULK-1 | Bulk archive MediaItems — operational need; admins process batches |
| BULK-3 | Bulk delete MediaItems — the `FolderDeleteFanoutWorker` command is outstanding (ADO `Media` #35086) |
| BULK-4 | Bulk content export — scope and UI involvement undefined (see `notes.md`) |

---

## 🟡 Medium

### Admin and tenant operations — no scenarios

| Gap | Why needed |
|---|---|
| ADM-1 | Tenant provisioning — and whether the seven default profiles are seeded there or only via the operator CLI is **still unverified** |
| ADM-2 | User role assignment — blocked on whether `magiq-auth` issues roles at all |
| ADM-3 | Storage quota check / enforcement |
| ADM-4 | Audit log — query activity history |

### Retention

`RetentionSchedule` has a design-decisions file and **no scenarios**, stated in the spec itself. It will
need them when it ships.

### Error paths

| Gap | Why needed |
|---|---|
| ERR-1 | Upload with invalid file type (rejected by profile) |
| ERR-2 | A refusal a client can act on — no refusal in Processing carries an `errorCode`, and `errorCode` does not reach the wire on any read endpoint, because only the `Api` host installs `ErrorCodeResponseConfigurator` |

---

## Summary

| Severity | Count | Domains |
|---|---:|---|
| 🔴 Critical | 6 | Broken spec references, Auth (AUTH-1..5) |
| 🟠 High | 9 | Search (SH-1..4), read paths, Signing (DS-4, DS-5), Bulk (BULK-1, 3, 4) |
| 🟡 Medium | 7 | Admin (ADM-1..4), Retention, Errors (ERR-1, 2) |
| **Total** | **22** | |

**Highest-leverage next work:** resolve the missing `error-catalog.md` and `authorization-matrix.md`.
Everything in the 🔴 authorization block and ERR-2 is specified *against those two files*, and while they
are absent there is no written authorization contract to build or review against.

---

## Housekeeping

**A duplicate of this file lives at `D:\source\github\sprbrk-standard\mgq-magiq-media\docs\use-cases.md`.**
It is byte-identical to the pre-2026-09-15 version of this one and is now stale — it still lists `CR-1..CR-5`,
`CRT-1`, `M-1..M-4`, `C-9`, `C-10`, `MW-4`, `MW-8` and `BRW-1..4`, none of which exist in the spec. Decide
which copy is authoritative and delete the other. The repo copy is the one other contributors can see.
