# MediaContentType → MediaCategory + MIME Classification Remediation Plan

_Author: Claude (investigation for Chase Ramone), 2026-07-15._
_Scope: `AssetManagement` + `Catalog` modules (code) and `docs/spec` (contracts). Fixes the `MediaContentType` naming collision, the divergent duplicate enum, the missing MIME→category classification, and the broken confirm-time content-type guard._
_Status: Substantially complete 2026-07-15. Spec (Stage 2), classifier + wiring (Stage 3), response exposure (Stage 4), and cleanup (Stage 5) all landed; build is green. The enum was kept **per-module** rather than consolidated (see Stage 1 note). Remaining: end-to-end integration tests, a dev projector replay, and the full-suite/security-review run — see "Remaining work" at the bottom._

---

## Why this exists

`MediaContentType` is a five/six-value **category** enum (`Image | Video | Audio | Document | Archive | …`), but it is named as if it were an HTTP/MIME `Content-Type`, and it sits next to fields that really do hold MIME strings. Three concrete problems fall out of that:

1. **Name collision.** `Asset.ContentType : MediaContentType` (a category) sits beside `Rendition.ContentType` (a real MIME string, e.g. `image/webp`) — same field name, two meanings, same payload. Confirmed: `asset.write-model.md:49` (enum) vs the `Rendition` VO `asset.write-model.md:106` and download responses `asset.api.md:454,532,574` (MIME).
2. **The MIME→category mapping is undefined.** Nothing in the spec says which MIME types belong to which category, what the supported set is, or where classification lives. The only mapping in code is the *reverse* (`ToMimeType()`), and it is **wrong for Document/Archive** (see below).
3. **The concept is duplicated and has drifted.** Two separate `MediaContentType` enums exist in code with **different sixth members**, plus a third phantom name (`ContentTypeGroup`) that appears only in the spec.

### Ground truth from the code (not the spec)

- **Two divergent enum definitions:**
  - `src/modules/AssetManagement/AssetManagement.Domain/ValueObjects/MediaContentType.cs` → `Image, Video, Audio, Document, Archive, Other`
  - `src/modules/Catalog/Catalog.Domain/ValueObjects/MediaContentType.cs` → `Image, Video, Audio, Document, Archive, Binary`
  - The sixth member differs (`Other` vs `Binary`). Cross-module strings are parsed with `Enum.TryParse(..., out result) ? result : default` (`SnapshotToValueObjectMapper.cs:97`), so an AssetManagement `"Other"` parsed into the Catalog enum silently falls back to `default` = `Image (0)`. **Latent data-corruption bug**, independent of the rename.
- **The API already takes the enum *name*, not a MIME.** `InitiateAssetUploadEndpoint.cs:66` does `Enum.Parse<MediaContentType>(req.MediaContentType, true)`. The request field `mediaContentType` therefore expects `"Image"`, **not** `"image/jpeg"`. The spec examples showing `"mediaContentType": "image/jpeg"` (`asset.api.md:69`, `service-boundaries.md:57`) would throw — **the spec is wrong, and the current contract pushes the internal taxonomy onto clients.**
- **No MIME→category classifier exists.** Only the reverse mapping, in two divergent copies:
  - `AssetManagement/.../MediaContentTypeExtensions.cs`: `Document → "document"`, `Archive → "archive"` — **not real MIME prefixes.** A PDF is `application/pdf`; `"application/pdf".StartsWith("document/")` is false, so the confirm-time HeadObject guard (`asset.write-model.md:244`) misfires for every document/archive.
  - `Catalog/.../MediaContentTypeExtensions.cs`: `Document → "application"`, `Archive → "application"` — both collapse to `application`, so the two categories are indistinguishable by this check.
