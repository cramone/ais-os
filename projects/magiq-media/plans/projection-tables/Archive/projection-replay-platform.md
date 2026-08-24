# Projection Replay — Platform Implementation Plan

## Context

Projectors in `magiq-media` had a bug causing missing computed properties in some read model records.
The projector bug is already fixed. We need a platform-level capability to replay domain events from
the event store back through the projection pipeline so broken read models can be rebuilt.

This belongs in `aspnetcore-platform` because it requires direct access to event store internals
(DynamoDB schema, serialization) that app-level code should not reach into.

After this platform work is done, `magiq-media` will add a thin CLI command on top.

---

## What already exists — do not rebuild

| Location | Status |
|---|---|
| `IProjectionPipeline.DispatchBatchAsync(IReadOnlyCollection<object>)` | Works, ready to use |
| `EventStreamAsyncEnumerator` | Works, but `internal` to `Magiq.Platform.EventSourcing.DynamoDb` — use it from within that project |
| `DynamoDbProjectionReplayStore<TEvent>` | All methods throw `NotImplementedException` — **leave it alone**, shadow-table approach is future work |
| `IProjectionReplayCoordinator.cs` | Exists but **fully commented out** with wrong API — redesign from scratch |
| `ProjectionReplayException.cs` | Exists but **fully commented out** — uncomment and keep |

---

## DynamoDB event store facts you need

Partition key format (tenant-scoped aggregates):
```
TENANT#{tenantId}#AGG#{aggregateType}#ID#{aggregateId}
```

Partition key format (global aggregates):
```
AGG#{aggregateType}#ID#{aggregateId}
```

Schema constants are in `DynamoDbEventStoreTableSchema`:
- `PartitionKey = "pk"`
- `SortKey = "sk"` (aggregate version number)
- `PayloadAttribute = "payload"` (binary — serialized event stream items)
- `AggregateTypeAttribute = "aggregate_type"`

`EventStreamItemSerializer` deserializes the binary payload attribute:
```csharp
// Already used in DynamoDbEventStore constructor — same pattern:
private readonly EventStreamItemSerializer _serializer = new(domainEventRegistry, options.Value, serviceProvider.GetService<IS3EventPayloadStore>());

// Deserialize one DynamoDB item's payload:
var events = await _serializer.DeserializeEventStreamItemStreamsToEventsAsync(payload.BS, ct);
```

`IS3EventPayloadStore` is `internal` — always inject via `serviceProvider.GetService<IS3EventPayloadStore>()`,
never as a direct constructor parameter (same pattern as `DynamoDbEventStore`).

---

## Version guard problem — important

`ProjectionDispatcher` skips events where `current.ProjectedVersion >= result.Version`.

The bug means an existing read model record was projected at version N with wrong data.
Replaying the same event at version N hits the guard and is **skipped** — the fix never lands.

**Solution:** callers must delete affected read model records **before** calling the coordinator.
The coordinator itself does not handle clearing — that is explicitly the caller's responsibility.
Document this clearly in the interface XML doc.

---

## The four pieces to build

### Piece 1 — `IEventScanner` + `EventScanOptions`
**Project:** `Magiq.Platform.EventSourcing.Abstractions`

New files:

```csharp
// IEventScanner.cs
namespace Magiq.Platform.EventSourcing;

/// <summary>
/// Streams all domain events from the event store for a given aggregate type,
/// optionally scoped to a tenant. Intended for projection replay and diagnostics.
/// </summary>
public interface IEventScanner
{
    IAsyncEnumerable<IDomainEvent> ScanAsync(EventScanOptions options, CancellationToken cancellationToken = default);
}
```

```csharp
// EventScanOptions.cs
namespace Magiq.Platform.EventSourcing;

/// <summary>
/// Options controlling which events IEventScanner streams.
/// </summary>
public record EventScanOptions
{
    /// <summary>Tenant to scope the scan to, or null for global (non-tenant-scoped) aggregates.</summary>
    public string? TenantId { get; init; }

    /// <summary>The CLR type of the aggregate whose events to stream (e.g. typeof(Asset)).</summary>
    public required Type AggregateType { get; init; }
}
```

