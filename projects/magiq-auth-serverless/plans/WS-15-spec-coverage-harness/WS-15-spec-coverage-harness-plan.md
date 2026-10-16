---
id: MAS-016
type: plan
project: magiq-auth-serverless
workstream: WS-15-spec-coverage-harness
repo: magiq-auth-serverless
tags: [tooling, spec-drift, ci-gate]
consumes: []
blocked-by-external: []
status: blocked
branches: []
created: 2026-10-15
---

# WS-15 — Spec coverage harness

Script + CI gate. Per module, cross-checks the module's artefacts against the module's spec files and reports gaps.

Blocks on MAS-002 (Tenant walking skeleton) so coverage patterns can be grounded against a real module before being codified.

## Session invocation

> Picking up WS-15 (plan MAS-016). Build `scripts/spec-coverage.ps1 -Module <X>` + wire as CI gate. Baseline against the Tenant module from MAS-002.

## Phase 0 — Baseline Tenant
- [ ] Enumerate Tenant spec sections: scenarios, commands in `*.api.md`, events in `*.write-model.md`, projections in `*.read-model.md`
- [ ] Enumerate Tenant code artefacts: integration test methods, command handlers, event records, projector methods
- [ ] Confirm the 1:1 heuristic that matches names across spec and code

## Phase 1 — Harness script
- [ ] `scripts/spec-coverage.ps1 -Module <X>` reads the module's spec files + walks the module code tree
- [ ] Reports:
  - Missing scenarios (spec scenario with no test)
  - Missing handlers (spec command with no handler)
  - Missing events (spec event with no record)
  - Missing projections (spec projection with no projector method)
  - Orphan code (handler/event/test with no spec hit)
- [ ] Exit 1 on any gap

## Phase 2 — CI wiring
- [ ] GitHub Actions job runs harness per module in parallel
- [ ] Report comment on PR

## Phase 3 — Validation
- [ ] Run against every module shipped so far — every one green
- [ ] Introduce a deliberate drift (delete a handler) → confirm harness fails
- [ ] Introduce a deliberate orphan → confirm harness fails

## Exit criteria

- Harness green on every live module
- CI gate active
- Documented in CLAUDE.md § Spec coverage harness

## Session log

- 2026-10-15: plan drafted
