---
name: ue-dev-orchestrator
description: >
  UE 开发自动化编排器（Meta-Skill）。当用户要求修改任何 UE C++/Blueprint/配置/资产时，
  自动接管并驱动完整开发闭环：侦察 → P4 Checkout → 规范确认 → 修改 → 审查 → 编译 → 测试 → 提交。
  内置 Capability Registry，硬编码任务类型到 Skill 调用链的映射，不依赖模型二次推理。
trigger_when: >
  用户说"改一下"、"添加"、"修复"、"删除"、"实现"、"修改"、"优化"任何 UE 相关的内容，
  包括 C++ 代码、Blueprint、配置文件、Excel 配表、资产、FlowGraph、材质、动画等。
  触发信号：".cpp"、".h"、"Blueprint"、".uasset"、"Excel"、"DataTable"、
  "词条"、"实体"、"Asset"、"FlowGraph"、"bug"、"fix"、"crash"、"error"。
  本 skill 的触发优先级高于所有其他具体实现 skill。
---

# UE 开发自动化编排器

> **核心原则：状态机驱动，不靠提示词。** 本 skill 内置 Capability Registry，任务类型一旦确定，调用链即锁定，模型不重新推理该调用谁。

---

## Capability Registry（能力注册表）

Orchestrator 不依赖 SKILL_INDEX.json 做运行时路由。以下映射直接内置于本 skill，永不遗忘：

| 任务类型 | 触发信号 | 自动调用的 Skill 链 |
|----------|----------|-------------------|
| **C++ 修改** | `.cpp`、`.h`、`.build.cs`、`C++`、`class`、`function` | `codebase-search` → `p4-workflow` → `ue-software-architecture` → `unreal-cpp-workflow` → `code-quality-guardian` → `unreal-build-commands` → `p4-workflow` |
| **Blueprint 修改** | `Blueprint`、`.uasset`、`蓝图`、`节点` | `codebase-search` → `p4-workflow` → `ue-cli-blueprint` → `code-quality-guardian` → `ue-cli-runtime` → `p4-workflow` |
| **配置/数据修改** | `Excel`、`.xlsx`、`DataTable`、`词条`、`实体` | `codebase-search` → `p4-workflow` → `excel-query`/`entity-tag-modifier` → `precheckin` → `p4-workflow` |
| **资产修改** | `Asset`、`FlowGraph`、`材质` | `codebase-search` → `p4-workflow` → `flowgraph-edit`/`damage-flow-graph-authoring` → `code-quality-guardian` → `ue-cli-runtime` → `p4-workflow` |
| **调试修复** | `bug`、`fix`、`crash`、`error`、`报错` | `codebase-search` → `core-redirects-debug`/`pie-error-fix-notify`/`unreal-build-fix` → `p4-workflow` → 修复 → `code-quality-guardian` → `p4-workflow` |

### 自动触发规则

1. **识别任务类型**：从用户请求中提取关键词，匹配上表第一列
2. **锁定 Skill 链**：直接按表的顺序调用对应 skill，不经过模型二次推理
3. **执行闭环**：按预设顺序执行，每一步成功才进入下一步
4. **失败回退**：某一步失败时，调用对应的修复 skill，修复后重试（最多 3 轮）

---

## 通用工作流结构（所有任务类型共享）

```
用户请求
  │
  ▼
[Step 1: 侦察] codebase-search → 定位文件、理解上下文
  │   └── 确认点：向用户展示找到的文件列表
  ▼
[Step 2: P4 Checkout] p4-workflow → checkout 所有相关文件
  │   └── 检查：文件是否已是 writable，避免重复 checkout
  ▼
[Step 3: 规范/上下文加载] 按任务类型加载对应规范 skill
  │   └── C++ → ue-software-architecture；Blueprint → ue-software-architecture；配置 → entity-tag-modifier
  ▼
[Step 4: 修改执行] 按任务类型调用实现 skill
  │   └── 确认点：向用户展示修改方案（diff 预览或文字描述）
  ▼
[Step 5: 代码审查] code-quality-guardian → 5-Gate 检查
  │   └── 自动执行，不阻塞（发现问题记录，继续下一步）
  ▼
[Step 6: 编译验证] unreal-build-commands / ue-cli-blueprint / precheckin
  │   └── 失败? → 对应修复 skill → 修复 → 回到 Step 6（重试计数 +1）
  ▼
[Step 7: 运行时验证] ue-cli-runtime / soft-ue-bridge → PIE 验证
  │   └── 失败? → pie-error-fix-notify → 修复 → 回到 Step 7（重试计数 +1）
  ▼
[Step 8: 回归检查] code-quality-guardian Gate 3 → 检查调用方/API 兼容性
  ▼
[Step 9: P4 提交] p4-workflow + pr → 生成 CL 描述并提交
  │   └── 确认点：向用户展示 CL 描述和文件列表
  ▼
✅ 完成 — 向用户汇报完整修改摘要
```

