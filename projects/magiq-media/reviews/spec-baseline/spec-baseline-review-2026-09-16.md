---
id: MM-001
type: review
project: magiq-media
workstream: spec-baseline
raised-by: []
status: draft
outcome: pending
todo-id: 8f9d3a14-4198-5e7e-a02c-e8ed12d23a12
created: 2026-09-16
---

# Spec Baseline — contradictions, gaps and the missing domain-model record

## Scope

**Read:** every file under `D:\source\github\sprbrk-standard\mgq-magiq-media\docs\` — 103 markdown files across
`spec/` (89) and `adrs/` (10), plus both `README.md`.

**Not read:** application code, CDK, tests. Every finding below is a statement about the documents, and
where two documents disagree this review says so without ruling on which is right — the code is not
evidence here and was not consulted.

**Why now.** Two sweeps landed on 2026-09-16 immediately before this review:

1. **Citations removed** — 430 off-repo ids (`X-*`, `CR-6+`, `AM-8+`, `D-*`, `MM-*`, `W29`, `SPEC-19`, …)
   across 63 files, plus every "in the drift review" phrase. `breaking-changes.md` was deleted.
2. **Build status removed** — implementation and deployment state across 76 files, per the rule now written
   into the repo `CLAUDE.md` § *Spec files state the specified system*.

Both sweeps were mechanical about *what* they removed and careful never to invent design. The consequence is
this review: **a large amount of the spec's apparent coherence was being supplied by correction notes,
drift-review citations and build-status caveats.** With those gone, the underlying contradictions and silences
are visible for the first time. That is the intended outcome, not a regression — but it is a backlog, and this
document is it.

**A note on what "gap" means here.** A finding marked *gap* is not a claim that behaviour is wrong. It is a
claim that **the spec does not say**, and that until it does, two engineers reading the same file will build
different things.

---

## Findings

Severity is `Critical | High | Medium | Low`. `Critical` is reserved for a defect that is live and exploitable
by a real caller, or that destroys data which cannot be reconstructed.

### A — Authorization is largely unspecified

The authorization matrix previously answered two different questions at once: *who may run this command* and
*what does the code currently check*. The second was an audit and has been removed. What remains shows that
for most commands the spec never answered the first.

A dash in an Authorization cell now means **the spec does not state who may execute the command** — explicitly
not "any authenticated tenant member may".

> **The shape of the answer is settled — see Open Question 1, Answered.** A Graph-style scope vocabulary
> (`Resource.Verb[.All]`) is declared once in `shared/api-permissions.md`; the endpoint → scope mapping is
> declared per route and per query in each `<agg>.api.md`; `shared/authorization-matrix.md` is retired as a
> source of truth. **Scopes do not replace resource checks** — every finding below still needs both a scope
> and, where the resource is owner- or membership-scoped, a stated resource predicate. That ruling changes
> the *form* of SB-1…SB-5 but closes none of them.

| Id | Severity | Finding | Evidence |
|---|---|---|---|
| SB-1 | **Critical** | **Registration decision commands have no specified authorization.** `ConfirmRegistration`, `RejectRegistration`, `ApproveAmendment`, `RejectAmendment`, `RecordRegistrationSubmission`. These finalise, terminate and amend statutory filings for government agencies — the highest-value operations in the platform. | `shared/authorization-matrix.md` § Privileged commands, rows 76–79 |
| SB-2 | High | **All 16 Metadata commands have no Authorization column at all** — tenant-wide schema mutation affecting every existing record. | `shared/authorization-matrix.md` § Metadata |
| SB-3 | High | **Catalog is unspecified across four aggregates** — MediaItems (12 incl. `PurgeMediaItemVersion`, `WithdrawMediaItem`, `DeleteMediaItem`), MediaProfiles (13 outside the five governance setters), Collections (8), Folders (11). Collections and Folders have no Authorization column. | `shared/authorization-matrix.md` §§ Catalog |
| SB-4 | High | **AssetManagement creation commands unspecified** — `InitiateAssetUpload`, `InitiateAssetMultipartUpload`, `BulkInitiateAssetUpload`. | `shared/authorization-matrix.md` § AssetManagement |
| SB-5 | Medium | **~20 pipeline-internal commands have no stated rule.** Not HTTP-reachable, which is a deployment property, not a specification. | `shared/authorization-matrix.md`, Processing + saga rows |
| SB-6 | High | **`folder.api.md` contradicts itself in 13 lines.** Write endpoints are specified as `caller.owner_id == folder.OwnerId`; thirteen lines later, *"`OwnerId` on a folder is provenance, not control. It is denormalised from the `Collection`."* | `folder.api.md:72` vs `:85` |
| SB-7 | High | **Five Registration endpoints specify `actor_type = "System"` with no stated enforcement point.** The spec gives the requirement and never says which layer applies it. | `registration.api.md` § Authorization |
| SB-8 | High | **Reviewer authorization names a field that does not exist.** *"Reviewer commands: `context.Actor.Id ∈ ChangeRequest.Reviewers[].ReviewerId`"*. `ChangeRequest` has no `Reviewers` member; approval is an invariant on `MediaItem.ReviewSession`. | `architecture/system-architecture.md:742`; cf. repo `CLAUDE.md` § Auth |
| SB-68 | High | **No query is covered by any authorization statement.** The matrix is scoped to *"every write command"* — 132 rows, zero queries. Under the ruling in Open Question 1 a `.Read` scope is required on every read route, so the mapping has to be extended to the read side of all ten aggregates, which no current document covers. | `shared/authorization-matrix.md:1`, `:8`, `:11` |
| SB-69 | Medium | **Existing per-route Authorization tables state resource predicates, not permissions, and disagree in form.** All ten `<agg>.api.md` files already carry an `## Authorization` section — e.g. `collection.api.md:57–59` gives `caller.owner_id == collection.OwnerId`, "Owner, or collection is `Public`", "Authenticated caller; results are tenant-scoped". These are the resource-predicate half and stay, but each needs a scope column adding and a consistent shape across the ten. | `collection.api.md:53–59`, and the nine siblings |
| SB-70 | Medium | **`Read` / `ReadWrite` is too coarse for regulated records.** `UpdateMediaItem` and `PurgeMediaItemVersion` cannot carry the same scope, nor can `AttachRecordType` and `PublishRecordType`. The privilege tier that § Privileged commands already identifies — governance and destructive operations — has no expression in a two-verb vocabulary. | `shared/authorization-matrix.md` § Privileged commands |

