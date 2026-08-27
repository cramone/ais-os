# Archive cascade — plan

_Opened 2026-08-27. Named for the review it consumes,
[`reviews/archive-cascade/archive-cascade-review-2026-08-25.md`](../../reviews/archive-cascade/archive-cascade-review-2026-08-25.md),
per the folder convention._

**Findings:** X-11.16 ☑ · X-11.18 ☑ · X-11.17 · X-11.41 · X-11.19 · X-11.15
**Spec:** `docs/spec/contexts/Catalog/sagas/archive-fan-out.md` (magiq-media repo) — current as of 2026-08-27

---

## The decision the workstream turned on

**Open question 1 — abort the level, or continue and report? Answered 2026-08-27: continue, and suppress
the ancestors of every refusal.**

The review framed it as a pair with a cost on each side: aborting prevents the stranding but leaves a
half-archived subtree; continuing needs the traversal to stop pruning. **The second half was wrong** —
continuing needs the traversal to stop pruning only if you continue *upward*. Continuing sideways does not:

- A refusal blocks its containing folder; a blocked folder blocks its parent; the block walks to the root.
- Siblings and unrelated branches archive normally.
- The un-archived remainder is a **connected subtree containing the root** — the same invariant that
  already made a clean crash safe — so the pruning is harmless and `FolderFoldersIndex` needs no change.
- The root is not archived, so on the folder path `IsArchived` becomes a **truthful completion signal**:
  an archived folder's subtree is fully archived. Neither option in the review offered that.

Aborting would have given the same reachability guarantee for less code, but one permanently-unarchivable
child — an item stuck checked out, a folder behind a stuck counter (**X-11.43**) — would block a whole
tenant's archive indefinitely, with a retry that never converges. For a records platform, *"archived 899
of 900, here is the one that refused and why"* is the more useful failure.

---

## Step 1 — X-11.16, closing X-11.18 ☑ 2026-08-27

### What changed

| | |
|---|---|
| `ArchiveFanOutReport` | New. Failures, skipped folders, archived-vs-attempted counts, `IsComplete`, `Describe()`. In `Catalog.WriteModel/Services/` |
| `ArchiveFanOutCascade` | New. Phases 2 and 3, shared by both workers. `Catalog.WriteModel.Infrastructure/Services/` |
| Both worker interfaces | `Task` → `Task<ArchiveFanOutReport>` |
| Both workers | Phase 1 now builds a **parent map** alongside the levels; the flat `List<List<FolderId>>` threw those links away and the suppression needs them |
| `ArchiveFolderHandler` | Archives the root only when `report.IsComplete`; otherwise **422 `FolderArchiveIncomplete`** |
| `CollectionArchivedEventHandler` | Logs Error on an incomplete run instead of claiming completion |
| `MediaItem.Archive` | Already-archived refusal now carries `MediaItemAlreadyArchived` — it was **uncoded** |
| `FolderErrorCodes` · `MediaItemErrorCodes` · `error-catalog.md` | Two new codes |
| Tests | `FolderArchiveFanOutWorkerTests` (11 cases) · `CollectionArchiveFanOutWorkerTests` (6). **Both workers had none** |

### Two things the review did not have

1. **A refusing media item strands exactly like a refusing folder.** Once its folder archives, the folder
   leaves the traversal and a retry from the root never revisits the item inside it. X-11.18 was written
   folder-only. So phase 2 tracks outcomes **per containing folder** rather than in one flat
   `Task.WhenAll`.

2. **Already-archived must be classified as success, by `errorCode`.** The cascade is re-entrant
   (**X-11.15**), so already-archived is the *ordinary* outcome of any nested or retried run, not an edge
   case. Counted as a refusal it would block every ancestor on every retry and nothing would ever finish
   archiving. `Folder.Archive` already carried a code; `MediaItem.Archive` did not, which is why a
   contract addition was unavoidable. **Never classify on the message string.**

### ⚠️ Not verified

**Written without a compiler** — no .NET SDK was available in the 2026-08-27 session. This is the same gap
that left X-11.31 "written but never compiled", and it is the reason neither finding is ticked on the gate
without a caveat.