---

## 用户确认点（不可跳过）

以下节点**必须**暂停并征求用户确认。用明确的 `[CONFIRM]` 标记：

| 步骤 | 确认内容 | 超时行为 |
|------|----------|----------|
| Step 1 后 | "找到以下文件，是否正确？" | 默认继续（记录"用户未确认"）|
| Step 4 前 | "修改方案：XXX，是否执行？" | 等待用户，不自动继续 |
| Step 6 编译失败时 | "编译错误：XXX，建议修复方案：XXX，是否按建议修复？" | 等待用户 |
| Step 9 前 | "CL 描述：XXX，提交文件：XXX，是否提交？" | 等待用户 |

**确认格式**：
```
[CONFIRM] Step {N}: {描述}
选项：
[A] 同意 / 继续
[B] 修改方案（请说明）
[C] 跳过此步骤
[D] 中止整个工作流
```

---

## 状态追踪（Parking States）

使用 `.workflow/{task_id}_state.json` 持久化进度，支持会话中断后恢复。

### 状态文件结构

```json
{
  "task_id": "auto-generated-from-timestamp",
  "workflow_type": "cpp|blueprint|config|asset|debug",
  "current_step": 4,
  "status": "modifying",
  "completed_steps": [1, 2, 3],
  "pending_steps": [4, 5, 6, 7, 8, 9],
  "checked_out_files": ["Source/.../PLCharacter.cpp"],
  "retry_counts": {"compile": 0, "pie": 0},
  "user_confirmations": {
    "step1": "approved",
    "step4": "pending"
  },
  "blockers": [],
  "modifications_summary": "准备添加 Sprint Ability..."
}
```

### 状态机定义

| 状态 | 含义 | 可转移状态 |
|------|------|-----------|
| `idle` | 刚识别任务，未开始 | `reconnaissance` |
| `reconnaissance` | Step 1 侦察中 | `checkout` / `blocked` |
| `checkout` | Step 2 P4 checkout | `loading_context` / `blocked` |
| `loading_context` | Step 3 加载规范 | `modifying` / `blocked` |
| `modifying` | Step 4 修改中 | `reviewing` / `blocked` |
| `reviewing` | Step 5 审查中 | `compiling` / `blocked` |
| `compiling` | Step 6 编译中 | `testing` / `fixing_compile` / `blocked` |
| `fixing_compile` | 编译失败修复中 | `compiling`（重试）/ `blocked` |
| `testing` | Step 7 PIE 验证中 | `regression_check` / `fixing_pie` / `blocked` |
| `fixing_pie` | PIE 报错修复中 | `testing`（重试）/ `blocked` |
| `regression_check` | Step 8 回归检查 | `submitting` / `blocked` |
| `submitting` | Step 9 P4 提交 | `completed` / `blocked` |
| `completed` | 全部完成 | — |
| `blocked` | 阻塞（需用户干预）| 任意状态（用户解除后）|

### 会话恢复协议

每次会话开始时：
1. 检查 `.workflow/` 目录下是否有未完成的 state 文件
2. 如有，读取并询问用户："检测到未完成任务：XXX，当前在 Step N（状态：XXX），是否继续？"
3. 用户确认后，从 `current_step` 继续执行
4. 用户拒绝后，将 state 文件归档到 `.workflow/archive/`

---

## Hard Gates（硬性阻塞门）

以下情况必须阻塞进度，不能自动跳过：

