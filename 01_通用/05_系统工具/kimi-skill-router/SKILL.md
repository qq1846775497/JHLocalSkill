# Kimi Skill Router Hook — 模块化配置指南

> 本 skill 描述 Kimi CLI Hook 注入系统的完整架构。任何对 hook 的修改、扩展、调试，必须先阅读本 skill。

## 系统概述

Skill Router Hook 是一个安装在 `~/.kimi/skill-router/kimi_skill_router.py` 的 Python 脚本，由 Kimi CLI 的 `UserPromptSubmit` hook 触发。每次用户提交消息时，hook 执行四层（可扩展）匹配，输出 JSON 供 Kimi CLI 注入 AI 上下文。

```
用户输入 → Hook 触发 → Step 1~N 匹配 → 格式化输出 → AI 上下文注入
```

**核心文件位置：**

| 文件 | 路径 | 作用 |
|------|------|------|
| 主程序 | `~/.kimi/skill-router/kimi_skill_router.py` | Hook 入口，模块化匹配管线 |
| Skill 索引 | `~/.kimi/skill-router/skill_index_cache.json` | 所有 skill 的 id/description/path |
| 触发词表 | `~/.kimi/skill-router/skill_triggers_enhanced.json` | 每个 skill 的触发词列表 |
| LLM Prompt | `~/.kimi/skill-router/router_prompt.txt` | SiliconFlow 语义匹配用的 prompt 模板 |
| API Key | `~/.kimi/skill-router/.env` | `SILICONFLOW_API_KEY` |
| 词汇规则 | `~/.kimi/skill-router/vocabulary_rules.json` | Step 5 用户语言画像的分类规则 |
| 词汇记录 | `~/.kimi/vocabulary_live.jsonl` | 增量记录的用户语言数据 |
| 调试日志 | `~/.kimi/skill-router/hook_debug.log` | Hook 调用日志 |

---

## 模块化管线（Step-by-Step）

### Step 0: 输入接收

**函数**: `main()` 入口  
**输入**: `stdin` JSON `{"prompt": "用户原始输入"}`  
**输出**: 无直接输出，驱动后续 Steps  

**行为**：
1. 从 `stdin` 读取 JSON
2. 提取 `prompt` 字段
3. 写一行 debug log 到 `hook_debug.log`
4. 如果 `prompt` 为空，直接返回

---

### Step 1: 硬编码规则匹配 `_match_hardcoded`

**类型**: 本地规则，零延迟  
**配置位置**: `kimi_skill_router.py` 中的 `HARDCODED_RULES` 常量 + `CODE_FILE_EXTS`  
**修改方式**: 直接修改 `.py` 文件中的常量  

**匹配逻辑**：
```python
for triggers, skill_id in HARDCODED_RULES:
    for trigger in triggers:
        if trigger in user_msg.lower():
            return (skill_id, 1.0, f"硬编码: '{trigger}'")
```

**特殊规则：代码文件自动检测**
- 如果用户消息包含代码文件扩展名（`.cpp`、`.h`、`.py` 等）或路径分隔符（`/`、`\`）
- 自动匹配 `file-skill-registry`
- 额外追加 C++ 相关 skill（`ue-software-architecture`、`unreal-cpp-workflow`、`native-class-derivation`）

**何时添加新的硬编码规则**：
- 某个 skill 有极其明确的中文关键词（如 "P4"、"编译"、"蓝图转C++"）
- 希望该匹配**零延迟**、**不依赖外部文件**
- 规则稳定，不经常变动

**添加示例**：
```python
HARDCODED_RULES = [
    # ... 已有规则 ...
    (["新关键词1", "新关键词2"], "新skill-id"),
]
```

---

### Step 2: 触发词匹配 `_match_triggers`

**类型**: 本地规则，零延迟  
**配置位置**: `~/.kimi/skill-router/skill_triggers_enhanced.json`  
**修改方式**: 直接编辑 JSON 文件  

**文件格式**：
```json
{
  "skill-id-1": ["触发词1", "触发词2", "触发词3"],
  "skill-id-2": ["关键词A", "关键词B"]
}
```

**匹配逻辑**：
1. 精确子串匹配：如果触发词完整出现在用户消息中 → 置信度 0.95
2. 分词交集匹配：将触发词和用户消息都分词，计算交集比例 → 置信度 0.50~0.75
3. 通用触发词（如 "修改"、"添加"、"修复"）命中时降分至 0.55，避免误匹配

**何时编辑此文件**：
- 为现有 skill 补充更多触发词
- 新 skill 上线时，批量导入其触发词
- 发现某个 skill 该命中但没命中时

**更新命令**：
```powershell
# 手动编辑
notepad $env:USERPROFILE\.kimi\skill-router\skill_triggers_enhanced.json

