---
id: MM-001
type: review
project: magiq-media
workstream: spec-baseline
raised-by: []
status: done
outcome: plan
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

**One deliberate scope exception, 2026-09-16.** `Magiq.AspNetCore.Idempotency` in the `aspnetcore-platform`
repo was read — `IIdempotencyStore`, `IdempotencyMiddleware` and `IdempotencyOptions` — to settle whether the
SDK can store and replay a response envelope. The exception is taken because the answer decides the plan's
**status field** rather than any document's content: if the SDK cannot, phase 5 is blocked on another repo
and no amount of spec writing closes SB-20. It could not. The finding is recorded under Q9, and it remains
the only code this review rests on.

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
| SB-6 | Medium | **`folder.api.md` contradicts itself in 13 lines.** Write endpoints are specified as `caller.owner_id == folder.OwnerId`; thirteen lines later, *"`OwnerId` on a folder is provenance, not control. It is denormalised from the `Collection`."* `collection.api.md:57` has the identical shape. *(Resolved by Q8, following Q5: two deletions. Severity dropped from High.)* | `folder.api.md:72` vs `:85`; `collection.api.md:57` |
| SB-71 | High | **Cascade commands have no resource-level restriction, and the spec does not say whether that is intended.** After Q5 and Q8, `ArchiveFolder` and `ArchiveCollection` — which archive an entire subtree — are governed by scope and tenant scoping alone, so any caller holding the scope may run them against any folder or collection in the tenant. That may well be correct; it is not a stated decision. Settled in phase 4b when the `Manage` tier is assigned. | consequence of Q5 + Q8; `archive-fan-out.md`, `folder.api.md`, `collection.api.md` |
| SB-7 | High | **Five Registration endpoints specify `actor_type = "System"` with no stated enforcement point.** The spec gives the requirement and never says which layer applies it. | `registration.api.md` § Authorization |
| SB-8 | High | **Reviewer authorization names a field that does not exist.** *"Reviewer commands: `context.Actor.Id ∈ ChangeRequest.Reviewers[].ReviewerId`"*. `ChangeRequest` has no `Reviewers` member; approval is an invariant on `MediaItem.ReviewSession`. | `architecture/system-architecture.md:742`; cf. repo `CLAUDE.md` § Auth |
| SB-68 | High | **No query is covered by any authorization statement.** The matrix is scoped to *"every write command"* — 132 rows, zero queries. Under the ruling in Open Question 1 a `.Read` scope is required on every read route, so the mapping has to be extended to the read side of all ten aggregates, which no current document covers. | `shared/authorization-matrix.md:1`, `:8`, `:11` |
| SB-69 | Medium | **Existing per-route Authorization tables state resource predicates, not permissions, and disagree in form.** All ten `<agg>.api.md` files already carry an `## Authorization` section — e.g. `collection.api.md:57–59` gives `caller.owner_id == collection.OwnerId`, "Owner, or collection is `Public`", "Authenticated caller; results are tenant-scoped". These are the resource-predicate half and stay, but each needs a scope column adding and a consistent shape across the ten. | `collection.api.md:53–59`, and the nine siblings |
| SB-70 | Medium | **`Read` / `ReadWrite` is too coarse for regulated records.** `UpdateMediaItem` and `PurgeMediaItemVersion` cannot carry the same scope, nor can `AttachRecordType` and `PublishRecordType`. The privilege tier that § Privileged commands already identifies — governance and destructive operations — has no expression in a two-verb vocabulary. | `shared/authorization-matrix.md` § Privileged commands |

### B — The domain model, its aggregates and their relationships

This is the cluster Chase asked to be got right, and it is where the spec contradicts itself most often.

