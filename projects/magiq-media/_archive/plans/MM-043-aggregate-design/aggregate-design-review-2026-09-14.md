---
id: MM-043
type: plan
project: magiq-media
workstream: aggregate-design
consumes: [MM-042]
depends-on: []
blocked-by-external: []
status: done
todo-id: abb69463-c98a-5e94-be75-dca015b8ff03
branches: [spec/initial-alignment]
ado: -
created: 2026-09-14
closed: 2026-09-15
outcome: spec-complete; code unowned
---

# Aggregate design remediation — the plan

> ## ✅ Closed `done` 2026-09-15 — **spec-complete. Nothing here is built.**
>
> **Thirteen of sixteen phases worked: 0–6 and 9–15.** Fifty-three spec and ADR files in
> `D:\source\github\sprbrk-standard\mgq-magiq-media\docs\`, committed and pushed by Chase on 2026-09-15 to
> **`spec/initial-alignment`**.
>
> ⚠ **`done` means the decided design is written down — not that any of it works.** Every section this plan
> added is marked ⏳ *designed, not built*. **There is no code in this workstream**, and the twenty-four
> decisions it wrote down remain unimplemented in the running system.
>
> ### What is unowned, stated plainly so it is not inherited by accident
>
> **Three phases were never worked, and closing this plan leaves them with no owner:**
>
> | Phase | Unit | Why it stopped |
> |---|---|---|
> | **5 (code half)** | 3 | Needs a working shell **and** `mgq-magiq-media-infra` connected — neither was available in six sessions |
> | **7** | 5 | Retention and classification on the item. Depends on Phase 5's code |
> | **8** | 6 | Disposition as a named act, then hold. Depends on Phases 5 and 7 |
>
> **This is the third ownerless gap in this project**, after MM-041's DF-1…DF-4 and the DF-8/9/14/15 seam
> — and **this plan's own § Scope warns against exactly this pattern.** The warning is repeated here rather
> than buried: *"Do not scope this out to keep a later phase shippable. That is what happened last time."*
>
> **What that means concretely.** `PurgeVersion` still sits wholly outside the disposition model, allowed
> even when archived, answering to nothing. There is still **no legal hold**. There is still **no fixity
> value anywhere** — the platform cannot answer *"is this still the bytes that were filed?"* — and **its
> cost rises with every object stored**, which is why DEC-2 was sequenced early and why leaving it is the
> most expensive of the three to defer.
>
> **Resuming means implementing, not re-deciding.** All twenty-four decisions are taken and written down,
> every phase states its files and acceptance checks, and the forced orderings are recorded in the spec
> itself rather than only here.
>
> ### Two rulings still owed — see § Findings discovered during execution
>
> 1. **The four cascade questions** in `cascade-rules.md`, written as **proposals, explicitly not ruled**
>    (row 3 half-settled by Phase 15, which specified the command but not the cascade).
> 2. **`MoveFolder` on an archived folder** — Q-3 said "on the same terms" without seeing that `Folder`
>    sits on the other side of the line from `MediaItem`.
>
> **A third item is not a ruling but is owed to MM-022:** **X-11.41's text and severity are wrong** and were
> corrected in the spec against source during Phase 2 — the finding itself still needs re-writing.

Consumes **MM-042** (`reviews/aggregate-design/aggregate-design-review-2026-09-14.md`, `findings-agreed`
2026-09-14). **Twenty-four decisions — DEC-1 … DEC-24 — were taken item by item with Chase and are not
re-opened here.** This plan sequences them; it decides nothing.

> **MM-042 is spec-only by declaration. No code was read.** Every unit below is therefore a **design change
> that lands in `docs/` first**, and the code shape is deliberately unscoped except where a decision
> determines it. A finding does not describe the running system — size code against source, not against the
> review.

Spec and ADRs: `D:\source\github\sprbrk-standard\mgq-magiq-media\docs\` — the only copy, nothing published
or mirrored. App code: the same repo's `src\`. Deploy/infra: `mgq-magiq-media-infra`, **not a connected
folder by default**.

---

## Scope

**In scope:** the spec and ADR changes that write down the decided design (DEC-1 … DEC-24), phase by phase,
plus the code shape where a decision fixes it. **Out of scope:** deciding anything, and implementing code
for units whose design has not landed.

### Not in scope — stated so it is not inherited silently

**MM-041's code is unowned, and DF-1 … DF-4 are live in the running system.** MM-041 is closed `done` and
is **not reopened** (DEC-18). Its Phase 4 was dropped the same day and nobody owns it. So today:

- a **confirmed** registration still locks its folder permanently;
- a **withdrawn** item can still be freshly registered;
- a governed edit can still **publish under an abandoned change request**.

**This plan does not own those.** It corrects the *retention text* MM-041 wrote (Phase 0) and nothing else
of MM-041's. If a unit here touches the same files, it does not quietly fix DF-1 … DF-4 and does not
quietly assume they are fixed.

**Do not re-raise anything with an owner.** DF-5 / DF-6 → MM-032 · DF-7 → MM-025 / MM-026 · DF-11 / DF-16 →
MM-030 / MM-035 · DF-12 → MM-038 · X-4.15 and the X-11.x series → MM-022.

**AD-21 is residue, not a unit.** *Cross-context guards are point-in-time where the domain needs standing
constraints.* Four decisions narrow it (DEC-3, DEC-10, DEC-11, DEC-16); none removes it. It is **a concept
to add, not a defect to schedule** — recorded in § The residue below, deliberately unplanned.

---

## Shape of every phase

**Spec and ADR first; code staged behind it.** Same shape MM-041 used, for the same reason: these are
design changes, so the corrected design has to be written down before it can be built.

Each phase states **what changes**, **which spec files**, an **acceptance check**, and **code shape only
where the decision determines it**.

⚠ **Before any code unit:** a working shell (`mcp__workspace__bash`) **and** `mgq-magiq-media-infra`
connected. Every unit that adds a handler needs a `[MessageType]` entry in that repo's `sqs-queues.ts` **as
well as** `ConsumerRegistrations` — a hand-maintained mirror with nothing enforcing the match (**X-4.15**),
and a handler missing from the allowlist **silently never delivers**. App-side-only is not a partial unit,
it is a broken one.

---

## Unit ↔ phase crosswalk

MM-042's revised sequencing table numbers its units `0, 1, 1b, 2, 2b, 3 … 13`, and that order is **not a
valid execution order**: unit 7 depends on unit 9. Phases below are numbered sequentially in a
topologically valid order and each names its unit, so the review's vocabulary survives and the
`## Phase <N> — <name>` shape `ado-create-from-plan` reads stays parseable. **No other heading in this file
begins `## Phase`** — that is deliberate, so the parser sees sixteen phases and nothing else.

| Phase | Unit | Name | Depends on (phases) |
|---|---|---|---|
| 0 | 0 | Correct the retention text | — |
| 1 | 1 | Generalise the completeness rule | — |
| 2 | 1b | Faithful containment | do with 1 |
| 3 | 2 | Fixity | — |
| 4 | 2b | Correction-by-append, once | — |
| 5 | 3 | Repair, then freshness | 2 |
| 6 | 4 | Read-only operator surface | 5 |
| 7 | 5 | Retention and classification on the item | 2, 4, 5 |
| 8 | 6 | Disposition as a named act, then hold | 2, 5, 7 |
| 9 | 9 | The pinned-vocabulary seam | — |
| 10 | 7 | Custody | 9 |
| 11 | 8 | Declaration | 3 |
| 12 | 10 | Disposal action vocabulary | 3 |
| 13 | 11 | Ten-year position | — |
| 14 | 12 | Governance records freeze on close | 4 |
| 15 | 13 | Un-archive, keeping the name reservation | — |

---

## Forced orderings — four, and they are not preferences

1. **Within Phase 5: repair before freshness.** The freshness change alters the schema of the seven
   cross-context indexes, and a schema change to them is *"a manual in-place rebuild"* that **no tool
   performs**. You cannot do the second without the first.
2. **Phase 2 before Phases 7 and 8.** DEC-1's closure stamp fans out over a folder's contents and DEC-3's
   hold can apply to a file — both assume containment is trustworthy, and today the projector is add-only.
3. **Within Phase 8: disposition before hold.** A hold must be able to *refuse a disposition*; until
   `PurgeVersion` is a named act there is nothing to refuse.
4. **Phase 9 before Phase 10.** DEC-6 requires auto-submit to read `ReviewPolicy`, which lives in the
   pinned-vocabulary seam. Doing custody first makes it inherit the seam's defect.

## Traps

> ⛔ **Do not "fix" AD-26 by putting children on the parent.** A folder holding its children is an
> unbounded aggregate, and the spec's rejection of a downward walk is correct. **DEC-16 is the remedy** —
> make the derived view faithful, not authoritative. MM-042 recorded this twice because it is the obvious
> wrong move.

- **Phase 0 is not Phase 7.** Correcting the retention *text* is cheap and immediate; building item-level
  retention is Phase 7. DEC-18 accepted a window where the spec carries **two incompatible retention
  placements** — Phase 0 closes that window, and it is why the plan opens there.
- **Phase 7 is two pieces, not one.** The retention pin is a field change. The closure stamp is **a saga
  with state, correlation key, timeout, resume path and a status surface** (DEC-23). Size them separately;
  the saga leans on Phase 2 far harder than the pin does.
- **Phase 4 is a prerequisite, not a deliverable.** Phases 7, 8, 10 and 14 all consume correction-by-append.
  It sat last in an earlier draft and had to be promoted — do not push it back.

---

## Phase 0 — Correct the retention text (unit 0)

**DEC-18.** Text only. Closes the one exposure MM-042 knowingly leaves: until this lands the spec describes
**two incompatible retention placements with nothing saying which wins** — MM-041's D3 profile-level gate
and DEC-1's item-level pin. **This is not the implementation.**

