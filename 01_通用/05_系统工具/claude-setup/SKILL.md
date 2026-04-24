---
name: claude-setup
description: Claude Code 个人级 Skill 系统安装与配置指南。涵盖 skills 目录结构、SKILL.md 规范、隐式/显式调用、跨项目共享配置。当用户在 Claude Code 中配置 skill、询问 skills 目录位置、skill 不生效时使用。
tags: [Claude-Code, Skills, Setup, Anthropic, MCP]
---

# Claude Code Skill 系统安装指南

## 目标

在 Claude Code 中配置个人级 Skill 系统，支持自动触发和显式引用，让 Claude 自动读取 JHLocalSkill 库中的专业技能。

## 核心机制

Claude Code 支持两种 Skill 系统：

1. **Skills** — 个人项目级 `.claude/skills/` 目录，自动被上下文引用
2. **MCP** — Model Context Protocol，外部服务连接（本指南不涉及）

## 目录结构

```
~/.claude/
├── skills/                  # 全局技能目录（~ = %USERPROFILE% on Windows）
│   ├── JHLocalSkill/        # Skill 主库
│   │   ├── 01_通用/
│   │   ├── 02_ProjectLungfish专用/
│   │   └── ...
│   └── my-custom-skill/
│       └── SKILL.md
```

## 1. 安装 Claude Code

```bash
# macOS/Linux
npm install -g @anthropic-ai/claude-code

# Windows（通过 WSL 或 npm）
npm install -g @anthropic-ai/claude-code
```

## 2. 配置 Skills 目录

Claude Code 会自动读取以下位置的 skills：

- **项目级**：`项目根目录/.claude/skills/`
- **用户级**：`~/.claude/skills/`

### 推荐方案：用户级全局配置

```powershell
# Windows
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.claude\skills"
# 创建软链接（或复制/克隆 skill 库）
New-Item -ItemType SymbolicLink -Path "$env:USERPROFILE\.claude\skills\JHLocalSkill" -Target "D:\jiangheng\JHLocalSkill"
```

```bash
# macOS/Linux
mkdir -p ~/.claude/skills
ln -s /path/to/JHLocalSkill ~/.claude/skills/JHLocalSkill
```

## 3. SKILL.md 格式规范

Claude Code 的 SKILL.md 使用 **YAML frontmatter** + Markdown body：

```markdown
---
name: skill-name
description: 一句话描述（用于匹配触发）
tags: [tag1, tag2]
---

# 标题

正文内容，支持：
- Markdown 格式
- 代码块
- 表格
- 图片（`![alt](assets/image.png)`）
- 外部脚本引用（见下方）
```

### 关键字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | string | Skill 唯一标识，用于显式调用 |
| `description` | string | 简短描述，Claude 用此匹配用户请求 |
| `tags` | string[] | 标签分类 |

### 高级字段（Claude 特有）

```yaml
---
name: advanced-skill
description: 高级示例
references:
  - type: script
    path: ./scripts/generate_report.py
    description: 生成报告脚本
  - type: file
    path: ./templates/template.md
    description: 模板文件
assets:
  - ./assets/diagram.png
---
```

| 字段 | 说明 |
|------|------|
| `references` | 外部文件/脚本引用，Claude 可读取执行 |
| `assets` | 图片等静态资源 |

## 4. 调用方式

### 隐式调用（自动）

用户发送消息时，Claude 自动分析 `description` 和 `tags`，决定是否加载 skill。

> ⚠️ **注意**：Claude 的自动匹配是**概率性**的，不如 Kimi 的 Hook 强制注入可靠。建议结合显式调用使用。

### 显式调用

```
@skill-name
```

或：

```
Claude, use the skill-name skill to ...
```

### 在项目级 skills 中调用

在项目目录下创建 `.claude/skills/`：

```
my-project/
├── .claude/
│   └── skills/
│       └── project-specific-skill/
│           └── SKILL.md
├── src/
└── ...
```

项目级 skills 优先于用户级，适合团队共享。

## 5. 与 JHLocalSkill 的集成

### 方案 A：直接链接（推荐）

```powershell
# 将 JHLocalSkill 链接到 Claude skills 目录
New-Item -ItemType SymbolicLink `
  -Path "$env:USERPROFILE\.claude\skills\JHLocalSkill" `
  -Target "D:\jiangheng\JHLocalSkill"
```

### 方案 B：包装目录（需要选择性暴露）

```powershell
# 创建包装目录，只暴露部分 skills
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.claude\skills\JHCore"

# 为每个需要的 skill 创建符号链接
$skills = @("kimi-setup", "claude-setup", "unreal-build-commands")
foreach ($skill in $skills) {
    New-Item -ItemType SymbolicLink `
      -Path "$env:USERPROFILE\.claude\skills\JHCore\$skill" `
      -Target "D:\jiangheng\JHLocalSkill\01_通用\05_系统工具\$skill"
}
```

## 6. 验证

启动 Claude Code 后：

```
# 检查已加载的 skills
/claude skills list

# 测试显式调用
@kimi-setup 如何配置 skill router？

# 测试隐式触发
帮我配置 Kimi CLI 的 hook
```

## 7. 注意事项

| 限制 | 说明 |
|------|------|
| **自动匹配不强制** | Claude 可能不加载 skill，取决于描述匹配度 |
| **描述是关键** | `description` 必须准确包含触发关键词 |
| **无 Hook 机制** | Claude 不支持 UserPromptSubmit hook，无法强制注入 |
| **Windows 路径** | 使用 PowerShell，注意反斜杠转义 |

## 与 Kimi CLI 的差异对比

| 特性 | Kimi CLI | Claude Code |
|------|----------|-------------|
| 注入机制 | Hook 强制注入 | 隐式/显式引用 |
| 可靠性 | 100% 触发 | 概率性匹配 |
| 目录结构 | `~/.kimi/skills/` | `~/.claude/skills/` |
| 文件格式 | 纯 Markdown | YAML frontmatter + Markdown |
| 外部引用 | 不支持（纯文本） | 支持脚本/文件/图片 |
| 调用语法 | 无（自动） | `@skill-name` |
| 跨平台 | Windows 为主 | macOS/Linux/Windows |

## 迁移建议

如果同时使用 Kimi CLI 和 Claude Code：

1. **保持一份 SKILL.md 源文件**（YAML frontmatter 格式，Claude 兼容）
2. **Kimi 端**：通过 Hook 读取并注入，忽略 frontmatter
3. **Claude 端**：直接读取，解析 frontmatter
4. **避免两份维护**：skill 内容一致，仅调用方式不同