| Gate | 条件 | 行为 |
|------|------|------|
| **编译失败 Gate** | Step 6 编译失败且重试 ≥3 次 | 状态设为 `blocked`，向用户汇报详细错误和已尝试的修复 |
| **PIE 崩溃 Gate** | Step 7 PIE 崩溃且重试 ≥3 次 | 状态设为 `blocked`，汇报调用栈和可能原因 |
| **P4 冲突 Gate** | Step 2 checkout 时文件已被他人 checkout | 状态设为 `blocked`，询问是否等待或切换 changelist |
| **API 破坏 Gate** | Step 8 发现公开 API 签名变更且未处理调用方 | 状态设为 `blocked`，要求用户确认是否进行破坏性变更 |
| **用户中止 Gate** | 用户在任意确认点选择 [D] 中止 | 立即保存 state 为 `blocked`，清理已 checkout 的文件（询问用户）|

---

## 重试与回退策略

```
Step 6 编译失败:
  重试 1: 调用 unreal-build-fix → 自动修复常见错误 → 重新编译
  重试 2: 读取更详细的错误日志 → 尝试更深入的修复 → 重新编译
  重试 3: 向用户展示错误 + 建议 → 等待用户决策
  重试 ≥3: Hard Gate 触发，状态 blocked

Step 7 PIE 失败:
  重试 1: 调用 pie-error-fix-notify → 自动修复 → 重新 PIE
  重试 2: 调用 ue-cli-runtime 读取更详细日志 → 定位 → 修复 → 重新 PIE
  重试 3: 向用户展示错误 → 等待用户决策
  重试 ≥3: Hard Gate 触发
```

---

## 与现有 Skill 的协作关系

```
ue-dev-orchestrator（本 skill = 总指挥）
    ├───► codebase-search        [Step 1]  侦察
    ├───► p4-workflow            [Step 2,9] Checkout / 提交
    ├───► pr                     [Step 9]  CL 描述
    │
    ├───► ue-software-architecture [Step 3] C++/BP 规范确认
    ├───► unreal-cpp-workflow    [Step 4] C++ 修改
    ├───► ue-cli-blueprint       [Step 4,6] BP 修改/编译
    ├───► excel-query            [Step 1] 配置定位
    ├───► entity-tag-modifier    [Step 3,4] 实体/词条修改
    ├───► flowgraph-edit         [Step 4] FlowGraph 修改
    ├───► damage-flow-graph-authoring [Step 4] 伤害节点编辑
    │
    ├───► code-quality-guardian  [Step 5,8] 审查 + 回归检查
    ├───► unreal-build-commands  [Step 6] 编译
    ├───► unreal-build-fix       [Step 6 失败] 编译修复
    ├───► precheckin             [Step 6] 配置导出验证
    ├───► ue-cli-automation      [Step 7 可选] 自动化测试
    ├───► ue-cli-runtime         [Step 7] PIE / 运行时日志
    ├───► soft-ue-bridge         [Step 4,7] 编辑器操作
    ├───► pie-error-fix-notify   [Step 7 失败] PIE 修复
    │
    └───► core-redirects-debug   [Step 2 调试] 重定向修复
```

---

## 输出规范

每个 Step 完成后，向用户输出一行进度：

```
[Orchestrator] Step 1/9 ✅ 侦察完成 — 找到 3 个相关文件
[Orchestrator] Step 2/9 ✅ P4 Checkout 完成 — 2 个文件已迁出
[Orchestrator] Step 3/9 ✅ 规范确认 — 使用 PL 命名约定 + GAS 标签层级
[Orchestrator] Step 4/9 ⏳ 修改执行 — [CONFIRM] 方案：添加 Sprint Ability，请确认
[Orchestrator] Step 5/9 ✅ 代码审查 — Gate 1-5 通过，0 个警告
[Orchestrator] Step 6/9 ✅ 编译验证 — Development Editor 编译通过（12.3s）
[Orchestrator] Step 7/9 ✅ PIE 验证 — 冲刺功能正常，无报错
[Orchestrator] Step 8/9 ✅ 回归检查 — 无 API 破坏，调用方无影响
[Orchestrator] Step 9/9 ⏳ P4 提交 — [CONFIRM] CL#123456 "Add Sprint Ability to PLCharacter"
[Orchestrator] ✅ 全部完成 — 修改摘要：...
```

---

## 参考文件

- `references/workflow-state-schema.md` — 状态文件 JSON Schema
- `references/workflow-templates.md` — 5 种工作流的打印版步骤清单
