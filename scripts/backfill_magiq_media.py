"""One-shot backfill: give every live magiq-media review and plan front-matter.

Run once, on 2026-08-31, to finish what the projection-tables / deployment-naming
backfill started. Kept in-repo as the record of what was written and where each value
came from — not as a tool to re-run.

**Every status below is transcribed from `reviews/README.md` and `plans/README.md`**,
which the review-cycle skill names as the derivation source for a backfill and which
were current as of 2026-08-27. Nothing is inferred from a file body. Where the two
READMEs disagree with each other the prose wins over the table, and the line that
decided it is quoted in the comment.

Ids are minted oldest-first so the batch reads chronologically. MM-001..MM-006 were
already taken, and two of them predate MM-007, so the sequence is not globally
chronological — ids are never renumbered, so that stays as it is.

Archive/ folders are deliberately skipped: those documents are finished, their pairing
is already recorded in the READMEs, and cards for them would only pad the Done column.
"""

import io
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from tower import cycle  # noqa: E402

PROJECT = "magiq-media"
ROOT = REPO / "projects" / PROJECT
ARCH_REVIEWS = [f"MM-{n:03d}" for n in range(7, 18)]  # the 11 module + cross-cutting reviews

# (id, rel path, type, created, fields...)
# `status` / `outcome` transcribed from the READMEs; see module docstring.
DOCS: list[dict] = []


def review(mm, rel, ws, created, status, outcome, note=None, exception=None):
    DOCS.append(dict(id=mm, rel=rel, type="review", workstream=ws, created=created,
                     status=status, outcome=outcome, note=note, exception=exception))


def plan(mm, rel, ws, created, status, consumes, note=None, exception=None, blocked=None):
    DOCS.append(dict(id=mm, rel=rel, type="plan", workstream=ws, created=created,
                     status=status, consumes=consumes, note=note, exception=exception,
                     blocked=blocked))


# --- 2026-07-19 · architecture-review-remediation, 11 reviews -----------------
# reviews/README.md: "11 module + cross-cutting reviews, read as one body | Done | plan"
_arch = [
    "assetmanagement-architecture-review.md",
    "catalog-collection-architecture-review.md",
    "catalog-folder-architecture-review.md",
    "catalog-mediaitem-architecture-review.md",
    "catalog-mediaprofile-architecture-review.md",
    "changerequests-architecture-review.md",
    "cross-module-impact-sweep-2026-07-19.md",
    "cross-module-integration-review.md",
    "metadata-recordtype-architecture-review.md",
    "processing-processingjob-architecture-review.md",
    "registration-registration-architecture-review.md",
]
for mm, name in zip(ARCH_REVIEWS, _arch):
    review(mm, f"reviews/architecture-review-remediation/{name}",
           "architecture-review-remediation", "2026-07-19", "done", "plan",
           note="One of 11 read as a single body of work; all consumed together by MM-018.")

# --- 2026-07-20 · architecture-review-remediation plans -----------------------
# plans/README.md: IMPLEMENTATION-PLAN "Active | The live tracker and source of truth
# for state". Chase's call 2026-08-31: the tracker carries the plan id, because its
# status is what the workstream's state actually means.
plan("MM-018", "plans/architecture-review-remediation/IMPLEMENTATION-PLAN.md",
     "architecture-review-remediation", "2026-07-20", "active", ARCH_REVIEWS,
     note="The live tracker and source of truth for state: status columns in §5, session "
          "log in §9. 169 ADO work items across 6 Epics, every row still To Do — the "
          "session log has one entry, 2026-07-20 'Plan created. Nothing started.'")
# plans/README.md: "**Parked** | Authorization (C0-C8) and the transactional outbox
# (B4/INV-2). Deferred in sequencing only - both remain pre-production gates."
plan("MM-019", "plans/architecture-review-remediation/architecture-review-authz-and-outbox-deferred-plan.md",
     "architecture-review-remediation", "2026-07-20", "parked", ARCH_REVIEWS,
     note="Parked reason: deferred in **sequencing only**. Both halves remain "
          "pre-production gates — see MM-006. Owner is Chase on every item, and the "
          "ADO items are drafted in the file rather than created.")

# --- 2026-08-20 · design -----------------------------------------------------
review("MM-020", "reviews/design/mediaitem-edit-lifecycle-as-is-vs-recommended.html",
       "design", "2026-08-20", "done", "plan",
       note="HTML. Front-matter is wrapped in an HTML comment so it does not render.")
plan("MM-021", "plans/design/mediaitem-edit-session-design.html",
     "design", "2026-08-20", "active", ["MM-020"],
     note="HTML, same wrapping as MM-020. Verified against the repo 2026-08-31: 5 of the "
          "7 commands exist (CheckOut, Renew, CheckIn, AbandonCheckout, ForceRelease). "
          "`AddSessionEditor` / `RemoveSessionEditor` do not — the collaborative half "
          "(scenario 2) is unbuilt, so only the solo path ships.")

