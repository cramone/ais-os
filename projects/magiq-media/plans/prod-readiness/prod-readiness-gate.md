---
id: MM-006
type: gate
project: magiq-media
workstream: prod-readiness
consumes: []
supersedes: -
status: active
todo-id: eecf8c43-1452-5bef-9920-42fbe4712d27
created: 2026-08-25
exception: consumes is empty only because the plans this gate triages — authorization, archive-cascade, event-reliability, spec-drift-review — are still legacy and carry no ids yet. Add each id here as that workstream is backfilled. A gate legitimately has no review, which is not the exception.
---

# Production Readiness Gate

_Created 2026-08-25 from the findings of the spec-drift review. **This is a gate, not a backlog** — it
exists to be checked before `PROD_ENABLED` is set to `true`._

---

## Why this file exists

The 2026-08 spec review produced **42 open code findings**, two of them Critical. **Five are now closed —
X-11.31 (Critical) and X-11.23 on 2026-08-26, X-11.16, X-11.18 and X-11.6 on 2026-08-27 — leaving 37 open
and one Critical.** They are recorded in
[`../spec-drift-review/spec-repo-drift-review.md`](../spec-drift-review/spec-repo-drift-review.md) with
full evidence, and that file remains the source of truth for *what each one is*.

**What was missing is triage.** A list of 42 findings with severities is not a plan, and severity alone
does not say what blocks a release. This file answers one question: **which of these must be closed before
production is enabled, and which can be scheduled normally.**

### The fact that shapes everything here

**Nothing is in production.** `build-and-push.yml` gates staging and prod behind `STAGING_ENABLED` and
`PROD_ENABLED`; both are unset, and only `dev` and `qa` deploy.

So **none of these findings is exploitable by a real tenant today.** The risk is not that they are live —
it is that they go live silently when someone flips those flags. That is why this is a gate rather than a
hotfix queue, and why the gate has to exist *before* the flags are touched rather than after.

> ### The rule
>
> **Do not set `PROD_ENABLED` or `STAGING_ENABLED` to `true` while any 🔴 or 🟠 row below is open.**
> A 🟡 row is a judgement call at the time. A ⚪ row never blocks.
>
> `STAGING_ENABLED` matters as much as `PROD_ENABLED` here: staging runs as
> `ASPNETCORE_ENVIRONMENT=Development`, so it does **not** exercise the async projection path or the queue
> behaviour prod uses. Enabling staging does not de-risk prod (**X-11.19**).

---

## The gate

### 🔴 Blockers — security. Close before any environment beyond `qa`

| # | Finding | Why it blocks |
|---|---|---|
| ☑ | **X-11.31** 🔒 | ~~An unprivileged tenant member can disable the guards tenant-wide.~~ **Closed 2026-08-26.** The five setters now require a System actor or the `MediaAdministrator` role, checked before the profile is read. **Caveat: written but never compiled** — no .NET SDK was available in that session. Not properly closed until `dotnet test` is green |
| ☐ | **X-11.30** 🔒 | **81 of 132 write commands have no authorization of any kind**; 61 are HTTP-reachable. Includes `ConfirmRegistration`, `RejectRegistration`, `ApproveAmendment` — the commands that *decide* a filing — and `PurgeMediaItemVersion`, which destroys a retained record version |

**These two are one workstream**, now planned in `../authorization/authorization-review-2026-08-25.md`.
The ADR (`docs/adrs/ownership-and-authorization.md`) and the matrix
(`docs/spec/shared/authorization-matrix.md`) are its evidence base and both are current as of
2026-08-26.

> ### X-11.30 is now blocked outside this repo
>
> **`magiq-auth` issues no `roles` claim and no `actor_type` claim** — established 2026-08-26 by reading
> its source. Metadata's 17 commands and MediaProfile's remaining 13 are tenant-wide configuration with
> **no owner to fall back on**, so they need a role and cannot be closed in any other shape. That makes
> `docs/spec/shared/magiq-auth-role-claims-requirements.md` — the hand-off to that team, written and
> **not yet sent** — this blocker's critical path.
>
> **Two things this changes about the current state, both worth knowing before the flags are flipped:**
> `ActorType` is always `"User"` over HTTP, so the System branch of `AssetOwnership.CheckOwner` and
> `ForceReleaseCheckout` never fires for a real caller — those guards are **owner-only in practice** and
> narrower than they read. And Registration's five decision commands could take a System-actor gate
> today without waiting on anybody, which is worth doing separately if the identity provider work is
> slow.

### 🟠 Blockers — data loss and compliance

