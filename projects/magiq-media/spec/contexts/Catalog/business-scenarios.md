# Catalog — Business Scenarios

_Context: `Catalog`_

> **Scenarios now live under each aggregate.** This file is an index only.

---

## Scenario Index

| # | Scenario | Key Aggregates | File |
|---|---|---|---|
| C-1 | Set Up a Collection Structure | Collection, Folder | [collection.scenarios.md](aggregates/Collection/collection.scenarios.md) |
| C-2 | Publish a MediaItem (No Review Policy) | MediaItem | [mediaitem.scenarios.md](aggregates/MediaItem/mediaitem.scenarios.md) |
| C-3 | Archive a Collection | Collection, MediaItem | [collection.scenarios.md](aggregates/Collection/collection.scenarios.md) |
| C-4 | Edit Lock (No Signing) | MediaItem | [mediaitem.scenarios.md](aggregates/MediaItem/mediaitem.scenarios.md) |
| C-5 | Cross-Collection MediaItem Move | MediaItem, Folder | [mediaitem.scenarios.md](aggregates/MediaItem/mediaitem.scenarios.md) |
| C-6 | Checkout Conflict (Concurrent Edit Attempt) | MediaItem | [mediaitem.scenarios.md](aggregates/MediaItem/mediaitem.scenarios.md) |
| C-7 | CR-First Checkout — Solo (No Review Required) | MediaItem | [mediaitem.scenarios.md](aggregates/MediaItem/mediaitem.scenarios.md) |
| C-8 | CR-First Checkout — With Change Request | MediaItem, MediaChangeRequest | [mediaitem.scenarios.md](aggregates/MediaItem/mediaitem.scenarios.md) |
| C-9 | CR-First Checkout — ForceRelease Auto-Abandons CR | MediaItem, MediaChangeRequest | [mediaitem.scenarios.md](aggregates/MediaItem/mediaitem.scenarios.md) |
| C-10 | CR-First Checkout — Profile Requires CR (Rejected at Checkout) | MediaItem | [mediaitem.scenarios.md](aggregates/MediaItem/mediaitem.scenarios.md) |
| MW-1 | MediaItem Withdrawal | MediaItem | [mediaitem.scenarios.md](aggregates/MediaItem/mediaitem.scenarios.md) |
| MW-2 | MediaItem Direct Archive (Individual) | MediaItem | [mediaitem.scenarios.md](aggregates/MediaItem/mediaitem.scenarios.md) |
| MW-3 | First Folder Assignment from Unassigned Pool | MediaItem, Folder | [mediaitem.scenarios.md](aggregates/MediaItem/mediaitem.scenarios.md) |
| MW-4 | User-Initiated Checkout Abandon | MediaItem | [mediaitem.scenarios.md](aggregates/MediaItem/mediaitem.scenarios.md) |
| MW-6 | Metadata Validation Failure at Publish | MediaItem | [mediaitem.scenarios.md](aggregates/MediaItem/mediaitem.scenarios.md) |
| MW-7 | Browse Unassigned Pool | MediaItem | [mediaitem.scenarios.md](aggregates/MediaItem/mediaitem.scenarios.md) |
| MW-8 | Checkout of Archived MediaItem (Rejected) | MediaItem | [mediaitem.scenarios.md](aggregates/MediaItem/mediaitem.scenarios.md) |
| BULK-2 | Bulk Metadata Update Across MediaItems | MediaItem | [mediaitem.scenarios.md](aggregates/MediaItem/mediaitem.scenarios.md) |
| MP-1 | Create and Publish a MediaProfile | MediaProfile | [mediaprofile.scenarios.md](aggregates/MediaProfile/mediaprofile.scenarios.md) |
| MP-2 | Re-pin a MediaProfile to a New RecordType Version | MediaProfile | [mediaprofile.scenarios.md](aggregates/MediaProfile/mediaprofile.scenarios.md) |
| MP-3 | Deprecate a MediaProfile | MediaProfile | [mediaprofile.scenarios.md](aggregates/MediaProfile/mediaprofile.scenarios.md) |
| MI-1 | Simple Version Increment with Asset Pipeline | MediaItem, Asset (cross-context) | [mediaitem.scenarios.md](aggregates/MediaItem/mediaitem.scenarios.md) |
| MI-2 | Change Request Rejection then Approval | MediaItem, Asset, MediaChangeRequest (cross-context) | [mediaitem.scenarios.md](aggregates/MediaItem/mediaitem.scenarios.md) |

**Cross-context scenarios** involving Catalog aggregates:
- Review-Gated Publish Workflow → see [ChangeRequests context](../../ChangeRequests/business-scenarios.md)
- Contract Signing Workflow → see [DocumentSigning context](../../DocumentSigning/business-scenarios.md)
- Upload and Process a Media Asset → see [AssetManagement context](../../AssetManagement/business-scenarios.md)
- Authorization Rejection Scenarios (PERM-1, PERM-2, PERM-3) → see [Shared Security Scenarios](../../../shared/security-scenarios.md)

---

## Related

- [Collection Scenarios](aggregates/Collection/collection.scenarios.md)
- [MediaItem Scenarios](aggregates/MediaItem/mediaitem.scenarios.md)
- [MediaProfile Scenarios](aggregates/MediaProfile/mediaprofile.scenarios.md)
- [Catalog Context Overview](context-overview.md)

<!-- Scenario bodies removed — see aggregate scenario files above -->
