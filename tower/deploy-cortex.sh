#!/usr/bin/env bash
# Run ON Cortex (not Windows). Pulls latest AIS-OS, rebuilds/restarts the
# Tower container, then moves the `deployed-tower` git tag to mark what's
# actually live — scripts/tower-deploy-check.sh reads this tag to tell you
# whether there are undeployed changes, without needing to reach Cortex.
#
# Usage: ./tower/deploy-cortex.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

echo "==> git pull"
git pull --rebase

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
