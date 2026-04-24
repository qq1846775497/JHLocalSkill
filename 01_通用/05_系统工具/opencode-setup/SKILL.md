---
name: opencode-setup
description: OpenCode 个人级配置与 Skill 系统安装指南。涵盖 opencode.jsonc 配置、agents.md 上下文注入、本地模型 Ollama 集成、多提供商配置。当用户在 OpenCode 中配置 skill、询问 agents.md 用法、切换模型、设置本地模型时使用。
tags: [OpenCode, Agents, Setup, Ollama, Local-Model, Multi-Provider]
---

# OpenCode 配置与 Skill 系统安装指南

## 目标

在 OpenCode 中配置个人级 Skill 系统，支持通过 `agents.md` 上下文注入和多提供商模型切换，让 OpenCode 读取 JHLocalSkill 库中的专业技能。

## 核心机制

OpenCode 不同于传统 CLI，它使用：

1. **`agents.md`** — 项目级上下文文件，自动注入到 AI 上下文
2. **`opencode.jsonc`** — 全局配置文件，定义模型、API key、自定义命令
3. **`/model` 命令** — 实时切换不同提供商的模型
4. **自定义命令** — 通过配置定义快捷指令

## 目录结构

```
~/.config/opencode/          # 全局配置目录
├── opencode.jsonc           # 主配置文件
└── ...

项目根目录/
├── agents.md                # 项目级上下文（类似 skill，但为单文件）
├── .opencode/               # OpenCode 项目级配置（可选）
└── ...
```

## 1. 安装 OpenCode

```bash
# 通过 npm
npm install -g opencode

# 或通过 bun
bun install -g opencode

# 验证
opencode --version
```

## 2. 配置 opencode.jsonc

编辑 `~/.config/opencode/opencode.jsonc`：

```jsonc
{
  // 默认模型
  "model": "openai/gpt-4o",
  
  // API Keys（从环境变量读取，不要硬编码）
  "api_keys": {
    "openai": "${OPENAI_API_KEY}",
    "anthropic": "${ANTHROPIC_API_KEY}",
    "google": "${GOOGLE_API_KEY}"
  },
  
  // 本地模型配置（Ollama）
  "local_model": {
    "enabled": true,
    "base_url": "http://localhost:11434",
    "model": "codellama:13b"
  },
  
  // 自定义命令
  "custom_commands": {
    "skill": {
      "description": "加载指定 skill 到上下文",
      "prompt": "请读取并应用以下 skill 的内容：{{args}}"
    }
  }
}
```

### 环境变量设置（Windows PowerShell）

```powershell
# 添加到 $PROFILE，永久生效
[System.Environment]::SetEnvironmentVariable("OPENAI_API_KEY", "sk-...", "User")
[System.Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY", "sk-ant-...", "User")
```

## 3. agents.md — Skill 替代方案

OpenCode 没有传统意义上的 skill 目录，而是使用 **单文件 `agents.md`** 作为项目级上下文。

### 创建 agents.md

在项目根目录创建 `agents.md`：

```markdown
# ProjectLungfish 开发助手

## 可用技能

### 1. UE 构建系统
- **触发词**: 编译、build、UBT、link error、C2065
- **文件**: `01_通用/05_系统工具/unreal-build-commands/SKILL.md`
- **内容摘要**: UBT 编译命令、项目文件生成、Development/Shipping 配置

### 2. P4 工作流
- **触发词**: p4、perforce、checkout、changelist、submit
- **文件**: `01_通用/04_项目管理与协作/01_P4工作流/p4-workflow/SKILL.md`

### 3. Skill Router 配置
- **触发词**: skill、router、hook、kimi setup
- **文件**: `01_通用/05_系统工具/kimi-setup/SKILL.md`

## 项目结构

```
Main/
├── Source/
│   └── ProjectLungfish/
├── Content/
├── Plugins/
└── ...
```

## 编码规范

- 禁止直接使用 UE 原生组件类，必须使用 PL 派生版本
- GAS 架构：Attribute → Ability → GameplayEffect
```

### agents.md 的局限性

| 限制 | 说明 |
|------|------|
| **单文件** | 无法像 Kimi/Claude 那样分目录管理多个 skill |
| **手动维护** | 需要手动汇总所有 skill 的摘要 |
| **无自动触发** | OpenCode 不会自动分析 agents.md 中的触发词 |
| **项目级** | 每个项目需要独立的 agents.md |

## 4. 自定义命令实现 Skill 加载

由于 OpenCode 不支持自动 skill 匹配，可以通过**自定义命令**实现显式加载：

### 方案 A：读取 skill 文件

在 `opencode.jsonc` 中配置：

```jsonc
{
  "custom_commands": {
    "load-skill": {
      "description": "读取 JHLocalSkill 中的指定 skill",
      "prompt": "请读取文件 D:\\jiangheng\\JHLocalSkill\\{{args}}\\SKILL.md 的内容，并在后续对话中应用这些规则。"
    }
  }
}
```

使用方式：

```
/load-skill 01_通用/05_系统工具/kimi-setup
```

### 方案 B：通过 wrapper 脚本

创建一个 PowerShell wrapper，在启动 OpenCode 前读取 skill：

```powershell
# opencode-with-skill.ps1
$skillPath = $args[0]
if ($skillPath) {
    $content = Get-Content "D:\jiangheng\JHLocalSkill\$skillPath\SKILL.md" -Raw
    $env:OPENCODE_INITIAL_CONTEXT = $content
}
opencode
```

### 方案 C：agents.md 生成器

编写脚本自动生成 agents.md：

