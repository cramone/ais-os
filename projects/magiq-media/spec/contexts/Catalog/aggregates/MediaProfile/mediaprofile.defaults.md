# MediaProfile — Platform Default Profiles

_Context: `Catalog`_
_Aggregate: `MediaProfile`_

---

## Purpose

Platform default media profiles are seeded at tenant provisioning time with `OwnerId = "owner_system"`. They are available to every tenant via the `OwnerId IN [ownerId, "owner_system"]` query pattern and serve as the baseline structural contracts that tenants can use directly or use as the basis for their own tenant-owned profiles.

All platform defaults are published at seed time (status `Published`, `PublishedVersion = 1`). They are never deprecated by the platform without a migration path.

---

## Profiles

### 1. Simple Image

| Property | Value |
|---|---|
| `Name` | `Simple Image` |
| `Description` | Single image asset. Renditions and EXIF metadata extracted on upload. |
| `OwnerId` | `owner_system` |
| `Capabilities` | `Processing`, `VersionControl` |
| `ReviewPolicy` | `None` |
| `CheckoutPolicy` | `None` |

**Asset Definitions:**

| RoleName | AcceptedContentTypes | Required | AllowMultiple | IsDefault | MaxFileSizeBytes | DimensionConstraints |
|---|---|---|---|---|---|---|
| `primary` | `Image` | `true` | `false` | `true` | — | — |

**Notes:**
- Routes through the full processing pipeline (Sharp/ImageMagick renditions, ExifTool metadata extraction).
- Suitable for standalone photos, artwork, graphics, and thumbnails.
- Tenant can open a revision to add dimension constraints or a file size cap without altering the content type.

---

### 2. Simple Video

| Property | Value |
|---|---|
| `Name` | `Simple Video` |
| `Description` | Single video asset with optional static thumbnail. |
| `OwnerId` | `owner_system` |
| `Capabilities` | `Processing`, `VersionControl` |
| `ReviewPolicy` | `None` |
| `CheckoutPolicy` | `None` |

**Asset Definitions:**

| RoleName | AcceptedContentTypes | Required | AllowMultiple | IsDefault | MaxFileSizeBytes | DimensionConstraints |
|---|---|---|---|---|---|---|
| `primary` | `Video` | `true` | `false` | `true` | — | — |
| `thumbnail` | `Image` | `false` | `false` | `false` | — | — |

**Notes:**
- `primary` routes to AWS MediaConvert (async); processing saga timeout is 4 hours.
- `thumbnail` is provided by the caller rather than extracted — useful when a specific frame is required before MediaConvert completes.
- File size cap on `primary` should be set in tenant-owned revisions; no platform default is enforced.

---

### 3. Simple Audio

| Property | Value |
|---|---|
| `Name` | `Simple Audio` |
| `Description` | Single audio asset with optional cover artwork. |
| `OwnerId` | `owner_system` |
| `Capabilities` | `Processing`, `VersionControl` |
| `ReviewPolicy` | `None` |
| `CheckoutPolicy` | `None` |

**Asset Definitions:**

| RoleName | AcceptedContentTypes | Required | AllowMultiple | IsDefault | MaxFileSizeBytes | DimensionConstraints |
|---|---|---|---|---|---|---|
| `primary` | `Audio` | `true` | `false` | `true` | — | — |
| `artwork` | `Image` | `false` | `false` | `false` | — | — |

**Notes:**
- `primary` routes through the audio rendition pipeline (Lambda layer).
- `artwork` is processed as a standard image asset (thumbnails extracted).

---

### 4. Document

| Property | Value |
|---|---|
| `Name` | `Document` |
| `Description` | Document-only asset. Virus scan only — no renditions generated. Used for registration supporting documents and other non-processed file attachments. |
| `OwnerId` | `owner_system` |
| `Capabilities` | `VersionControl` |
| `ReviewPolicy` | `None` |
| `CheckoutPolicy` | `None` |

**Asset Definitions:**

| RoleName | AcceptedContentTypes | Required | AllowMultiple | IsDefault | MaxFileSizeBytes | DimensionConstraints |
|---|---|---|---|---|---|---|
| `primary` | `Document` | `true` | `false` | `true` | — | — |

**Notes:**
- The absence of `Processing` capability is intentional and load-bearing. The `AssetIngestionSaga` routes these assets through the fast-exit (bypass) path — virus scan only, no rendition pipeline. Originals are stored in `media-documents` (not `media-source`).
- This profile is the required structural contract for **registration supporting documents** — the Registration context requires document media-items (MediaItems whose MediaProfile lacks `Processing`) for `AttachItemToRegistration` and `RequestAmendment`.
- Do not add the `Processing` capability to this profile or to revisions used as registration documents. Doing so would route uploads through the full pipeline and change the storage bucket — breaking the Registration context's expectations.
- Quota tracking does not apply to assets on profiles without `Processing`.

---

### 5. Governed Media Record

| Property | Value |
|---|---|
| `Name` | `Governed Media Record` |
| `Description` | Multi-asset catalog entry with structured governance: review gate before publish, checkout lock for edit isolation, and Registration capability for formal authority submission. |
| `OwnerId` | `owner_system` |
| `Capabilities` | `Processing`, `VersionControl`, `Review`, `CheckInOut`, `Registration` |
| `ReviewPolicy` | `RequiredForPublish` |
| `CheckoutPolicy` | `RequiredForEdit` |

**Asset Definitions:**

| RoleName | AcceptedContentTypes | Required | AllowMultiple | IsDefault | MaxFileSizeBytes | DimensionConstraints |
|---|---|---|---|---|---|---|
| `primary` | `Image`, `Video`, `Audio` | `true` | `false` | `true` | — | — |
| `supporting-document` | `Document` | `false` | `true` | `false` | — | — |

