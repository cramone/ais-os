# MM-045 · Appendix A — Phase 0 decisions

_Taken 2026-09-16. Phase 0 edits no spec file; every answer here is quoted by a later phase._

**Clean-tree waiver.** Phase 0's exit gate asks for `git status` clean under `docs/`. Nine files were already
modified and uncommitted on branch `spec/initial-alignment` when this session opened. Chase elected to work on
top of them as-is. The gate is waived for those nine and for that reason only; **no spec file was modified by
Phase 0**, so the waiver covers pre-existing state, not this plan's output. The nine:

`docs/README.md` · `archive-fan-out.md` · `recordtype-diagrams.html` · `recordtype.api.md` ·
`recordtype.write-model.md` · `retentionschedule.design-decisions.md` · Metadata `business-scenarios.md` ·
Metadata `context-overview.md` · `docs/use-cases.md`

> Four of these are files Phases 2, 5 and 6 will edit heavily. Whoever starts Phase 1 should establish what
> those uncommitted edits are before adding to them, or the two sets become indistinguishable in review.

---

## 1. This plan's own id — **MM-044 and MM-045 stand**

Closes the § Dependencies data error in MM-044.

```
$ grep -rhoE '^id: [A-Z]+-[0-9]{3}' projects/magiq-media/{reviews,plans,_archive}
id: MM-044      reviews/spec-coherence/spec-coherence-review-2026-09-16.md:2
id: MM-045      reviews/spec-coherence/spec-coherence-review-2026-09-16-prompt.md:142
id: MM-045      plans/spec-coherence/spec-coherence-review-2026-09-16.md:2
```

Three hits, all three minted by this cycle. `requests/` does not exist in the live tree. `_archive/` exists
and is **empty**. There is no prior id anywhere.

**So the tree is genuinely empty, and both branches of the rule were live:** MM-044/MM-045 collide with
nothing and may stand, or they may be renumbered from MM-001 — which MM-044 itself calls *"a tidier outcome
and equally valid since no document yet points at them."*

**Decision (Chase, 2026-09-16): keep MM-044 and MM-045.** Not renumbered. Recorded as a decision rather than
a cleanup, per the rule that ids are never silently renumbered.

**Consequence to carry forward.** The numbers imply forty-three predecessors that never existed. That is the
same false-provenance the workstream exists to remove, now carried by the workstream's own ids. It is
tolerable because the ids resolve **in-tree** — `plans/README.md` and `reviews/README.md` both index them —
which is exactly the test everything in Appendix B fails. Archive paths are therefore
`_archive/reviews/MM-044-spec-coherence/` and `_archive/plans/MM-045-spec-coherence/`.

---

## 2. The citation register — **228 occurrences, not 121**

Full register: [Appendix B](./mm-045-appendix-b-citation-register.md). One row per occurrence, `file:line`,
disposition. **228 rows across 41 files — 120 load-bearing, 108 provenance.**

The number moved three times, and each move is worth recording because each was a different kind of error:

| Count | Where it comes from | Why it is wrong |
|---|---|---|
| **121** | MM-045 § Phase 0, and MM-044's executive summary and SI-5/SI-6 | A count of **lines**, not occurrences. Two lines carry two ids each (`retentionschedule.design-decisions.md` ~16 and ~88), and several carry three or four. |
| **138** | The plan's own Loop A regex, `MM\|DEC\|AD\|DD\|X` | Correct for those five families. But the regex is an enumeration of families that were *already known*, so it cannot find a family nobody had noticed. |
| **228** | MM-044's **standing test** — *"an id is legitimate in a spec file only if it is defined in a file inside `docs/`"* | This is the count. |

**The gap between 138 and 228 is thirteen more families**, none of which the plan's regex matches and none
of which is defined anywhere in `docs/`: `DF-` 28 · `CR-` 19 · `AM-` 14 · `D-` 12 · `Q-` 4 · `MI-` 3 ·
`DS-7`/`DS-9` 3 · `U-` 2 · `DN-`, `PERM-`, `BI-`, `M-`, `F-` 1 each.

**Scope decision (Chase, 2026-09-16): the register covers everything failing the standing test.** Three
consequences, each of which a later phase must honour:

1. **Loop A's standing pattern is replaced by the test, not widened.** Enumerating families is what let
   thirteen of them through. The sweep asks *"is this id defined inside `docs/`?"*, per token.
