---
id: MM-042
type: review
project: magiq-media
workstream: aggregate-design
raised-by: []
status: done
outcome: plan
todo-id: -
created: 2026-09-14
---

# Aggregate design review — the model as specified

> **Spec only. No code was read.** Every claim cites the spec file that makes it, and where two spec files
> disagree, both are cited. Sources are `docs/spec/` and `docs/adrs/` in `mgq-magiq-media`; `src/`, `tests/`,
> the CDK repo and the platform SDK were not opened.
>
> **This review says nothing about what is built.** A finding here is a defect in the design or its
> documentation — **not** a statement that the running system misbehaves. Where the spec itself flags
> something as unbuilt, that is quoted as a fact about the spec, not verified against source. It cannot tell
> you whether a finding is already handled in code, and it cannot catch a defect the spec is silent about
> but the code gets right. That is the accepted trade for a clean design check.
>
> **Authentication and authorization are out of scope by instruction.** Where a finding touches a guard, it
> is about the *reach of a design mechanism* (what an edit lock covers), never about who may call what.

_Prefix `AD-` for the model as specified, `DD-` for the decided design. **Ten passes complete.** 35 + 6
findings · five roots, all remedied · **24 decisions** · Q-1 … Q-4 answered · **AD-21 recorded as the
residue**._

> ## ✅ `findings-agreed` — Chase, 2026-09-14
>
> **The findings are agreed and a plan may now be opened from this review.** Every finding has a decision or
> an accepted remedy; the coherence loop is at a fixed point across six rounds; and the **decided** design
> was itself reviewed in Pass 10 and its findings decided.
>
> **The plan starts at unit 0** — correct the retention text in the spec, per DEC-18's accepted risk. Until
> that lands the spec carries two incompatible retention placements, which is the one open exposure this
> review knowingly leaves.
>
> ⚠ **Two bookkeeping items still need a shell**, unchanged: the id `MM-042` was assigned by hand and should
> be verified free before this is relied on, and **no Control Tower card comment has been written for this
> review or for MM-041**.

---

## The verdict

**The per-aggregate models are good, and several are better than good.** `RecordType` is the best-designed
aggregate in the tree and this review raises nothing against it. `AssetIngestionSaga` is the strongest piece
of process design. The uniqueness registry, the two-tier reservation, the counter-over-projection argument
and the holder-set-not-counter decision are all correct and correctly reasoned.

**What is wrong is at three joins, and one thing is simply missing.**

**1 · The model has a record *class* and a record *aggregation*, and nothing connects them.** Governance —
classification, retention, security classification — attaches entirely to `MediaProfile`. The events that
should drive governance come from `Folder`: the `Closure` retention trigger reads `ClosedDate` on the item's
*current folder*. So the disposal rule and the disposal clock come from two unrelated hierarchies, moving an
item between files silently re-dates a statutory clock, and **the aggregation itself is derived** — a folder
does not know its children, so every operation over a file runs off a projection with no repair path.
*(AD-8, AD-9, AD-10, AD-13, AD-26.)*

**2 · Every rule is owned; no rule owns the set.** Five mechanisms carry cross-aggregate relationships and
nothing states when to use which, so one question gets two answers — *is this profile usable* is answered
from the aggregate by one rule and from a projection by another, and *"the difference is invisible"*. The
same shape recurs wherever two individually-correct rules compose: idempotency-keeps-first-cause silently
determines the failure taxonomy; cascade-nothing plus cannot-delete-while-assigned produces a state neither
rule intended and neither can exit. Operationally it is the same gap — four failure conventions, three of
which ack and continue, and no owner of what that adds up to. *(AD-7, AD-11, AD-12, AD-14, AD-16, AD-17,
AD-19, AD-20, AD-25, AD-28, AD-32, AD-33, AD-35.)*

**3 · The model reasons in instants; the domain reasons in durations.** Guards check eligibility once and
never again — which is what DF-3 turned out to be, and the same shape is unexamined in two further rules.
`PendingConfirmation` has no upper bound and nothing scans, so a filing to an unresponsive authority holds a
folder's archive guard open until a person notices. Underneath, replicated facts carry **no freshness
contract at all**: `ProjectedVersion` is *"a local monotonic watermark, with no relationship to the source
aggregate's event-store version"*, so no guard can ever say *this evidence is too old to act on*. Retention,
hold, custody, obligation and closure are all durations. *(AD-21, AD-22, AD-27, AD-34.)*

**4 · `MediaItem` carries several things and the lock protects one of them.** It runs three state machines
and the spec says one *"is coupled to nothing"*; a metadata write can take an item `Draft → Published`. The
edit lock covers content and not lifecycle — *"content edits are guarded and lifecycle transitions are
not"* — so a checked-out record can be published, withdrawn or archived out from under its holder. And a
multi-member session admits 25 collaborators and orders none of them, which the spec diagnoses in a
parenthesis and then ships. *(AD-1 … AD-6, AD-18, AD-23.)*

**5 · And the records-specific capabilities are absent.** Not built wrong — **not present**. There is no
fixity value anywhere, so the platform cannot answer *"is this still the bytes that were filed?"*. Legal
hold is, in the spec's own words, *"inexpressible"*. The disposal **action** vocabulary is never enumerated
while the trigger vocabulary is specified to the member. And the one operation that destroys record content
sits wholly outside the disposition model, allowed even when archived, answering to nothing.
*(AD-15, AD-29, AD-30, AD-31.)*

> **The fairest one-line summary:** the platform is strong at everything that happens to a record **while it
> is in use**, and has not yet modelled what happens to a record **because it is a record**. That is a
> coherent place to be partway through a build — the first half is harder to retrofit and was built first.
> **The risk is that the vocabulary already promises the second half.** The spec says it best, about
> itself: *"A capability name is not evidence a control exists."*

**Top five as first written, in order:** **AD-29** (no fixity) · **AD-15** (hold inexpressible) · **AD-31**
(disposition has no terminus) · **AD-26** (containment is derived) · **AD-3** (the lock does not cover
custody).

**The highest-leverage single change is none of them: AD-28.** Generalising the completeness rule from
reference projections to the other four relationship mechanisms is a documentation act whose own argument is
already written — and it is the only remedy in this review that makes the *next* defect visible rather than
closing one that exists.

> ### ⚠ Superseded by the decisions — read § Coherence re-run before acting on the order above
>
> **Fifteen decisions were taken with Chase on 2026-09-14** (§ Decisions on findings), and the re-run
> reordered this list. Four of the five roots now have remedies; the verdict's *diagnosis* stands unchanged.
>
> **AD-26 rose to first and was then closed.** It rose because two decisions came to rest on it — DEC-1's
> closure stamp and DEC-3's file-level hold both assume you can trust what is in a folder. **DEC-16 closed
> it**, after the review's own characterisation proved wrong: the containment indexes are *same-module*
> projections of authoritative state, not unrebuildable cross-context ones, and `media-item` already
> replays. `MediaItem.FolderId` was authoritative all along; only the inverse view was derived, and it was
> derived badly rather than necessarily.
>
> **All five roots now have remedies.** **AD-21 is the residue** — guards that check eligibility once where
> the domain needs a standing constraint. Four decisions narrow it; none removes it, because it is a concept
> to add rather than a defect to fix.
>
> **DEC-15 (AD-28) goes first overall**, with **DEC-16 alongside it** — the same rule applied to one index.
> **DEC-10 is the first structural unit**, ahead of the hold and the clock.

---

## Pass 0 — the map

**No findings in this section by design.** This is the inventory the rest of the review argues against.

### The aggregates

| Context | Aggregate | Terminal states | Built? |
|---|---|---|---|
| `Catalog` | `Collection` | `Archived` | ✅ |
| `Catalog` | `Folder` | `Archived` (+ `ClosedAt`, an orthogonal flag, not a status) | ✅ |
| `Catalog` | `MediaItem` | `Archived` → deleted | ✅ |
| `Catalog` | `MediaProfile` | `Deprecated` | ✅ |
| `AssetManagement` | `Asset` | `ContainsVirus`, `MultipartAborted`, `Deleted` | ✅ |
| `Processing` | `ProcessingJob` | `Succeeded`, `Bypassed` | ✅ |
| `Metadata` | `RecordType` | `Deprecated`, `Abandoned` | ✅ |
| `Metadata` | `RetentionSchedule` | inherits RecordType's | ⚠ **design only — "no aggregate, no table, no route"** (`retentionschedule.design-decisions.md:9`) |
| `Registration` | `Registration` | `Cancelled`, `Discharged` | ✅ (`Discharge` specified 2026-09-14, not built) |
| `ChangeRequests` | `ChangeRequest` | `Resolved`, `Abandoned` | ✅ |
| `DocumentSigning` | `DocumentSigningSession` | `Voided`, `Cancelled`, `TimedOut`, `SignedAssetRecorded` | ⚠ **"This context is a skeleton"** — no aggregate root (`DocumentSigning/context-overview.md:20`) |

### How relationships are carried

Five mechanisms, in descending strength. **Which one a relationship uses is the single most load-bearing
design choice in this model**, and the map below is what Pass 6 will argue against.

| Mechanism | Instances |
|---|---|
| **Other aggregate loaded** (strongest) | Rule 1 `CreateMediaItem` → `MediaProfile`; rule 9 `Asset` mirrored state; rule 11a profile version pinning |
| **Handler query service over a read model** | Rules 2, 3 via `MediaProfileIndex` |
| **Write-side reference index** (13 of them) | Rules 4, 5, 6, 7, 8, 10, 11, 12 — see below |
| **Counter** | Rules 13 (`active-registrations`), 14 (`depth`). *"Only two counters exist in the entire system"* (`cross-aggregate-invariants.md:161`) |
| **Name-reservation registry** | Rule 15 and six other uniqueness scopes |
| **Copy by value into an immutable snapshot** | `MediaProfile` → `MediaItem.SnapshotFields`; `RecordType` version → compiled template. *"Every edge downstream is a copy by value"* |

**Thirteen write-side reference indexes. Seven cross a context boundary and none of the seven can be
rebuilt** (`consistency-model.md:170-185`); the same-module six are *"replayable in principle but not in
practice"* because the CLI does not clear them (`:187-189`). **Neither counter can be rebuilt at all** — both
are written by command handlers rather than events, so no replay reproduces them (`:191-194`).

### Sagas and process managers

| | State | Correlation | Timeout | Resume |
|---|---|---|---|---|
| `AssetIngestionSaga` | ✅ `media-sagas` | `AssetId` | ✅ two-phase, 15 min → 4 h | ✅ via timeout-recovered event |
| `DocumentSigningSaga` | ⚠ design only | `SigningSessionId` | designed, 72 h | designed |
| `MediaItemReviewSaga` | ⛔ **deliberately removed 2026-06-02, not coming back** | — | — | — |
| `CollectionArchiveFanOutWorker`, `FolderArchiveFanOutWorker` | ❌ **none** | ❌ | ❌ | ❌ |

> *"**Two process managers are sagas without the name**, and both are **live in production**… Neither has
> state, a correlation key, a resume path, a timeout, a status surface or a test"* —
> `saga-patterns.md:142-147`.

### The stated consistency positions

| Question | The spec's answer |
|---|---|
| Read-your-own-writes | **No, on any production path** (`consistency-model.md:19`) |
| Staleness bound | **Unbounded and unmeasured** — no SLO, alarm, metric or dashboard (`:18, 64-76`) |
| Environment divergence | Projections **synchronous** in dev/qa/staging; async only in prod, so *"a staleness bug cannot be reproduced outside production"* (`:114-130`) |
| Idempotency | Event-store conditional write · `ProjectedVersion` guards · saga status checks. **No dedup key**; `IdempotencyKey` is not propagated through SNS/SQS (`concurrency-and-consistency.md:61-77`) |
| Outbox | **None.** Publication is inline after commit; a failed publish leaves the read model *"wrong **permanently**"* (`consistency-model.md:47-61`) |
| Replay | CLI covers **6 of 10** aggregates; table rotation has a **dev-only runbook**, so *"the rebuild path has never been exercised where it would actually be needed"* (`:138-162`) |

### Cascade behaviour

| Trigger | Cascades | Sync? |
|---|---|---|
| Folder archived | ✅ children + items, root last | **synchronous, inline** |
| Collection archived | ✅ everything, collection archived **first** | **asynchronous** |
| MediaItem archived | ❌ assets untouched | — |
| MediaItem deleted (hard) | ❌ **assets, registrations and change requests all untouched** | — |
| MediaProfile / RecordType deprecated | ❌ existing items and pins untouched — *"load-bearing"* | — |

**Explicitly undetermined** (`cascade-rules.md:135-144`): a ChangeRequest on item archive or delete —
*"Nothing. It stays open"*; an in-flight `ProcessingJob` on asset delete — *"Not determined"*; un-archive —
*"No un-archive command exists for any aggregate"*; counter reconciliation — *"No"*.

---

## Pass 1 — `MediaItem`

**The centre of the model, and the largest aggregate by a wide margin.** Sources:
`docs/spec/contexts/Catalog/aggregates/MediaItem/mediaitem.{write-model,read-model,api,scenarios}.md` and
`docs/spec/contexts/Catalog/context-overview.md`.

---

### AD-1 · High — Three state machines share one aggregate, and the spec says one of them is coupled to nothing

**What the spec says.** `mediaitem.write-model.md:218-226` states it outright:

> `MediaItem` runs three state machines at once — **A** Status · **B** Edit session · **C** Folder
> assignment. **"A and B are tightly coupled and sound; C is coupled to nothing."**

The folder-assignment guards are quoted in full (`:278-283`). `AssignToFolder` is
`if (FolderId.HasValue) → refuse`. `Move` is `if (!IsAssignedToFolder()) → refuse; if (FolderId ==
newFolderId) → refuse`. The file adds: **"No status check, no archive check, no checkout check."**

**What follows.** An aggregate is a consistency boundary — the things inside it that must be true together.
A sub-machine that is *coupled to nothing* is, by the spec's own description, not participating in that
boundary. It is a second aggregate sharing a transaction and an id.

Two concrete consequences the spec itself records:

- **C can drive A**, in the one direction that should be impossible. Auto-submit fires from **three**
  handlers, and `:290-294` states the outcome: *"**A metadata write can take an item `Draft → Published`.**"*
  A filing operation and a content edit both reach into the publication machine.
- **C ignores A entirely.** An item can be moved *while `Archived`* — and `:283-288` notes the move then runs
  against a title reservation that archive already released.

**Why this matters in a records context.** Classification (which file a record sits in) and declaration
(whether it is a fixed record) are *separate acts with separate authority* in every recordkeeping standard.
Fusing them into one aggregate while leaving them mutually blind produces exactly the failure the split is
meant to prevent: filing a record can publish it, and publishing it cannot stop it being refiled.

**This is the root the rest of Pass 1 hangs off**, and AD-2, AD-3 and AD-5 are all instances of it.

---

### AD-2 · High — `Archived` is described as terminal and accepts at least four mutating commands

**What the spec says.** `Archived` is *"Terminal soft-archive"* (`mediaitem.write-model.md:61`). Then:

| Command | Behaviour when archived | Cite |
|---|---|---|
| `PurgeVersion` | *"**Allowed even when archived**"* | `:358` |
| `AddRegistrationRef` / `RemoveRegistrationRef` | *"**No status guard** — removal is permitted regardless of status or archive state"* | `:357` |
| `Move` | permitted; *"inconsistent as well as odd, because `ArchiveMediaItemHandler` releases the title reservation on archive, so a subsequent move calls `MoveAsync` against a reservation row that no longer exists"* | `:283-288` |
| `Delete` | idempotent; *"a repeat delete returns success without emitting, **before** the archived check"* | `:355` |

**What follows.** "Terminal" is being used to mean "no status transition out", not "no further change" — and
those are different claims. The spec uses the stronger-sounding word while documenting the weaker property,
which is how a reader ends up believing an archived record is fixed.

`PurgeVersion` is the sharp one: it is **destructive**, it is permitted on an archived item, and
`cascade-rules.md:135-144` records that hard-deleting an item cascades to nothing — *"Assets, Registrations
and ChangeRequests all untouched"*. So the aggregate that should be most inert is the one where the
irreversible operation is least constrained.

**Records consequence.** An archived record is, in records practice, a record in its final resting state
pending disposition. If it can still be moved between files, have registration references added and removed,
and have versions destroyed, then "archived" carries no custodial meaning and cannot be relied on by a
retention rule that triggers on it — which `Archived` is, per
`retentionschedule.design-decisions.md:156`.

---

### AD-3 · High — The edit lock covers content and not lifecycle, so a checked-out record can be published, withdrawn or archived out from under the holder

**What the spec says.** Enforcement is structural and deliberately so — `IMediaItemContentCommand` plus
`MediaItemGuardedCommandHandler`, with `CheckoutEnforcementCoverageTests` failing the build if the two sets
diverge (`:167-182`). **Eight commands** run through the guard: title, description, tag, the two metadata
setters, and the three asset-role commands.

And then, stated as the rule rather than as a gap (`:263`):

> **"The pattern is that content edits are guarded and lifecycle transitions are not."**

`:257-261` gives the consequence directly: *"Any tenant member can publish, archive or withdraw an item
another user holds checked out."*

**What follows.** *(This is a finding about the lock's reach, not about permissions — the question is what
the check-out mechanism is designed to protect, not who may call it.)*

