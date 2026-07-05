# Control Tower on Cortex — Deployment Design

**Date:** 2026-07-03 (revised 2026-07-05)
**Status:** Approved — ready to implement
**Owner:** Chase

**Revision 2026-07-05:** the original design (below, superseded) gave Cortex its own git clone at `/opt/ais-os` with a timer auto-committing/pushing Tower's live writes so Windows could `git pull` and see them. That's now replaced: both Windows (`Z:\claudia\magiq`) and Cortex (`/mnt/shared/claudia/magiq`) already mount the same DS923 NAS share, so Tower's container just bind-mounts that share directly — no clone, no autosync timer, no git in the loop for cross-machine visibility at all. This aligns with the standing decision logged 2026-07-04 (`decisions/log.md` / `reference_aios-decisions.md`): *"Canonical AIS-OS location: single NAS share, not git-sync between clones"* — which named Tower specifically as one of the autonomous writers that made git-sync-between-clones unreliable. Git is kept for history/backup to GitHub, just not as the live sync mechanism. Sections below are updated in place; where something was cut outright (the autosync timer), a note explains what replaced it.

**Goal:** Tower runs as a Docker container on Cortex, reverse-proxied by Traefik at `tower.ramonedevelopment.com`, while staying actively developed day-to-day from Windows.

---

## Decisions

**Exposure: Tailscale-only, not public.**
Every other Cortex service (Seq, Portainer, Open WebUI) sits behind the `tailnet` entrypoint despite the same-looking `ramonedevelopment.com` hostname — only ACME uses `websecure`/public. Tower holds ADO items, decisions, and customer/interrupt data. It follows the existing pattern rather than becoming the first public exception.

**Deploy trigger: manual rebuild/restart on Cortex.**
`docker compose up -d --build tower` (or `restart`, if only Python code changed) — one command, no registry, no CI, no Watchtower. **Revised 2026-07-05:** no `git pull` step — see Data model below. Matches homelab scale. Revisit only if manual deploys become actual friction (3-use rule).

**Data model (revised 2026-07-05): the shared NAS mount is the single copy — no publisher/editor split.**
Superseded reasoning, kept for history: the original design gave Cortex its own clone at `/opt/ais-os` as a "live-data publisher," with Windows as the "editing copy" kept in sync via git push/pull and a timer. That's no longer how this works. `Z:\claudia\magiq` (Windows) and `/mnt/shared/claudia/magiq` (Cortex) are already the same files, live, over the DS923 SMB share (see the setup guide's Stage 14 for the mount itself). Tower's container bind-mounts `/mnt/shared/claudia/magiq` directly — the same path Claudia already treats as her working directory. A write from Tower's UI (an interrupt, a decision) is visible to Windows the instant the SMB client on each side catches up — no commit, no push, no pull, no timer.

**Image = runtime only, not code.**
The Docker image bundles Python + dependencies + `git`/`gh` CLI. `/mnt/shared/claudia/magiq` is bind-mounted into the container at `/app`. Code changes take effect on container restart with no rebuild; rebuild only when `tower/requirements.txt` changes. Cleanly separated (runtime vs. code/data) without needing a registry.

---

## Architecture

```
Windows (Chase, interactive editing)          Cortex (Chase, always-on)
┌─────────────────────────────┐               ┌──────────────────────────────┐
│ Z:\claudia\magiq              │  same files,   │ /mnt/shared/claudia/magiq    │
│  - Claude Code / Cowork edit │  live over SMB │  - bind-mounted into `tower` │
│  - python tower/start.py     │◄──────────────►│    container at /app        │
│    (--reload, local dev)     │  DS923 (NAS)   │  - Traefik: tower.ramone     │
└─────────────────────────────┘               │    development.com (tailnet)│
                                                │  - git push to GitHub is    │
                                                │    manual/periodic, backup  │
                                                │    only — not the sync path │
                                                └──────────────────────────────┘
```

Two things had to be possible; here's how each is satisfied:

