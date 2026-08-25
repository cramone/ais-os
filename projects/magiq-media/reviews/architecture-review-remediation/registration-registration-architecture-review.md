# Registration — Module Architecture Review (Specification vs Repository)

_Context: **Registration** (bounded context) — magiq-media_
_Aggregate: **Registration** (the context's only aggregate)_
_Reviewer role: Principal Domain Architect (DDD / CQRS / Event Sourcing / API)_
_Date: 2026-07-19_
_Scope: `src/modules/Registration/**` (Registration slice) vs `docs/spec/contexts/Registration/**` (context-overview, business-scenarios, registration.api / read-model / write-model / scenarios) + `docs/spec/shared/{api-conventions, error-catalog, security-scenarios, bulk-operations, media-types}.md` + `docs/adrs/**`_

> Method: every production `.cs` file in the Registration module (~90 files across Domain, Contracts, WriteModel{,.Endpoints,.Infrastructure}, ReadModel{,.Endpoints,.Infrastructure}) was read and compared against the four Registration aggregate specs, the context overview, the six business scenarios, the shared error catalog and API conventions, and the (superseded-stub) ADRs. The Catalog context is pulled in only where Registration references it (`MediaItem*IntegrationEvent`, the `RegistrationInitiatedConsumer` round-trip). Findings that hinge on `Magiq.Platform` base behaviour that could not be read directly (projection dedup, idempotency-key handling, JWT/actor-type pipeline) are flagged as such.

---

## 1. Module Summary

Registration owns a single aggregate, `Registration` (`media.registration` stream, `reg_`-prefixed), tracking the formal media-registration lifecycle of a published `MediaItem` with an external authority (Electronic or Physical). It is a textbook event-sourced CQRS slice: a rich aggregate with an owner-driven front half (initiate → attach documents → submit) and a System-actor back half (record dispatch → confirm/reject) plus a post-confirmation amendment workflow. It publishes six integration events via a domain-event mapper, maintains two DynamoDB read models (`media-registrations` summary, `media-registration-detail`) through SQS projectors, and keeps a write-side reference index (`MediaItemReference`) fed from Catalog `MediaItem*` integration events so upload/attach guards run without cross-BC aggregate calls.

Structurally the module is clean and consistent: command-per-folder, thin FastEndpoints, one integration-event mapper, and a reference-index projector. The aggregate is genuinely well-modelled — immutable `record` events, `Result<Unit, DomainError>` guards, event-stamped timestamps, and a correct two-event atomic write for amendment approval.

However, the module is **not production-ready**. The review surfaced two Critical and a cluster of High issues concentrated in four themes:

1. **Authorization is entirely absent — and the System/User boundary is unenforced.** No endpoint declares an auth policy and no handler compares the caller to `OwnerId` or checks `actor_type`. Because the five `[System]` endpoints (confirm, reject, submission, amendment approve/reject) are wide open, **any authenticated tenant user can self-confirm their own registration** and mint an official "external authority reference" — fabricating a legal record on a regulated-records platform.

2. **The document-eligibility guard is inverted.** `AttachMediaItemToRegistrationHandler` and `RequestAmendmentHandler` gate on `HasRegistrationCapability` instead of the spec's `!HasProcessingCapability`. They reject valid document media-items and admit processed media — the exact opposite of the invariant.

3. **The spec and code disagree on the core status name, and the read model diverges from the write model.** The aggregate uses `SubmissionRecorded`; the write-model spec, API error bodies and scenarios use `PendingConfirmation`. Full-text search is wired to an OpenSearch index that **no projector ever populates**, so `GET /registrations/search` returns nothing.

4. **The error/validation contract is unmet.** Every domain guard returns generic `InvalidOperation` (422); the catalog's coded `RegistrationConfirmed`, `DuplicatePendingAmendment`, `AmendmentNotPending`, `ReferenceRequired`, `NoDocumentsAttached`, `MediaItemNotPublished`, `NotResourceOwner`, `SystemActorRequired`, `InvalidStatusTransition` codes are never emitted; there are no request validators, so a malformed id or empty `reference` yields 500 instead of 400/422.

The aggregate itself is the strongest part of the slice; nearly every Critical/High defect lives in the **handler / endpoint / projector orchestration layer** around it, or is a **spec-internal contradiction** that the code was forced to pick a side of.

---

## 2. Aggregate Analysis

### `Registration` (Aggregate Root) — `Registrations.Domain/Aggregates/Registration.cs`

Single aggregate in the context. `EventSourced<Registration, RegistrationId>`, `ITenantScoped`, `[AggregateType("media.registration")]` (`Registration.cs:14-15`).

**Purpose & responsibilities.** Own the media-registration lifecycle for one MediaItem→authority submission: capture initiation, accumulate supporting documents, drive owner submission and authority decision, support rejection/resubmission retry cycles, and expose a post-confirmation amendment workflow.

**Aggregate root:** `Registration`. **Child entities:** none. **Value objects:** `RegistrationId`, `MediaItemId`, `MediaProfileId`, `RegistrationOfficerId`, `RegistrationType`, `RegistrationStatus`, `RegistrationReference`, `RegistrationItem`, `RegistrationItemType`, `Amendment`, `AmendmentId`, `AmendmentStatus`, `TenantId`. Healthy VO surface — not anemic.

**Key state:** `Status`, `MediaItemId`, `OfficerId` (owner), `RegistrationType`, `RegistrationAuthority` (normalised string), `Reference?`, `Items` (attached documents), `Amendments`, `SubmittedAt?`, `ConfirmedAt?`, `MediaProfileId`, and an always-null `Notes`.

**Invariants enforced in the aggregate (correct):**
- Status-gated transitions on every method: `Submit` requires `Initiated|Resubmitted` + ≥1 item (`Registration.cs:388-402`); `Resubmit` requires `Rejected`; `RecordSubmission` requires `Submitted`; `Confirm`/`Reject` require `SubmissionRecorded`; `Cancel` blocks `Confirmed`/`Cancelled`; amendment methods require `Confirmed`.
- Duplicate-document guard on attach (`Items.Any(d => d.MediaItemId == mediaItemId)`, `:187`).
- One-pending-amendment-per-MediaItem guard (`:351`).
- Attach blocked when `Confirmed` (→ amendment workflow, `:177-180`) and when `Cancelled` (`:182-185`).
- Two-event atomic write on `ApproveAmendment`: `RegistrationAmendmentApproved` + `RegistrationItemAttached` in one `Emit` sequence (`:154-155`) — matches the spec design note exactly.
- Timestamps are passed in from the handler/endpoint and stamped into events (no `UtcNow` inside domain methods) — replay-correct. Good.

**Aggregate boundary assessment:** boundaries are appropriate. The aggregate correctly does **not** own MediaItem existence/publish/capability checks (delegated to the handler via `IMediaItemRegistrationContextService`), and correctly trusts the handler for those. Size is reasonable.

**Aggregate-level defects (detailed in §12–13):**
- **RG-D1 (Medium, spec mismatch / naming).** The aggregate's `RegistrationStatus` enum (`RegistrationStatus.cs:3-12`) has seven values and uses **`SubmissionRecorded`** for the post-dispatch state. The write-model spec lifecycle, the API error bodies (`registration.api.md:230-249`) and the scenarios all call this state **`PendingConfirmation`**, and the read-model spec enum lists *both* plus five never-used amendment/approval states. `Confirm`/`Reject` guard on `SubmissionRecorded` (`:232, :277`), so the code is internally consistent — but it silently contradicts three of its own spec documents.
- **RG-D2 (Medium, domain modelling).** `Notes` is a first-class aggregate property (`:60`) and appears in `RegistrationDetailReadModel`, yet **no event ever sets it** — `RegistrationInitiated` carries no `Notes` field and the factory takes none, though the write-model spec lists `Notes?` on both the initiate command and the creation event. Owner notes are unreachable; the property is dead.
- **RG-D3 (Low, correctness).** `ApproveAmendment` re-attaches the amendment's `MediaItemId` without checking it isn't already in `Items` (`:154-155`), so an amendment for an already-attached document produces a duplicate `RegistrationItem`. The pre-confirmation `AttachMediaItem` path *does* dedupe (`:187`); the amendment path does not.
- **RG-D4 (Low, generic errors).** Every guard returns `DomainErrors.InvalidOperation(...)` (`DomainErrors.cs`), collapsing the catalog's distinct codes and 409/422 distinction (see §12 M-block and §11).

---

## 3. Lifecycle Analysis

### State machine (reconstructed from `Registration.cs` guards + `Apply` handlers)

```text
                          Initiate (handler: MediaItem Published + Registration capability)
                                             │
                                             ▼
                                        Initiated ──────────────┐
                                             │                  │ AttachMediaItem (≠Confirmed,≠Cancelled)
                                             │  Submit (≥1 item) │  (self-loop, accumulates Items)
                                             ▼                   │
                                        Submitted ◄──────────────┘
                                             │
                                             │  RecordSubmission (System)
                                             ▼
                                    SubmissionRecorded            ← spec calls this "PendingConfirmation"
                              ┌──────────────┴───────────────┐
                   Confirm (System)                     Reject (System, reason required)
                              │                               │
                              ▼                               ▼
                         Confirmed [terminal]             Rejected
                   (amendments only)                          │  Resubmit
                   RequestAmendment (owner) ─┐                ▼
                   ApproveAmendment (System) │           Resubmitted
                     └ +RegistrationItemAttached          │  Submit (≥1 item)
                   RejectAmendment  (System) │             ▼
                                             ┘         Submitted … (retry cycle)

     Cancel (owner) valid from any status except Confirmed and Cancelled → Cancelled [terminal]
```

**Terminal states:** `Confirmed` (legal record — amendments only), `Cancelled`. **Retry cycle:** `Rejected → Resubmitted → Submitted → SubmissionRecorded → …`.

### Lifecycle issues

- **RG-L1 (Medium) — Read-model status can never reach the states the read-model spec/enum defines.** The read-model spec enum defines `PendingConfirmation`, `Approved`, `AmendmentRequested`, `AmendmentApproved`, `AmendmentRejected`; the aggregate produces none of these, and (correctly) does **not** move top-level `Status` on amendment request/approve/reject. The read-model projector spec's "set aggregate `Status=AmendmentRequested`" instruction (`registration.read-model.md:120`) is therefore unimplementable and was rightly ignored — but the spec still asserts it.
- **RG-L2 (Low) — No timeout/compensation on the System-actor half.** `SubmissionRecorded` waits indefinitely for an external `Confirm`/`Reject`. The context-overview references a "saga orchestrator" that triggers authority submission, but there is no timeout scanner or compensation for a submission that is dispatched and never answered. Acceptable for v1 if the external adapter guarantees a terminal callback, but there is no in-platform recovery path. (The module has no saga of its own — consistent with the spec.)
- **RG-L3 (Low) — `Cancelled` and `Confirmed` read-model rows have no removal path.** Expected for a legal-records domain (retention semantics in `registration.write-model.md:282-331` require it), so this is by design — noted only for completeness. `ExpiresAt` on the detail read model is presumably meant to drive the `Cancelled`=3-years / `Confirmed`=10-years retention but is **never populated** (§8).

---

## 4. Commands

11 commands, each with a dedicated handler. `⚠` marks a command with at least one finding (detailed in §12–15).

| Command | Handler | Actor (spec) | Notes |
|---|---|---|---|
| InitiateRegistrationCommand | InitiateRegistrationHandler | Owner | ⚠ no owner/actor binding used; generic errors; `Notes` dropped |
| AttachMediaItemToRegistrationCommand | AttachMediaItemToRegistrationHandler | Owner | ⚠ **inverted capability guard** (RG-C2); no owner check |
| SubmitRegistrationCommand | SubmitRegistrationHandler | Owner | ⚠ no owner check |
| ResubmitRegistrationCommand | ResubmitRegistrationHandler | Owner | ⚠ no owner check; wrong-status → 422 not 409 |
| CancelRegistrationCommand | CancelRegistrationHandler | Owner | ⚠ no owner check |
| RecordRegistrationSubmissionCommand | RecordRegistrationSubmissionHandler | **System** | ⚠ **no `actor_type=System` check** (RG-C1) |
| ConfirmRegistrationCommand | ConfirmRegistrationHandler | **System** | ⚠ **no System check**; empty `reference` → 500 (RG-C1/RG-H2) |
| RejectRegistrationCommand | RejectRegistrationHandler | **System** | ⚠ **no System check** |
| RequestAmendmentCommand | RequestAmendmentHandler | Owner | ⚠ **inverted capability guard** (RG-C2); no owner check |
| ApproveAmendmentCommand | ApproveAmendmentHandler | **System** | ⚠ **no System check**; two-event atomic write ✔ |
| RejectAmendmentCommand | RejectAmendmentHandler | **System** | ⚠ **no System check** |

**Cross-cutting command issues:**
- **Every command carries a `RequestingUser`/`RequestedBy`/`OfficerId`** (sourced from `context.Actor.Id` in the endpoint) **but no handler ever compares it to `registration.OfficerId`** — the PERM ownership check is impossible even though the identity is threaded through (§12 RG-C1). The five System commands carry no actor-type assertion at all.
- **No missing/duplicate/redundant commands.** The 11 commands map cleanly 1:1 to aggregate methods; the command set matches the API surface.
- **`RecordRegistrationSubmissionCommand`** adds `ExternalReference`/`Notes` (not in the write-model command spec, which is `RecordRegistrationSubmissionCommand(RegistrationId)`), carried into `RegistrationSubmissionRecorded`. Reasonable extension, but undocumented and the projector maps `Notes → DispatchDetails` oddly (§9/§8).
- **Handlers return generic errors** (`InvalidOperation`, `ResourceNotFound`) rather than catalog codes (§11).

---

## 5. Queries

4 queries — `GetRegistrationById`, `ListRegistrationsByMediaItem`, `ListRegistrationsByOwner`, `SearchRegistrations`.

| Query | Paging | Owner scope | Notes |
|---|---|---|---|
| GetRegistrationByIdQuery | n/a | ⚠ none | any caller reads any registration in the tenant |
| ListRegistrationsByMediaItemQuery | cursor (ADR-014 ✔) | ⚠ none | returns all owners' registrations for the item |
| ListRegistrationsByOwnerQuery | cursor ✔ | ✔ (`context.Actor.Id`) | correctly owner-scoped |
| SearchRegistrationsQuery | OpenSearch `search_after` ✔ | ⚠ tenant-only | User results **not** scoped to `OwnerId` (spec requires it); index never populated |

**Query issues:**
- **CQRS boundary is clean** — handlers return DTOs / read models only, no aggregates or event payloads cross the boundary; cursor-only pagination with no total count matches ADR-014. Good.
- **Owner scoping is missing on 3 of 4 read paths** (§12 RG-C1). `GetRegistrationById` and `ListRegistrationsByMediaItem` return any owner's data within the tenant; the search DSL filters `TenantId.keyword` only (`SearchRegistrationsHandler.cs:48-49`) although `registration.api.md:436` requires `actor_type=User` results be scoped to `OwnerId`.
- **Search is non-functional** — see §12 RG-H1: the two projectors write only DynamoDB; nothing indexes into the OpenSearch `registrations` index the handler queries.
- **No missing query capability** — the by-owner / by-item / by-id / search set matches the spec.

---

## 6. API Endpoints

Spec (`registration.api.md`) vs implementation. All endpoints are `Version(1)`; all advertise `401/403` but no code path can emit `403`.

| Spec route | Verb | Impl? | Impl status | Note |
|---|---|---|---|---|
| /v1/items/{itemId}/registrations | POST | ✔ | 201 | ok; tag "Catalog"; summary Param key `mediaItemId`≠route `itemId` |
| /v1/registrations/{id}/documents | POST | ✔ | 204 | spec scenarios say 200; 204 matches api.md |
| /v1/registrations/{id}/submit | POST | ✔ | 204 | ok |
| /v1/registrations/{id}/resubmit | POST | ✔ | 204 | ok |
| /v1/registrations/{id}/cancel | POST | ✔ | 204 | dead `CancelRegistrationResponse` type |
| /v1/registrations/{id}/amendments | POST | ✔ | 201 | ok |
| /v1/registrations/{id}/submission `[System]` | POST | ✔ | 204 | **no System enforcement** |
| /v1/registrations/{id}/confirm `[System]` | POST | ✔ | 204 | **no System enforcement**; empty ref → 500 |
| /v1/registrations/{id}/reject `[System]` | POST | ✔ | 204 | **no System enforcement** |
| /v1/registrations/{id}/amendments/{amendmentId}/approve `[System]` | POST | ✔ | 204 | **no System enforcement** |
| /v1/registrations/{id}/amendments/{amendmentId}/reject `[System]` | POST | ✔ | 204 | **no System enforcement** |
| /v1/registrations/{id} | GET | ✔ | 200 | leaks `TenantId`; no owner scope |
| /v1/registrations?mediaItemId= | GET | ✔ | 200 | no owner scope on item path |
| /v1/registrations/search?q= | GET | ✔ | 200/400 | 400-on-empty-`q` ✔; index unpopulated |

**Endpoint issues:**
- **No endpoint declares authorization** (no `Roles/Permissions/Policies/PreProcessor`, no `actor_type` gate). Every `ProducesProblem(403)` is unbacked. (§12 RG-C1)
- **RFC 9457 `errorCode` not emitted.** Both endpoint bases do `AddError(message)` + `SendErrorsAsync(status)` (write base `RegistrationEndpoint.cs:20-24`; read base flattens to `NotFound→404 / Forbidden→403 / _→500`, `ReadModel.Endpoints/…/RegistrationEndpoint.cs:23-29`). No `extensions.errorCode`, contradicting `api-conventions.md`/`error-catalog.md`.
- **Empty `reference` returns 500, not 422.** `ConfirmRegistrationEndpoint.cs:51` constructs `new RegistrationReference(req.Reference)` *in the endpoint*; the VO throws `ArgumentException` on empty (`RegistrationReference.cs:7-10`) → unhandled → 500. Spec requires `422 ReferenceRequired`. (§12 RG-H2)
- **Malformed ids → 500.** `RegistrationId.Parse`/`AmendmentId.From` call `Guid.Parse` (throws) with no validator; spec expects 400. (§12 RG-M-block)
- **Doc-comment drift:** Initiate summary says "begins in Draft state" (actual: `Initiated`); Confirm/Reject summaries say "Submitted → Confirmed/Rejected" (actual source state: `SubmissionRecorded`); RecordRegistrationSubmission summary describes it as recording *authority confirmation of receipt* (actual: owner-dispatch record). Cosmetic but ships to the wiki.
- **Dead response types:** `CancelRegistrationResponse`, `SubmitRegistrationResponse`, `ResubmitRegistrationResponse` are declared as the endpoint `TResponse` but the handlers all `SendNoContentAsync` (204) — the DTOs are never serialized.

---

## 7. Request DTO Review

| DTO | Findings |
|---|---|
| InitiateRegistrationRequest | `ItemId` bound from route `{itemId}`; no `Notes` field (spec allows notes on initiate); no validation |
| AttachMediaItemToRegistrationRequest | `ItemId` + `RegistrationId` (both string, no GUID validation); enum `ItemType` binds silently to `0=ApplicationForm` if omitted/invalid |
| ConfirmRegistrationRequest | `Reference = null!` → empty/omitted body → **500** via VO throw (RG-H2); `RegistrationId` string unvalidated |
| RejectRegistrationRequest | `Reason` unvalidated (empty rejected in aggregate → 422, but no coded error) |
| RecordRegistrationSubmissionRequest | `ExternalReference`/`Notes` optional; undocumented vs spec |
| RequestAmendmentRequest | `ItemId`/`ItemType`/`Notes`; no length pre-check (aggregate caps notes at 1000) |
| Approve/RejectAmendmentRequest | `AmendmentId` string → `Guid.Parse` throw on malformed → 500 |

**Cross-cutting:**
- **No FluentValidation validators anywhere in the module** (none exist in the tree). Consequence: `Guid.Parse` in `RegistrationId.Parse` / `AmendmentId.From`, and the `RegistrationReference` constructor, **throw on malformed/empty input → unhandled → 500** where the spec expects 400/422. The module's `spec` requires validators per the platform convention; none are present.
- **Enum binding:** `RegistrationType`/`RegistrationItemType` bind from JSON; an out-of-range or omitted value silently becomes the `0` enum member (`Electronic` / `ApplicationForm`) rather than 400. No `[Required]`/validator.
- **Field-naming inconsistency:** the media-item is `ItemId` on requests but `MediaItemId` on the command/event/read model — the same divergence flagged elsewhere in the platform.

---

## 8. Response DTO Review

| DTO | Findings |
|---|---|
| InitiateRegistrationResponse | `(Id, MediaItemId, Timestamp)` — matches api.md ✔ |
| RequestAmendmentResponse | `(RegistrationId, Id, Timestamp)` — spec shows `{id}` only; extra fields, harmless |
| GetRegistrationByIdResponse | **leaks `TenantId`**; exposes **both** `ExternalReference` and `ReferenceNumber` (spec GET returns single `reference`); exposes always-null `ExpiresAt`; `Notes` actually carries dispatch details (§9) |
| RegistrationSummaryModel | **leaks `TenantId`**; single `Reference` (ok) |
| ListRegistrationsResponse / SearchRegistrationsResponse | `(Items, PageSize, NextPageToken/NextSearchAfter)` — matches api.md ✔ |
| RegistrationAmendmentModel | carries `RequestedBy` + `Notes` (present in code, **absent from the write-model amendment VO spec**) |
| Cancel/Submit/ResubmitRegistrationResponse | dead — never serialized (§6) |
| RegistrationDocumentDto | **dead type** — never referenced (Items use `RegistrationItemDto`) |

**Cross-cutting:**
- **`TenantId` leakage** in both the detail and summary responses — a multi-tenancy boundary value that should never round-trip to clients.
- **Dual reference fields** (`ExternalReference` = owner dispatch ref from `RegistrationSubmissionRecorded`; `ReferenceNumber` = authority ref from `RegistrationConfirmed`) are both exposed where the API spec shows one `reference`. Confusing and leaks internal submission bookkeeping.
- **`Notes` semantics bug:** `RegistrationDetailProjector` sets `Notes = e.DispatchDetails` on `RegistrationSubmissionRecorded` (`RegistrationDetailProjector.cs:72`). The GET response `notes` field therefore surfaces *dispatch details*, not the owner notes the API example implies. Owner notes are never captured (RG-D2).
- **Always-null exposed fields:** `ExpiresAt` (never set anywhere).

---

## 9. Domain Events

11 domain events, all registered in the aggregate's `When<>` block (`Registration.cs:19-29`) and all handled by an `Apply`. Publisher = `Registration` aggregate.

| Domain event | Summary proj. | Detail proj. | Integration mapped? | Notes |
|---|---|---|---|---|
| RegistrationInitiated | ✔ | ✔ | ✔ | no `Notes` field (spec lists `Notes?`) |
| RegistrationSubmitted | ✔ | ✔ | ✔ | |
| RegistrationSubmissionRecorded | ✔ | ✔ | ✖ (internal) | detail maps `SubmissionReference→ExternalReference`, `DispatchDetails→Notes` |
| RegistrationConfirmed | ✔ | ✔ | ✔ | carries full payload for the confirmed integration event ✔ |
| RegistrationRejected | ✔ | ✔ | ✔ | |
| RegistrationResubmitted | ✔ | ✔ | ✔ | detail/summary set status `Resubmitted` (spec table says `Submitted`) |
| RegistrationCancelled | ✔ | ✔ | ✔ | |
| RegistrationItemAttached | ✖ | ✔ | internal only ✔ | summary needs no items — correct |
| RegistrationAmendmentRequested | ✖ | ✔ | internal only ✔ | |
| RegistrationAmendmentApproved | ✖ | ✔ | internal only ✔ | followed atomically by ItemAttached ✔ |
| RegistrationAmendmentRejected | ✖ | ✔ | internal only ✔ | |

**Notes:**
- **Timing/ownership correct.** Timestamps event-stamped from the handler; the two-event amendment-approval write is emitted atomically as the spec requires.
- **`RegistrationResubmitted.SubmittedAt`** naming: the field is called `SubmittedAt` but semantically it is *resubmitted-at*; the summary projector maps it into `SubmittedAt` and the detail into `SubmittedAt` — the read-model `SubmittedAt` is thus overwritten on resubmit before the actual re-`Submit`. Minor.
- **Read-model spec vs code status drift:** the read-model projector table maps `RegistrationResubmitted → status "Submitted"` and `RegistrationSubmissionRecorded → "SubmissionRecorded"`, while the write-model lifecycle uses `PendingConfirmation`. The code uses `Resubmitted` and `SubmissionRecorded`. Code is self-consistent; the spec documents disagree with each other (§11).
- **No duplicate events**; `RegistrationItemAttached` correctly serves both the pre-confirmation attach and the amendment-approved attach, discriminated by `AddedViaAmendmentId`.

---

## 10. Integration Events

### Published — mapper `RegistrationDomainEventMapper.cs`

Six integration events, mapped 1:1 from the six spec-listed domain triggers (`RegistrationDomainEventMapper.cs:11-72`). Each carries `TenantId` (string), the relevant ids, and `EventVersion = e.AggregateVersion`. Amendment events + `RegistrationItemAttached` are correctly **not** mapped (domain-internal per the context overview).

| Spec message | Code type | Match |
|---|---|---|
| RegistrationInitiatedMessage | RegistrationInitiatedIntegrationEvent (`+MediaProfileId`, `+EventVersion`) | ✔ (superset — `media.registration.initiated`) |
| RegistrationSubmittedMessage | RegistrationSubmittedIntegrationEvent | ✔ |
| RegistrationResubmittedMessage | RegistrationResubmittedIntegrationEvent | ✔ |
| RegistrationConfirmedMessage | RegistrationConfirmedIntegrationEvent | ✔ (carries OwnerId, MediaItemId, reference, type, authority) |
| RegistrationRejectedMessage | RegistrationRejectedIntegrationEvent | ✔ |
| RegistrationCancelledMessage | RegistrationCancelledIntegrationEvent | ✔ |

**Issues:**
- **F-P1 (Low, doc).** The context-overview names the publisher `RegistrationIntegrationEventPublisher` and describes ADR-005 "inline publish in the command handler." The code uses the platform's `IDomainEventMapper<>` + `builder.UseIntegrationEventPublishing()` path (`WriteModel.Infrastructure/ServiceCollectionExtensions.cs:87-91`) — a mapper, not an inline publisher. Functionally equivalent and arguably better, but the spec name/mechanism is stale.
- **F-P2 (Low).** `RegistrationInitiatedIntegrationEvent` omits any `Notes` (consistent with the dropped-notes RG-D2); harmless downstream but diverges from the "carry full context" intent of the initiated message.
- **Idempotency/versioning:** each integration event carries `EventVersion`; no per-message dedup id is declared in the contract (delegated to the platform envelope — unverified).

### Consumed — `MediaItemReference` reference index (from Catalog)

Three consumer handlers (`MediaItemRegistrationContext{Created,Approved,Archived}EventHandler`) delegate to `MediaItemRegistrationIndexProjector`, maintaining the write-side `MediaItemReference` index used by the initiate/attach/amendment handlers.

| Issue | Severity | Detail |
|---|---|---|
| F-C1 | Medium | **Reorder drop:** `MediaItemApproved`/`MediaItemArchived` arriving before `MediaItemCreated` return `MissingCurrent` and are dropped (`MediaItemRegistrationIndexProjector.cs:41-43, 60-62`). A dropped `Approved` leaves `IsPublished=false` permanently (no re-send) → registration silently blocked for a legitimately-published item. Fail-closed (safer than the AssetManagement analogue) but still a correctness gap. Single version domain (all three from the MediaItem stream) — no cross-domain watermark mixing, good. |
| F-C2 | Low | The projector has no explicit `ProjectedVersion` monotonic guard; it relies on the platform store's conditional write. Unverified — confirm the store rejects stale `EventVersion`. |
| F-C3 | Low | `MediaItemRegistrationContextService` surfaces `IsPublished/HasRegistrationCapability/HasProcessingCapability/MediaProfileId` but **not** `IsArchived` (`MediaItemRegistrationContextService.cs:15`). Archive is folded into `IsPublished=false`, so the guard still works, but `IsArchived` is dead on the read side. |

---

## 11. Specification vs Repository Differences

| Item | Specification | Repository | Severity | Recommendation |
|------|---------------|------------|----------|----------------|
| Post-dispatch status name | `PendingConfirmation` (write-model lifecycle, api.md error bodies, scenarios) | `SubmissionRecorded` (aggregate enum + guards) | High | Pick one name; reconcile enum, spec lifecycle, API error bodies |
| Read-model status enum | 12 values incl. `PendingConfirmation`, `Approved`, `AmendmentRequested/Approved/Rejected` (`read-model.md:234-248`) | 7-value enum; none of the extra states produced | High | Delete the aspirational states from the spec enum |
| Attach/Amendment document guard | Document must be `Published` **and lack `Processing` capability** → `InvalidRegistrationItem` (`write-model.md:26, 180, 183`) | Handlers check `IsPublished` **and `HasRegistrationCapability`** | **Critical** | Replace `HasRegistrationCapability` with `!HasProcessingCapability` |
| Ownership authorization | `actor.Id == registration.OwnerId` on user writes/reads (`context-overview.md:56`, `api.md:45`, `security-scenarios.md`) | Not enforced anywhere; identity threaded but unused | **Critical** | Enforce owner check; return 403 `NotResourceOwner` |
| System-actor gate | `[System]` endpoints require `actor_type="System"` (`api.md:46`, `context-overview.md:56`) | No `actor_type` check on any system command/endpoint | **Critical** | Enforce `SystemActorRequired` (403) on confirm/reject/submission/approve/reject-amendment |
| Full-text search index | `RegistrationProjector` targets DynamoDB **+ OpenSearch `media-registrations`** (`read-model.md:63-88`) | No projector writes OpenSearch; search index never populated | High | Add an OpenSearch projector/indexer; align index name & fields |
| `ConfirmRegistration` empty reference | `422 ReferenceRequired` (`api.md:264`, `error-catalog.md:126`) | VO throws in endpoint → 500 | High | Validate in request/handler; return coded 422 |
| Coded errors / RFC 9457 | `error-catalog.md` codes + `errorCode` extension | Generic `InvalidOperation`; no `errorCode` | Medium | Emit coded errors + `errorCode` |
| Wrong-status HTTP code | `InvalidStatusTransition → 409` (`error-catalog.md:30`, api.md 409 bodies) | `InvalidOperation → 422` for all transition guards | Medium | Distinguish 409 transition vs 422 validation |
| `error-catalog` vs `api.md` status | catalog: `RegistrationConfirmed`, `DuplicatePendingAmendment`, `AmendmentNotPending` = **422**; api.md example bodies = **409** | code = 422 (matches catalog) | Medium (spec-internal) | Reconcile catalog vs api.md; the two spec docs disagree |
| `DocumentAlreadyAttached` code | referenced in api.md:109 + scenario R-6 (409) | not in `error-catalog.md`; code returns generic `InvalidOperation` (422) | Medium | Add the code to the catalog; emit it |
| Amendment VO shape | `RegistrationAmendment{AmendmentId, MediaItemId, ItemType, RequestedAt, Status, ResolvedAt?, DecisionNotes?}` (`write-model.md:98-108`) | `Amendment` adds `RequestedBy` + `Notes` | Low | Update the spec VO to include RequestedBy/Notes |
| Initiate `Notes` | `Notes?` on command + `RegistrationInitiated` (`write-model.md:136, 156`) | Not present on command/event/factory; aggregate `Notes` dead | Medium | Add `Notes` to command/event or remove from aggregate & spec |
| Detail read model `Notes` | owner free-text (api.md GET example) | populated from `DispatchDetails` | Medium | Separate dispatch details from owner notes |
| Scenario command/route shapes | R-4/R-6 use `POST /v1/registrations` w/ `mediaItemId` body, `registrationType:"Copyright"`, `itemType:"SupportingDocument"`, `jurisdiction:"AU"`, `Items` on init | route is `/items/{itemId}/registrations`; types are `Electronic\|Physical`; item types `ApplicationForm\|SupportingEvidence\|ConfirmationReceipt\|Other`; init takes no items | Low (spec) | Rewrite R-4/R-6 to the real contract |
| Detail table name | `media-registration-detail` | schema registered as `"media-registration"` (`ReadModel.Infrastructure/ServiceCollectionExtensions.cs:68`) | Low | Align table name |
| Projected read status on resubmit | read-model.md: `→ Submitted` | code: `→ Resubmitted` | Low (doc) | Fix spec table |

---

## 12. Bugs

### Critical

**RG-C1 — No ownership/authorization or System-actor enforcement anywhere (legal-record forgery + intra-tenant tampering/exfiltration).**
Verified across all 11 endpoints and handlers. No endpoint declares an auth policy; no handler compares `context.Actor.Id` to `registration.OfficerId`; the five `[System]` commands (`ConfirmRegistration`, `RejectRegistration`, `RecordRegistrationSubmission`, `ApproveAmendment`, `RejectAmendment`) perform no `actor_type == "System"` check (`ConfirmRegistrationCommandHandler.cs`, `RejectRegistrationHandler.cs`, `RecordRegistrationSubmissionHandler.cs`, `ApproveAmendmentHandler.cs`, `RejectAmendmentHandler.cs`, and their endpoints). `context-overview.md:40-56`, `api.md:42-49` and `security-scenarios.md` require both checks.
*Why it's a problem:* the confirm endpoint stamps an authoritative external `Reference` and moves the registration to the immutable, 10-year-retained `Confirmed` state. With no System gate, **any authenticated tenant user can call `POST /registrations/{id}/confirm` on their own registration and fabricate an official authority reference** — a falsified legal filing on a government/enterprise records platform. On the owner side, any tenant user can submit/cancel/attach-to/reject any other user's registration, and read (`GetRegistrationById`) or list-by-item any other owner's registration.
*Impact:* fabrication of legal records; cross-owner tampering; cross-owner data disclosure. *Recommendation:* enforce `actor.Id == OfficerId` (→ 403 `NotResourceOwner`) in all owner handlers; enforce `actor_type == "System"` (→ 403 `SystemActorRequired`) in the five system handlers; add owner scoping to `GetRegistrationById`, `ListRegistrationsByMediaItem`, and the search DSL (User → filter `OwnerId`).

**RG-C2 — Inverted document-eligibility guard on attach & amendment (rejects valid documents, admits processed media).**
`AttachMediaItemToRegistrationHandler.cs:38-41` and `RequestAmendmentHandler.cs:38-41` both do `if (!mediaItemRef.HasRegistrationCapability) return InvalidOperation(...)`. The spec invariant (`write-model.md:26, 180, 183`; scenarios R-1/R-6) is the **opposite**: an attachable document is a `Published` MediaItem whose profile **lacks the `Processing` capability** (`!HasProcessingCapability`), and it does **not** need the `Registration` capability. The context service already exposes `HasProcessingCapability` (`MediaItemRegistrationContext.cs:5`) — it is simply never consulted.
*Why it's a problem:* two-way wrong. Legitimate document media-items (which lack `Registration` capability) are rejected with a spurious 422, so the happy path in R-1/R-6 cannot complete; and processed media (video/audio/image with `Processing` capability) that happens to also carry `Registration` capability would be admitted as a "document," violating the quota-exempt-document invariant. *Impact:* core attach/amendment flows are broken and the document-type invariant is unenforced. *Recommendation:* replace the check with `if (mediaItemRef.HasProcessingCapability) return InvalidRegistrationItem(...)` and drop the `HasRegistrationCapability` requirement for attachments.

### High

**RG-H1 — Full-text search is wired to an OpenSearch index that no projector populates.**
`SearchRegistrationsHandler.cs:30` queries index `"registrations"`, but `RegistrationSummaryProjector` and `RegistrationDetailProjector` write only via `UpsertAsync` to the DynamoDB projection store — neither indexes into OpenSearch, and there is no separate search projector in the module (contrast the host list's `Projectors.Search`). `read-model.md:63-88` specifies an OpenSearch `media-registrations` index maintained by the projector.
*Why it's a problem:* `GET /v1/registrations/search` always returns an empty result set (best case) against a possibly non-existent index. The DSL also references fields the summary model doesn't carry (`ReferenceNumber`, `Notes`) and filters `TenantId.keyword` with no `OwnerId` scope. *Impact:* a documented, shipped query capability is non-functional; search results are silently empty. *Recommendation:* implement an OpenSearch indexing projector for the registration events, align the index name and field mappings with the DSL, and add the User `OwnerId` filter.

**RG-H2 — Empty/omitted `reference` on confirm returns 500 instead of 422 `ReferenceRequired`.**
`ConfirmRegistrationEndpoint.cs:51` constructs `new RegistrationReference(req.Reference)` inside `HandleAsync`; `RegistrationReference`'s constructor throws `ArgumentException` on null/whitespace (`RegistrationReference.cs:7-10`). `ConfirmRegistrationRequest.Reference` is `null!`, so an omitted/empty field throws before the command is even built → unhandled → 500. The aggregate's `Confirm` and the handler perform no reference check either. Spec: `422 ReferenceRequired` (`api.md:264`, `error-catalog.md:126`).
*Impact:* the documented 422 path is unreachable; malformed confirms surface as 500s. *Recommendation:* validate `reference` in the request validator/handler and return coded 422 before constructing the VO.

**RG-H3 — No request validation layer → malformed ids and enums yield 500.**
No FluentValidation validators exist in the module. `RegistrationId.Parse`/`AmendmentId.From` call `Guid.Parse` (throws on non-GUID route/body values, e.g. every write endpoint's `RegistrationId.Parse(req.RegistrationId)`); enum fields bind to `0` on omission/garbage. Spec expects 400 for malformed input.
*Impact:* trivial client errors become 500s; enum-omission silently defaults `RegistrationType=Electronic` / `ItemType=ApplicationForm`. *Recommendation:* add FastEndpoints validators (id well-formedness, required enums, `pageSize` cap, notes ≤1000, non-empty `reference`/`reason`).

**RG-H4 — Read endpoints leak `TenantId` and dual internal reference fields; no owner scoping.**
`GetRegistrationByIdResponse`/`RegistrationSummaryModel` include `TenantId`; the detail response exposes both `ExternalReference` (dispatch bookkeeping) and `ReferenceNumber` plus always-null `ExpiresAt`; and (per RG-C1) `GetRegistrationById`/`ListRegistrationsByMediaItem` apply no owner scope.
*Impact:* multi-tenant boundary value disclosure + internal submission bookkeeping exposed + cross-owner reads. *Recommendation:* drop `TenantId` from responses; expose a single `reference`; owner-scope the reads.

### Medium

- **RG-M1** — Generic errors throughout: `DomainErrors` collapses `RegistrationConfirmed`, `RegistrationAlreadyCancelled`, `DuplicatePendingAmendment` (=`InvalidOperation`), `UseAmendmentWorkflow`, document-already-attached, wrong-status, amendment-not-pending all to `DomainError.InvalidOperation` (422). The catalog's coded errors and the `InvalidStatusTransition`→409 distinction are lost, so clients cannot machine-discriminate retryable (409) from invalid (422) and get no `errorCode`. (`DomainErrors.cs`, `Registration.cs` guards.)
- **RG-M2** — `RegistrationDetailProjector` maps `RegistrationSubmissionRecorded.DispatchDetails → Notes` (`:72`), so the GET `notes` field surfaces dispatch details rather than owner notes; true owner notes are never captured (RG-D2). Two reference fields (`ExternalReference`, `ReferenceNumber`) further muddy the read model.
- **RG-M3** — `MediaItemReference` projector drops out-of-order `Approved`/`Archived` before `Created` (F-C1); a dropped `Approved` blocks registration for a published item with no re-drive.
- **RG-M4** — Wrong-status transitions (submit/resubmit/confirm/reject/record from an invalid state) return 422 where `error-catalog.md` classifies `InvalidStatusTransition` as 409; the api.md example bodies also use 409. (Note the catalog itself lists several registration-specific codes as 422 — a spec-internal contradiction to resolve, §11.)
- **RG-M5** — `Notes`/`RegistrationInitiated` mismatch: the write-model spec puts `Notes?` on initiate; the code omits it, leaving the aggregate `Notes`, the read-model `Notes`, and the initiated integration event unable to carry owner notes.
- **RG-M6** — Projector idempotency not visibly enforced: both read projectors and the reference projector set `ProjectedVersion = e.AggregateVersion`/`e.EventVersion` but contain no explicit `if (incoming <= current.ProjectedVersion) skip` guard; `read-model.md:101,125` claims a `ProjectedVersion` dedup guard. Relies on the platform store's conditional write — verify, since duplicate SQS delivery of `RegistrationItemAttached` would otherwise append a duplicate item.

### Low

- **RG-L4** — `ApproveAmendment` can double-attach an already-attached `MediaItemId` (RG-D3).
- **RG-L5** — Dead code: `RegistrationDocumentDto`, `CancelRegistrationResponse`, `SubmitRegistrationResponse`, `ResubmitRegistrationResponse`, aggregate `Notes`, read-model `ExpiresAt`, `MediaItemReference.IsArchived` (unused on the read path).
- **RG-L6** — Doc-comment/summary drift: "Draft"/"Submitted → Confirmed" in endpoint summaries; RecordRegistrationSubmission summary mislabels the operation; api.md `.Related` link and several scenario shapes are stale (§11).
- **RG-L7** — Detail projection schema table name `"media-registration"` vs spec `media-registration-detail`; detail projection key discriminator `"DETAIL"` vs registered entity `"REGISTRATION"` — verify these resolve to the intended partition.
- **RG-L8** — `RegistrationResubmitted.SubmittedAt` overwrites the read-model `SubmittedAt` on resubmit (before the actual re-submit), so the summary's `submittedAt` briefly reflects the resubmit timestamp.

---

## 13. Design Flaws

1. **Authorization is not modelled at all.** Owner identity is dutifully threaded from `context.Actor.Id` into every command yet never checked, and the System/User actor distinction — which is the entire security basis for letting an integration adapter (and *only* an adapter) confirm a legal filing — has no enforcement point. For a compliance-grade, government-facing records system this is the single biggest architectural weakness (RG-C1).

2. **A cross-cutting capability concept is applied inconsistently.** "Has Registration capability" gates the *target* item at initiate (correct) but is mistakenly reused to gate *document attachments* (RG-C2), where the real predicate is "lacks Processing capability." The two predicates are conflated in the handler layer even though the reference model exposes both booleans.

3. **The read model has drifted into a superset of two conflicting specs.** `RegistrationDetailReadModel` carries `ExternalReference`, `ReferenceNumber`, `Notes` (=dispatch details), `ExpiresAt`, `RejectedAt`, `CancelledAt` — a mix of populated, mis-populated, and never-populated fields — because it tried to satisfy both the write-model VO and the aspirational read-model enum/table. The result leaks internal bookkeeping and exposes dead fields.

4. **Search was designed as OpenSearch-backed but only the query half was built.** The handler, cursor codec, index name, and DSL are all present and reasonable, but no write path feeds the index — a half-implemented capability that reads as "done" from the endpoint surface (RG-H1).

5. **The error contract is bypassed at the domain layer.** Returning generic `InvalidOperation` everywhere collapses the catalog's 409/422 (retry-ability) distinction and prevents machine-discriminable `errorCode`, while input-shape errors escape as 500 for lack of validators.

6. **The status vocabulary is unsettled.** `SubmissionRecorded` (code) vs `PendingConfirmation` (spec) is not a cosmetic naming nit — it means the aggregate, the API error bodies, the scenarios, and the read-model enum are four sources of truth that disagree on the state graph.

---

## 14. Design Gaps

- **No authorization layer** (owner check + `actor_type` gate) — the largest gap.
- **No request-validation layer** (no FluentValidation) → no 400/422 for malformed input; VO throws surface as 500.
- **No RFC 9457 `errorCode` emission** and no coded domain errors mapped to catalog status codes.
- **No OpenSearch indexing projector** — search is non-functional (RG-H1).
- **No owner scoping** on `GetRegistrationById`, `ListRegistrationsByMediaItem`, or the search DSL.
- **No idempotency-key handling** visible on any mutating endpoint, though `api.md` states all mutating endpoints accept `IdempotencyKey` (may be platform-level — verify).
- **No explicit projector version-dedup guard** (RG-M6) — relies on unverified platform behaviour.
- **No timeout/compensation** on the `SubmissionRecorded` wait (RG-L2) — acceptable if the adapter guarantees a terminal callback, but undocumented.
- **Owner notes have no capture path** (RG-D2/RG-M5).
- **Retention/`ExpiresAt` not implemented** — the 3-year/10-year retention policy in `write-model.md` has no code (`ExpiresAt` always null); SPEC-17 offboarding acknowledged as not-yet-built.

---

## 15. Missing Features

- **Ownership + System-actor enforcement** on every write and read (identity is present but unchecked).
- **OpenSearch registration indexer** feeding the `registrations` search index.
- **FluentValidation validators** for all request DTOs (ids, enums, `reference`, `reason`, `pageSize`, notes length).
- **Coded domain errors** mapped to the catalog (`RegistrationConfirmed`, `DuplicatePendingAmendment`, `AmendmentNotPending`, `ReferenceRequired`, `NoDocumentsAttached`, `MediaItemNotPublished`, `DocumentAlreadyAttached`, `NotResourceOwner`, `SystemActorRequired`, `InvalidStatusTransition`) with RFC 9457 `errorCode` emission.
- **`Notes` capture** on `InitiateRegistration` (or removal from the model/spec).
- **`DocumentAlreadyAttached` catalog entry** (referenced by api.md/R-6 but absent from `error-catalog.md`).
- **`ExpiresAt`/retention population** for the documented `Cancelled`=3y / `Confirmed`=10y lifecycle.
- **Idempotency-key handling** if not provided by the platform.

---

## 16. Recommendations (prioritised)

### 1 — Correctness
- **R1 (Critical).** Fix the inverted document guard (RG-C2): in `AttachMediaItemToRegistrationHandler` and `RequestAmendmentHandler`, reject on `HasProcessingCapability == true` and drop the `HasRegistrationCapability` requirement; return coded `InvalidRegistrationItem` (422). Add a happy-path integration test proving R-1/R-6 complete.
- **R2 (High).** Implement the OpenSearch indexer so `GET /registrations/search` returns data; align index name + field mappings with the handler DSL; add the User `OwnerId` filter (RG-H1).
- **R3 (High).** Add validators so malformed ids/enums and empty `reference`/`reason` return 400/422, not 500 (RG-H2/RG-H3).

### 2 — Data Integrity
- **R4 (Medium).** Verify (or add) a `ProjectedVersion` dedup guard on all three projectors so duplicate SQS delivery of `RegistrationItemAttached`/`AmendmentRequested` cannot append duplicates (RG-M6); dedupe amendment re-attach (RG-D3).
- **R5 (Medium).** Harden the `MediaItemReference` projector against reordered `Approved`/`Archived`-before-`Created` (persist a tombstone / re-drive) (RG-M3/F-C1).
- **R6 (Medium).** Separate dispatch details from owner notes in the detail read model; stop overwriting `Notes` with `DispatchDetails`; capture owner `Notes` on initiate (RG-M2/RG-M5/RG-D2).

### 3 — Security
- **R7 (Critical).** Implement authorization: enforce `actor.Id == OfficerId` (→ 403 `NotResourceOwner`) in the six owner handlers; enforce `actor_type == "System"` (→ 403 `SystemActorRequired`) in the five system handlers; owner-scope `GetRegistrationById`, `ListRegistrationsByMediaItem`, and the search DSL (RG-C1). Add a test that a User token is rejected 403 on `/confirm`.
- **R8 (High).** Drop `TenantId` (and internal `ExternalReference`/`ExpiresAt`) from read responses; expose a single `reference` (RG-H4).

### 4 — Domain Modelling
- **R9 (Medium).** Return catalog-coded `DomainError`s with `errorCode` and the 409/422 distinction from aggregate guards and handlers; add the missing `DocumentAlreadyAttached` code (RG-M1/RG-M4).
- **R10 (Medium).** Resolve the `SubmissionRecorded` vs `PendingConfirmation` naming across aggregate, write-model spec, api.md error bodies, scenarios, and the read-model enum — one canonical vocabulary (RG-D1/§11).

### 5 — Lifecycle
- **R11 (Low).** Document (or implement) a timeout/compensation for a `SubmissionRecorded` registration that never receives a terminal authority callback (RG-L2); implement `ExpiresAt`/retention or mark it explicitly deferred.

### 6 — API
- **R12 (Medium).** Emit RFC 9457 problem-details with `errorCode`; stop the read base flattening domain errors to 500; return 409 for status-transition conflicts.
- **R13 (Low).** Fix endpoint summaries/Swagger params (Draft→Initiated, correct source states, `itemId` param key), and remove the dead response DTOs (`Cancel/Submit/Resubmit`) and `RegistrationDocumentDto`.

### 7 — Events
- **R14 (Low).** Confirm the integration-publisher mechanism vs the spec's named `RegistrationIntegrationEventPublisher`; either adopt the spec name or update the context-overview to describe the mapper path (F-P1).

### 8 — Maintainability
- **R15 (Low).** Reconcile the four Registration spec docs before the next wiki publish: read-model enum (delete unused states), read-model projector status table (`Resubmitted`/`SubmissionRecorded`), scenario R-4/R-6 command/route/type shapes, `error-catalog` vs api.md status codes, and the amendment VO shape (RequestedBy/Notes).

### 9 — Performance
- **R16 (Low).** Enforce the `pageSize` cap (100) locally on list/search rather than relying on unverified platform `PagerParameters`.

### 10 — Scalability
- **R17 (Low).** Once the OpenSearch indexer exists (R2), confirm the two-field `search_after` sort (`InitiatedAt desc, RegistrationId.keyword asc`) is backed by a mapping that makes both fields sortable, to preserve the deep-pagination guarantee the handler advertises.

---

### Top 5 before production
1. **RG-C1 / R7** — no ownership or System-actor enforcement: any tenant user can self-confirm a registration and fabricate an official authority reference (legal-record forgery), and can read/tamper with other owners' registrations.
2. **RG-C2 / R1** — inverted document-eligibility guard: attach/amendment reject valid documents and admit processed media, breaking the core happy path and the document invariant.
3. **RG-H1 / R2** — full-text search queries an OpenSearch index no projector populates: `GET /registrations/search` is non-functional.
4. **RG-H2 + RG-H3 / R3** — no validation layer: empty `reference` and malformed ids return 500 instead of the documented 400/422.
5. **RG-D1 / R10** — `SubmissionRecorded` vs `PendingConfirmation`: aggregate, API error bodies, scenarios, and read-model enum disagree on the state graph — reconcile before the contract ossifies.