A check-out that does not survive a lifecycle transition is not a check-out. The holder's guarantee is that
the thing they are working on will still be there, in the state they took it in, until they release it. A
concurrent `Publish` ends the edit session (`:230-239`), and a concurrent `Withdraw` or `Archive` moves the
record underneath them. The lock protects the *bytes* and not the *custody*.

**This is the requirement most directly at risk.** `MediaProfile.CheckoutPolicy = RequiredForEdit` is sold as
the control that makes editing serialised and governed. Within content commands it is; across the lifecycle
it is not, and nothing in the model tells the holder which of the two they have.

**A related asymmetry, from the same section.** `:268-275` records that `Withdraw` has no status
pre-condition — *"Withdrawing an item already in `Draft` is legal"* — and that doing so **supersedes any open
edit session**: *"a silent lock release on a no-op withdrawal."* An operation that changes nothing about the
record's status silently destroys someone's working session.

---

### AD-4 · High — The design states that the multi-user edit session does not order its own members, and calls that safer than not having one

**What the spec says** (`mediaitem.write-model.md:159-162`):

> It does **not** order two members of the same session against each other… **"A shared lock without version
> checking underneath looks like it prevents conflicts and does not, which is worse than no lock."**

The aggregate also has no client-facing concurrency surface: *"No command carries an `ExpectedVersion`"* for
`Folder` (`folder.write-model.md:143-145`), and for `MediaItem` the `ETag`/`If-Match` mechanism is honoured
on **exactly two** metadata endpoints and *"silently ignored elsewhere"* (`consistency-model.md:91-100`).

**What follows.** The spec has correctly *diagnosed* the hazard and then shipped the design that has it. The
sentence reads as a warning, but the model it describes is the one being specified: a session that admits up
to 25 collaborators, orders none of them, and offers no per-command precondition by which a caller could
order themselves.

For the stated requirement — check-in/check-out **supporting one or more users** — this is the gap. Single-user
check-out works. The moment a second member is added, the session provides mutual *awareness* and no mutual
*exclusion*, and last-write-wins applies to a regulated record with no record that a write was lost.

**What would close it is not a bigger lock.** Either the session orders its members (a per-session sequence,
or `ExpectedVersion` made mandatory for multi-member sessions), or the design states plainly that multi-member
sessions are collaborative-advisory and must not be used where lost updates are unacceptable. **The current
text does neither** — it warns about the failure mode in a parenthesis and leaves the reader to conclude it
was avoided.

---

### AD-5 · Medium — Nothing in the model distinguishes a working document from a declared record

**What the spec says.** `MediaItem` has a publication lifecycle (`Draft → PendingApproval → Published`), a
version number that increments on approval, and an immutable `SnapshotFields` (`:47`). What it does **not**
have is any statement that a published version's *content* is fixed. On the contrary:

- `Published → Draft` via `Withdraw`, and `Published → Revising` via `BeginRevision` **or** via `CheckOut`,
  which *"emits `MediaItemRevisionStarted` before `EditSessionOpened`"* (`:251-254`).
- Assets can be assigned, unassigned and replaced in role; `AssetUnassignedFromRole` and
  `AssetReplacedInRole` *"have no mapper and produce no integration event"* (`:716`), so a content change to
  a published record is invisible outside Catalog.
- Rule 6 checks asset status **at publish** and assignment has no status constraint at all
  (`cross-aggregate-invariants.md:53-55`).

**What follows.** The model has *publication* — a visibility and approval concept — and is using it where
records management needs *declaration*: the point at which a record becomes fixed, and after which its
content cannot change without a new record or an auditable amendment.

This is the question AD-2 and the versioning model both depend on and neither answers. **What is a version of
a record here?** If a version is a revision of one record, retention and citation attach to the record and
the versions are drafting history. If each is a new record superseding the last, then disposition applies per
version and `PurgeVersion` is destroying records. The spec commits to neither, while providing
`PurgeVersion`, `VersionArtifact` promotion, and a version-asset reference index that all imply the second.

**Recommended as an Open question rather than a fix** — the answer is a product and records-authority
decision, not a modelling one.

---

### AD-6 · Medium — The aggregate carries six concerns, and the spec's own inventory shows three of them are separately-lifecycled

**What the spec says.** `MediaItem`'s state (`:27-53`) holds: identity and classification; the profile
snapshot; content (assets, metadata); `ReviewSession` (embedded, set while `PendingApproval`, cleared on
resolution); the edit session; `ActiveSigningSessionId`; `RegistrationIds`; `CurrentVersionNumber`; and
`ConformanceStatus`/`ConformanceGaps`. Thirty domain events (`:472-504`).

**What follows.** Three of those have their own lifecycle, their own terminal states, and their own
external correlation — the edit session (opened, renewed, reopened, closed with six distinct reasons, pinned
numerically at `:121`), the review session, and the signing-session link. The registration references are
maintained entirely by *another context's* events.

That is not automatically wrong: `editing-lifecycle-and-concurrency.md:100` argues convincingly that review
decisions must stay on `MediaItem` because *"Cannot publish without approval" is a MediaItem invariant and
must be enforced inside that aggregate's transaction* — and moving it out would convert a local invariant into
a distributed one guarded by a saga. **That argument is correct and should not be reversed** (and
`saga-patterns.md:26-28` records that the review saga was built and deliberately removed).

**The finding is narrower:** the same argument has not been made for the other two. The edit session and the
signing-session link are in the aggregate *by default*, not by a recorded decision — and the edit session is
the one carrying the multi-user defect in AD-4 and the coverage gap in AD-3. **The spec should either make
the invariant argument for each, or acknowledge they are there for convenience.**

---

### AD-7 · Medium — Six members the file's own rules depend on do not exist, and the rules fail silently rather than loudly

**What the spec says** (`mediaitem.write-model.md:150-153`):

> ⚠ **Six members this file's rules depend on do not exist:** `IsDeprecated`, `IsSearchable`, `DisplayName`,
> `Description`, `Group` and `Order`.

And at `:442-451`, on field deprecation: *"None of the rule is reachable, and the guards fall back to
`IsRequired` **silently**."* Likewise `:453-468` on default values: *"`DefaultValue` is currently carried the
full length of the platform, six types across two contexts, and applied by nothing."*

**What follows.** This is a design finding rather than a drift one, because the *design* is what makes the
failure silent. A rule that depends on a member which may be absent should be unrepresentable, not
fall-through — and the pattern recurs: a value is carried across four representations, consumed by nobody,
and the consuming rule degrades to a weaker rule without saying so.

`metadata-schema-composition.md:181-184` names the underlying shape: *"Four representations of a field
definition between authoring and use. **Most of this platform's known defects live at that seam.**"*

**This is the seam DF-8/9/14/15 sit on**, which MM-040 argued is one problem that *"will not converge if
fixed separately"* and which currently has no owner. **Pass 3 should take it as a whole**; it is flagged here
only because `MediaItem` is where the consequences land.

---

## Pass 2 — `Collection` and `Folder`: the hierarchy and the file plan

Sources: `docs/spec/contexts/Catalog/aggregates/{Collection,Folder}/*.md`,
`docs/adrs/catalog-domain-invariants.md`, `docs/spec/contexts/Metadata/aggregates/RecordType/recordtype.write-model.md`,
`docs/spec/README.md`.

---

### AD-8 · High — The disposal **rule** and the disposal **clock** come from two unrelated hierarchies

**What the spec says.** Classification is not the folder tree. `recordtype.write-model.md:1863-1866` is
explicit:

> **"There is no hierarchy, no functional classification tree and no file plan.** A `RecordType` is a flat
> named element set, and **the classification of a record is a property of the record class — the
> `MediaProfile`.**"

Retention follows that same axis: a `RetentionSchedule` is *"pinned one-per-`MediaProfile`, because a
disposal rule varies per record **class**, not per record type"* (`spec/README.md:46`).

But the **clock** does not. Of the six retention triggers, `Closure` resolves from *"`ClosedDate` on the
item's **current folder**"* (`retentionschedule.design-decisions.md:159`).

**What follows.** The rule that says *how long* comes from the profile. The event that says *when the clock
starts* comes from the folder. **Nothing connects the two hierarchies**, and three consequences fall out:

1. **A folder is not an instance of a class.** Items with different profiles — and therefore different
   disposal rules — sit in one folder. Closing it starts clocks for a set of records whose rules were chosen
   independently of each other and of the folder.
2. **Moving an item between folders silently changes its disposal clock** without changing its rule. And
   `Move` is the command with no guards at all: *"No status check, no archive check, no checkout check"*
   (`mediaitem.write-model.md:283`). A filing operation with no preconditions re-dates a statutory clock.
3. **The same is true in reverse.** Re-pinning a profile changes the rule without touching the clock.

**Why this matters.** In records practice the business classification scheme is the single spine: it
determines both where a record is filed and what disposal class it inherits. Here the two are orthogonal by
construction, so **the file plan is containment and nothing else** — a folder governs no record in it.

**This is a design position, not an oversight** — `spec/README.md:45` lists business classification among
the recordkeeping controls the platform explicitly does not own, and *"A capability name is not evidence a
control exists."* The finding is that the position and the `Closure` trigger contradict each other: you
cannot both decline to own classification and take the disposal clock from the classification hierarchy.

---

### AD-9 · High — Folder closure carries retention semantics and no behaviour whatever

**What the spec says** (`folder.write-model.md:102-115`):

> *"`Close` guards only `IsClosed` → `FolderAlreadyClosed`, emits `FolderClosed`, and **does not touch
> `Status`**. There is no un-close, and **nothing else in the aggregate guards on `IsClosed`** — a closed
> folder can still be renamed, moved, described and metadata-edited. A folder can be closed and active, or
> archived and never closed."*

And the enforcement that would matter is *"⚠ **Specified, not implemented**"*: `ClosedDate` required on
close, and **assigning or moving a `MediaItem` into a closed folder refused**. Both unguarded.

**What follows.** Closure is the one concept in the hierarchy that is purely a records concept — a file is
closed when no further records will be added to it, which is precisely what makes its closure date a valid
retention trigger. **Here it prevents nothing.** A closed file accepts new records, and each arrival
inherits a clock that may already have elapsed.

Two further asymmetries the spec records without reconciling: `FolderClosed` produces **no integration
event** (`:377`), so no other context can learn a file closed; and closure is orthogonal to `Status`, so
"closed" and "archived" are independent flags with no stated relationship between them — an archived folder
that was never closed has, under the `Closure` trigger, **no disposal clock at all**.

**Read with AD-8**, this is the more serious half: AD-8 says the clock comes from the wrong hierarchy; AD-9
says the event that starts it is unenforced in both directions.

---

### AD-10 · Medium — The aggregate holding the retention-critical date has the least governed metadata in the model

**What the spec says.** `MediaItem` metadata is schema-governed: validated against the pinned
`SnapshotFields`, with `Origin` required per write, collision resolution, and a pure validation function run
at two points (`mediaitem.write-model.md:407-425`). `Folder` metadata is neither —
`catalog-domain-invariants.md:190`:

> *"Scoped to `MediaItem` only — **`Folder` metadata remains fully free-form** and out of scope for this
> decision."*

The only validation is a JSON-kind check against a type **the caller supplies in the command**:
`SetFolderMetadataFieldCommand(… FieldName, RawValue, FieldType, …)` (`folder.write-model.md:242, 289`).

**What follows.** The caller declares the type and the platform checks the value against the caller's own
declaration — which is a well-formedness check, not governance. There is no schema, no required fields, no
immutability, no collision handling, and nothing a records authority could point at.

**In a records system this is inverted.** File-level metadata — title, classification, opened and closed
dates, disposal class, custodian — is normally the *most* governed metadata in the system, because it
describes the aggregation that disposal acts on. Here the item is governed and the file is free-form, and
per AD-8 the file is where the disposal clock lives.

**The absence is stated but its consequence is not.** The ADR scopes folder metadata out of the collision
decision, which is reasonable on its own terms; nothing says folder metadata is ungoverned *by design* or
what that costs.

---

### AD-11 · Medium — `Collection`'s archived state is the weakest in the tree, and the visibility case is the one that matters

**What the spec says** (`collection.write-model.md:87-91`):

> ⚠ **Open decision (U-5) — an archived collection is still mutable.** Only `Rename` and `Archive` guard on
> `IsArchived`. `ApplyTags`, `SetDefaultMediaProfile`, `SetVisibility` and `UpdateDescription` carry no
> archived check, so an archived collection can still be tagged, re-profiled, re-described and **made
> `Public`**. The visibility case is the one that matters.

`Folder` is stricter — `Move`, `Rename` and all three metadata commands refuse with `FolderArchived`
(`folder.write-model.md:107-109`) — and `MediaItem` stricter still. **Three aggregates in one context, three
different answers to the same question.**

**What follows.** `Public` is what `GET /v1/collections/public` selects on (`collection.write-model.md:65`),
so this is not a cosmetic flag: an archived collection can be moved into a publicly-listed set. Archive is
also the point at which the name reservation is **released** (`:63`), so an archived collection is
simultaneously mutable and no longer holding its own identity.

**Settled by Q-3** — content is frozen, custodial operations stay legal. `SetVisibility` is not custodial by
any reading, and this closes U-5 on those terms. The finding stands as the record of *why* the inconsistency
existed: the guard was applied per command as each was written, rather than from a stated rule about what
archived means.

---

### AD-12 · Medium — Archive is irreversible everywhere, and it releases the name

**What the spec says.** `cascade-rules.md:135-144` answers the question flatly: *"un-archive — **No
un-archive command exists for any aggregate**."* `Collection`: *"There is no un-archive: no method, command,
endpoint or event"* (`collection.write-model.md:82`). `Folder`: archive is terminal (`:100`). And on archive
the name reservation is released — for `Collection` (`:63`), `Folder` (via `ArchiveFolderNodeHandler`), and
`MediaItem` title.

**What follows.** Two things compound. Archiving is a **one-way door** across the whole hierarchy, and the
identity is **surrendered** at the same moment — so the state cannot be reversed and the name may already
have been taken by something else by the time anyone tries.

**Mis-filing is routine in records work**, and archive here is not disposal — it is a soft state that
cascades down a subtree, in one case *"synchronous, inline"* and in another *"asynchronous"* with per-child
failures *"logged at warning, not collected, not retried, not returned"* (`cascade-rules.md:60-61`). An
operator who archives the wrong folder has no route back and no complete report of what moved.

**This is a candidate design position rather than a certain defect** — irreversibility is defensible for a
compliance product if it is *stated as a choice*. It is not: the spec records the absence three times and
never says it is deliberate, and `cascade-rules.md` files it under questions with no rule at all.

---

## Pass 3 — `MediaProfile`, `RecordType`, `RetentionSchedule`: the record class

Sources: `contexts/Catalog/aggregates/MediaProfile/*.md`, `contexts/Metadata/**`,
`adrs/metadata-schema-composition.md`. **This pass carries AD-7 and AD-8 in**, per the Pass 2 note.

> **`RecordType` is the best-designed aggregate in the tree and this pass raises nothing against it.**
> Derived status, a single transition table every mutating method consults, retained names and aliases,
> retired field definitions, four publish sweeps, per-field versioning, a one-hop `SupersededBy` with cycles
> unreachable by construction, and a no-op publish that mints nothing. Where findings below touch
> `RecordType` they are about **what crosses its boundary**, not about the aggregate.

---

### AD-13 · High — Governance is attached to a structural aggregate, and one versioning act serves both

**What the spec says.** `MediaProfile`'s stated purpose is structural — *"the structural contract for a
`MediaItem` type — asset role definitions, pinned RecordType schemas, capabilities, and
review/checkout/change-request policies"* (`mediaprofile.write-model.md:13-20`).

Three governance concerns are then attached to that same aggregate:

| Concern | Attached to `MediaProfile` because | Cite |
|---|---|---|
| **Classification** | *"the classification of a record is a property of the record class — the `MediaProfile`"* | `recordtype.write-model.md:1866` |
| **Retention** | *"a disposal rule varies per record **class**, not per record type"* — one schedule pinned per profile | `spec/README.md:46`; `retentionschedule.design-decisions.md:61` |
| **Security classification** | *"It is a **`MediaProfile`** concern — governance attaches to the record class, not to the citable element set"* — and *"**not modelled anywhere yet**"* | `Metadata/context-overview.md:48-52` |

**Each of those placements is individually well-argued.** The finding is what they add up to.

**What follows.** A `MediaProfile` version is minted by `CreateMediaProfileRevision` → draft mutations →
`PublishMediaProfile`, and that one act serves two populations changing at unrelated cadences:

- **Structural change** — add an asset role, re-pin a RecordType version, adjust a checkout policy. Frequent,
  owned by whoever administers the item type.
- **Governance change** — a new disposal authority supersedes the old one. Rare, owned by a records
  authority, and legally significant.

Fusing them has consequences in both directions. A records manager changing a disposal rule must publish a
**structural** version, which triggers conformance re-evaluation across every item pinned to the profile
(`catalog-domain-invariants.md`, the conformance fan-out). And an administrator adding an asset role mints a
version that carries a retention pin they have no authority over.

**And existing items do not follow.** `MediaItem.MediaProfileId` is immutable and `SnapshotFields` is
*"immutable after creation"* (`mediaitem.write-model.md:47`), so an item created under v3 keeps v3's
schema. The conformance fan-out re-evaluates **gaps**, not governance. So a disposal-rule change reaches new
items and is silent for existing ones — which is the correct records answer (a record keeps the rule it was
filed under) arrived at **by accident of the snapshot mechanism rather than by a stated rule**, and with no
way to tell the two populations apart afterwards.

