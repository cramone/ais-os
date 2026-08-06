# Document Lifecycle Cleaner — Working Context & Instructions

_Cross-project orientation for building the NATA Document Lifecycle Cleaner (DLC). Read this first in any DLC session. It tells you **where things live**, **how the three repos relate**, **the exact FastEndpoints → command/query → context pattern to follow**, and **how we run the branch/PR workflow together**._

_Last updated: 2026-07-22._

---

## 1. The three locations (and what each is for)

There are **three** folders in play. Keep them straight — only one of them is the code you ship.

| # | Location | Role | You edit here? |
|---|----------|------|----------------|
| **A** | `document-lifecycle-cleaner` (`Z:\claudia\magiq\projects\...`) | **Planning workspace.** Spec, ADRs, decision log, notes, MEMORY.md. The *source of truth for intent*. Not code. | Docs only (when asked) |
| **B** | `DocumentLifecycleCleaner` (`D:\source\azure\Documents\...`) | **The product repo.** .NET 8 FastEndpoints API + React SPA, single deployable. Hosted in **Azure DevOps Git**, org MAGIQSoftware, project **Documents**, repo `DocumentLifecycleCleaner`. Epic **#34120**. | **Yes — this is the ship.** |
| **C** | `magiq-media` (`D:\source\github\...`) | **Reference only.** The team's AWS-native, event-sourced platform. We copy its *house style* (FastEndpoints ergonomics, Result pattern, feature folders), **not** its infrastructure. | Never (read for patterns) |

**The single most important thing to internalise:** **DLC (B) deliberately does _not_ use the `Magiq.Platform.*` stack that magiq-media (C) is built on.** No DynamoDB, no event sourcing, no `ICommandDispatcher`/`IQueryDispatcher` SDK, no MediatR, no multi-tenancy. DLC is a vanilla FastEndpoints app on SQL Server + Dapper + Hangfire + SignalR, hosted on-prem. When you borrow a pattern from magiq-media, you borrow the **shape**, then re-implement it with vanilla primitives. `Directory.Packages.props` in the repo says this explicitly.

---

## 2. What DLC actually is

A once-a-year, operator-triggered, **on-premises** tool for the client **NATA**. It culls documents and empty folders from **MAGIQ Documents** based on a calendar year-end cutoff date, targeting a facility identified by folder-name acronyms.

It is **not CRUD** — it's a **resumable multi-phase pipeline** with an interactive review/confirm UI in the middle:

```
Phase 1  Identification    Steps 1–5   run configured SQL → candidate docs + folders
Phase 2  Review/Selection  Steps 6–8   operator reviews folders, confirms deletions, picks archive library   ← UI, run parked in AwaitingInput
Phase 3  Archival          Step  9     move documents to archive library (retry loop, resume from failure)
Phase 3  Cleanup           Steps 10–11 delete empty folders → purge archive + recycle bin (background)
```

Two constraints drive the whole architecture:
- **Step 9 moves must resume from the point of failure** (no rollback, re-run only failed docs).
- **The purge (Step 11) is a background system process**, never a direct user action, and gated behind a typed `"permanently delete"` confirmation.

The canonical business rules are in the spec (workspace A): `spec/NATA_Document_Lifecycle_Cleaner_Spec_v0.6.md` + the developer spec `spec/dev-spec.md` (API catalogue, data model, config schema, SignalR contract, sequence flows, error contracts). **When a business rule is unclear, that spec wins.**

---

## 3. Settled architecture (do not re-litigate)

These are decided and logged in workspace A (`decisions/log.md` + `references/adrs/`). Build to them.

