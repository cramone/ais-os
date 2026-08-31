---
name: review-cycle
description: Use to run the review → plan work cycle inside a project's reviews/ and plans/ folders — create a review with its paste-ready prompt, write the plan once findings are agreed, gate a plan on its dependencies, close out and archive a finished workstream. Triggers on "create a review for [project]", "write a review of [topic]", "write the plan for [workstream]", "close out [workstream]", "archive [workstream]", "/review-cycle". This is NOT a code-diff or PR review — for those use /code-review or /security-review. Writes to projects/{slug}/reviews/, projects/{slug}/plans/, and the tower/data/todos/{slug}.json todo store.
---

## What this skill does

Runs the write side of the review → plan cycle. A review argues findings; a plan sequences them and tracks execution. This skill creates both, keeps the Control Tower todos in step, and enforces the gates between them.

Read side — "what's unblocked", "what's blocked and why", dependency graphs — lives in [[workstream-query]]. Do not duplicate it here.

This extends the convention in `projects/magiq-media/CLAUDE.md` § "Review → Plan". Its three rules stand unchanged: the folder name is the link, the plan is named after the review, and both sides archive together.

## Adoption

The skill operates only on projects whose `CLAUDE.md` carries a `## Review → Plan cycle` section:

```markdown
## Review → Plan cycle
prefix: MM
we-operate: true
```

- `prefix` seeds document ids.
- `we-operate: true` means we own this project's code and may raise reviews in it.

No section, or `we-operate: false` → the project is out of scope. Say so and propose an external hand-off instead (§ Cross-project work).

## Document ids

Every review, plan and gate carries a stable id. **All cross-references use ids, never paths or folder names.**

```yaml
id: MM-014
```

- `<PREFIX>-<nnn>`, zero-padded to three, monotonic per project.
- Mint by grep: highest existing `id:` under that project's `reviews/` and `plans/`, **including every `Archive/`**, plus one.

  ```bash
  grep -rhoE '^id: [A-Z]+-[0-9]{3}' projects/<slug>/reviews projects/<slug>/plans | sort | tail -1
  ```

- No counter file, no registry. A duplicate id is a data error — stop and report it.
- Never reused, never renumbered. Survives rename, move and archive.

Ids exist rather than paths because locations change: `plans/` was reorganised on 2026-08-24 and `reviews/README.md` still carries a "References repaired in the move" section listing ten repointed links plus two that had been broken for months. Resolution is derived — grep `id: MM-014` to find the file wherever it now lives.

**Four id spaces, four jobs. Never conflate them.**

| Id | Scope | Set by |
|---|---|---|
| `id: MM-014` | one review / plan / gate document | this skill |
| `todo-id: <uuid>` | one Control Tower todo | **derived** — `uuid5` of `<slug>:<doc-id>` |
| `AC-1`, `X-11.30` | one finding inside a review | the review author |
| `adoItemId: 34275` | one ADO work item | `ado-create-from-plan` |

## Three document types

| type | Lives in | Consumes | Produced by |
|---|---|---|---|
| `review` | `reviews/<ws>/` | code / spec | Workflow 1 |
| `plan` | `plans/<ws>/` | one or more reviews | Workflow 2a |
| `gate` | `plans/<ws>/` | one or more **plans** | by hand, rarely |

A gate triages across workstreams and answers "which of these block a release". `plans/prod-readiness/prod-readiness-gate.md` is the existing one. **A gate has no review and does not need one** — the "no plan without a review" invariant does not apply to it.

## Naming

- workstream slug — kebab-case from the review topic, e.g. `archive-cascade`
- review — `projects/<project>/reviews/<workstream>/<workstream>-review-<YYYY-MM-DD>.md`
- prompt — `projects/<project>/reviews/<workstream>/<review-filename>-prompt.md`
- plan — `projects/<project>/plans/<workstream>/<primary-review-filename>.md`
- archives — `reviews/<ws>/Archive/` and `plans/<ws>/Archive/`, capital A