- [x] State in the retention design that **DEC-1's item-level pin supersedes D3's profile-level gate**, and
      that D3's per-tenant field-retirement migration is a **different migration** that does not apply to an
      item-level pin. *(DEC-18)* — **Files:** `docs/spec/contexts/Metadata/aggregates/RetentionSchedule/retentionschedule.design-decisions.md`.
      **Acceptance:** a reader arriving at the retention design from either direction finds one placement and
      a dated note saying what it replaced; no remaining sentence asserts profile-level resolution as current.
- [x] Sweep the **other** files that state or imply profile-level retention resolution and repoint them at
      the item, or mark them pending Phase 7 where the mechanism is not yet built. *(DEC-18)* — **Files:**
      `docs/spec/contexts/Catalog/aggregates/MediaProfile/mediaprofile.write-model.md`,
      `docs/spec/contexts/Catalog/aggregates/MediaItem/mediaitem.write-model.md`, `docs/spec/README.md`.
      **Acceptance:** `grep -ri "RetentionScheduleRef"` across `docs/` returns no statement that a schedule
      is *resolved through* `MediaProfile` at disposal time.
- [x] Record in the retention design that **MM-041 is not reopened** and that MM-043 carries the corrected
      migration. *(DEC-18)* — **Acceptance:** the note names MM-041 and MM-043 by id.

> ### ✅ Phase 0 landed 2026-09-14 — **uncommitted, on whatever branch the repo is on**
>
> **Seven files edited, three named by this phase and four the acceptance grep found.** Named:
> `retentionschedule.design-decisions.md` (a new `## Placement` section carrying the was/is table, the
> MM-041/MM-043 note, and superseded banners on the gate sequencing and the whole § migration),
> `mediaprofile.write-model.md` (the ⏳ `Retention` note and its capability row — the profile is now stated
> as the **default source**, not the resolution path), `spec/README.md` row 14f-i. Not named but in the
> acceptance grep's scope: `domain-model.md` (the `MediaProfile → RetentionSchedule` row corrected **and a
> new `MediaItem` row added**), `recordtype.write-model.md` § A disposal engine (*"Retention is a
> `MediaProfile` concern"*), `adrs/metadata-schema-composition.md` § The two shipped fields (D3's own ADR
> text — banner-marked superseded), and `mediaitem.write-model.md`, which said **nothing** about retention
> and now carries a ⏳ pending-Phase-7 note so its silence is not read as placement.
>
> **Acceptance met:** `grep -ri "RetentionScheduleRef"` across `docs/` returns no unmarked statement that a
> schedule is *resolved through* `MediaProfile` at disposal time. Every surviving profile-level hit is
> either the publish gate (which **stands** — it is what guarantees there is a value to copy), the
> explicitly-labelled "Was" side of a dated correction, or inside a section carrying a superseded banner.
>
> **One contradiction was found in the text and resolved in the text.** **DEC-1 grants a per-item override
> after creation; ruling 3 of the retention design (2026-09-03) says there is no per-record override in v1.**
> They cannot both stand, so Phase 0 recorded DEC-1 as the later decision and marked ruling 3 amended —
> leaving two answers is the exact defect this phase exists to close. **No decision was taken and none was
> needed.**
>
> ⚠ **Correction, same session — an earlier revision of this note claimed the review had not flagged this
> and routed it to Phase 7 for a ruling. Both halves were wrong; the mistake was mine, from writing the flag
> before reading Phases 4 and 7.** The review flagged it as **DD-5**, and **Phase 4 owns it**: box 2 names
> *"the retention override"* as one of correction-by-append's six consumers, and box 3 is *"state what an
> **override is as an act** rather than as a capability — who, when, why, against what prior value"*.
> Phase 7a box 4 then binds both overrides to it (*"neither override is a field write"*), and Phase 7a box 3
> rules on re-classification against an override in force. **Nothing here needs Chase's eye and nothing is
> owed before Phase 7.**
>
> **Deciding the override's shape early would be actively harmful**, which is why the plan does not: DEC-20
> was *promoted from last* precisely so that its four-plus consumers do not each invent their own correction
> model. An override designed here, ahead of Phase 4, is that failure by hand.
>
> **The one genuine residual is authorization** — *who may* override, as distinct from *who did*, which
> Phase 4 covers. **MM-042 scoped authz out by declaration**, so no phase here owns it. It is not a gap yet:
> no command exists. When Phase 7 specifies one it needs a row in
> `docs/spec/shared/authorization-matrix.md`, where per `spec/README.md` **a row saying "none" is a
> finding**. Noted so it is not discovered late.
>
> ⚠ **Nothing is committed and no branch was cut** — no shell this session (the workspace could not mount
> the drives). The edits are working-tree changes in `mgq-magiq-media`. **Check what branch you are on
> before committing**; per § Closing out, append it to `branches:` when you do.

> **Do not touch MM-041's file.** It is `done` and frozen. The correction lives in the spec, not in the
> closed plan.

## Phase 1 — Generalise the completeness rule (unit 1)

**DEC-15 · closes AD-28, settles AD-20.** MM-041's completeness rule covers **one** of five relationship
mechanisms. Generalise it to **cascades, synchronous query-service reads, aggregate-loaded relationships
and sagas**. Highest-leverage change in the review: it is the only remedy that makes the *next* defect
visible rather than closing one that exists.

- [x] Write the generalised rule: for every relationship mechanism, state **which producing events the
      consumer must handle**, and make an incomplete set a defect rather than a silence. *(AD-28)* —
      **Files:** `docs/spec/shared/cross-aggregate-invariants.md`, `docs/spec/shared/cascade-rules.md`.
      **Acceptance:** the rule names all five mechanisms and gives, for each, the test a reviewer applies.
- [~] Apply it to the **four `cascade-rules.md` rows that carry no rule at all** — this is where AD-20 is
      actually settled, not in a rule of its own. *(AD-20, DEC-14)* — **Files:**
      `docs/spec/shared/cascade-rules.md`. **Acceptance:** no row in the cascade table is blank; deleting a
      record no longer strands its content by the composition of two individually-correct rules.
      ⚠ **Partial — a ruling is owed. Rows written as _proposed_, section retitled, "Not determined" gone,
      and the composition argument (which is the finding) written as settled. But rows 1–3 are design calls
      MM-042 never took, and this plan does not take decisions.** See the callout below.
