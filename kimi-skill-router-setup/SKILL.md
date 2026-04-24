---
name: kimi-skill-router-setup
description: Kimi CLI / Claude Code 个人级 Skill Router 配置与安装指南。涵盖 hook 配置、源码补丁、跨 CLI 适配、新电脑一键安装、自动测试。当用户询问 skill 系统如何工作、如何配置 Kimi CLI skill、router 为什么不生效、换电脑如何迁移、Claude Code 如何接入 skill 时使用。
tags: [Kimi-CLI, Claude-Code, Skill-Router, Hook, Configuration, Setup, Windows, Migration]
---

# 个人级 Skill Router 配置与迁移指南

## 目标

无论使用 **Kimi CLI** 还是 **Claude Code**，在用户发送消息前，自动匹配 JHLocalSkill 库中的 SKILL.md，并**强制注入**到 AI 上下文，确保 AI 在行动前读取相关 skill。

---

## 一、Kimi CLI 完整安装（新电脑 / 重装后）

### 1.1 前提

- Windows 10/11
- Python 3.10+
- Kimi CLI 已安装（`uv tool install kimi-cli` 或 `pip install kimi-cli`）
- PowerShell 5.1+
- JHLocalSkill 仓库已 clone 到 `D:\jiangheng\JHLocalSkill`

### 1.2 目录结构

```
D:\jiangheng\JHLocalSkill          # Skill 主库（>=62 个 SKILL.md）
~/.kimi/skill-router/               # Router 脚本、索引、触发词
~/.kimi/config.toml                 # Kimi CLI 配置（含 hook）
~/.kimi/AGENTS.md                   # 可选：全局 AGENTS.md
```

### 1.3 config.toml Hook

编辑 `~/.kimi/config.toml`：

```toml
[[hooks]]
event = "UserPromptSubmit"
command = "python C:\\Users\\<USERNAME>\\.kimi\\skill-router\\kimi_skill_router.py"
timeout = 70
```

> `<USERNAME>` 替换为实际 Windows 用户名。

### 1.4 Router 脚本

将 `kimi_skill_router.py` 放到 `~/.kimi/skill-router/kimi_skill_router.py`。

该脚本要求：
- 三层匹配：硬编码规则 → 触发词 → 描述关键词
- 纯本地，零 API 调用
- **输出 JSON 格式**（这是补丁生效的关键）：
  ```json
  {"hookSpecificOutput":{"inject_prompt":"⚠️ SKILL ROUTER\n..."}}
  ```

### 1.5 核心：打源码补丁

Kimi CLI 1.30.0 原生不支持将 hook stdout 注入 AI 上下文。必须修改两个源码文件。

#### 补丁 A — `kimi_cli/hooks/runner.py`

**路径**：`%APPDATA%\uv\tools\kimi-cli\Lib\site-packages\kimi_cli\hooks\runner.py`

在 `run_hook` 函数末尾找到这一段：

```python
    # Exit 0 + JSON stdout = structured decision
    if exit_code == 0 and stdout.strip():
        try:
            raw = json.loads(stdout)
            if isinstance(raw, dict):
                parsed = cast(dict[str, Any], raw)
                hook_output = cast(dict[str, Any], parsed.get("hookSpecificOutput", {}))
                if hook_output.get("permissionDecision") == "deny":
                    return HookResult(
                        action="block",
                        reason=str(hook_output.get("permissionDecisionReason", "")),
                        stdout=stdout,
                        stderr=stderr,
                        exit_code=0,
                    )
        except (json.JSONDecodeError, TypeError):
            pass

    return HookResult(action="allow", stdout=stdout, stderr=stderr, exit_code=exit_code)
```

替换为：

```python
    # Exit 0 + JSON stdout = structured decision
    if exit_code == 0 and stdout.strip():
        try:
            raw = json.loads(stdout)
            if isinstance(raw, dict):
                parsed = cast(dict[str, Any], raw)
                hook_output = cast(dict[str, Any], parsed.get("hookSpecificOutput", {}))
                if hook_output.get("permissionDecision") == "deny":
                    return HookResult(
                        action="block",
                        reason=str(hook_output.get("permissionDecisionReason", "")),
                        stdout=stdout,
                        stderr=stderr,
                        exit_code=0,
                    )
                # Support inject_prompt: unwrap JSON so downstream sees plain text
                inject_prompt = hook_output.get("inject_prompt")
                if isinstance(inject_prompt, str) and inject_prompt.strip():
                    stdout = inject_prompt
        except (json.JSONDecodeError, TypeError):
            pass

    return HookResult(action="allow", stdout=stdout, stderr=stderr, exit_code=exit_code)
```

