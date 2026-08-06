# Deferred work — delivery plan (post-MVP)

_Created 2026-07-28, after Epic 34120 (Steps 1–11 pipeline, SPA, dual hosting, docs) was completed._
Everything below was consciously deferred during 34120 and flagged in `decisions/log.md` / `tasks.md`.
Same delivery model as 34120: one story per branch, one PR each, worked in order.

New ADO items hang under the **existing** features of Epic 34120 (no new epic needed):
34122 MAGIQ Integration, 34124 Orchestration & Progress, 34126 Review/Selection/Confirmation.

**Created on the board (2026-07-28), tagged `deferred-post-mvp`:** Story 34525 (+tasks 34529–34532), Story 34526 (+34533–34535), Story 34527 (+34536–34538), Story 34528 (+34539–34540).

**Update (2026-07-29):** Story 34525 SOAP verification done — see below; task **34547** added under 34525 for the still-outstanding Part B (SQL query shapes).

**Update (2026-07-31):** Story **34575** added (Item 4 below) — schema verification for the configurable MAGIQ queries (tasks 34576–34580, Feature 34122). Not one of the original four.

## Ordering rationale

**Do item 0 first.** The archival/cleanup/purge phases were built against *assumed* `xsd:any` SOAP
response shapes (`Move`, `CreateDomain`, `GetRecycleBinContent`, `PurgeRecycleBinItem`) — grounded in
the WSDL but never round-tripped against a live service. Verifying them retires the biggest risk in
the codebase and may generate small follow-up fixes; do it before building features on top.

Then the run **shell** (item 1) — the largest UX gap and the mount point for the register-download
button and progress panel; it removes the interim run-id loader. Recovery (item 2) and the existing-
library picker (item 3) are smaller and independent, orderable by preference.

---

## Item 0 — Verify MAGIQ SOAP integration against training  (Story 34525 · Feature 34122)

**Branch:** `feature/34525-verify-soap-integration`  ·  Verification, may produce small fixes.

The one item that is not a feature. Run a full cull against `training.magiqdocuments.com` and confirm
the inferred SOAP contracts, adjusting the parsers where reality differs.

Checklist:
1. **End-to-end run** against training: login → create run → identification → review → confirm →
   archive/move → delete-empty-folders → purge. Capture the raw SOAP responses for each op.
2. **Auth / heartbeat / queries** — confirm `AuthenticateUser`, `isValidTicket`, and the four
   configurable queries return the shapes the code expects (Story 34133/34134/34135 assumptions).
3. **Archival ops** — confirm `CreateDomain`, `CreateFolder`, `Move` signal success via the `success`
   attribute; adjust `ParseAck` / `ParseCreateDomain` if the shape differs. Confirm path-based `Move`
   (SourcePath/DestinationPath) behaves as assumed.
4. **Purge ops** — confirm `DeleteFolder`, `DeleteDomain`, and especially `GetRecycleBinContent` item
   shape (handle + name fields) and `PurgeRecycleBinItem` handle; tighten `ParseRecycleBinContent` +
   the name match if needed.
5. **Record findings** in `decisions/log.md`; open bug tasks for any parser adjustments.

**Status (2026-07-29): SOAP pass done, on branch `feature/34525-verify-soap-integration`.**
Full cull captured against training; all 9 ops reconciled (raw responses + findings in
`DocumentLifecycleCleaner/SOAP-VERIFICATION-34525.md`; entry in `decisions/log.md`). Two defects
found and fixed in the working tree: (1) `ReadTicket` — the ticket comes back in a `ticket`
**attribute**, not an element, so login was returning null; (2) Step 11 purge — `DeleteDomain`
scatters the domain's contents into the recycle bin as individual items (`DeletePath="\{library}"`),
not one entry, so the purge now captures `DeletePath` and purges **every** matched item. Tasks
34529–34531 done, 34532 (auth) done. **Still outstanding → task 34547:** Part B, the four
configurable SQL query column shapes (Dapper, not SOAP) — not captured in this pass; fill in Part B
of the verification doc + record findings. Also pending: a real `dotnet build` + live re-run to
confirm login and the multi-item purge post-fix.

---

## Item 1 — Jobs dashboard, new-run form & job details view  (Story 34526 · Feature 34124)

**Branch:** `feature/34526-jobs-dashboard-run-shell`  ·  Largest of the four; frontend-heavy.

Removes the interim run-id loader and gives operators a real shell.

Tasks:
- **`GET /api/v1/runs`** — a paged/filtered run list (id, cutoff, status, phase/step, counts, timestamps).
- **New-run form** (cutoff date → `POST /api/v1/runs`) + **jobs dashboard** listing runs with live
  status/progress (polling); replace the App-shell run-id loader.
- **Job details view** — mount the existing `RunProgressPanel` (34138) + the **Document Register
  download** control (built in 34139, never mounted) + the phase log.

