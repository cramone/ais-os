# MediaItem Checkout + CR-First Saga Design

_Context: `Catalog` + `ChangeRequests`_
_Status: Design — not yet implemented_

---

## Decision

CR intent is declared at **checkout time**. Actor decides upfront:
- Solo checkout (no CR) — only the checkout actor can checkin; auto-approves on submit
- CR checkout — CR created immediately; any CR participant can checkin; review cycle on submit

See: [decisions/log.md — CR-First Checkout Model](../../../../../decisions/log.md)

---

## Command Changes

### `CheckOutMediaItemCommand` (modified)

```csharp
record CheckOutMediaItemCommand(
    MediaItemId MediaItemId,
    bool WithChangeRequest,
    IReadOnlyList<UserId> ReviewerIds  // required when WithChangeRequest = true; may be empty if self-review is permitted
);
```

**Handler behaviour:**
1. Load MediaItem aggregate
2. Validate `CheckoutPolicy` and `CheckInOut` capability (existing)
3. If `WithChangeRequest = true`:
   - Validate `ReviewerIds` non-empty (unless self-review allowed — TBD)
   - Pre-generate `MediaChangeRequestId` (UUIDv7)
   - Call `IMediaChangeRequestService.CreateCheckoutChangeRequestAsync(tenantId, mediaItemId, mcrId, reviewerIds)` — creates CR in `Open` state, bound to this checkout (not to a submission)
   - Call `mediaItem.CheckOut(userId, mcrId)` — records both `CheckedOutBy` and `ActiveMediaChangeRequestId`
4. If `WithChangeRequest = false`:
   - Call `mediaItem.CheckOut(userId, mcrId: null)` — solo lock

---

## Aggregate Changes

### New property: `CheckoutChangeRequestId`

```csharp
MediaChangeRequestId? CheckoutChangeRequestId  // set at checkout, cleared at checkin/abandon
```

Distinct from `ActiveMediaChangeRequestId` (which is set at submit time). These may be the same CR or separate — see flow below.

> **Design note:** Simplest approach — `CheckoutChangeRequestId` IS the CR that will be used at submit time. No second CR created. At submit, if `CheckoutChangeRequestId` is set, that CR ID is reused.

### Updated invariants

| Rule | Error | Command |
|---|---|---|
| No CR → actor must be `CheckedOutBy` to checkin | `NotCheckedOutByUser` | `CheckInMediaItem` |
| With CR → actor must be a CR participant to checkin | `NotChangeRequestParticipant` | `CheckInMediaItem` |
| `CheckoutChangeRequestId` set → CR already exists at submit time | — | `SubmitForReview` |

### `CheckOut` method (modified)

```csharp
void CheckOut(UserId userId, MediaChangeRequestId? checkoutCrId)
// Raises: MediaItemCheckedOut { CheckedOutBy, CheckedOutAt, CheckoutChangeRequestId? }
```

### `CheckIn` method (modified)

```csharp
void CheckIn(UserId userId)
// Guard: if CheckoutChangeRequestId == null → userId must == CheckedOutBy
//        if CheckoutChangeRequestId != null → userId must be CR participant (validated by handler)
// Raises: MediaItemCheckedIn { CheckedInBy, CheckedInAt }
```

---

## Handler Changes

### `CheckInMediaItemHandler` (modified)

```csharp
// Additional pre-condition when CheckoutChangeRequestId is set:
if (mediaItem.CheckoutChangeRequestId.HasValue)
{
    var participants = await _mcrQueryService.GetParticipantsAsync(tenantId, mediaItem.CheckoutChangeRequestId.Value, ct);
    if (!participants.Contains(caller.Sub))
        return Result.Failure(new NotChangeRequestParticipant());
}
```

### `SubmitForReviewHandler` (modified)

Current: creates a new CR when `ReviewPolicy = RequiredForPublish`.

New behaviour:

```
if (mediaItem.CheckoutChangeRequestId != null)
    → reuse CheckoutChangeRequestId as the submission CR
    → transition CR from checkout-bound → submission-bound (new CR command: ActivateForReview?)
    → call mediaItem.SubmitForReview(checkoutCrId)
else if (ReviewPolicy == RequiredForPublish)
    → error: cannot submit for review without a CR checkout (CR-first model enforces this)
else (ReviewPolicy == None)
    → auto-approve path (unchanged)
```

> **Decision:** `ReviewPolicy = RequiredForPublish` enforced at **checkout**. `CheckOutMediaItemHandler` rejects `WithChangeRequest = false` for profiles with `RequiredForPublish`. Actor must provide reviewers to proceed.

---

## New CR State: `CheckoutBound` → `SubmissionBound`

The CR lifecycle gains an intermediate state:

```
CheckoutBound  ← created at checkout
    │
    │  ActivateForReview (triggered by SubmitForReview)
    ▼
SubmissionBound → [existing review cycle: Approved / Rejected / Abandoned]
```

Alternative: skip the state distinction and just use `Open` for both phases. Simpler but loses auditability of when the CR transitioned from "change in progress" to "under review". **Recommend separate states.**

---

## Event Changes

### `MediaItemCheckedOut` (modified)

```csharp
record MediaItemCheckedOut(
    MediaItemId MediaItemId,
    UserId CheckedOutBy,
    DateTimeOffset CheckedOutAt,
    MediaChangeRequestId? CheckoutChangeRequestId  // new
);
```

---

## Saga: `MediaItemCheckoutReviewSaga` (new)

Coordinates the checkout CR lifecycle. Separate from `MediaItemReviewSaga` (which handles submit → approve/reject).

### Correlation

Correlated on `CheckoutChangeRequestId` / `MediaChangeRequestId`. Saga instance created per unique checkout CR.

