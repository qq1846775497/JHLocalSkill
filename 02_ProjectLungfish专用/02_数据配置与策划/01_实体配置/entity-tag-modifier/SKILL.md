---
name: entity-tag-modifier
title: 实体 Tag 与属性修改流程
description: 修改实体 tag（增加/改变/删除）或修改实体属性的标准操作流程，涵盖 Excel 表操作、InstanceTag 唯一性检查、EntityInstanceConfig 行复制、属性表定位（通过 ConfigID 关联子表 Id）、excel_exporter.py 执行命令。注意：属性修改只需 excel_exporter 导出即生效，不需要 Export Row to DataAsset；该步骤仅用于 Tag 修改流程。当用户提到修改实体 tag、修改实体属性、修改燃点/温度/湿度等属性数值、PLEntityTagMapping、EntityPropertyInitializer、EntityInstanceConfig、InstanceTag、OtherTags、EntityTypes 时使用。
tags: [DataTables, Data-Driven, Excel, Content-Pipeline, EntityTag, EntityProperty, InstanceTag, Automation]
---

# Entity Tag & Attribute Modifier Skill

## 触发条件

当用户提到以下任意情况时，使用本 skill 作为操作依据：

- 需要修改实体的 tag（增加/改变/删除）
- 需要修改实体的属性数值（如燃点、温度、湿度等任何游戏数值）
- 需要修改实体的 InstanceTag 或查找实体在哪张属性表中
- 提及 `PLEntityTagMapping`、`EntityPropertyInitializer`、`EntityInstanceConfig`、`excel_exporter`
- 提及 export row to dataasset（**仅 Tag 修改需要此步骤，属性修改不需要**）
- 需要运行 excel 导出脚本
- 需要理解/修改实体修改流程脚本

---

## 背景知识

### 工具链概述（来自山外山工具链设计纲要）

UE5 不直接读取 Excel，因此：
1. Excel 维护源数据 → `excel_exporter.py` 导出为同名 DataTable
2. DataTable 再通过自动化安装到实体蓝图（DTToEntity）
3. 为避免锁文件冲突，可配置内容打包为 DataAsset (DA) → 配置到 Entity

### Excel 表结构（来自山外山工具链AI读取文档）

**路径：** `Main/RawData/`

**首要前置：**
- `EntityTag.xlsx` — 注册实体 tag

**三张核心主表（用于确认实体 tag）：**
- `PLEntityTagMapping.xlsx` — 非生物非武器工具防具实体
- `PLEntityTagMapping_Character.xlsx` — 生物实体
- `PLEntityTagMapping_WeaponArmor.xlsx` — 武器工具防具实体

**实体设置表：**
- `EntityPropertyInitializer.xlsx` — 设置实体蓝图 class defaults，主要用于设置 tag

**Tag 列说明（PLEntityTagMapping 中）：**
| 列名 | 列索引 | 说明 | 可增加 | 可删除 | 可修改 |
|------|--------|------|--------|--------|--------|
| EntityTag | 13 | 实体主 tag，有固定前缀 | 否 | 否 | 是 |
| InstanceTag | 5 | 属性模板 tag，单值列，前缀 `Instance.` | 无值时可新增 | 是 | 是 |
| EntityTypes | 14 | 实体类型 tag，多值列（`\|` 分隔），有固定前缀 | 是 | 是 | 是 |
| RarityTag | 31 | 稀有度 tag，有固定前缀 | 否 | 否 | 是 |
| OtherTags | 32 | 其他 tag，多值列（`\|` 分隔），无固定前缀 | 是 | 是 | 是 |

**InstanceTag 相关表：**
| 文件 | 路径 | 说明 |
|------|------|------|
| EntityInstanceConfig.xlsx | `Main/RawData/EntityInstanceConfig.xlsx` | 每个 InstanceTag 对应一行基础属性配置，含各子表的 ConfigID |
| InstanceTag.xlsx | `Main/RawData/InstanceTag.xlsx` | 注册所有可用的 InstanceTag |

---

## 标准操作流程

### 2. 修改一个实体上的属性

> ⚠️ **属性修改完成后，只需运行 `excel_exporter` 导出即可生效，不需要 Export Row to DataAsset。**
> Export Row to DataAsset 仅用于 Tag 修改流程（步骤 a.7）。

**2.0 前置：p4 edit checkout 目标属性子表**

在执行 `--set` 写入前，必须先将对应属性子表 checkout，否则 openpyxl 写入时会报 `PermissionError`。

根据要修改的属性所在子表（可先用 `--dry-run` 确认是哪张表），执行：

```bash
p4 edit -c <CL编号> "//CyanCookOfficialDepot/MainDev/Main/RawData/<子表文件名>"
# 示例：
p4 edit -c 88673 "//CyanCookOfficialDepot/MainDev/Main/RawData/PhaseChange_BurningAttributeConfig.xlsx"
```

> **操作顺序建议：**
> 1. 先建 CL：`p4 change -o | sed 's/<enter description here>/<描述>/' | p4 change -i`
> 2. 用 `--dry-run` 确认子表名和行号
> 3. `p4 edit -c <CL> <子表路径>` checkout
> 4. 正式执行 `--set --changelist=<CL>`

**2.1** 根据用户告知，在三张核心主表中找到对应的实体 tag（`PLEntityTagMapping` / `_Character` / `_WeaponArmor`）。

