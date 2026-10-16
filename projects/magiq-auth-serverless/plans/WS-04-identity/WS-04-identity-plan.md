---
id: MAS-005
type: plan
project: magiq-auth-serverless
workstream: WS-04-identity
repo: magiq-auth-serverless
tags: [identity, user, crypto-shredding, kek-pool, gdpr]
consumes: []
blocked-by-external: []
status: blocked
branches: []
created: 2026-10-15
---

# WS-04 — Identity

User aggregate. Introduces envelope encryption, per-user DEK + KEK pool, crypto-shredding for GDPR erasure, legacy password hash sunset.

Spec:
- `docs/spec/contexts/Identity/README.md`
- `docs/spec/contexts/Identity/aggregates/User/*.md`
- ADR-002 crypto-shredding
- ADR-013 verified-email requirement
- ADR-019 legacy password hash sunset
- ADR-020 envelope encryption with KEK pool

## Session invocation

> Picking up WS-04 (plan MAS-005). User aggregate — hot path for most downstream contexts. Introduces per-user DEK, KEK pool (`alias/auth/user-dek-kek-000..099`), `Encrypted<string>` on PII fields, crypto-shredding on erasure, Argon2id with legacy dual-verify sunset path.

## Phase 0 — Scaffold
- [ ] `scripts/new-module.ps1 -Name Identity -Aggregate User -Type auth.user`
- [ ] Confirm platform SDK provides `Encrypted<string>` wrapper + KMS wrapper; file gap in `mgq-dotnet-platform` if not

## Phase 1 — Domain
- [ ] `User` aggregate: profile (encrypted email, name, mobile), credentials, IP rules, 2FA toggle, external links
- [ ] `EncryptedDek` + `KekIndex = HASH(UserId) % 100`
- [ ] Password hash: Argon2id primary; legacy format tolerated on load
- [ ] Snapshot cadence every 50 events (ADR-002)

## Phase 2 — Commands + handlers
- [ ] `RegisterUser`, `ChangeEmail`, `ChangePassword`, `RequestPasswordReset`, `LinkExternalIdentity`, `UpdateIpRules`, `LockAccount`, `UnlockAccount`, `SuspendUser`, `EraseUser`
- [ ] Password rehash on login path emits `PasswordRehashed` (consumed by downstream to skip revoke per spec)
- [ ] Email uniqueness reservation (`USER_EMAIL_TAKEN`)

## Phase 3 — Erasure cascade orchestrator
- [ ] `Identity.ErasureOrchestrator` worker — tracks cascade bitmap
- [ ] On every `UserErasedBy<Context>Integration`, flip bit; when all set, emit `FinalizeUserErasure` → `UserDekDeleted`
- [ ] Wall-clock + stall alarms per `operations.md`

## Phase 4 — Projections
- [ ] `UserByEmail`, `UserById` projections per `user.read-model.md`
- [ ] Decrypt-at-projection (plaintext in read model, not per-request)

## Phase 5 — Hosts
- [ ] `Identity.Writes` — `/me/profile`, `/me/password`, `/me/email`, `/me/2fa-config`
- [ ] `Identity.Reads`
- [ ] `Identity.Admin` — `/platform/users/**`
- [ ] `Identity.Projector`
- [ ] `Identity.ErasureOrchestrator`

## Phase 6 — Tests
- [ ] Scenarios in `user.scenarios.md`
- [ ] Crypto-shred round-trip: encrypt → read → erase → tombstone `[erased]`
- [ ] Argon2id + legacy hash dual-verify
- [ ] Snapshot replay with encrypted fields
- [ ] Erasure cascade acknowledgement under partial completion

## Phase 7 — Deploy + validate

## Exit criteria

- All scenarios green
- GDPR erasure drill passes on dev
- KMS Decrypt metrics within budget
- `identity_credentials_legacy_algorithm_count` metric exposed

## Session log

- 2026-10-15: plan drafted
