"""Review-cycle documents projected onto the Control Tower todo board.

The `review-cycle` skill declares document front-matter authoritative over the todo
store, and for good reason: `tower/data/` is gitignored — local-only, disposable,
invisible to another clone — while a review or plan file is versioned.

**There is one writer and one reader.** A review or plan's `status:` is set by working
it; the board shows that status and cannot change it. Cycle cards do not drag. This is
not a restriction bolted onto a two-way sync — it is why no sync is needed. The board
holds no cycle state of its own, so there is nothing for it to disagree with.

That also matches what the statuses are. `blocked` is *derived* from unmet
dependencies. `findings-agreed` is a judgement made after reading findings. A plan
reaching `done` needs a recorded branch and explicit agreement. None of those are
things a drag gesture can mean, so a board that offered the gesture would be lying
about what it could do.

  document → board   `reconcile()`, on every todo read. Status, state tags, source.
  document → board   missing todos are created, deterministically (see `todo_id_for`).
  board → document   nothing. `PATCH` refuses a status change on a cycle todo.

Status is the only projected field. Priority, due date and comments are not in
front-matter and stay board-editable — a comment is session log, not state.

Documents resolve **by id, never by path**. Ids survive rename, move and archive;
paths do not. A todo whose plan was archived last week still resolves, and its stale
`source` is repaired in passing.
"""

from __future__ import annotations

import html
import re
import uuid
from pathlib import Path
from typing import Any

from tower import config

DOC_ID_RE = re.compile(r"^[A-Z]{2,}-\d{3}$")
_FIELD_RE = re.compile(r"^([a-z-]+):\s*(.*)$")

# Folders scanned for cycle documents, relative to projects/<slug>/.
DOC_FOLDERS = ("reviews", "plans")

# Document file types. `.html` is not incidental — the design workstream keeps both
# its review and its plan as HTML, with the front-matter wrapped in an HTML comment.
DOC_SUFFIXES = (".md", ".html")

# Front-matter status -> (todo status, required state tag). The tag is additive;
# every cycle todo also carries its document id, type and workstream.
# Source: review-cycle SKILL.md § Status vocabularies.
_TO_TODO: dict[tuple[str, str], tuple[str, str | None]] = {
    ("review", "draft"):           ("new",         None),
    ("review", "findings-agreed"): ("in-progress", None),
    ("review", "done"):            ("done",        None),
    ("review", "parked"):          ("deferred",    "parked"),
    ("review", "superseded"):      ("done",        "superseded"),
    ("plan", "active"):            ("in-progress", None),
    ("plan", "blocked"):           ("deferred",    "blocked"),
    ("plan", "parked"):            ("deferred",    "parked"),
    ("plan", "superseded"):        ("done",        "superseded"),
    ("plan", "done"):              ("done",        None),
    ("gate", "active"):            ("in-progress", None),
    ("gate", "superseded"):        ("done",        "superseded"),
    ("gate", "done"):              ("done",        None),
}

_STATE_TAGS = ("blocked", "parked", "superseded")

# Stable namespace for deriving a todo id from a document id. Deriving rather than
# minting means the store is fully reconstructible from the documents: delete
# tower/data/ and the same cards come back with the same ids, so front-matter
# `todo-id` never dangles and there is no create-todo-then-write-the-uuid-back step.
_TODO_NAMESPACE = uuid.UUID("6f2a1c58-7b3d-5e90-a4c1-9d8e2f0b7a63")


class CycleViolation(Exception):
    """A cycle rule the caller broke. Carries a reader-facing reason."""


def todo_id_for(slug: str, doc_id: str) -> str:
    """The deterministic todo id for a document. Same inputs, same id, forever."""
    return str(uuid.uuid5(_TODO_NAMESPACE, f"{slug}:{doc_id}"))


# --- front-matter -----------------------------------------------------------