**Never write a bare `prompt.md`.** A workstream folder can hold several reviews — `archive-cascade/` and `event-reliability/` each hold two today — and a fixed filename overwrites.

**Multi-review tiebreak:** where several reviews feed one plan, the plan is named after the **primary** review (the one whose findings dominate) and `consumes:` lists every one of them by id.

Filenames stay human-readable. Ids are for machines and cross-references; names are for people. README tables carry both.

**Dates come from the session environment, never from memory or inference.**

## Status vocabularies

Reviews, plans and gates have different lifecycles. Do not share one enum.

- **Review:** `draft` → `findings-agreed` → `done` | `parked` | `superseded`
- **Plan:** `active` | `blocked` | `parked` | `superseded` | `done`
- **Gate:** `active` | `superseded` | `done`

Front-matter is authoritative. It maps to the todo store and the README words:

| Front-matter | Todo status | Todo tag | README word |
|---|---|---|---|
| review `draft` | `new` | — | Draft |
| review `findings-agreed` | `in-progress` | — | Active |
| plan `active` | `in-progress` | — | Active |
| plan `blocked` | `deferred` | `blocked` | Active (blocked) |
| `parked` | `deferred` | `parked` | Parked |
| `superseded` | `done` | `superseded` | Superseded |
| `done` | `done` | — | Done |

- **Index everything from creation, including `draft`.** A review that exists but is not in `reviews/README.md` is invisible to the next session — the exact failure this convention prevents.
- `blocked` is **derived** from unmet dependencies, never set by hand.
- `parked` is a deliberate human call and must carry a reason.
- **`findings-agreed` is a transition Chase makes, not one you infer.** Chase says the findings are agreed; you set the front-matter and comment the card with what settled it. Until then the plan gate stays shut, however few open questions remain.

## Front-matter

Every field mandatory; use `-` or `[]` for empty.

Review:

```yaml
---
id: <PREFIX>-<nnn>
type: review
project: <slug>                  # project that OWNS the code/spec reviewed
workstream: <slug>
raised-by: [<id>, ...]           # origin documents; [] if raised directly
status: draft | findings-agreed | done | parked | superseded
outcome: pending | plan | parked | decision-only | folded-into:<id> | withdrawn
todo-id: <uuid>
created: YYYY-MM-DD
---
```

Plan:

```yaml
---
id: <PREFIX>-<nnn>
type: plan
project: <slug>
workstream: <slug>
consumes: [<review-id>, ...]
depends-on: [<plan-id>, ...]     # ids, any project; [] if none
blocked-by-external: []
status: active | blocked | parked | superseded | done
todo-id: <uuid>
branches: []                     # append each branch as it is cut
ado: -                           # or {project: <board>, epicId: <id>}
created: YYYY-MM-DD
---
```

Gate:

```yaml
---
id: <PREFIX>-<nnn>
type: gate
project: <slug>
workstream: <slug>
consumes: [<plan-id>, ...]
supersedes: <gate-id> | -
status: active | superseded | done
todo-id: <uuid> | -
created: YYYY-MM-DD
---
```

Optional on any of them, when a file deliberately breaks the convention:

```yaml
exception: <one-line reason>
```

Notes:

- **No `open-questions` count field.** Count `**Open**` markers in the review's `## Open Questions` section — a stored count is a second source of truth and will drift.
- **`branches` is a list.** `architecture-review-remediation` spans ~57 branches across 3 repos.
- **A gate has no `depends-on`.** It is the consumer, never the dependent. Nothing blocks a gate; the gate reports what is blocked.

## Todo store

`tower/data/todos/{project-slug}.json`, slug == the folder name under `projects/`. Never hand-edit — always go through `tower.interrupts.store`, run from repo root. Full API in [[project-todos]].

- status: `new` | `in-progress` | `deferred` | `done` — these four exist, no others
- priority: `urgent` | `normal` | `low`
- `source` — repo-relative path of the review or plan file
- tags — the document id, plus `review` / `plan` / `gate`, plus the workstream slug, plus a state tag where the mapping calls for one
- every status change gets a card comment saying why — `cycle.comment(slug, doc_id, text)`, see § The card is the session log

