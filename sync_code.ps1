# sync_code.ps1 - Pull latest code from GitHub (self-updating)
$ErrorActionPreference = "Stop"

$gitUrl = "https://github.com/Bgods/django_apscheduler.git"
$branch = "master"
$target = $PSScriptRoot

Set-Location $target

# 1. Init & self-update (always pull latest sync_code.ps1 first)
if (-not (Test-Path ".git")) {
    git init
    git remote add origin $gitUrl
}
git fetch origin $branch
git checkout origin/$branch -- sync_code.ps1

# 2. Pull the rest
Write-Host "Pulling latest code..." -ForegroundColor Cyan
git reset --hard origin/$branch

Write-Host "Done." -ForegroundColor Green
