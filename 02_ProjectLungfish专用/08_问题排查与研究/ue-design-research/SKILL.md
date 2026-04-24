---
name: ue-design-research
description: >
  UE 架构设计先行研究 skill。任何重构、新建系统、重大修改前，
  强制先搜索外部架构思路 → 吸收最佳实践 → 对齐项目内部代码风格 →
  输出简要设计文档 → 确认后再动工。禁止直接凭训练记忆上手改代码。
trigger_when: >
  用户说"重构"、"重写"、"新建"、"做一个"、"实现一个"、"设计一个"、
  "优化一下"、"把这个改成"、"添加系统"、"写一个新的"、"怎么设计"、
  "架构上怎么搞"、"参考一下别人怎么做的"。
  任何涉及新建 C++ 类、新增模块、重写现有系统的对话。
---

# UE 设计先行研究（Design-First Workflow）

> ⚠️ 红规：用户说完需求后，**必须先完成 Step 1→2→3，才能进入 Step 4 动工**。
> 未完成"外部吸收 + 内部对齐"前，禁止生成/修改任何 `.cpp`/`.h`/`.uasset` 文件。

---

## 5 步强制工作流

### Step 1: 需求澄清（30 秒内完成）

用户提出重构/新建需求后，**不碰任何文件**，先明确以下 4 点：

| 问题 | 说明 |
|------|------|
| **目标** | 解决什么问题？当前痛点是什么？ |
| **约束** | 性能要求？网络同步需求？Blueprint 兼容？ |
| **范围** | 影响哪些现有模块？需要改哪些文件？ |
| **参考** | 用户心中有没有参考实现（某游戏/某开源项目）？ |

如果用户表述模糊，用 **1 句话** 追问，不要写长段落。

---

### Step 2: 外部架构吸收（强制，不可跳过）

根据需求类型，用 `SearchWeb` 并行发 **2-4 个查询**（不是串行）：

| 场景 | 搜索 Query 模板 |
|------|----------------|
| GAS/Gameplay 相关 | `"UE5 GAS {topic} architecture"` / `"UE5 Gameplay Ability System {topic} best practice"` |
| AI/BehaviorTree | `"UE5 AI Perception design pattern"` / `"UE5 StateTree vs Behavior Tree"` |
| 网络同步 | `"UE5 network replication optimization"` / `"UE5 Multicast RPC pattern"` |
| 装备/物品系统 | `"Diablo-like item affix system design"` / `"UE5 inventory system architecture"` |
| 伤害计算 | `"UE5 damage calculation pipeline"` / `"GAS gameplay effect execution flow"` |
| UI/Slate | `"UE5 Slate architecture"` / `"UMG widget blueprint communication"` |
| 性能优化 | `"UE5 performance profiling best practice"` / `"UE5 object pooling pattern"` |
| 第三方集成 | `"{plugin_name} UE5 integration guide"` / `"UE5 {system} plugin architecture"` |
| 通用设计模式 | `"UE5 {pattern} implementation"` / `"Unreal Engine {topic} design pattern"` |

**读取至少 2 篇关键文章**（`FetchURL`），提取：
- 核心设计模式 / 架构决策
- 关键 API 选择理由
- 常见坑和 trade-offs
- 版本兼容性注意（UE 5.3 vs 5.4 行为差异？）

> 💡 优先读取：官方文档、UDN、官方论坛高质量帖、知名技术博客（
> 如 benui.ca, unrealinsider.com, tomlooman.com, medium 高赞文）。
> 避免：过时版本（UE4 为主）、低质量复制粘贴内容。

---

### Step 3: 内部 Codebase 对齐（强制，不可跳过）

加载 `codebase-search` skill，搜索项目内：

1. **同类系统现有实现**——项目里有没有类似功能？怎么实现的？
2. **命名约定**——对照 `ue-software-architecture` 规范
3. **模块边界**——改动会跨越哪些模块？是否违反现有架构？
4. **已有接口**——有没有可以复用的基类/接口？避免重复造轮子

**输出：简要设计文档（≤20 行，必须包含）**

```
## 设计概要：{功能名}

### 外部方案核心思路（来源）
- {来源1 URL}: {核心思路，1 句话}
- {来源2 URL}: {关键 API/模式，1 句话}

### 项目内适配点
- 与现有 {XXXSystem} 的集成方式
- 复用 {XXXBaseClass} / 新建接口
- 命名：{类名} 遵循 APL/UPL/SPL 前缀规范

### 接口设计
- 头文件草图（关键 UFUNCTION / 关键属性，不需要完整代码）

### 风险评估
- {高风险点}: {缓解方案}
```

---

### Step 4: 确认（用户点头 or 自动决策）

**展示设计文档给用户**，等待确认。

- 用户说"OK"/"就这样"/"搞" → 进入 Step 5
- 用户提出修改 → 回到 Step 3 调整
- 用户说"先不搞了" → 停止，不生成任何文件

> ⚠️ 红规：如果设计文档中**风险评估包含"高风险"或"可能破坏现有 XXX"**，
> **必须**等待用户确认，不可自动推进。

---

### Step 5: 动工执行

确认后，进入标准开发闭环：

```
P4 checkout → 写代码 → UBT 编译 → 测试 → P4 reconcile
```

由 `ue-dev-orchestrator` / `unreal-cpp-workflow` / `unreal-build-commands` 接管执行。
本 skill 的职责到此结束。

---

## 红规（违反 = 严重错误）

- ❌ **用户说完需求后 30 秒内就生成/修改任何源文件**
- ❌ **不搜外部资料直接凭训练记忆设计**
- ❌ **不检查项目内现有同类实现就新建模块**
- ❌ **不输出设计文档直接写代码**
- ❌ **高风险方案不经用户确认就实施**
- ✅ **必须**：外部方案注明来源 URL
- ✅ **必须**：内部对齐后说明"与现有 XXX 的集成点"
- ✅ **必须**：设计文档 ≤20 行，拒绝写长篇大论

---

## 关联 Skill（本 skill 会按需加载）

| Skill | 加载时机 |
|-------|----------|
| `codebase-search` | Step 3 内部对齐阶段 |
| `ue-software-architecture` | Step 3 检查命名约定/模块边界 |
| `ue-dev-orchestrator` | Step 5 动工执行阶段 |
| `unreal-build-commands` | Step 5 编译验证 |
| `p4-workflow` | Step 5 修改前 checkout |
| `unreal-build-fix` | Step 5 编译失败时 |
