# Contract validation — 19 screens vs swagger.json

Validated the mockups' field names, enum values, and routes against the real
OpenAPI contract (`swagger.json` — OpenAPI 3.0.0, MAGIQ Media API v1, 104 paths, 160 schemas).
Date: 2026-08-12.

**Headline:** field names and routes the screens use are accurate where the contract defines
them. The gaps are things the contract **doesn't define yet** — not things the screens got wrong.

---

## ✅ Enums — match

| Screen usage | Contract enum | Verdict |
|---|---|---|
| RecordType FieldType (Text/Number/Date/Boolean/Url/Enum/MultiEnum) #11 | `FieldType` = same 7 | ✅ exact |
| ReviewPolicy "Required for publish" #12 | `ReviewPolicy` = None, RequiredForPublish | ✅ |
| CheckoutPolicy "Required for edit" #12 | `CheckoutPolicy` = None, RequiredForEdit | ✅ |
| RegistrationType Electronic #9 | `RegistrationType` = Electronic, Physical | ✅ |
| Bulk onError Continue/FailFast #17 | `BulkOnErrorMode` = ContinueOnError, FailFast | ✅ |

> **All 4 drifts below were fixed in the mockups + re-rendered (2026-08-12).**

## ⚠ Enums — drift (screen shows a subset / wrong label)

| Screen | Showed | Contract | Fix |
|---|---|---|---|
| Collection manage #16 | Private / Public toggle | `CollectionVisibility` = Private, **Unlisted**, Public | add Unlisted (3-way) |
| Bulk ops #17 | onDuplicate Skip / Reject | `BulkOnDuplicateStrategy` = Reject, Skip, **AutoSuffix** | add AutoSuffix |
| Media profiles #12 | Capabilities: Processing, Registration, Signing | `Capability` = Registration, CheckInOut, Retention, Review, Processing, Distribution, Governance, VersionControl, Signing (9) | show full set / note "+6 more" |
| Registration #9 | docs labelled Primary / Supporting | `RegistrationItemType` = ApplicationForm, SupportingEvidence, ConfirmationReceipt, Other | relabel to real item types |

## ✅ Field names — match

| Screen | Contract model | Verdict |
|---|---|---|
| Library list/grid/mobile #3/#5 — title, status, currentVersionNumber, ownerId, publishedAt, tags, conformanceStatus | `MediaItemSummaryModel` | ✅ names exact. **Extra available, unused:** `recordDate`, `author` |
| Record types #11 — fieldName, fieldType, isRequired, isSearchable, isImmutable, sourceCapability, constraints | `AddRecordTypeFieldModel` | ✅ exact (capability-contributed = `sourceCapability`; immutable = `isImmutable`) |
| Bulk #17 — {succeeded, failed, skipped}; {index, errorCode, message, suggestedName} | `BulkCreateMediaItemsResponse` + `...FailedModel` | ✅ (per-item label is `title`, not `name`) |
| CR review #7 — threaded comments | `ChangeRequestCommentSummaryModel` = id, changeRequestId, authorId, body, parentCommentId, createdAt, editedAt, isDeleted | ✅ exact |
| Upload #4 — presigned response | `InitiateAssetUploadResponse` = id, uploadUrl, expiresAt | ✅ exact |
| Registration #9 — initiate | `InitiateRegistrationRequest` = registrationAuthority, registrationType | ✅ |

## ✅ Routes — match
Item lifecycle routes all present and back the screens: `/v1/items` + `/{itemId}/` publish · approve ·
reject · withdraw · begin-revision · discard-revision · archive · folder · metadata · metadata/{fieldName}
· roles/{roleName}/assets · versions · registrations. Bulk: `/items/bulk`, `/items/bulk/metadata`.
Search: `/items/search`. Path counts: registration 14 · change-request 4 · folder 16 · collection 11 ·
profile 18 · record-type 16.

---

## 🔴 NOT backed by the contract — flag to backend

These are the real findings. The screens depict behaviour the OpenAPI doesn't (yet) define.

1. **Checkout / lock is not in the contract at all.** Zero occurrences of `checkoutStatus` / `checkedOut` /
   lock in any schema. Screens #1, #3, #5, #6 show a "Checked out" chip + row lock flags with no field to
   bind to. → Is checkout state exposed on read models? If so, under what field?

2. **MediaItem detail response body is undocumented.** `GET /v1/items/{itemId}` exists but its `200` has
   **no response schema** in the export. So everything screen #6 (detail) renders beyond the summary —
   `metadata` (current/draft), `assets` by role, `activeMediaChangeRequestId`, `activeSigningSessionId`,
   `registrationIds`, `conformanceGaps` — is **absent from the contract** (0 occurrences each). Likely the
   detail model just isn't exported. → Add the detail response schema so the richest screen can be verified.

3. **Signing has no API.** 0 signing paths, 0 signing schemas. Screen #10 (signing session) is entirely
   ahead of contract — DocumentSigning isn't in v1. Same standing as audit. (Matches the backend "aggregate
   does not yet exist" note.)

4. **Audit has no API.** 0 audit paths — confirms the ADM-4 gap. Screen #18 already flagged design-ahead-of-spec.

5. **Status values are not enum-constrained.** MediaItem / ChangeRequest / Registration status fields are
   plain `string` in the contract (only `conformanceStatus` appears, and not as an enum). → The earlier
   "status enum drift" (read-model Rejected/Withdrawn vs write-model Draft|PendingApproval|Published|Revising|
   Archived) **cannot be resolved from swagger** — the contract doesn't pin these. Screens use the write-model
   set. Backend should decide whether to publish these as OpenAPI enums.

6. **CR reviewer list not contract-backed.** No `reviewers` field in any schema; CR detail response is inline
   and minimal. Screen #7's reviewer tally (ReviewerStatus Pending/Approved/Rejected/Withdrawn) has no schema
   to bind to. → Expose reviewers on the CR detail response.

---

## What this means for design
- **No screen needs a field rename** — where the contract defines fields, the screens already use the right
  names. The 4 enum drifts (Unlisted, AutoSuffix, full Capability set, RegistrationItemType labels) are quick
  fixes to the mockups.
- **4 screens depict unmodelled behaviour** (detail body, checkout, signing, audit). Keep them — they're
  valid design intent — but they double as a **backend contract backlog**: the API needs a MediaItem detail
  schema, checkout exposure, signing endpoints, audit endpoints, and (optionally) status enums + CR reviewers.
