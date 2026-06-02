#!/usr/bin/env pwsh
# Watches Hermes for draft projects not yet scaffolded in AIS-OS.
# Run by Windows Task Scheduler. No Claude API call needed.

$aiosRoot  = "C:\Users\chase\OneDrive\Magiq\AIS-OS"
$projectsDir = Join-Path $aiosRoot "projects"
$logFile   = Join-Path $aiosRoot "scripts\auto-scaffold.log"
$hermesDataPath = "/opt/data/.hermes/data/projects"
$telegramSession = "agent:main:telegram:dm:8538216952"

function Log($msg) {
    $ts = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    "$ts  $msg" | Tee-Object -FilePath $logFile -Append | Out-Null
}

function Hermes-MCP($tool, $args) {
    $init    = '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"auto-scaffold","version":"1.0"}}}'
    $call    = "{`"jsonrpc`":`"2.0`",`"id`":2,`"method`":`"tools/call`",`"params`":{`"name`":`"$tool`",`"arguments`":$($args | ConvertTo-Json -Compress)}}"
    $result  = ("$init`n$call") | docker exec -i hermes hermes mcp serve 2>$null
    $lines   = $result -split "`n" | Where-Object { $_ -match '"id":2' }
    if ($lines) { return $lines[-1] | ConvertFrom-Json } else { return $null }
}

function Send-Telegram($msg) {
    $args = @{ session_key = $telegramSession; content = $msg }
    Hermes-MCP "messages_send" $args | Out-Null
}

function Scaffold-Project($slug, $manifestJson, $briefContent) {
    $m = $manifestJson

    $projDir      = Join-Path $projectsDir $slug
    $decisionsDir = Join-Path $projDir "decisions"
    $adrsDir      = Join-Path $projDir "adrs"
    $specDir      = Join-Path $projDir "spec"

    New-Item -ItemType Directory -Force -Path $projDir, $decisionsDir, $specDir | Out-Null
    if ($m.modules -and $m.modules.Count -gt 0) {
        New-Item -ItemType Directory -Force -Path $adrsDir | Out-Null
    }

    $now = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssZ")
    $today = (Get-Date).ToString("yyyy-MM-dd")
    $displayName = $m.displayName
    $stack = $m.stack
    $modules = if ($m.modules) { ($m.modules | ForEach-Object { "- $_" }) -join "`n" } else { "_None specified_" }
    $integrations = if ($m.integrations) { $m.integrations } else { "_None specified_" }
    $ado = if ($m.adoBoard) { $m.adoBoard } else { "_Not yet assigned_" }
    $priority = if ($m.priority) { $m.priority } else { "Medium" }

    # brief.md
    Set-Content (Join-Path $projDir "brief.md") @"
$briefContent
_Scaffolded: $now | Source: Hermes auto-scaffold_
"@

    # CLAUDE.md
    Set-Content (Join-Path $projDir "CLAUDE.md") @"
# $displayName

## Project Overview
$($m.description)

**Current status:** Draft — auto-scaffolded from Hermes capture. Spec not yet started.

## Stack
$stack

## Modules
$modules

## Integrations
$integrations

## ADO Board
$ado

## Priority
$priority

## File Map

| File | Purpose |
|------|---------|
| brief.md | Project summary and constraints |
| notes.md | Open questions and session notes |
| risks.md | Risk register |
| decisions/log.md | Architecture and design decisions (append-only) |
| spec/ | Spec files |

## Memory System

Read MEMORY.md at session start. Use it silently.
Add entries only when Chase says "remember this", "log this", "save this".
Flag contradictions — never silently overwrite.
"@

    # MEMORY.md
    Set-Content (Join-Path $projDir "MEMORY.md") @"
# Memory — $slug
_Last updated: $today_

## Memory
<!-- Persistent — only remove or change if Chase asks. -->

- **Status**: Draft — auto-scaffolded $today, spec not yet started
- **Priority**: $priority
- **ADO Board**: $ado
"@

    # notes.md
    Set-Content (Join-Path $projDir "notes.md") @"
# Notes — $displayName

_Open questions, session notes, and resolutions._

---
"@

    # risks.md
    Set-Content (Join-Path $projDir "risks.md") @"
# Risks — $displayName

_Add new risks via "risk for $slug" in Telegram or directly here._

---
"@

    # decisions/log.md
    Set-Content (Join-Path $decisionsDir "log.md") @"
# Decision Log — $displayName

_Append-only. All architecture and design decisions recorded here._

---
"@

    Log "Scaffolded: $slug"
}

# --- Main ---
Log "--- auto-scaffold run start ---"

# Get Hermes project list
$hermesProjects = docker exec hermes sh -c "ls $hermesDataPath 2>/dev/null" 2>$null
if ($LASTEXITCODE -ne 0 -or -not $hermesProjects) {
    Log "Hermes not reachable or no projects found. Exiting."
    exit 0
}

$slugs = $hermesProjects -split "`n" | Where-Object { $_.Trim() -ne "" } | ForEach-Object { $_.Trim() }
$scaffolded = @()

foreach ($slug in $slugs) {
    $localPath = Join-Path $projectsDir $slug
    if (Test-Path $localPath) { continue }

    # Read manifest
    $manifestRaw = docker exec hermes cat "$hermesDataPath/$slug/manifest.json" 2>$null
    if (-not $manifestRaw) { Log "No manifest for $slug — skipping."; continue }

    $manifest = $manifestRaw | ConvertFrom-Json
    if ($manifest.status -ne "draft") { Log "$slug status=$($manifest.status) — skipping."; continue }

    # Read brief
    $brief = docker exec hermes cat "$hermesDataPath/$slug/brief.md" 2>$null
    if (-not $brief) { $brief = "# $($manifest.displayName)`n_No brief captured._" }

    Scaffold-Project $slug $manifest $brief
    $scaffolded += $slug
}

if ($scaffolded.Count -gt 0) {
    $list = $scaffolded -join ", "
    Log "Sending Telegram notification for: $list"
    Send-Telegram "🏗️ Auto-scaffolded: $list`nProject folders created in AIS-OS. Open Claude Code to start working."
} else {
    Log "Nothing to scaffold."
}

Log "--- auto-scaffold run end ---"