Create with id, source and tags in one call — `create_item` takes them, despite the `project-todos` doc showing only `title`/`priority`/`due_date`:

```bash
python -c "from tower.interrupts.store import create_item; from tower import config; import json; print(json.dumps(create_item(config.todos_file('SLUG'), title='TITLE', source='PATH', tags=['MM-014','review','WORKSTREAM'], priority='normal')))"
```

**Last write wins.** `save_interrupts` rewrites the whole file and the Control Tower UI writes the same store. Re-read immediately before every mutation; never cache item state across a long session.

**The store is disposable; the documents are not.** `tower/data/` is gitignored, so todo state is local-only — not versioned, not backed up, not visible to another clone. Front-matter is the durable record. If the store is lost or diverges, rebuild it from front-matter using the status mapping table above; never the other way round.

**The board is a projection of the documents. It holds no cycle state of its own.** `tower/cycle.py` renders every review, plan and gate as a card on each board read — full docs in `docs/review-cycle-todo-coupling.md`. Cycle cards **do not drag**, have no Done or delete button, and carry a badge showing their document id. `PATCH`ing their status returns **409**.

That is why there is no sync to keep honest: there is one writer, and it is the file.

**So the only way a cycle status changes is you writing it into front-matter.** That makes the rule below non-negotiable, because nothing else can correct a lapse:

> **Whenever you change what is true about a review or plan, write `status:` in the same edit.** Findings agreed → `findings-agreed`. Plan authored → `active`. Dependency unmet → `blocked`. Work finished and Chase agrees → `done`. Never "I'll update the board after" — there is no board update, only this one.

The rest follows automatically and must not be done by hand:

- **Never create a todo for a review or plan.** `reconcile()` creates it on the next board read, with a deterministic id derived from `<slug>:<doc-id>`. This retires the old chicken-and-egg step where a todo had to exist before the file could carry a real `todo-id`.
- **`todo-id` is derivable, not allocated.** If you need it, `cycle.todo_id_for(slug, doc_id)`. Delete `tower/data/` entirely and every card returns with the same id and status.
- **Never repair a `source` path.** Resolution is by id, so archiving and renaming self-heal.
- **Never hand-edit a cycle todo's status or state tags in the store.** They are overwritten on the next read from the document.

Still yours to set on the board, because they are not in front-matter: **priority, due date, and comments.**

## The card is the session log

**Status says where a document is. The card's comments say how it got there and where to pick it up.** Front-matter carries one word; a workstream picked up three weeks later needs the narrative beside it. Write that as you go — not reconstructed at the end, when the detail that mattered is gone.

One call, which resolves by document id and creates the card if the projection has not rendered it yet:

```bash
python -c "from tower import cycle; cycle.comment('magiq-media', 'MM-026', 'X-11.41 closed. Items moved out of a folder now produce real refusals rather than silent ones. X-11.17 next; it needs gate decision 5 first.')"
```

**Comment on these, every time:**

- **Picking a document up** — what you are starting, and the state you found it in. This is the entry that tells the next session the difference between "not started" and "started and abandoned".
- **A finding closed** — its id, what actually changed, and anything the finding's own text got wrong.
- **A decision taken** — what was decided and what it rules out. Log it via [[decision]] as well when it is architectural; the card entry is the pointer.
- **A blocker found** — what blocks, whose it is, and whether the ask is written and sent.
- **A branch cut** — the name. It goes in `branches:` too, but the card is where you see *when*.
- **Putting it down** — what moved, what did not, and **the next concrete action**. This is the one that answers "where am I up to", so never skip it, including when a session ends having achieved nothing.

**Do not comment on:** individual file edits, commands run, or anything already written in the document body. A card is a log of decisions and outcomes, not a transcript. If a comment could be replaced by reading one paragraph of the plan, it is noise.

