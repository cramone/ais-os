---
id: MM-034
type: review
project: magiq-media
workstream: archive-cascade
raised-by: []
status: draft
outcome: pending
todo-id: bfe54e3a-eca7-5a2b-8cd9-50175d0ddb73
created: 2026-08-27
---

> **Backfilled into the review cycle 2026-08-31 as MM-034.** Not yet planned. The cascade holds a whole subtree in memory and must finish in one invocation, so it has a hard ceiling; the X-11.16 fix made hitting it loud rather than silent. Tier 1 raised the ceiling ~100×. **Measure before building** — there is no telemetry on either path.

# Archive cascade at scale — the ceiling, and what a resumable cascade costs

_Opened 2026-08-27, from the question "if the collection was really large, would this approach work?"_
_Companion to [`archive-cascade-review-2026-08-25.md`](./archive-cascade-review-2026-08-25.md). Tier 1
landed the same day; **this review argues Tier 2 and has not been implemented.**_

---

## The one sentence

The cascade holds an entire subtree in memory and must finish inside a single Lambda or HTTP request, so
it has a hard ceiling — and **the X-11.16 fix moved the failure at that ceiling from "silently
half-archived" to "makes almost no progress and says so"**, which is correct, more visible, and more
urgent.

---

## Why this is a new finding, not a variation

The four findings in the sibling review are all about **correctness under failure**. This one is about
**capacity**, and it has the opposite shape: the code is now correct and that is exactly what makes it
stop. Before 2026-08-27 a throttled child was swallowed and its parents archived anyway, so a large
archive "completed". Now a throttled child is a recorded failure that blocks its whole ancestor chain, so
a large archive under throttle archives its leaves and skips everything above them.

**That is the right behaviour** — the alternative is stranding records — but it converts a latent
capacity problem into a visible one, and it means the ceiling now has to be raised rather than tolerated.

> **This is a numbers-free review.** There is no telemetry on either archive path — no metric, no
> dashboard, no timing. Every figure below is an order-of-magnitude estimate derived from the code, and
> **the first task in any plan built on this should be to measure, not to build.** See § What to do first.

---

## Where the ceilings are, in the order they bind

Assume a collection of ~50,000 media items across ~5,000 folders, depth 6. Estimates, not measurements.

| # | Ceiling | Binds at roughly | What happens |
|---|---|---|---|
| 1 | ~~Re-entrancy (**X-11.15**)~~ | ~~low thousands of items~~ | **Closed 2026-08-27.** Was the first ceiling by a wide margin: the registration guard ran O(depth) times over overlapping subtrees, each pass one sequential counter read per item beneath it |
| 2 | **API Gateway's 29s** on the folder path | hundreds of folders | 504, cascade killed mid-flight, **nothing retries**. Now pre-empted by a 500-folder refusal — a guard, not a fix |
| 3 | **The registration guard's counter walk** | tens of thousands of items | One sequential round trip per media item in the subtree. `IUniquenessCounterService` has `IncrementManyAsync` but **no batch read**, so this cannot be batched without a platform change. It is now the most expensive thing on the synchronous path |
| 4 | **Lambda's 15-minute ceiling** on the collection path | tens of thousands of items | SQS redelivers and the cascade **restarts from phase 1**. Nothing checkpoints, so a subtree that cannot finish in one invocation never finishes — it burns the redrive budget re-doing the same prefix and lands in the DLQ |
| 5 | **Memory** | ~1M items | The whole subtree is materialised before any work starts. Levels, the `parentOf` map, and one pending tuple + `Task` per media item |

Ceiling 4 is the one that decides whether Tier 2 is needed. **Every other ceiling can be pushed; that one
cannot be pushed, only removed**, because it is a property of doing the whole job in one invocation.

### What Tier 1 already changed

| | Before | After 2026-08-27 |
|---|---|---|
| Phase 3 command | `ArchiveFolderCommand` — re-entered the whole handler | `ArchiveFolderNodeCommand` — no guard, no cascade |
| Registration guard passes | O(depth), overlapping | Once (folder path); per item, once (collection path) |
| Index reads | One sequential `GetAsync` per folder | One batched `GetManyAsync` per level |
| Phase 2 concurrency | Unbounded `Task.WhenAll` | 16-permit `SemaphoreSlim` |
| Oversized folder subtree | 504 after 29s, half-archived, no retry | 422 `FolderSubtreeTooLargeToArchive`, nothing archived |

Estimated effect: the practical ceiling moves from ~hundreds of items to ~tens of thousands. **None of it
removes ceiling 4.**

---

## The knot: our own invariant is what forces durable state

This is the part worth reading twice before designing anything.

Open question 1 was answered **continue and suppress ancestors**: a folder is archived only when
everything beneath it archived. In one process that invariant costs a `HashSet<FolderId>` in a local
variable. **Across messages it cannot be a local**, because "everything beneath it" is now knowledge
distributed over many invocations that may run concurrently, out of order, and be retried.

So the shape of Tier 2 is not a free choice — it is dictated by the invariant we already committed to:

- **Abort-on-first-failure** would distribute almost for free (stop, and stop everything). We rejected it
  because one permanently-unarchivable child blocks a whole tenant's archive forever.
- **Not suppressing** would distribute for free too, and reintroduces **X-11.18** — the stranding.
- **Continue-and-suppress** needs a durable, per-run record of completion. That is saga state, whatever we
  call it.

