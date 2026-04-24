# remote-control Domain — 开发参考

> 适用于：在 `Tools/ue-cli` 中维护、扩展 `remote-control` domain 的开发者。
> 用户使用文档见 `.claude/skills/ue-cli-remote-control/SKILL.md`。

---

## 传输层说明

`remote-control` domain 使用 **UE Remote Control API**，与其他所有 domain 使用的 SoftUEBridge 完全独立：

| 对比项 | SoftUEBridge domains | remote-control domain |
|--------|---------------------|-----------------------|
| 端口 | 动态（instance.json） | 固定 30010 |
| 协议 | JSON-RPC 2.0 POST `/bridge` | REST PUT `/remote/object/call` |
| 发现机制 | `resolve_instance()` / `BridgeClient` | 无；直接构造 `RemoteControlClient` |
| UE 插件依赖 | SoftUEBridge | Remote Control API |

因此 `remote-control` **不调用 `make_client()`，不依赖 `instance.json`**，不需要 check-setup 前置。

---

## 文件结构

```text
src/domains/remote_control/
  __init__.py          # 空，包标记
  client.py            # RemoteControlClient — 纯 stdlib urllib，无第三方依赖
  commands.py          # register_remote_control() + ACTIONS 注册表 + 处理函数
```

`app.py` 中的注册：
```python
from .domains.remote_control.commands import register_remote_control
# build_parser() 末尾：
register_remote_control(subparsers)
```

---

## ACTIONS 注册表

`commands.py` 顶部的 `ACTIONS` 字典是具名 action 的唯一来源：

```python
ACTIONS: dict[str, tuple[str, str, dict[str, Any]]] = {
    "action-name": (
        "/Script/ModuleName.Default__ClassName",  # objectPath
        "FunctionName",                            # functionName
        {},                                        # default parameters
    ),
}
```

**新增 action 只需一行**，无需新增 handler 函数，CLI 子命令自动注册。

### 当前已注册 Actions

| Action | objectPath | functionName |
|--------|-----------|--------------|
| `unload-datatables` | `/Script/DataManagerEditor.Default__DMDataTableBPLibrary` | `UnloadPipelineDataTables` |

---

## RemoteControlClient API

```python
# src/domains/remote_control/client.py
client = RemoteControlClient(host="127.0.0.1", port=30010, timeout=5.0)
response: dict = client.call_object(
    object_path="...",
    function_name="...",
    parameters={"Param": value},   # 可选
)
```

**错误处理**：
- `HTTP 4xx/5xx` → `RuntimeError("Remote Control API request failed: HTTP <code>: <detail>")`
- 连接失败（超时/拒绝）→ `RuntimeError("Remote Control API connection failed: <reason>\nIs UE Editor running...")`

---

## objectPath 格式规范

| UE 对象类型 | 路径格式 |
|------------|----------|
| BlueprintFunctionLibrary CDO | `/Script/<Module>.Default__<ClassName>` |
| Actor（PIE/Editor） | `/Game/<Map>.<Map>:PersistentLevel.<ActorName>_<ID>` |
| DataTable | `/Game/<Path>/<DTName>.<DTName>` |

`UBridgeEditorFunctionLibrary` 的路径：
```
/Script/SoftUEBridgeEditor.Default__BridgeEditorFunctionLibrary
```

### Shell 路径解析陷阱

Git Bash / MSYS 会把 `/Script/...` 解释为文件系统绝对路径，拼上 `C:/Program Files/Git/` 前缀。

**规避方案**：
1. 用双引号 `"..."` 包裹（ue-cli 的 `--params` JSON 字符串内已有引号，通常安全）
2. 在 PowerShell 中直接调用 `Invoke-RestMethod`（最稳定）
3. 通过 SoftUEBridge 的 `run-python-script` 工具用 Python 发起调用（绕过 shell）

---

## 函数参数命名规则

UE Remote Control API 的 `parameters` 字段使用 **C++ 参数名**（不是 Python snake_case）。

```json
// ✅ 正确 — 与 C++ 函数签名一致
{ "Changelist": 200 }

// ❌ 错误 — Python 命名不被 UE 识别
{ "changelist": 200 }
```

查看参数名的方法：看 `.h` 头文件的 `UFUNCTION` 声明，或在编辑器 Python 中：
```python
import unreal
help(unreal.BridgeEditorFunctionLibrary.trigger_excel_pre_checkin_export)
```

---

## 同步阻塞函数

UE Remote Control API 的每次 HTTP 请求是同步的——UE 执行完函数才返回响应。
对于长时间运行的函数（如 `TriggerExcelPreCheckinExport`），客户端需要设置足够大的 timeout。

**CLI 用法**：
```bash
./ue-cli.bat remote-control call --rc-timeout 120 --object-path "..." --function "..."
```

**客户端层面**：`RemoteControlClient(timeout=120.0)`

---

## 单元测试

新增 domain 后，在 `tests/test_domain_commands.py` 中添加覆盖：
- `register_remote_control` 是否注册了所有 ACTIONS 子命令
- `handle_call` 的 `--params` JSON 解析错误处理
- `RemoteControlClient.call_object` 的 HTTP payload 构造（可 mock `urllib.request.urlopen`）

---

## 与 BridgeEditorFunctionLibrary 的关系

`UBridgeEditorFunctionLibrary`（`SoftUEBridgeEditor` 模块）是目前 remote-control domain 的主要调用目标之一：

| 文件 | 路径 |
|------|------|
| 头文件 | `Main/Plugins/SoftUEBridge/Source/SoftUEBridgeEditor/Public/BridgeEditorFunctionLibrary.h` |
| 实现 | `Main/Plugins/SoftUEBridge/Source/SoftUEBridgeEditor/Private/BridgeEditorFunctionLibrary.cpp` |

**当前方法**：

| C++ 方法 | Python 反射名 | 参数 |
|----------|--------------|------|
| `TriggerExcelPreCheckinExport` | `trigger_excel_pre_checkin_export` | `Changelist: int32` |

实现要点：
- 通过 `IPythonScriptPlugin::ExecPythonCommandEx`（`ExecuteFile` 模式）调用 excel_exporter.py
- Workspace root 通过 `FPaths::ConvertRelativePathToFull(ProjectDir)` 再取父目录得到
- 同步阻塞，返回值：`0`=成功，`1`=脚本失败，`-1`=PythonPlugin 不可用
