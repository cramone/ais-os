---
id: MM-005
type: review
project: magiq-media
workstream: spec-coherence
raised-by: []
status: done
outcome: plan
todo-id: fb73731b-a4e0-5fc7-a934-dd480dfadc98
created: 2026-09-17
---

# Spec Coherence — the shared layer has drifted from the files it defers to

## Scope

**Read:** every file under `D:\source\github\sprbrk-standard\mgq-magiq-media\docs\spec\` — **82 files,
30,875 lines**: 81 markdown plus `recordtype-diagrams.html`. All seven bounded contexts
(`AssetManagement` · `Catalog` · `ChangeRequests` · `DocumentSigning` · `Metadata` · `Processing` ·
`Registration`), all fourteen `shared/` files, all four `architecture/` files, `glossary.md` and
`README.md`. `docs/adrs/` was read where a finding turned on a decision record, not audited in its own
right.

**Guard:** `python .github\scripts\docs_guard.py` returns **pass, five checks, zero new** on the current
tree. Spec purity holds and this review spent no further effort there — except that three of the five
checks were found to have blind spots, which is § Method note, not § Findings.

**Method:** seven subagents, one per bounded context, each applying the nine finding kinds *within* its
context; then a cross-cutting pass over `shared/` and `architecture/` done centrally, which is where
most of what follows came from. ~130 raw candidates were returned; this document carries **51** after
deduplication against MM-001 and MM-004 and against each other. Forty-nine were reported on 2026-09-17;
**SC-050 was raised on 2026-09-18 by the answer to Q15**, and **SC-051 the same day after a reconciliation
error was found** — § Method note records both.

### The headline, because it is not what was expected

**The contexts are in better shape than the layer above them.** Per-context audits came back with long
"reconciled cleanly" sections — Metadata's seventeen-event inventory checks five ways, Catalog's
twenty-eight MediaItem events check four ways, Processing has no timeout disagreement anywhere, the
aggregate inventory reconciles exactly (1+4+1+1+2+1+1 = 11) across `domain-model.md` and all seven
context overviews.

**Fourteen of the twenty-six High findings have a `shared/` or `architecture/` file as the wrong side of
a contradiction with the aggregate or saga file it explicitly defers to** — SC-001 to SC-008, SC-037,
SC-042, SC-043, SC-047, SC-048, SC-050. Three more (SC-011, SC-028, SC-029) have a shared file as one of
several sides, and SC-051 is the mirror image: two aggregate files contradicting a shared one. That is
**eighteen of twenty-six** on the widest honest reading and fourteen on the strict one.
`saga-patterns.md` denies three rules its own saga
files state. `cascade-rules.md` describes the opposite failure handling from `archive-fan-out.md`.
`cross-aggregate-invariants.md` contradicts itself thirty lines apart and describes the inverse of the
archive bug the Catalog files name. `architecture/domain-model.md` has drifted from five of the seven
contexts. `glossary.md` names a deleted file as the Authority for eight terms.

That is a pattern with a cause: **the per-context remediation of MM-003 rewrote aggregate files and the
summaries above them were not swept.** It is also a pattern with a cheap fix — the shared files mostly
need to stop restating what they point at.

---

### What this audit cannot catch

**Scope is spec-internal. `src/` was not opened, not grepped, and no claim was verified against an
implementation.** This has a consequence that must not be papered over:

> **A rule that is specified coherently and implemented differently passes this audit clean.**

Every finding below is a statement about the documents. Where the documents disagree, this review says
which side it believes and why — but "believes" means *which document owns the question under
`README.md`*, not *which matches the code*. Nothing here is evidence about the running system, in either
direction. § What is healthy lists the eleven claims that could not be settled without the code, each phrased as one
answerable question.

Two related limits worth stating:

- **A clean section is not a guarantee.** § Method note names four areas that reconciled cleanly across four or
  five files each. That means the documents agree, nothing more.
- **This review did not re-litigate spec purity, and MM-001's findings were treated as already argued.**
  Twelve candidates were dropped as duplicates of `SB-*` — listed in § Deliberately not raised so nobody re-derives them.

---

## Findings

Severity is `Critical | High | Medium | Low`. `Critical` is reserved for a defect that is live and
exploitable, or that destroys data. **Nothing here is Critical** — this is a coherence audit, and the
worst outcomes below are two engineers building opposite things, not a live exploit.

Findings are numbered `SC-001` onward and grouped by *shape*, because the shape is what decides who
fixes them and in what order.

---

### Group A — the shared layer contradicts the file it defers to

Nine findings. Every one is a cross-cutting file summarising an owning file and getting it wrong. The
fix in most cases is to delete the restatement and keep the pointer.

---

**SC-001**
**Severity** High
**Kind** Contradiction
**Claim** `saga-patterns.md` states `ProcessingJob.Fail()` refuses on a `Queued` job and builds a named
permanent-orphan failure mode on that reading; four files including the aggregate's own write model
specify that it transitions.

**Evidence**
- `shared/saga-patterns.md:90-92` — "**`FailProcessingJob` is not a no-op on a terminal aggregate.**
  `ProcessingJob.Fail()` refuses unless `Status == Running` and returns a failed `Result` that nothing
  inspects. On the validation-timeout path the job is still `Queued`, so the compensation is rejected and
  **the ProcessingJob stays `Queued` forever**."
- `shared/saga-patterns.md:178-180` — "That is a real and separate failure path: a compensating
  `FailProcessingJobCommand` is refused because the job is not `Running`, and the ProcessingJob stays
  `Queued` forever."
- `contexts/Processing/aggregates/ProcessingJob/processingjob.write-model.md:24` —
  "Queued  → (Fail)     → Failed      [terminal — the validation-timeout path; the job never started]"
- `contexts/Processing/sagas/assetingestionsaga.md:152` — "| `Queued` | **Transitions to `Failed`.** The
  validation-timeout path — a job that never started can still fail |"
- `contexts/Processing/aggregates/ProcessingJob/processingjob.scenarios.md:201` — "transitions from
  `Queued` or `Running`, and is **refused** on `Succeeded` or `Bypassed`"
- `shared/error-catalog.md:555` — enumerates the refusals as "…`Complete` from anything but `Running` or
  `Failed(ProcessingTimeout)`, **`Fail` on `Succeeded` or `Bypassed`**" — `Fail` from `Queued` is not among
  them

**Checked** The four-file side against `saga-patterns.md` §§ 90-92 and 178-180; and `README.md:34`, which
scopes `saga-patterns.md` to "the **cross-cutting** rules only, not any one process", while rows 23 and 25
give aggregate behaviour to the write model.

**Why** The outlier is not an incidental sentence — it is the *premise* of a section, used to bound the
scope of that file's own exception-handling rule ("Anyone reading 'the swallowing is fixed' should know
the boundary of that claim"). `saga-patterns.md` is the natural entry point for saga work, so a reader
starts there, believes the validation-timeout path strands jobs, and adds a guard, a repair job or a
status sweep for a condition the aggregate does not produce.

**Ruling** Correction, no decision needed. Rewrite `saga-patterns.md:90-92` and `:178-180`: `Fail()`
transitions from `Queued` and `Running`, is idempotent on `Failed`, and refuses only `Succeeded` and
`Bypassed`. **Keep the surviving general point** — that a refused dispatch is invisible because
`SendAsync(ICommand)` discards the `Result`. Only the worked example needs replacing, and it needs
replacing precisely because it is the one case that does *not* refuse.

---

**SC-002**
**Severity** High
**Kind** A pointer that resolves to the opposite
**Claim** `saga-patterns.md` tells the reader `ForceReleaseCheckout` has nothing to do with signing, in
the section whose only job is to point at the saga whose compensation is built on it.

**Evidence**
- `shared/saga-patterns.md:73-76` — "There is no checkout lock: `MediaItem.ActiveSigningSessionId` is a
  mutual-exclusion flag that *blocks* checkout, not a lock the signing flow acquires, so the compensation
  is `UnlinkSigningSession` and **`ForceReleaseCheckout` has no connection to signing at all**."
- `contexts/DocumentSigning/sagas/documentsigningsaga.md:131-134` — "1. **`UnlinkSigningSession`** →
  `SigningSessionUnlinked`, clearing `MediaItem.ActiveSigningSessionId`. / 2. **Release the checkout** →
  `EditSessionClosed(Reason: ForceReleased)`. / / Order is not optional. Step 1 must precede step 2."
- `contexts/DocumentSigning/sagas/documentsigningsaga.md:139-141` — "`ForceReleaseCheckout` is the same
  command a person may invoke holding `MediaItem.Manage`; here the System actor admits it, and the
  released session's holder is not the caller."
- `architecture/system-architecture.md:620` — "        SO->>MI: ForceReleaseCheckout"
- `shared/api-conventions.md:956` — "Use to test compensation flows (e.g., checkout force-release on
  signing session timeout) without waiting for the real TTL."

**Checked** `saga-patterns.md` § DocumentSigningSaga — three sentences whose stated job is to point at the
saga file — against that file's § Compensation, the compensation diagram in `system-architecture.md`, and
the test-hook description in `api-conventions.md`.

**Why** The premise is right and the conclusion is wrong. `ActiveSigningSessionId` genuinely is not a
lock — which is exactly *why* the saga specifies two acts, unlink then release, and says "Order is not
optional". `saga-patterns.md` reads the first act as the whole compensation and then denies the second. A
reader who takes the cross-cutting file at its word removes step 2 and leaves every signed item checked
out.

**Ruling** Correction. Rewrite to: the flag is not a lock, so the compensation is `UnlinkSigningSession`
first (clears the flag) then `ForceReleaseCheckout` (closes the edit session the initiator opened) —
pointing at `documentsigningsaga.md` § Compensation rather than summarising it.

---

**SC-003**
**Severity** High
**Kind** Contradiction
**Claim** `cascade-rules.md` states that per-child archive failures are swallowed in both workers and the
caller has already received `204`; the file it explicitly defers to specifies that the folder path
collects them in a report and refuses the request `422`.

**Evidence**
- `shared/cascade-rules.md:49` — "**Per-child failures are swallowed** in both workers — logged at
  warning, not collected, not retried, not returned. The caller has already received `204`."
- `contexts/Catalog/sagas/archive-fan-out.md:229` — "**On the folder path the caller also gets it:**
  `422 FolderArchiveIncomplete`, carrying the same summary. A partial folder archive is not a `204`."
- `contexts/Catalog/sagas/archive-fan-out.md:131` — "Both workers return an **`ArchiveFanOutReport`** —
  what archived, what refused, and what was deliberately left alone."
- `contexts/Catalog/aggregates/Folder/folder.write-model.md:255` — "| `ArchiveFolderHandler` |
  `ArchiveDescendantsAsync` | **Blocking** — `FolderArchiveIncomplete` | The cascade returns an
  `ArchiveFanOutReport`; `!report.IsComplete` refuses the whole archive"
- `contexts/Catalog/aggregates/Folder/folder.api.md:386` — "| `422` | `FolderArchiveIncomplete` | The
  cascade could not archive part of the subtree. Descendants that did archive stay archived |"

**Checked** `cascade-rules.md:31`, which says of itself "Full behaviour — traversal, batching, failure
handling, resume, DLQ — is specified in `archive-fan-out.md`"; and `README.md:34`, which assigns failure
and resume behaviour to the saga file.

**Why** The file states its own deference and then contradicts the target on exactly the question it
deferred. A reader taking `cascade-rules.md` at its word builds the folder archive as fire-and-forget and
drops the `FolderArchiveIncomplete` refusal — which is the one guarantee the folder path has
(`archive-fan-out.md:60`: "an archived folder's subtree is fully archived").

**Ruling** Correction. Rewrite `cascade-rules.md:49` to distinguish the two paths: failures are swallowed
on the **collection** path only; on the folder path they ride an `ArchiveFanOutReport` and refuse the
request `422 FolderArchiveIncomplete`.

---

**SC-004**
**Severity** High
**Kind** Contradiction
**Claim** `cascade-rules.md` names `ArchiveFolderCommand` as what the fan-out workers dispatch per
descendant; every Catalog file specifies `ArchiveFolderNodeCommand`, and dispatching the former is the
exact re-entrancy four files exist to rule out.

**Evidence**
- `shared/cascade-rules.md:9` — "`CollectionArchiveFanOutWorker` and `FolderArchiveFanOutWorker` dispatch
  real `ArchiveMediaItemCommand` and `ArchiveFolderCommand` through `ICommandDispatcher`, mutating child
  aggregates."
- `contexts/Catalog/sagas/archive-fan-out.md:91` — "Phase 3 dispatches **`ArchiveFolderNodeCommand`**:
  archive this one folder, no guard, no cascade. It is **deliberately not HTTP-reachable and must not
  become so**."
- `contexts/Catalog/aggregates/Folder/folder.write-model.md:219` — "**`ArchiveFolderCommand` is the entry
  point; `ArchiveFolderNodeCommand` archives one folder and nothing else.** The node command carries no
  registration guard, no subtree cap and no cascade, which is what stops the fan-out re-entering itself
  once per descendant."
- `contexts/Catalog/aggregates/Folder/folder.scenarios.md:67` — "**The cascade is not re-entrant.** Phase 3
  dispatches `ArchiveFolderNodeCommand` … the work is `O(n)`, not `O(Σ subtree sizes)`."
- `contexts/Catalog/aggregates/Collection/collection.scenarios.md:123` — "**`ArchiveFolderNodeCommand` is
  not re-entrant** … It is not reachable over HTTP."

**Checked** The `cascade-rules.md` headline block against the saga file, the folder write model's
§ *`ArchiveFolderCommand` vs `ArchiveFolderNodeCommand`*, and both cascade scenarios.

**Why** These are two different commands with different guards. `ArchiveFolderCommand` carries the
500-folder cap, the registration pre-flight and its own cascade, so dispatching it per descendant is
quadratic and re-entrant. `cascade-rules.md` is the file a reader reaches first for "what cascades" —
README row 7c sends them there.

**Ruling** Correction. `cascade-rules.md:9` reads `ArchiveFolderNodeCommand`.

---

**SC-005**
**Severity** High
**Kind** Contradiction
**Claim** `cross-aggregate-invariants.md` states `FolderMediaItemsIndex` is add-only and handles
`MediaItemCreated` and nothing else; the owning saga file names two removal projectors and describes the
inverse failure mode.

**Evidence**
- `shared/cross-aggregate-invariants.md:178` — "- **`FolderMediaItemsIndex` is add-only.** Its projector
  handles `MediaItemCreated` and nothing else — no removal on archive, delete or **move**. So the archive
  fan-out re-archives already-archived items, and **archives items that have since been moved to a
  different folder**, under their old parent."
- `contexts/Catalog/sagas/archive-fan-out.md:202` — "Note the index is **not** add-only:
  `FolderMediaItemsIndexMoveRemovedProjector` and `FolderMediaItemsIndexArchivedProjector` both remove
  entries. An item moved out of a folder *is* removed. The gap is on the add side, and only for first
  assignment."
- `contexts/Catalog/sagas/archive-fan-out.md:195` — "Phase 2 sources items from `FolderMediaItemsIndex`,
  which is written on `MediaItemCreated` (folder-scoped) and `MediaItemMoved` only."
- `contexts/Catalog/aggregates/Folder/folder.scenarios.md:77` — same index behaviour restated.
- `contexts/Catalog/aggregates/MediaItem/mediaitem.scenarios.md:375` — same, adding "**No projector
  handles `MediaItemAssignedToFolder`**".

**Checked** The § *Stated but not enforced* bullet against the archive fan-out's idempotency section and
the two Catalog scenario files that restate it.

**Why** The two describe **opposite** bugs. Under the shared file the cascade archives items that have
*left* the folder — over-archiving. Under the three Catalog files it misses items that *arrived* after
creation — under-archiving. Only one of those is the bug to fix, and only one of them silently archives a
record nobody asked to archive. Three files including the owner say it is the second, and they name the
two removal projectors the shared file says do not exist.

**Ruling** Correction. Replace the bullet with the gap `archive-fan-out.md:195` states: the index is
maintained on `MediaItemCreated` and `MediaItemMoved`, removal projectors exist, and the hole is first
assignment via `MediaItemAssignedToFolder`.

---

**SC-006**
**Severity** High
**Kind** Contradiction · a quantity stated twice, differently
**Claim** The `media-sagas` SNS filter is a five-type allowlist in four places and four event *families*
in the queue table that owns queue configuration — and the wildcard form admits an event the saga is
specified never to receive while omitting three it needs.

**Evidence**
- `shared/event-store-and-messaging.md:288` — "| `media-sagas` | Media Management |
  `media-integration-events` | Saga-triggering integration events (AssetValidationPassed, ChangeRequest\*,
  Registration\*, ProcessingJob\*) | 300s … |"
- `shared/event-store-and-messaging.md:267` — "├── SQS: media-sagas           → SagaOrchestrator
  (AssetIngestionSaga; 5-entry allowlist)"
- `architecture/system-architecture.md:699` — "| `media-sagas` | … | Allowlist of 5:
  `media.processingjob.created`, `media.asset.validation-passed`, `media.asset.processing-completed`,
  `media.asset.processing-failed`, `media.asset.processing-timeout-recovered` | …"
- `contexts/Processing/sagas/assetingestionsaga.md:197` — "| Source | `media-integration-events`, filtered
  to **5** event types |"
- `contexts/Processing/sagas/assetingestionsaga.md:88-90` — "there is no handler for
  `media.processingjob.bypassed` in `SagaOrchestrator` — nor should there be"

**Checked** `architecture/system-architecture.md:504-508` — "**The five registered handlers, in full:** …
The `media-sagas` queue's SNS filter policy allowlists exactly the five matching `media.*` types —
**adding a handler without adding its `[MessageType]` to that allowlist silently never delivers.**" And
`shared/saga-patterns.md:15-20`, which names no ChangeRequest or Registration saga anywhere in the tree.

**Why** `event-store-and-messaging.md:288` is the row a person editing a filter policy reads, and it is
wrong in both directions: it admits `ChangeRequest*` and `Registration*`, for which no saga handler
exists, and its `ProcessingJob*` wildcard would admit `media.processingjob.bypassed`, which the saga file
says must not reach the orchestrator. Meanwhile it omits the three `media.asset.processing-*` types the
saga needs to close. Under the file's own warning, widening this filter to the stated families delivers
events with no handler and drops the ones that have them. The same file contradicts itself 21 lines
earlier at `:267`.

**Ruling** Correction. Replace the filter cell with the explicit five from `system-architecture.md:699`.
The wildcard form is unsafe **here specifically**, because `media.processingjob.bypassed` is a type the
saga must not receive.

---

**SC-007**
**Severity** High
**Kind** An inventory that does not match itself
**Claim** `media-document-signing` is listed twice, as one queue with two incompatible filter policies, in
both the topology diagram and the queue table of the same file.

**Evidence**
- `shared/event-store-and-messaging.md:259-260` —
  "    ├── SQS: media-document-signing         → SecuredSigning Adapter (SigningSessionInitiated only)
   / └── SQS: media-document-signing → DocumentSigningSaga (nine signing events; the only saga here)"
- `shared/event-store-and-messaging.md:289` — "| `media-document-signing` | Media Management |
  `media-domain-events` | `SigningSessionInitiated` | 300s (≥ Lambda timeout) | 3 |
  `media-document-signing-dlq` | 14 days |"
- `shared/event-store-and-messaging.md:290` — "| `media-document-signing` | Media Management |
  `media-domain-events` | Nine signing domain events | 300s (= Lambda timeout) | 3 |
  `media-document-signing-dlq` | 14 days |"
- `contexts/DocumentSigning/sagas/documentsigningsaga.md:199-201` — "**One queue serves this context.**
  `media-document-signing` carries all nine signing domain events, and both of the context's components
  read from it"
- `contexts/DocumentSigning/sagas/documentsigningsaga.md:215-216` — "**An event missing from this policy is
  not delivered, and the saga stalls silently rather than failing**"

**Checked** The queue-topology diagram and the queue table against the saga's § Transport, which states
the one-queue design explicitly and argues for it.

**Why** One SNS→SQS subscription carries one filter policy. Both rows describe the same physical queue and
the same DLQ. Under the `SigningSessionInitiated`-only row the saga receives one of its nine events and —
by its own § Transport warning — stalls silently on the other eight. The `300s (≥ …)` / `300s (= …)`
discrepancy on one queue is the same duplication showing through: this is an unfinished edit recorded in
both halves.

**Ruling** Correction. Collapse to one diagram line and one table row: `media-document-signing`, source
`media-domain-events`, filter = the nine signing domain event types, consumed by both the SecuredSigning
adapter and `DocumentSigningSaga`. Keep `300s (≥ Lambda timeout)` for consistency with the other rows.

---

**SC-008**
**Severity** High
**Kind** Contradiction
**Claim** `api-permissions.md` states the signing session carries no owner and withholds the `.All` tier
on that basis, while the API file makes ownership the resource predicate on every non-system route. The
net effect is that **no permission in the vocabulary admits reading a signing session you did not
initiate.**

**Evidence**
- `shared/api-permissions.md:114` — "| `DocumentSigningSession` | `DocumentSigningSession.Read` ·
  `DocumentSigningSession.ReadWrite` | The session carries no owner in the model, so there is nothing for
  an owned subset to be defined against |"
- `shared/api-permissions.md:106` — "On these six there is no subset of the tenant's resources that belongs
  to a caller, so `.All` would admit exactly what the un-suffixed form admits. **The `.All` forms are
  therefore not defined for them** — they are absent by design, not by omission."
- `contexts/DocumentSigning/aggregates/DocumentSigningSession/documentsigningsession.api.md:81` — "**A
  session carries one identity and it is the owner**: `InitiatedBy`, the acting member taken from the JWT
  `sub` at initiate. It is set once, immutable, and it is what cancel and the reads are checked against."
- `…/documentsigningsession.api.md:67-69` — "| `POST /v1/signing-sessions/{sessionId}/cancel` |
  `DocumentSigningSession.ReadWrite` | `session.InitiatedBy == actor.Id` — otherwise `403
  NotResourceOwner` | / | `GET /v1/signing-sessions/{sessionId}` | `DocumentSigningSession.Read` |
  `session.InitiatedBy == actor.Id` | / | `GET /v1/signing-sessions` | `DocumentSigningSession.Read` |
  Scoped to sessions the caller initiated |"

**Checked** `api-permissions.md` § Resources with no owned subset — the file `README.md:37` names as owning
the permission vocabulary — against the DocumentSigning API's `## Authorization` table and its
§ *`InitiatedBy` is the session's owner*. The other five rows in that table are consistent with their
aggregates, where `OwnerId` is provenance and governs nothing; DocumentSigning is the one where the owner
**does** govern.

