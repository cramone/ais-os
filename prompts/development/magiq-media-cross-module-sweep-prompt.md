# Prompt — Fresh Cross-Module Impact Sweep (all modules, code-first)

> Paste everything below the line into a fresh Claude (Cowork) session for the
> **magiq-media** project. It independently re-derives the cross-module (seam)
> defects across the whole bounded context from code and spec — it does **not**
> start from the existing per-module or cross-module reviews. Their conclusions
> are used only as a final diff, after your own are formed.

---

You are a Principal Domain Architect for **magiq-media** (C# .NET 8, DDD / CQRS /
event sourcing, EDA + sagas, AWS-native). Review the **seams between modules** as
an event-driven distributed system and report every defect that makes one module
break, mislead, or fail to react to another. Work from **code and spec first-hand**.
Treat the existing reviews as unseen until the final step — the goal is a second
opinion that does not inherit their blind spots.

## What is in scope

Only **cross-module** behaviour — the wiring between bounded-context modules:
- integration events published on `media-integration-events` and who (should) consume them;
- domain events on `media-domain-events` that cross a projector/saga boundary;
- **command dispatch across a module boundary** (a consumer in one module dispatching a command that mutates another);
- **shared write-side reference/ACL/counter models** one module maintains and another reads (e.g. hierarchy counters, capability/state refs, profile-default refs, registration refs);
- **sagas / process managers** and timeout/compensation coverage;
- the **SNS/SQS/DLQ topology and filter policies** that decide whether an event actually reaches its consumer.

Out of scope: intra-aggregate internals, projector field bugs, validators,
response-DTO shape — anything whose blast radius stays inside one module and never
changes what another module receives or does.

## The five failure classes to hunt for

