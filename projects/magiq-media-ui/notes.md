# Notes — magiq-media-ui

## Design work (started 2026-08-12)

Mockup-first design in Claude. Domain source of truth = backend spec at
`D:\source\github\magiq-media\docs` (7 modules, ~50 use cases, 14 ADRs).

Decisions logged in `decisions/log.md` (D-001..D-005). Key ones:
- Tenant from JWT only, never in URL. Switch = token re-issue.
- Visual: MAGIQ/Cirrus family DNA (navy chrome, blue accent, card canvas) → evolved for media.
- Ingestion states first-class: pending → processing → available | failed.

### Design order
1. App shell + nav ✅ (mockup done)
2. Tenant switch flow ✅ (selector + switching sequence + upload guard; D-006, R-001)
3. Library browse ✅ (collection/folder tree + MediaItem list, all 5 statuses + checkout/conformance flags, list default / grid toggle)
4. Upload flow ✅ (drop zone + target selector + persistent queue; two-phase: client % vs server validating/processing; all failure categories)
5. Mobile shell ✅ (navy header + horizontal filter chips + record rows + bottom tab bar w/ upload FAB + nav drawer with tenant switcher)

**Design order 1–5 complete (2026-08-12).** All mockups done in Claude.

### Follow-up build queue (2026-08-12)
6. MediaItem detail screen ✅ (header + status/checkout + contextual actions; under-review banner w/ CR link; assets-by-role w/ processing states + download; metadata current-vs-draft diff w/ Governed/General origin; conformance gap; version history; properties + related CR/signing/registrations sidebar)
7. Library grid/thumbnail variant ✅ (auto-fill thumbnail tiles; type-aware preview: image tint / PDF icon / processing placeholder; status chip + version + checkout/conformance corner flags; grid⇄list toggle; cursor pager)

Detail screen data sourced from mediaitem.api.md (GET detail response) + read-model.
Spec facts baked in: metadata {current, draft}; assets [{assetId, roleName, assetStatus, order}];
activeMediaChangeRequestId / activeSigningSessionId / registrationIds; conformanceGaps [{GapType, Identifier}];
version history via GET /items/{id}/versions.

**Follow-up build queue 6–7 complete (2026-08-12).**

### Domain screen queue (2026-08-12)
8.  Change Request review        ✅ (reviewer-facing: header links MediaItem under review; threaded discussion w/ reply/edit-own; reviewer tally w/ ReviewerStatus Pending/Approved/Rejected/Withdrawn; Approve / Request-changes decision — reject requires reason; self-review guard note; "what changed" diff link. Decisions dispatch to MediaItem approve/reject endpoints, not CR — CR is comment thread only.)
9.  Search / faceted results     ✅ (OpenSearch-backed: query bar w/ 300ms debounce note; facet rail — status, media profile, owner, date-created, tags w/ AND/OR toggle; facet counts; removable active-filter chips; ranked results w/ <mark> highlight + relevance score bar + record path + status; eventual-consistency banner; search_after "Load more". Facets = indexed keyword fields; covers gap-report SH-1..4.)
10. Registration lifecycle       ✅ (stage stepper Initiated→Submitted→PendingConfirmation→Confirmed w/ actor labels owner-vs-authority + rejection/resubmit + cancel notes; event timeline distinguishing owner vs system/authority actions; attached docs primary+supporting (R-6 multi-item); details w/ external Reference "on confirm"; status-driven actions Attach/Cancel. States: Initiated/Submitted/PendingConfirmation/Confirmed/Rejected/Resubmitted/Cancelled; Electronic|Physical type.)
11. Signing session              ✅ (envelope stepper Initiated→EnvelopeCreated→EnvelopeSent→Completed→SignedAssetRecorded; sequential signer routing by RoutingOrder w/ Pending|Completed + current-signer highlight; activity fed by SecuredSigning webhooks; checkout-lock-held banner (auto-releases + publishes on signed-asset record); Cancel disabled after send — void only at provider. States incl Voided/Cancelled/TimedOut.)
12. Admin — Record types / Media profiles  ✅ (segmented toggle. Record types: schema editor — Published-vN + editing-draft badge, aliases, field table (FieldType Text|Number|Date|Boolean|Url|Enum|MultiEnum + Required + Searchable + constraints; capability-contributed fields locked/immutable), 100-field cap, Publish-draft/Deprecate, "type immutable → Replace" note. Media profiles: Draft/Published/Deprecated, Capabilities badges (Processing/Registration/Signing), ReviewPolicy/CheckoutPolicy, pinned RecordType versions w/ update-pin, AssetDefinitions roles required/optional + type + max size.)