```
dotnet test tests/modules/Catalog/Catalog.WriteModel.Infrastructure.Tests/ -v normal
dotnet test tests/modules/Catalog/Catalog.WriteModel.Tests/ -v normal
```

Known compile risks, in order of likelihood:

- **Moq setup of `ICommandDispatcher.SendAsync`.** Both test fixtures set up the generic overload as
  `SendAsync(It.IsAny<ICommand<Result<Unit, IDomainError>>>(), ...)`. If overload resolution picks the
  non-generic `SendAsync(ICommand, ...)` the strict mock throws rather than failing to compile — the
  symptom would be every test failing identically at the first dispatch.
- **`ProjectionKey<T>` construction in tests.** `CreateProjectionKey` is `internal` on both index types
  and the test assembly is separate, so the fixtures build keys with the public `ProjectionKey<T>` ctor
  and rely on the implicit `TenantId`/`FolderId`/`CollectionId` → `string` conversions. If the discriminator
  is not byte-identical to what the worker computes, the strict lookup mocks will not match.
- **`NullLogger<T>`** — assumes `Microsoft.Extensions.Logging.Abstractions` resolves in
  `Catalog.WriteModel.Infrastructure.Tests`. It already does in `Catalog.WriteModel.Tests`.
- **Transitive project reference.** The new tests use types from `Catalog.WriteModel`, which
  `Catalog.WriteModel.Infrastructure.Tests` reaches only transitively through
  `Catalog.WriteModel.Infrastructure`.

**Keep the negative assertions.** `_dispatched.Should().NotContain(...)` is what actually tests X-11.18 —
a test on the returned failure list alone passes with X-11.16 fixed and still permits the stranding,
because the stranding is caused by a command that *is* dispatched, not by one that fails.

---

## Step 1b — X-11.15 and Tier 1 scale work ☑ 2026-08-27

Landed the same day, prompted by "would this work for a really large collection?". It would not, and the
X-11.16 fix made that more urgent: a throttled child is now a recorded failure that blocks its ancestors,
so a large archive under throttle makes almost no progress instead of half-archiving silently.

| | |
|---|---|
| `ArchiveFolderNodeCommand` · `ArchiveFolderNodeHandler` | New. Archive one folder — no guard, no cascade. **Deliberately not HTTP-reachable** |
| `ArchiveFanOutCascade` phase 3 | Dispatches the node command, so the cascade no longer re-enters itself. **Closes X-11.15** |
| `ArchiveFolderHandler` | Archives its own root through the same node command, so root and descendants cannot drift. No longer takes `INameReservationService` |
| Phase 2 concurrency | 16-permit `SemaphoreSlim`, was an unbounded `Task.WhenAll` |
| Phases 1 and 2 lookups | Batched `GetManyAsync` per level, was one sequential `GetAsync` per folder. `IProjectionReader.GetManyAsync` existed and neither worker used it |
| `ArchiveFolderHandler` size guard | 422 `FolderSubtreeTooLargeToArchive` above 500 descendant folders, checked **before** the registration guard so a size refusal does not cost a full counter walk |
| Tests | `ArchiveFolderNodeHandlerTests` new; both worker fixtures reworked to dictionary-driven `It.IsAny` lookup mocks covering `GetAsync` and `GetManyAsync` |

### The trap in this step, and the test that guards it

**Removing the re-entrancy nearly deleted the collection path's only registration guard.**
`ArchiveCollectionHandler` has no pre-flight guard (**X-11.17**); the collection path was protected purely
as a *side-effect* of the re-entrancy, because every folder it dispatched re-entered `ArchiveFolderHandler`
and re-ran that guard. Dispatching node commands instead would have silently removed it — retention-locked
records archiving with no refusal anywhere.

So `ArchiveFanOutCascade` takes a `guardRegistrations` flag: **on** for the collection path, **off** for the
folder path, whose pre-flight guard already covers the subtree. The collection version is also *stricter*
than what it replaced — the old folder-granularity guard ran in phase 3, after phase 2 had already archived
the locked items and left only their folders unarchived. It now refuses the item itself, in phase 2, before
archiving it.

