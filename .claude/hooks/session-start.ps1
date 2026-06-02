#!/usr/bin/env pwsh
# Runs at SessionStart — scans project MEMORY.md files and checks for unscaffolded Hermes captures.
# Outputs JSON with additionalContext injected into Claude's context.

$aiosRoot = "C:\Users\chase\OneDrive\Magiq\AIS-OS"
$projectsDir = Join-Path $aiosRoot "projects"
$lines = @()

# --- Project memory digest ---
if (Test-Path $projectsDir) {
    $projects = Get-ChildItem $projectsDir -Directory | Sort-Object Name
    foreach ($proj in $projects) {
        $memFile = Join-Path $proj.FullName "MEMORY.md"
        if (Test-Path $memFile) {
            $content = Get-Content $memFile -Raw
            # Extract Status and Priority lines
            $status   = if ($content -match '(?m)^\*\*Status\*\*:\s*(.+)$')   { $Matches[1].Trim() } else { "unknown" }
            $priority = if ($content -match '(?m)^\*\*Priority\*\*:\s*(.+)$') { $Matches[1].Trim() } else { "" }
            $tag = if ($priority) { " [$priority]" } else { "" }
            $lines += "  $($proj.Name)$tag — $status"
        }
    }
}

# --- Adhoc notes from Hermes ---
$adhocFile = "C:\Users\chase\.hermes\data\adhoc-notes.md"
if (Test-Path $adhocFile) {
    $adhocContent = Get-Content $adhocFile -Raw
    if ($adhocContent -and $adhocContent.Trim() -ne "" -and $adhocContent -notmatch '^\s*#\s*Adhoc Notes\s*$') {
        $lines += ""
        $lines += "--- Adhoc Notes (from Hermes) ---"
        $lines += $adhocContent.Trim()
        $lines += "---"
    }
}

# --- Unscaffolded Hermes captures ---
$hermesDataPath = "/opt/data/data/projects"
$dockerCheck = docker exec hermes sh -c "ls $hermesDataPath 2>/dev/null" 2>$null
if ($LASTEXITCODE -eq 0 -and $dockerCheck) {
    $hermesProjects = $dockerCheck -split "`n" | Where-Object { $_.Trim() -ne "" }
    $unscaffolded = @()
    foreach ($slug in $hermesProjects) {
        $slug = $slug.Trim()
        $localPath = Join-Path $projectsDir $slug
        if (-not (Test-Path $localPath)) {
            $unscaffolded += $slug
        }
    }
    if ($unscaffolded.Count -gt 0) {
        $lines += ""
        $lines += "  PENDING SCAFFOLD: $($unscaffolded -join ', ') — say 'scaffold project <slug>' to create folder"
    }
}

# --- Output ---
if ($lines.Count -gt 0) {
    $digest = "AIS-OS project status:`n" + ($lines -join "`n")
    $output = @{ hookSpecificOutput = @{ hookEventName = "SessionStart"; additionalContext = $digest } } | ConvertTo-Json -Compress
    Write-Output $output
}