2. **The Phase 1 CI guard is written against the test**, not against a pattern list — *"fail any file under
   `docs/` containing an id not defined inside `docs/`"*, with an explicit allow-list for the external
   standards and domain data in Appendix B § Excluded. A guard built on an enumerated regex would pass a
   fourteenth family.
3. **`DS-` is handled per token.** `DS-1`–`DS-5` are in-tree scenario ids and stay; `DS-7` and `DS-9` go. A
   family-wide sweep destroys real content.

**Eighteen id-shaped tokens are excluded as not-citations** and listed in Appendix B so the next sweep does
not re-open them: `SHA-256`, `BCP-47`, `AIP-133`/`AIP-158`, and the `DA-`/`ACK-`/`BC-` numbers, which are
domain data inside worked examples.

> **Namespace collision, recorded here because it changes how the register is worked.** `CR-`, `AM-`, `MI-`
> and `M-` are off-repo finding ids in the spec **and** `CR-`, `MI-`, `MP-`, `RT-` are MM-044's own finding
> prefixes. Until the register is worked, `CR-16` in a spec file and `CR-16` in MM-044 are different things
> with the same name. This argues for stripping rather than renumbering MM-044 — the clash disappears when
> the spec-side ids go, and renumbering would break citations circulated on 2026-09-15 for no gain.

---

## 3. Restatements for the load-bearing citations

**Standing rule 2 applies to every one of these: never repair a citation by weakening it.** Two permitted
outcomes only — *write the authority*, or *state the rule here and delete the citation*. Softening the wording
so the missing file stops looking load-bearing is not a third option. **No restatement below contains an id.**

### 3a. The nine sites MM-044 named

**`domain-model.md` ~74** — retention relationship row. The cited decision is **overturned** (Open Question 4,
RS-1), so this is not a transcription:

> The disposal clock is a stamp written by `FolderClosed` onto each contained item. **It is stamped once.** A
> later audited move records the move; it does not re-date the clock. It is not a live read of the item's
> current folder.

**`archive-fan-out.md` ~151** — `IsComplete`:

> `IsComplete` is a claim about the **traversal**, not about the tree: it reports that every child the cascade
> enumerated was processed, not that every descendant was enumerated. ⏳ **The enumeration is known
> incomplete** — an item assigned to a folder after creation is not sourced by the cascade — so `IsComplete`
> cannot today be read as a statement about the tree. *Owner: Catalog. Condition: the first-assignment index
> gap is closed.*

**`archive-fan-out.md` ~175** — the cascade report:

> The cascade report is persisted per run and readable after the run. ⏳ **Designed, not built** — today the
> report exists for the length of one invocation and is then discarded, so a partial disposition leaves only a
> warning-level log line. *Owner: Catalog. Condition: a per-run report record with a stable identifier exists
> and the archive endpoints expose it.*

**`mediaprofile.write-model.md` ~165** — `ReviewPolicy`:

> `ReviewPolicy` is **authoritative**: the publish path reads it. Under `RequiredForPublish` an empty reviewer
> list is **refused**, not treated as an immediate publish, and `AutoSubmitOnComplete` may only move the item
> to `PendingApproval` — it may never publish. ⏳ **Not built:** the publish path does not read the policy
> today. *Owner: Catalog. Condition: the publish pre-conditions name `ReviewPolicy` and the three auto-submit
> handlers state the cap.*

**`mediaprofile.write-model.md` ~167** — the `Retention` gate:

> `Retention` is a publish gate: a profile carrying it must pin a `RetentionScheduleRef` before it may
> publish. The profile's pin is the **default**; the value each new `MediaItem` copies at creation is that
> item's own **pin of record**, which may be overridden afterwards by an attributed, reason-bearing act.
> ⏳ **Not expressible:** neither aggregate declares `RetentionScheduleRef` in its Properties table. *Owner:
> Catalog for the declarations, Metadata for the override mechanism. Condition: both Properties tables carry
> the field.*

**`collection.write-model.md` ~79** — un-archive. The citation names a phase **and** a *"below"* that does not
exist, so both go:

> There is no un-archive: no method, command, endpoint or event. ⏳ **Undecided whether one should exist.**
> *Owner: Chase. Condition: a decision on whether collection archive is reversible.* Until then `Archived` is
> terminal for `Collection` and this row states no target.

