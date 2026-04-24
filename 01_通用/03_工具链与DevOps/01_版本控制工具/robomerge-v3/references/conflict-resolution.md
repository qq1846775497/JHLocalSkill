# RoboMerge v3 冲突解决全流程

> 源文件：`src/robo/edgebot.ts`、`src/robo/conflicts.ts`、`src/robo/nodebot.ts`

---

## 冲突类型分类

### FailureKind 枚举

| 类型 | 说明 | 触发场景 |
|------|------|----------|
| `Merge conflict` | 文件内容冲突 | p4 resolve 后仍有未解决文件 |
| `Exclusive check-out` | 文件被独占锁定 | 文件类型为 `+l`（exclusive lock）的文件被他人打开 |
| `Commit failure` | 提交失败 | p4 submit 返回错误 |
| `Split move` | 移动操作拆分 | Move/delete 未与 Move/add 一起集成 |
| `Partial integrate` | 部分集成 | integrate 时文件已被独占打开 |

### ConflictedResolveNFile 结构

```python
@dataclass
class ConflictedFile:
    client_file: str            # 工作区本地路径
    from_file: str              # 源 depot 路径
    start_from_rev: str         # 起始版本 "#123"
    end_from_rev: str           # 结束版本 "#124"
    resolve_type: str           # content | branch | delete | unknown
    content_resolve_type: str   # 3waytext | 2wayraw | "" (非文本)
```

### 可 Stomp 判定逻辑

```python
def is_stompable(conflict_files: list[ConflictedFile], fstat_results: dict) -> bool:
    """
    所有冲突文件均为二进制 asset 时，才允许 Stomp。
    """
    NON_BINARY_EXTENSIONS = {'.cpp', '.h', '.cs', '.py', '.ini', '.cfg', '.txt', '.xml', '.json'}
    STOMPABLE_EXTENSIONS = {'.uasset', '.umap', '.upk', '.pak', '.collection'}

    for f in conflict_files:
        file_type = fstat_results.get(f.client_file, {}).get('headType', '')
        # P4 文件类型包含 "binary" 关键字 → 可 stomp
        if 'binary' not in file_type and 'ubinary' not in file_type:
            # 检查扩展名白名单
            ext = os.path.splitext(f.client_file)[1].lower()
            if ext not in STOMPABLE_EXTENSIONS:
                return False
    return True
```

---

## 三种解决方式详解

### 方式一：STOMP（覆盖合并，仅限二进制文件）

**触发条件：**
1. 用户在 Web UI 或 Slack 点击 [Stomp]
2. 或 EdgeBot 判断所有冲突文件均为 binary

**执行流程：**

```
verifyStomp(changeCl, targetBranch)
  ├─ [1] 验证参数和 edge 状态
  │     ├─ 该 edge 确实被 changeCl 阻塞
  │     ├─ 对应 PersistentConflict 存在且未解决
  │     └─ 不存在独占文件锁（exclusive checkout）
  │
  ├─ [2] 重新集成（验证模式）
  │     ├─ cleanWorkspace()
  │     ├─ p4 integrate -c @{changeCl}
  │     └─ p4 resolve -N → 获取冲突文件列表
  │
  ├─ [3] 文件分析
  │     ├─ 对每个冲突文件：
  │     │     ├─ p4 fstat → 获取文件类型
  │     │     ├─ 检查是否为 binary/ubinary
  │     │     └─ 非 binary → 报错，Stomp 不可用
  │     └─ 计算被覆盖的历史版本（stompedRevisions）
  │           └─ p4 filelog -m 100 → 从公共祖先到 HEAD 的所有修改
  │
  └─ [4] 返回验证结果
        ├─ isStompable: true/false
        ├─ stompedRevisions: [{cl, author, description}]
        └─ error?: string

stompChanges(owner, changeCl, targetBranch)
  ├─ 再次调用 verifyStomp（二次确认）
  ├─ 收集被覆盖的作者列表（stompedAuthors）
  ├─ p4 resolve -ay（accept yours = 接受目标分支版本 = 放弃源分支改动）
  ├─ 构造提交描述（添加 #fyi @stompedAuthor1 @stompedAuthor2）
  ├─ p4 submit -c {pendingCL}
  ├─ 标记冲突为 resolved（resolution = 'resolved'）
  └─ 发送 Stomp 完成通知给被覆盖的作者
```

