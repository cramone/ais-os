---
id: MM-045
type: plan
project: magiq-media
workstream: spec-coherence
consumes: [MM-044]
depends-on: []
blocked-by-external: []
status: active
todo-id: -
branches: []
ado: -
created: 2026-09-16
---

# Spec Coherence — Remediation Plan

Consumes [MM-044](../../reviews/spec-coherence/spec-coherence-review-2026-09-16.md). **Documents only** —
`D:\source\github\sprbrk-standard\mgq-magiq-media\docs\` (`spec\` + `adrs\`). No code is read, written or
reasoned from; authorization is out of scope.

**Dependency gate, run at authoring 2026-09-16:** `depends-on` empty, `blocked-by-external` empty, no
cycles. All clear → `status: active`. Re-run at every session start and every phase boundary.

---

## How this plan works

**Eleven phases, ordered outermost-authority first.** A spec is a graph of quotations — files quote the
glossary, aggregate specs quote `shared/`, derived surfaces quote write models, ADRs record decisions about
all of them. Fixing a Critical finding in a write model before the vocabulary it uses is settled guarantees
rework. The one exception is Phase 0: nine decisions each land in six or seven documents, so they are taken
before any file is edited. The full rationale is MM-044 § Recommended sequencing; do not re-derive it here.

**Three standing rules, in force for every item in every phase.**

1. **Loop A — the ripple sweep closes every item.** An item is not done when the edit is made; it is done
   when the blast radius has been walked. Grep the whole `docs/` tree for every term, type name, event
   name, routing key, error code, table name, scope key and file path the edit touched — **plus, without
   exception, `\b(MM-[0-9]{3}|DEC-[0-9]+|AD-[0-9]+|DD-[0-9]+|X-[0-9]+(\.[0-9]+)?)\b`** so the remediation
   cannot reintroduce what it is removing. Classify every hit: *consistent* → record the count and move on;
   *same finding, other file* → extend this item, it traces to a finding id the plan already consumes;
   *different defect* → **it does not become a checklist item**, it goes to the drift register or a new
   review, and the diversion is logged; *invalidates the phase's approach* → **stop**, do not re-plan in
   place.
2. **Never repair a citation by weakening it.** Where a rule cites an authority that does not exist, the
   two permitted outcomes are *write the authority* and *state the rule here and delete the citation*.
   Softening the wording so the missing file stops looking load-bearing is not a third option.
3. **Never write an off-repo id into a spec file.** The governing rule is the repo's own `CLAUDE.md`:
   *"Decisions related to changes or reasons do not belong in the spec files. Spec files need to remain
   pure finalized documents."* A reason worth keeping goes to an ADR or a `<agg>.design-decisions.md` —
   in-tree, and by name rather than by number.

**Loop B — the phase-exit gate** is the last item of every phase and is written out in each. **Loop C —
the re-baseline** is Phase 11.

**Acceptance checks are verifiable by reading the spec**, because this plan changes documents only. A grep
returning zero is an acceptance check; "the Billing consumer receives the event" is not.

---

## Phase 0 — Decide once ✅ **CLOSED 2026-09-16**

No spec file is edited in this phase. Every later phase quotes an answer taken here.

> **All nine items answered.** Decisions: [Appendix A](./mm-045-appendix-a-phase-0-decisions.md).
> Citation register: [Appendix B](./mm-045-appendix-b-citation-register.md) — **228 rows**, not 121.
> Loop B gate passed; see Appendix A §9.

- [x] **Settle this plan's own id.** Run `grep -rhoE '^id: [A-Z]+-[0-9]{3}' projects/magiq-media/{reviews,requests,plans,_archive}` against the live tree. Above MM-043 → MM-044/MM-045 collide, re-mint both before anything cross-references them. Genuinely empty → renumber from MM-001 is available and tidier. Chase decides; ids are never silently renumbered. Closes the § Dependencies data error. ✅ A written answer in this plan's session log naming the grep output and the decision. — **Done: tree genuinely empty (3 hits, all this cycle; `_archive/` empty, `requests/` absent). Chase: keep MM-044/MM-045.** Appendix A §1.
- [x] **Enumerate and classify all ~~121~~ 228 off-repo citations.** ~~43 `MM-` across 14 files, 78 `DEC-`/`AD-`/`X-` across 24.~~ Each is **provenance** (delete outright) or **load-bearing on a rule's status or scope** (delete, *then* restate the rule). Closes SI-5, SI-6. ✅ A table in this plan's appendix with one row per occurrence, `file:line` and disposition. The count must equal the grep count. — **Done: [Appendix B](./mm-045-appendix-b-citation-register.md), 228 rows across 41 files, 120 load-bearing / 108 provenance. The stated 121 was a *line* count; the plan's five-family regex gives 138; the standing test gives 228 across eighteen families. Scope set to the standing test (Chase).**
- [x] **Draft the restatement for every load-bearing citation.** Named in MM-044: `domain-model.md` ~74 (`DEC-9`, retention row), `archive-fan-out.md` ~151/~175 (`IsComplete`, cascade report), `mediaprofile.write-model.md` ~165/~167 (`ReviewPolicy` authoritative, `Retention` gate), `collection.write-model.md` ~79 (un-archive, and there is no "below"), `mediaitem.write-model.md` ~410 (`AD-14`), `asset.write-model.md` ~102/~137/~187 (`DEC-2`). Closes SI-5, SI-6. ✅ Each restatement written out, marked `⏳` with an owner and a condition where genuinely undecided and normative where not — and none of them containing an id. — **Done: Appendix A §3 — the nine named sites written in full, plus six mechanical patterns covering the remaining 111 load-bearing occurrences.**
- [x] **Ratify MM-044 § Recovered decisions and assign each of the fourteen an in-tree home.** Rule → the spec file that owns it. Reason → an ADR or `<agg>.design-decisions.md`. Confirm the one overturn (DEC-9) and the one new scope item (DEC-3 → RS-9). ✅ Fourteen rows, each naming a destination file. Zero decisions left homeless. — **Done: Appendix A §4. One receiving ADR, `adrs/recovered-design-decisions.md` (new). DEC-9 overturned, DEC-3 → RS-9 new scope, DEC-20 extended to a seventh consumer.**
- [x] **Record the eight unrecoverable `DEC-` numbers** (4, 6, 7, 8, 10, 13, 14, 15). Closes the honest half of SI-6. ✅ A note in the ADR that receives the recovered decisions, stating the gap exists and cannot be closed. — **Done: Appendix A §5 carries the drafted note verbatim for Phase 10. It is a statement, not a task — do not re-open it as work.**
- [x] **Decide the capability set that reaches a `MediaItem`** — declared `MediaProfile.Capabilities`, per MM-044 Q1 — and where the compiled union goes. Closes MP-2, and unblocks R-1, R-7, R-3. ✅ A written decision naming every file the change lands in: `mediaprofile.write-model.md`, `mediaitem.write-model.md`, Metadata `context-overview.md`, `glossary.md`, `domain-model.md`, two ADRs. — **Done: Appendix A §6. The declared set is authoritative and the compiled union is *removed*, not demoted. Nine landing files, two of them beyond MM-044's list (`mediaprofile.read-model.md`, `processingjob.write-model.md`) and marked to confirm in the Phase 6/7 ripple sweeps.**
- [x] **Decide the four `shared/` authorities to write and the ~~five citations~~ three files / eighteen sites to repoint.** Write: `cross-aggregate-invariants.md`, `cascade-rules.md`, `error-catalog.md`, `consistency-model.md`. Repoint or delete: `saga-patterns.md`, `operations.md`, `security-scenarios.md`. Out of scope: `authorization-matrix.md`, `magiq-auth-role-claims-requirements.md`. Closes SI-1. ✅ A written disposition per file, and a list of every citation site each one has. — **Done: Appendix A §7. All nine missing, cited from 84 sites — 54 to the four to write, 18 to the three to repoint, 12 out of scope. Every site listed by `file:line`.**
- [x] **Decide the terminal-state rule and the invariant/pre-condition test**, as one sentence each, to be applied mechanically in Phase 4 and Phase 9. Closes the E-2 and E-9 families at source. ✅ Two sentences, plus a worked example of each applied to one existing row. — **Done: Appendix A §8. Worked against `collection.write-model.md` ~61/~106–109 and `folder.write-model.md` § Invariants (3 of 9 rows move).**
- [x] **Loop B — Phase 0 exit.** ✅ Every item above has a written answer; no spec file has been modified (`git status` clean under `docs/`); the citation table's row count equals the grep count. — **Passed, with one waiver: the clean-tree check is waived for nine files already modified before this session (Chase). Phase 0 added none. Appendix A §9.**

---

## Phase 1 — Vocabulary and the authority map

Everything downstream cites these. Until the four authorities exist, no aggregate spec can be made correct.

- [ ] **Add the CI guard first.** ~~Extend~~ **Author** `.github/workflows/docs-guard.yml` to fail any file under `docs/` containing an id **not defined inside `docs/`**. Closes SI-5, SI-6 durably. ✅ The workflow fails on a branch with a deliberately reintroduced `MM-001`, and passes on a clean tree. **This lands before any stripping** — stripping without a guard just resets the clock.

  > ⚠ **Corrected 2026-09-16. `docs-guard.yml` does not exist and never has.** `.github/workflows/` contains
  > `build-and-push.yml` and nothing else — which the repo's own `CLAUDE.md` already states in its 2026-09-13
  > correction about the phantom wiki workflow. The item said *"extend"*; the work is to **author** it.
  >
  > **This is a scope exception, taken deliberately (Chase, 2026-09-16) and logged.** A CI workflow is not a
  > document, and this plan's scope line is *"Documents only — `docs/spec/` + `docs/adrs/`."* The exception is
  > granted because the plan makes the guard a precondition of Phases 2, 5, 6, 7 and 8, and the alternative —
  > stripping 228 citations with nothing preventing their return — is the outcome the item exists to avoid.
  >
  > **Write the guard against the test, not a pattern list** (Appendix A §2). An enumerated regex is what let
  > thirteen id families through the plan's own Loop A sweep. The guard needs an allow-list for the external
  > standards and domain data in Appendix B § Excluded — `SHA-256`, `BCP-47`, `AIP-1nn`, and the
  > `DA-`/`ACK-`/`BC-` reference numbers — and must treat `DS-` per token, not per family.
- [ ] **Write `shared/cross-aggregate-invariants.md`.** Every rule that spans two aggregates, and what enforces each. Closes the largest slice of SI-1. ✅ Every citation site named in Phase 0 resolves; each rule states its enforcement point and whether that point is an aggregate, a handler or a projection.
- [ ] **Write `shared/cascade-rules.md`.** What happens to related aggregates on archive, deprecate and delete. Closes SI-1, and gives CO-1/CO-2/FO-6 one home. ✅ Resolves from `spec/README.md` row 7c and `catalog-domain-invariants.md`; states the collection/folder asymmetry as the defect it is, not as two designs.
- [ ] **Write `shared/error-catalog.md`.** Every failure by code. Closes SI-1, and the dangling `errorCode` promises in `folder.api.md`, `collection.api.md` and both DocumentSigning files. ✅ Every `errorCode` string appearing anywhere in `docs/` has exactly one row; every row names the command or route that raises it.
- [ ] **Write `shared/consistency-model.md`.** Lag class, read-your-own-writes, rebuild, what replay cannot fix. Closes SI-1 and gives E-3 a home. ✅ Every read model's `Consistency` section resolves here; the file states what a cross-aggregate guard means when its projection is behind, which is the E-3 gap.
- [ ] **Repoint or delete the `saga-patterns.md`, `operations.md` and `security-scenarios.md` citations** per the Phase 0 disposition. Closes SI-1. ✅ Zero links in `docs/` to a `shared/` file that does not exist.
- [ ] **Sweep `glossary.md`.** Remove the bulk-import terms (`Batch`, `Chunk`, `Job`, `Phase`); fix `ReviewSession`'s first member (`Id`, not `ReviewSessionId`) and `EditSession`'s missing `ChangeRequestId`; strip every `DEC-` tag from `CaptureDigest`, `Declaration`, `Correction-by-append`, `VersionManifest` and restate each in its own terms. Closes MI-11 in part, SI-3, SI-5, SI-6. ✅ `grep -cE '(MM|DEC|AD|DD|X)-[0-9]' glossary.md` returns 0; the four ⏳ terms each state their own status without citing anything.
- [ ] **Sweep `spec/README.md`.** Correct row 3's inventory sentence, rows 7b/7c/12/13/15 now that the authorities exist, row 14b/14c to say those two files are out of scope for this workstream, and remove the bulk-import rows from the file tree. Closes SI-1, SI-2, SI-3. ✅ Every file named in the map exists; the aggregate sentence matches `domain-model.md` exactly.
- [ ] **Resolve SI-4's dangling internal references** — `U-1`, `D-2`, `D-11`, and the two *"see below"* / *"see the GSI note above"* in `changerequest.read-model.md`. ✅ Each either resolves to text in the same file or is removed with its claim restated inline.
- [ ] **Loop B — Phase 1 exit.** ✅ All items ticked; the phase ripple sweep over every term touched returns zero inconsistent hits; every file edited re-read in full against Phase 0's decisions; `docs-guard` green.

---

## Phase 2 — Inventory and relationship model

Settles what exists before anything describes it.

- [ ] **Remove `BulkFolderImportJob` and `BulkMediaImportJob` from `domain-model.md`** — the specified-aggregate table and the per-aggregate spec index. Closes SI-3, MM-044 Q12. ✅ Zero references in the file; the count reads nine coded plus two specified-and-unbuilt.
- [ ] **Remove them from `bulk-operations.md` and Catalog `business-scenarios.md`.** Closes SI-3. ✅ `grep -ri 'bulk.*importjob' docs/` returns 0. The inline bulk *endpoints* are untouched — verify `POST /v1/items/bulk`, `/v1/collections/bulk` and the folder bulk routes still read as before.
- [ ] **State the aggregate inventory once, in `domain-model.md`,** and make `spec/README.md` cite it rather than restate it. Closes SI-2, E-8 in part. ✅ Exactly one enumerated list of aggregates exists in `docs/`; the other two sites link to it.
- [ ] **Fix the cross-aggregate relationship table.** Remove references to fields no aggregate declares, or mark each `⏳` naming the aggregate that must declare it: `MediaItem.RetentionScheduleRef`, `MediaProfile.RetentionScheduleRef`, `MediaItem.EditSession.ChangeRequestId`. Closes MI-14, MP-7, MI-11. ✅ Every field named in the table appears in the named aggregate's Properties section, or carries `⏳` plus the owning aggregate.
- [ ] **Strip the `MM-`/`DEC-` citations in `domain-model.md`** and apply the Phase 0 restatement for ~74, including the DEC-9 overturn — the disposal clock is stamped once and an audited move records the move, not a new clock. Closes SI-5, SI-6, RS-1. ✅ `grep -cE '(MM|DEC|AD|DD|X)-[0-9]' domain-model.md` returns 0; the retention row states the stamp-once rule without citing anything.
- [ ] **Loop B — Phase 2 exit.** ✅ As Phase 1, plus: the inventory count is identical in every file that states one.

---

## Phase 3 — Published language

The external contract, fixed before the internals that feed it.

- [ ] **Create one normative routing-key table with one owner** — every `media.*` key, its source domain event, and its consumers. Closes E-1, MI-16, PJ-18, FO-19, CO-10 in part. ✅ Every routing key appearing anywhere in `docs/` has exactly one row; every per-aggregate "Published Integration Events" table cites it rather than restating consumers.
- [ ] **Correct `bounded-contexts.md`'s four `media.item.published` citations** to `media.item.approved`. Confirmed no live subscribers (MM-044 Q11), so this is a documentation fix with no migration and no notice owed. Closes E-1, MI-16. ✅ `grep -rn 'media\.item\.published' docs/` returns zero outside a dated historical note.
- [ ] **Reconcile `event-store-and-messaging.md`'s integration-event catalogue** with the new table — add `media.processingjob.bypassed`, `.created` and `media.asset.processing-timeout-recovered`. Closes PJ-18. ✅ Every event type on a documented SNS filter allowlist appears in the catalogue.
- [ ] **Record the missing Asset lifecycle events** — `AssetUnassignedFromRole` and `AssetReplacedInRole` have no integration event on either side, and `AssetDetachedFromMediaItem` and `AssetReprocessingRequested` have none either. Closes R-2 in part, AS-25. ✅ Each is either given a contract row or explicitly marked "no integration event, and here is what goes stale as a result".
- [ ] **Fix the `StorageKey` dependency in the rendition-cleanup contract** — `event-store-and-messaging.md` ~453 requires a field `AssetArchived`/`AssetDeleted` do not carry. Closes AS-15 in part. ✅ Either the events carry it in their payload tables or the contract states the cleanup cannot key on it.
- [ ] **Resolve the subscriber contradictions** — Folder integration events ("no subscriber" vs Search/Discovery consuming `media.folder.*`), Collection's four unconsumed events, `media.item.deleted`. Closes FO-19, CO-10. ✅ One statement per event, in the routing-key table, and no context overview contradicting it.
- [ ] **Loop B — Phase 3 exit.** ✅ As Phase 1, plus: every routing key in `docs/` resolves to exactly one row in the new table.

---

## Phase 4 — The invariant / pre-condition sweep

One rule, applied everywhere, before anyone argues about individual invariants. Mechanical.

- [ ] **Apply the Phase 0 test to Catalog's four write models.** Any rule in an § Invariants table naming a service, a read model or another aggregate moves to § Handler-side Pre-conditions. Closes FO-4, and the structural half of MP-6 and CO-3. ✅ No § Invariants row in any Catalog write model names an injected service or a read model.
- [ ] **Apply it to AssetManagement and Processing.** Closes AS-8, AS-11, AS-12 in part. ✅ As above. `asset.write-model.md`'s two self-contradicting invariant rows (~24 vs ~341; ~23 vs ~243) are resolved in favour of the prose, which is the later statement.
- [ ] **Apply it to Metadata, ChangeRequests, Registration and DocumentSigning.** Closes RG-12 in part, CR-3, DS-1 in part. ✅ As above.
- [ ] **Add the distinction to `spec/README.md` row 7/8 as a worked example**, so the next author does not re-blur it. ✅ The row names one moved rule and why.
- [ ] **Loop B — Phase 4 exit.** ✅ As Phase 1, plus: a full-tree grep for `§ Invariants` sections finds none containing a service name.

---

## Phase 5 — Metadata, retention and disposition

Metadata → Catalog is conformist, so the schema model is settled before what consumes it. Carries the
recovered decisions and the one piece of genuinely new scope.

- [ ] **RS-9 / DEC-3 — specify legal hold as a first-class concept.** Suspend disposal; refuse destruction while suspended; outrank both retention expiry and an erasure request; attributed, reason-bearing, auditable. Closes RS-9. ✅ A named concept with its own lifecycle, stating what it blocks and who may apply and release it — and `PurgeMediaItemVersion` refusing while a hold is in force.
- [ ] **RS-9 / DEC-3 — bring `PurgeVersion` inside the disposition model** as a named, authorised, recorded, refusable act. Closes RS-9. ✅ `retentionschedule.design-decisions.md` ~250's blocker is removed: `Destroy` can name an operation the platform performs, and the purge route's guards reference the disposition model.
- [ ] **RS-1 / DEC-9 overturned — the disposal clock is stamped once.** An audited move records the move, not a new clock. Remove the re-stamp text at ~28 and reconcile it with ~33. Closes RS-1. ✅ The file states stamp-once in one place and contradicts it nowhere.
- [ ] **RS-4 — the `Closure` trigger has one mechanism.** ~280's live lookup of the item's current folder contradicts ~28's stamp. Closes RS-4. ✅ One mechanism stated; the other removed, not softened.
- [ ] **RS-3 — the `Superseded` trigger stops resolving a record's clock from a schema's version row.** Closes RS-3. ✅ The trigger names a source that is a property of the record, or the trigger is withdrawn with a reason.
- [ ] **RS-2 — settle pin-by-value vs pin-by-reference for `RetentionScheduleRef`**, and specify the transport if by reference. Closes RS-2. ✅ One statement, and if by reference, a named integration event or reference index carrying the schedule content.
- [ ] **RS-5 / DEC-12 / DEC-19 — the disposition-action ladder.** `Transfer` and `Review` as first-class actions alongside `Destroy` and `RetainPermanently`. Closes RS-5. ✅ At least one computable disposal rule can be authored under the stated gates; "keep forever, no period" is not the only legal schedule.
- [ ] **RS-6 — the `authority` field.** Either a register with matchable identity, or the free-text field stays and the reference-query claim at ~214 is withdrawn. Closes RS-6. ✅ The file does not both keep unmatchable strings and claim the reference query works.
- [ ] **DEC-20 — specify correction-by-append as the platform mechanism**, with its consumers enumerated including the seventh, `Registration.Reference`. Closes RG-7 in part, and MM-044 Q10. ✅ One definition, in one place, cited by each consumer rather than restated.
- [ ] **RT-1 — the name-reservation guarantee.** State plainly that uniqueness rests on a one-phase row with no reclaim, and either specify promote-or-reclaim or mark every uniqueness invariant `⏳` with that dependency named. Closes RT-1, E-4. ✅ No uniqueness rule in `docs/` is stated as unconditional while its mechanism is stated as absent.
- [ ] **RT-2, RT-3, RT-4, RT-5, RT-6 — the versioning and alias rules.** One baseline for `ReplaceField`'s immutability guard; a deterministic rule for which alias qualifies a colliding field; alias edits guarded against pinned versions; "structural mutations operate on the draft only" made true or amended; `Name` uniqueness scoped honestly. ✅ Each rule stated once, with no second statement contradicting it in the same file.
- [ ] **RT-8, RT-9, RT-10, RT-11, RT-12 — version and type retirement.** Reconcile the shipped/not-shipped disagreement on `RecordTypeVersionDeprecated`; state whether retirement stops propagation to new items; give a deprecated type a forward path or say there is none; state what happens when the deprecation event is lost. ✅ Each has one answer, and where the answer is "nothing today", it is marked `⏳` with an owner.
- [ ] **RT-7, RT-13, RT-14, RT-15 — the remaining Metadata findings.** ✅ Each closed or marked `⏳` with a condition.
- [ ] **Strip every off-repo citation in the Metadata tree** and apply the Phase 0 restatements. Closes SI-5, SI-6. ✅ `grep -crE '(MM|DEC|AD|DD|X)-[0-9]' docs/spec/contexts/Metadata/` returns 0 across all files.
- [ ] **Loop B — Phase 5 exit.** ✅ As Phase 1, plus: a reader can state, from the files alone, what starts a disposal clock, what stops it, and what refuses a destruction.

---

## Phase 6 — Catalog write models

Profile → item → folder → collection: the profile defines the contract the item conforms to; folder and
collection are containers the item references.

- [ ] **MP-2 — apply the Phase 0 capability decision.** The declared set is authoritative; the compiled union is derived or removed. Closes MP-2, R-1, R-7 in part. ✅ One statement of which set reaches `MediaItemCreated`, and Metadata's "no capability concept" line no longer contradicts it.
- [ ] **MP-1 / MI-1 / DEC-22 — `ReviewPolicy` becomes authoritative and auto-submit is capped.** Publish reads the policy; `RequiredForPublish` refuses an empty reviewer list; auto-submit under it may only submit. Closes MP-1, MI-1. ✅ The publish path's pre-conditions name `ReviewPolicy`, and the three auto-submit handlers state the cap.
- [ ] **MP-3 — the capability table tells the truth.** Seven members gate nothing; either they gate something or the table says so without implying otherwise, and the seeded `Governed Media Record` profile's governance claim is reconciled. Closes MP-3, MP-14 in part. ✅ No capability is described as gating behaviour it does not gate.
- [ ] **MP-4 — `PublishedProfileReadModel` carries the fields its callers read**, or the callers are re-specified. Closes MP-4, MI-3 in part. ✅ Every field read from `GetPublishedAsync` anywhere in `docs/` appears on the record.
- [ ] **MP-5 — role rename.** Either `UpdateAssetDefinition` stops renaming, or the consequence for pinned items is specified. Closes MP-5. ✅ The rename's effect on existing items' `MediaAssetReference.RoleName` and on conformance gaps is stated.
- [ ] **MP-6, MP-7, MP-8, MP-9, MP-10 — profile lifecycle.** A never-published profile gets a disposal path; `RetentionScheduleRef` is declared; the one-sided publish compensation is stated as the defect it is; the breaking-change guard's best-effort nature is on the rule not just in prose; `AssetDefinitionDefaultSet` carries the old value or the release path is specified. ✅ Each closed or `⏳` with a condition.
- [ ] **MP-11, MP-12, MP-13, MP-15 — remaining MediaProfile findings**, including the retention non-sequitur in § Metadata field collision resolution and the two scope-key spellings. ✅ Each closed.
- [ ] **MI-3 — the checkout guard.** `profile?.CheckoutPolicy ?? PinnedCheckoutPolicy` is not a floor; state the intended semantics and make the expression match, and resolve the duplicate pinned policy. Closes MI-3. ✅ The stated intent and the stated expression agree.
- [ ] **MI-2 — folder assignment gets guards.** Status, archive and the released-reservation consequence. Closes MI-2. ✅ `AssignToFolder` and `Move` state what they refuse.
- [ ] **MI-4, MI-5 — withdraw.** From `Revising` returns to `Published` or is refused with a pointer to `DiscardRevision`; the silent lock release from `Draft` is specified or removed. Closes MI-4, MI-5. ✅ One target status per source status, in one table.
- [ ] **MI-10 / DEC-5 / DEC-17 — declaration.** `MediaItemApproved` is the declaration point; make `ReviewSessionId` nullable or give the immediate-publish path a session. Closes MI-10. ✅ The payload's optionality matches both paths that raise it.
- [ ] **MI-11, MI-12, MI-13, MI-15 — the value-object and command mismatches.** `EditSession` declares `ChangeRequestId`; `ReviewerAssignment.Withdrawn` gets a producer or goes; the discarded withdraw `Reason` is reconciled; `UnassignAssetFromRole`'s role derivation is made unambiguous. ✅ Each closed.
- [ ] **MI-6, MI-7, MI-8, MI-9 — routes, projections and the change-request gate.** The two non-atomic routes state what a partial failure leaves; the orphaned version summary row is fixed; the three-point gate's failure directions are stated with the reference-row contract they need; the unassigned item's position outside every Catalog mechanism is stated. ✅ Each closed or `⏳`.
- [ ] **FO-1, FO-2, FO-3 — the hierarchy invariants.** Depth on move, stale counters, and descendants keeping the old `CollectionId`. Closes FO-1, FO-2, FO-3, R-6 in part. ✅ Either the rules hold as stated, or each is restated as what it actually guarantees.
- [ ] **FO-5 — `ExpectedVersion`.** `concurrency-and-consistency.md` ~40 and `folder.write-model.md` ~102 cannot both stand. Closes FO-5. ✅ One statement.
- [ ] **FO-8, FO-9, FO-10, FO-11, FO-12, FO-13 — folder lifecycle and metadata.** `Close` gets an archive guard; `FolderClosed` gets a transport or the retention stamp gets another mechanism; the two metadata lifecycles are distinguished; the `400` invariant is reclassified; create-in-archived-collection is guarded; the collection-creating folder route is reconciled. ✅ Each closed or `⏳`.
- [ ] **FO-14 — one scope-key string per scope.** Closes FO-14, MP-12. ✅ Every scope key appears with one spelling across `docs/`.
- [ ] **CO-1, CO-2 / DEC-11 / DEC-16 — collection archive becomes a guarded request.** Registration guard, parent flipped after the cascade, and the cascade report persisted and inspectable. Closes CO-1, CO-2, FO-6, FO-7, R-5 in part, R-6. ✅ `cascade-rules.md` states one archive semantics for both levels; the registration gate is not bypassable by route selection.
- [ ] **CO-3, CO-4, CO-5, CO-6, CO-7, CO-8, CO-9, CO-11 — remaining Collection findings**, including the four unguarded commands, the statusless status VO, and the unreachable `DefaultMediaProfileId`. ✅ Each closed or `⏳`.
- [ ] **Strip every off-repo citation in the Catalog tree** and apply the Phase 0 restatements — including `collection.write-model.md` ~79's un-archive row, which cites a phase *and* a "below" that does not exist. Closes SI-5, SI-6. ✅ `grep -crE '(MM|DEC|AD|DD|X)-[0-9]' docs/spec/contexts/Catalog/` returns 0.
- [ ] **Loop B — Phase 6 exit.** ✅ As Phase 1, plus: a reader can state, from the files alone, what publishes a record and what stops it publishing unreviewed.

---

## Phase 7 — AssetManagement and Processing

One pipeline, fixed as one.

- [ ] **AS-1, AS-3, AS-4, AS-12 — the Asset state machine.** Trapped states get exits or the trap is stated; `Validating`'s two meanings are separated; `RecordValidationResult` gets an idempotency guard or the consequence is stated; the invariant and the stage matrix agree. ✅ Every status has a documented exit or an explicit "terminal, no exit".
- [ ] **AS-2 — the multipart completion path.** `ConfirmUpload` refusing multipart and being called by the multipart handler cannot both stand, and `CompleteMultipartUpload` gets a Methods row. ✅ One path, with a method behind it.
- [ ] **AS-8, AS-9, AS-10, AS-11 — the attach/role invariants.** The stale invariant row, the item-scoped asset that can never take a role, `MediaItemId` immutability vs detach, and the cross-context guard filed as an invariant. ✅ Each closed; Phase 4's sweep verified as applied here.
- [ ] **AS-14, AS-15, AS-16 — infection, archive and delete.** Three mutually exclusive infected-object answers reduced to one; archive's rendition retention settled; soft vs hard delete settled, including the claim that an event stream is removed. ✅ One answer each, stated once.
- [ ] **AS-17, AS-18, AS-19, AS-20 — the upload contract.** Id generation, confirmation idempotency, the pre-signed PUT terms, and standalone quota. ✅ Each stated once; `asset.api.md`, `asset.write-model.md`, `asset.scenarios.md` and the ADR agree.
- [ ] **AS-5, AS-6, AS-7, AS-13, AS-21..AS-25 — remaining Asset findings**, including the two components racing to branch the pipeline, reprocessing's missing owner and clock, and the GET that starts an S3 restore. ✅ Each closed or `⏳`.
- [ ] **AS-22 / DEC-2 — capture digest and version manifest are declared** on the aggregates and read models that must carry them. Closes AS-22. ✅ Every field the API returns appears in a read model and has a projector row, or is marked `⏳` naming what must write it.
- [ ] **PJ-1, PJ-2 — the saga's creation trigger and terminal state.** Three names to one; two terminal names to one, with `system-architecture.md`'s failure path corrected. Closes PJ-1, PJ-2. ✅ One trigger, one terminal state, identical across the saga file and the architecture diagrams.
- [ ] **PJ-3, PJ-5, PJ-6 — the saga's missing and unsafe transitions.** A failed or infected scan gets a transition; reordering gets a stated outcome; the bypass path stops writing terminal state before the dispatch that can fail. Closes PJ-3, PJ-5, PJ-6. ✅ Every event the pipeline can produce has a saga transition or an explicit "not handled, and here is the consequence".
- [ ] **PJ-4, PJ-7, PJ-8, PJ-9 — the watchdog's own gaps.** The dual-write risk on the creation leg; the validation budget shorter than the scan it budgets; the dead metrics pass; the permanently re-scanned saga. ✅ Each closed or `⏳` with the compensating control named.
- [ ] **PJ-10..PJ-19 — ProcessingJob's internal findings**, including one-row-per-asset vs many-jobs, the index that can never leave `Running`, and `Bypassed` as a status no projector writes. ✅ Each closed or `⏳`.
- [ ] **R-2, R-3 — the Asset↔MediaItem and Asset↔Processing edges.** Two mechanisms for one role binding reduced to one; the three asset-status bars reconciled; `VersionArtifact`'s only exit stated; capability lag's silent downgrade stated. ✅ Each edge has one mechanism and one owner.
- [ ] **Strip every off-repo citation in both trees.** ✅ `grep -crE '(MM|DEC|AD|DD|X)-[0-9]' docs/spec/contexts/{AssetManagement,Processing}/` returns 0.
- [ ] **Loop B — Phase 7 exit.** ✅ As Phase 1, plus: a reader can trace an upload from initiation to `Active` and to every failure terminal, from the files alone.

---

## Phase 8 — ChangeRequests, Registration, DocumentSigning

All three are driven by Catalog and cannot be made consistent until Catalog is.

- [ ] **CR-1, CR-2 — `Kind`.** Stored, derived or endpoint-derived — one answer, with a carrier on the creation event and the read models if stored. Closes CR-1, CR-2, R-4 in part. ✅ One mechanism, and both API responses render from it.
- [ ] **CR-3, CR-4 — comment edit/delete gating and the freeze claim.** Four statements reduced to one; "a governance record freezes when it closes" either implemented or withdrawn. ✅ One answer, and the API's error lists match it.
- [ ] **CR-5, CR-6, CR-7 — `Create` invariants, `Scope`, and who may close.** ✅ Each closed; `Scope` either constrained to `[MediaItemId]` by rule or the gate's `Scope` check restated.
- [ ] **CR-8, CR-9, CR-9b, CR-10 — the close paths.** The unrecoverable lost close; rejected/withdrawn recorded as `Resolved`; only approval closing a governance request; the inert withdrawn producer. Closes CR-8, CR-9, CR-9b, CR-10, R-4. ✅ All three review outcomes have a stated close for both request kinds, and the status recorded matches what happened.
- [ ] **CR-11..CR-15 — remaining ChangeRequests findings**, including the two disagreeing property tables and the twice-specified table. ✅ Each closed.
- [ ] **RG-1, RG-5, RG-6, RG-7, RG-8 — Registration lifecycle holes.** Cancel from a dispatched state; discharge orphaning pending amendments; post-dispatch mutability; the uncorrectable `Reference` (via DEC-20's mechanism); the amendment with no timeout. ✅ Each closed or `⏳`; no status has an entry and no exit.
- [ ] **RG-2, RG-3, RG-4 — the amendment path.** The false 409 contract; the bypassed `ItemAlreadyAttached`; eligibility checked at request and enforced at approval. ✅ Each closed.
- [ ] **RG-9, RG-10, RG-15 — the `Published` guard and duplicate registrations.** ✅ The guard is stated as a creation-time pre-condition, not an always-true rule, with what happens afterwards.
- [ ] **RG-11..RG-14, RG-16 — remaining Registration findings**, including the undeclared `Amendment` type and the four spellings of one concept. ✅ Each closed.
- [ ] **R-5 — the registration counter.** Double decrement, the two unbuilt repair events, seeding, the missing idempotency fence, invisible document items, the ungated registered item. Closes R-5. ✅ `cross-aggregate-invariants.md` states the counter's rule, its writers, its seeding requirement and every path that can drift it.
- [ ] **DS-1, DS-2 — the three layers claiming one enum, and signer status's two owners.** ✅ One owner each, stated once.
- [ ] **DS-3..DS-14 — the signing design.** No envelope void path; unresumable two-step compensation; archive deadlocking compensation; the mutual-exclusion window; the shared queue; the tenant-lookup exception; the force-release contradiction. ✅ Each closed or `⏳`; the design would be correct if built exactly as written.
- [ ] **DS-15..DS-18, R-8 — remaining signing findings and the MediaItem edge.** ✅ Each closed.
- [ ] **Strip every off-repo citation in all three trees.** ✅ `grep -crE '(MM|DEC|AD|DD|X)-[0-9]' docs/spec/contexts/{ChangeRequests,Registration,DocumentSigning}/` returns 0.
- [ ] **Loop B — Phase 8 exit.** ✅ As Phase 1, plus: every cross-context edge in `cross-aggregate-invariants.md` names one mechanism and one owner.

---

## Phase 9 — Derived surfaces

Every `api`, `read-model` and `scenarios` file, reconciled to the now-fixed write models. Deliberately last
of the content phases: derived documents quote normative ones, and phases 3, 4 and 5 all change shared
rules.

- [ ] **Asset** — `asset.api.md`, `.read-model.md`, `.scenarios.md`. ✅ Every route, status code, field and error resolves to the write model or the error catalog.
- [ ] **ProcessingJob** — same three. ✅ As above.
- [ ] **Collection** — same three. ✅ As above.
- [ ] **Folder** — same three, including FO-15, FO-16, FO-17, FO-18. ✅ As above, plus every field the API returns has a projector that writes it.
- [ ] **MediaItem** — same three, including MI-17..MI-22. ✅ As above, plus the projector count matches the projector list.
- [ ] **MediaProfile** — `.api.md`, `.read-model.md`, `.scenarios.md`, `.defaults.md`. ✅ As above.
- [ ] **RecordType** — same three. ✅ As above.
- [ ] **Registration** — same three. ✅ As above.
- [ ] **ChangeRequest** — same three. ✅ As above.
- [ ] **DocumentSigningSession** — same three plus the saga file. ✅ As above.
- [ ] **The cross-cutting shared files** — `api-conventions.md`, `bulk-operations.md`, `media-types.md`. Closes E-6 (one idempotency contract), MI-21, and the pagination, sort-order and status-code divergences. ✅ One statement per convention; no endpoint contradicts it.
- [ ] **E-8 and E-10 sweep — counts and naming.** Recount every "N of the following"; one timestamp convention; one id-field convention per model family. ✅ Every count in `docs/` matches the list it describes.
- [ ] **Loop B — Phase 9 exit.** ✅ As Phase 1, plus: every derived file's claims resolve to a normative file, and no normative file was changed by this phase.

---

## Phase 10 — ADR reconciliation

Last, because an ADR records a decision about the spec and the spec is not settled until Phase 9 closes.
**Additive corrections of fact are edits; a reversed decision gets a new ADR carrying `supersedes:`, and the
old one stays with a pointer forward** (MM-044 Q7).

- [ ] **Receive the recovered decisions.** One ADR carrying the fourteen recovered `DEC-` decisions in their own words, the DEC-9 overturn with this review's reasoning, and the note that eight were never cited and are gone. ✅ Every recovered decision has an in-tree home; no ADR cites an off-repo id.
- [ ] **`catalog-domain-invariants.md`** — the four false rule claims, the counter argument, and the missing-file links. ✅ Reconciled or superseded.
- [ ] **`metadata-schema-composition.md`** — the `ICapabilityRegistry` mechanism Metadata says does not exist, and the ruling-3 amendment. ✅ Reconciled or superseded.
- [ ] **`editing-lifecycle-and-concurrency.md`** — the change-request gate and the closer's tolerance, reconciled with ChangeRequests' opposite verdict. ✅ One verdict.
- [ ] **`asset-storage-and-processing.md`** — the pre-signed URL terms, the confirm path, reprocessing's timeout ownership. ✅ Reconciled.
- [ ] **`persistence-and-eventing.md`** — routing keys, against Phase 3's table. ✅ Reconciled.
- [ ] **`api-http-conventions.md`, `deployment-and-resource-naming.md`, `ownership-and-authorization.md`** — fact corrections only; `ownership-and-authorization.md` is otherwise out of scope. ✅ No factual claim contradicts the spec.
- [ ] **`adrs/README.md`** — the index, and its `MM-004` citation. ✅ Every ADR listed, no off-repo ids.
- [ ] **Loop B — Phase 10 exit.** ✅ As Phase 1, plus: no ADR asserts a mechanism the spec says does not exist.

---

## Phase 11 — Re-baseline (Loop C)

The acceptance test for the whole plan.

- [ ] **Run the re-baseline.** Fresh session, no context from the remediation, started from [MM-044's prompt file](../../reviews/spec-coherence/spec-coherence-review-2026-09-16-prompt.md) § Re-baseline. Same scope, same method. ✅ A finding register in the same shape as MM-044's.
- [ ] **Diff against MM-044.** ✅ A written diff: closed, still open, new.
- [ ] **Act on the diff.** Zero `High`+ tracing to MM-044's scope → the plan may close. Any `High`+ in scope → the plan re-opens at the owning phase and Loop C runs again. Any `Critical`/`High` outside scope → a **new review**, never a re-open. ✅ One of those three, written down and acted on.
- [ ] **Bound check.** Three iterations maximum. Failing to converge in three means the spec's *structure* rather than its content is the problem — say so and stop; that conclusion is the deliverable, not a failure to finish. ✅ Either convergence, or the structural finding written up as a new review.

---

## Closing out

- This plan moves to `status: done` **only after Chase agrees the work is implemented and complete.** The
  phases finishing is necessary, not sufficient.
- The close-out card comment records **every branch it was committed to**; each is appended to `branches:`
  in front-matter as it is cut.
- MM-044 is already `done` / `outcome: plan`. When this plan closes, **both sides archive in the same
  session** — review to `_archive/reviews/MM-044-spec-coherence/`, plan to
  `_archive/plans/MM-045-spec-coherence/`, whole folders moved, README rows moved to the archive sections
  rather than deleted, and the emptied workstream folders removed. Archiving is proposed, never automatic.

---

## Session log

Diversions, blockers and decisions taken during execution. A new finding **never** becomes a checklist item
here — it goes to the drift register or a new review, and the diversion is recorded in this section.

| Date | Phase | What happened |
|---|---|---|
| 2026-09-16 | — | Plan authored from MM-044. Dependency gate clear: no `depends-on`, no external blockers, no cycles → `active`. **Outstanding:** no card comments were written for MM-044 or MM-045 — the workspace shell was unavailable for the whole authoring session, so `cycle.comment(...)` could not be run. First session with a working shell should post the pick-up comment for both. |
| 2026-09-16 | 0 | **Phase 0 executed and closed.** Dependency gate re-run at session start: clear. All nine items answered — [Appendix A](./mm-045-appendix-a-phase-0-decisions.md), [Appendix B](./mm-045-appendix-b-citation-register.md). No spec file edited. |
| 2026-09-16 | 0 | **Decision — plan id.** Grep across `reviews/`, `plans/`, `_archive/` returned three hits, all minted by this cycle; `_archive/` empty, `requests/` does not exist. Tree genuinely empty, so both branches of the rule were live. **Chase: keep MM-044/MM-045, not renumbered.** Archive paths fixed accordingly. |
| 2026-09-16 | 0 | **Diversion — the citation count is wrong three ways, and the plan's instrument is the reason.** Stated 121 is a *line* count. The plan's own Loop A regex (`MM\|DEC\|AD\|DD\|X`) gives **138 occurrences**. MM-044's **standing test** — *an id is legitimate only if defined inside `docs/`* — gives **228 across 41 files**, in eighteen families. Thirteen families the regex cannot match: `DF-` 28, `CR-` 19, `AM-` 14, `D-` 12, `Q-` 4, `MI-` 3, `DS-7`/`DS-9` 3, `U-` 2, and five singletons. **Chase: register covers everything failing the standing test.** Consequence for later phases: **Loop A's enumerated pattern is replaced by the test**, and the Phase 1 guard is built on the test, not a family list. |
| 2026-09-16 | 0 | **Diversion — namespace collision, recorded not actioned.** `CR-`, `AM-`, `MI-`, `M-` are off-repo finding ids in the spec *and* `CR-`, `MI-`, `MP-`, `RT-` are MM-044's own finding prefixes. `CR-16` in a spec file and `CR-16` in MM-044 are currently different things with the same name. Argues for stripping rather than renumbering MM-044 (whose ids were circulated 2026-09-15). No re-open; the clash dies when the register is worked. |
| 2026-09-16 | 0 | **Diversion — SI-4 is understated.** MM-044 files `U-1`, `D-2`, `D-11` as *"dangling internal references"*, `Low`. Nothing in `docs/` defines them, so they are the same `Critical` defect as SI-5/SI-6. **Chase: leave SI-4 as written and handle in Phase 1** — the occurrences resolve either way. Recorded so the severity gap is not mistaken for agreement. |
| 2026-09-16 | 0 | **Scope exception granted — the CI guard.** `.github/workflows/docs-guard.yml` does not exist; Phase 1 item 1 said *"extend"*. Authoring a CI workflow falls outside *"documents only"*. **Chase: author it, logged as a scope exception.** Reason: the plan makes the guard a precondition of the five stripping phases. This is the only artifact MM-045 will produce outside `docs/`. |
| 2026-09-16 | 0 | **Waiver — clean-tree gate.** Nine files were modified and uncommitted under `docs/` before this session, on branch `spec/initial-alignment` (which matches no GitFlow pattern in the repo `CLAUDE.md`, and `branches:` in front-matter is still empty). **Chase: work on top as-is.** Phase 0 added no modifications. Four of the nine are files Phases 2, 5 and 6 will edit heavily — **establish what those edits are before adding to them.** |
| 2026-09-16 | 0 | **Blocker, unresolved — the cycle skills are not installed.** The repo `CLAUDE.md` § Review → Plan cycle names `[[review-cycle]]` and `[[workstream-query]]` as this project's adoption marker. Neither is available in this session, so the outstanding `cycle.comment(...)` for MM-044/MM-045 **still cannot be posted** despite the shell now working. Carried forward. |
