---
name: entry-design
description: 装备词条策划职责参考。覆盖词条设计、词条效果配置、词条池配表流程（Excel→脚本→JSON）、词缀系统、通货操作语义。当用户提到"词条"、"配表"、"词条池"、"词条设计"、"词条效果"、"词缀"、"affix"、"通货"、"增幅石"、"崇高石"、"重铸石"、"混沌石"、"前缀"、"后缀"、"词条平衡"、"词条描述" 时自动注入上下文。
tags:
  - 词条
  - 配表
  - 词条池
  - 词条设计
  - 词条效果
  - 词缀
  - affix
  - 通货
  - 增幅石
  - 崇高石
  - 重铸石
  - 混沌石
  - 前缀
  - 后缀
  - 词条平衡
  - 词条描述
  - EquipEntryPool
---

# 装备词条系统 — 策划参考

> Layer: Tier 3 (Plugin / Design)
> Plugin: `GASExtendedPL`

<memory category="core-rules">
## 词条系统范围

词条系统不只用于"装备词条"，游戏中多个子系统都用同一套 `UPLEquipmentEntryInst` 类体系实现，通过 GA/GE 挂载功能。所有词条汇总在：

**`/Game/000_GlobalSettings/DataTables/EquipmentEntry/CDT_TotalEntry.CDT_TotalEntry`**

其中包含 6 张子表，按命名即可识别各自功能。`DT_Old_EquipmentEntry` 代表"装备词条"这套子系统。其他子表分别对应材料特性、食物效果、歃附魔等。

---

## 词条设计基本概念

### 词条结构
每个词条（Entry）由以下要素构成：

| 要素 | 说明 |
|------|------|
| **词条 Tag** | 唯一标识，格式 `EquipmentEntry.*`（如 `EquipmentEntry.AddMaxHealth`） |
| **稀有度** | `Normal`（普通）/ `Unique`（独特） |
| **前/后缀位置** | `Prefix`（前缀）/ `Suffix`（后缀）/ `None`（无限制） |
| **触发时机** | 决定词条何时生效，见下方触发时机列表 |
| **参数** | 词条数值范围（MinValue ~ MaxValue），按等级分组 |
| **效果** | 触发时对装备/角色/其他 Actor 施加的 GE、Ability 或 Tag |

### T级数值标准模

装备词条数值使用“标准模”作为横向平衡基准。默认先覆盖 1-30 级，对应 3 个 T 级：

| T级 | 装备等级段 | 标准模倍率 |
|-----|------------|------------|
| T1 | 1-10 | 1.0x |
| T2 | 10-20 | 1.5x |
| T3 | 20-30 | 2.0x |

基础规则：
- 每 10 级提升一个 T 级，先配到前 30 级，即 `MinLevel=1/10/20` 三档
- T1 使用标准模，随机浮动按标准模的 `0.8x-1.2x`
- 每往上一个 T 级，中心值提升 50%
- T级区间默认：T1 `0.8x-1.2x`，T2 `1.2x-1.8x`，T3 `1.8x-2.2x`

当前标准模：
- INC 伤害词条（如 `xxx伤害提高{1}%`）：标准模 `5%`，T1 `4%-6%`，T2 `6%-9%`，T3 `9%-11%`
- 点伤害词条（如 `xxx伤害增加{1}点`）：标准模 `5点`，T1 `4-6`，T2 `6-9`，T3 `9-11`
- 攻击速度/动作速度词条（如 `xxx速度提高{1}%`、攻速类）：标准模 `5%`，T1 `4%-6%`，T2 `6%-9%`，T3 `9%-11%`