**2.2** 找到该实体的 `InstanceTag`（核心主表第 5 列）。

**2.3** 打开 `EntityInstanceConfig.xlsx`，找到该 InstanceTag 所在行（可能不止一行）。

> **子表行定位原理：** 脚本不是直接在属性子表里找 InstanceTag，而是通过以下链路定位：
> `EntityInstanceConfig[InstanceTag行]` → `BurningAttributeConfigID`（等各 ConfigID 列）→ 对应子表的 `Id` 列。
> 映射关系已内置于 `INSTANCE_CONFIG_COL_TO_SUBTABLE` 字典中。

**2.4.1** 如果 **只有一行** 使用该 InstanceTag：
- 直接执行 `entity_modifier.py <entity_tag> attr --set --attr-name=<属性列名> --value=<目标值>`，脚本自动定位子表并写入。

**2.4.2** 如果 **超过一行** 使用该 InstanceTag（tag 被多个实体共享）：
- `entity_modifier.py` 的 `--set` 会自动拆分（无需手动 `--ensure-unique`），直接执行：
  `entity_modifier.py <entity_tag> attr --set --attr-name=<属性列名> --value=<目标值>`
- 若需手动控制新 InstanceTag 命名，加 `--new-instance-tag=<新tag名>`。

**2.5 - 2.7**（共享时由 `--set` 自动完成）：
- 自动在 `InstanceTag.xlsx` 注册新 tag
- 自动更新核心主表中该实体的 `InstanceTag` 列
- 自动在 `EntityInstanceConfig.xlsx` 复制新行
- 自动在对应属性子表中定位列并写入新值

**2.8 导出（最后一步，无需额外操作）：**
- 执行 excel_exporter 导出即完成，**不需要 Export Row to DataAsset**
- 命令加 `--run-export` 可自动触发导出

> **属性列名模糊时的处理：**
> 当用户说"修改燃点"、"改一下温度"等模糊描述时，Claude 应根据飞书文档中各子表的功能描述推断可能的列名关键词，传给 `--attr-name`。脚本会在全部属性子表中做模糊搜索并汇报匹配结果。若匹配到多个列，脚本会列出所有候选，此时 Claude 应提示用户确认精确列名后重新执行。

---

### 1. 修改一个实体上的Tag

### 1.1 增加 Tag

**a.1** 根据用户告知，在三张核心主表中找到对应的实体 tag。

**a.2** 检查重复：在对应实体 tag 的 `EntityTag`、`InstanceTag`、`EntityTypes`、`RarityTag`、`OtherTags` 列中查找是否已有待添加的 tag。如有，**直接拒绝并告知重复**。

**a.3** 确定写入列：
- 待添加 tag 符合 `EntityTag` 前缀（Entity./Character./Building.）→ **拒绝**（只能修改，不能增加）
- 待添加 tag 符合 `RarityTag` 前缀（EntityRarity.）→ **拒绝**（只能修改，不能增加）
- 待添加 tag 符合 `InstanceTag` 前缀（Instance.）：
  - 该实体无 InstanceTag → 写入 `InstanceTag` 列（单值）
  - 该实体已有 InstanceTag → **拒绝**（已存在时只能 change，不能增加）
- 待添加 tag 符合 `EntityTypes` 前缀（EntityType./Affix.）→ 追加到 `EntityTypes` 列
- 其余情况 → 追加到 `OtherTags` 列

**a.4** 保存 `EntityPropertyInitializer.xlsx`。

**a.5** 在 `EntityPropertyInitializer.xlsx` 第三行任意列内容中多打一个空格后保存，以标记该表发生了变动（触发导出识别）。

**a.6** 执行导出命令：

> ⚠️ **前提检查（执行前必做）：**
>
> - **所有待导出的 Excel 文件不能在 P4 default changelist 中**，必须在一个具体编号的 changelist 里。若文件在 default 中，执行以下步骤创建新 CL 并移入：
>    ```bash
>    # 1. 创建新 changelist（记下返回的 CL 编号，下面记为 <新CL>）
>    p4 change -o | sed 's/<enter description here>/Excel Export for entity tag change/' | p4 change -i
>
>    # 2. 将 default 中的文件移入新 CL
>    p4 reopen -c <新CL> "Main/RawData/PLEntityTagMapping.xlsx"
>    p4 reopen -c <新CL> "Main/RawData/Editor/InitEntityTable/EntityPropertyInitializer.xlsx"
>
>    # 3. 确认 default 已清空
>    p4 opened -c default   # 应无输出
>    ```

**导出方式（脚本自动选择，根据 UE 是否开启）：**

| 状态 | 触发方式 | 备注 |
|------|----------|------|
| UE Editor 已开启 | UE Remote Control API → `TriggerExcelPreCheckinExport` | 进程内 Python，速度快；无需关闭 UE |
| UE Editor 未开启 | `Cmd.exe -run=pythonscript excel_exporter.py` | 会启动新 UE 进程，耗时约 1-2 分钟 |

**`entity_modifier.py` 和 `entity_adder.py` 已内置此逻辑**，直接调用 `--run-export` 即可：

