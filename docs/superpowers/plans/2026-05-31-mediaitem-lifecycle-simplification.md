# MediaItem Lifecycle Simplification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Checkout/ChangeRequest/Auto-revert lifecycle with a simpler Draft → UnderReview → Published model using an embedded ReviewSession on MediaItem.

**Architecture:** Remove CheckoutStatus, all checkout methods, the cross-module ChangeRequest lifecycle, and the MediaItemReviewSaga. Embed reviewer assignments and decisions directly in MediaItem as a `ReviewSession` value object. Simplify ChangeRequest aggregate to a comment-only thread. No backwards compatibility required — no production release exists.

**Tech Stack:** C# / .NET, event sourcing (event-raised-then-applied pattern), XUnit + Moq, MediatR command handlers.

---

## New Model Summary

**MediaItemStatus:** `Draft | UnderReview | Published | Archived` (remove `Rejected`, `SubmissionFailed`, `Withdrawn`)

**Removed from MediaItem:**
- `CheckoutStatus`, `CheckedOutBy`, `CheckoutChangeRequestId`, `ActiveMediaChangeRequestId`
- Auto-revert logic (`AutoRevertIfNeeded`, `MediaItemRevertedToDraft` event)
- `Metadata.Draft` lazy init — replaced with explicit rotation on Approve
- Methods: `CheckOut`, `CheckIn`, `AbandonCheckout`, `ForceReleaseCheckout`, `Withdraw`

**Added to MediaItem:**
- `_activeReview` (nullable `ReviewSession`) — holds reviewer list and their decisions
- `ApproveReview(MemberId, DateTimeOffset)` — reviewer casts approval vote; auto-publishes when all approve
- `RejectReview(MemberId, string reason, DateTimeOffset)` — any rejection returns item to Draft immediately
- `SubmitForReview` — simplified: no CR ID pre-gen, no integration event to ChangeRequests; if no reviewers → inline auto-approve

**Removed ChangeRequest aggregate lifecycle:** Status, Binding, reviewer tracking, sagas all deleted. ChangeRequest becomes a comment-only thread referenced by ID from MediaItem's ReviewSession.

---

## File Map

### New files
| File | Purpose |
|---|---|
| `src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/ValueObjects/ReviewSession.cs` | Embedded value object: ReviewSessionId, reviewer list, decisions |
| `src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/ValueObjects/ReviewerAssignment.cs` | Per-reviewer: MemberId, ReviewerDecision, timestamps |
| `src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/ValueObjects/ReviewerDecision.cs` | Enum: Pending \| Approved \| Rejected \| Withdrawn |
| `src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/ValueObjects/ReviewSessionId.cs` | Strongly-typed ID |
| `src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/Events/ReviewerApproved.cs` | Domain event: one reviewer approved |
| `src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/Events/ReviewerRejected.cs` | Domain event: one reviewer rejected |
| `src/modules/Catalog/Catalog.WriteModel/Commands/MediaItems/ApproveReview/ApproveReviewCommand.cs` | Command |
| `src/modules/Catalog/Catalog.WriteModel/Commands/MediaItems/ApproveReview/ApproveReviewHandler.cs` | Handler |
| `src/modules/Catalog/Catalog.WriteModel/Commands/MediaItems/RejectReview/RejectReviewCommand.cs` | Command |
| `src/modules/Catalog/Catalog.WriteModel/Commands/MediaItems/RejectReview/RejectReviewHandler.cs` | Handler |
| `tests/modules/Catalog/Catalog.WriteModel.Tests/MediaItems/Commands/ApproveReviewHandlerTests.cs` | Tests |
| `tests/modules/Catalog/Catalog.WriteModel.Tests/MediaItems/Commands/RejectReviewHandlerTests.cs` | Tests |

### Modified files
| File | Change |
|---|---|
| `src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/ValueObjects/MediaItemStatus.cs` | Remove Rejected, SubmissionFailed, Withdrawn |
| `src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/MediaItem.cs` | Major — see tasks below |
| `src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/Events/MediaItemSubmittedForReview.cs` | Add ReviewSessionId, reviewer IDs; remove CR ID pre-gen |
| `src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/Events/MediaItemApproved.cs` | Remove CR dependency |
| `src/modules/Catalog/Catalog.WriteModel/Commands/MediaItems/SubmitForReview/SubmitForReviewHandler.cs` | Remove CR ID pre-gen, remove integration events |
| `src/modules/Catalog/Catalog.WriteModel/Commands/MediaItems/ApproveMediaItem/ApproveMediaItemHandler.cs` | Remove IMediaChangeRequestQueryService dependency |
| `src/modules/ChangeRequests/ChangeRequests.Domain/Aggregates/Media/ChangeRequest.cs` | Strip to comment-only aggregate |
| `src/modules/ChangeRequests/ChangeRequests.Domain/ValueObjects/ChangeRequestStatus.cs` | Delete or replace with IsDeleted bool |
| `tests/modules/Catalog/Catalog.WriteModel.Tests/MediaItems/Commands/ApproveMediaItemHandlerTests.cs` | Remove CR service mock |
| `tests/modules/Catalog/Catalog.WriteModel.Tests/MediaItems/Commands/SubmitForReviewHandlerTests.cs` | Remove CR ID pre-gen assertions |

### Deleted files
```
# Checkout domain events
src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/Events/MediaItemCheckedOut.cs
src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/Events/MediaItemCheckedIn.cs
src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/Events/MediaItemCheckoutAbandoned.cs
src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/Events/MediaItemCheckoutForceReleased.cs
src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/Events/CheckInRequested.cs
src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/Events/MediaItemRevertedToDraft.cs
src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/Events/MediaItemSubmissionFailed.cs
src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/Events/ChangeRequestLinked.cs
src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/Events/ChangeRequestUnlinked.cs

# Checkout value objects
src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/ValueObjects/CheckoutStatus.cs
src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/ValueObjects/CheckoutMemberId.cs

# Checkout handlers
src/modules/Catalog/Catalog.WriteModel/Commands/MediaItems/CheckOutMediaItem/CheckOutMediaItemHandler.cs
src/modules/Catalog/Catalog.WriteModel/Commands/MediaItems/CheckInMediaItem/CheckInMediaItemHandler.cs
src/modules/Catalog/Catalog.WriteModel/Commands/MediaItems/AbandonCheckout/AbandonCheckoutHandler.cs
src/modules/Catalog/Catalog.WriteModel/Commands/MediaItems/ForceReleaseCheckout/ForceReleaseCheckoutHandler.cs
src/modules/Catalog/Catalog.WriteModel/Commands/MediaItems/LinkChangeRequest/LinkChangeRequestHandler.cs
src/modules/Catalog/Catalog.WriteModel/Commands/MediaItems/UnlinkChangeRequest/UnlinkChangeRequestHandler.cs

# CR query services (no longer needed by Catalog)
src/modules/Catalog/Catalog.WriteModel/Services/MediaItems/IMediaChangeRequestQueryService.cs
src/modules/Catalog/Catalog.WriteModel/Services/MediaItems/IMediaChangeRequestParticipantQueryService.cs
src/modules/Catalog/Catalog.WriteModel.Infrastructure/Services/MediaItems/MediaChangeRequestQueryService.cs
src/modules/Catalog/Catalog.WriteModel.Infrastructure/Services/MediaItems/MediaChangeRequestParticipantQueryService.cs

# Integration event handlers (Catalog consuming CR events)
src/modules/Catalog/Catalog.WriteModel.Infrastructure/IntegrationEvents/Consuming/Handlers/ChangeRequestCreatedEventHandler.cs
src/modules/Catalog/Catalog.WriteModel.Infrastructure/IntegrationEvents/Consuming/Handlers/ChangeRequestApprovedEventHandler.cs
src/modules/Catalog/Catalog.WriteModel.Infrastructure/IntegrationEvents/Consuming/Handlers/ChangeRequestRejectedEventHandler.cs
src/modules/Catalog/Catalog.WriteModel.Infrastructure/IntegrationEvents/Consuming/Handlers/ChangeRequestAbandonedEventHandler.cs

# Sagas (both)
src/modules/ChangeRequests/ChangeRequests.WriteModel/Sagas/MediaItemReview/MediaItemReviewSaga.cs
src/modules/ChangeRequests/ChangeRequests.WriteModel/Sagas/MediaItemReview/MediaItemReviewSagaState.cs
src/modules/ChangeRequests/ChangeRequests.WriteModel/Sagas/MediaItemReview/MediaItemReviewSagaStatus.cs
src/modules/ChangeRequests/ChangeRequests.WriteModel/Sagas/MediaItemCheckoutReview/MediaItemCheckoutReviewSaga.cs
src/modules/ChangeRequests/ChangeRequests.WriteModel/Sagas/MediaItemCheckoutReview/MediaItemCheckoutReviewSagaState.cs
src/modules/ChangeRequests/ChangeRequests.WriteModel/Sagas/MediaItemCheckoutReview/MediaItemCheckoutReviewSagaStatus.cs
src/hosts/SagaOrchestrator/MediaItemReview/ (entire folder)
src/hosts/SagaOrchestrator/MediaItemCheckoutReview/ (entire folder)

# ChangeRequest lifecycle handlers (keep comment handlers)
src/modules/ChangeRequests/ChangeRequests.WriteModel/Commands/CreateCheckoutChangeRequest/
src/modules/ChangeRequests/ChangeRequests.WriteModel/Commands/ActivateChangeRequestForReview/
src/modules/ChangeRequests/ChangeRequests.WriteModel/Commands/ApproveReview/
src/modules/ChangeRequests/ChangeRequests.WriteModel/Commands/RejectReview/
src/modules/ChangeRequests/ChangeRequests.WriteModel/Commands/AbandonChangeRequest/
src/modules/ChangeRequests/ChangeRequests.WriteModel/Commands/AssignReviewer/
src/modules/ChangeRequests/ChangeRequests.WriteModel/Commands/RemoveReviewer/
src/modules/ChangeRequests/ChangeRequests.WriteModel/Commands/WithdrawReviewer/

# ChangeRequest lifecycle domain events
src/modules/ChangeRequests/ChangeRequests.Domain/Aggregates/Media/Events/ChangeRequestActivatedForReview.cs
src/modules/ChangeRequests/ChangeRequests.Domain/Aggregates/Media/Events/ChangeRequestApproved.cs
src/modules/ChangeRequests/ChangeRequests.Domain/Aggregates/Media/Events/ChangeRequestRejected.cs
src/modules/ChangeRequests/ChangeRequests.Domain/Aggregates/Media/Events/ChangeRequestAbandoned.cs
src/modules/ChangeRequests/ChangeRequests.Domain/Aggregates/Media/Events/ReviewApproved.cs

# ChangeRequest contracts (lifecycle events)
src/modules/ChangeRequests/ChangeRequests.Contracts/Events/ChangeRequestActivatedForReviewIntegrationEvent.cs
src/modules/ChangeRequests/ChangeRequests.Contracts/Events/ChangeRequestApprovedIntegrationEvent.cs
src/modules/ChangeRequests/ChangeRequests.Contracts/Events/ChangeRequestRejectedIntegrationEvent.cs
src/modules/ChangeRequests/ChangeRequests.Contracts/Events/ChangeRequestAbandonedIntegrationEvent.cs

# ChangeRequest value objects (lifecycle)
src/modules/ChangeRequests/ChangeRequests.Domain/ValueObjects/ChangeRequestBinding.cs
src/modules/ChangeRequests/ChangeRequests.Domain/ValueObjects/ReviewerStatus.cs
src/modules/ChangeRequests/ChangeRequests.Domain/ValueObjects/Reviewer.cs
src/modules/ChangeRequests/ChangeRequests.Domain/ValueObjects/ChangeRequestStatus.cs

# Checkout integration event contracts
src/modules/Catalog/Catalog.Contracts/Events/MediaItems/MediaItemCheckedOutIntegrationEvent.cs

# MediaItem checkout-related contracts
src/modules/Catalog/Catalog.Contracts/Events/MediaItems/MediaItemCheckoutForceReleasedIntegrationEvent.cs
```

