# Memory

_Last updated: 2026-07-28_

## Memory
<!-- Things the user has asked to remember. Persistent — only remove or change if the user asks. -->

- **Description**: Automated yearly document culling for NATA — folder protection, deletion constraints.
- **"The spec"** refers to `spec/NATA_Document_Lifecycle_Cleaner_Spec_v0.6.md`, or the highest-versioned markdown rendition of that file if it has been updated since.

## Project status & resuming work (2026-07-28)

- **Epic 34120 is complete and merged** — the full pipeline (Steps 1–11: create → identify →
  review → confirm → archive/move → delete/purge), the React SPA, dual IIS/Docker hosting, and the
  deployment/operator docs. Shipped across PRs 721–737. `tasks.md` has the per-story ledger.
- **Next work = the deferred/post-MVP backlog.** Plan: `deferred-work-plan.md`. ADO stories (under
  Epic 34120's existing features, tagged `deferred-post-mvp`):
  - **34525** Verify MAGIQ SOAP integration against training _(do first — retires the xsd:any
    assumptions in 34143/34144; needs Chase's live access to training.magiqdocuments.com)_
  - **34526** Jobs dashboard, new-run form & job details view _(largest; removes the interim run-id loader)_
  - **34527** Run recovery & lifecycle actions (Reset/Retry/Cancel/Abandon)
  - **34528** Choose an existing archive library (Step 8)
  - Recommended order: 34525 → 34526 → 34527/34528. If Chase can't run the live cull immediately,
    start 34526 (pure implementation) and do 34525 alongside.
- **How we work + git/PR conventions:** `dev-context.md` §7 and the "Git & PR conventions" section of
  `deferred-work-plan.md`. In short: Claude designs the branch + implements in the working tree
  (uncommitted); Chase creates the branch, builds, commits, PRs, merges.
- **Verification here:** no .NET SDK on the bridge VM — Claude validates C# by balance/reference/XML
  checks and the frontend by `tsc -b`; Chase does the real `dotnet build`/`npm run build`.

