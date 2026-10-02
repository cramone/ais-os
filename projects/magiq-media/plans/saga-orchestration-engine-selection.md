# Saga Orchestration Engine — Selection and Migration Plan

**Status:** Recommendation for approval
**Owner:** Chase Ramone
**Date:** 2026-09-30
**Decision needed from:** Platform architecture (Tom), engineering leadership
**Related audit findings:** spec-audit-2026-09-29 F007, F018, F019, F022, F023, F028, F029, F030, F031, F032, F033, F034, F042, F049, F074, F075, F076, F087

---

## Executive Summary

The magiq-media platform coordinates asynchronous work (asset ingestion, document
signing, archive cascades) through hand-written sagas persisted in DynamoDB and
driven by SQS message redelivery. No production traffic currently flows through
these sagas — the coordination substrate is greenfield.

**Recommendation.** Build the coordination layer on **AWS Step Functions** rather
than continuing with the DIY SQS + DynamoDB saga substrate.

**Why.** Records-management workloads at our projected scale (10–50 tenants,
&lt;100k assets/day platform-wide in year one, sustained &lt;500k assets/day at
enterprise saturation) fall firmly in the range where the correctness,
operability, and engineering-cost benefits of a managed orchestrator dominate
the per-transition cost premium.

**Cost impact.** Step Functions Standard adds approximately $6.75 per million
state transitions above a DIY SQS + DynamoDB equivalent. At projected year-one
volume this is under $10k/year in coordination overhead. Break-even against the
engineering cost of maintaining a DIY substrate arrives around
**500 000 assets ingested per day sustained platform-wide** — an order of
magnitude beyond our projected 12-month scale.

**Portability.** The design keeps the aggregate, event, projection, and
integration-event surface identical under either substrate. If cost or scale
ever forces a migration, only the coordinator layer changes — and only for the
one saga (AssetIngestion) whose volume could realistically justify it.

**Revisit trigger.** A single CloudWatch alarm on sustained platform-wide
ingest &gt;300k assets/day. If it fires, revisit the math with real
production data. Nothing else changes until it does.

---

## Context

### What is a saga in this platform

magiq-media coordinates four kinds of asynchronous multi-step work, all
currently modelled as sagas or process managers:

| Coordinator | Purpose | Volume | Duration | Trigger |
|---|---|---|---|---|
| **AssetIngestionSaga** | Per-asset per-attempt: validation → processing → active | High (per upload) | 15 min – 4 h | `media.processingjob.created` |
| **DocumentSigningSaga** | Per signing session: envelope create → signers → signed-doc write-back → release | Low (per session) | 14 days + 24 h + retries | `SigningSessionInitiated` |
| **CollectionArchiveCascade** | Async cascade over collection subtree | Moderate (per archive) | Minutes – hours | `CollectionArchiveStarted` |
| **FolderArchiveCascade** | Async cascade over folder subtree, capped at 500 folders | Moderate | Seconds – minutes | Folder archive API call |

Non-saga scheduled work (upload expiry, registration-response overdue, retention
reconciliation, quarantine-move retry) runs on a separate scanner Lambda and is
out of scope for this decision.

### Why the decision matters now

The current spec models these coordinators as hand-written state machines
persisted in a `media-sagas` DynamoDB table, driven forward by SQS message
redelivery, and timed out by a scheduled scanner Lambda that queries a GSI. The
2026-09-29 spec audit surfaced **17 findings** that trace directly to defects in
these hand-rolled coordination primitives:

- Off-by-one attempt-counter semantics (F012, F030)
- Missing retry resume paths (F030)
- Scanner GSI density / starvation (F023)
- Retry-clock vs queue-visibility mismatch (F033)
- Unfenced continuation chains (F032, F076)
- Missing run identity for stale-trigger fencing (F032, F087)
- Missing lease semantics for concurrent cascades on same root (F087)
- Missing envelope-phase deadline (F034)
- Missing signed-asset retry driver (F035)
- Unspecified reconciliation grace vs redelivery interval (F022)
- Scanner writing saga state contra its own rule (F074)
- Folder-lock lease semantics (F075)
- No concurrency isolation or tenant fairness on shared queues (F049)

Every one of these findings is a bug in a primitive that a workflow engine
provides for free. Continuing on DIY guarantees a steady stream of similar
findings as the platform matures.

