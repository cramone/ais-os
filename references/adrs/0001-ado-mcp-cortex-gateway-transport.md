# 0001. ADO MCP transport: Cortex-hosted HTTP gateway, not local stdio

**Status:** Accepted
**Date:** 2026-08-06
**Owner:** Chase

## Context

The Azure DevOps MCP integration went through two designs. First (2026-07-05, `docs/aios-portability-plan.md` option 6c) it was dockerized in-repo as a **stdio** server (`mcp/azure-devops/Dockerfile`, image `azure-devops-mcp:latest`), spawned locally by each consumer via `docker run` in `.mcp.json`, with a plaintext PAT in the config. Then (2026-07-04 decision) the architecture moved to hosting **one** instance on Cortex — the official `@azure-devops/mcp` server bridged from stdio to Streamable HTTP by `supergateway` (`mcp/azure-devops/Dockerfile.gateway`), behind Traefik's `tailnet` entrypoint — so every consumer connects over the tailnet instead of each spawning a copy.

The Claude Code client's `.mcp.json` never got repointed. It still ran `docker run azure-devops-mcp:latest`, but that stdio image was never built on Claudia (only the gateway image `stack-mcp-azure-devops` exists there), so the MCP failed at startup with `-32000: Connection closed`. The gateway itself was up and healthy the whole time.

## Decision

`.mcp.json` connects `azure-devops` over HTTP transport to `https://mcp-ado.ramonedevelopment.com/mcp`. No local `docker run`, no image build on the consumer, no PAT in the file. The credential lives in the gateway container's environment; tailnet-only reachability (Traefik `tailnet` entrypoint) is the security boundary.

## Consequences

- **Easier:** one place to hold the PAT and pin the server version; consumers need nothing but the URL; no per-machine `docker build`; the plaintext secret leaves `.mcp.json`.
- **Harder / accepted:** ADO MCP is only reachable on the tailnet — an off-tailnet consumer can't use it without additional exposure. The single gateway is a shared dependency; if it's down, all MCP clients lose ADO.
- Requires a session restart / MCP reload on each consumer to pick up the transport change.

## Alternatives considered

- **Build the stdio image locally** (`docker build -t azure-devops-mcp:latest mcp/azure-devops/`) to make the old config work as-is — rejected: revives the per-machine stdio model the 2026-07-04 decision retired, and keeps the PAT in `.mcp.json`.
- **Leave the community fork / direct REST** — already superseded by the 2026-07-04 move to the official server.
