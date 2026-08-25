# Cortex Split — Design

**Date:** 2026-08-24
**Status:** Approved (design), pending implementation plan
**Author:** Chase Ramone + Claude
**Supersedes:** partially — `2026-07-03-tower-cortex-deployment.md` (tower deploy flow now `cortex-sync`-driven; tower now lives in magiq repo, not cortex/)

---

## 1. Problem

`cortex/` currently sits inside `Z:\claudia\magiq\` as a subfolder. This mixes two concerns in one repo and one git history:

- **Cortex** — shared infrastructure (traefik, authentik, docker stack, DNS, storage, observability) that any context or project can consume.
- **MAGIQ AIOS** — the operator's personal AIOS, AIS-OS projects, tower, MCP integrations, decisions log.

Consequences today:
- Cortex cannot evolve independently. Every change to shared infra requires a magiq commit.
- Future sibling contexts (`claudette`, others) have no clean way to register their own traefik routes or homepage tiles with cortex.
- The dependency runs only one way (`cortex/docker-compose.yml` → `/mnt/shared/claudia/magiq/*`); magiq never imports cortex. This is the accidental coupling worth removing.

## 2. Goals

1. Cortex becomes an independent repo, deployable and evolvable without touching magiq.
2. Any sibling context (magiq, claudette, future) can register a traefik service or homepage tile with cortex through a well-defined interface — no code inside cortex needs to know about the context.
3. No user-visible service downtime during cutover; every phase is reversible until the retirement phase.
4. Every piece of the new wiring is documented in-repo so recovery does not require re-derivation.
5. NAS remains the source of truth for all repos. Git remotes (GitHub, ADO, etc.) exist for versioning/backup/collab only — deploy trigger is separate.

## 3. Non-goals

- Redesigning traefik entrypoints, authentik providers, or the domain-cookie model. All existing patterns (loopback binds, forward-auth-domain-level, tailnet vs. public entrypoints) carry over unchanged.
- Splitting magiq itself. Only `cortex/` moves.
- Moving cortex to a different physical host. Same MINISFORUM AI X1 Pro, same tailnet IP.
- Retiring the NAS. NAS stays as source of truth.
- Git-hook-based deploy triggers. Deploy is script-triggered (see §5.4).

## 4. Current-state inventory (confirmed 2026-08-24)

**Cortex files today (`Z:\claudia\magiq\cortex\` = `/mnt/shared/claudia/magiq/cortex/`):**
- `docker-compose.yml` (35 KB, ~20 services)
- `traefik-dynamic/hermes.yml`, `traefik-dynamic/iis-tenants.yml`
- `.env.example` (cortex-local secrets template; real values in `~/stack/.env` cortex-box-local)

**Cortex box current layout (verified):**
```
~/stack/                          real dir, chase-owned
├── .env                          real file, chmod 600, cortex secrets (5 KB, dated Jul 13)
├── docker-compose.yml            SYMLINK → /mnt/shared/claudia/magiq/cortex/docker-compose.yml
├── docker-compose.yml.bak-presymlink  (leftover from Stage 22 migration)
├── iis-tenants.yml               real file (leftover — actual live copy is in traefik-dynamic/)
└── traefik-dynamic/              real dir (not the NAS one — divergence risk, cleaned up in Phase 4)
```
Key insight: docker compose auto-substitutes `${VAR}` from `.env` in the LAUNCH DIRECTORY. `~/stack/` is the launch dir. `.env` sits there as a real file (never on NAS). Compose file symlinks to NAS so file-edits from any client take effect. Split must preserve this pattern.

**Symlinks / junctions on Windows side:** none. Confirmed via `find -type l` and `dir /AL /S`.

**Couplings cortex → magiq root (three, all in `/mnt/shared/claudia/magiq/cortex/docker-compose.yml`):**
1. `env_file: /mnt/shared/claudia/magiq/.env` on `tower` and `mcp-azure-devops` (line refs from grep).
2. `build.context: /mnt/shared/claudia/magiq/mcp/azure-devops` on `mcp-azure-devops` (line 305).
3. `build.context: /mnt/shared/claudia/magiq` + `volumes: /mnt/shared/claudia/magiq:/app` on `tower` (lines 497, 505).
4. `volumes: /mnt/shared/claudia/magiq/homepage-config:/app/config` on `homepage` (line 269) — homepage-config moves in split.
5. `volumes: /mnt/shared/claudia/magiq/cortex/traefik-dynamic:/etc/traefik/dynamic:ro` on `traefik` (line 589) — path changes in split.

**Couplings magiq → cortex:** none. `grep -r cortex projects/` returns nothing.

**Setup documentation currently in magiq that belongs to cortex:**
- `AI-X1-Pro-Setup-Guide.md` (124 KB) — Stages 0–14 (hardware, OS, Docker, NAS), Stage 15.1–15.2 (Hermes install), Stage 22 (secrets extraction, `~/stack/.env` pattern).
- `hermes-integration.md` — cortex-side install content mixed with AIOS-side consumer content.
- `docs/superpowers/specs/2026-08-07-iis-traefik-file-provider.md` — cortex file-provider pattern.
- `docs/superpowers/specs/2026-07-03-tower-cortex-deployment.md` — hybrid; cortex-side flow moves, magiq-tower side stays.
- Cortex-tagged entries in `decisions/log.md`.

Setup content that stays in magiq: `SETUP.md` (AIOS setup), Stage 15.3b/15.4 (Claudia skill install, `SOUL.md`), consumer-side hermes docs.

## 5. Target architecture

### 5.1 Repo layout

All three repos live **on the NAS** as sibling working trees. Dev machines mount NAS as `Z:\` via CIFS. Cortex box mounts NAS at `/mnt/shared/`. Everyone edits the same files. `.git/` directories live on NAS — a git commit from any client updates the same history.

Git remotes (independent per repo, optional):
- `cortex` — `origin` = `git@github.com:cramone/cortex.git`
- `magiq` — TBD (github, ADO, or none — outside this spec's scope)
- `claudette` — TBD

Git remotes are for versioning/backup/collab only. **Deploy trigger is `cortex-sync`, not git push** (see §5.4).

| NAS path                          | Dev-machine mount   | Purpose                                    |
|-----------------------------------|---------------------|--------------------------------------------|
| `/mnt/shared/claudia/magiq/`      | `Z:\claudia\magiq\` | AIOS repo (git unchanged)                  |
| `/mnt/shared/cortex/`             | `Z:\cortex\`        | NEW sibling repo (git origin = GitHub)     |
| `/mnt/shared/claudette/`          | `Z:\claudette\`     | future sibling context                     |

**`/mnt/shared/claudia/magiq/` — AIOS repo (post-split):**
```
├── docker-compose.yml           NEW — tower + mcp-azure-devops only
├── .env                         magiq-owned; existing NAS-resident model unchanged
├── projects/
│   └── magiq-media/
│       └── traefik/             NEW convention — per-project routes
│           └── *.yml
├── traefik/                     OPTIONAL — magiq-wide routes
│   └── *.yml
├── homepage/                    OPTIONAL — per-context homepage additions
│   └── services.yaml            appended into cortex homepage services.yaml on sync
├── AI-X1-Pro-Setup-Guide.md     trimmed; cortex Stages replaced with breadcrumbs
├── hermes-integration.md        consumer-side only; install-side moved
├── CORTEX-MOVED.md              breadcrumb at magiq root (kept one release cycle)
├── tower/                       tower/Dockerfile still here; deploy-cortex.sh DELETED (obsolete post-sync)
└── (cortex/ folder deleted entirely in Phase 5)
```

**`/mnt/shared/cortex/` — NEW cortex repo:**
```
├── docker-compose.yml           pure infra — no tower, no mcp-ado
├── traefik-dynamic/
│   ├── _cortex/                 cortex-owned routes
│   │   ├── hermes.yml
│   │   └── iis-tenants.yml
│   ├── magiq/                   populated by cortex-sync from magiq's traefik/**
│   └── claudette/               (future, same pattern)
├── homepage-config/             moved from magiq (homepage container is cortex-infra)
│   ├── settings.yaml            cortex-owned
│   ├── bookmarks.yaml           cortex-owned
│   └── services.yaml            regenerated by cortex-sync = base + each context's homepage/services.yaml
├── homepage-config-src/         cortex's own homepage source (before context-merge)
│   └── services.yaml            cortex-owned base, merged with context contributions
├── .env.example                 template; real values in ~/stack/.env cortex-box-local
├── sync-contexts.sh             installed to /usr/local/bin/cortex-sync on cortex box
├── cron/cortex-sync.cron        installed to /etc/cron.d/cortex-sync (5min poll)
├── README.md                    repo purpose, quick-start
├── decisions/log.md             cortex-tagged decisions lifted from magiq
├── .gitignore                   excludes .env (real secrets never in git)
└── docs/
    ├── setup/
    │   ├── 01-hardware-and-os.md          from AI-X1 Stages 0-9
    │   ├── 02-docker-stack.md             from AI-X1 Stage 10 (10.1-10.4)
    │   ├── 03-openwebui-netdata-cockpit.md  from AI-X1 10.5-10.7
    │   ├── 04-split-dns-tailnet.md        from AI-X1 10.8
    │   ├── 05-benchmarks-v1-baseline.md   from AI-X1 11-13
    │   ├── 06-shared-storage-ds923.md     from AI-X1 14
    │   ├── 07-hermes-install.md           from AI-X1 15.1-15.2 + install-side of hermes-integration.md
    │   └── 22-secrets-local-env.md        from AI-X1 Stage 22 + .env.example commentary + ~/stack/ layout
    ├── patterns/
    │   ├── traefik-file-provider.md       from specs/2026-08-07-iis-traefik-file-provider.md
    │   └── tower-deploy-flow.md           cortex side of specs/2026-07-03-tower-cortex-deployment.md
    ├── deploy-topology.md                 NEW — NAS-as-truth, trigger model, cortex-sync flow
    ├── adding-a-context.md                NEW — wiring a sibling repo (traefik/, homepage/, compose)
    └── known-gotchas.md                   from AI-X1 "Known Gotchas"
```

### 5.2 Deploy topology

```
Chase's dev machines (Windows + others on tailnet)
        │
        │ edit + git commit + git push (versioning only, not deploy)
        ▼
NAS (/mnt/shared/…)  ─── working trees + .git/ live here ────
├── claudia/magiq/                                            │
├── cortex/                                                   │
└── claudette/                                                │
        ▲                                                     │
        │  CIFS mount                                         │
        │                                                     │
Cortex box:                                                   │
├── /mnt/shared/                    ← NAS mount               │
├── ~/stack/                         cortex-box-local real dir
│   ├── .env                         cortex secrets (chmod 600, NEVER on NAS)
│   ├── docker-compose.yml    →      /mnt/shared/cortex/docker-compose.yml (symlink)
│   ├── traefik-dynamic       →      /mnt/shared/cortex/traefik-dynamic (symlink)
│   ├── homepage-config       →      /mnt/shared/cortex/homepage-config (symlink)
│   └── logs/                        cortex-sync execution logs
├── /usr/local/bin/cortex-sync       deploy trigger — reads NAS, applies
└── /etc/cron.d/cortex-sync          `*/5 * * * * chase cortex-sync all` (idempotent poll)
```

