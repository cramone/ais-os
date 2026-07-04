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

## 2026-07-03 — Control Tower hosted on Cortex, Tailscale-only

**Decision:** Deploy Control Tower as a Docker container on Cortex behind Traefik at `tower.ramonedevelopment.com`, on the `tailnet` entrypoint (not public). Deploy via manual `git pull && docker compose up -d --build` on Cortex — no registry, no CI. Cortex gets its own `/opt/ais-os` clone as the live-data publisher; Windows stays the interactive editing copy; a systemd timer auto-commits/pushes Tower's writes so Windows can pull them. Full design: `docs/superpowers/specs/2026-07-03-tower-cortex-deployment.md`.

**Why:** Every other Cortex service (Seq, Portainer, Open WebUI) is Tailscale-only despite similar public-looking hostnames — Tower holds ADO/decision/customer data and follows that existing pattern rather than becoming the first public exception. Manual deploy fits homelab scale; CI/registry is deferred until it's actually friction. Cortex-as-publisher mirrors the existing Hermes pattern (writes straight into the git-tracked repo, no JSON handoff).

**Alternatives considered:** Public exposure via the `websecure`/`public` certresolver (rejected — first non-ACME public service, unnecessary given Tailscale already covers phone/remote access). Automatic build-on-push via GitHub Actions + GHCR + Watchtower (rejected for now — adds a registry and a new always-on updater for a single-operator tool; can add later). Baking app code into the image (rejected — bind-mounting `/opt/ais-os` means code changes need only a restart, not a rebuild, and keeps runtime cleanly separated from code/data).

**Owner:** Chase

**Open items:** Claudia chat integration (`docker exec hermes ...`) won't work on Cortex — Hermes runs bare-metal there, not Docker. ADO reachability from Cortex's egress IP is unverified — test before relying on interrupt pushes.

---

## 2026-07-04 — Azure DevOps MCP: migrate to official server, host once on Cortex via supergateway

**Decision:** Replace the `RainyCodeWizard/azure-devops-mcp-server` community fork with Microsoft's official `@azure-devops/mcp` (PAT auth — org blocks Entra app registrations, so the newer Remote MCP Server is unusable anyway, and separately doesn't yet support Claude Code as a client). Host ONE instance on Cortex, stdio bridged to Streamable HTTP via `supergateway`, behind Traefik's `tailnet` entrypoint — Claude Code (Windows) and Claudia (Cortex) both connect to it instead of each spawning a local copy. Tower stays on direct REST, unaffected. Full runbook: `docs/superpowers/specs/2026-07-04-azure-devops-mcp-integration.md`.

**Why:** Single-maintainer community fork was replaced with product-backed tooling for something used daily. Shared hosting avoids running/maintaining two local stdio instances of the same server. Tailscale-only reachability matches every other service on this stack — consistent security model, not a new one.

**Alternatives considered:** Microsoft's Remote MCP Server (rejected — Claude Code/Claude Desktop unsupported due to an Entra/MCP-spec OAuth gap, not just a rollout delay). Per-machine local stdio builds on both Windows and Cortex (rejected as the primary path but kept as a documented fallback if Cortex's ADO reachability turns out not to be allowlisted).

**Owner:** Chase

**Blocking dependency:** Cortex's egress IP must be within the ADO org's IP allowlist, or this entire design fails for both consumers (not just Claudia) — verify before building (Step 0 in the runbook). Also still pending from 2026-07-03: the exposed PAT rotation.

---

## 2026-07-03 — Claudia integration on Cortex: host-side HTTP bridge, not docker.sock

**Decision:** Bridge Tower (containerized) to bare-metal Claudia on Cortex via a small stdlib-only HTTP server (`scripts/claudia-bridge/server.py`) running as its own systemd `--user` service on the host, bound to `127.0.0.1:8901`. Tower reaches it via `host.docker.internal`, mirroring the existing Open WebUI → Ollama pattern. `tower/readers/claudia.py` branches on `CLAUDIA_BRIDGE_URL`: set → bridge (Cortex), unset → original `docker exec hermes ...` (Windows dev).