- [x] Add the **saga** mechanism to the rule explicitly, so *what kind of process is this?* has to be
      answered before a fan-out ships. *(DEC-23's fourth consumer)* — **Files:**
      `docs/spec/shared/saga-patterns.md`. **Acceptance:** the rule would have caught DD-2; write that test
      down as the worked example.

> ### ⚠ Phase 1 landed 2026-09-14 — one box is partial and needs a ruling
>
> **Done:** `cross-aggregate-invariants.md` § *Completeness of cross-context reference projections* is now
> § **Completeness of cross-aggregate relationships**, stating the rule once for **five mechanisms** with the
> reviewer test for each; the original rule survives unchanged beneath it as **mechanism 1**. Mechanism 2
> carries the extra **composition test** (AD-20's actual shape). `saga-patterns.md` gained § *Before a
> fan-out ships: what kind of process is this?* — six properties, each provided or explicitly declined,
> with **DD-2 written up as the worked example** in both files: the rule catching a defect **DEC-1 was about
> to create**, resolved by DEC-23.
>
> ⚠ **Owed: rule the four cascade questions.** The section is retitled *The four questions that had no rule
> — proposed answers, not yet ruled*, and **"Not determined" is gone**. But **rows 1–3 are decisions
> nobody has taken** — does a `ChangeRequest` close with its `MediaItem`? is a `ProcessingJob` terminally
> cancelled when its Asset is deleted? is un-archive the inverse of archive (row 3 pre-empts **Phase 15**)?
> Proposals with reasoning are written; **they are marked proposed and must not be implemented.** Row 4 is
> not really a proposal — it restates **X-11.43** and depends on Phase 6.
>
> **Why they were not just decided:** writing an unmade decision into the spec as settled is the precise
> defect this review exists to close, and § Scope says this plan decides nothing. **Ruling them is a
> decision item for Chase**, not a blocker for Phases 3+.

## Phase 2 — Faithful containment (unit 1b)

**DEC-16 · closes AD-26. Do this with Phase 1** — it is the same rule applied to one index, and Phases 7
and 8 depend on it.

> **MM-042 under-called this and the correction matters.** `FolderMediaItemsIndex` and `FolderFoldersIndex`
> are **same-module** projections of Catalog's own domain events — *not* among the seven cross-context
> indexes with no rebuild path — and `media-item` is one of the six aggregates the CLI already replays.
> `MediaItem.FolderId` **is already authoritative**; only the inverse view is derived, and it was derived
> badly rather than necessarily.

- [x] Specify the containment projectors as fed by the **complete** MediaItem event set — created,
      **assigned, moved, archived, deleted** — not `MediaItemCreated` alone. *(AD-26, DEC-16)* — **Files:**
      `docs/spec/contexts/Catalog/aggregates/Folder/folder.read-model.md`,
      `docs/spec/contexts/Catalog/aggregates/Collection/collection.read-model.md`,
      `docs/spec/shared/cross-aggregate-invariants.md`. **Acceptance:** an item assigned to a folder *after
      creation* appears in that folder's index; the producing event set is written down and matches Phase 1's
      rule.
- [x] Specify that the **CLI clears** same-module indexes before replay. *(AD-26, DEC-16)* — **Files:**
      `docs/spec/shared/consistency-model.md`. **Acceptance:** a replay of `media-item` yields an index equal
      to a rebuild from scratch — reconstructible on demand, which is stronger than Phase 5's *trustworthy*.
- [x] State the surviving consequence rather than assuming it: **faithful is not synchronous.** The
      projection stays eventually consistent, so an operation over an aggregation is still a point-in-time
      read — Phase 5's freshness contract bounds that, and **AD-21 is not solved by DEC-16**. — **Files:**
      `docs/spec/shared/consistency-model.md`. **Acceptance:** the sentence exists and is cited by Phases 7
      and 8.
- [x] State that the archive cascade's `IsComplete` becomes a claim about the **tree**, not about the index.
      — **Files:** `docs/spec/contexts/Catalog/sagas/archive-fan-out.md`. **Acceptance:** the claim is
      qualified by the producing event set, and MM-026 is referenced rather than duplicated.

**Code shape (determined):** ~~the projector stops being add-only~~ **two missing projectors are added**;
the CLI gains a clear-before-replay step for same-module indexes. Nothing else is determined — do not scope
beyond this.

> ### ✅ Phase 2 landed 2026-09-14 — and it re-sized itself against source
>
> **`cross-aggregate-invariants.md` gained § Containment**: both containment indexes enumerated per
> mechanism 1, the *clearing makes them reconstructible* rule, and **§ Faithful is not synchronous** (which
> Phases 7 and 8 now cite). `consistency-model.md` carries the CLI clear-before-replay requirement;
> `archive-fan-out.md` qualifies `IsComplete` as a traversal claim that becomes a **tree** claim only once
> the indexes are complete; `folder.read-model.md` separates the navigation read model from the write-side
> index; `collection.read-model.md` § No `RootFolderIds` is reinforced as **the trap, not the defect**.
>
> ⚠ **The premise above was wrong, and source says so. This corrects a finding, it does not raise one.**
> MM-042's AD-26 and this plan both said the containment projector is **add-only**;
> `cross-aggregate-invariants.md` § Stated but not enforced said the same, and gave two consequences.
> **`ServiceCollectionExtensions.cs` registers all four `FolderMediaItemsIndex` projectors** — created,
> move-added, move-removed, archived. **Removal on move and on archive both work**, so neither stated
> consequence follows.
>
> **The real gap is narrower and still serious:** `MediaItemAssignedToFolder` and `MediaItemDeleted` have
> **no projector**. An item created unassigned and later assigned is invisible to the cascade — not
> archived, not counted, not a recorded failure, **and the run still reports complete** — and the same index
> backs the folder registration pre-flight, so a **retention-locked item assigned after creation passes that
> guard too**. `archive-fan-out.md` § D-1 has said this correctly since 2026-08-25; **the two spec files
> contradicted each other and nobody had noticed.**
>
> **Consequence for planning: X-11.41's text is wrong and its severity needs re-assessing — it belongs to
> MM-022** and is not re-raised here. **Phase 7b's dependency on this phase is unchanged** (the closure
> stamp still misses items assigned after creation), but **the code is two handlers, not a projector
> rewrite.** Size it from source.

## Phase 3 — Fixity (unit 2)

**DEC-2 · closes AD-29, settles AD-18.** There is **no fixity value anywhere in the model** — the platform
cannot answer *"is this still the bytes that were filed?"*. **Both** halves, not either. Sequenced early
regardless of severity because **its cost rises with every object stored**.

- [x] Specify a **per-object capture digest**, computed at upload confirmation and stored immutably beside
      `StorageKey`. *(AD-29)* — **Files:**
      `docs/spec/contexts/AssetManagement/aggregates/Asset/asset.write-model.md`,
      `docs/spec/shared/event-store-and-messaging.md`, `docs/spec/architecture/system-architecture.md`.
      **Acceptance:** the digest is on the confirmation event, is immutable thereafter, and the spec says
      which algorithm and who may recompute.
- [x] Specify a **version manifest** — the set of object digests stamped onto the published version.
      *(AD-18, AD-29)* — **Files:**
      `docs/spec/contexts/Catalog/aggregates/MediaItem/mediaitem.write-model.md`,
      `docs/spec/shared/cross-aggregate-invariants.md`. **Acceptance:** *"is this the set of objects that was
      approved?"* is answerable from the item alone; what is currently emergent from `VersionArtifact`
      promotion becomes stated.
- [x] Record that the manifest is **what an archival transfer would have to carry** — Phase 12's `Transfer`
      and a future export review meet here. *(DEC-19)* — **Acceptance:** the cross-reference exists in both
      directions.
- [x] Update the API surface where a digest or manifest becomes client-visible. — **Files:**
      `docs/spec/shared/api-conventions.md`,
      `docs/spec/contexts/AssetManagement/aggregates/Asset/asset.api.md`. **Acceptance:** no endpoint returns
      a version without a way to obtain its manifest.

> ### ✅ Phase 3 landed 2026-09-14
>
> **`asset.write-model.md` gained § Fixity — the capture digest**: SHA-256 with the algorithm stored
> alongside the value, set at upload confirmation on **both** upload modes (they converge on
> `AssetUploadConfirmed`, which is why the digest hangs there), immutable for the life of the asset, with
> property / value-object / invariant / event rows added. **Two interactions stated that would otherwise
> have been got wrong:** `RequestReprocessing` republishes `AssetUploadConfirmedIntegrationEvent` and must
> carry the **original** digest unchanged, and **the S3 ETag is not usable** — for a multipart upload it
> digests the parts, not the object. `mediaitem.write-model.md` gained **§ The version manifest**;
> `cross-aggregate-invariants.md` gained **§ Fixity**, which is where the two halves are stated together
> because neither context could claim the guarantee alone — *that is why it was emergent*.
> `api-conventions.md` carries **no version without a route to its manifest**, and `asset.api.md` exposes
> `captureDigest` read-only. Glossary: **CaptureDigest**, **VersionManifest**, plus a warning on
> **VersionArtifact** that it is *structural* fixity only.
>
> **Renditions are a stated scope boundary, not an oversight** — DEC-2 decided originals at confirmation and
> said nothing about derivatives; recorded where an export review will meet it.
>
> ⚠ **AD-18's other two gaps are untouched and are marked as such:** `AssetUnassignedFromRole` /
> `AssetReplacedInRole` still produce no integration event, and `RequestReprocessing` re-entering
> `Validating` from `Active` is still not stated as interacting with `VersionArtifact`. **A manifest makes
> both detectable; it fixes neither.**

## Phase 4 — Correction-by-append, once (unit 2b)

**DEC-20 · generalises DEC-8. Promoted from last — it is a prerequisite, not a deliverable.** Phases 7, 8,
10 and 14 all consume it. Designing it once was the whole point; leaving it late produces the four
divergent correction models it exists to prevent, which is root 2 in miniature.

- [x] Specify correction-by-append **generically**: **attributed, reason-bearing, never overwriting**, with
      the prior value legible. *(AD-23, DEC-20)* — **Files:** `docs/spec/shared/cross-aggregate-invariants.md`
      (new shared concept), `docs/spec/glossary.md`. **Acceptance:** one definition, referenced by every
      consumer below; no consumer defines its own.
- [x] Name its consumers explicitly, **including the two DEC-20 missed**: DEC-8's comment correction ·
      DEC-7's audited move · DEC-9's clock re-stamp · DEC-3's disposition record · **the retention override**
      · **the classification override**. *(DD-5, DEC-24)* — **Acceptance:** six consumers listed; DD-5 closes
      on the list existing, not on the overrides being built.
- [x] State what an **override is as an act** rather than as a capability — who, when, why, against what
      prior value. *(DD-5)* — **Files:** the shared concept file plus a forward reference from
      `docs/spec/contexts/Metadata/aggregates/RetentionSchedule/retentionschedule.design-decisions.md`.
      **Acceptance:** *"overridable afterwards"* no longer reads as a field write anywhere in `docs/`.

> ### ✅ Phase 4 landed 2026-09-14 — and it closes most of what Phase 0 flagged
>
> **`cross-aggregate-invariants.md` gained § Correction-by-append**, stated once with **all six consumers
> named** — comment correction, audited move, clock re-stamp, disposition record, **retention override**,
> **classification override**. The last two are DD-5's addition; DEC-20 named three and missed three.
> Glossary carries the term. The retention design gained § *An override is an act*, and the phrase
> *"overridable afterwards"* now points at the concept in **all five** places it appears (`domain-model.md`,
> `mediaitem.write-model.md`, `mediaprofile.write-model.md`, `metadata-schema-composition.md` and the
> retention design itself) — acceptance grep clean.
>
> **Two points worth not losing.** *Never overwriting* is stated as **stronger than event-sourced
> recoverability** — a prior value is already recoverable from the stream, and `ReviewCommentEdited`
> omitting `OldBody` for that reason is sound; the requirement is that a records reader can answer *what
> did this say before, who changed it, why* **from the aggregate's surface**. So the fix is a read surface,
> not a payload field. And a correction is **bound to the value it replaces** — one applied against a value
> that has since changed is **refused, not silently re-based**.
>
> **This closes the DEC-1 ↔ ruling-3 residue** Phase 0 recorded: attribution, reason, and telling an
> overridden schedule from an inherited one all fall out of the concept. ⚠ **Authorization does not** —
> *who may* override is scoped out of MM-042 and owned by no phase; each of the six needs an
> `authorization-matrix.md` row when its command is specified, and **a row saying "none" is a finding**.

## Phase 5 — Repair, then freshness (unit 3)

**DEC-10 · closes AD-33 and AD-27. Ordering inside this phase is forced.** Promoted from follow-up to
prerequisite by DEC-3 and again by DEC-1: a hold over a *file* and a closure stamp fanning out over one
both need containment they can trust. It also closes the dated position — the repair rule is currently
satisfiable only by *"record that no affected data exists"*, which holds only while `PROD_ENABLED` and
`STAGING_ENABLED` are unset.

- [x] **Repair first.** Specify a rebuild path for the **seven cross-context reference indexes** and a
      seeding pass for the **two counters**. *(AD-33)* — **Files:** `docs/spec/shared/consistency-model.md`,
      `docs/spec/shared/operations.md`. **Acceptance:** for each of the seven, the spec names the producing
      events, the rebuild command and the expected end state; *"a manual in-place rebuild"* no longer appears
      as the only option.
- [x] **Then freshness.** Specify a **source-relative version** on reference rows, so a guard can refuse
      stale evidence. *(AD-27)* — **Files:** `docs/spec/shared/consistency-model.md`,
      `docs/spec/contexts/Registration/aggregates/Registration/registration.write-model.md`. **Acceptance:**
      `ProjectedVersion`'s *"local monotonic watermark, with no relationship to the source aggregate's
      event-store version"* is replaced by a value a guard can compare; a guard can say *this evidence is too
      old to act on*.
- [x] State that the freshness change **alters the schema of those seven indexes**, which is why the repair
      capability has to exist first. — **Acceptance:** the dependency is written in the file, not only in
      this plan.
- [x] State what freshness does **not** give: it lets a guard *know* a fact is stale; nothing yet lets a
      relationship *require* a fact to remain true. **That is AD-21, and it stays open.** — **Acceptance:**
      the limitation is named where the contract is defined.

**⚠ Code unit.** `mgq-magiq-media-infra` must be connected before any of the code half; new consumers need
their `[MessageType]` entries as well as `ConsumerRegistrations`.

> ### ✅ Phase 5 spec half landed 2026-09-14 — **the code half is untouched and still needs a shell**
>
> **`consistency-model.md` gained § Repair and § Freshness, in that order and for the stated reason.**
> Repair: a `references rebuild` verb per index — **all seven tabulated with producing aggregate and
> expected end state** — plus `counters reseed` for `active-registrations` and `depth`, which no replay
> can touch because command handlers write them. **`--dry-run` is specified as non-optional**: a repair
> tool that can only be run destructively will not be run when it is needed, and it doubles as the cheapest
> way to answer *does any affected data exist?*, the question § The repair position makes mandatory.
>
> **Freshness: `SourceVersion` is additive, not a replacement.** `ProjectedVersion` keeps its job — it was
> never wrong, it was being asked a question it does not answer — and collapsing the two would trade
> idempotency for freshness. `registration.write-model.md` carries both the field and the worked example,
> since rule 12 trusting `IsPublished` unconditionally is AD-27's live case.
>
> **Both forced orderings are now written in the files rather than only here**: repair before freshness
> (the schema change hits seven indexes nothing can rebuild — doing it the other way leaves a freshness
> column **absent on exactly the rows old enough to need it**), and **AD-21 stays open** — a guard can now
> *know* a fact is stale; nothing lets a relationship *require* it to remain true.
>
> ⚠ **What DEC-10 closes is a dated escape.** The repair position is satisfiable today only by *"record
> that no affected data exists"*, which holds **only while `PROD_ENABLED` and `STAGING_ENABLED` are
> unset**. This makes the first option real before that stops being true — that, not severity, is the
> argument for its position.

## Phase 6 — Read-only operator surface, including holds (unit 4)

**DEC-11, DD-3 · closes AD-32; makes AD-22 and AD-35 tractable without their own remedies.** Expose derived
state **before** building anything that writes to it: most incidents need diagnosis, not repair; read-only
cannot corrupt an invariant-backing value by hand; and it tells you which repair tools are worth building.

- [x] Specify read-only inspection for **counter values, saga status, cascade reports and stale
      registrations**. *(AD-32, DEC-11)* — **Files:** `docs/spec/shared/operations.md`,
      `docs/spec/contexts/Catalog/sagas/archive-fan-out.md`,
      `docs/spec/contexts/Processing/sagas/assetingestionsaga.md`,
      `docs/spec/contexts/DocumentSigning/sagas/documentsigningsaga.md`. **Acceptance:** the position the
      spec currently leaves operators in — forbidding *"Do not edit the saga row to a terminal status
      directly"* while providing no supported path — is ended.
- [x] **Add holds to the surface.** *(DD-3, DEC-24)* — **Acceptance:** *"these records are preserved, here
      is the list, here is when it was applied"* is answerable. **A hold that cannot be enumerated cannot be
      certified** — a hold list is a read model, and Phases 2 and 5 are already building read models, which
      is why this costs nothing here and a great deal later.
- [x] Record that **AD-22** (stalled registrations, unbounded and invisible) and **AD-35** (four failure
      dispositions, three of which ack and continue) become tractable once failure is visible, and get **no
      separate remedy**. *(DEC-14)* — **Files:**
      `docs/spec/contexts/Registration/aggregates/Registration/registration.write-model.md`.
      **Acceptance:** both findings are marked settled-by-visibility rather than left open.

> **Read-only means read-only.** No write path in this phase, however obvious the repair looks.

> ### ✅ Phase 6 landed 2026-09-14
>
> **`operations.md` gained § Derived-state operations** — the five surfaces (counters, saga status, cascade
> reports, stale registrations, **holds**) with why each is on the list, and the read-only rule stated as a
> ⛔ rather than a preference. The runbooks above it recover *tables*; this is about **derived values that
> are wrong while their table is perfectly healthy**, which is the distinction the file did not draw.
>
> **The AD-32 position is named at its source, not just in the shared file.** `assetingestionsaga.md` §
> Manual Intervention Runbook forbids editing the saga row to a terminal status — correctly — and then
> offers **direct edits to `media-sagas` as the last resort**. It gives back the forbidden thing as the
> fallback, which is what happens when derived state is invisible. Its existing levers stay correct and
> are marked so; **no force-close comes with the inspector**, because closing the saga while `Asset` and
> `ProcessingJob` stay untouched is exactly the mistake such a verb would make easy.
>
> **`archive-fan-out.md`: the report is already computed and then discarded.** What is missing is writing
> it down — and no repair verb, because re-issuing the archive against the root is already a complete
> recovery **precisely because** the cascade suppresses ancestors. **`documentsigningsaga.md` is the one
> saga where the surface is a precondition rather than a retrofit** — nothing is built, and where the
> platform's state and the world's can diverge while only one is correctable, seeing the platform's state
> *is* the recovery.
>
> **AD-22 and AD-35 are marked settled-by-visibility, with the distinction spelled out**: a deferred
> finding is one nobody decided about, and both are decided. AD-22 — **an expiry was deliberately not
> added**, because auto-cancelling a live statutory filing over a slow queue is worse than waiting, and
> visibility makes that an informed call rather than a guess. AD-35 — **unifying the four failure
> conventions is explicitly not the remedy**; making each ack-and-continue path report what it swallowed
> is, because you cannot judge which conventions lose work before you can see them.

## Phase 7 — Retention and classification on the item (unit 5)

**DEC-1, DEC-9, DEC-21, DEC-23, DD-4 · closes AD-8, AD-13, reshapes AD-9. Depends on Phases 2, 4 and 5.**
Domain owner: **Karen Barton**. **Two pieces — size them separately.**

### 7a · The pin (a field change)

- [ ] The retention schedule is **pinned on the `MediaItem`** — not resolved through `MediaProfile`, not
      inherited from `Folder` — **copied from the profile at creation, by value**, exactly as
      `SnapshotFields` works, with a per-item override afterwards. *(AD-8, DEC-1)* — **Files:**
      `docs/spec/contexts/Catalog/aggregates/MediaItem/mediaitem.write-model.md`,
      `docs/spec/contexts/Metadata/aggregates/RetentionSchedule/retentionschedule.design-decisions.md`,
      `docs/spec/contexts/Catalog/aggregates/MediaProfile/mediaprofile.write-model.md`. **Acceptance:** rule
      and clock are both item-local; the cross-hierarchy dependency AD-8 names is gone.
- [ ] **Classification moves to the item on the same pattern** — copied from the profile at creation, pinned
      by value, overridable afterwards. *(AD-13, DEC-21)* — **Files:** as above plus
      `docs/spec/contexts/Metadata/context-overview.md`. **Acceptance:** `MediaProfile` reads as *"the
      structural contract for a `MediaItem` type"* again, with no governance bolted on. **Security
      classification follows the same placement when it is built** — unmodelled today, and nothing about its
      content is decided here.
- [ ] **State which is authoritative for disposal.** The **pinned schedule is authoritative; the
      classification is descriptive** — and say what happens when a records officer changes one without the
      other: re-classification either **re-derives** the schedule or is **refused while an override is in
      force**. *(DD-4, DEC-24)* — **Acceptance:** two governance facts on the item can no longer disagree
      with nothing reconciling them. **This is root 2 reproduced by the decisions meant to close root 1 —
      do not leave it as a reading.**
- [ ] Both overrides use Phase 4's correction-by-append. *(DD-5)* — **Acceptance:** neither override is a
      field write.
- [ ] Record that **longest-retention-wins was not adopted and is not needed** — one pinned schedule per
      item makes two concurrent disposal authorities unconstructible, preserving the 2026-09-03
      prohibition-over-precedence decision. — **Acceptance:** stated, so it is not re-litigated.

### 7b · The closure stamp (a real saga — DEC-23)

- [ ] `FolderClosed` **stamps the closure date onto each contained item**. The clock becomes a fact the
      record holds, **not a live read of the current folder**. *(AD-9, DEC-1)* — **Files:**
      `docs/spec/contexts/Catalog/aggregates/Folder/folder.write-model.md`. **Acceptance:** all three move
      cases a live read leaves unruled are dissolved — into a closed folder, out of a closed folder, between
      two closed folders — and the path leaves AD-27's scope entirely.
- [ ] **Moving re-stamps**: cleared if the destination folder is open, re-stamped if it is closed. Every
      change to a disposal clock is **audited with the move that caused it**. *(DEC-9)* — **Files:**
      `docs/spec/contexts/Catalog/aggregates/MediaItem/mediaitem.write-model.md`. **Acceptance:** this is the
      review's one moving clock; no change to it is unattributable to an act.
- [ ] Build the fan-out **as a real saga** — state, correlation key, timeout, resume path and a status
      surface, the properties `AssetIngestionSaga` has and the two archive fan-out workers do not. *(DD-2,
      DEC-23)* — **Files:** `docs/spec/shared/saga-patterns.md`, plus a new saga spec under
      `docs/spec/contexts/Catalog/sagas/`. **Acceptance:** a partial stamp is visible and resumable. **An
      un-archived item is visible; a record with no disposal clock is not** — and a folder that reports
      closed successfully looks correct, which is the failure a retention system exists to prevent.
- [ ] The fan-out must reach items **assigned after creation**, which today's add-only projector misses —
      this is the Phase 2 dependency, and it binds 7b harder than 7a. — **Acceptance:** the saga's coverage
      claim cites Phase 2's producing event set.

**⚠ Code unit.** Infra repo connected; the saga's queue needs its `[MessageType]` entry.

## Phase 8 — Disposition as a named act, then hold (unit 6)

**DEC-3 · closes AD-15 and AD-31. Ordering inside this phase is forced. Depends on Phases 2, 5 and 7.**

- [ ] **First:** bring `PurgeVersion` inside the disposition model as a **named, authorised, recorded,
      refusable** disposition act. It is currently *"allowed even when archived"* with no guard at all, and
      it sits wholly outside the model. *(AD-31, Q-4)* — **Files:**
      `docs/spec/contexts/Catalog/aggregates/MediaItem/mediaitem.write-model.md`,
      `docs/spec/contexts/Metadata/aggregates/RetentionSchedule/retentionschedule.design-decisions.md`.
      **Acceptance:** Q-1 and Q-3 are consistent — a published version is a fixed manifestation of a record,
      so destroying one is disposition, not a content edit and not a custodial operation. The retention
      design's *"any link to `PurgeVersion` … out of scope"* is removed.
- [ ] The disposition act is recorded via Phase 4's correction-by-append. *(DEC-20)* — **Acceptance:** no
      bespoke record shape.
- [ ] **Then:** a first-class **hold** that applies to an **item or a whole file**, **survives archive**, and
      **blocks disposition and deletion**. *(AD-15, DEC-3)* — **Files:** as above plus
      `docs/spec/contexts/Catalog/aggregates/Folder/folder.write-model.md`,
      `docs/spec/shared/cross-aggregate-invariants.md`. **Acceptance:** legal hold stops being *"inexpressible"*;
      a hold refuses a named disposition act, which is only possible because the first item landed.
- [ ] Say **who places a hold, who may lift it, and whether it expires.** *(DD-3)* — **Acceptance:** all
      three answered in the spec; enumeration itself is Phase 6.
- [ ] A **file-level** hold asserts its coverage rather than covering whatever the index happens to hold —
      cite Phase 2. **A hold built on the old substrate would silently miss records, which is worse than no
      hold.** — **Acceptance:** the coverage claim is explicit and bounded by Phase 5's freshness contract.

## Phase 9 — The pinned-vocabulary seam (unit 9)

**AD-7 / AD-17, taken as one problem. Ownerless today; MM-040 argues the four will not converge if fixed
separately, and they should not be scoped out a second time. Phase 10 depends on this.**

- [x] Treat the seam as **one problem**: six members the file's own rules depend on do not exist, and the
      rules **fail silently rather than loudly**; the schema a class pins cannot be faithfully reconstructed
      by its only consumer. *(AD-7, AD-17)* — **Files:**
      `docs/spec/contexts/Catalog/aggregates/MediaItem/mediaitem.write-model.md`,
      `docs/spec/contexts/Metadata/context-overview.md`, `docs/adrs/metadata-schema-composition.md`.
      **Acceptance:** a missing pinned member is a loud failure with a named error; reconstruction is
      specified and testable.
- [x] **`ReviewPolicy` is inside this seam** (DF-8) — a capability pinned into immutable versions that gates
      nothing. Phase 10's DEC-6 and Phase 11's DEC-22 both read it, so it must be real here first.
      **Acceptance:** `ReviewPolicy` is readable and authoritative before either consumer is specified.

> **Do not scope this out to keep a later phase shippable.** That is what happened last time.

> ### ✅ Phase 9 landed 2026-09-14 — the ownerless seam now has an owner
>
> **Specified at both ends, as one rule seen from two sides** — which is the whole of MM-040's argument that
> the four *"will not converge if fixed separately"*.
>
> **Consuming end** (`mediaitem.write-model.md`): **a rule whose pinned member may be absent must be
> unrepresentable, not fall-through.** A missing member raises **`PinnedSchemaIncomplete`**, naming the
> member *and* the rule — deliberately not another bare `InvalidOperation`, since most refusals in that file
> already carry no `errorCode` and one more would bury it. **Refusal rather than a safe default**, because
> every member in the list governs whether a governed field may be written, seeded or required: a field
> treated as required because nothing said it was deprecated is a record refused for the wrong reason, and
> one treated as writable because nothing said it was immutable is worse.
>
> **Producing end** (`Metadata/context-overview.md`): the published contract must let a consumer
> reconstruct the pinned schema **from the event alone**, with the three failures tabulated — the
> five-property summary with no `Aliases`, the **unpublished-and-live** `FieldType` vocabulary (a tenant can
> author a `Url` field *today* with nothing specifying what Catalog does with it), and the unshipped
> `RecordTypeVersionDeprecated`. The ADR's *"the answer is contract work at the seam"* now says **what that
> work is** — that vagueness is arguably why the seam stayed ownerless.
>
> **The sharpest evidence it is one problem:** `IsDeprecated` missing from `MediaProfileSnapshotField` and
> `RecordTypeVersionDeprecated` never shipping are **the same lifecycle signal failing at each end**.
> Fixing either alone leaves the story broken.
>
> **`ReviewPolicy` (DF-8) is made authoritative on the publish path**, ahead of both consumers. One thing
> the specification adds that the finding did not: it must be read the way `CheckoutPolicy` is —
> `profile?.X ?? item.PinnedX` — **and `ReviewPolicy` has no pinned counterpart**, so the item must gain
> one. Otherwise the gate fails **open** exactly when the profile projection is lagging or dropped, which
> is the failure a review policy exists to prevent. **D-7's other three halves stay open** (reviewer-is-
> caller, no de-duplication, no minimum) — those are rules about the reviewer *set*, not about whether a
> set is required.

