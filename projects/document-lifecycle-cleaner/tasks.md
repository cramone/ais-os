# Tasks — Epic 34120 delivery status

_Living status tracker. Full branch design + per-branch scope in `delivery-plan.md`._
_Last updated: 2026-08-06._

## Now
- **Name Normalization (Step 8) — implemented; PARKED pending MAGIQ Documents vendor investigation (2026-08-06).**
  The full phase is in the latest code being checked in: the four SOAP rename ops (`GetFolder`/`UpdateFolderProperties`/
  `GetDocument`/`UpdateDocumentProperties`), `RunPhase.Normalization`, `CleanupRunRename` + the `EnteredNormalization`
  audit-lock (spec Rule 7), the pure `RenamePlanner` with current-path addressing + descendant repathing, the operation-audit
  `Rename` rows, and `confirm → normalization → archival` chaining. Steps renumbered so nothing collides: Normalization 8,
  Archival 9–10, Cleanup 11–12. **A bug has been reported to the MAGIQ Documents application developers** about the
  underlying whitespace behaviour — the SOAP service can't `Move`/`CreateFolder` a name containing a double space, and
  addressing an existing doubled item requires the exact doubled path (see `SOAP-VERIFICATION-34525.md` addendum 3). **They
  will investigate whether the service can handle doubled-whitespace names natively or provide an alternative**, which could
  let us **remove the Name Normalization phase** altogether. **Keep the phase in place until they respond; revisit then.**
- **Epic 34120 COMPLETE and merged** (PRs 721–737): pipeline Steps 1–11, SPA, dual IIS/Docker hosting,
  deployment + operator docs. The per-story checklist below is the historical ledger.
- **Deferred pass COMPLETE — all merged.** 34525, 34547, 34550, 34526, 34527 and 34528 are done and
  merged; the deferred/post-MVP backlog is cleared.
- **UI modernization COMPLETE — all merged (2026-07-31).** Migrated the SPA from ad-hoc inline styles to
  **Mantine v9** with a central theme layer (`src/theme/`: colour scale, semantic status-colour map, icon
  registry) — light/dark, mobile-responsive, single-file re-theming. Foundation **34584**, jobs dashboard
  **34585**, job details + progress **34586**, review wizard Steps 6–8 **34587**, polish/a11y **34588**,
  summary metric cards + `GET /runs/summary` **34589** (all Feature 34124, except 34587 under 34126;
  plan: `ui-modernization-plan.md`). Also fixed a lifecycle-action **400** (body-less POST sent as JSON)
  in 34585, and added `GetRunSummaryHandlerTests` + the fake's `GetStatusCountsAsync` in 34589. Safety
  guards (protected-folder delete block, typed "permanently delete" purge gate) preserved verbatim.
- **New story 34566 — source library is now per-run operator input** (Feature 34124; tasks 34567–34570) —
  *merged.* The operator picks the source domain (live `GetDomains` dropdown, all domains + icons) with the
  cutoff date at run creation; persisted on `CleanupRun`, bound as `@sourceDomainId` per run; `MagiqSourceOptions`
  removed. Pre-release migration consolidation: `0002`/`0003` folded back into `0001_baseline.sql` (deleted),
  source columns **NOT NULL**. **Retired the pre-go-live "set @SourceDomainId" blocker** — fresh install needs no scope pre-config.
- **SOAP fully verified (2026-07-30).** Both the 34525 pipeline ops and the two Step 8 ops round-tripped
  against training and reconciled: real op names are **`GetDomains`/`GetFolders`**; `GetFolders` needs the
  four `with*` flags + a domain-rooted, no-leading-slash path; response shapes matched the parsers.
  Findings in `SOAP-VERIFICATION-34525.md` (Part A addendum). Part B (SQL column shapes) superseded by
  `SQL-QUERY-DESIGN-34547.md`. The Step 8 picker shows **all** domains with distinct icons
  (📁 standard / 📦 archive / 🔒 hidden).
