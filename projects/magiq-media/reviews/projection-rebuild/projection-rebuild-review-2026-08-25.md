---
id: MM-032
type: review
project: magiq-media
workstream: projection-rebuild
raised-by: []
status: parked
outcome: parked
todo-id: cfc4736b-a986-5a2c-ad84-15065103942f
created: 2026-08-25
---

> **Backfilled into the review cycle 2026-08-31 as MM-032.** Parked reason, from reviews/README.md: split out for the same reason as asset-custody — the spec-drift plan corrects documentation, this one changes code. Seven write-side reference indexes cannot be rebuilt by replaying anything, and each backs a guard, so a stale row is a wrong authorization decision. The two uniqueness counters are worse — no replay reproduces them. **Start at question 7, divergence detection, not at the rebuild tool.**

# Projection Rebuild — the indexes replay cannot fix

_Opened 2026-08-25. **Parked deliberately** — raised while writing `shared/consistency-model.md` (W25), and
split out so the spec-drift work could finish. Nothing here is started._

---

## Why this is its own workstream

The spec-drift review corrects documentation against code. **This one changes code** — the same reason
`asset-custody` was split out.

It is also the workstream that decides whether a bad day is recoverable. Everything else on the drift
review makes the system wrong in a knowable way; this one determines whether you can **put it back**.

---

## The problem in one paragraph

A projection can be rebuilt by replaying its aggregate's event stream. **Seven write-side reference indexes
cannot**, because they are not fed by the aggregate that owns them — they are fed by **integration events
from a different module**, and nothing in this system re-emits integration events. Replaying the source
aggregate reproduces its own read models and leaves these seven exactly as broken as they were.

They are not display data. **Each one backs a guard**, so a stale or missing row is a wrong authorization
or invariant decision, not a wrong screen.

---

## The seven

| Index | Fed by (source module) | The guard it backs |
|---|---|---|
| `media-catalog-asset-ref` | AssetManagement | asset status/category checks on role assignment, publish, review approval — invariants 5, 6, 7 |
| `media-catalog-version-asset-ref` | Catalog MediaItem | version purge — which assets belong to a published version |
| `media-catalog-change-request-ref` | ChangeRequests | checkout gating when `ChangeRequestPolicy = RequiredForEdit` — invariant 10 |
| `media-catalog-record-type-index` | Metadata | *"is this RecordType version deprecated"* — invariant 11 |
| `media-asset-item-capability-ref` | Catalog MediaItem | `Processing` capability → quota exemption and validation routing |
| `media-asset-profile-default-ref` | Catalog MediaProfile | *"is this asset a profile default"* — blocks asset deletion, invariant 8 |
| `media-registration-item-ref` | Catalog MediaItem | *"is the item published and registration-capable"* — invariant 12 |

All seven are **unversioned** (`schemaVersion: null`), excluded from `projection-tables.manifest.json` and
from the blue-green rotation tool, whose own note says *"a breaking change to one is a manual in-place
rebuild."* **No tool performs that rebuild.**

## And the ones that are worse

**The two uniqueness counters cannot be rebuilt by anything.** `active-registrations` and `depth` are
written by **command handlers**, not by events, so no replay of any kind reproduces them. Reconstruction
means walking live aggregate state — folder parentage for depth, registration refs per item — and rewriting
the counters. They can already drift by design (**X-11.39** on subtree move, **X-11.43** on a stuck
decrement), and there is **no reconciliation job and no way to inspect a counter through the API**.

**Name reservations** are written transactionally with the aggregate event, so they are durable rather than
derived — equally not replay-rebuildable, though regenerable by enumerating live aggregate names per scope.
No tool exists.

**Same-module indexes are replayable in principle and not in practice**: the folder, profile and processing
indexes are fed by their own module's domain events, but **the CLI does not clear them**, so a replay leaves
stale rows behind rather than rebuilding. That is a smaller fix and probably belongs in the same change.

---

## Why this matters more than it looks

Three things compound, and the third is the one that turns an incident into a long one:

1. **There is no outbox** (**X-11.44**). A publish that fails after commit leaves a read model permanently
   divergent — nothing retries, because nothing knows. **A rebuild is the only repair**, which makes the
   missing rebuild path the second half of that defect.