### B — The domain model, its aggregates and their relationships

This is the cluster Chase asked to be got right, and it is where the spec contradicts itself most often.

| Id | Severity | Finding | Evidence |
|---|---|---|---|
| SB-9 | High | **`owner_system` both exists and does not.** `MediaProfile` is specified as *"Owner-scoped. Use `OwnerId = "owner_system"` for platform-level profiles"*, while two other places in the same file and one in `bounded-contexts.md` state there is no such sentinel and no owner-scoping. | `domain-model.md:219` vs `:158`, `:184`, `bounded-contexts.md:144` |
| SB-10 | High | **Registration both has and has not an expiry.** *"A Registration has no expiry. No event carries an `ExpiresAt`…"* sits 17 lines above `RegistrationExpiryRecorded` in the key-domain-events list. | `domain-model.md:444` vs `:461` |
| SB-11 | High | **`IdentityAcl` is named as the actor resolver in four places**, while the `Api` host section specifies resolution through `IExecutionContext`. One of the two is the design. | `bounded-contexts.md:94`, `:143`, `:331`, `domain-model.md:598` |
| SB-12 | High | **`DocumentSigningSession` is gated on an owner it does not have.** Cancel and both read routes are specified as *"Caller owns the session"*; the aggregate, its creation event and both read models carry no owner. `InitiatedBy` exists and was explicitly not the owner, because a delegate may initiate on an owner's behalf. **Carries a design decision** — what identifies the owner — taken in phase 6, not as a precondition. | `documentsigningsession.api.md:60–61`; write-model § Properties |
| SB-13 | Medium | **Three aggregates have no `AggregateType` discriminator.** `BulkFolderImportJob`, `BulkMediaImportJob` and `RetentionSchedule` carry `—` in the inventory. The discriminator is the event-stream identity; it is a design decision, not an implementation detail. | `domain-model.md:35`, `:36`, `:46` |
| SB-14 | Medium | **`RegistrationAmendment` and `Signer` are unclassified.** Both carry full shapes in § Value Objects but appear in no entity/value-object classification. | `domain-model.md` § Entity/VO table |
| SB-15 | Medium | **`MediaChangeRequest` survives as a type name in at least four spec files** and in every `mediachangerequest.*.md` filename. The type is `ChangeRequest`; `[AggregateType("media.changerequest")]` is the authority for the event segment. | `domain-model.md`, `system-architecture.md`, `mediaitem.api.md`, `mediaitem.read-model.md` |
| SB-16 | Medium | **`Media.Api` survives as a host name in three shared files.** No such project has ever existed; the write host is `Api`. | `concurrency-and-consistency.md:47`, `multi-tenancy-and-auth.md:76`, `security-scenarios.md:24` |
| SB-17 | Medium | **`ChangeRequest` is specified as both stateless and stateful.** § Design Notes: *"No lifecycle, no reviewers … a pure comment thread"*; § Status transitions in the same file defines `Open | Resolved | Abandoned`. | `mediachangerequest.write-model.md` |
| SB-18 | Low | **The `Capability` set is stated as nine members and enumerated nowhere.** The API's four-value list is described as contested. | `glossary.md:36`, `mediaprofile.write-model.md:177` |

