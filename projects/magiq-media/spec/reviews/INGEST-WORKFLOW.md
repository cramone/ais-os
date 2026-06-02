# Magiq Media — Core Ingest Workflow Reference

> Derived from spec (`spec/contexts/**/*.api.md`) cross-referenced against the actual endpoint implementations in `src/modules/`.
> Deviations between spec and implementation are called out explicitly.

---

## Prerequisites

All endpoints require:
```
Authorization: Bearer <jwt>
Content-Type: application/json
```

`TenantId` is sourced from the JWT `tenant_id` claim — never pass it in the request body.

IDs throughout this system are **UUID v7** (time-ordered). The server generates all resource IDs — they are **not** caller-supplied (unlike what the spec examples suggest). You receive the generated ID in the response.

---

## Step 1 — Create a Collection

Collections are the root organisational container. Everything lives inside one.

**Endpoint:** `POST /v1/catalog/collections`

**Description:** Creates a new top-level collection scoped to the caller's tenant. The server generates and returns the `collectionId`. The collection is immediately usable — no publish step required.

**Request:**
```json
{
  "name": "Q1 Campaign Assets",
  "description": "Assets for Q1 marketing campaign",
  "visibility": "Private"
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `name` | string | ✅ | Must be unique within tenant |
| `description` | string | ❌ | Optional |
| `visibility` | enum | ✅ | `"Private"` or `"Public"` |

**Response `201 Created`:**
```json
{
  "id": "019571a2-3f10-7b2a-8c4d-1a2b3c4d5e6f",
  "name": "Q1 Campaign Assets",
  "description": "Assets for Q1 marketing campaign",
  "visibility": "Private",
  "occurredAt": "2026-05-22T10:00:00Z"
}
```

The `id` field is the `collectionId` — capture this for use in Step 2.

**Key errors:**
- `409` — collection name already exists for this tenant

---

## Step 2 — Create a Root-Level Folder

Folders live inside a collection. A root-level folder has no parent.

**Endpoint:** `POST /v1/catalog/collections/{collectionId}/folders`

**Description:** Creates a new folder directly under the collection root. `parentFolderId` is omitted (or null) to make it a root folder. The server generates and returns the `folderId`.

**Request:**
```http
POST /v1/catalog/collections/019571a2-3f10-7b2a-8c4d-1a2b3c4d5e6f/folders
```
```json
{
  "name": "Hero Images",
  "description": "Primary hero assets for all campaigns"
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `name` | string | ✅ | Must be unique within parent scope |
| `description` | string | ❌ | Optional |
| `parentFolderId` | string | ❌ | Omit for root-level |

> `collectionId` is passed as a **route segment**, not in the body.

**Response `201 Created`:**
```json
{
  "id": "019571a3-0000-7000-8000-000000000001",
  "name": "Hero Images",
  "description": "Primary hero assets for all campaigns",
  "collectionId": "019571a2-3f10-7b2a-8c4d-1a2b3c4d5e6f",
  "parentFolderId": null,
  "occurredAt": "2026-05-22T10:01:00Z"
}
```

Capture the root `folderId` (`id` field) — you'll use it in Step 3 and Steps 6.

**Key errors:**
- `404` — `collectionId` not found
- `409` — folder name already exists at root of this collection

---

## Step 3 — Create a Sub-Folder

A sub-folder uses the same endpoint — the only difference is setting `parentFolderId`.

**Endpoint:** `POST /v1/catalog/collections/{collectionId}/folders`

**Description:** Creates a child folder nested under an existing folder. Folder nesting is capped at depth 10. Concurrent structural changes require an `expectedVersion` on mutations (rename, move, archive) but **not** on creation.

**Request:**
```http
POST /v1/catalog/collections/019571a2-3f10-7b2a-8c4d-1a2b3c4d5e6f/folders
```
```json
{
  "name": "Q1 Approved",
  "description": "Approved hero images for Q1",
  "parentFolderId": "019571a3-0000-7000-8000-000000000001"
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `name` | string | ✅ | Unique within the parent folder |
| `parentFolderId` | string | ✅ | The `folderId` of the parent — must exist in the same collection |
| `description` | string | ❌ | Optional |

**Response `201 Created`:**
```json
{
  "id": "019571a3-0000-7000-8000-000000000002",
  "name": "Q1 Approved",
  "description": "Approved hero images for Q1",
  "collectionId": "019571a2-3f10-7b2a-8c4d-1a2b3c4d5e6f",
  "parentFolderId": "019571a3-0000-7000-8000-000000000001",
  "occurredAt": "2026-05-22T10:02:00Z"
}
```

**Key errors:**
- `404` — `collectionId` or `parentFolderId` not found
- `409` — depth > 10
- `422` — `parentFolderId` belongs to a different collection (cross-collection move not permitted)

---

## Step 4 — Upload an Asset and Confirm It's Uploaded

Asset upload is a **three-step process**: initiate → PUT to S3 → confirm. No polling required before assignment — an asset can be assigned to a role at any status.

> **Status and download:** Asset status only gates **download** (presigned GET URL issuance). Only `Active` and `Archived` assets can be downloaded. All other statuses (`Pending`, `Validating`, `Processing`, etc.) can be assigned to roles freely.

### Step 4a — Initiate Upload

**Endpoint:** `POST /v1/assets/uploads`

**Description:** Registers the asset in the system and issues a pre-signed S3 PUT URL. The asset starts in `Pending` status. You must PUT the file binary directly to the returned URL — there is no Lambda proxy.

> For files ≥ 100 MB use the multipart flow (`POST /v1/assets/multipart-uploads`) instead.

**Request:**
```json
{
  "fileName": "hero-banner-q1.jpg",
  "mediaContentType": "Image",
  "contentLength": 2048576
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `fileName` | string | ✅ | Original filename including extension |
| `mediaContentType` | enum | ✅ | `"Image"`, `"Video"`, `"Audio"`, `"Document"` |
| `contentLength` | long | ✅ | File size in bytes |
| `itemId` | string | ❌ | Optional — associate with a MediaItem at upload time, or assign via role later |

**Response `202 Accepted`:**
```json
{
  "id": "019571b0-0000-7000-8000-000000000001",
  "uploadUrl": "https://media-source.s3.amazonaws.com/tenants/xxx/assets/019571b0-...?X-Amz-Signature=...",
  "expiresAt": "2026-05-22T10:17:00Z"
}
```

The pre-signed URL expires in **15 minutes**. Capture `assetId`.

**Key errors:**
- `413` — storage quota exceeded
- `400` — unsupported `mediaContentType` or filename invalid

---

### Step 4b — PUT the Binary to S3

Send the file bytes directly to the `uploadUrl`. This is a standard HTTP PUT — no auth header, no JSON.

**Request:**
```http
PUT https://media-source.s3.amazonaws.com/tenants/xxx/assets/019571b0-...?X-Amz-Signature=...
Content-Type: image/jpeg
Content-Length: 2048576

<binary file bytes>
```

**Response `200 OK`** — S3 returns an `ETag` header. You do not need the ETag for single-part uploads.

---

### Step 4c — Confirm the Upload

**Endpoint:** `POST /v1/assets/{assetId}/uploads/confirm`

**Description:** Signals to the system that the S3 PUT completed. Transitions the asset `Pending → Validating`. The validation pipeline (virus scan + metadata extraction + processing) then runs asynchronously. This endpoint is idempotent — the Ingest Lambda also calls it automatically on the S3 event, so calling it manually is a belt-and-suspenders confirmation.

**Request:**
```http
POST /v1/assets/019571b0-0000-7000-8000-000000000001/uploads/confirm
```
_(No request body)_

**Response `202 Created`**

**Key errors:**
- `404` — asset not found
- `409` — asset is not in `Pending` status (already confirmed or terminal)

After confirm, the validation and processing pipeline runs asynchronously (`Pending → Validating → Processing → Active`). **You do not need to wait for `Active` before proceeding** — role assignment in Step 6b works at any status. Poll `GET /v1/assets/{assetId}` only if you need to confirm the asset is downloadable or check for pipeline failures.

---

## Step 5 — Resolve a Media Profile

A MediaProfile defines the asset roles and capabilities a MediaItem must conform to. Every tenant is pre-seeded with five platform default profiles — **use one of these before reaching for a custom profile**.

### Platform Default Profiles

| Name | Primary role accepts | Extra roles | Capabilities |
|---|---|---|---|
| `Simple Image` | `Image` | — | Processing, VersionControl |
| `Simple Video` | `Video` | `thumbnail` (Image, optional) | Processing, VersionControl |
| `Simple Audio` | `Audio` | `artwork` (Image, optional) | Processing, VersionControl |
| `Document` | `Document` | — | VersionControl only (no renditions) |
| `Governed Media Record` | `Image`, `Video`, or `Audio` | `supporting-document` (Document, optional, multi) | Processing, VersionControl, Review, CheckInOut, Registration |

All five are `Published` at tenant provisioning time and are immediately assignable to MediaItems.

---

### Step 5a — Look Up a Default Profile by Name

**Endpoint:** `GET /v1/catalog/profiles`

**Description:** Returns a paginated list of all media profiles for the tenant, ordered by name. Pass the optional `name` query parameter for an **exact, case-insensitive match** — this is the fast path for resolving a known default profile to its `mediaProfileId`.

**Request:**
```http
GET /v1/catalog/profiles?name=Simple+Image
```

| Parameter | Location | Required | Notes |
|---|---|---|---|
| `name` | query string | ❌ | Exact name match (case-insensitive); omit to page all profiles |
| `page` | query string | ❌ | Page number, default `1` |
| `pageSize` | query string | ❌ | Items per page, default `20` |

**Response `200 OK`:**
```json
{
  "mediaProfiles": [
    {
      "id": "019571c0-0000-7000-8000-000000000001",
      "name": "Simple Image",
      "description": "Single image asset. Renditions and EXIF metadata extracted on upload.",
      "status": "Published"
    }
  ],
  "pageNumber": 1,
  "pageSize": 20,
  "totalCount": 1
}
```

Capture the `mediaProfileId` from the matching entry. If `mediaProfiles` is empty the name didn't match — check spelling against the table above (names are exact).

> **Skip Steps 5b–5d** if you're using a default profile. The profile is already `Published` — go straight to Step 5.5 or Step 6a with the resolved `mediaProfileId`.

**Key errors:**
- `401` / `403` — auth/permission failure

---

### Step 5b — Create a Custom Profile

> Only needed if none of the platform defaults fits your use case.

**Endpoint:** `POST /v1/catalog/profiles`

**Description:** Creates the profile and automatically opens an initial draft. The server generates and returns the `mediaProfileId`. The profile is in `Draft` state and cannot be assigned to MediaItems until published.

**Request:**
```json
{
  "name": "Campaign Image Profile",
  "description": "Profile for Q1 campaign hero images"
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `name` | string | ✅ | Must be unique within tenant |
| `description` | string | ❌ | Optional |

**Response `201 Created`:**
```json
{
  "id": "019571c0-0000-7000-8000-000000000001",
  "occurredAt": "2026-05-22T10:04:00Z"
}
```

Capture `mediaProfileId`.

**Key errors:**
- `409` — profile name already exists for this owner

---

### Step 5c — Add an Asset Definition (the Primary Role)

**Endpoint:** `POST /v1/catalog/profiles/{profileId}/asset-definitions`

**Description:** Adds a named asset role to the open draft. Each role defines what content types are accepted, whether it's required, and size/dimension constraints. The profile's draft was opened automatically at creation — you do **not** need to call `POST /draft` first for a brand-new profile.

> The `roleName` you define here is the value you'll use when assigning an asset in Step 6b.

**Request:**
```http
POST /v1/catalog/profiles/019571c0-0000-7000-8000-000000000001/asset-definitions
```
```json
{
  "roleName": "primary",
  "displayName": "Primary Image",
  "acceptedContentTypes": ["Image"],
  "isRequired": true,
  "allowMultiple": false,
  "maxFileSizeBytes": 52428800,
  "displayOrder": 1
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `roleName` | string | ✅ | Unique within this profile; used when assigning assets |
| `displayName` | string | ✅ | Human-readable label |
| `acceptedContentTypes` | array | ✅ | One or more of: `"Image"`, `"Video"`, `"Audio"`, `"Document"` |
| `isRequired` | bool | ✅ | Whether a MediaItem must have this role filled before submission |
| `allowMultiple` | bool | ✅ | Whether multiple assets can occupy this role |
| `maxFileSizeBytes` | long | ❌ | Optional size cap; platform default applies if omitted |
| `displayOrder` | int | ✅ | Render order in UI |
| `dimensionConstraints` | object | ❌ | Optional — `minWidth`, `maxWidth`, `minHeight`, `maxHeight`, etc. |
| `preferredStorageTier` | enum | ❌ | `"Standard"` (default) or `"Archive"` |

**Response `204 No Content`**

**Key errors:**
- `409` — no active draft (shouldn't occur on a freshly-created profile)
- `409` — `roleName` already exists on the draft

---

### Step 5d — Publish the Custom Profile

**Endpoint:** `POST /v1/catalog/profiles/{profileId}/publish`

**Description:** Promotes the current draft to the live published version (version 1). After this call the profile status becomes `Published` and can be assigned to MediaItems. The draft must contain at least one asset definition.

**Request:**
```http
POST /v1/catalog/profiles/019571c0-0000-7000-8000-000000000001/publish
```
_(No request body)_

**Response `200 OK`:**
```json
{
  "newVersion": 1
}
```

**Key errors:**
- `409` — no draft to publish
- `422` — draft is empty (no asset definitions or record types)

---

## Step 5.5 — Find a Folder by Name

If you don't already have the target `folderId` in hand, use the folder hierarchy endpoint to locate it by name before calling Step 6a.

**Endpoint:** `GET /v1/catalog/collections/{collectionId}/folders/hierarchy`

**Description:** Returns all folders in the collection as a flat list. Each node includes `parentFolderId` so clients can assemble the tree client-side. The optional `nameContains` query parameter applies a **case-insensitive substring filter** server-side (in-memory, after the DynamoDB fetch) — it is not a DynamoDB-level predicate.

> Use this step any time you know a folder name but not its ID — for example, when integrating with an external system that stores folder names rather than IDs.

**Request:**
```http
GET /v1/catalog/collections/019571a2-3f10-7b2a-8c4d-1a2b3c4d5e6f/folders/hierarchy?nameContains=Q1+Approved
```

| Parameter | Location | Required | Notes |
|---|---|---|---|
| `collectionId` | route | ✅ | The collection to search within |
| `nameContains` | query string | ❌ | Case-insensitive substring match on folder `name`; omit to return all folders |

**Response `200 OK`:**
```json
{
  "folders": [
    {
      "id": "019571a3-0000-7000-8000-000000000002",
      "parentFolderId": "019571a3-0000-7000-8000-000000000001",
      "name": "Q1 Approved",
      "isArchived": false
    }
  ]
}
```

The response is a **flat list** — nodes are not pre-nested. If `nameContains` matches multiple folders (e.g. "Q1" hits several), inspect `parentFolderId` to disambiguate. Archived folders (`isArchived: true`) are included in results — filter them out if you only want active targets.

Capture the `folderId` of your target node and use it as the route segment in Step 6a.

**Key errors:**
- `400` — `collectionId` is not a valid UUID
- `401` / `403` — auth/permission failure

---

## Step 6 — Create the MediaItem in a Folder, then Assign the Asset

### Step 6a — Create MediaItem in the Folder

**Endpoint:** `POST /v1/catalog/folders/{folderId}/items`

**Description:** Creates a MediaItem pre-assigned to the specified folder, bound to the given MediaProfile. The item starts in `Draft` status. The profile must be `Published`. The server generates and returns the `mediaItemId`.

> Use the sub-folder ID from Step 3 (`019571a3-...-000000000002`) if you want it nested, or the root folder ID from Step 2 for a top-level placement.

**Request:**
```http
POST /v1/catalog/folders/019571a3-0000-7000-8000-000000000002/items
```
```json
{
  "title": "Q1 Hero Banner — Approved",
  "description": "Final approved hero for Q1 campaign homepage",
  "profileId": "019571c0-0000-7000-8000-000000000001"
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `title` | string | ✅ | Must be unique within the folder |
| `profileId` | string | ✅ | Must reference a `Published` MediaProfile |
| `description` | string | ❌ | Optional |

> `folderId` is the **route segment** — not in the body.

**Response `201 Created`:**
```json
{
  "id": "019571d0-0000-7000-8000-000000000001",
  "title": "Q1 Hero Banner — Approved",
  "createdAt": "2026-05-22T10:06:00Z"
}
```

Capture `mediaItemId`.

**Key errors:**
- `404` — folder or media profile not found
- `400` — profile not in `Published` status

---

### Step 6b — Assign the Asset to the Primary Role

**Endpoint:** `POST /v1/catalog/items/{itemId}/roles/{roleName}/assets`

**Description:** Assigns an asset to the named role on the MediaItem. **No status constraint** — the asset can be in any status at time of assignment. The `roleName` must match a role defined in the MediaItem's MediaProfile. This also raises `AssetAttachedToMediaItem` on the Asset side, permanently binding `Asset.MediaItemId` — the asset can only be assigned to one MediaItem.

**Request:**
```http
POST /v1/catalog/items/019571d0-0000-7000-8000-000000000001/roles/primary/assets
```
```json
{
  "assetId": "019571b0-0000-7000-8000-000000000001"
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `assetId` | string | ✅ | Must exist and be owned by the same tenant; any status permitted |

> `itemId` and `roleName` are **route segments**.

**Response `204 No Content`**

**Key errors:**
- `404` — MediaItem, asset, or role not found (role name doesn't match any definition in the profile)
- `409` — role already has an asset assigned and `allowMultiple = false` (unassign first with `DELETE .../roles/{roleName}/assets/{assetId}`)
- `422` — asset content type not accepted by the role definition

---

## Full Sequence Summary

```
1.  POST /v1/catalog/collections
    → collectionId

2.  POST /v1/catalog/collections/{collectionId}/folders          (parentFolderId: null)
    → rootFolderId

3.  POST /v1/catalog/collections/{collectionId}/folders          (parentFolderId: rootFolderId)
    → subFolderId

4a. POST /v1/assets/uploads
    → assetId + uploadUrl

4b. PUT  {uploadUrl}                                             (binary, direct to S3)
    → 200 OK

4c. POST /v1/assets/{assetId}/uploads/confirm
    → 202 No Content                                             (pipeline runs async; no poll required before assignment)

5a. GET  /v1/catalog/profiles?name=Simple+Image                  ← preferred: resolve a default profile
    → mediaProfileId (skip 5b–5d if using a default)

--- OR (custom profile) ---

5b. POST /v1/catalog/profiles
    → mediaProfileId

5c. POST /v1/catalog/profiles/{mediaProfileId}/asset-definitions
    → 204 No Content

5d. POST /v1/catalog/profiles/{mediaProfileId}/publish
    → 200 OK { newVersion: 1 }

5.5 GET  /v1/catalog/collections/{collectionId}/folders/hierarchy?nameContains=<name>
    → flat list of FolderHierarchyNodeModel { folderId, parentFolderId, name, isArchived }
    (optional — use when you need to resolve a folder name to a folderId before Step 6a)

6a. POST /v1/catalog/folders/{subFolderId}/items
    → mediaItemId

6b. POST /v1/catalog/items/{mediaItemId}/roles/primary/assets
    → 204 No Content
```

---
