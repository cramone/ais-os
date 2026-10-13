---
id: MM-080c
type: plan
project: magiq-media
workstream: WS-58c-host-registration
repo: magiq-media
tags: [magiq-media, hosts, metrics, observability, policy-gated]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-12
split-from: WS-58 (parent superseded 2026-10-12)
depends-on: MM-080a (SDK EMF bridge)
policy-gated: true
adr: docs/adrs/metrics-export.md
exception: dependency-gap workstream — origin is docs/dependency-gaps/platform-capabilities/INDEX.md#WS-58c (row-tracked).
---

# WS-58c — Host registration

**Target repo:** `magiq-media`
**Depends on:** MM-080a (SDK bridge)
**User-policy-gated:** magiq-media touch forbidden until all Phase A SDK + infra
deps ship.

## Scope

One-line DI registration (`AddMagiqMetrics`) on every deployable Lambda host:
- `Api`
- `QueryApi`
- `Projectors.ReadModel`
- `Projectors.Search`
- `EventConsumers`
- `ProcessingWorker`
- `SagaOrchestrator` + `SagaOrchestrator.DocumentSigning`
- `MaintenanceScanner`

### Phases
- Phase 1: wire `AddMagiqMetrics` into each host's `ServiceCollection`
- Phase 2: confirm EMF records flow out of CloudWatch Logs → metric namespace
  on dev account
- Phase 3: dev smoke test — hit a route that touches a counter (e.g. a save that
  parks an outbox row), confirm CloudWatch surfaces the dimension set
- Phase 4: PR

## Session log
- 2026-10-12: drafted after WS-58 split.
