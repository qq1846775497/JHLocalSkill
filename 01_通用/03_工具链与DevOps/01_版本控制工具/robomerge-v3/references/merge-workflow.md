# RoboMerge v3 合并流程详解

> 源文件：`src/robo/nodebot.ts`、`src/robo/edgebot.ts`、`src/robo/targets.ts`、`src/robo/graph.ts`

---

## 总体流程图

```
┌─────────────────────────────────────────────────────────────┐
│                    watchdog.ts 守护进程                      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                   robo.ts 主进程                      │   │
│  │  ┌───────────────────────────────────────────────┐  │   │
│  │  │              GraphBot (每个 bot 一个)           │  │   │
│  │  │  ┌──────────────────┐  ┌──────────────────┐   │  │   │
│  │  │  │  NodeBot(Main)   │  │NodeBot(Release)  │   │  │   │
│  │  │  │  每 30s tick()   │  │  每 30s tick()   │   │  │   │
│  │  │  │         │        │  │        │         │   │  │   │
│  │  │  │  EdgeBot(→Rel)   │  │ EdgeBot(→DevBr)  │   │  │   │
│  │  │  └──────────────────┘  └──────────────────┘   │  │   │
│  │  └───────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 1. 初始化流程（Bot 启动）

```
watchdog.ts
  ├─ 启动 HTTP 状态服务（端口 4433）
  ├─ fork 子进程：node dist/robo/robo.js
  └─ 监控子进程崩溃，自动重启

robo.ts
  ├─ 初始化 PerforceContext（P4PORT/USER/PASSWD）
  ├─ 验证 P4 登录：p4 login -s
  ├─ 加载 branchmap.json（每个 botname 一个）
  ├─ 创建 GraphBot（一个 botname 对应一个）
  │     ├─ 解析分支图（Graph）
  │     ├─ 创建 NodeBot 实例（每个分支一个）
  │     └─ 创建 EdgeBot 实例（每条合并边一个）
  ├─ 启动 Web 服务器（端口 3000）
  └─ 初始化通知系统（Slack + Email）

NodeBot.start()
  ├─ 从持久化存储读取 lastCL
  ├─ 如果 lastCL 为空（新 bot）：
  │     └─ 查询当前最新 CL：p4 changes -m 1 //depot/...
  └─ 启动 EdgeBot（每个目标分支）
        └─ 从持久化读取 EdgeBot.lastCL
```

---

## 2. 轮询循环（NodeBot.tick()）

**触发频率：** 每 30 秒（`checkIntervalSecs`）

```
NodeBot.tick()
  │
  ├─ [跳过条件检查]
  │     ├─ Bot 被强制暂停（forcePause = true）→ skip
  │     ├─ 存在未解决冲突阻塞所有 edge → skip
  │     └─ 存在手动操作请求 → 优先处理队列
  │
  ├─ 查询新变更
  │     └─ p4 changes //depot/...@{lastCL+1},now
  │           ├─ 返回空 → tick 结束
  │           └─ 返回变更列表 → 按 CL 升序排列
  │
  └─ 对每个新 CL 执行：NodeBot._processChange(changeCl)
```

---

## 3. 变更处理（`_processChange(changeCl)`）

```
_processChange(changeCl)
  │
  ├─ [1] 获取变更详情
  │     └─ p4 describe -s -S @{changeCl}
  │           → 获取：user, description, files[], type[]
  │
  ├─ [2] 检查全局排除规则
  │     ├─ author ∈ excludeAuthors → 记录并跳过
  │     └─ description 匹配 excludeDescriptions 正则 → 跳过
  │
  ├─ [3] 解析 #robomerge 命令（见下方章节）
  │     └─ targets.ts: DescriptionParser.parse(description)
  │           → 返回 MergeAction[]（合并目标列表）
  │
  ├─ [4] 计算合并路径
  │     └─ graph.computeImplicitTargets(source, requestedTargets)
  │           → 展开 flowsTo 自动目标
  │           → 合并显式指定目标
  │           → 返回最终 targetList
  │
  ├─ [5] 对每个目标 EdgeBot 执行合并
  │     └─ EdgeBot.integrate(changeCl, mergeAction)
  │
  └─ [6] 更新 lastCL = changeCl
```

---

## 4. 描述解析（`DescriptionParser`）

### #robomerge 命令语法

RoboMerge 扫描提交描述的**每一行**，寻找以下模式：

```
#robomerge[botname] [flags/targets...]

