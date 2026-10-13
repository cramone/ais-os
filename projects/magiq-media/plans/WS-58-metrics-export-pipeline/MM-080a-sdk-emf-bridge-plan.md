---
id: MM-080a
type: plan
project: magiq-media
workstream: WS-58a-sdk-emf-bridge
repo: aspnetcore-platform
tags: [aspnetcore-platform, sdk, metrics, observability, emf, cloudwatch]
consumes: []
blocked-by-external: []
status: shipped
branches: [feature/chase/MM-080a-WS-58a-sdk-emf-bridge]
pr: https://github.com/magiqsoftware/aspnetcore-platform/pull/45
merge-sha: 9abdfb04
shipped: 2026-10-12
created: 2026-10-12
split-from: WS-58 (parent superseded 2026-10-12)
adr: docs/adrs/metrics-export.md
exception: dependency-gap workstream — origin is docs/dependency-gaps/platform-capabilities/INDEX.md#WS-58a (row-tracked); decisions in `docs/adrs/metrics-export.md`.
---

# WS-58a — SDK EMF bridge

**Target repo:** `aspnetcore-platform`
**Depends on:** none (ADR `metrics-export.md` landed 2026-10-12)
**Unblocks:** MM-023e (outbox instrumentation), MM-047 (projection-lag metric), export of every SDK counter already shipped (MM-013 snapshot fallbacks, MM-014 concurrency retries, MM-019 gap-fill events, MM-023c outbox parked, MM-021 reservation refusals) — all currently measured but unexported

## Scope

Deliver the SDK bridge that writes `IMeterFactory` measurements as CloudWatch
EMF log records. One SDK ship, consumed by every host once wired (WS-58c).

### What ships
- `IMetricsListener` (or `MeterListener` subclass) that subscribes to a configured
  set of Meters, serialises measurements to EMF JSON, writes to `ILogger` or a
  configurable sink
- Meter-name → CloudWatch namespace mapping: `Magiq.Platform.<Module>` →
  `MagiqMedia/<Module>` (e.g. `Magiq.Platform.Messaging.Outbox` →
  `MagiqMedia/Messaging`)
- Standard dimensions injected on every measurement: `tenant.id`, `environment`
  — resolved from `IExecutionContext` + `IHostEnvironment` at measurement time
- Dimension-key tag mapping — Meter instrument tags flow through as EMF
  dimensions when their keys match the configured category-specific set
  (`message.type`, `aggregate.type`, `model.type`, `command.type`)
- `AddMagiqMetrics(this IServiceCollection)` composition entry point —
  registers the listener, meter name whitelist, dimension configuration, EMF sink
- `MagiqMetricsOptions` for namespace prefix, environment name, dimension
  allowlist, sink override

### Phases
- **Phase 0**: ADR landed (done). Confirm `System.Diagnostics.Metrics` listener
  shape works per-measurement (not batched) under Lambda freeze.
- **Phase 1**: `EmfMetricsListener` + `EmfRecord` JSON serialisation.
  Namespace mapping. Dimension injection from `IExecutionContext`.
- **Phase 2**: `AddMagiqMetrics` + `MagiqMetricsOptions`. Default dimension
  allowlist = tenant.id, environment, message.type, aggregate.type, model.type,
  command.type.
- **Phase 3**: Unit tests — EMF record shape, dimension injection, namespace
  mapping, counter + histogram + gauge instrument types, tenant.id null-safety.
- **Phase 4**: PR.

### Design notes
- No batching, no flush — one EMF record per `Record` call. Lambda-friendly.
- Keep the listener Meter-whitelist narrow — opt-in per Meter name to avoid
  accidental cardinality blow-up from unexpected consumers.
- EMF JSON schema: `_aws.CloudWatchMetrics` object with `Namespace`,
  `Dimensions`, `Metrics[]` (Name + Unit); flat properties for each dimension
  value + each metric value.

## Session log
- 2026-10-12: drafted after WS-58 ADR + split.
- 2026-10-12: shipped. PR #45 merged as `9abdfb04`.
  - **Delivered**: `Magiq.Platform.Metrics.Emf` project. `MagiqMetricsOptions` (namespace prefix, env, Meter whitelist, static dims, resolver). `EmfMetricsListener` wraps `MeterListener`, writes one EMF JSON record per measurement via `IEmfRecordSink`; supports long/double/int instruments; UCUM-ish unit mapping; null-tag skip; `TimeProvider`-stamped `_aws.Timestamp`. `DefaultNamespaceResolver` maps `Magiq.Platform.<Module>.*` → `MagiqMedia/<Module>`. `IEmfRecordSink` + default `ConsoleEmfRecordSink`. `AddMagiqMetrics` + `IMagiqMetricsStartup` marker materialises listener on first scope.
  - **9 unit tests + 220/220 non-integration suite green**.
  - **Trackers updated**: platform-capabilities/INDEX.md WS-58a moved to Shipped; WS-58b + WS-58c flipped `open` → `ready`. INTEGRATION-BACKLOG MM-080a moved to § Shipped; MM-080b + MM-080c flipped. Readiness 58 new / 17 ready / 18 shipped.
  - **Follow-ups**: MM-023e dep narrowed (now only blocked by MM-023d). Five pre-existing SDK counters (snapshot fallbacks, concurrency retries, projector gap-fill, outbox parked, tenant refusals) exportable once hosts wire WS-58c.
