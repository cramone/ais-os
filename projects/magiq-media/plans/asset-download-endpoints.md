# Implementation Plan — Asset Download Endpoints

**Scope:** Add presigned S3 GET URL endpoints for original assets and renditions.
**Routes:**
- `GET /v1/assets/{assetId}/download` — original asset
- `GET /v1/assets/{assetId}/renditions/{renditionType}/download` — specific rendition

---

## Context

The spec references download as status-gated (INGEST-WORKFLOW.md:159) but no endpoint exists in the spec or codebase. `IPresignedUrlService` currently only covers PUT (ADR-004). Both new endpoints live in the **Query API** — they generate short-lived presigned GET URLs from existing `StorageKey` values already present on `AssetDetailReadModel`.

No new domain events, commands, or projectors are required.

---

## Spec Changes

### 1. `spec/contexts/AssetManagement/aggregates/Asset/asset.api.md`

**Route Structure table** — add two lines:

```
GET    /v1/assets/{assetId}/download                             Get presigned download URL (original)
GET    /v1/assets/{assetId}/renditions/{renditionType}/download  Get presigned download URL (rendition)
```

**Authorization Requirements table** — add:

| Endpoint | Requirement |
|---|---|
| `GET /v1/assets/{assetId}/download` | `caller.owner_id == asset.OwnerId` · asset must be `Active` or `Archived` |
| `GET /v1/assets/{assetId}/renditions/{renditionType}/download` | `caller.owner_id == asset.OwnerId` · asset must be `Active` or `Archived` |

**New Read Endpoints section** — document both endpoints (see §Endpoint Spec below).

**Command → Event → Projection table** — add:

| API Call | Command | Domain Event | Projection |
|---|---|---|---|
| `GET /v1/assets/{id}/download` | `GetAssetDownloadUrlQuery` | — | reads `media-asset-detail` |
| `GET /v1/assets/{id}/renditions/{type}/download` | `GetRenditionDownloadUrlQuery` | — | reads `media-asset-detail` |

---

### Endpoint Spec (to insert into asset.api.md)

#### `GET /v1/assets/{assetId}/download`

Returns a short-lived presigned S3 GET URL for the original asset binary.

**Status guard:** Asset must be `Active` or `Archived`. All other statuses return `409`.

**Response `200 OK`:**
```json
{
  "downloadUrl": "https://media-source.s3.amazonaws.com/tenantId/.../original.jpg?X-Amz-...",
  "expiresAt": "2026-05-29T12:15:00Z",
  "fileName": "photo.jpg",
  "contentType": "image/jpeg",
  "sizeBytes": 1048576
}
```

**Error responses:**
- `401` — unauthenticated
- `403` — caller does not own this asset
- `404` — asset not found
- `409` — asset is not `Active` or `Archived`

**Error response example (`409 Conflict`):**
```json
{
  "type": "https://errors.magiqmedia.com/domain/asset-not-downloadable",
  "title": "Asset is not downloadable",
  "status": 409,
  "detail": "Asset 018e4c7a-... is in status Processing. Only Active or Archived assets can be downloaded.",
  "extensions": { "errorCode": "AssetNotDownloadable", "currentStatus": "Processing" }
}
```

---

#### `GET /v1/assets/{assetId}/renditions/{renditionType}/download`

Returns a short-lived presigned S3 GET URL for a specific rendition of the asset.

**Status guard:** Asset must be `Active` or `Archived`. Returns `409` for any other status.

**`renditionType`** is case-insensitive. Valid values are whatever rendition types exist on the asset (e.g. `thumbnail`, `preview`, `web`). Returns `404` if the rendition type does not exist on this asset.

**Response `200 OK`:**
```json
{
  "downloadUrl": "https://media-source.s3.amazonaws.com/tenantId/.../thumbnail.webp?X-Amz-...",
  "expiresAt": "2026-05-29T12:15:00Z",
  "renditionType": "thumbnail",
  "contentType": "image/webp",
  "sizeBytes": 12400,
  "width": 256,
  "height": 256
}
```

