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
sleep 2
if curl -sf http://localhost:8765/api/health >/dev/null; then
  echo "OK"
else
  echo "FAILED — check: docker compose logs tower" >&2
  exit 1
fi

echo "==> tagging deployed commit"
git tag -f deployed-tower
git push -f origin deployed-tower
echo "Tagged deployed-tower @ $(git rev-parse --short HEAD)"
