---
name: ue-cli-remote-control
title: ue-cli Remote Control — UE Editor 函数直调
description: |
  通过 ue-cli remote-control 调用 UE Editor 内任意 UFUNCTION(BlueprintCallable) 函数或 CDO 方法。
  使用 UE Remote Control API（PUT /remote/object/call，端口 30010），独立于 SoftUEBridge。
  核心价值：SoftUEBridge 不可用时的后备通道（如 CI Unattended 构建、-game 模式、编辑器未挂载 bridge 时）；
  以及对没有 Python 反射的 C++ 函数做外部触发。
  若 SoftUEBridge 可用且目标函数有 Python 反射，优先用 tools call run-python-script。
  当用户提到以下场景时激活：
  "remote-control"、"CI 触发"、"SoftUEBridge 不可用"、"TriggerExcelPreCheckinExport"、
  "BridgeEditorFunctionLibrary"、"UnloadPipelineDataTables"、"release datatable"、
  "ue-cli remote"、"call UE function from CLI"、"远程调用编辑器函数"、"RC API"。
tags: [UE-CLI, Remote-Control, Blueprint, Editor-Automation, Excel-Pipeline, SoftUEBridge]
---

# ue-cli Remote Control

> Layer: Tier 3 (Workflow Skill)

**CRITICAL — `remote-control` 走 UE Remote Control API（端口 30010），不走 SoftUEBridge（端口 8080）。**
**两个独立传输层，互不依赖。check-setup / instance.json 对本 domain 无效。**

---

## 前提条件

| 条件 | 说明 |
|------|------|
| UE Editor 已启动 | 必须 |
| **Remote Control API 插件已启用** | Edit → Plugins → 搜索 "Remote Control API" → 启用 → 重启编辑器 |
| 端口 30010 可达 | 默认绑定 127.0.0.1:30010 |

> **⚠️ 若调用超时**：99% 是 Remote Control API 插件未启用，不是代码问题。

---

## Windows cmd 引号转义

`--params` 的 JSON 在不同 shell 下写法不同：

| Shell | 写法 |
|-------|------|
| **Windows cmd** | `--params "{\"Changelist\": 200}"` |
| Git Bash / PowerShell | `--params '{"Changelist": 200}'` |

Remote Control API **需要 Remote Control API 插件启用**（端口 30010）。
若插件未启用（超时），改用 SoftUEBridge 的 `run-python-script` 作为替代：

```bat
ue-cli.bat --timeout 120 tools call --name run-python-script --args "{\"script\": \"import unreal\nresult = unreal.BridgeEditorFunctionLibrary.trigger_excel_pre_checkin_export(200)\nprint('ExitCode:', result)\"}"
```

---

## 快速命令

### 触发 Excel 预提交导表（主要用途）

```bash
# 调用 UBridgeEditorFunctionLibrary::TriggerExcelPreCheckinExport(Changelist=200)
ue-cli.bat remote-control --rc-timeout 120 call --object-path "/Script/SoftUEBridgeEditor.Default__BridgeEditorFunctionLibrary" --function "TriggerExcelPreCheckinExport" --params "{\"Changelist\": 200}"
```