---

## Task 1: New ReviewSession value objects

**Files:**
- Create: `src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/ValueObjects/ReviewSessionId.cs`
- Create: `src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/ValueObjects/ReviewerDecision.cs`
- Create: `src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/ValueObjects/ReviewerAssignment.cs`
- Create: `src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/ValueObjects/ReviewSession.cs`

- [ ] **Step 1: Create ReviewSessionId**

```csharp
// src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/ValueObjects/ReviewSessionId.cs
namespace Magiq.Media.Catalog.ValueObjects;

public readonly record struct ReviewSessionId(Guid Value)
{
    public static ReviewSessionId New() => new(Guid.NewGuid());
    public override string ToString() => Value.ToString();
}
```

- [ ] **Step 2: Create ReviewerDecision enum**

```csharp
// src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/ValueObjects/ReviewerDecision.cs
namespace Magiq.Media.Catalog.ValueObjects;

public enum ReviewerDecision
{
    Pending,
    Approved,
    Rejected,
    Withdrawn
}
```

- [ ] **Step 3: Create ReviewerAssignment record**

```csharp
// src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/ValueObjects/ReviewerAssignment.cs
namespace Magiq.Media.Catalog.ValueObjects;

public sealed record ReviewerAssignment(
    MemberId ReviewerId,
    ReviewerDecision Decision,
    DateTimeOffset AssignedAt,
    DateTimeOffset? DecidedAt)
{
    public ReviewerAssignment WithDecision(ReviewerDecision decision, DateTimeOffset decidedAt)
        => this with { Decision = decision, DecidedAt = decidedAt };
}
```

- [ ] **Step 4: Create ReviewSession record**

```csharp
// src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/ValueObjects/ReviewSession.cs
namespace Magiq.Media.Catalog.ValueObjects;

public sealed record ReviewSession(
    ReviewSessionId Id,
    ChangeRequestId? CommentThreadId,
    IReadOnlyList<ReviewerAssignment> Reviewers,
    DateTimeOffset StartedAt)
{
    public bool AllReviewersDecided()
        => Reviewers.All(r => r.Decision != ReviewerDecision.Pending);

    public bool AllActiveReviewersApproved()
        => Reviewers
            .Where(r => r.Decision != ReviewerDecision.Withdrawn)
            .All(r => r.Decision == ReviewerDecision.Approved);

    public ReviewSession WithReviewerDecision(MemberId reviewerId, ReviewerDecision decision, DateTimeOffset decidedAt)
    {
        var updated = Reviewers
            .Select(r => r.ReviewerId == reviewerId ? r.WithDecision(decision, decidedAt) : r)
            .ToList();
        return this with { Reviewers = updated };
    }
}
```

- [ ] **Step 5: Build solution, confirm no errors**

```bash
dotnet build src/modules/Catalog/Catalog.Domain/Catalog.Domain.csproj
```

Expected: Build succeeded with 0 errors.

- [ ] **Step 6: Commit**

```bash
git add src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/ValueObjects/ReviewSessionId.cs \
        src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/ValueObjects/ReviewerDecision.cs \
        src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/ValueObjects/ReviewerAssignment.cs \
        src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/ValueObjects/ReviewSession.cs
git commit -m "feat(catalog): add ReviewSession embedded value objects for inline review tracking"
```

---

## Task 2: Simplify MediaItemStatus and add new domain events

**Files:**
- Modify: `src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/ValueObjects/MediaItemStatus.cs`
- Create: `src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/Events/ReviewerApproved.cs`
- Create: `src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/Events/ReviewerRejected.cs`
- Modify: `src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/Events/MediaItemSubmittedForReview.cs`
- Modify: `src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/Events/MediaItemApproved.cs`
- Modify: `src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/Events/MediaItemRejected.cs`

- [ ] **Step 1: Replace MediaItemStatus**

Replace the entire file content:

```csharp
// src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/ValueObjects/MediaItemStatus.cs
namespace Magiq.Media.Catalog.ValueObjects;

public enum MediaItemStatus
{
    Draft,
    UnderReview,
    Published,
    Archived
}
```

- [ ] **Step 2: Add ReviewerApproved domain event**

```csharp
// src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/Events/ReviewerApproved.cs
namespace Magiq.Media.Catalog.Events;

public sealed record ReviewerApproved(
    MediaItemId MediaItemId,
    ReviewSessionId ReviewSessionId,
    MemberId ReviewerId,
    DateTimeOffset ApprovedAt) : IMediaItemDomainEvent;
```

- [ ] **Step 3: Add ReviewerRejected domain event**

```csharp
// src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/Events/ReviewerRejected.cs
namespace Magiq.Media.Catalog.Events;

public sealed record ReviewerRejected(
    MediaItemId MediaItemId,
    ReviewSessionId ReviewSessionId,
    MemberId ReviewerId,
    string Reason,
    DateTimeOffset RejectedAt) : IMediaItemDomainEvent;
```

- [ ] **Step 4: Update MediaItemSubmittedForReview event**

Read the current file first, then replace the record definition to include ReviewSession fields and remove CR pre-gen fields. The event should contain:

```csharp
public sealed record MediaItemSubmittedForReview(
    MediaItemId MediaItemId,
    MemberId SubmittedBy,
    ReviewSessionId ReviewSessionId,
    ChangeRequestId? CommentThreadId,       // optional — only set if callers create a CR for comments
    IReadOnlyList<MemberId> ReviewerIds,    // empty = auto-approve path
    DateTimeOffset SubmittedAt) : IMediaItemDomainEvent;
```

Remove any `ActiveMediaChangeRequestId` or pre-generated CR ID fields that exist in the current version.

- [ ] **Step 5: Update MediaItemApproved event**

Remove `ActiveMediaChangeRequestId` field. Keep `CurrentVersionNumber`, `ApprovedAssets`, `EffectiveMetadata`, `ApprovedAt`. If a `ReviewSessionId` field is not present, add it:

```csharp
public sealed record MediaItemApproved(
    MediaItemId MediaItemId,
    ReviewSessionId? ReviewSessionId,       // null for auto-approve (no reviewers)
    int NewVersionNumber,
    IReadOnlyDictionary<string, object?> PublishedMetadata,
    IReadOnlyList<ApprovedAssetSnapshot> ApprovedAssets,
    DateTimeOffset ApprovedAt) : IMediaItemDomainEvent;
```

- [ ] **Step 6: Update MediaItemRejected event**

Remove CR fields. Add ReviewSessionId and rejecting reviewer:

```csharp
public sealed record MediaItemRejected(
    MediaItemId MediaItemId,
    ReviewSessionId ReviewSessionId,
    MemberId RejectedBy,
    string Reason,
    DateTimeOffset RejectedAt) : IMediaItemDomainEvent;
```

- [ ] **Step 7: Build to see all compile errors introduced by status enum change**

```bash
dotnet build src/
```

Expected: Many errors from removed enum values (Rejected, SubmissionFailed, Withdrawn). List them — these are the files to fix in subsequent tasks. Do not fix them yet.

- [ ] **Step 8: Commit what compiles**