| Concern | Decision | Ref |
|---------|----------|-----|
| Background/pipeline engine | **Hangfire**, in-process, `WorkerCount = 1`. Chain phases with **continuations** (a phase starts only once its predecessor confirms complete). Persistence + retries give Step 9 resumability. | ADR-001 |
| Run model | **`CleanupRun` persisted state machine** (`NotStarted→Running→AwaitingInput→…→Completed/Failed/Cancelled/Abandoned`). Single active run enforced at API layer (409 if a non-terminal run exists). Per-doc / per-folder / phase-log tables. | ADR-002 |
| Hosting | **IIS default, Docker supported**, Kestrel in both, no host-specific code. All env settings via config/env vars. React built into `wwwroot`, one artifact. | ADR-003, ADR-008 |
| MAGIQ integration | **Two paths:** SOAP (`srv.asmx`) for library/folder/document ops + auth; **Dapper** direct SQL for the configurable candidate/folder queries (Steps 1, 2, 5). SOAP returns HTTP 200 always — **check the `success` attribute, not the status code.** | ADR-004 |
| Database | **One dedicated app DB** holds `CleanupRun*` tables **and** Hangfire tables. Separate from the MAGIQ Documents DB. Two connection strings: `AppDatabase`, `MagiqDocumentsDatabase`. | ADR-005 |
| Auth | **Piggyback MAGIQ Documents.** No credential store. `AuthenticateUser` called **twice** at login → **two independent tickets**. Admin allowlist in config. | ADR-006 |
| Ticket model | **Ticket A (UI):** in-memory, dies on logout, not persisted. **Ticket B (process):** persisted to `CleanupRun.ProcessTicket`, kept alive by a heartbeat (default 300s), survives IIS recycles. Auto re-auth if UI session still active; else run → Failed and operator retries. | ADR-006, ADR-007 |
| Methodology | **CQRS-lite vertical slice** (FastEndpoints REPR). **No event sourcing** — the domain is a workflow, not a rich aggregate. | log 2026-07-13 |
| Command/query dispatch | **FastEndpoints built-in in-process bus** (`ICommand<Result<T>>` + `ICommandHandler`), dispatched via `command.ExecuteAsync(ct)`. No MediatR, no platform SDK. Results, not exceptions; map to HTTP via a shared `DlcEndpoint` base. | ADR-009 |
| Progress | **SignalR** hub `/hubs/run-progress` (SSE acceptable fallback), per-batch `ProgressUpdated`. | log 2026-07-13 |

Frontend: React SPA (Vite + TS) in `DocumentLifecycleCleaner.Web`, built into the API's `wwwroot`.

---

## 4. Repo B layout as it stands today

Current branch: `feature/34129-scaffold-api-spa-host`. The scaffold (Story 34129) is in and is the template every future slice copies.

```
DocumentLifecycleCleaner.sln
Directory.Build.props          # house style: LangVersion 12, Nullable enable, ImplicitUsings, AnalysisLevel latest-Recommended, NoWarn list (mirrors magiq-media)
Directory.Packages.props       # central package versions — FastEndpoints 6.2.0 only, for now
NuGet.config
src/
  build/TargetFrameworks.props
  DocumentLifecycleCleaner.Api/
    Program.cs                 # builder → AddFastEndpoints + Swagger; UseStaticFiles → UseFastEndpoints(RoutePrefix "api") → MapFallbackToFile("index.html")
    appsettings.json           # { "Application": { "Environment": "Local" }, ... }
    Configuration/
      ApplicationOptions.cs    # Options pattern, bound from "Application", ValidateDataAnnotations + ValidateOnStart
    Features/
      Health/
        PingEndpoint.cs        # GET /api/health/ping — the reference endpoint
        PingResponse.cs
    wwwroot/.gitkeep           # SPA build output lands here (git-ignored)
  DocumentLifecycleCleaner.Web/  # Vite + React + TS SPA (App.tsx, main.tsx)
```

Key facts already true in the scaffold, mirror them:
- **Route prefix `api` is mandatory on every endpoint** — a missing prefix lets the SPA fallback swallow the route (ADR-008). It's set globally in `Program.cs` via `c.Endpoints.RoutePrefix = "api"`, so you write routes *without* the prefix (`Get("/health/ping")` → resolves at `/api/health/ping`).
- **`public partial class Program { }`** is exposed at the bottom of `Program.cs` for `WebApplicationFactory` integration tests in later stories.
- **Strongly-typed config via the Options pattern** with `ValidateOnStart()` — every new config section (Queries, MagiqDocuments, Hangfire, TicketHeartbeat, etc.) gets its own `*Options` class in `Configuration/`, bound the same way.
- **XML doc comments on public members** (magiq-media house style; `GenerateDocumentationFile` conventions).
- Packages are added **with the story that first needs them**, never speculatively — the `Directory.Packages.props` comment names the plan: Dapper/SqlClient/Hangfire/SignalR arrive with their stories.

---

## 5. The endpoint → command/query → context pattern

This is the heart of "how to work." magiq-media's shape is the target ergonomics; here's the **DLC translation** of each piece.

### 5.1 Feature-folder vertical slices

Every endpoint is a self-contained slice under `Features/<Area>/<Feature>/`, exactly like the scaffold's `Features/Health/`. Namespaces mirror folders (`DocumentLifecycleCleaner.Api.Features.Runs.CreateRun`). Map the dev-spec's API catalogue onto areas:

```
Features/
  Auth/        Login, Logout
  Runs/        ListRuns, CreateRun, GetRun, CancelRun, AbandonRun, ResetRun, RetryRun, PurgeRun
  Folders/     GetRunFolders, SubmitFolderSelections, ConfirmDeletions
  Libraries/   ListLibraries, GetLibraryFolders
  Health/      Ping   (done)
```

Each feature folder: `XxxEndpoint.cs` + `XxxRequest.cs` + `XxxResponse.cs` (+ command/query + handler — see below). One class per endpoint, `public sealed`, primary-constructor DI, `Configure()` + `HandleAsync()`.

