---
name: ue-cli-runtime
title: ue-cli.exe Runtime Commands
description: 通过 ue-cli.exe 调用 SoftUEBridge 的 runtime 能力，处理关卡 Actor 查询、运行时日志读取，以及基于运行世界状态的排查。当用户说查询关卡、看 Actor、读 UE 日志、排查 PIE 运行时问题、或需要先确认场景状态再继续操作时使用。
tags: [UE-CLI, Runtime, Actor, Logs, PIE, SoftUEBridge]
---

# ue-cli.exe Runtime Commands

> Layer: Tier 3 (Workflow Skill)

**CRITICAL — 开始前先读取 [`../ue-cli-shared/SKILL.md`](../ue-cli-shared/SKILL.md)。**

## 适用场景

- “查一下关卡里有哪些 Actor”
- “看看 PIE 里有没有这个对象”
- “读最近的错误日志”
- “先确认运行时状态再决定下一步”

## 命令优先级

1. `ue-cli.bat runtime query-level`
2. `ue-cli.bat runtime get-logs`
3. `ue-cli.bat tools call`

## 命令示例

### 查询关卡

```powershell
ue-cli.bat runtime query-level --actor-filter “BP_Enemy*” --world-type pie --include-components --include-transform
```

适合先确认对象是否存在、位于哪个世界、是否带有目标组件。

### 获取日志

```powershell
ue-cli.bat runtime get-logs --count 200 --category LogAngelScript --filter Error
```

适合定位运行时报错、脚本错误、工具执行失败原因。

## 何时退回 tools call

- 需要 `runtime` 类里尚未封装的 bridge 工具
- 需要更完整的参数结构
- 想先验证某个新工具是否值得加 wrapper
