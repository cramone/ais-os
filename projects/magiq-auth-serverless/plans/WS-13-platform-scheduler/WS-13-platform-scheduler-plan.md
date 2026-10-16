---
id: MAS-014
type: plan
project: magiq-auth-serverless
workstream: WS-13-platform-scheduler
repo: magiq-auth-serverless
tags: [scheduler, eventbridge, cross-context, probes]
consumes: []
blocked-by-external: []
status: blocked
branches: []
created: 2026-10-15
---

# WS-13 — Platform scheduler

Cross-context periodic probes and sweepers. Not scoped to any single context.

Spec:
- `docs/spec/architecture/hosts.md § Platform`
- `docs/spec/shared/operations.md § Alarms` (recoverability check reference)
- ADR-009 tenant erasure salt invariants

## Session invocation

> Picking up WS-13 (plan MAS-014). Single Lambda, EventBridge-triggered. Hosts `TenantErasureSaltRecoverabilityCheck` monthly probe + idle-session sweeper + other cross-context sweepers.

## Phase 0 — Scaffold
- [ ] `src/hosts/Platform.Scheduler/`
- [ ] No module — host-only project

## Phase 1 — Probes
- [ ] `TenantErasureSaltRecoverabilityCheck` monthly
- [ ] Idle-session sweeper
- [ ] Erasure consumer runaway (4h wall clock) check

## Phase 2 — Scheduling
- [ ] EventBridge Scheduler rules per probe
- [ ] Each probe emits a command through `ICommandDispatcher` with `RequestingActor = "Scheduler:<ProbeName>"`

## Phase 3 — Alarms
- [ ] Probe failure page per `operations.md`
- [ ] Metrics exposed per probe

## Phase 4 — Tests
- [ ] Simulate missing salt → recoverability probe pages
- [ ] Simulate idle session past TTL → sweeper revokes

## Phase 5 — Deploy + validate

## Exit criteria

- Probes fire on schedule
- Alarms wire to pager
- Metrics visible in CloudWatch

## Session log

- 2026-10-15: plan drafted
