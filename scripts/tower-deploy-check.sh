#!/usr/bin/env bash
# Reports whether tower/ has changes on origin/main that haven't been
# deployed to Cortex yet. Compares the `deployed-tower` tag (moved by
# tower/deploy-cortex.sh on every successful deploy) against origin/main.
#
# Doesn't need to reach Cortex at all — just fetches tags from GitHub, so
# this can run from Windows, this repo's Cowork mount, or anywhere with a
# clone. Prints nothing and exits 0 if nothing's pending (safe to call from
# an unattended scheduled check).
set -euo pipefail

cd "$(dirname "$0")/.."   # repo root

git fetch origin --tags -q

if ! git rev-parse -q --verify refs/tags/deployed-tower >/dev/null; then
  echo "PENDING: no deployed-tower tag found yet — Tower hasn't been deployed via deploy-cortex.sh, or the tag hasn't reached this clone."
  exit 0
fi

if git diff --quiet deployed-tower origin/main -- tower/; then
  exit 0   # nothing pending
fi

echo "PENDING: tower/ has changes on origin/main not yet deployed to Cortex."
echo
echo "Commits since last deploy:"
git log --oneline deployed-tower..origin/main -- tower/
echo
echo "Deploy with: ssh cortex \"cd /mnt/shared/claudia/magiq && ./tower/deploy-cortex.sh\""