| # | Finding | Why it blocks |
|---|---|---|
| ☑ | **X-11.6** | ~~The saga DLQ is unreachable.~~ **Fixed 2026-08-27.** The rule — *a saga signals a handled outcome by returning, never by throwing* — is in `docs/spec/shared/saga-patterns.md` § Failure handling and applied to all five pairs: inner handlers catch nothing, the outer catches once solely to convert to `MessageProcessStatus.Failed()`. **No CDK change needed** — `reportBatchItemFailures`, the batch response, `maxReceiveCount: 3` and the DLQ alarm were all already correct and blocked only by the swallow. Eleven tests added; the `Sagas` test folder was empty, which is why this survived. **Caveat: written but never compiled** — no .NET SDK in that session. Not properly closed until `dotnet test` is green. *Expect `media-sagas-dlq-depth` to fire for the first time — that is the fix working* |
| ☐ | **X-11.44** | **No outbox.** A publish that fails after commit leaves the read model permanently divergent — nothing retries, because nothing knows. Compounds with the missing rebuild path. **Reframed 2026-08-27 and now needs a decision, not just work:** ADR-005 *does* document the dual-write risk (`persistence-and-eventing.md:60`) but calls the loss *"temporary"*, offers replay as the mitigation (**replay covers 6 of 10 aggregates and cannot rebuild seven indexes or either counter**), and conditions its revisit trigger on a measurement **nothing takes**. Separately, the platform's `IOutbox` **cannot join the event-store transaction** — `IOutboxStore.EnqueueAsync` takes no transaction handle and the single-aggregate `DynamoDbEventStore.SaveAsync` is a plain `PutItem` — so adopting it as-shipped moves the failure window rather than closing it. **Three options, in the review; Chase's call** |
| ☑ | **X-11.16** | ~~Archive fan-out discards every per-child failure.~~ **Fixed 2026-08-27.** Both workers return an `ArchiveFanOutReport`; the completion line reports outcomes and logs Error when incomplete; the folder path refuses with 422 `FolderArchiveIncomplete`. Both workers now have tests — they had none, which is why this went unnoticed. **Caveat: written but never compiled** — no .NET SDK in that session. Not properly closed until `dotnet test` is green |
| ☑ | **X-11.18** | ~~A swallowed child failure strands the subtree unreachably.~~ **Fixed 2026-08-27, as a consequence of X-11.16 exactly as predicted.** The cascade never archives a folder while anything beneath it is still active, so the un-archived remainder stays a connected subtree containing the root and re-issuing the archive recovers it. Same compile caveat |
| ☐ | **X-11.17** ⚖️ | A collection containing **registration-locked** folders archives anyway — no guard, no rollback, no user-visible record. Active registrations are exactly what a retention rule protects. **Narrowed 2026-08-27, not closed:** the refusal now escapes the worker and is logged at Error, and nothing is stranded — but `ArchiveCollectionHandler` still has no guard and the collection still reports archived. Needs decision 5 below |
| ☐ | **X-11.41** | `FolderMediaItemsIndex` is add-only, so archiving a folder **archives items the user has already moved out of it** |
| ☐ | **X-11.21** | The idempotency header is `Idempotency-Key`, not `IdempotencyKey`. Every client following the published contract gets **zero replay protection, silently**. *(Decide adopt-or-retire — see Decisions)* |

### 🟡 Judgement calls — decide explicitly, do not let them drift

