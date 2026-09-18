---
id: MM-006
type: plan
project: magiq-media
workstream: spec-coherence
consumes: [MM-005]
depends-on: []
blocked-by-external: []
status: done
todo-id: eecf8c43-1452-5bef-9920-42fbe4712d27
branches: [spec/coherence-remediation, spec/initial-alignment-work]
ado: -
created: 2026-09-18
---

# Spec Coherence — Remediation Plan

Consumes **MM-005** (51 findings, fifteen questions answered 2026-09-18). Eleven phases on
`spec/coherence-remediation`, cut from `develop`.

**Nothing here is blocked.** `depends-on` is empty and there is no external blocker. Every one of the 51
findings is spec-internal and fixable now — that is the difference between this plan and MM-003, which
cannot close while `AP-001` is unshipped.

---

## The shape of the work

**Thirty-six corrections and fifteen decisions, and the decisions are already made.** What remains is
mostly deleting restatements: fourteen of the twenty-six High findings are a `shared/` or `architecture/`
file contradicting the aggregate or saga file it explicitly defers to, and in nearly every case the fix is
to delete the summary and keep the pointer.

**Three phases carry genuine design work** and should be sized differently from the rest: phase 7 (the
rendition trigger), phase 8 (four items, including a new command), and phase 2 (declaring
`RetentionScheduleRef`).

**Two orderings are load-bearing.** Phase 0 lands the detectors before any editing, for the reason MM-003
records in its own phase 0. And phase 2 rewrites `mediaprofile.write-model.md` § Capabilities exactly once,
because Q1, Q2 and SC-032 all edit it and doing them separately means editing it three times.

### Deviation from MM-005 § Recommended sequencing, recorded

The review put the detectors at step 8, alongside the navigation fix. **This plan moves them to phase 0.**
MM-003's phase 0 is the precedent and the reasoning is the same: *"stripping without a guard just resets
the clock"*. Two of the three new detectors catch classes this plan is about to touch — SC-042 is a
plain-text `.md` reference and the `asset.api.md` truncation is an unclosed `](` — so landing them last
means editing the instances without the guard that stops them coming back.

---

## Phase 0 — Land the three detectors

**Before any spec file is edited.** `docs_guard.py` passes five checks today and MM-005 found three blind
spots, each from a live instance rather than from inspection.

- [x] **Year-month dates.** `DATE` matches only full `YYYY-MM-DD` or `Month YYYY`, so `2026-08` passes.
      Add the year-month alternative: `(?<![\d-])20\d{2}-(0[1-9]|1[0-2])(?![\d-])`. ✅ The check fires on
      `docs/spec/README.md:110` before phase 5 fixes it, and returns zero after. — **Done.** Added as a
      third alternation branch in `DATE`, ordered last so a full date still matches whole. Fires on
      `README.md:110` and nowhere else.
- [x] **Plain-text `.md` references that resolve to nothing.** The `links` check requires markdown link
      syntax, so a filename in a table cell or in prose is invisible — which is how SC-042 survived eleven
      citations of a deleted file. Add a check that every `` `<name>.md` `` token in a spec file resolves
      to a file under `docs/`. ✅ Fires on the eleven `system-spec.md` citations before phase 5, zero after.
      — **Done** as the new hard-zero check `references`. Two widenings against the literal wording, both
      forced by real instances: a token resolves against **any** markdown file the repo has, not only one
      under `docs/`, because `system-architecture.md:424` names `DEPLOYMENT.md` in a host folder and
      `operations.md:301` names `src/tools/ProjectionReplay/RUNBOOK.md`, and both exist; and a bare family
      name — `write-model.md`, `api.md` — resolves by suffix, because that is how this tree names the
      layer rather than one aggregate's copy of it. Placeholder forms (`<agg>.write-model.md`,
      `*.read-model.md`) are excluded by the leading character class rather than by an allowlist.
      **`deploy-runbook.md` is the one allowlist entry** — a real document that is not in this repo at all.
- [x] **Unclosed `](`.** A truncated link is not a broken link — the link regex needs a closing paren to
      match at all — and the `structure` check looks at a file's *end*, so a mid-file truncation passes.
      Add a check for an unclosed `](` on any line outside a fence. ✅ Fires on
      `asset.api.md:768` before phase 9, zero after. — **Done** as the new hard-zero check `truncation`.
      Inline code spans are stripped first, so a literal `](` inside backticks is not a hit.
- [x] **Baseline stays at zero.** All three land with no baseline entries. `docs-guard-baseline.tsv` is at
      its floor after MM-003 phase 9 and **must not grow** — a new hit is a finding, not a queue-jump.
      — **Done.** Baseline untouched at zero; both new checks are hard zero, so they cannot be baselined
      at all, and the year-month branch lands inside a `dates` baseline that is already empty.
- [x] **Phase exit.** ✅ ~~Eight~~ **seven** checks, all returning zero except the three deliberate pre-fix
      hits above, each of which is closed by its own phase. CI fails on a reintroduced instance of any of
      the three. — **Done.** The count is corrected: the year-month form is an alternative inside `DATE`,
      not a seventh registered check, so the guard reports **seven** checks covering eight detection
      classes. `.github/workflows/docs-guard.yml` needed no change — its push trigger already covers
      `spec/**`. Committed as `6175c579`.

> **The guard is red on this branch until phases 5 and 9 land, by design.** Phase 0's own exit expects
> three pre-fix hits, so "green before phase 2" is not a condition this plan can satisfy — what phase 0
> guarantees is that the detectors are *in place* before any spec file is edited, which is the point of
> putting them first. The three expected hits are `dates` on `README.md:110`, `references` on the
> `system-spec.md` citations plus `recordtype.design-decisions.md`, and `truncation` on `asset.api.md:768`.
> Any fourth hit is a regression.

## Phase 1 — Decide ✅ **CLOSED 2026-09-18**

All fifteen questions answered by Chase, recorded in MM-005 § Open Questions with the effect of each on the
finding list. Summarised here because the phases below quote them:

| Q | Answer | Consequence for the plan |
|---|---|---|
| Q1 | `RecordType` has **no** capability set | Correction in five files; **raises a code defect, diverted to MM-002** |
| Q2 | `RetentionScheduleRef` **is** a member, **not** a publish gate | Declare it; delete the gate; no refusal code needed |
| Q3 | Force-release: **both** tier and owner admit it | Encoded as `Manage` + owner predicate, widened by `Manage.All` — **confirm the encoding** |
| Q4 | `.All` **widens** on Registration, as the platform rule states | A `ReadWrite.All` holder can act on another officer's live filing — **state it explicitly** |
| Q5 | `DocumentSigningSession` `.All` forms **exist** | Move to the owned-subset table; closes SB-12's other side |
| Q6 | **Drop** the `actor_type` requirement on ProcessingJob | Deletion, not an enforcement mechanism |
| Q7 | `ProfileOrigin` guard is **command-level**, with a seeder exemption | The exemption is the hole — specify it precisely |
| Q8 | **Widen the `media-processing` filter** | Filter-policy change; video blocks in-invocation; EventBridge sentence removed |
| Q9 | `PUT …/metadata` is a **merge** | Delete one line |
| Q10 | Auto-submit is **inert** under review | Plus: settle `Governed Media Record`'s `AutoSubmit ✓` |
| Q11 | Reviewer withdrawal: **add the command** | Design work — command, event, route, permission, code, roster rule |
| Q12 | **Delete** `Compensated` | Runbook must say where the outcome is read |
| Q13 | Signing budget is **336 hours** | One line in `saga-patterns.md` |
| Q14 | Billing and Notifications are **asset-level only** | Strike two names; the two routing-row additions stand regardless |
| Q15 | `DocumentSigningSaga` **is** specified | **Raised SC-050** |