### C — Cross-file contradictions

| Id | Severity | Finding | Evidence |
|---|---|---|---|
| SB-19 | **Critical** | **Two incompatible designs for an infected upload.** AssetManagement specifies the infected original is **hard-deleted** from `media-originals`; Processing specifies it is **moved to `media-quarantine`**. This is a compliance-relevant evidence-handling path for a government records platform, and the spec states both. | `asset.scenarios.md:386`, `:417` vs `Processing/context-overview.md` §§ S3 Paths, External Dependencies |
| SB-20 | High | **Idempotency is specified two ways.** Bulk: *"A replayed key with the same payload returns the cached envelope without re-processing."* Conventions: the middleware rejects the duplicate with `409` and an empty body, and never replays. | `bulk-operations.md:155` vs `api-conventions.md` § What it actually does |
| SB-21 | High | **Cross-region DR is both a target and out of scope.** The RTO/RPO table specifies cross-region RTO < 4 h via active-passive failover; the runbook states there is no cross-region strategy in this design. | `operations.md:229` vs § runbook |
| SB-22 | Medium | **The error catalog claims to be exhaustive and is not.** *"Every error code produced by any endpoint in the platform is listed here."* Read-side behaviour is no longer stated, and MediaProfile draft refusals are specified as uncoded `422 InvalidOperation` with no rows. | `error-catalog.md:7` |
| SB-23 | Medium | **Download guard status sets disagree.** `asset.api.md` allows `{Active, Archived, VersionArtifact}`; DL-1/DL-2 allow `{Active, Archived}`. | `asset.api.md` vs `asset.scenarios.md` DL-1/DL-2 |
| SB-24 | Medium | **Read endpoints declare a `403` the read path cannot produce.** Four route definitions list *"`403` — caller does not own this asset"*, contradicting § *Read access is tenant-scoped, not owner-scoped* in the same file. | `asset.api.md:407`, `:439`, `:475`, `:561` |
| SB-25 | Medium | **`AssetId` generation is specified two ways** — caller-generated for idempotent initiation (write model) vs server-generated on `POST /v1/assets/uploads` and caller-generated only on the bulk path (api). | `asset.write-model.md` § Properties vs `asset.api.md` |
| SB-26 | Medium | **`POST /folders/{id}/close` takes no body and requires one.** The API states *"Request: none"*; the write model and error catalog require `closedDate` with `400 ClosedDateRequired`. | `folder.api.md` § close vs `folder.write-model.md`, `error-catalog.md:188` |
| SB-27 | Medium | **A `DEPRECATED` sentinel partition is both specified and ruled out.** `media-catalog-record-type-index` documents sentinel rows; cross-aggregate rule 11 states no projector writes one. | `event-store-and-messaging.md` vs `cross-aggregate-invariants.md` rule 11 |
| SB-28 | Low | **`202` usage needs reconciling.** Bulk specifies partial success is `200`, not `202`, while async bulk import initiate returns `202`; conventions reserve `202` for two named endpoints. | `bulk-operations.md:36` vs `api-conventions.md` § Async Operations |
| SB-29 | Low | **`media-used-jtis` exists in one document and not the other.** The repo `CLAUDE.md` specifies a replay-detection table with reject-if-exists; the spec states token validation is stateless with no JTI store. | repo `CLAUDE.md` § Auth vs `event-store-and-messaging.md` |