| Id | Severity | Finding | Evidence |
|---|---|---|---|
| SB-9 | High | **A `RecordType`-specific fact is stated as a platform-wide convention, and it is wrong there.** `owner_system` is load-bearing in 13 places across 8 files — seven platform-level `MediaProfile`s are seeded with it, `ChangeRequest.MayClose` is `actor == "owner_system" \|\| actor == OwnerId \|\| IsParticipant(actor)`, `MediaItemApprovedEventHandler` dispatches `ResolveChangeRequestCommand` as it, `AutoSubmitOnComplete` publishes as it, and the glossary reserves it for platform-level config aggregates. Against that, the Naming Conventions row states globally *"System owner \| No reserved value \| … `OwnerId` is provenance only"*. The two `RecordType` statements are correct **in that scope**; `bounded-contexts.md:144` states its first clause absolutely before narrowing. | 13 uses incl. `mediaprofile.defaults.md:15`, `mediachangerequest.write-model.md:70`, `glossary.md:79` — vs `domain-model.md:158`, `bounded-contexts.md:144` |
| SB-10 | High | **Registration both has and has not an expiry.** *"A Registration has no expiry. No event carries an `ExpiresAt`…"* sits 17 lines above `RegistrationExpiryRecorded` in the key-domain-events list. | `domain-model.md:444` vs `:461` |
| SB-11 | Medium | **`IdentityAcl` is named as the actor resolver in four places**, while `bounded-contexts.md:206` and `:388` specify `HttpExecutionContext` resolving `IActor` via `IHttpContextAccessor`. Only the latter is defined anywhere — `IExecutionContext` has an interface, a lifetime and seven `TenantId` invariants; `IdentityAcl` has none. *(Resolved by Q6: the type goes, the ACL relationship stays. Severity dropped from High — four deletions and one substitution, not a design question.)* | `bounded-contexts.md:94`, `:143`, `:331`, `domain-model.md:598` vs `:206`, `:388` |
| SB-12 | High | **`DocumentSigningSession` is gated on an owner it does not have.** Cancel and both read routes are specified as *"Caller owns the session"*; the aggregate, its creation event and both read models carry no owner. `InitiatedBy` exists and was explicitly not the owner, because a delegate may initiate on an owner's behalf. **Carries a design decision** — what identifies the owner — taken in phase 6, not as a precondition. | `documentsigningsession.api.md:60–61`; write-model § Properties |
| SB-13 | Medium | **`RetentionSchedule` has no `AggregateType` discriminator** — `—` in the inventory. The discriminator is the event-stream identity; it is a design decision, not an implementation detail. *(Scoped down by Q2: the two bulk-import aggregates carried the same defect and leave the spec.)* | `domain-model.md:46` |
| SB-14 | Medium | **`RegistrationAmendment` and `Signer` are unclassified.** Both carry full shapes in § Value Objects but appear in no entity/value-object classification. | `domain-model.md` § Entity/VO table |
| SB-15 | Medium | **`MediaChangeRequest` survives as a type name in at least four spec files** and in every `mediachangerequest.*.md` filename. The type is `ChangeRequest`; `[AggregateType("media.changerequest")]` is the authority for the event segment. | `domain-model.md`, `system-architecture.md`, `mediaitem.api.md`, `mediaitem.read-model.md` |
| SB-16 | Medium | **`Media.Api` survives as a host name in three shared files.** No such project has ever existed; the write host is `Api`. | `concurrency-and-consistency.md:47`, `multi-tenancy-and-auth.md:76`, `security-scenarios.md:24` |
| SB-17 | Medium | **`ChangeRequest` is specified as both stateless and stateful.** § Design Notes: *"No lifecycle, no reviewers … a pure comment thread"*; § Status transitions in the same file defines `Open | Resolved | Abandoned`. | `mediachangerequest.write-model.md` |
| SB-77 | Medium | **The spec does not say whether a tenant may modify a platform-seeded `MediaProfile`.** Seven profiles are seeded by `SeedDefaultProfilesService` and are then indistinguishable from tenant-authored ones except by the `owner_system` sentinel, which Q5 removes. Nothing states whether a `MediaAdministrator` may deprecate, revise, rename or delete one, nor what happens to items conforming to it if they do. `ProfileOrigin` makes the rule expressible; the rule itself still has to be written. | `mediaprofile.defaults.md`, `mediaprofile.write-model.md`; consequence of Q5 |
| SB-18 | Low | **The `Capability` set is stated as nine members and enumerated nowhere.** The API's four-value list is described as contested. | `glossary.md:36`, `mediaprofile.write-model.md:177` |

### C — Cross-file contradictions

| Id | Severity | Finding | Evidence |
|---|---|---|---|
| SB-19 | **Critical** | **Two incompatible designs for an infected upload.** AssetManagement specifies the infected original is **hard-deleted** from `media-originals`; Processing specifies it is **moved to `media-quarantine`**. This is a compliance-relevant evidence-handling path for a government records platform, and the spec states both. | `asset.scenarios.md:386`, `:417` vs `Processing/context-overview.md` §§ S3 Paths, External Dependencies |
| SB-20 | High | **Idempotency is specified two ways.** Bulk: *"A replayed key with the same payload returns the cached envelope without re-processing."* Conventions: the middleware rejects the duplicate with `409` and an empty body, and never replays. *(Resolved by Q9 toward the bulk statement: conform to `draft-ietf-httpapi-idempotency-key-header-07` in full. `api-conventions.md` § Idempotency is rewritten; bulk then becomes correct as written.)* | `bulk-operations.md:155` vs `api-conventions.md` § What it actually does |
| SB-72 | High | **No idempotency fingerprint, and no `422` for key reuse.** The draft (§2.4) requires a checksum of the request payload stored with the key so that a key replayed with a *different* body is refused `422` rather than silently returning the cached response. Neither the fingerprint nor the code exists in the spec. On a multi-tenant platform this is the failure mode that matters, and the draft treats it as a security consideration. | `api-conventions.md` § Idempotency; draft §2.4, §2.7 |
| SB-73 | Medium | **`409` conflates a concurrent request with a completed duplicate.** The draft reserves `409` for a retry arriving while the original is still in flight, and specifies a `ProblemDetails` body. The spec returns `409` with an empty body for every repeat inside the window. | `api-conventions.md:94` |
| SB-76 | High | **The idempotency key is not scoped to the operation.** `IIdempotencyStore` keys on tenant + owner + key only, so the same `Idempotency-Key` sent to two different endpoints collides — the second is refused `409` having never executed. The IETF draft requires a key not be reused with a *different payload*; this is weaker still, since the key is not bound to the route either. Confirmed against `IIdempotencyStore.cs` and `DynamoDbIdempotencyStoreTableSchema.cs`. Part of the same SDK change as SB-20. | `aspnetcore-platform`: `IIdempotencyStore.cs`, `IdempotencyMiddleware.cs` |
| SB-74 | Low | **A missing `Idempotency-Key` on a documented idempotent operation is unspecified.** The draft specifies `400` with a link to the idempotency documentation. The spec states only that a request without the header passes through, which is correct for opt-in endpoints but says nothing about endpoints where the key is required. | `api-conventions.md` § Idempotency |
| SB-21 | Low | **Cross-region DR is both a target and out of scope.** The RTO/RPO table specifies cross-region RTO < 4 h via active-passive failover; the runbook states there is no cross-region strategy in this design. *(Resolved by Q3 — single-region is the design. Severity dropped from High: this is now a two-row deletion plus one runbook sentence, worked in phase 8.)* | `operations.md:229` vs § runbook |
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