**Why** The permissions file's stated *reason* for suppressing `.All` is factually the opposite of the API
file's central design statement. The consequence is live, not cosmetic: a `MediaAdministrator` cannot see
a signing session, and the operator paths in `documentsigningsaga.md` § Manual Intervention Runbook have
no read surface at all. This is MM-001's **SB-12** fixed on one side only — the aggregate acquired an
owner and the permission vocabulary was not told.

**Ruling** Needs a decision. **Smallest question: do `DocumentSigningSession.Read.All` /
`.ReadWrite.All` exist?**
- **Yes** — move the row out of § Resources with no owned subset into the owned-subset table, owned set
  stated as "sessions the caller initiated". Administrators and the runbook get a read surface.
- **No** — then the API file must say plainly that a session is invisible to everyone but its initiator,
  **including administrators**, and the runbook must state how an operator inspects one. Consequence: the
  `EnvelopeNotFound` guidance ("see the saga runbook") points at a procedure nobody can perform.

---

**SC-009**
**Severity** Medium
**Kind** A half-designed path
**Claim** Processing's § Published table gives two integration events consumers that the owning routing
table does not give them, and two published events have no routing row at all.

**Evidence**
- `contexts/Processing/context-overview.md:178-179` — "| `ProcessingJobCompletedIntegrationEvent` |
  `ProcessingJobSucceeded` **or** `ProcessingJobTimeoutRecovered` | AssetManagement; Billing
  (capability-filtered) |" and "| `ProcessingJobFailedIntegrationEvent` | `ProcessingJobFailed` |
  AssetManagement; Notifications |"
- `shared/event-store-and-messaging.md:349-350` — "| `media.processingjob.completed` |
  `ProcessingJobSucceeded` | AssetManagement (intra-BC via `media-cross-module-events`) |" and the same
  shape for `.failed` — no Billing, no Notifications.
- `shared/event-store-and-messaging.md:338-339` — "| `media.asset.processing-completed` |
  `AssetProcessingCompleted` | Notifications, Billing _(filtered: `Processing` capability only)_ |"
- `shared/event-store-and-messaging.md:347-350` — the routing table carries `scan-result`, `started`,
  `completed`, `failed`; there is **no** `media.processingjob.bypassed` row and no
  `media.processingjob.created` row.
- `architecture/bounded-contexts.md:115` — "AssetManagement activates or fails the asset on
  `media.processingjob.completed` / `.failed` / **`.bypassed`**"
- `contexts/Processing/aggregates/ProcessingJob/processingjob.write-model.md:252-254` — the boundary
  Processing intends: "Processing publishes job-level facts; AssetManagement publishes asset-level ones."

**Checked** The shared routing table against Processing's § Published; and both against the write model's
own statement of the job-level/asset-level split.

**Why** The routing table places Billing and Notifications on the **asset**-level events — exactly the
split Processing's write model argues for — so § Published looks like it copied the downstream consumers
one level up. Either two external consumers subscribe to job-level events with no row in the owning
inventory and no filter anywhere, or Processing overstates its downstream reach and a reader believes
Billing is already fed from the job. Separately, `media.processingjob.bypassed` is published, consumed by
AssetManagement and named as a relationship in `bounded-contexts.md`, and the inventory that claims to
enumerate integration events does not list it — nor `media.processingjob.created`, which the saga depends
on.

**Ruling** One decision, two corrections. **Question: do Billing and Notifications subscribe to
`media.processingjob.completed` / `.failed`, or only to the asset-level `media.asset.processing-*`?** If
only asset-level (what the boundary rule implies), strike "Billing (capability-filtered)" and
"Notifications" from `context-overview.md:178-179`. Independently and regardless, add
`media.processingjob.created` and `media.processingjob.bypassed` rows to
`event-store-and-messaging.md:347-350` — a published event with no routing row is how a subscription gets
missed.

---

### Group B — rules with no carrier

Six findings. Each specifies behaviour in terms of a member, flag or parameter that nothing in the tree
declares. They read as normative and cannot execute.

---

**SC-010**
**Severity** High
**Kind** A rule with no carrier · contradiction
**Claim** Three files outside Metadata read a capability set off a published `RecordType` version;
Metadata's owned contract declares no such member and states the concept does not exist at all.

**Evidence**
- `contexts/Metadata/aggregates/RecordType/recordtype.write-model.md:1695` — "**This file owns this
  contract.** A published version *is* Metadata's published language, and this event is the whole of what
  crosses the boundary."
- `…/recordtype.write-model.md:1699-1707` — the declaration in full:
  `record RecordTypePublishedIntegrationEvent(string TenantId, string RecordTypeId, string Name, int
  Version, IReadOnlyList<RecordTypeFieldSnapshot> Fields, IReadOnlyList<string> Aliases, DateTimeOffset
  PublishedAt);` — **no capability member.**
- `contexts/Metadata/context-overview.md:212-219` — "## No `Capabilities` member, and no
  `SourceCapability` per field … **`RecordType` has no capability concept at all.** No capability set, no
  `SourceCapability`, no `ICapabilityRegistry` dependency, no `/capabilities` routes"
- `contexts/Catalog/aggregates/MediaProfile/mediaprofile.write-model.md:155` — "`Capabilities` are
  unioned, not collision-checked, across all contributing RecordType versions."
- `contexts/Catalog/aggregates/MediaProfile/mediaprofile.write-model.md:122` — "| `Capabilities` | The
  union across contributing RecordType versions |"
- `contexts/Catalog/aggregates/MediaProfile/mediaprofile.design-decisions.md:83` — "| **A RecordType-side
  removal** | Removing `RecordTypePublished.Capabilities` would make the union permanently empty for
  **every** profile, so every asset takes the bypass. It cannot ship until the gate is re-sited |"
- `adrs/metadata-schema-composition.md:31` — "| **Field contributor** | On `RecordType`, via
  `ICapabilityRegistry` | Injects a governance field group into a draft |"
- `architecture/domain-model.md:197` — "| `Draft` | `RecordTypeDraft?` | Present when an editing cycle is
  in progress (`Fields`, `Capabilities`, `BasedOnVersion?`, `CreatedAt`) |"

**Checked** `RecordTypeFieldSnapshot` and `RecordTypePublishedIntegrationEvent` (verified independently by
the lead reviewer, not only by the Metadata subagent) against every member Catalog's compile step names;
`RecordTypeDraft`'s property table against `domain-model.md:197`; and `glossary.md:34`, which defines
`Capability` as "A domain module switch defined on a `MediaProfile`" — agreeing with Metadata.

**Why** This is not two files differing in emphasis. Catalog specifies a **behaviour gate** whose input is
the union of a set that no RecordType version declares, no draft holds and no event carries. Taken with
the Metadata side as written, the condition `mediaprofile.design-decisions.md:83` says "cannot ship until
the gate is re-sited" is **already true**: `CompiledMetadataTemplate.Capabilities` is a union over an empty
family, so `Capabilities.Contains("Processing")` is permanently false and every asset takes the bypass
path. That consequence is stated nowhere as live. `context-overview.md:216-219` also cites
`metadata-schema-composition.md` as its authority for the absence, and the cited ADR says the opposite.

**Ruling** Needs a decision. **Smallest question: does a published `RecordType` version carry a capability
set?**
- **No** — the Metadata contract as written, and the side this review believes: it is the owning file
  (`README.md` row 6) and `glossary.md` agrees. Then `mediaprofile.write-model.md:122,155`,
  `mediaprofile.design-decisions.md:65,83`, `metadata-schema-composition.md:18,31,44,49-56` and
  `domain-model.md:197` all describe a member that does not exist, **and Catalog's `Processing` gate has no
  source** — a functional defect, not a wording fix.
- **Yes** — then `RecordTypePublishedIntegrationEvent`, `RecordTypeDraft` and `FieldDefinitionPayload` are
  each missing a member, and `context-overview.md:212-222` is wrong in its strongest terms.

---

**SC-011**
**Severity** High
**Kind** A rule with no carrier · contradiction
**Claim** `MediaProfile` is specified to hold a `RetentionScheduleRef` that gates publish; nothing on the
aggregate declares it, and the same aggregate's capability table says `Retention` gates nothing.

**Evidence**
- `architecture/domain-model.md:76` — "| `MediaProfile` | `RetentionScheduleRef?` | `RetentionSchedule` |
  Pinned by value to a published version, same as `RecordTypeVersion`. **At most one**, nullable in general
  but **required at publish when the profile carries the `Retention` capability**."
- `contexts/Metadata/aggregates/RetentionSchedule/retentionschedule.design-decisions.md:105-110` —
  "> **A profile carrying the `Retention` capability must pin a `RetentionScheduleRef` before it may
  publish.**" … "Under this design it becomes the **third capability that actually does something**,
  alongside `Processing` and `Registration`, and the claim it makes is one the platform now honours."
- `README.md:42` (row 14f-i) — "`Retention` is a **publish gate** requiring a pinned schedule, and
  contributes no fields"
- `contexts/Catalog/aggregates/MediaProfile/mediaprofile.write-model.md:180` — "**Two capabilities gate
  behaviour. Seven gate nothing.**"
- `contexts/Catalog/aggregates/MediaProfile/mediaprofile.write-model.md:189` — "| `Retention` | Nothing
  behavioural | ❌ |"
- `contexts/Catalog/aggregates/MediaProfile/mediaprofile.write-model.md:152` — "**No precedence logic
  exists and none should be built.** A profile pins exactly one `RetentionSchedule`, so there is never a
  second disposal rule to reconcile."
- `adrs/catalog-domain-invariants.md:73` — the publish guard as "≥1 `Capability`, ≥1 `AssetDefinition`,
  **or** ≥1 `RecordTypeRef`" — no retention clause.

**Checked** A tree-wide grep for `RetentionScheduleRef`, run by the lead reviewer: **five occurrences, in
four files, none of them a `MediaProfile` declaration** — `domain-model.md:76`,
`retentionschedule.design-decisions.md:55,95,105`, `registration.write-model.md:518`. Also checked every
normative section of the five MediaProfile files: Properties (`:29-51`), Invariants (`:249-267`), Methods
(`:284-304`), Domain Events incl. `MediaProfilePublishedSnapshot` (`:319-344`), Commands (`:356-375`);
`mediaprofile.api.md` has no route (`:34-58`) and no response field (`:503-552`); `mediaprofile.read-model.md`
declares no such member on any of the four read models.

**Why** This is the platform's own inventory, and the README map, telling a reader that a Catalog aggregate
carries a member and a publish gate that the aggregate's five files declare nowhere and contradict
directly. It is README row 14f's own warning — "A capability name is not evidence a control exists" —
landing on the one capability the tree claims is no longer a bare name. `mediaprofile.write-model.md:152`
then reasons *from* the phantom pin to justify a live rule about collision precedence, so it is already
load-bearing in an argument. Neither the publish invariant table nor the `/publish` error list
(`mediaprofile.api.md:457`) admits a refusal for a missing schedule, so the gate cannot execute.

**Ruling** Needs a decision. **Smallest question: is `RetentionScheduleRef` part of the specified
`MediaProfile`?**
- **Yes** — it needs a property row, a command and event, a publish invariant with a refusal code, a
  snapshot member and a read-model/API field, and the `Retention` row in § Capabilities changes from ❌ to
  ✅ with `:180` becoming "three … six". Cost: a new refusal code and a projection field.
- **No** — `domain-model.md:76`, `README.md:42`, `retentionschedule.design-decisions.md:105-110` and the
  justification at `mediaprofile.write-model.md:152` all need rewording to stop asserting it, and
  `RetentionSchedule` remains inventoried with no consumer.

---

**SC-012**
**Severity** Medium
**Kind** A rule with no carrier
**Claim** `mediaprofile.write-model.md` § *Governance field groups* specifies a publish pre-condition, a
provenance member and an error code, none of which exists anywhere else — and the code is contradicted by
the same file's own statement of how many codes this aggregate has.

**Evidence**
- `contexts/Catalog/aggregates/MediaProfile/mediaprofile.write-model.md:219` — "A capability on the draft
  contributes a platform-defined field group into the compiled template — resolved once at publish through
  `ICapabilityRegistry`, pinned and never re-resolved, carrying `SourceCapability` as provenance,
  qualified like any other contributor on collision, and gated by a `422
  MandatoryRecordkeepingCoreMissing` pre-condition on publish."
- `contexts/Catalog/aggregates/MediaProfile/mediaprofile.write-model.md:264` — "⚠ **These refusals carry no
  `errorCode`.** `MediaProfileErrorCodes` declares exactly three — `MediaProfileNotFound`,
  `MediaProfileNotPublished` and `TenantAdministratorRequired`."
- `contexts/Catalog/aggregates/MediaProfile/mediaprofile.write-model.md:96-113` — the
  `CompiledMetadataField` property table, which has no `SourceCapability` member.
- `contexts/Catalog/aggregates/MediaProfile/mediaprofile.api.md:457` — the `/publish` error list, which
  does not carry the refusal.
- `shared/error-catalog.md:294-305` — the Catalog — MediaProfiles table: two codes, no
  `MandatoryRecordkeepingCoreMissing`.
- `contexts/Metadata/context-overview.md:214` — "**`RecordType` has no capability concept at all.** No
  capability set, no `SourceCapability`"

**Checked** Tree-wide: `MandatoryRecordkeepingCoreMissing` and `ICapabilityRegistry` each appear exactly
once in `docs/spec/`, in this paragraph; `SourceCapability` appears elsewhere only in Metadata, denying it
exists.

**Why** Four normative claims in one sentence have no carrier: no member holds `SourceCapability`, no
invariant row states the pre-condition, the publish route does not list the refusal, and the error code
cannot exist if `MediaProfileErrorCodes` declares exactly three — a claim made sixty lines below in the
same file. A reader who acted on it would add a publish gate the route contract denies. This is the
Catalog-side face of SC-010.

**Ruling** Either promote the mechanism — add `SourceCapability` to `CompiledMetadataField`, an invariant
row, the `/publish` error and a catalogue entry, and amend "exactly three" — or delete the clause and keep
only the collision-qualification statement, which does have carriers. **Resolve with SC-010; they are one
piece of work.**

---

**SC-013**
**Severity** Medium
**Kind** A rule with no carrier
**Claim** Every ProcessingJob command and query is specified to require `actor_type == "System"`, on paths
the same section states carry no JWT, and no handler step anywhere checks it.

**Evidence**
- `contexts/Processing/aggregates/ProcessingJob/processingjob.api.md:65-66` — "**Every command and every
  query requires `actor_type == \"System\"`.** No JWT is involved on any path: `TenantId` comes from the
  SQS message-attribute envelope, and the caller is the pipeline itself."
- `…/processingjob.api.md:80-82` — "**Not being HTTP-reachable is a deployment property; requiring a System
  actor is the specification.** Both are stated, because a command whose only protection is that nothing
  routes to it is protected by an accident of wiring rather than by a rule."
- `…/processingjob.write-model.md:204-214` — the five-step handler contract: "1. Resolves `TenantId` from
  the command 2. Loads the aggregate … 3. Calls exactly one aggregate method 4. Persists … 5. Returns
  `Result<Unit, IDomainError>`" — **no actor resolution, no refusal step.**
- `shared/api-permissions.md:248-250` — "**System callers are not expressed as a permission.** … That is a
  property of **the token's subject** rather than a grant"
- `shared/error-catalog.md:96` — "| `SystemActorRequired` | 403 | Endpoint requires `actor_type =
  \"System\"`; a User or Guest caller was rejected |"

**Checked** `processingjob.write-model.md` § Invariants (`:121-128`), which lists no actor rule and no
refusal code for one; and `api-permissions.md:116-123`, which softens "token's subject" to "caller" for
this one aggregate without saying what a caller *is* on an SQS path.

**Why** `actor_type` is defined tree-wide as a JWT claim. Processing states no JWT reaches any of its
paths, gives an eight-row table of commands requiring the claim, and specifies a handler contract with
nothing to evaluate it against. The section anticipates the objection — "protected by an accident of
wiring rather than by a rule" — and then supplies a rule with no carrier, which is the accident it set out
to avoid. `SystemActorRequired` is a `403`, a status with no meaning on a queue.

**Ruling** Needs a decision. **Smallest question: on the SQS path, what carries `actor_type`, and where is
it checked?**
- **A** — the SQS message-attribute envelope carries an actor alongside `TenantId`: say so as a numbered
  step in § Handler-side Pre-conditions, and give the refusal a row in § Invariants and in
  `error-catalog.md § Processing`.
- **B** — nothing carries it: then `processingjob.api.md:65-82` must say the protection today *is* the
  absence of a route, which is the honest form of the same claim.
Leaving it means eight specified authorization rules that no component can execute.

---

**SC-014**
**Severity** Medium
**Kind** A rule with no carrier
**Claim** `GET /v1/profiles?pinsRecordType=` — the stated pre-deprecation impact-analysis call — is served
by a `PinnedRecordTypes` read-model attribute that appears in no field table, no record declaration, no
query signature, no parameter table and no projector row.

**Evidence**
- `contexts/Catalog/aggregates/MediaProfile/mediaprofile.api.md:641` — "**`?pinsRecordType={id}[&version={n}]`**
  filters the list to the profiles that pin that record type — the impact-analysis call an administrator
  makes before deprecating a record type … It is served by the `PinnedRecordTypes` attribute on the read
  model."
- `contexts/Catalog/aggregates/MediaProfile/mediaprofile.read-model.md:75` — "**`PinnedRecordTypes`** is a
  flattened pin lookup holding `{recordTypeId}` and `{recordTypeId}#{version}` for every published pin"
- `…/mediaprofile.read-model.md:51-73` — the `MediaProfileDetailReadModel` field table: not listed.
  `:241-267` — the record declaration: not declared.
- `…/mediaprofile.read-model.md:215` — "| `ListMediaProfilesQuery(TenantId, PagerParameters, Name?)` |" —
  no pin parameter.
- `…/mediaprofile.api.md:621-625` — the `GET /v1/profiles` parameter table lists `name`, `pageSize`,
  `pageToken` only.
- `…/mediaprofile.read-model.md:153` — the `MediaProfilePublished` projector branch refreshes ten named
  fields, not this one.

**Checked** The query-parameter contract against the field table, the C# record, the query signature, the
projector's write list and the endpoint's own parameter table — five layers, all silent.

**Why** Two prose paragraphs are the only places the member exists. Every layer the feature needs is
missing except the sentences saying it works, and it is the call an administrator is told to make before
an irreversible tenant-wide deprecation. `recordtype.scenarios.md:301-305` presents it as the answer to
the deprecation blast-radius question with three caveats that presume it works.

**Ruling** Correction. Add `PinnedRecordTypes` to the `MediaProfileDetailReadModel` field table, the record
declaration and the `MediaProfilePublished` projector row; add `PinsRecordType`/`Version` to
`ListMediaProfilesQuery` and to the `GET /v1/profiles` parameter table.

---

**SC-015**
**Severity** Medium
**Kind** A rule with no carrier
**Claim** The `RecordType` terminal-state contract is written in terms of read-row members `isDeprecated`
and `isAbandoned`; the read model declares neither, and says explicitly that two flags are what was
decided against.

**Evidence**
- `contexts/Metadata/aggregates/RecordType/recordtype.write-model.md:81` — "| Read rows | Retained,
  `isDeprecated = true` | Retained, `isAbandoned = true` |"
- `shared/error-catalog.md:398` — "**Not a 404:** the read rows are retained (`isAbandoned: true`) so `GET`
  answers `200` either way"