1. **Active development** — unchanged. Keep running `python tower/start.py` on Windows for the fast inner loop (`--reload`, no Docker). Docker is a deploy target, not a dev requirement.
2. **Build + host as a container on change** — `tower/deploy-cortex.sh` on Cortex: `docker compose up -d --build tower` (no `git pull` step anymore — the bind-mounted share already has whatever's on disk). Run it after editing from Windows, or straight from a Claude Code / Claudia session on Cortex. Restart alone (`docker compose restart tower`) is enough unless `requirements.txt` changed.

---

## What's already built (no new work needed)

- `tower/config.py` self-locates `AIOS_ROOT` from its own file position — the bind mount at `/app` resolves correctly with zero path config, whether that mount is `/opt/ais-os` or `/mnt/shared/claudia/magiq`.
- `TOWER_TOKEN` bearer-auth middleware already gates `/api/*`, and the frontend (`static/index.html`) already attaches it from a stored token — auth is deploy-ready.
- `.env` / `.mcp.json` are gitignored — secrets never touch the repo history. They're duplicated manually per location today (Windows `.env`, Cortex `.env`) — the shared-mount change doesn't affect this, since gitignored files were never part of what git was syncing anyway.

## What this work added

| File | Purpose |
|---|---|
| `tower/Dockerfile` | Runtime image: Python 3.12-slim + `tower/requirements.txt` + `git` + `gh` CLI. No app code copied in — bind-mounted instead. |
| `tower/.dockerignore` | Keeps `__pycache__`, `data/interrupts.json` (live data, comes from the mount not the build) out of the build context. |
| `tower/deploy-cortex.sh` | One-command deploy: rebuild, restart, health-check, tag `deployed-tower`. Run on Cortex. **Revised 2026-07-05:** no longer does `git pull` first — see Data model above. |
| `tower/deploy.bat` + `tower/create-deploy-shortcut.ps1` | Windows desktop shortcut ("Deploy Tower to Cortex") that runs the SSH deploy command in one click — only prompts for the SSH password. |
| `scripts/tower-deploy-check.sh` | Read-only: reports whether `tower/` has commits on `origin/main` not yet deployed (diffs the `deployed-tower` tag). Still useful for tracking *code* history/backup status — unrelated to live data sync now. |
| ~~`scripts/tower-autosync.sh`~~ | **Superseded 2026-07-05, no longer used.** Was: auto-commit + push Tower's own writes on a timer. Not needed once Tower writes straight to the shared mount Windows already sees. Left in the repo for reference; not wired into any systemd unit. |
| `tower/server.py` (edited) | CORS tightened from `allow_origins=["*"]` to an explicit allowlist via `TOWER_ALLOWED_ORIGINS` (defaults to localhost dev). |
| `.env.example` (edited) | Documents the deployment-only vars: `GH_TOKEN`, `TOWER_ALLOWED_ORIGINS`. (`GH_TOKEN` is for `tower/readers/github.py`'s PR-queue reader — unrelated to the sync mechanism, still required in the Cortex container.) |

---

## Cortex-side setup (one-time)

### 1. Confirm the shared mount, populate `.env`

**Revised 2026-07-05 — no clone step.** `/mnt/shared/claudia/magiq` should already exist on Cortex per the setup guide's Stage 14 (DS923 SMB mount) and Stage 15.5 (shared folder structure) — it's the same mount Claudia already works out of. Confirm it's there and populated before wiring Tower to it:

```bash
ls /mnt/shared/claudia/magiq/tower/server.py   # should exist — confirms the mount is live and has the repo on it
```

If `.env` doesn't already exist at `/mnt/shared/claudia/magiq/.env` (it's gitignored, so it won't have arrived via the share the way tracked files did):

```bash
cd /mnt/shared/claudia/magiq
cp .env.example .env
nano .env   # fill in TOWER_TOKEN, GH_TOKEN, AZURE_DEVOPS_*, ANTHROPIC_API_KEY, TOWER_ALLOWED_ORIGINS
```

`TOWER_ALLOWED_ORIGINS` on Cortex: `https://tower.ramonedevelopment.com`

`GH_TOKEN`: on Windows, `gh` was already interactively logged in, so no token was needed there. The container has no interactive session — `gh` picks up `GH_TOKEN` automatically. Fine-grained PAT, read-only on repos/PRs.

### 2. Add the service to the authoritative compose file

Per the setup guide: `~/stack/docker-compose.yml` is the single authoritative file — edit it directly, don't create a second one. Add:

```yaml
  # ── AIS-OS Control Tower ────────────────────────────────────────────────
  tower:
    build:
      context: /mnt/shared/claudia/magiq
      dockerfile: tower/Dockerfile
    restart: unless-stopped
    user: "1000:1000"
    env_file:
      - /mnt/shared/claudia/magiq/.env
    volumes:
      - /mnt/shared/claudia/magiq:/app
    extra_hosts:
      - "host.docker.internal:host-gateway"   # reaches claudia-bridge on the host, same pattern as Open WebUI -> Ollama
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.tower.rule=Host(`tower.ramonedevelopment.com`)"
      - "traefik.http.routers.tower.entrypoints=tailnet"
      - "traefik.http.routers.tower.tls.certresolver=public"
      - "traefik.http.services.tower.loadbalancer.server.port=8765"
```

Note: `tls.certresolver=public` (not bare `tls=true`) — matches the §10.3b pattern in the setup guide, gets a real Let's Encrypt cert for a tailnet-only router the same way `mcp-ado`/`seq`/`portainer`/`openwebui` already do. The original design's `tls=true` line would have repeated the self-signed-cert gap those four services had before it was fixed.

**CIFS write permissions — verified 2026-07-05.** Tested directly on cortex against the live mount (`mount | grep /mnt/shared` showed `forceuid,forcegid,file_mode=0755,dir_mode=0755,nounix`): a throwaway container writes through the bind mount successfully both as root (default, no `user:` line — `uid=0` bypasses the local permission check) and as `--user 1000:1000` (owner-match against the `forceuid`-presented ownership). Either works; `user: "1000:1000"` above is the least-privilege choice, not a requirement. No `noperm` remount or other mount changes needed.

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

### 4. ~~Autosync timer~~ — removed, not needed

**Superseded 2026-07-05.** The original design ran a systemd timer every 10 minutes to auto-commit + push Tower's live writes back to GitHub so Windows would see them on the next pull. That whole mechanism existed only to solve cross-machine visibility — and the shared NAS mount (Step 1 above) already solves that with no timer, no git identity/push credentials needed on Cortex, and no risk of an automated commit/push firing at a bad moment.

Git still matters for **history and GitHub backup** of the repo as a whole — just as a manual/periodic action, not a timer reacting to Tower's writes specifically. Run `git add -A && git commit && git push` from whichever machine you're on when you want a checkpoint (Windows, since that's where you're usually driving Claude Desktop/Claude Code). `scripts/tower-deploy-check.sh` still works for checking whether `tower/` code has unpushed commits — that's a separate, still-useful question from "did Tower's live data get backed up."

---

## Ongoing workflow

**Day-to-day dev (Windows):** unchanged. `python tower/start.py`, edit, test — against the same `Z:\claudia\magiq` files the Cortex container reads.

**Deploy to Cortex:**
```bash
ssh chase@cortex "cd /mnt/shared/claudia/magiq && ./tower/deploy-cortex.sh"
```

Or double-click **Deploy Tower to Cortex** on the Desktop (`tower/deploy.bat`, shortcut created via `tower/create-deploy-shortcut.ps1`) — runs the same command in a window, only prompts for the SSH password/passphrase. **Revised 2026-07-05:** `deploy-cortex.sh` no longer does `git pull` first — the bind-mounted share already reflects whatever's on disk the instant you save from Windows. The Docker build is still cache-hit if `requirements.txt` didn't change, so it's still safe to run speculatively; it just does less than it used to (rebuild/restart/health-check/tag only).

`deploy-cortex.sh` still moves a `deployed-tower` git tag to whatever commit is currently checked out, for history purposes. `scripts/tower-deploy-check.sh` diffs that tag against `origin/main` (scoped to `tower/`) if you want to check what code has been pushed to GitHub but not yet "tagged as deployed" — read-only, safe to run anytime, doesn't touch Cortex.

**Windows picks up Tower-originated data changes:** immediately — no `git pull` needed, it's the same file over SMB. (Subject to normal SMB client-side caching; if something looks stale, a manual refresh of the file/folder view is the first thing to try before assuming something's actually wrong.)

---

## Claudia integration — resolved

Original problem: `tower/readers/claudia.py` shelled out to `docker exec hermes hermes chat ...`, which assumes Hermes runs as a Docker container named `hermes`. On Cortex, Claudia runs bare-metal via systemd (`hermes-gateway-claudia`) — no such container exists, and that gateway process is Telegram-facing (outbound to Telegram's API), not a network listener Tower could call into. Mounting `docker.sock` into the Tower container was considered and rejected — real privilege escalation for a minor feature, and it wouldn't find a `hermes` container on Cortex anyway.

**Fix:** `scripts/claudia-bridge/server.py` — a ~90-line stdlib-only HTTP server that runs on the Cortex **host** (not in Docker), bound to `127.0.0.1:8901`, and shells out to the bare-metal `claudia` CLI. The Tower container reaches it via `host.docker.internal:8901` — the exact pattern already proven in this stack for Open WebUI → Ollama (`extra_hosts: host-gateway`). `tower/readers/claudia.py` branches on `CLAUDIA_BRIDGE_URL`: set → `_send_via_bridge()` (Cortex, containerized Tower). Unset → `_send_via_docker()` — a misleading function name kept from an earlier version; **this no longer does `docker exec`**. It was repointed 2026-07-04 to SSH into cortex directly (`ssh chase@cortex claudia chat -q "<message>" --yolo`) once the Windows Docker Hermes install was retired. So the real fallback today is: no bridge configured → SSH to cortex instead. Both paths end up running the same `claudia` CLI command; they just differ in how they reach the host that runs it (local HTTP call vs. SSH).

Why a bridge exists at all, rather than always using the SSH path: the Tower container has no SSH client/keys installed (its `Dockerfile` only adds `git`/`gh`), so `_send_via_docker()`'s SSH command wouldn't actually run from inside cortex's own Tower container — it's really the Windows/WSL-dev fallback, not a second Cortex-side option. On Cortex, the bridge is the only path that works from inside the container; SSH-from-container was considered and rejected anyway (key management overhead for no real benefit over a plain HTTP bridge), and replicating the Hermes venv inside the Tower image was rejected too (duplicates a working install, fragile to keep in sync).

**Not yet verified:** the bridge's `CLAUDIA_CMD` assumes `claudia chat -q "<message>" --yolo` is the correct non-interactive invocation, inferred from the `claudia gateway install/start` pattern in the setup guide but never directly confirmed. One-line fix if wrong — see step 3 in Cortex-side setup above.

**Single shared `.env` wrinkle (2026-07-05):** now that Windows/WSL and Cortex all read the same `.env` (per the Data model revision above), setting `CLAUDIA_BRIDGE_URL` there means a Windows/WSL dev instance of Tower (`python tower/start.py`, not in Docker) will also try `_send_via_bridge()` — and `host.docker.internal` doesn't resolve outside a container, so "Ask Claudia" specifically fails there. Every other feature is unaffected either way. Not fixed as of this writing — just documented so it doesn't look like a mystery bug.

## Open items — not resolved by this design

✅ **ADO reachability from Cortex — resolved 2026-07-04.** Originally flagged here as unverified (`connections.md`: "ADO writes must originate from Chase's machine, org IP allowlist"). This got tested as part of the separate Azure DevOps MCP work (`docs/superpowers/specs/2026-07-04-azure-devops-mcp-integration.md`, setup guide Stage 16.3) — same box, same egress path — and confirmed allowlisted. Tower's interrupt-push feature can rely on this; no separate re-test needed.

✅ **CIFS write permissions — resolved 2026-07-05.** See the verified note in Cortex-side setup Step 2. Tested directly against the live mount; writes work both as root and as UID 1000. `user: "1000:1000"` is in the compose block above as the least-privilege choice.

⚠️ **Availability coupling — accepted tradeoff, not a bug.** Tower on Cortex now depends on the DS923 SMB mount staying up (same dependency Claudia already has). If Tailscale or the NAS drops, Tower's container will error or hang on file access until the mount recovers — unlike the old `/opt/ais-os` local-disk-clone design, which kept running standalone regardless of NAS availability. Documented here so it's a conscious call, not a surprise.

---

## Rollout order

1. Confirm `/mnt/shared/claudia/magiq` is live on Cortex and populate `.env` there if missing (Step 1). ✅ CIFS write access confirmed 2026-07-05 — no blocker.
2. Verify Claudia CLI invocation (`which claudia`, manual `claudia chat -q "test" --yolo`), fix `CLAUDIA_CMD` in `scripts/claudia-bridge/server.py` if needed, then install + enable `claudia-bridge.service`.
3. Add `tower` service to `~/stack/docker-compose.yml` (includes `user: "1000:1000"` and `extra_hosts` for the bridge), `docker compose up -d --build tower`.
4. Verify: `curl https://tower.ramonedevelopment.com:8443/api/health` from a tailnet device — confirm `projects`/`decisions`/`interrupts`/`claudia` all `true`.
5. Confirm the frontend actually prompts for/stores `TOWER_TOKEN` (auth wiring exists in `index.html`; hasn't been exercised against a non-empty token in practice — smoke-test it).
