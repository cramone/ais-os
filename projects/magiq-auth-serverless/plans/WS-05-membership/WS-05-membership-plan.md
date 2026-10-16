---
id: MAS-006
type: plan
project: magiq-auth-serverless
workstream: WS-05-membership
repo: magiq-auth-serverless
tags: [membership, tenant-member, roles, erasure-cascade]
consumes: []
blocked-by-external: []
status: blocked
branches: []
created: 2026-10-15
---

# WS-05 — Membership

User ↔ tenant association, per-tenant roles. First erasure-cascade consumer. First `MemberAssigned` admin-flag monitor.

Spec:
- `docs/spec/contexts/Membership/README.md`
- `docs/spec/contexts/Membership/aggregates/TenantMember/*.md`
- ADR-014 invitation accept membership flow

## Session invocation

> Picking up WS-05 (plan MAS-006). TenantMember aggregate — bridges Identity and Tenant. Introduces erasure-cascade worker pattern + `MemberAssigned.AssignedAsTenantAdmin` monitor alarm.

## Phase 0 — Scaffold
- [ ] `scripts/new-module.ps1 -Name Membership -Aggregate TenantMember -Type auth.tenant-member`

## Phase 1 — Domain
- [ ] `TenantMember` aggregate: `LoginId` per tenant, admin flag, lockout, dissociation
- [ ] `(TenantId, LoginId)` reservation
- [ ] Invariant: last-admin cannot dissociate (`MEMBERSHIP_LAST_TENANT_ADMIN`)

## Phase 2 — Commands + handlers
- [ ] `AssignMember`, `PromoteMember`, `DemoteMember`, `DissociateMember`, `GrantRole`, `SetRoles`
- [ ] Invitation accept flow per ADR-014

## Phase 3 — Projections
- [ ] By-user + by-tenant projections per `tenantmember.read-model.md`

## Phase 4 — Erasure cascade worker
- [ ] `Membership.ErasureCascade` — consume `UserErasedIntegration`, delete membership rows, emit `UserErasedByMembershipIntegration`

## Phase 5 — Hosts
- [ ] `Membership.Admin` — `/platform/tenants/{tenantId}/members/**`
- [ ] `Membership.Reads` — `/me/memberships`
- [ ] `Membership.Projector`
- [ ] `Membership.ErasureCascade`

## Phase 6 — Tests
- [ ] Scenarios in `tenantmember.scenarios.md`
- [ ] Last-admin dissociation rejection
- [ ] Erasure cascade integration
- [ ] Admin-flag alarm fires on `AssignedAsTenantAdmin = true`

## Phase 7 — Deploy + validate

## Exit criteria

- All scenarios green
- Erasure cascade E2E green with WS-04
- Admin-flag alarm wired

## Session log

- 2026-10-15: plan drafted