> **注意**：UE Remote Control API 的 `objectPath` 对以 `/` 开头的路径有平台解析歧义。
> 若出现 "does not exist" 错误，请参见下方[路径格式说明](#object-path-格式)。

### 卸载 DataTable 资产

```bash
./ue-cli.bat remote-control unload-datatables
```

### 调用任意 UE 对象函数

```bash
./ue-cli.bat remote-control call \
  --object-path "<UE-Object-Path>" \
  --function "<FunctionName>" \
  --params '{"Param1": "value", "Param2": 42}'
```

---

## 参数速查

**父级参数**（所有子命令共享）：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--rc-host` | `127.0.0.1` | Remote Control API host |
| `--rc-port` | `30010` | Remote Control API port |
| `--rc-timeout` | `5.0` | 请求超时（秒）；同步阻塞函数需调大 |

**`call` 子命令参数**：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--object-path` | ✅ | UE 对象路径（见下方格式说明） |
| `--function` | ✅ | 函数名（与 C++ / Blueprint 中一致） |
| `--params` | ❌ | JSON 对象字符串，默认 `{}` |

---

## Object Path 格式

UE Remote Control API 的 `objectPath` 有两种惯用写法：

| 类型 | 格式示例 |
|------|----------|
| BlueprintFunctionLibrary CDO | `/Script/ModuleName.Default__ClassName` |
| 具体 UObject 路径 | `/Game/Maps/MainLevel.MainLevel:PersistentLevel.MyActor_0` |

**`UBridgeEditorFunctionLibrary` 的标准路径**：
```
/Script/SoftUEBridgeEditor.Default__BridgeEditorFunctionLibrary
```

> 若 Git Bash / PowerShell 把以 `/Script/` 开头的路径解释为文件系统路径，
> 使用双引号包裹或在 PowerShell 中直接 `Invoke-RestMethod`（见[备用调用方式](#备用调用方式)）。

---

## 已注册的具名 Action

直接使用命令名，无需手写 object-path 和 function：

| Action | 等价调用 |
|--------|----------|
| `unload-datatables` | `DMDataTableBPLibrary::UnloadPipelineDataTables` |

添加新 action：在 `Tools/ue-cli/src/domains/remote_control/commands.py` 的 `ACTIONS` 字典中增加一行即可。

---

## 同步阻塞函数的超时处理

`TriggerExcelPreCheckinExport` 是同步阻塞调用，excel_exporter.py 完成前不返回。
若导表耗时较长，需调大 `--rc-timeout`：

```bash
./ue-cli.bat remote-control call \
  --rc-timeout 120 \
  --object-path "/Script/SoftUEBridgeEditor.Default__BridgeEditorFunctionLibrary" \
  --function "TriggerExcelPreCheckinExport" \
  --params '{"Changelist": 87509}'
```

---

## 备用调用方式（Remote Control API 直连）

当 CLI 的 shell 引号转义导致路径解析错误时，直接用 PowerShell 调 REST：

```powershell
$body = @{
  objectPath   = "/Script/SoftUEBridgeEditor.Default__BridgeEditorFunctionLibrary"
  functionName = "TriggerExcelPreCheckinExport"
  parameters   = @{ Changelist = 200 }
} | ConvertTo-Json -Depth 5

Invoke-RestMethod -Uri "http://127.0.0.1:30010/remote/object/call" `
                  -Method Put `
                  -ContentType "application/json" `
                  -Body $body
```

---

## 与 SoftUEBridge 的关系

| 维度 | SoftUEBridge (`/bridge`) | Remote Control API (`/remote/object/call`) |
|------|--------------------------|--------------------------------------------|
| 端口 | 动态（instance.json） | 固定 30010 |
| 协议 | JSON-RPC 2.0 | REST PUT |
| 工具发现 | `tools list` | 无；需知道 objectPath + functionName |
| 适用场景 | Claude 操作 UE Editor 资产 | 直接调用任意 UE C++ / Blueprint 函数 |
| 插件依赖 | SoftUEBridge | Remote Control API |

---

## 排错速查

| 现象 | 原因 | 解法 |
|------|------|------|
| `timed out` | RC API 插件未启用 | Edit → Plugins → 启用 Remote Control API → 重启 |
| `HTTP 400: Object does not exist` | objectPath 格式错误或模块名拼错 | 用 PowerShell 直连验证路径格式 |
| `HTTP 400: Function not found` | 函数签名不匹配 | 确认 C++ 函数已 `UFUNCTION(BlueprintCallable)` 标注 |
| 调用成功但结果为 1（失败） | Python 脚本执行失败 | 查 UE Output Log → LogTemp / LogPython |
