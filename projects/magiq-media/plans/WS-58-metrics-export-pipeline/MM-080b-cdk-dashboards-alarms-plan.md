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