### State Machine

| State | Trigger | Action | Next State |
|---|---|---|---|
| _(start)_ | `MediaItemCheckedOut` (CheckoutChangeRequestId set) | Dispatch `CreateCheckoutChangeRequestCommand` | `AwaitingCheckin` |
| `AwaitingCheckin` | `MediaItemCheckedIn` | No dispatch — checkin recorded | `AwaitingSubmission` |
| `AwaitingCheckin` | `MediaItemCheckoutAbandoned` | Dispatch `AbandonChangeRequestCommand(reason: "CheckoutAbandoned")` | `CrAbandoned` [terminal] |
| `AwaitingCheckin` | `MediaItemCheckoutForceReleased` | Dispatch `AbandonChangeRequestCommand(reason: "CheckoutForceReleased")` | `CrAbandoned` [terminal] |
| `AwaitingSubmission` | `MediaItemSubmittedForReview` (matching CR) | No dispatch — `MediaItemReviewSaga` takes over via `ActivateChangeRequestForReview` | `HandedToReviewSaga` [terminal] |
| `AwaitingSubmission` | `MediaItemCheckoutForceReleased` | Dispatch `AbandonChangeRequestCommand(reason: "CheckoutForceReleased")` | `CrAbandoned` [terminal] |

> **Note:** `AwaitingSubmission` has no timeout. CR stays `CheckoutBound` indefinitely until actor submits or an admin force-releases. See [decisions/log.md — Checkin Without Submit Requires Explicit Abandon](../../../../../decisions/log.md).

### Terminal States

| State | Meaning |
|---|---|
| `HandedToReviewSaga` | Submit received — `MediaItemReviewSaga` owns the CR from here |
| `CrAbandoned` | Checkout abandoned or force-released — CR terminal, MediaItem available |

### Saga Data

```csharp
record MediaItemCheckoutReviewSagaData(
    string SagaId,
    string TenantId,
    string MediaItemId,
    string CheckoutChangeRequestId,
    string CheckedOutBy,
    string SagaState        // AwaitingCheckin | AwaitingSubmission | HandedToReviewSaga | CrAbandoned
);
```

### Integration Event Subscriptions

| Event | SNS Message Type | Handler |
|---|---|---|
| `MediaItemCheckedOutMessage` (CheckoutChangeRequestId set) | `media.mediaitem.checked-out` | `MediaItemCheckedOutCheckoutSagaHandler` — starts saga, dispatches `CreateCheckoutChangeRequestCommand` |
| `MediaItemCheckedInMessage` | `media.mediaitem.checked-in` | `MediaItemCheckedInCheckoutSagaHandler` — transitions `AwaitingCheckin → AwaitingSubmission` |
| `MediaItemCheckoutAbandonedMessage` | `media.mediaitem.checkout-abandoned` | `MediaItemCheckoutAbandonedSagaHandler` — dispatches abandon, terminates |
| `MediaItemCheckoutForceReleasedMessage` | `media.mediaitem.checkout-force-released` | `MediaItemCheckoutForceReleasedSagaHandler` — dispatches abandon, terminates |
| `MediaItemSubmittedForReviewMessage` (CheckoutChangeRequestId set) | `media.mediaitem.submitted-for-review` | `MediaItemSubmittedCheckoutSagaHandler` — transitions to `HandedToReviewSaga`, terminates |

---

## `MediaItemReviewSaga` (unchanged paths, one new entry point)

Existing fast path (`ReviewPolicy = None`) and review path (`ReviewPolicy = RequiredForPublish`) unchanged.

New entry: when `SubmitForReview` carries a pre-existing `CheckoutChangeRequestId`, saga is correlated to that CR ID rather than creating a new one. The `ActivateForReview` command transitions the CR from `CheckoutBound → SubmissionBound` and notifies reviewers.

---

## Resolved Design Decisions

| # | Question | Decision |
|---|---|---|
| 1 | Self-review with CR | No — reviewer ≠ initiator, hard rule enforced at checkout. `ReviewerIsInitiator` error. |
| 2 | Checkin without submit | Explicit abandon only. No timeout, no auto-abandon. CR stays `CheckoutBound` until actor or admin acts. |
| 3 | ForceReleaseCheckout with active CR | Auto-abandon CR. `ForceReleaseCheckout` always abandons `CheckoutChangeRequestId` CR if present. |
| 4 | ReviewPolicy enforcement point | Enforce at **checkout**. `CheckOutMediaItemHandler` reads `ReviewPolicy`; `RequiredForPublish` + `WithChangeRequest = false` = hard reject. |

---

## Files to Update

| File | Change |
|---|---|
| `mediaitem.write-model.md` | Add `CheckoutChangeRequestId` property, update `CheckOut`/`CheckIn` methods and invariants, update `MediaItemCheckedOut` event |
| `mediaitem.api.md` | Update `POST /checkout` request body with `withChangeRequest` + `reviewerIds` |
| `ChangeRequests/context-overview.md` | Add `CheckoutBound` CR state, new `ActivateForReview` command, `MediaItemCheckoutReviewSaga` |
| `ChangeRequests/aggregates/MediaChangeRequest/mediachangerequest.write-model.md` | Add `CheckoutBound` state, `ActivateForReview` command/event |
| `Catalog/business-scenarios.md` | Add CR-first checkout scenarios |

---

## Related

- [decisions/log.md — CR-First Checkout Model](../../../../../decisions/log.md)
- [MediaItem Write Model](./mediaitem.write-model.md)
- [ChangeRequests Context Overview](../../../ChangeRequests/context-overview.md)
- [MediaChangeRequest Write Model](../../../ChangeRequests/aggregates/MediaChangeRequest/mediachangerequest.write-model.md)
