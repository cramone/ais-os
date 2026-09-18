---
id: MM-003
type: plan
project: magiq-media
workstream: spec-baseline
consumes: [MM-001]
blocked-by-external: []
status: active
todo-id: a85d40df-3c91-5a96-b00d-94438dd9d1ba
branches: [spec/initial-alignment-work]
ado: -
created: 2026-09-16
---

# Spec Baseline — Remediation Plan

Consumes [MM-001](../../reviews/spec-baseline/spec-baseline-review-2026-09-16.md) — 77 findings, ten
questions answered. **Documents only:** `D:\source\github\sprbrk-standard\mgq-magiq-media\docs\`
(`spec\` + `adrs\`), plus the CI guard in phase 0. No application code is written.

**Dependency gate, run at authoring 2026-09-16.** `depends-on: [AP-001]` resolves **unmet** — AP-001 is a
review in `aspnetcore-platform` that has produced no plan, and the skill's rule 2 reads that as unmet by
design. **Status is `active`, not `blocked`**, under rule 6: the dependency reaches exactly one phase, and
blocking eleven of them on it would stop work with no relationship to the SDK.

**The dependency is isolated in phase 10, not spread through the plan.** Phases 0–9 are documents and run
to completion regardless; phase 10 is the release step that makes phase 5's idempotency contract true, and
it is the reason this plan cannot reach `done` — see § Closing out, *The hard gate*. Re-run this gate at
every session start and every phase boundary; when AP-001 produces a plan, repoint `depends-on` at that
plan's id.

---

## How this plan works

**Eleven phases, ordered so that nothing is written twice.** The spec is a graph of quotations: aggregate
specs quote the domain model, derived surfaces quote write models, and everything will quote the new
permission vocabulary. Fixing an authorization row before the vocabulary exists, or a write model before
the aggregate inventory is settled, guarantees rework. Phases 0 and 1 touch no spec file at all.

**Four standing rules, in force for every item in every phase.**

1. **The guard is the acceptance check.** Every phase ends with `python .github/scripts/docs_guard.py`
   returning pass. An item whose acceptance check cannot be expressed as something a reader or a grep can
   verify is not ready to be worked.
2. **Never invent design.** If closing an item would mean asserting behaviour no document states and no
   MM-001 ruling covers, **stop and ask.** A spec that is silent is a known gap; a spec that is
   confidently wrong is what this workstream exists to undo. Phase 6 is where this bites hardest — it
   writes new specification, and new specification deserves the scrutiny of any design.
3. **Never reintroduce what was removed.** No citation to anything undefined in `docs/`, no build or
   implementation status, no rationale, no open questions, no dates, no attribution. The guard enforces
   the mechanical half; the rest is judgement. **The baseline may shrink and must never grow.**
4. **A new defect does not become a checklist item here.** It goes to a new review, or to MM-002 if it is
   code. Only items tracing to a finding MM-001 already consumes may be split, corrected or closed in
   place. Log every diversion in § Session log.

**Acceptance checks are verifiable by reading the documents**, because this plan changes documents only.
"`grep -c 'owner_system' docs/spec` returns 0" is an acceptance check. "The handler enforces it" is not —
that is MM-002.

---

## Phase 0 — Land the guard ✅ **CLOSED 2026-09-17**

No spec file is touched. Everything after this phase is checked by what lands here; everything before it
was not.

**Why this is phase 0 and not phase 9.** The previous remediation attempt made the same call in the same
words — *"This lands before any stripping — stripping without a guard just resets the clock"* — recorded
the guard as done, and never wrote it. What survived on disk was `.github/scripts/__pycache__`. Nine
phases of editing with no detector running is how the citations got in.

- [x] **Write the detectors.** Five checks in one command: citations (hard zero), links and anchors (hard
      zero), build status, dates, structure (baselined). ✅ `python .github/scripts/docs_guard.py` returns
      pass on the current tree. — **Done 2026-09-16:** `.github/scripts/docs_guard.py`,
      `.github/docs-guard-baseline.tsv` (209 entries), `.github/workflows/docs-guard.yml`.
- [x] **Prove each check catches a regression.** ✅ Seven cases tested individually. — **Done.** Six passed
      first time; the date check did not, and the bug mattered: `\b` does not fire against
      `_2026-08-21_` because `_` is a word character, so **92 `_Last reviewed:_` stamps were invisible** —
      the single most common date form in the tree. Fixed with explicit lookarounds; the count went
      101 → 193.
- [x] **Commit to `spec/initial-alignment-work`** and confirm the workflow fires. The push trigger includes
      `spec/**` precisely because this branch is a long run of direct pushes rather than PRs. ✅ A green
      workflow run on the branch, and a deliberately reintroduced citation failing a run.
      — **Commit half done 2026-09-17:** `02f03c7e` (guard, baseline 209 entries, workflow) and `4ad38621`
      (UTF-8 report output), both pushed; `spec/initial-alignment-work` is level with
      `origin/spec/initial-alignment-work`. `python .github/scripts/docs_guard.py` returns pass locally
      (citations 0, links 0, build-status 0 new / 7 baselined, dates 0 new / 193 baselined, structure
      0 new / 9 baselined). **The box stays open on the CI half** — the run status is not visible from
      this machine's `gh` identity (`cramone`, org `magiqsoftware` only; `Sprbrk-Standard` returns 404),
      and the browser pane is blocked from github.com. Needs an identity with `Sprbrk-Standard` access,
      or Chase reading the Actions tab. The negative test (reintroduced citation fails a run) is
      attributable. — **CLOSED 2026-09-17.** Chase confirmed the workflow ran green on the branch. The
      negative test then ran too: commit `8f422e42` reintroduced two citations in a throwaway spec file and
      the run failed as designed; `5a324400` reverted it. **The guard is now proven in both directions**,
      which is what this box was for.
- [x] **Delete the `.github/scripts/__pycache__` orphan** — the only surviving trace of the previous
      attempt. ✅ `ls .github/scripts/` shows `docs_guard.py` and nothing else. — **Done.** Verified
      2026-09-17: `.github/scripts/` contains `docs_guard.py` and nothing else; the orphan is gone and
      nothing in `.gitignore` was masking it.

## Phase 1 — Decide ✅ **CLOSED 2026-09-16**

No spec file was touched. Every later phase quotes an answer taken here.

- [x] **All ten open questions answered**, in tier order — scope calls first because three of them changed
      the finding list. ✅ Zero `**Open**` markers in MM-001 § Open Questions. — **Done.** Four were genuine
      decisions and earn ADRs in phase 2; six were corrections. The rulings raised SB-68…SB-77 and closed
      SB-46 and SB-70.

## Phase 2 — Write the ADRs ✅ **CLOSED 2026-09-17**

Five files. The four decision ADRs are independent of each other and may be written in parallel; the
foundational one depends on phase 1, which is closed. **Phase 4 cannot start without the permission ADR,
and phase 5 cannot close SB-19 without the infected-originals ADR.**

- [x] **`adrs/domain-model.md`** — the foundational record, with a section per bounded context giving that
      context's aggregates, where its consistency boundaries fall, its relationships, and **what it
      deliberately does not model**. Closes SB-61. ✅ Every contradiction in MM-001 group B is adjudicable
      from this file alone; the four "deliberately not modelled" absences (no reserved owner sentinel, no
      review saga, no Registration expiry, no `RecordType` capability concept) are each stated as a
      decision rather than a correction. — **Done.** Eleven aggregates over seven internal contexts, one
      section each. Opens with the three tests that earn aggregate status, so the embedded/aggregate calls
      (`ReviewSession`, `EditSession`) are decidable rather than asserted. Carries no discriminator column:
      the inventory is spec, and `RetentionSchedule`'s discriminator is an open phase 3 item — putting the
      table here would have meant inventing the value or publishing the gap twice.
- [x] **`adrs/ownership-and-system-authority.md`** — `OwnerId` is provenance and carries no authority;
      system authority is `actor_type == "System"`; the `owner_system` sentinel is removed. Records the
      rejected alternative (keep the sentinel, fix the one wrong row). Closes part of SB-61. ✅ States why
      an owner id is the wrong carrier for authority, and names every one of the 13 sites the removal
      touches. — **Done, with one deliberate departure:** the sites are named **by file and by kind**
      (seeding, aggregate invariant, the two auto-dispatch paths, glossary definition, convention rows,
      diagram), not by line. A line-referenced list in an ADR goes stale on the first edit of the file it
      points at, and the exhaustive list is remediation tracking, which belongs on this side. Four rejected
      alternatives recorded, including the two the ruling did not name (nullable field, reserved platform
      member).
- [x] **`adrs/infected-originals.md`** — an infected upload moves to `media-quarantine` rather than being
      destroyed, and why evidence is retained on a records platform. ✅ States the rejected alternative
      (hard delete) and what retaining malware costs. — **Done.** The five things the ruling said must be
      specified before quarantine is a contract are carried as **consequences this decision commits the
      design to state**, not as open questions — phase 5 writes them into the spec.
- [x] **`adrs/idempotency-conformance.md`** — conformance to `draft-ietf-httpapi-idempotency-key-header-07`:
      cached replay, `409` for concurrency only, fingerprint and `422`. ✅ States why replay rejection was
      insufficient, and records that delivery depends on `aspnetcore-platform`. — **Done.** The SDK
      dependency is recorded as **ownership** — the response-storing contract belongs to that repo — rather
      than as build status, which keeps it inside the purity rule while still saying where delivery
      happens. The expiry-floor and operation-scoping constraints are carried as consequences.
- [x] **`adrs/api-permission-model.md`** — `Resource.Verb[.All]`, three verbs, the vocabulary/mapping
      split, and **the layering rule: a scope is checked at the edge and never replaces the resource
      predicate checked at the aggregate.** Absorbs the retired matrix's § Privileged commands analysis as
      the justification for the `Manage` tier. ✅ Every rule phase 4 applies is stated here first. —
      **Done.** The privileged-commands analysis moved as **reasoning only**: the operations and why each
      is privileged, without the matrix's *Authorization enforced* column, which was the enforcement audit
      this workstream exists to remove. `Manage` is defined by the five-part test rather than by the list,
      so a new command can be classified without amending an ADR. Five rejected alternatives, including
      `.Own`-as-a-scope — the shape the system drifts toward on its own.
- [x] **Update `adrs/README.md`.** Five new rows; settle whether ids are index-only. Closes SB-63.
      ✅ Every ADR file resolves from the index, and the index states how ids map to filenames. —
      **Done. SB-63 settled: ids are index-only and the set is closed.** `ADR-001`–`ADR-014` resolve only
      through the old-number index; no new id is minted and no filename carries one. § Adding a new
      decision now also states **when a decision earns its own file** — the could-this-be-superseded-on-
      its-own test — which is what reconciles the five-file shape with a tree organised by topic.
- [x] **Phase exit.** ✅ All items ticked; `docs_guard.py` pass; no ADR carries a citation to anything
      outside `docs/`. — **Done.** Guard passes; baseline unchanged at 209 and did not grow. One new hit
      was caught and **fixed rather than baselined**: the permission ADR linked forward to
      `spec/shared/api-permissions.md`, which phase 4a creates, so the reference is plain text until the
      file exists. Commit `6b5f45ad`, pushed.

## Phase 3 — The domain model ✅ **CLOSED 2026-09-17**

Everything downstream quotes this. Group B, plus the two inventory rulings.

- [x] **Remove `BulkFolderImportJob` and `BulkMediaImportJob`** — six spec files and every reference.
      Closes SB-46; scopes SB-13 and SB-67. Per Q2. ✅ `grep -ril 'bulk.*importjob' docs/` returns nothing,
      the inventory reads eleven aggregates, and the inline bulk *endpoints* (`POST /v1/items/bulk`,
      `/v1/collections/bulk`, the folder bulk routes) still read as before. — **Done. Eight files, not
      six** (four per aggregate: api, read-model, write-model, scenarios). Also removed:
      `bulk-operations.md` § Async Bulk Import Jobs and its inline-vs-async comparison, the import-job
      pagination exceptions and route-prefix row in `api-conventions.md`, the `BFI-*`/`BMI-*` scenario
      rows, and four glossary terms that existed only for bulk import (`Chunk`, `Job`, `Phase`, and sense
      one of `Batch`). The inline bulk endpoints were re-read and stand unchanged.
- [x] **Remove the `owner_system` sentinel** across all 13 sites. Closes SB-9. Per Q5. ✅
      `grep -rc 'owner_system' docs/` returns 0; `ChangeRequest.MayClose` is stated as an `ActorType` test;
      both auto-dispatch paths name a System actor. — **Done, and the acceptance check needed narrowing:
      zero in `docs/spec/`, not in `docs/`.** The ownership ADR names the sentinel three times, because an
      ADR that cannot name what it removed records nothing. Twenty-two sites in `docs/spec/`, not 13 —
      MM-001 counted semantic uses, the grep counts lines.
- [x] **`MediaProfile`: remove `OwnerId`, add `ProfileOrigin`.** Aggregate, `CreateMediaProfileCommand`,
      `MediaProfileCreated`, detail read model. `ProfileOrigin: Platform | Tenant`, set `Platform` by
      `SeedDefaultProfilesService`. ✅ No `OwnerId` on any `MediaProfile` surface; the event-schema change
      names the upcaster it requires. — **Done.** Also the summary read model's no-owner note, the API
      response example, and the seeding steps. The upcaster is stated on the Domain Events table where a
      reader meets the event, and says what it maps the seeded streams to.
- [x] **State the seeded-profile lifecycle rule.** Closes SB-77. ✅ The spec says whether a
      `MediaAdministrator` may deprecate, revise, rename or delete a `Platform`-origin profile, and what
      happens to items conforming to it. **If no ruling covers this, stop and ask — do not invent it.** —
      **Asked. Ruling (Chase, 2026-09-17): immutable — clone to customise.** Written as a new
      § Lifecycle in `mediaprofile.defaults.md`. Deliberately *not* written: a clone command or route, and
      the refusal's status code and error code. Neither is settled, and a route belongs to phase 4b and a
      code to the error catalog.
- [x] **Fix the Registration expiry contradiction.** Closes SB-10. ✅ `RegistrationExpiryRecorded` and
      "a Registration has no expiry" do not both appear. — **Done.** The event came out of the key-events
      list; the no-expiry statement stands, and the domain-model ADR now records it as a decision.
- [x] **Remove `IdentityAcl` as a type; keep the ACL relationship.** Four sites; name
      `HttpExecutionContext` as the translator. Closes SB-11. Per Q6. ✅ `grep -c 'IdentityAcl' docs/`
      returns 0, and the Identity → Media Management relationship is still typed **Upstream / ACL**. —
      **Done.** One of the four sites had typed the relationship plain *Upstream*; it now reads
      **Upstream / ACL** like the others.
- [x] **Correct the reviewer-authorization statement.** `system-architecture.md:742` names
      `ChangeRequest.Reviewers[]`, a field that does not exist. Closes SB-8. ✅ The statement names
      `MediaItem.ReviewSession` and no document says `ChangeRequest` has reviewers.
- [x] **Delete the folder and collection owner-gating rows.** Closes SB-6. Per Q8. ✅ Neither
      `folder.api.md` nor `collection.api.md` states an owner predicate on a write endpoint. — **Done for
      the write rows only.** `collection.api.md`'s *read* row ("Owner, or collection is `Public`") was
      briefly changed and then **put back**: it is outside SB-6, and removing it would have widened read
      access with nothing in its place. It is phase 4b's to settle with a scope and a predicate.
- [x] **Settle `AggregateType` for `RetentionSchedule`.** Closes SB-13. ✅ The inventory has no `—` in the
      discriminator column. **Needs a value; ask rather than invent one.** — **Asked. Ruling (Chase,
      2026-09-17): `media.retentionschedule`** — the convention applied straight, as
      `media.processingjob` and `media.recordtype` do.
- [x] **Classify `RegistrationAmendment` and `Signer`** as entity or value object. Closes SB-14. ✅ Every
      type carrying a shape in § Value Objects appears in the classification. — **Done, both entities**,
      each on the identity-and-lifecycle test the section already states. `Signer` is classified without
      restating its shape: the two documents that give one disagree, and that is SB-37's to settle in
      phase 6, not a disagreement to pick a side of here.
- [x] **Sweep the two dead names** — `MediaChangeRequest` (the type is `ChangeRequest`) and `Media.Api`
      (the host is `Api`). Closes SB-15, SB-16. ✅ Both greps return 0 outside filenames. Files are **not**
      renamed in this phase; note it if the filenames are to follow. — **Done. Seventeen files, far more
      than the "at least four" the finding estimated.** `MediaChangeRequestId` went with it, converging on
      the `ChangeRequestId` the commands already used. **The sweep briefly broke every link into the
      aggregate folder** — the directory is `MediaChangeRequest/` and the replace caught it — and the
      paths were put back; the guard's links check is what would have caught it either way.
      **If the filenames are to follow**, it is the folder and the four `mediachangerequest.*.md` files,
      plus the links in `business-scenarios.md` and `context-overview.md`.
- [x] **Reconcile `ChangeRequest`'s lifecycle.** § Design Notes says "no lifecycle"; § Status transitions
      defines `Open | Resolved | Abandoned`. Closes SB-17. ✅ One statement stands. — **Done: it has a
      lifecycle.** § Design Notes overreached — what it was defending is that the request holds no *review
      decisions*, which is true and is kept. The two sections now say the same thing, and the note
      distinguishes the request's lifecycle from the item's.
- [x] **Enumerate the `Capability` set.** Closes SB-18. ✅ The nine members are listed once, and the API's
      four-value list either matches or the difference is stated as design. — **Done; there is no
      four-value list.** The API already documents all nine and says so. The glossary was the only place
      still calling it contested, and it now enumerates the nine.
- [x] **Phase exit.** ✅ All items ticked; `docs_guard.py` pass; the aggregate inventory is identical in
      every file that states one; re-read every file edited against the phase 2 ADRs. — **Done.** Guard
      passes. **The baseline shrank 209 → 192** and the **structure check reached 0**, which closes SB-67
      early — its ragged tables were in the bulk-import folders, exactly as the ruling predicted. Commit
      `39e2fcfd`, pushed.

## Phase 4 — Authorization ✅ **CLOSED 2026-09-17**

The largest body of writing. Three sub-phases, strictly ordered.

### 4a — The vocabulary ✅ **CLOSED 2026-09-17**

- [x] **Write `shared/api-permissions.md`.** The closed set in `Resource.Verb[.All]`; the grammar; three
      verbs (`Read`, `ReadWrite`, `Manage`); `.All` semantics; how a granted scope reaches a handler.
      Closes SB-70. ✅ Every scope used anywhere in `docs/` is defined here and nowhere else; the file
      states that `.All` does no work on `Folder` and `Collection` and **why**, so the absence is not left
      to inference. — **Done.** Ten resources, one per aggregate carrying an HTTP surface; the resource
      segment is the aggregate's own name, which is a rule rather than a list to maintain. Three calls
      worth knowing before 4b quotes them:
      **(1) The verbs are inclusive** — `Manage` admits what `ReadWrite` admits, which admits `Read`. Each
      endpoint row therefore states the *least-privileged* permission and does not restate the tiers above
      it. Without this, ten tables would each have carried three columns of the same information.
      **(2) `.All` is defined on four resources and deliberately absent on six**, each with its reason
      stated: `Collection` and `Folder` per Q8, `MediaProfile` and `RecordType` because they are
      tenant-wide, `ProcessingJob` because a job belongs to an asset, and `DocumentSigningSession`
      because the session carries no owner in the model. **That last one is stated as a present-tense
      fact, not as an open question** — SB-12 gives it an owner in phase 6, and `.All` is added then.
      **(3) Two resources are short a tier, and the file says so**: `ChangeRequest` has no `Manage`
      (nothing on it overrides another user's state, acts tenant-wide, breaks a lock or disables a guard),
      and `ProcessingJob` has no `ReadWrite` (the pipeline creates and advances a job; the only operation
      a caller directs at one is bypass, which is `Manage` by the tier test).
- [x] **Repoint the role-claims contract.** `magiq-auth-role-claims-requirements.md` names the canonical
      list this file now owns. ✅ The two files do not each enumerate the scope set. — **Done, then
      reversed the same day after Chase challenged it. The reversal is the right answer; see § Session
      log.** The `roles` claim carries **role names**, and `magiq-media` expands them. The contract asks
      for the three names as it always did, and points at `api-permissions.md` for what they grant. The
      two files still do not each enumerate the set — one owns the names, the other owns what they
      confer.

### 4b — The mapping, one aggregate at a time ✅ **CLOSED 2026-09-17**

Ten aggregates. Each is one session's work and closes independently.

- [x] **Add a scope column to all ten `<agg>.api.md` Authorization tables**, and normalise their shape —
      they currently state resource predicates three different ways. Closes SB-69. ✅ All ten tables have
      the same columns in the same order. — **Done: `Endpoint | Permission | Resource predicate`**, with
      the same preamble on every file explaining that the row states the *least-privileged* permission and
      what *None beyond tenant scoping* means. Three of the ten had no table at all (`recordtype`,
      `processingjob`, and `asset`'s was split in half by a blockquote); the others disagreed on column
      headers. The sections were spliced by script so the shape could not drift between files.
- [x] **Map every write command to a scope**, with its resource predicate where the resource is owner- or
      membership-scoped. Closes SB-1, SB-2, SB-3, SB-4, SB-5, SB-7. ✅ No Authorization cell reads `—`;
      **every owner-scoped row carries both a scope and a predicate** — a row with a scope and no predicate
      on an owner-scoped resource is wrong. — **Done.** Predicates were *carried forward*, never invented:
      each is a standing rule the aggregate already states (owner, officer, review roster, edit session,
      participant set, comment author, `ProfileOrigin`). Where the aggregate states none, the cell reads
      *None beyond tenant scoping* rather than an em dash, so the absence is a statement.
- [x] **Map every query to a scope.** Closes SB-68. ✅ Every read route and every query has a `.Read` scope;
      `grep` for a route without one returns nothing. — **Done, and it forced a real consequence.** Read
      access on `Asset` and `MediaItem` is tenant-scoped by design, so their read rows require the **`.All`**
      form — the un-suffixed form would mean *your own*, which those aggregates explicitly do not do.
      `ChangeRequest`, `Registration` and `DocumentSigningSession` have genuinely caller-scoped list
      routes, so both forms are live there.
- [x] **Settle the cascade commands.** `ArchiveFolder` and `ArchiveCollection` get their `Manage`-tier
      assignment and either a resource restriction or an explicit statement that there is none. Closes
      SB-71. ✅ The spec states the answer rather than leaving it to follow from Q5 and Q8. — **Done:
      `Manage` tier, no resource restriction, stated explicitly in both files.** The tier is what restricts
      the operation, because the alternative — an owner predicate — rests on a field that carries no
      authority. The subtree checks (active registrations, ≤ 500 descendants, depth, name uniqueness) are
      separated out as **preconditions, not authorization**, so the two are not read as one.

### 4c — Retire the matrix ✅ **CLOSED 2026-09-17**

- [x] **Delete `shared/authorization-matrix.md`**, only after 4b covers every route it names. ✅ Every
      command in the retired file appears in an `<agg>.api.md` table; the file is gone. — **Done, and the
      gate caught a real gap first.** The matrix names **commands, not routes** — 72 of them, and
      **eighteen have no HTTP route at all**: ten on `Asset` (the processing-pipeline commands, the
      assignment consumer, attach/detach, the version-artifact pair), seven on `MediaItem`
      (`ExpireCheckout`, the two registration-ref commands, the two signing-session link commands,
      `RejectMediaItem`, `UpdateMediaItemConformanceStatus`) and one on `ChangeRequest`
      (`CreateChangeRequest`). **4b had not covered them, and this plan's 4b entry had recorded SB-5 as
      closed anyway — that was wrong.** Each now carries a stated rule in its aggregate's table.
      Fourteen inbound references repointed before deletion; the links check is hard zero, so a missed one
      would have failed the guard rather than rotting quietly.
- [x] **Repoint `spec/README.md` rows 14b and the file tree.** Closes SB-75. ✅ No row calls the retired
      file authoritative, and none describes a row saying "none" as a finding. — **Done.** Row 14b now
      routes the question to the relevant `<agg>.api.md` § Authorization, names `api-permissions.md` as the
      vocabulary, and its *don't look here* column says plainly that **there is deliberately no central
      matrix** — it is generated from the per-endpoint declarations if it is wanted at all. That last
      clause is what stops the retired file being recreated by the next person who wants the cross-cutting
      view.
- [x] **Phase exit.** ✅ All items ticked; `docs_guard.py` pass; the scope vocabulary and the mappings agree
      in both directions — no scope used that 4a does not define, no scope defined that nothing uses. —
      **Done.** Guard passes; baseline shrank 192 → 191. All three checker directions clean: nothing
      required and undefined, nothing required and ungranted, nothing granted and undefined.

## Phase 5 — Cross-file contradictions ✅ **CLOSED 2026-09-17**

The vocabulary underneath these is now settled. Two items are design work rather than reconciliation.

- [x] **The quarantine path.** Rewrite AssetManagement's hard-delete statement; then specify the
      performing component and pipeline step, the move semantics and partial-failure behaviour, the
      bucket's IAM posture, retention on quarantined objects, and a scoped retrieval path. Closes SB-19,
      SB-38. Needs the phase 2 ADR. ✅ One design is stated; `asset.scenarios.md` AM-5, its invariant list
      and Processing's § Pipeline agree. — **Done (`8c9c3a0e`).** Two rulings from Chase: retention is tenant-configurable, defaulting to **90 days** and deliberately *not* `RetentionSchedule` (a rejected upload never became a record, and a standalone upload has no schedule to inherit); retrieval is `GET /v1/assets/{assetId}/quarantine/download` under `Asset.Manage`. The move is **copy → verify → delete**, so the failure mode is a duplicate and never a loss, and the partial-failure case is written down rather than smoothed over. **A contradiction was nearly created here:** `event-store-and-messaging.md` already carried a § Quarantine bucket saying retrieval was an out-of-band operator action and objects were never expired — found by grepping the tree *after* writing. Reconciled so the storage document owns the bucket and the scenario owns the flow.
- [x] **Idempotency — write the conformant contract.** Rewrite `api-conventions.md` § Idempotency against
      the IETF draft: cached replay on a completed retry, `409` with a problem body for concurrency only,
      `422` on fingerprint mismatch, `400` for a missing key on an operation that requires one.
      `bulk-operations.md` then becomes correct as written. Closes SB-20, SB-72, SB-73, SB-74, SB-76.
      **This is no longer gated on the SDK** — see the note below. ✅ The four draft cases each have a
      stated response; `bulk-operations.md` and `api-conventions.md` agree. — **Done (`16b3da69`).** Four cases where there was one. The consume-on-`2xx` rule stays and is now load-bearing rather than incidental — it is what cached replay requires — and the concurrent-duplicate race it would otherwise reopen is closed by making the record **two-phase**: `Pending` with the fingerprint before execution, promoted to `Complete` with the envelope on `2xx`, released otherwise. That is the same shape name reservation already uses. Three error codes added; a dangling anchor into the replaced section repaired in `concurrency-and-consistency.md`, caught by the guard.
- [x] **Record the idempotency gap where build status belongs.** Add `Magiq.AspNetCore.Idempotency` to the
      repo `CLAUDE.md` § Known deferred/partial work: the spec states the conformant contract, the
      middleware does replay rejection, and conformance ships with AP-001. ✅ A reader who wants to know
      what the running system does finds the answer in one hop, from the file that is allowed to hold it.

  > **Why this item is no longer blocked.** The spec states **what the system is specified to be**, and
  > deliberately says nothing about whether the code has caught up — that is the rule this whole workstream
  > exists to establish. A spec that describes the conformant contract before the SDK implements it is
  > therefore correct by construction, not premature. The alternative — holding the spec text hostage to a
  > package release in another repo — would mean the one file everyone reads stays wrong for as long as the
  > release takes.
  >
  > **What does not move is the truth of it.** Phase 10 holds the release gate, and this plan cannot reach
  > `done` while that phase is open. Writing the contract is phase 5; making it true is phase 10. — **Done.** The `CLAUDE.md` entry names what the spec states, what the middleware does, and says explicitly **not** to "correct" the spec back to the narrower mechanism while the gap is open.
- [x] **Fix the error catalog's exhaustiveness claim.** Closes SB-22. ✅ Either every endpoint's errors are
      catalogued, or the claim is narrowed to what is true. — **Done.** Narrowed to every code a **write** endpoint produces, and the two things deliberately outside that claim are named so their absence is not mistaken for completeness: uncoded `422 InvalidOperation` refusals, and read endpoints (SB-53's, in phase 6).
- [x] **Reconcile the download guard status sets.** Closes SB-23. ✅ `asset.api.md` and DL-1/DL-2 state the
      same set. — **Done.** DL-1 and DL-2 now allow `VersionArtifact`. `asset.api.md` won because it is the endpoint contract and it states the reason; the scenarios were the looser statement.
- [x] **Remove the `403` from the asset read endpoints.** Four sites, contradicting § Read access is
      tenant-scoped. Closes SB-24. ✅ No read route declares an ownership `403`. — **Done. Three sites, not four** — the list route carried none. The write routes keep theirs, which is correct.
- [x] **Settle `AssetId` generation.** Closes SB-25. ✅ One statement across write model and api. — **Done, and it is not one rule.** The server mints on single and multipart initiate; the caller supplies it, required, on bulk — where re-using the ids is exactly what makes a retried batch safe. The API already said both; the write model's blanket "caller-generated" was the wrong one.
- [x] **Settle `POST /folders/{id}/close`.** The API says no body; the write model and error catalog
      require `closedDate`. Closes SB-26. ✅ One contract, and `ClosedDateRequired` has a request field to
      attach to. — **Done: the route gains a body with a required `closedDate`**, which is what the acceptance check implied by asking that `ClosedDateRequired` have a field to attach to. The business-date versus system-timestamp split is now stated where a caller meets it, and the write model's "unreachable over HTTP" note is corrected for close while standing for archive.
- [x] **Settle the `DEPRECATED` sentinel partition.** Closes SB-27. ✅ `event-store-and-messaging.md` and
      cross-aggregate rule 11 agree. — **Done, and it was never contested — both mechanisms exist and do different jobs.** The per-row `IsDeprecated` flag handles version-level deprecation; the sentinel handles whole-type deprecation and is **inherited by version rows inserted later**, which is what makes it survive unordered delivery. `cascade-rules.md` carried a ⚠ *mechanism is contested* note that the 2026-09 merge-rule work had already resolved; the note outlived the disagreement.
- [x] **Reconcile `202` usage.** Closes SB-28. ✅ The reserved-endpoint list and the bulk statements agree. — **Done, and most of it had already closed.** The bulk half dissolved in phase 3 when the async-import section left. What remained was that the reserved list **named two routes that do not exist** — `/assets/{id}/confirm` and `/items/{id}/signing-sessions`. Both spellings corrected.
- [x] **Settle the JTI store.** The repo `CLAUDE.md` specifies `media-used-jtis`; the spec says validation
      is stateless. Closes SB-29. ✅ One statement. **This one crosses into `CLAUDE.md` — flag it rather
      than silently changing agent instruction.** — **Done, after working out *why* rather than just which side was newer.** Not two competing designs: `CLAUDE.md` was stale. **`jti` is a claim inside the signed token, so it is identical on every request that token makes** — a store rejecting a seen `jti` would refuse a caller's *second* request. It is not a weak control, it is one that cannot be switched on. Replay checks belong to single-use credentials, all of which are `magiq-auth`'s. `jti` stays, logged, never validated. **One thing nobody had asked `magiq-auth` for: the `jti` must be unique per issuance** — added to their contract with an explicit request not to build replay detection. The ADR now carries the reasoning, including that the service-account *JTI replay exemption* is the fossil that produced the confusion.
- [x] **Phase exit.** ✅ All items ticked; `docs_guard.py` pass.

## Phase 6 — Close the context gaps ✅ **CLOSED 2026-09-18**

~30 findings, one bounded context at a time. **DocumentSigning first** — it has the most and is least
entangled. **This phase writes new specification**, so standing rule 2 governs it: where no ruling covers
a gap, ask.

- [x] **DocumentSigning.** SB-30 (saga transport: queue, topic, filter policy, visibility timeout, DLQ),
      SB-31 (signing budget value), SB-32 (saga acting identity), SB-33 (lag class), SB-34 (webhook
      dedup), SB-36 (cancellation actor), SB-37 (identifier types), SB-48 (what drives link/unlink), and
      **SB-12 + SB-35 — the two design decisions deliberately moved out of § Open Questions**: what
      identifies a session's owner, and whether signers act in sequence or in parallel. ✅ Every route,
      command and read model resolves without reference to a decision not yet taken.
- [x] **Processing / AssetManagement.** SB-39 (bypassed job read state), SB-40 (query handler name),
      SB-41 (rebuild path), SB-58 (rendition lifecycle). ✅ As above.

> **Both boxes were done and never ticked** — verified finding by finding against the tree on 2026-09-18,
> all twelve `CLOSED`. The work landed in this plan's own commits: `e814365a` (phase 6.1, carrying SB-12,
> SB-31, SB-32, SB-33, SB-34, SB-35, SB-36, SB-37, SB-48), `cad7a1fb` + `83c35e01` (SB-30), and `84064fd3`
> (phase 6.2, carrying SB-39, SB-40, SB-41, SB-58). **The phase-exit box below was ticked over the top of
> two open items**, which is how this phase came to look finished while reading as unfinished.
>
> **SB-41 closes as a stated decision rather than a path:** `ProcessingJob` is one of four aggregates the
> CLI replay path does not cover, and the spec now says so with the consequence written down, rather than
> specifying a rebuild that does not exist.
>
> **SB-58 closed and left a contradiction behind it.** `event-store-and-messaging.md:534` gives
> `media-renditions` an unconditional four-tier progression and says the rendition download route answers
> `409 AssetInColdStorage`; `asset.api.md:677` says the renditions bucket has **no** cold-storage lifecycle
> rule and that the refusal therefore cannot arise. Both predate MM-006 — `32ac2b55` wrote the first,
> `5930ec82` the second, and the tiering revert updated the owning file without sweeping the route file.
> **Not ticked into this box, and not MM-006's:** it is a new finding and needs a home.
- [x] **Catalog.** SB-43 (reviewer minimum and de-duplication), SB-44 (`PUT /metadata` null semantics),
      SB-45 (delete-role response code), SB-47 (cross-module filter allowlist), SB-49
      (`MediaAssetReference.Order`), SB-50 (asset-definition auto-default), SB-51 (search lag class). ✅ As
      above.
- [x] **Metadata / Registration.** SB-42 (history predating the projector), SB-52 (retention actor and
      trigger), SB-53 (read-endpoint `errorCode`), SB-59 (`WithMetadata` member set), SB-60
      (name-reservation probe dependency). ✅ As above.
- [x] **Platform / operations.** SB-54 (`deploySearch` condition), SB-55 (staging promote mechanism),
      SB-56 (what "guarded" means at the prod gate), SB-57 (backup and restore verification). ✅ As above.
- [x] **Phase exit.** ✅ All items ticked; `docs_guard.py` pass; **every gap closed by newly-written design
      is listed in § Session log**, so a later review knows which text has never been reviewed by anyone.

## Phase 7 — Clean the ADR tree ✅ **CLOSED 2026-09-17**

- [x] **Strip history and status residue from the ten existing ADRs** — 5 "Corrected", 6 "Decided <date>",
      12 "superseded", 1 revision note, 8 build-status phrases, one `(Chase)` attribution. Closes SB-62.
      ✅ An ADR records a decision and its rationale and does not narrate its own editing.
- [x] **Phase exit.** ✅ `docs_guard.py` pass; the citations check still returns hard zero across `adrs/`.

## Phase 8 — Sweep the residue ✅ **CLOSED 2026-09-17**

- [x] **Delete the cross-region RTO/RPO rows** and state single-region explicitly. Closes SB-21. Per Q3.
      ✅ `operations.md` does not state a cross-region target. — **Done.** § DR now states both targets are
      single-region and says there is no second region to fail over to, so the absence is a statement
      rather than a hole. § DR Runbook — full region failure says the escalation is a decision to be
      taken, not a documented failover.
- [x] **Fix the fenced diagrams.** The context map styles `SagaOrchestrator.DocumentSigning` `:::dead` and
      labels an edge *"adapter not built — see note"* pointing at a note that no longer exists; plus the
      `deploySearch` and `🟡 deferred` labels, the Processing pipeline's dangling `§ Service Boundaries`
      pointer, `<<NOT IMPLEMENTED>>`, and the `api-conventions.md` idempotency code block that contradicts
      the `2xx`-only rule. Closes SB-64. ✅ No fenced block asserts build status or points at removed text.
      — **Done.** `:::dead` and `<<NOT IMPLEMENTED>>` return nothing tree-wide. **`deploySearch` is not
      residue and stays** — it is a real deployment flag defaulting to `false`, and `consistency-model.md`,
      `system-architecture.md` and `persistence-and-eventing.md` all state the conditional OpenSearch path
      correctly. The dangling pointer was the last one: `processingjob.write-model.md`'s ⚠ claimed
      `Succeeded` is unreachable because `AssetProcessingWorker` has no trigger, and pointed at
      `context-overview.md § Service Boundaries` — which now states the opposite, that `ProcessingWorker`
      runs the pipeline via that worker. Deleted. The build-status fact behind it is already recorded in
      the `Z:\` docs project's `use-cases.md` (P-1), which is its home.
- [x] **Remove every date.** Row stamps, prose history, and the `_Last reviewed:_` / `_Last updated:_`
      headers tree-wide. Closes SB-65. Per Q4. ✅ **The dates baseline is 0** — the clearest single signal
      this plan produces. — **Done, and it took a second pass.** Stripping the dates alone left undated
      change-narration, which the rule bans just as firmly; per Chase's ruling the narration went with
      them.
- [x] **Move the eight embedded open questions out of spec prose.** Closes SB-66. ✅ No spec file poses a
      question. — **Done. Three, not eight.** 0 open-question headings; 6 prose matches of which 3 are
      domain language (*"the request is still open"*), 1 interrogative that is a legitimate decision
      criterion in `retentionschedule.design-decisions.md`, and **179 `⚠` markers that stay** — they are
      durable design caveats, and README row 14 documents that convention. The three real ones:
      `mediachangerequest.api.md`'s `sortBy=resolvedAt` speculation about a third sparse GSI (cut; the
      `400` and why it does not fall back are kept); `processingjob.read-model.md`'s *"flagged as
      unresolved"* pointer (cut); and the `IsDeprecated` carrier question, which needed a ruling.
      **Two rulings from Chase, both now ADR-backed:**
      **(1) deprecated fields compile as tombstones.** `CompileTemplateAsync` emits them with
      `IsDeprecated: true` and counts them toward collisions; `CompiledMetadataField`,
      `MediaProfileSnapshotField` and `CompiledMetadataFieldDto` all carry the member. Filtering would
      have un-qualified a surviving bare name the moment a contributor deprecated its field — a silent
      rename of a key items already store — and would have broken *deprecate → publish → remove* as a
      drain. Rationale in `adrs/metadata-schema-composition.md` § A deprecated field is compiled as a
      tombstone.
      **(2) rendition dimensions cross every boundary.** `Width`/`Height` added to
      `ProcessingRenditionDto` and `RenditionResultDto`, nullable and null where a rendition has no
      spatial extent. They are measured at generation time and unrecoverable without re-probing S3.
      Rationale in `adrs/asset-storage-and-processing.md` § Rendition dimensions cross every boundary.
- [x] **Fix the ragged table.** Closes SB-67. ✅ The structure baseline is 0. — **Done, by Q2's deletion.**
      Verified on inspection: structure baseline is 0, eight of the nine hits were in the bulk-import
      folders and the ninth went with the `operations.md` table.
- [x] **Phase exit.** ✅ All items ticked; `docs_guard.py` pass. — **Done.** Guard passes on all five
      checks. Also swept in this phase, outside the five boxes: `README.md` row 3 claimed *"two
      inventories still disagree — 10 vs 12"* (phase 3 made them agree) and row 7b pointed at
      `catalog-domain-invariants.md` as having *"four rule claims false"* (phase 7 fixed it) — both rows
      rewritten, plus three narration fragments in rows 7c, 13 and 14e. `domain-model.md`'s
      no-expiry note lost its appeal to a C# doc comment and its *"Recorded in …"* pointer.

## Phase 9 — Re-baseline ✅ **CLOSED 2026-09-17**

- [x] **Run every detector against a tree that now contains five new ADRs and
      `shared/api-permissions.md`,** neither of which existed when the baselines were taken. ✅ Citations 0,
      links 0, dates 0, structure 0, build-status baseline shrunk to whatever genuine design statements
      remain. — **Done. All five checks return 0, and the build-status residue turned out to be nothing.**
      Every one of the 7 baselined hits read as a false positive on inspection: five were `deferred` in
      *"the deferred quota is charged at assign time"* — domain vocabulary, not delivery status — and one
      was `not registered` in *"an event that is published but not registered never reaches the
      projectors"*, a rule about the message bus. **The pattern was wrong, not the prose**, so the fix is
      in the guard rather than the baseline (below). The seventh was real and is fixed in the tree.
- [x] **Shrink the baseline to its floor** and record what is left and why. ✅
      `.github/docs-guard-baseline.tsv` contains only entries someone has read and judged to be design.
      — **Done: the floor is 0.** `--update-baseline` wrote **0 accepted entries**. The arc is
      **209 → 192 → 187 → 7 → 0**, and it only ever shrank. Nothing is left, so there is nothing to
      justify — which is the outcome the file's own header asks for.
      **Two patterns were narrowed** to get there, both because they matched domain vocabulary:
      `deferred` now matches only the delivery sense (`deferred to|until a later|future|subsequent…`,
      `deferred indefinitely`, `🟡 deferred`) instead of the bare word, and `registered` is out of the
      `not (yet) …` alternation entirely. **Regression-checked against thirteen strings**: all eleven real
      forms — *not built*, *not wired*, *not yet deployed*, *nothing deploys it*, *skeleton only*, *no
      Lambda, no queue*, *specified and not implemented*, *deferred to a later release*, *deferred until a
      future phase*, *deferred indefinitely* — still fire; the two domain uses no longer do. **The earlier
      `(?!\s+to\s+assign)` carve-out is the tell**: someone had already hit this and patched one phrasing,
      which left four others firing.
- [x] **Confirm the guard's scope still matches the rule.** Dates and build status run over `docs/spec/`
      only, by design — an ADR legitimately records when a decision was taken. ✅ Stated in the script's
      docstring and still true. — **Done.** `check_build_status` and `check_dates` both iterate
      `md_files(SPEC)`; citations, links and structure iterate `md_files(DOCS)`. The docstring's scope
      note and its five-check table both match the code.
- [x] **Phase exit.** ✅ `docs_guard.py` pass with a baseline that only ever shrank. — **Done.** Pass on
      all five checks with an empty baseline. **Note what that changes:** with nothing baselined, the two
      baselined checks now behave as hard zeros in practice. The mechanism is unchanged — a new hit still
      fails the run — but there is no longer any accepted residue to hide behind, which makes the next
      failure a real finding rather than a queue-jump.

## Phase 10 — SDK release gate ⛔ **blocked on `AP-001`**

**Phases 0–9 can all be completed without this phase.** Nothing here is documentation work — it is the
step that makes the idempotency contract phase 5 wrote actually true of the running system, and it cannot
be done from this repo.

**This phase is the reason the plan cannot be marked `done`.** Every other box can be ticked while the
`Magiq.AspNetCore.Idempotency` contract is still replay-rejection. That is an acceptable state for the
*spec* and an unacceptable state for the *plan*, because a plan that closes here would claim SB-20, SB-72,
SB-73, SB-74 and SB-76 are closed when the system does none of it.

**The platform rule now agrees with that framing.** Since 2026-09-18 the spec is authoritative and a gap
between it and the code is a defect in the code — so a spec that is ahead is the expected state, and this
phase is simply the work the spec is ahead *of*. What changed is the remedy: where the middleware and the
contract differ, the contract does not move.

**Dependency:** `AP-001` in `aspnetcore-platform` — currently a review with no plan, which resolves as
unmet. Re-run the gate at every session start; repoint `depends-on` at AP-001's plan id once it exists.

> **Re-reviewed 2026-09-18 after MM-006 closed.** Phases 0–9 are now all complete — phase 6's two boxes
> were done and unticked, verified finding by finding. **This is the only phase left, which is what the
> plan always said would happen.** Two of its five boxes changed underneath it: box 3's rule was inverted
> platform-wide, and box 4 acquired a cross-reference. Boxes 1, 2 and 5 are untouched and still wait on
> `AP-001`.

- [ ] **AP-001 ships.** Its plan reaches `done`: `IIdempotencyStore` carries the response and the
      fingerprint, `MarkAsync` runs after the pipeline on `2xx` only, the key is scoped to the operation,
      and `409` means concurrent. ✅ AP-001's plan front-matter reads `status: done`.
- [ ] **Packages published and consumed.** The `.Abstractions` and plugin packages publish, and
      `MagiqPlatformVersion` bumps in this repo's `Directory.Packages.props`. Merging is not shipping —
      this SDK is consumed as NuGet, not by project reference. ✅ The resolved version is not `1.1.3.5`.
      **Consider shipping with ADO #35085 (`GuidFactory` byte order), which needs the same release chain —
      paying it twice is avoidable.**
- [ ] **Confirm the delivered middleware matches the spec.** Read it against the contract **in all five
      files that state it** — `api-conventions.md` § Idempotency (the owner),
      `concurrency-and-consistency.md`, `error-catalog.md` (the three codes), `recordtype.api.md` and
      `mediachangerequest.api.md`. Where they differ, **AP-001 reopens.** ✅ A stated confirmation, naming
      the version checked.
      > **Correcting the spec to the middleware is not an available outcome**, and this box used to say it
      > was. The repo `CLAUDE.md` § *When the spec and the code disagree* now makes the spec authoritative
      > and the divergence a code defect; taking the other branch here would revert phase 5.
- [ ] **Remove the deferred-work entry, and the citation that depends on it.** The `CLAUDE.md` § Known
      deferred/partial work line added in phase 5 comes out, because it is no longer true — **and
      `CLAUDE.md` § *When the spec and the code disagree* cites that entry as its worked example of a
      deliberate gap**, so the citation goes or is repointed in the same edit. ✅ `grep -c 'Idempotency'
      CLAUDE.md` reflects only live statements, and no section points at a removed one.
- [ ] **Phase exit.** ✅ All items ticked. **Only now may this plan move to `done`.**

---

## Closing out

This plan moves to `done` only after **Chase agrees the work is implemented and complete** — not when the
last box is ticked. The close-out card comment records every branch it was committed to. The review and
plan folders then archive together into `_archive/reviews/MM-001-spec-baseline/` and
`_archive/plans/MM-003-spec-baseline/`, each prefixed with its own id, both keeping the workstream name.

### The hard gate

**`status: done` requires phase 10 closed. There is no version of "documentation complete" that closes
this plan.**

Phases 0–9 are documents and can all finish while `Magiq.AspNetCore.Idempotency` still does replay
rejection. When they do, the plan is **substantially** complete and **not** complete: the spec will state
an idempotency contract the system does not honour, and five findings — SB-20, SB-72, SB-73, SB-74,
SB-76 — will look closed in the text while being open in fact.

That state is correct for the spec and wrong for the plan, and the two must not be conflated. So:

- **Do not set `status: done`** while any phase 10 box is open, however complete the rest looks. The card's
  status is projected from this front-matter and nothing else, so this line is the only mechanism.
- **When phases 0–9 finish, comment the card** saying documentation is complete and the plan is held on
  phase 10, naming `AP-001` and what it is waiting for. Leave the status `active`. A plan parked on a real
  external dependency is not the same as a plan nobody is working, and the card comment is what tells the
  difference.
- **If the SDK work is abandoned rather than shipped**, that is a decision, not a drift. Phase 5's spec
  text either reverts to the mechanism the platform actually provides, or the plan closes `superseded`
  with the reason recorded. **Silently ticking phase 10 to tidy the list is the one outcome that is not
  available.**

`_archive/` and `plans/README.md` did not exist when this plan was written. Create them at close-out and
hand-over respectively.

---

## Session log

**2026-09-16 — plan authored.** Consumes MM-001 (77 findings, ten questions answered). Dependency gate run:
`depends-on: [AP-001]` unmet — a review with no plan — so status is `active` under the partial-blocking
rule rather than `blocked`, with the single dependent item marked in phase 5. Phase 0 is written and
awaiting commit; phase 1 is closed. Branch `spec/initial-alignment-work`, cut from `spec/initial-alignment`
— not a GitFlow branch, accepted deliberately for this workstream.

**2026-09-16 — SDK dependency restructured (Chase).** Phase 5's idempotency item was un-blocked and the
dependency moved into a new **phase 10**. Rationale: the spec states what the system is *specified* to be
and says nothing about whether the code has caught up — so writing the conformant contract ahead of the SDK
is correct by construction, and holding the text hostage to a package release in another repo would leave
the most-read file wrong for the duration. Added in the same change: a phase 5 item recording the gap in
the repo `CLAUDE.md` § Known deferred/partial work, which is where build status is allowed to live.

**MM-001 was not edited.** The review is `done` and frozen; this is an execution decision and belongs on
the plan side. Anyone reading MM-001's Q9 will find it says phase 5 is blocked — that framing is superseded
by this entry, and the review is not rewritten to match.

**2026-09-17 — session picked up MM-003; dependency gate re-run; phase 0 reconciled against the repo.**

*Dependency gate.* `depends-on: [AP-001]` still resolves **unmet** —
`aspnetcore-platform/reviews/idempotency-conformance/idempotency-conformance-review-2026-09-16.md` reads
`status: draft`, `outcome: pending`, and `aspnetcore-platform/plans/` is empty. No plan id exists to
repoint at, so `depends-on` is unchanged and status stays `active` under the partial-blocking rule.

*Hand-over state was stale.* The execution prompt records phase 0 as "written and awaiting commit". It is
not: the guard, its baseline and its workflow were committed and pushed before this session
(`02f03c7e`, `4ad38621`), and the `__pycache__` orphan was already gone. Phase 0's fourth box is ticked on
inspection rather than on work done here. **Nothing was re-done on the strength of the prompt** — the repo
was read first, which is why the divergence surfaced before an edit rather than after one.

*Phase 0 is held on one thing only: proof the workflow ran.* The guard passes locally, the workflow's
trigger covers `spec/**` and both commits touched trigger paths, so runs should exist — but this machine
cannot see them. `gh` is authenticated as `cramone`, whose only org is `magiqsoftware`;
`Sprbrk-Standard/mgq-magiq-media` returns 404 on both `gh run list` and `gh api repos/...`, and the browser
pane is denied github.com.

*Ruling (Chase, 2026-09-17): phase 2 starts without the CI proof.* Offered four ways to confirm the run —
read the Actions tab himself, authenticate `gh` against `Sprbrk-Standard`, unblock the browser pane, or
proceed on the local pass alone — he chose to proceed, with the plan's own "do not start phase 2 before
the workflow has run green" stated in the option he picked. **Recorded here as a deliberate waiver, not a
skipped step.** What it costs: phase 2's edits land unchecked by CI, exactly as every edit before phase 0
did, and the negative test proving the guard fails a run is still unwritten. What it does not change:
`docs_guard.py` runs locally at every phase exit, and the baseline may still only shrink. **Phase 0 box 3
stays open** and is the first thing to close when CI becomes visible — if that run comes back red, phase
2's output is what it lands on.

*Flagged, not acted on.* `CLAUDE.md` in the repo is dirty in the working tree with the `todos.md`
retirement repointing (three hunks: the file-map row, the "where it goes instead" table, and two prose
pointers). That is 2026-09-16 work from another thread, not an MM-003 item, and it has not been committed,
staged or reverted here.

**2026-09-17 — phase 2 closed. Five ADRs written, one existing ADR narrowed.** Commit `6b5f45ad` on
`spec/initial-alignment-work`, pushed. Guard passes; the baseline stayed at 209 and did not grow.

*The collision phase 2 walked into, and how it was settled.* The ADR tree is organised **by topic**, and its
own § Adding a new decision says to add a decision as a section of the topic document it belongs to.
`adrs/ownership-and-authorization.md` already answered the question the new ownership ADR was written to
answer — what an owner identifier means, where an access check belongs — and parts of it are superseded by
the ruling: the change-request close rule, the media-profile classification, the seeder's use of the
sentinel. **Two ADRs both defining an owner identifier is the SB-9 failure mode**, so this was put to Chase
rather than resolved in place.

**Ruling (Chase, 2026-09-17): new file, and narrow the old one in the same phase.** Done both ways round —
`ownership-and-system-authority.md` now owns what an owner identifier means and how system authority is
carried; `ownership-and-authorization.md` is retitled *Ownership, Provenance & Custody* and keeps what is
still only its: the *would-an-admin-still-be-bound* test, the per-aggregate classification, and the `Asset`
custody decision, which nothing in MM-001 touches. The superseded passages were **deleted, not marked
superseded** — the diff is the history. Its ⚠ detach blocker and its dates are untouched: they are phase 7's
residue, and widening this edit to catch them would have been the diversion rule in reverse.

*Where the ADRs departed from the plan's wording, and why.* Three places, each recorded on its item above:
the ownership ADR names the sentinel's sites by file and kind rather than by line; the permission ADR takes
the privileged-commands **reasoning** and leaves the enforcement column behind; the quarantine and
idempotency ADRs carry their unresolved specification work as **consequences the decision commits to**
rather than as open questions, which spec purity forbids and which phases 5 writes properly.

*Not done, deliberately.* No ADR asserts a value the rulings do not supply. The foundational ADR carries no
`AggregateType` column, so `RetentionSchedule`'s missing discriminator is still exactly one open item in
phase 3 rather than two. Nothing in phase 3 was started.

**2026-09-17 — phase 0 closed, phase 3 closed.** Commits `8f422e42` / `5a324400` (the guard's negative
test and its revert) and `39e2fcfd` (phase 3), all pushed.

*Phase 0 is finally shut.* Chase confirmed the green run, and the negative test then ran for real: a
throwaway spec file carrying two citations was pushed, the run failed, and the file was reverted. The guard
is proven in both directions, which is what the box asked for and what the previous attempt never did.

*Two rulings taken before phase 3 started, so nothing was invented mid-sweep.* `RetentionSchedule`'s
discriminator is `media.retentionschedule`; a `Platform`-origin media profile is **immutable** — no revise,
rename, deprecate or delete, and a tenant that wants a variant authors its own. Both were put to Chase with
the alternatives, because both items say ask rather than invent.

*Where phase 3 stopped short, deliberately.* Three places, each on its item above: the collection **read**
row was reverted after being changed, because removing an ownership predicate without putting a scope in
its place widens access and 4b owns that; the seeded-profile rule states the lifecycle but **not** a clone
route or a refusal code, neither of which is settled; and `Signer` is classified without a shape, because
the two documents that state one disagree and that is SB-37's.

*Corrections to the finding set's own numbers*, recorded because the next reader will grep and get
different counts: the bulk aggregates were **eight** files, not six; `owner_system` was **22** lines in
`docs/spec/`, not 13 sites; `MediaChangeRequest` was **17** files, not "at least four". None of these is a
new defect — the work is the same work, and the estimates were low.

*One acceptance check was narrowed.* SB-9's is written as `grep -rc 'owner_system' docs/` returning 0. It
returns 0 for `docs/spec/` and 3 for `docs/adrs/`, all in the ADR that records the removal. The check is
read as scoped to the spec tree; an ADR that cannot name the thing it removed is not a decision record.

*Closed early, by someone else's work.* **SB-67** — the ragged-table finding parked in phase 8 — is closed:
the structure baseline is 0, because eight of its nine hits were inside the bulk-import folders that Q2
deleted and the ninth went with the `operations.md` table. Phase 8's item can be ticked on inspection.

**2026-09-17 — phase 4a closed.** Commit `d9d3c0a1`, pushed. Guard passes, baseline unchanged at 192.

*The vocabulary is written and the contract is repointed.* `shared/api-permissions.md` now owns the closed
set; `magiq-auth-role-claims-requirements.md` points at it and enumerates nothing.

**One thing needs Chase's eye before it travels.** Repointing the `magiq-auth` contract is not a
cross-reference tidy — under Q1 the `roles` claim carries **permissions rather than role names**, expanded
at token issue. That changes what an external team was already asked to build: the three role names they
were given are no longer a contract, only a suggested composition. The ask is smaller in some ways (no
role-name agreement needed) and larger in others (the identity provider must expand roles to permissions
before issuing). **The document has been rewritten to say so, but nobody has told that team.**

*A tier decision 4b will lean on.* The verbs are **inclusive** — `Manage` ⊃ `ReadWrite` ⊃ `Read` — so an
endpoint row states only the least-privileged permission that admits the call. This is what keeps 4b's ten
tables to one Authorization column instead of three, and it is stated in the vocabulary file rather than
left to each table to imply.

*Two absences stated rather than left to inference*, which is the SB-9 lesson applied: `.All` is undefined
on six of the ten resources and each says why, and two resources are short a verb tier and say why. The
`DocumentSigningSession` case is the delicate one — it has no owner *in the model today*, so the file
states that as a present-tense fact rather than as a question, and phase 6 adds `.All` when SB-12 gives it
an owner.

**2026-09-17 — 4a's delivery half reversed (Chase).** Commit `3e1a4400`, pushed. Guard passes.

*What was wrong.* Q1 says the permission set "is the canonical list `magiq-auth` must issue in the `roles`
claim". That was read as settling **two** decisions when it settles one. The **vocabulary** decision — the
endpoint contract is `Resource.Verb[.All]` — is Q1's and stands untouched. The **token payload**
decision — whether the claim carries permissions or role names — is independent, and was taken by
inference rather than by ruling.

*Chase's challenge, and why it wins.* A permission names an operation only magiq-media defines, so it is
magiq-media's ubiquitous language. Putting it in the identity provider pushes a downstream context's
vocabulary upstream, into a context that cannot validate or refuse it — and it compounds, because every
sibling Magiq application does the same until the identity provider holds a union of terms it does not
understand. **The context map already settles this:** Identity is typed *Upstream / ACL*, and
role-to-permission expansion is exactly the translation that layer exists to perform. Issue permissions
instead and the ACL has nothing left to translate, while the upstream has been made to conform to the
downstream.

*The ADR's original argument was also simply wrong.* It rejected roles because "a role is a bundle whose
membership the other side can change." Under this model magiq-media owns the mapping, so magiq-auth
cannot change what a role means — only who holds it, which is the point of having roles. That paragraph
is replaced with the bounded-context argument.

*What it costs, recorded rather than waved away.* The audit property: reconstructing what a caller could
do at a past moment now needs the token **and** the mapping as it then stood. The mapping is small,
versioned in the repo and changes rarely, which makes the loss acceptable, not absent.

*What did not move.* The vocabulary, the grammar, the three inclusive verbs, the `.All` semantics and all
ten of 4b's future tables. They read `MediaProfile.Manage` under either model, which is why this reversal
cost one commit rather than a phase.

**A gap the mapping exposed, and it needs a ruling.** Writing the role → permission mapping made role
coverage checkable for the first time, and **the three roles do not reach the whole vocabulary**: the
`Manage` tiers on `Asset`, `MediaItem`, `Collection`, `Folder` and `ProcessingJob`, and every `.All` form
except `Registration.Manage.All`, are granted by no role. So archiving a folder, purging a version and
deleting an asset are currently **System-only**. That is stated as a present-tense fact in
`api-permissions.md` rather than left implicit — but it is almost certainly not the intent, and
**inventing the missing grants is exactly what standing rule 2 forbids.** The right moment to settle it is
at the end of 4b, when every endpoint has a permission and the real demand is known. **Do not extend the
role set before then, and do not let 4b quietly assume a grant that no role makes.**

**2026-09-17 — 4b closed.** Commits `313f8aeb` (eight aggregates) and `ca79f343` (the last two, plus the
bidirectional check). Guard passes throughout.

*Two rulings taken mid-phase, both because a rule Q5 removed had left a row unanswerable.*

**Collection reads (Chase): `Visibility` governs listing, not access.** The old row read *"Owner, or
collection is `Public`"*, and Q5 took the owner half away, leaving `Private` distinguishing nothing. The
ruling makes `Visibility` a discovery control — `Public` lists publicly, `Unlisted` is reachable by id,
`Private` is hidden from listings and still readable by id. **The spec now says plainly that a collection
which must be unreadable by other tenant members is not expressible in this model**, because the
alternative was to leave a reader assuming `Private` meant private.

**Signing-session predicate (Chase): `InitiatedBy`.** Cancel and both reads were gated on an owner SB-12
says does not exist. `InitiatedBy` is the one identity the session carries — immutable, and narrower than
any owner phase 6 might introduce, so that phase widens rather than corrects. **My first suggestion here
was wrong and was withdrawn**: predicating on the item's checkout would have stranded sessions whose lease
lapsed, and handed cancellation to whoever took the checkout next. The rejected option is recorded in the
file so it is not re-proposed.

*Two corrections to 4a that only 4b's evidence could produce.* **`ProcessingJob` carries no permissions
at all** — nothing in it is HTTP-reachable, so its six commands and two queries require a System actor
instead; nine resources carry permissions out of ten aggregates. And the `.All` read consequence above,
which 4a had not anticipated.

*The bidirectional check now runs as a script* (`check_perms.py`, in the session's working directory, not
the repo). It reports: **no permission used by an endpoint is undefined**, and every permission defined
but unreferenced is either the widened `.All` counterpart of a row or a lower tier an inclusive verb
already carries — which the vocabulary file now states, so the list is not mistaken for dead entries.

**The role-coverage gap is now exact, and is the one thing 4b hands forward.** Nine permissions that an
endpoint requires are granted by no role, so the operations behind them are **System-only today**:
hard-deleting an asset, every asset and media-item read route, publish / withdraw / delete / purge /
force-release, bulk metadata update, reading a change request, archiving a collection or a folder subtree,
and initiating or cancelling a signing session. The list is in `api-permissions.md`. **This is the ruling
the end of 4b was supposed to make possible, and it is now ready to take** — the demand is known, so
extending the role set is no longer guesswork. It was deliberately not taken here.

**2026-09-17 — the role-set ruling, taken. A fourth verb and a fourth role.** Commit `66853930`, pushed.
Guard passes; all three bidirectional checks clean.

*Three decisions (Chase).* The five baseline permissions go to `MediaContributor` — without them a
contributor cannot read an item they did not create, edit one they have checked out, or start a signing
session. The four `Manage` tiers go to `MediaAdministrator`. And **the `MediaItem.Manage` bundle is
split**, because it conflated editorial authority (publish, withdraw) with disposal authority (delete an
item, purge a retained version), and no role assignment could separate them — the permission is the unit a
role composes from.

***`Dispose` had to sit outside the inclusive chain, and that is the interesting part.*** A fourth rung
would not have worked: in an inclusive chain every rung carries the ones beneath it, so destruction placed
above `Manage` is granted to whoever holds the rung above, and placed below it drags governance down. So
`Dispose` is **carried by nothing and carries nothing** — it does not even carry the read needed to see
what is being destroyed. A disposal grant is *composed* by a role from `Dispose` plus a read, which is why
`DisposalOfficer` lists its reads explicitly.

**The cost is that the vocabulary is no longer a simple ladder**, and a reader who assumes it is will be
wrong about exactly one thing. Stated in three places for that reason: the vocabulary file, and both
aggregates that carry `Dispose`. It exists only on `MediaItem` and `Asset`, where permanent destruction
exists — archiving a subtree is reversible and deprecating withdraws from use without destroying what was
filed, so both stay `Manage`.

*Four roles now, not three*, so the `magiq-auth` contract changed again — `DisposalOfficer` is a new name
that team has to be able to issue. The contract explains the administrator/disposal split in the one place
someone assigning roles will read it, and says plainly that a tenant not needing the separation can assign
both to one person.

*The coverage gap 4b handed forward is closed.* **Every permission an endpoint requires is granted by some
role, and every permission a role grants is defined.** The checker (`check_perms.py`, session working
directory — not the repo) now models `Dispose` as a non-tier and verifies all three directions. Worth
rebuilding rather than trusting: an earlier quick patch to it produced a bogus resource key and would have
reported a false pass.

**2026-09-17 — 4c closed, and with it phase 4.** Commit `628ce900`, pushed. Guard passes; baseline
192 → 191.

*The gate did its job.* 4c's first box says to delete the matrix **only after 4b covers every route it
names** — and checking that rather than assuming it found a real hole. **The matrix names commands, not
routes: 72 of them, and eighteen have no HTTP route at all.** 4b had covered every *route* and none of
those eighteen, while this plan's 4b entry recorded SB-5 as closed. **That entry was wrong when written,
and is corrected above rather than quietly fixed.** Each of the eighteen now carries a stated rule in its
aggregate's table, with the reason spelled out: *not being routable is a deployment property; requiring a
System actor is the specification* — a command whose only protection is that nothing routes to it is
protected by an accident of wiring, and a later release exposing one would silently unguard it.

*Fourteen inbound references repointed before deletion*, across four ADRs and eight spec files. The
links check is hard zero, so a missed one would have failed the guard rather than rotting quietly — which
is the first time the phase-0 guard has actively protected a structural change rather than just passing.

*The clause that matters most in `spec/README.md`* is not the repointing but the sentence added to row
14b's *don't look here* column: **there is deliberately no central matrix.** Without it, the next person
wanting a cross-cutting view rebuilds the file this phase just retired.

**Phase 4 is closed.** The vocabulary exists, all ten aggregates declare their permissions and predicates,
every permission is reachable from a role, and the enforcement audit that started this is gone.

**2026-09-17 — phase 5.1 closed: the quarantine path is specified.** Commit `8c9c3a0e`, pushed.

*Two rulings (Chase).* Retention is a tenant-configurable period defaulting to **90 days**, deliberately
**not** `RetentionSchedule` — a rejected upload never became a record, and a standalone upload has no
schedule to inherit. Retrieval is `GET /v1/assets/{assetId}/quarantine/download` under `Asset.Manage`.

*The five things Q7 required are all stated.* Performing component and pipeline step; move semantics as
copy → verify → delete, so **the failure mode is a duplicate and never a loss**; idempotent and re-runnable;
the bucket's access posture; retention; and the retrieval path. The partial-failure case is written down
rather than smoothed over: until the delete succeeds an infected object remains in `media-originals`, and
what bounds it is that `ContainsVirus` is terminal and no download route admits that status.

*A contradiction I nearly created, and the lesson from it.* `event-store-and-messaging.md` already carried
a § Quarantine bucket section stating that **retrieval is an out-of-band operator action** and that objects
are **never expired** — both directly against the rulings above. It was found by grepping the tree for the
concept after writing, not before. **Reconciled rather than duplicated:** the storage document keeps the
bucket's posture and retention, the scenario keeps the flow and points at it. *Grep the whole tree for a
concept before writing about it; a finding names the sites it found, not the sites that exist.*

**Raised as a new review, not worked here: MM-004 `storage-keys`.** That same file surfaced a live trap —
`Asset.StorageKey` is stamped once and never re-derived, so after a quarantine move it names the wrong
bucket. Chasing it found the field is **specified three ways** (bucket + key in the write model and
domain-model inventory, key-only in the read model, single-bucket in the generator), disagrees with itself
across two events in one file, and is denormalised into five places — while the read model already carries
`BucketName` separately. **None of that is an MM-001 finding**, so under standing rule 4 it went to a
review rather than into this plan. Chase routed it 2026-09-17. **Nothing MM-003 has committed depends on
the outcome**: the quarantine retrieval route derives its key rather than reading the stored one, which is
correct under every option MM-004 considers.

**2026-09-17 — phase 5 closed.** Commits `8c9c3a0e`, `16b3da69`, `59bca0cc`, `83a0b69b`, all pushed.
Guard passes; baseline 192 → 190.

*Four of the eleven items turned out not to be what the finding described*, and that is the pattern worth
carrying into phase 6. **SB-27** was not contested at all — both mechanisms exist and do different jobs,
and the ⚠ note saying otherwise had outlived the work that reconciled them. **SB-28** had mostly closed
itself when phase 3 removed the async-import section; what remained was two route names that do not exist.
**SB-24** was three sites, not four. **SB-25** has no single answer — the server mints on one route and
the caller supplies on another, which the API already said and the write model flattened.

*The JTI item was the one worth slowing down on.* Presented as a two-sided contradiction, it was a stale
instruction file against four consistent spec files and a verified teardown. **But taking the newer side
would have recorded the right answer for the wrong reason.** `jti` is a claim inside the signed token, so
it is identical on every request that token makes; a store rejecting a seen `jti` refuses a caller's
*second* request. It is not a weak control, it is one that cannot be switched on. That reasoning is now in
the ADR, along with the observation that the service-account *JTI replay exemption* is the fossil that
produced the confusion — an exemption implies a rule, and the rule was never viable for any actor type.

**One thing nobody had asked `magiq-auth` for**: the `jti` must be unique per issuance. `magiq-media`
cannot detect a collision, and a repeated value collapses two sessions into one line in an audit trail on
a platform whose customers are audited. Added to their contract, with an explicit request **not** to build
replay detection — because the obvious reading of "we need unique `jti`s" is exactly the thing that would
break the API.

*Two spec-purity notes.* The idempotency rewrite removed a large body of enforcement-audit prose — a C#
snippet of current middleware behaviour, a § *What it actually does*, and a warning that any text claiming
cached replay "is describing a mechanism this platform does not have". All of it was build status. And the
guard caught the dangling anchor that removal left behind, which is the second time this phase it has
protected a structural edit rather than merely passing.

**Phases 0–5 are closed. Six remains of the documentation work**, then 7, 8 and 9 — after which the plan
is held on phase 10 and the hard gate.

**2026-09-17 — verification pass: committed phase 5–6 work checked against the ten ADRs.** Commits
`fef48e8d`, `cad7a1fb`, `83c35e01`.

*Why it was run.* Two errors in one afternoon, the same shape both times: reason from the file the finding
names, without opening the document that owns the decision. The first invented a cold-storage break that
`asset-storage-and-processing.md` had already solved and reverted cleanly. The second was SB-23, which was
committed. **A third would have been the pattern, not an accident**, so Chase called a stop before anything
further was proposed.

*What the pass found.* Of everything committed in phases 5.3, 6.1 and 6.2, **three items were wrong**:

- **The DocumentSigning transport** gave the saga the domain topic *and the adapter's queue*, against an
  ADR that says only the projector queues subscribe to the domain topic. **Reverted**, then reopened and
  closed properly — see below.
- **The folder archive guard** listed four preconditions, two of which bound create and move rather than
  archive, and missed two steps of the real sequence: `FolderArchiveIncomplete`, and the root folder being
  archived **last** and left unarchived on an incomplete fan-out. **Rebuilt from
  `catalog-domain-invariants.md`.**
- **SB-23** was a three-way disagreement, not two. **Ruled: three statuses**; the ADR is corrected and now
  says why `VersionArtifact` belongs.

*What the pass cleared.* SB-24, SB-25, SB-26, SB-27 and SB-45 have **no ADR position at all** — the only
hits were ADRs written in phase 2. Quarantine, idempotency, `Dispose` and the ownership work trace to those
same phase-2 ADRs and are consistent by construction. Archive-keeps-renditions is *supported* by the asset
ADR, whose download gate admits `Archived`.

**SB-30 turned out to be forced, not chosen.** DocumentSigning publishes **no integration events at all**,
so the ADR's rule that sagas consume the boundary topic cannot apply — there is nothing there for this saga
to consume. One queue, `media-document-signing`, on the domain topic, read by both the adapter and the
saga. **The ADR's reserved name was right all along**; the spec's `media-signing` was the drift.

*Two contradictions found that were not mine*, both in `event-store-and-messaging.md`: its topic diagram
put `media-sagas` on the domain topic against its own table five lines below, and the signing queue was
named two ways. Both corrected.

**The method changes for the rest of phase 6.** Before proposing anything: identify the owning document,
read it in full, state what it already decides, and only then say what is missing. A pre-check across the
fifteen remaining findings shows **every one has prior material and seven have ADR-level decisions** — so
the assumption that a phase 6 gap means nothing has been decided was wrong as a general rule, not just
twice.

**Diversions:** one, and it is routed rather than absorbed — **MM-004**, above. The other corrections in
this log are to this plan's own record, to an existing ADR under an explicit ruling, and to 4a's own output
under evidence 4b produced — not to the finding set. **The vocabulary change is a 4a revision made under a
4b ruling**, not a new item: SB-70 is what asked for a tier fine enough to separate these operations, and
this is what satisfying it took. **SB-5's late closure is the one item this plan recorded as done before it
was** — worth remembering when reading any other tick in this file. Record every new defect here and route it to a new review or to MM-002 —
it does not become a checklist item in this plan.

**2026-09-17 — phase 6.3 (Catalog) closed.** Two commits: `f880bf2d` and `508f83e1`.

*Closed by newly-written design, so unreviewed by anyone but this session:*

- **SB-43** — the reviewer roster. **Ruled (Chase): minimum of one when review is required.** Written as a
  new § The reviewer roster on `mediaitem.write-model.md`: under `ReviewPolicy.RequiredForPublish` an empty
  roster is refused `MinimumReviewersRequired`, under `None` the empty-roster branch stays the ordinary
  path. Trim, de-duplication and the cap follow the collaborator decision in
  `editing-lifecycle-and-concurrency.md` rather than inventing a second rule; de-duplication runs before
  the count, and exceeding the bound reuses `TooManyCollaborators` rather than minting a second spelling of
  one limit. `MinimumReviewersRequired` and `ReviewerIsInitiator` were **orphaned codes** — named in the
  error catalog's ChangeRequests note and in `security-scenarios.md` respectively, with no row anywhere.
  Both now have rows under § Catalog — MediaItems, and the ChangeRequests note is repointed.
- **SB-49** — `order` added to the role-assign request body, with the distinction stated: `order` orders
  assets *within* one role, `AssetDefinition.DisplayOrder` orders the roles.
- **SB-44** — null-versus-absent on both metadata write paths, written as its own section.
- **SB-47** — the allowlist hazard stated above the queue table, where a publisher meets it.

*Closed on reading, nothing written:* **SB-45** (the route's `200`-with-body is stated explicitly, and
called out as the only MediaItem write endpoint that returns one) and **SB-51** (the lag table already
carries MediaItem·Registration at Async).

**SB-50 was not a gap. It was a dead field with two bugs in it, and it is being removed.**

The finding named "asset-definition auto-default". Reading the code rather than the spec: nothing consumes
`AssetDefinition.IsDefault`. Every occurrence outside `AddAssetDefinitionHandler` is plumbing from the
aggregate to the profile detail response, and the two hits inside it both *write* the flag. Its documented
purpose — the role an upload lands in when the caller names none — describes a resolution step no route
performs.

*The correction I had to make mid-report.* I first read `profile.AssetDefinitions` as the draft's and told
Chase the auto-default fires once, on the first definition. It is **published** state, and
`AddAssetDefinition` emits against the draft, so the handler's two checks read a collection the command
never writes to. The rule therefore fires on *every* definition added before first publish, and nothing
clears the flag on the others — `DefaultMediaProfiles` seeds Simple Audio's `artwork` with
`IsDefault: false` and the handler flips it, so four seeded profiles publish with two or more roles flagged
default, against the flag's own mutual-exclusivity rule. The back-compat shim beside it is unreachable
behind that. Neither is pinned by a test; `AddAssetDefinitionHandlerTests` has two tests and asserts
nothing about the field.

*Ruled (Chase): remove the flag everywhere, raise the code change on the board and stay on this plan.* So:
`ADO 35103` carries the code removal with the file list, the persistence analysis (no upcaster — neither
repo sets `JsonUnmappedMemberHandling`, so the serializer's default skip applies) and the two sign-offs it
needs, Enterprise Driver and UI. The spec side is done here — `IsDefault` returns zero hits across `docs/`
— and the decision, with the reasoning for removing rather than repairing, is a new §
*A MediaProfile has no default role* in `catalog-domain-invariants.md`. **`DefaultAssetId` is untouched**;
it is a different concept with real consumers.

*What this says about the method.* The re-verify rule — open the owning document before proposing — was not
enough here, because both owning documents were wrong. `mediaprofile.defaults.md` asserted a purpose the
API cannot serve and `mediaprofile.api.md` described the auto-default as firing once. Only the source
settled it. **For a finding about a field's behaviour, the code is the owning document.**

*Diversions:* one, routed — `ADO 35103`.

**2026-09-17 — phase 6.4 (Metadata / Registration) closed.** Two commits: `b8f3e5f8` and `3df843a7`.

*Closed by newly-written design:*

- **SB-52** — **the finding named a missing actor; it was a contradiction.** `context-overview.md`
  disowned retention and erasure outright while `registration.write-model.md § Retention` specified
  10-year and 3-year periods and an erasure action, with no command, event, actor, trigger or scanner
  anywhere. **The platform had already ruled on the general case** and Registration was contradicting it:
  `retentionschedule.design-decisions.md` § Scope holds that recording a record's retention and acting on
  it are different capabilities, that no engine computes a due date, and that a schedule is *a record of
  intent, not an instruction*. Same error, different file.
  **Ruled (Chase): delete the periods, keep erasure, make it honest.** A registration now carries no
  retention period, stated in its own terms — it is evidence of a disposal action, and evidence of a
  transfer has to outlive the thing transferred, or the platform destroys the proof and keeps the record.
  Modelled retention is pointed back at the item's `RetentionScheduleRef`.
  Erasure became `EraseRegistrationPersonalData` / `RegistrationPersonalDataErased` on
  `POST /v1/registrations/{registrationId}/erase-personal-data`, at `Registration.Manage.All` with **no**
  System-actor condition — the one `Manage.All` route on the aggregate a person calls, because a privacy
  request has no adapter to raise it. **Not `Dispose`**: erasure redacts and keeps, which is the opposite
  of disposal, and using the disposal verb would let `DisposalOfficer` reach into registrations.
  Three consequences written that the ruling implied but did not state: the erasure set was **incomplete**
  (`Amendment.RequestedBy`, `Notes` and `DecisionNotes` are personal data too and now clear in the same
  event); **after erasure the registration has no owner**, so every owner-scoped route answers `403`; and
  **the redaction is forward-only** — the event stream keeps the payload, an upcaster is what makes it
  survive a rebuild, and crypto-shredding is named as the upgrade path rather than implied as current
  behaviour.
- **SB-42** — the endpoint's contract was already complete and `operations.md` already specifies the
  rebuild. Added only what was missing: a record type whose events predate the history projector reads as
  one that has had no activity, the endpoint cannot tell the two apart, and the remedy is a replay rather
  than anything the endpoint does.
- **SB-60** — answered from source, not inferred:
  `services.AddUniquenessRegistry().UseDynamoDbStore("media-name-reservations")`, called per module in
  `Catalog` and `Metadata`, registering `INameReservationService` scoped against one shared table. Written
  with the reason the table is shared — the scope key separates its uses, and a second table name would
  silently partition uniqueness.

*Closed as misframed:* **SB-53** claimed read endpoints are specified as carrying no `errorCode`, in
contradiction with `api-conventions.md`. Nothing says that. The catalogue's *"**Read endpoints**: what a
query surface returns on refusal is stated with the endpoint rather than here"* is a statement about the
catalogue's scope, and the per-aggregate *"every refusal on a write endpoint carries `errorCode`"* is
silent about reads rather than a denial. The two "no `errorCode`" notes in `security-scenarios.md` are
about the force-release `403` raised by endpoint policy — a write endpoint. **What was genuinely absent
was a positive statement**, now written: a query surface refuses in the same shape, and the catalogue's
silence is its scope.

**SB-59 turned out to be the whole error contract, not a member list.**

The finding asked which `WithMetadata` members are permitted. Checking it found a three-way disagreement:
the shared docs say the members arrive at the root, `registration.api.md` said *"the platform's
problem-details pipeline carries no domain-error extension beyond `errorCode`"*, and the SDK supports
neither — `DefaultProblemDetailsFactory` takes no extensions argument and nothing anywhere writes
`errorCode`.

*Ruled (Chase): write the best-practice contract into the spec, reconcile the code afterwards.* So the
spec now states RFC 9457's model rather than a house one. `type` and `errorCode` are the same identity in
two forms and either is a valid branch; `title` and `status` are not branches. **Extension members are
declared per error and nowhere else** — § 3.2's model — with the six in use indexed in the catalogue, the
ignore-unrecognised rule, additive-vs-breaking stated, the machine-actionable-versus-prose test, and the
note that a member is part of the authorization surface. `currentStatus` on `InvalidStatusTransition` is
new and is what stops a client parsing English to learn where an aggregate is. Registration's
platform-wide claim was **deleted** — it was true about today and wrong as a place to put it, a fact about
the whole pipeline filed inside one aggregate's API page.

*The sweep that followed found the contract unimplemented in four places at once*, because they are one
missing mechanism: no `errorCode` is ever written, `type` is `httpstatuses.com/{status}` rather than the
`errors.magiqmedia.com` scheme, `title` derives from `ErrorType`'s category rather than the code, and
`DomainError.Extensions` is never copied onto a response. Raised whole as **`ADO 35104`**, with the
declared member set as its acceptance criteria.

*A note on method.* Two of these five were misframed findings rather than gaps — SB-52 named a missing
actor when it was a contradiction, SB-53 named a contradiction when there was none. **Reading the owning
document decided both**, which is the rule that came out of phase 6.2. What it did not decide was SB-59:
there the owning documents disagreed with each other and with the SDK, and only reading the source
settled it — the same lesson 6.3 recorded, and now twice.

*Diversions:* one, routed — `ADO 35104`.

**2026-09-17 — phase 6.5 (Platform / operations) closed, and with it phase 6.** Commit `1f62af8f`, plus a
`deploy-runbook.md` change in this project.

*Two of the four were already answered, and the findings were wrong about that.*

- **SB-55** said the staging promote mechanism is unspecified. `branching-and-deployment.md` specifies it
  completely: `env=staging` resolves to `config/qa.json` and deploys whatever QA holds, as a separate
  `deploy-staging` job gated on `STAGING_ENABLED`, with the reason — staging validates exactly what QA
  proved, never a separate build. **Nothing written.**
- **SB-54** said the `deploySearch` condition exists only inside fenced diagrams. It is also prose in
  `consistency-model.md` § Per-aggregate lag class and a row in the `persistence-and-eventing.md` queue
  table. **What the finding missed is the actual defect**: the ASCII diagram carried *"not passed by any
  workflow or config, so not live in any environment"* — build status, in a spec file, inside a fence
  where the guard's build-status check does not look. Removed, and replaced with a § of its own stating
  what the flag is, that it defaults to `false`, that the subscription, the Lambda and the indexes are
  conditional on it together, and that nothing degrades when it is off because `media-projector` carries
  no filter policy.

*Written:*

- **SB-56** — "guarded" was used in two ADRs and defined in neither, with enumeration deferred to the
  authorization matrix. Now defined once in `api-permissions.md`: a command is guarded when its handler
  compares the actor type on `IExecutionContext`; the guarantee is per-command, so **an unguarded command
  has no enforcement rather than a route-level default**; permission and actor type are separate
  conditions; and the per-endpoint `## Authorization` tables are the enumeration — a row whose predicate
  names `actor_type` is a guarded command. **No central register, deliberately** — it would be a copy that
  drifts from the tables reviewed beside the endpoints they govern.
- **SB-57 — routed, not written into spec.** `operations.md` already states RTO, RPO, PITR coverage and an
  eight-step recovery runbook. What was missing is that none of it is ever exercised, and a verification
  *practice* — cadence, owner, procedure — is an ops checklist, which § Spec purity routes to
  `deploy-runbook.md`. Owner is also attribution, which spec bans outright.
  **Ruled (Chase): annual, owned by the Cloud team.** Written as Scenario 4 in `deploy-runbook.md`.
  The drill is the whole runbook rather than a restore, because **restoring a table is the half that
  cannot be wrong** — cutover is, and the read-model path runs through `ProjectionReplay`'s `rotate` and
  the `read-model-metadata` pointer. Run end to end in dev or qa, since step 1 stops writes and that is an
  outage; plus one safe prod-side PITR restore to a new table name, which is the only way to confirm
  prod's recoverable window is really where we think. Rollback is exercised too. Results go to
  `decisions/`, and a drill that finds the runbook wrong has succeeded.

**`operations.md` was left alone on purpose.** The spec states the capability — PITR is continuous, the
restore procedure is this — and the runbook states the practice. A spec file may not cite a document
outside `docs/`, so there is no pointer between them, and that is the correct separation rather than a
missing link.

*Two process failures of mine in this phase, both invisible to the guard.* The SB-54 prose landed **inside
a fenced block**, where it would have rendered as literal ASCII art — caught on read-back, moved below the
fence. And the edit script **died mid-run on a `cp1252` print** after applying its first edit, so two of
three never ran; the guard passed anyway, because a partially-applied edit is still valid markdown. The
lesson is the same one twice: **the guard checks the rules, not whether the change I intended is the
change I made.** Read back what was written.

*Diversions:* none.

**Phase 6 is closed.** Thirty findings across five contexts. The standing rule that governed it — where no
ruling covers a gap, ask — produced five rulings: the reviewer minimum, removing `IsDefault`, Registration
retention and erasure, the error contract's direction, and this drill's cadence and owner. Two code
defects were found and routed rather than absorbed (`ADO 35103`, `ADO 35104`). Next is phase 7.

**2026-09-17 — phase 7 closed.** Two commits: `2308b5ae` and `8f681179`. Ten of twelve ADR files changed;
`idempotency-conformance.md` and `infected-originals.md` had nothing to strip, which is expected — they
were written in phase 2 under this rule.

**The item's estimate was low, and the work was not what it sounded like.** The estimate read as a
find-and-delete of ~33 marked phrases. An inventory across `docs/adrs/` found roughly 86 candidate lines,
and **most of the marked blocks were not deletable as written** — they carried the decision as well as the
narration of how the file came to say it. So the method was: separate *why the decision is what it is*
(stays) from *how this file came to say it* (goes), and rewrite rather than cut.

*What came out:* the "Corrected <date>" and "⛔ Corrected" blocks across seven files, the "Decided <date>"
stamps, the `(Chase)` attribution, `auth-and-security.md`'s two-entry **revision history** list, the
`(revision a)` label, `_Implemented on <branch>_` and `_Implemented._` notes, and the last few rationales
phrased as *"this previously said…"* — each rewritten to state the rule positively.

*What stayed, deliberately:* `- Superseded originals: archive/ADR-00X…` lines, which are provenance rather
than narration; rejected alternatives, including references to a superseded model as a rejected option;
and `**Phase B (deferred)**`, which is a decision to stage work rather than a status report.

**Seven blocks carried real facts about the code, and deleting them would have lost the only written
record.** Collected and raised whole as **`ADO 35105`** rather than dropped. The significant one is
**asset detach**: `DetachAssetFromMediaItemCommand` is dispatched by nothing and there is no unassign
consumer, so unassigning updates Catalog and the Asset never learns — `MediaItemId` stays set, the
standalone state is unreachable after first assignment, and **an asset can never be reassigned to a
different item**. Second is that **checkout enforcement covers metadata only**, so a locked-out caller can
still rename, retag and swap assets. The other five are smaller: `ForceReleaseCheckout` admitting the
owner against the ADR's System-only decision (kept *in* the ADR as a stated divergence, since it is a
custody-guarantee difference), the Retention capability's two-versus-four fields, nothing of
`RetentionSchedule` being built, the two folder-count projections never existing, and
`EnvironmentResetCommand` deriving a suffixed table name the naming decision removed.

*Three judgement calls were left open at first pass and closed immediately after, in `e08635b2`. Two of
the three descriptions below were wrong, and reading the files properly is what corrected them.*

1. **`asset-storage-and-processing.md` does not hold two conflicting decisions.** That was a
   mischaracterisation from reading the supersession sentence without the section under it. There is **one**
   decision wearing a revision label: a heading reading `### S12 revision (2026-07-17) — …`, a sentence
   claiming to supersede "the decision below", and `(S12)` sprinkled through the prose. What is actually
   below is the **tier ladder, which both designs share** — so there was nothing to delete, only a label to
   strip. Done: the heading now states the decision, the supersession sentence is gone, and the
   reversal-narrating rationale is rewritten as what it always was — a rejected alternative, keyed on
   status where this one keys on capability.
2. **Front matter repeated provenance**, and that one was right. Five files opened with *"Originally
   recorded as separate, chronologically-numbered ADRs (…); consolidated 2026-07-08 … Superseded originals
   are preserved in `adrs/archive/`"* while also carrying `Superseded originals:` in § Related. The opening
   line now says only what the file covers; the archive pointer survives once, at the bottom.
   `auth-and-security.md`'s middle sentence — why it is a topic document rather than a single-decision
   file — is organisation, not history, and was kept.
3. **There is one open-question section, not two.** Miscounted. `catalog-domain-invariants.md` carries it
   and no other ADR does. **Kept, and re-headed** `### What this decision does not settle`: the content is
   the boundary of the decision — alias-only qualification, with the always-also GUID address named as
   deliberately unresolved — which is exactly what an ADR should record. What it should not look like is a
   tracking item, and `Open question (not yet decided)` read like one.

**A real defect surfaced while checking that work, and it is not phase 7's.** `S12` — a finding id from an
earlier review — appears **13 times across four files**, three of them spec: `glossary.md`,
`architecture/domain-model.md`, `architecture/bounded-contexts.md` and the asset-storage ADR. Under
§ Spec purity that is a citation to an id undefined inside `docs/`, and it should not be there.

**The guard cannot see it, and that is the more useful half.** `docs_guard.py`'s citation pattern is
`\b([A-Z][A-Za-z]{0,5})-([0-9]+(?:\.[0-9]+)?)\b` — it **requires a hyphen**. Separator-less ids are
invisible to it, and the repo `CLAUDE.md` names `W29` as a banned form, which has no hyphen either. So the
citations check has returned a clean hard zero this whole workstream while thirteen citations sat in the
tree. The `S12` occurrences are residue for phase 8; **widening the citation pattern is a change to phase
0's artifact** and is routed rather than absorbed.

*Method note.* The guard passes on all of this and would have passed on none of it being done — its
build-status and dates checks are `docs/spec/` only, and `docs/adrs/` is outside them. **Phase 7 had no
automated backstop at all**, which is worth knowing when reading its tick.

**2026-09-17 — the citation check was widened and the tree swept.** Commits `d0484963` and `96129ae4`.
**Ruled (Chase): widen the guard, sweep, and look for anything else of the same shape.**

*The guard change.* `ID` required a hyphen, so `ID_NOSEP = \b([A-Z]{1,5})([0-9]{1,4})\b` now runs beside
it. A family allowlist cannot do this job — `S3` and `S12` share a prefix — so `ALLOW_TOKEN` names whole
tokens: AWS services, codecs, crypto and encoding, heading levels, incident priorities, versions and
quarters, plus the four the tree actually needed (`D3`/`D10` .NET format specifiers, `GSI1`/`GSI2`, `C0`
for the Unicode control range, `Z0` from a regex fragment). **It fired on exactly the 18 real citations
and nothing else**, which is the result that made the allowlist trustworthy rather than a guess.

*What the hyphen requirement had been hiding:* `S12` ×13 in `glossary.md`,
`architecture/domain-model.md`, `architecture/bounded-contexts.md` and the asset-storage ADR, mostly as
`(S12, 2026-07-17)` stamps on statements that read better without them; `C1`, `C2` and `C4` ×4 in
`api-http-conventions.md`, in two blockquotes narrating the closure of review findings — one of which
**named `reviews/api-rest-review.md` outright**, a document outside `docs/`; and `S1` ×1 in
`auth-and-security.md`. All rewritten as positive statements rather than blanked. A fourteenth `S12` sat
inside a fenced code comment in `asset.write-model.md`, which the guard skips by design and always will —
fixed by hand.

*Two more found while sweeping.* `spec/shared/magiq-auth-role-claims-requirements.md` opened with
`_Raised: 2026-08-26 · Owner: Chase Ramone (magiq-media)_` — a decision date and an attribution, both
banned in spec. Removed, and the context line reworded to *"a request **from** `magiq-media` to the
`magiq-auth` team"* so the document still says which side is asking without naming a person. **This one is
arguable** — it is a hand-off to another team, and a named contact is functional rather than decorative;
the reasoning for removing it is that the document states what is needed, and who asked is not part of
that. And `docs/implementation-plans/api-consistency-remediation-plan.md` was a five-line tombstone
pointing at a machine-local path, the only file in its directory, linked from nowhere in `docs/`.
**Ruled (Chase): delete.** Done; the directory went with it.

*The baseline shrank from 183 dated entries to 179* as the dated citations left, and was rewritten with
`--update-baseline` so it holds only what still exists.

**The wider point is about the guard, not the residue.** The citations check is one of the two that cannot
be baselined away, and it is the one this workstream has leaned on hardest — and it reported a clean hard
zero for the whole of phases 1 to 7 while eighteen citations sat in the tree. **A check that cannot fail
is indistinguishable from a check that passes**, and nothing in the workstream would have surfaced the
difference; it took reading a token the guard was silent about. Worth remembering before trusting a green
run on the checks that have never yet failed.

**2026-09-17 — phase 8 closed.** All five boxes ticked, guard green on all five checks.

*The embedded open questions were three, not eight — and the survey is the useful half.* 0 open-question
headings in `docs/spec`. Of 6 prose matches, 3 are domain language and stay (*"the request is still open"*
means an unresolved change request, not an unresolved design). 1 interrogative is a decision criterion in
`retentionschedule.design-decisions.md`. **179 `⚠` markers stay** — they are the register README row 14
points readers at, and stripping them would delete the thing the row promises. Two of the three real ones
were speculation with a settled rule attached, and were cut back to the rule. The third needed a decision.

**Two rulings (Chase), both ADR-backed.**

1. **Deprecated fields compile as tombstones.** `mediaitem.write-model.md` specified precedence rules for a
   snapshot field carrying `IsDeprecated` while `mediaprofile.write-model.md` said no carrier existed and
   the compile filtered deprecated fields out — rules with nothing to read. Chase chose tombstones over
   deleting the rules. The member now rides on `CompiledMetadataField`, `MediaProfileSnapshotField` and
   `CompiledMetadataFieldDto`, and deprecated fields **count toward collisions**. That last part is the
   decision: filtering drops the collision count when a contributor deprecates, so `{alias}.title` becomes
   `title` at the next publish — a silent rename of a key items already store — and it breaks
   *deprecate → publish → remove* by making the field vanish at deprecation rather than at removal.
2. **Rendition dimensions cross every boundary.** `RenditionResult.Width`/`Height` were carried on the
   value object and dropped by both DTOs, and the write model itself said *"either carry them through both
   DTOs or drop them from the value object."* Carried: both DTOs gain nullable `Width`/`Height`, null where
   a rendition has no spatial extent. They are measured once at generation and unrecoverable without
   re-probing S3, so dropping them discards a measurement rather than a derivation.

*Two boxes were already satisfied and one dangling pointer was not.* The cross-region rows were gone and
single-region stated; `:::dead` and `<<NOT IMPLEMENTED>>` return nothing; **`deploySearch` is a real
deployment flag, not residue** — it defaults to `false` and three files state the conditional OpenSearch
path correctly, so the plan's listing of it was wrong. What was still live:
`processingjob.write-model.md`'s ⚠ claiming `Succeeded` is unreachable because `AssetProcessingWorker` has
no trigger, pointing at a `§ Service Boundaries` that now states the opposite. Deleted — the build-status
fact is already in the `Z:\` docs project's `use-cases.md` as P-1, which is its home.

*README rows 3 and 7b were telling readers things this plan had already made false.* Row 3 said the
inventories disagree 10 vs 12 (phase 3 made them agree); row 7b sent readers to
`catalog-domain-invariants.md` warning that four of its rule claims are false (phase 7 fixed it, and the
ADR no longer says so at the top). **A navigation file ages against the tree it navigates**, and nothing in
the guard watches for it — both rows were pointing at a state that no longer existed, which is the exact
failure mode the README exists to prevent. Three narration fragments went with them (rows 7c, 13, 14e), and
`domain-model.md`'s no-expiry note lost its appeal to a C# doc comment and its *"Recorded in …"* pointer.

*The build-status baseline is 7 and all 7 look like false positives* — `deferred` in *"quota is deferred to
assign time"*, `not registered` in a code comment about assembly scanning. Left for phase 9 to judge
against a narrower pattern rather than absorbed here.

**2026-09-17 — phase 9 closed. The baseline reached 0.** All four boxes ticked, all five checks green.

*The 7 build-status entries were a pattern defect, not residue.* Six of the seven were domain vocabulary —
five `deferred` (a standalone upload's processing quota **is** deferred to assign time, and five passages
say so) and one `not registered` (an event published but unregistered never reaches the projectors). The
seventh was real: README row 14e promised that a spec file carries *"a design that is decided and not
built"*, which is the thing the purity rule forbids a spec file to carry — **the index was advertising the
violation**. Rewritten to *"the boundary of what a decision settles"*. So the guard was narrowed twice and
the tree fixed once, and `--update-baseline` wrote **0 accepted entries**: **209 → 192 → 187 → 7 → 0**,
monotonically down, exactly as the file's header demands.

**The lesson is the same one the citations check taught, inverted.** There the pattern was too narrow and a
check that could not fail reported a clean zero for seven phases. Here the pattern was too *wide*, and the
cost is different but not smaller: seven false positives sat in the baseline looking like accepted residue,
and any real build-status hit landing in those files would have been indistinguishable from them at a
glance. **A baseline is only readable if everything in it is real.** Both failures are the same root —
nobody had read what the checks were matching on — and both were invisible from a green run.

*Nine more history fragments came out while re-running the detectors*, none of which any check can see.
`error-catalog.md` carried five: `**Renamed from FieldOrderMismatch**`, `**Replaces** InvalidLocalisedText`,
`**Replaces** LocalisedTextTooLong — which capped one locale of a map`, *"It had no stated publish-time
enforcement point at all"*, and *"Keyed to the baseline it refused an ordinary rollback"* — the last two
rewritten rather than cut, since the rule underneath each is live and only the tense was wrong.
`system-architecture.md` said a queue was *"Renamed from `media-notifications`"*; `domain-model.md` carried
a **Correction:** block narrating that a note *"was spec drift and has been removed"*, plus *"This replaces
the earlier 'standalone defaults to the full pipeline' rule"* and *"The former `media-documents` /
`document.{ext}` split is retired"*. `cascade-rules.md` ended a rule with *"Stated here because it was
previously stated nowhere."* Per Chase's standing ruling — **treat this as the first production release** —
all of it goes.

**A mechanical sweep for these would have been wrong**, which is why they survived phase 8. The obvious
search — `retired|superseded|no longer|previously|used to|the former` — returns **165 hits in `docs/spec`**,
and the overwhelming majority are domain vocabulary: `retired` is a real concept here
(`RetiredFieldDefinitions`, the retired-name predicate), `superseded` is a real member (`SupersededBy`), and
*"a retired name is no longer available"* is a rule, not a change log. Narrowing to the forms that can only
be narration — `**Replaces**`, `Renamed from`, `had no stated`, `has been removed` — returned **8**, of
which 6 were real. **The signal is in the phrasing that has no domain reading**, and a grep for the concept
finds twenty times the noise.
