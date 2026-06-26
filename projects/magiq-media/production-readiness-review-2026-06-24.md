# magiq-media — Production Readiness Review
_2026-06-24 · repo: D:\source\github\magiq-media_

## Critical

**1. Hardcoded JWT signing key in source.** `src/hosts/Api/Auth/JwtConstants.cs:5` — `SigningKey = "super-secret-signing-key-for-dev-only-32x"`. No JWT-bearer registration was found in this repo (likely delegated to the `aspnetcore-platform` package), so it's unconfirmed whether this key is actually consumed outside Development. If it is, an attacker forges JWTs with arbitrary `tenant_id`/roles → full cross-tenant compromise. **Fix:** load signing key from Secrets Manager/KMS at startup; fail hard if a "dev" key is detected outside `Development`.

**2. No global exception handler / `DomainError → HTTP` mapping in any API host.** Zero matches for `UseExceptionHandler`/`IExceptionHandler`/`ProblemDetails` in `Api` or `QueryApi`. Combined with finding #3, unhandled exceptions hit FastEndpoints' default behavior with no structured client-facing error.

**3. Exceptions escape the `Result<T, DomainError>` convention at infra/event boundaries** — the one rule the architecture leans on hardest is violated in several places:
   - `AssetManagement.WriteModel/Commands/CompleteMultipartUpload/CompleteMultipartUploadHandler.cs:44-46` — S3 ETag mismatch left uncaught.
   - `Catalog.WriteModel.Infrastructure/Locking/DynamoDbFolderCreationLockService.cs:67-82` — bare `catch {}` swallows all exceptions on lock release.
   - `Processing.WriteModel.Infrastructure/Workers/AssetProcessingWorker.cs:51,82,99` — `NotImplementedException` (rendition pipeline is a stub) and raw `Exception` throws instead of `Result`.
   - `AssetManagement.WriteModel/IntegrationEvents/Consuming/Handlers/ProcessingJobScanResultEventHandler.cs:33` — throws `InvalidOperationException` on an unrecognized enum value with no catch; unlike the 154 command handlers (100% compliant, spot-checked), this integration-event boundary has no discipline. Propagates straight to the Lambda runtime / DLQ.

**4. No retry handling for DynamoDB optimistic concurrency.** Convention calls for ≤3 retries on conditional-write conflicts; none found anywhere in `src/`. `DynamoDbFolderCreationLockService.cs:50-53` treats `ConditionalCheckFailedException` as terminal. Polly is referenced only as a transitive binary — never wired to an actual retry pipeline for DynamoDB/S3/SQS/SNS calls.

**5. No consumer/projector idempotency for duplicate SQS delivery.** Zero `LastObservedAtUtc`-style dedup guards found in EventConsumers/TimeoutScanner projector code, despite the architecture's explicit "projections must tolerate duplicate event delivery" rule.

