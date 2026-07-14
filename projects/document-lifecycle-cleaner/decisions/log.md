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
