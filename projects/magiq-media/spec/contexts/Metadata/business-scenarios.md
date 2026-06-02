# Metadata — Business Scenarios

_Context: `Metadata`_

> **Scenarios now live under each aggregate.** This file is an index only.

---

## Index

| # | Scenario | Key Aggregates | File |
|---|---|---|---|
| M-1 | Create and Publish a RecordType Schema | RecordType | [recordtype.scenarios.md](aggregates/RecordType/recordtype.scenarios.md) |
| M-2 | Evolve a RecordType Field (Type Change) | RecordType | [recordtype.scenarios.md](aggregates/RecordType/recordtype.scenarios.md) |
| M-3 | Deprecate a RecordType | RecordType | [recordtype.scenarios.md](aggregates/RecordType/recordtype.scenarios.md) |
| M-4 | Bulk Metadata Update on a MediaItem (SetMetadataBatch) | MediaItem (cross-context) | [recordtype.scenarios.md](aggregates/RecordType/recordtype.scenarios.md) |

**Cross-context scenarios** involving RecordType and MediaProfile:
- Create and publish a MediaProfile (including attaching a RecordType) → see [Catalog Business Scenarios](../Catalog/business-scenarios.md)
- Re-pin a MediaProfile to a new RecordType version → see [Catalog Business Scenarios](../Catalog/business-scenarios.md)

---

## Related

- [RecordType Scenarios](aggregates/RecordType/recordtype.scenarios.md)
- [Catalog Business Scenarios](../Catalog/business-scenarios.md) — MediaProfile scenarios (create, publish, re-pin)

<!-- Scenario bodies removed — see aggregate scenario files above -->