**`mediaitem.write-model.md` ~410** — the sentence *"And it explains AD-14"* goes entirely; its premise is
unreachable. Replace with the claim itself:

> The same boundary explains the capability divergence: what crosses to the item is computed from the record
> types the profile cites, not from what the profile declares. Under §6 the **declared** set is authoritative
> and the compiled union carries no authority.

**`asset.write-model.md` ~102 / ~137 / ~187** — the digest:

> ~102 — ⏳ **Designed, not built.** The capture digest of a stored original is `{ Algorithm, Value }` —
> SHA-256, lowercase hex — computed at upload confirmation and immutable for the life of the asset. It is not
> the S3 ETag. No digest exists on any aggregate, DTO or read model today. *Owner: AssetManagement. Condition:
> `Asset` declares `ContentDigest` and a projector writes it.*
>
> ~137 — Fixity cannot be reconstructed retrospectively: once objects are stored without a digest there is no
> way to establish what was filed without reading every object back. That is why the digest is specified
> before the surfaces that consume it, independently of its severity.
>
> ~187 — ⏳ **Designed, not built.** `{ Algorithm, Value }` — the algorithm travels with the value, so a future
> change is a new member rather than a reinterpretation. Not the S3 ETag.

### 3b. The remaining 111 load-bearing occurrences — six patterns

Applied mechanically. Every one produces a rule that stands without the id.

| Pattern | Looks like | Becomes |
|---|---|---|
| **Status marker** | `⏳ specified 2026-09-14 (<plan> Phase N)` | `⏳` + the substance + **Owner:** a named context + **Condition:** a state a reader can verify. **Never a bare `⏳`.** |
| **Ownership claim** | `<plan> Phase N owns / carries / specifies X` | The rule stated here, or `⏳ Not specified. Owner: <context>. Condition: <what must exist>`. |
| **Precedence claim** | `<a> is the later decision and wins`; `supersedes D3 of <plan>` | The **surviving rule only**. Superseded text is deleted, not annotated — the argument goes to the ADR in §4. |
| **Pointer-only** | `see U-1`; `see D-2`; `read DF-15 first` | Inline the claim at the citation site. If the claim cannot be recovered, say so and mark `⏳` with an owner — do not delete the pointer and leave the sentence reading as though it resolved. |
| **Defect-table row label** | `**Open — D-1.**` | The defect stated in one clause, keeping the Open/Closed column. |
| **Correction note** | `⚠ Corrected 2026-08-31, drift review X-8.5` | Keep the **date and the statement**, drop the number. *(This is most of the 108 provenance rows too.)* |

---

## 4. The fourteen recovered decisions — ratified, and each given an in-tree home

MM-044 § Recovered decisions is **ratified as written**: ten adopted, one adopted-and-extended (DEC-20), one
**overturned** (DEC-9), one adopted as **new scope** (DEC-3 → RS-9). The split below follows the repo's own
rule — *"Decisions related to changes or reasons do not belong in the spec files"* — so the **rule** lands in
the spec file that owns it and the **reason** lands in an ADR. Per Phase 10 item 1 there is **one** receiving
ADR: `docs/adrs/recovered-design-decisions.md`, new.

