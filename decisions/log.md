# Decisions Log

Append-only record of meaningful decisions and why they were made. `/level-up` Phase 2 (Method interview) writes scoped automation specs here. You can also append manually whenever you decide something worth remembering.

**Format per entry:**

```
## YYYY-MM-DD — Short title

**Decision:** what was decided.

**Why:** the reasoning, constraints, and what would change your mind.

**Alternatives considered:** what else was on the table.

**Owner:** who's accountable.
```

Keep it terse. Future-you will thank present-you for capturing the *why*, not just the *what*.

---

## 2026-05-03 — Azure DevOps: REST API over MCP server

**Decision:** Connect to Azure DevOps via direct REST API calls (PAT auth) rather than an MCP server.

**Why:** MCP servers load full context on every call — token-heavy. Direct API calls return only what's queried. AIOS is token-cost-sensitive.

**Alternatives considered:** Azure DevOps MCP server (community-maintained). Rejected: token overhead, additional dependency, same capability via REST.

**Owner:** Chase Ramone

---

## 2026-05-03 — M365 (Outlook/Teams): deferred — org blocks app registration

**Decision:** Skip Outlook and Teams connection for now.

**Why:** Org policy blocks creating Entra app registrations. Azure CLI is blocked from requesting Mail/Calendar scopes (Microsoft first-party-to-first-party restriction). Microsoft Graph PowerShell is the only remaining path but requires interactive login each session — not suitable for automation.

**Alternatives considered:** Azure CLI token (blocked at scope level), Power Automate (wrong tool — cloud-only, no local integration), token reuse from desktop apps (unsupported, security risk).

**Revisit when:** Org relaxes app registration policy, or a supported delegated auth path emerges that doesn't require registration.

**Owner:** Chase Ramone

---

## 2026-05-03 — Notion: REST API over MCP server

**Decision:** Connect to Notion via direct REST API (internal integration token) rather than MCP server.

**Why:** Same rationale as DevOps — direct API is token-efficient, no server process, full control over what's queried.

**Alternatives considered:** Notion MCP server (official). Rejected: token overhead, same capability via REST.

**Owner:** Chase Ramone

---

## 2026-05-03 — AIOS tool connections strategy: API-first, token-efficient

**Decision:** For all tool connections, prefer direct REST API over MCP servers unless the MCP server provides capability not available via REST.

**Why:** MCP servers load schemas and context on every call. At scale across multiple tools this compounds token usage significantly. Direct API calls are surgical — return exactly what's asked.

**Owner:** Chase Ramone

---

## 2026-05-24 — Context Bridging via Claude Personal Preferences

**Decision:** Bridge AIS-OS context into Claude chat sessions by maintaining a generated
`context/claude-personal-preferences.md` and pasting its contents into Claude Settings →
Instructions for Claude.

**Why:** Claude chat has no file system access between sessions. Personal Preferences is the
only persistent injection point. Stable context (identity, priorities, stack, team) belongs
there; volatile context (task state, decisions) is fetched live.

**Alternatives considered:** Paste-on-demand at session start — rejected, too manual and easy
to forget.

**Owner:** Chase Ramone

---

## 2026-05-24 — Azure DevOps Chat Access Blocked by Org IP Allowlist

**Decision:** Azure DevOps REST API cannot be called from Claude chat interface — org IP
allowlist blocks external hosts. DevOps visibility is Claude Code only.

**Why:** All API calls from Anthropic's cloud return "Host not in allowlist". PAT scopes and
credentials are valid; the block is network-level, not auth-level.

**Alternatives considered:** Zapier webhook bridge, local proxy script — deferred, complexity
not justified when Claude Code already handles it cleanly.

**Revisit when:** Org relaxes IP allowlist, or a supported proxy path emerges.

**Owner:** Chase Ramone

---

## 2026-05-24 — DevOps Visibility Lives in Claude Code, Not Chat

**Decision:** Azure DevOps task visibility is handled in Claude Code sessions via
`scripts/devops_summary.py` and the `/devops` skill. Chat assistant handles scheduling,
memory, and comms.

**Why:** Claude Code runs on Chase's machine with full network access. Chat runs on Anthropic's
cloud and is blocked by the org IP allowlist. Clear separation of concerns.

**Alternatives considered:** Option A (paste output manually), Option B (local proxy), Option D
(Zapier bridge) — all rejected in favour of Claude Code as the natural fit.

**Owner:** Chase Ramone

---

## 2026-05-30 — CR-First Checkout Model for Media Item Version Control

**Decision:** Change request intent is declared at checkout time — actor decides upfront
whether the checkout includes a CR with reviewers, or is a solo checkout.

**Why:** Regulated records require a CR trail from the moment changes begin, not after.
Declaring intent at checkout enforces this and keeps the model auditable.

**Alternatives considered:** Review elected at checkin time (Option B — explicit submit step),
review driven by profile-level ReviewPolicy only (current model).

**Owner:** Chase Ramone

---

## 2026-05-30 — Defer "Add CR to Existing Checkout" Feature

**Decision:** Adding a change request to an already-open solo checkout is deferred as a
future feature — checkout type is fixed at the time of checkout.

**Why:** Decision at checkout is simpler and sufficient for current requirements. The data
model (CR FK on checkout record) supports the feature without breaking changes when needed.

**Alternatives considered:** Allow AddChangeRequestToCheckoutCommand now — rejected as
unnecessary complexity for Q2.

**Owner:** Chase Ramone

**Revisit when:** A concrete use case requires CR addition post-checkout.

---

## 2026-05-30 — No Self-Review on Change Requests

**Decision:** Reviewer must be a different user from the CR initiator — self-review is prohibited, hard rule.

**Why:** CR exists to get a second set of eyes in a regulated records context. Self-approval defeats the purpose and breaks compliance intent. `ReviewerIsInitiator` error already partially modeled.

**Alternatives considered:** Profile-driven self-review (some profiles allow it) — rejected as unnecessary complexity; all current profiles are regulated.

**Owner:** Chase Ramone

---

## 2026-05-30 — Checkin Without Submit Requires Explicit Abandon

**Decision:** If actor checks in but never submits, the CR stays `CheckoutBound` indefinitely until explicitly abandoned by the actor or force-released by an admin.

**Why:** No background jobs or timeouts needed. Explicit abandon keeps the model simple and auditable. Timeout can be added later without breaking the model.

**Alternatives considered:** Auto-abandon after N days (needs scheduler), atomic checkin+submit (removes flexibility).

**Owner:** Chase Ramone

**Revisit when:** Ops sees orphaned CRs becoming a real problem in production.

---

## 2026-05-30 — ForceReleaseCheckout Auto-Abandons Active CR

**Decision:** `ForceReleaseCheckout` automatically abandons the `CheckoutChangeRequestId` CR if one is present.

**Why:** Force-release is a corrective action — the checkout intent is dead, so the CR intent is dead too. Auto-abandon keeps state clean with no extra API surface.

**Alternatives considered:** CR survives force-release (ambiguous state), admin flag on command to control it (unnecessary complexity).

**Owner:** Chase Ramone

---

## 2026-05-30 — ReviewPolicy Enforced at Checkout Not Submit

**Decision:** `CheckOutMediaItemHandler` reads `ReviewPolicy`; profiles with `RequiredForPublish` reject `WithChangeRequest = false` at checkout time.

**Why:** Failing early is better — actor knows upfront they need reviewers, not after doing all the work. Keeps CR-first model honest.

**Alternatives considered:** Enforce at submit time (recoverable but late failure, actor wastes effort).

**Owner:** Chase Ramone

---