### 5.2 Endpoint declaration — mirror magiq-media's `Configure()` discipline

```csharp
public sealed class CreateRunEndpoint(/* dispatch + context injected */)
    : Endpoint<CreateRunRequest, CreateRunResponse>   // or a shared base — see 5.5
{
    public override void Configure()
    {
        Post("/runs");                          // NO "api/" — the global prefix adds it
        Description(x => x
            .WithName("CreateRun")
            .WithTags("Runs")
            .WithGroupName("v1")
            .Produces<CreateRunResponse>(201)
            .ProducesProblem(401)
            .ProducesProblem(409));             // RunAlreadyActive
        Summary(s => { s.Summary = "Create a run and trigger Phase 1."; /* … */ });
        Version(1);
    }

    public override async Task HandleAsync(CreateRunRequest req, CancellationToken ct)
    {
        // resolve context, build command, dispatch, map Result → HTTP (see 5.4/5.5)
    }
}
```

Conventions to copy verbatim from magiq-media: always `.WithName / .WithTags / .WithGroupName("v1")`, an exhaustive `.Produces*` per possible status, a full `Summary`, and `Version(1)`. Auth is **global** (default = auth required); add `AllowAnonymous()` only where justified (as `PingEndpoint` does).

### 5.3 Commands & queries — FastEndpoints built-in bus (ADR-009)

magiq-media dispatches through the proprietary `ICommandDispatcher`/`IQueryDispatcher` from `Magiq.Platform.*`. **DLC has no such SDK.** Decision (ADR-009): use **FastEndpoints' built-in in-process command bus** — reproduces the dispatch ergonomics with **zero new packages**:

```csharp
// Command + typed result
public sealed record CreateRunCommand(DateOnly SpecifiedDate, string CreatedBy)
    : ICommand<Result<RunSummary>>;

// Handler (lives in the same feature folder)
public sealed class CreateRunHandler(IRunStore runs, IMagiqAuth auth)
    : ICommandHandler<CreateRunCommand, Result<RunSummary>>
{
    public async Task<Result<RunSummary>> ExecuteAsync(CreateRunCommand cmd, CancellationToken ct)
    {
        if (await runs.HasActiveRunAsync(ct))
            return Result.Conflict("RunAlreadyActive");
        // create CleanupRun, persist process ticket, enqueue Hangfire ExecutePhase1, return summary
    }
}

// Endpoint dispatches
var result = await new CreateRunCommand(req.SpecifiedDate, ctx.Operator).ExecuteAsync(ct);
```

Commands/queries are `sealed record`s in feature folders; queries use the same primitive (a read-only command) rather than a second abstraction. The FastEndpoints **command bus** (synchronous, request-scoped) is distinct from the **Hangfire job queue** (ADR-001) used for long-running pipeline phases — don't conflate them.

### 5.4 Error handling — Results, not exceptions (magiq-media house rule)

magiq-media never throws for control flow: handlers return `Result<T, IDomainError>`, endpoints check `result.IsSuccess`, and a **shared base endpoint** maps the typed error to an HTTP status (`CatalogEndpoint.SendDomainErrorAsync`). Reproduce that:

- A small local `Result<T>` (or `CSharpFunctionalExtensions`, one tiny package) carrying success/value/error-code.
- A **`DlcEndpoint<TReq,TRes>` base** with `SendDomainErrorAsync(error)` that maps DLC's documented error contracts to status codes: `RunAlreadyActive`→409, `FolderValidationFailed`→422, `FolderIsLocked`→422, `ConfirmationRequired`→422, `SoapOperationFailed`→502/503. (Error shapes are enumerated in `dev-spec.md` → "Error Contracts".)

### 5.5 Context flow — the DLC analog of `IExecutionContext`

This is the trickiest translation. In magiq-media, a **DI-scoped `IExecutionContext`** carries `TenantId` (resolved from a validated JWT) + `Actor` (id/name/roles) into every endpoint and command. **DLC has no tenants and no JWT** — it's a single facility (NATA), single active run, MAGIQ-ticket auth. The equivalent ambient object is the **operator session**:

- Define a **scoped `ICurrentOperator`** (the DLC counterpart of `IExecutionContext`): `Username`, `IsAdmin` (allowlist check), and the **UI ticket** (Ticket A) for foreground SOAP calls. Resolved from the session token minted at `/api/auth/login`, via a small auth handler / middleware — **not** from a JWT claim.
- The **process ticket** (Ticket B) is **not** on `ICurrentOperator` — it belongs to the run. It's persisted on `CleanupRun.ProcessTicket` and read by **Hangfire jobs**, which run with no HTTP context. Background handlers resolve their ticket from the run record + the heartbeat service, never from `ICurrentOperator`.
- Endpoints inject `ICurrentOperator` and pass `Username` into commands as `CreatedBy` / `PurgeAuthorisedBy` — mirroring how magiq-media passes `context.Actor.Id` into commands. **Never read the operator from the request body**, same rule as "never read tenant from the payload."

