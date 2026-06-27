# ADR-006: Uniqueness Registry Counters for Strongly-Consistent Hierarchy Invariants

**Status:** Accepted
**Date:** 2026-04-30
**Deciders:** Chase Ramone

---

## Context

`ArchiveFolderHandler` must enforce two invariants before archiving a folder:

1. The folder has no active child folders.
2. The folder has no active media items.

The originally specified design called for `IFolderDomainService.HasActiveChildrenAsync` to read from two projection indexes — `FolderChildCountIndex` and `FolderActiveItemCountIndex` — maintained by event-driven projectors. **Correction (2026-06-17): these two projectors were never implemented.** A repo-wide grep of `magiq-media` finds zero hits for either name; the corresponding CDK table (`media-catalog-folder-active-item-count-index`) was provisioned but never registered via `AddProjectionSchema<T>` and has since been removed as dead infrastructure. The risk described below — eventual-consistency lag between a projector and a concurrent `ArchiveFolder` read — was therefore a design-time concern, not an observed production gap; the counter-based design in this ADR was implemented directly, and the projection-based path was superseded before it was ever built.

Had the projection-based design been implemented, it would have created a window where a concurrent `CreateFolder` or `AssignMediaItemToFolder` command could succeed, the projector had not yet incremented the count, and a concurrent `ArchiveFolder` read zero and incorrectly proceeded — a folder archived with active children, a hierarchy corruption that cannot be self-healed because the child events still exist in the event store but the parent is now archived. This risk motivates the strongly-consistent counter design below.

The Catalog write model already uses `Magiq.Platform.UniquenessRegistry` (via `INameReservationService`) for strongly-consistent name uniqueness enforcement on the same DynamoDB table. Version 1.1.0 of the platform package extends this with `IUniquenessCounterService`, which provides atomic counter operations backed by DynamoDB `UpdateItem` with ADD expressions — the same underlying table, different sort-key prefix (`counter#` vs `reservation#`).

---

## Decision

**Hierarchy invariant checks in `ArchiveFolderHandler` use `IUniquenessCounterService.CounterIsZeroAsync` instead of the eventually-consistent projection reads.**

Each command handler that creates or removes folder children or media items atomically increments or decrements the appropriate counter as part of its execution path — adjacent to the existing `INameReservationService` call it already makes. DynamoDB `UpdateItem` with the ADD expression provides atomic increment/decrement with no read required.

### Counter schema

Counters share the same DynamoDB table as name reservations using a distinct sort-key prefix:

```
PK: <tenantId>
SK: counter#<scope>#<counterName>
Attribute: Count (N)
```

### Counter assignments

| Counter | Scope key | Incremented by | Decremented by |
|---|---|---|---|
| `child-folders` | `ScopeKeys.Folder(parentFolderId)` or `ScopeKeys.RootFolder(collectionId)` | `CreateFolderHandler` | `ArchiveFolderHandler`, `MoveFolderHandler` (old parent) |
| `child-folders` | `ScopeKeys.Folder(newParentFolderId)` | `MoveFolderHandler` (new parent) | — |
| `active-items` | `ScopeKeys.Folder(folderId)` | `CreateMediaItemHandler`, `AssignMediaItemToFolderHandler`, `MoveMediaItemHandler` (new folder) | `ArchiveMediaItemHandler`, `MoveMediaItemHandler` (old folder) |
| `active-registrations` | `ScopeKeys.MediaItemRegistrations(mediaItemId)` | `AddRegistrationRefHandler` | `RemoveRegistrationRefHandler` |

### `ArchiveFolderHandler` guard

```csharp
var folderScope = ScopeKeys.Folder(command.FolderId);

if (!await counterService.CounterIsZeroAsync(command.TenantId, folderScope, "child-folders", ct))
    return InvalidOperation("Folder has active child folders.");

if (!await counterService.CounterIsZeroAsync(command.TenantId, folderScope, "active-items", ct))
    return InvalidOperation("Folder has active media items.");
```

Both checks are strongly consistent — they are point reads against DynamoDB, which provides read-your-writes consistency within a partition.

### `IFolderDomainService.HasActiveChildrenAsync`

Never added to the interface — the projection-backed implementation described in Context was superseded before it was built (see correction above). There is no advisory/diagnostic `HasActiveChildrenAsync` available on `FolderDomainService` today; admin tooling and bootstrap-period validation against legacy projections are not currently possible and would require building that read path from scratch if needed.

### Registration counters

`active-registrations` is tracked per media item (not per folder). It is used in `HasActiveRegistrationsInSubtreeAsync` to surface a **non-blocking warning** in `ArchiveFolderResult` — it does not gate the archive operation. This is intentional: registration lifecycle is owned by the Registration bounded context; blocking folder archive on registration state would couple the Catalog write model to an external BC.