| # | Finding | The call |
|---|---|---|
| ☐ | **X-11.35** | Folder assignment/move is guarded by nothing — an item can be moved while checked out, mid-review, or **while archived**. Is any of that legitimate? **Verified 2026-08-26, and the archived case is no longer undetermined:** archive releases the title reservation but does *not* clear `FolderId`, so a later move hits a conditional-write failure that surfaces as **`409 "a media item with this title already exists in the destination folder"` — a permanently unactionable error blaming a conflict that does not exist.** Neither command carries an actor at all, so guarding either means changing the command shape |
| ☐ | **X-11.38** | A deprecated MediaProfile's items can still be edited but not published. Nobody chose that half-life |
| ☐ | **X-11.24** ⚖️ | **No download is logged, audited or evented.** Who downloaded what is not recoverable. For regulated records, decide deliberately |
| ◐ | **X-11.5** | ~~Compensation is not idempotent; after a validation timeout the ProcessingJob stays `Queued` forever.~~ **Core fixed 2026-08-27.** `ProcessingJob.Fail()` is now a state machine — idempotent on `Failed`, **transitions from `Queued`** (the validation-timeout path), refuses `Succeeded`/`Bypassed`. Blanket idempotency would have re-created the bug, which is why open question 5's framing didn't survive contact. **Second defect found and fixed alongside:** `ProcessingJobFailureCategory` had no `ValidationTimeout`, so the saga fell back to `ProcessingTimeout` — the one category `Complete()` treats as *reversible* — mislabelling the failure and making it wrongly recoverable. **Two tests asserted the defect and passed**; both replaced. **Still open:** the bypass-branch save-before-dispatch ordering, and optimistic concurrency on saga `SaveAsync` (decision 3) — both deliberately separated, both made more reachable by X-11.6's fix. Same compile caveat |
| ☐ | **X-11.29** | `DELETE /v1/items/{itemId}` returns 204 and appends a duplicate event **every time** |
| ☐ | **X-11.27** | Declared status codes are wrong in both directions — ~30 unreachable 403s, 9 routes with no success code declared |
| ☐ | **X-11.19** | The archive cascade is synchronous in-request on dev/qa/staging and async on prod alone. **Closes as a side effect of the archive-cascade Tier 2 work** (`reviews/archive-cascade/archive-cascade-scale-review.md`), which converges both paths on async — decide it there rather than separately |
| ☐ | **X-11.34** 🔒 | Any tenant member can publish/archive/withdraw an item another user holds checked out. **Verified 2026-08-26**, with one correction: it is not *silent* — `EditSessionClosed` is emitted, persisted, published and projected, so it is auditable. What is missing is any user-facing notification, and on the archive path `closedBy` is `null`, so the record does not name who broke the lock. Withdraw reopens the session only from `PendingApproval`; archive never restores it. `ArchiveMediaItemCommand` carries no `RequestingUser` |
| ☐ | **X-11.25** | Nothing enforces the pre-signed upload deadline; the 15-minute TTL is a compiled constant |
| ☐ | **X-11.39 · X-11.43** | Counter drift — depth bypassable by subtree move; a stuck counter makes a folder permanently unarchivable with no visible cause |
| ☐ | **X-11.42 · X-11.32** | The assets of a deleted MediaItem can never be deleted. Belongs to `asset-custody` |
| ☑ | **X-11.15** | ~~Re-entrant cascade doing O(depth) work.~~ **Fixed 2026-08-27.** Phase 3 dispatches `ArchiveFolderNodeCommand`, so the cascade no longer re-enters itself; the guard runs once. Phase 2 bounded to 16 concurrent archives and the index reads batched at the same time. Same compile caveat |
| ☐ | **X-11.2 · X-11.3 · X-11.4** | Pre-existing, from the earlier drift pass |

### ⚪ Non-blocking — correctness of documentation and dead code

`X-11.8` · `X-11.9` · `X-11.10` · `X-11.11` · `X-11.12` · `X-11.13` · `X-11.14` · `X-11.20`
· `X-11.26` · `X-11.28` · `X-11.33` · `X-11.36` · `X-11.37` · `X-11.40`

*(**X-11.23 closed 2026-08-26** — moved to the Closed table below.)*

*(**X-11.1 closed 2026-08-25** — it was the last open item on the spec board. 145 references to ten invented projector class names across 28 files, rewritten to name the read-model table instead. The spec-drift plan is now complete end to end.)*

Mostly orphaned-but-registered commands, dead indexes, and code comments asserting behaviour the code
contradicts. **Cheap — they ride along with whatever PR touches the file.** Worth doing precisely because
each one is a trap for the next reader.

### ☑ Closed

| # | Outcome |
|---|---|
| X-11.7 | **Not a defect** — the processing worker is unwired deliberately; its queues are not active and the pipeline is a pass-through stub. *Carry forward: when the queues are activated, the saga success path has never actually run and needs an explicit test* |
| X-11.22 | **No security issue** — the token carries `client_id` and the platform's claims mapper normalises it to `tenant_id`. Nothing fails open. Docs corrected |
| X-11.45 | **Convention removed** — `LastObservedAtUtc` never existed; `ProjectedVersion` does the job |
| X-11.23 | **Fixed 2026-08-26** — the unreachable `403` declaration and its summary line deleted from both download endpoints. No check added: read access is tenant-scoped by design, and cross-tenant reads 404. Re-verified first — the only `Forbidden` in AssetManagement is write-side |

---

## Workstreams

The findings are not one job. Four groupings, each with different owners and tests:

| Workstream | Findings | Where it lives |
|---|---|---|
| **authorization** | X-11.30, 34, 35 (**31 and 23 closed**) | Planned in `../authorization/`. ADR + matrix are its evidence base, both current. **X-11.30 is blocked on `magiq-auth` issuing role claims** |
| **archive-cascade** | X-11.15–11.19, 11.41 (**16 and 18 closed 2026-08-27**) | Planned in `../archive-cascade/`. `docs/spec/contexts/Catalog/sagas/archive-fan-out.md` is the spec and is current |
| **event-reliability** | X-11.5, 11.44 (**11.6 closed 2026-08-27**) | Three routes to the same symptom: work and events disappear silently. **X-11.44 is blocked on an ADR-level decision** — see the gate row |
| **asset-custody** | X-11.32, 11.33, 11.42 | **Parked** — `reviews/asset-custody/` |
| **projection-rebuild** | X-11.44 (shared), counters, the seven indexes | **Parked** — `reviews/projection-rebuild/` |