**被覆盖版本追踪：**

```python
def get_stomped_revisions(depot_file: str, ancestor_rev: int) -> list:
    """
    找出从公共祖先到 HEAD 之间，目标分支上对该文件的所有修改。
    这些修改将被 Stomp 覆盖。
    """
    # p4 filelog -m 100 //target/depot/path/file
    # 过滤：version > ancestor_rev
    # 排除 Tasks 流（//Tasks/...）
    # 最多返回 100 个版本
    ...
```

---

### 方式二：SHELF（搁置，人工解决）

**触发条件：**
1. 用户点击 [Create Shelf]
2. 提交描述含 `#robomerge #manual`
3. Edge 配置了 `approval`（需审批）
4. 自动解决失败且文件包含文本冲突

**执行流程：**

```
createShelf(changeCl, targetBranch, reason)
  │
  ├─ [1] 重新集成
  │     ├─ cleanWorkspace()
  │     ├─ p4 integrate -c @{changeCl}
  │     └─ p4 resolve -am（尝试自动合并文本）
  │         → 保留仍有冲突的文件（标记 conflict markers）
  │
  ├─ [2] 修改 Changelist 描述
  │     └─ 添加以下标签：
  │           [ROBOMERGE] Shelved for manual resolution
  │           Reason: {reason}
  │           Original CL: #12345 by author@example.com
  │           #codereview   ← 触发代码审查邮件（如配置）
  │
  ├─ [3] 检查 Owner 是否为 bot
  │     └─ 如果 owner 是自动化账户 且 !forceCreateAShelf → 中止
  │
  ├─ [4] Shelf 操作
  │     └─ p4 shelve -c {pendingCL}   ← 创建 shelf
  │
  ├─ [5] 找到 Owner 的工作区
  │     └─ chooseBestWorkspaceForUser(owner)
  │           → 匹配流的工作区 > 最近使用的工作区
  │
  ├─ [6] 转移 Shelf 给 Owner
  │     ├─ p4 reopen -c {pendingCL} -s {ownerWorkspace}
  │     └─ p4 change -u {owner} -c {pendingCL}
  │           ← 修改 changelist owner 为目标用户
  │
  └─ [7] 发送通知
        ├─ Email 给 owner：
        │     "Shelf #{pendingCL} 已在你的工作区 {ownerWorkspace} 中创建
        │      请在 P4V 中解决冲突并提交"
        └─ Slack 消息（如有配置）

用户手动解决步骤（P4V）：
  1. Pending Changelists → 找到 shelf CL
  2. 右键 → Unshelve Files
  3. 手动解决冲突文件
  4. Submit（P4V 会提示删除 shelved 文件）
  5. RoboMerge 检测到该变更，识别 ROBOMERGE 标签
  6. 将 edge 标记为已解决，lastCL 推进
```

**Approval 工作流（Edge 配置了 approval 字段）：**

```
createShelf(changeCl, reason="Awaiting approval")
  ├─ 同上流程创建 Shelf
  ├─ 阻塞 edge（不处理后续变更）
  └─ 发送审批请求
        ├─ Slack 消息到 approval.channelId
        └─ 消息含 [Approve] [Reject] 按钮

审批通过后：
  roboserver.ts 接收 /approve 请求
  └─ 标记 approval 完成 → edge 解除阻塞
```

---

### 方式三：SKIP（跳过）

**触发条件：**
1. 用户在 Web UI 或 Slack 点击 [Skip]
2. 提交描述含 `-TargetBranch`

**执行流程：**

```
skipConflict(skippingAuthor, changeCl, targetBranch)
  ├─ cleanWorkspace()（清理任何 pending 状态）
  ├─ 标记 PersistentConflict.resolution = 'skipped'
  ├─ 标记 PersistentConflict.resolvingAuthor = skippingAuthor
  ├─ 更新 EdgeBot.lastCL = changeCl（跳过该 CL）
  ├─ 解除 edge 阻塞
  └─ 发送通知："CL #12345 已被 {skippingAuthor} 跳过"

注意：被跳过的 CL 不会合并到目标分支。
     如果该 CL 修改的文件后续有冲突，可能导致后续合并更复杂。
```

