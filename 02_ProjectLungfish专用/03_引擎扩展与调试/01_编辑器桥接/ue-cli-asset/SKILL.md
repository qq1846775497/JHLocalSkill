---
name: ue-cli-asset
title: ue-cli.exe Asset Commands
description: 通过 ue-cli.exe 调用 SoftUEBridge 的 asset 能力，处理资产查询、按路径或类型筛选，以及把资产定位作为后续编辑前的探测步骤。当用户需要查资产、确认资产路径、按类型筛选资源、或在动手前先摸清内容浏览器对象时使用。
tags: [UE-CLI, Assets, Content-Browser, Query, SoftUEBridge, UE5]
---

# ue-cli.exe Asset Commands

> Layer: Tier 3 (Workflow Skill)

**CRITICAL — 开始前先读取 [`../ue-cli-shared/SKILL.md`](../ue-cli-shared/SKILL.md)。**

## 适用场景

- “查一下这个路径下有哪些资产”
- “找某类资产”
- “确认资源路径和类型”
- “先定位资产，再决定后续编辑或引用分析”

## 命令优先级

1. `ue-cli.bat asset query`
2. `ue-cli.bat tools call`

## 命令示例

```powershell
ue-cli.bat asset query --asset-path /Game/Blueprints --asset-type Blueprint
ue-cli.bat asset query --name BP_Player
```

## 何时退回 tools call

- 需要 `find-references`、`open-asset`、`save-asset` 等未封装能力
- 需要服务端原始返回结构

## 使用原则

- 先缩小资产范围，再执行更具体的桥接工具
- 把 `asset query` 视为编辑前探测步骤，而不是最终工作流终点