```bash
git add src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/ValueObjects/MediaItemStatus.cs \
        src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/Events/ReviewerApproved.cs \
        src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/Events/ReviewerRejected.cs \
        src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/Events/MediaItemSubmittedForReview.cs \
        src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/Events/MediaItemApproved.cs \
        src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/Events/MediaItemRejected.cs
git commit -m "feat(catalog): simplify MediaItemStatus to Draft|UnderReview|Published|Archived; update lifecycle events"
```

---

## Task 3: Refactor MediaItem aggregate — remove checkout, add ReviewSession

**Files:**
- Modify: `src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/MediaItem.cs`

This is the core domain change. Read the full file first, then apply the changes below.

- [ ] **Step 1: Read current MediaItem.cs**

```bash
# Check line count first
wc -l src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/MediaItem.cs
```

Use Read tool to load the entire file.

- [ ] **Step 2: Remove checkout state fields**

Delete these private fields from the aggregate:
- `_checkoutStatus` / `CheckoutStatus`
- `_checkedOutBy` / `CheckedOutBy`
- `_checkoutChangeRequestId` / `CheckoutChangeRequestId`
- `_activeMediaChangeRequestId` / `ActiveMediaChangeRequestId`

Add new field:
```csharp
private ReviewSession? _activeReview;
```

- [ ] **Step 3: Remove Metadata.Draft lazy init — replace with explicit fields**

Remove `Metadata.Draft` property (or the draft/current split value object). Replace with:
```csharp
private IReadOnlyDictionary<string, object?>? _draft;     // null when not editing
private IReadOnlyDictionary<string, object?>? _published;  // null until first approval
```

Update any property that exposed `Metadata.Current` / `Metadata.Draft` to expose `_published` and `_draft` directly.

- [ ] **Step 4: Remove checkout methods**

Delete entire method bodies for:
- `CheckOut(...)`
- `CheckIn(...)`
- `AbandonCheckout(...)`
- `ForceReleaseCheckout(...)`
- `AutoRevertIfNeeded()` (private helper)
- `Withdraw(...)` — replace with a direct "return to draft" transition (see Step 6)
- `SubmitForReview` guard that checked `CheckoutStatus`

- [ ] **Step 5: Replace SubmitForReview method**

```csharp
public Result<Unit, DomainError> SubmitForReview(
    MemberId submittedBy,
    ReviewSessionId reviewSessionId,
    ChangeRequestId? commentThreadId,
    IReadOnlyList<MemberId> reviewerIds,
    DateTimeOffset submittedAt)
{
    if (Status != MediaItemStatus.Draft)
        return DomainError.InvalidOperation("MediaItem must be in Draft status to submit for review.");

    // Validate required metadata fields (existing logic — keep as-is)
    var missingFields = GetMissingRequiredFields();
    if (missingFields.Any())
        return DomainError.ValidationFailed($"Required fields missing: {string.Join(", ", missingFields)}");

    Raise(new MediaItemSubmittedForReview(
        Id, submittedBy, reviewSessionId, commentThreadId, reviewerIds, submittedAt));

    if (!reviewerIds.Any())
    {
        // No reviewers = auto-approve inline
        var autoApproved = new MediaItemApproved(
            Id,
            ReviewSessionId: null,
            NewVersionNumber: CurrentVersionNumber + 1,
            PublishedMetadata: _draft ?? _published ?? new Dictionary<string, object?>(),
            ApprovedAssets: new List<ApprovedAssetSnapshot>(),
            ApprovedAt: submittedAt);
        Raise(autoApproved);
    }

    return Unit.Value;
}
```

- [ ] **Step 6: Add ApproveReview method (reviewer casts vote)**

```csharp
public Result<Unit, DomainError> ApproveReview(
    MemberId reviewerId,
    IReadOnlyList<ApprovedAssetSnapshot> approvedAssets,
    DateTimeOffset approvedAt)
{
    if (Status != MediaItemStatus.UnderReview)
        return DomainError.InvalidOperation("MediaItem is not under review.");
    if (_activeReview is null)
        return DomainError.InvalidState("No active review session.");

    var reviewer = _activeReview.Reviewers.FirstOrDefault(r => r.ReviewerId == reviewerId);
    if (reviewer is null)
        return DomainError.NotFound("Reviewer is not part of this review session.");
    if (reviewer.Decision != ReviewerDecision.Pending)
        return DomainError.InvalidOperation("Reviewer has already made a decision.");

    Raise(new ReviewerApproved(Id, _activeReview.Id, reviewerId, approvedAt));

    // After Apply updates _activeReview, check if all active reviewers approved
    if (_activeReview.AllActiveReviewersApproved())
    {
        Raise(new MediaItemApproved(
            Id,
            _activeReview.Id,
            NewVersionNumber: CurrentVersionNumber + 1,
            PublishedMetadata: _draft ?? _published ?? new Dictionary<string, object?>(),
            ApprovedAssets: approvedAssets,
            ApprovedAt: approvedAt));
    }

    return Unit.Value;
}
```

- [ ] **Step 7: Add RejectReview method (reviewer rejects)**

```csharp
public Result<Unit, DomainError> RejectReview(
    MemberId reviewerId,
    string reason,
    DateTimeOffset rejectedAt)
{
    if (Status != MediaItemStatus.UnderReview)
        return DomainError.InvalidOperation("MediaItem is not under review.");
    if (_activeReview is null)
        return DomainError.InvalidState("No active review session.");

    var reviewer = _activeReview.Reviewers.FirstOrDefault(r => r.ReviewerId == reviewerId);
    if (reviewer is null)
        return DomainError.NotFound("Reviewer is not part of this review session.");
    if (reviewer.Decision != ReviewerDecision.Pending)
        return DomainError.InvalidOperation("Reviewer has already made a decision.");

    if (string.IsNullOrWhiteSpace(reason))
        return DomainError.ValidationFailed("Rejection reason is required.");

    Raise(new ReviewerRejected(Id, _activeReview.Id, reviewerId, reason, rejectedAt));
    Raise(new MediaItemRejected(Id, _activeReview.Id, reviewerId, reason, rejectedAt));

    return Unit.Value;
}
```

- [ ] **Step 8: Update Approve method (now called only internally or by system)**

The old `Approve(DateTimeOffset, IReadOnlyList<ApprovedAssetSnapshot>)` was called by a handler. Now approval is triggered by `ApproveReview` raising `MediaItemApproved`. Remove the public `Approve` method — the event does the work. If any external trigger still needs it (e.g. an admin override), keep it as `ForceApprove` with clear intent.

- [ ] **Step 9: Update Apply event handlers**

Add Apply handlers for new events and remove Apply handlers for deleted events:

```csharp
private void Apply(MediaItemSubmittedForReview e)
{
    Status = MediaItemStatus.UnderReview;
    if (e.ReviewerIds.Any())
    {
        _activeReview = new ReviewSession(
            e.ReviewSessionId,
            e.CommentThreadId,
            e.ReviewerIds.Select(id => new ReviewerAssignment(id, ReviewerDecision.Pending, e.SubmittedAt, null)).ToList(),
            e.SubmittedAt);
    }
}

private void Apply(ReviewerApproved e)
{
    _activeReview = _activeReview?.WithReviewerDecision(e.ReviewerId, ReviewerDecision.Approved, e.ApprovedAt);
}

private void Apply(ReviewerRejected e)
{
    _activeReview = _activeReview?.WithReviewerDecision(e.ReviewerId, ReviewerDecision.Rejected, e.RejectedAt);
}

private void Apply(MediaItemApproved e)
{
    Status = MediaItemStatus.Published;
    CurrentVersionNumber = e.NewVersionNumber;
    _published = e.PublishedMetadata;
    _draft = null;         // explicit clear — no lazy init
    _activeReview = null;  // review complete
}

private void Apply(MediaItemRejected e)
{
    Status = MediaItemStatus.Draft;  // direct transition — no auto-revert state
    _activeReview = null;
    // _draft is preserved for the owner to revise
}
```

Remove Apply handlers for: `MediaItemCheckedOut`, `MediaItemCheckedIn`, `MediaItemCheckoutAbandoned`, `MediaItemCheckoutForceReleased`, `MediaItemRevertedToDraft`, `MediaItemSubmissionFailed`, `ChangeRequestLinked`, `ChangeRequestUnlinked`, `MediaItemWithdrawn`.

- [ ] **Step 10: Remove Withdraw method or simplify**

If Withdraw is still needed (owner wants to recall a published item), simplify to:

```csharp
public Result<Unit, DomainError> Withdraw(MemberId requestedBy, DateTimeOffset withdrawnAt)
{
    if (Status == MediaItemStatus.Archived)
        return DomainError.InvalidOperation("Cannot withdraw an archived item.");

    // If under review, cancel the review and return to draft
    // If published, return to draft for editing
    Raise(new MediaItemWithdrawn(Id, requestedBy, withdrawnAt));
    return Unit.Value;
}

private void Apply(MediaItemWithdrawn e)
{
    Status = MediaItemStatus.Draft;  // direct — no intermediate Withdrawn status
    _activeReview = null;
    // If _draft is null and _published exists, initialize draft from published
    _draft ??= _published?.ToDictionary(kvp => kvp.Key, kvp => kvp.Value);
}
```

- [ ] **Step 11: Update metadata write guard**

Any method that writes metadata (e.g. `SetMetadataField`, `BatchSetMetadata`) previously called `AutoRevertIfNeeded()`. Replace with:

```csharp
// Before writing: if Published, initialize draft from published snapshot
if (Status == MediaItemStatus.Published)
{
    _draft = _published?.ToDictionary(kvp => kvp.Key, kvp => kvp.Value);
    // Status stays Published — it becomes Draft only on explicit Withdraw or Reject
}
```