### D — Gaps the sweeps exposed

Each of these is a behaviour the spec now describes incompletely, because the only sentence covering it was a
build-status claim. Grouped by context; all Medium unless noted.

**DocumentSigning** — SB-30 no queue, topic, filter policy, visibility timeout or DLQ is specified for the
signing saga, though the happy-path diagram shows SQS · SB-31 the signing budget names a config section and key
with no value, default or range · SB-32 the saga releases a checkout via `ForceReleaseCheckout(MemberId)` with
no specified acting identity · SB-33 no lag class or projection is specified for signing-session read models ·
SB-34 webhook deduplication is assigned to the adapter with no specified mechanism · SB-36 `CancelSigningSession`
takes `CancelledBy` and `SigningSessionCancelled` carries no actor · SB-37 the four signing identifiers are
specified as wrapping `string`, against the platform's `Id<T>`/UUID v7 convention, and Catalog's own
`SigningSessionId` is a different type · SB-48 nothing states what drives `LinkSigningSession` /
`UnlinkSigningSession`.

**SB-31 and SB-35 carry a design decision** — whether signers act in sequence or in parallel. It determines
what a signing timeout measures and what `RoutingOrder` means, and it is taken in phase 6 alongside SB-12,
not as a precondition to starting.

**Processing / AssetManagement** — SB-38 the quarantine move (SB-19 notwithstanding) names no performing
component and no pipeline step · SB-39 neither projector lists `ProcessingJobBypassed`, so a bypassed job's read
state is unspecified · SB-40 `ListProcessingJobsForAssetIdQuery` has no named handler · SB-41 no
aggregate-specific rebuild or replay path for `ProcessingJob` read models · SB-58 no retention or lifecycle rule
on `media-renditions` for objects cleanup misses.

**Catalog** — SB-43 **High** MediaItem publish specifies no minimum reviewer count and no reviewer
de-duplication; `ReviewerIsInitiator` survives only in `security-scenarios.md` · SB-44 `PUT /metadata` null
semantics (clear vs skip) unstated · SB-45 `DELETE /roles/{roleName}/assets/{assetId}` response code unresolved
(`200` + body vs `204`) · SB-46 the Catalog context overview omits both bulk-import aggregates entirely ·
SB-47 the `media-cross-module-events` filter allowlist scope is stated nowhere, though two relationships depend
on `media.recordtype.*` arriving · SB-49 whether any command sets a non-null `MediaAssetReference.Order` ·
SB-50 the asset-definition auto-default rule and its `"All Media"`/`"original"` special case · SB-51 no lag
class for the OpenSearch-backed MediaItem queries.