- **SQL queries verified against training (2026-07-30).** All four ran against a real MAGIQ Documents DB
  (`verify-magiq-queries.sql`): column shapes, the `LASTUPDATED` cutoff (Q1), null-at-root tree, and the
  `Move`/`DeleteFolder` path format all confirmed. Findings in `SQL-QUERY-DESIGN-34547.md`. **Defect found +
  fixed (committed to main 2026-07-30):** the three path-building queries hit `Msg 451` collation conflict
  (`DOMAINS`/`FOLDERS`/`PUBLICATION` `NAME` collations differ); fixed with `COLLATE DATABASE_DEFAULT` in
  `ConfiguredQueryDefaults.cs` **and** the verify script. A fresh DB re-seeds the corrected SQL; an
  already-seeded `dbo.ConfiguredQuery` must be re-seeded / edited via `/admin/queries`.
- **Pre-go-live remaining:** apply the `FOLDERMAP` index (SQL in product `README.md`); set
  `DeletableFolderAcronyms` to NATA's list; one clean end-to-end live cull on training.
- **34547 spun off design + a new story.** Authored the four MAGIQ queries against the real schema
  (`SQL-QUERY-DESIGN-34547.md`); then, rather than keep SQL in `appsettings.json`, **34550** moved it
  to a DB-backed store with an admin editor and a bound `@sourceDomainId` (decisions/log.md 2026-07-29).
  Both merged.
- **Specified, not yet built — Name Normalization phase (Step 8).** Works around the SOAP double-space
  bug; renumbers the spec to 12 steps and makes a normalized run an audit (spec Rule 7). Full breakdown in
  the "Name Normalization phase" section below; ADO story deferred.

## Active backlog — deferred / post-MVP
Plan + branch/PR breakdown: `deferred-work-plan.md`. ADO stories tagged `deferred-post-mvp`.

- [x] **34525** Verify MAGIQ SOAP integration against training  (Feature 34122; tasks 34529–34532) — *merged (PR 738).* Confirmed the `<response success=…/>` shape; fixed two defects (ticket-attribute login bug in `ReadTicket`; Step 11 purge now matches by `DeletePath` and purges every item). Findings in `decisions/log.md` + `DocumentLifecycleCleaner/SOAP-VERIFICATION-34525.md`.
  - [x] **34547** Part B — confirm the four configurable SQL query column shapes (child of 34525) — *merged.* Four MAGIQ queries authored against the real schema (`SQL-QUERY-DESIGN-34547.md`)
- [x] **34526** Jobs dashboard, new-run form & job details view  (Feature 34124; tasks 34533–34535) — *merged.* New `GET /runs` (paged, single-SQL counts) + `GET /runs/{id}/log`; React jobs dashboard + new-run form + job details view (mounts `RunProgressPanel`, register-download, phase log); retired the App-shell run-id loader.
- [x] **34527** Run recovery & lifecycle actions (Reset/Retry/Cancel/Abandon)  (Feature 34124; tasks 34536–34538) — *merged.* State machine widened (Cancel/Abandon/Retry/Reset/BeginReview); `IRunPipeline.StartCleanup`/`EnqueuePhase`; POST /runs/{id}/cancel|abandon|reset|retry; `CurrentPhase` now flips to `ReviewSelection` at Step 6; UI recovery controls in the job details view.
- [x] **34528** Choose an existing archive library (Step 8)  (Feature 34126; tasks 34539–34540) — *merged.* SOAP `GetDomains`/`GetFolders` (verified vs training); `GET /libraries` + `GET /libraries/folders?path=` (UI-ticket → SOAP, 502 on failure); Step 8 modal "Choose existing" tab — filterable library list with distinct icons (📁 standard / 📦 archive / 🔒 hidden) + one-level subfolder browser, emits `mode:'existing'` (confirm path already accepted it since 34142).
- [x] **34550** Configured query store — DB-backed with admin editor  (Feature 34122; tasks 34551–34555) — *merged.* Moved the four MAGIQ queries out of `appsettings.json` into `dbo.ConfiguredQuery` + an admin `/admin/queries` screen; binds `@sourceDomainId`. Supersedes the appsettings storage (decisions/log.md 2026-07-29).