**Processing / AssetManagement** — SB-38 **promoted to design work by Q7 and moved to phase 5**: the
quarantine move names no performing component and no pipeline step, and now also needs the move semantics,
the bucket's IAM posture, retention on quarantined objects, and a retrieval path with a scope · SB-39 neither projector lists `ProcessingJobBypassed`, so a bypassed job's read
state is unspecified · SB-40 `ListProcessingJobsForAssetIdQuery` has no named handler · SB-41 no
aggregate-specific rebuild or replay path for `ProcessingJob` read models · SB-58 no retention or lifecycle rule
on `media-renditions` for objects cleanup misses.

**Catalog** — SB-43 **High** MediaItem publish specifies no minimum reviewer count and no reviewer
de-duplication; `ReviewerIsInitiator` survives only in `security-scenarios.md` · SB-44 `PUT /metadata` null
semantics (clear vs skip) unstated · SB-45 `DELETE /roles/{roleName}/assets/{assetId}` response code unresolved
(`200` + body vs `204`) · SB-46 **closed by Q2** — the Catalog context overview omitted both bulk-import aggregates, which now leave
the spec entirely ·
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
| SB-75 | Medium | **`spec/README.md`'s map is overturned by the Q1 ruling in two places.** Row 14b routes *"who may run a given write command"* to `authorization-matrix.md` as authoritative and states *"A row saying 'none' is a finding, not a specification"* — a description of the enforcement audit that ruling retires. The file tree at `:71` lists the same file the same way. Both must be repointed at `shared/api-permissions.md` and the per-endpoint tables, in phase 4c alongside the retirement. | `spec/README.md:39`, `:71` |
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
| SB-65 | Medium | **Every date in a spec file.** Out of scope for both completed sweeps: `error-catalog.md` `*(added 2026-09-07)*` row stamps and "Removed 2026-09-04"; `api-conventions.md` "This paragraph read … until 2026-09-04"; `recordtype.write-model.md` "`AllowsConcurrentEdit` was added after events had already been written"; `Metadata/context-overview.md` strikethrough pointing at a removed document; **and the `_Last reviewed:_` / `_Last updated:_` headers tree-wide** — widened by Q4, which settled the rule at its strongest form: no date in a spec file, for any reason. Acceptance is one grep returning zero, and the check is CI-enforceable. | tree-wide |
| SB-66 | Low | **Eight open questions are embedded in spec prose**, which the purity rule forbids regardless of merit. They are carried into § Open Questions below rather than left in place. | `mediaprofile.write-model.md:165`, `mediachangerequest.api.md:332`, `documentsigningsession.write-model.md:86`, `registration.api.md:101`, `registration.context-overview.md:111`, + 3 |
| SB-67 | Low | **One markdown table has a ragged column count.** *(Scoped down by Q2: eight of the nine were in the two bulk-import aggregate folders, which leave the spec.)* | `operations.md:41` |

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

2. **Do `BulkFolderImportJob` and `BulkMediaImportJob` stay in the spec?** —
   **Answered:** *no — remove them.* (Chase, 2026-09-16.)

   Both aggregates and all six of their spec files leave `docs/spec/`, along with every reference to them.
   The specified inventory becomes **eleven aggregates**, each of which someone has designed to completion.
   They are re-specified when they are genuinely designed; nothing is lost that git history does not hold.

   **Not affected:** the inline bulk *endpoints* — `POST /v1/items/bulk`, `/v1/collections/bulk` and the
   folder bulk routes — are a different thing and stay. Verify they still read correctly after the sweep.

   **Effect on the findings.** SB-46 closes outright. SB-67 reduces to `operations.md:41` alone. SB-13
   reduces to `RetentionSchedule` — one aggregate with no `AggregateType`, not three. The `BFI-*` / `BMI-*`
   scenario ids disappear with their files, so the citation keep-list shrinks accordingly.

   **Remediation:** delete the six files, remove the two rows from `domain-model.md` § Aggregates, and sweep
   `docs/` for every remaining mention — `bulk-operations.md` and Catalog `business-scenarios.md` both carry
   them. Acceptance: `grep -ril 'bulk.*importjob' docs/` returns nothing.