**Metadata / Registration** — SB-42 what `GET …/history` returns for a record type whose events predate the
history projector, and whether a backfill is specified · SB-52 **High** Registration retention states 10-year /
3-year periods and erasure tombstoning with no specified actor, trigger evaluation or process · SB-53 read
endpoints are specified as carrying no `errorCode`, which contradicts `api-conventions.md` · SB-59 the permitted
`WithMetadata` extension member set is unspecified · SB-60 the name-reservation probe assumes an
`aspnetcore-platform` registration point that no document specifies.

**Platform / operations** — SB-54 the `deploySearch` activation condition for `Projectors.Search` now exists
only inside fenced diagrams · SB-55 the staging promote mechanism is unspecified · SB-56 the prod gate defers
entirely to the authorization matrix, so nothing states which commands require guarding or what "guarded" means
· SB-57 backup and restore verification is entirely unspecified — no cadence, owner or procedure.

### E — ADRs

Chase's explicit ask: the domain model, the aggregates and their relationships should have a decision record,
and the ADR tree should be cleaned to the same standard as the spec.

| Id | Severity | Finding | Evidence |
|---|---|---|---|
| SB-61 | High | **There is no ADR for the domain model.** Ten ADRs cover storage, eventing, auth, HTTP conventions, editing lifecycle, metadata composition, catalog invariants, naming and ownership. **None records why the aggregate set is what it is, where the boundaries fall, or why the relationships between them are shaped as they are.** That reasoning lived in review documents which no longer exist — so every contradiction in group B is currently un-adjudicable from the repo alone. **Scope now also covers the permission model** — see below. | `adrs/` — 10 files |
| SB-62 | Medium | **ADRs carry the history and status residue the spec rule now forbids** — 5 "Corrected <date>", 6 "Decided <date>", 12 "superseded", 1 revision note, 8 build-status phrases, one `(Chase)` attribution, across all 10 files. An ADR legitimately records a decision and its rationale; it should not narrate its own editing. | `adrs/*.md` |
| SB-63 | Low | **ADR identity is index-only.** Ids `ADR-001`…`ADR-014` are referenced, ten topic files exist, and no file name carries an id — the `README.md` index is the sole resolution path and is load-bearing. | `adrs/README.md` |

**What the domain-model ADR has to record** (SB-61). Four bodies of reasoning, none of which currently exists
in the repo, and each of which is a decision rather than a specification:

1. **The aggregate set and its boundaries** — why these aggregates, why the consistency boundary falls where
   it does, and why `ReviewSession` and `EditSession` are embedded value objects rather than aggregates of
   their own. This is what makes group B adjudicable.
2. **The relationships between them** — which references are by id, which by value (`MediaProfile` pins a
   `RecordType` and a `RetentionSchedule` by value), which cross a context boundary, and why cross-module
   reads go through projected reference indexes rather than direct queries.
3. **The permission model** — the `Resource.Verb[.All]` grammar, why three verbs, what `.All` means, and the
   layering rule: **a scope is checked at the edge and never replaces the resource predicate checked at the
   aggregate.** The retired matrix's § Privileged commands analysis moves here, as the justification for
   which operations earn the `Manage` tier.
4. **What is deliberately not modelled** — no reserved owner sentinel, no review saga, no expiry on
   Registration, no capability concept on `RecordType`. Group B exists largely because these absences were
   recorded as corrections rather than as decisions, so each was re-litigated and re-asserted inconsistently.

### F — Residue the sweeps could not reach