Recommended order: 34526 → 34527/34528 (independent).

## Branch checklist (recommended order — see delivery-plan.md)
- [x] 34129 scaffold-api-spa-host — *merged (PR 721)*
- [x] 34131 app-db-and-hangfire — *merged (PR 722)*
- [x] 34132 soap-client-srv-asmx — *merged (PR 723)*
- [x] 34133 dapper-configurable-query-store — *merged (PR 724)*
- [x] 34134 auth-login-two-ticket — *merged (PR 725)*
- [x] 34136 admin-allowlist-authz — *merged (PR 726)*
- [x] 34137 cleanuprun-state-machine — *merged (PR 727)*
- [x] 34135 durable-process-ticket — *merged (PR 728)*
- [x] 34138 progress-reporting-signalr — *merged (PR 729)*
- [x] 34139 identify-candidates-export — *merged (PR 730)*
- [x] 34140 candidate-folders-protection — *merged (PR 731)*
- [x] 34141 review-selection-ui — *merged (PR 732)*
- [x] 34142 confirm-delete-constraint — *merged (PR 733)*
- [x] 34143 archival-create-move — *merged (PR 734)*
- [x] 34144 cleanup-delete-purge — *merged (PR 735)*
- [x] 34130 dual-hosting-iis-docker — *merged (PR 736)*
- [x] 34145 deployment-operator-docs — *merged (PR 737)* — closes Epic 34120

## Deferred branch checklist (post-MVP — see deferred-work-plan.md)
- [x] 34525 verify-soap-integration — *merged (PR 738)* — SOAP contracts verified vs training; ticket-attr + purge-by-DeletePath fixes
- [x] 34547 confirm-configurable-sql-query-shapes — *merged* — Part B (SQL), child of 34525
- [x] 34526 jobs-dashboard-run-shell — *merged* — GET /runs + /runs/{id}/log; dashboard, new-run form, job details view
- [x] 34527 run-recovery-lifecycle — *merged* — Cancel/Abandon/Retry/Reset + BeginReview; lifecycle endpoints + UI controls
- [x] 34528 existing-archive-library-picker — *merged* — GetDomains/GetFolders (verified) + /libraries endpoints + Step 8 existing-library picker with type/visibility icons
- [x] 34550 configured-query-store — *merged* — DB-backed queries + admin editor + bound `@sourceDomainId` (branch `feature/34550-configured-query-store`)
- [~] 34575 schema-verification — *code present in tree; confirm branch merged* — on-demand admin `POST /admin/schema/verify`: SchemaOnly-describes each configured query + diffs against code-constant column contracts; Verify-schema button + report on `/admin/queries`. Branch `feature/34575-schema-verification` (tasks 34576–34580, Feature 34122). The **verify UI surface** on `/admin/queries` was restyled and shipped in the 34588 polish merge, so the frontend is in `main`; **Chase to confirm** the 34575 backend branch (the `VerifySchema` endpoint/handler) was merged and `GetSchemaTable` type names were confirmed against training.

- [~] **34590** system-settings-store — *code present in tree; pending Chase's build/PR/merge.* Moves `DeletableFolderAcronyms`, the query command timeout and the ticket-heartbeat interval out of appsettings into `dbo.ConfiguredSetting` (migration `0002`), seeded from `SettingDefinitions`, edited **live** via a new admin **System Settings** page (`GET/GET{key}/PUT{key} /api/v1/admin/settings`). Consumers read live (query executor/probe timeout, `LiveFolderAcronymRule`, heartbeat `Task.Delay` loop); `QueriesOptions`/`TicketHeartbeatOptions` + the appsettings sections deleted. Design → `decisions/log.md` [2026-07-31]. Branch `feature/34590-system-settings-store` (Epic 34120, alongside 34550).

