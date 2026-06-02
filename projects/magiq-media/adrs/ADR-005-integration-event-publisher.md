# ADR-005: Distributed Integration Event Publishers and `media-integration-events` SNS Topic

**Status:** Accepted
**Date:** 2026-04-17
**Deciders:** Chase Ramone
**Supersedes:** The `media-notifications` role portion of ADR-002

---

## Context

ADR-002 introduced `media-notifications` as an SQS queue subscribed to the `media-domain-events` SNS topic, intended to feed a single "Notification Dispatcher Lambda." Subsequent architecture and spec documents drifted and began describing `media-notifications` as a queue that external bounded contexts (Notifications, Search/Discovery, Billing, Compliance) subscribe to directly.

That later framing is structurally broken:

- **SQS is point-to-point.** A single SQS queue can only be consumed by one logical consumer — if four external contexts attempted to pull from `media-notifications`, they would race for each message and most events would never reach most consumers.
- **It couples boundaries.** External contexts subscribing to a Media Management-owned queue inverts ownership. Downstreams should own their own queues, subscribe filters, and consumption cadence.
- **It leaks internal event shapes.** `media-domain-events` carries internal domain events (`AssetProcessingCompleted`, `MediaItemApproved`, etc.). Exposing those directly to external BCs violates Published Language discipline — any internal refactor becomes a breaking cross-BC change.

We need a topology that: (a) physically supports multi-consumer fan-out to external BCs, (b) exposes a stable, curated integration-event contract, and (c) gives downstreams their own retry/DLQ envelopes.

---

## Decision

Introduce a **second SNS topic**, `media-integration-events`, carrying only the curated integration-event subset in published-language (`media.*`) envelope form. **Translation happens inline in the write model**, not in a separate Lambda: each module owns a `*DomainEventMapper` class that implements `IDomainEventMapper<T>` for its published events, constructs the corresponding integration-event record, and publishes to `media-integration-events` via `IMessageBus.PublishAsync(...)`. These mappers run in the same transaction-scope as the domain event being handled (Command Handler Lambda), so publish happens after the event is durably appended to the event store.