- [x] **All fifteen answered.** ✅ Zero `**Open**` markers in MM-005 § Open Questions. — **Done 2026-09-18.**
- [x] **Confirm Q3's encoding.** The answer was "both admit it"; this plan reads that as `MediaItem.Manage`
      plus an owner predicate widened tenant-wide by `MediaItem.Manage.All`, which keeps it inside
      `api-permissions.md:73`'s existing rule rather than inventing an OR. **One line from Chase before
      phase 6 writes the rows.** ✅ Confirmed or corrected in the card comment. — **Confirmed by Chase
      2026-09-18, as read.** The explicit-OR form was offered and declined. Phase 6's SC-025 item is
      unblocked; **nothing in phase 6 is now waiting on anyone.**

## Phase 2 — `MediaProfile` § Capabilities, rewritten once

**SC-010 · SC-011 · SC-012 · SC-032.** All four edit the same section. Doing them separately means editing
it three times and getting a different count each time.

- [x] **Remove the RecordType capability set** (SC-010, Q1). Five files describe a member that does not
      exist: `mediaprofile.write-model.md:122,155`, `mediaprofile.design-decisions.md:65,83`,
      `metadata-schema-composition.md:18,31,44,49-56`, `domain-model.md:197`. ✅ No file outside Metadata
      reads a capability off a `RecordType` version; `grep -rn 'RecordTypePublished.Capabilities' docs/`
      returns nothing. — **Done.** The four tokens (`RecordTypePublished.Capabilities`,
      `CompiledMetadataTemplate.Capabilities`, `ICapabilityRegistry`, `SourceCapability`) now occur in
      **Metadata's stated absences only**. The ADR's field-contributor role moved from `RecordType` to
      `MediaProfile` rather than being deleted — `context-overview.md:215` already says governance field
      groups attach to a profile, and `:221` says `Capability` is one vocabulary with two consequences, so
      the role has a home. **`metadata-schema-composition.md` was edited in place**, not superseded by a
      new ADR; reverse that if you'd rather the decision record were left standing and superseded.
- [x] **Delete the governance-field-group clause** (SC-012). `SourceCapability`, `ICapabilityRegistry` and
      `MandatoryRecordkeepingCoreMissing` each occur exactly once in the tree, in one sentence with no
      carriers. Keep only the collision-qualification statement. ✅ All three tokens return zero;
      `mediaprofile.write-model.md:264`'s "exactly three codes" is now true. — **Done**, as ruled: the
      mechanism claims go, the collision-qualification statement stays and now names where a governance
      field group actually attaches.
- [x] **Declare `RetentionScheduleRef`, and delete the publish gate** (SC-011, Q2). Add the property row,
      the command, the event, the `MediaProfilePublishedSnapshot` member and the read-model/API field —
      nullable, at most one. **Remove the gate** from `domain-model.md:76`, `README.md:42` (row 14f-i) and
      `retentionschedule.design-decisions.md:105-110`. ✅ The member is declared in all five places a
      `MediaProfile` member appears; no file states a publish requirement; **no new error code exists**,
      and `catalog-domain-invariants.md:73`'s publish guard is unchanged. — **Done.** Declared as
      `SetRetentionSchedule` / `SetRetentionScheduleCommand` / `MediaProfileRetentionScheduleSet`, plus
      `PUT /v1/profiles/{profileId}/retention-schedule`, `RetentionScheduleRefDto` on both read-model DTOs
      and all three API response examples. **No invariant row and no error code were added** — the ruling
      scoped five things and an existence guard is not one of them, so a profile may pin a schedule the
      spec does not require to resolve. Worth a look in its own right; not raised here.
- [x] **Correct the `Signing` row and the count** (SC-032). `Signing` gates `InitiateSigningSession` in
      DocumentSigning with `SigningCapabilityNotEnabled`. ✅ `mediaprofile.write-model.md:190` reads ✅ and
      `:177` reads "three … six" — `Retention` still gates nothing, so Q2 does not change the count.
      — **Done.** Now `:192` and `:182` after the section was rewritten.
- [x] **Divert the code defect.** With no capability set on any version,
      `CompiledMetadataTemplate.Capabilities` is a union over an empty family, so
      `Capabilities.Contains("Processing")` is permanently false and every asset takes the bypass. **Where
      Catalog's `Processing` gate reads its input from is a code question.** Raise it on MM-002 and log the
      diversion in § Session log — it does not become a checklist item here. ✅ MM-002 carries it and its
      card names this plan as the origin. — **Done.** The spec now states the target, so the code question
      is bounded: the gate must read the profile's declared set.
- [x] **Phase exit.** ✅ § Capabilities edited once; `docs_guard.py` pass. — **Done.** Edited once, in one
      commit (`3fb4e792`). Guard unchanged: same three designed pre-fix hits, no new ones, `links` still
      hard zero so the new `#where-a-capability-is-declared` anchor resolves.

## Phase 3 — Sweep `shared/`

**SC-001 · SC-002 · SC-003 · SC-004 · SC-005 · SC-006 · SC-007 · SC-009 · SC-023 · SC-047 · SC-048 ·
SC-050 · SC-051.** Thirteen findings, all corrections, one shape: **delete the restatement, keep the
pointer.**
The cheapest high-value block in the plan and it can be done by one person in one pass.

- [x] **`saga-patterns.md` × 4.** `Fail()` transitions from `Queued` (SC-001 — keep the general point about
      a discarded `Result`, replace only the worked example); `ForceReleaseCheckout` **is** the signing
      compensation's second act (SC-002); the signing budget is **336 hours** (SC-048, Q13); the timeout
      scanner covers every non-terminal signing state (SC-050, first half). ✅ Each of the four points at
      its owning saga file rather than summarising it. — **Done.** SC-001's replacement example is a
      `FailProcessingJobCommand` racing a job already at `Succeeded` or `Bypassed`, which is the refusal
      `processingjob.scenarios.md:201` states. SC-050: all four non-terminal statuses scanned, `Releasing`
      included — which is the "state whether `Releasing` is included" half of the ruling.
- [x] **`cascade-rules.md` × 2.** Failures are swallowed on the **collection** path only; the folder path
      refuses `422 FolderArchiveIncomplete` (SC-003). The workers dispatch **`ArchiveFolderNodeCommand`**
      (SC-004). ✅ Both agree with `archive-fan-out.md`, which `cascade-rules.md:31` already defers to.
      — **Done.**