```bash
# entity_modifier.py 自动判断
python entity_modifier.py Entity.FireMaker tag add AssetTag.CanHangOnMount --run-export --changelist=88000

# entity_adder.py finalize 自动判断
python entity_adder.py finalize Entity.NewSword --similar=Entity.FireMaker --changelist=88000
```

**手动调用（UE 已开启时）— Remote Control API：**

```bash
# PUT http://127.0.0.1:30010/remote/object/call
curl -s -X PUT "http://127.0.0.1:30010/remote/object/call" \
  -H "Content-Type: application/json" \
  -d '{"objectPath": "/Script/SoftUEBridgeEditor.Default__BridgeEditorFunctionLibrary",
       "functionName": "TriggerExcelPreCheckinExport",
       "parameters": {"Changelist": <你的CL编号>}}'
# 返回 {"ReturnValue": 0} 表示成功
```

**手动调用（UE 未开启时）— Cmd.exe：**

> 前置：UE Editor 必须**完全关闭**，否则 Cmd.exe 无法打开同一项目。
>
> 可执行文件选取规则：在 `Engine/Binaries/Win64/` 下找修改时间最新的 `UnrealEditor*-Cmd.exe`。

```bash
# 1. 获取工作区根目录（bash 下执行）
WORKSPACE_ROOT=$(cd "$(dirname "$(p4 -F %clientRoot% info 2>/dev/null || pwd)")" 2>/dev/null && pwd)
# 若 p4 info 失败，手动设置，例如：
# WORKSPACE_ROOT="D:/QiuDesheng_AfterDemo"

# 2. 查找最新 Cmd.exe
CMD_EXE=$(ls -t "${WORKSPACE_ROOT}/Engine/Binaries/Win64/"UnrealEditor*-Cmd*.exe 2>/dev/null | head -1)

# 3. 执行导出（<你的CL编号> 替换为上面确认的 changelist 号）
"${CMD_EXE}" \
  "${WORKSPACE_ROOT}/Main/ProjectLungfish.uproject" \
  -run=pythonscript \
  -as-force-preprocess-editor-code \
  -LiveCoding=false \
  -nosplash \
  -nopause \
  -NoLoadingScreen \
  -unattended \
  -AllowCommandletRendering=false \
  -script="${WORKSPACE_ROOT}/Main/Plugins/PLPythonPipeline/Content/Python/excel_exporter.py --precheckin --changelist=<你的CL编号> --p4"
```

> 成功判断依据：`DT_EntityPropertyInitializer` 表发生变动。

**a.7** 执行 export row to dataasset，将 DT 数据写入对应 BP 的 CDO 并保存。

> ⚠️ **UE 已开启时由 AI 自动执行，不要求用户手动操作。** 只要 UE Editor 开着且 SoftUEBridge 连接，AI 应直接通过 ue-cli 完成此步骤，完成后将 BP 文件 reopen 到目标 CL。

**自动执行方式（AI 直接通过 ue-cli 执行）：**

```bash
# BP 路径从 PLEntityTagMapping 的 SoftActorToSpawnClass 列读取，去掉 _C 后缀
./Tools/ue-cli/bin/ue-cli.exe --host 127.0.0.1 --port 8080 tools call \
  --name run-python-script \
  --args '{
    "script": "import unreal\ndt = unreal.load_asset(\"/Game/003_DataTablePipeline/DT_PLEntityTagMapping\")\nbp = unreal.load_asset(\"<BP资产路径>\")\nresult = unreal.PLPythonAutomationFunctionLibrary.set_entity_properties_from_data_table(dt, unreal.Name(\"<entity_tag>\"), bp)\nif result:\n    unreal.BlueprintEditorLibrary.compile_blueprint(bp)\n    unreal.EditorAssetLibrary.save_loaded_asset(bp)\n    print(\"Done\")\nelse:\n    print(\"ERROR: returned False\")"
  }'

# 保存后 BP 会进入 P4 default CL，需移入目标 CL
p4 reopen -c <CL编号> "//CyanCookOfficialDepot/MainDev/Main/Content/.../BP_XXX.uasset"
```

> ⚠️ **关键注意事项：**
> - compile 必须用 `unreal.BlueprintEditorLibrary.compile_blueprint(bp)`
> - **不要用** `unreal.EditorAssetLibrary.compile_blueprint`（不存在，报 AttributeError）
> - **不要用** `unreal.KismetEditorUtilities.compile_blueprint`（此环境不可用）
> - 若仅 save 不 compile，继承自 C++ 父类的属性（如 `static_gameplay_tags`）**不会序列化进磁盘**，reload 后仍显示旧值
> - BP 保存后 UE 会自动 checkout 到 P4 default changelist，需手动 `p4 reopen -c <CL>` 移入目标 CL

**备用方式（手动，UE 未开启或 SoftUEBridge 不可用时）：** 在 UE 编辑器中打开 `DT_PLEntityTagMapping`，找到实体 tag 所在行，右键 → **Export Row to DataAsset**（UE 内部会自动触发 compile+save）。

> 成功判断依据：对应 Blueprint (BP) 文件发生变动，且 reload 后 `static_gameplay_tags` 中包含正确 tag。

---

### 1.2 改变 Tag（修改现有 tag 的值）

**b.1** 在三张核心主表中找到对应的实体 tag。

**b.2** 在对应实体 tag 的 `EntityTag`、`InstanceTag`、`EntityTypes`、`RarityTag`、`OtherTags` 中寻找待改变的 tag，找到后：先删除旧值，再写入新值。

