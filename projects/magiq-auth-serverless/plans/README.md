# Plans — magiq-auth-serverless

Implementation plans. One folder per workstream; the folder name is the stable link. The spec is the acceptance criteria — every workstream realises specific files under `D:\source\github\cramone\magiq-auth-serverless\docs\spec\`.

Ids are `MAS-<nnn>`, monotonic, never reused.

## Live

| Id | Workstream | Plan | Status | Depends on |
|---|---|---|---|---|
| MAS-001 | `WS-00-platform-foundation` | [plan](./WS-00-platform-foundation/WS-00-platform-foundation-plan.md) | active | none |
| MAS-002 | `WS-01-tenant-walking-skeleton` | [plan](./WS-01-tenant-walking-skeleton/WS-01-tenant-walking-skeleton-plan.md) | blocked | MAS-001 |
| MAS-003 | `WS-02-application` | [plan](./WS-02-application/WS-02-application-plan.md) | blocked | MAS-002 |
| MAS-004 | `WS-03-api-client` | [plan](./WS-03-api-client/WS-03-api-client-plan.md) | blocked | MAS-002 |
| MAS-005 | `WS-04-identity` | [plan](./WS-04-identity/WS-04-identity-plan.md) | blocked | MAS-002, MAS-017 Phase 1 + 4 (F004, F008) |
| MAS-006 | `WS-05-membership` | [plan](./WS-05-membership/WS-05-membership-plan.md) | blocked | MAS-005 |
| MAS-007 | `WS-06-external-provider` | [plan](./WS-06-external-provider/WS-06-external-provider-plan.md) | blocked | MAS-005, MAS-017 Phase 1 + 2 (F004, F005) |
| MAS-008 | `WS-07-token-issuance` | [plan](./WS-07-token-issuance/WS-07-token-issuance-plan.md) | blocked | MAS-003, MAS-004, MAS-006, MAS-017 Phase 2 (F005) |
| MAS-009 | `WS-08-authentication` | [plan](./WS-08-authentication/WS-08-authentication-plan.md) | blocked | MAS-008, MAS-017 Phase 2 + 3 (F005, F007) |
| MAS-010 | `WS-09-two-factor` | [plan](./WS-09-two-factor/WS-09-two-factor-plan.md) | blocked | MAS-009, MAS-017 Phase 1 + 2 (F004, F005) |
| MAS-011 | `WS-10-notification` | [plan](./WS-10-notification/WS-10-notification-plan.md) | blocked | MAS-005, MAS-017 Phase 1 + 2 (F004, F005) |
| MAS-012 | `WS-11-audit` | [plan](./WS-11-audit/WS-11-audit-plan.md) | blocked | MAS-002, MAS-017 Phase 3 (F007) |
| MAS-013 | `WS-12-media` | [plan](./WS-12-media/WS-12-media-plan.md) | blocked | MAS-001, MAS-017 Phase 2 (F005) |
| MAS-014 | `WS-13-platform-scheduler` | [plan](./WS-13-platform-scheduler/WS-13-platform-scheduler-plan.md) | blocked | MAS-002, MAS-017 Phase 3 (F007) |
| MAS-015 | `WS-14-legacy-facade` | [plan](./WS-14-legacy-facade/WS-14-legacy-facade-plan.md) | parked | MAS-008, MAS-009 |
| MAS-016 | `WS-15-spec-coverage-harness` | [plan](./WS-15-spec-coverage-harness/WS-15-spec-coverage-harness-plan.md) | blocked | MAS-002 |
| MAS-017 | `WS-16-sdk-platform-primitives` | [plan](./WS-16-sdk-platform-primitives/WS-16-sdk-platform-primitives-plan.md) | active | none (cross-repo — `mgq-dotnet-platform` PR for constraint #3 pending merge) |

## Build order rationale

Phase 0 — platform foundation — one time, blocks everything else.

Phase 1 — Tenant — walking skeleton. Smallest aggregate, no user coupling, exercises every pattern (event store, SNS, projector, admin host, reservation). Learnings feed `_template`.

Phase 2 — fan out per `docs/dependency-gaps/migration-from-legacy/F001-bounded-context-rename.md § Suggested build order`:

1. Application + ApiClient (parallel, independent)
2. Identity (introduces crypto-shredding, KEK pool)
3. Membership (first cross-context erasure cascade consumer)
4. ExternalProvider (platform-scoped encryption)
5. TokenIssuance (OpenIddict + KMS Sign hot path)
6. Authentication + TwoFactor (hot path, revoke cascade, cold flush)
7. Notification (rate counters, SES/SMS)
8. Audit (SNS unfiltered + Merkle chain)
9. Media (quarantine + GuardDuty)
10. Platform scheduler (cross-context probes)

Legacy facade (MAS-015) is parked. Scoped only when a cutover timeline exists.

## Conventions

- **One plan per workstream.** Pick next unblocked; finish before starting another.
- **Spec is contract.** Each plan cites the spec files it realises.
- **Divergence = finding, not stealth edit.** Raise a `docs/review/spec-audit-<date>/` finding; do not weaken the spec.
- **Platform gaps go to `mgq-dotnet-platform`.** Any capability needed by two contexts belongs in the SDK.
- **Status.** `active` | `blocked` | `parked` | `done`. `blocked` is derived from unmet dependencies.
- **Done is Chase's call** — not when the last box is ticked.

## Archived

none yet.
