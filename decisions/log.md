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

---

## 2026-07-05 — Admin-UI gap fill: Uptime Kuma, CloudBeaver, Traefik dashboard, Homepage

**Decision:** Added four services to cortex's `docker-compose.yml` to close gaps found in an audit of tailnet admin UIs: Uptime Kuma (`status.ramonedevelopment.com`) for uptime/availability history, CloudBeaver (`sql.ramonedevelopment.com`) as a web SQL client for MySQL + SQL Server (previously TCP-only), Traefik's built-in dashboard (`traefik.ramonedevelopment.com`, via `--api.dashboard=true` + `api@internal`), and Homepage (`home.ramonedevelopment.com`) as a landing page for all tailnet subdomains.

**Why:** Netdata covers resource pressure but not per-service up/down history (Kuma). MySQL/SQL Server had no browser-based admin tool (CloudBeaver). Traefik's routing table grew past what's easy to reason about from logs alone once ADO MCP, Tower, Kuma, and CloudBeaver all started routing through it (dashboard). Nine-plus tailnet subdomains is past the point of reliably remembering them (Homepage).

**Homepage over Dashy:** both are YAML-config, git-trackable. Homepage supports Docker-label auto-discovery (`homepage.*` labels alongside the `traefik.*` labels already written for routing) — a new service's dashboard tile is the same edit as adding its routing labels, no second file to maintain. Dashy's differentiator is an in-browser drag-and-drop config editor, which doesn't solve a real problem here since direct YAML editing is already this project's norm.

**Pattern followed:** all four use the same tailnet-only Traefik entrypoint + §10.3b real-cert-via-public-ACME pattern as every existing service. No new security model introduced. Homepage's config bind-mounts into the magiq repo itself (`homepage-config/`), same convention as Tower's bind mount — editable directly, versioned with everything else.