**b.3** 改变 tag 操作**允许修改所有列**，包括 `EntityTag`、`InstanceTag`、`RarityTag`。

执行后续步骤同增加 tag 的 **a.4 → a.7**。

---

### 1.3 删除 Tag

**c.1** 在三张核心主表中找到对应的实体 tag。

**c.2** 在 `InstanceTag`、`EntityTypes`、`OtherTags` 中寻找待删除的 tag，找到则删除（`InstanceTag` 为单值列，置空即可）。

> **注意：`EntityTag` 和 `RarityTag` 不允许删除。`InstanceTag` 允许删除。**

执行后续步骤同增加 tag 的 **a.4 → a.7**。

---

## 脚本说明（excel_exporter.py）

**脚本路径：** `Main/Plugins/PLPythonPipeline/Content/Python/excel_exporter.py`

**核心作用：**
- 将 `Main/RawData/` 下的 Excel 表导出为同名 DataTable 资产
- `--precheckin` 模式：仅处理发生了变动的表（通过 P4 检测）
- `--changelist=<CL编号>`：指定 P4 changelist 号（**必须是具体编号，不能是 default**）
- `--p4`：启用 P4 集成（自动 checkout 变动的资产文件）

**触发方式（智能双路径，由脚本自动选择）：**

| UE 状态 | 触发方式 | 实现 |
|---------|----------|------|
| UE Editor 已开启 | UE Remote Control API | PUT `http://127.0.0.1:30010/remote/object/call` → `TriggerExcelPreCheckinExport` |
| UE Editor 未开启 | Cmd.exe `-run=pythonscript` | 启动新 UE 进程执行 `excel_exporter.py` |

`entity_modifier.py::run_export()` 和 `entity_adder.py::run_export_smart()` 均已实现此逻辑。

**判断导出是否成功：** 检查 `DT_EntityPropertyInitializer` DataTable 资产的修改时间或 P4 状态是否有变动。

---

## 关键文件路径速查

| 文件 | 路径 |
|------|------|
| 核心主表（通用） | `Main/RawData/PLEntityTagMapping.xlsx` |
| 核心主表（生物） | `Main/RawData/PLEntityTagMapping_Character.xlsx` |
| 核心主表（武器防具） | `Main/RawData/PLEntityTagMapping_WeaponArmor.xlsx` |
| 实体设置表 | `Main/RawData/Editor/InitEntityTable/EntityPropertyInitializer.xlsx` |
| 实体实例配置表 | `Main/RawData/EnitiyInstanceConfig.xlsx` |
| InstanceTag 注册表 | `Main/RawData/InstanceTag.xlsx` |
| 导出脚本 | `Main/Plugins/PLPythonPipeline/Content/Python/excel_exporter.py` |
| 实体修改脚本 | `Main/Plugins/PLPythonPipeline/Content/Python/entity_modifier.py` |
| UE 命令行工具 | `Engine/Binaries/Win64/` 下修改时间最新的 `UnrealEditor*-Cmd.exe` |
| UE 项目文件 | `Main/ProjectLungfish.uproject` |

---

## 注意事项

1. **修改 Excel 前**，确认文件已通过 P4 checkout（`p4 edit`），否则文件为只读。
2. **EntityTag 和 RarityTag** 只能改变值，不能增加新行也不能删除。
3. **a.5 步骤不可省略**：EntityPropertyInitializer 表需要有实质变动才会被 `--precheckin` 模式识别并导出。
4. **a.7 步骤：UE 已开启时由 AI 通过 ue-cli 自动执行**（`BlueprintEditorLibrary.compile_blueprint` + `save_loaded_asset`），不需要用户手动操作。UE 未开启时才退回手动方式。
5. 整个流程涉及 P4 文件操作，参照 `.claude/skills/p4-workflow/SKILL.md` 管理 changelist。
6. **编译工程时**（如文档提及"需要编译工程"），应选择 **DebugGame_Editor** 方案进行编译，不要选择 Development 或 DebugGame。

---

## 脚本使用（entity_modifier.py）

**脚本路径：** `Main/Plugins/PLPythonPipeline/Content/Python/entity_modifier.py`

该脚本整合了 **Tag 修改**（原 `entity_tag_modifier.py`）和**属性修改**两类操作。

### Tag 操作（子命令: tag）

自动完成流程的 **a.1 → a.5** 步骤（在主表中查找实体、校验规则、写入 Excel、标记 EPI 变动）。a.6（导出）可通过 `--run-export` 参数触发。a.7（export row to dataasset）当 UE 已开启时 AI 通过 ue-cli 自动完成，UE 未开启时才需要用户手动操作。

```bash
# 增加 tag
python entity_modifier.py Entity.FireMaker tag add AssetTag.CanHangOnMount

# 改变 tag（格式: 旧值:新值）
python entity_modifier.py Entity.FireMaker tag change EntityType.Material:EntityType.Food

# 删除 tag
python entity_modifier.py Entity.FireMaker tag remove AssetTag.CanHangOnMount

# 修改后自动执行 excel_exporter 导出（a.6）
python entity_modifier.py Entity.FireMaker tag add AssetTag.CanHangOnMount --run-export

# 修改后自动执行导出 + export row to dataasset（需 UE 编辑器开启 + SoftUEBridge 连接）
python entity_modifier.py Entity.FireMaker tag remove AssetTag.UnInteractable --run-export --export-to-bp

# 指定 P4 changelist
python entity_modifier.py Entity.FireMaker tag add AssetTag.CanHangOnMount --run-export --changelist=88000

# 仅检查，不写入
python entity_modifier.py Entity.FireMaker tag add AssetTag.CanHangOnMount --dry-run
```

