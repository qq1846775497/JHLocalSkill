---
name: pie-error-fix-notify
description: |
  PIE 错误分析、蓝图自动修复、修复报告生成、飞书群通知的完整流程。
  当用户提到 PIE 错误、PIEErrorList、运行时蓝图崩溃、需要修复 PIE 报错并通知相关人员时触发此 skill。
  触发词：PIE 错误、PIEErrorList、蓝图空指针、运行时崩溃修复、发飞书通知、notify_pie_errors。
  即使用户只说"帮我看看 PIE 报错"或"PIE 又出问题了"，也应使用此 skill。
---

# PIE 错误修复 + 飞书通知 Skill

## 概述

本 skill 覆盖从 PIE 错误分析到飞书通知的完整流程：

1. **分析** `PIEErrorList.txt` — 读取、去重、分类
2. **修复** 可自动修复的蓝图/资产问题（通过 UnrealMCP）
3. **记录** 修复报告到 `ClaudeTasks/Fixes/PIEErrorFixes.md`
4. **通知** 飞书群，每个错误类别一条消息，@相关责任人

---

## 关键路径

| 资源 | 路径 |
|------|------|
| 错误数据 | `D:/ChaosCookOfficeMainDepot/PIEErrorList.txt` |
| 通知脚本 | `F:/ClaudeProjects/feishu-cli/notify_pie_errors.py` |
| 修复报告 | `ClaudeTasks/Fixes/PIEErrorFixes.md` |
| 飞书配置 | `~/.feishu-cli/config.yaml` |
| P4 用户 → Feishu UID API | `GET http://192.168.2.13:5000/user/get_feishu_userid?users=<p4name>` |
| 中文姓名 API | `GET http://192.168.2.13:5000/content_manager/users` |
| 自动化通知群 chat_id | `oc_afc800ef3a9a65ae7c924795357c5240` |

---

## Step 1：分析 PIEErrorList.txt

每行是一个 JSON 对象：
```json
{"affected_users": 4, "error_count": 240, "message": "...", "user_list": ["JiangLei", "ZhangYichen"]}
```

**分类逻辑：**
- **已修复**：message 中匹配 `FIXED_PATTERNS`（见通知脚本）
- **可自动修复**：有明确根因且可通过 MCP 加 IsValid/删空引用解决
- **待人工处理**：架构决策、数据配表、关卡美术、复杂业务逻辑

按 `error_count` 降序排列，对相同前 60 字符的消息去重。

**常见可自动修复模式（IsValid 空指针保护）：**
- `GetXxxComponent() → downstream node`（无 null 检查）→ 在执行链插入 IsValid + Branch
- `GrantedGameplayAbilities` 含 `Ability = None` 条目 → Python 脚本过滤删除

---

## Step 2：蓝图修复（UnrealMCP）

**前置条件：** 读取 `.claude/skills/projectlungfish-unrealmcp-use/SKILL.md` 了解 MCP 调用格式。

**修复前必须 P4 checkout：**
```bash
p4 edit "Main/Content/路径/Blueprint.uasset"
p4 edit "Main/Content/路径/Blueprint.uexp"
```

**IsValid 空指针保护标准做法（两节点模式）：**

因为 `KismetSystemLibrary::IsValid` 是纯函数（无 exec 引脚），需要配合 Branch：

```
原执行链:  EntryNode.then → TargetNode.execute
修复后:    EntryNode.then → Branch.execute
           GetComponent.ReturnValue → IsValid(pure).Object
           IsValid.ReturnValue → Branch.Condition
           Branch.then → TargetNode.execute
           Branch.else → (空，即提前返回)
```

MCP 操作顺序：
1. `disconnect-pins`：断开原 execute 连接
2. `add-graph-node`（IsValid，纯函数）：`{"FunctionReference": {"MemberParentClass": "KismetSystemLibrary", "MemberName": "IsValid"}}`
3. `add-graph-node`（Branch / K2Node_IfThenElse）
4. `connect-pins`：按上图接线
5. `compile-blueprint`：确认无报错
6. `save-asset`

