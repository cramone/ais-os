# ChangeRequests — Module Architecture Review (Specification vs Repository)

_Module: **ChangeRequests** (bounded context) — magiq-media · Aggregate: **MediaChangeRequest** (implemented as `ChangeRequest`)_
_Reviewer role: Principal Domain Architect (DDD / CQRS / Event Sourcing / API)_
_Date: 2026-07-19_
_Scope: `src/modules/ChangeRequests/**` (the `ChangeRequest` aggregate slice — all layers) vs `docs/spec/contexts/ChangeRequests/**` (context-overview, business-scenarios, and the `MediaChangeRequest` write-model / read-model / api / scenarios specs) + shared conventions (`api-conventions`, `error-catalog`, `security-scenarios`, `bulk-operations`, `media-types`), `adrs/api-http-conventions.md` (ADR-012 response-identifier naming, ADR-014 pagination), ADR-005 (inline integration-event publishing), and `adrs/catalog-domain-invariants.md`._

> Method: all 71 production `.cs` files in `src/modules/ChangeRequests/**` were read (Domain, Contracts, WriteModel, WriteModel.Endpoints, WriteModel.Infrastructure, ReadModel, ReadModel.Endpoints, ReadModel.Infrastructure) and compared line-by-line against the four `MediaChangeRequest` aggregate specs plus the context overview and shared docs. The Catalog `MediaItem` aggregate (which now owns the review lifecycle) and the `Magiq.Platform` SDK are referenced only where `ChangeRequest` depends on them; findings that hinge on platform-base behaviour that could not be read directly (snapshot policy, optimistic-concurrency retry, idempotency middleware, `DomainError` → `errorCode` mapping) are flagged as such.
>
> **Filename note:** named `changerequests-architecture-review.md` to match the single-aggregate precedent set by `assetmanagement-architecture-review.md`, rather than the prompt's `catalog-…` template string (a copy-paste artifact from the Catalog runs — this aggregate is not in the Catalog context).

---

## 1. Module Summary

ChangeRequests owns a single aggregate, `ChangeRequest` (spec name: `MediaChangeRequest`, stream type `media.changerequest`). In its **current, shipped form it is a pure comment thread** attached to a MediaItem review cycle: it holds a fixed participant roster, a list of soft-deletable threaded comments, and nothing else. All review lifecycle — status, reviewer roster, approve/reject/abandon decisions — has been moved to the Catalog `MediaItem` aggregate and its embedded `ReviewSession`. The module comprises one event-sourced aggregate, one published integration event (`ChangeRequestCreatedIntegrationEvent`), one inbound integration-event consumer that creates the thread, three DynamoDB read models (summary, detail, per-comment) maintained by three projectors, and seven HTTP endpoints (three write, four read).

Structurally the slice is clean and idiomatic for this codebase: command-per-folder, thin FastEndpoints, a domain-event → integration-event mapper, `Result<T, DomainError>` handlers, per-comment projection to avoid unbounded read-model rows. The comment-threading model itself is reasonable.

However, the module is **not production-ready**, and the dominant problem is **not the code — it is that the specification is in a three-way inconsistent state** and the code silently diverges from all three versions of it. The review surfaced two thematic clusters:

1. **The specification has not been reconciled after the "comment-only" refactor.** `context-overview.md` and `mediachangerequest.read-model.md` still describe the *old* full-lifecycle model (reviewer rosters, `Status`/`Binding`, `Approved`/`Rejected`/`Abandoned`, five integration events, saga coordination). `write-model.md`, `scenarios.md` and `api.md` describe the *new* comment-only model — but even those contradict each other (public create endpoint vs system-created; bodies-never-in-aggregate vs bodies-in-aggregate). The `error-catalog` ChangeRequests section is entirely the old reviewer surface. A reviewer or new engineer reading the spec will be actively misled. This is the single most important finding of the review.

2. **A small cluster of real correctness / security / reliability defects in the code.** The aggregate snapshot silently drops the participant roster and review-session id (breaking the core write path once a snapshot is taken); comment-body validation is missing at the command boundary and the only enforcement is a *throwing* `Result.Value` inside an `Apply` handler (unhandled 500 instead of 400); the body length limit is 255 chars vs the spec's 4 000; **read endpoints perform no authorization at all** in a government/compliance context; authorship and not-found failures return `InvalidOperation` (422) instead of the catalog's `NotCommentAuthor` (403) / `CommentNotFound` (404); and the create-on-publish consumer swallows failures with no retry.

The comment aggregate is small and the write path is short; nearly all defects are either **spec-reconciliation debt** or live in the **snapshot / validation / authorization** seams around the aggregate.

---

## 2. Aggregate Analysis

### `ChangeRequest` (Aggregate Root) — `ChangeRequests.Domain/Aggregates/Media/ChangeRequest.cs`

Single aggregate in the context. `EventSourced<ChangeRequest, ChangeRequestId, ChangeRequestSnapshot>`, `ITenantScoped`, `[AggregateType("media.changerequest")]` (`ChangeRequest.cs:16-17`). The class-level doc comment is candid: _"Lifecycle tracking (status, reviewers, binding) has moved to MediaItem. ChangeRequest is now comment-only."_ (`ChangeRequest.cs:12-15`).

**Purpose & responsibilities:** provide a participant-scoped, threaded comment space for one MediaItem review cycle, and emit `ChangeRequestCreated` so downstream (Catalog reference index, notifications) can link the thread.

**Aggregate root:** `ChangeRequest`.
**Child entities:** none. Comments are modelled as a value-object list (`ReviewComment`), which is correct — a comment has no independent lifecycle outside the thread.
**Value objects:** `ChangeRequestId`, `CommentId`, `MediaItemId`, `MemberId`, `NonEmptyString`, `ReviewComment`. Healthy VO surface; the aggregate is not anemic.

**Key state (`ChangeRequest.cs:19-39`):** `_comments` (`List<ReviewComment>`), `_participantIds` (`IReadOnlyList<MemberId>`), `ChangeRequestId`, `CreatedById`, `MediaItemId`, `ReviewSessionId`, `TenantId`.