Actually — reconsider: in the new model, a Published item should not be editable without first calling Withdraw. Remove the auto-revert entirely. Metadata writes should guard:

```csharp
if (Status != MediaItemStatus.Draft)
    return DomainError.InvalidOperation("MediaItem must be in Draft status to edit metadata.");
```

- [ ] **Step 12: Build Catalog.Domain**

```bash
dotnet build src/modules/Catalog/Catalog.Domain/Catalog.Domain.csproj
```

Expected: Build succeeded. Fix any remaining compile errors in this project before proceeding.

- [ ] **Step 13: Commit**

```bash
git add src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/MediaItem.cs
git commit -m "feat(catalog): refactor MediaItem aggregate — embed ReviewSession, remove checkout, remove auto-revert"
```

---

## Task 4: Delete checkout-related domain events and value objects

**Files:** All files listed in the Deleted files section under "Checkout domain events" and "Checkout value objects".

- [ ] **Step 1: Delete checkout domain events**

```bash
rm src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/Events/MediaItemCheckedOut.cs
rm src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/Events/MediaItemCheckedIn.cs
rm src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/Events/MediaItemCheckoutAbandoned.cs
rm src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/Events/MediaItemCheckoutForceReleased.cs
rm src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/Events/CheckInRequested.cs
rm src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/Events/MediaItemRevertedToDraft.cs
rm src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/Events/MediaItemSubmissionFailed.cs
rm src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/Events/ChangeRequestLinked.cs
rm src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/Events/ChangeRequestUnlinked.cs
```

- [ ] **Step 2: Delete checkout value objects**

```bash
rm src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/ValueObjects/CheckoutStatus.cs
rm src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/ValueObjects/CheckoutMemberId.cs
```

- [ ] **Step 3: Build to find all remaining references**

```bash
dotnet build src/modules/Catalog/
```

Fix any remaining references to deleted types (there should be none after Task 3, but confirm).

- [ ] **Step 4: Commit**

```bash
git add -u
git commit -m "chore(catalog): delete checkout domain events and value objects"
```

---

## Task 5: Delete and replace checkout command handlers

**Files:** Checkout and CR-link handler folders listed in Deleted files.

- [ ] **Step 1: Delete checkout handlers**

```bash
rm -rf src/modules/Catalog/Catalog.WriteModel/Commands/MediaItems/CheckOutMediaItem/
rm -rf src/modules/Catalog/Catalog.WriteModel/Commands/MediaItems/CheckInMediaItem/
rm -rf src/modules/Catalog/Catalog.WriteModel/Commands/MediaItems/AbandonCheckout/
rm -rf src/modules/Catalog/Catalog.WriteModel/Commands/MediaItems/ForceReleaseCheckout/
rm -rf src/modules/Catalog/Catalog.WriteModel/Commands/MediaItems/LinkChangeRequest/
rm -rf src/modules/Catalog/Catalog.WriteModel/Commands/MediaItems/UnlinkChangeRequest/
```

- [ ] **Step 2: Delete CR query services**

```bash
rm src/modules/Catalog/Catalog.WriteModel/Services/MediaItems/IMediaChangeRequestQueryService.cs
rm src/modules/Catalog/Catalog.WriteModel/Services/MediaItems/IMediaChangeRequestParticipantQueryService.cs
rm src/modules/Catalog/Catalog.WriteModel.Infrastructure/Services/MediaItems/MediaChangeRequestQueryService.cs
rm src/modules/Catalog/Catalog.WriteModel.Infrastructure/Services/MediaItems/MediaChangeRequestParticipantQueryService.cs
```

- [ ] **Step 3: Delete Catalog integration event handlers consuming CR events**

```bash
rm src/modules/Catalog/Catalog.WriteModel.Infrastructure/IntegrationEvents/Consuming/Handlers/ChangeRequestCreatedEventHandler.cs
rm src/modules/Catalog/Catalog.WriteModel.Infrastructure/IntegrationEvents/Consuming/Handlers/ChangeRequestApprovedEventHandler.cs
rm src/modules/Catalog/Catalog.WriteModel.Infrastructure/IntegrationEvents/Consuming/Handlers/ChangeRequestRejectedEventHandler.cs
rm src/modules/Catalog/Catalog.WriteModel.Infrastructure/IntegrationEvents/Consuming/Handlers/ChangeRequestAbandonedEventHandler.cs
```

- [ ] **Step 4: Build Catalog.WriteModel**

```bash
dotnet build src/modules/Catalog/Catalog.WriteModel/Catalog.WriteModel.csproj
dotnet build src/modules/Catalog/Catalog.WriteModel.Infrastructure/Catalog.WriteModel.Infrastructure.csproj
```

Expected: 0 errors. Fix any DI registrations that referenced deleted services.

- [ ] **Step 5: Commit**

```bash
git add -u
git commit -m "chore(catalog): delete checkout handlers, CR query services, and CR integration event handlers"
```

---

## Task 6: Simplify SubmitForReview and ApproveMediaItem handlers

**Files:**
- Modify: `src/modules/Catalog/Catalog.WriteModel/Commands/MediaItems/SubmitForReview/SubmitForReviewHandler.cs`
- Modify: `src/modules/Catalog/Catalog.WriteModel/Commands/MediaItems/ApproveMediaItem/ApproveMediaItemHandler.cs`

- [ ] **Step 1: Read SubmitForReviewHandler.cs**

Use Read tool to load the current handler.

- [ ] **Step 2: Simplify SubmitForReviewHandler**

Remove:
- `IMediaChangeRequestQueryService` dependency
- CR ID pre-generation logic
- `MediaItemSubmittedForReviewMessage` publishing (integration event to ChangeRequests module)
- ReviewPolicy routing fork (the handler no longer needs to know about policy)

The simplified handler:
```csharp
public sealed class SubmitForReviewHandler : ICommandHandler<SubmitForReviewCommand>
{
    private readonly IMediaItemRepository _repository;
    private readonly IAssetQueryService _assetService;

    public SubmitForReviewHandler(IMediaItemRepository repository, IAssetQueryService assetService)
    {
        _repository = repository;
        _assetService = assetService;
    }

    public async Task<Result<Unit, CommandError>> HandleAsync(
        SubmitForReviewCommand command,
        ICommandHandlingContext context,
        CancellationToken cancellationToken)
    {
        var item = await _repository.GetByIdAsync(command.TenantId, command.MediaItemId, cancellationToken);
        if (item is null)
            return CommandError.NotFound("MediaItem not found.");

        // Validate all required asset roles are filled
        var assetValidationError = await ValidateRequiredAssetsAsync(item, command.TenantId, cancellationToken);
        if (assetValidationError is not null)
            return assetValidationError;

        var reviewSessionId = ReviewSessionId.New();
        var result = item.SubmitForReview(
            command.SubmittedBy,
            reviewSessionId,
            command.CommentThreadId,
            command.ReviewerIds,
            command.SubmittedAt);

        if (result.IsFailure)
            return CommandError.DomainError(result.Error);

        await _repository.SaveAsync(item, cancellationToken);
        return Unit.Value;
    }

    private async Task<CommandError?> ValidateRequiredAssetsAsync(
        MediaItem item, TenantId tenantId, CancellationToken cancellationToken)
    {
        // Keep existing asset role validation logic — just moved here from old handler
        // ...
        return null;
    }
}
```

- [ ] **Step 3: Update SubmitForReviewCommand**

Add `CommentThreadId` (nullable), `ReviewerIds` (list, may be empty). Remove any CR-pre-gen fields.

```csharp
public sealed record SubmitForReviewCommand(
    TenantId TenantId,
    MediaItemId MediaItemId,
    MemberId SubmittedBy,
    ChangeRequestId? CommentThreadId,
    IReadOnlyList<MemberId> ReviewerIds,
    DateTimeOffset SubmittedAt) : ICommand;
```

- [ ] **Step 4: Read ApproveMediaItemHandler.cs**

Use Read tool.

- [ ] **Step 5: Remove IMediaChangeRequestQueryService from ApproveMediaItemHandler**

The old handler checked `CR must be Approved` via `_crService`. Remove that check — approval is now driven by `ApproveReview` on the aggregate itself. The `ApproveMediaItem` command becomes an admin/system override (force-approve without reviewer votes). Or, remove it entirely if only reviewer-voted approval is needed.

If keeping as admin override:

```csharp
public sealed class ApproveMediaItemHandler : ICommandHandler<ApproveMediaItemCommand>
{
    private readonly IMediaItemRepository _repository;
    private readonly IAssetQueryService _assetService;

    public ApproveMediaItemHandler(IMediaItemRepository repository, IAssetQueryService assetService)
    {
        _repository = repository;
        _assetService = assetService;
    }

    public async Task<Result<Unit, CommandError>> HandleAsync(
        ApproveMediaItemCommand command,
        ICommandHandlingContext context,
        CancellationToken cancellationToken)
    {
        var item = await _repository.GetByIdAsync(command.TenantId, command.MediaItemId, cancellationToken);
        if (item is null)
            return CommandError.NotFound("MediaItem not found.");

        var approvedAssets = await BuildApprovedAssetSnapshotsAsync(item, command.TenantId, cancellationToken);
        var result = item.ForceApprove(command.ApprovedBy, approvedAssets, command.ApprovedAt);

        if (result.IsFailure)
            return CommandError.DomainError(result.Error);

        await _repository.SaveAsync(item, cancellationToken);
        return Unit.Value;
    }

    private async Task<IReadOnlyList<ApprovedAssetSnapshot>> BuildApprovedAssetSnapshotsAsync(
        MediaItem item, TenantId tenantId, CancellationToken cancellationToken)
    {
        // Keep existing asset snapshot building logic
        // ...
    }
}
```

