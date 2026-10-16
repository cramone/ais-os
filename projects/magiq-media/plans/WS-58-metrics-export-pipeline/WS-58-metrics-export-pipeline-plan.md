---
id: MM-080
type: plan
project: magiq-media
workstream: WS-58-metrics-export-pipeline
repo: magiq-media
tags: [magiq-media, mgq-dotnet-platform, cdk-magiq-media, observability, metrics]
consumes: []
blocked-by-external: []
status: superseded
branches: []
created: 2026-10-08
superseded-by: [MM-080a (WS-58a SDK EMF bridge), MM-080b (WS-58b CDK dashboards + alarms), MM-080c (WS-58c host registration)]
adr: docs/adrs/metrics-export.md
exception: dependency-gap workstream — origin is docs/dependency-gaps/platform-capabilities/INDEX.md#WS-58 (no gap file; row-tracked). Decision-first parent: split 2026-10-12 into per-repo child workstreams after ADR landed.
---

# WS-58 — Metrics export pipeline

**Target repos:**
- the decision: `magiq-media` `docs/adrs/`
- implementation: `mgq-dotnet-platform`, `cdk-magiq-media`, and the magiq-media hosts

**Depends on:** none
**Unblocks:**
- MM-047 (WS-36b, projection-lag metric)
- every metric the spec names: `OutboxEntryParked`, `Catalog.ArchivedItemsWithActiveRegistrations`, `MediaErasurePending.*`, scanner-pass metrics in `operations.md`
- MM-013's `magiq.event_sourcing.snapshot.fallbacks` counter
**Sequencing:** the CDK child belongs in the "CDK plans last" group. The decision and the SDK child do not.

**Today:**
- The SDK has no `Meter`, `IMeterFactory` usage or OpenTelemetry metrics; `Observability/` is health checks only.
- The spec names CloudWatch metrics and their alarm thresholds, but nothing states how a metric leaves a host.

## Phase 0 — Decide the export mechanism (ADR)
- [ ] Options to weigh:
  - (a) OpenTelemetry SDK + OTLP to the ADOT Lambda collector layer, `awsemf` exporter → CloudWatch
  - (b) An in-process EMF exporter writing Embedded Metric Format to stdout → CloudWatch Logs
  - (c) `PutMetricData`
- [ ] Criteria: Lambda cold start and the per-invocation flush model (metrics must flush before freeze), cost, alarm support, local-dev story, X-Ray alignment
- [ ] Decide: CloudWatch namespace (e.g. `Magiq/Media`); how OTel instrument names (`magiq.event_sourcing.snapshot.fallbacks`) map to the spec's metric names; which tags become dimensions (bounded only)
- [ ] Write the ADR in `docs/adrs/`, and state the metric-emission rule in `operations.md` in spec terms
- [ ] Chase approves

## Phase 1 — Split into child workstreams
- [ ] Reserve the next unused `WS-NN` / `MM-NNN` for each child: SDK registration (`AddMagiqMetrics`: meters, exporter, flush), CDK (layer/config, IAM, namespace), magiq-media host wiring
- [ ] Mark this plan `superseded`; repoint MM-047's dependency to the child that delivers export

## Closing out

The plan's card moves to `superseded` once its children exist, or `done` if the decision proves no child work is needed. Chase's call.

## Session log
- 2026-10-08: plan drafted — the snapshot-fallback counter (MM-013 D7) is the platform's first metric, and the spec already names others with nothing to export them. Deciding the export path once, not per workstream.
- 2026-10-12: decisions landed via ADR `docs/adrs/metrics-export.md`:
  - Mechanism = **CloudWatch EMF** emitted via a bridge listener on `IMeterFactory`. Rejected OTel+ADOT (Lambda cold-start cost, no multi-cloud driver) and direct `PutMetricData` (sync AWS SDK on hot path).
  - Namespace = **`MagiqMedia/<Module>`** (e.g. `MagiqMedia/Catalog`, `MagiqMedia/Messaging`, `MagiqMedia/EventSourcing`). Env separation stays per-AWS-account.
  - Core dimensions on every metric: `tenant.id`, `environment`. Category-specific: `message.type`, `aggregate.type`, `model.type`, `command.type`.
  - Tenant cardinality fine at low-hundreds scale; revisit if thousands+.
  - Flush model = inline-write per measurement (no batching, no end-of-invocation flush needed; Lambda freeze preserves log data).
- 2026-10-12: split into children. MM-080a (SDK — EMF bridge, Meter conventions, `AddMagiqMetrics`), MM-080b (CDK — namespace, dashboards, alarms, IAM), MM-080c (hosts — per-Lambda registration). This plan → `superseded`.