**Invariants enforced in the aggregate (correct):**
- Only a participant may add a comment — `IsParticipant(authorId)` else `Forbidden` (`:64-67, 133-136`).
- A threaded reply's `ParentCommentId` must reference an existing, non-deleted comment (`:69-76`).
- Edit/Delete require the comment to exist, not be already deleted, and the caller to be the author (`:87-101, 113-127`).

**Aggregate boundary assessment:** boundaries are appropriate for the comment-only responsibility. Correctly, the aggregate does **not** own review decisions, reviewer assignment, or MediaItem state — those live in Catalog. The concern is not the boundary but three modelling choices detailed below and in §12–13.

**Aggregate-level defects (detailed later):**
- **CR-B1 (High).** `TakeSnapshot` (`:138-160`) and `ChangeRequestSnapshot` (`Snapshots/ChangeRequestSnapshot.cs:6-22`) do **not** persist `_participantIds` or `ReviewSessionId`; `FromSnapshot` (`:164-190`) therefore restores them to `[]` / `""`. After any snapshot-based rehydration, `IsParticipant` returns false for every caller and **all `AddComment` calls fail with 403**. Core write-path breakage.
- **CR-B2 (High).** Body validity is never checked in `AddComment`/`EditComment`; the only enforcement is `NonEmptyString.Create(e.Body).Value` inside `Apply` (`:209, 221`), where `.Value` on a failed `Result` throws → unhandled 500.
- **CR-F1 (High, design).** `ReviewComment` stores the full `Body` in aggregate state (`ValueObjects/ReviewComment.cs:6`), and the snapshot serialises every body (`:148-157`). The spec's Design Notes explicitly forbid this ("Comment bodies never in aggregate state … prevents DynamoDB's 400 KB item limit from being breached", `write-model.md:148`). Divergence **and** a real scalability risk on long threads.
- **CR-F2 (Medium).** Participant set is snapshotted from `ChangeRequestCreated` and never updated, so it drifts from the live MediaItem `ReviewSession` roster.

---

## 3. Lifecycle Analysis

`ChangeRequest` has **no status field** — it is deliberately lifecycle-free. The only meaningful "state machine" is per-comment (Active → Edited* → Deleted), plus thread existence.

### Thread lifecycle

```text
              MediaItemSubmittedForReview (carries CommentThreadId)
                                 │
             MediaItemPublicationRequestedEventHandler
                                 │
                     CreateChangeRequestCommand
                                 │
                       ChangeRequestCreated
                                 │
                                 ▼
                       ┌──────────────────┐
                       │  Thread (open)   │◄──────────────┐
                       └──────────────────┘               │
                          │      │      │                  │
                 AddComment  EditComment  DeleteComment    │ (no terminal state —
                          │      │      │                  │  thread never closes,
                          └──────┴──────┴──────────────────┘  archives, or deletes)
```

### Per-comment lifecycle

```text
   AddComment            EditComment (author)        DeleteComment (author)
        │                      │                            │
        ▼                      ▼                            ▼
     Active ───────────────► Active(edited) ───────────► Deleted (soft; IsDeleted=true)
                                                            │
                                                    (no un-delete; no hard delete)
```

**Lifecycle observations:**
- **No terminal thread state.** The thread never closes. Per the *current* spec this is intentional (`DeleteComment` is "status-agnostic", `write-model.md:150`). But the endpoint OpenAPI descriptions still promise a `422` "the change request is in a terminal state — comments may not be added after resolution" (`AddCommentEndpoint.cs:38`, `DeleteCommentEndpoint.cs:39`, `EditCommentEndpoint.cs:39`) which **can never be returned** — stale copy from the old model (CR-S6).
- **Comments outlive the review.** Because the thread has no link to the MediaItem's review status, comments can be added/edited after the review is approved or rejected. This may be acceptable, but it is an unbounded, unguarded write surface on a resolved record — worth an explicit product decision for a compliance system.
- **Dead-end on delete.** Soft-delete is one-way; no recovery path (acceptable for audit).
- **Orphaned replies.** Deleting a parent comment does not cascade or re-flag its replies; a reply can also already point at a parent that is later deleted. Thread reconstruction is client-side (`scenarios.md:106`), so this is tolerable but undocumented.

---

## 4. Commands

| Command | Endpoint? | Aggregate method | Domain event | Notes |
|---|---|---|---|---|
| `CreateChangeRequestCommand` (`Commands/CreateChangeRequest/…`) | **No** — system-only | `ChangeRequest.Create` | `ChangeRequestCreated` | Dispatched only by `MediaItemPublicationRequestedEventHandler`. No validation, no auth. |
| `AddCommentCommand` | `POST …/comments` | `AddComment` | `ReviewCommentAdded` | Participant guard in aggregate. |
| `EditCommentCommand` | `PATCH …/comments/{id}` | `EditComment` | `ReviewCommentEdited` | Author guard in aggregate. |
| `DeleteCommentCommand` | `DELETE …/comments/{id}` | `DeleteComment` | `ReviewCommentDeleted` | Author guard in aggregate; soft delete. |

**Issues:**
- **Missing validation (CR-G1).** No `FluentValidation` validator exists for any command or request, contradicting the platform rule "All commands validated with FluentValidation" (aspnetcore-platform CLAUDE.md; magiq-media conventions). Empty/oversized bodies, malformed GUIDs, and empty participant lists are unguarded at the boundary.
- **`CreateChangeRequestCommand` performs no invariant checks** (`CreateChangeRequestHandler.cs:20-31`): no participant-non-empty check, no dedupe. Duplicate integration-event delivery relies entirely on the event-store optimistic-concurrency conditional write to fail, which then surfaces as an error log rather than an idempotent no-op (CR-B6).
- **Authorship guard mislabelled as a business-rule error.** `DeleteComment`/`EditComment` return `DomainError.InvalidOperation("Comment author mismatch.")` (`ChangeRequest.cs:100, 126`) — a 422, where the catalog/spec require `NotCommentAuthor` → **403** (CR-B5). `AddComment`, by contrast, correctly uses `Forbidden` (`:66`). Inconsistent authorization modelling within the same aggregate.
- **`CreateChangeRequest` command note in the spec says "User-facing"** (`write-model.md:101`) — the code has no create endpoint and the api spec says system-created. Spec self-contradiction (CR-S5), code matches the api.md side.
- No `AbandonChangeRequest`, `ActivateForReview`, `AssignReviewer`, `Approve`/`Reject`/`Withdraw` commands exist — correct for the comment-only model, but the context-overview / error-catalog still reference all of them (CR-S1/CR-S3).