## Phase 10 — Custody (unit 7)

**DEC-4, DEC-6, DEC-7, DEC-22, Q-2, DD-6 · closes AD-1, AD-3, AD-4. Depends on Phase 9.**

- [x] **The lock covers custody, not just content.** `Publish`, `Withdraw`, `Archive` and `Move` become
      guarded while a session is open. **Reviewer commands (`ApproveReview`, `RejectReview`) and
      system-internal commands stay unguarded** — *"marking `ApproveReview` would make review impossible"*.
      *(AD-3, DEC-4)* — **Files:**
      `docs/spec/contexts/Catalog/aggregates/MediaItem/mediaitem.write-model.md`,
      `docs/adrs/editing-lifecycle-and-concurrency.md`. **Acceptance:** a checked-out record can no longer be
      published, withdrawn or archived out from under its holder; the marker distinguishes an owner's
      lifecycle act from a reviewer's.
- [x] **The session initiator takes custody.** Additional members may make content and metadata changes;
      they **may not perform lifecycle acts**. **Many editors, one custodian.** *(AD-4, DEC-4)* —
      **Acceptance:** *"one or more users"* becomes a coherent claim rather than a partial one.
- [x] **`ExpectedVersion` / `If-Match` becomes mandatory on content commands when a session has more than
      one member**, and a multi-member session **refuses** a content command that arrives without one.
      *(Q-2)* — **Files:** `docs/spec/shared/consistency-model.md`,
      `docs/spec/shared/concurrency-and-consistency.md`, `docs/spec/shared/api-conventions.md`.
      **Acceptance:** the set of commands honouring `If-Match` is **explicit and complete**. Today it is
      honoured on two metadata endpoints and *"silently ignored elsewhere"* — silently ignoring it here would
      reproduce AD-4 exactly.
