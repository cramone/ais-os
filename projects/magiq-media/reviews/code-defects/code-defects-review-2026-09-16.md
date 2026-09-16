---
id: MM-002
type: review
project: magiq-media
workstream: code-defects
raised-by: []
status: draft
outcome: pending
todo-id: e9fa6eb2-3337-5f33-9ea8-9290013e2b3e
created: 2026-09-16
---

# Code defects — five clusters carried out of the retired todo file

## Scope

**What this is.** `projects/magiq-media/todos.md` was retired on 2026-09-16. Most of it was deploy
checklists (moved to `deploy-runbook.md` § Implementation status), small concrete fixes (moved to the
`Media` ADO board), or items already resolved. What is left is five clusters of **code** defects that carry
argument rather than instruction — the reasoning is the deliverable, and a work item cannot hold it.

**What this is not.** This is not [`MM-001`](../spec-baseline/spec-baseline-review-2026-09-16.md). That
review is about what the documents say; this one is about what the code does. They overlap in subject —
authorization most of all — and the boundary matters: **`MM-001` fixes a spec that never stated a rule;
`MM-002` fixes code that does not enforce one.** Writing the rule does not guard the command, and guarding
the command does not write the rule. Neither closes the other.

**Not verified in this review.** Every finding below was captured between 2026-08-24 and 2026-09-01 against
a codebase that has moved since — one item in the source file was already marked fixed and verified, which
is precisely why the others cannot be assumed live. **Re-verification is the first task of any plan that
consumes this**, and each finding says what would settle it.

**The dead ids.** The source file cited `X-11.30`, `X-11.44`, `X-9.6` and about forty others, all belonging
to a global drift register that no longer exists. The ids are not recoverable and are not reconstructed
here; each cluster is restated in its own terms, which is the same rule applied to the spec tree on the same
day. Where a finding's substance came from a cited id, the substance survives and the citation does not.

---

## Findings

Severity is `Critical | High | Medium | Low`. Severities are inherited from the source file's own markers
(🔴 → Critical/High, 🟠 → High/Medium) and should be re-judged on verification, not trusted.

### CD-1 · Authorization is not enforced, anywhere but one place — **Critical**

No `Collection`, `Folder`, `MediaItem` or `MediaProfile` command performs an ownership check at any layer.
The five MediaProfile governance setters are the only guarded commands in the Catalog module. The source
file recorded 86 of 132 write commands with no authorization check of any kind, 66 of them reachable over
HTTP — those figures are from 2026-08-25 and are the least trustworthy part of this finding; the shape is
what matters.

**Why it is Critical and not merely High:** the same file records that an unprivileged tenant member can
disable the guards *tenant-wide* through the policy setters. That is privilege escalation, not a missing
check — it converts a caller with no privileges into one for whom the remaining guards no longer apply.

**Start with the five setters.** Smallest fix, largest effect, and it closes the escalation path
independently of everything else.

**Relationship to `MM-001`:** SB-1…SB-5 and SB-68…SB-71 specify who *may* run each command, and Q1 settled
the model — `Resource.Verb[.All]` scopes at the edge, resource predicates at the aggregate. **That gives
this cluster its target.** Do not design the authorization model here; consume it.

✅ Settled by a re-count against `develop`, plus a decision on whether the five setters ship ahead of the
rest.

### CD-2 · Archive cascade loses failures and mis-targets moved items — **High**

A cluster of four, from the same capture. The load-bearing one: **on a per-child failure the cascade
neither aborts the level nor reports — the failure is discarded.** Closing that closes a second finding
about failures that vanish, which is why it goes first. Separately, an item moved between folders is
archived under its *old* folder.

**The design decision the work turns on, and it is not a code question:** on a per-child failure, does the
cascade abort the level, or continue and report? Everything else in the cluster is downstream of that
answer. `MM-001`'s SB-71 is adjacent — it asks whether cascade commands should be restricted at all — but
it does not answer this.

✅ A stated failure policy, then the code matching it.

### CD-3 · Event reliability — no outbox, and a deviation that was never documented — **High**

Integration events are published inline by the command handler after the event store write. If the publish
fails after the commit, the event is lost and is repairable only by rebuilding — which CD-4 says cannot be
done for seven of the affected tables.

**The open question gating this is a decision, not an investigation: adopt an outbox, or document the
deviation.** The platform SDK provides one — its own `CLAUDE.md` states *"Never publish integration events
directly — always go through `IOutbox` or `IApplicationBus`"* and *"the outbox guarantees at-least-once
delivery atomically with the aggregate write"*. magiq-media's ADR-005 deliberately chose inline publication
instead. **So this is not a gap against the platform's intent by accident — it is a documented divergence
from it**, and the question is whether that divergence still holds.

One finding in this cluster — saga DLQ unreachable, events silently lost — was **fixed and verified on
2026-09-08**. It is recorded here only so nobody re-raises it.

✅ Either an outbox adoption plan, or an ADR stating the deviation and what it costs.

### CD-4 · Seven write-side reference indexes cannot be rebuilt at all — **High**

Replay does not reproduce them. They are fed by integration events from another module, and **nothing
re-emits integration events** — so replaying the source aggregate leaves them exactly as broken. Each backs
a **guard** (asset status, checkout gating, RecordType deprecation, profile defaults, registration
capability), so staleness is a wrong authorization decision rather than a stale screen.

