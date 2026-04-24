# RoboMerge v3 → Python 复刻指南

> 本文档提供将 RoboMerge v3（TypeScript/Node.js）核心逻辑以 Python 实现的模块划分、数据结构、关键代码骨架。

---

## 模块架构对应关系

| RoboMerge TS 类 | Python 模块 | 职责 |
|----------------|------------|------|
| `Perforce` (perforce.ts) | `p4client.py` | P4 命令封装、ztag 解析 |
| `NodeBot` (nodebot.ts) | `node_bot.py` | 分支监控、tick 循环 |
| `EdgeBot` (edgebot.ts) | `edge_bot.py` | 合并执行、冲突处理 |
| `DescriptionParser` (targets.ts) | `description_parser.py` | #robomerge 命令解析 |
| `Graph` (graph.ts) | `branch_graph.py` | 分支图与路由计算 |
| `Conflicts` (conflicts.ts) | `conflict_manager.py` | 冲突持久化与管理 |
| `Notifications` (notifications.ts) | `notifier.py` | Slack/Email 通知 |
| `Gate` (gate.ts) | `gate.py` | CIS 质量门禁 |
| `RoboServer` (roboserver.ts) | `api_server.py` | REST API（可选） |
| `Settings` (settings.ts) | `state_store.py` | 状态持久化 |

---

## 实现优先级

```
P1（核心，必须先实现）：
  1. p4client.py       — 所有后续模块依赖此模块
  2. description_parser.py — 决定是否合并和合并目标
  3. branch_graph.py   — 路由计算
  4. state_store.py    — 持久化 lastCL 和冲突

P2（主要功能）：
  5. node_bot.py       — 监控循环
  6. edge_bot.py       — 实际集成逻辑
  7. conflict_manager.py — 冲突追踪

P3（扩展功能）：
  8. gate.py           — CIS 门禁
  9. notifier.py       — Slack/Email
  10. api_server.py    — Web UI（可用 FastAPI）
```

---

## P1：`p4client.py` — P4 命令封装