---

## 5. Queries

| Query | Reader | Endpoint | Notes |
|---|---|---|---|
| `GetChangeRequestByIdQuery` | `IReadModelReader<ChangeRequestDetailReadModel>` | `GET …/{id}` | 404 if absent. |
| `GetChangeRequestCommentQuery` | `IReadModelReader<ChangeRequestCommentReadModel>` | `GET …/comments/{commentId}` | 404 if absent **or soft-deleted** (`GetChangeRequestCommentHandler.cs:16`). |
| `ListChangeRequestCommentsQuery` | index query | `GET …/comments` | `Matches` filters `!IsDeleted` (`…Query.cs:23`). |
| `ListChangeRequestsByMediaItemQuery` | GSI `ChangeRequestByMediaItemIndex` | `GET …?mediaItemId=` | |
| `ListChangeRequestsByOwnerQuery` | GSI `ChangeRequestByOwnerIndex` | `GET …` (no `mediaItemId`) | `OwnerId = Actor.Id`. |

**Issues:**
- **No authorization on any query (CR-B4).** Handlers apply tenant scoping only. `api.md:46` requires read endpoints to be restricted to "Owner or assigned reviewer of the linked MediaItem", and every read endpoint documents a `403`. No handler ever returns `Forbidden`, so the documented 403 is unreachable and **any authenticated tenant user can read any change request and every comment in the tenant** — a confidentiality gap for regulated records.
- **Reviewers cannot discover their threads (CR-G4).** The only non-mediaItem list is *by owner* (creator). A reviewer who is a participant but not the creator has no query to list the threads they are on; they must already know the `mediaItemId`. The participant roster is not projected to any read model, so participant-scoped listing/authorization is impossible without new infrastructure.
- **Soft-delete leaks body via list.** `ListChangeRequestComments` filters deleted rows out (`…Query.cs:23`), but the row still retains `Body` and `AuthorId` (CR-G5) — a `GetById` on a MediaItem's other read paths, or a projector change, would expose them. The spec requires clearing `Body → "[deleted]"` and `AuthorId → null` on delete (`read-model.md:94`, `scenarios.md:153`); the projector does neither (`ChangeRequestCommentProjector.cs:47-50`).
- **`ListChangeRequestsByMediaItem` returns all threads for an item to any tenant user** — same authz gap as CR-B4, and additionally there is no filter to the caller's participation.

---

## 6. API Endpoints

| Verb | Route (v1) | Auth (documented) | Auth (implemented) | Request | Response | Command/Query |
|---|---|---|---|---|---|---|
| POST | `/change-requests/{crId}/comments` | owner/reviewer of MediaItem | participant-of-thread (aggregate) | `AddCommentRequest` | `201 {Id, CreatedAt}` | `AddCommentCommand` |
| PATCH | `/change-requests/{crId}/comments/{commentId}` | comment author | author (aggregate) | `EditCommentRequest` | `204` | `EditCommentCommand` |
| DELETE | `/change-requests/{crId}/comments/{commentId}` | comment author (+ "admin") | author only | — | `204` | `DeleteCommentCommand` |
| GET | `/change-requests/{crId}` | owner/reviewer | **none** | route | `200 GetChangeRequestByIdResponse` | `GetChangeRequestByIdQuery` |
| GET | `/change-requests/{crId}/comments/{commentId}` | owner/reviewer | **none** | route | `200 …CommentResponse` | `GetChangeRequestCommentQuery` |
| GET | `/change-requests` (`?mediaItemId=`) | owner/reviewer | **none** | query | `200 ListChangeRequestsResponse` | `List…ByMediaItem`/`ByOwner` |
| GET | `/change-requests/{crId}/comments` | owner/reviewer | **none** | query | `200 ListChangeRequestCommentsResponse` | `ListChangeRequestCommentsQuery` |

**Issues:**
- **No `[Authorize]`/permission policy declared on any endpoint** and no handler-side authz on reads (CR-B4). Consistent with the AssetManagement finding — this appears to be a module-wide (possibly platform-wide) gap.
- **OpenAPI descriptions contain authoring TODOs and stale responses (CR-S6).** `AddCommentEndpoint.cs:32` literally sets the Swagger description to _"Document that comments are visible to all assigned reviewers…"_; `DeleteCommentEndpoint.cs:33` and `EditCommentEndpoint.cs:33` likewise begin _"Document that…"_. The `422` "terminal state / closed — comments are immutable after resolution" responses (`AddComment:38`, `Delete:39`, `Edit:39`) describe a lifecycle the aggregate no longer has. `DeleteCommentEndpoint.cs:37` promises `403` for "not the original comment author **and does not hold admin role**" — there is no admin override in `DeleteComment`. Consumers of the generated spec see instructions-to-self and impossible error codes.
- **Verb/status choices are otherwise correct.** `POST` → 201 body-only with `{Id}` (matches ADR-012 §Resource Creation, no `Location`), `PATCH`/`DELETE` → 204, list endpoints cursor-paginated (ADR-014). Good.
- **`DeleteComment` declares a `DeleteCommentResponse` DTO but returns 204 No Content** (`DeleteCommentEndpoint.cs:64`) — the response record is dead code (CR-F4).
- **Idempotency (CR-G2).** `api.md:13` states all mutating endpoints accept `IdempotencyKey`; no endpoint references it. Either it is platform middleware (verify) or the documented behaviour is absent.

---

## 7. Request DTO Review

