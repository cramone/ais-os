# Fix Auto-Submit Asset Active Guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent auto-submit from firing in `AssignAssetToRoleHandler` when assigned assets are still processing — only dispatch `PublishMediaItemCommand` once all assigned assets are confirmed Active.

**Architecture:** Single guard added to `AssignAssetToRoleHandler` before the auto-submit dispatch. Uses the already-injected `IAssetQueryService` to fetch current asset statuses. The backstop handler (`AssetProcessingCompletedAutoSubmitHandler`) already fires correctly when each asset reaches Active — this fix eliminates premature dispatch from the assignment path without removing the backstop.

**Tech Stack:** C# / .NET, XUnit + Moq, MediatR command handlers.

---

## File Map

### Modified
| File | Change |
|---|---|
| `src/modules/Catalog/Catalog.WriteModel/Commands/MediaItems/AssignAssetToRole/AssignAssetToRoleHandler.cs` | Add Active status guard before auto-submit dispatch |
| `tests/modules/Catalog/Catalog.WriteModel.Tests/MediaItems/Commands/AssignAssetToRoleHandlerTests.cs` | Add tests for Active guard behaviour |

---

## Task 1: Fix auto-submit guard in AssignAssetToRoleHandler

**Files:**
- Modify: `src/modules/Catalog/Catalog.WriteModel/Commands/MediaItems/AssignAssetToRole/AssignAssetToRoleHandler.cs`
- Test: `tests/modules/Catalog/Catalog.WriteModel.Tests/MediaItems/Commands/AssignAssetToRoleHandlerTests.cs`

- [ ] **Step 1: Read the existing test file**

Read `tests/modules/Catalog/Catalog.WriteModel.Tests/MediaItems/Commands/AssignAssetToRoleHandlerTests.cs` to understand the current test structure, mock setup pattern, and which scenarios already exist.

- [ ] **Step 2: Write failing tests**

Add these three tests to `AssignAssetToRoleHandlerTests.cs`. Find the existing test class and add them. Match the exact mock/factory pattern used in the existing tests.

```csharp
[Fact]
public async Task HandleAsync_AllRequiredRolesFilled_AllAssetsActive_AutoSubmitDispatches()
{
    // Arrange
    var profileId = MediaProfileId.New();
    var assetId = AssetId.New();
    var roleName = new RoleName("primary");

    var profile = MediaProfileFactory.CreatePublishedWithRequiredRole(
        _tenant, profileId, roleName, autoSubmitOnComplete: true);

    var item = MediaItemFactory.CreateDraft(_tenant, _itemId, profileId);

    // Asset already Active
    var assetRef = new MediaItemAssetReference(
        assetId, AssetStatus.Active, MediaContentType.Document, "file.pdf", null, []);

    _repository.Setup(r => r.GetByIdAsync(_tenant, _itemId, CancellationToken.None))
        .ReturnsAsync(item);
    _profileRepository.Setup(r => r.GetByIdAsync(_tenant, profileId, CancellationToken.None))
        .ReturnsAsync(profile);
    _assetService.Setup(s => s.GetAsync(_tenant, assetId, CancellationToken.None))
        .ReturnsAsync(assetRef);
    _assetService.Setup(s => s.GetManyAsync(_tenant, It.IsAny<IReadOnlyList<AssetId>>(), CancellationToken.None))
        .ReturnsAsync(new List<MediaItemAssetReference> { assetRef });
    _repository.Setup(r => r.SaveAsync(It.IsAny<MediaItem>(), CancellationToken.None))
        .Returns(Task.CompletedTask);
    _commandDispatcher.Setup(d => d.SendAsync(It.IsAny<PublishMediaItemCommand>(), CancellationToken.None))
        .ReturnsAsync(Result.Success<PublishMediaItemResult, IDomainError>(new PublishMediaItemResult(null)));

    var cmd = new AssignAssetToRoleCommand(_tenant, _itemId, assetId, roleName, DateTimeOffset.UtcNow);

    // Act
    var result = await CreateHandler().HandleAsync(cmd, new Mock<ICommandHandlingContext>().Object, CancellationToken.None);

    // Assert
    result.IsSuccess.Should().BeTrue();
    _commandDispatcher.Verify(d => d.SendAsync(It.IsAny<PublishMediaItemCommand>(), CancellationToken.None), Times.Once);
}

[Fact]
public async Task HandleAsync_AllRequiredRolesFilled_AssetStillProcessing_AutoSubmitDoesNotDispatch()
{
    // Arrange — asset is Processing, not Active
    var profileId = MediaProfileId.New();
    var assetId = AssetId.New();
    var roleName = new RoleName("primary");

    var profile = MediaProfileFactory.CreatePublishedWithRequiredRole(
        _tenant, profileId, roleName, autoSubmitOnComplete: true);

    var item = MediaItemFactory.CreateDraft(_tenant, _itemId, profileId);

    // Asset still Processing
    var assetRef = new MediaItemAssetReference(
        assetId, AssetStatus.Processing, MediaContentType.Document, "file.pdf", null, []);

    _repository.Setup(r => r.GetByIdAsync(_tenant, _itemId, CancellationToken.None))
        .ReturnsAsync(item);
    _profileRepository.Setup(r => r.GetByIdAsync(_tenant, profileId, CancellationToken.None))
        .ReturnsAsync(profile);
    _assetService.Setup(s => s.GetAsync(_tenant, assetId, CancellationToken.None))
        .ReturnsAsync(assetRef);
    _assetService.Setup(s => s.GetManyAsync(_tenant, It.IsAny<IReadOnlyList<AssetId>>(), CancellationToken.None))
        .ReturnsAsync(new List<MediaItemAssetReference> { assetRef });
    _repository.Setup(r => r.SaveAsync(It.IsAny<MediaItem>(), CancellationToken.None))
        .Returns(Task.CompletedTask);

    var cmd = new AssignAssetToRoleCommand(_tenant, _itemId, assetId, roleName, DateTimeOffset.UtcNow);

    // Act
    var result = await CreateHandler().HandleAsync(cmd, new Mock<ICommandHandlingContext>().Object, CancellationToken.None);

    // Assert
    result.IsSuccess.Should().BeTrue();
    // Auto-submit must NOT fire — backstop handler will fire when asset reaches Active
    _commandDispatcher.Verify(d => d.SendAsync(It.IsAny<PublishMediaItemCommand>(), CancellationToken.None), Times.Never);
}

[Fact]
public async Task HandleAsync_AutoSubmitDisabled_NeverDispatches()
{
    // Arrange — AutoSubmitOnComplete = false
    var profileId = MediaProfileId.New();
    var assetId = AssetId.New();
    var roleName = new RoleName("primary");

    var profile = MediaProfileFactory.CreatePublishedWithRequiredRole(
        _tenant, profileId, roleName, autoSubmitOnComplete: false);

    var item = MediaItemFactory.CreateDraft(_tenant, _itemId, profileId);
    var assetRef = new MediaItemAssetReference(
        assetId, AssetStatus.Active, MediaContentType.Document, "file.pdf", null, []);

    _repository.Setup(r => r.GetByIdAsync(_tenant, _itemId, CancellationToken.None))
        .ReturnsAsync(item);
    _profileRepository.Setup(r => r.GetByIdAsync(_tenant, profileId, CancellationToken.None))
        .ReturnsAsync(profile);
    _assetService.Setup(s => s.GetAsync(_tenant, assetId, CancellationToken.None))
        .ReturnsAsync(assetRef);
    _repository.Setup(r => r.SaveAsync(It.IsAny<MediaItem>(), CancellationToken.None))
        .Returns(Task.CompletedTask);

    var cmd = new AssignAssetToRoleCommand(_tenant, _itemId, assetId, roleName, DateTimeOffset.UtcNow);

    // Act
    var result = await CreateHandler().HandleAsync(cmd, new Mock<ICommandHandlingContext>().Object, CancellationToken.None);

    // Assert
    result.IsSuccess.Should().BeTrue();
    _commandDispatcher.Verify(d => d.SendAsync(It.IsAny<ICommand>(), CancellationToken.None), Times.Never);
}
```

