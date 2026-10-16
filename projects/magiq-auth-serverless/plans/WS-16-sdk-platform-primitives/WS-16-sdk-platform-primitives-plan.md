---
id: MAS-017
type: plan
project: magiq-auth-serverless
workstream: WS-16-sdk-platform-primitives
repo: magiq-auth-serverless + mgq-dotnet-platform
tags: [sdk, platform-primitives, cross-repo]
consumes: []
blocked-by-external: []
status: active
branches: []
created: 2026-10-16
---

# WS-16 — SDK platform primitives

Cross-repo workstream. SDK work lands in `Sprbrk-Standard/mgq-dotnet-platform`; `magiq-auth-serverless` picks up each phase via `Directory.Packages.props`.

**Gap audit outcome (2026-10-16):** two of the six MAS-001-identified gaps already resolved by existing SDK primitives.

| Gap | Status after audit |
|---|---|
| F004 envelope encryption | Open — build |
| F005 non-ES aggregate adapter | Open — build |
| F006 name reservation | **Resolved** — `Magiq.Platform.UniquenessRegistry` fulfils; consumer wiring per slice |
| F007 HMAC pseudonymizer | Open — build |
| F008 erasure orchestrator | Open — platform `Magiq.Platform.Erasure` is retry driver (ADR-002 model); ADR-020 bitmap orchestrator still missing |
| F009 inline publisher + outbox toggle | **Resolved** — `TransactionalOutboxCommandMiddleware` fulfils stronger invariant; spec amended to always-outbox |

Remaining SDK work in four phases below.

## Session invocation

> Picking up WS-16 (plan MAS-017). SDK platform primitives — four phases across `mgq-dotnet-platform`: envelope encryption (F004), non-ES aggregate adapter (F005), HMAC pseudonymizer (F007), erasure cascade orchestrator (F008). Each phase lands a NuGet bump + `Directory.Packages.props` update in `magiq-auth-serverless`.

## Phase 0 — Merge pending platform PRs
- [ ] `Sprbrk-Standard/mgq-dotnet-platform` PR `feature/chase/MAS-001-non-es-opt-out` (constraint #3 amend) → review + merge
- [ ] Confirm `main` clean + CI green

## Phase 1 — F004 envelope encryption
- [ ] `Magiq.Platform.Security.Envelope.Abstractions` project — `Encrypted<T>`, `IKekPoolClient`, `IPlatformScopedKmsClient`, `IEnvelopeDecryptor`
- [ ] Serialization: `{ "ciphertext": "<base64>", "kek_alias": "..." }` and `{ "ciphertext", "kms_alias" }`
- [ ] Field-level AAD binding: `sha256(field-name || scope-id)`
- [ ] KEK pool client — slot derivation `HASH(UserId) % 100`, alias `alias/auth/user-dek-kek-{Index:D3}`, `Kms.GenerateDataKey`
- [ ] Rehydration contract: one KMS `Decrypt` per aggregate load, local AES-256-GCM per field
- [ ] Snapshot support: wrapped DEK on snapshot row; one KMS call on snapshot rehydration
- [ ] Erasure tombstone `"[erased]"` when `EncryptedDek` null
- [ ] Multi-region MRK invariant preserved (ADR-018)
- [ ] Unit + integration tests (localstack KMS)
- [ ] NuGet bump → `Directory.Packages.props` update in `magiq-auth-serverless`
- [ ] F004 gap file → Resolved

## Phase 2 — F005 non-ES aggregate adapter
- [ ] `Magiq.Platform.WriteModel.StateStored.Abstractions` — `IStateStoredAggregate<TId>`, `IStateStoredRepository<T, TId>`, `RowVersion` convention
- [ ] DynamoDB adapter: `Load`, `SaveNew` (`attribute_not_exists`), `SaveTransition` (`RowVersion` + status conditional)
- [ ] TTL field convention (`ExpiresAt` → DynamoDB TTL attribute + 60s grace per `retention-and-disposition.md`)
- [ ] Streams-driven terminal-transition publisher template (TTL expiry → published terminal event via outbox)
- [ ] Domain-event emit on state transition (reuses `IDomainEventPublisher`)
- [ ] Unit + integration tests
- [ ] NuGet bump → `Directory.Packages.props` update
- [ ] F005 gap file → Resolved

## Phase 3 — F007 HMAC pseudonymizer
- [ ] `Magiq.Platform.Security.Pseudonymization.Abstractions` — `IPseudonymizer`, `ITenantSaltResolver`
- [ ] HMAC-SHA256 + double-HMAC APIs; constant-time comparison helper
- [ ] Tenant salt resolver with 15-minute Lambda-memory cache; Secrets Manager namespace `auth/tenant-erasure-salt/*`
- [ ] Salt-creation hook: tenant provisioning emits `CreateSecret` with 256-bit random; version retention enabled
- [ ] `TenantErasureSaltRecoverabilityCheck` probe primitive (reusable across sweepers)
- [ ] Infra templates in `mgq-magiq-auth-infra`: SCP + resource policy denying `PutSecretValue`/`UpdateSecret`/`RotateSecret`/`DeleteSecret`; CloudTrail metric-filter alarm
- [ ] Unit + integration tests (localstack Secrets Manager)
- [ ] NuGet bump → `Directory.Packages.props` update
- [ ] F007 gap file → Resolved

## Phase 4 — F008 erasure cascade orchestrator (ADR-020)
- [ ] Decide: extend `Magiq.Platform.Erasure` or fork new `Magiq.Platform.Erasure.Cascade` module (see F008 gap § Remediation options)
- [ ] `IErasureOrchestrator` — bitmap state, 24-hour settling window, `FinalizeUserErasure` command, `ForceImmediate` break-glass
- [ ] `ErasureCascadeConsumer<T>` base — idempotent "delete user-linked state + emit cascade-ack event"; wall-clock guard; DLQ P1 semantics
- [ ] `ERASURE_PROGRESS` DynamoDB schema + helpers
- [ ] Alarm templates: `ErasureCascadeStalled`, `ErasureCascadeForceCompleted`, `ErasureConsumerRunaway`, `Wedged` detector
- [ ] Unit + integration tests
- [ ] NuGet bump → `Directory.Packages.props` update
- [ ] F008 gap file → Resolved

## Exit criteria

- Four SDK primitives shipped + consumed in `magiq-auth-serverless`
- F004, F005, F007, F008 gap files all Resolved
- No open blocker for MAS-005 (Identity), MAS-007, MAS-008, MAS-009, MAS-010, MAS-011, MAS-012, MAS-013, MAS-014

## Session log

- 2026-10-16: plan drafted after Phase 0 audit of mgq-dotnet-platform found F006 + F009 already resolved; F008 primitive exists but for superseded ADR-002 model; scope narrowed to four phases.
