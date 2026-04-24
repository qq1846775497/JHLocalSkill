---
name: file-skill-registry
description: JH-AI-Dev-Workflow 核心元 Skill。五阶段工作流：需求澄清→设计→实现→验证→归档。负责 File-Skill 档案的发现、询问创建、读取、询问更新。Hook 驱动，按需注入。
tags: [File-Skill, Registry, Meta-Skill, Workflow, JH-AI-Dev]
---

# JH-AI-Dev-Workflow（文件档案管理工作流）

## 触发时机

本 Skill 由 Hook 在用户涉及**代码/文件修改**时自动注入。以下场景均会触发：
- 消息中包含文件扩展名（`.cpp` `.h` `.hpp` `.cs` `.as` `.py` `.js` `.ts` `.json` `.toml` `.md` `.build.cs` `.ini` `.uasset`）
- 消息中包含路径特征：`Source\` `Content\` `Plugins\` `Config\` `.cpp` `.h`

---

## 总体原则

1. **尊重用户选择权**：不自动创建 File-Skill，必须询问用户确认
2. **不强制更新**：修改完成后询问用户是否更新档案，用户可拒绝
3. **五阶段工作流**：需求澄清 → 设计 → 实现 → 验证 → 归档
4. **历史约束**：读取已有档案时，必须遵循其中的 constraints 和 history

---

## Phase 1: 需求澄清 + File-Skill 发现/询问

**在调用任何工具之前，必须完成以下步骤：**

### Step 1: 提取目标文件

从用户消息中提取所有涉及的文件路径或文件名。常见形式：
- 绝对路径：`D:\project\Main\Source\...\Foo.cpp`
- 相对路径：`Source/ProjectLungfish/Foo.cpp`
- 仅文件名：`Foo.cpp` `Foo.h`
- 类名/函数名暗示的文件：`APLFoo` → `Foo.cpp`

### Step 2: 查找 File-Skill

使用 `Glob` 搜索 `D:\jiangheng\JHLocalSkill\02_ProjectLungfish专用\09_文件档案管理\00_FileSkills\**\SKILL.md`。

匹配逻辑：
- `file_path` 字段包含目标文件路径
- `trigger_words` 字段包含目标文件名、类名或函数名

### Step 3A: 若找到已有档案

1. `ReadFile` 读取该 File-Skill
2. **向用户展示档案摘要**（用 `TextPart` 或回复文本）：
   - 文件概述
   - 当前函数列表（前 5 个）
   - 最近 3 条修改历史
3. **询问用户**："是否基于此档案继续修改？"
   - 用户确认 → 进入 Phase 2
   - 用户拒绝 → 仍进入 Phase 2，但档案仅作参考，不强制约束

### Step 3B: 若未找到档案（核心变更）

**必须使用 `AskUserQuestion` 询问用户：**

> 文件 `{filename}` 暂无 File-Skill 档案。是否需要创建一个？
>
> **创建**：我会扫描文件结构，提取函数列表，建立初始档案，方便后续迭代追踪。
>
> **跳过**：直接修改代码，不建立档案。

- **用户选"创建"**：
  1. 新建目录：`00_FileSkills/{kebab-case-filename}/`
  2. 复制模板 `_TEMPLATE/SKILL.md`
  3. 使用 `Grep`/`ReadFile` 扫描目标文件，填入：
     - `id`: kebab-case 文件名（不含扩展名）
     - `file_path`: 绝对路径
     - `trigger_words`: [文件名, 类名, 关键函数名]
     - `functions`: 提取所有 `UFUNCTION`、主要函数、类名
     - `constraints`: 留空（后续设计阶段可填入）
     - `history`: 留空数组 `[]`
  4. 使用 `WriteFile` 保存
  5. 告知用户："档案已创建，路径：`{path}`"
  6. 进入 Phase 2

- **用户选"跳过"**：
  1. 告知用户："已跳过档案创建，直接开始修改。"
  2. 进入 Phase 2

---

## Phase 2: 设计（Plan Mode）

### 触发条件（满足任一即进入）

- 用户消息包含："设计" "怎么设计" "架构" "重构" "新建系统" "方案"
- File-Skill 的 history 显示该文件过去有复杂修改记录（涉及 >3 个函数或跨文件改动）
- AI 判断当前需求涉及 >3 个函数的改动或新增

### 规则

1. **强制进入 Plan Mode**（调用 `EnterPlanMode`）
2. 在 Plan 文件中必须引用 File-Skill 的 `history`，避免重复过去的错误
3. 设计完成后，**询问用户**："是否将设计要点写入 File-Skill 的 `constraints` 字段？"
   - 用户确认 → 更新 File-Skill，填入设计约束
   - 用户拒绝 → 跳过
4. 如果用户跳过了 Phase 1 的档案创建，**再次询问**："设计已完成，是否现在创建 File-Skill 来记录这些设计约束？"

---

## Phase 3: 实现

### 规则

1. **读取 File-Skill**（如果存在且用户确认过）
2. 遵循 `constraints` 中的设计约束
3. 避免重复 `history` 中已标记为 `regression_detected: true` 的错误模式
4. **每轮代码修改完成后，询问用户**：
   > "本次改动是否需要记录到 File-Skill 档案？"
   > - **记录**：追加 history
   > - **跳过**：不记录（适合微小改动如变量重命名）
5. **函数签名变更必须更新** `functions` 列表（无论用户是否选择记录 history）

### history 记录格式

```yaml
- date: "YYYY-MM-DD"
  requirement: "用户原始需求的简洁描述"
  changes: "具体改了什么"
  functions_affected: ["函数1", "函数2"]
  regression_detected: false  # 若验证阶段发现回归问题，改为 true