| DTO | Shape | Findings |
|---|---|---|
| `AddCommentRequest` (`…/AddComment/AddCommentRequest.cs`) | `class { Body; ChangeRequestId; ParentCommentId? }` mutable | Mutable `class` with public setters where the codebase norm is immutable `record`. `Body` has no validation attribute or validator (CR-G1/CR-B2). `ChangeRequestId` is bound from the route. |
| `EditCommentRequest` | `class { ChangeRequestId; CommentId; NewBody }` mutable | Same mutability/validation concerns. Field `NewBody` — spec api.md request example uses `body`, not `newBody` (`api.md:92`) → wire-name mismatch. |
| `DeleteComment` | no request DTO (uses `RequiredRoute`) | Fine. `RequiredRoute` calls `ThrowError` → FastEndpoints 400; acceptable. |
| `GetChangeRequestByIdRequest` / `…CommentRequest` | `record(string …)` | Fine. |
| `ListChangeRequestsRequest` | `record(MediaItemId?, PageToken?, PageSize=20)` | `PageSize` default 20 matches spec; no max-clamp visible (spec caps comments at 100). |
| `ListChangeRequestCommentsRequest` | `record(ChangeRequestId, PageToken?, PageSize=20)` | Spec says comments default `pageSize = 50`, max `100` (`api.md:190`, `read-model.md:69`). Code defaults **20** and enforces no max → default mismatch (CR-G8). |

**Cross-cutting:** no request-level validation anywhere; `Body`/`NewBody` empties and > length reach the aggregate and blow up in `Apply` (CR-B2).

---

## 8. Response DTO Review

| DTO | Findings |
|---|---|
| `GetChangeRequestByIdResponse` (`Id, OwnerId, MediaItemId, CommentCount, CreatedAt, UpdatedAt`) | Spec api.md body is `{ id, mediaItemId, createdById, commentCount, createdAt }` (`api.md:147-153`). Code names the creator field **`OwnerId`** (spec: `createdById`) and adds **`UpdatedAt`** (not in spec). ADR-012 is satisfied structurally (own id = `Id`), but "OwnerId" is semantically misleading — the value is the *creator* (`ChangeRequestCreated.InitiatedBy`), not a resource owner in the ownership sense. Naming should be reconciled with the spec. |
| `ChangeRequestSummaryModel` (`Id, MediaItemId, OwnerId, CreatedAt`) | Spec list item is `{ id, mediaItemId, createdAt }` (`api.md:172-174`) — code adds `OwnerId`. Minor over-exposure; harmless but undocumented. |
| `ChangeRequestCommentSummaryModel` / `GetChangeRequestCommentResponse` (`Id, ChangeRequestId, AuthorId, Body, ParentCommentId, CreatedAt, EditedAt?, IsDeleted`) | Matches spec wire shape well (ADR-012 compliant: own `Id`, foreign `ChangeRequestId`). `ParentCommentId` coalesces `null → ""` (`ChangeRequestCommentSummaryModel.cs:22`) — spec shows `parentCommentId: null`, so emitting `""` for top-level comments is a subtle contract drift. |
| Mapping mechanism | Every DTO conversion is an **`implicit operator`** (read model → model → response), sometimes chained two deep (`GetChangeRequestCommentResponse ← ChangeRequestCommentSummaryModel ← ChangeRequestCommentReadModel`). Surprising, hard to unit-test, and — as ADR-012 itself records for `FolderSummaryModel` — implicit-operator mappers have already caused a live field-swap data-corruption bug elsewhere in this codebase. Prefer explicit mappers (CR-F4). |
| `DeleteCommentResponse` | Declared, never sent (204). Dead DTO. |
| `AddCommentResponse` | Mutable `class` with setters vs record norm; contents (`Id`, `CreatedAt`) fine. |

---

## 9. Domain Events

| Event | Publisher (aggregate method) | Payload | Consumers (projection) | Findings |
|---|---|---|---|---|
| `ChangeRequestCreated` | `Create` (`:53`) | `TenantId, ChangeRequestId, MediaItemId, InitiatedBy, ReviewSessionId, ParticipantIds, CreatedAt` | Summary + Detail projectors; mapped to integration event | Carries `ParticipantIds` + `ReviewSessionId` — the event stream **does** have the data the snapshot loses (confirms CR-B1 is a snapshot-only defect). Field `InitiatedBy` here vs `CreatedById` on the aggregate/state — naming drift. |
| `ReviewCommentAdded` | `AddComment` (`:78`) | `TenantId, ChangeRequestId, CommentId, AuthorId, Body, ParentCommentId?, AddedAt` | Comment + Detail projectors | `Body` carried in event (correct — projected out). |
| `ReviewCommentEdited` | `EditComment` (`:129`) | `TenantId, ChangeRequestId, CommentId, OldBody, NewBody, EditedAt` | Comment + Detail projectors | `OldBody` sourced from **in-aggregate** `comment.Body.Value` (`:129`), not from `ICommentReadModel.GetBodyAsync` as the spec prescribes (`write-model.md:124-129`). The spec's `ICommentReadModel` interface is unimplemented — a direct consequence of CR-F1 (bodies kept in aggregate). |
| `ReviewCommentDeleted` | `DeleteComment` (`:103`) | `TenantId, ChangeRequestId, CommentId, DeletedAt` | Comment + Detail projectors | Projector sets `IsDeleted=true` but does **not** clear `Body`/`AuthorId` (CR-G5). |

