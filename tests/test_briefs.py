"""Briefs reader: parsing and status derivation (no git, no network)."""

from tower.readers.briefs import (
    Brief,
    derive,
    front_matter,
    latest_revision,
    list_field,
    parse_brief,
    plan_phases,
)

BRIEF = """---
id: WG-180
type: brief
kind: feature
title: Rate-limit the public API
status: active
raised-by: alice@example.com
raised: 2026-10-25
origin: -
depends-on: [WG-171, WG-172]
superseded-by: -
---

# Rate-limit the public API

## Ask

Rate-limit it.
"""

REVIEW_R1 = """---
id: WG-180
type: brief-review
revision: 1
previous: -
imported: -
basis: []
---

## Findings

### R1 — x
- **Severity:** High

## External requests

### X1 — SDK primitive
- **To:** acme/platform

## Open questions

- **Q1:** which header? — Chase
"""

REVIEW_R2 = REVIEW_R1.replace("revision: 1", "revision: 2").split("## Open questions")[0] + "## Open questions\n\nNone.\n"

PLAN = """---
id: WG-180
type: plan
revision: 2
---

## Phase 1 — Config surface

- [ ] T1 — Options
  - Accept: x
- [ ] T2 — Defaults
  - Accept: y

## Phase 2 — Wire the limiter (blocked: X1)

- [ ] R1 — Middleware
  - Accept: z
"""


def _brief(**board):
    b = parse_brief("WG-180-rate-limit-the-public-api",
                    {"brief.md": BRIEF, "review-r1.md": REVIEW_R1, "plan-r1.md": PLAN,
                     "review-r2.md": REVIEW_R2, "plan-r2.md": PLAN})
    b.board = board
    return b


def test_front_matter_is_line_based_and_tolerates_dash_values():
    fm = front_matter(BRIEF)
    assert fm["id"] == "WG-180" and fm["superseded-by"] == "-" and fm["status"] == "active"
    assert front_matter("no fence") == {}
    assert front_matter("---\nstatus: active   # comment\n---\n")["status"] == "active"


def test_list_field():
    assert list_field("[WG-1, WG-2]") == ["WG-1", "WG-2"]
    assert list_field("[]") == [] and list_field("-") == [] and list_field(None) == []


def test_latest_revision_needs_both_files():
    assert latest_revision(["brief.md", "review-r1.md", "plan-r1.md", "review-r2.md"]) == 1
    assert latest_revision(["brief.md", "review-r1.md"]) == 0
    assert latest_revision(["review-r10.md", "plan-r10.md", "review-r2.md", "plan-r2.md"]) == 10


def test_plan_phases_strip_markers():
    ph = plan_phases(PLAN)
    assert [p["n"] for p in ph] == [1, 2]
    assert ph[1]["name"] == "Wire the limiter" and ph[1]["blocked"] == ["X1"]
    assert ph[0]["items"] == ["T1", "T2"] and ph[1]["items"] == ["R1"]


def test_parse_brief_reads_latest_revision():
    b = _brief()
    assert b.revision == 2 and b.depends_on == ["WG-171", "WG-172"]
    assert b.open_questions == 0          # r2 answered them; r1's question doesn't count
    assert b.external_requests == ["X1"] and not b.imported
    assert parse_brief("not-a-brief", {"brief.md": BRIEF}) is None
    assert parse_brief("WG-1-x", {"plan-r1.md": PLAN}) is None


def _phase(done=False, excluded=False, waits=()):
    return {"id": 1, "state": "", "done": done, "excluded": excluded, "inReview": False,
            "blocked": False, "waits": list(waits)}


def test_derive_order():
    b = _brief(); derive(b)
    assert b.chip == "not pushed" and b.next == "/ado-flow:push-plan WG-180"

    b = _brief(epic={"id": 9, "state": "Active"}, pushedRev=1, phases={}, outOfArea=[]); derive(b)
    assert b.chip == "behind r1 → r2"

    key = "acme/widgets/WG-180/X1"
    b = _brief(epic={"id": 9}, pushedRev=2, outOfArea=[],
               phases={1: _phase(done=True), 2: _phase(waits=[key])}); derive(b)
    assert b.chip == "waiting on X1" and b.next == "/ado-flow:brief deps WG-180"

    b = _brief(epic={"id": 9}, pushedRev=2, outOfArea=[],
               phases={1: _phase(done=True), 2: _phase(excluded=True)}); derive(b)
    assert b.chip == "ready to close" and b.next == "/ado-flow:wrapup 9"

    b = _brief(epic={"id": 9}, pushedRev=2, outOfArea=[{"id": 77, "area": "X"}], phases={}); derive(b)
    assert b.chip == "moved out of area" and "#77" in b.next


def test_derive_terminal_and_prs_win():
    b = _brief(); b.status = "superseded"; b.superseded_by = "WG-200"; derive(b)
    assert b.chip == "superseded → WG-200" and b.next == ""

    b = _brief(); b.prs = [{"number": 5, "needsAnswers": True}]; derive(b)
    assert b.chip == "needs answers"

    b = _brief(); b.prs = [{"number": 5, "needsAnswers": False}]; derive(b)
    assert b.chip == "brief PR open" and b.next == "merge PR #5"


def test_imported_unpushed_brief_asks_for_refresh():
    b = _brief()
    b.imported = True
    derive(b)
    assert b.chip == "imported — refresh" and b.next == "/ado-flow:brief refresh WG-180"


def test_brief_project_reads_memory_fields(tmp_path, monkeypatch):
    from tower import config
    from tower.readers import briefs
    monkeypatch.setattr(config, "PROJECTS_DIR", tmp_path)
    (tmp_path / "mm").mkdir()
    (tmp_path / "mm" / "MEMORY.md").write_text(
        "- **Repo**: Org/repo\n- **Repo base**: develop\n- **Brief source**: repo — a note\n", encoding="utf-8")
    p = briefs.brief_project("mm")
    assert p and p.repo == "Org/repo" and p.base == "develop" and p.remote == "https://github.com/Org/repo.git"
    (tmp_path / "mm" / "MEMORY.md").write_text("- **Repo**: Org/repo\n- **Brief source**: tower\n", encoding="utf-8")
    assert briefs.brief_project("mm") is None
