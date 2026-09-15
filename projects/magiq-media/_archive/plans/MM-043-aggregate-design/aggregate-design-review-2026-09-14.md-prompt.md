# Aggregate design remediation — paste-ready session prompt for writing the plan

You are opening the **plan** for a review that is already `findings-agreed`. This prompt assumes you have
**no context from any previous session**. Everything you need is below or at the paths it names.

> ## ⛔ Read this first
>
> **Every design decision is already taken.** Twenty-four of them, worked item by item with Chase and
> recorded in the review's § *Decisions on findings*. **Your job is to sequence work, not to re-decide
> anything.** If a decision looks wrong, say so and stop — do not quietly plan around it.
>
> **The review is spec-only by declaration.** No code was read. So **every unit below is a design change
> that must land in `docs/` first**, and the code shape for each is unscoped on purpose. Do not assume a
> finding describes the running system.

---

## Where you are

| | |
|---|---|
| Project slug | `magiq-media` |
| Project folder | `Z:\claudia\magiq\projects\magiq-media` |
| **Consumes** | **MM-042** — `reviews/aggregate-design/aggregate-design-review-2026-09-14.md`, `status: findings-agreed` |
| Plan file to create | `plans/aggregate-design/aggregate-design-review-2026-09-14.md` *(same filename as the review — that is the convention)* |
| Spec and ADRs | `D:\source\github\sprbrk-standard\mgq-magiq-media\docs\` — the only copy, nothing published or mirrored |
| App code | `D:\source\github\sprbrk-standard\mgq-magiq-media\src\` |
| CDK / infra | `D:\source\github\sprbrk-standard\mgq-magiq-media-infra` — **not a connected folder by default; add it before any code unit** |
| Workstream slug | `aggregate-design` |
| Plan id | **Mint the next free `MM-` id** via the `review-cycle` skill. ⚠ **MM-042 was assigned by hand and may not be free — verify it before minting anything after it** |
| Finding prefixes | `AD-` (model as specified) · `DD-` (the decided design) · `DEC-` (decisions) |

## First actions

1. **Verify MM-042's id is free**, then create the plan through the `review-cycle` skill: `type: plan`,
   `workstream: aggregate-design`, `consumes: [MM-042]`, `status: active`, `ado: -`.
2. Write a card comment recording what you are picking up:

   ```bash
   python -c "from tower import cycle; cycle.comment('magiq-media', '<your id>', 'Opening the aggregate-design plan from MM-042; starting unit 0')"
   ```

   Run from the AIS-OS repo root (`Z:\claudia\magiq`). Status is **projected from front-matter and cannot be
   set from the board** — a `PATCH` returns 409.
3. **Index the workstream** in `plans/README.md`. A folder nobody indexed is a folder the next session
   won't find.

## What to read, in this order

1. **MM-042 § The verdict** — including the ⚠ *Superseded by the decisions* block, which reorders it.
2. **MM-042 § Decisions on findings** — DEC-1 … DEC-24. **The whole section.** This is the plan's input.
3. **MM-042 § Recommended sequencing** — the ✅ *Revised after the decisions* table is the live order; the
   table below it is kept for its reasoning only.
4. **MM-042 § Coherence re-run** — six rounds. Rounds 3, 4 and 5 contain the ordering constraints.
5. `D:\source\github\sprbrk-standard\mgq-magiq-media\CLAUDE.md` — stack, conventions, module and host layout.
6. Only then the individual findings, as each unit needs them.

---

## The decisions, in one table

**Do not re-open any of these.** Read the review for the reasoning; this is the index.

| | Decision | Closes |
|---|---|---|
| **Q-1** | The `MediaItem` **is** the record; published versions are fixed manifestations | AD-5 |
| **Q-2** | Multi-member sessions ordered by **mandatory `If-Match`** | AD-4 |
| **Q-3** | Archived: **content frozen, custodial operations legal** | AD-2, AD-11 |
| **Q-4** | `PurgeVersion` is **disposition** | → DEC-3 |
| **DEC-1** | **Retention pinned on the item**, copied from the profile at creation, stamped at folder closure | AD-8, part of AD-13 |
| **DEC-2** | Fixity: **capture digest *and* version manifest** | AD-29, AD-18 |
| **DEC-3** | **Full hold model** + `PurgeVersion` becomes a named, authorised, recorded, **refusable** disposition act | AD-15, AD-31 |
| **DEC-4** | Lock covers **custody**; session initiator holds it; members edit content, not lifecycle | AD-3 |
| **DEC-5** | **Approval declares** the record | AD-5 |
| **DEC-6** | Auto-submit may submit, **never declare** | AD-1 (pt 1) |
| **DEC-7** | Move: **hold blocks, custody blocks, archive does not**; always audited | AD-1 (pt 2) |
| **DEC-8** | Governance records **freeze on close**, with a correction act | AD-23 |
| **DEC-9** | A re-filed record **takes the disposal of its new file** (re-stamp, audited) | amends DEC-1 |
| **DEC-10** | **Repair, then freshness** — rebuild the seven indexes, seed the counters, then source-relative versions | AD-33, AD-27 |
| **DEC-11** | **Read-only** operator surface first | AD-32, AD-22, AD-35 |
| **DEC-12** | Disposal actions **enumerated and gated on capability** | AD-30 |
| **DEC-13** | State a **ten-year position**; derive the bounds from it | AD-34 |
| **DEC-14** | Fourteen findings accepted as stated | AD-2, 4, 6, 10, 11, 16, 18, 19, 20, 21, 22, 24, 25, 35 |
| **DEC-15** | **Generalise the completeness rule** to cascades, query-service reads, aggregate-loaded relationships, sagas | AD-28, AD-20 |
| **DEC-16** | **Make the containment projection faithful** — full MediaItem event set; CLI clears before replay | AD-26 |
| **DEC-17** | **Declaration fixes content, not filing**; re-filing is the same audited act either way | clarification |
| **DEC-18** | MM-041 stays closed; **this plan corrects the spec** | accepted risk |
| **DEC-19** | **Defer export**; `Transfer` enumerated and refused until one exists | refines DEC-12 |
| **DEC-20** | **Correction-by-append, designed once** — attributed, reason-bearing, never overwriting | generalises DEC-8 |
| **DEC-21** | **Classification moves to the item** too | closes AD-13 |
| **DEC-22** | **`ReviewPolicy` becomes real on the publish path**; declaration records whether it was reviewed | DD-1, D-7 |
| **DEC-23** | The closure stamp is built as **a real saga** | DD-2 |
| **DEC-24** | DD-3, DD-4, DD-5, DD-6 fold into existing units | — |

---

## The sequencing — this is the live order

**Copy it into the plan as the phase structure.** Heading shape is load-bearing:
`## Phase <N> — <name>`, because `ado-create-from-plan` reads it.

