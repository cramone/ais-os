# ChangeRequest + Review Session Integration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When a MediaItem is published with reviewers, automatically create a ChangeRequest comment thread linked to that review session — and restrict commenting to review participants (owner + reviewers), using a snapshot stored on the ChangeRequest at creation time.

**Architecture:** `PublishMediaItemHandler` pre-generates a `ChangeRequestId` when reviewers are present and passes it as `commentThreadId` to `SubmitForReview`. The `MediaItemPublicationRequested` integration event carries the ID and reviewer list to `MediaItemPublicationRequestedEventHandler` in the ChangeRequests module, which creates the CR with `ReviewSessionId` and a `ParticipantIds` snapshot. `ChangeRequest.AddComment` guards against non-participants using this snapshot. No synchronous cross-module dependency — Catalog never calls ChangeRequests directly.

**Tech Stack:** C# / .NET, event sourcing, XUnit + Moq, MediatR command handlers.

---

## New model summary

**ChangeRequest gains:**
- `ReviewSessionId` — links CR to the specific review session
- `ParticipantIds` — snapshot of [SubmittedBy] + ReviewerIds at creation time
- `IsParticipant(MemberId)` — used by AddComment guard

**PublishMediaItemHandler changes:**
- When `InitialReviewers.Any()`: generates `ChangeRequestId.New()`, passes it as `commentThreadId`
- Returns the CR ID in `PublishMediaItemResult`

**MediaItemPublicationRequestedEventHandler changes:**
- Already creates CR when `CommentThreadId` present
- Now also passes `ReviewSessionId` and `ParticipantIds` to `CreateChangeRequestCommand`

**AddComment gets participant guard:**
- `ChangeRequest.AddComment` returns `Forbidden` if commenter not in `ParticipantIds`

---

## File map

### Modified
| File | Change |
|---|---|
| `src/modules/ChangeRequests/ChangeRequests.Domain/Aggregates/Media/Events/ChangeRequestCreated.cs` | Add `ReviewSessionId`, `IReadOnlyList<MemberId> ParticipantIds` |
| `src/modules/ChangeRequests/ChangeRequests.Domain/Aggregates/Media/ChangeRequest.cs` | Store ReviewSessionId + participants; add `IsParticipant`; update `Create`; guard `AddComment` |
| `src/modules/ChangeRequests/ChangeRequests.WriteModel/Commands/CreateChangeRequest/CreateChangeRequestCommand.cs` | Add `ReviewSessionId`, `IReadOnlyList<MemberId> ParticipantIds` |
| `src/modules/ChangeRequests/ChangeRequests.WriteModel/Commands/CreateChangeRequest/CreateChangeRequestHandler.cs` | Pass new fields through to aggregate |
| `src/modules/ChangeRequests/ChangeRequests.WriteModel/IntegrationEvents/Consuming/Handlers/MediaItemPublicationRequestedEventHandler.cs` | Build participant list from event; pass ReviewSessionId + ParticipantIds to command |
| `src/modules/Catalog/Catalog.WriteModel/Commands/MediaItems/PublishMediaItem/PublishMediaItemHandler.cs` | Pre-generate CR ID when reviewers present; pass as commentThreadId; return in result |
| `src/modules/ChangeRequests/ChangeRequests.ReadModel/ReadModels/ChangeRequestDetailReadModel.cs` | Add `ReviewSessionId` |
| `src/modules/ChangeRequests/ChangeRequests.ReadModel/Projectors/ChangeRequestDetailProjector.cs` | Project `ReviewSessionId` from `ChangeRequestCreated` |

### New tests
| File | Purpose |
|---|---|
| `tests/modules/ChangeRequests/ChangeRequests.WriteModel.Tests/Commands/CreateChangeRequestHandlerTests.cs` | New fields round-trip |
| `tests/modules/ChangeRequests/ChangeRequests.WriteModel.Tests/Commands/AddCommentHandlerTests.cs` | Participant guard |

---

## Task 1: Update ChangeRequestCreated event + ChangeRequest aggregate

**Files:**
- Modify: `src/modules/ChangeRequests/ChangeRequests.Domain/Aggregates/Media/Events/ChangeRequestCreated.cs`
- Modify: `src/modules/ChangeRequests/ChangeRequests.Domain/Aggregates/Media/ChangeRequest.cs`

- [ ] **Step 1: Read both files in full**

