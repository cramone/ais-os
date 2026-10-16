---
id: MAS-010
type: plan
project: magiq-auth-serverless
workstream: WS-09-two-factor
repo: magiq-auth-serverless
tags: [two-factor, totp, trusted-device, challenge]
consumes: []
blocked-by-external: []
status: blocked
branches: []
created: 2026-10-15
---

# WS-09 — TwoFactor

Challenge state machine (non-ES, TTL). TrustedDevice (ES, snapshot every 10 events). TOTP shared secret envelope-encrypted (ADR-016).

Spec:
- `docs/spec/contexts/TwoFactor/README.md`
- `docs/spec/contexts/TwoFactor/aggregates/*`
- ADR-016 envelope encryption for TOTP shared secret
- ADR-001 ephemeral aggregates opt out of ES

## Session invocation

> Picking up WS-09 (plan MAS-010). Challenge non-ES, TrustedDevice ES. Mounted on `Authentication.Writes` host from WS-08.

## Phase 0 — Scaffold
- [ ] `scripts/new-module.ps1 -Name TwoFactor`

## Phase 1 — Domain
- [ ] `TwoFactorChallenge` non-ES with TTL (5–10 min)
- [ ] `TrustedDevice` ES keyed by `(UserId, IP + DeviceFingerprint)` with expiry
- [ ] TOTP shared secret encrypted via `Encrypted<string>` on `User` DEK

## Phase 2 — Commands + handlers
- [ ] `IssueChallenge`, `VerifyChallenge`, `LockChallenge`, `RecordTrustedDevice`, `ExpireTrustedDevice`
- [ ] Delivery adapter port (Authy / Email / TOTP) — infra, not aggregate

## Phase 3 — Projections
- [ ] TrustedDevice-by-user projection
- [ ] Challenge state projection

## Phase 4 — Workers
- [ ] `TwoFactor.Projector`
- [ ] `TwoFactor.RevokeCascade` — consume `UserPasswordChangedIntegration`, `SessionRevokedIntegration`
- [ ] `TwoFactor.ErasureCascade`

## Phase 5 — Hosts
- [ ] Three workers; no own HTTP host (routes on `Authentication.Writes`)

## Phase 6 — Tests
- [ ] Scenarios across TwoFactorChallenge and TrustedDevice
- [ ] TOTP enroll + verify round-trip under envelope encryption
- [ ] Trusted-device expiry

## Phase 7 — Deploy + validate

## Exit criteria

- All scenarios green
- Challenge TTL expiry works
- Trusted-device replay prevented after expiry

## Session log

- 2026-10-15: plan drafted