### 属性操作（子命令: attr）

对应流程 **2.1 → 2.7**，脚本全程自动完成：

| 模式 | 用途 |
|------|------|
| `--query` | 查询 InstanceTag 及共享情况（只读） |
| `--set` | **直接修改属性值**（推荐，完整自动化） |
| `--ensure-unique` | 仅拆分独占 InstanceTag，不写属性值 |

#### `--set`（推荐）完整流程（自动执行 2.1→2.7）

1. 找实体 InstanceTag（步骤 2.1、2.2）
2. 检查 InstanceTag 是否被多行共享（步骤 2.3）
3. 若共享 → 自动拆分（注册新 tag、更新主表、复制 EnitiyInstanceConfig 行）（步骤 2.4.2→2.6）
4. 在所有属性子表中搜索 `--attr-name` 对应列（步骤 2.7）
5. 写入 `--value` 到对应子表的对应单元格

```bash
# 修改属性值（精确列名）
python entity_modifier.py Entity.FireMaker attr --set --attr-name=IgnitionPoint --value=300

# 修改属性值（模糊列名，脚本自动在所有属性子表中搜索匹配列）
python entity_modifier.py Entity.FireMaker attr --set --attr-name=燃点 --value=300

# 修改后自动执行 excel_exporter 导出
python entity_modifier.py Entity.FireMaker attr --set --attr-name=IgnitionPoint --value=300 --run-export

# InstanceTag 共享时手动指定新 tag 名称
python entity_modifier.py Entity.FireMaker attr --set --attr-name=IgnitionPoint --value=300 \
    --new-instance-tag=Instance.FireMaker_Unique

# dry-run 预览全流程，不写入任何文件
python entity_modifier.py Entity.FireMaker attr --set --attr-name=IgnitionPoint --value=300 --dry-run

# 查询 InstanceTag 共享情况（不写入）
python entity_modifier.py Entity.FireMaker attr --query

# 仅拆分独占 InstanceTag，不修改属性值
python entity_modifier.py Entity.FireMaker attr --ensure-unique
python entity_modifier.py Entity.FireMaker attr --ensure-unique --new-instance-tag=Instance.FireMaker_Unique
```

#### 属性子表列表（`--attr-name` 搜索范围）

脚本会在以下所有子表的**表头**中搜索 `--attr-name`，支持精确列名和模糊关键词：

| 文件名 | 内容说明 |
|--------|----------|
| `EntityBattleAttributeConfig.xlsx` | 实体战斗属性基础值 |
| `EntityBattleAttributeRoteConfig.xlsx` | 实体战斗属性倍率值 |
| `EquipBattleAttributeConfig.xlsx` | 装备属性基础值 |
| `EquipBattleAttributeRoteConfig.xlsx` | 装备属性倍率值 |
| `ExpAutoValuesConfig.xlsx` | 经验自动计算相关 |
| `ExpDropConfig.xlsx` | 经验掉落相关 |
| `PhaseChange_BBQAttributeConfig.xlsx` | 烤相关属性 |
| `PhaseChange_BurningAttributeConfig.xlsx` | 燃烧相关属性 |
| `PhaseChange_CookingAttributeConfig.xlsx` | 食物属性（非食物通常无） |
| `PhaseChange_FreezeAttributeConfig.xlsx` | 冻结相关属性 |
| `OtherAttributeConfig.xlsx` | 杂项属性 |
| `Pet_AttributeConfig.xlsx` | 宠物驯养相关属性 |
| `PhaseChange_GrowAttributeConfig.xlsx` | 生长相关属性 |
| `PhaseChange_MeltAttributeConfig.xlsx` | 熔炼相关属性 |
| `PhaseChange_PressureAttributeConfig.xlsx` | 压力相关属性 |
| `PhaseChange_ProsperityAttributeConfig.xlsx` | 繁茂相关属性 |
| `PhaseChange_TemperatureHumidityAttributeConfig.xlsx` | 温度湿度相关属性 |
| `PhaseChange_WatchAttributeConfig.xlsx` | 观察相关属性 |
| `PhysicsAttributeConfig.xlsx` | 物理相关属性 |
| `DropLibraryConfig.xlsx` | 物品掉落模板 |
| `DropConfig.xlsx` | 具体掉落配置 |

**自动执行的规则校验（Tag 操作）：**
- 重复 tag → 拒绝并报错
- 增加 `Entity./Character./Building.` 前缀的 tag → 拒绝（EntityTag 只能 change）
- 增加 `EntityRarity.` 前缀的 tag → 拒绝（RarityTag 只能 change）
- 增加 `Instance.` 前缀的 tag，但该实体已有 InstanceTag → 拒绝（已存在时只能 change）
- 增加 `Instance.` 前缀的 tag，该实体无 InstanceTag → 允许新增
- 删除 EntityTag / RarityTag → 拒绝（只能 change）
- 删除 InstanceTag → 允许