def parse_front_matter(path: Path) -> dict[str, str] | None:
    """Return the front-matter block as a flat str->str map, or None if absent.

    Values are returned raw (unquoted, unparsed) — callers that need a list read
    the bracket form themselves. Only the first block is considered, and only when
    the file opens with it; a `---` rule further down the body is not front-matter.

    Two openings are accepted. Markdown uses a bare `---` fence. **HTML documents
    wrap the same block in a comment**, because a bare fence at the top of an .html
    file renders as visible text on the page:

        <!--
        ---
        id: MM-020
        ---
        -->

    The design workstream keeps both its review and its plan as HTML, so this is not
    a hypothetical.
    """
    try:
        with path.open(encoding="utf-8", errors="replace") as fh:
            first = fh.readline().strip()
            if first == "<!--":
                first = fh.readline().strip()
            if first != "---":
                return None
            fields: dict[str, str] = {}
            for line in fh:
                line = line.rstrip("\n")
                if line.strip() == "---":
                    return fields
                match = _FIELD_RE.match(line)
                if match:
                    fields[match.group(1)] = match.group(2).strip()
    except OSError:
        return None
    return None


def write_status(path: Path, status: str) -> None:
    """Rewrite the front-matter `status:` line in place, leaving all else untouched.

    Handles both openings `parse_front_matter` accepts — the bare `---` fence and the
    HTML-comment-wrapped form.
    """
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.split("\n")
    start = 0
    if lines and lines[0].strip() == "<!--":
        start = 1
    if len(lines) <= start or lines[start].strip() != "---":
        raise CycleViolation(f"{path.name} has no front-matter to update.")
    for index in range(start + 1, len(lines)):
        if lines[index].strip() == "---":
            break
        if lines[index].startswith("status:"):
            lines[index] = f"status: {status}"
            path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
            return
    raise CycleViolation(f"{path.name} front-matter has no `status:` field.")


def is_empty_list(raw: str | None) -> bool:
    """True when a front-matter list field is absent or empty (`[]` / `-` / blank)."""
    return raw is None or raw.strip() in ("", "[]", "-")


# --- document index ---------------------------------------------------------


def index_documents(slug: str) -> dict[str, dict[str, Any]]:
    """Map document id -> {path, rel, type, status, fields} for one project.

    Scans reviews/ and plans/ recursively, Archive/ folders included — an archived
    document is still a resolvable id. Files without front-matter are legacy and are
    skipped silently; per the skill their status is UNKNOWN and must not be inferred.
    """
    root = config.PROJECTS_DIR / slug
    index: dict[str, dict[str, Any]] = {}
    for folder in DOC_FOLDERS:
        base = root / folder
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if path.suffix not in DOC_SUFFIXES or not path.is_file():
                continue
            fields = parse_front_matter(path)
            if not fields:
                continue
            doc_id = fields.get("id", "")
            if not DOC_ID_RE.match(doc_id):
                continue
            index[doc_id] = {
                "path": path,
                "rel": path.relative_to(config.PROJECTS_DIR.parent).as_posix(),
                "type": fields.get("type", ""),
                "status": fields.get("status", ""),
                "fields": fields,
            }
    return index


def todo_doc_id(item: dict[str, Any]) -> str | None:
    """The document id tag on a todo, or None if this is not a cycle todo."""
    for tag in item.get("tags") or []:
        if DOC_ID_RE.match(tag):
            return tag
    return None


# --- mapping ----------------------------------------------------------------


def to_todo(doc_type: str, doc_status: str) -> tuple[str, str | None]:
    """Front-matter status -> (todo status, state tag). Raises on an unknown pair."""
    try:
        return _TO_TODO[(doc_type, doc_status)]
    except KeyError:
        raise CycleViolation(
            f"`{doc_status}` is not a valid status for a {doc_type or 'document'}. "
            f"Valid: {', '.join(s for t, s in _TO_TODO if t == doc_type) or 'none'}."
        )


# --- projection --------------------------------------------------------------


