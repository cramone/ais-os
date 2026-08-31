---
id: MM-033
type: review
project: magiq-media
workstream: spec-structure
raised-by: []
status: done
outcome: folded-into:MM-024
todo-id: a1652504-6d8f-5bf7-b8a5-4638cc3bf3c4
created: 2026-08-25
---

> **Backfilled into the review cycle 2026-08-31 as MM-033.** No plan of its own — most of it lands in MM-024's Phases 2/4a/5; four items are new.

# Spec structure — what the 16 dimensions need, and what this repo already has

_Written 2026-08-25 for Chase Ramone. Scope: `D:\source\github\magiq-media\docs\` as it stands today —
72 spec files, 7 contexts, 12 aggregates, 5 architecture files, 6 shared files, 21 ADRs._

> **This is not a proposal to restructure the spec.** The per-aggregate structure this repo already uses
> is better than most production specs and should be left alone. The recommendation is narrower and
> duller: **give every dimension exactly one owning file, and add the four file types that do not exist.**

---

## 0. Verdict

**Twelve of the sixteen dimensions are already covered, and covered well. The four that are not have one
thing in common: they span aggregates.**

That is the whole finding. This repo's spec is organised per aggregate — `write-model` / `read-model` /
`api` / `scenarios`, four files each, twelve times. Any dimension that fits inside one aggregate is in
good shape: commands, events, invariants, state transitions, entities and value objects, API, edge cases.
Any dimension that spans aggregates has no natural file to live in, so it has either been **duplicated
into every overview that felt like mentioning it** (ubiquitous language: 8 copies; bounded contexts: 3;
aggregate inventory: 3, disagreeing 9 / 10 / 12) or it has **fallen through entirely** (sagas,
eventual-consistency policy, cascade rules, the contradiction register).

The DDD coverage review reached the same place from the other side — *"coverage is not the problem,
authority is"*. Structure is what fixes authority. A dimension with no file of its own gets copied into
three; a dimension with one file gets edited in one place.

---

## 1. Dimension ownership — current vs recommended

Legend: ✅ well owned · ⚠️ owned but duplicated or misplaced · ❌ no owner.

| # | Dimension | Today | Recommended single owner |
|---|---|---|---|
| 1 | **Ubiquitous language** | ❌ **8 competing tables** — `domain-model.md`, `system-spec.md § Ubiquitous Language (Cross-Context)`, and a `## Ubiquitous Language` section in 6 of 7 context overviews. `system-spec.md`'s is corrupted mid-table at ~line 1103 | **`spec/glossary.md`** — one table, term / definition / owning context / first introduced. Context overviews link to it; none defines terms |
| 2 | **Bounded contexts** | ⚠️ **3 answers** — `architecture/bounded-context.md` (2026-03-11, stale), `architecture/service-boundaries.md` (2026-08-24, authoritative, explicitly repudiates the first), `context-overview.md § Service Boundaries` × 7 | **`architecture/bounded-contexts.md`** — merge the two architecture files. Context relationship type (ACL / conformist / partnership / published language) for **all 12 relationships**, not just the 5 external ones |
| 3 | **Aggregates** | ⚠️ Per-aggregate specs ✅; **inventory duplicated 3×** and inconsistent (9 / 10 / 12) | Aggregate *specs* stay where they are. The **inventory** lives once, in `architecture/domain-model.md`. Delete the other two |
| 4 | **Entities & value objects** | ⚠️ `<agg>.write-model.md § Value Objects` — present on most, **absent on Folder**. The entity-vs-VO rule is never stated, and `Reviewer`, `ReviewComment`, `RegistrationItem`, `RegistrationAmendment`, `Signer` all have identity and mutable state but are catalogued as VOs | Keep in `write-model.md`, but **state the rule once** in `architecture/domain-model.md` and make the section mandatory (see §4) |
| 5 | **Commands** | ✅ `write-model.md § Methods (Commands)`, `§ Commands`, `§ Handler-side Pre-conditions` — this is the strongest part of the spec | Unchanged |
| 6 | **Domain events** | ✅ `write-model.md § Domain Events`, payload-level | Unchanged |
| 7 | **Invariants** | ⚠️ Per-aggregate ✅ in `write-model.md § Invariants`. **Cross-aggregate invariants live in `adrs/catalog-domain-invariants.md` — outside the spec tree**, in a folder for decisions, not rules | Per-aggregate stays. **`shared/cross-aggregate-invariants.md`** — new; absorb the ADR's rules, leave the ADR as the decision record it is |
| 8 | **Business rules** | ⚠️ Real, but homeless — split across `§ Handler-side Pre-conditions`, `§ Invariants` and prose in scenarios. No stated distinction between an invariant and a rule | Fold into `write-model.md` deliberately: **invariants = always true of the aggregate; pre-conditions = must hold to accept a command.** Name the distinction in the file-type contract rather than adding a file |
| 9 | **State transitions** | ⚠️ `write-model.md § Status transitions` ✅ per machine. **MediaItem has three interacting machines** (status × edit-session/checkout × folder assignment) each specified alone, interaction nowhere | Keep. Add a **required interaction matrix** to `write-model.md` for any aggregate with more than one state machine |
| 10 | **Relationships** | ⚠️ Cross-*context* in 3 places (`service-boundaries`, `system-spec § Cross-Context Relationships`, `bounded-context`). Cross-*aggregate* nowhere. Reference-by-id is implied everywhere, stated nowhere | Cross-context → `architecture/bounded-contexts.md`. Cross-aggregate → `architecture/domain-model.md`, including the reference-by-id and one-aggregate-per-transaction rules |
| 11 | **Workflows** | ✅ `contexts/<Ctx>/business-scenarios.md` + `<agg>.scenarios.md` | Unchanged |
| 12 | **Sagas / process managers** | ❌ **No owning file exists.** `AssetIngestionSaga` is in production with 5 handlers under `src/hosts/SagaOrchestrator/AssetIngestion/` and no spec file. `CollectionArchiveFanOutWorker` and `IFolderArchiveFanOutWorker` are process managers nobody calls process managers | **`contexts/<Ctx>/sagas/<saganame>.md`** — new file type, one per saga *and per fan-out worker*. Owning context = the one that owns the outcome |
| 13 | **Eventual consistency** | ❌ Projection mechanics ✅ in `read-model.md`. **Policy absent** — no read-your-own-writes rule, no projection-lag bound, no rebuild procedure. `api-conventions.md` alludes to "a client that reads a lagging projection" and gives no figure | **`shared/consistency-model.md`** — new. Lag SLO, RYOW rule, rebuild procedure, and the reference indexes `service-boundaries.md:133` says replay cannot rebuild |
| 14 | **Edge cases & contradictions** | ⚠️ Edge cases ✅ in `scenarios.md`. **Contradictions have no in-repo home** — they live in review documents on `Z:\`, which per the repo's own `CLAUDE.md` is Chase's machine only. **Estelle and Akshay cannot see them** | **`spec/open-questions.md`** — new, in-repo. Every known contradiction with its status. See §5 |
| 15 | **API documentation** | ✅ `<agg>.api.md` × 12 + `shared/api-conventions.md` (768 lines) + `error-catalog.md`. Genuinely strong | Unchanged — except the traceability tables, see §6 |
| 16 | **Business scenarios** | ⚠️ `business-scenarios.md` × 7 ✅. But **`scenarios.md` exists for 9 of 12 aggregates** — Folder, BulkFolderImportJob and BulkMediaImportJob have none, and Folder's two highest-risk behaviours (archive cascade, cross-collection subtree move) have no worked example anywhere | Make `scenarios.md` **mandatory per aggregate** |

**Score: 5 ✅ · 7 ⚠️ · 4 ❌.** Every ❌ and most ⚠️ are cross-aggregate.

---

## 2. Target structure

Additions marked **NEW**; everything unmarked stays exactly where it is.

```
docs/spec/
  README.md                            NEW  the map — which file answers which question (§3)
  glossary.md                          NEW  the ubiquitous language, once
  open-questions.md                    NEW  contradiction register, in-repo (§5)

  architecture/
    bounded-contexts.md                     merged bounded-context.md + service-boundaries.md
    domain-model.md                          aggregate inventory · cross-aggregate relationships ·
                                             entity-vs-VO rule · reference-by-id · 1-aggregate-per-txn
    system-architecture.md
    branching-and-deployment.md

  shared/
    api-conventions.md                       ✓ strong, leave alone
    error-catalog.md                         ✓
    bulk-operations.md                       ✓
    media-types.md                           ✓
    security-scenarios.md                    ✓
    consistency-model.md               NEW  eventual-consistency policy
    cross-aggregate-invariants.md      NEW  absorbed from adrs/catalog-domain-invariants.md
    cascade-rules.md                   NEW  what archiving/deprecating one thing does to another
    system-spec.md                     SPLIT 1,213 lines, 19 top-level sections — see §7

  contexts/<Context>/
    context-overview.md                      ✓ but strip the glossary and the duplicated inventories
    business-scenarios.md                    ✓
    sagas/<saganame>.md                NEW  one per saga and per fan-out process manager
    aggregates/<Aggregate>/
      <agg>.write-model.md                   ✓
      <agg>.read-model.md                    ✓
      <agg>.api.md                           ✓
      <agg>.scenarios.md                     ✓ now mandatory (3 missing)