---

## 独占文件锁（Exclusive Check-out）

### 检测流程

```python
# 集成时检测独占文件
# INTEGRATION_FAILURE_REGEXES[0]:
# r"^(.*[\\\/])(.*) - can't \w+ exclusive file already opened"
#
# 返回 ExclusiveFileDetails：
@dataclass
class ExclusiveFileDetails:
    depot_path: str   # 被锁文件的 depot 路径
    user: str         # 锁定该文件的用户
    client: str       # 锁定该文件的工作区
```

### 处理方式

1. **等待（推荐）：** 文件被锁定通常是临时状态，等待锁定用户提交后再重试
2. **强制解锁（管理员）：** 通过 Web UI 的 [Unlock] 按钮

```
verifyUnlock(changeCl, targetBranch)
  └─ 确认文件确实被锁定（非仅冲突）

unlockChanges(owner, changeCl, targetBranch)
  └─ p4 unlock -f -c {lockedCL} //depot/path/locked-file
     ← 需要 P4 管理员权限
```

---

## PersistentConflict 完整生命周期

```
[创建]
conflicts.onBlockage(blockage)
  ├─ 创建 PersistentConflict 对象
  ├─ 写入持久化存储（JSON 文件）
  ├─ 发送 Slack/Email 通知
  └─ 如配置 reportToBuildHealth → 创建 UGS issue

[查询]
conflicts.getUnresolvedConflicts()
  └─ 返回所有 resolution 为 null 的冲突

[确认（Acknowledge）]
conflicts.acknowledgeConflict(acknowledger, changeCl)
  ├─ 记录 acknowledger, acknowledgedAt
  └─ 停止 nag 提醒（但不解除阻塞）

[解决]
conflicts.resolveConflict(changeCl, resolution, resolvingAuthor)
  ├─ 设置 resolution = 'resolved' | 'skipped'
  ├─ 设置 resolvingAuthor
  ├─ 计算 timeTakenToResolveSeconds
  └─ 持久化更新

[解除阻塞]
nodeBot.unblock(reason)
  ├─ 清除 blockedCl 状态
  ├─ 触发等待该 edge 的 queuedChanges
  └─ 如配置 UGS → 更新 UGS issue 状态为已解决

[Nag 调度]
nagScheduler.tick()
  ├─ 检查所有未解决冲突
  ├─ 如果 (now - lastNagTime) > nagInterval：
  │     ├─ 重发 Slack/Email 提醒
  │     ├─ nagCount++
  │     └─ lastNagTime = now
  └─ 继续等待
```

---

## 阻塞状态下的 Edge 行为

当 edge 被阻塞时：

```
EdgeBot.integrate()
  ├─ 检查 this.blockage 是否存在
  └─ 如果有 blockage：
        ├─ 记录"edge 被 CL #{blockage.cl} 阻塞"
        ├─ 不执行任何 p4 操作
        └─ 返回 'blocked' 状态

NodeBot._processChange()
  ├─ 检查相关 EdgeBot 是否阻塞
  └─ 如果阻塞：
        ├─ 将 changeCl 加入 queuedChanges
        └─ 等待 unblock 信号后重新处理
```

---

## 冲突相关的 REST API

| Endpoint | 参数 | 说明 |
|----------|------|------|
| `POST /api/:bot/:node/stomp` | `{cl, targetBranch}` | 触发 Stomp |
| `POST /api/:bot/:node/shelf` | `{cl, targetBranch}` | 创建 Shelf |
| `POST /api/:bot/:node/skip` | `{cl, targetBranch}` | 跳过冲突 CL |
| `POST /api/:bot/:node/acknowledge` | `{cl}` | 确认收到冲突通知 |
| `POST /api/:bot/:node/unacknowledge` | `{cl}` | 取消确认 |
| `GET /api/:bot/:node/conflicts` | — | 获取当前所有冲突 |
| `POST /api/:bot/:node/unlock` | `{cl, targetBranch}` | 强制解除文件锁 |
| `POST /api/:bot/:node/reconsider` | `{cl}` | 重新处理指定 CL |