---

---

## 新增实体标准流程

> **触发词：** 新增实体、添加实体、创建实体、新建 Entity/Character tag

飞书文档原文：https://cyancook.feishu.cn/wiki/RObPwSbMniTSqpkVq43cQc2inHU

### 流程总览

| 步骤 | 阶段 | 脚本/工具 | 是否需要 UE 进程 |
|------|------|-----------|-----------------|
| 一 | 注册 EntityTag | `entity_adder.py tag-register` | **否**（自动检测 UE；未开启直接完成；已开启写入后提示关闭再编译） |
| 二 | 复制蓝图 | `entity_adder.py bp-copy` | **是**（自动检测 UE；已开启通过 SoftUEBridge 自动完成；未开启给出提示） |
| 三 | 主表通用列 | `entity_adder.py excel-common` | 否 |
| 四 | 主表非通用列 | `entity_adder.py excel-custom` | 否 |
| 五 | 扩展关联表+导出 DT | `entity_adder.py finalize` | **是** |

**步骤一和步骤二无严格先后顺序**，根据 UE 是否开启动态决定：

| UE 状态 | 推荐策略 |
|---------|---------|
| **UE 未开启** | 先步骤一（自动完成）→ 提示编译 → 开启 UE → 步骤二 |
| **UE 已开启** | 先步骤二（SoftUEBridge 自动完成）→ 关闭 UE → 步骤一编译 |

---

### 步骤一：注册 EntityTag（`tag-register`）

**（非脚本部分）** 先从用户处获得待新增实体 tag。

**自动化逻辑（无需用户介入）：**
1. 通过 SoftUEBridge 检测 UE 是否运行
2. 检查 `Main/RawData/GameplayTag/EntityTag.xlsx` 是否已有该 tag
3. 若无，`p4 edit` 后追加新行并保存
4. 根据 UE 状态给出对应提示

```bash
python entity_adder.py tag-register Entity.NewSword
python entity_adder.py tag-register Entity.NewSword --dry-run
```

> ⚠️ **编译警告**：写入后必须**关闭 UE Editor**，重新编译工程（DebugGame_Editor），否则 UE5 不识别新 tag。

---

### 步骤二：复制蓝图（`bp-copy`）

**（非脚本部分）** 需从用户获得：
- 待新增实体 tag
- 最接近的类似实体 tag
- 预期目录（`\Main\Content\007_Entities\` 的子目录，不可选 000_Template / 06_Plant / 01_Uncategoried；若子目录下还有子目录，需再询问；允许新建目录）

**自动化逻辑（`bp-copy` 推荐命令）：**
- **UE 已开启** → 通过 SoftUEBridge `run-python-script` 内联执行蓝图复制，新增 BP 自动移入目标 CL
- **UE 未开启** → 打印旧版命令行提示，等待用户开启 UE 后重新执行

**关键经验（2026-04-17 验证）：**
- `EditorAssetLibrary.duplicate_asset` **必须在完整 UE Editor 进程中执行**，在 `-run=pythonscript` Cmd.exe commandlet 模式下不可用（`does_asset_exist` 始终返回 False）
- 正确方式：SoftUEBridge `run-python-script` 内联代码；**不能通过 `exec(open(...).read())` 加载文件**（因 `__file__` 未定义）
- 内联脚本中路径必须用硬编码绝对路径或从外部传参字符串

```bash
# 推荐：自动检测，已开启则 SoftUEBridge 自动完成
python entity_adder.py bp-copy Entity.NewSword \
    --similar=Entity.FireMaker \
    --target-dir=/Game/007_Entities/002_Tools/ \
    --changelist=88000

python entity_adder.py bp-copy Entity.NewSword \
    --similar=Entity.FireMaker \
    --target-dir=/Game/007_Entities/002_Tools/ \
    --dry-run

# 兼容旧版：仅打印 UE 命令行（UE 未开启时的备用方案）
python entity_adder.py bp-command Entity.NewSword \
    --similar=Entity.FireMaker \
    --target-dir=/Game/007_Entities/002_Tools/
