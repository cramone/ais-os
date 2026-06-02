# Creates a desktop shortcut for AIS-OS Control Tower
$WshShell = New-Object -ComObject WScript.Shell
$Desktop = [Environment]::GetFolderPath('Desktop')
$Shortcut = $WshShell.CreateShortcut("$Desktop\AIS-OS Control Tower.lnk")
$Shortcut.TargetPath = "C:\Users\chase\OneDrive\Magiq\AIS-OS\tower\launch.bat"
$Shortcut.WorkingDirectory = "C:\Users\chase\OneDrive\Magiq\AIS-OS"
$Shortcut.WindowStyle = 7
$Shortcut.Description = "AIS-OS Control Tower - http://localhost:8765"
$Shortcut.IconLocation = "C:\Windows\System32\shell32.dll,14"
$Shortcut.Save()
Write-Host "Shortcut created on Desktop: AIS-OS Control Tower"
