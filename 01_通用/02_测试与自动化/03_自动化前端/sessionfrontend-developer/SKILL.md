---
name: sessionfrontend-developer
title: SessionFrontend 自动化测试前端
description: Unreal Engine Developer 模块 `SessionFrontend`，把 Session Browser、Session Console、Automation、Trace Control 和 Screen Comparison 汇总到同一个前端窗口。当用户需要分析 `Engine/Source/Developer/SessionFrontend`、排查自动化测试工具入口、理解远程 session 发现与日志命令链路，或判断问题应该落在 `SessionFrontend` 还是 `AutomationWindow`/`SessionServices`/`ScreenShotComparison` 时使用。
tags: [Engine, UE5, Automation, Session-Services, Slate, Developer-Tool, Trace]
---

# SessionFrontend 自动化测试前端

> Layer: Tier 3 (Module Documentation)
> Parent: [引擎源码](../../../SKILL.md)

<memory category="core-rules">
- `SessionFrontend` 是自动化测试与远程调试的前端聚合层，不是测试执行内核
- 真正的自动化执行逻辑主要在 `AutomationController` 和 `AutomationWindow`，这里只负责把它们挂到 Tab
- 如果问题涉及 session 发现、实例选择、远程日志、控制台命令派发、截图对比入口或 Trace 控制，优先读这里
- 如果问题涉及测试用例枚举、执行队列、结果汇总或 screenshot compare 算法，转去对应外部模块，不要误判为 `SessionFrontend` 自身逻辑
</memory>

<memory category="code-locations">
- 模块入口: `Engine/Source/Developer/SessionFrontend/Private/SessionFrontendModule.cpp`
- 主容器: `Engine/Source/Developer/SessionFrontend/Private/Widgets/SSessionFrontend.cpp`
- Session Browser: `Engine/Source/Developer/SessionFrontend/Private/Widgets/Browser/SSessionBrowser.cpp`
- Session Browser 树模型: `Engine/Source/Developer/SessionFrontend/Private/Models/SessionBrowserTreeItems.h`
- Session Console: `Engine/Source/Developer/SessionFrontend/Private/Widgets/Console/SSessionConsole.cpp`
- Console 命令注册: `Engine/Source/Developer/SessionFrontend/Private/Models/SessionConsoleCommands.h`
- 依赖声明: `Engine/Source/Developer/SessionFrontend/SessionFrontend.Build.cs`
</memory>

<memory category="common-patterns">
- 看自动化入口先从 `SSessionFrontend::HandleTabManagerSpawnTab` 开始，确认 Tab 是本模块自建还是外部模块创建
- 看远程日志链路先走 `Session Browser -> SessionManager 选中实例 -> SessionConsole::ReloadLog/HandleSessionManagerLogReceived`
- 看远程命令链路先走 `SSessionConsole::HandleCommandSubmitted -> SendCommand -> ISessionInstanceInfo::ExecuteCommand`
- 看 session 树分类先看 `SSessionBrowser::FilterSessions` 和 `AddInstanceItemToTree`
</memory>

## Overview

`SessionFrontend` 是 Unreal Engine 的 Developer 模块，职责是把若干与远程 session 运维相关的工具集中到一个 Nomad Tab 里。

它自己维护的核心只有两块：
- `Session Browser`: 浏览、分组并选择活跃 session/instance
- `Session Console`: 聚合选中实例的日志、做过滤并向实例发送控制台命令

它同时把以下外部能力挂进统一工作台：
- `AutomationWindow`: 自动化测试面板
- `TraceTools`: Trace Control 面板
- `ScreenShotComparison`: 截图比对面板

这意味着它非常适合分析“自动化测试入口套件”的装配关系，但不适合直接承载测试执行细节。

## When To Use

适合在这些场景读取本目录：
- 用户提到 `Engine/Source/Developer/SessionFrontend`
- 想知道自动化测试页签是怎么被挂到 Session Frontend 里的
- 排查 Session Browser 选中实例后，Console 为什么没有日志或无法发命令
- 想梳理 Session Frontend 与 `SessionServices`、`AutomationWindow`、`TraceTools` 的职责边界
- 想修改 Session Frontend 的 Slate 布局、Tab 注册、Browser/Console 交互

不该只停留在这里的场景：
- 真正的 Automation Test 执行、过滤、结果树、队列调度
- 截图差异算法、基线管理
- Session 消息总线发现机制的底层实现
- Trace 数据采集或分析后端

## Architecture

```text
SessionFrontendModule
└── SSessionFrontend
    ├── Session Browser         -> SSessionBrowser
    ├── Session Console         -> SSessionConsole
    ├── Automation              -> AutomationWindowModule.CreateAutomationWindow(...)
    ├── Trace Control           -> TraceToolsModule.CreateTraceControlWidget(...)
    └── Screen Comparison       -> ScreenShotComparisonModule.CreateScreenShotComparison(...)
```

关键依赖在 `SessionFrontend.Build.cs` 中已经直接暴露出模块定位：
- 基础数据与消息面来自 `SessionServices`
- 自动化面板来自 `AutomationWindow`
- 截图比对来自 `ScreenShotComparison` 和 `ScreenShotComparisonTools`
- Trace 页来自 `TraceTools`

## Main Code Paths

### 1. 模块入口与总 Tab

`Private/SessionFrontendModule.cpp`

- `FSessionFrontendModule::StartupModule` 注册全局 Nomad Tab `SessionFrontend`
- `InvokeSessionFrontend` 可选激活某个子页签
- `SpawnSessionFrontendTab` 创建 `SSessionFrontend`