| # | Unit | Decisions | Depends on |
|---|---|---|---|
| **0** | **Correct the retention text in the spec** — DEC-1's item-level pin supersedes MM-041's D3 profile-level gate. **Text only, not the implementation** | DEC-18 | — |
| **1** | **Generalise the completeness rule** | DEC-15 | — |
| **1b** | **Faithful containment** — full MediaItem event set, CLI clears | DEC-16 | do with 1 |
| **2** | **Fixity** — capture digest + version manifest | DEC-2 | — |
| **2b** | **Correction-by-append, once** | DEC-20 | — |
| **3** | **Repair, then freshness** | DEC-10 | 1b |
| **4** | **Read-only operator surface** — *including holds* (DD-3) | DEC-11, DD-3 | 3 |
| **5** | **Retention *and classification* on the item** — two pieces: the pin, and the **closure-stamp saga** | DEC-1, DEC-9, DEC-21, DEC-23, DD-4 | 1b, 2b, 3 |
| **6** | **Disposition as a named act, then hold** | DEC-3 | 1b, 3, 5 |
| **7** | **Custody** — lock covers lifecycle, initiator holds custody, auto-submit capped, move guards, `ReviewPolicy` real on publish | DEC-4, DEC-6, DEC-7, DEC-22, Q-2, DD-6 | 9 |
| **8** | **Declaration** — approval declares; fixes content, not filing | DEC-5, DEC-17 | 2 |
| **9** | **The pinned-vocabulary seam**, as one problem | AD-7/AD-17 | — |
| **10** | **Disposal action vocabulary**, gated; `Transfer` refused until export exists | DEC-12, DEC-19 | 2 |
| **11** | **Ten-year position** and the bounds from it | DEC-13 | — |
| **12** | **Governance records freeze on close** — applies 2b | DEC-8 | 2b |
| **13** | **Un-archive, keeping the name reservation** | AD-12 | — |

### Forced orderings — four, and they are not preferences