- [~] **34591** abandoned-run-rollback-delete — *code present in tree; pending Chase's build/PR/merge.* Tiered cleanup of terminal (Abandoned/Cancelled) runs: **delete** if nothing changed; **roll back then delete** if only documents were archived (reverse the Step 9 moves + tear down a run-created library); **retain** (no delete) once folders were purged. Effect-based tiers via `CleanupRun.DescribeDeletability`; soft-delete hides from dashboard but keeps audit; rollback is a Hangfire job authorised by the operator's UI ticket. Migration `0003` (+`CreatedArchiveLibrary`,`RollbackStatus`,`DeletedAtUtc`,`DeletedBy`; `MoveStatus.RolledBack`); endpoints `GET /runs/{id}/deletability`, `POST /runs/{id}/rollback`, `DELETE /runs/{id}`; `RunCleanupActions` on Job Details. Design → `decisions/log.md` [2026-08-01]. Branch `feature/34591-abandoned-run-rollback-delete` (Epic 34120).

- [~] **34592** magiq-connstring-secret — *code present in tree; pending Chase's build/PR/merge.* Moves the read-only MAGIQ Documents connection string out of appsettings into the settings store as a new `SettingKind.Secret`, **encrypted at rest** with ASP.NET Core Data Protection (`ISecretProtector`); write-only/masked in the admin API + a password field on System Settings. `IMagiqConnectionStringProvider` decrypts for `MagiqDbConnectionFactory` (no restart). Hard cut — removed from appsettings/.env + `ConnectionStringsOptions`; set via UI before first run. Key ring at `DataProtection:KeyRingPath` (DPAPI on Windows / secured Docker volume). **Honest scope: encryption at rest only** (protects DB dumps, not a compromised host); current value is Windows-auth so no password anyway. No migration (seeds into `dbo.ConfiguredSetting`). Design → `decisions/log.md` [2026-08-01]. Branch `feature/34592-magiq-connstring-secret` (Epic 34120).

- [~] **34593** magiq-soap-settings — *code present in tree; pending Chase's build/PR/merge.* Moves the MAGIQ SOAP `Endpoint`, `TimeoutSeconds`, `MaxRetries`, `RetryBaseDelayMilliseconds` out of appsettings into the settings store + UI (live per next SOAP-client resolution). New `SettingKind.Url` for the endpoint; timeout/retries are Integer settings seeded with current defaults. **Endpoint keeps a config bootstrap** (login needs it → seeded from `MagiqDocuments:Endpoint` on first boot; can't hard-cut). `MagiqDocumentsOptions` keeps only `AdminAllowlist`; null-endpoint → clean SOAP error. Design → `decisions/log.md` [2026-08-01]. Branch `feature/34593-magiq-soap-settings` (Epic 34120). **ADO create timed out — confirm story 34593 exists / re-create.**

## Setup onboarding checklist (branch `feature/setup-onboarding`, Epic 34120 — design `decisions/log.md` 2026-08-01)
First-run wizard: all settings in the DB, only the app-DB connection string stored externally (partial credential encryption). Two-mode startup + a once-configured 409 gate. Slices 1–4 = app-DB step; the self-restart replaced the live-Hangfire activation; slice 5 = the MAGIQ-access step + allowlist to the DB.
- [~] **Slices 1–4** app-database step — *code present in tree; pending Chase's build/PR/merge.* External bootstrap file (`App_Data/appdb.json`) with partial credential encryption; two-mode startup (`isConfigured` gate); anonymous `GET /setup/status` + `POST /setup/test-connection` + `POST /setup/app-database`; Mantine wizard behind an `App.tsx` gate.
- [~] **Self-restart** activation — *code present in tree; pending Chase's build/PR/merge + host-restart verification.* `/setup/app-database` validates the DB (migrate+seed, rolls the file back on failure) then `StopApplication()`; the host restarts into configured mode with standard Hangfire wiring; SPA waits for a new per-process `InstanceId`. Needs a host that auto-restarts (IIS in-process / Docker restart policy / service); timeout path covers bare `dotnet run`.
- [~] **Admin UI reorg** settings-by-section + queries-page move — *code present in tree; pending Chase's build/PR/merge.* Frontend-only. System Settings is now one page of sections (MAGIQ connection, SOAP transport, process ticket, access control) with a single diff-save (writes only changed fields, per-key rowversion). Deletable-folder acronyms + query command timeout moved to the Configured Queries page ("Query settings" section, same save). Shared `admin/settingsEditing.tsx` (`useConfiguredSettingsEditor`, `SettingField`, keys/sections). No backend/API change; `SettingKeys.All` unchanged. Design → `decisions/log.md` [2026-08-02].
- [~] **Admin UI follow-ups** MAGIQ-DB test-connection + example, Queries single-save — *code present in tree; pending Chase's build/PR/merge.* Authenticated `POST /admin/settings/magiq-database/test-connection` (tests candidate or stored value; shared `Common/SqlConnectionTester`, setup tester delegates). System Settings MAGIQ-connection field gains a Test button + example string (`SettingField` `onTest`/`example` props). Configured Queries rewritten to one page + single diff-save over all queries **and** the two query-settings (`useConfiguredQueriesEditor`). Design → `decisions/log.md` [2026-08-02].

