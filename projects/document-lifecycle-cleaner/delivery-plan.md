# Epic 34120 — Branch & Delivery Plan

_Document Lifecycle Cleaner — NATA. ADO project **Documents**, repo **DocumentLifecycleCleaner**._
_One branch per User Story; tasks under a story are commits within its branch. Branch naming `feature/{storyId}-{slug}` (matches the live `feature/34129-scaffold-api-spa-host`). Chase creates branches + commits; Claude designs and works inside._
_Generated 2026-07-23 from the live work-item tree._

> **Historical record — as-built numbering.** This plan describes Epic 34120 as it was delivered; its step numbers are the **as-built** ones (Archival Steps 8–9, Cleanup 10–12) and are left unchanged. The later **Name Normalization** phase (`decisions/log.md` [2026-08-05]) inserts a new **Step 8** and renumbers the spec (Archival → 9–10, Cleanup → 11–12); it is a **future branch**, not yet planned in ADO — see `tasks.md` → "Name Normalization phase" and the spec. When that story is cut, add its branch below rather than renumbering the rows above.

---

## The tree (8 Features · 17 Stories · 49 Tasks)

| Feature | Stories |
|---|---|
| **34121** Platform & Solution Foundation | 34129 scaffold · 34130 dual hosting · 34131 app DB + Hangfire |
| **34122** MAGIQ Documents Integration | 34132 SOAP client · 34133 Dapper + query store |
| **34123** Authentication & Authorisation | 34134 login (two tickets) · 34135 durable process ticket · 34136 admin allowlist |
| **34124** Cleanup Run Orchestration & Progress | 34137 CleanupRun state machine · 34138 live progress |
| **34125** Identification & Candidate Analysis | 34139 identify docs + export · 34140 candidate folders + protection |
| **34126** Review, Selection & Confirmation | 34141 review & select · 34142 confirm + delete-constraint |
| **34127** Archival, Cleanup & Purge | 34143 create archive + move · 34144 delete empty + purge |
| **34128** Deployment & Documentation | 34145 deployment + operator docs |

Only 34129 is **In Progress** (its 4 tasks too); all others **New** (as of 2026-07-23).

---

## Critical path (build order)

```
34129 scaffold ─▶ 34131 app-db+hangfire ─▶ 34132 soap ─▶ 34134 login ─▶ 34137 cleanuprun-sm
   ─▶ 34133 dapper ─▶ 34139 identify ─▶ 34140 folders ─▶ 34141 review ─▶ 34142 confirm
   ─▶ 34143 archive+move ─▶ 34144 cleanup+purge ─▶ 34145 docs
```

**Off the critical path (slot in when convenient):** 34130 dual-hosting (any time after scaffold), 34136 admin-allowlist (after 34134), 34135 durable-ticket (after 34137), 34138 progress-SignalR (after 34137, before 34143 for move UX).

---

## Recommended sequence

Executable one-at-a-time (Chase creates → Claude builds → Chase commits loop). Each row: the branch to cut, what it closes, and what must exist first.

| # | Branch | Closes (Story ▸ Tasks) | Depends on |
|---|--------|------------------------|-----------|
| 0 | `feature/34129-scaffold-api-spa-host` *(in progress)* | 34129 ▸ 34146–34149 | — |
| 1 | `feature/34131-app-db-and-hangfire` | 34131 ▸ 34153–34155 | 34129 |
| 2 | `feature/34132-soap-client-srv-asmx` | 34132 ▸ 34156–34158 | 34129 |
| 3 | `feature/34134-auth-login-two-ticket` | 34134 ▸ 34162–34164 | 34132 |
| 4 | `feature/34136-admin-allowlist-authz` | 34136 ▸ 34168–34169 | 34134 |
| 5 | `feature/34137-cleanuprun-state-machine` | 34137 ▸ 34170–34173 | 34131, 34134 |
| 6 | `feature/34135-durable-process-ticket` | 34135 ▸ 34165–34167 | 34137 |
| 7 | `feature/34133-dapper-configurable-query-store` | 34133 ▸ 34159–34161 | 34129 *(parallel w/ 2)* |
| 8 | `feature/34138-progress-reporting-signalr` | 34138 ▸ 34174–34176 | 34137 |
| 9 | `feature/34139-identify-candidates-export` | 34139 ▸ 34177–34179 | 34133, 34137 |
| 10 | `feature/34140-candidate-folders-protection` | 34140 ▸ 34180–34182 | 34139 |
| 11 | `feature/34141-review-selection-ui` | 34141 ▸ 34183–34185 | 34140, 34134 |
| 12 | `feature/34142-confirm-delete-constraint` | 34142 ▸ 34186–34187 | 34141 |
| 13 | `feature/34143-archival-create-move` | 34143 ▸ 34188–34190 | 34132, 34142, 34138 |
| 14 | `feature/34144-cleanup-delete-purge` | 34144 ▸ 34191–34192 | 34143 |
| 15 | `feature/34130-dual-hosting-iis-docker` | 34130 ▸ 34150–34152 | 34129 *(flex — recommend early)* |
| 16 | `feature/34145-deployment-operator-docs` | 34145 ▸ 34193–34194 | all feature work |