---

### AD-14 · High — The capability set that reaches a record is not the one its class declared

**What the spec says** (`mediaprofile.write-model.md:217-229`):

> `CompiledMetadataTemplate.ToSnapshot()` copies the **compiled union** into
> `MediaProfileSnapshot.Capabilities`, which is what `MediaItemCreated` embeds… `MediaProfile.Capabilities`
> — **the set the author declared** — reaches `MediaProfilePublishedIntegrationEvent` and stops there.
>
> ⚠ **This is a live defect, not a design (U-6).** A behaviour gate belongs to the record class, and the
> class declares its own capabilities; inheriting it from the descriptive schemas the class happens to cite
> means **a profile pinning no RecordType publishes an empty capability set**.

**What follows, and it is worse than U-6 states.** The two sets are read by different gates:

- The **retention publish gate** is profile-side: *"A profile carrying the `Retention` capability must pin a
  `RetentionScheduleRef` before it may publish"* (`retentionschedule.design-decisions.md:111`) — the
  **declared** set.
- Every **item-side** check is *"a `string` `Contains` on a cross-module reference model"* (`:208-209`)
  against the **compiled** set that `MediaItemCreated` carried.

So a profile can declare `Retention`, pass the gate, pin a schedule — and mint items whose capability set
does not contain `Retention` at all. **The record is governed by a schedule it does not advertise.** Anything
item-side that later asks "is this record under retention" — a disposal engine, a hold check, an export —
reads the compiled set and sees nothing.

U-6 frames this as a `Processing` problem with a one-line fix. **It is a governance problem**: it means the
capability vocabulary, which `spec/README.md:45` already warns is *"not evidence a control exists"*, is also
not evidence of what the class *declared*. Fixing it before `RetentionSchedule` is built is materially
cheaper than after, because every item minted in between carries the wrong set immutably.

---

### AD-15 · High — Legal hold is inexpressible, and three other decisions assume something will stop a disposal

**What the spec says.** `Metadata/context-overview.md:55-57`:

> **Legal hold.** Modelled on `Registration` alone, with nothing connecting it to Catalog — so *"**this item
> is under hold and must not be disposed of**" is inexpressible.* Named here so nobody reads the retention
> work as implying a hold exists.

The retention design lists it out of scope in the same terms (`retentionschedule.design-decisions.md:135`),
and ruling 3 defers per-record exceptions — *"A record under legal hold, or individually appraised as
archival against a class that says destroy, is a real thing this design does not express"* (`:329`).

**What follows.** Each statement is honest in isolation. Together with findings already raised, the platform
has a destruction primitive and no way to refuse it:

| | |
|---|---|
| `PurgeVersion` destroys a fixed manifestation of a record | AD-2, and **Q-1** makes it part of the record |
| It is *"**Allowed even when archived**"* with no guard | `mediaitem.write-model.md:358` |
| Retention is *"a record of intent, not an instruction"* — no engine evaluates it | `retentionschedule.design-decisions.md:137-140` |
| Legal hold cannot be expressed at all | above |
| The disposal clock comes from a hierarchy that governs nothing | **AD-8** |

**This is the largest records gap in the model and it is not a gap in any one aggregate** — which is why
each file could honestly record its own part of it as out of scope. A regulated-records platform is expected
to be able to say *"this must not be destroyed yet"* and have something enforce it. **Nothing here can say
it, and nothing would enforce it if it could.**

**Recommended as the first thing Pass 7 tests end to end**, and a strong candidate for the review's top
finding.

---

### AD-16 · Medium — "Deprecated" means three different things depending on which path reaches it

**What the spec says.** Retiring a record class should stop it being used. Three paths disagree:

| Path | Behaviour when the profile is `Deprecated` | Cite |
|---|---|---|
| Create a new item (rule 1) | **Blocked** — the handler loads the **aggregate** and sees `Deprecated` | `cross-aggregate-invariants.md:32` |
| Edit / check out (rule 3) | **Permitted** — reads `MediaProfileIndex`, whose projector *"handles `MediaProfilePublished` **only**, never the deprecation event"*, so the index *"keeps returning the old published snapshot forever"* | `:41-43` (X-11.38) |
| Publish an existing item | **Permitted** — *"`IsUsableByExistingItems()` admits `Deprecated`"* | `mediaitem.write-model.md:629-630` |

The spec names the consequence exactly: *"**After a profile is deprecated, creating and publishing items is
blocked while editing and checking them out continues to work.**"*

**What follows.** Two of the three are a **design** choice and one is a projection gap, and the spec presents
them as one state. Permitting existing items to continue is defensible — a record class is retired
prospectively, and records already filed keep the rule they were filed under (the same principle
`RecordType` implements carefully at version granularity). **Permitting editing because a projector never
learned of the deprecation is not a choice at all**, and it is invisible: the two enforcement mechanisms
disagree and nothing reconciles them.

**The design finding is the mixed enforcement basis**, not the drift. Rule 1 loads the aggregate; rule 3
reads a projection. A single governance fact — *is this class retired* — is answered from two sources of
different freshness, so the answer depends on which door the caller came through.

---

### AD-17 · Medium — The schema a class pins cannot be faithfully reconstructed by its only consumer

_The pinned-vocabulary seam (**DF-8/9/14/15**), taken as one problem per MM-040's argument that the four
*"will not converge if fixed separately"*. Ownerless; in scope for this review by the prompt._

**What the spec says.** `metadata-schema-composition.md:181-184` names the shape:

> **Four representations of a field definition between authoring and use** — record type version, integration
> event, Catalog's reference index, compiled template, item snapshot. **"Most of this platform's known
> defects live at that seam."**

Three independent failures of the same seam, from Metadata's own overview:

- **The contract is too narrow.** *"the shipped event carries a five-property `RecordTypeFieldSummary` and no
  `Aliases`. **Until it is widened a consumer cannot compile a template or enforce a constraint from the
  event alone**"* (`Metadata/context-overview.md:252-254`).
- **The vocabulary is unpublished.** The `FieldType` mapping *"is **live, not designed-only**: Catalog
  projects `media.recordtype.published` today, so a tenant can author a `Url` field now and nothing
  specifies what the consumer does with it"* (`:290-293`).
- **Version-level deprecation has no enforcement path.** `RecordTypeVersionDeprecated` is *"⚠ not shipped"*
  (`:161`), so the retire-a-bad-version story — the reason `DeprecateRecordTypeVersion` exists — reaches
  nobody.

**What follows.** `RecordType` pins a complete, carefully-specified version. Its only consumer receives a
subset, against an unpublished type vocabulary, with one of the three lifecycle signals missing. **The
authoritative schema and the schema in use are different objects, and the difference is not stated anywhere
as a contract** — each file describes its own representation as if it were the whole.

**This is the seam AD-7 said lands on `MediaItem`.** It also explains AD-14: the capability set diverges at
the same boundary, for the same reason — what crosses is computed from what was cited, not from what was
declared.

---

## Pass 4 — `Asset` and `ProcessingJob`: content and its processing

Sources: `contexts/AssetManagement/**`, `contexts/Processing/**`, `shared/saga-patterns.md`.

> **Run as a control.** These two are furthest from the records lens, so if the class/aggregation statement
> in the Pass 3 note is really the root, this pass should find little that fits it. **Result: it found
> almost nothing that fits it** — AD-18 is the single finding that reaches the records lens, and it reaches
> it through `MediaItem` rather than from anything in these aggregates. **That is a useful negative**: the
> root statement is a *records-axis* root, not a universal one, and Pass 9 should scope it that way rather
> than stretching it to cover the whole model.
>
> `AssetIngestionSaga` is the strongest piece of process design in the tree — a correlation key chosen with
> a stated reason (*"the job can be recreated, the asset cannot"*), a two-phase clock reset rather than
> extended, clocks run from event timestamps rather than `UtcNow`, projected attributes so the scanner
> never deserialises state, and a scanner that never writes saga state. **Nothing raised against it here.**

---

### AD-18 · High — What makes a published version's content fixed is an event plus an index that cannot be rebuilt

**Why this is the finding.** **Q-1** settled that the `MediaItem` is the record and each published version is
a *fixed manifestation* of it. This pass asks the obvious follow-up: **what actually fixes it?**

**What the spec says.** Three mechanisms, and no file states that together they are the fixity guarantee:

| Mechanism | What it does | Cite |
|---|---|---|
| `PromoteToVersionArtifact` | On `MediaItemApproved`, each approved asset is promoted; in that state `Archive` and `Delete` are **refused** | `asset.write-model.md:78-88` |
| `VersionArtifactHolders` | **A set of `(MediaItemId, VersionNumber)`, not a counter** — deliberately, *"because SQS is at-least-once and there is no inbox/dedup store"* | `:218-234` |
| `MediaItemVersionAssetReference` | Answers *"which assets are in this published version?"*, read by version purge | `cross-aggregate-invariants.md:229` |

The holder set is good design and the reason given for it is exactly right. **The problem is what sits
around it.**

**What follows.** Three gaps, each individually noted in a different file, and none of them connected to
fixity by any of them:

1. **The index that records a version's contents cannot be rebuilt.** `media-catalog-version-asset-ref` is
   one of the seven cross-context reference models — unversioned, excluded from the manifest and the
   rotation tool, and *"No tool performs that rebuild today"* (`consistency-model.md:176-185`). **If it is
   lost or diverges, what a published version contained is not recoverable**, and the only consumer that
   would notice is version purge, which would then release the wrong assets.
2. **Content changes to a published record leave no trace outside Catalog.** `AssetUnassignedFromRole` and
   `AssetReplacedInRole` *"have **no mapper** and produce no integration event"*
   (`mediaitem.write-model.md:716`). So the role composition of a record can change and no other context —
   including Registration, which may hold a filing against it — can learn.
3. **`Active` is reversible.** `RequestReprocessing` re-enters `Validating` from `Active`
   (`asset.write-model.md:95`), so the asset behind a record can be re-derived. Promotion to
   `VersionArtifact` is what should prevent this for approved content, and the spec's transition table does
   not state the interaction either way.

**The design finding is that fixity is emergent rather than stated.** Three mechanisms in two contexts
combine to produce it, no document claims the guarantee, and one of the three rests on an index with no
repair path. For a regulated-records platform, *"this is the content that was approved"* is the single claim
that most needs to be underwritten explicitly.

---

### AD-19 · Medium — The failure taxonomy is the client contract, and it is both unreadable and mis-assigned

**What the spec says.** The contract is explicit (`processingjob.write-model.md:41-43`):

> **"`Failed` is not absorbing, and `ProcessingTimeout` is the only reversible category.**… This is what
> lets a client observe `Failed → Succeeded`, so **a client must not treat `Failed` as final without reading
> the category.**"

The read model then says the check is impossible (`processingjob.read-model.md:221-223`):

> ⚠ **Neither read model projects `FailureCategory`**, so **the check that sentence asks for cannot be
> performed against the read side.** A client sees `Failed` plus a free-text reason and has no supported way
> to tell a recoverable timeout from a terminal error.

And the category a client would read is wrong anyway (`processingjob.write-model.md:98-103`):

> ⚠ **`ValidationTimeout` is never written to a job.**… A validation-timed-out job therefore reads
> `ProcessingTimeout` and is **wrongly eligible for timeout recovery**.

**What follows.** A state machine that requires a discriminator, does not expose the discriminator, and
mis-assigns it on one of its three paths. Each of the three files is honest about its own half; **no file
owns the contract as a whole**, which is how three compatible statements produce an unusable one.

The mis-assignment is the substantive half: `ValidationTimeout` is *"never written"* because the scanner
dispatches `ProcessingTimeout` first and `Fail` is idempotent, keeping the first category. So the
idempotency rule — correct in isolation, and adopted for a good reason — **silently determines the failure
taxonomy by arrival order**.

---

### AD-20 · Medium — Deleting a record strands its content permanently, from two rules that are each correct

**What the spec says.** Two rules, neither wrong:

- Hard-deleting a `MediaItem` cascades to nothing: *"**Assets, Registrations and ChangeRequests all
  untouched**"* (`cascade-rules.md:30`).
- An asset cannot be deleted *"while **assigned to a role**"* — rule 9, enforced by `Asset` aggregate state
  mirrored from Catalog (`cross-aggregate-invariants.md:62`).

`cascade-rules.md:104-107` records where they meet: *"⚠ **The assets of a deleted MediaItem can never be
deleted.**"* (X-11.42.)

**What follows.** Composition produces a state neither rule intended and neither can exit: the item that
held the assignment is gone, so nothing can unassign, and the asset's mirrored state says assigned forever.
**The storage is unreclaimable and the content of a deleted record persists indefinitely** — which, for a
platform whose delete path is described as the *"one destructive cascade in the system"* (`:109`), is the
opposite of what a deletion is for.

**The design finding is not the deadlock itself** (X-11.42 owns that) **but that nothing owns cascade
completeness.** `cascade-rules.md:135-144` lists four questions with no rule at all — a ChangeRequest on item
delete (*"Nothing. It stays open"*), an in-flight `ProcessingJob` on asset delete (*"Not determined"*),
un-archive, counter reconciliation. A cascade table with four blanks is a design that has not decided what
deletion means.

---

## Pass 5 — `Registration`, `ChangeRequest`, `DocumentSigningSession`: the lifecycle satellites

Sources: `contexts/Registration/**`, `contexts/ChangeRequests/**`, `contexts/DocumentSigning/**`.

> **DF-1 … DF-4 are closed in the spec by MM-041 and are not re-argued.** That text is the newest in the
> tree and the least reviewed, so it was read for what it gets *wrong* — see the correction under AD-23,
> which is against MM-040 rather than MM-041.

---

### AD-21 · High — Cross-context guards are point-in-time, and the domain needs standing constraints

**What the spec says.** Three rules check a cross-context fact once, at command time, and never again:

| Rule | Checked | Never re-checked |
|---|---|---|
| 12 — a Registration may only be initiated or attached for a **published** item | at initiate/attach, from `MediaItemReference` | the item may be withdrawn, archived or deleted afterwards |
| 6 — **publication** requires every assigned asset `Active` | at publish, from `AssetStateReference` | an asset may leave `Active` afterwards; assignment has no status constraint at all (`cross-aggregate-invariants.md:53-55`) |
| 10 — checkout requires an open governance request | at checkout… | …and now at submit and publish, **because MM-041 found exactly this defect** and added two more check points |

**What follows.** Rule 10's fix is the tell. DF-3 was not *"the gate is missing"* — the gate was there and
was **point-in-time**, and closing it took re-checking at the two later moments where the fact must still
hold. **The same shape is unexamined in rules 12 and 6.**

A registration is the clearest case: a filing is *"a **permanent legal record**"*
(`registration.write-model.md`), and its supporting documents were checked for publication status when
attached. Nothing re-checks them, and nothing prevents them being withdrawn or deleted afterwards — so a
confirmed statutory filing can come to cite documents that no longer exist in a publishable state.

**The design finding is the missing concept, not the three instances.** The model has **eligibility** —
*was this true when the command ran* — and no notion of a **standing constraint** — *this must remain true
while the relationship lives*. Records work is full of the second kind. The reference models are shaped for
the first: `MediaItemReference` holds `IsPublished` for a command-time lookup, and *"`IsArchived` is written
by the archive handler and **read by nothing**"* (`registration.write-model.md`), which is what a field
carried for a standing check nobody makes looks like.

> The Registration instance is enumerated in **DF-17**, owned by the drift review, and is not re-raised
> here. This finding is the pattern across all three rules and the absent concept underneath — the same way
> MM-040's DF-5 generalised three counters into one problem.

---

### AD-22 · High — The obligation counter has no timeout on any path, and every exit is human

**What the spec says.** `registration.write-model.md` § Deliberately not supported:

> **No expiry or timeout.** Nothing scans for stale registrations, and `PendingConfirmation` has no upper
> bound. A filing whose authority never responds stays there until someone cancels it.

And `PendingConfirmation` is reached **after** initiation, which raised `active-registrations` — the sole
gate on `ArchiveFolder` (rule 13).

**What follows.** **DF-1 closed the successful path** — `confirmed` keeps the counter raised deliberately,
and the new `Discharged` transition releases it. **The unanswered path is still open and is not the same
defect.** A registration submitted to an authority that never replies holds its folder's archive guard
raised indefinitely, and the only exits are `Cancel` (owner-driven) and `Discharge` (System, and only from
`Confirmed` — unreachable from `PendingConfirmation`).

So the obligation can only be cleared **by a person who notices**, and nothing surfaces it: there is no
scan, no stale-registration query, and *"**No status filter on any query.** Neither GSI keys on `Status`"*.
A tenant cannot even list what is stuck.

**Compare the platform's own answer elsewhere.** `AssetIngestionSaga` has a two-phase clock, a scanner on a
five-minute schedule and a compensating dispatch. The pattern exists and is well built — it is simply not
applied to the one lifecycle whose stalling blocks a records operation.

**Why this is not DF-1.** DF-1 was *the counter is never released on success*. This is *the counter has no
release path when nothing happens at all*, and no decision in MM-041 touches it.

---

### AD-23 · Medium — The governance container imposes no governance constraints, and stays mutable after the change lands

**What the spec says.** `ChangeRequest` exists to hold *why* a change was made. Two properties sit oddly
with that:

- **It constrains nothing.** *"There is **no uniqueness constraint, no reservation and no per-item
  open-request count** anywhere in this module… **This aggregate imposes no cardinality at all**"*
  (`changerequest.write-model.md:57-60`). Cardinality is enforced by Catalog, on `MediaItem.ReviewSession`.
- **It stays editable after it closes.** *"**`EditComment` and `DeleteComment` do not check `IsOpen`.**
  Comments on a resolved or abandoned request can still be edited and soft-deleted by their author.
  **Whether that is intended is not stated.**"*

**What follows.** The governance record for a landed change remains mutable by its authors after the change
has landed, and the aggregate whose purpose is governance delegates every constraint on itself to another
context. **A governance record should be at least as fixed as the record it governs** — under Q-1 the item
is the record and its published versions are fixed manifestations, while the justification for the change
that produced them is not fixed at all.

**Correction to MM-040 — DF-17 overstates this, and the overstatement matters.** DF-17 says
`ReviewCommentEdited` *"deliberately carries no `OldBody`, so **no evidence of the change survives**."* The
first half is right and the second is wrong: `changerequest.scenarios.md:276-279` states that *"the prior
text is **recoverable from the preceding `ReviewCommentAdded`/`ReviewCommentEdited` in the stream**, so
nothing needed to duplicate it."* Event sourcing preserves the history; what `OldBody` would have added is
convenience, not evidence.

**That changes what the fix is.** The problem is not an audit hole — it is that a closed governance record
accepts mutation, and that nothing says whether that is intended. **Raised for the drift register (MM-022),
which owns DF-17**, so the enumeration can be corrected rather than acted on as written.

---

### AD-24 · Medium — `DocumentSigningSession` is specified as a closed loop that cannot inform the rest of the model

**What the spec says.** *"This context is a skeleton"* (`DocumentSigning/context-overview.md:20`), with no
aggregate root. Reviewing the **design** rather than the build, two structural properties:

- **Its events reach nothing.** Nine domain events exist and are well-formed, and **no integration events
  are specified at all**; *"`DomainEventPublishingMiddleware` omits `ISigningDomainEvent`… so none reaches
  SNS"*. Signing outcomes are stated to surface *through Catalog* instead.
- **Its invariants reference state it does not hold.** Every ownership rule is expressed against an owner —
  *"⚠ **Code gap — the session has no owner**"*, and no event carries one. `SigningSessionCancelled` carries
  no `CancelledBy`, so a cancellation is unattributable.

**What follows.** As specified, the aggregate can be driven and can reach terminal states, and **nothing
outside it can observe any of that except through Catalog's link field**. For a signing session the outcome
*is* the point — a signed instrument is a record — so an aggregate that produces one and cannot announce it
has a boundary drawn in the wrong place.

**This is the cheapest finding in the review to act on**, because nothing is built: the integration contract
and the owner field cost nothing now and are a migration later. Compare `Registration`, which is the same
shape done right — an external process the platform does not control, modelled with a full published event
set and a reference model.

> DF-12's mutual-exclusion fault and the orphaned signed artefact belong to **MM-038** (`document-signing/`,
> parked) and are not re-raised. MM-040's advice stands: *"it should be fixed **before the module is built**,
> not after"* — which applies to this finding too.

---

## Pass 6 — the relationships

Sources: `shared/cross-aggregate-invariants.md`, `consistency-model.md`, `cascade-rules.md`,
`saga-patterns.md`, `concurrency-and-consistency.md`, `architecture/domain-model.md`.

**The main event.** Passes 1–5 fed it, and it is the first real test of the three candidate roots.

---

### AD-25 · High — Nothing states how to choose a relationship mechanism, and the same question is answered two ways

**What the spec says.** Five mechanisms carry cross-aggregate relationships (Pass 0 map). The catalogue in
`cross-aggregate-invariants.md` records **which** each rule uses. **No file states why, or when to use
which.**

The cost is visible where one question gets two answers:

| One question | Answered by | And by |
|---|---|---|
| *Is this profile usable?* | Rule 1 — loads the **aggregate**, sees `Deprecated`, refuses | Rule 3 — reads `MediaProfileIndex`, a **projection** that never learned of the deprecation |
| *Is this asset in use?* | Rule 9 — `Asset` **aggregate state**, mirrored from Catalog | Rule 8 — `AssetProfileDefaultReference`, a **reference index** |
| *What capabilities does this class have?* | The retention gate — the **declared** set on the aggregate | Every item-side check — the **compiled** set copied into a snapshot (AD-14) |

The first pair is the sharpest: the spec states the consequence itself — *"**Rules 1 and 3 disagree with each
other after deprecation, and the difference is invisible**"* (`:41-43`) — and the reason is purely that two
rules about one fact were implemented against two different sources.

**What follows.** Mechanism choice is the most consequential decision in a distributed model: it fixes the
freshness, the failure mode, the repair path and the coupling of every relationship. Here it is made
per-rule, at implementation time, and recorded only after the fact.

**The rule that would prevent this already exists in miniature and is stated elsewhere.**
`folder.write-model.md` says twice that a projection is *"the wrong basis for an invariant"*; the
counter design was chosen over projections for exactly that reason
(`adrs/catalog-domain-invariants.md`); and `cross-aggregate-invariants.md:53-55` justifies rule 6's
placement explicitly. **Three good arguments, none generalised into a rule**, and four rules break the
principle they establish.

**This is the "no owner of compositions" pattern at its source.** Each rule is defensible where it was
written. The set is not coherent, because nothing owns the set.

---

### AD-26 · High — Containment has no authoritative representation, only derived ones

**What the spec says.** The hierarchy is expressed entirely child-to-parent, and every aggregate says so:

- *"**No entities.** A `Collection` holds no child collection of its own — folders and items reference it,
  not the reverse"* (`collection.write-model.md:71-72`).
- *"**No entities** — a folder does not know its children"* (`folder.write-model.md:86`).

So *"what is in this file?"* can only be answered by projection: `FolderFoldersIndex` and
`FolderMediaItemsIndex`, both *"read by handlers to make decisions, not served to clients"*
(`cross-aggregate-invariants.md:165-166`). Both are same-module indexes that *"the CLI does not clear"*, so
a replay *"leaves stale entries behind rather than rebuilding"* (`consistency-model.md:187-189`).

**Child-points-to-parent is the correct aggregate design** and should not change — a folder holding its
children would be an unbounded aggregate, and the spec's reasoning for rejecting a downward walk (*"that
would be O(descendants) and would rest on a projection"*) is right.

**What follows.** The consequence is not the modelling choice; it is that **the one relationship a records
system is built around has no authoritative form**, and every operation over an aggregation is therefore an
operation over a projection:

- The **archive cascade** — a records act over a file and its contents — traverses these indexes. It is run
  by two workers that `saga-patterns.md:142-147` calls *"**sagas without the name**… Neither has state, a
  correlation key, a resume path, a timeout, a status surface or a test."*
- **Disposition, when it arrives**, will have the same problem: a retention rule applies to a class, the
  clock comes from a file (AD-8), and *which records are in that file* is a projection with no repair path.
- **A completeness claim cannot be made.** The cascade reports `IsComplete`, but it is complete with respect
  to the index, not to the tree.

**This is the class/aggregation root seen from the relationship side.** AD-8 said governance attaches to the
class while the events come from the aggregation. AD-26 adds that **the aggregation itself is derived** — so
the half of the model that records practice leans on hardest is the half with no authoritative
representation and no rebuild path.

---

### AD-27 · High — Replicated facts carry no freshness contract, so no consumer can refuse to act on a stale one

**What the spec says.** Thirteen reference indexes replicate facts across boundaries. The only freshness
marker on a row is `ProjectedVersion`, and its own definition rules out the use a consumer would need:

> `ProjectedVersion` | `long` | **A local monotonic watermark, with no relationship to the source
> aggregate's event-store version.** — `registration.write-model.md`

Around it: read-your-own-writes is *"**No — not on any production path**"*; staleness is **unbounded and
unmeasured**, with *"no SLO, no alarm, no metric, no dashboard"*; and `ProjectedVersion` *"never exposed"*
(`consistency-model.md:18-19, 64-76, 91-100`).

**What follows.** Every cross-context guard in the catalogue reads a replicated fact, and **not one of them
can tell how old the fact is.** The design has only two available responses to a row — trust it, or treat
absence as unknown — and the spec picks per rule: rule 10 *"leans open"* at checkout and fails closed at
submit and publish (correctly, and for a stated reason); rule 12 trusts `IsPublished` unconditionally.

**A third response is unavailable and is the one records work needs:** *this fact is too old to act on.*
There is no way to express it, because there is no measure. A disposal decision, a hold check or a
publication gate cannot say "refuse, the evidence is stale" — only "proceed" or "not found".

**This is instants-vs-durations at the infrastructure level.** A replicated fact is a point-in-time copy with
no expiry, used to answer questions whose correctness depends on currency. AD-21 found the same shape in the
guards; this is why the guards cannot do better — **the substrate offers them nothing to reason with.**

---

### AD-28 · Medium — The completeness rule covers one mechanism of five

**What the spec says.** MM-041 added § *Completeness of cross-context reference projections*
(`cross-aggregate-invariants.md:240-261`) after DF-1 and DF-2: a cross-context reference model must
enumerate the producing context's **complete published event set** and state, per event, the write it makes
or why it makes none. *"A silent omission is not permitted."*

**What follows.** The rule is right and it is scoped to *reference projections* — indexes, counters, and
write-side state derived from another context's events. **Four other mechanisms carry relationships and none
has an equivalent:**

| Mechanism | Completeness question nobody asks |
|---|---|
| **Cascades** | Which relationships propagate on archive, delete, deprecate — and which deliberately do not? `cascade-rules.md:135-144` has **four rows with no rule at all**, including *"Not determined"* |
| **Synchronous query-service reads** | Which facts does this handler need, and what does it do when the read is empty vs stale? Decided per rule (AD-25, AD-27) |
| **Aggregate-loaded relationships** | When is loading the other aggregate required rather than optional? Rules 1 and 9 do; rules 3 and 8 answer the same questions without |
| **Sagas and process managers** | Which cross-aggregate processes need state, correlation, timeout and resume? Two live ones have none |

**The generalisation is cheap and the argument is already written.** The completeness rule's own reasoning —
*it is checkable by reading, it survives the producer growing, "makes no write" is a legitimate answer, and
nothing else will catch this* — applies unchanged to all four. Extending it is a documentation act, not a
design one.

**And it is the highest-leverage single change this review has found**, because it is the only finding whose
fix makes the *next* defect visible rather than fixing one that exists.

---

## Pass 7 — the records lens, end to end

Walking **capture → declaration → classification → governance → retention → disposition** and asking what
the *system* cannot answer. As expected, the findings here are about **absent concepts**.

Stages already covered: declaration (**AD-5**, and Q-1 settled the record is the item), classification
(**AD-8**, **AD-13**), governance (**AD-3**, **AD-23**), retention clock (**AD-8**, **AD-9**), hold
(**AD-15**). This pass adds capture and disposition, which had not been walked.

---

### AD-29 · High — There is no fixity value anywhere in the model

**What the spec says.** Nothing. A search of the whole spec tree for a checksum, digest or hash of stored
content returns **three unrelated uses and no fixity concept**: HMAC-SHA256 for webhook signature
verification (`api-conventions.md:954-958`), and S3 key sharding from `AssetId` — *"**No hashing
required**"* (`event-store-and-messaging.md:535`; `system-architecture.md:907`).

`Asset` holds `StorageKey` *"immutable after `AssetUploadInitiated`"*, `AssetMetadata` write-once, and a
`Renditions` list. **None of them is a content digest.**

**What follows.** The platform cannot answer the most basic question asked of a records system: **"is this
still the bytes that were filed?"** There is no value to compute at capture, nothing to re-verify against
later, and nothing to include in an export or a transfer.

Three consequences, each of which a finding already raised depends on:

- **AD-18's fixity is structural only.** `VersionArtifact` promotion prevents *deletion* of an approved
  asset. It says nothing about whether the object's bytes are unchanged — S3 objects are addressed by key,
  and the key is immutable while the object it points at is not modelled as such.
- **A transfer cannot be attested.** Handing records to an archival authority requires evidence they arrived
  intact. There is nothing to hand over.
- **Bit rot and silent corruption are undetectable**, and the retention periods are long — the
  Registration statutory default alone is **10 years** (`registration.write-model.md`).

**This is the one absence in the review with no partial answer anywhere in the tree.** Every other records
gap has at least a design, a stated non-goal, or a deferred ruling. Fixity is simply not a concept the model
contains, and it is cheap at capture and expensive to retrofit across existing content.

---

### AD-30 · High — The retention design specifies the clock to the member and the act not at all

**What the spec says.** `trigger` gets a six-row table, a stated rule — *"a retention trigger must name an
event the platform raises and timestamps"* — a readiness column per member, an "undeterminable when" column,
and a decision record for the two that needed timestamps (D4).

`action` gets a one-word type declaration. It is described as *"a domain enum on the aggregate, **closed by
construction**"* (`retentionschedule.design-decisions.md:243`) and **its members are never enumerated
anywhere in the current design.** `RetainPermanently` appears in the model sketch and in an invariant;
`Destroy` appears once, in a warning. `Transfer` and `Review` appear **only in the withdrawn design's
precedence ladder** (`adrs/metadata-schema-composition.md:159`).

**What follows.** The half of a disposal rule that says *when* is specified with real care. The half that
says *what happens* — which is the half with legal consequences — has no vocabulary, no readiness
assessment, and no equivalent of the trigger rule.

**Apply the trigger rule to the actions and the gap is obvious.** *"A retention trigger must name an event
the platform raises and timestamps"* has an exact analogue: **a disposal action must name an operation the
platform can perform.** Against that test:

| Action | Can the platform perform it? |
|---|---|
| `RetainPermanently` | ✅ — it is the absence of an act |
| `Review` | ❌ no review workflow, no queue, no assignment; *"any engine that… runs a disposal review"* is out of scope |
| `Transfer` | ❌ **no export exists anywhere in the platform** — Registration's own retention section notes *"no tenant-offboarding export"*, and no transfer or archival-export capability appears in any context |
| `Destroy` | ⚠ only `PurgeVersion`, which is outside the disposition model entirely — see AD-31 |

So a records authority can author a schedule whose disposal action the platform has no way to carry out,
and — unlike the trigger case, where D4 required the missing timestamps to ship with the vocabulary —
**nothing prevents it.** This is the same defect D4 was raised to prevent, on the other axis, and it is
unexamined.

---

### AD-31 · High — The lifecycle has no terminus, and the one destruction primitive sits outside the disposition model _(answers **Q-4**)_

**What the spec says.** Every disposition capability is out of scope by an explicit, individually-reasonable
decision:

| | |
|---|---|
| Any engine computing a due date, evaluating a trigger, or running a disposal review | out of scope (`retentionschedule.design-decisions.md:127`) |
| *"Any link to `PurgeVersion` or **any other destruction primitive**"* | out of scope (`:129`) |
| Legal hold | out of scope, and inexpressible (**AD-15**) |
| Per-record exceptions and archival appraisal | deferred, ruling 3 |
| Transfer / export | does not exist (AD-30) |
| Un-archive | *"No un-archive command exists for any aggregate"* (**AD-12**) |

And the design states the outcome plainly: *"a record pinned to a schedule saying `Destroy` whose period has
elapsed **will sit there indefinitely**… the schedule is a **record of intent, not an instruction**"*
(`:137-140`).

**What follows — and this is Q-4's answer.** The model contains exactly one operation that destroys record
content: `PurgeVersion`. Q-1 made a published version a fixed manifestation of the record, so purging one
destroys part of a record. Q-3 froze archived content but kept custodial operations legal. **`PurgeVersion`
is neither** — it is not a content edit and it is not custody. **By elimination it is disposition**, which
is the classification the review predicted.

The consequence is what Q-4 was opened to surface:

> **The platform's only act of disposition sits entirely outside its disposition model.** `PurgeVersion` is
> *"**Allowed even when archived**"* (`mediaitem.write-model.md:358`) with no guard, no authority, no
> recorded authorisation, no hold check — and the retention design excludes it by name, so no schedule can
> ever authorise or restrain it.

**The records lifecycle therefore has no end.** Records can be captured, declared, classified, governed and
scheduled; they cannot be disposed of — except by one operator command that answers to nothing. **That is the
inverse of what a compliance-grade platform is for**, where the destruction path is normally the most
controlled path in the system.

**Recommendation, and it is not "build the engine".** The engine is correctly out of scope — recording
retention and acting on it *are* different capabilities, and the design is right to say so. What is missing
is far smaller: **bring `PurgeVersion` inside the model as a named disposition act** — authorised, recorded,
refusable — so that when hold and the engine arrive there is something for them to attach to. Today they
would have nothing to gate.

---

## Pass 8 — robustness of the design

Not *"is it production ready"* — that is a question about a running system. **Does the model, as specified,
survive the first bad day?** The test is whether the spec has an answer; "it does not say" is the finding.

---

### AD-32 · High — The model has no operator surface for any of the derived state it depends on

**What the spec says.** The design depends on thirteen reference indexes, two counters, sagas and two
unnamed process managers. For **none** of them can an operator see the state, repair it, or re-run the
process. Collected from four files:

| State | What an operator can do |
|---|---|
| `active-registrations` counter (gates folder archive) | *"There is **no reconciliation job** and **no way to inspect the counter through the API**"* — and a persistent failure leaves it high, so *"**the folder becomes permanently unarchivable with no visible cause**"* (`cascade-rules.md:128-131`) |
| Saga state | *"no CLI saga verb, no admin endpoint, no force-close, no state inspector"* — and *"**Do not edit the saga row to a terminal status directly**"* (`assetingestionsaga.md:236-261`) |
| Collection archive cascade | *"There is no way to re-trigger the cascade through the API"* (`archive-fan-out.md`, via DF-7) |
| Per-child cascade failures | *"logged at warning, **not collected, not retried, not returned**"* (`cascade-rules.md:60-61`) |
| Stale registrations | No scan, no query — *"**No status filter on any query.** Neither GSI keys on `Status`"* (AD-22) |
| Signing sessions | *"**Manual Intervention Runbook** ⚠ Not implemented… **Write this before the first deploy, not after**"* (`documentsigningsaga.md:209-224`) |

**What follows.** The saga entry is the clearest statement of the problem: the spec **forbids the manual
workaround and provides no supported path**. That is the correct instruction and it leaves an operator with
nothing.

**This is a design finding, not a tooling backlog.** Derived state that cannot be inspected cannot be
trusted, and this model's derived state **backs decisions, not screens** — `cross-aggregate-invariants.md`
says so directly of the counters and indexes: *"**Every one of these backs a decision.**"* An invariant
enforced against state nobody can see or correct is an invariant only while nothing goes wrong.

**The asymmetry is the tell.** Enormous care has gone into making these mechanisms *correct* — strongly
consistent counter reads, `ConsistentRead` on saga load, projected attributes so the scanner never
deserialises, idempotent handlers, a holder set rather than a counter. Almost none has gone into making them
*observable*. The model is designed for a world where it does not drift, and the spec elsewhere states
plainly that it does.

---

### AD-33 · High — Repair is a stated requirement that the platform cannot discharge

**What the spec says.** MM-041 added the repair position (`consistency-model.md`): a change to a reference
model's rules *"is not complete until it states one of two things"* — a seeding or repair pass, or a
recorded finding that no affected data exists. It also says, in the same breath: *"**No such tool exists
today** — writing one is part of the change, not a follow-up."*

Now the inventory of what repair is available:

| | |
|---|---|
| CLI event replay | **6 of 10** aggregates |
| Same-module indexes | replayable *"in principle but not in practice"* — the CLI **does not clear them**, so a replay *"leaves stale entries behind rather than rebuilding"* |
| The seven cross-context indexes | *"**No tool performs that rebuild today**"* |
| Both counters | written by command handlers — *"**no replay reproduces them at all**"* |
| Blue-green table rotation | *"explicitly a **dev procedure**"*, and *"**the rebuild path has never been exercised where it would actually be needed**"* |

**What follows.** The requirement and the capability are stated in the same file and do not meet. **Every
change to derived cross-context state carries an obligation the platform has no means to satisfy**, so in
practice the second option — *record that no affected data exists* — is the only one available, and it is
only available while nothing is in production.

**That is a temporary escape and the spec depends on it silently.** `PROD_ENABLED` and `STAGING_ENABLED`
are both unset; the moment they are not, the repair position becomes unmeetable rather than merely unmet.
**The design should say which of the two closes it is relying on** — and if it is the second, that is a
dated position, not a rule.

**Read with AD-32**, this is the same gap twice: the model cannot show you its derived state, and it cannot
rebuild it either.

---

### AD-34 · Medium — The stated limits bound the infrastructure; nothing bounds what the domain grows

**What the spec says.** The model is carefully bounded where a platform constraint bites, and each limit has
a stated reason:

| Limit | Reason given |
|---|---|
| 500 descendant folders per archive | API Gateway's 29s timeout — *"the alternative is… a half-archived subtree nothing retries"* |
| 25 collaborators | *"not a product rule, it is a durability bound"* — the set is replayed forever |
| Depth 10, 3 record types, 100 fields | schema and traversal bounds |
| 160 KB / 512 KB / 256 KB schema caps | *"a version that cannot be announced is never minted"* |

**And the domain quantities are unbounded:**

- **Saga rows.** *"⚠ **Nothing ever deletes a saga row and `media-sagas` has no TTL attribute.**"* Terminal
  instances accumulate indefinitely (`assetingestionsaga.md:62`).
- **Registrations.** No cap per item, **no expiry**, no timeout (AD-22) — each one raising a counter that
  gates a records operation.
- **Items per folder.** No cap. The archive cascade bounds *folders*, not items.
- **Read partitions.** *"⚠ **Every job summary for a tenant shares one partition**"*
  (`processingjob.read-model.md:47-50`).

**What follows.** The bounded quantities are the ones that would break a Lambda. The unbounded ones are the
ones a records tenant accumulates over a ten-year retention period — and the spec's own statutory default is
exactly that (`registration.write-model.md`).

**Nothing here is wrong today and the reasoning behind each stated limit is good.** The finding is that the
limits were derived from the runtime rather than from the domain, so **the model has no stated position on
what a large tenant looks like after a decade** — which is the only timescale a records platform operates
on.

---

### AD-35 · Medium — Four failure dispositions, each locally reasoned, none reconciled

**What the spec says.** Four cross-aggregate mechanisms fail four different ways, each with an argument:

| Mechanism | On failure | Stated reason |
|---|---|---|
| Sagas | return, never throw; outer handler catches **once**, only to convert to `Failed()`; *"`catch (Exception)` never qualifies"* | a rejected command is not an exception |
| Registration ref handlers | *"logged and acked, deliberately, for idempotency"* — trade accepted: a persistent failure leaves the counter high | idempotency under redelivery |
| Cascade workers | per-child failures *"logged at warning, not collected, not retried, not returned"* | — |
| ChangeRequest close | *"acks the message whatever happens"*; *"a failed close is **not retried and not dead-lettered**"* | redelivery must not poison-queue a succeeded outcome |

**What follows.** Three of the four choose *ack and continue*, each for a defensible reason, and the
composite effect is that **a persistent failure anywhere in the cross-aggregate machinery is invisible**:
the message is acknowledged, nothing reaches a dead-letter queue, and per AD-32 nothing can be inspected
afterwards.

The saga rule is the one that is fully specified — it says what to catch, what not to catch, and why
`OperationCanceledException` is not a handled outcome. **It is also the only mechanism with a DLQ and an
alarm.** The other three inherited "ack and continue" from idempotency arguments without inheriting the
observability that makes it safe.

**This is the composition pattern in its most operationally costly form** — and it is what AD-28's
generalised completeness rule would surface, since *"what happens when this relationship fails"* is exactly
the kind of question a per-mechanism rule forces someone to answer.

---

## The records-management verdict

**Can this system do records management?** It can do the first half well and the second half not at all.

| Stage | State |
|---|---|
| **Capture** | ✅ Solid — upload, validation, processing, provenance fields. ❌ **No fixity value** (AD-29) |
| **Declaration** | ❌ **Not modelled.** Publication is a visibility and approval concept being used where declaration is needed (AD-5) |
| **Classification** | ⚠ Real but split — the class is `MediaProfile`, the aggregation is `Folder`, and **nothing connects them** (AD-8, AD-13). The aggregation is itself derived (AD-26) |
| **Governance** | ⚠ Present and incomplete — the edit lock covers content not custody (AD-3), multi-user sessions do not order their members (AD-4), and the governance record stays mutable after the change lands (AD-23) |
| **Retention** | ⚠ Designed, unbuilt, and **specified only on the clock side** (AD-30). The clock comes from a hierarchy that governs nothing (AD-8) |
| **Hold** | ❌ **Inexpressible** (AD-15) |
| **Disposition** | ❌ **No terminus.** Every path out of scope; the one destruction primitive answers to nothing (AD-31) |

**What an agency would ask first, and the answer it would get:**

- *"Prove this record has not been altered."* — **Cannot.** No fixity value exists (AD-29).
- *"Place these records on hold."* — **Cannot.** The statement is inexpressible (AD-15).
- *"Show me everything in this file and dispose of it as a unit."* — **Partially.** Containment is a
  projection with no repair path (AD-26), and disposition does not exist (AD-31).
- *"When is this due for destruction?"* — **Soon.** Designed and unbuilt; the clock is sound in principle
  and comes from the wrong hierarchy (AD-8).
- *"Transfer this series to the archives."* — **Cannot.** No export exists (AD-30).

**The pattern across all five is the same**, and it is the fairest summary of this model: **the platform is
strong at everything that happens to a record while it is in use, and has not yet modelled what happens to a
record because it is a record.** That is a coherent place to be partway through a build — the first half is
harder to retrofit than the second, and it was built first. **The risk is that the vocabulary already
promises the second half**: capability names, a retention schedule, statutory periods in the Registration
spec. `spec/README.md:45` says it best, about itself — *"**A capability name is not evidence a control
exists.**"*

---

## Open questions

**All three answered by Chase, 2026-09-14.** Recorded with what each commits the design to; the consequences
are carried into the findings and into Q-4, which the answers created.

### ✅ Q-1 — The `MediaItem` **is** the record; versions are fixed manifestations of it _(AD-5)_

Retention and citation attach to the item, not to a version. Consistent with what the model already does:
`RetentionScheduleRef` pins at profile → item, `Registration` references a `MediaItemId` rather than a
version, and `VersionArtifact` promotion already protects a published version's assets without versions
needing to be records in their own right.

**What it commits the design to.** A published version is a **fixed manifestation of a record**, so
destroying one is not housekeeping — `PurgeVersion` must be governed (Q-4, which this decision creates). And
the spec has to say where **declaration** happens, because "the item is the record" is only meaningful if
there is a point after which the item is fixed. **AD-5 stands on that basis** and narrows to: name the
declaration point.

### ✅ Q-2 — Exclusion, enforced by preconditions _(AD-4)_

`ExpectedVersion` / `If-Match` becomes **mandatory on content commands when an edit session has more than one
member**. Chosen over a new session-ordering concept because it extends machinery that exists rather than
inventing one.

**What it commits the design to.** The current silent-ignore behaviour becomes a defect rather than a quirk:
`If-Match` is honoured on exactly two metadata endpoints and *"silently ignored elsewhere"*
(`consistency-model.md:91-100`). A precondition that is mandatory in one place and ignored in another is
worse than one that is absent, because a caller cannot tell which they are getting. **The set of commands
honouring it must become explicit and complete, and a multi-member session must refuse a content command
that arrives without one** — silently ignoring it there would reproduce AD-4 exactly.

### ✅ Q-3 — Freeze content, allow custodial operations _(AD-2)_

*Chase's call, against the review's recommendation to freeze outright.* Archived **content** is fixed —
assets, metadata, title, description, tags. **Filing operations stay legal**: moving between folders, adding
and removing registration references. The reasoning holds and the review accepts it — reorganising a file
plan after archive is legitimate records practice, and freezing it would make the archive state fight the
archivist.

**What it commits the design to, and this is no longer optional.** The review flagged one cost with this
option; choosing it makes that cost load-bearing:

> **The archived-`Move` defect must be fixed as part of this decision.** `ArchiveMediaItemHandler` releases
> the title reservation on archive, so a later move *"calls `MoveAsync` against a reservation row that no
> longer exists"* (`mediaitem.write-model.md:283-288`). Keeping `Move` legal on an archived item is choosing
> to make it work. Under *freeze outright* this would have resolved itself.

**Applies once across `Collection`, `Folder` and `MediaItem`**, closing U-5
(`collection.write-model.md:87-91`) on the same terms. `Collection` is the weaker case: four commands there
carry no archived check at all, including `SetVisibility` — so an archived collection can currently be made
**`Public`**, which is not custodial by any reading and is frozen under this decision.

### 🔶 Q-4 — Is `PurgeVersion` content, custody, or disposition? **New — created by Q-1 and Q-3 together**

Neither decision settles it, and together they make it sharp. Under **Q-1** a published version is a fixed
manifestation of a record, so purging one destroys part of the record. Under **Q-3** archived items still
accept custodial operations — and `PurgeVersion` is *"**Allowed even when archived**"*
(`mediaitem.write-model.md:358`) with no guard at all.

The two positions are consistent **only** if `PurgeVersion` is classified as **disposition** — not a content
edit (which Q-3 freezes) and not a custodial operation (which Q-3 permits freely). The review's reading is
that disposition is the only classification that survives both answers. **But the governance that would
attach to it does not exist:** `retentionschedule.design-decisions.md:129` puts *"any link to `PurgeVersion`
or any other destruction primitive"* explicitly out of scope for the retention design.

So the model would have a destruction primitive classified as disposition, with no disposition authority
able to authorise it. **This is a decision for Chase, not a finding.** Carried into Pass 7, where disposition
is reviewed end to end.

---

## Recommended sequencing

> ### ✅ Revised after the decisions — this is the live order
>
> _Corrected by the round-5 sweep: DEC-20 promoted, DEC-21 folded in, DEC-18's spec fix split out._
>
> | # | Unit | Decisions |
> |---|---|---|
> | **0** | **Correct the retention text in the spec** — state that DEC-1's item-level pin supersedes D3's profile-level gate | DEC-18 · **not the implementation, just the text.** Closes the window where the spec carries two incompatible placements |
> | **1** | **Generalise the completeness rule** to cascades, query-service reads, aggregate-loaded relationships and sagas | DEC-15 · closes AD-28, settles AD-20 |
> | **1b** | **Make the containment projection faithful** — full MediaItem event set, CLI clears before replay | DEC-16 · closes AD-26. **Do it with unit 1** — the same rule applied to one index; units 5 and 6 depend on it |
> | **2** | **Fixity — capture digest and version manifest** | DEC-2 · independent, and the only remedy whose cost rises with every object stored |
> | **2b** | **Correction-by-append, designed once** — attributed, reason-bearing, never overwriting | DEC-20 · **promoted from last.** Units 5, 6, 7 and 12 all consume it; leaving it late produces the four divergent models it exists to prevent |
> | **3** | **Repair, then freshness** — rebuild the seven indexes, seed the counters, then source-relative versions | DEC-10 · underpins DEC-1 and DEC-3; ordering within it is forced |
> | **4** | **Read-only operator surface** | DEC-11 · pairs with 3; makes AD-22 and AD-35 tractable without their own remedies |
> | **5** | **Retention *and classification* on the item** — both pinned from the profile, stamped at closure, re-stamped on audited move | DEC-1, DEC-9, **DEC-21** · depends on 1b, 2b and 3. **State which is authoritative for disposal** |
> | **6** | **Disposition as a named act, then hold** | DEC-3 · ordering forced; file-level hold depends on 1b and 3 |
> | **7** | **Custody** — lock covers lifecycle, initiator holds custody, auto-submit capped at `PendingApproval`, assignment guards | DEC-4, DEC-6, DEC-7, Q-2 · **needs unit 9 first** or DEC-6 inherits the seam's defect |
> | **8** | **Declaration** — approval declares; declaration fixes content, not filing | DEC-5, DEC-17 · pairs with 2 |
> | **9** | **The pinned-vocabulary seam**, as one problem | AD-7/AD-17 · promoted — DEC-6 depends on it |
> | **10** | **Disposal action vocabulary**, gated on capability; `Transfer` enumerated and refused until export exists | DEC-12, DEC-19 · export deferred to its own review; unit 2's manifest is what it will need |
> | **11** | **Ten-year position** and the bounds derived from it | DEC-13 |
> | **12** | **Governance records freeze on close** — applies unit 2b rather than inventing its own path | DEC-8 |
> | **13** | **Un-archive, keeping the name reservation** | AD-12 |
> | — | **AD-21 is the review's residue** — cross-context guards are point-in-time where the domain needs standing constraints. Narrowed by DEC-10, DEC-11, DEC-16 and DEC-3, remedied by none. A design concept to add, not a defect to fix | — |
>
> The original ordering below is kept for its reasoning, which the revision draws on.

---

**Grouped by what has to move together, not by severity** — so the order below is not the severity order in
the verdict.

| # | Unit | Why here |
|---|---|---|
| **1** | **AD-28 — generalise the completeness rule** to cascades, query-service reads, aggregate-loaded relationships, sagas | Documentation only, conflicts with nothing, and it is what forces the answers the rest of this list needs. Doing it later means answering each question twice |
| **2** | **AD-29 — add a fixity value at capture** | **Cost rises with every object stored**, and it is the only finding whose remedy gets strictly more expensive the longer it waits. Independent of everything else |
| **3** | **AD-33 then AD-27 — repair capability, then the freshness contract** | **Ordering is forced**: AD-27's remedy changes the schema of the seven cross-context indexes, and a schema change to those is *"a manual in-place rebuild"* that AD-33 says no tool performs. The fix for AD-27 requires the capability AD-33 says is missing |
| **4** | **AD-32 — an operator surface** for counters, sagas, cascades and stale registrations | Pairs with 3 — same gap seen from the other side. AD-22 and AD-35 both become tractable once failures are visible |
| **5** | **AD-31 then AD-15 — bring `PurgeVersion` inside the disposition model, then hold** | **Ordering is forced**: a hold must be able to *refuse a disposition*, and until disposition is a named act there is nothing for a hold to gate. Both want the AD-26 answer first if a hold applies to a file rather than an item |
| **6** | **AD-1, AD-3, AD-4, AD-5 — the record's custody** | One unit: the three-machine split, the lock's reach, multi-member ordering (**Q-2** decided) and the declaration point (**Q-1** decided). They touch the same aggregate and the same session |
| **7** | **AD-8, AD-9, AD-13, AD-26 — the class/aggregation join** | The largest and the one to decide rather than to schedule — see the Open question below |
| **8** | **AD-7/AD-17 — the pinned-vocabulary seam**, as one problem | Ownerless today; MM-040 argues the four *"will not converge if fixed separately"* |
| — | AD-2, AD-6, AD-10, AD-11, AD-12, AD-14, AD-16, AD-18, AD-19, AD-20, AD-23, AD-24, AD-30, AD-34, AD-35 | Work on their merits, mostly small. **AD-14 is the exception — cheap now and immutable later**, since every item minted before the fix carries the wrong capability set forever |