- [ ] **Step 3: Run tests — confirm they fail**

```bash
dotnet test "D:\source\github\magiq-media\tests\modules\Catalog\Catalog.WriteModel.Tests" --filter "AssignAssetToRoleHandlerTests" -v 2>&1 | tail -15
```

Expected: compile errors or failures because Active guard doesn't exist yet.

- [ ] **Step 4: Add the Active status guard to AssignAssetToRoleHandler**

Replace the auto-submit block (lines 84–94) with:

```csharp
// Auto-submit: if the profile has AutoSubmitOnComplete enabled and all required asset roles
// are now filled, submit as the system actor — but ONLY if all assigned assets are Active.
// If any asset is still Validating/Processing, the backstop handler
// (AssetProcessingCompletedAutoSubmitHandler) will fire when it reaches Active.
if (profile.AutoSubmitOnComplete
    && mediaItem.Status == MediaItemStatus.Draft
    && profile.AssetDefinitions.Where(d => d.IsRequired).All(d => mediaItem.Assets.Any(a => a.RoleName == d.RoleName)))
{
    var assignedAssetIds = mediaItem.Assets.Select(a => a.AssetId).ToList();
    var assetRefs = await assetService.GetManyAsync(command.TenantId, assignedAssetIds, cancellationToken);
    if (assetRefs.All(a => a.Status == AssetStatus.Active))
    {
        await commandDispatcher.SendAsync(
            new PublishMediaItemCommand(command.TenantId, mediaItem.Id, SystemActor, [], command.OccurredAt),
            cancellationToken);
    }
}
```

- [ ] **Step 5: Run tests — confirm they pass**

```bash
dotnet test "D:\source\github\magiq-media\tests\modules\Catalog\Catalog.WriteModel.Tests" --filter "AssignAssetToRoleHandlerTests" -v 2>&1 | tail -10
```

Expected: all pass.

- [ ] **Step 6: Run full test suite**

```bash
dotnet test "D:\source\github\magiq-media\tests\modules\" --logger "console;verbosity=minimal" 2>&1 | tail -5
```

Expected: 0 failures.

- [ ] **Step 7: Commit**

```bash
git -C "D:\source\github\magiq-media" add src/modules/Catalog/Catalog.WriteModel/Commands/MediaItems/AssignAssetToRole/AssignAssetToRoleHandler.cs tests/modules/Catalog/Catalog.WriteModel.Tests/MediaItems/Commands/AssignAssetToRoleHandlerTests.cs
git -C "D:\source\github\magiq-media" commit -m "fix(catalog): guard auto-submit on asset Active status — prevent premature publish when assets still processing"
```

---

## Self-Review

### Spec coverage
No spec changes needed — this is a bug fix aligning implementation with existing spec intent. The spec states "All assets must be Active before publish" — this fix enforces it in the assignment path.

### Placeholder scan
None present. All test code is complete.

### Type consistency
- `AssetStatus.Active` — from `Magiq.Media.Catalog.ValueObjects.AssetStatus` enum ✅
- `MediaItemAssetReference.Status` — `AssetStatus` property confirmed in `MediaItemAssetReference.cs` ✅
- `IAssetQueryService.GetManyAsync` — already injected into handler ✅
- `PublishMediaItemCommand` — already used in handler ✅