```

---

## Phase 4: 验证（质量门禁）

修改完成后，**必须进行自检**，使用 `SetTodoList` 建立检查清单：

```
□ 编译验证：代码语法正确，能编译通过吗？（如涉及 UE C++，建议调用 UBT）
□ 功能验证：改动是否符合用户需求？
□ 回归检查：是否破坏了 File-Skill history 中记录的其他功能？
□ 网络同步：如涉及 RPC/Replication/Owner 变更，是否正确处理了？
□ 文件清理：是否有临时文件、未使用的引用、调试日志未删除？
□ Skill 合规：是否违反了相关领域 Skill 的规则？（如违反了 native-class-derivation）
```

**若发现 regression**：
1. 立即修复
2. 在 File-Skill 的对应 history 记录中标记 `regression_detected: true`
3. 在回复中告知用户："发现回归问题，已修复并在档案中标记"

---

## Phase 5: 归档

### 规则

1. **询问更新 File-Skill**：
   > "本次修改已完成，是否将改动记录追加到 File-Skill 档案？"
   > - **追加**：更新 history
   > - **跳过**：不更新

2. 用户确认后 → `ReadFile` → `StrReplaceFile` 更新档案

3. **生成本次修改摘要**（无论是否更新档案，都展示给用户）：
   ```
   📋 修改摘要
   ├── 文件：{filename}
   ├── 涉及函数：{func1}, {func2}
   ├── 参考 Skill：{skill1}, {skill2}
   ├── File-Skill：已更新 / 未更新 / 未创建
   └── 质量检查：通过 / 发现问题已修复
   ```

---

## 目录位置

- 元 Skill（本文件）：`D:\jiangheng\JHLocalSkill\02_ProjectLungfish专用\09_文件档案管理\file-skill-registry\SKILL.md`
- 所有 File-Skill：`D:\jiangheng\JHLocalSkill\02_ProjectLungfish专用\09_文件档案管理\00_FileSkills\<kebab-case-name>\SKILL.md`
- 模板：`D:\jiangheng\JHLocalSkill\02_ProjectLungfish专用\09_文件档案管理\00_FileSkills\_TEMPLATE\SKILL.md`

---

## 与其他 Skill 的协作

| 场景 | 协作 Skill |
|------|-----------|
| 需要搜索代码 | `codebase-search` |
| 需要编译验证 | `unreal-build-commands` |
| 需要代码审查 | `code-quality-guardian` |
| 需要设计架构 | `ue-design-research` |
| 涉及 P4 提交 | `p4-workflow` |
| PIE 运行时错误 | `pie-error-fix-notify` |

---

## 故障排查

| 现象 | 原因 | 解决 |
|------|------|------|
| AI 未询问就自动创建档案 | file-skill-registry 规则被忽略 | 检查 AI 是否已读取本 SKILL.md |
| AI 未询问就强制更新档案 | Phase 3 规则被忽略 | 提醒 AI "修改后先询问用户是否更新" |
| File-Skill 历史记录丢失 | 未正确执行 StrReplaceFile | 检查 append 逻辑，确保在数组顶部插入 |
| Hook 未触发 | 输入未匹配代码文件扩展名 | 检查用户消息是否包含 `.cpp`/`.h` 等 |
