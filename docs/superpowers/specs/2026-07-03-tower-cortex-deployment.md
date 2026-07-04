# Control Tower on Cortex — Deployment Design

**Date:** 2026-07-03
**Status:** Approved — ready to implement
**Owner:** Chase

**Goal:** Tower runs as a Docker container on Cortex, reverse-proxied by Traefik at `tower.ramonedevelopment.com`, while staying actively developed day-to-day from Windows.

---

## Decisions

**Exposure: Tailscale-only, not public.**
Every other Cortex service (Seq, Portainer, Open WebUI) sits behind the `tailnet` entrypoint despite the same-looking `ramonedevelopment.com` hostname — only ACME uses `websecure`/public. Tower holds ADO items, decisions, and customer/interrupt data. It follows the existing pattern rather than becoming the first public exception.

**Deploy trigger: manual pull + build on Cortex.**
`git pull && docker compose up -d --build tower` — one command, no registry, no CI, no Watchtower. Matches homelab scale. Revisit only if manual deploys become actual friction (3-use rule).

**Data model: Cortex clone is the live-data publisher; Windows stays the editing copy.**
Precedent: Hermes already writes directly into the git-tracked AIS-OS repo on Windows (see `hermes-integration.md`) — no JSON handoff, git is the sync layer. Same pattern extended across machines: Cortex gets its own clone at `/opt/ais-os`, Tower reads/writes it directly (bind-mounted into the container), and a timer auto-commits + pushes so Windows can `git pull` and see Tower-originated changes (interrupts, decisions added via the UI, notes/todos edits).

**Image = runtime only, not code.**
The Docker image bundles Python + dependencies + `git`/`gh` CLI. The `/opt/ais-os` clone is bind-mounted into the container at `/app`. Code changes take effect on container restart with no rebuild; rebuild only when `tower/requirements.txt` changes. Reproducible (versioned image) and cleanly separated (runtime vs. code/data) without needing a registry.

---

## Architecture

```
Windows (Chase, interactive editing)          Cortex (Chase, always-on)
┌─────────────────────────────┐               ┌──────────────────────────────┐
│ C:\...\AIS-OS                │  git push/pull │ /opt/ais-os                  │
│  - Claude Code / Cowork edit │◄──────────────►│  - bind-mounted into `tower` │
│  - python tower/start.py     │   GitHub        │    container at /app        │
│    (--reload, local dev)     │  cramone/ais-os │  - tower-autosync.sh timer  │
└─────────────────────────────┘               │    auto-commits Tower writes │
                                                │  - Traefik: tower.ramone     │
                                                │    development.com (tailnet)│
                                                └──────────────────────────────┘
```

Two things had to be possible; here's how each is satisfied:

1. **Active development** — unchanged. Keep running `python tower/start.py` on Windows for the fast inner loop (`--reload`, no Docker). Docker is a deploy target, not a dev requirement.
2. **Build + host as a container on change** — `tower/deploy-cortex.sh` on Cortex: `git pull` → `docker compose up -d --build tower`. Run it after pushing from Windows, or straight from a Claude Code / Claudia session on Cortex.

---

## What's already built (no new work needed)

- `tower/config.py` self-locates `AIOS_ROOT` from its own file position — the bind mount at `/app` resolves correctly with zero path config.
- `TOWER_TOKEN` bearer-auth middleware already gates `/api/*`, and the frontend (`static/index.html`) already attaches it from a stored token — auth is deploy-ready.
- `.env` / `.mcp.json` are gitignored — secrets never touch the repo history.

## What this work added

| File | Purpose |
|---|---|
| `tower/Dockerfile` | Runtime image: Python 3.12-slim + `tower/requirements.txt` + `git` + `gh` CLI. No app code copied in — bind-mounted instead. |
| `tower/.dockerignore` | Keeps `__pycache__`, `data/interrupts.json` (live data, comes from the mount not the build) out of the build context. |
| `tower/deploy-cortex.sh` | One-command deploy: pull, rebuild, restart, health-check, tag `deployed-tower`. Run on Cortex. |
| `tower/deploy.bat` + `tower/create-deploy-shortcut.ps1` | Windows desktop shortcut ("Deploy Tower to Cortex") that runs the SSH deploy command in one click — only prompts for the SSH password. |
| `scripts/tower-deploy-check.sh` | Read-only: reports whether `tower/` has commits on `origin/main` not yet deployed (diffs the `deployed-tower` tag). Doesn't touch Cortex — just fetches tags from GitHub. |
| `scripts/tower-autosync.sh` | Auto-commit + push Tower's own writes. Run on Cortex only, on a timer — never on Windows. |
| `tower/server.py` (edited) | CORS tightened from `allow_origins=["*"]` to an explicit allowlist via `TOWER_ALLOWED_ORIGINS` (defaults to localhost dev). |
| `.env.example` (edited) | Documents the two new deployment-only vars: `GH_TOKEN`, `TOWER_ALLOWED_ORIGINS`. |