No new project references needed — `IDomainEvent` is already in `Magiq.Platform.WriteModel.Domain`
which `Magiq.Platform.EventSourcing.Abstractions` already references.

---

### Piece 2 — `DynamoDbEventScanner`
**Project:** `Magiq.Platform.EventSourcing.DynamoDb`

New file: `DynamoDbEventScanner.cs`

Strategy: DynamoDB **Scan** with `FilterExpression = "begins_with(#pk, :prefix)"`.
This is a full table scan — acceptable for a one-off repair operation. Document the cost.
Future optimisation: add a GSI on the `aggregate_type` attribute.

```csharp
namespace Magiq.Platform.EventSourcing;

/// <summary>
/// Streams domain events from DynamoDB by scanning the event store table for all
/// partitions belonging to the specified aggregate type and tenant.
/// Note: uses DynamoDB Scan (full table read). Acceptable for repair operations;
/// consider a GSI on aggregate_type for high-frequency use.
/// </summary>
public sealed class DynamoDbEventScanner(
    IAmazonDynamoDB dynamoDb,
    ITableResolver tableResolver,
    IDomainEventRegistry domainEventRegistry,
    IOptions<DynamoDbEventStoreOptions> options,
    IServiceProvider serviceProvider) : IEventScanner
{
    private readonly EventStreamItemSerializer _serializer = new(
        domainEventRegistry,
        options.Value,
        serviceProvider.GetService<IS3EventPayloadStore>());

    public async IAsyncEnumerable<IDomainEvent> ScanAsync(
        EventScanOptions scanOptions,
        [EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        var aggregateTypeName = scanOptions.AggregateType.GetAggregateType();
        var tableName = /* resolve via tableResolver — see note below */;

        var pkPrefix = string.IsNullOrEmpty(scanOptions.TenantId)
            ? $"AGG#{aggregateTypeName}#ID#"
            : $"TENANT#{scanOptions.TenantId}#AGG#{aggregateTypeName}#ID#";

        Dictionary<string, AttributeValue>? lastEvaluatedKey = null;

        do
        {
            var request = new ScanRequest
            {
                TableName = tableName,
                FilterExpression = "begins_with(#pk, :prefix)",
                ExpressionAttributeNames = new Dictionary<string, string>
                {
                    ["#pk"] = DynamoDbEventStoreTableSchema.PartitionKey
                },
                ExpressionAttributeValues = new Dictionary<string, AttributeValue>
                {
                    [":prefix"] = new AttributeValue { S = pkPrefix }
                },
                ExclusiveStartKey = lastEvaluatedKey
            };

            var response = await dynamoDb.ScanAsync(request, cancellationToken).ConfigureAwait(false);

            foreach (var item in response.Items)
            {
                var payload = item[DynamoDbEventStoreTableSchema.PayloadAttribute];
                var events = await _serializer
                    .DeserializeEventStreamItemStreamsToEventsAsync(payload.BS, cancellationToken)
                    .ConfigureAwait(false);

                foreach (var @event in events)
                {
                    yield return @event;
                }
            }

            lastEvaluatedKey = response.LastEvaluatedKey;
        }
        while (lastEvaluatedKey is { Count: > 0 });
    }
}
```

**Table name resolution — check first:**
`DynamoDbEventStore` uses a private `TableName(Type aggregateType)` method that wraps `tableResolver`.
Find the exact `ITableResolver` method signature and replicate the call here.
The table is keyed by `DynamoDbEventStoreOptions.TableId` (a constant — find its value).

**Register in DI:**
Find the `ServiceCollectionExtensions` or `IEventSourcingBuilder` extension for
`Magiq.Platform.EventSourcing.DynamoDb` and add:
```csharp
services.AddSingleton<IEventScanner, DynamoDbEventScanner>();
```

---

### Piece 3 — `IProjectionReplayCoordinator`, `ReplayOptions`, `ReplayProgress`, `ProjectionReplayException`
**Project:** `Magiq.Platform.Projections.Abstractions`

**File:** `Replay/IProjectionReplayCoordinator.cs` — replace the commented-out content entirely:

```csharp
namespace Magiq.Platform.Projections.Replay;

/// <summary>
/// Orchestrates a full projection replay for a given aggregate type and tenant.
/// Streams all domain events from the event store and dispatches them through
/// the projection pipeline in batches.
///
/// IMPORTANT — version guard:
/// The projection dispatcher skips events where current.ProjectedVersion >= event version.
/// If existing read model records are stale (projected from a buggy handler), they will
/// block the replay. Delete affected read model records via IProjectionStore before calling
/// ReplayAsync so the dispatcher sees no existing record and re-projects from scratch.
/// </summary>
public interface IProjectionReplayCoordinator
{
    /// <summary>
    /// Replays all domain events for the specified aggregate type and tenant through
    /// the projection pipeline.
    /// </summary>
    Task ReplayAsync(ReplayOptions options, CancellationToken cancellationToken = default);
}
```

**File:** `Replay/ReplayOptions.cs` (new):

```csharp
namespace Magiq.Platform.Projections.Replay;

/// <summary>Options controlling a projection replay run.</summary>
public record ReplayOptions
{
    /// <summary>Tenant to replay, or null for global (non-tenant-scoped) aggregates.</summary>
    public string? TenantId { get; init; }

    /// <summary>CLR type of the aggregate whose events to replay (e.g. typeof(Asset)).</summary>
    public required Type AggregateType { get; init; }

    /// <summary>Number of events dispatched per batch. Default 25.</summary>
    public int BatchSize { get; init; } = 25;

    /// <summary>Optional progress receiver. Reports after each batch.</summary>
    public IProgress<ReplayProgress>? Progress { get; init; }
}
```

**File:** `Replay/ReplayProgress.cs` (new):

```csharp
namespace Magiq.Platform.Projections.Replay;

/// <param name="EventsProcessed">Cumulative events dispatched so far.</param>
/// <param name="BatchesCompleted">Cumulative batches dispatched so far.</param>
public record ReplayProgress(int EventsProcessed, int BatchesCompleted);
```

**File:** `Replay/ProjectionReplayException.cs` — uncomment and keep as-is:

```csharp
namespace Magiq.Platform.Projections.Replay;

public class ProjectionReplayException(string message, Exception? innerException = null)
    : ProjectionException(message, innerException);
```

No new project references needed for this piece — `ReplayOptions.AggregateType` is `System.Type`,
no `IDomainEvent` or event sourcing dependency.

---

### Piece 4 — `ProjectionReplayCoordinator`
**Project:** `Magiq.Platform.Projections`

**New .csproj dependency** — add to `Magiq.Platform.Projections.csproj`:
```xml
<ProjectReference Include="..\Magiq.Platform.EventSourcing.Abstractions\Magiq.Platform.EventSourcing.Abstractions.csproj"/>
```

Verify the relative path is correct for the solution layout.

**New file:** `Replay/ProjectionReplayCoordinator.cs`

```csharp
namespace Magiq.Platform.Projections.Replay;

public sealed class ProjectionReplayCoordinator(
    IEventScanner eventScanner,
    IProjectionPipeline projectionPipeline,
    ILogger<ProjectionReplayCoordinator> logger) : IProjectionReplayCoordinator
{
    public async Task ReplayAsync(ReplayOptions options, CancellationToken cancellationToken = default)
    {
        var scanOptions = new EventScanOptions
        {
            TenantId = options.TenantId,
            AggregateType = options.AggregateType
        };

        var batch = new List<object>(options.BatchSize);
        var eventsProcessed = 0;
        var batchesCompleted = 0;

        logger.LogInformation(
            "Projection replay starting — aggregate: {AggregateType}, tenant: {TenantId}",
            options.AggregateType.Name,
            options.TenantId ?? "(global)");

        await foreach (var @event in eventScanner.ScanAsync(scanOptions, cancellationToken).ConfigureAwait(false))
        {
            batch.Add(@event);

            if (batch.Count < options.BatchSize)
            {
                continue;
            }

            await projectionPipeline.DispatchBatchAsync(batch, cancellationToken).ConfigureAwait(false);
            eventsProcessed += batch.Count;
            batchesCompleted++;
            options.Progress?.Report(new ReplayProgress(eventsProcessed, batchesCompleted));
            logger.LogDebug("Batch {Batch} dispatched — {Total} events processed", batchesCompleted, eventsProcessed);
            batch.Clear();
        }

        if (batch.Count > 0)
        {
            await projectionPipeline.DispatchBatchAsync(batch, cancellationToken).ConfigureAwait(false);
            eventsProcessed += batch.Count;
            batchesCompleted++;
            options.Progress?.Report(new ReplayProgress(eventsProcessed, batchesCompleted));
        }

        logger.LogInformation(
            "Projection replay complete — {EventsProcessed} events in {Batches} batches",
            eventsProcessed, batchesCompleted);
    }
}
```

