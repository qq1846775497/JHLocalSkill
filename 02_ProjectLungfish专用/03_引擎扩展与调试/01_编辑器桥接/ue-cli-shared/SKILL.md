---
name: ue-cli-shared
title: ue-cli Shared Setup and Safety
description: ue-cli 的共享基础：SoftUEBridge 前提检查、项目目录发现、instance.json 定位、check-setup 用法、tools list 探测、tools call 兜底、以及常见连接失败排查。当用户第一次使用 ue-cli, SoftUEBridge 是否连通、遇到端口或 instance.json 问题、或准备通过 CLI 调用 UE bridge 时使用。
tags: [UE-CLI, SoftUEBridge, MCP, Setup, JSON-RPC, UE5]
---

# ue-cli.bat Shared Setup and Safety

> Layer: Tier 3 (Workflow Skill)

## 快速入口

```bash
./ue-cli.bat check-setup
```

## 何时使用

- 首次使用 `./ue-cli.bat`
- 需要确认 `SoftUEBridge` 是否已启动
- 需要定位 `.soft-ue-bridge/instance.json`
- 命令调用失败，不确定是连接问题还是工具参数问题

## 前提条件

1. UE 编辑器已启动
2. `SoftUEBridge` 插件已启用
3. 项目根目录下存在 `.soft-ue-bridge/instance.json`

## 标准 SOP

### Step 1: 先检查连通性

```bash
./ue-cli.bat check-setup
```

必须先确认：

- 当前项目目录是否正确
- `instance.json` 是否存在
- `/bridge` 健康检查是否通过
- `tools/list` 是否返回成功

**如果 `check-setup` 失败（UE 编辑器未启动或 SoftUEBridge 未连接），直接中止当前任务**，并告知用户：

> ❌ SoftUEBridge 连接失败。请确保：
> 1. UE 编辑器已启动
> 2. SoftUEBridge 插件已启用
> 3. 等待编辑器完全加载后重试

### Step 2: 先探测工具，再调用

```bash
./ue-cli.bat tools list
```

不要凭印象猜工具名和参数结构。先列出工具，再选择 domain 命令或 `tools call`。

### Step 3: 优先使用 domain 命令，缺失时退回通用调用

```bash
./ue-cli.bat tools call --name query-level --args '{"actor_filter":"BP_Enemy*"}'
```

domain 命令适合高频操作；非高频或尚未封装的工具，一律用 `tools call`。

## 常见问题

## 批处理输出为空

**问题**: 使用 `cmd.exe /c "ue-cli.bat ..."` 执行时，输出为空或不显示结果。

**原因**: Windows 批处理通过 cmd.exe 间接调用时，输出无法正确捕获。

**解决**: 直接调用 `./ue-cli.bat`，不使用 `cmd.exe /c` 包装：

```bash
# 直接调用（正确）
./ue-cli.bat check-setup

# 或通过 Tools 目录调用 ue-cli.exe
./Tools/ue-cli/bin/ue-cli.exe check-setup
```

## 找不到 instance.json

- 当前工作目录不是项目根目录
- 编辑器未启动 bridge
- 插件未正常初始化

优先处理方式：

```bash
./ue-cli.bat check-setup --project-dir <ProjectRoot>
```

## health 成功但 tools/call 失败

- 工具名错误
- 参数 JSON 结构错误
- UE 侧工具执行失败

排查顺序：

1. `./ue-cli.bat tools list`
2. 确认 tool name
3. 缩小参数到最小必需集

## 使用原则

- 先 `check-setup`，再做任何写操作或复杂调用
- 先 `tools list`，再补封装命令
- 让 `SoftUEBridge` 成为工具行为的单一事实来源
