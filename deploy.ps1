# deploy.ps1 - 一键部署/更新脚本
# 使用方式：右键 → 使用 PowerShell 运行（需管理员权限）

Set-Location $PSScriptRoot

$SERVICE_NAME = 'Django_APScheduler'
$GIT_URL      = 'https://github.com/Bgods/django_apscheduler.git'
$BRANCH       = 'master'
$NSSM         = '.\nssm\nssm.exe'
$PORT         = 8000
$PYTHON       = '.\.venv\Scripts\python.exe'

Write-Host ''
Write-Host '========================================'
Write-Host '  一键部署 / 更新脚本'
Write-Host '========================================'
Write-Host ''

# 注册/操作 Windows 服务需要管理员权限
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host '  [错误] 请以管理员身份运行（注册 Windows 服务需要管理员权限）' -ForegroundColor Red
    Write-Host '  操作方式：右键 deploy.bat → 以管理员身份运行' -ForegroundColor Yellow
    pause
    exit 1
}

# ============================================================
# Step 0: 拉取最新代码（确保脚本自身也是最新版）
# ============================================================
Write-Host '[0/9] 更新代码...'

# 检查 Git
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host '  [错误] 未找到 Git，请先安装 Git 并加入 PATH' -ForegroundColor Red
    exit 1
}

# 检查 Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host '  [错误] 未找到 Python，请先安装 Python 3.10+ 并加入 PATH' -ForegroundColor Red
    exit 1
}

# 首次运行：初始化 Git 仓库
if (-not (Test-Path '.git')) {
    Write-Host '  初始化 Git 仓库...'
    git init
    git remote add origin $GIT_URL
    git fetch origin $BRANCH
    if ($LASTEXITCODE -ne 0) { Write-Host '  [错误] 拉取代码失败' -ForegroundColor Red; exit 1 }
    git reset --hard "origin/$BRANCH"
    Write-Host ''
    Write-Host '  [提示] 代码已首次同步，请重新运行 deploy.ps1' -ForegroundColor Yellow
    pause
    exit 0
}

# 非首次：拉取最新代码
git fetch origin $BRANCH
if ($LASTEXITCODE -ne 0) { Write-Host '  [错误] 拉取代码失败' -ForegroundColor Red; exit 1 }

# 检查本地是否有已跟踪文件的修改（未跟踪文件如 .env 不影响）
$trackedChanges = git diff --name-only HEAD 2>$null
$stagedChanges = git diff --cached --name-only 2>$null
if ($trackedChanges -or $stagedChanges) {
    Write-Host ''
    Write-Host '  [警告] 检测到本地有未提交的修改：' -ForegroundColor Yellow
    git status --short
    Write-Host ''
    $confirm = Read-Host '  继续将覆盖本地修改（git reset --hard），是否继续？(y/N)'
    if ($confirm -ne 'y' -and $confirm -ne 'Y') {
        Write-Host '  已取消代码更新，使用当前本地代码继续部署...' -ForegroundColor Cyan
    } else {
        git reset --hard "origin/$BRANCH"
        Write-Host '  代码已更新到最新版本（本地修改已覆盖）' -ForegroundColor Yellow
    }
} else {
    git reset --hard "origin/$BRANCH"
    Write-Host '  代码已更新到最新版本'
}

# ============================================================
# Step 1: 环境检查
# ============================================================
Write-Host ''
Write-Host '[1/9] 环境检查...'
$pyVer = (python --version 2>&1) -replace 'Python ', ''
Write-Host "  Python: $pyVer"
Write-Host '  环境检查通过'

# ============================================================
# Step 2: 下载 NSSM（如不存在）
# ============================================================
Write-Host ''
Write-Host '[2/9] 检查 NSSM...'
if (Test-Path $NSSM) {
    Write-Host '  NSSM 已存在'
} else {
    Write-Host '  正在下载 NSSM...'
    if (-not (Test-Path 'nssm')) { New-Item -ItemType Directory -Path 'nssm' | Out-Null }
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $zipUrl = 'https://nssm.cc/release/nssm-2.24.zip'
    $zipFile = 'nssm\nssm.zip'
    try {
        Invoke-WebRequest -Uri $zipUrl -OutFile $zipFile -UseBasicParsing
    } catch {
        $zipUrl2 = 'https://github.com/kirillkovalenko/nssm/releases/download/2.24/nssm-2.24.zip'
        Invoke-WebRequest -Uri $zipUrl2 -OutFile $zipFile -UseBasicParsing
    }
    Expand-Archive -Path $zipFile -DestinationPath 'nssm' -Force
    $nssmExe = Get-ChildItem -Path 'nssm' -Recurse -Filter 'nssm.exe' | Select-Object -First 1
    if ($nssmExe) { Copy-Item $nssmExe.FullName 'nssm\nssm.exe' -Force }
    Remove-Item $zipFile -Force -ErrorAction SilentlyContinue
    Write-Host '  NSSM 下载完成'
}

# ============================================================
# Step 3: 停止服务
# ============================================================
Write-Host ''
Write-Host '[3/9] 停止服务...'
$svc = Get-Service -Name $SERVICE_NAME -ErrorAction SilentlyContinue
if ($svc) {
    & $NSSM stop $SERVICE_NAME 2>$null
    Start-Sleep -Seconds 2
    Write-Host '  服务已停止'
} else {
    Write-Host '  服务不存在，跳过停止'
}

