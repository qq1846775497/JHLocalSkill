# RoboMerge v3 P4 命令封装参考

> 源文件：`src/common/perforce.ts`（1500+ 行）、`src/common/p4util.ts`

---

## 执行层：`_execP4()`

底层通过 `child_process.execFile` 运行 `p4` 命令：

```typescript
static async _execP4(
  logger: Logger,
  workspaceDir: string,     // 工作区根目录（设置 CWD）
  args: string[],           // 命令参数数组
  opts?: ExecP4Opts
): Promise<string>
```

### 环境变量注入

```
P4PORT   = perforceContext.port
P4USER   = perforceContext.user
P4CLIENT = workspace.name   （执行工作区相关命令时）
P4PASSWD = token            （通过 vault 注入，不写入磁盘）
```

### 错误分类

```typescript
// 集成失败（立即返回，不重试）
const INTEGRATION_FAILURE_REGEXES = [
  [/^(.*[\\\/])(.*) - can't \w+ exclusive file already opened/, 'partial_integrate'],
  [/Move\/delete\(s\) must be integrated along with matching move\/add\(s\)/, 'split_move'],
]

// 瞬时错误（自动重试，最多 3 次，指数退避）
const RETRY_ERROR_MESSAGES = [
  'socket: Connection reset by peer',
  'socket: Broken pipe',
  'TCP receive failed',
]
```

---

## ztag 输出解析

RoboMerge 大量使用 `p4 -ztag` 格式获取结构化输出：

```
... change 12345678
... user builduser
... desc My commit message\n
... status submitted
```

解析函数 `parseZTag(output: string): Record<string, string>[]`：
1. 按空行分割 record
2. 每行解析为 `... key value` 格式
3. 支持数组字段（如 `depotFile0`, `depotFile1`）
4. 返回对象数组

---

## RoboMerge 使用的完整 P4 命令

### 认证与连接

```bash
p4 login -s                          # 验证登录状态（不续期）
p4 login                             # 交互登录（获取 ticket）
p4 info                              # 获取服务器信息（版本、时区等）
p4 users -m 1000                     # 列出用户（用于邮箱查找）
```

### 变更查询

```bash
# 查询分支最新变更
p4 -ztag changes -m 1 //depot/path/...

# 查询区间变更（不含起始，含结束）
p4 -ztag changes //depot/path/...@{fromCL+1},{toCL}

# 查询某分支某 CL 之后的所有变更
p4 -ztag changes -l //depot/path/...@{lastCL+1},now

# 获取变更详情（含文件列表）
p4 -ztag describe -s -S @{CL}        # -S 包含 shelved 文件
p4 -ztag describe -s @{CL}           # 不含 shelved

# 获取集成历史
p4 -ztag integrated -i @{CL}         # 哪些变更被集成进该 CL

# 获取文件历史
p4 -ztag filelog -m 100 //depot/path/file   # 最多 100 个版本
```

**describe -ztag 输出字段：**
```
change      变更号
user        提交用户
desc        描述（多行，以 \n 拼接）
status      submitted | pending | shelved
date        时间戳（Unix 秒）
depotFile0  第一个文件的 depot 路径
type0       文件类型（binary/text/unicode 等）
action0     操作（add/edit/delete/branch/integrate 等）
rev0        版本号
```

### 工作区管理

```bash
# 创建或更新工作区（从 stdin 读取 spec）
p4 client -i < client_spec.txt

# 删除工作区
p4 client -d {workspace_name}

# 列出工作区
p4 -ztag clients -u {username}

# 获取工作区详情
p4 -ztag client -o {workspace_name}
```

**Client Spec 格式（创建合并工作区）：**
```
Client: robomerge-main-to-release50
Owner:  robomerge-service
Root:   /tmp/robomerge/workspaces/main-to-release50
Options: noallwrite noclobber nocompress unlocked nomodtime normdir
SubmitOptions: submitunchanged
View:
    //UE5/Main/... //robomerge-main-to-release50/...
```

### 同步操作

```bash
# 同步到指定版本（强制覆盖）
p4 sync -f //depot/path/...#{revision}

# 同步到最新（带进度）
p4 sync //depot/path/...

# 同步到空（清空工作区本地文件）
p4 sync //depot/path/...#0

# 预览同步（不实际下载）
p4 sync -n //depot/path/...
```

### 集成（核心操作）

```bash
# 使用 branchspec 集成特定 CL
p4 integrate -b {branchspec} -c @{CL} -S -P

# 使用路径集成
p4 integrate //from/...@{CL},{CL} //to/...

# 使用流集成（stream-based）
p4 integrate -S //UE5/Main -r -c @{CL}

# 查看已集成内容
p4 -ztag integrated //depot/path/...
```

**integrate 参数说明：**
- `-b branchspec`：使用命名的 branchspec 定义映射
- `-c @CL`：只集成该 CL 的内容（Create changelist）
- `-S`：使用流映射（stream integration）
- `-P`：仅集成父流（不向上传播）
- `-r`：反向集成（子流 → 父流）

### 解决冲突