botname 可选：不写则所有 bot 处理；写了则只有匹配 bot 处理
```

### 目标解析逻辑

```python
def parse_description(description: str, bot_name: str, node_aliases: list, macros: dict):
    targets = []
    flags = set()

    for line in description.split('\n'):
        line = line.strip()

        # 匹配 #robomerge 或 #robomerge[BOTNAME]
        m = re.match(r'#robomerge(?:\[(\w+)\])?(.*)', line, re.IGNORECASE)
        if not m:
            continue

        # 检查 bot 名匹配
        specified_bot = m.group(1)
        if specified_bot and specified_bot.upper() != bot_name.upper():
            continue

        tokens = m.group(2).split()
        for token in tokens:
            # 全局标志
            if token.lower() in ('ignore', 'deadend'):
                return []  # 完全跳过
            if token.lower() in ('#manual', 'manual', 'nosubmit', 'stage'):
                flags.add('manual')
            if token.lower() in ('null',):
                flags.add('null')

            # 跳过目标（-TargetName）
            elif token.startswith('-'):
                branch = resolve_alias(token[1:], node_aliases)
                targets.append(MergeAction(branch, mode='skip'))

            # Null merge 目标（!TargetName）
            elif token.startswith('!'):
                branch = resolve_alias(token[1:], node_aliases)
                targets.append(MergeAction(branch, mode='null'))

            # 宏展开（#macroname）
            elif token.startswith('#'):
                macro_name = token[1:].lower()
                if macro_name in macros:
                    for b in macros[macro_name]:
                        targets.append(MergeAction(b, mode='normal'))

            # 普通目标
            else:
                branch = resolve_alias(token, node_aliases)
                if branch:
                    targets.append(MergeAction(branch, mode='normal'))

    return targets, flags
```

### MergeMode 枚举

| MergeMode | 含义 |
|-----------|------|
| `normal` | 正常集成：integrate → resolve → submit |
| `null` | Null merge：integrate -i（只记录合并关系，不修改内容） |
| `skip` | 跳过：不集成，直接标记处理完毕 |
| `manual` | 手动：integrate → resolve → shelve（不提交） |
| `clobber` | 覆盖：等同 stomp（accept target version） |
| `safe` | 安全合并：不处理 conflicting edits，只接受 non-conflicting |

### Owner 优先级

在解析和执行过程中，RoboMerge 确定"谁负责解决问题"的优先级：

1. 手动/搁置/Stomp 请求发起者（最高优先级）
2. Edge 级别的 `resolver` 配置
3. Node 的 `reconsider` 操作发起者
4. 提交描述中的 `#robomerge-author` 标签
5. 变更的原始作者（最低优先级）

---

## 5. 分支图路由计算

```typescript
// src/robo/graph.ts

class Graph {
  // 节点（分支）
  nodes: Map<string, Node>
  // 边（合并路径）
  edges: Map<string, Edge>  // key: "SOURCE->TARGET"
}

// 计算隐式合并目标（flowsTo 展开）
computeImplicitTargets(
  source: Node,
  requestedTargets: Map<Node, MergeMode>
): ComputeResult {

  // 对每个 flowsTo 分支：
  for (const target of source.flowsTo) {
    // 如果显式请求中有 skip → 不添加
    // 如果显式请求中有 null → 用 null mode
    // 否则 → 用 normal mode 添加到目标列表

    // 检查 blockAssetFlow
    // 检查 disallowDeadend
    // 检查 forceAll
  }

  return {
    targets: Map<Node, MergeMode>,
    errors: string[]
  }
}
```

### 合并路径示例

```
Main ──flowsTo──→ Release-5.1 ──flowsTo──→ Release-5.0

提交在 Main，无 #robomerge 命令：
  → 自动合并到 Release-5.1
  → Release-5.1 tick 时，再合并到 Release-5.0

提交在 Main，含 #robomerge -Release-5.1：
  → 跳过 Release-5.1
  → 不自动到 Release-5.0（链断）

提交在 Main，含 #robomerge Release-5.0：
  → 自动到 Release-5.1（flowsTo）
  → 显式合并到 Release-5.0（绕过中间）
```

---

## 6. EdgeBot 合并执行（`EdgeBot.integrate()`）

