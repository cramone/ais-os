# Archive cascade — failures that vanish, and the records they strand

_Opened 2026-08-25 from the spec-drift review (W21, W24). **Four 🟠 gate blockers are here**, and three of
them are the same defect seen from different angles._

---

## The one sentence

**Both archive fan-out workers discard every per-child failure** — and because the traversal index is
pruned as folders archive, a discarded failure does not merely go unreported: **it strands the failed
subtree permanently, unreachable from the root, with no tool that can find it.**

---

## What the workers are

`CollectionArchiveFanOutWorker` and `FolderArchiveFanOutWorker` are **process managers nobody called
process managers** — no state, no `media-sagas` row, no `ISagaRepository`. They were unspecified until
2026-08-25.

**Full behaviour spec:** `docs/spec/contexts/Catalog/sagas/archive-fan-out.md` in the magiq-media repo —
written against the saga contract deliberately, so every absent section had to be stated as absent.

They differ in ways that matter:

| | Collection | Folder |
|---|---|---|
| Invocation | **Async** via `CollectionArchivedIntegrationEvent` → SQS | **Synchronous**, inline in the command handler |
| Parent archived | **Before** the cascade | **After** the cascade |
| Registration guard | **None** | Whole-subtree check, refuses with 422 |
| Retry on crash | SQS redelivery | **Nothing retries it** |

**Neither invocation model is wrong alone. Having both is** — a collection archive cascades *into* the
folder path, so one logical operation runs with two sets of guarantees.

---

## The compounding chain — read this before picking a finding

**1. Failures are discarded.** Both workers, identical code:

```csharp
if (!result.IsSuccess)
{
    logger.LogWarning("Failed to archive media item {MediaItemId}: {Error}", mediaItemId, result.Error.ErrorMessage);
}
```

Nothing collected, nothing retried, nothing returned — `ArchiveSubtreeAsync` returns `Task`, not
`Task<Result>`. The completion line logs **attempted** counts, so *"Fan-out complete: 40 folders, 900 media
items"* prints whether all 900 archived or none did. **X-11.16.**

**2. That discarded failure strands the subtree.** Phase 3 archives **leaf-first**, `await Task.WhenAll`
per level. If folder D fails at level *k+1*, the loop proceeds to level *k* and archives D's parent P.
`FolderChildIndexProjector.ResolveKey(FolderArchived)` targets `(ParentFolderId ?? CollectionId)` — **the
parent's record** — and does `SetRemove("ChildFolderIds", {P})`. So P leaves the only traversal either
worker has. **D is unarchived and now unreachable from the root**, along with everything beneath it.
**X-11.18** — confirmed from code 2026-08-25, not speculative.

> **A clean crash is safe**, which is why this looked theoretical. Leaf-first means the unarchived folders
> always form a **connected subtree containing the root**, so a retry reaches all of them. It is the
> *discarded failure* that breaks the invariant, not the crash.

**3. Fixing (1) closes (2).** Collect per-child failures and abort the level rather than proceeding, and
the stranding cannot occur. **That is a stronger argument for X-11.16 than the reporting problem it was
filed under.**

---

## Findings in this workstream

| # | Severity | What |
|---|---|---|
| **X-11.16** | 🟠 High | Per-child failures discarded; *"Fan-out complete"* is meaningless. **Fix this first — it closes X-11.18** |
| **X-11.18** | 🟠 High | A discarded failure strands the subtree, unreachable from the root, permanently |
| **X-11.17** | 🟠 High ⚖️ | `ArchiveCollectionHandler` has **no registration guard** (verified) and archives *before* the cascade. A collection holding retention-locked folders reports archived; the folders stay active; the refusal is swallowed. **Active registrations are exactly what a retention rule protects** |
| **X-11.41** | 🟠 High | `FolderMediaItemsIndex` is **add-only** — its projector handles `MediaItemCreated` and nothing else. So archiving a folder **archives items the user has already moved out of it**, under their old parent |
| **X-11.19** | Med | The cascade is **synchronous in-request on dev/qa/staging** and async over SQS on prod alone. A production partial-archive cannot be reproduced anywhere |
| **X-11.15** | Med | Cascade is re-entrant: each `ArchiveFolderCommand` re-enters `ArchiveFolderHandler`, re-running the registration guard **O(depth) times** over overlapping subtrees, flooding the log with benign "already archived" warnings |

---

## Facts worth having before you start

- **No resume path, no checkpoint, no status surface.** Everything lives in local variables
  (`List<List<FolderId>> levels`, `List<Task> mediaItemTasks`) for one invocation.
- **Unbounded parallelism and unbounded memory.** Phase 2 is one `Task` per media item into a single
  `Task.WhenAll` — no `SemaphoreSlim`, no batching. The whole subtree is materialised before any work
  starts; no paging, no cap on breadth or depth.
- **The caller always gets `204`**, on both paths, regardless of what happened to the children.
- **Neither worker has a test.** `ArchiveFolderHandlerTests` and `CollectionArchivedEventHandlerTests` both
  **mock the worker away**. Every behaviour above is untested — which is very likely why none of it was
  noticed.