def _heading_of(path: Path) -> str:
    """The document's first `# ` heading, or `<title>` for HTML. Empty if neither."""
    try:
        with path.open(encoding="utf-8", errors="replace") as fh:
            for _ in range(80):  # headings live near the top; do not read whole files
                line = fh.readline()
                if not line:
                    break
                stripped = line.strip()
                if stripped.startswith("# "):
                    # Drop a leading "Plan:" / "Review:" — the badge already says which.
                    return re.sub(r"^(plan|review|gate)\s*[:—-]\s*", "",
                                  stripped[2:].strip(), flags=re.I)
                match = re.search(r"<title>(.*?)</title>", stripped, re.I)
                if match:
                    # A <title> carries entities (&amp;, &mdash;); a card title should not.
                    return html.unescape(match.group(1)).strip()
    except OSError:
        pass
    return ""


def _title_for(doc: dict[str, Any]) -> str:
    """A readable title for an auto-created card.

    Prefers the document's own H1, because `MM-034 — archive-cascade review` tells you
    nothing you could not read off the badge, while "Archive cascade — scale ceiling"
    is the thing you are actually deciding whether to pick up. Falls back to the
    workstream and type when a document has no heading.
    """
    fields = doc["fields"]
    heading = _heading_of(doc["path"])
    if heading:
        return heading
    workstream = fields.get("workstream") or "unassigned"
    return f"{fields.get('id', '?')} — {workstream} {doc['type'] or 'document'}"


def reconcile(
    slug: str, items: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], bool]:
    """document -> board. Return (items, changed).

    Projects every indexed document's status onto its card, creating the card if it
    does not exist yet. Resolution is by document id, so a document that has been
    renamed, moved or archived still matches and its stale `source` is repaired.

    A todo whose id tag resolves to no document is **left alone** — a dangling id is a
    data error for a human to look at, not something to normalise away silently. A
    document whose front-matter carries a status this skill does not define is skipped
    rather than projected; `check()` reports both.
    """
    from tower.interrupts.store import make_item, set_archived, stamp_done

    index = index_documents(slug)
    if not index:
        return items, False

    changed = False
    by_doc_id = {todo_doc_id(i): i for i in items if todo_doc_id(i)}

    for doc_id, doc in sorted(index.items()):
        item = by_doc_id.get(doc_id)
        try:
            status, state_tag = to_todo(doc["type"], doc["status"])
        except CycleViolation:
            continue  # malformed front-matter: check() reports it, don't guess

        wanted_tags = [doc_id, doc["type"] or "document"]
        workstream = doc["fields"].get("workstream")
        if workstream:
            wanted_tags.append(workstream)
        if state_tag:
            wanted_tags.append(state_tag)

        if item is None:
            item = make_item(
                _title_for(doc), source=doc["rel"], status=status, tags=wanted_tags,
            )
            item["id"] = todo_id_for(slug, doc_id)
            if "/Archive/" in doc["rel"]:
                set_archived(item, True)
            items.append(item)
            changed = True
            continue

        if item.get("status") != status:
            previous = item.get("status")
            item["status"] = status
            stamp_done(item, previous)
            changed = True
        elif status == "done" and not item.get("doneAt"):
            stamp_done(item)            # backfill for cards that predate the field
            changed = True

        # A document filed under Archive/ is finished, so its card is too. Derived,
        # not set by hand — unarchiving a card whose document is still archived would
        # only come back on the next read.
        doc_archived = "/Archive/" in doc["rel"]
        if doc_archived and not item.get("archivedAt"):
            set_archived(item, True)
            changed = True

        # Preserve any tag a human added; only the cycle-owned ones are managed here.
        tags = list(item.get("tags") or [])
        managed = set(_STATE_TAGS) | {doc_id, doc["type"], workstream} - {None}
        merged = [t for t in tags if t not in managed] + wanted_tags
        seen: set[str] = set()
        merged = [t for t in merged if not (t in seen or seen.add(t))]
        if merged != tags:
            item["tags"] = merged
            changed = True

        if item.get("source") != doc["rel"]:
            item["source"] = doc["rel"]
            changed = True

    return items, changed


