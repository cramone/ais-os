---
id: MM-080b
type: plan
project: magiq-media
workstream: WS-58b-cdk-dashboards-alarms
repo: cdk-magiq-media
tags: [cdk-magiq-media, metrics, observability, cloudwatch, dashboards, alarms]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-12
split-from: WS-58 (parent superseded 2026-10-12)
depends-on: MM-080a (SDK EMF bridge)
adr: docs/adrs/metrics-export.md
exception: dependency-gap workstream — origin is docs/dependency-gaps/platform-capabilities/INDEX.md#WS-58b (row-tracked).
---

# WS-58b — CDK dashboards + alarms

**Target repo:** `cdk-magiq-media`
**Depends on:** MM-080a (SDK bridge publishes the metric namespace)

## Scope
- CDK constructs for CloudWatch dashboards keyed by Meter namespace (one per
  `MagiqMedia/<Module>`)
- CloudWatch alarms per spec threshold (`OutboxEntryParked > 0 pages`,
  `MediaErasurePending.*`, `Catalog.ArchivedItemsWithActiveRegistrations > 0`,
  projection-lag thresholds, scanner-pass thresholds in `operations.md`)
- IAM for each Lambda host to write to CloudWatch Logs (EMF path already has
  this via default Lambda role; alarms side is read-only)
- Per-env parametrisation (dev / qa / staging / prod) via existing config files
- Alarm SNS topic for pager routing

### Phases
- Phase 0: enumerate every spec-named metric + alarm threshold
- Phase 1: dashboard construct per module
- Phase 2: alarm construct per metric
- Phase 3: pager SNS topic + subscription
- Phase 4: PR

## Session log
- 2026-10-12: drafted after WS-58 split.
- 2026-10-15: shipped on `spec/initial-alignment` in `cdk-magiq-media` (pending merge). Two commits: (1) `MetricsDashboards` construct — five dashboards keyed by Meter namespace (MagiqMedia-{Messaging, EventSourcing, Projections, Catalog, Tenancy}) with widgets per spec-named metric; (2) `MetricsAlarms` construct — six alarms (`ArchivedItemsWithActiveRegistrations`, `GovernanceGroupUnresolved`, three `MediaErasurePending.*`, `projection.lag_seconds`) all paging `media-alarms-pager`. `OutboxEntryParked` alarm stays on OutboxRelay construct (MM-023d). Pager topic (`media-alarms-pager`) already shipped in MM-031 scaffolding; MM-080b scope narrowed accordingly. Alarms whose emitters are pending (F041 erasure, WS-36b lag) carry `TreatMissingData.NOT_BREACHING`. Nothing emits yet — WS-58c host registration remaining.