落表注意：
- 飞书 `词条T级属性` 使用 `(Name:1,MinLevel:1,Value:0.04-0.06,Name:1,MinLevel:10,Value:0.06-0.09,Name:1,MinLevel:20,Value:0.09-0.11,Weight:1000)` 这类格式
- `EquipmentEntryInfoDef.xlsx` 是当前权威生效表；同步 T 级数值时要同时更新 `MinEquipLevel/MaxEquipLevel/LevelWeight/ParameterMinValue/ParameterMaxValue`
- `EquipmentEntryInfoDef.xlsx` 的 3 档 MaxEquipLevel 按 `10/20/30` 落，不再把第 3 档无限延伸
- `EquipmentEntryInfoDef.xlsx` 的 `ParameterNameN` 必须使用数字字符串，对应词条描述中的占位符：`ParameterName1=1` 对应 `{1}`，`ParameterName2=2` 对应 `{2}`，以此类推；不要用 `Damage`、`Health`、`Dura` 这类语义名填 `ParameterName`
- 修表时要校验 `ParameterMinValueN/ParameterMaxValueN` 是否完整对应同一个 `{N}`；单值必须写成 `Min==Max`，不要只填一侧；描述没有 `{2}` 时不要残留空的 `ParameterName2/ParameterTag2`
- 若策划提供外部 T 级表（如桌面 `词条T级.xlsx`），外部表优先于标准模；必须先 `p4 edit` 迁出 `EquipmentEntryInfoDef.xlsx`，按外部表的 `随机下限/随机上限/等级下限/等级上限/权重` 完整落入 Info 表，再同步飞书
- 外部 T 级表如果存在每档不同 `权重` 或明确 `等级上限`，飞书 `词条T级属性` 要使用带 `MaxLevel` 和逐档 `Weight` 的完整格式，例如 `(Name:1,MinLevel:1,MaxLevel:14,Value:4-6,Weight:50,Name:1,MinLevel:8,MaxLevel:100,Value:12-18,Weight:50)`
- 当前桌面通用词条 T 级表分类：`斩打突点伤`、`装备攻击力百分比`、`INC百分比伤害`、`元素点伤`、`B区攻速/战斗乘区`、`HP/血量增加X%`、`HP/点血量`；不要把没有明确分类的移动速度、防御、回复速度、暂不考虑词条硬套进这些配置

### 触发时机（策划视角语义）

| 触发时机 | 中文含义 | 典型用途 |
|----------|----------|----------|
| `Permanent` | 装备时立即生效，卸装时失效 | 被动属性加成（+血量、+护甲） |
| `OnHitOtherBeforeDamage` | 攻击命中对方、伤害计算前 | 修改伤害值、附加特殊效果 |
| `OnHitOtherAfterDamage` | 攻击命中对方、伤害结算后 | 击中后触发的额外效果 |
| `OnBeHitBeforeDamage` | 被攻击命中、受伤计算前 | 减伤、格挡类效果 |
| `OnBeHitAfterDamage` | 被攻击命中、受伤结算后 | 受伤后反击类效果 |
| `OnTagChanged` | Owner 身上某个 Tag 数量变化时 | 状态联动（如中毒时触发） |
| `OnAttributeChanged` | Owner 某个属性值变化时 | 血量阈值触发（如血量低于30%） |
| `OnGameplayEvent` | 收到指定 GameplayEvent 时 | 技能联动触发 |
| `BeforeDeadDamage` | 受到致命伤害前 | 免死类词条 |
| `OnAttachToInstance` | 词条附加到物品时（一次性） | 附加时立即产生效果 |

### bActivateOnce 规则
- 开启后：角色身上同 Tag 词条同时只允许一个激活（后来的等待，前者消失后自动补上）
- 关闭后：同 Tag 多件装备上的词条可同时叠加生效
- 独特词条（Unique）通常开启此选项

### 词条来源类型
| 来源 | 含义 |
|------|------|
| `Random` | 装备掉落时随机生成 |
| `Affix` | 词缀系统分配 |
| `Sha` | 歃词条（特殊机制） |
| `Default` | 暗金装备固定词条 |
</memory>

<memory category="config-workflow">
## 词条池配表工作流（Excel → 游戏）

### 涉及文件
| 文件 | 用途 |
|------|------|
| `ClaudeTasks/EquipEntryPoolConfig/Entry_Pool.xlsx` | **主配表**（策划编辑这个） |
| `ClaudeTasks/EquipEntryPoolConfig/Entry_EquipmentTag.xlsx` | 装备类型中文名 → GameplayTag 映射 |
| `ClaudeTasks/EquipEntryPoolConfig/Entry_List.xlsx` | 词条中文名 → `EquipmentEntry.*` Tag 映射 |
| `ClaudeTasks/EquipEntryPoolConfig/generate_config.py` | 生成脚本 |
| `Main/RawData/EquipEntryPoolConfig.xlsx.json` | 输出（游戏读取） |
| `Main/RawData/EquipEntryPoolConfig.xlsx` | 输出（人工核查用） |

### 操作步骤
1. 编辑 `Entry_Pool.xlsx`
   - 修改词条中文名、调整权重（保持小数格式如 `108.0`）
   - 添加/删除行时注意：**第 16 行是前缀/后缀分界线**
2. **关闭** `Main/RawData/EquipEntryPoolConfig.xlsx`（否则脚本无法写入）
3. 运行脚本：
   ```bash
   python ClaudeTasks/EquipEntryPoolConfig/generate_config.py
   ```
4. 检查脚本输出中的警告：
   ```
   ⚠ 警告: 以下词条缺少Tag映射 (共N个):
       - 某词条名
   ```
   有警告说明该词条在 `Entry_List.xlsx` 里没有对应映射，**缺少映射的词条会被静默跳过**
5. 验证输出：
   - 装备类型数量正确（当前 14 种）
   - 权重为浮点数（`108.0` 而非 `108`）
