# Aggregate design review — paste-ready session prompt

You are opening a new review in the `magiq-media` project. This prompt assumes you have **no context from
any previous session**. Everything you need is below or at the paths it names.

**What you are being asked to do:** interrogate the design of every aggregate and every relationship
between them, and answer three questions about each — *is it documented, is it sound, is it robust?* This is
a **records management and media management platform**, and the design has to hold up as one, not merely as
a well-formed DDD model.

> ## 📘 This is a spec-only review. Do not read the repo code.
>
> **A pure domain design check**, by instruction. The spec tree and the ADRs are the entire evidence base.
> You are reviewing **the model as designed** — not what is built, not how far the code has got, not whether
> the two agree.
>
> **What that means in practice:**
>
> - **Read `docs/spec/` and `docs/adrs/`. Read nothing under `src/` or `tests/`,** and do not open the CDK
>   or platform-SDK repos.
> - **Never write "this is not implemented", "the code does X", or "this is unbuilt."** You have not looked
>   and you cannot know. Where the spec itself flags something as unbuilt, you may quote that as a fact
>   *about the spec*, not as a verified fact about the system.
> - **Every finding is a statement about the design or its documentation.** Nothing here is a bug report.
> - **A spec that is silent is a finding.** In a code-reading review, silence gets resolved by looking; here
>   it is exactly what you are hunting. An unstated rule is an undesigned rule.
>
> **What this review consequently cannot do, stated so nobody mistakes its output:** it cannot tell you
> whether a finding is already handled in code, and it cannot catch a defect the spec is silent about but
> the code has. That is the accepted trade for a clean design check. **Say so in the review's opening
> section** — a previous spec-only review in this project (MM-040) was read later as a statement about the
> running system, and its sizings were wrong because of it.

---

## Where you are