def _ids_in(raw: str | None) -> list[str]:
    """Document ids named in a front-matter list field, in order."""
    return [] if is_empty_list(raw) else re.findall(r"[A-Z]{2,}-\d{3}", raw or "")


# A dependency is met when the thing depended on has finished. `parked` and
# `superseded` are explicitly NOT met — SKILL.md § Dependency gating: "it is not
# coming unless someone restarts it", which is the case most worth surfacing.
_MET = {"done", "superseded"}


def _external_blockers(fields: dict[str, str], path: Path) -> list[dict[str, Any]]:
    """Parse the `blocked-by-external` list. Empty when absent or `[]`.

    Nested YAML, so it needs the raw lines rather than the flat field map.
    """
    raw = fields.get("blocked-by-external")
    if raw and raw.strip() not in ("", "[]", "-"):
        return []  # inline form, nothing structured to read
    out: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").split("\n")
    except OSError:
        return out
    inside = False
    current: dict[str, Any] = {}
    for line in lines[:60]:
        if line.startswith("blocked-by-external:"):
            inside = True
            continue
        if inside:
            if line.strip() == "---" or (line and not line.startswith(" ")):
                break
            match = re.match(r"\s*-?\s*([a-z]+):\s*(.*)$", line)
            if not match:
                continue
            key, value = match.group(1), match.group(2).strip()
            if key == "owner" and current:
                out.append(current)
                current = {}
            current[key] = value
    if current:
        out.append(current)
    for entry in out:
        entry["sent"] = str(entry.get("sent", "")).lower() == "true"
    return out


def dependency_graph(slug: str) -> dict[str, dict[str, Any]]:
    """Per-document dependency edges, both directions, with met/unmet resolved.

    The forward edges (`consumes`, `depends-on`) are in front-matter. The **reverse**
    edge — what a document blocks — is not written anywhere, and it is the one that
    answers "can I close this yet". Derived here so the board can show both.
    """
    index = index_documents(slug)
    graph: dict[str, dict[str, Any]] = {
        doc_id: {"consumes": [], "dependsOn": [], "blocks": [], "external": [],
                 "unmet": 0, "unsentAsks": 0}
        for doc_id in index
    }

    def describe(ref: str) -> dict[str, Any]:
        target = index.get(ref)
        if not target:
            return {"id": ref, "status": "missing", "type": "", "met": False,
                    "title": "", "dangling": True}
        return {"id": ref, "status": target["status"], "type": target["type"],
                "met": target["status"] in _MET,
                "title": _title_for(target)}

    for doc_id, doc in index.items():
        fields = doc["fields"]
        for field, key in (("consumes", "consumes"), ("depends-on", "dependsOn")):
            for ref in _ids_in(fields.get(field)):
                edge = describe(ref)
                graph[doc_id][key].append(edge)
                if ref in graph:
                    graph[ref]["blocks"].append(
                        {"id": doc_id, "status": doc["status"], "type": doc["type"],
                         "via": key, "title": _title_for(doc)})
        graph[doc_id]["external"] = _external_blockers(fields, doc["path"])

    for doc_id, entry in graph.items():
        # `consumes` is a provenance link, not a gate — a plan consumes a review that
        # is already done by construction. Only `depends-on` and external asks gate.
        entry["unmet"] = sum(1 for e in entry["dependsOn"] if not e["met"])
        entry["unsentAsks"] = sum(1 for e in entry["external"] if not e.get("sent"))
    return graph