6. 在 UE Editor 里导入 `EquipEntryPoolConfig.xlsx.json`

### 常见问题
| 现象 | 原因 | 解决 |
|------|------|------|
| 某装备类型的词条池为空 | `Entry_EquipmentTag.xlsx` 缺少该类型的 Tag 映射 | 在映射表里补充该中文名对应的 Tag |
| 某词条未出现在池里 | `Entry_List.xlsx` 缺少该词条的 Tag 映射 | 在映射表里补充该词条对应的 `EquipmentEntry.*` Tag |
| Excel 保存失败 | 输出文件被 Excel 占用 | 关闭 Excel 重新运行脚本（JSON 仍会正常保存） |
| 权重格式错误 | 单元格格式为整数 | 将列格式改为数值并保留一位小数 |

### 当前装备类型（14 种）
| 中文 | Tag |
|------|-----|
| 头盔 | `EntityType.Equip.Helmet` |
| 胸甲 | `EntityType.Equip.ChestPlate` |
| 裤子 | `EntityType.Equip.Leggings` |
| 鞋子 | `EntityType.Equip.Shoes` |
| 手套 | `EntityType.Equip.Gloves` |
| 饰品 | `EntityType.Equip.Charm` |
| 盾牌 | `EntityType.Hand.Shield` |
| 单手斧 | `EntityType.Hand.Axe` |
| 单手锤 | `EntityType.Hand.Hammer` |
| 单手矛 | `EntityType.Hand.Spear` |
| 双手斧 | `EntityType.Hand.Axe2H` |
| 双手锤 | `EntityType.Hand.Hammer2H` |
| 笛子 | `EntityType.Hand.HornBone` |
| 弓箭 | `EntityType.Hand.Bow` |
</memory>

<memory category="entry-pool-config">
## 词条池配置表（EquipEntryPoolConfig.xlsx）

**文件路径：** `Main/RawData/EquipEntryPoolConfig.xlsx`

该表定义了每种装备类型的词条池（哪些词条可以出现、出现概率权重），是词条池系统的权威配置源。

### 表结构

| 列名 | 类型 | 说明 |
|------|------|------|
| `Id` | `INT&index` | 行索引 |
| `注释` | — | 人工备注（不影响游戏） |
| `EquipSlot` | `tag` | 装备类型 Tag，格式 `EntityType.Equip.*` 或 `EntityType.Hand.*` |
| `PrefixesNumber` | `list[,](tuple[:](tag:float))` | **前缀池**：逗号分隔的 `词条Tag:权重` 列表 |
| `SuffixesNumber` | `list[,](tuple[:](tag:float))` | **后缀池**：逗号分隔的 `词条Tag:权重` 列表 |

### 数据格式示例

```
Entry.Equipment.AddEquipmentDef:86.0,Entry.Equipment.AddHpRestore:86.0,Entry.Equipment.AddFoodResult:33.0
```

- 词条 Tag 格式：`Entry.Equipment.<词条名>`
- 权重为浮点数（`86.0` 而非 `86`），影响随机掉落概率
- 前缀池和后缀池完全独立，同一词条可同时出现在两个池中

### 当前覆盖装备类型（14 种）

| EquipSlot | 中文 |
|-----------|------|
| `EntityType.Equip.Helmet` | 头盔 |
| `EntityType.Equip.ChestPlate` | 胸甲 |
| `EntityType.Equip.Leggings` | 裤子 |
| `EntityType.Equip.Shoes` | 鞋子 |
| `EntityType.Equip.Gloves` | 手套 |
| `EntityType.Equip.Charm` | 饰品 |
| `EntityType.Hand.Shield` | 盾牌 |
| `EntityType.Hand.Axe` | 单手斧 |
| `EntityType.Hand.Hammer` | 单手锤 |
| `EntityType.Hand.Spear` | 单手矛 |
| `EntityType.Hand.Axe2H` | 双手斧 |
| `EntityType.Hand.Hammer2H` | 双手锤 |
| `EntityType.Hand.HornBone` | 笛子 |
| `EntityType.Hand.Bow` | 弓箭 |

### 与飞书表格的对应关系

飞书装备词条多维表格中的"出现部位"、"前后缀"字段，均来源于此表的解析结果（通过 `generate_config.py` 脚本生成后同步）。

### 编辑注意事项

- 权重必须为浮点格式（保留一位小数），整数格式会导致导入异常
- 修改后运行 `python ClaudeTasks/EquipEntryPoolConfig/generate_config.py` 重新生成 JSON
- 脚本运行前需关闭 `Main/RawData/EquipEntryPoolConfig.xlsx`（否则无法写入输出文件）
</memory>

