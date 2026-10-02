# Decisions — magiq-media

**The project's decision log.** A decision that settles a question and governs future work is recorded here
so the answer survives the session that produced it. Karen Barton's retention ruling of 2026-09-14 (DEC-1)
was once lost for want of this folder — that is the failure it exists to prevent.

---

## What belongs here

A decision that **settles a question and governs future work**. Specifically:

- A ruling on an open design question, whoever made it.
- A correction where the tree contradicted itself and one side was chosen.
- A standing rule that governs how later questions are answered.

## What belongs elsewhere

| Content | Home |
|---|---|
| **Why** a decision was made — rationale, rejected options | `D:\...\mgq-magiq-media\docs\adrs\` |
| The **specified system** itself | `D:\...\mgq-magiq-media\docs\spec\` |
| Findings and evidence | `reviews/<workstream>/` |
| Open questions, sequencing, tracking | `plans/<workstream>/` |
| Build status, "do not rebuild this", open domain questions | the repo's `CLAUDE.md` · the `Media` ADO board |
| Durable session facts | `MEMORY.md` |

**A decision record is not an ADR.** The ADR carries the argument; this carries the answer and what it
closes. Where a decision earns an ADR, the record says so.

---

## The log

| Record | Decisions | Subject | Date |
|---|---|---|---|
| — | — | — | — |

**The next decision id is D93.** D1–D92 and the standing rule P1 were issued by the write-model validation
record (2026-09-19 → 2026-09-26), since removed; its outcomes are in `docs/spec/` and `docs/adrs/`, and P1 is
the repo `CLAUDE.md` § When the spec and the code disagree, the spec wins.

---

## Karen's rulings

Recorded because they were lost once. All four are carried in `docs/adrs/retention-and-disposal.md`.

| # | Ruling | By |
|---|---|---|
| **DEC-1** | Retention applies at the **item** level, not on `MediaProfile`, `RecordType` or `Folder`; an item tracks its filing folder so folder closure drives its retention events | Karen Barton, 2026-09-14 |
| **D57** | A legal hold **always wins** over a matured class schedule, and is recorded on the record with who applied it, when and under what authority | Chase, 2026-09-20 |
| **D58** | `DisposalAction` = `Destroy \| RetainPermanently \| Transfer \| Review` — the MoReq2010 set | Chase, 2026-09-20; confirmed against UK/US/NZ/AU practice 2026-09-28 |
| **D59** | A per-schedule `PeriodBasis` — `TriggerDate \| EndOfYear`, default `EndOfYear` — with a per-schedule `YearEnd`, default 31 December. Calendar vs financial year is data, not design | Chase, 2026-09-20 |

---

## Conventions

- **Ids are `D<n>`, monotonic, never reused.** They are not in the `MM-` space, which covers reviews, plans
  and gates — a decision is not a workstream.
- **One record per batch of work**, dated, named for its subject. Not one file per decision.
- **A decision states what it closes.** Every entry names the findings it resolves, reshapes or withdraws,
  so a later reader can tell whether something is still open.
- **Corrections are folded in, not layered.** Where a decision was later found wrong, the record says so in
  one place rather than leaving the reader to reconcile two entries.
