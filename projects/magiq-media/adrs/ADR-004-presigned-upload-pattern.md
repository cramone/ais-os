# ADR-004: Client-Direct S3 Upload via Pre-Signed URLs

**Status:** Accepted
**Date:** 2026-03-10
**Deciders:** Chase Ramone

---

## Context

Media assets can be large (images up to 50MB, videos up to 2GB). We need to decide how raw binary data flows from the client to S3.

Options:
1. **Client → API → S3** (proxy through Lambda/ECS)
2. **Client → S3 directly via pre-signed PUT URL** (Ingest API issues URL, client uploads directly)
3. **S3 Multipart Upload via pre-signed parts** (for large files)

---

## Decision

**Clients upload directly to S3 using a pre-signed PUT URL** issued by the Ingest API. For files > 100MB, the Ingest API issues pre-signed multipart upload URLs instead.

**Flow:**
```
1. Client POST /assets/upload-url  →  Ingest API
2. Ingest API dispatches UploadAsset command
3. Ingest API generates pre-signed S3 PUT URL (TTL: 15 minutes)
4. Ingest API returns { assetId, uploadUrl, expiresAt }
5. Client PUT binary to uploadUrl directly
6. S3 emits ObjectCreated event → SQS
7. Ingest API SQS trigger dispatches ConfirmAssetUpload command
8. Domain transitions asset to Validating state
```

**Pre-signed URL constraints:**
- `content-type`: signed into the URL — client must PUT with the matching `Content-Type` header
- `content-length` (exact): the declared `SizeBytes` is signed as a required `Content-Length` header — S3 rejects any PUT that doesn't match (SignatureDoesNotMatch). This is the correct enforcement mechanism for pre-signed PUT URLs. Note: `content-length-range` (a range condition) is a **POST policy feature only** and is not available for pre-signed PUT URLs. Upper-bound enforcement is layered:
  1. Application-layer guard in `UploadAssetHandler` (rejects before URL is issued)
  2. S3 bucket policy condition `s3:content-length-range` on `media-source` and `media-documents` buckets (CDK)
  3. Server-side re-check in `ConfirmAssetUploadHandler` (defence-in-depth)
- Key: `{tenantId}/{shard}/{assetId}/original.{ext}` in the `media-source` bucket (processable assets), or `{tenantId}/{shard}/{assetId}/document.{ext}` in the `media-documents` bucket (assets whose MediaProfile lacks the `Processing` capability). Bucket and key are determined by `StorageKeyGenerator`; the client cannot influence them. `{shard}` = last 4 hex chars of the UUID v7 `AssetId` (no dashes). `OwnerId` is excluded — keys must remain valid across ownership transfers.

**S3 notification:** `s3:ObjectCreated:Put` on both `media-source` and `media-documents` buckets → SNS → SQS queue → Ingest API SQS handler.

---

## Consequences

**Positive:**
- Lambda is not on the data path for binary I/O — eliminates Lambda payload limits (6MB sync, 256KB async response), memory pressure, and transfer time costs
- S3 handles durability, multipart, and retry natively
- Pre-signed URL scoping (key, content-type, size) prevents clients from overwriting arbitrary keys
- Scales to any file size without Lambda changes

**Negative / Accepted trade-offs:**
- Client must make two requests (get URL, then PUT to S3) — minor UX consideration, well-understood pattern
- If client uploads with incorrect `Content-Type` header, S3 rejects the PUT — Ingest API must communicate this clearly in the response
- Virus scanning / content validation must happen async after upload (see Processing Worker); we cannot block the upload for synchronous scanning
- Pre-signed URL leakage: a captured URL can be used by anyone within the TTL. Mitigated by 15-minute TTL and S3 conditions. Acceptable risk.

**Multipart for large files (> 100MB):**
Ingest API will issue up to 10,000 pre-signed part URLs via `CreateMultipartUpload` + `UploadPart`. Client is responsible for assembling parts and calling `CompleteMultipartUpload`. Ingest API tracks `UploadId` in a short-lived DynamoDB entry (TTL-based, 30 minutes).

**Not chosen — Proxy through Lambda:**
- Lambda 6MB synchronous payload limit makes video uploads impossible
- Even with streaming, Lambda memory and timeout configuration become a reliability risk
- Transfer costs: data would transit Lambda unnecessarily (egress from S3 + ingress back)

---

## Review Trigger

Revisit if: compliance requirements mandate server-side content inspection before S3 write (consider S3 Object Lambda or a dedicated gateway). Current design defers virus/content scanning to the async validation step post-upload.

---

## Extension: Presigned GET URLs for Download

**Added:** 2026-05-29

The same client-direct S3 pattern applies to reads. The Query API issues presigned S3 GET URLs for asset and rendition downloads — no Lambda proxy on the read path either.

**Interface:** `IPresignedGetUrlService` in `AssetManagement.ReadModel`, implemented by `S3PresignedGetUrlService` in `AssetManagement.ReadModel.Infrastructure`. Registered in the Query API host.

**Endpoints:**
- `GET /v1/assets/{assetId}/download` — original asset binary
- `GET /v1/assets/{assetId}/renditions/{renditionType}/download` — specific rendition

**GET URL constraints:**
- TTL: 15 minutes (same as upload TTL — `AssetDownloadStorageOptions.PresignedUrlExpiryMinutes`)
- No `Content-Type` or `Content-Length` signed — GET has no body
- Original asset download: `ResponseContentDisposition: attachment; filename="{originalFileName}"` signed into the URL so browsers trigger a save dialog
- Rendition download: no `ResponseContentDisposition` — renditions are display assets

**Status gate:** enforced in the query handler before URL issuance, not by S3. Only `Active` and `Archived` assets can generate download URLs; any other status returns `409 AssetNotDownloadable`.

**Bucket resolution:**
- Original asset: bucket stored on `AssetDetailReadModel.BucketName` (projected from `AssetUploadInitiated.BucketName`)
- Renditions: always `media-renditions` (resolved from `AssetDownloadStorageOptions.RenditionBucketName`)