- [x] **`cross-aggregate-invariants.md`.** `FolderMediaItemsIndex` is maintained on `MediaItemCreated` and
      `MediaItemMoved`, two removal projectors exist, and the gap is first assignment via
      `MediaItemAssignedToFolder` (SC-005). ✅ The bullet describes under-archiving, not over-archiving —
      the two are opposite bugs and only one is real. — **Done.**
- [x] **`event-store-and-messaging.md` × 3.** The `media-sagas` filter is the explicit five, not four
      wildcard families (SC-006). `media-document-signing` collapses to one row with the nine signing event
      types (SC-007). Add `media.processingjob.created` and `media.processingjob.bypassed` routing rows, and
      strike Billing and Notifications from the job-level events (SC-009, Q14). ✅ No wildcard admits
      `media.processingjob.bypassed`; every published event has a routing row. — **Done.** The
      `media-document-signing` duplicate collapsed to one row keeping `300s (≥ Lambda timeout)`, and the
      queue-topology diagram with it; the "three of the queues carry an explicit allowlist" count still
      holds. Processing's § Published now states that every consumer of a job-level event is inside the
      bounded context, so the boundary rule is visible where the mistake was made.
- [x] **`error-catalog.md` × 4** (SC-023). Add `RateLimitExceeded` and `RenditionNotFound` or remove the
      example payloads that produce them; add `DuplicateAssetId` and `PersistenceFailed`; give
      `CheckoutRequired` a raise site or remove the row. ✅ Every `errorCode` in the tree resolves both
      ways, which is what `:3-5` claims. — **Done**, with one addition and one correction to the review.
      Added: a request-level `QuotaExceeded` row, because the review's part (c) deletes the per-item row at
      `asset.api.md:867` and leaves `asset.api.md:779`'s `400 QuotaExceeded` uncatalogued — exhaustiveness
      would still have failed. Corrected: the review says to replace `DeclaredSizeExceeded` and
      `ProfileLimitExceeded` with catalogued codes; **both are already catalogued**, under § Batch
      Operations, so only `DuplicateAssetId` and `PersistenceFailed` were genuinely missing.
      `CheckoutRequired` was removed rather than given a raise site — inventing a refusal to justify a
      catalogue row is the wrong direction.
- [x] **`If-Match` — eleven, everywhere** (SC-047). `api-conventions.md:412,418` and `error-catalog.md:92`
      to eleven; `consistency-model.md:89` points at `recordtype.api.md § Optimistic concurrency` rather
      than re-enumerating; `mediaitem.api.md:340` narrows to "the only two on which `If-Match` is
      **optional**". ✅ One number, stated once, with the other files pointing at it. — **Done.**
      `consistency-model.md`'s neighbouring "on **every other write** a supplied `If-Match` is silently
      ignored" was corrected with it — with eleven mandatory routes named, that clause was false as written
      and re-created the very trap it warns about.
- [x] **Idempotency residue** (SC-051). Sweep `recordtype.api.md:16-18, :282-289` and
      `mediachangerequest.api.md:13-14` to the conformant contract MM-003 phase 5 wrote, letting both cite
      `api-conventions.md § Idempotency` rather than restating it. **`recordtype.api.md:282-286`'s ordering
      argument is built on the retired semantics** — the `Idempotency-Key`-before-`If-Match` rule survives,
      its worked example does not. Add the three conformant codes to the write-route error lists.
      ✅ Only `api-conventions.md` states the mechanism; `IdempotentRequestInProgress`,
      `IdempotencyKeyReused` and `IdempotencyKeyRequired` each appear in at least one endpoint's
      `**Errors:**` list, which none does today. — **Done for two of the three codes.**
      `IdempotentRequestInProgress` and `IdempotencyKeyReused` now appear on write routes in both files.
      **`IdempotencyKeyRequired` cannot be placed without inventing design:** `api-conventions.md:145`
      says the key is optional by default and that an endpoint requiring it declares so in its own
      `<agg>.api.md`, and **no endpoint in the tree declares it**. Listing the code on a route that accepts
      the header optionally would be false. The absence is already stated in the right place, which is the
      `security-scenarios.md:154` pattern phase 10 blesses — **not** the `CheckoutRequired` case, where
      nothing stated the absence at all.
- [x] **Tell MM-003.** Comment MM-006's finding on MM-003's card: **phase 10 box 3 names one file and the
      contract lives in six.** Recommend widening its scope to the five files that state the mechanism.
      Not a dependency in either direction — this plan does not wait on AP-001, and AP-001 does not wait on
      this. ✅ MM-003's card carries the note. — **Done**, posted before the sweep started.
- [x] **Phase exit.** ✅ All thirteen; `docs_guard.py` pass. — **Done.** Commit `2c380991`, twelve files.
      Guard unchanged: same three designed pre-fix hits, no new ones, `links` still hard zero.

## Phase 4 — Sweep `architecture/`

**SC-037 · SC-038 · SC-039 · SC-040 · SC-041.** Same shape as phase 3, different files. `domain-model.md`
has drifted from five of the seven contexts.

- [x] **`ProcessingJob` is created per confirmed upload, whatever the capability** (SC-037). The capability
      decides which *exit* the job takes, not whether it exists. Fix the host attribution
      (`ProcessingWorker`, not `EventConsumers`) and the four-event "key domain events" list.
      ✅ `domain-model.md § ProcessingJob` agrees with `processingjob.write-model.md`.
- [x] **The saga owns the branch, not the worker** (SC-038). Delete ", with `AssetProcessingWorker` as
      defensive fallback" from `asset.write-model.md:89`; rewrite `domain-model.md:377` to name
      AssetManagement's three handlers. ✅ No file credits the Processing Worker with dispatching an
      AssetManagement command.
- [x] **`domain-model.md § Registration` × 4** (SC-039). `RegistrationSubmissionRecorded` moves
      `Submitted → PendingConfirmation`; amendments are scoped to `Confirmed`; `RegistrationAmendment`
      becomes `Amendment` with `DecisionNotes` and files as a value object; drop "the primary item plus".
      ✅ `Confirm` and `Reject` are reachable, which they are not as written.
- [x] **`domain-model.md § DocumentSigningSession`** (SC-040). Delete the `OwnerId` row; retype
      `InitiatedBy` to `MemberId` and `SignedAssetId` to `AssetId?`; redraw the lifecycle with all eight
      enum members under their enum names; drop `OwnerId` from `bounded-contexts.md:354`. ✅ The phantom
      the API file argues against appears nowhere.
- [x] **Two `system-architecture.md` diagrams** (SC-041). Redraw both `AssetIngestionSaga` rects with
      AssetManagement as a participant; `:490` dispatches against `ProcessingJob`; `:493` reads
      "state → Failed". ✅ Neither diagram shows a cross-context command dispatch, and neither names a
      state the transition table lacks.
- [x] **`bounded-contexts.md` scanner registration** (SC-050, second half). Add the signing scanner.
      ✅ `documentsigningsaga.md:108`'s expiry rule has a host. — **Done**, registered as
      `DocumentSigningTimeoutScanner`, matching the name the repo `CLAUDE.md` already uses for it.