**Error responses:**
- `401` — unauthenticated
- `403` — caller does not own this asset
- `404` — asset not found, or rendition type does not exist on this asset
- `409` — asset is not `Active` or `Archived`

---

### 2. `adrs/ADR-004-presigned-upload-pattern.md`

Add a section at the bottom:

```markdown
## Extension: Presigned GET URLs for Download

**Added:** 2026-05-29

The same pattern is used for read access. `IPresignedUrlService` now exposes
`GenerateGetUrlAsync(StorageKey, CancellationToken)`. This is called by the
`GetAssetDownloadUrlQuery` and `GetRenditionDownloadUrlQuery` handlers in the
Query API.

**GET URL constraints:**
- TTL: 15 minutes (same as upload TTL — `S3AssetStorageOptions.PresignedUrlExpiryMinutes`)
- No `Content-Type` or `Content-Length` signed — GET has no body
- `ResponseContentDisposition` header set to `attachment; filename="{originalFileName}"` on
  the original download URL so browsers trigger a save dialog
- Rendition downloads do not set `ResponseContentDisposition` — renditions are display assets

**Status gate:** enforced in the query handler before URL issuance, not by S3.
Only `Active` and `Archived` assets can generate download URLs. Handlers return
`DomainError.AssetNotDownloadable` for any other status.
```

---

## Repo Changes

### Layer 1 — `AssetManagement.WriteModel` (Storage abstraction)

**File: `AssetManagement.WriteModel/Storage/IPresignedUrlService.cs`**

Add method to the existing interface:

```csharp
/// <summary>
/// Generates a pre-signed S3 GET URL for direct client download (ADR-004 extension).
/// </summary>
/// <param name="storageKey">Bucket + key for the asset or rendition.</param>
/// <param name="downloadFileName">
/// When set, signed as <c>ResponseContentDisposition: attachment; filename="{value}"</c>.
/// Pass <c>null</c> for renditions (no forced download prompt).
/// </param>
/// <param name="cancellationToken">Cancellation token.</param>
Task<PresignedDownloadResult> GenerateGetUrlAsync(
    StorageKey storageKey,
    string? downloadFileName,
    CancellationToken cancellationToken = default);
```

Add new result type alongside `PresignedUploadResult`:

```csharp
// AssetManagement.WriteModel/Storage/PresignedDownloadResult.cs
public sealed record PresignedDownloadResult(string Url, DateTimeOffset ExpiresAt);
```

---

### Layer 2 — `AssetManagement.WriteModel.Infrastructure`

**File: `Storage/S3PresignedUrlService.cs`**

Implement `GenerateGetUrlAsync`:

```csharp
public async Task<PresignedDownloadResult> GenerateGetUrlAsync(
    StorageKey storageKey,
    string? downloadFileName,
    CancellationToken cancellationToken = default)
{
    var expiresAt = DateTime.UtcNow.AddMinutes(options.Value.PresignedUrlExpiryMinutes);

    var request = new GetPreSignedUrlRequest
    {
        BucketName = storageKey.BucketName,
        Key = storageKey.Value,
        Verb = HttpVerb.GET,
        Expires = expiresAt
    };

    if (downloadFileName is not null)
    {
        request.ResponseHeaderOverrides.ContentDisposition =
            $"attachment; filename=\"{Uri.EscapeDataString(downloadFileName)}\"";
    }

    var url = await s3Client.GetPreSignedURLAsync(request);
    return new PresignedDownloadResult(url, new DateTimeOffset(expiresAt, TimeSpan.Zero));
}
```

---

### Layer 3 — `AssetManagement.ReadModel` (Query handlers)

**New folder: `Queries/GetAssetDownloadUrl/`**

