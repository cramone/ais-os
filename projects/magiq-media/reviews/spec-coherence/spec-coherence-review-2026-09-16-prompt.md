# Prompt — MM-044 · spec-coherence

Paste into a fresh session. It assumes no context from any previous one.

---

## Where you are

- **Project slug:** `magiq-media`
- **Project folder (AI-operating-system layer):** `Z:\claudia\magiq\projects\magiq-media`
- **Code + spec repo:** `D:\source\github\sprbrk-standard\mgq-magiq-media`
- **Review:** `MM-044`, at
  `Z:\claudia\magiq\projects\magiq-media\reviews\spec-coherence\spec-coherence-review-2026-09-16.md`
- **Plan:** `MM-045` — **does not exist yet.** See § The gate.
- **Todo id:** derived, not allocated. Get it with `cycle.todo_id_for('magiq-media', 'MM-044')` if you need
  it; the board renders the card from the file on every read.

**Your first action, before reading anything else:**

```bash
python -c "from tower import cycle; cycle.comment('magiq-media', 'MM-044', 'Picked up. Found it at <status>, <n> open questions. Starting <what>.')"
```

The card's status is projected from front-matter and is **not settable from the board** — do not try. Status
changes are made by editing `status:` in the file, and only there.

---

## What this review is

A design review of the magiq-media **specification documents** — aggregate by aggregate, then the
relationships between them — looking for design flaws, inconsistencies, contradictions and invalid
invariants. It carries roughly 190 findings across eleven aggregates, nine relationship edges, ten systemic
patterns and four spec-integrity findings.

Read `MM-044` in full before doing anything with it. Its `## Scope` states the method; its
`## Recommended sequencing` states the phase order and the three convergence loops, and is the thing
`MM-045` transcribes.

---

## Scope — read this and nothing else

**In scope:** `D:\source\github\sprbrk-standard\mgq-magiq-media\docs\` — the whole of `spec\` and `adrs\`.

**Out of scope, by standing instruction:**

- **Repository source code.** Do not read it. Do not reason from it. This review's findings are statements
  about what the documents say, and a finding that depends on what the code does is out of scope, not a
  better finding. Where the spec and the code disagree the code wins — but establishing that is a different
  workstream with a different method.
- **Authorization and permission rules.** Who may call what, role claims, ownership checks. Where a finding
  sits next to an authorization rule, take only the non-authorization half. `authorization-matrix.md` and
  `magiq-auth-role-claims-requirements.md` are explicitly excluded from the missing-files work.
- **Any other review, drift register or audit document in either tree.** They did not inform MM-044 and must
  not inform its successors, or the register stops being independently reproducible — which is what makes
  the Loop C re-baseline meaningful.

**Anything you find outside scope** does not go into MM-044's findings. Surface it and ask where it belongs.

---

## How to work findings

- **Evidence before conclusion.** Quote the text, then say what is wrong with it. A finding with no quote is
  an opinion.
- **Cite `file ~line`.** Line numbers are approximate by convention here and were taken 2026-09-15; they
  locate the statement, they are not a commitment to a revision.
- **Severity is `Critical | High | Medium | Low`.** Never 🔴 / 🟠 — those belong to `type: gate` documents
  and mean something different (they are a claim about a release decision, not about a defect).
- **Finding ids are the per-aggregate prefixes already in use** — `AS` `PJ` `CO` `FO` `MI` `MP` `CR` `RT`
  `RS` `RG` `DS` `R` `E` `SI`. They are stable. Never renumber. New findings continue the relevant
  sequence. This departs from the usual one-prefix-per-workstream rule and the departure is recorded as an
  `exception:` in the front-matter.
- **Do not fix anything during a review.** Not the spec, not the code. A review argues; a plan sequences.
- **"Not built" is not a finding on its own.** A rule that *depends on* unbuilt machinery is.
- **Never write an off-repo id into a spec edit.** No `MM-nnn`, and pending Q14 no `DEC-`, `AD-` or `X-`
  either. The governing rule is the repo's own `CLAUDE.md`: *"Decisions related to changes or reasons do
  not belong in the spec files. Spec files need to remain pure finalized documents."* A reason worth
  keeping goes to an ADR or a `<agg>.design-decisions.md`, in-tree and by name rather than by number.

---

## The gate

**Do not write the plan until both are true:**

1. Every `## Open Questions` entry reads `**Answered:**`. **All fourteen do, as of 2026-09-16** — ten from
   records-management and media-management practice with the reasoning stated, four from Chase. Do not
   re-open an answered question because you would have decided it differently; each answer carries its
   argument, and overturning one is a decision, not an edit.
2. **Chase has moved the review to `status: findings-agreed`.** This is a transition he makes, not one you
   infer. Zero open questions is necessary and not sufficient — check the front-matter, and if it still
   reads `draft`, the gate is shut however finished the review looks.

**Three answers you will otherwise re-derive wrongly:**

- **There are no subscribers to `media.item.published`.** E-1 is a documentation fix with no migration and
  no notice owed to Search/Discovery, Billing or Notifications.
- **The two bulk-import aggregates are removed from the spec**, not written. Inventory becomes nine coded
  plus two specified-and-unbuilt. This does not touch the inline bulk *endpoints*, which are unaffected.
- **No `MM-nnn` id exists, and none should ever have been cited in a spec file.** Not a dependency, not a
  supersede target, not an authority. All 43 citations across 14 files are stripped (**SI-5**), and every
  rule whose status or scope was expressed as a phase of one is restated in its own terms. Do not defer to
  one, do not go looking for one, and do not write one into any front-matter or any spec edit.
