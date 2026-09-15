# Memory — magiq-media
_Last updated: 2026-09-13_

## Memory
<!-- Persistent — only remove or change if Chase asks. -->

- **Description**: Document management API — tenants, auth, user security, signing.
- **Q2 priorities**: Complete API, tenant management + auth, user security + policies
- **"The spec"** refers to `D:\source\github\sprbrk-standard\mgq-magiq-media\docs\spec\` (ADRs: `docs\adrs\`) — moved there
  from this docs project on 2026-07-07; that repo is the only source of truth. The old
  `projects/magiq-media/spec/` path is dead — don't look there.
- **Deferred**: DocumentSigningSaga (not registered), SigningSessionSummaryProjector, DocumentSigningTimeoutScanner
- **MediaItemReviewSaga is NOT deferred — it was deliberately removed 2026-06-02** and is not coming back.
  Struck from the Deferred list 2026-09-13 (Chase). Shipped on `develop` and `release/1.0.0`, never reached
  `main`, deleted in `7d1f32e5` (PR #81, promoted as `cc7f9be8`, PR #83); zero hits in `src/` today.
  Replaced by the embedded `ReviewSession` on `MediaItem`, which is why approval is an aggregate invariant.
  See `docs/spec/shared/saga-patterns.md` § The review saga was built and then removed.
- **magiq-auth repo**: `D:\source\github\magiqsoftware\magiq-auth` — referenced in this project (likely upstream Identity/auth context)
