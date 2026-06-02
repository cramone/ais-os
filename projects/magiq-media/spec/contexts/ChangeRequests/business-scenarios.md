# ChangeRequests — Business Scenarios

_Context: `ChangeRequests`_

> **Scenarios now live under each aggregate.** This file is an index only.

---

## Overview

`MediaChangeRequest` is a comment thread for a MediaItem review cycle. It has no lifecycle status and no reviewer roster. Review decisions (approve/reject) are made directly on `MediaItem` — see [MediaItem Business Scenarios](../Catalog/aggregates/MediaItem/mediaitem.scenarios.md).

---

## Index

| # | Scenario | Key Aggregates | File |
|---|---|---|---|
| CRC-1 | Create a Comment Thread for a Review | MediaChangeRequest, MediaItem | [mediachangerequest.scenarios.md](aggregates/MediaChangeRequest/mediachangerequest.scenarios.md) |
| CRC-2 | Add a Comment | MediaChangeRequest | [mediachangerequest.scenarios.md](aggregates/MediaChangeRequest/mediachangerequest.scenarios.md) |
| CRC-3 | Edit Own Comment | MediaChangeRequest | [mediachangerequest.scenarios.md](aggregates/MediaChangeRequest/mediachangerequest.scenarios.md) |
| CRC-4 | Delete Own Comment | MediaChangeRequest | [mediachangerequest.scenarios.md](aggregates/MediaChangeRequest/mediachangerequest.scenarios.md) |
| CRC-5 | Non-Author Cannot Edit Another User's Comment | MediaChangeRequest | [mediachangerequest.scenarios.md](aggregates/MediaChangeRequest/mediachangerequest.scenarios.md) |

---

## Related

- [MediaChangeRequest Scenarios](aggregates/MediaChangeRequest/mediachangerequest.scenarios.md)
- [Catalog Business Scenarios](../Catalog/business-scenarios.md) — MediaItem lifecycle
- [MediaItem Business Scenarios](../Catalog/aggregates/MediaItem/mediaitem.scenarios.md) — review approve/reject