# 或通过脚本批量生成（如果有 skill 元数据）
python generate_triggers.py
```

---

### Step 3: 描述匹配 `_match_description`

**类型**: 本地规则，零延迟  
**配置位置**: `~/.kimi/skill-router/skill_index_cache.json` 中的 `description` 字段  
**修改方式**: 修改对应 skill 的 `SKILL.md` 中的 Description 段落  

**匹配逻辑**：
1. 从用户消息中提取 ≥3 字的实词（过滤 "这个"、"怎么" 等停用词）
2. 与每个 skill 的 description 字段做分词交集
3. 交集词数 ≥3 → 置信度 0.70；交集 = 2 → 0.60；交集 = 1 → 0.50

**何时会触发**：
- 用户没有使用明确的关键词，但描述的内容与某个 skill 的 description 语义相近
- 例如用户说 "帮我看看这段代码质量" → 匹配 `code-quality-guardian`（description 含 "代码质量"）

**优化方法**：
- 如果某个 skill 经常被描述匹配但不该命中，精简其 description
- 如果某个 skill 该命中但没命中，在 description 中补充更多关键词

---

### Step 4: LLM 语义匹配 `_match_llm`

**类型**: 远程 API，有延迟（15s 超时）  
**配置位置**: 
- `~/.kimi/skill-router/.env` → `SILICONFLOW_API_KEY`
- `~/.kimi/skill-router/router_prompt.txt` → Prompt 模板

**触发条件**（满足任一即触发）：
1. Step 1~3 完全未命中任何 skill
2. Step 1~3 的最高置信度 < `LLM_CONFIDENCE_THRESHOLD`（默认 0.70）

**工作原理**：
1. 将全部 skill 列表（id + description）拼成文本
2. 插入到 `router_prompt.txt` 模板中
3. 调用 SiliconFlow API（`Pro/MiniMaxAI/MiniMax-M2.5`）
4. 模型返回应匹配的 skill id 列表
5. 过滤无效的 id，返回置信度 0.85

**何时调整配置**：
- API 经常超时 → 降低 `LLM_TIMEOUT` 或换模型
- LLM 经常返回无效 id → 优化 `router_prompt.txt` 的格式说明
- 不想用 LLM → 将 `LLM_CONFIDENCE_THRESHOLD` 设为 0.0（永远不触发）

**Prompt 模板变量**：
```text
{skill_list}    # 自动插入的全部 skill 列表
{user_prompt}   # 用户的原始输入
```

---

### Step 5: 词汇实时记录 `_update_vocabulary`

**类型**: 本地规则，零延迟，副作用（写文件）  
**配置位置**: `~/.kimi/skill-router/vocabulary_rules.json`  
**输出位置**: `~/.kimi/vocabulary_live.jsonl`  

**目的**：持续构建用户的语言画像，记录其独特的表达方式、缩写、习惯用语。

**处理流程**：
1. 加载 `vocabulary_rules.json`（4 类规则：动作动词、约束词、情绪信号、技术实体）
2. 提取用户消息中的关键短语（规则匹配 + 路径提取 + 英文术语 + 中文短语）
3. 与已有记录去重（按 token 小写）
4. 追加到 `vocabulary_live.jsonl`

**记录格式**：
```json
{
  "timestamp": "2026-04-23T14:58:42",
  "session_marker": "9c447384",
  "token": "迁出",
  "raw": "迁出了 你再试试呢",
  "category": "action_verb",
  "confidence": 0.9,
  "verified": false,
  "misunderstood": false,
  "frequency": 1
}
```

**何时编辑 `vocabulary_rules.json`**：
- 发现用户使用了新的习惯用语，但未被记录
- 某个词被错误分类（如 "直接" 被分到 emotion，实际应为 constraint）
- 需要新增分类（如新增 "project_specific" 类记录项目内部术语）

**定期归纳**：
- 当 `vocabulary_live.jsonl` 积累 ~20 条 `verified: false` 记录时
- AI 读取 jsonl → 验证分类 → 合并到 `~/.kimi/vocabulary_profile_full.md`
- 标记 `verified: true`

---

### Step 6+: 扩展接口（预留）

**如何添加新的 Step**：

在 `kimi_skill_router.py` 中，遵循以下规范：

```python
def _match_new_layer(user_msg: str) -> list:
    """
    新匹配层模板。
    
    Args:
        user_msg: 用户的原始输入字符串
        
    Returns:
        list of tuples: [(skill_id, confidence, reason), ...]
        - skill_id: str, skill 的 id
        - confidence: float, 0.0~1.0
        - reason: str, 匹配原因（用于日志和调试）
        
        如果没有匹配，返回空列表 []
    """
    results = []
    # ... 匹配逻辑 ...
    return results
