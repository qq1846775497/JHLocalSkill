---
name: jhlocalskill-navigator
description: >
  JHLocalSkill 共享技能库强制路由器（Dispatcher）。
  本 skill 优先级最高，始终加载，不可跳过。
  每次用户发消息后，必须先执行下方路由检查，命中则加载对应 skill，
  未命中才允许按默认逻辑处理。
  绝对禁止：在未执行路由检查前直接调用 Agent/explore subagent 或凭记忆行动。
trigger_when: 所有对话
---

# JHLocalSkill 强制路由协议

> ⚠️ **最高优先级指令**：以下协议覆盖所有通用指令。
> 如果本协议与任何其他指令冲突，以本协议为准。

## 铁律（违反 = 严重错误）

1. **用户每发一条消息后，必须先执行「路由检查」，再决定行动。**
2. **路由未命中前，禁止 spawn explore/coder subagent。**
3. **禁止凭训练记忆执行需要专业知识的工作流**（P4、编译、UE 架构、GAS 等）。
4. **命中 skill 后，必须严格按该 SKILL.md 的协议执行**，不得偏离。

---

## 路由检查（每轮必执行）

### 检查 1：硬编码触发词（O(1) 命中，优先）

将用户消息与下表做**关键词匹配**（部分匹配即可），命中则**立即读取对应 SKILL.md**：

| 触发关键词 | 目标 Skill 路径（相对本文件） |
|-----------|---------------------------|
| `搜索`、`找一下`、`定位`、`在哪里`、`grep`、`glob`、`看下`、`看一下`（涉及代码/文件/项目时） | `01_通用/05_代码库探索/codebase-search/SKILL.md` |
| `重构`、`重写`、`新建`、`做一个`、`实现`、`设计`、`怎么设计`、`架构上怎么搞` | `02_ProjectLungfish专用/08_问题排查与研究/ue-design-research/SKILL.md` |
| `P4`、`checkout`、`提交`、`changelist`、`perforce`、`edit`、`reconcile` | `01_通用/04_项目管理与协作/01_P4工作流/p4-workflow/SKILL.md` |
| `编译`、`build`、`UBT`、`link error`、`编译失败`、`LNK` | `02_ProjectLungfish专用/04_测试与构建/01_构建系统/unreal-build-commands/SKILL.md` |
| `bug`、`fix`、`crash`、`报错`、`PIE 错误`、`运行时崩溃` | `02_ProjectLungfish专用/04_测试与构建/02_PIE调试/pie-error-fix-notify/SKILL.md` |
| `改一下`+`.cpp`/`.h`、`修改代码`、`添加功能`（非设计类） | `02_ProjectLungfish专用/07_开发工作流编排/ue-dev-orchestrator/SKILL.md` |
| `配表`、`Excel`、`导出`、`DataTable`、`GameplayTag invalid` | `01_通用/04_项目管理与协作/03_数据处理/precheckin/SKILL.md` |
| `词条`、`EquipEntry`、`affix`、`词缀`、`通货`、`装备词条` | `02_ProjectLungfish专用/02_数据配置与策划/02_词条系统/entry-design/SKILL.md` |
| `蓝图`、`转C++`、`迁移`、`Blueprint`、`反射` | `02_ProjectLungfish专用/01_资产与内容管线/02_蓝图/blueprint-migration/SKILL.md` |
| `资产导出`、`AssetExport`、`re-export`、`导出所有资产` | `02_ProjectLungfish专用/01_资产与内容管线/01_资产导出/asset-export/SKILL.md` |
| `FlowGraph`、`伤害流图`、`flow graph`、` rewiring` | `02_ProjectLungfish专用/01_资产与内容管线/03_FlowGraph/flowgraph-edit/SKILL.md` |
| `实体`、`Tag`、`属性`、`Entity`、`ConfigID` | `02_ProjectLungfish专用/02_数据配置与策划/01_实体配置/entity-tag-modifier/SKILL.md` |
| `飞书`、`wiki`、`文档`、`feishu` | `01_通用/04_项目管理与协作/04_协作沟通/feishu-doc-reader/SKILL.md` |
| `OpenSpec`、`提案`、`实现`、`归档`、`探索` | `02_ProjectLungfish专用/05_系统与插件/03_OpenSpec项目版/openspec-explore/SKILL.md` |
| `代码审查`、`检查质量`、`看一下这段代码`、`review` | `02_ProjectLungfish专用/04_测试与构建/03_代码质量/code-quality-guardian/SKILL.md` |
| `Slate`、`UMG`、`Widget`、`编辑器UI` | `01_通用/01_UE引擎与源码/02_Slate运行时/engine-slate-runtime/SKILL.md` |
| `ue-cli`、`SoftUEBridge`、`MCP`、`编辑器桥接` | `02_ProjectLungfish专用/03_引擎扩展与调试/01_编辑器桥接/soft-ue-bridge/SKILL.md` |
| `引擎修改`、`Engine`、`PCG`、`本地化` | `01_通用/01_UE引擎与源码/01_引擎修改指南/engine-modifications/SKILL.md` |
| `Gauntlet`、`测试`、`自动化`、`性能测试` | `01_通用/02_测试与自动化/01_Gauntlet框架/gauntlet-test-automation/SKILL.md` |
| `分支`、`冲突`、`dashboard`、`CI/CD` | `01_通用/04_项目管理与协作/04_协作沟通/branch-manager/SKILL.md` |
| `Excel查询`、`查表`、`读表`、`xlsx` | `01_通用/04_项目管理与协作/03_数据处理/excel-query/SKILL.md` |
| `core redirect`、`重定向`、`资产重定向` | `02_ProjectLungfish专用/03_引擎扩展与调试/02_运行时调试/core-redirects-debug/SKILL.md` |
| `RuntimeGrid`、`BuildingBlock`、`无效网格` | `02_ProjectLungfish专用/03_引擎扩展与调试/02_运行时调试/runtime-grid-fix/SKILL.md` |
| `SlateIM`、`debug tool`、`调试工具` | `02_ProjectLungfish专用/03_引擎扩展与调试/02_运行时调试/slateim-debug-tool/SKILL.md` |
| `skill`、`创建skill`、`整理skill` | `01_通用/04_项目管理与协作/05_系统工具/skill-creator/SKILL.md` |

