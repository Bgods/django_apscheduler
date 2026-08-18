# Django APScheduler Windows Service - One-click install
# Run as Administrator
#
# 修改端口：修改下方 $port 变量（默认 8000）
# 多机部署时每台机器需使用相同的端口，要求与 `.env` 中的 `SCHEDULER_API_PORT` 一致

$ErrorActionPreference = "Stop"
$serviceName = "Django_APScheduler"
$pwd = $PSScriptRoot
$pythonPath = "$pwd\.venv\Scripts\python.exe"
$managePath = "$pwd\manage.py"
$port = 8000  # 服务端口，多机部署时所有机器必须保持一致，要求与 `.env` 中的 `SCHEDULER_API_PORT` 一致

# ---------- Step 0: Admin check ----------
$wid = [System.Security.Principal.WindowsIdentity]::GetCurrent()
$wpr = New-Object System.Security.Principal.WindowsPrincipal($wid)
$adminRole = [System.Security.Principal.WindowsBuiltInRole]::Administrator
if (!$wpr.IsInRole($adminRole)) {
    Write-Host "Please run as Administrator!" -ForegroundColor Red
    pause
    exit 1
}

# ---------- Step 1: Download NSSM ----------
Write-Host "[1/4] Downloading NSSM..." -ForegroundColor Cyan
$nssmDir = "$pwd\nssm"
$nssmExe = "$nssmDir\nssm.exe"
$nssmZip = "$nssmDir\nssm.zip"

if (!(Test-Path $nssmDir)) {
    New-Item -ItemType Directory -Path $nssmDir | Out-Null
}

if (!(Test-Path $nssmExe)) {
    $url = "https://nssm.cc/release/nssm-2.24.zip"
    Write-Host "  Fetching NSSM..."
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    try {
        Invoke-WebRequest -Uri $url -OutFile $nssmZip -UseBasicParsing
    } catch {
        $url2 = "https://github.com/kirillkovalenko/nssm/releases/download/2.24/nssm-2.24.zip"
        Write-Host "  Trying mirror..." -ForegroundColor Yellow
        Invoke-WebRequest -Uri $url2 -OutFile $nssmZip -UseBasicParsing
    }
    Expand-Archive -Path $nssmZip -DestinationPath $nssmDir -Force
    $found = Get-ChildItem -Path $nssmDir -Recurse -Filter "nssm.exe" | Select-Object -First 1
    if ($found) { Copy-Item $found.FullName $nssmExe -Force }
    Remove-Item $nssmZip -Force
    Write-Host "  NSSM ready" -ForegroundColor Green
} else {
    Write-Host "  NSSM already exists" -ForegroundColor Green
}

# ---------- Step 2: Clean old service ----------
Write-Host "[2/4] Cleaning old service..." -ForegroundColor Cyan
try {
    $oldService = Get-Service $serviceName -ErrorAction SilentlyContinue
    if ($oldService) {
        if ($oldService.Status -eq 'Running') {
            Stop-Service $serviceName -Force
            Start-Sleep -Seconds 2
        }
        sc.exe delete $serviceName
        Write-Host "  Waiting for system cleanup..." -ForegroundColor Yellow
        Start-Sleep -Seconds 3
    }
} catch {
    Write-Host "  No existing service or cleanup in progress" -ForegroundColor Green
}

# ---------- Step 3: Install service with NSSM ----------
Write-Host "[3/4] Installing service..." -ForegroundColor Cyan
& $nssmExe install $serviceName $pythonPath
& $nssmExe set $serviceName AppDirectory $pwd
& $nssmExe set $serviceName AppParameters "$managePath runserver 0.0.0.0:$port --noreload"
& $nssmExe set $serviceName DisplayName "Django APScheduler"
& $nssmExe set $serviceName Start SERVICE_AUTO_START
& $nssmExe set $serviceName AppExit Default Restart
& $nssmExe set $serviceName AppRestartDelay 5000
Write-Host "  Service installed" -ForegroundColor Green

# ---------- Step 4: Start service ----------
Write-Host "[4/4] Starting service..." -ForegroundColor Cyan
Start-Sleep -Seconds 1
& $nssmExe start $serviceName
Start-Sleep -Seconds 3
$status = & $nssmExe status $serviceName 2>&1

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  INSTALL COMPLETE!" -ForegroundColor Green
Write-Host "  Service : $serviceName" 
Write-Host "  Status  : $status"
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Commands:" -ForegroundColor Yellow
Write-Host "  $nssmExe status  $serviceName"
Write-Host "  $nssmExe start   $serviceName"
Write-Host "  $nssmExe stop    $serviceName"
Write-Host "  $nssmExe restart $serviceName"
Write-Host "  $nssmExe remove  $serviceName confirm"
Write-Host ""
pause
