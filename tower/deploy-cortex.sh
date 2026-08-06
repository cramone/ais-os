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
(cd ~/stack && docker compose up -d --build tower)

echo "==> health check"
# Probe INSIDE the container: tower publishes no host port (Traefik-only,
# behind Authentik auth), so the host's localhost:8765 has nothing to hit.
# Retry a few times to allow uvicorn startup.
health_ok=false
for _ in 1 2 3 4 5; do
  if (cd ~/stack && docker compose exec -T tower curl -sf http://localhost:8765/api/health >/dev/null 2>&1); then
    health_ok=true
    break
  fi
  sleep 2
done
if $health_ok; then
  echo "OK"
else
  echo "FAILED — check: docker compose logs tower" >&2
  exit 1
fi

echo "==> tagging deployed commit"
git tag -f deployed-tower
git push -f origin deployed-tower
echo "Tagged deployed-tower @ $(git rev-parse --short HEAD)"
