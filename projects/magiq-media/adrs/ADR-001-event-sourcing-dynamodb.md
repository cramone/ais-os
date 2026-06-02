# ADR-001: DynamoDB as Event Store

**Status:** Accepted
**Date:** 2026-03-10
**Deciders:** Chase Ramone

---

## Context

The Media Management system uses event sourcing as its write-side persistence strategy. We need to choose an event store implementation. Options evaluated:

1. **EventStoreDB** (managed or self-hosted)
2. **DynamoDB** (custom implementation)
3. **Aurora PostgreSQL** (append-only table)

Constraints:
- All infrastructure must be AWS-native to avoid operational overhead of a separate managed service
- Lambda-based compute cannot maintain persistent connections efficiently (rules out RDS connection pooling at scale)
- Team has existing DynamoDB expertise from other services

---

## Decision

Use **DynamoDB** as the event store with a custom append-only implementation.

**Table schema:**
```
PK: AggregateId       (string, e.g., "asset_018e4c7a-3f10-7b2a-8c4d-1a2b3c4d5e6f")
SK: AggregateVersion    (number, 0-based monotonic integer)
EventType: string
OccurredAt: ISO 8601
Payload: string (JSON)
SchemaVersion: number
```

**Optimistic concurrency:** Conditional expression `attribute_not_exists(AggregateVersion)` on each `PutItem`. If the condition fails, a `ConditionalCheckFailedException` is raised → translate to `ConcurrencyException` in the domain layer → command handler retries up to 3 times with exponential backoff.

**Event loading:** `Query` on PK with ascending SK order. No scan. All events for an aggregate are in a single partition.

---

## Consequences

**Positive:**
- No additional service to operate or pay for
- DynamoDB is already in our AWS account with IAM roles established
- Lambda cold starts are fast because DynamoDB uses HTTP/HTTPS (no connection warmup)
- Pay-per-request billing aligns with Lambda invocation patterns
- Point-in-time recovery gives us an event store backup strategy for free

**Negative / Accepted trade-offs:**
- No built-in subscription/streaming from DynamoDB (we use SQS for event fan-out instead of DynamoDB Streams — see ADR-002)
- Partition hot-spotting risk if a single aggregate receives very high write throughput. Mitigated: media upload is not a hot-write aggregate; one upload = a handful of events, spread across many partition keys
- No server-side projection or catch-up subscription (we implement projection rebuilds as full table scans on `media-events` with paginated Query per aggregate)
- Payload stored as JSON string, not binary — acceptable for event sizes we anticipate (< 4KB per event)

**Not chosen — EventStoreDB:**
- Excellent feature set but requires ECS or EC2, adding operational burden and a network hop from Lambda
- Persistent TCP connections from Lambda are expensive to manage correctly

**Not chosen — Aurora PostgreSQL:**
- RDS Proxy + Lambda connection limits are manageable but add complexity
- SQL DDL migrations add a deployment dependency not present with DynamoDB

---

## Review Trigger

Revisit if: any single aggregate accumulates > 10,000 events (rehydration latency), or if DynamoDB Streams lag causes unacceptable projection delay.
