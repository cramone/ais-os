# Reviews — magiq-media

_Reorganised 2026-08-24 to mirror `plans/`, one subfolder per workstream. Nothing was rewritten; only
locations changed, plus the references that pointed at the old paths._

**A review is where work starts.** Findings get argued here; sequencing, PR shaping and execution
tracking happen in the matching `plans/` folder. The folder name is shared between the two trees, so a
review and the plan that consumes it stay traceable — including after both are archived. See
`CLAUDE.md § Review → Plan` for the convention in full.

**Status vocabulary** — the full set, matching the `review-cycle` skill's front-matter. Nothing outside
this list: _Draft_ — written, findings not yet agreed · _Active_ — findings agreed, being worked ·
_Parked_ — real but deliberately not being worked · _Superseded_ — withdrawn or overtaken, kept for
reasoning · _Done_ — closed out with a terminal outcome.

**Outcome** is how a review ended, and every review needs one eventually: _plan_ · _parked_ ·
_decision-only_ · _folded-into_ · _withdrawn_. _pending_ means it has not ended yet — it is a state to
leave, not to rest in.

| Id | Workstream | Review | Status | Outcome | Its plan |
|---|---|---|---|---|---|
| MM-003 | `projection-tables/` | `projection-tables-review-2026-08-31.md` | Done | plan | MM-002 — **Parked** on Phase B only; Phase A shipped |
| MM-005 | `deployment-naming/` | `deployment-naming-review-2026-08-31.md` | Done | plan | MM-004 — **Done** 2026-09-01; DN-1 (the ADR) and DN-4 (stale build output) both closed |
| MM-007…MM-017 | `architecture-review-remediation/` | 11 module + cross-cutting reviews, read as one body | Done | plan | `plans/architecture-review-remediation/` |
| MM-023 | `spec-drift-review/` | `spec-ddd-coverage-review-2026-08-24.md` | Done | plan | `plans/spec-drift-review/` — same filename |
| MM-033 | `spec-structure/` | `spec-structure-recommendation-2026-08-25.md` | Done | folded-into: MM-024 | *(no plan of its own — most of it lands in the DDD plan's Phases 2/4a/5)* |
| MM-020 | `design/` | `mediaitem-edit-lifecycle-as-is-vs-recommended.html` | Done | plan | `plans/design/mediaitem-edit-session-design.html` |
| MM-027 | `asset-custody/` | `asset-custody-review-2026-08-25.md` | **Parked** | parked | *(none — parked 2026-08-25, not started; blocked by X-11.32)* |
| MM-032 | `projection-rebuild/` | `projection-rebuild-review-2026-08-25.md` | **Parked** | parked | *(none — parked 2026-08-25, not started)* |
| MM-031 | `pending-decisions/` | `pending-decisions-review-2026-08-25.md` | Done | decision-only | *(none — decisions, not work; evidence is complete)* |
| MM-028 | `authorization/` | `authorization-review-2026-08-25.md` | Done | plan | MM-029 — **Active (blocked)**, X-11.30 waiting on `magiq-auth`; the ask is written and unsent |
| MM-025 | `archive-cascade/` | `archive-cascade-review-2026-08-25.md` | Done | plan | MM-026 — **Active**, X-11.41 next |
| MM-034 | `archive-cascade/` | `archive-cascade-scale-review.md` | **Draft** | pending | *(not yet planned — measure before building; no telemetry on either path)* |
| MM-030 | `event-reliability/` | `event-reliability-review-2026-08-25.md` | **Active** | pending | *(no plan — being worked directly; X-11.6 and X-11.5 core closed, X-11.44 decision-gated)* |
| MM-035 | `event-reliability/` | `outbox-implementation-review-2026-08-27.md` | **Draft** | pending | *(not yet planned — the work is almost entirely in `aspnetcore-platform`)* |
| — | `Archive/` | 4 reviews — 3 consumed, plus `request-response-review.md` moved here 2026-08-31 | Done | plan | `plans/Archive/` |

Two rows need reading twice. **`event-reliability/`'s parent review is `Active` with outcome `pending`** —
findings agreed and being worked without a plan, which is the one shape the cycle does not model. It
either gets a plan or a terminal outcome; leaving it here indefinitely is the drift this table exists to
catch. **`archive-cascade/` and `event-reliability/` each hold two reviews at different statuses**, which
is why this table is one row per review rather than one per folder.

> **Backfill completed for every live workstream, 2026-08-31.** All 12 rows above now carry an `MM-nnn`
> id and front-matter, so each appears on the Control Tower board — the reason the backfill was finished
> rather than continued piecemeal: a half-populated board reads as "there is no work here", which is how
> `archive-cascade`'s and `event-reliability`'s draft reviews came to be invisible.
>
> **Every status was transcribed from this table and from `plans/README.md`**, which the skill names as
> the derivation source. None was inferred from a file body. The one place the two disagreed — the
> authorization plan, filed *Active* in the heading but described in its own prose as blocked on another
> team — was resolved to `blocked` with a `blocked-by-external` entry, because that is what the prose and
> the skill both say. See `scripts/backfill_magiq_media.py` for the full transcription, kept as the record.
>
> **Only `Archive/` is left legacy.** Those documents are finished and their pairing is already recorded
> below; cards for them would pad the Done column and tell you nothing. Ids are minted oldest-first, so
> MM-007 onward reads chronologically — but MM-001…MM-006 were already taken and two of them predate
> MM-007, so the sequence is not globally ordered. Ids are never renumbered; that stays as it is.
>
> **The two retrospective reviews carry an `exception:` line.** They have no paste-ready prompt file and
> no session was ever run from them — they exist to record verified state, not to drive work. That also
> retires the `review-cycle` skill's § Known exceptions entry claiming `plans/projection-tables/` and
> `plans/deployment-naming/` should never be retro-fitted with a review.
>
> **Renamed 2026-08-27:** `event-reliability/prompt.md` → `outbox-implementation-review-2026-08-27-prompt.md`.
> A bare `prompt.md` in a folder holding two reviews was ambiguous about which one it drives; it drives
> the outbox one. Nothing referenced the old path.
>
> **Moved 2026-08-31:** `plans/archive-cascade/prompt.md` → `archive-cascade/archive-cascade-scale-review-prompt.md`.
> Same fault twice over — a bare `prompt.md`, and on the plans side. It drives the scale review, which
> is where it now sits. Nothing referenced the old path.

---

## `projection-tables/` — MM-003, retrospective · 2026-08-31

One review, written after the fact to bring MM-002 under the cycle. `plans/README.md` had carried
MM-002 as *Parked — written and ready, not being worked*; **Phase A had in fact shipped**, roughly a
month earlier.

Verified against three repos at source level — `magiq-media` and `cdk-magiq-media` on
`feature/change-requests`, `aspnetcore-platform` on `main`. Every one of MM-002 § 11's
*Definition of done* items traces to code: `-v{n}` physical naming, version-string metadata with no
runtime counter, CDK-owned tables built from the committed `projection-tables.manifest.json`, a CI
drift gate, and an operator tool that holds **no** `CreateTable` right — the broad `table/media-*`
control-plane wildcard MM-002 set out to remove is gone.

**Nothing has been compiled or run.** The manifest tool's own introducing commit is titled *"added
projection manifest untested"*. One green `dotnet test` converts this review from source-level to
verified — recommended sequencing item 2.

**PT-2 is the finding to remember.** Phase B — version-aware projectors, the zero-window mechanism —
is deliberately deferred, and `docs/adrs/persistence-and-eventing.md` records both the deferral and
its trigger: the first breaking read-model change. **Nothing monitors that trigger.** No check fails
or warns when a developer bumps a `schemaVersion`. The drift gate already has the hook to enforce it.

**PT-4:** the work straddles a merge boundary. `develop` (2026-07-29) has the platform and manifest
work; `feature/change-requests` (2026-08-27, pushed, unmerged) has the later refinements. Reading
either alone gives a wrong answer, which is how the README came to say *Parked*.

## `deployment-naming/` — MM-005, retrospective · 2026-08-31

> **Closed 2026-09-01.** Both open findings are resolved: DN-1's ADR is written at
> `docs/adrs/deployment-and-resource-naming.md` (README row now links it), and DN-4's stale build
> output is deleted — 46 `.js`/`.d.ts` artifacts across `cdk-magiq-media/{lib,bin,test}`, not just the
> one file named below. MM-004 is `done`. Still unrun, and not blocking: `cdk diff` (needs AWS
> credentials), `dotnet test`, and the post-deploy `/healthz` probe. The findings below are kept
> as-written — they are the record of what was found.

One review, same shape and same reason. `plans/README.md` had carried MM-004 as *Parked — four open
decisions, ADR-first*. Three of those decisions were taken and implemented. The fourth is the ADR,
and it is the one thing left.

**DN-1 — the ADR was never written, and the repo says so.** MM-004's header names
`docs/adrs/deployment-and-resource-naming.md` as a deliverable, due *before* the code. It does not
exist on any branch, and `docs/adrs/README.md:20` carries the row marked ⚠ **not written** with its
own warning underneath. The consequence that most needs recording — CloudFormation *replaces* renamed
stateful resources, so every non-prod tier loses data on cutover — currently lives only in a planning
repo that is not code-reviewed.

Everything else verified in both repos: `resourceName` returns the bare name, `bucketName` is
`{name}-{account}-{region}`, `TableSuffix` is always `''`, and a residual-suffix grep over tracked
`.ts` sources returns zero hits. **DN-3:** decision 4 resolved as *keep and repurpose* rather than
remove — `ENVIRONMENT_NAME` now selects the Secrets Manager overlay only, a contract documented in a
component README rather than in the missing ADR. Which is DN-1 restated.

**DN-4:** `lib/constructs/compute/media-api-function.construct.js` is untracked build output from
May 2026 that still shows `-${config.env}`. Its `.ts` source no longer exists. It will mislead the
next grep, as it did this one.

---

## `architecture-review-remediation/` — the 2026-07-19 architecture pass

Eleven reviews, read together and consumed as one body of work by
`plans/architecture-review-remediation/architecture-review-remediation-pr-plan.md`. Finding IDs and
severities are theirs; the plan only sequences them.

Per module: `assetmanagement` · `catalog-collection` · `catalog-folder` · `catalog-mediaitem` ·
`catalog-mediaprofile` · `changerequests` · `metadata-recordtype` · `processing-processingjob` ·
`registration-registration`.

Cross-cutting: `cross-module-integration-review.md` (the seams between modules) and
`cross-module-impact-sweep-2026-07-19.md` (what each finding breaks elsewhere).

> The plans referred to these as living in `D:\source\github\magiq-media\docs\reviews\`. That folder
> exists in the repo and is **empty** — the reviews never moved there. Corrected 2026-08-24.

## `spec-drift-review/` — the spec, interrogated

| Review | What it asks |
|---|---|
| `spec-ddd-coverage-review-2026-08-24.md` | Are the 14 DDD dimensions covered across 68 spec files? Spec only, no code read — every finding is "the spec does not say", not "the code does not do". Consumed by `plans/spec-drift-review/spec-ddd-coverage-review-2026-08-24.md` — same filename, per the convention. |

## `spec-structure/` — where each dimension should live

| Review | What it asks |
|---|---|
| `spec-structure-recommendation-2026-08-25.md` | Given the repo as it stands, what structure guarantees the 16 DDD/spec dimensions each have **one** owning file? Verdict: 12 are already well covered — every gap is a dimension that spans aggregates, so it has either been duplicated into every overview (glossary ×8, bounded contexts ×3, aggregate inventory ×3 disagreeing) or has no home at all (sagas, eventual-consistency policy, cascade rules, contradiction register). Recommends +7 files, one merge, one split, and required-section checks in CI. Most of the work already sits in the DDD plan's Phases 2/4a/5; four items are new. |

> The drift review itself — `plans/spec-drift-review/spec-repo-drift-review.md` — is both a review and
> its own working checklist, so it lives on the plans side where the ✓ column is worked. It is the one
> document that does not follow the review-then-plan split, because splitting it would separate the
> findings from the checkboxes that track them.

## `design/` — feature design review

| Review | Produced |
|---|---|
| `mediaitem-edit-lifecycle-as-is-vs-recommended.html` | `plans/design/mediaitem-edit-session-design.html` |

## `Archive/` — reviews whose work is finished

| Review | Plan it produced |
|---|---|
| `api-rest-review.md` | `plans/Archive/api-consistency-remediation-plan.md` |
| `architecture-spec-review.md` | `plans/Archive/s13-uniqueness-atomicity-remediation-plan.md` + its implementation runbook (finding S13) |
| `handler-status-code-review.md` | Folded into the API-consistency plan (status-code stage) |
| `request-response-review.md` | *(none — moved here from `plans/Archive/` on 2026-08-31; it is a review, and was the only one in the plans tree without a working-checklist reason to be there)* |

> S13's subject — name-reservation atomicity and name-release paths — is live again as **X-9.6** in the
> drift review. Read the S13 review before re-deriving that history.

---

## `asset-custody/` — parked 2026-08-25, not started

One review, no plan. Raised while classifying `Asset` for the ownership ADR and **split out so the
spec-drift work could continue**. It is separate from `spec-drift-review/` for one reason: that plan
corrects documentation against code; **this one changes code**.

The decision is already recorded in `docs/adrs/ownership-and-authorization.md`. What is parked is the work:
`Asset` needs a third concept — **custody**, which transfers on detach — and building it is blocked by
**X-11.32**, the detach half of the asset lifecycle never reaching the Asset aggregate. Sequencing is fixed:
wire detach → model custody → let authorization replace the interim owner checks. Do not remove
`AssetOwnership.CheckOwner` before the last step; it currently guards 8 commands.

---

## `projection-rebuild/` — parked 2026-08-25, not started

One review, no plan. Raised while writing `shared/consistency-model.md` (W25) and split out for the same
reason as `asset-custody/`: the spec-drift plan corrects documentation, **this one changes code**.

**Seven write-side reference indexes cannot be rebuilt by replaying anything**, because they are fed by
integration events from another module and nothing re-emits those. Each backs a **guard** — asset status,
checkout gating, RecordType deprecation, profile defaults, registration capability — so a stale row is a
wrong authorization decision, not a wrong screen. The two uniqueness counters are worse: written by command
handlers rather than events, so **no replay of any kind** reproduces them, and they already drift by design.

It compounds with **X-11.44** (no outbox — a rebuild is the *only* repair for a lost publish) and with the
absence of any lag metric (divergence is discovered, not detected). **Start at question 7 in the review —
divergence detection — not at the rebuild tool.** A rebuild nobody knows to run is worth less than a check
that says an index is behind, and it is far smaller.

---

## `pending-decisions/` — two calls, not two projects · 2026-08-25

One review, **no plan and no research left** — the evidence is complete and the code is understood. What is
missing is a decision, twice.

**Idempotency (X-11.21):** the middleware is deployed, global on the `Api` host, table CDK-provisioned —
and **nothing sends the header**, while three code comments assert the feature does not exist. Worse, the
header is `Idempotency-Key` and every document said `IdempotencyKey`, so any client following the contract
got **zero protection, silently**. Adopt or retire; the current contradiction is the one option to rule out.

**BI-1:** two fully specified aggregates with no class, no command, no queue, no table and no route. They
own **all 16** remaining CI warnings, and those warnings are correct — the sections cannot honestly be
written. Build it, delete the spec, or badge it design-only with a deadline. Note the precedent: W18
retired the truncation guard's exemption on principle, so adding one to the sibling guard is a step back.

---

## The three code workstreams — 2026-08-25

Written so each can be picked up in its own session. All three **change code**, which is why they are
separate from `spec-drift-review/`. Start every one from
`plans/prod-readiness/prod-readiness-gate.md`.

### `authorization/` — one 🔴 blocker left. Plan at `plans/authorization/`
**81 of 132 write commands have no authorization of any kind**, 61 HTTP-reachable, and **no endpoint
anywhere** uses `Roles()`/`Permissions()`/`Policies()`/`Claims()`. Evidence base:
`docs/spec/shared/authorization-matrix.md` (all 132 classified, current) and
`docs/adrs/ownership-and-authorization.md`.

**Worked 2026-08-26.** X-11.31 — the five policy setters — is **closed**: System actor or the
`MediaAdministrator` role, checked before the profile is read. X-11.23 closed with it. X-11.34 and
X-11.35 verified against source and both hold, with the "not determined" clause in X-11.35 now
determined and worse than it read.

**X-11.30 is now blocked outside this repo.** `magiq-auth` issues **no `roles` claim and no `actor_type`
claim** — so the role branch of the new guard admits nobody yet, and `ActorType` is always `"User"` over
HTTP, which makes `AssetOwnership.CheckOwner` and `ForceReleaseCheckout` **owner-only in practice**.
That is one more reason not to delete them, not fewer. The ask to the other team is written and unsent:
`docs/spec/shared/magiq-auth-role-claims-requirements.md`.

**Still standing: do not delete `AssetOwnership.CheckOwner` before the layer exists**, and do not spread
owner checks as a mitigation.

### `archive-cascade/` — two 🟠 blockers left. Plan at `plans/archive-cascade/`
Per-child failures were **discarded**, and because the traversal index prunes as folders archive, a
discarded failure **stranded the subtree unreachable from the root**. Behaviour spec:
`docs/spec/contexts/Catalog/sagas/archive-fan-out.md`, current as of 2026-08-27.

**Worked 2026-08-27.** Open question 1 answered — **continue and suppress ancestors**, not abort. Both
workers now return an `ArchiveFanOutReport`, no folder is archived while anything beneath it is still
active, and `ArchiveFolderHandler` refuses with 422 `FolderArchiveIncomplete` rather than archiving over a
refusal. **X-11.16 and X-11.18 closed**, exactly the dependency the review predicted. Both workers now
have tests; they had none, which is the most likely reason all six findings went unnoticed.

**Also 2026-08-27: X-11.15 closed and Tier 1 scale work landed.** Phase 3 dispatches a non-cascading
`ArchiveFolderNodeCommand`, phase 2 is bounded to 16 concurrent archives, the index reads are batched, and
the folder path refuses an oversized subtree up front rather than 504-ing into a half-archived state.
Watch the trap recorded in the plan: removing the re-entrancy nearly deleted the **collection path's only
registration guard**, which existed purely as a side-effect of it.

**X-11.41 is next** and gets louder first: items moved out of a folder now produce real refusals rather
than silent ones. **X-11.17 is narrowed but open** — the refusal escapes and nothing is stranded, but a
collection holding retention-locked folders still reports archived; it is now decision 5 on the gate.

**A second review sits here now:** `archive-cascade-scale-review.md` — the cascade holds a whole subtree in
memory and must finish in one invocation, so it has a hard ceiling, and the X-11.16 fix made hitting it
loud rather than silent. Tier 1 raised the ceiling ~100×; removing it needs a durable run model. **Measure
before building it** — there is no telemetry on either path.

**The change has never been compiled** — no .NET SDK in the session, same as X-11.31. Run
`dotnet test tests/modules/Catalog/` before treating either finding as closed.

### `event-reliability/` — one 🟠 blocker left, and it is waiting on a decision
Three ways work disappears silently: the **saga DLQ is unreachable** (handlers swallow, message acked,
event lost), there is **no outbox** (a failed publish diverges the read model permanently), and saga
compensation is not idempotent despite its comment. **Nothing measures any of it** — no queue-age alarm,
no projector metric — so all three are discovered rather than detected, and **none can be reproduced
outside production**.

**Worked 2026-08-27.** **X-11.6 closed.** The fix was a rule, now in `docs/spec/shared/saga-patterns.md`
§ Failure handling: *a saga signals a handled outcome by returning, never by throwing* — so there is no
exception type meaning "handled", the inner handler catches nothing, and the outer catches once solely to
convert to `Failed()`. **No CDK change was needed**; `reportBatchItemFailures`, the batch response,
`maxReceiveCount` and the DLQ alarm were already correct and blocked only by the swallow. *Expect
`media-sagas-dlq-depth` to fire for the first time — that is the fix working.*

**X-11.5 core closed.** `ProcessingJob.Fail()` is now a state machine — idempotent on `Failed`,
**transitions from `Queued`** (the validation-timeout path), refuses `Succeeded`/`Bypassed`. Open question
5's framing did not survive contact: blanket idempotency on `Queued` returns success without
transitioning and strands the job exactly as before. A second defect surfaced while fixing it —
`ProcessingJobFailureCategory` had no `ValidationTimeout`, so the saga fell back to `ProcessingTimeout`,
**the one category `Complete()` treats as reversible**. Two tests asserted the defect and passed; both
replaced. **Still open in X-11.5:** the bypass save-before-dispatch ordering, and optimistic concurrency
on saga `SaveAsync` (decision 3 — worth settling *before* `DocumentSigningSaga` exists).

**X-11.44 is now decision-gated, not work-gated.** ADR-005 is corrected — it had described the loss as
*temporary*, offered replay as mitigation (covers 6 of 10 aggregates, no indexes, neither counter), and
set a revisit trigger nothing could observe. Chase's call 2026-08-27: **correct the ADR and let
measurement choose the remedy**, which makes gate decision 7 (the divergence metric) this finding's
critical path.

**A second review sits here now:** `outbox-implementation-review-2026-08-27.md`. Verdict —
**`Magiq.Platform.Messaging.Outbox` has never been run**: zero adopters and zero tests platform-wide, the
drain is invoked by nothing, and sent messages are never marked sent, so adopting it as-is would produce
**unbounded duplicate publication** of every event. It also swallows its own enqueue failures (X-11.6's
pattern, inside the proposed fix) and uses a single constant partition key for all tenants. **Read it
before anyone treats "adopt `IOutbox`" as the small option** — the work is almost entirely in
`aspnetcore-platform`, and the magiq-media side is close to a DI swap.

**The change has never been compiled** — no .NET SDK in the session, same as `authorization/` and
`archive-cascade/`. One green `dotnet test` now clears that caveat for all three workstreams at once.
