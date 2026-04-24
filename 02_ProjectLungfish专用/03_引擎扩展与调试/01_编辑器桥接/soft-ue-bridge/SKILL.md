---
name: soft-ue-bridge
description: SoftUEBridge MCP bridge plugin for UE5. Use when user wants Claude to directly control the UE editor — query Actors, modify properties, run PIE, compile Blueprints, read logs, capture screenshots, manipulate Blueprint graphs, DataTables, StateTrees, or any editor automation. Trigger when user mentions "bridge", "SoftUEBridge", "MCP", "UE工具调用", "从Claude操作UE", "query-level", "call-function", "get-logs", or asks Claude to perform editor operations directly.
tags: [SoftUEBridge, MCP, Editor-Automation, UE5, HTTP-Bridge, JSON-RPC]
---

# SoftUEBridge Workflow Skill

> Full plugin reference: `Main/Plugins/SoftUEBridge/SKILL.md`

---

## 何时使用

当用户希望 Claude 直接控制 UE 编辑器时激活此 skill：
- 查询/修改关卡 Actor 属性
- 读取 UE 运行时日志
- 操作 Blueprint 图（添加节点、连接引脚、编译）
- PIE 会话控制（启动/停止）
- 截图、截取 Viewport
- DataTable 行操作
- StateTree 结构修改
- 资产查询/创建/删除
- 类继承关系分析
- 运行 Python 脚本
- 触发编译/LiveCoding

---

## 前提条件

1. UE 编辑器已启动且 SoftUEBridge 插件已启用（`.uproject` 中 `"Enabled": true`）
2. `USoftUEBridgeSubsystem` 已自动启动 HTTP 服务器（默认 `127.0.0.1:8080`）
3. MCP 客户端（如 `soft-ue-cli`）已连接或 Claude 通过 MCP 直接访问
4. 运行 `soft-ue-cli` 时，工作目录必须是包含 `.uproject` 的目录；本仓库应使用 `Main/`
5. `soft-ue-cli` 是终端命令，不是 slash command；应直接在 shell 中执行 `soft-ue-cli ...`

验证服务器状态：
```bash
cd Main
soft-ue-cli check-setup
```
推荐优先使用 `check-setup` 做首轮验证，因为它会同时检查插件文件、`.uproject` 启用状态和 bridge 可达性。

**本仓库实测：**
- 在仓库根目录执行会报 `Plugin not found` 和 `No .uproject file found`
- 在 `Main/` 下执行 `soft-ue-cli check-setup` 可正常返回 `Plugin files found`、`SoftUEBridge enabled`、`Bridge server reachable`

---

## 已验证的 CLI 用法

以下命令已在 `Main/` 目录实测通过：

```bash
cd Main

soft-ue-cli check-setup
soft-ue-cli project-info
soft-ue-cli get-logs --lines 20 --filter error
soft-ue-cli query-asset --query "BP_*" --class Blueprint --path /Game --limit 10
```

已验证结果：
- `project-info` 可返回项目名、引擎版本、插件版本、bridge 端口
- `get-logs --filter error` 可直接读取最近的 UE 错误/警告日志
- `query-asset` 可按 `/Game` 路径、类名和通配符列出蓝图资产

若端口自动发现异常，可显式指定：