Read:
- `src/modules/ChangeRequests/ChangeRequests.Domain/Aggregates/Media/Events/ChangeRequestCreated.cs`
- `src/modules/ChangeRequests/ChangeRequests.Domain/Aggregates/Media/ChangeRequest.cs`

- [ ] **Step 2: Update ChangeRequestCreated event**

Add two fields to the record. Read the current field list and append:

```csharp
[DomainEvent(nameof(ChangeRequestCreated))]
public sealed record ChangeRequestCreated(
    TenantId TenantId,
    ChangeRequestId ChangeRequestId,
    MediaItemId MediaItemId,
    MemberId InitiatedBy,
    ReviewSessionId ReviewSessionId,
    IReadOnlyList<MemberId> ParticipantIds,
    DateTimeOffset CreatedAt) : DomainEvent, IChangeRequestDomainEvent;
```

`ReviewSessionId` is from `Magiq.Media.Catalog.Aggregates.MediaItems.ValueObjects` — check existing usings in ChangeRequests.Domain. If `ReviewSessionId` lives in the Catalog namespace and ChangeRequests.Domain doesn't reference it, use `string ReviewSessionId` instead and add a `ReviewSessionId.From(string)` conversion where needed. Check existing using statements in `ChangeRequest.cs` to decide which type to use.

- [ ] **Step 3: Update ChangeRequest aggregate state fields**

Add private fields after existing ones:
```csharp
private ReviewSessionId _reviewSessionId;
private IReadOnlyList<MemberId> _participantIds = [];
```

Add public read-only property:
```csharp
public ReviewSessionId ReviewSessionId => _reviewSessionId;
```

- [ ] **Step 4: Update ChangeRequest.Create factory**

Update the static `Create` method signature to accept the new parameters:
```csharp
public static ChangeRequest Create(
    TenantId tenantId,
    ChangeRequestId id,
    MediaItemId mediaItemId,
    MemberId initiatedById,
    ReviewSessionId reviewSessionId,
    IReadOnlyList<MemberId> participantIds,
    DateTimeOffset createdAt)
{
    var cr = new ChangeRequest();
    cr.Raise(new ChangeRequestCreated(
        tenantId, id, mediaItemId, initiatedById,
        reviewSessionId, participantIds, createdAt));
    return cr;
}
```

- [ ] **Step 5: Add IsParticipant method**

```csharp
public bool IsParticipant(MemberId memberId)
    => _participantIds.Any(p => p == memberId);
```

- [ ] **Step 6: Update Apply(ChangeRequestCreated) to capture new fields**

Find the existing `Apply(ChangeRequestCreated e)` handler and add:
```csharp
private void Apply(ChangeRequestCreated e)
{
    Id = e.ChangeRequestId;
    TenantId = e.TenantId;
    MediaItemId = e.MediaItemId;
    CreatedById = e.InitiatedBy;
    _reviewSessionId = e.ReviewSessionId;
    _participantIds = e.ParticipantIds;
}
```

- [ ] **Step 7: Add participant guard to AddComment**

Find the `AddComment` method. Before the existing validation, add:
```csharp
if (!IsParticipant(authorId))
{
    return DomainError.Forbidden("Only review participants can comment on this thread.");
}
```

- [ ] **Step 8: Build ChangeRequests.Domain**

```bash
dotnet build "C:\Users\chase\OneDrive\repos\magiq-media\src\modules\ChangeRequests\ChangeRequests.Domain\ChangeRequests.Domain.csproj" 2>&1 | grep -E "error CS|Build succeeded|Build FAILED"
```

Fix all errors. If `ReviewSessionId` type causes a cross-assembly reference issue, switch to `string ReviewSessionId` and add appropriate conversions.

- [ ] **Step 9: Commit**

```bash
git -C "C:\Users\chase\OneDrive\repos\magiq-media" add src/modules/ChangeRequests/ChangeRequests.Domain/
git -C "C:\Users\chase\OneDrive\repos\magiq-media" commit -m "feat(change-requests): add ReviewSessionId + participant snapshot to ChangeRequest; guard AddComment to participants only"
```

---

## Task 2: Update CreateChangeRequestCommand and handler

**Files:**
- Modify: `src/modules/ChangeRequests/ChangeRequests.WriteModel/Commands/CreateChangeRequest/CreateChangeRequestCommand.cs`
- Modify: `src/modules/ChangeRequests/ChangeRequests.WriteModel/Commands/CreateChangeRequest/CreateChangeRequestHandler.cs`

- [ ] **Step 1: Read both files**

Read `CreateChangeRequestCommand.cs` and `CreateChangeRequestHandler.cs`.

