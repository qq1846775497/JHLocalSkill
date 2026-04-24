---
name: codex-setup
description: Codex CLI (OpenAI) 个人级 Skill 系统安装与配置指南。涵盖 .codex/skills/ 目录、SKILL.md 格式、$skill-name 调用语法、config.toml 配置。当用户在 Codex CLI 中配置 skill、询问 skills 目录位置、skill 不生效时使用。
tags: [Codex-CLI, OpenAI, Skills, Setup, Windows, MacOS, Linux]
---

# Codex CLI Skill 系统安装指南

## 目标

在 Codex CLI 中配置个人级 Skill 系统，支持通过 `$skill-name` 语法显式调用，让 Codex 读取 JHLocalSkill 库中的专业技能。

## 核心机制

Codex CLI（OpenAI）支持项目级 `.codex/skills/` 目录，skill 文件格式与 Claude Code 兼容。

## 目录结构

```
项目根目录/               # 或任意工作目录
├── .codex/
│   ├── skills/           # Skill 目录（项目级）
│   │   ├── JHLocalSkill/ # Skill 主库（链接或复制）
│   │   └── my-skill/
│   │       └── SKILL.md
│   └── config.toml       # Codex CLI 配置（可选）
├── src/
└── ...
```

Codex CLI **只支持项目级 skills**，不支持全局用户级配置。需要在每个工作目录下创建 `.codex/skills/`。

## 1. 安装 Codex CLI

```bash
# 全局安装
npm install -g @openai/codex

# 验证安装
codex --version
```

## 2. 配置 Skills 目录

### 方案 A：每个项目单独链接（推荐）

```powershell
# 在项目根目录下创建 .codex/skills/
New-Item -ItemType Directory -Force -Path ".\.codex\skills"

# 创建符号链接指向 JHLocalSkill
New-Item -ItemType SymbolicLink `
  -Path ".\.codex\skills\JHLocalSkill" `
  -Target "D:\jiangheng\JHLocalSkill"
```

```bash
# macOS/Linux
mkdir -p ./.codex/skills
ln -s /path/to/JHLocalSkill ./.codex/skills/JHLocalSkill
```

### 方案 B：全局配置（通过 config.toml）

Codex CLI 1.32.0+ 支持 `~/.codex/config.toml`：

```toml
[skills]
# 全局 skills 目录路径
paths = [
  "D:\\jiangheng\\JHLocalSkill",
  "C:\\Users\\<USER>\\.codex\\skills"
]
```

> ⚠️ **注意**：全局配置支持可能因版本而异，建议先测试项目级配置。

## 3. SKILL.md 格式规范

Codex CLI 的 SKILL.md 格式与 Claude Code **完全兼容**：

```markdown
---
name: skill-name
description: 一句话描述
tags: [tag1, tag2]
---

# 标题

正文内容...
```

### 关键字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | string | Skill 标识，用于 `$skill-name` 调用 |
| `description` | string | 描述，用于自动匹配 |
| `tags` | string[] | 标签 |

## 4. 调用方式

### 显式调用

```
$skill-name
```

或：

```
Use the $skill-name skill to help me with ...
```

### 示例

```
$kimi-setup 如何配置 Kimi CLI 的 skill router？

$unreal-build-commands 编译项目报错 LNK2019
```

### 自动调用

Codex 会分析用户输入，如果与 skill 的 `description` 匹配，会自动提示是否加载 skill。

> ⚠️ **注意**：自动调用不如显式 `$skill-name` 可靠。

## 5. 与 JHLocalSkill 的集成

### 推荐工作流

```powershell
# 1. 在 UE 项目目录创建 .codex/skills/
$projectRoot = "D:\jiangheng\JiangHengWork\Main"
New-Item -ItemType Directory -Force -Path "$projectRoot\.codex\skills"

# 2. 链接 JHLocalSkill
New-Item -ItemType SymbolicLink `
  -Path "$projectRoot\.codex\skills\JHLocalSkill" `
  -Target "D:\jiangheng\JHLocalSkill"

# 3. 验证
cd $projectRoot
codex
# 在 Codex 中输入：$kimi-setup
```

### 多项目共享

如果有多个项目需要相同的 skills，可以：

1. **创建中央 skill 仓库**：`D:\Skills\JHLocalSkill`
2. **每个项目链接到中央仓库**
3. **或使用 `~/.codex/config.toml` 配置全局路径**

## 6. 验证

```bash
# 启动 Codex CLI
codex

# 检查已加载的 skills（如果支持）
# 不同版本命令可能不同，尝试：
/codex skills list
/skills

# 测试显式调用
$kimi-setup 如何配置 hook？

# 测试自动匹配
帮我配置 Kimi CLI 的 skill router
```

## 7. 注意事项

| 限制 | 说明 |
|------|------|
| **只支持项目级** | 默认情况下 skills 必须放在 `.codex/skills/` 下 |
| **显式调用优先** | `$skill-name` 是最可靠的调用方式 |
| **格式兼容** | 与 Claude Code 的 YAML frontmatter 格式完全兼容 |
| **无 Hook 机制** | 不支持 UserPromptSubmit hook |

## 与 Kimi CLI / Claude Code 的差异对比

| 特性 | Kimi CLI | Claude Code | Codex CLI |
|------|----------|-------------|-----------|
| 注入机制 | Hook 强制注入 | 隐式/显式引用 | 显式 `$skill-name` |
| 可靠性 | 100% 触发 | 概率性匹配 | 显式调用 100% |
| 目录结构 | `~/.kimi/skills/` | `~/.claude/skills/` | `.codex/skills/`（项目级） |
| 文件格式 | 纯 Markdown | YAML frontmatter + MD | YAML frontmatter + MD |
| 调用语法 | 无（自动） | `@skill-name` | `$skill-name` |
| 全局配置 | 支持 | 支持 | 部分支持（1.32.0+） |

## 迁移建议

如果同时使用多个平台：

1. **统一使用 YAML frontmatter 格式**（Codex/Claude 兼容）
2. **Kimi 端**：Hook 读取时跳过 frontmatter，只取 body
3. **Codex 端**：使用 `$skill-name` 显式调用关键 skill
4. **Claude 端**：使用 `@skill-name` 显式调用
