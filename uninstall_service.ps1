# Django APScheduler Windows Service - Uninstall
# Run as Administrator

$ErrorActionPreference = "Stop"
$serviceName = "Django_APScheduler"
$pwd = $PSScriptRoot

# --- Admin check ---
$wid = [System.Security.Principal.WindowsIdentity]::GetCurrent()
$wpr = New-Object System.Security.Principal.WindowsPrincipal($wid)
$adminRole = [System.Security.Principal.WindowsBuiltInRole]::Administrator
if (!$wpr.IsInRole($adminRole)) {
    Write-Host "Please run as Administrator!" -ForegroundColor Red
    pause
    exit 1
}

# --- Stop and remove ---
$existing = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
if (-Not $existing) {
    Write-Host "[INFO] Service '$serviceName' does not exist, nothing to uninstall" -ForegroundColor Yellow
} else {
    Write-Host "[INFO] Stopping service..." -ForegroundColor Cyan
    if ($existing.Status -eq 'Running') {
        Stop-Service $serviceName -Force
        Start-Sleep -Seconds 2
    }

    Write-Host "[INFO] Removing service..." -ForegroundColor Cyan
    sc.exe delete $serviceName
    Start-Sleep -Seconds 2

    Write-Host "[OK] Service uninstalled" -ForegroundColor Green
}

pause