- [ ] **Step 2: Update CreateChangeRequestCommand**

Add `ReviewSessionId` and `ParticipantIds` fields. Current record:
```csharp
public sealed record CreateChangeRequestCommand(
    TenantId TenantId,
    ChangeRequestId ChangeRequestId,
    MediaItemId MediaItemId,
    MemberId CreatedById,
    OccurredAt) : Command;
```

Updated (add two fields, preserve order):
```csharp
public sealed record CreateChangeRequestCommand(
    TenantId TenantId,
    ChangeRequestId ChangeRequestId,
    MediaItemId MediaItemId,
    MemberId CreatedById,
    ReviewSessionId ReviewSessionId,
    IReadOnlyList<MemberId> ParticipantIds,
    DateTimeOffset OccurredAt) : Command;
```

- [ ] **Step 3: Update CreateChangeRequestHandler**

Find `ChangeRequest.Create(...)` call in the handler and update to pass the new parameters:

```csharp
var changeRequest = ChangeRequest.Create(
    command.TenantId,
    command.ChangeRequestId,
    command.MediaItemId,
    command.CreatedById,
    command.ReviewSessionId,
    command.ParticipantIds,
    command.OccurredAt);
```

- [ ] **Step 4: Build ChangeRequests.WriteModel**

```bash
dotnet build "C:\Users\chase\OneDrive\repos\magiq-media\src\modules\ChangeRequests\ChangeRequests.WriteModel\ChangeRequests.WriteModel.csproj" 2>&1 | grep -E "error CS|Build succeeded|Build FAILED"
```

- [ ] **Step 5: Commit**

```bash
git -C "C:\Users\chase\OneDrive\repos\magiq-media" add src/modules/ChangeRequests/ChangeRequests.WriteModel/Commands/CreateChangeRequest/
git -C "C:\Users\chase\OneDrive\repos\magiq-media" commit -m "feat(change-requests): add ReviewSessionId and ParticipantIds to CreateChangeRequestCommand"
```

---

## Task 3: Update MediaItemPublicationRequestedEventHandler

**Files:**
- Modify: `src/modules/ChangeRequests/ChangeRequests.WriteModel/IntegrationEvents/Consuming/Handlers/MediaItemPublicationRequestedEventHandler.cs`

Current handler (lines 31-36) builds `CreateChangeRequestCommand` with 5 params. Must add `ReviewSessionId` and `ParticipantIds`.

- [ ] **Step 1: Read the handler in full**

Read `MediaItemPublicationRequestedEventHandler.cs`.

Also check `MediaItemSubmittedForReviewIntegrationEvent` — confirm it has `ReviewSessionId` (string), `ReviewerIds` (IReadOnlyList<string>), and `SubmittedBy` (string).

- [ ] **Step 2: Build participant list from event**

The participant snapshot = submitter + all reviewers:

```csharp
public async Task HandleAsync(MediaItemSubmittedForReviewIntegrationEvent e, IMessageHandlingContext context, CancellationToken cancellationToken = default)
{
    if (string.IsNullOrEmpty(e.CommentThreadId))
    {
        return;
    }

    // Build participant snapshot: owner (submitter) + all assigned reviewers
    var participantIds = e.ReviewerIds
        .Select(MemberId.From)
        .Prepend(MemberId.From(e.SubmittedBy))
        .ToList();

    var command = new CreateChangeRequestCommand(
        new TenantId(e.TenantId),
        ChangeRequestId.From(e.CommentThreadId),
        MediaItemId.From(e.MediaItemId),
        MemberId.From(e.SubmittedBy),
        ReviewSessionId.From(e.ReviewSessionId),
        participantIds,
        e.SubmittedAt);

    var result = await commandDispatcher.SendAsync(command, cancellationToken);
    if (!result.IsSuccess)
    {
        var exception = result.Error.Exception ?? new DomainOperationException(result.Error.ErrorMessage, null);
        logger.LogError(exception, "Failed to create ChangeRequest for MediaItem {MediaItemId}.", e.MediaItemId);
    }
}
```

Note: `ReviewSessionId.From(string)` — check if this factory method exists in the Catalog ValueObjects type. If ReviewSessionId is a `readonly record struct ReviewSessionId(Guid Value)`, use `new ReviewSessionId(Guid.Parse(e.ReviewSessionId))` instead.

- [ ] **Step 3: Build**

