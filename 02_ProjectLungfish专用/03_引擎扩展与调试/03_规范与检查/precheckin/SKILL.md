---
name: precheckin
title: Excel → UE DataTable 导出（excel_exporter.py）
description: 将 Main/RawData/ 下的 Excel 表通过 excel_exporter.py 导出为 UE DataTable 资产的完整操作流程。涵盖前提检查（P4 checkout、CL 编号）、双路径触发方式（UE 已开启用 Remote Control，未开启用 Cmd.exe）、成功判断依据、以及 EntityTag 特殊限制（只生成 C++ AutoGen 文件，需编译才生效）。当用户提到 excel_exporter、precheckin 导出、Excel 转 DataTable、DT 导出失败、GameplayTag invalid 时使用。
tags: [DataTables, Excel, Content-Pipeline, Automation, P4, UE-Export]
---

# Excel → UE DataTable 导出 Skill

## 触发条件

- 需要执行 `excel_exporter.py` 导出
- Excel 改完后需要刷新 UE 内 DataTable
- 遇到 `--precheckin` 导出相关问题
- 遇到 `GameplayTag validation` / `invalid tag` 报错
- 遇到 `Base Id require to be set > 0` 报错

---

## 核心职责

UE5 不直接读取 Excel，流程为：

```
Excel (Main/RawData/) → excel_exporter.py → DataTable 资产 (.uasset)
```

`EntityTag.xlsx` 例外：不生成 DataTable，只更新 C++ AutoGen 文件，**必须重新编译工程**才能生效。

---

## 前提检查（执行前必做）

### 1. 目标 Excel 文件已 checkout

```bash
p4 edit -c <CL编号> "Main/RawData/<文件名>.xlsx"
```

未 checkout 时 openpyxl 写入报 `PermissionError`。

### 2. Excel 文件必须在具体编号的 CL 中（不能在 default）

```bash
# 查看 default 中有哪些文件
p4 opened -c default

# 若有文件在 default，先建新 CL
p4 change -o | sed 's/<enter description here>/<描述>/' | p4 change -i

# 将文件移入新 CL
p4 reopen -c <新CL> "Main/RawData/PLEntityTagMapping.xlsx"
p4 reopen -c <新CL> "Main/RawData/Editor/InitEntityTable/EntityPropertyInitializer.xlsx"

# 确认 default 已清空（应无输出）
p4 opened -c default
```

---

## 触发方式（双路径，脚本自动选择）

| UE 状态 | 触发方式 | 耗时 |
|---------|----------|------|
| **UE Editor 已开启** | Remote Control API → `TriggerExcelPreCheckinExport` | 秒级 |
| **UE Editor 未开启** | Cmd.exe `-run=pythonscript` | 约 1–2 分钟 |

### 推荐：通过 entity_modifier / entity_adder 自动触发

```bash
# entity_modifier：加 --run-export 自动选择路径
python entity_modifier.py Entity.FireMaker tag add AssetTag.CanHangOnMount \
    --run-export --changelist=88000

# entity_adder finalize：内置 run_export_smart()
python entity_adder.py finalize Entity.NewSword \
    --similar=Entity.FireMaker --changelist=88000
```

### 手动调用 — UE 已开启（Remote Control）

```bash
curl -s -X PUT "http://127.0.0.1:30010/remote/object/call" \
  -H "Content-Type: application/json" \
  -d '{
    "objectPath": "/Script/SoftUEBridgeEditor.Default__BridgeEditorFunctionLibrary",
    "functionName": "TriggerExcelPreCheckinExport",
    "parameters": {"Changelist": <CL编号>}
  }'
# 返回 {"ReturnValue": 0} 表示成功
```

### 手动调用 — UE 未开启（Cmd.exe）

> ⚠️ UE Editor 必须**完全关闭**，否则无法打开同一项目。