**The two uniqueness counters are worse:** written by command handlers rather than events, so nothing
reproduces them, and they are already known to drift.

**Why it compounds:** with CD-3 (a publish that fails after commit is repairable only by rebuild) and with
there being no lag metric at all — so divergence is *discovered*, not detected. The blue-green rebuild
runbook has only ever been exercised against dev, which projects synchronously and therefore has neither
lag nor a queue.

**Start with divergence detection, not the rebuild tool.** Comparing `ProjectedVersion` against aggregate
version is small, and it tells you whether the rest is urgent. **Do not begin by building a bespoke rebuild
for seven tables** — if they become versioned manifest tables, the existing blue-green rotation already does
the work. A related proposal, schema-versioned table rotation, supersedes the older hot-swap approach and
may already be the home for: Registration and Processing summary rows each landing in one partition per
tenant, `media-processing-asset-index` registered `schemaVersion: null` (which the replay tooling refuses),
and the absence of a CLI rebuild verb for `ProcessingJob` and `Registration`.

✅ A divergence check that runs, before any rebuild tooling is designed.

### CD-5 · `Asset` needs custody, and has nowhere to put it — **Medium, parked**

`Asset` needs a third concept the codebase lacks. **Custody** differs from provenance in that it *transfers*,
and from authorization in that it attaches to the resource. The proposal: split `Asset.OwnerId` into
`UploadedBy` (immutable) and `CustodianId` (transfers to whoever detaches the asset from a role).

**Blocked, and the blocker is worth knowing on its own.** Detach never reaches the `Asset` aggregate:
`DetachFromMediaItem` exists but nothing dispatches it, there is no unassign consumer, and
`ApplyAssetAssignmentCommand` is attach-only. **So after its first assignment an asset can never return to
standalone and can never be reassigned to a different MediaItem.** That is a functional defect in its own
right, independent of custody, and it should probably not wait for the custody design.

**Sequencing is fixed:** wire detach → model custody → authorization replaces the interim owner checks.
**Do not remove `AssetOwnership.CheckOwner` before the last step** — it currently guards eight commands
including delete, and removing it early widens CD-1.

**Settle before coding:** the Asset-side handler runs in `EventConsumers` with no HTTP actor, so **the
detaching user's identity has to travel on the integration event**. Cheap to decide now, expensive later.

**Interaction with `MM-001`:** the four provenance aggregates (`Collection`, `Folder`, `MediaItem`,
`MediaProfile`) have a decided-but-unbuilt rename of `OwnerId` → `CreatedBy`. `MM-001`'s Q5 removed the
`owner_system` sentinel and ruled `OwnerId` provenance-only, and its `MediaProfile` ruling removes the field
there entirely. **Whoever works this cluster must read those two rulings first** — the rename and the
custody split are the same conversation, and `MediaProfile` has already left it.

✅ A decision on whether detach ships ahead of custody, and how the detaching identity reaches the consumer.

---

## Open Questions

1. **Are these still live?** — **Open.** Captured 2026-08-24 to 2026-09-01; one item in the source was
   already fixed. Nothing here should reach a plan un-reverified, and the re-count for CD-1 in particular
   will move.
2. **On a per-child cascade failure: abort the level, or continue and report?** (CD-2) — **Open.**
3. **Outbox, or a documented deviation?** (CD-3) — **Open.** ADR-005 chose inline publication deliberately;
   the question is whether that still holds, not whether the platform offers an alternative.
4. **Does detach ship ahead of custody?** (CD-5) — **Open.** The reassignment defect stands alone and may
   not want to wait.
5. **Where do the four standing reports live?** — **Open.** The retired file referenced Catalog, Processing,
   Registration and DocumentSigning code-defect reports dated 2026-09-07/08 in an `adhoc/` folder. **That
   folder does not exist in this project and did not exist before the board was cleared.** Those reports are
   more recent than every finding above and would re-verify much of this review. If they survive somewhere,
   they belong in this workstream.

---

## Dependencies

**Documents:** [`MM-001`](../spec-baseline/spec-baseline-review-2026-09-16.md) — not a blocker, but CD-1
should consume its Q1 permission model rather than invent one, and CD-5 must read its Q5 ruling before
touching `OwnerId`. Promote to `depends-on` only if a plan here would otherwise design authorization
independently.

**External blockers:** none. Note that CD-1's role branch depends on `magiq-auth` issuing `roles` claims for
*implementation*, but not for deciding or specifying.

**Not tracked here:** the deploy and ops items from the same source file are in `deploy-runbook.md`
§ Implementation status, items 12–16. The four small concrete fixes are on the `Media` ADO board.

---

## Recommended sequencing

Rough; the plan refines it, and nothing starts before question 1 is answered.

1. **Re-verify all five clusters against `develop`**, and find out whether the `adhoc/` reports survive —
   they are newer than everything here.
2. **CD-1's five governance setters.** Smallest fix, closes the escalation path, independent of every open
   question in this review.
3. **Answer questions 2, 3 and 4.** Each gates its own cluster and none needs investigation — they need
   calls.
4. **CD-4's divergence detection** — small, and it tells you whether CD-4's remainder is urgent or not.
5. **CD-5's detach wiring**, which is a functional defect regardless of whether custody follows.
6. **The rest**, in whatever order the answers to step 3 imply.