3. **Is cross-region DR in scope?** (SB-21) — **Answered:** *no — the design is single-region.*
   (Chase, 2026-09-16.)

   Delete the cross-region RTO/RPO rows. The in-region targets (RTO < 30 min, RPO < 1 min) stand unchanged.
   The runbook states plainly that there is no cross-region failover in this design, so a reader cannot infer
   a capability that was never designed — an absence stated is a design fact and belongs in the spec; an
   absence left implicit is how the contradiction arose.

   If cross-region DR is later required it arrives as a feature request with its own design, not as a target
   row in an operations document.

   **Effect on the findings.** SB-21 stops being a contradiction to resolve and becomes a two-row deletion
   plus one runbook sentence. It moves out of phase 5 and into phase 8 with the rest of the residue.
4. **Do `_Last reviewed:` / `_Last updated:` stamps stay?** (SB-65) — **Answered:** *no — remove them.*
   (Chase, 2026-09-16.)

   Git is the review record, and it cannot go stale. A hand-maintained stamp can, and several already have —
   files edited this week still carry August dates, which is worse than no signal because it makes a wrong
   file look freshly checked.

   **This settles the rule at its strongest form: no date appears in a spec file, for any reason.** That is
   the acceptance check — one grep, returning zero — rather than a judgement about which dates are metadata
   and which are history. Freshness is answered by `git log`.

   **Effect on the findings.** SB-65 widens to cover the header stamps as well as the inline row stamps
   (`*(added 2026-09-07)*`), the prose history (*"until 2026-09-04 this read…"*) and the strikethrough
   pointing at a removed document. All of it is phase 8.

   **Consequence worth noting:** this makes the rule mechanically enforceable. A CI guard can assert that no
   file under `docs/spec/` matches a date pattern — which is the kind of check phase 9 should promote, since
   this class of drift returned once already.

**Tier 2 — domain-model rulings. Everything downstream quotes these.**

5. **Is `owner_system` a reserved value?** (SB-9) — **Answered:** *no — remove the sentinel entirely.*
   (Chase, 2026-09-16.)

   The Naming Conventions row is the design: **`OwnerId` is provenance only, and carries no authority.** The
   13 existing uses are drift, not precedent. System authority is expressed through `actor_type == "System"`,
   which the platform already carries as a JWT claim and already uses for privileged commands — an owner id
   is the wrong carrier for it, because it conflates *who created this* with *what this caller may do*.

   This also sits well with the Q1 ruling: a scope says what the token may attempt, `actor_type`
   distinguishes a system caller, and `OwnerId` feeds the resource predicate. Three concerns, three carriers.
   `owner_system` was doing two jobs at once.

   **This is the larger of the two available answers, and the review records it as such.** Eight files, 13
   sites, and two of them are authorization paths rather than labels:

   - **`ChangeRequest.MayClose(actor)`** is `actor == "owner_system" || actor == OwnerId ||
     IsParticipant(actor)`. Becomes an `ActorType` test. This is an aggregate invariant, so it changes the
     aggregate's specified behaviour, not just its prose.
   - **`MediaItemApprovedEventHandler`** dispatches `ResolveChangeRequestCommand` as `owner_system`, and
     **`AutoSubmitOnComplete`** dispatches `PublishMediaItemCommand` the same way. Both need a System actor
     instead. `mediachangerequest.write-model.md:114` calls this path load-bearing.
   - **`glossary.md:79`** defines the term as reserved; the definition goes.
   - **`mediaprofile.defaults.md`** and Catalog `context-overview.md` seed **seven platform-level profiles**
     owned by it.
   - `system-architecture.md:538` carries it inside a sequence diagram — phase 8, with the other fenced
     content.

   **The follow-on — what owns the seven seeded platform profiles — was settled 2026-09-16 (Chase):
   nothing does. `MediaProfile` loses `OwnerId` and gains `ProfileOrigin`.**

   The question turned out to be the wrong one. **Nothing reads `MediaProfile.OwnerId`** — every occurrence
   is the seeding call, the event payload, or a statement that it governs nothing
   (`authorization-matrix.md:113`, `error-catalog.md:70`). The summary read model omits the field
   (`mediaprofile.read-model.md:101`), so no owner-scoped profile query could be served even if one existed,
   and profile governance is already role-based: `ProfileGovernanceAuthorization.CheckPrivileged` is System
   **or** `MediaAdministrator`.

   On `MediaItem`, `Asset` and `Registration`, `OwnerId` answers *whose is this* and feeds a resource
   predicate. On `MediaProfile` it answers nothing — a profile is tenant-wide configuration, not a member's
   resource. And because the field is `MemberId` **non-nullable**, keeping it forces the very problem this
   ruling removes: it must be populated with something, so either a sentinel, a fake member, or a nullable
   field nobody reads. The platform SDK's own conventions rule out the sentinel form twice —
   *"never raw `Guid` or `string` for identifiers"* and *"avoid raw string literals for type discriminators"*.

   **`owner_system` was encoding three things, not two.** Q5 stripped identity and authority. The third is
   **origin** — platform-provided versus tenant-authored — and deleting the field without replacing that
   would lose a real distinction. `ProfileOrigin: Platform | Tenant` carries it, as a smart enum
   (`Ardalis.SmartEnum`, already in the stack) rather than a magic value.

   **Changes, in phase 3:** remove `OwnerId` from the aggregate, `CreateMediaProfileCommand`,
   `MediaProfileCreated` and the detail read model; add `ProfileOrigin`, set to `Platform` by
   `SeedDefaultProfilesService` and `Tenant` otherwise.

   **Cost to carry:** `MediaProfileCreated` is a persisted event, so removing a field needs an upcaster. The
   SDK provides the mechanism — `IEventUpcaster<TEvent>`, registered via
   `AddDomainEventUpcastersFromAssembly` — and this is its first use. Note the existing events for the seven
   already carry `"owner_system"`, so they need handling under any option, not just this one.

   **Raised by this ruling: SB-77** — the lifecycle rule `ProfileOrigin` now makes expressible.

   **Effect on the findings.** SB-9 keeps High severity but changes shape: from correcting one wrong row to
   removing a sentinel across eight files, with an aggregate-invariant change inside it. It stays in phase 3.