**Domain screen queue 8–12 COMPLETE (2026-08-12).**

## Overall status — 12 screens designed
Shell + tenant switch + library (list+grid) + upload + mobile + item detail
+ CR review + search + registration + signing + admin. All mockups in Claude, spec-accurate.

Remaining parked/open: read-model status enum drift flag to backend; R-001 (magiq-auth silent switch); ADO board unassigned.
### Remaining screen queue (2026-08-12)
13. Login / auth (OIDC PKCE)             ✅ (branded sign-in card → "Continue with magiq-auth"; no creds entered in app; side flow: PKCE challenge → redirect to IdP → auth+MFA+tenant at IdP → code exchange → access token in memory / refresh in httpOnly cookie, nothing in localStorage.)
14. 403 permission-denied page           ✅ (full page, stays signed in — NOT a login redirect (403≠401); names resourceOwner; Back to library + Request access; collapsible RFC 9457 ProblemDetails technical detail w/ errorCode Forbidden.)
15. Empty / error state catalog          ✅ (reusable card grid: empty folder / no search results (w/ did-you-mean) / empty upload queue / nothing to review / load failure+retry / offline / still-processing / permission-limited-hidden. CDS voice: empty=invitation+CTA, error=what happened+what to do; error/processing cards wrapped in aria-live polite.)
16. Collection / Folder create + manage  ✅ (settings: name, description, Visibility Private/Public toggle, default media profile, tags; folder hierarchy manager w/ nested tree + inline create-subfolder; danger zone Archive — cascades to child items, active-registrations blocks archive.)
17. Bulk operations (archive / metadata) ✅ (multi-select + navy bulk action bar (Edit metadata/Archive/Move), max-100 note; shared-field metadata apply (blank=unchanged); onError Continue|FailFast + onDuplicate Skip|Reject toggles; result view = partial-success envelope {succeeded/failed/skipped} tallies + per-item BulkItemError w/ #index + errorCode + message; 202 Accepted on partial.)
18. Audit log viewer                      ✅ (FLAGGED design-ahead-of-spec — gap ADM-4, no read-model/endpoint yet. Filterable tenant-scoped event stream: actor/action/target/time/source; category filters (Publishing/Access control/Security/Admin); security events highlighted (infection, force-release, 403 denied, sign-in); export. Backend must confirm shape.)
19. Notifications                         ✅ (bell-anchored panel w/ unread count; domain-event types — virus-blocked, review-assigned, review-approved/published, processing-failed, signing-completed, registration-confirmed, checkout-force-released; grouped by day; read/unread + deep links to records; mark-all-read; aria-live polite.)

**Remaining screen queue 13–19 COMPLETE (2026-08-12).**

## FINAL STATUS — 19 screens designed
All mockups built in Claude, spec-accurate against D:\source\github\magiq-media\docs.

Frame: Shell · Tenant switch · Mobile shell · Login (OIDC PKCE) · 403 page · Empty/error catalog · Notifications
Library: Browse list · Browse grid · Item detail · Collection/Folder manage
Workflows: Upload · CR review · Registration · Signing · Bulk operations
Discovery: Search (faceted)
Admin: Record types · Media profiles · Audit log

### Flags raised for backend
- Read-model status enum drift (Rejected/Withdrawn vs canonical Draft|PendingApproval|Published|Revising|Archived).
- Audit log (screen 18) — no read-model/endpoint exists (gap ADM-4); designed a proposed shape.
- R-001 — magiq-auth must support silent tenant switch (user-scoped refresh token + tenant param).

### Still open (non-screen)
ADO board unassigned. Next possible phase: assemble into clickable prototype, or begin real React scaffold (shell first).

### Screenshots (2026-08-12)
All 19 screens exported to PNG in `screenshots/` (01..19-*.png).
Pipeline: standalone HTML per screen in `screenshots/_build/screens/`, rendered via puppeteer-core
driving installed Chrome (`_build/shot.js`, fullPage). Re-run: `cd screenshots/_build && node shot.js [filter]`.
CDS light-mode tokens + Tabler icon webfont are defined in shot.js HEAD. node_modules gitignored.
Admin split into two shots (11 record types, 12 media profiles). Multi-state screens captured at primary/default state.

### Design foundations (2026-08-12)
Decision: keep mockup-in-Claude as the design medium (no Figma, no React scaffold yet).
Built two extractable foundations from the 19 screens → `design-system/`:
- ✅ tokens.css + tokens.json (colors/type/spacing/radii/shadow/layout; provisional dark mode incl.)
- ✅ components.md (15 primitives catalogued: chrome, nav rail, status chip, button, card, table row, stepper, timeline, banner, toast, metadata-diff row, facet, empty state, avatar, segmented toggle)
- ✅ shot.js now imports tokens.css → single source of truth feeds every screenshot.
Brand values in tokens are PLACEHOLDER (navy/blue inferred from Cirrus) — pending real MAGIQ brand assets (logo SVG, official palette hex, typeface).

### What still helps Claude design (ranked)
3. Real MAGIQ brand assets — needs marketing. Request list: `design-system/brand-asset-request.md`. ← BLOCKING resume
4. ✅ Live OpenAPI — `swagger.json` in project root (OpenAPI 3.0.0, MAGIQ Media API v1, 104 paths, 160 schemas). Use for exact field/enum validation.
5. User journeys (end-to-end flows) → surface missing transition/confirmation screens.
6. Dark mode in/out decision (tokens are dark-ready but provisional).
7. Responsive breakpoint spec (only desktop + 1 mobile defined).
8. Interaction/motion spec (skeletons, transitions, polling cadence, focus mgmt).
9. Per-component WCAG 2.2 AA checklist (axe-in-CI mandated, no checklist yet).

---

## ⏸ RESUME POINT (2026-08-12)

**Branding — DISCOVERED + APPLIED** from springbrooksoftware.com:
navy **#1D3455** (chrome + primary + active nav), **Manrope** type (OFL, free), secondary accents
cyan #00A0D2 / green #2DCD7C / teal #003B49 / red #B80105. Applied to `tokens.css` + `tokens.json`
and re-rendered across all 19 screenshots (`screenshots/01–19-*.png` now on-brand). shot.js loads
Manrope from Google Fonts + reads tokens.css.

**Still ideal from marketing (small, non-blocking):** SVG logo (site ships PNG only) + favicon SVG
+ palette sign-off. Product name confirmed: **MAGIQ Media** (product), Springbrook (owner co., using
their scheme) — no wordmark change. List: `design-system/brand-asset-request.md`.
When the SVG logo arrives: replace the placeholder "M" chip in app-bar + login, add favicon, re-render.

### Contract validation vs swagger.json (2026-08-12) → `design-system/contract-validation.md`
Field names + routes the screens use are ACCURATE where the contract defines them. Findings:
- ✅ Match: MediaItemSummaryModel fields, RecordType field model (fieldName/isRequired/isSearchable/isImmutable/sourceCapability), bulk envelope, CR comment model, upload response, registration request, FieldType/ReviewPolicy/CheckoutPolicy/RegistrationType enums, all item/bulk/search/registration/folder/collection/profile/record-type routes.
- ⚠ 4 quick mockup fixes: Collection visibility missing **Unlisted**; bulk onDuplicate missing **AutoSuffix**; Capability real set is 9 (showed 3); Registration doc labels should be ApplicationForm/SupportingEvidence.
- 🔴 Backend contract gaps (screens ahead of contract — keep as design intent + backlog):
  1. Checkout/lock: NO field anywhere in contract (screens 1/3/5/6 show it).
  2. MediaItem detail (GET /v1/items/{itemId}) has NO response schema → metadata/assets/activeCR/activeSigning/registrationIds/conformanceGaps all absent (screen 6).
  3. Signing: 0 paths / 0 schemas (screen 10 fully ahead — like audit).
  4. Audit: 0 paths (confirms ADM-4).
  5. Statuses are plain strings, not enums → RESOLVES the old "status enum drift" flag: contract doesn't pin them; screens use the write-model set correctly. Backend to decide whether to publish status enums.
  6. CR reviewers list not in any schema (screen 7 tally unbacked).
- MediaItemSummaryModel exposes unused `recordDate` + `author` — could surface in list/detail.

### 2026-08-12 — 4 enum fixes applied + Gaps handed off
- ✅ Applied 4 mockup fixes + re-rendered: Collection visibility 3-way (+Unlisted, #16); bulk onDuplicate +Auto-suffix (#17); Media profiles show all 9 capabilities "3 of 9 active" (#12); Registration doc types → ApplicationForm/SupportingEvidence (#9).
- ✅ 6 backend gaps written for API team → `Gaps/api-contract-gaps.md` (detail-response schema, checkout exposure, signing API, audit API, status enums, CR reviewers).

### 2026-08-12 — Implementation-bridge artifacts (design → code) → `design-system/`
Medium stays mockup-in-Claude; frontend repo is separate, so these are TRANSFER artifacts (author here, apply in repo).
- ✅ `tailwind.tokens.cjs` — Tailwind theme.extend mapping utilities → CSS-var tokens (tokens.css stays single source; dark mode auto-flips). Drop-in for repo tailwind.config.
- ✅ `component-props.ts` — TS Props interfaces for all 15 primitives (from components.md). Design→code contract; domain types come from generated client, not duplicated.
- ✅ `build-sheets.md` — per-screen spec for all 19: route, queries (real swagger endpoints + query-key factories), components, state tiers (SRV/URL/CLI), states, mutations+invalidations. Marks 🔴 GAP screens. Includes query-key factory list + suggested build order.

### Implementation readiness
Design fully specced for build. Remaining to actually implement (repo-side, not doable from this AIOS folder):
- Generate API client: `pnpm generate:api` from swagger.json → typed openapi-fetch client.
- Wire tailwind.tokens.cjs + import tokens.css at app entry; self-host Manrope (OFL).
- Scaffold shell-first per build-sheets build order.
- Optional next here: ADO work-item breakdown (screens→Epic/Feature/Story/Task, board "Media") via ado-create-from-plan skill.

### 2026-08-12 — Coverage sweep: 9 more screens (20–28) + 3 API gaps
Cross-checked ~50 use cases + swagger against the 19 screens. Built the API-backed gaps + design-only variants; logged no-API admin screens as gaps.
- ✅ 20 create-mediaitem (POST /v1/items — profileId/title/folder/author/recordDate)
- ✅ 21 version-compare (GET /items/{id}/versions/{n} — metadata + asset diff; fixes CR #7 dead link)
- ✅ 22 move-item dialog (PUT /items/{id}/folder — folder/collection tree picker)
- ✅ 23 publish-dialog (POST /items/{id}/publish {reviewerIds} — publish-now vs assign-reviewers)
- ✅ 24 create-collection (POST /v1/collections {name,description,visibility}; folder-create noted)
- ✅ 25 confirm-dialogs family (withdraw/archive-cascade/discard-revision/force-release — reusable ConfirmDialog)
- ✅ 26 checkout-conflict (locked-by-another read-only + admin force-release)
- ✅ 27 signing-exceptions (voided DS-2 + declined DS-4 states) — design-only, GAP-3
- ✅ 28 registration-rejected (rejected→resubmit, R-2) — design variant
- ✅ Gaps 7–9 added to `Gaps/api-contract-gaps.md`: Users/roles (RBAC), tenant provisioning, storage quota — no API, design-ahead.

**Screen count now 28** (screenshots 20–28-*.png rendered on-brand). No-API admin screens (Users/tenant/quota) intentionally NOT designed — logged as gaps.

### 2026-08-12 — Browsable prototype
Generated `prototype/index.html` — single self-contained file: left-nav through all 28 screens (isolated via iframe srcdoc, no id collisions) + live Design-system page (colour swatches, Manrope type scale, radii from tokens.css). Opens by double-click in any browser; only external deps are Tabler icons + Manrope via CDN (needs internet). Regenerate: `cd screenshots/_build && node prototype.js`.
### 2026-08-12 — Prototype upgraded: offline + click-through flow
`prototype/index.html` now (485 KB, single file, verified):
- **Fully offline** — Tabler icons subset to the 116 used (878KB→22KB) + Manrope variable, both embedded as data-URI woff2 in one `<style id="fonts">` (~66KB, injected into each iframe post-load, not duplicated). 0 CDN refs. Opens by double-click with NO internet.
- **Click-through flow** — in-screen actions navigate: Upload→upload, media row→detail, View change request→CR review, version View→compare, related CR/signing/registration links, publish→CR, create→detail, back-arrows, nav-rail items, mobile tabs. Flow map in `screenshots/_build/prototype.js` (FLOW config). Parent binds handlers into each srcdoc iframe on load (same-origin).
- Offline font CSS: `screenshots/_build/fonts-inline.css` (regen via /tmp subset if icons change). Regenerate prototype: `cd screenshots/_build && node prototype.js`.
- shot.js (PNG pipeline) unchanged — still uses CDN online for screenshots.

**Ready to pick up anytime (not blocked by brand):**
- `swagger.json` now available → validate/correct field names + enums across the 19 screens against the real contract; note any drift (esp. the earlier MediaItem status-enum flag).
- User-journey map (#5) — buildable now from the ~50 use cases.
- Remaining unbuilt screens: bulk-archive confirm, tenant-switch success, admin create-new flows, notifications full-page, settings/profile.

**State of play:** 19 screens designed + screenshotted (`screenshots/01–19-*.png`). Design system foundations built (`design-system/tokens.css`, `tokens.json`, `components.md`). Medium = mockup-in-Claude. Open flags for backend: MediaItem status-enum drift, audit-log has no read endpoint (ADM-4), R-001 magiq-auth silent tenant switch.

_Rule: update this log after each operation so progress is never lost._

### Design notes captured
- MediaItem canonical status enum = Draft | PendingApproval | Published | Revising | Archived (write-model). Read-model doc drift (Rejected/Withdrawn) flagged for backend.
- Upload UX splits client-controlled % (S3 PUT) from server-side polled states (Validating→Processing→Active|Failed). Retry affordance per FailureCategory: virus=terminal, expired/processing=re-runnable.
- Open follow-ups to revisit: MediaItem detail screen, Library grid variant.

### Reference assets
- `screenshots/` — Cirrus Payroll (desktop + mobile) = brand family reference.

### Still open
- ADO board not assigned.
- Real field shapes pulled per-screen from `spec/contexts/*/*.api.md` as each screen is designed.