### Direction conflicts — remedies that constrain other remedies

**Four found. Three are ordering constraints (folded into the table above); one is a trap.**

> ⛔ **AD-26's obvious remedy is wrong and must not be taken.** *"Containment has no authoritative
> representation"* reads like an argument for putting children on the parent. **It is not.** A folder
> holding its children is an unbounded aggregate, and the spec's rejection of a downward walk — *"that would
> be O(descendants) and would rest on a projection"* — is correct and should stand. The remedy is to **accept
> derived containment and give it what derived state needs**: a repair path (AD-33) and a freshness contract
> (AD-27). **AD-26 is therefore not a separate unit of work from 3 and 4** — it is the reason they matter.

- **AD-3's remedy must not guard reviewer commands.** Extending the lock to lifecycle transitions runs into
  a stated rule: *"Marking `ApproveReview` would make review impossible"*, and reviewer and system-internal
  commands are deliberately excluded. The fix has to distinguish an owner's lifecycle act from a reviewer's,
  which the current marker interface does not.
- **AD-14's one-line fix is right under either AD-13 outcome**, but do not let it imply the current shape is
  settled. If governance moves off `MediaProfile` (unit 7), the capability question changes shape — the fix
  is still correct, the reasoning behind it is not.

### Contradiction sweep

**No finding contradicts another.** Two pairs imply a third thing worth stating:

- **AD-29 + AD-33** — if a version-asset index is wrong about what a published version contained, there is
  no digest to detect it and no tool to rebuild it. **The error is undetectable and uncorrectable.**
- **AD-22 + AD-32** — a stalled registration is both unbounded in time and invisible to an operator, which
  is why it needs no malice to become permanent.

---

## Coherence record — Pass 9

**Three rounds; stable on the third.**

| Round | What changed |
|---|---|
| 1 | **AD-2 narrowed.** Q-3 legalised custodial operations on archived aggregates, so AD-2's residue is `PurgeVersion` alone — which is **AD-31**. AD-2 amended in place rather than superseded. **AD-5 narrowed** to *name the declaration point*, per Q-1 |
| 2 | **Root count went 4 → 5.** Pass 6's three did not account for AD-1 … AD-6, AD-18 and AD-23; a fifth root — *`MediaItem` carries several things and the lock protects one* — accounts for all eight. **AD-7 and AD-17 merged** into the pinned-vocabulary seam as one problem. **AD-12's cascade blanks** reassigned from root 1 to root 2 |
| 3 | **No changes.** Fixed point |

**Deliberately not collapsed.** **AD-15, AD-29, AD-30 and AD-31** are absent capabilities, not structural
faults, and three are top-five findings. Merging an absence into a structural pattern is how it stops being
visible, so they are kept as root 5 — *a root of a different kind, and labelled as one*.

**AD-24 sits outside all five roots** and is left there: `DocumentSigningSession` has no aggregate root, so
it is a design with no composition to be incoherent with. Cheapest finding in the review to act on, for the
same reason.

---

## Decisions on findings — the `findings-agreed` walkthrough

_Worked item by item with Chase, 2026-09-14. **Round 1 of 4 complete.** Each decision names the findings it
moves and what it leaves open. The coherence loop is re-run once all rounds land._

### ✅ DEC-1 — Retention attaches to the **item**, stamped at closure, defaulted from the profile

_Settles the class/aggregation join — **AD-8**, and part of **AD-13**. Domain owner: **Karen Barton**._

Three parts:

1. **The schedule is pinned on the `MediaItem`**, not resolved through `MediaProfile` and not inherited
   from `Folder`.
2. **`FolderClosed` stamps the closure date onto each contained item.** The clock becomes a fact the record
   holds — **not a live read of the current folder**. **Amended in round 2 (DEC-9): the stamp is re-applied
   on move**, so a re-filed record takes the disposal of the file it now sits in.
3. **The schedule is copied from the profile at creation**, by value, exactly as `SnapshotFields` works —
   with a per-item override available afterwards.

**Why this beat the three options the review put up.** Under **Q-1** the item is the record, so the
obligation belongs on the thing that bears it. It is also the only placement that makes **per-record
exceptions expressible** — legal hold and individual archival appraisal, both deferred by ruling 3 and both
needed by **AD-15**. On the profile or the folder there is nowhere for them to live. It handles heterogeneous
files honestly, which is the realistic case.

**Why stamping, and not the live read as first described.** A live read through the current folder keeps
AD-8's cross-hierarchy dependency alive in the trigger and leaves three move cases unruled: moving **into** an
already-closed folder starts a clock retroactively, possibly already elapsed; moving **out of** a closed
folder un-starts a started clock; moving between two closed folders re-dates to whichever file the item
currently sits in. Stamping dissolves all three and makes the date a fact rather than a replicated lookup —
which also takes this path out of **AD-27**'s scope.

**A naming collision produced a false disagreement and is worth recording.** The initial proposal was
*"retention belongs to the record type"*. In records practice that is correct — but **`RecordType` here is a
metadata element set**, citable and deliberately shared across profiles; the spec says a disposal rule
*"varies per record class, not per record type"*. The functional class the records sense means is closer to
`MediaProfile`, and neither is quite it: `MediaProfile` is a **format-and-structure contract** with
governance bolted on (AD-13), while records classification is **functional**. Item-level placement steps
around the collision rather than resolving it.

**What DEC-1 changes in the findings:**

| Finding | Effect |
|---|---|
| **AD-8** | **Substantially closes.** Rule and clock both become item-local |
| **AD-9** | **Changes shape.** Folder closure stops being a records concept with no behaviour and becomes the event that stamps |
| **AD-13** | **Partially closes.** Retention leaves `MediaProfile`; classification and security classification stay parked there |
| **AD-26** | **Unchanged.** Containment is still derived — and the closure stamp is a fan-out over a folder's items, so it inherits the completeness problem |

**Two things it does not settle.** **Longest-retention-wins is not needed and was not adopted** — precedence
is only required if a record can be under two disposal authorities at once, and one pinned schedule per item
makes that unconstructible, preserving the 2026-09-03 prohibition-over-precedence decision. And **it changes
D3's migration shape from MM-041**, which sequenced a *profile-level* gate behind per-tenant field
retirement; an item-level pin is a different migration and D3 should be revisited.

### ✅ DEC-2 — Fixity: a capture digest **and** a version manifest _(**AD-29**)_

A per-object digest computed at upload confirmation and stored immutably beside `StorageKey`, **plus** a
manifest of digests stamped onto the published version. Both, not either.

**What it buys.** The capture digest answers *"are these still the bytes that were filed?"*; the manifest
answers *"is this the set of objects that was approved?"* — which is what **AD-18** found is currently
emergent rather than stated, and what an archival transfer would have to hand over. **This is the remedy
whose cost rises with every object stored**, so it is sequenced early regardless of severity order.

### ✅ DEC-3 — Full hold model now _(**AD-15**, **AD-31**)_

A first-class hold that applies to an item or a whole file, survives archive, and blocks disposition and
deletion — together with bringing `PurgeVersion` inside the model as a named, authorised, recorded,
**refusable** disposition act.

**Ordering is forced and unchanged:** disposition becomes a named act first, then hold gates it. Until
`PurgeVersion` is inside the model there is nothing for a hold to refuse.

⚠ **This pulls units 3 and 4 forward.** A hold over a **file** requires containment to be authoritative, and
per **AD-26** it is not — so DEC-3 depends on the repair path (**AD-33**) and the freshness contract
(**AD-27**) that the sequencing had placed after it. **Carried into the re-run as a direction conflict.**

### ✅ DEC-4 — The lock covers custody; the session initiator holds it _(**AD-3**, **AD-4**)_

`Publish`, `Withdraw`, `Archive` and `Move` become guarded while a session is open. Reviewer commands
(`ApproveReview`, `RejectReview`) and system-internal commands stay unguarded — *"marking `ApproveReview`
would make review impossible"*.

**And the custody model is now explicit**, which the spec never stated:

> **The member who opens the session takes custody.** Additional members may be added and may make
> **content and metadata changes**; they **may not perform lifecycle acts**. Custody is singular even when
> editing is collaborative.

**This is the answer AD-4 was missing.** Q-2 settled *how* concurrent edits are ordered — mandatory
`If-Match` for multi-member sessions. DEC-4 settles *who may end the session's subject*, which is the
question a records officer actually asks. Together they make "one or more users" a coherent claim rather
than a partial one: **many editors, one custodian.**

### ✅ DEC-5 — **Approval declares the record** _(**AD-5**)_

`MediaItemApproved` is the declaration point. From that moment the version is fixed, its asset manifest is
stamped (DEC-2), and content changes require a new version.

**Why approval and not a separate act.** It is the only transition that already mints a version, promotes
its assets to `VersionArtifact` and has a review behind it — **the machinery exists and was unnamed**. A
separate `Declare` command would add a fourth state machine to an aggregate that already has three (AD-1).

⚠ **Immediate-publish declares too.** `RequestPublication` with an empty reviewer list goes straight to
`Published`, so declaration can occur with no reviewer. **This is what makes DEC-6 necessary** and must be
stated explicitly in the spec rather than left as a consequence.

### ✅ DEC-6 — Auto-submit may submit, never declare _(**AD-1**, part 1)_

`AutoSubmitOnComplete` may move an item `Draft → PendingApproval` and **no further**. Where `ReviewPolicy`
is `None` and no reviewers exist, it does nothing rather than publishing immediately.

**This decision exists because DEC-5 changed the stakes.** Auto-submit fires from **three** content handlers
— assign-to-folder, assign-asset-to-role, set-metadata-batch — each dispatching `PublishMediaItemCommand` as
`owner_system`. With approval declaring, *"a metadata write can take an item `Draft → Published`"* becomes
**a metadata write can declare a record with no human act anywhere in the chain**.

> **It also resolves a direction conflict between two decisions taken an hour apart.** DEC-4 guards
> lifecycle acts while a session is open but deliberately exempts system-internal commands — so
> `owner_system` auto-submit would have **published a record out from under its custodian**, which is
> exactly what DEC-4 exists to prevent. Capping auto-submit at `PendingApproval` closes that route.

**Side effect worth having:** it also closes D-7's *"the publish path never reads the profile's
`ReviewPolicy`"*, since auto-submit must now consult it to know whether to act at all.

### ✅ DEC-7 — Folder assignment: hold blocks, custody blocks, **archive does not** _(**AD-1**, part 2)_

Every move is audited with a reason. No move while under hold (DEC-3). No move while an edit session is open
(DEC-4). **Archived items remain movable** — with Q-3's released-title-reservation defect fixed, as Q-3
already requires.

> **The review's first recommendation here was wrong and is withdrawn.** It proposed blocking moves on
> archived items. **Common EDRMS practice permits re-filing closed and archived records** as a privileged,
> audited act reserved to records administrators — because **mis-files are discovered during appraisal,
> which happens after closure**. Blocking it is stricter than the field and would have reversed Q-3. What
> practice guards instead is *hold* and *audit*, which is what DEC-7 adopts. Recorded because the first
> recommendation over-indexed on a mechanical defect rather than the domain.

**Check-out is genuinely split in the field** — some systems treat it as a content lock only and permit
administrators to re-file, notifying the holder. DEC-7 takes the stricter reading because **DEC-1 makes
filing affect the custodian's own disposal clock**, which is not true in systems where that split is benign.

### ✅ DEC-8 — Governance records freeze on close, with an explicit correction act _(**AD-23**)_

A resolved or abandoned `ChangeRequest` accepts no further comment edits or deletions. Corrections are made
by an **explicit, attributed act that appends rather than overwrites**.

**Why not simply freeze.** People do need to correct a governance record, and a flat freeze pushes that
need somewhere worse. An append-only correction keeps the original legible, which is what a reader of *why
this change was made* actually needs. **Note this is a concept nothing else in the model has yet** — the
first append-only correction path on the platform, and worth designing once rather than per-aggregate.

### ✅ DEC-9 — A re-filed record takes the disposal of the file it now sits in _(amends **DEC-1**)_

Moving an item **re-stamps** its closure clock: cleared if the destination folder is open, re-stamped if the
destination is closed. **Every change to a disposal clock is audited with the move that caused it.**

**Why this reverses the round-1 answer.** DEC-1 first chose *first closure wins, moves never re-date*.
Common practice is the opposite — **a re-filed record takes the disposal of its new file, because it now
documents a different activity** — and the round-1 rule is wrong for the case that motivates most moves:
a **mis-file correction**, where the record was never really in the first file at all and correcting the
filing could not correct the disposal.

⚠ **This is the review's one moving clock, and it needs its own audit trail.** A disposal date that can
change is acceptable only if every change is attributable to an act. DEC-7's audited move is where that
lives.

### ✅ DEC-10 — Build repair, then freshness _(**AD-33**, **AD-27**)_

A rebuild path for the seven cross-context reference indexes and a seeding pass for the two counters —
**then** a source-relative version on reference rows, so a guard can refuse stale evidence.

**Ordering is forced and was found by the direction-conflict sweep:** AD-27's remedy changes the schema of
those indexes, and a schema change to them is *"a manual in-place rebuild"* that **no tool performs**
(AD-33). The fix for AD-27 requires the capability AD-33 says is missing.

**DEC-3 promoted this from follow-up to prerequisite.** A hold that applies to a **file** needs containment
to be authoritative, and per AD-26 it is derived with no repair path — so a file-level hold built on today's
substrate would **silently miss records**, which is worse than no hold.

**It also closes the dated position.** The repair rule is currently satisfiable only by *"record that no
affected data exists"*, which holds only while `PROD_ENABLED` and `STAGING_ENABLED` are unset. DEC-10 makes
the first option real before that stops being true.

### ✅ DEC-11 — Operator surface: read-only inspection first _(**AD-32**)_

Expose the derived state — counter values, saga status, cascade reports, stale registrations — **before**
building anything that writes to it.

**Why inspection first.** Most incidents need diagnosis, not repair; read-only cannot corrupt an
invariant-backing value by hand; and **it tells you which repair tools are worth building** rather than
guessing. It also ends the position the spec currently leaves operators in — forbidding the manual
workaround (*"Do not edit the saga row to a terminal status directly"*) while providing no supported path.

**Pairs with DEC-10**, which supplies the repair half. **AD-22** (stalled registrations, invisible and
unbounded) and **AD-35** (three mechanisms that ack-and-continue) both become tractable the moment failure
is visible — neither needs its own remedy first.

### ✅ DEC-12 — Enumerate disposal actions and gate them on capability _(**AD-30**)_

Write the action table with a readiness column, and apply the analogue of the trigger rule: **a disposal
action must name an operation the platform can perform.** Authoring a schedule that pins an unperformable
action is **refused**, exactly as D4 gated `Superseded` and `Closure` on their missing timestamps.

**This is D4's argument on the axis nobody checked.** The trigger vocabulary got six rows, a readiness
column and a rule; `action` was declared *"a domain enum, closed by construction"* and its members were
never written down. Against the test: `RetainPermanently` ✅, `Review` ❌ (no workflow), `Transfer` ❌ (**no
export exists anywhere in the platform**), `Destroy` — via DEC-3's named disposition act.

**Consequence worth stating:** `Transfer` cannot ship until an export exists, and **DEC-2's version manifest
is what an export would have to carry** to be attestable. The two are the same piece of work seen from
either end.

### ✅ DEC-13 — State a ten-year position, and derive the bounds from it _(**AD-34**)_

Write what a large tenant looks like after a decade — the platform's own statutory default — and derive the
missing bounds from that: a saga-row TTL, a stale-registration sweep, a partition strategy for job
summaries.

**Why a position rather than three fixes.** Every stated limit in the model today came from a runtime
constraint — an API Gateway timeout, a DynamoDB item size, an event-replay cost — and each is well reasoned
on those terms. **None came from the domain.** Retention is the only timescale a records platform operates
on, and the model has no stated view of it, which is why the unbounded quantities are exactly the ones a
records tenant accumulates.

### ✅ DEC-14 — The remaining fourteen findings accepted as stated

**AD-2, AD-4, AD-6, AD-10, AD-11, AD-16, AD-18, AD-19, AD-20, AD-21, AD-22, AD-24, AD-25, AD-35** agreed as
findings with the remedies the review describes. None needed a judgement call — each is either mechanical
(project `FailureCategory`; fix the deprecation projector) or already determined by DEC-1 … DEC-13.

### ✅ DEC-15 — Adopt AD-28 and sequence it first

Generalise MM-041's completeness rule to **cascades, synchronous query-service reads, aggregate-loaded
relationships and sagas**. Sequenced ahead of everything else: it forces the answers the rest of the list
needs, **including the four `cascade-rules.md` rows with no rule at all — which is where AD-20 actually gets
settled.** Doing it later means answering each question twice.

### ✅ DEC-16 — Make the containment projection faithful _(**AD-26**)_