# --- 2026-08-21 · the drift review, which lives on the plans side ------------
# review-cycle SKILL.md § Known exceptions #1.
review("MM-022", "plans/spec-drift-review/spec-repo-drift-review.md",
       "spec-drift-review", "2026-08-21", "findings-agreed", "pending",
       exception="a review living in plans/ deliberately — it is its own working checklist, and "
                 "splitting it would separate the findings from the boxes tracking them. "
                 "SKILL.md § Known exceptions #1.",
       note="58 of 213 findings still open. The ✓ column in the file is the working checklist. "
            "Its 154 closed findings live in Archive/spec-repo-drift-review-completed.md; "
            "the id sets do not overlap.")

# --- 2026-08-24 · spec-ddd-coverage ------------------------------------------
review("MM-023", "reviews/spec-drift-review/spec-ddd-coverage-review-2026-08-24.md",
       "spec-drift-review", "2026-08-24", "done", "plan",
       note="Spec only, no code read — every finding is 'the spec does not say', never "
            "'the code does not do'.")
plan("MM-024", "plans/spec-drift-review/spec-ddd-coverage-review-2026-08-24.md",
     "spec-drift-review", "2026-08-24", "active", ["MM-023"],
     note="Six phases. **Phase 1 complete 2026-08-25** — 15 of 17 truncated spec tails "
          "recovered, 3 quarantined to docs/spec/_recovered/, 2 unrecoverable. D2 resolved; "
          "**D1 and D3-D6 still block Phases 2 and 4**.")

# --- 2026-08-25 · the batch --------------------------------------------------
review("MM-025", "reviews/archive-cascade/archive-cascade-review-2026-08-25.md",
       "archive-cascade", "2026-08-25", "done", "plan")
plan("MM-026", "plans/archive-cascade/archive-cascade-review-2026-08-25.md",
     "archive-cascade", "2026-08-25", "active", ["MM-025"],
     note="X-11.16, X-11.18 and X-11.15 closed 2026-08-27; **X-11.41 next**, X-11.17 "
          "narrowed but open, X-11.19 open. Never compiled — no .NET SDK in those "
          "sessions; run `dotnet test tests/modules/Catalog/` before treating any of it "
          "as closed.")
review("MM-027", "reviews/asset-custody/asset-custody-review-2026-08-25.md",
       "asset-custody", "2026-08-25", "parked", "parked",
       note="Parked reason, from reviews/README.md: raised while classifying `Asset` for the "
            "ownership ADR and split out so the spec-drift work could continue. The decision "
            "is already recorded in docs/adrs/ownership-and-authorization.md — what is parked "
            "is the work, and it is **blocked by X-11.32**, the detach half of the asset "
            "lifecycle never reaching the Asset aggregate. Sequencing is fixed: wire detach → "
            "model custody → let authorization replace the interim owner checks. Do not remove "
            "`AssetOwnership.CheckOwner` before the last step; it currently guards 8 commands.")
review("MM-028", "reviews/authorization/authorization-review-2026-08-25.md",
       "authorization", "2026-08-25", "done", "plan")
# plans/README.md heading says Active, but its own prose says "**X-11.30 is now blocked
# on another team**" and names the unsent hand-off. Per SKILL.md an unmet
# blocked-by-external entry makes the plan `blocked`; `sent: false` is the actionable
# state and the critical path.
plan("MM-029", "plans/authorization/authorization-review-2026-08-25.md",
     "authorization", "2026-08-25", "blocked", ["MM-028"],
     blocked=dict(owner="magiq-auth team",
                  ask="docs/spec/shared/magiq-auth-role-claims-requirements.md",
                  sent="false", since="2026-08-26"),
     note="X-11.31 and X-11.23 closed 2026-08-26; X-11.34 and X-11.35 verified and both hold. "
          "**X-11.30 is the only 🔴 left on MM-006** — 81 of 132 write commands with no "
          "authorization, 61 HTTP-reachable — and it is blocked outside this repo: magiq-auth "
          "issues no `roles` claim and no `actor_type` claim, so the role branch admits nobody "
          "and `ActorType` is always \"User\" over HTTP. **The ask is written and unsent** — "
          "that makes sending it the critical path, not an errand.")
review("MM-030", "reviews/event-reliability/event-reliability-review-2026-08-25.md",
       "event-reliability", "2026-08-25", "findings-agreed", "pending",
       note="reviews/README.md flags this row as one to read twice: findings agreed and being "
            "worked **with no plan**, which is the one shape the cycle does not model. It needs "
            "either a plan or a terminal outcome. X-11.6 and the X-11.5 core closed 2026-08-27; "
            "X-11.44 is decision-gated, not work-gated.")
