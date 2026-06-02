# AssetManagement — Business Scenarios

_Context: `AssetManagement`_

> **Scenarios now live under each aggregate.** This file is an index only.

---

## Scenario Index

| # | Scenario | Key Aggregates | File |
|---|---|---|---|
| A-1 | Upload and Process a Media Asset | Asset | [asset.scenarios.md](aggregates/Asset/asset.scenarios.md) |
| A-2 | Drag-and-Drop Upload (Standalone Asset Before MediaItem) | Asset | [asset.scenarios.md](aggregates/Asset/asset.scenarios.md) |
| A-3 | Processing Pipeline Failure Recovery | Asset, AssetIngestionSaga | [asset.scenarios.md](aggregates/Asset/asset.scenarios.md) |
| AM-4 | Large File Upload (Multipart) | Asset, AssetIngestionSaga | [asset.scenarios.md](aggregates/Asset/asset.scenarios.md) |
| AM-5 | Virus Scan Failure (Asset Infection Detected) | Asset, AssetIngestionSaga | [asset.scenarios.md](aggregates/Asset/asset.scenarios.md) |
| AM-6 | User-Initiated Asset Archive | Asset | [asset.scenarios.md](aggregates/Asset/asset.scenarios.md) |
| AM-7 | Asset Hard Delete | Asset | [asset.scenarios.md](aggregates/Asset/asset.scenarios.md) |
| DL-1 | Download Original Asset (Presigned URL) | Asset | [asset.scenarios.md](aggregates/Asset/asset.scenarios.md) |
| DL-2 | Download Asset Rendition (Presigned URL) | Asset | [asset.scenarios.md](aggregates/Asset/asset.scenarios.md) |
| DL-3 | Expired Download URL — Access Denied by S3 | Asset | [asset.scenarios.md](aggregates/Asset/asset.scenarios.md) |

---

## Related

- [Asset Scenarios](aggregates/Asset/asset.scenarios.md)
- [Processing Context — Business Scenarios](../Processing/business-scenarios.md)
- [System Spec — Saga Coordination](../../shared/system-spec.md#saga-coordination-patterns)

<!-- Scenario bodies removed — see aggregate scenario files above -->
