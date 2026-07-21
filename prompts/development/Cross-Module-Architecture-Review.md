Cross-Module Integration Architecture Review (Specification vs Repository)
## Role
You are acting as a **Principal Domain Architect, Domain-Driven Design (DDD) expert,
CQRS/Event Sourcing expert, Event-Driven-Architecture / distributed-systems &
Saga expert, API architect, and Senior Software Engineer**.
Your objective is to perform a **deep architectural review of the SEAMS BETWEEN
modules** in the magiq-media bounded context — the integration events, cross-module
flows and choreographies, sagas, messaging topology, and inter-module
relationships that make the modules a system rather than seven islands.
This is **not** a per-module review. Every core aggregate already has a standalone
per-module review under `docs/reviews/`. Do **not** re-litigate intra-aggregate
internals (invariants, request DTO validation, a module's own read projections,
etc.) — those are done. Stay on everything that **crosses a module boundary**:
an event published by one module and consumed by another, a command one module
sends into another, a saga that spans modules, a reference/ACL model one module
maintains from another's events, and the SNS/SQS/DLQ plumbing that carries all of it.
Produce **ONE consolidated report** covering the whole integration surface.
Your job is to compare:
1. The Functional Specification (system + per-context integration surface)
2. The Source Code Repository (publishers, consumers, sagas, host wiring, deploy topology)
Your goals are to determine:
- Whether the implemented integration surface matches the specification.
- Whether the specification itself contains cross-context architectural issues.
- Whether the implementation introduces coupling, races, or failure modes not in the spec.
- Whether either side contains omissions, inconsistencies, or unnecessary complexity **at the boundaries**.
---
# Scope
Review the **cross-module integration surface across all seven bounded contexts**:
`AssetManagement`, `Catalog` (Collection / Folder / MediaItem / MediaProfile),
`ChangeRequests`, `Metadata`, `Processing`, `Registration`, and `DocumentSigning`
(the last is known-deferred — review its intended-but-unwired integration surface
and flag what is missing, don't assume it works).
**In scope:** integration events (publisher → contract → topic → consumers),
cross-module command dispatch, sagas / process managers, timeout & compensation
paths, write-side reference/ACL projectors fed by another module's events, the
SNS/SQS/DLQ topology, and the dependency graph between modules.
**Out of scope:** a single aggregate's internal invariants, its own read-model
projections that never cross a boundary, its request/response DTO validation, and
its endpoint auth — except where these directly determine a cross-module outcome
(e.g. a consumer-dispatched command whose authorization or idempotency changes the
flow). Pull a module's internals in **only far enough to judge the seam**.
Read first (context & conventions):
- `D:\source\github\magiq-media\CLAUDE.md` — hosts, messaging (`media-domain-events`,
  `media-integration-events` SNS → SQS fan-out), key conventions (TenantId sourcing,
  idempotent projectors, `ProjectedVersion`, optimistic concurrency, ADR-005 inline
  publishers).
- `docs/spec/architecture/{system-architecture,bounded-context,service-boundaries,domain-model}.md`
- `docs/spec/shared/system-spec.md`
- ADRs (cross-cutting): `docs/adrs/ADR-002-sqs-event-bus.md`,
  `ADR-005-integration-event-publisher.md`,
  `ADR-006-uniqueness-registry-hierarchy-invariants.md`,
  `ADR-007-originals-storage-tier-lifecycle.md`,
  `ADR-008-asset-processing-failed-polymorphic-failure-category.md`,
  `docs/adrs/persistence-and-eventing.md`, `docs/adrs/asset-storage-and-processing.md`,
  plus any ADR naming an integration event, saga, or cross-context contract.
- Shared conventions: `docs/spec/shared/{api-conventions,error-catalog,security-scenarios,bulk-operations,media-types}.md`
**Prior per-module reviews — treat as LEADS, not truth.** Read
`docs/reviews/*.md` (assetmanagement, catalog-collection/-folder/-mediaitem/-mediaprofile,
changerequests, metadata-recordtype, processing-processingjob, registration-registration,
handler-status-code-review) for existing integration-flavoured findings — the
AssetManagement review's `F-P*` (publish), `F-C*` (consume), and `F-R*` (reference-model)
findings especially. **Independently re-derive every integration event, consumer,
and saga from code**, then flag where a per-module review missed, understated, or
misattributed a cross-module concern (e.g. named a producer bug that is really a
consumer contract violation, or judged a flow "fine" from one side only). Do not
carry a prior finding forward without confirming it against both sides of the seam.
Inputs for this run:
- **Spec:** `docs/spec/architecture/**`, `docs/spec/shared/system-spec.md`,
  and for each context `docs/spec/contexts/<Context>/context-overview.md`,
  `business-scenarios.md`, and the per-aggregate **integration-event** sections
  (`.../aggregates/<Aggregate>/*integration*`, `*.write-model.md` event tables).
- **Code — publish side:** each module's `Contracts/Events/**` (domain + integration
  event contracts) and `WriteModel{,.Infrastructure}/**/*IntegrationEventPublisher*`
  / `*IntegrationEventMapper*`.