| Id | Severity | Finding | Evidence |
|---|---|---|---|
| SB-64 | Medium | **Fenced diagrams still carry removed content.** The Bounded Context Map styles `SagaOrchestrator.DocumentSigning` with a `:::dead` class and labels the SecuredSigning edge *"adapter not built — see note"* — pointing at a note that no longer exists. Also: `system-architecture.md` ascii and mermaid (`deploySearch`, `🟡 deferred` nodes), `Processing/context-overview.md` pipeline (*"⚠ no trigger; see § Service Boundaries"*, now dangling), `asset.scenarios.md` plantuml `<<NOT IMPLEMENTED>>`, `processingjob.scenarios.md` mermaid *"no trigger today"*, `concurrency-and-consistency.md` reservation schema *"⚠ designed, not shipped"* ×2. Separately, the `api-conventions.md` idempotency code block shows `MarkAsync` before `next(context)`, contradicting the `2xx`-only rule the prose now states. | as listed |
| SB-65 | Medium | **Dated change history without a citation id survives**, and is out of scope for both completed sweeps: `error-catalog.md` `*(added 2026-09-07)*` row stamps and "Removed 2026-09-04"; `api-conventions.md` "This paragraph read … until 2026-09-04"; `recordtype.write-model.md` "`AllowsConcurrentEdit` was added after events had already been written"; `Metadata/context-overview.md` strikethrough pointing at a removed document; `_Last reviewed:_` / `_Last updated:_` stamps tree-wide. | as listed |
| SB-66 | Low | **Eight open questions are embedded in spec prose**, which the purity rule forbids regardless of merit. They are carried into § Open Questions below rather than left in place. | `mediaprofile.write-model.md:165`, `mediachangerequest.api.md:332`, `documentsigningsession.write-model.md:86`, `registration.api.md:101`, `registration.context-overview.md:111`, + 3 |
| SB-67 | Low | **Nine markdown tables have ragged column counts**, all in the two bulk-import aggregate folders and `operations.md`. Pre-existing; at least one row is genuinely missing a cell. | `bulkfolderimportjob.*`, `bulkmediaimportjob.*`, `operations.md:41` |

---

## Open Questions

Every one of these must be answered before a plan is written. Several are rulings only Chase can make; the rest
need a design decision that no document currently records.

1. **Is the authorization matrix a specification of intent, or a description of enforcement?** —
   **Answered:** *intent — and it is not a matrix.* (Chase, 2026-09-16.)

   Authorization is specified as **three separate things, in three places**, modelled on Microsoft Graph:

   **a. The scope vocabulary — one new `shared/api-permissions.md`.** A closed set of API permissions in the
   grammar `Resource.Verb[.All]`. This file defines the grammar, the full set, the tier semantics, the `.All`
   semantics, and how a granted scope reaches a handler (claim name and format). A scope used anywhere in
   `docs/` and absent from this file is a defect. The set is also the canonical list `magiq-auth` must issue
   in the `roles` claim, so this file becomes the contract that
   `docs/spec/shared/magiq-auth-role-claims-requirements.md` points at.

   **Three verbs, not two** (closes SB-70):

   | Verb | Covers |
   |---|---|
   | `Read` | queries and read routes |
   | `ReadWrite` | ordinary create and mutate |
   | `Manage` | governance and destructive operations — publish, withdraw, purge, deprecate, archive-cascade, the five MediaProfile policy setters, the Registration decisions |

   **The `.All` constraint carries the owner distinction.** Omitted means the caller's own resources;
   `.All` means any resource in the tenant. `Asset.ReadWrite` is your own assets, `Asset.ReadWrite.All` is
   any asset in the tenant. This is the declarative form of the distinction currently expressed by bespoke
   `AssetOwnership.CheckOwner` / `RegistrationOwnership.CheckOwner` guards.

   **b. The endpoint → scope mapping — the existing `## Authorization` section of each `<agg>.api.md`.**
   Per route *and per query*, giving the least-privileged scope that admits the call and any
   higher-privileged scope that also admits it. It sits with the route's status codes and error codes
   because it is part of that endpoint's contract. **There is no central mapping table.** A 132-row file is
   maintained by a different edit than the one adding the command, which is how the current one drifted; and
   a derived table that is hand-written is drift with extra steps. If the cross-cutting view is wanted, it
   is generated from the per-endpoint declarations — tooling, not a spec file.

   **c. Resource-level rules — where they already are.** Owner match, reviewer-roster membership,
   edit-session participation, change-request participant set. These stay as aggregate invariants in
   `<agg>.write-model.md` and as stated preconditions.

   **Scopes do not replace resource checks, and the two are never merged.** A scope says what the *token* is
   permitted to attempt; a resource predicate says whether *this* resource is in range for *this* caller.
   `Asset.ReadWrite` still requires `asset.OwnerId == actor.Id` to be evaluated at the resource. Collapsing
   the two layers is precisely how the retired matrix came to be an enforcement audit rather than a
   specification, so the distinction is structural, not stylistic:

   - A scope is checked at the edge, is coarse, and is the same for every caller holding it.
   - A resource predicate is checked in the handler or the aggregate, is per-resource, and is what produces
     `403 NotResourceOwner` / `NotAssignedReviewer`.
   - `.All` **widens the scope, it does not remove the predicate** — it changes the predicate's range from
     "owned by the caller" to "in the caller's tenant". Tenant scoping remains structural and universal, and
     is never expressed as a scope.

   **`shared/authorization-matrix.md` is retired as a source of truth.** The one part worth keeping is its
   § Privileged commands analysis — which operations can override another user's state, act tenant-wide,
   break a lock or disable a guard. That reasoning is a decision, not a specification, and moves to the ADR
   (SB-61), where it becomes the justification for the `Manage` tier.

   **Effect on the findings.** SB-1…SB-5 keep their severity and none of them closes. What changes is their
   form: each becomes *assign a scope, and state the resource predicate where the resource is owner- or
   membership-scoped*, rather than ~100 bespoke prose rules. SB-68 (no query is covered) and SB-69 (the ten
   existing tables need a scope column and a consistent shape) are raised by this ruling. SB-70 is closed by
   the three-verb decision above.
