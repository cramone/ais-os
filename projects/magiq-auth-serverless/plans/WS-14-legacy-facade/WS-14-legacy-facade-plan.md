---
id: MAS-015
type: plan
project: magiq-auth-serverless
workstream: WS-14-legacy-facade
repo: magiq-auth-serverless
tags: [legacy, compat, facade, deferred]
consumes: []
blocked-by-external: []
status: parked
branches: []
created: 2026-10-15
---

# WS-14 — Legacy API compatibility facade

**Parked.** Scope only when a cutover timeline exists and new system reaches feature parity on the surfaces named below.

Supports:
- `/auth/v1/*` and `/auth/v2/*` admin REST (consumed by MAGIQ Auth+ and current admin UI)
- Legacy IDS4 route shapes already preserved by TokenIssuance (`/connect/*`, `/.well-known/*`) — no facade needed
- Web MVC + cookie SSO replay for Enterprise / Performance / Documents

Spec reference:
- `docs/legacy-spec/05-http-api.md` — target surface
- `docs/dependency-gaps/migration-from-legacy/F001-bounded-context-rename.md`
- Future: `docs/dependency-gaps/migration-from-legacy/F002-legacy-api-compat-facade.md` (to open when scheduled)

## Session invocation

> Picking up WS-14 (plan MAS-015). Legacy compat facade. Only start if cutover plan requires per-surface overlap with existing MAGIQ Auth. Facade is adapter-only — no new aggregates or events.

## Phase 0 — Scope confirmation
- [ ] Identify which legacy surfaces must keep working at cutover
- [ ] Confirm MAGIQ Auth+ migration path and date
- [ ] Confirm Enterprise / Performance / Documents cookie-replay replacement
- [ ] File `F002-legacy-api-compat-facade.md` gap

## Phase 1 — Facade host
- [ ] `src/hosts/LegacyApi/` — mounts legacy paths
- [ ] Per-module `*.LegacyAdapters/` translating legacy DTOs to new commands/queries

## Phase 2 — v1 + v2 admin REST
- [ ] Route tables mapping to new `ICommandDispatcher` commands
- [ ] Preserve legacy response shapes (`GenericApiResult<T>` envelope, `ApacheHashForLogin` typo field)

## Phase 3 — Legacy cookie adapter
- [ ] `LegacyCookieAdapter` mints `session-<customer>`, `perf-session`, `ticket` cookies from new Membership + Tenant read models
- [ ] Isolated outside domain per F001 rule

## Phase 4 — Password hash dual-verify path
- [ ] Confirm WS-04 (MAS-005) implementation handles legacy Rfc2898/SHA1 on verify
- [ ] Rehash emits `PasswordRehashed`; downstream consumers skip revoke per `SetByLegacyRehash = true`

## Phase 5 — Rollout flags
- [ ] Per-surface feature flag
- [ ] DNS / CloudFront routing override to switch legacy → facade per surface

## Phase 6 — Sunset metric
- [ ] Per-route call-rate metric
- [ ] Alarm when rate drops to zero for 30 consecutive days → candidate for retirement

## Phase 7 — Decommission trigger
- [ ] Each surface closes individually when consumer migrated

## Exit criteria

- All consuming systems migrated off facade
- Last route retired
- Host decommissioned

## Session log

- 2026-10-15: plan drafted (parked)