#### 补丁 B — `kimi_cli/soul/kimisoul.py`

**路径**：`%APPDATA%\uv\tools\kimi-cli\Lib\site-packages\kimi_cli\soul\kimisoul.py`

找到 `UserPromptSubmit hook` 处理段（约第 478-502 行）：

```python
            for result in hook_results:
                if result.action == "block":
                    wire_send(TurnBegin(user_input=user_input))
                    turn_started = True
                    wire_send(TextPart(text=result.reason or "Prompt blocked by hook."))
                    wire_send(TurnEnd())
                    turn_finished = True
                    return

            wire_send(TurnBegin(user_input=user_input))
            turn_started = True
            user_message = Message(role="user", content=user_input)
```

替换为：

```python
            for result in hook_results:
                if result.action == "block":
                    wire_send(TurnBegin(user_input=user_input))
                    turn_started = True
                    wire_send(TextPart(text=result.reason or "Prompt blocked by hook."))
                    wire_send(TurnEnd())
                    turn_finished = True
                    return

            wire_send(TurnBegin(user_input=user_input))
            turn_started = True

            # Inject hook stdout into context before processing the turn
            for result in hook_results:
                if result.stdout.strip():
                    await self._context.append_message(
                        Message(
                            role="user",
                            content=[system_reminder(result.stdout.strip())],
                        )
                    )

            user_message = Message(role="user", content=user_input)
```

> 这两个补丁不需要重新编译或重新安装 Kimi CLI，修改 `site-packages` 中的 `.py` 文件后立即生效。

### 1.7 验证

```powershell
# 1. 手动测试 router 脚本（不启动 Kimi CLI）
echo '{"prompt":"帮我编译项目，有个 link error"}' | python ~/.kimi/skill-router/kimi_skill_router.py
# 期望输出 JSON，包含 hookSpecificOutput.inject_prompt

# 2. 运行自动测试脚本
cd ~/.kimi/skill-router
python test_hook_injection.py
# 期望：12 passed, 0 failed

# 3. 启动 Kimi CLI，发送 "帮我编译项目"
# AI 响应中应提到 "unreal-build-commands" skill
```

---

## 二、Claude Code 适配方案

### 2.1 现状

Claude Code 是闭源二进制（`claude.exe`），**没有开放 `UserPromptSubmit` hook**。无法像 Kimi CLI 那样打源码补丁注入 skill。

### 2.2 可行方案：System Prompt 动态注入（Wrapper 脚本）

**思路**：写一个 PowerShell wrapper，在调用 `claude` 之前，根据用户输入匹配 skill，然后通过 `--append-system-prompt` 或 `--system-prompt-file` 注入。

**限制**：
- 只能**启动时**注入一次，无法做到每轮对话动态匹配。
- 适合单轮 / 非交互式调用（`claude -p "..."`）。

**Wrapper 示例** (`claude-router.ps1`)：

```powershell
# 读取用户输入（第 1 个参数或管道）
$prompt = $args -join " "
if (-not $prompt) {
    Write-Host "Usage: claude-router.ps1 <prompt>"
    exit 1
}

# 调用 router 脚本获取匹配 skill
$routerInput = @{prompt = $prompt} | ConvertTo-Json -Compress
$routerOutput = $routerInput | python "$env:USERPROFILE\.kimi\skill-router\kimi_skill_router.py"

# 提取 inject_prompt
$inject = ""
try {
    $parsed = $routerOutput | ConvertFrom-Json
    $inject = $parsed.hookSpecificOutput.inject_prompt
} catch {}

# 调用 Claude Code
if ($inject) {
    claude --append-system-prompt "$inject" -p "$prompt"
} else {
    claude -p "$prompt"
}
```

### 2.3 可行方案：CLAUDE.md 静态路由

在项目根目录创建 `.claude/CLAUDE.md`：

```markdown
# Skill Router Protocol

你在每次回复前，必须检查用户消息是否涉及以下领域。如果是，先读取对应 SKILL.md 再行动：

- 编译 / Build / UBT / Link Error → `D:\jiangheng\JHLocalSkill\...\unreal-build-commands\SKILL.md`
- P4 / Perforce / 提交 → `D:\jiangheng\JHLocalSkill\...\p4-workflow\SKILL.md`
- 搜索代码 / grep / glob → `D:\jiangheng\JHLocalSkill\...\codebase-search\SKILL.md`
- ...（按 skill 列表展开）
```

**优点**：每轮对话 AI 都能看到，不依赖 hook。
**缺点**：占用上下文 token，不能动态更新。

### 2.4 可行方案：Claude Code Skills 目录