**Shape.** Lead with the outcome, not the activity — *"X-11.16 closed"*, not *"worked on the archive cascade"*. Name finding and document ids so entries are greppable. Two or three sentences. The timestamp and author are recorded for you, so do not write the date.

**Never record status in a comment as the record.** Front-matter is the record and the board projects it; a comment saying "moved to blocked" is fine as narrative but it is not what makes it blocked.

Documents with no front-matter are invisible to the projection. Legacy files get no card and keep whatever board state they already had, which is correct: their status is UNKNOWN and must not be inferred.

**`cycle.check(slug)`** reports what the projection stays deliberately quiet about: duplicate ids, front-matter with a malformed or missing `id:`, statuses outside the vocabulary, a `todo-id` that is not the derived one, `consumes` / `depends-on` entries naming a document that does not exist, and — the one no render can see — **a plan with no review**.

A plan proves it has a review one of two ways: front-matter `consumes:` naming at least one review id, or the legacy folder pairing `plans/<ws>/` ↔ `reviews/<ws>/` (with `plans/Archive/` pairing to `reviews/Archive/`). Anything else is flagged, including a plan sitting loose at the `plans/` root. **The bias is deliberate** — a new unpaired plan should trip this.

**`exception:` silences every check on a file, and `cycle.known_exceptions(slug)` lists them.** That is the § Known exceptions rule made real: skip, and report, never "fix". It also means the silence is never free — someone has to write a sentence and stand behind it.

Run both after any backfill. Duplicate ids and hand-allocated `todo-id`s are the live risks while ids are still being minted into legacy files.

## Workflow 1 — create a review

Trigger: Chase is discussing a project's repo code or spec docs and asks for a review.

1. **Resolve target.** Project slug and workstream slug. Ambiguous project → ask, do not guess. Read the target's adoption marker. **No marker, or `we-operate: false` → stop** and propose an external hand-off (§ Cross-project work).
2. **Mint the id** from the target project's prefix.
3. **Create folders.** `reviews/<workstream>/`, plus the `reviews/` tree and `README.md` if the project has none.
4. **Do not create the todo.** The board projects it from the file on the next read, with the id `cycle.todo_id_for(<slug>, <doc-id>)` — put that value in `todo-id` and it will match. Cross-project → set the origin's id as a tag and inherit its priority once the card exists; those are board fields the projection leaves alone.
5. **Write the review** with front-matter (`status: draft`, `outcome: pending`, the id from step 2, the uuid from step 4). Required sections, in order:
   - `## Scope` — what was read, what was not
   - `## Findings` — finding id, severity (High/Medium/Low), evidence as `file:line`, impact
   - `## Open Questions` — numbered, each `**Open**` or `**Answered:** <answer>`
   - `## Dependencies` — other documents needed, by id, plus any external blocker; `none` if none
   - `## Recommended sequencing` — rough; the plan refines it
6. **Write the prompt file** — `<review-filename>-prompt.md` beside it (§ The prompt file).
7. **Index it.** A row in `reviews/README.md` carrying id and name, status `Draft`.
8. **Cross-project only:** add this review's id to the origin document's `depends-on` (or its `## Dependencies` if the origin has no plan yet, promoted when it does), and comment on the origin's todo naming the new id.
9. **Report** id, paths written, todo id, and the one-line summary used.

## The prompt file

Pasted into a fresh Claude session with zero context from this one. It must stand alone — no "as we discussed", no unresolved pronouns.

Contents:

