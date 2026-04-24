---
name: kimi-setup
description: Kimi CLI 个人级 Skill Router 安装与配置指南。涵盖 hook 配置、源码补丁、skill 目录设置、新电脑一键安装。当用户询问如何在 Kimi CLI 中配置 skill、router 不生效、换电脑迁移、安装 hook 时使用。
tags: [Kimi-CLI, Skill-Router, Hook, Setup, Windows, Migration]
---

# Kimi CLI Skill Router 安装指南

## 目标

在 Kimi CLI 中实现：用户每次发送消息前，自动匹配 JHLocalSkill 库中的 SKILL.md，并**强制注入**到 AI 上下文。

## 目录结构

```
~/.kimi/
├── config.toml              # Kimi CLI 主配置（含 hook）
├── skill-router/
│   ├── kimi_skill_router.py # Hook 主程序
│   ├── skill_index_cache.json
│   ├── skill_triggers_enhanced.json
│   ├── router_prompt.txt    # LLM 语义匹配 prompt
│   ├── .env                 # SILICONFLOW_API_KEY
│   └── test_hook_injection.py
├── skills/
│   └── JHLocalSkill/        # Skill 主库（树状结构）
├── vocabulary_rules.json    # 词汇分类规则
└── vocabulary_live.jsonl    # 用户语言画像记录
```

## 1. 安装 Kimi CLI

```powershell
# 方式 A：uv（推荐）
uv tool install kimi-cli

# 方式 B：pip
pip install kimi-cli
```

## 2. 配置 Hook

编辑 `~/.kimi/config.toml`：

```toml
[[hooks]]
event = "UserPromptSubmit"
command = "python C:\\Users\\<USERNAME>\\.kimi\\skill-router\\kimi_skill_router.py"
timeout = 70
```

将 `<USERNAME>` 替换为实际 Windows 用户名。

## 3. 放置 Router 脚本

将 `kimi_skill_router.py` 及配套文件放到 `~/.kimi/skill-router/`。

Router 脚本要求：
- 四层匹配：硬编码规则 → 触发词 → 描述 → LLM 兜底
- 纯本地，零 API 调用（仅兜底层可选调用 SiliconFlow）
- **输出 JSON 格式**：
  ```json
  {"hookSpecificOutput":{"inject_prompt":"⚠️ SKILL ROUTER\n..."}}
  ```

## 4. 打源码补丁（关键）

Kimi CLI 1.30.0 原生不支持将 hook stdout 注入 AI 上下文。必须修改两个源码文件。

### 补丁 A — runner.py

**路径**：`%APPDATA%\uv\tools\kimi-cli\Lib\site-packages\kimi_cli\hooks\runner.py`

在 `run_hook` 函数的 JSON 解析段之后，添加 `inject_prompt` unwrap：

```python
# Support inject_prompt: unwrap JSON so downstream sees plain text
inject_prompt = hook_output.get("inject_prompt")
if isinstance(inject_prompt, str) and inject_prompt.strip():
    stdout = inject_prompt
```

### 补丁 B — kimisoul.py

**路径**：`%APPDATA%\uv\tools\kimi-cli\Lib\site-packages\kimi_cli\soul\kimisoul.py`

在 `TurnBegin` 发送之后，添加 hook stdout 注入：

```python
# Inject hook stdout into context before processing the turn
for result in hook_results:
    if result.stdout.strip():
        await self._context.append_message(
            Message(
                role="user",
                content=[system_reminder(result.stdout.strip())],
            )
        )
```

> 这两个补丁不需要重新编译或重新安装 Kimi CLI，修改 `.py` 文件后立即生效。

### 一键安装脚本

运行 `install-kimi-hook-patch.ps1`（已包含备份和缓存清理）：

```powershell
& "$env:USERPROFILE\.kimi\skills\JHLocalSkill\01_通用\05_系统工具\kimi-setup\scripts\install-kimi-hook-patch.ps1"
```

## 5. 验证

```powershell
# 手动测试 router 脚本
echo '{"prompt":"帮我编译项目，有个 link error"}' | python ~/.kimi/skill-router/kimi_skill_router.py

# 运行自动测试
cd ~/.kimi/skill-router
python test_hook_injection.py

# 启动 Kimi CLI，发送 "帮我编译项目"
# AI 响应中应提到 "unreal-build-commands" skill
```

## 6. 词汇实时记录（可选增强）

Hook 已集成用户语言画像系统，每次对话自动提取关键词到 `~/.kimi/vocabulary_live.jsonl`。

- **规则文件**：`~/.kimi/vocabulary_rules.json`（4 类：动作动词、约束词、情绪信号、技术实体）
- **记录文件**：`~/.kimi/vocabulary_live.jsonl`（JSON Lines 格式，增量追加）

## 7. 故障排查

| 现象 | 原因 | 解决 |
|------|------|------|
| AI 不读取 skill | hook stdout 未被注入 | 检查 runner.py / kimisoul.py 补丁 |
| 新 CLI 实例不触发 | `.pyc` 缓存未刷新 | 删除 `__pycache__` 或重新打补丁 |
| 匹配 skill 太少 | 阈值过高或规则缺失 | 降低阈值、补充触发词 |
| Kimi CLI 升级后失效 | 补丁被覆盖 | 重新运行 install 脚本 |

## 维护 Checklist

- [ ] 新增 skill 后更新 `skill_index_cache.json` 和 `skill_triggers_enhanced.json`
- [ ] Kimi CLI 升级后**必须重新打补丁**
- [ ] 定期运行 `python test_hook_injection.py` 验证 pipeline
