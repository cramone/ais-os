# magiq-media-ui

## Project Overview
Frontend UI application for the magiq-media project. Client-only React SPA consuming the `magiq-media` REST API. No SSR, no BFF — the browser talks directly to the API.

Serves records officers, administrators, and end users in government and enterprise tenants. Domain covers media, document, and records management — ingestion, storage, search, retrieval, classification, retention and disposition, audit.

**Current status:** Active
**Priority:** Medium

## Related Repos

| Repo | Location | Notes |
|------|----------|-------|
| `magiq-media-ui` | Frontend repo (separate, not directly accessible from here) | This repo — React SPA |
| `magiq-media` | `../magiq-media` | Backend API — OpenAPI spec is the contract |

> The API spec lives in `../magiq-media/docs`. This repo never redefines it — the client is generated from it via `pnpm generate:api`.

## Stack

| Layer | Technology |
|---|---|
| Framework | React 19.2 (React Compiler enabled) |
| Language | TypeScript (`strict: true`) |
| Build | Vite |
| Routing | TanStack Router — file-based, typed params |
| Server state | TanStack Query |
| Client state | Zustand — one store per concern, UI only |
| Styling | Tailwind CSS with design system tokens |
| Forms | React Hook Form + Zod |
| API client | `openapi-typescript` + `openapi-fetch` (generated) |
| Testing | Vitest + Testing Library, Playwright (E2E), MSW (network mocking) |
| Package manager | pnpm — single lockfile, do not mix |

**React 19 specifics:** `ref` is a plain prop — no `forwardRef`. Use `useActionState` / `useOptimistic` for submission state. Do **not** add `useMemo`, `useCallback`, or `React.memo` — the compiler handles memoisation.

## Commands

```bash
pnpm dev            # local dev server
pnpm build          # production build
pnpm test           # unit tests (watch: pnpm test --watch)
pnpm test:e2e       # Playwright
pnpm lint           # eslint + prettier check
pnpm typecheck      # tsc --noEmit
pnpm generate:api   # regenerate the API client from ../docs OpenAPI spec
```

`pnpm typecheck` and `pnpm lint` must pass before any task is considered done.

## Project Structure

```
src/
├── routes/        # TanStack Router route files — composition and data loading only
├── features/      # vertical slices: component + hooks + schema + tests co-located
│   ├── media/
│   ├── search/
│   ├── upload/
├── components/    # shared primitives — no feature or domain knowledge
├── lib/
│   ├── api/       # generated client + typed wrappers
│   ├── auth/
│   ├── query/     # query client config, key factories
│   └── telemetry/
└── styles/
```

- Features never import from other features. Shared code moves up to `components/` or `lib/`.
- No barrel `index.ts` re-export files.
- Tests sit next to the code they test.

## ADO Board
Media

## Key Conventions

### State tiers
1. **Server state** — TanStack Query. Anything the API owns.
2. **URL state** — TanStack Router search params. Filters, sort, pagination, selected item, open tab.
3. **Client state** — Zustand. Ephemeral UI only: upload queue, command palette, unsaved draft buffers.

Never copy server data into Zustand.

### API integration
- Client is **generated** from the OpenAPI spec — never hand-edit or bypass with raw `fetch`.
- Regenerate when spec changes; commit the diff as its own commit.
- Query keys come from per-feature key factories (`documentKeys.detail(id)`), never inline arrays.
- Mutations invalidate — they do not patch server-derived state by hand.
- Pagination is cursor-based. Don't assume total counts or page numbers.

### Eventual consistency
The read model lags writes — the largest source of frontend bugs against this backend.
- After a mutation, invalidate affected queries and render an explicit **processing** state.
- `useOptimistic` only for state the client fully owns — never for server-assigned values (IDs, version numbers, computed retention dates, ingestion status).
- Ingestion is async: `pending → processing → available | failed`. Model all four states.
- Poll with backoff for processing items. Stop on unmount and tab blur.

