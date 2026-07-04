#!/usr/bin/env bash
# Auto-commits + pushes Tower's own writes on Cortex (interrupts.json,
# decisions/log.md edits, projects/*/notes.md, todos.md, MEMORY.md) so
# Chase's Windows copy picks them up on the next `git pull`.
#
# Run ON CORTEX ONLY, on a timer (see tower-cortex-deployment.md for the
# systemd unit). Do not run this on Windows — Windows is the interactive
# editing copy; Cortex is the live-data publisher.
set -euo pipefail

cd "$(dirname "$0")/.."   # repo root (/opt/ais-os)

git add -A

if git diff --cached --quiet; then
  exit 0   # nothing to commit
fi

git commit -m "tower: auto-sync $(date -u +%Y-%m-%dT%H:%M:%SZ)"
git pull --rebase
git push
