# ADR-002: SQS for Event Fan-Out (Not DynamoDB Streams)

**Status:** Accepted (amended 2026-04-17 — see ADR-005)
**Date:** 2026-03-10
**Deciders:** Chase Ramone

> **Amendment note (2026-04-17):** The `media-notifications` queue role described below has been superseded by ADR-005. `media-notifications` is renamed `media-cross-module-events` and its source is repointed from `media-domain-events` to the new `media-integration-events` SNS topic. Integration-event translation happens inline in the Command Handler via per-module `*IntegrationEventPublisher` classes (no separate Lambda). External BCs subscribe their own SQS queues to `media-integration-events`. The fan-out topology choice (SNS → SQS) described in this ADR is unchanged.

---

## Context

After events are persisted to the DynamoDB event store, downstream consumers (projectors, processing worker, sagas, SecuredSigning adapter) need to be notified. Options:

1. **DynamoDB Streams → Lambda** (native, no infrastructure)
2. **SQS queues** (Command Handler publishes after write)
3. **SNS + SQS fan-out** (pub/sub pattern)
4. **EventBridge** (rule-based routing)

---

## Decision

**Command Handler publishes domain events to SQS directly after a successful write to the event store.**

Each consumer has its own SQS queue. The Command Handler publishes to an SNS topic; each downstream queue subscribes. This is the standard SNS → SQS fan-out pattern.

```
Command Handler
      │  (after successful PutItem to event store)
      ▼
  SNS Topic: media-domain-events
      │
      ├──▶ SQS: media-projector        (Projectors Lambda)
      ├──▶ SQS: media-processing       (Processing Worker Lambda)
      ├──▶ SQS: media-sagas            (SagaOrchestrator Lambda)
      └──▶ SQS: media-signing          (SecuredSigning Adapter Lambda)

  SNS Topic: media-integration-events  (populated inline by module
      │                                 *IntegrationEventPublisher classes
      │                                 running in Command Handler — see ADR-005)
      │
      ├──▶ SQS: media-cross-module-events  (MM-owned intra-BC fan-in)
      └──▶ External BC-owned SQS queues    (Notifications, Search/Discovery,
                                            Billing, Compliance)
```

All queues have a DLQ (max 3 retries, then DLQ). CloudWatch alarms on DLQ depth.

---

## Consequences

**Positive:**
- Consumer isolation — projector failures don't block processing worker
- Each queue has independent retry, DLQ, and scaling configuration
- SQS message visibility timeout gives us processing-time guarantees without distributed locks
- SNS fan-out is a well-understood AWS pattern with minimal operational risk
- Avoids tight coupling to DynamoDB Streams shard limitations

**Negative / Accepted trade-offs:**
- **Dual-write risk:** If Command Handler writes to event store but crashes before publishing to SNS, the event is "lost" from the bus. Mitigation: Outbox pattern (see below) or idempotent catch-up rebuild. **Accepted for v1** — full event store replay is always available for projection rebuilds.
- SNS + SQS adds a small latency (typically < 100ms) vs. DynamoDB Streams
- More IAM roles and queue ARNs to manage

**Outbox consideration (deferred to v2):**
A proper outbox would write events to a `media-outbox` DynamoDB table in the same transaction as the event store write (using DynamoDB transactions), with a separate Lambda polling and publishing. This eliminates the dual-write gap. Deferred — acceptable risk at current scale.

**Not chosen — DynamoDB Streams:**
- DynamoDB Streams deliver at the shard level, not the event level — ordering guarantees are per shard, not per aggregate
- Shard count is managed by DynamoDB automatically; fan-out to multiple consumers requires Lambda → SNS → SQS anyway, adding complexity without benefit
- Streams have a 24-hour retention window; SQS retention is configurable up to 14 days

**Not chosen — EventBridge:**
- Excellent for cross-account routing and complex rule matching
- Overhead unjustified for an internal, single-account bounded context
- Higher latency than SQS for simple delivery

---

## Review Trigger

Revisit if: dual-write failures are observed in production at measurable frequency, or if the bounded context needs to fan out to more than 6–8 consumers (SNS subscription limit considerations).