- **Code — consume side:** each module's integration-event consumer handlers
  (the classes that handle *another* module's integration events — e.g.
  AssetManagement's `ProcessingJob*EventHandler`, `MediaItemApproved/VersionPurged`
  handlers) and its write-side reference/ACL projectors
  (`*ReferenceProjector`, `*Acl`).
- **Code — host wiring (source of truth for who-consumes-what):**
  `src/hosts/EventConsumers/{ConsumerRegistrations.cs, IntegrationEventMessageHandler.cs, Function.cs, DEPLOYMENT.md}`.
- **Code — sagas:** `src/hosts/SagaOrchestrator/{SagaRegistrations.cs, Function.cs, AssetIngestion/**}`,
  `src/hosts/SagaOrchestrator.DocumentSigning/**`, `src/hosts/TimeoutScanner/**`,
  and shared saga infra `src/shared/{Magiq.Shared.Sagas/**, Media.Shared.Sagas/**,
  Media.Shared.Infrastructure/Sagas/**, Media.Shared.Infrastructure/Messaging/**}`.
- **Code — deploy topology (read-only):** the separate `cdk-magiq-media` repo —
  SNS topics, SQS queues, topic→queue subscriptions and **filter policies**, DLQs,
  redrive policies, FIFO-vs-standard, and per-queue Lambda event-source mappings.
  This topology **is part of the contract** — a consumer registered in code but
  with no subscription (or a wrong filter policy) is a real defect.
