# Session prompt — MA-001 · ValidateUser lockout

Paste this into a fresh session. It assumes no prior context.

---

## Where you are

- **Project slug:** `magiq-auth`
- **Planning workspace:** `Z:\claudia\magiq\projects\magiq-auth` — reviews, plans, decisions. No source code.
- **Code repo:** `D:\source\github\magiq-auth` — all C# source, tests, scripts, audit reports.
- **Review document id:** `MA-001`
- **Review path:** `Z:\claudia\magiq\projects\magiq-auth\reviews\validateuser-lockout\validateuser-lockout-review-2026-08-28.md`
- **Todo id:** `6f75a44e-360f-4565-b6bb-66af3f128ef6` in `tower/data/todos/magiq-auth.json`
- **Workstream slug:** `validateuser-lockout` — used identically for the review folder, the plan folder and both todos.

## First action, before anything else

Set the todo above to `in-progress` via the `project-todos` skill, with an `append_activity` comment
noting the session started and what you intend to work. Re-read the store immediately before the write —
the Control Tower UI writes the same file and last write wins.

## Read first

1. The review at the path above — front-matter, then all ten findings.
2. `D:\source\github\magiq-auth\reports\ValidateUser-Lockout-Review.md` — the source analysis. Its
   §§3–5, 7, 8 are the **proposed design, test plan and rollout notes**. They were deliberately left out
   of the review and are the raw material for the plan.
3. `src/MagiqAuth.Services/Users/UserMembershipService.cs` — the `ValidateUser` lockout branch, lines
   ~85–110. Everything starts here.
4. `Z:\claudia\magiq\projects\magiq-auth\CLAUDE.md` — in particular § "Stack: Current vs. Future
   Migration Target".

## Scope

**In scope:** the lockout behaviour of `UserMembershipService.ValidateUser`, its six call sites, and the
password-reset path that a locked user cannot currently reach.

**Out of scope — do not widen into these:**

- The Openiddict / FastEndpoints / DynamoDB / Lambda migration target. Those solution folders are empty
  scaffolding. **This work is entirely on the current deployed system**: ASP.NET Core .NET 8,
  IdentityServer4 4.1.2, MySQL via Pomelo EF Core, Autofac, Redis/Valkey, EC2.
- Password policy, hashing, `GetCurrentPassword` correctness.
- The Azure AD / external-IdP login path — federated logins never reach `ValidateUser`.
- IS4 client and grant configuration beyond `UserStore.ValidateCredentials`.

**Hotfix constraint, carried from the source report:** no interface signature changes, no enum renames,
no controller response-shape changes, no DB schema migration. Design within it. If a finding cannot be
addressed inside that constraint, say so plainly rather than quietly relaxing it.

## How to work

- **Finding id prefix is `VUL-`.** VUL-1 to VUL-10 exist and are stable. Never renumber them; plans cite
  them by id.
- **Severity is High / Medium / Low.** Never 🔴 / 🟠 — those belong to gate documents only, and this
  project has no gate.
- **Evidence before conclusion.** Cite `file:line` for every claim. Read the code; do not infer
  behaviour from the review's summary of it.
- **Do not fix code during a review.** No edits to the code repo in a review session.
- **Anything you find outside the scope above does not go into MA-001's findings.** Surface it and ask
  where it belongs — a new review in another workstream, or an entry on
  `PRODUCTION_CODE_AUDIT_REPORT.md`. Do not append it here.

## The gate

**Do not write the plan until both are true:**

1. Every question in `## Open Questions` is marked `**Answered:** …` — zero `**Open**` markers remain.
   There are seven open right now.
2. Chase has moved the review to `status: findings-agreed`. **This is Chase's call, not an inference.**
   However few questions remain, the gate stays shut until he says the findings are agreed.

Work the open questions in this session. OQ 1 (Valkey multi-key), OQ 4 (NAT and per-IP thresholds) and
OQ 5 (client IP behind the LB / IS4 pipeline) are the ones most likely to change the design, so start
there. OQ 2, 3 and 7 are ownership and sequencing calls for Chase.

## Writing the plan

Once the gate opens:

**Path:** `Z:\claudia\magiq\projects\magiq-auth\plans\validateuser-lockout\validateuser-lockout-review-2026-08-28.md`
— the plan is named after its primary review, same filename, different tree.

**Front-matter** — mint a fresh id. Grep `^id: MA-[0-9]{3}` across `reviews/` and `plans/` including
every `Archive/`, take the highest and add one. Likely `MA-002`, but verify rather than assume. Write
the real id into the block below in place of the placeholder:

```yaml
---
id: MA-<next>
type: plan
project: magiq-auth
workstream: validateuser-lockout
consumes: [MA-001]
depends-on: []
blocked-by-external: []
status: active
todo-id: <uuid of the new plan todo>
branches: []
ado: -
created: <today, from the session environment — never from memory>
---
```

**Body:** phases, each a checklist of `- [ ]` items small enough to finish in one session. Every item
names the finding id it closes and its acceptance check. Follow the review's `## Recommended sequencing`
unless the answered open questions have changed it — and say so if they have. Lift the design detail
from §§3–5 of the source report into the phases rather than restating it loosely; lift §7 into the
acceptance checks and §8 into a rollout phase.

Mark any phase blocked by a dependency as blocked in the body, and do not block the whole plan when only
some phases are affected.

**Include a `## Closing out` section** stating that the plan todo moves to `done` only after Chase agrees
the work is implemented and complete, that the close-out comment records every branch it was committed
to, and that review and plan are then archived together in the same session.

**Then close the review:** MA-001 front-matter → `status: done`, `outcome: plan`. Review todo → `done`
with a comment naming the plan's id and path. Create the plan todo (tags `[<the plan id>, plan,
validateuser-lockout]`, priority `urgent`, source = plan path). Update both READMEs.

**Hand-over is complete only when all of that has happened. Report it explicitly before any execution
begins.**

## During execution

- Tick checkboxes in the file as work lands, so the next session resumes from the file rather than from
  chat history.
- Append every branch you cut to `branches` in the plan's front-matter.
- **A new problem found while executing never becomes a new checklist item in this plan.** It goes to a
  new review, or to `PRODUCTION_CODE_AUDIT_REPORT.md`. Ask which. Record the diversion in the plan's
  session log.
- If something found mid-execution invalidates the plan's approach, **stop**. Do not re-plan in place —
  say so, and Chase decides whether MA-001 reopens or a new review starts.

## End of every session

1. Update the plan checklist.
2. Update front-matter `status` on whichever document moved.
3. Append any new branch to `branches`.
4. Comment the todo with what actually moved — every status change gets a comment saying why.

If front-matter and the todo store disagree, **the file is authoritative.** Reconcile to the file and say
that you did.
