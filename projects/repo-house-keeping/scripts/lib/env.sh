#!/usr/bin/env bash
# Load .env into the current shell (CRLF-safe), then select an ADO org for az CLI / git.
# Usage:  source scripts/lib/env.sh && use_ado_org infoxpert
#         az repos list --org "$ADO_ORG_URL" ...

_HK_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
_HK_ENV="${REPO_HK_ENV_FILE:-$_HK_ROOT/.env}"

if [[ -f "$_HK_ENV" ]]; then
  while IFS='=' read -r k v; do
    [[ -z "$k" || "$k" =~ ^[[:space:]]*# ]] && continue
    k="${k//[[:space:]]/}"; v="${v%$'\r'}"; v="${v%\"}"; v="${v#\"}"
    [[ -z "${!k:-}" ]] && export "$k=$v"     # don't override existing env
  done < "$_HK_ENV"
else
  echo "env.sh: no env file at $_HK_ENV (copy .env.example → .env)" >&2
fi

# use_ado_org <infoxpert|magiqsoftware> — exports ADO_ORG_URL + AZURE_DEVOPS_EXT_PAT (used by az devops and archive-ado-repo.sh)
use_ado_org() {
  local key; key="$(echo "${1:?org key}" | tr '[:lower:]' '[:upper:]')"
  local url_var="ADO_${key}_ORG_URL" pat_var="ADO_${key}_PAT"
  [[ -n "${!pat_var:-}" ]] || { echo "use_ado_org: $pat_var not set" >&2; return 1; }
  export ADO_ORG_URL="${!url_var}" AZURE_DEVOPS_EXT_PAT="${!pat_var}"
  echo "ADO org → $ADO_ORG_URL"
}