Because **no production traffic yet flows through these coordinators**, the cost
of choosing the right substrate now is negligible; the cost of choosing wrong is
either a stream of correctness incidents (DIY at scale) or a migration project
in year two or three.

### What must not change

Whatever substrate coordinates them, the following stay identical:

- Every aggregate (`Collection`, `Folder`, `MediaItem`, `MediaProfile`, `Asset`,
  `ProcessingJob`, `Registration`, `RecordType`, `ChangeRequest`,
  `DocumentSigningSession`)
- Every domain event and every persisted event stream on `media-events`
- Every projection and read model
- Every published integration event on `media-integration-events`
- Every command handler and its idempotency contract
- Every permission, error code, and API contract
- The `TimeoutScanner` host, for its four non-saga passes (upload expiry,
  registration-response overdue, retention reconciliation, quarantine-move
  retry). It is renamed `MaintenanceScanner` and its saga passes are removed.

The domain model is stable. Only the coordinator layer is under consideration.

---

## Options Considered

### Option 1 — AWS Step Functions (recommended)

Managed workflow orchestrator native to AWS. Two workflow types:

- **Standard workflows** — up to 1 year duration, priced per state transition,
  full execution history, exactly-once execution model. Used for
  DocumentSigningSaga (14+ day lifecycle) and cascade orchestration (parent
  state machine).
- **Express workflows** — up to 5 minutes duration, priced per invocation +
  duration, higher throughput. Considered for AssetIngestionSaga but rejected
  because validation-phase budget alone can exceed 5 minutes. Used for cascade
  child executions.

Coordination via declarative Amazon States Language (JSON). Native primitives
for retry policies, timers, parallel/map execution, waiting on external
callbacks (task tokens), event-driven signalling (EventBridge), and error
handling. Distributed Map state provides bounded per-iteration concurrency for
fan-out, replacing the hand-coded semaphore + per-tenant budget the DIY design
requires.

### Option 2 — SQS + DynamoDB DIY (current spec)

Sagas persist state in a `media-sagas` DynamoDB row keyed on
`(TenantId, SagaType, CorrelationId)`. Messages on `media-domain-events` drive
transitions. A `TimeoutScanner` Lambda runs every 5 minutes, queries a GSI on
saga rows past their deadline, and dispatches compensation commands. Retry
policy is hand-written per saga, backed by SQS `maxReceiveCount` and visibility
timeouts.

Full portability off AWS (SQS + Kafka/RabbitMQ, DynamoDB + PostgreSQL/Cassandra
equivalents). Correspondingly, every coordination primitive is our
responsibility to build, test, monitor, evolve, and fix.

### Option 3 — Temporal (self-hosted or Temporal Cloud)

Workflow-as-code engine originally developed at Uber. Deterministic replay,
first-class timers, signals, activities with retry policies.

**Self-hosted:** requires a Kubernetes cluster running the Temporal control
plane (frontend, matching, history, worker services) backed by
Cassandra or PostgreSQL. Substantial ops burden and infrastructure surface.

**Temporal Cloud:** managed service, but US and EU regions only.
Government-agency tenant data crossing the provider boundary is a sovereignty
risk that likely rules it out for Australian and New Zealand government
customers.

Rejected — self-hosted doubles the platform's Kubernetes surface area for one
subsystem; Temporal Cloud fails the sovereignty test for our primary customer
segment.

### Option 4 — Azure Durable Functions

We are not on Azure. Rejected.

---

## Analysis Dimensions

### 1. Scale and throughput

| Dimension | SQS + DynamoDB | Step Functions |
|---|---|---|
| Coordination TPS | Effectively unbounded (SQS Standard has no throughput cap; DynamoDB on-demand scales to 40k WCU per partition) | 4 000 state transitions per second per account (soft, raise to 20 000+) |
| Concurrent in-flight | Bounded only by Lambda concurrency | Bounded by state-transition TPS |
| Long-lived state | Unlimited (row + TTL) | 1 year (Standard workflow hard cap) |
| Timer precision | 5-minute scanner poll floor | Sub-second |

At FAANG scale (10M+ concurrent workflows, sustained 100k+ transitions/sec) DIY
on cell primitives wins because it can outrun account-level Step Functions
caps. **Not our scale.**

At records-management scale (thousands of concurrent workflows peak, tens of
thousands of transitions per second peak) both substrates comfortably fit.