- [x] **Phase exit.** ✅ All six; `docs_guard.py` pass. — **Done.** Commit `00035fdb`, four files. Guard
      unchanged. `SignedAssetId` needed no retype — it was already `AssetId?`, so only `InitiatedBy` moved.
      The `Amendment` row's Entity/value-object justification was rewritten rather than just relabelled:
      leaving "**Entity.** `AmendmentId` is a stable identifier…" under a value-object ruling would have
      filed it one way and argued the other. It is now stated as a value object addressed by identity,
      which is the pattern `ReviewerAssignment` already uses.

## Phase 5 — Navigation

**SC-042 · SC-043 · SC-044 · SC-045 · SC-046.** `README.md` and `glossary.md` — the two files whose only
job is to send a reader to the right place. **SC-042 first:** eleven pointers at a deleted file is what
actively misleads a new reader on day one.

- [x] **Repoint the `system-spec.md` citations** (SC-042). Eight glossary Authority cells —
      `TenantId`, `OwnerId`, `IActor`, `System actor`, `Event Store`, `Projection`, `tier-policy`,
      `Alias (OpenSearch)` — plus `system-architecture.md:746`, `api-conventions.md:57` and
      `api-conventions.md:989`. **Twelve, not eleven:** phase 0's detector found a twelfth at
      `glossary.md:4`, in the prose sentence about competing tables, which the review's count missed.
      ✅ Phase 0's `references` check returns zero. — **Done, and the check does return zero.** The
      twelfth, `glossary.md:4`, was change narration as well as a dead pointer — it described what the tree
      used to look like — so the preamble was rewritten to state the present rule rather than repointed.
- [x] **Settle the saga count** (SC-043, Q15). `README.md:85` loses "a design record for a saga that does
      not exist"; row 12's parenthetical names both sagas; `glossary.md:98` says two. ✅ Three statements,
      one answer.
- [x] **Fix the design-decisions rows** (SC-044). Row 14e and the file-tree annotation name `MediaProfile`
      and `RetentionSchedule`, not RecordType. Either write the promised note at the foot of
      `recordtype.write-model.md` or drop the "see the note" clause from `Metadata/context-overview.md:260`.
      ✅ Both rows name files that exist. — **Done.** The "see the note" clause was dropped rather than the
      note written: the note would have been a pointer to an absence, and the absence is better stated
      where the reader already is.