| # | Decision | Rule lands in | Reason lands in | Phase |
|---|---|---|---|---|
| 1 | Retention pin of record moves to `MediaItem`, copied from the profile at creation | `mediaitem.write-model.md` + `mediaprofile.write-model.md` Properties; `retentionschedule.design-decisions.md` § Placement | `recovered-design-decisions.md` | 5 rule, 6 declarations |
| 2 | `CaptureDigest`/`ContentDigest` `{ Algorithm, Value }` and the `VersionManifest` | `asset.write-model.md`; `mediaitem.write-model.md` (manifest); `glossary.md` | `recovered-design-decisions.md`; fact-correct `asset-storage-and-processing.md` | 7, manifest half 6 |
| 3 | `PurgeVersion` inside the disposition model; **legal hold first-class** | `retentionschedule.design-decisions.md` — new § Legal hold and § Purge | `recovered-design-decisions.md` | 5 — **new scope, RS-9** |
| 5 | Declaration is `MediaItemApproved`; no separate `Declare` command | `mediaitem.write-model.md`; `glossary.md` § Declaration | `recovered-design-decisions.md` | 6 |
| 9 | ~~Clock re-applied on an audited move~~ → **stamp once** | `retentionschedule.design-decisions.md` ~28 and ~33; `domain-model.md` ~74 | `recovered-design-decisions.md`, **with the overturn reasoning** | 5 — **OVERTURNED** |
| 11 | Cascade report persisted and inspectable per run | `archive-fan-out.md` | `recovered-design-decisions.md`; fact-correct `catalog-domain-invariants.md` | 6 |
| 12 | Disposition-action ladder — `Transfer`, `Review` first-class | `retentionschedule.design-decisions.md` | `recovered-design-decisions.md` | 5 |
| 16 | `IsComplete` is a claim about the traversal, not the tree | `archive-fan-out.md` ~151 | `recovered-design-decisions.md` | 6 |
| 17 | Folded into 5 — declaration point | with DEC-5 | with DEC-5 | 6 |
| 18 | Folded into 1 — pin placement | with DEC-1 | with DEC-1 | 5 |
| 19 | Folded into 12 — `Transfer` refused until an export exists | with DEC-12 | with DEC-12 | 5 |
| 20 | Correction-by-append — attributed, reason-bearing, never overwriting | `glossary.md`; `shared/cross-aggregate-invariants.md` as the platform mechanism | `recovered-design-decisions.md` | 5 mechanism, 8 Registration |
| 21 | Folded into 1 — the retention override | with DEC-1 | with DEC-1 | 5 |
| 22 | `ReviewPolicy` authoritative — and auto-submit capped | `mediaprofile.write-model.md` ~165; `mediaitem.write-model.md` publish path | `recovered-design-decisions.md`; fact-correct `editing-lifecycle-and-concurrency.md` | 6 |

**Fourteen rows. Zero decisions left homeless.** Two extensions beyond MM-044's table, both already argued
there: DEC-20 gains a **seventh** consumer, `Registration.Reference` after confirmation (RG-7, Phase 8); and
DEC-3 is **new scope**, raised as RS-9 and not merely adopted.

**Per Open Question 7, nothing above edits an ADR's decision.** `catalog-domain-invariants.md`,
`editing-lifecycle-and-concurrency.md` and `asset-storage-and-processing.md` take **additive fact
corrections** only. The one reversal — DEC-9 — is carried by the new ADR with `supersedes:`, and no existing
ADR is rewritten to match.

---

## 5. The eight unrecoverable `DEC-` numbers

`DEC-4`, `DEC-6`, `DEC-7`, `DEC-8`, `DEC-10`, `DEC-13`, `DEC-14`, `DEC-15`. Draft note for
`docs/adrs/recovered-design-decisions.md`, to land in Phase 10:

> **What is missing from this record.** The decisions collected here were recovered from the spec files that
> cited them, because each citation stated its decision inline. That method recovers only what the spec
> happened to cite. Eight further decisions were taken in the same series and cited nowhere: numbers 4, 6, 7,
> 8, 10, 13, 14 and 15. **Whatever they settled is gone.** Nothing in this repository records it, no
> reconstruction is possible, and no work item will close the gap. It is recorded here because a reader is
> entitled to know that this ADR is a partial recovery rather than a complete one — and because it is the
> measurable cost of keeping decision provenance outside the repository, which is the practice this
> workstream ends.

**This closes the honest half of SI-6.** It is a statement, not a task; nothing later depends on it and it
must not be re-opened as work.

---

## 6. The capability set that reaches a `MediaItem` — **the declared set**

Ratifies MM-044 Open Question 1. Closes **MP-2**; unblocks **R-1**, **R-7**, **R-3**.

**Decision.** `MediaProfile.Capabilities` — the set the contract author declares — is the authoritative set,
and it is what `MediaItemCreated` embeds and what every downstream gate reads.

**And the compiled union is removed, not demoted.** MM-044 allowed either *"a derived convenience with no
authority, or removed"*. Removed: a derived field sitting beside an authoritative one, computed differently
and named almost identically, is the two-sources defect that produced MP-2 in the first place.
`CompiledMetadataTemplate.Capabilities` therefore ceases to exist rather than becoming advisory.

**Why.** A capability is a governance aspect of the record class, asserted by whoever authors the contract.
Deriving it from which schema elements a profile happens to cite makes an administrative control an accident
of composition, and lets a control appear or vanish when a record type is attached or detached for unrelated
reasons — in a compliance product, on records under statutory obligation.
`metadata-schema-composition.md` already states that `Capability` is *"a platform governance aspect and never
a general composition mechanism"*; this is that rule applied consistently rather than a new one.