### 2. Cost at scale

Per-transition cost, coordination overhead only (excluding activity Lambda
cost, which is identical under either substrate):

| Substrate | Cost per 1M transitions |
|---|---|
| Step Functions Express | ~$1.50 |
| SQS + DynamoDB DIY | ~$4 |
| Step Functions Standard | $25 |

Step Functions Standard is approximately **6× more expensive per transition**
than DIY. Express is cheaper than DIY but unusable for AssetIngestion's
duration.

**Cost crossover math.** DIY's savings must exceed the engineering cost of
building and maintaining the coordination primitives:

- Build cost, DIY coordination substrate: ~1.5 FTE for two quarters (~$250k)
- Steady-state maintenance: ~0.25 FTE (~$65k/year)
- Ongoing coordination-bug rate: ~20 bugs/year at ~8 hours each = ~$19k/year
- Total steady-state cost of DIY: **~$85k/year**

Break-even where Step Functions Standard premium equals steady-state DIY cost:

| DIY steady-state cost | Break-even volume | Assets/day (@ 15 transitions each) |
|---|---:|---:|
| $65k/year | ~8M transitions/day | ~530k |
| $85k/year | ~10M transitions/day | ~670k |
| $250k/year | ~30M transitions/day | ~2M |

### 3. Correctness

The 2026-09-29 audit found **17 coordination defects** in the DIY design across
one review cycle. Each is a class of bug that Step Functions eliminates by
construction:

| Defect class | Findings | Step Functions eliminates by |
|---|---|---|
| Scanner starvation / GSI density | F023, F074 | No scanner — durable timers |
| Retry-vs-visibility mismatch | F033, F034 | Declarative retry policy on activity |
| Timer imprecision | F022, F030 | Sub-second timers |
| Run identity / stale trigger fencing | F032, F076, F087 | Execution ARN is the run identity |
| Attempt off-by-one | F012, F030 | Retry attempt is engine-managed |
| Concurrent-cascade lease semantics | F075, F087 | Execution existence is the lease |
| Missing resume paths | F030 | Executions resume from history natively |
| Reconciliation grace vs redelivery | F022 | No message-driven state machine |
| Concurrency isolation / tenant fairness | F049 | Distributed Map `MaxConcurrency` per iteration |

Every one of these findings would recur, in mutated forms, across every future
audit cycle on the DIY substrate. Compliance-grade records systems cannot
absorb that class of defect stream as a normal engineering burden.

### 4. Operational complexity

**DIY:** we own the scanner Lambda, the GSI shape, the sparse-index
maintenance, the retry backoff logic per saga, the timer scheduling, the
message deduplication, the versioning strategy for in-flight sagas, the DLQ
redrive procedures, the "already past state" idempotency guards, the dashboards
for each of the above.

**Step Functions:** AWS owns all of it. Console visualisation of every
execution end-to-end. Native retry policy per activity. Native timers. Native
error/catch/finally semantics. Native versioning that lets in-flight executions
complete on their original definition while new executions run new logic.

### 5. Observability

**DIY:** correlate saga rows in DynamoDB with SQS message traces via CloudWatch
Logs Insights queries; join per-handler metrics to derive per-saga time-in-state;
build dashboards from scratch for every saga type.

**Step Functions:** every execution has a graphical event history, timeline,
current state, next scheduled event, active retry attempt — available in
console or via API, without building anything.

### 6. Multi-tenancy fairness

**DIY:** the platform's fair-queue routing gives per-message fairness across
tenants on shared queues. Per-tenant fan-out budgets are hand-coded
(`Media:Catalog:FanOut:MaxDispatchPerTenantPerInvocation`).

**Step Functions:** execution-level throttling per tenant via IAM condition on
execution-name prefix. Distributed Map `MaxConcurrency` per iteration replaces
the fan-out budget natively.

### 7. Long-lived workflows

DocumentSigningSaga runs up to 14 days for human signing, plus 24 hours for
signed-asset recording, plus release retry.

**DIY:** the scanner poll floor is 5 minutes; timer precision below that
requires additional infrastructure. Visibility timeouts on the driving queue
fight with business retry semantics (F033 is exactly this class of bug).

**Step Functions:** `Wait` state supports sub-second timestamps. No polling. No
queue involvement in the wait mechanic.

