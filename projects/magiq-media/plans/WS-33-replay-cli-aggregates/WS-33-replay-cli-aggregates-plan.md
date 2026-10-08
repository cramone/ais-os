---
id: MM-067
type: plan
project: magiq-media
workstream: WS-33-replay-cli-aggregates
repo: magiq-media
tags: [magiq-media, projections, cli, tooling]
consumes: []
blocked-by-external: [MM-077]
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — pure magiq-media; origin is docs/dependency-gaps/projections/INDEX.md#WS-33.
---

# WS-33 — Projection replay CLI expand to all eleven aggregates

**Target repo:** `magiq-media`
**User policy gate:** no magiq-media change until all external deps ship.
**External prerequisite:** MM-077 (WS-55) — the CDK seeds `read-model-metadata`. Until that is deployed, no row exists in any CDK-owned environment, and `ProjectionReplay rotate` cannot start: `BeginReplayAsync` is a conditional `UpdateItem` against the missing row. Replay strategies added here are reachable through `rotate` only once WS-55 is live. Spec: `system-architecture.md` § Seeding.

Current CLI covers 6 of 11: `asset`, `media-item`, `folder`, `collection`, `media-profile`, `record-type`. Add remaining five.

## Session invocation

> Picking up WS-33 (plan MM-067). Expand `src/tools/ProjectionReplay` to cover all 11 aggregates. Remaining five per `docs/spec/shared/consistency-model.md` § 1: `processing-job`, `change-request`, `retention-schedule`, `registration`, `document-signing-session`. Each gets a replay strategy. Confirm MM-077 (WS-55) is deployed before starting.

## Phase 0 — Scope confirmation
- [x] ~~Enumerate 11 aggregates per spec~~ — `consistency-model.md` § 1: `asset`, `processing-job`, `media-item`, `folder`, `collection`, `media-profile`, `change-request`, `record-type`, `retention-schedule`, `registration`, `document-signing-session`
- [ ] Current CLI coverage
- [x] ~~Confirm remaining five~~ — `processing-job`, `change-request`, `retention-schedule`, `registration`, `document-signing-session` (earlier draft listed `signing-session` and omitted `retention-schedule`)
- [ ] MM-077 (WS-55) deployed: `read-model-metadata` holds one row per manifest table in the target environment

## Phase 1 — Add replay strategies
- [ ] Per aggregate: replay strategy class + CLI verb
- [ ] Reuse base pattern from existing six

## Phase 2 — Tests
- [ ] Per aggregate: replay rebuilds read model from events
- [ ] Idempotent across runs
- [ ] `rotate` end to end in dev (CDK-owned tables, `EnableMigrations = false`): rotation finds the CDK-seeded row, starts, flips, rolls back

## Phase 3 — Ship
- [ ] PR to `develop`

## Phase 4 — Close
- [ ] projections/INDEX.md: WS-33 → § Shipped
- [ ] Remove `Projection replay CLI covers 6 of 11 aggregates` bullet from `CLAUDE.md`

## Session log
- 2026-10-08: plan drafted (blocked by user policy)
- 2026-10-08: added External prerequisite on the SDK `RotationMetadataSeeder` (aspnetcore-platform `feature/guid-projection-rotation`); corrected the remaining-five aggregate list against `consistency-model.md` § 1.
- 2026-10-08: prerequisite moved from the SDK startup seeder to MM-077 (WS-55, CDK seeding) after Chase ruled hosts must not seed; `blocked-by-external: [MM-077]`.
