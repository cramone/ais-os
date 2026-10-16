---
id: MAS-011
type: plan
project: magiq-auth-serverless
workstream: WS-10-notification
repo: magiq-auth-serverless
tags: [notification, email, sms, templates, rate-limit, dispatch]
consumes: []
blocked-by-external: []
status: blocked
branches: []
created: 2026-10-15
---

# WS-10 — Notification

MessageTemplate, Notification (in-app), DispatchRecord. Per-recipient rate limit (ADR-022). Token-payload asymmetric encryption (ADR-007).

Spec:
- `docs/spec/contexts/Notification/README.md`
- `docs/spec/contexts/Notification/aggregates/*`
- `docs/dependency-gaps/platform-capabilities/F002-notification-rate-counter.md`
- ADR-007 token-payload encryption
- ADR-022 per-recipient rate limiter

## Session invocation

> Picking up WS-10 (plan MAS-011). MessageTemplate + Notification ES; DispatchRecord non-ES. Rate counters per `auth-notification-rate-counters` table with 2h TTL. Dispatch via SES + SMS adapters.

## Phase 0 — Scaffold
- [ ] `scripts/new-module.ps1 -Name Notification`

## Phase 1 — Domain
- [ ] `MessageTemplate` ES
- [ ] `Notification` ES (in-app banner)
- [ ] `DispatchRecord` non-ES

## Phase 2 — Commands + handlers
- [ ] `CreateTemplate`, `UpdateTemplate`, `QueueDispatch`, `PublishNotification`, `ExpireNotification`, `DismissNotification`
- [ ] Rate guard on `QueueDispatch` → emits `NotificationThrottled` when breached (ADR-022)
- [ ] Token-payload asymmetric encryption via `alias/auth/notification-payload-key` (ADR-007)

## Phase 3 — Projections
- [ ] In-app read-model per `notification.read-model.md`
- [ ] DispatchRecord projection

## Phase 4 — Dispatcher worker
- [ ] `Notification.Dispatcher` — consume `NotificationQueued` → SES / SMS adapter
- [ ] Idempotent on retry

## Phase 5 — Erasure cascade
- [ ] `Notification.ErasureCascade` — purge user-targeted notifications + dispatch records

## Phase 6 — Hosts
- [ ] `Notification.Admin` — `/platform/message-templates/**`, `/platform/email-accounts/**`
- [ ] `Notification.Reads` — `/me/notifications`, `/platform/notifications/**`
- [ ] `Notification.Projector`, `Notification.Dispatcher`, `Notification.ErasureCascade`

## Phase 7 — Tests
- [ ] Scenarios across all three aggregates
- [ ] Rate-limit happy + breach path emits `NotificationThrottled`
- [ ] Asymmetric token-payload round-trip

## Phase 8 — Deploy + validate

## Exit criteria

- All scenarios green
- SES + SMS adapters working in dev
- Rate counter TTL verified

## Session log

- 2026-10-15: plan drafted
