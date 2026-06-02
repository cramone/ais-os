# DocumentSigning — Business Scenarios

_Context: `DocumentSigning`_

> **Scenarios now live under each aggregate.** This file is an index only.

---

## Index

| # | Scenario | Key Aggregates | File |
|---|---|---|---|
| DS-1 | Happy Path — Contract Signed and Published | DocumentSigningSession, MediaItem | [documentsigningsession.scenarios.md](aggregates/DocumentSigningSession/documentsigningsession.scenarios.md) |
| DS-2 | Envelope Voided (Compensation Path) | DocumentSigningSession, MediaItem | [documentsigningsession.scenarios.md](aggregates/DocumentSigningSession/documentsigningsession.scenarios.md) |
| DS-3 | Stale Lock — Force Release via Signing Session Timeout | DocumentSigningSession, MediaItem | [documentsigningsession.scenarios.md](aggregates/DocumentSigningSession/documentsigningsession.scenarios.md) |

---

## Related

- [DocumentSigningSession Scenarios](aggregates/DocumentSigningSession/documentsigningsession.scenarios.md)
- [Catalog Business Scenarios](../Catalog/business-scenarios.md) — checkout flows
- [AssetManagement Business Scenarios](../AssetManagement/business-scenarios.md) — asset upload
- [System Spec — Saga Coordination](../../shared/system-spec.md#saga-coordination-patterns)

<!-- Scenario bodies removed — see aggregate scenario files above -->