```python
import subprocess
import re
import time
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# ─── 错误分类 ───────────────────────────────────────────────────

INTEGRATION_FAILURE_PATTERNS = [
    (re.compile(r"can't \w+ exclusive file already opened"), "partial_integrate"),
    (re.compile(r"Move/delete\(s\) must be integrated along with matching move/add\(s\)"), "split_move"),
]

RETRY_ERRORS = [
    "socket: Connection reset by peer",
    "socket: Broken pipe",
    "TCP receive failed",
]

class P4Error(Exception):
    pass

class P4IntegrationFailure(P4Error):
    def __init__(self, msg: str, kind: str):
        super().__init__(msg)
        self.kind = kind  # 'partial_integrate' | 'split_move'

class P4TransientError(P4Error):
    pass

# ─── ztag 输出解析 ───────────────────────────────────────────────

def parse_ztag(output: str) -> list[dict]:
    """
    解析 p4 -ztag 输出格式为 Python 对象列表。
    每个 record 以空行分隔，每行格式为 "... key value"。

    支持数字后缀数组（depotFile0, depotFile1...）→ 转为列表。
    """
    records = []
    current = {}
    arrays: dict[str, list] = {}

    for line in output.splitlines():
        line = line.strip()
        if not line:
            if current or arrays:
                # 合并数组字段
                for key, values in arrays.items():
                    current[key] = values
                records.append(current)
                current = {}
                arrays = {}
            continue

        m = re.match(r'^\.\.\. (\S+)\s*(.*)', line)
        if m:
            key, value = m.group(1), m.group(2)
            # 检测数字后缀（depotFile0 → depotFile 数组）
            arr_m = re.match(r'^(.+?)(\d+)$', key)
            if arr_m:
                base, idx = arr_m.group(1), int(arr_m.group(2))
                if base not in arrays:
                    arrays[base] = []
                # 确保列表足够长
                while len(arrays[base]) <= idx:
                    arrays[base].append(None)
                arrays[base][idx] = value
            else:
                current[key] = value

    if current or arrays:
        for key, values in arrays.items():
            current[key] = values
        records.append(current)

    return records

# ─── 核心 P4Client 类 ────────────────────────────────────────────

class P4Client:
    def __init__(
        self,
        port: str,
        user: str,
        password: Optional[str] = None,
        client: Optional[str] = None,
        max_retries: int = 3,
    ):
        self.port = port
        self.user = user
        self.password = password
        self.client = client
        self.max_retries = max_retries

    def _build_env(self, workspace: Optional[str] = None) -> dict:
        import os
        env = os.environ.copy()
        env["P4PORT"] = self.port
        env["P4USER"] = self.user
        if self.password:
            env["P4PASSWD"] = self.password
        ws = workspace or self.client
        if ws:
            env["P4CLIENT"] = ws
        return env

    def run(
        self,
        args: list[str],
        workspace: Optional[str] = None,
        use_ztag: bool = True,
        input_data: Optional[str] = None,
        retries: Optional[int] = None,
    ) -> list[dict] | str:
        """
        执行 p4 命令。默认使用 -ztag 格式并解析为对象列表。
        use_ztag=False 时返回原始字符串输出。
        """
        if retries is None:
            retries = self.max_retries

        cmd = ["p4"]
        if use_ztag:
            cmd.append("-ztag")
        cmd.extend(args)

        env = self._build_env(workspace)

        for attempt in range(retries):
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    env=env,
                    input=input_data,
                    timeout=120,
                )
                stdout = result.stdout
                stderr = result.stderr

                # 检查集成失败（不重试）
                for pattern, kind in INTEGRATION_FAILURE_PATTERNS:
                    if pattern.search(stderr) or pattern.search(stdout):
                        raise P4IntegrationFailure(stderr or stdout, kind)

                # 检查瞬时错误（重试）
                for retry_msg in RETRY_ERRORS:
                    if retry_msg in stderr:
                        raise P4TransientError(stderr)

                # 普通错误
                if result.returncode != 0 and stderr.strip():
                    # 某些 p4 命令在成功时也会有 returncode != 0（如 resolve 有冲突）
                    # 这里不直接抛出，让调用者判断
                    pass

                if use_ztag:
                    return parse_ztag(stdout)
                return stdout

            except P4TransientError:
                if attempt < retries - 1:
                    wait = 2 ** attempt
                    logger.warning(f"P4 transient error, retrying in {wait}s (attempt {attempt+1})")
                    time.sleep(wait)
                    continue
                raise
            except subprocess.TimeoutExpired:
                raise P4Error(f"P4 command timed out: {' '.join(cmd)}")

    # ─── 高级方法 ────────────────────────────────────────────────

    def get_latest_change(self, depot_path: str) -> Optional[int]:
        """获取指定路径的最新 CL 号"""
        results = self.run(["changes", "-m", "1", depot_path])
        if results:
            return int(results[0].get("change", 0))
        return None

    def get_changes_since(self, depot_path: str, since_cl: int) -> list[dict]:
        """获取 since_cl 之后的所有变更（不含 since_cl）"""
        path_range = f"{depot_path}@{since_cl+1},now"
        results = self.run(["changes", "-l", path_range])
        # 按 CL 升序排列
        return sorted(results, key=lambda r: int(r.get("change", 0)))

    def describe(self, cl: int, include_shelved: bool = True) -> Optional[dict]:
        """获取变更详情（含文件列表）"""
        args = ["describe", "-s"]
        if include_shelved:
            args.append("-S")
        args.append(f"@{cl}")
        results = self.run(args)
        return results[0] if results else None

    def integrate(
        self,
        source_path: str,
        target_path: str,
        cl: int,
        workspace: str,
        branchspec: Optional[str] = None,
        pending_cl: Optional[int] = None,
    ) -> list[dict]:
        """执行 p4 integrate"""
        args = ["integrate"]
        if branchspec:
            args.extend(["-b", branchspec])
            args.extend(["-c", f"@{cl}"])
            args.extend(["-S", "-P"])
        else:
            args.extend([f"{source_path}@{cl},{cl}", target_path])
            if pending_cl:
                args.extend(["-c", str(pending_cl)])
        return self.run(args, workspace=workspace)

    def resolve_check(self, workspace: str) -> list[dict]:
        """p4 resolve -N —— 检查未解决冲突（不实际解决）"""
        # resolve -N 在有冲突时返回非零，但输出在 stdout
        cmd = ["p4", "-ztag", "resolve", "-N"]
        env = self._build_env(workspace)
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        return parse_ztag(result.stdout + result.stderr)

    def resolve_auto_merge(self, workspace: str) -> str:
        """p4 resolve -am —— 自动文本合并"""
        return self.run(["resolve", "-am"], workspace=workspace, use_ztag=False)

    def resolve_accept_target(self, workspace: str) -> str:
        """p4 resolve -ay —— 接受目标版本（用于 Stomp）"""
        return self.run(["resolve", "-ay"], workspace=workspace, use_ztag=False)

    def submit(self, workspace: str, cl: int) -> int:
        """提交 changelist，返回提交后的 CL 号"""
        result = self.run(["submit", "-c", str(cl)], workspace=workspace, use_ztag=False)
        # 解析 "Change NNNN submitted." 或 "Change NNNN renamed change MMMM and submitted."
        m = re.search(r"Change (\d+) (?:renamed change (\d+) and )?submitted", result)
        if m:
            return int(m.group(2) or m.group(1))
        raise P4Error(f"Submit did not return a CL number: {result}")

    def shelve(self, workspace: str, cl: int):
        """搁置 changelist"""
        self.run(["shelve", "-c", str(cl)], workspace=workspace, use_ztag=False)

    def revert(self, workspace: str, path: str = "//..."):
        """还原工作区修改"""
        self.run(["revert", path], workspace=workspace, use_ztag=False)

    def sync(self, workspace: str, path: str, revision: str = ""):
        """同步文件"""
        target = f"{path}{revision}" if revision else path
        self.run(["sync", "-f", target], workspace=workspace, use_ztag=False)

    def create_changelist(self, workspace: str, description: str) -> int:
        """创建新的 pending changelist"""
        spec = f"""Change:\tnew
Client:\t{workspace}
Status:\tnew
Description:
\t{description.replace(chr(10), chr(10) + chr(9))}
"""
        result = self.run(["change", "-i"], workspace=workspace,
                          use_ztag=False, input_data=spec)
        m = re.search(r"Change (\d+) created", result)
        if m:
            return int(m.group(1))
        raise P4Error(f"Failed to create changelist: {result}")

    def create_workspace(self, spec: dict):
        """创建或更新工作区"""
        spec_text = self._format_client_spec(spec)
        self.run(["client", "-i"], use_ztag=False, input_data=spec_text)

    def fstat(self, workspace: str, path: str) -> list[dict]:
        """获取文件状态"""
        return self.run(["fstat", "-Ro", path], workspace=workspace)

    def filelog(self, depot_path: str, max_revisions: int = 100) -> list[dict]:
        """获取文件历史"""
        return self.run(["filelog", "-m", str(max_revisions), depot_path])

    def clean_workspace(self, workspace: str, root_path: str = "//..."):
        """清理工作区：revert → 删除所有 shelved → sync #0（优化版）

        RoboMerge 原版在每个 CL integrate 前都无条件调用 sync #0。
        因为其 workspace 从不真正 sync 文件，代价可接受。
        Python 复刻若 workspace 可能存有文件，应先用 p4 have 检查，
        仅在 workspace 非空时才执行 sync @0，并分批处理避免命令行过长。
        """
        # 1. 还原所有 pending
        self.revert(workspace, root_path)

        # 2. 获取并删除所有 pending changelists
        pending = self.run(["changes", "-s", "pending", "-c", workspace])
        for record in pending:
            cl = int(record.get("change", 0))
            if cl:
                try:
                    self.run(["shelve", "-d", "-c", str(cl)], workspace=workspace, use_ztag=False)
                except Exception:
                    pass
                try:
                    self.run(["change", "-d", str(cl)], workspace=workspace, use_ztag=False)
                except Exception:
                    pass

        # 3. 优化版 sync @0：先用 p4 have 检查，workspace 已空则跳过
        _SYNC_BATCH_SIZE = 500
        try:
            have_results = self.run(["have", root_path], workspace=workspace)
            depot_paths = [
                r["depotFile"]
                for r in (have_results or [])
                if isinstance(r, dict) and "depotFile" in r
            ]
            if not depot_paths:
                logger.info("[clean_workspace] workspace already empty, skip sync @0")
                return
            # 分批 sync @0，避免单次命令参数过长
            for i in range(0, len(depot_paths), _SYNC_BATCH_SIZE):
                batch = [f"{p}@0" for p in depot_paths[i:i + _SYNC_BATCH_SIZE]]
                self.run(["sync"] + batch, workspace=workspace, use_ztag=False)
            logger.info("[clean_workspace] sync @0 done, %d files removed", len(depot_paths))
        except Exception as e:
            logger.warning("[clean_workspace] sync @0 warning: %s", e)

    def _format_client_spec(self, spec: dict) -> str:
        """将 dict 格式化为 P4 client spec 文本"""
        lines = []
        for key in ["Client", "Owner", "Root", "Options", "SubmitOptions", "LineEnd"]:
            if key in spec:
                lines.append(f"{key}:\t{spec[key]}")
        if "View" in spec:
            lines.append("View:")
            for mapping in spec["View"]:
                lines.append(f"\t{mapping}")
        return "\n".join(lines) + "\n"
```