6. **Does `IdentityAcl` exist in the design?** (SB-11) — **Answered:** *no as a type; yes as a relationship.*
   (Chase, 2026-09-16.)

   **Remove `IdentityAcl` as a named type** from all four sites. **Keep "Identity → Media Management:
   Upstream / ACL"** as the relationship type in the context map, and name **`HttpExecutionContext`** as what
   performs the claim → `IActor` translation.

   **Why the type goes.** Only one of the two is designed. `IExecutionContext` has an interface definition, an
   implementation table naming `HttpExecutionContext` resolving `IActor` *"from validated JWT claims via
   `IHttpContextAccessor`"*, a scoped-per-request lifetime, and seven invariants governing `TenantId`
   sourcing. `IdentityAcl` appears only in relationship tables and the context-map diagram — no interface, no
   lifetime, no owning project. `bounded-contexts.md:206` and `:388` agree with each other; the four
   `IdentityAcl` mentions are the outlier.

   The translation it would perform is five direct field assignments — `sub`→`Actor.Id`, `name`→`Actor.Name`,
   `roles`→`Actor.Roles`, `actor_type`→`Actor.ActorType`, `tenant_id`→`TenantId` — with no lookup, no
   enrichment and no runtime call. Compare `BillingAcl` in the same table, which calls an external service and
   translates *Billing's* response into `QuotaCheckResult`: that layer absorbs a change we cannot prevent, and
   the spec defines its signature. A five-claim rename is not that.

   **Why the relationship stays.** A context map records what kind of coupling two contexts have — who
   conforms to whom, and where we defend our model. A class name records which code does it. The first is
   architecture, the second an implementation detail that can change without the relationship changing. If
   `magiq-auth` reshapes `roles`, a translator gets extracted; the relationship was ACL before and after, and
   a map recording only the class name would have to be edited to register a refactor — and would meanwhile
   claim no boundary exists, which is false.

   **Conformist would be the wrong label.** It asserts we adopt the upstream model wholesale and change our
   domain when theirs changes. Untrue here: `IActor` is our type with our `User | System | Guest` notion, and
   `OwnerId` is stamped from `Actor.Id` into our own ownership concept. We translate at that boundary already.
   **A thin ACL is still an ACL** — and under the Q1 ruling it stops being thin, because
   `Resource.Verb[.All]` scopes arrive as claims and need mapping onto something handlers can evaluate. That
   is exactly the work the boundary exists for.

   **Effect on the findings.** SB-11 becomes four deletions plus one substitution, not a design question. It
   stays in phase 3. The context-map diagram edge label is fenced content and is swept in phase 8.

**Tier 3 — contradictions between two stated designs. The finding stands either way; the answer picks which
side gets rewritten.**

7. **Infected upload: hard delete, or move to quarantine?** (SB-19) — **Answered:** *quarantine — and
   specify the move properly.* (Chase, 2026-09-16.)

   The infected original **moves to `media-quarantine`**; it is not destroyed. The Processing spec is the
   design and the AssetManagement hard-delete statement is the error. `ContainsVirus` and
   `AssetInfectionDetected` still record the detection — what changes is that the bytes survive.

   **This ruling creates work rather than closing it, and the review says so plainly.** AssetManagement's
   text is the only place that currently says what happens to the object, and it is being deleted. Five
   things have to be specified before the quarantine path is a contract rather than a bucket name:

   1. **Which component performs the move**, and at which pipeline step. `Processing/context-overview.md`
      § Pipeline has no quarantine step at all. This is SB-38, which stops being a gap and becomes design.
   2. **Copy-then-delete or server-side move**, and what happens if the second half fails — a partial move
      leaves an infected object in `media-originals`, which is the outcome the whole path exists to prevent.
   3. **What access `media-quarantine` grants.** It is a bucket that knowingly holds malware, so its IAM
      posture is a security decision, not an infrastructure detail.
   4. **Retention on quarantined objects** — indefinite, or a disposal period. On a records platform the
      answer probably interacts with `RetentionSchedule`, and nothing currently connects them.
   5. **Who may retrieve one, and how.** A forensic copy nobody is permitted to read is an expense, not
      evidence. Under the Q1 ruling this needs a scope, and plausibly a `Manage`-tier one.

   **Effect on the findings.** SB-19 stays **Critical** and stays in phase 5 — two specs still state
   incompatible things and one must be rewritten. SB-38 is promoted from a gap to design work and moves from
   phase 6 into phase 5 beside it, since the two are one piece of work. Items 2–5 above are new scope, taken
   in the same phase.

   **Not settled by this ruling:** the AM-5 scenario, its PlantUML diagram (which already draws the move and
   marks it unbuilt — fenced content, phase 8), and the `asset.scenarios.md` invariant list all need
   rewriting together, not one at a time.
