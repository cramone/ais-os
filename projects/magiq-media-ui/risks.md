# Risks — magiq-media-ui

## R-001 — magiq-auth must support silent tenant switch
_Raised 2026-08-12 · design dependency · owner: TBD (magiq-auth team)_

D-006 assumes the tenant switch can re-mint an access token **silently** (no OIDC redirect). This requires `magiq-auth` to:
1. Accept a target `tenant_id` on the refresh/token-exchange call, and
2. Issue **user-scoped** refresh tokens (spanning all of a user's tenants), not tenant-scoped ones.

If magiq-auth only issues tenant-scoped refresh tokens or has no tenant param, the switch must fall back to a full OIDC redirect per tenant (visible flicker). **Confirm with the magiq-auth team before building the switch.** UI design should keep the switch abstraction swappable so a redirect fallback is a contained change.
