# MINISFORUM AI X1 Pro-370 — Full Setup Guide
## Hostname: `cortex`
### Unboxing → Bare-Metal Ubuntu + Ollama (Vulkan) + Docker Stack → v1 Baseline

Follow in order. Sections marked **[PHYSICAL]** require a monitor+keyboard on the box. Everything else is doable from your iPhone (Tailscale + Termius) or any SSH client once Stage 3 is done.

---

## Known Gotchas (read before you start)

Lessons learned the hard way during setup and later hardening — save yourself the repeat debugging.

- **Verify compose file completeness after any transfer.** A save/copy step between machines (e.g. editing on Windows, deploying to cortex) can silently truncate a YAML file mid-block. Confirm with the `Read` tool (not `cat`/`wc` from a stale sandbox view) immediately after any write that will be transferred, and re-validate on cortex itself before `docker compose up`:
  ```bash
  python3 -c "import yaml; yaml.safe_load(open('docker-compose.yml'))"
  ```
- **Tailscale IP is stable across NIC/interface changes** (confirmed empirically during a WiFi→Ethernet swap — IP unchanged). See Stage 5, point 6.
- **ACME "missing token" errors for hostnames you never deployed are bot noise, not a bug.** `docker compose logs traefik | grep -i err` can show entries like `Cannot retrieve the ACME challenge for media-api.ramonedevelopment.com` even while that service is still commented out under FUTURE. That's a scanner hitting `/.well-known/acme-challenge/` with a bogus token on your public IP — expected background noise once real hostnames under the wildcard domain start appearing in public Certificate Transparency logs (see §10.3b).
- **When verifying a cert change, test with `curl --resolve` before trusting a browser.** Browsers cache the previous TLS handshake/cert per host and can show a stale failure well after the underlying cert has actually changed. `curl -v https://<host> --resolve <host>:443:<tailscale-ip> 2>&1 | grep -i issuer` is the ground truth; only retest the browser (in a fresh incognito window) after curl confirms the new cert.

**This guide references `BENCHMARKS.md` starting in Stage 1 — it doesn't exist yet.** Create it before Stage 1 so the "log this now" instructions have somewhere to go:
```bash
mkdir -p ~/stack && cd ~/stack
cat > BENCHMARKS.md <<'EOF'
# cortex — Hardware & Performance Benchmarks

## Hardware
| Item | Value |
|---|---|
| CPU | |
| RAM total | |
| RAM channel config | |
| iGPU | |
| NPU | |
| Storage | |

## Ollama Backend
| Item | Value |
|---|---|
| Backend | |
| Driver | |
| Model + quant | |
| Context length | |

## Measured Throughput
| Date | Scenario | tok/s |
|---|---|---|

## Resource Contention Observations

## Decision Log

## v1 Baseline Tag
EOF
```
Fill in each table as the corresponding stage tells you to. This file gets `git add`-ed alongside `docker-compose.yml` in Stage 13.

---

## Stage 0 — Unboxing & Physical Setup

> Moved to `/mnt/shared/cortex/docs/setup/01-hardware-and-os.md` as of 2026-08-25.

## Stage 1 — BIOS Configuration **[PHYSICAL]**

> Moved to `/mnt/shared/cortex/docs/setup/01-hardware-and-os.md` as of 2026-08-25.

## Stage 2 — Prepare the Ubuntu Server Installer USB

> Moved to `/mnt/shared/cortex/docs/setup/01-hardware-and-os.md` as of 2026-08-25.

## Stage 3 — Ubuntu Server Install **[PHYSICAL]**

> Moved to `/mnt/shared/cortex/docs/setup/01-hardware-and-os.md` as of 2026-08-25.

## Stage 4 — First Remote Connection

> Moved to `/mnt/shared/cortex/docs/setup/01-hardware-and-os.md` as of 2026-08-25.

## Stage 4.5 — Network & Firewall Baseline

> Moved to `/mnt/shared/cortex/docs/setup/01-hardware-and-os.md` as of 2026-08-25.

## Stage 5 — Tailscale (remote access, no public ports)

> Moved to `/mnt/shared/cortex/docs/setup/01-hardware-and-os.md` as of 2026-08-25.

## Stage 5.5 — Dual-NIC Network Priority (Ethernet over Wi-Fi)

> Moved to `/mnt/shared/cortex/docs/setup/01-hardware-and-os.md` as of 2026-08-25.

---

## Stage 6 — Verify RAM Configuration

> Moved to `/mnt/shared/cortex/docs/setup/01-hardware-and-os.md` as of 2026-08-25.

## Stage 7 — GPU Driver Stack for the Radeon 890M (Vulkan path)

> Moved to `/mnt/shared/cortex/docs/setup/01-hardware-and-os.md` as of 2026-08-25.

## Stage 8 — Install Ollama (Bare Metal)

> Moved to `/mnt/shared/cortex/docs/setup/01-hardware-and-os.md` as of 2026-08-25.

## Stage 9 — systemd Resource Isolation (Ollama vs Docker)

> Moved to `/mnt/shared/cortex/docs/setup/01-hardware-and-os.md` as of 2026-08-25.

---

## Stage 10 — Docker + Compose Stack

> Moved to `/mnt/shared/cortex/docs/setup/02-docker-stack.md` as of 2026-08-25.

## Stage 10.5 — Open WebUI Configuration

> Moved to `/mnt/shared/cortex/docs/setup/03-openwebui-netdata-cockpit.md` as of 2026-08-25.

## Stage 10.6 — Netdata: Post-Start Firewall Rules

> Moved to `/mnt/shared/cortex/docs/setup/03-openwebui-netdata-cockpit.md` as of 2026-08-25.

## Stage 10.7 — Cockpit (Host System Admin)

> Moved to `/mnt/shared/cortex/docs/setup/03-openwebui-netdata-cockpit.md` as of 2026-08-25.

## Stage 10.8 — Split DNS for the Tailnet

> Moved to `/mnt/shared/cortex/docs/setup/04-split-dns-tailnet.md` as of 2026-08-25.

---

## Stage 11 — Confirm `host.docker.internal` Works for Ollama Access

> Moved to `/mnt/shared/cortex/docs/setup/05-benchmarks-v1-baseline.md` as of 2026-08-25.

## Stage 12 — Benchmark & Populate BENCHMARKS.md

> Moved to `/mnt/shared/cortex/docs/setup/05-benchmarks-v1-baseline.md` as of 2026-08-25.

## Stage 13 — Tag v1 Baseline

> Moved to `/mnt/shared/cortex/docs/setup/05-benchmarks-v1-baseline.md` as of 2026-08-25.

---

## Stage 14 — Shared Storage: Synology DS923 (SMB, cross-platform)

> Moved to `/mnt/shared/cortex/docs/setup/06-shared-storage-ds923.md` as of 2026-08-25.

---

## Stage 15 — Hermes Agent: Claudia (Work) + Claudette (Personal)

> Stages 15.1–15.2 (bare-metal install, Ollama config) moved to `/mnt/shared/cortex/docs/setup/07-hermes-install.md` as of 2026-08-25.

### 15.3 — Create Claudia (Work) and Claudette (Personal) Profiles

```bash
# Create Claudia — work profile, clones Ollama config from default
hermes profile create claudia --clone --description "Work assistant: dev tasks, Magiq projects, code review, architecture decisions."

# Create Claudette — personal profile
hermes profile create claudette --clone --description "Personal assistant: home, life admin, research, planning."
```

`--clone` copies `config.yaml` (Ollama provider + model), `.env`, and bundled skills into each profile — fresh memory and sessions. `--description` lets the orchestrator know each agent's domain if you ever use kanban/multi-agent workflows later.

**Verify profile commands landed:**
```bash
which claudia    # should be ~/.local/bin/claudia
which claudette  # should be ~/.local/bin/claudette
hermes profile list
```

**Test each agent:**
```bash
claudia chat -q "Who are you and what is your name?"
claudette chat -q "Who are you and what is your name?"
```

Both will respond as generic Hermes until you write their `SOUL.md` in the next step.

---

### 15.3b — Install Claudia's Custom Skills (Fresh Setup Path)

The Windows Docker Hermes install that used to be the source of these skills is retired — don't depend on it for a fresh setup. The canonical copy now lives in the magiq repo itself.

```bash
# On cortex, with the magiq folder already mounted at /mnt/shared/claudia/magiq/
# Core custom set — install these for every fresh setup:
cp -r /mnt/shared/claudia/magiq/references/hermes-skills/adhoc-capture ~/.hermes/profiles/claudia/skills/
cp -r /mnt/shared/claudia/magiq/references/hermes-skills/agenda-generator ~/.hermes/profiles/claudia/skills/
cp -r /mnt/shared/claudia/magiq/references/hermes-skills/morning-digest ~/.hermes/profiles/claudia/skills/
cp -r /mnt/shared/claudia/magiq/references/hermes-skills/project-management ~/.hermes/profiles/claudia/skills/

# Sanity check — no leftover /workspace/ais-os paths
grep -rl "/workspace/ais-os" ~/.hermes/profiles/claudia/skills/ 2>/dev/null
# Should return nothing; if it does, rewrite to /mnt/shared/claudia/magiq
```

