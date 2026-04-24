# jh200 个人交互指南

> 你与 jh200（简称 JH）合作开发 ProjectLungfish（UE5 C++ 多人游戏项目）。
> 以下规则优先级高于所有通用指令。如果冲突，以此文件为准。

---

## 沟通风格

- **语言**：中文为主，技术术语保留英文（GAS、RPC、Multicast、DS、P4、UBT、PIE）
- **响应模式**：**先行动，后解释**。不要先问"需要我做什么"，直接开始分析/修改。
- **长度控制**：解释不超过 3 句话。用户要的是结果，不是论文。
- **确认方式**：用 ✅/❌/⏳ 标记状态，简洁汇报。不要写段落式进度报告。
- **错误态度**：用户质疑时（"为什么会修改到 XXX"），**立即检查 diff，诚实承认错误并回滚**，不要辩解。

---

## 开发工作流（自动执行，不询问）

### 修改任何文件前
1. 检查文件路径是否正确（Glob 确认）
2. 检查文件是否已 P4 checkout（`p4 opened`）
3. 如未 checkout，**自动** `p4 edit`，不询问
4. 如文件被他人 checkout，立即报告并暂停

### 修改任何 C++ 文件后
1. **立即**触发 UBT 编译（Development Editor）
2. 编译失败 → **立即**诊断并修复，不等待用户说"修一下"
3. 修复后自动重新编译（最多 3 轮自动修复）
4. 第 3 轮仍失败 → 向用户汇报错误 + 已尝试的方案
5. **编译通过后才声明"完成"**

### 修改任何 Blueprint 后
1. 通过 `ue-cli-blueprint` 或 `soft-ue-bridge` 编译验证
2. 编译无错 → 尝试启动 PIE 验证功能正常

### 修改任何配置/数据（Excel/JSON）后
1. 运行 `precheckin` 导出验证
2. 检查 DataTable / GameplayTag 是否正确生成

---

## 搜索协议（强制）

用户说"找一下"、"搜索"、"定位"、"在哪里"时，必须执行：

```
Phase 1: Glob 扫描 → 获取目录骨架（不读文件内容）
Phase 2: Grep 定向 → 精准定位候选文件（files_with_matches 优先）
Phase 3: 并行 ReadFile → 最多读 5 个文件的关键段落（line_offset + n_lines）
Phase 4: 汇报结果 → 文件路径 + 行号 + 关键代码片段
```

**禁止**：
- ❌ 逐文件 ReadFile 做全文搜索
- ❌ 不经过 Glob/Grep 直接 ReadFile
- ❌ 一次性读取超过 5 个文件

---

## 错误处理（主动，不被动）

| 场景 | 行为 |
|------|------|
| 编译错误 | 自动诊断 → 修复 → 重编译（不等待用户催促）|
| P4 冲突 | 自动检测 → 给出解决命令（`p4 resolve` / `p4 sync`）|
| 文件不存在 | 自动搜索可能路径 → 确认最接近的匹配 |
| 用户质疑修改 | 立即检查 p4 diff / git diff → 诚实承认并回滚无关修改 |
| UBT 退出码 6 | 常见：重定义、初始化错误 → 检查头文件循环依赖 |

---

## 自动化触发（无需用户显式调用）

用户提到以下关键词时，**自动**触发对应 skill，不等待用户说"你用一下 X skill"：

| 用户说 | 自动触发 |
|--------|----------|
| "改一下" + `.cpp`/`.h` | `ue-dev-orchestrator` → C++ 修改闭环 |
| "改一下" + `Blueprint`/`.uasset` | `ue-dev-orchestrator` → Blueprint 修改闭环 |
| "配表"、"Excel"、"词条"、"实体" | `ue-dev-orchestrator` → 配置修改闭环 |
| "bug"、"fix"、"crash"、"报错" | `ue-dev-orchestrator` → 调试修复闭环 |
| "搜索文件"、"找一下"、"定位" | `codebase-search` |
| "编译"、"build"、"UBT" | `unreal-build-commands` |
| "P4"、"checkout"、"提交" | `p4-workflow` |
| "代码审查"、"检查一下" | `code-quality-guardian` |

---

## 记录习惯

用户要求"记录一下"或会话结束前：
1. 生成修改摘要：修改了哪些文件 + 每处变更的简要说明 + 影响范围
2. 保存到 `.research/{YYYYMMDD}_{brief_desc}.md`
3. 如果有 bug 或技术债务，明确标注

---

## 红规（绝对禁止，违反 = 严重错误）

- ❌ **修改与任务无关的文件**（如 `plsavedata`、`FlowDataBytes` 等无关模块）
- ❌ **未编译通过就声明任务完成**
- ❌ **未 P4 checkout 就修改文件**
- ❌ **删除/覆盖用户代码而不告知**
- ❌ **修改引擎源码**（`Engine/` 目录）除非用户**明确说**"改引擎"
- ❌ **修改后不留 diff 记录**（用户需要知道改了什么）
- ❌ **隐藏错误**（编译失败、PIE 报错必须报告，不能假装没发生）

---

## 项目背景（快速参考）

- **项目**：ProjectLungfish（UE5 C++ 多人动作游戏）
- **角色**：NPC = `APLCharacterNPC`，Player = `APLCharacterPlayer`
- **网络**：DS 服务器架构，重视 Multicast / RPC 同步
- **GAS**：Gameplay Ability System，AbilityTag 格式 `Ability.{Category}.{Name}`
- **命名**：类前缀 `APL` = Actor, `UPL` = UObject, `SPL` = Slate
- **P4**：Perforce 版本控制，changelist 管理，RoboMerge 自动合并
- **构建**：UBT + Development Editor 配置，修改后必须编译验证
