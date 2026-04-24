# ConfigurationTools SKILL

## 概述

`Tools/ConfigurationTools/` 目录收录所有**策划用 DataTable / 资产自动配置工具**。
每个子目录对应一类配置任务，包含：
- `.bat` — 双击即可使用的交互式窗口工具
- `.py`  — 实际执行逻辑的 Python 脚本（通过 SoftUEBridge HTTP API 操作 Unreal Editor）
- `batch_input.txt` — 批量模式输入模板

**前提条件：** Unreal Editor 已打开，SoftUEBridge 插件正在运行。

---

## 工具列表

### ConfigFacilityOrAccessory — 建筑设施 / 配件条目配置

**目录：** `Tools/ConfigurationTools/ConfigFacilityOrAccessory/`

**触发词：** 注册建筑配件、注册建筑设施、配置配件、配置设施

**用途：** 给定一个建筑实体 EntityTag 和中文名称，自动完成四步 DataTable 配置：

| 步骤 | 目标 DataTable / 资产 | 写入内容 |
|------|-----------------------|----------|
| 1 | `DT_AchievementBuildMergeTag` | 注册图鉴 GameplayTag |
| 2 | `BuildingMergeAchievementList.xlsx` + TriggerExcelPreCheckinExport | 写入新行，Editor 内运行 excel_exporter 生成 `DT_BuildingMergeAchievementList` uasset（含本地化） |
| 3 | `AQ_<Name>` DataAsset + `DT_BuildingMergeAchievementList` | 创建 PLAchievementQuery，写入 AchievementQuery 字段 |
| 4 | `DT_BuildingBlockList` | 添加建造模块列表行（Type 自动从 DT_PLEntityTagMapping 推导） |

**使用方式：**

```
# 双击交互模式（推荐）
Tools\ConfigurationTools\ConfigFacilityOrAccessory\add_building_entry.bat

# 命令行单条（从项目根目录执行）
python Tools/ConfigurationTools/ConfigFacilityOrAccessory/add_building_entry.py "Entity.FireFlyLamp" "萤火灯"

# 批量模式（编辑 batch_input.txt 后执行）
add_building_entry.bat --batch batch_input.txt
```

**幂等性：** 每步均检查数据是否已存在，已存在则跳过（SKIP）继续下一步，可重复执行。

**关键文件：**

| 文件 | 说明 |
|------|------|
| `add_building_entry.bat` | 交互入口，检查依赖，调用 Python |
| `add_building_entry.py` | 核心逻辑 |
| `batch_input.txt` | 批量输入模板（格式：`EntityTag,中文名`） |

---

## 注意事项

### 前提条件（必须满足，否则会失败）

1. **UE Editor 必须已打开**，SoftUEBridge 插件正在运行（Step 1/3/4 依赖 bridge，Step 2 依赖 Remote Control）
2. **Remote Control 插件需在 30010 端口运行**（Step 2 调用 `TriggerExcelPreCheckinExport`）
3. **EntityTag 必须已注册到 PLEntityTagMapping.xlsx**（Step 0 推导 Type 依赖此表）
4. **必须有 pending 的具体编号 CL**（不能是 default），脚本通过 `p4 changes` 自动检测最近的 pending CL

### P4 文件管理

- 脚本会自动 `p4 edit` 所有需要修改的文件（uasset、xlsx）
- **AQ DataAsset**：UE Editor 在 default CL 创建，脚本执行后自动 `p4 reopen` 到当前 CL
- Step 2 的 xlsx 写入 + export 完成后，相关本地化文件（`ST_Text.csv`、`ST_Text.uasset`、`TextContent_Achievement_zhCN.xlsx`、`dt_metadata.json` 等）会被 excel_exporter 自动 checkout 到当前 CL

### Step 2 Export 说明

- **不走 PreCheckin.exe commandlet**，改为调用 Remote Control API `TriggerExcelPreCheckinExport`
- 在 Editor 进程内运行 excel_exporter，无文件锁问题，包含完整本地化链路
- export 完成后 `DT_BuildingMergeAchievementList` 的行由 excel_exporter 写入（含本地化），Step 3 再 patch `AchievementQuery` 字段

### Type 推导逻辑（自动）

- 读取 `Main/RawData/PLEntityTagMapping.xlsx`（CSV 备用）
- `EntityType.Building.Facility` → `BuildingBlock.Facility`
- `EntityType.Building.Accessory.X`（X 非 Big/Medium/Small）→ `BuildingBlock.Accessory.X`

---

## 新增工具规范

新增配置工具时，请在本 SKILL 的「工具列表」下追加一节，包含：
- 工具用途（一句话）
- 触发词
- 使用方式（bat 调用示例）
- 写入的 DataTable / 资产列表
- 注意事项