如果问题是“为什么菜单里能打开 Session Frontend”或“外部模块如何调起某个子页签”，从这里看。

### 2. 前端容器与页签装配

`Private/Widgets/SSessionFrontend.cpp`

- `InitializeControllers` 从 `SessionServices`、`TargetDeviceServices`、`ScreenShotComparisonTools` 拉控制器
- `Construct` 注册 5 个子页签并定义左右布局
- `HandleTabManagerSpawnTab` 决定每个页签是本模块自建，还是调用外部模块工厂

自动化测试相关的关键事实：
- `AutomationPanel` 页签不是 `SessionFrontend` 自己实现
- 它在打开页签时动态加载 `AutomationController` 和 `AutomationWindow`
- `SessionFrontend` 只负责把 `AutomationWindowModule.CreateAutomationWindow(...)` 产物挂进 DockTab

所以如果你在排查“自动化测试逻辑套件”，第一步要先判断问题是“入口装配错误”还是“AutomationWindow 内部错误”。

### 3. Session Browser

`Private/Widgets/Browser/SSessionBrowser.cpp`

Browser 的职责是把 `ISessionManager` 给出的 session/instance 组织成树并同步选择状态。

重要函数：
- `ReloadSessions`: 重拉 session 列表并重新监听 `OnInstanceDiscovered`
- `FilterSessions`: 只保留本地 owner 或 standalone session，并重建树
- `AddInstanceItemToTree`: 把当前实例挂到 `This Application`，其他实例挂到所属 session
- `HandleSessionTreeViewSelectionChanged`: UI 选择回写给 `ISessionManager`

调试 Browser 时要注意：
- session 可见性依赖 `-messaging`
- UI 树和 `ISessionManager` 双向同步，靠 `IgnoreSessionManagerEvents`/`updatingTreeExpansion` 避免回环
- 默认会优先选中当前应用实例，但 `UnrealInsights` 例外

### 4. Session Console

`Private/Widgets/Console/SSessionConsole.cpp`

Console 的职责是消费已选实例的日志，并把命令广播给这些实例。

重要函数：
- `ReloadLog(true)`: 从 `SessionManager->GetSelectedInstances()` 全量重建日志堆
- `HandleSessionManagerLogReceived`: 实时接收新日志，只在实例已选中时显示
- `HandleFilterChanged`: 只重跑过滤，不重拉基础日志
- `SendCommand`: 对所有已选实例调用 `ExecuteCommand`

调试 Console 时要注意：
- 没有选中实例时，主内容禁用，并显示 overlay 提示
- 过滤失败的日志不会丢，仍保存在 `AvailableLogs`
- 保存日志和复制日志只是 UI 层输出，不影响 session 本身

## Analysis Workflow

当用户让你“分析 SessionFrontend 自动化测试相关逻辑”时，建议按这个顺序：

1. 先看 `SessionFrontend.Build.cs`
   目的：确定哪些能力是本模块拥有，哪些只是依赖装配
2. 再看 `SSessionFrontend.cpp`
   目的：确认具体页签和外部模块工厂的绑定关系
3. 如果问题在 session 发现或实例选择，转 `SSessionBrowser.cpp`
4. 如果问题在日志、命令派发或实例联调，转 `SSessionConsole.cpp`
5. 如果问题落在自动化执行本身，跳去 `AutomationWindow` / `AutomationController`

## Debugging Notes

常见误判：
- “Automation 面板在 Session Frontend 里” 不等于 “Automation 逻辑在 SessionFrontend 里”
- “Console 没日志” 往往是实例未选中，或远端实例未通过 messaging 暴露
- “想改测试结果展示” 大概率不是这里，而是 `AutomationWindow`

快速定位问题类型：

| 现象 | 优先检查 |
|------|----------|
| Session Frontend 打不开 | `SessionFrontendModule.cpp` 的 Tab 注册 |
| Automation 页签空白/失效 | `SSessionFrontend::HandleTabManagerSpawnTab` 与 `AutomationWindow` 模块加载 |
| Browser 里看不到实例 | `ISessionManager` 数据源、`-messaging`、`FilterSessions` 筛选 |
| Console 无法发命令 | `GetSelectedInstances()` 是否为空，`SendCommand` 是否被调用 |
| Console 新日志不刷新 | `HandleSessionManagerLogReceived` 与 Filter 条件 |

## Code Locations

**Primary Files**
- `Engine/Source/Developer/SessionFrontend/SessionFrontend.Build.cs`
- `Engine/Source/Developer/SessionFrontend/Public/ISessionFrontendModule.h`
- `Engine/Source/Developer/SessionFrontend/Private/SessionFrontendModule.cpp`
- `Engine/Source/Developer/SessionFrontend/Private/Widgets/SSessionFrontend.h`
- `Engine/Source/Developer/SessionFrontend/Private/Widgets/SSessionFrontend.cpp`
- `Engine/Source/Developer/SessionFrontend/Public/Widgets/Browser/SSessionBrowser.h`
- `Engine/Source/Developer/SessionFrontend/Private/Widgets/Browser/SSessionBrowser.cpp`
- `Engine/Source/Developer/SessionFrontend/Private/Models/SessionBrowserTreeItems.h`
- `Engine/Source/Developer/SessionFrontend/Private/Widgets/Console/SSessionConsole.h`
- `Engine/Source/Developer/SessionFrontend/Private/Widgets/Console/SSessionConsole.cpp`
- `Engine/Source/Developer/SessionFrontend/Private/Models/SessionConsoleCommands.h`

