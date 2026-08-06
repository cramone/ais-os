# ADR-006 — Authentication: MAGIQ Piggybacking + Two-Ticket Model

**Date:** 2026-07-13  
**Status:** Accepted

---

## Context

The application needs operator authentication. Options considered:

- **Own credential store** — adds an identity system, password management, and a second login for operators who already use MAGIQ Documents.
- **Piggyback MAGIQ Documents auth** — operators authenticate with existing credentials; the app holds no passwords.

The MAGIQ Documents SOAP endpoint (`srv.asmx`) exposes `AuthenticateUser` (username + password → `AuthenticationTicket`). The ticket has a sliding 20-minute timeout. Importantly, `AuthenticateUser` returns a **new, independent ticket on every call** — multiple concurrent tickets for the same user are valid.

A secondary problem: the background pipeline (esp. Step 9 — moving tens of thousands of documents) runs beyond the operator's active session and can span hours. The UI session ticket cannot be used to authenticate background jobs, because the operator may log out mid-run.

---

## Decision

### Authentication

Piggyback MAGIQ Documents. No own credential store.

- Operator signs in with MAGIQ Documents credentials.
- API calls `AuthenticateUser` **twice in parallel** at login, obtaining two independent tickets.
- **Ticket A (UI ticket):** held in-memory for the operator's UI session. Invalidated on logout. Not persisted.
- **Ticket B (process ticket):** dedicated to the background pipeline. Persisted to the app database (see ADR-007). Independent of the UI session lifecycle.

### Authorisation

Access gated by an **admin allowlist of usernames** in `appSettings.json`. Authenticated users not on the list are denied. This is interim — a database-backed configurable store is a planned future iteration.

### Ticket Keep-Alive

The process ticket's 20-minute sliding window is kept open by a **lightweight periodic heartbeat SOAP call** (configurable interval, default 300 seconds). This covers lulls between phases, not just high-activity phases.

### Ticket Expiry Recovery

If the stored process ticket has expired (e.g. prolonged outage):
- If the operator's UI session is still active: the app calls `AuthenticateUser` automatically and replaces the stored ticket. No manual re-auth required.
- If the UI session has ended: the run enters `Failed` state. The operator logs in and triggers Retry.

---

## Consequences

- No password is stored anywhere. The app never persists credentials.
- The UI session and background pipeline are fully decoupled — the operator can log out without affecting a running job.
- The heartbeat is a lightweight operational dependency — if it fails silently, the process ticket will eventually expire. Monitor heartbeat health.
- `AdminAllowlist` in `appSettings.json` requires a config update (and app restart under IIS) to add/remove users — acceptable for an admin tool, but a future iteration should make this configurable without a restart.

---

## Amendment — 2026-08-05: run ownership (read-only to non-owners)

Decision detail in `decisions/log.md` [2026-08-05]. The admin allowlist is the *authentication/authorisation gate* (who may use the app); it is now complemented by a per-resource **ownership** check on runs.

A `CleanupRun` carries an `Owner` (initially the creator; distinct from the immutable `CreatedBy` so it can be transferred later via `CleanupRun.TransferOwnership`). A run is **read-only to any operator other than its owner**: a global FastEndpoints pre-processor (`RunOwnerPreProcessor`) short-circuits any **non-GET** request on a `{runId}` route with **`403 RunNotOwned`** unless the authenticated operator is the owner. GET/view requests are unrestricted. This makes every mutating action (and its audit attribution) provably the owner's, and gives a clean seam for future approvals / ownership-transfer. Enforcement lives in the pre-processor, not the handlers, so the vertical slices and their tests are untouched. Migration `0003` adds the column and backfills `Owner = CreatedBy`.

Open: whether an admin may act on a run they don't own (currently no — even admins are read-only on others' runs); a transfer endpoint/UI (domain method exists, no endpoint yet).
