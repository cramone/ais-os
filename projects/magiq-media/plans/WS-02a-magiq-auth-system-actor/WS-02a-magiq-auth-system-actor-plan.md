---
id: MM-025
type: plan
project: magiq-media
workstream: WS-02a-magiq-auth-system-actor
repo: magiq-auth
tags: [magiq-auth, security, auth, token-mint]
consumes: []
blocked-by-external: []
status: new
branches: []
created: 2026-10-08
exception: dependency-gap workstream — origin is docs/dependency-gaps/security/F024-system-actor-issuance.md and INDEX.md#WS-02; no separate review document.
---

# WS-02a — `actor_type = System` restricted to platform-owned integration clients

**Target repo:** `magiq-auth` — `D:\source\github\magiqsoftware\magiq-auth` (no `CLAUDE.md` — read `README.md` + `src/` tree first)
**Depends on:** none
**Unblocks:** MM-033 (WS-02b — defence-in-depth on magiq-media; may be minimal/no-op)

Pre-staging-gate security. Today magiq-auth emits `actor_type = System` for any client-credentials client; a tenant admin provisioning an M2M client can mint `System` and reach signing callback routes.

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\magiqsoftware\magiq-auth`. Paste:

> Picking up WS-02a (plan MM-025). Plan at `Z:\claudia\magiq\projects\magiq-media\plans\WS-02a-magiq-auth-system-actor\WS-02a-magiq-auth-system-actor-plan.md`. Gap: `D:\source\github\sprbrk-standard\mgq-magiq-media\docs\dependency-gaps\security\F024-system-actor-issuance.md`.
>
> magiq-auth has no CLAUDE.md — read `README.md`, `src/` first. Identify token-mint pipeline. Add `ClientClass` on client record: `PlatformIntegration | TenantProvisioned`. Migration classifies existing clients (SigningAdapter, RegistrationAdapter → Platform; everything else → Tenant). Token mint: Platform may emit `actor_type = System`; Tenant always emits `User`. No scope grants System to Tenant clients.
>
> Pre-staging security — coordinate with magiq-auth owner on token-mint rollout. PR to magiq-auth per its branching convention.

## Phase 0 — Prereq investigation
- [ ] magiq-auth has no CLAUDE.md — read `README.md`, `src/` tree
- [ ] Identify token-mint pipeline + where `actor_type` claim is populated
- [ ] Enumerate existing clients: platform-owned integration vs tenant-provisioned
- [ ] Confirm no breaking downstream usage of today's over-broad `System` issuance

## Phase 1 — Client classification
- [ ] Add `ClientClass` column on client record: `PlatformIntegration | TenantProvisioned`
- [ ] Migration: classify existing clients
  - Platform-owned seed (SigningAdapter, RegistrationAdapter, any other platform integration) → `PlatformIntegration`
  - Tenant-provisioned → `TenantProvisioned`
- [ ] Admin API/UI (if present) to classify new clients; default new client → `TenantProvisioned`

## Phase 2 — Gate `actor_type = System` emission at mint
- [ ] Token mint reads `ClientClass`
- [ ] `PlatformIntegration` → may emit `actor_type = System`
- [ ] `TenantProvisioned` → always `actor_type = User`
- [ ] No scope grants `System`; no claim-mapper override

## Phase 3 — Audit tooling
- [ ] Report: clients emitting `System` → confirms set == platform-owned
- [ ] CI check / scheduled report flagging any `TenantProvisioned` with `System` emission (expected zero)
- [ ] Metric: `token_mint_system_count` with `client_class` dimension

## Phase 4 — Tests
- [ ] Unit: `PlatformIntegration` client → `actor_type = System`
- [ ] Unit: `TenantProvisioned` client → `actor_type = User` (regardless of scope)
- [ ] Unit: migration classification correct
- [ ] Integration (if feasible): token round-trip → claim respected

## Phase 5 — Ship
- [ ] Coordinate with magiq-auth owner (token-mint behaviour change)
- [ ] PR to magiq-auth
- [ ] Communicate change to magiq-media + other downstream BCs

## Phase 6 — Close
- [ ] F024: `status: shipped`, `pr: <link>`, `shipped: <date>`
- [ ] security/INDEX.md: WS-02 split — `WS-02a shipped`, `WS-02b open or n/a`
- [ ] INTEGRATION-BACKLOG: MM-033 (WS-02b) `Dep status: shipped`

## Session log
- 2026-10-08: plan drafted