2. **Nothing measures projection lag** — no alarm on queue age, no projector metric. So divergence is not
   detected; it is *discovered*, usually by a guard behaving oddly.
3. **The rebuild path has never been exercised where it would be needed.** The blue-green runbook is
   explicitly *"run every step against dev first"*, and dev projects **synchronously in-request** — so the
   procedure has only ever run in an environment that has no lag and no queue.

---

## What exists to build on

| Piece | State |
|---|---|
| `projections rebuild --aggregate … --tenant …` CLI | **Works**, covers **6 of 10** aggregates: asset, media-item, folder, collection, media-profile, record-type. Clears then replays. **No verb** for ChangeRequest, ProcessingJob, Registration, DocumentSigningSession |
| Blue-green table rotation (`src/tools/ProjectionReplay/`) | **Implemented** — `rotate`, `rollback`, `abort`, `cleanup`; replays into `-v{new}`, verifies by item count, flips a pointer in `read-model-metadata`; hosts pick it up within a 10 s TTL. Dev-only runbook |
| `projection-tables.manifest.json` | Authoritative for versioned projection tables. **The seven are not in it** |

The gap is not tooling from scratch — it is **a way to re-emit integration events**, which nothing has.

---

## Open questions for whoever picks this up

| # | Question |
|---|---|
| 1 | **How do you re-emit integration events?** Replay the source aggregate through its `*IntegrationEventPublisher` into `EventConsumers`, or read the event store and republish to SNS? The first reuses real mapping code; the second risks fanning out to *every* consumer, not just the index being rebuilt |
| 2 | **How do you rebuild one index without side effects?** Re-publishing `MediaItemApproved` would also hit Registration, AssetManagement and the notifier. Does the rebuild need a targeted consumer, or a replay mode consumers can recognise? |
| 3 | **Are these rebuilds idempotent?** The seven projectors are `ProjectedVersion`-guarded like any other, so a replay without clearing is a no-op — meaning clearing is mandatory, meaning **the guard is unavailable while the rebuild runs**. Is that acceptable, or does it need the blue-green treatment (rebuild beside, then flip)? |
| 4 | **Should the seven be versioned and brought into the manifest**, so rotation covers them like every other projection? That is probably the real answer to (3) |
| 5 | **Counters:** reconciliation job, or make them derivable? A `depth` counter is recomputable from folder parentage; `active-registrations` from live registration refs. Deriving beats reconciling if the read cost is acceptable |
| 6 | Should the CLI cover the four aggregates it currently skips, and should it clear same-module indexes? |
| 7 | **How would you know a rebuild is needed?** Without lag detection this is invisible. Does this workstream need a divergence check — compare `ProjectedVersion` against aggregate version — before it needs a rebuild tool? |

> **Question 7 may be the one to answer first.** A rebuild tool nobody knows to run is worth less than a
> check that says *"index X is behind"*. It is also much smaller.

---

## Sequencing

```
0. Divergence detection            ← smallest, and it tells you whether the rest is urgent
1. Re-emit mechanism for integration events   ← the actual missing capability
2. Rebuild the seven, ideally via the manifest + rotation rather than a bespoke path
3. Counter reconciliation (or derivation)
4. CLI gap-fill: 4 missing aggregates, clear same-module indexes
```

**Do not start at 2.** Building a bespoke rebuild for seven tables is the obvious move and probably the
wrong one — if they become versioned manifest tables, the existing rotation tool already does it.

---

## Related

- `docs/spec/shared/consistency-model.md` (magiq-media repo) — the full lag path, what replay can and cannot
  rebuild, and the environment divergence
- `docs/spec/shared/cross-aggregate-invariants.md` — what each of the seven indexes is guarding, which is
  what makes their staleness matter
- `plans/spec-drift-review/spec-repo-drift-review.md` — **X-11.44** (no outbox), **X-11.39** and
  **X-11.43** (counter drift), **X-11.40** (a dead index), **X-11.41** (an add-only index)
- `reviews/asset-custody/` — the other parked code workstream, same shape