```

然后在 `main()` 的 `_merge()` 调用链中加入：

```python
local_results = _merge(
    _match_hardcoded(user_msg),
    _match_triggers(enhanced, user_msg),
    _match_description(skills, user_msg),
    _match_new_layer(user_msg),  # ← 新增
)
```

**扩展建议**（未来可实现的 Step）：

| Step | 名称 | 思路 |
|------|------|------|
| 6 | 历史上下文匹配 | 根据当前会话的历史消息判断用户意图 |
| 7 | 文件变更感知 | 检测用户最近修改的文件类型，推荐相关 skill |
| 8 | 时间模式匹配 | 根据当前时间判断（如深夜调试 → 推荐 bug 排查 skill）|
| 9 | 情绪状态响应 | 根据 Step 5 的情绪信号调整推荐策略 |

---

## 结果合并与输出

### `_merge()` 合并策略

所有 Step 的结果按 skill_id 合并：
- **多 Step 命中同一 skill**：取最高置信度 × 1.1 加成（多层确认）
- **不同 Step 命中不同 skill**：各自保留
- **排序**：按置信度降序
- **截断**：保留前 `MAX_SKILLS` 个（默认 5）

### `_format()` 输出格式

最终输出为 JSON：

```json
{
  "hookSpecificOutput": {
    "inject_prompt": "⚠️ Skill Router 提醒\n\n检测到 3 个相关 skill：\n- file-skill-registry (置信度1.0)\n..."
  }
}
```

Kimi CLI 的 `runner.py` 会提取 `inject_prompt` 字段，将其内容注入到 AI 上下文中。

---

## 配置速查表

### 快速修改（无需重启 Kimi CLI）

| 想改什么 | 改哪个文件 | 生效方式 |
|---------|-----------|---------|
| 新增硬编码关键词 | `kimi_skill_router.py` → `HARDCODED_RULES` | **需重启** CLI（Python 模块缓存） |
| 补充 skill 触发词 | `skill_triggers_enhanced.json` | **无需重启**（每次调用都重新加载） |
| 调整 LLM 阈值/模型 | `kimi_skill_router.py` → 顶部常量 | **需重启** CLI |
| 补充词汇分类规则 | `vocabulary_rules.json` | **无需重启** |
| 换 LLM API Key | `.env` | **无需重启** |

### 关键常量

```python
MAX_SKILLS = 5                    # 最多推荐几个 skill
CONFIDENCE_THRESHOLD = 0.60       # Step 2~3 的最低置信度
LLM_CONFIDENCE_THRESHOLD = 0.70   # Step 4 触发阈值
LLM_TIMEOUT = 15                  # API 超时（秒）
```

---

## 调试与排查

### Hook 没生效？

1. 检查 `hook_debug.log` 是否有 `"RECEIVED prompt_len=..."` 记录
   - 没有 → Kimi CLI 没有调用 hook，检查 `~/.kimi/config.yaml` 的 hook 配置
2. 检查是否有 `"OUTPUT matched=..."` 记录
   - 没有 → 所有 Step 都未命中，检查规则配置
3. 检查 stdout 是否有 JSON 输出
   - 没有 → 代码异常，查看 `"VOCAB_ERROR"` 或 `"INPUT_ERROR"`

### 匹配到的 skill 太少？

1. 降低 `CONFIDENCE_THRESHOLD`（如从 0.60 降到 0.50）
2. 为未命中的 skill 补充触发词到 `skill_triggers_enhanced.json`
3. 检查 `skill_index_cache.json` 是否包含该 skill
4. 确认 LLM 层配置正确（API key、网络连通性）

### 词汇记录没写入？

1. 检查 `~/.kimi/vocabulary_live.jsonl` 是否存在且可写
2. 检查 `hook_debug.log` 中是否有 `"VOCAB: added=N"`
3. 检查 `vocabulary_rules.json` 是否格式正确（JSON 无语法错误）

---

## 版本历史

| 日期 | 变更 |
|------|------|
| 2026-04-20 | 初始版本：四层匹配（硬编码→触发词→描述→LLM） |
| 2026-04-21 | 修复 `text_input_for_hook` list[TextPart] 提取 bug |
| 2026-04-22 | 放宽 `MAX_SKILLS` 3→5，增强代码场景硬编码规则 |
| 2026-04-23 | **新增 Step 5：词汇实时记录**，用户语言画像系统上线 |