- [~] **Slice 5** magiq-access + allowlist-to-DB — *code present in tree; pending Chase's build/PR/merge.* Allowlist becomes the `AdminAllowlist` StringList setting (seeded from `MagiqDocuments:AdminAllowlist` on first boot), read **live** by `AdminAllowlist` (no restart to change operators); `MagiqDocumentsOptions` reduced to its section-name constant (unbound). Setup now two-phase: `GET /setup/status` reports `DatabaseConfigured`+`MagiqConfigured`; anonymous `GET/POST /setup/magiq` set the SOAP endpoint + allowlist (409 once complete), applied live via `SetupSettingWriter` — no second restart. Wizard gains the MAGIQ-access step; MAGIQ *DB* connection string stays post-login in System Settings. Tests: `SetupMagiqStateTests`, `SetupSettingWriterTests`, allowlist helpers rebuilt on the fake store. Design → `decisions/log.md` [2026-08-01]. **ADO story TBD (was disconnected).**

## UI modernization checklist (2026-07-31 — all merged; plan `ui-modernization-plan.md`)
Migrate the SPA to Mantine v9 + central theme (light/dark, mobile, single-file re-theming). Additive; no data-shape changes. Safety guards preserved verbatim.
- [x] **34584** ui-foundation-mantine (Feature 34124) — *merged.* Mantine + `MantineProvider`/`ColorScheme`, `src/theme/` (theme, status-colour map, icon registry), responsive `AppShell`, shared primitives (`StatusBadge`, `PageHeader`, `SectionCard`, `ColorSchemeToggle`). Blocks the rest.
- [x] **34585** ui-jobs-dashboard (Feature 34124) — *merged.* `JobsDashboard` on Mantine `Table` (status badges, progress cell, filters, pagination, skeletons), new-run `Modal`. **Also fixed the lifecycle-action 400** (`api/http.ts`: only send `Content-Type: application/json` when a body is present — body-less cancel/abandon/retry/reset were failing FastEndpoints binding).
- [x] **34586** ui-job-details (Feature 34124) — *merged.* `JobDetailsView` + `RunProgressPanel` restyled; `RunLifecycleActions` on Mantine buttons. SignalR/polling untouched.
- [x] **34587** ui-review-wizard (Feature 34126) — *merged.* `SetupWizard` → Mantine `Stepper`; Steps 6–8 restyled (virtualization kept). **Protected-folder delete block and typed "permanently delete" purge gate preserved verbatim.**
- [x] **34588** ui-polish (Feature 34124) — *merged.* Native `window.confirm` → Mantine confirmation `Modal`; `LoginPage` + `ConfiguredQueriesPage` restyled; skeleton loading; zero hardcoded hex remaining.
- [x] **34589** dashboard-summary-metrics (Feature 34124) — *merged.* Four summary cards + `GET /api/v1/runs/summary` (`GROUP BY Status`); `getRunSummary()` frontend; `GetRunSummaryHandlerTests` + fake `GetStatusCountsAsync`. Counts unpaged/unfiltered.

