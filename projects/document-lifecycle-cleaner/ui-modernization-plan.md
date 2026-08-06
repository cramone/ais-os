# UI modernization — delivery plan

_Created 2026-07-31. Same delivery model as Epic 34120 and the deferred-work plan: one story per
branch, one PR each, worked in order; Claude implements in the working tree (uncommitted), Chase
creates the branch, builds, commits, PRs, merges._

> **Status: COMPLETE — all merged 2026-07-31.** All six stories shipped: 34584 foundation,
> 34585 dashboard (+ lifecycle-action 400 fix), 34586 job details, 34587 review wizard, 34588 polish,
> 34589 summary cards (+ `GET /runs/summary`, handler tests). Safety guards (protected-folder delete
> block, typed "permanently delete" purge gate) preserved verbatim. Per-story ledger in `tasks.md`.

## Why

The SPA shipped in Epic 34120 is functionally complete but visually unstyled: every component styles
itself with inline `style={}` objects and `CSSProperties` helpers, zero shared CSS classes, no design
tokens, no component library, ad-hoc colours (`#555`, `#c00`) per file. The structure is sound; the
presentation layer is missing. This plan adds that layer without touching the API surface.

## Decisions (settled 2026-07-31)

- **Component library: Mantine.** Batteries-included (tables, modals, notifications, forms, theming),
  bundles fully at build time — fits the on-prem, single-deployable, served-from-`wwwroot` constraint
  (no runtime CDN dependency).
- **Visual language: clean neutral / greenfield.** No MAGIQ Documents brand constraint. Professional
  neutral theme appropriate to an internal gov/enterprise operator tool. A brand palette can be
  retrofitted later by swapping theme tokens — the token layer makes that a one-file change.
- **Additive only.** No API, SignalR, or data-shape changes. Pure frontend; every existing behaviour
  (polling, run lifecycle, register download, typed purge confirmation) is preserved.
- **Light and dark mode** are first-class — every surface works in both via Mantine's colour scheme,
  with a toggle. No hardcoded hex anywhere; colours resolve through the theme.
- **Mobile-responsive** — every screen is usable at a narrow viewport (nav collapses, tables
  stack/scroll, no horizontal overflow).
- **Dynamically themeable** — a single theme layer (colour scale, semantic status-colour map, icon
  map, typography/spacing tokens) so icons, colours, or the whole theme can change from one file on
  customer feedback, no per-component edits. A MAGIQ or per-customer brand can be dropped in later by
  swapping that layer.

ADO: Epic 34120 · Feature 34124 (items 1-3, 5) / Feature 34126 (item 4). Stories 34584-34588,
tagged `ui-modernization; document-lifecycle-cleaner`, customer NATA.

## Constraints to honour

- Bundle at build time; no external CDN at runtime (on-prem).
- Keep the existing `tsc -b` + `vite build` pipeline; verification here is `tsc -b` + Chase's real
  `npm run build`. No bridge-VM Node build assumed.
- Preserve the typed `"permanently delete"` purge gate and the folder-validation delete block exactly
  — restyle, never loosen.

## Ordering rationale

Do the **foundation** first (item 1): it installs Mantine, the theme provider, and the app shell, and
every later item depends on it. Then the two highest-traffic surfaces — **dashboard** (item 2) and
**job details / progress** (item 3). The **wizard** (item 4) is the emotional core (review + confirm)
and largest UI-logic surface, so it comes after the system is proven on simpler screens. **Polish**
(item 5) closes out states, accessibility, and responsive layout across everything.

ADO: new stories under Epic 34120, Feature **34124 Orchestration & Progress** (items 1–3, 5) and
Feature **34126 Review/Selection/Confirmation** (item 4). Tag `ui-modernization`. Story IDs below are
placeholders — Chase creates the board items.

---

## Item 1 — Design foundation: Mantine, theme, app shell  (Story 34584 · Feature 34124)

**Branch:** `feature/34584-ui-foundation-mantine`  ·  Blocks items 2–5.

- Add Mantine (`@mantine/core`, `@mantine/hooks`, `@mantine/notifications`, PostCSS preset) to
  `DocumentLifecycleCleaner.Web`; wire `MantineProvider` + notifications in `main.tsx`.