def annotate(slug: str, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Tag each cycle item with a transient `cycle` block for the UI.

    Not persisted — `save_interrupts` is called before this. The frontend reads it to
    render the card as a document projection: no drag, no status buttons, a link back
    to the file, and the dependency picture.
    """
    index = index_documents(slug)
    graph = dependency_graph(slug)
    for item in items:
        doc_id = todo_doc_id(item)
        doc = index.get(doc_id) if doc_id else None
        if doc:
            item["cycle"] = {
                "id": doc_id,
                "type": doc["type"],
                "status": doc["status"],
                "path": doc["rel"],
                "workstream": doc["fields"].get("workstream", ""),
                "archived": "/Archive/" in doc["rel"],
                "deps": graph.get(doc_id, {}),
            }
        elif doc_id:
            # Tagged as a cycle todo but the document is gone. Say so on the card
            # rather than silently rendering it as an ordinary draggable item.
            item["cycle"] = {"id": doc_id, "dangling": True}
    return items


def comment(slug: str, doc_id: str, text: str, author: str = "Claude") -> dict[str, Any]:
    """Append a session-log entry to a document's card. Resolves by document id.

    The card is the running history of a review or plan: what was picked up, what
    moved, where to resume. Status lives in front-matter and is projected; a comment
    is the *narrative* beside it, and the only writable thing on a cycle card.

    One call on purpose. Doing this through the store directly means resolving the
    todos file, then the card's uuid, then appending — three steps, and a log that
    costs three steps is a log that does not get written.

    Creates the card first if the projection has not rendered it yet, so a comment
    can be the first thing that happens to a freshly written document.
    """
    from tower.interrupts.store import append_activity, load_interrupts, save_interrupts

    path = config.todos_file(slug)
    items = load_interrupts(path) if path.exists() else []
    items, changed = reconcile(slug, items)
    if changed:
        save_interrupts(path, items)

    todo_id = todo_id_for(slug, doc_id)
    if not any(i["id"] == todo_id for i in items):
        # Reconcile creates cards for indexed documents; a miss means the id is unknown.
        raise CycleViolation(
            f"{doc_id} resolves to no document in {slug}, so there is no card to comment on."
        )
    return append_activity(path, todo_id, "comment", text.strip(), author=author)


def assert_not_cycle(slug: str, item: dict[str, Any], action: str) -> None:
    """Raise CycleViolation if `item` is a cycle todo. Guards status writes and delete."""
    doc_id = todo_doc_id(item)
    if not doc_id:
        return
    raise CycleViolation(
        f"{doc_id} is a review-cycle document, so its status is not the board's to "
        f"{action}. Status comes from the `status:` field in {doc_id}'s file and the "
        "board shows it — work the document and the card follows. "
        "Priority, due date and comments are still yours to change here."
    )


# --- integrity check ---------------------------------------------------------


def known_exceptions(slug: str) -> list[tuple[str, str]]:
    """Files carrying `exception:`, as (rel path, reason).

    SKILL.md § Known exceptions: *any check must skip files carrying `exception:` and
    report them, never "fix" them.* `check()` does the skipping; this does the
    reporting, so a deliberate deviation stays visible instead of becoming invisible.
    """
    found: list[tuple[str, str]] = []
    root = config.PROJECTS_DIR / slug
    for folder in DOC_FOLDERS:
        base = root / folder
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if path.suffix not in DOC_SUFFIXES or not path.is_file():
                continue
            fields = parse_front_matter(path)
            if fields and fields.get("exception"):
                rel = path.relative_to(config.PROJECTS_DIR.parent).as_posix()
                found.append((rel, fields["exception"]))
    return found


def _review_folders(slug: str) -> set[str]:
    """Workstream folder names under reviews/ that actually contain a review."""
    base = config.PROJECTS_DIR / slug / "reviews"
    if not base.is_dir():
        return set()
    names: set[str] = set()
    for path in base.rglob("*"):
        if path.suffix in (".md", ".html") and path.is_file() and path.name != "README.md":
            # reviews/<ws>/... and reviews/<ws>/Archive/... both credit <ws>.
            names.add(path.relative_to(base).parts[0] if len(path.relative_to(base).parts) > 1
                      else "Archive" if path.parent.name == "Archive" else "")
    return {n for n in names if n}


def check(slug: str) -> list[str]:
    """Problems the projection cannot fix by itself. Empty list means clean.

    Covers what `reconcile` deliberately stays quiet about — it skips malformed and
    dangling records rather than guessing, which is right for a board render and wrong
    as a permanent silence — plus the structural invariant no render can see:
    **a plan cannot exist without a review.**

    Files carrying `exception:` are skipped entirely and reported by
    `known_exceptions()` instead.
    """
    problems: list[str] = []
    root = config.PROJECTS_DIR / slug
    seen: dict[str, str] = {}

    for folder in DOC_FOLDERS:
        base = root / folder
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if path.suffix not in DOC_SUFFIXES or not path.is_file():
                continue
            fields = parse_front_matter(path)
            if not fields or fields.get("exception"):
                continue
            rel = path.relative_to(config.PROJECTS_DIR.parent).as_posix()
            doc_id = fields.get("id", "")
            if not DOC_ID_RE.match(doc_id):
                problems.append(f"{rel}: front-matter present but `id:` is missing or malformed")
                continue
            if doc_id in seen:
                problems.append(f"{doc_id}: duplicate id — also at {seen[doc_id]} ({rel})")
            seen[doc_id] = rel
            try:
                to_todo(fields.get("type", ""), fields.get("status", ""))
            except CycleViolation as exc:
                problems.append(f"{doc_id} ({rel}): {exc}")
            expected = todo_id_for(slug, doc_id)
            if fields.get("todo-id") not in (None, "-", expected):
                problems.append(
                    f"{doc_id}: `todo-id` is {fields.get('todo-id')}, but the derived id "
                    f"is {expected}. Derive it — never allocate one"
                )

    for doc_id, rel in seen.items():
        fields = parse_front_matter(config.PROJECTS_DIR.parent / rel) or {}
        for field in ("consumes", "depends-on"):
            raw = fields.get(field)
            if is_empty_list(raw):
                continue
            for ref in re.findall(r"[A-Z]{2,}-\d{3}", raw or ""):
                if ref not in seen:
                    problems.append(
                        f"{doc_id}: `{field}` names {ref}, which resolves to no document"
                    )

    problems.extend(_check_plans_have_reviews(slug, seen))
    return problems


def _check_plans_have_reviews(slug: str, seen: dict[str, str]) -> list[str]:
    """`A plan cannot exist without a review.` A gate can — it consumes plans.

    Two ways a plan proves it has one, matching how the tree actually works:

    - **Cycle-compliant** — front-matter `consumes:` names at least one review id.
    - **Legacy** — the workstream folder pairing: `plans/<ws>/` ↔ `reviews/<ws>/`, which
      is the convention every pre-cycle plan was filed under. `plans/Archive/` at the
      root pairs with `reviews/Archive/`.

    Anything else is flagged. That bias is deliberate: a new unpaired plan should trip
    this, and the way to silence it is an `exception:` line saying why — which is a
    sentence someone has to write and stand behind.
    """
    problems: list[str] = []
    base = config.PROJECTS_DIR / slug / "plans"
    if not base.is_dir():
        return problems

    paired = _review_folders(slug)
    for path in sorted(base.rglob("*")):
        if path.suffix not in DOC_SUFFIXES or not path.is_file():
            continue
        if path.name == "README.md":
            continue
        rel = path.relative_to(config.PROJECTS_DIR.parent).as_posix()
        fields = parse_front_matter(path) or {}
        if fields.get("exception"):
            continue
        if fields.get("type") in ("gate", "review", "doc"):
            continue  # a gate consumes plans; a review here is its own exception case

        parts = path.relative_to(base).parts
        workstream = parts[0] if len(parts) > 1 else ""

        doc_id = fields.get("id", "")
        if DOC_ID_RE.match(doc_id):
            if is_empty_list(fields.get("consumes")):
                problems.append(
                    f"{doc_id} ({rel}): plan has no review — `consumes:` is empty. "
                    "A plan cannot exist without a review"
                )
            continue

        if not workstream:
            problems.append(f"{rel}: plan sits at the plans/ root, outside any workstream folder")
        elif workstream not in paired:
            problems.append(
                f"{rel}: plan has no review — reviews/{workstream}/ holds none. "
                "Pair it, or add an `exception:` line saying why it has none"
            )
    return problems