**Deploy invocation (any of these, they compose):**
- **Manual (M):** `ssh cortex cortex-sync <context|all>` — Chase runs after making changes he wants immediate.
- **Cron (C):** every 5 minutes, cortex box auto-runs `cortex-sync all`. Catches anything Chase forgot to trigger manually. Idempotent — rsync + `docker compose up -d` = no-op when nothing changed.
- (Optional future: webhook receiver for instant post-push deploy — not in scope.)

### 5.3 Contracts between cortex and contexts

Cortex publishes contracts, contexts consume:

1. **Docker network `cortex_edge`** — created manually via `docker network create cortex_edge` (Phase 2). Both cortex compose and each context compose reference it as `external: true`. Neither owns network lifecycle. `docker compose down` on either stack does NOT tear down the network — cross-stack traffic survives restarts.
2. **Traefik file-provider directory** — cortex traefik watches `/etc/traefik/dynamic` (bind-mounted from `/mnt/shared/cortex/traefik-dynamic/`) recursively with `--providers.file.watch=true`. `_cortex/` subdir = cortex-owned routes. `{context}/` subdirs = written by `cortex-sync` from each context's `traefik/**/*.yml`.
3. **Named middlewares** — cortex-defined middlewares (`authentik-fwd`, etc.) referenced by name from any context's YAML. Registry in `cortex/traefik-dynamic/README.md`.
4. **Homepage tiles** — contexts drop tiles into their own `homepage/services.yaml`. `cortex-sync` regenerates `cortex/homepage-config/services.yaml` = `homepage-config-src/services.yaml` (cortex base) + each context's file appended under a context-named group. Homepage container reloads on file change (built-in behavior of gethomepage/homepage).