**Notes:**
- `Registration` capability is included because content that requires formal governance (review + checkout) will frequently also require formal registration. The capability is permissive — having it present does not force registration on any MediaItem; it simply allows `InitiateRegistrationHandler` to pass its capability gate check.
- `supporting-document` role assets take the fast-exit processing path (no renditions, `media-documents` bucket). The `primary` asset takes the full processing path.
- `RequiredForPublish` means `SubmitForReview` creates a `MediaChangeRequest`; `MediaItemReviewSaga` waits for reviewer approval before dispatching `ApproveMediaItemCommand`. A reviewer must approve via the MCR cycle.
- `RequiredForEdit` means `CheckOutMediaItem` must be called before any write command is accepted. Concurrent edit attempts by other users return `DomainError.MediaItemCheckedOut`.
- Tenants should create a revision to restrict `primary` to a single `AcceptedContentType` and to add `DimensionConstraints` or `MaxFileSizeBytes` where appropriate.

---

## Seeding

### Why not application startup

Platform profiles are **per-tenant in DynamoDB** — the PK is `TENANT#{TenantId}#{MediaProfileId}`, so `OwnerId = "owner_system"` is a logical designation, not a shared storage partition. There is no cross-tenant row. Seeding at `Media.Api` startup is incorrect for two reasons: Lambda containers cold-start frequently and horizontally, causing concurrent seed races with no clear owner; and a single application instance has no authority to decide which tenants to seed — it only has a `TenantId` per request context.

### Trigger: `TenantProvisioned` integration event

The correct trigger is a `TenantProvisioned` integration event emitted by the (forthcoming) tenant management context. The Catalog context subscribes via the `media-cross-module-events` SQS queue and handles it with `SeedDefaultProfilesConsumer`.

> **Note:** The tenant management context is a Q2 2026 priority and is not yet spec'd. Until it exists, seeding is performed by invoking `SeedDefaultProfilesLambda` directly at tenant onboarding — see [Short-term path](#short-term-path) below.

### `SeedDefaultProfilesConsumer`

**Consumer:** `SeedDefaultProfilesConsumer` (`Catalog.WriteModel`)  
**Queue:** `media-cross-module-events`  
**Trigger:** `TenantProvisionedMessage`  
**Actor:** `SystemActor` (`ActorType = "System"`, `Id = "system"`)  

For each profile in `DefaultMediaProfiles.All`:

1. `IMediaProfileService.NameExistsAsync(tenantId, profileName)` — skip if already seeded (idempotency guard).
2. Dispatch `CreateMediaProfileCommand` with a deterministic `IdempotencyKey = Uuid5("platform-seed", $"{tenantId}:{profileSlug}")`.
3. Dispatch `AddAssetDefinitionCommand` for each asset role.
4. Dispatch `SetMediaProfileCapabilitiesCommand`, `SetReviewPolicyCommand`, `SetCheckoutPolicyCommand`.
5. Dispatch `PublishMediaProfileCommand`.

All commands run through the standard MediatR pipeline under an `SqsExecutionContext` constructed from the `TenantProvisionedMessage` attributes. No HTTP or JWT is involved. The deterministic `IdempotencyKey` makes the full sequence safe to re-run on SQS redelivery or Lambda retry.

`DefaultMediaProfiles.All` is a static list of value objects defined in `Catalog.WriteModel` — the canonical in-code representation of the five profiles defined in this document.

```csharp
// Catalog.WriteModel — DefaultMediaProfiles.cs
internal static class DefaultMediaProfiles
{
    public static IReadOnlyList<DefaultMediaProfileDefinition> All { get; } =
    [
        new("Simple Image",          "simple-image",          ...),
        new("Simple Video",          "simple-video",          ...),
        new("Simple Audio",          "simple-audio",          ...),
        new("Document",              "document",              ...),
        new("Governed Media Record", "governed-media-record", ...),
    ];
}
```

### Short-term path

Until the tenant management context exists, a standalone **`SeedDefaultProfilesLambda`** (CDK stack, `src/functions/seed-default-profiles/`) accepts a `SeedDefaultProfilesRequest` payload and runs the same `SeedDefaultProfilesConsumer` logic directly. It is invoked once per tenant via CDK or a deployment script at onboarding time.

The implementation is intentionally identical to the consumer — the only difference is the trigger. When the tenant management context is built, the Lambda is retired and the consumer takes over.

### Migrations

The seeder does **not** deprecate or modify existing platform profiles. Changes to a platform default after initial seed require an explicit migration: open a revision via `CreateMediaProfileRevisionCommand`, apply changes, and publish. Migrations run through the same `SeedDefaultProfilesLambda` (or a dedicated migration Lambda) and are versioned alongside the codebase.

---

## Tenant Customisation

Tenants can create their own profiles with `OwnerId = tenantId`. They can also open a revision on a platform default — but because `OwnerId` is set at creation and is immutable, platform profiles remain owned by `owner_system`. Tenants cannot modify a platform profile; they can only create their own by cloning the structure.

The recommended pattern for tenant-specific structural variants is:

1. Call `POST /v1/catalog/profiles` to create a new tenant-owned profile.
2. Add asset definitions, record type refs, and capabilities matching the desired structure.
3. Publish.

---

## Related

- [MediaProfile Write Model](./mediaprofile.write-model.md)
- [MediaProfile Read Model](./mediaprofile.read-model.md)
- [MediaProfile API](./mediaprofile.api.md)
- [Registration Context Overview](../../../Registration/context-overview.md)
- [Processing Context Overview](../../../Processing/context-overview.md)
- [Catalog Context Overview](../../context-overview.md)
