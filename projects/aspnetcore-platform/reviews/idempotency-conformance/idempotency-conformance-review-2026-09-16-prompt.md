# Pick-up prompt — AP-001, idempotency-conformance

Paste into a fresh session. It assumes no prior context.

---

## Where you are

**Project:** `aspnetcore-platform` · slug `aspnetcore-platform`
**Project folder:** `Z:\claudia\magiq\projects\aspnetcore-platform`
**Code repo:** `D:\source\github\magiqsoftware\aspnetcore-platform`

**Document:** `AP-001`, a review
**Path:** `Z:\claudia\magiq\projects\aspnetcore-platform\reviews\idempotency-conformance\idempotency-conformance-review-2026-09-16.md`
**Todo id:** `f7899288-c1d1-58b9-b00c-6c9954c9d51e`

`AP-001` is the **first id minted in this project.** The `## Review → Plan cycle` marker was added to its
`CLAUDE.md` on 2026-09-16; `adrs/`, `plans/`, `spec/` and the decision log all predate it. Prefixes in use
across the workspace: `AP` here, `MM` magiq-media, `MA` magiq-auth.

## First action, before anything else

```bash
python -c "from tower import cycle; cycle.comment('aspnetcore-platform', 'AP-001', 'Picked up AP-001. Found: <state>. Working: <what>.')"
```

Run it from `Z:\claudia\magiq` so `tower` imports. The card's status is projected from the document's
front-matter and **cannot be set from the board** — do not try.

## Read first

1. The review itself, in full.
2. `draft-ietf-httpapi-idempotency-key-header-07` §2.2, §2.4, §2.6, §2.7 — the standard the findings measure
   against. Read it before forming a view; several findings only make sense against its three-way split of
   retry / concurrent / payload-mismatch.
3. The five source files named in § Scope.
4. `Z:\claudia\magiq\projects\aspnetcore-platform\MEMORY.md`.

## Why this exists

magiq-media's spec-baseline review (`MM-001`) ruled that its API conforms to the draft, then found the SDK
cannot express it — `IIdempotencyStore` has no response parameter and no retrieval method. **The
remediation is here, not there.** `MM-001` cannot close its SB-20 from its own repo whatever it writes in
its spec.

This is a `we-operate: true` project, so the work is tracked here as a first-class review rather than as an
external blocker on someone else's plan.

## Out of scope

- **Every other package in this SDK.** IC-7 records that the blast radius across consumers is unknown; if
  answering it means surveying other packages, that is its own piece of work — surface it, do not absorb it.
- **magiq-media's spec.** Its wording is settled by `MM-001` and is not this review's to change.
- **Fixing anything during the review.** A review argues; a plan sequences; execution follows both.

## Working the findings

- Finding ids are `IC-<n>`, already minted. **Stable — never renumber.** New findings continue the sequence.
- Severity is `Critical | High | Medium | Low`. Never 🔴/🟠 — those belong to gate documents.
- **Evidence before conclusion.** Cite `file:line`. This review rests on code, unlike its parent — so
  quote the code, and re-verify rather than trusting a line reference that may have moved.
- Anything found outside scope does **not** become an `IC-` finding. Surface it and ask where it belongs.

## The gate

**Do not write the plan until both are true:**

1. Every question in `## Open Questions` reads `**Answered:** …` — zero `**Open**` markers.
2. Chase has moved the review to `status: findings-agreed`. His call, never an inference.

Questions 2 and 3 are the ones to get right. **Q2** — is `IIdempotencyStore` a published extension point? —
decides whether changing the interface breaks consumers or is free. **Q3** — route-scoping versus payload
fingerprinting — is one decision covering two findings, and answering it twice will produce a contradictory
contract.

## Writing the plan

When the gate opens, write
`Z:\claudia\magiq\projects\aspnetcore-platform\plans\idempotency-conformance\idempotency-conformance-review-2026-09-16.md`
— the plan takes the review's filename. Front-matter: a freshly minted `AP-` id, `type: plan`,
`consumes: [AP-001]`, `depends-on: []`, `status: active`, `todo-id` from
`cycle.todo_id_for('aspnetcore-platform', '<new-id>')`, `branches: []`, `ado: -`.

A phase is a `## Phase <N> — <name>` heading, then `- [ ]` items small enough for one session, each naming
the `IC-` finding it closes and its acceptance check. The heading shape is parsed by tooling — keep it.

**Two things this plan must carry that a documents-only plan would not:**

- **Acceptance checks are tests, not greps.** "`MarkAsync` is not called when the pipeline returns `500`"
  is a test. Every behaviour change in IC-3, IC-4 and IC-5 needs one, because the failure modes are all
  "the wrong thing happened silently".
- **A release phase, stated explicitly.** This SDK is consumed as NuGet, not by project reference.
  Merging is not shipping: the packages must be published and `$(MagiqPlatformVersion)` bumped in the
  consumer before anything is done. magiq-media's `todos.md` records that the chain is awkward — ten
  packages pull `Magiq.Platform.Core` transitively with `CentralPackageTransitivePinningEnabled` set
  `false`, so publishing one package alone changes nothing downstream. Do not leave this implicit.

## Cross-project bookkeeping

`MM-001` names `AP-001` in its `## Dependencies`. When **this** review produces a plan, tell whoever is
working `MM-001` so its plan's `depends-on` points at the plan id rather than the review id — a review that
has produced no plan resolves as an **unmet** dependency, which is correct but blocks their phase 5.

Comment this card whenever that relationship changes. The other side cannot see your front-matter.

## Every session

Tick the checklist as work lands. Update front-matter `status` in the same edit that changes what is true —
there is no board update, only the file. Append each branch to `branches`. Close with a card comment saying
what moved, what did not, and the next concrete action.
