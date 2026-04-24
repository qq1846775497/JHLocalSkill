#Requires -RunAsAdministrator
#Requires -Version 5.1
<#
.SYNOPSIS
    一键安装 Kimi CLI Skill Router Hook 补丁。
.DESCRIPTION
    1. 检测 Kimi CLI site-packages 路径
    2. 备份原文件（首次运行时）
    3. 打 runner.py 补丁（inject_prompt unwrap）
    4. 打 kimisoul.py 补丁（hook stdout injection）
    5. 清理 .pyc 缓存
    6. 运行测试验证
#>

$ErrorActionPreference = "Stop"

$sitePackages = "$env:APPDATA\uv\tools\kimi-cli\Lib\site-packages"
$runnerPy     = "$sitePackages\kimi_cli\hooks\runner.py"
$kimisoulPy   = "$sitePackages\kimi_cli\soul\kimisoul.py"

# 检测 Kimi CLI 是否存在
if (-not (Test-Path $runnerPy)) {
    Write-Error "Kimi CLI not found at $sitePackages. Install with: uv tool install kimi-cli"
}

Write-Host "=== Kimi CLI Skill Router Patch Installer ===" -ForegroundColor Cyan
Write-Host ""

# =============================================================================
# 1. 备份原文件（仅首次）
# =============================================================================

$runnerBak = "$runnerPy.bak"
$kimisoulBak = "$kimisoulPy.bak"

if (-not (Test-Path $runnerBak)) {
    Copy-Item $runnerPy $runnerBak -Force
    Write-Host "[Backup] runner.py -> runner.py.bak" -ForegroundColor Gray
}
if (-not (Test-Path $kimisoulBak)) {
    Copy-Item $kimisoulPy $kimisoulBak -Force
    Write-Host "[Backup] kimisoul.py -> kimisoul.py.bak" -ForegroundColor Gray
}

# =============================================================================
# 2. Patch runner.py
# =============================================================================

$runnerSrc = Get-Content $runnerPy -Raw

if ($runnerSrc.Contains("inject_prompt")) {
    Write-Host "[Skip] runner.py already patched." -ForegroundColor Green
} else {
    $oldRunner = @"
                if hook_output.get(""permissionDecision"") == ""deny"":
                    return HookResult(
                        action=""block"",
                        reason=str(hook_output.get(""permissionDecisionReason"", """)),
                        stdout=stdout,
                        stderr=stderr,
                        exit_code=0,
                    )
        except (json.JSONDecodeError, TypeError):
            pass

    return HookResult(action=""allow"", stdout=stdout, stderr=stderr, exit_code=exit_code)
"@

    $newRunner = @"
                if hook_output.get(""permissionDecision"") == ""deny"":
                    return HookResult(
                        action=""block"",
                        reason=str(hook_output.get(""permissionDecisionReason"", """)),
                        stdout=stdout,
                        stderr=stderr,
                        exit_code=0,
                    )
                # Support inject_prompt: unwrap JSON so downstream sees plain text
                inject_prompt = hook_output.get(""inject_prompt"")
                if isinstance(inject_prompt, str) and inject_prompt.strip():
                    stdout = inject_prompt
        except (json.JSONDecodeError, TypeError):
            pass

    return HookResult(action=""allow"", stdout=stdout, stderr=stderr, exit_code=exit_code)
"@

    $runnerSrc = $runnerSrc.Replace($oldRunner, $newRunner)
    Set-Content $runnerPy $runnerSrc -Encoding UTF8
    Write-Host "[Done] runner.py patched." -ForegroundColor Green
}

# =============================================================================
# 3. Patch kimisoul.py
# =============================================================================

$kimisoulSrc = Get-Content $kimisoulPy -Raw

if ($kimisoulSrc.Contains("Inject hook stdout into context")) {
    Write-Host "[Skip] kimisoul.py already patched." -ForegroundColor Green
} else {
    $oldKimisoul = @"
            wire_send(TurnBegin(user_input=user_input))
            turn_started = True
            user_message = Message(role=""user"", content=user_input)
"@

    $newKimisoul = @"
            wire_send(TurnBegin(user_input=user_input))
            turn_started = True

            # Inject hook stdout into context before processing the turn
            for result in hook_results:
                if result.stdout.strip():
                    await self._context.append_message(
                        Message(
                            role=""user"",
                            content=[system_reminder(result.stdout.strip())],
                        )
                    )
                    # Visible notification to user
                    try:
                        import json as _json
                        parsed = _json.loads(result.stdout.strip())
                        hso = parsed.get(""hookSpecificOutput"", {})
                        inject_text = hso.get(""inject_prompt"", """)
                        matched_skills = []
                        for line in inject_text.splitlines():
                            if line.startswith(""- "") and "" (置信度"" in line:
                                skill_id = line[2:].split("" (置信度"")[0].strip()
                                matched_skills.append(skill_id)
                        if matched_skills:
                            skill_tags = """", "".join(matched_skills)
                            wire_send(TextPart(text=f""⚠️ 已推荐 skill: {skill_tags}""))
                    except Exception:
                        pass

            user_message = Message(role=""user"", content=user_input)
"@

    $kimisoulSrc = $kimisoulSrc.Replace($oldKimisoul, $newKimisoul)
    Set-Content $kimisoulPy $kimisoulSrc -Encoding UTF8
    Write-Host "[Done] kimisoul.py patched." -ForegroundColor Green
}

# =============================================================================
# 4. 清理 .pyc 缓存
# =============================================================================

$pycFiles = @(
    "$sitePackages\kimi_cli\hooks\__pycache__\runner.cpython-313.pyc",
    "$sitePackages\kimi_cli\soul\__pycache__\kimisoul.cpython-313.pyc"
)

foreach ($pyc in $pycFiles) {
    if (Test-Path $pyc) {
        Remove-Item $pyc -Force
        Write-Host "[Clear] $pyc" -ForegroundColor Gray
    }
}

# =============================================================================
# 5. 运行测试
# =============================================================================

Write-Host ""
Write-Host "Running tests..." -ForegroundColor Cyan
$testScript = "$env:USERPROFILE\.kimi\skill-router\test_hook_injection.py"
if (Test-Path $testScript) {
    python $testScript
} else {
    Write-Host "Test script not found at $testScript" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Done. Restart Kimi CLI to apply changes." -ForegroundColor Green
Write-Host "Run check-patch.ps1 anytime to verify patch status." -ForegroundColor Gray