---

## Cortex-side setup (one-time)

### 1. Clone the repo

```bash
sudo mkdir -p /opt/ais-os && sudo chown chase:chase /opt/ais-os
git clone https://github.com/cramone/ais-os.git /opt/ais-os
cd /opt/ais-os
cp .env.example .env
nano .env   # fill in TOWER_TOKEN, GH_TOKEN, AZURE_DEVOPS_*, ANTHROPIC_API_KEY, TOWER_ALLOWED_ORIGINS
```

`TOWER_ALLOWED_ORIGINS` on Cortex: `https://tower.ramonedevelopment.com`

`GH_TOKEN`: new requirement. On Windows, `gh` was already interactively logged in, so no token was needed. The container has no interactive session — `gh` picks up `GH_TOKEN` automatically. Fine-grained PAT, read-only on repos/PRs.

### 2. Add the service to the authoritative compose file

Per the setup guide: `~/stack/docker-compose.yml` is the single authoritative file — edit it directly, don't create a second one. Add:

```yaml
  # ── AIS-OS Control Tower ────────────────────────────────────────────────
  tower:
    build:
      context: /opt/ais-os
      dockerfile: tower/Dockerfile
    restart: unless-stopped
    env_file:
      - /opt/ais-os/.env
    volumes:
      - /opt/ais-os:/app
    extra_hosts:
      - "host.docker.internal:host-gateway"   # reaches claudia-bridge on the host, same pattern as Open WebUI -> Ollama
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.tower.rule=Host(`tower.ramonedevelopment.com`)"
      - "traefik.http.routers.tower.entrypoints=tailnet"
      - "traefik.http.routers.tower.tls=true"
      - "traefik.http.services.tower.loadbalancer.server.port=8765"
```

```bash
cd ~/stack
docker compose up -d --build tower
```

### 3. Claudia bridge

Fixes the open item below. Install as a systemd `--user` service on Cortex:

```bash
mkdir -p ~/.config/systemd/user
cp scripts/claudia-bridge/claudia-bridge.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now claudia-bridge.service
systemctl --user status claudia-bridge.service
```

**Before enabling:** confirm the CLI invocation in `scripts/claudia-bridge/server.py`'s `CLAUDIA_CMD`. It assumes `claudia chat -q "<message>" --yolo` works non-interactively (`claudia` as a scoped wrapper around `hermes --profile claudia`, per the `claudia gateway install/start` pattern in the setup guide). Verify with `which claudia` and a manual `claudia chat -q "test" --yolo` on Cortex first — adjust `CLAUDIA_CMD` if the real invocation differs. Nothing else in the bridge, Tower's `claudia.py`, or the compose file needs to change if it does.

Set `CLAUDIA_BRIDGE_URL=http://host.docker.internal:8901` in Cortex's `.env`. On Windows, leave it unset — Tower falls back to `docker exec hermes ...` automatically (`tower/readers/claudia.py` branches on whether `CLAUDIA_BRIDGE_URL` is set).

### 4. (Recommended) Autosync timer

Bridges Tower's live writes (interrupts, decisions, notes/todos edits) back to GitHub so Windows sees them on the next pull.

```ini
# /etc/systemd/system/tower-autosync.service
[Unit]
Description=AIS-OS Tower autosync

[Service]
Type=oneshot
WorkingDirectory=/opt/ais-os
ExecStart=/opt/ais-os/scripts/tower-autosync.sh
User=chase
```

```ini
# /etc/systemd/system/tower-autosync.timer
[Unit]
Description=Run tower-autosync every 10 minutes

[Timer]
OnBootSec=2min
OnUnitActiveSec=10min

[Install]
WantedBy=timers.target
```

```bash
sudo systemctl enable --now tower-autosync.timer
```

Needs Cortex's git identity + push credentials configured for the `cramone/ais-os` remote (SSH deploy key or a stored PAT) — set that up before enabling the timer.

