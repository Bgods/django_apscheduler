# restart.ps1 - 重启 Django APScheduler 服务
Set-Location $PSScriptRoot

$NSSM = '.\nssm\nssm.exe'
$SERVICE_NAME = 'django_apscheduler'

if (-not (Test-Path $NSSM)) {
    Write-Host "错误: 未找到 $NSSM" -ForegroundColor Red
    exit 1
}

Write-Host "正在重启服务: $SERVICE_NAME"
& $NSSM restart $SERVICE_NAME

$status = (& $NSSM status $SERVICE_NAME).Trim()
if ($status -eq 'SERVICE_RUNNING') {
    Write-Host "服务重启成功: $status" -ForegroundColor Green
} else {
    Write-Host "服务状态异常: $status" -ForegroundColor Red
}
