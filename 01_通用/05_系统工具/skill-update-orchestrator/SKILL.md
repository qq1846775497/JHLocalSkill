---
name: skill-update-orchestrator
description: Skill 库批量更新编排器。当用户提到"更新所有 skill"时，通过交互式询问确定更新类型（语言包/项目 File-Skill/新增 Skill），然后执行对应的扫描、对比、更新、索引同步全流程。
tags: [Skill-Update, Meta-Skill, Batch-Update, File-Skill, Vocabulary, Orchestrator]
---

# Skill 库批量更新编排器

## 触发时机

用户消息包含以下任一关键词时触发：
- "更新所有 skill"
- "批量更新 skill"
- "迭代 skill"
- "刷新 skill 库"
- "同步 skill"
- "更新 file-skill"

---

## Phase 1：询问更新类型（必须）

**在调用任何工具之前，必须先询问用户。**

使用 `AskUserQuestion` 弹出以下选项：

A. 更新语言包（vocabulary_live.jsonl + vocabulary_rules.json）
   → 基于近期对话提取新词汇，更新分类规则和语言画像

B. 更新 ProjectLungfish 项目 Skill（File-Skill 批量扫描）
   → 扫描 Main/Source/ProjectLungfish/ 源码变更，更新所有 File-Skill

C. 添加新 Skill
   → 基于项目新模块/系统，创建新的 SKILL.md 并注册到索引

- **用户选 A** → 进入分支 A（语言包更新）
- **用户选 B** → 进入分支 B（项目 Skill 批量更新）
- **用户选 C** → 进入分支 C（添加新 Skill）

---

## 分支 A：语言包更新

**目标**：基于近期对话记录，提取新词汇并更新语言画像系统。

### 执行步骤

1. **读取现有规则**
   - `ReadFile`：`~/.kimi/vocabulary_rules.json`
   - 记录现有 4 类分类器：动作动词、约束词、情绪信号、技术实体

2. **读取对话历史**
   - `ReadFile`：`~/.kimi/vocabulary_live.jsonl`（读取最近 100 条）
   - 如无此文件，跳过并告知用户"暂无语言画像记录"

3. **分析新词汇**
   - 扫描最近对话中出现的技术术语（如新增类名、函数名、项目专有名词）
   - 识别未被 `vocabulary_rules.json` 覆盖的词汇

4. **更新规则文件**
   - 将新识别的词汇补充到对应分类中
   - 使用 `StrReplaceFile` 更新 `vocabulary_rules.json`

5. **输出摘要**
   ```
   📊 语言包更新摘要
   ├── 新增动作动词：X 个
   ├── 新增约束词：X 个
   ├── 新增情绪信号：X 个
   ├── 新增技术实体：X 个
   └── 总计新词汇：X 个
   ```

6. **提醒用户手动提交 Git**
   - 语言包文件位于 `~/.kimi/`，不属于 JHLocalSkill 仓库
   - 如需备份，建议 `cp ~/.kimi/vocabulary_rules.json D:/jiangheng/JHLocalSkill/config/`

---

## 分支 B：项目 Skill 批量更新

**目标**：扫描项目源码变更，批量更新所有 File-Skill，同步 SKILL_INDEX.json。

### 执行步骤

#### Step 1：发现现有 File-Skill

1. `Glob` 扫描：`02_ProjectLungfish专用/09_文件档案管理/00_FileSkills/**/SKILL.md`
2. 排除 `_TEMPLATE/SKILL.md`
3. 为每个 file-skill 记录：
   - `skill_path`：SKILL.md 的绝对路径
   - `skill_dir`：所在目录名（如 `pl-collision-component`）

#### Step 2：逐个检查源码变更

对每个 file-skill 执行：

1. `ReadFile` 读取 SKILL.md（仅读取 frontmatter 和前 30 行）
2. 从 frontmatter 提取 `file_path`（源码绝对路径）
3. 检查源码文件是否存在：
   ```powershell
   Test-Path <file_path>
   ```
4. 如果源码不存在：
   - 标记为 **"源文件已删除"**
   - 询问用户是否归档此 file-skill
5. 如果源码存在：
   - 获取源码 `LastWriteTime`
   - 对比 SKILL.md 的 `LastWriteTime`
   - 如果源码更新：标记为 **"需要更新"**

#### Step 3：生成变更报告