```bash
dotnet build "C:\Users\chase\OneDrive\repos\magiq-media\src\modules\ChangeRequests\ChangeRequests.WriteModel\ChangeRequests.WriteModel.csproj" 2>&1 | grep -E "error CS|Build succeeded|Build FAILED"
```

Fix any type resolution errors.

- [ ] **Step 4: Commit**

```bash
git -C "C:\Users\chase\OneDrive\repos\magiq-media" add src/modules/ChangeRequests/ChangeRequests.WriteModel/IntegrationEvents/Consuming/Handlers/MediaItemPublicationRequestedEventHandler.cs
git -C "C:\Users\chase\OneDrive\repos\magiq-media" commit -m "feat(change-requests): pass ReviewSessionId and participant snapshot when creating comment thread CR"
```

---

## Task 4: Pre-generate CR ID in PublishMediaItemHandler

**Files:**
- Modify: `src/modules/Catalog/Catalog.WriteModel/Commands/MediaItems/PublishMediaItem/PublishMediaItemHandler.cs`

Current line 74:
```csharp
var result = mediaItem.SubmitForReview(command.RequestingUser, reviewSessionId, null, command.InitialReviewers, command.OccurredAt);
```
Current line 82:
```csharp
return new PublishMediaItemResult(null);
```

- [ ] **Step 1: Write failing test**

Read `tests/modules/Catalog/Catalog.WriteModel.Tests/MediaItems/Commands/` to find existing Publish handler tests if any. Find the test project and add:

```csharp
// tests/modules/Catalog/Catalog.WriteModel.Tests/MediaItems/Commands/PublishMediaItemHandlerTests.cs
// (add to existing file or create new)

[Fact]
public async Task HandleAsync_WithReviewers_ReturnsChangeRequestId()
{
    // Arrange
    var item = MediaItemFactory.Build(_tenant, _itemId);
    var reviewerId = new MemberId(Guid.NewGuid());

    _repository.Setup(r => r.GetByIdAsync(_tenant, _itemId, CancellationToken.None)).ReturnsAsync(item);
    _profileRepository.Setup(r => r.GetByIdAsync(_tenant, item.MediaProfileId, CancellationToken.None))
        .ReturnsAsync(MediaProfileFactory.CreatePublished(_tenant, item.MediaProfileId));
    _assetService.Setup(s => s.GetManyAsync(_tenant, It.IsAny<IReadOnlyList<AssetId>>(), CancellationToken.None))
        .ReturnsAsync(new List<MediaItemAssetReference>());
    _repository.Setup(r => r.SaveAsync(It.IsAny<MediaItem>(), CancellationToken.None)).Returns(Task.CompletedTask);

    var cmd = new PublishMediaItemCommand(_tenant, _itemId, new MemberId(Guid.NewGuid()), new[] { reviewerId }, DateTimeOffset.UtcNow);

    // Act
    var result = await CreateHandler().HandleAsync(cmd, new Mock<ICommandHandlingContext>().Object, CancellationToken.None);

    // Assert
    result.IsSuccess.Should().BeTrue();
    result.Value.ChangeRequestId.Should().NotBeNull("a comment thread CR ID should be pre-generated when reviewers are present");
}

[Fact]
public async Task HandleAsync_WithoutReviewers_ReturnsNullChangeRequestId()
{
    var item = MediaItemFactory.Build(_tenant, _itemId);

    _repository.Setup(r => r.GetByIdAsync(_tenant, _itemId, CancellationToken.None)).ReturnsAsync(item);
    _profileRepository.Setup(r => r.GetByIdAsync(_tenant, item.MediaProfileId, CancellationToken.None))
        .ReturnsAsync(MediaProfileFactory.CreatePublished(_tenant, item.MediaProfileId));
    _assetService.Setup(s => s.GetManyAsync(_tenant, It.IsAny<IReadOnlyList<AssetId>>(), CancellationToken.None))
        .ReturnsAsync(new List<MediaItemAssetReference>());
    _repository.Setup(r => r.SaveAsync(It.IsAny<MediaItem>(), CancellationToken.None)).Returns(Task.CompletedTask);

    var cmd = new PublishMediaItemCommand(_tenant, _itemId, new MemberId(Guid.NewGuid()), Array.Empty<MemberId>(), DateTimeOffset.UtcNow);

    var result = await CreateHandler().HandleAsync(cmd, new Mock<ICommandHandlingContext>().Object, CancellationToken.None);

    result.IsSuccess.Should().BeTrue();
    result.Value.ChangeRequestId.Should().BeNull("no comment thread needed without reviewers");
}
```