Feed `FolderMediaItemsIndex` and `FolderFoldersIndex` from the **complete** MediaItem event set — created,
**assigned, moved, archived, deleted** — not `MediaItemCreated` alone; and make the CLI **clear** them before
replay.

> **The review under-called this finding and the correction matters.** AD-26 grouped containment with the
> unrebuildable state. **It is not.** These two indexes are **same-module**, fed by Catalog's own domain
> events — they are *not* among the seven cross-context indexes with no rebuild path — and **`media-item` is
> one of the six aggregates the CLI already replays.** Containment is blocked by two specific fixable things,
> not by its nature: an **add-only projector**, and a CLI that *"does not clear"* same-module indexes.

**Why this is the right shape.** `MediaItem.FolderId` **is already authoritative** — the item knows its
folder, and that is correct aggregate design (the Pass 9 trap: putting children on the parent would make an
unbounded aggregate). Only the *inverse view* is derived. DEC-16 makes that view a **faithful projection of
authoritative state, reconstructible on demand** — which is a stronger property than DEC-10's *trustworthy*,
and it needs no model change.

**It is DEC-15 and DEC-10 applied to one index.** The completeness rule forces the full producing event set;
the rebuild work makes it clearable. Nothing new is invented.

**What it does for the decisions that rest on it:**

| | |
|---|---|
| **DEC-1** — the closure stamp fans out over a folder's contents | The fan-out reaches items **assigned after creation**, which the add-only projector misses today |
| **DEC-3** — a hold applying to a whole file | A hold can assert its coverage, rather than covering whatever the index happens to hold |
| The archive cascade | `IsComplete` becomes a claim about the **tree** rather than about the index |

⚠ **One consequence survives and should be stated rather than assumed.** The projection is still eventually
consistent, so an operation over an aggregation is still a point-in-time read — DEC-10's freshness contract
is what bounds that, and **AD-21's standing-constraint problem is not solved by DEC-16.** Faithful is not
synchronous.

### ✅ DEC-17 — Declaration fixes content, not filing _(clarification the decisions require)_

The spec must state it in those words. A declared version's **content** is fixed — assets, metadata, the
stamped manifest (DEC-2). Its **filing** is not: a declared record may be re-filed, and DEC-9 re-stamps its
disposal clock when it is.

**Re-filing is the same act whether or not the record is declared** — a privileged, audited act gated by
hold and custody per DEC-7, with no additional guard for declared records.

**Why not make the declared case harder.** Mis-files are discovered during **appraisal, which happens after
declaration** — so an extra guard on the declared case penalises precisely the case that occurs. **The audit
trail is what makes it safe, not a second gate.** It also avoids the per-case rule-making AD-25 was raised
about.

### ✅ DEC-18 — MM-041 stays closed; the plan from this review corrects the spec

**DEC-1 supersedes D3's placement.** D3 (MM-041, closed `done` 2026-09-14) sequenced a **profile-level**
retention gate behind a per-tenant field retirement; DEC-1 makes retention **item-level**, which is a
different migration. MM-041 is **not** reopened and no correction note is added now — the plan that comes
out of this review rewrites the retention text and carries the corrected migration.

> ⚠ **Accepted risk, stated so the plan inherits it as its first item.** Until that plan lands, the spec in
> `mgq-magiq-media` describes **two incompatible retention placements with nothing saying which wins** —
> D3's profile-level gate and DEC-1's item-level pin. That is the same defect class this review found
> repeatedly (AD-16, AD-25: one question, two answers). **The window is the risk, not the choice**, so the
> plan should open with the retention text rather than reach it in sequence.

### ✅ DEC-19 — Defer export; ship `Transfer` gated off _(**AD-30**, refines DEC-12)_

`Transfer` is enumerated in the disposal action vocabulary and **authoring a schedule that pins it is
refused until an export exists** — exactly as D4 gated `Superseded` and `Closure` on their missing
timestamps.

**Why gate rather than drop.** Widening an enum pinned into immutable published versions is the change this
design exists to avoid. Gating keeps the vocabulary whole without letting an unperformable rule reach a
version. **Export is a substantial capability and deserves its own review**, not a corner of this one — and
DEC-2's version manifest is what it will need to be attestable, so the two meet when it is taken up.

### ✅ DEC-20 — Design correction-by-append once, as a shared concept _(**AD-23**, generalises DEC-8)_

Specify it generically — **attributed, reason-bearing, never overwriting** — and apply it to change-request
comments first.

**Four places already want the same shape**, which is why it is designed once rather than per-aggregate:
DEC-8's comment correction, **DEC-7's audited move**, **DEC-9's clock re-stamp**, and **DEC-3's record of a
disposition act**. Per-aggregate design here produces four slightly different correction models, which is
root 2 in miniature — each locally reasonable, incoherent as a set.

### ✅ DEC-21 — Classification moves to the item as well _(closes **AD-13**)_

Following DEC-1's pattern: **copied from the profile at creation, pinned by value, overridable afterwards**.

**This fully closes AD-13.** With retention (DEC-1) and classification both on the item, `MediaProfile`
returns to being what its own spec says it is — *"the structural contract for a `MediaItem` type"* — and
stops being a record class with governance bolted on.

**The review recommended against this and was too cautious.** The objection was that classification is
*functional* and attaches to a class or a file rather than an instance. That is right about **where
classification is authored** and wrong about **where it is carried**: in EDRMS practice a record carries its
classification, normally inherited at filing. **Inherited-and-carried is exactly DEC-1's pattern**, so
DEC-21 is the consistent choice, not the departure.

**Security classification follows the same placement when it is built.** It is unmodelled today
(`Metadata/context-overview.md:48-52`), so nothing is decided about its content — only that it will sit
where classification sits.

> ⚠ **New interaction the spec must settle — surfaced by the round-4 sweep.** In records practice
> **retention derives *from* classification**. DEC-1 and DEC-21 put both on the item **independently**, each
> copied from the profile, each separately overridable — so an item can carry a classification saying one
> thing and a pinned schedule saying another, with nothing reconciling them.
>
> **The review's reading: the pinned schedule is authoritative for disposal and the classification is
> descriptive**, because a schedule is versioned, cites an authority and is what an auditor acts on. **But
> the spec must state it**, and it must say what happens when a records officer changes one without the
> other. Left as a spec obligation rather than reopened — it is a statement to write, not a fork.

---

## Coherence re-run — after the decisions

**Two rounds; stable on the second.** Run against DEC-1 … DEC-15.

### Contradictions

**None among the decisions.** DEC-9 amends DEC-1 rather than contradicting it, and DEC-6 was created
*by* the sweep to resolve the DEC-4 / auto-submit conflict before it reached this point.

**One clarification the decisions require and none of them states:**

> **Declaration fixes content, not filing.** DEC-5 fixes a version at approval; DEC-7 and DEC-9 allow a
> declared record to be re-filed and its disposal clock re-stamped. Both are right — re-filing does not
> alter the record, it alters which aggregation it belongs to — but a reader will assume "fixed" covers
> both. **The spec must say which.**

### Direction conflicts — two new, both promotions

1. **DEC-10 now underpins DEC-1 as well as DEC-3.** The closure stamp is a fan-out over a folder's items,
   and the re-stamp on move is per-item — so both depend on containment being trustworthy, and per AD-26 it
   is derived with no repair path. **DEC-10 was already a prerequisite for the file-level hold; it is now a
   prerequisite for the retention clock too.** It moves to the front of the structural work.
2. **DEC-6 lands on the pinned-vocabulary seam.** Auto-submit must consult `ReviewPolicy` to know whether to
   act — and `ReviewPolicy` is one of the capabilities pinned into immutable versions that gates nothing
   (DF-8), inside the ownerless seam AD-7/AD-17 covers. **DEC-6 cannot be implemented cleanly before that
   seam is addressed**, or it inherits the defect.

### One finding got smaller

**AD-14 partially defuses.** Its sharpest consequence was that a record could be governed by a retention
schedule it did not advertise, because the item carries the *compiled* capability union rather than the
*declared* set. **DEC-1 pins the schedule on the item directly**, so retention no longer depends on the
capability reaching it. AD-14 stands for `Processing` and for the general defect — it is no longer a
governance finding.

### Root-cause collapse — the roots hold, four of five now have remedies

| Root | State after the decisions |
|---|---|
| **1 · Class / aggregation** | **Reduces to AD-26.** DEC-1 closes AD-8, reshapes AD-9, partially closes AD-13 — and leaves containment derived |
| **2 · No owner of compositions** | **Remedied at source** by DEC-15; members stand as work |
| **3 · Instants vs durations** | **Largely remedied** — DEC-10 (freshness), DEC-11 (visibility), DEC-13 (a domain timescale). AD-21 stands |
| **4 · Absent records capabilities** | **All four now have remedies** — DEC-2, DEC-3, DEC-12. The root changes character from *absence* to *scheduled work* |
| **5 · `MediaItem` custody** | **Largely remedied** — DEC-4, DEC-5, DEC-6, DEC-7, DEC-8, Q-2 |

### The re-run's headline

> **AD-26 rose from fourth to first, and then was remedied.** It rose because **two decisions came to rest
> on it** — DEC-1's closure stamp and DEC-3's file-level hold both assume you can trust what is in a folder.
> It was then closed by **DEC-16**, once the review's own characterisation of it turned out to be wrong:
> containment is a *same-module* projection of authoritative state, not one of the unrebuildable
> cross-context indexes, and `media-item` already replays.
>
> **DEC-10 remains the first structural unit of work** — ahead of the hold and ahead of the clock — because
> the freshness contract still bounds what any point-in-time read over an aggregation can claim. **DEC-16
> makes containment faithful; it does not make it synchronous**, and AD-21's standing-constraint problem is
> untouched by either.

**Round 2: no further changes. Fixed point.**

### Round 3 — after DEC-16 and DEC-17

Re-run required because DEC-16 closed a root. **One round; stable.**

- **No new contradictions.** DEC-16 strengthens DEC-1, DEC-3 and the archive cascade without altering any
  other decision.
- **Root 1 closes.** Its residue was AD-26; DEC-16 remedies it. **All five roots now have remedies.**
- **AD-21 is now the largest finding with no decision against it** — cross-context guards are point-in-time
  where the domain needs standing constraints. DEC-10's freshness contract lets a guard *know* a fact is
  stale; nothing yet lets a relationship *require* a fact to remain true. **Recorded as the review's
  residue rather than reopened**: it is a design concept, not a defect, and the four remedies that touch it
  (DEC-10, DEC-11, DEC-16, DEC-3's hold) narrow it substantially.
- **DEC-17 removes the last ambiguity** the decisions created between fixity and filing.

### Round 4 — after DEC-18 … DEC-21

**One round; stable.** All four are consequences of earlier decisions rather than of findings.

- **AD-13 closes.** DEC-21 moves classification to the item alongside DEC-1's retention, so `MediaProfile`
  returns to being a structural contract. **Root 1 is now fully closed** rather than closed-with-residue.
- **One new interaction, recorded as a spec obligation rather than a fork:** retention derives *from*
  classification in practice, and DEC-1 and DEC-21 place both on the item **independently**. The pinned
  schedule is authoritative for disposal; the classification is descriptive; **the spec must say so** and
  must say what happens when one is changed without the other. See the note under DEC-21.
- **DEC-20 absorbs three findings' remedies into one concept** — DEC-7's audited move, DEC-9's clock
  re-stamp and DEC-3's disposition record all want correction-by-append. **This is root 2 being remedied
  prospectively** rather than after the fact, which is the first time in this review that has happened.
- **DEC-18 accepts a stated risk rather than resolving one.** Until the plan lands, the spec carries two
  incompatible retention placements. **Recorded as the plan's first item**, not as a finding.

**No contradictions. Fixed point on the findings — and the register is empty.**

### Round 5 — the sequencing sweep

**Run because round 4 checked contradictions and roots and *did not re-check the sequencing table* against
DEC-18 … DEC-21.** It should have. Three errors, all introduced by the decisions themselves:

1. **DEC-20 was sequenced last and is a prerequisite for four earlier units.** Correction-by-append is
   wanted by DEC-7's audited move (unit 5), DEC-3's disposition record (unit 6), DEC-9's clock re-stamp
   (unit 5) and DEC-8's comment correction (unit 12) — but it sat at unit 12 with its own consumer.
   **Promoted to 2b.** Designing it once was the whole point of DEC-20; leaving it last would have produced
   the four divergent models it exists to prevent.
2. **DEC-21 was not in the sequencing at all.** Classification moving to the item is work, and it pairs
   with DEC-1's retention pin — same aggregate, same copied-from-profile pattern, same override path.
   **Folded into unit 5.**
3. **DEC-18 conflated two different acts.** *"The plan should open with the retention text"* means
   **correct the spec**, which is cheap and immediate; it does not mean **build item-level retention**,
   which is unit 5. Separating them is what makes DEC-18's accepted risk actually closeable early.
   **Split out as unit 0.**

**One finding shrank again.** **AD-14** was partially defused by DEC-1 (retention stopped depending on the
capability reaching the item); **DEC-21 does the same for classification**. With both governance concerns
now pinned directly on the item, AD-14 is **purely a `Processing` defect** — the compiled-vs-declared
divergence still matters, but no governance decision rests on it any more.

**Round 6: no changes. Fixed point.**

> **Worth recording about the method.** Five of the six loop rounds changed something, and **round 5 caught
> errors the review itself had introduced rather than errors in the model.** A coherence loop that only ever
> re-reads the findings will miss those — the sequencing and the roots have to be swept too, because they
> are derived artefacts and decisions invalidate them the same way they invalidate findings.

---

## Pass 10 — the decided design

**A different artifact from the one Passes 0–9 reviewed.** DEC-1 … DEC-21 move retention and classification
to the item, add hold and fixity, change custody, cap auto-submit and generalise two rules. **The plan will
implement this model, not the one that was reviewed**, and it had not been interrogated. Findings prefixed
**`DD-`**.

---

### DD-1 · High — A record can be declared with no human review

**The decided design.** DEC-5 makes `MediaItemApproved` the declaration point: the version is fixed, its
manifest stamped, retention begins. But `RequestPublication` **with an empty reviewer list goes straight to
`Published`** — so declaration can occur with **zero reviewers**.

**What follows.** In a compliance product, a record becomes fixed and enters a statutory retention schedule
with **no human attesting to it**. DEC-5 recorded this as something the spec "must state explicitly"; that
was the wrong disposition. **Stating it does not make it acceptable — it makes it documented.**

**And the control that would prevent it does not work.** `ReviewPolicy = RequiredForPublish` is the profile
setting that would require reviewers, and it is one of the **seven capabilities that gate nothing** — D-7
records that *"the publish path never reads the profile's `ReviewPolicy`"*. DEC-6 fixes that **for
auto-submit only**; the explicit publish path is untouched.

**This is the sharpest issue the decisions created**, because declaration did not exist when the review ran.
It needs a decision: either declaration requires at least one reviewer, or `ReviewPolicy` becomes real on
the publish path, or the design accepts self-declared records and says why.

---

### DD-2 · High — The closure fan-out is a third unnamed process manager

**The decided design.** DEC-1 stamps the closure date onto **each contained item** when a folder closes, and
DEC-9 re-stamps on move.

**What follows.** That is a **fan-out over a folder's contents** — structurally identical to
`CollectionArchiveFanOutWorker` and `FolderArchiveFanOutWorker`, which `saga-patterns.md:142-147` describes
as *"**sagas without the name**… Neither has state, a correlation key, a resume path, a timeout, a status
surface or a test"*. **The decided design adds a third**, and no decision says it should be a saga.

**The stakes are higher than the existing two.** An incomplete archive cascade leaves items un-archived —
visible, and re-runnable once DEC-11 lands. **An incomplete closure stamp leaves records with no disposal
clock at all**, silently, and DEC-11's read-only surface would show a folder that closed successfully.

**This is the review's own root 2 reproduced by its own decisions** — a mechanism added without anyone
owning the question *what kind of process is this?*. DEC-15's generalised completeness rule is the thing
that should have caught it, which is an argument for sequencing it first, as unit 1 already does.

---

### DD-3 · High — A hold that cannot be enumerated cannot be certified

**The decided design.** DEC-3 gives a first-class hold that applies to an item or a file, survives archive,
and blocks disposition and deletion.

**What no decision says.** Who places it; who may lift it; whether it expires; and — the operative one —
**how anyone lists what is currently held.** DEC-11's read-only operator surface names counters, saga
status, cascade reports and stale registrations. **It does not name holds.** DEC-13's ten-year position does
not say what a hold outliving a saga TTL does.

**What follows.** The entire purpose of a litigation hold is to be able to **attest** — *these records are
preserved, here is the list, here is when it was applied*. A hold that blocks a disposition it will
probably never face, and cannot produce that list, satisfies the mechanism and not the obligation.

**Cheap to fix now and expensive later**, because the enumeration is a read model and read models are what
DEC-10 and DEC-16 are already building. **Add holds to DEC-11's surface** and the finding closes.

---

### DD-4 · Medium — Two governance facts on the item, independently overridable, with nothing reconciling them

**The decided design.** DEC-1 pins the retention schedule on the item; DEC-21 pins classification. Both are
copied from the profile at creation and **both are separately overridable**.

**What follows.** In records practice **retention derives *from* classification**. Here they are siblings.
Re-classify an item and nothing says whether its schedule follows; override a schedule and nothing says
whether the classification still describes it.

DEC-21 recorded this as *"a statement to write, not a fork"*, with the reading that the **schedule is
authoritative for disposal and the classification descriptive**. That reading is right and **it is still a
finding**, because the decided design has two facts that can disagree with no rule reconciling them —
**which is precisely root 2**, reproduced by the decisions that were meant to close root 1.

**It is the cheapest of the four to close**: state the derivation, and make re-classification either
re-derive the schedule or refuse while an override is in force.

---

### DD-5 · Medium — "Overridable" is specified as a capability, not as an act

**The decided design.** DEC-1 and DEC-21 both end *"overridable afterwards"*. **Neither says what an
override is.**

**What follows.** Overriding a record's retention or its classification is a records-authority decision with
legal weight — the kind of act that must carry **who, when, why, and against what prior value**. Specified
as a property, it is a field write.

**DEC-20 already built the answer and nothing connected it.** Correction-by-append — *attributed,
reason-bearing, never overwriting* — is exactly this shape, and DEC-20 names three consumers (DEC-7's move,
DEC-9's re-stamp, DEC-3's disposition record) **without naming the two overrides**. Adding them costs
nothing and is the difference between an override that is auditable and one that is not.

---

### DD-6 · Low — Auto-submit goes inert for the tenants most likely to use it

**The decided design.** DEC-6 caps auto-submit at `PendingApproval` and, *"where `ReviewPolicy` is `None`
and no reviewers exist, it does nothing rather than publishing immediately"*.

**What follows.** A tenant with no review process — typically a small one — loses the feature entirely
rather than having it change. That is the right safety answer and a silent product regression, and **the two
should not be conflated**. Worth stating in the spec and worth telling those tenants; it is the only
decision in the set with a user-visible behaviour change that nothing announces.

---

### Decisions on Pass 10

### ✅ DEC-22 — `ReviewPolicy` becomes real on the publish path, and declaration records how it happened _(**DD-1**)_

`PublishMediaItemHandler` reads the profile's `ReviewPolicy`. A profile set to `RequiredForPublish`
**cannot self-declare** — an empty reviewer list is refused. Where the policy is `None`, self-declaration is
permitted and **the declaration records that it was unreviewed**.

**Why this and not a blanket reviewer requirement.** The control already exists, is pinned into immutable
versions, and simply **is not read** — D-7. Making it authoritative puts the choice where it belongs, with
the tenant's records authority, and legitimate self-declared records (routine correspondence, auto-captured
system records) keep working without mandatory review that adds friction and no governance.