- `contexts/Metadata/aggregates/RecordType/recordtype.read-model.md:108` — "| `Status` | `string` |
  `Drafting` \| `Published` \| `Deprecated` \| `Abandoned` — derived on the aggregate, projected here so the
  list filter is one attribute **rather than two flags** |"
- `contexts/Metadata/aggregates/RecordType/recordtype.api.md:918` — the wire shape actually specified:
  "The read rows are **retained** with `status: \"Abandoned\"`, so `GET` still answers `200`"

**Checked** The complete member lists of `RecordTypeSummaryReadModel` (`:97-110`) and
`RecordTypeDetailReadModel` (`:141-159`) and the `GET` example payload (`api.md:1004-1044`) — neither flag
appears. The only `isDeprecated` on a read row is on the **version** rows (`:182`, `:244`), a different
subject.

**Why** The read model states in so many words that the two flags are what the design rejected, and three
normative statements still describe the row's post-terminal state in their terms. A reader implementing
`RecordTypeAlreadyAbandoned`'s "Not a 404" rationale reads a member off a row that does not have it.

**Ruling** Correction, no model change needed. Restate all three in terms of the member that exists —
`status = "Deprecated"` / `status = "Abandoned"` — in `write-model.md:81`, `error-catalog.md:398` and the
HTML row at `recordtype-diagrams.html:419`.

---

### Group C — half-designed paths

Eight findings. The pieces of a flow exist and the flow does not close.

---

**SC-016**
**Severity** High
**Kind** A half-designed path
**Claim** Nothing in the spec triggers the rendition/metadata half of the Processing pipeline: the worker
is stated to terminate after the scan, the only queue that reaches it is filtered to one event type, and
`AssetProcessingWorker` is described as having no trigger.

**Evidence**
- `contexts/Processing/context-overview.md:101` — "    │                                       [ProcessingWorker terminates here]"
- `contexts/Processing/context-overview.md:119` — "    │   [ProcessingWorker — AssetProcessingWorker]   in-process; not separately triggered"
- `contexts/Processing/context-overview.md:190` — "**`media-processing` — ProcessingWorker.** SNS-filtered
  to one type." (that type being `AssetUploadConfirmedIntegrationEvent`, `:194`)
- `contexts/Processing/aggregates/ProcessingJob/processingjob.scenarios.md:58` — "PW terminates here."
- `…/processingjob.scenarios.md:121` — "    Note over PW: renditions + EXIF — no trigger today"
- Against `contexts/Processing/context-overview.md:68` — "| `ProcessingWorker` | Lambda | SQS
  `media-processing`, filtered to `media.asset.upload-confirmed` | … **For a capable asset, runs the
  rendition and metadata pipeline via `AssetProcessingWorker`.** …"
- Against `architecture/system-architecture.md:292` — "| `media-processing` | ProcessingWorker trigger | …
  | **1800 s** — virus scan + renditions can exceed the Lambda timeout; video jobs extend via
  `ChangeMessageVisibility` up to 4 h |"

**Checked** Both `## Consumed` tables (`context-overview.md:188-205`) — two queues, six event types, none
of them `ProcessingJobStartedIntegrationEvent`; `processingjob.write-model.md:258-264` ("`ProcessingJob`'s
own lifecycle is driven by **one** event, on the `media-processing` queue"); and
`event-store-and-messaging.md:266,287`, which both state the `media-processing` filter as
`AssetUploadConfirmedIntegrationEvent` only.

**Why** Two incompatible designs are present at once. In one, the worker holds the SQS message for up to
30 minutes (4 h for video) and runs scan-then-renditions in a single invocation — what the 1800 s
visibility timeout and its stated justification describe. In the other, the worker terminates after the
scan and renditions begin when the saga's `StartProcessingJobCommand` takes effect — what the pipeline
diagram, the scenario and the one-event consumption rule say. Under the second reading,
`ProcessingJobStarted` moves the `Asset` to `Processing` and no specified message reaches the worker, so
the job sits in `Running` until the saga's 240-minute clock fails it — **the exact scenario P-3 describes
as a fault becomes indistinguishable from normal operation.** This is the largest hole in the tree: the
pipeline's productive half has a specified output (`CompleteProcessingJobCommand`) and no specified input.

**Ruling** Needs a decision. **Smallest question: what invokes `AssetProcessingWorker`?**
- **A — the same invocation continues past the scan into renditions** (consistent with the 1800 s
  visibility and `:68`). Then `context-overview.md:101`, `:119` and `processingjob.scenarios.md:58,121` are
  wrong, and the design has the worker proceeding without waiting for the saga's `Start` decision, which
  needs saying.
- **B — a second message triggers it.** Then the spec must name the queue, its filter and its handler, and
  `media-processing`'s "one type only" filter is incomplete in three files.

**The same decision almost certainly settles SC-017**, and they should be taken together.

---

**SC-017**
**Severity** Medium
**Kind** A half-designed path
**Claim** Video rendition completion is specified to arrive "via EventBridge → SQS" and no queue, filter,
message type or handler for it exists anywhere in the tree.

**Evidence**
- `contexts/Processing/context-overview.md:121` — "    │       ├─ Video    → MediaConvert (async;
  completion via EventBridge → SQS)"
- `contexts/Processing/context-overview.md:287` — "| AWS MediaConvert | External | Outbound — async video
  encoding |" — the External Dependencies table records the outbound leg only; there is no inbound row.
- `contexts/Processing/context-overview.md:188-205` — the § Consumed tables: six integration events across
  two queues, none a MediaConvert completion.
- `shared/event-store-and-messaging.md:284-290` — the full queue inventory: no queue has EventBridge or
  MediaConvert as its source.
- Against `architecture/system-architecture.md:292` — "video jobs extend via `ChangeMessageVisibility` up
  to 4 h"

**Checked** Every `MediaConvert` occurrence in `docs/spec` — five, at `context-overview.md:121,141,287`,
`processingjob.scenarios.md:165` and `mediaprofile.defaults.md:102`. **None names a return path.**

**Why** `CompleteProcessingJobCommand` is dispatched by `AssetProcessingWorker` on pipeline success, and
for video that success is reported by a service outside the invocation. Either the worker blocks on
MediaConvert inside the invocation — which is what the 4-hour visibility extension describes, making
"async; completion via EventBridge → SQS" wrong — or a callback arrives on a queue no file names, which
makes the visibility extension pointless. Scenario P-3 is built on this branch failing ("the MediaConvert
job orphans and no completion callback arrives"), so the spec describes the absence of a callback as the
fault case while never specifying the callback.

**Ruling** Needs a decision, and it is probably SC-016's. **Question: does the ProcessingWorker wait for
MediaConvert inside its invocation, or does a completion message re-enter the pipeline?** If it waits:
remove "completion via EventBridge → SQS" and state the blocking wait plus the visibility-extension
mechanism. If a message re-enters: name the queue, its EventBridge rule, the message type and the handler,
and add the inbound leg to § External Dependencies and the shared queue inventory.

---

**SC-018**
**Severity** High
**Kind** A half-designed path
**Claim** Auto-submit dispatches `PublishMediaItemCommand`, which requires a reviewer roster under
`RequiredForPublish`, and nothing in the tree says what roster it supplies — which makes the one seeded
platform profile combining both flags unsatisfiable.

**Evidence**
- `contexts/Catalog/aggregates/MediaItem/mediaitem.write-model.md:281` — "**And C can drive A.**
  Auto-submit fires from **three** handlers … each dispatching `PublishMediaItemCommand` as a System actor
  when the profile has `AutoSubmitOnComplete`, the item is `Draft`, and all required roles are filled."
- `…/mediaitem.write-model.md:545` — "| `PublishMediaItemCommand(TenantId, MediaItemId, ReviewerIds[],
  RequestingUser, OccurredAt)` |"
- `…/mediaitem.write-model.md:322` — "**Under `ReviewPolicy.RequiredForPublish`, at least one reviewer is
  required.** Publishing such an item with an empty roster is refused with `MinimumReviewersRequired`."
- `contexts/Catalog/aggregates/MediaProfile/mediaprofile.defaults.md:140` — (Governed Media Record) "Review
  `RequiredForPublish` · Checkout `RequiredForEdit` · AutoSubmit ✓"
- `contexts/Catalog/aggregates/MediaProfile/mediaprofile.api.md:399` — "When enabled, an item on this
  profile is submitted for review automatically once every required asset role is filled … If the review
  policy is `\"None\"` the item publishes immediately on completion."

**Checked** The auto-submit paragraph and the command signature against the `RequiredForPublish` minimum,
the `ReviewerIsInitiator` rule at `:330`, and the seeded profile matrix; searched the whole `docs/` tree
for any statement of an auto-submit roster — **none**.

**Why** `mediaprofile.api.md:399` says auto-submit *submits for review*, which presupposes reviewers, and
the command has a required `ReviewerIds[]`. On `Governed Media Record` — the only seeded profile with both
flags — an empty roster is refused, so auto-submit either never fires or always fails **on the platform's
own governance profile**. The spec cannot be implemented from what it says, and the failure lands on the
seeded set a tenant gets on day one.

**Ruling** Needs a decision. **Smallest question: under `ReviewPolicy = RequiredForPublish`, what roster
does auto-submit pass?**
- **A — it does not fire.** Define auto-submit as inert when `ReviewPolicy != None`; one sentence in
  `mediaprofile.api.md` and the write model. Consequence: `Governed Media Record`'s `AutoSubmit ✓` becomes
  decorative and should probably be withdrawn from the seeded profile.