`media-notifications` is retained as the internal SQS trigger queue — but its source is repointed from `media-domain-events` to `media-integration-events`, and it feeds intra-BC consumers (e.g. AssetManagement projecting Catalog's `MediaItemCreatedMessage` into its capability index). It is renamed to `media-cross-module-events` to reflect its intra-BC fan-in role (see ADR migration notes).

```
Command Handler (per module)
      │  appends to event store (media-events DynamoDB)
      │  dispatches domain event handlers synchronously
      │    ├─▶ projector handlers (own local read models)
      │    └─▶ *DomainEventMapper (this module)
      │          │  constructs media.* message record
      │          ▼
      │      SNS Topic: media-integration-events   ← published language, media.* envelopes
      │
      │  (separately) publishes domain event to:
      ▼
  SNS Topic: media-domain-events                   ← internal, domain event shapes
      │
      ├──▶ SQS: media-projector       (Projectors Lambda — cross-aggregate projections)
      ├──▶ SQS: media-processing      (Processing Worker — AssetValidationPassed only)
      ├──▶ SQS: media-sagas           (SagaOrchestrator)
      └──▶ SQS: media-signing         (SecuredSigning Adapter)

  SNS Topic: media-integration-events
      │
      ├──▶ SQS: media-cross-module-events (intra-BC fan-in: AssetManagement, Catalog,
      │                                    ChangeRequests consumers that react to
      │                                    other modules' integration events)
      ├──▶ Notifications-owned SQS        (filter policy per catalog)
      ├──▶ Search/Discovery-owned SQS     (filter policy per catalog)
      ├──▶ Billing-owned SQS              (filter policy per catalog)
      └──▶ Compliance-owned SQS           (filter policy per catalog)
```

### Per-Module Integration Event Mappers

Each module in `src/modules/` owns a mapper class in its `WriteModel/IntegrationEvents/Publishing/Mappers/` folder:

| Module | Mapper class |
|---|---|
| AssetManagement | `AssetIntegrationEventMapper` |
| Catalog | `MediaItemDomainEventMapper`, `CollectionDomainEventMapper`, `FolderDomainEventMapper`, `MediaProfileDomainEventMapper` |
| ChangeRequests | `ChangeRequestDomainEventMapper` |
| Metadata | `RecordTypeDomainEventMapper` |
| Processing | `ProcessingDomainEventMapper` |
| Registration | `RegistrationDomainEventMapper` |

**Responsibilities (each mapper):**
- Implement `IDomainEventMapper<TDomainEvent>` for every domain event in its module that maps to an integration event.
- Expose a `Map(TDomainEvent e)` method returning `IEnumerable<IIntegrationEvent>`. One domain event may produce zero or more integration events (yield-return pattern allows conditional or multi-event mappings).
- Translate domain event → `media.*` integration event record (an `IntegrationEvent`-derived `record` in the module's `.Contracts` project).
- The framework invokes `Map(...)`, collects the results, and calls `messageBus.PublishAsync(message, cancellationToken)` for each. The `IMessageBus` implementation resolves the target SNS topic from the AWS.Messaging publisher mapping and stamps SNS message attributes (`TenantId`, `EventType`, `AggregateId`, `AggregateVersion`, `CorrelationId`, `OwnerId`) from message fields and ambient context.

**Do NOT:**
- Write to DynamoDB or any read model (projections are separate handlers).
- Dispatch commands.
- Consume from any queue (they are outbound translators only).

**Idempotency:** Downstream consumers remain responsible for their own idempotency. `EventId` on the integration event is stamped deterministically from the source domain event's `(AggregateId, AggregateVersion, EventType)` so that re-dispatch through the handler pipeline produces the same integration-event ID and downstream consumers can de-dupe.

**No catalog drift enforcement:** Because mapping is distributed across modules, the Integration Event Catalog (in `bounded-context.md`) is not auto-enforced by a single mapping table. A unit test in each module's WriteModel test project asserts that every `IntegrationEvent`-derived type registered in DI maps to a catalog entry, and vice versa.

### Topic Ownership

| Topic | Owner | Contract |
|---|---|---|
| `media-domain-events` | Media Management | Internal. Carries domain events in internal shape. Only MM-owned consumers may subscribe. |
| `media-integration-events` | Media Management | Boundary. Carries `media.*` integration events in published language. External BCs subscribe with their own SQS + filter policies. |

### Queue Ownership

| Queue | Owner | Source topic | Purpose |
|---|---|---|---|
| `media-projector`, `media-processing`, `media-sagas`, `media-signing` | Media Management | `media-domain-events` | Internal consumers of domain events |
| `media-cross-module-events` (renamed from `media-notifications`) | Media Management | `media-integration-events` | Intra-BC consumers that react to *other modules'* integration events (e.g. AssetManagement maintaining capability index from Catalog's `MediaItemCreatedMessage`) |
| Each external BC's consumer queue (e.g. `notifications-media-events`, `search-media-events`, `billing-media-events`, `compliance-media-events`) | That BC | `media-integration-events` | External BC consumption with own filter policies and DLQs |

---

## Consequences

**Positive:**
- External BCs get real fan-out. Each owns its queue, filter policy, DLQ, and retry behaviour.
- Published Language is enforced at the topic boundary. Internal domain event refactors no longer leak across BCs.
- **No additional Lambda to operate.** Translation is an in-process responsibility of the Command Handler, which already has full ambient context (tenant, correlation id, user).
- **Lower latency.** Publish happens inline with the command that produced the domain event; no SQS hop to a translator Lambda.
- **Strong context locality.** The translation for each aggregate lives next to the aggregate's domain events — refactors stay in one module.
- Intra-BC consumers share the same integration-event stream as external consumers, so module-to-module reads use the same Published Language discipline as cross-BC reads.

**Negative / Accepted trade-offs:**
- **Catalog drift risk.** Translation is scattered across per-module mappers rather than centralised. Mitigated by DI-registration-vs-catalog unit tests per module.
- **Publish failure semantics are command-scoped.** If SNS publish fails after the domain event has been appended to the event store, the failure surfaces on the command — the caller can retry, but the integration event may have been published already on an earlier attempt (AWS.Messaging handles this via deterministic `EventId` + at-least-once delivery). The deferred outbox (ADR-002 v2 review trigger) will harden this to exactly-once semantics.
- **Two topics to manage IAM and subscription policies for.** External BC subscriptions require cross-account policy on `media-integration-events` if they live in different AWS accounts.
- **Cross-module write-model coupling via mapper files.** Each module's mapper depends on its own domain events and its own `.Contracts` project, but any cross-module change to a shared contract (rare) requires coordinated edits.

**Not chosen — centralised Integration Event Mapper Lambda:**
- Cleaner catalog enforcement (single mapping table), but adds a Lambda, a queue, and ~100ms latency for no functional gain. The per-module mappers already exist in the repo and cleanly encapsulate translation. Rejected on operational and latency grounds.

**Not chosen — external BCs subscribe directly to `media-domain-events`:**
- Fastest and simplest, but leaks internal event shapes across the BC boundary and couples downstream consumers to our internal schema evolution cadence. Rejected on Published Language grounds.

**Not chosen — EventBridge for the outbound topic:**
- EventBridge rule-based routing and cross-account delivery are attractive, but the extra latency and operational surface are not justified for the current consumer set. Revisit if we cross into cross-account delivery at scale or need schema registry integration.

---

## Migration Notes

- `media-notifications` SQS queue is renamed `media-cross-module-events`. Its SNS subscription source changes from `media-domain-events` to `media-integration-events`. The existing DLQ and alarms carry over.
- `media-integration-events` SNS topic is new. Publisher mappings registered in each module's DI composition point `IntegrationEvent`-derived types at the topic ARN (via `AddSNSPublisher<T>(topicArn)`).
- The existing `Media.IntegrationEventConsumers.Lambda` host continues to consume the renamed queue. Its `sqs-event-source-mapping.json` is updated for the new queue name.
- Existing specs and ADRs referencing "external BCs subscribe to `media-notifications`" are updated to reflect the new topology (see `system-spec.md`, `bounded-context.md`, `system-architecture.md`, `service-boundaries.md`).
- External BCs must stand up their own SQS queues subscribed to `media-integration-events`. Media Management will not provision or manage downstream subscriber queues.

---

## Review Trigger

Revisit if: the integration event catalog grows past ~50 event types (consider schema registry); cross-account fan-out to more than three external AWS accounts becomes required (consider EventBridge); publish failure rates after event-store append exceed SLA (accelerate outbox, ADR-002 v2); or catalog drift tests become flaky (revisit centralised translator).