`CollectionArchiveFanOutWorkerTests.ArchiveSubtree_ItemWithActiveRegistrations_IsRefusedBeforeBeingArchived`
is the test standing where that side-effect used to be. **If it goes, retention-locked records archive
silently.**

### Fixture rule, learned the hard way — twice

**A Moq `Setup`/`Verify` argument is a C# expression tree, and expression trees are a restricted subset of
the language.** Two build breaks in this workstream came from forgetting that:

| Written inside the tree | Result |
|---|---|
| `new ProjectionKey<T>(_tenant, _collection)` | Broke. Build the key into a local or field first |
| `It.Is<ICommand<…>>(c => c is ArchiveFolderNodeCommand n && n.FolderId == id)` | **CS8122** — *"An expression tree cannot contain a pattern-matching 'is' expression"* |

The rule for anything added here: **keep the expression tree to `It.IsAny` / plain member access, and put
every construction, cast, pattern or conditional outside it.** In practice that means capturing what the
mock received and asserting on the captured value:

- Index lookups → dictionary-backed `It.IsAny` setups. Also means new `GetManyAsync` call sites need no
  new setups.
- Dispatched commands → a `List<ICommand<…>>` filled in the `.Returns(...)` delegate, then
  `.Should().ContainSingle().Which.Should().BeOfType<T>()`.

Note the asymmetry that makes this confusing: the lambda passed to `.Returns(...)` is a **delegate**, not
an expression tree, so `switch` expressions and pattern matching are perfectly legal there — which is why
the worker fixtures' command-type `switch` compiles while the same syntax inside `It.Is` does not.

---

## Remaining steps

| # | Finding | What it needs | Notes |
|---|---|---|---|
| 2 | **X-11.41** 🟠 | Removal handlers on `FolderMediaItemsIndex`, or stop using it as the traversal (open question 5) | **Next.** Add-only today, so the cascade archives items the user has already moved out. Compounds with step 1: those items now produce *real* refusals rather than silent ones, so this gets louder before it gets better. **Tier 2 depends on it** — a planner writing counts from a stale index deadlocks rather than slows |
| 3 | **X-11.17** 🟠 ⚖️ | Guard `ArchiveCollectionHandler` like `ArchiveFolderHandler`, **or** make the collection archive a request the cascade can refuse | Now **decision 5** on the prod-readiness gate. Step 1 narrowed it — the refusal escapes, is logged at Error, and nothing is stranded — and step 1b tightened the collection path's own guard to per-item, pre-archive. But the collection still reports archived with locked folders active |
| 4 | **Scale / Tier 2** | A durable, chunked, counter-based completion model | **New — argued in [`../../reviews/archive-cascade/archive-cascade-scale-review.md`](../../reviews/archive-cascade/archive-cascade-scale-review.md).** Do not start it without measurements; **measure first**, then X-11.41, then decide |
| 5 | **X-11.19** 🟡 | Converge the environment behaviour, or accept and document | Sync in-request on dev/qa/staging, async over SQS on prod alone. **Closes as a side effect of Tier 2**, which converges both paths on async and changes the folder endpoint from 204 to 202 |

Steps 2–5 extend the two test fixtures from step 1 rather than starting from nothing. That scaffolding was
most of step 1's cost and it is already paid.

## Still open from the review

- **Question 2** — converge on one invocation model? Unchanged.
- **Question 3** — does a partial archive need a status surface? Unchanged. What exists now is a **log**
  surface (Error line, alarmable) and a 422 on the folder path — not a status record.
- **Question 4** — folded into gate decision 5, above.
- **Question 5** — folded into step 2, above.

---

## Related

- [`../../reviews/archive-cascade/archive-cascade-review-2026-08-25.md`](../../reviews/archive-cascade/archive-cascade-review-2026-08-25.md) — the review
- [`../prod-readiness/prod-readiness-gate.md`](../prod-readiness/prod-readiness-gate.md) — the gate
- [`../spec-drift-review/spec-repo-drift-review.md`](../spec-drift-review/spec-repo-drift-review.md) — X-11.15–11.19, X-11.41 in full
- `docs/spec/contexts/Catalog/sagas/archive-fan-out.md` (magiq-media repo) — the behaviour spec
