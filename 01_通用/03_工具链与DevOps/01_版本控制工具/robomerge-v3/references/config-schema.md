# RoboMerge v3 配置 Schema 完整参考

> 源文件：`src/robo/branchdefs.ts`

---

## CLI 启动参数

```
node dist/robo/watchdog.js [OPTIONS]

必填：
  -botname=BOT1,BOT2      运行的 bot 名称（逗号分隔，对应 data/{name}.branchmap.json）

可选：
  -devMode                开发模式（不连接真实 P4）
  -previewOnly            预览模式（不执行实际合并）
  -externalUrl=https://.. Web UI 对外 URL（生成通知链接用）
  -branchSpecsRootPath    P4 中存储 branchspec 数据的路径
  -vault_path=/vault      密钥存储路径
  -noMail                 禁用 Email 通知
  -noTLS                  禁用 HTTPS
  -useSlackInDev          在 devMode 下也启用 Slack
  -port=3000              Web 服务端口（默认 3000）
  -watchdogPort=4433      Watchdog HTTP 端口（默认 4433）
```

---

## BotConfig（Bot 级，branchmap.json 根字段）

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `defaultStreamDepot` | string | **必填** | 该 bot 管理的默认流 depot 名称 |
| `isDefaultBot` | boolean | false | 是否处理没有指定 bot 名的 `#robomerge` 命令 |
| `checkIntervalSecs` | number | 30 | tick 轮询间隔（秒） |
| `yieldFrequency` | number | 10 | 每个 bot 每轮最多处理多少个集成后让步给其他 bot |
| `noStreamAliases` | boolean | false | 禁止在命令中使用流别名 |
| `slackChannel` | string | — | 阻塞通知发送的 Slack 频道（如 `#robomerge-alerts`） |
| `visibility` | string[] | [] | 可查看 Web UI 的用户组（如 `["fte"]`） |
| `globalNotify` | string[] | [] | 所有阻塞事件的额外邮件收件人 |
| `excludeAuthors` | string[] | [] | 跳过这些作者的变更（如 `["buildmachine"]`） |
| `excludeDescriptions` | string[] | [] | 描述匹配这些正则的变更将被跳过 |
| `emailOnBlockage` | boolean | true | 发生阻塞时发送邮件 |
| `nagWhenBlocked` | boolean | true | 阻塞持续时定期发提醒 |
| `nagSchedule` | object | — | nag 调度，如 `{"hour": 9, "tzOffset": -5}` |
| `reportToBuildHealth` | boolean | false | 将阻塞报告给 UGS Build Health |
| `aliases` | string[] | [] | Bot 的备用名称 |
| `macros` | object | {} | 自定义命令宏，如 `{"myalias": ["Main","Release-5.0"]}` |
| `badgeProject` | string | — | UGS badge 项目名 |
| `slackToken` | string | — | Slack API token（通常从 vault 读取） |

---

## NodeOptions（分支级，branches[] 数组元素）

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | string | **必填** | 分支名称（唯一标识符） |
| `aliases` | string[] | [] | 该分支的别名（用于 #robomerge 命令中） |
| `streamDepot` | string | defaultStreamDepot | 该分支所在 depot |
| `streamName` | string | — | 流名称（通常与 name 相同） |
| `rootPath` | string | — | 完整 depot 路径（如 `//UE5/Main/...`），与 stream 二选一 |
| `streamSubpath` | string | `/...` | 流内子路径 |
| `flowsTo` | string[] | [] | 自动合并目标分支列表 |
| `forceAll` | boolean | false | 强制所有变更流向 flowsTo（忽略 #robomerge 指令） |
| `blockAssetFlow` | string[] | [] | 阻止资产类变更流向这些目标 |
| `disallowDeadend` | boolean | false | 禁止对本分支使用 deadend 标记 |
| `initialCL` | number | — | 新 bot 的起始 CL 号（不设则从最新 CL 开始） |
| `resolver` | string | — | 指定负责解决冲突的用户（邮箱） |
| `enabled` | boolean | true | 是否启用该分支 |
| `forcePause` | boolean | false | 强制暂停该分支 |
| `integrationWindow` | object[] | — | 允许集成的时间窗口（见下方） |
| `badgeProject` | string | — | UGS badge 覆盖 |
| `streamServer` | string | — | 自定义 P4 服务器地址（如多服务器场景） |
| `edgeProperties` | object | {} | 针对特定目标的 EdgeOptions（键为目标分支名） |

### integrationWindow 格式

```json
"integrationWindow": [
  {
    "startHourUTC": 19,
    "durationHours": 10,
    "daysOfWeek": [1, 2, 3, 4, 5]
  }
]
```

- `startHourUTC`：UTC 时间的开始小时（0-23）
- `durationHours`：持续小时数
- `daysOfWeek`：可选，1=周一 … 7=周日；不填则每天