---

## P1：`description_parser.py` — 描述解析

```python
import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional

class MergeMode(Enum):
    NORMAL = "normal"
    NULL = "null"
    SKIP = "skip"
    MANUAL = "manual"

@dataclass
class MergeAction:
    branch: str
    mode: MergeMode
    flags: set = None

    def __post_init__(self):
        if self.flags is None:
            self.flags = set()

@dataclass
class ParseResult:
    targets: list[MergeAction]
    flags: set[str]          # 全局标志：'manual', 'null', 'ignore'
    owner: Optional[str]     # #robomerge-author 标签指定的 owner
    errors: list[str]

GLOBAL_IGNORE_FLAGS = {'ignore', 'deadend'}
GLOBAL_MANUAL_FLAGS = {'manual', 'nosubmit', 'stage'}
GLOBAL_NULL_FLAGS = {'null'}

def parse_description(
    description: str,
    bot_name: str,
    branch_aliases: dict[str, str],   # alias → canonical branch name
    macros: dict[str, list[str]],     # macro_name → [branch1, branch2]
    all_branch_names: set[str],       # 所有已知分支名（大写）
    is_default_bot: bool = False,
) -> ParseResult:
    """
    解析提交描述中的 #robomerge 命令。

    branch_aliases: {'main': 'Main', '5.0': 'Release-5.0', ...}
    macros: {'allrelease': ['Release-5.0', 'Release-5.1']}
    """
    targets: list[MergeAction] = []
    global_flags: set[str] = set()
    owner: Optional[str] = None
    errors: list[str] = []
    found_command = False

    ROBOMERGE_PATTERN = re.compile(
        r'#robomerge(?:\[([^\]]+)\])?(.*)',
        re.IGNORECASE
    )
    OWNER_PATTERN = re.compile(r'#robomerge-author\s+(\S+)', re.IGNORECASE)

    def resolve_branch(name: str) -> Optional[str]:
        """将别名或分支名解析为规范分支名"""
        # 尝试直接匹配（大小写不敏感）
        upper = name.upper()
        if upper in {b.upper() for b in all_branch_names}:
            for b in all_branch_names:
                if b.upper() == upper:
                    return b
        # 尝试别名
        lower = name.lower()
        if lower in branch_aliases:
            return branch_aliases[lower]
        return None

    for line in description.split('\n'):
        line = line.strip()

        # 检查 owner 标签
        owner_m = OWNER_PATTERN.search(line)
        if owner_m:
            owner = owner_m.group(1)

        # 检查 #robomerge 命令
        m = ROBOMERGE_PATTERN.search(line)
        if not m:
            continue

        # 检查 bot 名匹配
        specified_bot = m.group(1)
        if specified_bot:
            if specified_bot.upper() != bot_name.upper():
                continue
        else:
            if not is_default_bot:
                continue

        found_command = True
        tokens = m.group(2).split() if m.group(2) else []

        for token in tokens:
            token_lower = token.lower().lstrip('#')

            # 全局忽略标志
            if token_lower in GLOBAL_IGNORE_FLAGS:
                return ParseResult([], {'ignore'}, owner, errors)

            # 全局 manual 标志
            if token_lower in GLOBAL_MANUAL_FLAGS:
                global_flags.add('manual')
                continue

            # 全局 null 标志
            if token_lower in GLOBAL_NULL_FLAGS:
                global_flags.add('null')
                continue

            # 跳过特定目标（-BranchName）
            if token.startswith('-') and len(token) > 1:
                branch = resolve_branch(token[1:])
                if branch:
                    targets.append(MergeAction(branch, MergeMode.SKIP))
                else:
                    errors.append(f"Unknown branch in skip: {token[1:]}")
                continue

            # Null merge 特定目标（!BranchName）
            if token.startswith('!') and len(token) > 1:
                branch = resolve_branch(token[1:])
                if branch:
                    targets.append(MergeAction(branch, MergeMode.NULL))
                else:
                    errors.append(f"Unknown branch in null: {token[1:]}")
                continue

            # 宏（#macroname）
            if token.startswith('#') and len(token) > 1:
                macro_name = token[1:].lower()
                if macro_name in macros:
                    for b in macros[macro_name]:
                        targets.append(MergeAction(b, MergeMode.NORMAL))
                else:
                    errors.append(f"Unknown macro: {token}")
                continue

            # 普通目标
            branch = resolve_branch(token)
            if branch:
                targets.append(MergeAction(branch, MergeMode.NORMAL))
            else:
                errors.append(f"Unknown branch: {token}")

    # 应用全局 null 标志到所有 NORMAL 目标
    if 'null' in global_flags:
        targets = [
            MergeAction(t.branch, MergeMode.NULL if t.mode == MergeMode.NORMAL else t.mode, t.flags)
            for t in targets
        ]

    # 应用全局 manual 标志
    if 'manual' in global_flags:
        for t in targets:
            t.flags.add('manual')

    return ParseResult(targets, global_flags, owner, errors)
```