```

Net: **+7 files, +1 folder type, −2 by merge, 1 split.** Nothing moves that does not have to.

---

## 3. `spec/README.md` — the piece that makes the rest hold

The single highest-value new file, and the cheapest. One table: **question → the one file that answers
it.** Not an index of files; an index of *questions*.

```markdown
| If you need to know… | Read | Not |
|---|---|---|
| what a term means | `glossary.md` | any context overview |
| which context owns X | `architecture/bounded-contexts.md` | `system-spec.md` |
| what commands an aggregate accepts | `<agg>.write-model.md` | `<agg>.api.md` |
| what a route does | `<agg>.api.md` | `<agg>.write-model.md` |
| how a long-running process ends | `contexts/<Ctx>/sagas/<saga>.md` | the scenarios files |
| how stale a read can be | `shared/consistency-model.md` | — |
| what is still contested | `open-questions.md` | the Z:\ docs project |
```

The "Not" column is doing the real work. Every duplicated section in this spec exists because somebody
needed an answer, could not tell which file owned it, and wrote it where they were.

---

## 4. File-type contracts — required sections

The structure only stays true if coverage is checkable. Phase 0 of the DDD plan already calls for a CI
docs guard against truncation; **extend that same workflow to assert required headings per file type**.
It is a heading-presence check — cheap, and it makes "the 16 dimensions are covered" a build result
rather than an opinion.

| File type | Required sections |
|---|---|
| `<agg>.write-model.md` | `Purpose` · `Invariants` · `Properties` · `Value Objects` · `Status transitions` · `Methods (Commands)` · `Domain Events` · `Handler-side Pre-conditions` · `Published Integration Events` · `Consumed Integration Events` · **`State Machine Interaction`** *(only when the aggregate has >1 machine)* |
| `<agg>.read-model.md` | `Read Models` · `Projection Handlers` · `Queries` · `Read Model Types` · **`Consistency`** *(lag class + RYOW behaviour, linking `consistency-model.md`)* |
| `<agg>.api.md` | `API Conventions` · `Authorization` · `Write Endpoints` · `Read Endpoints` · `Command → Event → Projection Traceability` · `Related` |
| `<agg>.scenarios.md` | `Index` · `Diagram Key` · ≥1 scenario · `Related` |
| `context-overview.md` | `Purpose` · `Responsibilities` · `Aggregate List` *(links only — no inline table)* · `Service Boundaries` · `High-Level Event Flows` · `Integration Event Contracts` · `Related Specifications` — **no `Ubiquitous Language` section** |
| `sagas/<saga>.md` | `Purpose` · `Correlation Key` · `State Table` · `Transition Table` · `Timeouts` *(values **with their config keys**)* · `Compensation` · `Idempotency` · `DLQ & Poison Policy` · `Manual Intervention Runbook` |
| every file | `_Last reviewed: YYYY-MM-DD_` |

The saga contract is the one to get right first. `AssetIngestionSaga` today has a **live behavioural
hole** that only this contract would have caught: a bypassed asset emits neither `ProcessingJobSucceeded`
nor `ProcessingJobFailed` — the only two closure triggers — so the fast-exit branch has no stated way to
end. That is not a documentation gap found by reading documentation; it is one found by being forced to
fill in a *Transition Table* row.

---

## 5. `open-questions.md` — the dimension nobody plans for

"Edge cases and contradictions" is two dimensions wearing one name. Edge cases are covered — the
`scenarios.md` files are good at them. **Contradictions are not, and the reason is structural rather than
editorial: this repo has nowhere to put a known-unresolved disagreement**, so they accumulate in review
documents on `Z:\`, which the repo's own `CLAUDE.md` states is Chase's machine only.

Two of three engineers on this project cannot read the list of things the spec is wrong about.

A contradiction register in-repo costs one file and changes who can act:

```markdown
| # | Question | Sides | Status | Owner | Opened |
|---|---|---|---|---|---|
| Q-1 | Integration event naming: `media.mediaitem.*` (16 uses) or `media.item.*` (12)? | … | **Open** — blocks external SNS filter policies | Chase | 2026-08-24 |
| Q-2 | `Capability` enum: API allows 4, write model defines 9, defaults seed 2 the API rejects | … | Open | Chase | 2026-08-24 |
| Q-3 | Approve authorization specified 3 ways across `system-spec:147`, `security-scenarios:123`, `error-catalog:297` | … | Open — security-relevant | Chase | 2026-08-24 |
```

Entries close by being deleted, with the winning rule written into the owning file. The register should
never grow a "resolved" section — that is how it becomes a second spec.

---

## 6. One thing the structure cannot fix

`<agg>.api.md § Command → Event → Projection Traceability` is the correct home for that dimension and the
table is in the right file. It is also **wrong in every file**: the projector classes it names —
`MediaItemProjector`, `CollectionProjector`, `SigningSessionProjector`, `AssetProjector` — do not exist.
The real projectors are split detail/summary/index; there are 50 of them. The singular names appear **69
times across `docs/spec/`**. Filed as drift-review **X-11.1**.

Worth stating plainly because it bounds what this document can promise: **a structure guarantees that a
question has one answer, not that the answer is right.** The two failure modes are independent, and this
repo currently has both. Structure fixes the first. Only reading code fixes the second — which is the
argument for the file-type contracts in §4 being *heading* checks, and for X-11.1's sweep being a
separate, larger piece of work owned by the drift review.

---

## 7. Deletions and the `system-spec.md` split

Nothing above works while the duplicates survive. Structure is subtractive here.

| Delete | Why |
|---|---|
| `## Ubiquitous Language` from 6 context overviews + `domain-model.md` + `system-spec.md` | Replaced by `glossary.md`. Repair `system-spec.md`'s corrupted table before extracting it |
| `bounded-context.md`'s aggregate inventory, event catalogue, queue table, host list | Three inventories is two too many; `service-boundaries.md` already repudiates these |
| `bounded-context.md` itself, after the merge | Dated 2026-03-11 and contradicted by a file five months newer |
| `contexts/Catalog/aggregates/BULK-IMPORT-SPEC-UPDATES.md` | An unmerged changelog in imperative future tense sitting in `aggregates/`, prescribing `/v1/catalog/...` routes that **do not exist in the codebase**. Merge `BulkCreateMediaItemsCommand` and the SQS/DLQ config out of it first — they exist nowhere else |
| `docs/implementation-plans/` | Retired 2026-07-08; stale redirect stubs |
| `docs/spec/_recovered/` | On Phase 3 close, per its own README |

