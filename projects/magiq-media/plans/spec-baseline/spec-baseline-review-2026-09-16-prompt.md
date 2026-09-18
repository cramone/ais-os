# Execution prompt — MM-003, spec-baseline

Paste into a fresh session. It assumes no prior context.

> A prompt file beside a *plan* extends the convention, which defines one only for reviews. Same naming
> rule — `<plan-filename>-prompt.md` — and the same job: let a session pick this up cold.

---

## Where you are

**Project:** `magiq-media` · **Plan:** `MM-003` · **Consumes:** `MM-001`
**Plan:** `Z:\claudia\magiq\projects\magiq-media\plans\spec-baseline\spec-baseline-review-2026-09-16.md`
**Review:** `Z:\claudia\magiq\projects\magiq-media\reviews\spec-baseline\spec-baseline-review-2026-09-16.md`
**Repo:** `D:\source\github\sprbrk-standard\mgq-magiq-media` · **Branch:** `spec/initial-alignment-work`
**Todo id:** `a85d40df-3c91-5a96-b00d-94438dd9d1ba`

**State at hand-over:** phase 1 closed (all ten questions answered). Phase 0 written and **awaiting
commit**. Phases 2–10 untouched. 77 findings, all reachable from the plan.

## First action, before anything else

```bash
python -c "from tower import cycle; cycle.comment('magiq-media', 'MM-003', 'Picked up MM-003. Found: <state>. Working: <phase and items>.')"
```

Run from `Z:\claudia\magiq` so `tower` imports. The card's status is projected from the plan's front-matter
and **cannot be set from the board** — do not try.

## Second action — run the dependency gate

Required at every session start and every phase boundary, not just the first.

1. Read `depends-on` in the plan's front-matter: `[AP-001]`.
2. Resolve it — `grep -rn "^id: AP-001" Z:\claudia\magiq\projects\aspnetcore-platform` and read its
   `status`. **A review that has produced no plan resolves as unmet.**
3. Unmet is expected and is **not** a reason to stop. The dependency reaches phase 10 only; phases 0–9 run
   regardless. If AP-001 has since produced a plan, **repoint `depends-on` at that plan's id.**

## Read before editing anything

1. **The plan**, in full — especially § How this plan works and § Closing out.
2. **`D:\source\github\sprbrk-standard\mgq-magiq-media\CLAUDE.md` § Spec files state the specified system** — the rule every edit is
   measured against.
3. **`MM-001` § Open Questions** — ten answers, four of them decisions with rejected alternatives recorded.
   **This is the reasoning behind most of the plan's items.** An item that looks arbitrary usually has its
   justification there.
4. `Z:\claudia\magiq\projects\magiq-media\MEMORY.md`.

Read `MM-001`'s findings tables as you reach each phase, not upfront — 77 findings will not stay in your
head, and each plan item names the ones it closes.

## The four standing rules

These are in the plan and repeated here because they are the ones most easily lost mid-session.

1. **The guard is the acceptance check.** `python .github/scripts/docs_guard.py` from the repo root must
   return pass at every phase exit. Five checks: citations and links are hard zero; build-status, dates and
   structure are baselined. **The baseline may shrink and must never grow** — CI fails a change that grows
   it. If a new hit is a legitimate design statement, fix the wording rather than baselining it away.
2. **Never invent design.** If closing an item would mean asserting behaviour no document states and no
   `MM-001` ruling covers — **stop and ask.** A spec that is silent is a known gap; a spec that is
   confidently wrong is what this workstream exists to undo. Phase 6 is where this bites: it writes new
   specification, and several items say explicitly *"needs a value; ask rather than invent one"*.
3. **Never reintroduce what was removed.** No citation to anything undefined in `docs/`, no build or
   implementation status, no rationale, no open questions, no dates, no attribution. 430 citations and a
   tree's worth of build status came out on 2026-09-16; the guard catches the mechanical half.
4. **A new defect never becomes a checklist item here.** It goes to a new review, or to `MM-002`
   (`reviews/code-defects/`) if it is code. Only items tracing to a finding `MM-001` already consumes may
   be split, corrected or closed in place. **Log every diversion in § Session log.**

## Where to start

**Phase 0, third box: commit the guard.** `.github/scripts/docs_guard.py`,
`.github/docs-guard-baseline.tsv` and `.github/workflows/docs-guard.yml` are written and tested but not
committed. Everything after this is checked by what lands here; everything before it was not. Then delete
the `.github/scripts/__pycache__` orphan — the only surviving trace of a previous attempt that recorded its
guard as done and never wrote it.

Do not start phase 2 before phase 0 is committed and its workflow has run green on the branch.

## Phase order is not advisory

Phases 2 and 3 are what make 4–6 possible. The spec is a graph of quotations: aggregate specs quote the
domain model, derived surfaces quote write models, everything will quote the new permission vocabulary.
**Working 4b against an unsettled domain model means doing it twice**, and 4b — every write command and
every query across ten aggregates — is the largest phase in the plan.

**The rule most likely to be lost in 4b's volume:** a scope is checked at the edge and never replaces the
resource predicate checked at the aggregate. **A row with a scope and no predicate on an owner-scoped
resource is wrong.** `.All` widens a scope's range; it does not remove the predicate.

## The hard gate

**`status: done` requires phase 10 closed. There is no version of "documentation complete" that closes this
plan.**

Phases 0–9 can all finish while `Magiq.AspNetCore.Idempotency` still does replay rejection. At that point
the plan is *substantially* complete and **not** complete — SB-20, SB-72, SB-73, SB-74 and SB-76 will read
as closed in the spec while being open in fact.

- **Do not set `status: done`** while any phase 10 box is open, however finished the rest looks. The card's
  status is projected from front-matter and nothing else, so that is the only mechanism there is.
- **When phases 0–9 finish**, comment the card saying documentation is complete and the plan is held on
  phase 10, naming `AP-001`. Leave the status `active`.
- **If the SDK work is abandoned rather than shipped**, that is a decision: phase 5's text reverts to the
  mechanism the platform provides, or the plan closes `superseded` with the reason recorded. Ticking
  phase 10 to tidy the list is the one outcome not available.

## Every session

- **Tick boxes in the file as work lands** — a later session resumes from the file, not from chat history.
- **Write `status:` in the same edit that changes what is true.** There is no board update, only this file.
- **Append each branch to `branches`** as it is cut.
- **Close with a card comment**: what moved, what did not, and the next concrete action. Front-matter
  carries one word; the card carries the narrative, and a workstream picked up three weeks later needs
  both.