# ============================================================
# Step 4: 检查 .env 配置
# ============================================================
Write-Host ''
Write-Host '[4/9] 检查环境配置...'
if (-not (Test-Path '.env')) {
    if (Test-Path '.env.example') {
        Copy-Item '.env.example' '.env'
        Write-Host '  [提示] 已根据 .env.example 生成 .env（默认使用 SQLite，无需安装数据库）' -ForegroundColor Yellow
        Write-Host '         多机部署请先取消注释并填写 MySQL 配置，然后重新运行本脚本' -ForegroundColor Yellow
        pause
        exit 0
    } else {
        Write-Host '  [警告] 未找到 .env 和 .env.example，请手动创建 .env 配置文件' -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host '  .env 配置文件已存在'
}

# 服务端口与 .env 中的 SCHEDULER_API_PORT 保持一致（多机部署必须一致）
$portLine = Get-Content '.env' -ErrorAction SilentlyContinue | Where-Object { $_ -match '^\s*SCHEDULER_API_PORT\s*=\s*(\d+)' } | Select-Object -First 1
if ($portLine -and $portLine -match '=\s*(\d+)') {
    $PORT = [int]$Matches[1]
}
Write-Host "  服务端口: $PORT"

# ============================================================
# Step 5: 安装 Python 依赖
# ============================================================
Write-Host ''
Write-Host '[5/9] 安装 Python 依赖...'
if (-not (Test-Path $PYTHON)) {
    Write-Host '  创建虚拟环境...'
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { Write-Host '  [错误] 创建虚拟环境失败' -ForegroundColor Red; exit 1 }
}
& $PYTHON -m pip install -r requirements.txt -q
if ($LASTEXITCODE -ne 0) { Write-Host '  [错误] 安装 Python 依赖失败' -ForegroundColor Red; exit 1 }
Write-Host '  Python 依赖安装完成'

# ============================================================
# Step 6: 数据库迁移
# ============================================================
Write-Host ''
Write-Host '[6/9] 数据库迁移...'
& $PYTHON manage.py migrate --noinput
if ($LASTEXITCODE -ne 0) {
    Write-Host '  [错误] 数据库迁移失败，请检查 .env 中的数据库配置' -ForegroundColor Red
    exit 1
}
Write-Host '  数据库迁移完成'

# ============================================================
# Step 7: 检查前端构建产物
# ============================================================
Write-Host ''
Write-Host '[7/9] 检查前端构建产物...'
if (Test-Path 'tasks\static\app\index.html') {
    Write-Host '  前端构建产物已存在'
} else {
    Write-Host '  [警告] 前端构建产物不存在，管理后台将无法访问' -ForegroundColor Yellow
}

# ============================================================
# Step 8: 首次部署检查（创建管理员）
# ============================================================
Write-Host ''
Write-Host '[8/9] 首次部署检查...'
$hasAdmin = & $PYTHON -c "import os,django;os.environ.setdefault('DJANGO_SETTINGS_MODULE','task_scheduler.settings');django.setup();from django.contrib.auth.models import User;exit(0 if User.objects.filter(is_superuser=True).exists() else 1)" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host '  [提示] 未检测到管理员账户，正在创建...' -ForegroundColor Yellow
    Write-Host ''
    & $PYTHON manage.py createsuperuser
    if ($LASTEXITCODE -ne 0) {
        Write-Host '  [警告] 创建管理员失败，可稍后手动执行' -ForegroundColor Yellow
    } else {
        Write-Host '  管理员账户创建成功'
    }
} else {
    Write-Host '  管理员账户已存在'
}

# ============================================================
# Step 9: 注册并启动服务
# ============================================================
Write-Host ''
Write-Host '[9/9] 注册并启动服务...'
$svc = Get-Service -Name $SERVICE_NAME -ErrorAction SilentlyContinue
$workDir = (Get-Location).Path
# --insecure：DEBUG=False 时 runserver 仍可提供 /static/ 前端产物
$appParams = "manage.py runserver 0.0.0.0:$PORT --noreload --insecure"
if (-not $svc) {
    Write-Host '  注册服务...'
    & $NSSM install $SERVICE_NAME "$workDir\.venv\Scripts\python.exe"
    & $NSSM set $SERVICE_NAME DisplayName "Django APScheduler"
    & $NSSM set $SERVICE_NAME Start "SERVICE_AUTO_START"
    & $NSSM set $SERVICE_NAME AppExit "Default" "Restart"
    & $NSSM set $SERVICE_NAME AppRestartDelay 5000
    Write-Host '  服务注册完成'
}
# 每次部署都同步服务参数，端口或启动参数变更后无需删除服务重建
& $NSSM set $SERVICE_NAME AppDirectory "$workDir"
& $NSSM set $SERVICE_NAME AppParameters $appParams
& $NSSM restart $SERVICE_NAME 2>$null
Start-Sleep -Seconds 3

$status = (& $NSSM status $SERVICE_NAME 2>$null).Trim()
if ($status -eq 'SERVICE_RUNNING') {
    Write-Host '  服务启动成功'
} else {
    Write-Host "  [警告] 服务状态: $status，请检查日志" -ForegroundColor Yellow
}

Write-Host ''
Write-Host '========================================'
Write-Host '  部署完成！'
Write-Host "  访问地址: http://localhost:$PORT/app/"
Write-Host '========================================'
Write-Host ''
pause