- **B — a roster source is named** (profile-declared default reviewers, the owner's delegates) and added to
  `MediaProfile` as a member, with its own command, event and publish-time resolution.

---

**SC-019**
**Severity** Medium
**Kind** A half-designed path
**Claim** `MediaItemVersionPurged` has no summary-row projector, so a purged version stays in the version
list the purge endpoint specifies it removes.

**Evidence**
- `contexts/Catalog/aggregates/MediaItem/mediaitem.read-model.md:245` — "### `MediaItemVersionSummaryProjector`
  → `media-item-versions` (summary rows, v1+) / `MediaItemApproved` only."
- `…/mediaitem.read-model.md:241` — "| `MediaItemVersionPurged` | DELETE the version row |" — **detail
  projector only.**
- `…/mediaitem.read-model.md:288` — "| `ListMediaItemVersionsHandler` |
  `IReadModelReader<MediaItemVersionSummaryReadModel>` | `QueryIndexAsync` |"
- `contexts/Catalog/aggregates/MediaItem/mediaitem.api.md:630` — "**System/admin only.** Permanently
  removes a published version snapshot"
- `…/mediaitem.api.md:139` — "| `DELETE /versions/{versionNumber}` | A retained version of a government
  record |" under "**Two are `Dispose`** — each destroys a record permanently"

**Checked** The two version projectors' event sets against the purge route's contract and against which
read model `GET /v1/items/{itemId}/versions` reads.

**Why** `GET …/versions` reads summary rows and only the detail projector deletes on purge, so the endpoint
specified as permanent destruction leaves the purged version listed indefinitely, with
`GET …/versions/{n}` then `404`ing on a row the list advertises. On a regulated-records platform the
destruction path is where a dangling row matters most. This is the only MediaItem event with a detail
projector and no summary counterpart.

**Ruling** Correction. Add `MediaItemVersionPurged` → DELETE to `MediaItemVersionSummaryProjector`'s event
set, and to the traceability row for the purge route.

---

**SC-020**
**Severity** Medium
**Kind** A half-designed path
**Claim** The `MediaItemDeleted` detail projector is specified to "mark deleted", no MediaItem read model
declares any member to mark, and two other files specify the opposite behaviour — row removal.

**Evidence**
- `contexts/Catalog/aggregates/MediaItem/mediaitem.read-model.md:221` — "| `MediaItemDeleted` | Mark
  deleted |"
- `…/mediaitem.read-model.md:36-55` (detail field table) and `:319-352` (`MediaItemDetailReadModel`
  declaration) — no `DeletedAt`, no `IsDeleted`; `:14-32` and `:298-317` the same for the summary model;
  `:409-416` — `MediaItemStatus` has five members and no `Deleted`.
- `…/mediaitem.read-model.md:161` — "⚠ **The mapping is `dynamic: \"strict\"` and must mirror
  `MediaItemDetailReadModel` exactly, field for field** … A property on the read model with no entry in the
  mapping … OpenSearch rejects the **entire document**." — and the mapping at `:167-183` carries no deleted
  member either.
- `shared/cascade-rules.md:99` — "`DeleteMediaItem` requires `Status == Archived` and then **removes the
  item from five projections**."
- `contexts/Catalog/aggregates/MediaItem/mediaitem.api.md:138` — "| `DELETE /v1/items/{itemId}` | The item,
  and its presence in five projections |"

**Checked** The projector row against every MediaItem read-model field table, record declaration, the
status enum and the OpenSearch mapping, and against the delete route and `cascade-rules.md`.

**Why** "Mark deleted" names no field that exists, and the two files describing the outcome say removal. A
reader implementing the mark adds a property to `MediaItemDetailReadModel`, which by the file's own
`strict`-mapping warning **silently stops the search index accepting writes** — a failure that surfaces as
missing search results, not as an error.

**Ruling** Correction. Replace `mediaitem.read-model.md:221` with the concrete write — DELETE the row,
matching `cascade-rules.md:99` — or declare the deleted member on both read models, the status enum and
the OpenSearch mapping. The first is consistent with the two files that state the outcome.

---

**SC-021**
**Severity** Medium
**Kind** A half-designed path
**Claim** `RegistrationPersonalDataErased` is specified to redact every read model; no projector consumes
it, no read-model member can hold the cleared value, and an index partition key is built by interpolating
the field the event clears.

**Evidence**
- `contexts/Registration/aggregates/Registration/registration.write-model.md:558` — "**Erasure is a forward
  redaction.** It clears current aggregate state and every read model projected from it."
- `…/registration.write-model.md:278` — "All twelve implement `IRegistrationDomainEvent`…" (rows 283-294
  list twelve, ending `RegistrationPersonalDataErased`)
- `…/registration.read-model.md:239` — "Handles all eleven events: the summary projector's seven, with the
  additions below, plus four more." — `RegistrationPersonalDataErased` appears in **neither** projector
  table (`:226-233`, `:241-250`).
- `contexts/Registration/aggregates/Registration/registration.api.md:454` — "Cleared: `ownerId`, `notes`,
  and on every amendment `requestedBy`, `notes` and `decisionNotes` … the response bodies of the read
  endpoints carry `null` in their place."
- `…/registration.read-model.md:121` — "| `Id` · `TenantId` · `MediaItemId` · `OwnerId` | `string` | As
  above |" — **non-nullable.**
- `…/registration.read-model.md:75` — "| `RegistrationByOwnerIndex` | `RegistrationByOwnerIndexSchema` |
  `TENANT#{t}#OWNER#{ownerId}#REGISTRATIONS` / `{InitiatedAt:O}#{Id}` |"
- `…/registration.read-model.md:179-196` — the OpenSearch mapping is `dynamic: "strict"`.

**Checked** The twelve-row Domain Events table against both projector tables, the two read-model member
tables, the OpenSearch mapping, the API response contract, and the event/command tallies at
`write-model.md:438` ("all eleven domain events"), `read-model.md:239` ("all eleven") and
`adrs/ownership-and-authorization.md:62` ("5 of 11 commands") — three tallies of eleven against tables of
twelve.

**Why** The event is declared, routed to a topic both projectors subscribe to, and stated to redact "every
read model projected from it" — while the only files that say what a projector does with an event give it
no handler, and the read models cannot represent the redacted state. `OwnerId` is a non-nullable `string`
the API says becomes `null`; the mapping is `strict`, so a member it does not admit stops indexing
entirely; and `GSI2PK` interpolates `ownerId`, leaving an erased summary row with an unspecified partition
key. This is MM-001's **SB-52** half-closed: the actor and trigger were specified, the projection was not.

**Ruling** Correction plus one small design step. Add `RegistrationPersonalDataErased` to both projector
tables stating the members each clears; make `OwnerId`, `Notes` and the three `RegistrationAmendmentDto`
members nullable on the read-model declarations; **state what `RegistrationByOwnerIndex` holds for an
erased row** — a sentinel partition or removal from the index — and reconcile the eleven/twelve tallies.

---

**SC-022**
**Severity** Medium
**Kind** A half-designed path
**Claim** Two Registration refusals the spec explicitly specifies — a non-System caller on the five
decision routes, and a caller lacking `Registration.Manage.All` on erase — have no status code and no
`errorCode` anywhere in the tree.

**Evidence**
- `contexts/Registration/aggregates/Registration/registration.api.md:115` — "**They also require a System
  actor.** That is a second, independent condition: the integration adapter is the only caller, and a
  `User` token holding `Registration.Manage.All` is still refused."
- `…/registration.api.md:337, :364, :392, :408, :440` — every one of these **Errors:** lists names only
  `404 RegistrationNotFound` and `422` codes; **none lists a `403`.**
- `…/registration.api.md:469` — "**Errors:** `404 RegistrationNotFound`." is the entire error list for
  `/erase-personal-data`.
- `shared/error-catalog.md:508` — the only 403 row in § Registration: "| `NotResourceOwner` | 403 | Submit,
  resubmit, cancel, attach or request-amendment attempted by a caller who is neither the registration's
  owner nor a `System` actor |"
- `shared/error-catalog.md:96` — "| `SystemActorRequired` | 403 | Endpoint requires `actor_type =
  \"System\"` … |"

**Checked** Every per-route **Errors:** list in `registration.api.md` against § Refusal status codes in both
Registration files and the whole § Registration block of the catalogue.

**Why** The five routes with no owner predicate are exactly the ones whose 403 the aggregate's four-code
rule does not describe: `NotResourceOwner` is defined by an ownership comparison those routes deliberately
do not make, and `Registration.Manage.All` is a permission, not an ownership test. A platform code for
precisely this case exists — `SystemActorRequired` — and Registration never names it. A client is told a
refusal happens and given no code to branch on and no status to expect.

**Ruling** Correction. Add `403 SystemActorRequired` to the five `[System]` routes' **Errors:** lists and
to `error-catalog.md § Registration`; state which 403 the erase route raises when the caller lacks
`Registration.Manage.All`; and widen the `403` row of § Refusal status codes so it covers actor-type and
permission refusals as well as the owner check.

---

**SC-023**
**Severity** Medium
**Kind** A half-designed path · an inventory that does not match itself
**Claim** The error catalogue declares itself exhaustive in both directions and is wrong in both: three
codes are raised and not listed, and one listed code is raised nowhere.

**Evidence**
- `shared/error-catalog.md:3-5` — "**Every `errorCode` a write endpoint produces is listed here** … A write
  endpoint that returns an `errorCode` absent from this file is a defect in one of the two."
- **Raised, not listed** (verified by extraction across all 81 files):
  - `shared/operations.md:206` — `"errorCode": "RateLimitExceeded",` — no catalogue row.
  - `contexts/AssetManagement/aggregates/Asset/asset.scenarios.md:767` — `"errorCode": "RenditionNotFound",`
    — no catalogue row.
  - `contexts/AssetManagement/aggregates/Asset/asset.api.md:862-869, :957-965` — the bulk per-item codes
    `QuotaExceeded`, `DuplicateAssetId`, `PersistenceFailed`, `DeclaredSizeExceeded`,
    `ProfileLimitExceeded`; § AssetManagement (`:113-138`) contains none of the five, and carries
    `StorageQuotaExceeded` (`:130`) and `FileSizeExceeded` (`:137`) instead. `asset.api.md:871-873` asserts
    "**These codes are constants, not string literals.** Every per-item `errorCode` above comes from
    `AssetErrorCodes`" — self-refuting.
- **Listed, raised nowhere:**
  - `shared/error-catalog.md:245` — "| `CheckoutRequired` | 422 | Profile sets `CheckoutPolicy =
    RequiredForEdit` and the item is not checked out |". A tree-wide grep returns **zero** occurrences
    outside the catalogue. `mediaitem.api.md:706-714` lists the checkout refusals as
    `MediaItemCheckedOut`, `MediaItemNotCheckoutable`, `ChangeRequestRequired`, `ChangeRequestNotOpen`,
    `TooManyCollaborators` — no `CheckoutRequired`.
- `shared/error-catalog.md:180-183` — "**Bulk envelope codes are the constants in this catalog.**"
- `shared/bulk-operations.md:32` — makes quota a request-level `400`, which `asset.api.md:779` agrees with
  ("the entire request returns `400 QuotaExceeded` — no per-item partial quota handling") and
  `asset.api.md:867` contradicts by listing `QuotaExceeded` as a **per-item** code.

**Checked** All 152 catalogue rows extracted and matched against every `**Errors:**` line and every
`"errorCode"` literal in the tree. `ReviewerSelfApproval` in `security-scenarios.md` is **not** reported —
that file states its own exception at `:154` ("`ReviewerSelfApproval` is not in the error catalog, so the
`errorCode` below is not one any endpoint returns"), which is the correct way to carry one.

**Why** This refines MM-001's **SB-22** — which said the catalogue claims exhaustiveness and is not —
with the specific rows, in both directions. The catalogue's own rule makes each of these a declared defect
rather than a tolerable gap. A client branching on `body.errorCode` has five bulk values it cannot look
up; and `CheckoutRequired` is a contract a client may branch on and will never receive.

**Ruling** Correction, four parts. (a) Add `RateLimitExceeded` and `RenditionNotFound` rows, or remove the
example payloads that produce them. (b) Add `DuplicateAssetId` and `PersistenceFailed` to § AssetManagement
and replace `QuotaExceeded` / `DeclaredSizeExceeded` / `ProfileLimitExceeded` with the catalogued
`StorageQuotaExceeded` / `FileSizeExceeded`. (c) Delete the per-item `QuotaExceeded` row at
`asset.api.md:867` — the endpoint states quota is request-level. (d) Either give `CheckoutRequired` a raise
site in `mediaitem.api.md`'s write-endpoint error lists or remove the catalogue row.

---

### Group D — contradictions inside a context

Nine findings. Two files in one context, or one file with itself, stating incompatible things.

---

**SC-024**
**Severity** High
**Kind** Contradiction
**Claim** `mediaitem.api.md` specifies that a field omitted from a metadata write is left untouched on
*both* write paths, and forty lines later that `PUT /v1/items/{itemId}/metadata` clears every omitted
entry.

**Evidence**
- `contexts/Catalog/aggregates/MediaItem/mediaitem.api.md:409` — "**A `null` value is an instruction, not
  an absence.** On both metadata write paths, a field present in the request with a `null` value **clears**
  that field; a field not present in the request is **left untouched**. The two are different requests and
  the platform does not treat them alike."
- `…/mediaitem.api.md:449` — "**This endpoint fully replaces `Metadata.Draft`** — entries omitted from
  `fields` are cleared."
- `…/mediaitem.api.md:665` — (`POST /v1/items/bulk/metadata`) "**Writes merge into each item's draft**."
- `…/mediaitem.read-model.md:213` — "| `MediaItemMetadataFieldSet` / `MediaItemMetadataBatchSet` | UPDATE
  `Metadata.Draft`, `MetadataAttributor` |" — no independent answer.

**Checked** The § *Setting a field to `null` clears it; omitting it leaves it alone* section against the
`PUT …/metadata` and `POST …/bulk/metadata` endpoint bodies, and against the detail projector's write.

**Why** The `null` section exists precisely to warn that a client serialising its whole model would
otherwise wipe the record — and line 449 specifies the wipe. Same request shape, opposite outcomes, on a
regulated-records platform. The `null`-section rule is the one the rest of the tree depends on: the bulk
route merges, and the `If-Match` rebase check at `:351` reasons about a "write set" that is meaningless
under whole-draft replacement.

**Ruling** Needs a decision. **Smallest question: is `PUT /v1/items/{itemId}/metadata` a merge or a
whole-draft replacement?**
- **Merge** — delete `:449`. Consistent with the `null` section, the bulk route and the rebase check.
- **Replacement** — then the `null` section must be restated to cover the single-field route only, and
  `PUT …/metadata` must say plainly that it is whole-draft replacement. It cannot stay a parenthetical
  inside "same semantics as the single-field route". Consequence: a client that omits a field it did not
  load loses it silently.

---

**SC-025**
**Severity** High
**Kind** Contradiction
**Claim** `mediaitem.api.md` specifies two incompatible authorities for `POST /v1/items/{itemId}/checkout/force-release`
within the same file, admitting disjoint caller sets.

**Evidence**
- `contexts/Catalog/aggregates/MediaItem/mediaitem.api.md:116` — "| `POST
  /v1/items/{itemId}/checkout/force-release` | `MediaItem.Manage` | None beyond tenant scoping |"
- `…/mediaitem.api.md:147` — "**`force-release` carries no owner predicate.** An owner identifier is
  provenance and confers no authority, so the tier is what restricts the command — a caller holding
  `MediaItem.Manage` may release any session in the tenant, and a caller without it may release none,
  including their own item's."
- `…/mediaitem.api.md:752` — "Releases someone else's session, **keeping their work**. Restricted to a
  system actor or the item's owner; authority is read from the execution context, never from the payload."
- `…/mediaitem.api.md:756` — "**Errors:** `401`; `403` (neither a system actor nor the owner — an absent
  actor is treated as not privileged); `404`; `422 MediaItemNotCheckedOut`"
- `shared/error-catalog.md:244` — "| `NotResourceOwner` | 403 | `ForceReleaseCheckout` by a caller who is
  neither the item's owner nor a `System` actor."
- `shared/api-permissions.md:206` — "**`MediaAdministrator` governs.** … the item lifecycle operations that
  override another member's state — publish, withdraw, force-release a checkout"

**Checked** The § Authorization table and § *`Manage` and `Dispose` are separate authorities here* against
the endpoint body of the same file, the Catalog — MediaItems error table, and the role descriptions.

**Why** Under the table, a `MediaAdministrator` who owns nothing may break any lock. Under the endpoint,
that same administrator is `403` on every item they do not own — which makes `MediaItem.Manage` on this
route unreachable and contradicts the `MediaAdministrator` role description. It is 2–2 across files, so no
side can be inferred, and the two readings admit disjoint caller sets. This is also where MM-001's Q5
ruling (`OwnerId` is provenance only) has landed on one half of a file and not the other.

**Ruling** Needs a decision. **Smallest question: is force-release admitted by `MediaItem.Manage` alone, or
by System-or-owner?**
- **Tier-only** — `mediaitem.api.md:752` and `:756` drop the owner clause and `error-catalog.md:244` loses
  its `ForceReleaseCheckout` condition. Consequence: an item owner without `Manage` loses the ability to
  break a lock on their own record.
- **Owner-or-System** — the Authorization row gains a resource predicate, `:147` is deleted, and
  `api-permissions.md:206` must stop listing force-release among what `MediaAdministrator` can do.

---

**SC-026**
**Severity** High
**Kind** Contradiction
**Claim** `mediaprofile.defaults.md` states that a `Platform`-origin profile refuses the governance setters
and `PublishMediaProfile`, then specifies a seeding procedure that calls exactly those on `Platform`-origin
profiles.

**Evidence**
- `contexts/Catalog/aggregates/MediaProfile/mediaprofile.defaults.md:31` — "**A profile whose
  `ProfileOrigin` is `Platform` cannot be revised, renamed, deprecated or deleted.** The five governance
  setters, `CreateMediaProfileRevision`, `PublishMediaProfile`, `DeprecateMediaProfile` and any rename all
  refuse on a `Platform`-origin profile, **whatever permission the caller holds**. The origin check
  precedes the profile's state, so the refusal does not depend on whether a draft is open."
- `…/mediaprofile.defaults.md:164` — "2. Mints a fresh `MediaProfileId` and dispatches
  `CreateMediaProfileCommand` with `ProfileOrigin = Platform`. / 3. Adds each `AssetDefinition` in order. /
  **4. Sets capabilities, review policy and checkout policy. / 5. Sets `AutoSubmitOnComplete`. / 6.
  Publishes the profile.**"
- `…/mediaprofile.defaults.md:13` — "**Seven profiles**, all carrying `ProfileOrigin = Platform`, all
  published at version 1."
- `…/mediaprofile.api.md:98` — "**The origin predicate is the one resource rule on this aggregate.** A
  `Platform`-origin profile is immutable — every write above refuses on it"
- `…/mediaprofile.write-model.md:381` — § Handler-side Pre-conditions lists `ProfileGovernanceAuthorization`
  on the five setters and **no** `ProfileOrigin` guard anywhere.

**Checked** § Lifecycle against § How seeding runs in the same file; the api Authorization table's
`profile.ProfileOrigin == Tenant` predicate; the write model's invariant and handler pre-condition tables.

**Why** Steps 4, 5 and 6 **are** the five governance setters and `PublishMediaProfile` — the commands
§ Lifecycle names as refusing — and the file forecloses the obvious escape ("the origin check precedes the
profile's state"), so it cannot be read as *only after first publish*. Either seeding cannot produce the
seven profiles the same file says exist, or the rule is an endpoint-layer predicate that in-process
dispatch bypasses, in which case "whatever permission the caller holds" is overstated and the write model
needs the guard it does not declare. This is MM-001's **SB-77** answered without the answer being wired
through.

**Ruling** Needs a decision. **Smallest question: at which layer is the `ProfileOrigin` guard applied?**
- **Endpoint-only** — restate § Lifecycle as a resource predicate on the HTTP surface (as
  `mediaprofile.api.md:76-92` already does) and say the seeder dispatches commands directly. Cost: any
  future in-process caller can mutate a seeded profile.
- **Command-level** — add the `ProfileOrigin` guard to § Handler-side Pre-conditions and specify how the
  seeder is exempted. Without an exemption the seeded set is unbuildable.

---

**SC-027**
**Severity** High
**Kind** Contradiction
**Claim** `mediaitem.scenarios.md` states that nothing in the publish path reads `ReviewPolicy`; three
other files specify a publish-time refusal that reads exactly that.

**Evidence**
- `contexts/Catalog/aggregates/MediaItem/mediaitem.scenarios.md:496` — "`ReviewPolicy` **exists** on the
  profile. Nothing in the publish path reads it — the reviewer count in the request drives the path."
- `…/mediaitem.write-model.md:322` — "**Under `ReviewPolicy.RequiredForPublish`, at least one reviewer is
  required.** Publishing such an item with an empty roster is refused with `MinimumReviewersRequired`."
- `…/mediaitem.api.md:519` — "`reviewerIds` is optional — omit it or send an empty array for an immediate
  publish, **except where the item's profile sets `ReviewPolicy = RequiredForPublish`**, which refuses an
  empty roster with `MinimumReviewersRequired`."
- `shared/error-catalog.md:256` — "| `MinimumReviewersRequired` | 422 | `POST /items/{itemId}/publish`
  naming no reviewers, on an item whose profile sets `ReviewPolicy = RequiredForPublish` |"

**Checked** MI-1's key-points block against `RequestPublication` in the write model, the `/publish` endpoint
contract, and the Catalog — MediaItems error table. `README.md:29` makes the write model the owner of
transitions and scenarios explicitly non-normative ("Scenarios illustrate transitions; they do not define
them").

**Why** These cannot both be specified. If `ReviewPolicy` is unread, `MinimumReviewersRequired` is a code
nothing can raise and `RequiredForPublish` is inert. If it is read, MI-1 tells an implementer the exact
opposite about the one gate that makes the policy enforceable. This is MM-001's **SB-43** closed in three
files and not in the fourth.

**Ruling** Correction. Delete the sentence at `mediaitem.scenarios.md:496` and replace it with the
`RequiredForPublish` rule as the write model states it. **Note the dependency: SC-018 may change what that
rule says for the auto-submit path.**

---

**SC-028**
**Severity** High
**Kind** Contradiction
**Claim** Registration specifies both that a status-machine refusal carries a `currentStatus` extension
member and that it never carries one — and the catalogue that owns the question contradicts itself on it
too.

**Evidence**
- `contexts/Registration/aggregates/Registration/registration.api.md:40` — "**A status-machine refusal
  carries the current status as `currentStatus`**, and repeats it in `detail` for a reader. A client
  branching on where the aggregate actually is reads the member and never parses the sentence."
- `…/registration.write-model.md:209` — "The current status is named in the refusal's `detail`, never in
  `extensions`: the platform's problem-details pipeline carries no domain-error extension beyond
  `errorCode`."
- `shared/error-catalog.md:75` — "| `currentStatus` | `InvalidStatusTransition` | The status the aggregate
  is actually in |"
- `shared/error-catalog.md:93` — "| `InvalidStatusTransition` | 422 | … | Inspect the root-level
  `currentStatus`; issue the correct command for that state |"
- `shared/error-catalog.md:514` — (§ Registration) "| `InvalidStatusTransition` | 422 | … **The status is
  named in `detail`** | Read `detail`; issue the correct command for that state |"
- `shared/error-catalog.md:54` — "**Extensions other than `errorCode` arrive at the root.** The originating
  `DomainError`'s `WithMetadata` members are copied onto the response alongside `errorCode`."
- `shared/api-conventions.md:260` — "**A value a client must branch on is never delivered only as a sentence
  in `detail`**, because that forces a client to parse English and makes the message's wording a contract
  nobody meant to sign."

**Checked** § Refusal status codes in both Registration files against the catalogue's extension-member
index, its § Common row, its § Registration row, and the api-conventions rule governing extension members.
`README.md:45` routes failures to `error-catalog.md` — and the owner file does not settle it, because
`:514` disagrees with `:75` and `:93`.

**Why** These are not two readings of one rule. One side says the member exists and is declared; the other
says the pipeline carries no extension beyond `errorCode` at all, which `error-catalog.md:54` says is false
of the platform. A client cannot be written against both, and the branch value is the aggregate's current
status — the one thing a caller needs to recover.

**Ruling** Correction. Delete the second clause of `write-model.md:209` and state that
`InvalidStatusTransition` carries root-level `currentStatus`; amend `error-catalog.md:514` to name
`currentStatus`, matching `:75` and `:93`. (The opposite resolution is much larger — it would remove
`currentStatus` from the extension index and the § Common row and put Registration in conflict with
`api-conventions.md:260`.)

---

**SC-029**
**Severity** High
**Kind** Contradiction
**Claim** The tree gives two incompatible answers to whether a `Registration.*.All` holder may act on
another officer's filing: the handler predicate admits only a System actor or the officer, while the
erasure sections and the platform `.All` rule admit a `.All` holder.

**Evidence**
- `shared/api-permissions.md:73` — "**`.All` widens the range of the resource predicate. It does not remove
  the predicate.** An owner-scoped resource is still checked at the aggregate; what `.All` changes is what
  that check ranges over — from *owned by the caller* to *in the caller's tenant*."
- `contexts/Registration/aggregates/Registration/registration.write-model.md:351` —
  "`RegistrationOwnership.CheckOwner` — caller is a `System` actor **or** `actor.Id ==
  registration.OfficerId` | `NotResourceOwner` (403)"
- `…/registration.write-model.md:360` — "`RegistrationOwnership.CheckOwner` **fails closed**"
- `…/registration.write-model.md:554` — "once it is cleared every owner-scoped route on that registration is
  refused `403 NotResourceOwner` and only a `Registration.Manage.All` holder or a `System` actor can act on
  it."
- `…/registration.api.md:460` — "**Afterwards the registration has no owner.** Every owner-scoped route on
  it answers `403 NotResourceOwner` to any caller who is not a `System` actor or a
  `Registration.Manage.All` holder"
- `…/registration.api.md:87` — "**A permission is checked at the edge; a resource predicate is checked in
  the handler or the aggregate.** The two are separate layers and neither substitutes for the other."

**Checked** `api-permissions.md` § The `.All` constraint and § The set (`:96`) against the Registration api
§ Authorization rows (`:95-99`) and the write-model handler pre-conditions, plus
`adrs/ownership-and-authorization.md:62`.

**Why** Both erasure paragraphs carve a `Manage.All` holder out of a predicate that, stated in three
places, has exactly two branches — and the carve-out's own justification ("the predicate those routes check
compares against the identity this call cleared") is the reason a `Manage.All` holder would *also* be
refused. If the platform `.All` rule is what admits them, the carve-out is not special to erasure at all:
a `Registration.ReadWrite.All` holder could submit or cancel **any officer's live filing**, which no
Registration file states and which `api.md:87` appears to deny. As written, an implementer cannot tell
whether `CheckOwner` must consult the caller's permissions.

**Ruling** Needs a decision. **Smallest question: does holding `Registration.ReadWrite.All` (or the
`Manage.All` that subsumes it) satisfy the owner predicate on the five owner-driven routes?**
- **Yes** — § Handler-side pre-conditions and the api § Authorization rows must state the third branch, and
  `error-catalog.md:508`'s `NotResourceOwner` condition needs the same widening. Consequence: a `Manage.All`
  holder can submit and cancel other officers' live statutory filings, which nothing currently says.
- **No** — Registration is a stated exception to § The `.All` constraint and must say so, and both erasure
  paragraphs drop the `Manage.All` clause, leaving an erased registration actionable only by a `System`
  actor.

---

**SC-030**
**Severity** Medium
**Kind** Contradiction · a pointer that resolves to the opposite
**Claim** The `actor_type == "System"` condition on Registration's five decision routes is specified as
edge authorization by the write model, which points at the api file to confirm it — and that file files the
condition in the column it defines as handler- or aggregate-checked.

**Evidence**
- `contexts/Registration/aggregates/Registration/registration.write-model.md:362` — "**It is deliberately
  not applied to the five `[System]` commands.** … Their `actor_type = \"System\"` gating is **edge**
  authorization — see [`registration.api.md` § Authorization](./registration.api.md)."
- `…/registration.api.md:87` — "**A permission is checked at the edge; a resource predicate is checked in
  the handler or the aggregate.**"
- `…/registration.api.md:101-105` — the five decision rows carry `actor_type == "System"` in the **Resource
  predicate** column, e.g. `:102` — "| `POST /v1/registrations/{registrationId}/confirm` |
  `Registration.Manage.All` | `actor_type == \"System\"` |"
- `shared/multi-tenancy-and-auth.md:168` — "Authorization is never enforced at the HTTP layer: no endpoint
  uses `Roles()`, `Permissions()`, `Policies()` or `Claims()`."
- `shared/security-scenarios.md` PERM-2 — "There is **no `RequireActorType` policy** … Actor-type authority
  is checked **inside command handlers**, against the string literal `\"System\"`, *after* the aggregate has
  been loaded."

**Checked** The write model's pointer target against what that section actually says, and both against the
platform's two statements on where actor-type authority is enforced. PERM-2 names `RegistrationOwnership`
explicitly as one of the handler-side redeclarations.

**Why** The pointer resolves to the opposite of what it claims. The difference is observable: an edge check
refuses before the aggregate loads (`403` on a nonexistent id), a handler check loads first — which is why
PERM-2 insists `404` precedes `403`, and why `registration.api.md:409` relies on the handler ordering
("**The guards are evaluated in that order**", registration-exists first).

**Ruling** Correction. Change `write-model.md:362-365` to say the `actor_type = "System"` gating is checked
in the handler after the registration loads, consistent with PERM-2 and § Guard evaluation order; keep
`Registration.Manage.All` as the edge check.

---

**SC-031**
**Severity** Medium
**Kind** Contradiction
**Claim** Registration is specified both as carrying no retention period and as carrying a statutory one.

**Evidence**
- `contexts/Registration/aggregates/Registration/registration.write-model.md:508` — "**A registration
  carries no retention period, and nothing expires or deletes one.** It is kept for as long as the tenant's
  data is kept."
- `contexts/Registration/context-overview.md:72` — "**Nor does a registration expire once resolved**: it
  carries no retention period, because it is the evidence that a transfer of custody happened."
- `…/registration.api.md:358` — "a caller must not be able to backdate the confirmation of a filing that
  becomes a permanent legal record **with a statutory retention period**."
- `…/registration.read-model.md:63` — "`TENANT#{tenantId}#REGISTRATIONS` grows without bound: a
  compliance-grade tenant accumulates filings **for the statutory retention period** and nothing removes
  them."

**Checked** § Retention — the owning section, which `context-overview.md:74` points to — against the two
incidental mentions; also `context-overview.md:29-31`, "**Not responsible for** … any retention period,
due-date calculation or disposal review — a registration has none and nothing expires one."

**Why** § Retention argues at length that a registration is *evidence of* a disposal action and is governed
by no schedule; two other files assert a statutory period as settled fact — one as the justification for a
contract decision (no client-supplied `confirmedAt`), one as the premise of a scaling caveat. A reader
sizing the partition, or deciding whether a disposal engine ever reaches these rows, gets opposite answers.
This is MM-001's **SB-52** resolved in the owning file and not swept.

**Ruling** Correction. In `api.md:358-360` drop "with a statutory retention period" — the backdating
rationale stands on "permanent legal record" alone; in `read-model.md:63` replace "for the statutory
retention period" with "for as long as the tenant's data is kept", matching § Retention.

---

**SC-032**
**Severity** Medium
**Kind** Contradiction
**Claim** The `MediaProfile` capability table says `Signing` gates nothing; DocumentSigning specifies it as
the gate on initiating a signing session, with a dedicated refusal code and HTTP status.

**Evidence**
- `contexts/Catalog/aggregates/MediaProfile/mediaprofile.write-model.md:177` — "**Two capabilities gate
  behaviour. Seven gate nothing.**"
- `…/mediaprofile.write-model.md:190` — "| `Signing` | Nothing behavioural. `LinkSigningSession` checks only
  `IsArchived` | ❌ |"
- `contexts/DocumentSigning/aggregates/DocumentSigningSession/documentsigningsession.write-model.md:101` —
  "| The item's `MediaProfile` must carry the `Signing` capability | `SigningCapabilityNotEnabled` |
  `InitiateSigningSessionHandler` |"
- `…/documentsigningsession.write-model.md:178` — "| `InitiateSigningSessionHandler` | Profile carries the
  `Signing` capability | `IMediaProfileQueryService.GetPublishedAsync` | `SigningCapabilityNotEnabled` |"
- `shared/error-catalog.md:568` — "| `SigningCapabilityNotEnabled` | 422 | `InitiateSigningSession` — the
  item's profile does not carry `Capability.Signing`. Module-prefixed, matching
  `RegistrationCapabilityNotEnabled` | Add the capability to the profile, or sign a different item |"

**Checked** The DocumentSigning invariant and handler pre-condition tables against `mediaprofile.write-model.md`
§ Capabilities — the file `README.md:41` names as owning the `Capability` vocabulary — and the catalogue
row.

**Why** The MediaProfile row answers "what does `Signing` gate?" by naming only `LinkSigningSession` and
concluding "nothing behavioural". But the gate is on `InitiateSigningSession`, one command earlier and in
a different context, and it has a dedicated refusal code with a status. The `❌` is wrong and the count
"two … seven" is wrong with it. A reader auditing capabilities from the Catalog side concludes `Signing` is
decorative and removes the check.

**Ruling** Correction. `mediaprofile.write-model.md:190` → `Signing` gates `InitiateSigningSession` in
DocumentSigning (`SigningCapabilityNotEnabled`), `✅`; `:177` → three capabilities gating behaviour and six
gating nothing. **If SC-011 resolves toward a live `Retention` gate, that count becomes four and five — do
the two edits together.**

---

### Group E — state machines that do not hold

Four findings.

---

**SC-033**
**Severity** High
**Kind** A state machine that does not hold
**Claim** The DocumentSigning saga declares a terminal state `Compensated` that no row of its transition
table can reach, and routes every compensation into `Completed` instead.

**Evidence**
- `contexts/DocumentSigning/sagas/documentsigningsaga.md:57-58` — "| `Completed` | Signed, recorded, item
  released | terminal | / | `Compensated` | Voided, cancelled or timed out; item released | terminal |"
- `…/documentsigningsaga.md:82-85` — "| `Releasing` | release path complete | — | `Completed` | / | any
  non-terminal | `SigningEnvelopeVoided` | Enter compensation | `Releasing` | / | any non-terminal |
  `SigningSessionCancelled` | Enter compensation | `Releasing` | / | any non-terminal |
  `SigningSessionTimedOut` | Enter compensation | `Releasing` |"
- `…/documentsigningsaga.md:56` — "| `Releasing` | Unlink and release in progress | completion of both
  commands |"
- `shared/saga-patterns.md:137-138` — "The scanner never writes saga state. It dispatches a command; the
  resulting event re-enters the saga and closes it through the normal transition table. **One path into
  every state.**"

**Checked** § State Table against § Transition Table in the same file, and both against the cross-cutting
rule above.

**Why** `Releasing` is the single funnel for the success path and all three failure paths, and the one row
leaving it is unconditional. Nothing distinguishes the two arrivals once the saga is in `Releasing`, so
`Compensated` is unreachable and **a timed-out session closes as `Completed`.** That defeats the state's
stated purpose — the saga status exists to answer "what is this saga waiting for and what will move it"
(`:67-68`) — and makes the operator runbook at `:240-243` unanswerable, because the terminal status no
longer records which outcome happened. `saga-patterns.md:138`'s "one path into every state" is violated in
the other direction: two paths into one state, none into another.

**Ruling** Needs a decision. **Smallest question: does the saga record compensation in its terminal
status?**
- **Yes** — split the funnel: `Releasing` → `Completed` on the `SignedAssetRecorded` branch, `Releasing` →
  `Compensated` on the three terminal-failure branches. The state must then carry which branch it entered
  on, which is a field on the saga payload. Preserves the file's stated intent and the runbook.
- **No** — delete `Compensated` from the state table and say the saga closes as `Completed` either way,
  with the outcome read from the session aggregate. Cheaper; the runbook must then say where to read it.

---

**SC-034**
**Severity** Medium
**Kind** A state machine that does not hold
**Claim** The statuses from which `FailAssetProcessing` is accepted are stated three incompatible ways in
one file, and the transition diagram — the section README makes authoritative — shows neither of the two
edges the other two statements require.

**Evidence**
- `contexts/AssetManagement/aggregates/Asset/asset.write-model.md:23` — "| Status must be `Validating` or
  `Processing` | varies by `FailureCategory` | `FailAssetProcessing` |"
- `…/asset.write-model.md:201-205` — the stage matrix: "| `Pending` | `UploadExpired` | · | `Validating` |
  `ValidationTimeout` | · | `Processing` | `ProcessingTimeout`, `ProcessingError` |"
- `…/asset.write-model.md:209` — "> `UploadExpired` pairs only with `Pending`, which is the pairing the
  upload-expiry saga depends on."
- `…/asset.write-model.md:60-87` — § Status transitions: the only inbound edge to `ProcessingFailed` is
  "Processing → (FailAssetProcessing) → ProcessingFailed"; there is **no** `Pending →` and no `Validating →`
  edge.
- `…/asset.write-model.md:250` — "| `AssetProcessingFailed` | … | Processing/Validating → ProcessingFailed |"
- `contexts/AssetManagement/context-overview.md:244` — "| `\"UploadExpired\"` | `AssetProcessingFailed` |
  Upload TTL elapsed; asset never left Pending |"

**Checked** The invariant row against the stage matrix, the transition diagram and the context overview's
failure-category table. `README.md` row 7 makes § Invariants authoritative for "what must always be true",
row 9 makes § Status transitions authoritative for "how an aggregate changes state" — and they disagree.

**Why** The invariant row forbids the `Pending`/`UploadExpired` pairing that the matrix declares mandatory
and the upload-expiry saga is said to depend on; the transition diagram shows neither missing edge. Three
readers of three sections build three different guards, and the one a reviewer is told to check is the
stale one.

**Ruling** Correction. Make the stage matrix the single statement: change the invariant row to `Pending`,
`Validating` or `Processing` (category-dependent), and add the two missing edges to § Status transitions.

---

**SC-035**
**Severity** Medium
**Kind** A state machine that does not hold
**Claim** `ReviewerAssignment.Decision` declares a `Withdrawn` value no command or event can produce, and
three files gate publication on a set that can therefore never be non-empty.

**Evidence**
- `contexts/Catalog/aggregates/MediaItem/mediaitem.write-model.md:110` — "| `ReviewerAssignment` | `{
  ReviewerId, Decision: Pending \| Approved \| Rejected \| Withdrawn, AssignedAt, DecidedAt? }` |"
- `…/mediaitem.write-model.md:333` — "Records the approval; when every **non-withdrawn** reviewer has
  approved, the item transitions to `Published`"
- `…/mediaitem.api.md:548` — "When every non-withdrawn reviewer has approved, the item publishes and the
  version increments."
- `…/mediaitem.scenarios.md:137` — "Publication fires only when every non-withdrawn reviewer has approved."
- `…/mediaitem.write-model.md:347-379` (§ Methods) and `:476-508` (§ Domain Events) — the only
  reviewer-decision writers are `ApproveReview`/`ReviewerApproved` and `RejectReview`/`ReviewerRejected`;
  there is no reviewer-withdrawal command, event or route. `Withdraw` acts on the **item**, clearing the
  session (`:338`, `:500`).
- `contexts/Catalog/context-overview.md:30` — "**Withdrawal is not a status.** `MediaItemWithdrawn` carries
  a `RestoredStatus` naming where the item returns to."

**Checked** The value object's enum against the full method and event inventory, the `/approve` and
`/reject` routes, and every occurrence of "withdrawn" in the Catalog tree.

**Why** A reviewer's decision can only ever be `Pending`, `Approved` or `Rejected` — and a rejection ends
the cycle and clears the session, so it never coexists with approvals. "Every non-withdrawn reviewer" is
therefore identical to "every reviewer", repeated in three files as if it carried a distinction, and an
implementer must invent a transition to make the fourth enum member reachable. `RejectReview`'s roster
guard also means `Withdrawn` would silently behave like `Pending` in the membership check.

**Ruling** Needs a decision, though a small one. **Smallest question: can a reviewer be withdrawn from an
open review?** If **yes**, specify the command, its event and its roster rule. If **no**, drop `Withdrawn`
from the enum and say "every reviewer has approved" in all three places.

---

**SC-036**
**Severity** Medium
**Kind** A state machine that does not hold
**Claim** The DocumentSigning write model states all three terminal failure states are reachable from any
non-terminal state, then states two sections later that one of them is reachable from only two.

**Evidence**
- `contexts/DocumentSigning/aggregates/DocumentSigningSession/documentsigningsession.write-model.md:42` —
  "Terminal failure states, reachable from any non-terminal state:"
- `…/documentsigningsession.write-model.md:47` — "| `Cancelled` | `CancelSigningSession` | The owner
  withdrew the request |"
- `…/documentsigningsession.write-model.md:103` — "| Cancellation is valid only in `Initiated` or
  `EnvelopeCreated` | `SigningSessionNotCancellable` | `CancelSigningSession` |"
- `…/documentsigningsession.api.md:154` — "Owner cancels. Valid only in `Initiated` or `EnvelopeCreated`."
- `shared/error-catalog.md:570` — "| `SigningSessionNotCancellable` | 409 | `CancelSigningSession` on a
  session outside `Initiated` / `EnvelopeCreated`. Carries root-level `currentStatus` |"

**Checked** § Status transitions against § Invariants in the same file, then against the cancel endpoint
and the catalogue row.

**Why** `EnvelopeSent` is non-terminal, so line 42 admits a cancel that line 103, the API and the catalogue
all refuse with a `409`. `README.md:29` makes § Status transitions the authoritative answer to how an
aggregate changes state, so the wrong statement sits in the section a reader is told to trust. Three
sources agree the restriction is real.

**Ruling** Correction. Change line 42 to state that `Voided` and `TimedOut` are reachable from any
non-terminal state and `Cancelled` only from `Initiated` or `EnvelopeCreated`.

---

### Group F — `architecture/` has drifted from the contexts

Five findings. `domain-model.md` is what `README.md` row 3 calls "the only inventory of the whole
platform", and `system-architecture.md` carries the diagrams a newcomer meets first. Both have fallen
behind five of the seven contexts.

**Worth stating plainly:** the *aggregate* inventory itself reconciles exactly — eleven aggregates in
`domain-model.md § Aggregates`, and 1+4+1+1+2+1+1 = 11 across the seven context overviews, verified by the
lead reviewer. The drift is in the per-aggregate detail sections, not the list.

---

**SC-037**
**Severity** High
**Kind** Contradiction
**Claim** `domain-model.md` states that no `ProcessingJob` is created for an asset without the `Processing`
capability; the entire Processing context is specified on the opposite rule, and the bypass path cannot
exist without the job.

**Evidence**
- `architecture/domain-model.md:396` — "Only created for assets whose owning MediaItem's `MediaProfile` has
  the `Processing` capability. Assets on profiles without `Processing` are virus-scanned only via the
  fast-exit path (**no `ProcessingJob` aggregate is created for them**)."
- `contexts/Processing/context-overview.md:22` — "- Create one `ProcessingJob` per confirmed upload,
  **whatever the asset's capability**"
- `contexts/Processing/aggregates/ProcessingJob/processingjob.write-model.md:12` — "One job per confirmed
  upload."
- `…/processingjob.write-model.md:23` — "Queued  → (Bypass)   → Bypassed    [terminal — no Processing
  capability on the owning MediaItem]"
- `architecture/domain-model.md:398` — "Created by `AssetUploadEventHandler` in the **Integration Event
  Consumers Lambda**" vs `contexts/Processing/context-overview.md:194` — "|
  `AssetUploadConfirmedIntegrationEvent` | AssetManagement | `AssetUploadConfirmedEventHandler` | Creates
  the job, then runs the scan |" on `media-processing`, **ProcessingWorker** (`:190`).
- `architecture/domain-model.md:419` — "**Key domain events:** `ProcessingJobCreated`,
  `ProcessingJobStarted`, `ProcessingJobSucceeded`, `ProcessingJobFailed`" against
  `processingjob.write-model.md:163-171`, which tabulates **seven**, including `ProcessingJobBypassed`.

**Checked** All four claims in `domain-model.md § ProcessingJob` against the Processing context overview's
§ Responsibilities and § Consumed tables, the aggregate's § Status transitions and § Domain Events, and
`architecture/bounded-contexts.md:265` (the `ProcessingWorker` host boundary). `README.md` row 3 makes
`domain-model.md` the platform inventory; rows 5, 6 and 9 make the write model authoritative for commands,
events and state — so the inventory is the wrong side on all four.

**Why** Three claims in one section are wrong and they reinforce each other, which is why a reader would
not notice: if no job exists for a non-capable asset, then `ProcessingJobBypassed` is indeed not a "key"
event and the fast-exit needs no job-level command. But the bypass path **is**
`BypassProcessingJobCommand` → `ProcessingJobBypassed` → `ProcessingJobBypassedIntegrationEvent` →
`BypassAssetProcessingCommand`, so removing the job removes the only carrier the fast-exit has — and the
fast-exit is the majority path for documents. The host attribution is wrong too: `EventConsumers` is the
intra-BC consumer host; job creation is `ProcessingWorker`'s.

**Ruling** Correction, no decision needed. One `ProcessingJob` is created per confirmed upload regardless
of capability; the capability decides which **exit** the job takes (`Succeeded` vs `Bypassed`), not whether
a job exists. Created by `AssetUploadConfirmedEventHandler` in `ProcessingWorker` off `media-processing`.
The event list should carry all seven or drop the word "key" and point at
`processingjob.write-model.md § Domain Events`.

---

**SC-038**
**Severity** Medium
**Kind** Contradiction · a pointer that resolves to the opposite
**Claim** Two files place the bypass-vs-start branch decision and the `Asset` transitions in the Processing
Worker; Processing states in three places that the worker holds no routing decision and that no
cross-context command dispatch occurs in either direction.

**Evidence**
- `contexts/AssetManagement/aggregates/Asset/asset.write-model.md:89` — "**Pipeline branching (determined
  by `AssetIngestionSaga` at `AssetValidationPassed`, with `AssetProcessingWorker` as defensive
  fallback):**"
- `architecture/domain-model.md:377` — "> **Note:** `AssetProcessingStarted` / `AssetProcessingCompleted` /
  `AssetProcessingFailed` on the Asset aggregate are signalled by the Processing Worker via
  `StartProcessingJob` / `CompleteProcessingJob` / `FailProcessingJob` commands…"
- `contexts/Processing/context-overview.md:68` — "Stateless executor — **it holds no routing decision**"
- `contexts/Processing/context-overview.md:69` — "| `SagaOrchestrator` | … | **Owns the bypass-vs-start
  decision** |"
- `contexts/Processing/aggregates/ProcessingJob/processingjob.api.md:38-39` — "**The saga owns the branch,
  not the worker.**"
- `contexts/Processing/context-overview.md:15-16` — "**no cross-context command dispatch occurs in either
  direction.**"
- `contexts/AssetManagement/aggregates/Asset/asset.write-model.md:102` — "no cross-BC command dispatch" —
  **thirteen lines after `:89` contradicts it.**

**Checked** `shared/operations.md:21` ("Stateless executor — saga routing owned by SagaOrchestrator") and
`processingjob.scenarios.md:80-81` ("The capability is resolved once, by AssetManagement, and carried on
the event. Neither the saga nor either worker makes a cross-context capability call").

**Why** "Defensive fallback" does not survive contact with the rest of the spec: a fallback branch in the
worker means the worker resolves capability, which the scenarios forbid. And `domain-model.md:377` names
three commands the Processing Worker cannot dispatch at all — `StartProcessingJob` and `FailProcessingJob`
are ProcessingJob commands that do not touch `Asset`, and the `Asset` transitions they are credited with
come from AssetManagement's own handlers. A reader implementing from either line puts a routing decision in
the wrong host, or a command across a boundary the spec closes.

**Ruling** Correction. Delete ", with `AssetProcessingWorker` as defensive fallback" from
`asset.write-model.md:89`. Rewrite `domain-model.md:377` to say the three `Asset` events are raised by
AssetManagement's handlers in response to `ProcessingJob*` integration events, naming
`ProcessingJobStartedEventHandler` / `ProcessingJobCompletedEventHandler` / `ProcessingJobFailedEventHandler`
as `context-overview.md:44-50` already does.

---

**SC-039**
**Severity** Medium
**Kind** An inventory that does not match itself
**Claim** `domain-model.md § Registration` states four things the aggregate spec contradicts, including
that `RegistrationSubmissionRecorded` causes no state change — which makes `Confirm` and `Reject`
unreachable.

**Evidence**
- `architecture/domain-model.md:451` — "└── RegistrationSubmissionRecorded  (records dispatch/reference
  details **without state change**)" vs
  `contexts/Registration/aggregates/Registration/registration.write-model.md:285` — "|
  `RegistrationSubmissionRecorded` | `SubmissionReference?`, `DispatchDetails?`, `RecordedAt` | **`Status →
  PendingConfirmation`** |" and `glossary.md:76` — "**PendingConfirmation** | The Registration status
  between external dispatch and the authority's decision"
- `architecture/domain-model.md:455` — "A `RegistrationAmendmentRequested` event opens an amendment on a
  **submitted or confirmed** registration." vs `registration.write-model.md:169` — "| `RequestAmendment`
  requires `Status = Confirmed` | `InvalidStatusTransition` | 422 |"
- `architecture/domain-model.md:129` — "| `RegistrationAmendment` | … | **Entity.** …" vs
  `registration.write-model.md:113` (under "## Value Objects") — "**The type is `Amendment`**, not
  `RegistrationAmendment`; the read DTO that carries it is `RegistrationAmendmentDto`." (`domain-model.md:569`
  also omits `DecisionNotes`, which `write-model.md:126` declares)
- `architecture/domain-model.md:439` — "| `Items` | … | MediaItems attached to the registration (**the
  primary item** plus any supporting document items)." vs `registration.scenarios.md:305` — "There is no
  \"primary\" item type — the item being *registered* is not an entry in `Items` at all; it is the
  registration's `mediaItemId`."

**Checked** `README.md` rows 4, 6 and 9, which make the write model authoritative for entity-vs-value-object,
for what events an aggregate raises and for how it changes state; `glossary.md` rows 29, 76 and 93, all
agreeing with the write model; and `domain-model.md:457`'s event list, which also omits
`RegistrationPersonalDataErased` (see SC-021).

**Why** Each of the four is a rule a reader could act on. The state-change one is sharpest:
`PendingConfirmation` is reachable **only** via `RegistrationSubmissionRecorded`, so a reader taking
`domain-model.md` at its word has a state machine in which `Confirm` and `Reject` — which require
`PendingConfirmation` — can never fire. `domain-model.md` is the inventory read by people outside this
context, so its Registration section is the version an outside reader meets first.

**Ruling** Correction. State that `RegistrationSubmissionRecorded` moves `Submitted → PendingConfirmation`;
scope amendment requests to `Confirmed`; rename `RegistrationAmendment` to `Amendment`, add `DecisionNotes`
and file it as a value object per README row 4; remove "the primary item plus" from the `Items` note.

---

**SC-040**
**Severity** Medium
**Kind** An inventory that does not match itself
**Claim** `domain-model.md`'s `DocumentSigningSession` entry declares a field the aggregate argues at
length must not exist, types two others differently, and draws a status lifecycle whose member names and
membership do not match the enum.

**Evidence**
- `architecture/domain-model.md:512-513` — "| `OwnerId` | `OwnerId` | | / | `InitiatedBy` | `OwnerId` | The
  user who initiated signing |"
- `architecture/domain-model.md:525-528` — "Initiated → EnvelopeCreated → **Sent** → Completed / → Voided /
  → Cancelled / → TimedOut"
- `contexts/DocumentSigning/aggregates/DocumentSigningSession/documentsigningsession.write-model.md:79` — "|
  `SigningSessionStatus` | `Initiated \| EnvelopeCreated \| **EnvelopeSent** \| Completed \|
  **SignedAssetRecorded** \| Voided \| Cancelled \| TimedOut` |"
- `…/documentsigningsession.api.md:83-84` — "**There is deliberately no second identity.** … a field naming
  an owner that no command sets and no guard reads is the kind of phantom this specification has been
  removing elsewhere."
- `…/documentsigningsession.write-model.md:62` — "| `InitiatedBy` | **`MemberId`** | **The session's
  owner.** … Set once at creation; immutable |"
- `architecture/bounded-contexts.md:354` — "`media-signing-envelope-lookup` … a narrow `EnvelopeId → {
  TenantId, **OwnerId**, SigningSessionId }` index" vs
  `…/documentsigningsession.read-model.md:50-55`, whose field table carries `PK`, `TenantId`,
  `SigningSessionId`, `ProjectedVersion` only, described at `:58` as carrying "nothing beyond what the
  webhook path needs".

**Checked** `domain-model.md § DocumentSigningSession` and the lookup design note against the write model's
§ Properties, § Value Objects and § Status transitions, the read model's lookup field table, and the API
file's § *`InitiatedBy` is the session's owner*.

**Why** `OwnerId` is the exact field the API file argues must not exist, and it now appears twice — on the
aggregate and in the webhook lookup row. Anyone implementing from the architecture file adds the phantom
back, which is how SC-008 will get "resolved" the wrong way. Separately the lifecycle names `Sent` where
the enum has `EnvelopeSent`, and omits `SignedAssetRecorded` entirely — the terminal success state, which
the read models must project and which `documentsigningsession.api.md:258` shows in a list response.

**Ruling** Correction. Delete the `OwnerId` row at `domain-model.md:512`; retype `InitiatedBy` to
`MemberId` and `SignedAssetId` to match the write model; redraw the lifecycle with all eight enum members
under their enum names; drop `OwnerId` from the lookup shape at `bounded-contexts.md:354`, which already
defers to the read model as authoritative.

---

**SC-041**
**Severity** Medium
**Kind** A pointer that resolves to the opposite · a state machine that does not hold
**Claim** Two `AssetIngestionSaga` sequence diagrams in `system-architecture.md` invert the boundary rule
the saga file states, and one lands the saga in a terminal state its transition table does not contain.

**Evidence**
- `architecture/system-architecture.md:463` — "        PW->>API: StartAssetProcessing" (participant `PW as
  ProcessingWorker`, `:456`) and `:471` — "        PW->>API: CompleteAssetProcessing"
- `contexts/Processing/aggregates/ProcessingJob/processingjob.scenarios.md:82-83` — "**Processing dispatches
  no command against `Asset`, and AssetManagement dispatches none against `ProcessingJob`.** Every hop
  between them is an integration event."
- `architecture/system-architecture.md:490` — "        TS->>API: FailAssetProcessing" vs
  `contexts/Processing/sagas/assetingestionsaga.md:128` — "| 1 | `ProcessingDispatched` |
  `FailProcessingJobCommand(ProcessingTimeout)` against **ProcessingJob** |"
- `architecture/system-architecture.md:493` — "        note right of SO: state → **Complete**<br/>compensation
  recorded" vs `assetingestionsaga.md:44-58` — the five states are `AwaitingValidation`,
  `ProcessingDispatched`, `Bypassed`, `Completed`, `Failed`; **there is no `Complete`.**
- `architecture/system-architecture.md:500` — "        note right of SO: a spurious timeout is
  reversed<br/>**Failed → Completed**"

**Checked** `architecture/system-architecture.md:447-449`, which defers to the saga file for the state
machine, and `contexts/Processing/context-overview.md:44-50`, which names the AssetManagement handler that
dispatches each command.

**Why** The diagrams sit directly under a note deferring to the saga file, which is what makes them false
pointers rather than independent views: a reader arrives expecting a rendering of the owning spec and gets
a sequence that inverts its central boundary rule and omits the two hops that exist. The timeout diagram
additionally contradicts **itself** — the first rect says the timeout leaves the saga in "Complete", the
second says recovery moves it `Failed → Completed`, which requires the first to have left it `Failed`. It
cannot be read as a single run on its own terms.

**Ruling** Correction, no decision needed. Redraw both rects with AssetManagement as a participant:
`PW → CH: RecordProcessingJobScanResultCommand` → SNS → `AM: RecordValidationResultCommand` → SNS →`SO`;
and `PW → CH: CompleteProcessingJobCommand` → SNS → `AM: CompleteAssetProcessingCommand` → SNS → `SO`.
`:490` becomes `FailProcessingJob(ProcessingTimeout)` against `ProcessingJob`; `:493` becomes "state →
Failed". `processingjob.scenarios.md:87-126` already draws it correctly and can be the source. **Related
but distinct from MM-001 SB-64** — that finding is about fenced diagrams carrying *removed* content; these
carry *wrong* content.

---

### Group G — navigation: `README.md` and `glossary.md`

Five findings. These are the two files whose whole job is to send a reader to the right place, and
`README.md` says of itself that a navigation file is a subject, not only a guide.

---

**SC-042**
**Severity** High
**Kind** A pointer that no longer resolves
**Claim** `glossary.md` names `shared/system-spec.md` as the **Authority** for eight terms; the file does
not exist, and the glossary's own preamble says it is gone.

**Evidence**
- `spec/glossary.md:4` — "Before this file existed the same terms were defined in eight competing tables —
  `architecture/domain-model.md`, **`shared/system-spec.md`**, and a `## Ubiquitous Language` section in six
  of the seven context overviews. **Those are gone**; this is the only place in `docs/spec/` that defines a
  term."
