#Requires -Version 5.1
<#
.SYNOPSIS
    快速检查 Kimi CLI Skill Router Hook 的补丁状态。
.DESCRIPTION
    检查 runner.py 和 kimisoul.py 的 inject_prompt 补丁是否存在。
    如果不存在，提示运行 install-kimi-hook-patch.ps1。
    同时检查并清理过期的 .pyc 缓存。
#>

$ErrorActionPreference = "Stop"

$sitePackages = "$env:APPDATA\uv\tools\kimi-cli\Lib\site-packages"
$runner     = "$sitePackages\kimi_cli\hooks\runner.py"
$kimisoul   = "$sitePackages\kimi_cli\soul\kimisoul.py"
$runnerPyc  = "$sitePackages\kimi_cli\hooks\__pycache__\runner.cpython-313.pyc"
$kimisoulPyc= "$sitePackages\kimi_cli\soul\__pycache__\kimisoul.cpython-313.pyc"

$ok = $true

Write-Host "=== Kimi CLI Skill Router Patch Check ===" -ForegroundColor Cyan
Write-Host ""

# 1. 检查 runner.py
if (Test-Path $runner) {
    if ((Get-Content $runner -Raw) -match "inject_prompt") {
        Write-Host "[OK]   runner.py  — inject_prompt unwrap patched" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] runner.py  — inject_prompt unwrap NOT patched" -ForegroundColor Red
        $ok = $false
    }
} else {
    Write-Host "[FAIL] runner.py  — file not found at $runner" -ForegroundColor Red
    $ok = $false
}

# 2. 检查 kimisoul.py
if (Test-Path $kimisoul) {
    if ((Get-Content $kimisoul -Raw) -match "Inject hook stdout into context") {
        Write-Host "[OK]   kimisoul.py — hook stdout injection patched" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] kimisoul.py — hook stdout injection NOT patched" -ForegroundColor Red
        $ok = $false
    }
} else {
    Write-Host "[FAIL] kimisoul.py — file not found at $kimisoul" -ForegroundColor Red
    $ok = $false
}

# 3. 检查 .pyc 缓存是否过期
$cacheIssue = $false
if (Test-Path $runnerPyc) {
    if ((Get-Item $runnerPyc).LastWriteTime -lt (Get-Item $runner).LastWriteTime) {
        Write-Host "[WARN] runner.pyc   — cache older than source, will auto-recompile" -ForegroundColor Yellow
        $cacheIssue = $true
    }
}
if (Test-Path $kimisoulPyc) {
    if ((Get-Item $kimisoulPyc).LastWriteTime -lt (Get-Item $kimisoul).LastWriteTime) {
        Write-Host "[WARN] kimisoul.pyc — cache older than source, will auto-recompile" -ForegroundColor Yellow
        $cacheIssue = $true
    }
}

Write-Host ""
if ($ok) {
    Write-Host "All patches are in place. " -ForegroundColor Green -NoNewline
    if ($cacheIssue) {
        Write-Host "But .pyc cache is stale — restart Kimi CLI to refresh." -ForegroundColor Yellow
    } else {
        Write-Host "Hook should work in all new CLI instances." -ForegroundColor Green
    }
} else {
    Write-Host "Patches missing! Run the following to fix:" -ForegroundColor Red
    Write-Host ""
    Write-Host "    & `"$env:USERPROFILE\.kimi\skills\JHLocalSkill\kimi-skill-router-setup\scripts\install-kimi-hook-patch.ps1`"" -ForegroundColor White
}

Write-Host ""