- Project slug and the absolute path to the project folder
- The review's document id, its absolute path, and the todo id
- Instruction that the **first** action is a card comment recording what is being picked up and the state it was found in — `cycle.comment('<slug>', '<id>', '…')`. The card's status is projected from front-matter and is not settable from the board, so do not try
- What to read first, and what is out of scope
- The finding-id prefix to use, and that severity is High/Medium/Low — never 🔴/🟠, which belong to the gate
- How to work findings: evidence before conclusion, cite `file:line`, **do not fix code during a review**
- What to do with anything found outside scope: it does not go in this review's findings — surface it and ask where it belongs
- The gate, plainly: **do not write the plan until every open question is answered AND Chase has moved the review to `findings-agreed`**
- A `## Writing the plan` section giving the plan format: front-matter as above with a freshly minted id, then phases. **A phase is a `## Phase <N> — <name>` heading**, an intro line, then a checklist of `- [ ]` items small enough to finish in one session; each item naming the finding id it closes and its acceptance check; phases blocked by a dependency marked as such. The heading shape is not cosmetic — [[ado-create-from-plan]] reads `## Phase <N> — <name>` to find Features, and `## ADO mapping` keys its branch table on the same `<N> — <name>`
- That `ado:` in the plan front-matter is left as `-`. Pushing a plan to the board is a separate, explicit step run through [[ado-create-from-plan]] once the plan is `active` — never during the review, and most plans never go to the board at all. The field is a slot for that step to fill, not something to populate by hand
- Whether this workstream is board-tracked. If it is, the plan ends with an `## ADO mapping` block giving a branch per phase and a type per item (`bugfix` · `feat` · `refactor` · `infra` · `chore`); if it is not, the block is omitted entirely rather than filled with placeholders. Severity is never repeated there — it lives on the finding in the review
- That checkboxes are ticked in the file as work lands, so a later session resumes from the file rather than from chat history
- End-of-session protocol: update the checklist, update front-matter `status`, append any new branch to `branches`, and **write the closing card comment** — what moved, what did not, and the next concrete action (§ The card is the session log)

## Workflow 2a — the review produces a plan

Preconditions, all three, checked and reported before anything is written:

- review `status: findings-agreed`
- zero `**Open**` markers in `## Open Questions`
- Chase has said to write the plan

Then:

1. **Mint the plan id.** Resolve dependencies (§ Dependency gating) and write `plans/<workstream>/<primary-review-filename>.md`, `consumes` listing every review id it takes, status from the dependency result.
2. **Close the review.** Front-matter → `status: done`, `outcome: plan`. Its card follows on the next board read; comment it with the plan's id and what the review concluded.
3. **Do not create the plan todo.** The projection makes it from the plan's front-matter. Comment it with the hand-over — which reviews it consumes, and the first phase to work.
4. **Index it** in `plans/README.md` with id and name; update the pairing row in `reviews/README.md`.
5. The plan must contain a `## Closing out` section stating: the plan todo moves to `done` only after Chase agrees the work is implemented and complete, the close-out comment records every branch it was committed to, and the pair is then archived.

**Hand-over is complete only when steps 1–4 have all happened.** Execution does not start before that — not because the review todo says `done`, which step 2 guarantees by construction, but because a plan whose READMEs and dependency status are unwritten is a plan the next session cannot pick up correctly. Report hand-over complete, explicitly, before any execution begins.

## Workflow 2b — the review produces no plan

**Normal, and must be supported.** Four magiq-media workstreams are review-only by design: `pending-decisions/` (decisions, not work), `asset-custody/` and `projection-rebuild/` (parked), `spec-structure/` (folded into another plan). A cycle that closes a review only when a plan is written leaves those open forever.

Set `outcome`, with a reason line in the review body:

| outcome | Review status | Todo | Also |
|---|---|---|---|
| `parked` | `parked` | `deferred` + tag `parked` | Reason mandatory |
| `decision-only` | `done` | `done` + tag `decision` | Log the call via [[decision]] when made |
| `folded-into:<id>` | `done` | `done` | Add this review's id to that document's `consumes` |
| `withdrawn` | `superseded` | `done` + tag `superseded` | Reason mandatory |

Update both READMEs in every case. **Never leave a review at `outcome: pending` once we have stopped working it.**

## Dependency gating

Run at plan authoring, at every session start on a plan, and at every phase boundary.

