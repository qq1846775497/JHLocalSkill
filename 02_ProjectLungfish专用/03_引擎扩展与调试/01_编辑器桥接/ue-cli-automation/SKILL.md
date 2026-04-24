---
name: ue-cli-automation
title: ue-cli Automation Test Runner
description: |
  自动化单元测试快速验证工具：通过 ue-cli automation run-tests 触发 BuildGraph，
  编译 Editor 后用编辑器 binary（-ExecCmds 模式）直接运行 UE Automation 单元测试。
  不使用 Gauntlet，不启动游戏进程，纯 in-process 测试。
  当用户提到以下任意场景时激活：
  "添加了测试用例"、"需要快速验证"、"验一下"、"跑一下测试"、
  "run unit test"、"触发 automation"、"BuildGraph 测试"、
  "PLAutomationCenter"、"RunUAT"、"验证代码改动"、"预提交验证"、
  "ue-cli automation"、"单元测试"。
tags: [UE-CLI, Automation, BuildGraph, UnitTest, RunUAT, Verification, Testing]
---

# ue-cli Automation Test Runner

> Layer: Tier 3 (Workflow Skill)

**CRITICAL — 本 skill 通过 ue-cli 调用 RunUAT BuildGraph，不依赖 SoftUEBridge，无需先 check-setup。**
**测试运行方式：编辑器 binary `-ExecCmds "Automation RunTests ...;Quit"`，不启动游戏进程，不用 Gauntlet。**

## 适用场景

- 添加或修改测试用例（`.spec.cpp`）后快速验证
- 修改 C++ / AngelScript / Blueprint 后的预提交单元测试验证
- 完整 UE Automation 框架测试套件运行

---

## 标准命令（编译 + 跑所有单元测试）

```bash
# 编译 Editor 然后跑单元测试（默认过滤器 Project.）
./ue-cli.bat automation run-tests
```

等价于手动调用：
```
Engine\Build\BatchFiles\RunUAT.bat BuildGraph
  -Script=Main/Build/PLAutomationCenter.xml
  -Target="Run Tests"
  -set:ProjectName=ProjectLungfish
  -set:AutomationTestFilter=Project.
```

---

## 跳过编译（已有最新 binary）

```bash
./ue-cli.bat automation run-tests --skip-compile
```

---

## 指定测试模块

```bash
# 只跑 Gameplay 模块的测试
./ue-cli.bat automation run-tests --filter "Project.Gameplay."

# 跳过编译 + 指定模块
./ue-cli.bat automation run-tests --skip-compile --filter "Project.Gameplay."
```

---

## 带 HTML 报告输出

```bash
./ue-cli.bat automation run-tests --report-output D:\MainDev\Main\TestResults
```

---

## 验证命令（不实际执行，打印 RunUAT 调用）

```bash
./ue-cli.bat automation run-tests --dry-run
./ue-cli.bat automation run-tests --skip-compile --filter "Project.Gameplay." --dry-run
```

---

## 参数速查

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--project-name` | `ProjectLungfish` | 与 .uproject 文件名一致 |
| `--script` | `Main/Build/PLAutomationCenter.xml` | BuildGraph 脚本路径（相对 RootDir） |
| `--target` | `Run Tests` | BuildGraph Aggregate Target 名称 |
| `--filter` | `Project.` | Automation 测试过滤器 |
| `--max-duration` | `600` | 最大运行时间（秒） |
| `--report-output` | `` | 报告输出目录（空=不输出） |
| `--skip-compile` | `false` | 跳过编译，直接跑测试 |
| `--dry-run` | `false` | 只打印命令，不实际执行 |

---

## 何时主动调用

Claude 在以下情况应**主动建议或直接调用**此命令：

| 触发情况 | 推荐命令 |
|----------|----------|
| 用户新增 `.spec.cpp` 测试文件 | `run-tests`（编译 + 验证） |
| 修改游戏逻辑 C++ 或 AngelScript | `run-tests`（编译 + 测试） |
| 用户说「快速验证」「验一下」 | `run-tests --skip-compile`（跳过编译，快） |
| 用户说「跑 XXX 模块的测试」 | `run-tests --filter "Project.XXX."` |
| 用户说「只测不编译」 | `run-tests --skip-compile` |

---

## 标准验证工作流

```
1. 完成代码改动（C++ / AngelScript / Blueprint）
2. ./ue-cli.bat automation run-tests              ← 编译 + 全量单元测试
   # 或只测不编译（binary 已是最新）：
   ./ue-cli.bat automation run-tests --skip-compile
3. 测试全部通过 → 可提交
```

---

## BuildGraph 脚本位置

`Main/Build/PLAutomationCenter.xml` — 包含两个 Node：

| Node | 说明 |
|------|------|
| `Compile Editor` | 增量编译 ProjectLungfishEditor（`--skip-compile` 时跳过） |
| `Run Unit Tests` | 用编辑器 binary `-ExecCmds` 模式跑 UE Automation 单元测试（in-process，无 Gauntlet） |

## 测试运行原理

`Run Unit Tests` 节点等价于：
```
Engine\Binaries\Win64\UnrealEditor-Cmd.exe Main/ProjectLungfish.uproject
  -ExecCmds="Automation RunTests Project.;Quit"
  -unattended -nopause -log -NullRHI
```

- **不启动游戏进程**：全程在编辑器进程内执行
- **不用 Gauntlet**：无 SmokeTestGauntlet，无 EditorGame 角色
- **不需要游戏 binary**：只需 UnrealEditor-Cmd.exe
