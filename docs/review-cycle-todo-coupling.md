# Review-cycle documents on the Control Tower board

**Added 2026-08-31.** Implemented in `tower/cycle.py`, wired into `tower/server.py` at three points
and `tower/static/index.html` at three more.

## The problem it fixes

The `review-cycle` skill declares document front-matter authoritative over the todo store. Until now
that was etiquette, not mechanism. There were two writable stores with nothing between them:

- Drag a card on the board → the store changed, the review or plan did not.
- A Claude session edits a plan's `status:` → the file changed, the board did not.

Either way the next session read a status that had quietly stopped being true. The asymmetry made it
worse than it sounds: `tower/data/` is **gitignored** — local-only, not versioned, invisible to
another clone — so the thing you actually touch was the disposable copy, and the durable record was
the one nobody was updating.

## The design

**One writer, one reader.** A review or plan's status is set by working it. The board shows that
status and cannot change it. Cycle cards do not drag, have no Done or delete button, and carry a
badge naming their document.

This is not a lock bolted onto a two-way sync — it is *why no sync is needed*. The board holds no
cycle state of its own, so there is nothing for it to disagree with.

It also matches what those statuses are. `blocked` is **derived** from unmet dependencies.
`findings-agreed` is a judgement made after reading findings. A plan reaching `done` needs a recorded
branch and explicit agreement. None of those are things a drag gesture can mean, so a board offering
the gesture would be lying about what it could do.

| Direction | Trigger | What happens |
|---|---|---|
| document → board | `GET /api/projects/{slug}/todos` | Status, state tags and `source` projected onto the card |
| document → board | same | A document with no card gets one, created deterministically |
| board → document | — | Nothing. `PATCH` of a cycle todo's status returns 409 |

**Status is the only projected field.** Priority, due date and comments are not in front-matter, so
they stay board-editable. A comment is session log, not state — keep using them.

## Deterministic ids

A card's id is `uuid5(namespace, "<slug>:<doc-id>")`, so it is a pure function of the document.

Three things fall out:

- **The store is fully reconstructible.** Delete `tower/data/` and every card returns with the same
  id, status and tags. The documents *are* the backup.
- **`todo-id` in front-matter can never dangle**, because it is derivable rather than allocated:
  `cycle.todo_id_for(slug, doc_id)`.
- **The old chicken-and-egg step is gone.** Workflow 1 used to require creating a todo first so the
  file could carry a real `todo-id`. Now you write the file; the card follows.

## Resolution is by id, never by path

`index_documents()` scans `projects/<slug>/reviews/` and `projects/<slug>/plans/` recursively,
**`Archive/` folders included**, and keys everything by front-matter `id:`.

This is the whole reason the skill mandates ids. A plan archived last week still resolves, and the
card's now-stale `source` is repaired in passing. Renames, moves and archiving are all free.

Files without front-matter are **skipped silently** — they are legacy, their status is UNKNOWN per
the skill's § Legacy files, and inferring one would be worse than leaving them alone. They get no
card and keep whatever board state they already had.

## Status mapping

`_TO_TODO` in `tower/cycle.py`, straight from SKILL.md § Status vocabularies:

| Type | Front-matter | Todo status | State tag |
|---|---|---|---|
| review | `draft` | `new` | — |
| review | `findings-agreed` | `in-progress` | — |
| review | `done` | `done` | — |
| review | `parked` | `deferred` | `parked` |
| review | `superseded` | `done` | `superseded` |
| plan | `active` | `in-progress` | — |
| plan | `blocked` | `deferred` | `blocked` |
| plan | `parked` | `deferred` | `parked` |
| plan | `superseded` | `done` | `superseded` |
| plan | `done` | `done` | — |
| gate | `active` | `in-progress` | — |
| gate | `superseded` | `done` | `superseded` |
| gate | `done` | `done` | — |

There is no reverse map. It was deleted along with the guardrails that existed only to police it —
a status the board cannot set needs no validation.

Tags a human adds are preserved; only the cycle-owned ones (document id, type, workstream, state tag)
are managed.

## In the UI

| Element | Behaviour |
|---|---|
| Card | `draggable="false"`, `data-cycle="1"`, `data-cycle-type`, left border and tint coloured by type |
| Badge | glyph + **type word** + id — `◇ REVIEW · MM-003`, `▤ PLAN · MM-004`, `⛌ GATE · MM-0xx` |
| Tooltip | id, type, workstream, status, what that phase means, and the file path |
| Footnote | *projection-tables — review status set in MM-003* |
| Done / delete | Suppressed, on both the kanban card and the list row |
| Dangling id | Red `⚠ MM-0xx missing` badge — the card is tagged but no document has that id |

**Colour encodes the phase**, because that is the question the card is being asked:

| Type | Colour | Means |
|---|---|---|
| review | amber (`--warn`) | Findings still being argued. Nothing sequenced; no plan exists until findings are agreed |
| plan | blue (`--accent`) | Findings agreed, work sequenced. This is what execution tracks against |
| gate | purple (`--purple`) | A release decision over plans. Not a work item |

Amber → blue reads as the cycle's own direction of travel, so a workstream's phase is legible from
the colours alone. The footnote carries the workstream slug, so a review and its plan are visibly a
pair — `projection-tables` on both MM-002 and MM-003 says that workstream has finished arguing and is
now sequenced.

`dragstart` is also skipped for `data-cycle` elements, so a drag cannot start from a source that
ignores the `draggable` attribute.

## Integrity check

`reconcile()` deliberately stays quiet about malformed and dangling records — guessing would be
worse for a board render. `cycle.check(slug)` is where that silence gets broken:

```bash
python -c "from tower import cycle; [print(p) for p in cycle.check('magiq-media')] or print('clean')"
```

Reports duplicate ids, front-matter with a missing or malformed `id:`, statuses outside the
vocabulary, and `consumes` / `depends-on` entries naming a document that does not exist. Run it after
any backfill — duplicate ids are the live risk while ids are still being minted into legacy files.

## Failure modes

| Situation | Behaviour |
|---|---|
| Card tagged with an id matching no document | Rendered with a red *missing* badge; left otherwise alone. A dangling id is a data error for a human, not something to normalise away |
| Document status not in the vocabulary | No card projected; `check()` reports it |
| Document has no front-matter | Not indexed, no card |
| `tower/data/todos/{slug}.json` deleted | Every cycle card returns on the next board load, same ids. Ordinary todos are lost — they only live there |
| Two documents share an id | Last scanned wins the projection; `check()` names both files |
| Someone `PATCH`es a cycle status via the API | 409 with the reason. The UI never offers it, but the API is the real boundary |

## Rolling it back

Server — three edits in `tower/server.py`: the `cycle.reconcile` / `cycle.annotate` calls in
`get_todos`, and the `cycle.assert_not_cycle` guard in `patch_todo` and `delete_todo`.

Frontend — three in `tower/static/index.html`: the `.cycle-card` CSS block, the `_cycleBadge` helper
plus its use in `_itemCardHTML` and `_itemRowHTML`, and the `data-cycle` skip in the `dragstart`
wiring.

`tower/cycle.py` has no other callers and imports nothing from the server, so it can be left in place
or deleted. No data schema changed: cycle todos are ordinary todos that carry an id tag, and every
document keeps the front-matter the skill already specified.

## Related

- `.claude/skills/review-cycle/SKILL.md` § Todo store, § Status vocabularies
- `.claude/skills/project-todos/SKILL.md` — the store API
- `tower/cycle.py` — the implementation, with the reasoning in its module docstring