**`system-spec.md` — 1,213 lines, 19 top-level sections, and the file the cutter has truncated twice.**
It is the spec's junk drawer: multi-tenancy, auth, concurrency, idempotency, cross-aggregate constraints,
event sourcing, messaging, storage, S3, sagas, relationships, infrastructure, observability, naming,
glossary, CORS, rate limiting, DR. Its size is why it keeps getting cut — a wholesale rewrite runs out of
output budget in the same neighbourhood every time.

Split along the seams it already has:

| Section(s) | Goes to |
|---|---|
| Multi-Tenancy · Authentication & Authorization | `shared/multi-tenancy-and-auth.md` |
| Concurrency · Idempotency · Cross-Aggregate Constraint Enforcement | `shared/concurrency-and-consistency.md` |
| Event Sourcing Mechanics · Messaging Patterns · Storage Boundaries · S3 Upload Patterns | `shared/persistence-and-eventing.md` |
| Saga Coordination Patterns | `shared/saga-patterns.md` — the cross-cutting rules; individual sagas get their own files |
| Cross-Context Relationships | `architecture/bounded-contexts.md` |
| Ubiquitous Language | `glossary.md` |
| Infrastructure · Observability · DR · CORS · Rate Limiting | `shared/operations.md` |
| Naming Conventions | `architecture/domain-model.md` |

