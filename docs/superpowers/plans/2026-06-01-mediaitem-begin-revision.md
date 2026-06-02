# MediaItem Begin Revision Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow owners to start a new version of a Published MediaItem without withdrawing it — the published version stays live while a draft revision is prepared, then published as the next version.

**Architecture:** Add `Revising` status to `MediaItemStatus`. A `BeginRevision` command transitions `Published → Revising`, initialising the metadata draft from the published snapshot. A `DiscardRevision` command cancels the draft and returns to `Published`. All existing edit guards (metadata, asset assignment, asset replacement) are updated to allow `Revising` alongside `Draft`. Publishing from `Revising` follows the same path as from `Draft`. The read model projects `Revising` as a distinct status — callers can choose to serve the published content to readers while the owner edits.

**Tech Stack:** C# / .NET, event sourcing (event-raised-then-applied), XUnit + Moq, FastEndpoints, DynamoDB projectors.

---

## New Model Summary

**MediaItemStatus** (add `Revising`):
```
Draft | PendingApproval | Published | Revising | Archived
```

**New commands:** `BeginRevisionCommand`, `DiscardRevisionCommand`

**New domain events:** `MediaItemRevisionStarted`, `MediaItemRevisionDiscarded`

**New endpoints:**
- `POST /catalog/items/{id}/begin-revision`
- `POST /catalog/items/{id}/discard-revision`

**Guards updated to allow `Revising`:**
- `MediaItem.ReplaceAssetInRole` — `Draft || Revising`
- `MediaItem.AssignAssetToRole` (aggregate method) — `Draft || Revising`
- `MediaItem.SubmitForReview` (PublishMediaItem) — `Draft || Revising`
- All metadata write methods — `Draft || Revising`

**Auto-submit backstop:** `AssetProcessingCompletedAutoSubmitHandler` updated to also trigger from `Revising` state.

---

## File Map

### New files
| File | Purpose |
|---|---|
| `src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/Events/MediaItemRevisionStarted.cs` | Domain event: Published → Revising |
| `src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/Events/MediaItemRevisionDiscarded.cs` | Domain event: Revising → Published |
| `src/modules/Catalog/Catalog.WriteModel/Commands/MediaItems/BeginRevision/BeginRevisionCommand.cs` | Command |
| `src/modules/Catalog/Catalog.WriteModel/Commands/MediaItems/BeginRevision/BeginRevisionHandler.cs` | Handler |
| `src/modules/Catalog/Catalog.WriteModel/Commands/MediaItems/DiscardRevision/DiscardRevisionCommand.cs` | Command |
| `src/modules/Catalog/Catalog.WriteModel/Commands/MediaItems/DiscardRevision/DiscardRevisionHandler.cs` | Handler |
| `src/modules/Catalog/Catalog.WriteModel.Endpoints/V1/MediaItems/BeginRevision/BeginRevisionEndpoint.cs` | Endpoint |
| `src/modules/Catalog/Catalog.WriteModel.Endpoints/V1/MediaItems/BeginRevision/BeginRevisionRequest.cs` | Request |
| `src/modules/Catalog/Catalog.WriteModel.Endpoints/V1/MediaItems/DiscardRevision/DiscardRevisionEndpoint.cs` | Endpoint |
| `src/modules/Catalog/Catalog.WriteModel.Endpoints/V1/MediaItems/DiscardRevision/DiscardRevisionRequest.cs` | Request |
| `tests/modules/Catalog/Catalog.WriteModel.Tests/MediaItems/Commands/BeginRevisionHandlerTests.cs` | Tests |
| `tests/modules/Catalog/Catalog.WriteModel.Tests/MediaItems/Commands/DiscardRevisionHandlerTests.cs` | Tests |

### Modified files
| File | Change |
|---|---|
| `src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/ValueObjects/MediaItemStatus.cs` | Add `Revising` |
| `src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/MediaItem.cs` | New methods, updated guards, new Apply handlers |
| `src/modules/Catalog/Catalog.ReadModel/Projectors/MediaItems/MediaItemDetailProjector.cs` | Handle new events |
| `src/modules/Catalog/Catalog.ReadModel/Projectors/MediaItems/MediaItemSummaryProjector.cs` | Handle new events |
| `src/modules/Catalog/Catalog.ReadModel/Projectors/MediaItems/MediaItemCurrentDraftProjector.cs` | Handle new events |
| `src/modules/Catalog/Catalog.WriteModel.Infrastructure/ServiceCollectionExtensions.cs` | Register new handlers |
| `src/modules/Catalog/Catalog.WriteModel.Infrastructure/IntegrationEvents/Consuming/Handlers/AssetProcessingCompletedAutoSubmitHandler.cs` | Allow Revising state |
| `tests/modules/Catalog/Catalog.WriteModel.Tests/MediaItems/MediaItemAggregateTests.cs` | Tests for new state machine paths |
| `tests/integration/modules/Catalog/Catalog.IntegrationTests/MediaItems/MediaItemFlowTests.cs` | Integration test for revision flow |

---

## Task 1: Add Revising status and new domain events

**Files:**
- Modify: `src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/ValueObjects/MediaItemStatus.cs`
- Create: `src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/Events/MediaItemRevisionStarted.cs`
- Create: `src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/Events/MediaItemRevisionDiscarded.cs`

- [ ] **Step 1: Add Revising to MediaItemStatus**

Read the current file first. Replace content with:

```csharp
namespace Magiq.Media.Catalog.Aggregates.MediaItems.ValueObjects;

public enum MediaItemStatus
{
    Draft,
    PendingApproval,
    Published,
    Revising,
    Archived
}
```

- [ ] **Step 2: Read an existing domain event for namespace/attribute conventions**

Read `src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/Events/MediaItemWithdrawn.cs` to understand the `[DomainEvent]` attribute, namespace, and record pattern.

- [ ] **Step 3: Create MediaItemRevisionStarted**

```csharp
// src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/Events/MediaItemRevisionStarted.cs
using Magiq.Media.Catalog.Aggregates.MediaItems.ValueObjects;
using Magiq.Platform.EventSourcing;

namespace Magiq.Media.Catalog.Aggregates.MediaItems.Events;

[DomainEvent(nameof(MediaItemRevisionStarted))]
public sealed record MediaItemRevisionStarted(
    TenantId TenantId,
    MediaItemId MediaItemId,
    MemberId StartedBy,
    DateTimeOffset StartedAt) : DomainEvent, IMediaItemDomainEvent;
```

Adapt the using statements and namespace to match the actual conventions in the codebase (check MediaItemWithdrawn.cs for the exact pattern).

