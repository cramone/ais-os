---
id: MM-068
type: plan
project: magiq-media
workstream: WS-34-rebuild-index-cli
repo: magiq-media
tags: [magiq-media, projections, cli, tooling, index]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — pure magiq-media; origin is docs/dependency-gaps/projections/INDEX.md#WS-34.
---

# WS-34 — `projections rebuild-index` CLI verb

**Target repo:** `magiq-media`
**User policy gate:** no magiq-media change until all external deps ship.
**Unblocks:** MM-069 (WS-35 membership indexes), MM-070 (WS-37 OpenSearch), MM-045 (WS-38b backfill)

Spec: `rebuild-index --index <name> --tenant <name>` rebuilds each write-side reference index per tenant.

**Not affected by `read-model-metadata` seeding.** `rebuild-index` targets unversioned tables (`schemaVersion: null`), which have no metadata row and are not in the manifest the CDK seeds from (MM-077, WS-55). The one link: `consistency-model.md` § 1 sends a tenant that cannot bear the projector pause to `rotate` instead, and `rotate` only works once WS-55 is deployed — see MM-067 (WS-33) External prerequisite.

## Session invocation

> Picking up WS-34 (plan MM-068). Add `projections rebuild-index --index <name> --tenant <name>` CLI verb. Per-tenant clear + mapper-driven replay. Pause consuming handler per tenant for duration. Cross-module via replaying producing aggregate's stream through `*DomainEventMapper`.

## Phase 0 — Scope confirmation
- [ ] Read `docs/spec/shared/consistency-model.md` § rebuild-index
- [ ] Enumerate write-side reference indexes
- [ ] Enumerate `*DomainEventMapper` instances

## Phase 1 — CLI verb
- [ ] `src/tools/ProjectionReplay`: `rebuild-index` command
- [ ] Flags: `--index <name>`, `--tenant <name>`

## Phase 2 — Per-tenant pause
- [ ] Pause flag on consuming handler (per tenant)
- [ ] Flag cleared after rebuild

## Phase 3 — Rebuild
- [ ] Same-module: replay owning module's domain events
- [ ] Cross-module: replay producing aggregate's stream through `*DomainEventMapper` into consuming handler under same `SourceVersion`/`EventVersion` merge

## Phase 4 — Tests
- [ ] Unit: pause flag honored
- [ ] Integration: rebuild on a test tenant produces identical index to live

## Phase 5 — Ship
- [ ] PR to `develop`

## Phase 6 — Close
- [ ] projections/INDEX.md: WS-34 → § Shipped
- [ ] Remove `projections rebuild-index not built` bullet from `CLAUDE.md`

## Session log
- 2026-10-08: plan drafted (blocked by user policy)
- 2026-10-08: noted relationship to the SDK rotation-seeder fix — none for `rebuild-index` itself; the `rotate` fallback path depends on it.
- 2026-10-08: seeding note repointed from the SDK startup seeder to MM-077 (WS-55).