**Alternatives considered:** Grafana/Prometheus for monitoring (rejected — Netdata already covers metrics, a second monitoring stack contradicts the resource-contention priority baked into this whole project). Adminer instead of CloudBeaver (rejected — Adminer doesn't support SQL Server, would need two separate tools instead of one).

**Owner:** Chase Ramone

**Full detail:** `AI-X1-Pro-Setup-Guide.md` Stages 18–21.

---

## 2026-07-05 — Secrets extracted from docker-compose.yml to local-only .env

**Decision:** Removed literal password values (`MYSQL_ROOT_PASSWORD`, `SA_PASSWORD`, CIFS `shared_data` password) from `docker-compose.yml` entirely, replaced with `${VAR}` references. Real values now live only in `~/stack/.env` on cortex — never on the `/mnt/shared/claudia/magiq` NAS share, never in anything an AI session reads.

**Why:** The share copy of `docker-compose.yml` had these hand-redacted to `xxxx`/`xxx` specifically to keep secrets away from Claude/Cowork sessions doing routing edits. That redaction was the actual reason `~/stack/docker-compose.yml` and the share copy stayed as two manually-synced files instead of a symlink — and the manual sync silently fell out of date, causing real routing regressions (Seq and Portainer 404s, Traefik dashboard cert failure) after the 2026-07-05 admin-UI additions. Variable substitution removes the reason for the two-copy setup entirely.

**Alternatives considered:** Keep manual copy process but make it more careful (rejected — same single point of failure, just slower to fail). Docker secrets / external secret store (rejected — adds infra for a single-operator box where a local `.env` file already fully satisfies "never exposed to the AI editing the routing file").

**Follow-up enabled:** `~/stack/docker-compose.yml` can now be safely symlinked to the share copy (Stage 22.4) — same "single NAS share, not git-sync between clones" principle already applied to Tower and mcp-azure-devops, now extended to the compose file itself.

**Owner:** Chase Ramone

**Full detail:** `AI-X1-Pro-Setup-Guide.md` Stage 22.

---

## 2026-07-05 — docker-compose.yml relocated to cortex/ subfolder, symlinked from ~/stack

**Decision:** Moved `docker-compose.yml` and `.env.example` out of the magiq repo root into a new `cortex/` subfolder (`/mnt/shared/claudia/magiq/cortex/`). `~/stack/docker-compose.yml` on cortex becomes a symlink to `cortex/docker-compose.yml` on the share instead of a manually-synced copy.

**Why:** Follow-on to the same-day secrets-extraction decision (docker-compose.yml → ${VAR} substitution). With secrets fully out of the compose file, the manual-copy step between `~/stack` and the share was pure liability with no remaining upside — a symlink removes the single point of failure that caused the Seq/Portainer/Traefik-dashboard drift bug. Grouping the file under `cortex/` alongside its own `.env.example` also keeps cortex-Docker-stack-specific files out of the repo root, separate from AIOS's own files.

**Confirmed safe:** every path inside docker-compose.yml is already absolute (`/mnt/shared/claudia/magiq/...`), none relative to the compose file's own location — the move required zero changes to the file's contents.

**Owner:** Chase Ramone

**Full detail:** `AI-X1-Pro-Setup-Guide.md` Stage 22.2–22.5.

---

## 2026-07-05 — Seq requires SEQ_FIRSTRUN_ADMINPASSWORD (Seq 2025.2.x behavior change)

**Decision:** Added `SEQ_FIRSTRUN_ADMINPASSWORD` as a required secret (via `${VAR}` substitution, same pattern as the MySQL/SQL Server/CIFS passwords) to the `seq` service.

**Why:** The `seq` container was crash-looping on boot with `No default admin password was supplied; set firstRun.adminPassword or SEQ_FIRSTRUN_ADMINPASSWORD, or opt out of authentication using firstRun.noAuthentication/SEQ_FIRSTRUN_NOAUTHENTICATION`. Seq 2025.2.x (the current `datalust/seq:latest`) requires this explicitly — the original Stage 10.3 setup never set it because older Seq versions allowed interactive admin account creation via the browser on first load. Because the container never stayed up, Traefik's Docker provider never got a stable container to register a router for, which surfaced as `router not found: seq@docker` — not a routing or labels bug, a downstream symptom of Seq itself failing to start.

**Chose real admin password over `SEQ_FIRSTRUN_NOAUTHENTICATION=true`:** matches the defense-in-depth posture already used for Open WebUI (`WEBUI_AUTH=true`) and Portainer (own admin account) — both already have their own auth layer on top of Tailscale-only reachability, not just Tailscale alone.

**Owner:** Chase Ramone

**Full detail:** `AI-X1-Pro-Setup-Guide.md` Stage 22.1, `cortex/.env.example`.

---

## 2026-07-05 — Explicit loadbalancer port required for multi-port images (Seq, Portainer)

**Decision:** Added `traefik.http.services.<name>.loadbalancer.server.port` labels to `seq` (port 80) and `portainer` (port 9000) — the two services in this file whose images expose multiple ports and had no explicit port label.

**Why:** Seq's router registered correctly in Traefik (confirmed via `/api/http/routers/seq@docker`) but still 404'd. Checking `/api/http/services/seq-stack@docker` would have shown Traefik's auto-selected backend port — Seq's image exposes four ports (80 plain UI, 443 TLS UI, 5341 plain ingestion, 45341 TLS ingestion) and without an explicit label, Traefik's docker provider has to guess which one is the actual web UI, and got it wrong. Portainer has the identical exposure pattern (8000 edge agent, 9000 plain UI, 9443 TLS UI) and was fixed proactively before it caused the same symptom.

**Pattern going forward:** any service whose image `EXPOSE`s more than one port needs an explicit `loadbalancer.server.port` label — don't rely on Traefik's auto-detection for those. Single-port images (Open WebUI, Tower, CloudBeaver, Kuma, mcp-azure-devops — the latter three already had explicit labels anyway) aren't at risk from this specific bug, but there's no real downside to labeling explicitly across the board going forward.

**Owner:** Chase Ramone

**Full detail:** `AI-X1-Pro-Setup-Guide.md` Stage 22.1 area / `cortex/docker-compose.yml` inline comments.

---

## 2026-07-13 — Authentik added as the identity provider (SSO) for the cortex stack

**Decision:** Added Authentik (`authentik-postgresql` + `authentik-server` + `authentik-worker`) to `cortex/docker-compose.yml` at `login.ramonedevelopment.com`, tailnet-only, `public` cert resolver — same pattern as every other admin UI. Purpose: one identity for the tailnet admin fleet.

**Integration split:**
- **Forward-auth (embedded outpost)** for the three UIs that had *no login of their own* — `homepage`, `redis-stack` (RedisInsight), and the Traefik dashboard. A reusable `authentik` forwardauth middleware is defined once on `authentik-server`; each protected host gets `middlewares=authentik@docker` plus a sibling `-outpost` router for the `/outpost.goauthentik.io/` callback path.
- **Native OIDC (follow-up, not in compose)** for the self-login apps — `portainer`, `seq`, `open-webui`, `cloudbeaver`, `uptime-kuma`. Stacking forward-auth on those = double login; OIDC federates the account instead. Configured per-app in the Authentik UI after first boot (needs providers minted first, so it can't live in the compose file).

**Deliberately excluded:** `mcp-azure-devops` (machine API — a browser redirect breaks the MCP client), `netdata` (`network_mode: host`, bypasses Traefik entirely — a Traefik middleware can't reach it; stays ufw+tailnet-locked), `tower` (its own `TOWER_TOKEN` bearer auth + programmatic API), and Authentik itself.

**Redis reused, Postgres new:** Authentik hard-requires PostgreSQL and the stack had none (only mysql + mssql) — hence a dedicated `authentik-postgresql`. Redis is *not* dedicated: Authentik points at the existing `redis-stack` (DB 0), which nothing else in the stack wires an app to. Chose reuse over a dedicated redis container to honor the lean-by-default rule; minor coupling accepted (a manual redis-stack flush would drop Authentik sessions).

**host-net Traefik gotcha (why the loopback publish exists):** `traefik` runs `network_mode: host`, so it is NOT on the compose bridge network and cannot resolve `authentik-server` by Docker service name for the forward-auth sub-request. Fix: publish the server on `127.0.0.1:9000:9000` (host loopback only, never tailscale/public) and point the middleware at `http://127.0.0.1:9000/outpost.goauthentik.io/auth/traefik`. Normal UI routing is unaffected — Traefik's docker provider dials the container's bridge IP directly, same as tower/portainer.

**Hostname:** `login.ramonedevelopment.com`. `auth.` intentionally avoided — reserved for the future `magiq-auth` migration off the Windows box. No DNS/cert change needed: dnsmasq already wildcards `*.ramonedevelopment.com` to cortex and DNS-01 mints the cert on demand.

**Ordering caveat:** the forward-auth labels are inert until a Proxy Provider + Application exist in the Authentik UI for each protected host. Until then that host 302-loops — expected, not a routing bug.

**Secrets added** (`cortex/.env.example`, real values only in `~/stack/.env`): `AUTHENTIK_SECRET_KEY`, `AUTHENTIK_PG_PASS`, `AUTHENTIK_BOOTSTRAP_PASSWORD`, optional `AUTHENTIK_TAG` (default 2025.12).

**Owner:** Chase Ramone

**Full detail:** `cortex/docker-compose.yml` inline comments, `C:\Users\chase\.claude\plans\kind-squishing-bubble.md`.

**Amendment 2026-07-13 (same day):** switched the forward-auth group from single-application to **domain-level** per operator request ("one login for the entire domain and all its apps"). Removed the per-host `homepage-outpost` / `redisinsight-outpost` / `traefik-outpost` routers — domain-level serves `/outpost.goauthentik.io/` centrally on `login.` and shares one `ramonedevelopment.com` session cookie. Each protected host now carries only `middlewares=authentik@docker`. Authentik side = a SINGLE proxy provider (Forward auth → domain level, cookie domain `ramonedevelopment.com`) bound to the embedded outpost. Self-login apps (portainer/seq/open-webui/cloudbeaver) still reach seamless single-login only via native OIDC (phase 2b) — stacking forward-auth on them would double-prompt.

**Amendment 2026-07-13 (same day, #2):** reverted the forward-auth group from domain-level BACK to **single-application**. Domain-level forward auth is broken on non-443 ports (authentik issue #12503): the tailnet entrypoint is `:8443`, so the browser Host header carries `home.ramonedevelopment.com:8443`, which fails the outpost's cookie-domain suffix match against `ramonedevelopment.com` — the request falls through to the authentik core and returns 404 (confirmed via `logger=authentik.asgi ... host=...:8443 ... status=404`). Single-application mode matches by exact `external_host` (including `:8443`), so it works. Restored the per-host `homepage-outpost` / `redisinsight-outpost` / `traefik-outpost` routers. Cost: one Authentik proxy provider + application per protected host (vs. one for the whole domain) and separate per-app cookies — but the UX is still effectively single sign-on (one credential entry at Authentik; subsequent apps pass through the existing Authentik session). "One login for the whole domain" as a single shared proxy cookie is not achievable while everything runs on `:8443`.

**Amendment 2026-07-14:** moved the tailnet Traefik entrypoint from `100.90.195.22:8443` to `100.90.195.22:443` and re-adopted **domain-level** forward auth (reverting the single-app amendment above). Rationale: domain-level forward auth needs the default HTTPS port so the browser Host header has no `:port` (authentik #12503). To free `:443` on the tailscale IP, the public `websecure`/`web` entrypoints were pinned from all-interfaces (`:443`/`:80`) to the LAN NIC IP (`192.168.0.253:443`/`:80`, enp196s0) — transparent to the router's existing port-forward, keeps whoami-test/future magiq-auth public. Tailnet services stay tailnet-only (still bound to the tailscale IP alone), now reached without the `:8443` suffix. Swept `:8443` out of every `homepage.href` tile, the Authentik href, mcp-ado's `/mcp` URL, and `HOMEPAGE_ALLOWED_HOSTS` (now bare `home.ramonedevelopment.com`). Per-host `-outpost` routers removed again; back to one domain-level proxy provider. **Prereq before deploy:** cortex's LAN IP `192.168.0.253` must be DHCP-reserved/static or the public path breaks on lease renewal.

## 2026-07-14 — Control Tower exposed publicly behind Authentik (group-restricted)

**Decision:** `tower.ramonedevelopment.com` is now reachable from the public internet and gated by Authentik forward-auth restricted to a `tower-users` group. It's the first service to leave the all-tailnet posture.

**How:**
- Tower's router listens on BOTH `tailnet` and `websecure` (public) entrypoints. Public path = router-forward WAN:443 → `192.168.0.253:443` (websecure, pinned to the LAN NIC). Tailnet path unchanged (split-DNS → tailscale IP).
- **Single-application** proxy provider `tower-fwd` (external host `https://tower.ramonedevelopment.com`) with an Application policy bound to the `tower-users` group — only members get in. Chosen over the domain-level gate because domain-level is all-or-nothing; a public tool needs per-app user restriction. Single-app exact-host match takes precedence over the domain-level provider. Added the per-host `tower-outpost` router (both entrypoints) for the callback path.
- `login.ramonedevelopment.com` (Authentik) also added to `websecure` — mandatory, since public visitors get redirected there to authenticate. Accepted consequence: the IdP is now internet-facing.
- Tower keeps its `TOWER_TOKEN` bearer auth underneath — defense in depth.

**Exposure method:** router port-forward (not Cloudflare Tunnel), per operator choice. Recommend the public Cloudflare A records for `tower`/`login` be proxied (orange, SSL Full-Strict) to hide the WAN IP and add WAF/rate-limiting; if the WAN IP is dynamic, the A records need DDNS.

**Hardening required (public IdP):** strong `akadmin` password + MFA, MFA for `tower-users`, Authentik reputation/brute-force policies on, optional Cloudflare WAF. `sqlserver`/`mysql` remain bridge-only (never exposed); `mcp-azure-devops` stays tailnet-only.

**Owner:** Chase Ramone

**Full detail:** `cortex/docker-compose.yml` (tower + authentik-server blocks), this session's plan.

---

## 2026-07-14 — magiq-media per-branch dev hosts: public, DNS-only, dual-entrypoint

**Decision:** The per-branch media dev environments (`media-api-{akshay,damian}`, `dynamodb-admin-{akshay,damian}`) are public, **unproxied (grey-cloud) DNS**, and `media-api` routes on BOTH `tailnet` and `websecure`. No Authentik on any of them.

**How:**
- `media-api` router entrypoints changed `websecure` → `tailnet,websecure` (magiq-media repo `docker-compose.cortex.yml:74`). It was public-only by design (Akshay/Damian aren't tailnet members), but that meant Chase's own tailnet machine hit the `tailnet` entrypoint via split-DNS and got a Traefik 404. Dual entrypoint serves external devs (websecure/WAN) AND tailnet (Chase) off the same backend. Mirrors `tower`.
- Public DNS: No-IP is decommissioned and there is **no wildcard** record anymore, so each public host needs its own A record. Added a **second** `cloudflare-ddns` instance `cloudflare-ddns-media` (`PROXIED=false`) managing the four `media-api-*` + `dynamodb-admin-*` hostnames → cortex WAN IP. Kept separate from the main DDNS (which is `PROXIED=true` for tower/login) to avoid mixing proxied modes in one container.
- **DNS-only (grey) chosen over proxied** because media-api handles large media payloads and Cloudflare's free proxy caps request bodies at 100MB + buffers streaming. Accepted tradeoff: exposes cortex's WAN IP and skips the CF WAF for these hosts. `media-api` carries no auth (public dev API); `dynamodb-admin` is Traefik basicauth-gated; `media-dynamodb-local` stays tailnet-only (no public record).

**Alternatives considered:** Proxied/orange DNS (rejected — 100MB body cap + streaming buffering breaks a media API). Per-domain `PROXIED` expression on the single DDNS instance (rejected — a second flat-`false` instance is unambiguous, no expression-syntax risk). Traefik file-provider router for the tailnet path (rejected — needs hardcoded container bridge IPs, fragile across recreates; the label change is the clean fix).

**Owner:** Chase Ramone

**Full detail:** magiq-media `docker-compose.cortex.yml` (media-api block), `cortex/docker-compose.yml` (`cloudflare-ddns-media` block). Also swept stale `:8443` / No-IP-wildcard comments out of the media compose header this session.