向用户展示报告：

```
📋 File-Skill 扫描报告
├── 总档案数：X
├── 源文件已删除：X（需确认归档）
├── 需要更新：X
│   ├── pl-collision-component → PLCcollisionComponent.cpp（3天前修改）
│   ├── wind-tornado-trap → WindTornadoTrap.as（1周前修改）
│   └── ...
└── 无需更新：X
```

#### Step 4：批量更新（逐个执行，防覆盖协议）

对每个"需要更新"的 file-skill：

1. **询问确认**（除非用户已选择"全部自动更新"）：
   > 是否更新 `{skill_name}`？源文件 `{file_path}` 有变更。
   > - **更新**：重新扫描源码，刷新档案
   > - **跳过**：保留当前档案

2. **执行更新（防覆盖协议）**：
   a. `ReadFile` 读取最新源码（提取 UFUNCTION、主要函数、类声明）
   b. `ReadFile` 读取现有 SKILL.md（**完整内容**，用于确认 frontmatter 不被破坏）
   c. **绝对禁止** `WriteFile` 重写整个 SKILL.md
   d. 只允许使用 `StrReplaceFile` 做以下**局部替换**：

   | 字段 | 操作 | 说明 |
   |------|------|------|
   | `functions` | **追加**新函数 | 不删除旧函数，只追加源码中新发现的函数 |
   | `history` | **顶部追加**新记录 | 在数组开头插入，保持时间倒序 |
   | body"文件概述" | **局部刷新** | 只替换概述段落，不动其他章节 |
   | `id` | **禁止修改** | 档案标识，一经创建永不变 |
   | `file_path` | **禁止修改** | 源码路径，除非文件被移动 |
   | `trigger_words` | **禁止修改** | 用户可能手动添加过自定义触发词 |
   | `constraints` | **禁止修改** | 设计约束是 Plan Mode 阶段的人工产物，不可自动覆盖 |

   e. history 追加格式：
      ```yaml
      - date: "YYYY-MM-DD"
        requirement: "批量更新：同步源码变更"
        changes: "新增函数：{func1}, {func2}"
        functions_affected:
          - "{func1}"
          - "{func2}"
        regression_detected: false
      ```

#### Step 5：发现新源码文件

1. `Glob` 扫描：`D:/jiangheng/JiangHengWork/Main/Source/ProjectLungfish/**/*.cpp`
2. `Glob` 扫描：`D:/jiangheng/JiangHengWork/Main/Source/ProjectLungfish/**/*.h`
3. 对比现有 file-skill 的 `file_path` 列表
4. 列出**无对应 file-skill 的新文件**
5. 询问用户：
   > 发现 X 个新文件暂无 File-Skill 档案，是否创建？
   > - **批量创建**：为所有新文件建立档案
   > - **逐个选择**：列出文件列表，用户勾选
   > - **跳过**：不创建

6. 如用户选择创建，委托 `file-skill-registry` 的创建流程（复制模板、填入元数据）

#### Step 6：同步 SKILL_INDEX.json（防覆盖协议）

**绝对禁止** `WriteFile` 重写整个 SKILL_INDEX.json。必须使用 `StrReplaceFile` 做局部修改。

1. `ReadFile` 读取 `SKILL_INDEX.json`（确认格式和现有内容）
2. **更新现有 skill**（仅 `estimated_tokens`）：
   - 找到目标 skill 的 `"estimated_tokens": <旧值>`
   - 使用 `StrReplaceFile` 替换为新的 token 估算值
   - **禁止**修改 `triggers`、`vector`、`description` 等其他字段
3. **新增 skill**（追加到数组末尾）：
   - 找到 `skills` 数组最后一个元素的 `}`
   - 在其后插入新 skill 的 JSON 对象（带前导逗号）
   - 使用 `StrReplaceFile` 精确插入
4. **更新 relations**（如需）：
   - 找到 `"relations": {` 后的合适位置
   - 使用 `StrReplaceFile` 插入新 skill 的关联条目
5. **更新 routing_table**（如需）：
   - 找到 `"routing_table": {` 内末尾条目之前
   - 使用 `StrReplaceFile` 插入新路由条目

#### Step 7：完成汇报