After the split, `system-spec.md` should not exist. A file that survives as a stub is a file somebody
will write into again.

---

## 8. What not to do

- **Do not add a file per dimension.** Commands, events and invariants are correctly owned by
  `write-model.md`. Pulling them into `commands.md` / `events.md` / `invariants.md` would trade the
  current authority problem for a worse one — three files to open before you know what an aggregate does,
  and three places for them to drift apart.
- **Do not make `context-overview.md` the answer to everything.** It became the duplication site precisely
  because it is the file people open first. Its job is orientation and links, not definitions.
- **Do not restructure before Phase 2 of the DDD plan.** Moving text between files while three documents
  still disagree about what is true just relocates the disagreement. Establish which document wins, then
  move.
- **Do not put the glossary in the wiki.** It is generated from `docs/`, lags it, and per `CLAUDE.md`
  should not be hand-edited — a glossary that lives downstream of the spec cannot be the spec's authority.

---

## 9. Sequencing

This slots into existing plans rather than competing with them.

| Work | Where it belongs |
|---|---|
| Deletions, the merge, `_Last reviewed:` | **DDD plan Phase 2** — already scoped there |
| `sagas/` file type + `AssetIngestionSaga`, `DocumentSigningSaga`, both fan-out workers | **DDD plan Phase 4a** — already scoped |
| `glossary.md`, `cross-aggregate-invariants.md`, `cascade-rules.md`, missing `scenarios.md` | **DDD plan Phase 5** — already scoped |
| `spec/README.md`, `open-questions.md`, `consistency-model.md`, file-type contracts in CI, `system-spec.md` split | **New** — not in any plan today |

The four new items are roughly 2–3 days together, and `spec/README.md` plus `open-questions.md` are half a
day of it. Both are worth doing **before** Phase 2 rather than after: the deletions in Phase 2 are much
easier to argue when there is a file that says where the surviving copy lives, and a register to record
the ones nobody can decide yet.
