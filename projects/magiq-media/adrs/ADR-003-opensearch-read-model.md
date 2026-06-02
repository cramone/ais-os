# ADR-003: OpenSearch for Asset Search Read Model

**Status:** Accepted
**Date:** 2026-03-10 (updated 2026-03-11)
**Deciders:** Chase Ramone

---

## Context

The Query API needs to support:
- Full-text search across file names, tags, and metadata
- Faceted filtering by content type, status, and date range
- Tag-based queries (multi-tag AND/OR)
- Owner-scoped queries with pagination

DynamoDB can serve the list and detail read models efficiently, but its query capability is unsuitable for multi-attribute filtering and full-text search. Options for search:

1. **OpenSearch** (AWS managed)
2. **DynamoDB PartiQL + GSIs** (no additional service)
3. **Typesense** (self-managed)
4. **Meilisearch** (self-managed)

---

## Decision

Use **AWS OpenSearch Service** for the search read model. DynamoDB remains for structured list/detail models. Two indexes:

- **`media-items`** — primary search surface for catalogued media items
- **`media-registrations`** — registration authority faceting and status filtering

The `MediaItemProjector` Lambda maintains the `media-items` index. The `RegistrationProjector` Lambda maintains the `media-registrations` index. All writes to OpenSearch are from these projectors only.

**Index mapping — `media-items` (abbreviated):**
```json
{
  "mappings": {
    "properties": {
      "mediaItemId":    { "type": "keyword" },
      "collectionId":   { "type": "keyword" },
      "folderId":       { "type": "keyword" },
      "ownerId":        { "type": "keyword" },
      "title":          { "type": "text", "analyzer": "standard" },
      "status":         { "type": "keyword" },
      "isAccessible":   { "type": "boolean" },
      "mediaProfileId": { "type": "keyword" },
      "tags":           { "type": "keyword" },
      "metadata":       { "type": "object",
                          "note": "Only fields where FieldDefinition.IsSearchable = true are indexed. Mapping per FieldType: Text → text (analyzed), Number → double, Date → date, Boolean → boolean, Url → keyword, Enum/MultiEnum → keyword[]" },
      "createdAt":      { "type": "date" },
      "publishedAt":    { "type": "date" }
    }
  }
}
```

**Index mapping — `media-registrations` (abbreviated):**
```json
{
  "mappings": {
    "properties": {
      "registrationId":        { "type": "keyword" },
      "mediaItemId":           { "type": "keyword" },
      "ownerId":               { "type": "keyword" },
      "registrationType":      { "type": "keyword" },
      "registrationAuthority": { "type": "keyword" },
      "status":                { "type": "keyword" },
      "submittedAt":           { "type": "date" },
      "confirmedAt":           { "type": "date" }
    }
  }
}
```

**Access pattern:** Query API queries OpenSearch directly over HTTPS using the AWS SDK (SigV4 signing). Results are `mediaItemId` / `registrationId` lists, then hydrated from DynamoDB `media-item-detail` / `media-registrations` if full detail is needed.

---

## Consequences

**Positive:**
- First-class full-text and faceted search without DynamoDB GSI limitations
- Managed by AWS — no cluster ops; automatic scaling via UltraWarm for older data
- Index rebuilds are possible: replay relevant domain events (`MediaItemApproved`, `MediaItemTagged`, `MediaItemMetadataFieldSet`, `RegistrationConfirmed`, etc.) through the projectors
- Fine-grained auth via IAM + OpenSearch resource policies; no credentials in application code

**Negative / Accepted trade-offs:**
- Additional service cost (OpenSearch domain vs. DynamoDB-only)
- OpenSearch is eventually consistent with the event store — acceptable; search is a discovery feature, not a transactional one
- Index schema changes require coordinated reindex. Mitigated by maintaining `schemaVersion` in the index and using index aliases (`media-assets-v1` → alias `media-assets`)
- Cold start on Lambda → OpenSearch connection: HTTPS/SigV4 overhead; acceptable at Lambda concurrency levels

**Not chosen — DynamoDB PartiQL + GSIs:**
- Tag multi-value queries require a ListContains filter scan — not efficient at scale
- Full-text search is not supported
- Adding more GSIs for every filter combination is not scalable

**Not chosen — Typesense / Meilisearch:**
- Self-managed; ECS/EC2 operational burden
- No native SigV4 / IAM integration
- Not justified when AWS OpenSearch is available

---

## Review Trigger

Revisit if: OpenSearch domain cost exceeds acceptable threshold at low query volume (consider OpenSearch Serverless), or if search requirements expand to semantic/vector search (OpenSearch supports k-NN — upgrade path is available within the same service).