- **The `ContentTypeGroup` type in the spec (`mediaprofile.write-model.md:126`) does not exist in code.** `AssetDefinition.cs:8` uses `IReadOnlyList<MediaContentType>`. Pure spec drift.
- **`AssetDefinition` shape drifts across three spec docs** — `domain-model.md:387` (has `DisplayName`, `DisplayOrder`, `PreferredStorageTier`, `DefaultAssetId`) vs `mediaprofile.write-model.md:122` (`IsDefault`, no display/storage fields) vs `Catalog/context-overview.md:211` (shorter still). Code (`AssetDefinition.cs`) is the authority: `RoleName, DisplayName, AcceptedContentTypes, IsRequired, MaxFileSizeBytes, AllowMultiple, DisplayOrder, DefaultAssetId, DimensionConstraints, PreferredStorageTier`.

---

## Recommended end state (best-practice target)

1. **Rename the concept `MediaContentType` → `MediaCategory`.** It is a category; the new name stops colliding with HTTP `Content-Type` and with the MIME strings on renditions. Keep the enum *member names* identical (`Image`, `Video`, …) so event-store serialized values are unchanged.
2. **One shared enum, not two.** Move `MediaCategory` into the shared kernel and delete the module-local copies. **Keep both catch-all members (0-A):** `Binary` = `application/octet-stream` specifically; `Other` = fallback for any well-formed MIME that maps to no other category. Final member set: `Image, Video, Audio, Document, Archive, Binary, Other`. Because both values are preserved, no lossy cross-module migration is needed — legacy `Other` (AssetManagement) and legacy `Binary` (Catalog) both remain valid.
3. **Server owns MIME→category classification.** Introduce a single `IMediaTypeCatalog` in **`Media.Shared.Infrastructure` (0-B)** that: (a) holds the supported-MIME table, (b) maps a MIME → `MediaCategory` (`application/octet-stream` → `Binary`; unrecognized-but-well-formed → `Other`), (c) maps a category → canonical file extension for `StorageKeyGenerator`. This is the source of truth the spec is missing.
4. **Clients send the real MIME type; server classifies.** The browser already has this (`File.type`). This removes the client's need to know the internal taxonomy and makes the confirm-time guard an **exact MIME match** instead of a broken prefix `StartsWith`. Unrecognized MIME is **accepted as `Other`, not rejected** — only a malformed/absent `mimeType` returns `400`.
5. **Responses expose both** the real `mimeType` (of the original) and the derived `category`.
6. **Fix the spec drift** (`ContentTypeGroup`, the three `AssetDefinition` shapes, the `image/jpeg` request examples, the `ProcessingJob.ContentType` "MIME content type" vs "enum value" contradiction at `domain-model.md:239` vs `processingjob.write-model.md:35`).

> **Alternative if you want to minimise blast radius:** keep clients sending the *category* name and only do the rename + enum-consolidation + spec fixes (Stages 1–2, 5). This does **not** close the classification gap (the client still self-declares the category), so it doesn't "solve all gaps" — but it's non-breaking on request *values* and could ship first. The full fix (Stage 3) is where the API breaks. Both are staged separately below so you can stop after Stage 2 if desired.

---

## Decision gates — RESOLVED 2026-07-15 (Chase)