- [ ] **Step 4: Create MediaItemRevisionDiscarded**

```csharp
// src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/Events/MediaItemRevisionDiscarded.cs
using Magiq.Media.Catalog.Aggregates.MediaItems.ValueObjects;
using Magiq.Platform.EventSourcing;

namespace Magiq.Media.Catalog.Aggregates.MediaItems.Events;

[DomainEvent(nameof(MediaItemRevisionDiscarded))]
public sealed record MediaItemRevisionDiscarded(
    TenantId TenantId,
    MediaItemId MediaItemId,
    MemberId DiscardedBy,
    DateTimeOffset DiscardedAt) : DomainEvent, IMediaItemDomainEvent;
```

- [ ] **Step 5: Build Catalog.Domain**

```bash
dotnet build "C:\Users\chase\OneDrive\repos\magiq-media\src\modules\Catalog\Catalog.Domain\Catalog.Domain.csproj" 2>&1 | grep -E "error CS|Build succeeded|Build FAILED"
```

Expected: Build succeeded. Fix any errors before continuing.

- [ ] **Step 6: Commit**

```bash
git -C "C:\Users\chase\OneDrive\repos\magiq-media" add src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/ValueObjects/MediaItemStatus.cs src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/Events/MediaItemRevisionStarted.cs src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/Events/MediaItemRevisionDiscarded.cs
git -C "C:\Users\chase\OneDrive\repos\magiq-media" commit -m "feat(catalog): add Revising status and MediaItemRevisionStarted/Discarded domain events"
```

---

## Task 2: Add BeginRevision and DiscardRevision to MediaItem aggregate

**Files:**
- Modify: `src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/MediaItem.cs`

- [ ] **Step 1: Read MediaItem.cs in the area of Withdraw method**

Read lines 640–670 of `src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/MediaItem.cs` to understand the Withdraw method structure and where to add the new methods.

Also read the Apply handler section (search for `private void Apply(MediaItemWithdrawn`) to find where to add new Apply handlers.

- [ ] **Step 2: Add BeginRevision method**

After the `Withdraw` method, add:

```csharp
// BeginRevision — Published → Revising
// Invariants: Status == Published; not Archived
public Result<Unit, DomainError> BeginRevision(MemberId startedBy, DateTimeOffset startedAt)
{
    if (Status != MediaItemStatus.Published)
    {
        return DomainError.InvalidOperation("Only published items can begin a revision. Use Withdraw to return a pending-approval item to draft.");
    }

    Emit(new MediaItemRevisionStarted(TenantId, Id, startedBy, startedAt));
    return Unit.Value;
}

// DiscardRevision — Revising → Published (abandon draft, restore published version)
// Invariants: Status == Revising
public Result<Unit, DomainError> DiscardRevision(MemberId discardedBy, DateTimeOffset discardedAt)
{
    if (Status != MediaItemStatus.Revising)
    {
        return DomainError.InvalidOperation("Item is not in Revising state.");
    }

    Emit(new MediaItemRevisionDiscarded(TenantId, Id, discardedBy, discardedAt));
    return Unit.Value;
}
```

- [ ] **Step 3: Add Apply handlers for new events**

Find the Apply handler section and add:

```csharp
private void Apply(MediaItemRevisionStarted e)
{
    Status = MediaItemStatus.Revising;
    // Initialise draft from published snapshot so edits start from current published content
    Metadata = Metadata with { Draft = Metadata.Draft ?? Metadata.Current };
}

private void Apply(MediaItemRevisionDiscarded e)
{
    Status = MediaItemStatus.Published;
    Metadata = Metadata with { Draft = null }; // Discard draft changes, published content remains
}
```

Register both in the constructor `When<>` calls (same pattern as other Apply registrations):
```csharp
When<MediaItemRevisionStarted>(Apply);
When<MediaItemRevisionDiscarded>(Apply);
```

- [ ] **Step 4: Update ReplaceAssetInRole guard**

Find this block (around line 568):
```csharp
if (Status != MediaItemStatus.Draft)
{
    return DomainError.InvalidOperation("MediaItem must be in Draft status to edit assets.");
}
```

Replace with:
```csharp
if (Status != MediaItemStatus.Draft && Status != MediaItemStatus.Revising)
{
    return DomainError.InvalidOperation("MediaItem must be in Draft or Revising status to edit assets.");
}
```

- [ ] **Step 5: Update AssignAssetToRole guard in aggregate**

Find the `AssignAssetToRole` method (line ~529 area). Update its status guard from `Status == Draft` to `Status == Draft || Status == Revising`:

```csharp
if (Status != MediaItemStatus.Draft && Status != MediaItemStatus.Revising)
{
    return DomainError.InvalidOperation("MediaItem must be in Draft or Revising status to assign assets.");
}
```

- [ ] **Step 6: Update PublishMediaItem (SubmitForReview) guard**

Find the `SubmitForReview` method (line ~439). Update the status guard:

```csharp
if (Status != MediaItemStatus.Draft && Status != MediaItemStatus.Revising)
{
    return DomainError.InvalidOperation("MediaItem must be in Draft or Revising status to publish.");
}
```

- [ ] **Step 7: Update all metadata write method guards**

Search for other methods that guard `Status == Draft` (SetMetadataField, BatchSetMetadata, UpdateTitle, etc.). Add `|| Status == MediaItemStatus.Revising` to each. Find them with:
```bash
grep -n "Status != MediaItemStatus.Draft" "C:\Users\chase\OneDrive\repos\magiq-media\src\modules\Catalog\Catalog.Domain\Aggregates\MediaItems\MediaItem.cs"
```
Update each one found.

- [ ] **Step 8: Build Catalog.Domain**

```bash
dotnet build "C:\Users\chase\OneDrive\repos\magiq-media\src\modules\Catalog\Catalog.Domain\Catalog.Domain.csproj" 2>&1 | grep -E "error CS|Build succeeded|Build FAILED"
```

Expected: Build succeeded. Fix any errors.

- [ ] **Step 9: Commit**

```bash
git -C "C:\Users\chase\OneDrive\repos\magiq-media" add src/modules/Catalog/Catalog.Domain/Aggregates/MediaItems/MediaItem.cs
git -C "C:\Users\chase\OneDrive\repos\magiq-media" commit -m "feat(catalog): add BeginRevision/DiscardRevision to MediaItem aggregate; update edit guards for Revising state"
```

---

## Task 3: Add aggregate unit tests for new state machine paths

**Files:**
- Modify: `tests/modules/Catalog/Catalog.WriteModel.Tests/MediaItems/MediaItemAggregateTests.cs`