- **`DEC-n` is the decision log of MM-042, a prior aggregate-design review — the same job this review does.**
  All fourteen cited decisions are already recovered and re-adjudicated in **§ Recovered decisions**; read
  that table before touching retention, declaration, correction-by-append or the archive cascade. Ten are
  adopted, one extended, **DEC-9 is overturned** (the disposal clock does not re-stamp on a move), and
  **DEC-3 is adopted as new scope** — legal hold, raised as **RS-9**. Do not go looking for MM-042; the
  decisions no longer depend on it. Eight `DEC-` numbers were never cited and are gone — if you find a
  rule that seems to assume one, treat it as an undocumented rule and raise it, do not invent the decision.
- **`AD-n` and `X-n.n` are finding ids and are stripped outright** (**SI-6**). Keep the correction and the
  date, drop the number.

**Before minting any id, re-check the high-water mark — including this review's own.** MM-044 and MM-045
were minted from the highest id appearing in the repo spec, because `projects\magiq-media\reviews\` and
`plans\` did not exist when this review was written. **That basis is now known to be worthless**: those
citations should never have been in the spec, so they were never evidence about the id space. The true
high-water mark is unknown. Run the real grep first:

```bash
grep -rhoE '^id: [A-Z]+-[0-9]{3}' projects/magiq-media/reviews projects/magiq-media/requests projects/magiq-media/plans projects/magiq-media/_archive | sort | tail -1
```

If it returns anything above `MM-043`, MM-044 and MM-045 collide and must be re-minted before any
cross-reference is written to them. If the tree is genuinely empty, they may be renumbered from MM-001 —
tidier, and equally valid while no document points at them. Either way it is Chase's call, not a cleanup
step: a duplicate id is a data error, and ids are never silently renumbered.

---

## Writing the plan

Once the gate is open, write `plans/spec-coherence/spec-coherence-review-2026-09-16.md` — the plan takes the
primary review's filename.

Front-matter:

```yaml
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
created: <today, from the session environment — never from memory>
---
```

No `exception:` line, no `supersedes:`, and nothing in `depends-on` or `blocked-by-external`. This
workstream has no dependencies — see MM-044 § Dependencies.

Then phases. **A phase is a `## Phase <N> — <name>` heading**, an intro line, then a checklist of `- [ ]`
items each small enough to finish in one session. Every item names the finding id it closes and its
acceptance check. The heading shape is not cosmetic — `ado-create-from-plan` reads it.

The eleven phases and their contents are in `MM-044` § Recommended sequencing. Transcribe them; do not
re-derive the order. Its rationale — outermost-authority first, decisions before edits — is the argument the
review makes and the plan is not the place to re-open it.

**Acceptance checks must be verifiable by reading the spec**, because this plan changes documents only.
"`grep -rn 'media.item.published' docs/` returns zero hits outside a historical note" is an acceptance
check. "The Billing consumer receives the event" is not — that is a different workstream.

**Every item ends with its Loop A ripple sweep** (MM-044 § The loops). Every phase ends with the Loop B
exit gate. Phase 11 is Loop C.

`ado:` stays `-`. Pushing a plan to the board is a separate, explicit step run through
`ado-create-from-plan`, and most plans never go. Omit the `## ADO mapping` block entirely unless Chase says
this workstream is board-tracked — do not fill it with placeholders.

The plan must contain a `## Closing out` section stating that it moves to `done` only after Chase agrees the
work is complete, that the close-out comment records every branch it was committed to, and that the pair is
then archived on both sides in the same session.

### Hand-over

Not complete until all four have happened: plan written, review moved to `status: done` / `outcome: plan`,
**both** READMEs updated, dependency status resolved. Report hand-over complete explicitly before any
execution starts.

---

## Re-baseline (Loop C)

MM-044 § Recommended sequencing designates **this prompt file** as the source for the re-baseline. When
Phase 11 runs:

- Start a **fresh session** with no context from the remediation. That isolation is the whole point — a
  reviewer who knows what was fixed will not see what was missed.
- Use the § Scope and § How to work findings sections above, unchanged.
- Produce a finding register in the same shape, then diff it against MM-044's.
- **Zero `High`+ tracing to MM-044's scope** → the plan may close. **Any `High`+ in scope** → the plan
  re-opens at the owning phase and Loop C runs again. **Any `Critical`/`High` outside scope** → a new
  review, never a re-open.
- **Three iterations maximum.** Failing to converge in three means the spec's structure rather than its
  content is the problem; say so and stop. That conclusion is the deliverable, not a failure to finish.

---

## Working the plan, session to session

- **Tick checkboxes in the file as work lands.** The next session resumes from the file, never from chat
  history.
- **A new finding never becomes a checklist item in the plan that found it.** It goes to the drift register
  with an `X-` number or to a new review — ask which. The only permitted mid-execution edits are ones that
  close, split or correct an item tracing to a finding id the plan already consumes; a split keeps the
  original finding id on both halves.
- **If a new finding invalidates the plan's approach, stop.** Do not re-plan in place. Say so; Chase decides
  whether the review reopens or a new one starts.
- **End of session, every time:** update the checklist, update front-matter `status:`, append any new branch
  to `branches:`, and write the closing card comment — what moved, what did not, and **the next concrete
  action**. Write it even when nothing moved; that is the entry that answers "where am I up to".