```
✅ 项目 Skill 批量更新完成
├── 更新档案数：X
├── 新增档案数：X
├── 归档（源文件已删除）：X
├── 跳过未更新：X
├── SKILL_INDEX.json：已同步（局部修改，不覆盖其他 skill）
└── 下一步：git add -A && git commit -m "更新 File-Skill 档案" && git push
```

---

## 分支 C：添加新 Skill

**目标**：基于用户需求创建新的 SKILL.md 并注册到索引。

### 执行步骤

1. **询问新 Skill 信息**
   - 使用 `AskUserQuestion` 询问：
     > 新 Skill 的领域？
     > - 通用（UE 引擎、工具链、项目管理）
     > - ProjectLungfish 专用（资产管线、数据配置、调试）
   - 询问用途描述（一句话）

2. **确定目录位置**
   - 通用 skill → `01_通用/{分类}/`
   - PL 专用 → `02_ProjectLungfish专用/{分类}/`

3. **创建 SKILL.md**
   - 如果是 file-skill → 委托 `file-skill-registry` Phase 1 Step 3B
   - 如果是系统 skill → 基于以下模板创建：
     ```markdown
     ---
     name: <skill-name>
     description: <一句话描述>
     tags: [tag1, tag2]
     ---
     
     # <标题>
     
     ## 触发时机
     
     ## 执行步骤
     
     ## 注意事项
     ```

4. **注册到 SKILL_INDEX.json**
   - 按分支 B Step 6 的方式追加新 skill 元数据（局部插入，不覆盖索引）

5. **汇报**
   ```
   ✅ 新 Skill 已创建
   ├── 路径：{path}
   ├── 名称：{name}
   ├── SKILL_INDEX.json：已注册（局部追加）
   └── 下一步：git add -A && git commit -m "添加新 skill: {name}" && git push
   ```

---

## 安全约束（红规）

| 约束 | 说明 |
|------|------|
| **不自动 Git 提交** | 所有更新完成后仅告知用户提交命令，由用户手动执行 |
| **不覆盖未 checkout 文件** | 更新前检查 `p4 opened` 或 `git status`，如文件未被编辑则自动 `p4 edit` |
| **保留完整历史** | 所有更新以追加 `history` 方式记录，不删除旧记录 |
| **逐个询问确认** | 默认模式下每个 file-skill 更新前询问用户；提供"全部自动更新"快捷选项 |
| **源文件不存在时归档而非删除** | 发现源文件已删除时，询问是否归档 skill，不自动删除 |
| **防覆盖协议** | 禁止 `WriteFile` 重写整个 SKILL.md 或 SKILL_INDEX.json，必须使用 `StrReplaceFile` 局部替换 |
| **frontmatter 只读** | `id`/`name`/`file_path`/`description`/`tags`/`trigger_words`/`constraints` 禁止自动修改 |

---

## 与其他 Skill 的协作

| 场景 | 调用/协作 |
|------|----------|
| 创建单个 file-skill | 委托 `file-skill-registry` Phase 1 Step 3B |
| 更新单个 file-skill 的 history | 遵循 `file-skill-registry` Phase 3 规则 |
| 编译验证（如更新涉及 C++） | 调用 `unreal-build-commands` |
| 代码搜索 | 调用 `codebase-search` 协议（Glob → Grep → ReadFile） |
| 质量检查 | 调用 `code-quality-guardian` 5-Gate 检查 |

---

## 故障排查

| 现象 | 原因 | 解决 |
|------|------|------|
| 扫描不到 file-skill | Glob 路径错误 | 确认 `00_FileSkills` 目录存在 |
| 源码文件权限拒绝 | P4 未 checkout | 自动执行 `p4 edit` |
| SKILL_INDEX.json 格式损坏 | 追加时 JSON 语法错误 | 更新前备份原文件，出错时恢复 |
| 更新后 AI 不加载新 skill | 索引未同步 | 确认 `SKILL_INDEX.json` 已更新且 `git push` |
| **frontmatter 被重置** | AI 使用了 `WriteFile` 而非 `StrReplaceFile` | 立即停止，从 git 恢复旧版本，改用 `StrReplaceFile` 局部替换 |
| **trigger_words 丢失** | 更新时覆盖了 frontmatter | 同上，从 git 恢复，禁止修改 `trigger_words` |
| **constraints 被清空** | AI 误将 constraints 视为可自动更新字段 | 恢复文件，constraints 为 Plan Mode 人工产物，禁止自动覆盖 |