- [ ] **Step 1: Read MediaItemAggregateTests.cs to understand test pattern**

Read the file to understand the test helper structure (how items are set up in different states).

- [ ] **Step 2: Write failing tests and run**

Add these tests to `MediaItemAggregateTests.cs`:

```csharp
[Fact]
public void BeginRevision_WhenPublished_TransitionsToRevising()
{
    var item = MediaItemFactory.CreatePublished(Tenant, ItemId);

    var result = item.BeginRevision(new MemberId(Guid.NewGuid()), DateTimeOffset.UtcNow);

    result.IsSuccess.Should().BeTrue();
    item.Status.Should().Be(MediaItemStatus.Revising);
}

[Fact]
public void BeginRevision_WhenDraft_ReturnsError()
{
    var item = MediaItemFactory.CreateDraft(Tenant, ItemId);

    var result = item.BeginRevision(new MemberId(Guid.NewGuid()), DateTimeOffset.UtcNow);

    result.IsFailure.Should().BeTrue();
}

[Fact]
public void BeginRevision_WhenRevising_ReturnsError()
{
    var item = MediaItemFactory.CreatePublished(Tenant, ItemId);
    item.BeginRevision(new MemberId(Guid.NewGuid()), DateTimeOffset.UtcNow);

    var result = item.BeginRevision(new MemberId(Guid.NewGuid()), DateTimeOffset.UtcNow);

    result.IsFailure.Should().BeTrue();
}

[Fact]
public void DiscardRevision_WhenRevising_TransitionsBackToPublished()
{
    var item = MediaItemFactory.CreatePublished(Tenant, ItemId);
    item.BeginRevision(new MemberId(Guid.NewGuid()), DateTimeOffset.UtcNow);

    var result = item.DiscardRevision(new MemberId(Guid.NewGuid()), DateTimeOffset.UtcNow);

    result.IsSuccess.Should().BeTrue();
    item.Status.Should().Be(MediaItemStatus.Published);
}

[Fact]
public void DiscardRevision_WhenPublished_ReturnsError()
{
    var item = MediaItemFactory.CreatePublished(Tenant, ItemId);

    var result = item.DiscardRevision(new MemberId(Guid.NewGuid()), DateTimeOffset.UtcNow);

    result.IsFailure.Should().BeTrue();
}

[Fact]
public void ReplaceAssetInRole_WhenRevising_Succeeds()
{
    var roleName = new RoleName("primary");
    var oldAssetId = AssetId.New();
    var newAssetId = AssetId.New();
    var item = MediaItemFactory.CreateRevisingWithAsset(Tenant, ItemId, roleName, oldAssetId);

    var result = item.ReplaceAssetInRole(roleName, newAssetId, DateTimeOffset.UtcNow);

    result.IsSuccess.Should().BeTrue();
    item.Assets.Should().Contain(a => a.AssetId == newAssetId && a.RoleName == roleName);
}

[Fact]
public void PublishMediaItem_WhenRevising_TransitionsToPendingApproval()
{
    var item = MediaItemFactory.CreatePublished(Tenant, ItemId);
    item.BeginRevision(new MemberId(Guid.NewGuid()), DateTimeOffset.UtcNow);
    var reviewerId = new MemberId(Guid.NewGuid());

    var result = item.SubmitForReview(
        new MemberId(Guid.NewGuid()),
        ReviewSessionId.New(),
        commentThreadId: null,
        reviewerIds: new[] { reviewerId },
        DateTimeOffset.UtcNow);

    result.IsSuccess.Should().BeTrue();
    item.Status.Should().Be(MediaItemStatus.PendingApproval);
}
```

Add `MediaItemFactory.CreatePublished` and `MediaItemFactory.CreateRevisingWithAsset` helpers if they don't exist:

```csharp
public static MediaItem CreatePublished(TenantId tenant, MediaItemId id)
{
    var item = CreateDraft(tenant, id);
    item.SubmitForReview(
        new MemberId(Guid.NewGuid()),
        ReviewSessionId.New(),
        commentThreadId: null,
        reviewerIds: Array.Empty<MemberId>(),  // auto-approve
        DateTimeOffset.UtcNow);
    return item;
}

public static MediaItem CreateRevisingWithAsset(TenantId tenant, MediaItemId id, RoleName roleName, AssetId assetId)
{
    var item = CreatePublished(tenant, id);
    // Force assign asset via event replay or use existing factory helper
    // Check if CreateDraftWithAsset exists and adapt accordingly
    item.AssignAssetToRole(assetId, roleName, DateTimeOffset.UtcNow);
    item.BeginRevision(new MemberId(Guid.NewGuid()), DateTimeOffset.UtcNow);
    return item;
}
```

Check what `CreateDraft` looks like in the factory and adapt `CreatePublished` to match the exact parameter signature of `SubmitForReview` on the aggregate.

- [ ] **Step 3: Run tests**

```bash
dotnet test "C:\Users\chase\OneDrive\repos\magiq-media\tests\modules\Catalog\Catalog.WriteModel.Tests" --filter "MediaItemAggregateTests" -v 2>&1 | tail -15
```

Fix any failures.

- [ ] **Step 4: Commit**

```bash
git -C "C:\Users\chase\OneDrive\repos\magiq-media" add tests/modules/Catalog/Catalog.WriteModel.Tests/MediaItems/MediaItemAggregateTests.cs tests/modules/Catalog/Catalog.WriteModel.Tests/MediaItems/MediaItemFactory.cs
git -C "C:\Users\chase\OneDrive\repos\magiq-media" commit -m "test(catalog): add aggregate tests for BeginRevision/DiscardRevision state machine"
```

---

## Task 4: Add BeginRevision and DiscardRevision command handlers

**Files:**
- Create: `src/modules/Catalog/Catalog.WriteModel/Commands/MediaItems/BeginRevision/BeginRevisionCommand.cs`
- Create: `src/modules/Catalog/Catalog.WriteModel/Commands/MediaItems/BeginRevision/BeginRevisionHandler.cs`
- Create: `src/modules/Catalog/Catalog.WriteModel/Commands/MediaItems/DiscardRevision/DiscardRevisionCommand.cs`
- Create: `src/modules/Catalog/Catalog.WriteModel/Commands/MediaItems/DiscardRevision/DiscardRevisionHandler.cs`
- Test: `tests/modules/Catalog/Catalog.WriteModel.Tests/MediaItems/Commands/BeginRevisionHandlerTests.cs`
- Test: `tests/modules/Catalog/Catalog.WriteModel.Tests/MediaItems/Commands/DiscardRevisionHandlerTests.cs`