---

## Item 2 — Run recovery & lifecycle actions  (Story 34527 · Feature 34124)

**Branch:** `feature/34527-run-recovery-lifecycle`

Lets an operator recover a failed run in-tool instead of starting over.

Tasks:
- **Reset / Retry a Failed run** — widen the `CleanupRun` state-machine to admit a re-run from
  `Failed`, and re-enqueue the failed phase (identification/archival/cleanup) idempotently
  (resume logic already skips completed work).
- **Cancel / Abandon** endpoints + UI controls.
- **Tidy `CurrentPhase`** — it currently stays `Identification` through Steps 6–7; flip it to
  `ReviewSelection` so the dashboard/details show the right phase.

---

## Item 3 — Choose an existing archive library (Step 8)  (Story 34528 · Feature 34126)

**Branch:** `feature/34528-existing-archive-library-picker`

The Step 8 modal only supports "create new" today; the confirm API already accepts `mode:"existing"`.

Tasks:
- **`GET /api/v1/libraries`** (SOAP `GetDomains`) + optionally `GET /api/v1/libraries/{id}/folders`
  for lazy subfolder browsing.
- **Step 8 modal** — existing-library list (name filter) + one-level-at-a-time subfolder browser;
  wire the `mode:"existing"` path end to end.

---

## Item 4 — Schema verification for the configured MAGIQ queries  (Story 34575 · Feature 34122)

**Branch:** `feature/34575-schema-verification`  ·  Added 2026-07-31 (not part of the original four).

NATA's on-prem MAGIQ schema can drift between versions; the app's only dependency on it is the four
configurable queries (ADR-004), so a dropped/renamed/retyped column surfaces mid-run. On-demand admin
pre-flight to catch it up front. See `decisions/log.md` [2026-07-31] for the full design.

Tasks (34576–34580):
- **Contracts + type-compatibility matrix + report model** — code-constant required columns per query
  (register has none); logical→SQL matrix mirroring the Dapper reader.
- **SchemaOnly probe + verifier** — `CommandBehavior.SchemaOnly` describe (no execution), `@folderIds`
  IN-rewrite; store→probe→diff→report; DI.
- **Admin endpoint** — `POST /api/v1/admin/schema/verify` on the `DlcEndpoint` bus, string-enum view.
- **Configured Queries UI** — Verify-schema button + per-query/per-column report panel.
- **Confirm + docs** — `GetSchemaTable` type names against training; `dotnet build`; docs.

**Status (2026-07-31):** implemented in the working tree, `tsc -b` clean, C# validated by
balance/reference checks. Pending Chase's build/PR/merge. Confirm `GetSchemaTable` `DataTypeName`
shapes against training on merge (same live-shape risk class as 34525).

---

## Git & PR conventions (same as Epic 34120)

Division of labour (dev-context.md §7): **Claude designs the branch + implements in the working tree
(uncommitted); Chase creates the branch off `main`, builds, commits, opens + completes the PR.** The
loop per story: Claude gives the branch name -> Chase creates it -> Claude implements -> Chase builds
(`dotnet build` / `npm run build`) + commits + PRs + merges -> next story starts on the clean base.

- **Branch:** `feature/{storyId}-{kebab-slug}` (one story per branch/PR). See each item above.
- **Commit message:** `{short summary} #{taskId} #{taskId}` + an optional wrapped body. Match the
  existing history (e.g. `implemented confirm + delete-constraint (Step 7) #34186 #34187`). Chase
  commits, so no AI-authorship trailers.
- **PR title:** `{storyId} - {Story title}` (e.g. `34526 - Jobs dashboard, new-run form & job details view`).
- **PR description:** short intro line, then a bullet per task with `#{taskId}`, then a one-line note
  on packages/verification. Claude drafts the full commit + PR text at the end of each story.
- **Always:** link the Story on the PR; keep the `document-lifecycle-cleaner` tag.

### Gotchas carried from this build

- **No .NET SDK on the bridge VM** - Claude verifies C# by brace/paren balance, reference checks, and
  XML/JSON well-formedness, and the frontend by `tsc -b`; Chase runs the real builds.
- **Changes land uncommitted** in the device working tree; Chase moves them onto the feature branch.
  Watch for gitignored deliverables (e.g. `*.pubxml`) and files written to the wrong filesystem
  (use device_bash / the device tree, not the cloud sandbox).
- **Device bridge can drop mid-write** - file edits are atomic (whole-file or nothing), so on a drop,
  re-verify the last write and re-apply if missing.
- **ADO board quirks:** `Custom.AffectedCustomer` is required on User Stories (use `NATA`);
  `System.Parent` does not set on create through the MCP - create the story, then link it to its
  Feature with `wit_work_items_link` (type `parent`); the ADO MCP can time out, so verify after writes.

## Start here (next session)