Contexts must honor:
- Their compose (if any) joins the `cortex_edge` external network.
- Traefik routes live under `traefik/**/*.yml` at any depth in their repo (glob).
- Homepage tiles (optional) live at `homepage/services.yaml`.
- They own their own `.env`. Cortex does not read context env files.
- Router names auto-prefixed with `{context}-` by `cortex-sync` to prevent collision (see §5.4).

### 5.4 Sync mechanism

**Trigger:** invocation of `/usr/local/bin/cortex-sync`. Two invocation paths (M+C):
- Manual: `ssh cortex cortex-sync <context|all>` from Chase's dev machine.
- Cron: `/etc/cron.d/cortex-sync` runs `cortex-sync all` every 5 minutes.

Both paths run the SAME script. Fully idempotent. Concurrent invocations serialized via `flock` on `/var/lock/cortex-sync.lock`.

**`/usr/local/bin/cortex-sync [context|all]`** behavior:

```
Args:
  cortex-sync magiq              # sync one context
  cortex-sync all                # sync cortex-self + every context in /mnt/shared/cortex/contexts.yaml
  cortex-sync --dry-run <ctx>    # rsync -n + lint, no compose invocation
  cortex-sync --check-installed  # verify /usr/local/bin/cortex-sync matches /mnt/shared/cortex/sync-contexts.sh
```

Steps per context:
1. Resolve paths from `/mnt/shared/cortex/contexts.yaml`:
   - `CORTEX_ROOT=/mnt/shared/cortex`
   - `CONTEXT_ROOT` = value of `path` for the requested `name` in `contexts.yaml`. Hard-fail if name absent.
