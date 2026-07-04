# Azure DevOps MCP Integration — Shared Hosting on Cortex

**Date:** 2026-07-04
**Status:** Ready to implement — Step 0 must pass before anything else
**Owner:** Chase

This is a self-contained runbook. A fresh Claude session with no memory of prior conversation should be able to execute this end to end using only this file plus the AIS-OS repo.

---

## Context (read this first)

Chase runs **AIS-OS**, a personal work OS at `C:\Users\chase\OneDrive\Magiq\AIS-OS` (git repo: `github.com/cramone/ais-os`). Two consumers need Azure DevOps (ADO) access via MCP:

- **Claude Code**, running natively on Chase's Windows PC, configured via `AIS-OS/.mcp.json` (gitignored, machine-local).
- **Claudia**, a Hermes AI agent profile running bare-metal (systemd) on **Cortex**, Chase's home server (MINISFORUM AI X1 Pro-370, Ubuntu 24.04, reachable via Tailscale, hostname `cortex`, already running a Traefik reverse proxy stack at `~/stack/docker-compose.yml` — the single authoritative compose file, edited directly, no separate compose files).

**Control Tower** (AIS-OS's local dashboard, `AIS-OS/tower/`) does **not** use MCP and should not — it reads/writes ADO via direct REST (`scripts/devops_summary.py`, `tower/interrupts/ado_push.py`), a deliberate decision logged 2026-05-03 to avoid MCP's per-call schema/token overhead. Don't wire Tower into anything below.

### What was previously wired up (and is being replaced)

`.mcp.json` pointed Claude Code at a **local git clone**, `D:\mcp\azure-devops-mcp-server` — actually `RainyCodeWizard/azure-devops-mcp-server`, a small single-maintainer community project, NOT Microsoft's official server. It ran via `node build/index.js` (stdio), with the ADO PAT hardcoded in plaintext in `.mcp.json`.

**That PAT is compromised and must be rotated before anything else in this doc matters** — it was read into an LLM session's context on 2026-07-03/04. If this hasn't been done yet, stop and do it first: Azure DevOps → User Settings → Personal Access Tokens → revoke the old one, create a new one.

### Decision: migrate to Microsoft's official server

`microsoft/azure-devops-mcp` (MIT license, npm package `@azure-devops/mcp`, current version `2.7.0`) replaces the community fork. Confirmed:
- Supports **PAT authentication** (`--authentication pat`, reads `PERSONAL_ACCESS_TOKEN` env var) — required, because MAGIQSoftware's ADO org policy blocks Entra app registrations (same reason M365/Outlook/Teams integration is blocked — this is a known standing org constraint, see `connections.md`). This rules out Microsoft's newer **Remote MCP Server** (`mcp.dev.azure.com`) entirely for now anyway — separately from the org's auth policy, that remote server doesn't yet support Claude Code or Claude Desktop as clients at all (Entra doesn't implement the OAuth dynamic client registration the MCP spec requires — a protocol gap, not a rollout timing issue).
- **PAT format is base64**, not raw: `PERSONAL_ACCESS_TOKEN` must be `base64(<any-non-empty-string>:<raw-PAT>)`, e.g. `base64("chase:<pat>")`. This is different from Tower's REST scripts, which use the raw PAT directly (`AZURE_DEVOPS_PAT` in `.env`). Keep both env vars in sync when rotating.
- Domains supported: `core, work, work-items, search, test-plans, repositories, wiki, pipelines, advanced-security`. Default recommendation: enable `core work work-items repositories wiki` — matches what Claude Code/Claudia actually need, keeps the tool schema footprint down (same token-efficiency principle behind Tower staying on REST).

### Decision: host ONE shared instance on Cortex, not duplicate local builds

Original plan (superseded by this doc) was: build the Docker image separately on Windows (for Claude Code) and on Cortex (for Claudia) — two local stdio spawns of the same image, no shared state but no duplication of *effort* either. Chase asked for better: **one running instance on Cortex that both consumers talk to**, since MCP servers are normally spawned per-process over stdio and don't share state or a network endpoint by default.

This requires bridging stdio → network transport. **Supergateway** (`supercorp-ai/supergateway`, MIT, actively maintained, Docker image available) does exactly this — wraps a stdio MCP server and exposes it over SSE or Streamable HTTP. Verified CLI (from its README):

```bash
npx -y supergateway --stdio "<stdio command>" --outputTransport streamableHttp --port 8000
```
Endpoint defaults to `http://localhost:8000/mcp` (path configurable via `--streamableHttpPath`).

**Claude Code supports HTTP-transport remote MCP servers natively**, including static bearer-token auth (`claude mcp add --transport http <name> <url> --header "Authorization: Bearer <token>"`) — no OAuth needed, sidesteps the Entra problem entirely for this use case.

**Important gap, not yet resolved:** supergateway's `--header`/`--oauth2Bearer` flags, per its own docs, are for *outbound* auth when supergateway is bridging *to* a remote server (SSE→stdio / StreamableHttp→stdio direction). There's no documented flag for requiring an incoming auth header when supergateway is the one exposing stdio→StreamableHttp (our use case). **Practical implication: this endpoint has no app-level access gate of its own — Tailscale-only reachability (via the `tailnet` Traefik entrypoint, same as every other Cortex service) is the actual security boundary, not a bearer token.** That's consistent with how Seq/Portainer/Open WebUI are already secured on this stack, so it's not a new risk model — just flagging that "add a bearer token" isn't a real option here without extra work (a Traefik `forwardAuth`/basicAuth middleware, unverified, would be the way to add one later if wanted).

---

## Step 0 — Verify ADO reachability from Cortex (BLOCKING — do this first)

Per `connections.md`: *"ADO writes must originate from Chase's machine (org IP allowlist)."* Today, Claude Code's ADO MCP calls originate from Chase's Windows PC — inside whatever the allowlist covers. **Under the shared-hosting design below, 100% of ADO traffic (Claude Code's AND Claudia's) would originate from Cortex's egress IP instead.** If Cortex doesn't share the same allowlisted egress IP as Chase's Windows machine (e.g. different ISP path, CGNAT), this entire design fails for both consumers — not just Claudia.

**Test before building anything:**
```bash
ssh chase@cortex
curl -I https://dev.azure.com
curl -s -u ":$AZURE_DEVOPS_PAT_RAW" "https://dev.azure.com/MAGIQSoftware/_apis/projects?api-version=7.1"
```
If the second command returns a JSON project list (not a 401/403), Cortex's egress is allowlisted and the rest of this doc is safe to proceed with. If it fails with auth/network errors that don't reproduce identically from Windows, **stop** — fall back to the per-machine local-stdio-build approach instead (Dockerfile already exists at `mcp/azure-devops/Dockerfile`; build it separately on Windows and Cortex, each consumer spawns its own local process, no shared hosting, no Cortex-egress dependency for Claude Code since it'd keep running locally on Windows).

---

## Step 1 — Rotate the exposed PAT (if not already done)

1. Azure DevOps → profile → Security → Personal Access Tokens → revoke the old token (the one that was hardcoded in `.mcp.json`).
2. Create a new PAT. Scopes needed: Work Items (read, write), Code (read, write), Wiki (read, write), Project and Team (read) — matches what Tower's `.env.example` and the MCP domains above need.
3. Update `AIS-OS/.env` (not `.env.example` — that's the template) on Chase's Windows machine:
   ```
   AZURE_DEVOPS_PAT=<new raw PAT>
   AZURE_DEVOPS_PAT_B64=<base64 of "chase:<new raw PAT>">
   ```
   Generate the base64 value:
   ```bash
   echo -n "chase:<new raw PAT>" | base64
   ```
4. This same PAT (base64 form) needs to reach Cortex too — it'll go in Cortex's own `/opt/ais-os/.env` in Step 3. **Do not commit either `.env` file** — both are gitignored.

---

## Step 2 — Build the combined image (ADO MCP + supergateway)

Two Dockerfiles now exist / will exist under `AIS-OS/mcp/azure-devops/` (in-repo so both Windows and Cortex get them via git):

- `Dockerfile` (already created) — plain stdio image, `mcp-server-azuredevops` only. This is the **fallback** if Step 0 fails, or useful for local debugging (`docker run -i --rm ... azure-devops-mcp:latest`).
- `Dockerfile.gateway` (create this now) — the shared-hosting version, wraps the stdio server with supergateway and exposes Streamable HTTP.

Create `AIS-OS/mcp/azure-devops/Dockerfile.gateway`:

```dockerfile
# Shared Azure DevOps MCP server — stdio bridged to Streamable HTTP via
# supergateway, so Claude Code (Windows) and Claudia (Cortex) can both
# reach ONE running instance instead of each spawning their own.
#
# Runs on Cortex only. Tailscale-only reachability (Traefik `tailnet`
# entrypoint) is the security boundary — supergateway has no documented
# incoming-auth gate for this direction (stdio->StreamableHttp), so don't
# expose this beyond the tailnet.

FROM node:22-alpine

RUN npm install -g @azure-devops/mcp@2.7.0 supergateway

EXPOSE 8000

# Domains kept lean on purpose — same token-efficiency principle as Tower
# staying on REST. Add more (search, pipelines, test-plans,
# advanced-security) only if something actually needs them.
ENTRYPOINT ["npx", "supergateway", \
  "--stdio", "mcp-server-azuredevops MAGIQSoftware --authentication pat -d core work work-items repositories wiki", \
  "--outputTransport", "streamableHttp", \
  "--port", "8000"]
```

Verify this builds and runs locally (on Windows, as a smoke test, before touching Cortex):
```bash
cd AIS-OS/mcp/azure-devops
docker build -f Dockerfile.gateway -t azure-devops-mcp-gateway:latest .
docker run --rm -p 8000:8000 -e PERSONAL_ACCESS_TOKEN="$AZURE_DEVOPS_PAT_B64" -e ado_mcp_project=Media azure-devops-mcp-gateway:latest
```
In another terminal:
```bash
curl -s http://localhost:8000/mcp -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'
```
Expect a JSON-RPC response, not a connection error. If supergateway's actual flag behavior differs from what's documented above (versions drift), adjust `--stdio` / `--outputTransport` / `--streamableHttpPath` against supergateway's current README before proceeding — don't assume this Dockerfile is final without this smoke test passing.

---

## Step 3 — Deploy on Cortex

```bash
ssh chase@cortex
cd /opt/ais-os   # the clone already set up for Tower's deployment — see docs/superpowers/specs/2026-07-03-tower-cortex-deployment.md
git pull
```

Add `AZURE_DEVOPS_PAT_B64` and `ado_mcp_project` to Cortex's `/opt/ais-os/.env` (same values as Windows' `.env`, Step 1).

Add this service to `~/stack/docker-compose.yml` (the single authoritative compose file — edit it directly):

```yaml
  # ── Azure DevOps MCP (shared: Claude Code + Claudia) ────────────────────
  mcp-azure-devops:
    build:
      context: /opt/ais-os/mcp/azure-devops
      dockerfile: Dockerfile.gateway
    restart: unless-stopped
    env_file:
      - /opt/ais-os/.env
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.mcp-ado.rule=Host(`mcp-ado.ramonedevelopment.com`)"
      - "traefik.http.routers.mcp-ado.entrypoints=tailnet"
      - "traefik.http.routers.mcp-ado.tls=true"
      - "traefik.http.services.mcp-ado.loadbalancer.server.port=8000"
```

```bash
cd ~/stack
docker compose up -d --build mcp-azure-devops
```

Verify from Cortex itself:
```bash
curl -s http://localhost:8000/mcp -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'
```

Verify from a tailnet device (e.g. Chase's Windows PC, which should already be on the same Tailscale network — it already reaches other tailnet-only Cortex services):
```bash
curl -s https://mcp-ado.ramonedevelopment.com/mcp -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'
```

---

## Step 4 — Wire up Claude Code (Windows)

Replace the `azure-devops` entry in `AIS-OS/.mcp.json` (gitignored, edit directly — this session couldn't write to it directly, so this has to happen by hand or via a fresh session with file access):

```json
{
  "mcpServers": {
    "azure-devops": {
      "type": "http",
      "url": "https://mcp-ado.ramonedevelopment.com/mcp"
    }
  }
}
```

Or via CLI:
```bash
claude mcp add --transport http azure-devops https://mcp-ado.ramonedevelopment.com/mcp
```

No docker build needed on Windows anymore for day-to-day use — Claude Code just makes HTTP calls to Cortex. (The local `Dockerfile` still exists as a fallback if Step 0 ever fails or Cortex is down and local stdio access is needed temporarily.)

Update `AIS-OS/.mcp.json.example` to match (already points at the dockerized local version from the prior session — update it to show the HTTP/shared form as the primary documented path, with a note on the local fallback).

Test: ask Claude Code something like "list my ADO projects" and confirm it comes back without error.

---

## Step 5 — Wire up Claudia (Hermes, Cortex)

**Not verified in this session** — no direct access to Cortex's `~/.hermes/profiles/claudia/config.yaml` or Hermes' MCP config schema. Before wiring this in:

1. Check Hermes' own documentation/schema for how it declares MCP servers — specifically whether it supports an HTTP/Streamable-HTTP type entry (analogous to Claude Code's `"type": "http"`), or only local command-spawned (stdio) entries.
2. Since Claudia runs on the same host as the new `mcp-azure-devops` container, she doesn't need to go through Tailscale/Traefik at all — `http://localhost:8000/mcp` should work directly, simpler and doesn't depend on the tailnet routing working.
3. The config entry, once the correct schema is confirmed, should look conceptually like:
   ```yaml
   mcp_servers:
     azure-devops:
       type: http   # or whatever Hermes actually calls it — VERIFY
       url: http://localhost:8000/mcp
   ```
4. Restart the gateway after config changes — same gotcha noted elsewhere in AIS-OS docs: `hermes-gateway-claudia` caches profile state at process start.
   ```bash
   claudia gateway restart
   ```
5. Test with a prompt like "list my ADO work items" via Claudia's Telegram bot or however she's normally invoked.

---

## Rollout order (summary)

1. **Step 0** — verify ADO reachability from Cortex. Do not proceed past this if it fails; use the fallback (separate local builds, no shared hosting) instead.
2. **Step 1** — rotate the exposed PAT if not already done. Generate the base64 form.
3. **Step 2** — build `Dockerfile.gateway` locally on Windows, smoke-test with curl before deploying anywhere.
4. **Step 3** — deploy on Cortex via the shared compose file, verify both locally (on Cortex) and via the tailnet hostname.
5. **Step 4** — point Claude Code's `.mcp.json` at the new HTTP endpoint, test a real ADO query.
6. **Step 5** — confirm Hermes' actual MCP config schema, wire Claudia to `http://localhost:8000/mcp`, restart her gateway, test.

## Files this touches

| File | State |
|---|---|
| `mcp/azure-devops/Dockerfile` | Already created (prior session) — plain stdio image, fallback path |
| `mcp/azure-devops/Dockerfile.gateway` | Create in Step 2 |
| `.env` (Windows, gitignored) | Add/update `AZURE_DEVOPS_PAT`, `AZURE_DEVOPS_PAT_B64` |
| `.env` (Cortex, `/opt/ais-os/.env`, gitignored) | Add `AZURE_DEVOPS_PAT_B64`, `ado_mcp_project` |
| `.env.example` | Already updated (prior session) with `AZURE_DEVOPS_PAT_B64` |
| `.mcp.json` (Windows, gitignored) | Update in Step 4 to the HTTP form — could not be edited directly in the prior session (protected path), must be done by hand or a session with file access |
| `.mcp.json.example` | Update in Step 4 to document the HTTP form as primary |
| `~/stack/docker-compose.yml` (Cortex only, not in this repo) | Add `mcp-azure-devops` service in Step 3 |
| `~/.hermes/profiles/claudia/config.yaml` (Cortex only, not in this repo) | Add MCP entry in Step 5 — schema unverified |