**Tier 1 — scope calls. Answer these first: each one changes the finding list itself.**

2. **Do `BulkFolderImportJob` and `BulkMediaImportJob` stay in the spec?** — **Open.** Both are fully
   specified, neither carries an `AggregateType`, and their six files hold most of the ragged tables.
   Removing them closes SB-13 in part, SB-46, and most of SB-67. Keeping them is defensible; so is removing
   them until they are designed for real. **Blast radius: ~4 findings, 6 files.**
3. **Is cross-region DR in scope?** (SB-21) — **Open.** If it is, the runbook has to specify it. If it is
   not, the cross-region RTO/RPO rows are deleted and SB-21 stops being a contradiction to resolve.
   **Blast radius: reshapes 1 finding.**
4. **Do `_Last reviewed:` / `_Last updated:` stamps stay?** (SB-65) — **Open.** Document metadata rather than
   system state, so the purity rule does not obviously reach them — but they are the last dated thing in the
   tree. **Blast radius: sets SB-65's boundary, tree-wide.**

**Tier 2 — domain-model rulings. Everything downstream quotes these.**

5. **Is `owner_system` a reserved value?** (SB-9) — **Open.** Either `MediaProfile` uses it for
   platform-level profiles, or there is no sentinel and no owner-scoping. Three files state one, one states
   the other.
6. **Does `IdentityAcl` exist in the design?** (SB-11) — **Open.** Named as the actor resolver in four
   places; the `Api` host section specifies `IExecutionContext`. **Answerable as intent only** — this review
   read no code, and for a spec what matters is what we intend the resolver to be. If the code disagrees,
   that is a board item, not a spec question.

**Tier 3 — contradictions between two stated designs. The finding stands either way; the answer picks which
side gets rewritten.**

7. **Infected upload: hard delete, or move to quarantine?** (SB-19) — **Open.** Compliance-relevant evidence
   handling on a government records platform; the two specs are irreconcilable as written.
8. **Are folder write endpoints owner-gated?** (SB-6) — **Open.** Either `OwnerId` on a folder is control,
   or it is provenance and the authorization row goes. Also feeds the scope assignment in phase 4b.
9. **Idempotency: replay the response, or reject the duplicate?** (SB-20) — **Open.**

**Tier 4 — shapes the plan.**