### 8. Vendor lock-in

**DIY:** portable in principle to any queue + KV store. In practice a
port to a different cloud is a rewrite (Kafka semantics differ from SQS;
Postgres semantics differ from DynamoDB).

**Step Functions:** AWS-only. Migration off is a rewrite.

Given that the platform is already AWS-native (Lambda hosts, DynamoDB event
store, S3 storage, SNS integration events, ECR container images, CDK for
infrastructure), the marginal lock-in from adding Step Functions is
negligible.

---

## Service Limits and Risk Assessment

Step Functions service limits with implications for this workload:

| Limit | Value | Risk for this workload | Mitigation |
|---|---|---|---|
| Standard workflow duration | 1 year | None | 14-day signing lifecycle fits |
| Express workflow duration | 5 minutes | AssetIngestion validation alone can exceed | Use Standard for AssetIngestion; accept the cost premium |
| `StartExecution` TPS | 1 000 per second per account (soft) | Bulk create of 200 items × concurrent bulk requests could throttle | Raise to 5 000+ via AWS support ticket; batch through SQS to smooth bursts |
| State transitions per second | 4 000 per account (soft) | Multi-tenant peak sum | Raise to 20 000+ via ticket; monitor `ExecutionsStarted` and `ExecutionThrottled` |
| Payload input/output size | 256 KB | Compiled MediaProfile snapshot + item metadata already flagged as size concern (F008, F052) | Payload contract = identifiers only; activities load state from event store |
| Execution history events | 25 000 per Standard execution | Long-lived DocumentSigning with many callbacks + retries | Typical session ~30 events; worst case &lt;200. No practical concern |
| State machine definition size | 1 MB | Complex sagas approach it | Modularise: cascades use Distributed Map (small map definition, not unrolled) |
| Distributed Map — children per iteration | 10 000 | Collections with &gt;10k items | Chunk parent map into iterations of 5k; hierarchical map supports millions |
| State machines per account per region | 10 000 (soft) | None — 4 machines total under execution-name-multitenancy | Not applicable |
| Concurrent executions | No hard limit; throttled at transitions | Peak burst | Alarms on `ExecutionThrottled`; downstream Lambda concurrency caps upstream |
| Task token TTL | 1 year (Standard) | Signed-asset callback wait | Fits — DocumentSigning waits &lt;24 h for signed asset |

**Hard-limit crossovers (regardless of cost).** DIY becomes forced if any of
these become required:

- Sustained `StartExecution` &gt;5 000/sec (AWS support-ticket ceiling)
- Single execution needs &gt;1 year lifespan
- Single execution needs &gt;25 000 history events
- On-prem or non-AWS deployment mandated

**None of these apply to magiq-media** at present or in projected 5-year growth.

---

## Cost Modelling

### Year-one projection

| Assumption | Value |
|---|---|
| Tenants (year one) | 10–50 |
| Average assets ingested per tenant per day | 500–5 000 |
| Platform-wide assets ingested per day | 50 000 (low) – 100 000 (high) |
| Coordination transitions per asset | ~15 (AssetIngestionSaga) |
| Coordination transitions per day, platform-wide | 750 000 – 1 500 000 |
| Coordination transitions per year | ~270M – ~550M |

**Coordination cost, year one:**

| Substrate | Annual coordination cost |
|---|---|
| Step Functions Standard | ~$6 750 – ~$13 750 |
| SQS + DynamoDB DIY (transaction cost only) | ~$1 080 – ~$2 200 |
| **Delta (SFN premium)** | **~$5 670 – ~$11 550** |

**Engineering cost, year one:**

| Substrate | Estimated first-year engineering cost |
|---|---|
| Step Functions Standard | ~$60k (state machine definitions, IaC, activity wiring, monitoring setup) |
| SQS + DynamoDB DIY | ~$250k (coordination primitives, scanner logic, retry/backoff framework, versioning, monitoring, coordination-bug remediation) |
| **Delta (DIY premium)** | **~$190k** |

**Net year-one advantage of Step Functions: approximately $180k.**

### Break-even scale

| Metric | Value |
|---|---|
| Sustained assets/day at which SFN premium equals DIY steady-state maintenance | ~530k |
| Sustained assets/day at which SFN premium equals full DIY build cost amortised | ~2M |
| Platform-wide tenant profile at 530k assets/day | 100 tenants averaging 5 300/day; or 500 tenants averaging 1 100/day |