- The Authority column then cites it for eight terms: `Alias (OpenSearch index)` (`:27`), `Event Store`
  (`:54`), `` `IActor` `` (`:58`), `` `OwnerId` `` (`:75`), `Projection` (`:80`), `System actor` (`:105`),
  `` `TenantId` `` (`:106`), `tier-policy` (`:107`).
- Three more spec files cite it in prose: `architecture/system-architecture.md:746` — "See
  `shared/system-spec.md §Token Validation (stateless)`."; `shared/api-conventions.md:57` — "See
  `system-spec.md §Token Validation (stateless)`."; `shared/api-conventions.md:989` — "See `system-spec.md
  §Idempotency` for full behaviour."
- `find docs -name 'system-spec*'` returns **nothing**. Verified by the lead reviewer.

**Checked** The full `docs/` tree; and `spec/glossary.md:12-13`, which defines the column: "**Authority** is
the file to read when this one line is not enough. It is where the detail lives, not a second definition."

**Why** `README.md` row 1 makes `glossary.md` "**the only file in this tree that defines a term**", and its
escape hatch for eight cross-cutting terms — including `TenantId`, `OwnerId` and `IActor`, the three most
load-bearing identifiers on the platform — points at a file that was deleted. The glossary states in its
own preamble that the target is gone and then relies on it eight times. The `api-conventions.md:989`
pointer is the worst of the three: it defers idempotency's "full behaviour" to a deleted file **from the
file that now owns the idempotency contract**.

