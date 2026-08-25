# magiq-media — DDD Spec Coverage Review

**Date:** 2026-08-24
**Scope:** `D:\source\github\magiq-media\docs\spec\` — 9 architecture/shared files + 7 contexts, 12 aggregates, 68 files, ~25,300 lines.
**Question asked:** are the 14 DDD dimensions covered — ubiquitous language, bounded contexts, aggregates, entities/VOs, commands, domain events, invariants, business rules, state transitions, relationships, workflows, sagas, eventual consistency, edge cases/contradictions.
**Method:** five parallel deep reads (AssetManagement+Processing · Catalog core · MediaProfile/Bulk/Metadata · ChangeRequests/Registration/DocumentSigning · shared+architecture), then a verification pass over the systemic claims. Spec only — no code was read, so every finding is "the spec does not say", not "the code does not do".

> **Line numbers are indicative.** The systemic findings (§1) and a sample of the contradictions in §5 were verified first-hand; the rest carry the reading agent's citation and should be confirmed before someone edits on them.

---

## 0. Verdict

**All 14 dimensions are present somewhere. Coverage is not the problem — authority is.**

The per-aggregate specs are genuinely strong: full command tables with handler pre-conditions, payload-level event tables, invariant tables, status lifecycles, worked scenarios, and command→event→projection traceability. Several have been through a dated drift-review pass (S12, AM-*, C-*, M-*, CR-*, R-*, X-*) and now carry self-audit notes that are better than most production specs.

The architecture tier has not had that pass. `bounded-context.md` (2026-03-11), `domain-model.md` (2026-04-26) and `system-spec.md` (2026-06-17) still describe a system that the aggregate specs have since corrected — and they are the documents a new reader opens first. **Roughly two thirds of the contradictions below are architecture-tier docs disagreeing with a reconciled aggregate spec, not two aggregate specs disagreeing with each other.**

Three findings are systemic and worth fixing before anything else (§1). Everything after that is ordinary spec debt.

---

## 1. Systemic findings — fix these first

### 1.1 Fifteen spec files are physically truncated mid-token

Verified by trailing-byte scan. These files end mid-word or mid-table-row; content after the cut is simply gone:

| File | Ends at |
|---|---|
| `contexts/AssetManagement/aggregates/Asset/asset.api.md` | `` `BulkConfirmAssetUploa `` |
| `contexts/AssetManagement/aggregates/Asset/asset.scenarios.md` | `[Processing Context — Busines` |
| `contexts/Catalog/context-overview.md` | `## Relat` |
| `contexts/Catalog/aggregates/Collection/collection.api.md` | `` `CollectionCr `` |
| `contexts/Catalog/aggregates/Folder/folder.api.md` | `[Folder Read Mod` |
| `contexts/Catalog/aggregates/MediaItem/mediaitem.api.md` | `## Updated Command → Even` |
| `contexts/Catalog/aggregates/MediaItem/mediaitem.write-model.md` | `consuming Asse` |
| `contexts/Catalog/aggregates/MediaProfile/mediaprofile.api.md` | `.../RecordType/reco` |
| `contexts/Catalog/aggregates/MediaProfile/mediaprofile.read-model.md` | `- ` |
| `contexts/Catalog/aggregates/BulkFolderImportJob/bulkfolderimportjob.api.md` | `` `BulkFolderImportJobS `` |
| `contexts/Catalog/aggregates/BulkMediaImportJob/bulkmediaimportjob.api.md` | `` (Worker) \| `Reco `` |
| `contexts/ChangeRequests/.../mediachangerequest.api.md` | dangling `\|` on the traceability table |
| `contexts/DocumentSigning/.../documentsigningsession.api.md` | `` `SigningSessionProject `` |
| `contexts/Metadata/aggregates/RecordType/recordtype.write-model.md` | `scope key `RECORDTYPE`. Returns` |
| `contexts/Processing/.../processingjob.write-model.md` | `Mirrors current job statu` |
| `shared/system-spec.md` | `Active-passive cross-region failover (future ` |

Plus `architecture/branching-and-deployment.md` (`` `workflow_di ``). A further ~6 files merely lack a trailing newline with complete content.

The cut lands on the **Command → Event → Projection traceability table in most of the API files** — the single most load-bearing artifact in the spec, and the one a projector author reads. `system-spec.md` is worse: at ~line 1103 the Ubiquitous Language table breaks mid-cell into a duplicate OpenSearch field table, so the cross-context glossary is truncated *inside the file*, not just at the end.

This is a tooling defect, not a writing defect — something generating or copying these files is cutting at a byte budget. Worth finding before the next regeneration silently truncates a different set. `recordtype.api.md:636` already documents this class of defect as having hidden that file from grep sweeps; it was never swept for platform-wide.

### 1.2 The architecture tier is a stale second source of truth

| File | Stated last-updated | State |
|---|---|---|
| `architecture/bounded-context.md` | 2026-03-11 | Oldest. Pre-drift-review queue tables, saga tables, event catalogues, host list. |
| `architecture/domain-model.md` | 2026-04-26 | Header names `specs/media-management-domain-spec.md` as "the authoritative spec" — **that file does not exist anywhere in the repo** (also dangling from `bounded-context.md:598`). |
| `shared/system-spec.md` | 2026-06-17 | Body has 2026-08-24 corrections; tables stale against `system-architecture.md`; structurally corrupt at ~1103. |
| `architecture/system-architecture.md` | 2026-07-07 | Inline content current; header stale. |
| `architecture/service-boundaries.md` | rewritten 2026-08-24 | Current — the reference point the other four have not caught up to. |
| `shared/api-conventions.md`, `shared/media-types.md`, `shared/security-scenarios.md` | none | No header date at all. |
| 6 of 7 `contexts/*/context-overview.md` | none | No way to tell which side of the drift review they sit on. |

`service-boundaries.md` explicitly repudiates claims the other three still make ("there is no `IdentityAcl` type", "there is no `MediaItemReviewSaga`", "no configurable fail-open flag … was never built"). Until the older three are either rewritten or demoted, the spec has two answers to most architecture questions and a reader has no way to know which wins.

**Recommendation:** add a `_Last reviewed:_` line to every spec file, and either rewrite `bounded-context.md` / `domain-model.md` / `system-spec.md` against `service-boundaries.md`, or put a banner at the top of each pointing to the aggregate specs as authoritative for anything they disagree on. The banner is a day's work and removes most of §5.

### 1.3 Two artifacts are missing outright, one is an unmerged changelog

- **`contexts/Catalog/aggregates/Folder/folder.scenarios.md` does not exist.** Every other aggregate except the Bulk jobs has one. Folder's two highest-risk behaviours — the archive cascade and a cross-collection subtree move — therefore have no worked example anywhere, and `Catalog/business-scenarios.md` lists no Folder-owned scenario to notice the hole.
- **Neither Bulk import job has a scenarios file.** `BulkMediaImportWorker` is a five-phase process manager spanning Asset, MediaItem and Processing, spec'd with no compensation, no timeout and no dedup rule.
- **`contexts/Catalog/aggregates/BULK-IMPORT-SPEC-UPDATES.md` is an unmerged changelog living in `aggregates/`**, written in imperative future tense ("Add two new Lambda services", "Changes needed to existing spec files"). Most of it has landed elsewhere and it is now drifting from its own targets (it prescribes `/v1/catalog/...` routes; every shipped file uses `/v1/...`). But its `BulkCreateMediaItemsCommand` contract and SQS/DLQ configuration exist nowhere else, so it cannot just be deleted — merge those two sections out, then remove the file.

---

## 2. Coverage matrix

Global rating per dimension. "Aggregate tier" = the per-aggregate write/read/api/scenario files; "Architecture tier" = `architecture/` + `shared/`.

| # | Dimension | Aggregate tier | Architecture tier | Net |
|---|---|---|---|---|
| 1 | Ubiquitous language | Partial | **Partial — no canonical glossary** | ⚠️ |
| 2 | Bounded contexts | Covered | Partial — internal contexts unmapped | ⚠️ |
| 3 | Aggregates | Covered | Partial — 3 competing inventories | ⚠️ |
| 4 | Entities & value objects | Partial | Partial — entity-vs-VO never stated | ⚠️ |
| 5 | Commands | Covered | **Missing — no global inventory or authz matrix** | ⚠️ |
| 6 | Domain events | Covered | Partial — 2 naming schemes, catalogue incomplete | ⚠️ |
| 7 | Invariants | Covered | Partial — no cross-aggregate catalogue | ⚠️ |
| 8 | Business rules | Covered | **Missing — no rules catalogue** | ⚠️ |
| 9 | State transitions | Covered | Partial — no consolidated reference | ⚠️ |
| 10 | Relationships | Covered | Partial — cascade rules stated once, inconsistently | ⚠️ |
| 11 | Workflows | Partial — no Folder, no Bulk scenarios | Partial — no publish or registration workflow | ⚠️ |
| 12 | Sagas / process managers | **Missing** — only `AssetIngestionSaga` is real, and it has no owning file | Partial | 🔴 |
| 13 | Eventual consistency | Partial | Partial — no read-your-writes policy, no lag SLO | ⚠️ |
| 14 | Edge cases & contradictions | Partial | **Missing** | 🔴 |

**Strongest dimensions:** commands, domain events, invariants and state transitions *at the aggregate tier*. Event versioning/upcasting, the domain-vs-integration distinction, projector idempotency and the two-tier uniqueness check are all properly specified in `system-spec.md` and are genuinely good.

**Weakest:** sagas (§3) and cross-cutting catalogues (§4).

---

## 3. Sagas — the one dimension that is genuinely missing

This is the largest real gap, distinct from the staleness problem.

**`AssetIngestionSaga` — the only saga that actually runs — has no owning spec file.** It is described in three places with three different state sets (`AwaitingValidation`, `ProcessingDispatched`, `Complete`, `Failed`), no state table, no transition table. Its timeouts are given as "Video = 4h, others shorter" — the actual per-content-type values are undefined. And nothing specifies its behaviour on the **bypass branch**, which never emits `ProcessingJobSucceeded` or `Failed` — the only two closure triggers listed — so a fast-exit asset's saga has no stated exit.

**`MediaItemReviewSaga` is specified four mutually exclusive ways.** Verified:

- `bounded-context.md:624` — live, with SQS subscriptions and a full happy path.
- `domain-model.md:317-319` — "saga-driven", then "designed but not yet implemented".
- `system-architecture.md:293,322,337` — deferred, with a 14-day timeout whose scanner does not exist ("stale review sagas must be manually identified and resolved").
- `service-boundaries.md:186` — "**There is no `MediaItemReviewSaga` and no `MediaItemCheckoutReviewSaga` type**".
- `ChangeRequests/context-overview.md:8-10` (rewritten 2026-08-23) — the saga and its resolution events "were all fiction"; **the direction is inverted**: Catalog emits `MediaItemApprovedIntegrationEvent`, and ChangeRequests' own handler dispatches `ResolveChangeRequestCommand` against its own aggregate. No saga required.

`system-spec.md:885` still specifies the saga over `ChangeRequestApproved`/`ChangeRequestRejected` — **events the current ChangeRequests write model does not have** (it has `ChangeRequestResolved`/`Abandoned`). `api-conventions.md:485` and `mediaitem.api.md:474` both independently record that the saga never existed. The ChangeRequests version is the reconciled one; the other four should be deleted or rewritten to match.

**`DocumentSigningSaga`** is narrated in scenarios with no state list, no correlation key (`SigningSessionId` vs `MediaItemId` vs `EnvelopeId` — never stated), no idempotency rule, no compensation-failure path, and a timeout quoted three ways ("configurable, e.g. 72 hours" / "72 vs 4 hours") with no config key.

**Missing for every saga:** correlation-id scheme, retry budget, DLQ/poison-message policy, manual-intervention runbook. Also undefined: what closes the two real process managers that aren't called sagas — `CollectionArchiveFanOutWorker` and `IFolderArchiveFanOutWorker` have no failure, retry, partial-completion or resume spec at all, so a half-archived subtree has no compensation and no status surface.

---

## 4. Cross-cutting gaps by dimension

**Ubiquitous language.** No single canonical glossary — two cross-cutting tables (`domain-model.md`, `system-spec.md`, the latter truncated mid-table) plus six per-context ones, which disagree. Systematically missing: every term added by the 2026-08 corrections — `EditSession`, `ReviewSession`, `OriginStatus`, `ConformanceGap`, `Alias`, `CompiledMetadataTemplate`, `SuppressedFieldNames`, `AllowsConcurrentEdit`, `VersionArtifact`, `tier-policy`, saga state names, and `Job`/`Batch`/`Phase`/`Chunk` for bulk. The `Capability` enum — the pivot of the whole activation chain — is named in two glossaries and specified nowhere; `domain-model.md` points at "the domain spec", which does not exist.

**Bounded contexts.** `bounded-context.md` names relationship patterns (ACL, Published Language) for the 5 **external** contexts only. The 7 internal contexts appear only in `system-spec.md §Internal Context Dependencies` with no relationship type — no shared-kernel, conformist or partnership designation anywhere.

**Aggregates.** Three inventories: 9 (`bounded-context.md`), 10 (`domain-model.md`, adds `ProcessingJob`), 12 (per-context overviews, add both Bulk jobs). No "one aggregate per transaction" rule is stated anywhere — and the one genuine multi-write transaction (event + name reservation) is described but never justified as the exception.

**Entities & VOs.** Entity-vs-VO distinction never stated. `Reviewer`, `ReviewComment`, `RegistrationItem`, `RegistrationAmendment` and `Signer` all have identity and mutable state but are catalogued as value objects. Folder has no VO section at all despite using `MetadataChangeset`, `Attributor`, `FolderName`, `Originator`.

**Commands.** No global inventory — `service-boundaries.md` explicitly deleted the ~35-row table and delegated to the aggregate specs, which is defensible. But the **authorization matrix went with it**: `system-spec.md §Command-Level Authorization` covers 6 of ~150 commands, and `ForceReleaseCheckout`, `ExpireCheckout`, `BulkCreateMediaItems` and every Processing/Bulk command are unlisted. For a compliance-grade government platform that is the gap I'd close first after §1.

**Domain events.** The domain catalogue in `bounded-context.md` omits `ProcessingJob` and both Bulk aggregates entirely. Two competing integration-event naming schemes are in live use — `media.mediaitem.*` (16 occurrences) and `media.item.*` (12) — and **external SNS filter policies cannot be written against both**. Integration-event versioning is undefined: the envelope carries `schemaVersion: 1` but the upcaster policy is explicitly scoped to domain events only.

**Invariants & business rules.** No cross-aggregate invariant catalogue (e.g. "a Registration's MediaItem must be Published", "a Folder cannot be archived with active registrations in subtree"); hierarchy invariants live in `adrs/catalog-domain-invariants.md`, outside the spec tree. No business-rules catalogue distinct from invariants exists at any level.

**Relationships & cascade.** Reference-by-id is implied everywhere and stated as a rule nowhere. Cascade is stated once and inconsistently — `domain-model.md`: "Archiving is read-layer only — no write-side cascade" vs `bounded-context.md`'s `CollectionArchiveFanOutJob`, which archives the whole subtree. Nothing defines what happens to Assets when a MediaItem is archived, to Registrations when a Folder is archived, or to MediaItems when a MediaProfile is deprecated.

**Eventual consistency.** Duplicate delivery, out-of-order, dual-write risk and two-tier uniqueness are all covered well. Missing: any read-your-own-writes policy, any projection-lag bound or SLO (`api-conventions.md` alludes to "a client that reads a lagging projection" with no figure), and any rebuild procedure for the reference indexes `service-boundaries.md:133` says "cannot be rebuilt by aggregate replay".

**Edge cases.** The highest-value one: **MediaItem has three orthogonal state machines — status × edit-session/checkout × folder-assignment — each specified alone, and their interaction is defined nowhere.** Undefined as a result: does `Archive` close an open `EditSession`? Does `MediaItemApproved` (the `EditSessionCloseReason.Submitted` value exists but no method raises it)? Can a non-editor `Publish`/`Archive`/`Withdraw` an item another user holds? Can you `Withdraw` or `Archive` from `Revising` (the diagram shows the arrow; the methods don't list the state)? A status × session × assignment matrix in `mediaitem.write-model.md` would close a dozen open questions at once.

---

## 5. Contradiction register

~60 were found. Grouped by cost, highest first. Full per-slice detail with line citations is in the working notes; the ones below are the ones that change what someone builds.

### Tier 1 — a developer would build the wrong thing

| # | Contradiction | Sides |
|---|---|---|
| T1 | **Integration event naming** — `media.mediaitem.*` vs `media.item.*` | `bounded-context.md:441` / `service-boundaries.md:236` vs `system-spec.md:620` |
| T2 | **Review saga** — live / deferred / never existed / inverted direction | see §3 |
| T3 | **Standalone asset processing & quota** — full pipeline vs fast-exit-unprocessed; charged at upload vs deferred to assign | `bounded-context.md:516`, `service-boundaries.md:161` vs `domain-model.md:208`, `system-architecture.md:192`, `asset.write-model.md:317`. Also self-contradictory *within* AssetManagement: `asset.write-model.md:317` "quota NOT charged" vs `asset.scenarios.md:179` "quota check still applies". The S12 rule (fast-exit, deferred charge) is the reconciled one. |
| T4 | **Infected object: delete or quarantine** | `asset.write-model.md:248` "handler **must** hard-delete the S3 object" vs `asset.scenarios.md:393` "moved to `media-quarantine` (**not deleted**) for forensic review". Compliance-relevant. |
| T5 | **Upload confirmation trigger** — S3 `ObjectCreated` → SQS → auto-confirm vs client POST after its own PUT | `system-spec.md:823`, `bounded-context.md:488` vs `service-boundaries.md:81` ("was never built"). Confirmation is also declared **non-idempotent** while every other pipeline command is idempotent — which only matters under the S3-event reading. |
| T6 | **Capability enum** — API allows `Processing, VersionControl, Registration, DigitalSigning`; write model defines 9 values with `Signing`; defaults seed `Review`/`CheckInOut`, both rejected by the API list | `mediaprofile.api.md:294` vs `mediaprofile.write-model.md` vs `mediaprofile.defaults.md:139`. Compounded by DocumentSigning using `DigitalSigning` and `Signing` in one file. |
| T7 | **DynamoDB key shapes** — ~10 rows diverge between the two "authoritative" tables (`media-item-versions`, `media-folder-children`, `media-asset`, `media-collection`, `media-folder`, `media-item`, `media-registration`, `media-record-type`, `media-change-request`, `media-processing-job`) | `system-spec.md:670-701` vs `system-architecture.md:438-441`. `system-spec.md` claims the two "are kept in step". |
| T8 | **Read-model table names** — `media-*-detail` vs `media-*` | `bounded-context.md:171` and `system-spec.md:990` vs `system-architecture.md:122` and `system-spec.md:674` (self-contradictory) |
| T9 | **Role field naming across the write/read seam** — clients write `AcceptedContentTypes`, read `AllowedMediaCategories` | `mediaprofile.write-model.md` vs `mediaprofile.read-model.md` |
| T10 | **Asset status on role assignment** — "no asset status constraint, any status" vs "asset must be `Active`" (blocking) | `mediaitem.api.md:377` vs `mediaitem.write-model.md:414` |
| T11 | **Ownership scoping on MediaProfile** — owner-scoped list + `caller.owner_id` check vs "`ListMediaProfilesByOwnerQuery` does not exist and never did … **every profile in the tenant is returned to every caller**" | `mediaprofile.api.md:41` vs `mediaprofile.read-model.md:223`. Security-relevant. |
| T12 | **DocumentSigning webhook tenant lookup** — dedicated `media-signing-envelope-lookup` table vs `media-signing-sessions[EnvelopeId]`, which the read model rules out as "eventually consistent and unsuitable for a security decision" | `DocumentSigning/context-overview.md:85` vs `documentsigningsession.write-model.md:238` |
| T13 | **Approve authorization — three-way** — reviewer-scoped vs System-only vs `ReviewSession` roster | `system-spec.md:147` vs `security-scenarios.md:123` vs `error-catalog.md:297` |
| T14 | **Billing failure mode** — "configurable, default fail-closed" vs "no configurable flag exists … was never built" | `bounded-context.md:101` vs `service-boundaries.md:233` |

### Tier 2 — wrong client contract

Status codes (publish `200` vs `202`; deprecate `204` vs `202` on both RecordType and MediaProfile; folder name collision `409` vs `422`; DS cancel `409` vs the platform's `422` ruling), route spellings (three for the DS webhook; `/media-items/` vs `/v1/items/`; `/v1/catalog/...` vs `/v1/...`), part-URL TTL (15 min vs 1 hour), bulk batch caps (50 vs 100 vs 200), download authorization (owner-scoped vs any tenant member), delete semantics (soft status flip vs hard record removal), and **idempotency** — every API file documents an `IdempotencyKey` convention that `collection.write-model.md:44` and `bulk-operations.md:154` both say "is not implemented … nothing implements it".

### Tier 3 — internally inconsistent within one file

`MediaItemStatus` membership (`Withdrawn` vs `Revising` vs `UnderReview`, three variants); checkout model (`CheckoutStatus`/`CheckedOutBy` in `domain-model.md` vs `EditSession` + collaborators + leases in `error-catalog.md`); `ITenanted` vs `ITenantScoped`; host inventory (8 vs 9 vs 12); projector count (13 vs 24 vs 37 vs 10); bucket list (3 vs 2); `FailureCategory` wire values that would throw on `Enum.Parse`; ChangeRequest event names (`MediaChangeRequest*` vs `ChangeRequest*`); Registration expiry ("exists nowhere / no expiry concept" vs a field and an event in `domain-model.md`); registration types (`Electronic|Physical` vs `Copyright` + a `jurisdiction` field appearing nowhere else); and several read-model files declaring a field "does not exist" and then projecting it in the same file (`ActiveMediaChangeRequestId`, folder metadata attribution, `EventId`).

---

## 6. Recommended order

1. **Find and fix the truncation** (§1.1), then regenerate the 15 files. Everything else is edits on top of files that may be re-cut.
2. **Banner or rewrite the three stale architecture docs** (§1.2). Cheapest single action; removes most of §5 Tier 1 and Tier 3.
3. **Resolve T1 (event naming) and T7/T8 (key shapes / table names)** — these are the contradictions that produce silently wrong infrastructure rather than a failed build.
4. **Write the saga specs** (§3): one file per saga with state table, transition table, correlation key, timeout values + config keys, compensation, idempotency, DLQ. Start with `AssetIngestionSaga` — it's the one in production.
5. **Rebuild the authorization matrix** for all ~150 commands (§4, Commands).
6. **Add the MediaItem status × session × assignment matrix** (§4, Edge cases).
7. Backfill the missing artifacts: `folder.scenarios.md`, bulk scenarios, merge-and-delete `BULK-IMPORT-SPEC-UPDATES.md`.
8. One canonical glossary; delete the competing tables and link to it.
9. Cross-aggregate invariant + cascade catalogue; read-your-own-writes / projection-lag policy.

Items 1–3 are days. Items 4–6 are where the domain risk actually is.

---

## 7. Note for the docs project

`MEMORY.md` still says *"'The spec' refers to the most recent files in `projects/magiq-media/spec/`"*. Spec moved to `D:\source\github\magiq-media\docs\spec\` on 2026-07-07. Flagging rather than editing — memory is user-triggered.