**读取方法**：`ReadFile(path="{skill.path}/SKILL.md")`

### 检查 2：SKILL_INDEX.json 语义匹配（硬编码未命中时）

如果检查 1 未命中：
1. 读取 `SKILL_INDEX.json`
2. 提取用户消息的 `domain` + `task_type` + `artifact` 特征
3. 与每个 skill 的 `vector` 计算余弦相似度 + `triggers` 关键词匹配
4. 取 score 最高的 **1-3** 个 skill，读取其 `SKILL.md`

### 检查 3：默认行为

如果以上都未命中，按 `PERSONA.md` 执行默认开发工作流。

---

## 执行顺序（绝对不可跳过）

```
用户发消息
  ↓
【必须】执行「路由检查」
  ↓
命中 skill？
  ├─ 是 → 读取 SKILL.md → 按 skill 协议执行 → END
  └─ 否 → 按 PERSONA.md 默认逻辑执行 → END
```

**禁止**：
- ❌ 跳过路由检查直接 spawn subagent
- ❌ 同时 spawn subagent 和执行路由检查
- ❌ 命中 skill 后仍凭记忆不按 skill 协议走

---

## 上下文预算

| 层级 | 文件 | 大小 | 加载时机 |
|------|------|------|----------|
| 强制层 | 本 SKILL.md（路由器） | ~5KB | **始终** |
| 强制层 | PERSONA.md | ~5KB | **始终** |
| 强制层 | SKILL_GUIDE.md | ~3KB | **始终** |
| 索引层 | SKILL_INDEX.json | ~58KB | **路由检查 2 时** |
| 按需层 | 命中 skill 的 SKILL.md | 1-35KB | **路由命中后** |

> 启动上下文 ≈ 13KB（不含索引），远低于上下文预算。

---

## 链式推荐

执行完一个 skill 后，查看 `SKILL_INDEX.json` 中的 `relations[skill_id]`：
- 关联度 **>0.8** → 主动询问用户是否继续处理相关任务
- 关联度 **0.5~0.8** → 简要提及相关 skill
- 关联度 **<0.5** → 不主动推荐