---

## P1：`state_store.py` — 状态持久化

```python
import json
import os
import threading
from pathlib import Path
from typing import Any, Optional

class StateStore:
    """
    简单的 JSON 文件持久化存储。
    线程安全（使用 Lock）。
    """
    def __init__(self, data_dir: str, bot_name: str):
        self.path = Path(data_dir) / f"{bot_name}.state.json"
        self._lock = threading.Lock()
        self._data: dict = {}
        self._load()

    def _load(self):
        if self.path.exists():
            try:
                with open(self.path, 'r') as f:
                    self._data = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._data = {}

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, 'w') as f:
            json.dump(self._data, f, indent=2, default=str)

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._data.get(key, default)

    def set(self, key: str, value: Any):
        with self._lock:
            self._data[key] = value
            self._save()

    def get_int(self, key: str, default: int = 0) -> int:
        val = self.get(key, default)
        return int(val) if val is not None else default

    def get_sub(self, *keys: str) -> 'SubStateStore':
        return SubStateStore(self, list(keys))


class SubStateStore:
    """嵌套路径的状态访问器（如 node.edge 的状态）"""
    def __init__(self, root: StateStore, path: list[str]):
        self._root = root
        self._path = path

    def _get_nested(self, data: dict, keys: list) -> dict:
        for key in keys:
            data = data.setdefault(key, {})
        return data

    def get(self, key: str, default: Any = None) -> Any:
        with self._root._lock:
            node = self._get_nested(self._root._data, self._path)
            return node.get(key, default)

    def set(self, key: str, value: Any):
        with self._root._lock:
            node = self._get_nested(self._root._data, self._path)
            node[key] = value
            self._root._save()
```