<memory category="currency-and-affix">
## 通货与词缀系统

### 通货操作（词条改造）
| 通货 | 效果 | 适用对象 |
|------|------|----------|
| **增幅石** | 向物品添加 1 个随机词条 | 普通/非凡物品 |
| **崇高石** | 向物品添加 1 个随机词条 | 稀有物品 |
| **重铸石** | 移除物品上所有随机词条 | 任意 |
| **混沌石** | 移除所有随机词条后重新填满 | 任意 |

通货操作只影响来源为 `Random` 的词条，不影响 `Default`（暗金固定词条）和 `Affix`（词缀词条）。

### 词缀系统（Affix）
- 词缀（Affix Tag：`Affix.*`）通过 `FPLAffixToEquipmentEntry` DataTable 映射到具体词条
- 一个词缀可以对不同装备槽位分配不同词条（`EquipSlotEntry`）
- 词缀词条来源为 `EPLEntrySource::Affix`，不受通货影响

### GameplayTag 命名规范
- 词条 Tag：`EquipmentEntry.*`（如 `EquipmentEntry.AddMaxHealth`）
- 装备类型：`EntityType.Equip.*` / `EntityType.Hand.*`
- 词缀：`Affix.*`
- 特性：`Trait.*`
</memory>

<memory category="feishu-entry-maintenance">
## 飞书装备词条维护流程（待创建 / 待修复 / 待删除）

当用户要求根据飞书多维表同步装备词条时，默认同时核对这三层：

| 层级 | 必查内容 |
|------|----------|
| 飞书记录 | `词条名`、`词条tag`、`词条状态`、`词条依赖属性`、`期望属性`、`词条状态描述` |
| DT 配表 | `DT_Old_EquipmentEntry.csv` 中是否已有行、文案是否一致、是否仍挂着对应 GE |
| 项目资产 | `DefaultGameplayTags.ini`、`/Game/019_RPGModifiers/002_Equipment/Entry/GE/*` 是否存在且属性绑定正确 |

### 状态处理规则

#### 1. `待创建`
- 先看 `词条tag` 是否已存在；若飞书写成待创建但项目已有同语义词条，不能盲目重复造轮子
- 若 `词条依赖属性` 为空，则**不创建**
- 若项目中找不到期望依赖属性，则**不创建**；不要为了凑飞书去改成别的 tag 或别的属性
- 若只是缺少 GameplayTag，可在现有 `Entry.Equipment.*` 段中按相同命名格式新增
- 新词条要成套落地：`DefaultGameplayTags.ini`、`DT_Old_EquipmentEntry.csv`、对应 GE

#### 2. `待修复`
- 若 `期望属性` 有值且不是 `待定`，以 `期望属性` 作为修复目标
- 若 `期望属性` 为空，则以 `词条依赖属性` 作为修复目标
- 修复范围不仅是 GE 属性绑定；如果飞书文案已经改了，`DT_Old_EquipmentEntry.csv` 的描述也要同步
- 验证时必须直接检查 GE 实际 Modifier 绑定到的 `AttributeName`，不能只看脚本执行是否返回成功
- `CreateOrUpdateGameplayEffect` 在本项目里不适合作为“修已有 GE”的唯一验证手段；更稳妥的做法是直接修改 GE 蓝图默认对象的 `Modifiers`，然后编译并保存蓝图

#### 3. `待删除`
- 先删除 `DT_Old_EquipmentEntry.csv` 对应行
- 若 GE 没有其他词条复用，可直接删除对应 GE 资产
- 若 GE 仍被其他词条引用，则只能删词条，不能删 GE
- 默认**不要顺手删除 GameplayTag**；Tag 可能仍被历史存档、飞书记录或其他系统引用，除非用户明确要求一起清理
- 若本地存在该 GE 的导出 JSON/Readable 文件，也要一并清掉，避免后续误判

### 飞书字段冲突时的判定
- 若 `词条名` 与 `词条依赖属性` 语义冲突，先按属性名语义核对项目真实含义
- 在项目内落地时，以最终确认的依赖属性语义为准；不要把“错位的飞书文字”直接实现进项目
- 若后续需要回写飞书，先修正飞书中的错位记录，再改状态

### 推荐执行顺序
1. 从飞书筛出 `待创建`、`待修复`、`待删除`
2. 在 `DT_Old_EquipmentEntry.csv` 中核对当前 tag、描述、GE 引用
3. 统计 GE 是否被多条词条复用，再决定是否允许删除
4. 先改 CSV，再进编辑器修 GE / 删 GE，并重新导入 DataTable
5. 抽查 GE 的 `AttributeName`、确认待删除 GE 真的不存在
6. 把本次规则差异和特殊判断写入 `ClaudeTasks/Equipment/*.md`
</memory>
