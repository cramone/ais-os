# Creates a desktop shortcut for AIS-OS Control Tower
$WshShell = New-Object -ComObject WScript.Shell
$Desktop = [Environment]::GetFolderPath('Desktop')
$Shortcut = $WshShell.CreateShortcut("$Desktop\AIS-OS Control Tower.lnk")
# Self-locate: this script lives at <root>/tower/create-shortcut.ps1
$Root = Split-Path -Parent $PSScriptRoot
$Shortcut.TargetPath = Join-Path $PSScriptRoot "launch.bat"
$Shortcut.WorkingDirectory = $Root
$Shortcut.WindowStyle = 7
$Shortcut.Description = "AIS-OS Control Tower - http://localhost:8765"
$Shortcut.IconLocation = "C:\Windows\System32\shell32.dll,14"
$Shortcut.Save()
Write-Host "Shortcut created on Desktop: AIS-OS Control Tower"