```csharp
// GetAssetDownloadUrlQuery.cs
public sealed record GetAssetDownloadUrlQuery(TenantId TenantId, AssetId AssetId)
    : IQuery<AssetDownloadUrlResult>;

// GetAssetDownloadUrlResult.cs
public sealed record AssetDownloadUrlResult(
    string DownloadUrl,
    DateTimeOffset ExpiresAt,
    string FileName,
    string ContentType,
    long? SizeBytes);

// GetAssetDownloadUrlHandler.cs
public sealed class GetAssetDownloadUrlHandler(
    IReadModelReader<AssetDetailReadModel> reader,
    IPresignedUrlService presignedUrlService)
    : QueryHandler<GetAssetDownloadUrlQuery, AssetDownloadUrlResult>
{
    private static readonly IReadOnlySet<AssetStatus> DownloadableStatuses =
        new HashSet<AssetStatus> { AssetStatus.Active, AssetStatus.Archived };

    protected override async Task<Result<AssetDownloadUrlResult, IQueryError>> ExecuteAsync(
        GetAssetDownloadUrlQuery request, CancellationToken cancellationToken)
    {
        var asset = await reader.GetAsync(request, cancellationToken);
        if (asset is null)
            return ResourceNotFound("Asset not found.");

        if (!DownloadableStatuses.Contains(asset.Status))
            return DomainConflict("AssetNotDownloadable",
                $"Asset {asset.Id} is in status {asset.Status}. Only Active or Archived assets can be downloaded.");

        var result = await presignedUrlService.GenerateGetUrlAsync(
            StorageKey.From(asset.StorageKey),
            asset.OriginalFileName,
            cancellationToken);

        return new AssetDownloadUrlResult(
            result.Url,
            result.ExpiresAt,
            asset.OriginalFileName,
            asset.ContentType,
            asset.SizeBytes);
    }
}
```

**New folder: `Queries/GetRenditionDownloadUrl/`**

```csharp
// GetRenditionDownloadUrlQuery.cs
public sealed record GetRenditionDownloadUrlQuery(TenantId TenantId, AssetId AssetId, string RenditionType)
    : IQuery<RenditionDownloadUrlResult>;

// GetRenditionDownloadUrlResult.cs
public sealed record RenditionDownloadUrlResult(
    string DownloadUrl,
    DateTimeOffset ExpiresAt,
    string RenditionType,
    string ContentType,
    long SizeBytes,
    int? Width,
    int? Height);

// GetRenditionDownloadUrlHandler.cs
public sealed class GetRenditionDownloadUrlHandler(
    IReadModelReader<AssetDetailReadModel> reader,
    IPresignedUrlService presignedUrlService)
    : QueryHandler<GetRenditionDownloadUrlQuery, RenditionDownloadUrlResult>
{
    private static readonly IReadOnlySet<AssetStatus> DownloadableStatuses =
        new HashSet<AssetStatus> { AssetStatus.Active, AssetStatus.Archived };

    protected override async Task<Result<RenditionDownloadUrlResult, IQueryError>> ExecuteAsync(
        GetRenditionDownloadUrlQuery request, CancellationToken cancellationToken)
    {
        var asset = await reader.GetAsync(request, cancellationToken);
        if (asset is null)
            return ResourceNotFound("Asset not found.");

        if (!DownloadableStatuses.Contains(asset.Status))
            return DomainConflict("AssetNotDownloadable",
                $"Asset {asset.Id} is in status {asset.Status}. Only Active or Archived assets can be downloaded.");

        var rendition = asset.Renditions
            .FirstOrDefault(r => r.RenditionType.Equals(request.RenditionType, StringComparison.OrdinalIgnoreCase));

        if (rendition is null)
            return ResourceNotFound($"Rendition '{request.RenditionType}' not found on asset {asset.Id}.");

        var result = await presignedUrlService.GenerateGetUrlAsync(
            StorageKey.From(rendition.StorageKey),
            downloadFileName: null, // no forced download for renditions
            cancellationToken);

        return new RenditionDownloadUrlResult(
            result.Url,
            result.ExpiresAt,
            rendition.RenditionType,
            rendition.ContentType,
            rendition.SizeBytes,
            rendition.Width,
            rendition.Height);
    }
}
```

