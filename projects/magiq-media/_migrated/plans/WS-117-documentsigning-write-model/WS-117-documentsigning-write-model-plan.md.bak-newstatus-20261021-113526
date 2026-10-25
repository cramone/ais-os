---
id: MM-157
type: plan
project: magiq-media
workstream: WS-117-documentsigning-write-model
repo: magiq-media
tags: [magiq-media, documentsigning, signingsession, write-model, aggregate, saga, snapshot, hmac]
consumes: []
blocked-by-external: []
status: active
branches: []
created: 2026-10-16
depends-on: 'MM-154, WS-57'
breaking-change: Internal
source: alignment-sweep-2026-10-15 cell DocumentSigningSession × write-model
---

# WS-117 — DocumentSigningSession write-model: full aggregate build

**Target repo:** `magiq-media`
**Depends on:** MM-154, WS-57

## Problem

Spec names 16 DocumentSigningSession domain events. Aggregate class absent per CLAUDE.md modules table "specified, no aggregate class exists". Full aggregate build required.

Missing domain events (16):

| event | emitting command / trigger |
|---|---|
| `SigningSessionInitiated` | `InitiateSigningSessionCommand` (MM-155) |
| `SigningEnvelopeCreated` | adapter callback via SecuredSigning webhook |
| `SigningEnvelopeSent` | adapter callback |
| `SignerCompleted` | adapter callback per signer |
| `SignerDeclined` | adapter callback per signer |
| `SigningCompleted` | all signers completed |
| `SigningEnvelopeVoided` | provider voided envelope |
| `SigningSessionCancelled` | `CancelSigningSessionCommand` |
| `SigningSessionStranded` | timeout; MaintenanceScanner |
| `SigningSessionTimedOut` | timeout window elapsed |
| `SigningSessionReconciliationRequested` | `ForceUnlinkSigningSessionCommand` (reconcile) |
| `SigningSessionReleaseFailed` | aggregate release path error |
| `SigningSessionReleaseRetryRequested` | retry scheduled |
| `SignedAssetRecorded` | Catalog saga returns `SignedAssetId` |
| `SignedAssetRecordingFailed` | Catalog saga reports failure |
| `SigningSessionPersonalDataErased` | `EraseSigningSessionPersonalDataCommand` |

Missing commands (6 user-facing + N adapter-driven):

- `InitiateSigningSessionCommand` (server-side `SigningSessionId` mint)
- `CancelSigningSessionCommand`
- `ForceUnlinkSigningSessionCommand` (reconcile)
- `EraseSigningSessionPersonalDataCommand`
- `RecordSigningEnvelopeEventCommand` (dispatched by webhook handler per adapter event type)
- `MarkSigningSessionStrandedCommand` (scanner-dispatched)

Supporting work:

- `DocumentSigningSession` aggregate (`EventSourced<DocumentSigningSession, SigningSessionId>`, `ITenantScoped`, `[AggregateType("media.signing-session")]`).
- `SigningSessionId` strongly typed; **minted server-side** at initiate (never caller-supplied) per `document-signing.md` ADR anti-oracle.
- `SigningSessionStatus` enum ordinals pinned (`Initiated=1`, `EnvelopeCreated=2`, `EnvelopeSent=3`, `AwaitingSigners=4`, `Completed=5`, `Cancelled=6`, `Stranded=7`, `TimedOut=8`, `Voided=9`).
- `Signer` value object `{ SignerId, Email, Role, Status, DecidedAt? }`; `SignerStatus` enum ordinals pinned.
- `SigningSessionSnapshot` `[Snapshot(Revision = 1)]`.
- `ISigningSessionRepository` DynamoDB event-store repository.
- `SecuredSigningAdapter` outbound client (initiate envelope + resend) stub for host wiring.
- Webhook event classifier maps provider event types → aggregate methods.

## What the spec requires

- `InitiateSigningSessionCommand(TenantId, MediaItemId, Signers, EnvelopeMetadata)` — mints new `SigningSessionId` server-side; refuses `MediaItemNotCheckedOutByCaller 422`, `SigningCapabilityNotEnabled 422`, `InvalidSignerList 422`, `SigningSessionInProgress 409` (MM-154).
- `DocumentSigningSession.Initiate(mintedId, mediaItemId, signers, metadata)` factory emits `SigningSessionInitiated` + writes `media-signing-envelope-lookup` row (MM-156) atomically or via post-save projector.
- Lifecycle methods (`CreateEnvelope`, `SendEnvelope`, `MarkSignerCompleted`, `MarkSignerDeclined`, `CompleteSession`, `VoidEnvelope`, `Cancel`, `MarkStranded`, `MarkTimedOut`, `RequestReconciliation`, `ReleaseFailed`, `RequestReleaseRetry`, `RecordSignedAsset`, `MarkSignedAssetRecordingFailed`, `ErasePersonalData`) each guard valid-from-status + emit matching domain event.
- `RecordSigningCompletedCommand` refuses `SignersNotAllCompleted 422` when any signer still `Pending`.
- Webhook adapter integration — SecuredSigning adapter dispatches `RecordSigningEnvelopeEventCommand` with classified provider event; aggregate maps to internal lifecycle methods.