```bash
# 查找最新 Cmd.exe（取修改时间最新的）
CMD_EXE=$(ls -t "${WORKSPACE_ROOT}/Engine/Binaries/Win64/"UnrealEditor*-Cmd*.exe | head -1)

"${CMD_EXE}" \
  "${WORKSPACE_ROOT}/Main/ProjectLungfish.uproject" \
  -run=pythonscript \
  -as-force-preprocess-editor-code \
  -LiveCoding=false \
  -nosplash -nopause -NoLoadingScreen -unattended \
  -AllowCommandletRendering=false \
  -script="${WORKSPACE_ROOT}/Main/Plugins/PLPythonPipeline/Content/Python/excel_exporter.py \
    --precheckin --changelist=<CL编号> --p4"
```

---

## 关键参数速查

| 参数 | 说明 |
|------|------|
| `--precheckin` | 仅处理 P4 该 CL 内有变动的表（增量） |
| `--changelist=<N>` | 指定 CL 编号，**不能填 default** |
| `--p4` | 启用 P4 集成，自动 checkout 变动的资产文件 |
| `--forceall` | 强制导出所有表（全量，用于初始化/排查） |

---

## 成功判断

| 场景 | 判断依据 |
|------|----------|
| 通用 | `DT_EntityPropertyInitializer` 资产修改时间/P4 状态变动 |
| Tag 修改 | `DT_PLEntityTagMapping` 等相关 DataTable 变动 |
| EntityTag 注册 | `EntityGameplayTags.h/.cpp` AutoGen 文件更新（**无 DataTable 产出**） |

---

## 常见错误排查

### `Base Id require to be set > 0`

**原因：** 新行的 A 列（EntityId）是 Excel 公式，但 openpyxl 以 `data_only=True` 读取时缓存值为 `None`（该机器未打开过文件计算公式）。

**修复（推荐，用 win32com 强制重算）：**

```python
import win32com.client, os
path = os.path.abspath('Main/RawData/PLEntityTagMapping.xlsx')  # 替换为报错文件
excel = win32com.client.Dispatch('Excel.Application')
excel.Visible = False
excel.DisplayAlerts = False
wb = excel.Workbooks.Open(path)
excel.CalculateFull()
wb.Save()
wb.Close()
excel.Quit()
```

完成后重新运行 `excel_exporter.py`。

**备用（手动）：** 在 Excel 中将报错行的 A 列公式替换为手动输入的整数值，保存后重跑。

---

### `GameplayTag validation` 报 invalid tag

**原因：** 新 `Entity.xxx` tag 写入了 `EntityTag.xlsx` 但未编译进引擎，UE 运行时 GameplayTagsManager 不认识该 tag。

**修复流程：**

1. 确认 `Main/Plugins/DataManager/Source/TableDataManager/Private/AutoGen/EntityGameplayTags.h` 中有该 tag 的 `UE_DECLARE_GAMEPLAY_TAG_EXTERN`
2. 若无：关闭 UE → 用 Cmd.exe 模式跑 `excel_exporter.py --forceall`（或含 EntityTag.xlsx 的 precheckin 导出），更新 AutoGen 文件
3. **关闭 UE → 重新编译工程（DebugGame_Editor）**
4. 重新开启 UE → 再触发导出

**关键约束：**
- `EntityTag.xlsx` 必须在目标 CL 里（`--precheckin` 只处理该 CL 内的文件）
- `--precheckin` 下即使只导 EntityTag.xlsx，最终校验仍对全表执行——必须编译后 UE 认识 tag 才能通过
- `EntityTag.xlsx` 对应的表 `PackagePath` 为空，**不产出 DataTable 资产，只生成 AutoGen C++ 文件**

---

## 关键文件路径

| 文件 | 路径 |
|------|------|
| 导出脚本 | `Main/Plugins/PLPythonPipeline/Content/Python/excel_exporter.py` |
| Excel 源数据 | `Main/RawData/` |
| UE 命令行工具 | `Engine/Binaries/Win64/` 下修改时间最新的 `UnrealEditor*-Cmd.exe` |
| UE 项目文件 | `Main/ProjectLungfish.uproject` |
| EntityTag AutoGen | `Main/Plugins/DataManager/Source/TableDataManager/Private/AutoGen/EntityGameplayTags.h` |