---

## Decisions still owed

| # | Decision | Needed for |
|---|---|---|
| 1 | **Idempotency: adopt or retire?** The middleware is deployed and working; **nothing in the app sends the header**, and three code comments claim it does not exist. Fix the name and use it, or drop the package and table. The current state — docs and comments disagreeing about whether the feature exists — is the one option to rule out | X-11.21 |
| 2 | **Is tenant-wide read access the intended model?** Confirmed as intended for now, with per-resource control deferred to authorization. Recorded so it is a decision rather than a default | X-11.23 |
| 3 | **Is `Asset.OwnerId` custody or provenance?** Answered — custody, and it transfers on detach. Blocked on X-11.32 | asset-custody |
| 4 | **BI-1** — the bulk-import spec describes a feature with no code, no queues, no tables. Build it, delete the spec, or keep it badged as design? It owns **16 of the 17** remaining CI warnings | CI going green |
| 6 | ☑ **Answered 2026-08-27 (Chase): correct ADR-005 now, and let measurement choose the remedy.** ADR-005's dual-write paragraph is **corrected** — the loss is permanent not temporary, replay is not the safety net it claimed (6 of 10 aggregates, no indexes, neither counter), and the revisit trigger was conditioned on a measurement nothing takes. Also corrected: the platform `IOutbox` **cannot join the event-store transaction**, so adopting it as-shipped narrows the window rather than closing it — the old text promised "same transaction" and "exactly-once", neither of which is achievable. **X-11.44 stays open** as a known, accepted, unmeasured risk; the choice between the as-shipped outbox and a transaction-participating one waits on decision 7. **⚠ Update same day — "as-shipped" is not an option.** `reviews/event-reliability/outbox-implementation-review-2026-08-27.md` establishes that `Magiq.Platform.Messaging.Outbox` **has never been run**: zero adopters and zero tests platform-wide, **nothing invokes the drain**, and **sent messages are never marked sent** — so adopting it unchanged would re-publish every event on every drain, unboundedly. It also swallows its own enqueue failures, which is X-11.6's pattern inside the proposed fix. The remedy is a multi-item job in **`aspnetcore-platform`**, not here | **X-11.44** |
| 7 | **Who owns the projection-divergence metric?** Shared between `event-reliability` and `projection-rebuild` and unowned in both. **Promoted 2026-08-27 from "nice to have" to load-bearing:** decision 6 deliberately defers the outbox remedy until this exists, so X-11.44 cannot come off the gate without it. Comparing `ProjectedVersion` to aggregate version is small | **X-11.44** · the flags |
| 5 | **Should `ArchiveCollection` acquire the folder path's registration guard, or should the collection archive become a *request* the cascade can refuse?** Opened by the archive-cascade work on 2026-08-27. The guard is the smaller change and matches `ArchiveFolderHandler`; making it a request is the honest fix for the collection reading `archived` before its subtree is, but it changes the endpoint's contract. Until one is chosen, a collection holding retention-locked folders still reports archived | X-11.17 |

---

## Before flipping the flags

A short list of things that are *not* findings but would bite on day one:

- **The rebuild runbook has never been run where it would be needed.** It is explicitly a dev procedure, and
  dev projects synchronously — so it has only ever been exercised in an environment with no lag and no queue.
- **There is no alarm on projection lag** — no metric, no dashboard, nothing on `ApproximateAgeOfOldestMessage`.
  Divergence will be discovered, not detected. *(Now also decision 7 — it is what makes ADR-005's own
  revisit trigger capable of firing.)*
- **`media-sagas-dlq-depth` is about to fire for the first time.** X-11.6's fix means saga failures now
  reach the DLQ instead of vanishing. The alarm has never fired for an in-handler failure because it could
  not. **Its first firing is the fix working, not a new fault** — worth saying out loud before someone is
  paged by it.
- **Seven reference indexes cannot be rebuilt by replay at all**, and the two uniqueness counters cannot be
  rebuilt by anything. See `reviews/projection-rebuild/`.
- **`SagaOrchestrator.DocumentSigning` is built and pushed every commit and deployed nowhere.** Deliberate,
  but an operator watching image tags advance should not infer it is running.

---

## Related

- [`../spec-drift-review/spec-repo-drift-review.md`](../spec-drift-review/spec-repo-drift-review.md) —
  every finding in full, with evidence. **The source of truth; this file only triages it**
- [`../spec-drift-review/spec-ddd-coverage-review-2026-08-24.md`](../spec-drift-review/spec-ddd-coverage-review-2026-08-24.md)
  — the spec board, all 31 units complete
- `../../reviews/asset-custody/` · `../../reviews/projection-rebuild/` — the two parked code workstreams
- `docs/spec/shared/authorization-matrix.md` (magiq-media repo) — the evidence base for the two blockers
