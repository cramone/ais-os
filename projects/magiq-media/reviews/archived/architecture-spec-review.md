# Architecture & Systemic Spec Review

_magiq-media · Reviewed against `docs/spec/architecture/*` (system-architecture, service-boundaries, domain-model), `docs/spec/shared/*` (system-spec, security-scenarios, api-conventions), all five consolidated `docs/adrs/*` topic docs, and the `ChangeRequests`/`Catalog` context overviews, as of 2026-07-16._
_Reviewer: systemic/architecture pass (AI-assisted), for Chase Ramone._
_Companion to `reviews/api-rest-review.md` — that one covers the REST wire contract; this one covers cross-cutting system design, auth, eventing, and cross-document consistency._

> **How to use this document.** Each finding is self-contained: **Where** (files + sections), **What the spec says** (with the specific tension), **Why it matters**, **Options**, and a **Decision** box to fill in. You can work these in any order across future sessions — nothing here has been changed in the spec yet. Nothing in this review touches app code; every item is a spec/design decision or a documentation-consistency fix. Severity reflects blast radius if it ships as-is, not implementation effort.

---

## Executive Summary

The spec is unusually mature for pre-implementation: every aggregate has write/read/API/scenario coverage, the ADRs record real rationale and rejected alternatives, and the docs are heavily self-audited (many table-shape and naming anomalies already carry their own inline notes). This review deliberately skips those already-tracked cosmetic items and focuses on **design-level** issues and **cross-document contradictions** that a self-audit pass within a single file won't catch.

Three themes:

1. **Auth is the weakest part of the design.** The JTI replay model makes User tokens effectively single-use (acknowledged as interim), and the write-side authorization model is ownership-only with no role usage — a poor fit for a multi-tenant government/enterprise records platform. These are design decisions to revisit, not bugs.
2. **The event bus accepts a dual-write gap that is safe for internal projections but risky for external compliance consumers.** Worth revisiting given the regulated-records domain.
3. **Cross-document drift.** Several safety-relevant values and contracts (saga timeout, upload endpoint path, review-flow authority, a reused table name) are specced two or more different ways across the architecture docs, shared spec, and context overviews. These are cheap to fix now and expensive to discover during implementation.

**Overall design rating: 7/10.** The core CQRS/ES/multi-tenancy design is sound and consistently applied at the aggregate level. Points come off for the auth model and for cross-doc consistency at the system level — the individual documents are strong, but the seams between them have drifted.

---

## Findings Index