## Notes carried forward
- `MagiqDocuments`: endpoint `https://…/srv.asmx`, `AdminAllowlist` = `["sysadmin"]` (Chase set).
- Configurable SQL (guarded at first use, not on start-up): `CandidateDocuments` (Step 1), `DocumentRegister` (Step 2 export), `CandidateFolders` (Step 4), `FolderPaths` (Step 5). A run whose `CandidateDocuments`/`CandidateFolders`/`FolderPaths` are unset lands in **Failed**; the register export returns **502** until `DocumentRegister` is set.
- `DeletableFolderAcronyms` — **as of 34590** a system setting in `dbo.ConfiguredSetting`, edited live via the admin System Settings screen (`/admin/settings`); case-sensitive contains, applies with no restart. The query command timeout and ticket-heartbeat interval moved to the same store. **Protection (Rule 2) overrides the acronym lock.**
- Candidate documents + folders are stored during identification; Step 9 move logic (34143) drives `CleanupRunDocument.MoveStatus`; Step 10 delete (34144) drives `CleanupRunFolder.Status`.
- `RunProgressPanel` (34138) is mounted on the SetupWizard's post-confirm view and the JobDetailsView; the register-download control is now placed on the JobDetailsView (34526).
- All pipeline phases implemented (identification → archival → cleanup/purge). `RunPhaseExecutor` is feature-complete for Steps 1–11. `ListRuns` shipped in 34526; **Reset/Retry/Cancel/Abandon shipped in 34527** (below).
- **34527 (merged):** `CleanupRun` gains `Cancel`/`Abandon`/`Retry`/`Reset`/`BeginReview`; `IRunPipeline` gains `StartCleanup` + `EnqueuePhase(phase)`. Reset/Retry re-enqueue the failed phase (resume-safe bodies skip completed work); Cancel is cooperative (phase stops at its next guarded checkpoint). Identification now enters **ReviewSelection** at Step 6 (`BeginReview`) so Steps 6–8 report the right phase. **Design note for review:** given the phase bodies are idempotent, Reset and Retry converge behaviourally (neither re-moves moved docs nor recreates the library) — they differ in the step marker + log event (`Reset` vs `Retried`). Flag if you'd rather collapse to one action.
- **SOAP now verified (2026-07-29, 34525).** The `xsd:any` response shapes are confirmed against training: `<{Op}Result><response success="…" …/></{Op}Result>` (nested element, `success` attribute). Ticket comes back as a `ticket` **attribute** (fixed in `ReadTicket`); a deleted domain scatters its contents into the recycle bin as items keyed by `DeletePath="\{library}"` (Step 11 purge now matches + purges all). **Still unverified:** the four configurable SQL query column shapes (Part B → 34547).