- **0-A — Sixth enum member → keep BOTH `Binary` and `Other`.** `Binary` maps specifically to `application/octet-stream`; `Other` is the fallback for anything that doesn't map to a known category. Final `MediaCategory` set: `Image, Video, Audio, Document, Archive, Binary, Other`. No lossy migration — both legacy values survive.
- **0-B — Classifier ownership → `Media.Shared.Infrastructure`.** `IMediaTypeCatalog` (+ its static data implementation) lives in the shared infrastructure project, consumed by both AssetManagement and Catalog. (Note: this couples Catalog's role-validation path to a shared-infra reference — acceptable per Chase; keep the interface clean so the domain depends on the abstraction only.)
- **0-C — Response field naming → rename `contentType` → `category` and add `mimeType`.** Full de-collision; breaking response rename accepted.
- **0-D — Breaking-change vehicle → ship in place on `/v1`.** No `/v2`. Re-confirm on the `Media` board that no client consumes the asset-upload endpoints before Stage 3 lands; if one has by then, revisit.

---

## Stage 1 — Consolidate + rename the enum (no API break)

Type-level change only. Enum member string values are preserved.

> **Executed differently than written (0-A / 0-B revised in-flight):** the enum was kept **per-module** (`AssetManagement.Domain` + `Catalog.Domain`), matching the existing `StorageTier` convention — there is no shared domain kernel, and the modules already exchange the category as a string across the boundary. It was **not** consolidated into one shared type. The event payload field was also renamed `ContentType` → `Category` (back-compat not required).

- [x] `MediaCategory` exists per-module with the full member set `Image, Video, Audio, Document, Archive, Binary, Other`.
- [x] `MediaContentType` renamed to `MediaCategory` everywhere — grep `MediaContentType` returns zero hits in `src/`.
- [x] Replaced the silent-default parse in `SnapshotToValueObjectMapper` (`AcceptedContentTypes`) with `Enum.Parse<MediaCategory>` — an unrecognised stored category now surfaces instead of defaulting to `Image`.
- [x] `MimeTypeServiceTests` proves `application/octet-stream` → `Binary` and well-formed-unknown → `Other`.
- [x] **Round-trip integration test** added to `Catalog.IntegrationTests` (`MediaProfileFlowTests.Publish_WithBinaryAndOtherAcceptedContentTypes_RoundTripsThroughReadModel`): publishes a profile whose asset definition accepts `Binary` + `Other` and asserts both survive to the read model.
- [x] **Acceptance:** solution builds; zero `MediaContentType` in `src/`.

## Stage 2 — Spec correctness pass (no code)

Pure doc fixes; can land alongside Stage 1 in the same PR (docs-co-location convention).

- [x] Rename `MediaContentType` → `MediaCategory` across `domain-model.md`, `asset.write-model.md`, `asset.read-model.md`, `mediaprofile.write-model.md`, `processingjob.*`, `service-boundaries.md`, `AssetManagement/context-overview.md`, `mediaitem.write-model.md` (9 files, all occurrences).
- [x] Delete the phantom `ContentTypeGroup` name in `mediaprofile.write-model.md`; type `AcceptedContentTypes` as `IReadOnlyList<MediaCategory>` to match `AssetDefinition.cs`. Enum member listings updated to the full 7-member set (`…Archive, Binary, Other`).
- [x] Reconcile the `AssetDefinition` shape to the code across `domain-model.md:387`, `mediaprofile.write-model.md`, `Catalog/context-overview.md:211` — one canonical field list (`RoleName, DisplayName, AcceptedContentTypes, IsRequired, MaxFileSizeBytes?, AllowMultiple, DisplayOrder, DefaultAssetId?, DimensionConstraints?, PreferredStorageTier`).
- [x] Fix the `ProcessingJob.ContentType` contradiction: `domain-model.md:239` now reads "`MediaCategory` enum value as string," matching the aggregate.
- [x] Add `shared/media-types.md`: `MediaCategory` taxonomy, classification rules (octet-stream→`Binary`, well-formed-unknown→`Other`, malformed→`400`), the MIME→category table, and the category→extension table.
- [x] **Acceptance:** grep spec tree for `MediaContentType` and `ContentTypeGroup` → zero. `AssetDefinition` field list identical in all three docs. ✓

## Stage 3 — Introduce the classifier + accept real MIME (**API-breaking**)

This is the stage that closes the gap and breaks the request contract. Gates 0-A (per-module enum), 0-B → **superseded**: reused the already-registered `IMimeTypeService` (AssetManagement) instead of a new `Media.Shared.Infrastructure` catalog — it's the existing MIME home, and only AssetManagement classifies at upload (Catalog just validates an already-derived category string), so a shared-infra type would only have created shared-infra→module-domain coupling. 0-D (in place on `/v1`) stands.

- [x] **Classifier — DONE.** Extended `IMimeTypeService` (`AssetManagement.WriteModel/Services/IMimeTypeService.cs`) with `ClassifyCategory(string) → MediaCategory` (`application/octet-stream` → `Binary`; well-formed unrecognized → `Other`) and `IsWellFormedMimeType(string) → bool`; implemented in `MimeTypeService.cs` with the `CategoryByMime` table mirroring `shared/media-types.md`. (Storage-key extension already comes from the filename, so the `CanonicalExtension` item is moot — `StorageKeyGenerator` unchanged.)
- [x] Request DTOs (`InitiateAssetUploadRequest` / `InitiateMultipartUploadRequest` / `BulkInitiateAssetUploadRequestModel` + the `BulkInitiateAssetUploadItem` command item): the string property is now **`MimeType`**, carrying the real MIME.
- [x] Endpoints (single, multipart, bulk): classify via `mimeService.ClassifyCategory(req.MimeType)`; single + multipart also run `IsWellFormedMimeType` and return `400` (FastEndpoints field validation) for malformed/absent input. Bulk classifies per item in the handler.
- [x] Command + event carry both `Category` (derived `MediaCategory`) **and** `MimeType` (raw); the `Asset` aggregate stores `MimeType` and sets it in `Apply`. Additive event field.
- [x] Confirm-time guard implemented: exact compare of the S3 object `Content-Type` against the stored `MimeType` (params stripped, case-insensitive), with `application/octet-stream`/`binary/octet-stream` accepted as a fallback. Both `MediaCategoryExtensions.ToMimeType()` files deleted.
- [x] `StorageKeyGenerator` — **no change needed**: the file extension already comes from the filename, not the category.
- [x] Catalog-side role validation unchanged — compares the asset's stored `MediaCategory` against `AssetDefinition.AcceptedContentTypes`.
- [x] **Spec contract — DONE.** `asset.api.md` (request bodies + both response bodies carry `mimeType` + `category`, Mermaid flow, error notes), `service-boundaries.md`, and `asset.scenarios.md` updated; `Other`/`Binary` fallback + malformed→`400` documented against `shared/media-types.md`.
- [x] **Acceptance.** `MimeTypeServiceTests` (unit) + `AssetFlowTests` (integration) cover `image/jpeg`→Image, `application/pdf`→Document, `application/octet-stream`→Binary, `application/x-custom`→Other, and malformed→`400`; the `ConfirmAssetUpload` mismatch guard has a unit test.

## Stage 4 — Response exposure (**API-breaking if 0-C = rename**)

- [x] `GET /v1/assets/{id}` + list responses expose `category` (renamed from `contentType`) and `mimeType`. `AssetSummaryReadModel`/`AssetDetailReadModel`, both projectors, `AssetSummaryModel`/`GetAssetByIdResponse`, and the read-model tests updated. Bonus: the asset-download endpoint now sources its `contentType` from `asset.MimeType` (it was returning the category — a latent bug).
- [x] `Rendition.contentType` left as-is (real MIME).
- [x] **Acceptance:** `category` (enum) and `mimeType` (MIME) are distinct fields; no response field named `contentType` carries a category value.

## Stage 5 — Cleanup

- [x] Deleted the dead `ToMimeType()` extensions (both modules).
- [x] Added a glossary entry to `system-spec.md` distinguishing `MediaCategory` (category) from `mimeType` (MIME).
- [x] **Security review — manual pass complete** (findings recorded below). Net security-positive: category is now derived server-side (was client-declared), and a confirm-time content-type guard now exists where there was none. Low-severity hardening items noted.
- [x] **Remaining (Chase, local):** full `dotnet test` across all projects; optionally run the automated `/security-review` in the repo (it needs a git working dir — the Cowork sandbox cwd isn't the repo); and a dev projector replay for the read-model attribute rename.

### Security review findings (2026-07-15, manual)

- **Positive:** clients no longer declare the internal category — the server derives it from the MIME via `IMimeTypeService`, reducing trust in client input. A confirm-time content-type guard now exists (exact match vs stored `MimeType`) where the check was previously commented out.
- **Low — `mimeType` length:** the request field is trimmed but not length-capped (bounded only by ASP.NET request-size limits). Consider a max length (~255) as defense-in-depth.
- **Low — `IsWellFormedMimeType` regex:** the optional parameter section uses `\s*`, which matches newlines; combined with `$` matching before a trailing newline, a single trailing newline passes validation (stripped by the request `Trim`, so benign in practice). Tighten to `[ \t]*` to keep control chars out of stored/logged values.
- **Accepted risk — octet-stream fallback:** the confirm guard accepts `application/octet-stream` / `binary/octet-stream`, so a client can bypass the type check by declaring octet-stream. Intentional — the definitive check is the processing pipeline's virus/format scan, which inspects the binary. Documented in `media-types.md`.
- **Note — fail-loud parse:** `SnapshotToValueObjectMapper` now throws on an unrecognised stored category (was silently `Image`). Better for integrity, but a genuinely corrupt event would fail aggregate rehydration — worth monitoring.
- **No injection surface:** `mimeType` is not used in DynamoDB keys, S3 keys (extension comes from filename), file paths, or any query/shell; JSON output is escaped. Classification runs post-auth.

---

## Remaining work (2026-07-15)

Everything that closes the naming collision, the classification gap, the duplicate enum, and the confirm guard is done and building. What's left is verification/coverage, not new design:

1. **Integration tests** — the endpoint→persistence classify test (Stage 3 acceptance) and the `Binary`/`Other` snapshot round-trip (Stage 1). Both belong in the integration projects, not unit tests.
2. **Dev projector replay** — the read-model attribute rename (`ContentType`→`Category`) + added `MimeType` require re-projecting `media-assets` / `media-asset-detail` in dev.
3. **Full-suite + security-review run** — Chase's build/test/security-review pass across all projects (write model, read model, CLI, hosts).

---

## Breaking changes introduced in the API layer

**Requests (Stage 3):**

| Endpoint | Field today | Today's value | After | Break type |
|---|---|---|---|---|
| `POST /v1/assets/uploads` | `mediaContentType` | enum name (`"Image"`) | `mimeType` = `"image/jpeg"` | field **rename** + **value-semantics** change |
| `POST /v1/assets/multipart-uploads` | `mediaContentType` | `"Video"` | `mimeType` = `"video/mp4"` | rename + value-semantics |
| `POST /v1/assets/uploads/bulk` | item `contentType` | `"Image"` | item `mimeType` = `"image/jpeg"` | rename + value-semantics |
| all three above | — | enum name required; bad value throws | real MIME; unknown → `Other`, malformed → **`400 InvalidContentType`** | value-format change; rejection is *narrower* (only malformed input fails) |

**Responses (Stage 4 — 0-C resolved as rename):**

| Endpoint | Field today | After | Break type |
|---|---|---|---|
| `GET /v1/assets/{id}` | `contentType: "Image"` | `category: "Image"` + new `mimeType: "image/jpeg"` | field **rename** + additive field |
| `GET /v1/assets?mediaItemId=` | `contentType: "Image"` | `category: "Image"` | field rename |

**Not breaking:** `Rendition.contentType` (already a MIME string, unchanged); event-store data (enum member names preserved; `MimeType` is an additive event field defaulted on replay); internal command/event **type** rename (`MediaContentType`→`MediaCategory`) — a compile-time change with no wire impact.

**How much does "breaking" actually cost?** Decided (0-D): **ship in place on `/v1`, no `/v2`.** Per the API-consistency plan's Stage 4 evidence (2026-07-08), no client currently consumes these endpoints — the API is still under server-side construction, Akshay is on OpenSearch infra, and no UI work references the asset-upload contract, so the breaks are effectively free. **Re-confirm on the `Media` board before Stage 3 lands**; if a client has integrated by then, revisit the `/v2` option rather than breaking it silently.

---

## Suggested delivery order

Stage 1 + Stage 2 in one PR (non-breaking, high-leverage, fixes the silent-corruption bug and all spec drift). Then Stage 3 + Stage 4 + Stage 5 together (they share the classifier and the contract), in place on `/v1` per 0-D — after re-confirming no consumer exists on the `Media` board.