| # | Severity | Finding | Type |
|---|----------|---------|------|
| S1 | ✅ Done | ~~JTI replay model makes every User JWT effectively single-use~~ — resolved 2026-07-16 (**stateless JWT**; superseded the revocation-list build) | Design |
| S2 | ✅ Done | ~~Replay-check applicability contradicts itself (system-spec vs auth ADR)~~ — moot under stateless JWT (no check) | Contradiction |
| S3 | ⏸ Deferred | Dual-write gap on the boundary (integration) event topic — discussed, parked 2026-07-16 | Design |
| S4 | ⏸ Deferred | Authorization is ownership-only; roles captured but unused for writes — discussed, parked 2026-07-16 | Design |
| S5 | ✅ Done | ~~StorageTier duplicates the S3 lifecycle policy and reconciles by daily full-table scan~~ — resolved 2026-07-16 (Option B, derive-on-read) | Design |
| S6 | ✅ Done | ~~Ingestion saga single non-resetting clock — specced two ways~~ — **A+C implemented 2026-07-17** (two-phase per-profile clock; reversible `ProcessingTimeout`). Max-input cap + per-profile derivation are tracked follow-ups | Design + Contradiction |
| S7 | ✅ Done | ~~Upload endpoint path specced four different ways~~ — resolved 2026-07-17 (spec aligned to code; canonical `POST /v1/assets/uploads`) | Contradiction |
| S8 | ✅ Done | ~~Review-flow authority contradicts itself (domain-model vs ChangeRequests overview)~~ — resolved 2026-07-17 (domain-model aligned to saga-driven model; review saga marked deferred/unbuilt) | Contradiction |
| S9 | ✅ Done | ~~system-architecture saga section stale vs ChangeRequests context spec~~ — resolved 2026-07-17 (added S6 recovery handler; review/checkout sagas marked deferred; added checkout saga + binding routing + activation handler) | Drift |
| S10 | ✅ Done | ~~`media-signing-sessions` names two incompatible tables~~ — resolved 2026-07-17 (**split into 3 tables**, diverges from the review's Option A — see decision) | Contradiction |
| S11 | ✅ Done | ~~`system-architecture.md` is physically truncated~~ — resolved 2026-07-17 (SQS bulk rows from CDK; Key Invariants recovered verbatim from git `6fc139ee`) | Doc integrity |
| S12 | ✅ Done | ~~Standalone-asset bucket/role mismatch after late attachment~~ — resolved 2026-07-18 (**single originals bucket + capability `tier-policy` tag applied at assign**; placement is now a mutable tag, not a bucket/key — reassignment-proof) + **process-on-assign** (standalone no longer processed/charged speculatively; processed on assign) | Latent edge case |
| S13 | Low | Reservation + counter non-atomicity; confirm all name-freeing paths release | Latent edge case |
| S14 | ✅ Done | ~~`asset.write-model.md` physically truncated (sibling to S11, not originally flagged)~~ — found + reconstructed 2026-07-17 (interface block + Published/Consumed Integration Events rebuilt from code) | Doc integrity |

---

## Critical

### S1 — JTI replay model makes every User JWT effectively single-use

> **✅ COMPLETED 2026-07-16 — final decision: STATELESS JWT. Do not re-do.** After building the revocation-list model (Option A), we superseded it: with a 15-min access-token TTL and a refresh-token flow at `magiq-auth`, magiq-media now validates JWTs statelessly and runs no JTI middleware. Revocation lives upstream (revoke the refresh token). See the Decision box below.

**Where:** `docs/spec/shared/system-spec.md §Token Replay Detection` (table `media-used-jtis`, PK `jti`, TTL `exp`); `docs/adrs/auth-and-security.md §Service Account Authentication`.

**What the spec says.** On every authenticated request, after JWT validation: `GetItem(jti)` → reject 401 if present; then conditional `PutItem({jti, exp})` with `attribute_not_exists(PK)` → reject 401 on failure. The auth ADR states the model plainly: "every token is effectively single-use," designed around browser `User` sessions. The ADR itself names the record-on-first-use approach **interim** and calls an explicit revocation list "the *correct long-term architecture*," deferred to a future ADR.

**Why it matters.** Single-use bearer tokens conflict with normal HTTP client behavior:
- A browser (or SDK) firing concurrent requests on one token gets 401s on all but the first — the `GetItem`/`PutItem` race means only one wins.
- Clients must fetch a fresh token per request, putting the Identity provider on the critical path of every call and multiplying auth-server load.
- Any transparent retry (network blip, 5xx backoff) re-sends the same token and fails closed.

This is currently the normative spec, not a hypothetical. It works in a demo (one request at a time) and breaks under real client concurrency.

**Options.**
- **A (recommended):** Move `User` tokens to the revocation-list model the ADR already endorses — write to `media-used-jtis` only on explicit revocation (logout, rotation, incident), check on every request. Preserves replay protection without penalizing normal reuse. Requires a revocation endpoint + runbook (the ADR's stated blocker).
- **B:** Keep single-use but make it viable by having the Identity provider issue very-short-lived per-request tokens with a client-side token pump. High auth-server load; fragile; the ADR already rejected per-request issuance for System actors at 500 req/s.
- **C:** Do nothing pre-release, accept the constraint, document it loudly for client teams. Only tenable if clients are strictly serial.

**Decision:** _2026-07-16 (final) — **STATELESS JWT**, superseding the revocation-list build below._

Chase confirmed a 15-minute access-token TTL + refresh-token flow at `magiq-auth`. Given that, magiq-media validates JWTs statelessly (signature/claims/`exp`) and runs **no** JTI middleware — revocation is relocated upstream (revoke the refresh token; the 15-min TTL bounds exposure to ≤15 min). This is a simpler resolution of S1's original single-use problem than the revocation list, and removes a per-request DynamoDB dependency.

- **Code (magiq-media):** removed the `Magiq.AspNetCore.JtiReplayDetection` package reference from `Api.csproj`, the `JtiReplayDetectionOptions` wiring + `using` from `Startup.cs`, and neutralized `Auth/LogoutEndpoint.cs` (logout is now client-side + upstream refresh revocation). **`git rm` `Auth/LogoutEndpoint.cs`.**
- **Spec:** `system-spec.md`, `api-conventions.md`, `system-architecture.md`, `error-catalog.md`, and the ADR (`auth-and-security.md §2`, with full revision history) rewritten to stateless. `media-used-jtis` marked retired.
- **CDK:** `media-used-jtis` table flagged deprecated/for-teardown (kept temporarily to avoid a destructive delete on deploy).
- **Platform SDK:** the `JtiValidationMode.RevocationList` capability (from the build below) is **kept in the platform, dormant** — available to wire back in if a customer ever requires immediate (sub-TTL) hard revocation.
- **⚠ Verify locally:** `dotnet build` `Media.Api` (confirm removing the package reference leaves no dangling using/DI), and confirm no other host referenced the plugin.

---

_Superseded build (kept for history):_ **Option A (revocation-list), implemented then replaced.** Scope was a per-`jti` revocation registry (the existing `media-used-jtis` table, repurposed; physical name retained to avoid CDK churn). Actor/tenant-level bulk revocation had been deferred to a documented v-next follow-up.

- **Platform SDK** (`aspnetcore-platform`, `Magiq.AspNetCore.JtiReplayDetection`): added `JtiValidationMode { RecordOnUse (default), RevocationList }` — additive/non-breaking, existing consumers keep single-use behavior. `IUsedJtiStore.RevokeAsync` added as a default interface method (delegates to `MarkAsync`). Middleware branches on `Mode`; in `RevocationList` the request path is read-only.
- **App** (`magiq-media`): `Api/Startup.cs` sets `Mode = RevocationList`; new `Auth/LogoutEndpoint` → `POST /v1/auth/logout` revokes the caller's own token.
- **Spec**: `system-spec.md` (§Token Revocation rewrite + JWT-claims + table-list rows), `api-conventions.md`, `error-catalog.md`, `system-architecture.md`, and this ADR (`auth-and-security.md`) updated. ADR-009 archive preserved.
- **⚠ Release step for alignment:** magiq-media consumes the platform via NuGet PackageReferences, not project references. The new `Magiq.AspNetCore.JtiReplayDetection` + `.Abstractions` packages must be built, version-bumped, and restored in magiq-media before the app compiles against `JtiValidationMode`/`RevokeAsync`.
- **Follow-ups:** incident-response revocation runbook; actor/tenant-level bulk revocation (v-next).

---

### S2 — Replay-check applicability contradicts itself

> **✅ COMPLETED 2026-07-16 — moot under stateless JWT (S1). Do not re-do.** With no server-side replay/revocation check at all, there is no "which actor types are enforced" question — the contradiction dissolves entirely.

**Where:** `docs/spec/shared/system-spec.md §Token Replay Detection` line ~134 vs `docs/adrs/auth-and-security.md §2 (System actors exempt from JTI replay recording)`.

**What the spec says.** system-spec: *"Full enforcement for all actor types that present a JWT."* The auth ADR: the `HttpExecutionContext` JTI middleware **skips** the `GetItem`/`PutItem` cycle entirely when `actor_type == "System"` — that carve-out is the entire point of the service-account ADR (a backend service or CLI makes many calls on one token).

**Why it matters.** An implementer building to the shared spec would enforce replay on System tokens and break every service account after the first request. One building to the ADR would leave the shared spec documented wrong. Per the project's "flag contradictions" rule, this needs an explicit reconciliation, not a silent pick.

**Options.**
- **A (recommended):** ADR is the intended behavior — add the System carve-out to `system-spec.md §Token Replay Detection` so the normative shared spec matches. Cheap.
- **B:** If S1 is resolved toward a revocation-list model, rewrite this whole section once and make the System distinction moot (revocation-list checks are cheap for all actor types).

**Decision:** _2026-07-16 — **Moot under stateless JWT (S1, final).**_ magiq-media performs no server-side replay or revocation check, so there is no actor-type applicability question to reconcile. `system-spec.md §Token Validation (stateless)` and `auth-and-security.md §2` now describe stateless validation uniformly; the ADR's revision history records the path from the original System-exemption → revocation-list → stateless.

---

### S3 — Dual-write gap on the boundary (integration) event topic

> **⏸ DEFERRED 2026-07-16 — discussed with Chase, parked for later; not yet actioned.** Recommendation stands: Option A (outbox on the integration-events topic first). Note: platform already ships `Magiq.Platform.Messaging.Outbox(.DynamoDb)` and `Api.csproj` references it, so this is likely partly a wiring exercise.

**Where:** `docs/adrs/persistence-and-eventing.md §Domain Event Bus` (accepted dual-write risk) and `§Integration Events (Per-Module Publishers)`; `docs/spec/shared/system-spec.md §Dual-Write Risk`; consumers in `docs/spec/architecture/service-boundaries.md §Integration Contracts` (Compliance, Billing, Notifications, Search).

**What the spec says.** After the event-store `PutItem`, the Command Handler publishes to `media-domain-events` (SNS); the two steps are not atomic. This is **accepted** because full event-store replay rebuilds projections. Separately, the per-module `*DomainEventMapper` classes publish `media.*` integration events to `media-integration-events` **inline in the same handler**, under the same non-atomic pattern. External bounded contexts subscribe to that topic: Compliance consumes `media.registration.confirmed`, Billing consumes processing/publish events, etc.

**Why it matters.** The "replay rebuilds it" mitigation covers *internal* projections — replaying the event store re-runs your projectors. It does **not** re-deliver a lost publish to an external BC's SQS queue. If the handler commits the event then dies before the integration-event publish, Compliance never sees a confirmed registration, and nothing automatically retries the cross-boundary delivery. On a regulated-records platform, a silently dropped compliance event is a materially worse failure than a stale internal read model. The ADR documents a transactional outbox as the future hardening but defers it.

**Options.**
- **A (recommended):** Implement the documented outbox for the integration-events topic first (it's the higher-stakes topic), even if the domain-events topic keeps the accepted dual-write risk for now. Write the integration event to a `media-outbox` row in the same `TransactWriteItems` as the event-store append; a poller Lambda publishes and marks sent.
- **B:** Full outbox for both topics — cleanest, more work.
- **C:** Keep as-is but add a reconciliation job that diffs event store vs a per-consumer delivery ledger and re-publishes gaps. More moving parts than the outbox for weaker guarantees.

**Decision:** _(to fill in)_

---

## High

### S4 — Authorization is ownership-only; roles captured but unused for writes

> **⏸ DEFERRED 2026-07-16 — discussed with Chase, parked for later; not yet actioned.** Needs a product read on whether near-term customers need team editing (Option A) or just admin + `TransferOwnership` (Option B) before choosing.

**Where:** `docs/spec/shared/security-scenarios.md` PERM-1/PERM-2/PERM-3; `docs/spec/architecture/service-boundaries.md §Cross-Cutting Concerns` (Rules 6); `docs/spec/architecture/system-architecture.md §Authentication & Authorization`.

**What the spec says.** Every write command gates on `context.Actor.Id == aggregate.OwnerId`. The only other authorization primitives are the `System` actor-type gate (`RequireActorType("System")` on `approve`/`force-release-checkout`) and reviewer-membership checks on `MediaChangeRequest`. The `roles` JWT claim is resolved onto `Actor.Roles` but drives no write-side decision. There is no ownership-transfer command in the domain model.

**Why it matters.** For a multi-tenant government/enterprise records platform this produces predictable operational pain:
- **No shared/team editing** — two users cannot both maintain a `Collection` or `Folder`; only the creator can mutate it.
- **No admin/delegate** — a tenant admin cannot manage another user's resources except by minting a `System` token, which is far too coarse (System bypasses replay detection and satisfies System-only endpoints).
- **Orphaned resources on offboarding** — when an owner leaves the org, their `MediaItem`s/`Collection`s/`Folder`s become immutable to everyone; there's no transfer path.

The `roles` claim is right there and unused, which suggests RBAC was anticipated but never specced.

**Options.**
- **A (recommended):** Design an explicit access model now (pre-release, no migration cost): keep owner-implicit-allow, add role-based grants (e.g. `Editor`/`Admin` on a Collection subtree), and add an `TransferOwnership` command. Decide the resource granularity (per-Collection vs per-item).
- **B:** Minimal: add only an admin role that satisfies the ownership check tenant-wide, plus `TransferOwnership`. Solves offboarding and admin management; still no fine-grained sharing.
- **C:** Defer, accept single-owner semantics for v1, document the constraint. Risk: retrofitting authz after the wire contract and read models ship is expensive.

**Decision:** _(to fill in)_

---

### S5 — StorageTier duplicates the S3 lifecycle policy and reconciles by daily full-table scan

> **✅ COMPLETED 2026-07-16 — Option B (derive-on-read) implemented in code + spec. Do not re-do.** Full removal of `StorageTier` from the aggregate; cold-storage download returns 409 + async restore. See the Decision box below. **Requires local `dotnet build` + test run, and `git rm` of 4 neutralized files (listed below).**

**Where:** `docs/adrs/asset-storage-and-processing.md §Storage Tier Lifecycle`; `docs/spec/architecture/system-architecture.md §12 StorageTierTransitionScanner Lambda`.

**What the spec says.** `media-source` uses a time-based four-tier S3 lifecycle (Standard → StandardIA @90d → GlacierInstant @365d → DeepArchive @730d), applied by the bucket policy. Because S3 lifecycle transitions emit no events, `StorageTierTransitionScanner` runs a **daily `TotalSegments=10` parallel Scan** over the `media-assets` table, using a `FilterExpression` that infers the expected tier from each asset's `CreatedAt` age (the same 90/365/730 thresholds, hardcoded a second time), and dispatches `RecordStorageTierTransitionCommand` where the recorded tier lags.

**Why it matters.**
- **Two sources of truth for the thresholds** — the CDK bucket-lifecycle config and the scanner's filter constants. Change one without the other and the domain's `StorageTier` silently diverges from reality.
- **Inference, not observation** — the scanner assumes the asset followed the standard curve based on age; it never reads the actual S3 storage class. Any object that transitioned off-schedule (manual restore, exception rule) will be mislabeled.
- **Cost/scale** — a daily parallel Scan of the whole asset table is a blunt instrument; the doc itself notes it needs a fan-out redesign past ~50M assets.
- **Open gap** — DeepArchive's 12-hour retrieval means `GetObject` can throw `InvalidObjectState`; the ADR says this error path "must exist before production" but no spec describes it.

**Options.**
- **A:** Single-source the thresholds (one config consumed by both CDK and the scanner) — smallest change, keeps the architecture.
- **B (recommended for correctness):** Stop modeling `StorageTier` as authoritative aggregate state; derive it on read via S3 `HeadObject` (or cache it on the detail read model, refreshed on access). Removes the scanner and the drift entirely. Trade-off: a HeadObject on download-URL issuance.
- **C:** Drive transitions from S3 → EventBridge (S3 Lifecycle transition events) into the existing bus instead of scanning. Event-driven, no polling; verify S3 emits the transition events you need.
- **Regardless:** spec the `InvalidObjectState` restore path before production.

**Decision:** _2026-07-16 — **Option B (derive-on-read), implemented.** Full removal (Chase's call): `StorageTier` is no longer domain state; cold-storage retrieval returns **409 + async restore**, mapped at the endpoint layer (no platform change)._

- **Removed:** `Asset.StorageTier` field, `AssetStorageTierTransitioned` event, `RecordStorageTierTransition` command+handler, and `StorageTier` from the 3 creation events + the `AssetSummaryReadModel`. The `StorageTierTransitionScanner` was **never coded** (spec-only), so nothing to delete there.
- **Added (read side):** `IAssetRetrievalInspector` + `S3AssetRetrievalInspector` (S3 `HeadObject` → retrievable vs cold; initiates `RestoreObject`). `GetAssetDownloadUrlHandler` derives tier on read; `AssetDownloadUrlResult` gained a `Restoring` discriminator; `GetAssetDownloadUrlEndpoint` maps it to **409**. `AssetDownloadStorageOptions.RestoreAvailabilityDays` (default 3).
- **Spec:** ADR `asset-storage-and-processing.md §Storage Tier Lifecycle` rewritten; `system-architecture.md §12` (scanner → derive-on-read) + infra table; `domain-model.md`, `service-boundaries.md`, `bounded-context.md`, `asset.write-model.md`, `asset.read-model.md`; `error-catalog.md` (`AssetInColdStorage` 409); CDK `README.md`. S3 **lifecycle policy unchanged** (physical tiering stays).
- **⚠ Manual step — can't delete on this mount:** `git rm` these 4 now-neutralized (empty) files: `AssetManagement.Domain/ValueObjects/StorageTier.cs`, `AssetManagement.Domain/Aggregates/Events/AssetStorageTierTransitioned.cs`, and the `AssetManagement.WriteModel/Commands/RecordStorageTierTransition/` folder (Command + Handler).
- **⚠ Verify locally:** no compiler in this session. `dotnet build` + run `AssetManagement.*.Tests`. Confirm the AWS SDK member names used in `S3AssetRetrievalInspector` (`GetObjectMetadataResponse.StorageClass` / `.RestoreExpiration` / `.RestoreInProgress`, `RestoreObjectRequest.RetrievalTier`) against the pinned `AWSSDK.S3` version.
- **Follow-up:** the endpoint returns 409 via `AddError`/`SendErrorsAsync` (FastEndpoints validation shape); wiring the `AssetInColdStorage` errorCode into `ProblemDetails.extensions` for strict error-catalog conformance is a small follow-up.

---

### S6 — Ingestion saga single non-resetting 30-min clock (and specced as two values)

> **✅ COMPLETED 2026-07-17 — A+C implemented in code + spec + CDK; `dotnet build` and tests green. Do not re-do.** Two-phase clock with a per-profile (`MediaProfile`) processing budget resolves the reset + the 30 min-vs-4 h contradiction (A); a reversible `ProcessingTimeout` (late success un-fails job/asset/saga, distinct external `AssetProcessingTimeoutRecoveredIntegrationEvent`) resolves the orphaned-success race (C). CDK saga subscription filter updated. Remaining follow-ups (NOT part of S6's fix): per-profile budget **derivation** from rendition definitions (needs the rendition stage) and the **max-input cap**. See the Decision box below.

**Where:** `docs/spec/architecture/system-architecture.md §9 (Saga Timeout Durations table + "Key design decision")`; `docs/spec/shared/system-spec.md §AssetIngestionSaga` / saga-timeout table; `docs/adrs/asset-storage-and-processing.md §Processing Failure Taxonomy`.

**What the spec says.** `AssetIngestionSaga.TimeoutAt` is set once on `ProcessingJobCreated` and **never reset** on the `AwaitingValidation → ProcessingDispatched` transition — one 30-minute window covers validation + processing combined. The doc acknowledges large video is handled by MediaConvert async callbacks and "should complete well within budget." **Separately**, `system-spec.md` states the asset-processing saga TTL "defaults to **4 hours**," while `system-architecture.md` uses **30 minutes**.

**Why it matters.**
- **Race on overrun:** a 2 GB video that validates in ~25 min leaves ~5 min for MediaConvert. If it overruns, `SagaTimeoutScanner` dispatches `FailAssetProcessing(ProcessingTimeout)` while the job is still running. The aggregate goes terminal; the later MediaConvert completion callback hits a terminal aggregate and is treated as an idempotent no-op — so an asset whose processing actually **succeeded** is permanently `ProcessingFailed`, with orphaned rendition output in S3 and a spurious failure surfaced to the user.
- **Contradiction:** 30 minutes vs 4 hours is a safety-relevant value specced two ways. Whichever is real, the other doc misleads.

**Options.**
- **A (recommended):** Reset the clock on the validation→processing transition (separate validation budget and processing budget) so processing time isn't eaten by validation time. Reconcile the single value to the higher, realistic processing ceiling.
- **B:** Keep a single clock but set it to the 4-hour figure and make the two docs agree; simplest, still shares one budget across both stages.
- **C:** Make MediaConvert completion able to "un-fail" a `ProcessingTimeout` (compensation on late success) rather than no-op. Removes the orphaned-success case but adds a non-terminal transition out of `ProcessingFailed` — more domain complexity.

**Decision:** _2026-07-17 — **Two-phase clock + per-profile budget (Decision 1 of A+C), implemented.** The "specced two ways" contradiction is resolved._

Chose **A** (reset the clock on the validation→processing transition) with the processing budget modelled at the **`MediaProfile` level** (Chase's call — absorb the plumbing pre-release rather than retrofit after the wire contracts ship). Budgets are **system-derived, not author-set**.

- **Budgets:** validation `ValidationBudget` default **15 min** (global); processing = per-profile `ProcessingTimeoutMinutes` when set, else `DefaultProcessingBudget` default **4 h**. All in `AssetIngestionTimeoutOptions` (config `Media:Processing:AssetIngestionTimeouts`) — single-sourced, so the 30 min-vs-4 h contradiction is gone.
- **Clock reset:** the saga sets `TimeoutAt = CreatedAt + ValidationBudget` at creation and resets it to `PassedAt + processingBudget` on `AwaitingValidation → ProcessingDispatched`. Validation time no longer eats the processing budget.
- **Per-profile plumbing (code):** `int? ProcessingTimeoutMinutes` threaded profile → `CompiledMetadataTemplate` → `MediaProfileSnapshot` → `MediaItemCreatedIntegrationEvent` → `MediaItemCapabilityReference` → `MediaItemCapabilities` → `RecordValidationResultHandler` → `AssetValidationPassed` (domain + integration event) → saga. Null everywhere today (see derivation follow-up); the saga falls back to the default.
- **Scanner:** the `SagasApproachingTimeout` warning window is now `WarningWindowFraction` (default 20 %) of the *current phase* budget, not a hardcoded 6 min.
- **Spec:** `system-architecture.md §9` + `system-spec.md` rewritten to the two-phase model.
- **Verified 2026-07-17:** `dotnet build` + `AssetManagement.*` / `Catalog.*` / `Processing.*` test projects pass. (`BindConfiguration` resolved transitively via `Magiq.Platform.WriteModel.Application`; no extra package needed.)

**Still open — the "C" half of A+C, plus follow-ups:**
- **C — reversible `ProcessingTimeout` (decisions 2–4 settled 2026-07-17; implemented — see below):**
  - **D2 — reversible set:** `{ ProcessingTimeout }` only, on **both** `ProcessingJob` and `Asset`; every other category (`ProcessingError`, `ValidationTimeout`/`ValidationError`, virus detection) stays strictly terminal. Guard is a single-value check on the stored failure category.
  - **D3 — event model:** explicit recovery domain events (`ProcessingJobTimeoutRecovered`, `AssetProcessingTimeoutRecovered`), each carrying the success payload and transitioning `Failed(ProcessingTimeout) → Succeeded`/active in one guarded event — not a bare `Failed→Succeeded`. Keeps the stream auditable, gives projectors an explicit compensation hook, and makes recovery a countable ops signal (budget too tight).
  - **D4 — cross-BC contract:** publish a **distinct** external `AssetProcessingTimeoutRecoveredIntegrationEvent` (full success payload), not a re-emitted completion or a boolean flag, so downstream BCs (Compliance/Billing/Notifications/Search) get an unambiguous retract-and-succeed signal. Best-effort correction (some effects — e.g. an already-sent notification — can't be undone). Internally, recovery drives the same consequences as a normal completion.

    **Implemented 2026-07-17 (in-repo):** stored `FailureCategory` on both `ProcessingJob` and `Asset`; `Complete()`/`CompleteProcessing()` are state-aware and un-fail only `Failed(ProcessingTimeout)`; new domain events `ProcessingJobTimeoutRecovered` + `AssetProcessingTimeoutRecovered`; the internal Processing→AssetManagement hop **reuses** `ProcessingJobCompletedIntegrationEvent` (internal, not the external contract), while the Asset publishes the **new external** `AssetProcessingTimeoutRecoveredIntegrationEvent`; mappers, both job + both asset projectors, the SNS publisher, the saga's `OnAssetProcessingTimeoutRecovered` (Failed→Completed), and the SagaOrchestrator bridge are all wired; recovery aggregate tests added.
    **CDK (cdk-magiq-media) — done 2026-07-17:** `media.asset.processing-timeout-recovered` added to the `media-sagas` SNS→SQS subscription filter (`sqs-queues.construct.ts`). The internal recovery hop reuses `media.processingjob.completed`, already allow-listed on the cross-module queue, so no other filter changed. Any **external** BC (Compliance/Billing/Notifications/Search) that wants the correction subscribes to the new type in its own infra. **⚠ Verify locally:** `dotnet build` + run `Processing.*`, `AssetManagement.*` tests; `cdk synth`/`diff` the CDK repo.
- **Max-input cap:** per-profile upload size/duration ceiling so timeouts stay exceptional — separate subsystem (upload-URL validation + error-catalog). Follow-up.
- **Per-profile derivation:** compute `ProcessingTimeoutMinutes` from the profile's rendition/asset definitions once the rendition stage exists (currently always null → default).

---

## Medium — cross-document consistency

### S7 — Upload endpoint path specced four different ways

**Where:** authoritative `docs/spec/contexts/AssetManagement/aggregates/Asset/asset.api.md` and `docs/spec/shared/api-conventions.md`: `POST /v1/assets/uploads`. `system-spec.md`, `service-boundaries.md`, `bounded-context.md`, `system-architecture.md §Cross-Cutting`: `POST /media-assets/upload-url`. `system-architecture.md §Services`: also `POST /assets/upload-url`. `asset.scenarios.md`: `POST /assets/uploads` (no `/v1`).

**What the spec says.** Same operation, four spellings, differing on the `/v1` prefix, `media-` prefix, and `uploads` vs `upload-url`.

**Why it matters.** This is the single most-referenced endpoint in the system (every ingestion flow starts here). Client SDKs, Postman collections, and the ADO wiki will inherit whichever doc a given reader lands on. The REST review (`api-rest-review.md`) already standardized on flat, `/v1`-prefixed, resource-oriented routes — this should follow that.

**Options.**
- **A (recommended):** Canonicalize on `POST /v1/assets/uploads` (matches the authoritative aggregate spec + api-conventions + the REST review's flat-URL decision). Find/replace the architecture and shared docs.

**Decision:** _2026-07-17 — **Option A (canonical `POST /v1/assets/uploads`), implemented.**_

Code was already aligned (`Post("/assets/uploads")` under the FastEndpoints `V1/` group → `/v1/assets/uploads`); the spec was the laggard. All divergent live docs updated to `POST /v1/assets/uploads`:

- **Paths fixed:** `system-spec.md`, `asset.scenarios.md` (×5), `processingjob.scenarios.md` (×4), `system-architecture.md` (§Cross-Cutting + §Services), `service-boundaries.md`, `bounded-context.md`, and the `asset-storage-and-processing.md` ADR flow diagram. Also aligned the confirm path in `system-spec.md` to `POST /v1/assets/{id}/uploads/confirm`.
- **Note (correction to this finding):** the review lists `system-architecture.md`/`service-boundaries.md`/`bounded-context.md` as already-drifted, and they were — the first fix pass missed four of those lines because grep classified the files as *binary* (a stray non-UTF-8 byte). Re-run binary-safe; now fixed. **Those four files (+ `asset.write-model.md`) still carry the non-UTF-8 byte — worth cleaning since they publish to the wiki.**
- **Left as-is:** archived ADRs (ADR-004) retain the historical `/assets/upload-url` as a point-in-time record.

**Related fix landed in the same effort (command/event naming drift, beyond S7's path scope):**
- Stale `UploadAsset*` / `Asset.Upload(` / `AssetUploaded` → canonical `InitiateAssetUploadCommand` / `InitiateAssetUploadHandler` / `Asset.InitiateUpload(` / `AssetUploadInitiated` across 13 files.
- ProcessingJob-creation trigger docs (`processingjob.api.md`, `processingjob.write-model.md`) corrected from the *initiated* event to the actual trigger — `AssetUploadConfirmedIntegrationEvent` / `media.asset.upload-confirmed` via `AssetUploadConfirmedEventHandler` — matching code (initiated handler is an intentional no-op) and `write-model.md`'s own lines 56/114/193/195.
- Two wrong SNS topics in `processingjob.api.md` corrected: the `media-processing` fan-out source and the published `media.asset.processing-failed` both moved `media-domain-events` → `media-integration-events` (integration-event topic, per CDK `sqs-queues.construct.ts`).
- **Not touched (code, not spec):** two Catalog XML-doc comments (`S3Key.cs`, `Catalog.WriteModel.Infrastructure/ServiceCollectionExtensions.cs`) still say `AssetUploaded` — flag for a code cleanup._

---

### S8 — Review-flow authority contradicts itself

**Where:** `docs/spec/architecture/domain-model.md §MediaChangeRequest` (dated 2026-04-26) vs `docs/spec/contexts/ChangeRequests/context-overview.md`.

**What the spec says.** domain-model.md: *"on `Approved`, command handler issues `ApproveMediaItem` on the linked `MediaItem`"* — i.e. a synchronous cross-aggregate write inside the CR command handler. ChangeRequests context-overview.md (authoritative, newer): outcome commands `ApproveMediaItem`/`RejectMediaItem` are dispatched by the **`MediaItemReviewSaga`**, and the context explicitly "does not own MediaItem state."

**Why it matters.** These describe two different consistency models. The domain-model version mutates two aggregates in one handler with no transaction and no compensation — if the second write fails, the CR is `Approved` but the MediaItem isn't, and nothing heals it. The saga exists precisely to avoid that (integration event → saga → command, with the timeout/compensation machinery). The stale summary would mislead anyone implementing from it.

**Options.**
- **A (recommended):** Update `domain-model.md §MediaChangeRequest` auto-resolution note to point at the saga, matching context-overview. Documentation-only.

**Decision:** _2026-07-17 — **Option A (align to the saga-driven model), implemented.**_ `domain-model.md §MediaChangeRequest` auto-resolution rewritten: the MCR emits `ChangeRequestApproved`/`Rejected`/`Abandoned`; the `MediaItemReviewSaga` dispatches `ApproveMediaItem`/`RejectMediaItem`. The MCR never mutates MediaItem state directly. Added an implementation-status note — the aggregate + resolution events exist in code, but the review-saga orchestration is **not implemented** (only `AssetIngestionSaga` is registered).

---

### S9 — system-architecture saga section stale vs ChangeRequests context spec

**Where:** `docs/spec/architecture/system-architecture.md §9 SagaOrchestrator` vs `docs/spec/contexts/ChangeRequests/context-overview.md`.

**What the spec says.** context-overview describes a richer review model: a `MediaItemCheckoutReviewSaga`, a `CheckoutBound` vs non-checkout binding routed by `ChangeRequestCreatedSagaHandler`, and a `ChangeRequestActivatedForReview` event / `ChangeRequestActivatedSagaHandler` that moves the saga into `AwaitingReview`. system-architecture.md lists only `MediaItemReviewSaga` with four handlers and none of that.

**Why it matters.** The system-level reference is where someone gets the "how does review work" mental model; it currently under-describes the actual design and omits an entire saga. Not a correctness bug, but a drift that compounds S8.

**Options.**
- **A (recommended):** Bring the system-architecture saga tables up to the context-overview model (add `MediaItemCheckoutReviewSaga`, the binding routing, and the activation handler).

**Decision:** _2026-07-17 — **Option A, implemented (+ a code-drift fix the review didn't flag).**_ `system-architecture.md §9` brought up to the ChangeRequests context-overview model: added `MediaItemCheckoutReviewSaga`, the `ChangeRequestCreatedSagaHandler` binding routing (CheckoutBound → checkout saga, else review saga), and `ChangeRequestActivatedSagaHandler`; review/checkout sagas marked 🔴 deferred (only `AssetIngestionSaga` is implemented). Also fixed two code drifts: the stale "two active sagas" claim, and the missing S6 `AssetProcessingTimeoutRecoveredSagaHandler` in the AssetIngestionSaga handler table.

---

### S10 — `media-signing-sessions` names two incompatible tables

**Where:** `docs/spec/architecture/system-architecture.md §Infrastructure` (read-model tables) vs `docs/spec/architecture/service-boundaries.md §SecuredSigning Adapter` + `docs/spec/shared/system-spec.md` table list.

**What the spec says.** system-architecture: `media-signing-sessions` (plural) is the signing-session **summary read model**, PK `TENANT#{TenantId}#{SigningSessionId}`. service-boundaries + system-spec: `media-signing-sessions` is the **`EnvelopeId → {TenantId, OwnerId, SigningSessionId}` webhook lookup** table, PK `EnvelopeId`, explicitly "not the primary read model."

**Why it matters.** One table name, two incompatible schemas and purposes. The webhook `TenantId`-resolution path (the one place in the system that derives `TenantId` from a table rather than `IExecutionContext`) depends on the lookup table being unambiguous. A CDK author or projector author reading the wrong doc provisions/writes the wrong shape.

**Options.**
- **A (recommended):** Rename the lookup table (e.g. `media-signing-envelope-lookup`) and leave `media-signing-sessions` as the summary read model. Update service-boundaries + system-spec.
- **B:** Keep the name for the lookup and rename the summary (more churn; the summary is referenced by more docs).

**Decision:** _2026-07-17 — **Split into three tables (diverges from the review's Option A above).**_ Investigation showed the authoritative DocumentSigning read-model + code had already drifted toward a split, and the "single table PK=`EnvelopeId`" was both the outlier and the one table violating the platform `TENANT#{TenantId}#{EntityId}` PK convention. Chase's call: split. Target: `media-signing-sessions` (summary, PK `TENANT#{TenantId}#{SigningSessionId}`, GSI `MediaItemIndex`), `media-signing-session-detail` (detail, same PK), `media-signing-envelope-lookup` (webhook lookup, PK `EnvelopeId`, write-once, strongly-consistent `GetItem` — the sole table-based TenantId resolution path). Projectors split to match the Asset summary/detail convention: `SigningSessionSummaryProjector` / `SigningSessionDetailProjector` / `SigningEnvelopeLookupProjector`. Spec fully updated (read-model.md, context-overview, system-architecture, service-boundaries, system-spec); code comments + projection registration aligned. **Deferred to the DocumentSigning impl phase:** author `SigningSessionSummaryProjector` + `SigningEnvelopeLookupProjector` (+ lookup read model), register both, provision the 3 tables in CDK. **Open design Q:** summary needs `OwnerId` but `SigningSessionInitiated` only carries `InitiatedBy` — decide `OwnerId := InitiatedBy` vs add to the event.

---

### S11 — `system-architecture.md` is physically truncated

**Where:** `docs/spec/architecture/system-architecture.md`, end of §SQS Queues table and end of document.

**What the spec says.** The SQS Queues table cuts off mid-row at `media-bulk-folder-imports` (self-noted with a flag), and the file ends mid-sentence at "`- TenantId is never`". The remaining queue rows (at least `media-bulk-media-imports`) and the entire Key Invariants section are missing.

**Why it matters.** This file publishes to the ADO wiki via CI, so the published system reference is incomplete for anyone outside your machine. It's already flagged internally but not repaired.

**Options.**
- **A (recommended):** Reconstruct the missing SQS rows from the CDK (`cdk-magiq-media`, queue constructs) and finish the Key Invariants list, then let CI republish.

**Decision:** _2026-07-17 — **Option A, reconstructed.**_ (Separate from the NUL-byte corruption — see the 2026-07-17 batch below.) SQS Queues table: `media-bulk-folder-imports` row completed + `media-bulk-media-imports` added, both marked deferred (from CDK `sqs-queues.construct.ts`, which lists them not-provisioned). Key Invariants: full 6-bullet list **recovered verbatim from commit `6fc139ee`** (it had regressed to a single truncated bullet after 2026-07-09). Both carry a dated reconstruction note in the file.

---

## Low — latent edge cases

### S12 — Standalone-asset bucket/role mismatch after late attachment

**Where:** `docs/spec/architecture/domain-model.md §Asset` (S3 path conventions, `RoleName`, `StorageKey` immutability) + `docs/adrs/asset-storage-and-processing.md §Pre-Signed Upload`.

**What the spec says.** A standalone upload (`MediaItemId` null) defaults to the full pipeline and lands in `media-source/{tenantId}/{shard}/{assetId}/original.{ext}`; `StorageKey` is immutable after assignment. Lightweight-profile assets (owning profile lacks `Processing`) are supposed to live in `media-documents/.../document.{ext}` with `RoleName = null`. But `AssignAssetToRole` (which is how an asset attaches to a MediaItem) assigns a `RoleName`.

**Why it matters.** If a standalone asset is later attached to a MediaItem whose profile lacks `Processing`, it's already in `media-source` with an `original.{ext}` key that can't change, and the attach path assigns a role that the lightweight model says should be null. The two asset shapes aren't reconcilable after a standalone-first upload. Core path, low frequency, no reconciliation story specced.

**Options.**
- **A:** Disallow attaching a standalone (media-source) asset to a lightweight (non-Processing) profile item — validation error, force a fresh upload into `media-documents`.
- **B:** Accept the bucket/key as-is for late attachments and relax the "lightweight assets live in media-documents / RoleName null" invariant to "bucket is decided at upload time, not re-derived on attach." Document it.
- **C:** Copy-on-attach into the correct bucket (extra S3 op, breaks the immutable-key claim).

**Decision:** _2026-07-18 — **superseded by a better option (F): single originals bucket + capability lifecycle tag.** Implemented in code + spec + CDK; build/tests pending (no compiler in-session)._

Investigation (against `D:\source\github\magiq-media`) confirmed the finding was reachable **and** understated: the assign→Asset seam was dead code, `media-source`/`media-documents` differed **only** by lifecycle (identical SSE-S3/BLOCK_ALL/enforceSSL/versioning; no delete permission; versioned), the rendition pipeline is a `NotImplementedException` stub, and the `RoleName = null` half of the finding was not code-real (every assigned asset carries a `RoleName`). So Options A–C were all papering over a model that reassignment (asset → different-capability item, which **is** supported; item → different profile is **not**) would keep breaking.

**Chosen (Option F):** collapse to one `media-source` originals bucket (`media-documents` retired) and drive lifecycle by a mutable `tier-policy` object tag rather than by bucket. `StorageKey` is stamped once at upload (`original.{ext}`, no capability parameter) and never re-derived. At **assign** (`ApplyAssetAssignmentHandler`, consuming a new `media.item.asset-assigned` integration event) the tier is (re)classified with a cheap `PutObjectTagging` — `managed` for a Processing profile, `retain` for a document profile — so both S12 and its reassignment variant reduce to a re-tag: no object copy, no key change, immutability preserved.

**Also fixed the adjacent gaps this review surfaced (Chase: "everything now"):**
- **Process-on-assign:** standalone uploads no longer run the pipeline or consume quota speculatively; `Asset.RequestReprocessing` (guarded: Active + no renditions + attached) re-enters `Validating` and re-publishes `AssetUploadConfirmedIntegrationEvent`, running the pipeline + charging the deferred quota at assign. Known follow-up: the `AssetIngestionSaga` is idempotent per `AssetId`, so a reprocess is worker-driven and **not** saga-timeout-tracked in this cut.
- **Spec contradiction** (standalone "runs the full pipeline" vs. bypass) and the **`RoleName = null`** drift corrected in `domain-model.md`, `asset.write-model.md`, `system-architecture.md`, ADR `asset-storage-and-processing.md`.

**Changed (all committed to disk, build pending):** CDK `media-buckets.construct.ts` (single bucket, tag-filtered lifecycle), `magiq-media-stack.ts` (documents grants/outputs removed, tagging grant added), `sqs-queues.construct.ts` (new event type); app `StorageKeyGenerator`/`IStorageKeyGenerator`/`S3AssetStorageOptions`, upload handlers (quota-defer + signature), new `IAssetStorageLifecycle`/`S3AssetStorageLifecycle`, new `AssetAssignedToRoleIntegrationEvent` + mapper + publisher, new `AssetAssignedToRoleEventHandler` + `ApplyAssetAssignment` command/handler, `Asset.RequestReprocessing` + `AssetReprocessingRequested` event/mapper, DI + domain-event registrations, `EnvironmentResetCommand`. **⚠ Verify locally:** `dotnet build` + tests (esp. `AssetManagement.*`, `Catalog.*`), `cdk synth`/`diff`; confirm AWS SDK `PutObjectTaggingRequest`/`Tagging`/`Tag` member names against the pinned `AWSSDK.S3`; confirm VO→string implicit conversions used in the new mappers.

---

### S13 — Reservation + counter non-atomicity; confirm all name-freeing paths release

**Where:** `docs/adrs/catalog-domain-invariants.md §Hierarchy Invariants`; `docs/spec/shared/system-spec.md §Name Uniqueness` (reservation release note, line ~305).

**What the spec says.** Name reservations (`media-name-reservations`) and hierarchy counters share a table but are written in **two separate DynamoDB calls**, not one transaction; a mid-Lambda failure can leave a counter or reservation drifted until an idempotent replay corrects it. Mitigated by idempotent command replay + a CloudWatch alarm on negative counters; the real fix (`ITransactionalUniquenessRegistry` via `TransactWriteItems`) is deferred. Reservations are noted to release "on rename or archive."

**Why it matters.** Mostly acceptable and already tracked — but two things to confirm before production: (1) that **every** name-freeing transition releases the reservation (rename, archive, and any hard-delete/terminal path — the spec only names rename and archive), otherwise a name gets permanently locked; (2) that the two-call window has the alarm + replay path actually wired, since it's the backstop for a real correctness edge.

**Options.**
- **A (recommended):** Audit all terminal/name-changing commands for reservation release; land `ITransactionalUniquenessRegistry` before scale. Track as follow-up, not a blocker.

**Decision:** _(to fill in)_

## Additional fixes landed 2026-07-17 (beyond the numbered findings)

Discovered and fixed during the S7–S11 pass; logged so they aren't re-investigated. All in the working tree, none committed.

- **Command/event naming drift (initiate side).** Stale `UploadAsset*` / `Asset.Upload(` / `AssetUploaded` → `InitiateAssetUploadCommand` / `InitiateAssetUploadHandler` / `Asset.InitiateUpload(` / `AssetUploadInitiated` across 13 spec files. Also renamed the Catalog handler class `AssetUploadedEventHandler` → `AssetUploadInitiatedEventHandler` (file + class + DI registration + test).
- **ProcessingJob trigger corrected to the confirmed event.** `processingjob.api.md` + `processingjob.write-model.md` said the job is created from `AssetUploaded*` / `media.asset.uploaded`; code creates it from `AssetUploadConfirmedIntegrationEvent` (`media.asset.upload-confirmed`) via `AssetUploadConfirmedEventHandler` (the initiated handler is a deliberate no-op). Fixed. Also corrected two wrong SNS topics in `processingjob.api.md` — `media-domain-events` → `media-integration-events` for both the `media-processing` fan-out and the published `media.asset.processing-failed` (per CDK).
- **Asset endpoint paths aligned to code (S7 family).** Beyond the upload path: `GET /v1/assets/{assetId}`, `GET /v1/assets`, `POST /v1/assets/{assetId}/uploads/confirm`, and multipart (`POST /v1/assets/multipart-uploads`, `/v1/assets/{assetId}/multipart-upload/complete|abort`) across service-boundaries, system-spec, system-architecture, asset.scenarios. (The code itself is inconsistent — `multipart-uploads` plural for initiate vs `multipart-upload` singular for complete/abort; docs now mirror code.)
- **S3Key `{ownerId}` drift.** `S3Key.cs` comment claimed key format `media-assets/{ownerId}/{shard}/{assetId}.{ext}`; actual `StorageKeyGenerator` produces `{tenantId}/{shard}/{assetId}/original.{ext}` (media-source) or `.../document.{ext}` (media-documents), keyed on `tenantId`. Fixed the comment + aligned `asset.write-model.md` interface signatures (`S3Key`→`StorageKey`; `Generate(... string extension, bool hasProcessingCapability)`; `GeneratePutUrlAsync(StorageKey, long fileSizeBytes)`).
- **NUL-byte corruption.** 4 files (`system-architecture.md`, `service-boundaries.md`, `bounded-context.md`, `asset.write-model.md`) had trailing NUL padding making them read as binary to grep and the wiki publish. Stripped. Two were also truncated in HEAD (S11 + S14).

## Outstanding (carried forward)

- **Not committed / git hygiene.** All 2026-07-17 work is in the working tree, mixed with in-flight S5/S6 code. Stale `.git/index.lock` must be deleted before the next git write. **S5's `git rm`** of the 4 neutralized `StorageTier` files is still pending (files present on disk).
- **Local verify.** Nothing built/tested in-session — run `dotnet build` + module tests, especially the Catalog handler rename and anything referencing the renamed symbols.
- **S10 deferred impl.** Author the 2 new projectors + lookup read model, register them, provision the 3 CDK tables when DocumentSigning is un-deferred. Resolve the `OwnerId`/`InitiatedBy` design Q.
- **Reconstructions need a read before wiki publish.** S14 (`asset.write-model.md` Published/Consumed Integration Events) and the S11 SQS rows are code-grounded but partly authored; the S11 Key Invariants are exact git recovery (safe).
- **Adjacent drifts flagged, not fixed:** DocumentSigning read-model field-name drift (`SessionId` vs `Id` in the summary record); the code-level multipart route singular/plural inconsistency; DocumentSigning detail read-model doc still lists an extra `SigningSessionSummaryProjector` naming that the impl phase should reconcile.

---

## Not covered here

- Table-shape / groupKey-inversion / stale-XML-doc anomalies already annotated inline in `system-architecture.md` (RecordTypeVersionDetail placement, `media-asset` Detail inversion, stale read-model doc comments) — these carry their own notes and decisions; not re-litigated here.
- The full REST wire-contract review (envelope keys, status codes, identifier naming, filter params) — see `reviews/api-rest-review.md`.
- App-code verification — every finding above is spec/design; none has been checked against `D:\source\github\magiq-media` source beyond what the specs assert.
