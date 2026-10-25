---
id: MM-035
type: plan
project: magiq-media
workstream: WS-15b-originating-actor-populate
repo: magiq-media
tags: [magiq-media, actor, context, scanner, saga]
consumes: []
blocked-by-external: [MM-017]
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — magiq-media integration half of WS-15 F079.
---

# WS-15b — Populate `OriginatingActorId` on dispatched commands + `MaintenanceScanner` per-dispatch context

**Target repo:** `magiq-media`
**Depends on:** MM-017 (WS-15a SDK)
**User policy gate:** no magiq-media code change until all external deps ship.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-15b (plan MM-035). SDK (MM-017) ships `OriginatingActorId` on `MessageMetadata` + `IScannerExecutionContextFactory`.
>
> Audit handler sites that dispatch commands: populate `OriginatingActorId` on inner command's execution context (SDK default copies from outer; verify). Refactor `MaintenanceScanner` passes to open per-row context via `IScannerExecutionContextFactory.Create(tenantId, originatingActorId-from-row)`.
>
> PR to `develop`.

## Phase 0 — Scope confirmation
- [ ] Confirm MM-017 shipped
- [ ] Enumerate handler sites that dispatch inner commands (cross-aggregate flows)
- [ ] Enumerate `MaintenanceScanner` passes (upload expiry, registration-response overdue, retention reconciliation, reopen clear, retention-schedule deprecation, quarantine-move retry, erasure retry)

## Phase 1 — Handler-side populate
- [ ] Confirm SDK context-propagation copies `OriginatingActorId` through inner command dispatch (unit test)
- [ ] Any handler explicitly building command context: ensure `OriginatingActorId` set

## Phase 2 — MaintenanceScanner refactor
- [ ] Each pass loads rows with `OriginatingActorId` attribute (write path must populate — confirm per aggregate's event-sourced path writes it to read-model row)
- [ ] Open per-row context via factory
- [ ] Scoped per-dispatch (no bleed)

## Phase 3 — Tests
- [ ] Unit: handler-dispatched command carries originating actor forward
- [ ] Unit: scanner-pass dispatch carries originating-actor-from-row
- [ ] Integration: full saga flow — audit log at terminal step names originating human/system

## Phase 4 — Ship
- [ ] PR to `develop`

## Phase 5 — Close
- [ ] F079: shipped (full)
- [ ] INTEGRATION-BACKLOG: WS-15b → § Shipped
- [ ] Remove `Originating actor and scanner execution context not carried` bullet from `CLAUDE.md`

## Session log
- 2026-10-08: plan drafted (blocked on MM-017 + user policy)