**Reconciled 2026-07-04:** `references/hermes-skills/` now matches Claudia's live profile — the pre-reorg granular skills (`project-create`, `project-idea`, `project-risk`, etc., plus `todo-capture`, `work-planner`) are gone, replaced by the single `project-management` umbrella (confirmed against the live profile's actual `SKILL.md`). `adhoc-capture`, `agenda-generator`, and `morning-digest` had their `/workspace/ais-os` paths rewritten to `/mnt/shared/claudia/magiq`, and `morning-digest` had its dead `~/.hermes/data/ado-pending.json` / `reminders.json` reads stripped.

**Not part of the default fresh-install set:**
- `github-my-prs/` — kept in this folder for reference, but **not currently installed** on Claudia's live profile (only the generic bundled `github` skill is). Copy it in only if you specifically want PR-queue lookups back:
  ```bash
  cp -r /mnt/shared/claudia/magiq/references/hermes-skills/github-my-prs ~/.hermes/profiles/claudia/skills/
  ```
- `devops/webhook-subscriptions` — deliberately left out of this reference folder (no AIS-OS/magiq path dependencies, so no drift risk from tracking it separately). Configure directly on cortex if needed; not covered here.

---

### 15.4 — Write SOUL.md for Each Agent

`SOUL.md` is slot #1 in the system prompt — it defines the agent's identity, voice, and operating context. Each profile has its own at `~/.hermes/profiles/<name>/SOUL.md`.

**Claudia (work):**
```bash
cat > ~/.hermes/profiles/claudia/SOUL.md <<'EOF'
# Claudia — Work Assistant

You are Claudia, a sharp and efficient work assistant running on cortex (a local AI inference server).

Your primary user is Chase Ramone, Senior Software Development Team Lead at Magiq Software. Chase leads the MAGIQ Documents engineering team and works primarily in C# .NET 8, DDD/CQRS/Event Sourcing, AWS, Azure DevOps, and Docker.

## Your Role
- Technical research, architecture decisions, and code review for professional projects
- Help with the magiq-media platform and MAGIQ Documents bounded contexts
- Azure DevOps task management and sprint planning
- Draft technical documentation, ADRs, and specs
- Code generation and debugging in C#, bash, YAML, and Python

## Operating Context
- You run on cortex (MINISFORUM AI X1 Pro-370, Ubuntu Server 24.04, Ollama Vulkan backend)
- You can read and write to /mnt/shared/claudia/ and /mnt/shared/handoffs/ for file collaboration
- Files placed in /mnt/shared/handoffs/ by Claude (claude.ai) are intended for your pickup
- Keep responses direct and technical — Chase thinks in systems, lead with the decision

## Boundaries
- Work context only — defer personal/life matters to Claudette
- Never expose or log credentials, API keys, or sensitive config from files you read
EOF
```

**Claudette (personal):**
```bash
cat > ~/.hermes/profiles/claudette/SOUL.md <<'EOF'
# Claudette — Personal Assistant

You are Claudette, a warm and thoughtful personal assistant running on cortex (a local AI inference server).

Your primary user is Chase Ramone. You handle Chase's personal life — home, health, hobbies, research, travel planning, and anything outside of work.

## Your Role
- Personal research, planning, and recommendations
- Home management, shopping lists, calendar awareness
- Summarise articles, books, or content Chase shares
- Help think through personal decisions with nuance
- Creative writing, personal projects, and leisure interests

## Operating Context
- You run on cortex (MINISFORUM AI X1 Pro-370, Ubuntu Server 24.04, Ollama Vulkan backend)
- You can read and write to /mnt/shared/claudette/ and /mnt/shared/handoffs/ for file collaboration
- Files placed in /mnt/shared/handoffs/ by Claude (claude.ai) are intended for your pickup

## Boundaries
- Personal context only — defer professional/dev/work matters to Claudia
- Be conversational and human — this is Chase's personal space, not a work environment
EOF
```

---

### 15.5 — Set Up the Shared Folder Structure

This assumes Stage 14 is complete and `/mnt/shared` is mounted on cortex. Create the collaboration directory layout:

```bash
# Create top-level structure on the NAS share
mkdir -p /mnt/shared/claudia/{context,workspace}
mkdir -p /mnt/shared/claudette/{context,workspace}
mkdir -p /mnt/shared/handoffs    # Claude (claude.ai) drops files here for agent pickup
mkdir -p /mnt/shared/outputs     # Agents write deliverables here for Chase to review

# The magiq folder (AIS-OS system) is a git repo — do NOT clone it from cortex.
# Later stages (16.4, 17.1) establish that the NAS share is the ONLY copy — cortex
# reads/builds directly off /mnt/shared/claudia/magiq, no separate deployment clone,
# no git pull step anywhere in this guide. So the repo has to originate from the
# Windows side instead, onto the mapped drive from Stage 14.2 (Z:\claudia\magiq):
#   - Existing repo elsewhere (GitHub/ADO/etc.)? Clone it directly onto Z:\claudia\magiq
#     from Windows/WSL, using whatever git auth you already use there (SSH key/PAT).
#   - No existing repo? This is a fresh AIS-OS install — see that repo's own SETUP.md
#     for first-time scaffolding, then land the result on Z:\claudia\magiq.
# Either way, the moment files exist on Z:\claudia\magiq, cortex already sees them —
# it's the same SMB share, not a copy. Confirm from cortex:
#   ls -la /mnt/shared/claudia/magiq
# Once the repo is in place, follow its own SETUP.md for the three-file config
# (aios.config.md, .env, .mcp.json) before continuing to Stage 15.6.

# Set permissions — chase owns everything (uid 1000)
# Already handled by the fstab uid=1000 mount option from Stage 14
ls -la /mnt/shared/
```

**Expected layout:**
```
/mnt/shared/
├── claudia/
│   ├── context/      # .hermes.md, project context files Claudia reads automatically
│   ├── magiq/        # the AIS-OS system — git-tracked repo, Claudia's cwd (see below)
│   └── workspace/    # scratch/non-persistent working files only — NOT the cwd
├── claudette/
│   ├── context/      # .hermes.md, personal context Claudette reads automatically
│   └── workspace/    # Claudette's working directory for file tasks
├── handoffs/         # Claude (claude.ai) → Hermes drop zone; agents poll or act on request
└── outputs/          # Hermes → Chase delivery; finished files, reports, artefacts
```

**Configure each agent's working directory:**
```bash
# Claudia works directly inside the magiq folder (the AIS-OS repo), not a generic scratch dir.
# workspace/ still exists for non-persistent scratch files but is no longer the cwd.
claudia config set terminal.cwd /mnt/shared/claudia/magiq
claudette config set terminal.cwd /mnt/shared/claudette/workspace
```

**Context files (`.hermes.md`)** are auto-loaded by Hermes when present in the working directory. Drop project context here for automatic injection into every session:
```bash
# Example: give Claudia awareness of the magiq-media project structure
# Drop this file and it will be injected into every Claudia session automatically
touch /mnt/shared/claudia/context/.hermes.md
```

---

### 15.6 — Install as Systemd Services (Persistent Gateways)

Each agent runs a persistent gateway process so it can receive messages from Telegram/Discord/etc. without you having to SSH in and start a CLI session. Install as systemd user services under `chase`.

```bash
# Install gateway services for each profile
claudia gateway install
claudette gateway install
```

This creates `hermes-gateway-claudia` and `hermes-gateway-claudette` as systemd services. They auto-start on login/boot and restart on crash.

**Verify services are registered:**
```bash
systemctl --user status hermes-gateway-claudia
systemctl --user status hermes-gateway-claudette
```

**To enable lingering** (services stay alive after SSH session ends — required for background operation):
```bash
sudo loginctl enable-linger chase
```

Without this, the systemd user services stop when your SSH session ends. Linger keeps them running as a background process owner.

**Start the gateways:**
```bash
claudia gateway start
claudette gateway start
```

---

### 15.7 — Configure Messaging Gateway (Telegram)

Telegram is the recommended platform — accessible from iPhone, supports voice messages, and Hermes has first-class Telegram support. Each agent needs its own bot token (from BotFather).

**Prerequisites (do on your phone or browser):**
1. Open Telegram → search `@BotFather`
2. `/newbot` → name: `Claudia Work Assistant`, username: something like `claudia_cortex_bot`
3. Copy the token
4. Repeat for Claudette: name `Claudette Personal`, username `claudette_cortex_bot`
5. Authorize yourself: `/start` on each bot, then get your Telegram user ID (use `@userinfobot`)