- [ ] **Step 6: Build**

```bash
dotnet build src/modules/Catalog/Catalog.WriteModel/Catalog.WriteModel.csproj
```

Expected: 0 errors.

- [ ] **Step 7: Commit**

```bash
git add src/modules/Catalog/Catalog.WriteModel/Commands/MediaItems/SubmitForReview/ \
        src/modules/Catalog/Catalog.WriteModel/Commands/MediaItems/ApproveMediaItem/
git commit -m "feat(catalog): simplify SubmitForReview and ApproveMediaItem handlers — remove CR choreography"
```

---

## Task 7: Add ApproveReview and RejectReview handlers (in Catalog)

These replace the old CR-based approval that lived in the ChangeRequests module.

**Files:**
- Create: `src/modules/Catalog/Catalog.WriteModel/Commands/MediaItems/ApproveReview/ApproveReviewCommand.cs`
- Create: `src/modules/Catalog/Catalog.WriteModel/Commands/MediaItems/ApproveReview/ApproveReviewHandler.cs`
- Create: `src/modules/Catalog/Catalog.WriteModel/Commands/MediaItems/RejectReview/RejectReviewCommand.cs`
- Create: `src/modules/Catalog/Catalog.WriteModel/Commands/MediaItems/RejectReview/RejectReviewHandler.cs`
- Test: `tests/modules/Catalog/Catalog.WriteModel.Tests/MediaItems/Commands/ApproveReviewHandlerTests.cs`
- Test: `tests/modules/Catalog/Catalog.WriteModel.Tests/MediaItems/Commands/RejectReviewHandlerTests.cs`

- [ ] **Step 1: Write failing tests for ApproveReviewHandler**

```csharp
// tests/modules/Catalog/Catalog.WriteModel.Tests/MediaItems/Commands/ApproveReviewHandlerTests.cs
using FluentAssertions;
using Magiq.Media.Catalog.Aggregates.MediaItems;
using Magiq.Media.Catalog.Commands.MediaItems.ApproveReview;
using Magiq.Media.Catalog.Repositories;
using Magiq.Media.Catalog.Services;
using Magiq.Media.Catalog.ValueObjects;
using Magiq.Platform.WriteModel.Commands;
using Moq;
using Xunit;

namespace Magiq.Media.Catalog.Tests.MediaItems.Commands;

public sealed class ApproveReviewHandlerTests
{
    private static readonly TenantId _tenant = MediaItemFactory.Tenant;
    private static readonly MediaItemId _itemId = MediaItemFactory.ItemId;
    private readonly Mock<IMediaItemRepository> _repository = new(MockBehavior.Strict);
    private readonly Mock<IAssetQueryService> _assetService = new(MockBehavior.Strict);

    private ApproveReviewHandler CreateHandler() =>
        new ApproveReviewHandler(_repository.Object, _assetService.Object);

    [Fact]
    public async Task HandleAsync_MediaItemNotFound_ReturnsNotFound()
    {
        _repository.Setup(r => r.GetByIdAsync(_tenant, _itemId, CancellationToken.None))
            .ReturnsAsync((MediaItem?)null);

        var cmd = new ApproveReviewCommand(_tenant, _itemId, new MemberId(Guid.NewGuid()), DateTimeOffset.UtcNow);
        var result = await CreateHandler().HandleAsync(cmd, new Mock<ICommandHandlingContext>().Object, CancellationToken.None);

        result.IsFailure.Should().BeTrue();
    }

    [Fact]
    public async Task HandleAsync_ItemNotUnderReview_ReturnsError()
    {
        var item = MediaItemFactory.CreateDraft(_tenant, _itemId);
        _repository.Setup(r => r.GetByIdAsync(_tenant, _itemId, CancellationToken.None))
            .ReturnsAsync(item);
        _assetService.Setup(s => s.GetApprovedAssetSnapshotsAsync(It.IsAny<IEnumerable<MediaAssetReference>>(), _tenant, CancellationToken.None))
            .ReturnsAsync(new List<ApprovedAssetSnapshot>());

        var cmd = new ApproveReviewCommand(_tenant, _itemId, new MemberId(Guid.NewGuid()), DateTimeOffset.UtcNow);
        var result = await CreateHandler().HandleAsync(cmd, new Mock<ICommandHandlingContext>().Object, CancellationToken.None);

        result.IsFailure.Should().BeTrue();
    }

    [Fact]
    public async Task HandleAsync_LastReviewerApproves_ItemBecomesPublished()
    {
        var reviewerId = new MemberId(Guid.NewGuid());
        var item = MediaItemFactory.CreateUnderReviewWithSingleReviewer(_tenant, _itemId, reviewerId);

        _repository.Setup(r => r.GetByIdAsync(_tenant, _itemId, CancellationToken.None))
            .ReturnsAsync(item);
        _repository.Setup(r => r.SaveAsync(It.IsAny<MediaItem>(), CancellationToken.None))
            .Returns(Task.CompletedTask);
        _assetService.Setup(s => s.GetApprovedAssetSnapshotsAsync(It.IsAny<IEnumerable<MediaAssetReference>>(), _tenant, CancellationToken.None))
            .ReturnsAsync(new List<ApprovedAssetSnapshot>());

        var cmd = new ApproveReviewCommand(_tenant, _itemId, reviewerId, DateTimeOffset.UtcNow);
        var result = await CreateHandler().HandleAsync(cmd, new Mock<ICommandHandlingContext>().Object, CancellationToken.None);

        result.IsSuccess.Should().BeTrue();
        item.Status.Should().Be(MediaItemStatus.Published);
    }
}
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
dotnet test tests/modules/Catalog/Catalog.WriteModel.Tests/ --filter "ApproveReviewHandlerTests" -v
```

Expected: Compile error (handler not yet created).

- [ ] **Step 3: Create ApproveReviewCommand**

```csharp
// src/modules/Catalog/Catalog.WriteModel/Commands/MediaItems/ApproveReview/ApproveReviewCommand.cs
namespace Magiq.Media.Catalog.Commands.MediaItems.ApproveReview;

public sealed record ApproveReviewCommand(
    TenantId TenantId,
    MediaItemId MediaItemId,
    MemberId ReviewerId,
    DateTimeOffset ApprovedAt) : ICommand;
```

- [ ] **Step 4: Create ApproveReviewHandler**

```csharp
// src/modules/Catalog/Catalog.WriteModel/Commands/MediaItems/ApproveReview/ApproveReviewHandler.cs
namespace Magiq.Media.Catalog.Commands.MediaItems.ApproveReview;

public sealed class ApproveReviewHandler : ICommandHandler<ApproveReviewCommand>
{
    private readonly IMediaItemRepository _repository;
    private readonly IAssetQueryService _assetService;

    public ApproveReviewHandler(IMediaItemRepository repository, IAssetQueryService assetService)
    {
        _repository = repository;
        _assetService = assetService;
    }

    public async Task<Result<Unit, CommandError>> HandleAsync(
        ApproveReviewCommand command,
        ICommandHandlingContext context,
        CancellationToken cancellationToken)
    {
        var item = await _repository.GetByIdAsync(command.TenantId, command.MediaItemId, cancellationToken);
        if (item is null)
            return CommandError.NotFound("MediaItem not found.");

        var approvedAssets = await _assetService.GetApprovedAssetSnapshotsAsync(
            item.Assets, command.TenantId, cancellationToken);

        var result = item.ApproveReview(command.ReviewerId, approvedAssets, command.ApprovedAt);
        if (result.IsFailure)
            return CommandError.DomainError(result.Error);

        await _repository.SaveAsync(item, cancellationToken);
        return Unit.Value;
    }
}
```

- [ ] **Step 5: Write failing tests for RejectReviewHandler**

```csharp
// tests/modules/Catalog/Catalog.WriteModel.Tests/MediaItems/Commands/RejectReviewHandlerTests.cs
using FluentAssertions;
using Magiq.Media.Catalog.Aggregates.MediaItems;
using Magiq.Media.Catalog.Commands.MediaItems.RejectReview;
using Magiq.Media.Catalog.Repositories;
using Magiq.Media.Catalog.ValueObjects;
using Magiq.Platform.WriteModel.Commands;
using Moq;
using Xunit;

namespace Magiq.Media.Catalog.Tests.MediaItems.Commands;

public sealed class RejectReviewHandlerTests
{
    private static readonly TenantId _tenant = MediaItemFactory.Tenant;
    private static readonly MediaItemId _itemId = MediaItemFactory.ItemId;
    private readonly Mock<IMediaItemRepository> _repository = new(MockBehavior.Strict);

    private RejectReviewHandler CreateHandler() => new RejectReviewHandler(_repository.Object);

    [Fact]
    public async Task HandleAsync_MediaItemNotFound_ReturnsNotFound()
    {
        _repository.Setup(r => r.GetByIdAsync(_tenant, _itemId, CancellationToken.None))
            .ReturnsAsync((MediaItem?)null);

        var cmd = new RejectReviewCommand(_tenant, _itemId, new MemberId(Guid.NewGuid()), "Not ready", DateTimeOffset.UtcNow);
        var result = await CreateHandler().HandleAsync(cmd, new Mock<ICommandHandlingContext>().Object, CancellationToken.None);

        result.IsFailure.Should().BeTrue();
    }

    [Fact]
    public async Task HandleAsync_ReviewerRejects_ItemReturnsToDraft()
    {
        var reviewerId = new MemberId(Guid.NewGuid());
        var item = MediaItemFactory.CreateUnderReviewWithSingleReviewer(_tenant, _itemId, reviewerId);

        _repository.Setup(r => r.GetByIdAsync(_tenant, _itemId, CancellationToken.None))
            .ReturnsAsync(item);
        _repository.Setup(r => r.SaveAsync(It.IsAny<MediaItem>(), CancellationToken.None))
            .Returns(Task.CompletedTask);

        var cmd = new RejectReviewCommand(_tenant, _itemId, reviewerId, "Missing required metadata", DateTimeOffset.UtcNow);
        var result = await CreateHandler().HandleAsync(cmd, new Mock<ICommandHandlingContext>().Object, CancellationToken.None);

        result.IsSuccess.Should().BeTrue();
        item.Status.Should().Be(MediaItemStatus.Draft);
    }

    [Fact]
    public async Task HandleAsync_EmptyReason_ReturnsError()
    {
        var reviewerId = new MemberId(Guid.NewGuid());
        var item = MediaItemFactory.CreateUnderReviewWithSingleReviewer(_tenant, _itemId, reviewerId);

        _repository.Setup(r => r.GetByIdAsync(_tenant, _itemId, CancellationToken.None))
            .ReturnsAsync(item);

        var cmd = new RejectReviewCommand(_tenant, _itemId, reviewerId, "", DateTimeOffset.UtcNow);
        var result = await CreateHandler().HandleAsync(cmd, new Mock<ICommandHandlingContext>().Object, CancellationToken.None);

        result.IsFailure.Should().BeTrue();
    }
}
```