### Sequencing and failure window

Counter increments run sequentially after the name reservation call and before the aggregate save. There is a failure window between the two DynamoDB writes (reservation + counter) that cannot be closed without transactional support. Until `ITransactionalUniquenessRegistry` is introduced (deferred to a follow-up ADR), callers handle failures via idempotent command replay — re-running the handler will re-attempt the counter increment, and the reservation check will short-circuit if already held.

DynamoDB ADD on a missing numeric attribute initialises it to 0 before adding, so counters do not require explicit bootstrap for new resources. Existing resources require a one-off bootstrap (see consequences).

### Projector indexes — correction: not implemented

This ADR originally claimed `FolderChildCountIndex`, `FolderActiveItemCountIndex`, and `MediaItemRegistrationCountIndex` "continue to be maintained by projectors" and back the BFS traversal in `HasActiveRegistrationsInSubtreeAsync`. **None of the three exist in `magiq-media`** — confirmed by repo-wide grep, zero hits for all three names. `HasActiveRegistrationsInSubtreeAsync` is implemented and does run a BFS traversal, but it is backed by `catalogFolderRegistrationIndex` (`media-catalog-folder-registration-index`, maintained by the real `RegistrationCountIndexProjector` registered in `Catalog.WriteModel.Infrastructure`) — a different, genuinely-implemented index, not the three named above. There is no separate advisory/diagnostic read path for child-folder or active-item counts; the counters in this ADR are the only mechanism enforcing those two invariants.

---

## Consequences

**Positive:**
- Archive invariant enforcement is **strongly consistent**. No window where a concurrent create slips past the archive gate.
- Counter reads are **single DynamoDB point reads** — no cross-table join, no BFS traversal, no projection lag dependency.
- **Eliminates the read-modify-write cycle** in `ArchiveFolderHandler`. The old implementation read two projection rows; the new one reads two counter rows that are always current.
- `ISkipReadProjectionHandler` is added to all count projectors, eliminating the `GetAsync` round-trip for projectors that only emit atomic results (10 projectors affected).

**Negative / Accepted trade-offs:**
- **Bootstrap required for existing tenants.** Counter records do not exist for pre-existing folders or media items. A one-off Lambda replays aggregate state (or reads projection table point-in-time) to seed counter values before the counter guards in command handlers are activated in production. Until bootstrap is complete, the old `HasActiveChildrenAsync` path or a feature flag gates which check runs.
- **Sequential DynamoDB calls, not atomic.** Reservation + counter increment are two separate calls. If the counter increment fails after a successful reservation, the counter is under-reported until a compensating replay corrects it. This is accepted until transactional support (`ITransactionalUniquenessRegistry`) is designed.
- **Counter drift on Lambda failure between writes.** If the Lambda crashes between reservation and counter increment (or between counter and aggregate save), the counter may be stale. This is mitigated by idempotent command replay: re-running the command will retry the sequence; the reservation check short-circuits if already held. A CloudWatch alarm on negative counter values serves as a safety net.
- **Domain guarantees required for decrement correctness.** DynamoDB ADD with a negative delta can produce a negative count if a decrement runs against a row that never received the corresponding increment (bootstrap interleaving). The domain guarantees that every Archive or Remove has exactly one corresponding Create or Add — the counter will not go negative in steady state. No floor-at-zero is enforced in the store.

**Not chosen — keep `HasActiveChildrenAsync` backed by projection indexes:**
- Simpler, requires no counter infrastructure, but leaves the eventual consistency window open. Any sufficiently concurrent workload (parallel creates racing an archive) can corrupt hierarchy. Rejected on consistency grounds.

**Not chosen — pessimistic locking / conditional writes on the aggregate:**
- DynamoDB does not support range-scan conditions on the event store partition without a GSI. Adding a "children" aggregate would require cross-aggregate transactions, which violates the aggregate boundary rule. Rejected on architectural grounds.

**Not chosen — two-phase check (read projection, then re-check after a delay):**
- Introduces artificial latency, does not eliminate the race — only narrows it. Rejected as complexity without correctness guarantee.

---

## Review Trigger

Revisit when: (a) `ITransactionalUniquenessRegistry` is designed — at that point, reservation + counter increment should be collapsed into a single `TransactWriteItems` call, eliminating the failure window; (b) counter bootstrapping is complete for all tenants and `HasActiveChildrenAsync` is removed from `FolderDomainService`; (c) a CloudWatch alarm fires on negative counter values — investigate and replay the affected aggregate to correct drift.
