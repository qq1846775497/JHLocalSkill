# JHLocalSkill — 个人级 AI 技能库

跨平台 AI CLI 工具（Kimi CLI / Claude Code / Codex CLI / OpenCode）通用的专业技能库，覆盖 Unreal Engine 5 开发、项目管理、数据配置、测试构建等场景。

## 快速开始

### 选择你的平台

| 平台 | 定位 | 推荐安装方式 |
|------|------|-------------|
| **Kimi CLI** | 主力开发工具，强制 skill 注入 | [kimi-setup](01_通用/05_系统工具/kimi-setup/SKILL.md) |
| **Claude Code** | 辅助编码，显式 skill 调用 | [claude-setup](01_通用/05_系统工具/claude-setup/SKILL.md) |
| **Codex CLI** | OpenAI 官方 CLI，显式 skill 调用 | [codex-setup](01_通用/05_系统工具/codex-setup/SKILL.md) |
| **OpenCode** | 多模型切换，本地模型支持 | [opencode-setup](01_通用/05_系统工具/opencode-setup/SKILL.md) |

### 一键安装（Kimi CLI — 推荐）

```powershell
# 1. 克隆仓库
git clone https://github.com/YOUR_USERNAME/JHLocalSkill.git D:\jiangheng\JHLocalSkill

# 2. 安装 Kimi CLI
uv tool install kimi-cli

# 3. 配置 skill 目录（创建符号链接）
New-Item -ItemType SymbolicLink `
  -Path "$env:USERPROFILE\.kimi\skills\JHLocalSkill" `
  -Target "D:\jiangheng\JHLocalSkill"

# 4. 安装 hook 补丁
& "D:\jiangheng\JHLocalSkill\01_通用\05_系统工具\kimi-setup\scripts\install-kimi-hook-patch.ps1"
```

## 技能分类

### 01_通用

| Skill | 描述 |
|-------|------|
| `kimi-setup` | Kimi CLI Skill Router 安装与配置 |
| `claude-setup` | Claude Code Skill 系统配置 |
| `codex-setup` | Codex CLI Skill 系统配置 |
| `opencode-setup` | OpenCode 配置与 agents.md |
| `kimi-skill-router-setup` | Skill Router 完整安装指南（含补丁代码） |
| `unreal-build-commands` | UBT 编译命令与构建系统 |
| `unreal-build-fix` | 构建错误诊断与修复 |
| `unreal-cpp-workflow` | UE C++ 开发工作流 |
| `codebase-search` | 代码库高效搜索 |
| `excel-query` | Excel 数据查询 |
| `xlsx-row-copy` | Excel 行复制 |
| `feishu-doc-reader` | 飞书文档读取 |
| `p4-workflow` | Perforce 版本控制工作流 |
| `pr` | P4 changelist 描述生成 |
| `branch-manager` | 分支管理面板操作 |
| `gauntlet-test-automation` | Gauntlet 测试自动化 |
| `automated-perf-testing` | 性能测试自动化 |
| `sessionfrontend-developer` | UE SessionFrontend 开发 |
| `engine-modifications` | UE 引擎修改 |
| `engine-pcg-plugin` | PCG 插件 |
| `engine-slate-runtime` | Slate UI 运行时 |
| `ue-blueprint-reflection` | Blueprint 反射系统 |
| `localization-string-table` | 本地化 StringTable |
| `native-class-derivation` | 派生类规则（禁止直接使用 UE 原生类） |

### 02_ProjectLungfish专用

| Skill | 描述 |
|-------|------|
| `asset-export` | 资产全量导出管线 |
| `blueprint-migration` | Blueprint 迁移到 C++ |
| `flowgraph-audit` | FlowGraph 审计与修复 |
| `flowgraph-edit` | FlowGraph 编辑 |
| `damage-flow-graph-authoring` | 伤害流图节点创作 |
| `entity-tag-modifier` | 实体 Tag 与属性修改 |
| `entry-cpp` | 装备词条系统程序实现 |
| `entry-design` | 装备词条策划设计 |
| `equip-entry-pool-config` | 装备词条池配置 |
| `configuration-tools` | 策划工具 |
| `precheckin` | Excel 导出 DataTable |
| `runtime-grid-fix` | RuntimeGrid 批量修复 |
| `core-redirects-debug` | CoreRedirects 调试 |
| `pie-error-fix-notify` | PIE 错误修复与通知 |
| `slateim-debug-tool` | SlateIM 调试工具 |
| `soft-ue-bridge` | SoftUEBridge MCP 桥接 |
| `ue-cli-asset` | ue-cli 资产查询 |
| `ue-cli-automation` | ue-cli 自动化测试 |
| `ue-cli-blueprint` | ue-cli Blueprint 查询 |
| `ue-cli-remote-control` | ue-cli Remote Control |
| `ue-cli-runtime` | ue-cli 运行时查询 |
| `ue-cli-shared` | ue-cli 共享基础 |
| `ue-cli-development` | ue-cli 开发 |
| `ue-design-research` | UE 架构设计研究 |
| `ue-dev-orchestrator` | UE 开发自动化编排 |
| `ue-software-architecture` | UE 软件工程规范 |
| `unreal-game-sync` | Unreal Game Sync |
| `plbehaviortreesm-editor-context` | PLBehaviorTreeSM 编辑器 |

## 目录结构

```
JHLocalSkill/
├── 01_通用/                    # 通用技能
│   ├── 01_UE引擎与源码/
│   ├── 02_测试与自动化/
│   ├── 03_工具链与DevOps/
│   ├── 04_项目管理与协作/
│   └── 05_系统工具/            # setup skills 在此
├── 02_ProjectLungfish专用/     # ProjectLungfish 专用
│   ├── 01_资产与内容管线/
│   ├── 02_数据配置与策划/
│   ├── 03_引擎扩展与调试/
│   ├── 04_测试与构建/
│   ├── 05_系统与插件/
│   ├── 06_软件工程规范/
│   ├── 07_开发工作流编排/
│   └── 08_问题排查与研究/
├── .gitignore
└── README.md
```

## 设计原则

1. **一份源码，多平台使用** — 所有 SKILL.md 采用兼容格式（YAML frontmatter + Markdown），可被 Kimi/Claude/Codex 同时读取
2. **树状结构，清晰分类** — 按领域和项目分层，便于查找和维护
3. **触发词驱动** — 每个 skill 包含明确的触发关键词，便于自动匹配
4. **渐进式增强** — 从硬编码规则到 LLM 语义匹配，多层 fallback

## 贡献

本库为个人使用，不接收外部 PR。但可以参考目录结构和 skill 设计模式，创建自己的技能库。

## 许可证

MIT
