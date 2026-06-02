# Bulk Operations — Shared Conventions

_Applies to all bulk write endpoints in the Catalog and AssetManagement contexts._

---

## Overview

Bulk endpoints process multiple media-items in a single HTTP call. They follow a **partial-success model**: processing continues across all media-items even if some fail (unless `onError = FailFast`). Every response accounts for every media-item in the request.

---

## Response Envelope

All bulk endpoints return the same typed envelope:

```json
{
  "succeeded": [ ... ],
  "failed":    [ ... ],
  "skipped":   [ ... ]
}
```

**Status codes:**

| Condition | Status |
|---|---|
| All media-items succeeded (`failed` and `skipped` both empty) | `201 Created` |
| At least one media-item failed or was skipped | `202 Accepted` |
| Request-level failure (quota exceeded, circular dependency, invalid batch) | `400 Bad Request` |

---

## BulkItemError

Appears in the `failed` array. Each entry identifies the position and reason for the failure.

```json
{
  "index": 2,
  "name": "Season 1",
  "errorCode": "DuplicateName",
  "message": "A media-folder named 'Season 1' already exists under this parent.",
  "suggestedName": "Season 1 (1)"
}
```

| Field | Notes |
|---|---|
| `index` | 0-based position in the request `items` array |
| `name` | Human-readable identifier (name, title, or fileName depending on resource) |
| `errorCode` | Machine-readable code — see per-endpoint error taxonomy |
| `message` | Human-readable description |
| `suggestedName` | Only present when `errorCode = "DuplicateName"` and `onDuplicate = "Reject"`. Server-computed available alternative. |

---

## BulkItemSkipped

Appears in the `skipped` array when `onDuplicate = "Skip"`.

```json
{
  "index": 2,
  "name": "Season 1",
  "reason": "DuplicateName"
}
```

---

## `onError` — Error Mode

Controls whether processing halts on first failure or continues across all media-items.

| Value | Behaviour |
|---|---|
| `ContinueOnError` *(default)* | Process all media-items; accumulate failures; return partial results |
| `FailFast` | Pre-flight only; if any media-item would fail, abort before writing anything and return the failure list |

Under `FailFast`, the `succeeded` list is always empty — the endpoint is all-or-nothing.

---

## `onDuplicate` — Name Conflict Strategy

Applies to Collections, Folders, and MediaItems (not Assets, which have no name-uniqueness constraint).

| Value | Behaviour |
|---|---|
| `Reject` *(default)* | Item goes to `failed` with `errorCode = "DuplicateName"` and a `suggestedName` if one is available |
| `Skip` | Item goes to `skipped`. No error raised. Useful for idempotent re-runs |
| `AutoSuffix` | Server appends ` (1)`, ` (2)`, … until a free name is found (up to 99 attempts). If exhausted → `failed` with `errorCode = "AutoSuffixExhausted"` |

> **Note on `Skip`:** The server only checks name collision — it does not verify that the existing resource has matching properties. Use `Reject` when semantic correctness matters.

---

## Name Uniqueness — Two-Tier Check

Bulk endpoints implement the same two-tier uniqueness guarantee as single-item create:

1. **Tier 1 (pre-flight):** Single `DynamoDB BatchGetItem` across all names in the batch (ConsistentRead=true). Batches exceeding 100 names are split into multiple parallel calls.
2. **Tier 2 (write-time):** Atomic `INameReservationService.ReserveAsync` per media-item. Conflicts at this tier (concurrent writers) are retried up to `BulkOperationsOptions.MaxRetryAttemptsPerItem` (default 3) with exponential back-off before the media-item is recorded as `Failed` with `errorCode = "NameReservationFailed"`.

---

## Within-Batch Duplicate Detection

Before the Tier 1 DynamoDB check, the handler scans the request itself for duplicate names within the same scope (normalised: `Trim().ToLowerInvariant()`). Intra-batch duplicates are subject to the same `onDuplicate` strategy as external conflicts.

---

## Batch Size Limits

Enforced by the endpoint before the command is dispatched. Exceeding the limit returns `400` immediately.

| Resource | Default cap | Config key (`BulkOperations`) |
|---|---|---|
| Collections | 100 | `MaxCollectionsPerRequest` |
| Folders | 200 | `MaxFoldersPerRequest` |
| Assets (upload + confirm) | 50 | `MaxAssetsPerRequest` |
| Media Items | 200 | `MaxMediaItemsPerRequest` |

All caps are tunable via `appsettings.json` `BulkOperations` section without code changes.

---

## Write-Phase Concurrency

All bulk handlers use `Parallel.ForEachAsync` with `MaxDegreeOfParallelism = BulkOperationsOptions.WritePhaseMaxDegreeOfParallelism` (default 10). This bounds DynamoDB throughput and Lambda memory pressure while providing ~10× throughput versus serial processing.

---

## Idempotency

Bulk endpoints honour the `IdempotencyKey` header. The platform middleware caches the entire response envelope for the TTL window. A replayed key with the same payload returns the cached envelope without re-processing.

All bulk endpoints accept caller-generated IDs (UUID v7). Re-submitting a failed media-item with the **same ID** is safe — the event store's `attribute_not_exists(AggregateVersion)` conditional write treats a pre-existing aggregate as a no-op success. Re-submitting with a **corrected name** requires a **new ID** (the original ID was never persisted).

---

## Re-Submission Pattern

Failed media-items can be re-submitted in isolation without re-sending the full original batch:

```
POST /media-collections/bulk
{
  "items": [ <only the previously failed media-items, with corrected names> ],
  "onError": "ContinueOnError"
}
```

---

## Related

- [api-conventions.md](./api-conventions.md) — idempotency, error contract, auth