1. **Cycle check first.** Walk the `depends-on` graph by id. If A depends on B and B on A, directly or transitively, stop, print the cycle, ask which edge to break. Never report both as blocked and move on.
2. **Resolve each `depends-on` id** — grep for that `id:` and read its `status`:
   - id not found anywhere → **stop and ask.** A dangling id is a data error, not a blocked state.
   - review exists but has produced no plan → **unmet**
   - file with no front-matter → **unknown**: stop and ask, do not assume
   - `parked` or `superseded` → unmet, and say so explicitly: it is not coming unless someone restarts it
3. **Each `blocked-by-external` entry** → unmet. If `sent: false`, name writing and sending that ask as the critical path.
4. **All clear** → plan `status: active`, todo `in-progress`, drop `blocked`.
5. **Anything unmet** → plan `status: blocked`, plus a card comment naming which id blocks it, that id's current state, and — for an external blocker — whether the ask is written and sent.
6. **Partial blocking is the common case.** If only some phases depend on the blocked item, list the phases that can proceed now and the ones that cannot, and mark the blocked phases in the plan body. Do not block the whole plan.
7. **Never silently proceed past an unmet dependency.** Report and ask.

## External blockers

Work blocked outside this workspace — `authorization/` X-11.30 waits on the `magiq-auth` team to issue role claims, and the hand-off doc is written and unsent.

```yaml
blocked-by-external:
  - owner: <team or person>
    ask: <path to the written hand-off, or `-` if unwritten>
    sent: true | false
    since: YYYY-MM-DD
```

- Sets plan `status: blocked` and todo `deferred` + tag `blocked`, same as an internal dependency.
- **`sent: false` is the actionable state** — surface it as the critical path, not an errand. An unsent ask is work we own; a sent ask is work we wait on.
- **Never convert an external blocker into a `depends-on` entry.**

## Cross-project work

`magiq-auth` is both a project folder here and another team's repo. Which it is for a given piece of work is settled by the adoption marker, not by the folder.

- **Target has `we-operate: true`** → we own its code. Raise the review there: file, todo and id all land in the target project. The todo is tagged with the **origin's document id** and **inherits the origin's priority**, so it does not sit at `normal` while blocking urgent work. The origin lists the new review by id in `raised-by` / `depends-on`.
- **Target has no marker, or `we-operate: false`** → we do not own it. **Do not create a review there.** It is a `blocked-by-external` entry on the origin plan, with a hand-off doc.

Nothing orphans, because [[workstream-query]] sweeps every project's todo store, not one. A foreign-tagged todo surfaces from both ends.

## Finding ids and severity

**Finding ids are workstream-scoped.** Live schemes in use: `X-11.30` and `X-9.6` (the global drift register), `S13`, `INV-4`, `A1`. A review numbering `1..n` produces plans citing "finding 3" ambiguously.

- New review → prefix with an abbreviation of the workstream: `AC-1`, `AC-2` for `archive-cascade`.
- A finding belonging in the global drift register gets an `X-` number **there** instead, and the review cites that number rather than minting a local one. In doubt, ask which register — do not mint both.
- Stable once written. Plans reference them; never renumber.
- Finding ids are a different space from document ids: `AC-1` is a finding, `MM-014` is the review it lives in.

**Two scales, kept apart:**

- **Severity** — `High | Medium | Low`. A property of the finding. Every review, no exceptions, no emoji.
- **Gate status** — 🔴 / 🟠. A property of the *release decision*, owned solely by `type: gate` documents. Means "blocks the flag flip", not "is bad".

A High finding is not automatically a gate blocker; **the gate decides**. That is already how this repo works — `prod-readiness-gate.md` triages 42 open drift findings into 2 🔴 and 6 🟠. A review must not pre-empt that call.

## Findings discovered during execution

Work uncovers new problems constantly here — X-11.1 surfaced while *working* Phase 1 of the DDD plan, and a second defect (`ProcessingJobFailureCategory` missing `ValidationTimeout`) surfaced while fixing X-11.5. Without a rule these get appended to the plan as fresh checklist items, bypassing review, agreement and id discipline.