- Define the neutral theme: colour scale, semantic status colours (NotStarted / Running /
  AwaitingInput / Failed / Completed / Cancelled / Abandoned), typography, spacing, radius — one
  `theme.ts` as the single source of truth.
- Replace the hand-rolled `AuthenticatedShell` in `App.tsx` with a Mantine `AppShell` (header, nav for
  Runs / Configured queries, sign-out, signed-in-as).
- Extract a shared `<StatusBadge>` and reusable primitives (page header, section card) so later items
  don't re-derive them.
- No behavioural change; `LoginPage` restyle can ride along here or in item 5.

## Item 2 — Jobs dashboard + new-run form  (Story 34585 · Feature 34124)

**Branch:** `feature/34585-ui-jobs-dashboard`

- Rebuild `JobsDashboard` on the Mantine `Table`: status badges, a phase/step progress cell, right-
  aligned numeric counts, hover + clickable rows, empty/loading/error states.
- Summary metric cards (total / awaiting input / running / failed) above the table.
- Restyle the filter toolbar (status select, optional source filter, reload) and pagination.
- Rework `NewRunForm` with Mantine form controls (date picker for the cutoff, validation, submit
  state); keep the `RunAlreadyActive` 409 handling.
- See the approved prototype (`dlc_jobs_dashboard_redesign_prototype`) for the target look.

## Item 2a — Dashboard summary metric cards  (Story 34589 · Feature 34124)

**Branch:** `feature/34589-dashboard-summary-metrics`  ·  Follow-up to item 2; needs a small backend add.

The four prototype cards (Total / Awaiting input / Running / Failed) were deferred out of 34585:
accurate counts span all runs, but `GET /runs` is paged, so a page-scoped count would mislead.
Adds a cheap `GET /api/v1/runs/summary` (`GROUP BY Status`) and renders the cards above the table,
polled on the run-list cadence, coloured from the central status map. Additive; `GET /runs`
unchanged. Full acceptance criteria on the ADO story.

## Item 3 — Job details + progress panel  (Story 34586 · Feature 34124)

**Branch:** `feature/34586-ui-job-details`

- Restyle `JobDetailsView`: run header (source, cutoff, status badge, created-by), lifecycle action
  buttons (`RunLifecycleActions`), the register-download control, and the phase log as a clean
  timeline/table.
- Restyle `RunProgressPanel` — the live SignalR progress into Mantine `Progress` + per-step states.
- Preserve all polling/SignalR wiring untouched.

## Item 4 — Wizard: Steps 6–8 review, confirm, archive  (Story 34587 · Feature 34126)

**Branch:** `feature/34587-ui-review-wizard`

- Restyle `SetupWizard` as a Mantine `Stepper`.
- `Step6FolderReview` — the folder review `Table` with selection, the blocked-folder validation
  surface, and the delete-constraint block clearly signposted.
- `Step7ConfirmDeletions` — confirmation summary; keep the delete-block-until-validation rule.
- `Step8ArchiveLibraryModal` + `PurgeControl` — Mantine `Modal`; **preserve the typed
  `"permanently delete"` gate verbatim**, restyled as a clear danger action.

## Item 5 — Polish: states, accessibility, responsive  (Story 34588 · Feature 34124)

**Branch:** `feature/34588-ui-polish`

- Consistent empty/loading/skeleton/error states across all surfaces (Mantine `Skeleton`, `Alert`).
- Accessible focus rings, colour-contrast pass on status colours, keyboard nav on tables/modals.
- Responsive layout down to a laptop width; icon set (Tabler via `@tabler/icons-react`).
- `LoginPage` and `ConfiguredQueriesPage` (admin) final restyle if not already covered.

---

## Git & PR conventions (same as Epic 34120)

- **Branch:** `feature/{storyId}-{kebab-slug}` (one story per branch/PR).
- Claude designs + implements in the working tree (uncommitted); Chase creates the branch off `main`,
  builds (`npm run build`), commits, opens + completes the PR.
- Changes land uncommitted in the device working tree; Chase moves them onto the feature branch.
- Verification here: `tsc -b` (types) by Claude; real `npm run build` + visual check by Chase.

## First branch to create

**`feature/34584-ui-foundation-mantine`** (item 1, Story 34584) — unblocks everything else, pure
scaffolding, low risk. Cut this off `main`; Claude implements once confirmed.
