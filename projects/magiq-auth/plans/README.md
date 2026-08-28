# Plans — magiq-auth

**A plan sequences findings a review already argued.** Plans mirror `reviews/`, one subfolder per
workstream, and the plan is named after its primary review — same filename, different tree. See
`CLAUDE.md § Review → Plan`.

**Status vocabulary** — `active` · `blocked` (derived from unmet dependencies, never set by hand) ·
`parked` · `superseded` · `done`. A plan is not `done` without Chase's explicit agreement plus at least
one recorded branch.

## Under the cycle

| Id | Workstream | Plan | Status | Consumes |
|---|---|---|---|---|
| — | `validateuser-lockout/` | *(not written)* | — | MA-001 — **gate shut**, 7 open questions and review not yet at `findings-agreed` |

Nothing else yet. `MA-001` is the project's first review.

## Legacy plans — no ids, no front-matter

These five predate the cycle. Per the `review-cycle` skill's § Legacy files their status is **UNKNOWN**:
do not treat any of them as met, unmet, active or done, and do not list them in a `depends-on`. The
`.done` suffix on two of them is the old convention, not front-matter — it is the only status signal
they carry.

| File | Signal | Summary |
|---|---|---|
| `claims-normalization.done` | `.done` suffix | Central `IMagiqJwtTokenFactory`; fixed the silent `JwtTokenBuilder.AddClaims` no-op; aligned claim type names across JWT and OIDC paths. |
| `client-credentials-plan.done` | `.done` suffix | OAuth2 client-credentials grant (`ApiClient` entity); fixed the hardcoded `"secret".Sha256()` across all OIDC clients. Legacy fallback still to be removed once all `AppRegistration`/`Customer` clients are confirmed rotated. |
| `tenant-switching-plan.md` | none | In progress per `CLAUDE.md`. Cookie switch (v1, built) plus the new OIDC RFC 8693 token-exchange grant for VSTO, plus audit-logging gap fixes on both mechanisms. |
| `customer-deletion-plan.md` | none | Open, with unresolved decisions: MySQL username collision on name reuse, hard-delete retention window, authorization policy tier, whether IS4 `PersistedGrant` revocation needs new wiring. |
| `external-providers-plan.md` | none | Open. Move Azure AD SSO config from `appsettings.json` to a DB-backed `ExternalProvider` table with dynamic scheme registration, no restart. |

**Backfill** — one workstream at a time, only when that workstream is next picked up, minting ids oldest
file first so the numbering reads chronologically. Offer it as a separate reviewable step. Do not
bulk-rewrite.

Three further analysis documents live in the code repo and are in the same UNKNOWN position:
`PRODUCTION_CODE_AUDIT_REPORT.md`, `AuditLogging-Separation-Plan.md`, `sync-to-async-review-plan.md`.