Claude Code 支持 `~/.claude/skills/` 目录，结构与 Kimi CLI skill 类似（`SKILL.md`）。

**迁移步骤**：
1. 将 `D:\jiangheng\JHLocalSkill` 下的 skill 子目录**软链接**或**复制**到 `~/.claude/skills/`
2. 在 Claude Code 中使用 `/skill-name` 手动调用

**限制**：没有自动匹配，需要用户手动 `/skill-name` 或 AI 主动识别。

### 2.5 推荐组合

| 场景 | 推荐方案 |
|------|---------|
| 日常开发（主要用 Kimi CLI） | Kimi CLI Hook + 源码补丁（本指南第一节） |
| 偶尔用 Claude Code | `.claude/CLAUDE.md` 静态路由协议 |
| 需要脚本化调用 Claude | Wrapper 脚本 `--append-system-prompt` |
| 团队共享 skill | 同步到 `~/.claude/skills/` + `~/.kimi/skills/` 双份 |

---

## 三、一键安装脚本（Kimi CLI）

将以下脚本保存为 `install-kimi-hook-patch.ps1`，在新电脑上以管理员权限运行：

```powershell
#Requires -RunAsAdministrator
$ErrorActionPreference = "Stop"

$sitePackages = "$env:APPDATA\uv\tools\kimi-cli\Lib\site-packages"
$runnerPy     = "$sitePackages\kimi_cli\hooks\runner.py"
$kimisoulPy   = "$sitePackages\kimi_cli\soul\kimisoul.py"

if (-not (Test-Path $runnerPy)) {
    Write-Error "Kimi CLI not found at $sitePackages. Install kimi-cli first."
}

# Patch runner.py
$runnerSrc = Get-Content $runnerPy -Raw
$oldRunner = @"
                if hook_output.get(""permissionDecision"") == ""deny"":
                    return HookResult(
                        action=""block"",
                        reason=str(hook_output.get(""permissionDecisionReason"", """")),
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
                        reason=str(hook_output.get(""permissionDecisionReason"", """")),
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

if ($runnerSrc.Contains("inject_prompt")) {
    Write-Host "runner.py already patched."
} else {
    $runnerSrc = $runnerSrc.Replace($oldRunner, $newRunner)
    Set-Content $runnerPy $runnerSrc -Encoding UTF8
    Write-Host "runner.py patched."
}

# Patch kimisoul.py
$kimisoulSrc = Get-Content $kimisoulPy -Raw
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

            user_message = Message(role=""user"", content=user_input)
"@

if ($kimisoulSrc.Contains("Inject hook stdout into context")) {
    Write-Host "kimisoul.py already patched."
} else {
    $kimisoulSrc = $kimisoulSrc.Replace($oldKimisoul, $newKimisoul)
    Set-Content $kimisoulPy $kimisoulSrc -Encoding UTF8
    Write-Host "kimisoul.py patched."
}

Write-Host "Done. Restart Kimi CLI to apply changes."
```

---

## 四、自动测试脚本

`~/.kimi/skill-router/test_hook_injection.py`

运行方式：

```powershell
cd ~/.kimi/skill-router
python test_hook_injection.py
```

测试覆盖：
1. Router JSON 输出格式（3 个场景）
2. Router 无匹配返回空
3. Runner 解析 inject_prompt unwrap
4. KimiSoul 注入逻辑模拟
5. Block 阻止注入模拟
6. 源码补丁存在性检查

---

## 五、维护 Checklist

- [ ] 新增 skill 后更新 `skill_index_cache.json` 和 `skill_triggers_enhanced.json`
- [ ] 修改触发词后运行索引生成脚本
- [ ] Kimi CLI 升级后**必须重新打补丁**（`pip/uv upgrade` 会覆盖 site-packages）
- [ ] 定期运行 `python test_hook_injection.py` 验证 pipeline
- [ ] 关注 Kimi CLI 官方更新日志，若原生支持 `inject_prompt` 可移除本地补丁

---

## 六、故障排查

| 现象 | 原因 | 解决 |
|------|------|------|
| AI 不读取 skill | hook stdout 未被注入 | 检查 runner.py / kimisoul.py 补丁是否存在 |
| router 脚本无输出 | 索引文件缺失 | 确保 `skill_index_cache.json` 存在 |
| 补丁后 Kimi CLI 崩溃 | 补丁应用错误 | 恢复源码备份，重新运行安装脚本 |
| Claude Code 无法自动匹配 | 闭源无 hook | 使用 `.claude/CLAUDE.md` 或 wrapper 脚本 |
| 新 CLI 实例不触发 skill | `.pyc` 缓存未刷新 / 升级覆盖补丁 | 删除 `__pycache__` 或重新打补丁 |
| 匹配到的 skill 太少 | 阈值过高或规则缺失 | 降低阈值、补充触发词 |

