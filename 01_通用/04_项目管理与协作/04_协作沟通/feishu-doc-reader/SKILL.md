---
name: feishu-doc-reader
title: 飞书文档读取与流程图解析
description: |
  通过飞书开放平台 API（tenant_access_token）读取飞书 Wiki 文档正文及内嵌流程图（画板/Board）的完整工作流。
  当用户提到飞书文档、飞书 wiki、飞书链接、想要读取/理解/总结飞书文档内容、或文档 URL 包含 feishu.cn/wiki/ 时，必须使用此 skill。
  即使用户只说"帮我看看这个飞书文档"、"这个 wiki 写的什么"、"读一下飞书链接里的流程图"，也应使用此 skill。
tags: [Feishu, Wiki, Document, Flowchart, API, Automation]
---

# 飞书文档读取与流程图解析 Skill

## 概述

飞书 Wiki 文档不能直接爬取，必须通过飞书开放平台 API 访问。本 skill 覆盖：

1. **申请凭证** — 向用户索取 App ID 和 App Secret（不保存、不记忆）
2. **获取 Token** — 用凭证换取 `tenant_access_token`
3. **读取文档元信息** — 从 wiki URL 提取 node token，查询文档标题和 obj_token
4. **读取文档正文** — 获取纯文本内容
5. **解析流程图** — 找出所有 Board 块，读取节点和连线，重建逻辑关系

---

## Step 0：申请凭证

**不要使用任何已保存或记忆中的凭证。** 每次都向用户索取：

> 请提供你的飞书 CLIBot 凭证：
> - **App ID**（格式：`cli_xxxxxxxxxxxxxxxx`）
> - **App Secret**（32位字符串）

凭证仅在当前会话中使用，不写入任何文件或记忆系统。

---

## Step 1：获取 tenant_access_token

```bash
curl -s -X POST "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal" \
  -H "Content-Type: application/json" \
  -d '{"app_id":"<APP_ID>","app_secret":"<APP_SECRET>"}'
```

成功响应：
```json
{"code":0,"expire":7200,"msg":"ok","tenant_access_token":"t-xxxxxxxx"}
```

token 有效期 2 小时，单次会话内无需重新获取。

**常见失败原因：**
- `code: 10003` — App ID 或 Secret 错误
- `code: 10013` — 应用未启用或已被禁用

---

## Step 2：从 Wiki URL 提取 node_token

Wiki URL 格式：`https://<tenant>.feishu.cn/wiki/<node_token>`

例：`https://cyancook.feishu.cn/wiki/LSxYw1NddiQgg4kvRVacMEbGnlg`
→ node_token = `LSxYw1NddiQgg4kvRVacMEbGnlg`

查询节点元信息（获取文档标题和 obj_token）：

```bash
curl -s -X GET "https://open.feishu.cn/open-apis/wiki/v2/spaces/get_node?token=<NODE_TOKEN>" \
  -H "Authorization: Bearer <TOKEN>"
```

响应中的关键字段：
- `data.node.title` — 文档标题
- `data.node.obj_token` — 文档内容 token（用于后续步骤）
- `data.node.obj_type` — 通常为 `docx`

**权限问题（code: 131003）：**
应用没有访问该知识库的权限。需要文档所有者在知识库设置中将机器人加为成员，或将文档设为"组织内获得链接可查看"。

---

## Step 3：读取文档正文

```bash
curl -s "https://open.feishu.cn/open-apis/docx/v1/documents/<OBJ_TOKEN>/raw_content" \
  -H "Authorization: Bearer <TOKEN>"
```

返回纯文本，适合快速了解文档大意。

---

## Step 4：获取文档块结构（含流程图定位）

```bash
curl -s "https://open.feishu.cn/open-apis/docx/v1/documents/<OBJ_TOKEN>/blocks?page_size=500" \
  -H "Authorization: Bearer <TOKEN>"
```

重点关注 `block_type: 43` 的块，这是飞书画板（Board）即流程图：

```json
{"block_id": "...", "block_type": 43, "board": {"token": "<BOARD_TOKEN>"}, ...}
```

记录所有 board token 及其在文档中的位置（前后标题块可判断它属于哪个章节）。

---

## Step 5：解析流程图内容

对每个 board_token 调用画板节点 API：

```bash
curl -s "https://open.feishu.cn/open-apis/board/v1/whiteboards/<BOARD_TOKEN>/nodes" \
  -H "Authorization: Bearer <TOKEN>"
```

用管道直接解析，避免临时文件路径问题（Windows 环境下 `/tmp` 可能不可用）：

```bash
curl -s "https://open.feishu.cn/open-apis/board/v1/whiteboards/<BOARD_TOKEN>/nodes" \
  -H "Authorization: Bearer <TOKEN>" | python3 -c "
import json, sys
data = json.load(sys.stdin)
nodes = data.get('data', {}).get('nodes', [])
texts = {}
connectors = []
for n in nodes:
    t = n.get('type', '')
    if t == 'connector':
        s = n.get('connector', {}).get('start_object', {}).get('id', '')
        e = n.get('connector', {}).get('end_object', {}).get('id', '')
        connectors.append((s, e))
    elif 'text' in n:
        texts[n['id']] = n['text'].get('text', '').strip()
print('节点:')
for nid, v in texts.items():
    if v: print('  [' + nid + '] ' + v)
print('连线:')
for s, e in connectors:
    sname = texts.get(s, s)
    ename = texts.get(e, e)
    print('  ' + sname + ' --> ' + ename)
"
```

### 节点类型说明

| type | 含义 |
|------|------|
| `composite_shape` | 流程图方框（有 `text` 字段） |
| `text_shape` | 独立文本标注（有 `text` 字段） |
| `connector` | 连线箭头（有 `connector.start_object.id` 和 `end_object.id`） |

### 重建逻辑关系

1. 建立 `id → 文本内容` 的映射（过滤空文本和连线节点）
2. 将连线的 start/end id 替换为对应文本
3. 结合节点的 x 坐标（从左到右）和 y 坐标（从上到下）辅助判断层级关系
4. 根据前后章节标题确定该流程图的语义背景

### 注意事项

- 部分节点的 `text` 字段包含 `[mentionUser]xxx(enName:xxx)` 格式，是飞书 @提及，代表人名
- 有 `line_through: true` 的文本节点表示该内容已被划掉（废弃/过时）
- 连线可能有 `caption` 字段，表示连线上的标签文字（条件分支等）

---

## 输出格式

解析完成后，用自然语言总结流程图逻辑，格式参考：

```
## [章节名] 流程图总结

**数据流：**
A → B → C → D

**各步骤说明：**
- A：...（来源于节点文本或标注文字）
- B：...
- C：...

**注意事项：**
- 已废弃的步骤（划线文本）：...
- 需人工介入的步骤：...
```

---

## 快速参考：API 端点汇总

| 用途 | 方法 | URL |
|------|------|-----|
| 获取 token | POST | `https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal` |
| Wiki 节点信息 | GET | `https://open.feishu.cn/open-apis/wiki/v2/spaces/get_node?token=<node_token>` |
| 文档纯文本 | GET | `https://open.feishu.cn/open-apis/docx/v1/documents/<obj_token>/raw_content` |
| 文档块结构 | GET | `https://open.feishu.cn/open-apis/docx/v1/documents/<obj_token>/blocks?page_size=500` |
| 画板节点 | GET | `https://open.feishu.cn/open-apis/board/v1/whiteboards/<board_token>/nodes` |

所有请求均需 Header：`Authorization: Bearer <tenant_access_token>`
