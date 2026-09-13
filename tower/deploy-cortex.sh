#!/usr/bin/env bash
# Run ON Cortex (not Windows). Rebuilds/restarts the Tower container, then
# moves the `deployed-tower` git tag to mark what's actually live —
# scripts/tower-deploy-check.sh reads this tag to tell you whether there are
# undeployed changes, without needing to reach Cortex.
#
# There is deliberately NO `git pull` here. Windows (Z:\claudia\magiq) and
# Cortex (/mnt/shared/claudia/magiq) mount the same DS923 NAS share, and the
# container bind-mounts that share — so a commit made from Windows is already
# on Cortex's disk before this script runs. Git is kept for history and backup
# to GitHub, not as the sync mechanism (decisions/log.md 2026-07-04: "Canonical
# AIS-OS location: single NAS share, not git-sync between clones"; design in
# docs/superpowers/specs/2026-07-03-tower-cortex-deployment.md).
#
# The pull was not merely redundant, it was actively harmful: `pull --rebase`
# aborts on any unstaged change, and a share that several machines and agents
# write to is dirty most of the time. Unrelated work-in-progress under
# projects/ could block a Tower deploy outright.
#
# Usage: ./tower/deploy-cortex.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

# The build takes the working tree, not HEAD, but the tag below names HEAD.
# Uncommitted tower/ changes make the two disagree, so say so rather than let
# `deployed-tower` quietly claim something that was never committed. A warning,
# not a failure — deploying from a dirty tree is a legitimate thing to do when
# you are testing a fix on the real host.
if [ -n "$(git status --porcelain -- tower/)" ]; then
  echo "WARNING: uncommitted changes under tower/ — they WILL be deployed, but" >&2
  echo "         the deployed-tower tag can only point at HEAD:" >&2
  git status --short -- tower/ >&2
fi

echo "==> docker compose up -d --build tower"
# Compose lives in THIS repo, not ~/stack. The cortex split moved tower and
# mcp-azure-devops into magiq's own docker-compose.yml (Phase 1) and removed
# them from the ~/stack compose (Phase 3), so the old `cd ~/stack` here failed
# with "no such service: tower". The running container is `magiq-tower-1`,
# compose project `magiq`, config /mnt/shared/claudia/magiq/docker-compose.yml.
docker compose up -d --build tower

echo "==> health check"
# Probe INSIDE the container: tower publishes no host port (Traefik-only,
# behind Authentik auth), so the host's localhost:8765 has nothing to hit.
# Retry a few times to allow uvicorn startup.
health_ok=false
for _ in 1 2 3 4 5; do
  if docker compose exec -T tower curl -sf http://localhost:8765/api/health >/dev/null 2>&1; then
    health_ok=true
    break
  fi
  sleep 2
done
if $health_ok; then
  echo "OK"
else
  echo "FAILED — check: cd /mnt/shared/claudia/magiq && docker compose logs tower" >&2
  exit 1
fi

echo "==> tagging deployed commit"
git tag -f deployed-tower
git push -f origin deployed-tower
echo "Tagged deployed-tower @ $(git rev-parse --short HEAD)"
