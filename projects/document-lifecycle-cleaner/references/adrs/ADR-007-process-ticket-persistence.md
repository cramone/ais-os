# ADR-007 — Process Ticket Persisted in App Database

**Date:** 2026-07-13  
**Status:** Accepted  
**Supersedes:** The "accepted limitation" in the two-ticket model decision (decisions/log.md 2026-07-13) which treated mid-run IIS recycles as requiring re-authentication.

---

## Context

The two-ticket model (ADR-006) obtains a dedicated process ticket at login for the background pipeline. The question: where is this ticket stored?

- **In-memory only** — simple, but an IIS recycle or app restart mid-run loses the ticket. The operator would need to re-authenticate to resume the background job. For a process that can run for hours across tens of thousands of document moves, this is a real operational risk.
- **App database** — one row on the `CleanupRun` record. Survives restarts. Requires no stored password.

The only scenario where database persistence fails to help is a **downtime exceeding the 20-minute sliding window** — a normal IIS recycle (seconds) is well within this window.

---

## Decision

Store the **process ticket in the dedicated app database**, associated with the `CleanupRun` record:

- `CleanupRun.ProcessTicket` — the SOAP auth ticket string.
- `CleanupRun.ProcessTicketObtainedAt` — timestamp for expiry reasoning.

On application startup, if a `CleanupRun` is in a non-terminal state:
- Reload the stored process ticket.
- Resume the heartbeat timer.
- Continue the background job (Hangfire re-queues automatically on restart).

The **UI ticket is not persisted** — it does not need to survive a recycle. If the app restarts, the operator re-authenticates for the UI only.

---

## Consequences

- Mid-run IIS recycles no longer require operator re-authentication — the accepted limitation from the prior decision is eliminated.
- A normal recycle (seconds to low tens of seconds) will always fall within the 20-minute window; the stored ticket will still be valid on resume.
- A prolonged outage (>20 minutes) still expires the ticket. This is handled by the expiry recovery path in ADR-006 — not a restart problem, a network-outage problem.
- No password is persisted at any point. The ticket is a short-lived opaque credential issued by the platform; persisting it is no different in risk profile from a session token.