**Every file the change lands in:**

| File | What changes | Phase |
|---|---|---|
| `Catalog/.../mediaprofile.write-model.md` | Declared set authoritative; capability table tells the truth (MP-3) | 6 |
| `Catalog/.../mediaitem.write-model.md` | `MediaItemCreated` embeds the declared set | 6 |
| `Metadata/context-overview.md` | Compiled union removed; the *"no capability concept"* line stops contradicting Catalog | 5 |
| `spec/glossary.md` | `Capability` restated against the declared set | 1 |
| `spec/architecture/domain-model.md` | Relationship row for `MediaItem → MediaProfile → Capabilities` | 2 |
| `adrs/metadata-schema-composition.md` | Fact correction — the union is no longer what crosses | 10 |
| `adrs/catalog-domain-invariants.md` | Fact correction — activation chain | 10 |
| `Catalog/.../mediaprofile.read-model.md` | ⏳ **To confirm in the Phase 6 ripple sweep** — whether the snapshot surfaces the union | 6 |
| `Processing/.../processingjob.write-model.md` | ⏳ **To confirm in the Phase 7 ripple sweep** — the gate reads the set (R-3) | 7 |

The last two are beyond MM-044's named list and were found by grep during this phase. They are **the same
finding in another file**, not new findings, so they extend the item rather than diverting (Loop A, branch 2).

---

## 7. The `shared/` authorities — four written, three repointed, two out of scope

Ratifies Open Question 6. Closes **SI-1**. `docs/spec/shared/` contains exactly six files today:
`api-conventions.md`, `bulk-operations.md`, `concurrency-and-consistency.md`, `event-store-and-messaging.md`,
`media-types.md`, `multi-tenancy-and-auth.md`. **All nine below are missing, and are cited from 84 sites.**

### Write — cited as *the* authority for a rule that appears nowhere else (54 sites)

| File | Sites | Citation sites |
|---|---|---|
| **`error-catalog.md`** | 20 | `api-http-conventions.md`:133 · `asset.api.md`:15,16,271 · `collection.api.md`:18 · `folder.api.md`:18 · `documentsigningsession.api.md`:18,243 · `documentsigningsession.write-model.md`:278 · `recordtype.api.md`:22,1217 · `recordtype.write-model.md`:935,1888 · `processingjob.write-model.md`:104 · `registration.api.md`:20 · `registration.write-model.md`:168,575 · Registration `context-overview.md`:233 · `spec/README.md`:49,71 |
| **`cross-aggregate-invariants.md`** | 17 | `catalog-domain-invariants.md`:6,109 · `domain-model.md`:73 · `mediaitem.write-model.md`:554,665 · `archive-fan-out.md`:162 · `retentionschedule.design-decisions.md`:53,249 · `registration.write-model.md`:456,484 · Registration `context-overview.md`:98 · `glossary.md`:46,48,49,123 · `spec/README.md`:30,80 |
| **`consistency-model.md`** | 14 | `catalog-domain-invariants.md`:83 · `persistence-and-eventing.md`:75 · `asset.read-model.md`:258 · `collection.read-model.md`:185 · `folder.read-model.md`:240 · `mediaitem.read-model.md`:439 · `mediaprofile.read-model.md`:377 · `recordtype.read-model.md`:532 · `retentionschedule.design-decisions.md`:167 · Metadata `context-overview.md`:306 · `processingjob.read-model.md`:221 · `registration.read-model.md`:315 · `spec/README.md`:39,82 |
| **`cascade-rules.md`** | 3 | `catalog-domain-invariants.md`:8 · `spec/README.md`:31,81 |

### Repoint or delete — cited for cross-cutting context that exists elsewhere (18 sites)