**Register in `ServiceCollectionExtensions.AddProjections`:**

In both `AddProjections(Action<IProjectionsBuilder>)` and `AddProjections()` overloads, add:
```csharp
services.TryAddScoped<IProjectionReplayCoordinator, ProjectionReplayCoordinator>();
```

---

## Build order

1. `Magiq.Platform.EventSourcing.Abstractions` — add `IEventScanner`, `EventScanOptions`
2. `Magiq.Platform.EventSourcing.DynamoDb` — add `DynamoDbEventScanner`, register in DI
3. `Magiq.Platform.Projections.Abstractions` — uncomment + replace `IProjectionReplayCoordinator`, add `ReplayOptions`, `ReplayProgress`, uncomment `ProjectionReplayException`
4. `Magiq.Platform.Projections` — add ProjectReference to EventSourcing.Abstractions, add `ProjectionReplayCoordinator`, register in `AddProjections`

Build and run unit tests after each piece before moving to the next.

---

## Things to verify before writing code

1. **`ITableResolver` method signature** — check how `DynamoDbEventStore.TableName(Type)` calls
   `tableResolver` and replicate exactly in `DynamoDbEventScanner`.

2. **`GetAggregateType()` extension method** — used in `DynamoDbEventStore` as
   `aggregate.GetUnproxiedType().GetAggregateType()`. Verify it also works on a bare `Type`
   (i.e. `typeof(Asset).GetAggregateType()`) — if not, find the correct way to derive the
   aggregate type string from a `Type`.

3. **`EventStreamItemSerializer` accessibility** — it's used inside `DynamoDbEventStore`.
   Confirm it's `internal` (not `private`) so `DynamoDbEventScanner` (same project) can use it.

4. **`IS3EventPayloadStore` accessibility** — confirm it's `internal` so the same
   `serviceProvider.GetService<IS3EventPayloadStore>()` pattern works in the scanner.

5. **Relative ProjectReference path** — `Magiq.Platform.Projections` → `Magiq.Platform.EventSourcing.Abstractions`.
   Verify the path before adding it to the .csproj.

6. **Existing DI registration for EventSourcing.DynamoDb** — find where `DynamoDbEventStore`
   is registered and add `DynamoDbEventScanner` in the same place.

---

## What is explicitly out of scope (do not implement)

- **Shadow table approach** — `DynamoDbProjectionReplayStore` stays as a stub with `NotImplementedException`.
  The commented-out code inside it describes the future shadow-table replay strategy. Leave it.
- **Clearing existing records** — the coordinator does not delete read model records. Callers do.
- **Date range filtering** — `EventScanOptions` has no `From`/`To` date. DynamoDB sort key is
  aggregate version, not timestamp. Timestamp filtering would require a full scan + filter by `ts`
  attribute. Defer to a future iteration.
- **Per-event-type filtering** — the scanner returns all events for the aggregate type. The
  `ProjectionPipeline` only dispatches to handlers registered for each event type, so unhandled
  events are silently ignored — no filtering needed at the scanner level.
- **Progress persistence / crash recovery** — replay is stateless. If interrupted, re-run from scratch.

---

## How magiq-media will use this (for reference — implement separately)

After this platform work ships as a new NuGet version, `magiq-media` will add:

```
projections rebuild --module <name> --tenant <name> [--confirm] [--dry-run]
```

The CLI command will:
1. Delete affected read model records via `IProjectionStore<T>.DeleteBatchAsync` (handles version guard)
2. Call `IProjectionReplayCoordinator.ReplayAsync(options, ct)`
3. Stream `ReplayProgress` to the console

The module name maps to an aggregate type (e.g. `--module assets` → `typeof(Asset)`).