review("MM-031", "reviews/pending-decisions/pending-decisions-review-2026-08-25.md",
       "pending-decisions", "2026-08-25", "done", "decision-only",
       note="No plan and no research left — the evidence is complete and the code understood. "
            "**Two decisions are outstanding and neither is logged in decisions/log.md** "
            "(checked 2026-08-31): X-11.21 idempotency, adopt or retire — the middleware is "
            "deployed and nothing sends the header, and the header name mismatch means clients "
            "following the contract got zero protection silently; and BI-1 — build, delete the "
            "spec, or badge it design-only with a deadline. Log both via /decision when made.")
review("MM-032", "reviews/projection-rebuild/projection-rebuild-review-2026-08-25.md",
       "projection-rebuild", "2026-08-25", "parked", "parked",
       note="Parked reason, from reviews/README.md: split out for the same reason as "
            "asset-custody — the spec-drift plan corrects documentation, this one changes code. "
            "Seven write-side reference indexes cannot be rebuilt by replaying anything, and "
            "each backs a guard, so a stale row is a wrong authorization decision. The two "
            "uniqueness counters are worse — no replay reproduces them. **Start at question 7, "
            "divergence detection, not at the rebuild tool.**")
review("MM-033", "reviews/spec-structure/spec-structure-recommendation-2026-08-25.md",
       "spec-structure", "2026-08-25", "done", "folded-into:MM-024",
       note="No plan of its own — most of it lands in MM-024's Phases 2/4a/5; four items are new.")

# --- 2026-08-27 · the two drafts, the ones missing from the board ------------
review("MM-034", "reviews/archive-cascade/archive-cascade-scale-review.md",
       "archive-cascade", "2026-08-27", "draft", "pending",
       note="Not yet planned. The cascade holds a whole subtree in memory and must finish in one "
            "invocation, so it has a hard ceiling; the X-11.16 fix made hitting it loud rather "
            "than silent. Tier 1 raised the ceiling ~100×. **Measure before building** — there "
            "is no telemetry on either path.")
review("MM-035", "reviews/event-reliability/outbox-implementation-review-2026-08-27.md",
       "event-reliability", "2026-08-27", "draft", "pending",
       note="Not yet planned; the work is almost entirely in `aspnetcore-platform`. Verdict: "
            "`Magiq.Platform.Messaging.Outbox` has never been run — zero adopters, zero tests, "
            "the drain is invoked by nothing and sent messages are never marked sent, so "
            "adopting it as-is would produce **unbounded duplicate publication** of every event. "
            "Read it before anyone treats 'adopt IOutbox' as the small option.")


def build(doc: dict) -> str:
    mm, typ = doc["id"], doc["type"]
    lines = [f"id: {mm}", f"type: {typ}", f"project: {PROJECT}",
             f"workstream: {doc['workstream']}"]
    if typ == "review":
        lines += ["raised-by: []", f"status: {doc['status']}", f"outcome: {doc['outcome']}"]
    else:
        lines += [f"consumes: [{', '.join(doc['consumes'])}]", "depends-on: []"]
        if doc.get("blocked"):
            b = doc["blocked"]
            lines += ["blocked-by-external:",
                      f"  - owner: {b['owner']}", f"    ask: {b['ask']}",
                      f"    sent: {b['sent']}", f"    since: {b['since']}"]
        else:
            lines += ["blocked-by-external: []"]
        lines += [f"status: {doc['status']}"]
    lines += [f"todo-id: {cycle.todo_id_for(PROJECT, mm)}"]
    if typ == "plan":
        lines += ["branches: []", "ado: -"]
    lines += [f"created: {doc['created']}"]
    if doc.get("exception"):
        lines += [f"exception: {doc['exception']}"]
    return "\n".join(lines)


def main(apply: bool) -> int:
    written = 0
    for doc in DOCS:
        path = ROOT / doc["rel"]
        if not path.exists():
            print(f"  MISSING {doc['rel']}")
            continue
        text = io.open(path, encoding="utf-8").read()
        if cycle.parse_front_matter(path):
            print(f"  skip (has front-matter) {doc['id']} {doc['rel']}")
            continue
        body = build(doc)
        note = f"\n> **Backfilled into the review cycle 2026-08-31 as {doc['id']}.** {doc['note']}\n" \
            if doc.get("note") else ""
        if path.suffix == ".html":
            # Same `---` fences as markdown, wrapped in a comment so the block does not
            # render on the page. parse_front_matter() requires the fences either way.
            block = f"<!--\n---\n{body}\n---\n-->\n"
            note = ""  # an HTML doc has no markdown blockquote to carry the note
        else:
            block = f"---\n{body}\n---\n{note}"
        if apply:
            io.open(path, "w", encoding="utf-8", newline="\n").write(block + "\n" + text)
        print(f"  {'wrote' if apply else 'would write'} {doc['id']:<7} {doc['type']:<6} "
              f"{doc['status']:<15} {doc['rel']}")
        written += 1
    print(f"\n{written} document(s) {'written' if apply else 'pending'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(apply="--apply" in sys.argv))