I would still make the same call. But it should be recorded that the decision has this cost, so nobody
re-derives it later as though the durable state were incidental complexity.

---

## The proposed shape — counter-based completion, leaf-first

**One row per folder per archive run**, in DynamoDB, keyed under the run:

```
PK  TENANT#{TenantId}
SK  ARCHIVE#{RunId}#FOLDER#{FolderId}
    ParentFolderId          — null for the run's root
    OutstandingChildren     — folders + media items not yet resolved
    FailedDescendants       — count
```

The protocol:

1. **Plan.** Walk the tree once, paged, writing one row per folder with its child + item count. This is
   the only full traversal and it does no archiving.
2. **Work.** Leaves are enqueued first. Each message archives one folder's media items and then the folder.
3. **Complete.** On success, atomic `ADD OutstandingChildren -1` on the parent row. When the parent's
   count reaches zero **and** `FailedDescendants == 0`, enqueue the parent. On failure, `ADD
   FailedDescendants 1` on the parent and propagate that upward without archiving.
4. **Finish.** The root row reaching zero is the run's completion signal — and, unlike today's
   `IsArchived`, it is a real one that survives a restart.

Why this shape:

- It **is** the current invariant, expressed durably. `OutstandingChildren == 0 && FailedDescendants == 0`
  is precisely `!blocked.Contains(folder)`.
- Atomic `ADD` means no read-modify-write race between concurrent children.
- Every message is bounded, so ceilings 2, 4 and 5 all go away together.
- Retry and DLQ come from SQS per chunk rather than per whole cascade.
- **It answers open question 3 for free.** The run rows *are* the status surface, and they are also the
  thing today's runbook says does not exist — "enumerate the subtree and compare" against a traversal
  index that has already been pruned of exactly the folders you are looking for.

### What it forces

- **Open question 2 resolves to async.** The folder endpoint becomes **202 + a run id**, not 204. Both
  paths converge on one invocation model, which closes **X-11.19** as a side effect — today the collection
  cascade is synchronous in-request on dev/qa/staging and async on prod alone, so a production
  partial-archive cannot be reproduced anywhere.
- **Idempotency per message**, since SQS is at-least-once. A redelivered "child completed" must not
  decrement twice — the decrement needs to be conditional on a per-child completion marker, not fired
  blind. **This is the single easiest thing to get wrong in the whole design.**
- **Run expiry.** Rows need a TTL and the plan step needs to be resumable or restartable.

### What it does not fix

- **X-11.41.** `FolderMediaItemsIndex` is add-only, so the plan step still enumerates items that have been
  moved out. At scale this is worse, not better — a bigger tree means more stale entries. **Fix X-11.41
  before building the planner**, or the planner writes wrong counts and `OutstandingChildren` never
  reaches zero. That is a deadlock, not a slowdown.
- **X-11.17.** The collection still archives before its cascade runs. A run record makes it *fixable* —
  the collection could archive when the run completes — but that is a separate decision (gate decision 5).
- **The registration guard's counter walk** (ceiling 3). Batching it needs a platform change to
  `IUniquenessCounterService`. In the run-record model it can at least be folded into the plan step and
  paid once.

---

## What to do first

**Not build this.** In order:

1. **Measure.** Add timing and item/folder counts to both cascade paths, and a queue-age metric on the
   collection path. There is currently no way to tell whether the real ceiling is 5,000 items or 500,000,
   and that number decides whether Tier 2 is urgent or theoretical.
2. **Ask what "really large" means for actual tenants.** Records-management collections can be an entire
   agency series. If the p99 collection is 2,000 items, Tier 1 is sufficient for a long time and this
   review can be parked with a note. If it is 500,000, Tier 2 is a gate item.
3. **Fix X-11.41** — it is next in the workstream anyway, and Tier 2's planner depends on it being correct.
4. **Then** decide Tier 2, with numbers.

> The honest summary: **Tier 1 raised the ceiling by roughly two orders of magnitude for about a day's
> work. Tier 2 removes the ceiling and costs a durable run model, an endpoint contract change, and a
> distributed idempotency problem.** Do not start it without the measurement, and do not skip X-11.41
> before it.

---

## Open questions

| # | Question |
|---|---|
| 1 | What is the realistic upper bound on items in one collection, per tenant? **Blocks everything else here** |
| 2 | Is the 500-folder synchronous limit right? It is a guess on a proxy — folder count, not item count — so a wide-but-shallow folder with very many items still passes it and can still 504 |
| 3 | Should the *collection* archive also get a size refusal? It has no pre-flight guard at all, and on dev/qa/staging it runs in-request (**X-11.19**), so it hits the same 29s wall with none of the protection |
| 4 | Does a completed run record become the audit trail for "this collection was archived on this date, comprising N items"? For regulated records that may be worth more than the performance |

---

## Related

- [`archive-cascade-review-2026-08-25.md`](./archive-cascade-review-2026-08-25.md) — the correctness review; open question 1 is answered there
- `../../plans/archive-cascade/archive-cascade-review-2026-08-25.md` — the plan, where Tier 1 is recorded
- `../../plans/prod-readiness/prod-readiness-gate.md` — X-11.19 and X-11.41 are gate rows
- `../projection-rebuild/` — parked, and shares the "no lag metric, divergence is discovered not detected" problem named in § What to do first
- `docs/spec/contexts/Catalog/sagas/archive-fan-out.md` (magiq-media repo) — the behaviour spec, current as of 2026-08-27
