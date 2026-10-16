---
id: MAS-012
type: plan
project: magiq-auth-serverless
workstream: WS-11-audit
repo: magiq-auth-serverless
tags: [audit, legal-hold, merkle-chain, dlq-inventory]
consumes: []
blocked-by-external: []
status: blocked
branches: []
created: 2026-10-15
---

# WS-11 — Audit

Consumer-only context. Subscribes to `auth-domain-events` unfiltered. Builds hot read model + per-tenant per-day Merkle chain. `LegalHold` aggregate (ADR-023). Audit DLQ inventory with replay.

Spec:
- `docs/spec/contexts/Audit/README.md`
- `docs/dependency-gaps/platform-capabilities/F003-audit-chain-and-legal-hold.md`
- ADR-003 cold-storage projection
- ADR-006 audit storage tier selection
- ADR-023 audit chain + legal hold

## Session invocation

> Picking up WS-11 (plan MAS-012). Audit consumes every domain event. Writes to `auth-audit-events` + chain to `auth-audit-chain` + maintains retention state. Supports legal-hold aggregate blocking erasure.

## Phase 0 — Scaffold
- [ ] `scripts/new-module.ps1 -Name Audit`

## Phase 1 — Domain
- [ ] `LegalHold` aggregate — per-tenant tenant-wide or targeted hold
- [ ] Audit is a projection sink; no own aggregates besides `LegalHold`

## Phase 2 — Audit projector
- [ ] Consumes `auth-domain-events` unfiltered
- [ ] Writes canonical record to `auth-audit-events`
- [ ] Updates `auth-audit-retention-state` per date + tenant partition

## Phase 3 — Chain projector
- [ ] Per-tenant per-day Merkle leaf → counter → root per `auth-audit-chain` partition pattern
- [ ] Inclusion proof query

## Phase 4 — Legal hold integration
- [ ] On `LegalHoldApplied`, block erasure cascade for scope
- [ ] On `LegalHoldLifted`, resume

## Phase 5 — Erasure cascade (gated)
- [ ] `Audit.ErasureCascade` — purge only when no legal hold covers the user
- [ ] Emits `UserErasedByAuditIntegration` when complete

## Phase 6 — DLQ inventory
- [ ] `AuditDlqInventory` read endpoint
- [ ] `ReplayDlqMessage` command

## Phase 7 — Hosts
- [ ] `Audit.Reads` — `/platform/audit/**`, DLQ inventory
- [ ] `Audit.Projector` — SNS unfiltered
- [ ] `Audit.ErasureCascade`

## Phase 8 — Tests
- [ ] Chain integrity: ingest N events, verify root, request inclusion proof
- [ ] Legal-hold prevents erasure cascade; lift restores
- [ ] DLQ replay round-trip

## Phase 9 — Deploy + validate

## Exit criteria

- Chain verifies for 1-day window across all contexts
- Legal-hold integration gates erasure
- DLQ inventory + replay working

## Session log

- 2026-10-15: plan drafted
