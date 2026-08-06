# Decision Log

Append-only. One entry per decision. Do not edit past entries.

---

## [2026-05-04] Project initialised

**Context:** New project folder created for the NATA Document Lifecycle Cleaner — a yearly automated process to cull documents and folders from MAGIQ Documents based on a calendar year-end cutoff date.

**Decision:** Initialise as an AIS-OS Cowork workspace. Establish CLAUDE.md, MEMORY.md, and this decisions log as standard project scaffolding.

**Rationale:** Consistent structure across projects ensures Claude can pick up context across sessions without re-briefing. decisions/log.md is the authoritative record of architecture and design choices — brief.md defers to it rather than duplicating.

**Status:** Spec in draft (v0.2). Two blocking open questions must be resolved before architecture begins. No implementation decisions made yet.

---

## [2026-07-13] Implementation architecture and infrastructure

**Context:** With all blocking spec questions resolved (v0.3), the project is ready for architecture. The application is not simple CRUD — it is a long-running, multi-phase pipeline (identify → review → confirm → create archive library → move documents → delete empty folders → purge) with an interactive operator UI for the review and confirmation steps (Steps 6–7). The spec imposes two constraints that drive the design: document moves (Step 9) must resume from the point of failure with no rollback, and the purge (Step 12) runs as a background system process. Hosting is on-premises / customer-hosted (inside NATA's environment), not AWS — this project deliberately departs from the team's usual AWS-native stack. Frontend is React (chosen for a rich review experience); backend is C# with FastEndpoints (chosen for team familiarity and its REPR / vertical-slice model). Source is hosted in Azure DevOps Git, MAGIQSoftware organisation, repo `DocumentLifecycleCleaner`.

**Decision:**

1. **Background/pipeline engine — Hangfire.** Use Hangfire (not raw `BackgroundService`/`IHostedService`, not Quartz.NET, not the FastEndpoints built-in job queue) to run the archival, move, delete, and purge phases. Chain phases with Hangfire continuations so a phase only starts once its predecessor confirms complete (satisfies Step 10's "must not execute until moves confirmed"). Rely on Hangfire's persistence + automatic retries for the "resume from point of failure" requirement (Step 9), and on its dashboard for operator observability.

2. **Dedicated Hangfire database.** Hangfire storage lives in its own SQL Server database, separate from the MAGIQ Documents database. Keeps the app's job/state tables isolated from the records-management schema and avoids retention/cleanup of Hangfire tables interfering with the client DB.

3. **Run modelled as a persisted state machine.** Represent each execution as a persisted `CleanupRun` record with a status per phase. This makes the process resumable (restart reads the last completed phase), auditable, and enforces a single active run at a time. Per-document move failures (Step 9) are recorded against the run for the identify-skip-resume behaviour the spec requires.

4. **Hosting — IIS, in-process.** Host the ASP.NET Core/FastEndpoints app under IIS on-prem. The Hangfire server runs in-process within the same application. Single-server deployment; no clustering or distributed queue complexity needed (once-a-year, operator-triggered run).

5. **React served from the API's `wwwroot`.** The React SPA is built and published into the API's `wwwroot`, served as static files from the same ASP.NET Core app — no separate web server or CORS surface. **Confirmed feasible:** FastEndpoints runs on the standard ASP.NET Core minimal-API pipeline, so `UseDefaultFiles()` + `UseStaticFiles()` + `MapFallbackToFile("index.html")` coexist with `UseFastEndpoints()`. To keep the SPA deep-link fallback from swallowing API routes, give FastEndpoints a route prefix (e.g. `api`) so the catch-all fallback only matches non-API paths.

6. **API methodology — CQRS-lite vertical slice, not event sourcing.** Use the FastEndpoints REPR / vertical-slice pattern (each endpoint self-contained). Keep CQRS lightweight (commands/handlers); do **not** apply full event sourcing here — the domain is a workflow, not a rich aggregate, and event sourcing is reserved for magiq-media. The `CleanupRun` phase-transition log provides an audit trail if one is wanted.

7. **Progress reporting — SignalR (SSE acceptable fallback).** Push live progress for long phases (a move may cover thousands of documents) to the review/execution UI with SignalR, pairing with Hangfire's built-in progress tracking. SignalR degrades to polling automatically. If running WebSocket infrastructure on-prem is undesirable, Server-Sent Events is an acceptable one-way alternative since progress is server→client only.

**Rationale:** On-prem removes the team's usual SQS/Lambda options, so a persistent in-process job engine is needed; Hangfire gives persistence, retries, continuations, and a dashboard with the least ceremony, and directly satisfies the spec's resumability and background-purge constraints. Quartz.NET's clustering/advanced-scheduling strengths are irrelevant for a single-server annual run. A persisted state machine is the natural model for a resumable multi-phase workflow and gives auditability for a records-management context. Serving React from `wwwroot` yields a single deployable artifact under IIS with no CORS or second-server overhead. Event sourcing would be over-engineering for this workflow-shaped domain.

**Open items:** IIS in-process vs out-of-process hosting model (default in-process is expected); whether the app database and the Hangfire database are one dedicated DB or two; authentication/authorisation approach for the operator UI (not yet specified).

**Sources:**
- [Job Queues — FastEndpoints](https://fast-endpoints.com/docs/job-queues)
- [ASP.NET Core Background Jobs: Hosted Services, Hangfire, Quartz — BoldSign](https://boldsign.com/blogs/aspnet-core-background-jobs-hosted-services-hangfire-quartz/)
- [Quartz.NET vs Hangfire for .NET 8 — 10decoders](https://10decoders.com/blog/building-reliable-net-8-backends-with-hangfire-or-quartz/)
- [Tracking Progress — Hangfire Documentation](https://docs.hangfire.io/en/latest/background-processing/tracking-progress.html)
- [Communicate background job status with SignalR — Jerrie Pelser](https://www.jerriepelser.com/blog/communicate-status-background-job-signalr/)
- [Real-Time Progress Updates with SSE in ASP.NET — medialesson](https://medium.com/medialesson/real-time-progress-updates-for-long-running-api-tasks-with-server-sent-events-sse-in-asp-net-1c5fdbac6065)
- [FastEndpoints + Vertical Slice Architecture — antondevtips](https://antondevtips.com/blog/productive-web-api-development-with-fast-endpoints-and-vertical-slice-architecture-in-dotnet)
- [Overview of Single Page Apps (SPAs) — Microsoft Learn](https://learn.microsoft.com/en-us/aspnet/core/client-side/spa/intro?view=aspnetcore-8.0)

---

## [2026-07-13] Support both Docker and IIS deployment targets

**Context:** The earlier architecture entry fixed hosting on IIS in-process. The client may later prefer a containerised deployment, so the application should support both **IIS** and **Docker** without code changes. This supersedes the single-target hosting decision in the entry above; all other decisions in that entry (Hangfire, dedicated DB, React in `wwwroot`, CleanupRun state machine, CQRS-lite, SignalR) stand unchanged.

**Decision:**

1. **Two supported deployment targets — IIS and Docker.** The build produces artifacts for both. Under IIS the app runs behind the IIS reverse proxy; under Docker it runs as a container. No host-specific code paths.

2. **Stay hosting-agnostic.** Kestrel is the web server in both cases. All environment-specific settings — SQL connection strings (app DB and dedicated Hangfire DB), MAGIQ Documents API endpoints, listening ports — are supplied via configuration / environment variables, never hard-coded to a host. This is already compatible with the `wwwroot` static-hosting decision: the SPA is served from the same app regardless of target.

3. **Dockerfile builds one self-contained image.** The container build compiles the React SPA and publishes it into the API image's `wwwroot`, yielding the same single artifact deployed under IIS. Hangfire continues to run in-process inside the container.

**Rationale:** For a single-server, once-a-year operator tool, both IIS and a single container are equally viable; the only cost of supporting both is keeping configuration externalised and avoiding host-specific APIs, which is good practice regardless. This preserves the client's freedom to switch hosting without re-architecting.

**Open items:** which target is the default; if Docker, Windows vs Linux base image (driven by whether the MAGIQ Documents integration or SQL client has Windows-only dependencies).

---

## [2026-07-13] MAGIQ Documents integration approach — SOAP + direct SQL

**Context:** The prior entry left the Docker base image (Windows vs Linux) open, pending whether the MAGIQ Documents integration had Windows-only dependencies.

**Decision:** MAGIQ Documents is integrated via two paths: (1) a **SOAP web service API** for library/folder/document operations, and (2) **direct SQL Database** access for the pre-configured queries (Steps 1, 2, 5 — candidate retrieval and folder-path resolution). Neither path carries Windows-specific dependencies.

**Rationale / resolution:** Because the integration is host-agnostic, a **Linux container** is viable for the Docker target. The SOAP client is consumed via a generated proxy / `HttpClient` over standard .NET (cross-platform), and SQL access uses the cross-platform `Microsoft.Data.SqlClient`. This resolves the Windows-vs-Linux base-image open item from the entry above in favour of Linux being available (final choice still at the client's discretion).

---

## [2026-07-13] Default hosting, single application database, Dapper for MAGIQ SQL

**Context:** Resolving the remaining hosting/data open items so architecture can proceed.

**Decision:**

1. **IIS is the default deployment target.** Docker remains a supported alternative (per the earlier entry); the two-target, hosting-agnostic build is unchanged. IIS is simply the assumed default for delivery.

2. **One dedicated application database.** A single dedicated SQL Server database holds both the application's own state (`CleanupRun` records and related workflow tables) and the Hangfire tables. It stays separate from the MAGIQ Documents database. (Supersedes the "one DB or two" open item — one dedicated DB, not two.)

3. **Dapper for direct MAGIQ Documents SQL access.** Direct SQL communication with the MAGIQ Documents database (Steps 1, 2, 5) is handled with **Dapper**.

**Rationale:** A single dedicated DB keeps operational overhead low for a single-server annual tool while still isolating the app's tables from the client's records-management schema. Dapper fits the spec's requirement that these queries be system-level and configurable raw SQL — it executes the configured SQL and maps results without imposing an ORM model or schema assumptions, and runs on the cross-platform `Microsoft.Data.SqlClient` so it does not affect the Linux-container option.

**Open items:** authentication/authorisation for the operator UI (still open).

---

## [2026-07-13] Authentication & authorisation — piggyback on MAGIQ Documents

**Context:** Resolving the operator-UI auth open item.

**Decision:**

1. **Authentication delegated to MAGIQ Documents.** The app does not maintain its own credential store. It authenticates against the MAGIQ Documents SOAP endpoint `srv.asmx` via the **`AuthenticateUser`** action (username + password), which returns an **`AuthenticationTicket`** required on all subsequent web-service calls.

2. **Ticket tracked with sliding 20-minute timeout.** The ticket has a sliding 20-minute expiry (each call resets the window). The app stores the ticket per session and re-authenticates when it lapses.

3. **Admin allowlist in `appSettings.json`.** Authorisation is gated by a list of admin-only usernames stored in `appSettings.json` for now. An authenticated user not on the allowlist is denied. This is interim — a database-backed / configurable store is a likely future iteration.

**Rationale:** Piggybacking on Documents auth avoids a second identity system and keeps the app consistent with the platform operators already use; the allowlist adds a coarse admin-only gate on top with minimal machinery for launch.

**Open items (deferred to architecture):**
- **Background-job ticket continuity** — Hangfire phases (esp. Step 9 moves) can exceed the 20-minute sliding window and run beyond the operator's presence. Resolve via continuous SOAP activity keeping the window alive vs a dedicated service account for background phases. This is the most significant unknown, given the pipeline is the core of the app.
- **Ticket storage** — dedicated app DB (survives restarts) vs in-memory/cache.

---

## [2026-07-13] Two-ticket authentication model for UI vs long-running process

**Context:** Resolving the background-job ticket-continuity open item from the entry above. Confirmed behaviour: `AuthenticateUser` returns a **new, independent `AuthenticationTicket` on every call**, so multiple concurrent tickets can be held for the same user.

**Decision:**

1. **Two tickets per login.** At login the app calls `AuthenticateUser` twice: one ticket for the **UI session** and one dedicated to the **long-running process**. The two are independent, so the operator can log out (ending the UI ticket) without affecting an in-flight run.

2. **Keep-alive heartbeat on the process ticket.** The process ticket's sliding 20-minute window is held open by a lightweight periodic keep-alive SOAP call, in addition to incidental calls made during work. This covers lulls between phases, not just high-activity phases like the Step 9 move — more robust than relying on incidental call timing alone.

**Rationale:** Two independent tickets cleanly separate UI session lifecycle from the pipeline with no extra identity machinery, since the platform issues a fresh ticket per authentication. A dedicated heartbeat removes the fragile assumption that work-driven calls always fall within 20 minutes.

**Accepted limitation:** Both tickets live only for the app process's lifetime. If IIS recycles or the app restarts **mid-run**, the process ticket cannot be regenerated — re-authentication needs the password, which is deliberately not persisted. This is **accepted** for a once-a-year, operator-attended run: the operator re-authenticates and the persisted `CleanupRun` resumes from its last completed phase. A dedicated service account (credentials in secret config) would be the alternative if fully unattended restart-resilience were ever required — noted, not adopted.

**Remaining open item:** ticket storage location (dedicated app DB vs in-memory/cache); either works on single-server, and neither changes the accepted-limitation above.

---

## [2026-07-13] Persist the process ticket — supersedes the mid-run restart limitation

**Context:** The entry above assumed both tickets were in-memory only and treated a mid-run recycle as an accepted limitation requiring re-authentication. This corrects that.

**Decision:**

1. **Process ticket stored in the dedicated app database**, associated with the `CleanupRun`. It is persisted, not held only in memory.

2. **Ticket survives IIS recycles / app restarts.** On startup the app reloads the stored process ticket and resumes the keep-alive heartbeat — no re-authentication and no stored password. This holds provided the app resumes within the ticket's 20-minute sliding window, which a normal recycle comfortably does. (Only a downtime exceeding the sliding window would expire the ticket and force re-auth — not a normal recycle.)

3. **UI ticket is not persisted.** It does not need to survive a recycle; if the app restarts, the operator simply re-authenticates for the UI. Only the process ticket is persisted, because only the background run must continue uninterrupted.

**Supersedes:** the "accepted limitation" in the previous entry — a mid-run recycle no longer forces re-authentication of the background process. **Resolves:** the ticket-storage-location open item (dedicated app DB, chosen specifically for recycle survival).

**Rationale:** Persisting the one ticket the pipeline depends on removes the last fragility in the background run at trivial cost (one row in the app DB), while the ephemeral UI ticket needs no such treatment.

---

## [2026-07-22] Command/query dispatch — FastEndpoints built-in bus

**Context:** The CQRS-lite vertical-slice methodology (2026-07-13) requires an in-process command/query dispatch mechanism. The reference codebase `magiq-media` uses its proprietary `Magiq.Platform.*` dispatcher (`ICommandDispatcher`/`IQueryDispatcher`), which is deliberately excluded from this on-prem project. A vanilla equivalent was needed. No command exists in the repo yet (only the handler-less `PingEndpoint`), so the pattern is set before the first real slice.

**Decision:** Adopt **FastEndpoints' built-in in-process command bus**. Commands/queries are `sealed record`s implementing `ICommand<Result<T>>` in their feature folder; handlers implement `ICommandHandler<TCommand, Result<T>>`; endpoints dispatch via `command.ExecuteAsync(ct)` and map the `Result<T>` to HTTP through a shared `DlcEndpoint` base (the counterpart of magiq-media's `CatalogEndpoint.SendDomainErrorAsync`). Results, not exceptions. No new package. See **ADR-009**.

**Rationale:** Reproduces the magiq-media dispatch ergonomics the team knows, with zero additional dependency and no AWS-platform coupling. The FastEndpoints command bus (synchronous, request-scoped) is distinct from the Hangfire job queue (ADR-001) used for long-running pipeline phases. MediatR (pipeline behaviours, +1 dependency) and plain handler-injection (no uniform dispatch) were the considered alternatives.

**Prerequisites:** a shared `Result<T>` type and the `DlcEndpoint<TReq,TRes>` base class, introduced with the first command-bearing slice.

---

## [2026-07-23] Application-database access — Dapper + thin repositories, DbUp migrations

**Context:** Story 34131 (the persistence spine) is next. ADR-004 settled Dapper for the read-only MAGIQ Documents SQL but left the access technology for the application's *own* `CleanupRun*` tables open (Dapper vs EF Core vs a micro-ORM), and no schema versioning mechanism had been chosen. Both must be settled before 34131 code.

**Decision:** Access the app database with **Dapper over `Microsoft.Data.SqlClient`, wrapped in thin per-aggregate repositories** (hand-written SQL, no ORM model), and manage the app schema with **DbUp** — embedded, ordered, forward-only SQL scripts applied at startup and journaled in `SchemaVersions`, starting with a baseline of the four `CleanupRun*` tables. Hangfire continues to own its own schema via `UseSqlServerStorage(prepareSchemaIfNecessary)` in the same `AppDatabase` (ADR-005); DbUp does not touch Hangfire's tables. See **ADR-010**.

**Rationale:** One data-access idiom across the app and MAGIQ paths (consistent with ADR-004), no ORM/`Magiq.Platform.*` coupling, explicit reviewable SQL for an audit context, and journaled forward-only migrations that stay clean as later stories evolve the schema. EF Core (heavy, ORM-over-workflow) and a hand-rolled no-package runner (no version journal) were the considered alternatives.

**Packages introduced (Story 34131):** `Dapper`, `Microsoft.Data.SqlClient`, `dbup-sqlserver`. (`Microsoft.Data.SqlClient` is shared with the later MAGIQ Dapper story 34133.)

---

## [2026-07-27] MAGIQ SOAP consumption — typed HttpClient, not a WCF proxy

**Context:** Story 34132 (the MAGIQ SOAP primitive) is being cut. ADR-004 settled *that* MAGIQ is reached over SOAP `srv.asmx` but left the consumption style open — generated WCF proxy vs typed `HttpClient`. This was the one open sub-decision for the branch. The published WSDL was reviewed to decide: it is a classic ASMX service (SOAP 1.1/1.2 + HTTP GET/POST), ~1.3 MB, and its result payloads are typed `xsd:any` (`mixed="true"` + `<s:any/>`) — so the real response shape (the infoRouter `success` attribute + ticket) is **not** described by the WSDL.

**Decision:** Consume the SOAP service via a **hand-built typed `HttpClient`** (`IMagiqSoapClient`/`MagiqSoapClient`, `AddHttpClient`), not a WCF proxy. SOAP 1.1 document/literal, envelopes built with `System.Xml.Linq`, quoted `SOAPAction` header, operation namespace `http://tempuri.org/`. Endpoint + timeout + transient-retry are configurable options (Task 34158). The `success` attribute — not HTTP status — drives the outcome (`MagiqResponseReader`); `success="false"` is a business failure and is never retried, only transport faults (network/timeout/5xx) are. See **ADR-011**.

**Rationale:** Because the responses are `xsd:any`, a generated WCF proxy would surface untyped `XmlElement` for exactly the part that matters, so it buys no real type safety while adding the `System.ServiceModel.*` stack and a large generated artefact to keep in sync with a 1.3 MB WSDL. The hand-built client uses only framework XML APIs (**zero new packages**), gives full control of the wire format and a retry policy that understands the 200-with-`success="false"` contract, and fits the vanilla-primitives grain. WCF proxy and the ASMX HTTP GET/POST bindings were the considered alternatives.

**Packages introduced (Story 34132):** none — `System.Xml.Linq` / `System.Net.Http` are in the framework.

**Open detail:** the exact infoRouter result child-element names (`Ticket`, `ErrorMsg`/`ErrorNo`) are inferred (WSDL is `xsd:any`); matched case-insensitively with fallbacks, to be confirmed against a live response during the Story 34134 auth integration pass.

---

## [2026-07-27] Process-ticket heartbeat + expiry recovery (Story 34135)

**Context:** ADR-006/007 require a keep-alive heartbeat on the persisted process ticket (Ticket B) and an expiry-recovery path. Two frictions surfaced against the WSDL and the "no stored password" rule:
1. **Which SOAP op for keep-alive?** `RenewTicket` requires `UID`+`PWD` (we store no password, ADR-006), so it can't be used. `isValidTicket(AuthenticationTicket)` is password-less, takes just the ticket, and is used as the heartbeat — it both refreshes the 20-minute sliding window and reports validity.
2. **ADR-006 says "if the UI session is active, the app calls `AuthenticateUser` automatically" to recover an expired ticket — but `AuthenticateUser` also needs the password.** This clause is not implementable under the no-stored-password design.

**Decision (confirmed with Chase):** On a dead ticket the heartbeat **marks the run `Failed`** with `"Process ticket expired; re-authentication required."`; the operator logs in again (fresh Ticket B) and triggers Retry (a later story re-attaches the ticket). The heartbeat keeps the ticket alive continuously while the app runs, so true expiry only happens after >20 min of downtime. A transport error during a heartbeat is treated as transient (never fails a run). Startup reload is implicit — the heartbeat reads the active run's persisted ticket each tick.

**Deferred:** the ADR-006 "auto re-auth while UI active" path. The only password-less way to mint a fresh Ticket B is the WSDL's `CreateTicketforUser` (mints via a **server-configured trusted account**, password in web.config). That needs a configured trusted credential + a security review, so it's out of scope for 34135 and noted as the future auto-recovery mechanism.

**Assumptions to confirm at integration (xsd:any responses, like ADR-011):**
- `isValidTicket` **refreshes** the sliding window (assumed — any authenticated infoRouter call should; if not, swap to another lightweight authenticated read).
- Validity is read as: an explicit boolean in the result payload if present, else the `success` attribute (`MagiqResponseReader.ReadBoolean` → fallback).

**Config:** `TicketHeartbeat.IntervalSeconds` (default 300; validated 30–1199, i.e. under the 1200s window).

## [2026-07-27] Phase 1 identification body + Document Register export (Story 34139)

**Context:** Story 34139 (Steps 1–3) fills the identification stub left by 34137/34138. Three tasks: candidate documents (34177, Step 1), the Document Register (34178, Step 2), and the Excel export + download (34179, Step 3). Two shaping questions surfaced: (a) the dev-spec data model has no register table, and the delivery plan calls the register "for viewing (no retention)" — so where does the register live? (b) how should the background identification job behave on a query/config failure, given operator Reset/Retry is a later story?

**Decision:**
1. **Split the work by persistence, not by spec-step boundary.** The *background* identification job (`RunPhaseExecutor.ExecuteIdentificationAsync`) does only the persisted work: run the configurable `CandidateDocuments` query (Step 1) and populate `CleanupRunDocument` (all `Pending`) in batches of 500, emitting `PhaseStarted(total)` → per-batch `ProgressUpdated` → `PhaseCompleted`, then `AwaitInput(6)`. Candidate-folder derivation + protection (Steps 4–5) stay out — they are Story 34140.
2. **The Document Register (Steps 2–3) is an on-demand endpoint, not background work and not persisted.** `GET /api/v1/runs/{runId}/register/export` re-runs the configured `DocumentRegister` query for the run's cut-off date and streams an `.xlsx`. "No retention" is honoured literally: nothing register-shaped is written to the app DB (the schema has no table for it, and the columns are operator-defined). Every download reflects the query's current output. A new persistence store, `ICleanupRunDocumentStore`, owns the Step 1 inserts (+ `DeleteByRunAsync` so a re-invoked Hangfire job re-populates cleanly).
3. **Excel via ClosedXML** (delivery-plan recommendation). A stateless `IDocumentRegisterExcelWriter` derives columns from the untyped register rows (first-appearance order), bold+frozen header, native cell types for dates/numbers. **Package introduced: `ClosedXML` 0.104.2** (Reporting group).
4. **On failure, fail the run and stop.** A misconfigured/failing query marks the run `Failed`, logs a `Failed` phase event with the message, emits `RunStateChanged`, and returns (no rethrow) — so Hangfire does not hammer a permanent config error. `OperationCanceledException` is left to bubble so Hangfire re-queues the still-`Running` job on restart; `DeleteByRunAsync` at the top makes that re-run idempotent. Operator Reset/Retry semantics remain a later story.

**Rationale:** Persisting tens of thousands of arbitrary-column register rows for a throwaway report would add a table the spec doesn't define and duplicate data the query already returns on demand; regenerating on download is cheaper and always current, and matches "no retention". Failing fast on a config error (rather than relying on Hangfire's 10 automatic retries) gives the operator a clear, immediate `Failed` state consistent with the CleanupRun state machine, while still letting genuine transient shutdown cancellation resume via Hangfire. Reusing the existing `IMagiqDocumentQueries` (Story 34133) for both Step 1 and Step 2 keeps all MAGIQ SQL in configuration (ADR-004) with zero embedded schema.

**Packages introduced (Story 34139):** `ClosedXML` 0.104.2.

**Scope note:** backend only (the three tasks are backend). The operator's "Download register" button and any candidate-count surfacing land with the review UI (Story 34141), the same way the 34138 SignalR client is built but not yet mounted.

**Deferred / to confirm:** operator Reset/Retry re-enqueue of a `Failed` identification run (needs the guard to admit a re-run from `Failed`) — a later story. Register export currently maps any query failure to `502 DocumentRegisterExportFailed`; a dedicated 5xx for "query not configured" vs. an upstream SQL fault can be split later if operators need to tell them apart.

## [2026-07-27] Folder identification data shape + protection-vs-lock precedence (Story 34140)

**Context:** Story 34140 (Steps 4–5 + Rule 2) derives the candidate folder list, applies full-ancestor protection, marks acronym-locked folders, resolves paths, and populates `CleanupRunFolder`. `CleanupRunFolder` needs per-folder **document count, folder count, size**; Rule 2 needs each folder's **parent/ancestor chain** and **which folders hold a post-cutoff (> cutoff) document**. The three queries defined through Story 34133 (`CandidateDocuments`, `DocumentRegister`, `FolderPaths`) carry none of that — `CandidateDocuments` returns no folder id and only pre-cutoff documents. Approach chosen with Chase: **add configurable queries** rather than parse document paths or hard-code schema (keeps ADR-004's "all MAGIQ schema in config" grain).

**Decision:**
1. **One new configurable query — `Queries:CandidateFolders`** (parameter `@specifiedDate`). Returns each candidate folder **and its full ancestor chain** with `FolderId`, `ParentFolderId` (null at root), `FolderName`, `DocumentCount`, `FolderCount`, `SizeBytes`, and `ContainsPostCutoffDocument` (bit). Folding the Rule 2 trigger into a bit column on this query avoids a second protection query. `Queries:FolderPaths` (existing) still resolves paths (Step 5).
2. **In-app rules over the result** (not in SQL): full-ancestor protection propagates *up* the `ParentFolderId` chain from every folder with `ContainsPostCutoffDocument = 1`; acronym lock is a case-sensitive contains match of `FolderName` against `DeletableFolderAcronyms`.
3. **Protection overrides the acronym lock.** A folder that is both acronym-matched and protected is **not** pre-locked/pre-selected — `Status = Protected`, `IsLocked = 0`, `IsSelectedForDeletion = 0`. Rule 2 ("must not be deleted") is a hard safety rule and outranks the acronym convenience pre-selection; it also avoids a dead-end where a force-selected, non-deselectable locked row is blocked by the Step 7 delete-constraint (Rule 4) with no operator escape.

**Rationale:** The candidate-folder + ancestor closure in one query lets the app do protection propagation and acronym matching with plain in-memory logic (testable, no schema assumptions), while all schema stays operator-configurable. Doing ancestor propagation in-app (not SQL) keeps the recursive/tree logic out of the configurable SQL the operator maintains. Protection-over-lock is the safety-preserving reading of the spec (Rules 2 and 4 are absolute; the acronym pre-lock is a convenience) and the only reading without an unresolvable UI dead-end.

**Config introduced (Story 34140):** `Queries:CandidateFolders`; `DeletableFolderAcronyms[]` gets its first bound options class (case-sensitive contains). Contract written up in `spec/dev-spec.md` → "Folder Identification (Steps 4-5)".

**Sequencing:** implement after Story 34139 merges — 34140 extends the same `RunPhaseExecutor.ExecuteIdentificationAsync` method 34139 changed (Steps 4–5 slot between Step 1 and the Step 6 `AwaitInput`), so stacking both uncommitted would entangle the two stories' diffs.

## [2026-07-28] Step 7 confirm + delete-constraint scope (Story 34142)

**Context:** Story 34142 has two tasks — confirmation screen (34186) and delete-constraint validation + blocker reporting (34187). The delivery plan also lists a Step 8 archive-library modal and `Features/Libraries/`, but "choose existing library" needs a MAGIQ `ListLibraries` SOAP op that does not exist (the SOAP client only has auth/ticket ops; the archive SOAP ops — `CreateDomain`/`Move`/`DeleteDomain` — arrive with Story 34143). Two shaping decisions.

**Decision:**
1. **`POST /api/v1/runs/{runId}/confirm`** validates the delete constraint (Rule 4 — no `IsSelectedForDeletion` folder may be `Protected`, else `422 FolderValidationFailed` with the blocking `{folderId, folderPath, reason}` list), validates + captures the archive-library choice and purge pre-authorisation on the run, and enqueues archival via `IRunPipeline.StartArchival`. `404 RunNotFound`, `409 RunNotAwaitingConfirmation`, `400 InvalidArchiveLibrarySelection`.
2. **Confirm moves the run `AwaitingInput → Running`** (new `CleanupRun.ConfirmDeletions`), rather than leaving it AwaitingInput. This guards against a double-confirm (a second POST hits the 409) and reflects that confirming starts execution; the archival job then refines phase/step. When `autoProceedWithPurge` is set, the confirming operator + timestamp are recorded as the purge authorisation (Rule 5, Path A).
3. **"Choose existing library" is deferred to Story 34143.** The Step 8 modal fully supports **create new** (name prefilled `Archive - {Mon YYYY}`, optional subfolder) — which needs no SOAP, since the library is created during archival — and the confirm API accepts `mode: "existing"` with a `libraryId`. Only the existing-library *listing* UI (needs `GET /api/libraries` → SOAP `ListLibraries`) waits for 34143, where the archive SOAP ops live. Keeps speculative SOAP out of a confirm story and grouped with the other domain ops.

**Rationale:** Create-new is the spec's prefilled default path and unblocks the whole confirm→archive→cleanup flow end-to-end without adding an unverified SOAP op (the WSDL is `xsd:any`, per ADR-011). Blocker reporting is inline on the rows (spec Step 7 resolved: "inline on blocked rows. No separate banner"). Moving to Running on confirm mirrors how the run leaves NotStarted when identification is enqueued, and gives a clean idempotency guard.

**UI note:** the SetupWizard now drives Step 6 → Step 7 → "archival started", and mounts the Story 34138 `RunProgressPanel` on that final view (its first real mount). The interim run-id loader in the app shell still stands in for the jobs dashboard.

**Deferred:** `GET /api/libraries` + `GET /api/libraries/{id}/folders` (SOAP `ListLibraries`) and the Step 8 "choose existing" + subfolder-browser UI → Story 34143.

## [2026-07-28] Archival phase — SOAP shapes, path-based move, resume model (Story 34143)

**Context:** Story 34143 fills the archival phase (Steps 8–9): create the archive library, move the candidate documents, with identify-skip-resume (34188/34189/34190). The `srv.asmx` WSDL (in the repo root) was read to ground the SOAP shapes rather than guess.

**Decision:**
1. **SOAP ops from the WSDL** (added to `IMagiqSoapClient`): `CreateDomain`(AuthenticationTicket, DomainName, Anonymous, Hidden, WelcomeMessage) → the archive library; `CreateFolder`(AuthenticationTicket, Path) → the optional subfolder; `Move`(AuthenticationTicket, **SourcePath, DestinationPath**) → the document move. Move is **path-based**, which fits — `CleanupRunDocument.DocumentPath` is the source and the destination is the library path. Result payloads are `xsd:any`, so outcome is read from the `success` attribute (ADR-004) via the shared `ParseAck`/`ParseCreateDomain`; the exact shapes are **to confirm at integration** (same caveat as ADR-011).
2. **Destination path is derived from the name, not an id.** infoRouter addresses a domain as `/{DomainName}`; the destination is that root + the optional subfolder. So no library id is needed to move — `ArchiveLibraryId` is used only as the **create-idempotency marker** (null = not yet created; set to the returned id, or the root path when the response omits one) and for the later Step 11 delete.
3. **Resume model.** The archival job is safe to re-invoke: it enters the phase only if not already in it (no step reset), skips `CreateDomain` when `ArchiveLibraryId` is set, and moves only the *movable* set (`MoveStatus <> 'Moved'`). Step 9 does a full pass then **one retry** over the still-failed; any remaining failures **fail the run** (no rollback) for operator retry (deferred). Per-document status is persisted per batch (size 25).
4. **Cleanup gating.** Archival returns normally even on failure (sets the run `Failed`, consistent with identification), so the Hangfire `OnlyOnSucceeded` continuation still fires. `ExecuteCleanupAsync` now guards: it skips a `Failed` run and skips while `HasUnmovedDocumentsAsync` is true — implementing the Step 10 rule ("must not run until all moves confirmed complete") and preventing a failed run from being resurrected by the continuation.

**Rationale:** Grounding on the real WSDL removes most of the guesswork (only the `xsd:any` *response* shapes remain to confirm). Name-derived paths avoid a dependency on parsing an id out of an `xsd:any` response. Marker-based (not step-based) create-idempotency survives a `StartPhase` step reset. Failing normally + a cleanup precondition guard keeps control flow Result-shaped (no exceptions for control flow) while still stopping cleanup after a failed move.

**Known edge (accepted):** per-batch status persistence leaves a small window — a crash after a successful SOAP `Move` but before the batch's DB update would, on resume, re-`Move` an already-moved document (its path now missing → recorded Failed). Narrow timing on an annual on-prem job; per-document persistence (10k+ individual UPDATEs) was judged not worth the cost. Revisit if integration shows `Move` is not safely repeatable.

**Still deferred (from 34142):** `GET /api/libraries` (SOAP `GetDomains`) + the Step 8 "choose existing" / subfolder-browser UI. Create-new is the working path; the confirm API already accepts `mode:"existing"`, and `Move`/paths would work for an existing library too once the picker supplies the name.

## [2026-07-28] Cleanup phase — folder delete, targeted purge, Path A/B (Story 34144)

**Context:** Story 34144 fills the cleanup phase (Steps 10–11): delete the now-empty source folders, then delete + purge the archive library — the irreversible final deletion. Two tasks (34191 empty-folder deletion, 34192 archive delete + purge). WSDL-grounded again.

**Decision:**
1. **SOAP ops from the WSDL:** `DeleteFolder`(ticket, Path), `DeleteDomain`(ticket, DomainName), `GetRecycleBinContent`(ticket), `PurgeRecycleBinItem`(ticket, ItemHandler). Ack ops reuse `ParseAck`; the recycle-bin listing is parsed leniently (per-item handle + name off attributes/children) — `xsd:any`, **to confirm at integration**.
2. **The archive library is a quarantine.** Culled documents are moved into it (Step 9); Step 11 **deletes + purges the whole library** = the permanent deletion. Only the archive library is purged; the emptied *source* folders are deleted to the recycle bin (Step 10) but not purged (spec requires purging only the archive library).
3. **Targeted purge (operator's choice, 2026-07-28).** After `DeleteDomain`, `GetRecycleBinContent` → match this run's library by name → `PurgeRecycleBinItem` on that one handle. Never `EmptyRecycleBin` (would purge the account's whole bin). Best-effort with logging: `DeleteDomain` may already have run on a resume, and a recycle-bin miss is warned (manual purge fallback), not fatal — the purge is a background/eventual step.
4. **Path A / Path B (Rule 5).** `ExecuteCleanupAsync` does Step 10 always. For Step 11: if `AutoProceedWithPurge` (pre-authorised at Step 7) it deletes+purges inline and completes (Path A); otherwise it pauses at `AwaitingInput` step 11 ("Ready for purge"). `POST /api/v1/runs/{id}/purge` requires the typed phrase **"permanently delete"** (else `422 InvalidConfirmation`), records the operator + time (`AuthorisePurge`: AwaitingInput→Running), and enqueues `ExecutePurgeAsync` which deletes+purges and completes (Path B). `404 RunNotFound`, `409 RunNotReadyForPurge`.
5. **Folder-delete is best-effort.** A failed `DeleteFolder` is surfaced as `ItemFailed`, marked `Failed`, and does **not** fail the run — the archive purge (the point of the run) still proceeds. Move/purge failures fail the run; a stray empty-folder that won't delete does not.

**Rationale:** Targeted purge is the safe reading of "permanently purge the archive library" without collateral damage on a shared account. Best-effort delete/purge with logging keeps the phase resumable (DeleteDomain/PurgeRecycleBinItem aren't cleanly idempotent, so tolerate "already gone"). The typed-confirmation + AwaitingInput-step-11 gate implements Rule 5 Path B; Path A reuses the purge auth recorded at Step 7 (34142).

**Known edge (accepted):** the recycle-bin name match (`Name` contains the library name) could in principle match an unrelated item with a superstring name; the process account's bin is expected to hold only this run's deletions, and the match is confirmed at integration. If ambiguous, tighten to an exact-name/most-recent match once the item shape is known.

**Pipeline complete:** Steps 1–11 are now implemented end to end (create → identify → review → confirm → archive/move → delete/purge). Remaining epic work is non-pipeline: dual hosting (34130) and deployment docs (34145).

## [2026-07-28] Dual hosting: IIS + Docker (Story 34130)

**Context:** Package the single API-serves-SPA artifact for both Windows IIS and Linux Docker, with externalised config (tasks 34150 Dockerfile, 34151 IIS web.config/profile, 34152 config docs). The API csproj already reserved a spot for the SPA publish hook.

**Decision:**
1. **SPA publish hook in the API csproj.** A `PublishSpa` MSBuild target (`AfterTargets="ComputeFilesToPublish"`) runs `npm ci && npm run build` and adds `wwwroot/**` to the publish output. It only runs on `dotnet publish`, and only builds the SPA when `BuildSpa` is true (defaults true in Release). So an IIS publish is self-contained; the Docker build passes `-p:BuildSpa=false` because it builds the SPA in a dedicated Node stage (no Node in the .NET SDK image).
2. **Multi-stage Linux Dockerfile:** `node:20-alpine` (SPA) → `dotnet/sdk:8.0` (restore + publish with the SPA copied into wwwroot) → `dotnet/aspnet:8.0` runtime on port 8080. Plus a `.dockerignore` (keeps secrets/build outputs out of the context) and a convenience `docker-compose.yml` (app + a bundled SQL Server for the app/Hangfire DB; MAGIQ DB + SOAP stay external via config).
3. **IIS in-process:** `AspNetCoreHostingModel=InProcess` in the csproj, a committed `web.config` (ANCMv2, in-process, stdout logging off, env block), and an `IIS.pubxml` publish profile (framework-dependent, win-x64). The hosting-bundle prerequisite is documented. The hosting model is inert under Kestrel/Docker.
4. **Config externalised + documented (34152):** `docs/configuration.md` lists every key with its `Section__Key` env-var form and per-host guidance; `.env.example` is a fillable template (was empty); README gains a Deployment section. No host-specific code — the same build runs both places.

**Gotchas handled:** `*.pubxml` is gitignored by the default VS ignore, so a `!…/IIS.pubxml` exception was added to keep the profile tracked (it's a deliverable). The `PublishSpa` target excludes already-resolved files to avoid duplicate-publish errors and errors clearly if `wwwroot/index.html` is missing at publish time.

**Not verified here:** no .NET SDK on the bridge VM, so no compile/`docker build`/`dotnet publish` dry-run was possible — validated by XML/YAML well-formedness and review. Worth a real `docker compose up --build` and an IIS publish smoke test on merge.

## [2026-07-29] SOAP integration verified against training — parser fixes (Story 34525)

**Context:** Story 34525 (deferred item 0) ran the inferred `xsd:any` SOAP contracts against a live
`training.magiqdocuments.com` and reconciled the parsers. Chase captured a real end-to-end cull
(login → create → identify → review → confirm → archive/move → delete-empty → purge); raw responses
for all nine ops are recorded in `DocumentLifecycleCleaner/SOAP-VERIFICATION-34525.md` (Part A). Part B
(the four configurable SQL queries) is still to be captured.

**Confirmed as-built:** the universal response shape is
`<{Op}Result><response success="true|false" error="..." [attrs] xmlns="">[children]</response></{Op}Result>`
— a **nested element** (not an escaped/CDATA string), `success` an **attribute** on `<response>`, as
`ReadOutcome`/`UnwrapPayload` assumed. `isValidTicket` (validity via the `success` fallback, incl. the
`[901]` expired case), `CreateDomain` (no id returned → `DomainId` null → path-addressing fallback),
`CreateFolder`, `Move`, `DeleteFolder`, `DeleteDomain`, and `PurgeRecycleBinItem` (`ItemHandler` +
handle round-trip) all verified. On failure, `error` carries a bracketed `[code]message` — there is no
separate `errorno` attribute, so `ReadOutcome` returns `code=null`, `message="[901]…"` (accepted).

**Two defects found and fixed:**

1. **`AuthenticateUser` ticket is an attribute, not an element (login was broken).** The ticket comes
   back as `ticket="…"` on `<response>`, but `MagiqResponseReader.ReadTicket` only looked for a `ticket`
   *element* or bare text → returned null → `ParseAuthenticateUser` failed "success but no ticket".
   **Fix:** `ReadTicket` now also reads a `ticket` **attribute** (element → attribute → text order).

2. **Step 11 targeted purge matched nothing (corrects the 2026-07-28 "known edge").** `DeleteDomain`
   does **not** create a single domain recycle-bin entry — it scatters the domain's **contents** into
   the bin as individual `<document>`/`<folder>` items, each with `DeletePath="\{ArchiveLibraryName}"`
   and its own `Handler`. The old logic (`Items.FirstOrDefault(Name.Contains(library))` + one purge)
   matched no item and, even fixed, would purge only one. **Fix:** `RecycleBinItem` +
   `ParseRecycleBinContent` now also capture **`DeletePath`**; the purge selects **every** item whose
   `DeletePath` equals `\{library}` (or starts with `\{library}\` for nested subfolders — exact/segment
   match, no substring collision) and purges **each** handle, aggregating purged/failed counts into the
   log. The "nothing matched → warn, manual purge may be needed" guard is retained.

**Files touched:** `Integration/Magiq/Soap/MagiqResponseReader.cs` (ReadTicket),
`Integration/Magiq/Soap/RecycleBinItem.cs` (+DeletePath),
`Integration/Magiq/Soap/MagiqSoapClient.cs` (`_deletePathNames`, parse call),
`Pipeline/RunPhaseExecutor.cs` (Step 11 purge selection + loop).

**Rationale:** both are exactly the `xsd:any` response-shape risks 34525 existed to retire, grounded now
in real training responses rather than the WSDL (which types every result as opaque `xsd:any`).

**Open sub-question (non-blocking):** whether an emptied domain *shell* survives `DeleteDomain` or the
container itself is removed — not needed for the purge (contents are matched by `DeletePath`), noted for
completeness. **Still to do:** Part B SQL-query column-shape confirmation; real `dotnet build` + a live
re-run to confirm login and the multi-item purge (no .NET SDK on the bridge VM).

## [2026-07-29] Configurable SQL queries designed against the MAGIQ schema (Story 34547)

**Context:** Story 34547 (Part B of the 34525 verification) — the four `Queries:*` in `appsettings.json`
shipped **empty** (site-configured, no schema in code per ADR-004), and had never been authored against
NATA's real MAGIQ Documents schema. Chase supplied the `CREATE TABLE` definitions (`PUBLICATION`,
`FOLDERS`, `FOLDERMAP`, `DOMAINS`, `VERSIONS`); the full design — column contracts, rules, per-query SQL,
and the Q&A that resolved the unknowns — is captured in
`DocumentLifecycleCleaner/SQL-QUERY-DESIGN-34547.md`. The four queries are now written into
`appsettings.json` `Queries:*`, ready to run against training to fill Part B of
`SOAP-VERIFICATION-34525.md`.

**Decision:**

1. **Modification date = `PUBLICATION.LASTUPDATED`** (confirmed with Chase). Candidacy = `LASTUPDATED <=
   @specifiedDate`; the Rule 2 protection trigger = a directly-held document with `LASTUPDATED >
   @specifiedDate`.

2. **`FOLDERMAP` (closure table) replaces recursive CTEs.** For a folder `F`, every ancestor is
   `SELECT PARENTID FROM FOLDERMAP WHERE FOLDERID = F` (`DEEP` = distance) — used for both ancestor
   expansion (`CandidateFolders`) and path building (`FolderPaths` + the path columns in
   `CandidateDocuments`/`DocumentRegister`). The domain is **not** a `FOLDERMAP` descendant and has no
   self-row; the `DomainId` appears only as `PARENTID` at `DEEP = 1`. Root folders are detected via
   `FOLDERS.PARENTID = DOMAINID` (emitted as `ParentFolderId = null`), and the domain node is excluded
   everywhere via `<> f.DOMAINID`. Recommended supporting index:
   `FOLDERMAP(FOLDERID, DEEP) INCLUDE (PARENTID)`.

3. **Scope = single source library.** Since the code binds only `@specifiedDate`/`@folderIds`, the library
   scope is a literal `DECLARE @SourceDomainId int = 0;` at the top of the configured `CandidateDocuments`,
   `DocumentRegister`, and `CandidateFolders` SQL. **Placeholder `0` until NATA's source-library `DOMAINID`
   is supplied** — must be set before a real run.

4. **Paths composed `/Library/Folder/Sub`** (forward-slash, leading `/`, library segment from
   `DOMAINS.NAME`), built from the ordered `FOLDERMAP` chain via `FOR XML PATH('') … .value('.', …)` so
   folder names containing `&`/`<` decode back correctly instead of XML-escaping. Must line up with the
   SOAP `Move`/`DeleteFolder` path ops — confirmed at Part B against training.

5. **Default Document Register authored — NATA has no existing register report.** This **voids the spec
   Step 2 "reuse the existing pre-configured report" assumption.** `DocumentRegister` now ships a sensible
   default over the same candidate set (id, name, folder path, folder, library, modified/published/
   registered dates, owner, last-modified-by, doc type, author, MIME, size, retain-until, disposition
   date). It stays system-configurable, and its SELECT aliases become the Excel headers verbatim, so NATA
   can add/remove columns without a code deploy.

6. **Type mapping:** `PUBLICATIONID`/`FOLDERID` cast `int → nvarchar` (code maps `string`);
   `SUM(CAST(DOCUMENTSIZE AS bigint))` for `SizeBytes` (`long`, overflow-safe); post-cutoff flag as `bit`.
   `CandidateFolders` review counts (`DocumentCount`/`FolderCount`/`SizeBytes`) are direct + date-unfiltered
   (they describe the folder's real current contents); the post-cutoff bit is directly-held only —
   protection propagation stays in-app (per the 2026-07-28 34140 entry).

**Rationale:** The closure table makes the hard query (candidate folders + full ancestor chain) a single
set operation rather than a recursive walk, and keeps path resolution index-seekable. Keeping library scope
as a `DECLARE`d literal honours ADR-004 (all MAGIQ schema/scope in configuration, code binds only its two
documented params). Authoring a default register is the minimal way to satisfy Step 2 now that the assumed
existing report doesn't exist, while preserving the operator-configurable, no-fixed-shape contract the code
already expects.

**Still to do:** set `@SourceDomainId` to the real source-library `DOMAINID`; run all four against training
to confirm column shapes/types and fill Part B of `SOAP-VERIFICATION-34525.md`; verify the library-root
edge case (documents/folders directly under `FOLDERID = DOMAINID`) composes a correct path; confirm the
default register column set meets NATA's audit needs.

## [2026-07-29] Configurable queries move to a DB-backed store with an admin UI + bound source-library param

**Context:** The four queries were first written into `appsettings.json` `Queries:*` (entry above). Chase
judged minified SQL-in-JSON crude — hard to read, diff, and escape — and chose, over external `.sql` files,
to store the queries in the **application database** and edit them through an **admin UI**. Separately, the
per-run source-library scope (`@SourceDomainId`, previously an inline `DECLARE`) is to become a **bound
parameter** to remove any SQL-injection surface. This **supersedes the `appsettings.json` storage mechanism**
from the earlier 2026-07-29 entry (the authored SQL is retained, repurposed as seed data).

**Decision:**

1. **Queries live in a dedicated app-DB table** (e.g. `ConfiguredQuery`: `QueryKey` PK, `Sql`,
   `UpdatedAtUtc`, `UpdatedBy`, concurrency token), created via a DbUp migration (ADR-010) and **seeded**
   with the four authored defaults. `MagiqDocumentQueries` reads SQL from the store (cached, invalidated on
   update) instead of `IOptions<QueriesOptions>`. The first-use "query not configured" guard is retained.

2. **Admin UI + endpoints to view/edit the SQL.** Admin-only (via `ICurrentOperator` + the MAGIQ admin
   allowlist, ADR-006), on the vanilla `DlcEndpoint` base, versioned, `api/`-less routes: list, get, update.
   Query bodies remain trusted admin-authored config; only admins can edit.

3. **`@sourceDomainId` becomes a bound Dapper parameter.** The source-library `DOMAINID` moves out of the
   SQL body into a config setting the executor **binds as a parameter** alongside `@specifiedDate`
   (`CandidateDocuments`, `DocumentRegister`, `CandidateFolders`; `FolderPaths` is unaffected). No value is
   ever concatenated into SQL — removes the injection surface Chase flagged.

4. **`appsettings.json` `Queries:*` SQL strings are removed** once the store lands; `CommandTimeoutSeconds`
   stays (plus the new source-library id setting). The authored SQL becomes the DbUp seed, rewritten to use
   the `@sourceDomainId` parameter in place of the `DECLARE`.

**Rationale:** A DB-backed store keeps queries system-configurable and deploy-free to change (the ADR-004
requirement) while giving a proper editing surface and audit (`UpdatedBy`/`UpdatedAtUtc`) — better than
JSON escaping or loose `.sql` files for a records-management product where change provenance matters.
Binding the one dynamic scalar is the correct injection-safe design; the SQL bodies themselves are trusted
admin configuration, not user input. This is scoped as its own story under Epic 34120 (post-MVP), not part
of the 34547 verification.

**Follow-up:** new ADO story + tasks (schema+seed, store+executor with bound param, admin endpoints, admin
UI, config cleanup); update `dev-spec.md` (config schema + query contract) and `CLAUDE.md` file map.
Story 34547's verification still runs against these queries — just sourced from the store, not JSON.

---

## [2026-07-30] Source library becomes per-run operator input (Story 34566)

**Context:** `@sourceDomainId` was a single install-wide config value (`MagiqSource:LibraryDomainId`,
`MagiqSourceOptions`) bound into the Phase 1 queries. That forced one source library per deployment and
made "set `@SourceDomainId` before first run" a go-live step.

**Decision:** The source library becomes **per-run operator input**. On the new-run form the operator picks
the source domain from the live `GetDomains` list (the same picker as Step 8 archival, all domains, with
standard/archive/hidden icons) alongside the cutoff date. The chosen `SourceDomainId` + name are persisted
on `CleanupRun` and passed into `IMagiqDocumentQueries` per call, bound as `@sourceDomainId`.
`MagiqSourceOptions` and its appsettings section are removed. Because the app is unreleased, the schema
change is folded into `0001_baseline.sql` (the interim `0002`/`0003` scripts are consolidated back into
the single baseline and deleted) with the two source columns **NOT NULL** — a fresh DB is built from the
one baseline. Configured SQL is unchanged — it already binds `@sourceDomainId` (the `DECLARE @…`
in `SQL-QUERY-DESIGN-34547.md` was illustrative only). Date model unchanged (single year-end cutoff).

**Rationale:** Makes the tool multi-library without a redeploy, puts the scope decision with the operator
who knows it, and retires the pre-go-live `@SourceDomainId` config step. Reuses the 34528 `GetDomains`
list, so no new integration surface.

**Status:** Implemented on `feature/34566-run-source-domain` (tasks 34567–34570); pending Chase's
build/PR/merge.

---

## [2026-07-31] Schema verification for the configured MAGIQ queries (Story 34575)

**Context:** NATA runs an on-prem MAGIQ Documents instance the team does not control. The app's only
dependency on that schema is mediated by the four operator-configurable queries (ADR-004) — the app
never names a MAGIQ table. A MAGIQ version upgrade, or a query edit, can silently drop/rename/retype a
column the pipeline's mapping code depends on, and today that only surfaces **mid-run** — the worst
failure point for a once-a-year destructive tool. Chase asked for a way to check the schema up front.
Scope was agreed interactively: **on-demand admin action only** (no run-creation gate — an operator
pre-flight before a cull and after any MAGIQ upgrade); **names required + types compatibility-checked,
extras ignored**; the report carries **actual-vs-expected** type.

**Decision:**

1. **Verify the query result contract, not MAGIQ's tables.** Because the schema dependency is entirely
   indirect (mediated by the configurable queries), verification checks whether each query still
   produces the output columns the Dapper-mapped records require. The required-column set is a **code
   constant** (`SchemaContracts`) derived from the result records — the *queries* are operator-editable,
   the *contract the code consumes* is fixed. The Document Register has operator-defined columns, so it
   has no fixed contract and is checked only for executability.

2. **Mechanism — `CommandBehavior.SchemaOnly` + `GetSchemaTable`.** Describe each query's live
   result-set shape without executing it (no rows, no data touched); diff column names + SQL types
   against the contract. Chosen over `sys.dm_exec_describe_first_result_set` because it rides the normal
   `SqlCommand` parameter path (uniform for all four queries) and needs no per-query `@params` string;
   the deprecated-`FMTONLY` caveat doesn't bite our single-statement selects. The one wrinkle — Dapper's
   `IN @folderIds` list syntax in `FolderPaths`, invalid for a raw command — is handled by rewriting it
   to `IN (@folderIds)` with a single placeholder for the probe. A SQL fault (missing table/column,
   syntax, undeclared parameter) is surfaced as `QueryError`.

3. **Type-compatibility matrix mirrors the reader, conservatively.** `string` ← char family only (an
   int read as string throws at runtime); integers accept **widening only** (so a `bigint` where an
   `int` is required — a possible overflow — is flagged); `bool` ← `bit`. Dapper is sometimes more
   lenient via `Convert`, so a flagged mismatch may still happen to run — surfacing the drift is the
   point. **Nullability is not checked** (SchemaOnly cannot know whether live rows contain nulls, and
   computed columns over-report nullability); **extra columns are ignored**.

4. **Surface — admin screen, not a gate.** `POST /api/v1/admin/schema/verify` (admin-allowlisted, on the
   vanilla `DlcEndpoint` bus, `Version(1)`, `api/`-less route) returns a per-query/per-column report; a
   **Verify schema** button + report panel on the existing Configured Queries screen (`/admin/queries`)
   renders it. A failing check is a normal `200` with `passed:false`, not an HTTP error. Enums are
   surfaced as their names via a response view (the `RunSummary` convention), since the app does not
   register a `JsonStringEnumConverter`.

**Rationale:** Verifying the *result contract* is the meaningful check for a design that deliberately
holds no schema in code — it catches exactly the "MAGIQ changed between versions" failure modes
(dropped/renamed/retyped column, or a query that no longer binds) without re-introducing table
knowledge the app avoids. SchemaOnly keeps it read-only and side-effect-free. On-demand (not a gate) is
the accepted tradeoff for an attended annual run: the residual risk is an operator who skips it,
mitigated by admin-screen copy prompting a pre-cull check. The gate remains available as a future
tightening if wanted.

**Residual risk / to confirm at integration (same class as ADR-011/Story 34525):** that
`GetSchemaTable`'s `DataTypeName` returns bare type names (`nvarchar`, `bigint`, `bit`) under SchemaOnly
against the real MAGIQ SQL Server — the matrix keys on those. Confirm with one verify run against
training. No .NET SDK on the bridge VM, so the real `dotnet build` is Chase's.

**Status:** Implemented on `feature/34575-schema-verification` (story 34575, tasks 34576–34580; under
Feature 34122 *MAGIQ Documents Integration*, tagged `deferred-post-mvp`); `tsc -b` clean, C# validated by
balance/reference checks. Pending Chase's build/PR/merge.

## [2026-07-31] System settings moved to a DB-backed store with a live admin editor (Story 34590)

**Context:** Three operational settings still lived in `appsettings.json` — `DeletableFolderAcronyms`
(the Step-6 pre-lock list), `Queries:CommandTimeoutSeconds`, and `TicketHeartbeat:IntervalSeconds` — and
each was read **once at startup** (the acronym rule comment even said "restart to change, like the admin
allowlist"). Chase asked to manage them the same way as the configurable SQL queries (Story 34550):
defaults in code, overridable through the admin UI, applied without a restart. Two design points were
settled interactively: **apply live (no restart)**, and — since only the query timeout is genuinely
query-related — a **separate System Settings page**, not a section on the Configured Queries screen.

**Decision:**

1. **Mirror the ConfiguredQuery store, don't overload it.** New `dbo.ConfiguredSetting` table
   (`SettingKey` PK, `Value`, `UpdatedAtUtc`, `UpdatedBy`, `RowVersion`) — migration
   `0002_configured_settings.sql`, forward-only after the released 0001 baseline. `IConfiguredSettingStore`
   / `ConfiguredSettingStore` is a singleton with a warm value cache; unlike the lazy query cache it is
   **warmed at startup** (`SeedDefaultsAsync`) and exposes a synchronous `GetCachedValue` so the per-folder
   acronym hot path needs no `await`. The SQL stays in `ConfiguredQuery` (it has a `Sql` column + schema
   verification coupling); scalar/list settings get their own table so neither concept is contorted.

2. **Typed contract in code, values in the DB.** `SettingDefinitions` holds each setting's kind
   (`Integer` | `StringList`), seeded default (the old appsettings values — the 22 acronyms, 120, 300),
   and — for integers — the valid range (timeout 1–3600; heartbeat 30–1199, still under the 20-minute
   sliding window). The `ISystemSettings` accessor parses/clamps and memoizes the acronym list against its
   raw string (reference-stable while unchanged). Update validation is definition-driven; list values are
   normalized (trim, de-dupe, one-per-line); an empty acronym list is legitimately "match nothing".

3. **Consumers read live.** `DapperMagiqQueryExecutor` and `MagiqSchemaProbe` read the timeout per query;
   `LiveFolderAcronymRule` wraps the pure `FolderAcronymRule` and rebuilds it only when the list actually
   changes (so an edit applies on the next identification run); `TicketHeartbeatService` drops its fixed
   `PeriodicTimer` for a `Task.Delay` loop that re-reads the interval each tick. `QueriesOptions` and
   `TicketHeartbeatOptions` (and the three appsettings sections) are deleted.

4. **Surface — a separate admin screen, vanilla stack.** `GET/GET{key}/PUT{key} /api/v1/admin/settings`
   on the shared `DlcEndpoint` base (Results not exceptions, `Version(1)`, `api/`-less route,
   admin-allowlist gated, operator from `ICurrentOperator` never the body), optimistic-concurrency via a
   base64 rowversion. A new React **System Settings** page (`/admin/settings`) renders a NumberInput for
   integers and a one-per-line Textarea for the acronyms, with reset-to-default and the same
   load-edit-save-with-concurrency flow as the Configured Queries page.

**Rationale:** Reproduces exactly the query-store pattern Chase liked, so the mechanism (seed-if-absent,
never overwrite edits, audit + rowversion, admin edit) is already familiar and tested. Living values in the
DB + a warm cache is what makes "no restart" honest without threading options reloads through singletons.
Keeping the SQL and the settings in separate tables preserves the schema-verification design and keeps each
store's validation simple.

**Residual risk / to confirm:** no .NET SDK on the bridge VM, so `dotnet build` + the xUnit run are Chase's
(the C# was validated by balance/reference/using checks; `tsc -b` clean). The heartbeat loop now uses
`Task.Delay(interval)` re-read each tick — an interval change applies on the *next* cycle, not mid-wait
(acceptable; the max is 1199s).

**Status:** Implemented in the `DocumentLifecycleCleaner` tree for **Story 34590** (branch
`feature/34590-system-settings-store`, tagged `document-lifecycle-cleaner`; alongside Story 34550 under Epic
34120). Pending Chase's branch/build/commit/PR/merge.

## [2026-08-01] Terminal-run cleanup — tiered soft-delete with archival rollback (Story 34591)

**Context:** Abandoning a run leaves it terminal but does nothing else — partial destructive work stays
as-is, and there was no way to remove a dead run from the dashboard or undo a half-finished archival.
Chase asked for a gated cleanup: delete a run that changed nothing; roll back (and then delete) a run
that only moved documents to the archive; refuse to delete a run that reached the irreversible
folder-delete/purge, since history must be kept. Applies to **Abandoned and Cancelled** runs.

**Decision:**

1. **Tier by persisted effect, not step number.** Step 8 straddles the Review→Archival boundary, so
   `CurrentStep` is unreliable. `CleanupRun.DescribeDeletability(movedCount)` derives the tier from state:
   **Irreversible** if `CurrentPhase == Cleanup`; **Reversible** if `Archival` and (`CreatedArchiveLibrary`
   or `movedCount > 0`); **NoChanges** otherwise (incl. an archival that failed at Step 8 before
   `CreateDomain`). A new `CreatedArchiveLibrary` flag is set in archival's create branch so rollback can
   tell a run-created library from an operator-chosen existing one.

2. **Rollback is the reverse of Step 9 + a teardown.** For each `Moved` document, `Move` it from its
   archive location (`/{library}[/subfolder]/{leaf}`) back to its original folder (`parent(DocumentPath)`);
   the originals still exist because folder deletion is Step 10. Then **fully restore**: if the run created
   the library, `DeleteDomain` + targeted recycle-bin purge (the Step 11 purge logic, extracted to a shared
   `PurgeArchiveLibraryAsync`); an existing library is left untouched (archival never created a subfolder in
   that path). All move-backs succeed ⇒ `RollbackStatus = Succeeded` (deletable); any failure ⇒ `Failed`
   (non-deletable, re-runnable). Docs that go back are marked `MoveStatus.RolledBack`.

3. **Delete is soft.** `DeletedAtUtc`/`DeletedBy` stamp the run; `ListAsync` and the summary counts filter
   `DeletedAtUtc IS NULL`, so it drops off the dashboard while the row + phase log stay for audit. `GetAsync`
   still returns it (details/audit reachable).

4. **Ticket for rollback = the operator's session (UI) ticket.** A terminal run's process ticket is no
   longer heartbeated and will be expired, so the rollback endpoint passes `ICurrentOperator.UiTicket` into
   the Hangfire job. Expiry mid-rollback fails the job to `RollbackStatus = Failed`, re-runnable after a
   fresh login — the same expiry model as the forward pipeline. No stored credentials. (The ticket travels
   in the job args, like the persisted process ticket already does.)

5. **Surface — vanilla endpoints + Job Details controls.** `GET /runs/{id}/deletability`,
   `POST /runs/{id}/rollback` (body-less; `.Accepts<RunActionRequest>()` so it doesn't 415),
   `DELETE /runs/{id}` (request-less, `Route<Guid>`). A `RunCleanupActions` panel on the Job Details view
   shows Delete/Roll-back gated by tier, with destructive-action confirms; it polls deletability while a
   rollback runs. Migration `0003` adds the four columns + `MoveStatus.RolledBack`.

**Residual risk / to confirm:** (a) name collisions — two candidate docs with the same leaf name moved into
one archive folder are ambiguous to reverse (a pre-existing hazard of the forward move; flag for the doc
register/naming review). (b) `dotnet build` + xUnit are Chase's (no SDK on the bridge VM); `tsc -b` clean.
(c) Confirm the operator UI ticket authorises `Move`/`DeleteDomain`/`PurgeRecycleBinItem` against training
(same class as the ADR-011/34525 checks).

**Status:** Implemented in the `DocumentLifecycleCleaner` tree for **Story 34591** (branch
`feature/34591-abandoned-run-rollback-delete`, under Epic 34120). Pending Chase's branch/build/commit/PR/merge.

### [2026-08-01] Addendum (34591) — per-item failure reasons + duplicate-on-move

Per-item errors are now symmetric. **Documents** already persisted `CleanupRunDocument.FailureReason`
(set on any move failure, forward or rollback); **folders** previously only got `Status = Failed` with the
error going to the live progress feed + phase log. Migration `0004` adds `CleanupRunFolder.FailureReason`
(and `FolderStatusUpdate`/`FolderItem` carry it), so a folder that fails to delete now shows its error next
to the row like a document does — exposed via `GET /runs/{id}/folders`.

**Duplicate on move:** no special handling — a name collision when moving into the archive (or back on
rollback) comes back as a MAGIQ business failure, which is already recorded as a per-item failure with the
MAGIQ error text (document left `Failed`/`Moved`, folder left `Failed`), not retried or auto-renamed. That
is the intended "just log it as a failure" behaviour.

UI: a **Folder cleanup outcomes** table (`CleanupOutcomesPanel`) on the Job Details view lists every folder the run attempted to delete (Step 10) with its final status and, for a failure, the persisted `FailureReason` — self-hides until there is a delete outcome, and polls while the run is active. This is the post-cleanup surface for the per-folder errors.

## [2026-08-01] MAGIQ Documents connection string → encrypted setting (Story 34592)

**Context:** The read-only `MagiqDocumentsDatabase` connection string sat in `appsettings.json`. Chase
asked to move it into the DB/settings and encrypt it "so it can't be hacked". Flagged the honest limit
up front: the app must decrypt at runtime, so this is **encryption at rest** (defends a stolen DB backup /
DBA browsing), not protection against a compromised host or the key ring; and the current value uses
`Trusted_Connection` (Windows auth) so it holds no password anyway. Two decisions taken interactively:
**ASP.NET Core Data Protection** for encryption, and a **hard cut** (no appsettings fallback — set via the
admin screen before first run). `AppDatabase` stays in config (it's the bootstrap DB the settings live in).

**Decision:**

1. **New `SettingKind.Secret`.** The connection string becomes the `MagiqDocumentsConnectionString`
   setting (seeded empty). Secrets are **write-only** in the admin API: list/get mask the value and expose
   only `IsSecret`/`IsSet`; update validates non-empty, encrypts, and stores ciphertext. The frontend
   renders a password field showing configured/not-configured.

2. **Encryption via Data Protection.** `ISecretProtector` / `DataProtectionSecretProtector` wraps an
   `IDataProtector` (purpose-scoped) with a `dpapi:v1:` marker so a stored value is recognisably encrypted
   and decrypt failures (wrong/rotated key, tampering) degrade to "unset" rather than crashing. Key ring
   persisted to `DataProtection:KeyRingPath` (default `<contentRoot>/keys`) and `ProtectKeysWithDpapi()` on
   Windows; under Docker it must be a secured persistent volume. **Losing the key ring makes secrets
   undecryptable** — documented.

3. **Read path.** `IMagiqConnectionStringProvider` reads the setting store's warm cache and decrypts;
   `MagiqDbConnectionFactory` resolves it per `Create()` (so an admin edit applies with no restart) and
   throws a clear "set it on the admin screen" error when unset — never crashing boot. `MagiqDocumentsDatabase`
   is removed from `ConnectionStringsOptions`, `appsettings*.json` and `.env.example`.

**Residual risk / to confirm:** encryption-at-rest scope as above; the key ring is the real secret to
protect (secure the folder / Docker volume; back it up with the DB). `dotnet build` + xUnit are Chase's
(no SDK on the bridge VM); `tsc -b` clean. Confirm the DataProtection key folder is writable by the IIS
app-pool identity in the target environment.

**Status:** Implemented in the `DocumentLifecycleCleaner` tree for **Story 34592** (branch
`feature/34592-magiq-connstring-secret`, under Epic 34120). No migration needed — the setting seeds into the
existing `dbo.ConfiguredSetting` at startup. Pending Chase's branch/build/commit/PR/merge.

## [2026-08-01] MAGIQ SOAP endpoint + transport tuning → settings store (Story 34593)

**Context:** Following 34592 (connection string → encrypted setting), Chase asked to also move the
`MagiqDocuments` `Endpoint`, `TimeoutSeconds`, `MaxRetries` and `RetryBaseDelayMilliseconds` into the
DB/settings and UI. `AdminAllowlist` deliberately stays in config (authorisation bootstrap).

**Decision:**

1. **Endpoint keeps a config bootstrap — it can't be hard-cut.** Login authenticates against the endpoint,
   so an unset endpoint at first boot would deadlock sign-in (can't log in to set it). So the endpoint is a
   new `SettingKind.Url` setting **seeded from `MagiqDocuments:Endpoint` on first boot** (the Program.cs
   seed overrides the endpoint default with the config value). `appsettings` keeps `MagiqDocuments:Endpoint`
   as the documented bootstrap seed; after first boot the DB row is the source of truth. This differs from
   the connection-string hard-cut (which login doesn't need) — an accepted, deliberate divergence.

2. **Timeout/retries move fully.** Three Integer settings (`MagiqTimeoutSeconds` 1–600/100,
   `MagiqMaxRetries` 0–10/3, `MagiqRetryBaseDelayMilliseconds` 0–60000/500), seeded with the current code
   defaults and removed from `appsettings`/`.env`. `MagiqDocumentsOptions` keeps only `AdminAllowlist`.

3. **Live via the typed client's transient lifetime.** The typed `HttpClient`'s configure delegate reads
   the endpoint + timeout from `ISystemSettings` per resolution (the typed client is transient), and
   `MagiqSoapClient` reads the retry tuning from settings — so an admin edit applies on the next SOAP call,
   no restart. An unset endpoint leaves `BaseAddress` null; `MagiqSoapClient` guards it and returns a clean
   "set it on the admin screen" failure instead of throwing.

4. **URL validation.** The endpoint setting validates as an absolute http/https URL. New `SettingKind.Url`
   renders as a single-line text field in the admin screen.

**Residual risk / to confirm:** moving the SOAP endpoint to a DB setting means an admin can repoint the app
at any URL (already true via config; admin-only, low delta). `dotnet build` + xUnit are Chase's (no SDK on
the bridge VM); `tsc -b` clean.

**Status:** Implemented in the `DocumentLifecycleCleaner` tree for **Story 34593** (branch
`feature/34593-magiq-soap-settings`, under Epic 34120). No migration — settings seed into the existing
`dbo.ConfiguredSetting` at startup. Pending Chase's branch/build/commit/PR/merge. (ADO create timed out
mid-request; confirm the 34593 story exists / re-create if not.)

## [2026-08-01] First-run setup / onboarding — app-DB stored externally, everything else in the DB (Story TBD)

**Context:** Chase asked for a setup process that onboards all application settings: on first boot the app
prompts for the **application-database connection string** (the only thing stored externally); everything
else lives in the DB and is managed in the UI. The app-DB string is stored **mostly plaintext except the
username/password**, which are encrypted. Chosen (interactively): setup surface **open until configured**,
activate **live without a restart**, **full guided wizard**.

**Decision (delivered as sequenced slices):**

1. **External file + partial credential encryption.** `ConnectionStringCredentials` encrypts only
   `User ID`/`Password` (Data Protection, `ENC(…)` tokens) leaving the rest readable; Windows-auth strings
   have no creds. `IAppConnectionStringProvider`/`AppConnectionStringProvider` read the bootstrap file
   (`App_Data/appdb.json`, overridable via `Bootstrap:ConnectionFilePath`) with a config fallback;
   `AppDbConnectionFactory` + `DatabaseMigrator` resolve through it.

2. **Two-mode startup + gate.** `AppConnectionStringProvider.HasConnectionString` picks the mode at boot.
   In **setup mode** the app doesn't touch the DB: migrations/seed, Hangfire (+dashboard) and the
   resume/heartbeat hosted services are skipped. Anonymous endpoints `GET /setup/status`,
   `POST /setup/test-connection`, `POST /setup/app-database`; the save endpoint tests the connection, writes
   the file, and runs migrations+seed live (`DatabaseBootstrapper`). Mutating setup endpoints refuse (409)
   once configured — bounding the open surface to the install window (accepted trade-off).

3. **Live activation (no restart).** After save, `HangfireRuntime` starts Hangfire storage+server+client
   in-process so runs can be queued/processed immediately. Scoped to the setup path only — the normal
   configured-at-boot path keeps the standard `AddHangfire`/`AddHangfireServer` wiring **unchanged**.

4. **Guided wizard UI.** `GET /setup/status` gates the SPA (`App.tsx`); `FirstRunSetupPage` collects/tests/
   saves the app-DB string, then hands off to sign-in + System Settings for the rest.

**Residual risk / to confirm (flagged):**
- **In-process Hangfire start (slice 3) needs real IIS/Docker verification** — Hangfire isn't designed to be
  configured after startup; the programmatic storage/activator/server path is unverified here.
- On the no-restart first-run path, the **Hangfire dashboard and the resume/heartbeat hosted services do not
  come up until the next restart** (a run started in that first session isn't heartbeated). Acceptable for
  first-run; normal restarts bring them up.
- "Open until configured" is unauthenticated during install — mitigated by the once-configured 409 gate.
- The "full guided wizard" currently covers the app-DB step (the only setup endpoint); MAGIQ DB/endpoint/etc.
  are finished post-login in System Settings. A fully unauthenticated multi-step wizard would need setup
  endpoints for those + moving the allowlist out of config (a further slice).
- `dotnet build` + xUnit and `tsc -b` are Chase's (no SDK on the bridge VM). ADO disconnected — story TBD.

**Status:** Slices 1–4 implemented in the `DocumentLifecycleCleaner` tree (branch
`feature/setup-onboarding`, under Epic 34120). Pending Chase's branch/build/commit/PR/merge + the slice-3
Hangfire verification.

### [2026-08-01] Setup activation — switched from in-process Hangfire start to a self-restart

Replaced slice 3's risky in-process Hangfire activation (`HangfireRuntime`, now removed) with a
**forced self-restart** after setup — Chase's call, and the more robust option. `/setup/app-database`
now: tests the connection → saves the file → runs migrations + seed to validate the DB is usable
(rolling the file back on failure, so no boot-fail loop) → returns success → schedules
`IHostApplicationLifetime.StopApplication()`. The host brings the process back up in configured mode with
the **standard, fully-tested** `AddHangfire`/`AddHangfireServer` wiring — no unverified Hangfire code.

Detection: the old (setup-mode) process reports `configured = true` the instant the file is saved, so the
SPA can't tell the restart happened from that flag. `GET /setup/status` now returns a per-process
`InstanceId` (regenerated each start); the wizard records the initial id after save and polls until a
**new** id answers, then continues to sign-in. A ~90s timeout shows a "restart manually" message.

**Requires a host that auto-restarts a stopped worker:** IIS in-process (restarts on next request), Docker
with a restart policy, or a Windows service / systemd. Bare `dotnet run` won't auto-restart — the wizard's
timeout path covers that (operator restarts, reloads). This supersedes the earlier "live, no restart"
decision for the background pipeline specifically; config/settings still activate live before the restart.

### [2026-08-01] Setup onboarding — final slice: unauthenticated MAGIQ-access step + allowlist to the DB

Made first-run setup fully self-contained: a fresh install can reach a working sign-in with **no config
file and no restart beyond the database one**. Two changes.

1. **Admin allowlist moved out of config into the settings store.** It is now the `AdminAllowlist`
   system setting (`SettingKind.StringList`), seeded from `MagiqDocuments:AdminAllowlist` on first boot so
   existing config-driven deployments keep working. `AdminAllowlist` (the `IAdminAllowlist` impl) reads it
   **live** from the store's warm cache on every check instead of an `IOptions` snapshot — so adding/removing
   an operator now applies on the next request, no restart (supersedes ADR-006's "restart to change the
   allowlist"). Fail-closed unchanged: an empty list denies everyone. `MagiqDocumentsOptions` is now just the
   section-name constant (nothing binds it); its `AddOptions` registration was removed.

2. **Second wizard phase for the MAGIQ access essentials.** After the database restart the app is in
   configured mode but not yet loginable if the endpoint/allowlist weren't seeded from config. So setup is
   now two phases and `GET /setup/status` reports both (`DatabaseConfigured`, `MagiqConfigured`) plus the
   overall `Configured = both`. New anonymous endpoints — `GET/POST /setup/magiq` — read/write the MAGIQ SOAP
   endpoint + allowlist during first-run, **refused (409) once the DB phase is incomplete or setup is already
   complete** (same once-configured gate as `/setup/app-database`, so it's not an open settings-write
   surface). Writes go through `SetupSettingWriter` (reads the seeded row's rowversion → updates through the
   store's normal optimistic-concurrency path, no operator token). Both values apply live (the SOAP client is
   transient; the allowlist reads live), so this **completes setup with no second restart**.

Scope kept deliberately tight: the wizard covers only what **login** needs (endpoint + allowlist). The MAGIQ
*database* connection string (a secret, needed for the first cull, not for login) is still set post-login in
System Settings — keeps the unauthenticated surface to non-secret login-bootstrap values. The SPA gate
(`App.tsx`) now shows the wizard until `Configured`; `FirstRunSetupPage` picks its start phase from status
(DB up but MAGIQ unset → resume at the MAGIQ step) and, after the restart, advances DB→MAGIQ→done by
watching for the new `InstanceId`.

Tests: `AdminAllowlist`/`LoginHandler` allowlist helpers rebuilt on the fake settings store;
`SetupMagiqStateTests` (the two-signal completeness rule) and `SetupSettingWriterTests` (token-free write +
missing-row throw) added. `dotnet build`/xUnit + `tsc -b` remain Chase's (no SDK on the bridge VM).

**Status:** Slice 5 implemented in the `DocumentLifecycleCleaner` tree (branch `feature/setup-onboarding`,
Epic 34120). Pending Chase's branch/build/commit/PR/merge.

### [2026-08-02] Admin UI reorg — settings by section + single diff-save; two settings to the Queries page

Frontend-only (the `/admin/settings` API is generic, keyed by setting, so no backend change). Three changes:

- **System Settings** dropped the NavLink master-detail (one setting at a time) for a single page of
  **sections** — MAGIQ connection, SOAP transport, process ticket, access control — with every field visible
  at once and **one Save**. Save diffs each field against its loaded value and writes **only what changed**,
  each through its own optimistic-concurrency row version (partial success is reported; a secret is "changed"
  only when a new value is typed).
- **Deletable folder acronyms** and **Query command timeout (seconds)** moved off System Settings onto the
  **Configured Queries** page (they tune the identification pass), in a "Query settings" section with the same
  single diff-save.
- Extracted a shared `admin/settingsEditing.tsx` — `useConfiguredSettingsEditor(keys)` (load/draft/dirty/
  save-only-changed), the `SettingField` renderer (by kind), the key constants and the section layout — so
  both pages share one implementation and the split is just which keys each page owns.

No settings were added/removed and `SettingKeys.All` is unchanged, so seeding/consumers are untouched;
`tsc -b`/build is Chase's (the bridge VM can't finish a cold typecheck in-session).

### [2026-08-02] Admin UI follow-ups — MAGIQ DB test-connection + example, and single-save on Queries

- **Test connection for the MAGIQ Documents database.** New authenticated `POST
  /admin/settings/magiq-database/test-connection` opens the connection and returns `{ ok, error }` (always
  200; a failed connect is in the body). It tests the candidate string in the body when supplied, else the
  **stored** value (resolved/decrypted server-side via `IMagiqConnectionStringProvider`, since the secret is
  never sent to the client). The open logic moved to a shared `Common/SqlConnectionTester`; the setup tester
  now delegates to it. The System Settings MAGIQ-connection field gains a **Test connection** button (tests
  the typed draft, or the stored value when blank) and an **example connection string** help line (SQL-auth
  and Windows-auth forms). `SettingField` grew optional `onTest`/`example` props to carry this generically.
- **Configured Queries now saves like System Settings.** Dropped the master-detail + per-query Save for a
  single page showing every query at once, with **one Save** that writes only the changed queries **and** the
  two query-settings (acronyms, command timeout) together — each optimistic-concurrency checked via its own
  row version. New `useConfiguredQueriesEditor` mirrors `useConfiguredSettingsEditor`; the page orchestrates
  both under one button.

Frontend + one additive backend endpoint; no schema or settings-shape change. `tsc -b`/build is Chase's.

### [2026-08-02] Fix — folder-path resolution batched under SQL Server's 2100-parameter cap

Identification Step 4/5 failed on a real-sized facility with *"The incoming request has too many parameters.
The server supports a maximum of 2100 parameters."* Root cause: `MagiqDocumentQueries.GetFolderPathsAsync`
bound the whole candidate-folder id set as `new { folderIds }`, and Dapper expands `IN @folderIds` to one
SQL parameter per id — so >2100 folders overflowed the cap. (It surfaced as Step 4 because `CurrentStep` is
still 4 when the Step-5 path query runs.)

Fix: resolve paths in batches of **500** ids (`folderIds.Chunk`), concatenating the results — ids are
already distinct and each lands in one batch, so the merged result equals a single query's. 500 leaves
headroom even if an operator's FolderPaths SQL references `@folderIds` more than once (each reference is
expanded) and matches the pipeline's identification batch size. The row-by-row `AddBatchAsync` inserts were
already safe (Dapper runs the parameterised INSERT once per row, not a multi-row VALUES). Regression test:
`MagiqDocumentQueriesTests` (1201 ids → 3 batches of 500/500/201, none over the cap, all ids resolved).

## [2026-08-04] Acronym folders are pre-selected and operator-overridable (supersedes the pre-lock rule)

**Context:** The spec + CLAUDE.md stated deletable-acronym folders are "pre-locked in the UI — NATA cannot override them" (enforced by `CleanupRunFolder.IsLocked`, an SQL guard, and a `422 FolderIsLocked` on submit). Operators occasionally need to keep an individual acronym-matched folder.

**Decision:** Rename the concept from "locked" to **pre-selected** (`IsLocked` → `IsPreSelected`; column renamed and folded into the consolidated baseline migration). Acronym-matched folders stay selected for deletion by default, but the operator can **deliberately override** (deselect) an individual folder via a per-row control in the Step 6 review. The submit handler no longer returns `422 FolderIsLocked`; every non-protected selection is honoured. Protection (Rule 2) is unchanged and remains **absolute** — a protected folder is never selectable/deletable, guarded in code and in SQL (`Status <> 'Protected'`).

**Rationale:** The hard lock was a convenience guard, not the safety rule; protection (Rule 2) is the real "must not delete" guarantee and stays absolute. Making the pre-selection overridable — deliberately, per row — gives operators the control they need without weakening protection.

**Status:** Implemented (backend + review UI). Spec text ("pre-locked… cannot override") to be updated to match.

---

## [2026-08-04] Re-run identification for an unconfirmed in-review run

**Context:** A run paused at the folder review (`AwaitingInput` / `ReviewSelection`, before the Step 7 confirmation) had no way to refresh its candidate set — e.g. after source documents changed, or to restart the review clean. The single-active-run rule blocks creating a second run; cancel + recreate loses the run's cutoff/library and leaves a cancelled run behind.

**Decision:** Add a **re-run identification** capability for an unconfirmed in-review run: a guarded state transition `CleanupRun.Reidentify()` (`AwaitingInput` + `ReviewSelection` → `Running` + `Identification`, Step 1) and `POST /runs/{runId}/reidentify`, which re-enqueues the identification phase. Identification's idempotent body clears and rebuilds the run's candidate documents/folders for the same cutoff + source library. The re-scan **discards the operator's current review selections** (the candidate set is rebuilt), so the UI gates it behind a confirmation. Guards: `409 RunNotInReview` (any other state, including the Step 11 purge pause), `404 RunNotFound`. A `Reset` phase-log entry records the re-run.

**Rationale:** Reuses the existing idempotent identification job (delete-all + re-insert) rather than a complex selection-preserving merge; a re-scan legitimately invalidates prior selections since the folder set may change. Keeps the same run (id, cutoff, library) instead of forcing cancel + recreate.

**Status:** Implemented (domain transition, endpoint, review-screen button + confirm, unit tests). No spec conflict — new capability.

---

## [2026-08-05] Folder delete-rule handling — reactive lift/revert + review tracking

**Context:** MAGIQ folders carry per-folder rules, two of which block deletion: `DISALLOWDOCUMENTDELETE` (documents in the folder) and `DISALLOWFOLDERDELETE` (child folders of the folder; the **parent** governs a child's deletion). A `Move` is internally a copy + delete, so archiving a document out of a folder whose `DISALLOWDOCUMENTDELETE` is set fails the delete-half and the whole move errors (nothing moves). Likewise a Step 10 `DeleteFolder` fails when the parent disallows folder deletes. Options ranged from pre-flight detection/skip, through leaving the docs in place, to temporarily lifting the rule. Chase chose: **track the restrictions for operator visibility, and reactively lift-and-revert the rule at execution time** — reactive (not pre-flight) specifically so a rule changed *mid-run* is still honoured, since the guard reads the live rule at the moment of failure rather than a stale identification snapshot.

**Decision:**

1. **Reactive rule guard (execution, authoritative).** New `IFolderDeleteRuleGuard` / `FolderDeleteRuleGuard`. When a Step 9 `Move` or Step 10 `DeleteFolder` fails, the guard calls `GetFolderRules` on the governing folder; if the relevant rule (`DocumentDeletes` for a move, on the document's own folder; `FolderDeletes` for a folder delete, on the **parent**) currently reads `disallows`, it `SetFolderRules` with just that one rule flipped to `allows` (`ApplyToTree=false`), retries the operation once, then — in a `finally` with a non-cancellable token — restores the captured original rules **verbatim**. If the rule already permits the action, or the rules can't be read, or the relax is rejected, the guard changes nothing and returns the original error. A failed *restore* is logged as an error (folder left permissive → manual follow-up).

2. **New SOAP primitives.** `GetFolderRulesAsync` / `SetFolderRulesAsync` on `IMagiqSoapClient` (infoRouter `GetFolderRules`/`SetFolderRules`), plus a `FolderRuleSet` type that preserves the exact `<Rules>` XML and flips a single rule. `xmlRules` is the escaped `<Rules>…</Rules>` fragment; rule `Value` is `allows`/`disallows`.

3. **Review tracking (informational).** `CandidateDocuments` gains `DocumentDeleteBlocked`; `CandidateFolders` gains `DocumentDeleteBlocked` (own rule) + `FolderDeleteBlocked` (parent's rule, via a join on `PARENTID`). Flowed through the records, persisted on `CleanupRunFolder`/`CleanupRunDocument` (migration `0002`), surfaced in the Step 6 review as a "Delete-locked" badge + filter chip. These flags are a **snapshot, not the execution source of truth** — the guard always re-reads live. They are deliberately **not** part of the hard schema-verification contract (they default to `false` when a customised query omits them), so existing operator queries keep verifying.

**Rationale:** Reading the live rule at failure time is the only way to stay correct when someone edits a folder's rules during a run; a pre-flight snapshot could lift the wrong set. Reverting verbatim (not reconstructing) guarantees no other rule is disturbed. Scoped to the forward Steps 9/10 only (rollback's move-back/folder-delete run against the run-created archive, which we own with default rules).

**Residual risk:** a process crash between relax and revert leaves that one folder's rule permissive until the next run touches it — logged loudly; crash-recovery not built (accepted, low-probability, single-folder blast radius).

**Follow-ups:** confirm the exact `Get/SetFolderRules` path format against training (Story 34525 pattern — currently domain-rooted, no leading slash, matching `GetFolders`); update `verify-magiq-queries.sql` + `SQL-QUERY-DESIGN-34547.md` §1/§3 with the new columns (§1/§3 done); dev-spec SOAP contract + component map to add the two ops and the guard.

**Status:** Implemented in the product tree (SOAP client + `FolderRuleSet`, guard + Steps 9/10 wiring, DI, SQL seed + design doc, records/persistence/migration 0002, review DTO + SPA badge/chip, unit tests for `FolderRuleSet` and the guard). Pending Chase: branch/commit, `dotnet build` + `npm run build`, and the training path-format confirmation. Two branches suggested (guard; review-tracking) — see below.

---

## [2026-08-05] Folder-rule handling — extend to the rollback move-back (NewDocuments)

**Context:** The entry above scoped the reactive guard to the forward Steps 9/10 and left the Tier 2 **rollback** move-back unguarded, reasoning it only touches the run-created archive. That is wrong for the **destination**: a rollback moves a document from the archive back to its **original** folder, and a `Move` is a copy + delete, so the copy-half creates a *new document* in that original folder — which the folder's `NewDocuments` rule can block. The original folders are NATA's own (not the archive we created), so the rule genuinely can be `disallows`.

**Decision:** Extend the guard to the rollback move-back (`MoveDocumentsBackAsync`): on a failed move-back, relax **`NewDocuments`** on the document's original folder (`ParentPath(DocumentPath)`), retry once, restore. The guard itself is unchanged — it is rule-agnostic. The rule enum is renamed `FolderDeleteRule` → **`FolderRule`** and gains a `NewDocuments` member, since it now covers the copy-half (a non-delete rule) as well as the delete-half. Forward handling is unchanged (`DocumentDeletes` on the source for Step 9; `FolderDeletes` on the parent for Step 10).

**Rationale:** Same reactive lift/revert with the same safety (live read at failure, verbatim restore in a `finally`). Only the copy-half of the move-back needs handling — its delete-half removes from the archive folder we created (default rules). The rollback's *run-created-folder cleanup* is still unguarded on purpose (those are archive folders we own).

**Status:** Implemented (enum rename + `NewDocuments`, guard wired into `MoveDocumentsBackAsync`, executor-level wiring tests for all three sites — Step 9, Step 10, rollback). Supersedes the "forward Steps 9/10 only" scoping note above. Pending Chase: build/PR.

---

## [2026-08-05] Archive library treated as open / unrestricted folder rules

**Context:** The rollback also deletes the archive folders a run created during Step 9 (`RemoveCreatedArchiveFoldersAsync`), and Step 9 creates that archive folder structure. Those archive-side `DeleteFolder`/`CreateFolder` calls are **not** wrapped in the reactive rule guard, unlike the operations on NATA's own folders. Question was whether that is a gap.

**Decision:** For now, treat the **archive library as completely open** — unrestricted folder rules. The guard is scoped to operations on the customer's own source/original folders (`DocumentDeletes` on the source, `FolderDeletes` on the parent, `NewDocuments` on the original folder during rollback). Archive-side operations (create the archive folder tree; delete run-created archive folders on rollback) are left unguarded on the assumption that the run-created library and its folders carry permissive defaults.

**Rationale:** The run creates the archive library itself, so its rules are ours and expected to allow creates/deletes; guarding them pre-emptively adds complexity for a case that shouldn't arise. Recorded as an explicit assumption (ADR-004 amendment) so it's a known, revisitable decision rather than an oversight.

**Revisit if:** an administrator applies restrictive rules to the archive library, or the Step 8 "choose an existing library" path targets a library that already carries rules — then the archive-side create/delete would need the same guard. `RemoveCreatedArchiveFoldersAsync` also currently has no unit coverage (the rollback wiring test exercises the run-created-library teardown branch instead); a test for that branch is a separate, open follow-up.

**Status:** Documented (ADR-004 amendment). No code change — captures the current, deliberate scope.

---

## [2026-08-05] Name Normalization phase — work around the SOAP double-space bug

**Context:** The MAGIQ Documents desktop UI lets a user create a document or folder whose name contains a run of consecutive whitespace (e.g. a double space), but the SOAP web service **collapses and trims whitespace** in names on `CreateFolder`/`Move`. So the service cannot create or move an item whose name — or whose containing folder path, at any level — holds a double space: the target it would produce never matches the doubled-whitespace source, and the archival `Move` errors (nothing moves). `MagiqPath.Normalize` already collapses SQL-derived paths to the service's single-space view so *destinations* line up (see its usage in `RunPhaseExecutor.BuildDestinationPath`/`BuildLibraryRootPath`), but the **source** items physically retain their doubled whitespace in the repository, so the move still fails. Chase asked to work around the bug by renaming the offending source items before the move.

**Decision:**

1. **New pipeline phase — Name Normalization — inserted before archival.** A new `RunPhase.Normalization` runs as its own Hangfire job (chaining to archival on success), between operator confirmation (Step 7) and the archival move. It is a new **Step 8**; the archival/cleanup steps renumber in the spec (Archival → Steps 9–10, Cleanup → Steps 11–12). The as-built code keeps the pre-insertion numbering (Archival 8–9, Cleanup 10–11) until this phase is implemented — flagged in the spec/ADR-002/ADR-004 so the divergence is explicit, not an oversight.

2. **What it does.** From the run's candidate documents and their resolved paths, rename in the **source** repository every item with a doubled-whitespace run, collapsing each run to a single space: **folder levels first, top-down (ancestors before descendants)** via `UpdateFolderProperties`(`Path`, `NewFolderName`) so descendant paths stay resolvable, then **documents** via `UpdateDocumentProperties`(`Path`, `NewDocumentName`). Items already clean are skipped, so the phase is idempotent/resume-safe and batches progress like the Step 10 move. Only when normalization completes does the pipeline chain to archival.

3. **Every rename is recorded.** Item type (folder/document), original path/name, new normalized name, operator/process ticket, and timestamp are persisted against the run (a new `CleanupRunRename`-style store) and written to `CleanupRunPhaseLog`. The record is the point of the phase — a permanent audit of the changes made to NATA's live repository.

4. **Audit lock — a normalized run can never be deleted, only archived (spec Rule 7).** Normalization is the first phase that **mutates** the customer's source repository, and a rollback does **not** un-rename (it only returns moved documents and tears down a run-created archive). So once a run has entered the Normalization phase it is permanently an audit: `CleanupRun.DescribeDeletability` must never return `CanDelete` for it — the tier can be `Reversible`/`Irreversible` but never `NoChanges` — regardless of how far it then progressed or whether its moves were later rolled back. It may be archived for the record; the run row and its rename log are retained.

**Rationale:** Renaming the source in place is the minimal change that makes the existing `Move` succeed, versus alternatives (skip-and-report the affected items, or a bespoke copy that recreates a clean name — both leave source data behind or duplicate the move logic). Doing folder levels top-down keeps paths resolvable through the pass. Recording every rename and locking the run as an audit are non-negotiable for a records-management product: the tool has altered NATA's live documents/folders, and that history must survive.

**To confirm at integration (same `xsd:any`/behaviour class as ADR-011 / Story 34525):** the exact path form `UpdateFolderProperties`/`UpdateDocumentProperties` accept to address a *still-doubled* source item (does the service resolve the normalized path to the doubled item, or must the raw doubled path be sent?), and the success/response shape of both ops. Confirm against `training.magiqdocuments.com` before the phase ships.

**Follow-ups:** new ADO story + tasks under Epic 34120 (SOAP ops on `IMagiqSoapClient`; the `RunPhase.Normalization` job + chaining; the rename store + migration; deletability audit-lock; UI surfacing of the rename log); `dev-spec.md` (API/data-model/SOAP contract/sequence-flow for the new phase) and `CLAUDE.md`/`delivery-plan.md`/`tasks.md` still to be updated to match. Spec, ADR-002, ADR-004 and `dlc-process-walkthrough.html` updated with this decision.

**Status (2026-08-05): implemented in the product working tree (uncommitted).** The four rename SOAP ops (`GetFolder`/`UpdateFolderProperties`/`GetDocument`/`UpdateDocumentProperties`) were captured against training and recorded in `SOAP-VERIFICATION-34525.md` (Part A addendum 3) — the cardinal finding is that rename is a **read-modify-write** (the Update ops blank `Description`/`UpdateInstructions` unless re-supplied, so each rename first Gets them). Built: the SOAP ops + `FolderProperties`/`DocumentProperties`; `RunPhase.Normalization` (new **Step 8**); `dbo.CleanupRunRename` + `EnteredNormalization` flag (migration `0004`); `ICleanupRunRenameStore`; a pure `RenamePlanner` (detects doubled-whitespace folder levels top-down + documents from the **raw** candidate paths — a new `GetRawCandidateDocumentPathsAsync` returns un-normalized paths); `RunPhaseExecutor.ExecuteNormalizationAsync` (Get→Update pairs preserving metadata, `CleanupRunRename` + `Rename` audit rows, batched/resume-safe); `IRunPipeline.StartNormalization` chaining Normalization→Archival→Cleanup; confirm now enqueues normalization; the deletability **audit-lock** (`DescribeDeletability` never returns `CanDelete` once `EnteredNormalization`). Test fakes + assertions updated.

**Step renumbering (done 2026-08-05).** The archival/cleanup steps are now renumbered so nothing collides with Normalization: **Normalization = Step 8, Archival = Steps 9–10** (create library 9, move 10), **Cleanup = Steps 11–12** (delete empty folders 11, purge 12). Renumbered across `RunPhaseExecutor` (phase-log/progress/audit rows, the purge-ready gate), `PurgeArchiveHandler` (`CurrentStep != 12`), `CleanupRun.PhaseStartStep`, and the affected tests/comments.

**Rename addressing + folder tracking (done 2026-08-05; behaviour confirmed 2026-08-06).** A rename addresses an item by its **exact current name, double spaces included** — **confirmed against training**: `GetFolder`/`GetDocument`/`Move` require the stored name verbatim, and a whitespace-collapsed path does **not** resolve a still-doubled item (the service's collapse is on *creation*, not lookup). So `MagiqSoapClient`'s four rename ops send the path verbatim (leading slash stripped, internal whitespace preserved) via `RawRenamePath`, not the collapsing `NormalizePath`; `RenamePlanner` emits raw paths. Because renaming a folder changes its descendants' paths, `ExecuteNormalizationAsync` processes folders top-down then documents and, after each successful folder rename, **repaths the still-pending descendants** — persisted (`ICleanupRunRenameStore.UpdatePathsAsync`) and in the in-memory work list — so folder tracking stays correct as renames happen at any level. Downstream phases (archival `Move`, cleanup `DeleteFolder`) keep using the run's **normalized** paths — correct **because** normalization has already renamed every source to single-space, so the collapsed path matches the physical item (this also corrects the earlier Story 34527 note, which mis-described the collapse as happening on lookup; see SOAP-VERIFICATION-34525.md). `RenamePlanner` has unit coverage.

**Follow-ups:** a dedicated SPA rename-log panel (renames already appear in the operation audit trail). Verified by house checks (balance/param/enum, all interface implementers, migration order); Chase runs `dotnet build`/`test`.

---

## [2026-08-05] Operation audit trail + before/during/after Document Register (CSV)

**Context:** Chase asked us to (a) verify that every run records all of its operations — creates, moves, deletes, renames, decisions — and decide whether that warrants a dedicated audit feature, and (b) make the Document Register capturable **before** a run and again **after** it, exportable to CSV, so a run reads as *before → during → after*.

**Findings (as-built):** There is exactly one append-only log, `CleanupRunPhaseLog`, and it is **phase-grain** (`Started|Completed|Failed|Reset|Retried|Cancelled` per phase+step). Every object-level outcome is a **mutable status flip**, not an audit event: `CleanupRunDocument.MoveStatus` (persisted per-*batch*, not per-document — accepted edge, 2026-07-28), `CleanupRunFolder.Status`, the `CreatedArchiveLibrary` bit, `CleanupRunArchiveFolder` (rollback bookkeeping only). `DeleteDomain`/`PurgeRecycleBinItem` and the reactive rule-relax/restore guard actions leave no durable per-op record; an operator **override** of a pre-select at Step 6 is only visible as the final boolean. Renames are unbuilt (the separately-specified `CleanupRunRename`, [2026-08-05]). So: no object-level "what happened, when, by whom, with what result" trail — a real gap for a government records tool that mutates NATA's live repository. The Document Register export is on-demand, **not retained** (2026-07-27), `.xlsx`-only, and re-runs the live source query — so it cannot hold a before/after pair and cannot reconstruct "before" once documents are moved/purged.

**Decision:**

1. **New append-only operation audit — `dbo.CleanupRunOperation`.** One immutable row per mutating primitive executed against MAGIQ, written at the SOAP call sites in `RunPhaseExecutor`. Columns: `Id, RunId, Seq (per-run monotonic), OccurredAtUtc, Phase, Step, OperationType, Outcome (Ok|Failed|Relaxed), TargetType (Domain|Folder|Document|Rule|RecycleBinItem|Selection), SourcePath, DestinationOrNewName, SoapSuccess, Detail (nvarchar json, optional), ErrorMessage, Operator`. `OperationType` ∈ `CreateDomain|CreateFolder|Move|DeleteFolder|DeleteDomain|Purge|Rename|RuleRelax|RuleRestore|OperatorOverride|PurgeAuthorised`. This **complements** — does not replace — `CleanupRunPhaseLog` (phase transitions stay there) and `CleanupRunRename` (which doubles as resume state and carries the audit-lock; a rename also writes a `Rename` audit row for the unified trail).

2. **Move audit granularity = batch-summary (Chase's call, 2026-08-05).** Per-op audit rows for the low-volume, high-consequence ops (create/delete/domain/purge/rename/rule-relax+restore/override). Moves record **one summary row per batch** (`Move`, with moved/failed counts + last path in `Detail`), preserving the deliberate per-batch (not per-document) move-throughput decision (2026-07-28) — no 10k+ extra inserts.

3. **Before/during/after register = three retained artifacts, CSV + xlsx.**
   - **Before** — a **Pre-run register snapshot** (the current source query), captured and *retained* at run start.
   - **During** — the `CleanupRunOperation` audit above.
   - **After** — a **run outcome ledger** built from the run's own tables (per-document final `MoveStatus`, per-folder final `Status`/protection reason, the rename log), **not** a re-query of the source (the source is gone by then).
   Retention: `dbo.RegisterExport` gains `SnapshotKind (PreRun|PostRun|AdHoc)`; the "delete the run's prior export" behaviour is dropped for the two pinned snapshots (AdHoc stays bounded to latest). A `RegisterCsvWriter` sits parallel to `DocumentRegisterExcelWriter` (same untyped column→value rows); export request/download take a `format` (`xlsx|csv`), CSV being the better diff format for before-vs-after.

**Rationale:** The phase log answers "which phases ran," not "what the tool did to each object" — insufficient for records management. A single append-only operation table is the least-ceremony way to close that (one insert per consequential op; batch-summary keeps moves cheap), and it slots into the existing Dapper/DbUp/FastEndpoints grain with no new infrastructure. Pinned pre/post snapshots + the op audit are exactly the before/during/after the operator needs; sourcing "after" from the run's own ledger avoids a source re-query that would return nothing post-purge.

**Follow-ups (ADO under Epic 34120 — see delivery-plan.md):** two stories — **operation audit** and **register before/after + CSV**.

**Implemented in the working tree (uncommitted):**

- *Operation audit* — migration `0002` (`CleanupRunOperation`), domain enums, `ICleanupRunOperationStore` + Dapper store, `GET /api/runs/{runId}/operations` read endpoint, DI, and executor/handler wiring at **every** SOAP site and decision point: `CreateFolder`, `CreateDomain`, `Move` (batch-summary), `DeleteFolder`, `DeleteDomain` + `Purge` (in `ArchiveLibraryTeardown`), `RuleRelax`/`RuleRestore` (via new `onRelaxed`/`onRestored` guard hooks on all three call sites), `OperatorOverride` (Step 6 submit), and `PurgeAuthorised` (Path A confirm / Path B typed purge). `HardDeleteAsync` clears the audit table.
- *Register before/after + CSV* — migration `0002` adds `SnapshotKind` (`AdHoc|PreRun|PostRun`) + `Format` (`Xlsx|Csv`); `RegisterCsvWriter`; `?format=xlsx|csv` on the on-demand export with content-type-aware download; retention keeps AdHoc latest-only while pinning Pre/Post; a **PreRun** snapshot is captured at confirmation and a **PostRun outcome ledger** (built from `CleanupRunDocument`/`CleanupRunFolder`) at completion, both CSV.

**SPA (in the tree):** the Job Details view now renders an **Operation audit trail** panel (polled, outcome-coloured) and a **Document Register** card with an Excel/CSV format toggle and a **before/after snapshot** list (per-snapshot download once the background render is ready), backed by a new `GET /api/runs/{runId}/register/exports` list endpoint. `tsc -b` clean.

**Still open:** `Rename` audit rows arrive with the Name Normalization phase; `OperatorOverride` is attributed to `run.CreatedBy` (tightening to the reviewing operator needs `ICurrentOperator` threaded through the submit command); per-format capture of the pinned snapshots (currently CSV). Spec v0.6, ADR-002, ADR-004, `dev-spec.md`, `CLAUDE.md`, and `deferred-work-plan.md` updated to match.

**Status:** Decision recorded; both stories substantially implemented in the product working tree (uncommitted), verified by house checks (no .NET SDK on the bridge — Chase runs `dotnet build`/`test`). Chase owns branch/commit/PR.

---

## [2026-08-05] Run ownership — a run is read-only to everyone but its owner

**Context:** The operation audit attributes an operator *override* at Step 6 to whoever made the call, but the submit path didn't carry the caller's identity, so it fell back to `CreatedBy` (the run creator, not necessarily the reviewer). Rather than thread `ICurrentOperator` through every mutating command — which would also force ownership-matching updates across dozens of existing handler tests — Chase chose a stronger, simpler model: **give a run an owner and make it read-only to anyone else.** With that, the actor on any mutating call is *necessarily* the owner, so attribution is correct by construction, and the door is open to approvals / ownership transfer later.

**Decision:**

1. **`CleanupRun.Owner`, initially the creator.** A new `Owner` column (migration `0003`) and domain property, set to `CreatedBy` at `Create`. `Owner` is **distinct from** the immutable `CreatedBy` (the creation record) so it can be transferred without losing history — `CleanupRun.TransferOwnership(newOwner)` exists for a future approvals/hand-off flow. Existing rows backfill `Owner = CreatedBy`.

2. **Enforcement in one place — a global pre-processor.** `RunOwnerPreProcessor` (a FastEndpoints `IGlobalPreProcessor`, registered in `Program.cs`) runs before every endpoint: for a **non-GET** request whose route carries a `{runId}`, it loads the run and, if the authenticated operator is not `run.Owner`, short-circuits with **`403 RunNotOwned`**. GETs (view run, phase log, operation audit, folders, register snapshot downloads) are never blocked; a missing run is left for the handler to `404`. Doing it in a pre-processor (not the handlers) means the per-handler unit tests are unaffected — they never traverse the pipeline — so the blast radius is one new class + registration rather than ~14 handlers and their tests.

3. **Override attribution → `run.Owner`.** Since only the owner can submit, the Step-6 `OperatorOverride` audit row is now attributed to `run.Owner` (accurate today, and correct after any future transfer). `PurgeAuthorised`/confirm already carry the real operator (`ConfirmedBy`) and are unchanged.

4. **SPA.** The run summary now carries `owner`; the Job Details view shows it, renders a **read-only** notice for non-owners, and hides the action controls (lifecycle/cleanup actions, the review wizard, the purge control, the on-demand export button) while keeping all read views — progress, outcomes, audit trail, phase log, and the before/after snapshot downloads — visible.

**Rationale:** Ownership is the least-code way to make override (and every other) attribution trustworthy, and it's a genuinely useful guard for a records tool — one operator drives a run; others can watch but not interfere. A single pre-processor is the right seam for cross-cutting resource authorization and keeps the change surface (and test churn) tiny.

**To verify on build (one FastEndpoints-API point):** the `IGlobalPreProcessor` / `IPreProcessorContext<object>` signature and the `ep.PreProcessor<RunOwnerPreProcessor>(Order.Before)` registration against FastEndpoints 8.2 — the short-circuit relies on `Response.SendAsync` starting the response so FE skips the handler.

**Follow-ups (open):** an ownership-**transfer** endpoint + UI and any approval workflow (the domain method exists; no endpoint yet); deciding whether admins may act on any run (currently even an admin is read-only on a run they don't own).

**Status:** Implemented in the product working tree (uncommitted); SPA `tsc` clean. Chase owns branch/commit/PR. ADR-006 amended; `dev-spec.md` updated.

---

## [2026-08-06] Migration consolidation — 0002–0004 folded into the baseline

**Context:** The 2026-08-05/06 work landed as three forward-only scripts on top of `0001_baseline.sql`: `0002` (operation audit `CleanupRunOperation` + `RegisterExport.SnapshotKind`/`Format`), `0003` (`CleanupRun.Owner`), `0004` (`CleanupRun.EnteredNormalization` + `CleanupRunRename`). None had been released/applied to a real database yet.

**Decision (Chase):** Since Chase is **resetting the database**, fold `0002`–`0004` into `0001_baseline.sql` and delete the three scripts — a fresh DB is created from the single baseline. The columns are added inline to `CleanupRun` (`Owner`, `EnteredNormalization`) and `RegisterExport` (`SnapshotKind`, `Format`); `CleanupRunOperation` and `CleanupRunRename` are baked in as `CREATE TABLE`s. Backfills are dropped (no existing rows in a fresh DB). Verified: parens balanced, all four columns + both tables present, 10 `GO` batches.

**Note:** this only makes sense pre-release. Any environment that had already applied 0001 (and would journal 0002–0004 in `SchemaVersions`) must **not** consume this consolidated baseline — the reset path is the assumption here.

**Status:** Done in the product working tree; `0001_baseline.sql` is the sole migration. `dev-spec.md` migration references updated.

---

## [2026-08-06] Name Normalization — bug reported to MAGIQ Documents vendor; phase parked (may be removed)

**Context:** The whole Name Normalization phase (Step 8) exists to work around a MAGIQ Documents **SOAP** limitation: the service can't `Move`/`CreateFolder` a name containing a double space, and addressing an existing doubled item requires its exact doubled path (confirmed against training — `SOAP-VERIFICATION-34525.md` addendum 3, cardinal findings). It's a real amount of moving parts (a mutating phase, an audit-lock, a rename table, SOAP ops) to compensate for what is arguably a platform bug.

**Decision / status:** A **bug has been reported to the MAGIQ Documents application development team** describing the whitespace behaviour. They will **investigate** whether the service can handle doubled-whitespace names natively (`Move`/`CreateFolder`/addressing) or offer an **alternative** — which could let us **retire the Name Normalization phase** entirely. Until they respond, the phase **stays as implemented** (it's being checked in with the latest code) so the annual cull is unblocked. **Parked; revisit when the vendor replies.**

**If the vendor fixes/waives it:** removal would unwind `RunPhase.Normalization` + `ExecuteNormalizationAsync`, the `confirm → normalization` chaining (back to `confirm → archival`), the rename SOAP ops + `RawRenamePath`, `CleanupRunRename` + `ICleanupRunRenameStore`, the `EnteredNormalization` audit-lock, and `RenamePlanner`. The step renumbering (Archival 9–10, Cleanup 11–12) would revert to 8–9 / 10–11. The operation-audit `Rename` type can stay harmlessly. Track that as its own story if it happens.

**Status:** Reported to vendor; phase implemented and retained. No code change — this is a status/decision record. Chase checking in the latest (normalization-inclusive) code.