2. `mountpoint -q /mnt/shared` — fail fast if NAS unmounted.
3. **Traefik routes:** `rsync -a --delete $CONTEXT_ROOT/**/traefik/*.yml → $CORTEX_ROOT/traefik-dynamic/$context/`, preserving subpath with `_` separator (e.g. `projects/magiq-media/traefik/media-api.yml` → `traefik-dynamic/magiq/projects_magiq-media_media-api.yml`).
4. **Router-name namespace:** pass over each `$context/*.yml`; prefix router names with `$context-` if not already prefixed. Hard-fail if any post-prefix router name still collides with another context's.
5. **Homepage tiles:** if `$CONTEXT_ROOT/homepage/services.yaml` exists, append under a group named after `$context` into the regenerated `$CORTEX_ROOT/homepage-config/services.yaml` (rebuild = `homepage-config-src/services.yaml` + each context's contribution).
6. **Context compose:** if `$CONTEXT_ROOT/docker-compose.yml` exists, run `docker compose -f "$CONTEXT_ROOT/docker-compose.yml" up -d --remove-orphans`.
7. Log to `~/stack/logs/sync-$context-<ts>.log`.

Cortex-self sync (`cortex-sync cortex` OR triggered by `all`):
- Skips step 3 (`_cortex/` files ship in cortex repo already).
- Skips step 4 (cortex routes not auto-prefixed).
- Skips step 5.
- Step 6: `cd ~/stack && docker compose up -d` — launch from `~/stack/` so auto-substitution picks up local `.env`.

**`all` mode order:** read context list from `/mnt/shared/cortex/contexts.yaml`. Iterate cortex-self first (base infra), then each context in `contexts.yaml` order. Ensures `cortex_edge` + traefik + homepage in place before contexts attach.

**Context registry (`/mnt/shared/cortex/contexts.yaml`):** required. Each context entry has `name` (short slug used for `traefik-dynamic/<name>/` subdir + router prefix) and `path` (NAS working-tree root). Cortex-sync fails hard if `cortex-sync <name>` invoked with a name not in the registry (prevents typos writing arbitrary dirs). Adding a context = edit registry, `cortex-sync <name>`, verify.

**Log rotation:** `logrotate` config at `/etc/logrotate.d/cortex-sync` — daily, 30-day retention, compress.

### 5.5 Environment files across contexts

Two patterns coexist by design. **`cortex-sync` never touches `.env` files** — no copy, no move, no read. Docker Compose handles env resolution per-context, independently.

**Cortex secrets** (mysql root, mssql sa, seq admin, authentik, cifs, cloudflare, etc.):
- Live at `~/stack/.env` on cortex box. Real file, chmod 600, **never on NAS**. Stage 22 constraint.
- Cortex compose launched from `~/stack/` (`cd ~/stack && docker compose up -d`). Docker auto-substitutes `${VAR}` from `~/stack/.env` (launch dir = `~/stack/`).
- Compose file symlinks to NAS (`~/stack/docker-compose.yml` → `/mnt/shared/cortex/docker-compose.yml`), so file-content edits from any dev client take effect, but the `.env` used is the local one.
- `cortex-sync cortex` uses this exact pattern (§5.4 cortex-self path).

**Magiq secrets** (ADO_PAT, GITHUB_TOKEN, ANTHROPIC_API_KEY, NOTION_*, CLAUDIA_BRIDGE_URL, etc.):
- Live at `/mnt/shared/claudia/magiq/.env` on NAS. Existing model — Chase accepts these on NAS since they're workspace-accessible.
- Magiq services declare `env_file: ./.env` — Docker resolves relative to compose file location = `/mnt/shared/claudia/magiq/.env`.
- `cortex-sync magiq` runs `docker compose -f /mnt/shared/claudia/magiq/docker-compose.yml up -d`. Docker's project dir = compose parent, so any `${VAR}` auto-sub reads the same NAS `.env`.
- No launch-dir gymnastics needed because magiq accepts NAS-resident `.env`.

**Claudette / future contexts:**
- Default: follow magiq pattern (`.env` at context NAS root, `env_file: ./.env`).
- If a context needs cortex-box-local secrets (some token that must not touch NAS), adopt cortex pattern: create a `~/{context}-launch/` real dir with local `.env` + symlink to NAS compose file, launch from there. Document in `cortex/docs/adding-a-context.md`.

**What happens on sync:**
| Operation                | Cortex `.env`  | Magiq `.env`         | Context `.env`         |
|--------------------------|----------------|----------------------|------------------------|
| Location                 | `~/stack/.env` | NAS                  | NAS (default) or local |
| Touched by `cortex-sync` | never          | never                | never                  |
| Read by Docker at up     | auto-sub       | `env_file` + auto-sub | `env_file` + auto-sub  |
| Launch dir               | `~/stack/`     | context NAS root     | context NAS root       |

If a `.env` file goes missing, `docker compose` fails at that context's `up -d` step, `cortex-sync` exits non-zero, log entry visible in `~/stack/logs/sync-<ctx>-*.log`. Cron alert fires (see §8).

### 5.6 Rollback path per phase

- Phases 0–1: revert commit; nothing on cortex box changed yet.
- Phase 2: `cortex_edge` network created manually + attached to running containers. Rollback = detach from compose, `docker network rm cortex_edge`, `docker compose up -d --remove-orphans`.
- Phases 3–4: `git tag pre-cortex-split` on both repos before cutting; `git reset --hard pre-cortex-split && cortex-sync all` restores.
- Phase 5: only `magiq/cortex/` subfolder deleted. NAS stays. Rollback = `git revert` the delete commit + `cortex-sync all`.

## 6. Cutover plan

**Prerequisites (verify before Phase 0):**
- Chase's dev machine has `~/.ssh/config` `Host cortex` entry reaching cortex box on tailnet.
- NAS mounted read/write on cortex box at `/mnt/shared/` (existing, via `/etc/fstab`).
- Chase can `git commit` from Windows against `Z:\claudia\magiq\.git` (existing).
- GitHub repo `cramone/cortex` created (done 2026-08-24).

### Phase 0 — prep and doc extraction (no service impact)

- **0a.** On dev machine: `mkdir Z:\cortex` (creates `/mnt/shared/cortex/`). `cd /d Z:\cortex && git init && git remote add origin git@github.com:cramone/cortex.git`.
- **0b.** Copy `Z:\claudia\magiq\cortex\*` into `Z:\cortex\`.
- **0b-audit.** Verify traefik flags in the copied compose already use `--providers.file.directory=/etc/traefik/dynamic --providers.file.watch=true` (confirmed present at lines 565–566 as of 2026-08-24). Recursive + watch mode. No change needed for `_cortex/` subdir move.
- **0b-bis.** **Strip `tower` and `mcp-azure-devops` service blocks from `Z:\cortex\docker-compose.yml`.** Also strip any top-level `depends_on` chains that referenced them. Validate: `docker compose -f docker-compose.yml config` passes.
- **0b-ter.** **Reorganize traefik routes into `_cortex/` subdir:** `mkdir Z:\cortex\traefik-dynamic\_cortex && move hermes.yml + iis-tenants.yml into it`. Since traefik flag is directory-recursive, no compose change needed for this restructure.
- **0b-quater.** **COPY `homepage-config/` from magiq into cortex (do NOT delete magiq copy yet — live homepage container is still bind-mounted against it until Phase 4).** Update cortex-new compose paths:
  - On dev machine: `xcopy /E /I Z:\claudia\magiq\homepage-config Z:\cortex\homepage-config` (Windows) — file COPY, not move. Live container keeps working against `/mnt/shared/claudia/magiq/homepage-config`.
  - Establish base/generated split inside cortex: `mkdir Z:\cortex\homepage-config-src && move Z:\cortex\homepage-config\services.yaml Z:\cortex\homepage-config-src\services.yaml`. `settings.yaml` and `bookmarks.yaml` remain in `homepage-config/` (cortex-owned, not regenerated). First `cortex-sync` run rebuilds `homepage-config/services.yaml` from src + contexts.
  - Edit `Z:\cortex\docker-compose.yml` (the NEW cortex compose, not live): change `/mnt/shared/claudia/magiq/homepage-config:/app/config` → `/mnt/shared/cortex/homepage-config:/app/config`.
  - Also edit the traefik dynamic mount in the NEW cortex compose: `/mnt/shared/claudia/magiq/cortex/traefik-dynamic:/etc/traefik/dynamic:ro` → `/mnt/shared/cortex/traefik-dynamic:/etc/traefik/dynamic:ro`.
  - Magiq copy of `homepage-config/` stays git-tracked in magiq repo until Phase 5a (`git rm -r homepage-config`). During Phases 1-4, both copies exist on disk — divergence risk is low since edits to homepage happen through the cortex `homepage-config-src/` + context `homepage/services.yaml` model from now on. Add a note to the magiq copy: `Z:\claudia\magiq\homepage-config\MOVED.md` warning "edits to this dir don't apply post-Phase-4 — edit /mnt/shared/cortex/homepage-config-src or your context's homepage/services.yaml".
  - Commits: one in cortex repo (new dir added, compose paths updated), one in magiq repo (MOVED.md added). Magiq git rm deferred to Phase 5a.
- **0c.** Doc migration (touches BOTH repos):
  - Create `cortex/docs/` structure per §5.1.
  - Extract cortex-owned sections from `magiq/AI-X1-Pro-Setup-Guide.md` into `cortex/docs/setup/*.md`. In magiq, replace each extracted section with `> Moved to cortex/docs/setup/<file>.md as of 2026-08-24`.
  - Extract install-side of `magiq/hermes-integration.md` into `cortex/docs/setup/07-hermes-install.md`. Leave breadcrumb line at extraction point.
  - MOVE `magiq/docs/superpowers/specs/2026-08-07-iis-traefik-file-provider.md` → `cortex/docs/patterns/traefik-file-provider.md`. Leave stub file at old magiq path with single line: `> Moved to cortex/docs/patterns/traefik-file-provider.md (2026-08-24)`. Stub deleted in Phase 5f.
  - Split `magiq/docs/superpowers/specs/2026-07-03-tower-cortex-deployment.md`: cortex-side flow → `cortex/docs/patterns/tower-deploy-flow.md`. Magiq/tower side stays in original file, trimmed. Add note at top of trimmed file: `> Cortex-side flow moved to /mnt/shared/cortex/docs/patterns/tower-deploy-flow.md`.
  - Lift cortex-tagged entries from `magiq/decisions/log.md` into `cortex/decisions/log.md`. Leave one-line breadcrumb per moved entry in magiq log pointing at cortex log.
- **0d.** (Merged into 0c above — each stripped/moved artifact leaves a breadcrumb inline.)
- **0e.** Author artifacts in `Z:\cortex\`:
  - `sync-contexts.sh` (with all §5.4 behavior including `--dry-run`, `--check-installed`, `flock`, subpath preservation, router prefix, homepage merge, log rotation-friendly output). Reads context registry from `contexts.yaml` (below).
  - `contexts.yaml` (context registry — top-level list mapping context name → NAS path). Initial content:
    ```yaml
    contexts:
      - name: magiq
        path: /mnt/shared/claudia/magiq
      # - name: claudette
      #   path: /mnt/shared/claudette
    ```
    Cortex not listed — it's implicit (self). `cortex-sync all` iterates this list plus cortex-self. Adding a new context = one entry here + `cortex-sync <name>`.
  - `cron/cortex-sync.cron` (5-minute schedule).
  - `README.md` (quick-start).
  - `docs/deploy-topology.md`, `docs/adding-a-context.md`.
  - `.gitignore` covering:
    - `.env` (real secrets, chmod 600, cortex-box-local — never in git)
    - `logs/` (runtime output)
    - `traefik-dynamic/*/` (context-generated dirs — output of `cortex-sync`, don't commit magiq's changes indirectly)
    - `!traefik-dynamic/_cortex/` (explicit un-ignore for cortex-owned routes — these ARE git-tracked)
    - `homepage-config/services.yaml` (generated at every sync; commit `homepage-config-src/services.yaml` instead)
    - `!homepage-config/settings.yaml`, `!homepage-config/bookmarks.yaml` (cortex-owned, hand-edited)
- **0f.** Commits (two repos, close in time):
  - Cortex repo (`Z:\cortex\`): initial commit containing everything from 0a–0e. `git push -u origin main` (GitHub `cramone/cortex`).
  - Magiq repo (`Z:\claudia\magiq\`): commit containing all breadcrumb stubs from 0c + `homepage-config/MOVED.md` from 0b-quater + trimmed setup docs. Push to whatever remote magiq uses (or just commit locally if no remote yet — decision deferred per §9).
- **0g.** On cortex box (via SSH): install `cortex-sync` script ONLY (cron install deferred to Phase 4d — running cron during cutover would race with manual steps in Phases 2-4).
  - `sudo cp /mnt/shared/cortex/sync-contexts.sh /usr/local/bin/cortex-sync && sudo chmod +x /usr/local/bin/cortex-sync`.
  - Do NOT install `/etc/cron.d/cortex-sync` yet.
  - Test: `cortex-sync --dry-run cortex` — should exit 0 with no filesystem or docker changes.

### Phase 1 — extract magiq container definitions (no cutover yet)

- **1a.** Author `Z:\claudia\magiq\docker-compose.yml`. Per-service build context (they differ):
  - `tower`: `build: { context: ., dockerfile: tower/Dockerfile }`, `env_file: ./.env`, `volumes: [ ".:/app" ]`. On cortex box `.` resolves to `/mnt/shared/claudia/magiq/`, matching existing bind-mount.
  - `mcp-azure-devops`: `build: { context: ./mcp/azure-devops, dockerfile: Dockerfile.gateway }`, `env_file: ./.env`.
  - Both attach to `networks: [cortex_edge]`; top-level `networks: { cortex_edge: { external: true, name: cortex_edge } }`.
  - Copy all `labels:` traefik.* blocks verbatim from live cortex compose so routes stay identical.
- **1b.** Validate on dev machine: `docker compose -f Z:\claudia\magiq\docker-compose.yml config`. No `up` yet.

### Phase 2 — create `cortex_edge` network + prepare live cortex

- **2a.** On cortex box: `docker network create cortex_edge`. Verify: `docker network inspect cortex_edge`.
- **2b.** Edit LIVE `/mnt/shared/claudia/magiq/cortex/docker-compose.yml` (still the running compose file on the NAS). Add top-level `networks: { cortex_edge: { external: true, name: cortex_edge } }`. Attach `tower` and `mcp-azure-devops` services to `networks: [cortex_edge]` in addition to existing default network.
- **2c.** `cd ~/stack && docker compose up -d` on cortex box. **Expect brief container recreate** — tower and mcp-ado restart (~5s each) since their network set changed. Verify: `docker network inspect cortex_edge` shows both containers.

### Phase 3 — cutover magiq containers to magiq compose

- **3a.** No bare repo needed. On cortex box: `cortex-sync magiq` runs the new magiq compose from `/mnt/shared/claudia/magiq/docker-compose.yml`. This starts NEW containers under the `magiq` compose project (`magiq-tower-1`, `magiq-mcp-azure-devops-1`) attached to `cortex_edge`.
- **3b.** **Immediately after 3a**, remove `tower` and `mcp-azure-devops` service blocks from LIVE `/mnt/shared/claudia/magiq/cortex/docker-compose.yml`. Run `cd ~/stack && docker compose up -d --remove-orphans`. Old `stack-tower-1` + `stack-mcp-azure-devops-1` stop.
  - **Router-label overlap window:** between 3a and 3b, both `stack-tower-1` and `magiq-tower-1` declare `Host(tower.ramonedevelopment.com)`. Traefik logs duplicate-router warning and routes to whichever it discovered first. Expect ~30-60s inconsistency. Do 3a and 3b in same session, back-to-back.
- **3c.** Verify: `docker ps` shows only `magiq-*` variants (no `stack-tower-1`). Routes resolve (`curl -kI https://tower.ramonedevelopment.com`, `curl -kI https://mcp-ado.ramonedevelopment.com`). Sync log at `~/stack/logs/sync-magiq-*.log` shows no errors. Traefik logs no duplicate-router warnings.

### Phase 4 — cutover cortex working tree

Goal: switch `~/stack/docker-compose.yml` symlink from old NAS path to new NAS path, and update the `traefik-dynamic` + `homepage-config` symlinks to match.

- **4a.** On cortex box, prepare new symlinks WITHOUT breaking live:
  ```
  cd ~/stack
  # New symlinks pointing at cortex repo — created alongside current live symlink
  ln -sfn /mnt/shared/cortex/traefik-dynamic traefik-dynamic-new
  ln -sfn /mnt/shared/cortex/homepage-config homepage-config-new
  ```
  Verify: `ls -la traefik-dynamic-new` resolves cleanly.
- **4b.** Atomic switch — run all 4 steps as a single shell block (no user pause between). Cron is not yet installed (deferred to 4d), so no reconcile race. Chase's own sessions must not run `cortex-sync` mid-switch.
  ```bash
  cd ~/stack && \
    ln -sfn /mnt/shared/cortex/docker-compose.yml docker-compose.yml && \
    rm -rf traefik-dynamic && mv traefik-dynamic-new traefik-dynamic && \
    { rm -rf homepage-config 2>/dev/null; true; } && mv homepage-config-new homepage-config && \
    docker compose up -d
  ```
  Notes on each step:
  1. Flip compose file symlink from old (`/mnt/shared/claudia/magiq/cortex/docker-compose.yml`) to new (`/mnt/shared/cortex/docker-compose.yml`). No container effect until step 4.
  2. `rm -rf traefik-dynamic` removes the **real cruft dir** on cortex box (confirmed unused per §4 audit — live traefik container bind-mounts `/mnt/shared/claudia/magiq/cortex/traefik-dynamic` directly, not `~/stack/traefik-dynamic`). `mv traefik-dynamic-new` installs the new symlink.
  3. `homepage-config` at `~/stack/` may not exist pre-Phase-4 (no cruft observed) — `rm -rf ... 2>/dev/null; true` handles both cases. Install new symlink.
  4. `docker compose up -d` reads NEW compose file, sees changed volume paths, reconciles.
     - Traefik container recreates (bind-mount source changed under `/etc/traefik/dynamic`). ~10s of 502s during recreate. Largest visible impact of the split.
     - Homepage container recreates (bind-mount source changed). ~5s downtime for `home.ramonedevelopment.com`.
     - `cortex_edge` survives (external, created in Phase 2, not owned by compose). Magiq containers stay attached — no downtime for tower/mcp-ado.
- **4c.** Verify:
  - `docker network inspect cortex_edge` — magiq containers still attached.
  - `docker ps` — all cortex services running (traefik freshly restarted).
  - Routes: `curl -kI https://home.ramonedevelopment.com`, `hermes.ramonedevelopment.com`, `tower.ramonedevelopment.com` — all 200/302 through authentik.
  - `readlink ~/stack/docker-compose.yml` → `/mnt/shared/cortex/docker-compose.yml`.
  - `readlink ~/stack/traefik-dynamic` → `/mnt/shared/cortex/traefik-dynamic`.
- **4d.** Reconcile any magiq compose edits made between Phases 1 and 4: `ssh cortex cortex-sync magiq`. Should be no-op if magiq compose unchanged since Phase 3. Then confirm `cortex-sync all` end-to-end: `ssh cortex cortex-sync all`. Expect:
  - Cortex compose reconcile: no-op.
  - Magiq compose reconcile: no-op.
  - Homepage regen: **first real write** to `/mnt/shared/cortex/homepage-config/services.yaml` (Phase 0e excluded it as generated, Phase 0b-quater moved services.yaml into `homepage-config-src/`). Homepage container reloads via built-in watcher — brief tile-refresh flicker, no downtime.
  - Log at `~/stack/logs/sync-*.log`.
  Then install cron (deferred from Phase 0g):
  - `sudo cp /mnt/shared/cortex/cron/cortex-sync.cron /etc/cron.d/cortex-sync && sudo chmod 644 /etc/cron.d/cortex-sync`.
  - Verify: `sudo systemctl status cron`, `cat /etc/cron.d/cortex-sync`.
  - Wait 6 minutes, confirm fresh sync log appeared at `~/stack/logs/sync-*-<recent-ts>.log`.
- **4e.** Cleanup: `rm ~/stack/docker-compose.yml.bak-presymlink` (Stage 22 leftover). `rm ~/stack/iis-tenants.yml` (leftover — real copy is in `~/stack/traefik-dynamic/_cortex/`).

### Phase 5 — retire the magiq/cortex/ subfolder (only after ≥7 days stable)

**NAS itself NOT retired.** Only the `cortex/` subfolder inside magiq goes away.

- **5a.** Delete from magiq repo (single commit):
  - `Z:\claudia\magiq\cortex\` — entire folder (docker-compose.yml, traefik-dynamic, .env.example).
  - `Z:\claudia\magiq\homepage-config\` — the copy left behind by Phase 0b-quater (live homepage now bind-mounts `/mnt/shared/cortex/homepage-config` since Phase 4b).
  - `Z:\claudia\magiq\tower\deploy-cortex.sh` — obsolete (workflow is now `cortex-sync`).
  - Update `scripts/tower-autosync.sh` + `scripts/tower-deploy-check.sh` to drop references to `deploy-cortex.sh`; keep any useful parts (deployed-tag tracking) under renamed scripts.
  - Add `Z:\claudia\magiq\CORTEX-MOVED.md` at magiq ROOT pointing to `/mnt/shared/cortex/` and the new deploy trigger (`ssh cortex cortex-sync`).
- **5b.** Grep across cortex box (`~/`, `/etc/`, `/srv/`) AND both repos for the deprecated paths:
  - `/mnt/shared/claudia/magiq/cortex`
  - `/mnt/shared/claudia/magiq/homepage-config`
  - `deploy-cortex.sh`
  Expect zero live references outside migration breadcrumbs and old backups (e.g. `docker-compose.yml.bak-presymlink` already deleted in Phase 4e). Resolve any hits before proceeding.
- **5c.** Verify no dangling symlinks: `find ~/stack -type l -not -exec test -e {} \; -print` should return nothing (all symlinks resolve).
- **5d.** Update `magiq/CLAUDE.md` — new section: "Cortex is a sibling repo at `Z:\cortex\` (`/mnt/shared/cortex/`), no longer part of this repo. Deploy via `ssh cortex cortex-sync <context>` or wait 5min for cron." Update `aios.config.md` if it references cortex. Update `magiq/README.md` deploy instructions.
- **5e.** Record ADR in `magiq/references/adrs/adr-NNN-cortex-split.md` and cross-link `cortex/decisions/log.md`.
- **5f.** After one further release cycle, delete `CORTEX-MOVED.md` from magiq (git history preserves the pointer).

### Symlink audit checkpoints

- **Before Phase 0:** `find ~/stack -maxdepth 2 -type l` on cortex box. Baseline: only `~/stack/docker-compose.yml` → `/mnt/shared/claudia/magiq/cortex/docker-compose.yml`.
- **After Phase 4:** rerun. Expected new state:
  - `~/stack/docker-compose.yml` → `/mnt/shared/cortex/docker-compose.yml`
  - `~/stack/traefik-dynamic` → `/mnt/shared/cortex/traefik-dynamic`
  - `~/stack/homepage-config` → `/mnt/shared/cortex/homepage-config`
- **After Phase 5:** confirm all `~/stack` symlinks still resolve (source dirs still exist on NAS).
- **On dev machine:** `find /z/claudia /z/cortex -type l` before + after each phase. Expected: zero.

## 7. Documentation deliverables (non-negotiable)

Every artifact below ships alongside the code change. Missing docs block the phase from being marked complete.

**Cortex repo:**
- `README.md` — purpose, quick-start (`ssh cortex cortex-sync all` after any change), deploy topology, contract list, add-a-context, rollback.
- `sync-contexts.sh` — header comment: trigger paths (manual + cron), inputs, outputs, side effects, `--dry-run` and `--check-installed` flags.
- `cron/cortex-sync.cron` — comment: cron schedule, install target, how to disable, log location.
- `traefik-dynamic/README.md` — file-provider convention, `_cortex/` vs `{context}/` dirs, middleware registry, router-name auto-prefix rule, YAML template.
- `homepage-config/README.md` — services.yaml regen from `homepage-config-src/services.yaml` + context contributions, do-not-hand-edit warning for generated file, template for context `homepage/services.yaml` snippets.
- `docker-compose.yml` — inline commentary (hermes.yml-style); block header per service group; note `cortex_edge` is external and not owned.
- `docs/deploy-topology.md` — NAS-as-truth model, sibling repo layout, `~/stack/` symlink pattern, `cortex-sync` behavior, cron schedule, log dir, GitHub-as-versioning role.
- `docs/adding-a-context.md` — step-by-step: create dir on NAS, `git init`, optional GitHub remote, add `traefik/*.yml` and/or `homepage/services.yaml` and/or `docker-compose.yml` (joining `cortex_edge`), first `cortex-sync <name>`, verify.
- `docs/setup/*.md` — extracted setup Stages.
- `docs/patterns/*.md` — traefik file-provider pattern, tower deploy flow (cortex side).
- `docs/known-gotchas.md` — router collision diagnostic, sync log location, `--check-installed` drift symptom, NAS unmount handling.

**Magiq repo:**
- `docker-compose.yml` (new) — header explaining: joins `cortex_edge` external network, `env_file: ./.env` = existing NAS `.env` (unchanged model), why tower + mcp-ado live here.
- `projects/{name}/traefik/README.md` — convention, examples, sync note ("this file rsyncs into `cortex/traefik-dynamic/magiq/` on next `cortex-sync magiq`; router name auto-prefixed with `magiq-`").
- `homepage/README.md` (if used) — services.yaml snippet convention, how it merges into cortex homepage-config.
- `CLAUDE.md` — new section: cortex sibling at `Z:\cortex\`, deploy trigger, `cortex_edge` join pattern for new containers.
- `decisions/log.md` — decision entry + ADR pointer.
- `references/adrs/adr-NNN-cortex-split.md` — full ADR.

**Cortex box (documented in cortex repo's `docs/`, not tracked on the box):**
- `~/stack/` layout convention (real dir + symlinks + local `.env`).
- `/usr/local/bin/cortex-sync` install location, re-install command.
- `/etc/cron.d/cortex-sync` install location.
- Log dir `~/stack/logs/`, `logrotate` config `/etc/logrotate.d/cortex-sync`.

**Breadcrumbs at old paths:**
- `Z:\claudia\magiq\CORTEX-MOVED.md` at magiq ROOT (one release cycle, then deleted per 5f).
- Each stripped section in `AI-X1-Pro-Setup-Guide.md` and `hermes-integration.md` gets a `> Moved to cortex/docs/…` line.

## 8. Risks and mitigations

- **`cortex-sync` fails silently.** Mitigation: `set -e`, log to `~/stack/logs/sync-*.log`, cron sends failure via `MAILTO=` or writes to `/var/log/cortex-sync-failures.log` monitored by uptime-kuma (existing infra).
- **Route YAML references a nonexistent middleware.** Mitigation: `watch=true` means traefik logs router-not-loaded warning without crashing. Diagnostic step in `docs/known-gotchas.md`.
- **Two contexts define the same router name.** Mitigation: `cortex-sync` auto-prefixes with `{context}-` and hard-fails on residual collision (impossible unless two contexts share a slug — caught at sync time).
- **Chase edits on NAS but never runs `cortex-sync` and forgets cron exists.** Impact: 5min max lag before cron catches up. If cron itself broken, changes never deploy. Mitigation: cron health-check ping to uptime-kuma every run; alert if silent >15min.
- **NAS unmount on cortex box mid-sync.** Mitigation: `mountpoint -q /mnt/shared` guard at top of `cortex-sync` — fail fast with clear message. `~/stack/docker-compose.yml` symlink also breaks if NAS gone — traefik + everything stops. Alert via uptime-kuma.
- **Cortex box loses `~/stack/.env`.** Existing risk, unchanged. `.env` chmod 600, cortex-box-local, never on NAS or in git. Documented in `docs/setup/22-secrets-local-env.md`. Consider encrypted NAS backup (out of scope).
- **`/usr/local/bin/cortex-sync` drifts from `/mnt/shared/cortex/sync-contexts.sh`.** Mitigation: `cortex-sync --check-installed` diffs the two, warns. Cron runs `--check-installed` daily; alert on drift.
- **Homepage regen wipes hand-edits to generated `services.yaml`.** Mitigation: `homepage-config/services.yaml` header comment "GENERATED — edit `homepage-config-src/services.yaml` or your context's `homepage/services.yaml`". `.gitignore` blocks it from being committed (see Phase 0e).
- **`flock` contention if manual and cron overlap.** `flock -n` returns immediately if locked; manual invocation waits (`flock -w 60`). Documented in `--help`.
- **Phase 4 traefik recreate ~10s.** Schedule Phase 4 in low-usage window. Documented in `docs/deploy-topology.md`.

## 9. Open items for implementation plan

- Homepage-config regeneration format: does gethomepage/homepage support a "generated + append" pattern natively, or does `cortex-sync` need to YAML-merge? Likely straight file rebuild (concat under YAML groups). Confirm.
- ~~`.gitignore` policy for `cortex/homepage-config/services.yaml`~~ → RESOLVED: ignored (generated); `homepage-config-src/services.yaml` tracked. Same rule for `traefik-dynamic/*/` (context-generated dirs ignored, `_cortex/` explicitly un-ignored). See Phase 0e `.gitignore` block.
- Log rotation exact policy (retention, compression).
- Cron user — `chase` (matches `docker compose` group membership) vs root (with `sudo -u chase`).
- Whether to add a systemd path unit as a supplement to cron for near-instant reaction on NAS file writes (CIFS inotify may not fire — needs testing).
- Whether magiq gets its own GitHub remote as part of this work or later.

**Resolved during self-review:**
- ~~rsync filename convention~~ → preserve subpath, `_` separator (§5.4 step 3).
- ~~context compose invocation~~ → yes, `cortex-sync` runs it (§5.4 step 6).
- ~~NAS retirement~~ → NAS NOT retired (§2, §3).
- ~~push transport / bare repos / post-receive hooks~~ → all dropped. Deploy trigger is `cortex-sync` (§5.4).
- ~~cortex-sync install path~~ → `/usr/local/bin/cortex-sync` (§5.4).
- ~~`cortex_edge` ownership~~ → created manually in Phase 2, external in both composes.
- ~~Phase 3 router-overlap window~~ → 30-60s inconsistency, 3a and 3b back-to-back.
- ~~Fate of `deploy-cortex.sh`~~ → deleted entirely (Phase 5a).
- ~~Traefik file-provider flags~~ → already correct (directory + watch), no change needed.
- ~~Cortex `.env` location~~ → stays at cortex-box-local `~/stack/.env`; `~/stack/docker-compose.yml` symlinks to NAS; auto-substitution works when compose launched from `~/stack/`.
- ~~Homepage-config volume path~~ → updated in NEW cortex compose (Phase 0b-quater). Files COPIED not moved — magiq copy remains until Phase 5a to keep live homepage container working during transition.
- ~~Traefik-dynamic volume path~~ → updated to `/mnt/shared/cortex/traefik-dynamic` in same commit (Phase 0b-quater).
- ~~Deploy trigger model~~ → manual (M) `ssh cortex cortex-sync <ctx>` + cron (C) 5-minute poll (§5.4).
- ~~Context registry / discovery~~ → RESOLVED: `contexts.yaml` at cortex repo root, explicit name→path mapping (§5.4).
- ~~`.gitignore` for generated files~~ → RESOLVED: ignore `traefik-dynamic/*/` (allow `_cortex/`), ignore `homepage-config/services.yaml` (keep `homepage-config-src/services.yaml`) (Phase 0e).
- ~~Doc extraction breadcrumbs for fully-moved specs~~ → RESOLVED: leave one-line stub at old magiq path, delete stubs in Phase 5f (Phase 0c).
- ~~Magiq commit in Phase 0~~ → RESOLVED: Phase 0f explicitly commits both repos (Phase 0f).
- ~~Magiq compose edits between Phase 1 and Phase 4~~ → RESOLVED: Phase 4d runs `cortex-sync magiq` before installing cron (Phase 4d).

## 10. Approvals

- Registration model: file drop (git-based), one dir per context in `traefik-dynamic/`; optional `homepage/services.yaml` per context merged into cortex homepage. — Chase, 2026-08-24.
- Repo topology: separate sibling repos at NAS `/mnt/shared/{cortex,claudette}/`, dev mount `Z:\cortex\` / `Z:\claudette\`. — Chase, 2026-08-24.
- Container ownership: tower + mcp-azure-devops move to magiq; cortex stays pure-infra. — Chase, 2026-08-24.
- Documentation coverage per §7. — Chase, 2026-08-24.
- Cutover plan §6, including doc extraction in Phase 0. — Chase, 2026-08-24.
- `homepage-config/` moves from magiq to cortex. — Chase, 2026-08-24.
- NAS stays as source of truth for all repos. — Chase, 2026-08-24.
- GitHub `cramone/cortex` is git origin for cortex repo (versioning only, not deploy trigger). — Chase, 2026-08-24.
- Deploy trigger = `cortex-sync` script, invoked manually via SSH (M) + cron poll every 5 minutes (C). Idempotent. — Chase, 2026-08-24.
- `sync-contexts.sh` installed at `/usr/local/bin/cortex-sync`. — 2026-08-24.
- Router-name auto-prefix with `{context}-`, hard-fail on residual collision. — 2026-08-24.
- `cortex_edge` network created manually in Phase 2, external in both composes. — 2026-08-24.
- Phase 3 sequencing: 3a (magiq up) → 3b (remove old) back-to-back. — 2026-08-24.
- Delete `tower/deploy-cortex.sh` entirely in Phase 5. — 2026-08-24.
- `~/stack/` stays as real dir + symlinks pattern (Stage 22 constraint preserved). — 2026-08-24.