### Auth
- OIDC authorisation code flow with PKCE.
- Access token in memory only. Refresh token in httpOnly SameSite cookie. Nothing in `localStorage` / `sessionStorage`.
- Single interceptor: 401 → silent refresh → retry once → redirect to login.
- 403 is not 401 — render permission-denied, do not redirect to login.

### Uploads & files
- Uploads go **direct to storage** via presigned URLs. File bytes never pass through app state.
- Multipart/chunked with per-chunk retry and resume.
- Upload queue lives outside component state — navigation does not cancel it.
- Never render an uploaded document inline as HTML. Use sandboxed viewer (PDF in worker, `<img>`/`<video>` with explicit types, sandboxed iframe). SVG is executable — treat as hostile.
- Downloads via short-lived signed URLs. Do not proxy bytes through the SPA.

### Lists & search
- Virtualise any list exceeding ~100 rows (TanStack Virtual).
- Search state lives in the URL — shareable, bookmarkable, survives refresh.
- Debounce search input at 300ms; cancel in-flight requests on change.

### TypeScript
- No `any`. No non-null assertions (`!`). Use `unknown` and narrow.
- Domain types derive from generated spec types — no hand-written duplicates.
- Branded types for identifiers (`DocumentId`, `RecordId`, `ContainerId`).
- Discriminated unions for anything with modes (ingestion status, retention status).

### Security
- No secrets in `VITE_`-prefixed env vars — everything prefixed `VITE_` is public.
- No tokens or document data in `localStorage`, `sessionStorage`, or IndexedDB.
- No `dangerouslySetInnerHTML` without reviewed justification and sanitisation.
- Permission-gated UI is a convenience, not a control — the server enforces authorisation.
- Strict CSP with no `unsafe-inline`.

### Accessibility
WCAG 2.2 AA — non-negotiable for government procurement.
- Semantic HTML first. ARIA only where semantics run out.
- All interactive elements keyboard-reachable with visible focus ring.
- Real `<label>` elements. Icon-only buttons get accessible names.
- Async results announced via polite live region.
- `axe` runs in CI and fails the build on violations.
- Respect `prefers-reduced-motion`.

### Testing
- Test behaviour through the DOM — not implementation details or snapshot markup.
- Mock at the network boundary with MSW. Do not stub hooks.
- Every feature needs at least one failure-path test.
- Coverage floor 70%, enforced in CI (route files and generated code excluded).

### Git & ADO
- Branch: `feature/{ADO-id}-short-description`
- Commit messages reference the ADO work item ID.
- PRs stay small and single-purpose. Contract regeneration, refactors, and behaviour changes are separate PRs.
- Required to merge: typecheck, lint, unit tests, axe, one reviewer.

## Do Not
- Add a dependency without stating the problem and alternatives first.
- Refactor adjacent code while fixing a bug (separate PR).
- Add a second data-fetching or state library.
- Bypass the generated API client.
- Add `useMemo` / `useCallback` / `React.memo`.
- Create files the task doesn't require.

## Open Decisions
- Multi-tenancy in the URL: subdomain per tenant vs. path segment.
- Whether `components/` eventually becomes a shared package across other MAGIQ UIs.
- Offline behaviour beyond upload resume — currently out of scope.
- Dark mode: in or out of scope for v1.

## File Map

| File | Purpose |
|------|---------|
| `brief.md` | Project summary and constraints |
| `notes.md` | Open question resolutions and session notes |
| `risks.md` | Risk register |
| `decisions/log.md` | Architecture and design decisions (append-only) |
| `adrs/` | Formal ADRs for architectural decisions |
| `spec/` | Spec files |
| `frontend-CLAUDE.md` | Source CLAUDE.md from the frontend repo (read-only reference) |

## Decisions

All architecture and design decisions go in `decisions/log.md`.
Formal ADRs go in `adrs/`.

---

## Memory System

This folder contains `MEMORY.md` — external memory for this project.

At the start of every session: Read `MEMORY.md` before responding. Use what you find — do not announce it.

Memory is user-triggered only. Only add entries when the user explicitly asks using phrases like "remember this", "make a note", "log this". Write immediately and confirm.

All memories are persistent until the user asks to remove or change them.

Flag contradictions — never silently overwrite.