1. **Read** `MEMORY.md` -> this plan -> `dev-context.md` §7 -> `decisions/log.md` (esp. the 2026-07-28
   archival/cleanup entries - the SOAP assumptions 34525 verifies).
2. **Item 0 (34525) is a joint task:** the live cull must run against `training.magiqdocuments.com`,
   which needs Chase's environment. Claude prepares the verification checklist (tasks 34529-34532)
   and, from the captured SOAP responses, adjusts `ParseAck` / `ParseCreateDomain` /
   `ParseRecycleBinContent`. If Chase can't run it immediately, **start 34526 instead** (pure
   implementation) and do 34525 alongside.
3. First branch to request from Chase (pure-implementation path): **`feature/34526-jobs-dashboard-run-shell`**
   (Story 34526, tasks 34533-34535).

## Item 5 — Run operation audit trail  (new Story · Feature 34124 Orchestration & Progress)

**Branch:** `feature/{id}-run-operation-audit`  ·  Backend + small SPA panel. See `decisions/log.md` [2026-08-05] "Operation audit trail…".

Close the gap that the only append-only log today (`CleanupRunPhaseLog`) is phase-grain; object-level
outcomes are mutable status flips with no "what happened, when, by whom, with what result" trail.

Scope:
1. **Migration `0002`** — `dbo.CleanupRunOperation` (append-only; `Seq` per-run monotonic, `OperationType`,
   `Outcome`, `TargetType`, `SourcePath`, `DestinationOrNewName`, `SoapSuccess`, `Detail`, `ErrorMessage`, `Operator`).
2. **Domain enums** `RunOperationType` / `RunOperationOutcome` / `OperationTargetType`; `CleanupRunOperation`
   record; `ICleanupRunOperationStore` + Dapper store (append + `GetByRunAsync`).
3. **Executor wiring** at every SOAP site in `RunPhaseExecutor` — `CreateFolder`/`CreateDomain` (per-op),
   `Move` (**batch-summary**, Chase's call — moved/failed counts per batch), `DeleteFolder`/`DeleteDomain`/
   `Purge` (per-op), rule-relax + restore (from the guard), and the Step-6 operator `OperatorOverride` +
   Step-7/12 `PurgeAuthorised` decision events. A `Rename` row when Name Normalization lands.
4. **Read surface** — `GET /api/v1/runs/{runId}/operations` (mirrors `GetRunLog`) + a "Operations" panel in the
   Job Details view.

In the tree (uncommitted): 0002, enums, store, `GET .../operations` read endpoint, DI, and wiring at
**all** SOAP sites + decision points — create-folder/domain, move (batch-summary), delete-folder,
delete-domain + purge (teardown), rule-relax/restore (guard hooks), operator override, purge-authorised;
`HardDeleteAsync` clears the audit. **SPA: the Job Details view now shows an "Operation audit trail"
panel** (polled, outcome-coloured). **Remaining:** `Rename` rows (arrive with Name Normalization) and
tightening override attribution to the reviewing operator (`ICurrentOperator`).

## Item 6 — Before/during/after Document Register + CSV  (new Story · Feature 34126 Review/Selection/Confirmation)

**Branch:** `feature/{id}-register-snapshots-csv`  ·  Backend + export UI. See `decisions/log.md` [2026-08-05].

Make the register capturable **before** and **after** a run and exportable to CSV, so a run reads
before → during → after (the "during" being Item 5's audit).

Scope:
1. **Retention** — `dbo.RegisterExport` gains `SnapshotKind (PreRun|PostRun|AdHoc)`; drop the delete-prior
   behaviour for the two pinned snapshots (AdHoc stays latest-only).
2. **`RegisterCsvWriter`** parallel to `DocumentRegisterExcelWriter`; export request/download take `format=xlsx|csv`.
3. **Pre-run snapshot** captured at confirm (Step 7) / before Normalization; **outcome ledger** ("after")
   built from the run's own tables (`CleanupRunDocument`/`CleanupRunFolder`/rename log), not a source re-query.

In the tree (uncommitted): `RegisterCsvWriter`; `SnapshotKind`+`Format` columns (0002); `?format=xlsx|csv`
on the on-demand export with content-type-aware download; retention (AdHoc latest-only, Pre/Post pinned);
PreRun snapshot captured at confirm; PostRun outcome ledger (from the run's tables) at completion — both
CSV; `GET .../register/exports` list endpoint. **SPA: the Document Register card now has an Excel/CSV
format toggle and a before/after snapshot list with per-snapshot download.** **Remaining:** per-format
snapshot capture if operators want the pinned snapshots in Excel too (currently CSV).

## Not planned (intentional)

- Alternate purge strategies (EmptyRecycleBin) — targeted purge chosen (2026-07-28 decision).
- Anything requiring a schema rollback path — migrations remain forward-only.