```bash
soft-ue-cli --server http://127.0.0.1:8080 project-info
```
  ## 工具选择原则

  ### 优先使用 `run-python-script` 的场景
  - **数据读取**：资产属性查询、CDO 读取、AssetRegistry 扫描
  - **批处理**：批量遍历资产、批量读取 modifier/属性
  - **CDO 属性查询**：读取 Blueprint 生成类的默认对象属性（如 GE 的 DurationPolicy、Modifiers）

  Python 脚本模板（CDO 查询）：
  ```python
  import unreal, json
  registry = unreal.AssetRegistryHelpers.get_asset_registry()
  assets = registry.get_assets_by_path('/Game/Path', recursive=True)
  results = []
  for a in assets:
      pkg = str(a.package_name)
      name = str(a.asset_name)
      bp = unreal.load_asset(pkg)
      if isinstance(bp, unreal.Blueprint):
          cdo = unreal.get_default_object(bp.generated_class())
          val = cdo.get_editor_property('SomeProperty')
          results.append({'name': name, 'val': str(val)})
  print(json.dumps(results, ensure_ascii=False))

  注意：AssetData 没有 object_path 属性，正确路径拼法是 package_name + '.' + asset_name。

  不可被 Python 替代、必须用专用 tool 的场景

  - Blueprint 图节点操作：add-graph-node、connect-graph-pins、remove-graph-node
  - Viewport 截图：capture-viewport
  - 实时日志读取：get-logs
  - LiveCoding 触发：trigger-live-coding
  - PIE 控制：pie-session

  ---
  工具名确认原则

  严禁猜测工具名。 遇到 Unknown tool 错误或不确定工具是否存在时：
  1. 先用 tools/list 拿完整工具列表
  2. 从列表中找匹配的工具名
  3. 查阅插件源码确认参数：Main/Plugins/SoftUEBridge/Source/SoftUEBridge[Editor]/Private/Tools/ 下各 .cpp 文件

  ---

## CLI JSON 参数陷阱

当命令包含 JSON 参数时（尤其是 `add-graph-node --properties ...`、`set-node-property ...`、`run-python-script` 的复杂入参），`soft-ue-cli` 在 PowerShell / cmd 下可能因为引号和转义被 shell 改写，表现为：

- `--properties must be valid JSON`
- 实际发到 bridge 的字段缺失
- 看起来是工具失败，实际是 CLI 参数解析失败

优先建议：

1. 简单命令继续使用 `soft-ue-cli`
2. 一旦遇到 JSON 参数转义问题，不要反复和 shell quoting 对抗
3. 直接改用 JSON-RPC 调 bridge

直接 JSON-RPC 的好处：

- 跳过 `soft-ue-cli` 的命令行参数解析层
- 请求体是结构化 JSON，复杂对象更稳定
- 适合 Blueprint 图编辑这类深层嵌套参数

PowerShell 示例：

```powershell
$body = @{
  jsonrpc = '2.0'
  id = '1'
  method = 'tools/call'
  params = @{
    name = 'add-graph-node'
    arguments = @{
      asset_path = '/Game/MyBP'
      graph_name = 'EventGraph'
      node_class = 'K2Node_CallFunction'
      properties = @{
        FunctionReference = @{
          MemberParent = '/Game/000_GlobalSettings/FunctionLibraries/BFL_DTUtils.BFL_DTUtils_C'
          MemberName = 'FindEatEffect'
          bSelfContext = $false
        }
      }
    }
  }
} | ConvertTo-Json -Depth 20

Invoke-RestMethod -Uri 'http://127.0.0.1:8086/bridge' -Method Post -ContentType 'application/json' -Body $body
```

本仓库实测结论：

- `soft-ue-cli` 适合无 JSON 或浅层参数调用
- 遇到复杂 JSON 入参失败时，应直接用 JSON-RPC 调 `http://127.0.0.1:<port>/bridge`
- 端口以 `Main/.soft-ue-bridge/instance.json` 或 `soft-ue-cli project-info` 返回值为准

---

## 常用工具速查

### 查询关卡 Actor
```json
{
  "method": "tools/call",
  "params": {
    "name": "query-level",
    "arguments": {
      "actor_filter": "BP_Enemy*",
      "world_type": "pie",
      "include_components": true,
      "include_transform": true
    }
  }
}
```

### 读取 Actor 属性
```json
{
  "name": "get-property",
  "arguments": { "actor_name": "BP_Player_0", "property_name": "Health" }
}
```

### 写入属性
```json
{
  "name": "set-property",
  "arguments": { "actor_name": "BP_Player_0", "property_name": "Health", "value": "100" }
}
```

### 调用函数
```json
{
  "name": "call-function",
  "arguments": { "actor_name": "BP_Player_0", "function_name": "RespawnPlayer" }
}
```

### 获取日志
```json
{
  "name": "get-logs",
  "arguments": { "count": 100, "category": "LogAngelScript", "filter": "Error" }
}
```

### 编译 Blueprint
```json
{
  "name": "compile-blueprint",
  "arguments": { "asset_path": "/Game/Blueprints/BP_MyActor" }
}
```

---

## 新增工具的标准流程

1. 在 `Source/SoftUEBridge[Editor]/Private/Tools/<Category>/` 下创建 `.h` + `.cpp`
2. 继承 `UBridgeToolBase`，实现四个虚函数
3. 在对应模块的 `StartupModule()` 中 `Registry.RegisterToolClass<UMyTool>()`
4. P4 add 新文件 → 用 `unreal-cpp-workflow` skill 编译验证
5. 更新此 SKILL.md 工具清单

---

## 端口冲突排查

```bash
# 查看 instance.json 确认实际端口
cat ~/.soft-ue-bridge/instance.json

# 自定义端口（编辑器启动前设置）
set SOFT_UE_BRIDGE_PORT=8090
```

若服务器未启动，在编辑器 Output Log 中搜索 `SoftUEBridge` 查看启动状态。也可通过 Blueprint/C++ 手动调用 `USoftUEBridgeSubsystem::StartServer()`。