```bash
# 检查剩余冲突（不实际解决，仅报告）
p4 resolve -N

# 自动接受合并（文本 3-way merge）
p4 resolve -am

# 接受目标版本（"yours"，用于 stomp 场景）
p4 resolve -ay

# 接受源版本（"theirs"）
p4 resolve -at

# 接受分支（binary 文件的 branch resolve）
p4 resolve -ab

# 查看已打开文件的状态（用于分析冲突类型）
p4 -ztag fstat -Ro //depot/path/...
p4 -ztag fstat -Ru //depot/path/...       # 未解决的文件
```

**resolve -N 输出解析（ConflictedResolveNFile）：**
```
... clientFile  /path/to/workspace/file.cpp
... fromFile    //UE5/Main/Engine/Source/file.cpp
... startFromRev  #123
... endFromRev    #124
... resolveType   content    ← content | branch | delete | unknown
... contentResolveType  3waytext  ← 3waytext | 2wayraw
```

**resolveType 含义：**
- `content`：文件内容冲突（可能是文本或二进制）
- `branch`：文件在一侧新增（branch 操作）
- `delete`：文件在一侧删除
- `unknown`：无法确定（通常需要人工干预）

**contentResolveType 含义：**
- `3waytext`：可做 3-way 文本合并
- `2wayraw`：无法 3-way（二进制或无公共祖先）

### 提交操作

```bash
# 提交指定 changelist
p4 submit -c {changelist_number}

# 提交并重用描述
p4 submit -c {changelist_number} -d "合并描述"

# 搁置（Shelf）
p4 shelve -c {changelist_number}

# 删除搁置的文件
p4 shelve -d -c {changelist_number}

# 取消搁置（恢复到工作区）
p4 unshelve -s {shelf_cl} -c {target_cl}
```

### Changelist 管理

```bash
# 创建/修改 changelist（从 stdin 读取 spec）
p4 change -i < changelist_spec.txt

# 删除 pending changelist（须先 revert）
p4 change -d {changelist_number}

# 列出指定工作区的 pending changelists
p4 -ztag changes -s pending -c {workspace_name}

# 将文件重新分配到另一个 changelist
p4 reopen -c {new_cl} //depot/path/file

# 查看 changelist 打开的文件
p4 -ztag opened -c {changelist_number}
```

**Changelist Spec 格式：**
```
Change: new
Client: robomerge-main-to-release50
User:   robomerge-service
Status: new
Description:
    [Merge CL #12345 from //UE5/Main to //UE5/Release-5.0]
    [RoboMerge] Main -> Release-5.0
    #robomerge[MYBOT] Release-5.0
```

### 还原操作

```bash
# 还原工作区所有修改
p4 revert //depot/path/...

# 还原未修改的文件（减少提交噪音）
p4 revert -a //depot/path/...

# 强制还原（忽略锁）
p4 revert -k //depot/path/...
```

### 文件状态查询

```bash
# 获取文件状态（打开/未打开、类型、action 等）
p4 -ztag fstat //depot/path/file

# 批量状态（集成后检查）
p4 -ztag fstat -Ro //depot/path/...    # 已打开的文件

# 查看文件锁定状态
p4 -ztag fstat -Op //depot/path/file
```

**fstat 输出关键字段：**
```
depotFile       //depot/path/file
clientFile      /workspace/path/file
headRev         HEAD 版本号
headType        文件类型（text, binary+l, etc.）
haveRev         本地版本号
action          本地操作（edit/add/delete/branch/integrate）
ourLock         是否被当前用户锁定
otherLock       是否被其他用户锁定
otherOpen0      其他打开用户
otherAction0    其他用户操作
```

---

## 工作区清理（`p4util.cleanWorkspace()`）

初始化 EdgeBot 工作区时执行：

```python
# 对应的 Python 逻辑：
def clean_workspace(workspace_name: str, workspace_root: str):
    # 1. 还原所有 pending 变更
    run_p4(['revert', '//...'], workspace=workspace_name)

    # 2. 删除所有 shelved 文件
    pending_cls = get_pending_changelists(workspace_name)
    for cl in pending_cls:
        run_p4(['shelve', '-d', '-c', str(cl)], workspace=workspace_name)
        run_p4(['change', '-d', str(cl)], workspace=workspace_name)

    # 3. 同步到空（清除本地文件）
    run_p4(['sync', '-k', f'//...#0'], workspace=workspace_name)
```

---

## 工作区选择（`chooseBestWorkspaceForUser()`）

为 Shelf 操作选择用户的最佳工作区：

1. 列出该用户的所有工作区：`p4 clients -u {username}`
2. 过滤排除：
   - 名称含 `horde-p4bridge-` 的工作区
   - 名称含 `swarm-` 的工作区
3. 优先选择：与目标流匹配的工作区
4. 否则选择：最近访问时间最新的工作区

---

## P4 错误处理规范

```python
class P4Error(Exception):
    pass

class P4IntegrationFailure(P4Error):
    kind: str  # 'partial_integrate' | 'split_move'

class P4TransientError(P4Error):
    pass  # 可重试

def run_p4(args, workspace=None, retries=3):
    """
    执行 p4 命令，处理错误分类和重试逻辑。
    """
    for attempt in range(retries):
        try:
            result = subprocess.run(['p4', '-ztag', *args], ...)
            check_integration_failures(result.stderr)
            return parse_ztag(result.stdout)
        except P4TransientError:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)  # 指数退避
                continue
            raise
```
