---
id: MAS-008
type: plan
project: magiq-auth-serverless
workstream: WS-07-token-issuance
repo: magiq-auth-serverless
tags: [token-issuance, oidc, oauth2, openiddict, kms-sign, signing-keys, hot-path]
consumes: []
blocked-by-external: []
status: blocked
branches: []
created: 2026-10-15
---

# WS-07 — TokenIssuance

OIDC/OAuth2 issuer. Hot path. OpenIddict runtime (ADR-005). KMS Sign per issued token. Signing-key rotation state machine. Non-ES `PersistedGrant` with TTL.

Spec:
- `docs/spec/contexts/TokenIssuance/README.md`
- `docs/spec/contexts/TokenIssuance/aggregates/PersistedGrant/*.md`
- `docs/spec/contexts/TokenIssuance/aggregates/SigningKeyMetadata/*.md`
- ADR-005 OpenIddict runtime
- ADR-018 multi-region MRK

## Session invocation

> Picking up WS-07 (plan MAS-008). TokenIssuance — hot path, provisioned concurrency 10 on writes, 2 on JWKS. Grants are non-ES (DynamoDB + TTL). Signing keys are ES. All token signing via KMS MRK; no local caching.

## Phase 0 — Scaffold + OpenIddict spike
- [ ] `scripts/new-module.ps1 -Name TokenIssuance`
- [ ] Spike OpenIddict integration with `ICommandDispatcher` + `Kms.Sign` adapter

## Phase 1 — Domain
- [ ] `SigningKeyMetadata` aggregate: `Pending → Active → Retiring → Retired` state machine
- [ ] `PersistedGrant` non-ES with TTL
- [ ] Snapshot cadence per `event-store-and-messaging.md`

## Phase 2 — Commands + handlers
- [ ] `IssueAuthorizationCode`, `ExchangeAuthorizationCode`, `IssueClientCredentialsToken`, `RefreshTokens`, `RevokeToken`, `InitiateDeviceAuthorization`, `Authorize`
- [ ] Signing-key lifecycle: `AnnounceSigningKey`, `ActivateSigningKey`, `RetireSigningKey`
- [ ] Refresh-token single-flight single-use with grace per ADR-005

## Phase 3 — KMS Sign integration
- [ ] Adapter calls `Kms.Sign` once per issued access token
- [ ] No `GetPublicKey` or `GenerateDataKeyPairWithoutPlaintext` patterns
- [ ] `KmsThrottleException` → high-severity page per `operations.md`

## Phase 4 — JWKS host
- [ ] `TokenIssuance.Jwks` — `/.well-known/openid-configuration`, `/.well-known/openid-configuration/jwks`, `/connect/userinfo`
- [ ] Multiple active `kid` during rotation
- [ ] CloudFront caching with sensible TTL

## Phase 5 — Outbox mode
- [ ] DynamoDB-Streams outbox for integration events on `/connect/token`
- [ ] Operator toggle inline ↔ outbox per alarm
- [ ] Semantics unchanged for consumers

## Phase 6 — Revoke-cascade worker
- [ ] `TokenIssuance.RevokeCascade` — consume `SessionRevokedIntegration`, `UserPasswordChangedIntegration` (skip when `SetByLegacyRehash = true`), `MemberDissociatedIntegration`, `UserSuspendedIntegration`
- [ ] Idempotent revoke-already-revoked = no-op

## Phase 7 — Erasure-cascade worker
- [ ] `TokenIssuance.ErasureCascade` — delete user grants, emit `UserErasedByTokenIssuanceIntegration`

## Phase 8 — Scheduler
- [ ] `TokenIssuance.Scheduler` — EventBridge key-rotation reminders

## Phase 9 — Hosts
- [ ] `TokenIssuance.Writes` — `/connect/token`, `/connect/authorize`, `/connect/deviceauthorization`, `/connect/revocation`, `/connect/introspect` — provisioned concurrency 10
- [ ] `TokenIssuance.Jwks` — provisioned concurrency 2
- [ ] `TokenIssuance.Projector`, `TokenIssuance.RevokeCascade`, `TokenIssuance.ErasureCascade`, `TokenIssuance.Scheduler`

## Phase 10 — Tests
- [ ] Scenarios in `persistedgrant.scenarios.md`
- [ ] Multiple-active `kid` discovery doc
- [ ] Refresh-token grace replay metric wired
- [ ] p99 under 500 ms on `/connect/token` on load profile

## Phase 11 — Deploy + validate
- [ ] Load test `/connect/token` under provisioned concurrency floor
- [ ] Validate KMS quota headroom
- [ ] Key rotation drill: Pending → Active → Retiring → Retired

## Exit criteria

- Discovery doc served with multi-kid during rotation
- p99 budget met on hot path
- KMS alarms wired
- Grace replay metric < 0.01

## Session log

- 2026-10-15: plan drafted
