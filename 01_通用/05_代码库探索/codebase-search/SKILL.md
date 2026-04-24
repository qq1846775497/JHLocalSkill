---
name: codebase-search
description: >
  高效侦察代码库结构，定位目标文件和符号。使用 Glob → Grep → 选择性 ReadFile
  的三阶段渐进式探索协议，避免逐文件读取造成的上下文膨胀和搜索延迟。
  当用户要求"找一下XX文件"、"搜索XX代码"、"探索代码库"、"了解项目结构"
  或任何需要在未知代码库中定位信息时触发。
trigger_when: >
  用户提到"找文件"、"搜索代码"、"定位"、"探索项目"、"了解结构"、
  "这个项目怎么组织的"、"找一下XX的实现"、"XX在哪里"、"scan codebase"、
  "codebase exploration"、"find where X is defined"。
  也应在任何修改任务开始前主动触发，用于快速了解涉及的代码范围。
---

# 代码库高效侦察

> ⚠️ **核心原则：先侦察，后深入。** 绝不在第一阶段就读取源文件内容。

## 侦察协议（4 阶段）

任何代码库探索任务必须按以下顺序执行。跳过阶段 = 浪费 token。

---

### Phase 1: Glob 扫描 — 建立全局视图

**目标**：用最少 token 获取代码库骨架，不读任何文件内容。

**操作**：
1. 用 `Glob` 扫描关键目录模式：
   - C++ 项目：`Source/**/*.h`, `Source/**/*.cpp`, `Source/**/*.build.cs`
   - UE 项目：`*.uproject`, `Config/*.ini`, `Content/**/*.uasset`
   - Python 项目：`**/*.py`, `requirements.txt`, `pyproject.toml`
   - 通用：`README*`, `AGENTS.md`, `CLAUDE.md`, `.gitignore`
2. 用 `Shell` 的 `findstr` / `where` / `dir` 快速定位配置文件
3. **绝不**在此阶段 `ReadFile` 任何源代码

**输出**：目录树摘要（最多 50 个关键路径），标注：
- 入口点（main / GameMode / 启动模块）
- 配置文件位置
- 测试目录
- 第三方依赖目录

**时间预算**：< 10 秒

---

### Phase 2: Grep 定向 — 精准定位候选

**目标**：用 Grep 替代 ReadFile 做全文搜索，只拿文件列表。

**操作**：
1. 基于 Phase 1 的目录结构，用 `Grep` 搜索目标符号/关键词
2. **优先**使用 `output_mode: files_with_matches` — 只返回文件路径，不返回内容
3. 如需上下文，使用 `output_mode: content` 但严格限制：
   - `-n` 显示行号
   - `-C 2` 最多前后 2 行
   - `head_limit: 20` 最多 20 条结果
4. 如需精确定位某文件的特定区域，用 `Grep` 拿到行号后，再用 `ReadFile` 读该区域

**输出**：候选文件列表（Top 10），附关键词出现次数。

**禁止**：
- ❌ 用 `ReadFile` 做全文搜索（Grep 快 10 倍且省 token）
- ❌ `output_mode: content` 时不限制 `-C` 和 `head_limit`

**时间预算**：< 15 秒

---

### Phase 3: 并行 ReadFile — 选择性深入

**目标**：只读确认相关的文件段落，不读完整文件。

**操作**：
1. 从 Phase 2 的候选列表中，选择最相关的 **≤5 个文件**
2. 并行 `ReadFile`，使用 `line_offset` + `n_lines` 只读关键区域
3. 读取范围规则：
   - 类/结构体定义：从声明行 ±30 行
   - 函数实现：从函数签名 ±50 行
   - 配置文件：只读相关 section
4. 读完后如需在文件内二次定位，再次用 `Grep`（而非读更多内容）

**输出**：确认的目标文件 + 具体行号范围 + 关键代码片段。

**禁止**：
- ❌ 一次性读取超过 5 个文件
- ❌ 不指定 `line_offset` 就读大文件（>500 行）
- ❌ 读取与任务无关的文件

**时间预算**：< 20 秒

---

### Phase 4: 结构化输出 — 生成探索报告

**目标**：将侦察结果保存为可复用的结构化文档。

**操作**：
1. 生成探索报告，包含：
   - 任务目标
   - 关键文件路径列表（附行号范围）
   - 关键类/函数/变量清单
   - 依赖关系图（文本形式）
2. 保存到 `.research/{task_name}_{YYYYMMDD}.md`
3. 向用户简要汇报发现（3-5 句话）

**输出格式**：
```markdown
# Recon: [任务名]

## 关键文件
| 文件 | 相关行号 | 说明 |
|------|----------|------|
| `Source/Gameplay/PLCharacter.cpp` | 120-180 | 移动逻辑实现 |

## 依赖关系
- `PLCharacter` → `PLMovementComponent` → `PLAbilitySystem`
```

---

## 并行探索模式（复杂任务）

当任务涉及多个独立搜索目标时，启动并行子代理：

| 代理角色 | 职责 | 成本 |
|----------|------|------|
| `locator` | 快速定位文件和符号（Phase 1-2）| 低 |
| `analyzer` | 深入分析代码逻辑（Phase 3-4）| 高 |
| `pattern-finder` | 寻找代码模式和重复结构 | 中 |

**约束**：
- 每个子代理只负责一个独立目标
- 子代理不读取彼此已探索的文件
- 主代理汇总结果，去重并生成统一报告

---

## 常见代码库模式的快速侦察命令

### UE C++ 项目
```powershell
# 模块结构
Glob: Source/*/*.Build.cs

# 查找某个类的所有引用
Grep: "class APLMyClass" | "APLMyClass::" | "->APLMyClass"

# 查找 UFUNCTION
Grep: "UFUNCTION.*BlueprintCallable" + "MyFunctionName"
```

### Blueprint / 资产
```powershell
# 列出所有 Blueprint
Glob: Content/**/*.uasset

# 查找引用某个 Blueprint 的地方
Grep: "/Game/Path/BP_MyAsset" --glob="*.cpp" --glob="*.h"
```

### 配置文件 / 数据表
```powershell
# 查找某个 Config ID
Grep: "MyConfigID" --glob="*.json" --glob="*.csv" --glob="*.xlsx"
```

---

## 红规（违反 = 效率崩溃）

1. **❌ 禁止无侦察直接 ReadFile**：任何文件读取前，必须先经过 Glob 或 Grep 确认相关性
2. **❌ 禁止 ReadFile 做全文搜索**：Grep 是搜索工具，ReadFile 是阅读工具
3. **❌ 禁止并行读取超过 5 个文件**：上下文会爆炸，且多数内容无关
4. **❌ 禁止读取无关文件**：如果 Glob/Grep 显示某文件与任务无关，绝不读取
5. **❌ 禁止重复侦察**：如果 `.research/` 中已有同主题报告，先读取报告而非重新探索

---

## 何时使用本 Skill

| 场景 | 操作 |
|------|------|
| "找一下 XX 的实现" | 触发本 skill → Phase 2 Grep 定位 → Phase 3 读取 |
| "这个项目怎么组织的" | 触发本 skill → Phase 1 Glob 扫描 → 输出结构摘要 |
| "修改前先看看涉及哪些文件" | 触发本 skill → 完整 4 阶段 → 保存 `.research/` |
| 修改过程中发现新依赖 | 快速 Phase 2-3，定位新文件 |

## 参考
- 详细侦察模式：`references/reconnaissance-patterns.md`