8. **Are folder write endpoints owner-gated?** (SB-6) — **Answered:** *no — delete the row.*
   (Chase, 2026-09-16.)

   Follows directly from Q5. `OwnerId` is provenance and carries no authority, so it cannot gate a write.
   `folder.api.md:85` is the rule and `:72` is the outlier. The same applies to `collection.api.md:57`,
   which has the identical shape.

   Folder and Collection writes are governed by **scope plus tenant scoping** — tenant scoping being
   structural and universal, never expressed as a scope. Under Q1 that means the `.All` constraint does no
   work on these two aggregates, because there is no owned-subset to distinguish from the tenant-wide set.
   **Say that explicitly in `shared/api-permissions.md`** rather than leaving a reader to infer why
   `Folder.ReadWrite.All` never appears — an unexplained absence is how SB-9 happened.

   **What this ruling does not answer, and must not be read as answering:** whether anything below tenant
   level restricts who may archive a folder subtree. `ArchiveFolder` and `ArchiveCollection` cascade across
   an entire tree, and after this ruling any caller holding the scope may run them against any folder in the
   tenant. That may be correct. It is not currently a stated decision, and it is exactly the kind of absence
   this review exists to stop being implicit.

   **Raised as SB-71** (High, group A): *the cascade commands have no resource-level restriction, and the
   spec does not say whether that is intended.* Settled in phase 4b when the `Manage` tier is assigned —
   `Folder.Manage` / `Collection.Manage` may be the whole answer, but the decision has to be written down.

   **Effect on the findings.** SB-6 becomes two deletions and stays in phase 3. SB-71 is new.
9. **Idempotency: replay the response, or reject the duplicate?** (SB-20) — **Answered:** *cached replay —
   conform to the IETF draft in full.* (Chase, 2026-09-16.)

   The target is `draft-ietf-httpapi-idempotency-key-header-07` (Standards Track, still a draft).
   `bulk-operations.md` is closer to it than `api-conventions.md`; the fully-specified file describes the
   narrower mechanism and is candid about it — *"Call this replay rejection, not idempotency, when precision
   matters."*

   **The draft distinguishes four cases where the spec currently has one:**

   | Case | Response |
   |---|---|
   | Retry **after** the original completed | the result of the previous operation — success **or** error |
   | Retry **while** the original is in flight | `409 Conflict` with a `ProblemDetails` body |
   | Same key, **different payload** | `422 Unprocessable Content` |
   | Key missing on a documented idempotent operation | `400` with a link to the idempotency documentation |

   `409` is for genuine concurrency only — not for duplicates in general, which is what the current spec
   uses it for.

   **The hardest prerequisite is already decided.** `api-conventions.md:121` specifies that `MarkAsync` runs
   *after* `next(context)` and only on a `2xx`, so a failed request leaves its key unconsumed and an honest
   retry re-executes. That is exactly the ordering cached replay requires, and it already fixes the
   worse-than-nothing case where a transient failure permanently burnt a key.

   **One concept is absent entirely and has to be added: the idempotency fingerprint** (draft §2.4) — a
   checksum of the request payload stored alongside the key, so a key reused with a different body is caught
   and refused `422`. Without it a client bug silently returns the wrong cached response. The draft treats
   this as a **security** consideration, not merely a correctness one, and this review agrees: on a
   multi-tenant records platform, returning one caller's cached envelope to another request is the failure
   mode that matters.

   **Two constraints this ruling inherits rather than solves:**

   - **Expiry is not what the spec claims.** `api-conventions.md:113` already states that `ExistsAsync`
     checks key presence only and never reads the stored `ExpiresAt`, so expiry depends entirely on
     DynamoDB's TTL sweeper — *"which AWS does not guarantee within 48 h"*. The stated 24-hour window is
     therefore a floor, not a window, and that matters more once response bodies are being stored.
   - **Envelope storage is not ours to specify — resolved 2026-09-16 against the SDK source.** See the
     scope exception in § Scope; this is the one place this review read code, because the answer decides
     the plan's *status field* rather than its content.

     **`Magiq.AspNetCore.Idempotency` cannot store or replay a response.** `IIdempotencyStore` has exactly
     two methods — `ExistsAsync(tenantId, ownerId, key) → bool` and
     `MarkAsync(tenantId, ownerId, key, expiresAt)`. **No response parameter, and no retrieval method.**
     The abstraction has nowhere to put an envelope, so conformance is a change to the SDK contract, not a
     magiq-media spec edit.

     Four further facts from the same source, each of which the spec will have to state or the plan will
     have to close:

     - **`MarkAsync` runs before `next(context)`.** The `2xx`-only consumption rule at
       `api-conventions.md:121` is genuinely unimplemented, exactly as the spec says. It is a prerequisite
       for cached replay and is part of the same SDK change.
     - **The `409` carries no body at all** — `context.Response.StatusCode = 409; return;`. Confirms the
       spec.
     - **There is no fingerprint and no in-flight concept**, so neither the `422` (key reused with a
       different payload) nor the draft's `409`-means-concurrent semantics can be expressed today.
     - **The key is scoped to tenant + owner only, not to the operation.** The same key sent to two
       different endpoints collides. The IETF draft requires a key not be reused with a different payload;
       here it is not even scoped per route. **Raised as SB-76.**

     **Delivery shape.** Two packages — `Magiq.AspNetCore.Idempotency.Abstractions` (the contract) and
     `Magiq.AspNetCore.Idempotency` (the DynamoDB store, middleware and migration). magiq-media consumes
     them as NuGet via `Directory.Packages.props` at `$(MagiqPlatformVersion)`, currently resolving
     `1.1.3.5` — not a project reference. So the change is: contract, plugin, package release, version bump
     here. **Phase 5 records this as blocked, and the plan cannot mark SB-20 done from this repo alone.**

   **Effect on the findings.** SB-20 stays High and stays in phase 5, but changes from *"correct one file to
   match the other"* to *"rewrite `api-conventions.md` § Idempotency against the draft, then `bulk-operations.md`
   becomes correct as written."* Raised by this ruling: **SB-72** (fingerprint and `422` absent), **SB-73**
   (`409` conflates concurrent with duplicate), **SB-74** (missing-key `400` unspecified).