- [ ] **Step 6: Create RejectReviewCommand**

```csharp
// src/modules/Catalog/Catalog.WriteModel/Commands/MediaItems/RejectReview/RejectReviewCommand.cs
namespace Magiq.Media.Catalog.Commands.MediaItems.RejectReview;

public sealed record RejectReviewCommand(
    TenantId TenantId,
    MediaItemId MediaItemId,
    MemberId ReviewerId,
    string Reason,
    DateTimeOffset RejectedAt) : ICommand;
```

- [ ] **Step 7: Create RejectReviewHandler**

```csharp
// src/modules/Catalog/Catalog.WriteModel/Commands/MediaItems/RejectReview/RejectReviewHandler.cs
namespace Magiq.Media.Catalog.Commands.MediaItems.RejectReview;

public sealed class RejectReviewHandler : ICommandHandler<RejectReviewCommand>
{
    private readonly IMediaItemRepository _repository;

    public RejectReviewHandler(IMediaItemRepository repository)
    {
        _repository = repository;
    }

    public async Task<Result<Unit, CommandError>> HandleAsync(
        RejectReviewCommand command,
        ICommandHandlingContext context,
        CancellationToken cancellationToken)
    {
        var item = await _repository.GetByIdAsync(command.TenantId, command.MediaItemId, cancellationToken);
        if (item is null)
            return CommandError.NotFound("MediaItem not found.");

        var result = item.RejectReview(command.ReviewerId, command.Reason, command.RejectedAt);
        if (result.IsFailure)
            return CommandError.DomainError(result.Error);

        await _repository.SaveAsync(item, cancellationToken);
        return Unit.Value;
    }
}
```

- [ ] **Step 8: Add MediaItemFactory helpers for tests**

Find the `MediaItemFactory` test helper (likely in `tests/modules/Catalog/Catalog.WriteModel.Tests/`). Add:

```csharp
public static MediaItem CreateUnderReviewWithSingleReviewer(TenantId tenant, MediaItemId id, MemberId reviewerId)
{
    var item = CreateDraft(tenant, id);
    var reviewSessionId = ReviewSessionId.New();
    item.SubmitForReview(
        new MemberId(Guid.NewGuid()),
        reviewSessionId,
        commentThreadId: null,
        reviewerIds: new[] { reviewerId },
        DateTimeOffset.UtcNow);
    return item;
}
```

- [ ] **Step 9: Run all new tests**

```bash
dotnet test tests/modules/Catalog/Catalog.WriteModel.Tests/ --filter "ApproveReviewHandlerTests|RejectReviewHandlerTests" -v
```

Expected: All pass.

- [ ] **Step 10: Commit**

```bash
git add src/modules/Catalog/Catalog.WriteModel/Commands/MediaItems/ApproveReview/ \
        src/modules/Catalog/Catalog.WriteModel/Commands/MediaItems/RejectReview/ \
        tests/modules/Catalog/Catalog.WriteModel.Tests/MediaItems/Commands/ApproveReviewHandlerTests.cs \
        tests/modules/Catalog/Catalog.WriteModel.Tests/MediaItems/Commands/RejectReviewHandlerTests.cs
git commit -m "feat(catalog): add ApproveReview and RejectReview handlers — reviewer votes tracked on MediaItem"
```

---

## Task 8: Delete sagas

- [ ] **Step 1: Delete MediaItemReview saga**

```bash
rm -rf src/modules/ChangeRequests/ChangeRequests.WriteModel/Sagas/MediaItemReview/
rm -rf src/modules/ChangeRequests/ChangeRequests.WriteModel/Sagas/MediaItemCheckoutReview/
rm -rf src/hosts/SagaOrchestrator/MediaItemReview/
rm -rf src/hosts/SagaOrchestrator/MediaItemCheckoutReview/
```

- [ ] **Step 2: Remove saga registrations**

Search for saga registrations in DI setup files:

```bash
grep -r "MediaItemReviewSaga\|MediaItemCheckoutReviewSaga" src/hosts/SagaOrchestrator/ --include="*.cs" -l
```

Open each file found and remove the saga registration line.

- [ ] **Step 3: Build SagaOrchestrator host**

```bash
dotnet build src/hosts/SagaOrchestrator/
```

Expected: 0 errors.

- [ ] **Step 4: Commit**

```bash
git add -u
git commit -m "chore(sagas): delete MediaItemReview and MediaItemCheckoutReview sagas — review now inline on MediaItem"
```

---

## Task 9: Simplify ChangeRequest aggregate to comment-only

**Files:**
- Modify: `src/modules/ChangeRequests/ChangeRequests.Domain/Aggregates/Media/ChangeRequest.cs`
- Delete: lifecycle handlers, events, value objects listed in Deleted files section

- [ ] **Step 1: Delete ChangeRequest lifecycle handlers**

```bash
rm -rf src/modules/ChangeRequests/ChangeRequests.WriteModel/Commands/CreateCheckoutChangeRequest/
rm -rf src/modules/ChangeRequests/ChangeRequests.WriteModel/Commands/ActivateChangeRequestForReview/
rm -rf src/modules/ChangeRequests/ChangeRequests.WriteModel/Commands/ApproveReview/
rm -rf src/modules/ChangeRequests/ChangeRequests.WriteModel/Commands/RejectReview/
rm -rf src/modules/ChangeRequests/ChangeRequests.WriteModel/Commands/AbandonChangeRequest/
rm -rf src/modules/ChangeRequests/ChangeRequests.WriteModel/Commands/AssignReviewer/
rm -rf src/modules/ChangeRequests/ChangeRequests.WriteModel/Commands/RemoveReviewer/
rm -rf src/modules/ChangeRequests/ChangeRequests.WriteModel/Commands/WithdrawReviewer/
```

- [ ] **Step 2: Delete ChangeRequest lifecycle domain events**

```bash
rm src/modules/ChangeRequests/ChangeRequests.Domain/Aggregates/Media/Events/ChangeRequestActivatedForReview.cs
rm src/modules/ChangeRequests/ChangeRequests.Domain/Aggregates/Media/Events/ChangeRequestApproved.cs
rm src/modules/ChangeRequests/ChangeRequests.Domain/Aggregates/Media/Events/ChangeRequestRejected.cs
rm src/modules/ChangeRequests/ChangeRequests.Domain/Aggregates/Media/Events/ChangeRequestAbandoned.cs
rm src/modules/ChangeRequests/ChangeRequests.Domain/Aggregates/Media/Events/ReviewApproved.cs
```

- [ ] **Step 3: Delete ChangeRequest lifecycle value objects**

```bash
rm src/modules/ChangeRequests/ChangeRequests.Domain/ValueObjects/ChangeRequestBinding.cs
rm src/modules/ChangeRequests/ChangeRequests.Domain/ValueObjects/ReviewerStatus.cs
rm src/modules/ChangeRequests/ChangeRequests.Domain/ValueObjects/Reviewer.cs
rm src/modules/ChangeRequests/ChangeRequests.Domain/ValueObjects/ChangeRequestStatus.cs
```

- [ ] **Step 4: Delete ChangeRequest contract events (lifecycle)**

```bash
rm src/modules/ChangeRequests/ChangeRequests.Contracts/Events/ChangeRequestActivatedForReviewIntegrationEvent.cs
rm src/modules/ChangeRequests/ChangeRequests.Contracts/Events/ChangeRequestApprovedIntegrationEvent.cs
rm src/modules/ChangeRequests/ChangeRequests.Contracts/Events/ChangeRequestRejectedIntegrationEvent.cs
rm src/modules/ChangeRequests/ChangeRequests.Contracts/Events/ChangeRequestAbandonedIntegrationEvent.cs
```

- [ ] **Step 5: Rewrite ChangeRequest aggregate as comment-only**

Read the current `ChangeRequest.cs` first. Strip it to only what is needed for a comment thread:

```csharp
// src/modules/ChangeRequests/ChangeRequests.Domain/Aggregates/Media/ChangeRequest.cs
namespace Magiq.Media.ChangeRequests.Aggregates.Media;

public sealed class ChangeRequest : AggregateRoot<ChangeRequestId>
{
    private readonly List<ReviewComment> _comments = new();

    public TenantId TenantId { get; private set; }
    public MediaItemId MediaItemId { get; private set; }
    public MemberId CreatedById { get; private set; }
    public IReadOnlyList<ReviewComment> Comments => _comments.AsReadOnly();

    private ChangeRequest() { }

    public static ChangeRequest Create(
        TenantId tenantId,
        ChangeRequestId id,
        MediaItemId mediaItemId,
        MemberId createdById,
        DateTimeOffset createdAt)
    {
        var cr = new ChangeRequest();
        cr.Raise(new ChangeRequestCreated(tenantId, id, mediaItemId, createdById, createdAt));
        return cr;
    }

    public Result<Unit, DomainError> AddComment(
        CommentId commentId,
        MemberId authorId,
        string body,
        CommentId? parentCommentId,
        DateTimeOffset addedAt)
    {
        if (string.IsNullOrWhiteSpace(body))
            return DomainError.ValidationFailed("Comment body cannot be empty.");

        Raise(new CommentAdded(Id, commentId, authorId, body, parentCommentId, addedAt));
        return Unit.Value;
    }

    public Result<Unit, DomainError> EditComment(
        CommentId commentId,
        MemberId requestedBy,
        string newBody,
        DateTimeOffset editedAt)
    {
        var comment = _comments.FirstOrDefault(c => c.CommentId == commentId);
        if (comment is null)
            return DomainError.NotFound("Comment not found.");
        if (comment.AuthorId != requestedBy)
            return DomainError.Forbidden("Only the comment author can edit it.");
        if (comment.IsDeleted)
            return DomainError.InvalidOperation("Cannot edit a deleted comment.");
        if (string.IsNullOrWhiteSpace(newBody))
            return DomainError.ValidationFailed("Comment body cannot be empty.");

        Raise(new CommentEdited(Id, commentId, requestedBy, comment.Body, newBody, editedAt));
        return Unit.Value;
    }

    public Result<Unit, DomainError> DeleteComment(CommentId commentId, MemberId requestedBy, DateTimeOffset deletedAt)
    {
        var comment = _comments.FirstOrDefault(c => c.CommentId == commentId);
        if (comment is null)
            return DomainError.NotFound("Comment not found.");
        if (comment.AuthorId != requestedBy)
            return DomainError.Forbidden("Only the comment author can delete it.");
        if (comment.IsDeleted)
            return DomainError.InvalidOperation("Comment is already deleted.");

        Raise(new CommentDeleted(Id, commentId, requestedBy, deletedAt));
        return Unit.Value;
    }

    private void Apply(ChangeRequestCreated e)
    {
        Id = e.ChangeRequestId;
        TenantId = e.TenantId;
        MediaItemId = e.MediaItemId;
        CreatedById = e.CreatedById;
    }

    private void Apply(CommentAdded e)
    {
        _comments.Add(new ReviewComment(e.CommentId, e.AuthorId, e.Body, e.ParentCommentId, e.AddedAt, IsDeleted: false));
    }

    private void Apply(CommentEdited e)
    {
        var idx = _comments.FindIndex(c => c.CommentId == e.CommentId);
        if (idx >= 0)
            _comments[idx] = _comments[idx] with { Body = e.NewBody };
    }

    private void Apply(CommentDeleted e)
    {
        var idx = _comments.FindIndex(c => c.CommentId == e.CommentId);
        if (idx >= 0)
            _comments[idx] = _comments[idx] with { IsDeleted = true };
    }
}
```

- [ ] **Step 6: Build ChangeRequests module**

```bash
dotnet build src/modules/ChangeRequests/
```

Expected: 0 errors. Fix any remaining references.

- [ ] **Step 7: Commit**

```bash
git add -u
git commit -m "feat(change-requests): simplify ChangeRequest to comment-only thread — lifecycle tracking moved to MediaItem"
```

---

## Task 10: Update existing tests

**Files:**
- Modify: `tests/modules/Catalog/Catalog.WriteModel.Tests/MediaItems/Commands/ApproveMediaItemHandlerTests.cs`
- Modify: `tests/modules/Catalog/Catalog.WriteModel.Tests/MediaItems/Commands/SubmitForReviewHandlerTests.cs` (if exists)
- Delete: tests for deleted handlers (checkout, CR lifecycle)

- [ ] **Step 1: Find all test files referencing deleted types**

```bash
grep -r "IMediaChangeRequestQueryService\|CheckoutStatus\|CheckedOutBy\|SubmissionFailed\|MediaItemRevertedToDraft\|MediaItemCheckedOut\|MediaItemCheckedIn" \
  tests/modules/Catalog/ --include="*.cs" -l
```

- [ ] **Step 2: Update ApproveMediaItemHandlerTests**

Remove `_crService` mock. Update constructor call:

```csharp
private ApproveMediaItemHandler CreateHandler()
{
    return new ApproveMediaItemHandler(_repository.Object, _assetService.Object);
    // removed: _crService.Object
}
```

Remove any test cases that tested CR status gating (those scenarios are now handled by reviewer vote logic in ApproveReview).

- [ ] **Step 3: Delete test files for removed handlers**

```bash
# Find and delete tests for checkout handlers
find tests/ -name "*CheckOut*Tests*" -o -name "*CheckIn*Tests*" -o -name "*AbandonCheckout*Tests*" | xargs rm -f
```

- [ ] **Step 4: Run full test suite**

```bash
dotnet test tests/modules/Catalog/ -v
dotnet test tests/modules/ChangeRequests/ -v
```

Expected: All remaining tests pass.

- [ ] **Step 5: Commit**

```bash
git add -u
git commit -m "test(catalog): update tests for simplified lifecycle — remove checkout and CR mocks"
```

---

## Task 11: Update read model projectors

Read model projectors that project `CheckoutStatus`, `CheckedOutBy`, `CheckoutChangeRequestId`, `ActiveMediaChangeRequestId` need to be updated. These fields will no longer appear in domain events.

- [ ] **Step 1: Find affected projectors**

```bash
grep -r "CheckoutStatus\|CheckedOutBy\|CheckoutChangeRequestId\|ActiveMediaChangeRequestId\|RevertedToDraft\|SubmissionFailed" \
  src/modules/Catalog/Catalog.ReadModel/ --include="*.cs" -l
```

- [ ] **Step 2: For each projector found — remove deleted fields, add ReviewSession projection**

For each projector, remove properties that no longer exist in events. Add projection of the new `ReviewSession` data from `MediaItemSubmittedForReview`:

If there is a `MediaItemDetailProjector` or similar:
- Remove: `CheckoutStatus`, `CheckedOutBy`, `ActiveChangeRequestId`
- Add: `ReviewSessionId` (nullable), `Reviewers` (list with `ReviewerId` + `Decision`), `ReviewStartedAt`

- [ ] **Step 3: Update read model DTOs**

Find DTO/read model classes (likely in `Catalog.ReadModel/`) that exposed checkout fields. Remove them. Add reviewer tracking if the read model should surface current review state.

- [ ] **Step 4: Build ReadModel project**

```bash
dotnet build src/modules/Catalog/Catalog.ReadModel/
dotnet build src/modules/Catalog/Catalog.ReadModel.Infrastructure/
```

Expected: 0 errors.

- [ ] **Step 5: Run read model tests**

```bash
dotnet test tests/modules/Catalog/Catalog.ReadModel.Tests/ -v
```

Fix any failing projector or query tests.

- [ ] **Step 6: Commit**

```bash
git add -u
git commit -m "feat(catalog-read): update projectors — remove checkout fields, project ReviewSession state"
```

---

## Task 12: Update API endpoints

HTTP endpoints that exposed checkout/checkin and ChangeRequest lifecycle operations need to be removed or replaced.

- [ ] **Step 1: Find checkout and CR lifecycle endpoints**

```bash
grep -r "checkout\|checkin\|change-request" src/ --include="*.cs" -l -i | grep -i "endpoint\|controller\|route"
```

- [ ] **Step 2: Remove checkout endpoints**

Remove endpoint classes/routes for:
- `POST /catalog/items/{id}/checkout`
- `POST /catalog/items/{id}/checkin`
- `POST /catalog/items/{id}/checkout/abandon`
- `POST /catalog/items/{id}/checkout/force-release`
- `POST /change-requests` (CreateChangeRequest — checkout variant)
- `POST /change-requests/{id}/activate`
- `POST /change-requests/{id}/approve-review`
- `POST /change-requests/{id}/reject-review`
- `POST /change-requests/{id}/abandon`

- [ ] **Step 3: Add new review endpoints**

Add endpoints for the new reviewer-vote commands:
- `POST /catalog/items/{id}/review/approve` → `ApproveReviewCommand`
- `POST /catalog/items/{id}/review/reject` → `RejectReviewCommand`

Example endpoint (follow existing endpoint pattern in codebase):

```csharp
// POST /catalog/items/{mediaItemId}/review/approve
public sealed class ApproveReviewEndpoint : IEndpoint
{
    public void MapEndpoints(IEndpointRouteBuilder app)
    {
        app.MapPost("/catalog/items/{mediaItemId}/review/approve", HandleAsync)
           .RequireAuthorization();
    }

    private static async Task<IResult> HandleAsync(
        Guid mediaItemId,
        ApproveReviewRequest request,
        ICommandDispatcher dispatcher,
        ICurrentTenant currentTenant,
        CancellationToken ct)
    {
        var cmd = new ApproveReviewCommand(
            currentTenant.TenantId,
            new MediaItemId(mediaItemId),
            new MemberId(request.ReviewerId),
            DateTimeOffset.UtcNow);

        var result = await dispatcher.DispatchAsync(cmd, ct);
        return result.IsSuccess ? Results.Ok() : result.Error.ToHttpResult();
    }
}

public sealed record ApproveReviewRequest(Guid ReviewerId);
```