## Scope boundary

- Aggregate + commands + handlers + domain events + value-objects + repository + snapshot.
- Error codes → MM-154.
- No SNS wire (MM-156 integration-events cell clean per spec).
- HTTP endpoints → MM-155.
- Read-model (incl. envelope-lookup + webhook-dedup) → MM-156.
- Catalog saga coordination (`UnlinkSigningSession`, `ForceReleaseCheckout`, `RecordSignedAsset`) consumed by Catalog's existing MediaItem signing-session handler flow; cross-aggregate integration event wiring unchanged (events are intra-BC).

## Wire-visibility

- Internal — SigningSessionId server-side-mint IS wire-visible but captured by MM-155 (route behavior). No SNS types published (MM-156 clean).

## Session invocation

Open a new Claude Code session, `cd` into `D:\source\github\sprbrk-standard\mgq-magiq-media`. Paste:

> Picking up WS-117 (plan MM-157). MM-154 + WS-57 must be reachable. SigningSessionId is server-minted — never caller-supplied. Siblings MM-155/156 land after this write-model core (routes dispatch commands; MM-156 projector consumes `SigningSessionInitiated` to populate envelope-lookup).

## Phase 0 — Scope confirmation

- [ ] MM-154 constants reachable
- [ ] WS-57 snapshot revision mechanism available

## Phase 1 — Value objects

- [ ] `SigningSessionId` strong id (server-minted UUID v7)
- [ ] `SigningSessionStatus` enum with pinned ordinals (Initiated=1..Voided=9)
- [ ] `Signer` value object + `SignerStatus` enum pinned ordinals
- [ ] `SigningEnvelopeMetadata`, `SignedAssetReference`

## Phase 2 — Domain events

- [ ] 16 event records under `DocumentSigning.Domain/Aggregates/Events/` with `[DomainEvent]` ordinals

## Phase 3 — Aggregate + repository

- [ ] `DocumentSigningSession` aggregate class with 16 lifecycle methods
- [ ] `SigningSessionRepository`
- [ ] `SigningSessionSnapshot [Snapshot(Revision = 1)]`

## Phase 4 — Commands + handlers

- [ ] `InitiateSigningSessionCommand` + handler (mints `SigningSessionId` server-side; emits `SigningSessionInitiated` — envelope-lookup row written by MM-156 projector from that event, not here)
- [ ] `CancelSigningSessionCommand` + handler
- [ ] `ForceUnlinkSigningSessionCommand` + handler (reconcile)
- [ ] `EraseSigningSessionPersonalDataCommand` + handler
- [ ] `RecordSigningEnvelopeEventCommand` + handler (webhook-dispatched; classifies adapter event + maps to lifecycle method)
- [ ] `MarkSigningSessionStrandedCommand` + handler (scanner-dispatched, System actor)

## Phase 5 — Adapter integration

- [ ] `ISecuredSigningAdapter` interface + stub implementation
- [ ] Webhook event classifier (adapter event name → aggregate method)

## Phase 6 — Tests

- [ ] Unit: each lifecycle method — happy path + guard precedence
- [ ] Unit: `InitiateSigningSession` mints distinct id each call; caller `sessionId` input (if present) refused or ignored
- [ ] Unit: `MarkSignerCompleted` on all signers → aggregate transitions to `Completed`; emits `SigningCompleted`
- [ ] Unit: `Cancel` refuses non-`Initiated`/`EnvelopeCreated` → `SigningSessionNotCancellable`
- [ ] Unit: `ForceUnlink` refuses non-`Stranded` → `SigningSessionNotStranded`
- [ ] Integration: webhook event → `RecordSigningEnvelopeEventCommand` → aggregate update → `media-signing-session-detail` reflects

## Phase 7 — Communicate change

- [ ] No `breaking-changes.md` entry — wire captured by MM-155 (HTTP) + MM-156 (envelope-lookup is non-wire storage shape)

## Phase 8 — Ship

- [ ] PR to `develop`

## Phase 9 — Close

- [ ] CLAUDE.md modules table: `DocumentSigningSession ⚠ specified, no aggregate class exists` → `DocumentSigningSession` (⚠ removed)
- [ ] INTEGRATION-BACKLOG.md: MM-157 → § Shipped
- [ ] spec-divergence/INDEX.md: WS-117 close row

## Session log

- 2026-10-16: plan drafted (alignment-sweep-2026-10-15 cell DocumentSigningSession × write-model; full aggregate build — 16 events + 6 commands + value-objects + snapshot + repository + SecuredSigning adapter interface; wire captured by MM-155/156)