---

## Per-branch scope

### 1 · `feature/34131-app-db-and-hangfire` — the persistence spine
Closes **34131** (▸ 34153 provision app DB + schema baseline, 34154 Hangfire storage + in-process server, 34155 secure Hangfire dashboard admin-only).
- App DB connection (`AppDatabase`), migration/baseline for `CleanupRun*` tables (schema in `dev-spec.md`), Hangfire schema in the same DB, `WorkerCount = 1`, dashboard behind the admin gate.
- **Touches:** `Program.cs` (Hangfire + DB registration), `Configuration/` (`ConnectionStringsOptions`, `HangfireOptions`), a `Persistence/` area, migration scripts.
- **Packages (add to `Directory.Packages.props`):** `Microsoft.Data.SqlClient`, `Hangfire.AspNetCore`, `Hangfire.SqlServer`. Dashboard auth ties to 34136 — until then, lock it to Development or a temporary filter.
- ⚠ **Sub-decision:** app-DB access tech (Dapper vs EF Core vs a thin repo). Recommend **Dapper** for consistency with the MAGIQ path and the "no ORM assumptions" grain — flag an ADR when we start.

### 2 · `feature/34132-soap-client-srv-asmx` — MAGIQ SOAP primitive
Closes **34132** (▸ 34156 `srv.asmx` client wrapper, 34157 `AuthenticateUser` → `AuthenticationTicket`, 34158 configurable endpoint + timeouts/retries).
- Typed SOAP client; **must check the `success` attribute, not HTTP status** (SOAP always returns 200). `AuthenticateUser` returns a fresh independent ticket per call (the two-ticket foundation).
- **Touches:** `Integration/Magiq/Soap/` client + response contracts, `Configuration/MagiqDocumentsOptions`.
- **Packages:** `System.ServiceModel.Http` + `System.ServiceModel.Primitives` (WCF client) *or* pure `HttpClient` — ADR-004 allows either. Recommend the typed WCF proxy if the WSDL is clean, else HttpClient.

### 3 · `feature/34134-auth-login-two-ticket`
Closes **34134** (▸ 34162 two-call login → UI + process tickets, 34163 React login/logout + session, 34164 end UI ticket on logout without touching the process ticket).
- `POST /api/auth/login` calls `AuthenticateUser` ×2; UI ticket in-memory, process ticket held for run creation; session token to the SPA. **First command-bearing slice** → this branch introduces the shared `Result<T>` + `DlcEndpoint` base (ADR-009) unless 34137 lands first.
- **Touches:** `Features/Auth/`, `ICurrentOperator` scoped service + session store, React `LoginPage` + auth context.

### 4 · `feature/34136-admin-allowlist-authz`
Closes **34136** (▸ 34168 allowlist from `appSettings.json`, 34169 enforce on API + UI routing).
- Authenticated-but-not-allowlisted → denied. Applies the gate globally; also secures the Hangfire dashboard from step 1.
- **Touches:** auth policy in `Program.cs`, `MagiqDocumentsOptions.AdminAllowlist`, SPA route guards.

### 5 · `feature/34137-cleanuprun-state-machine` — orchestration spine
Closes **34137** (▸ 34170 model + persist `CleanupRun`, 34171 single-active-run, 34172 run initiation + Hangfire continuation chaining, 34173 resume from last completed phase on startup).
- `POST /api/runs` (201 / **409 RunAlreadyActive**), status/phase/step transitions, phase continuations chained (stub phase bodies for now), startup resume. Persists the process ticket onto the run.
- **Touches:** `Features/Runs/`, `Domain/CleanupRun`, `Persistence/` repositories, Hangfire job entry points.

### 6 · `feature/34135-durable-process-ticket`
Closes **34135** (▸ 34165 persist process ticket in app DB, 34166 keep-alive heartbeat, 34167 reload + resume heartbeat on startup).
- `CleanupRun.ProcessTicket` persistence, heartbeat service (`TicketHeartbeat.IntervalSeconds`, default 300), startup reload. Expiry-recovery path per ADR-006.
- **Touches:** heartbeat hosted service, run repository, `Configuration/TicketHeartbeatOptions`.

### 7 · `feature/34133-dapper-configurable-query-store`
Closes **34133** (▸ 34159 Dapper connection + query executor, 34160 configurable query store, 34161 parameterise + map).
- Executes the three system-configurable queries against `MagiqDocumentsDatabase`, untouched (no ORM model). Parameterised (`@specifiedDate`, `@folderIds`).
- **Touches:** `Integration/Magiq/Sql/`, `Configuration/QueriesOptions`. **Packages:** `Dapper` (+ `Microsoft.Data.SqlClient` if not already in from step 1). Independent of SOAP — can run parallel to step 2.