Adapt factory/mock setup to match the exact pattern in existing handler tests. Check what `MediaItemFactory.Build` produces and whether MediaProfile mock needs asset definitions.

- [ ] **Step 2: Run tests to confirm they fail**

```bash
dotnet test "C:\Users\chase\OneDrive\repos\magiq-media\tests\modules\Catalog\Catalog.WriteModel.Tests" --filter "PublishMediaItemHandlerTests" -v 2>&1 | tail -10
```

Expected: fails (handler still returns `null`).

- [ ] **Step 3: Update PublishMediaItemHandler**

Replace lines 73-82 with:

```csharp
var reviewSessionId = ReviewSessionId.New();

// Pre-generate a comment thread ID when reviewers are present.
// The ChangeRequest is created asynchronously by MediaItemPublicationRequestedEventHandler
// in the ChangeRequests module — but the ID is returned immediately so callers can start commenting.
ChangeRequestId? commentThreadId = command.InitialReviewers.Any()
    ? ChangeRequestId.New()
    : null;

var result = mediaItem.SubmitForReview(
    command.RequestingUser,
    reviewSessionId,
    commentThreadId,
    command.InitialReviewers,
    command.OccurredAt);

if (!result.IsSuccess)
{
    return result.Error;
}

await repository.SaveAsync(mediaItem, cancellationToken);

return new PublishMediaItemResult(commentThreadId);
```

- [ ] **Step 4: Run tests — confirm they pass**

```bash
dotnet test "C:\Users\chase\OneDrive\repos\magiq-media\tests\modules\Catalog\Catalog.WriteModel.Tests" --filter "PublishMediaItemHandlerTests" -v 2>&1 | tail -10
```

- [ ] **Step 5: Build Catalog.WriteModel**

```bash
dotnet build "C:\Users\chase\OneDrive\repos\magiq-media\src\modules\Catalog\Catalog.WriteModel\Catalog.WriteModel.csproj" 2>&1 | grep -E "error CS|Build succeeded|Build FAILED"
```

- [ ] **Step 6: Commit**

```bash
git -C "C:\Users\chase\OneDrive\repos\magiq-media" add src/modules/Catalog/Catalog.WriteModel/Commands/MediaItems/PublishMediaItem/PublishMediaItemHandler.cs tests/modules/Catalog/Catalog.WriteModel.Tests/MediaItems/Commands/PublishMediaItemHandlerTests.cs
git -C "C:\Users\chase\OneDrive\repos\magiq-media" commit -m "feat(catalog): pre-generate comment thread CR ID when publishing with reviewers"
```

---

## Task 5: Update ChangeRequest read model

**Files:**
- Modify: `src/modules/ChangeRequests/ChangeRequests.ReadModel/ReadModels/ChangeRequestDetailReadModel.cs`
- Modify: `src/modules/ChangeRequests/ChangeRequests.ReadModel/Projectors/ChangeRequestDetailProjector.cs`

- [ ] **Step 1: Read both files in full**

Read both files.

- [ ] **Step 2: Add ReviewSessionId to ChangeRequestDetailReadModel**

Find the read model record/class. Add `ReviewSessionId` (string) field. Follow the exact pattern of existing fields.

- [ ] **Step 3: Update ChangeRequestDetailProjector to project ReviewSessionId**

Find the `ApplyAsync(ChangeRequestCreated e, ...)` handler in the projector. Add:

```csharp
model.ReviewSessionId = e.ReviewSessionId.ToString(); // or e.ReviewSessionId.Value.ToString() depending on type
```

Match the exact projection pattern used for other fields.

- [ ] **Step 4: Build read model**

```bash
dotnet build "C:\Users\chase\OneDrive\repos\magiq-media\src\modules\ChangeRequests\ChangeRequests.ReadModel\ChangeRequests.ReadModel.csproj" 2>&1 | grep -E "error CS|Build succeeded|Build FAILED"
dotnet build "C:\Users\chase\OneDrive\repos\magiq-media\src\modules\ChangeRequests\ChangeRequests.ReadModel.Infrastructure\ChangeRequests.ReadModel.Infrastructure.csproj" 2>&1 | grep -E "error CS|Build succeeded|Build FAILED"
```

- [ ] **Step 5: Commit**

```bash
git -C "C:\Users\chase\OneDrive\repos\magiq-media" add src/modules/ChangeRequests/ChangeRequests.ReadModel/
git -C "C:\Users\chase\OneDrive\repos\magiq-media" commit -m "feat(change-requests-read): project ReviewSessionId onto ChangeRequestDetailReadModel"
```

