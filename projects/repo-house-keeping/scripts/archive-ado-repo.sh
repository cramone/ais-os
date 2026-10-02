#!/usr/bin/env bash
# Archive an ADO repo to the local file system: a full mirror (all branches and tags), a verified bundle with a sha256 checksum, and a read-only checkout for browsing.
# Usage: AZURE_DEVOPS_EXT_PAT=... ./scripts/archive-ado-repo.sh <source-key> <org-url> <project> <repo>
#   e.g. ./scripts/archive-ado-repo.sh magiq-vs-ado https://magiq.visualstudio.com <Project> Extensions
# The PAT is read from the environment and sent as an HTTP header, so it never appears in the remote URL or in .git/config.
set -euo pipefail

SOURCE_KEY="${1:?source key (e.g. magiq-vs-ado)}"
ORG_URL="${2:?org url}"
PROJECT="${3:?ADO project name}"
REPO="${4:?repo name}"
: "${AZURE_DEVOPS_EXT_PAT:?set AZURE_DEVOPS_EXT_PAT (Code: Read scope)}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/archive/$SOURCE_KEY/$REPO"
REMOTE="${ORG_URL%/}/$(printf '%s' "$PROJECT" | sed 's/ /%20/g')/_git/$REPO"
AUTH_HEADER="Authorization: Basic $(printf ':%s' "$AZURE_DEVOPS_EXT_PAT" | base64 -w0)"
STAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

[[ -e "$DEST/mirror.git" ]] && { echo "Already archived at $DEST — aborting (refusing to overwrite)."; exit 1; }
mkdir -p "$DEST"

echo "→ Mirror clone $REMOTE"
git -c http.extraHeader="$AUTH_HEADER" clone --mirror "$REMOTE" "$DEST/mirror.git"
git -C "$DEST/mirror.git" remote set-url origin "$REMOTE"   # no credentials stored

echo "→ LFS check"
if git -C "$DEST/mirror.git" grep -q "filter=lfs" $(git -C "$DEST/mirror.git" rev-parse HEAD) -- .gitattributes 2>/dev/null; then
  echo "  ⚠ LFS detected — fetching all LFS objects"
  git -C "$DEST/mirror.git" -c http.extraHeader="$AUTH_HEADER" lfs fetch --all
  LFS=true
else
  LFS=false
fi

echo "→ Bundle + checksum"
git -C "$DEST/mirror.git" bundle create "$DEST/$REPO.bundle" --all
git bundle verify "$DEST/$REPO.bundle" >/dev/null
( cd "$DEST" && sha256sum "$REPO.bundle" > "$REPO.bundle.sha256" )

echo "→ Read-only checkout of default branch"
git clone -q "$DEST/mirror.git" "$DEST/src"
DEFAULT_BRANCH="$(git -C "$DEST/mirror.git" symbolic-ref --short HEAD)"
HEAD_SHA="$(git -C "$DEST/mirror.git" rev-parse HEAD)"
LAST_COMMIT="$(git -C "$DEST/mirror.git" log -1 --format='%cs|%an')"

echo "→ Write manifest"
cat > "$DEST/archive-manifest.txt" <<EOF
source_key=$SOURCE_KEY
source_url=$REMOTE
archived_utc=$STAMP
archived_by=$(git config user.email || whoami)
default_branch=$DEFAULT_BRANCH
head_sha=$HEAD_SHA
last_commit_date=${LAST_COMMIT%%|*}
last_commit_author=${LAST_COMMIT##*|}
branches=$(git -C "$DEST/mirror.git" for-each-ref refs/heads --format='%(refname:short)' | paste -sd, -)
tags=$(git -C "$DEST/mirror.git" for-each-ref refs/tags --format='%(refname:short)' | paste -sd, -)
has_lfs=$LFS
bundle_sha256=$(cut -d' ' -f1 "$DEST/$REPO.bundle.sha256")
EOF

echo "✓ Archived to $DEST"
cat "$DEST/archive-manifest.txt"