- [ ] **Step 4: Build API host**

```bash
dotnet build src/hosts/Api/
```

Expected: 0 errors.

- [ ] **Step 5: Commit**

```bash
git add -u
git commit -m "feat(api): remove checkout endpoints, add review/approve and review/reject endpoints"
```

---

## Task 13: Update integration event contracts

- [ ] **Step 1: Delete removed contract events**

```bash
rm src/modules/Catalog/Catalog.Contracts/Events/MediaItems/MediaItemCheckedOutIntegrationEvent.cs
rm src/modules/Catalog/Catalog.Contracts/Events/MediaItems/MediaItemCheckoutForceReleasedIntegrationEvent.cs
```

- [ ] **Step 2: Update MediaItemSubmittedForReviewIntegrationEvent**

Remove CR ID fields, add `ReviewSessionId` and `ReviewerIds`.

- [ ] **Step 3: Check for consumers of deleted contracts**

```bash
grep -r "MediaItemCheckedOutIntegrationEvent\|MediaItemCheckoutForceReleasedIntegrationEvent" src/ --include="*.cs" -l
```

Remove any handlers found.

- [ ] **Step 4: Build Contracts**

```bash
dotnet build src/modules/Catalog/Catalog.Contracts/
```

- [ ] **Step 5: Commit**

```bash
git add -u
git commit -m "chore(contracts): remove checkout integration events; update SubmittedForReview contract"
```

---

## Task 14: Full build and test

- [ ] **Step 1: Full solution build**

```bash
dotnet build src/
```

Expected: 0 errors, 0 warnings about missing types.

- [ ] **Step 2: Full test run**

```bash
dotnet test tests/ -v --logger "console;verbosity=normal"
```

Expected: All tests pass.

- [ ] **Step 3: Fix any remaining failures**

For each failing test, identify whether it tests deleted behaviour (delete the test) or updated behaviour (update the test).

- [ ] **Step 4: Commit**

```bash
git add -u
git commit -m "fix: resolve remaining build and test failures after lifecycle simplification"
```

---

## Task 15: Update spec documentation

**Files:**
- Modify: `projects/magiq-media/spec/contexts/Catalog/aggregates/MediaItem/mediaitem.write-model.md`
- Modify: `projects/magiq-media/spec/contexts/Catalog/aggregates/MediaItem/mediaitem.api.md`
- Modify: `projects/magiq-media/spec/contexts/Catalog/aggregates/MediaItem/mediaitem.scenarios.md`
- Modify: `projects/magiq-media/spec/contexts/Catalog/aggregates/MediaItem/mediaitem.scenarios.md`
- Modify: `projects/magiq-media/spec/contexts/ChangeRequests/aggregates/ChangeRequest/changerequest.write-model.md`
- Modify: `projects/magiq-media/spec/contexts/ChangeRequests/aggregates/ChangeRequest/changerequest.api.md`
- Modify: `projects/magiq-media/spec/contexts/ChangeRequests/aggregates/ChangeRequest/changerequest.scenarios.md`
- Modify: `projects/magiq-media/spec/contexts/Catalog/business-scenarios.md` (or aggregate-level file)
- Modify: `projects/magiq-media/spec/contexts/ChangeRequests/business-scenarios.md`

- [ ] **Step 1: Update mediaitem.write-model.md**

Replace the status state machine section with:

```markdown
## Status

| Value | Description |
|---|---|
| `Draft` | Editable. Initial state and state after rejection or withdrawal. |
| `UnderReview` | Submitted for review. Writes blocked until review concludes. |
| `Published` | Approved. Item is live. Requires Withdraw to return to Draft. |
| `Archived` | Terminal. No further operations permitted. |

## Status transitions

```
Draft ──SubmitForReview──► UnderReview ──all reviewers approve──► Published
                                      ──any reviewer rejects───► Draft
Draft ──Archive──────────► Archived
Published ──Withdraw─────► Draft
UnderReview ──Withdraw───► Draft
```

## Review lifecycle

Review is managed inline on the MediaItem via an embedded `ReviewSession`.

### SubmitForReview
- `Status` must be `Draft`
- All required metadata fields must be present
- All required asset roles must be filled with Active assets
- If `ReviewerIds` is empty: item auto-approves and transitions directly to `Published`
- If `ReviewerIds` is non-empty: `Status` → `UnderReview`, `ReviewSession` created with all reviewers in `Pending` state

### Reviewer vote
- Any reviewer in the session may call `ApproveReview` or `RejectReview`
- **Approve:** reviewer's decision recorded as `Approved`. When all non-withdrawn reviewers have approved, item transitions to `Published` and `CurrentVersionNumber` increments.
- **Reject:** reviewer's decision recorded as `Rejected`. Item immediately transitions back to `Draft`. Draft metadata is preserved for revision.

### ReviewSession
Embedded value object on MediaItem. Contains:
- `ReviewSessionId` — unique per submit cycle
- `CommentThreadId` (nullable) — reference to a `ChangeRequest` comment thread if one was created
- `Reviewers` — list of `ReviewerAssignment` (ReviewerId, Decision, AssignedAt, DecidedAt)
- `StartedAt`

## Removed operations (not supported)
- Checkout / Checkin — replaced by optimistic concurrency (version number on aggregate)
- AutoRevert — statuses Rejected, SubmissionFailed, Withdrawn no longer exist
```

- [ ] **Step 2: Update mediaitem.api.md**

Remove endpoint specs for:
- `POST /catalog/items/{id}/checkout`
- `POST /catalog/items/{id}/checkin`
- `POST /catalog/items/{id}/checkout/abandon`
- `POST /catalog/items/{id}/checkout/force-release`

Add endpoint specs for:
- `POST /catalog/items/{id}/review/approve`
- `POST /catalog/items/{id}/review/reject`

Update `POST /catalog/items/{id}/submit` to remove `checkoutChangeRequestId` field and document `reviewerIds` (array, may be empty for auto-approve) and `commentThreadId` (optional CR ID).

- [ ] **Step 3: Update mediaitem.scenarios.md**

Remove scenarios for:
- Checkout with and without change request
- Checkin
- Abandoned checkout
- Force release
- SubmissionFailed and resubmit
- Withdrawn status auto-revert

Add/update scenarios:
- Submit with no reviewers → auto-approve
- Submit with reviewers → all approve → publish
- Submit with reviewers → one rejects → returns to draft
- Reviewer tries to vote when not in session → error
- Reviewer votes twice → error

- [ ] **Step 4: Update ChangeRequest spec files**

In `changerequest.write-model.md`: Replace the lifecycle section with "ChangeRequest is a comment thread. It has no lifecycle status. It is created when a caller optionally wants a comment space during review."

Remove: status state machine, reviewer tracking, binding, ActivateForReview, ApproveReview, RejectReview, Abandon sections.

Keep: AddComment, EditComment, DeleteComment.

In `changerequest.api.md`: Remove all lifecycle endpoints. Keep comment endpoints.

- [ ] **Step 5: Update business scenarios index files**

In Catalog business scenarios: remove checkout/checkin scenarios, update submission scenarios to reflect inline review.

In ChangeRequests business scenarios: remove review lifecycle scenarios, update to comment-thread-only scenarios.

- [ ] **Step 6: Commit spec updates**

```bash
git add projects/magiq-media/spec/
git commit -m "docs(spec): update MediaItem and ChangeRequest specs — simplified lifecycle, inline review, comment-only CR"
```

---

## Self-Review

### Spec coverage check
| Requirement | Task |
|---|---|
| Remove CheckoutStatus, checkout methods | Tasks 3, 4, 5 |
| Embed ReviewSession in MediaItem | Tasks 1, 3 |
| Simplified MediaItemStatus (4 values) | Task 2 |
| Remove auto-revert states | Task 3 (Step 9 Apply handlers) |
| Explicit metadata rotation on Approve | Task 3 (Step 8) |
| No reviewers = auto-approve inline | Task 3 (Step 5), Task 7 |
| Reviewer votes on MediaItem directly | Tasks 3, 7 |
| ChangeRequest = comment-only | Task 9 |
| Delete sagas | Task 8 |
| Delete cross-module integration event handlers | Task 5 |
| New ApproveReview / RejectReview handlers | Task 7 |
| API endpoint updates | Task 12 |
| Contract cleanup | Task 13 |
| Spec docs updated | Task 15 |

### Type consistency check
- `ReviewSessionId` defined Task 1, used Tasks 2, 3, 7 ✅
- `ReviewerAssignment` defined Task 1, used Tasks 3, 7 ✅
- `ReviewerDecision` defined Task 1, used Tasks 1, 3 ✅
- `ReviewSession` defined Task 1, used Task 3 ✅
- `MediaItemStatus.Draft|UnderReview|Published|Archived` defined Task 2, used Tasks 3, 7 ✅
- `ApproveReviewCommand` defined Task 7, used Task 12 ✅
- `RejectReviewCommand` defined Task 7, used Task 12 ✅
- `MediaItemFactory.CreateUnderReviewWithSingleReviewer` defined Task 7 Step 8, used Tasks 7 Steps 1+5 ✅

### Placeholder scan
No TBD, TODO, or "similar to above" patterns present. All steps contain actual code or exact commands.