**The attestation half is the part that makes it safe either way.** A declared record carries whether it was
reviewed and by whom, so "unreviewed" is a recorded property rather than an absence — which is what an
auditor needs and what a silent empty-reviewer-list path could never provide.

**Closes D-7 on the publish path.** DEC-6 closed it for auto-submit only; the two together retire the
finding.

### ✅ DEC-23 — The closure stamp is built as a real saga _(**DD-2**)_

State, correlation key, timeout, resume path and a status surface — the properties `AssetIngestionSaga` has
and the two archive fan-out workers do not.

**Why the platform's own good pattern rather than its bad one.** The failure mode is **worse than the
archive cascade's**: an un-archived item is visible and re-runnable once DEC-11 lands, while **a record with
no disposal clock is invisible** — and a folder that reports closed successfully looks correct. A silent
partial stamp produces records that will never become due, which is the failure a retention system exists to
prevent.

⚠ **It also means the decided design must not add a third nameless fan-out** while the review's own finding
says two already exist. **DEC-15's generalised completeness rule is what should catch the next one**, which
is an argument for unit 1 staying first.

### ✅ DEC-24 — DD-3, DD-4, DD-5 and DD-6 fold into units already sequenced

| Finding | Folds into |
|---|---|
| **DD-3** — holds cannot be enumerated | **Unit 4**, DEC-11's read-only surface. A hold list is a read model, and units 3 and 1b are already building read models |
| **DD-4** — classification and schedule can disagree | **Unit 5.** State the derivation: the schedule is authoritative for disposal, the classification descriptive, and re-classification either re-derives the schedule or is refused while an override is in force |
| **DD-5** — "overridable" is a capability, not an act | **Unit 2b**, DEC-20's correction-by-append, with the retention and classification overrides added as named consumers |
| **DD-6** — auto-submit goes inert where `ReviewPolicy` is `None` | **Unit 7.** State it in the spec and announce it — the set's only user-visible behaviour change |

**None needs a new unit.** Three cost nothing because the machinery is being built anyway.

---

### Loop on Pass 10 — one round, then stable

- **No contradictions with DEC-1 … DEC-21.** All six are gaps in the decided design, not conflicts within it.
- **The pattern across DD-2, DD-4 and DD-5 is the same one**: a decision solved its own problem and did not
  ask what it added to the system. **That is root 2**, and it is worth noticing that a set of decisions
  taken to remedy a root can reproduce it.

### Loop after DEC-22 … DEC-24 — one round, stable

- **No contradictions.** All three close findings without disturbing DEC-1 … DEC-21.
- **DEC-22 retires D-7 jointly with DEC-6** — auto-submit and the explicit publish path were the two halves
  of *"the publish path never reads the profile's `ReviewPolicy`"*, and each was closed by a different
  decision an hour apart. **Neither alone would have closed it**, which is the kind of half-fix the
  completeness rule exists to prevent.
- **DEC-23 adds a fourth consumer to unit 1's rule.** A saga is a relationship mechanism, so the generalised
  completeness rule now has to answer *what kind of process is this* for the closure stamp as well —
  strengthening rather than complicating unit 1.
- **One sequencing consequence:** DEC-23 makes unit 5 larger than the table implies. The retention pin is a
  field change; the closure stamp is now **a saga with the full apparatus**. Unit 5 should be read as two
  pieces, and the saga piece depends on unit 1b (faithful containment) more strongly than the pin does.
- **Nothing further. Fixed point — and the decided design is now reviewed.**

---

## Wave log

| Pass | Date | Covered | Outcome |
|---|---|---|---|
| 0 | 2026-09-14 | Full aggregate + relationship inventory across all six contexts and the shared/architecture specs | Map complete. No findings, by design |
| 1 | 2026-09-14 | `MediaItem` | **AD-1 … AD-7** raised; Q-1, Q-2, Q-3 opened. AD-1 identified as the root that AD-2, AD-3 and AD-5 instantiate |
| 1b | 2026-09-14 | **Q-1, Q-2, Q-3 answered by Chase** | AD-5 narrows to *name the declaration point*. AD-2 and AD-4 gain committed directions. **Q-4 opened** — the first cross-decision interaction this review has produced: Q-1 and Q-3 are consistent only if `PurgeVersion` is disposition, and no disposition authority exists to authorise it. U-5 on `Collection` closes on Q-3's terms |
| 2 | 2026-09-14 | `Collection`, `Folder` — the hierarchy and the file plan | **AD-8 … AD-12** raised. The pass question — *does the hierarchy carry file-plan semantics or only containment?* — resolved to **containment only**, and AD-8 is the consequence: the disposal **rule** comes from the profile and the disposal **clock** from the folder, with nothing connecting them. AD-11 closes U-5 on Q-3's terms |
| 3 | 2026-09-14 | `MediaProfile`, `RecordType`, `RetentionSchedule` — the record class | **AD-13 … AD-17** raised. `RecordType` itself raised nothing — findings are about what crosses its boundary. **AD-15 (legal hold inexpressible) is the current candidate for top finding.** AD-7's pinned-vocabulary seam taken as one problem and closed into AD-17 |
| 4 | 2026-09-14 | `Asset`, `ProcessingJob` — **run as a control** | **AD-18 … AD-20** raised. **Control result: negative, as hoped.** Almost nothing here fits the class/aggregation root — AD-18 reaches the records lens only through `MediaItem`. Confirms that statement is a *records-axis* root, not a universal one. `AssetIngestionSaga` raised nothing |
| 5 | 2026-09-14 | `Registration`, `ChangeRequest`, `DocumentSigningSession` | **AD-21 … AD-24** raised. **AD-21 generalises what DF-3's fix actually was** — point-in-time vs standing constraints — and finds the same shape unexamined in rules 6 and 12. **AD-22 is a second, un-closed path to DF-1's outcome.** One **correction against MM-040's DF-17** recorded in AD-23 and routed to MM-022 |
| 6 | 2026-09-14 | **The relationships** — the main event | **AD-25 … AD-28** raised. **All three candidate roots survived their first real test**, and AD-26 and AD-27 are each a root seen from the relationship side. **AD-28 is the highest-leverage single fix in the review** — the only one whose remedy makes the *next* defect visible rather than closing one that exists |
| 7 | 2026-09-14 | **The records lens, end to end** | **AD-29 … AD-31** raised and **the records verdict written**. **AD-29 (no fixity value anywhere) is new and is the only absence in the review with no partial answer in the tree.** **Q-4 answered by AD-31**: `PurgeVersion` is disposition by elimination, and sits wholly outside the disposition model. AD-15 confirmed as a top finding, not downgraded |
| 8 | 2026-09-14 | **Robustness of the design** | **AD-32 … AD-35** raised. **AD-32 and AD-33 are the same gap twice** — the model can neither show you its derived state nor rebuild it. AD-33 also finds the repair position **silently depending on nothing being in production**, which is a dated position rather than a rule. AD-35 is the composition pattern at its most operationally costly |
| 10 | 2026-09-14 | **`findings-agreed` walkthrough with Chase — 4 rounds** | **DEC-1 … DEC-15.** Every finding agreed. Two review recommendations **withdrawn on domain grounds** (DEC-7 archive-blocks-move; DEC-9 first-closure-wins). **DEC-6 created by the sweep** to resolve a conflict between two decisions taken an hour apart. Domain owner **Karen Barton** consulted on DEC-1 |
| 16 | 2026-09-14 | **Pass 10 decided** | **DEC-22 … DEC-24.** `ReviewPolicy` becomes real on the publish path and declaration records whether it was reviewed; the closure stamp is built as a real saga; the other four fold into existing units. **DEC-6 + DEC-22 jointly retire D-7** — neither alone would have. Loop clean. **The decided design is now reviewed** |
| 15 | 2026-09-14 | **Pass 10 — the decided design** | **DD-1 … DD-6.** The decisions created a different model and it had not been reviewed. **DD-1 (a record can be declared with no human review) is the sharpest issue in the set** and needs its own decision. **DD-2, DD-4 and DD-5 are root 2 reproduced by the decisions that were meant to close root 1** — each solved its own problem without asking what it added. Four of six fold into units already sequenced |
| 14 | 2026-09-14 | **Sequencing sweep** | **Three errors found, all introduced by the decisions and missed by round 4**, which checked findings and roots but not the derived sequencing. DEC-20 promoted from last to 2b — four earlier units consume it. DEC-21 folded into unit 5, having been absent entirely. DEC-18's spec fix split from its implementation as unit 0. **AD-14 shrank again** — with classification also item-pinned, it is now purely a `Processing` defect. Round 6 clean |
| 13 | 2026-09-14 | **Decision consequences swept** | **DEC-18 … DEC-21.** Four items the *decisions* left unsettled, not the findings. **AD-13 closes** via DEC-21 — root 1 fully closed. **DEC-20 remedies root 2 prospectively**, the first time in this review. DEC-18 accepts a stated risk: the spec carries two retention placements until the plan lands. One new spec obligation — classification vs schedule authority. **Register empty** |
| 12 | 2026-09-14 | **Final open questions** | **DEC-16, DEC-17.** The review's characterisation of AD-26 was **wrong and is corrected** — containment is a same-module projection of authoritative state, and `media-item` already replays, so it was derived *badly* rather than *necessarily*. **All five roots now have remedies.** AD-21 recorded as the residue |
| 11 | 2026-09-14 | **Coherence re-run** | Three rounds, stable on the third. No contradictions. **Two new direction conflicts, both promotions**: DEC-10 now underpins DEC-1 as well as DEC-3; DEC-6 lands on the pinned-vocabulary seam. **AD-14 got smaller** — DEC-1 defuses its governance half. **AD-26 moves from fourth to first** and is the only major finding no decision remedies. Verdict and sequencing revised |
| 9 | 2026-09-14 | **Coherence loop** | **Three rounds, stable on the third.** No contradictions. Roots 4 → 5. AD-2 and AD-5 narrowed; AD-7/AD-17 merged. **Four direction conflicts found — three ordering constraints and one trap (AD-26's obvious remedy is wrong).** Verdict and sequencing written. **Findings are no longer provisional** |

**Running note for Pass 9 — updated after Pass 3.**

Pass 2 asked whether AD-8 was a second root or a symptom. **Pass 3 suggests both AD-1 and AD-8 sit under one
statement**, which is the shape to test in the coherence loop:

> **The model has a record *class* (`MediaProfile`) and a record *aggregation* (`Folder`). All governance is
> attached to the class; several of the events that should drive governance come from the aggregation; and
> nothing connects them.**

Read that way: AD-8 is the clock crossing the gap, AD-13 is the class carrying governance it was not shaped
for, AD-9/AD-10 are the aggregation carrying records semantics with no records behaviour, and AD-14/AD-17
are the class's own declarations not surviving the boundary to the record. **AD-1 may be a third thing** —
it is about one aggregate's internal structure rather than the class/aggregation split — so do not force it
in.

**AD-15 is the exception and must not be collapsed into anything.** It is not a structural finding; it is an
absent capability with four independent decisions leaning on it, and merging it would hide it.

**A second pattern is now visible, and it is not the class/aggregation one.** AD-19 and AD-20 are both
**compositions of individually-correct rules**: idempotency-keeps-first-category silently determines the
failure taxonomy; cascade-nothing plus cannot-delete-while-assigned produces an unexitable state. AD-16 is
the same shape (two enforcement bases for one governance fact), and so is AD-14 (declared vs compiled). Test
in Pass 9 whether this is a second root — provisionally: **each file owns its own rule and no file owns the
composition.** It would explain why so many findings here are things the spec states honestly in two places
and nowhere reconciles.

**Third pattern, from Pass 5, and it may subsume the second.** AD-21 is *eligibility checked once where the
domain needs it to hold continuously*. AD-22 is *a state with no time bound in a model whose other
long-running process has a scanner*. Both are **the model reasoning about instants where the domain reasons
about durations** — and a records domain is almost entirely durations: retention periods, hold, custody,
obligation, closure. Test in Pass 9 against the Pass 4 composition pattern; they may be the same thing seen
from two sides, since a composition defect is usually two rules that are each instantaneously correct.

**The three roots after Pass 6 — all held, and they are not independent.** Provisional shape for Pass 9:

1. **Class / aggregation (records axis).** Governance attaches to the class; the events that drive it come
   from the aggregation; nothing connects them — **and the aggregation is itself derived** (AD-26). Covers
   AD-8, AD-9, AD-10, AD-13, AD-26.
2. **No owner of compositions.** Each rule is defensible where written; the set is not coherent because
   nothing owns the set (AD-25 is this at its source). Covers AD-14, AD-16, AD-19, AD-20, AD-25, AD-28.
3. **Instants vs durations.** The model reasons about moments; the domain reasons about durations — and
   AD-27 shows why the guards cannot do better, because the substrate carries no freshness measure. Covers
   AD-21, AD-22, AD-27, and part of AD-18.

**AD-15 stays outside all three** and must not be collapsed: an absent capability, not a structural fault.
**AD-1 may also stay outside** — it is one aggregate's internal structure, not a cross-aggregate pattern.

**A fourth root, from Pass 7, and it is not structural.** AD-15, AD-29, AD-30 and AD-31 are not defects in
how the model is built — they are **capabilities the domain requires that the model does not contain**.
They cluster cleanly: *everything that happens to a record **because it is a record*** — fixity, hold,
disposition, transfer. Keep this separate from roots 1–3 in Pass 9; merging an absence into a structural
pattern is how it stops being visible, and three of the four are the review's highest-severity findings.

**The review is complete.** All nine passes run, 35 findings, five roots, the loop at a fixed point.

**Next concrete action — Chase's, not the review's.** Two decisions and a status move:

1. **The one substantive question this review leaves open is unit 7** — the class/aggregation join. The
   remedy is a decision about whether `Folder` becomes a classification-bearing aggregation or the `Closure`
   trigger stops reading from it. **The review deliberately does not recommend one**: it is a records-authority
   choice about what a file *is* in this product, and either answer makes the model coherent.
2. **AD-29 and AD-14 are the two that get more expensive with every day of use** — fixity because every
   stored object misses its digest, AD-14 because every item minted carries the wrong capability set
   immutably. Worth deciding ahead of the rest even though neither is top of the severity list.
3. **`findings-agreed` is yours to set.** The review does not move itself, and no plan may open from it
   until you do. Q-1 … Q-4 are all answered, so nothing blocks that but your agreement with the findings.

> ⚠ **Two bookkeeping items still need a shell**, unchanged since the file was created: the id `MM-042` was
> assigned by hand and should be verified free, and no Control Tower card comment has been written for any
> part of this review.

> **The answers do not move this review to `findings-agreed`.** Passes 2–9 are outstanding and the Pass 9
> coherence loop has not run, so every finding is still provisional. `findings-agreed` is Chase's call once
> the review is complete — and Q-4 is open, which the gate counts.

> ⚠ **Two bookkeeping items need a shell.** The id `MM-042` was assigned by hand because the `review-cycle`
> skill could not be run (no `mcp__workspace__bash` — the Sept-8 Windows update blocking the workspace
> mount); **verify it is free before this is indexed.** And no Control Tower card comment has been written
> for this review — this log is the only record.