---

## Ongoing workflow

**Day-to-day dev (Windows):** unchanged. `python tower/start.py`, edit, test, commit, push.

**Deploy to Cortex:**
```bash
ssh chase@cortex "cd /opt/ais-os && ./tower/deploy-cortex.sh"
```

Or double-click **Deploy Tower to Cortex** on the Desktop (`tower/deploy.bat`, shortcut created via `tower/create-deploy-shortcut.ps1`) — runs the same command in a window, only prompts for the SSH password/passphrase. `deploy-cortex.sh` is safe to run speculatively: `git pull` no-ops if nothing changed and the Docker build is cache-hit if `requirements.txt` didn't change, so there's no harm in running it "just in case" instead of checking first.

`deploy-cortex.sh` also moves a `deployed-tower` git tag to whatever commit it just deployed. `scripts/tower-deploy-check.sh` diffs that tag against `origin/main` (scoped to `tower/`) if you ever want to check what's pending without deploying — read-only, safe to run anytime, doesn't need to reach Cortex (just fetches tags from GitHub).

**Windows picks up Tower-originated data changes:** `git pull` before your next AIS-OS session — the autosync timer will have already pushed them.

---

## Claudia integration — resolved

Original problem: `tower/readers/claudia.py` shelled out to `docker exec hermes hermes chat ...`, which assumes Hermes runs as a Docker container named `hermes`. On Cortex, Claudia runs bare-metal via systemd (`hermes-gateway-claudia`) — no such container exists, and that gateway process is Telegram-facing (outbound to Telegram's API), not a network listener Tower could call into. Mounting `docker.sock` into the Tower container was considered and rejected — real privilege escalation for a minor feature, and it wouldn't find a `hermes` container on Cortex anyway.

**Fix:** `scripts/claudia-bridge/server.py` — a ~90-line stdlib-only HTTP server that runs on the Cortex **host** (not in Docker), bound to `127.0.0.1:8901`, and shells out to the bare-metal `claudia` CLI. The Tower container reaches it via `host.docker.internal:8901` — the exact pattern already proven in this stack for Open WebUI → Ollama (`extra_hosts: host-gateway`). `tower/readers/claudia.py` now branches on `CLAUDIA_BRIDGE_URL`: set on Cortex → bridge; unset on Windows → the original `docker exec` path, unchanged.

Why a new bridge instead of SSH-from-container or replicating the Hermes venv inside the Tower image: no key management inside the image, no duplicating Claudia's Python environment/deps in two places, and it reuses a networking pattern already working on this exact host.

**Not yet verified:** the bridge's `CLAUDIA_CMD` assumes `claudia chat -q "<message>" --yolo` is the correct non-interactive invocation, inferred from the `claudia gateway install/start` pattern in the setup guide but never directly confirmed. One-line fix if wrong — see step 3 in Cortex-side setup above.

## Open items — not resolved by this design

⚠️ **ADO reachability from Cortex is unverified.**
`connections.md` — "ADO writes must originate from Chase's machine (org IP allowlist)." This assumes Cortex shares the same home-network egress IP as your Windows box. Likely true (same physical location) but not confirmed. **Before relying on this in production:** from Cortex, run `curl -I https://dev.azure.com` and test one interrupt push end-to-end. If Cortex's egress IP differs (e.g. different ISP path, CGNAT), ADO reads/writes will 401/403 and this whole plan needs a rethink (VPN/proxy through the Windows box, or an ADO allowlist change).

---

## Rollout order

1. Clone repo to `/opt/ais-os` on Cortex, populate `.env`.
2. Verify Claudia CLI invocation (`which claudia`, manual `claudia chat -q "test" --yolo`), fix `CLAUDIA_CMD` in `scripts/claudia-bridge/server.py` if needed, then install + enable `claudia-bridge.service`.
3. Add `tower` service to `~/stack/docker-compose.yml` (includes `extra_hosts` for the bridge), `docker compose up -d --build tower`.
4. Verify: `curl https://tower.ramonedevelopment.com/api/health` from a tailnet device — confirm `projects`/`decisions`/`interrupts`/`claudia` all `true`.
5. Test ADO end-to-end (see open item above) before trusting it for real interrupt pushes.
6. Enable `tower-autosync.timer`.
7. Confirm the frontend actually prompts for/stores `TOWER_TOKEN` (auth wiring exists in `index.html`; hasn't been exercised against a non-empty token in practice — smoke-test it).
