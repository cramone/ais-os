# Azure DevOps MCP gateway

One shared instance of the official `@azure-devops/mcp` server, hosted on Cortex,
bridged from stdio to Streamable HTTP by `supergateway`. Every consumer (Claude Code
on Windows, Claudia on Cortex) connects to the same running server over the tailnet
instead of spawning its own copy.

Transport decision and history: [ADR 0001](../../references/adrs/0001-ado-mcp-cortex-gateway-transport.md).
Access-path split (MCP vs REST): [connections.md](../../connections.md).

| | |
|---|---|
| URL | `https://mcp-ado.ramonedevelopment.com/mcp` |
| Transport | Streamable HTTP (`type: "http"`) |
| Org | `MAGIQSoftware` |
| Domains | `core work work-items repositories wiki` |
| Auth to ADO | `AZURE_DEVOPS_PAT` from `.env`, injected into the container only |
| Auth to the gateway | none — tailnet-only reachability is the boundary |
| Server version | pinned in `Dockerfile.gateway` (`@azure-devops/mcp@2.7.0`, `supergateway@4.2.0`) |

## Server side (Cortex)

| Thing | Where |
|---|---|
| Image build | `mcp/azure-devops/Dockerfile.gateway` |
| Compose service | `mcp-azure-devops` in [docker-compose.yml](../../docker-compose.yml) (project `magiq`, container `magiq-mcp-azure-devops-1`) |
| Routing | Traefik labels on that service — host `mcp-ado.ramonedevelopment.com`, entrypoint `tailnet`, port 8000 |
| Secrets | `env_file: ./.env` → NAS-resident `/mnt/shared/claudia/magiq/.env` |

### Deploy / sync flow

Repo lives on the NAS at `/mnt/shared/claudia/magiq` (mounted as `Z:\claudia\magiq` on
Windows). Cortex reads it from there — no clone, no push step.

1. Edit `Dockerfile.gateway` (or the compose service) in the NAS repo.
2. Deploy: `ssh cortex cortex-sync magiq` — or wait up to 5 min for the sync cron.
3. `cortex-sync` rebuilds and recreates changed services for the `magiq` compose project.
4. Clients must restart their session (or reload MCP) only if the **URL or transport**
   changed; a rebuild behind the same URL needs no client change.

Logs: `ssh cortex docker logs magiq-mcp-azure-devops-1`.

## Client side

Registered at **user scope**, so it loads in every working directory:

```bash
claude mcp add --scope user --transport http azure-devops https://mcp-ado.ramonedevelopment.com/mcp
```

Stored in `~/.claude.json` under the top-level `mcpServers`. Verify from any folder:

```bash
claude mcp list
```

`azure-devops: https://mcp-ado.ramonedevelopment.com/mcp (HTTP) - ✓ Connected`.

The gitignored `Z:\claudia\magiq\.mcp.json` still declares the same server at project
scope. Project scope wins over user scope for that folder — same URL, so it is a no-op.
Keep it for consumers that read the repo instead of `~/.claude.json` (Claudia on Cortex).

### Why user scope

Project-scoped `.mcp.json` is per-folder, is gitignored, and exists only in this repo —
so a Claude Code session started in a code repo (e.g. a `magiq-media` checkout) got no
ADO tools at all. User scope removes the per-folder wiring.

Note: project-scoped servers also need approval before they load — `~/.claude/settings.json`
`enabledMcpjsonServers` lists only `hermes`. User-scoped servers skip that gate.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Connection closed` / connect timeout | Tailscale down on the client, or the host only resolves via MagicDNS (router DNS returns NXDOMAIN) | bring Tailscale up; check `curl -sv https://mcp-ado.ramonedevelopment.com/mcp` |
| Works on Windows, fails in WSL | WSL `resolv.conf` has no MagicDNS resolver | run Claude Code on Windows, or point WSL at the tailnet resolver |
| No ADO tools in one folder only | that folder's session predates the user-scope entry | restart the session |
| 401 / 203 from ADO | PAT expired, or the write came from an IP outside the org allowlist | rotate `AZURE_DEVOPS_PAT` in `.env`, re-sync |
| Tool missing (e.g. pipelines, search) | that domain is not enabled | add it to the `-d` list in `Dockerfile.gateway`, re-sync |

Client-side MCP logs:
`%LOCALAPPDATA%\claude-cli-nodejs\Cache\<cwd-slug>\mcp-logs-azure-devops\*.jsonl`.

## Rollback

- **Client, user scope:** `claude mcp remove -s user azure-devops`. The project-scoped
  `.mcp.json` in this repo keeps working for sessions started here.
- **Client, config restore:** `~/.claude.json` is backed up as `.claude.json.bak-<timestamp>`
  before manual edits; restore that file and restart the session.
- **Server, version pin:** revert the version in `Dockerfile.gateway`, then
  `ssh cortex cortex-sync magiq`.
- **Server, transport:** the retired per-machine stdio model is still in
  `mcp/azure-devops/Dockerfile` — see ADR 0001 for why it was dropped before reviving it.