- [x] **Auto-submit may submit, never declare.** `AutoSubmitOnComplete` moves an item `Draft →
      PendingApproval` and **no further**; where `ReviewPolicy` is `None` and no reviewers exist it **does
      nothing**. *(AD-1 pt 1, DEC-6)* — **Acceptance:** the three content handlers that dispatch
      `PublishMediaItemCommand` as `owner_system` — assign-to-folder, assign-asset-to-role,
      set-metadata-batch — can no longer declare a record with no human act. This also closes the
      DEC-4/auto-submit direction conflict: `owner_system` would otherwise have published a record out from
      under its custodian.
- [x] **`ReviewPolicy` becomes real on the publish path**, and declaration **records how it happened**. A
      profile set to `RequiredForPublish` **cannot self-declare** — an empty reviewer list is refused. Where
      the policy is `None`, self-declaration is permitted and the declaration **records that it was
      unreviewed**. *(DD-1, DEC-22)* — **Files:**
      `docs/spec/contexts/Catalog/aggregates/MediaItem/mediaitem.write-model.md`,
      `docs/spec/contexts/Catalog/aggregates/MediaProfile/mediaprofile.write-model.md`. **Acceptance:**
      **D-7 retires** — DEC-6 closed it for auto-submit, DEC-22 closes it for the explicit publish path, and
      neither alone would have. "Unreviewed" is a recorded property, not an absence.
- [x] **Folder assignment: hold blocks, custody blocks, archive does not.** Every move audited with a
      reason. *(AD-1 pt 2, DEC-7)* — **Acceptance:** archived items remain movable, and the review's first
      recommendation — blocking moves on archived items — is recorded as **withdrawn**: common EDRMS practice
      permits re-filing closed and archived records as a privileged audited act, because **mis-files are
      discovered during appraisal, which happens after closure**.
- [x] **Fix the archived-`Move` defect.** `ArchiveMediaItemHandler` releases the title reservation on
      archive, so a later move calls `MoveAsync` against a reservation row that no longer exists. *(Q-3)* —
      **Acceptance:** keeping `Move` legal on an archived item is choosing to make it work — it works.
- [~] Apply Q-3's freeze **across `Collection`, `Folder` and `MediaItem`**, closing U-5 on the same terms.
      **`Collection` is the weaker case** — four commands carry no archived check at all, including
      `SetVisibility`, so an archived collection can currently be made **`Public`**. *(AD-2, AD-11, DEC-14)*
      — **Files:** `docs/spec/contexts/Catalog/aggregates/Collection/collection.write-model.md`,
      `docs/spec/contexts/Catalog/aggregates/Folder/folder.write-model.md`. **Acceptance:** archived content
      is frozen; filing operations stay legal; `SetVisibility` is frozen.