For reference, a large enterprise DMS or national records-management program
typically processes 100 000 – 1 000 000 assets/day platform-wide across all
customers. Our projected scale is one to two orders of magnitude below the
break-even threshold.

### Extreme-scale crossover

At **100M+ coordination transitions per day sustained** (~6.7M assets/day):

- Step Functions Standard cost ~$1M/year in coordination alone
- DIY cost ~$150k/year AWS + ~$250k/year dedicated coordination team = ~$400k/year
- Net savings ~$600k/year favouring DIY

This scale is not projected for our customer segment within a 5-year horizon.

---

## Recommendation

**Adopt AWS Step Functions as the saga orchestration engine for magiq-media.**

Specifically:

1. **AssetIngestionSaga → Step Functions Standard.** Duration exceeds Express
   5-minute limit; volume is well below break-even.
2. **DocumentSigningSaga → Step Functions Standard.** 14-day lifecycle
   mandates Standard; volume is negligible for cost.
3. **CollectionArchiveCascade → Step Functions Standard parent + Express
   children via Distributed Map.** Per-tenant `MaxConcurrency` replaces the
   hand-coded fan-out budget.
4. **FolderArchiveCascade → Step Functions Standard parent + Express children
   via Distributed Map.** Same shape as collection cascade; bounded at 500
   folders.

Execution-name convention: `{tenantId}#{correlationId}`. One state machine per
saga type per AWS account per region. Tenant scoping enforced via IAM condition
on execution-name prefix.

Existing Lambdas continue to run the activities (no new compute pool). The
`TimeoutScanner` host is renamed `MaintenanceScanner`, its saga passes are
removed, and its four non-saga passes (upload expiry, registration overdue,
retention reconciliation, quarantine-move retry) remain.

---

## Revisit Criteria

Set one CloudWatch alarm now and stop actively considering the decision until
it fires:

- **Metric:** sustained platform-wide asset ingest per day, 7-day trailing
  average
- **Threshold:** 300 000 assets/day (two-thirds of the cost break-even
  threshold)
- **Action if it fires:** revisit the cost math with real production data;
  evaluate whether AssetIngestionSaga specifically warrants migration to a DIY
  substrate

**Additional automatic escalation triggers (regardless of alarm):**

- Sustained `ExecutionThrottled` &gt;1% of `ExecutionsStarted` for one week
- Any tenant requires on-premises deployment
- Any saga design requires &gt;25 000 history events per execution
- Any saga design requires &gt;1 year execution lifespan

**Sagas that would never migrate, even at extreme scale:**

- **DocumentSigningSaga** — volume is nil in absolute terms; Standard workflow
  duration and durable timers are the design requirement, not the constraint.
- **Cascade sagas** — Distributed Map's per-iteration concurrency is not
  practically reproducible under DIY without rebuilding much of what Step
  Functions provides.

Only **AssetIngestionSaga** is a realistic migration candidate under any future
scenario.

---

## Portability Rules — Keeping the Door Open

The design must observe these invariants so that a future migration of any
individual saga back to DIY is a coordinator swap rather than a rewrite:

1. **Payload = identifiers only.** State passed between workflow states carries
   `{tenantId, aggregateId, expectedVersion, correlationId, runId}` and nothing
   domain-shaped. Activities load aggregates from the event store. Works
   identically under Step Functions and under DIY.

2. **Saga = pure orchestration, zero business logic.** Every retry decision,
   every guard, every outcome computed by the aggregate. Coordinator only
   sequences activity invocations and waits for outcomes.

3. **Activity idempotency on aggregate version + attempt number.** Every
   command handler is idempotent by its aggregate's version and attempt number.
   Both substrates deliver at-least-once; both need the same guards.

4. **External integration via events.** Webhooks land, dispatch a command,
   emit a domain event; the coordinator picks up the event. No coordinator
   feature is used that a DIY substrate could not mimic with correlation ids on
   aggregates.

5. **Fan-out via bounded per-tenant concurrency.** Under Step Functions this is
   `MaxConcurrency` on Distributed Map. Under DIY it is the semaphore +
   per-tenant budget already specified. Same semantics, different mechanism.