---

## Task 6: Full build, tests, and spec update

**Files:**
- Full solution
- `projects/magiq-media/spec/contexts/ChangeRequests/aggregates/MediaChangeRequest/mediachangerequest.write-model.md`
- `projects/magiq-media/spec/contexts/ChangeRequests/aggregates/MediaChangeRequest/mediachangerequest.scenarios.md`
- `projects/magiq-media/spec/contexts/Catalog/aggregates/MediaItem/mediaitem.write-model.md`
- `projects/magiq-media/spec/contexts/Catalog/aggregates/MediaItem/mediaitem.scenarios.md`

- [ ] **Step 1: Full solution build**

```bash
dotnet build "C:\Users\chase\OneDrive\repos\magiq-media\src\" 2>&1 | grep -E "error CS|Build succeeded|Build FAILED" | head -20
```

Fix all errors.

- [ ] **Step 2: Full test run**

```bash
dotnet test "C:\Users\chase\OneDrive\repos\magiq-media\tests\modules\" --logger "console;verbosity=minimal" 2>&1 | tail -5
```

Fix any failures.

- [ ] **Step 3: Run integration tests**

```bash
dotnet test "C:\Users\chase\OneDrive\repos\magiq-media\tests\integration\" --logger "console;verbosity=minimal" 2>&1 | tail -5
```

- [ ] **Step 4: Update mediachangerequest.write-model.md**

Read the file. Update:
- Add `ReviewSessionId` to state table
- Add `ParticipantIds` (snapshot of owner + reviewers, stored at creation) to state table
- Update `AddComment` precondition: "Commenter must be a review participant (owner or reviewer in the linked ReviewSession)"
- Add note: "ChangeRequest is automatically created by the system when a MediaItem is published with reviewers. Callers do not create ChangeRequests directly."

- [ ] **Step 5: Update mediachangerequest.scenarios.md**

Add scenario: "Reviewer comments during review — commenter is participant → succeeds"
Add scenario: "Non-participant tries to comment → 403 Forbidden"

- [ ] **Step 6: Update mediaitem.write-model.md**

In the Publish / SubmitForReview section, add:
"When `ReviewerIds` is non-empty, a `ChangeRequest` comment thread is automatically created and its ID is returned in the response as `commentThreadId`. Review participants (owner + reviewers) can post comments to this thread during the review cycle."

- [ ] **Step 7: Update mediaitem.scenarios.md**

In the "Submit with reviewers → all approve" scenario, add step: "Client uses `commentThreadId` from publish response to post comments to the review thread."

- [ ] **Step 8: Commit**

```bash
git -C "C:\Users\chase\OneDrive\repos\magiq-media" add -u
git -C "C:\Users\chase\OneDrive\repos\magiq-media" commit -m "fix: resolve any remaining build/test failures after CR+review integration"
```

---

## Self-Review

### Spec coverage
| Requirement | Task |
|---|---|
| CR created automatically when publishing with reviewers | Task 4 (pre-generate ID) + Task 3 (event handler) |
| ReviewSessionId stored on CR | Tasks 1, 3 |
| Participant snapshot on CR | Tasks 1, 3 |
| AddComment guards non-participants | Task 1 |
| CommentThreadId returned from publish endpoint | Task 4 (result flows through existing endpoint) |
| Read model projects ReviewSessionId | Task 5 |
| Full build + tests | Task 6 |
| Spec updated | Task 6 |

### Type consistency
- `ReviewSessionId` — in Catalog.Domain ValueObjects. ChangeRequests.Domain references Catalog.Domain (check .csproj). If no reference exists, use `string ReviewSessionId` in the domain event and convert at the boundary.
- `ChangeRequestId.New()` — static factory on `ChangeRequestId` value object in Catalog.Domain ✅
- `IsParticipant(MemberId)` — defined Task 1, used Task 1 (AddComment guard) ✅
- `PublishMediaItemResult.ChangeRequestId` — already exists (returns null today), Task 4 populates it ✅

### Placeholder scan
No TBD or "similar to above" patterns present.

### Cross-module dependency note
`MediaItemPublicationRequestedEventHandler` in ChangeRequests references `ReviewSessionId` from `Magiq.Media.Catalog.Aggregates.MediaItems.ValueObjects`. Verify `ChangeRequests.WriteModel.csproj` already references `Catalog.Domain` (it should — it already uses `MediaItemId` from there). If not, add the project reference.