> **Note:** `IPresignedUrlService` is currently registered only in `AssetManagement.WriteModel.Infrastructure`. The Query API host needs it too — see Layer 6.

---

### Layer 4 — `AssetManagement.ReadModel.Endpoints`

**New folder: `V1/GetAssetDownloadUrl/`**

```csharp
// GetAssetDownloadUrlRequest.cs
public sealed class GetAssetDownloadUrlRequest
{
    public string AssetId { get; init; } = string.Empty;
}

// GetAssetDownloadUrlResponse.cs
public sealed record GetAssetDownloadUrlResponse(
    string DownloadUrl,
    DateTimeOffset ExpiresAt,
    string FileName,
    string ContentType,
    long? SizeBytes);

// GetAssetDownloadUrlEndpoint.cs
public sealed class GetAssetDownloadUrlEndpoint(IQueryDispatcher dispatch)
    : AssetManagementEndpoint<GetAssetDownloadUrlRequest, GetAssetDownloadUrlResponse>
{
    public override void Configure()
    {
        Get("/assets/{assetId}/download");
        Description(x => x
            .WithName("GetAssetDownloadUrl")
            .WithTags("Assets")
            .WithGroupName("v1")
            .Produces(200)
            .ProducesProblem(401)
            .ProducesProblem(403)
            .ProducesProblem(404)
            .ProducesProblem(409)
        );
        Summary(summary =>
        {
            summary.Summary = "Get a presigned download URL for an asset.";
            summary.Params["assetId"] = "The unique identifier of the asset.";
            summary.Response(200, "A short-lived presigned GET URL for the original asset binary.");
            summary.Response(401, "Authentication is required.");
            summary.Response(403, "The caller does not own this asset.");
            summary.Response(404, "Asset not found.");
            summary.Response(409, "Asset is not Active or Archived and cannot be downloaded.");
        });
        Version(1);
    }

    public override async Task HandleAsync(GetAssetDownloadUrlRequest req, CancellationToken cancellationToken)
    {
        var query = new GetAssetDownloadUrlQuery(TenantId, AssetId.From(req.AssetId));
        var result = await dispatch.QueryAsync(query, cancellationToken);

        if (!result.IsSuccess)
        {
            await SendQueryErrorAsync(result.Error, cancellationToken);
            return;
        }

        var r = result.Value;
        await SendOkAsync(new GetAssetDownloadUrlResponse(
            r.DownloadUrl, r.ExpiresAt, r.FileName, r.ContentType, r.SizeBytes), cancellationToken);
    }
}
```

**New folder: `V1/GetRenditionDownloadUrl/`**

```csharp
// GetRenditionDownloadUrlRequest.cs
public sealed class GetRenditionDownloadUrlRequest
{
    public string AssetId { get; init; } = string.Empty;
    public string RenditionType { get; init; } = string.Empty;
}

// GetRenditionDownloadUrlResponse.cs
public sealed record GetRenditionDownloadUrlResponse(
    string DownloadUrl,
    DateTimeOffset ExpiresAt,
    string RenditionType,
    string ContentType,
    long SizeBytes,
    int? Width,
    int? Height);

// GetRenditionDownloadUrlEndpoint.cs
public sealed class GetRenditionDownloadUrlEndpoint(IQueryDispatcher dispatch)
    : AssetManagementEndpoint<GetRenditionDownloadUrlRequest, GetRenditionDownloadUrlResponse>
{
    public override void Configure()
    {
        Get("/assets/{assetId}/renditions/{renditionType}/download");
        Description(x => x
            .WithName("GetRenditionDownloadUrl")
            .WithTags("Assets")
            .WithGroupName("v1")
            .Produces(200)
            .ProducesProblem(401)
            .ProducesProblem(403)
            .ProducesProblem(404)
            .ProducesProblem(409)
        );
        Summary(summary =>
        {
            summary.Summary = "Get a presigned download URL for a specific asset rendition.";
            summary.Params["assetId"] = "The unique identifier of the asset.";
            summary.Params["renditionType"] = "The rendition type (e.g. thumbnail, preview). Case-insensitive.";
            summary.Response(200, "A short-lived presigned GET URL for the rendition binary.");
            summary.Response(401, "Authentication is required.");
            summary.Response(403, "The caller does not own this asset.");
            summary.Response(404, "Asset not found, or rendition type does not exist on this asset.");
            summary.Response(409, "Asset is not Active or Archived and cannot be downloaded.");
        });
        Version(1);
    }

    public override async Task HandleAsync(GetRenditionDownloadUrlRequest req, CancellationToken cancellationToken)
    {
        var query = new GetRenditionDownloadUrlQuery(TenantId, AssetId.From(req.AssetId), req.RenditionType);
        var result = await dispatch.QueryAsync(query, cancellationToken);

        if (!result.IsSuccess)
        {
            await SendQueryErrorAsync(result.Error, cancellationToken);
            return;
        }

        var r = result.Value;
        await SendOkAsync(new GetRenditionDownloadUrlResponse(
            r.DownloadUrl, r.ExpiresAt, r.RenditionType, r.ContentType, r.SizeBytes, r.Width, r.Height),
            cancellationToken);
    }
}
```