```
EdgeBot.integrate(changeCl, mergeAction)
  │
  ├─ [1] 检查 edge 是否被阻塞
  │     └─ 如果 blockedCl 不为空 → 跳过（等待冲突解决）
  │
  ├─ [2] 检查 Gate 条件
  │     ├─ 读取 lastGoodCLPath 文件内容
  │     ├─ 如果 changeCl > gateLastGoodCL → 跳过
  │     └─ 检查 integrationWindow
  │
  ├─ [3] 获取/创建工作区
  │     ├─ 工作区命名：robomerge-{botname}-{source}-{target}
  │     └─ p4 client -i（如不存在则创建）
  │
  ├─ [4] 启动清理（进程生命周期内每 workspace 只执行一次）
  │     └─ cleanWorkspace()（p4util.ts）
  │           ├─ 全局 Map cleanedWorkspaces 保护：已清理 → 直接 return
  │           ├─ 还原所有 pending changes（revert）
  │           ├─ 删除所有 shelved 文件（shelve -d）
  │           ├─ 删除所有 pending changelists（change -d）
  │           └─ sync rootPath#0（清空 workspace，彻底重置到空状态）
  │
  ├─ [4b] integrate 前强制 sync #0（每个 CL 都执行，无去重保护）
  │     └─ 在 p4 integrate 调用之前（edgebot.ts:581/665）：
  │           await p4.sync(targetWorkspace, rootPath + '#0')
  │           ├─ integrate()  — 同服务器合并
  │           └─ transfer()   — 跨服务器合并（使用 targetServerP4）
  │           ▶ 为什么代价低：该 workspace 从不真正 sync 文件到磁盘，
  │             每次 integrate 后 revert/delete 已清空，
  │             sync #0 时本地没有文件需要删除，仅一次空确认往返
  │
  ├─ [5] 执行集成
  │     ├─ MergeMode = null：
  │     │     p4 integrate -i //from/...@{CL},{CL} //to/...
  │     │     p4 resolve -at（接受目标版本 = 放弃 null 内容）
  │     │     p4 submit
  │     │
  │     ├─ MergeMode = skip：
  │     │     记录 lastCL，不执行任何 p4 操作
  │     │
  │     └─ MergeMode = normal/clobber：
  │           p4 integrate [-b branchspec] -c @{CL}
  │           p4 resolve -N  → 检查是否有冲突
  │           ├─ 无冲突 → [6a] 提交
  │           └─ 有冲突 → [6b] 冲突处理
  │
  ├─ [6a] 提交
  │     ├─ 构造提交描述（含 #robomerge 追踪标签）
  │     └─ p4 submit -c {pendingCL}
  │
  ├─ [6b] 冲突处理（见 conflict-resolution.md）
  │     ├─ 分析冲突类型
  │     ├─ MergeMode = manual → shelf
  │     ├─ 需 approval → shelf + 阻塞
  │     └─ 自动处理失败 → 创建 blockage + 发通知
  │
  └─ [7] 更新 EdgeBot.lastCL = changeCl
```

---

## 7. 提交描述构造

RoboMerge 在合并提交的描述中添加追踪信息：

```
[Merge CL #12345 from //UE5/Main to //UE5/Release-5.0]

原始描述内容...

#robomerge[MYBOTNAME] Release-5.0
ROBOMERGE-SOURCE: Main
ROBOMERGE-OWNER: author@example.com
```

**Incognito 模式（`incognitoMode: true`）：**
```
[Merge from Main]
```
（不含 CL 号、不含 #robomerge 追踪标签）

---

## 8. Gate（CIS 质量门禁）

### Gate 文件格式

P4 中的纯文本文件，内容为一行 CL 号：

```
12345678
```

空文件表示没有通过 CI 的 CL，边界条件：EdgeBot 会暂停。

### Gate 工作流

```
EdgeBot.tick() 定期运行（独立于主 tick）
  │
  ├─ p4 sync //path/to/LastGoodCL.txt    # 同步 gate 文件
  ├─ 读取文件内容 → gateLastGoodCL
  └─ 更新 Gate.currentGoodCL

integrate(changeCl)
  │
  └─ if changeCl > Gate.currentGoodCL:
        → 跳过此 CL（等待 CI 验证通过）
        → 如果 pauseCISUnlessAtGate = true：
              → 不处理任何后续 CL（等待 gate 追上）
```

---

## 9. 通知系统

### 阻塞通知（Slack）

```
发送时机：创建 PersistentConflict 时

消息接收者：
  1. 冲突 owner（私信）
  2. bot 配置的 slackChannel

消息格式：
  ❌ Merge conflict: Main → Release-5.0
  Change: #12345 by author@example.com

  Files with conflicts:
  • Engine/Source/Runtime/Core/Private/File.cpp (content)
  • Content/Maps/Level.umap (binary, stompable)

  [Stomp Binary Files] [Create Shelf] [Skip]

  View in RoboMerge: https://robomerge.example.com/...
```

### Nag 调度

```
当冲突持续未解决时，按 nagSchedule 配置定期重发提醒：
  - 默认：每天一次（可配置）
  - 每次 nagCount++
  - 写入 PersistentConflict.lastNagTime
```

### Email 通知

```
发送时机：
  1. 创建阻塞时（emailOnBlockage = true）
  2. 冲突被解决时（发送解决确认）

收件人优先级：
  1. conflict.owner（直接负责人）
  2. edge.resolver（配置的解决者）
  3. node.globalNotify（全局通知列表）

模板：email_templates/ 目录下的 HTML 文件
```