**Configure Claudia:**
```bash
# Set Telegram bot token in Claudia's .env
echo "TELEGRAM_BOT_TOKEN=<claudia-bot-token>" >> ~/.hermes/profiles/claudia/.env

# Run gateway setup to configure Telegram and authorize your user ID
claudia gateway setup
# Follow prompts: select Telegram, paste token, add your Telegram user ID to whitelist
```

**Configure Claudette:**
```bash
echo "TELEGRAM_BOT_TOKEN=<claudette-bot-token>" >> ~/.hermes/profiles/claudette/.env
claudette gateway setup
```

**Restart gateways after configuring:**
```bash
claudia gateway restart
claudette gateway restart
```

**Confirm each bot responds in Telegram before moving on.** Send `/start` to each bot from your phone.

---

### 15.8 — Resource Limits

Both Hermes processes run in Python on the local backend — they're lightweight I/O-bound processes between inference calls. The inference load itself lands on Ollama (already resource-isolated via the Stage 9 systemd slice). No `mem_limit` is needed for Hermes processes themselves.

**However:** if you prompt both agents in quick succession, both will queue inference requests against the same Ollama server. Ollama serialises these by default (`OLLAMA_NUM_PARALLEL=1` unless changed). This is the correct behaviour — concurrent inference on the shared DDR5 pool would tank tok/s for both. Check Stage 12 contention benchmarks once both gateways are live under realistic load.