**Findings:**
- **Timestamps are passed in (deterministic).** All events take the timestamp from the command (`AddedAt`, `EditedAt`, `DeletedAt`, `CreatedAt`) — good; no wall-clock inside domain methods (contrast the AssetManagement A-D2 defect). *However* `TakeSnapshot` uses `DateTimeOffset.UtcNow` (`:158`) — snapshots aren't replayed for equivalence, so this is benign but worth noting.
- **Projector idempotency is correct** — all handlers guard on `ProjectedVersion`/`MissingCurrentAsync` and set `ProjectedVersion = e.AggregateVersion` (`ChangeRequestCommentProjector.cs`, `ChangeRequestDetailProjector.cs`). `CommentCount` decrement floors at 0 (`Detail:61`). Good.
- **`ChangeRequestDetailProjector` maintains only a `CommentCount` scalar** and comment events update `UpdatedAt` — reasonable separation from the per-comment table.
- No missing/duplicate domain events for the comment-only model. (The old lifecycle events — `ReviewerAssigned`, `ReviewApproved`, `ChangeRequestApproved/Rejected/Abandoned`, etc., still in `context-overview.md` and `read-model.md`'s projector table — do not exist and should not, per the refactor.)

---

## 10. Integration Events

### Published

| Integration event | Trigger | Payload (code) | Findings |
|---|---|---|---|
| `ChangeRequestCreatedIntegrationEvent` (`Contracts/Events/…`) `[MessageType("media.changerequest.created")]` | `ChangeRequestCreated` via `ChangeRequestDomainEventMapper` | `TenantId, ChangeRequestId, CreatedById, MediaItemId, CreatedAt, EventVersion` | Publishing is inline via the domain-event mapper per ADR-005 — correct. **Payload mismatch vs spec** (`context-overview.md:110-119`): spec declares `OwnerId` (code: `CreatedById`) **and a `Binding` field** ("CheckoutBound"/"SubmissionBound"/"Open") that no longer exists in the code model. Self-describing (all `string` scalars, `EventVersion` present) — good per ADR-012 Rule 5. |

- Comment events (`ReviewCommentAdded/Edited/Deleted`) are **not** published as integration events — correct and matches `write-model.md:142` ("domain-internal only").
- **Only one integration event is published**, versus the five (`…Activated/Approved/Rejected/Abandoned`) still listed in `context-overview.md` (CR-S1). Those are correctly absent from code.

### Consumed

| Integration event | Source | Consumer | Findings |
|---|---|---|---|
| `MediaItemSubmittedForReviewIntegrationEvent` | Catalog | `MediaItemPublicationRequestedEventHandler` | Class name (`…PublicationRequested`) does not match the event it handles (`…SubmittedForReview`) — naming drift. Reads `CommentThreadId`, prepends `SubmittedBy` to `ReviewerIds` to form participants, dispatches `CreateChangeRequestCommand`. No-ops when `CommentThreadId` empty (`:25-29`). **Failure handling is unsafe (CR-B6):** on a failed create it logs and returns (`:46-50`) — it does **not** rethrow, so the SQS message is acknowledged and the thread is never created on a transient failure; and duplicate delivery re-emits `ChangeRequestCreated`, failing the optimistic-concurrency write and logging an error rather than an idempotent success. |

- The three consumed messages in `context-overview.md` (`MediaItemCheckedOutMessage`, `MediaItemSubmittedForReviewMessage`, `MediaItemCheckoutForceReleasedMessage`, each with a distinct shape and consumer) are stale — only one consumer exists, on a differently-named event (CR-S1).
- Idempotency/ordering requirements for the consumer are undocumented and unenforced (CR-B6/CR-G2).

### External dependencies

Catalog context (source of the inbound event and owner of the review lifecycle); DynamoDB (event store `media-events`, read-model tables, GSIs); SNS `media-integration-events`; SQS projector queue. Coupling is appropriate and event-only — no synchronous cross-BC calls. Correct per the module's design intent.

---

## 11. Specification vs Repository Differences

| Item | Specification | Repository | Severity | Recommendation |
|---|---|---|---|---|
| Overall model | `context-overview.md` + `read-model.md`: full lifecycle (Status, Binding, reviewers, approve/reject/abandon, 5 integration events, sagas). `write-model.md`/`scenarios.md`/`api.md`: comment-only. | Comment-only. | **High** | Rewrite/retire `context-overview.md` and `read-model.md` to the comment-only model; they are actively misleading. |
| Aggregate name | `MediaChangeRequest` | class `ChangeRequest`, folder `Aggregates/Media` | Low | Align name to ubiquitous language or update spec; pick one. |
| Snapshot fidelity | (implied) aggregate rebuildable | Snapshot omits `ParticipantIds` + `ReviewSessionId` → broken restore | **High/Critical** | Add both fields to `ChangeRequestSnapshot` + `FromSnapshot`. |
| Comment body max length | 4 000 chars, control-char regex (`write-model.md:69`) | 255 chars, no regex (`NonEmptyString.cs:12`) | **High** | Raise limit to 4 000; add validator; strip/reject control chars. |
| Body validation failure mode | `InvalidCommentBody` 4xx (`write-model.md:39`) | `Result.Value` throws in `Apply` → 500 | **High** | Validate at command boundary (validator + aggregate guard returning `DomainError`). |
| Bodies in aggregate state | Never — index tuples only; bodies via `media-change-request-comments`/`ICommentReadModel` (`write-model.md:27,148`) | Full bodies in `ReviewComment` + snapshot | **High** | Store `(CommentId, AuthorId, IsDeleted)` only; add `ICommentReadModel` for `EditComment` `OldBody`. |
| Read authorization | Owner/reviewer of linked MediaItem (`api.md:46`) | None (tenant scope only) | **High** | Enforce participant/owner check on read handlers; project participants. |
| Author-mismatch error | `NotCommentAuthor` → **403** (`error-catalog:111`) | `InvalidOperation` → 422 | **High** | Return a `Forbidden`/coded 403. |
| Comment-not-found error | `CommentNotFound` → **404** (`error-catalog:112`) | `InvalidOperation` → 422 | Medium | Return `ResourceNotFound` 404. |
| Soft-delete projection | Clear `Body → "[deleted]"`, `AuthorId → null` (`read-model.md:94`) | Only `IsDeleted=true`; body/author retained | Medium | Clear body & author in `ReviewCommentDeleted` projection. |
| Create endpoint | `scenarios.md:50` shows public `POST /v1/change-requests`; `write-model.md:101` "User-facing"; `api.md:20` "no public HTTP endpoint" | System-created via consumer only | Medium | Fix spec: remove the public-create scenario/command note; api.md is correct. |
| `ICommentReadModel` for `OldBody` | Required (`write-model.md:113,124`) | Not implemented; `OldBody` from aggregate | Medium | Follows from bodies-in-aggregate fix. |
| Comment list default page size | 50 (max 100) (`api.md:190`) | 20, no max | Low | Default 50, clamp 100. |
| `GetById` response field | `createdById` (`api.md:150`) | `OwnerId` + extra `UpdatedAt` | Low | Rename to `createdById`; decide whether `updatedAt` is contractual. |
| Integration event payload | `OwnerId` + `Binding` (`context-overview.md:110`) | `CreatedById`, no `Binding` | Low | Reconcile stale spec to code. |
| Endpoint OpenAPI text | Clean prose | "Document that…" TODOs + impossible 422s | Medium | Rewrite summaries; remove stale 422 responses. |
| Error-catalog CR section | Full reviewer surface (`ChangeRequestNotOpen`, `Reviewer*`, `MinimumReviewersRequired`…) | Only `NotCommentAuthor`/`CommentNotFound` are relevant; neither is emitted | Medium | Trim catalog to comment-only codes; add `InvalidCommentBody`/`CommentDeleted` if used. |

---

## 12. Bugs

### Critical

None that are unconditionally reproducible in every deployment — but **CR-B1 is Critical-in-effect** wherever the platform snapshot policy is active (see below); it is filed as High only because its trigger is environment/policy dependent.

### High

**CR-B1 — Snapshot silently drops `ParticipantIds` and `ReviewSessionId`; all commenting breaks after a snapshot.**
`ChangeRequestSnapshot` (`Snapshots/ChangeRequestSnapshot.cs:6-22`) has no participant or review-session fields; `TakeSnapshot` (`ChangeRequest.cs:138-160`) does not serialise `_participantIds`/`ReviewSessionId`; `FromSnapshot` (`:164-190`) leaves `_participantIds = []` and `ReviewSessionId = ""`.
- *Why it's a problem:* once the platform takes a snapshot of a thread (typically after N events — an active review easily crosses that), every subsequent rehydration loads an empty participant set. `IsParticipant` (`:133-136`) then returns false for all callers, so `AddComment` returns `Forbidden` (403) for every legitimate participant. The thread is silently write-dead.
- *Failure scenario:* thread `cr-01` accrues > snapshot-threshold comment events → snapshot taken → reviewer Alice `POST …/comments` → aggregate rehydrated from snapshot → `IsParticipant(alice)=false` → 403, despite Alice being a valid reviewer.
- *Impact:* core feature breakage, data-loss-of-capability, hard to diagnose (works then stops). Government review workflows blocked.
- *Recommendation:* add `IReadOnlyList<string> ParticipantIds` and `string ReviewSessionId` to `ChangeRequestSnapshot`, populate in `TakeSnapshot`, restore in `FromSnapshot`. Add a rehydration test that snapshots then adds a comment. (Confirm snapshot policy/threshold with the platform team; even if snapshots are currently disabled, the code is latently broken.)

**CR-B2 — Comment body is never validated at the boundary; invalid body throws in `Apply` → unhandled 500.**
`AddComment` (`:57-79`) and `EditComment` (`:107-131`) validate participant/author/parent but not the body. The body is first parsed in the `Apply` handlers via `NonEmptyString.Create(e.Body).Value` (`:209`) and `NonEmptyString.Create(e.NewBody).Value` (`:221`). `NonEmptyString.Create` returns a *failed* `Result` for empty/whitespace/over-length input (`NonEmptyString.cs:23-33`); calling `.Value` on a failed `CSharpFunctionalExtensions.Result` throws `InvalidOperationException`. Because `Emit` applies synchronously, the exception propagates out of the aggregate method → out of the handler → unhandled → HTTP 500.
- *Why it's a problem:* the endpoints document `400` "Empty body or exceeds max length" (`AddCommentEndpoint.cs:34`, `EditCommentEndpoint.cs:35`); the actual result is a 500 with no RFC 9457 `ProblemDetails`. There is no `FluentValidation` validator to pre-empt it.
- *Failure scenario:* `POST …/comments` with `{"body":""}` → 500.
- *Impact:* every empty/oversized comment is a server error; poor observability; contract violation.
- *Recommendation:* add a request/command validator (non-empty, ≤ 4 000) and have the aggregate `AddComment`/`EditComment` return `DomainError.ValidationFailure` (`InvalidCommentBody`) instead of relying on a throwing `.Value`.

**CR-B3 — Comment body max length is 255, not 4 000.**
`NonEmptyString.MaxLength = 255` (`NonEmptyString.cs:12`); spec requires 4 000 (`write-model.md:46,69`).
- *Why:* combined with CR-B2, any legitimately long review comment (256–4 000 chars) is not merely rejected — it triggers the 500 path. Reviewers writing substantive feedback are blocked.
- *Recommendation:* dedicated `CommentBody` VO with `MaxLength = 4000` (don't reuse a generic 255-char `NonEmptyString`), validated at the boundary.

**CR-B4 — No authorization on read endpoints.**
`GetChangeRequestByIdHandler`, `GetChangeRequestCommentHandler`, `ListChangeRequestComments/ByMediaItem/ByOwner` handlers apply tenant scope only; no endpoint declares a policy. `api.md:46` restricts reads to owner/assigned reviewer.
- *Why:* any authenticated user in the tenant can read any change request and every comment (including soft-deleted bodies that were never cleared, CR-G5) for any MediaItem — a confidentiality breach for regulated/government records.
- *Failure scenario:* user with no involvement in `mi-01`'s review calls `GET /change-requests?mediaItemId=mi-01` and reads all feedback.
- *Recommendation:* project the participant roster (or resolve it from the MediaItem `ReviewSession`), and enforce owner/participant membership in read handlers, returning `Forbidden` (403).

**CR-B5 — Authorship and existence failures return 422 instead of 403/404.**
`DeleteComment`/`EditComment` return `DomainError.InvalidOperation("Comment author mismatch.")` (`:100,126`) and `"Comment not found."`/`"Comment already deleted."` (`:90,95,116,121`). Per the error catalog these are `NotCommentAuthor` → **403** and `CommentNotFound` → **404** (`error-catalog:111-112`); `InvalidOperation` maps to **422** (`error-catalog:31`).
- *Why:* clients (and the endpoints' own documented 403/404) get the wrong status; a non-author editing another's comment is an authorization failure (403), not an unprocessable entity (422). The RFC 9457 `errorCode` is the generic `InvalidOperation`, not the machine-discriminable `NotCommentAuthor`/`CommentNotFound`.
- *Recommendation:* return `DomainError.Forbidden` (403) for author mismatch and `DomainError.NotFound`/`ResourceNotFound` (404) for missing/deleted comment; wire the specific `errorCode`s.

### Medium

**CR-B6 — Create-on-publish consumer swallows failure and is non-idempotent.**
`MediaItemPublicationRequestedEventHandler.HandleAsync` (`:45-50`) logs and returns on a failed `CreateChangeRequestCommand` without rethrowing.
- *Why:* (a) on a transient failure (Dynamo throttle, etc.) the SQS message is acknowledged and the comment thread is **never** created — reviewers then cannot comment, with no retry/DLQ; (b) on duplicate delivery, `Create` re-emits `ChangeRequestCreated` at version 0, the optimistic-concurrency conditional write fails, and the handler logs an *error* rather than treating "already exists" as success.
- *Recommendation:* treat "already created" (concurrency/exists) as an idempotent success; rethrow genuine transient failures so the platform retries / DLQs. Add a dedupe/exists check keyed on the deterministic `ChangeRequestId`.

**CR-B7 — Comment soft-delete does not clear body/author in the read model.**
`ChangeRequestCommentProjector.ApplyAsync(ReviewCommentDeleted)` (`:47-50`) sets `IsDeleted=true` only. Spec requires `Body → "[deleted]"`, `AuthorId → null` (`read-model.md:94`, `scenarios.md:153`).
- *Why:* deleted comment text and authorship remain retrievable in the store and via any code path that doesn't filter `IsDeleted`; the "retract" semantics users expect are not honoured. For a compliance system, "deleted" that still exposes content is a data-handling defect.
- *Recommendation:* clear body and author on delete in the projector (and confirm the event store copy is acceptable for audit-only access).

### Low

**CR-B8 — `ParentCommentId` emitted as `""` for top-level comments** (`ChangeRequestCommentSummaryModel.cs:22`) where the spec shows `null` (`api.md:199`). Wire-contract drift.

**CR-B9 — Comment list default page size 20 vs spec 50, no max clamp** (`ListChangeRequestCommentsRequest.cs:3`, spec `api.md:190`).

---

## 13. Design Flaws

**CR-F1 — Comment bodies live in aggregate state and snapshots (violates the stated design + DynamoDB limit).**
`ReviewComment.Body : NonEmptyString` (`ValueObjects/ReviewComment.cs:6`) and `TakeSnapshot` serialises every body (`:148-157`). The spec's Design Notes (`write-model.md:148`) mandate the opposite precisely to avoid DynamoDB's 400 KB item limit on long threads, and describe an `ICommentReadModel.GetBodyAsync` mechanism (`write-model.md:113-129`) that the code does not implement. A long-running government review with hundreds of comments will grow the snapshot toward the item-size ceiling; and the aggregate is doing work (holding bodies) it exists specifically not to do. This is the root cause of both the snapshot bloat and the unimplemented `ICommentReadModel`.

**CR-F2 — Participant roster is a fixed creation-time snapshot, decoupled from the live `ReviewSession`.**
`_participantIds` is set once from `ChangeRequestCreated` (`:201`) and never updated; there is no `AddParticipant`/`RemoveParticipant`. `scenarios.md:213-247` explicitly endorses this ("does not re-query the ReviewSession"), but `write-model.md:112` and `api.md:43` say authorization is against the *linked MediaItem's* reviewer set. If reviewers are added/removed on the MediaItem after the thread is created, a newly-added reviewer cannot comment and a removed reviewer still can. The spec itself is contradictory here; the design needs a decision (snapshot vs live), and whichever is chosen must be enforced consistently on both writes and reads.

**CR-F3 — Authorization modelled as a business-rule error.**
`DeleteComment`/`EditComment` express "not the author" as `InvalidOperation` (CR-B5). Authorization and domain-rule violations should be distinct error types with distinct status codes; conflating them yields wrong HTTP semantics and makes the guard invisible to any cross-cutting authorization concern.

**CR-F4 — Implicit-operator mapping chains and a dead response DTO.**
DTO conversions are implicit operators, chained up to two deep (§8). ADR-012 records that an implicit-operator mapper already caused a live field-swap corruption elsewhere (`FolderSummaryModel`). `DeleteCommentResponse` is declared but never sent. Prefer explicit, testable mappers; delete dead DTOs.

**CR-F5 — Naming drift from the ubiquitous language.**
Aggregate class `ChangeRequest` (spec `MediaChangeRequest`), folder `Aggregates/Media`, read models under `ReadModels/MediaItems`, event field `InitiatedBy` vs state `CreatedById`, response field `OwnerId` vs spec `createdById`, consumer class `MediaItemPublicationRequestedEventHandler` handling `MediaItemSubmittedForReviewIntegrationEvent`. Individually minor; collectively they erode traceability between spec and code.

---

## 14. Design Gaps

- **CR-G1 — No `FluentValidation` validators** for any command or request (platform rule violated). Bodies, GUIDs, and participant lists are unvalidated at the boundary.
- **CR-G2 — Idempotency not visible.** `api.md` promises `IdempotencyKey` on all mutating endpoints; nothing references it. The create consumer has no dedupe (CR-B6).
- **CR-G3 — RFC 9457 `errorCode` not emitted for CR-specific codes.** Endpoints surface `error.ErrorMessage` + generic `ErrorType`; the catalog's `NotCommentAuthor`/`CommentNotFound`/`InvalidCommentBody` are never produced.
- **CR-G4 — No participant-scoped read path.** Participants aren't projected; reviewers can't list "threads I'm on"; read authz can't be enforced without new infrastructure.
- **CR-G5 — Deleted-comment content not scrubbed** in the read model (CR-B7).
- **CR-G6 — Control-character sanitisation absent** (spec regex `write-model.md:69`).
- **CR-G7 — No admin/moderator delete** though `DeleteCommentEndpoint.cs:37` documents it. Either implement (privileged actor can delete any comment) or remove the doc.
- **CR-G8 — No observability of the create-on-publish drop** beyond a single `LogError`; no metric/alarm for "review submitted but thread not created".
- **CR-G9 — No test evidence** in-slice for the snapshot round-trip, the empty-body path, or read authz — the three highest-risk behaviours.

---

## 15. Missing Features

Relative to the **current (comment-only) spec**, missing:
- Body validation (length 4 000, non-empty, control-char reject) — CR-B2/B3/G6.
- Read-side authorization + participant projection — CR-B4/G4.
- Coded 403/404 errors for author/exists — CR-B5.
- Deleted-body scrubbing — CR-B7.
- `ICommentReadModel` + bodies-out-of-aggregate — CR-F1.
- Idempotent, retry-safe thread creation — CR-B6.
- Request validators — CR-G1.

Relative to the **stale spec** (`context-overview.md`/`read-model.md`/`error-catalog`), the reviewer roster, status lifecycle, decision commands, and five integration events are "missing" — but these were **deliberately moved to Catalog `MediaItem`** and should be **removed from the spec**, not implemented here. Do not treat the stale spec as a backlog.

---

## 16. Recommendations

_Priority order: Correctness → Data Integrity → Security → Domain Modelling → Lifecycle → API → Events → Maintainability → Performance → Scalability._

1. **[Correctness] Fix the snapshot (CR-B1).** Add `ParticipantIds` + `ReviewSessionId` to `ChangeRequestSnapshot`, `TakeSnapshot`, `FromSnapshot`. *Approach:* extend the record, populate/restore, add a test that snapshots a thread then asserts a participant can still comment. Confirm the platform snapshot threshold. **Blocker for production.**

2. **[Correctness] Validate comment bodies at the boundary (CR-B2/B3/G1/G6).** Introduce a `CommentBody` VO (non-empty, ≤ 4 000, control-char reject) and a `FluentValidation` validator on `AddComment`/`Edit` requests; have the aggregate return `DomainError.ValidationFailure("InvalidCommentBody")` rather than a throwing `.Value`. *Approach:* validator + aggregate guard + remove `.Value` reliance in `Apply` (parse-and-return, or trust the pre-validated string).

3. **[Data Integrity] Take comment bodies out of aggregate state (CR-F1).** Store `(CommentId, AuthorId, IsDeleted)` tuples only; implement `ICommentReadModel.GetBodyAsync` for `EditComment` `OldBody`. Removes snapshot bloat and the 400 KB risk, and realigns with the spec.

4. **[Data Integrity] Scrub deleted comments (CR-B7/G5).** Clear `Body`/`AuthorId` in the `ReviewCommentDeleted` projection.

5. **[Security] Enforce read authorization (CR-B4/G4).** Project the participant roster (or resolve via the MediaItem `ReviewSession`) and gate all read handlers to owner/participant, returning 403. Highest-value security fix; compliance-relevant.

6. **[Security] Correct error semantics (CR-B5/G3).** Author-mismatch → 403 `NotCommentAuthor`; missing/deleted comment → 404 `CommentNotFound`; emit RFC 9457 `errorCode`s.

7. **[Domain Modelling] Decide the participant-source contract (CR-F2).** Snapshot-at-creation vs live `ReviewSession`. Update whichever spec pages are wrong, and enforce the choice on both writes and reads. If snapshot-at-creation stays, add an explicit note that late reviewer changes don't propagate.

8. **[Reliability] Make thread creation idempotent and retry-safe (CR-B6/G8).** Treat "already exists" as success; rethrow transient failures for platform retry/DLQ; add a metric/alarm for creation drops.

9. **[Lifecycle] Decide whether comments are writable after review resolution.** Currently unguarded; if a gate is wanted, the thread needs to observe the MediaItem review status (today it can't). If not, remove the stale 422 responses (CR-S6).

10. **[API] Clean the OpenAPI surface (CR-S6/B8/B9).** Replace "Document that…" descriptions with real prose; remove impossible 422/admin-delete responses; `parentCommentId: null` not `""`; default comment page size 50 (max 100); reconcile `createdById` vs `OwnerId`.

11. **[Events] Reconcile the integration-event payload (CR-S7)** to the shipped shape (drop `Binding`, name the creator consistently), and update `context-overview.md`.

12. **[Maintainability] Replace implicit-operator mappers with explicit mappers (CR-F4);** delete `DeleteCommentResponse`; align naming to the ubiquitous language (CR-F5).

13. **[Spec — do first, it gates the rest] Reconcile the specification (CR-S1–S6).** Rewrite/retire `context-overview.md` and `mediachangerequest.read-model.md` to the comment-only model; trim the `error-catalog` ChangeRequests section to comment codes (add `InvalidCommentBody`/`CommentDeleted` if used); remove the public-create scenario in `scenarios.md`; resolve the `write-model.md` "user-facing create" and "bodies-never-in-aggregate" contradictions. Until this is done, "spec vs repo" cannot be judged cleanly for the next aggregate either.

---

## Top 5 Before Production

1. **CR-B1 — Snapshot drops participants/review-session → all commenting breaks after a snapshot.** (`ChangeRequest.cs:138-190`, `Snapshots/ChangeRequestSnapshot.cs:6-22`)
2. **CR-B4 — No read authorization; any tenant user reads any change request and every comment.** (query handlers; `api.md:46`)
3. **CR-B2/B3 — Missing body validation + 255-char cap → empty/long comments throw an unhandled 500 instead of 400.** (`ChangeRequest.cs:78,129,209,221`, `NonEmptyString.cs:12,34`)
4. **CR-B5 — Author-mismatch/not-found return 422 instead of 403/404.** (`ChangeRequest.cs:90,100,116,126`; `error-catalog:111-112`)
5. **CR-S1/S2 — Specification is internally three-way inconsistent (stale full-lifecycle overview + read-model vs comment-only code).** Reconcile before the module is signed off. (`context-overview.md`, `read-model.md`, `error-catalog:99-112`)

_Honourable mention:_ CR-B6 (thread-creation failures silently swallowed) and CR-F1 (comment bodies in aggregate state → DynamoDB 400 KB risk).