- [x] **State and announce DD-6.** A tenant with no review process loses auto-submit entirely rather than
      having it change. **That is the right safety answer and a silent product regression, and the two must
      not be conflated** — it is the only decision in the set with a user-visible behaviour change that
      nothing announces. *(DD-6, DEC-24)* — **Acceptance:** stated in the spec **and** a note that affected
      tenants are told.

> ### ✅ Phase 10 landed 2026-09-14 — eight of nine boxes; one needs a ruling
>
> **Custody.** `mediaitem.write-model.md` and `editing-lifecycle-and-concurrency.md` now carry the rule that
> the lock covers **custody, not only content** — `Publish`, `Withdraw`, `Archive`, `Move` guarded while a
> session is open, structurally, with the three exclusions and their reasons. **Many editors, one
> custodian.** One asymmetry closes with it: `Withdraw` on an already-`Draft` item is a no-op that
> **silently destroys someone's session**, and is now refused.
>
> **Concurrency.** `If-Match` mandatory on content commands in a **multi-member** session, `428` otherwise,
> with the load-bearing consequence written down: **the silent-ignore behaviour must end in the same
> change.** A precondition mandatory in one place and ignored in another is worse than one that is absent,
> because a careful client cannot tell which it is getting — and silently ignoring it here reproduces AD-4
> with a client that did everything right. Single-member sessions unchanged.
>
> **Declaration.** Auto-submit capped at `PendingApproval`; `RequiredForPublish` cannot self-declare;
> **"unreviewed" becomes a recorded property, not an absence** — an absence is indistinguishable from a gap
> in the record. **D-7 retires**, and only because both halves landed. DD-6 stated *and* an announcement
> obligation recorded, with the affected tenants made identifiable (`AutoSubmitOnComplete = true` **and**
> `ReviewPolicy = None`).
>
> ⚠ **One thing the findings did not say, added here.** The pinned-policy decision in that ADR exists so
> the checkout guard **survives an unreadable profile projection** — `profile?.X ?? item.PinnedX`.
> **`ReviewPolicy` has no pinned counterpart**, so made authoritative as-is it fails **open** during exactly
> the projection gap that decision was written to survive. The item must pin it on the same terms.
>
> ⚠ **Box 9 is `[~]`: Q-3's freeze exposed a question Q-3 did not notice.** `Collection` and `MediaItem`
> are specified — including **`SetVisibility` frozen**, the sharpest case, since an archived collection can
> currently be made `Public`, which is a disclosure change and custodial by no reading. But **`Folder`
> already blocks `MoveFolder` when archived**, and under Q-3's *filing stays legal* that guard arguably
> should come off — re-parenting a folder **is** a filing operation, and `MediaItem.Move` is being unblocked
> for precisely that reason. Q-3 said "on the same terms" without seeing that one of the three sits on the
> other side of the line. **Left as written; ruling recorded in § Findings discovered during execution.**

## Phase 11 — Declaration (unit 8)

**DEC-5, DEC-17 · closes AD-5. Pairs with Phase 3.**

- [x] **`MediaItemApproved` is the declaration point.** From that moment the version is fixed, its asset
      manifest is stamped (Phase 3), and content changes require a new version. *(AD-5, DEC-5)* — **Files:**
      `docs/spec/contexts/Catalog/aggregates/MediaItem/mediaitem.write-model.md`,
      `docs/spec/shared/cross-aggregate-invariants.md`, `docs/spec/glossary.md`. **Acceptance:** approval is
      named as declaration; **no separate `Declare` command is added** — that would give an aggregate with
      three state machines a fourth.
- [x] **Declaration fixes content, not filing** — in those words. A declared version's content is fixed;
      its filing is not. A declared record may be re-filed, and Phase 7's re-stamp moves its disposal clock
      when it is. *(DEC-17)* — **Acceptance:** the sentence is in the spec, because a reader will otherwise
      assume "fixed" covers both.
- [x] **Re-filing is the same audited act whether or not the record is declared** — gated by hold and
      custody per DEC-7, with **no additional guard** for declared records. *(DEC-17)* — **Acceptance:** the
      reasoning is recorded: mis-files are found during appraisal, *after* declaration, so an extra guard
      penalises exactly the case that occurs. **The audit trail is what makes it safe, not a second gate.**

## Phase 12 — Disposal action vocabulary (unit 10)

**DEC-12, DEC-19 · closes AD-30. Depends on Phase 3.** The trigger vocabulary got six rows, a readiness
column and a rule; `action` was declared *"a domain enum, closed by construction"* and its members were
**never written down**. This is D4's argument on the axis nobody checked.

- [x] Write the **action table with a readiness column**, and apply the trigger rule's analogue: **a disposal
      action must name an operation the platform can perform.** Authoring a schedule that pins an
      unperformable action is **refused**, exactly as D4 gated `Superseded` and `Closure` on their missing
      timestamps. *(AD-30, DEC-12)* — **Files:**
      `docs/spec/contexts/Metadata/aggregates/RetentionSchedule/retentionschedule.design-decisions.md`,
      `docs/adrs/metadata-schema-composition.md`. **Acceptance:** every member has a readiness verdict —
      `RetainPermanently` ✅ · `Review` ❌ (no workflow) · `Transfer` ❌ (no export exists) · `Destroy` via
      Phase 8's named act.
- [x] **`Transfer` is enumerated and refused until an export exists.** *(DEC-19)* — **Acceptance:** gated,
      not dropped — widening an enum pinned into immutable published versions is the change this design
      exists to avoid. **Export is a substantial capability and deserves its own review**, not a corner of
      this plan; Phase 3's manifest is what it will need to be attestable.

> ### ✅ Phases 11 and 12 landed 2026-09-14
>
> **Phase 11.** `cross-aggregate-invariants.md` gained **§ Declaration**, with `mediaitem.write-model.md`
> § Review lifecycle and a glossary entry pointing at it. **`MediaItemApproved` is the declaration point**,
> naming machinery that already exists — and **no `Declare` command**, stated as a design constraint: the
> aggregate already runs three state machines and one of them is *"coupled to nothing"*, so a fourth would
> deepen the root while appearing to fix something else. **Declaration fixes content, not filing** is in
> those words, with the reason re-filing needs no extra guard — **mis-files are found during appraisal,
> which happens after declaration**, so a guard there penalises exactly the case that occurs.
>
> **Phase 12.** The `action` vocabulary is written down for the first time, with a readiness verdict per
> member: `RetainPermanently` ✅ · `Destroy` ⏳ (gated on Phase 8) · `Review` ❌ (no appraisal workflow) ·
> `Transfer` ❌ (no export). **Every unready member is *refused*, never absent** — widening an enum pinned
> into immutable published versions is the change this design exists to avoid. The ADR's deleted precedence
> ladder is annotated, since **it was the only place in the tree where `Transfer` and `Review` appeared at
> all** — which is how an enum declared *"closed by construction"* went its whole life with its members
> unwritten.
>
> ⚠ **One self-contradiction found and marked rather than fixed.** § Scope still lists *"any link to
> `PurgeVersion` or any other destruction primitive"* as out of scope, and `Destroy`'s readiness depends on
> exactly that link. **Phase 8 owns removing that row** (its checklist says so), so it is struck-through and
> marked pending rather than removed here.

## Phase 13 — Ten-year position (unit 11)

**DEC-13 · closes AD-34.** Every stated limit in the model came from a runtime constraint — an API Gateway
timeout, a DynamoDB item size, an event-replay cost — each well reasoned on those terms. **None came from
the domain.**

- [x] Write **what a large tenant looks like after a decade** — the platform's own statutory default.
      *(AD-34, DEC-13)* — **Files:** `docs/spec/architecture/system-architecture.md`,
      `docs/spec/shared/operations.md`. **Acceptance:** a stated domain timescale exists, and it is retention,
      not infrastructure.
- [x] **Derive the missing bounds from it:** a saga-row TTL, a stale-registration sweep, a partition
      strategy for job summaries. *(AD-34)* — **Files:**
      `docs/spec/contexts/Processing/sagas/assetingestionsaga.md`,
      `docs/spec/contexts/Registration/aggregates/Registration/registration.write-model.md`,
      `docs/spec/contexts/Processing/aggregates/ProcessingJob/processingjob.read-model.md`. **Acceptance:**
      the unbounded quantities are exactly the ones a records tenant accumulates, and each now has a bound
      traceable to the position.
