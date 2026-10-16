---
id: MAS-009
type: plan
project: magiq-auth-serverless
workstream: WS-08-authentication
repo: magiq-auth-serverless
tags: [authentication, login, session, lockout, cold-flush, hot-path]
consumes: []
blocked-by-external: []
status: blocked
branches: []
created: 2026-10-15
---

# WS-08 — Authentication

Login flows, session lifecycle, per-user lockout. Hot-path writes (prov. concurrency 5). `LoginAttempt` ES with 90-day cold-flush to S3. `Session` + `UserAuthenticationState` non-ES.

Spec:
- `docs/spec/contexts/Authentication/README.md`
- `docs/spec/contexts/Authentication/aggregates/*`
- ADR-003 LoginAttempt retention + cold-storage projection
- ADR-019 legacy password hash sunset

## Session invocation

> Picking up WS-08 (plan MAS-009). Authentication hot path. Hosts public write surface (login, 2fa, external callback, password reset). TwoFactor + ExternalProvider command handlers mounted via `ICommandDispatcher` reference.

## Phase 0 — Scaffold
- [ ] `scripts/new-module.ps1 -Name Authentication`
- [ ] Three aggregates: LoginAttempt, Session, UserAuthenticationState

## Phase 1 — Domain
- [ ] `LoginAttempt` ES per attempt
- [ ] `Session` non-ES with TTL
- [ ] `UserAuthenticationState` non-ES (lockout counters)

## Phase 2 — Commands + handlers
- [ ] `SubmitCredentials`, `IssueChallenge` (hot-path inline for 2FA), `CompleteLogin`, `RevokeSession`, `HandleExternalCallback`, `RequestPasswordReset`, `ApplyPasswordReset`
- [ ] Argon2id verify + legacy dual-verify + rehash emits `PasswordRehashed`
- [ ] 100 ms floor on `/auth/login` per `operations.md`

## Phase 3 — Projections
- [ ] Session + login-history read models per `*.read-model.md`

## Phase 4 — Workers
- [ ] `Authentication.Projector`
- [ ] `Authentication.RevokeCascade` — consume `UserPasswordChangedIntegration`, `MemberDissociatedIntegration`, `UserSuspendedIntegration`
- [ ] `Authentication.ErasureCascade`
- [ ] `Authentication.ColdFlush` — EventBridge daily, flushes aged `LoginAttempt` to S3 + `auth-cold-storage-ledger` (ADR-003)

## Phase 5 — Hosts
- [ ] `Authentication.Writes` — `/auth/login*`, `/auth/2fa/**`, `/auth/external/**`, `/auth/password-reset:*` — provisioned concurrency 5
- [ ] `Authentication.Reads` — `/me/sessions`, `/me/login-history`
- [ ] 4 workers above

## Phase 6 — Tests
- [ ] Scenarios in `loginattempt.scenarios.md`, `session.scenarios.md`, `userauthenticationstate.scenarios.md`
- [ ] Cold-flush dry-run: aged events flushed, ledger confirms before deletion
- [ ] Credential-stuffing alarm: `WriteThrottleEvents > 10 / 1 min` on `auth-user-authentication-state`
- [ ] p99 under 800 ms on `/auth/login`

## Phase 7 — Deploy + validate

## Exit criteria

- All scenarios green
- Cold-flush round-trip verified
- Legacy rehash path verified
- Hot-path budget met

## Session log

- 2026-10-15: plan drafted
