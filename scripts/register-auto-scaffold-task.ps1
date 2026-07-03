#!/usr/bin/env pwsh
# Run this once (as your user, no admin needed) to register the scheduled task.
# Re-run to update it if the script path changes.

$scriptPath = Join-Path $PSScriptRoot "auto-scaffold.ps1"
$taskName   = "AIS-OS Auto Scaffold"

$action  = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-ExecutionPolicy Bypass -NonInteractive -WindowStyle Hidden -File `"$scriptPath`""

# Runs every 15 minutes, indefinitely
$trigger = New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Minutes 15) -Once -At (Get-Date)

$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 5) `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -DontStopIfGoingOnBatteries

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -RunLevel Limited `
    -Force

Write-Host "Task '$taskName' registered. Runs every 15 minutes."
Write-Host "Manage it: taskschd.msc or Get-ScheduledTask -TaskName '$taskName'"
