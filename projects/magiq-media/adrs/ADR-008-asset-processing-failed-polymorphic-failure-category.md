# ADR-008: `AssetProcessingFailed` — Polymorphic Failure via `FailureCategory`

**Status:** Accepted  
**Date:** 2026-05-16  
**Deciders:** Chase Ramone

---

## Context

The asset ingestion pipeline can fail at two distinct stages, from two distinct aggregate states:

1. **Validation stage** — asset is `Validating`. Failures here are caused by upload expiry, validation timeout, or a format/size violation caught by the validation worker.
2. **Processing stage** — asset is `Processing`. Failures here are caused by a processing worker crash, a MediaConvert job error, or a processing timeout.

When implementing the `FailAssetProcessing` aggregate method and the `AssetProcessingFailed` domain event, the question arose: should there be a single event covering both stages, or two separate events (`AssetValidationFailed` is already taken by the domain-visible validation failure — format/virus — path)?

### Options Considered

**Option A: Two separate domain events**
- `AssetValidationStageFailed` (emitted from `Validating` state)
- `AssetProcessingFailed` (emitted from `Processing` state)

**Option B: Single `AssetProcessingFailed` event with a `FailureCategory` discriminator**

`FailureCategory` carries enough information to:
- Identify which pipeline stage failed
- Drive the appropriate compensation path in the saga
- Surface a meaningful failure reason to callers via the read model

The aggregate's `FailProcessing` method enforces which categories are valid from which state:

```csharp
// Validating → allowed categories
ValidationError, UploadExpired, ValidationTimeout

// Processing → allowed categories  
ProcessingTimeout, ProcessingError
```

---

## Decision

Use **Option B** — a single `AssetProcessingFailed` event with a `FailureCategory` discriminator field.

The aggregate enforces the state/category invariant at write time:

```csharp
public Result<Unit, DomainError> FailProcessing(FailureCategory category, string reason)
{
    if (Status == AssetStatus.Validating &&
        category is FailureCategory.ValidationError or FailureCategory.UploadExpired or FailureCategory.ValidationTimeout)
    {
        Raise(new AssetProcessingFailed(AssetId, category, reason));
        return Result.Ok();
    }

    if (Status == AssetStatus.Processing &&
        category is FailureCategory.ProcessingTimeout or FailureCategory.ProcessingError)
    {
        Raise(new AssetProcessingFailed(AssetId, category, reason));
        return Result.Ok();
    }

    return DomainError.InvalidOperation(
        $"FailureCategory '{category}' is not valid from status '{Status}'.");
}
```

Both code paths produce the same terminal status (`ProcessingFailed`) and the same event type. Downstream consumers (sagas, projectors, integration event publishers) switch on `FailureCategory` to differentiate compensation behaviour.

### `FailureCategory` Values

| Value | Valid from state | Cause | Compensation |
|---|---|---|---|
| `ValidationError` | `Validating` | Format check or size violation detected by validation worker | No retry; asset marked permanently failed; owner notified |
| `UploadExpired` | `Validating` | S3 presigned URL TTL elapsed; no object uploaded | No retry; owner must re-upload |
| `ValidationTimeout` | `Validating` | Saga timeout: validation did not complete within the 30-minute window | `AssetIngestionSaga` dispatches timeout compensation; owner may retry |
| `ProcessingTimeout` | `Processing` | Saga timeout: processing did not complete within the 30-minute window | `AssetIngestionSaga` dispatches timeout compensation; owner may retry |
| `ProcessingError` | `Processing` | Processing worker or MediaConvert job failed with a non-retriable error | No automatic retry; operator inspection required |

---

## Consequences

**Positive:**
- Single event type simplifies projector and saga handler registration — one handler per consumer rather than two.
- `FailureCategory` is a stable discriminator that can be extended with new categories (additive — no schema version bump) without introducing a new event type.
- The aggregate's invariant check ensures `FailureCategory` is always consistent with the aggregate state at write time — no invalid combinations reach the event store.
- Integration event publishers can map `FailureCategory` to structured failure metadata for downstream consumers (Notifications, Billing) without requiring those consumers to understand aggregate state.

**Negative / Trade-offs:**
- Projectors and saga handlers that only care about one stage must filter on `FailureCategory`. This is a minor nuisance but acceptable — the filter is a single switch statement.
- The `AssetStatus` transition is identical (`→ ProcessingFailed`) regardless of category, which means the read model cannot distinguish validation failures from processing failures by status alone. Projectors must denormalise `FailureCategory` into the read model if callers need to surface this distinction.

**Decision:** Denormalise `FailureCategory` into the `media-asset-detail` read model as `failureCategory: string | null`. This gives the Query API enough information to return a structured failure reason without requiring callers to re-query the event store.
