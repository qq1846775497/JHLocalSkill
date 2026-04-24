---
name: robomerge-v3
title: RoboMerge v3 自动化 P4 Merge 技术参考
description: RoboMerge v3 技术参考文档。RoboMerge 是一套运行在 Node.js 上的 Perforce 多分支自动化合并系统，负责监控分支变更、按配置规则自动将提交合并到下游分支，并在冲突时通知相关人员介入处理。
tags: [Perforce, Automation, Merge, RoboMerge, P4, BranchManagement]
---

# RoboMerge v3 技术参考文档

> **目标读者：** 需要理解 RoboMerge 工作原理、或以 Python 复刻核心逻辑的工程师。

## 快速导航

| 主题 | 文件 |
|------|------|
| 完整配置字段参考 | [references/config-schema.md](references/config-schema.md) |
| P4 命令封装与解析 | [references/p4-commands.md](references/p4-commands.md) |
| 合并流程（含流程图） | [references/merge-workflow.md](references/merge-workflow.md) |
| 冲突解决全流程 | [references/conflict-resolution.md](references/conflict-resolution.md) |
| Python 复刻指南 | [references/python-replication-guide.md](references/python-replication-guide.md) |

---

## 1. 系统架构概述

RoboMerge v3 是一个运行在 Node.js/TypeScript 上的 Perforce 自动化合并服务。

### 进程层级

```
watchdog.ts          ← 守护进程，监控主进程崩溃并自动重启
  └── robo.ts        ← 主进程，初始化 P4 上下文 + Web 服务器
        └── GraphBot ← 每个 botname 一个，管理整个分支图
              ├── NodeBot(Main)         ← 监控 Main 分支
              ├── NodeBot(Release-5.0)  ← 监控 Release 分支
              │     └── EdgeBot(Main→Release-5.0) ← 执行合并
              └── ...
```

### 关键源文件

| 文件 | 行数 | 职责 |
|------|------|------|
| `src/robo/nodebot.ts` | 2356 | 分支监控、tick 循环、冲突管理 |
| `src/robo/edgebot.ts` | 1348 | 合并执行、Stomp/Shelf/Skip |
| `src/robo/targets.ts` | 950 | `#robomerge` 描述解析、目标计算 |
| `src/robo/graph.ts` | 936 | 分支图结构、路由计算 |
| `src/robo/notifications.ts` | 1105 | Slack/Email 通知 |
| `src/robo/gate.ts` | 1028 | CIS 质量门禁 |
| `src/robo/branchdefs.ts` | 622 | 配置 Schema 定义 |
| `src/robo/conflicts.ts` | 452 | 冲突持久化管理 |
| `src/common/perforce.ts` | 1500+ | P4 命令封装、ztag 解析 |
| `src/robo/roboserver.ts` | — | Web 服务器 + REST API |

---

## 2. 配置系统（三级结构）

配置文件路径：`./data/{BOTNAME}.branchmap.json`

### 三级配置层次

```
BotConfig（全局）
  └── branches[].NodeOptions（分支级）
        └── edgeProperties[target].EdgeOptions（边级，可选）
```

详细字段说明见 → [references/config-schema.md](references/config-schema.md)

### 最小配置示例

```json
{
  "defaultStreamDepot": "UE5",
  "isDefaultBot": true,
  "checkIntervalSecs": 30,
  "branches": [
    {
      "name": "Main",
      "streamDepot": "UE5",
      "streamName": "Main",
      "flowsTo": ["Release-5.0"]
    },
    {
      "name": "Release-5.0",
      "streamDepot": "UE5",
      "streamName": "Release-5.0"
    }
  ]
}
```

---

## 3. 合并流程摘要

```
[NodeBot.tick()]
    ↓ 查询 p4 changes
[新变更 CL]
    ↓ p4 describe → 解析 #robomerge 命令
[计算合并目标]
    ↓ 遍历 EdgeBot
[p4 integrate → p4 resolve]
    ├─ 无冲突 → p4 submit → 更新 lastCL
    ├─ 冲突   → 创建 blockage → 发通知 → 阻塞 edge
    └─ manual → p4 shelve → 通知作者手动解决
```

完整流程图和步骤说明见 → [references/merge-workflow.md](references/merge-workflow.md)

---

## 4. #robomerge 命令语法

在提交描述中写入，控制 RoboMerge 的合并行为：

| 语法 | 含义 |
|------|------|
| `#robomerge Main` | 额外合并到 Main |
| `#robomerge -Release-5.0` | 跳过到 Release-5.0 的自动合并 |
| `#robomerge !Main` | Null merge 到 Main（告知 P4 已合并，不改变内容） |
| `#robomerge #manual` | 生成 Shelf，不自动提交 |
| `#robomerge ignore` | 完全忽略，不产生任何合并 |
| `#robomerge deadend` | 同 ignore（旧语法） |
| `#robomerge null` | 所有自动合并目标均做 null merge |

---

## 5. 冲突处理（三种解决方式）

| 方式 | 适用条件 | 操作 |
|------|----------|------|
| **Stomp** | 所有冲突文件均为二进制（assets） | 用目标分支版本覆盖源分支变更 |
| **Shelf** | 包含文本文件冲突，需人工解决 | 创建 P4 shelf，通知作者在 P4V 手动解决 |
| **Skip** | 该变更不需要合并 | 跳过此 CL，继续处理后续变更 |

详细流程见 → [references/conflict-resolution.md](references/conflict-resolution.md)

---

## 6. Gate 质量门禁

Edge 配置 `lastGoodCLPath` 后，RoboMerge 只合并 CI 验证过的变更：

```json
{
  "lastGoodCLPath": "//UE5/Main/Engine/Build/LastGoodCL.txt",
  "pauseCISUnlessAtGate": true
}
```

Gate 文件内容为一行数字（CL 号），RoboMerge 定期读取，只集成 ≤ 该 CL 的变更。

---

## 7. REST API 快速参考

默认端口：3000

| Endpoint | 说明 |
|----------|------|
| `GET /allbots` | 所有 bot 状态 |
| `GET /api/:bot/:branch` | 分支状态 |
| `POST /api/:bot/:branch/stomp` | 执行 Stomp |
| `POST /api/:bot/:branch/shelf` | 创建 Shelf |
| `POST /api/:bot/:branch/skip` | 跳过冲突 |
| `POST /api/:bot/pause` | 暂停 bot |
| `POST /api/:bot/unpause` | 恢复 bot |
| `POST /api/:bot/:branch/reconsider` | 重新处理变更 |

---

## 8. 启动命令

```bash
# 开发模式
node dist/robo/watchdog.js -botname=MYBOTNAME -devMode

# 生产模式
node dist/robo/watchdog.js -botname=BOT1,BOT2 -externalUrl=https://robomerge.example.com
```

完整 CLI 参数见 → [references/config-schema.md#cli-arguments](references/config-schema.md)