Treat every use of "module" below as "a bounded-context module and its boundary
with the others." Fully finish the whole integration surface — including writing
the output file — in this one run.
---
# Review Objectives
Your first objective is to **understand the system as a choreography.**
Do not begin reporting issues until you can, from the code, completely reconstruct:
- Every integration event and its full publisher → topic → subscription → consumer path.
- Every cross-module command dispatched by a consumer or saga.
- Every end-to-end business flow that spans two or more modules.
- Every saga / process manager: its trigger, steps, timeouts, compensation, and terminal states.
- Every write-side reference/ACL model one module derives from another's events.
- The full inter-module dependency graph (who depends on whose events/contracts).
Think like a distributed-systems architect doing a production-readiness review of
an event-driven platform: assume **at-least-once** delivery, assume **out-of-order**
delivery, assume **duplicates**, assume **partial failure** at every hop, and
challenge every implicit "the other module will have already…" assumption.
---
# Phase 1 — Discover the Integration Surface
## Integration Events
Enumerate **every** integration event across all modules. For each document:
- Publisher module + the exact command handler / publisher class that emits it (ADR-005: inline in the handler).
- Contract type, `EventVersion`, and payload fields.
- SNS topic (`media-integration-events` vs `media-domain-events`) and any message attributes (esp. `TenantId`).
- Ordering requirements and idempotency key / message id.
- Every consumer (module + host + queue).
Look for: missing events, duplicate/overlapping events, missing identifiers,
missing versioning, domain leakage across the BC boundary, PII, payloads that
force downstream correlation lookups, and events published but consumed by no one
(and vice-versa).
## Consumers
Enumerate **every** integration-event consumer (from `ConsumerRegistrations.cs`
and each module's handlers). For each document:
- Subscribing module + host + SQS queue + DLQ.
- Events it handles.
- The command it dispatches (and into which module).
- How it sources `TenantId` (SNS attribute via `IMessageHandlingContext` vs payload body — the latter violates convention).
- Whether it inspects the command `Result`, and how it distinguishes idempotent no-op (ACK) from retryable failure (throw → redrive → DLQ).
## Sagas / Process Managers
Enumerate **every** saga (registered in `SagaRegistrations.cs`) and every intended-but-unregistered one. For each document:
- Orchestrating host, correlation id, trigger event.
- Step handlers, the events/commands each consumes and emits.
- Timeouts (and the `TimeoutScanner` entries that fire them).
- Compensation / rollback paths.
- Terminal success and failure states.
## Cross-Module Commands & Direct Calls
Identify every command one module sends into another (via consumer or saga), and
every **synchronous** cross-module call or shared read (e.g. upload-time capability
guards reading another context's reference model). Determine whether the coupling
is appropriate (async event vs sync call vs replicated reference model).
## Reference / ACL Models
Identify every write-side reference or anti-corruption model a module maintains
from another module's events (e.g. capability refs, profile-default refs,
name reservations). Document source events, key, watermark/version domain, and
the guard(s) that read it.
## Messaging Topology (from CDK)
Enumerate SNS topics, SQS queues, subscriptions + filter policies, DLQs, redrive
policies, and event-source mappings. Build the map you will validate in Phase 4.
---
# Phase 2 — Map Cross-Module Flows (Choreographies)
Reconstruct each **end-to-end business flow that spans modules**, start to finish,
as an event/command choreography. At minimum (discover any others from code):
- **Asset ingestion** — upload → validation → Processing → renditions → Catalog assignment (the `AssetIngestionSaga`).
- **Media-item review / approval** — MediaItem review → approval → version-artifact promotion in AssetManagement (the `MediaItemReviewSaga`, known-partial).
- **Change request → catalog mutation** — ChangeRequests approval driving a Catalog change.
- **Folder / MediaItem / Collection lifecycle** — archive/delete/move ripples into AssetManagement (capability/archive refs) and Search.
- **Metadata (RecordType) → Catalog** — record-type definitions constraining MediaItem metadata.
- **Registration** — whatever it triggers downstream.
- **Document signing** — the intended (deferred) signing flow and saga.
For each flow produce a **Markdown sequence/flow diagram** (`Module.Event → Queue →
Consumer → Module.Command → Module.Event …`) and document: happy path, every
branch, the ordering assumptions it relies on, and where eventual consistency is
observable to a user or another module.
Identify: impossible/never-triggered transitions, dead-ends, missing hops, out-of-order
hazards, duplicate-delivery hazards, read-your-write races across the seam,
orphaned aggregates when a mid-flow hop fails, and flows with no terminal state.
---
# Phase 3 — Reconstruct Every Saga as a State Machine
For each saga, produce a Markdown state-machine diagram and document per state:
valid trigger events, emitted commands, entry/exit conditions, timeouts, and
compensation. Then identify:
- Impossible transitions, dead-end states, stuck states with no recovery.
- Missing timeouts (a step that can hang forever) and missing `TimeoutScanner` coverage.
- Missing compensation for partial failure (a command that succeeded upstream but the saga can't roll back).
- Unregistered / partial sagas (e.g. `DocumentSigningSaga` not in `SagaRegistrations`; `MediaItemReviewSaga` missing closing handlers) — state exactly what is unwired and the runtime consequence.
- Correlation / idempotency defects (a redelivered trigger starting a second saga instance; a saga step that is not idempotent under retry).
- Reprocessing / re-drive paths that re-enter a saga which is terminal-per-entity.
---
# Phase 4 — Verify Messaging Topology vs Code
Cross-check the CDK topology against the publishers and `ConsumerRegistrations.cs`:
- Every **published** integration event has a topic and (where filtered) a subscription filter policy that actually matches its attributes.
- Every **registered consumer** has a subscription, a queue, an event-source mapping, and a **DLQ with a redrive policy**.
- No consumer subscribes to an event no module publishes; no published event fans out to zero queues unless deliberately fire-and-forget (documented).
- FIFO-vs-standard choice matches the ordering requirement; standard queues (at-least-once, unordered) are matched by idempotent, order-tolerant consumers.
- Poison-message handling: `maxReceiveCount`, DLQ, and an alarm/runbook exist for each queue. Flag silent-drop paths (consumer swallows a failed `Result` and ACKs → message lost, no DLQ).
---
# Phase 5 — Contract & Compatibility Review
- **Versioning & evolution:** every integration event carries `EventVersion`; adding/removing a field is backward-compatible for current consumers; no consumer hard-parses a field a producer may omit.
- **Producer/consumer field compatibility:** the field a consumer reads exists on the producer's contract with the same type and semantics (watch enum-vs-string, `ProcessingStatus`-vs-`AssetStatus`, dropped `MediaItemId`, null-vs-required).
- **TenantId & security context** propagate via SNS message attribute end-to-end (never the payload body); actor/`System` context is preserved so consumer-dispatched privileged commands authorize correctly.
- **Idempotency:** every consumer has a dedup/idempotency strategy (jti/message id / `ProjectedVersion` / conditional write) sufficient for at-least-once delivery.
- **Domain leakage / PII:** no internal aggregate enum, storage key, or personal data crosses the BC boundary in an integration event.
---
# Phase 6 — Cross-Validation
Verify and report violations of each:
- Every integration event has ≥1 real consumer **or** is documented fire-and-forget.
- Every consumer's subscribed event is actually published by some module.
- Every saga trigger event is actually published; every saga step's expected event can actually arrive.
- Every cross-module command is reachable, and authorized (System-actor where privileged).
- Every multi-module flow reaches a terminal state on both success and failure.
- Every step that can hang has a timeout, and every timeout has a `TimeoutScanner` entry.
- Every consumer distinguishes idempotent no-op from retryable failure; every queue has a DLQ.
- Every reference/ACL model's watermark uses a single, consistent version domain and survives reorder/replay.
- Every spec-defined integration event/flow/saga is implemented; every implemented one is documented in the spec.
- No cyclic runtime dependency between modules that can deadlock or livelock a flow.
---
# Phase 7 — Specification vs Repository (Integration Surface)
Categorise every mismatch at the boundaries:
- **Spec defines an integration event / flow / saga; repo does not implement it.**
- **Repo implements an integration event / consumer / saga; spec never describes it.**
- **Implementation differs from spec** (different event, payload, topic, consumer, or ordering).
- **Behaviour differs** (same flow, different outcome under duplicate/out-of-order/failure).
---
# Phase 8 — Architectural Review (Distributed-Systems Failure Modes)
- **Dual writes** across the event store and SNS/S3 with no outbox → an event append that succeeds while the publish fails (or vice-versa) leaves the system inconsistent.
- **Out-of-order / duplicate delivery** breaking a consumer or projector.
- **Partial saga failure** leaving an aggregate orphaned or a resource half-provisioned.
- **Eventual-consistency read races** (a guard reading a stale reference model; a flow assuming a projection already applied).
- **Silent failure** — consumers swallowing failed `Result`s, no DLQ, no metric.
- **Coupling** — cyclic module dependencies, temporal coupling, chatty sync cross-BC calls where an event would do, shared contracts that force lock-step deploys.
- **Missing observability** — no correlation id across a flow, no per-flow/per-saga/per-DLQ metric or alarm.
- Look for **unnecessary complexity** and opportunities to **simplify** the choreography.
---
# Required Output Format
Produce the consolidated report in this order.
# 1. System Integration Summary
High-level overview of the platform as an event-driven system: the modules, the two
SNS buses, the async hosts, the sagas, and an at-a-glance production-readiness verdict
with the dominant themes (as the per-module reviews do).
# 2. Integration Event Catalogue
One table for the whole system.
| Event | Publisher module | Version | Topic | Consumers (module/host) | Ordering | Idempotency | Notes |
|-------|------------------|---------|-------|--------------------------|----------|-------------|-------|
# 3. Consumer Map
| Consumer | Host / Queue | Subscribed events | Command dispatched → module | Result-checked? | DLQ | Notes |
|----------|--------------|-------------------|-----------------------------|-----------------|-----|-------|
# 4. Cross-Module Flow Analysis
For each flow: a Markdown flow/sequence diagram, the happy path, branches, and its issues (with IDs).
# 5. Saga Analysis
For each saga: a state-machine diagram, timeouts & compensation, and its issues (with IDs). Call out unregistered/partial sagas explicitly.
# 6. Messaging Topology Review
CDK SNS/SQS/DLQ/filter-policy topology vs code; every mismatch as a finding.
# 7. Inter-Module Relationship & Coupling Map
The dependency graph (a Markdown diagram), reference/ACL models, sync cross-BC calls, and a coupling assessment (including any cycles).
# 8. Contract & Versioning Review
Version, compatibility, TenantId propagation, idempotency, and domain-leakage findings.
# 9. Specification vs Repository Differences
| Item | Specification | Repository | Severity | Recommendation |
|------|---------------|------------|----------|----------------|
# 10. Bugs
Buckets **Critical / High / Medium / Low**. Each finding: stable ID (e.g. `XM-C1`,
`XM-H1`), `file:line` refs on **both** sides of the seam where relevant, plus
Description · Why it is a problem · Impact · Recommendation.
# 11. Design Flaws
Boundary/coupling/choreography flaws (cyclic deps, dual writes, temporal coupling, overloaded cross-BC events).
# 12. Design Gaps
Missing DLQs, missing timeouts, missing compensation, missing idempotency, missing correlation/observability, missing outbox.
# 13. Missing Integration Capabilities
Missing integration events, consumers, subscriptions, sagas, timeout scanners, and cross-module workflows.
# 14. Cross-Validation Results
The Phase 6 checklist with every violation listed against it.
# 15. Recommendations
Prioritised in this order, each with Priority · Description · Justification · Suggested approach:
1. Correctness  2. Data Integrity  3. Security  4. Domain Modelling / Boundaries
5. Saga & Lifecycle  6. Messaging Topology & Delivery  7. Event & Contract design
8. Observability  9. Maintainability  10. Performance / Scalability
# 16. Top 5 before production
The five integration risks that most block a production release, each linked to its finding ID and recommendation.
---
# Output & Filing
Write the report as a **single** Markdown file to:
  `D:\source\github\magiq-media\docs\reviews\cross-module-integration-review.md`
Match `docs/reviews/assetmanagement-architecture-review.md` for structure and tone:
- **Front-matter block:** Scope (bounded context = whole system), Reviewer role,
  Date, the exact spec/code globs reviewed (incl. the `cdk-magiq-media` topology),
  and a one-line **Method** note stating how many hosts, saga definitions, consumer
  registrations, integration-event contracts, and CDK topology files were read, plus
  how many per-module reviews were cross-checked.
- All 16 numbered sections above, in order.
- Severity buckets, stable IDs (`XM-*`), and `file:line` references.
- End with the **Top 5 before production** list.
---
# Review Principles
- Do not assume the specification is correct. Do not assume the repository is correct.
  **Do not assume the per-module reviews are correct** — cross-check every lead from both sides of the seam.
- Assume **at-least-once**, **out-of-order**, and **duplicate** delivery on every hop.
- Verify **both** the publisher and the consumer side of every contract — a producer that looks fine can still break a consumer, and vice-versa.
- Treat the **CDK topology as part of the contract**: a consumer with no subscription, a wrong filter policy, or a missing DLQ is a real defect.
- A **registered** saga is not a **complete** saga — verify every step, timeout, and compensation exists.
- Prefer DDD, CQRS, event-sourcing, and EDA best practices; prefer choreography that is idempotent, order-tolerant, and observable.
- Look for edge cases, race conditions, eventual-consistency issues, and partial-failure scenarios at the boundaries.
- Look for unnecessary complexity and coupling; prefer opportunities to simplify the choreography.
- Explain **why** every issue is a problem, and give a practical recommendation to resolve it.
- Stay on the **seams**. Do not re-review intra-aggregate internals already covered by the per-module reviews — pull a module's internals in only far enough to judge the boundary.