**Tier 4 — shapes the plan.**

10. **What shape should the domain-model ADR take?** (SB-61) — **Answered:** *one foundational ADR,
    structured by context internally, plus one standalone ADR per contested decision.* (Chase, 2026-09-16.)

    **The test for which file something goes in: could this be superseded on its own?** If yes, it is a
    decision and gets its own ADR. If it describes structure, it is a section in the foundational one.

    **`adrs/domain-model.md`** — the foundational record, with a section per bounded context giving that
    context's aggregates, where its consistency boundaries fall, its relationships to other contexts, and
    what it deliberately does not model. Internal structure is per-context because the aggregate set and its
    boundaries genuinely are context-shaped knowledge; a reader working in Catalog reads Catalog's section.

    **Four standalone decision ADRs**, one per contested ruling from this review:

    | ADR | Records | From |
    |---|---|---|
    | Ownership and system authority | `OwnerId` is provenance only and carries no authority; system authority is `actor_type == "System"`; the `owner_system` sentinel is removed | Q5 |
    | Infected originals | An infected upload moves to `media-quarantine` rather than being destroyed, and why evidence is retained on a records platform | Q7 |
    | Idempotency conformance | Conformance to `draft-ietf-httpapi-idempotency-key-header-07` — cached replay, `409` for concurrency only, fingerprint and `422` | Q9 |
    | API permission model | `Resource.Verb[.All]`, three verbs, the vocabulary/mapping split, and the rule that scopes never replace resource predicates | Q1 |

    **Why not one ADR per bounded context** — the shape considered and rejected. **SB-9 is what that scheme
    produces.** A `RecordType`-specific fact was recorded as a platform-wide naming convention, and 13 uses
    across three contexts drifted from it; organising decisions by context institutionalises that failure,
    because each context records its own view of a shared rule. The four decisions above have no
    context-shaped scope: `owner_system` touches Catalog, ChangeRequests and Metadata; quarantine spans
    AssetManagement and Processing; permissions and idempotency are platform-wide. Each would be duplicated
    across contexts, which drifts, or assigned to one arbitrarily, which makes it unfindable from the others.
    The existing tree already settles this by example — nine ADRs organised by topic, only two of them
    context-shaped. And supersession is per-decision: a decision is overturned, a bounded context is not, so
    a per-context file has no meaningful `status`.

    **Why not decisions-as-sections in one file** — a decision superseded later would mean editing the
    document every spec file cites.

    **Effect on the findings.** SB-61 becomes five files rather than one, and phase 2 splits accordingly. The
    four decision ADRs can be written in parallel with each other; the foundational one depends on phase 1's
    corrections being settled, which they now are.

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

**Documents:** **`AP-001`** — [Idempotency — the store contract cannot express the standard](../../../aspnetcore-platform/reviews/idempotency-conformance/idempotency-conformance-review-2026-09-16.md),
raised in `aspnetcore-platform` on 2026-09-16 out of this review's Q9.

**Promote this to the plan's `depends-on` when the plan is written**, and point it at `AP-001`'s *plan* id
rather than the review id once that exists — a review that has produced no plan resolves as an **unmet**
dependency. That is the correct reading, and it is what will hold phase 5 blocked.

**Only phase 5 depends on it.** SB-20, SB-72, SB-73, SB-74 and SB-76 are all downstream of the SDK contract
and cannot be closed from this repo whatever the spec says. Everything else proceeds — this is the partial
blocking the dependency rules expect, not a stopped plan.

Otherwise none. This was the first review on a fresh board; `reviews/` and `plans/` were cleared on
2026-09-16 and the `MM-` sequence restarted at this document.

**External blockers:** none for the review. Note for the eventual plan: the role-claims contract in
`shared/magiq-auth-role-claims-requirements.md` describes what the platform needs from the `magiq-auth` team.
Specifying authorization (group A) does not depend on it — the rule can be written before the claim is issued —
but implementing it will.