---

## P2：`node_bot.py` — 分支监控

```python
import threading
import time
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

@dataclass
class NodeBotConfig:
    name: str
    depot_path: str           # 如 "//UE5/Main/..."
    flows_to: list[str]       # 目标分支名列表
    exclude_authors: list[str] = field(default_factory=list)
    exclude_descriptions: list[str] = field(default_factory=list)
    resolver: Optional[str] = None
    check_interval_secs: int = 30

class NodeBot:
    def __init__(
        self,
        config: NodeBotConfig,
        p4: 'P4Client',
        state: 'StateStore',
        edge_bots: dict[str, 'EdgeBot'],
        parser_config: dict,   # branch_aliases, macros, etc.
        notifier: Optional['Notifier'] = None,
    ):
        self.config = config
        self.p4 = p4
        self.state = state
        self.edge_bots = edge_bots  # target_branch_name → EdgeBot
        self.parser_config = parser_config
        self.notifier = notifier

        self.last_cl: int = state.get_int('lastCl', 0)
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self):
        """启动监控线程"""
        # 如果 lastCL 为 0（新 bot），初始化为当前最新 CL
        if self.last_cl == 0:
            latest = self.p4.get_latest_change(self.config.depot_path)
            if latest:
                self.last_cl = latest
                self.state.set('lastCl', self.last_cl)
                logger.info(f"[{self.config.name}] New bot, starting from CL {self.last_cl}")

        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=60)

    def _run_loop(self):
        while not self._stop_event.is_set():
            try:
                self.tick()
            except Exception as e:
                logger.exception(f"[{self.config.name}] tick() error: {e}")
            self._stop_event.wait(timeout=self.config.check_interval_secs)

    def tick(self):
        """单次轮询：查询新变更并处理"""
        changes = self.p4.get_changes_since(self.config.depot_path, self.last_cl)

        for change_record in changes:
            cl = int(change_record.get("change", 0))
            if cl <= self.last_cl:
                continue

            try:
                self._process_change(cl)
                self.last_cl = cl
                self.state.set('lastCl', self.last_cl)
            except Exception as e:
                logger.exception(f"[{self.config.name}] Error processing CL {cl}: {e}")
                # 不推进 lastCL，下次重试
                break

    def _process_change(self, cl: int):
        """处理单个变更"""
        # 1. 获取变更详情
        detail = self.p4.describe(cl)
        if not detail:
            logger.warning(f"[{self.config.name}] CL {cl} not found")
            return

        author = detail.get("user", "")
        description = detail.get("desc", "")

        # 2. 检查排除规则
        if author in self.config.exclude_authors:
            logger.info(f"[{self.config.name}] Skipping CL {cl}: excluded author {author}")
            return

        for pattern in self.config.exclude_descriptions:
            if re.search(pattern, description):
                logger.info(f"[{self.config.name}] Skipping CL {cl}: excluded description")
                return

        # 3. 解析 #robomerge 命令
        parse_result = parse_description(
            description=description,
            bot_name=self.parser_config["bot_name"],
            branch_aliases=self.parser_config["aliases"],
            macros=self.parser_config["macros"],
            all_branch_names=set(self.edge_bots.keys()),
            is_default_bot=self.parser_config["is_default_bot"],
        )

        if 'ignore' in parse_result.flags:
            logger.info(f"[{self.config.name}] CL {cl}: ignore flag set")
            return

        # 4. 计算最终目标（flowsTo + 显式命令）
        final_targets = self._compute_targets(parse_result)

        # 5. 对每个目标执行合并
        for action in final_targets:
            edge = self.edge_bots.get(action.branch)
            if not edge:
                logger.warning(f"[{self.config.name}] No edge bot for {action.branch}")
                continue

            edge.process_change(cl, action, author, description)

    def _compute_targets(self, parse_result: 'ParseResult') -> list['MergeAction']:
        """
        合并 flowsTo 自动目标 + 显式 #robomerge 命令目标。
        显式 skip (-branch) 覆盖 flowsTo。
        """
        from description_parser import MergeAction, MergeMode

        explicit_by_branch = {a.branch: a for a in parse_result.targets}

        result = []
        # 添加 flowsTo 自动目标（除非被显式 skip）
        for branch in self.config.flows_to:
            if branch in explicit_by_branch:
                action = explicit_by_branch[branch]
                if action.mode != MergeMode.SKIP:
                    result.append(action)
            else:
                result.append(MergeAction(branch, MergeMode.NORMAL))

        # 添加不在 flowsTo 中的显式目标
        for branch, action in explicit_by_branch.items():
            if branch not in self.config.flows_to and action.mode != MergeMode.SKIP:
                result.append(action)

        return result
```