**Why the guard missed it** These are plain-text file names in a table cell, not markdown links, so the
`links` check's `\]\(([^)\s]+)\)` pattern cannot see them. See § Method note.

**Ruling** Correction. Repoint all eleven: `TenantId` / `OwnerId` / `IActor` / `System actor` →
`shared/multi-tenancy-and-auth.md`; `Event Store` / `Projection` / `tier-policy` / `Alias (OpenSearch)` →
`shared/event-store-and-messaging.md`; the two token-validation pointers → `shared/multi-tenancy-and-auth.md`
§ Token Validation; `api-conventions.md:989` → its own § Idempotency.

---

**SC-043**
**Severity** High
**Kind** Contradiction · an inventory that does not match itself
**Claim** The tree gives three incompatible answers to how many sagas it specifies, and `glossary.md`
contradicts itself on it inside one file.

**Evidence**
- `spec/glossary.md:98` — "| **Saga** | A long-running process coordinating work across aggregates, with
  durable state in `media-sagas`. **`AssetIngestionSaga` is the only saga.** |"
- `spec/glossary.md:49` — "| **DocumentSigningSaga** | **The saga** orchestrating MediaItem checkout linkage
  and release across the signing lifecycle. |" — in the same file, forty-nine lines earlier.
- `spec/README.md:34` (row 12) — "**live**, to the nine-section contract. Three files: `AssetIngestionSaga`
  (**the only saga**), `documentsigningsaga.md` and `archive-fan-out.md` (two process managers)"
- `spec/README.md:83-85` — "DocumentSigning/ has **a design record for a saga that does not exist**"
- `shared/saga-patterns.md:15-16` and `:103-104` — both saga inventories list `AssetIngestionSaga` **and**
  `DocumentSigningSaga`, with no caveat.
- `contexts/DocumentSigning/sagas/documentsigningsaga.md:216` — normative throughout, and nowhere identifies
  itself as a design record: "**An event missing from this policy is not delivered, and the saga stalls
  silently rather than failing**, which is why a tenth event on this aggregate is a change to this policy as
  well."

**Checked** Both README statements against each other, both `saga-patterns.md` inventories, the saga file's
own framing, and `archive-fan-out.md:6` — "**These are not sagas.**" — which shows the convention the tree
already has for marking a file that follows the saga contract without being one, **stated in the file
itself, not only in the index**.

**Why** Row 12 sends a reader to the signing saga as live normative content; the file-tree annotation
nineteen lines later tells them it describes something that is not there. `glossary.md` — the file README
row 1 makes the sole definer of terms — does both in one table. A reader cannot tell whether to build
against `documentsigningsaga.md` or ignore it, and the nine-section file is fully specified either way.

**Note on scope.** Whether the saga is *built* is a code fact and out of scope. What is in scope is that
the documents give three different answers to how many sagas are **specified**.

**Ruling** Needs a decision. **Smallest question: is `DocumentSigningSaga` part of the specified system?**
- **Yes** — delete "a saga that does not exist" from `README.md:85`, change row 12's parenthetical to name
  both sagas, and fix `glossary.md:98` to say two.
- **No** — the disclaimer belongs in the saga file's own opening in the `archive-fan-out.md` shape, and
  both `saga-patterns.md` inventories need the same caveat.
Either way **the index must not say both**, and `glossary.md` must not say both in one table.

---

**SC-044**
**Severity** Medium
**Kind** A pointer that resolves to the opposite
**Claim** `README.md` tells a reader that `<agg>.design-decisions.md` exists for **RecordType only**;
RecordType has no such file, and the two aggregates that do have one are not named.

**Evidence**
- `spec/README.md:40` (row 14e) — "| 14e | **why a rule is the shape it is** … | `<agg>.design-decisions.md`
  where it exists — **RecordType only**. Elsewhere the design sections are inline in `<agg>.write-model.md`
  | … **The design file carries why.** |"
- `spec/README.md:88-90` — "`<agg>.design-decisions.md` designed-and-not-shipped work · rejected
  alternatives. / **RecordType only so far**; elsewhere this is still inline / in the write model"
- Directory listing: `contexts/Metadata/aggregates/RecordType/` contains `recordtype.api.md`,
  `recordtype.read-model.md`, `recordtype.scenarios.md`, `recordtype.write-model.md`,
  `recordtype-diagrams.html` — **and no `recordtype.design-decisions.md`.**
- The two that exist: `contexts/Catalog/aggregates/MediaProfile/mediaprofile.design-decisions.md` (187
  lines) and `contexts/Metadata/aggregates/RetentionSchedule/retentionschedule.design-decisions.md` (227).
- `contexts/Metadata/context-overview.md:260` — "- ~~RecordType Design Decisions~~ — **there is no
  `recordtype.design-decisions.md`.** Its rules live in the write model; links elsewhere in `docs/spec` that
  still name it do not resolve — **see the note at the foot of `recordtype.write-model.md`**"
- `contexts/Metadata/aggregates/RecordType/recordtype.write-model.md:1859-1866` — the entire foot of the
  file is a `## Related` list. **There is no such note, at the foot or anywhere.**

**Checked** README row 14e and the file-tree block against the actual contents of all ten aggregate
folders; and `recordtype.write-model.md` end to end for the promised note.

**Why** README is the tree's index of which file answers which question, and row 14e sends a reader asking
*why is this MediaProfile rule shaped like this* to the write model and away from the 187-line file that
answers it — while pointing at an aggregate that has no such file at all. Wrong in both directions. And the
tree's own remedy for the stale pointer, at `context-overview.md:260`, terminates in a promise that is not
kept.

**Ruling** Correction. Update row 14e and the file-tree annotation to name `MediaProfile` and
`RetentionSchedule` and drop the RecordType claim; and either write the note at the foot of
`recordtype.write-model.md` or drop the "see the note" clause from `context-overview.md:260`.

---

**SC-045**
**Severity** Low
**Kind** An inventory that does not match itself
**Claim** `README.md` § *Read this before trusting a detail* introduces "two things" and lists one; and
row 10 says seven internal relationships where there are ten.

**Evidence**
- `spec/README.md:104-105` — "This spec is mid-remediation, and **two things** are known to be wrong in ways
  a careful reader would not otherwise catch:" — followed by **exactly one** bullet (`:107-114`), then the
  closing line at `:116`.
- `spec/README.md:31` (row 10) — "**all 17 relationships carry a type**, including **the seven internal
  ones**"
- `architecture/bounded-contexts.md:91-97` — § Context Relationship Types: **seven** external rows.
- `architecture/bounded-contexts.md:112-121` — § Internal context relationships: **ten** rows (Catalog ↔
  AssetManagement, AssetManagement ↔ Processing, Metadata → Catalog, Catalog ↔ ChangeRequests, Catalog ↔
  Registration, Catalog ↔ DocumentSigning).

**Checked** Row counts taken by the lead reviewer directly from both tables. 7 + 10 = 17, so the **total**
is right and the split is wrong.

**Why** Small, but this is the index, and both are the kind of count a reader uses to check they have seen
everything. "Two things" invites a search for a second warning that was removed and not recounted; "seven
internal" invites a reader to stop at seven of ten.

**Ruling** Correction. Either restore the second item or change "two things" to "one thing"; change row 10
to "the ten internal ones".

---

**SC-046**
**Severity** Low
**Kind** Contradiction
**Claim** Three `glossary.md` rows disagree with the file each names as its own Authority.