每修复一个蓝图，验证 compile 输出无错误后再继续。

**注意：** GA 蓝图的图名通常是 `"Gameplay Ability Graph"`，而非默认的 `"EventGraph"`。

---

## Step 3：写修复报告

路径：`ClaudeTasks/Fixes/PIEErrorFixes.md`

结构：
```markdown
# PIE Error Fixes — YYYY-MM-DD

## Summary
（简述：分析了多少条错误，修复了哪些，P4 CL 号）

## Fixed Items
### 1. 蓝图名 — 函数名 问题描述
**Error**: 原始错误信息
**Root cause**: 根因分析
**Fix**: 修复方式
**Graph delta**: 具体节点操作记录

## Pending Confirmation
（需策划/美术确认的项目）

## Items That Could NOT Be Auto-Fixed
（表格：# | 错误模式 | 无法自动修复的原因）
```

P4 add 报告文件到同一个 CL：
```bash
p4 add "ClaudeTasks/Fixes/PIEErrorFixes.md"
p4 reopen -c <CL号> "ClaudeTasks/Fixes/PIEErrorFixes.md"
```

---

## Step 4：更新通知脚本并发送飞书通知

### 4a. 更新 FIXED_PATTERNS

打开 `F:/ClaudeProjects/feishu-cli/notify_pie_errors.py`，在 `FIXED_PATTERNS` 和 `fixed_meta` 中添加本次新修复的条目：

```python
# FIXED_PATTERNS 里加匹配规则（keyword1, keyword2, group_key）
("BlueprintName", "FunctionName", "fix_new_key"),

# fixed_meta 里加描述
"fix_new_key": (
    "✅ [已修复] BlueprintName — FunctionName 问题描述 CL XXXXX",
    "错误：...\n修复：...\n修改文件：...",
),
```

同样，如果本次有新的待处理错误类型，在 `PENDING_GROUPS` 中补充对应条目。

### 4b. 运行脚本发送通知

```bash
cd F:/ClaudeProjects/feishu-cli
echo y | py -X utf8 notify_pie_errors.py
```

脚本会：
1. 读取 `PIEErrorList.txt`，批量获取全部用户的 Feishu open_id
2. 把错误分类为「已修复」和「待处理」
3. 发送 1 条总结 + 每个错误类别 1 条独立消息（含修复建议、@相关人员）

**消息格式要求：**
- 已修复：`✅ [已修复] 标题\n\n错误描述\n修复描述\n修改文件\n\n影响人员：@...`
- 待处理：`⚠️ [优先级] 标题\n\n错误描述\n修复建议\n负责人\n\n相关人员：@...`
- At-mention 格式：`<at user_id="ou_xxx">中文姓名</at>`

---

## 错误分类参考（不可自动修复的常见类型）

| 类型 | 原因 | 负责人 |
|------|------|--------|
| GSCAttributeSet 未 Grant | ASC 初始化时序（架构决策） | 程序组 |
| ensureAsRuntimeWarning BT | AI 销毁时 BT 还在运行 | AI 程序 |
| EntityRowToDTTag 缺失 | 数据配表工作 | 策划组 |
| SetByCaller 未赋值 | 所有调用点不明 + 正确值不明 | 战斗程序 |
| BuildingBlock 无效 RuntimeGrid | 关卡 Actor 配置 | 关卡/美术组 |
| EditCondition 字段不存在 | C++ 字段删除，需 CoreRedirects | 程序 |
| 结构体未知（PLProjectileAttachConfig 等） | Schema 变更 | 程序 |

---

## 完成后的收尾

- 确认飞书群消息已发出，@mention 显示正常
- 报告 CL 号给用户，等待用户明确说 submit 后再提交
- **不要**在用户确认前执行 `p4 submit`
