# AIS-OS Portability Plan

**Goal:** Move the AIS-OS folder to any location, machine, or user with minimal config edits.

**Target end state:**
- **Move folder anywhere** → nothing to edit. All internal paths self-locate.
- **New machine / new person** → edit exactly **2 files**: `.env` (paths, secrets, external services) and `aios.config.md` (identity/context).

---

## Problem: two kinds of machine coupling

### Bucket A — internal paths hardcoded in code (8 files)

Every script embeds `C:\Users\chase\OneDrive\Magiq\AIS-OS` or a sibling absolute path instead of deriving its own location. Moving the folder breaks all of them.

| File | Line | Hardcoded value | Fix |
|---|---|---|---|
| `tower/config.py` | 11 | `AIOS_ROOT` default = Chase path | Default to `Path(__file__).resolve().parent.parent` |
| `dashboards/claudia/server.py` | 13-14 | `DASHBOARD_DIR`, `AIOS_ROOT` (`/mnt/c/...`) | Derive both from `Path(__file__).resolve()` |
| `dashboards/claudia/start.sh` | 3-4 | `VENV`, `DIR` (`/mnt/c/...`) | Derive `DIR` from `$BASH_SOURCE`; `VENV` from `$HOME`/env |
| `scripts/auto-scaffold.ps1` | 5, 8 | `$aiosRoot`, `$hermesDataPath` | `$aiosRoot = Split-Path -Parent $PSScriptRoot`; hermes path from env |
| `scripts/register-auto-scaffold-task.ps1` | 5 | `$scriptPath` | Build from `$PSScriptRoot` |
| `tower/create-shortcut.ps1` | 5-6 | `TargetPath`, `WorkingDirectory` | Build from `$PSScriptRoot` |
| `tower/launch.bat` | 3 | `cd /d "C:\...\AIS-OS"` | `cd /d "%~dp0.."` |
| `.mcp.json` | 6 | `D:\mcp\azure-devops-mcp-server\build\index.js` | Externalize — see Bucket C |

**Principle:** internal paths are never config. Each script computes the root from its own file position. Directory layout is fixed inside the repo, so relative-from-self always resolves.

### Bucket B — identity/context baked into prose

`CLAUDE.md` hardcodes the operator ("Chase Ramone"), employer ("Magiq Software"), product ("MAGIQ Documents"), current focus ("magiq-media API, tenant management…"), and Q2 priorities. A new user must hand-edit prose scattered through the file.

Content files under `projects/`, `security-incidents/`, `decisions/` etc. reference `magiq-media`, `Hermes`, etc. — **these are user data, not config. Leave untouched.** Portability = swapping the operator/context, not rewriting their history.

**Fix:** extract the identity/context block into one file, `aios.config.md`. `CLAUDE.md` keeps the operating rules (generic) and references the config file for the "who/what" specifics.

### Bucket C — irreducible external config (`.env` + `.mcp.json`)

Things that genuinely can't self-derive because they point outside the repo or hold secrets. These stay as config, documented in `.env.example`:

- `HERMES` — external Hermes home (default `~/.hermes` if unset)
- MCP server binary path (currently `D:\mcp\...` in `.mcp.json`)
- Secrets: `AZURE_DEVOPS_PAT`, `NOTION_TOKEN`, `ANTHROPIC_API_KEY`, `TOWER_TOKEN`
- `AZURE_DEVOPS_ORG` / `AZURE_DEVOPS_PROJECT`
- `TOWER_PORT`

**Security note:** `.env` and `.mcp.json` are already in `.gitignore` and NOT tracked. Live secrets are local-only, not in git history. Good — no leak. `.env.example` (tracked) stays placeholder-only.

---

## Changes

### 1. `tower/config.py`
Replace hardcoded default with self-derived root:
```python
AIOS_ROOT = Path(os.getenv("AIOS_ROOT") or Path(__file__).resolve().parent.parent)
```
`.env` override still honored; default now portable.

### 2. `dashboards/claudia/server.py`
```python
AIOS_ROOT = Path(os.getenv("AIOS_ROOT") or Path(__file__).resolve().parents[2])
DASHBOARD_DIR = Path(__file__).resolve().parent
HERMES_HOME = Path(os.getenv("HERMES") or (Path.home() / ".hermes"))
```
(`server.py` is at `dashboards/claudia/`, so `parents[2]` = repo root.)

### 3. `dashboards/claudia/start.sh`
```sh
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="${HERMES:-$HOME/.hermes}/hermes-agent/venv"
```

### 4. `scripts/auto-scaffold.ps1` + `register-auto-scaffold-task.ps1`
```powershell
$aiosRoot   = Split-Path -Parent $PSScriptRoot          # scripts/ -> root
$hermesData = $env:HERMES_DATA ?? "/opt/data/.hermes/data/projects"
$scriptPath = Join-Path $PSScriptRoot "auto-scaffold.ps1"
```

### 5. `tower/create-shortcut.ps1` + `tower/launch.bat`
```powershell
$root = Split-Path -Parent $PSScriptRoot
$Shortcut.TargetPath       = Join-Path $PSScriptRoot "launch.bat"
$Shortcut.WorkingDirectory = $root
```
```bat
cd /d "%~dp0.."
```

### 6. `.mcp.json`
Externalize the ADO MCP binary path. Options:
- **6a** — env expansion: `"args": ["${MCP_ADO_SERVER}"]`, set `MCP_ADO_SERVER` in `.env` / shell. (Confirm this Claude Code / runtime supports `${VAR}` in `.mcp.json` args before relying on it.)
- **6b** — vendor the server under the repo (`vendor/azure-devops-mcp/`) and use a relative path. Heavier but fully self-contained.
- Recommend **6a**; document the var in `.env.example`.

### 7. New `aios.config.md` (identity/context extraction)
Single editable block:
```markdown
# AIS-OS Operator Config

operator:      <Name>
role:          <Title / team lead of…>
employer:      <Company>
product:       <Product line>
current_focus: <one line>
priorities:    <bulleted current priorities>
task_tracker:  Azure DevOps
comms:         Outlook + Teams
```
`CLAUDE.md` "Knowledge base" + intro sections replaced with: *"Operator identity and current focus live in `aios.config.md` — read it at session start."*

### 8. `.env.example` update
Add documented placeholders for every irreducible var (Bucket C), grouped: Paths / Secrets / Services.

---

## Verification

1. `python -c "import tower.config as c; print(c.AIOS_ROOT)"` from repo root — prints repo root, no env set.
2. Copy repo to a throwaway path (e.g. `/tmp/aios-test`), run tower + claudia dashboard, confirm both start and resolve paths.
3. Run `pytest` — existing tower tests still pass (they import `tower.config`).
4. Grep for the old absolute string across `*.py *.ps1 *.bat *.sh *.json` → **zero hits**.

## Non-goals

- Rewriting user content (`projects/`, specs, decisions, incidents) — that is data.
- Changing `.gitignore` secret handling — already correct.
- Any secret rotation (separate concern; do if repo was ever pushed with `.env` — confirmed it wasn't).

---

## Rollout order

1. Bucket A code fixes (low risk, mechanical) → verify tower + tests.
2. `.mcp.json` externalize → confirm ADO MCP still loads.
3. Bucket B identity extraction → `aios.config.md` + trim `CLAUDE.md`.
4. `.env.example` doc pass.
5. Final grep + portable-copy smoke test.