Mapping cheat-sheet:

| magiq-media | DLC equivalent |
|-------------|----------------|
| `IExecutionContext` (scoped) | `ICurrentOperator` (scoped) |
| `context.TenantId` (from JWT) | *(none — single facility)* |
| `context.Actor.Id/Name/Roles` | `operator.Username` + `operator.IsAdmin` (allowlist) |
| JWT bearer auth | MAGIQ `AuthenticateUser` → session token → UI ticket |
| tenant resolution middleware | login endpoint + session/ticket store |
| ambient context in background workers | `CleanupRun.ProcessTicket` + heartbeat service |

---

## 6. Configuration surface (add sections as their stories land)

Full annotated schema is in `dev-spec.md`. Every section gets an `*Options` class in `Configuration/`, bound + validated like `ApplicationOptions`:

- `ConnectionStrings`: `AppDatabase`, `MagiqDocumentsDatabase`
- `MagiqDocuments`: `SoapEndpoint`, `AdminAllowlist[]`
- `Queries`: `CandidateDocuments`, `DocumentRegister`, `FolderPaths` — **system-level configurable raw SQL**, updatable without redeploy (Dapper executes them as-is; no ORM model)
- `DeletableFolderAcronyms[]` — **case-sensitive contains match**; NATA can add/remove
- `Hangfire`: `DashboardPath`, `WorkerCount` (1)
- `TicketHeartbeat`: `IntervalSeconds` (300; must be well under 1200)
- `RunProgress`: `DashboardPollIntervalSeconds` (30)

---

## 7. How we work together — the branch/PR protocol

**Division of labour:** _Chase_ owns git (branch creation, commits, pushes, PR completion). _Claude_ designs the branch plan and does the work inside the tree. This keeps commit authorship and approval firmly with Chase.

**The loop per work item:**
1. **Claude designs** the branch: name, the work-item(s) it closes, scope/acceptance, the files it touches, and the ordered task list. Mapped to Epic #34120's Features/Stories/Tasks.
2. **Chase creates** the branch off `main` and confirms it exists (or Claude stages the exact `git checkout -b` command).
3. **Claude implements** inside the working tree — endpoints, handlers, options, migrations, SPA — matching the conventions in §4–§6, staying inside that branch's scope.
4. **Chase commits & pushes**, opens the PR, and links the work items.

**Conventions to hold:**
- **Branch naming:** `feature/{workItemId}-{kebab-slug}` — matches the existing `feature/34129-scaffold-api-spa-host`. Bugfix → `bugfix/{id}-{slug}`.
- **One story per branch/PR** (magiq-media-style small slices). Tasks under a story are commits within its branch.
- **Work items:** each branch closes a Story (and its Tasks); PRs link the work items; keep the `document-lifecycle-cleaner` tag + per-branch tags.
- **Scope discipline:** a branch touches only what its story owns. New package? Add it to `Directory.Packages.props` **in the story that introduces it**, with a one-line justification comment.
- **Definition of done per slice:** builds clean under `latest-Recommended`; endpoint has full `Configure()` metadata; XML docs on public members; a `WebApplicationFactory` integration test where the story warrants it (`Program` is already `partial` for this).

**The ordered branch plan for Epic 34120 lives in `delivery-plan.md`.**

**Post-MVP:** Epic 34120 is delivered; the deferred backlog and its branch plan live in `deferred-work-plan.md` (ADO stories 34525-34528).

---

## 8. Quick-reference rules

- **Never** pull `Magiq.Platform.*` / DynamoDB / event-sourcing into DLC. Borrow shape, not infrastructure.
- **Every** endpoint route omits `api/` (global prefix adds it) and carries full `Configure()` metadata + `Version(1)`.
- **Results, not exceptions**, for domain outcomes; map to HTTP in a shared base endpoint using the dev-spec error contracts.
- **Check the SOAP `success` attribute**, not the HTTP status (SOAP always returns 200).
- **Two tickets:** UI ticket on `ICurrentOperator` (foreground); process ticket on `CleanupRun` (background/Hangfire). Don't cross them.
- **Configurable SQL** stays in config and runs through Dapper untouched — no ORM model over MAGIQ's schema.
- **Packages arrive with their story**, justified in `Directory.Packages.props`.
- **Business rule unclear?** `spec/NATA_..._v0.6.md` + `dev-spec.md` win. **Architecture question?** `decisions/log.md` + ADRs win.
- **Chase commits; Claude doesn't.** Claude designs branches and works inside them.