- [x] Say what a **hold outliving a saga TTL** does. *(DD-3's open edge)* — **Acceptance:** answered, not
      left to inference.

## Phase 14 — Governance records freeze on close (unit 12)

**DEC-8 · closes AD-23. Applies Phase 4 rather than inventing its own path. Depends on Phase 4.**

- [x] A **resolved or abandoned `ChangeRequest` accepts no further comment edits or deletions.** *(AD-23,
      DEC-8)* — **Files:**
      `docs/spec/contexts/ChangeRequests/aggregates/ChangeRequest/changerequest.write-model.md`,
      `docs/spec/contexts/ChangeRequests/aggregates/ChangeRequest/changerequest.scenarios.md`.
      **Acceptance:** the governance container stops being mutable after the change lands.
- [x] Corrections use **Phase 4's** attributed, reason-bearing, append-only act — **not a local one.**
      *(DEC-20)* — **Acceptance:** a reader of *why this change was made* sees the original and the
      correction; a flat freeze would have pushed that need somewhere worse.

## Phase 15 — Un-archive, keeping the name reservation (unit 13)

**AD-12 · DEC-14.** Archive is irreversible everywhere, and it releases the name.

- [x] Specify **un-archive**, retaining the name reservation across the archive/un-archive cycle. *(AD-12)*
      — **Files:** `docs/spec/contexts/Catalog/aggregates/Collection/collection.write-model.md`,
      `docs/spec/contexts/Catalog/aggregates/MediaItem/mediaitem.write-model.md`,
      `docs/spec/shared/cascade-rules.md`. **Acceptance:** un-archiving cannot fail on a name another
      aggregate took in the interval; the cascade blanks AD-12 names are filled by Phase 1's rule rather than
      restated here.

> ### ✅ Phases 13, 14 and 15 landed 2026-09-15 — **every spec-reachable phase in this plan is now done**
>
> **Phase 13.** `operations.md` gained **§ The ten-year position** — the platform's own statutory default is
> 10 years, so that is the design horizon — with the shape of a large tenant at a decade, and the three
> bounds derived at their own sources: a **terminal-saga-row TTL** (`assetingestionsaga.md`), a
> **stale-registration sweep** (`registration.write-model.md`), a **time-keyed job-summary partition**
> (`processingjob.read-model.md`). `system-architecture.md` carries the horizon where every runtime-derived
> limit lives. **The one-line summary worth keeping: *the bounded quantities are the ones that would break a
> Lambda; the unbounded ones are the ones a records tenant accumulates.***
>
> **DD-3's open edge answered on a distinction rather than a carve-out:** a hold applies to **records**, and
> **a saga row is not one** — it is a coordination artefact whose outcome lives on the aggregates and whose
> events live in the store. So a hold never suppresses the TTL and the TTL never weakens a hold. ⛔ **But a
> non-terminal row is never expired**, hold or not. And if a future saga ever carries state that *is*
> evidence, **that state belongs on an aggregate** — the TTL is the reason to put it there, not an exception
> to carve out of it.
>
> **Phase 14.** The `IsOpen` check lands on `EditComment`/`DeleteComment`, **checked first per this module's
> own CR-19 rule** — they were the one pair that did not follow it. Corrections go through **Phase 4's
> shared act**, and this is **consumer 1 and the first to be built**, deliberately: the narrowest of the six,
> proving the concept on a comment before it carries a disposal clock or a record of destruction.
> ⚠ **MM-040's DF-17 is corrected in the spec**: the prior text *is* recoverable from the stream, so this
> was **never an audit hole** — the defect is a closed governance record accepting mutation, plus
> legibility from the aggregate.
>
> **Phase 15.** `Unarchive` on `Collection` and `MediaItem`, **retaining the name reservation across the
> cycle** — which is the load-bearing half: *an un-archive that can fail on a name collision is not a
> recovery path; it works when nothing else happened and fails exactly when the archive has been in place
> long enough for someone to reuse the name.* **One change fixes two defects** — this and the archived-`Move`
> reservation from Phase 10, both from **treating archive as an end state for the *name* when it is not an
> end state for the *record***. It also settles something never stated as a choice: the spec recorded the
> absence of un-archive **three times and never said it was deliberate**.
> ⚠ **The cascade half stays a proposal** — restoring a container does not restore its children — and is
> row 3 of the four cascade questions awaiting Chase.

---

## The residue — AD-21, deliberately unplanned

**Cross-context guards are point-in-time where the domain needs standing constraints.** Guards check
eligibility once and never again; retention, hold, custody, obligation and closure are all **durations**.

Four decisions narrow it — DEC-10 (a guard can know a fact is stale), DEC-11 (failure becomes visible),
DEC-16 (containment becomes faithful, though **not synchronous**), DEC-3 (hold is a standing constraint in
one place). **None removes it.** Nothing yet lets a relationship *require* a fact to remain true.

**This is a design concept to add, not a defect to schedule.** It is recorded here so the next session
finds it and does not mistake its absence from the phases for an oversight. Raising it as work means a new
review, not a checklist item here.

---

## Findings discovered during execution

A new finding **never** becomes a new checklist item in this plan. It goes to the global drift register
with an `X-` number (MM-022), or to a new review in the appropriate workstream — ask which when it is not
obvious. If a new finding invalidates this plan's approach, **stop**: do not re-plan in place. Record every
such diversion in § Session log.

### Raised 2026-09-14, working Phases 0–2

**Three items. None is a new checklist box; two need Chase.**

| # | What | Kind | Where it goes |
|---|---|---|---|
| 1 | **X-11.41 is mis-described.** `cross-aggregate-invariants.md` § Stated but not enforced called `FolderMediaItemsIndex` *"add-only… no removal on archive, delete or move"* and drew two consequences from it. **Source disagrees:** all four projectors are registered, so removal on move and on archive both work and neither consequence follows. The real gap is `MediaItemAssignedToFolder` and `MediaItemDeleted`. `archive-fan-out.md` § D-1 had it right since 2026-08-25 — **two spec files contradicted each other.** The spec text is corrected in place; **the finding's own text and severity are not mine to edit** | **Correction to an existing finding** — not new | **MM-022.** Re-write X-11.41 against source and re-assess severity. ⚠ It also means **MM-042's AD-26 premise was wrong**, which is a note for the review's record |
| 2 | **The four cascade questions need a ruling** — `ChangeRequest` on item archive/delete · `ProcessingJob` on asset delete · un-archive and cascade reversal (pre-empts **Phase 15**) · counter reconciliation (this one is **X-11.43** and needs no ruling). Proposals written and marked **proposed**; nothing implementable | **Decision owed** | **Chase.** Ruling them unblocks nothing immediately — Phases 3+ do not wait — but they sit in the spec as proposals until ruled |
| 3 | **DEC-1 grants a per-item retention override; ruling 3 of the retention design forbids one.** Recorded as amended in DEC-1's favour | **Already owned** — it is **DD-5**, and **Phase 4** carries it | No action. *(Flagged for a ruling in an earlier revision of this file; that was my error and is corrected.)* |
| 4 | **Does Q-3's freeze unblock `MoveFolder` on an archived folder?** Q-3 says *filing operations stay legal* and *applies once across all three on the same terms* — but `Folder` **already guards `MoveFolder` on `IsArchived`**, while `MediaItem.Move` is being unblocked on archived items for exactly the filing argument. One of the three sits on the other side of the line and Q-3 did not notice. **Two defensible answers:** unblock it for consistency, or keep it blocked because moving a *container* relocates every record beneath it and is a larger act than re-filing one item | **Decision owed** — a gap in a decision, not a new finding | **Chase.** Phase 10 left the guard as-is and flagged it in `folder.write-model.md`. Does not block Phases 11–15 |

---

## Session log

| Date | What moved | What did not | Next concrete action |
|---|---|---|---|
| 2026-09-14 | Plan created from MM-042 as **MM-043**, `status: active`. Sixteen phases written from DEC-1 … DEC-24 with spec targets and acceptance checks; both READMEs indexed; MM-042 closed `done` / `outcome: plan`. Desktop Commander verified working for filesystem **and** process execution on this machine. | No spec file touched yet. No branch cut. `mgq-magiq-media-infra` not connected. | **Phase 0** — correct the retention text in `retentionschedule.design-decisions.md`, then sweep the profile-level statements. Text only; it needs no shell and no infra repo. |
| 2026-09-14 | **Phase 0 complete — all three boxes ticked.** Seven files in `mgq-magiq-media\docs\` edited (three named by the phase, four found by its own acceptance grep — including `mediaitem.write-model.md`, which said nothing about retention and now carries a pending-Phase-7 note, and `domain-model.md`, which gained a `MediaItem → RetentionSchedule` row). Acceptance grep clean: no unmarked "resolved through `MediaProfile`" statement survives. **The two-incompatible-placements window that DEC-18 called the review's one open exposure is closed.** | **Nothing committed, no branch cut** — the sandbox shell could not mount the drives this session, so no `git`. Edits are working-tree only. No code touched (Phase 0 is text by definition). `mgq-magiq-media-infra` still not connected. No Control Tower card comment written — still outstanding for MM-042 and MM-041 too. | **Chase: check the branch and commit the seven doc files**, then append the branch to `branches:`. **No ruling is owed on the DEC-1 ↔ ruling-3 override contradiction** — Phase 0 marked ruling 3 amended, and the substance is **DD-5, owned by Phase 4** (correction-by-append names the retention override as a consumer and specifies the act). An earlier revision of this log and of the Phase 0 note said otherwise and asked for a ruling; corrected in the same session. Next workable unit is **Phase 1 + Phase 2 together** — spec-only, no shell needed. |
| 2026-09-14 | **Phases 1 and 2 complete** (Phase 1 box 2 partial — see below). Seven more files edited, five of them new this session. **Phase 1:** the completeness rule is generalised to **five mechanisms** with a reviewer test each, mechanism 2 carries the composition test, `saga-patterns.md` gained the *what kind of process is this?* gate, and **DD-2 is written up as the worked example in both files** — the rule catching a defect DEC-1 was about to create. **Phase 2:** § Containment enumerates both indexes, the CLI clear-before-replay rule is specified, `IsComplete` is qualified as a traversal claim, and **faithful-is-not-synchronous** is written where Phases 7 and 8 can cite it. **Phase 2 also corrected its own premise against source** — see § Findings #1. | **Nothing committed; still no branch and no shell** (the sandbox could not mount the drives again). **Phase 1 box 2 is `[~]`, not `[x]`**: the four cascade answers are written as **proposed** because rows 1–3 are decisions MM-042 never took and this plan takes none. **No code touched** — Phases 1 and 2 are spec by definition, and the Phase 2 code (two projectors + the CLI clear) is deliberately unstarted. Control Tower card comments still unwritten for MM-041, MM-042 and MM-043. | **Chase: commit fourteen doc files** across `mgq-magiq-media\docs\` (check the branch first), then **rule the four cascade questions** in `cascade-rules.md` and **re-write X-11.41 against source** in MM-022. Next workable unit is **Phase 3 — Fixity (unit 2)**, which is independent of everything landed so far and is *"the only remedy whose cost rises with every object stored"*. Phase 4 should not slip far behind it — four later phases consume it. |
| 2026-09-14 | **Phases 3 and 4 complete — all seven boxes.** Five of the six roots now have their prerequisite written down. **Phase 3:** the capture digest (SHA-256, both upload modes, immutable, *not* the S3 ETag) and the version manifest, plus § Fixity stated **across** the two contexts because neither could claim the guarantee alone. **Phase 4:** correction-by-append specified once with **six** named consumers — DEC-20 named three, DD-5 added the two overrides, and the sixth was already implied. *"Overridable afterwards"* now points at an act in all five places it appears. **Phase 4 also closes the DEC-1 ↔ ruling-3 residue** Phase 0 recorded. **Twenty-two doc files touched this session across Phases 0–4.** | **Still nothing committed, no branch, no shell** — third session running. **No code anywhere**: Phases 0–4 are spec by definition, and everything specified in 3 and 4 is marked ⏳ *designed, not built*. **Phase 1 box 2 remains `[~]`** pending Chase's ruling on the four cascade questions. Control Tower card comments still unwritten. | **Chase: commit — twenty-two files is getting large for one uncommitted tree.** Then two rulings: **the four cascade questions** (`cascade-rules.md`) and **X-11.41's re-write against source** (MM-022). Next workable unit is **Phase 5 — Repair, then freshness (unit 3)**: still spec, ordering forced inside it (repair before freshness), and it is the prerequisite Phases 7 and 8 both rest on. ⚠ **Phase 6 onward starts needing a shell and the infra repo.** |
| 2026-09-14 | **Phase 5's spec half and all of Phase 6 complete.** `consistency-model.md` gained **§ Repair** (a rebuild verb per index, all seven tabulated; `counters reseed` for the two counters; `--dry-run` specified as non-optional) and **§ Freshness** (`SourceVersion` **additive** to `ProjectedVersion`, not a replacement). Both forced orderings are now written in the spec rather than only in this plan, and **AD-21 is named where the contract is defined** — the reader who has just gained a freshness measure is the one most likely to assume the standing-constraint problem went with it. `operations.md` gained **§ Derived-state operations** with all five surfaces including holds; the AD-32 position is named at its source in `assetingestionsaga.md`; `archive-fan-out.md` and `documentsigningsaga.md` carry their halves; **AD-22 and AD-35 marked settled-by-visibility** with the reasoning for why that is a settlement and not a deferral. **Seven more files — twenty-nine across Phases 0–6.** | **Phase 5's code half is untouched** — it needs a shell and `mgq-magiq-media-infra`, neither available in four sessions now. **Still nothing committed and no branch.** Phase 1 box 2 still `[~]` pending the cascade rulings. No Control Tower card comments. | ⚠ **Chase: commit. Twenty-nine files in one uncommitted tree across four sessions is the main risk now** — a conflict or a stray `git checkout` loses the lot. Then the two rulings (four cascade questions; X-11.41 against source). ~~**After that the spec-only run is over**: Phase 7 needs Phases 2/4/5 *code*, so the next real unit is **Phase 5's code half**.~~ **Wrong — corrected in the next row.** Phase 9 has **no dependencies at all**, and 11, 12, 13, 14 and 15 are reachable without any code. |
| 2026-09-14 | **Phase 9 complete — the ownerless pinned-vocabulary seam now has an owner.** Specified at **both ends as one rule**: consuming side gets *a rule whose pinned member may be absent must be unrepresentable, not fall-through*, with a named `PinnedSchemaIncomplete`; producing side gets the reconstruction contract with its three failures tabulated; the ADR's *"the answer is contract work at the seam"* now says what that work is. **`ReviewPolicy` (DF-8) made authoritative on the publish path** ahead of Phases 10 and 11 — and specified with the `profile?.X ?? item.PinnedX` fallback `CheckoutPolicy` already uses, **because it has no pinned counterpart today and would otherwise fail open exactly when the projection is lagging**. **Four more files — thirty-three across Phases 0–6 and 9.** | ⚠ **The previous row's "spec-only run is over" was wrong and is struck.** Phase 9 depends on nothing; Phases 11, 12 (both on Phase 3 ✅), 13 (none), 14 (Phase 4 ✅) and 15 (none) are all reachable as spec. Only **7, 8 and 10** are genuinely gated — 7 and 8 on Phase 5's code, 10 on Phase 9's. **Still nothing committed, no branch.** Phase 1 box 2 still `[~]`. | **Chase: commit — thirty-three files now.** Then the two rulings. Next workable unit is **Phase 11 (Declaration)** or **Phase 12 (Disposal action vocabulary)**, both unblocked by Phase 3 and both spec; **Phase 13 and 15 are free-standing** if a smaller unit suits. **Phase 10 (Custody) is now unblocked by Phase 9** but is the largest remaining spec unit. |
| 2026-09-14 | **Phase 10 complete — eight of nine boxes, the largest spec unit in the plan.** Custody extends the lock to `Publish`/`Withdraw`/`Archive`/`Move` with three reasoned exclusions; **many editors, one custodian**; the no-op-`Withdraw` silent lock release closes with it. `If-Match` mandatory on multi-member sessions (`428`), **with the end of silent-ignore written in as load-bearing**. Auto-submit capped at `PendingApproval`, `RequiredForPublish` cannot self-declare, **"unreviewed" is a recorded property**, **D-7 retires** (both halves, neither sufficient alone), DD-6 stated with an announcement obligation and the affected tenants made identifiable. Move rules: hold blocks, custody blocks, **archive does not** — with the title-reservation defect fixed as part of the same decision. **Seven more files — forty across Phases 0–6, 9 and 10.** | **Box 9 is `[~]`** — see § Findings #4: Q-3's freeze is specified for `Collection` (including **`SetVisibility`**, the disclosure case) and `MediaItem`, but `Folder` already blocks `MoveFolder` when archived and Q-3's own *filing stays legal* argues it should not. Guard left as-is. **Still nothing committed, no branch, no shell** — fifth session. Phase 1 box 2 still `[~]`. | **Chase: commit — forty files.** Three rulings now owed: the four cascade questions, X-11.41 against source, and **`MoveFolder` on an archived folder**. Next workable: **Phase 11 (Declaration)**, **12 (Disposal actions)**, **13**, **14** or **15** — all spec, all unblocked. **Only Phases 7 and 8 are gated**, on Phase 5's code half. |
| 2026-09-14 | **Phases 11 and 12 complete — all five boxes.** Declaration is named at `MediaItemApproved` in a new § Declaration, with **no `Declare` command** and the reason stated as a design constraint; *declaration fixes content, not filing* is in the spec verbatim, with the appraisal-comes-after-declaration argument for why re-filing needs no extra guard. The `action` vocabulary is enumerated for the first time with a readiness verdict per member and the rule that **an unperformable action is refused, not absent**. **Four more files — forty-four across Phases 0–6 and 9–12.** | ⚠ **One self-contradiction marked, not fixed**: § Scope of the retention design still calls any link to `PurgeVersion` out of scope, while `Destroy`'s readiness depends on that link — **Phase 8 owns removing the row**, so it is struck and marked pending. **Still nothing committed, no branch, no shell.** Boxes still `[~]`: Phase 1 box 2 (cascade rulings), Phase 10 box 9 (`MoveFolder`). | **Chase: commit — forty-four files.** Three rulings unchanged. Next workable: **Phase 13 (Ten-year position)**, **14 (Governance freeze on close)** or **15 (Un-archive)** — all spec, all unblocked, and 14 is the one that applies Phase 4's correction-by-append to its first real consumer. **Phases 7 and 8 remain the only gated units.** |
| 2026-09-15 | **Phases 13, 14 and 15 complete — all six boxes. ▶ Every spec-reachable phase in this plan is now done: 0–6 and 9–15, thirteen of sixteen.** Phase 13 states the **ten-year horizon** and derives three bounds at their own sources, answering DD-3's hold-vs-TTL edge on the distinction that **a saga row is not a record**. Phase 14 freezes governance records on close and is **correction-by-append's first consumer**, deliberately the narrowest of the six. Phase 15 specifies `Unarchive` **retaining the name reservation** — one change fixing two defects, both from treating archive as an end state for the *name* rather than the *record*. **Nine more files — fifty-three across the whole run.** | **The three remaining phases are 5's code half, 7 and 8 — all gated on a shell and `mgq-magiq-media-infra`**, neither available in six sessions. **Nothing is committed and no branch has been cut.** Two boxes stay `[~]` pending rulings: Phase 1 box 2 (four cascade questions) and Phase 10 box 9 (`MoveFolder`). No Control Tower card comments for MM-041, MM-042 or MM-043. | ▶ **Chase: the spec work is finished — commit it.** Fifty-three files, six sessions, one uncommitted tree. Then the **three rulings**: the four cascade questions (row 3 now half-settled by Phase 15), X-11.41 against source, and `MoveFolder` on an archived folder. **After that MM-043 needs a working shell and the infra repo to go any further** — Phase 5's code half is the entry point, and Phases 7 and 8 follow it. **The plan does not move to `done` until Chase agrees and a branch is recorded in `branches:`.** |
| 2026-09-15 | ▶ **Closed `done`, scope narrowed to spec. Chase committed and pushed the fifty-three files to `spec/initial-alignment` and agreed the plan can be completed.** MM-042 and MM-043 archived together in the same session; both README rows moved to their archive sections. | **The code was never worked and is now unowned** — Phase 5's code half, 7 and 8. **This is the project's third ownerless gap**, and the pattern is the one § Scope explicitly warns against. Branch recorded: **`spec/initial-alignment`**. Two rulings still owed (four cascade questions; `MoveFolder` on an archived folder), plus X-11.41's re-write, which belongs to MM-022. | **Resuming means implementing, not re-deciding** — all 24 decisions are written down with files and acceptance per phase. Entry point is **Phase 5's code half**, once a shell and `mgq-magiq-media-infra` are available. **Of the three, Phase 3's fixity is the most expensive to leave**: its cost rises with every object stored. |

---

## Closing out

This plan moves to `done` **only** when Chase agrees the work is implemented and complete, **and** at least
one branch is recorded in `branches:`. The close-out card comment records every branch it was committed to.
The review and the plan are then archived **together**, in the same session — `reviews/aggregate-design/Archive/`
and `plans/aggregate-design/Archive/` — and the rows move into the archive sections of both READMEs rather
than being deleted. **Archiving is never automatic; propose it, and Chase confirms.**

Every session, including one that achieves nothing: update the checklist, write `status:` in the same edit
as whatever made it true, append any branch cut to `branches:`, add a § Session log row, and write the
closing card comment naming **what moved, what did not, and the next concrete action**.