**6. `MediaItemReviewSaga` does not exist** (memory said "partial" — it's actually zero implementation). No handler classes for `MediaItemSubmittedForReview`/`ChangeRequestApproved` exist anywhere; `SagaOrchestrator/SagaRegistrations.cs` only wires `AssetIngestionSaga`. The review approve/reject flow (`Catalog.WriteModel/Commands/MediaItems/ApproveReviewHandler.cs`, `RejectReviewHandler.cs`) is plain CQRS with no orchestration.

**7. `DocumentSigningSaga` unregistered, and DocumentSigning has zero tests.** `SagaOrchestrator.DocumentSigning` is a separate Lambda host with `SigningSessionInitiatedHandler`/`SecuredSigningWebhookHandler`, but neither is registered in `SagaRegistrations.AddSagaMessageHandlers`, and there's no compensation logic for envelope voiding. No WriteModel/ReadModel/integration tests exist for this module at all — it's the least production-ready module in the repo.

## High

**8. No command-level authorization beyond "is authenticated."** `Api/Startup.cs:83` defines exactly one policy (`AuthenticatedUser`). Zero `Permissions(`/`Roles(`/`Policies(`/`[Authorize]` hits across any endpoint, and zero `IPermissionService` call sites anywhere in `magiq-media`. Any authenticated actor — regardless of role — can currently invoke any command endpoint. This matches the project's own Q2 roadmap (user security/policies is priority #3, not yet started), but it means **the API is not safe to expose beyond trusted internal callers today.**

**9. Permissive CORS** — `Api/Startup.cs:80`: `AllowAnyOrigin().AllowAnyHeader().AllowAnyMethod()`. Low risk with bearer-only auth, but should be locked to known frontend origins before go-live.

**10. Cross-module domain coupling bypasses the Contracts seam.** `Catalog.WriteModel.Infrastructure` has a direct `ProjectReference` to `Registrations.Domain` (not `Registrations.Contracts`); `RegistrationCountIndexProjector.cs` reacts directly to Registration's internal domain events (`RegistrationInitiated`, `RegistrationCancelled`, `RegistrationRejected`). Every other cross-module link in the solution goes through Contracts + integration events — this is the one violation of "no service may directly modify/read another service's internals."

**11. CI never runs tests.** `.github/workflows/build-and-push.yml` only does `dotnet restore`/`dotnet publish` — no `dotnet test` stage. Combined with zero test projects for any of the 5 actual hosts (Api, QueryApi, EventConsumers, TimeoutScanner, SagaOrchestrator.DocumentSigning — note: `ProcessingWorker`, `Projectors.ReadModel/Search`, and a standalone `SagaOrchestrator` named in CLAUDE.md don't exist as named; structure has drifted from the doc), nothing currently gates a regression from shipping.

**12. Observability is mostly aspirational.** Stack is actually **NLog**, not Serilog (`Api/Program.cs:19`), and only the `Api` host has it wired — the other 4 hosts (all Lambda) rely on bare default console logging. OpenTelemetry packages are referenced (`Api.csproj:20-22`) but `AddOpenTelemetry()` is never called anywhere. X-Ray appears only in a markdown doc, not in code. CorrelationId is logged in 0 of 94 sampled call sites; TenantId in ~2%. No metrics (`Meter`/`Counter`/`Histogram`) anywhere. Health checks exist only on `Api` (`/healthz`) — QueryApi and all Lambda hosts have none.

**13. `SigningSessionSummaryProjector` confirmed missing** (matches memory) — only `SigningSessionDetailProjector` exists; the summary read model has no projector populating it.

**14. `DocumentSigningTimeoutScanner` confirmed missing** — `TimeoutScanner` only implements `AssetIngestionTimeoutScanner`; no timeout logic for signing sessions/envelopes exists.

## Medium

**15. Metadata module: two endpoints rely on an implicit conversion operator instead of an explicit map step** (see endpoint-mapping section below) — `GetRecordTypeByIdEndpoint` and `GetRecordTypeVersionEndpoint` pass the raw ReadModel into `SendOkAsync`, relying on a silent `implicit operator` on the response DTO. Works today only because the DTO happens to mirror the read model field-for-field; a future read-model field addition would leak silently. Every other endpoint in every other module does this mapping explicitly.

**16. `PatchRecordTypeEndpoint` (and likely `PatchCollectionEndpoint`, same shape) does multi-command orchestration with no atomicity.** Dispatches up to three sequential commands per PATCH; if the second fails after the first succeeds, the aggregate is left partially updated with no compensation. PATCH presence/null validation also lives in the endpoint instead of FluentValidation.

**17. `DeleteCommentEndpoint` contract mismatch.** XML doc claims 403 + admin-override for non-authors; the domain (`ChangeRequest.cs:103,128`) has no admin-bypass logic and returns a generic `InvalidOperation` error rather than a Forbidden-style error — likely surfaces as the wrong HTTP status to clients.

**18. OpenSearch query built via string interpolation.** `Catalog.ReadModel/Queries/MediaItems/SearchMediaItems/SearchMediaItemsHandler.cs:52-75` — `SearchTerm` is escaped for `\`/`"` only; `TenantId` is interpolated unescaped. Low practical risk since `TenantId` is a typed value object, but unconfirmed whether the JWT `tenant_id` claim is validated as a strict UUID before being wrapped — worth closing off rather than relying on luck.

**19. `ReviewSessionId` uses raw `Guid.NewGuid()`** instead of the UUID v7 convention every other ID type follows (`Catalog.Domain/.../ReviewSessionId.cs:5`).

**20. DLQ `maxReceiveCount: 3` is configured at the CDK layer only** (`cdk-magiq-media/.../sqs-queues.construct.ts:120-124`); no app-level evidence this is exercised or tested given finding #5.

**21. No `USER` directive in any Lambda Dockerfile** — containers run as the base image default (likely root).

## Low / Informational

- **API request/response DTO mapping is otherwise clean and consistent.** AssetManagement, Catalog, ChangeRequests, and Registration map ReadModel→Response and Request→Command explicitly via a uniform `implicit operator` convention on the DTO records; no AutoMapper used anywhere; Request types never implement `ICommand` directly. `Processing` and `DocumentSigning` have no `.Endpoints` projects at all yet (by design — Processing is a stateless SQS worker; DocumentSigning's API surface isn't built).
- TenantId sourcing is clean repo-wide: zero `Request.cs` DTOs carry a `TenantId` field; it's sourced exclusively from `IExecutionContext` (JWT-derived). DynamoDB PKs are consistently `TENANT#{TenantId}#...` including on GSIs. Asset download IDOR is mitigated (lookup is tenant-scoped before presigning).
- Aggregates correctly implement tenant scoping (actual interface is `ITenantScoped`, not `ITenanted` as CLAUDE.md states — doc/code naming drift, not functional). 154 command handlers spot-checked, 100% return `Result`.
- No hardcoded secrets/connection strings outside the JWT key noted in #1.
- `aspnetcore-platform`'s `ITenantSettingsManager` is only consumed by CLI tooling in this repo, not visibly wired into any host's `Program.cs` (may be transitive via platform DI extensions — unverified from this repo alone).
- A `.claude/worktrees/blissful-gauss-cc3626` worktree contains a materially different host/module layout (`Media.Api`, `Media.QueryApi`, Lambda-suffixed names) — appears to be in-progress refactor work, excluded from this review.
- Test coverage is uneven: Catalog and AssetManagement are well covered (300+ and 150+ tests respectively); ChangeRequests is thin (19 tests); Processing/Metadata/Registration integration test projects exist but are empty or fully commented out; DocumentSigning has none (see #7).

---

## Bottom line

The DDD/CQRS/event-sourcing discipline is genuinely solid where it's been applied — tenant isolation, ID strategy, and the Result-everywhere convention hold up under a hostile read in 5 of 7 modules. But the platform is **not production-ready** on three independent axes that would each block a go-live on their own: (1) authorization is effectively absent above "is logged in," (2) the resilience/idempotency story (retries, exception containment, dedup) is missing at exactly the boundaries — DynamoDB writes, SQS consumers — where it matters most for a compliance-grade system, and (3) DocumentSigning is scaffolding, not a working feature (no saga, no summary projector, no timeout handling, no tests). The endpoint-mapping concern you specifically asked about is in good shape — only two low-impact instances in Metadata need tightening to match the pattern already used everywhere else.

**Suggested sequencing:** authorization (#8) and exception/retry discipline (#2-5) before anything else ships externally; DocumentSigning saga + tests (#7, #13, #14, #6) before that module is considered usable; the Metadata mapping and Catalog/Registration coupling fixes (#10, #15) are cheap and should ride along with the next touch of those modules.