- [x] **Two counts** (SC-045). "Two things are known to be wrong" lists one — restore the second item or
      change the number. Row 10's "seven internal" becomes ten. ✅ 7 + 10 = 17 reconciles in the row that
      claims it. — **Done**, changed to "one thing". The surviving bullet also carried the `2026-08` the
      `dates` detector fires on, plus the change narration around it ("five once carried a note… and the
      note is retired"), so the bullet was restated in the present tense. **That is what closes the `dates`
      hit**, and it was not separately listed as a finding.
- [x] **Three glossary rows** (SC-046). `ReviewSession` gains `Id`, `SessionEditorsOrNull?` and
      `EditSessionChangeRequestId?`; `SigningSessionStatus` is a domain value object projected onto the read
      models, keeping "not a saga status"; `ProcessingJob` gains `Bypassed`. ✅ Each row agrees with the
      file its own Authority column names. — **Done.**
- [x] **Phase exit.** ✅ All five; phase 0's two navigation detectors return zero. — **Done.** Commit
      `14f9beb6`, five files. **`dates` and `references` both return zero**, each having fired on exactly
      its known instances before this commit — which is the before/after proof phase 0 was sequenced for.
      Only `truncation` still fires, on `asset.api.md:768`, closed in phase 9.

## Phase 6 — Authorization

**SC-008 · SC-013 · SC-022 · SC-025 · SC-029 · SC-030.** The residue MM-003 phase 4 left. ~~Blocked on the
one confirm in phase 1~~ — **Q3's encoding was confirmed 2026-09-18 as the plan reads it. Nothing in this
phase waits on anyone.**

- [x] **`DocumentSigningSession` gains an owned subset** (SC-008, Q5). Move the row out of
      `api-permissions.md` § Resources with no owned subset; define `.Read.All` and `.ReadWrite.All`; owned
      set is "sessions the caller initiated". Add the missing `**Errors:**` line to the detail route
      (SC-019 in the review's Group C is a different item — this is the read refusal at
      `documentsigningsession.api.md:218-239`). ✅ A `MediaAdministrator` can read a session they did not
      initiate, and the runbook is performable.
- [x] **Force-release** (SC-025, Q3). `MediaItem.Manage` plus `item.OwnerId == actor.Id`, widened
      tenant-wide by `MediaItem.Manage.All`. Delete `mediaitem.api.md:147`. ✅ Owner and administrator are
      both admitted, stated once, in the existing grammar. **Do not start before phase 1's confirm.**
- [x] **Registration `.All` widens** (SC-029, Q4). `CheckOwner` gains the third branch; the api rows and
      `error-catalog.md:508` widen. **State explicitly in `registration.api.md` § Authorization that a
      `ReadWrite.All` holder can submit and cancel another officer's live filing** — it is a real
      consequence on statutory filings and must not be left to be inferred. ✅ The sentence exists.
- [x] **Registration's missing 403s** (SC-022). Add `403 SystemActorRequired` to the five `[System]` routes
      and to § Registration; state the erase route's 403; widen the four-code rule. ✅ Every specified
      refusal has a code and a status.
- [x] **Registration's enforcement point** (SC-030). `actor_type = "System"` is checked in the handler
      after the registration loads, per PERM-2 and § Guard evaluation order — not at the edge.
      ✅ `write-model.md:362`'s pointer resolves to something that agrees with it.
- [x] **Drop ProcessingJob's actor rule** (SC-013, Q6). Remove it from `processingjob.api.md:65-82` and the
      eight-row table. ✅ No unenforceable authorization rule remains;
      `api-permissions.md:116-126` stands alone. **`SystemActorRequired` is untouched** — it stays live for
      Registration.
- [x] **Phase exit.** ✅ All six; every route in the ten `<agg>.api.md` files carries a permission and,
      where the resource is owner- or membership-scoped, a predicate. — **Done.** Commit `a3527d5a`, seven
      files. Two additions beyond the review's text, both forced: `api-permissions.md`'s two table counts
      moved with the row ("these four" was already a five before the move, so it is now correct for the
      first time), and `SystemActorRequired` gained a § Registration catalogue row, without which the five
      routes' new `**Errors:**` entries would have pointed at nothing. The detail route's `404` is left
      untagged — there is no `SigningSessionNotFound` in the catalogue and inventing one to fill the slot
      is the wrong direction.

## Phase 7 — The rendition trigger

**SC-016 · SC-017.** Design work, not an edit. The largest hole in the tree: the pipeline's productive half
has a specified output and no specified input.

- [x] **Widen the `media-processing` filter** (Q8). It admits `media.asset.upload-confirmed` **and**
      `media.processingjob.started`; `ProcessingWorker` branches on message type. Change the "one type only"
      statement in all four places: `event-store-and-messaging.md:266`, `:287`,
      `system-architecture.md:292`, `:698`. ✅ `AssetProcessingWorker` has a stated trigger, and the saga's
      bypass-vs-start decision gates it. — **Done, and it was six places, not four.** The review named
      `event-store-and-messaging.md:266`, `:287`, `system-architecture.md:292` and `:698`; the sweep also
      found `system-architecture.md:663` (the mermaid filter label), `:710` (a **second** queue table in the
      same file), `context-overview.md:68` and `processingjob.write-model.md:260` ("driven by **one**
      event"). A filter stated in eight places is why this took a phase.
- [x] **Give `media.processingjob.started` its second consumer.** It currently routes to AssetManagement
      only. ✅ The routing row names both, and the `media-processing` filter matches. — **Done.**
- [x] **Rewrite the pipeline diagram** (`context-overview.md:88-130`). `[ProcessingWorker terminates here]`
      is correct for the scan invocation; the rendition block is a **second** invocation and must be drawn
      as one, not as an unindented continuation. `:119`'s "in-process; not separately triggered" goes.
      ✅ A reader can trace the trigger for every box. — **Done.** The second invocation is drawn as its own
      top-level block, and the reason it must be separate — the capability is resolved and the branch taken
      after invocation 1 ends — is stated under the diagram rather than left to be inferred.
- [x] **Settle the video branch** (SC-017). The worker blocks on MediaConvert in-invocation and extends
      visibility to 4 h, which `system-architecture.md:292` already states. **Remove "completion via
      EventBridge → SQS"** from `context-overview.md:121`. ✅ No file implies an inbound MediaConvert leg;
      `§ External Dependencies` needs no new row. — **Done.** The Rendition Tools row for video also said
      "(async)", which read as the same claim; it now names the in-invocation wait.
- [x] **Re-read P-3.** The orphan scenario is built on the absence of a callback. With the blocking design
      it is a visibility-timeout expiry instead. ✅ P-3 describes a reachable fault. — **Done.** The fault is
      now the encode outlasting the 4-hour visibility ceiling, so the invocation ends without dispatching a
      completion. **The recovery path improved with it:** a redelivery that finds the encode finished
      dispatches `CompleteProcessingJobCommand`, which is what raises `ProcessingJobTimeoutRecovered` —
      previously that late success had no stated sender.
- [x] **Phase exit.** ✅ All five; the four "one type only" statements agree. — **Done.** Commit `5fb33086`,
      five files. **Eight statements, not four** — see the first box. Guard passes.

## Phase 8 — Design items

**SC-018 · SC-026 · SC-033 · SC-035.** Four findings where the answer creates work rather than closing it.
Sized separately because each needs a decision inside it.

- [x] **Auto-submit is inert under review** (SC-018, Q10). One sentence in `mediaprofile.api.md:399` and the
      write model's auto-submit paragraph. **Then settle `Governed Media Record`:** it sets
      `RequiredForPublish` and `AutoSubmit ✓`, so the flag now claims a behaviour that never happens on it.
      Withdraw the flag, or state why it is carried inertly. ✅ No seeded profile claims a behaviour it
      cannot perform. — **Done; the flag was withdrawn.** Stating it as carried-inertly would have left the
      defaults table advertising a behaviour a reader has to cross-check another rule to discount.
- [x] **`ProfileOrigin` guard at command level** (SC-026, Q7). Add it to
      `mediaprofile.write-model.md § Handler-side Pre-conditions`. **Specify the seeder exemption
      precisely — it is the hole.** ✅ `mediaprofile.defaults.md:31`'s "whatever permission the caller
      holds" reads true, and the seeding procedure at `:164` is buildable against the stated guard.
      — **Done. Chase chose the System-actor exemption** over a before-first-publish window or naming the
      seeder class. It reuses the mechanism that already gates `ForceReleaseCheckout` and Registration's
      decision routes; it leaves `defaults.md:31` true as written, because an actor type is not a
      permission; and it is not a lifecycle window, so a seeded profile is no more mutable on day one than
      a year later.
- [x] **Delete `Compensated`** (SC-033, Q12). Remove the row from § State Table; the unconditional row
      leaving `Releasing` then reads correctly. **The runbook at `:240-243` must say where the real outcome
      is read** — the session aggregate's own status. ✅ Every state in the table is reachable, and the
      runbook answers what happened. — **Done.** The runbook now opens by telling an operator to start from
      the session rather than the saga. **A second site of SC-046 was corrected alongside:**
      `documentsigningsaga.md:66` also called `SigningSessionStatus` a read-model status, which would have
      left the saga file and the glossary disagreeing the moment phase 5 landed.
- [x] **Add reviewer withdrawal** (SC-035, Q11). A remove-reviewer command, its event, a route, a
      permission row, an error code, and a roster rule. **Sub-decision inside this item:** removing the last
      reviewer on a `RequiredForPublish` item must either be refused or must block publication —
      `MinimumReviewersRequired` already exists and the interaction has to be stated. ✅ `Withdrawn` is
      reachable, and "every non-withdrawn reviewer" carries a real distinction in all three files.
      — **Done. The sub-decision: refuse the withdrawal**, with `MinimumReviewersRequired` — the same code
      publication raises, because it is the same rule arriving from the other direction, so no code was
      added. **What settled it:** the roster is set once by `RequestPublication` and **no command adds to
      it**, so an emptied roster would strand the item in `PendingApproval` with nothing able to move it.
      Shipped as `DELETE /v1/items/{itemId}/reviewers/{reviewerId}`, `WithdrawReviewerCommand`,
      `ReviewerWithdrawn`, taking `MediaItem.Manage` plus the owner predicate rather than roster membership
      — changing a roster is not a reviewer's own act. The assignment stays on the roster as `Withdrawn`
      rather than being removed, so the record of who was asked survives.
- [x] **Phase exit.** ✅ All four, each with its sub-decision recorded rather than left implicit.
      — **Done.** Commit `b8e32612`, seven files. Guard passes.

## Phase 9 — Remaining per-context corrections

**SC-014 · SC-015 · SC-019 · SC-020 · SC-021 · SC-024 · SC-027 · SC-028 · SC-031 · SC-034 · SC-036 ·
SC-049.** Twelve corrections, no decisions. Independent of each other; work in any order.

- [x] **Catalog × 5.** Declare `PinnedRecordTypes` across all five layers (SC-014). Add
      `MediaItemVersionPurged` to the summary projector (SC-019). Replace "Mark deleted" with the concrete
      DELETE (SC-020). `PUT …/metadata` merges — delete `mediaitem.api.md:449` (SC-024, Q9). Delete
      `mediaitem.scenarios.md:496`'s claim that nothing reads `ReviewPolicy` (SC-027). ✅ Each names a
      member or event that exists.
- [x] **Registration × 3.** Project `RegistrationPersonalDataErased` and make the cleared members nullable,
      **and state what `RegistrationByOwnerIndex` holds for an erased row** (SC-021). `InvalidStatusTransition`
      carries root-level `currentStatus`; fix `error-catalog.md:514` (SC-028). Drop the two statutory-retention
      claims (SC-031). ✅ Erasure is implementable; the catalogue agrees with itself. — **Done.** The one
      judgement call in this phase: **`RegistrationByOwnerIndex` drops the row on erasure** rather than
      taking a sentinel partition. The review framed this as a design step and no answer covers it; removal
      was chosen because the partition key interpolates the field the event clears, so a sentinel would be
      a grouping that erasure exists to destroy, and `write-model.md:554` already says every owner-scoped
      route on an erased registration is refused. **Reverse it if you want the row findable after erasure.**
- [x] **AssetManagement × 3.** `FailAssetProcessing`'s accepted statuses stated once, with the two missing
      transition edges added (SC-034). Five quantities and four status codes (SC-049) — 100 not 50,
      15 minutes not 1 hour, ≥ 100 MB not 50 MB, `201`/`204` not `202`. **Repair the truncated link and the
      duplicate traceability table** at `asset.api.md:768` and `:973`. ✅ Phase 0's unclosed-`](` check
      returns zero. — **Done, and it does.** The duplicate table was merged into the first rather than
      deleted — its two bulk rows are real — and § Related moved to the end of the file, which is where the
      truncation had stranded it mid-document. **A fifth status-code site** was corrected alongside the four
      named: the single-part initiate scenario at `:63` and the legend at `:31` both showed `202` where the
      endpoint declares `201`. Same finding, sites the review's enumeration missed.
- [x] **Metadata + DocumentSigning × 2.** Restate the terminal-state contract in terms of `Status`, not the
      two flags that were decided against (SC-015). `Cancelled` is reachable only from `Initiated` or
      `EnvelopeCreated` (SC-036). ✅ Both agree with the models they describe.
- [x] **Phase exit.** ✅ All twelve; `docs_guard.py` pass on seven checks. — **Done.** Commit `305f5596`,
      fourteen files. **The guard now passes outright** — all seven checks at zero, baseline still empty.
      All three phase-0 detectors have gone fired → zero on their own instances, which is the whole
      before/after proof the phase was sequenced for.

## Phase 10 — Re-baseline

- [x] **Run all seven checks** against a tree that now contains a declared `RetentionScheduleRef`, a
      widened queue filter and a new reviewer-withdrawal command. ✅ All seven return zero. — **Done. Pass.**
- [x] **Re-run MM-005's three shape-based greps** — codes against the catalogue, permissions against the
      vocabulary, plain-text `.md` references. ✅ Each returns zero real hits, and any stated absence is
      stated in the file that uses it, as `security-scenarios.md:154` does. — **Done.**
      - **Plain-text `.md` references: zero** (the `references` check).
      - **Permissions against the vocabulary: zero.** Every `X.Tier[.All]` named in an api Authorization
        table resolves, including the `.All` forms the vocabulary defines as "each with `.All`" rather than
        writing out.
      - **Codes, forward direction: one hit, and it is the blessed one.** `ReviewerSelfApproval` at
        `security-scenarios.md:184`, whose own file states the exception at `:154` — exactly the pattern
        this box calls correct.
      - **Codes, reverse direction: six real hits, diverted.** See below.
- [x] **Spot-check the fourteen shared-layer findings.** Every `shared/` and `architecture/` file that was
      wrong now points at its owning file rather than summarising it. ✅ A named reviewer confirms, file by
      file. — **Done by independent verification, accepted by Chase 2026-09-18.** Eleven confirmed, three
      partial, all three partials closed in commit `638ba5ce`. The pass also returned seven findings nobody
      asked it for, five of which became phase 11 and two of which were defects in this plan's own edits.
      The files to walk, if it is ever re-run: The files to walk, with what to
      check in each: `saga-patterns.md` (four points, each deferring to its saga file), `cascade-rules.md`
      (two paths distinguished; `ArchiveFolderNodeCommand`), `cross-aggregate-invariants.md` (the gap is
      first assignment, not removal), `event-store-and-messaging.md` (explicit five; one signing queue; two
      new routing rows), `error-catalog.md` (five rows added, two removed), `api-conventions.md` +
      `consistency-model.md` (eleven), `domain-model.md` (ProcessingJob, Registration, DocumentSigning),
      `system-architecture.md` (both saga diagrams), `bounded-contexts.md` (scanner registration; the
      lookup shape).
- [x] **Baseline still at its floor.** ✅ `docs-guard-baseline.tsv` has zero accepted entries. A growing
      baseline means the guard is being talked out of its job. — **Done. Zero.**
- [x] **Phase exit.** ✅ All four. — **Done.**

> **Diverted from phase 10 — six catalogued codes with no raise site anywhere in the tree.**
> `DuplicateTitle`, `EnvelopeNotFound`, `FolderNotEmpty`, `MediaItemAlreadyExists`,
> `ProcessingJobNotFound`, `ProcessingJobStatusInvalid`. This is the same class as SC-023's
> `CheckoutRequired`, which the review caught because it extracted from `**Errors:**` lines; a whole-tree
> grep finds six more, so `error-catalog.md:3-5`'s exhaustiveness claim is still untrue in the reverse
> direction. **A new defect never becomes a checklist item in the plan that found it** — this goes to a new
> review. `NotFound` is not among them: it is a generic cross-cutting row that routes reach by listing a
> bare `404`.

## Phase 12 — the two undeclared migrations

Found by asking what the spec now commits the *implementation* to, which is a different question from
whether the spec is coherent. Two of this plan's own changes remove a field from a shape held in the event
store, and both were written as clean deletions. **The obligation would have reached whoever built them on
the first replay of an old stream.**

- [x] **`MediaProfilePublished` gains an upcaster note.** The event carries the compiled template on
      `PublishedSnapshot.CompiledTemplate`, which held `Capabilities` until phase 2. Every published
      profile in every tenant has such a stream. The upcast drops the member; the set the snapshot needs is
      the profile's declared one, which the same event already carries.
- [x] **The signing saga's `Status` says that `Compensated` is a removed enum member**, not an absent one.
      The name is persisted in `media-sagas`, and one that no longer resolves throws on load rather than
      defaulting. Rows carrying it are terminal and map to `Completed`.
- [x] **Phase exit.** ✅ Guard passes; commit `8004872a` on `spec/initial-alignment-work`.

## Phase 11 — scope widened by Chase, 2026-09-18

**Three things that the standing rules would have sent to a new review stay here instead, on Chase's
explicit instruction.** Recorded rather than done silently: the rule is *a new defect never becomes a
checklist item in the plan that found it*, and this phase sets it aside deliberately for three batches.

- [x] **The five contradictions the independent verification found on its own** — commit `26903d38`.
      `ChangeRequestApproved`/`Rejected` routing rows for events that do not exist; the validation-timeout
      row dispatching the **reversible** category on a strictly-terminal path; registration events routed to
      a SagaOrchestrator whose allowlist admits none of them; both queue inventories incomplete and both
      written as authoritative; and `ApproveMediaItem via saga` offered as an example of a System command
      when the review saga was deliberately removed.
- [x] **The six catalogued codes with no raise site** — commit `c916b185`. Two got tagged raise sites
      (`MediaItemAlreadyExists`, `DuplicateTitle`), one was removed as ruled out by its own caller-action
      column (`FolderNotEmpty`), two got a § Refusals section stating that a pipeline-internal aggregate has
      no HTTP surface to list them on (`ProcessingJobNotFound`, `ProcessingJobStatusInvalid`), and one now
      states its own absence (`EnvelopeNotFound`). **Reverse-direction orphans: 19 → 2**, and both remaining
      state the absence in the file that owns them, which is the `security-scenarios.md:154` pattern.
- [x] **MM-005 § Could not settle, all eleven, answered by design** — commit `1bceb178`. Chase's
      instruction was to work each through from what the spec already commits to rather than reading code.
      Two were load-bearing on work already committed: **#2** confirms phase 7's blocking design (the
      1800 s visibility bounds the second invocation), and **#8** confirms the phase 9 erasure work and adds
      the half that was missing — `/search` reaches an erased row only for a `.All` holder or a System
      actor. **#4** was the one with a real race: `SaveAsync` writes conditionally on `Version`, because
      guards make *duplicate* delivery safe and do nothing for *concurrent* delivery, which is exactly the
      shape of two `SignerCompleted` callbacks.
- [x] **SK-7, which was not one table** — commit `77333c74`. MM-005 recommended folding the `media-assets`
      key disagreement into MM-004. Checking before editing found that `system-architecture.md` and
      `event-store-and-messaging.md` each carry a **full projection-key inventory**, both written as
      authoritative, disagreeing across ~15 tables in PK as well as SK — and not as typos but as **two
      complete, mutually exclusive designs**. One category-partitions everything; the other puts the id in
      the partition for a detail row and reserves the collection partition for lists.
      **Settled two ways, both pointing the same direction.** On the merits: category-partitioning detail
      rows makes DynamoDB's per-partition throughput and 10 GB limits into tenant-wide ceilings, which is
      the wrong trade on a platform sized for large tenants, and `TENANT#{TenantId}#{EntityId}` is the rule
      the repo `CLAUDE.md` already states. On ownership: `event-store-and-messaging.md:377` declares itself
      the authoritative inventory and defers to `system-architecture.md` for write-side reference indexes
      only. So the duplicate goes, the owner is completed with the six bulk-import tables only the
      duplicate carried, and the three key rules are stated once where they belong.
      **No key shape was changed** — a deployed key is data, not prose. Two internal inconsistencies
      survive in the owner and are noted below rather than edited for the same reason.
- [x] **Phase exit.** ✅ Guard passes on all seven checks; baseline still zero.

> **Left standing deliberately, for a review that can read the schema classes.** `media-record-type`'s PK
> carries both the entity name and the id (`TENANT#{t}#RECORD_TYPE#{RecordTypeId}`) where the rule above
> would give `TENANT#{t}#{RecordTypeId}`; and `media-signing-sessions` is named as a list table while
> partitioning per session, which no list query can use — it is really the summary half of a two-row-type
> partition it shares with `media-signing-session-detail`. **Both are key shapes, so both are migrations,
> and neither is a wording fix.**

---

## Closing out

This plan moves to `done` only after **Chase agrees the work is implemented and complete** — not when the
last box is ticked. The close-out card comment records every branch it was committed to. The review and
plan folders then archive together into `_archive/reviews/MM-005-spec-coherence/` and
`_archive/plans/MM-006-spec-coherence/`, each prefixed with its own id, both keeping the workstream name.

**There is no external gate on this plan.** Unlike MM-003, nothing here waits on a package release, and
`status: done` needs no dependency to resolve first. If a phase cannot be finished, that is a decision to
record — not a box to tick.

### What must not be lost

Three things in this plan are easy to drop and expensive to re-derive:

- **Phase 2 rewrites § Capabilities once.** If phases 2's four items are split across sessions, the count
  in `mediaprofile.write-model.md:177` will be wrong at least once and probably twice.
- **Phase 6's two explicit sentences.** Q4's consequence — a `Registration.ReadWrite.All` holder acting on
  another officer's live statutory filing — and Q5's, if it had gone the other way. An accepted consequence
  that nobody wrote down is indistinguishable from one nobody noticed.
- **Phase 7 is design, not an edit.** Sizing it as a filter change because the *mechanism* is a filter
  change will underestimate it: the pipeline diagram, P-3, the video branch and four "one type only"
  statements all move with it.

---

## Session log

**2026-09-18 — plan authored.** Consumes MM-005 (50 findings; fifteen questions answered the same day).
Dependency gate run: `depends-on` empty, no external blocker, `status: active`. Branch
`spec/coherence-remediation`, to be cut from `develop`.

**Deviation recorded:** the detectors move from MM-005's suggested step 8 to phase 0, on MM-003's phase 0
precedent. Two of the three catch classes this plan edits, so landing them last would mean fixing the
instances without the guard.

**Diversion recorded (Q1).** With `RecordType` carrying no capability set, Catalog's `Processing` gate has
no input and `Capabilities.Contains("Processing")` is permanently false. **That is a code question and it
goes to MM-002**, not into this plan — per the standing rule that a new defect never becomes a checklist
item in the plan that found it.

**Two findings were added after MM-005's fan-out**, both on 2026-09-18 and both folded into the review at
hand-over. **SC-050** was raised by the answer to Q15; it is carried across phases 3 and 4 because its two
halves live in different files. **SC-051** — the idempotency residue in two aggregate api files — was lost
to working-id reuse during reconciliation and recovered when the id was quoted and did not match. MM-005
§ Method note records both mechanisms. **SC-051 is the one finding in this plan that touches MM-003:** its
fix should land before MM-003 phase 10 box 3 runs, and that box's scope should widen from one file to
five.

**One item is open on Chase (phase 1):** confirming Q3's encoding. It blocks the SC-025 item in phase 6 and
nothing else.

---

**2026-09-18 — session 2. Dependency gate run: `depends-on` empty, `blocked-by-external` empty,
`status: active` unchanged. Phase 0 landed.**

**Deviation — the branch is cut from `spec/initial-alignment-work`, not `develop`.** The plan said
`develop`, and that is wrong on the facts: `develop` carries none of MM-003's work. It has **no
`docs_guard.py`**, no `docs-guard-baseline.tsv`, and 74 spec files against MM-003's 82 — the branch is 59
commits behind `spec/initial-alignment-work`. Every premise phase 0 rests on (a guard passing five checks,
a baseline at its floor, MM-003 phase 5's conformant idempotency contract for SC-051 to sweep toward) is
true only on MM-003's branch, and all 51 of MM-005's `file:line` citations were taken there. The branch was
cut from `develop` first, found bare, deleted, and re-cut. **Consequence to carry:** MM-006 is stacked on an
unmerged branch and cannot reach `develop` before MM-003's does. That is a merge-order fact, not a
dependency — nothing in this plan waits on `AP-001`, and `depends-on` stays empty.

**Correction — seven checks, not eight.** Phase 0's own bullet says to add the year-month form as an
*alternative* inside `DATE`, which is the right place for it: a partial date is a date, and a second date
check would be a structural smell. So five registered checks become seven, covering eight detection
classes. The three acceptance criteria that said "eight checks" (phase 0 exit, phase 9 exit, phase 10 box
1) are corrected in place.

**Widening recorded — `references` resolves against the whole repo, not only `docs/`.** The literal wording
was "resolves to a file under `docs/`". Two live references defeat it: `system-architecture.md:424` names
`DEPLOYMENT.md`, which exists at `src/hosts/EventConsumers/DEPLOYMENT.md`, and `operations.md:301` names
`src/tools/ProjectionReplay/RUNBOOK.md`, which exists. Both are resolvable pointers and neither is a
finding. A bare family name (`write-model.md`, `api.md`) resolves by suffix for the same reason. One
allowlist entry survives: `deploy-runbook.md`, which is real but lives in the docs project, not this repo.

**SC-042 is twelve citations, not eleven.** The detector found `glossary.md:4` — prose, not an Authority
cell — which the review's count missed. Phase 5's box is corrected.

**The guard is red on this branch until phases 5 and 9 land, and that is the designed state.** Phase 0's
exit expects three pre-fix hits, so the hand-over's "phase 0's workflow must run green before phase 2" is
not satisfiable as written; what phase 0 actually guarantees, and what it was moved first for, is that the
detectors exist before any spec file is edited. The three expected hits are named under phase 0. **A fourth
hit is a regression.**

**Phase 2 closed, and it needed a sixteenth answer.** Q1 rules that `RecordType` has no capability concept,
which leaves `CompiledMetadataTemplate.Capabilities` — the member `MediaItemCreated` embeds and the
`Processing` gate reads — with no source. Deleting the union without saying what replaces it would have
widened the hole rather than closed it, so the work stopped and asked. **Chase's answer: remove
`Capabilities` from `CompiledMetadataTemplate` entirely.** The compiled template is the merged field schema;
`Publish` sources `MediaProfileSnapshot.Capabilities` from the profile's declared set, the way the snapshot
already takes `CheckoutPolicy`. No downstream consumer moves.

This was chosen over the "fix candidate" already written at `mediaprofile.design-decisions.md:90` — make
`ToSnapshot()` emit the declared set but keep the member — because that leaves one value with two homes,
which is how the bug arose: a capability list sitting beside a field list gets merged like one. **The
consequence worth keeping:** a capabilities-only profile that pins no RecordType now carries every
capability it declared instead of compiling to `[]` and silently taking the bypass.

**Diversion raised on MM-002 (Q1's code defect), with a narrower brief than the review gave it.** The
review left it as "where does Catalog's `Processing` gate read its input from" — an open question. The spec
now answers it, so the code item is: the gate must read the profile's declared set, not a union over pinned
RecordType versions.

**Phase 3 closed, thirteen findings, commit `2c380991`.** Three departures from the review's text, each
because the text was wrong on a detail rather than because the ruling was: `DeclaredSizeExceeded` and
`ProfileLimitExceeded` are already catalogued under § Batch Operations, so only two codes were genuinely
missing; deleting the per-item `QuotaExceeded` row left the request-level one uncatalogued, so a row was
added for it; and `consistency-model.md`'s "every other write" clause had to move with the eleven, since
naming eleven mandatory routes makes that clause false where it stands. **`IdempotencyKeyRequired` was not
placed** — no endpoint declares the key required, and listing the code on a route that accepts it
optionally would be a false statement. The absence is stated where it belongs, in `api-conventions.md:145`.

**Phases 4, 5, 6 and 9 closed the same day, commits `00035fdb`, `14f9beb6`, `a3527d5a` and `305f5596`.**
**The guard now passes outright** — seven checks, all zero, baseline still empty. Each of the three phase-0
detectors fired on its known instances and then returned zero once its phase landed, which is the
before/after proof the detectors-first ordering existed for.

**Small corrections to the review's text, made where the text was wrong on a detail rather than the
ruling.** `SignedAssetId` was already `AssetId?` and needed no retype. `api-permissions.md`'s "these six"
was a five before SC-008 moved a row out of it. SC-049 had a fifth status-code site the enumeration missed
— the single-part initiate scenario and the file's own legend. And the `Amendment` row's justification had
to be rewritten rather than relabelled: leaving "**Entity.** `AmendmentId` is a stable identifier…" under a
value-object ruling would file it one way and argue the other.

**All three flagged judgement calls settled by Chase 2026-09-18, commit `a021eda1`.**

1. **`metadata-schema-composition.md` stays revised in place**, and the **ADR index row now records the
   revision** — which was the half that was actually missing. The repo's convention decides this: ids are
   closed, no new number is ever minted, a new decision goes in as a `##` section of the topic document it
   belongs to, and a *new* document is for a ruling that could be superseded on its own. The same row
   already recorded a 2026-09-09 in-place revision of this file, so the precedent was on the document
   itself.
2. **The retention pin takes the record-type pin's guard** — must resolve, must not be deprecated, on
   `SetRetentionSchedule` and `PublishMediaProfile`. It costs **no new error code**: like every other rule
   in that table it returns an untagged `422 InvalidOperation`, so Q2's "publishing gains no refusal"
   stands. `retentionschedule.design-decisions.md` had already committed to reusing `RecordType`'s
   lifecycle wholesale, so reusing its guard is the consistent move rather than a new one.
3. **The erased registration's row leaves `RegistrationByOwnerIndex`**, confirmed. The argument is stronger
   than when it was first written: the index serves one query, `ListRegistrationsByOwnerQuery`, and after
   erasure **there is no `ownerId` for anyone to pass** — so nothing usable is lost, and the row stays
   reachable by id, by `mediaItemId` and through search. A sentinel partition would collect every erased
   registration in the tenant into one key: a hot partition, and a standing list of whose data was erased,
   produced by the operation that erased it.

**Phases 7, 8 and 10 closed, commits `5fb33086`, `b8e32612`. Ten of eleven phases done; the guard passes
on all seven checks with the baseline still at zero.**

**Phase 7 was eight statements, not four.** The review named four "one type only" sites; the sweep found
`system-architecture.md:663` (a mermaid filter label), `:710` (a **second** queue table in the same file),
`context-overview.md:68` and `processingjob.write-model.md:260` as well. A filter stated in eight places is
why a filter-policy change took a phase — which is what § What must not be lost warned about.

**Phase 8's two decisions, both Chase's, both taken against a stated alternative.** The `ProfileOrigin`
seeder exemption is the **actor type and nothing else**, reusing the mechanism that already gates
`ForceReleaseCheckout`; it leaves `defaults.md:31` true as written and is not a lifecycle window. And
withdrawing the last reviewer who could still decide on a `RequiredForPublish` item is **refused** with
`MinimumReviewersRequired` — settled by the fact that the roster is set once by `RequestPublication` and
**no command adds to it**, so the alternative strands the item permanently.

**Phase 10 diverted six findings and left one box open.** The six are catalogued codes with no raise site
— the reverse-direction half of SC-023, which the review under-caught because it extracted from
`**Errors:**` lines only. The open box is the named-reviewer spot-check, which is not something this
session can sign.

**The two judgement calls phase 2 left open are the first two settled above.** Neither was a finding in
MM-005 and neither became a checklist item; both were carried as flagged deviations until Chase ruled on
them.
