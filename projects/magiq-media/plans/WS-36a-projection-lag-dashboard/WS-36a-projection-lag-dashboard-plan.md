---
id: MM-027
type: plan
project: magiq-media
workstream: WS-36a-projection-lag-dashboard
repo: cdk-magiq-media
tags: [cdk-magiq-media, infra, cloudwatch, projections]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — origin is docs/dependency-gaps/projections/INDEX.md#WS-36 (no gap file; row-tracked); no separate review document.
---

# WS-36a — Projection-lag CloudWatch dashboard (infra half)

**Target repo:** `cdk-magiq-media` — `D:\source\github\sprbrk-standard\mgq-magiq-media-infra`
**Depends on:** none
**Unblocks:** MM-047 (WS-36b — magiq-media projectors emit matching metric)

Dashboard first (empty graphs); magiq-media emits data in WS-36b.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media-infra`. Paste:

> Picking up WS-36a (plan MM-027). Plan at `Z:\claudia\magiq\projects\magiq-media\plans\WS-36a-projection-lag-dashboard\WS-36a-projection-lag-dashboard-plan.md`.
>
> Define metric contract: `MagiqMedia/Projections/Lag` with dimensions `aggregate_type`, `projector` (`ReadModel` | `Search`), unit seconds. Build CloudWatch dashboard `media-projection-lag` with row per projector, widget per aggregate type (p50/p99/max). Alarms on p99 lag.

## Phase 0 — Scope confirmation
- [ ] Metric name + dimensions pinned
- [ ] Spec review: `docs/dependency-gaps/projections/INDEX.md`

## Phase 1 — CloudWatch dashboard
- [ ] Create dashboard `media-projection-lag`
- [ ] Row per projector
- [ ] Widget per aggregate type (p50 / p99 / max)

## Phase 2 — Alarms
- [ ] Alarm on p99 lag > 30s (configurable per-env) for `ReadModel`
- [ ] Alarm on p99 lag > 60s for `Search`
- [ ] SNS topic for ops notifications

## Phase 3 — Deploy
- [ ] Deploy to `dev`
- [ ] Verify dashboard renders (empty until WS-36b)
- [ ] Document metric contract for WS-36b

## Phase 4 — Close
- [ ] projections/INDEX.md: WS-36 split — `WS-36a shipped`, `WS-36b open`
- [ ] INTEGRATION-BACKLOG: MM-047 (WS-36b) ready

## Session log
- 2026-10-08: plan drafted
- 2026-10-15: shipped on `spec/initial-alignment` in `cdk-magiq-media` (pending merge). One commit — `ProjectionLagDashboard` construct: dedicated `media-projection-lag` dashboard with row per projector (ReadModel, Search); each row carries a summary widget (MAX/p99/p50 across aggregate types) + a per-aggregate p99 series via CloudWatch metric search so new aggregates auto-appear. Two p99 alarms paging `media-alarms-pager` — ReadModel > 30 s and Search > 60 s, both across 3 consecutive 5-minute periods. Metric contract: `MagiqMedia/Projections::projection.lag_seconds` dims `aggregate_type` + `projector`. Removed the aggregate-less `media-projection-lag` alarm from `MetricsAlarms` (MM-080b) so alarms don't double-fire. MM-047 (WS-36b) flipped `new -> ready`.