---

## 七、多实例与 `.pyc` 缓存陷阱

### 现象
- 当前 CLI 实例能看到 "⚠️ 已推荐 skill: xxx"
- 新开 CLI 实例（同一台电脑）看不到 skill 推荐
- `hook_debug.log` 有记录，但 AI 不读取 skill

### 根因

Python 的 `.pyc` 字节码缓存。当 Kimi CLI 启动时：
1. Python 检查 `__pycache__/kimisoul.cpython-xxx.pyc` 是否存在且比 `.py` 新
2. 如果是，直接加载 `.pyc`，**跳过重新编译 `.py`**
3. 如果 `.pyc` 是在打补丁之前生成的，新实例会加载旧代码

### 快速修复

```powershell
# 删除缓存，强制 Python 重新编译补丁后的源码
Remove-Item "$env:APPDATA\uv\tools\kimi-cli\Lib\site-packages\kimi_cli\soul\__pycache__\kimisoul.cpython-313.pyc" -Force
Remove-Item "$env:APPDATA\uv\tools\kimi-cli\Lib\site-packages\kimi_cli\hooks\__pycache__\runner.cpython-313.pyc" -Force

# 然后重启新 CLI 实例
```

### 升级后补丁被覆盖

每次执行 `uv tool upgrade kimi-cli` 或 `pip install -U kimi-cli` 后：
1. site-packages 中的 `runner.py` 和 `kimisoul.py` 会被覆盖为官方原版
2. `.pyc` 缓存也会更新为官方原版
3. 必须重新打补丁 + 删除缓存

```powershell
# 一键恢复（运行安装脚本）
& "$env:USERPROFILE\.kimi\skills\JHLocalSkill\kimi-skill-router-setup\scripts\install-kimi-hook-patch.ps1"
```

---

## 八、词汇实时记录（Step 5）

Hook 已集成用户语言画像系统，每次对话自动提取关键词到 `~/.kimi/vocabulary_live.jsonl`。

### 配置
- **规则文件**：`~/.kimi/vocabulary_rules.json`
  - 4 类规则：action_verb, constraint, emotion, technical_entity
  - 直接编辑 JSON 即可新增/修改规则，无需重启 CLI
- **记录文件**：`~/.kimi/vocabulary_live.jsonl`
  - JSON Lines 格式，增量追加
  - 每条约 200 字节，长期运行不会膨胀
- **词典文件**：`~/.kimi/vocabulary_profile_full.md`
  - AI 定期读取 jsonl，归纳验证后合并到此处

### 记录格式
```json
{
  "timestamp": "2026-04-23T14:58:42",
  "session_marker": "9c447384",
  "token": "迁出",
  "raw": "迁出了 你再试试呢",
  "category": "action_verb",
  "confidence": 0.9,
  "verified": false,
  "misunderstood": false,
  "frequency": 1
}
```

### 定期归纳
当 `vocabulary_live.jsonl` 积累 ~20 条 `verified: false` 记录时，AI 读取并验证分类，合并到 `vocabulary_profile_full.md`。

---

## 九、补丁备份与自动恢复

### 备份机制

`install-kimi-hook-patch.ps1` 运行时会自动备份原文件：
```
runner.py.bak
kimisoul.py.bak
```

### 快速检查脚本

将以下脚本保存为 `check-patch.ps1`，随时检查补丁状态：

```powershell
$sitePackages = "$env:APPDATA\uv\tools\kimi-cli\Lib\site-packages"
$runner = "$sitePackages\kimi_cli\hooks\runner.py"
$kimisoul = "$sitePackages\kimi_cli\soul\kimisoul.py"

$ok = $true

if ((Get-Content $runner -Raw) -match "inject_prompt") {
    Write-Host "[OK] runner.py patched"
} else {
    Write-Host "[FAIL] runner.py NOT patched"
    $ok = $false
}

if ((Get-Content $kimisoul -Raw) -match "Inject hook stdout into context") {
    Write-Host "[OK] kimisoul.py patched"
} else {
    Write-Host "[FAIL] kimisoul.py NOT patched"
    $ok = $false
}

if (-not $ok) {
    Write-Host "Run install-kimi-hook-patch.ps1 to fix."
}
```

运行方式：
```powershell
& "$env:USERPROFILE\.kimi\skills\JHLocalSkill\kimi-skill-router-setup\scripts\check-patch.ps1"
```
