---
name: kimi-wrapper-setup
description: >
  Kimi CLI Skill 自动发现 Wrapper 安装器。
  解决 Kimi CLI 不支持递归加载深层 skill 目录的已知限制（issue #1894）。
  换电脑、新环境、重装系统时，运行本 skill 的脚本一键配置 PowerShell wrapper，
  使树状结构的 JHLocalSkill 技能库能被正确加载。
trigger_when: >
  用户说"换电脑"、"迁移"、"新环境"、"安装 skill wrapper"、"重装"、
  "skill 没加载"、"怎么让 Kimi 扫到深层 skill"、"issue 1894"。
---

# Kimi CLI Skill Wrapper 安装器

## 问题

Kimi CLI 只扫描 `~/.kimi/skills/` 的**直接子目录**（`*/SKILL.md`），不递归进入深层目录。

你的 `JHLocalSkill` 是 3-4 级树状结构：
```
~/.kimi/skills/JHLocalSkill/
├── 01_通用/
│   └── 05_代码库探索/
│       └── codebase-search/
│           └── SKILL.md     ← Kimi CLI 扫不到
```

## 解决方案

PowerShell Wrapper 脚本：在启动 `kimi` 时，自动递归扫描 `JHLocalSkill` 下所有包含 `SKILL.md` 的目录，并以 `--skills-dir` 参数注入。

## 换电脑 / 新环境 部署步骤

### Step 1: 复制 JHLocalSkill 目录

把 `C:\Users\{旧用户}\.kimi\skills\JHLocalSkill` 复制到新电脑的 `C:\Users\{新用户}\.kimi\skills\JHLocalSkill`。

> 树状结构本身不需要变，只复制即可。

### Step 2: 运行安装脚本

在新电脑的 PowerShell 中执行（**不需要先启动 kimi**，这是鸡生蛋问题，脚本独立运行）：

```powershell
# 方式 A：直接运行脚本（推荐）
& "$env:USERPROFILE\.kimi\skills\JHLocalSkill\01_通用\05_系统工具\kimi-wrapper-setup\scripts\Install-SkillWrapper.ps1"

# 方式 B：如果脚本路径太长，先 cd 进去
cd "$env:USERPROFILE\.kimi\skills\JHLocalSkill\01_通用\05_系统工具\kimi-wrapper-setup\scripts"
.\Install-SkillWrapper.ps1
```

### Step 3: 生效

```powershell
# 当前窗口立即生效
. $PROFILE

# 或新开 PowerShell 窗口
```

### Step 4: 验证

```powershell
kimi
```

看到 `[kimi-wrapper] Auto-loaded X skills from JHLocalSkill` 即成功。

---

## 脚本功能

`scripts/Install-SkillWrapper.ps1` 会：
1. 检测原始 `kimi.exe` 路径
2. 检测 `JHLocalSkill` 是否存在
3. 在 PowerShell profile 中追加 wrapper 函数
4. 备份原 profile（`*.backup`）
5. 支持重复运行（幂等，不会重复追加）

## 跳过 Wrapper

临时禁用：
```powershell
$env:KIMI_NO_SKILL_WRAPPER = 1
kimi
```

永久禁用：编辑 `$PROFILE`，删除 `# Kimi CLI Skill Auto-Discovery Wrapper` 到函数结尾的代码块。
