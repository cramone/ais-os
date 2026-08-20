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

---

## [2026-08-07] Name Normalization — conflict dry run + operator resolution gate; audit lock retimed

**Context:** Normalizing source names can make two previously-distinct items collapse onto the **same** name under one parent — `Report` + `Report ` → `Report`, or a regular-space vs non-breaking-space pair → the same string. A blind rename would then fail or silently merge. These collisions need an operator decision, not an automated guess. Requested by Chase (spec-first; product implementation to follow).

**Decision:**

1. **Three-part phase.** Step 8 becomes **8a dry run** (`AnalyzeNormalizationAsync` / pure `RenamePlanner`) that plans every rename and detects conflicts **without mutating** → **conflict gate** (`AwaitingInput`) when any exist → **8b execute** (`ExecuteNormalizationAsync`) that applies renames/merges/deletes. No step renumber (8a/8b are narrative sub-parts of Step 8; `RunPhaseExecutor` still emits step 8).

2. **Conflict scope.** A conflict is ≥2 items resolving to the same name under the same parent, evaluated against the **whole projected structure including non-candidate siblings** (`FolderFolder` / `DocumentDocument`).

3. **Resolution options + safe default.** Per conflict: rename folder, rename document, merge the two folders (then inner document conflicts → rename or keep-one/delete-other), or keep-one/delete-other. The **pre-selected default is always a non-destructive disambiguating rename** (`" (2)"`, …); merge and delete-duplicate require a deliberate choice + confirmation and are written to `CleanupRunOperation` (`FolderMerge` / `DeleteDuplicate`). Resolutions draft-saved like Step 6.

4. **Re-analysis loop.** Submitting resolutions re-runs 8a with them applied (a chosen rename/merge can create a new collision) — fixpoint loop until zero conflicts; only then 8b is enqueued. ("Re-run identification" = re-analyse the normalization plan, not Phase 1.)

5. **Audit lock retimed (amends Rule 7).** The lock now trips on the **first executed mutation in 8b** (signalled by `CleanupRun.EnteredNormalization`), **not** on entering `RunPhase.Normalization`. A run still in 8a / the gate has changed nothing and stays deletable. `DescribeDeletability` keys off `EnteredNormalization`, superseding the earlier "any `CleanupRunRename` row / `CurrentPhase` reached" signal. New **Rule 8** covers the conflict gate.

6. **Surfaces.** New `CleanupRunNameConflict` (+ `…ConflictItem`) table (into `0001_baseline.sql`; DB reset pre-release); endpoints `GET /normalization/plan`, `POST /normalization/conflicts/draft`, `POST /normalization/resolve`; SOAP `DeleteDocument` (op name to confirm at integration) plus `Move`+`DeleteFolder` reused for merge; SPA **Normalization Review** view adapted from the Step 6 folder tree.

**Rationale:** A dry run + explicit operator resolution is the only safe way to handle name collisions in a records tool — auto-merging or auto-deleting source items without a decision is unacceptable. Retiming the audit lock to the first real change is both more accurate (nothing has changed until 8b) and kinder to operators who abandon during resolution. Reusing the Step 6 tree view and the existing `AwaitingInput` pause keeps the surface small and avoids a renumber.

**Contingency:** This sits on top of the Name Normalization phase, which is **parked pending the MAGIQ vendor** (`[2026-08-06]`). If the vendor fixes the whitespace `Move`/`CreateFolder` behaviour and the phase is retired, there are no normalization renames and therefore no conflicts — this entire feature retires with it. Flagged to Chase; building it keeps the annual cull unblocked in the meantime.

**Status:** Spec-first — `NATA…Spec_v0.6.md` (Step 8, Rules 7–8, run states, UI, SOAP, navigation) and `dev-spec.md` (phase behaviour, conflict data model, endpoints, component map, sequence) updated; CLAUDE.md constraint updated. **Product implementation not yet started** (`RenamePlanner` conflict detection, the two-job split, the gate endpoints, the SPA view). Chase owns branch/commit/PR.

---

## [2026-08-07] Name Normalization is permanent — vendor won't change; conflict-resolution SOAP ops confirmed

**Context:** The `[2026-08-06]` entry parked the Name Normalization phase pending a MAGIQ Documents vendor investigation of the whitespace `Move`/`CreateFolder` limitation, noting the phase might be retired if the vendor fixed it. Chase has now heard back.

**Decision (Chase, from the vendor):**

1. **The vendor will not change the behaviour.** The whitespace/invisible-character limitation stays. Name Normalization is therefore **permanent** — this **supersedes the "parked / may be removed" status** of `[2026-08-06]`. The removal-unwind plan in that entry is now moot; the conflict dry-run + resolution gate (`[2026-08-07]`, above) proceeds as real, non-contingent work.

2. **`DeleteDocument` verified.** Backs the Step 8 keep-one/delete-other resolution: `AuthenticationTicket` + full `Path` → recycle bin, simple `<response success="…"/>` ack. Captured in `SOAP-VERIFICATION-34525.md` op 18. The earlier "op name/shape to confirm at integration" hedge is removed from both specs.

3. **`GetDocument` `withVersions=true` verified, and drives duplicate identity.** The response carries a `<Versions>` block with a per-version `CheckSum` (+ `VersionSize`). For a **DocumentDocument** conflict the dry run reads each colliding document with versions and compares checksums: **all match ⇒ true duplicates** (keep-one/delete-other is a safe collapse and the gate says so); **any mismatch ⇒ distinct content** (keep-one/delete-other is flagged lossy; the disambiguating rename stays the default). Persisted on `CleanupRunNameConflict.Identical`. Captured in `SOAP-VERIFICATION-34525.md` op 16.

**Rationale:** A permanent platform limitation makes the phase load-bearing, so investing in safe conflict resolution is warranted. Checksum comparison is the only trustworthy way to tell an accidental duplicate (safe to collapse) from two same-named but different documents (must not silently delete) — filename equality alone is not enough in a records system.

**Status:** `SOAP-VERIFICATION-34525.md` updated (ops 16, 18 + addendum-4 findings). Specs updated (`DeleteDocument` un-hedged; checksum identity added to the Step 8 conflict gate; `CleanupRunNameConflict.Identical`). Product implementation still pending with the rest of the conflict-gate work. Chase owns branch/commit/PR.

---

## [2026-08-07] Protection (Rule 2) overrides Name Normalization conflict resolution

**Context:** The Step 8 conflict gate offers destructive resolutions (merge folders, keep-one/delete-other). Without a guard these could delete a **protected** folder (one holding a post-cutoff document, or an ancestor of one) or a **post-cutoff document** — violating Rule 2, the tool's cardinal preservation guarantee. Chase: protection must hold at all times.

**Decision:** Protection wins over every conflict resolution.

1. **No resolution may delete protected content.** 8a tags each `CleanupRunNameConflictItem` with `Protected` (from the Step 4 protection computation). The gate filters options: `MergeFolders` must orient with the **protected folder as the survivor** (the non-protected side is the one whose contents move and which is then deleted — never the protected one); `KeepOneDeleteOther` can't pick a protected/post-cutoff document as the delete target; the pre-selected default `Rename` targets the **non-protected** side; and if **all** colliding members are protected, **rename is the only option**.

2. **Rename is always protection-safe.** A rename deletes nothing, so a protection-safe resolution always exists — the operator can never be forced into removing protected content. (Renaming a protected folder to disambiguate is permitted; Rule 2 forbids *deletion*, not renaming, and the default avoids it by renaming the other side where possible.)

3. **Server re-validates.** `POST /normalization/resolve` re-checks protection against the persisted `Protected` flags and rejects a protection-violating resolution, so a crafted request can't bypass it.

**Rationale:** Rule 2 is the strongest guarantee in the system; a convenience feature (conflict resolution) must never be able to breach it. Orienting merges by protection (rather than blocking them outright) keeps the useful "two folders are really one" case available without risking preserved records.

**Open (Gap 2):** handling of collisions with a **non-candidate** folder (outside the cull) — recommended to treat like protection for deletion (never delete a non-candidate folder; default to renaming the candidate side; allow merge only with the non-candidate as survivor + a clear out-of-scope warning). Awaiting Chase's confirmation before spec'ing.

**Status:** Specs updated — main spec Step 8 conflict section + Rules 2 & 8; `dev-spec` conflict-item `Protected` + protection-filter behaviour. Product implementation pending with the rest of the conflict gate. Chase owns branch/commit/PR.

---

## [2026-08-07] Gap 2 resolved — Name Normalization collisions with a folder outside the cull

**Context:** A candidate folder can normalize onto a **non-candidate** sibling (a folder the cull never selected — no candidate documents beneath it). Merging archived candidates into an out-of-scope folder, or deleting one, would touch data the operator didn't put in scope. Follow-up to the `[2026-08-07]` protection decision (its open Gap 2).

**Decision (Chase — accepted the recommended option):** Treat a non-candidate folder like protected content for **deletion**, but allow a deliberate, warned merge into it.

1. **Never delete a non-candidate folder.** 8a tags `CleanupRunNameConflictItem.NonCandidate`; such a folder is **survivor-only** — a merge may keep it, never `DeleteFolder` it.
2. **Default renames the candidate side**, leaving the out-of-scope folder untouched.
3. **Merge stays available, warned + direction-locked.** For the real "these two are the same folder, duplicated by a paste" case, merge is offered only with the non-candidate as survivor and behind an *"outside this cull — contents will be combined with archived candidates"* warning + confirmation. The response carries an `outOfScope` flag; the SPA badges the out-of-scope side. `resolve` re-validates that neither a `NonCandidate` nor a `Protected` item is ever the deleted side.

**Rationale:** Renaming is the least-surprise automatic outcome; forcing rename-only would block the legitimate paste-duplicate reconciliation. Direction-locking + a loud warning keeps that case available without ever silently absorbing or deleting out-of-scope content.

**Status:** Specs updated — main spec Step 8 conflict section + Rule 8; `dev-spec` conflict-item `NonCandidate` + non-candidate filter + component note. Product implementation pending with the rest of the conflict gate. Chase owns branch/commit/PR.

---

## [2026-08-07] Name Normalization conflict gate — implemented (branches B1–B8); open items for later

**Context:** The conflict dry-run + resolution gate designed spec-first across the four `[2026-08-07]` entries
above was built out end to end in the product working tree, following the ordered branch plan in
`normalization-conflict-gate-plan.md` (B1–B8). Verified by inspection + xUnit (author) / `tsc -b` (SPA);
Chase runs `dotnet build`/`test` + `npm run build` and owns git. This entry records the load-bearing
implementation decisions and, more importantly, the deferred / confirm-at-integration items so a later
session can pick them up without re-deriving context.

**As-built (what landed):**

- **B1** `MagiqPath.Normalize` widened to a single-pass char walk — every `char.IsWhiteSpace` → one space
  (collapse+trim), the six invisibles stripped (the whitespace half was already covered by the old `\s`
  regex; the strip is the real fix). `RenamePlanner.Analyze` added as a pure function returning a
  `NormalizationPlan { Renames, Conflicts }`; conflicts carry a **natural-key identity** (Kind + ParentPath +
  CollidingName), not a Guid, so the planner stays deterministic. `Build` retained as an adapter.
- **B2** `CleanupRunNameConflict(+Item)` into `0001_baseline.sql`; `RunOperationType += FolderMerge,
  DeleteDuplicate`; `NameConflictStatus`; `ICleanupRunNameConflictStore` (+ Dapper + fake); `CleanupRun`
  gate helpers `PauseForNormalizationConflicts` / `ResumeNormalization`. The audit-lock retiming call-site
  move was deferred to B5 (B2 changed no deletability behaviour).
- **B3** `IMagiqSoapClient.DeleteDocumentAsync` (op 18) + `GetDocumentAsync(withVersions)` overload (op 16,
  `DocumentVersion`/`CheckSum`), non-breaking (`DocumentProperties.Versions` is an init-property defaulting
  empty). Overload (not a signature change) so existing callers bind unchanged.
- **B4** `AnalyzeNormalizationAsync` (8a): gathers raw paths + protected folders + committed resolutions +
  doc-conflict checksums, runs `Analyze`, persists conflicts, and **pauses-or-enqueues-execute**; the pipeline
  split into `StartNormalizationAnalysis` / `StartNormalizationExecute`; `ConfirmDeletionsHandler` retargeted.
  8b reads the persisted plan (no build) and the **audit lock now trips on the first executed mutation in
  8b** — a run parked at the gate stays deletable (Rule 7 realised). Protection is keyed to raw folder paths
  by expanding the normalized `CleanupRunFolder` protected set (fail-safe over-protection in the rare
  same-normalized-collision case).
- **B5** 8b executes the operator's destructive resolutions: **duplicate deletes** (`DeleteDocument`) and
  **folder merges** via a **temp-rename mechanism** — the loser is renamed in place to a unique clean name
  (raw-addressed `UpdateFolderProperties`), its immediate children `Move`d into the survivor, the emptied
  loser `DeleteFolder`d through the reactive rule guard; `FolderMerge`/`DeleteDuplicate` audit rows.
  `Analyze` excludes merged/deleted items from the rename plan. The conflict store keeps **Resolved** rows
  across 8a re-analysis (`DeletePendingByRunAsync`) so they survive as the durable 8b action log.
- **B6** Endpoints `GET …/normalization/plan`, `POST …/conflicts/draft`, `POST …/resolve`. **`resolve` is
  asynchronous**: it validates (every pending conflict resolved; no Protected/NonCandidate as a
  delete/merge-loser — server-side defence in depth), persists `Resolved`, `ResumeNormalization` +
  re-enqueues 8a, and responds `{ runStatus, message }`; the client polls the plan for the loop outcome.
  `dev-spec` resolve-endpoint prose updated to match the async/poll model.
- **B7/B8** `api/normalization.ts`; `JobDetailsView` gate is now **phase-based** (`AwaitingInput` +
  `currentPhase` → ReviewSelection/Normalization/Cleanup), replacing the fragile `currentStep <= 8` test;
  `NormalizationReview` renders each conflict with protection/scope/identity badges, the pre-selected safe
  rename, gated destructive options behind warnings, an impact summary, debounced draft autosave, and a
  submit→re-analyse poll loop. `tsc -b` clean.

**Open / deferred items (left here in the decision trail, not a separate backlog):**

1. **Gap-2 non-candidate sibling detection is not wired at runtime.** 8a passes `ExistingSiblings` **empty**,
   so a candidate colliding with a folder *outside the cull* isn't detected yet — the planner (B1) fully
   supports it; what's missing is 8a enumerating each affected parent's existing children, which needs a
   SOAP folder-listing approach + a cost decision (plan `normalization-conflict-gate-plan.md` §13). Current
   behaviour detects candidate-vs-candidate collisions only. Safe (never deletes out-of-scope), just narrower.
2. **Folder-merge SOAP addressing is confirm-at-integration (ADR-011 class).** The temp-rename mechanism,
   the `Move` destination form, and deeply-nested/whitespace child interactions are validated against
   `training.magiqdocuments.com`; merge resume-idempotency is best-effort (consistent with the archival
   accepted edge). Duplicate-delete (`DeleteDocument`, op 18) is already verified.
3. **The SPA review renders a conflict *list*, not a projected folder *tree*.** Spec §"UI structure" and the
   plan §9 (`ProjectedStructureTree` reusing `wizard/folderTree.ts`) describe a folder-structure view of the
   projected archive outcome; the built view is conflict-focused because `GET …/plan` returns conflicts, not
   a projected tree. A richer tree would need the API to return the projected structure too. Not reconciled
   into the spec — a UI-richness enhancement to layer on later.

**Status:** Implemented in the product working tree (uncommitted). Build/test green on Chase's machine
(`dotnet build`/`test`, `npm run build`); the bridge VM has no .NET SDK and its `node_modules` lacks the
Linux rollup binary, so SPA bundling is Chase-side (`tsc -b` passes on the bridge). Chase owns
branch/commit/PR (big-PR delivery). Specs already describe the built behaviour (spec-first); only the three
open items above remain unreconciled, and deliberately so.

---

## [2026-08-08] First-run allowlist reworked to a bootstrap sign-in + `GetAllUsers` typeahead

**Context:** A MAGIQ Documents update means the anonymous `UserExists` SOAP op can no longer be called by
an unauthenticated caller. First-run setup relied on it: the wizard tested the SOAP endpoint (anonymous
`ServerInfo`), then validated each typed admin-allowlist username via anonymous `UserExists` before saving.
That validation now fails, and there is no anonymous way to confirm an allowlist username exists — but the
allowlist must be seeded before anyone can sign in (fail-closed: an empty allowlist denies everyone).

**Decision:**

1. **Bootstrap sign-in during setup.** The MAGIQ access phase becomes *test endpoint → sign in → allowlist*.
   The operator authenticates with a MAGIQ account against the candidate endpoint (`POST /setup/magiq/login`).
   On success the account is **auto-added to the allowlist as the first operator, pinned (non-removable)** so
   the operator can't save an allowlist that locks themselves out. The resulting UI ticket is stashed in the
   shared httpOnly `ticket` cookie (kept out of JS, reusing the existing auth-cookie infra), so the follow-up
   user-list and save calls re-present it server-side.

2. **`GetAllUsers` typeahead.** Authenticated `GetAllUsers` (SOAP-VERIFICATION-34525.md op 19) powers a
   name/username typeahead — search by UserName / FirstName / LastName, each shown as `First Last (username)`.
   Accounts with `Enabled="FALSE"` are filtered out. Setup uses `POST /setup/magiq/users` (cookie ticket,
   candidate endpoint); System Settings uses `GET /admin/magiq/users` (live UI ticket, configured endpoint) —
   the same typeahead **replaces the plain newline-list allowlist editor** there too, with a manual
   add-by-username escape hatch when `GetAllUsers` is unavailable.

3. **Server-side save enforcement via `GetAllUsers`.** `POST /setup/magiq` no longer re-checks each username
   with anonymous `UserExists`; it re-lists enabled users with the cookie ticket and rejects any allowlist
   entry not among them (the call also proves endpoint reachability).

4. **Retired the anonymous check.** `POST /setup/magiq/validate-user` (`SetupMagiqProbe.UserExistsAsync`) was
   removed. The SOAP client keeps `UserExistsAsync` for authenticated existence checks; a new
   `GetAllUsersAsync` + `MagiqUser`/`MagiqUserList` + `ParseUserList` were added.

**Rationale:** A bootstrap sign-in is the only way to obtain an authenticated ticket before the allowlist
exists, and it doubles as proof the operator holds a real, working MAGIQ account. Pinning the bootstrap user
prevents self-lockout. Reusing the httpOnly cookie keeps the raw ticket out of JS, consistent with the app's
ticket-handling stance. Filtering disabled accounts and offering a searchable name/username picker removes
the "type an exact username and hope" failure mode the old flow had.

**Status:** Implemented in the product working tree (uncommitted). Frontend `tsc -b` passes on the bridge VM;
C# validated by balance/reference checks (no .NET SDK on the bridge) — Chase runs `dotnet build`/`test`.
Specs updated in the same unit of work (v0.6 Authorisation + First-run setup + SOAP ops table + History;
`dev-spec.md` setup/admin endpoint tables + admin-allowlist SOAP op; `SOAP-VERIFICATION-34525.md` op 19).
Chase owns branch/commit/PR.

---

## [2026-08-08] First-run setup UX refinements — endpoint auto-suffix, lock-on-sign-in, skip second login

**Context:** Follow-up polish on the reworked first-run allowlist flow (previous entry). Three rough edges:
operators forget the `/srv.asmx` suffix on the SOAP URL; nothing stopped signing in against one service and
then editing the URL to point at another before saving; and after finishing setup the operator was shown the
login screen even though they'd just authenticated.

**Decision:**

1. **Auto-suffix `/srv.asmx`.** On endpoint blur/test the wizard tidies the URL — trims, drops trailing
   slashes, and appends `/srv.asmx` when the path doesn't already end in an `.asmx` service file (an explicit
   `…/x.asmx` is left alone; a non-URL is left for the field's own validation).

2. **Lock the endpoint after sign-in.** Once signed in, the endpoint renders as a distinct read-only field
   (lock icon, tinted, monospace, "Locked" badge) with a **Change** button. Change re-opens editing, clears
   the sign-in, and **resets the allowlist** (those users came from the previous service's directory), so a
   fresh sign-in is required — you can't authenticate against service A and save an allowlist against B. The
   server already rejects this too (a save re-lists users with the cookie ticket, which won't validate
   against a different endpoint), so the lock is defence-in-depth + a clear UX.

3. **Skip the second login.** `AuthContext` gains `revalidate()` (re-runs `/auth/me`); the wizard calls it on
   completion, so the bootstrap sign-in's shared ticket cookie is adopted and the operator lands straight in
   the app. If the ticket has lapsed (very slow setup, past the 20-minute window) `revalidate` fails and the
   login screen is the fallback.

**Status:** Implemented in the product working tree (uncommitted); `tsc -b` passes on the bridge VM. Same
branch/PR as the previous entry. Spec updated (v0.6 First-run setup paragraph). Chase owns branch/commit/PR.

## [2026-08-09] Idempotent archive-library create (adopt existing on name collision)

**Context:** During a live Step 9 run, `CreateDomain` failed with *"A library with this name already
exists. Please choose another name."* This happens in create mode (`ArchiveLibraryId is null`) when a
prior attempt created the domain but crashed before persisting `ArchiveLibraryId`, so a resume re-enters
create mode and re-issues `CreateDomain` against a name that now exists.

**Decision:** Make library creation idempotent. Before `CreateDomain`, `ExecuteArchivalAsync` calls
`GetDomains` (`ListDomainsAsync`) and, if a library whose name equals `ArchiveLibraryName`
(case-insensitive) already exists, it **adopts** that library — `SetArchiveLibraryId(match.Id ?? root)`
and skips `CreateDomain`. A `GetDomains` fault fails the phase (same as a create fault).

**Ownership / teardown:** an adopted library is deliberately **NOT** marked `CreatedArchiveLibrary`.
Create mode cannot prove *this* run created the colliding library, and a records-management tool must
never schedule a `DeleteDomain` teardown for a library it can't prove it made. Trade-off (chosen by
Chase, "don't mark created — safer"): an orphaned empty library from a prior crash is left for the
operator to remove, in exchange for never auto-deleting a pre-existing library that merely shares the
name. The adoption is audited as `CreateDomain / Ok` with a `Detail` noting creation was skipped.

**Status:** Implemented in the product working tree (uncommitted) —
`RunPhaseExecutor.ExecuteArchivalAsync`, plus `RunPhaseExecutorArchivalCreateDomainTests` (adopt + create
paths). Spec updated (v0.6 Step 10 paragraph + History; dev-spec new "Step 9 — Create (or adopt)" flow).
Chase owns branch/commit/PR.

## [2026-08-09] Operation audit trail — scale rework (live feed + paged/searchable trail; per-document moves)

**Context:** The SPA Job Details view loaded the **entire** operation audit trail on every 5s poll and
rendered it in one unbounded Mantine table. On a long-lived run the trail grows without bound, so the
payload and the DOM grow with it and the page slows down. Two asks from Chase: (a) a live "what's
happening now" view with plain-language descriptions plus a paged/searchable full trail, filterable on
operation, target, outcome and path; and (b) show a batch document move as its **individual items**, not
one summary line.

**(b) reverses a logged decision.** The 2026-08-05 entry recorded moves as **batch-summary** — one
`Move` row per batch of 25 (moved/failed counts in `Detail`) — explicitly to avoid tens of thousands of
inserts. This was surfaced to Chase before proceeding; he chose per-document rows, reconciled against the
insert-volume concern by **bulk-inserting one set-based INSERT per batch** (not per-row round-trips), so
move throughput matches the old summary write while each document becomes a first-class, searchable row.

**Decisions:**
1. **Per-document move audit, bulk-inserted.** `MoveDocumentsAsync` now builds a `CleanupRunOperationDraft`
   per document (path, archive destination, `Ok`/`Failed`, error, SOAP success) and writes the batch in one
   `ICleanupRunOperationStore.AppendManyAsync` — a single `VALUES`-list INSERT that assigns the per-run
   monotonic `Seq` as `MAX(Seq) + ordinal`. The old single batch-summary `AppendAsync` is gone. The retry
   pass naturally adds a second row per re-attempted document (a truthful audit of the retry).
2. **Server-paged, filtered read.** `GET /runs/{runId}/operations` now returns one **newest-first page**
   (`Seq DESC`) plus the unpaged `total`, with `?page=`/`?pageSize=` (default 50, max 200) and filters
   `?operationType=`, `?targetType=`, `?outcome=`, `?path=` (substring over source/destination) and
   `?search=` (free text over path/destination/detail/error). Backed by a new
   `GetPageByRunAsync(runId, filter, skip, take)`; `LIKE` terms are wildcard-escaped with `ESCAPE '\'`.
   Unknown enum filters are ignored (matching the `ListRuns` forgiving contract). No schema/migration
   change — the existing `IX_CleanupRunOperation_RunId_Seq` covers newest-first paging within a run.
3. **SPA split into two surfaces.** New `OperationAuditPanel`: a compact **live activity** feed (latest ~8,
   plain-language `describeOperation` lines, polled every 5s while the run is live) above the **full trail**
   — a searchable/filterable, server-paged table with a Mantine pager. `JobDetailsView` no longer loads the
   trail in its polling `load()`; the panel fetches on demand, so the 5s poll no longer re-pulls the whole
   history.

**Rationale:** Paging + server-side filtering is the actual fix for the perf issue; the live feed gives the
"during" narrative the operator wants without scrolling a huge table. Per-document rows are the right audit
grain for a government records tool — the batch-summary was a throughput compromise, and bulk-insert removes
the reason it existed, so the reversal costs nothing at write time while making every move auditable and
searchable.

**Status:** Implemented in the product working tree (uncommitted). API — `AppendManyAsync` +
`GetPageByRunAsync` (+ `CleanupRunOperationDraft`/`CleanupRunOperationFilter`), `MoveDocumentsAsync`
per-document rows, paged/filtered `GetRunOperations` endpoint/query/handler/response, fake store + new
`GetRunOperationsHandlerTests` and a per-document `RunPhaseExecutorArchivalCreateDomainTests` case. SPA —
`OperationAuditPanel`, `api/runs.ts` paged call, `JobDetailsView` wiring, two new icons. Verified by house
checks (interface implementers, Dapper param/`LIKE` escaping, `QueryMultipleAsync` order) and `tsc -b`
(clean); Chase runs `dotnet build`/`test` and owns branch/commit/PR. Spec updated (v0.6 "during" + Job
Details paragraphs + History; dev-spec endpoint row + `CleanupRunOperation` grain; baseline SQL +
`RunOperationType.Move` comments).

**Follow-up (2026-08-09, same work):** two fixes on top of the above.
1. **Live audit refresh.** The full trail only updated on a manual run reload. `OperationAuditPanel`'s
   `FullAuditTrail` now re-fetches its current page/filters on the 5s poll while the run is live (a `tick`
   bumped by an interval, plus `live` in the fetch deps for a final refresh when the run stops). Because the
   trail is newest-first, new rows land on page 1 — so paging/totals stay correct and the operator sees
   activity without reloading. No API change.
2. **Cancel actually stops in-flight phases.** Cancel is cooperative — `CancelRun` only flips the DB to
   `Cancelled` and each phase must observe it at a guarded checkpoint (`IsCancellationRequestedAsync`, a
   fresh DB read). Only the Step 9/10 **move** and **normalization** had checkpoints; **identification**
   (Steps 1 & 4 batch loops) and **cleanup** (`DeleteEmptyFoldersAsync` delete loop) had none, so a cancel
   during those phases let the phase run to completion — and worse, identification then **clobbered** the
   `Cancelled` status by calling `BeginReview` (→ `AwaitingInput`) on its in-memory run. Added a shared
   `StopIfCancelledAsync(runId, phase, step, message, ct)` helper (logs `Cancelled`, refreshes the UI,
   returns true to stop **without** writing further run state) and called it between batches in both
   identification loops, before identification's step-advance/`BeginReview` transitions, and between
   batches in `DeleteEmptyFoldersAsync` (now returns `bool` cancelled; `ExecuteCleanupAsync` stops before
   the irreversible purge). Purge/teardown is deliberately left uninterruptible (irreversible, and Cancel
   is disallowed once terminal). This brings the code in line with the spec's existing promise that Cancel
   "stops cooperatively at the next guarded checkpoint" (v0.6 Cancel row) — no spec change needed, though it
   was previously inaccurate for those two phases. Test: `RunPhaseExecutorRuleGuardTests`
   `Cleanup_cancelled_by_operator_stops_before_deleting_folders_and_stays_cancelled`.

## [2026-08-09] Reactive delete-rule handling: relax once per folder, not per item

**Context:** During a live NATA cull, Step 10 moves failed with MAGIQ's *"Folder rules disallow
deletions in this folder."* even though the source folder genuinely only needed its
`DISALLOWDOCUMENTDELETE` relaxed. Chase verified relaxing the parent folder once lets every child move.
The reactive guard (`RetryWithRuleRelaxedAsync`) was invoked **per item**: for each blocked document it
read the folder's rules, relaxed the one rule, retried, and restored — so a folder with N blocked
documents had its rule flipped allows→disallows N times in rapid succession. Against MAGIQ that
flip/read churn left the second and later documents in the folder failing (the guard's live re-read and
the retried move race the just-reverted rule; the audit even shows the first document relaxing/moving/
reverting and the next failing). The single per-item guard was correct in isolation but wrong-shaped for
a folder of items.

**Decision:** Relax once per folder. Group the work by the rule-bearing folder (a folder's documents in a
Step 10 move, a parent's child folders in a Step 11 delete, a folder's returning documents in a rollback
move-back), attempt each item once, and — only if some are blocked — relax that folder's rule a **single**
time, retry just the still-blocked items under the relaxed rule, then restore **once**. Implemented as a
new folder-scoped guard primitive `IFolderDeleteRuleGuard.WithRuleRelaxedAsync(folder, rule, body, …)`
(read rules → if the rule is the blocker, relax → run body → restore in a `finally`; if the rule already
allows or can't be read, the body does not run and the caller's items stay failed). The per-operation
`RetryWithRuleRelaxedAsync` now delegates to it and is kept for the genuinely single-op site (the
Normalization folder-merge loser delete). A shared `RunFolderGroupAsync` helper drives "attempt-all →
relax-once-retry-failed" for the three loops.

**Consequences:** For a folder of N blocked items the rule is now read once and flipped twice (relax +
restore) instead of N reads and 2N flips — fewer live mutations of the customer repository and no
flip/read race. Live-rule read at failure time, the verbatim restore, the non-cancellable revert, and the
"rule already allows / unreadable / relax rejected → original error stands" semantics are all preserved.
No behaviour change for a folder with a single blocked item (the SOAP call sequence is identical), so the
existing guard/executor tests hold unchanged.

**Status:** Implemented in the product working tree (uncommitted) — `FolderDeleteRuleGuard` +
`IFolderDeleteRuleGuard` (new `WithRuleRelaxedAsync`), `RunPhaseExecutor` (`RunFolderGroupAsync` + the
Step 10 move, Step 11 delete, and rollback move-back loops grouped by folder). Tests: new
`WithRuleRelaxedAsync` unit tests + `RunPhaseExecutorRelaxOncePerFolderTests` proving one read + one relax
+ one restore per folder across multiple items. Spec updated (v0.6 "Folder rules and the Move is copy +
delete constraint" + History). Chase owns branch/commit/PR.

## [2026-08-09] Audit trail — sortable + resizable columns, friendly Path, Path typeahead

**Context:** Follow-on polish to the reworked operation audit trail. Chase asked for sortable and resizable
columns, friendlier display of the (often very long) Path values, and a typeahead on the Path filter.

**Decisions:**
1. **Server-side sort.** Because the trail is server-paged, sorting must order the whole (filtered) dataset,
   not just the visible page — so it's a server concern. `GetPageByRunAsync` gained `sort`
   (`CleanupRunOperationSort`: `OccurredAt`|`OperationType`|`TargetType`|`Outcome`|`Path`) + `descending`;
   the column name comes from a fixed **allow-list** map (never interpolated from client input) with `Seq DESC`
   as a stable tiebreaker. `GET /operations` takes `?sort=`/`?dir=` (defaults `occurredAt`/`desc`; unknown
   values fall back). SPA headers toggle sort and show a caret.
2. **Resizable columns, persisted.** SPA-only: `table-layout: fixed` with per-column widths dragged via a
   pointer handle on each header's right edge, clamped to a per-column min, saved to `localStorage`
   (`dlc.auditTrail.columnWidths.v1`) so they survive reloads. No backend involvement.
3. **Friendly Path cell.** The Path column truncates **at the front** (`direction: rtl` + `bdi`) so the
   identifying leaf (file/folder name) stays visible, with a leading ellipsis, the full path on hover, and a
   copy button. `source -> destination` is shown when the op has a destination/new name.
4. **Path typeahead.** New read `GET /runs/{runId}/operations/paths?contains=&take=` ->
   `GetDistinctPathsAsync` (distinct `SourcePath`, optional case-insensitive `contains`, capped). The SPA
   Path filter is a Mantine `Autocomplete` fed by this endpoint as the operator types (debounced).

**Rationale:** Sorting has to be server-side to be correct over paged data; everything else is presentation.
The front-truncation is the key call — end-ellipsis would hide the filename, which is the most identifying
part; RTL truncation keeps it. A distinct-paths endpoint (rather than deriving from the loaded page) makes
the typeahead cover the whole run.

**Status:** Implemented in the product working tree (uncommitted). API — `CleanupRunOperationSort`, sort
params on `GetPageByRunAsync`, `GetDistinctPathsAsync`, `GetRunOperations` sort wiring, new
`GetRunOperationPaths` feature (endpoint/handler/query/request/response). SPA — `OperationAuditPanel`
sortable/resizable table + `PathCell` + `Autocomplete`, `api/runs.ts` (`sort`/`dir`, `getRunOperationPaths`),
five icons. Tests — sort case in `GetRunOperationsHandlerTests`, new `GetRunOperationPathsHandlerTests`, fake
store updated. Verified by house checks + `tsc -b` (clean); Chase runs `dotnet build`/`test` and owns
branch/commit/PR. Spec updated (v0.6 Job Details paragraph; dev-spec `/operations` sort params + new
`/operations/paths` row).

## [2026-08-09] Audit trail — content-sized fixed columns (resizable removed)

**Change (Chase's call):** dropped the resizable columns added earlier the same day in favour of
**content-sized fixed columns** for When, Operation, Target and Outcome, and reverted the Path cell's
front-truncation while keeping the copy button.

- **Content sizing.** A `useLayoutEffect` measures each of the four columns against its header label (plus a
  sort-caret allowance) using the table's actual rendered font (canvas `measureText`), takes the widest, and
  adds a **10px buffer on each side** — applied as cell padding so, with `box-sizing: border-box`, the text's
  own space equals the measured maximum. The three **enum** columns (Operation, Target, Outcome) are sized
  against their **full list of possible enum names** (not the current page), so their widths are constant and
  never shift when paging; **When** is measured from the page's timestamps (uniform width). Columns are single
  line (`white-space: nowrap`); the flexible columns (What happened / Path / Detail) wrap as before.
- **Removed:** the `localStorage`-persisted widths, the pointer-drag resize handles, and `table-layout: fixed`.
- **Path cell:** back to the plain source (or `source → destination`) text that wraps, **with the copy button
  retained**. The RTL leaf-first truncation is gone.

Sorting (server-side), the Path typeahead, and the live refresh are unchanged. `tsc -b` clean. Spec updated
(v0.6 Job Details paragraph). Chase owns branch/commit/PR.

## [2026-08-09] Audit trail — split Path into Source path + Destination path columns/filters

**Change (Chase's call):** the single Path column carried both source and destination (`source → destination`).
Split it into two first-class, independently **sortable** and **filterable** columns.

- **Columns.** Replaced "What happened" (the derived plain-language cell — still used by the live feed) with
  **Source path** (`SourcePath`), and the combined Path column with **Destination path** (`DestinationOrNewName`).
  Order: When | Source path | Operation | Target | Outcome | Destination path | Detail. Both path cells keep
  the copy button.
- **Sort.** `CleanupRunOperationSort.Path` → `SourcePath` + `DestinationPath` (mapping to the `SourcePath` /
  `DestinationOrNewName` columns via the allow-list). `GET /operations` `?sort=` accepts `sourcePath` /
  `destinationPath`.
- **Filter.** The single `?path=` filter (which matched source OR destination) became `?sourcePath=` and
  `?destinationPath=`, each a substring match on its own column; `CleanupRunOperationFilter.Path` → `SourcePath`
  + `DestinationPath`. The free-text `?search=` still spans both plus detail/error.
- **Typeahead.** `GET /operations/paths` gained `?field=source|destination` (default source), backed by
  `GetDistinctPathsAsync(runId, destination, …)` selecting the chosen column (from a fixed pair). The SPA now
  has two Autocomplete filters, each fed by its field.

`tsc -b` clean; C# by house checks. Tests: source + destination filter cases and a destination-sort/typeahead
case added; existing cases updated for the new signatures. Spec updated (v0.6 Job Details paragraph; dev-spec
`/operations` + `/operations/paths` rows). Chase owns branch/commit/PR.

## [2026-08-09] Faithful audit ordering for the relaxed retry (relax → items → restore)

**Context:** Reading a live run's audit trail, Chase saw for one folder: `RuleRelax` (DocumentDeletes
allowed) → `RuleRestore` (DocumentDeletes disallowed) → `Move` (Document, Failed). The trail read as if
the folder rule was reverted *before* the documents were moved. Two things were happening: (1) in the old
per-item guard, a later document's relaxed retry genuinely failed (the churn bug, fixed by
relax-once-per-folder); and (2) the per-item/per-batch audit **rows** for the moves were appended *after*
the `RuleRestore` row, because the move rows were persisted after the guard returned — so even a
successful move would be stamped after the restore, making the trail misleading for an audit surface that
operators rely on.

**Decision:** Record each folder group's per-item outcomes (results + audit rows) from **inside** the
relaxed scope — after the retries, before the restore. `RunFolderGroupAsync` now takes a `recordOutcomes`
callback and invokes it exactly once: in the all-succeeded-first-try path (no relax), or inside the
`WithRuleRelaxedAsync` body before the `finally` restore (when relaxed), or after the guard when it chose
not to relax. Because `RuleRelax`/`RuleRestore` are appended by the guard's `onRelaxed`/`onRestored` hooks
(the relax hook fires before the body, the restore hook in the `finally` after it), stamping the item rows
inside the body places them, by `Seq`, between `RuleRelax` and `RuleRestore`. The trail now reads
`RuleRelax → Move/DeleteFolder rows → RuleRestore`, faithfully matching the SOAP order.

**Consequences:** Move audit rows are now appended per **folder group** (one `AppendManyAsync` per group)
rather than once per batch — still set-based, no per-row round-trip. No functional change to what moves/
deletes happen; purely the ordering and grouping of the audit writes. Folder-delete rows likewise land
between the relax/restore; rollback has no per-move audit rows so only its results move into the callback.

**Status:** Implemented in the product working tree (uncommitted) — `RunFolderGroupAsync` (`recordOutcomes`
callback) and the three call sites' record callbacks. Tests: `RunPhaseExecutorRelaxOncePerFolderTests` now
asserts the audit order `RuleRelax → item rows → RuleRestore` for both the Step 10 move and the Step 11
delete. Same branch as the relax-once change. Chase owns branch/commit/PR.

## [2026-08-10] Export the operation audit trail to CSV (honouring the current filters)

**Context:** Operators wanted to pull the operation audit trail out of the Job Details view for offline
review / attaching to records — and specifically the *filtered* view they'd narrowed to (e.g. failed
Moves under one facility), not the whole trail.

**Decision:** Add a synchronous CSV export driven by the same filters as the paged trail. New
`GET /api/v1/runs/{runId}/operations/export` takes the identical `?operationType/targetType/outcome/
sourcePath/destinationPath/search/sort/dir` query as `.../operations` (minus paging) and streams a
`text/csv` file of every matching row. Backed by a new `ICleanupRunOperationStore.GetAllByRunAsync` (the
unpaged form of `GetPageByRunAsync`, sharing the exact WHERE/ORDER building so the export matches the SPA
one-for-one) and a hand-rolled `RunOperationsCsvWriter` (fixed schema, RFC 4180, UTF-8 BOM, CRLF — the
same approach as `RegisterCsvWriter`). The file opens with a `#`-prefixed **filter-summary header** (run,
export time, sort, and the active filters) so it is a self-documenting audit artifact. The SPA adds an
**Export CSV** button to the audit panel header that calls the endpoint with the current filters and
downloads the streamed file (bearer-auth fetch → blob, mirroring the register download).

**Why CSV-only, synchronous:** the trail is a fast bounded DB read + string build, so — unlike the
Document Register's large, background-rendered xlsx — it needs no job/polling/stored artifact. CSV opens
cleanly in Excel and is the natural fit for an audit extract. (Chase's call: CSV only, with the filter
header.)

**Status:** Implemented in the product working tree (uncommitted) — `ExportRunOperations` feature
(endpoint/query/handler/request/content), `IRunOperationsCsvWriter`+`RunOperationsCsvWriter` (registered
in `Program.cs`), `GetAllByRunAsync` on the store + fake, and the SPA `exportRunOperations` client +
Export CSV button. Tests: `RunOperationsCsvWriterTests` (header/escaping/BOM) and
`ExportRunOperationsHandlerTests` (filtered rows, filter header, 404). Frontend `tsc -b` passes on the
bridge VM. Spec + dev-spec updated. Chase owns branch/commit/PR.

## [2026-08-10] SetFolderRules must send <Rules> as nested XML, not escaped text (the real cause of the delete-lock failures)

**Context:** After the per-folder relax-once change and the faithful audit ordering, a live NATA cull
STILL failed Step 10 moves with *"Folder rules disallow deletions in this folder."* The now-faithful audit
showed, for the exact source folder: `RuleRelax` (DocumentDeletes) → `Move` (Failed) → `RuleRestore` — i.e.
the relax ran on the right folder, the move happened while "relaxed", and it still failed. A live
`GetFolderRules` capture (training, 2026-08-10) confirmed the rule **names/values match the code exactly**
(`DocumentDeletes` = `allows`/`disallows`), so the read and the relax *content* were correct.

**Root cause:** `MagiqSoapClient.SetFolderRulesAsync` sent `xmlRules` as a raw string set as element text,
which the envelope builder XML-**escaped** (`<xmlRules>&lt;Rules&gt;…</xmlRules>`). MAGIQ's `SetFolderRules`
reads the **child `<Rules>` markup**; an escaped string is **silently ignored** and the call returns
`success="true"` **without applying anything**. So every relax was a no-op — the folder stayed
`DocumentDeletes=disallows`, and the retried Move's delete-half stayed blocked. A hand-run Postman request
with the `<Rules>` as **inline nested XML** flipped the rule; the escaped form did not. (This was an
`xsd:any`/unverified request shape — deferred Story 34525.)

**Decision:** Send `xmlRules` as real nested XML. `SetFolderRulesAsync` now parses the `<Rules>` fragment
and rebuilds it into the tempuri namespace (`ToTempuri`) so it embeds as a child of `<xmlRules>` and
inherits the operation's default `xmlns` on the wire (no `xmlns=""` reset) — byte-for-byte the
verified-working request. `ApplyToTree=false` unchanged. Everything else stands: the per-folder
relax-once structure, the faithful audit ordering, `GetFolderRules`/`ParseFolderRules`, and
`FolderRuleSet.WithAllowed`/`OriginalXml` (which still produce the `<Rules>` string the client now embeds).

**Caveat for the audit trail:** a `SetFolderRules` `success="true"` does NOT prove the rules were applied —
confirm with a follow-up `GetFolderRules`. Documented in `SOAP-VERIFICATION-34525.md` (op 21) under the
"encoding is the finding" note.

**Status:** Implemented in the product working tree (uncommitted) — `MagiqSoapClient.SetFolderRulesAsync`
(+ `ToTempuri`). Wire-level tests updated (`MagiqSoapClientFolderRulesTests`) to assert nested XML instead
of escaped text; the failing test that encoded the bug is inverted. Docs: `SOAP-VERIFICATION-34525.md`
addendum 6 (ops 20–21, with the verified request/response), ADR-004 + ADR-011 amended. Chase owns
branch/commit/PR — and should re-run the cull to confirm the moves now succeed.

---

## [2026-08-10] Step 8 review gate widened to any name change + name-change export

**Context:** The Step 8 Normalization gate only paused when there were **name conflicts**; a clean plan
(plain whitespace/invisible renames, no collisions) ran 8a → 8b automatically, so the operator never saw
the folder/document renames before they were applied. The `GET …/normalization/plan` endpoint returned
only the conflicts, dropping the full rename set the planner already computes, and there was no way to
download a before → after list of the changes. Chase asked to extend the (existing) Document Register
before/after story so an operator can review **every** planned name change — and export it — before
confirming, while still working through conflicts as today. Two forks were settled with Chase: (1) the run
pauses whenever there are **any** renames (not only conflicts); (2) the download is a **targeted
name-change list** (before → after), reusing the register's Excel/CSV writers — not full pre/post register
snapshots.

**Decision:**

1. **Pause on any change.** `AnalyzeNormalizationAsync` (8a) now pauses the run in `AwaitingInput` +
   `Normalization` whenever the plan contains a conflict **or** a rename. Only a plan that changes nothing
   skips the gate and chains 8b automatically. The audit lock (Rule 7) is unchanged — it still trips only
   on the first executed mutation in 8b, so a parked run has changed nothing and stays deletable.

2. **Explicit confirm.** A resolved-clean plan no longer auto-executes; it parks at the review gate showing
   the full change list. A new `POST /runs/{runId}/normalization/confirm` (owner-guarded) resumes the run
   and enqueues 8b → archival → cleanup. Confirm is rejected (`409 UnresolvedConflicts`) if any conflict is
   still pending — server-side defence on top of the UI.

3. **Full rename list surfaced.** `GET …/normalization/plan` now returns `Renames` (type, path, original →
   new, status) alongside the conflicts, populated from `dbo.CleanupRunRename`.

4. **Name-change export.** `GET /runs/{runId}/normalization/changes/export?format=xlsx|csv` renders the
   change set — renames plus resolved merges/duplicate-deletes — reusing `IRegisterCsvWriter` /
   `IDocumentRegisterExcelWriter`. Synchronous (change-bounded row set, no Hangfire job), available at the
   gate and afterward as the record of what 8b did.

5. **SPA.** `NormalizationReview` now shows an "All name changes" table (before → after with invisibles
   made visible), a format toggle + Download-changes control, and a Confirm & continue action; the
   no-conflict case skips the resolver and goes straight to the change list. `JobDetailsView` gate trigger
   (`AwaitingInput` + `Normalization`) is unchanged and already covers the no-conflict pause.

**Rationale:** "Review all name changes prior to confirming" requires a human step whenever names change,
not only on collisions. Reusing the register writers keeps the export format consistent and avoids new
rendering code. Keeping the audit lock on the first 8b mutation preserves the Rule 7 invariant. Note the
side effect: a reset/retry that re-enters 8a now pauses for a re-confirm instead of auto-continuing —
acceptable and safer given the gate philosophy.

**Status:** Implemented in the product working tree (uncommitted): executor gate retiming; `Confirm` +
`ExportChanges` features; `Renames` on the plan response + handler; `DraftResolutions` updated for the new
response shape; SPA `NormalizationReview` + `api/normalization.ts` + `JobDetailsView` copy; xUnit tests
(gate pause-on-rename + zero-change auto-continue, confirm handler, export handler, plan renames). C#
validated by balance/reference checks; Chase runs `dotnet build`/`dotnet test` + `npm run build`, and owns
branch/commit/PR. Plan: `normalization-change-review-plan.md`. Spec + dev-spec updated in step.

---

## [2026-08-10] Step 10 operator move-failure retry + post-archival pause

**Context:** When Step 10 (document move) finishes with documents that could not be moved, the phase does a
single automatic retry and then fails the whole run (`FailArchival`) — the executor comment literally noted
per-item retry was "deferred". The only recovery was the generic **Retry (resume)** lifecycle action, which
re-runs the entire archival phase and auto-chains cleanup; there was no failures list and no way to retry a
single document. Chase asked to surface the Step 10 failures and let the operator work through them —
retrying individually or all together. Two forks were settled: (1) after a retry clears the last failure the
run should **stop and let the operator proceed** to cleanup (not auto-continue); (2) UI placement was left to
best practice — a failures panel in the Job Details view.

**Decision:**

1. **Scoped retry job.** New `RunPhaseExecutor.RetryDocumentMovesAsync(runId, documentRowIds?)` re-attempts
   the selected failed documents (or all failed when null/empty) via the existing move machinery
   (destination-ensure, per-folder relax-once, per-document audit). It is enqueued by a new pipeline method
   `StartMoveFailureRetry` and is **not** chained to cleanup.

2. **Stop-and-proceed after archival.** On full success (no document left failed) the job calls the new
   `CleanupRun.PauseAfterArchival()` → `AwaitingInput` in the Archival phase, rather than auto-chaining
   cleanup. The operator proceeds with `POST …/archival/continue` (`CleanupRun.ResumeAfterArchival()` →
   `StartCleanup`). If any move still fails, the run returns to `Failed` for another attempt. This keeps a
   human checkpoint before the irreversible cleanup/purge, per Chase's choice. (Note: the normal, no-failure
   archival path still auto-chains cleanup — only the recovery path gains the checkpoint.)

3. **Endpoints.** `GET /runs/{runId}/archival/move-failures` (list + `canRetry`/`canContinue` flags),
   `POST …/archival/move-failures/retry` (`{ documentRowIds? }`), `POST …/archival/continue`. Retry is valid
   only for a `Failed` run in the archival phase with at least one failure; continue only for a run paused
   post-archival. Owner-guarded (non-GET).

4. **SPA.** A **Document move failures** panel in the Job Details view lists each failed document (path,
   error, attempts) with per-row Retry, Retry selected, and Retry all; while a retry runs it polls and
   disables the actions; once all clear it shows **Continue to cleanup**.

**Rationale:** Reusing the move machinery keeps the retry faithful to the normal move (rules, audit,
resume-safety) with no duplicate SOAP logic. Pausing after a recovery retry — but not on the clean path —
gives the operator a deliberate checkpoint exactly when something already went wrong, without adding friction
to the happy path. The generic Retry/Reset lifecycle actions remain for whole-phase recovery.

**Refinement (2026-08-10, after first UX review).** On feedback the retry was made **synchronous and
per-row inline** rather than a background job: the endpoint now returns each targeted document's outcome and
the panel shows *Retrying… → Moved* in the row itself, keeping resolved rows in the table, without touching the
main run-progress panel. Consequently the async path was removed — `RetryDocumentMovesAsync` +
`IRunPipeline.StartMoveFailureRetry` are gone, replaced by `IMoveFailureRetryer.RetryDocumentMovesInlineAsync`
(implemented by `RunPhaseExecutor`, injected into the handler) which moves the targets with
`MoveDocumentsAsync(…, emitProgress: false)` and pauses (`Retry()` → `PauseAfterArchival()`) only when the
last failure clears. The retry endpoint returns `{ runStatus, allCleared, results[] }`; the SPA calls it once
per failed row (so Retry-all shows per-row progress) and per-row Retry no longer depends on a checkbox
(the selection UI was dropped).

**Status:** Implemented in the product working tree (uncommitted): `CleanupRun.PauseAfterArchival` /
`ResumeAfterArchival`; `IMoveFailureRetryer` + `RunPhaseExecutor.RetryDocumentMovesInlineAsync` (synchronous,
`emitProgress` flag on `MoveDocumentsAsync`); the three `Features/Runs/Archival/*` features (retry returns
per-doc outcomes); SPA `MoveFailuresPanel` (inline per-row status, kept rows, sequential Retry-all) +
`api/runs.ts` client + `JobDetailsView` mount; xUnit tests (run-state transitions, the three handlers via a
`FakeMoveFailureRetryer`, and two executor inline-retry-outcome cases). SPA `tsc` clean; C# validated by
reference/pattern checks — Chase runs `dotnet build`/`dotnet test` + `npm run build` and owns branch/commit/PR.
Plan: `move-failure-retry-plan.md`. Spec + dev-spec updated in step.

---

## [2026-08-11] Fix: Step 8 renames/merges left candidate document paths stale → "source folder not found"

**Context:** A live run surfaced Step 10 move failures reading *"source folder not found"*. Root cause: Step 8b
renames source folders/documents in place and repaths the pending **rename rows**
(`RepathPendingDescendantsAsync` → `CleanupRunRename.UpdatePaths`), but it never repaths the **candidate
documents** (`CleanupRunDocument.DocumentPath`). The archival move (Step 10) addresses each document by its
stored path, which after normalization still pointed at the old (whitespace) folder/name — a path that no
longer exists — so every normalized item's move failed. The same gap hits folder **merges** (the loser's
candidate documents are moved under the survivor but keep the loser path).

**Decision:** During Step 8b, repath the candidate document set in lockstep with each applied change — the
`CleanupRunDocument` counterpart of the existing rename-row repath. After a **folder rename**, rewrite the
path prefix of every candidate document beneath it; after a **document rename**, rewrite the matching
candidate document's leaf; after a **folder merge**, rewrite the loser's candidate documents onto the survivor
path. New `ICleanupRunDocumentStore.UpdatePathsAsync` + `DocumentPathUpdate` persist the changes; the executor
keeps an in-memory candidate list in sync so a later rename/merge matches the current path. Renames address
raw paths and are applied top-down, so replaying them onto the candidate paths reproduces the live path
exactly.

**Follow-ups (both now done, 2026-08-11):**

1. **Salvage the already-failed run (reconcile from the rename log).** A run whose 8b predates the repath fix
   has stale candidate paths persisted, so a panel retry alone still fails. `RunPhaseExecutor.RetryDocumentMovesInlineAsync`
   now first calls `ReconcileCandidateDocumentPathsAsync`, which replays the completed `CleanupRunRename` rows
   (folders top-down, then documents — the 8b order) plus any resolved folder merges onto the candidate
   documents and persists the corrected paths (`UpdatePathsAsync`). Idempotent: on an already-current run the
   raw prefixes no longer match, so nothing changes. So the operator just retries and the run self-heals.

2. **Exclude a deleted duplicate from the move set.** A keep-one/delete-other resolution removes the victim in
   8b; its candidate row is now marked `MoveStatus.Deleted` (matched by the victim's raw path captured before
   the repaths). `GetMovable`/`HasUnmovedDocuments` were changed from `<> 'Moved'` to `IN ('Pending','Failed')`,
   so a `Deleted` candidate is excluded from Step 10 and is neither moved nor counted as a failure — and the
   row is retained (not deleted) so the before/after register ledger and audit still show it as removed.

3. **Deterministic rename order (`CleanupRunRename.Seq`).** `CleanupRunRename.Id` is `NEWID()` and the store
   read `ORDER BY Id` — i.e. a random order — so Step 8b applied renames (and the reconcile replayed them) in a
   non-deterministic order rather than the intended folders-top-down. Added a per-run monotonic `Seq` (assigned
   in plan order in the insert, `MAX(Seq)+1`, mirroring `CleanupRunOperation`); `GetByRunAsync` now orders by
   `Seq` and the index is `IX_CleanupRunRename_RunId_Seq (RunId, Seq)`. Baseline-schema edit (fresh-DB
   convention). This makes ancestors reliably rename before descendants — the repath/reconcile logic already
   held for any fixed order, but a deterministic top-down order removes the latent nested-rename hazard.

**Status:** Implemented in the product working tree (uncommitted): `ICleanupRunDocumentStore.UpdatePathsAsync`
+ `DocumentPathUpdate` + Dapper impl; `RunPhaseExecutor` candidate-doc load + repath helpers wired into the 8b
rename loop and merge loop, `ReconcileCandidateDocumentPathsAsync` (called from the inline retry), and
`ExcludeDeletedDuplicateAsync`; new `MoveStatus.Deleted` with `GetMovable`/`HasUnmoved` narrowed to
Pending/Failed; `CleanupRunRename.Seq` added to the baseline schema + `CleanupRunRenameStore` insert/read
(`ORDER BY Seq`); xUnit tests (folder-rename repath, inline-retry reconcile-then-move, deleted-duplicate
exclusion) + existing stubs updated for the new interface method. **Baseline schema changed → dev DBs need a
reset (fresh-DB convention).** C# validated by reference/pattern checks — Chase runs `dotnet build`/`dotnet
test`. Spec + dev-spec updated in step.

---

## [2026-08-13] Audit trail scoped to Normalization+, protected-folder visibility, Step 6 global bulk actions

**Context:** Four Job Details / Step 6 usability fixes requested together. The operation audit trail was
visible (and its live/full surfaces polled) from the moment a run started, including Identification and the
Step 6/7 review — before the run has done anything auditable (Rule 7: the audit starts where the run starts
mutating the live repository). Its "live" polling was also keyed off `Running || AwaitingInput`, so it kept
polling — and showing an animated refresh spinner — while merely paused for operator input. Separately, the
Step 6 candidate folder list always rendered protected folders inline (Rule 2: never deletable), cluttering
the list the operator actually acts on. And Step 6's only bulk actions ("select/deselect all matching") were
filter-scoped and explicitly excluded pre-selected folders, so there was no way to reset the whole selection.

**Decision:**

1. **Audit trail hidden pre-Normalization, server-enforced.** `CleanupRunOperationStore.BuildFilter` now hard-excludes
   `Phase IN ('Identification','ReviewSelection')` rows from `GetPageByRunAsync`/`GetAllByRunAsync` — a fixed
   WHERE clause, not an operator-facing filter — so `GET .../operations` and its CSV export never surface
   pre-Normalization rows (e.g. the Step 6 `OperatorOverride`) regardless of caller. `JobDetailsView` mirrors
   this: `hasReachedNormalization` (`currentPhase` is not `Identification`/`ReviewSelection`) gates whether
   `LiveActivity`/`FullAuditTrail` mount at all.
2. **Polling narrowed to `Running`; spinner replaced with a static label.** Both surfaces' `live` prop is now
   `run.status === 'Running'` (was `Running || AwaitingInput`) — polling stops the moment the run pauses, not
   just when it finishes. The animated dots/spinner shown during polling is replaced with a static "Polling…"
   text label, present only while `live` and otherwise absent (no flicker, no continuous animation).
3. **Protected folders hidden by default in Step 6.** `Step6FolderReview`'s `filteredItems` now excludes
   `status === 'Protected'` for every status filter except `protected` itself — an operator has to deliberately
   select the Protected chip to see them, instead of them always being inline.
4. **Two new global bulk actions.** `Deselect all` clears every selection including pre-selected folders (and
   marks them overridden, so the row reads "Overridden" and stays editable) — independent of the current
   filter/search, unlike the existing "matching" actions. `Select empty, naming-convention folders` selects
   only folders that are both acronym pre-selected and empty (no documents, no subfolders) — a safe rebuild
   starting point after a full deselect.

**Rationale:** The audit trail's purpose is to record what the run did to the live repository (Rule 7) —
surfacing pre-mutation phases only added noise and made "nothing happened yet" look like a gap in the trail.
Gating it server-side (not just hiding it in the SPA) means the CSV export and any future caller get the same
guarantee. Narrowing polling to `Running` matches "is a process actually running right now" more precisely
than the old `Running || AwaitingInput`, and a static label is cheaper and less distracting than a perpetual
spinner for something that's normally idle. Hiding protected folders by default keeps the Step 6 list focused
on folders the operator can actually act on, while the Protected filter still makes them inspectable on
demand. The two new bulk actions were requested because the existing "matching" actions deliberately exclude
pre-selected folders (by design, per the override model) — there was no in-UI way to zero out the whole
selection and rebuild it from just the empty, acronym-matching set.

**Status:** Implemented in the product working tree (uncommitted): `CleanupRunOperationStore.BuildFilter`
(API); `JobDetailsView.hasReachedNormalization` + `live` narrowing, `OperationAuditPanel`'s spinner → static
"Polling…" label (SPA); `Step6FolderReview` protected-hide filter + `deselectAll`/`selectMatchingEmpty` +
`allDeletableIds`/`emptyPreSelectedIds` memos and their buttons (SPA). `npx tsc -b` passes clean on the SPA;
the API change is a single-line WHERE-clause addition validated by inspection only — no `dotnet` toolchain in
this sandbox, so Chase should run `dotnet build`/`dotnet test` before merging. Spec (`NATA_Document_Lifecycle_Cleaner_Spec_v0.6.md`)
and dev-spec (`dev-spec.md`) updated in step.

---

## [2026-08-13] Step 6 follow-up: split empty/naming-convention bulk action, fix tree tri-state, filter header

**Context:** Same-day feedback on the Step 6 work above. **(1)** The tree view's parent/aggregate checkbox
was wrong for any subtree made up entirely of pre-selected (naming-convention) folders: `subtreeCheckboxState`
computed checked/indeterminate from `TreeNode.selectableIds`, which by design **excludes** pre-selected
folders (they change only via a per-row override) — so a fully-selected all-pre-selected subtree showed a
plain, disabled, unchecked box instead of a tick, and a partially-selected one showed nothing instead of a
dash. **(2)** The prior "Select empty, naming-convention folders" bulk action conflated two different rules
(empty = no documents; naming-convention = acronym pre-select match) into one AND'd action, which is not
what was wanted — they needed to be independent, each selectable on its own. **(3)** The status filter chip
row had per-chip tooltips but no header explaining what the row as a whole does.

**Decision:**

1. **Tree checkbox now reads `TreeNode.deletableIds` (all non-protected descendants, incl. pre-selected) for
   its checked/indeterminate state**, via a new `isEffectivelySelected(f)` helper (pre-selected → `selected[id]
   ?? true`; else → `!!selected[id]`) and a `folderById` lookup map (tree nodes only carry ids). Clicking the
   checkbox still only bulk-toggles `selectableIds` (pre-selected folders still need a deliberate override),
   so it's `disabled` exactly when there's nothing freely selectable — independent of what the tick/dash is
   showing. `protectedSubtreeState` got the same fix for the same reason (a protected ancestor's "selected
   content below it" hint had the identical blind spot).
2. **Split into two independent, self-toggling actions.** `Select empty folders` toggles every unprotected
   folder with `documentCount === 0` (irrespective of acronym match); `Select naming-convention folders`
   toggles every unprotected pre-selected folder (irrespective of document count). Each is a single toggle
   button, not a select/deselect pair: `allEmptySelected`/`allNamingConventionSelected` (derived from
   `isEffectivelySelected` over the target set, no extra state) decide whether the click selects or deselects
   the whole set. Turning pre-selected members off via either toggle also marks them overridden, matching the
   existing per-row override semantics.
3. **Added a two-line header** ("Filter by status" + "Choose which folders the list below shows — this only
   changes what's visible, not what's selected.") above the chip row.

**Rationale:** (1) is a straight bug — the whole point of a tri-state parent checkbox is to reflect the real
selection state of its subtree, and excluding an entire class of descendant (pre-selected) from that
computation defeats it; `selectableIds` is the right target for the *bulk-toggle action* but the wrong source
for the *displayed state*, so the fix separates the two uses of the id lists that had been conflated. (2) two
rules that only partially overlap ("no documents" vs "acronym match") produce a materially different result
set when AND'd vs. offered independently — the operator asked for the latter, and toggling on the observed
current state ("select if not all selected, else deselect") avoids needing a second pair of explicit
select/deselect buttons per criterion. (3) the per-chip tooltips explain *each* option but nothing previously
said what the row as a whole was for.

**Status:** Implemented in the product working tree (uncommitted), all in `Step6FolderReview.tsx`: `folderById`
map, `isEffectivelySelected`, `emptyFolders`/`emptyFolderIds`/`allEmptySelected`,
`namingConventionFolders`/`namingConventionIds`/`allNamingConventionSelected`, `toggleEmptyFolders`/
`toggleNamingConventionFolders` (replacing `selectMatchingEmpty`/`emptyPreSelectedIds`), the rewritten
`subtreeCheckboxState`/`protectedSubtreeState`, and the new filter header. `npx tsc -b` passes clean. Spec
(`NATA_Document_Lifecycle_Cleaner_Spec_v0.6.md`, rev 2) updated in step.

---

## [2026-08-13] Step 6 follow-up 2: unify the four filter-scoped bulk actions onto one scope

**Context:** Further same-day feedback: `Select empty folders` and `Select naming-convention folders`
(added in the previous entry) computed their target sets from the full `folders` list, while `Select all
matching`/`Deselect all matching` were already scoped to `filteredItems` (the path/acronym text filter +
status filter). So typing a filter and clicking "Select empty folders" would select empty folders across
the whole run, not just the ones on screen — inconsistent with the other two buttons sitting right next to
it, and not what "matching" implies.

**Decision:** `emptyFolders`/`emptyFolderIds` and `namingConventionFolders`/`namingConventionIds` are now
derived from `filteredItems` instead of `folders ?? []` — the exact same base the "matching" actions already
used. `allDeletableIds` (the `Deselect all` full-run reset) is untouched and explicitly called out in a
comment as the one action that's meant to ignore the filter. In the UI, the text filter and all four
filter-scoped buttons were moved into a single `Stack`/`Group` so they read as one toolbar, with a caption
below naming the active filter when one is set ("All four buttons above act only on folders currently
matching “…”."); `Deselect all` was pulled into its own row below with an updated tooltip making the
"ignores the filter" behaviour explicit.

**Rationale:** Four controls that visually sit together but only two of them respect the filter is a
correctness trap — an operator narrows the list, expects every button in that toolbar to act on what they're
looking at, and two would have silently reached past it. Reusing `filteredItems` (already the single source
of truth for "what's currently in view") rather than introducing a second filtered-list computation keeps
the four actions provably consistent with each other and with the list below them.

**Status:** Implemented in the product working tree (uncommitted), `Step6FolderReview.tsx` only —
`emptyFolders`/`namingConventionFolders` memo base changed, JSX regrouped into one toolbar `Stack` +
filter-name caption + a separated `Deselect all` row. No functions needed to change (`toggleEmptyFolders`/
`toggleNamingConventionFolders` already read off the memos). `npx tsc -b` passes clean. Spec
(`NATA_Document_Lifecycle_Cleaner_Spec_v0.6.md`, rev 3) updated in step.

---

## [2026-08-13] Fix: Step 10 archived every candidate document, ignoring the Step 6/7 folder selection

**Context:** Reported defect — "the archive step Step 10 is archiving everything rather than only the
selected candidates." Traced end to end (read-only investigation first, via a sub-agent, before touching
anything): `CleanupRunDocument` has no `FolderId`/link back to `CleanupRunFolder` at all, and
`CleanupRunDocumentStore.GetMovableAsync` (Step 10's input) filters only by `MoveStatus IN
('Pending','Failed')` — never by folder selection. Worse, the two candidate sets are independently
computed at identification: Step 1's `GetCandidateDocumentsAsync` scopes documents only by cutoff date +
source domain, with no reference at all to the acronym/protection rules Steps 4–5 use to build
`CleanupRunFolder`. Nothing between identification and archival ever intersects the two — `Confirm
DeletionsHandler` (Step 7) validates Rule 4 (no selected folder may be protected) but never reads
`IsSelectedForDeletion` to narrow the document set. So Step 10 moved every candidate document for the run,
full stop, independent of what the operator checked, unchecked, or overrode at Step 6. (Step 11's folder
delete was **not** affected — `CleanupRunFolderStore.GetDeletableAsync` already filters
`WHERE IsSelectedForDeletion = 1` — so an unselected folder was never itself deleted, only needlessly
emptied first.)

**Decision:** Close the gap at the one point in the pipeline where the final selection state is already
being read and validated — `ConfirmDeletionsHandler`, right after the Rule 4 check and before
`StartNormalizationAnalysis` is enqueued:

1. Build the selected-folder-path set from the already-loaded `CleanupRunFolder` rows
   (`IsSelectedForDeletion`), `StringComparer.OrdinalIgnoreCase` to match the comparer used for folder
   paths elsewhere in the pipeline.
2. Load every still-`Pending` `CleanupRunDocument` (`GetByMoveStatusAsync`) — nothing has moved yet at
   Step 7, so this is the whole candidate set.
3. For each, compute its containing folder via the existing `RunPhaseExecutor.ParentPath(path)` helper
   (already `internal static`, already used by the Step 10 batching/grouping code — no new path-parsing
   logic introduced) and check membership in the selected set.
4. Anything not selected (or with a null path, defensively) is set to a **new terminal `MoveStatus.Kept`**
   via the existing `UpdateMoveResultsAsync` — the exact call shape Step 8's keep-one/delete-other
   resolution already uses for `MoveStatus.Deleted`. `Kept` sits outside `GetMovable`/
   `HasUnmovedDocuments`'s `IN ('Pending','Failed')`, so it needed **no SQL change** to either query — the
   exclusion is automatic. It also flows into the before/after Document Register ledger unmodified
   (`Disposition = MoveStatus.ToString()`), so a kept document shows as `"Kept"` for free.

**Rationale:** The alternative — filtering inside `GetMovableAsync`/Step 10 itself via a live join against
`CleanupRunFolder` — would need a document→folder link that doesn't exist in the schema (`DocumentPath`
prefix matching against `FolderPath`, computed fresh on every archival read/resume). Doing it once at
confirm, by reusing the `Deleted`-status precedent, needed no schema change, no new store method, and no
change to the two SQL queries Step 10/11 already rely on — `Kept` documents are invisible to them simply
because they're not `Pending`/`Failed`. Projecting once at the single moment the final selection is known
(Step 7 confirm, before any mutation) is also the natural place: Normalization's later repathing
(`UpdatePathsAsync`) still applies to `Kept` documents same as any other, keeping their recorded path
accurate for the register even though they'll never move.

**Status:** Implemented in the product working tree (uncommitted). API: `Domain/MoveStatus.cs` (+`Kept`),
`ConfirmDeletionsHandler` (+`ICleanupRunDocumentStore documents` dependency, the projection block). No
changes needed to `CleanupRunDocumentStore`, `RunPhaseExecutor`, or any SQL — `Kept` is excluded from the
move/gate queries by construction. Tests: `ConfirmDeletionsHandlerTests` — new
`Marks_documents_under_an_unselected_folder_as_Kept_and_leaves_selected_ones_pending`, plus the shared
`Handler(...)` helper updated to take the (now required) document store with a default `Fake
CleanupRunDocumentStore()` so the existing tests needed no other changes. No `dotnet` toolchain in this
sandbox — Chase should run `dotnet build`/`dotnet test` before merging. Spec
(`NATA_Document_Lifecycle_Cleaner_Spec_v0.6.md`, rev 4) and dev-spec (`dev-spec.md`) updated in step.

---

## [2026-08-13] Follow-up: the Kept-exclusion fix itself made Confirm hang on a real run

**Context:** Chase clicked "Confirm & start archival" against a real run and it hung — spinner, no visible
progress. Root cause was the fix above: it reused `ICleanupRunDocumentStore.UpdateMoveResultsAsync` to
write `MoveStatus.Kept`, but that method passes an array of per-document parameter objects to Dapper's
`ExecuteAsync`, which multi-execs — **one round trip to SQL Server per document**, not one batched
statement. That shape is fine for its original purpose (a Step 10 move batch, `ArchivalBatchSize = 25`,
processed incrementally in the background); it is not fine run synchronously, inside the Step 7 confirm
HTTP request, against the *entire* candidate document set — a run with thousands of documents meant
thousands of sequential round trips before the request could return, which is indistinguishable from a
hang from the operator's side. This was missed in the original fix because the correctness tests (in-memory
fakes) don't have a "how many round trips" dimension to catch it, and the sandbox here has no `dotnet`
runtime to load-test against a real SQL Server.

**Decision:** Added a dedicated `ICleanupRunDocumentStore.ExcludeAsync(documentRowIds, ct)` — a single
`UPDATE dbo.CleanupRunDocument SET MoveStatus = 'Kept' WHERE Id IN @ids` per **chunk of 1,000 ids** (well
under SQL Server's ~2,100 parameter cap), so a run with N excluded documents costs `ceil(N/1000)` round
trips instead of N. `ConfirmDeletionsHandler` now calls this instead of building a `DocumentMoveResult`
list through `UpdateMoveResultsAsync`. As a side benefit this also fixed a semantic wrong in the original
fix: `UpdateMoveResultsAsync` unconditionally increments `AttemptCount` and stamps `LastAttemptAt` — correct
for an actual move attempt, wrong for a document that was excluded before ever being attempted.
`ExcludeAsync` touches only `MoveStatus`.

**Rationale:** Bulk state transitions that can scale with the candidate set (which the spec explicitly
sizes at "tens of thousands") must be O(chunks), not O(rows), in round trips — the existing
`GetPageByRunAsync`/`GetAllByRunAsync` paging on the operation audit trail and the `AppendManyAsync`
bulk-insert on `CleanupRunOperation` already follow this rule; `UpdateMoveResultsAsync`'s per-row loop was
only ever exercised at small batch sizes before, so the anti-pattern was latent until this fix used it at
full-candidate-set scale. A dedicated, correctly-shaped method is clearer than trying to retrofit chunking
onto `UpdateMoveResultsAsync`, which still needs its current one-row-worth-of-different-values shape for
real move results (status **and** failure reason vary per row; `ExcludeAsync` only ever sets one fixed
status, which is exactly what makes the `IN (...)` chunking possible).

**Status:** Implemented in the product working tree (uncommitted). API:
`ICleanupRunDocumentStore.ExcludeAsync` (interface + Dapper impl in `CleanupRunDocumentStore`),
`ConfirmDeletionsHandler` updated to call it. Tests: `FakeCleanupRunDocumentStore.ExcludeAsync` added; the
existing `Marks_documents_under_an_unselected_folder_as_Kept_...` test needed no changes (same observable
outcome, just via a different store method). No `dotnet`/SQL Server available in this sandbox to measure
actual round-trip counts — Chase should verify against a real run with a non-trivial candidate set before
relying on this. Spec (`dev-spec.md`) updated in step.

---

## [2026-08-13] Feature: archive destination splits into Library vs Folder

**Context:** The archive destination (Step 9) only ever let the operator pick a **library** — "create
new" (name a library, optionally type a free-text subfolder with no validation) or "choose existing"
(pick from the live list, then browse one level at a time into a real subfolder, Story 34528). Chase asked
to make it a first-class choice between a library and a folder, in both the API and the SPA. Presented
three restructuring options (library/folder as the top-level toggle; folder as a third tab alongside
create/existing; or just add browsing to the create-new tab) — Chase picked the top-level toggle.

**Decision:**

1. **API contract** — `ArchiveLibrarySelection` gained `DestinationType` (`"library"`|`"folder"`) and
   `FolderPath` (replacing `SubfolderPath`); `Mode` (`"create"`|`"existing"`) is now only meaningful for
   `DestinationType == "library"`. `ConfirmDeletionsHandler`'s validation switches on `DestinationType`
   first: `library` reuses the existing create/existing `Mode` branch (root only —
   `ArchiveSubfolderPath` is always set to `null`); `folder` requires a non-empty `LibraryId`+`LibraryName`
   (a `folder` destination can never create a brand-new library in the same step — it always targets one
   that already exists) and a non-empty `FolderPath`, which flows straight into the existing
   `CleanupRun.ArchiveSubfolderPath`. **No changes** to `CleanupRun`, the DB schema, or
   `RunPhaseExecutor`'s `BuildDestinationPath`/`EnsureArchiveDestinationAsync` — those already treat
   `ArchiveSubfolderPath` as an opaque forward-slash path and already create missing folder levels on
   demand, regardless of how the path was chosen. The whole feature is a request/validation-layer
   reshaping onto an unchanged domain/pipeline.
2. **SPA** — `Step8ArchiveLibraryModal` restructured around a top-level `Library`/`Folder`
   `SegmentedControl`. **Library**: the existing create/existing sub-toggle, minus the subfolder field
   (root only now — that's the whole point of splitting Folder out). **Folder**: reuses the same
   library-picker list/filter component as Library/existing, then the existing one-level subfolder
   browser (`GET /libraries/folders?path=`), **plus a new "New folder name" text input** that lets the
   operator type a name to append at the currently-browsed level — closing a real gap, since before this
   there was no way to create a not-yet-existing folder while browsing an existing library (only the
   create-new-library tab's blind free-text field could do that, and only at the library root level).
3. Corrected a stale spec/dev-spec route (`GET /api/libraries/{libraryId}/folders`) found while
   documenting this to match the actual implementation (`GET /libraries/folders?path=`), per this
   project's spec-must-match-repo convention — unrelated to the feature itself but caught in passing.

**Rationale:** Reworking the request layer only, and leaving `CleanupRun`/`RunPhaseExecutor` untouched, is
the minimum-risk shape here — the two "kinds" of destination the operator now picks between were already
representable as `(ArchiveLibraryId, ArchiveLibraryName, ArchiveSubfolderPath)` triples; the gap was purely
in how the operator expressed the choice, not in what the pipeline could already do with it once expressed.
Requiring an existing library for `folder` (rather than also supporting "create a library and target a
folder in it") keeps the validation simple and matches how the SPA's browsing UI naturally works — you
can't browse subfolders of a library that doesn't exist yet.

**Status:** Implemented in the product working tree (uncommitted). API:
`ArchiveLibrarySelection.cs`, `ConfirmDeletionsRequest.cs` (default), `ConfirmDeletionsHandler.cs`
(destination-type switch). Tests: `ConfirmDeletionsHandlerTests` — updated `Command()` to build a
`library`-typed selection, added `FolderCommand()`, and four new/changed tests covering a successful
folder destination, a missing-library/missing-folder-path rejection, and an unknown `destinationType`
rejection. SPA: `api/runs.ts` (`ArchiveLibrarySelection` interface), `Step8ArchiveLibraryModal.tsx`
(full restructure), `Step7ConfirmDeletions.tsx` (destination summary line). `npx tsc -b` passes clean. No
`dotnet` toolchain in this sandbox — Chase should run `dotnet build`/`dotnet test` before merging. Spec
(`NATA_Document_Lifecycle_Cleaner_Spec_v0.6.md`, rev 5) and dev-spec (`dev-spec.md`) updated in step.

---

## [2026-08-13] Fix: a "folder" archive destination's pre-existing ancestor chain wasn't normalized

**Context:** Chase asked to double-check that name normalization — which Step 8 already applies to
*source* items — also protects the *destination* side once a "folder" destination (the entry above) lets
the operator target a folder several levels deep in an existing library, not just the library root. A
pre-existing MAGIQ folder anywhere in that ancestor chain (one this run did not create) can carry the same
whitespace/invisible-character problem Step 8 fixes for source items — plausible here specifically because
the folder path was captured by browsing/typing in the Step 8 modal, which reads/echoes real MAGIQ folder
names verbatim. Root-caused: `EnsureFolderPathAsync` (Step 9) checks/creates against the **normalized**
composed path, but SOAP requires the **exact raw stored name** to address an existing item (the same
addressing rule Story 34525/34527 established for source renames). So a dirty pre-existing ancestor would
not be found by `FolderExistsAsync` — risking a duplicate "clean" folder being created alongside the dirty
one, a hard `CreateFolder` failure, or (later) a Tier 2 rollback move-back that can't resolve the same
path. This gap existed only for a `folder` destination — a `library` destination's path is always the
library root, so there was nothing to walk.

**Decision:**

1. **New `RunPhaseExecutor.NormalizeArchiveDestinationAncestorsAsync`**, called from
   `EnsureArchiveDestinationAsync` immediately before `EnsureFolderPathAsync`. Walks
   `run.ArchiveSubfolderPath`'s segments top-down from the library root. For each segment still known to
   exist: if its raw name is dirty (`MagiqPath.Normalize` differs), rename it in place with the same
   Get-then-Update pair Step 8's `ApplyRenameAsync` uses, and audit it as a Step 9 `Rename` operation row.
   Once a segment is found not to exist, every remaining segment is normalized **in memory only** (never
   sent dirty to `CreateFolderAsync`) — covers an operator-typed brand-new folder name the same way,
   without a separate code path. If anything changed, the corrected path is persisted via a new
   `CleanupRun.SetArchiveSubfolderPath` mutator (mirrors `SetArchiveLibraryId`), so `EnsureFolderPathAsync`
   right after, a resumed run, and a Tier 2 rollback move-back all address the corrected name.
2. **No separate confirm-time (Step 7) normalization.** Considered and rejected: at confirm time the app
   doesn't yet know via SOAP which segments of the chosen path already exist, so blindly normalizing there
   could rewrite the address of a pre-existing dirty ancestor *before* Step 9 gets a chance to detect and
   rename the real folder — the wrong fix, applied at the wrong layer. The Step 9 pass above already covers
   an operator-typed new segment correctly (case 2 above), so no client- or request-side normalization was
   added.
3. **Known residual gap, left open (not this fix): the archive library's own name.** When the operator
   adopts an *existing* library by id (either destination type), the library name itself is never checked
   or renamed — `CreateDomain`/adopt-by-name is skipped entirely once `ArchiveLibraryId` is set, and that is
   a different code path than the one this fix touches. A dirty existing library name is a smaller, rarer
   risk (library names get far less casual free-text pasting than folder paths) but is not yet covered.
   Flagging here rather than silently ignoring it, per this project's spec-honesty convention.

**Rationale:** Reusing the exact Get-then-Update rename mechanism and audit shape Step 8 already uses
keeps this consistent with the established normalization pattern rather than inventing a second one.
Doing the walk inside `EnsureArchiveDestinationAsync` means both its call sites (the main archival flow and
`RetryDocumentMovesInlineAsync`'s inline retry) benefit automatically with no extra wiring. Persisting the
correction onto the run (rather than only using it for one call) is what makes a later resume or rollback
safe — those read `run.ArchiveSubfolderPath` fresh, not a value carried only in a local variable.

**Status:** Implemented in the product working tree (uncommitted; product repo, not committed by Claude —
Chase owns git per this project's working agreement). Files: `Domain/CleanupRun.cs`
(`SetArchiveSubfolderPath`), `Pipeline/RunPhaseExecutor.cs`
(`NormalizeArchiveDestinationAncestorsAsync` + the call site in `EnsureArchiveDestinationAsync`). Tests:
new `RunPhaseExecutorArchiveDestinationNormalizationTests.cs` — a dirty pre-existing ancestor is renamed
and the run's path corrected; a clean pre-existing ancestor is left untouched (no SOAP rename call, no
audit row); a not-yet-existing (operator-typed) segment is normalized before `CreateFolder` ever sees it.
No `dotnet` toolchain in this sandbox — Chase should run `dotnet build`/`dotnet test` before merging. Spec
and dev-spec updates for this fix are the next step (this entry).

---

## [2026-08-13] Feature: new-run source scope narrows from the whole library to a starting folder

**Context:** Chase reported "New run doesn't allow me to select the starting folder, still only the
library." Investigation found this was never built, not a regression — Story 34566 gave the new-run form
a source *library* picker (`SourceDomainId`/`SourceDomainName` on `CleanupRun`), but no folder-level
scoping ever existed: `CreateRunRequest`/`CreateRunCommand`/`CleanupRun.Create` had no folder field, and
the three configured queries (`CandidateDocuments`, `CandidateFolders`, `DocumentRegister`) bind only
`@specifiedDate`/`@sourceDomainId`. Confirmed with Chase before building: (1) build it, (2) a chosen
starting folder scopes to that folder **and its full subtree** (not just its immediate contents), (3) it's
**optional**, defaulting to the original whole-library scope.

**Decision:**

1. **In-app path-prefix filter, not a bound SQL parameter.** Considered adding `@sourceFolderId` to the
   configured queries the way `@sourceDomainId` was bound (Story 34566/34550's pattern) — rejected. MAGIQ's
   SOAP surface addresses folders and documents by **path only** (Move/CreateFolder/GetFolder all take a
   path, never an id — ADR-004/011), and the operator picks the starting folder by **browsing** (same
   one-level `GET /libraries/folders?path=` browser Step 8/9's "Folder" destination uses), which likewise
   only ever returns folder names/paths, never a MAGIQ `FOLDERID`. There is no id to bind cleanly. Instead,
   `RunPhaseExecutor` fetches the (still whole-library) query results exactly as before, then filters them
   in-app by path prefix — `BuildSourceScopePrefix`/`IsWithinSourceScope`, comparing `MagiqPath.Normalize`d
   paths against `/{SourceDomainName}/{SourceFolderPath}` — before persisting. **No change to any
   operator-configured SQL** (ADR-004 stays intact — the app still holds zero MAGIQ schema/scope logic).
2. **Where the filter is applied.** Step 1 candidate documents: filtered right after the query returns,
   before batching into `CleanupRunDocument`. Step 4-5 candidate folders: `CandidateFolderBuilder.Build` is
   still run over the **full unscoped** ancestor rows first (protection propagation, Rule 2, needs the
   complete ancestor chain to be correct), and only the *output* `CandidateFolder` list is narrowed to
   scope afterward — an out-of-scope ancestor can still end up flagged `Protected` in the process, but
   since it was never a deletion candidate that's inert. Step 8 normalization's raw-path fetches (both the
   dry-run analysis and the folder-merge descendant expansion) go through a new shared
   `GetScopedRawCandidateDocumentPathsAsync` so a scoped run never proposes renaming something outside the
   subtree it was asked to cull.
3. **Known, documented limitation: the Document Register (Step 2) is not scoped.** Its rows are
   `IReadOnlyDictionary<string, object?>` with fully operator-defined columns (no guaranteed path column to
   filter on), so there's no reliable generic way to prefix-filter it the way typed candidate
   documents/folders are filtered. A folder-scoped run's downloaded "before" register still reflects the
   whole source library. Flagged in code and here rather than silently narrowing incorrectly or leaving it
   undocumented.
4. **New `CleanupRun.SourceFolderPath` (nullable string), not a separate folder-id column.** Mirrors the
   reasoning in point 1 — there's no id to store. `null` means the original whole-library scope; a non-null
   value is the raw MAGIQ folder path (as returned by the browse endpoint, which returns true raw names)
   relative to the library root, trimmed of leading/trailing slashes at `Create`. A genuine forward-only
   migration (`0002_source_folder_scope.sql`) adds the column — unlike earlier schema changes, this one is
   **not** folded back into the `0001` baseline, since the app is now as-built/merged (Epic 34120), not
   pre-release.
5. **SPA:** `NewRunForm.tsx` gained a `Whole library` / `Starting folder` toggle, shown once a source
   library is picked. "Starting folder" reuses the same one-level folder-browse UX as the Step 8/9 "Folder"
   destination picker (minus its "new folder name" field — a *starting* folder must already exist; there's
   nothing to scope to if it doesn't). Changing the source library resets any browsed folder scope, since
   it was browsed under the old library. `RunSummary`/`JobDetailsView` surface the chosen scope for
   display.

**Rationale:** The id-vs-path mismatch is the crux of the design — MAGIQ simply doesn't expose a folder id
anywhere the operator-facing browse flow could capture, so a bound-parameter design (consistent with how
`@sourceDomainId` was done) isn't available without inventing a path→id resolution query that doesn't
otherwise need to exist. Filtering in-app after the existing whole-library queries run is simple, requires
zero SQL changes (so it can never conflict with NATA's own edits to the configured queries), and is cheap
at this tool's actual scale (one facility, annual run, in-memory list filtering). Running
`CandidateFolderBuilder.Build` over the *full* ancestor rows before narrowing preserves Rule 2's
correctness exactly — the alternative (filtering rows before Build) would have needed to reason carefully
about whether protection propagation could ever need an out-of-scope ancestor, which it structurally
cannot (protection only flows upward from a folder to its ancestors, never sideways or downward), but
narrowing after is simpler to verify and equally correct.

**Status:** Implemented in the product working tree (uncommitted; product repo, not committed by Claude).
API: `Domain/CleanupRun.cs` (`SourceFolderPath` + `Create`/`Restore`), `Persistence/CleanupRunStore.cs`,
`Persistence/Migrations/0002_source_folder_scope.sql`, `Features/Runs/CreateRun/*`,
`Features/Runs/RunSummary.cs`, `Pipeline/RunPhaseExecutor.cs` (`BuildSourceScopePrefix`,
`IsWithinSourceScope`, `GetScopedRawCandidateDocumentPathsAsync`, and the filters applied around the Step
1/4-5 fetches), `Features/Runs/ExportRegister/RegisterExportJob.cs` (limitation comment only). SPA:
`api/runs.ts` (`RunSummary.sourceFolderPath`, `createRun`), `components/NewRunForm.tsx` (folder browser),
`pages/JobDetailsView.tsx` (scope display). Tests: `CleanupRunTests` (Create trims/normalizes the scope),
`CreateRunHandlerTests` (captures the optional scope), new
`RunPhaseExecutorIdentificationScopeTests.cs` (scoped run persists only in-subtree documents/folders;
unscoped run is unaffected). `npx tsc -b` passes clean. No `dotnet` toolchain in this sandbox — Chase
should run `dotnet build`/`dotnet test` and apply the new migration before merging. Spec and dev-spec
updated in the same unit of work (below).

---

## [2026-08-13] Fold 0002_source_folder_scope.sql back into the baseline

**Context:** Chase asked to fold the `SourceFolderPath` migration into `0001_baseline.sql` and delete the
interim `0002_source_folder_scope.sql`, since he's recreating the database from scratch rather than
upgrading an existing one — the same move made on 2026-07-30 for the source-domain columns.

**Decision:** `CleanupRun.SourceFolderPath NVARCHAR(1000) NULL` moved into the `CleanupRun` table
definition in `0001_baseline.sql` (next to `ArchiveSubfolderPath`), and the baseline's header comment
updated to record the fold, matching the existing "formerly migrations 0002–0004" convention. The interim
script's *content* was replaced with a no-op/superseded marker rather than the file being deleted:
**the sandbox this edit was made from could not delete or rename the file** (`rm`/`mv` both returned
"Operation not permitted" on this mount, even for a freshly created test file — a one-way sync mount that
doesn't propagate deletes back to the Windows host, distinct from the write path which works fine).

**Chase needs to manually delete** `src\DocumentLifecycleCleaner.Api\Persistence\Migrations\0002_source_folder_scope.sql`
before recreating the database — its current no-op content is harmless if left in place (DbUp would just
journal an empty script), but it should not linger as a stray file.

**Status:** `0001_baseline.sql` updated (schema + header comment); `0002_source_folder_scope.sql` content
neutralized, pending Chase's manual delete. No other files affected — the C# `CleanupRunStore` column
list/SQL already referenced `SourceFolderPath` unconditionally, so nothing there depends on which script
created the column.

---

## [2026-08-13] New-run source picker restructured to match the Step 8/9 Library/Folder picker

**Context:** The starting-folder-scope feature above shipped `NewRunForm.tsx` with a plain Mantine
`Select` for the source library plus a "Whole library"/"Starting folder" toggle underneath. Chase asked
for "a library and folder picker" on the new-run form; clarified interactively that the request was to
match the **Step 8/9 archive-destination picker's actual UI** (a top-level Library/Folder
`SegmentedControl`, both branches sharing a browsable library list with archive/hidden icons and a filter
box — `Step8ArchiveLibraryModal`'s `renderLibraryPicker`), not just add folder-scoping capability, which
already existed.

**Decision:** `NewRunForm.tsx` rewritten around the same structure as `Step8ArchiveLibraryModal`: a
top-level **Library** / **Folder** `SegmentedControl` (renamed from "Whole library"/"Starting folder"),
both branches sharing one browsable library-list component (filter `TextInput`, standard/archive/hidden
icon legend, scrollable clickable rows) ported from the Step 8 modal. **Library** culls the whole chosen
library (unchanged scope); **Folder** additionally browses one level at a time into the chosen library
(Story 34528's browser, already reused) and narrows to the selected folder + subtree — no "new folder
name" field, since (unlike an archive destination) a *starting* folder must already exist. One
intentional divergence from Step 8's exact behaviour: switching between Library/Folder does **not** reset
an already-picked library (Step 8 resets on switch because Library/Folder there are truly different
destinations; here the same library is almost always what the operator wants regardless of scope, so only
the browsed folder segments reset).

**Rationale:** Reusing the established picker look/interaction keeps the new-run flow visually consistent
with the archive-destination flow the operator already knows, rather than introducing a second bespoke
"library selector" pattern in the same app.

**Status:** Implemented in the product working tree (uncommitted). File:
`components/NewRunForm.tsx` (full rewrite; no API/domain changes — this is UI-only, the
`sourceFolderPath` wire-up from the previous entry is unchanged). `npx tsc -b` passes clean.

---

## [2026-08-13] Library/folder browser moved to a DB-backed catalog; name filter + path typeahead added

**Context:** Chase asked to update the library/folder browser (`NewRunForm.tsx`'s new-run source
picker and `Step8ArchiveLibraryModal.tsx`'s archive-destination picker — both share the same
`GET /libraries` / `GET /libraries/folders` endpoints) to query the database instead of live MAGIQ
SOAP (`ListDomainsAsync`/`ListFoldersAsync`), and to add a name filter plus a typeahead path textbox
that can select a path directly.

There is no existing catalog table for the full MAGIQ library/folder tree — `dbo.CleanupRunFolder`
(Steps 4–5's per-run candidate-folder snapshots) was the closest fit and, on discussion, is the one
Chase chose to reuse/adapt rather than building a new SOAP-synced catalog. Two consequences of that
choice were surfaced and resolved with Chase directly before implementing:

1. `CleanupRunFolder` has no domain/library id column (only `FolderId`/`FolderPath`), but
   `CreateRunCommand`/the identification pipeline requires a numeric `SourceDomainId`. **Resolved:**
   the library picker is DB-backed (name only); `CreateRunHandler` resolves the live MAGIQ domain id
   via a single SOAP `GetDomains` call at submit time, keyed by the picked name, and fails fast with
   `404 SourceLibraryNotFound` if the name no longer resolves (renamed/deleted library). The Step 8/9
   archive-destination confirm path needed no equivalent change — it already tolerated a `null`
   SOAP-sourced id and falls back to addressing the destination by name.
2. `IsHidden`/`IsArchive`/a real `Id` are SOAP-only facts `CleanupRunFolder` never recorded — the
   picker's archive/hidden icon distinction is lost (both flags are now always `false`, `Id` always
   `null`, per `LibraryView`'s updated doc comment). Accepted as a known trade-off of this data source,
   not fixed here.

**Decision:**
- New `IFolderCatalogStore`/`FolderCatalogStore` (Dapper, direct SQL — not `IConfiguredQueryStore`,
  which is reserved for MAGIQ's external schema, not DLC's own `dbo.CleanupRunFolder`) derives library
  names and one-level-at-a-time child folders from every run's recorded `FolderPath` values
  (`/{Library}/{...}` convention), plus a `SearchPathsAsync` for the typeahead. Registered in
  `Program.cs`.
- `ListLibrariesEndpoint`/`ListLibraryFoldersEndpoint` repointed from `IMagiqSoapClient` to
  `IFolderCatalogStore`; both gained an optional `nameFilter` query parameter (substring match,
  server-side) and dropped their UI-ticket requirement (no SOAP call left to authorise).
- New `GET /libraries/paths?term=` (`SearchLibraryPathsEndpoint`) returns known paths containing the
  typed term, for the new "jump to a path" `Autocomplete` in both pickers — `onOptionSubmit` parses
  the picked path into library + folder segments and jumps straight there instead of browsing level
  by level.
- `CreateRunRequest`/`CreateRunCommand` dropped `SourceDomainId` (the frontend has none to send);
  `CreateRunHandler` now takes `IMagiqSoapClient` + the operator's UI ticket and resolves the id itself.
- Frontend: `NewRunForm.tsx` and `Step8ArchiveLibraryModal.tsx` both gained a debounced (300ms,
  `@mantine/hooks` `useDebouncedValue`) server-side name filter on the folder level (the library level
  already had a filter box; it's now server-side too instead of an in-memory `.filter()`), and the
  path-typeahead `Autocomplete` (pattern copied from `OperationAuditPanel.tsx`'s existing path-filter
  typeahead).

**Rationale:** Reuses existing infrastructure (`dbo.CleanupRunFolder`, already populated every run)
instead of standing up a new SOAP-synced cache, per Chase's explicit choice — trades live-truth
fidelity (a library/folder with no run history yet won't appear until a run touches it) and the
hidden/archive icon distinction for a browser that's fast and independent of MAGIQ availability.
Resolving the domain id at submit time (rather than browse time) keeps `CreateRun`'s correctness
guarantee intact — a stale id from a slow browsing session can never be persisted onto a run.

**Status:** Implemented in the product working tree (uncommitted). Backend:
`Persistence/IFolderCatalogStore.cs`, `Persistence/FolderCatalogStore.cs`, `Program.cs` (DI);
`Features/Libraries/ListLibraries/*`, `Features/Libraries/ListLibraryFolders/*` (rewired);
`Features/Libraries/SearchLibraryPaths/*` (new); `Features/Runs/CreateRun/*` (domain-id resolution).
Tests: `Fakes/FakeMagiqSoapClient.cs` gained a settable `Domains` result;
`Features/Runs/CreateRunHandlerTests.cs` updated for the new constructor/command shape plus a new
`SourceLibraryNotFound` case. Frontend: `api/libraries.ts`, `api/runs.ts`, `components/NewRunForm.tsx`,
`wizard/Step8ArchiveLibraryModal.tsx`. `npx tsc -b` passes clean; the API side could not be built in
this sandbox (no .NET SDK/network available to install one) — a `dotnet build`/test pass is still
needed before this is considered verified.

---

## [2026-08-14] Library list reverted to live SOAP; folder browsing/typeahead stay DB-backed

**Context:** The previous entry moved both the library list and the one-level folder browser onto a
DB-backed catalog (`dbo.CleanupRunFolder`). Chase asked to get libraries from SOAP again "so we can
get their names" — i.e. the DB catalog's name-only, no-id/no-flags view of libraries wasn't good
enough; a library needs its real MAGIQ name/id/hidden/archive facts, which only `GetDomains` has.

**Decision:** `GET /libraries` (`ListLibrariesEndpoint`/`Handler`/`Query`) reverted to calling
`IMagiqSoapClient.ListDomainsAsync` directly (as before the previous entry), restoring the UI-ticket
requirement, real `Id`, and real `IsHidden`/`IsArchive`. The `nameFilter` query parameter added in the
previous entry is kept, now applied as an in-memory filter over the SOAP result rather than a SQL
`LIKE`. `GET /libraries/folders` and `GET /libraries/paths` (the one-level folder browser and the
path typeahead) are **unchanged** — they stay DB-backed against `dbo.CleanupRunFolder`, since folder
browsing has no id/hidden/archive concern and the DB source is still faster/SOAP-independent there.

Consequences of the library list needing a real id again: `CreateRunRequest`/`CreateRunCommand`/
`CreateRunHandler` reverted to trusting a `sourceDomainId` sent directly from the picker (the
SOAP-resolve-at-submit-time safety net from the previous entry was removed — Chase's call, since the
id is fresh from SOAP every time the picker loads, same as the original pre-catalog design).
`IFolderCatalogStore.ListLibraryNamesAsync`/its SQL/its fake were deleted as dead code (folder
browsing and the typeahead never needed a library-*names* method — `ListChildFoldersAsync`/
`SearchPathsAsync` are the ones actually used, and both remain). One follow-on wrinkle: the path
typeahead (still DB-backed) can surface a library name the *current* SOAP-backed `libraries` list
doesn't have loaded (e.g. filtered out) — `NewRunForm.tsx`'s `jumpToPath` now does a fallback
exact-name `listLibraries` lookup to recover a real id in that case, leaving `id: null` (submission
blocked) only if the name no longer resolves in MAGIQ at all.

**Rationale:** A library is a MAGIQ-native concept (id, hidden/archive flags) that only MAGIQ itself
can authoritatively answer; the DB catalog's "names seen in past runs' folders" view was a reasonable
proxy for folder-level browsing but the wrong source of truth for the library picker itself. Folder
browsing is different — MAGIQ never exposed subfolder ids anyway (addressed by path, not id), so the
DB catalog's blind spots (no run history yet) are a fair trade there for speed/availability, but not
for the top-level library list.

**Status:** Implemented in the product working tree (uncommitted). Reverted:
`Features/Libraries/ListLibraries/*` (back to `IMagiqSoapClient`, `nameFilter` kept),
`Features/Runs/CreateRun/*` (back to `sourceDomainId` in the wire contract, no SOAP resolution),
`Persistence/IFolderCatalogStore.cs`/`FolderCatalogStore.cs` (dropped `ListLibraryNamesAsync`),
`api/runs.ts` (`createRun` takes `sourceDomainId` again), `components/NewRunForm.tsx` (`jumpToPath`
resolves a real id via SOAP-backed `listLibraries`, `canSubmit`/`submit` gate on `source.id !== null`
again). `Step8ArchiveLibraryModal.tsx` needed no logic change (it already tolerated a null id from
SOAP). Tests: `CreateRunHandlerTests.cs` reverted to the non-SOAP shape;
`Features/Libraries/ListLibrariesHandlerTests.cs` rewritten against `FakeMagiqSoapClient`;
`Fakes/FakeFolderCatalogStore.cs` dropped its now-unused library-names method.
`ListLibraryFoldersHandlerTests.cs`/`SearchLibraryPathsHandlerTests.cs` (folder browsing/typeahead)
are unaffected. `npx tsc -b` passes clean; the API side still could not be built in this sandbox (no
.NET SDK/network available) — a `dotnet build`/test pass is still needed before this is considered
verified.

---

## [2026-08-14] Folder browser redesigned: live FOLDERS/FOLDERMAP queries + OneDrive-style UI

**Context:** Chase asked for two changes together: (1) a nicer folder-picker design, shared between
`NewRunForm.tsx` and `Step8ArchiveLibraryModal.tsx`, modelled on the OneDrive "Move to" picker
(breadcrumbs, search, clean folder list); (2) the folder-listing query wasn't what he meant — not a
cache of previously-culled candidate folders, but a proper query against MAGIQ's own `FOLDERS`/
`FOLDERMAP` tables (SQL-QUERY-DESIGN-34547.md's schema — `FOLDERMAP` is the ancestor/descendant
closure table keyed `(PARENTID, FOLDERID, DEEP)`).

**Decision:**

1. **Three new configured MAGIQ queries** (`ConfiguredQueryKeys`/`ConfiguredQueryDefaults`, seeded like
   the original four — Story 34550's pattern, admin-editable, never hardcoded per-request):
   - **`FolderChildren`** — immediate children of `@parentId` within `@domainId`. A root-level
     folder's `PARENTID` equals its `DOMAINID` (Q4 of SQL-QUERY-DESIGN-34547.md), so root browsing is
     just `@parentId = @domainId` — no special-cased "root" branch anywhere in the stack. Also returns
     `FolderCount` (has-children affordance) and `DocumentCount`.
   - **`FolderSearch`** — folders in `@domainId` whose name contains `@term`, with the same
     `FOLDERMAP`-built `FolderPath` as the original `FolderPaths` query, for the browser's "jump to a
     folder" search.
   - **`FolderAncestors`** — the ordered ancestor chain (root first, folder itself last) for a single
     `@folderId`, via the same closure-table pattern as path-building but returning rows instead of a
     concatenated string — rebuilds the browser's breadcrumb trail after a search jump.
   - `MagiqSchemaProbe`/`SchemaContracts` extended so schema verification covers all seven queries now
     (six new parameters — `domainId`/`parentId`/`folderId`/`nameFilter`/`term`/`maxResults` — supplied
     unconditionally alongside the original two, matching the probe's existing loose style).
2. **New `IMagiqFolderBrowseQueries`/`MagiqFolderBrowseQueries`** (`Integration/Magiq/Sql`, mirroring
   `MagiqDocumentQueries`'s configured-query/executor pattern) — `GetChildFoldersAsync`,
   `SearchFoldersAsync`, `GetFolderAncestorsAsync`. Builds the escaped `%term%` LIKE pattern in C#
   (never concatenated into SQL); a blank search term short-circuits without a round trip.
3. **`GET /libraries/folders` contract changed** from `?path=` (a path string) to
   `?domainId=&parentId=&nameFilter=` — folders are now addressed by id, not path text, since MAGIQ
   itself addresses them that way and it composes correctly with the closure-table queries.
   `LibraryFolderView` gained `HasChildren`/`DocumentCount`, dropped `Path`. Two new endpoints:
   `GET /libraries/folders/search?domainId=&term=` (replaces the DB-catalog-era
   `GET /libraries/paths?term=` — `SearchLibraryPaths` feature deleted) and
   `GET /libraries/folders/ancestors?folderId=` (new — breadcrumb reconstruction).
4. **The now-fully-superseded DB-catalog code was deleted, not just unregistered:**
   `Persistence/IFolderCatalogStore.cs`/`FolderCatalogStore.cs` and their tests/fake — the two
   [2026-08-13] entries' `dbo.CleanupRunFolder`-backed browser is gone; folder browsing is a live read
   again (like the library list already was, per the same day's other reversal), closing the gap those
   entries called out (a folder with no run history yet not appearing in the browser).
5. **New shared `components/FolderBrowser.tsx`** (OneDrive-style) — replaces the duplicated
   one-level-at-a-time list + separate "new folder name" input duplicated across
   `NewRunForm.tsx`/`Step8ArchiveLibraryModal.tsx`. Controlled on a `trail: FolderAncestor[]` (the
   breadcrumb from the library root to the current folder — empty means viewing the root); renders
   clickable `Breadcrumbs`, a single search box (folder search + ancestor-chain jump, replacing the
   separate per-level name filter and the old typed-path `Autocomplete`), and a scrollable folder list
   with a document-count readout. An optional `newFolderName`/`onNewFolderNameChange` pair (Step 8/9
   only) reveals a "New folder" button/inline text field; `NewRunForm` omits them since a starting
   folder must already exist.
6. **Restoring a previous `Step8ArchiveLibraryModal` folder selection** (the `initial` prop, id-less —
   it only ever carried a path string) now does a best-effort resolve: search for the leaf folder name,
   accept the exact full-path match, then fetch its ancestor chain to rebuild the trail. Silently opens
   at the library root instead if the library's stored id isn't a real numeric domain id (the existing
   name-fallback case) or no exact match is found — a graceful degradation, not a crash.

**Rationale:** MAGIQ's own schema already models exactly what a folder browser needs — an immediate
one-level-at-a-time child query and an ancestor closure table for breadcrumbs — so querying it directly
gives a live, always-correct tree (nothing to fall out of date, no run-history gap) with SQL that's no
more complex than the identification queries already shipped. Addressing folders by id (matching how
MAGIQ itself does) rather than path text is what makes the closure-table queries compose cleanly.

**Status:** Implemented in the product working tree (uncommitted). Backend: `Integration/Magiq/Sql/`
gained `FolderBrowseRow.cs`, `FolderSearchRow.cs`, `FolderAncestorRow.cs`, `IMagiqFolderBrowseQueries.cs`,
`MagiqFolderBrowseQueries.cs`; `ConfiguredQueryKeys.cs`/`ConfiguredQueryDefaults.cs`/
`SchemaVerification/SchemaContracts.cs`/`SchemaVerification/MagiqSchemaProbe.cs` extended;
`Features/Libraries/ListLibraryFolders/*` rewired to the new contract; `Features/Libraries/
SearchFolders/*` (new, replacing the deleted `SearchLibraryPaths`); `Features/Libraries/
GetFolderAncestors/*` (new); `Program.cs` DI. `Persistence/IFolderCatalogStore.cs`/
`FolderCatalogStore.cs` deleted (file deletion needed an explicit `allow_cowork_file_delete` grant in
this sandbox — the product folder normally blocks deletes). Frontend: `api/libraries.ts` rewritten;
new `components/FolderBrowser.tsx`; `components/NewRunForm.tsx`/`wizard/Step8ArchiveLibraryModal.tsx`
both rewired onto it; `theme/icons.ts` gained `newFolder`/`breadcrumbSeparator`. Tests: new
`Fakes/FakeMagiqFolderBrowseQueries.cs`; new handler tests for `ListLibraryFolders`/`SearchFolders`/
`GetFolderAncestors`; new `MagiqFolderBrowseQueriesTests.cs` (LIKE-escaping, blank-term short-circuit,
mirroring `MagiqDocumentQueriesTests.cs`'s style); old `FakeFolderCatalogStore.cs` and its tests
deleted. `npx tsc -b` passes clean; the API side still could not be built in this sandbox (no .NET
SDK/network available) — a `dotnet build`/test pass, and a real run against training to verify the
three new queries' column shapes (the same "verify against training" step the original four got), are
still needed before this is considered verified.

---

## [2026-08-14] Folder search scoped to the current folder, not the whole library

**Context:** Chase reported the browser's typeahead was suggesting folders anywhere in the whole
library (matching `@term` against every folder under `@domainId`), and asked for it to only suggest
subfolders under the folder currently being browsed.

**Decision:** `FolderSearch` gained an `@parentId` scope parameter — the same id `FolderChildren` already
takes to mean "current location" (a real `FOLDERID`, or the library's own `DOMAINID` at the root). A
folder is only a candidate if a `dbo.FOLDERMAP` row exists with `PARENTID = @parentId AND FOLDERID =
f.FOLDERID` — the closure table already lists every ancestor-descendant pair at any depth (not just
immediate parent/child; confirmed by the 2026-08-05 note that "for a folder F, every ancestor is `SELECT
PARENTID FROM FOLDERMAP WHERE FOLDERID = F`"), so this scopes to the whole subtree under the current
folder in one `EXISTS` check, with no recursion needed. Passing `@parentId = @domainId` (root) still
searches the entire library, since every folder's ancestor chain up to the domain is present in the
closure table — so root-level search behaviour is unchanged. `f.FOLDERID <> @parentId` excludes the
current folder itself from its own suggestions.

Threaded through the stack: `IMagiqFolderBrowseQueries.SearchFoldersAsync` gained a `parentId` parameter
(alongside `domainId`/`term`/`maxResults`); `SearchFoldersQuery`/`SearchFoldersRequest`/
`SearchFoldersResponse` mapping unchanged, but the query/request/handler chain now carries `ParentId`;
the endpoint validates `domainId`+`parentId` together (`400 ParentRequired`, matching
`ListLibraryFoldersEndpoint`'s existing validation shape) instead of just `domainId`. Route is now `GET
/libraries/folders/search?domainId=&parentId=&term=`.

`FolderBrowser.tsx` passes its own `parentId` (the same value it already computes for `listChildFolders`)
into `searchFolders`, so the search box is automatically rescoped as the operator navigates; it also now
clears any typed search text when navigating to a new folder, since a match found under the old location
may not be a valid suggestion under the new one. The search placeholder text now reads "Search in
{current folder name}" rather than always naming the library. `Step8ArchiveLibraryModal.tsx`'s
`resolveInitialTrail` (a one-shot restore-by-leaf-name lookup, not a live typeahead) passes `parentId =
domainId` deliberately, to keep searching the whole library — restoring a previously-picked folder needs
its full path to be findable regardless of where the browser happens to be pointed when the modal reopens.

**Rationale:** A whole-library search returning distant, unrelated folders defeats the "search within
where I am" mental model a OneDrive-style picker sets up, and gets noisier as a library accumulates more
history. Scoping via the existing closure table costs nothing extra structurally — it is the same table
and the same kind of `EXISTS` check `FolderChildren`/`FolderAncestors` already use — so this is a
narrowing of an existing query, not a new capability.

**Status:** Implemented in the product working tree (uncommitted): `ConfiguredQueryDefaults.cs`
(`FolderSearch` SQL + doc comment), `IMagiqFolderBrowseQueries.cs`, `MagiqFolderBrowseQueries.cs`,
`Features/Libraries/SearchFolders/{SearchFoldersRequest,SearchFoldersQuery,SearchFoldersHandler,
SearchFoldersEndpoint}.cs`, `api/libraries.ts`, `components/FolderBrowser.tsx`,
`wizard/Step8ArchiveLibraryModal.tsx`. Tests updated: `Fakes/FakeMagiqFolderBrowseQueries.cs`
(`LastSearchCall` tuple gained `ParentId`), `SearchFoldersHandlerTests.cs`,
`MagiqFolderBrowseQueriesTests.cs` (new test asserting `parentId` binds alongside `term`). `npx tsc -b`
passes clean; as with the rest of this feature, the API side could not be `dotnet build`ed in this
sandbox (no .NET SDK/network) — still needs a real build/test pass and schema verification before this
is considered fully verified.

---

## [2026-08-14] New-run source picker's search becomes a plain name filter, not a subtree jump

**Context:** Chase asked that in the "Start a run" source picker specifically, "Search in" just filter
the names in the current folder listing — not search/jump elsewhere, which is what the shared
`FolderBrowser` search box (scoped to the current subtree per the same-day follow-up above) still does.

**Decision:** `FolderBrowser` gained a `searchMode` prop, `'filter' | 'jump'` (default `'jump'`, preserving
existing behaviour everywhere it wasn't asked to change):

- **`'filter'`** (now used by `NewRunForm`'s source picker only) — a plain `TextInput`, no API call. It
  narrows the already-loaded `folders` list for the current location by a case-insensitive substring
  match on name, client-side. Nothing to select, nothing to navigate to — the visible list just shrinks.
- **`'jump'`** (default; still used by `Step8ArchiveLibraryModal`'s archive-destination picker,
  unchanged) — the existing `Autocomplete` + `GET /libraries/folders/search` + navigate-to-match
  behaviour from the two entries above.

Both modes still clear the search text when the browser navigates to a new folder (the effect that does
this was already mode-agnostic). The `'jump'`-only API round trip (`useEffect` calling `searchFolders`)
is skipped entirely in `'filter'` mode. Empty-state text now distinguishes "no subfolders here" (nothing
loaded) from `No folders match "x".` (a filter with no matches).

**Rationale:** The two pickers have different jobs. Archive-destination browsing genuinely benefits from
jumping deep into a big library in one step. New-run source selection is about picking a starting point
*within what's already listed* — a deep subtree jump there is more surprising than helpful (it silently
moves the operator's location out from under them while they're just trying to eyeball a name), so a
plain filter over the visible list is the better fit. Making this a prop rather than a blanket behaviour
change keeps the archive-destination picker exactly as it was.

**Status:** Implemented in the product working tree (uncommitted): `components/FolderBrowser.tsx`
(`searchMode` prop, `visibleFolders` computation, conditional `TextInput`/`Autocomplete` render,
mode-agnostic doc comment), `components/NewRunForm.tsx` (`searchMode="filter"`). No backend change —
this is purely a client-side rendering/interaction difference; `Step8ArchiveLibraryModal.tsx` is
untouched. `npx tsc -b --force` passes clean.

---

## [2026-08-14] New-run library picker: client-side filter instead of a server round trip per keystroke

**Context:** Chase reported that typing in the new-run form's "Filter libraries" box was "completely
reloading the list" and asked for a plain hide/show filter instead, plus removal of the border around
each row. Tracing it: this box (`renderLibraryPicker` in `NewRunForm.tsx`, the library-selection step
that precedes folder browsing) was unrelated to the `FolderBrowser` `searchMode` work from earlier the
same day — it debounced the typed text and re-called `listLibraries()` (live SOAP `GetDomains`) on every
change, which really does reload the whole list from MAGIQ each keystroke. Its row style also carried a
literal `border: '1px solid var(--mantine-color-default-border)'`, unlike `FolderBrowser`'s borderless
rows.

**Decision:** `listLibraries()` is now fetched once per mount/token change (no `nameFilter` passed); the
typed filter text narrows the already-fetched list client-side (`visibleLibraries`, same
case-insensitive substring pattern as `FolderBrowser`'s filter mode and the archive-destination search).
`useDebouncedValue` is no longer needed here and was removed. The row's `border` was dropped from
`rowStyle`, matching `FolderBrowser`'s borderless list rows.

**Note:** `Step8ArchiveLibraryModal.tsx` had the same library-list pattern (debounced server filter +
bordered rows) — Chase asked for the identical fix there too (same day, see next entry).

**Status:** Implemented in the product working tree (uncommitted): `components/NewRunForm.tsx`
(`visibleLibraries`, effect keyed on `token` only, `rowStyle` border removed, empty-state text split into
"No libraries found." vs `No libraries match "x".`). `npx tsc -b --force` passes clean.

---

## [2026-08-14] Same client-side library filter + borderless rows applied to the archive-destination picker

**Context:** Chase asked for the same fix in `Step8ArchiveLibraryModal.tsx`'s library picker (shared by
"Library / existing" and "Folder" destination types) — flagged as having the identical pattern in the
previous entry.

**Decision:** Same shape as `NewRunForm`: `listLibraries()` fetched once (`useEffect` on
`[needsLibraryList, token]`, no `nameFilter` passed — `needsLibraryList` still gates the fetch to only
when the picker is actually shown), typed filter text narrows the fetched list client-side
(`visibleLibraries`), `useDebouncedValue` import removed (no longer used anywhere in the file), and the
row `border` dropped from `rowStyle`. Empty state now distinguishes "No libraries found." (nothing
fetched) from `No libraries match "x".` (a filter with no matches), matching `NewRunForm`.

**Status:** Implemented in the product working tree (uncommitted): `wizard/Step8ArchiveLibraryModal.tsx`.
`npx tsc -b --force` passes clean. The two library pickers (`NewRunForm`, `Step8ArchiveLibraryModal`) and
the shared `FolderBrowser` (filter/jump modes) now all follow the same "fetch once, filter client-side,
no row border" pattern.

---

## [2026-08-14] Normalization Review table column widths (Type/Change/Status)

**Context:** Chase reported the `NameChangesTable` on the Normalization Review screen (`Type`/`Current
name`/`Becomes`/`Change`/`Status` columns) looked cramped: the `Type` badges (`FOLDER`/`DOCUMENT`,
Mantine's default badge uppercasing) sat at inconsistent widths since the two words differ in length,
and the `Change` column's longer phrases (e.g. `rename — has extra spaces`, or a joined list like `has a
non-breaking space, extra spaces`) didn't fit on one line.

**Decision:** Gave `Type`/`Change`/`Status` explicit column widths (`Table.Th w={110}` /`miw={230}`/
`w={100}`, `Table.ScrollContainer minWidth` bumped 640→760 to fit them), gave each `Type` badge a fixed
`minWidth: 84` + centred text so `FOLDER`/`DOCUMENT` sit evenly regardless of word length, and set
`whiteSpace: 'nowrap'` on the `Change`/`Status` cell text so short phrases never wrap awkwardly (a long
joined reason list still wraps at the column's `miw`, which is intentional — better than truncating).

**Status:** Implemented in the product working tree (uncommitted): `wizard/NormalizationReview.tsx`
(`NameChangesTable`, both the rename rows and the resolved-action rows). `npx tsc -b --force` passes clean.

---

## [2026-08-14] Step 8 name-change download moved to the Document Register, as pinned before/after snapshots

**Context:** Chase asked for two related changes together: (1) the Normalization Review table formatting
above, and (2) move the "Download changes" button off that screen entirely, folding its content into the
Document Register section as another pair of pinned before/after snapshots — captured automatically
(like the existing `PreRun`/`PostRun` register snapshots) rather than downloaded on demand.

**Decision:**

1. **Two new `RegisterSnapshotKind` values** — `PreNormalization` (the Step 8 rename plan, captured once
   the dry run settles clean and the operator is shown the Normalization Review gate, before Step 8b
   applies anything) and `PostNormalization` (the same rename list, captured once every item is
   confirmed `Renamed` and the operator proceeds to archival, so its `Status` column reflects what 8b
   actually did rather than what it planned). Both fit the existing `SnapshotKind NVARCHAR(20)` column —
   no schema migration needed, just new string values in an already-unconstrained column.

2. **Shared row-building extracted** — the row-assembly logic that used to live only in
   `ExportNameChangesHandler` (renames + resolved folder merges/duplicate deletes → `Type`/`Change`/
   `Parent path`/`Original name`/`New name`/`Reason`/`Resolution`/`Status` rows, plus the plain-language
   `DescribeReason`/`SpecialCharName` whitespace-naming helpers) moved into a new
   `INameChangeRegisterRows`/`NameChangeRegisterRows` (`Features/Runs/ExportRegister/`), so it can be
   shared by both the new snapshot kinds and (previously) the on-demand endpoint — column order and the
   "why" text stay identical to what the SPA's `NormalizationReview` already showed, so nothing drifts.

3. **`RegisterExportJob` branches on the new kinds** — `PreNormalization`/`PostNormalization` build rows
   via `INameChangeRegisterRows.BuildAsync` (reads only the DLC-owned `CleanupRunRename`/
   `CleanupRunNameConflict` tables — no MAGIQ round trip, same as the outcome ledger for `PostRun`) instead
   of the MAGIQ register query; the downloaded file is named `Name-Changes-Before_{date}`/
   `Name-Changes-After_{date}` rather than `Document-*`, to make clear it's a different dataset from the
   candidate register.

4. **Two new pin points, mirroring the existing `PreRun`/`PostRun` hooks:**
   - `RunPhaseExecutor.AnalyzeNormalizationAsync` — right where the "hasRenames" branch already pauses
     the run for the Normalization Review gate, it now also deletes any prior `PreNormalization` export
     for the run and creates + enqueues a fresh one. A conflict-resolution round that loops back through
     8a and reaches a clean plan again replaces the previous snapshot, exactly like `PreRun`.
   - `ContinueAfterNormalizationHandler` — right before it starts archival (after confirming every rename
     is `Renamed`, no outstanding), it now also deletes any prior `PostNormalization` export and creates +
     enqueues a fresh one. Both hooks use `CancellationToken.None` for the snapshot calls, matching the
     existing `PreRun`/`PostRun` best-effort pattern: a snapshot failure must not block the state
     transition, only get recorded on the export row.
   - `ContinueAfterNormalizationHandler`'s constructor gained `IRegisterExportStore exports`.

5. **Retired the standalone `GET .../normalization/changes/export?format=xlsx|csv` endpoint** — deleted
   `Features/Runs/Normalization/ExportChanges/*` (`ExportNameChangesEndpoint`/`Handler`/`Query`/`Request`/
   `NameChangesExport`) now that the same content is reachable via `.../register/exports` +
   `.../register/export/{exportId}/download`. `ExportNameChangesHandlerTests.cs` deleted; replaced by
   `Features/Runs/ExportRegister/NameChangeRegisterRowsTests.cs` testing the extracted builder directly
   (row shape, `DescribeReason` mapping, resolved merge/delete rows, pending-conflict exclusion).

6. **Frontend** — `NormalizationReview.tsx` lost the `NameChangeToolbar` (format toggle + "Download
   changes" button), its `format`/`downloading`/`downloadError` state, and the `download()` function; the
   in-app change table (`NameChangesTable`) stays for review, now under a plain count line plus a note
   pointing to the Document Register section above for a downloadable copy. `api/normalization.ts` lost
   `downloadNameChanges` (and its now-unused `RegisterExportFormat` import). `api/runs.ts`'s
   `RegisterSnapshotKind` type gained the two new values. `JobDetailsView.tsx`'s `snapshotLabel()` gained
   `Name changes — before`/`Name changes — after` (cyan/violet), and the `RegisterSnapshots` sort `order`
   became `PreRun(0) → PreNormalization(1) → PostNormalization(2) → PostRun(3) → AdHoc(4)` — run-timeline
   order. The Document Register section's descriptive text and empty-state note were extended to mention
   the name-change snapshots.

**Rationale:** The two mechanisms (register export polling/pinning, and the on-demand name-change export)
already did almost the same thing — render schema-less rows to CSV/Excel via a background job, track
status, stream on download — so giving the name-change list the same pinned-snapshot treatment as the
whole-run register, rather than a bespoke button, removes a parallel download path for no loss of
capability, and gives the operator the same "before vs after" comparison for the name-change step
specifically, not just the whole run.

**Status:** Implemented in the product working tree (uncommitted). Backend: `Domain/RegisterSnapshotKind.cs`
(two new values), new `Features/Runs/ExportRegister/NameChangeRegisterRows.cs`, `RegisterExportJob.cs`
(new dependency + branches + filename switch), `Pipeline/RunPhaseExecutor.cs`
(`AnalyzeNormalizationAsync` pin point), `Features/Runs/Normalization/Failures/
ContinueAfterNormalizationHandler.cs` (new dependency + pin point), `Program.cs` DI registration; deleted
`Features/Runs/Normalization/ExportChanges/*`. Tests: new `NameChangeRegisterRowsTests.cs`; updated
`NormalizationFailuresHandlerTests.cs` (new `FakeRegisterExportStore` param + snapshot assertions) and
`RunPhaseExecutorNormalizationTests.cs` (`Fixture` gained an `Exports` field + snapshot assertions on the
review-gate-pause and zero-change tests); deleted `ExportNameChangesHandlerTests.cs`. Frontend:
`wizard/NormalizationReview.tsx`, `api/normalization.ts`, `api/runs.ts`, `pages/JobDetailsView.tsx`. `npx
tsc -b --force` passes clean; as with the rest of this project's backend work, the API side could not be
`dotnet build`ed in this sandbox (no .NET SDK/network) — a real build/test pass is still needed before
this is considered fully verified.

---

## [2026-08-14] Name Normalization execution-results table polish; snapshot no-show explained

**Context:** Chase manually tested the Step 8b execution results view (`NormalizationExecutionPanel.tsx`,
distinct from the pre-execution `NormalizationReview.tsx` table fixed earlier) and the new
`PreNormalization`/`PostNormalization` Document Register snapshots from the entry above, and reported two
things: the results table's Type/Status columns didn't fit their badge labels and errors were shown inline
in the Status cell with no dedicated column, and the two new snapshot downloads never appeared in the
Document Register section at all.

**Decision:**

1. **Extracted the whitespace/invisible-character visualiser out of `NormalizationReview.tsx`** into a new
   shared `components/WhitespaceVisible.tsx` (`isSpecialChar`, `humanCharName`, `Visible` exported;
   `shortLabel`/`SpecialMarker`/`INVISIBLE` stay module-private). `NormalizationReview.tsx` now imports
   `Visible`/`humanCharName` from there instead of defining them locally (`describeDifference` stays local,
   just calls the imported `humanCharName`) — needed so the execution panel could reuse the same dot/chip
   rendering for its Rename column.

2. **`NormalizationExecutionPanel.tsx` table reworked:** the Type badge gets the same `w={110}`/
   `minWidth: 84, textAlign: 'center'` treatment as `NameChangesTable`'s Type column so FOLDER/DOCUMENT fit
   consistently. Status became a fixed-width (`w={130}`) badge for every settled state — `Renamed` (teal)
   and `Failed` (red, previously shown as bare text) both now render as badges the same size as `Pending`
   (gray), so the column no longer resizes based on content. The failure reason moved out of Status into a
   new **Error** column, rendered (header + every row cell) only when `hasErrors = failed > 0` — `failed`
   is the run's total failed count from `data.failedCount`, not the currently-filtered `rows`, so the
   column doesn't flicker in and out as the Failures/All toggle changes what's visible. The Rename column
   is now two stacked lines (`Stack gap={2}`) — the original path, then a dimmed `→` and the new name —
   each run through `Visible` so doubled/non-breaking/invisible characters show as dots and chips on both
   lines, not just inline in one run of text.

3. **Investigated why the `PreNormalization`/`PostNormalization` snapshots never appeared.** Not a code
   bug: `git status` on the product repo shows every file that creates those export rows —
   `Pipeline/RunPhaseExecutor.cs`, `Features/Runs/Normalization/Failures/ContinueAfterNormalizationHandler.cs`,
   `Features/Runs/ExportRegister/RegisterExportJob.cs`, `Domain/RegisterSnapshotKind.cs` — as modified but
   **uncommitted** working-tree changes (all written in this same session, per the entry above; per this
   project's workflow, Claude never commits — Chase owns git). The committed `HEAD` (`53b322d`) predates
   all of it. Whatever build Chase tested against (deployed via IIS/Docker, or even a from-HEAD local
   build) has no code path that ever inserts a `RegisterExport` row with `SnapshotKind = PreNormalization`
   or `PostNormalization`, so `ListRegisterExportsHandler` correctly returns none and the SPA correctly
   shows nothing for them — the frontend display logic (`snapshotLabel`, `RegisterSnapshots` sort order)
   was already fine and needed no change. Confirmed no exhaustive `RegisterSnapshotKind` switch elsewhere
   would throw on the two new values (`RegisterExportStore.ToDomain` uses `Enum.Parse`, the response DTO
   uses `.ToString()`) — ruling out a serialization-path bug as well.

**Rationale:** Matching the Type/Status badge treatment already used in `NormalizationReview.tsx` keeps the
two Name Normalization views visually consistent instead of inventing a second convention. Gating the Error
column on the run's real failure count (not the filtered view) means it behaves the same regardless of
which toggle the operator has selected. The snapshot "bug" report resolves to a deployment-state fact, not
an application defect — worth recording so a future session doesn't re-investigate the same dead end.

**Status:** Implemented in the product working tree (uncommitted, same as the entry above).
`components/WhitespaceVisible.tsx` (new), `wizard/NormalizationReview.tsx` (imports from it),
`components/NormalizationExecutionPanel.tsx` (Type/Status/Error/Rename rework). `npx tsc -b --force` passes
clean. No backend changes this round. **Action needed from Chase:** commit and rebuild/redeploy the API
before re-testing the Document Register snapshot downloads — the feature is code-complete but not yet in
any build he can run.

---

## [2026-08-14] Operation audit trail defaults to ascending; live poll no longer replaces visible rows

**Context:** `FullAuditTrail` (`components/OperationAuditPanel.tsx`) defaulted to newest-first (`occurredAt`
desc) and, while a run was live, re-fetched the current page/filters on a 5s tick, replacing `entries`
outright each time. On page 1 (the default view) that meant the visible rows kept shuffling as the run
appended new operations — every poll could reorder or bump rows the operator was mid-read on. Chase asked
for the trail to order ascending instead, so a run's rows land in an append-only fashion (new operations
land on later pages, not page 1), and for the live poll to refresh only the count/pagination, not the rows
themselves.

**Decision:**

1. **Default sort direction flipped to ascending.** `FullAuditTrail`'s `dir` state now initialises `'asc'`
   instead of `'desc'`; `onSort`'s "switch to a new column" branch now always defaults to `'asc'` (previously
   `occurredAt` alone defaulted to `'desc'`). Clicking a header still toggles direction as before — this
   only changes the *starting* direction, including for When.

2. **Split the live poll from the row fetch.** The row-fetch effect (keyed on `page`/filters/`sort`/`dir`/
   `live`) no longer runs on a timer — it only runs when the operator actually changes the page, a filter,
   or the sort, plus once more when `live` flips to `false` (to catch the last few rows). A separate new
   effect polls every `LIVE_POLL_MS` (only while `live`) with `pageSize: 1` against the same filters, and
   applies only `result.total` to state — `entries` is never touched by the poll. This keeps the range label
   and the `Pagination` control's page count current (so a growing run visibly gains pages) without ever
   swapping the rows the operator is looking at out from under them.

**Rationale:** Ascending + poll-the-count-only is the append-only reading of an audit trail: page 1 is the
oldest, stable slice, so there's nothing to silently refresh there, and the operator's context (scroll
position, in-progress read, any hover state) survives a live run's polling instead of getting reset every 5
seconds. The count-only poll (`pageSize: 1`) is a cheap way to keep the pagination UI honest without a
dedicated count endpoint.

**Status:** Implemented in the product working tree (uncommitted). Frontend only —
`components/OperationAuditPanel.tsx`. `npx tsc -b --force` passes clean. No backend or API-contract change:
the server's own default (`dir=desc` when the caller omits it) is unchanged; the SPA now simply always
requests `asc` explicitly. `LiveActivity` (the separate short live-activity feed above the trail) is
unaffected — it already re-fetches its own small newest-first list on its own poll and was not part of this
change.

---

## [2026-08-14] Trim duplicate failure surfaces now that the audit trail carries every operation

**Context:** With the operation audit trail now the durable, filterable, exportable record of every
create/move/delete/rename (and the entry above making it behave append-only), two other places on the run
page were showing the same information redundantly. Chase asked to (1) stop listing successfully **deleted**
folders in the Step 10 outcomes panel — a successful `DeleteFolder` is already an `Ok` row in the audit trail
— while still surfacing **failed** deletes with their reason (an actionable gap the audit trail alone doesn't
close, since nothing there offers "here's what still needs attention"), and (2) remove the generic
"N failed ▼" collapsible list from the live `RunProgressPanel`.

**Decision:**

1. **`CleanupOutcomesPanel` now lists failures only.** `outcomes` (Deleted + Failed) became `failures`
   (Failed only); the panel self-hides once there are no failures rather than once there are no outcomes at
   all. Renamed "Folder cleanup outcomes" → **"Folder cleanup failures"**, dropped the deleted/failed tally
   line for a plain failed count plus a note that successful deletes live in the audit trail below, and
   dropped the now-always-`Failed` Status column from the table (Folder + Error is enough once every row is
   a failure by definition).

2. **`RunProgressPanel` no longer renders its own failed-items list.** Removed the `{failedItems.length}
   failed ▼` `Collapse`/`List` block and its `useDisclosure` state; the component no longer destructures
   `failedItems` from `useRunProgress`. This list was a fourth, ephemeral (session-only, not paginated or
   persisted) place a failure could be seen, on top of the audit trail, `CleanupOutcomesPanel` (folder
   deletes), `MoveFailuresPanel` (document moves), and `NormalizationExecutionPanel`'s Error column (renames)
   — none of which it added anything over. `useRunProgress` itself is untouched (still accumulates
   `ItemFailed` messages into `failedItems` internally); nothing else in the app reads that field, so it is
   simply unconsumed now rather than removed from the hook's contract.

**Rationale:** Once the audit trail is the trustworthy, complete, filterable ledger, a redundant "successful
outcome" listing elsewhere is pure duplication with a staleness/consistency risk of its own (two places that
could theoretically disagree). Failures are the one thing worth a dedicated, actionable surface per phase
(they're what the operator needs to *do* something about — retry, fix in MAGIQ, etc.), so those stay;
everything "it worked" collapses down to the one audit trail.

**Status:** Implemented in the product working tree (uncommitted). Frontend only —
`components/CleanupOutcomesPanel.tsx`, `components/RunProgressPanel.tsx`. `npx tsc -b --force` passes
clean. No backend change — `FolderItem`/`getRunFolders` and the `ItemFailed` SignalR message are unchanged;
this is purely which of the data already available gets rendered.

---

## [2026-08-14] Step 11 folder-delete-failure retry (individual + all)

**Context:** The entry above narrowed the Folder cleanup panel to failures-only, matching the Document move
failures panel's philosophy — but that panel also lets the operator *act* on a failure (retry it), which the
folder panel didn't yet. Chase asked for the same: retry a failed folder delete individually, or all
together. Unlike a Step 10 move failure, a Step 11 folder-delete failure never fails the run (`ExecuteCleanupAsync`
treats it as best-effort and still proceeds to the purge/pause), so the retry design differs from
`RetryMoveFailuresHandler` in one key way: there is no `RunStatus`/phase gate and no "resume the run" step —
the operator can retry a stray failure at any time, including after the run has already `Completed`.

**Decision:**

1. **New `ICleanupRunFolderStore.GetByStatusAsync(runId, status, ct)`** — mirrors
   `ICleanupRunDocumentStore.GetByMoveStatusAsync`, filtering a run's folders to one `FolderStatus` (used
   here for `Failed`). Added to the Dapper store and all seven test doubles that implement the interface
   (`FakeCleanupRunFolderStore` plus six inline `StubFolders`/`RecordingFolders` classes across the
   `RunPhaseExecutor*Tests` files) so the interface addition doesn't strand any existing test.

2. **`IFolderDeleteRetryer.RetryFolderDeletesInlineAsync`** (implemented by `RunPhaseExecutor`, registered
   in `Program.cs` the same way as `IMoveFailureRetryer`/`INormalizationFailureRetryer`) re-attempts the
   given failed folders in place, reusing the **exact same per-parent rule-relax + audit machinery**
   (`RuleGuardedOp`/`RunFolderGroupAsync`, grouped by `ParentPath` since a folder's delete is governed by
   its *parent's* `FolderDeletes` rule) as the original Step 11 pass in `DeleteEmptyFoldersAsync` — just
   scoped to the targeted rows instead of the run's whole deletable set, and with no run-progress emission
   or `RunStatus` change (there is nothing to resume, unlike the move retry).

3. **`POST /runs/{runId}/folders/delete-failures/retry`** — body `{ folderIds?: string[] }`. The API deals
   in the MAGIQ `FolderId` (the same identifier `FolderItem` already exposes to the SPA), **not** the
   `CleanupRunFolder` row id — `RetryFolderDeleteFailuresHandler` resolves requested `FolderId`s against the
   run's currently-`Failed` folders, narrows to that intersection (empty/omitted request = all failed), and
   translates to row ids only at the boundary to call the retryer. `404 RunNotFound`;
   `409 NoFailuresToRetry` if nothing failed or none of the requested ids are currently failed. **Not**
   gated on run status/phase, unlike `RetryMoveFailuresHandler`'s `RunNotRetryable` check — this is the
   deliberate behavioural difference from the move retry, not an oversight.

4. **Frontend:** `api/folders.ts` gained `retryFolderDeleteFailures(runId, folderIds, token)`.
   `CleanupOutcomesPanel.tsx` gained a **Retry all failed (N)** button and a per-row **Retry** button
   (mirroring `MoveFailuresPanel`'s inline retry UX — a `Retrying…` loader replaces the error text mid-call),
   patching the retried folders' status/error directly from the response rather than waiting for the next
   poll; a folder that comes back `Deleted` simply drops out of the Failed filter on the next render, same
   as any other resolved failure (no special "just fixed" confirmation state, keeping with the panel's
   already-established philosophy of only showing what still needs attention).

5. **Housekeeping:** while touching this code, corrected a pre-existing stale **"Step 10"** label on the
   folder-delete comments/doc-comments this work sits next to (`ExecuteCleanupAsync`'s summary,
   `DeleteEmptyFoldersAsync`'s two comments, `CleanupOutcomesPanel.tsx`'s doc comment) to the correct
   **Step 11** (folder deletes are Step 11 per the business spec's own section header; Step 10 is the
   archival move) — the audit rows themselves were always correctly stamped `11`, only the prose had drifted
   during an earlier renumbering pass. Left the identical pre-existing mislabel alone everywhere it wasn't
   directly adjacent to this change (out of scope for this round), and left past `decisions/log.md` entries
   as-is (append-only).

**Rationale:** Reusing the same rule-relax/audit primitives as the original Step 11 pass means the retry
behaves identically to a fresh attempt (same reactive rule handling, same audit trail shape) with no
duplicated logic. Keying the API on `FolderId` rather than introducing a new row-id field into `FolderItem`
keeps the request body natural for the SPA, which already has that identifier on every row it's showing.
Not gating on run status is the correct reading of "Step 11 is best-effort" — the run's lifecycle already
moved on regardless of a folder-delete failure, so the retry shouldn't require rewinding it.

**Status:** Implemented in the product working tree (uncommitted). Backend: `Persistence/ICleanupRunFolderStore.cs`
+ `CleanupRunFolderStore.cs` (`GetByStatusAsync`), new `Pipeline/IFolderDeleteRetryer.cs`,
`Pipeline/RunPhaseExecutor.cs` (`RetryFolderDeletesInlineAsync` + the Step 11 comment fixes), new
`Features/Folders/RetryFolderDeleteFailures/*` (Command/Request/Response/Handler/Endpoint), `Program.cs` DI.
Tests: new `Fakes/FakeFolderDeleteRetryer.cs`, new `Features/Folders/RetryFolderDeleteFailuresHandlerTests.cs`;
updated `Fakes/FakeCleanupRunFolderStore.cs` and the six `RunPhaseExecutor*Tests.cs` inline stubs for the new
interface member. Frontend: `api/folders.ts`, `components/CleanupOutcomesPanel.tsx`. `npx tsc -b --force`
passes clean; as with the rest of this project's backend work, the API side could not be `dotnet build`ed or
test-run in this sandbox (no .NET SDK) — verified by careful manual review only. `spec/dev-spec.md` (new
endpoint row) and `spec/NATA_Document_Lifecycle_Cleaner_Spec_v0.6.md` (rev 15, Step 11 section + History)
updated to match.

---

## [2026-08-14] Real incident: a Step 11 parent folder deleted before its still-present child — deepest-first ordering + a live pre-delete emptiness guard

**Context:** Chase hit a path error deleting a target folder on a live run (`c60553b1-e053-4e53-b178-19f8d0770c7c`)
and, reading the operation audit trail CSV, found the cause: `/03.01 Facilities/02178 DHM (DO NOT USE
PORTAL)/02717 Dubbo/ARE 2011` (seq 927, `DeleteFolder`, `Ok`) was deleted **before** its own child
`.../ARE 2011/39374 RES 2011 Hist` (seq 929, `DeleteFolder`, `Failed`, "Target folder not found") — roughly
90ms later. Both folders had had all their documents successfully archived first (Step 10); both were
legitimate Step 11 candidates. Chase asked specifically whether ARE 2011 had been treated as "empty" while it
still had a child, and asked for the root cause.

**Root cause (confirmed by direct review, not just the investigating sub-agent's report):**
`ICleanupRunFolderStore.GetDeletableAsync`'s SQL used a plain `ORDER BY FolderPath` — no depth ordering. Because
a parent's path is always a string-prefix of its child's path, this happens to sort the shorter parent path
first in the common case (exactly what happened here). `RunPhaseExecutor.DeleteEmptyFoldersAsync` deleted
folders in that order without ever re-sorting them, so the parent was deleted while the child folder still
physically existed beneath it. MAGIQ's `DeleteFolder` — never previously verified against a non-empty folder
(`SOAP-VERIFICATION-34525.md` only covers already-empty leaf paths) — turned out to **cascade-remove** the
still-present child along with the parent, rather than fail. The pipeline's own later delete attempt for the
child then failed "Target folder not found", because MAGIQ had already removed it as a side effect.

**Broader finding, once this was investigated further (Chase asked to also investigate the Rule 2
downward-closure angle):** the SQL-level ordering bug is not the only way a live folder can end up under a
parent Step 11 deletes. `ConfiguredQueryDefaults.CandidateFolders`' `FolderSet` CTE closes only **upward** —
`CandidateFolder ∪ ancestors-of-CandidateFolder` via `FOLDERMAP.PARENTID` — never downward toward descendants.
`CandidateFolderBuilder.ResolveProtectedIds` then only walks `ParentFolderId` **within the rows SQL already
returned**. The combination means: a subfolder holding *only* post-cutoff documents (which Rule 2 says must
never be deleted) is invisible end-to-end — no `CleanupRunFolder` row, no `Protected` status — unless it
happens to independently be an ancestor of some other candidate folder elsewhere. The same blind spot also
covers a subfolder the operator has seen and **deliberately left deselected**: its documents are never
archived (Step 7's Kept-exclusion), and it's just as exposed to a cascading parent delete. Deepest-first
ordering cannot defend against either case, because neither folder was ever going to appear in `deletable` in
the first place.

**Decision:**

1. **Deepest-first ordering in `DeleteEmptyFoldersAsync`** — re-sort whatever `GetDeletableAsync` returns by
   `OrderByDescending(f => f.FolderPath.Count(c => c == '/'))` before batching, the same pattern already used
   by the rollback teardown's `RemoveCreatedArchiveFoldersAsync`. Guarantees every folder *this run knows
   about* is deleted child-before-parent regardless of the store's own ordering. `ICleanupRunFolderStore
   .GetDeletableAsync`'s SQL itself is left as `ORDER BY FolderPath` — the depth-safety guarantee lives solely
   in the executor (its only caller), documented in the interface's XML doc comment rather than duplicated.

2. **Live pre-delete emptiness guard — `RunPhaseExecutor.DeleteFolderIfEmptyAsync`.** Before every
   `DeleteFolder` call (the original Step 11 pass and its operator-driven retry), call
   `IMagiqSoapClient.ListFoldersAsync(ticket, path)` and refuse the delete — marking the folder `Failed` with a
   clear reason, never invoking `DeleteFolderAsync` — if MAGIQ reports any remaining subfolder. A
   `ListFoldersAsync` failure is treated the same as "not empty" (fail closed) rather than risk a silent
   cascade. This is the actual backstop for the broader finding: it is independent of the candidate set,
   `FolderCount` snapshots, and operator selection, so it catches an invisible Rule-2 folder, a deliberately
   deselected sibling, or anything else ordering can't reach — at the cost of one extra SOAP round trip per
   folder delete attempt, deemed acceptable for a once-a-year background job.

3. **Chose the live guard over closing the SQL downward-closure gap.** Chase was offered both (fix ordering,
   fix downward closure) plus "write-up only", and picked the ordering fix plus **the live guard** in place of
   the SQL change. Rationale: the live guard is a single, general defense that requires no changes to the
   customer-configurable `CandidateFolders` query (a recursive downward closure there would need a fixed-point
   computation to reach a subfolder under a folder that only qualified as an *ancestor* of some other
   candidate — not just a direct one — and wouldn't retroactively help any run already using a customized
   query default). The SQL-level gap remains real (Step 6 review still won't show the invisible folder or flag
   it Protected), but is no longer able to result in data loss, since Step 11 can no longer delete a folder
   that still has *any* live subfolder for *any* reason. Revisiting the SQL/UI-visibility side is left to the
   deferred backlog.

**Rationale:** The two defenses are complementary, not redundant: ordering is cheap and handles the overwhelmingly
common case (both folders were legitimate candidates) without adding a round trip per delete when it isn't
needed for depth reasons alone; the live guard is what actually closes the safety gap for folders the pipeline
never had visibility into. Fixing the visible-ordering bug alone would have "fixed" this specific incident but
left the strictly worse (silent, no-audit-trail) case wide open.

**Status:** Implemented in the product working tree (uncommitted). Backend:
`Pipeline/RunPhaseExecutor.cs` (`DeleteEmptyFoldersAsync` deepest-first re-sort; new `DeleteFolderIfEmptyAsync`
wrapping both the original Step 11 pass and `RetryFolderDeletesInlineAsync`'s `DeleteFolder` calls),
`Persistence/ICleanupRunFolderStore.cs` (doc comment corrected + explains the executor's re-sort). Tests: new
`RunPhaseExecutorRelaxOncePerFolderTests.Step11_deletes_a_child_folder_before_its_parent_even_when_the_store_returns_them_parent_first`
and `...Step11_refuses_to_delete_a_folder_that_still_has_a_live_subfolder_the_run_never_evaluated`; updated that
file's `RuleEnforcingSoap` double (`ListFoldersAsync` now configurable via `SetChildCount`, `DeleteFolderCalls`
tracked) and `RunPhaseExecutorRuleGuardTests.cs`'s `RecordingSoap.ListFoldersAsync` (empty-by-default, was
`NotSupportedException`) since both suites exercise `ExecuteCleanupAsync` and would otherwise throw on the new
call. As with the rest of this project's backend work, the API side could not be `dotnet build`ed or test-run
in this sandbox (no .NET SDK) — verified by careful manual line-by-line review only. Spec update still pending
as part of this same entry's follow-through (Step 11 section of `spec/NATA_Document_Lifecycle_Cleaner_Spec_v0.6.md`
+ `spec/dev-spec.md`) — the SQL-level Rule 2 downward-closure gap itself is flagged here rather than fixed,
per CLAUDE.md's rule not to silently resolve a finding that touches a documented spec rule (Rule 2) without
reconciling intent first.

---

## [2026-08-14] Document Register: PreRun scoped to the run's starting folder + new PostReview snapshot

**Context:** Diagnosing the Step 11 cascade-delete incident above needs a reliable before/after picture of
what a run actually saw and selected. Two problems with the existing Document Register stood in the way.
First, the pinned "before" (`PreRun`) snapshot — and the on-demand `AdHoc` export — always queried the whole
source *library*, ignoring a run's optional starting-folder scope (Story 34566, decisions/log.md
[2026-08-13]); this was a known, explicitly documented limitation (`RegisterExportJob.cs`'s old comment,
and the [2026-08-13] entry itself), because the register's columns are operator-configured SQL with no
guaranteed path column to filter by, unlike the typed `CandidateDocument`/`CandidateFolder` rows Steps 1/4/8
already scope. Second, there was no snapshot at all capturing what the operator's Step 6/7 review actually
selected/kept before Normalization or Archival start mutating anything — `PreRun` reflects the raw candidate
universe (unfiltered by selection, by design), and `PostRun` only exists once the run has already finished,
by which point the source documents have moved. Chase asked for both: PreRun scoped to the chosen folder, and
a new report reflecting the review selection, to use as the before/after pair for diagnosing cases like the
"60912 SRV 2016 still has 4 subfolders" failure.

**Decision:**

1. **Extracted `Pipeline/SourceScope.cs`** — `BuildPrefix(run)`/`IsWithinScope(path, prefix)`, pulled out of
   `RunPhaseExecutor`'s private `BuildSourceScopePrefix`/`IsWithinSourceScope` (which Steps 1/4/8 already used)
   with identical behaviour, so `RegisterExportJob` can reuse the exact same scope logic rather than
   duplicating it. `RunPhaseExecutor`'s three call sites now delegate to `SourceScope`; no behaviour change
   there.

2. **PreRun/AdHoc now scoped to the run's starting folder.** The register query itself is unchanged (still
   pulls the whole library — there's no folder id to bind, same reasoning as Steps 1/4/8); scoping instead
   filters the returned rows in `RegisterExportJob.BuildScopedRegisterRowsAsync`, matching `SourceScope`
   against whichever of a documented set of column names (`"Folder Path"`, `FolderPath`, `Document Path`,
   `DocumentPath`, `Path` — tried in that order, case-insensitive) the row actually carries. The **default**
   `DocumentRegister` query already produces exactly such a column (aliased `[Folder Path]`, built the same
   way the destination-scope prefix is), so this works out of the box for the shipped default; a
   heavily-customized query that drops every one of those column names is **left unscoped** (fails open,
   with a warning logged) rather than silently returning zero rows, which would be indistinguishable from
   "this folder is empty." `ConfiguredQueryDefaults.DocumentRegister`'s doc comment now states this as an
   explicit contract for anyone customizing the query.

3. **New `RegisterSnapshotKind.PostReview`.** Captured in `ConfirmDeletionsHandler` immediately alongside the
   existing `PreRun` capture — i.e. right after the Kept-exclusion projection applies the operator's Step 6/7
   folder selections, before `StartNormalizationAnalysis` is enqueued. Reuses `BuildOutcomeLedgerAsync`
   (previously PostRun-only) rather than a new builder: it reads the run's own `CleanupRunDocument`/
   `CleanupRunFolder` tables (already narrowed by `SourceScope` at Step 1/4 insert time — this snapshot gets
   the folder-scope fix "for free," no separate column-matching needed), so a document that was excluded is
   already `Kept` and a folder's `IsSelectedForDeletion` reflects exactly what got confirmed. `PostRun` and
   `PostReview` are the same ledger shape, captured at two different points in the run's life (right after
   review vs. at completion) — a genuine "diff the pipeline's own bookkeeping against itself" comparison,
   distinct from `PreRun`'s "diff MAGIQ's raw universe against what got selected."

4. **Enriched the outcome-ledger folder rows** with `IsSelectedForDeletion`, `DocumentCount`, `FolderCount`
   (previously only `ItemType`/`Path`/`Disposition`/`ProtectionReason`/`FailureReason`) — applies to both
   `PostRun` and `PostReview`. `Disposition` (`FolderStatus`) alone can't show what the operator *chose*
   pre-archival (everything not `Protected` just reads `Pending`), and `DocumentCount`/`FolderCount` answer,
   in the same report, exactly the question that motivated this work: "does this folder still have
   subfolders/documents according to what this run itself recorded."

5. **Frontend:** `RegisterSnapshotKind` gains `'PostReview'` (`api/runs.ts`); `JobDetailsView.tsx`'s
   `snapshotLabel()` adds a teal "After review (pre-normalization)" badge, and the pinned-snapshot timeline
   order becomes PreRun → PostReview → PreNormalization → PostNormalization → PostRun.

**Rationale:** Reusing `SourceScope` and `BuildOutcomeLedgerAsync` rather than writing new scoping/ledger
logic keeps this consistent with the already-established patterns (Steps 1/4/8's in-app prefix filter; the
existing PostRun ledger shape) instead of inventing a third approach. Column-name matching (rather than a
bound SQL `@sourceFolderId` parameter) was chosen over rewriting the register query to resolve a path to a
folder id server-side — the run stores only `SourceFolderPath` (a string), never a resolved id, and adding
one would touch the frontend browse flow, `CreateRunRequest`/`CreateRunCommand`, the `CleanupRun` domain
model, and a migration, for a reporting-only feature; the column-matching approach, with a documented
contract and a fail-open safety net, was judged the appropriately-scoped fix. Building `PostReview` from the
run's own tables (not a live MAGIQ re-query, unlike PreRun/AdHoc) was the natural choice since Step 7 already
projects the operator's selection onto exactly those tables — a fresh query would have no way to see that
projection at all.

**Status:** Implemented in the product working tree (uncommitted). Backend: new `Pipeline/SourceScope.cs`;
`Pipeline/RunPhaseExecutor.cs` (delegates to `SourceScope`, private duplicate methods removed);
`Domain/RegisterSnapshotKind.cs` (new `PostReview` value); `Features/Runs/ExportRegister/RegisterExportJob.cs`
(`BuildScopedRegisterRowsAsync` + `FindFolderPathColumn`, `BuildOutcomeLedgerAsync` enriched, `PostReview`
routed alongside `PostRun`, new filename case); `Features/Folders/ConfirmDeletions/ConfirmDeletionsHandler.cs`
(captures + enqueues `PostReview` alongside `PreRun`); `Integration/Magiq/Sql/ConfiguredQueryDefaults.cs`
(doc comment states the folder-path-column contract). Tests: new
`Features/Runs/RegisterExportJobTests.cs` (unscoped no-op, scoped narrowing, fail-open with no path column,
PostReview's enriched ledger); `ConfirmDeletionsHandlerTests.cs`'s
`Confirms_create_mode_and_enqueues_archival` now asserts both `PreRun` and `PostReview` are created and
enqueued. Frontend: `api/runs.ts`, `pages/JobDetailsView.tsx`; `npx tsc -b --force` passes clean. As with the
rest of this project's backend work, the API side could not be `dotnet build`ed or test-run in this sandbox
(no .NET SDK) — verified by careful manual line-by-line review only. `spec/dev-spec.md` and
`spec/NATA_Document_Lifecycle_Cleaner_Spec_v0.6.md` (rev 17) updated to match.

---

## [2026-08-14] Root cause of the Step 11 failures: acronym pre-selection doesn't cascade to structural subfolders — fixed by cascading selection at identification

**Context:** Chase provided a real run's exports (`example-run/audit-trail.csv` + the new `post-review.csv`,
proof the [2026-08-14] Document Register work above is already earning its keep) and asked whether the 154
Step 11 "folder still has N subfolder(s) remaining" failures from the earlier incident were legitimate, or
could just be skipped. Cross-referencing the two files answered a much bigger question than intended.

**Finding:** every one of the 154 failing folders has the identical shape: a "case" folder that matches the
deletable-acronym convention on its own name (e.g. `60912 SRV 2016`, matching `SRV`) has structural children
— folders literally named `1) Preparation`, `2) Report Package`, `3) Response`, `Notification Package`,
`Submission 1`, etc. — that hold the actual documents but never match any acronym themselves. Quantified
across this one run: **7,505 of 8,183 candidate documents (92%) ended up `MoveStatus.Kept`** (never
archived), and the large majority of those sit beneath a folder that *was* selected for deletion. Root
cause, confirmed by reading the code (not assumed):

1. `CandidateFolderBuilder.Build` pre-selected a folder only if **its own name** matched the acronym rule
   (`acronymRule.IsDeletable(folder.FolderName)`) — a structural child's name never does, so it was never
   itself selected, regardless of its acronym-matched parent.
2. `ConfirmDeletionsHandler`'s Kept-exclusion checks only a document's **direct parent** against the
   selected-folder set (decisions/log.md [2026-08-13]) — a document under `.../60912 SRV 2016/1)
   Preparation/plan.pdf` is excluded because `1) Preparation` isn't selected, even though `60912 SRV 2016`
   above it is.
3. Checked the Step 6 SPA for a workaround (there wasn't one): the tree's subtree-cascade checkbox
   (`node.selectableIds`, `folderTree.ts`) only fires from a row that **isn't itself** pre-selected — the
   case folder's own row is pre-selected, so its checkbox is hard-wired to self-only toggling
   (`folderControls` → `setIds([f.folderId], value)`), and since the case folder is a top-level candidate
   with no matched ancestor of its own, there's no row above it to click instead. None of the bulk actions
   (Select naming-convention/empty folders) reach a differently-named child either. `ApplySelectionsAsync`
   writes exactly the folder ids in the request, no expansion. Today, the only way to include these
   documents is to individually tick every structural subfolder under every case folder, for the whole run.

So the 154 Step 11 failures (decisions/log.md [2026-08-14], the live emptiness guard) were the guard
correctly reporting the truth — those case folders genuinely still held content, because the tool never
selected or archived it. **Skipping/suppressing the failures would have hidden that ~92% of the run's
documents were being silently left behind while the run reported clean** — the opposite of what was asked
for, so this was flagged back to Chase rather than just answered narrowly.

**Decision:** offered three options (cascade selection at identification; fix only the archival Kept-exclusion
projection to check any selected ancestor; write up only) — Chase picked **cascading selection at
identification**, the most complete fix:

`CandidateFolderBuilder` now cascades: a folder whose own name matches the acronym rule has **every
non-protected descendant folder** — not just itself — selected too, regardless of the descendant's own
name. New `ResolveSelectedIds` builds a parent→children map from the Step 4 rows' `ParentFolderId` (the
same rows already used for the upward Rule 2 walk) and DFS-walks down from each self-matched, non-protected
folder, marking every visited non-protected id selected; a `visited` set (mirroring `ResolveProtectedIds`'
`HashSet.Add`-based cycle guard) ensures a shared descendant of two overlapping matches, or a FOLDERMAP
cycle, is only walked once. **Protection still always wins**: the cascade does not stop traversing at a
protected folder (a protected folder's own descendants are not automatically protected — Rule 2 only
propagates up, not down — so a non-protected grandchild beneath a protected child still inherits from the
matched ancestor further up), but the protected folder itself is never added to the selected set, exactly
as before.

This single change fixes all three symptoms at once, with no other code change needed: Step 7's
Kept-exclusion already checks a document's direct parent against `IsSelectedForDeletion` — now that
`1) Preparation` etc. are themselves selected, their documents are no longer excluded; Step 11's
`GetDeletableAsync` already filters on `IsSelectedForDeletion = 1` — now the structural subfolders are
included in the deletable set too, and with the [2026-08-14] deepest-first ordering + live emptiness guard
already in place, they delete in the correct order and the case folder actually empties, clearing the
failures. Step 6 review will now show every structural child under a matched case pre-ticked (a real,
visible behavior change from before) rather than only the case folder's own row — this is the intended
effect of the fix, not a side effect to work around.

**Rationale:** the alternative (fix only `ConfirmDeletionsHandler`'s Kept-exclusion to check any selected
ancestor, not just the direct parent) would have fixed archival alone, leaving the structural subfolders
themselves unselected — Step 11 would still refuse to delete the case folder because an unselected
subfolder remains, so the reported failures would persist even once documents archived correctly.
Cascading at identification is the only option that resolves the failures themselves, and it matches the
acronym convention's actual intent — "select this case for deletion" was always meant to mean the whole
case, not just its top folder — rather than leaving that intent implicit and re-deriving it ad hoc at each
downstream consumer (archival projection, cleanup deletion, review display) separately.

**Status:** Implemented in the product working tree (uncommitted). Backend:
`Pipeline/FolderAnalysis/CandidateFolderBuilder.cs` (new `ResolveSelectedIds`, `Build` now computes
`isSelected` from it instead of a bare acronym-name check), `ICandidateFolderBuilder.cs` (doc comment).
Tests: `CandidateFolderBuilderTests.cs` gained
`An_acronym_match_cascades_selection_to_its_non_matching_structural_children`,
`A_protected_descendant_is_excluded_but_its_own_non_protected_children_still_inherit`, and
`A_non_matching_folder_with_no_matching_ancestor_is_never_selected`; none of the pre-existing tests in that
file exercised a matched-parent/unmatched-child shape, so none needed changes. As with the rest of this
project's backend work, the API side could not be `dotnet build`ed or test-run in this sandbox (no .NET
SDK) — verified by careful manual line-by-line review only, including manually tracing the DFS/visited-set
logic against both traversal orderings (matched ancestor processed before vs. after an already-matched
descendant) to confirm order-independence. `spec/dev-spec.md` and
`spec/NATA_Document_Lifecycle_Cleaner_Spec_v0.6.md` (rev 18) updated to match — this is a behavior change to
a documented rule (the deletable-folder-acronym convention), not a bug fix to unstated behavior, so both
specs' description of what gets pre-selected needed updating, not just a history footnote.

---

## [2026-08-14] Step 8b duplicate-delete/merge resolutions used a stale ancestor path after an in-pass folder rename

**Context:** after the selection-cascade fix above, Chase re-ran the pipeline and shared a fresh
`audit-trail.csv`/`post-review.csv`/`pre-run.csv` plus (this round) `name-normalization-before.csv` and
`name-normalization-after.csv`. The re-run's coverage was dramatically better (Kept dropped from 92% to
12% of documents), but a small new failure mode appeared: 14 Step 10 `Move` rows failed
`"Source folder not found."` for 3 distinct documents, and — one level up the chain — a Step 8
`DeleteDuplicate` row failed `"Document not found."` for 2 of those same documents' duplicate siblings.
Chase asked directly whether this was "an error with not updating after naming normalization completes."

**Finding:** it was, and narrowly so. `RunPhaseExecutor.ExecuteNormalizationAsync` (Step 8b) runs renames
first (folders top-down, then documents), then the operator's resolved conflict actions (folder merges,
duplicate-deletes). As each folder rename succeeds, the executor already repaths two in-flight
collections in lockstep so they never go stale mid-pass: `pendingRenames` (`RepathPendingDescendantsAsync`)
and the run's candidate documents (`RepathCandidateDocumentsUnderFolderAsync`) — both established by the
[2026-08-11] fix referenced in this same log. `resolvedActions` (the loaded `CleanupRunNameConflictEntry`
rows for `MergeFolders`/`KeepOneDeleteOther`) was the one collection **not** repathed: it is read once at
the top of the method, and `ExecuteDuplicateDeleteAsync`/`ExecuteFolderMergeAsync` call SOAP directly
against `conflict.Items[].OriginalPath` (`victim.OriginalPath`/`loser.OriginalPath`) — whichever raw
ancestor path was captured back when the operator's resolution was recorded at the Step 8a gate. When an
ancestor folder of that item is *also* renamed earlier in the very same 8b pass (the common case — the
whitespace-collapse convention routinely touches a top-level facility folder before working down into its
children), the conflict item's stale `OriginalPath` still carries the old ancestor segment, which no
longer exists under that name. SOAP correctly reports the delete/merge target "not found" — not because
the document is gone, but because the address is stale. Confirmed via `pre-run.csv` that the flagged pairs
are genuinely separate MAGIQ document ids (not a query fan-out), so Step 8a's conflict detection was
correct; only the Step 8b *execution* of the resolution used a stale path. Because the delete then fails,
`ExcludeDeletedDuplicateAsync` (gated on success) never marks the duplicate's candidate row `Deleted`, so it
survives into the Step 10 movable set under its own now-correctly-repathed (ancestor-only) path and
competes with its kept sibling for the same archive destination — consistent with the repeated Step 10
"Source folder not found" failures observed for the same final name.

**Decision:** repath `resolvedActions` the same way `pendingRenames`/candidate documents already are.
Added `RepathResolvedConflictItemsUnderFolderAsync` to `RunPhaseExecutor.cs`, called alongside
`RepathCandidateDocumentsUnderFolderAsync` in the renames loop's folder branch: for every resolved
conflict's item whose `OriginalPath` falls under a folder that just renamed successfully, rewrite the
ancestor-prefix portion in place (both the in-memory `resolvedActions` list, so the resolution loop that
runs after all renames complete sees the live path, and persisted via a new
`ICleanupRunNameConflictStore.UpdateItemPathsAsync` / `ConflictItemPathUpdate`, so a resumed run picks up
the same corrected path). A second, smaller consequence of the same root cause: `ExcludeDeletedDuplicateAsync`
matches a successfully-deleted victim back to its candidate document row via a `candidateIdByRawPath`
lookup that was snapshotted *before* the renames loop ran — once the conflict item's own `OriginalPath` is
correctly repathed, that snapshot would not longer match. Moved the `candidateIdByRawPath` build to
immediately before the resolved-actions loop (after all folder renames have already repathed
`candidateDocs`), so both sides of that lookup are in the same "current" coordinate space.

**Rationale:** the alternative — teaching `ExecuteDuplicateDeleteAsync`/`ExecuteFolderMergeAsync` to
re-derive a live path some other way (e.g. re-querying MAGIQ by name) — would duplicate the repathing logic
that already exists for `pendingRenames` and candidate documents, and would still need the
`candidateIdByRawPath` timing fix regardless. Repathing `resolvedActions` in the same lockstep, using the
same `IsUnder`/prefix-rewrite shape as the existing helpers, keeps all three "things Step 8 renames a
folder out from under" collections (pending renames, candidate documents, resolved conflict items) governed
by one consistent pattern.

**Status:** Implemented in the product working tree (uncommitted). Backend:
`Persistence/CleanupRunNameConflictEntry.cs` (new `ConflictItemPathUpdate` record),
`Persistence/ICleanupRunNameConflictStore.cs` / `CleanupRunNameConflictStore.cs` (new
`UpdateItemPathsAsync`), `Pipeline/RunPhaseExecutor.cs` (new `RepathResolvedConflictItemsUnderFolderAsync`,
called from the renames loop; `candidateIdByRawPath` construction moved to just before the resolved-actions
loop). Tests: `Tests/Fakes/FakeCleanupRunNameConflictStore.cs` gained an in-memory `UpdateItemPathsAsync`;
`RunPhaseExecutorNormalizationTests.cs` gained
`Execute_repaths_a_resolved_duplicate_deletes_stale_ancestor_path_before_deleting`, proving the
`DeleteDocument` SOAP call addresses the live (post-rename) ancestor path rather than the stale one
captured at resolution time. As with the rest of this project's backend work, could not be `dotnet
build`ed or test-run in this sandbox (no .NET SDK) — verified by manual line-by-line review, including
tracing the exact prefix-rewrite arithmetic against the real NATA paths from the shared CSVs. This is a
bug fix to already-documented behavior (the repath-in-lockstep guarantee from [2026-08-11]), not a change
to any spec-level rule, so no spec text needed updating beyond noting it here.

---

## [2026-08-14] Move Failures panel could go missing after a failed archival run

**Context:** Chase reported that when a run's archival failed with unmoved documents, the SPA never showed
a view to see and retry the failures. `MoveFailuresPanel.tsx` and its backing endpoints
(`GET/POST .../archival/move-failures[/retry]`) already exist (decisions/log.md [2026-08-10]), so this was
investigated as a wiring/rendering bug rather than a missing feature.

**Finding:** two independent defects, either of which reproduces the report:

1. **Swallowed load error.** `MoveFailuresPanel`'s `load()` sets `error` on a failed
   `GET .../archival/move-failures` (network blip, expired session, etc.) but leaves `rows` empty. The
   render guard `if (rows.length === 0 && !allCleared) return null;` ran unconditionally after `loaded`
   became `true`, so a failed fetch and a genuinely-empty, healthy result were indistinguishable — the
   panel rendered nothing and the `error` state was set but never shown. A run that fails archival after a
   long-running move phase is exactly the shape where a session/ticket might have aged out by the time the
   operator checks back, making this the likely trigger.
2. **No non-owner explanation.** `JobDetailsView.tsx`'s three other AwaitingInput-style gates
   (`inReview`, `inNormalizationGate`, `inNormalizationExecution`) each render an explicit "Awaiting the
   owner's action" `Alert` for a non-owner viewer. The archival-failure state (`Failed` + `Archival`) had no
   such condition — `MoveFailuresPanel` (and `PurgeControl`) were simply omitted for a non-owner with no
   explanation, unlike every other gated state.

**Decision:**

1. `MoveFailuresPanel.tsx`: added an explicit error branch between the "not loaded" and "nothing to show"
   guards — `if (error && rows.length === 0 && !allCleared)` now renders the error with a "Retry loading"
   button that re-invokes `load()`, instead of falling through to the silent `return null`.
2. `JobDetailsView.tsx`: added `inArchivalMoveFailures` (`run.status === 'Failed' && run.currentPhase ===
   'Archival'`) alongside the existing phase-gate booleans, and used it to render the same "Awaiting the
   owner's action" `Alert` pattern for a non-owner in that state, matching the other three gates.

**Rationale:** both fixes follow the pattern already established by the Normalization Failures /
Normalization Review gates elsewhere in the same file — an error should always be visible somewhere, and
every AwaitingInput/Failed-with-action state should tell a non-owner why the action surface is missing
rather than just omitting it silently.

**Status:** Implemented in the product working tree (uncommitted). Frontend:
`src/DocumentLifecycleCleaner.Web/src/components/MoveFailuresPanel.tsx`,
`src/DocumentLifecycleCleaner.Web/src/pages/JobDetailsView.tsx`. Verified with `npx tsc -b --force`
(clean) — no Vitest/RTL suite exists for either component yet, so this was not covered by an automated
regression test; worth adding if this area gets touched again.

---

## [2026-08-14] Move Failures panel — the actual recurring cause was a missing live refresh, not the load-error/owner gaps

**Context:** the two fixes above did not resolve it — Chase reported the exact same symptom again: run
progress shows `Failed - Archival (step 10)`, the progress bar sits at 100% red, "Most recent activity" is
right there, but the Document Move Failures section is simply absent until the page is hard-refreshed and
the run reopened, at which point it appears correctly with working retry buttons.

**Finding:** the real defect. `MoveFailuresPanel` sits in `JobDetailsView`'s fallback `else` branch (not
`inReview`/`inNormalizationGate`/`inNormalizationExecution`), which archival occupies throughout — Running
*and* Failed both land there, with **no `key` prop** to force a remount between them. So the component is
already mounted from the moment archival starts (while the run is still `Running` and there are zero
failures yet), its one-shot `useEffect(() => { void load(); }, [load])` fires exactly once with `load`'s
dependencies (`[runId, token]`) that never change again for the life of the run, and it correctly renders
nothing (zero failures, healthy fetch). `JobDetailsView`'s own `run` object *does* update live — it's
polled every 5s (`POLL_MS` in `load(false)`) — so `run.status`/`run.currentPhase` correctly flip to
`Failed`/`Archival` and the surrounding UI (StatusBadge, progress bar, RunPhaseStepper) reacts immediately.
But `MoveFailuresPanel` itself has no equivalent live refresh of its own — unlike `RunProgressPanel` (built
on the SignalR+poll `useRunProgress` hook) or `CleanupOutcomesPanel` (takes a `live: boolean` prop and
polls every 5s while true) — so its stale, empty first fetch is exactly what stays on screen. A hard
refresh remounts everything from scratch, so the panel's `load()` runs fresh against the now-actually-
failed state and works correctly — which is exactly what Chase observed. The two earlier fixes in this log
entry (surfacing a swallowed load error; a non-owner explanation) are still correct, independent
improvements, but neither was the reproducing cause here — the panel wasn't failing to load or being
hidden from a non-owner, it just never asked again after its first (empty) answer.

**Decision:** give `MoveFailuresPanel` the same `live`-prop polling pattern `CleanupOutcomesPanel` already
uses, rather than inventing a new mechanism: a `live: boolean` prop, and a
`useEffect` that polls `load()` every 5s (`POLL_MS`) while `live` is true, cleared on unmount/prop change.
Wired from `JobDetailsView` as `live={run.status === 'Running' || run.status === 'Failed' || run.status
=== 'AwaitingInput'}` — covering the whole archival window (before, during, and after a failure) plus the
post-archival "continue to cleanup" pause, so the panel picks up a new failure, a resolved retry, or the
all-clear state within one poll tick without any page reload.

**Rationale:** `CleanupOutcomesPanel` already solved this exact shape of problem (a fallback-branch panel
that outlives a status transition without remounting) with a caller-supplied `live` flag plus its own
interval — reusing that pattern keeps the two "failures panel that can appear mid-run" components
consistent rather than solving the same problem two different ways.

**Status:** Implemented in the product working tree (uncommitted). Frontend:
`src/DocumentLifecycleCleaner.Web/src/components/MoveFailuresPanel.tsx` (new `live` prop + `POLL_MS`
interval effect, doc comment updated), `src/DocumentLifecycleCleaner.Web/src/pages/JobDetailsView.tsx`
(passes `live` through). Verified with `npx tsc -b --force` (clean). Still no automated test for this
panel — the failure mode here (a component silently going stale because nothing remounts or re-triggers
it across a live state transition) is exactly the kind of thing an RTL test with fake timers would catch;
worth adding once this area is touched again rather than relying on manual review a third time.

---

## [2026-08-14] Root cause: Step 1 pre-normalizes `CleanupRunDocument.DocumentPath`, so two colliding documents share one path string that Step 8/10 can never disambiguate — fixed by threading the MAGIQ document id end-to-end

**Context:** Chase asked why three specific documents from the latest `audit-trail.csv`/`pre-run.csv` re-run
failed Step 10 with `"Source folder not found"`. Two (the "Blood Gas…"/"Gen Chem…" St George documents) had
each been moved once successfully and then re-attempted 2–3 more times, always failing. The third (Bathurst's
"…roaint signed.pdf") had, per Chase's own read of the CSVs, been renamed during Step 8 to a disambiguated
`… (2).pdf` name, but no move ever addressed that `(2)` name — only the plain name, which matched a sibling
document instead.

**Finding:** this is a distinct, deeper defect from the two path-repathing bugs earlier in this log ([2026-08-11],
[2026-08-14] "stale ancestor path") — those were timing bugs in *when* a path gets rewritten; this one is
architectural. `MagiqDocumentQueries.GetCandidateDocumentsAsync` (Step 1 Identification) applies
`MagiqPath.Normalize` to every candidate's path before it is stored in `CleanupRunDocument.DocumentPath`
(Story 34527, so the stored path matches what SOAP itself would report). `GetRawCandidateDocumentPathsAsync`
(feeding Step 8's `RenamePlanner`) deliberately returns the *un-normalized* path from the same underlying
query, for the same underlying rows. Whenever two distinct MAGIQ documents naively collapse onto the
identical normalized name — precisely the case Step 8's conflict detection exists to catch — their
`CleanupRunDocument` rows carry the identical `DocumentPath` string **from Identification onward**,
regardless of whether Step 8 ever runs or how it resolves the conflict. Every piece of Step 8b/Step 10
plumbing that correlated a rename/merge/delete outcome back to "the matching candidate document" did so by
path string — `RunPhaseExecutor.RepathRenamedCandidateDocumentAsync` (exact `DocumentPath` match),
`ExcludeDeletedDuplicateAsync`'s `candidateIdByRawPath` lookup, and `ReconcileCandidateDocumentPathsAsync`'s
`ApplyDocumentRewrite` — and none of them can disambiguate two rows that share that string, whether the
string used is raw or normalized: the ambiguity is inherent to using *any* path as the lookup key once two
rows share it. Traced through concretely: a `KeepOneDeleteOther` resolution deletes one sibling from MAGIQ
(the "Blood Gas"/"Gen Chem" case) — if the exclude-lookup can't find (or finds the wrong) candidate row,
the deleted document's own row is never marked `Deleted` and stays `Pending` at the same stored path its
still-live sibling was already moved from, so Step 10 retries a move against a source that is genuinely gone
(not because the document doesn't exist, but because a *different* document used to be there and already
left). A `RenameDocument` disambiguation (the Bathurst case) hits the same wall from the other side: the SOAP
rename to `… (2).pdf` succeeds, but the exact-path repath of the candidate row never matches (the row's
stored path was already normalized to the *pre-disambiguation* name at Step 1), so the row is left pointing
at a name Step 10 will never find a move-worthy source for, while the sibling's own untouched row gets moved
in its place and then re-attempted once that path, too, is empty. Confirmed by careful reasoning (no DB
access in this sandbox) that ancestor-prefix repathing (`RepathCandidateDocumentsUnderFolderAsync`,
`RepathMergedCandidateDocumentsAsync`) is *not* subject to this same bug: those rewrite every row under a
prefix in bulk rather than looking up one specific row by path, so there is nothing to disambiguate — a
folder's final normalized destination is, by construction, the same value Step 1 already stored.

**Decision:** thread the MAGIQ document id end-to-end through the Step 8 pipeline so document-level
correlation keys off identity instead of path string:

1. **`IMagiqDocumentQueries.GetRawCandidateDocumentPathsAsync`** now returns
   `IReadOnlyList<RawCandidateDocument>` (new record: `DocumentId` + `RawPath`) instead of bare
   `IReadOnlyList<string>`, so the id survives alongside the raw path from the same query row
   (`Integration/Magiq/Sql/CandidateDocument.cs`, `IMagiqDocumentQueries.cs`, `MagiqDocumentQueries.cs`).
2. **`RenamePlanner`** threads the id through every stage that touches a document leaf:
   `EnumeratePathItems` now yields `(type, path, leaf, documentId)` (folders always `null`); the internal
   `ProjectedItem` carries `DocumentId`; `BuildConflict` copies it onto the emitted `NameConflictItem`;
   `BuildBaseRenames`/`ApplyRenameResolutions` copy it onto the emitted `PendingRename`
   (`NormalizationPlan.cs`, `RenamePlanner.cs`). The planner's *internal* conflict-detection/resolution
   matching (which already keys off raw path, unambiguous at that pre-mutation stage) needed no logic
   changes — only its output needed the id attached. `AppliedResolution` gained
   `RenameTargetDocumentId` for the (rarer) case where a conflict-driven rename resolution targets an item
   not already in the base rename plan.
3. **Persistence carries the id through**: `CleanupRunRenameEntry`/`PendingRename` and
   `CleanupRunNameConflictItemEntry` gained a nullable `DocumentId`; `dbo.CleanupRunRename` and
   `dbo.CleanupRunNameConflictItem` gained a matching nullable `DocumentId NVARCHAR(200)` column (folded
   into `0001_baseline.sql`, consistent with how this feature's schema has been evolved so far); the Dapper
   stores read/write the new column.
4. **`RunPhaseExecutor` matches by id, with a path fallback**: `RepathRenamedCandidateDocumentAsync` and
   `ReconcileCandidateDocumentPathsAsync`'s `ApplyDocumentRewrite` now match a `CleanupRunDocument` row by
   `DocumentId` when the rename entry carries one (falling back to the old exact-path match only for a row
   persisted before this fix shipped); `ExcludeDeletedDuplicateAsync` now takes both a
   `candidateIdByDocumentId` map and the pre-existing `candidateIdByRawPath` map, trying identity first.
   `GetScopedRawCandidateDocumentPathsAsync` and its two call sites were updated for the new
   `RawCandidateDocument` shape (folder-scoped filtering and `ExecuteFolderMergeAsync`'s
   `ImmediateChildren` still operate on bare raw paths, unaffected — folder-level repathing was never the
   ambiguous half of this bug).

**Rationale:** a narrower patch — comparing normalized strings instead of raw ones, or de-duplicating by
some other string transform — was considered and rejected: it does not remove the ambiguity, since the
whole failure mode is *two rows already sharing one string*, and no string-shaped key can ever tell them
apart. Only the MAGIQ document id (already present on every candidate row, merely discarded by the raw-path
query) is guaranteed unique per document, so it is the only reliable correlation key. Keeping a path-based
fallback alongside the id-based match (rather than requiring the id everywhere) means an in-flight run whose
rename/conflict rows were persisted before this fix still degrades to the previous (occasionally-buggy but
not worse) behavior instead of silently doing nothing.

**Status:** Implemented in the product working tree (uncommitted). Backend:
`Integration/Magiq/Sql/CandidateDocument.cs` (new `RawCandidateDocument` record), `IMagiqDocumentQueries.cs`,
`MagiqDocumentQueries.cs`, `Pipeline/NormalizationPlan.cs`, `Pipeline/RenamePlanner.cs`,
`Domain/NameConflict.cs`, `Persistence/CleanupRunRenameEntry.cs`, `Persistence/CleanupRunNameConflictEntry.cs`,
`Persistence/CleanupRunRenameStore.cs`, `Persistence/CleanupRunNameConflictStore.cs`,
`Persistence/Migrations/0001_baseline.sql`, `Pipeline/RunPhaseExecutor.cs`. Tests:
`Fakes/FakeCleanupRunRenameStore.cs`/`FakeCleanupRunNameConflictStore.cs` updated to carry the id through;
seven `IMagiqDocumentQueries` test stubs updated for the new return type; `RenamePlannerAnalyzeTests.cs`'s
`Input` helper wraps bare test paths with the path itself as a synthetic id (these tests exercise
conflict-detection logic, not id-based repathing); `RunPhaseExecutorNormalizationTests.cs` gained two new
regression tests — `Execute_excludes_the_correct_duplicate_when_two_candidates_share_a_normalized_path` and
`Execute_repaths_only_the_renamed_documents_own_row_when_a_sibling_shares_its_normalized_path` — each seeding
two `CleanupRunDocument` rows with the *same* stored path but distinct document ids, proving the fix picks
the right row by identity rather than by the shared path. As with the rest of this project's backend work,
could not be `dotnet build`ed or test-run in this sandbox (no .NET SDK) — verified by manual line-by-line
review. This is a bug fix restoring the intended behavior of the existing Step 8/10 pipeline (spec Rules 7/8
already describe conflict resolution and archival as they should behave); no spec text needed changing
beyond this record of the root cause and fix.

---

## [2026-08-14] Closing the loop on the upward-only-closure gap: Rule 9, a review-time completeness warning, a terminal `Skipped` status, and the post-archival document gate

**Context:** The [2026-08-14] entry *"Real incident: a Step 11 parent folder deleted before its still-present
child"* diagnosed the Rule 2 downward-closure gap and deliberately deferred the SQL fix in favour of the live
pre-delete guard. The guard then earned its keep on a fresh live run: `/03.01 Facilities/.../02131 Darlinghurst
Laboratory/60912 SRV 2016/3) Response` failed its Step 11 delete with *"Folder still has 1 subfolder(s)
remaining."* Its own `FolderCount` was 2, but only one of its subfolders ("sub1") ever appeared as a candidate
row — the identical invisible-folder scenario. No data was lost, which is the guard working exactly as
designed. The problem was what came next: `3) Response` **and** its parent `60912 SRV 2016` were left
permanently `Failed`, retry was deterministically futile (the guard sees the same live subfolder every time),
there was no way to have seen it coming at review, and no in-product way to resolve it — someone had to open
MAGIQ and decide by hand, with the run left carrying a red mark forever. Chase asked to think the option space
through and then implement the recommended ordering.

**Correction to the prior entry's rationale (flagged, not silently rewritten).** That entry justified deferring
the SQL fix partly on the grounds that a downward closure *"would need a fixed-point computation to reach a
subfolder under a folder that only qualified as an ancestor."* That is **wrong**: `FOLDERMAP` is a full closure
table (`PARENTID, FOLDERID, DEEP`) — `SQL-QUERY-DESIGN-34547.md` §2 calls it "the key asset" and notes it
replaces recursive CTEs — so downward closure is the exact mirror of the ancestor arm already in `FolderSet`,
one extra `UNION` reaching all depths, and it is *seek-friendlier* than the upward arm (the `FOLDERMAP` PK
leads on `PARENTID`). Perf is a non-argument here and should be dropped from the decision. The prior entry's
conclusion still stands, but for a different and better reason (below). Per CLAUDE.md the log is append-only,
so the original text is left intact and corrected here.

**The real reason not to widen `CandidateFolders`:** closing downward over `FolderSet` (candidates ∪ ancestors)
asks for *every descendant of every ancestor* — and the ancestor set reaches root level (`/03.01 Facilities`),
so its descendants are effectively the whole library. `FolderSet` would become ≈ all of `FOLDERS` for the
domain, and the **Step 6 review list would become the entire library instead of the candidate set**. That is a
product-usability failure, not a performance one. If the closure is ever wanted, the right shape is a
**separate** `FolderDescendants(@folderIds)` query — same form as the existing `FolderPaths` — driven from C#
*after* `CandidateFolderBuilder` computes protection + selection, over just the selected roots: bounded by the
acronym subtrees, compatible with an operator-customized `CandidateFolders`, and it keeps the acronym rule
(a live case-sensitive `Contains` setting, whose T-SQL `LIKE` equivalent would diverge under a
case-insensitive collation) out of operator-editable SQL. **Still deferred** — deliberately, and now for a
reason that holds up.

**Decision:**

1. **New spec Rule 9 — the completeness invariant:** *never delete a folder whose contents this run has not
   fully evaluated.* Named as its own rule rather than folded into Rule 2. Rule 2 is a **retention** rule about
   *known* post-cutoff content and is auditable precisely because its reason can be stated; this is an
   **epistemic** guard about content the run cannot see. Folding them together would make Rule 2 unfalsifiable,
   turn `ProtectionReason` into a lie for these folders, and leave an auditor unable to distinguish *retained by
   policy* from *skipped through ignorance* — which need different follow-ups. The invariant now has two
   enforcement points: the existing Step 11 live guard (the guarantee) and the new review-time warning (the
   prediction).

2. **`FolderCompletenessAnalyzer` — the derived prediction, free.** The detection signal was already persisted:
   `CleanupRunFolder.FolderCount` is a live, date-unfiltered `COUNT(*)` over `FOLDERS.PARENTID` captured at Step
   4, while the run only holds rows for what `CandidateFolders` returned. `FolderCount` minus the child rows
   actually held (derived by path — no new column, no SQL change, no SOAP call) *is* the invisible set. A second,
   independent blocker is covered in the same pass: a **known child that will remain**, typically one the
   operator deliberately deselected — the counts agree there, so the arithmetic alone would miss it. Blockers
   then **propagate up the ancestor chain** using the same up-walk shape as
   `CandidateFolderBuilder.ResolveProtectedIds`, because a folder that can't be emptied can't be deleted: this is
   why one invisible grandchild produced two `Failed` rows, and the propagation is what lets the UI show one root
   cause instead of N warnings. The walk stops at the first ancestor the run is *not* attempting — that ancestor
   is staying regardless, so anything above it is blocked by *it*, and attributing the block past it would
   misdirect the operator. Pure, static, no DI.

3. **`GET /runs/{runId}/folders/completeness` — targeted live verification.** Derived analysis first, then
   `ListFoldersAsync` on **only the directly-blocked** folders (capped at 50/request) to name the actual
   undiscovered children — O(suspects), not O(candidates); a blanket sweep at Step 6 would be thousands of SOAP
   calls with the operator waiting. Same call the Step 11 guard makes, several steps earlier. Uses the
   **UI ticket** (`ICurrentOperator`), never the run's process ticket (ADR-006, two tickets not crossed); with no
   usable ticket it degrades to `liveVerified: false` rather than failing, since the counts need no ticket and
   are the valuable part. **On demand** rather than computed during identification, specifically so the operator
   can re-check after fixing something in MAGIQ without re-running Steps 1–5.

4. **Surfaced at Step 6 *and* Step 7 (`FolderCompletenessPanel`), informational only.** Chase's call:
   pre-selection is **left alone** — consistent with the established review-signal pattern
   (`DocumentDeleteBlocked`/`FolderDeleteBlocked` are informational bit columns whose doc comments already say
   "execution relies on the live rules, not this snapshot"). The panel never changes selection and never blocks a
   submit, and says so: `FolderCount` is a Step 4 snapshot, so a folder created in MAGIQ since identification is
   invisible to it — a **predictor, not a proof**. No `FolderStatus` value and no new column was added for it.

5. **New terminal `FolderStatus.Skipped` + `POST /runs/{runId}/folders/skip`.** The missing primitive: a way to
   close out a delete that can never succeed. Only a currently-`Failed` folder is eligible (this is never a way
   to pull a folder out of the delete set pre-attempt — deselecting at Step 6 is that), `folderIds` and `reason`
   are both **required** (no all-by-omission; the reason is the auditable point), the blocking `FailureReason` is
   **preserved** rather than cleared, and the operator + reason go to the audit trail as a new
   `RunOperationType.FolderSkipped` row — so the decision is auditable with no new columns. `GetDeletableAsync`
   excludes `Skipped` alongside `Deleted`/`Protected` so a resumed pass never re-attempts it. Not gated on run
   status, same reasoning as the delete-failure retry. Chase chose a real enum value over a `Resolved` flag:
   terminal and self-describing in the register/audit trail is worth the ripple.

6. **"What's in it?" on each failure row** — the same targeted live check, surfaced per folder. This is what
   makes the difference between *legitimately retained content* (settle it) and *a subtree the run never saw*
   (cull it separately) visible without leaving the product.

7. **Unsticking is a scoped follow-up run, not adoption into the old run.** Deliberately **not** building
   "adopt the missed child into this run": the child's ≤-cutoff documents need archiving, and by the time a
   Step 11 failure is being worked the per-run archive library may already be deleted and purged
   (`DeleteAndPurgeArchiveAsync` → `DeleteDomain` at Step 12) — there is no destination left to move into.
   Re-entering archival from cleanup would mean resurrecting a purged library, which is a data-loss vector, not a
   feature. The mechanism already exists: a **starting-folder-scoped run** (decisions/log.md [2026-08-13]) rooted
   at the parent, which with (2)–(4) in place *sees* the previously-invisible subfolder at its own Step 6. So:
   settle + inspect on the old run, scoped run for the work. Documented in the spec so the operator knows.

8. **Closed the post-archival document gate (`409 UnresolvedMoveFailures`).** Investigating the guard turned up a
   second, unrelated asymmetry: `DeleteFolderIfEmptyAsync` live-checks **subfolders only** (`ListFoldersAsync`),
   and `ContinueToCleanupHandler` checked only run status/phase — so an operator could proceed into Step 11 with
   documents still unarchived in a selected folder, and `DeleteFolder` is already known to **cascade** rather than
   refuse. Chase asked to verify reachability first and fix only if open; it was open. Fixed at the **gate**
   rather than the guard: there is no `ListDocuments`/`GetDocuments` op on `IMagiqSoapClient`, and inventing an
   unverified SOAP op would contradict the project's verified-op discipline (`SOAP-VERIFICATION-34525.md`) — and
   blocking at the decision point is cheaper than a second round trip per folder delete *and* is the correct
   product behaviour anyway, since pausing before the irreversible purge is precisely what that gate is for.
   Deliberately `MoveStatus.Failed` only, **never `Pending`**: a document under a folder deselected at Step 7 is
   legitimately left `Pending` by the Kept-exclusion, so gating on `Pending` would block every normal run.

**Rationale:** The ordering was chosen cheapest-first and each step is independently useful. The derived check
(2) needs no SQL change, no schema change and no round trip, yet catches the exact live incident — and its
existence is what makes the deferred SQL closure (which costs review-list bloat) plausibly never worth doing.
The targeted live verify (3) buys the operator a name instead of a number for a handful of SOAP calls. The
`Skipped` status (5) and inspect action (6) are what turn a permanent dead end into a decision with a record.
Rule 9 (1) is the piece that makes all of it coherent rather than a bag of fixes, and it is the reconciliation
the prior entry explicitly left pending rather than silently resolving.

**Status:** Implemented in the product working tree (uncommitted). Backend: new
`Pipeline/FolderAnalysis/FolderCompletenessAnalyzer.cs`; new `Features/Folders/GetFolderCompleteness/*`
(Query/Request/Response/Handler/Endpoint); new `Features/Folders/SkipFolderDelete/*`
(Request/Command/Response/Handler/Endpoint); `Domain/FolderStatus.cs` (`Skipped`),
`Domain/RunOperationType.cs` (`FolderSkipped`), `Persistence/CleanupRunFolderStore.cs`
(`GetDeletableAsync` excludes `Skipped`), `Persistence/ICleanupRunFolderStore.cs` (doc comment),
`Persistence/Migrations/0001_baseline.sql` (status/operation-type comments only — no DDL change; both values fit
the existing column widths), `Features/Runs/Archival/ContinueToCleanupHandler.cs` +
`ContinueToCleanupEndpoint.cs` (the move-failure gate). Tests: new
`Pipeline/FolderAnalysis/FolderCompletenessAnalyzerTests.cs` (11 cases incl. the live incident's exact shape,
ancestor propagation, the stop-at-unattempted-ancestor rule, deselected/skipped/deleted children, and the
non-negative guard), new `Features/Folders/GetFolderCompletenessHandlerTests.cs` (clean run makes zero SOAP
calls, live-verify names the invisible child while collateral ancestors cost no call, failure/no-ticket
degradation, the 50-folder cap), new `Features/Folders/SkipFolderDeleteHandlerTests.cs`; `Fakes/
FakeCleanupRunFolderStore.cs` (`UpdateStatusesAsync` now records instead of throwing),
`Fakes/FakeMagiqSoapClient.cs` (`ListFoldersAsync` seedable + call-recording),
`Features/Runs/Archival/MoveFailuresHandlerTests.cs` (constructor + two new gate tests). Frontend: new
`components/FolderCompletenessPanel.tsx`; `api/folders.ts` (`getFolderCompleteness`, `skipFolderDeletes`),
`api/runs.ts` (doc comment), `wizard/Step6FolderReview.tsx`, `wizard/Step7ConfirmDeletions.tsx`,
`components/CleanupOutcomesPanel.tsx` (inspect + settle actions, muted Skipped rows). `npx tsc -b --force`
passes clean; as with the rest of this project's backend work the API side could not be `dotnet build`ed or
test-run in this sandbox (no .NET SDK) — verified by careful manual line-by-line review only.
`spec/NATA_Document_Lifecycle_Cleaner_Spec_v0.6.md` (rev 19 — new Rule 9, Step 6 completeness bullet, rewritten
Step 11 gap note + failures section, History) and `spec/dev-spec.md` (two new endpoint rows, the
`archival/continue` 409, `Skipped` in the folder-item/DDL status lists, `FolderSkipped` in the operation-type
list, `FolderCompletenessPanel` in the component map) updated to match.

---

## [2026-08-14] Frontend↔backend enum mirrors made drift-proof, after `MoveBack` proved they weren't

**Context:** Adding `RunOperationType.FolderSkipped` meant hand-editing `OperationAuditPanel.tsx`'s
`OPERATION_OPTIONS` — a plain array carrying a comment that claimed it was "kept in sync with the
RunOperationType / OperationTargetType / RunOperationOutcome enums." Checking that claim showed it was false:
**`MoveBack` had been missing since the day Tier 2 rollback shipped.** Both `RunOperationType.MoveBack` and
the `MoveBackAuditRow` that writes those rows are committed, so a rollback emits one audit row per document
that the operator could not select in the Operation filter — nor in the filtered CSV export, which honours
it. The rows were only findable by free text, and only by accident: `MoveBackAuditRow` happens to set
`Detail = "Rollback"`, and the server's search predicate covers `SourcePath`/`DestinationOrNewName`/`Detail`/
`ErrorMessage` but never `OperationType`. Chase asked for a full review of the mirrors and the best action,
noting there is no released version so any change is fair game.

**Review — every backend enum diffed against its frontend mirror.** Nineteen enums in `Api/Domain` plus
`SettingKind`. Exactly one had drifted: `RunOperationType` (missing `MoveBack`, and `FolderSkipped` would have
been next). `OperationTargetType`, `RunOperationOutcome`, `RunStatus`, `RunPhase`, `RegisterSnapshotKind`,
`RegisterExportStatus`/`Format`, `RunChangeTier`, `RunRollbackStatus` and `SettingKind` all matched. So the
value drift was a single instance — but **nothing anywhere prevented it**, and three more lists were one enum
addition away from the same silent failure (`RUN_STATUSES` is a hand-written `RunStatus[]`, where a missing
member compiles; `PHASES` in `RunPhaseStepper` was an `as const` array keyed by loose strings; the three
audit option arrays were untyped).

**Decision — enforce completeness where a missing value silently changes behaviour; stay tolerant elsewhere.**

1. **Unions declared in `api/runs.ts`** for `RunOperationType`, `OperationTargetType`, `RunOperationOutcome`
   and `RunPhase`, and in `api/folders.ts` for `FolderStatus` (now including `Skipped`). `RunOperationEntry`'s
   three enum fields and the folder DTOs' `status` fields are typed with them instead of `string`.

2. **The three audit option lists become `Record<Union, string>` label maps**, with the rendered
   `{ value, label }[]` arrays derived from them by a small `toOptions` helper. A `Record` over the full union
   cannot compile with a member missing, so declaring a new operation *forces* a label. Declaration order is
   display order, so nothing about the UI changed. This deliberately mirrors the pattern already established
   in `theme/status.ts` (`STATUS_META: Record<RunStatus, StatusMeta>`) rather than inventing a new one.

3. **The row-sentence `switch` keeps its runtime fallback but gains compile-time exhaustiveness** via a
   `const unhandled: never = e.operationType` in the `default` branch. Both properties matter: forgetting a
   case for a new operation is now a build error, while a server upgraded ahead of a cached bundle can still
   send an unknown value and get a readable degraded label instead of an exception.

4. **`RUN_STATUSES` is now derived** (`Object.keys(STATUS_META)`) instead of hand-listed, and
   `RunPhaseStepper`'s `PHASES` is derived from a new `PHASE_META: Record<RunPhase, …>`. Both were complete
   today and both could have silently lost a member.

5. **`FolderStatus` gets the union for value-correctness only, not exhaustiveness** — and that is the right
   call, not a shortfall. There is no single place that must handle every folder status: the cleanup panel
   deliberately shows only `Failed`/`Skipped`, Step 6's badge cares about `Protected`, Step 7 about
   delete-vs-keep. Forcing exhaustiveness would mean enumerating statuses in three components that
   legitimately don't care. Verified by experiment: adding a fake `FolderStatus` member produces no build
   error, whereas adding a fake `RunOperationType` or `RunStatus` member does. The union still earned its
   keep immediately — it caught a real latent bug in `CleanupOutcomesPanel.applyOutcomes`, whose parameter was
   typed `status: string` and so would have happily written a nonsense status into the folder list.

**Verification:** `npx tsc -b --force` clean. The guards were then *proved* rather than assumed, by
temporarily adding a member to each union and confirming the build breaks in the right place: a new
`RunOperationType` fails twice (the `Record` and the `never` check), a new `RunStatus` fails on `STATUS_META`,
and — as designed — a new `FolderStatus` fails nowhere. All three probes reverted; build clean afterwards.

**Rationale:** The one-line data fix (adding `MoveBack`) treats the symptom; the enum mirrors would have
drifted again on the next addition, and the failure mode is nasty precisely because it is invisible — no
error, no missing UI, just an operation the operator can never filter for. Converting the two hand-maintained
mirrors into derived, type-checked ones costs almost nothing and moves the failure from "discovered during a
live cull" to "discovered by the compiler." Deliberately **not** extended to the remaining loose enum mirrors
(`api/normalization.ts`'s `itemType`/`action`/`kind`/`resolutionType`/`status`, `MoveStatus`,
`PhaseEventType`, `schemaVerification`'s `kind`/`status`): those are subset comparisons with no exhaustive map
behind them, so typing them would be consistency work rather than safety work, and it would touch the
largest and most intricate component in the SPA for no behavioural gain. Left as a noted follow-up.

**Status:** Implemented in the product working tree (uncommitted), alongside the Rule 9 work in the same
branch. Frontend only — no API, DTO or behavioural change; the backend enums were already correct.
`api/runs.ts` (four new unions + three field types), `api/folders.ts` (`FolderStatus` union + three field
types), `components/OperationAuditPanel.tsx` (label maps + `toOptions` + exhaustive `default`),
`components/CleanupOutcomesPanel.tsx` (`applyOutcomes` parameter type — the latent bug), `theme/status.ts`
(`RUN_STATUSES` derived), `components/RunPhaseStepper.tsx` (`PHASE_META` record). `tasks.md`'s follow-up item
closed out.

---

## [2026-08-14] Withdrew the Step 6/7 completeness panel — it analysed the wrong thing, at a step where it could not verify

**Context:** The completeness warning shipped earlier the same day (entry above) went in front of a real run's
data and was wrong in two independent ways at once. Chase's screenshot: *"119 selected folders will fail to
delete at Step 11 … (81 directly, 38 only because a folder beneath them is blocked)"*, and against nearly every
entry, *"Contains N subfolders this run never evaluated (couldn't list them: **Target folder not found**)"*.

**Two findings, either sufficient on its own to remove it:**

1. **It described a set that was about to stop being true.** The panel loads on mount at Step 6, so the
   "selected folders" it analysed were the **acronym pre-selection** — the defaults the review step exists to
   let the operator change. Warning that 119 pre-selected folders will fail, immediately before the operator
   edits which folders are selected, is noise dressed as a finding. Chase's read, and it is correct.

2. **The live verification cannot work before Step 8 — structurally, not incidentally.** `GetFolders` returned
   *"Target folder not found"* for essentially every folder checked. That is the exact failure Name
   Normalization exists to fix: SOAP cannot address a path whose name still carries a whitespace variant or an
   invisible format character. Steps 6 **and** 7 both run before Step 8, so at review time the live half is
   guaranteed to fail for precisely the population worth checking — the dirty-named folders. The Step 11 guard
   makes the identical `ListFoldersAsync` call successfully only because by then normalization has run. This
   was not foreseen when the panel was designed, and it is the more damning of the two: the feature could not
   have worked where it was placed, at any level of polish.

**Decision: remove the panel outright from both Step 6 and Step 7** (Chase's call, given the second finding —
the option of keeping a counts-only panel at Step 7 was offered and declined). `FolderCompletenessPanel.tsx`
deleted; both call sites and imports removed. **Everything behind it is retained** —
`FolderCompletenessAnalyzer`, `GET /runs/{runId}/folders/completeness`, its handler, response contract and
tests — because it is still consumed, and consumed somewhere it works: the **"What's in it?"** action on the
Folder cleanup failures panel, which the operator uses *after* normalization and archival, on a folder that
has actually failed. There the derived counts are stable (selection is final) and the live listing can address
the path (names are normalized). Doc comments on the analyzer, handler and endpoint now state that constraint
explicitly so the panel is not reinstated at review time by someone reading only the code.

**What this costs.** The "see it coming" goal is given up: an operator no longer learns about an unevaluated
subfolder until the Step 11 delete refuses. What survives is the part that made the original incident a dead
end — the failure is now explained (named blocking children, ancestor attribution), and resolvable in-product
(retry / inspect / settle as `Skipped`, then a scoped follow-up run). That was always the larger half.

**If a review-time warning is ever wanted again**, the honest placement is **after Step 8 normalization and
before archival** — the run already pauses there (the 8b execution gate), selection is final, and paths are
addressable. That is a different feature in a different place, not a relocation of this one, so it is left
unbuilt rather than half-moved.

**Also worth recording:** the derived, DB-only half of the analysis was never in question — it needs no SOAP
at all and correctly identified `3) Response` and the 60912 SRV 2016 chain from `FolderCount` arithmetic
alone. Only the live-verification half and the placement were wrong. If the pre-normalization live check is
ever needed, it would have to address folders by id rather than path, which MAGIQ's SOAP surface does not
offer (`decisions/log.md` [2026-08-13] — the same constraint that made the starting-folder scope a path-prefix
filter rather than a bound parameter).

**Status:** Implemented in the product working tree (uncommitted). Frontend: `components/FolderCompletenessPanel.tsx`
**deleted**; `wizard/Step6FolderReview.tsx` + `wizard/Step7ConfirmDeletions.tsx` (panel + import removed).
Backend doc comments only: `Pipeline/FolderAnalysis/FolderCompletenessAnalyzer.cs`,
`Features/Folders/GetFolderCompleteness/GetFolderCompletenessHandler.cs` + `GetFolderCompletenessEndpoint.cs`
(summary/description reworded from "Steps 6–7 review" to the post-normalization failure diagnostic, with the
"Target folder not found" constraint spelled out). No API, contract, DTO or test change — the endpoint and its
tests are unaffected. `npx tsc -b --force` clean. `spec/NATA_Document_Lifecycle_Cleaner_Spec_v0.6.md` (rev 20 —
Step 6 bullet removed, Rule 9 rewritten to a single enforcement point plus the withdrawal rationale, Step 11
note corrected, History), `spec/dev-spec.md` (endpoint row + component map), `CLAUDE.md` and `tasks.md`
updated to match.

---

## [2026-08-14] Step 11 empty-subtree prune — the downward closure, finally, driven from the blocked folders

**Context:** With the review-time warning withdrawn (entry above), a blocked folder was explained and
closeable but never actually *resolved*: the operator's only outcomes were retry (futile), settle as skipped
(gives up), or a whole new scoped run. Chase asked for a phase that handles it properly — deliberately look
into the subfolder tree of a refused folder and delete the empty children so the selected folder can finally
be deleted, without letting MAGIQ cascade-remove anything.

**The insight that makes it safe.** Deleting a folder whose **entire subtree holds zero documents** cannot
lose anything — there is nothing in it to lose. That is a different proposition from "delete a folder the run
never evaluated", which Rule 9 forbids. Rule 9 is about *evaluation*, so the correct move is to **extend the
evaluation** to those folders and then act on what it finds. The spec's Rule 9 now says so explicitly.

**The enabling move: prove emptiness from the database, not SOAP.** There is no verified `GetDocuments` op
(the same gap that forced the `409 UnresolvedMoveFailures` gate earlier today), so SOAP cannot answer "does
this folder hold documents". `PUBLICATION` can, live, and `FOLDERMAP` — a closure table — yields the entire
descendant set in a single non-recursive join. Checked the schema for a soft-delete trap first: neither
`PUBLICATION` nor `FOLDERS` carries a deleted/status flag, and `PUBLICATION` is unambiguously *the* document
table (`UQKEY (FOLDERID, NAME)`, FK to `FOLDERS`), so a live `COUNT(*)` **cannot miss a live document**. It
could only over-report if MAGIQ retained rows for deleted documents — and over-reporting means the prune
refuses. **The design fails closed in the only direction that matters.**

**Decision (all four shape questions put to Chase; he took the recommendation on each):**

1. **Prune empty subtrees only — never adopt documents.** Any document anywhere beneath a folder keeps that
   folder, and every ancestor of it up to the blocked folder, out of the plan. The date is deliberately
   irrelevant: post-cutoff means Rule 2 should have protected the branch, pre-cutoff means content this run
   never reviewed and never archived. The alternative (archive the eligible ones into the still-alive archive
   library, since purge is Step 12) was considered and rejected — it would archive documents the operator
   never reviewed and re-enter Step 10 from Step 11, for a case that is rare and that a scoped follow-up run
   already handles properly.

2. **Dry run → operator confirms → execute**, the same shape as the Step 8 normalization gate. These are
   folders the operator never saw at review, so a deliberate confirmation is the only thing consistent with
   the purge gate, the Step 8 gate and the post-archival pause.

3. **Reactive — only over folders that actually failed.** Costs nothing on a healthy run, and keeps the
   descendant query tiny (81 directly-blocked folders on the real run, not the whole candidate set).

4. **A second pass inside Step 11, not a new step or phase.** It is folder deletion, just of folders the run
   never evaluated, so it belongs in the step that already does that — and this avoids a second renumbering
   exercise across spec, dev-spec, code, ADRs and existing audit rows.

**Design notes worth keeping:**

- **`FolderSubtree`, the eighth configured query.** `PARENTID IN @folderIds` against `FOLDERMAP` — one join,
  all depths, and it seeks on the existing primary key (which leads on `PARENTID`), so unlike the ancestor
  direction it needs no extra index. Its doc comment carries an explicit contract for anyone customizing it:
  `DocumentCount` must stay **direct and date-unfiltered**, because under-reporting there would destroy
  documents. This is the "separate descendant query driven from the selected set" flagged as the right shape
  when the downward closure was deferred — the reason it is safe here is that it is driven from the *blocked*
  folders, not the candidate set, so it never approaches the whole-library explosion that made widening
  `CandidateFolders` unacceptable.
- **Only unevaluated folders are pruned.** A descendant with its own `CleanupRunFolder` row is excluded: if
  selected, Step 11's normal pass owns it and pruning it too would double-delete; if not selected, keeping it
  was a deliberate operator decision, reported as *retained* rather than silently overridden. This division is
  what keeps the prune consistent with the review rather than second-guessing it. `WillRemain` was promoted
  from private to public on `FolderCompletenessAnalyzer` so the prune and the failure explanation share one
  definition of "this folder will still be there" instead of two that can drift.
- **Global de-duplicated delete order.** Two blocked folders on one chain share descendants, so the same path
  can appear in several plans; `DeleteOrder` de-duplicates and sorts deepest-first *across* plans, because a
  descendant of one blocked folder can be an ancestor of another's. Without both, a success would turn into a
  spurious "Target folder not found".
- **No plan table.** The plan is one query plus pure computation, so it is derived for the dry run and
  **re-derived immediately before executing**. That is not laziness, it is the safety property: persisting the
  reviewed plan would let a document added while the review sat open be deleted along with its folder. Every
  individual delete then still passes the live `DeleteFolderIfEmptyAsync` guard on top.
- **Audited as `DeleteFolder` with `Detail = "Empty-subtree prune"`**, following the rollback teardown's
  precedent rather than adding a `RunOperationType` — these *are* Step 11 folder deletes; the detail is what
  tells an auditor the folder was never on the reviewed list. (A new enum value would also have had to be
  added to the now-exhaustive frontend mirrors, which is a point in favour of the detail-tag approach.)
- **Synchronous, driven per folder by the SPA**, like the delete-failure retry, so each row reports its own
  progress and no single request has to carry hundreds of SOAP deletes. No run-state transition, not gated on
  run status — the run is usually Completed by the time an operator works its failures.

**Status:** Implemented in the product working tree (uncommitted). Backend: new
`Integration/Magiq/Sql/FolderSubtreeRow.cs`; `ConfiguredQueryKeys.cs` + `ConfiguredQueryDefaults.cs`
(`FolderSubtree`, registered in `All`, class doc now says eight); `IMagiqDocumentQueries.cs` +
`MagiqDocumentQueries.cs` (`GetFolderSubtreeAsync`, batched + de-duplicated + path-normalised); new
`Pipeline/FolderAnalysis/SubtreePrunePlanner.cs` (`SubtreePrunePlan`, `Plan`, `PlanAll`, `DeleteOrder`); new
`Pipeline/IFolderPruner.cs` (`SubtreePruneOutcome`, `PruneFailure`); `Pipeline/RunPhaseExecutor.cs`
(implements `IFolderPruner`; `PlanSubtreePruneAsync`, `ExecuteSubtreePruneAsync`, `BuildPrunePlanAsync`);
`Pipeline/FolderAnalysis/FolderCompletenessAnalyzer.cs` (`Remains` → public `WillRemain`); new
`Features/Folders/PruneEmptySubtrees/*` (contracts, handlers, endpoints); `Program.cs` DI. Tests: new
`Pipeline/FolderAnalysis/SubtreePrunePlannerTests.cs` (11 cases — the live incident shape, documents deep in
a branch protecting every ancestor, an empty branch beside a document-bearing one, deepest-first order,
evaluated/retained exclusion, and the cross-plan de-duplication); the seven existing `IMagiqDocumentQueries`
test stubs gained `GetFolderSubtreeAsync`. Frontend: `api/folders.ts` (`getPrunePlan`, `pruneEmptySubtrees`
+ types), `components/CleanupOutcomesPanel.tsx` (per-row "Clear N empty subfolders", confirmation modal
listing exactly what will be deleted and warning when it will not resolve the folder). `npx tsc -b --force`
clean; the API side could not be `dotnet build`ed or test-run in this sandbox (no .NET SDK) — verified by
careful manual review. `spec/NATA_Document_Lifecycle_Cleaner_Spec_v0.6.md` (rev 21 — Rule 9 clarification,
new Step 11 prune section, History), `spec/dev-spec.md` (two endpoints, the index note), `CLAUDE.md` and
`tasks.md` updated to match.

**Post-implementation review corrections (same day).** An independent compile-and-logic review of the prune
found the code sound on the data-loss question — no path puts a document-bearing folder in `PrunablePaths` —
but surfaced one honesty defect and three sharp edges, all now fixed:

- **The docs overclaimed the guard, in four places.** `SubtreePrunePlanner`, `IFolderPruner`,
  `PruneEndpoints` and `dev-spec.md` each said or implied that the live pre-delete guard means "a document
  added since the review cannot be destroyed". It does not: `DeleteFolderIfEmptyAsync` calls `GetFolders` and
  inspects `FolderList.Folders` — **subfolders only**. It guards MAGIQ's cascade behaviour, not documents,
  because no verified document-listing SOAP op exists (the same gap that forced the post-archival gate). The
  document case is protected by exactly one thing — re-reading the descendant closure immediately before
  executing — and a narrow read→delete window remains that no available operation can close. All four now say
  so plainly. Worth recording as a process point: this session established that gap explicitly hours earlier
  and then wrote docs contradicting it, which is how a false safety claim gets into a spec.
- **An ancestor of a *retained* folder was prunable.** Its subtree holds no documents, so it passed the test —
  but it contains a folder the operator chose to keep, so the live guard was certain to refuse the delete. The
  plan would have spent a SOAP call and a `Failed` audit row per such folder learning what it already knew.
  Fixed by propagating a `containsRetained` flag bottom-up over the same post-order list, with a test.
- **`ConfiguredQueryKeys.All` omitted `FolderSubtree`** (and still said "seven"). Nothing consumes it today —
  seeding goes through `ConfiguredQueryDefaults.All` — but it was a live trap for the next caller. All three
  registries now agree at eight.
- **No `SchemaContracts` entry**, so the admin schema verifier silently skipped the one query whose column
  contract actually decides whether folders get deleted. Added, with every column required and a comment
  saying why: a customized query that drops or renames `DocumentCount` must fail verification loudly rather
  than default quietly to zero.
- Audit rows now use `run.CreatedBy`, matching every other Step 11 row (they were using `run.Owner`).

**Known, accepted:** when two blocked folders sit on one chain and are pruned in the same request, the
ancestor's own blockage is only cleared on a second invocation — the descendant is still `Failed` (and so
"retained") at plan time. The SPA reloads the plan after each prune, so the button simply reappears; not worth
a bounded retry loop.

---

## [2026-08-14] Corrected the prune to run automatically in Step 11 — the gate I recommended was the wrong call

**Context:** Chase came back on seeing the failures panel still listing entries like *"Folder still has 1
subfolder(s) remaining"* — "I thought the changes we just did was to add a step to look into the sub folders
to determine whether the folder and child folders can be deleted and do it, then for the ones that can't be
because there are documents in any of the levels show it as skipped and why. **This will help avoid a lot of
manual work.**"

**The mistake was mine.** When the four shape questions were put, I recommended "dry run → operator confirms →
execute" and Chase took the recommendation. That recommendation was wrong for the stated goal: a confirmation
dialog per blocked folder, across 81 directly-blocked folders on a real run, *is* the manual work the feature
existed to remove. Worth recording because the reasoning error is reusable — the gate was justified by analogy
to the Step 8 and purge gates without checking whether the same justification applied.

**It does not, and the argument I under-weighted is decisive:** the operator **already authorised deleting
these folders at Step 7**. The empty descendants are *inside* what was approved, and deleting the parent was
always going to remove them — that is precisely the cascade the pre-delete guard exists to prevent. Pruning
them first is not extending the approved scope, it is achieving it safely and in the right order. Automatic
execution also *narrows* the read→delete window rather than holding it open while a human reads a dialog, so
it is better on the one axis where the design has a real residual risk.

**Decision — the prune runs automatically as part of Step 11:**

1. `ExecuteCleanupAsync` calls `ResolveBlockedFoldersAsync` immediately after `DeleteEmptyFoldersAsync`.
2. It **cycles** (bounded, `MaxPruneCycles = 3`), because resolving one folder can unblock its ancestor, and
   exits as soon as a pass changes nothing.
3. Whatever is still blocked afterwards is blocked by content, so it is set to **`Skipped`** with a generated
   reason naming the blocking paths and document counts — not left as a `Failed` row implying someone still
   has work to do. This is exactly what Chase asked for: *"show it as skipped and why."*
4. The operator-facing endpoints stay, now framed as a **re-run** for a run that finished before this existed
   (Chase's current one) or where MAGIQ changed underneath it, and the panel gained a **bulk** action so such
   a run is one click rather than 81.

**Review findings, all fixed before this entry.** An independent pass on the automatic path found three real
defects, one serious:

- **A cancel was swallowed and the irreversible purge proceeded.** `ResolveBlockedFoldersAsync` returned
  `void`, so `ExecuteCleanupAsync` could not tell a cancel from a normal finish and fell through to Step 12 —
  either purging, or clobbering the `Cancelled` status off a stale in-memory run. Now returns `Task<bool>` and
  is `return`ed on, mirroring `DeleteEmptyFoldersAsync` exactly; cancellation is additionally checked
  **between batches** inside the cycle, not just at the top of each pass, and propagated on the outcome.
- **Auto-skip could terminally close a folder that was one pass from succeeding.** On cap exhaustion the plans
  were built *before* the last cycle's deletes, so a deep chain could be skipped citing a descendant that no
  longer existed — and `Skipped` is terminal with no un-skip. Two independent fixes: `RetryFolderDeletesInlineAsync`
  now sorts targets **deepest-first** (it was inheriting `GetByStatusAsync`'s `ORDER BY FolderPath`, i.e.
  parent-before-child, so a chain unwound only one level per invocation — a latent bug in the pre-existing
  manual retry too), and auto-skip now only runs when the loop exited via the *settled* break, never on cap
  exhaustion.
- **Auto-skip broke the `Skipped` contract.** It overwrote `FailureReason`, destroying the blocking error that
  `FolderStatus.Skipped` documents as preserved, and inverted the audit convention (reason in `detail`,
  error in `errorMessage`) that the operator path establishes. Both corrected; the reason is now appended to
  the original error rather than replacing it.
- Also: wrapped the whole pass in a `try/catch` so an unconfigured `FolderSubtree` query cannot fail a run
  *after* archival has moved everything (Step 11 is best-effort and this is an improvement on top of it);
  narrowed the retry to folders the prune could plausibly have helped, removing up to three rounds of
  redundant rule relax/restore churn and audit noise per folder; dropped the per-cycle `PhaseStarted` that
  reset the operator's progress bar mid-step; hardened a `ToDictionary` that could throw on a duplicate
  `FolderId`; and stopped `DescribeUnresolvable` calling a *failed* descendant "kept by choice" (`RetainedPaths`
  comes from `WillRemain`, which counts `Failed` as remaining).

**Known gap:** there is no automated test over the automatic path — the planner is well covered, but this
round's defects were all in the executor glue, which is the argument for adding one. The existing cleanup
suites do not exercise it (their `IMagiqDocumentQueries` stubs throw on `GetFolderSubtreeAsync` and are never
reached, because the fake folder store's `GetByStatusAsync` filters the seeded list rather than reflecting
status updates). Making that fake stateful would be the first step and would likely surface more.

**Status:** Implemented in the product working tree (uncommitted). Backend: `Pipeline/RunPhaseExecutor.cs`
(`MaxPruneCycles`; `ExecuteCleanupAsync` cancel-aware call; new `ResolveBlockedFoldersAsync`,
`AutoSkipUnresolvableFoldersAsync`, `DescribeUnresolvable`, `RunPruneCycleAsync`; `ExecuteSubtreePruneAsync`
delegates; `RetryFolderDeletesInlineAsync` deepest-first), `Pipeline/IFolderPruner.cs` (`Cancelled` on the
outcome; docs reframed), `Domain/FolderStatus.cs` + `Domain/RunOperationType.cs` (both now describe the
automatic and operator routes). Frontend: `components/CleanupOutcomesPanel.tsx` (bulk "clear and retry",
reworded panel copy and Skipped tooltip). `npx tsc -b --force` clean; C# verified by manual review and an
independent symbol-level pass (no .NET SDK here). `spec/NATA_Document_Lifecycle_Cleaner_Spec_v0.6.md` Step 11
section rewritten from operator-gated to automatic-with-operator-re-run.

**Test coverage for the automatic path (closing the gap flagged in the previous entry).** The executor glue is
where every defect in this feature landed, so it now has its own suite —
`Pipeline/RunPhaseExecutorSubtreePruneTests.cs`, six tests through the real `ExecuteCleanupAsync`: an empty
unevaluated subfolder is pruned and the blocked folder then deletes; a subtree holding documents is never
touched and the folder is auto-skipped with the blocking path named and the original error preserved; a cancel
mid-prune stops before the (pre-authorised) purge; a failing `FolderSubtree` query leaves the folder Failed
without failing the run; a nested chain clears without a second run; and a folder the operator chose to keep is
reported rather than pruned out from under them. The SOAP double keeps a **live folder tree that actually
mutates** — `ListFolders` reports what is still there and `DeleteFolder` removes it — which is what makes the
cycle behaviour meaningful rather than stubbed.

Two things worth recording from building them:

- **`RecordingFolders` in `RunPhaseExecutorRelaxOncePerFolderTests` was lying**, exactly as suspected. It
  filtered the *seeded* list and returned nothing from `GetByRunAsync`, so after a refused delete
  `GetByStatusAsync(Failed)` came back empty, the prune found no targets, and the stub that would have thrown
  was never reached. Now stateful. All four tests in that file still pass, and the empty `GetByRunAsync` was
  the more dangerous half — it would have let an *evaluated* folder look unevaluated and be pruned.
- **The first cut of the cancel test passed for the wrong reason.** It cancelled on the second run-store read,
  which `DeleteEmptyFoldersAsync`'s own checkpoint consumes — so the prune was never entered and the test would
  have stayed green with the fix reverted. Re-pinned to fire off the prune's own delete, which lands the cancel
  unambiguously inside the pass and cannot drift as checkpoints are added or removed. While re-tracing it, one
  more real gap showed up and was fixed: the retry after the prune ran even once a cancel had been observed, so
  there is now a checkpoint before it, and it propagates `Cancelled` on the outcome. A `FolderRuleSet` comment
  in the double was also inverted — an *absent* rule reads as **not** allowed, so an empty `<Rules/>` sends the
  guard relaxing and restoring around every failed delete; the double now returns explicit "allows".

---

## [2026-08-14] Step 11 prune: subtree-scoped rule escalation with ApplyToTree

**Context:** Chase: the last blocker is folder rules on a parent stopping the child being deleted. His spec —
attempt the delete first; if it fails, check whether folder rules are the cause; then relax `FolderDeletes` at
the highest level containing the empty children using `ApplyToTree`, delete them, and restore the original.

**Why the existing reactive handling isn't enough.** A folder delete is governed by its *parent's*
`FolderDeletes`, so `RunFolderGroupAsync` relaxes each parent in turn with `ApplyToTree=false`. That reaches a
rule on the immediate parent and nothing else — not one set further up, and not one inherited across a branch,
which is what a rule "on a parent folder" usually means in infoRouter. Setting from the top with `ApplyToTree`
does reach it, in one call rather than one per level.

**Decision — a new `WithSubtreeRuleRelaxedAsync` on the guard, used only by the prune, under two conditions.**

1. **New guard primitive.** Same get → relax → body → restore-in-`finally` shape as the per-folder form, but
   both the relax and the restore use `ApplyToTree=true` — restoring only the root would leave every
   descendant permissive, which is worse than never having relaxed. Two deliberate differences: it does
   **not** short-circuit when the root already allows (the root permitting the action says nothing about the
   folders beneath it — that short-circuit is exactly what makes the per-folder form unable to help here), so
   the *caller* owns the judgement that a rule is to blame; and its doc comment states plainly that a
   surviving descendant ends up carrying the root's rules rather than its own.

2. **Delete first, then diagnose** — as Chase specified, and as the rest of the pipeline already works. The
   normal pass runs unchanged; only what it could not delete is reconsidered.

3. **Condition one: the rejection must have come from MAGIQ.** `DeleteFolderIfEmptyAsync` raises its own
   refusals ("still has N subfolders", "could not verify"), and those are the tool's judgement, not evidence
   of a rule problem — escalating on them would mutate a customer's rule tree for no reason. Those errors now
   carry a `PreDeleteGuard` code and the escalation filters on it. This is a real path, not a theoretical one:
   the plan comes from the database and the tree is checked live, so they can legitimately disagree.

4. **Condition two: the whole subtree must be going away** (`plan.ResolvesFolder`). A tree-wide set stamps the
   root's rules over every descendant and the restore does the same, so a folder that *survives* would be left
   with the root's rules instead of its own — a silent, permanent change to NATA's configuration on folders we
   were never asked to touch. When nothing survives there is nothing to damage. Worth noting the planner makes
   this checkable: `ResolvesFolder` is true exactly when every descendant is either pruned or deleted by the
   normal pass, because anything else lands in `BlockingPaths` or `RetainedPaths`.

5. **Audited** as `RuleRelax`/`RuleRestore` rows naming the subtree scope, and the retried deletes as
   `DeleteFolder` + `Detail = "Empty-subtree prune (subtree rule relaxed)"`, so the trail distinguishes a
   delete that needed a tree-wide relax from one that did not. A failed restore is logged as an error and
   flagged for manual attention, same as the per-folder form.

**Rationale:** the two conditions are what make an inherently blunt instrument safe. `ApplyToTree` is
destructive to per-folder rule configuration by nature — it cannot be undone precisely, because the restore is
equally blunt. Confining it to (a) genuine MAGIQ rejections and (b) subtrees where every folder is being
deleted anyway means the blast radius is always empty by the time the dust settles.

**Open question for Chase, worth answering before this ships.** With the per-parent relax already in place,
this escalation should only be reachable when the blocking rule is *not* on the immediate parent. If what he
is actually seeing is the per-parent relax being attempted and not working, the root cause is different — e.g.
`SetFolderRules` not taking effect without `ApplyToTree` at all, or the rule living above the folder the run is
allowed to touch (in which case even a subtree relax rooted at the blocked folder will not help, because the
blocker is outside it). The MAGIQ operation audit trail will show which: look for a `RuleRelax` on the parent
followed by a still-failing `DeleteFolder`.

**Status:** Implemented in the product working tree (uncommitted). Backend:
`Pipeline/IFolderDeleteRuleGuard.cs` + `Pipeline/FolderDeleteRuleGuard.cs` (`WithSubtreeRuleRelaxedAsync`);
`Pipeline/RunPhaseExecutor.cs` (`PreDeleteGuardCode` stamped on the pre-delete guard's own refusals; prune
failures now carry the `MagiqSoapError` rather than just its message; new `EscalateRuleBlockedPrunesAsync`
called from `RunPruneCycleAsync`; `Report` helper). Tests: four new cases in
`Pipeline/FolderDeleteRuleGuardTests.cs` (ApplyToTree on both halves, applies even when the root allows,
restores on a throw, touches nothing when the rules are unreadable); a new
`A_pre_delete_guard_refusal_never_triggers_a_tree_wide_rule_change` in
`Pipeline/RunPhaseExecutorSubtreePruneTests.cs`, with the SOAP double now recording `ApplyToTree` sets; the two
`StubGuard`s in `RunPhaseExecutorNormalizationTests`/`RunPhaseExecutorIdentificationScopeTests` gained the new
member. Docs: spec rev 22 (Rule 6 subtree form + the Step 11 prune section + History), `CLAUDE.md`.

---

## [2026-08-14] The folder-delete rule is on the folder itself, not its parent — disproved from a live audit trail

**Context:** After the subtree escalation shipped, Chase reported the same *"Folder rules disallow deletion of
folders"* failures and supplied `example-run/audit-trail.csv` (run `8f2b3d13`, 9,620 rows) to analyse.

**What the trail actually shows — the feature works; one assumption does not.**

- 1,128 folders deleted, and **119 of them failed at least once and then succeeded** — the empty-subtree
  prune, its cycling, and the deepest-first retry are all doing their job on real data (121 prune deletes, 4
  auto-skips, all correctly reasoned).
- **Only 8 folders were left failed at the end:** four `.../22506 Miranda (SCI)/{case}/Final Records` rejected
  by MAGIQ with *"Folder rules disallow deletion of folders"*, and their four parent case folders, each
  auto-skipped with the correct explanation that a subfolder below it was not being removed.

**The root cause, and it invalidates a long-standing assumption.** The trail contains **zero `RuleRelax` rows
in the Cleanup phase** — all 24 relaxes are `Archival`/`DocumentDeletes`. `RunFolderGroupAsync` *does* invoke
the guard whenever any delete in a group fails, so for each of those four the guard ran, read the **parent's**
rules, found `FolderDeletes` already permitted, and correctly concluded the parent was not the blocker — so it
relaxed nothing. MAGIQ nonetheless refused the delete. The only consistent explanation: **`DISALLOWFOLDERDELETE`
on a folder blocks deleting *that folder*, not its children.**

That contradicts what this codebase has assumed since the delete-rule work landed, stated explicitly in the
`CandidateFolders` SQL: *"the PARENT's folder-delete rule (blocks deleting THIS folder). Parent controls child
deletion."* Every folder-delete relax has therefore been targeting the wrong folder, which is exactly why the
audit trail shows the guard silently declining to act rather than failing loudly — from its point of view the
rule it was asked about genuinely did permit the operation.

It also explains why the subtree escalation did not help: those four are **evaluated candidates**, not prune
targets, so they never appear in a plan's `PrunablePaths`; and their parents' plans have them in
`RetainedPaths` (a `Failed` folder counts as remaining), making `ResolvesFolder` false and disabling the
escalation by design. Chase's `ApplyToTree` instinct would have worked — but for an incidental reason: setting
from an ancestor happens to cover the folder itself. The surgical fix is better.

**Decision — relax the rule on the folder being deleted.** New
`RunPhaseExecutor.DeleteFolderWithSelfRuleRelaxAsync` wraps the delete: attempt it, and only if **MAGIQ**
rejected it (never when this pipeline's own pre-delete check refused — still keyed off `PreDeleteGuardCode`)
relax that folder's own `FolderDeletes`, re-verify emptiness, retry, and restore. Used by all three
folder-delete sites: the main Step 11 pass, the operator retry, and the prune. The existing per-parent relax in
`RunFolderGroupAsync` is **kept** as the outer tier — it costs one rule read on an already-failed group and
still covers the other semantic wherever it does apply. Deliberately not removed on the strength of one run's
inference.

**Still to confirm, and it is a one-query answer.** Whether `FOLDERS.DISALLOWFOLDERDELETE` on the folder is
the true governing flag can be settled directly:
`SELECT NAME, DISALLOWFOLDERDELETE FROM dbo.FOLDERS WHERE NAME = 'Final Records'` alongside the same for their
parents. If confirmed, two follow-ups fall out: the `CandidateFolders` `FolderDeleteBlocked` column (currently
joined to the **parent**, `pf.DISALLOWFOLDERDELETE`) is flagging the wrong folders in the Step 6 review, so the
"Delete-locked" badge has been pointing at parents rather than the locked folders themselves; and the
per-parent tier can then be dropped. Both left alone until the semantic is confirmed — the column is
informational and mis-flagging is not harmful, whereas changing operator-editable SQL on an inference would be.

**Status:** Implemented in the product working tree (uncommitted). Backend:
`Pipeline/RunPhaseExecutor.cs` (new `DeleteFolderWithSelfRuleRelaxAsync`; the three `RuleGuardedOp` delete
sites now use it). Tests: new `A_rule_on_the_folder_itself_is_relaxed_so_the_delete_succeeds` in
`Pipeline/RunPhaseExecutorSubtreePruneTests.cs`, reproducing the exact live shape (rule on the folder, parent
permitting) and asserting the relax is recorded against the folder itself and the original restored; the SOAP
double now models per-folder `FolderDeletes` and enforces it on `DeleteFolder`, with `SetFolderRules` honouring
`ApplyToTree`. No spec change yet — Rule 6's wording stays until the semantic is confirmed.

**Confirmed by direct query (same day).** Chase ran the schema check across every `Final Records` folder:
`DISALLOWFOLDERDELETE = 1` on the folders themselves, `0` on **every one** of their parents — including all
four that failed (`53107 ADV 2014`, `54295 ASS 2014`, `58824 SRV 2015`, `60917 RES 2016`). The result set also
contains a second copy of each path with the flag `0`, which is the **archive library's** recreated structure
(1,060 `CreateFolder` rows in the same run, and a newly created folder carries no rule) — corroboration rather
than contradiction.

So the semantic is settled: **`FOLDERS.DISALLOWFOLDERDELETE` on a folder blocks deleting that folder.** The
"parent controls child deletion" assumption is retired. Two consequences actioned:

1. **`CandidateFolders`' `FolderDeleteBlocked` was reading the wrong folder** — `pf.DISALLOWFOLDERDELETE` via a
   `LEFT JOIN` to the parent — so the Step 6 **"Delete-locked" badge has been flagging parents rather than the
   folders that are actually locked, for as long as the flag has existed.** Now `f.DISALLOWFOLDERDELETE`; the
   parent join is gone. Doc comments corrected on `CandidateFolderRow`, `CandidateFolder`, `CleanupRunFolder`,
   `FolderItem`, the baseline DDL comment, and the Step 6 tooltip copy.
   **Operational note:** `ConfiguredQuery` is seeded only for absent keys, so an **already-seeded database
   keeps the old SQL** — the corrected query must be re-seeded or edited via `/admin/queries`, exactly as with
   the 2026-07-30 collation fix. Until then the badge stays wrong, though nothing else depends on it.
2. **The per-parent relax tier is now known to be aimed at the wrong folder for Step 11.** Kept anyway, as a
   cheap outer fallback (one rule read per already-failed group) rather than deleted on the strength of one
   environment, but its comment now says plainly that `DeleteFolderWithSelfRuleRelaxAsync` is what does the
   real work. Worth revisiting once a second environment confirms.

Not changed: spec Rule 6's wording still describes the reactive relax generically, which remains accurate —
only the *target* folder was wrong, not the mechanism.

---

## [2026-08-14] A folder delete needs BOTH delete permissions — relaxing FolderDeletes alone just moves the rejection

**Context:** The run after the own-folder fix (`a5305435`, audit trail supplied) shows the fix working and the
error moving one step along. The Cleanup phase now contains **4 `RuleRelax` + 4 `RuleRestore` rows** that did
not exist before — `DeleteFolderWithSelfRuleRelaxAsync` correctly identified the folder's own
`FolderDeletes` as blocking and relaxed it. The same four folders then failed with a *different* message:
**"Folder rules disallow deletion of documents."**

**Why that is surprising, and what it means.** Those four folders are empty of documents by then: the trail
shows 4, 11, 5 and 4 documents respectively archived out of them at Step 10, with **zero move failures** across
the whole run (7,188 moves, all Ok). MAGIQ nonetheless refuses the folder delete on document-delete grounds.
So **a `DeleteFolder` is validated against the folder's `DocumentDeletes` as well as its `FolderDeletes`,
regardless of whether the folder currently holds any documents** — presumably because a folder delete is a
recursive operation and the permission check is static rather than content-dependent.

Corroborating detail from the same data: the 24 `Archival`/`DocumentDeletes` relaxes in the earlier run were on
these very `Final Records` folders — that is how their documents were archived out in the first place. So
`DISALLOWDOCUMENTDELETE = 1` and `DISALLOWFOLDERDELETE = 1` are both set on them, and the folder delete needs
both lifted.

**Decision — relax both permissions together, in one call.**

1. **`FolderRuleSet.WithAllowed(IReadOnlyCollection<string>)`** — a multi-rule overload; the single-rule form
   now delegates to it. One payload keeps the captured original a single verbatim string to restore.
2. **`IFolderDeleteRuleGuard.WithRulesRelaxedAsync`** — relaxes every *blocking* rule from a requested set in
   one `SetFolderRules`, runs the body, restores. Deliberately not built by nesting the one-rule form: that
   form declines when its rule already permits the action, so a nested call would silently skip the second
   rule whenever the first happened to be open — which is exactly the shape that would have produced this same
   bug again.
3. **`RunPhaseExecutor.FolderDeleteRules`** (`FolderDeletes` + `DocumentDeletes`) is now what every folder
   delete relaxes, both in `DeleteFolderWithSelfRuleRelaxAsync` and in the subtree escalation
   (`WithSubtreeRuleRelaxedAsync` also takes the set now, so the tree-wide form cannot drift from the
   per-folder one).

**Rationale:** treating "the permissions this operation needs" as a set rather than a single rule is the
generalisation the last two rounds have been converging on. Each round has been the same shape — a permission
check aimed at one folder or one rule, correct in the abstract and wrong against the real service. Naming the
full permission set for the operation removes the class of bug rather than the instance.

**Status:** Implemented in the product working tree (uncommitted).
`Integration/Magiq/Soap/FolderRuleSet.cs` (multi-rule `WithAllowed`);
`Pipeline/IFolderDeleteRuleGuard.cs` + `Pipeline/FolderDeleteRuleGuard.cs` (new `WithRulesRelaxedAsync`;
`WithSubtreeRuleRelaxedAsync` now takes a rule set); `Pipeline/RunPhaseExecutor.cs` (`FolderDeleteRules`,
used by the self-relax and the subtree escalation). Tests: three new cases in `FolderDeleteRuleGuardTests`
(both blocking rules relaxed in a single set; only the actually-blocking rule changed; no-op when neither is
blocking), the four subtree tests updated to the collection signature, and both `StubGuard`s gained the new
member. Frontend untouched.

**Prediction to check on the next run:** the four `Final Records` folders should delete, and their four parent
case folders should then delete too — taking the run's outstanding failures from 8 to 0. If a *third* message
appears instead, the same diagnostic applies: it is another permission in the set, and the fix is to add it to
`FolderDeleteRules` rather than to add another tier.

---

## [2026-08-14] The manual purge was unreachable — the Step 8 renumbering missed `AwaitInput`

**Context:** Chase reported a run apparently stuck at *"Status: AwaitingInput · Cleanup (step 11)"*. It is not
stuck in the sense of hanging — Step 11 finished and the run parked at the "Ready for purge" gate. But it
could never have got past it.

**A three-way disagreement about which step the purge pause is, all in the same code path:**

| Place | Says |
|---|---|
| `RunPhaseExecutor` Path B | `run.AwaitInput(11)` |
| `PurgeControl` (SPA) | shows the Purge button at `step === 11` |
| `PurgeArchiveHandler` | requires `CurrentStep == 12`, else `409 RunNotReadyForPurge` |

So the operator is shown the Purge button, types *"permanently delete"*, and the API rejects it — with no
route through. **Path B is the default** (`AutoProceedWithPurge` is false unless pre-authorised at Step 7), so
this affects every ordinary run. Path A was unaffected, which is why it went unnoticed: it calls
`DeleteAndPurgeArchiveAsync` directly, and that does `AdvanceToStep(12)` correctly.

The giveaway was in the same six lines: the phase-log append already used step **12** and the log message
already read *"ready for manual purge (Step 12)"* — only the state write said 11. A leftover from the Step 8
renumbering (Cleanup became Steps 11–12, purge = 12): the handler was updated, the `AwaitInput` was not, and
`PurgeControl` was written to match the executor rather than the spec, which made the pair look
self-consistent and hid the mismatch with the handler.

**Decision:**

1. **`run.AwaitInput(12)`** — the purge pause is Step 12, matching the handler, the phase log, the log message
   and the spec.
2. **`PurgeArchiveHandler` accepts 11 or 12**, and **`PurgeControl` renders at 11 or 12.** Not tidiness —
   necessity: a run already parked by the old code is persisted with `CurrentStep = 11`, and tightening both
   ends to 12 would strand it permanently unpurgeable with no UI affordance. Chase has such a run right now.
   The tolerance can be dropped once no such runs remain.

**Worth noting about the shape of this bug.** Both halves were individually defensible — the executor and the
SPA agreed, the handler and the spec agreed — and each pair looked correct in isolation. What made it
invisible is that no test crossed the boundary: `PurgeArchiveHandlerTests` sets the run state by hand, so it
never observed what the executor actually writes. The new
`Accepts_a_run_parked_at_the_pre_fix_step_11` covers the compatibility path, and
`RunPhaseExecutorRuleGuardTests` now asserts the executor parks at 12 — which is the assertion that would have
caught it originally, since it is the only one that runs the real cleanup phase to its pause.

**Status:** Implemented in the product working tree (uncommitted). Backend:
`Pipeline/RunPhaseExecutor.cs` (`AwaitInput(12)`), `Features/Runs/PurgeArchive/PurgeArchiveHandler.cs`
(accepts 11 or 12). Frontend: `wizard/PurgeControl.tsx` (renders at 11 or 12; doc comment corrected from
"Step 11 manual purge" to Step 12). Tests: new `Accepts_a_run_parked_at_the_pre_fix_step_11`; the not-ready
case documented as needing a step that is neither; `RunPhaseExecutorRuleGuardTests`'
`Step10_folder_delete_blocked_by_parent_rule…` renamed to `Step11_folder_delete_blocked_by_a_rule…`, now
asserting the rules are read on the **folder itself** rather than its parent (the 2026-08-14 own-rule finding)
and that the run parks at 12. `npx tsc -b --force` clean.

---

## [2026-08-14] Folder cleanup failures are hidden until the run settles — `Failed` is a working state mid-phase

**Context:** Chase, watching a run: the Folder cleanup failures panel fills with "can't delete, has child
folders" entries which then resolve in a later step and disappear. His question — if they resolve themselves,
do they need showing at all until they are a *true* blocking failure?

**No, and the observation identifies the real problem.** `FolderStatus.Failed` is doing double duty. Step 11
marks a folder failed the instant its first delete attempt is refused, and its own second pass then prunes the
empty subfolders beneath it and retries — so for the duration of the phase, `Failed` means "not deleted *yet*",
not "needs a human". The last live run makes the scale plain: **119 folders failed and then succeeded**, and
only 8 were still failed at the end. Under the old behaviour the operator watched 119 alarming rows appear and
drain away.

That is worse than merely noisy. The panel's stated purpose — in its own doc comment and in the spec — is
"only what still needs attention". A list that shrinks on its own teaches the operator that the panel is not
to be trusted, and invites action on rows that will be gone before they finish reading them.

**Decision: hide the panel entirely while the run is `Running`; show it once the run settles.** The panel now
takes the run status rather than a `live` boolean, and derives two things from it: *settled*
(`status !== 'Running'`) gates both visibility and the initial fetch — no reason to poll for something not
being displayed — and *live* (`status === 'AwaitingInput'`) keeps it refreshing at the Ready-for-purge pause,
where the operator can still retry, prune and settle from the panel itself. `JobDetailsView` already polls the
run every 5s, so the panel appears the moment cleanup finishes without needing its own run poll.

A pleasant consequence rather than a designed one: the panel now naturally lands as a **pre-purge review** —
the last thing the operator sees before authorising the irreversible Step 12, listing exactly what could not
be cleaned and why.

**Considered and rejected: stop marking folders `Failed` until the phase gives up.** Conceptually cleaner —
it would fix the overload at source rather than papering over it in the UI — but `Failed` is load-bearing in
two places. `GetDeletableAsync` includes it, which is what makes a resumed Step 11 retry those folders; and
the audit trail deliberately records *every* attempt, including the ones that later succeed, because that
history is what diagnosed the last three bugs in this area. A transient in-memory notion of "failed but still
being worked" would have to be threaded through both. The display rule achieves the same operator-visible
outcome for a fraction of the risk. Worth revisiting only if some other consumer of `Failed` starts caring
about the distinction.

**Not changed: `MoveFailuresPanel`.** A failed document move has no self-healing pass behind it, so it is
always worth showing immediately. Its doc comment now says why the two panels differ, since they used to
share the `live` prop and an unexplained divergence invites someone to "fix" it.

**Status:** Implemented in the product working tree (uncommitted). Frontend only:
`components/CleanupOutcomesPanel.tsx` (`runStatus` prop; `settled`/`live` derivation; effects keyed on
`settled`; visibility gate after the hooks), `pages/JobDetailsView.tsx` (call site),
`components/MoveFailuresPanel.tsx` (doc comment). `npx tsc -b --force` clean. Spec Step 11 "Working through
folder-delete failures" updated to describe the visibility rule.

---

## [2026-08-14] "Confirm permanent deletion does nothing" — the wiring is complete; two things were hiding the result

**Context:** Chase typed the confirmation phrase and saw nothing happen, asking whether the purge is wired up
at all.

**It is, end to end** — traced and verified: `PurgeControl` → `purgeArchive()` →
`POST /runs/{runId}/purge` (route and body binding match) → `PurgeArchiveEndpoint` (operator from the session,
never the body) → `PurgeArchiveHandler` (state gate, phrase check, `PurgeAuthorised` audit row) →
`CleanupRun.AuthorisePurge` (records who/when and flips `AwaitingInput` → **Running**, which is what lets the
job past `LoadRunnableAsync`) → `IRunPipeline.StartPurge` → Hangfire → `ExecutePurgeAsync` →
`DeleteAndPurgeArchiveAsync` (`AdvanceToStep(12)`, then `IArchiveLibraryTeardown.PurgeAsync`) →
`CompleteRunAsync`. No missing link.

**Two real defects found in the same component, either of which produces "nothing happened":**

1. **The panel stopped polling the moment the purge was authorised.** `useEffect(… if (purging) return; …)`
   meant that once `setPurging(true)` fired, `PurgeControl` never fetched the run again — so it sat on
   "Purge started…" indefinitely even on a completely successful purge. Fixed: it polls throughout, and
   `purging` now drives a dedicated **"Purge in progress"** alert instead of a line inside the ready-state
   alert. That distinction matters because authorising sends the run back to `Running`, which makes
   `readyForPurge` false — so without its own branch the whole panel silently unmounted mid-purge, taking the
   only acknowledgement with it.

2. **The step-11/12 mismatch from the entry above is very likely the actual cause for Chase's run.** It is
   parked with `CurrentStep = 11`, and the *unfixed* `PurgeArchiveHandler` requires 12 — so the POST returns
   `409 RunNotReadyForPurge` and nothing is enqueued. That fix (executor writes 12; handler and SPA accept 11
   or 12) is in the working tree but **not yet built**, so a run against the current binary still rejects.

**Diagnostic if it recurs after a rebuild,** in order of what it discriminates: the browser network tab on the
POST (a 409 body carries `status` and `step`, which names the problem outright); then the operation audit
trail for a `PurgeAuthorised` row (present ⇒ the handler accepted and Hangfire is the suspect; absent ⇒ the
request never got through); then the Hangfire dashboard for an `ExecutePurgeAsync` job.

**Status:** Implemented in the product working tree (uncommitted). Frontend only:
`wizard/PurgeControl.tsx` (polls throughout; dedicated in-progress alert; the ready-state alert now only ever
renders the button). `npx tsc -b --force` clean. No backend change — the backend path was already correct.

---

## [2026-08-14] Latest run (`16131403`): cleanup is clean; two things left — a false "left permissive" alarm, and a purge that was authorised but never ran

**Correction to the previous entry's advice.** That analysis was run against a stale export. The current trail
supersedes it, and the recommendation it produced — retry the stragglers, then hand-delete four
terminally-skipped parents — is **moot**: nothing was skipped and nothing is outstanding.

**What the latest run actually shows: the cleanup work is finished and correct.**

- **1,136 folder deletes, every one `Ok`. Zero folders left failed.** (Previous run: 1,128 Ok, 8 failed.)
- The four `Final Records` folders **and** their four parent case folders all deleted — the both-permissions
  relax did exactly what it was meant to.
- **No `FolderSkipped` rows at all.** Nothing needed settling, so the auto-skip never fired.
- The 119 `DeleteFolder | Failed` rows are all transient "still has N subfolder(s)" — every one of those
  folders later succeeded. This is the prune working, and it is exactly the churn the panel now hides.

**Finding 1 — four `RuleRestore | Failed` rows are a false alarm, and they are my doing.**
`DeleteFolderWithSelfRuleRelaxAsync` relaxes the rule on **the folder being deleted**, deletes it inside the
relaxed scope, and then the `finally` tries to `SetFolderRules` on a folder that no longer exists. The restore
fails, and the audit says *"the folder is left permissive and needs manual attention"* — about a folder that
is gone. Nothing is permissive; there is nothing to attend to. The pre-existing per-parent design never hit
this because the parent survives its child's deletion; relaxing the target's own rule is what introduced it.
Confirmed against the data: the four failed restores are precisely the four `Final Records` paths, and all
four appear as successful deletes.

Fixed with an optional `restoreRequired` predicate on `WithRulesRelaxedAsync`, evaluated in the `finally`:
when the delete succeeded the restore is skipped entirely, `onRestored` is still invoked with `true`, and
`RecordRuleRestoreAsync` marks the row `restored: "not-required-folder-deleted"` so an auditor can tell "put
back" from "there was nothing to put back". Two new guard tests cover skip-and-report-success and the
still-restores-when-the-folder-survives case.

**Finding 2 — the purge was authorised and then nothing happened.** `PurgeAuthorised | Ok` at
`01:17:15` (so the endpoint, the state gate and `AuthorisePurge` all worked — the step 11/12 fix is in), but
the export at `01:21:07` contains **no `DeleteDomain` and no `Purge` rows**, and the last operation of any
kind is a folder delete at `01:08`. `ArchiveLibraryTeardown` writes both row types unconditionally as it goes,
so their absence means `ExecutePurgeAsync` did not reach the teardown — roughly four minutes after
authorisation.

Its early exits are: run not found; run not `Running` (`AuthorisePurge` sets `Running`, so no); not in the
`Cleanup` phase (it is); or an empty process ticket, which calls `FailCleanupAsync` and would show as a
`Failed` run. An expired-but-non-empty ticket would fail *inside* the teardown and leave a `DeleteDomain |
Failed` row — there is none. So the most likely explanation is that the **Hangfire job never executed**, which
is outside what the audit trail can show.

Diagnostics, in the order that discriminates fastest: the run's current status (still `Running` ⇒ the job
never completed); the Hangfire dashboard for an `ExecutePurgeAsync` job and its state; and the application log
for `ExecutePurgeAsync`'s own early-exit lines ("run … is {Status} (not Running); nothing to do" / "not in the
cleanup phase; skipping") or "The run has no process ticket".

**Status:** Implemented in the product working tree (uncommitted). Backend:
`Pipeline/IFolderDeleteRuleGuard.cs` + `Pipeline/FolderDeleteRuleGuard.cs` (`restoreRequired` on
`WithRulesRelaxedAsync`), `Pipeline/RunPhaseExecutor.cs` (passes it from the delete; `RecordRuleRestoreAsync`
gained a `deleted` flag for the audit detail). Tests: two new guard cases; both `StubGuard`s updated for the
new parameter. No fix attempted for the purge until the diagnostics identify where it stops.

**Resolved: the purge did run.** The Hangfire job (`#13`, `ExecutePurgeAsync`) reports **Succeeded, 7 minutes**.
`PurgeAuthorised` is at `01:17:15` and the export was taken at `01:21:07` — **3.1 minutes before the job
finished**. The `DeleteDomain` and `Purge` rows were written during the remaining three minutes, so the trail
was simply captured mid-flight. There is no defect here, and the earlier "the job never executed" inference
was wrong: it was drawn from an export that could not yet contain the evidence.

Seven minutes is entirely plausible for the work involved — `DeleteDomain` on a library holding 7,188
documents across 1,060 folders, then `GetRecycleBinContent`, then one `PurgeRecycleBinItem` SOAP round trip
per item.

**What was actually wrong was the silence, and that has two causes, both now addressed.** The panel froze on
"Purge started…" because it stopped polling the moment the purge was authorised (fixed in the entry above:
it polls throughout and shows a dedicated in-progress alert). And `DeleteAndPurgeArchiveAsync` emitted its one
`PhaseStartedMessage` with **step 11** — the third instance of the Step 8 renumbering drift, after
`AwaitInput(11)` and the purge handler's gate — so the only progress signal during a multi-minute step was
mislabelled. Corrected to 12.

**Remaining, not built:** the purge reports no per-item progress at all. `IArchiveLibraryTeardown` has no
progress notifier, and `PhaseStartedMessage(..., totalItems: 1)` means the bar sits at 0/1 for the whole run.
The clean shape is an optional `Func<int,int,Task>? onProgress` on `PurgeAsync` supplied by the executor —
rather than injecting `IRunProgressNotifier` into the teardown, which is shared with the rollback and
run-delete paths where a "Cleanup step 12" label would be a lie. Left for Chase to call.

---

## [2026-08-14] Purge visibility, and the source folders it was leaving in the recycle bin

**Context:** Chase asked for progress statistics and purge operation logs in the audit trail, and flagged a
case: *"empty folders were deleted and these will be missed during the purge."* He is right, and it is the
larger of the two.

**First, a correction: per-item purge logs already existed.** `ArchiveLibraryTeardown` writes a `Purge` row
per recycle-bin item — name, handle, `DeletePath`, outcome — and a `DeleteDomain` row for the library. They
were absent from the export only because it was taken three minutes before the job finished. What was actually
missing was *progress* and a *summary*.

**The real gap — source folders are soft-deleted and never purged.** `DeleteFolder` sends a folder to the
recycle bin; Step 12 then matches bin items by `DeletePath` against `\{ArchiveLibraryName}` and below. Every
folder Step 11 removed from the **source** library therefore stays in the bin indefinitely — **1,136 of them
on the last run**, every year, recoverable and cluttering the bin. The cull's own purpose says they should go.

**Decision — purge them in the same authorised operation, matched fail-closed.**

`PurgeAsync` gains `deletedSourceFolders`, supplied by `DeleteAndPurgeArchiveAsync` from the run's own
`CleanupRunFolder` rows with status `Deleted`. Matching is deliberately **paired**: an item qualifies only if
its `DeletePath` *and* its `Name` reconstruct to a path this run recorded deleting. Never by library — the
source library's bin holds everything anyone has ever deleted from it, and a name-only or path-only match
would destroy other people's items. "Final Records" exists under hundreds of parents in this data set, which
makes the point concrete. An item missing either half is skipped rather than guessed at.

Where the shape does not match, it **purges nothing and says so**, logging a sample of the bin's actual
`name`/`deletePath` pairs. The recycle-bin shape is only verified for the deleted-domain case
(`SOAP-VERIFICATION-34525.md`); a deleted source folder may well describe itself differently. Given this
session's repeated experience of assuming a MAGIQ semantic, the fallback is "leave it alone and show me what
you saw", never "match loosely and hope" — and the next run's log tells us the true shape without having
destroyed anything to find out.

**Rollback and run-delete deliberately do not pass source folders.** A rollback is putting things back; the
source deletions are precisely what it must not make permanent.

**Also added:**
- **Progress** — an `onProgress(done, total, item)` callback per purged item, wired to the executor's existing
  `EmitProgressAsync`. Previously the phase emitted `PhaseStarted(totalItems: 1)` once, so the bar sat at 0/1
  for the seven minutes a real purge takes, which is what made a working purge look like a hung one.
  Preferred over injecting `IRunProgressNotifier` into the teardown: it is shared with the rollback and
  run-delete paths, where a "Cleanup step 12" progress label would be a lie.
- **A summary audit row** — one `Purge` row with `TargetType = Selection` carrying
  `{purged, failed, archiveItems, sourceFolders, sourceFoldersExpected}`. The per-item rows stay the record of
  what was destroyed; this answers "how much, and did any of it fail" without counting thousands of rows, and
  keeps the archive's items and the source folders countable separately. `sourceFoldersExpected` vs
  `sourceFolders` is the diagnostic for the shape question above.
- **Confirmation wording** — the typed-confirmation modal and the ready-for-purge alert now say the source
  folders are purged too. The old wording promised only "the archive library and everything moved into it",
  which no longer describes what the operator is authorising.

**Status:** Implemented in the product working tree (uncommitted). Backend:
`Pipeline/ArchiveLibraryTeardown.cs` (signature, paired source matcher, progress, summary row, fail-closed
diagnostic), `Pipeline/RunPhaseExecutor.cs` (`DeleteAndPurgeArchiveAsync` supplies the deleted folders and the
progress callback; rollback call site left archive-only), `Features/Runs/DeleteRun/DeleteRunHandler.cs` (named
`ct:`). Tests: new `Pipeline/ArchiveLibraryTeardownTests.cs` — six cases, weighted towards what must *not* be
purged (same folder name under a different parent, unrelated items, unusable bin shape) plus progress and the
summary; `Fakes/FakeArchiveLibraryTeardown.cs` records the source-folder argument. `npx tsc -b --force` clean.

---

## 2026-08-17 — Deleted-folder manifest, and one definition of "which source folders did this run delete"

**Context.** Step 12 now purges the source folders Step 11 deleted out of the recycle bin (log
[2026-08-14]), which closes the "empty folders left behind" gap but removes the last copy of the deleted
structure. Chase: *"Could we keep track of the empty folders that were deleted and purged and if absolutely
necessary they could be used to re-create the empty folders again."*

**Decision — export a manifest; re-create by hand if ever needed.** No in-product re-create action, and no
capture of the full folder rule XML. Two reasons. The recovery case is genuinely last-resort ("if absolutely
necessary"), so the cost of a re-create feature is paid on every run for a scenario that should never occur;
and a re-create button implies a fidelity the tool cannot deliver — description, owner and security are never
read by the pipeline, so what came back would be an empty shell wearing the right name. A CSV a human walks
top-down is honest about that. **Scope: path + the two delete rules already snapshotted**, plus the
identification counts and the pre-deletion folder id for cross-referencing the trail.

**Nothing new is persisted.** The records already exist and are durable: a run that reached cleanup is
`RunChangeTier.Irreversible`, so `CanDelete` is false and `HardDeleteAsync` (which drops the
`CleanupRunFolder` rows) is unreachable for exactly the runs this matters for. The export's job is to get
them out of the application database.

**The correction that made it correct — read the audit trail, not the folder rows.** The obvious
implementation is `GetByStatusAsync(runId, FolderStatus.Deleted)`. That is wrong, and wrong in the exact
place the request was about: the empty-subtree prune deletes folders the run **never evaluated**, which have
no `CleanupRunFolder` row at all — only a `DeleteFolder` audit row tagged `"Empty-subtree prune"`. A manifest
built from folder rows would omit precisely the empty folders Chase asked to keep track of.

Worse, **Step 12's purge had the same bug**, introduced three days earlier: it fed
`GetByStatusAsync(Deleted)` to `PurgeAsync`, so the pruned folders were not purged either. The fix for the
manifest is the fix for the purge, so both now go through one shared definition —
`Pipeline/DeletedSourceFolders.From(entries)`: `Cleanup`-phase `DeleteFolder`/`Ok`/`Folder` rows,
de-duplicated, in deletion order, each carrying `WasPruned`.

**Why the phase check is load-bearing.** The rollback teardown also emits `DeleteFolder`/`Ok` rows — for
**archive** folders, with `phase: null`. Without the `Cleanup` filter, a rolled-back run would hand the purge
a list of archive paths it has no business matching against the source bin. Pinned by a test.

**Manifest shape.** Ordered **shallowest-first** — the order the folders must be re-created in, which is the
reverse of the deepest-first order they were deleted in; the file is ordered for the job it exists to
support, not for the job that produced it. `Origin` distinguishes `Reviewed` from `Pruned`, and a pruned
folder's count/rule columns are left **blank rather than zeroed** — a written `0` reads as a measurement
someone might act on, when the truth is that the run never looked. The `#`-prefixed header states plainly
that description, owner and security are not captured; a recovery record that overstates itself is worse
than none.

**Placement.** Its own always-visible card (`DeletedFolderManifestPanel`), not folded into
`CleanupOutcomesPanel` — that panel self-hides when a run had no failures, and a clean run is exactly the one
whose entire deleted structure is about to exist nowhere else. Shown from the moment the run reaches Cleanup,
and the typed purge confirmation prompts for it, because that is the last point the structure still exists in
MAGIQ. The rows outlive the run either way.

**Status:** Implemented in the product working tree (uncommitted). Backend: new
`Pipeline/DeletedSourceFolders.cs`; new `Features/Runs/ExportDeletedFolders/` (Request/Query/Export/Handler/
Endpoint) serving `GET /api/v1/runs/{runId}/folders/deleted/export`; `Pipeline/RunPhaseExecutor.cs`
(`DeleteAndPurgeArchiveAsync` now derives its purge list the same way). SPA: new
`components/DeletedFolderManifestPanel.tsx`, mounted in `pages/JobDetailsView.tsx`; `api/runs.ts` gained
`exportDeletedFolders` and a shared `downloadFile` helper (the audit export now uses it too);
`wizard/PurgeControl.tsx` prompts for the manifest in the confirmation modal. Tests: new
`Pipeline/DeletedSourceFoldersTests.cs` (both directions — the prune's folders in, the rollback's archive
deletes out) and `Features/Runs/ExportDeletedFoldersHandlerTests.cs`. `npx tsc -b --force` clean; `dotnet
build`/`dotnet test` pending on Chase's machine.

**Flagged, not changed:** `dev-spec.md` §"Step 12 — Path B" said the purge confirmation is validated
*case-sensitive*, but `PurgeControl` compares `typed.trim().toLowerCase()`. Left the API's actual behaviour
unasserted in the spec pending confirmation of which is intended.

---

## 2026-08-17 — A purge that outlives its timeout is unknown, not failed

**What happened on the live run.** Under the rev 23 purge, Chase watched the recycle bin: **one very large
entry** for the archive library, then individual entries for the empty folders Step 11 removed. The folder
half ran fine with good progress. The archive entry threw — a dropped connection surfacing as
`HttpConnection.InitialFillAsync` failing inside `MagiqSoapClient.SendWithRetryAsync`. He then checked
afterwards: **the entry is gone.** MAGIQ completed the destroy. We reported a failure for work that
succeeded.

**Three defects, in increasing order of seriousness.**

**1. The timeout was never plausible.** `MagiqTimeoutSeconds` defaults to 100s (ceiling 600) and applied to
every operation alike, because it was set on `HttpClient.Timeout`. Destroying an archive library's
recycle-bin content is one call measured in minutes. No value of a single global timeout is right for both a
`GetFolders` and that.

**2. The spec's model of the bin was wrong.** It said `DeleteDomain` *"scatters the domain's contents into
the recycle bin as individual items"* — from the 34525 training verification. The observed shape is one
entry. The `DeletePath` matcher handles either, so nothing broke, but it explains the bad progress: the
archive half is a **single** item, so the bar can only read 0 → 1 no matter how long it takes. Corrected to
the observed behaviour rather than the training note (spec rev 24). Another instance of the standing lesson
about assuming a MAGIQ semantic.

**3. We retried it. Four times.** `IsTransient` covers `TaskCanceledException` and `HttpRequestException`,
and `MagiqMaxRetries` defaults to 3, so a timed-out `PurgeRecycleBinItem` was re-issued up to four times —
each attempt asking the service to start another destroy while it was still grinding through the first. This
is the real bug, and it would be a bug at *any* timeout value. **A transport failure on a non-idempotent
destructive call does not mean it failed. It means we do not know.**

**Decision.**

- **Per-operation policies.** `SoapOperationPolicy(Timeout, RetryTransportFailures)`. `HttpClient.Timeout`
  becomes `InfiniteTimeSpan` and the deadline moves to a per-request `CancellationTokenSource` linked to the
  caller's token — `HttpClient.Timeout` is a client-wide ceiling and simply cannot express "reads get 100s,
  purge gets 30 minutes". `DeleteDomain` and `PurgeRecycleBinItem` take the destructive policy; everything
  else is unchanged. New setting `MagiqPurgeTimeoutSeconds` (default 1800, range 60–14400). It needs no DB
  action on an existing install: `ReadInt` falls back to the definition default when the row is absent.
- **A new error kind, `Indeterminate`.** Deliberately not folded into `Protocol`. `Protocol` means the call
  did not do what was asked; `Indeterminate` means nobody knows. They demand opposite handling, and
  collapsing them is what let the old code treat "no answer" as "failed".
- **Verify, don't guess.** On an indeterminate purge, `ArchiveLibraryTeardown` re-reads the recycle bin
  (`HasLeftRecycleBinAsync`) and checks whether the handle is gone. Gone → counted as purged, audited
  `Outcome = Ok` with `soapSuccess: false` and `"verifiedAgainstRecycleBin": true`, because the honest record
  is that the service never answered and we established the outcome by inspection. Still present, **or the
  bin cannot be re-read** → stays a failure. Fails closed: claiming success on the strength of a read that
  itself failed would invent the certainty the check exists to provide. The summary row gains a
  `verifiedAgainstRecycleBin` count so this is visible rather than silent.

**Why not just raise the timeout.** Considered and rejected as the whole answer. It leaves the
multiple-destroy behaviour in place, it slows failure detection on every other call if done globally, and
600s may still not be enough on a bigger library. The retry rule is the fix; the budget is the thing that
stops it happening routinely.

**Four things the review pass caught, all fixed.**

1. **An unanswered `DeleteDomain` could report a *finished* purge.** Deleting a library is itself slow, so if
   it was still running when we stopped waiting, the bin read that follows legitimately finds none of the
   library in it — and "no targets" was treated as "already gone, nothing to do", returning `true`. That is
   the same defect this entry is about, one call earlier. `PurgeAsync` now remembers an indeterminate delete
   and refuses that conclusion.
2. **The verification trusted the handle alone.** Nothing guarantees infoRouter keeps a recycle-bin handle
   stable across reads, and this very file already declines to trust it — `MatchesDeletedSourceFolder` pins
   `(name, DeletePath)` for exactly that reason. A re-issued handle would have read as proof of a purge that
   never happened. The item is now judged gone only when neither its handle nor its `(name, DeletePath)` pair
   is still in the bin.
3. **`SetupMagiqProbe` still set a finite `HttpClient.Timeout`** on the one-off client it builds a real
   `MagiqSoapClient` over, silently capping the destructive budget. Harmless today (setup only reads), fixed
   so the trap is not left set.
4. **The new setting was unreachable in the admin UI** — absent from `SETTING_KEYS` and the SOAP transport
   section, which is what `SystemSettingsPage` filters the API response against. Seeded and read, but not
   editable by anyone. Added.

Also: the per-item audit's `verifiedAgainstRecycleBin` is a boolean while the summary's count needed a
different name (`verifiedByBinRead`) — same key, two types, one audit surface.

**Deliberately left alone, and worth a decision later.** The standard policy still blind-retries `Move`,
`DeleteFolder` and `DeleteDocument`, which are also non-idempotent. A timed-out `Move` that actually
succeeded gets retried, fails *"source not found"*, and lands in the Step 10 move-failure panel where the
operator's retry fails the same way. Same root cause as this entry; out of scope for a fix driven by a live
purge failure, but it is the next one of these.

**Status:** Implemented in the product working tree (uncommitted).
`Integration/Magiq/Soap/SoapOperationPolicy.cs` (new), `MagiqSoapErrorKind.cs` (`Indeterminate`),
`MagiqSoapClient.cs` (policies, per-request deadline, policy-scoped retry budget, indeterminate mapping),
`Program.cs` (`Timeout.InfiniteTimeSpan`), `Configuration/Settings/*` (new `MagiqPurgeTimeoutSeconds`),
`Pipeline/ArchiveLibraryTeardown.cs` (verification + audit), `Features/Setup/SetupMagiqProbe.cs`.
SPA: `admin/settingsEditing.tsx`. Tests: six new cases in `Pipeline/ArchiveLibraryTeardownTests.cs` —
verified-gone, still-there, bin-unreadable, never-re-issued, indeterminate-DeleteDomain, and
handle-re-issued — with the SOAP double gaining an indeterminate mode and a mutable bin. `npx tsc -b --force`
clean. `dotnet build`/`dotnet test` pending on
Chase's machine.

---

## [2026-08-17] Operator-surface pass: liveness that means something, summaries before walls of text, and setup that finishes

**Context.** A set of SPA changes requested after watching the tool in use, plus one that is not cosmetic at
all: first-run setup finished without the MAGIQ Documents connection string and told the operator to set it
in System Settings afterwards. That produced an install that *looks* configured, passes sign-in, lets a run
be created, and then fails at the first identification query. Setup's whole job is to leave the app usable;
deferring a setting the first run cannot start without meant it wasn't doing that job.

**Decisions.**

1. **The Documents connection string is captured during setup, and required.** It sits in the MAGIQ access
   step after the bootstrap sign-in (endpoint → who you are → what to query), with a **Test connection**
   action on a new `POST /setup/magiq/test-database`. That endpoint exists rather than reusing
   `POST /setup/test-connection` because the latter refuses once the *app* connection string is set — which
   it always is by this step — so reusing it would answer 409 to every call. It is gated on the MAGIQ phase
   instead (`SetupMagiqState.IsConfigured`), so it is never an open "probe a SQL Server for me" surface on a
   live install. `POST /setup/magiq` validates **and actually opens** the connection before writing anything,
   and writes it **first** — ahead of the endpoint/allowlist pair that `SetupMagiqState` reads as
   "configured" — so setup can never be observed complete with the connection string missing. It is a
   `Secret` setting, so the endpoint encrypts it via `ISecretProtector` exactly as
   `UpdateConfiguredSettingHandler` does (the store holds ciphertext; encryption is the writer's job, not the
   store's).

2. **Animation marks live work, and nothing else.** The Running badge, the phase stepper's current step, the
   Run progress transport chip and the audit trail's follow indicator animate **only while the run's status
   is `Running`** — not `AwaitingInput`, not `Failed`, not settled. The transport chip is now hidden entirely
   when the run isn't working (it used to report "live"/"polling" on a finished run, which said nothing about
   the run), and the indeterminate striped progress bar no longer runs while the run sits at an operator gate,
   where it read as motion that wasn't happening. The rule behind all of it: **a pulse that outlives the work
   it stands for teaches the operator to ignore the pulse.** Motion lives in one stylesheet
   (`theme/animations.css`), is purely decorative — every state it marks is also stated in text — and is
   switched off wholesale under `prefers-reduced-motion`.

3. **"Polling…" → "Tailing".** Polling named the transport, which is both an implementation detail and, for
   the full trail, a half-truth: its live tick refreshes the *count*, deliberately not the rows (see
   [2026-08-14]). "Tailing" names what the operator is getting, in the sense they already know from `tail -f`.

4. **Rows carry the path they refer to.** The live-activity summary names only the leaf ("Archived
   invoice.pdf"), which is unplaceable in a repository where the same name recurs under dozens of folders; the
   full source path and any error now sit on their own lines beneath it. In the full trail, the **Destination
   path** column composes a rename's recorded new name with the source's parent — a rename can only ever
   record a name (that is all `UpdateFolderProperties`/`UpdateDocumentProperties` take), so the column was
   showing a bare leaf next to a fully-qualified source. Done at render time on purpose: no schema or pipeline
   change, and it fixes the runs already recorded, whose rows can't be rewritten.

5. **The Normalization Review summarises before it lists.** A real cull normalizes hundreds to thousands of
   names, and rendering that table straight into the gate pushed the two controls that matter (Re-check,
   Confirm) below a wall of paths. The default is now the shape of the change — counts by kind, plus a tally
   of *why* ("extra spaces ×214, non-breaking space ×3") — with **Show all** revealing the unchanged, still
   filterable table. The full record remains downloadable from the pinned before/after register snapshots.

6. **Pending conflicts are grouped by the decision they pose,** not listed in plan order: identical documents
   (every version's checksum matches, so deleting the duplicate loses nothing), duplicate names with differing
   or uncomparable content (rename unless certain), and folders (rename or merge — never a delete decision,
   and content-identity doesn't apply). Each group carries the standing advice once, in its heading, instead
   of the operator re-deriving it per card.

**Status:** Implemented in the product working tree (uncommitted).
API: `Features/Setup/TestMagiqDatabase/*` (new endpoint), `Features/Setup/SaveMagiqAccess/*` (connection
string on the request; validate + open + encrypt + write-first).
SPA: `theme/animations.css` (new) + `main.tsx`, `components/StatusBadge.tsx` (opt-in `animated`),
`components/RunPhaseStepper.tsx`, `components/RunProgressPanel.tsx`, `components/OperationAuditPanel.tsx`
(`TailingBadge`, `fullDestinationPath`, restructured live rows), `wizard/NormalizationReview.tsx`
(`ChangeListSummary`, `groupConflicts`), `pages/FirstRunSetupPage.tsx`, `api/setup.ts`,
`pages/JobDetailsView.tsx`. `npx tsc -b` clean; `dotnet build`/`dotnet test` pending on Chase's machine.

---

## [2026-08-17] Step 8b execution: summary first, detail on demand, and the confirm button where every other phase puts it

**Context.** Rev 25 summarised the Step 8 *review* list. The Step 8b *execution* panel still rendered the whole
per-item table unconditionally, and put **Confirm & continue to archival** above it.

**Decisions.**

1. **Summary first, detail on demand.** The panel leads with the progress bar, the applied/failed/pending
   counts and a **per-kind** breakdown — folders and documents counted separately, because a folder rename
   repaths every pending descendant, so "12 of 40 folders" is a materially different position mid-flight from
   "12 of 40 documents". **Show detail** expands the existing table unchanged, filters and Retry buttons and
   all.

2. **The detail auto-opens exactly once, when the phase stops with failures.** That is the one state where the
   list isn't reference material — every row has a reason to read and a Retry button to press. A `useRef`
   one-shot means having opened it we never re-open it against the operator's wishes on a later poll.

3. **The confirm button moved to a footer after the content**, with a status line saying why it is or isn't
   available — the shape the Step 6–7 review, the Normalization Review and the purge control already use.
   Above the table it asked for the decision before presenting the evidence for it, and it was inconsistent
   with every other gate in the run. **Retry all failed** stayed with the table: it acts on the list, not on
   the run.

**Status:** Implemented in the product working tree (uncommitted).
SPA: `components/NormalizationExecutionPanel.tsx`. Spec rev 26. `npx tsc -b --force` clean.

---

## [2026-08-17] The rollback (and Step 12 purge) audit rows were invisible — `NULL NOT IN (…)` is NULL, not true

**Symptom.** Rollback showed nothing in the Live activity feed.

**Cause.** One line of SQL in `CleanupRunOperationStore.BuildFilter`, shared by the paged trail read, the
filtered count and the CSV export:

```sql
WHERE RunId = @runId AND Phase NOT IN ('Identification', 'ReviewSelection')
```

The intent (2026-08-13) is the audit window: the trail starts at Name Normalization, the first phase that
mutates the customer's repository, so the pre-mutation phases' rows are recorded but never surfaced. The
predicate expresses that correctly for every row that *has* a phase. **A rollback is not a pipeline phase**,
so `MoveBackAuditRow` writes `Phase = null` — and in SQL's three-valued logic `NULL NOT IN (…)` evaluates to
NULL, not true, so the row fails the WHERE and disappears. The rollback audit trail added on 2026-08-11
existed, wrote correct rows, and could not be read.

**Blast radius is wider than rollback.** `ArchiveLibraryTeardown` also appends with `phase: null`, and it is
shared by three callers — the rollback teardown, the run delete, and **the Step 12 purge**. So the per-item
and summary purge rows added for purge visibility on 2026-08-14 were invisible by the same mechanism, in the
live feed, the paged trail, the count *and* the CSV export. Both are fixed by the one predicate.

**Fix.** `AND (Phase IS NULL OR Phase NOT IN ('Identification', 'ReviewSelection'))`. Deliberately **not** the
alternative fix of stamping the teardown rows with `Cleanup`/12 for the Step 12 caller: that would thread a
phase through a helper whose whole point is that it serves three callers with different (and for two of them,
genuinely absent) phase context, and it would leave the recorded data of every existing run still unreadable.
The predicate is where the mistake was, so the predicate is what changed. Stamping the Step 12 caller's rows
with a real phase is a reasonable separate improvement — it would let the trail's filters distinguish a purge
that was part of the pipeline from one that was an undo — and is noted for the backlog, not done here.

**Why no test caught it.** `FakeCleanupRunOperationStore.Matches` mirrored every operator-facing filter but
not the audit window, so the fake was strictly more permissive than the store and the handler tests passed
either way. The fake now mirrors the rule, **including the null-phase case**, and two tests pin it: a
null-phase `MoveBack` is returned (with full paths at both ends — out of the archive, back to the original
source location), and a `ReviewSelection` row is not. The underlying defect was in raw SQL semantics, which
only a real-database test could have caught directly; making the fake agree with the store is the closest
available guard, and it is the one that would have failed.

**Also noted, not changed:** `GetDistinctPathsAsync` (the path-filter typeahead) applies no phase window at
all, so it can suggest an Identification-phase path that the trail will then show no rows for. Cosmetic, and
pre-existing.

**Status:** Implemented in the product working tree (uncommitted).
API: `Persistence/CleanupRunOperationStore.cs`. Tests: `Fakes/FakeCleanupRunOperationStore.cs` +
two cases in `Features/Runs/GetRunOperationsHandlerTests.cs`. dev-spec endpoint note updated.
`dotnet build`/`dotnet test` pending on Chase's machine.

---

## [2026-08-17] Live activity names items by full path; failure reasons get their own line

Following the rev 25 row rework: `describeOperation` now names the item by its **full source path** rather
than its leaf, and the separate path line it previously sat above was removed — one line, one path. The leaf
("Archived invoice.pdf") reads better in isolation but is unplaceable in a repository where the same document
name recurs under dozens of folders, which is the exact question the operator is watching the feed to answer.
A failure reason moved from a dimmed continuation of the description onto **its own line** beneath it: a long
SOAP error and a long path ran together into one unreadable string. `MoveBack` now shows both ends in full
(archive path → original source path), which is only visible at all because of the store fix above.

**Status:** Implemented in the product working tree (uncommitted).
SPA: `components/OperationAuditPanel.tsx`. `npx tsc -b --force` clean.

---

## [2026-08-17] "Tailing" wasn't tailing — two causes, and a superseded decision

**Symptom.** New audit rows didn't appear in Recent activity or the Operation audit trail; leaving the run view
and re-entering it showed them.

**Cause 1 — `live` was defined too narrowly (supersedes [2026-08-13] item 2).** Both surfaces polled only while
`run.status === 'Running'`. That rule was written before the work that happens at a *stopped* run, and by now
that is most of the interesting work: a **rollback** runs against a `Failed` run; the **move-failure retry**,
the **normalization retry**, the **empty-subtree prune** and the **Step 12 purge** all run while the run sits
at `AwaitingInput` or `Failed`. The result was exactly inverted — the trail was live in the state where the
operator is mostly waiting, and frozen in the states where the operator is pressing buttons that write audit
rows. Both surfaces now tail while the run is `Running`, `AwaitingInput` **or** `Failed`, and stop at a
terminal state (`Completed`/`Cancelled`/`Abandoned`) where nothing more can ever be appended.
`MoveFailuresPanel` already used this broader definition of live; the audit surfaces now agree with it, which
is also why the inconsistency was easy to miss.

I am recording this as **superseding** the 2026-08-13 decision rather than as a bug: that decision was
correct for what it was reacting to (a spinner that ran forever on a paused run). What changed underneath it
is the amount of pipeline work that now happens at a stopped run.

**Cause 2 — the trail's tick refreshed the count, not the rows (supersedes [2026-08-14]).** The full trail
deliberately polled only the filtered *count*, to keep the range label and pagination honest "without ever
touching `entries`, so the rows on screen never flicker or get replaced mid-read". The stated harm is real for
a **newest-first** trail — but this trail defaults to **oldest-first**, and there a refetch of any page except
the last returns identical rows: new rows land on later pages, so nothing the operator is reading moves. What
the count-only poll actually delivered was a pagination control advertising a new last page whose contents
never arrived. The tick now re-runs the row fetch. Under an explicitly-chosen newest-first sort the visible
rows do change on the tick — which is what choosing newest-first asks for.

**Shape of the fix.** A `tick` counter bumped by one interval, added to the existing row-fetch effect's
dependencies, replacing the separate count-only effect entirely (the row fetch already returns `total`). A
counter rather than a boolean so no two ticks can coalesce into one dependency value. `live` remains a
dependency, so the trail still does one final refresh the moment the run settles.

**Status:** Implemented in the product working tree (uncommitted).
SPA: `pages/JobDetailsView.tsx` (shared `tailing` flag for both surfaces),
`components/OperationAuditPanel.tsx` (live clock → row refetch; count-only effect removed). Spec rev 27.
`npx tsc -b --force` clean.

---

## [2026-08-17] Stop inferring liveness from run status — the audit surfaces detect activity themselves

**Symptom (third round).** Run status `Cancelled`, rollback actively running, Run progress showing items rolling
back — and no "Tailing" on either audit surface.

**The pattern, finally named.** Three attempts, all the same mistake: deciding whether to poll by reasoning
about `run.status`.

1. [2026-08-13] *only while `Running`* — missed the retries and the prune, which run at `AwaitingInput`.
2. [2026-08-17, earlier today] *any non-terminal status* — missed a **rollback of a `Cancelled` run**, which is
   terminal by status and busy in fact.

Each fix enumerated the states in which work can happen. That list is a **derived, unowned invariant**: nothing
enforces it, it lives in the SPA far from the code that decides a run's status, and every new operator action
(rollback, retry, prune, purge, and whatever comes next) can invalidate it silently. A run's status describes
its *disposition*; it was never a statement about the present moment, and we kept reading it as one.

**Decision: invert it — poll unconditionally, adapt the speed, and detect the work.** `useTailClock` runs a
clock that never stops: 5s while it observes the trail growing (newest `seq` for the feed, the filtered total
for the trail), 15s when it doesn't. `live` survives only as a *hint* biasing the initial speed. The failure
mode is now bounded and self-correcting — an unforeseen operation shows up one 15s tick late and the clock
speeds itself up — where before it was a view frozen until the operator navigated away and back. Cost is one
25-row query per 15s while a run view is open, which is not worth optimising against.

**The same principle, applied to progress.** `useRunProgress` now stamps `lastMessageAt` on every hub message,
and `isWorking(status, lastMessageAt)` is the shared answer to "working right now": `Running`, or a hub message
within 20s. The Run progress panel's live chip uses it, so a rollback reads as live instead of animating a bar
with no indication anything is running. A run merely paused at an operator gate emits nothing, so it still
reads as idle — which was the point of the original narrowing, preserved.

**Deliberately unchanged: the run status badge.** It still reads `Cancelled`, unanimated, during a rollback.
The status is the run's disposition, and pulsing it would assert the run is running, which is exactly the
conflation that caused this bug three times. If the header should say "background work in progress", that wants
its own indicator next to the badge — which needs the hub subscription lifted from `RunProgressPanel` into
`JobDetailsView` — not an overloaded status badge. Noted, not done.

**Status:** Implemented in the product working tree (uncommitted).
SPA: `hooks/useRunProgress.ts` (`lastMessageAt`, `isWorking`, `ACTIVITY_WINDOW_MS`),
`components/RunProgressPanel.tsx`, `components/OperationAuditPanel.tsx` (`useTailClock`, both surfaces),
`pages/JobDetailsView.tsx` (`likelyWorking` hint). Spec rev 28. `npx tsc -b --force` clean.

---

## [2026-08-17] Name the steps, and name each pass within a step — a step is not one operation

**Two complaints, one root cause.** (1) The run view labelled Step 11 "Cleanup (step 11)". (2) During Step 11
the progress bar reached 100% twice, reading as two operations with no way to tell what either was.

Both come from the SPA describing the pipeline in the pipeline's own vocabulary. `RunPhase.Cleanup` + step
number is exactly how `RunPhaseExecutor` thinks, and it was rendered raw. But **Cleanup** spans deleting the
emptied source folders — a `DeleteFolder`, i.e. a soft delete to the recycle bin, recoverable — and Step 12's
`DeleteDomain` + `PurgeRecycleBinItem`, which is not. Those are the two most different operations in the tool,
and the label collapsed them into one word. Meanwhile the bar filling twice was accurate and unexplained:
Step 11 really does run two passes.

**Decision 1: steps get operator-facing labels** (`theme/steps.ts`). Step 11 → "Empty folder cleanup", Step 12
→ "Purging deleted items", and so on across the pipeline. Used by the run header, the progress panel and — for
the *current* phase only — the stepper's description, which now reads "Empty folder cleanup · In progress"
instead of "Steps 11–12". The phase keeps its own name: the stepper is deliberately phase-grain, and a phase
is a real thing. What changed is that a phase whose steps do materially different work now says which step it
is on.

**Decision 2: the progress contract carries an `operation`** — the name of the individual **pass**, on
`PhaseStarted` and `ProgressUpdated`, with the values as constants in `Hubs/Messages/RunOperations.cs`
("Deleting empty folders", "Pruning empty subfolders", "Purging deleted items", "Archiving documents",
"Returning documents to their original folders", …).

This has to come from the server. The SPA cannot derive it: from the client's side a second pass is
indistinguishable from the first except that `total` changed, which is precisely the ambiguity being
complained about. Every multi-pass step is now legible:

| Step | Passes |
|---|---|
| 11 | Deleting empty folders → Pruning empty subfolders |
| 12 | Purging deleted items (archive library, then the source folders Step 11 deleted) |
| Rollback | Returning documents → Removing the archive folders → Purging the archive from the recycle bin |

Both message fields are **optional with a default**, so this is additive: every existing construction still
compiles, and a null leaves the SPA on its `(phase, step)` fallback. Old client + new server and new client +
old server both work.

**Panel layout followed the same logic.** The Run progress panel now leads with *what is happening*
("Deleting empty folders") and demotes *where in the pipeline* ("Running · Cleanup step 11") to a dimmed
second line. The operator's question is the former; the latter is context for it.

**Deliberately not done:** emitting a second `PhaseStarted` for the prune pass. The [2026-08-14] decision not
to was about avoiding repeated progress-bar resets mid-step, and it still holds — the pass already announces
itself through `operation` on its `ProgressUpdated`, which is the labelling that was missing.

**Status:** Implemented in the product working tree (uncommitted).
API: `Hubs/Messages/RunOperations.cs` (new), `Hubs/Messages/PhaseStartedMessage.cs`,
`Hubs/Messages/ProgressUpdatedMessage.cs`, `Pipeline/RunPhaseExecutor.cs` (16 emit sites labelled).
SPA: `theme/steps.ts` (new) + `theme/index.ts`, `api/runProgress.ts`, `hooks/useRunProgress.ts`,
`components/RunProgressPanel.tsx`, `components/RunPhaseStepper.tsx`, `pages/JobDetailsView.tsx`.
Spec rev 29 + dev-spec SignalR contract. `npx tsc -b --force` clean; `dotnet build`/`dotnet test` pending on
Chase's machine.

---

## [2026-08-17] Step 11's pre-delete guard refusal is a deferral, not a failure

**Symptom.** A live Step 11 produced many rows like *"Failed to delete empty folder … — Folder still has 2
subfolder(s) remaining; refusing to delete it to avoid MAGIQ cascade-removing them."* — each of which the run
then resolved by itself moments later.

**The refusal is the design working.** Step 4's candidate closure is upward-only, so a wholly-empty subfolder
this run never evaluated is invisible to it; the guard catches that at execution time (fail-closed, because
MAGIQ's `DeleteFolder` cascade-removes a still-present subfolder rather than failing), and the **second pass**
prunes the empty children so the parent then deletes cleanly. For that shape of folder — the common one — a
refusal on the first attempt is the *expected* outcome, not an error. Recording it as `Failed` meant a
completely healthy cleanup filled the activity feed with red rows the run cleared seconds later, and an
operator who learns that failures are usually noise will miss the one that isn't.

**Decision 1: a new audit outcome, `Deferred`.** The row is still written — the attempt happened, and the
sequence *deferred → pruned → deleted* is precisely what an auditor wants — but it is classified as "not
attempted yet; the run expects to clear the blocker itself". The reason goes in `Detail` (nothing errored, so
`ErrorMessage` stays null) and no `ItemFailed` is pushed. In the SPA it renders grey, labelled *Deferred*, and
reads *"Waiting to delete <path> — pruning its empty subfolders first"*.

Scoped narrowly on purpose: only the guard's **"still has subfolders"** refusal defers. Its sibling *"could not
verify … before deleting it"* means the listing call itself failed, which is a real problem, and stays a
failure — so the guard's single error code was split into two (`PreDeleteGuard`, `PreDeleteGuardSubfolders`)
behind an `IsPreDeleteGuard` helper for the places that only care that the refusal was ours. The
operator-initiated retry also still reports `Failed`: nothing will automatically resolve it there, because a
retry does not run the prune.

**The folder row deliberately still goes to `Failed`.** That status is the durable handoff to the prune pass
(`BuildPrunePlanAsync` selects `Status = Failed`) and it is what keeps an *unresolved* deferral visible in the
Folder cleanup failures panel after the run settles. Introducing a `FolderStatus.Deferred` would have meant a
schema value, a second status for the prune, the manual prune endpoint and the failures panel to understand,
and a new way for a folder to be quietly lost between passes — all to restate something the audit row now says.
Only the classification of the *audit row* changed; the guard, the handoff, the prune and the resolution are
untouched.

**Decision 2 (found while fixing the above): a guard refusal no longer triggers the rule handling.**
`RunFolderGroupAsync` relaxed the parent's rule whenever *any* op in the group failed — including a guard
refusal. So a deferred folder dragged its parent through a `GetFolderRules` and, where that parent disallowed
folder deletes, an actual relax → retry (which the guard refused again, because a rule change cannot make a
live subfolder disappear) → restore. Real, needless mutations of the customer's folder rules, in a codebase
that has already been bitten twice by rule churn. The group now treats a guard refusal as "not rule-blocked",
which is the same rule the prune's tree-wide escalation has always applied to our own refusals.

**Status:** Implemented in the product working tree (uncommitted).
API: `Domain/RunOperationOutcome.cs` (`Deferred`), `Pipeline/RunPhaseExecutor.cs` (split guard code +
`IsPreDeleteGuard`, deferral classification in the Step 11 pass, `RunFolderGroupAsync` skip).
SPA: `api/runs.ts`, `components/OperationAuditPanel.tsx` (label, colour, description, reason line).
Tests: `Pipeline/RunPhaseExecutorRuleGuardTests.cs` — a new case proving the refusal audits as `Deferred` with
its reason in `Detail`, pushes no failed item, touches no folder rules, and still leaves the folder row
`Failed` with its reason; the SOAP double gained a parameterised folder listing and the harness now exposes the
audit store and a recording progress notifier. Spec rev 30 + dev-spec column comment.
`npx tsc -b --force` clean; `dotnet build`/`dotnet test` pending on Chase's machine.

---

## [2026-08-17] Picker placeholders: reserve the space rather than collapse it

**Problem.** The three pickers — the new-run source library list, the Step 8/9 archive-destination library
list, and the folder browser shared by both — replaced their list with a one-line "Loading…" while fetching.
Every navigation therefore collapsed the control to a single line and then re-expanded it: opening a folder,
walking back up a breadcrumb, switching library. In the Step 8/9 modal that moves the confirm buttons up and
down the screen between clicks, which is how a misclick happens on an irreversible-ish choice.

**Decision.** Placeholder (skeleton) rows shaped like the content that is coming, in one shared
`PickerSkeleton`, with two details that matter more than the skeleton itself:

- **Geometry comes from the caller's own `rowStyle`.** Each picker passes the same style constant its real
  rows use, and the skeleton's height is `calc(var(--mantine-font-size-sm) * var(--mantine-line-height-sm))`
  — one line of the same text — rather than a pixel guess. Placeholder and loaded row are the same height by
  construction, not by two numbers someone has to keep in agreement.
- **The row count is remembered from the last listing that loaded** (`usePlaceholderRowCount`, clamped 3–6).
  The jump the operator actually notices is the one *between* navigations, where a list they can see becomes a
  spinner and then another list; reusing the previous count holds the control near its current height. The
  ceiling is 6 because the lists sit in a `ScrollArea.Autosize` capped at 220–280px — a taller placeholder
  block would just trade one jump for the opposite one.

Widths vary across rows so it reads as "names are coming" rather than as a progress bar, and are a fixed
cycle rather than random: random widths re-roll on any re-render mid-load and make the placeholder twitch.

Presentation only — nothing changed about what is fetched or when.

**Status:** Implemented in the product working tree (uncommitted).
SPA: `components/PickerSkeleton.tsx` (new), `components/FolderBrowser.tsx`, `components/NewRunForm.tsx`,
`wizard/Step8ArchiveLibraryModal.tsx`. Spec rev 31. `npx tsc -b --force` clean.

---

## [2026-08-17] Pickers hold their height while filtering too

The placeholder work [2026-08-17] stopped the pickers collapsing while a listing *loads*. Filtering had the
same defect from a different direction: narrowing thirty folders to two shrinks the list by a few hundred
pixels, so whatever sits below it jumps up under the operator's cursor mid-interaction — and back down when
they press backspace.

**Decision.** `useReservedListHeight` measures the list **unfiltered** and applies that as a `mih` on the
scroll container while a filter is active. Three details:

- **Only the unfiltered list is measured.** A filtered one is precisely what must not define the size.
- **The measurement is clamped to the list's own `mah`.** Past that the list is already scrolling, so its
  content height is far taller than its box and reserving it would blow the layout open. The cap is now a
  named constant per picker, used by both the `mah` and the clamp, so they cannot drift apart.
- **The "no matches" message moved inside the reserved box** instead of replacing it — otherwise filtering
  down to zero was the one case that still collapsed, and it is the most common way to reach a narrow result.

A `useLayoutEffect`, not an effect: the height is read and re-applied in the same frame the rows render, so
the box never paints at the wrong size first.

`components/PickerSkeleton.tsx` became `components/PickerList.tsx` — it now holds the skeleton plus both
sizing hooks, and the old name had stopped describing it.

**Status:** Implemented in the product working tree (uncommitted).
SPA: `components/PickerList.tsx` (renamed, `useReservedListHeight` added), `components/FolderBrowser.tsx`,
`components/NewRunForm.tsx`, `wizard/Step8ArchiveLibraryModal.tsx`. Spec rev 32. `npx tsc -b --force` clean.

---

## [2026-08-17] Start-a-run form: cutoff first, and label the source picker as required

Four small changes to the new-run modal, all the same theme — the form knew what it needed but did not say so.

1. **The cutoff moved above the source picker.** It is the decision the run is about, it is one field, and it
   frames what the operator is then choosing a library or folder *for*. Below the picker it also sat behind a
   library list tall enough to push it off the bottom of the modal.
2. **It gained a description** of what the date does: documents last modified on or before it are archived and
   their emptied folders removed; anything newer is kept *and protects every folder above it* — that second
   half is Rule 2, and it is the part operators are surprised by.
3. **The source picker got a required label** (*Library or folder to cull*), rendered through an
   `Input.Wrapper` so its asterisk and typography match the cutoff's exactly. Two required inputs sat side by
   side with only one of them marked, which made the picker read as an optional refinement.
4. **A description under the Library/Folder tabs** saying what each selects. That choice decides how much of
   the repository the run may touch — whole library versus one subtree — so it belongs before the choice, not
   in the confirmation text that appears after it. It is placed under the tabs rather than in the wrapper's
   own `description` slot, which Mantine renders above the control.

**Status:** Implemented in the product working tree (uncommitted).
SPA: `components/NewRunForm.tsx`. Spec rev 33. `npx tsc -b --force` clean.

---

## [2026-08-17] Folder browser: one up control, and search above the address bar

**Two changes to `FolderBrowser`, applying to both callers.**

**"Change library" folded into the breadcrumb as an up-folder button.** It was a separate text link sitting
above the browser, expressing navigation the breadcrumb was already expressing — and it only handled the
outermost step, so leaving a library was a different gesture from going up a level inside one. The up button
is a single control with two meanings, the way a file manager's is: up one level while a level remains, and at
the library root back out to the library list (via the new optional `onExitLibrary`). Disabled when neither
applies — a browser whose caller owns no library list and whose trail is empty. The tooltip names the
destination rather than the action ("Up to 2019", "Back to the library list"), since the action is obvious
from the icon and the destination is what the operator is deciding about.

**Search moved above the breadcrumb.** The breadcrumb is the address of the list beneath it; with the search
box between them, the trail and the folders it describes were separated by an unrelated control. Above the
breadcrumb the reading order is: narrow it → where am I → what's here.

**Status:** Implemented in the product working tree (uncommitted).
SPA: `components/FolderBrowser.tsx` (up control, `onExitLibrary`, reordered), `theme/icons.ts` (`folderUp`),
`components/NewRunForm.tsx`, `wizard/Step8ArchiveLibraryModal.tsx` (links removed, prop wired).
Spec rev 34. `npx tsc -b --force` clean.

---

## [2026-08-17] The phase log belongs to the stepper, not to a card of its own

**Problem (Chase).** The phase log is a review artifact — nobody works with it while a run is in flight — yet
it held a full card at the bottom of the run view on every run, active or finished, pushing the panels that
*are* worked with further down.

**Decision: fold it into the phase stepper, behind a closed-by-default disclosure.**

The two are the same information at different resolutions. The stepper answers *where is this run*; the phase
log answers *when did it get there*, from the same phase/step transitions. Putting the log in the stepper's
card puts it where its context already is, and deletes a card rather than relocating one — which was the point
of the request.

Alternatives weighed: a second tab on the audit-trail card (consolidates the two logs, but keeps a large card
and leaves the phase log a table you scroll past), and simply collapsing it where it stood (cheapest, but
leaves a card whose entire content is one link). The stepper won because it removes a surface instead of
re-dressing one.

**Nothing shows on an active run unless asked for** — no timings on the face of the stepper, disclosure
closed, only a `Phase timeline (14)` link. A failed phase does not depend on it: the stepper already renders
that phase red, and the failure itself surfaces in the panel that owns it (move failures, folder cleanup
failures, the normalization results table) with something actionable attached, which a log row never has.

The table itself is deliberately plain — no filters, paging or sorting. It is a dozen rows on the longest run,
and everything that would justify that machinery is the operation audit trail's job. Its rows now name steps
through `stepLabel`, so "Empty folder cleanup" rather than "Cleanup / 11", consistent with the header, the
progress panel and the stepper.

**Status:** Implemented in the product working tree (uncommitted).
SPA: `components/RunPhaseStepper.tsx` (owns the log; new `PhaseTimeline`), `pages/JobDetailsView.tsx`
(`RunPhaseLog` deleted, `log` passed to the stepper). Spec rev 35. `npx tsc -b --force` clean.

---

## [2026-08-18] Re-run from Step 1 clears the previous attempt's derived state

**Context:** *Re-run from Step 1* (`POST /runs/{runId}/rerun`, Story 34527) rewinds a clean-slate terminal
run and starts it again. The run **keeps its id** — that is the whole shape of the feature. `CleanupRun.Rerun`
already discarded the archive/purge/rollback bookkeeping, and the identification phase clears and rebuilds
`CleanupRunDocument`/`CleanupRunFolder` itself. Three other per-run tables had no such treatment: they were
reachable only by hard-deleting the run, so a re-run silently inherited them from the abandoned attempt.

Two distinct problems, one cosmetic and one not:

- **`RegisterExport`** — the Run details **Document Register** panel lists a run's exports by run id, so the
  previous attempt's pinned before/after snapshots (`PreRun`, `PostReview`, `PreNormalization`,
  `PostNormalization`, `PostRun`) and its on-demand export presented as belonging to the new attempt. An
  operator comparing "before" against "after" would be diffing two different runs of the tool.
- **`CleanupRunRename` / `CleanupRunNameConflict`** — worse, and only found while fixing the first. Step 8a
  persists a fresh plan **only when no rename rows exist** (`if (existing.Count == 0)`, the idempotent-resume
  guard). A re-run therefore skipped planning entirely and re-applied the *previous* attempt's rename plan
  against the current library — addressing items by paths that may no longer exist, and missing names that
  now need normalizing. A correctness bug, not a display one.

**Decision:** Add `ICleanupRunStore.ClearRerunStateAsync(runId, ct)` — a single transaction deleting
`RegisterExport`, `CleanupRunRename`, and `CleanupRunNameConflictItem` + `CleanupRunNameConflict` for the run
— and call it from `RerunRunHandler`.

Two deliberate boundaries:

- **The audit trail and phase log are kept.** `CleanupRunOperation` and `CleanupRunPhaseLog` record what the
  previous attempt actually did in MAGIQ and the rollback that made the run re-runnable. A re-run must not
  erase that; only *re-derivable* state is cleared. This is the line between the two: if the new attempt will
  regenerate it, clear it; if it is a record of something that happened, keep it.
- **The clear runs before the rewind, not after.** If it throws, the run is still terminal and still
  re-runnable — the recoverable direction. Rewinding first would risk a run sitting `Running` with stale state
  and no identification job enqueued, which no operator action resolves. The cost of the chosen order is that
  a failure between clear and rewind loses the register exports of a run that is provably clean-slate; that is
  the cheaper loss, and the operator simply re-runs again.

**Alternatives weighed:** *keep everything and mark it superseded* with a run-attempt number, so the SPA could
group the previous attempt's snapshots — the most informative option, but it needs a schema column, store and
SPA changes, and it does nothing about the rename-plan bug, which needs the rows gone regardless. *Clear the
pinned snapshots but keep the AdHoc export* — leaves a row dated to an attempt that no longer exists, for no
gain. *Do it in the handler with three injected stores* — no transaction, so a partial failure could leave a
stale rename plan behind while the register was cleared, which is the exact state this fixes.

**Status:** Implemented in the product working tree (uncommitted). API:
`Persistence/ICleanupRunStore.cs` + `CleanupRunStore.cs` (`ClearRerunStateAsync`),
`Features/Runs/RerunRun/RerunRunHandler.cs`, `RerunRunEndpoint.cs` (summary).
Tests: new `Features/Runs/RerunRunHandlerTests.cs` (clears on success, does **not** clear when a guard
rejects, unknown run, rewind + re-enqueue); `Fakes/FakeCleanupRunStore.cs` and the
`CancellingRunStore` stub in `RunPhaseExecutorSubtreePruneTests.cs` implement the new member.
No SPA change needed — `RegisterSnapshots` already renders the empty case with its "No snapshots yet"
explanation. Spec rev 36; dev-spec endpoint table gains the `/rerun` row.

---

## [2026-08-18] Step 8 review — one layout across both of its states

**Context:** The Normalization Review card renders two states from one component — *Review name changes*
(clean plan, confirm-and-go) and *Resolve name conflicts* (pending conflicts, work-through-and-submit). Chase
read the review state as "messy and all over the place". It is, and for four specific reasons:

1. **The register note was pinned opposite the headline count.** `Group justify="space-between"` put
   `**1,284** name changes planned` on the left and a two-line sentence about where to download the list on
   the right. An aside and a headline figure given equal billing; at any narrow card width the sentence
   wrapped into the number. This was the single biggest contributor to the "broken" look.
2. **Counts were prose, not figures.** Four `Label <b>N</b>` texts in a row read label-first, burying each
   number mid-sentence, at the same size and weight as the body copy around them. Nothing said "these are
   the numbers".
3. **A bare "Because of" label** floated beside its badges with no anchor.
4. **Both states had drifted into two near-identical hand-rolled footers**, and the conflict state put its
   `ImpactSummary` tally at the *bottom*, so the two Step 8 screens an operator sees back-to-back had
   different information architecture.

**Decision:** Rebuild on the skeleton `NormalizationExecutionPanel` already uses (rev 26) — header with the
headline counts beside the title → one description → summary → disclosure → detail → footer:

- **Counts move into the header row**, right-aligned against the title. "How big is this?" is the first
  question either state is asked, so it is answered level with the title rather than three blocks down. The
  conflict state shows `N conflicts / N confirmed`; the review state shows `N name changes`.
- **New `Stat` + `StatRow`** — number first at `size="xl"`, label under it, the row on one inset
  `Paper`. Both summaries use it, so the figures are one bounded surface distinct from the prose explaining
  them and the table evidencing them. `tone` colours a destructive count (folder merges, duplicate deletes)
  only when non-zero, so a plan that destroys nothing says so without drawing the eye.
- **The register note moves under the *Show all* link.** Both answer "I want to look at the actual list", so
  they belong together; it also gets it out of the header entirely.
- **The reason tally gets a real label** (*Why these names change*).
- **`ReviewFooter` extracted** — status line left, Re-check + the commit action right — and used by both
  states, matching the footer every other operator gate ends with.
- **`ImpactSummary` moves above the conflict cards**, so summary-then-detail-then-action holds in both
  states. The live tally is no longer beside the button, but the header's confirmed-count and the footer's
  status line both track progress, and the tally's job is scope-setting.

Descriptions were also cut (the review state's dropped from four sentences to three) — the "download the
before → after list" clause was doing the register note's job a second time.

**Deliberately unchanged:** `ConflictCard` and its per-item Keep/Rename/Delete controls. Those are a working
surface, not a summary; they are dense because the decision is. The `NameChangesTable` behind *Show all* is
untouched, filter and all.

**Status:** Implemented in the product working tree (uncommitted). SPA:
`wizard/NormalizationReview.tsx` only (new `Stat`, `StatRow`, `ReviewFooter`; header, both summaries and both
footers reworked). No API change. `npx tsc -b --force` clean. Spec rev 37.

---

## [2026-08-18] Live activity — the outcome badge is sized to the widest outcome

**Context:** Each live-activity row is `[outcome badge] [description]`, with a reason line hanging beneath.
The badge shrink-wrapped its own text, so its width varied by row — `Ok` is two characters, `Deferred` is
eight. Every row therefore started its description at a different x. That alone would be untidy; what makes
it a real problem is that the description carries the item's **full path** (it is the only path line the row
has), which wraps to two or three lines on a deep folder, and the reason line beneath it wraps again. So each
row wrapped at a different column, and a feed of mixed outcomes — exactly what Step 11 produces now that a
guard refusal is `Deferred` rather than `Failed` (`decisions/log.md` [2026-08-17]) — read as ragged.

**Decision:** Give the badge a **minimum width sized to the longest outcome**, so the description column is
fixed however short the outcome. The full audit trail already does the equivalent for its Outcome column
(`FIXED_COLUMNS`, sized against the whole enum universe rather than the current page) — this is the same rule
applied to the feed, which had simply never had it. The reason line's indent derives from the same constant
plus the row's gap, replacing a magic `pl={26}` that matched neither the badge nor the gap.

Three details worth keeping:

- **Derived from `OUTCOME_LABELS`**, over both the enum names and their labels — the badge renders the raw
  `e.outcome`, the filter renders the label, and they coincide today but need not. A new or renamed outcome
  stays covered without anyone remembering this constant exists.
- **`em`, not `ch`.** Mantine renders badge text uppercase and bold with 0.25px letter-spacing, so the
  `0`-width `ch` unit under-measures it by roughly a fifth. That matters because the badge root is
  `overflow: hidden; text-overflow: ellipsis` — under-measuring *clips* ("DEFERRE…") rather than merely
  misaligning. 0.75em deliberately over-estimates an uppercase bold glyph: erring wide costs a few pixels,
  erring narrow costs the alignment the change exists for.
- **`miw`, not `w`.** If the estimate ever falls short the badge grows instead of clipping. The dot variant's
  root is `inline-grid` with `grid-template-columns: auto 1fr`, so the extra width lands in the label column
  and the content stays left-packed with no justify override.

**Alternatives weighed:** measuring the text with the file's existing `measureTextWidth` + `fontOf` helpers,
as the trail table does — most accurate, but it needs a ref and a layout effect in a component that has
neither, for a four-value enum whose widest member is known at author time. A hardcoded pixel width — same
result, but silently wrong the first time an outcome is added.

**Status:** Implemented in the product working tree (uncommitted). SPA:
`components/OperationAuditPanel.tsx` only (`LONGEST_OUTCOME`, `OUTCOME_BADGE_WIDTH`,
`OUTCOME_REASON_INDENT`; badge and reason line in `LiveActivityFeed`). No API change. The full audit trail
is untouched — it was already correct. `npx tsc -b --force` clean. Spec rev 38.

---

## [2026-08-18] Document Register — one list of everything a run produces

**Context:** Three related problems with the run view's downloadable records.

**(1) The deleted folder manifest lived in its own card** at the bottom of the run view
(`decisions/log.md` [2026-08-14], where it was deliberately *not* folded into the failures panel — that
panel self-hides on a clean run, and a clean run is exactly when the manifest matters). That reasoning still
holds against the failures panel, but it was never an argument for a separate card: the manifest is a
downloadable record of what the run did to the repository, which is precisely what the Document Register
card is. An operator looking for "the files this run produced" had to know about two places.

**(2) No item said what it contained.** Each row was a coloured badge, a format and a row count. Choosing
between five near-identically-shaped CSVs meant already knowing the pipeline.

**(3) The labels were timeline markers, and awkward ones.** `Before (pre-run)` said the same thing twice.
`After review (pre-normalization)` pinned one file to two different points in the run and left the reader to
work out which mattered. `Name changes — before` / `— after` read as two sentence fragments. The list was a
set of timestamps to decode rather than a set of documents to pick from.

**Decision:**

- **Titles name the artefact, not the moment**: `Starting register`, `Reviewed plan`, `Planned name
  changes`, `Applied name changes`, `Final outcome`, `Deleted folder manifest`, `On-demand export`. The
  before/after pairing is still legible (planned/applied, starting/final) without a parenthetical.
- **Each row carries a one-line description** of what is in the file, always visible — not a tooltip, which
  hides content behind a hover and is useless on touch. The card's intro paragraph shrank to two lines,
  since the per-item lines now carry the detail it was summarising.
- **The manifest becomes a row in that list.** It differs mechanically — a synchronous CSV from
  `GET /runs/{runId}/folders/deleted/export`, not a pinned background render, so it has no row count and is
  never `Pending` — which a shared `RegisterFile` view-model absorbs. `RegisterSnapshots` became
  `RegisterFiles`; `DeletedFolderManifestPanel` is deleted.
- **Order is the run's own timeline**, with the manifest between the final outcome and the on-demand export:
  it is a different artefact (folders, not documents), not a later one.

**The cost, and what pays for it:** the manifest loses a dedicated card, which is a discoverability
regression at exactly the moment it matters most — before the purge, when it is about to become the only
record of the deleted structure. Mitigated by giving it the one warm-coloured badge in an otherwise cool
list, by keeping its "take this before you purge" line in the description, and by the purge confirmation's
prompt now naming the Document Register explicitly rather than "this page".

**Also considered:** making the manifest a real `RegisterSnapshotKind` so it flows through the same export
job. Rejected — it would put a synchronous CSV behind a background render and a poll for no gain, and the
manifest is derived from the audit trail (`DeletedSourceFolders.From`), not from a register query.

**Two accessibility fixes taken while here**, both surfaced by a review pass over the new list. Seven rows
whose only control reads "Download" gave a screen-reader user seven identically named buttons, the
distinguishing title sitting in a sibling badge that does not label the control — each now carries
`aria-label={`Download ${title}`}` (the manifest had had a distinct "Download manifest" button before the
move, so this was a regression the move introduced). And the `Failed` state wrapped a bare `Text` in a
Tooltip, making the failure reason hover-only and unreachable by keyboard — it is now focusable with the
reason in its accessible name. The second was pre-existing in `RegisterSnapshots`, not caused by this change.

**Status:** Implemented in the product working tree (uncommitted). SPA only, no API change:
`pages/JobDetailsView.tsx` (`registerFileInfo`, `RegisterFile`, `RegisterFiles`, `REGISTER_ORDER`,
`MANIFEST_KEY`, `downloadManifest`), `wizard/PurgeControl.tsx` (confirmation copy),
`wizard/NormalizationReview.tsx` (its register pointer named the now-gone "before"/"after" snapshots),
`components/DeletedFolderManifestPanel.tsx` deleted. `npx tsc -b --force` clean. Spec rev 39.

---

## [2026-08-18] Archived and purged document records

**Context:** The Document Register said what the run *planned* and what the repository *looked like*, but nothing
said what it **did to the documents themselves**: where they went, and what the purge destroyed. The deleted
folder manifest covers the structural half (which folders were removed); there was no document equivalent.

**Decision:** Two new synchronous CSV exports, modelled on the manifest, added to the register list:

- **Archived documents** — `GET /runs/{runId}/documents/archived/export`. Every document Step 10 moved into
  the archive, with its source path and the path it landed at. Available once anything has moved.
- **Purged documents** — `GET /runs/{runId}/documents/purged/export`. What Step 12 irreversibly destroyed.
  Available once the run completes.

Both derive from the **operation audit trail** via new single-definition types (`ArchivedDocuments`,
`ArchivePurge`), mirroring `DeletedSourceFolders`. No new `RegisterSnapshotKind`, no schema change, no
pipeline hook, no background job: the source rows are durable, and a run that reached archival has MAGIQ
history so it is archived rather than hard-deleted. The trail is used rather than `CleanupRunDocument`
because the audit row carries **the destination the move actually used**; the document row does not store it,
so reading those would mean recomputing the path now and hoping it matched.

**The grain problem, and why the purged file is honest about it.** `DeleteDomain` puts the archive into the
recycle bin as **one very large entry** (spec rev 24), so purging it destroys everything inside in one
operation and MAGIQ confirms the destruction *once, for the library*. There is no per-document purge record
and none can be exported. Each row is therefore an inference — *this run archived it, and the archive was
purged* — and the file says exactly that in its header, prints the two library-level confirmations it rests
on, and carries a `Basis` column. Presenting derived rows as confirmed ones would make the file worse than no
file, because it would be trusted more than it deserves. Chase chose the derived-documents form over the
literal purge record, which never names a document and whose folder half duplicates the manifest.

**Three bugs caught in review before this shipped**, all in the purged export and all of the same kind —
claiming an irreversible destruction that did not happen:

1. **A rolled-back run reported every archived document as destroyed.** The Tier 2 rollback moves documents
   back and *then* tears down the archive through the same `DeleteDomain` + purge Step 12 uses, so the trail
   is indistinguishable — but the archive was empty when destroyed. `ArchivePurge` deliberately cannot tell
   them apart; the handler now checks `RollbackStatus != None` (any state, not just `Succeeded`: a failed or
   in-progress rollback returned an unknown subset, so the honest answer is "cannot say", not a list).
2. **The archive's bin entry was matched by item name, which would have made the file permanently empty.**
   The SOAP client reads an item's `Name` from the first of `name`/`title`/`path`/`fullpath`/… present, so it
   may arrive as a full path — and under the scattered-entry shape it is a document's name. Neither equals
   the library name. Matching now uses **`DeletePath`**, which is what the teardown itself selects archive
   items by and which every per-item row records verbatim in `Detail`. Same rule as the teardown, on the
   escaped form.
3. **A re-run of a rolled-back run would have resurrected attempt 1's purge as attempt 2's.** `Rerun` resets
   `RollbackStatus` and `ArchiveLibraryName`, but `ClearRerunStateAsync` deliberately keeps the audit trail
   (`decisions/log.md` [2026-08-18]) — so the old `DeleteDomain`/`Purge` rows survive with nothing on the run
   to disown them, and if the operator reused the archive library name a name match would adopt them.
   Mitigated without new schema by requiring a purge to **post-date this attempt's last archival activity**,
   which holds by construction for a real purge and excludes a prior attempt's; and by requiring the run's
   *current* `ArchiveLibraryName` rather than falling back to the name on the audit rows.

**Known residual — flagged, not fixed.** Point 3's mitigation is a heuristic, not attempt scoping. The audit
trail spans re-run attempts with no boundary marker, so the *archived* export can still list a previous
attempt's moves. Doing this properly needs an attempt watermark on the run (a `Seq` or attempt number written
at re-run) and touches the schema; it is a separate unit of work.

`DeleteDomain`'s single-entry shape also contradicted a stale comment on `DeleteAndPurgeArchiveAsync`, which
still described the pre-rev-24 scattered-items model; corrected in the same pass. `ExportDeletedFoldersHandler`
was folded onto the new shared `CsvText` helpers so the RFC 4180 escaping exists once rather than three times.

**Status:** Implemented in the product working tree (uncommitted). API: `Pipeline/ArchivedDocuments.cs`,
`Pipeline/ArchivePurge.cs`, `Features/Runs/Exports/RunCsvExport.cs`,
`Features/Runs/ExportArchivedDocuments/*`, `Features/Runs/ExportPurgedDocuments/*`, plus the comment fix in
`RunPhaseExecutor.cs` and the helper fold in `ExportDeletedFoldersHandler.cs`. SPA: `api/runs.ts`
(two download helpers), `pages/JobDetailsView.tsx` (two register rows). Endpoints and handlers are picked up
by FastEndpoints' assembly scan — no registration needed. **Not yet compiled**: no .NET SDK available in this
environment, so the C# is inspection-verified only and needs a `dotnet build` + `dotnet test`.
`npx tsc -b --force` clean for the SPA. Spec rev 40.

---

## [2026-08-18] SPA routes — the URL names the page

**Context:** The shell held its current page in `useState`, so the whole app lived at one URL. A refresh, a
bookmark or a browser restart always landed back on the runs list, the browser's Back button did nothing
useful, and — the one that actually costs the operator something — a run could not be linked to. "Have a look
at this run" meant "open the tool, go to Runs, find the row from 2026-08-14".

**Decision:** Four addressable routes, flat: `/runs`, `/runs/{runId}`, `/queries`, `/settings`, with `/`
resolving to the runs list. Implemented as a **hand-rolled `useRoute` hook** over the History API
(`routing/routes.ts`) rather than by adding a routing library.

The SPA has seven runtime dependencies and no routing or state library at all — data fetching is plain
`fetch`, state is `useState`. Four routes and one parameter do not justify changing that posture for an
on-prem, single-artifact deployment. The hook is ~110 lines: a `Route` union, `parseRoute`, `routePath`, a
`popstate` listener and a normalisation effect. If nested or guarded routes ever appear, that is the point to
reconsider — the union makes the switch a compile error rather than a silent gap.

**Nothing was needed server-side.** `Program.cs` already had `MapFallbackToFile("index.html")` registered
last, after `UseStaticFiles` and `UseFastEndpoints` (whose routes are all under the `api` prefix), so deep
links already resolved on both hosts — IIS sends `path="*"` to ANCMv2 in-process, Docker runs the same
Kestrel pipeline, and Vite's dev server does history fallback by default. Vite's `base` is `/`, so the
root-absolute `/assets/*` references resolve from a two-segment URL.

**Two details that make the URLs worth having:**

- **Nav items and run rows are real anchors** with real `href`s. Only a plain left click is intercepted;
  modifier-clicks and middle-clicks fall through, so "open in a new tab" and "copy link address" work, and
  the status bar previews the destination. A row `onClick` alone cannot be copied, opened in a new tab, or
  reached by keyboard — and the dashboard's rows were previously keyboard-unreachable, so the anchor is also
  an accessibility fix. The row stays clickable for convenience; the anchor stops propagation so the two
  never fire the same navigation twice.
- **The page segment matches case-insensitively.** The server's fallback serves `/Runs/{id}` as happily as
  `/runs/{id}`, so an exact match would parse a good pasted link as nothing and quietly redirect to the run
  list, losing the id with no error. Mail clients and Windows habits both produce that, and pasted links are
  the whole point. The run id itself stays case-sensitive — it is opaque.

Deep links survive the sign-in gate for free: the login screen renders at whatever URL the operator arrived
on and never navigates, so the shell reads that same URL once the session is established. The same holds for
a mid-session 401 — re-authenticating returns the operator to the run they were on.

**Known limitation:** `routePath` emits root-absolute paths, so the app cannot be hosted under an IIS virtual
directory. That was already true — `vite base` is `/`, so `/assets/*` would 404 first — and the README
describes pointing an IIS *site* at the publish output, not an application beneath one. Worth knowing before
anyone tries it. Query strings and hash fragments are likewise not preserved across navigation; nothing uses
them today.

**Also fixed, unrelated and pre-existing:** `JobsDashboard`'s `TOTAL_STEPS` was still `11`, left over from
before Name Normalization pushed cleanup out to Steps 11–12, so a purging run computed 109% (clamped by
`Progress`, but wrong).

**Status:** Implemented in the product working tree (uncommitted). SPA only, no API change:
new `routing/routes.ts`; `App.tsx` (shell driven by the route, nav items as anchors);
`pages/JobsDashboard.tsx` (run name as an anchor, `TOTAL_STEPS`). `npx tsc -b --force` clean. Spec rev 41.

---

## [2026-08-18] Folder browser — breadcrumb above the filter box

**Context:** Rev 34 (`decisions/log.md` [2026-08-17]) put the filter box *above* the breadcrumb, reasoning
that the breadcrumb is the browser's address bar and so belongs directly above the list it addresses — with
the search box between them separating the trail from its contents.

**Decision:** Reverse it. The order is now **breadcrumb → filter box → folder list**.

Read top-down that is *where you are* → *how to narrow it* → *what is here*, which is both the order a file
manager puts them in (Explorer, Finder, OneDrive all lead with the path) and the order the operator asks the
questions in: they orient first, then filter. Rev 34's argument was about adjacency — keeping the trail next
to its list — but adjacency is the weaker claim here, because the filter box is *also* about the current
location (its placeholder literally names it: "Filter folders in {current}"), so it sits perfectly well
between the two. Leading with the address is the stronger convention, and this is a picker operators use
against an unfamiliar library where knowing where they are matters most.

The up control keeps its place at the head of the breadcrumb row — it is trail navigation, so it belongs with
the trail, which rev 34 got right and this does not disturb.

One change covers both callers: `FolderBrowser` is shared by the new-run source picker and the Step 8/9
archive-destination picker, and it holds the only breadcrumb in the SPA.

**Status:** Implemented in the product working tree (uncommitted). SPA only, one file:
`components/FolderBrowser.tsx` (the two `Group`s swapped; the comment that argued for the old order replaced
with this one). No API change. `npx tsc -b --force` clean. Spec rev 42, superseding rev 34's ordering.

---

## [2026-08-18] Step 12 destroys the archive in chunks, not in one call

**Context:** Chase, from watching a live cull: "in the cleanup phase, step 12 we perform a recycle bin purge of
all the items we have deleted. The issue is deleting the top level archive path. Sometimes the top level
contains so many items it takes a very long time to delete and the UI appears inactive and seems like it's
locked."

That is exactly what the code did. `DeleteDomain` bins the whole archive library as **one** entry (spec rev 24,
`decisions/log.md` [2026-08-17]), so `PurgeRecycleBinItem` against it was a single call of many minutes whose
progress could only ever read `0/1`. Every mitigation so far was around the edges — the 30-minute budget, the
no-retry rule, the indeterminate re-read, the always-on tail clock. None of them could make one call countable.
During the one part of the run that cannot be undone, the operator's honest reading of the screen was that the
tool had hung.

**Decision:** Take the archive apart before deleting it. Step 12 now runs three named passes:

1. **Deleting the archive contents** — `DeleteFolder` per chunk folder. A folder delete leaves **one bin entry
   per folder**, which is the whole mechanism: it converts one opaque destroy into N countable ones.
2. **Purging the archive contents** — one bin read, then `PurgeRecycleBinItem` per matched entry.
3. **Purging the remaining deleted items** — the existing `DeleteDomain` + `DeletePath` sweep, now over a
   near-empty library plus the Step 11 source folders.

**Chunks are chosen by depth, not folder-by-folder** (`ArchiveChunkPlanner`): the shallowest depth beneath the
archive destination holding at least `ArchivePurgeChunkTarget` folders (default 25), preferring a shallower level over one
that would exceed 1000 pieces (a preference, not a ceiling — if the shallowest depth itself overshoots there is
nothing coarser than the whole library to fall back to). A `DeleteFolder` already takes the folder's whole subtree in one
server-side operation, so the only question is granularity — one chunk per recorded folder would be roughly
2× folder count in extra round-trips (over two thousand on a NATA-sized run) to say what a few hundred chunks
already say. Taking every chunk at **one** depth is what makes them non-nesting: no chunk contains another, so
the deletes are order-independent, no bin entry nests inside another, and concurrency is safe by construction.

The plan is drawn from the run's own `CleanupRunArchiveFolder` records — no live walk of the tree — which is
affordable precisely because **chunking is an optimisation and never the guarantee**. A folder that was never
recorded, a delete MAGIQ rejects, a bin shape the matcher does not recognise, a bin that cannot be read: all of
it is still inside the library when `DeleteDomain` runs and still swept up by the `DeletePath` match behind it.
Nothing about completeness rests on the plan being right.

**The one new hazard, and its guard.** A chunk purge that goes **indeterminate** (sent, no answer, still in the
bin) is still under the library's `DeletePath`, so pass 3 would match it and fire a second destroy at a service
that may still be working through the first — the precise mistake [2026-08-17] exists to prevent. Such items
are therefore **barred** from later passes, keyed on (delete path, name) rather than handle, and left as
recorded failures.

**Two things deliberately left alone, both raised in review.** The chunk `DeleteFolder` keeps the *standard*
SOAP policy rather than the destructive one: a large recursive delete can outlive the 100s budget and be
retried, but a `DeleteFolder` is a **soft** delete, so a retry that lands on an already-moved folder just fails
and falls through to the `DeleteDomain` sweep — nothing is destroyed twice, which is the only thing the
destructive policy exists to prevent. Worth revisiting if the retries prove noisy in the field. And
`MaximumChunks` is a preference rather than a hard cap, because enforcing one would mean chunking part of a
level and leaving the rest to the library, which is a more confusing shape than simply taking a wide level as
it stands.

Concurrency > 1 also required serialising the **audit writes**: `CleanupRunOperationStore` computes `Seq` as
`MAX(Seq) + 1` per run and documents that it relies on a phase being single-threaded per run — these passes are
the first code that could break that, and the index is not unique, so a race would have corrupted the trail's
ordering, its paging and `ArchivePurge`'s attempt boundary silently. The SOAP calls stay parallel; only the
write is queued (`_auditGate`).

**Sequential by default.** `ArchivePurgeConcurrency` (default 1, max 8) is an operator dial, not a new default:
simultaneous destroys against one MAGIQ instance are unverified, and the service was already timing out on a
single one. Chase chose this explicitly over bounded parallelism.

**Rationale for accepting the cost.** Chunking is strictly *more* work — the same rows destroyed, plus ~2N
round-trips. Chase's framing was "this may take longer but visibility will be better", and there are two things
bought beyond visibility: the destruction becomes **resumable in fact** (a pass that stops has already finished
the chunks it got through, each individually audited), and each purge call is bounded by a chunk rather than a
library, which is the shape that blew the timeout budget in the first place.

**Side effects.** The purged-document record's grain improves from one library-level confirmation to one per
archive folder — still not per document, and `ExportPurgedDocumentsHandler`/`ArchivePurge` say so in the same
words as before, adjusted. Chunk deletes are audited with a **null phase**, which is what keeps them out of
`DeletedSourceFolders` (`Cleanup`-phase only) and so out of the deleted folder manifest.

**Found and fixed en route:** the rollback teardown matched bin items against its recorded archive folders by
raw string — a recorded path is `Archive/2019/Case`, a reconstructed bin path is `\Archive\2019/Case`, so it
matched **nothing** and every rollback left its archive folders sitting in the recycle bin. Both sides now fold
through `ArchiveChunkPlanner.Key`. Worth noting that no test caught this because the rollback tests exercised
the delete half, not the match.

**Status:** Implemented in the product working tree (uncommitted). API: new `Pipeline/ArchiveChunkPlanner.cs`;
`Pipeline/ArchiveLibraryTeardown.cs` (chunk passes, `PurgeItemsAsync` extracted, `PurgeTally`, pass callbacks,
`ISystemSettings` injected); `Pipeline/RunPhaseExecutor.cs` (wiring + the rollback matcher fix);
`Hubs/Messages/RunOperations.cs` (two new pass names; `PurgingRecycleBin` reworded so it does not repeat the
step's own label); `Configuration/Settings/*` (`ArchivePurgeChunkTarget`, `ArchivePurgeConcurrency`);
`ExportPurgedDocuments`/`ArchivePurge` doc corrections. SPA: `admin/settingsEditing.tsx` (an *Archive purge*
section). Tests: new `ArchiveChunkPlannerTests`, five new teardown tests, `FakeArchiveLibraryTeardown` and the
teardown test double updated. `npx tsc -b` clean; **the C# is inspection-verified only — no .NET SDK in the
authoring environment, so it still needs `dotnet build` + `dotnet test`.** Spec rev 43.

---

## [2026-08-18] SPA design system — refined slate and deep indigo

**Context:** The SPA's whole visual identity was thirty-five lines: a mid-blue Mantine colour tuple, a system
font stack, `defaultRadius: 'md'`, and heading weight 600. Everything else was Mantine's out-of-the-box
appearance. That was the right call while the pipeline was being built — no time was spent on chrome that the
behaviour hadn't earned yet — but the tool now ships to a customer, and the screen an operator sits in front of
while irreversibly destroying a document library looked like an untouched component-library demo.

Chase asked for a more premium, corporate and contemporary design, scoped deliberately: **the theme layer plus
the shared primitives every screen flows through**, not a sweep of all thirty components. That scope is the
decision underneath the visual one — it is chosen so the ~25 panels that were laid out carefully over specs
rev 26/37/38/39 inherit the new surface *without being re-laid-out*, because those layouts were argued for on
their own merits and re-opening them here would mean re-litigating them for aesthetic reasons.

**Decision:** A **refined slate + deep indigo** system, expressed in two files and applied through component
defaults.

1. **Ramps re-cut to Mantine's index semantics, not lifted from a palette.** `gray` (slate) and `dark`
   (graphite) keep Mantine's *lightness distribution* — five light stops before the first mid-tone — because
   Mantine derives specific things from specific indices: `gray-4` is every border in the app, `gray-6` is
   every `c="dimmed"`, `dark-6`/`dark-7` are the surface/canvas pair. Dropping in an evenly-spaced modern
   ramp (Tailwind `slate`, say) puts a 400-level grey at index 4 and turns every hairline into a drawn line.
   Contrast was the second constraint: Mantine's stock `gray-6` dimmed text is ~3.5:1, and roughly half the
   words in this app are dimmed — the new stop is 4.6:1, and dark-scheme dimmed is 6.3:1.

2. **Brand moves from mid-blue to deep indigo**, and `Running` moves from `'blue'` to `'brand'`
   (`theme/status.ts`). With an indigo brand, a separate mid-blue status hue was a near-duplicate colour
   carrying a different meaning; and "the app's own colour" is the right reading for "the app is doing the
   thing you asked it to". The remaining status hues (`red`, `orange`→amber, `teal`, `green`) are re-cut
   deeper and less saturated — Open Color is bright and friendly, which is wrong next to a typed confirmation
   that destroys a library.

3. **A canvas/surface relationship, applied to `AppShell.Main` rather than to `--mantine-color-body`.**
   Mantine's light scheme paints white cards onto a white page, so a card is visible only by its border. The
   page gets a faint slate tint and surfaces stay white. It is scoped to the shell's main region on purpose:
   `Paper` derives its background from `--mantine-color-body`, so tinting that would tint the cards too and
   lose precisely the contrast this is for.

4. **Component defaults carry the redesign to the untouched screens.** Radius, weight, casing and density are
   set once per component in `theme.ts`; anything a component passes explicitly still wins, which is why no
   panel had to change to pick this up. The one default with a visible semantic edge is **Badge sentence
   case** — badges here carry content ("Awaiting input", "Deferred", "Planned name changes"), and uppercasing
   a phrase costs room, loses the word shapes that make it scannable, and reads as shouting on a screen where
   the loud things should be the failures. Several callers already passed `tt="none"` one at a time.

5. **`theme/tokens.css` for what the theme object cannot express** — the canvas/chrome/surface tokens, the
   two-layer elevation recipe, table-header type, scrollbars, and the `.dlc-*` utilities.

**Rationale for the two placements that look arbitrary.** Table-header styling lives in `tokens.css` and *not*
in `theme.components.Table.styles` because Mantine emits theme `styles` as **inline** styles, and
`text-transform`/`color` inherit into whatever a header wraps its label in — the audit trail's sortable headers
nest a `Text` that re-declares `font-size` but not those two, so an inline rule left five headers
uppercase-and-dimmed at 14px beside their plain neighbours at 11px. A stylesheet rule can normalise the nested
element back; an inline one cannot be reached. And the `--dlc-*` tokens are seeded on `:root` as well as under
each `[data-mantine-color-scheme]` block, because the provider writes that attribute after hydration and until
it does, a variable guarded by it resolves to nothing — the first painted frame would lose its canvas and every
hairline.

**Four regressions found in review and fixed before this entry was written**, all worth recording because each
is a trap the next visual change can fall into:

- **The app's only `<h1>` vanished on a phone.** The wordmark was hidden below `xs` with Mantine's
  `visibleFrom`, which is `display: none` — it removes the element from the accessibility tree, and the mark
  beside it is `aria-hidden`. Now hidden *visually* via `.dlc-optical-from-xs` and still announced.
- **Every `Paper` was the canvas colour in dark mode.** Mantine paints `Card` from `dark-6` but `Paper` from
  `--mantine-color-body` (= `dark-7`, = the canvas), so the runs table, the metric tiles and the sign-in card
  had no figure/ground separation at all — invisible in light, where both are white. `Paper` is lifted onto
  the card surface, excluding any that sets its own background.
- **The row-hover brand rail never rendered.** A `box-shadow` on a `<tr>` is not painted under
  `border-collapse: collapse`, which is how Mantine's tables are built. Moved to the first cell.
- **The purge/rollback-era `indigo`** used for the *Archived documents* register row is now the brand hue, so
  that row read as promoted rather than as one file among several. Changed to `blue`.

**Deliberately not done.** The remaining Open Color hues used as *labels* (`blue`, `cyan`, `violet`, `grape` on
the register rows and the folder/document distinction) were left un-recut: they appear only as 10% tints with
shade-6 text, and five more hand-tuned ramps is five more chances to get a contrast pair wrong with no visual
feedback available in the authoring environment. Worth a follow-up pass with the app actually running.
`SectionCard` was restyled and given `meta`/`actions` slots but **has no call sites** — it is dead code that
predates the panels, and adopting it across them is a layout change, which this deliberately is not.

**Status:** Implemented in the product working tree (uncommitted). New: `theme/tokens.css`. Changed:
`theme/theme.ts` (the design system), `theme/status.ts` (`Running` → `brand`), `main.tsx` (stylesheet order),
`App.tsx` (header lockup, grouped nav, content measure), `components/{SectionCard,PageHeader,StatusBadge,
ColorSchemeToggle}.tsx`, `pages/{LoginPage,JobsDashboard,FirstRunSetupPage,JobDetailsView}.tsx`,
`admin/settingsEditing.tsx`. `npx tsc -b`
clean and both stylesheets parse; **`npm run build` has not been run — the authoring environment's
`node_modules` is a Windows install, so Rollup's Linux binary is absent.** No API change, no spec change: this
alters no behaviour the spec describes.

**Follow-up from Chase's first look at the built app (same unit of work).** On System settings, the integer
settings' descriptions wrapped into a narrow column while the text settings beside them ran full width: the
`NumberInput` carried `w={240}`, which sizes the wrapper's *root* — label and description included — not the
input. Narrowed via `styles={{ wrapper: … }}` instead, so a number box stays small and the prose explaining it
does not. No other fixed-width input in the app carries a description, so this was the only instance.

Field descriptions are then left **uncapped**, at Chase's call — an interim `68ch` measure cap was reverted
(and removed from `SectionCard` with it). A cap there would have been the odd one out: the card and section
descriptions immediately above these already run the full width of their container, so capping only the
field-level ones ragged the right edge of a settings page against itself. The page measure is the container's
job — `.dlc-content` holds it to 1440px — not each block of prose capping itself.

**Section headings, same unit of work.** Chase asked for them to stand out more. The cause was in the type
scale, not on any page: **`h5` is the app's card heading** — twelve panels use `Title order={3} size="h5"` —
and Mantine's 15px put it one pixel above the 14px body text beneath it, so the only thing separating a section
title from its own description was weight. Raised to **17px**, giving a legible ladder of page 24 / section 17 /
body 14; h3/h4/h6 moved only to keep the scale monotonic. One change, all twelve panels.

The two admin pages were a second, separate problem: their section titles were not headings at all but
`<Text fw={600}>`, so they were invisible to the type scale *and* to the document outline. Both now use the
shared **`SectionCard`**, which had been written with exactly the `title`/`description`/`meta` slots they needed
and had **zero call sites** — noted as dead code in the entry above, now retired by its first real use. The
"Unsaved"/"N unsaved" badge moves from hard-right to beside the title: it describes the section rather than
acting on it, which is what `meta` is for.

**Second pass on the same complaint — weight, not size.** 17px was "better but not very distinct". Size was
never going to be enough on its own: this app is full of 500- and 600-weight text (input labels, table figures,
`Text fw={500}` captions, badge labels), so a 600-weight heading was the same colour and nearly the same weight
as half the page and only its size said "heading". `headings.fontWeight` goes to **700** — the step that
separates a heading from everything merely emphasised — with `h5` nudged to 18px and the scale re-spaced to
even 2px steps (h3 22 / h4 20 / h5 18). Bold is affordable here precisely because a heading is about six words
per card.

---

## [2026-08-19] Four defects behind a failing suite — and the three tests that were simply out of date

Eight failing tests. Five root causes, three of them behaviours the spec already claimed and nobody had
checked. Recorded together because the pattern is the point: every one of these was a *documented* behaviour
that the code had quietly stopped exhibiting, and in three cases the only reason it surfaced was that
somebody re-ran a suite.

**1. The acronym pre-select cascade stopped at a protected folder — the 92%-left-behind defect, back.**
`CandidateFolderBuilder.ResolveSelectedIds` skipped the DFS at its **root** when that root was in
`protectedIds`. Rule 2 protection propagates **upward**, so one post-cutoff document anywhere beneath a
matched case folder marks the matched folder protected too — which meant a single recent document in
`2) Report Package` silently un-selected the whole of `60912 SRV 2016`, the exact failure the cascade was
added to fix. The per-node guard inside the walk, written specifically to *continue through* a protected
node, was unreachable dead code as a result.

The root-level clause is gone. Nothing about safety changes: the protected folder is still withheld by the
per-node guard, and `Build` independently re-checks `!isProtected` when computing `IsSelectedForDeletion`.
Two checks already covered "never select a protected folder"; the third was doing something else entirely —
it was deciding *whether to walk*, which is not the same question. Worth naming, because the class doc,
`dev-spec.md` and the spec all described the corrected behaviour and had done since 2026-08-14; only the
code disagreed, and `dev-spec.md`'s own sentence contradicted itself mid-paragraph ("from every self-matched,
**non-protected** folder … traversal continues through a protected node"), which is probably how it survived
review.

**2. No CSV the tool produces has ever carried a UTF-8 BOM.** All three writers do
`new UTF8Encoding(true).GetBytes(text)`. `encoderShouldEmitUTF8Identifier` only affects `GetPreamble()` and
`StreamWriter` — `GetBytes` never emits the preamble. So the flag reads as "with BOM", the comment beside it
says "so Excel detects the encoding", the endpoint table in `dev-spec.md` promises "UTF-8 BOM, RFC 4180" for
five endpoints, and the byte was never there. Excel therefore read every non-ASCII folder name as mojibake —
on a tool whose Step 8 exists *because* those names carry non-ASCII whitespace.

Fixed in all three (`RunOperationsCsvWriter`, `RegisterCsvWriter`, `CsvText.ToBytes`) by prepending
`GetPreamble()`. The reason it went unnoticed for so long is instructive: every test that reads these files
does `GetString(bytes).TrimStart('﻿')` — stripping a BOM that was never present, and passing either way.
One test asserted the bytes directly, and it was the only one that failed. Each writer now has a byte-level
assertion of its own.

**3. A guard refusal reached through the retry was still a red `Failed` row.** Rev 30 reclassified the Step 11
pre-delete guard refusal as `Deferred` — reason in `Detail`, no `ItemFailed` — in `DeleteEmptyFoldersAsync`
only. `RetryFolderDeletesInlineAsync` kept writing `Failed` with the reason in `ErrorMessage`, and the prune
cycle calls it automatically on every pass, so the rows rev 30 set out to remove reappeared on any run with a
blocked folder. Now classified identically in both. The related exemption — a guard refusal must not drag the
parent through relax → retry → restore — was already shared, because it lives in `RunFolderGroupAsync`; only
the audit shape had been duplicated, which is why only the audit shape drifted.

**4. The prune's auto-skip is narrower than the spec said — and stays narrow (Chase's call).**
`AutoSkipUnresolvableFoldersAsync` settles only plans where `!ResolvesFolder`. A plan that *claimed* it could
resolve a folder and then failed to — because a delete it planned was itself guard-refused over a descendant
the subtree query never knew about — leaves the folder `Failed`. The spec said flatly "no retry will ever
succeed, so it is set to `Skipped`", which is true of the proved case and false of this one: deal with the
unknown descendant and the retry succeeds.

Left as `Failed`, spec corrected to match. `Failed` is what keeps a folder in the Folder cleanup failures
panel with **Retry**, **What's in it?** and the on-demand prune; `Skipped` is terminal and takes all three
away. Auto-skipping on a *claim* that didn't hold would close the door on the one folder still worth a look —
tidier run summary, worse outcome. The rejected alternative was to widen the auto-skip; a middle option
(escalate only if a later cycle repeats the same claimed-then-failed result) was declined as needing
per-folder cycle tracking that doesn't exist for a case that resolves itself once someone looks at it.

**The other three failures were stale tests, not defects.** Two had been written against the always-restore
shape of the rule guard and predate [2026-08-14]'s "when the delete succeeded there is nothing to put back"
— one asserted the restore `SetFolderRules` call, the other the fake's residual rule state for a folder that
no longer exists. Both now assert the `RuleRestore` audit row carrying `not-required-folder-deleted`, which
is the actual contract and survives the SOAP call not happening. The third asserted a `Failed` outcome rev 30
had already changed to `Deferred`, duplicating a test written for rev 30 three files away. A fourth was not
stale but malformed: `LastChildrenCall` is a 3-tuple and the assertion passed a 2-tuple, and a
`BeEquivalentTo` over an `IEnumerable<object?>` projection bound to the `char` overload, comparing two paths
against the 27 characters of the first one. Both were assertions that could never pass, in tests whose
subject matter was fine.

**Verification.** Inspection only — no .NET SDK in the authoring environment. Needs `dotnet build` +
`dotnet test` before this goes near a branch. The CandidateFolderBuilder change is the one to look at hardest:
it widens what a run pre-selects for deletion, which is the correct behaviour and also the highest-consequence
of the four.

---

## [2026-08-19] A missing Docker engine is a skip, not three failures

The three `ApiSmokeTests` are the only Docker-dependent tests in the suite — the only class carrying
`[Trait("Category", "Integration")]`, the only one using Testcontainers. They share one class fixture that
starts a SQL Server container in `InitializeAsync`, so with Docker stopped that start throws before any HTTP
request is made and **all three go red together**, including the anonymous health ping that touches nothing.
Three failures, none of them about the code.

`ApiFactory`'s own doc comment already gave the workaround — `dotnet test --filter Category!=Integration` —
which is the wrong shape of fix: it asks every developer to remember a flag, forever, and the cost of
forgetting is a suite that looks broken. Red has to mean *something is broken*. "You didn't start Docker" is
not that, and a suite that cries wolf stops being read — which is how the four real defects in the entry
above sat unnoticed behind a wall of expected-red.

So: a `DockerFactAttribute` (a `FactAttribute` subclass setting `Skip` from a one-off probe) on the three
tests, and `ApiFactory` **builds and starts its container behind the same probe**. Both halves are needed,
for reasons that only show up when you trace xUnit's lifecycle: a class fixture is constructed and
initialized *even when every test in the class is skipped* (`XunitTestClassRunner.AfterTestClassStartingAsync`
has no skip short-circuit), so the container work had to come off that path or it would still throw. And the
container was a **field initializer**, which runs in the constructor where no guard can reach it —
`MsSqlBuilder.Build()` resolves a Docker endpoint eagerly and throws *"Docker is either not running or
misconfigured"* right there. It is now built inside `InitializeAsync`, after the check, and fielded before
`StartAsync` so a container that fails to start is still torn down.

**The probe is a cheap endpoint check, not a real ping.** On Windows, enumerate the pipe filesystem for a
pipe whose name contains `docker` and ends in `engine` (not the default `docker_engine` alone — a Desktop
exposing only `dockerDesktopLinuxEngine` would otherwise read as stopped); elsewhere `/var/run/docker.sock`
or the rootless socket under `XDG_RUNTIME_DIR`; and if `DOCKER_HOST` is set, assume the operator means it
and let Testcontainers do the talking. Every one of those choices leans the same way — **a false skip is
silent and a false failure is loud**, so where the probe is unsure it says available. Rejected: `Docker.DotNet`'s `System.PingAsync`, which is only a
transitive of Testcontainers (depending on a transitive is how you get a surprise at the next upgrade) and
costs a multi-second timeout on every run of the whole suite. Rejected: adding `Xunit.SkippableFact` — a
package for a fifteen-line attribute. The pipe exists only while the engine is running, which is exactly the
distinction worth drawing: Docker Desktop installed but stopped reads as unavailable.

**A probe that throws reports "available".** Deliberately the fail-*open* direction here: the cost of being
wrong that way is one honest failure, and the cost of being wrong the other way is a test that silently never
runs. A skip guard that can hide a real failure is worse than no skip guard.

**Also, from the same suite run:** `MagiqFolderBrowseQueries.EscapeLike` escapes `\`, `%`, `_` and `[` — a
test expected `]` escaped too, and the test was wrong. `]` is special only as the terminator of a bracket
expression, so escaping the `[` means one is never opened and a bare `]` is already literal. SQL Server
tolerates `\]` after an `ESCAPE` character, so both patterns work; the minimum is the one to write, because
it is the one that reads correctly in a query plan. Test corrected, and the production comment (which said
"the three characters" while escaping four) now says which four and why `]` is not among them. `dev-spec.md`
now documents the escaping on the endpoint row, since it is a contract an operator-customised query has to
keep.
