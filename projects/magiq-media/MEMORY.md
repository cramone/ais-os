# Memory — magiq-media
_Last updated: 2026-09-16_

## Memory
<!-- Persistent — only remove or change if Chase asks. -->

- **Description**: Document management API — tenants, auth, user security, signing.
- **Q2 priorities**: Complete API, tenant management + auth, user security + policies
- **"The spec"** refers to `D:\source\github\sprbrk-standard\mgq-magiq-media\docs\spec\` (ADRs: `docs\adrs\`) — moved there
  from this docs project on 2026-07-07; that repo is the only source of truth. The old
  `projects/magiq-media/spec/` path is dead — don't look there.
- **Spec files state the specified system only** (Chase, 2026-09-16). Present tense, no history, no
  progress. Never write into `docs/spec/`: change history or "this previously said…"; citations to
  anything not defined inside `docs/` (review/finding/plan/workstream ids — `X-4.14`, `MM-045`,
  `DEC-9`, `W29`); **build or implementation status** — whether code exists, is wired, deployed or
  deferred; rationale and rejected options; recommendations, open questions or ✓ tracking; notes to a
  reader or AI agent; who decided and when. Fix the statement and delete the wrong one — the diff is
  the history; a removed feature is simply absent, never documented as removed. Homes: rationale →
  `docs/adrs/` · build status → `Media` ADO board and the repo `CLAUDE.md` § Known deferred/partial
  work · findings → `reviews/` · open questions → `plans/`/`todos.md` · durable facts → here. Full
  rule: repo `CLAUDE.md` § Spec files state the specified system.
- **A review may quote a spec file; a spec file may never cite a review.** If a remediation item can't
  be written without naming a finding id, restate the rule in its own terms in the spec and keep the
  id on the plan side.
- **Deferred**: DocumentSigningSaga (not registered), SigningSessionSummaryProjector, DocumentSigningTimeoutScanner
- **MediaItemReviewSaga is NOT deferred — it was deliberately removed 2026-06-02** and is not coming back.
  Struck from the Deferred list 2026-09-13 (Chase). Shipped on `develop` and `release/1.0.0`, never reached
  `main`, deleted in `7d1f32e5` (PR #81, promoted as `cc7f9be8`, PR #83); zero hits in `src/` today.
  Replaced by the embedded `ReviewSession` on `MediaItem`, which is why approval is an aggregate invariant.
  See `docs/spec/shared/saga-patterns.md` § There is no review saga — approval is a MediaItem invariant.
- **magiq-auth repo**: `D:\source\github\magiqsoftware\magiq-auth` — referenced in this project (likely upstream Identity/auth context)
