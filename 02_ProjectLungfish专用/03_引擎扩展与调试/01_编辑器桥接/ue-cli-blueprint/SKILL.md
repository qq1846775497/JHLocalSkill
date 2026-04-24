---
name: ue-cli-blueprint
title: ue-cli.exe Blueprint Commands
description: 通过 ue-cli.exe 调用 SoftUEBridge 的 blueprint 能力，处理 Blueprint 查询与编译，作为蓝图排查和自动化操作的轻量入口。当用户需要查看 Blueprint 信息、确认函数或属性、触发编译、或先做低风险蓝图检查时使用。
tags: [UE-CLI, Blueprint, Compile, Editor-Automation, SoftUEBridge, UE5]
---

# ue-cli.exe Blueprint Commands

> Layer: Tier 3 (Workflow Skill)

**CRITICAL — 开始前先读取 [`../ue-cli-shared/SKILL.md`](../ue-cli-shared/SKILL.md)。**

## 适用场景

- “查一下这个 Blueprint 有哪些属性/函数”
- “编译这个蓝图”
- “确认某个蓝图路径是否有效”
- “先做轻量蓝图检查，再决定是否继续改图”

## 命令优先级

1. `ue-cli.bat blueprint query`
2. `ue-cli.bat blueprint compile`
3. `ue-cli.bat tools call`

## 命令示例

### 查询 Blueprint

```bash
./ue-cli.bat blueprint query --asset-path /Game/Blueprints/BP_MyActor --include-functions --include-properties
```

用于先确认路径、函数列表、属性列表，再决定是否进入更复杂的蓝图工具调用。

### 编译 Blueprint

```bash
./ue-cli.bat blueprint compile --asset-path /Game/Blueprints/BP_MyActor
```

适合在修改后快速验证是否存在明显编译问题。

## 使用原则

- 先查询，再编译，比盲目调用更稳
- 如果需要图节点级操作，转回 `SoftUEBridge` 相关工具并用 `tools call`