| | |
|---|---|
| Project slug | `magiq-media` |
| Project folder | `Z:\claudia\magiq\projects\magiq-media` |
| **Spec and ADRs** | `D:\source\github\sprbrk-standard\mgq-magiq-media\docs\` — **the only thing you read** |
| Workstream slug | `aggregate-design` |
| Review file | `reviews/aggregate-design/aggregate-design-review-2026-09-14.md` |
| Finding id prefix | `AD-` |
| Document id | **Mint the next free `MM-` id** via the `review-cycle` skill. MM-041 was the highest as of 2026-09-14; do not assume MM-042 is free |

**The spec lives at `mgq-magiq-media\docs\spec\` and the ADRs at `docs\adrs\`. That repo is the only copy —
nothing is published or mirrored**, so anything you write reaches readers only through a PR there.

The same repo holds `src/` and `tests/`, and two sibling repos hold the CDK and the platform SDK. **All of
that is out of bounds for this review.**

## First actions, before anything else

1. Create the review through the `review-cycle` skill so it gets an id, front-matter and a board card.
   `status: draft`, `type: review`, `workstream: aggregate-design`.
2. Write a card comment recording what you are picking up:

   ```bash
   python -c "from tower import cycle; cycle.comment('magiq-media', '<your id>', 'Opening the aggregate design review; starting Pass <N>')"
   ```

   Run it from the AIS-OS repo root (`Z:\claudia\magiq`). A card's status is **projected from front-matter
   and cannot be set from the board** — a `PATCH` returns 409. The only way a status changes is you writing
   it into front-matter.

## What to read first, in this order

1. `D:\source\github\sprbrk-standard\mgq-magiq-media\CLAUDE.md` — stack, conventions, module and host
   layout. **Read it before forming any opinion**; several plausible-sounding assumptions about this
   codebase are wrong and it says which. *(This one file, not the tree it describes.)*
2. `docs/spec/README.md` — the question map, and the entry point to the spec tree.
3. `docs/spec/architecture/domain-model.md` — the aggregate inventory and the one-aggregate-per-transaction
   rule the cross-aggregate machinery exists to work around.
4. `docs/spec/shared/cross-aggregate-invariants.md` — **the single most important file for this review.**
   Every rule that spans two aggregates, and what actually enforces each.
5. `docs/spec/shared/consistency-model.md` — the lag path, environment divergence, and § What replay cannot
   rebuild.
6. `docs/spec/shared/cascade-rules.md`, `saga-patterns.md`, `concurrency-and-consistency.md`.
7. Then, per pass, the aggregate's own four files: `*.write-model.md`, `*.read-model.md`, `*.api.md`,
   `*.scenarios.md`, plus its `context-overview.md`.

---

## Scope

**In scope — every aggregate and every relationship between them:**

| Context | Aggregates |
|---|---|
| `Catalog` | `Collection`, `Folder`, `MediaItem`, `MediaProfile` |
| `AssetManagement` | `Asset` |
| `Metadata` | `RecordType`, `RetentionSchedule` *(designed, wholly unbuilt)* |
| `Registration` | `Registration` |
| `ChangeRequests` | `ChangeRequest` |
| `Processing` | `ProcessingJob` |
| `DocumentSigning` | `DocumentSigningSession` *(specified; no aggregate class exists)* |

Also in scope, because they *are* the relationships: sagas and process managers, write-side reference
models and counters, integration-event contracts and their consumers, the read-model projections where they
carry a design claim, and every seam where an invariant crosses a context boundary.

**Out of scope, by instruction:**

- 🚫 **The repo code.** `src/`, `tests/`, the CDK repo and the platform SDK. See the notice at the top — this
  is a design check, and spec↔code drift is a different review with a different method. That drift already
  has an owner: **MM-022**, 48 open findings.
- 🚫 **Authentication and authorization.** No claims, roles, actor types, ownership checks, edge gating or
  permission questions. If a finding's only substance is "this is unguarded", it belongs to the
  `authorization/` workstream (MM-029) and you leave it alone. *This exclusion is narrow: if an aggregate's
  **design** is wrong in a way that happens to have an authz consequence, review the design and say nothing
  about the guard.*
- 🚫 **Deploy mechanics, CDK structure, CI, infrastructure.**

---

## What this review is for — the three lenses

Apply all three to everything. They find different things and a document can pass one and fail another.

**1 · Is it documented?** Does the spec state the design, or does it state a shape and leave the reader to
infer the rules? Specifically: are invariants enumerated with what enforces each; is every published event's
consumer stated; is every consumed event's effect stated; are the terminal states and the transitions
between them complete; is what is *deliberately not supported* written down as a position rather than
absent.

**2 · Is the design sound?** Is each aggregate a genuine consistency boundary — everything inside it
invariant-true at commit, nothing outside it needed to decide? Is it the right *size*? Are the relationships
modelled at the right strength — reference by id, replicated fact, synchronous read, or event? Does any
invariant span a boundary it cannot span? Does the model say what the domain means, or what was convenient
to build?

**3 · Is the design robust?** Not *"is it production ready"* — that is a question about a running system and
you are not looking at one. The design question is: **does the model, as specified, survive the first bad
day?** Take each failure and ask what the *design* says happens — a redelivered message, a projector that
lags or gaps, two concurrent writers, a tenant with 100,000 items, a publish that fails after the write
committed, a cascade that dies halfway.

The test is whether the spec **has an answer**. Three outcomes, and they are different findings:

- It states the behaviour and the behaviour is right → nothing to raise.
- It states the behaviour and the behaviour is wrong → a design finding.
- **It does not say** → the most common and most valuable finding in this review. An unhandled failure is
  not a gap in the code, it is a gap in the model.

`plans/prod-readiness/prod-readiness-gate.md` triages which known findings block the release flags — **read
it so you do not duplicate it**, and note that it reasons about built code, which you are not.

---

## The domain lens — this is a records management system

**This is the half a conventional DDD review misses, and it is the half that matters most here.** The
platform serves government agencies and large enterprises managing **regulated records**. A model that is
clean DDD and wrong about recordkeeping is wrong.

Interrogate the aggregate set against the records lifecycle end to end — **capture → declaration →
classification → governance → retention → disposition** — and ask, for each stage, *which aggregate owns
this, and can it actually answer?*

Specific questions to put to the model:

**Fixity and declaration.** When does a thing stop being a working document and become a *record*? A record
is fixed: once declared, its content must not change. Does the model distinguish the two states, or is a
published `MediaItem` still mutable in ways that matter? Trace what can still change after publication —
assets in roles, metadata, folder assignment, title — and say whether each is defensible. **A records
system that cannot say "this is the thing that was filed, unaltered" has a foundational problem.**

**Classification.** `Collection` → `Folder` → `MediaItem` is the classification scheme, and `Folder` is the
*file*. Does the hierarchy carry the semantics a file plan needs — closure, aggregation, inheritance of
retention, the relationship between a file's disposition and its contents'? What happens to a record moved
between files, and does its governance move with it?

**Provenance and audit.** Event sourcing gives an audit trail by construction — but is it *complete* and is
it *truthful*? Look for places where the trail is lossy by design, where a corrective act is indistinguishable
from an original one, or where a record's history can be edited after the fact.

**Retention and disposition.** `RetentionSchedule` is designed and entirely unbuilt; the design is explicit
that **no engine computes a due date, evaluates a trigger, or runs a disposal review**, and that a schedule
is *"a record of intent, not an instruction"*. Take that at face value and review what it implies: is the
*aggregate* design right for when an engine does arrive, and does anything in the current model foreclose
it? **Legal hold** is named as Registration-only and connected to nothing in Catalog — interrogate that
seam; a hold that cannot stop a disposal or an archive is not a hold.

**Governance.** `ChangeRequest` is the governance container — a documented reason-for-change, a participant
list, a comment thread, a lifecycle. Does the model make governance *enforceable* rather than merely
*recorded*? Where a policy field exists on a profile and is pinned into immutable versions, does anything
read it?

**Versioning.** What *is* a version of a record — a revision of the same record, or a new record superseding
it? The answer drives retention, citation, disposition and supersession, and the model should commit to one.
Examine `MediaItemVersion`, `VersionArtifact`, `PurgeVersion` and the version reference index against that
question. **`PurgeVersion` destroys something in a regulated context — what governs it?**

**Check-in / check-out, one *or more* users.** This is an explicit requirement and it is where the model is
thinnest. `EditSession` carries membership and a lease; `MediaProfile.CheckoutPolicy` decides whether edits
are serialised and `ChangeRequestPolicy` whether they are justified. Interrogate:

- **Coverage** — does the lock cover *everything* that changes the item? Partial coverage means a locked-out
  caller can still mutate the record by another route.
- **The collaborative half** — multi-editor sessions are specified; check what of it exists (see MM-021,
  which found 5 of 7 commands built and the two membership commands missing). A design for *one or more*
  users that only supports one is a documented capability the product does not have.
- **Lease expiry** — what happens to in-flight work when a lease lapses? Is the answer stated, and is it
  the right answer for a records system where the edit may be hours of professional work?
- **Concurrency** — optimistic concurrency with conditional writes and retry is the platform mechanism. Where
  is it *not* applied, and what does a lost update cost there?
- **Conflict** — when two members of a session write, what reconciles them?

---

## The pass order

**Take the passes in this order and do not skip ahead.** The relationship passes depend on having the
per-aggregate invariants in hand, and the records lens depends on both.

| Pass | Subject | Why here |
|---|---|---|
| **0** | **Orientation and the map.** Build the inventory: every aggregate, its invariants, its events, its terminal states, and every cross-aggregate rule with what enforces it. Produce no findings — produce the table the rest of the review argues against | Everything after this is cheaper and sharper for having it |
| **1** | **`MediaItem`** — alone, because it is the centre of the model and by far the largest | If its boundary is wrong, several later findings are consequences rather than causes |
| **2** | **`Collection`, `Folder`** — the hierarchy and the file plan | |
| **3** | **`MediaProfile`, `RecordType`, `RetentionSchedule`** — the schema and governance vocabulary | These three are one seam; reviewing them apart is how the existing defects there survived |
| **4** | **`Asset`, `ProcessingJob`** — content and its processing | |
| **5** | **`Registration`, `ChangeRequest`, `DocumentSigningSession`** — the lifecycle satellites | |
| **6** | **The relationships.** Every cross-context seam: reference models, counters, integration contracts, sagas and process managers, the cascade rules | The main event. Prior experience in this codebase says **this is where the defects are** |
| **7** | **The records lens, end to end.** Walk the full lifecycle across aggregates and ask what the *system* cannot answer | Findings here are usually about absent concepts, not wrong ones — and they are the most valuable |
| **8** | **Robustness of the design.** Failure modes, scale, rebuild and repair, idempotency, and whether the model is observable enough to operate — all as specified, not as built | |
| **9** | **Coherence.** Read every finding together and resolve them against each other. **Loop until stable** — see § The coherence rule | Findings raised eight passes apart interact, and nothing before this point forces them to meet |

**Keep a wave log in the review file** — one row per pass with date, what was covered and what was found —
so the next session resumes from the file rather than from chat history. Expect roughly one pass per
session; say so in the log if a pass is partial.

---

## The coherence rule

**Findings are not independent, and a review that only accumulates them is wrong by the end.** This is the
failure mode this section exists to prevent: nine passes, each internally sound, producing a set that
contradicts itself and recommends two incompatible directions in different sections.

### At the end of every pass

Before you close a pass, re-read the findings you already hold and ask three questions:

1. **Does anything I just found invalidate an earlier finding?** If the model turns out to work differently
   than Pass 2 assumed, Pass 2's finding may be wrong, or may be a *consequence* of a deeper one rather
   than a cause. **Amend it in place** — do not leave a superseded finding standing and add a corrected one
   beside it. Note the amendment in the wave log so the change is visible.
2. **Is this the same finding I already raised, wearing different clothes?** Two aggregates exhibiting one
   design fault is **one finding with two instances**, not two findings. Merging them is what makes the
   remedy converge; leaving them apart is how four faces of one problem end up fixed separately and not
   converging. *(This project has exactly that case on file — see DF-8/9/14/15.)*
3. **Did this pass depend on something I assumed rather than read?** If so, go and read it now, while the
   pass is still open.

Keep finding ids stable through all of this: an amended `AD-7` stays `AD-7`, and a split keeps the original
number on both halves.

### Pass 9 — the convergence loop

Read the whole finding set together and run it to a fixed point:

1. **Contradiction sweep.** Does any finding assert something another denies? Does any two-finding pair
   imply a third thing you never checked?
2. **Direction conflict sweep.** For every finding, ask what fixing it would take — then ask whether that
   direction **breaks another finding's direction.** This is the check that matters most and the one nobody
   does by accident. Worked example from this project: one decision rejected *"a write-side invariant
   enforced against a projection"*; a later, unrelated decision's obvious remedy was a new reverse-lookup
   projection carrying exactly such an invariant. Sound in isolation, incoherent together — and only
   visible because both were held at once.
3. **Root-cause collapse.** Where several findings share a cause, say so and rank the cause above the
   symptoms. A review whose top finding is a symptom sends the plan to the wrong place.
4. **Re-run.** Resolving any of the above can surface a new contradiction. **Loop until a pass produces no
   changes.** If it will not settle after three rounds, stop: that is itself the finding, and it usually
   means two irreconcilable models of the same thing are in the tree. Say so and raise it as **Open**.

**Record the loop in the wave log** — how many rounds, what changed in each. A Pass 9 that reports no
changes on the first round has almost certainly not been done.

---

## What to interrogate — the question bank

Use these as prompts, not a checklist to tick. A pass that answers ten of them well beats one that mentions
all of them.

**Aggregate boundary and size**
- What invariant justifies this boundary? If none does, why is it an aggregate rather than an entity or a
  value object on another?
- Is anything inside the boundary that does not need to be transactionally consistent with the rest? Large
  aggregates are usually several aggregates that were never separated.
- Is any invariant *stated* on this aggregate that it cannot enforce from its own state?
- Does the aggregate load a second aggregate to make a decision? That is a boundary failure wearing a
  handler's clothes.

**Lifecycle and state**
- Is the status machine complete — every state reachable, every terminal state genuinely terminal?
- **Does any terminal state still accept mutating commands?** Does any state have no successor where the
  domain plainly needs one?
- Is the irreversible act ordered *after* the decision that permits it, or before?
- Are enums pinned into persisted events or read-model rows? **Several here are persisted numerically, so
  member order is a stored contract** — check every one for whether that constraint is documented where a
  future developer will look.

**Relationships**
- For each relationship: reference by id, replicated fact, synchronous read, or event? Is the strength
  justified, and is it the *same* in both directions?
- Is any write-side invariant enforced against an eventually-consistent projection? The spec states in
  several places that this is wrong; check whether practice follows.
- Is derived cross-aggregate state written once and never reconciled? For each such value: what moves it,
  what *should* move it, and can it be rebuilt?
- **Does every published event have a stated consumer, and every consumer a producer that exists?**

**Consistency and failure**
- What is the idempotency mechanism — a dedup key, or a status guard? A status guard whose success leaves
  the status unchanged does not guard against redelivery.
- Publication is inline after commit, with no outbox. What is permanently wrong if the publish fails?
- What compensates a cross-context operation that half-succeeds? If nothing does, is that stated?
- Under concurrent writers, what is lost?

**Process managers and sagas**
- Which coordinating code is a saga with state, a correlation key, timeouts and a resume path — and which is
  a worker doing saga work without any of it?
- Can every long-running process be observed, resumed and re-triggered? If a cascade fails halfway, what
  does an operator do?

**Multi-tenancy**
- `TenantId` first field, set once, immutable; DynamoDB PK on every table; sourced from the token or the
  message envelope and **never** from a payload body. Where is that not true, and what leaks?

---

## Known failure shapes in this codebase — prior art

**Do not rediscover these. Do check whether they recur where nobody has looked.** A previous review
(MM-040) traced every lifecycle end to end and found the failures clustered into four shapes:

1. **Derived cross-aggregate state, written once, never reconciled** — and per the consistency model, **not
   rebuildable**. Divergence is permanent by construction rather than eventually consistent.
2. **Write-side invariants enforced against read-side projections**, in a spec that states the correct rule
   twice and then breaks it in four places.
3. **Terminal states reached before the irreversible act, or without the compensating one.**
4. **Events published with no consumer, and consumers with no producer** — where the *missing* consumer is
   what makes a happy path corrupt state.

Two standing hazards. **You cannot check either from the spec — that is the point of including them.** They
tell you how expensive an under-specified relationship is here, and therefore how hard to push on one:

- **The consumer allowlist is hand-maintained.** Two lists — the app's consumer registrations and the CDK's
  message-type entries — with nothing enforcing the match (**X-4.15**). A handler missing from the allowlist
  **silently never delivers**: no error, no dead letter, no failed subscription. This has caused at least
  three real defects. **The design consequence is what concerns you:** when the spec does not enumerate a
  relationship's full event set and each event's effect, there is no other line of defence. A vague
  integration table is not a documentation problem here, it is the only safety net.
- **Projections are synchronous in dev, qa and staging, and asynchronous only in production.** So every
  ordering and staleness defect is invisible on every tier a developer can reach. **The design consequence:**
  correctness under async delivery has to be *argued in the spec*, because nothing downstream will discover
  it. Where the spec assumes ordering, assumes a read-your-own-write, or is silent about redelivery, raise
  it — nobody is going to trip over it in testing.

---

## Already owned — do not re-raise as new

Check each against source before citing it, but these have homes and a duplicate finding costs someone a
triage:

| Area | Owner |
|---|---|
| **DF-1 … DF-4** — the registration obligation counter, the Registration reference model's missing events, the `RequiredForEdit` gate, the retention capability migration | **MM-041, closed `done` 2026-09-14.** The spec you are reading already carries the corrected design for all four, landed days ago. **Do not re-argue them.** Do flag anything the *corrected* design gets wrong — it is the newest text in the tree and the least reviewed |
| DF-5, DF-6 — derived state with no reconciler | MM-032 `projection-rebuild/`, parked |
| DF-7 — the archive cascade's two contracts | MM-025 / MM-026 `archive-cascade/` |
| DF-8, DF-9, DF-14, DF-15 — **the pinned-vocabulary seam** | **No owner.** Four faces of one problem, argued not to converge if fixed separately. **In scope for this review to re-argue as a whole** if Pass 3 reaches it |
| DF-11, DF-16 — idempotency, orphan contracts | MM-030 / MM-035 `event-reliability/` |
| DF-12 — signing mutual exclusion | MM-038 `document-signing/`, parked |
| Outbox absence | X-11.44 / MM-035, decision-gated |
| 48 open spec↔repo drift findings | MM-022 `spec-drift-review/` |

**`MediaItemReviewSaga` was deliberately removed on 2026-06-02 and is not coming back.** Approval is an
aggregate invariant on `MediaItem` via an embedded `ReviewSession`, which is the point. Read
`docs/spec/shared/saga-patterns.md` § *The review saga was built and then removed* **before proposing
anything shaped like it**.

---

## How to work findings

- **Evidence before conclusion.** State what the file says, then what follows from it. Quote it.
- **Cite `file:line` for every claim.** Where two files disagree, cite both — **that disagreement is the
  richest seam in a spec-only review.** Two documents describing the same rule differently is a design
  defect you can prove without reading a line of code, and this tree has form for it.
- **Your evidence is the spec, and every finding inherits that.** Do not hedge each one individually; put
  the declaration once, at the top of the review — *"Spec only. No code was read."* — and let every finding
  stand on the documents it cites.
- **Silence is evidence.** If a rule is not stated, the finding is that it is not stated. Do not write
  "presumably the code handles this" — that sentence is the whole problem, and it is how an undesigned rule
  survives a review.
- **A finding is a defect in the design or its documentation, not a preference.** "I would have modelled
  this differently" is not a finding. "This invariant cannot hold because X" is. In a design review the
  temptation to redesign is strong — resist it: say what is wrong and why it matters, and leave what to do
  instead to the plan.
- **Severity is `High` / `Medium` / `Low`.** Never 🔴/🟠/🟡 — those belong to `type: gate` documents only,
  where they mean "blocks the release flag flip". A High finding is not automatically a gate blocker;
  `prod-readiness-gate.md` makes that call and a review must not pre-empt it.
- **Number findings `AD-1`, `AD-2`, …** in the order raised, and keep the number stable if the finding is
  later split or amended. **Findings are living until Pass 9 closes** — amend, merge and supersede them as
  later passes teach you more, rather than letting a set of snapshots accumulate. See § The coherence rule.
- **Do not fix anything.** A review argues; a plan sequences. No spec edits, no code edits, no "while I was
  there" corrections — including obvious ones. Record them as findings.

## Anything you find outside scope

It does **not** become a finding here. Surface it and ask where it belongs — the global drift register (an
`X-` number in MM-022) or a new review in the right workstream. Record the diversion in the wave log.

If something you find **invalidates this review's framing** — for example, if the spec turns out to describe
two incompatible models of the same aggregate, so that "the design" is not a single thing to review —
**stop and say so** rather than re-scoping in place. Chase decides whether the scope changes.

**If a question can only be settled by reading code, that is a finding, not a reason to read the code.**
Write it as *"the spec does not settle X"* and, where it matters enough, raise it as an **Open** question.
Resist the pull — a design check that starts checking implementations stops being a design check.

---

## Deliverable

`reviews/aggregate-design/aggregate-design-review-2026-09-14.md`, with front-matter from the `review-cycle`
skill and this shape:

0. **The evidence declaration**, before anything else: *"Spec only. No code was read. Every claim cites the
   spec file that makes it, and where two spec files disagree, both are cited."* Then the one sentence that
   stops it being misread: **this review says nothing about what is built, and a finding here is not a
   statement that the system misbehaves.**
1. **The verdict, up front.** What is actually wrong with this model, in a few sentences, ranked. Write this
   last and put it first.
2. **The map** from Pass 0 — the aggregate and relationship inventory the rest argues against.
3. **The findings**, `AD-n`, ranked by severity, each with: what the spec says (quoted, cited), what
   follows from it, and what it costs in a regulated-records context. Where the finding is that the spec
   says *nothing*, say so plainly and name the file where the rule should have been.
4. **The records-management verdict** — a section of its own. Can this system do records management, and
   where does it fall short of what an agency would expect?
5. **Open questions for Chase** — decisions the review cannot take. Mark each **Open**.
6. **Recommended sequencing** — what to fix first and why, with what genuinely groups together.

   **Every recommended direction must be stated as a direction, and tested against the others.** For each,
   say in one line what fixing it implies for the rest of the model, and name any finding whose own remedy
   it constrains or rules out. **Where two remedies conflict, say so rather than picking silently** — that
   conflict is a decision for Chase, and burying it produces a plan that discovers the problem halfway
   through implementation.

   Group by **what has to move together**, not by severity. Two findings with one cause, or two whose
   remedies touch the same invariant, are one unit of work however differently they are ranked.

7. **The coherence record** — the Pass 9 loop: how many rounds, what each changed, what was merged into
   what, and anything that would not settle.
8. **The wave log.**

Then update `reviews/README.md` to index the new workstream. **A folder nobody indexed is a folder the next
session won't find.**

## The gate

**No plan may be opened from this review until every `**Open**` question is answered *and Chase has moved
the review to `findings-agreed`*.** That transition is Chase's to make and is never inferred, however few
questions remain.

## ADO

`ado:` stays `-`. Pushing work to the board is a separate, explicit step run through `ado-create-from-plan`
once a plan exists and is `active` — never during a review. **Do not create ADO items.**

## End-of-session protocol

Non-negotiable, every session, including one that achieves nothing:

1. Update the wave log and the findings in the review file.
2. Update front-matter `status:` in the same edit as whatever made it true. The file is the only writer.
3. Write the closing card comment — what moved, what did not, and **the next concrete action**:

   ```bash
   python -c "from tower import cycle; cycle.comment('magiq-media', '<your id>', '<what moved, what did not, next concrete action>')"
   ```

   Lead with the outcome, not the activity. Name finding and document ids so entries are greppable. Two or
   three sentences. The timestamp and author are recorded for you — do not write the date, and do not log
   individual file edits; the card is a log of decisions and outcomes, not a transcript.