**Why:** Cortex runs Claudia bare-metal via systemd, not Docker — the original `docker exec hermes ...` call has nothing to attach to. Mounting `docker.sock` into the Tower container was the alternative and was rejected: real privilege escalation (host-level Docker control from inside a container) for a minor chat feature, and it still wouldn't find a `hermes` container on Cortex. SSH-from-container was also considered and rejected in favor of the bridge — avoids managing SSH keys inside the image and duplicating Claudia's environment.

**Alternatives considered:** `docker.sock` mount (rejected — privilege escalation, wrong host model anyway). SSH from container to host (rejected — key management overhead for no real benefit over a plain HTTP bridge). Replicating the Hermes venv inside the Tower image (rejected — duplicates a working install, fragile to keep in sync).

**Owner:** Chase

**Not yet verified:** the bridge assumes `claudia chat -q "<message>" --yolo` is the correct non-interactive CLI invocation. Confirm on Cortex before enabling — see `docs/superpowers/specs/2026-07-03-tower-cortex-deployment.md`.

---

## 2026-05-03 — Azure DevOps: REST API over MCP server 1

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

## 2026-06-15 — InfoXpert SQL injection fix approach

**Decision:** Fix IXReports SQL injection via operator whitelisting + single-quote escaping rather than full parameterized query refactor.

**Why:** Parameterized queries require refactoring the OleDBDataSource execution layer — a large change to legacy code with no test coverage. Operator whitelisting closes the highest-risk vector entirely; quote escaping is the correct SQL literal defense. Risk-adjusted, the fix is correct and safe.

**Alternatives considered:** Full parameterization (deferred — flagged as outstanding recommendation). Stored procedures (not viable without schema access).

## 2026-06-15 — Security incident folder added to AIS-OS

**Decision:** Add `security-incidents/{customer}/{dd mm yyyy}/` to AIS-OS as a standing folder for recording security events across customers.

**Why:** InfoXpert incident review produced findings worth retaining for audit, future document generation, and pattern detection across customers. Lean addition — only created when an incident occurs.

**Alternatives considered:** Storing in `projects/` (not right — incidents are cross-project); storing in `references/` (not right — these are time-bound events, not reusable knowledge).

---

## 2026-06-27 — /level-up: ADO standup rollup skill (status reporting automation)

**Decision:** Build an AI-assisted skill `standup-rollup` that turns the current ADO iteration into a stakeholder-ready status draft in Chase's voice.

**Why:** Top weekly pain = ADO task overhead; the specific drain (confirmed via /level-up Mindset interview) is *reporting status up/out* — translating raw ADO items into prose for standup/stakeholders. Data pull is already solved (`scripts/devops_summary.py --all --sprint --json`); the leverage is the prose translation. Automating the draft cuts time-to-report from ~35 min to <5 min review.

**Method spec (3Ms):**
- Trigger: weekly (Fri / pre-standup) + on-demand
- Source: ADO current iteration, all assignees — `devops_summary.py --all --sprint --json`
- Transform: group by area/module theme × state; surface blockers + Code Review queue
- Decision points: what to surface vs drop; flag risks/blockers
- Destination: markdown draft → Chase reviews/edits → Teams/email
- **Autonomy: L2 Drafted** — AI drafts, human edits before send. L4 prohibited: CLAUDE.md forbids external comms in Chase's voice without a draft first.
- **KPI: Less cost** — time-to-status-report, ~35 min → <5 min.

**EAD:** Not eliminable (lead comms required), not delegable (Chase's voice). Automate, 60/30/10.

**Alternatives considered:** Deterministic-only skill (rejected — produces a raw list, not the prose summary that is the actual pain). Sub-agent (rejected — overkill; single AI draft step suffices). Candidate 1 (daily triage brief) and Candidate 3 (intake formatter) deferred — Chase picked status reporting as the top drain.

**Owner:** Chase Ramone

**Bike Method:** Phase 1 (manual run first).

*Adapted from The Three Ms of AI™ © 2026 Nate Herk.*
