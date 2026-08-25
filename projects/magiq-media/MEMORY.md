# Memory — magiq-media
_Last updated: 2026-08-25_

## Memory
<!-- Persistent — only remove or change if Chase asks. -->

- **Description**: Document management API — tenants, auth, user security, signing.
- **Q2 priorities**: Complete API, tenant management + auth, user security + policies
- **"The spec"** refers to `D:\source\github\magiq-media\docs\spec\` (ADRs: `docs\adrs\`) — moved there
  from this docs project on 2026-07-07; that repo is the only source of truth. The old
  `projects/magiq-media/spec/` path is dead — don't look there.
- **Deferred**: DocumentSigningSaga (not registered), SigningSessionSummaryProjector, DocumentSigningTimeoutScanner, MediaItemReviewSaga (partial — missing closing handlers)
- **magiq-auth repo**: `D:\source\github\magiq-auth` — referenced in this project (likely upstream Identity/auth context)