`aspnetcore-platform` is **not** an external blocker. It carried no adoption marker until 2026-09-16, which
would have made it one; the marker was added (`prefix: AP`, `we-operate: true`) because we own that repo, so
the work is tracked there as a first-class review instead of as a hand-off note here.

**Standing constraints:** the repo `CLAUDE.md` § *Spec files state the specified system* governs every edit this
review leads to. No remediation may reintroduce a citation, a build-status claim, a rationale, an open question
or a date.

---

## Recommended sequencing

Rough; the plan refines it. The ordering principle is that **a contradiction must be resolved before anything
quoting it is rewritten**, and the domain model is quoted by everything.

0. **Land the detectors as repo scripts, before any editing.** The citation, build-status, date, link/anchor
   and table/fence checks used to produce this review currently exist only as throwaway scripts. They are the
   acceptance checks for nine phases of rewriting across ~100 files, and an acceptance check that has to be
   rebuilt from memory each session is not one.

   **This is not a nice-to-have, and the tree carries the evidence.** The previous remediation attempt made
   the same call in its own words — *"This lands before any stripping — stripping without a guard just
   resets the clock"* — recorded the guard as done, and the guard was never written. What survives on disk
   today is `.github/scripts/__pycache__` and nothing else. Nine phases of edits with no detector running is
   how the citations got in.

   ✅ Five checks runnable from one command, each returning zero on the current tree, plus a CI workflow
   that fails on a deliberately reintroduced citation, build-status phrase or date.

1. **Decide, before editing.** Answer the questions in tier order — tier 1 first, because those three change
   the finding list itself and agreeing a list you are about to alter is ceremony. No spec file is touched in
   this phase. ✅ **Complete, 2026-09-16 — all ten Answered.**
2. **Write the ADRs** (SB-61) — five files, per Q10. `adrs/domain-model.md` carries the aggregate set,
   boundaries, relationships and what is deliberately not modelled, in a section per bounded context. Four
   standalone decision ADRs record the contested rulings: ownership and system authority, infected
   originals, idempotency conformance, and the API permission model. The four can be written in parallel;
   the foundational one depends on phase 1, which is complete. **Phases 4a/4b cannot start without the
   permission ADR, and phase 5 cannot close SB-19 without the infected-originals ADR.**
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
     is lost in the gap. Its § Privileged commands reasoning has already moved to the ADR in phase 2. Repoint
     `spec/README.md` rows 14b and `:71` in the same edit (SB-75) — the map currently calls the retired file
     authoritative and describes it in the terms Q1 overturned.
   - **Also closed in 4b:** SB-70 by the three-verb vocabulary, and **SB-71** — the cascade commands
     (`ArchiveFolder`, `ArchiveCollection`) get their `Manage`-tier assignment and either a resource
     restriction or an explicit statement that there is none.
5. **Resolve the cross-file contradictions** (group C), now that the vocabulary underneath them is settled.
   Two items in this phase are design work rather than reconciliation, and are sized accordingly:
   - **SB-19 + SB-38 together** — the quarantine path. Rewriting AssetManagement's hard-delete statement is
     the small half; specifying the performing component, the move semantics and partial-failure behaviour,
     the bucket's IAM posture, retention on quarantined objects, and a scoped retrieval path is the rest.
     Needs the infected-originals ADR from phase 2 first.
   - **SB-20 + SB-72 + SB-73 + SB-74** — idempotency, rewritten against the IETF draft. **First task of the
     item is establishing whether `Magiq.AspNetCore.Idempotency` can store and replay a response envelope.**
     If it cannot, this becomes `blocked-by-external` on `aspnetcore-platform` and the plan records it as
     such rather than as a spec edit.
6. **Close the context gaps** (group D), one bounded context at a time — DocumentSigning first, since it has
   the most and is least entangled with the rest.
7. **Clean the ADR tree** (SB-62, SB-63) — history out, identity settled.
8. **Sweep the residue** (group F) — diagrams, dated history, ragged tables.
9. **Re-baseline.** Re-run every detector from phase 0 — citations, build status, dates, links and anchors,
   tables and fences. All must return zero on a tree that now also contains five new ADRs and
   `shared/api-permissions.md`, neither of which existed when the baselines were taken.

---

### Open items for the plan, not for this review

Four things the plan must settle that no finding covers, because they are about how the work is run rather
than what the documents say:

- **Branch strategy.** The repo sits on `spec/initial-alignment`, which is not in the GitFlow table in the
  repo `CLAUDE.md`. This workstream touches ~100 files across nine phases. One long-lived branch or one per
  phase is a real choice, and the plan's `branches: []` expects appends either way.
- **The `aspnetcore-platform` question** (Q9). Resolve it early: it decides whether phase 5 contains a spec
  edit or a `blocked-by-external` entry, and that changes the plan's status.
- **Who owns the seven seeded platform `MediaProfile`s** once `owner_system` is removed (Q5). Flagged as
  phase 3, not a blocker on starting, but it is new design and needs an owner.
- **`_archive/reviews/` and `_archive/plans/` do not exist.** Harmless now — the mint grep simply finds
  nothing — but they are required at close-out, and `plans/README.md` is required at hand-over. Create them
  when the plan is written, not before.