1. **DEC-10 internally: repair before freshness.** The freshness change alters the schema of the seven
   cross-context indexes, and a schema change to them is *"a manual in-place rebuild"* that **no tool
   performs**. You cannot do the second without the first.
2. **Unit 1b before units 5 and 6.** DEC-1's closure stamp fans out over a folder's contents and DEC-3's
   hold can apply to a file — both assume containment is trustworthy, and today it is add-only.
3. **DEC-3 internally: disposition before hold.** A hold must be able to *refuse a disposition*; until
   `PurgeVersion` is a named act there is nothing to refuse.
4. **Unit 9 before unit 7.** DEC-6 requires auto-submit to read `ReviewPolicy`, which lives in the
   pinned-vocabulary seam. Doing 7 first makes it inherit the seam's defect.

---

## Traps — things a reasonable plan would get wrong

> ⛔ **Do not "fix" AD-26 by putting children on the parent.** A folder holding its children is an unbounded
> aggregate, and the spec's rejection of a downward walk is correct. **DEC-16 is the remedy** — make the
> derived view faithful, not authoritative. This trap was recorded twice in the review because it is the
> obvious wrong move.

- **Unit 0 is not unit 5.** Correcting the retention *text* is cheap and immediate; building item-level
  retention is unit 5. DEC-18 accepted a window where the spec carries **two incompatible retention
  placements** — unit 0 closes that window, and it is why the plan opens there.
- **Unit 5 is two pieces, not one.** The retention pin is a field change. The closure stamp is **a saga with
  state, correlation key, timeout, resume path and a status surface** (DEC-23). Size them separately; the
  saga leans on 1b far harder than the pin does.
- **DEC-20 is a prerequisite, not a deliverable.** Units 5, 6, 7 and 12 all consume correction-by-append.
  It sat last in an earlier draft and had to be promoted — do not push it back.
- **AD-21 is residue, not a unit.** *Guards are point-in-time where the domain needs standing constraints.*
  Four decisions narrow it; none removes it. **It is a concept to add, not a defect to schedule** — record
  it, do not plan it.
- **Do not re-raise anything with an owner.** DF-5/DF-6 → MM-032 · DF-7 → MM-025/026 · DF-11/DF-16 →
  MM-030/035 · DF-12 → MM-038 · X-4.15, X-11.x → MM-022.

## What MM-041 leaves you

**MM-041 is closed `done` and is not reopened** (DEC-18). Two things carry over:

- **Its D3 is superseded by DEC-1** — that is unit 0.
- **Its code was dropped and is unowned**, so **DF-1 … DF-4 are still live in the running system**: a
  confirmed registration still locks its folder permanently, a withdrawn item can still be freshly
  registered, and a governed edit can still publish under an abandoned change request. **This plan does not
  own them.** Do not silently inherit them, and do not silently leave them out of scope either — state the
  position in § Not in scope.

## Shape of the plan

**Spec and ADR first, per unit; code staged behind it.** Same shape MM-041 used and for the same reason:
these are design changes, so the corrected design has to be written down before it can be built.

Per unit: what changes, which spec files, the acceptance check, and the code shape **only where the decision
determines it**. Do not scope code in detail — the review read no code, so it would be guessing.

⚠ **Before any code unit:** a working shell (`mcp__workspace__bash`) **and** `mgq-magiq-media-infra`
connected. Every unit that adds a handler needs a `[MessageType]` entry in that repo's `sqs-queues.ts` as
well as `ConsumerRegistrations` — the two lists are a hand-maintained mirror with nothing enforcing the
match (**X-4.15**), and a handler missing from the allowlist **silently never delivers**. App-side-only is
not a partial unit, it is a broken one.

## ADO

`ado:` stays `-`. Pushing to the board is a separate explicit step through `ado-create-from-plan` once the
plan is `active`. **Do not create ADO items.**

## End-of-session protocol

Every session, including one that achieves nothing:

1. Update the checklist and the session log in the plan.
2. Update front-matter `status:` in the same edit as whatever made it true — the file is the only writer.
3. Append any branch you cut to `branches:`.
4. Write the closing card comment — what moved, what did not, **and the next concrete action**:

   ```bash
   python -c "from tower import cycle; cycle.comment('magiq-media', '<your id>', '<what moved, what did not, next concrete action>')"
   ```

   Lead with the outcome. Name unit and decision ids so entries are greppable. Two or three sentences; the
   timestamp and author are recorded for you.

**The plan is `done` only when Chase agrees the work is complete, and only with at least one recorded
branch.**
