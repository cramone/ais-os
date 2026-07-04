# Creates a desktop shortcut that deploys AIS-OS Control Tower to Cortex
# (SSH in, git pull, docker compose build/restart). Companion to
# create-shortcut.ps1, which launches the local dev server instead.
$WshShell = New-Object -ComObject WScript.Shell
$Desktop = [Environment]::GetFolderPath('Desktop')
$Shortcut = $WshShell.CreateShortcut("$Desktop\Deploy Tower to Cortex.lnk")
# Self-locate: this script lives at <root>/tower/create-deploy-shortcut.ps1
$Root = Split-Path -Parent $PSScriptRoot
$Shortcut.TargetPath = Join-Path $PSScriptRoot "deploy.bat"
$Shortcut.WorkingDirectory = $Root
$Shortcut.WindowStyle = 1
$Shortcut.Description = "Deploy AIS-OS Control Tower to Cortex (ssh + docker compose build/restart)"
$Shortcut.IconLocation = "C:\Windows\System32\shell32.dll,137"
$Shortcut.Save()
Write-Host "Shortcut created on Desktop: Deploy Tower to Cortex"
