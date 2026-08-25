# Cortex Split Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract cortex infrastructure from `magiq/cortex/` subfolder into a standalone sibling repo at `/mnt/shared/cortex/`, enable any sibling context (magiq, claudette, future) to register traefik routes and homepage tiles via a `cortex-sync` script, with zero user-visible downtime during cutover.

**Architecture:** NAS-canonical (all repos on `/mnt/shared/`, edited from any dev machine, cortex box mounts NAS). Deploy trigger = `/usr/local/bin/cortex-sync <ctx|all>` script invoked manually via SSH + cron poll every 5 min. Bare repos and post-receive hooks NOT used. `cortex_edge` docker network created manually and consumed as external by both cortex and context composes. `~/stack/` on cortex box is real dir with `.env` local + compose/traefik/homepage symlinks to NAS.

**Tech Stack:** Docker Compose, Traefik v3.6 (file-provider with directory watch), gethomepage/homepage, Bash, rsync, cron, git, GitHub (cortex origin = `cramone/cortex`).

**Spec:** `docs/superpowers/specs/2026-08-24-cortex-split-design.md` — read first if not already familiar.

---

## File structure

**Created (`/mnt/shared/cortex/`, dev-mount `Z:\cortex\`):**
- `docker-compose.yml` — pure cortex infra (~18 services, no tower/mcp-ado)
- `sync-contexts.sh` — deploy trigger script
- `contexts.yaml` — context registry
- `cron/cortex-sync.cron` — 5-min poll cron file
- `.gitignore` — excludes .env, logs/, generated dirs
- `README.md`
- `traefik-dynamic/_cortex/hermes.yml`, `iis-tenants.yml`
- `homepage-config/settings.yaml`, `bookmarks.yaml`
- `homepage-config-src/services.yaml`
- `decisions/log.md`
- `docs/deploy-topology.md`, `adding-a-context.md`, `known-gotchas.md`
- `docs/setup/01-hardware-and-os.md` through `07-hermes-install.md`, `22-secrets-local-env.md`
- `docs/patterns/traefik-file-provider.md`, `tower-deploy-flow.md`

**Created (`/mnt/shared/claudia/magiq/`, dev-mount `Z:\claudia\magiq\`):**
- `docker-compose.yml` — tower + mcp-azure-devops only, joins `cortex_edge`
- `CORTEX-MOVED.md` — breadcrumb (Phase 5, deleted Phase 5f)
- `homepage-config/MOVED.md` — warning breadcrumb (Phase 0)
- `references/adrs/adr-NNN-cortex-split.md` — ADR (Phase 5)

**Modified (magiq):**
- `AI-X1-Pro-Setup-Guide.md` — trimmed (cortex Stages → breadcrumbs)
- `hermes-integration.md` — trimmed (install-side moved)
- `docs/superpowers/specs/2026-07-03-tower-cortex-deployment.md` — trimmed (cortex-side moved)
- `decisions/log.md` — cortex entries → breadcrumbs
- `CLAUDE.md` — new cortex-sibling section (Phase 5)
- `README.md` — deploy instructions updated (Phase 5)
- `scripts/tower-autosync.sh`, `scripts/tower-deploy-check.sh` — deploy-cortex.sh refs removed (Phase 5)

**Modified (live during cutover):**
- `/mnt/shared/claudia/magiq/cortex/docker-compose.yml` — Phase 2 (network add) + Phase 3b (tower/mcp-ado removal)

**Deleted (Phase 5):**
- `/mnt/shared/claudia/magiq/cortex/` (entire folder)
- `/mnt/shared/claudia/magiq/homepage-config/`
- `/mnt/shared/claudia/magiq/tower/deploy-cortex.sh`
- `/mnt/shared/claudia/magiq/docs/superpowers/specs/2026-08-07-iis-traefik-file-provider.md` stub (Phase 5f)

**Cortex box changes:**
- `/usr/local/bin/cortex-sync` — script installed (Phase 0)
- `/etc/cron.d/cortex-sync` — cron installed (Phase 4d)
- `/etc/logrotate.d/cortex-sync` — log rotation config
- `~/stack/docker-compose.yml` — symlink repointed (Phase 4)
- `~/stack/traefik-dynamic` — new symlink (Phase 4)
- `~/stack/homepage-config` — new symlink (Phase 4)
- `~/stack/logs/` — dir created by script on first run
- `~/stack/docker-compose.yml.bak-presymlink` — deleted (Phase 4e)
- `~/stack/iis-tenants.yml` — deleted (Phase 4e)
- `~/stack/traefik-dynamic/` (real cruft dir) — deleted (Phase 4b)

---

## Prerequisites check

- [ ] **Step 1: Verify SSH access to cortex box**

Run: `ssh cortex 'hostname && whoami'`
Expected: `cortex` and `chase`.

- [ ] **Step 2: Verify NAS mount on cortex box**

Run: `ssh cortex 'mountpoint -q /mnt/shared && echo mounted'`
Expected: `mounted`.

- [ ] **Step 3: Verify current live layout matches spec §4 audit**

Run:
```bash
ssh cortex 'ls -la ~/stack/ && readlink ~/stack/docker-compose.yml'
```
Expected: `~/stack/` = real dir with `.env` (chmod 600) + `docker-compose.yml` symlink → `/mnt/shared/claudia/magiq/cortex/docker-compose.yml` + leftover files.

If layout differs from spec §4, STOP and update the spec before proceeding.

- [ ] **Step 4: Verify GitHub repo exists**

Run: `git ls-remote git@github.com:cramone/cortex.git`
Expected: empty output (empty repo) — command succeeds.

- [ ] **Step 5: Baseline snapshot**

Run on cortex box:
```bash
ssh cortex '
  docker ps --format "{{.Names}}" | sort > /tmp/pre-split-containers.txt
  docker network ls --format "{{.Name}}" | sort > /tmp/pre-split-networks.txt
  find ~/stack -maxdepth 2 -type l > /tmp/pre-split-symlinks.txt
  cat /tmp/pre-split-containers.txt /tmp/pre-split-networks.txt /tmp/pre-split-symlinks.txt
'
```
Save output — used for after-cutover comparison.

---

## Phase 0 — prep and doc extraction (no service impact)

### Task 1: Create cortex repo skeleton on NAS

**Files:**
- Create: `Z:\cortex\.git\` (init)

- [ ] **Step 1: Create dir + init git**

Run (Windows):
```cmd
mkdir Z:\cortex
cd /d Z:\cortex
git init -b main
```
Expected: `Initialized empty Git repository in Z:/cortex/.git/`.

- [ ] **Step 2: Add GitHub remote**

Run:
```cmd
git remote add origin git@github.com:cramone/cortex.git
git remote -v
```
Expected: `origin  git@github.com:cramone/cortex.git (fetch)` + `(push)`.

- [ ] **Step 3: No commit yet — remainder of Phase 0 builds the content**

### Task 2: Import cortex files from magiq

**Files:**
- Create: `Z:\cortex\docker-compose.yml` (copy)
- Create: `Z:\cortex\traefik-dynamic\hermes.yml`, `iis-tenants.yml` (copy)
- Create: `Z:\cortex\.env.example` (copy)

- [ ] **Step 1: Copy all files from magiq/cortex/**

Run (Windows):
```cmd
xcopy /E /I /Y Z:\claudia\magiq\cortex\* Z:\cortex\
```
Expected: `3 File(s) copied` (approx).

- [ ] **Step 2: Verify copy**

Run:
```cmd
dir Z:\cortex\
dir Z:\cortex\traefik-dynamic\
```
Expected: `docker-compose.yml`, `.env.example`, `traefik-dynamic\` with `hermes.yml` + `iis-tenants.yml`.

- [ ] **Step 3: Audit traefik file-provider flags**

Run:
```bash
grep -n 'providers.file' Z:\cortex\docker-compose.yml
```
Expected output:
```
      - "--providers.file.directory=/etc/traefik/dynamic"
      - "--providers.file.watch=true"
```
If either line is `providers.file.filename=...`, CHANGE to `directory=./traefik-dynamic --providers.file.watch=true` at this task, else no change needed.

### Task 3: Strip tower + mcp-azure-devops from cortex compose

**Files:**
- Modify: `Z:\cortex\docker-compose.yml` (remove tower + mcp-azure-devops service blocks)

- [ ] **Step 1: Identify service blocks to remove**

Read `Z:\cortex\docker-compose.yml`. Find:
- `  tower:` service block (approx lines 496-540)
- `  mcp-azure-devops:` service block (approx lines 300-340)
- Any top-level `depends_on:` referencing these

- [ ] **Step 2: Remove both service blocks + any orphan depends_on lines**

Edit `Z:\cortex\docker-compose.yml`. Delete the two blocks entirely. Preserve everything else.

- [ ] **Step 3: Validate compose syntax**

Run:
```bash
docker compose -f Z:\cortex\docker-compose.yml config > /dev/null && echo OK
```
Expected: `OK` (no YAML errors, no undefined references).

If error mentions missing service reference, remove the stale `depends_on` line and re-validate.

### Task 4: Reorganize traefik routes into `_cortex/` subdir

**Files:**
- Create: `Z:\cortex\traefik-dynamic\_cortex\hermes.yml` (move from parent)
- Create: `Z:\cortex\traefik-dynamic\_cortex\iis-tenants.yml` (move from parent)

- [ ] **Step 1: Create subdir + move files**

Run (Windows):
```cmd
mkdir Z:\cortex\traefik-dynamic\_cortex
move Z:\cortex\traefik-dynamic\hermes.yml Z:\cortex\traefik-dynamic\_cortex\
move Z:\cortex\traefik-dynamic\iis-tenants.yml Z:\cortex\traefik-dynamic\_cortex\
```

- [ ] **Step 2: Verify**

Run:
```cmd
dir Z:\cortex\traefik-dynamic\_cortex\
```
Expected: `hermes.yml` + `iis-tenants.yml`.

- [ ] **Step 3: No compose change needed** — traefik flag `--providers.file.directory=/etc/traefik/dynamic` is recursive.

### Task 5: Copy homepage-config + establish base/generated split + update NEW compose paths

**Files:**
- Create: `Z:\cortex\homepage-config\settings.yaml`, `bookmarks.yaml` (copy from magiq, keep in place)
- Create: `Z:\cortex\homepage-config-src\services.yaml` (moved from homepage-config/)
- Modify: `Z:\cortex\docker-compose.yml` (homepage volume path + traefik-dynamic volume path)
- Create: `Z:\claudia\magiq\homepage-config\MOVED.md`

- [ ] **Step 1: COPY (not move) homepage-config from magiq to cortex**

Run (Windows):
```cmd
xcopy /E /I /Y Z:\claudia\magiq\homepage-config Z:\cortex\homepage-config
```
Expected: `settings.yaml`, `bookmarks.yaml`, `services.yaml` copied. **Do NOT delete magiq copy** — live homepage container still reads it until Phase 4.

- [ ] **Step 2: Split services.yaml into src/**

Run (Windows):
```cmd
mkdir Z:\cortex\homepage-config-src
move Z:\cortex\homepage-config\services.yaml Z:\cortex\homepage-config-src\services.yaml
```
Expected: `services.yaml` now under `homepage-config-src/`; `homepage-config/` retains `settings.yaml` + `bookmarks.yaml`.

- [ ] **Step 3: Update NEW cortex compose volume paths**

Edit `Z:\cortex\docker-compose.yml`. Find the two lines:
```yaml
      - /mnt/shared/claudia/magiq/homepage-config:/app/config
```
Change to:
```yaml
      - /mnt/shared/cortex/homepage-config:/app/config
```

Find:
```yaml
      - /mnt/shared/claudia/magiq/cortex/traefik-dynamic:/etc/traefik/dynamic:ro
```
Change to:
```yaml
      - /mnt/shared/cortex/traefik-dynamic:/etc/traefik/dynamic:ro
```

- [ ] **Step 4: Validate compose syntax**

Run:
```bash
docker compose -f Z:\cortex\docker-compose.yml config > /dev/null && echo OK
```
Expected: `OK`.

- [ ] **Step 5: Add MOVED.md breadcrumb in magiq copy**

Create `Z:\claudia\magiq\homepage-config\MOVED.md` with content:
```markdown
# homepage-config moved

This directory has been COPIED to `/mnt/shared/cortex/homepage-config/` as of 2026-08-25.

The live homepage container is bind-mounted against THIS copy until Phase 4 of the cortex split (see `docs/superpowers/plans/2026-08-25-cortex-split.md`).

**Edits made here after Phase 4 will have no effect.** Instead edit:
- `/mnt/shared/cortex/homepage-config-src/services.yaml` — cortex-owned base
- Your context's `homepage/services.yaml` — auto-merged by cortex-sync

This entire directory is deleted from the magiq repo in Phase 5a of the split.
```

### Task 6: Extract cortex-owned setup docs from AI-X1-Pro-Setup-Guide

**Files:**
- Create: `Z:\cortex\docs\setup\01-hardware-and-os.md` (from AI-X1 Stages 0-9)
- Create: `Z:\cortex\docs\setup\02-docker-stack.md` (from AI-X1 Stage 10.1-10.4)
- Create: `Z:\cortex\docs\setup\03-openwebui-netdata-cockpit.md` (from AI-X1 10.5-10.7)
- Create: `Z:\cortex\docs\setup\04-split-dns-tailnet.md` (from AI-X1 10.8)
- Create: `Z:\cortex\docs\setup\05-benchmarks-v1-baseline.md` (from AI-X1 11-13)
- Create: `Z:\cortex\docs\setup\06-shared-storage-ds923.md` (from AI-X1 14)
- Create: `Z:\cortex\docs\setup\07-hermes-install.md` (from AI-X1 15.1-15.2 + hermes-integration install-side)
- Create: `Z:\cortex\docs\setup\22-secrets-local-env.md` (from AI-X1 22 + .env.example commentary + `~/stack/` layout)
- Modify: `Z:\claudia\magiq\AI-X1-Pro-Setup-Guide.md` (replace extracted sections with breadcrumbs)

- [ ] **Step 1: Create setup dir**

Run:
```cmd
mkdir Z:\cortex\docs\setup
```

- [ ] **Step 2: Extract Stages 0-9 → 01-hardware-and-os.md**

Read `Z:\claudia\magiq\AI-X1-Pro-Setup-Guide.md` lines 60-372 (Stages 0-9). Copy full section text to `Z:\cortex\docs\setup\01-hardware-and-os.md`. Prepend:
```markdown
# 01 — Hardware & OS Setup

> Extracted from `magiq/AI-X1-Pro-Setup-Guide.md` on 2026-08-25 as part of the cortex split.
> Covers MINISFORUM AI X1 Pro hardware setup through Ollama installation.
```

- [ ] **Step 3: Replace extracted section in magiq guide with breadcrumb**

Edit `Z:\claudia\magiq\AI-X1-Pro-Setup-Guide.md`. Delete the Stages 0-9 content (lines 60-372). Replace with:
```markdown
## Stages 0-9 — moved to cortex repo

> Moved to `/mnt/shared/cortex/docs/setup/01-hardware-and-os.md` as of 2026-08-25.
```

- [ ] **Step 4: Repeat for Stages 10.1-10.4 → 02-docker-stack.md**

Extract lines 373-685 (Docker + Compose Stack) to `Z:\cortex\docs\setup\02-docker-stack.md`. Prepend heading + breadcrumb note. Replace in magiq guide with:
```markdown
## Stage 10.1-10.4 — Docker + Compose Stack

> Moved to `/mnt/shared/cortex/docs/setup/02-docker-stack.md` as of 2026-08-25.
```

- [ ] **Step 5: Repeat for Stages 10.5-10.7 → 03-openwebui-netdata-cockpit.md**

Extract lines 686-737. Same pattern.

- [ ] **Step 6: Repeat for Stage 10.8 → 04-split-dns-tailnet.md**

Extract lines 737-773.

- [ ] **Step 7: Repeat for Stages 11-13 → 05-benchmarks-v1-baseline.md**

Extract lines 774-814.

- [ ] **Step 8: Repeat for Stage 14 → 06-shared-storage-ds923.md**

Extract lines 815-893.

- [ ] **Step 9: Repeat for Stages 15.1-15.2 → 07-hermes-install.md**

Extract lines 894-955 from AI-X1 Guide. Also extract install-side content from `Z:\claudia\magiq\hermes-integration.md` (whatever describes installing hermes on cortex box). Combine both into `07-hermes-install.md`. Leave consumer-side content in `hermes-integration.md` with a top-of-file note:
```markdown
> Install-side content moved to `/mnt/shared/cortex/docs/setup/07-hermes-install.md` (2026-08-25). This file now covers consumer-side integration only.
```

- [ ] **Step 10: Repeat for Stage 22 → 22-secrets-local-env.md**

Extract Stage 22 content (search for "Stage 22"). Also lift commentary from cortex `.env.example` about `~/stack/.env` model. Add a section documenting the verified `~/stack/` layout (real dir + `.env` real + `docker-compose.yml` symlink to NAS) per spec §4.

- [ ] **Step 11: Verify all setup docs created**

Run:
```cmd
dir Z:\cortex\docs\setup\
```
Expected: 8 files (`01-` through `07-`, `22-`).

- [ ] **Step 12: Verify all magiq breadcrumbs in place**

Run:
```bash
grep -c "Moved to.*cortex/docs/setup" Z:\claudia\magiq\AI-X1-Pro-Setup-Guide.md
```
Expected: 8.

### Task 7: Move iis-traefik-file-provider spec + split tower-cortex-deployment spec

**Files:**
- Create: `Z:\cortex\docs\patterns\traefik-file-provider.md` (from magiq spec, whole file)
- Create: `Z:\cortex\docs\patterns\tower-deploy-flow.md` (cortex-side of tower-cortex-deployment)
- Modify: `Z:\claudia\magiq\docs\superpowers\specs\2026-08-07-iis-traefik-file-provider.md` (stub with breadcrumb)
- Modify: `Z:\claudia\magiq\docs\superpowers\specs\2026-07-03-tower-cortex-deployment.md` (trim cortex-side, keep tower-side)

- [ ] **Step 1: Create patterns dir + move iis spec**

Run:
```cmd
mkdir Z:\cortex\docs\patterns
copy Z:\claudia\magiq\docs\superpowers\specs\2026-08-07-iis-traefik-file-provider.md Z:\cortex\docs\patterns\traefik-file-provider.md
```

- [ ] **Step 2: Replace magiq iis spec with breadcrumb stub**

Overwrite `Z:\claudia\magiq\docs\superpowers\specs\2026-08-07-iis-traefik-file-provider.md` with:
```markdown
> Moved to `/mnt/shared/cortex/docs/patterns/traefik-file-provider.md` (2026-08-25).
>
> This stub file will be deleted in Phase 5f of the cortex split.
```

- [ ] **Step 3: Split tower-cortex-deployment spec**

Read `Z:\claudia\magiq\docs\superpowers\specs\2026-07-03-tower-cortex-deployment.md`. Identify sections that describe cortex-side deploy flow (docker compose behavior on cortex box, `~/stack/` handling, deploy tag mechanics). Copy those sections into `Z:\cortex\docs\patterns\tower-deploy-flow.md`. Prepend:
```markdown
# Tower deploy flow — cortex side

> Extracted from `magiq/docs/superpowers/specs/2026-07-03-tower-cortex-deployment.md` on 2026-08-25 as part of the cortex split.
> Post-split, tower deploy is triggered by `cortex-sync magiq` — see `docs/deploy-topology.md`.
```

- [ ] **Step 4: Trim cortex-side from magiq spec**

Delete the extracted sections from `Z:\claudia\magiq\docs\superpowers\specs\2026-07-03-tower-cortex-deployment.md`. Add note at top:
```markdown
> Cortex-side flow moved to `/mnt/shared/cortex/docs/patterns/tower-deploy-flow.md` (2026-08-25). This file now covers the tower application side only.
```

### Task 8: Lift cortex-tagged decisions from magiq log

**Files:**
- Create: `Z:\cortex\decisions\log.md`
- Modify: `Z:\claudia\magiq\decisions\log.md`

- [ ] **Step 1: Create cortex decisions dir + log**

Run:
```cmd
mkdir Z:\cortex\decisions
```

Create `Z:\cortex\decisions\log.md` with header:
```markdown
# Cortex Decisions Log

Append-only record of architecture and operational decisions specific to the cortex infrastructure repo.

Entries lifted from `magiq/decisions/log.md` on 2026-08-25 as part of the cortex split.

---
```

- [ ] **Step 2: Identify cortex-tagged entries in magiq log**

Read `Z:\claudia\magiq\decisions\log.md`. Find entries about: cortex box, Stage 22 secrets, `~/stack/.env`, traefik, authentik, docker network, homepage, IIS tenants file-provider, hermes install.

- [ ] **Step 3: Copy each cortex entry into cortex log**

Append each identified entry (verbatim) to `Z:\cortex\decisions\log.md` under a `## <date> — <topic>` header.

- [ ] **Step 4: Replace each entry in magiq log with breadcrumb**

For each moved entry in magiq, replace with:
```markdown
## <date> — <topic>

> Moved to `/mnt/shared/cortex/decisions/log.md` (2026-08-25).
```

### Task 9: Write `sync-contexts.sh`

**Files:**
- Create: `Z:\cortex\sync-contexts.sh`

- [ ] **Step 1: Write the full script**

Create `Z:\cortex\sync-contexts.sh` with content:

```bash
#!/bin/bash
# cortex-sync — deploy trigger for cortex + contexts.
#
# Reads /mnt/shared/cortex/contexts.yaml, rsyncs each context's
# traefik/**/*.yml into /mnt/shared/cortex/traefik-dynamic/<name>/,
# regenerates /mnt/shared/cortex/homepage-config/services.yaml from
# homepage-config-src/services.yaml + each context's homepage/services.yaml,
# then runs `docker compose up -d` for cortex-self and each context that
# has a docker-compose.yml.
#
# INVOCATION PATHS:
#   Manual: `ssh cortex cortex-sync <name|all>` from any dev machine.
#   Cron:   `/etc/cron.d/cortex-sync` runs `cortex-sync all` every 5 min.
#
# Both paths run this same script. Fully idempotent. Concurrent invocations
# serialized via flock on /var/lock/cortex-sync.lock.
#
# ARGS:
#   cortex-sync <name>              sync single context (must exist in contexts.yaml)
#   cortex-sync cortex              sync cortex-self (docker compose up -d in ~/stack)
#   cortex-sync all                 sync cortex-self + every context in contexts.yaml
#   cortex-sync --dry-run <name>    rsync -n + lint only, no compose invocation
#   cortex-sync --check-installed   diff installed /usr/local/bin/cortex-sync vs source
#
# SIDE EFFECTS:
#   - Writes to /mnt/shared/cortex/traefik-dynamic/<name>/
#   - Rewrites /mnt/shared/cortex/homepage-config/services.yaml
#   - Runs `docker compose up -d --remove-orphans` per context
#   - Logs to ~/stack/logs/sync-<name>-<ts>.log
#
# EXIT CODES:
#   0 = success
#   1 = usage error / unknown context
#   2 = NAS unmounted
#   3 = router-name collision after prefix
#   4 = docker compose failure
#   5 = drift detected (--check-installed)

set -euo pipefail

export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

CORTEX_ROOT="/mnt/shared/cortex"
CONTEXTS_YAML="$CORTEX_ROOT/contexts.yaml"
STACK_ROOT="$HOME/stack"
LOG_DIR="$STACK_ROOT/logs"
LOCK_FILE="/var/lock/cortex-sync.lock"
INSTALLED_PATH="/usr/local/bin/cortex-sync"

DRY_RUN=0

usage() {
  cat <<EOF
cortex-sync — deploy trigger for cortex + contexts

Usage:
  cortex-sync <name>           sync single context (name from contexts.yaml)
  cortex-sync cortex           sync cortex-self (compose up in ~/stack)
  cortex-sync all              sync cortex-self + every context in contexts.yaml
  cortex-sync --dry-run <name> rsync -n + lint only, no compose invocation
  cortex-sync --check-installed diff installed script vs source in cortex repo
EOF
}

check_installed() {
  if ! diff -q "$INSTALLED_PATH" "$CORTEX_ROOT/sync-contexts.sh" > /dev/null 2>&1; then
    echo "DRIFT: $INSTALLED_PATH differs from $CORTEX_ROOT/sync-contexts.sh" >&2
    echo "Reinstall: sudo cp $CORTEX_ROOT/sync-contexts.sh $INSTALLED_PATH" >&2
    exit 5
  fi
  echo "OK: installed script matches source"
  exit 0
}

# Parse contexts.yaml — minimal YAML parser for our known structure.
# Emits lines "name<TAB>path" one per registered context.
list_contexts() {
  awk '
    /^  - name:/ { name=$3 }
    /^    path:/ { print name "\t" $2 }
  ' "$CONTEXTS_YAML"
}

resolve_context_path() {
  local name="$1"
  list_contexts | awk -F'\t' -v n="$name" '$1 == n { print $2; found=1 } END { if (!found) exit 1 }'
}

sync_traefik_routes() {
  local name="$1"
  local ctx_root="$2"
  local dest="$CORTEX_ROOT/traefik-dynamic/$name"

  mkdir -p "$dest"

  # Find all traefik/*.yml files at any depth under ctx_root.
  # Flatten subpath to filename with "_" separator.
  # Example: projects/magiq-media/traefik/media-api.yml
  #      → traefik-dynamic/magiq/projects_magiq-media_media-api.yml
  local RSYNC_FLAGS="-a --delete"
  [ "$DRY_RUN" -eq 1 ] && RSYNC_FLAGS="$RSYNC_FLAGS -n"

  # Build file list first, then rsync each with renamed target
  local tmp_list
  tmp_list=$(mktemp)
  find "$ctx_root" -type f -path "*/traefik/*.yml" > "$tmp_list" 2>/dev/null || true

  # Wipe destination first to honor --delete semantics for this scheme
  if [ "$DRY_RUN" -eq 0 ]; then
    find "$dest" -maxdepth 1 -type f -name "*.yml" -delete 2>/dev/null || true
  fi

  while IFS= read -r src; do
    local rel="${src#$ctx_root/}"
    local flat="${rel//\//_}"
    if [ "$DRY_RUN" -eq 1 ]; then
      echo "DRY: cp $src $dest/$flat"
    else
      cp "$src" "$dest/$flat"
    fi
  done < "$tmp_list"

  rm -f "$tmp_list"
}

prefix_router_names() {
  local name="$1"
  local dest="$CORTEX_ROOT/traefik-dynamic/$name"

  [ "$DRY_RUN" -eq 1 ] && return 0
  [ -d "$dest" ] || return 0

  # In-place prefix: transform "routers:\n  foo:" into "routers:\n  <name>-foo:"
  # only if the router name doesn't already start with "<name>-".
  # Simple case: single-space indent under routers:. Extend if repo uses deeper nesting.
  for f in "$dest"/*.yml; do
    [ -f "$f" ] || continue
    python3 - "$f" "$name" <<'PY'
import sys, re
path, ctx = sys.argv[1], sys.argv[2]
prefix = ctx + "-"
with open(path) as fh: text = fh.read()
def repl(m):
    router = m.group(2)
    if router.startswith(prefix): return m.group(0)
    return f"{m.group(1)}{prefix}{router}:"
# Match router keys under `routers:` block (2-space indent under a 2-space `routers:`)
new = re.sub(r'(\n {4})([a-zA-Z0-9_-]+):', repl, text)
with open(path, 'w') as fh: fh.write(new)
PY
  done
}

check_router_collisions() {
  # After prefixing, ensure no router name appears in two different context files.
  local tmp
  tmp=$(mktemp)
  find "$CORTEX_ROOT/traefik-dynamic" -mindepth 2 -maxdepth 2 -name "*.yml" -type f | while read -r f; do
    python3 -c "
import sys, re
path = sys.argv[1]
with open(path) as fh: text = fh.read()
for m in re.finditer(r'\n {4}([a-zA-Z0-9_-]+):', text):
    print(f'{m.group(1)}\t{path}')
" "$f"
  done | sort > "$tmp"

  local dups
  dups=$(awk -F'\t' '{ print $1 }' "$tmp" | sort | uniq -d)
  if [ -n "$dups" ]; then
    echo "COLLISION: router names appear in multiple context files:" >&2
    for d in $dups; do
      echo "  $d:" >&2
      grep -P "^$d\t" "$tmp" | awk -F'\t' '{ print "    " $2 }' >&2
    done
    rm -f "$tmp"
    exit 3
  fi
  rm -f "$tmp"
}

regen_homepage() {
  local base="$CORTEX_ROOT/homepage-config-src/services.yaml"
  local dest="$CORTEX_ROOT/homepage-config/services.yaml"

  [ -f "$base" ] || { echo "WARN: no homepage-config-src/services.yaml, skipping regen"; return 0; }
  [ "$DRY_RUN" -eq 1 ] && { echo "DRY: would regen $dest"; return 0; }

  {
    echo "# GENERATED by cortex-sync from homepage-config-src/services.yaml + each context's homepage/services.yaml."
    echo "# DO NOT hand-edit. Edit homepage-config-src/services.yaml or your context's homepage/services.yaml instead."
    echo ""
    cat "$base"
    while IFS=$'\t' read -r name path; do
      local ctx_file="$path/homepage/services.yaml"
      if [ -f "$ctx_file" ]; then
        echo ""
        echo "- $name:"
        # Indent context content under the group
        sed 's/^/    /' "$ctx_file"
      fi
    done < <(list_contexts)
  } > "$dest.tmp"
  mv "$dest.tmp" "$dest"
}

sync_context() {
  local name="$1"
  local ctx_root
  ctx_root="$(resolve_context_path "$name")" || {
    echo "ERROR: context '$name' not in $CONTEXTS_YAML" >&2
    exit 1
  }

  echo "===> syncing $name (path: $ctx_root)"

  sync_traefik_routes "$name" "$ctx_root"
  prefix_router_names "$name"

  if [ -f "$ctx_root/docker-compose.yml" ] && [ "$DRY_RUN" -eq 0 ]; then
    echo "     compose up -d --remove-orphans"
    docker compose -f "$ctx_root/docker-compose.yml" up -d --remove-orphans
  fi
}

sync_cortex() {
  echo "===> syncing cortex (self)"
  if [ "$DRY_RUN" -eq 0 ]; then
    cd "$STACK_ROOT" && docker compose up -d
  else
    echo "DRY: would cd $STACK_ROOT && docker compose up -d"
  fi
}

main() {
  # Parse args
  local target=""
  while [ $# -gt 0 ]; do
    case "$1" in
      --dry-run) DRY_RUN=1; shift ;;
      --check-installed) check_installed ;;
      -h|--help) usage; exit 0 ;;
      *) target="$1"; shift ;;
    esac
  done

  [ -z "$target" ] && { usage; exit 1; }

  # NAS mount guard
  mountpoint -q /mnt/shared || {
    echo "ERROR: /mnt/shared not mounted" >&2
    exit 2
  }

  # Log setup
  mkdir -p "$LOG_DIR"

  # Acquire lock (serialize with cron)
  exec 200>"$LOCK_FILE"
  flock -w 60 200 || {
    echo "ERROR: could not acquire lock $LOCK_FILE within 60s" >&2
    exit 1
  }

  case "$target" in
    all)
      sync_cortex
      while IFS=$'\t' read -r name path; do
        sync_context "$name"
      done < <(list_contexts)
      regen_homepage
      check_router_collisions
      ;;
    cortex)
      sync_cortex
      ;;
    *)
      sync_context "$target"
      regen_homepage
      check_router_collisions
      ;;
  esac

  echo "===> done"
}

main "$@"
```

- [ ] **Step 2: Verify shebang + syntax**

Run:
```bash
bash -n Z:\cortex\sync-contexts.sh && echo OK
```
Expected: `OK` (no syntax errors).

### Task 10: Write `contexts.yaml`

**Files:**
- Create: `Z:\cortex\contexts.yaml`

- [ ] **Step 1: Write registry**

Create `Z:\cortex\contexts.yaml`:
```yaml
# cortex context registry — read by /usr/local/bin/cortex-sync.
#
# Each entry maps a context slug (used for traefik-dynamic/<name>/ subdir
# and router-name prefix) to the context's working-tree root on NAS.
#
# Add a new context: add an entry here, then `ssh cortex cortex-sync <name>`.
# Cortex itself is implicit (self) — do NOT list it here.

contexts:
  - name: magiq
    path: /mnt/shared/claudia/magiq
  # - name: claudette
  #   path: /mnt/shared/claudette
```

### Task 11: Write cron file

**Files:**
- Create: `Z:\cortex\cron\cortex-sync.cron`

- [ ] **Step 1: Create dir + file**

Run:
```cmd
mkdir Z:\cortex\cron
```

Create `Z:\cortex\cron\cortex-sync.cron`:
```
# cortex-sync poll — installed to /etc/cron.d/cortex-sync.
#
# Runs `cortex-sync all` every 5 minutes as user chase. Idempotent —
# rsync + docker compose up -d = no-op when nothing changed.
#
# Disable: sudo rm /etc/cron.d/cortex-sync
# View logs: ls ~/stack/logs/sync-*-<recent-ts>.log
# Verify running: sudo systemctl status cron

SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
MAILTO=""

*/5 * * * * chase /usr/local/bin/cortex-sync all >> /home/chase/stack/logs/cron.log 2>&1
```

### Task 12: Write `.gitignore`

**Files:**
- Create: `Z:\cortex\.gitignore`

- [ ] **Step 1: Write ignore rules**

Create `Z:\cortex\.gitignore`:
```
# Real secrets — cortex-box-local at ~/stack/.env, NEVER on NAS in git
.env

# Runtime output
logs/

# Context-generated route dirs — output of cortex-sync, don't commit
# magiq's changes indirectly. Cortex-owned routes in _cortex/ ARE tracked.
traefik-dynamic/*/
!traefik-dynamic/_cortex/

# Generated homepage file — rebuilt on every sync from src + contexts.
# homepage-config-src/services.yaml is the source of truth.
homepage-config/services.yaml
!homepage-config/settings.yaml
!homepage-config/bookmarks.yaml

# Editor / OS cruft
.DS_Store
Thumbs.db
*.swp
```

### Task 13: Write `README.md`

**Files:**
- Create: `Z:\cortex\README.md`

- [ ] **Step 1: Write quick-start README**

Create `Z:\cortex\README.md`:
```markdown
# cortex

Shared infrastructure for the AIS-OS tailnet. Runs on the MINISFORUM AI X1 Pro hostname `cortex`. Consumed by any sibling context (magiq, claudette, future).

**Repo lives on NAS at `/mnt/shared/cortex/` — dev machines mount as `Z:\cortex\` (Windows CIFS).**
**Origin remote: `git@github.com:cramone/cortex.git` — versioning only, not the deploy trigger.**

## Quick start

- **See what runs:** `ssh cortex 'docker ps'`
- **Deploy after any change:** `ssh cortex cortex-sync all`
- **Deploy one context:** `ssh cortex cortex-sync magiq`
- **Check for drift:** `ssh cortex cortex-sync --check-installed`
- **View logs:** `ssh cortex 'ls ~/stack/logs/'`

Cron polls every 5 minutes as a safety net — manual invocation only needed for immediate deploy.

## What lives here

- `docker-compose.yml` — cortex infra services (traefik, authentik, mysql, mssql, seq, redis, dns-internal, homepage, portainer, netdata, uptime-kuma, open-webui, cloudflare-ddns×2, cloudbeaver, whoami)
- `traefik-dynamic/_cortex/` — cortex-owned traefik routes (hermes, iis-tenants)
- `traefik-dynamic/<context>/` — GENERATED by cortex-sync from each context's `traefik/**/*.yml`
- `homepage-config-src/services.yaml` — cortex's homepage tile source
- `homepage-config/services.yaml` — GENERATED = src + each context's `homepage/services.yaml`
- `sync-contexts.sh` — deploy trigger; installed to `/usr/local/bin/cortex-sync` on cortex box
- `contexts.yaml` — registry of contexts cortex-sync knows about
- `cron/cortex-sync.cron` — installed to `/etc/cron.d/cortex-sync`

## Adding a context

1. Create working tree at `/mnt/shared/<name>/` (or nested like `/mnt/shared/foo/<name>/`).
2. Add entry to `contexts.yaml`.
3. In the context repo: add `traefik/*.yml`, optionally `homepage/services.yaml`, optionally `docker-compose.yml` (must reference `cortex_edge` as external).
4. `ssh cortex cortex-sync <name>`.
5. Verify at `~/stack/logs/sync-<name>-<ts>.log`.

See `docs/adding-a-context.md` for details.

## Architecture docs

- `docs/deploy-topology.md` — NAS-as-truth, trigger model, sync flow
- `docs/adding-a-context.md` — new-context wiring
- `docs/setup/` — one-time cortex box setup stages
- `docs/patterns/` — traefik file-provider, tower deploy flow
- `docs/known-gotchas.md` — router collisions, drift, NAS unmount

## Contracts published

1. **Docker network `cortex_edge`** — external, referenced by contexts as `networks: { cortex_edge: { external: true, name: cortex_edge } }`.
2. **Traefik file-provider dir** — `/mnt/shared/cortex/traefik-dynamic/` recursive, watched.
3. **Named middlewares** — `authentik-fwd`, others — see `traefik-dynamic/README.md`.
4. **Homepage tiles** — contexts drop `homepage/services.yaml`, cortex-sync merges.
```

### Task 14: Write architecture docs

**Files:**
- Create: `Z:\cortex\docs\deploy-topology.md`
- Create: `Z:\cortex\docs\adding-a-context.md`
- Create: `Z:\cortex\docs\known-gotchas.md`
- Create: `Z:\cortex\traefik-dynamic\README.md`
- Create: `Z:\cortex\homepage-config\README.md`

- [ ] **Step 1: Write `docs/deploy-topology.md`**

Create with the topology diagram + explanation from spec §5.2 + §5.4. Include:
- NAS as source of truth
- `~/stack/` real dir + symlink pattern
- `/usr/local/bin/cortex-sync` install
- `/etc/cron.d/cortex-sync` schedule
- Push flow (edit anywhere → cortex-sync trigger)
- Log location + rotation
- GitHub role (versioning only)

- [ ] **Step 2: Write `docs/adding-a-context.md`**

Step-by-step for wiring a new sibling repo:
1. `mkdir /mnt/shared/<name>` (or under existing namespace)
2. `git init` + optional GitHub remote
3. Add to `contexts.yaml`: `- name: <name>` + `path: /mnt/shared/<name>`
4. Add `traefik/*.yml` (optional) — example route
5. Add `homepage/services.yaml` (optional) — example tile group
6. Add `docker-compose.yml` (optional) — must have `networks: [cortex_edge]` + external declaration
7. Author `.env` per context's secret model (NAS-resident like magiq OR cortex-box-local pattern)
8. `ssh cortex cortex-sync <name>` — verify log
9. Check tiles at `home.ramonedevelopment.com`

- [ ] **Step 3: Write `docs/known-gotchas.md`**

Copy relevant items from `magiq/AI-X1-Pro-Setup-Guide.md` "Known Gotchas" section. Add cortex-split-specific ones:
- Router-name collision diagnostic (grep sync log for exit code 3)
- Sync log location + how to rotate
- `--check-installed` drift symptom
- NAS unmount → mount check fails, script exits 2
- Homepage regen wipes hand-edits (edit src or context/homepage instead)

- [ ] **Step 4: Write `traefik-dynamic/README.md`**

```markdown
# traefik-dynamic

Directory watched by cortex traefik via `--providers.file.directory=/etc/traefik/dynamic --providers.file.watch=true` (recursive).

## Layout

- `_cortex/` — cortex-owned routes (`hermes.yml`, `iis-tenants.yml`). Git-tracked. Hand-edited.
- `<context>/` — GENERATED by `cortex-sync` from `/mnt/shared/<context>/**/traefik/*.yml`. Do NOT hand-edit — changes get overwritten. Not tracked in git (`.gitignore`).

## Router-name convention

`cortex-sync` auto-prefixes context router names with `<context>-` on write. Two contexts can't declare the same router name — sync hard-fails with exit code 3.

## Middleware registry

Cortex-defined middlewares that contexts may reference by name:

| Name              | Purpose                                    | Defined in                    |
|-------------------|--------------------------------------------|-------------------------------|
| `authentik-fwd`   | forward-auth against authentik (domain-cookie) | `../docker-compose.yml` traefik labels |
| (add as needed)   |                                            |                               |

## YAML template for context routes

```yaml
http:
  routers:
    <route-name>:              # will become <context>-<route-name> after sync
      rule: "Host(`<host>.ramonedevelopment.com`)"
      entryPoints:
        - tailnet
      service: <service-name>
      middlewares:
        - authentik-fwd@docker
      tls:
        certResolver: public
  services:
    <service-name>:
      loadBalancer:
        servers:
          - url: "http://<container-name>:<port>"
```
```

- [ ] **Step 5: Write `homepage-config/README.md`**

```markdown
# homepage-config

Config dir for the `homepage` container (gethomepage/homepage). Bind-mounted at `/app/config`.

## Layout

- `settings.yaml` — cortex-owned. Global homepage settings. Hand-edited. Git-tracked.
- `bookmarks.yaml` — cortex-owned. Bookmarks section. Hand-edited. Git-tracked.
- `services.yaml` — **GENERATED** by cortex-sync on every run. Do NOT hand-edit. Not git-tracked.

## Generation model

`services.yaml` = `homepage-config-src/services.yaml` (cortex base) + each context's `homepage/services.yaml` (appended under a group named after the context).

## Adding tiles for a context

In your context repo, create `homepage/services.yaml`:

```yaml
- <tile-name>:
    icon: <icon>
    href: https://<host>.ramonedevelopment.com
    description: <what this is>
```

Run `ssh cortex cortex-sync <context>` — tile appears in the `<context>` group on `home.ramonedevelopment.com` within seconds (homepage container watches config dir).

## Adding cortex-owned tiles

Edit `homepage-config-src/services.yaml`. Run `ssh cortex cortex-sync cortex` (or `all`).
```

### Task 15: First cortex commit + push to GitHub

**Files:**
- All above created content

- [ ] **Step 1: Stage everything**

Run (Windows):
```cmd
cd /d Z:\cortex
git add .
git status
```
Expected: many new files, no `.env` (per .gitignore).

- [ ] **Step 2: Commit**

Run:
```cmd
git commit -m "$(cat <<'EOF'
initial import from magiq/cortex — cortex sibling repo

- docker-compose.yml (tower + mcp-azure-devops stripped)
- traefik-dynamic/_cortex/ (hermes + iis-tenants routes moved into subdir)
- homepage-config/ + homepage-config-src/ (moved from magiq, generated split)
- sync-contexts.sh (deploy trigger)
- contexts.yaml (context registry)
- cron/cortex-sync.cron (5-min poll)
- docs/setup/ (extracted AI-X1 Stages 0-14, 15.1-15.2, 22)
- docs/patterns/ (traefik-file-provider, tower-deploy-flow cortex-side)
- decisions/log.md (cortex-tagged entries lifted from magiq)

See docs/superpowers/specs/2026-08-24-cortex-split-design.md for design.
Implements Phase 0 of docs/superpowers/plans/2026-08-25-cortex-split.md.
EOF
)"
```

- [ ] **Step 3: Push to GitHub**

Run:
```cmd
git push -u origin main
```
Expected: `Branch 'main' set up to track 'origin/main'`.

### Task 16: Magiq commit (breadcrumbs + trimmed docs)

**Files:**
- Modified: `Z:\claudia\magiq\AI-X1-Pro-Setup-Guide.md`
- Modified: `Z:\claudia\magiq\hermes-integration.md`
- Modified: `Z:\claudia\magiq\docs\superpowers\specs\2026-08-07-iis-traefik-file-provider.md`
- Modified: `Z:\claudia\magiq\docs\superpowers\specs\2026-07-03-tower-cortex-deployment.md`
- Modified: `Z:\claudia\magiq\decisions\log.md`
- Created: `Z:\claudia\magiq\homepage-config\MOVED.md`

- [ ] **Step 1: Stage magiq changes**

Run (Windows):
```cmd
cd /d Z:\claudia\magiq
git add AI-X1-Pro-Setup-Guide.md hermes-integration.md docs/superpowers/specs/2026-08-07-iis-traefik-file-provider.md docs/superpowers/specs/2026-07-03-tower-cortex-deployment.md decisions/log.md homepage-config/MOVED.md
git status
```

- [ ] **Step 2: Commit**

Run:
```cmd
git commit -m "$(cat <<'EOF'
docs: breadcrumbs for cortex split (Phase 0)

Cortex infrastructure extracted into sibling repo at /mnt/shared/cortex/
(git origin cramone/cortex on GitHub). This commit adds breadcrumb stubs
in magiq pointing at the new locations:

- AI-X1-Pro-Setup-Guide.md: Stages 0-14, 15.1-15.2, 22 moved to
  cortex/docs/setup/
- hermes-integration.md: install-side moved to
  cortex/docs/setup/07-hermes-install.md
- specs/2026-08-07-iis-traefik-file-provider.md: full stub, moved to
  cortex/docs/patterns/traefik-file-provider.md
- specs/2026-07-03-tower-cortex-deployment.md: cortex-side moved to
  cortex/docs/patterns/tower-deploy-flow.md
- decisions/log.md: cortex-tagged entries lifted, breadcrumbs left
- homepage-config/MOVED.md: warning that edits here don't apply post-Phase-4

magiq/cortex/ folder + magiq/homepage-config/ dir deleted in Phase 5a.
See docs/superpowers/plans/2026-08-25-cortex-split.md.
EOF
)"
```

### Task 17: Install `cortex-sync` on cortex box (no cron yet)

**Files (cortex box):**
- Create: `/usr/local/bin/cortex-sync` (copy of `/mnt/shared/cortex/sync-contexts.sh`)

- [ ] **Step 1: Install script**

Run:
```bash
ssh cortex 'sudo cp /mnt/shared/cortex/sync-contexts.sh /usr/local/bin/cortex-sync && sudo chmod +x /usr/local/bin/cortex-sync && ls -la /usr/local/bin/cortex-sync'
```
Expected: `-rwxr-xr-x 1 root root ... /usr/local/bin/cortex-sync`.

- [ ] **Step 2: Verify --check-installed passes**

Run:
```bash
ssh cortex cortex-sync --check-installed
```
Expected: `OK: installed script matches source`.

- [ ] **Step 3: Smoke test with --dry-run**

Run:
```bash
ssh cortex cortex-sync --dry-run cortex
```
Expected: exits 0, prints `===> syncing cortex (self)` + `DRY: would cd ~/stack && docker compose up -d` + `===> done`. NO changes to filesystem or docker.

- [ ] **Step 4: Test magiq dry-run (should be no-op — magiq has no traefik files yet)**

Run:
```bash
ssh cortex cortex-sync --dry-run magiq
```
Expected: exits 0, prints `===> syncing magiq (path: /mnt/shared/claudia/magiq)` + `===> done`. No files listed under DRY (magiq has no `traefik/*.yml` yet).

- [ ] **Step 5: Verify NO cron installed yet**

Run:
```bash
ssh cortex 'ls /etc/cron.d/cortex-sync 2>&1'
```
Expected: `ls: cannot access '/etc/cron.d/cortex-sync': No such file or directory`.

---

## Phase 1 — extract magiq container definitions (no cutover yet)

### Task 18: Author magiq docker-compose.yml

**Files:**
- Create: `Z:\claudia\magiq\docker-compose.yml`

- [ ] **Step 1: Read tower + mcp-azure-devops service blocks from live cortex compose**

Read `Z:\claudia\magiq\cortex\docker-compose.yml`. Locate the `  tower:` and `  mcp-azure-devops:` service blocks. Note all `labels:` (traefik.*), `env_file:`, `build:`, `volumes:`, `image:`, `environment:`, `depends_on:`, `mem_limit:`, `restart:`, `<<:` (yaml anchors) content for each.

- [ ] **Step 2: Write new magiq compose**

Create `Z:\claudia\magiq\docker-compose.yml`:

```yaml
# magiq — application containers that consume the cortex infrastructure stack.
#
# tower and mcp-azure-devops moved here from the cortex compose as part of the
# cortex split (see /mnt/shared/cortex/docs/superpowers/specs/... spec). They
# stay attached to the cortex_edge external network so traefik keeps routing
# to them via docker labels — same routes as before, different compose project.
#
# env_file references NAS-resident /mnt/shared/claudia/magiq/.env (existing
# model, unchanged). Compose project = magiq (docker naming: magiq-tower-1,
# magiq-mcp-azure-devops-1).
#
# Deploy: `ssh cortex cortex-sync magiq` (or wait 5min for cron).

x-default-logging: &default-logging
  logging:
    driver: json-file
    options:
      max-size: "10m"
      max-file: "3"

networks:
  cortex_edge:
    external: true
    name: cortex_edge

services:
  tower:
    build:
      context: .
      dockerfile: tower/Dockerfile
    restart: unless-stopped
    <<: *default-logging
    user: "1000:1000"
    env_file:
      - ./.env
    volumes:
      - .:/app
    extra_hosts:
      - "host.docker.internal:host-gateway"
    networks:
      - cortex_edge
    labels:
      # ... COPY VERBATIM from live cortex compose tower block labels
      # (all traefik.enable, traefik.http.routers.tower.*, traefik.http.services.tower.*, homepage.* labels)

  mcp-azure-devops:
    build:
      context: ./mcp/azure-devops
      dockerfile: Dockerfile.gateway
    mem_limit: 1g
    restart: unless-stopped
    <<: *default-logging
    env_file:
      - ./.env
    networks:
      - cortex_edge
    labels:
      # ... COPY VERBATIM from live cortex compose mcp-azure-devops block labels
      # (traefik.enable, traefik.http.routers.mcp-ado.*, etc.)
```

Replace the two `# ... COPY VERBATIM` comment blocks with the actual labels copied verbatim from live cortex compose. Verify all labels transferred.

- [ ] **Step 3: Validate compose**

Run (on dev machine or via `ssh cortex`):
```bash
docker compose -f /mnt/shared/claudia/magiq/docker-compose.yml config > /dev/null && echo OK
```
Expected: `OK`. If `cortex_edge` external not found → skip (network doesn't exist yet, created in Phase 2). Add `--profile config-only` or accept the warning.

- [ ] **Step 4: Commit magiq compose**

Run:
```cmd
cd /d Z:\claudia\magiq
git add docker-compose.yml
git commit -m "$(cat <<'EOF'
feat: magiq docker-compose.yml — tower + mcp-azure-devops (Phase 1)

Extracted from the (still-live) cortex compose. Both services attach to
external cortex_edge network (created manually in Phase 2). env_file
reads existing NAS /mnt/shared/claudia/magiq/.env (unchanged). Same
traefik labels — routes stay identical.

Not deployed yet — Phase 2 creates the network, Phase 3 cuts over to
this compose via `cortex-sync magiq`.

See docs/superpowers/plans/2026-08-25-cortex-split.md.
EOF
)"
```

---

## Phase 2 — create `cortex_edge` network + prepare live cortex

### Task 19: Create `cortex_edge` docker network

**Files (cortex box):**
- No filesystem change — docker network only

- [ ] **Step 1: Create network**

Run:
```bash
ssh cortex 'docker network create cortex_edge'
```
Expected: hash (network ID) printed.

- [ ] **Step 2: Verify**

Run:
```bash
ssh cortex 'docker network inspect cortex_edge --format "{{.Name}} {{.Driver}}"'
```
Expected: `cortex_edge bridge`.

### Task 20: Add `cortex_edge` to LIVE cortex compose + reconcile

**Files:**
- Modify: `Z:\claudia\magiq\cortex\docker-compose.yml` (LIVE — top-level networks + tower/mcp-ado service network attachment)

- [ ] **Step 1: Edit live cortex compose — add top-level network**

Edit `Z:\claudia\magiq\cortex\docker-compose.yml`. Find `services:` line. ABOVE it, add:
```yaml
networks:
  cortex_edge:
    external: true
    name: cortex_edge
```

If a top-level `networks:` block already exists, add the `cortex_edge:` entry to it.

- [ ] **Step 2: Attach tower service to cortex_edge**

In the same file, find `  tower:` block. Find its `networks:` list (may not exist yet). Add or create:
```yaml
    networks:
      - default
      - cortex_edge
```
(Keep any existing default network attachment.)

- [ ] **Step 3: Attach mcp-azure-devops service to cortex_edge**

Same pattern for `  mcp-azure-devops:` block.

- [ ] **Step 4: Validate on dev machine**

Run:
```bash
docker compose -f Z:\claudia\magiq\cortex\docker-compose.yml config > /dev/null && echo OK
```
Expected: `OK`.

- [ ] **Step 5: Reconcile on cortex box (brief container restart)**

Run:
```bash
ssh cortex 'cd ~/stack && docker compose up -d'
```
Expected output includes: `Recreating stack-tower-1 ...` and `Recreating stack-mcp-azure-devops-1 ...`. Each takes ~5s.

- [ ] **Step 6: Verify both containers attached to cortex_edge**

Run:
```bash
ssh cortex 'docker network inspect cortex_edge --format "{{range .Containers}}{{.Name}} {{end}}"'
```
Expected: `stack-tower-1 stack-mcp-azure-devops-1` (order may differ).

- [ ] **Step 7: Verify routes still resolve**

Run:
```bash
curl -kI https://tower.ramonedevelopment.com 2>&1 | head -3
curl -kI https://mcp-ado.ramonedevelopment.com 2>&1 | head -3
```
Expected: `HTTP/2 200` or `HTTP/2 302` (via authentik).

- [ ] **Step 8: Commit live cortex compose change**

Run (in magiq repo since cortex/ is still a subfolder):
```cmd
cd /d Z:\claudia\magiq
git add cortex/docker-compose.yml
git commit -m "$(cat <<'EOF'
chore(cortex): attach tower + mcp-azure-devops to cortex_edge network (Phase 2)

Preparation for cortex split — adds external cortex_edge network reference
and attaches tower + mcp-azure-devops to it in addition to default. Enables
Phase 3 cutover where these services move to magiq compose but stay
reachable via traefik on the same network.

Live cortex compose reconciled — brief ~5s restart per container. No user-
visible impact.

See docs/superpowers/plans/2026-08-25-cortex-split.md.
EOF
)"
```

---

## Phase 3 — cutover magiq containers to magiq compose

### Task 21: Tag pre-cortex-split on both repos

**Files:**
- None — git tags only

- [ ] **Step 1: Tag magiq**

Run:
```cmd
cd /d Z:\claudia\magiq
git tag pre-cortex-split -m "State before magiq container cutover (Phase 3)"
```

- [ ] **Step 2: Tag cortex**

Run:
```cmd
cd /d Z:\cortex
git tag pre-cortex-split -m "State before magiq container cutover (Phase 3)"
```

### Task 22: `cortex-sync magiq` — start magiq-owned containers

**Files (cortex box):**
- No repo changes — docker action only

- [ ] **Step 1: Run cortex-sync magiq**

Run:
```bash
ssh cortex cortex-sync magiq
```
Expected output includes:
- `===> syncing magiq (path: /mnt/shared/claudia/magiq)`
- `compose up -d --remove-orphans`
- Docker build output (first-time build of tower + mcp-azure-devops images — takes minutes)
- `===> done`

If build fails, read error, fix magiq compose or Dockerfile, retry.

- [ ] **Step 2: Verify new containers up**

Run:
```bash
ssh cortex 'docker ps --format "{{.Names}}" | grep -E "^(magiq|stack)-(tower|mcp)"'
```
Expected (during router-overlap window):
```
magiq-tower-1
magiq-mcp-azure-devops-1
stack-tower-1
stack-mcp-azure-devops-1
```
Both old and new running.

- [ ] **Step 3: Note traefik duplicate-router warning**

Run:
```bash
ssh cortex 'docker logs stack-traefik-1 2>&1 | tail -20 | grep -i "duplicate\|already exist"'
```
Expected: warning lines about `tower@docker` or `mcp-ado@docker` router being redefined. Not fatal — traefik continues with one of them.

**PROCEED TO NEXT TASK IMMEDIATELY** (don't leave dual-router state for long).

### Task 23: Remove tower + mcp-azure-devops from LIVE cortex compose

**Files:**
- Modify: `Z:\claudia\magiq\cortex\docker-compose.yml` (delete tower + mcp-azure-devops service blocks)

- [ ] **Step 1: Delete both service blocks**

Edit `Z:\claudia\magiq\cortex\docker-compose.yml`. Remove:
- `  tower:` service block (whole block, all lines under it, until next service key at 2-space indent)
- `  mcp-azure-devops:` service block (same)
- Any `depends_on:` lines referencing either

- [ ] **Step 2: Validate**

Run:
```bash
docker compose -f Z:\claudia\magiq\cortex\docker-compose.yml config > /dev/null && echo OK
```
Expected: `OK`.

- [ ] **Step 3: Reconcile on cortex box — old containers stop**

Run:
```bash
ssh cortex 'cd ~/stack && docker compose up -d --remove-orphans'
```
Expected output includes: `Stopping stack-tower-1 ... done` and `Stopping stack-mcp-azure-devops-1 ... done`. `Removing` follows.

### Task 24: Verify Phase 3 cutover

- [ ] **Step 1: Only magiq-* containers remain**

Run:
```bash
ssh cortex 'docker ps --format "{{.Names}}" | grep -E "tower|mcp-azure-devops"'
```
Expected:
```
magiq-tower-1
magiq-mcp-azure-devops-1
```
No `stack-tower-1` or `stack-mcp-azure-devops-1`.

- [ ] **Step 2: Routes still resolve**

Run:
```bash
curl -kI https://tower.ramonedevelopment.com 2>&1 | head -1
curl -kI https://mcp-ado.ramonedevelopment.com 2>&1 | head -1
```
Expected: `HTTP/2 200` or `HTTP/2 302`.

- [ ] **Step 3: Sync log clean**

Run:
```bash
ssh cortex 'ls -t ~/stack/logs/sync-magiq-*.log | head -1 | xargs tail -30'
```
Expected: last log ends with `===> done`. No errors.

- [ ] **Step 4: Traefik logs — no duplicate warnings anymore**

Run:
```bash
ssh cortex 'docker logs stack-traefik-1 --since 2m 2>&1 | grep -i "duplicate\|already exist" | wc -l'
```
Expected: `0` (or only warnings older than 2 minutes).

- [ ] **Step 5: Commit LIVE cortex compose change**

Run:
```cmd
cd /d Z:\claudia\magiq
git add cortex/docker-compose.yml
git commit -m "$(cat <<'EOF'
chore(cortex): remove tower + mcp-azure-devops from live cortex compose (Phase 3)

These now run under magiq compose project on cortex_edge network. Old
stack-tower-1 + stack-mcp-azure-devops-1 stopped and removed by
`docker compose up -d --remove-orphans`.

Router-overlap window (~30-60s between cortex-sync magiq bringing new
containers up and this compose reconcile stopping old ones) accepted
per plan Phase 3 documentation.

See docs/superpowers/plans/2026-08-25-cortex-split.md.
EOF
)"
```

---

## Phase 4 — cutover cortex working tree

### Task 25: Prep new symlinks on cortex box (non-breaking)

**Files (cortex box):**
- Create: `~/stack/traefik-dynamic-new` (symlink)
- Create: `~/stack/homepage-config-new` (symlink)

- [ ] **Step 1: Create staging symlinks**

Run:
```bash
ssh cortex '
  cd ~/stack
  ln -sfn /mnt/shared/cortex/traefik-dynamic traefik-dynamic-new
  ln -sfn /mnt/shared/cortex/homepage-config homepage-config-new
  ls -la traefik-dynamic-new homepage-config-new
'
```
Expected: both symlinks show as `lrwxrwxrwx ...` and target resolves (`ls -la` shows target dir contents implicitly on symlinks).

### Task 26: Atomic switch — flip symlinks + reconcile

**Files (cortex box):**
- Modify: `~/stack/docker-compose.yml` (symlink target changed)
- Delete: `~/stack/traefik-dynamic/` (real cruft dir)
- Rename: `~/stack/traefik-dynamic-new` → `traefik-dynamic`
- Create/rename: `~/stack/homepage-config` (from `homepage-config-new`)

- [ ] **Step 1: Verify cron NOT installed (safety check)**

Run:
```bash
ssh cortex 'ls /etc/cron.d/cortex-sync 2>&1'
```
Expected: `No such file or directory`. If exists, ABORT — cron would race the atomic switch.

- [ ] **Step 2: Execute atomic switch in single ssh session**

Run:
```bash
ssh cortex '
  cd ~/stack && \
    ln -sfn /mnt/shared/cortex/docker-compose.yml docker-compose.yml && \
    rm -rf traefik-dynamic && mv traefik-dynamic-new traefik-dynamic && \
    { rm -rf homepage-config 2>/dev/null; true; } && mv homepage-config-new homepage-config && \
    docker compose up -d
'
```
Expected output includes: `Recreating stack-traefik-1 ... done` and `Recreating stack-homepage-1 ... done`. Each takes ~5-10s. Other services stay up (no unexpected `Recreating`).

- [ ] **Step 3: Wait ~15s for traefik + homepage to be ready**

Run:
```bash
sleep 15
ssh cortex 'docker ps --format "{{.Names}} {{.Status}}" | grep -E "traefik|homepage"'
```
Expected: both `Up`.

### Task 27: Verify Phase 4 cutover

- [ ] **Step 1: Symlinks correct**

Run:
```bash
ssh cortex '
  readlink ~/stack/docker-compose.yml
  readlink ~/stack/traefik-dynamic
  readlink ~/stack/homepage-config
'
```
Expected:
```
/mnt/shared/cortex/docker-compose.yml
/mnt/shared/cortex/traefik-dynamic
/mnt/shared/cortex/homepage-config
```

- [ ] **Step 2: cortex_edge survived — magiq containers still attached**

Run:
```bash
ssh cortex 'docker network inspect cortex_edge --format "{{range .Containers}}{{.Name}} {{end}}"'
```
Expected: contains `magiq-tower-1 magiq-mcp-azure-devops-1`.

- [ ] **Step 3: All cortex services running**

Run:
```bash
ssh cortex 'docker ps --format "{{.Names}}" | sort > /tmp/post-phase4-containers.txt; diff /tmp/pre-split-containers.txt /tmp/post-phase4-containers.txt || true'
```
Expected diff: `-stack-tower-1`, `-stack-mcp-azure-devops-1`, `+magiq-tower-1`, `+magiq-mcp-azure-devops-1`. All other containers unchanged.

- [ ] **Step 4: Routes resolve**

Run:
```bash
for host in home hermes tower mcp-ado logs portainer status; do
  echo -n "$host: "
  curl -kI --max-time 5 https://$host.ramonedevelopment.com 2>&1 | head -1
done
```
Expected: all show `HTTP/2 200`, `HTTP/2 302`, or `HTTP/2 401` (through authentik).

### Task 28: Reconcile magiq + install cron

**Files (cortex box):**
- Create: `/etc/cron.d/cortex-sync`
- Create: `/mnt/shared/cortex/homepage-config/services.yaml` (first regen)

- [ ] **Step 1: Reconcile magiq compose (catches any edits between Phase 1 and now)**

Run:
```bash
ssh cortex cortex-sync magiq
```
Expected: `===> syncing magiq ...` + `compose up -d --remove-orphans` (no-op if magiq compose unchanged) + `===> done`.

- [ ] **Step 2: Run cortex-sync all — first real full sync**

Run:
```bash
ssh cortex cortex-sync all
```
Expected:
- `===> syncing cortex (self)` + `docker compose up -d` (no-op).
- `===> syncing magiq (path: ...)` + compose reconcile (no-op).
- `===> done`.
- Side effect: writes `/mnt/shared/cortex/homepage-config/services.yaml` for the first time.

- [ ] **Step 3: Verify homepage services.yaml generated**

Run:
```bash
ssh cortex 'head -10 /mnt/shared/cortex/homepage-config/services.yaml'
```
Expected: starts with `# GENERATED by cortex-sync from homepage-config-src/services.yaml + each context's homepage/services.yaml.`

- [ ] **Step 4: Install cron**

Run:
```bash
ssh cortex '
  sudo cp /mnt/shared/cortex/cron/cortex-sync.cron /etc/cron.d/cortex-sync
  sudo chmod 644 /etc/cron.d/cortex-sync
  sudo systemctl status cron | head -3
  cat /etc/cron.d/cortex-sync
'
```
Expected: cron service `active (running)`; cron file content shown.

- [ ] **Step 5: Wait 6 min, verify cron fired**

Run:
```bash
sleep 360
ssh cortex 'ls -t ~/stack/logs/sync-*.log | head -3'
```
Expected: at least one fresh log with timestamp within the last 6 minutes.

### Task 29: Cleanup Stage 22 leftovers on cortex box

**Files (cortex box):**
- Delete: `~/stack/docker-compose.yml.bak-presymlink`
- Delete: `~/stack/iis-tenants.yml`

- [ ] **Step 1: Delete leftovers**

Run:
```bash
ssh cortex '
  rm ~/stack/docker-compose.yml.bak-presymlink
  rm ~/stack/iis-tenants.yml
  ls -la ~/stack/
'
```
Expected: `~/stack/` now contains only `.env`, `docker-compose.yml` (symlink), `traefik-dynamic` (symlink), `homepage-config` (symlink), `logs/`. Nothing else.

- [ ] **Step 2: Symlink sanity — nothing dangling**

Run:
```bash
ssh cortex 'find ~/stack -type l -not -exec test -e {} \; -print'
```
Expected: empty output (all symlinks resolve).

- [ ] **Step 3: Baseline comparison — symlinks**

Run:
```bash
ssh cortex 'find ~/stack -maxdepth 2 -type l > /tmp/post-phase4-symlinks.txt; diff /tmp/pre-split-symlinks.txt /tmp/post-phase4-symlinks.txt'
```
Expected diff:
```
- ~/stack/docker-compose.yml → /mnt/shared/claudia/magiq/cortex/docker-compose.yml (old)
+ ~/stack/docker-compose.yml → /mnt/shared/cortex/docker-compose.yml (new)
+ ~/stack/traefik-dynamic → /mnt/shared/cortex/traefik-dynamic
+ ~/stack/homepage-config → /mnt/shared/cortex/homepage-config
```

---

## Phase 5 — retire the magiq/cortex/ subfolder (only after ≥7 days stable)

### Task 30: Wait ≥7 days + verify stability

- [ ] **Step 1: Wait**

Do not run this task until at least 7 days after Phase 4d completion.

- [ ] **Step 2: Verify stability**

Run:
```bash
ssh cortex '
  # Sync logs — no errors in past 7 days
  find ~/stack/logs -name "sync-*.log" -mtime -7 -exec grep -l ERROR {} \; | wc -l
  # Container uptime
  docker ps --format "{{.Names}} {{.Status}}"
  # cortex_edge stability
  docker network inspect cortex_edge --format "{{range .Containers}}{{.Name}} {{end}}"
'
```
Expected: zero error logs, all containers up multiple days, cortex_edge has expected members.

If ANY failure signs, hold Phase 5 until root-caused.

### Task 31: Delete magiq/cortex/ + magiq/homepage-config/ + deploy-cortex.sh

**Files:**
- Delete: `Z:\claudia\magiq\cortex\`
- Delete: `Z:\claudia\magiq\homepage-config\`
- Delete: `Z:\claudia\magiq\tower\deploy-cortex.sh`
- Modify: `Z:\claudia\magiq\scripts\tower-autosync.sh` (remove deploy-cortex.sh refs)
- Modify: `Z:\claudia\magiq\scripts\tower-deploy-check.sh` (remove deploy-cortex.sh refs)
- Create: `Z:\claudia\magiq\CORTEX-MOVED.md`

- [ ] **Step 1: Read tower-autosync + tower-deploy-check for deploy-cortex refs**

Run:
```bash
grep -n 'deploy-cortex' Z:\claudia\magiq\scripts\tower-autosync.sh Z:\claudia\magiq\scripts\tower-deploy-check.sh Z:\claudia\magiq\tower\deploy-cortex.sh
```
Note which lines reference the deprecated script.

- [ ] **Step 2: Update scripts — remove or rename deploy-cortex refs**

Edit `Z:\claudia\magiq\scripts\tower-autosync.sh`: replace deploy-cortex.sh invocations with `ssh cortex cortex-sync magiq`. Preserve any deployed-tag tracking under a new name (`tower-deploy-tag.sh` if needed).

Edit `Z:\claudia\magiq\scripts\tower-deploy-check.sh`: same. This script checks if there are undeployed changes — replace its "undeployed" check with a `cortex-sync --dry-run magiq` diff or a git rev-parse against a `deployed-magiq` tag maintained by cortex-sync.

- [ ] **Step 3: Delete files**

Run (Windows):
```cmd
rmdir /S /Q Z:\claudia\magiq\cortex
rmdir /S /Q Z:\claudia\magiq\homepage-config
del Z:\claudia\magiq\tower\deploy-cortex.sh
```

- [ ] **Step 4: Create CORTEX-MOVED.md at magiq root**

Create `Z:\claudia\magiq\CORTEX-MOVED.md`:
```markdown
# Cortex moved out of magiq

The `cortex/` subfolder that used to live at the root of this repo has been
extracted into a standalone sibling repo:

- **NAS path:** `/mnt/shared/cortex/`
- **Dev-machine mount:** `Z:\cortex\` (Windows CIFS)
- **Git origin:** `git@github.com:cramone/cortex.git`

The `homepage-config/` dir also moved to cortex — homepage is a cortex-infra
container. Add your own homepage tiles via `magiq/homepage/services.yaml`
(auto-merged by cortex-sync).

## Deploy

Cortex + all contexts (magiq, claudette, future) are deployed via a single
script on the cortex box:

- Manual: `ssh cortex cortex-sync <context|all>` (fires immediately)
- Cron: `/etc/cron.d/cortex-sync` runs `cortex-sync all` every 5 minutes

Push to git (GitHub, ADO, etc.) is versioning only, not a deploy trigger.

## What to read

- `/mnt/shared/cortex/README.md` — quick-start
- `/mnt/shared/cortex/docs/deploy-topology.md` — full topology
- `/mnt/shared/cortex/docs/adding-a-context.md` — wire a new context
- `references/adrs/adr-NNN-cortex-split.md` — full ADR

This file will be deleted one release cycle after the split (git history
preserves the pointer).
```

- [ ] **Step 5: Stage + commit**

Run:
```cmd
cd /d Z:\claudia\magiq
git add -A cortex homepage-config tower/deploy-cortex.sh scripts/tower-autosync.sh scripts/tower-deploy-check.sh CORTEX-MOVED.md
git status
git commit -m "$(cat <<'EOF'
refactor: remove cortex/ subfolder + homepage-config/ + deploy-cortex.sh (Phase 5a)

Cortex infrastructure now lives at /mnt/shared/cortex/ (git origin
cramone/cortex on GitHub). Deploy trigger is `ssh cortex cortex-sync`,
not deploy-cortex.sh.

- cortex/ folder deleted (was subfolder, now sibling repo)
- homepage-config/ deleted (homepage container now bind-mounts cortex copy)
- tower/deploy-cortex.sh deleted (obsolete — cortex-sync handles deploy)
- scripts/tower-autosync.sh + tower-deploy-check.sh: deploy-cortex refs
  replaced with cortex-sync invocations
- CORTEX-MOVED.md: breadcrumb (deleted one release cycle from now)

See docs/superpowers/plans/2026-08-25-cortex-split.md Phase 5.
See /mnt/shared/cortex/README.md for cortex quick-start.
EOF
)"
```

### Task 32: Grep for deprecated paths + verify clean

- [ ] **Step 1: Grep cortex box**

Run:
```bash
ssh cortex '
  echo "=== ~/ ==="
  grep -r "/mnt/shared/claudia/magiq/cortex\|/mnt/shared/claudia/magiq/homepage-config\|deploy-cortex.sh" ~/ 2>/dev/null | grep -v "\.git/" | head -20
  echo "=== /etc/ ==="
  sudo grep -r "/mnt/shared/claudia/magiq/cortex\|/mnt/shared/claudia/magiq/homepage-config" /etc/ 2>/dev/null | head -20
  echo "=== /srv/ ==="
  sudo grep -r "/mnt/shared/claudia/magiq/cortex\|/mnt/shared/claudia/magiq/homepage-config" /srv/ 2>/dev/null | head -20
'
```
Expected: no output (or only in backup files clearly labeled `.bak`).

If any live reference: fix it.

- [ ] **Step 2: Grep magiq repo**

Run:
```bash
cd /d Z:\claudia\magiq
git grep -n "cortex/docker-compose\|/mnt/shared/claudia/magiq/cortex\|deploy-cortex.sh" -- ':(exclude)CORTEX-MOVED.md'
```
Expected: no output.

- [ ] **Step 3: Grep cortex repo**

Run:
```bash
cd /d Z:\cortex
git grep -n "/mnt/shared/claudia/magiq/cortex\|/mnt/shared/claudia/magiq/homepage-config" -- ':(exclude)docs/setup/*' ':(exclude)decisions/log.md'
```
Expected: no output (setup docs and decisions log may reference old paths in historical context — that's fine).

### Task 33: Symlink audit after Phase 5

- [ ] **Step 1: Dangling symlink check**

Run:
```bash
ssh cortex 'find ~/stack -type l -not -exec test -e {} \; -print'
```
Expected: empty output.

- [ ] **Step 2: Symlink layout unchanged from Phase 4**

Run:
```bash
ssh cortex 'find ~/stack -maxdepth 2 -type l'
```
Expected: same 3 symlinks as after Phase 4d.

### Task 34: Update magiq CLAUDE.md + README.md + aios.config.md

**Files:**
- Modify: `Z:\claudia\magiq\CLAUDE.md`
- Modify: `Z:\claudia\magiq\README.md`
- Modify: `Z:\claudia\magiq\aios.config.md` (if references cortex)

- [ ] **Step 1: Add cortex sibling section to CLAUDE.md**

Edit `Z:\claudia\magiq\CLAUDE.md`. Add a new section (after the existing structure):

```markdown
## Cortex sibling repo

Cortex infrastructure lives at `Z:\cortex\` (`/mnt/shared/cortex/`) — separate git repo, GitHub origin `cramone/cortex`.

**Deploy:** `ssh cortex cortex-sync <context>` (or wait 5min for cron poll).

**Adding a magiq route or homepage tile:**
- Route: create `projects/{name}/traefik/*.yml` or `traefik/*.yml`. Reference `authentik-fwd@docker` middleware. Router names auto-prefixed with `magiq-` on sync.
- Homepage tile: create `homepage/services.yaml` with tile entries. Merged into cortex homepage under `magiq` group.

**Adding a magiq container:**
- Add service to `docker-compose.yml`. Attach to `cortex_edge` external network:
  ```yaml
  networks:
    - cortex_edge
  ```
  With top-level:
  ```yaml
  networks:
    cortex_edge:
      external: true
      name: cortex_edge
  ```
- Traefik labels work as usual (docker provider).
- Run `ssh cortex cortex-sync magiq` to deploy.

See `Z:\cortex\README.md` for full cortex quick-start.
```

- [ ] **Step 2: Update magiq README.md deploy instructions**

Edit `Z:\claudia\magiq\README.md`. Find deploy section. Replace old `./tower/deploy-cortex.sh` references with:
```markdown
## Deploy

Cortex infra + all context containers deploy via a single script on the cortex box:

- Immediate: `ssh cortex cortex-sync magiq` (or `cortex-sync all` for everything).
- Auto: cron runs `cortex-sync all` every 5 minutes.

See `Z:\cortex\README.md` for details.
```

- [ ] **Step 3: Update aios.config.md if it references cortex**

Run:
```bash
grep -n cortex Z:\claudia\magiq\aios.config.md
```
If matches: update to point at `Z:\cortex\` / `/mnt/shared/cortex/`.

- [ ] **Step 4: Commit**

Run:
```cmd
cd /d Z:\claudia\magiq
git add CLAUDE.md README.md aios.config.md
git commit -m "docs: update magiq CLAUDE + README for cortex sibling repo (Phase 5d)"
```

### Task 35: Write ADR

**Files:**
- Create: `Z:\claudia\magiq\references\adrs\adr-NNN-cortex-split.md` (NNN = next available number)
- Modify: `Z:\claudia\magiq\decisions\log.md` (add entry pointing at ADR)

- [ ] **Step 1: Determine next ADR number**

Run:
```cmd
dir Z:\claudia\magiq\references\adrs\adr-*.md
```
Note highest existing number. New one = highest + 1.

- [ ] **Step 2: Write ADR**

Create `Z:\claudia\magiq\references\adrs\adr-<NNN>-cortex-split.md`:

```markdown
# ADR <NNN> — Cortex Split from Magiq

**Date:** 2026-08-25
**Status:** Accepted
**Deciders:** Chase Ramone

## Context

The `cortex/` subfolder inside `Z:\claudia\magiq\` mixed shared infrastructure (traefik, authentik, docker stack, DNS, storage, observability) with the MAGIQ AIOS repo. Consequences:
- Cortex could not evolve independently — every infra change required a magiq commit.
- Future sibling contexts (claudette, etc.) had no clean way to register traefik routes or homepage tiles.
- Coupling ran one-way (`cortex/docker-compose.yml` → `/mnt/shared/claudia/magiq/*`) — magiq never imported cortex.

## Decision

Extract cortex into a standalone sibling repo at `/mnt/shared/cortex/` (dev-mount `Z:\cortex\`, GitHub origin `cramone/cortex`). Establish a file-drop contract: any context registers traefik routes via `traefik/*.yml` and homepage tiles via `homepage/services.yaml` in its own repo. A `cortex-sync` script on the cortex box (manual + 5-min cron) rsyncs, prefixes router names by context, regenerates homepage config, and runs `docker compose up -d` per context.

NAS remains source of truth for all repos. Bare git repos and post-receive hooks were considered and rejected as unnecessary given the shared NAS filesystem. GitHub `cramone/cortex` is used for versioning/backup only, not for deploy trigger.

Tower and mcp-azure-devops (magiq-specific containers) moved out of cortex compose into a new `magiq/docker-compose.yml`, joining a manually-created external docker network `cortex_edge` that both stacks reference.

## Consequences

**Positive:**
- Cortex has its own history, own GitHub repo, own release cycle.
- Contexts self-register — new sibling contexts wire up in ~5 minutes via `contexts.yaml` + first `cortex-sync`.
- Router-name collisions caught at sync time (hard-fail).
- Homepage tiles composable across contexts.
- Cutover was zero-downtime except ~15s during Phase 4 traefik+homepage recreate.

**Negative:**
- Deploy trigger is now a separate action from git commit. Chase must remember to run `cortex-sync` OR wait 5min for cron. Documented in magiq CLAUDE.md + cortex README.
- Two homepage-config paths existed briefly (magiq copy + cortex copy) during Phases 0-4. Cleaned up in Phase 5.
- `~/stack/` on cortex box now has 3 symlinks (compose, traefik-dynamic, homepage-config) instead of 1. Documented in cortex `docs/setup/22-secrets-local-env.md`.

**Neutral:**
- Cortex `.env` model unchanged (cortex-box-local at `~/stack/.env`, never on NAS, Stage 22 constraint preserved).
- Magiq `.env` model unchanged (NAS-resident at `/mnt/shared/claudia/magiq/.env`).
- Traefik entrypoints, authentik providers, domain-cookie model — all unchanged.

## Alternatives considered

- **Git-hook-based deploy trigger (bare repo on cortex box + post-receive):** rejected — required Chase to push to two remotes (GitHub + cortex-box) and added git infrastructure that duplicates the NAS-shared filesystem.
- **Retire NAS, clone repos on cortex box:** rejected — Chase edits from multiple computers via NAS share; local clones would fragment history and break the workflow.
- **Cortex + contexts in monorepo with CODEOWNERS:** rejected — didn't solve the "cortex can't evolve independently" concern.
- **Webhook-triggered deploy from GitHub push:** deferred to future — cron + manual is sufficient for current scale.

## References

- Design spec: `docs/superpowers/specs/2026-08-24-cortex-split-design.md`
- Implementation plan: `docs/superpowers/plans/2026-08-25-cortex-split.md`
- Cortex repo: `/mnt/shared/cortex/`, `git@github.com:cramone/cortex.git`
- Cortex decisions log: `/mnt/shared/cortex/decisions/log.md`
```

- [ ] **Step 3: Add decisions log entry**

Append to `Z:\claudia\magiq\decisions\log.md`:
```markdown
## 2026-08-25 — Cortex split from magiq

Extracted cortex infrastructure into standalone sibling repo at `/mnt/shared/cortex/`. Deploy trigger is `ssh cortex cortex-sync`. See `references/adrs/adr-<NNN>-cortex-split.md` for full context.
```

- [ ] **Step 4: Commit ADR**

Run:
```cmd
cd /d Z:\claudia\magiq
git add references/adrs/adr-<NNN>-cortex-split.md decisions/log.md
git commit -m "docs(adr): ADR <NNN> — cortex split from magiq (Phase 5e)"
```

### Task 36: (deferred one release cycle) Delete CORTEX-MOVED.md

**Files:**
- Delete: `Z:\claudia\magiq\CORTEX-MOVED.md`

- [ ] **Step 1: Wait one release cycle after Phase 5**

Do not execute until the cortex split has been in place through at least one release/deploy cycle of magiq. Git history preserves the CORTEX-MOVED breadcrumb.

- [ ] **Step 2: Delete + commit**

Run:
```cmd
cd /d Z:\claudia\magiq
del CORTEX-MOVED.md
git add CORTEX-MOVED.md
git commit -m "chore: remove CORTEX-MOVED.md breadcrumb — split settled (Phase 5f)"
```

- [ ] **Step 3: Also delete deferred stub in magiq specs dir**

Run:
```cmd
del Z:\claudia\magiq\docs\superpowers\specs\2026-08-07-iis-traefik-file-provider.md
git add docs/superpowers/specs/2026-08-07-iis-traefik-file-provider.md
git commit --amend --no-edit
```

---

## Self-review

**Spec coverage checked:**
- ✅ §5.1 repo layout — Task 2 (import), Tasks 4-5 (reorg), Tasks 6-8 (docs)
- ✅ §5.2 deploy topology — Task 17 (install), Task 28 (cron)
- ✅ §5.3 contracts — Task 18 (cortex_edge in magiq compose), Task 19 (network create), Task 20 (attach), Task 14 (docs)
- ✅ §5.4 sync mechanism — Task 9 (script), Task 10 (registry), Task 11 (cron file), Task 17 (install), Task 28 (cron install)
- ✅ §5.5 env files — Task 18 (magiq env_file), Task 29 (no changes to ~/stack/.env)
- ✅ §5.6 rollback — Task 21 (pre-cortex-split tag)
- ✅ §6 all phases — Tasks 1-36
- ✅ §7 docs deliverables — Tasks 13-15, 34-35
- ✅ §8 risks — mitigations wired into script (Task 9: mountpoint guard, flock, --check-installed, router prefix + collision check)

**Placeholder scan:** No TBDs, TODOs, "TBD in implementation", "similar to Task N" without full code. Concrete file paths + commands + code throughout.

**Type consistency:** Script name is consistently `cortex-sync` (installed) vs `sync-contexts.sh` (source). `cortex_edge` network name consistent. Context name `magiq` consistent. Paths `/mnt/shared/cortex/` consistent.

**Known handoffs to implementation (not gaps, decisions plan surfaces):**
- Task 6 line-number ranges for AI-X1 Guide extraction are approximate — engineer verifies actual boundaries on read.
- Task 18 label copy is literal ("COPY VERBATIM") — engineer reads live compose and copies traefik labels for tower + mcp-ado.
- Task 31 script updates (tower-autosync, tower-deploy-check) require reading the actual scripts to preserve deployed-tag logic — general direction given, exact edits engineer-driven.