```python
# generate_agents_md.py
import os
import glob
import re

SKILL_ROOT = "D:\\jiangheng\\JHLocalSkill"

def extract_skill_info(skill_md_path):
    with open(skill_md_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 提取 YAML frontmatter
    match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
    if match:
        frontmatter = match.group(1)
        name = re.search(r'^name:\s*(.+)$', frontmatter, re.M)
        desc = re.search(r'^description:\s*(.+)$', frontmatter, re.M)
        return {
            'name': name.group(1).strip() if name else 'Unknown',
            'description': desc.group(1).strip() if desc else '',
            'path': skill_md_path.replace(SKILL_ROOT + '\\', '').replace('\\', '/')
        }
    return None

skills = []
for skill_md in glob.glob(f"{SKILL_ROOT}/**/SKILL.md", recursive=True):
    info = extract_skill_info(skill_md)
    if info:
        skills.append(info)

# 生成 agents.md
with open('agents.md', 'w', encoding='utf-8') as f:
    f.write("# JHLocalSkill 技能库\n\n")
    for skill in skills:
        f.write(f"## {skill['name']}\n")
        f.write(f"- **描述**: {skill['description']}\n")
        f.write(f"- **路径**: `{skill['path']}`\n\n")
```

## 5. 模型切换

OpenCode 支持实时切换模型：

```
# 切换到 OpenAI
/model openai/gpt-4o

# 切换到 Anthropic
/model anthropic/claude-3-5-sonnet

# 切换到本地 Ollama
/model ollama/codellama:13b

# 切换到 Google
/model google/gemini-pro
```

### Ollama 本地模型配置

```bash
# 1. 安装 Ollama
# https://ollama.com/download

# 2. 拉取模型
ollama pull codellama:13b
ollama pull llama3:8b

# 3. 启动 Ollama 服务（默认 http://localhost:11434）
ollama serve

# 4. 在 OpenCode 中切换
/model ollama/codellama:13b
```

## 6. 与 JHLocalSkill 的集成

### 推荐工作流

```powershell
# 1. 在 UE 项目根目录创建 agents.md
cd D:\jiangheng\JiangHengWork\Main

# 2. 运行生成脚本（定期更新）
python D:\jiangheng\JHLocalSkill\tools\generate_agents_md.py

# 3. 启动 OpenCode
opencode

# 4. 在对话中使用自定义命令
/load-skill 01_通用/05_系统工具/unreal-build-commands
```

### agents.md 内容建议

```markdown
# ProjectLungfish 开发上下文

## 项目信息
- **引擎**: Unreal Engine 5.4
- **项目路径**: D:\jiangheng\JiangHengWork\Main
- **源码**: Main/Source/ProjectLungfish/

## 可用技能库

### 构建与编译
- **路径**: `01_通用/05_系统工具/unreal-build-commands/SKILL.md`
- **用途**: UBT 编译命令、链接错误修复

### P4 版本控制
- **路径**: `01_通用/04_项目管理与协作/01_P4工作流/p4-workflow/SKILL.md`
- **用途**: checkout、changelist、submit

### 数据配置
- **路径**: `02_ProjectLungfish专用/02_数据配置与策划/03_策划工具/ConfigurationTools/SKILL.md`
- **用途**: Excel 导出、DataTable 配置

## 编码规范
- [规范详见: 01_通用/05_系统工具/ue-software-architecture/SKILL.md]
```

## 7. 验证

```bash
# 启动 OpenCode
opencode

# 测试模型切换
/model openai/gpt-4o

# 测试自定义命令（如果配置了）
/load-skill 01_通用/05_系统工具/kimi-setup

# 检查 agents.md 是否生效
# agents.md 内容应自动出现在系统提示中
```

## 8. 注意事项

| 限制 | 说明 |
|------|------|
| **无自动 skill 匹配** | OpenCode 不会自动分析目录中的 skill 文件 |
| **agents.md 为单文件** | 需要手动维护或脚本生成 |
| **无 Hook 机制** | 不支持 UserPromptSubmit hook |
| **自定义命令有限** | 相比 Kimi/Claude 的自动注入，需要更多手动操作 |

## 与 Kimi CLI / Claude Code / Codex CLI 的差异对比

| 特性 | Kimi CLI | Claude Code | Codex CLI | OpenCode |
|------|----------|-------------|-----------|----------|
| 注入机制 | Hook 强制注入 | 隐式/显式引用 | 显式 `$skill-name` | agents.md 静态注入 |
| 可靠性 | 100% 触发 | 概率性匹配 | 显式调用 100% | 100%（静态） |
| 目录结构 | `~/.kimi/skills/` | `~/.claude/skills/` | `.codex/skills/` | `agents.md`（单文件） |
| 文件格式 | 纯 Markdown | YAML frontmatter + MD | YAML frontmatter + MD | Markdown |
| 调用语法 | 无（自动） | `@skill-name` | `$skill-name` | 无（agents.md 自动） |
| 模型切换 | 不支持 | 不支持 | 不支持 | `/model` 实时切换 |
| 本地模型 | 不支持 | 不支持 | 不支持 | Ollama 支持 |

## 迁移建议

OpenCode 的设计理念与其他三个 CLI 不同，更适合作为**多模型探索工具**使用：

1. **日常使用**：Kimi CLI（强制 skill 注入，最可靠）
2. **特定任务**：Claude Code / Codex CLI（显式 skill 调用）
3. **模型对比**：OpenCode（快速切换不同模型，比较输出质量）
4. **本地离线**：OpenCode + Ollama（无网络时）

如果需要在 OpenCode 中使用 JHLocalSkill：

1. **定期运行生成脚本**更新 agents.md
2. **在 agents.md 中维护常用 skill 的摘要**
3. **使用自定义命令**实现显式 skill 加载