---

### Layer 5 — `AssetManagement.ReadModel.Infrastructure`

Create a new infrastructure project (or add to existing read model infra if one exists):

**`AssetManagement.ReadModel.Infrastructure/ServiceCollectionExtensions.cs`**

Register `IPresignedUrlService` for the Query API host:

```csharp
services.AddScoped<IPresignedUrlService, S3PresignedUrlService>();
// IAmazonS3 is assumed already registered by the host's AWS setup
```

Alternatively: extract the registration of `IPresignedUrlService` + `S3PresignedUrlService` out of `AssetManagement.WriteModel.Infrastructure` into a shared `AssetManagement.Storage.Infrastructure` registration method callable from both the Ingest API host and the Query API host.

> **Decision point:** Check whether the Query API host (`src/hosts/QueryApi`) already wires up `IAmazonS3`. If yes, just add the `IPresignedUrlService` registration there. If no, also add the AWS S3 client registration to the Query API host DI setup.

---

### Layer 6 — Host wiring (`src/hosts/QueryApi`)

Ensure the Query API host registers the new handlers and the S3 service:

1. Confirm `IAmazonS3` is registered (check `Function.cs` or `Startup.cs`).
2. Call the `IPresignedUrlService` registration from step 5.
3. The FastEndpoints auto-discovery will pick up the new endpoint classes if they're in a referenced assembly — verify the `AssetManagement.ReadModel.Endpoints` assembly is already referenced by the Query API host (it should be, given `GetAssetById` works).

---

## DomainError addition

Add to the shared error catalogue (wherever `DomainError` / `IQueryError` codes are defined):

```csharp
public static IQueryError AssetNotDownloadable(string assetId, string currentStatus) =>
    DomainConflict(
        "AssetNotDownloadable",
        $"Asset {assetId} is in status {currentStatus}. Only Active or Archived assets can be downloaded.");
```

---

## Implementation order

1. `IPresignedUrlService` — add `GenerateGetUrlAsync` + `PresignedDownloadResult`
2. `S3PresignedUrlService` — implement the new method
3. `GetAssetDownloadUrlQuery/Handler` + `GetRenditionDownloadUrlQuery/Handler`
4. Endpoint classes + request/response models
5. Host DI wiring (confirm S3 client + register `IPresignedUrlService` in Query API)
6. Spec updates (asset.api.md routes, auth table, endpoint docs, ADR-004 extension section)
7. Manual smoke test: upload an asset, wait for `Active`, hit both download endpoints, verify URL resolves from S3

---

## What this does NOT require

- No new domain events or commands
- No projector changes — `StorageKey` and `Renditions[].StorageKey` are already on `AssetDetailReadModel`
- No DynamoDB table changes
- No CDK changes (S3 bucket policies for PUT are unchanged; GET is already permitted for the Lambda execution role)