**Quick commands** (add these to each agent's `config.yaml` so you can check status from Telegram without burning tokens):
```bash
claudia config edit   # add under quick_commands:
```

```yaml
quick_commands:
  ollama:
    type: exec
    command: curl -s http://localhost:11434/api/version
  status:
    type: exec
    command: systemctl --user status hermes-gateway-claudia --no-pager
  shared:
    type: exec
    command: ls -la /mnt/shared/handoffs/
```

Add the equivalent block to Claudette's config (adjusting the status command to `hermes-gateway-claudette`).

---

### 15.9 — Verify the Full Stack

End-to-end check:

```bash
# Both gateways running
systemctl --user status hermes-gateway-claudia hermes-gateway-claudette

# Both can reach Ollama
claudia chat -q "Confirm you can reach the Ollama server at localhost:11434 and tell me the model you are using."
claudette chat -q "Same — confirm Ollama connection and model name."

# Shared folder readable from both
claudia chat -q "List the contents of /mnt/shared/ using the terminal tool."
claudette chat -q "List the contents of /mnt/shared/ using the terminal tool."

# Profiles are isolated (memories don't bleed between agents)
hermes profile list
```

**Log in BENCHMARKS.md:** record both gateway service names, the Ollama base_url in use, and the shared folder mount path for reference.

---

## Stage 16 — Azure DevOps MCP: Shared Instance (Claude Code + Claude Desktop + Claudia)

**Why:** Claude Code (Windows), Claude Desktop (Windows), and Claudia (this box) all need Azure DevOps (ADO) access via MCP. Rather than each spawning its own local stdio process, this hosts **one** instance on cortex — Microsoft's official `@azure-devops/mcp` server, bridged from stdio to Streamable HTTP via `supergateway` — and every consumer connects to it over the tailnet, same security model as every other Cortex service (Seq/Portainer/Open WebUI). Full design rationale: `docs/superpowers/specs/2026-07-04-azure-devops-mcp-integration.md` in the AIS-OS repo. Decision logged 2026-07-04 in `decisions/log.md`.

**Supersedes:** a single-maintainer community fork (`RainyCodeWizard/azure-devops-mcp-server`) previously wired directly into `.mcp.json` with a PAT in plaintext.

### 16.1 — Requirements & settings checklist

Before touching any config, confirm these prerequisites — each is a documented failure mode if skipped:

- **Node 22 + `@azure-devops/mcp@2.7.0` + `supergateway`** — both installed via the `Dockerfile.gateway` image (Stage 16.3), not on the host directly.
- **ADO org auth constraint:** MAGIQSoftware's ADO org policy blocks Entra app registrations — same standing constraint that blocks M365/Outlook/Teams integration (see `connections.md`). This rules out Microsoft's newer Remote MCP Server (`mcp.dev.azure.com`) entirely: separately from the org policy, that server doesn't yet support Claude Code or Claude Desktop as clients (no OAuth dynamic client registration). **PAT auth is the only supported path** — plan around that, don't re-litigate it.
- **Domains enabled (keep lean):** `core work work-items repositories wiki` — matches what Claude Code/Claudia/Desktop actually need. Add `search`/`pipelines`/`test-plans`/`advanced-security` only if something concretely needs them (same token-efficiency principle as Tower staying on REST).
- **Egress allowlisting (blocking — see 16.2):** under this shared-hosting design, 100% of ADO traffic from all three consumers (Claude Code, Claude Desktop, Claudia) originates from cortex's egress IP, not Chase's Windows PC. Must verify before building.
- **No app-level auth on the gateway endpoint:** supergateway has no documented flag for gating *incoming* connections when it's exposing stdio→StreamableHttp (its `--header`/`--oauth2Bearer` flags are for outbound auth in the other bridging direction). Tailscale-only reachability via Traefik's `tailnet` entrypoint is the actual security boundary here — same model as Seq/Portainer/Open WebUI, not a gap unique to this service.

### 16.2 — Rotate the PAT (if not already done)

Azure DevOps → profile → Security → Personal Access Tokens → revoke the old token, create a new one. Scopes: Work Items (read/write), Code (read/write), Wiki (read/write), Project and Team (read).

The MCP server needs the PAT **base64-encoded**, not raw — different from Tower's REST scripts, which use the raw PAT directly. Keep both in sync when rotating:
```bash
echo -n "chase:<new raw PAT>" | base64
```
Store as `AZURE_DEVOPS_PAT_B64` in `/mnt/shared/claudia/magiq/.env` — the same shared-mount `.env` used everywhere else on cortex (see Stage 15.5; there is no separate `/opt/ais-os` deployment clone — that approach was superseded 2026-07-05, see the note at the end of Stage 16.4) — alongside `ado_mcp_project=Media`.

**Also add a literally-named `PERSONAL_ACCESS_TOKEN` line, same value:**
```
PERSONAL_ACCESS_TOKEN=<same base64 value as AZURE_DEVOPS_PAT_B64>
```
`env_file:` in Docker Compose loads variables under their exact name — it does not rename anything, and the container's entrypoint (`mcp-server-azuredevops ... --authentication pat`) reads the literal env var `PERSONAL_ACCESS_TOKEN`, not `AZURE_DEVOPS_PAT_B64`. Skip this and the child process starts, then immediately dies with `PERSONAL_ACCESS_TOKEN environment variable is not set or empty` — while Traefik routing and the container itself look completely healthy, so this is easy to misdiagnose as a networking problem. Keep `AZURE_DEVOPS_PAT_B64` too, for consistency with Tower/Windows conventions — duplicate the value under both names.

Never commit `.env` — it's gitignored.

### 16.3 — Verify ADO reachability from cortex (blocking)

Per `connections.md`: ADO writes must originate from an allowlisted IP. Under this shared-hosting design, **all** ADO traffic — Claude Code's and Claudia's — originates from cortex's egress IP instead of Chase's Windows PC. Confirm it's allowlisted before building anything:
```bash
curl -s -u ":$AZURE_DEVOPS_PAT_RAW" "https://dev.azure.com/MAGIQSoftware/_apis/projects?api-version=7.1"
```
A JSON project list back (not a 401/403) means proceed. If it fails, fall back to per-machine local stdio builds instead — the plain `Dockerfile` in `mcp/azure-devops/` (no shared hosting, no cortex-egress dependency, Claude Code keeps running its own local copy on Windows).

### 16.4 — Build & deploy the gateway container

The image lives in the AIS-OS repo, at `mcp/azure-devops/Dockerfile.gateway` — reachable on cortex directly at `/mnt/shared/claudia/magiq/mcp/azure-devops/Dockerfile.gateway`, since that's the same live DS923 share Windows edits (Stage 14/15.5). No separate `git pull` needed to get it onto cortex; whatever's on disk is already there.

```dockerfile
FROM node:22-alpine
RUN npm install -g @azure-devops/mcp@2.7.0 supergateway
EXPOSE 8000
ENTRYPOINT ["npx", "supergateway", \
  "--stdio", "mcp-server-azuredevops MAGIQSoftware --authentication pat -d core work work-items repositories wiki", \
  "--outputTransport", "streamableHttp", \
  "--port", "8000"]
```

Add to `~/stack/docker-compose.yml` (the same authoritative file from Stage 10.3 — edit it directly, don't add snippets elsewhere):

```yaml
  # ── Azure DevOps MCP (shared: Claude Code + Claudia) ────────────────────
  mcp-azure-devops:
    build:
      context: /mnt/shared/claudia/magiq/mcp/azure-devops
      dockerfile: Dockerfile.gateway
    restart: unless-stopped
    env_file:
      - /mnt/shared/claudia/magiq/.env
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.mcp-ado.rule=Host(`mcp-ado.ramonedevelopment.com`)"
      - "traefik.http.routers.mcp-ado.entrypoints=tailnet"
      - "traefik.http.routers.mcp-ado.tls.certresolver=public"
      - "traefik.http.services.mcp-ado.loadbalancer.server.port=8000"
```

```bash
cd ~/stack
docker compose up -d --build mcp-azure-devops
```

Scoping the command to the single service name only builds/recreates that container — Traefik and every other running service are untouched.

**Superseded 2026-07-05:** this used to start with `cd /opt/ais-os && git pull` against a separate deployment clone. That clone no longer exists — `/mnt/shared/claudia/magiq` (the same share Windows edits) is now the only copy, per the standing decision in `decisions/log.md` (2026-07-04, "canonical AIS-OS location: single NAS share, not git-sync between clones") and the equivalent revision made to Control Tower's cortex deployment design. Whatever's on disk in the share is already what this build uses — no pull step required.

**Env var changes need `--force-recreate`, not just a restart** — `env_file:` is only re-read on container creation:
```bash
docker compose -f ~/stack/docker-compose.yml up -d --force-recreate mcp-azure-devops
```

**Resolved 2026-07:** this label block previously used a bare `tls=true` with no certresolver, so Traefik served its self-signed default cert here — same underlying gap as the other four tailnet services, fixed the same way, using the §10.3b pattern. No client-side cert bypass needed for testing anymore.

**No `ports:`/`expose:` mapping is defined on this service** — Traefik reaches it over the internal Docker network only. A bare `curl http://localhost:8000/mcp` run directly on the cortex host will hang/fail; that's not a bug, it just means there's no published host port to hit. Test via the tailnet hostname below, or `docker compose exec` into a container on the same Docker network if you need a from-cortex check.

### 16.5 — Verify

From a tailnet device (e.g. Chase's Windows PC, already on the same Tailscale network it uses for other tailnet-only cortex services):
```bash
curl -s https://mcp-ado.ramonedevelopment.com/mcp \
  -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"smoke-test","version":"0.1"}}}'
```
**No port needed — `:443` (updated 2026-07).** The `tailnet` entrypoint now listens on `:443` (was `:8443` — §10.3), so the bare `https://mcp-ado.ramonedevelopment.com/mcp` is correct. If you have an old `:8443` URL cached anywhere (MCP client config, `.mcp.json`), drop the port. mcp-ado stays tailnet-only — reachable over Tailscale, never on the public entrypoint.

**`Accept` header is required** — a request without `-H "Accept: application/json, text/event-stream"` gets back `{"error":{"code":-32000,"message":"Not Acceptable..."}}`. Expected Streamable HTTP behavior; real MCP clients (Claude Code, `mcp-remote`) send this automatically.

Expect a JSON-RPC `result` containing `protocolVersion`/`capabilities`/`serverInfo`, presented with a real Let's Encrypt cert (§10.3b pattern, no bypass needed) — confirms the gateway, the underlying ADO MCP process, and PAT auth are all working end to end. Note `initialize` requires the full params shape above; an empty `params: {}` returns a schema-validation error (still proves the pipe is wired, just not a successful handshake).

### 16.6 — Wire up Claude Code (Windows)

```bash
claude mcp add --transport http azure-devops https://mcp-ado.ramonedevelopment.com/mcp
```
Or edit `AIS-OS/.mcp.json` (gitignored, machine-local) directly:
```json
{ "mcpServers": { "azure-devops": { "type": "http", "url": "https://mcp-ado.ramonedevelopment.com/mcp" } } }
```
No port needed (`:443`) — see 16.5.

Test: ask Claude Code to list ADO projects. ✅ Verified working 2026-07-04.

### 16.7 — Wire up Claude Desktop (Windows)

**Different mechanism from Claude Code, not just a different config file.** Settings → Connectors → "Add custom connector" in Claude Desktop is a dead end for this setup: per Anthropic's own docs, custom connectors added that way connect to the remote MCP server **from Anthropic's cloud infrastructure**, not from the local machine — true across claude.ai, Cowork, and Desktop alike. Anthropic's servers aren't on the tailnet, so they can't reach a Tailscale-only host like `mcp-ado.ramonedevelopment.com`, and there's no way to allowlist around that without exposing the endpoint publicly — which defeats the point of the `tailnet`-only entrypoint. Don't use the Connectors UI for this.

The working path is Desktop's legacy local-stdio config (`claude_desktop_config.json`), paired with `mcp-remote` — a small Node package bridging stdio (what Desktop speaks) to a remote Streamable HTTP endpoint. Requires Node.js on Windows (`npx`).

`%APPDATA%\Claude\claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "azure-devops": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://mcp-ado.ramonedevelopment.com/mcp"]
    }
  }
}
```

Fully quit and reopen Claude Desktop after editing — MCP config is read at process start, not on window reload. No `--header`/bearer token needed, same as Claude Code: Tailscale reachability is the only gate (see 16.1).

Test: ask "list my ADO projects" in a new Desktop chat. ✅ Verified working 2026-07-04 — returned all 32 MAGIQSoftware projects.

### 16.8 — Wire up Claudia — not yet verified

Claudia runs on the same host as `mcp-azure-devops`, so in principle she can hit `http://localhost:8000/mcp` directly — no tailnet/Traefik hop, no TLS involved at all.

**Second unconfirmed item, don't skip this one:** per 16.4, the compose service has no `ports:`/`expose:` mapping — Traefik reaches it over the internal Docker network only, not a published host port. Since Claudia is a bare-metal systemd process (not a container on that same Docker network), `localhost:8000` may not actually be reachable from her either, for the same reason the direct cortex-host curl test doesn't work. Verify with a plain `curl http://localhost:8000/mcp` from cortex's shell before wiring Claudia's config — if it hangs/fails, either add a `ports: ["127.0.0.1:8000:8000"]` line to the service (loopback-only, safe) or have Claudia go through the tailnet hostname (`https://mcp-ado.ramonedevelopment.com/mcp`) like every other consumer instead.

**Unconfirmed:** whether Hermes' MCP config schema supports an HTTP-transport entry analogous to Claude Code's `"type": "http"`, or stdio-only. Check before wiring — Hermes' own docs/schema for `config.yaml`'s `mcp_servers` block. If supported, conceptually:
```yaml
mcp_servers:
  azure-devops:
    type: http   # verify actual key name against Hermes' schema
    url: http://localhost:8000/mcp
```
Restart after config changes (same gotcha as elsewhere in this guide — the gateway caches profile state at process start):
```bash
claudia gateway restart
```
Test: `claudia chat -q "List my ADO work items."`

---

## Stage 17 — AIS-OS Control Tower (Docker on cortex)

**Why:** Tower is the local dashboard (ADO sprint data, Hermes inbox, decisions, interrupts, team workload) that's normally run interactively on Windows (`python tower/start.py`). This stage hosts it as an always-on container on cortex too, reverse-proxied by Traefik at `tower.ramonedevelopment.com`, same tailnet-only pattern as every other cortex service. Full design rationale, including two superseded approaches (a separate `/opt/ais-os` clone with a git-based autosync timer): `docs/superpowers/specs/2026-07-03-tower-cortex-deployment.md`. Decisions logged 2026-07-03 and 2026-07-05 in `decisions/log.md`.

**Confirmed working 2026-07-05.**

### 17.1 — Requirements & settings checklist

- **No separate deployment clone.** Tower's container bind-mounts `/mnt/shared/claudia/magiq` directly — the same live DS923 share Windows edits (Stage 14/15.5), not a git-synced copy. Whatever's on disk is what the container sees, instantly, no `git pull` involved. This also means `mcp-azure-devops` (Stage 16) and `tower` now build from and read `.env` from the same shared path — there is no `/opt/ais-os` on cortex anymore.
- **Do NOT set `AIOS_ROOT` in `.env`.** `tower/config.py` self-locates the repo root from its own file position specifically so it works regardless of where the repo is mounted. A hardcoded `AIOS_ROOT` (e.g. `/mnt/shared/claudia/magiq`, cortex's own path) breaks every other environment that mounts the same repo somewhere else — confirmed 2026-07-05, a stray `AIOS_ROOT=` line broke startup everywhere except cortex itself with `RuntimeError: Directory '.../tower/static' does not exist`. Leave it unset; `.env.example` shows it commented out for exactly this reason.
- **Required `.env` vars** (same shared file as everything else — see Stage 16.1): `TOWER_TOKEN` (bearer auth for `/api/*` — required once reachable beyond localhost), `TOWER_ALLOWED_ORIGINS` (`https://tower.ramonedevelopment.com` on cortex), `GH_TOKEN` (the container's `gh` CLI has no interactive login), `ANTHROPIC_API_KEY` (email/standup draft generation), `AZURE_DEVOPS_ORG`/`AZURE_DEVOPS_PROJECT`/`AZURE_DEVOPS_PAT` (dashboard ADO cards — separate from the base64 form Stage 16's MCP gateway needs, keep both in sync).
- **`CLAUDIA_BRIDGE_URL` — set for cortex, but read the tradeoff first.** See 17.4. Because Windows/WSL and cortex now share one `.env`, setting this affects both; it's not a simple "set it and forget it" var.
- **Local dev on the CIFS share (WSL or elsewhere) needs the Stage 14.3 gotchas** — `git config --global --add safe.directory` and the `venv` symlink workaround — before you can run `python tower/start.py` directly against `/mnt/shared/claudia/magiq`.

### 17.2 — Add the service to the authoritative compose file

Per Stage 10.3: `~/stack/docker-compose.yml` is the single authoritative file — edit it directly.

```yaml
  # ── AIS-OS Control Tower ────────────────────────────────────────────────
  tower:
    build:
      context: /mnt/shared/claudia/magiq
      dockerfile: tower/Dockerfile
    restart: unless-stopped
    <<: *default-logging
    user: "1000:1000"
    env_file:
      - /mnt/shared/claudia/magiq/.env
    volumes:
      - /mnt/shared/claudia/magiq:/app
    extra_hosts:
      - "host.docker.internal:host-gateway"
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.tower.rule=Host(`tower.ramonedevelopment.com`)"
      - "traefik.http.routers.tower.entrypoints=tailnet"
      - "traefik.http.routers.tower.tls.certresolver=public"
      - "traefik.http.services.tower.loadbalancer.server.port=8765"
```

Notes on this block:
- `user: "1000:1000"` — least-privilege choice, not a requirement. Verified 2026-07-05 directly against the live CIFS mount (`forceuid,forcegid,file_mode=0755,dir_mode=0755`): writes work both as root (default, no `user:` line) and as UID 1000 (owner-match). Either works; this is the cleaner one.
- `<<: *default-logging` — the same log-rotation anchor every other service in this file uses (`x-logging` at the top); without it, Tower's container logs grow unbounded under Docker's default json-file driver.
- `tls.certresolver=public` (not bare `tls=true`) — the §10.3b pattern, same as every other tailnet-only router.
- `extra_hosts: host-gateway` — same mechanism Open WebUI uses to reach Ollama; here it's what lets the container reach the claudia-bridge (17.4) on the host.

```bash
cd ~/stack
python3 -c "import yaml; yaml.safe_load(open('docker-compose.yml'))" && echo "YAML OK"
docker compose up -d --build tower
```

### 17.3 — Verify

```bash
TOKEN=$(grep '^TOWER_TOKEN=' /mnt/shared/claudia/magiq/.env | cut -d= -f2)
curl -s https://tower.ramonedevelopment.com/api/health \
  -H "Accept: application/json" -H "Authorization: Bearer $TOKEN"
```
No port needed — `:443`, the bare hostname (see 16.5; the tailnet entrypoint moved off `:8443` in §10.3). Expect `{"status":"ok","sources":{...}}` with `projects`/`decisions`/`interrupts` all `true`. `ado`/`github` being `true` here only means the credentials/CLI are present, not that a live connection succeeded — those aren't real connectivity probes (see `tower/server.py`'s `health()`).

### 17.4 — Claudia bridge (for the "Ask Claudia" feature)

Tower's container can't reach Claudia (bare-metal, systemd, not Docker) directly, so a small host-side HTTP bridge sits in between. Full detail: `scripts/claudia-bridge/server.py`'s docstring and the spec's "Claudia integration" section.

```bash
mkdir -p ~/.config/systemd/user
cp /mnt/shared/claudia/magiq/scripts/claudia-bridge/claudia-bridge.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now claudia-bridge.service
systemctl --user status claudia-bridge.service
```

**Before enabling, verify the CLI invocation** the bridge assumes (`claudia chat -q "<message>" --yolo`) is actually correct:
```bash
which claudia
claudia chat -q "test" --yolo
```
If the real invocation differs, `CLAUDIA_CMD` in `scripts/claudia-bridge/server.py` is the only line that needs to change.

**The `CLAUDIA_BRIDGE_URL` tradeoff:** Windows/WSL and cortex share one `.env` file. Setting `CLAUDIA_BRIDGE_URL=http://host.docker.internal:8901` there makes "Ask Claudia" work from cortex's containerized Tower — but a Windows/WSL dev instance (`python tower/start.py`, not in Docker) will also try to reach `host.docker.internal`, which doesn't resolve outside a container, so "Ask Claudia" specifically fails there while every other feature keeps working. There's no single value that makes it work in both places at once with the current design. Pick based on where you'll actually use that one feature.

**Security:** the bridge binds `127.0.0.1:8901` only — never the tailnet or a public entrypoint. It shells out with `--yolo` (no confirmation prompts), so anything that can reach `/chat` can make Claudia execute non-interactively. Localhost-only binding is the entire access control; don't change that without adding a real auth layer first.

Restart after any config change (same gotcha as Claudia's own gateway — cached state at process start):
```bash
systemctl --user restart claudia-bridge.service
```

### 17.5 — Known gotchas, quick reference

- **CIFS write permissions:** resolved — see 17.2's note. No `noperm` remount or other mount changes needed.
- **Availability coupling (accepted, not a bug):** Tower on cortex now depends on the DS923 SMB mount staying up, same as Claudia already does. If Tailscale or the NAS drops, Tower's container errors/hangs on file access until it recovers — unlike the retired `/opt/ais-os` local-disk-clone design, which ran standalone regardless of NAS availability.
- **`AIOS_ROOT`:** see 17.1 — leave it unset, always.
- **`CLAUDIA_BRIDGE_URL`:** see 17.4 — one shared `.env`, one tradeoff, pick a side.

---

## Stage 18 — Uptime Kuma (Status Monitoring)

**Why:** Netdata (Stage 10.6) covers CPU/RAM/resource pressure. It doesn't give you an at-a-glance up/down history or alerting per service. Uptime Kuma fills that gap — one lightweight container, same tailnet-only Traefik pattern as everything else. Added 2026-07-05 as part of the admin-UI gap review.

### 18.1 — Service definition

Already added to `~/stack/docker-compose.yml` (the single authoritative file — Stage 10.3):

```yaml
  uptime-kuma:
    image: louislam/uptime-kuma:1
    restart: unless-stopped
    <<: *default-logging
    volumes:
      - kuma_data:/app/data
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.kuma.rule=Host(`status.ramonedevelopment.com`)"
      - "traefik.http.routers.kuma.entrypoints=tailnet"
      - "traefik.http.routers.kuma.tls.certresolver=public"
      - "traefik.http.services.kuma.loadbalancer.server.port=3001"
```

Add `kuma_data:` to the top-level `volumes:` block.

### 18.2 — Bring it up

```bash
cd ~/stack
python3 -c "import yaml; yaml.safe_load(open('docker-compose.yml'))" && echo "YAML OK"
docker compose up -d uptime-kuma
```

### 18.3 — First-run setup

`https://status.ramonedevelopment.com` — first account created becomes admin (same pattern as Open WebUI/Seq).

### 18.4 — Adding monitors: bridge network vs host network matters here

**Gotcha to plan around, not hit by surprise:** Kuma's container is on the default Docker bridge network, not `network_mode: host`. If you add a monitor pointing at a tailnet hostname like `https://chat.ramonedevelopment.com`, it will fail — Kuma's container resolves that hostname via normal outbound DNS (not `dns-internal`, which only binds the `tailscale0` interface). Since the wildcard record was removed (§4.5.1), public DNS returns **no record** for tailnet-only hosts, so the monitor can't even resolve them. It'll look like every monitor is down when the services are actually fine. Fix: point Kuma monitors at the tailscale IP directly, or at the container over the compose bridge network — not the public hostname.

Two correct patterns instead:

- **Services sharing the bridge network** (mysql, sqlserver, redis-stack, seq, portainer, open-webui, cloudbeaver, tower, mcp-azure-devops, whoami-test — anything without `network_mode: host`): monitor by **Docker service name + internal container port**, e.g. `http://mcp-azure-devops:8000/mcp`, `http://cloudbeaver:8978`, `http://tower:8765/api/health`, `http://redis-stack:8001`. This resolves via Docker's embedded DNS with zero dependency on Tailscale/Traefik — confirm the exact internal port per service with `docker port <container>` before saving, since several services (seq, portainer, open-webui) don't declare an explicit `loadbalancer.server.port` label and rely on Traefik's own auto-detection.
- **Host-network services** (traefik, netdata, dns-internal): monitor via cortex's **Tailscale IP directly**, not the hostname — a bridge container can still route to the host's own IPs. Netdata: `http://100.90.195.22:19999`. Traefik dashboard: needs the `Host` header set to `traefik.ramonedevelopment.com` in Kuma's monitor advanced options (SNI/Host-based routing means a bare IP hit 404s otherwise). `dns-internal`: use Kuma's built-in **DNS monitor type** against resolver `100.90.195.22`, query any `*.ramonedevelopment.com` name, expect it to resolve to `100.90.195.22`.

---

## Stage 19 — CloudBeaver (SQL Admin UI)

**Why:** MySQL and SQL Server have had TCP-only access since Stage 10.3 — no browser-based query/admin tool. CloudBeaver covers both engines from one container, same tailnet pattern as everything else. Added 2026-07-05.

### 19.1 — Service definition

Already added to `~/stack/docker-compose.yml`:

```yaml
  cloudbeaver:
    image: dbeaver/cloudbeaver:latest
    restart: unless-stopped
    <<: *default-logging
    volumes:
      - cloudbeaver_data:/opt/cloudbeaver/workspace
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.cloudbeaver.rule=Host(`sql.ramonedevelopment.com`)"
      - "traefik.http.routers.cloudbeaver.entrypoints=tailnet"
      - "traefik.http.routers.cloudbeaver.tls.certresolver=public"
      - "traefik.http.services.cloudbeaver.loadbalancer.server.port=8978"
```

Add `cloudbeaver_data:` to the top-level `volumes:` block.

### 19.2 — Bring it up

```bash
cd ~/stack
docker compose up -d cloudbeaver
```

### 19.3 — First-run setup

`https://sql.ramonedevelopment.com` — CloudBeaver CE prompts you to create the admin account and a workspace on first load (no pre-seeded connections via compose; the CE edition doesn't support that without the enterprise config API).

### 19.4 — Add the two database connections

Both databases are reachable by **Docker service name** over the same default compose network CloudBeaver sits on — no Tailscale hop needed:

- **MySQL:** New Connection → MySQL → Host `mysql`, Port `3306`, user `root`, password = `MYSQL_ROOT_PASSWORD` from `.env`.
- **SQL Server:** New Connection → SQL Server → Host `sqlserver`, Port `1433`, user `sa`, password = `SA_PASSWORD` from `.env`. CloudBeaver will prompt to download the MS SQL JDBC driver on first connection — needs outbound internet from cortex (Maven Central), same egress consideration flagged in Stage 16.1 for the ADO PAT.

### 19.5 — Note on access control

CloudBeaver CE has one global admin config, no per-user granular permissions — fine for single-operator use here. If this ever needs multi-user access control, that's an Enterprise-edition feature, not a CE gap to work around.

---

## Stage 20 — Traefik Dashboard

**Why:** With ADO MCP, Tower, Kuma, and CloudBeaver all routing through Traefik now, the routing table has grown past what's easy to reason about from `docker compose logs traefik` alone. The dashboard gives a live view of routers/services/middlewares. Added 2026-07-05.

### 20.1 — Enable it

Two changes to the existing `traefik` service in `~/stack/docker-compose.yml` — add the flag to `command:`, and add a `labels:` block (the service had none before, since it never routed to itself):

```yaml
    command:
      # ...existing flags unchanged...
      - "--api.dashboard=true"
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.traefik-dashboard.rule=Host(`traefik.ramonedevelopment.com`)"
      - "traefik.http.routers.traefik-dashboard.entrypoints=tailnet"
      - "traefik.http.routers.traefik-dashboard.tls.certresolver=public"
      - "traefik.http.routers.traefik-dashboard.service=api@internal"
```

`api@internal` is Traefik's built-in virtual service for its own API — no separate container. Same §10.3b cert pattern as every other tailnet-only router here.

**No extra basic-auth middleware added.** Tailscale-only reachability is already this whole stack's security boundary (same as Portainer, Seq, RedisInsight) — not treating the dashboard as a special case that needs more.

### 20.2 — Redeploy

Command-line changes need a recreate, not just a restart (same rule as `env_file` changes elsewhere in this guide):

```bash
cd ~/stack
docker compose up -d --force-recreate traefik
```

### 20.3 — Verify

```bash
curl -s https://traefik.ramonedevelopment.com/api/overview \
  -H "Host: traefik.ramonedevelopment.com" | jq .
```

Expect JSON with router/service/middleware counts. Then load `https://traefik.ramonedevelopment.com` in a browser for the visual dashboard.

---

## Stage 21 — Homepage (Landing Page)

**Decision:** Homepage (`gethomepage/homepage`), not Dashy. Both are YAML-config, git-trackable options; Homepage won because it supports **Docker-label auto-discovery** — a new service's dashboard tile is added with the same edit that adds its `traefik.*` labels, no second file to remember to update. Dashy's differentiator (in-browser drag-and-drop config editor) solves a problem this guide's whole workflow doesn't have — direct YAML editing is already the norm here. Decided 2026-07-05, see `decisions/log.md`.

### 21.1 — Service definition

Already added to `~/stack/docker-compose.yml`:

```yaml
  homepage:
    image: ghcr.io/gethomepage/homepage:latest
    restart: unless-stopped
    <<: *default-logging
    environment:
      HOMEPAGE_ALLOWED_HOSTS: "home.ramonedevelopment.com"
    volumes:
      - /mnt/shared/claudia/magiq/homepage-config:/app/config
      - /var/run/docker.sock:/var/run/docker.sock:ro
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.homepage.rule=Host(`home.ramonedevelopment.com`)"
      - "traefik.http.routers.homepage.entrypoints=tailnet"
      - "traefik.http.routers.homepage.tls.certresolver=public"
      - "traefik.http.services.homepage.loadbalancer.server.port=3000"
```

Config is a **bind mount into the magiq repo** (`homepage-config/`), not a named volume — same reasoning as Tower's bind mount (Stage 17): it's editable directly and versioned alongside `docker-compose.yml`, no `docker exec` needed to change a tile. The `docker.sock` mount is read-only — Homepage only needs it to read labels and (optionally) container stats, never to manage containers.

**Gotcha confirmed 2026-07-05:** Homepage's base image ships on Next.js 16, which added its own Host-header validation independent of Traefik. Without `HOMEPAGE_ALLOWED_HOSTS`, every request 500s with `Host validation failed for: home.ramonedevelopment.com` in the container logs even though Traefik routing, the cert, and the container itself are all fine — easy to misdiagnose as a Traefik problem. The value must be the literal `Host` header Traefik forwards through unchanged — on the `:443` tailnet entrypoint (§10.3) that's the **bare hostname, no port** (`home.ramonedevelopment.com`). (It used to require `:8443` when the entrypoint was on that port.) If you ever add a second hostname pointing at this container, comma-separate both in the same env var.

### 21.2 — Config files

Four files now live in `/mnt/shared/claudia/magiq/homepage-config/` (== `Z:\claudia\magiq\homepage-config\` from Windows):

- **`settings.yaml`** — title, theme, and a `layout:` block defining four groups (`AI`, `Infrastructure`, `Data`, `Ops`) with column counts. Group names here must match `homepage.group` label values exactly (case-sensitive) or a service falls into an unstyled default group.
- **`docker.yaml`** — registers the local socket as a Docker provider (`my-docker: socket: /var/run/docker.sock`). This is what turns on label discovery.
- **`services.yaml`** — manual entries only, for things that aren't Docker containers and so can't carry a label. Currently just **Cockpit** (`https://100.90.195.22:9090`), grouped under `Infrastructure` so it merges with the label-discovered Traefik/Portainer/Netdata tiles in the same section.
- **`bookmarks.yaml`** / **`widgets.yaml`** — present but empty/placeholder. Homepage supports a live resource widget here, but it needs the same `/proc`/`/sys`/docker.sock mounts Netdata (Stage 10.6) already provides — skipped since Netdata already does that job; revisit only if a single-glance top-of-page summary becomes worth the duplicated mounts.

### 21.3 — Label convention for future services

**Every service that gets a set of `traefik.*` labels for routing should also get a matching set of `homepage.*` labels in the same edit** — this is now the standing convention for this file, not a one-off:

```yaml
      - "homepage.group=<AI|Infrastructure|Data|Ops>"
      - "homepage.name=<Display Name>"
      - "homepage.icon=<icon-slug>.png"
      - "homepage.href=https://<subdomain>.ramonedevelopment.com"
      - "homepage.description=<one line>"
```

Icon slugs come from Homepage's bundled icon set (`walkxcode`/`selfh.st` icons) — if a slug doesn't resolve, the tile just renders without an icon (non-breaking), swap it later via Homepage's icon picker. Ten services carry these labels today: CloudBeaver, Azure DevOps MCP, Netdata, Open WebUI, Portainer, RedisInsight, Seq, AIS-OS Tower, Traefik, and Uptime Kuma.

### 21.4 — Bring it up

```bash
cd ~/stack
python3 -c "import yaml; yaml.safe_load(open('docker-compose.yml'))" && echo "YAML OK"
docker compose up -d homepage
```

### 21.5 — Verify

`https://home.ramonedevelopment.com` — expect four grouped sections (AI, Infrastructure, Data, Ops) with all ten labeled tiles plus the manually-added Cockpit tile under Infrastructure. If a tile is missing, check its container's labels landed correctly (`docker inspect <container> --format '{{json .Config.Labels}}'`) and that `homepage.group` matches a `layout:` key in `settings.yaml` exactly.

---

## Stage 22 — Secrets Hygiene: `.env` Variable Substitution

> Moved to `/mnt/shared/cortex/docs/setup/22-secrets-local-env.md` as of 2026-08-25.

---

## Stage 23 — Authentik (Identity Provider / SSO)

**Added 2026-07-14.** One identity for the tailnet admin fleet, and the mechanism that lets Control Tower go public safely. Depends on the `:443` tailnet entrypoint and Cloudflare DNS-01 from §10.3 (both updated 2026-07) — do those first.

Two integration modes, both driven by a single reusable Traefik middleware defined on the Authentik server:
- **Forward-auth, domain-level** — one Authentik proxy provider gates every tailnet UI that has no login of its own (`home.`, `redis.`, `traefik.`) with one shared `ramonedevelopment.com` cookie. Anyone who can authenticate gets in (fine for tailnet-only admin UIs).
- **Forward-auth, single-application** — a dedicated provider + group policy per host, used for anything **public** or anything that must be **restricted to specific users**. Control Tower uses this.
- **Native OIDC** (not covered step-by-step here) — the right integration for apps that have their own user DB (`portainer.`, `open-webui`, `seq.`, `cloudbeaver`) so they don't double-prompt. Configure per-app in the Authentik UI after this stage.

Deliberately **not** gated: `mcp-azure-devops` (machine API — a browser redirect breaks the MCP client) and `netdata` (host-network, bypasses Traefik).

### 23.1 — Services (authentik-postgresql, authentik-server, authentik-worker)

Authentik hard-requires PostgreSQL (the stack had none — only mysql/mssql), so this adds a dedicated Postgres. Redis is **reused** from the existing `redis-stack` (DB 0 — nothing else uses it). Add to `docker-compose.yml`:

```yaml
  authentik-postgresql:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_USER: authentik
      POSTGRES_DB: authentik
      POSTGRES_PASSWORD: ${AUTHENTIK_PG_PASS}
    volumes: [ authentik_pg:/var/lib/postgresql/data ]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U authentik"]
      interval: 10s
      timeout: 5s
      retries: 5

  authentik-server:
    image: ghcr.io/goauthentik/server:${AUTHENTIK_TAG:-2025.12}
    restart: unless-stopped
    command: server
    environment:
      AUTHENTIK_SECRET_KEY: ${AUTHENTIK_SECRET_KEY}
      AUTHENTIK_POSTGRESQL__HOST: authentik-postgresql
      AUTHENTIK_POSTGRESQL__USER: authentik
      AUTHENTIK_POSTGRESQL__NAME: authentik
      AUTHENTIK_POSTGRESQL__PASSWORD: ${AUTHENTIK_PG_PASS}
      AUTHENTIK_REDIS__HOST: redis-stack
      AUTHENTIK_BOOTSTRAP_PASSWORD: ${AUTHENTIK_BOOTSTRAP_PASSWORD}
      AUTHENTIK_BOOTSTRAP_EMAIL: <your-email>
    volumes: [ authentik_media:/media, authentik_certs:/certs ]
    ports:
      # HOST-LOOPBACK ONLY. Traefik runs network_mode: host and can't resolve the
      # container by service name for the forward-auth sub-request, so it hits the
      # embedded outpost at 127.0.0.1:9000 instead. Never bind this to tailscale/public.
      - "127.0.0.1:9000:9000"
    depends_on:
      authentik-postgresql: { condition: service_healthy }
      redis-stack: { condition: service_healthy }
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.authentik.rule=Host(`login.ramonedevelopment.com`)"
      # tailnet + PUBLIC: public visitors to tower get redirected here to log in (23.6).
      - "traefik.http.routers.authentik.entrypoints=tailnet,websecure"
      - "traefik.http.routers.authentik.tls.certresolver=public"
      - "traefik.http.services.authentik.loadbalancer.server.port=9000"
      # Reusable forward-auth middleware (embedded outpost), referenced as authentik@docker:
      - "traefik.http.middlewares.authentik.forwardauth.address=http://127.0.0.1:9000/outpost.goauthentik.io/auth/traefik"
      - "traefik.http.middlewares.authentik.forwardauth.trustForwardHeader=true"
      - "traefik.http.middlewares.authentik.forwardauth.authResponseHeaders=X-authentik-username,X-authentik-groups,X-authentik-email,X-authentik-name,X-authentik-uid,X-authentik-jwt,X-authentik-meta-jwks,X-authentik-meta-outpost,X-authentik-meta-provider,X-authentik-meta-app,X-authentik-meta-version,X-authentik-entitlements"
      - "homepage.group=Ops"
      - "homepage.name=Authentik"
      - "homepage.icon=authentik.png"
      - "homepage.href=https://login.ramonedevelopment.com"

  authentik-worker:
    image: ghcr.io/goauthentik/server:${AUTHENTIK_TAG:-2025.12}
    restart: unless-stopped
    command: worker
    environment:
      AUTHENTIK_SECRET_KEY: ${AUTHENTIK_SECRET_KEY}
      AUTHENTIK_POSTGRESQL__HOST: authentik-postgresql
      AUTHENTIK_POSTGRESQL__USER: authentik
      AUTHENTIK_POSTGRESQL__NAME: authentik
      AUTHENTIK_POSTGRESQL__PASSWORD: ${AUTHENTIK_PG_PASS}
      AUTHENTIK_REDIS__HOST: redis-stack
    volumes: [ authentik_media:/media, authentik_certs:/certs ]
    depends_on:
      authentik-postgresql: { condition: service_healthy }
      redis-stack: { condition: service_healthy }
      authentik-server: { condition: service_healthy }
    # No docker.sock mount (least-privilege). The embedded outpost runs inside
    # authentik-server; the worker only needs Docker if you run SEPARATE outposts.
```

Add the named volumes: `authentik_pg`, `authentik_media`, `authentik_certs`.

Secrets in `~/stack/.env` (generate on cortex, never over the share):
```bash
echo "AUTHENTIK_SECRET_KEY=$(openssl rand -base64 60 | tr -d '\n')" >> ~/stack/.env
echo "AUTHENTIK_PG_PASS=$(openssl rand -base64 36 | tr -d '\n')"    >> ~/stack/.env   # Postgres caps at 99 chars
echo "AUTHENTIK_BOOTSTRAP_PASSWORD=<pick a strong one>"             >> ~/stack/.env
```

### 23.2 — Bring it up + first boot

```bash
cd ~/stack && docker compose up -d authentik-postgresql authentik-server authentik-worker
docker compose ps            # postgres healthy; server/worker go healthy after first-boot migrations (1-3 min)
```

**Gotchas seen during the real build:**
- A blank `AUTHENTIK_PG_PASS` makes Postgres refuse to init ("superuser password not specified") → unhealthy → server/worker blocked. Fill the secrets *before* `up`.
- **Traefik hides unhealthy containers** — until `authentik-server` is `(healthy)`, Traefik builds no router/service/middleware for it, so `login.` serves the default self-signed cert and every `authentik@docker` reference logs "does not exist". This clears the moment it's healthy. First boot just takes a few minutes for migrations.
- The `POSTGRES_PASSWORD ... using fallback` warning in the server log is benign — `AUTHENTIK_POSTGRESQL__PASSWORD` is what connects (`PostgreSQL connection successful` on the next line).

Then open **`https://login.ramonedevelopment.com/if/flow/initial-setup/`** from a tailnet device and set the `akadmin` password (or log in with `AUTHENTIK_BOOTSTRAP_PASSWORD`).

### 23.3 — Domain-level gate for the tailnet UIs (home / redis / traefik)

On each of those three routers in `docker-compose.yml`, add just the middleware:
```yaml
      - "traefik.http.routers.<name>.middlewares=authentik@docker"
```
Then in the Authentik UI:
1. **Providers → Create → Proxy Provider** `ramonedev-fwd`: Mode **Forward auth (domain level)**, External host `https://login.ramonedevelopment.com` (no port), **Cookie domain `ramonedevelopment.com`**.
2. **Applications → Create** `Ramone Dev SSO`, provider `ramonedev-fwd`.
3. **Outposts → edit the embedded outpost → add the application.**

> **Critical: domain-level forward auth requires `:443` (authentik #12503).** On a non-443 port the browser Host header carries the port (`home.ramonedevelopment.com:8443`), which fails the outpost's cookie-domain suffix match → the request falls through to authentik core and 404s (`logger=authentik.asgi ... status=404`). This is the whole reason §10.3's tailnet entrypoint was moved to `:443`. Single-application mode (23.6) matches by exact host and works on any port, but domain-level does not.

### 23.4 — Public Control Tower, restricted to a group (single-application)

Tower is the one host exposed to the internet, so it gets its own provider + a group policy instead of riding the domain-level gate (which can't restrict per-app). Tower's router (Stage 17) becomes:
```yaml
      - "traefik.http.routers.tower.entrypoints=tailnet,websecure"   # public + tailnet
      - "traefik.http.routers.tower.middlewares=authentik@docker"
      # per-host outpost router for the login callback (single-app needs this; domain-level doesn't):
      - "traefik.http.routers.tower-outpost.rule=Host(`tower.ramonedevelopment.com`) && PathPrefix(`/outpost.goauthentik.io/`)"
      - "traefik.http.routers.tower-outpost.entrypoints=tailnet,websecure"
      - "traefik.http.routers.tower-outpost.tls.certresolver=public"
      - "traefik.http.routers.tower-outpost.service=authentik@docker"
```
Tower keeps its own `TOWER_TOKEN` bearer auth underneath — defense in depth.

Authentik UI:
1. **Directory → Groups → Create** `tower-users`; add the users allowed in. **Superuser does not bypass this** — even `akadmin` must be a member (or bound) to get through.
2. **Providers → Create → Proxy Provider** `tower-fwd`: Mode **Forward auth (single application)**, External host **`https://tower.ramonedevelopment.com`** (the app's own URL — *not* `login.`; getting this wrong is a 404).
3. **Applications → Create** `Tower`, provider `tower-fwd` → **Bindings** tab → **bind the `tower-users` group** (this is the access restriction).
4. **Outposts → embedded → add `Tower`.**

Exact-host (`tower-fwd`) beats domain-level (`ramonedev-fwd`), so Tower's restrictive policy wins even though it's under the same domain.

**Expose it (public path in):**
- **Cloudflare → SSL/TLS → Overview → Full (Strict)** (Traefik serves a valid LE cert). Never Flexible.
- **Router:** forward WAN `:443` → cortex LAN IP `:443` (§4.5.2).
- **cortex firewall:** `sudo ufw allow in on <lan-nic> to any port 443 proto tcp`.
- **Public DNS + DDNS:** handled by the `cloudflare-ddns` service (23.5) — it creates/maintains `login.` and `tower.` A records (proxied) at the current WAN IP.

### 23.5 — Dynamic DNS (favonia/cloudflare-ddns)

Replaces the old No-IP DDNS. Reuses the same `CF_DNS_API_TOKEN` as Traefik's DNS-01. Add:
```yaml
  cloudflare-ddns:
    image: favonia/cloudflare-ddns:latest
    restart: unless-stopped
    user: "1000:1000"
    read_only: true
    cap_drop: [ all ]
    security_opt: [ "no-new-privileges:true" ]
    environment:
      CLOUDFLARE_API_TOKEN: ${CF_DNS_API_TOKEN}
      DOMAINS: tower.ramonedevelopment.com,login.ramonedevelopment.com   # the ONLY public hosts
      PROXIED: "true"          # orange-cloud — hides WAN IP, adds WAF. "false" for DNS-only.
      IP6_PROVIDER: none
```
`docker compose up -d cloudflare-ddns` → it detects the WAN IP via Cloudflare's trace, **creates** the two records if missing, and rechecks every 5 min. Because they're proxied, a public `nslookup` returns Cloudflare edge IPs, not your WAN IP — verify the origin in the Cloudflare dashboard, not via nslookup.

### 23.6 — MFA + hardening (the login is now internet-facing)

1. **Enroll first, enforce second** (or you risk a broken enrollment loop). As each user: **Settings (`/if/user/`) → MFA Devices → Enroll** a TOTP or WebAuthn/passkey, plus **Static** recovery codes. Do this for your own user *and* `akadmin`.
2. **Enforce:** Flows → Stages → the authenticator-validate stage in the default auth flow (`default-authentication-mfa-validation`) → set **Not configured action = "Force the user to configure an authenticator"**, check device classes, and add a TOTP/WebAuthn setup stage under Configuration stages.
3. Create a **personal admin user** (add to `authentik Admins` + `tower-users`) and use it daily; keep `akadmin` as break-glass only — strong password + MFA + recovery codes, don't disable it.
4. Confirm the default auth flow keeps its reputation/brute-force policies (ships by default).

### 23.7 — Known gotcha: the embedded outpost caches

The embedded outpost keeps its provider list in memory. **After any provider/binding change it won't take effect until `authentik-server` restarts:**
```bash
docker compose restart authentik-server
```
If a host still 404s after that, dump the live state — this is the fastest diagnostic:
```bash
docker compose exec authentik-server ak shell -c "
from authentik.outposts.models import Outpost
from authentik.providers.proxy.models import ProxyProvider
o=Outpost.objects.get(managed='goauthentik.io/outposts/embedded')
print('OUTPOST PROVIDERS:', [p.name for p in o.providers.all()])
for p in ProxyProvider.objects.all():
    print(p.name,'| mode=',p.mode,'| ext=',p.external_host,'| cookie=',repr(p.cookie_domain))
"
```
Correct end state: `ramonedev-fwd | forward_domain | ext=https://login... | cookie='ramonedevelopment.com'` and `tower-fwd | forward_single | ext=https://tower... | cookie=''`, both bound to the outpost. A single-app provider whose `ext` points at `login.` instead of its own host is the classic 404.

### 23.8 — Verify

- Tailnet: `https://home.ramonedevelopment.com` → Authentik login → back to Homepage; `redis.`/`traefik.` then pass with no second login (shared cookie).
- Public (phone on cellular): `https://tower.ramonedevelopment.com` → Authentik login → a `tower-users` member gets in, a non-member is denied ("Permission denied, Policy binding returned False" = the restriction working).
- Watch the flow: `docker compose logs -f authentik-server 2>&1 | grep auth/traefik` — want `302` then `200`, not `404`.

---

## Windows PC Checklist — Consolidated

Every item below is already covered inline at the stage listed — this section just collects them into one pass so nothing on the Windows side gets missed. Work top to bottom; each depends on the one above it being done.

| # | Task | Needed for | Stage |
|---|---|---|---|
| 1 | Install WSL2 (`wsl --install` in an admin PowerShell, reboot) | Running Claude Code's bash tool, `python tower/start.py` locally | prereq (implicit, before Stage 2) |
| 2 | Generate SSH keypair (`ssh-keygen -t ed25519 -C "cortex"`), stage public key during Ubuntu install | Passwordless SSH to cortex | 2 |
| 3 | Copy the same private key into WSL (`~/.ssh/`, `chmod 600`) — don't generate a second pair | Both Windows OpenSSH *and* WSL need to SSH to cortex non-interactively | 2 |
| 4 | Verify both contexts: `ssh chase@cortex echo ok` from PowerShell **and** from WSL, no prompt either way | Confirms step 3 actually worked | 2 |
| 5 | Install Tailscale (Windows native client) | Reaching cortex/DS923 without port-forwarding | 5 |
| 6 | Map network drive: `\\<ds923-tailnet-name>\shared` → `Z:\` | File access to the shared workspace, and to the magiq repo itself | 14.2 |
| 7 | In WSL: mount the same share via CIFS, add `git config --global --add safe.directory /mnt/shared/claudia/magiq`, and create any Python venvs on local disk (not on the CIFS mount) | Working on the magiq repo from WSL without the dubious-ownership or symlink-venv failures | 14.3 |
| 8 | Clone or scaffold the magiq repo onto `Z:\claudia\magiq` (from Windows/WSL, not from cortex) | cortex sees it automatically via the same share — no separate clone step on cortex | 15.5 |
| 9 | Install Node.js on Windows (needed for `npx`) | Running `mcp-remote` for Claude Desktop's MCP bridge | 16.7 |
| 10 | Wire Claude Code: `claude mcp add --transport http azure-devops https://mcp-ado.ramonedevelopment.com/mcp` (or edit `.mcp.json`) | ADO tools inside Claude Code | 16.6 |
| 11 | Wire Claude Desktop: edit `%APPDATA%\Claude\claude_desktop_config.json`, fully quit + reopen Desktop after | ADO tools inside Claude Desktop (Connectors UI does **not** work here — see 16.7 for why) | 16.7 |

**Optional (phone, not PC):** Tailscale + Termius app, for SSH access from an iPhone (Stage 4).

**Migration note (existing installs, 2026-07):** when the tailnet entrypoint moved `:8443`→`:443` (§10.3), any Windows-side config with a cached `:8443` URL must drop the port — `.mcp.json`, `%APPDATA%\Claude\claude_desktop_config.json` (the `mcp-ado` URL), and any browser bookmarks. Fresh setups following items 10-11 above already use the no-port form.

---

## Quick Reference — What's Physical vs Remote

| Stage | Physical needed? |
|---|---|
| 0. Unboxing | Yes |
| 1. BIOS config | **Yes** |
| 2. USB prep | No (separate machine) |
| 3. Ubuntu install | **Yes** (last physical step) |
| 4-23. Everything else (incl. 4.5 network/firewall baseline, 5.5 dual-NIC priority, 23 Authentik/SSO) | No — fully remote via Tailscale + SSH, plus a browser for the Authentik UI + Cloudflare/router config in Stage 23 |

Total physical time: roughly 20-30 minutes across Stages 0-3, all up front.