6. **Every state machine has an equivalent DIY translation stated at ADR-write
   time.** Not built — just stated. If AssetIngestion ever migrates, the ASL
   definition maps to `{state, awaiting, timeoutAt, attemptNumber}` with named
   saga transitions. Migration is mechanical.

These six rules are captured as invariants in the umbrella ADR
(`docs/adrs/saga-orchestration-engine.md`) so that any future saga design or
refactor preserves the migration option at zero ongoing cost.

---

## Migration Roadmap — Spec-Side Work

Because no production traffic currently runs through the sagas, the migration
is purely a spec + implementation effort. There is no data cutover, no
dual-stack window, no drain period, no feature flag.

### Phase 1 — Umbrella ADR

**Deliverable:** `docs/adrs/saga-orchestration-engine.md`

**Contents:**

- Context and problem statement
- Decision: Step Functions
- Engine selection: Standard vs Express per saga
- Multi-tenancy strategy: execution-name convention
- Activity execution model: reuse existing Lambdas
- State machine inventory:
  - `magiq-media-asset-ingestion` (Standard)
  - `magiq-media-document-signing` (Standard)
  - `magiq-media-collection-archive-cascade` (Standard parent, Express children)
  - `magiq-media-folder-archive-cascade` (Standard parent, Express children)
- Payload contract: identifiers only, activities load state
- Portability rules (the six invariants above)
- Consequences
- Rejected alternatives: Temporal, Azure Durable Functions, continuing SQS+DDB

**Estimated time:** one iteration of `/spec-audit-next`.

### Phase 2 — Rewrite saga specs against Step Functions primitives

**Deliverables:**

- `docs/spec/contexts/Processing/sagas/assetingestionsaga.md` — rewritten as an
  Amazon States Language state machine definition with state / task / retry /
  timeout / catch semantics
- `docs/spec/contexts/DocumentSigning/sagas/documentsigningsaga.md` — same
- `docs/spec/contexts/Catalog/sagas/archive-fan-out.md` — rewritten as two
  state machine definitions using Distributed Map
- `docs/spec/shared/saga-patterns.md` — rewritten around Step Functions
  primitives; MaintenanceScanner section retained for the four non-saga passes

Semantic behaviour preserved; coordination primitives replaced.

**Estimated time:** three to four iterations.

### Phase 3 — Sweep affected shared specs

**Deliverables:**

- `docs/spec/shared/event-store-and-messaging.md` — drop `media-sagas` from
  DynamoDB tables inventory; drop `SagaTimeoutIndex` from GSI inventory;
  simplify Queue Topology
- `docs/spec/architecture/system-architecture.md` — update Queues section;
  update Lambda Hosts section (rename `SagaOrchestrator` and
  `SagaOrchestrator.DocumentSigning` hosts to Step Functions activity workers)
- `docs/spec/shared/operations.md` — update Poison-Message Policy (Step
  Functions failure states replace DLQ semantics for coordination; DLQ still
  applies to activity Lambda queues)
- `CLAUDE.md` — update § Stack (add Step Functions), § Hosts (rename saga
  hosts), § Known deferred/partial work (state machines specified but not
  deployed)

**Estimated time:** two iterations.

### Phase 4 — Revisit closed audit findings

**Deliverable:** re-evaluate each of the following against the new substrate.
Most close as "resolved by saga-orchestration-engine ADR"; some become
`platform-gap` awaiting Step Functions IaC delivery.

Findings to revisit: F007, F022, F028, F029, F030, F031, F032, F034, F035,
F074, F076, F080, F086, F104.

**Estimated time:** one iteration.

### Phase 5 — Close F033

**Deliverable:** update `docs/spec/contexts/Processing/sagas/assetingestionsaga.md`
so that the validation phase becomes an ASL `Task` state with `TimeoutSeconds:
900` and `Retry: [{ ErrorEquals: [TransientError], MaxAttempts: 3,
IntervalSeconds: 60, BackoffRate: 2 }]`. The divergent-branch guard on the
Asset aggregate (`FailAssetProcessing(ValidationTimeout)` refuses when
`ValidationOutcome = Passed`) is added to `asset.write-model.md` regardless of
substrate.

**Estimated time:** falls out of Phase 2; no separate iteration required.

### Phase 6 — Record platform-gap entries in CLAUDE.md

**Deliverable:** § Known deferred/partial work entries for:

- The four state machine definitions (specified but not deployed as CDK
  constructs in `cdk-magiq-media`)