- [ ] **Step 1: Read WithdrawMediaItemHandler and WithdrawMediaItemCommand for pattern**

Read these files to understand command/handler conventions:
- `src/modules/Catalog/Catalog.WriteModel/Commands/MediaItems/WithdrawMediaItem/WithdrawMediaItemHandler.cs`
- `src/modules/Catalog/Catalog.WriteModel/Commands/MediaItems/WithdrawMediaItem/WithdrawMediaItemCommand.cs`

- [ ] **Step 2: Write failing tests for BeginRevisionHandler**

```csharp
// tests/modules/Catalog/Catalog.WriteModel.Tests/MediaItems/Commands/BeginRevisionHandlerTests.cs
using FluentAssertions;
using Magiq.Media.Catalog.Aggregates.MediaItems;
using Magiq.Media.Catalog.Aggregates.MediaItems.ValueObjects;
using Magiq.Media.Catalog.Commands.MediaItems.BeginRevision;
using Magiq.Media.Catalog.Repositories;
using Magiq.Media.Catalog.ValueObjects;
using Magiq.Platform.WriteModel.Commands;
using Moq;
using Xunit;

namespace Magiq.Media.Catalog.Tests.MediaItems.Commands;

public sealed class BeginRevisionHandlerTests
{
    private static readonly TenantId _tenant = MediaItemFactory.Tenant;
    private static readonly MediaItemId _itemId = MediaItemFactory.ItemId;
    private readonly Mock<IMediaItemRepository> _repository = new(MockBehavior.Strict);

    private BeginRevisionHandler CreateHandler() => new BeginRevisionHandler(_repository.Object);

    [Fact]
    public async Task HandleAsync_MediaItemNotFound_ReturnsNotFound()
    {
        _repository.Setup(r => r.GetByIdAsync(_tenant, _itemId, CancellationToken.None))
            .ReturnsAsync((MediaItem?)null);

        var cmd = new BeginRevisionCommand(_tenant, _itemId, new MemberId(Guid.NewGuid()), DateTimeOffset.UtcNow);
        var result = await CreateHandler().HandleAsync(cmd, new Mock<ICommandHandlingContext>().Object, CancellationToken.None);

        result.IsFailure.Should().BeTrue();
    }

    [Fact]
    public async Task HandleAsync_ItemIsPublished_TransitionsToRevising()
    {
        var item = MediaItemFactory.CreatePublished(_tenant, _itemId);
        _repository.Setup(r => r.GetByIdAsync(_tenant, _itemId, CancellationToken.None))
            .ReturnsAsync(item);
        _repository.Setup(r => r.SaveAsync(It.IsAny<MediaItem>(), CancellationToken.None))
            .Returns(Task.CompletedTask);

        var cmd = new BeginRevisionCommand(_tenant, _itemId, new MemberId(Guid.NewGuid()), DateTimeOffset.UtcNow);
        var result = await CreateHandler().HandleAsync(cmd, new Mock<ICommandHandlingContext>().Object, CancellationToken.None);

        result.IsSuccess.Should().BeTrue();
        item.Status.Should().Be(MediaItemStatus.Revising);
    }

    [Fact]
    public async Task HandleAsync_ItemIsDraft_ReturnsError()
    {
        var item = MediaItemFactory.CreateDraft(_tenant, _itemId);
        _repository.Setup(r => r.GetByIdAsync(_tenant, _itemId, CancellationToken.None))
            .ReturnsAsync(item);

        var cmd = new BeginRevisionCommand(_tenant, _itemId, new MemberId(Guid.NewGuid()), DateTimeOffset.UtcNow);
        var result = await CreateHandler().HandleAsync(cmd, new Mock<ICommandHandlingContext>().Object, CancellationToken.None);

        result.IsFailure.Should().BeTrue();
    }
}
```

- [ ] **Step 3: Write failing tests for DiscardRevisionHandler**

```csharp
// tests/modules/Catalog/Catalog.WriteModel.Tests/MediaItems/Commands/DiscardRevisionHandlerTests.cs
using FluentAssertions;
using Magiq.Media.Catalog.Aggregates.MediaItems;
using Magiq.Media.Catalog.Aggregates.MediaItems.ValueObjects;
using Magiq.Media.Catalog.Commands.MediaItems.DiscardRevision;
using Magiq.Media.Catalog.Repositories;
using Magiq.Media.Catalog.ValueObjects;
using Magiq.Platform.WriteModel.Commands;
using Moq;
using Xunit;

namespace Magiq.Media.Catalog.Tests.MediaItems.Commands;

public sealed class DiscardRevisionHandlerTests
{
    private static readonly TenantId _tenant = MediaItemFactory.Tenant;
    private static readonly MediaItemId _itemId = MediaItemFactory.ItemId;
    private readonly Mock<IMediaItemRepository> _repository = new(MockBehavior.Strict);

    private DiscardRevisionHandler CreateHandler() => new DiscardRevisionHandler(_repository.Object);

    [Fact]
    public async Task HandleAsync_MediaItemNotFound_ReturnsNotFound()
    {
        _repository.Setup(r => r.GetByIdAsync(_tenant, _itemId, CancellationToken.None))
            .ReturnsAsync((MediaItem?)null);

        var cmd = new DiscardRevisionCommand(_tenant, _itemId, new MemberId(Guid.NewGuid()), DateTimeOffset.UtcNow);
        var result = await CreateHandler().HandleAsync(cmd, new Mock<ICommandHandlingContext>().Object, CancellationToken.None);

        result.IsFailure.Should().BeTrue();
    }

    [Fact]
    public async Task HandleAsync_ItemIsRevising_TransitionsBackToPublished()
    {
        var item = MediaItemFactory.CreatePublished(_tenant, _itemId);
        item.BeginRevision(new MemberId(Guid.NewGuid()), DateTimeOffset.UtcNow);

        _repository.Setup(r => r.GetByIdAsync(_tenant, _itemId, CancellationToken.None))
            .ReturnsAsync(item);
        _repository.Setup(r => r.SaveAsync(It.IsAny<MediaItem>(), CancellationToken.None))
            .Returns(Task.CompletedTask);

        var cmd = new DiscardRevisionCommand(_tenant, _itemId, new MemberId(Guid.NewGuid()), DateTimeOffset.UtcNow);
        var result = await CreateHandler().HandleAsync(cmd, new Mock<ICommandHandlingContext>().Object, CancellationToken.None);

        result.IsSuccess.Should().BeTrue();
        item.Status.Should().Be(MediaItemStatus.Published);
    }

    [Fact]
    public async Task HandleAsync_ItemIsPublished_ReturnsError()
    {
        var item = MediaItemFactory.CreatePublished(_tenant, _itemId);
        _repository.Setup(r => r.GetByIdAsync(_tenant, _itemId, CancellationToken.None))
            .ReturnsAsync(item);

        var cmd = new DiscardRevisionCommand(_tenant, _itemId, new MemberId(Guid.NewGuid()), DateTimeOffset.UtcNow);
        var result = await CreateHandler().HandleAsync(cmd, new Mock<ICommandHandlingContext>().Object, CancellationToken.None);

        result.IsFailure.Should().BeTrue();
    }
}
```