---

## EdgeOptions（边级，edgeProperties[targetName] 的值）

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `integrationMethod` | string | `"normal"` | `"normal"` 或 `"skip-if-unchanged"` |
| `branchspec` | string | — | 自定义 P4 branchspec 名称（替代默认流集成） |
| `lastGoodCLPath` | string | — | Gate 文件 P4 路径（含最后通过 CI 的 CL 号） |
| `pauseCISUnlessAtGate` | boolean | false | CIS 追赶时暂停 |
| `disallowSkip` | boolean | false | 禁用 Skip 选项（必须 stomp 或 shelf） |
| `disallowDeadend` | boolean | false | 禁止 deadend |
| `incognitoMode` | boolean | false | 合并提交描述使用简短格式（隐藏细节） |
| `emailOnBlockage` | boolean | true | 该 edge 阻塞时发送邮件（覆盖 bot 级设置） |
| `excludeAuthors` | string[] | [] | 该 edge 专用的作者排除列表 |
| `excludeDescriptions` | string[] | [] | 该 edge 专用的描述排除规则 |
| `resolver` | string | — | 覆盖 node 级的 resolver |
| `workspaceNameOverride` | string | — | 自定义工作区名称 |
| `integrationWindow` | object[] | — | 该 edge 专用的时间窗口（覆盖 node 级） |
| `invertIntegrationWindow` | boolean | false | 翻转时间窗口逻辑（窗口外才合并） |
| `approval` | object | — | Approval 工作流配置（见下方） |

### approval 对象格式

```json
"approval": {
  "description": "等待主管审批后才合并",
  "channelId": "C1234567890",
  "block": true
}
```

- `description`：Shelf/通知中显示的说明文字
- `channelId`：发送审批通知的 Slack 频道 ID
- `block`：是否阻塞该 edge 直到审批完成

---

## 完整 branchmap.json 示例

```json
{
  "defaultStreamDepot": "UE5",
  "isDefaultBot": true,
  "checkIntervalSecs": 30,
  "slackChannel": "#robomerge-alerts",
  "globalNotify": ["lead@example.com"],
  "excludeAuthors": ["buildmachine", "p4-service"],
  "macros": {
    "allrelease": ["Release-5.0", "Release-5.1"]
  },
  "branches": [
    {
      "name": "Main",
      "streamDepot": "UE5",
      "streamName": "Main",
      "aliases": ["main", "trunk"],
      "flowsTo": ["Release-5.1"],
      "resolver": "tech-lead@example.com",
      "edgeProperties": {
        "Release-5.1": {
          "lastGoodCLPath": "//UE5/Main/Engine/Build/LastGoodCL.txt",
          "pauseCISUnlessAtGate": true,
          "integrationWindow": [
            {"startHourUTC": 18, "durationHours": 12}
          ]
        }
      }
    },
    {
      "name": "Release-5.1",
      "streamDepot": "UE5",
      "streamName": "Release-5.1",
      "aliases": ["5.1"],
      "flowsTo": ["Release-5.0"],
      "blockAssetFlow": ["Release-5.0"]
    },
    {
      "name": "Release-5.0",
      "streamDepot": "UE5",
      "streamName": "Release-5.0",
      "aliases": ["5.0"]
    }
  ],
  "branchspecs": [
    {
      "name": "ROBO:Main->Release-5.0",
      "from": "Main",
      "to": "Release-5.0"
    }
  ]
}
```

---

## 持久化数据结构

Bot 状态保存在 `./data/{BOTNAME}/` 目录下，格式为 JSON。

### NodeBot 持久化字段

```json
{
  "lastCl": 12345678,
  "queuedCls": [
    {"changeCl": 12345679, "request": null}
  ],
  "edgesQueuedToUnblock": ["RELEASE-5.0"],
  "conflicts": [...]
}
```

### PersistentConflict 结构

```typescript
{
  cl: number                        // 导致冲突的合并 CL
  sourceCl: number                  // 原始变更 CL
  blockedBranchName: string         // 源分支（大写），如 "MAIN"
  targetBranchName: string          // 目标分支（大写），如 "RELEASE-5.0"
  author: string                    // 原始变更作者（邮箱）
  owner: string                     // 当前负责解决的人（邮箱）
  kind: FailureKind                 // 'Merge conflict' | 'Exclusive check-out' | 'Commit failure' | ...
  time: Date                        // 冲突发现时间
  nagCount: number                  // 已发送提醒次数
  lastNagTime?: Date
  resolution?: 'resolved' | 'skipped' | 'cancelled'
  resolvingAuthor?: string
  timeTakenToResolveSeconds?: number
  acknowledger?: string
  acknowledgedAt?: Date
  ugsIssue?: number                 // UGS Build Health issue 编号
}
```