## Folder delete-rule handling (2026-08-05 — code in tree, pending Chase build/PR/merge)
Decision → `decisions/log.md` [2026-08-05]. MAGIQ folder delete rules (`DISALLOWDOCUMENTDELETE` / `DISALLOWFOLDERDELETE`; parent governs child-folder deletion) block a `Move` (copy + delete) and a `DeleteFolder`. Two pieces, both implemented:
- [~] **Reactive rule guard (execution).** `IFolderDeleteRuleGuard`/`FolderDeleteRuleGuard` + new SOAP `GetFolderRules`/`SetFolderRules` on `IMagiqSoapClient` + `FolderRuleSet`. On a failed Step 9 `Move` / Step 10 `DeleteFolder`, reads the **live** rules, flips the one blocking rule to `allows` (`ApplyToTree=false`) on the doc's folder (`DocumentDeletes`) or the parent (`FolderDeletes`), retries once, then restores the exact original in a `finally`. No-op if the rule already allows / rules unreadable / relax rejected. Wired in `RunPhaseExecutor` (both sites); DI in `Program.cs`. Reactive-not-preflight so a **mid-run** rule change is honoured. **Also wired into the rollback move-back** (`decisions/log.md` [2026-08-05]): relaxes `NewDocuments` on the document's original folder (the copy-half of the move-back), since NATA's own folders — not the archive we created — can disallow new documents. Enum renamed `FolderDeleteRule` → `FolderRule` (now covers the non-delete `NewDocuments`). The rollback's run-created-folder cleanup stays unguarded (archive folders we own).
- [~] **Review tracking (informational).** `CandidateDocuments` → `DocumentDeleteBlocked`; `CandidateFolders` → `DocumentDeleteBlocked` (own) + `FolderDeleteBlocked` (parent, join on `PARENTID`). Flowed through records → `CleanupRunFolder`/`CleanupRunDocument` (**migration `0002_folder_delete_rule_flags.sql`**) → `FolderItem` → Step 6 "Delete-locked" badge + filter chip. Snapshot only (guard re-reads live); **not** a required schema-verification column (defaults false when omitted). SQL design doc §1/§3 updated.
- Tests: `FolderRuleSetTests`, `FolderDeleteRuleGuardTests`. Frontend `tsc -b` clean; C# reference-checked (no SDK on VM — Chase runs `dotnet build`).
- **Follow-ups:** confirm `Get/SetFolderRules` path format vs training (currently domain-rooted, no leading slash, like `GetFolders` — Story 34525 pattern); update `verify-magiq-queries.sql` + dev-spec SOAP contract/component map; **ADO story/branch(es) TBD** (suggest one for the guard, one for review-tracking). Stray untracked `*.out` files in `src/DocumentLifecycleCleaner.Web/` are tsc-run scratch — safe to `git clean`.

## Name Normalization phase (2026-08-05 — specified, NOT yet built)
Decision → `decisions/log.md` [2026-08-05]; spec §"Phase 3 — Name Normalization" (Step 8); ADR-002 + ADR-004 amendments; `dlc-process-walkthrough.html`. Works around the MAGIQ double-space bug: the desktop UI allows a document/folder name with a run of consecutive whitespace, but SOAP `Move`/`CreateFolder` collapse whitespace and can't move such an item — the archival `Move` fails.
- [ ] **New Phase 3 — Name Normalization, inserted before archival (new Step 8).** Renumbers the spec: Archival → Steps 9–10, Cleanup → Steps 11–12. **As-built code keeps the old numbers (Archival 8–9, Cleanup 10–11) until this ships** — flagged in spec/CLAUDE.md/ADR-002/ADR-004 so it isn't mistaken for drift.
- [ ] **Rename source items in place.** From the run's candidate docs + resolved paths, rename every item with doubled whitespace (→ single space): folder levels first, **top-down** (`UpdateFolderProperties`), then documents (`UpdateDocumentProperties`). New SOAP ops on `IMagiqSoapClient`. Idempotent/resume-safe; batched progress like the move.
- [ ] **Record every rename (audit).** New `CleanupRunRename`-style store + migration: item type, original path/name, new name, operator/ticket, timestamp; also to `CleanupRunPhaseLog`. Surface the rename log in the UI.
- [ ] **Audit lock (spec Rule 7).** `RunPhase.Normalization`; `CleanupRun.DescribeDeletability` must never return `CanDelete` once the run entered normalization (tier can be Reversible/Irreversible, never NoChanges) — renames aren't reversed by rollback, so the run is archived-only, retained with its rename log.
- **To confirm at integration (ADR-011/34525 class):** the exact path form `UpdateFolderProperties`/`UpdateDocumentProperties` accept to address a *still-doubled* source item, and both ops' response shapes — against `training.magiqdocuments.com`.
- **Follow-ups:** dev-spec.md (API/data-model/SOAP contract/sequence flow for the phase); **ADO story + tasks TBD** under Epic 34120 (deferred for now).

## Legend
`[ ]` not started · `[~]` in progress · `[x]` done (merged, or verified & pending merge)