10. **What shape should the domain-model ADR take?** (SB-61) — **Open.** One foundational ADR covering the
    aggregate set, boundaries, relationships and the permission model; or one per bounded context; or an ADR
    per contested decision in group B. Answer last — the right shape depends on how many of tiers 2 and 3
    turn out to be genuine decisions rather than corrections.

---

### Two questions deliberately not listed here

An earlier draft carried *"do signers act in sequence or in parallel?"* and *"what identifies a signing
session's owner?"* as open questions. **They are not review questions and listing them made this review
un-closable by construction** — the gate demands zero `**Open**` markers, and neither can be answered without
doing the remediation the gate is blocking.

They are not open questions. They are findings — **SB-35 and SB-31** for signer routing, **SB-12** for session
ownership — and each is a design decision to be taken in phase 6, where DocumentSigning is scheduled first
precisely because it is the least entangled context. Nothing is lost by moving them; what changes is that
answering them is remediation work rather than a precondition for starting it.

---

## Dependencies

**Documents:** none. This is the first review on a fresh board; `reviews/` and `plans/` were cleared on
2026-09-16 and the `MM-` sequence restarted at this document.

**External blockers:** none for the review. Note for the eventual plan: the role-claims contract in
`shared/magiq-auth-role-claims-requirements.md` describes what the platform needs from the `magiq-auth` team.
Specifying authorization (group A) does not depend on it — the rule can be written before the claim is issued —
but implementing it will.

**Standing constraints:** the repo `CLAUDE.md` § *Spec files state the specified system* governs every edit this
review leads to. No remediation may reintroduce a citation, a build-status claim, a rationale, an open question
or a date.

---

## Recommended sequencing

Rough; the plan refines it. The ordering principle is that **a contradiction must be resolved before anything
quoting it is rewritten**, and the domain model is quoted by everything.

1. **Decide, before editing.** Answer the nine questions still `Open`, in tier order — tier 1 first, because
   those three change the finding list itself and agreeing a list you are about to alter is ceremony. No spec
   file is touched in this phase.
2. **Write the domain-model ADR** (SB-61) — all four bodies of reasoning above, including the permission
   model. Everything downstream cites it, and phases 4a/4b cannot start without §3 of it.
3. **Fix the domain model itself** (group B) — `domain-model.md`, `bounded-contexts.md`, `glossary.md`.
   Inventory, discriminators, entity/VO classification, `owner_system`, expiry, `IdentityAcl`, the naming
   corrections (SB-15, SB-16).
4. **Specify authorization** (group A), in the three-part shape settled in Open Question 1. Largest single
   body of writing in the plan, and it splits cleanly:
   - **4a. Write the vocabulary** — `shared/api-permissions.md`. One file, closed set, done once. Nothing in
     4b can be written until the grammar and the verb set exist.
   - **4b. Map endpoints to scopes**, one aggregate at a time, in each `<agg>.api.md`. Covers **queries as
     well as commands** (SB-68) and adds a scope column to the ten existing tables while normalising their
     shape (SB-69). Each row carries a scope *and*, where the resource is owner- or membership-scoped, its
     resource predicate — the two are never merged.
   - **4c. Retire `shared/authorization-matrix.md`.** Only after 4b covers every route it names, so nothing
     is lost in the gap. Its § Privileged commands reasoning has already moved to the ADR in phase 2.
5. **Resolve the cross-file contradictions** (group C), now that the vocabulary underneath them is settled.
6. **Close the context gaps** (group D), one bounded context at a time — DocumentSigning first, since it has
   the most and is least entangled with the rest.
7. **Clean the ADR tree** (SB-62, SB-63) — history out, identity settled.
8. **Sweep the residue** (group F) — diagrams, dated history, ragged tables.
9. **Re-baseline.** Re-run the citation and build-status detectors, the link and anchor checker, and the table
   and fence integrity checks. All must return zero. Consider promoting them to a CI guard so this class of
   drift cannot return silently.