Classify every finding as exactly one:
1. **Missing subscription** — event published but no module consumes it though one should; or a consumer exists in code but the SNS filter policy / bridge registration never delivers it.
2. **Event not emitted** — a consumer (or a needed reaction) exists, but the producing module never publishes the event that would drive it (no mapper entry, no route registration, or only published from a host that can't publish).
3. **Mishandled event** — a consumer exists but swallows the command `Result`, ACKs on transient faults (no DLQ path), sources `TenantId` from the payload body instead of the SNS message attribute, is non-idempotent under redelivery/reorder, or is unbounded/non-checkpointed.
4. **Bad event design → wrong downstream action** — the event fires in the wrong state or with a payload that makes the consumer do the wrong thing (spurious/duplicate emissions, empty-but-required fields, an irreversible downstream effect triggered without the upstream guard that should precede it).
5. **Invalid cross-module flow** — following a choreography end-to-end reaches an inconsistent, stuck, or unrecoverable state (a saga trigger never published, a fan-out that hard-mutates children irreversibly, a resurrection-on-reorder, a permanent-DLQ hop).

## Method — triangulate every seam from all three sides

The defects live where these three disagree. For **each** integration event, verify:
- **(A) Producer contract** — is there a mapper entry (`*IntegrationEventMapper*` / per-module `*.Contracts/Events/**`) that emits it, and from a host that can actually publish it in production? Note the `[MessageType]` routing string.
- **(B) Consumer bridge** — is a handler registered (`hosts/EventConsumers/ConsumerRegistrations.AddIntegrationEventMessageHandlers`, or the relevant worker/saga host), and does that handler inspect the command `Result` and source tenant correctly?
- **(C) Transport/filter** — does the CDK SNS subscription **filter policy** actually let this `[MessageType]` through to that consumer's queue, and does every queue have a DLQ? (`cdk-magiq-media/lib/**` — SNS topics, SQS queues, subscriptions, filter policies, event-source mappings.)

A seam is only healthy when A, B, and C all agree. Flag every A/B/C mismatch:
event consumed in code but filtered out at SNS; event allowed by the filter but with
no bridged handler; event mapped but published only from a host with no message bus;
handler bridged but no producer.

## Where to read (pointers, not conclusions)

Repos: app code `D:\source\github\magiq-media`; deploy topology
`D:\source\github\cdk-magiq-media`; platform publish/consume mechanism
`D:\source\github\aspnetcore-platform`; spec/ADRs under
`D:\source\github\magiq-media\docs\`. Read each repo's `CLAUDE.md` first.

- **Modules** (`src/modules/**`): `AssetManagement`, `Catalog`
  (Collection / Folder / MediaItem / MediaProfile), `ChangeRequests`, `Metadata`,
  `Processing`, `Registration`, `DocumentSigning`. For each, read
  `*.Contracts/Events/**`, `IntegrationEvents/{Publishing/Mappers,Consuming/Handlers}/**`,
  and any `*ReferenceProjector` / counter-maintaining handler.
- **Hosts** (`src/hosts/**`): `Api`, `EventConsumers`
  (`ConsumerRegistrations`, `IntegrationEventMessageHandler`, `Function`),
  `ProcessingWorker`, `Projectors.ReadModel`, `Projectors.Search`,
  `SagaOrchestrator`, `SagaOrchestrator.DocumentSigning`, `TimeoutScanner`.
  Check which hosts register the platform message bus / SNS publishers.
- **Sagas** (`src/shared/Media.Shared.Infrastructure/{Sagas,Messaging}/**` +
  saga hosts): saga definitions, correlation routing, state-store concurrency,
  and TimeoutScanner coverage per saga.
- **Spec/ADRs**: `docs/spec/architecture/**`, `docs/spec/shared/{api-conventions,
  error-catalog,security-scenarios}.md`, per-aggregate `*.write-model.md` event
  tables, and ADRs on the event bus, integration-event publisher, hierarchy
  invariants, and persistence/eventing — for what the seams are *supposed* to do.
- **Platform SDK**: the integration-event publishing pipeline / outbox in
  `aspnetcore-platform` — enough to judge whether dual-write / outbox / bus
  registration is correct, not a full SDK review.

## Rules

- **Do not read the existing reviews** in `docs/reviews/` until the final step.
- Spot-check depth: read enough code to confirm each seam from all three sides.
  Cite `file:line` for every claim (which mapper, which registration, which CDK
  filter). If you can't confirm a side, say so and mark the finding provisional.
- Analysis only — no edits, no PRs.
- Multi-tenancy is non-negotiable: any seam that could cross tenants, or sources
  tenant from a payload body, is at least High.
- Prefer prose and tables over long bullet lists.

## Output — structured findings report (Markdown, for `docs/reviews/`)

1. **System integration summary** — the topology you derived (topics, queues, hosts,
   which module publishes/consumes what), and a one-paragraph production-readiness
   verdict. Counts of findings by failure class and by severity.

2. **Integration event catalogue** — one row per `media.*` event:
   `[MessageType]` · producer module · producing host · **route registered? (A)** ·
   **bridged consumer? (B)** · **SNS filter passes? (C)** · real consumer(s) ·
   ordering sensitivity · idempotency mechanism · seam status
   (ok / missing-sub / not-emitted / mishandled / bad-design / invalid-flow).

3. **Consumer map** — one row per consumer host/queue: subscribed events (SNS filter),
   command/projection dispatched → target module, `Result`-checked?, DLQ?, notes.

4. **Cross-module flow analysis** — trace each end-to-end choreography (asset
   ingestion, asset ⇄ catalog lifecycle, record-type → catalog, registration →
   catalog, media-item review → change-request, collection archive fan-out,
   profile publish → conformance, document-signing). For each, an ASCII flow and
   the exact hop where it breaks, with the wrong end state a real request reaches.

5. **Findings**, grouped by failure class, each with: a stable ID you assign,
   title, the A/B/C evidence (`file:line`), the concrete failure flow, target
   module(s), severity (Critical/High/Medium/Low + risk type: data-integrity /
   reliability / security / destructive), and recommended fix.

6. **Sequenced recommendations** — the changes in landing order, flagging pairs that
   must ship together (e.g. emit an event **and** add its consumer/filter) and
   prerequisites.

7. **Final step — diff against the existing reviews.** *Only now* read
   `docs/reviews/cross-module-integration-review.md` and the per-module reviews.
   Produce a short reconciliation: (a) findings you found that they missed, (b)
   findings they raised that you did **not** independently reproduce (and why —
   false positive, or a blind spot in your sweep), (c) any contradictions. Keep
   your independent findings as the body; this is an appendix.

Begin by deriving the topology from the CDK and host wiring, then walk every event
through the A/B/C triangulation.
