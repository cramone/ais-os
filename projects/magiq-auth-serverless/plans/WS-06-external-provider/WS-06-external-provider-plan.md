---
id: MAS-007
type: plan
project: magiq-auth-serverless
workstream: WS-06-external-provider
repo: magiq-auth-serverless
tags: [external-provider, oidc-federation, platform-scoped-encryption]
consumes: []
blocked-by-external: []
status: blocked
branches: []
created: 2026-10-15
---

# WS-06 — ExternalProvider

OIDC IdP configuration. Platform-scoped encryption for provider client secret. Dual-approval email-verification opt-out per ADR-015.

Spec:
- `docs/spec/contexts/ExternalProvider/README.md`
- `docs/spec/contexts/ExternalProvider/aggregates/ExternalProvider/*.md`
- ADR-010 external provider secret encryption
- ADR-015 dual-approval email-verification opt-out

## Session invocation

> Picking up WS-06 (plan MAS-007). ExternalProvider aggregate — platform-scoped encryption using `alias/auth/external-provider-secret`. Dual-approval email-verification opt-out emits security event.

## Phase 0 — Scaffold
- [ ] `scripts/new-module.ps1 -Name ExternalProvider -Aggregate ExternalProvider -Type auth.external-provider`

## Phase 1 — Domain
- [ ] Aggregate: `SchemaName`, authority, client_id, encrypted client secret, callback paths, email-claim mapping, scopes
- [ ] Snapshot cadence every 20 events (encrypted field)
- [ ] Dual-approver state for email-verification opt-out

## Phase 2 — Commands + handlers
- [ ] `RegisterProvider`, `UpdateProviderConfig`, `DisableProvider`, `RequestEmailVerificationOptOut`, `ApproveEmailVerificationOptOut`
- [ ] `ExternalProviderEmailVerificationDisabledIntegration` publishes to `auth-security-events`

## Phase 3 — Projections
- [ ] Platform read-model with ciphertext carried through; consumer decrypts at build time

## Phase 4 — Hosts
- [ ] `ExternalProvider.Admin` — `/platform/external-providers/**`
- [ ] `ExternalProvider.Reads`
- [ ] `ExternalProvider.Projector`

## Phase 5 — Tests
- [ ] Scenarios in `externalprovider.scenarios.md`
- [ ] Dual-approval happy path + rejection
- [ ] Secret round-trip via `alias/auth/external-provider-secret`

## Phase 6 — Deploy + validate

## Exit criteria

- All scenarios green
- Security event published on opt-out approve
- Projector carries ciphertext (no plaintext at rest)

## Session log

- 2026-10-15: plan drafted