---

## P2：`edge_bot.py` — 合并执行（骨架）

```python
import logging
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

logger = logging.getLogger(__name__)

class EdgeBotStatus(Enum):
    IDLE = "idle"
    INTEGRATING = "integrating"
    BLOCKED = "blocked"

@dataclass
class IntegrationResult:
    success: bool
    submitted_cl: Optional[int] = None
    shelved_cl: Optional[int] = None
    error: Optional[str] = None
    kind: Optional[str] = None  # 'conflict', 'exclusive', 'split_move', etc.

class EdgeBot:
    def __init__(
        self,
        source_branch: str,
        target_branch: str,
        source_depot_path: str,
        target_depot_path: str,
        workspace_name: str,
        workspace_root: str,
        p4: 'P4Client',
        state: 'SubStateStore',
        conflict_manager: 'ConflictManager',
        notifier: Optional['Notifier'] = None,
        branchspec: Optional[str] = None,
        options: dict = None,
    ):
        self.source = source_branch
        self.target = target_branch
        self.source_path = source_depot_path
        self.target_path = target_depot_path
        self.workspace = workspace_name
        self.workspace_root = workspace_root
        self.p4 = p4
        self.state = state
        self.conflict_manager = conflict_manager
        self.notifier = notifier
        self.branchspec = branchspec
        self.options = options or {}

        self.last_cl: int = state.get_int('lastCl', 0)
        self._blockage_cl: Optional[int] = state.get('blockageCl')

    def is_blocked(self) -> bool:
        return self._blockage_cl is not None

    def process_change(
        self,
        cl: int,
        action: 'MergeAction',
        author: str,
        description: str,
    ):
        """处理单个变更的合并"""
        if self.is_blocked():
            logger.info(f"[{self.source}→{self.target}] Blocked on CL {self._blockage_cl}, queuing CL {cl}")
            # 可以将 cl 加入队列，等解除阻塞后处理
            return

        from description_parser import MergeMode

        if action.mode == MergeMode.SKIP:
            logger.info(f"[{self.source}→{self.target}] Skipping CL {cl}")
            self._update_last_cl(cl)
            return

        logger.info(f"[{self.source}→{self.target}] Integrating CL {cl} (mode={action.mode.value})")

        try:
            # 确保工作区存在
            self._ensure_workspace()

            # 清理工作区（对应 RoboMerge 的两层清理）：
            # - cleanWorkspace()：进程生命周期内仅首次执行（原版有全局 Map 保护）
            # - integrate 前 sync #0：每个 CL 都会执行
            # Python 版将两者合并为一次 clean_workspace()，通过 p4 have 优化空 workspace 检测
            self.p4.clean_workspace(self.workspace)

            # 执行集成
            result = self._do_integrate(cl, action, author, description)

            if result.success:
                self._update_last_cl(cl)
                logger.info(f"[{self.source}→{self.target}] CL {cl} → submitted as {result.submitted_cl}")
            elif result.shelved_cl:
                # Shelf 创建成功，等待人工解决
                self._set_blocked(cl)
                if self.notifier:
                    self.notifier.notify_shelf_created(self, cl, result.shelved_cl, author)
            else:
                # 创建 blockage
                self._set_blocked(cl)
                conflict = self.conflict_manager.create_conflict(
                    cl=cl,
                    source_branch=self.source,
                    target_branch=self.target,
                    author=author,
                    kind=result.kind or "Merge conflict",
                )
                if self.notifier:
                    self.notifier.notify_conflict(conflict)

        except Exception as e:
            logger.exception(f"[{self.source}→{self.target}] Integration failed for CL {cl}: {e}")
            self._set_blocked(cl)

    def _do_integrate(
        self,
        cl: int,
        action: 'MergeAction',
        author: str,
        description: str,
    ) -> IntegrationResult:
        from description_parser import MergeMode

        # 创建 pending changelist
        merge_description = self._build_description(cl, description)
        pending_cl = self.p4.create_changelist(self.workspace, merge_description)

        try:
            # 执行 p4 integrate
            if action.mode == MergeMode.NULL:
                self.p4.integrate(
                    self.source_path, self.target_path, cl,
                    self.workspace, self.branchspec, pending_cl
                )
                self.p4.resolve_accept_target(self.workspace)
            else:
                self.p4.integrate(
                    self.source_path, self.target_path, cl,
                    self.workspace, self.branchspec, pending_cl
                )
                # 尝试自动合并文本冲突
                self.p4.resolve_auto_merge(self.workspace)

            # 检查剩余冲突
            conflicts = self.p4.resolve_check(self.workspace)
            unresolved = [r for r in conflicts if r.get("resolveType")]

            if unresolved:
                # 有冲突
                if action.mode == MergeMode.MANUAL or 'manual' in action.flags:
                    # 创建 shelf
                    self.p4.shelve(self.workspace, pending_cl)
                    return IntegrationResult(success=False, shelved_cl=pending_cl)
                else:
                    return IntegrationResult(
                        success=False,
                        kind=self._classify_conflict(unresolved),
                    )

            # 提交
            if action.mode == MergeMode.MANUAL or 'manual' in action.flags:
                self.p4.shelve(self.workspace, pending_cl)
                return IntegrationResult(success=False, shelved_cl=pending_cl)

            submitted = self.p4.submit(self.workspace, pending_cl)
            return IntegrationResult(success=True, submitted_cl=submitted)

        except Exception:
            # 清理失败的 pending CL
            try:
                self.p4.revert(self.workspace)
            except Exception:
                pass
            raise

    def _classify_conflict(self, unresolved: list[dict]) -> str:
        """根据冲突文件分类冲突类型"""
        for f in unresolved:
            resolve_type = f.get("resolveType", "")
            if "exclusive" in resolve_type:
                return "Exclusive check-out"
        return "Merge conflict"

    def _build_description(self, source_cl: int, original_desc: str) -> str:
        return (
            f"[Merge CL #{source_cl} from {self.source} to {self.target}]\n\n"
            f"{original_desc.strip()}\n\n"
            f"#robomerge[{self.options.get('bot_name', 'ROBOMERGE')}] {self.target}\n"
            f"ROBOMERGE-SOURCE: {self.source}\n"
        )

    def _ensure_workspace(self):
        """确保合并工作区存在"""
        self.p4.create_workspace({
            "Client": self.workspace,
            "Owner": self.p4.user,
            "Root": self.workspace_root,
            "Options": "noallwrite noclobber nocompress unlocked nomodtime normdir",
            "SubmitOptions": "submitunchanged",
            "View": [
                f"{self.source_path.rstrip('.')} //{self.workspace}/from/...",
                f"{self.target_path.rstrip('.')} //{self.workspace}/to/...",
            ],
        })

    def _update_last_cl(self, cl: int):
        self.last_cl = cl
        self.state.set('lastCl', cl)

    def _set_blocked(self, cl: int):
        self._blockage_cl = cl
        self.state.set('blockageCl', cl)

    def unblock(self):
        self._blockage_cl = None
        self.state.set('blockageCl', None)
```

