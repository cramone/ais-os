# Decision Log — magiq-media-ui

---

## 2026-08-12 — UI design kickoff: shell, tenancy, visual direction

**Context:** Beginning frontend design work in Claude (mockup-first). Project folder was scaffold-only; backend `magiq-media` spec at `D:\source\github\magiq-media\docs` is the domain source of truth (7 modules, ~50 use cases, 14 ADRs).

### D-001 — Tenant identity from JWT only, never in the URL
Tenant is **not** represented in the URL (no subdomain, no path segment). Tenant is resolved from the JWT `tenant_id` claim and applied server-side to scope all API responses.

- **Why:** Aligns exactly with backend contract — `TenantId` is sourced from the JWT `tenant_id` claim, never from payload/URL (magiq-media brief, `auth-and-security.md`). No tenant identifier in the URL to tamper, leak, or desync. Simpler routes.
- **Implication:** A multi-tenant user switches tenant by **token re-issue** (re-auth against the target tenant), not by navigation. On switch: swap in-memory access token → invalidate all TanStack Query caches → render processing state → refetch. Single-tenant users get a static tenant display, no switcher.
- **Supersedes:** the open "multi-tenancy in the URL: subdomain vs path segment" question in CLAUDE.md — resolved as *neither*.

### D-002 — Visual direction: MAGIQ (Cirrus) family DNA, evolved for media
Base the visual language on the existing MAGIQ product family (Cirrus Payroll screenshots as reference), then evolve it for media-library content.

- **Keep (family DNA):** dark navy top chrome, blue primary accent (~`#378ADD`), light card canvas, thin hairline borders, gov-grade restraint, sectioned left nav rail, cursor-style data pagination.
- **Evolve (media-specific):** thumbnail/grid browse (Cirrus is form-heavy), asset processing states as first-class UI, denser tree nav for collection/folder hierarchy, sandboxed preview surfaces.
- **Why:** Consistency across the MAGIQ suite for existing customers; media domain needs visual browse Cirrus never had.

### D-003 — Ingestion states are first-class UI
Model all four ingestion states explicitly in the UI: `pending → processing → available | failed` (plus domain states like `in review`). Each gets a distinct visual treatment (chip + icon; spinner for processing).

- **Why:** Read model lags writes — the largest source of frontend bugs against this backend (CLAUDE.md). After a mutation: invalidate + render explicit processing state; poll with backoff; announce via polite live region.

### D-004 — Cursor pagination in UI, no page numbers / totals
Lists use cursor-based "Load more" affordance. No page numbers, no total counts assumed.

- **Why:** Backend is cursor-only, no total count (ADR-014).

### D-005 — App shell designed first
Design order: **app shell → tenant switch → library browse → upload → mobile**. Shell = navy top chrome (logo, tenant display, global search + ⌘K palette, notify/help/user), collapsible left nav rail (Library, Search, Uploads, Change requests, Registrations, Signing + Admin group: Record types, Media profiles, Users, Audit), content frame (breadcrumb, page header + actions, content slot), global processing live region.

- **Why:** Shell is the frame every screen sits in; settle chrome, nav taxonomy, and global patterns before per-screen design.

### Nav taxonomy — backend module → user-facing section
| Backend module | UI section |
|---|---|
| Catalog (Collection/Folder/MediaItem) | Library |
| (OpenSearch read layer) | Search |
| AssetManagement | Uploads |
| ChangeRequests | Change requests |
| Registration | Registrations |
| DocumentSigning | Signing |
| Metadata (RecordType) | Admin › Record types |
| Catalog (MediaProfile) | Admin › Media profiles |
| (Tenant/RBAC) | Admin › Users |
| (Audit log) | Admin › Audit |

---

## 2026-08-12 — Tenant switch flow

### D-006 — Silent tenant switch via user-scoped refresh token
Switching tenant re-mints the access token **silently** — no OIDC redirect. The UI calls the `magiq-auth` token endpoint with the target `tenant_id`; `magiq-auth` returns a new access token carrying the swapped `tenant_id` claim. Refresh token is **user-scoped** (spans all of the user's tenants), stays in the httpOnly cookie.

- **Why:** Best UX — no redirect flicker on every switch. Consistent with memory-only access token (15-min TTL, auth ADR).
- **Switch sequence:** mint new access token → invalidate **all** TanStack Query caches (prior data was tenant-scoped) → reset tenant-scoped client state (palette, filters, selection) → navigate to Library root (old-tenant deep-link IDs return `404` under structural cross-tenant isolation — never restore the old route) → announce via polite live region.
- **Selector:** shown only when the user belongs to >1 tenant; single-tenant users get a static tenant display.
- **Upload guard:** active in-flight uploads block a silent switch. A tenant switch is a session boundary — the upload queue (which otherwise survives in-tenant navigation, per CLAUDE.md) cannot continue or resume in the new tenant. Confirm dialog: "Stay and finish" vs "Switch anyway" (destructive).
- **Creates dependency:** `magiq-auth` must support a `tenant_id` parameter on the refresh/token exchange and issue user-scoped (not tenant-scoped) refresh tokens. See `risks.md`. Resolve with the magiq-auth team before build.