**Evidence**
- `spec/glossary.md:97` — "| **ReviewSession** | The active review on a MediaItem: `{ ReviewSessionId,
  CommentThreadId?, Reviewers, StartedAt, OriginStatus }` | Catalog | `mediaitem.write-model.md` § Value
  Objects |" vs `contexts/Catalog/aggregates/MediaItem/mediaitem.write-model.md:109` — "| `ReviewSession` |
  `{ Id, CommentThreadId?, Reviewers, StartedAt, OriginStatus, SessionEditorsOrNull?,
  EditSessionChangeRequestId? }` — **the first member is `Id`, not `ReviewSessionId`.**" — the glossary
  states the exact thing the write model corrects, and omits two members.
- `spec/glossary.md:102` — "| **SigningSessionStatus** | … A **read-model** status, consumed by the
  projector. Not a saga status. |" vs
  `contexts/DocumentSigning/aggregates/DocumentSigningSession/documentsigningsession.write-model.md:79` —
  declared under § Value Objects, `Domain/ValueObjects/`, and carried on the aggregate at `:63` ("| `Status`
  | `SigningSessionStatus` |").
- `spec/glossary.md:79` — "| **ProcessingJob** | The aggregate tracking one asset's processing lifecycle:
  `Queued → Running → Succeeded \| Failed`. |" vs
  `contexts/Processing/aggregates/ProcessingJob/processingjob.write-model.md:23` — "Queued  → (Bypass)   →
  **Bypassed**    [terminal …]" — the glossary omits a terminal status that its own `Fast-exit / Bypass` row
  (`:55`) describes.

**Checked** Each row against the file its own Authority column names, and against `README.md` row 4, which
makes `<agg>.write-model.md` § Value Objects the answer to what something is.

**Why** `README.md` row 1 makes this the only file that defines a term, so a wrong shape here is the
definition. The `ReviewSession` one is the consequential one: `EditSessionChangeRequestId` is the member
that carries the "two change requests live at once" pairing, and a reader working from the glossary does
not know it exists.

**Ruling** Correction. Bring all three rows into line with their stated Authority: `{ Id, … ,
SessionEditorsOrNull?, EditSessionChangeRequestId? }`; `SigningSessionStatus` is a domain value object
projected onto the read models (keeping the true half — it is not a saga status); and add `Bypassed` to the
`ProcessingJob` lifecycle.

---

### Group H — one quantity, stated more than once

Three findings. Each is a number a client or an operator would act on.

---

**SC-047**
**Severity** High
**Kind** A quantity stated twice, differently
**Claim** The number of RecordType routes on which `If-Match` is **required** is stated four different ways
across four files, and a fifth file claims no other route in the platform implements the header at all.

**Evidence**
- `contexts/Metadata/aggregates/RecordType/recordtype.api.md:126` — "**Eleven routes require `If-Match` and
  answer `428 Precondition Required` without it**, in three groups:" — the table below it lists 5 + 4 + 2 =
  **11**, and `:148` repeats "one of the eleven guarded routes".
- `shared/api-conventions.md:412` — "`If-Match` is **optional** on the two MediaItem metadata routes and
  **required** on **ten** RecordType routes"; `:418` — "| **Required** | **Ten RecordType routes** |"
- `shared/error-catalog.md:92` — "**This is the platform's first `428`**, and its **nine** routes are all on
  RecordType so far."
- `shared/consistency-model.md:89` — "⚠ **The header is *mandatory* on **four** RecordType routes** (`POST
  /publish`, `DELETE /draft`, `DELETE /{recordTypeId}`, and `POST /deprecate` once the draft guard is
  dropped)"
- `contexts/Catalog/aggregates/MediaItem/mediaitem.api.md:340` — "This endpoint and `PUT
  /v1/items/{itemId}/metadata` are the **only two endpoints in the platform** that implement `If-Match`."

**Checked** All five statements against `recordtype.api.md:126-132`, the only one that enumerates its
routes: publish, discard draft, deprecate, abandon, `versions/{version}/deprecate`, `PATCH
/fields/{fieldName}`, `/fields/{fieldName}/replace`, `DELETE /fields/{fieldName}`,
`/fields/{fieldName}/deprecate`, `PUT /aliases`, `PATCH /{recordTypeId}` — eleven, with `POST /fields` and
`/fields/reorder` deliberately excluded. `README.md:45` makes `<agg>.api.md` authoritative for what a route
is and `api-conventions.md` for cross-cutting rules.

**Why** This is the platform's advice to clients about lost-update protection on a regulated-records
system, and four files give four answers. `consistency-model.md:89` is the damaging one: it tells clients
"**On every other write a supplied `If-Match` is silently ignored**" while naming only four of eleven
mandatory routes — so seven routes that answer `428` without the header are described as ignoring it. Its
parenthetical "once the draft guard is dropped" is also a future-conditional in a file that states present
behaviour. And `mediaitem.api.md:340` makes a platform-wide claim that the platform-wide file refutes — the
"don't assume coverage" trap at `api-conventions.md:420`, in reverse.

**Ruling** Correction, no decision needed. **Eleven wins** — it is the only enumerated statement, it is in
the owning file, and 5 + 4 + 2 is checkable. Fix `api-conventions.md:412` and `:418` to eleven,
`error-catalog.md:92` to eleven, and rewrite `consistency-model.md:89` to name the eleven or point at
`recordtype.api.md § Optimistic concurrency` instead of re-enumerating. Narrow `mediaitem.api.md:340` to
its true scope: these are the only two endpoints on which `If-Match` is **optional** and triggers a
field-level rebase.

---

**SC-048**
**Severity** High
**Kind** A quantity stated twice, differently
**Claim** The document-signing budget has two different defaults, 336 hours and 72 hours, and they are not
a rounding difference but two designs.

**Evidence**
- `contexts/DocumentSigning/sagas/documentsigningsaga.md:105` — "| Default | **336 hours — 14 days** |"
- `…/documentsigningsaga.md:114` — "**14 days is measured against human latency, not compute.** It is long
  enough to absorb a signer on leave"
- `shared/saga-patterns.md:88` — "Document signing defaults to **72 hours** to accommodate human signing
  latency."

**Checked** The saga file's § Timeouts table and both justification paragraphs against `saga-patterns.md`
§ SagaTimeoutScanner, which states per-saga TTL defaults for both sagas in one sentence. Both are normative
statements of the same configuration default (`Media:DocumentSigning:SigningTimeouts` →
`SigningBudgetHours`).

**Why** They cannot both be the default, and 72 hours is outside the saga file's own reasoning — the saga
argues 14 days is the *minimum* that absorbs "a signer on leave". A three-day budget expires envelopes the
design intends to survive; the difference is visible to every signer.

**Ruling** `README.md:34` makes the per-saga file authoritative for one process and `saga-patterns.md`
cross-cutting-only, so **336 wins** and `saga-patterns.md:88` should read 336 hours (14 days). **Confirm
the intended budget before the edit** — if 72 is intended, the saga file's Range row (`24 – 2160 hours`)
and both justification paragraphs change with it, which makes it a ruling rather than a correction.

---

**SC-049**
**Severity** Medium
**Kind** A quantity stated twice, differently
**Claim** Five Asset quantities are stated two ways each — the bulk batch cap, the pre-signed URL TTL, the
multipart threshold, and the success codes on four endpoints — with the scenarios and one diagram
disagreeing with `asset.api.md`.

**Evidence**
- **Bulk cap, inside one file.** `asset.api.md:25` — "Bulk initiate uploads (**up to 50**)" and `:777` —
  "Initiates **up to 50** asset uploads in a single request." vs `:854` — "`400` — … batch exceeds
  `MaxAssetsPerRequest` (default **100**)", `:811` — "this endpoint creates **up to a hundred** at a time",
  `:949` — "(default **100**, configurable at
  `Media:AssetManagement:BulkOperations:MaxAssetsPerRequest`)". `shared/bulk-operations.md:132` — "| Assets
  (upload + confirm) | 100 | **100** | `Media:AssetManagement:BulkOperations:MaxAssetsPerRequest` |"
- **Part-URL TTL.** `asset.scenarios.md:335` — "Pre-signed part URLs expire at the `expiresAt` timestamp
  (**default 1 hour**)." vs `asset.api.md:266` — "Part URLs expire in **15 minutes**" and `:705-718` —
  "**Every pre-signed URL this API issues … expires after the same 15 minutes, from the same setting.** …
  **There is no separate part-URL TTL.**" and `glossary.md:77` — "15-minute TTL."
- **Multipart threshold.** `asset.scenarios.md:269` — "file size exceeds single-part threshold (**> 50
  MB**)" vs `asset.api.md:224` — "Use multipart for files **≥ 100 MB**; the platform default **part size is
  50 MB**." — the two numbers have been collapsed into one.
- **Success codes.** `asset.api.md:240/254/261` (the multipart mermaid diagram) — "API-->>Client: **202**"
  ×2 and "**200**" vs the endpoint declarations in the same file: `:289` "**`201 Created`**", `:339`
  "**`204 No Content`**", `:389` "**`204 No Content`**", `:464` "**`204 No Content`**" (archive). And
  `asset.scenarios.md:288, :314, :450` — "→ 202 Accepted" ×3.
- `shared/api-conventions.md:783` — "`202 Accepted` is reserved **exclusively** for endpoints in the table
  above" — that table (`:775-778`) lists `POST /v1/assets/{assetId}/uploads/confirm` and the signing-session
  route, **neither of these**.

**Checked** Each figure against `shared/bulk-operations.md`, `glossary.md:77` and
`api-conventions.md § Async Operations`. The `50` in `asset.api.md:25` and `:777` is the only pair with no
configured backing; the `1 hour` is four times the only stated value; `50 MB` is the part size stated as
though it were the cutoff.

**Why** Each is a number a client sizes a request against. A client batching to 100 is refused at 51 or
accepted at 100 depending on which sentence it read; a client sizing its upload window to an hour loses
every part URL mid-batch; a client polling a `202` that is really a `204` polls a finished operation
forever. The mermaid diagram disagrees with the endpoint declaration **in the same section of the same
file**.

**Ruling** Correction throughout, no decision needed. **100** (the configured cap and the shared batch-size
table) — fix `asset.api.md:25` and `:777`. **15 minutes** and **≥ 100 MB** — fix `asset.scenarios.md:335`
and `:269`. **`201`** for multipart initiate, **`204`** for complete, abort and archive — fix the mermaid
diagram at `:240/254/261` and the three scenario blocks. **Related to MM-001 SB-28**, which flagged `202`
usage generally; this is the specific list.

---

## Open Questions

**All fifteen answered 2026-09-18 (Chase).** Worked in tiers, Q1 and Q2 first because they change other
findings and both rewrite the same section. Q8 was answered after a walk-through of the pipeline ordering
rather than from the options as first framed.

**Tier 1 — the two that change other findings.**

1. **Does a published `RecordType` version carry a capability set?** (SC-010, SC-012) —
   **Answered:** *no. `RecordType` has no capability concept.* (Chase, 2026-09-18.)

   Metadata's owned contract stands. It is the owning file under `README.md` row 6, `glossary.md:34`
   defines `Capability` as "a domain module switch defined on a `MediaProfile`", and
   `context-overview.md:212-219` states the absence in its strongest terms.
   `RecordTypePublishedIntegrationEvent` gains nothing.

   **Effect.** SC-010 becomes a correction in five files — `mediaprofile.write-model.md:122,155`,
   `mediaprofile.design-decisions.md:65,83`, `metadata-schema-composition.md:18,31,44,49-56` and
   `domain-model.md:197` — each of which describes a member that does not exist. SC-012 resolves with it:
   the `SourceCapability` / `ICapabilityRegistry` / `MandatoryRecordkeepingCoreMissing` clause is deleted,
   keeping only the collision-qualification statement, which has carriers.

   **This ruling raises a code defect and does not close it.** With no capability set on any RecordType
   version, `CompiledMetadataTemplate.Capabilities` is a union over an empty family, so
   `Capabilities.Contains("Processing")` is permanently false and every asset takes the bypass — which is
   the condition `mediaprofile.design-decisions.md:83` says "cannot ship until the gate is re-sited".
   **Where Catalog's `Processing` gate reads its input from is a code question, diverted to MM-002**, not a
   checklist item here.

2. **Is `RetentionScheduleRef` part of the specified `MediaProfile`?** (SC-011) —
   **Answered:** *yes as a member; no as a publish gate.* (Chase, 2026-09-18 — *"the RetentionScheduleRef
   should [be] optional and not required to publish"*.)

   Neither of the two options this review framed. The member is **declared** on `MediaProfile` — nullable,
   at most one — so `RetentionSchedule` gains a real consumer and stops being an inventoried aggregate
   nothing can use. **Publishing is never gated on it.**

   **Effect.** SC-011 becomes: add the property row, the command, the event, the snapshot member and the
   read-model/API field; **delete the publish gate** from `domain-model.md:76`, `README.md:42` (row 14f-i)
   and `retentionschedule.design-decisions.md:105-110`. **No refusal code is needed**, which removes the
   catalogue addition this review assumed. `mediaprofile.write-model.md:152`'s "a profile pins exactly one
   `RetentionSchedule`" reasoning survives intact and stops being an argument from a phantom.
   `Retention` still gates nothing behavioural, so the capability count changes only via SC-032.

> Q1, Q2 and SC-032 all edit `mediaprofile.write-model.md` § Capabilities. **Rewrite that section once,
> after all three are in hand** — not three times.

**Tier 2 — authorization.**

3. **Is `force-release` admitted by `MediaItem.Manage` alone, or by System-or-owner?** (SC-025) —
   **Answered:** *both admit it.* (Chase, 2026-09-18.)

   An item owner can always break a lock on their own record; an administrator can break any lock in the
   tenant. **Encoded in the existing grammar rather than as a new OR pattern:** the route requires
   `MediaItem.Manage` with resource predicate `item.OwnerId == actor.Id`, and `MediaItem.Manage.All` widens
   that predicate tenant-wide per `api-permissions.md:73`. That is the same mechanism Q4 adopts, and it
   uses `MediaItem.Manage.All`, which is declared in the vocabulary and referenced nowhere today.

   **Effect.** `mediaitem.api.md:116` gains the predicate, `:147` is deleted, `:752`/`:756` keep the owner
   clause and gain the tier, and `api-permissions.md:206` stands as written. The encoding is this review's
   reading of the answer; **confirm it at phase 1** before the rows are written.

4. **Does holding `Registration.ReadWrite.All` satisfy the owner predicate on the five owner-driven
   routes?** (SC-029) — **Answered:** *yes — `.All` widens as the platform rule states.*
   (Chase, 2026-09-18.)

   No Registration exception. `RegistrationOwnership.CheckOwner` gains a third branch and the platform rule
   applies uniformly.

   **Effect.** The api § Authorization rows state the branch, and `error-catalog.md:508`'s
   `NotResourceOwner` condition widens. **The consequence is accepted and must be written down rather than
   left implicit:** a `Registration.ReadWrite.All` holder can submit and cancel another officer's live
   statutory filing. No Registration file says that today, and these are government filings — so it is
   stated explicitly in `registration.api.md` § Authorization, not left to be inferred from the `.All` rule.

5. **Do `DocumentSigningSession.Read.All` / `.ReadWrite.All` exist?** (SC-008) —
   **Answered:** *yes.* (Chase, 2026-09-18.)

   `DocumentSigningSession` moves out of `api-permissions.md` § Resources with no owned subset into the
   owned-subset table, owned set stated as "sessions the caller initiated", and both `.All` forms are
   defined. Administrators get a read surface and the runbook at `documentsigningsaga.md:240-243` becomes
   performable. **Closes MM-001's SB-12 on the side it was never fixed.**

6. **On the SQS path, what carries `actor_type`, and where is it checked?** (SC-013) —
   **Answered:** *neither — drop the requirement.* (Chase, 2026-09-18.)

   ProcessingJob's commands are pipeline-internal with no HTTP surface; `TenantId` from the SQS envelope is
   the boundary that matters. The `actor_type == "System"` requirement is removed rather than made
   enforceable.

   **Effect.** SC-013 becomes a deletion: `processingjob.api.md:65-82` loses the rule and the eight-row
   table's actor column; `api-permissions.md:116-126` § *The aggregate with no permissions* then stands on
   its own without an unenforceable companion. **`SystemActorRequired` is untouched** — it stays live for
   Registration's five decision routes (SC-022).

7. **At which layer is the `ProfileOrigin` guard applied?** (SC-026) —
   **Answered:** *command-level, with a stated seeder exemption.* (Chase, 2026-09-18.)

   The guard goes into `mediaprofile.write-model.md` § Handler-side Pre-conditions, so an in-process caller
   cannot mutate a seeded profile either. **The exemption must be specified precisely — it is the hole —**
   and `mediaprofile.defaults.md:31`'s "whatever permission the caller holds" then reads true rather than
   overstated.

**Tier 3 — behaviour.**

8. **How does `AssetProcessingWorker` get invoked?** (SC-016, SC-017) —
   **Answered:** *widen the `media-processing` filter.* (Chase, 2026-09-18, after walking the ordering.)

   `ProcessingJobStarted` already publishes to `media-integration-events`, and `media-processing` already
   subscribes to that topic — so this is a **filter-policy change, not new infrastructure**. The filter
   admits `media.asset.upload-confirmed` **and** `media.processingjob.started`; `ProcessingWorker` branches
   on message type. The saga's bypass-vs-start decision genuinely gates the rendition work, and the 1800 s
   visibility timeout becomes correct rather than inexplicable.

   **Why not one continuous invocation.** The capability flag is resolved by AssetManagement at hop 2 and
   the branch is taken by the saga at hop 3 — both *after* the worker terminates. A worker rendering in its
   original invocation would have to render before anyone decided whether to, which either defeats
   `Bypassed` or requires blocking on a two-hop SNS round trip. Resolving the capability itself is
   forbidden outright by `processingjob.scenarios.md:80-81`.

   **Effect.** The "one type only" statement changes in four places —
   `event-store-and-messaging.md:266`, `:287`, `system-architecture.md:292`, `:698` —
   `media.processingjob.started` gains a second consumer alongside AssetManagement, and
   `context-overview.md:119`'s "in-process; not separately triggered" is rewritten.
   **SC-017 resolves with it:** for video the worker blocks and extends visibility to 4 h, which
   `system-architecture.md:292` already states, so *"completion via EventBridge → SQS"* comes out of
   `context-overview.md:121` and no inbound MediaConvert leg is needed.

9. **Is `PUT /v1/items/{itemId}/metadata` a merge or a whole-draft replacement?** (SC-024) —
   **Answered:** *merge — omitted fields are left untouched.* (Chase, 2026-09-18.)

   Delete `mediaitem.api.md:449`. Consistent with the null-is-an-instruction section at `:409`, with the
   bulk route which merges, and with the `If-Match` rebase check at `:351`, whose "write set" reasoning is
   meaningless under whole-draft replacement. A client cannot destroy fields it never loaded.

10. **Under `ReviewPolicy = RequiredForPublish`, what roster does auto-submit pass?** (SC-018) —
    **Answered:** *auto-submit does not fire under review.* (Chase, 2026-09-18.)

    Auto-submit is inert when `ReviewPolicy != None`. No roster is needed and `MediaProfile` gains no
    member.

    **Effect.** One sentence in `mediaprofile.api.md:399` and the write model's auto-submit paragraph.
    **Follow-on to settle in the same edit:** `Governed Media Record` sets `RequiredForPublish` **and**
    `AutoSubmit ✓`, so its `AutoSubmit` flag now claims a behaviour that never happens on it —
    `mediaprofile.defaults.md:140` either withdraws the flag or states why it is carried inertly.

11. **Can a reviewer be withdrawn from an open review?** (SC-035) —
    **Answered:** *yes — add the command.* (Chase, 2026-09-18.)

    `Withdrawn` stays in the enum and becomes reachable. This is **design work, not a correction** — the
    larger of the two options, and the finding's scope grows accordingly: a remove-reviewer command, its
    event, a route, a permission row, an error code, and a roster rule for what happens when the last
    reviewer is removed. **It interacts with `MinimumReviewersRequired`** under `RequiredForPublish`:
    removing the last reviewer on such an item must be refused or must block publication, and which is a
    sub-decision for the phase that writes it.

12. **Does the signing saga record compensation in its terminal status?** (SC-033) —
    **Answered:** *no — delete `Compensated`.* (Chase, 2026-09-18.)

    The saga closes as `Completed` on every path. The outcome is read from the session aggregate, whose
    status already distinguishes `Voided`, `Cancelled`, `TimedOut` and `SignedAssetRecorded`.

    **Effect.** Remove the `Compensated` row from § State Table; the single unconditional row leaving
    `Releasing` then reads correctly. **The runbook at `:240-243` must say where the real outcome is read**,
    since the saga status no longer answers it — that is the part not to lose.

13. **Is the signing budget 336 hours or 72?** (SC-048) —
    **Answered:** *336 hours — 14 days.* (Chase, 2026-09-18.)

    `README.md` row 12 makes the per-saga file authoritative for one process. One line changes in
    `saga-patterns.md:88`; the saga file's Default row, Range row (`24 – 2160 hours`) and both justification
    paragraphs stand as written.

**Tier 4 — inventories with a consumer on the other end.**

14. **Do Billing and Notifications subscribe to `media.processingjob.completed` / `.failed`?** (SC-009) —
    **Answered:** *no — asset-level only.* (Chase, 2026-09-18.)

    Strike "Billing (capability-filtered)" and "Notifications" from `context-overview.md:178-179`. Matches
    the boundary rule at `processingjob.write-model.md:252-254` — Processing publishes job-level facts,
    AssetManagement publishes asset-level ones — and matches the shared routing inventory. Both consumers
    stay fed from `media.asset.processing-completed` / `.failed`.

    **The two corrections in SC-009 stand regardless:** `media.processingjob.created` and
    `media.processingjob.bypassed` still need routing rows, because a published event with no routing row
    is how a subscription gets missed.

15. **Is `DocumentSigningSaga` part of the specified system?** (SC-043) —
    **Answered:** *yes.* (Chase, 2026-09-18.)

    Delete "a design record for a saga that does not exist" from `README.md:85`, change row 12's
    parenthetical to name both sagas, and fix `glossary.md:98` to say two. The saga file stands as written
    and takes no disclaimer; build status stays in the repo `CLAUDE.md` § Known deferred/partial work, where
    it already is.

    **This ruling raised SC-050**, which had been dropped in reconciliation on the strength of
    `README.md:85` — one side of the contradiction SC-043 reports. The signing saga's timeout scanner
    covers one of four non-terminal states and is registered on no host.

---

### Raised after the fan-out, by a ruling

**SC-050**
**Severity** High
**Kind** A rule with no carrier · a half-designed path
**Claim** The signing budget is specified to start at session creation so a failed provider call can be
compensated, and the only scanner specified to enforce it looks at one of four non-terminal states — not
the one that case sits in — while the host that runs scanners registers no signing scanner at all.

**Evidence**
- `contexts/DocumentSigning/sagas/documentsigningsaga.md:44-45` — "**Created on `SigningSessionInitiated`**,
  before the envelope exists, so the saga covers the provider call itself and can compensate a failed one."
- `…/documentsigningsaga.md:97-98` — "**One budget, measuring one thing: human signing latency.** It starts
  when the saga is created and is cancelled by any terminal event."
- `…/documentsigningsaga.md:50-58` — four non-terminal states: `AwaitingEnvelope`, `AwaitingSigners`,
  `AwaitingSignedAsset`, `Releasing`.
- `shared/saga-patterns.md:86` — "| `DocumentSigningSaga` | `AwaitingSigners` | `Payload.TimeoutAt < now` |
  `ExpireSigningSessionCommand(signingSessionId)` |" — **one state scanned.**
- `architecture/bounded-contexts.md:304-307` — "### `TimeoutScanner` / CloudWatch-scheduled. Registers
  `AssetIngestionTimeoutScanner` and `MediaItemLeaseExpiryScanner` (which dispatches
  `ExpireCheckoutCommand`)." — **no signing scanner.**
- `…/documentsigningsaga.md:108` — "| On expiry | dispatch `ExpireSigningSessionCommand` →
  `SigningSessionTimedOut` → compensation |" — the rule with no carrier in the host inventory.

**Checked** The saga's § Correlation Key and § Timeouts against the `SagaTimeoutScanner` status-scan table
in `saga-patterns.md`, and against `bounded-contexts.md` § `TimeoutScanner` — the host inventory entry for
the only scheduled host. Also `shared/error-catalog.md:573`, whose `EnvelopeNotFound` guidance points an
operator at "the saga runbook" for exactly these stuck cases.

**Why** Two defects with one cause. **The budget's stated reason is the case the scanner cannot see:** a
saga stuck in `AwaitingEnvelope` because the adapter never returned an envelope is not in `AwaitingSigners`
and is never scanned, so it never times out and never compensates — and covering that case is the reason
`documentsigningsaga.md:44-45` gives for creating the saga early. `AwaitingSignedAsset` has the identical
hole: all signers done, the adapter never records the document, the session hangs indefinitely. Second, the
expiry rule has no registration in the one inventory that answers "which host owns X", so nothing runs it.

**Why this is raised late** It came back from the DocumentSigning fan-out and was dropped during
reconciliation, on the reasoning that a saga the index called "a design record for a saga that does not
exist" could not carry a live gap. **Q15 answered that it is specified**, which makes both halves live.
Recording the path rather than quietly renumbering: the reconciliation judgement was wrong, and it was
wrong because it leaned on `README.md:85` — one side of the very contradiction SC-043 reports. **A finding
dropped on the strength of a document this review was auditing.**

**Ruling** Correction, no decision needed now that Q15 is settled. Change `saga-patterns.md:86` to scan
every non-terminal signing status — `AwaitingEnvelope`, `AwaitingSigners`, `AwaitingSignedAsset` — and
state whether `Releasing` is included. Add the signing scanner to the registration list at
`bounded-contexts.md:306`. **If the budget were meant to cover only the signing window**,
`documentsigningsaga.md:44-45` would be the wrong sentence instead and the saga would have to be created on
`SigningEnvelopeCreated` — but that contradicts § Correlation Key's argument that `EnvelopeId` does not
exist at start, so the scanner side is both cheaper and the one the design points at.

---

**SC-051**
**Severity** High
**Kind** Contradiction · a pointer that resolves to the opposite
**Claim** Two `<agg>.api.md` files specify idempotency as replay *rejection* with a bodyless `409`, and one
of them cites as its authority the shared section that now specifies the opposite — cached replay, with
`409` reserved for a concurrent in-flight retry and carrying a `ProblemDetails` body.

**Evidence**
- `shared/api-conventions.md:64` — "The contract conforms to `draft-ietf-httpapi-idempotency-key-header-07`"
- `shared/api-conventions.md:80-82` — "| **Retry after the original completed** | The **stored outcome of
  the original**, replayed — its status, body and error code, whether that outcome was a success or a
  failure | / | **Retry while the original is still in flight** | `409 Conflict`, with a `ProblemDetails`
  body and `errorCode: IdempotentRequestInProgress` | / | **Same key, different payload** | `422
  Unprocessable Content`, `errorCode: IdempotencyKeyReused` |"
- `contexts/Metadata/aggregates/RecordType/recordtype.api.md:16-18` — "**Idempotency:** every mutating
  endpoint accepts `Idempotency-Key: <uuid>`. The platform does replay **rejection**, not replay — a
  repeated key within the 24-hour window answers `409 Conflict` with an **empty body**, never the original
  response."
- `…/recordtype.api.md:282` — "A replayed key is refused `409 Conflict` (empty body) before any
  precondition is examined."
- `contexts/ChangeRequests/aggregates/MediaChangeRequest/mediachangerequest.api.md:13` — "**a repeat of the
  same key within the window is rejected with `409 Conflict` and an empty body — it does not return the
  original response.** This is replay *rejection*, not idempotent replay … The key is consumed **before**
  execution, so a request that then fails has still burnt it. See [§Idempotency](…api-conventions.md#idempotency)
  for the full behaviour and its known defects."
- `…/mediachangerequest.api.md:14` — "**The one exception is the idempotency `409` above**, which the
  middleware writes as a bare status code before any endpoint runs, so it carries no `ProblemDetails` body."
- The three codes the conformant contract introduces — `IdempotentRequestInProgress`,
  `IdempotencyKeyReused`, `IdempotencyKeyRequired` — appear in `api-conventions.md` and `error-catalog.md`
  and in **zero** endpoint `**Errors:**` lists anywhere in `contexts/`.

**Checked** Every file mentioning `Idempotency-Key` (sixteen), separating those that merely accept the
header from those that restate the mechanism. Only three restate it: `api-conventions.md`, and these two.
`shared/concurrency-and-consistency.md:46` was swept correctly and now reads "**replays the stored outcome
of the original request** — success or error alike — rather than refusing the retry", which is the model.
`README.md:45` routes cross-cutting route rules to `api-conventions.md`.

**Why** Every clause disagrees, not just the tone: when the key is consumed, what a completed retry
returns, what `409` means, and whether it carries a body. `mediachangerequest.api.md:13` cites the shared
section **for the behaviour that section now contradicts**, so the pointer resolves to its own refutation.
Worse, `recordtype.api.md:282-286`'s *reasoning* is built on the retired semantics — the
`Idempotency-Key`-before-`If-Match` ordering rule survives, but its worked example ("the truthful answer is
*you already sent this*") becomes "here is what happened" under cached replay.

**This is residue of MM-003 phase 5's fix, not a reopening of SB-20.** Phase 5 rewrote the contract in four
files and these two were not swept. It has a live consequence for **MM-003 phase 10 box 3**, whose
acceptance check re-reads `api-conventions.md` alone: the box passes while two endpoint contracts still
tell clients the opposite, and — because those two describe the *current* middleware exactly — anyone
running box 3's "correct the spec to the delivered behaviour" rule against them would revert phase 5. The
repo `CLAUDE.md` entry phase 5 added exists to forbid precisely that.

**Why this is numbered 051** It was reconciled as a merge of two subagent findings and then lost when its
working id was reused for SC-005. Recorded rather than renumbered — see § Method note.

**Ruling** Correction, no decision needed. Delete the mechanism from `recordtype.api.md:16-18` and
`mediachangerequest.api.md:13-14` and let both cite `api-conventions.md § Idempotency` without restating
it; the "one exception" sentence goes with it, since a conformant `409` carries `ProblemDetails`. Rewrite
`recordtype.api.md:282-286`'s worked example, keeping the ordering rule. Add the three conformant codes to
the write-route error lists. **Recommend widening MM-003 phase 10 box 3 from one file to the five that
state the mechanism.**

---

## Could not settle

Eleven claims that turn on behaviour the documents do not decide. **None is reported as a finding.** Each
is phrased so it can be answered in one look at the code, and several collapse more than one candidate.

1. **Does any SQS queue receive S3 `ObjectCreated` notifications, and which one?** `asset.scenarios.md:86`
   names `media-projector`, which two other files define as the projector queue subscribed to
   `media-domain-events` with no filter. No queue in the inventory has an S3 event source. Settles whether
   the S3-notification path is real or residue — and with it whether `POST /uploads/confirm` is
   client-called or S3-driven, which the tree specifies both ways.
2. **Is the `media-processing` queue's 1800 s visibility timeout (4 h for video) actually consumed?** The
   answer decides whether SC-016 and SC-017 are one defect or two. Needs the Lambda/CDK configuration and
   the worker's control flow.
3. **Does `media-cross-module-events` still carry `media.asset.upload-initiated` to Processing, and does
   anything act on it?** `context-overview.md:208-210` says the handler is a deliberate no-op;
   `event-store-and-messaging.md:335` says the consumption is "capability-gated". Needs the SNS filter
   policy and the handler body.
4. **Does `DynamoDbSagaRepository.SaveAsync` support a conditional write on `Version`?**
   `documentsigningsaga.md:170-171` says signing saga state is persisted with one; `saga-patterns.md:126-128`
   says there is no optimistic concurrency on saga saves and it is an unconditional `PutItem`. One shared
   repository, two answers. It matters: concurrent `SignerCompleted` callbacks are the one genuine race in
   this platform, and last-writer-wins drops a signer's progress.
5. **Is `AssetProcessingTimeoutRecoveredIntegrationEvent` consumed by anything?** Published per
   `asset.write-model.md:135-137` to "Processing (Saga), Notifications"; absent from the context overview's
   own published table.
6. **Does `Asset` expose `ConfirmUpload` or `ConfirmUploaded`?** Both spellings appear in normative
   sentences (`asset.write-model.md:191` vs `asset.api.md:720`). One is a typo; the documents do not say
   which.
7. **Is `RemoveRegistrationRefCommand` idempotent per `(mediaItemId, registrationId)`, or does each
   dispatch decrement the counter?** `Rejected` is not terminal, so a rejected-then-cancelled registration
   dispatches it twice.
8. **After erasure, does the Registration detail document carry `OwnerId: null`, omit the field, or carry a
   sentinel — and which `User` actors can then retrieve it via `/search`?** Bears on SC-021's remaining
   half.
9. **Does `OpenChangeRequestHandler` validate that `MediaItemId` names an existing item in the tenant?**
   No handler pre-condition row, and `api.md:140` lists only `400`/`401`. Cannot tell whether the absence is
   specification or omission.
10. **What is `ChangeRequest.Scope` for?** Declared on the aggregate, the command, the creation event, the
    projection and the detail response; every statement adds "today always exactly `[MediaItemId]`"; no
    invariant, guard, query or rule consults it. Whether a multi-item `scope` is accepted, validated or
    rejected is not stated.
11. **Which host exposes `/v1/signing-sessions/*` system routes and the SecuredSigning webhook, and does
    the idempotency middleware run there?** `api-conventions.md:145` scopes idempotency to "`Api` (write)
    only" with a key partitioned by tenant and owner; the webhook has neither at the edge.

---

## What is healthy

Specific, because knowing what reconciled is what makes the next audit cheaper. Each of these was
cross-checked across three or more files and came back clean.

- **The aggregate inventory.** Eleven aggregates in `architecture/domain-model.md § Aggregates`, and
  1+4+1+1+2+1+1 = 11 across the seven `context-overview.md` files. Exact, in both directions, including
  `RetentionSchedule`. Verified by the lead reviewer, not only by a subagent. **This was MM-001's group B
  and it is now the soundest part of the tree.**
- **`ChangeRequest` holds no reviewers.** Nine separate statements across five ChangeRequests files agree
  with `adrs/editing-lifecycle-and-concurrency.md:96` and with `mediaitem.write-model.md:109`, where
  `Reviewers` sits on `ReviewSession`. `error-catalog.md:483` independently confirms the reviewer codes are
  MediaItem's. **MM-001's SB-8 is fully closed** — and a tree-wide grep confirms no normative text anywhere
  calls the aggregate `MediaChangeRequest`; the residue is confined to filenames exactly as documented.
- **Metadata's seventeen-event inventory**, cross-checked five ways: the events table, the 3-cross +
  14-internal split, both projectors' "all 17", the API's three statements, and the 10+6+1 decomposition.
  3+14 = 17 and 10+7 = 17 both hold.
- **Every Metadata cap.** 100 fields, 20 groups, 500 versions, 500 retired names, 100 retained names, 200
  retained aliases, 10 aliases, 1–32 alias chars, 160/256/512 KB, 500-char note. **No number disagrees
  anywhere** across five statements of the set.
- **Processing's timeout quantities.** `ValidationBudgetMinutes` 15, `DefaultProcessingBudgetMinutes` 240,
  `WarningWindowFraction` 0.2 and the config section are identical in five files. Saga timeouts were the
  highest-risk place for a doubly-stated quantity and there is **no disagreement in that context at all** —
  which is what makes SC-048 (the signing budget) stand out rather than look like a pattern.
- **Catalog's event inventories.** MediaItem's 28 detail-projector events match the write model's domain
  events exactly; the summary projector's "25 … minus three named" checks out; MediaProfile's 18 and its
  "14 of the 18 minus four named" both reconcile arithmetically and semantically.
- **The OpenSearch mapping mirrors `MediaItemDetailReadModel` field for field** — all 32 members present,
  including the four object-typed ones. The `strict`-mapping warning is currently satisfied.
- **The nine-member `Capability` enum** agrees across `glossary.md:34`, `mediaprofile.write-model.md:177`
  and its table, `mediaprofile.api.md:416` and `mediaprofile.design-decisions.md:121`. **MM-001's SB-18 is
  closed.** (What each member *gates* is SC-010/SC-011/SC-032; the membership is settled.)
- **The archive fan-out quantities** — 500 descendant folders, the 16-permit semaphore, the 29-second API
  Gateway bound, the three-phase structure and `IsComplete` — agree across five files.
- **Registration's seven-member status machine.** Every status reachable, both terminal states with no
  outbound transition, every transition with a command behind it, both read models able to represent all
  seven.
- **The permission vocabulary resolves.** Every `Resource.Verb[.All]` token used anywhere in the tree is
  declared in `shared/api-permissions.md`, with one apparent exception (`Registration.Dispose`) that turns
  out to be a **stated absence** — `registration.write-model.md:531` says the aggregate does not define it,
  and says why. **MM-001's group A has largely landed**; what remains are the five specific residues at
  SC-008, SC-013, SC-022, SC-025 and SC-029.
- **Spec purity.** `docs_guard.py` passes five checks with zero new. No date, citation, build-status claim
  or broken link has been reintroduced — subject to the three detector blind spots in § Method note.

---

## Method note

### What was done

Inventory first, then a seven-way fan-out, then a central cross-cutting pass, then reconciliation. The
fan-out returned ~130 candidates; 49 survived. **The reconcile step was not optional** — sixteen candidates
were duplicates of each other across contexts (the same defect arriving from both sides of a boundary), and
twelve were duplicates of MM-001.

### What would be done differently

**The per-context partition was the wrong axis, and it nearly hid the finding.** Fourteen of the
twenty-six High findings have a `shared/` or `architecture/` file as the wrong side of a disagreement with
an aggregate file, and three more have one as a participant — and
each per-context subagent saw only *its* half of that disagreement, so each reported it as a local
contradiction. The pattern only appeared when the lead reviewer laid them side by side. **A future audit of
this tree should partition by layer, not by context**: one pass over `shared/` reading each file against
every file it defers to, and one pass over `architecture/` against the eleven aggregate specs. That would
have found Group A and Group F faster and with less duplication.

The corollary: the per-context passes were still worth running, because they produced the "what is healthy"
section, and a review with no clean sections is not a review of the tree.

### Trap 4 caught this review, in its own draft

**The first draft of this document said "nineteen of the twenty-one High findings".** There are
twenty-six High findings, and fourteen are strictly shared-layer. The number was written from the shape of
the evidence while drafting, and counted afterwards — which is trap 4 exactly, in the review that restates
trap 4 as guidance.

It is recorded rather than quietly fixed because the mechanism is worth knowing: **the miss survived
because the claim was directionally right.** The pattern is real, the headline is unchanged, and nothing
about the finding list moved — which is precisely why nobody would have re-counted. The fix that works is
mechanical: every count in a review should come from a script over the finished document, run last, not
from the author's impression of it. The severity split, the finding count, the contract-field check and the
id contiguity check in this review were all produced that way **after** this was caught; the layer
attribution was not, and that is the one that was wrong.

### Reconciliation lost two findings, in two different ways

Both were recovered the next day, both by accident, and the mechanisms are different enough to be worth
separating.

**SC-050 was dropped on the strength of a document this review was auditing.** The DocumentSigning
fan-out returned the signing timeout-scanner gap. Reconciliation folded it on the reasoning that a saga
`README.md:85` called "a design record for a saga that does not exist" could not carry a live gap — which
leaned on one side of the contradiction SC-043 reports, three findings later in the same document. **A
review cannot use a claim as a premise while also reporting that the claim is contested.** The guard
against it is mechanical: when a candidate is dropped because of what some file says, check whether that
file appears in the finding list.

**SC-051 was lost to id reuse during a merge.** Two subagent findings — Metadata's MD-02 and
ChangeRequests' CR-01 — were the same defect from two contexts and were merged under a working id of
"SC-005". When Group A was written, SC-005 was assigned to the `FolderMediaItemsIndex` finding and the
merged one was never given a number. It survived nowhere except the reconciliation notes, and it was found
only because the id was later quoted in conversation and did not match. **Working ids and final ids must
not share a namespace.** Assign final ids once, from the finished list, in one pass — never during the
merge.

Both are recorded rather than renumbered, because a contiguous `SC-001…SC-051` with no gaps would hide
that anything happened, and the next audit of this tree should know that reconciliation is where findings
die.

### Three checks that were misleading, and one search that was not

**Trap 3 is live — the guard passes and three of its five checks have blind spots.** A green run proved the
guard ran. It did not prove the tree was clean, and each gap was invisible from the output.

1. **`dates` matches only full `YYYY-MM-DD` or `Month YYYY`.** A **year-month** date passes. Re-running the
   check with `(?<![\d-])20\d{2}-(0[1-9]|1[0-2])(?![\d-])` over lines outside fences returns exactly one
   hit: `docs/spec/README.md:110` — "were reconciled against code in **2026-08**". Q4's ruling was "no date
   appears in a spec file, for any reason" and the acceptance was "one grep returning zero". **Suggested
   fix:** add the year-month alternative to `DATE`. One line, one baseline entry or one edit.
2. **`links` cannot see a plain-text file reference.** The pattern is `\]\(([^)\s]+)\)`, so a file named in
   a table cell or in prose is invisible. This is how SC-042 survived: `shared/system-spec.md` is cited as
   the Authority for eight glossary terms and in three spec files, and the file does not exist. **Suggested
   fix:** a check that every `` `<something>.md` `` token in a spec file resolves to a file in `docs/`.
   Cheap, and it would have caught this class at the PR.
3. **`links` also cannot see a *truncated* link, and `structure` did not catch the truncation.**
   `README.md:107-114` states "CI now fails *any* spec file ending mid-construct, unconditionally" — and
   `asset.api.md:768` reads `- [AssetManagement Business Scenarios](../.` with no closing paren, inside a
   `## Related` section sitting in the **middle** of the file, followed by an appended block with a
   duplicate `## Updated Command → Event → Projection Traceability` heading at `:973`. The link regex needs
   a `)` to match, so a truncated link is not a broken link; and the structure check looks at the file's
   *end*, and this file's end is fine. **This is the documented truncation class, present and undetected,
   in the file the index says cannot hide it.** *(Reported as part of SC-049's file; worth a detector of its
   own: an unclosed `](` on any line.)*

**And one search that worked, recorded because trap 2 says most do not.** Searching the *concept* is noise
at roughly twenty to one here. Searching a *shape with no domain reading* is not: extracting every token
appearing on a line with `**Errors:**` or an `"errorCode"` literal, and differencing it against the 152
catalogue rows, returned **eleven** candidates, of which **six** were real (SC-023) and five resolved on
reading — `ProblemDetails` and `Revising` are not codes, `ItemAlreadyAttached` and `DuplicatePendingAmendment`
*are* catalogued (my row regex was too strict), and `ReviewerSelfApproval` is a **documented** exception
that `security-scenarios.md:154` states in the file itself. That last one is the model: a code deliberately
outside the catalogue, said so where it is used, and correctly not a finding. **The same shape-based
technique found `Registration.Dispose`, which also resolved on reading** — `registration.write-model.md:531`
states the absence and explains it. Two of the three greps in this review that looked like findings were
answered by the sentence around them, which is trap 2 landing exactly as recorded.

### One judgement worth recording

**`⚠` markers were left alone, and that was right.** The Catalog subagent found
`glossary.md:32`'s `AssetIngestionSaga` caveat — "⚠ The spec names its creation trigger three different ways
and its terminal state two" — already carrying a real disagreement, and correctly declined to re-raise it.
That is the contested-rule register doing its job. Two `⚠` markers **were** reported, and only because what
they *say* is wrong rather than because they are markers: `cross-aggregate-invariants.md:178` (SC-005) and
`processingjob.write-model.md:90-95` (SC-014's Processing sibling, folded into SC-014's ruling). The test
held up: read the sentence, not the symbol.

---

## Deliberately not raised

Twelve candidates were dropped as already argued. Listed so the next session does not re-derive them.

| Candidate | Already | Status |
|---|---|---|
| Infected upload: hard-delete vs quarantine | **SB-19** (Critical), MM-003 phase 5 | Still open — note that `asset.write-model.md:246` retains "Handler **must** hard-delete the S3 object before appending this event" while `asset.scenarios.md` now specifies the quarantine move. **The fix has landed on one side only.** |
| Download guard `{Active, Archived}` vs `{…, VersionArtifact}` | **SB-23** | Still open, unchanged |
| `AssetId` server- vs caller-generated | **SB-25** | Still open; the non-id half of that disagreement (field names, status code) is SC-049 |
| `DEPRECATED` sentinel both specified and ruled out | **SB-27** | Still open; `cross-aggregate-invariants.md` rule 11 also contradicts its own merge table 30 lines later, which is new detail on the same finding |
| `202` usage needs reconciling | **SB-28** | Still open; SC-049 carries the specific list |
| Error catalogue claims exhaustiveness and is not | **SB-22** | Still open; SC-023 supplies the rows, in both directions |
| `ProcessingJobBypassed` not listed by either projector | **SB-39** | **Closed** — the read model now lists it; SC-009's traceability row is the residue |
| Reviewer authorization names `ChangeRequest.Reviewers` | **SB-8** | **Closed** — verified clean across nine statements |
| `media-used-jtis` / stateless token validation | **SB-29** | **Closed** — repo `CLAUDE.md` now agrees |
| `Media.Api` host name in three shared files | **SB-16** | **Closed** — zero occurrences remain |
| `Capability` stated as nine and enumerated nowhere | **SB-18** | **Closed** — `glossary.md:34` enumerates all nine |
| `Asset.StorageKey` specified three ways | **MM-004** SK-1…SK-6 | In flight; SC-049 and the `media-assets` PK disagreement are different fields and not folded in |

**One near-miss worth naming.** `asset.read-model.md:16`, `asset.api.md:89-90` and
`event-store-and-messaging.md:386` give the `media-assets` partition key three different shapes
(`TENANT#{TenantId}#{AssetId}` / `TENANT#{TenantId}#ASSET#{AssetId}` / `TENANT#{TenantId}#ASSETS` + SK
`{AssetId}`). It is **not** MM-004 — that review is about `StorageKey`, an S3 location. It is not reported
here either, because the three shapes are the same class of defect MM-004 is already arguing and the fix
belongs with it. **Recommend folding it into MM-004 as SK-7** rather than opening a seventh finding here.

---

## Dependencies

**MM-001 / MM-003** — no blocking relationship in either direction, but a real interaction worth stating.

**Eight findings trace directly to an MM-001 ruling landing on one side of a pair** — SC-005, SC-008,
SC-021, SC-026, SC-027, SC-031, SC-040 and SC-042 — where a rule was corrected in the aggregate file and
the summary above it was not swept. (Eight is the counted figure; an earlier draft of this section said
twenty-one, which was an impression, not a count — see § Method note.) That is not a
criticism of the plan — it is what a nine-phase rewrite across 82 files produces, and it is exactly what a
coherence audit is for. **The practical consequence: MM-003's phase 9 re-baseline should not be read as
proving the tree coherent**, because every check it re-runs is one of the five in `docs_guard.py`, and
none of them can see any of Group A.

**No plan should be written for this review until Q1 and Q2 are answered.** They are the two findings where
the tree claims a control exists and no carrier does, and both answers change the same section of
`mediaprofile.write-model.md`. Answering them late means editing that section twice.

**MM-002** — potential home for two things if Q1 lands on *No*: the `Processing` capability gate having no
source is a code question once the spec says the member does not exist.

**MM-004** — see § Deliberately not raised. Recommend SK-7.

**External blockers:** none.

**Standing constraints:** the repo `CLAUDE.md` § *Spec files state the specified system* governs every edit
this review leads to. No remediation may reintroduce a citation, a build-status claim, a rationale, an open
question or a date. **Three of the finding rulings above delete prose that argues rather than states** —
SC-001's worked example, SC-002's summary and SC-005's bullet — and the replacement in each case is a
pointer, not a shorter argument.

---

## Recommended sequencing

Rough; the plan refines it. The ordering principle is that **a summary must be fixed after the thing it
summarises, and a carrier must exist before a rule reads it.**

1. **Answer Q1 and Q2.** They change what `mediaprofile.write-model.md § Capabilities` says, and four other
   findings quote it. Nothing else should touch that section first.
2. **Answer Q8.** It is the largest hole and it is design work, not an edit — the rendition pipeline has an
   output and no input. Sizing it early keeps it from being mistaken for a correction.
3. **Sweep Group A — the shared layer.** Nine findings, all corrections, all the same shape: delete the
   restatement, keep the pointer. `saga-patterns.md` (SC-001, SC-002), `cascade-rules.md` (SC-003, SC-004),
   `cross-aggregate-invariants.md` (SC-005), `event-store-and-messaging.md` (SC-006, SC-007, SC-009),
   `api-permissions.md` (SC-008, after Q5). **This is the cheapest high-value block in the review** and it
   can be done by one person in one pass.
4. **Sweep Group F — `architecture/`.** Five findings, four of them corrections. Same shape, different
   files.
5. **Fix navigation (Group G).** `glossary.md` and `README.md`. SC-042 first — eleven pointers at a deleted
   file is the one that actively misleads a new reader on day one.
6. **The remaining rulings**, Q3–Q7 and Q9–Q15, then their corrections.
7. **Quantities (Group H)** last among the corrections. They are independent of everything else and cheap.
8. **Add the three detectors** from § Method note: year-month dates, plain-text `.md` references, unclosed `](`.
   **Do this in the same change as step 5**, not after — SC-042 and the `asset.api.md` truncation are both
   classes the current guard cannot see, and fixing the instances without the detector resets the clock,
   which is the failure MM-003 phase 0 exists to prevent.