- Step Functions client integration in `aspnetcore-platform` (task-token
  callback helpers, execution-name conventions, activity worker registration)

**Estimated time:** one iteration.

**Total estimated spec-side effort:** 8–10 `/spec-audit-next` iterations,
tracked through the same audit workflow that surfaces coordination findings
today.

---

## What the Spec Will Look Like After Migration

### Before (DIY, current spec)

```
Trigger event → SQS queue → Lambda handler → load saga row from media-sagas
  → check status guard → apply transition → save saga row with ConditionExpression on Version
  → dispatch outbound command → publish event → return

Timer expiry: TimeoutScanner (Lambda, 5-min schedule) → query SagaTimeoutIndex
  → dispatch compensation command → new event → saga handler picks up
```

Each saga file describes: State Table, Transition Table, Timeout Table, Idempotency,
Compensation, DLQ policy, Manual Intervention Runbook. Roughly 300–500 lines
per saga. Every field, transition, and timeout precisely specified because it
is code we write.

### After (Step Functions, target spec)

```
Trigger event → EventBridge rule → StartExecution on magiq-media-asset-ingestion
  → state machine runs:
    - Validate (Task: invoke validation Lambda, Retry policy on TransientError, Timeout 900s)
    - CheckValidationOutcome (Choice: Passed → Process, Failed → RecordFailure, VirusDetected → RecordInfection)
    - Process (Task: invoke processing Lambda, Retry policy, Timeout per profile)
    - RecordActive (Task: invoke aggregate command)
  → execution completes; history retained 90 days
```

Each saga file describes: State machine ASL definition, activity mappings, IAM
role, execution-name convention, retry policies, error handlers. Roughly 100–200
lines per saga. Retry, timeout, and compensation semantics are engine-provided
and stated declaratively rather than as prose specification of hand-coded logic.

The 17 audit findings that traced to DIY coordination primitives no longer have
surfaces to attach to.

### Concrete example — DocumentSigningSaga three-phase clock

**Current spec (excerpt from `documentsigningsaga.md`):**

- 200 lines describing envelope budget, signing budget, signed-asset budget,
  release retry clock, their config keys, defaults, ranges, expiry behaviours,
  scanner passes, transition table entries, persisted fields
  (`TimeoutAt`, `NextReleaseAttemptAt`, `SignedAssetAlerted`,
  `ReconciliationRequestedAt`), compensating command dispatches, third-attempt
  strand semantics, DLQ redrive procedures.

**Target spec:**

- A state machine with four `Wait` states (one per phase), each with its own
  configured duration, followed by a `Task` state that dispatches the
  reconcile/expire/retry command
- A `Retry` block on the release task with `MaxAttempts: 3`, `BackoffRate: 2`,
  and a `Catch` that dispatches `StrandSigningSession`
- One `WaitForTaskToken` on the signed-asset write-back, with the token
  correlated via EventBridge rule matching `SignedAssetId`
- Approximately 60 lines of ASL and 30 lines of prose

The engine owns the retry counter, the backoff schedule, the timer precision,
the resume path, and the "already past state" idempotency. The spec states the
policy declaratively.

---

## Approvals Required

- [ ] Platform architecture — engine selection and cost model
- [ ] Engineering leadership — Phase 2–6 spec effort allocation
- [ ] Finance — coordination cost line item in year-one budget (~$14k p.a.
  worst case for year one)
- [ ] Security — IAM boundary review for cross-tenant execution-name scoping

## References

- Audit findings: `docs/review/spec-audit-2026-09-29/` — index and per-finding
  files listed in the executive summary
- Current saga spec: `docs/spec/contexts/Processing/sagas/assetingestionsaga.md`,
  `docs/spec/contexts/DocumentSigning/sagas/documentsigningsaga.md`,
  `docs/spec/contexts/Catalog/sagas/archive-fan-out.md`
- Shared patterns: `docs/spec/shared/saga-patterns.md`
- AWS Step Functions pricing: <https://aws.amazon.com/step-functions/pricing/>
- AWS Step Functions quotas: <https://docs.aws.amazon.com/step-functions/latest/dg/limits-overview.html>

---

## Change Log

| Date | Author | Change |
|---|---|---|
| 2026-09-30 | Chase Ramone (drafted with Claude) | Initial recommendation |