```

> 成功判据：`/Game/.../BP_NewSword` 在 UE Content Browser 可见，P4 状态为 add，已在指定 CL 中。

**蓝图命名规则：**
| Entity tag | BP 名 |
|------------|-------|
| `Entity.FireMaker` | `BP_FireMaker` |
| `Entity.Item.FireMaker` | `BP_Item_FireMaker` |
| `Character.Monster.Frog` | `BP_Monster_Frog` |

---

### 步骤三：填充主表通用列（`excel-common`）

**（非脚本部分）** 需从用户获得同步骤二相同的信息（如连续流程则复用）。

**脚本逻辑（含 5 条关键修正规则）：**
1. 检查核心主表中是否已有该 entity_tag 行，若有则跳过
2. 查找类似实体，获取其 **B(group) 分组号**
3. **⚠️ 插入位置：扫描同一 group 的最后一行，`insert_rows` 插入其后**（不是表格末尾 `append`）
4. 写入各列（见下表）

| 列 | 写入值 | 规则说明 |
|----|--------|---------|
| A(0) | `=B{r}*1000+D{r}` | 公式 |
| **B(1)** | **与 similar 实体相同的分组号** | **直接复用，不新建分组** |
| **D(3)** | `=IF(B{r}=B{r-1},D{r-1}+1,1)` | **r-1 必须是同组最后行（有数据），不能引用空行** |
| E(4)/N(13) | entity_tag | 实体 tag |
| J(9) | `0\|0\|0` | 默认值 |
| K(10) | prepath | 蓝图目录 |
| **L(11)** | **`=IF(K{r}="","",IF(LEFT(E{r},7)="Entity.",K{r}&_xlfn.LET(...`** | **必须填与现有行完全一致的公式，不能留空** |
| M(12) | 条件：similar M 列有值时填 `/Game/007_Entities/013_ArmorAccessory/BP_<名>_Equip.BP_<名>_Equip_C` | |
| Y(24) | `False` | Python bool |
| AA(26) | `0` | |
| AB(27) | `none` | |
| AD(29) | `1` | |
| **AE(30)** | **`True` 或 `False`（Python bool）** | **不填 1/0** |

```bash
python entity_adder.py excel-common Entity.NewSword \
    --similar=Entity.FireMaker \
    --prepath=/Game/007_Entities/002_Tools/ \
    --changelist=88000

# dry-run 预览不写入
python entity_adder.py excel-common Entity.NewSword \
    --similar=Entity.FireMaker \
    --prepath=/Game/007_Entities/002_Tools/ \
    --dry-run
```

---

### 步骤四：填充主表非通用列（`excel-custom`）

**（非脚本部分）** 建议用户手动在 Excel 中填充；若用户要求在 AI 中继续，则需用户提供以下信息：
- **C列（groupdesc）**：分组类型
- **F列（InstanceTag）**：属性模板 tag
- **G列（EntityName2）**：中文名
- **H列（EntityDesc）**：描述
- **I列（ThinkDesc）**：思考描述
- **O列（EntityTypes）**：类型 tag（`|` 分隔）
- **R/S/T/U/V/W/X/Z列**：各 bool 属性
- **AF列（RarityTag）**：稀有度 tag（EntityRarity.Common/UnCommon/Rare/Unique）
- **AG列（OtherTags）**：其他 tag（`|` 分隔）
- **AC列（SoftCharacterActorClass）**：若是 Character 实体，还需提供蓝图路径

```bash
python entity_adder.py excel-custom Entity.NewSword \
    --groupdesc=武器 \
    --name-cn=新剑 \
    --entity-types="EntityType.Weapon" \
    --stack-limit=1 \
    --can-stack=False \
    --can-pickup=True \
    --can-lift=True \
    --rarity-tag=EntityRarity.Common \
    --other-tags="|AssetTag.CanHangOnMount" \
    --dry-run
```

---

### 步骤五：扩展关联表 + 导出 DT（`finalize`）

**（非脚本部分）** 需从用户获得同上信息（连续流程复用）。

**脚本逻辑：**
1. 调用 `table_module.table_manager --command=add-entity` 将新实体扩展至所有关联属性子表（复制自类似实体行）
2. 执行 `excel_exporter.py --precheckin --p4` 将所有变动的 Excel 导出为 DataTable 资产
3. 提示在 UE 编辑器手动执行 export row to dataasset

```bash
python entity_adder.py finalize Entity.NewSword \
    --similar=Entity.FireMaker \
    --changelist=88000

# dry-run 预览
python entity_adder.py finalize Entity.NewSword \
    --similar=Entity.FireMaker \
    --dry-run
```

> 成功判据：
> - add-entity 成功：关联属性子表新增了对应行
> - excel_exporter 成功：`DT_PLEntityTagMapping` 等 DataTable 发生变动
> - export row to dataasset 成功：对应 BP 文件发生变动

---

### 主表列速查（PLEntityTagMapping.xlsx，0-based 索引）

| 列 | 索引 | 字段名 | 通用/非通用 | 默认值 |
|----|------|--------|------------|--------|
| A | 0 | EntityId | 公式 | `=B*1000+D` |
| B | 1 | group | 复制自similar | — |
| C | 2 | groupdesc | **非通用** | — |
| D | 3 | index | 公式 | 自动递增 |
| E | 4 | Name | **通用** | = entity_tag |
| F | 5 | InstanceTag | **非通用** | — |
| G | 6 | EntityName2 | **非通用** | — |
| H | 7 | EntityDesc | **非通用** | — |
| I | 8 | ThinkDesc | **非通用** | — |
| J | 9 | ReactionWidgetOffset | **通用** | `0\|0\|0` |
| K | 10 | prepath | **通用** | 用户提供 |
| L | 11 | SoftActorToSpawnClass | 公式 | 由 K+E 自动算 |
| M | 12 | SoftActorToEquip | **通用（条件）** | 类似实体有则填 |
| N | 13 | EntityTag | **通用** | = entity_tag |
| O | 14 | EntityTypes | **非通用** | — |
| R | 17 | ItemStackCountLimit | **非通用** | — |
| S–X | 18–23 | 各 bool 属性 | **非通用** | — |
| Y | 24 | bCanBeRope | **通用** | False |
| Z | 25 | bHasDurability | **非通用** | — |
| AA | 26 | EnterContainerType | **通用** | 0 |
| AB | 27 | MeshName | **通用** | none |
| AC | 28 | SoftCharacterActorClass | **非通用** | — |
| AD | 29 | InUse | **通用** | 1 |
| AE | 30 | NeedPhaseComponent | **通用** | 1 |
| AF | 31 | RarityTag | **非通用** | — |
| AG | 32 | OtherTags | **非通用** | — |

---

### 脚本说明（entity_adder.py / entity_blueprint_ue.py）

| 脚本 | 路径 | 运行环境 |
|------|------|----------|
| `entity_adder.py` | `Main/Plugins/PLPythonPipeline/Content/Python/entity_adder.py` | 普通 Python |
| `entity_blueprint_ue.py` | `Main/Plugins/PLPythonPipeline/Content/Python/entity_blueprint_ue.py` | **UE 进程内**（`-run=pythonscript`）|

两者均通过 `__file__` 向上5级动态定位项目根目录，无绝对路径。

---

## 常见错误排查

### `text_map_type` 报错：`Base Id require to be set > 0`

**现象：** 运行 `excel_exporter.py` 时，某行抛出此异常，错误信息类似：
```
Exception: Base Id require to be set > 0
  at EntityId column, row: Entity.XXX
```

**根本原因：**
- 该行的 `EntityName2`（或 `EntityDesc`/`ThinkDesc` 等文本列）有非空内容，触发了 `textmap` 类型解析
- 同时该行的 `EntityId`（A列，公式 `=B*1000+D`）由 Excel 公式计算，但 openpyxl 以 `data_only=True` 读取时返回 `None`（Excel 未曾在本机打开计算过该公式，缓存值为空）
- `id_offset == 0 or None` → 抛出 "Base Id require to be set > 0"

**修复方法（推荐：COM 自动化，无需手动操作）：**

用 win32com 让 Excel 进程打开文件、强制重算、保存，openpyxl 下次读取时缓存值即为正确整数：

```python
import win32com.client, os
path = os.path.abspath('Main/RawData/PLEntityTagMapping.xlsx')  # 替换为实际报错的文件
excel = win32com.client.Dispatch('Excel.Application')
excel.Visible = False
excel.DisplayAlerts = False
wb = excel.Workbooks.Open(path)
excel.CalculateFull()
wb.Save()
wb.Close()
excel.Quit()
```

完成后直接重新运行 `excel_exporter.py` 即可。

**备用方法（手动）：**
1. 在错误信息中找到报错的行名（如 `Entity.Poison`）
2. 用 Excel 打开对应主表，找到该行
3. 定位到 **A列（EntityId）**，该单元格显示为公式 `=B*1000+D`
4. **将该公式替换为手动输入的整数值**（例如公式结果是 2042，就直接输入 `2042`）
5. 保存文件后重新运行 `excel_exporter.py`

> ⚠️ **注意：** 同一文件中其他行的 A列保持公式不变；只需将报错行转为硬编码值。
> 其他行之所以不报错，是因为它们的 `EntityName2` 等文本列为空，`textmap` 类型在空值时直接返回 0，不会执行到 Base Id 检查。

---

### `GameplayTag validation` 报 invalid tag：新实体 tag 未被 UE 识别

**现象：** 导出时报错：
```
❌ Error: Found 1 columns with invalid GameplayTags:
  PLEntityTagMapping.EntityTag: 1 invalid tags
  - Row XXX: 'Entity.NewXxx'
```

**根本原因：**
- `Entity.xxx` tag 的注册方式是：`EntityTag.xlsx` → `excel_exporter` 生成 `EntityGameplayTags.h/.cpp`（AutoGen C++ 文件）→ 编译进引擎 → UE GameplayTagsManager 启动时加载
- 若新 tag 在 AutoGen 文件里但从未编译，或 AutoGen 文件本身就没更新，UE 启动时不认识这个 tag
- `validate_gameplay_tags` 调用的是 UE 运行时内存中的 GameplayTagsManager，无法热更新

**修复流程：**
1. 确认 `Main/Plugins/DataManager/Source/TableDataManager/Private/AutoGen/EntityGameplayTags.h` 里有该 tag 的 `UE_DECLARE_GAMEPLAY_TAG_EXTERN`
2. 若没有：先关闭 UE，用 Cmd.exe 模式跑一次 `excel_exporter.py --forceall`（或带 EntityTag.xlsx 的 precheckin 导出），让 AutoGen 文件更新
3. **关闭 UE → 重新编译工程（DebugGame_Editor）**
4. 重新开启 UE → 再触发导出

**关键约束：**
- EntityTag.xlsx 必须在目标 CL 里（precheckin 模式只处理该 CL 内的文件）
- `--precheckin` 模式下即使只导 EntityTag.xlsx，最终校验仍对全表执行——必须编译后 UE 认识 tag 才能通过
- `GameplayTagTable`（EntityTag.xlsx 对应的表）的 `PackagePath` 为空，**不导出 DataTable 资产**，只生成 C++ AutoGen 文件

---

## 参考文档（飞书）

- 山外山工具链设计纲要：https://cyancook.feishu.cn/wiki/LSxYw1NddiQgg4kvRVacMEbGnlg
- 山外山工具链AI读取文档：https://cyancook.feishu.cn/wiki/MXIsw42HKi2AtDkZ4xic5cMbn3e
- 实体修改常用流程：https://cyancook.feishu.cn/wiki/SlDRwmwl0iIMBukqxwhc9NG7nxd
