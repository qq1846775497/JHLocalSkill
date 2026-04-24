# JHLocalSkill 导航协议

> ⚠️ **红规：禁止一次性读取本库内任何 SKILL.md。**
> 必须先读 `SKILL_INDEX.json` 做语义路由，命中后再加载单个 SKILL.md。

## 路由协议（3 步）

```
用户请求 → 读 SKILL_INDEX.json → 计算关联度 → Top-K 命中 → 读对应 SKILL.md
```

### Step 1：读取索引

始终先读取 `SKILL_INDEX.json`（~51KB，被动索引）。它包含：
- `skills[]`：55 个技能的元数据 + 三维向量 + triggers
- `relations{}`：技能间关联度矩阵（用于链式推荐）
- `routing_table{}`：高频场景到技能 ID 的速查表

### Step 2：计算关联度

将用户请求映射为三维向量 `(domain, task_type, artifact)`，与索引中各 skill 的 `vector` 计算加权相似度。

**维度说明：**

| 维度 | 含义 | 典型值 |
|------|------|--------|
| `domain` | 技术领域 | 引擎、构建、资产、蓝图、数据配置、调试、版本控制 … |
| `task_type` | 任务类型 | 查询、修改、创建、调试、修复、迁移、审核、构建 … |
| `artifact` | 操作对象 | .cpp/.h、Blueprint、.xlsx、FlowGraph、.uasset … |

**评分公式：**

```
score = 0.30 × cos_domain
      + 0.30 × cos_task
      + 0.20 × cos_artifact
      + 0.20 × keyword_match(user_text, skill.triggers)
```

- `cos_*` = 余弦相似度（请求向量与 skill 向量）
- `keyword_match` = 用户原文与 skill.triggers 列表的命中比例（0~1）

**快捷路径：** 如果用户请求明显匹配 `routing_table` 中的某个场景（如"编译错误"→`编译/Build/UBT/C++`），可直接取该场景下的技能列表，跳过向量计算。

### Step 3：取 Top-K 并加载

- 取 `score` 最高的 **1~3** 个 skill
- 按 `path` 读取其 `SKILL.md`
- 如果最高分的 skill 与第二名差距 <0.1，向用户列出候选让其确认

---

## 链式推荐

执行完一个 skill 后，查看 `relations[skill_id]`：
- 关联度 **>0.8**：极可能需要连续执行，主动询问用户
- 关联度 **0.5~0.8**：相关但可选，简要提及
- 关联度 **<0.5**：不主动推荐

**示例：**
- 执行完 `unreal-build-commands`（编译）后，`relations` 显示 `unreal-build-fix: 0.92` → 主动问"编译过程中是否遇到错误需要诊断？"
- 执行完 `openspec-propose`（提案）后，`relations` 显示 `openspec-apply-change: 0.85` → 问"是否要开始实现这个提案？"

---

## 上下文预算

| 层级 | 文件 | 大小 | 加载时机 |
|------|------|------|----------|
| 被动层 | `SKILL_INDEX.json` | ~51KB | **始终**（会话开始时） |
| 被动层 | `SKILL_GUIDE.md` | ~2KB | **始终**（会话开始时） |
| 按需层 | `{skill}/SKILL.md` | 1~35KB | **触发后** |
| 按需层 | `{skill}/references/` | 不定 | **JiT**（skill 指令内显式要求时） |
| 按需层 | `{skill}/scripts/` | 不定 | **JiT**（skill 指令内显式要求时） |

> 永远不要一次性加载超过 3 个 SKILL.md。

---

## Lost in the Middle 防护

- 本文件顶部即包含核心规则（红规 + 3 步协议）
- 模型在上下文压缩后仍能抓住关键点：**先读索引，算关联度，再加载**
- `SKILL_INDEX.json` 的 `routing_table` 提供兜底速查，无需完整向量计算即可命中高频场景