- A new finding **never** becomes a new checklist item in the plan that found it.
- It goes to the global drift register with an `X-` number, or to a new review in the appropriate workstream. Ask which when it is not obvious.
- The only mid-execution checklist edits allowed are ones that close, split, or correct an item tracing to a finding id the plan already consumes. Splitting keeps the original finding id on both halves. One further exception: [[ado-create-from-plan]] appends `AB#<story-id>` to an item when the plan is pushed to the board — that annotates an existing item rather than adding one, and it is what stops a re-run duplicating the hierarchy.
- If a new finding invalidates the plan's approach, **stop**. Do not re-plan in place — say so, and Chase decides whether the review reopens or a new one starts.
- Record every such diversion in the plan's session log.

## Gate lifecycle

- **Todo:** one, tagged [`<gate-id>`, `gate`], when the gate is worked as a unit. `prod-readiness-gate.md` qualifies — every code workstream starts from it.
- **Active:** while any consumed plan is open. Derive that automatically from the `consumes` ids.
- **Done:** every consumed plan `done` or `superseded` **and** Chase confirms the gate's question is answered — flags flipped, release cut. **Never auto-close.** The plans finishing is necessary, not sufficient.
- **A consumed plan archiving changes nothing.** `consumes` holds ids; archived is still `done`. Keep the entry.
- **Never auto-archived.** A gate outlives its plans — a release gate is re-read at the next release. It goes `superseded` only when a newer gate replaces it, with `supersedes:` on the successor pointing back.
- A gate may be added to at any time; it is not frozen until `done`.

## Frozen documents

A file at `status: done` is frozen: no edits, no status changes, no re-scoping.

Because cross-references are ids rather than paths, moving a file breaks nothing, so there is no reference-repair exception to make. Two narrow additive cases may still touch a frozen file:

- a `folded-into` review being added to a closed plan's `consumes:`
- a `supersedes:` pointer written onto a gate being replaced

Both are additive, both are reported, neither changes status.

## Archiving

A workstream is finished when its plan is `done` and no review in the folder is still `pending`. Then, in one step:

1. **Move both sides, same session.** Review(s) → `reviews/<workstream>/Archive/`, plan → `plans/<workstream>/Archive/`. A matched pair is what keeps the pairing legible afterwards.
2. **No reference repair needed.** `consumes` and `depends-on` hold ids, which the move does not touch. Confirm by re-resolving every id in the moved files; if any fails, something used a path and must be fixed.
3. **Move the README rows** into the archive section of each README, keeping id and name. Do not delete them.
4. **Todos stay `done`** in the store; do not delete them.
5. If the workstream folder is left empty apart from `Archive/`, leave it. Do not collapse into the top-level `plans/Archive/` — that is only for completed work with no live workstream left.

**Archiving is never automatic.** Propose it; Chase confirms.

## Legacy files

Roughly twenty review and plan files predate this skill and carry neither ids nor front-matter.

- **Never infer.** No front-matter means UNKNOWN status and no id. Do not treat it as met, unmet, active, or done. Stop and ask.
- **Do not bulk-rewrite.** Offer a backfill as a separate reviewable step, one workstream at a time, and only for workstreams about to be worked.
- Backfill derives status from `plans/README.md` and `reviews/README.md` — which are current — not from guesswork about the body, and mints ids oldest file first so the numbering reads chronologically.

## Known exceptions

1. `plans/spec-drift-review/spec-repo-drift-review.md` — a review living on the plans side, deliberately: it is its own working checklist and splitting it would separate the findings from the boxes tracking them. `type: review` plus an `exception:` line; leave it in place.
2. ~~`plans/projection-tables/` and `plans/deployment-naming/` — plan folders with no review counterpart~~ — **retired 2026-08-31.** Both were backfilled: MM-003 and MM-005 are *retrospective* reviews, written after their plans to record verified state rather than to argue work not yet done. Each carries an `exception:` line saying so and has no prompt file, because no session was ever run from it. The plans keep their legacy filenames (also `exception:`-marked) rather than being renamed after their reviews — ids are the link, so renaming would be churn.

   **The general rule this establishes:** where a plan predates the cycle and its work has already shipped, a retrospective review is the right way in, not a reason to leave the workstream outside. It is not licence to retro-fit a review for work that has *not* happened — that is fabricating the argument the cycle exists to make.