---

## 关键注意事项（TypeScript → Python 转换陷阱）

| 问题 | TypeScript 处理方式 | Python 建议 |
|------|-------------------|-------------|
| 异步并发 | async/await + Promise.all | asyncio 或 threading |
| 状态机 | 类成员变量 | dataclass + 文件持久化 |
| P4 ztag 数组字段 | 自定义解析 | 见 parse_ztag() 中的数字后缀处理 |
| Slack API | @slack/web-api | slack_sdk（Python） |
| 邮件发送 | nodemailer | smtplib / email |
| 文件锁 | exclusive file +l | p4 fstat 的 otherLock 字段 |
| CL 描述多行 | `\n` 拼接 | 注意 Windows `\r\n` 行尾处理 |
| 时区处理 | UTC Date 对象 | datetime.timezone.utc |
| 工作区命名 | 自动生成 | `robomerge-{bot}-{src}-{tgt}` |
| 重试逻辑 | Async retry | 同步指数退避（见 P4Client.run()） |

---

## 最小可用 Python 实现顺序

```
1. 实现 p4client.py → 测试基本 P4 操作
2. 实现 description_parser.py → 单元测试各种 #robomerge 命令
3. 实现 state_store.py → 测试持久化
4. 实现 edge_bot.py（简化版） → 测试单次集成
5. 实现 node_bot.py → 测试轮询
6. 集成测试：监控一个真实分支，执行一次合并
7. 添加 conflict_manager.py → 测试冲突持久化
8. 添加 notifier.py（Slack/Email）
9. 可选：api_server.py（FastAPI）提供 REST 接口
```