| File | Sites | Citation sites | Disposition |
|---|---|---|---|
| **`saga-patterns.md`** | 8 | AssetManagement `business-scenarios.md`:32 · ChangeRequests `context-overview.md`:132 · DocumentSigning `context-overview.md`:123 · `documentsigningsaga.md`:174 · `assetingestionsaga.md`:238 · `glossary.md`:121 · `spec/README.md`:38,77 | **Repoint** to `assetingestionsaga.md`, the one real saga in the tree. ⚠ The repo's own `CLAUDE.md` also cites this file, for *"§ The review saga was built and then removed"* — that account exists nowhere and must be written into `assetingestionsaga.md` or `CLAUDE.md` corrected. **Outside `docs/`; flagged, not fixed here.** |
| **`operations.md`** | 7 | `asset.api.md`:673 · `collection.api.md`:23 · `folder.api.md`:35 · `archive-fan-out.md`:176 · `assetingestionsaga.md`:243 · `spec/README.md`:78,79 | **Delete** the links and inline the operational claim each makes, or mark `⏳` with an owner. No target exists to repoint to. |
| **`security-scenarios.md`** | 3 | `auth-and-security.md`:61 · Catalog `business-scenarios.md`:50 · `spec/README.md`:79 | **Delete.** The `auth-and-security.md` link carries a section anchor, `§PERM-2`, for a section of a file that does not exist — register row, family `PERM-`. |

> The plan's Phase 0 text says *"five citations to repoint"*. It is **three files across eighteen sites**.
> Recorded as a correction to the plan, not a scope change.

### Out of scope — the authorization exclusion (12 sites)

`authorization-matrix.md` (9 sites) and `magiq-auth-role-claims-requirements.md` (3). Neither written nor
repointed by this workstream. Phase 1 marks `spec/README.md` rows 14b/14c as out of scope for MM-045 and
leaves the links as they are — **and says so at the row**, so the next reader knows the gap is deliberate
rather than missed.

---

## 8. The terminal-state rule and the invariant / pre-condition test

One sentence each, applied mechanically in Phase 4 and Phase 9. These close the **E-2** and **E-9** families
at source rather than aggregate by aggregate.

### The terminal-state rule

> **A terminal status refuses every substantive command; the only writes permitted after it are metadata about
> the disposition itself.**

**Worked example — `collection.write-model.md`.** Line 61 declares *"`Archived` is terminal"*. Lines 106–109
then give four methods — `UpdateDescription`, `SetVisibility`, `SetDefaultMediaProfile`, `ApplyTags` — each
carrying `⏳ Not archived` as an unowned guard, so an archived collection can today be made `Public`. Under
the rule all four are **refused** from `Archived`, returning `CollectionAlreadyArchived`; a hypothetical
`RecordArchiveReport` — metadata about the archive — would be permitted. The four `⏳` markers become stated
pre-conditions and the register's four `Q-3` rows are closed by the same edit.

### The invariant / pre-condition test

> **A rule belongs in § Invariants only if the aggregate can evaluate it from its own state at the moment it
> decides; every rule needing an injected service, a read model or another aggregate is a handler-side
> pre-condition.**

**Worked example — `folder.write-model.md` § Invariants.** Nine rows. Three fail the test and move to
§ Handler-side Pre-conditions:

- *"No media item in the subtree may have an active registration"* → `FolderHasActiveRegistrations` on
  `ArchiveFolder`. A `Folder` holds no registrations and no subtree; this reads the `active-registrations`
  counter on an eventually-consistent projection.
- *"Subtree must not exceed 500 descendant folders"* → `FolderSubtreeTooLargeToArchive`. Requires the subtree
  index.
- *"The cascade must archive every descendant"* → `FolderArchiveIncomplete`. A claim about a cascade the
  aggregate does not run.

The remaining six — depth, circularity, same-collection, and the three archived/closed checks — are evaluable
from the folder's own state and **stay**. The move is not a downgrade: a pre-condition that reads a lagging
projection is a rule with a staleness question, and Phase 1's `consistency-model.md` is where that question
gets its answer (E-3).

---

## 9. Phase 0 exit — Loop B

| Gate | Result |
|---|---|
| Every Phase 0 item has a written answer | ✅ Nine of nine, §§1–8 above plus Appendix B |
| No spec file modified | ✅ `git status --porcelain docs/` returns the **same nine** pre-existing files; zero added by Phase 0 |
| Citation table row count equals the grep count | ✅ 228 rows = 228 occurrences under the standing test |
| Dependency gate re-run at phase boundary | ✅ `depends-on` empty · `blocked-by-external` empty · no cycles → `active` |

**Phase 0 closes.** Phase 1 does **not** start clean: its first item is blocked and the block is recorded in
the plan's session log.