- **Per-child operations are idempotent** — `MediaItem.Archive` and `Folder.Archive` both guard on
  already-archived and return a `DomainError` without emitting. So a re-run corrupts nothing; it just
  produces warnings indistinguishable from real failures.

---

## Open questions

| # | Question |
|---|---|
| 1 | ~~**On a per-child failure, abort the level or continue and report?**~~ **Answered 2026-08-27 by Chase: continue, and suppress the ancestors of every refusal.** See below |
| 2 | Should the two workers converge on **one** invocation model? Async-with-a-status-record is the obvious target, but it changes the folder endpoint's contract from synchronous 204 to accepted-202 |
| 3 | Does a partial archive need a **status surface**? Today the only way to detect one is to enumerate the subtree — and the traversal index has already been pruned of exactly the folders you would be looking for |
| 4 | Should `ArchiveCollection` acquire the same registration guard as `ArchiveFolder`, or should the collection archive become a *request* that the cascade can refuse? |
| 5 | `FolderMediaItemsIndex` — add removal handlers, or stop using it as the traversal? |

### Question 1, answered — 2026-08-27

**Continue and report, with the ancestors of every refusal suppressed.** The framing in the table above
was a false pair: *"continuing needs the traversal to stop pruning"* is only true if you continue
**upward**. Continuing sideways does not.

- A refusal blocks its containing folder; a blocked folder blocks its parent; the block walks to the root.
- Siblings and unrelated branches archive normally.
- The un-archived remainder is therefore a **connected subtree containing the root** — the same invariant
  that already made a clean crash safe — so the pruning is harmless and the index needs no change.
- On the folder path the root is not archived, so `IsArchived` becomes a *truthful completion signal*:
  an archived folder's subtree is fully archived. That is a property neither option in the table offered.

**Why not abort.** Identical reachability guarantee for less code, but one permanently-unarchivable child
— an item stuck checked out, a folder behind a stuck counter (X-11.43) — would block a whole tenant's
archive indefinitely, and the retry would never converge. "Archived 899 of 900, here is the one that
refused and why" is the more useful failure for a records platform.

**Two things the review did not have, found while implementing:**

1. **Already-archived must be classified as success, by `errorCode`.** The cascade is re-entrant
   (X-11.15), so already-archived is the *ordinary* outcome of any nested or retried run, not an edge
   case. Counted as a refusal it would block every ancestor on every retry and nothing would ever finish.
   This forced a small contract addition: `MediaItem.Archive` refused **uncoded**, so
   `MediaItemErrorCodes.MediaItemAlreadyArchived` had to be added. `Folder.Archive` already had one.
2. **A refusing media item strands exactly like a refusing folder.** Once its folder archives, the folder
   leaves the traversal and a retry from the root never revisits the item. So phase 2 had to start
   tracking outcomes **per containing folder** instead of one flat `Task.WhenAll`. The review's framing of
   X-11.18 was folder-only.

Question 2 (converging the two invocation models) and question 3 (a status surface) are **unchanged and
still open** — what exists now is a log surface and a 422 on the folder path, not a status record.
Question 4 is now tracked as decision 5 on the prod-readiness gate.

---

## Sequencing

```
1. ☑ X-11.16 — collect failures, decide abort-vs-report (open question 1)   [2026-08-27]
   ☑ → closed X-11.18 as a side effect, exactly as predicted
2. X-11.41 — removal handlers on FolderMediaItemsIndex          ← next
3. X-11.17 — the collection-level registration guard ⚖️          (decision 5 on the gate)
4. X-11.15 — stop the re-entrancy
5. X-11.19 — converge the environment behaviour, or accept and document
```

**Write the tests first.** Nothing covered either worker, and every finding here is a behaviour that a
test would have caught. Going straight to the fix repeats how this happened.

> **Both workers now have tests** (`FolderArchiveFanOutWorkerTests`, `CollectionArchiveFanOutWorkerTests`,
> in `Catalog.WriteModel.Infrastructure.Tests/Services/`). Steps 2–5 extend those files rather than
> starting from nothing — that scaffolding is most of the cost of step 1 and it is already paid.
>
> ⚠️ **Step 1 was written without a compiler** — no .NET SDK was available in the 2026-08-27 session, the
> same gap that left X-11.31 "written but never compiled". Run `dotnet test` on
> `tests/modules/Catalog/` before treating X-11.16 and X-11.18 as closed.

---

## Related

- `docs/spec/contexts/Catalog/sagas/archive-fan-out.md` — **the behaviour spec**, written from code
- `docs/spec/shared/cascade-rules.md` — what cascades and what does not, system-wide
- `docs/spec/shared/cross-aggregate-invariants.md` — rule 13 (registration guard), rule 14 (depth)
- `docs/spec/contexts/Catalog/aggregates/Folder/folder.scenarios.md` — worked archive-cascade examples
- `plans/spec-drift-review/spec-repo-drift-review.md` — X-11.15 to X-11.19, X-11.41 in full
- `plans/prod-readiness/prod-readiness-gate.md`