3. `plans/prod-readiness/prod-readiness-gate.md` — not an exception. It is `type: gate`, which legitimately has no review.

**Any check must skip files carrying `exception:` and report them, never "fix" them.**

## ADO

**Never create ADO items as part of the review → plan cycle.** It is a separate, explicit step, and most plans never go to the board at all. `ado:` stays `-` until someone runs [[ado-create-from-plan]] on purpose.

When it does run, it reads the plan shape this skill writes: phase → Feature, `- [ ]` item → User Story, the item's acceptance check → acceptance criteria verbatim, the finding id → Story title prefix and tag, and the finding's severity → story points. It refuses a plan that is `blocked`, `parked` or `superseded`, and skips phases the plan marks blocked — board items nobody can start are worse than none.

It writes back three ways, and all three matter: `ado: {project, epicId}` into the plan front-matter, `AB#<story-id>` appended to each checklist item, and `adoItemId` (the Epic) onto the plan's todo. Without the write-back a re-run duplicates the hierarchy and a ticked checkbox never closes its Story.

### `## ADO mapping` — optional, board-tracked plans only

Two things the board wants that a plan otherwise has no reason to carry. Add this block **only** when the workstream is tracked on ADO; omit it entirely otherwise rather than filling it with placeholders.

```markdown
## ADO mapping

| Phase | Branch |
|---|---|
| 1 — stop the stranding | `fix/archive-cascade-report` |
| 2 — bound the subtree | `fix/archive-cascade-bounds` |

| Item | Type |
|---|---|
| AC-1 | bugfix |
| AC-4 | refactor |
```

- **Branch per phase** — the Feature's branch. A phase is one branch, an item is one PR, matching the `Story/Bug = one PR` rule the architecture-review workstream already runs on.
- **Type per item** — `bugfix` · `feat` · `refactor` · `infra` · `chore`. Drives default task generation. **No type means no tasks generated** — that is correct behaviour, not a gap to paper over with a guess.

Severity is not repeated here. It lives on the finding in the review, and `ado-create-from-plan` reads it from the review named in `consumes`.

## Invariants

- Every review, plan and gate has an `id`. Ids are never reused or renumbered.
- All cross-references are ids. A path in `consumes` or `depends-on` is a bug.
- A dangling id is a data error — stop and ask, never treat it as blocked.
- A `plan` cannot exist without a review. A `gate` can — it consumes plans.
- A gate has no `depends-on`, and is never auto-closed or auto-archived.
- Plan execution does not start until hand-over is complete: plan written, review closed, both READMEs updated, dependency status resolved.
- A review with any `**Open**` question, or not yet at `findings-agreed`, cannot produce a plan.
- A review must reach a terminal `outcome`; `pending` is not a resting state.
- A plan is not `done` without Chase's explicit agreement plus at least one recorded branch.
- Every session that touches a review or plan leaves at least two card comments: what it picked up, and what it put down with the next concrete action. A session that ends with nothing moved still writes the second one.
- A finished workstream archives on both sides, in the same session.
- A `done` file is frozen; only additive `consumes` / `supersedes` edits touch it.
- A finding discovered during execution never becomes a checklist item in the plan that found it.
- Severity is High/Medium/Low. 🔴/🟠 appear only in `type: gate` documents.
- One workstream slug, used identically for the review folder, plan folder and both todos.
- **Status is written to the file, and only to the file.** The board is a projection: `tower/cycle.py` renders each document as a card on every read, and cycle cards cannot be dragged, closed or deleted. There is one writer, so there is nothing to reconcile.
- Reviews are raised only in projects with `we-operate: true`.

## Related

- [[workstream-query]] — the read side; never duplicate its queries here
- [[project-todos]] — the todo store API
- [[decision]] — for `decision-only` outcomes
- [[interrupt]] / [[triage]] — same item schema, different store