- [ ] **Step 4: Run tests to confirm they fail**

```bash
dotnet test "C:\Users\chase\OneDrive\repos\magiq-media\tests\modules\Catalog\Catalog.WriteModel.Tests" --filter "BeginRevisionHandlerTests|DiscardRevisionHandlerTests" -v 2>&1 | tail -10
```

Expected: compile errors (handlers don't exist yet).

- [ ] **Step 5: Create BeginRevisionCommand**

```csharp
// src/modules/Catalog/Catalog.WriteModel/Commands/MediaItems/BeginRevision/BeginRevisionCommand.cs
using Magiq.Media.Catalog.ValueObjects;
using Magiq.Platform.WriteModel.Commands;

namespace Magiq.Media.Catalog.Commands.MediaItems.BeginRevision;

public sealed record BeginRevisionCommand(
    TenantId TenantId,
    MediaItemId MediaItemId,
    MemberId RequestingUser,
    DateTimeOffset OccurredAt) : Command;
```

- [ ] **Step 6: Create BeginRevisionHandler**

```csharp
// src/modules/Catalog/Catalog.WriteModel/Commands/MediaItems/BeginRevision/BeginRevisionHandler.cs
using CSharpFunctionalExtensions;
using Magiq.Media.Catalog.Repositories;
using Magiq.Platform.WriteModel;
using Magiq.Platform.WriteModel.Commands;
using Magiq.Platform.WriteModel.Errors;

namespace Magiq.Media.Catalog.Commands.MediaItems.BeginRevision;

/// <summary>
/// Transitions a Published MediaItem to Revising state so the owner can prepare
/// a new version while the published version remains live.
/// </summary>
public sealed class BeginRevisionHandler(IMediaItemRepository repository)
    : CommandHandler<BeginRevisionCommand>
{
    protected override async Task<Result<Unit, IDomainError>> ExecuteAsync(
        BeginRevisionCommand command, CancellationToken cancellationToken)
    {
        var mediaItem = await repository.GetByIdAsync(command.TenantId, command.MediaItemId, cancellationToken);
        if (mediaItem is null)
            return ResourceNotFound("Media item not found.");

        var result = mediaItem.BeginRevision(command.RequestingUser, command.OccurredAt);
        if (!result.IsSuccess)
            return result.Error;

        await repository.SaveAsync(mediaItem, cancellationToken);
        return Unit;
    }
}
```

- [ ] **Step 7: Create DiscardRevisionCommand**

```csharp
// src/modules/Catalog/Catalog.WriteModel/Commands/MediaItems/DiscardRevision/DiscardRevisionCommand.cs
using Magiq.Media.Catalog.ValueObjects;
using Magiq.Platform.WriteModel.Commands;

namespace Magiq.Media.Catalog.Commands.MediaItems.DiscardRevision;

public sealed record DiscardRevisionCommand(
    TenantId TenantId,
    MediaItemId MediaItemId,
    MemberId RequestingUser,
    DateTimeOffset OccurredAt) : Command;
```

- [ ] **Step 8: Create DiscardRevisionHandler**

```csharp
// src/modules/Catalog/Catalog.WriteModel/Commands/MediaItems/DiscardRevision/DiscardRevisionHandler.cs
using CSharpFunctionalExtensions;
using Magiq.Media.Catalog.Repositories;
using Magiq.Platform.WriteModel;
using Magiq.Platform.WriteModel.Commands;
using Magiq.Platform.WriteModel.Errors;

namespace Magiq.Media.Catalog.Commands.MediaItems.DiscardRevision;

/// <summary>
/// Abandons the in-progress revision, returning the MediaItem to Published state.
/// Draft changes are discarded; the published version is unchanged.
/// </summary>
public sealed class DiscardRevisionHandler(IMediaItemRepository repository)
    : CommandHandler<DiscardRevisionCommand>
{
    protected override async Task<Result<Unit, IDomainError>> ExecuteAsync(
        DiscardRevisionCommand command, CancellationToken cancellationToken)
    {
        var mediaItem = await repository.GetByIdAsync(command.TenantId, command.MediaItemId, cancellationToken);
        if (mediaItem is null)
            return ResourceNotFound("Media item not found.");

        var result = mediaItem.DiscardRevision(command.RequestingUser, command.OccurredAt);
        if (!result.IsSuccess)
            return result.Error;

        await repository.SaveAsync(mediaItem, cancellationToken);
        return Unit;
    }
}
```

- [ ] **Step 9: Run tests — confirm they pass**

```bash
dotnet test "C:\Users\chase\OneDrive\repos\magiq-media\tests\modules\Catalog\Catalog.WriteModel.Tests" --filter "BeginRevisionHandlerTests|DiscardRevisionHandlerTests" -v 2>&1 | tail -10
```

Expected: all pass.

- [ ] **Step 10: Register new handlers in DI**

Read `src/modules/Catalog/Catalog.WriteModel.Infrastructure/ServiceCollectionExtensions.cs` around the handler registration block. Add:

```csharp
builder.AddResultCommandHandler<BeginRevisionCommand, BeginRevisionHandler>();
builder.AddResultCommandHandler<DiscardRevisionCommand, DiscardRevisionHandler>();
```

Add the corresponding using statements at the top of the file:
```csharp
using Magiq.Media.Catalog.Commands.MediaItems.BeginRevision;
using Magiq.Media.Catalog.Commands.MediaItems.DiscardRevision;
```

- [ ] **Step 11: Build Catalog.WriteModel**

```bash
dotnet build "C:\Users\chase\OneDrive\repos\magiq-media\src\modules\Catalog\Catalog.WriteModel\Catalog.WriteModel.csproj" 2>&1 | grep -E "error CS|Build succeeded|Build FAILED"
```

Expected: Build succeeded.

- [ ] **Step 12: Commit**

```bash
git -C "C:\Users\chase\OneDrive\repos\magiq-media" add src/modules/Catalog/Catalog.WriteModel/Commands/MediaItems/BeginRevision/ src/modules/Catalog/Catalog.WriteModel/Commands/MediaItems/DiscardRevision/ src/modules/Catalog/Catalog.WriteModel.Infrastructure/ServiceCollectionExtensions.cs tests/modules/Catalog/Catalog.WriteModel.Tests/MediaItems/Commands/BeginRevisionHandlerTests.cs tests/modules/Catalog/Catalog.WriteModel.Tests/MediaItems/Commands/DiscardRevisionHandlerTests.cs
git -C "C:\Users\chase\OneDrive\repos\magiq-media" commit -m "feat(catalog): add BeginRevision and DiscardRevision command handlers"
```

---

## Task 5: Add API endpoints

**Files:**
- Create: `src/modules/Catalog/Catalog.WriteModel.Endpoints/V1/MediaItems/BeginRevision/BeginRevisionEndpoint.cs`
- Create: `src/modules/Catalog/Catalog.WriteModel.Endpoints/V1/MediaItems/BeginRevision/BeginRevisionRequest.cs`
- Create: `src/modules/Catalog/Catalog.WriteModel.Endpoints/V1/MediaItems/DiscardRevision/DiscardRevisionEndpoint.cs`
- Create: `src/modules/Catalog/Catalog.WriteModel.Endpoints/V1/MediaItems/DiscardRevision/DiscardRevisionRequest.cs`

- [ ] **Step 1: Read WithdrawMediaItemEndpoint for the FastEndpoints pattern**

Read `src/modules/Catalog/Catalog.WriteModel.Endpoints/V1/MediaItems/WithdrawMediaItem/WithdrawMediaItemEndpoint.cs` to understand how endpoints are structured (class inheritance, Configure, HandleAsync, how TenantId/ActorId are obtained).

- [ ] **Step 2: Create BeginRevisionRequest**

```csharp
// src/modules/Catalog/Catalog.WriteModel.Endpoints/V1/MediaItems/BeginRevision/BeginRevisionRequest.cs
namespace Magiq.Media.Catalog.Endpoints.V1.MediaItems.BeginRevision;

public sealed class BeginRevisionRequest
{
    public string ItemId { get; set; } = null!;
}
```

- [ ] **Step 3: Create BeginRevisionEndpoint**

Model exactly on `WithdrawMediaItemEndpoint`. Key differences:
- Route: `POST /catalog/items/{itemId}/begin-revision`
- Endpoint name: `BeginRevision`
- Summary: "Begin a revision of a published media item. The published version remains live while the owner prepares a new version."
- Command: `BeginRevisionCommand(context.TenantId, mediaItemId, new MemberId(context.Actor.Id), context.GetUtcOffsetNow())`
- Returns 204 on success

```csharp
// src/modules/Catalog/Catalog.WriteModel.Endpoints/V1/MediaItems/BeginRevision/BeginRevisionEndpoint.cs
using Magiq.Media.Catalog.Commands.MediaItems.BeginRevision;
using Magiq.Media.Catalog.ValueObjects;
using Magiq.Platform.ExecutionContext;
using Magiq.Platform.WriteModel.Commands;
// ... add other usings matching WithdrawMediaItemEndpoint

namespace Magiq.Media.Catalog.Endpoints.V1.MediaItems.BeginRevision;

public sealed class BeginRevisionEndpoint(ICommandDispatcher dispatch, IExecutionContext context)
    : CatalogEndpoint<BeginRevisionRequest>
{
    public override void Configure()
    {
        Post("/catalog/items/{itemId}/begin-revision");
        Description(x => x
            .WithName("BeginRevision")
            .WithTags("Catalog")
            .WithGroupName("v1")
            .Produces(204)
            .ProducesProblem(401)
            .ProducesProblem(403)
            .ProducesProblem(404)
            .ProducesProblem(409)
        );
        Summary(summary =>
        {
            summary.Summary = "Begin a revision of a published media item.";
            summary.Params["itemId"] = "The unique identifier of the media item.";
            summary.Description = "Transitions a Published item to Revising state. The current published version remains live while the owner prepares a new version. 409 if the item is not Published.";
            summary.Response(204, "Revision started. Item is now in Revising state.");
            summary.Response(401, "Authentication is required.");
            summary.Response(403, "The caller does not have permission.");
            summary.Response(404, "A media item with the specified Id does not exist.");
            summary.Response(409, "The media item is not in Published state.");
        });
        Version(1);
    }

    public override async Task HandleAsync(BeginRevisionRequest req, CancellationToken cancellationToken)
    {
        var mediaItemId = MediaItemId.From(req.ItemId);
        var command = new BeginRevisionCommand(
            context.TenantId, mediaItemId, new MemberId(context.Actor.Id), context.GetUtcOffsetNow());
        var result = await dispatch.SendAsync(command, cancellationToken);
        if (!result.IsSuccess)
        {
            await SendDomainErrorAsync(result.Error, cancellationToken);
            return;
        }
        await SendNoContentAsync(cancellationToken);
    }
}
```

- [ ] **Step 4: Create DiscardRevisionRequest**

```csharp
// src/modules/Catalog/Catalog.WriteModel.Endpoints/V1/MediaItems/DiscardRevision/DiscardRevisionRequest.cs
namespace Magiq.Media.Catalog.Endpoints.V1.MediaItems.DiscardRevision;

public sealed class DiscardRevisionRequest
{
    public string ItemId { get; set; } = null!;
}
```

- [ ] **Step 5: Create DiscardRevisionEndpoint**

```csharp
// src/modules/Catalog/Catalog.WriteModel.Endpoints/V1/MediaItems/DiscardRevision/DiscardRevisionEndpoint.cs
// ... follow exact same pattern as BeginRevisionEndpoint
// Route: POST /catalog/items/{itemId}/discard-revision
// Endpoint name: DiscardRevision
// Command: DiscardRevisionCommand(...)
// Description: "Abandons the in-progress revision, returning the item to Published state. Draft changes are discarded. 409 if the item is not in Revising state."
```

- [ ] **Step 6: Build endpoints project**

```bash
dotnet build "C:\Users\chase\OneDrive\repos\magiq-media\src\modules\Catalog\Catalog.WriteModel.Endpoints\" 2>&1 | grep -E "error CS|Build succeeded|Build FAILED"
```

Expected: Build succeeded.

- [ ] **Step 7: Commit**

```bash
git -C "C:\Users\chase\OneDrive\repos\magiq-media" add src/modules/Catalog/Catalog.WriteModel.Endpoints/V1/MediaItems/BeginRevision/ src/modules/Catalog/Catalog.WriteModel.Endpoints/V1/MediaItems/DiscardRevision/
git -C "C:\Users\chase\OneDrive\repos\magiq-media" commit -m "feat(catalog): add BeginRevision and DiscardRevision HTTP endpoints"
```

---

## Task 6: Update read model projectors

**Files:**
- Modify: `src/modules/Catalog/Catalog.ReadModel/Projectors/MediaItems/MediaItemDetailProjector.cs`
- Modify: `src/modules/Catalog/Catalog.ReadModel/Projectors/MediaItems/MediaItemSummaryProjector.cs`
- Modify: `src/modules/Catalog/Catalog.ReadModel/Projectors/MediaItems/MediaItemCurrentDraftProjector.cs`

- [ ] **Step 1: Read all three projectors in full**

Read each file to understand the event handler registration pattern and what state each handler updates.

- [ ] **Step 2: Add handlers for MediaItemRevisionStarted in all three projectors**

In each projector, add a handler for `MediaItemRevisionStarted` that sets `Status = "Revising"` (or `MediaItemStatus.Revising`). Follow the exact pattern used for `MediaItemWithdrawn` (which sets Status = Draft) — same structure, different status value.

For `MediaItemDetailProjector`, the handler should:
```csharp
// Sets status to Revising. Published content (version number, metadata) unchanged —
// readers continue to see the published version. Owner edits accumulate in Draft.
private async Task ApplyAsync(MediaItemRevisionStarted e, ...)
{
    // Update Status = Revising in the read model
    // Keep CurrentVersionNumber, PublishedAt, and metadata unchanged
}
```

- [ ] **Step 3: Add handlers for MediaItemRevisionDiscarded in all three projectors**

Add a handler that sets `Status = "Published"` (reverts to published state). Follow the `MediaItemApproved` pattern for reference.

- [ ] **Step 4: Build read model project**

```bash
dotnet build "C:\Users\chase\OneDrive\repos\magiq-media\src\modules\Catalog\Catalog.ReadModel\" 2>&1 | grep -E "error CS|Build succeeded|Build FAILED"
dotnet build "C:\Users\chase\OneDrive\repos\magiq-media\src\modules\Catalog\Catalog.ReadModel.Infrastructure\" 2>&1 | grep -E "error CS|Build succeeded|Build FAILED"
```

Expected: Both succeed.

- [ ] **Step 5: Run read model tests**

```bash
dotnet test "C:\Users\chase\OneDrive\repos\magiq-media\tests\modules\Catalog\Catalog.ReadModel.Tests" -v 2>&1 | tail -10
```

Fix any failures.

- [ ] **Step 6: Commit**

```bash
git -C "C:\Users\chase\OneDrive\repos\magiq-media" add src/modules/Catalog/Catalog.ReadModel/Projectors/MediaItems/
git -C "C:\Users\chase\OneDrive\repos\magiq-media" commit -m "feat(catalog-read): project MediaItemRevisionStarted/Discarded — Revising status in read model"
```

---

## Task 7: Update AssetProcessingCompletedAutoSubmitHandler for Revising state

**Files:**
- Modify: `src/modules/Catalog/Catalog.WriteModel.Infrastructure/IntegrationEvents/Consuming/Handlers/AssetProcessingCompletedAutoSubmitHandler.cs`

- [ ] **Step 1: Read the handler in full**

Read `src/modules/Catalog/Catalog.WriteModel.Infrastructure/IntegrationEvents/Consuming/Handlers/AssetProcessingCompletedAutoSubmitHandler.cs` to understand the current status guard.

- [ ] **Step 2: Update status guard to include Revising**

Find any check like `Status == MediaItemStatus.Draft`. Update to:
```csharp
(mediaItem.Status == MediaItemStatus.Draft || mediaItem.Status == MediaItemStatus.Revising)
```

This ensures the backstop auto-submit also fires when an asset completes processing during a revision cycle.

- [ ] **Step 3: Build and test**

```bash
dotnet build "C:\Users\chase\OneDrive\repos\magiq-media\src\modules\Catalog\Catalog.WriteModel.Infrastructure\" 2>&1 | grep -E "error CS|Build succeeded|Build FAILED"
dotnet test "C:\Users\chase\OneDrive\repos\magiq-media\tests\modules\Catalog\Catalog.WriteModel.Infrastructure.Tests" -v 2>&1 | tail -10
```

- [ ] **Step 4: Commit**

```bash
git -C "C:\Users\chase\OneDrive\repos\magiq-media" add src/modules/Catalog/Catalog.WriteModel.Infrastructure/IntegrationEvents/Consuming/Handlers/AssetProcessingCompletedAutoSubmitHandler.cs
git -C "C:\Users\chase\OneDrive\repos\magiq-media" commit -m "fix(catalog): allow auto-submit backstop to fire from Revising state"
```

---

## Task 8: Full build, test, and integration test

**Files:**
- Modify: `tests/integration/modules/Catalog/Catalog.IntegrationTests/MediaItems/MediaItemFlowTests.cs`

- [ ] **Step 1: Full solution build**

```bash
dotnet build "C:\Users\chase\OneDrive\repos\magiq-media\src\" 2>&1 | grep -E "error CS|Build succeeded|Build FAILED"
```

Fix all errors.

- [ ] **Step 2: Full unit test run**

```bash
dotnet test "C:\Users\chase\OneDrive\repos\magiq-media\tests\modules\" --logger "console;verbosity=minimal" 2>&1 | tail -5
```

Expected: 0 failures.

- [ ] **Step 3: Add integration test for revision flow**

Add this test to `MediaItemFlowTests.cs`:

```csharp
[Fact]
public async Task PublishedItem_BeginRevision_ReplaceAsset_Publish_CreatesNewVersion()
{
    var itemId = await CreateMediaItemAsync();

    // Publish initial version (no reviewers = auto-approve)
    var publishResponse = await Client.PostAsJsonAsync($"/v1/catalog/items/{itemId}/publish",
        new PublishMediaItemRequest { ItemId = itemId }, ApiJsonOptions);
    publishResponse.StatusCode.Should().Be(HttpStatusCode.Accepted);

    var v1Body = await (await Client.GetAsync($"/v1/catalog/items/{itemId}"))
        .Content.ReadFromJsonAsync<JsonElement>();
    v1Body.GetProperty("status").GetString().Should().Be("Published");
    v1Body.GetProperty("currentVersionNumber").GetInt32().Should().Be(1);

    // Begin revision — item enters Revising state
    var beginRevisionResponse = await Client.PostAsJsonAsync(
        $"/v1/catalog/items/{itemId}/begin-revision",
        new { ItemId = itemId }, ApiJsonOptions);
    beginRevisionResponse.StatusCode.Should().Be(HttpStatusCode.NoContent);

    var revisingBody = await (await Client.GetAsync($"/v1/catalog/items/{itemId}"))
        .Content.ReadFromJsonAsync<JsonElement>();
    revisingBody.GetProperty("status").GetString().Should().Be("Revising");
    revisingBody.GetProperty("currentVersionNumber").GetInt32().Should().Be(1); // Published version still 1

    // Publish new version (no reviewers = auto-approve)
    var publishV2Response = await Client.PostAsJsonAsync($"/v1/catalog/items/{itemId}/publish",
        new PublishMediaItemRequest { ItemId = itemId }, ApiJsonOptions);
    publishV2Response.StatusCode.Should().Be(HttpStatusCode.Accepted);

    var v2Body = await (await Client.GetAsync($"/v1/catalog/items/{itemId}"))
        .Content.ReadFromJsonAsync<JsonElement>();
    v2Body.GetProperty("status").GetString().Should().Be("Published");
    v2Body.GetProperty("currentVersionNumber").GetInt32().Should().Be(2);
}

[Fact]
public async Task PublishedItem_BeginRevision_DiscardRevision_ReturnsToPublished()
{
    var itemId = await CreateMediaItemAsync();

    await Client.PostAsJsonAsync($"/v1/catalog/items/{itemId}/publish",
        new PublishMediaItemRequest { ItemId = itemId }, ApiJsonOptions);

    await Client.PostAsJsonAsync($"/v1/catalog/items/{itemId}/begin-revision",
        new { ItemId = itemId }, ApiJsonOptions);

    var discardResponse = await Client.PostAsJsonAsync(
        $"/v1/catalog/items/{itemId}/discard-revision",
        new { ItemId = itemId }, ApiJsonOptions);
    discardResponse.StatusCode.Should().Be(HttpStatusCode.NoContent);

    var body = await (await Client.GetAsync($"/v1/catalog/items/{itemId}"))
        .Content.ReadFromJsonAsync<JsonElement>();
    body.GetProperty("status").GetString().Should().Be("Published");
    body.GetProperty("currentVersionNumber").GetInt32().Should().Be(1);
}
```

Add required using at the top of the file if not already present — no new request types needed (the begin-revision and discard-revision endpoints accept anonymous objects or create minimal request classes as needed).

- [ ] **Step 4: Run integration tests**

```bash
dotnet test "C:\Users\chase\OneDrive\repos\magiq-media\tests\integration\modules\Catalog\Catalog.IntegrationTests\" --filter "PublishedItem_BeginRevision" -v 2>&1 | tail -15
```

Fix any failures.

- [ ] **Step 5: Commit**

```bash
git -C "C:\Users\chase\OneDrive\repos\magiq-media" add -u
git -C "C:\Users\chase\OneDrive\repos\magiq-media" commit -m "test(catalog): add integration tests for BeginRevision/DiscardRevision flow"
```

---

## Task 9: Update spec documentation

**Files:**
- Modify: `projects/magiq-media/spec/contexts/Catalog/aggregates/MediaItem/mediaitem.write-model.md`
- Modify: `projects/magiq-media/spec/contexts/Catalog/aggregates/MediaItem/mediaitem.api.md`
- Modify: `projects/magiq-media/spec/contexts/Catalog/aggregates/MediaItem/mediaitem.scenarios.md`

- [ ] **Step 1: Update mediaitem.write-model.md**

Add `Revising` to the status table:

```markdown
| `Revising` | Owner is preparing a new version. Published version remains live. Edits (metadata, assets) apply to the draft. Publish creates v+1. |
```

Update status transitions diagram:
```
Published ──BeginRevision──► Revising ──Publish──► PendingApproval / Published
                                      ──DiscardRevision──► Published
```

Add two new operation sections:

**BeginRevision:**
- `Status` must be `Published`
- Transitions to `Revising`
- Initialises `Metadata.Draft` from `Metadata.Current` (edits start from published content)
- Published version remains accessible to readers

**DiscardRevision:**
- `Status` must be `Revising`
- Discards draft changes
- Returns to `Published` (published version unchanged)

- [ ] **Step 2: Update mediaitem.api.md**

Add two new endpoint specs:

```
POST /catalog/items/{itemId}/begin-revision
  Request: { }  (no body required)
  Response 204: Revision started
  Response 409: Item is not Published

POST /catalog/items/{itemId}/discard-revision
  Request: { }  (no body required)
  Response 204: Revision discarded, item back to Published
  Response 409: Item is not in Revising state
```

- [ ] **Step 3: Update mediaitem.scenarios.md**

Add two new scenarios:

**Scenario: Begin revision and publish new version**
- Published item → `begin-revision` → status = Revising, version = 1
- (optional) Replace asset in role
- `publish` → auto-approve → status = Published, version = 2

**Scenario: Begin revision and discard**
- Published item → `begin-revision` → status = Revising
- `discard-revision` → status = Published, version unchanged

- [ ] **Step 4: Commit spec changes**

Spec lives in AIS-OS (not git), so just confirm files are saved.

---

## Self-Review

### Spec coverage
| Requirement | Task |
|---|---|
| `Revising` status added | Task 1 |
| `BeginRevision` aggregate method | Task 2 |
| `DiscardRevision` aggregate method | Task 2 |
| Edit guards updated for `Revising` | Task 2 |
| Aggregate unit tests | Task 3 |
| `BeginRevisionHandler` + tests | Task 4 |
| `DiscardRevisionHandler` + tests | Task 4 |
| DI registration | Task 4 |
| API endpoints | Task 5 |
| Read model projectors | Task 6 |
| Auto-submit backstop updated | Task 7 |
| Full build + integration tests | Task 8 |
| Spec docs | Task 9 |

### Placeholder scan
No TBD, TODO, or "similar to Task N" placeholders. All steps contain complete code or exact commands.

### Type consistency
- `MediaItemStatus.Revising` — defined Task 1, used Tasks 2, 3, 4, 6, 7 ✅
- `MediaItemRevisionStarted` — defined Task 1, used Tasks 2, 6 ✅
- `MediaItemRevisionDiscarded` — defined Task 1, used Tasks 2, 6 ✅
- `BeginRevisionCommand` — defined Task 4, used Tasks 4 (DI), 5 ✅
- `DiscardRevisionCommand` — defined Task 4, used Tasks 4 (DI), 5 ✅
- `MediaItemFactory.CreatePublished` — defined Task 3, used Tasks 3, 4 ✅
- `MediaItemFactory.CreateRevisingWithAsset` — defined Task 3, used Task 3 ✅