### 8 · `feature/34138-progress-reporting-signalr`
Closes **34138** (▸ 34174 hub + progress contract, 34175 Hangfire→progress integration, 34176 React client + polling fallback).
- Hub `/hubs/run-progress`, `run:{runId}` groups, the 5 server→client messages from `dev-spec.md`, per-batch `ProgressUpdated`. SignalR is built into ASP.NET Core (no server package).
- **Touches:** `Hubs/`, progress emitter used by phases, React progress client (`@microsoft/signalr` via npm).

### 9 · `feature/34139-identify-candidates-export` — Phase 1, Steps 1–3
Closes **34139** (▸ 34177 candidate docs (Step 1), 34178 Document Register (Step 2), 34179 Excel export + download (Step 3)).
- Runs the configured queries via Dapper, populates `CleanupRunDocument`, Excel export for viewing (no retention).
- **Touches:** Phase 1 Hangfire handler, `Features/Runs/...`, export endpoint. **Package:** `ClosedXML` (recommended) for the xlsx.

### 10 · `feature/34140-candidate-folders-protection` — Phase 1, Steps 4–5
Closes **34140** (▸ 34180 candidate folder list (Step 4), 34181 **full-ancestor protection** (Rule 2), 34182 folder-path SQL (Step 5)).
- Derive folders, mark `IsLocked` per acronym (contains, case-sensitive), apply full-ancestor protection, resolve paths. Populates `CleanupRunFolder`.
- **Touches:** Phase 1 handler continuation, protection logic, `Configuration/DeletableFolderAcronyms`.

### 11 · `feature/34141-review-selection-ui` — Step 6
Closes **34141** (▸ 34183 review UI + API, 34184 acronym pre-lock, 34185 capture selection/retention).
- `GET/PUT /api/runs/{id}/folders`, virtual-scroll folder table, locked rows non-deselectable (**422 FolderIsLocked**), columns: path, doc count, folder count, size.
- **Touches:** `Features/Folders/`, React `SetupWizard/Step6FolderReview`.

### 12 · `feature/34142-confirm-delete-constraint` — Step 7
Closes **34142** (▸ 34186 confirmation screen, 34187 **delete-constraint validation (Rule 4)** + blocker reporting).
- `POST /api/runs/{id}/confirm`, **422 FolderValidationFailed** with blocked-folder list, auto-proceed-with-purge checkbox, archive-library selection (Step 8 modal).
- **Touches:** `Features/Folders/confirm`, `Features/Libraries/`, React `Step7ConfirmDeletions` + `Step8ArchiveLibraryModal`.

### 13 · `feature/34143-archival-create-move` — Steps 8–9
Closes **34143** (▸ 34188 archive library create/reuse (Step 8), 34189 document move (Step 9), 34190 identify-skip-resume).
- SOAP `CreateDomain`/`Move`, batched move with per-doc status, **retry loop + resume from failure** (no rollback), progress via 34138.
- **Touches:** Phase 3 Hangfire handlers, `CleanupRunDocument` retry logic, SOAP ops.

### 14 · `feature/34144-cleanup-delete-purge` — Steps 10–12
Closes **34144** (▸ 34191 empty-folder deletion gated on move completion (Step 10), 34192 archive delete + background purge (Step 12)).
- `DeleteFolder` gated on Step 9 complete; **purge** = `DeleteDomain` + recycle-bin drain, typed `"permanently delete"` confirm (**422 ConfirmationRequired**), Path A auto / Path B manual.
- **Touches:** Phase 3 continuation, `POST /api/runs/{id}/purge`, `PurgePanel`/`PurgeConfirmModal`.

### 15 · `feature/34130-dual-hosting-iis-docker` *(flex — recommend early)*
Closes **34130** (▸ 34150 multi-stage Linux Dockerfile, 34151 IIS in-process publish profile / web.config, 34152 env-var/config docs).
- Publish-time `npm ci && npm run build` into `wwwroot` (the hook the scaffold csproj defers to this story), Dockerfile, web.config, config-key reference. No host-specific code.
- **Note:** non-blocking, but doing it right after scaffold locks the deployable shape every later slice ships in — worth pulling forward if you want CI building the SPA sooner.

### 16 · `feature/34145-deployment-operator-docs` — last
Closes **34145** (▸ 34193 IIS + Docker runbook + config reference, 34194 operator runbook + README).
- Docs only; lands once behaviour is stable.

---

## Notes for the loop
- **Linking:** each PR links its **Story** (task roll-up follows); reference task IDs in commit messages (`#34153`). Keep the `document-lifecycle-cleaner` tag + the per-story `feat/…`·`infra/…`·`chore/…` tag already on each item.
- **Shared abstractions** (`Result<T>`, `DlcEndpoint<TReq,TRes>`) land in whichever of **34134**/**34137** we start first, per ADR-009.
- **Two open sub-decisions** to settle when we hit them: app-DB access tech (step 1) and SOAP consumption style (step 2). Draft an ADR for each at that point.
- **Parallelism** if two branches ever run at once: {34132 SOAP} ∥ {34133 Dapper} are independent; {34130 hosting} and {34136 allowlist} are low-coupling fillers.
