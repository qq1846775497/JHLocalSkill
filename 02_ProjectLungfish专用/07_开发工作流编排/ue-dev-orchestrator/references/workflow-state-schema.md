# 工作流状态文件 JSON Schema

## 文件位置
`.workflow/{task_id}_state.json`

## Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["task_id", "workflow_type", "current_step", "status"],
  "properties": {
    "task_id": {
      "type": "string",
      "description": "任务唯一标识，格式：{workflow-type}-{YYYYMMDD}-{HHMMSS}"
    },
    "workflow_type": {
      "type": "string",
      "enum": ["cpp", "blueprint", "config", "asset", "debug"],
      "description": "任务类型"
    },
    "current_step": {
      "type": "integer",
      "minimum": 1,
      "maximum": 9,
      "description": "当前执行到的步骤编号"
    },
    "status": {
      "type": "string",
      "enum": [
        "idle", "reconnaissance", "checkout", "loading_context",
        "modifying", "reviewing", "compiling", "fixing_compile",
        "testing", "fixing_pie", "regression_check", "submitting",
        "completed", "blocked"
      ],
      "description": "当前状态机状态"
    },
    "completed_steps": {
      "type": "array",
      "items": { "type": "integer", "minimum": 1, "maximum": 9 },
      "description": "已完成的步骤列表"
    },
    "pending_steps": {
      "type": "array",
      "items": { "type": "integer", "minimum": 1, "maximum": 9 },
      "description": "待执行的步骤列表"
    },
    "checked_out_files": {
      "type": "array",
      "items": { "type": "string" },
      "description": "已 P4 checkout 的文件路径列表"
    },
    "retry_counts": {
      "type": "object",
      "properties": {
        "compile": { "type": "integer", "minimum": 0, "description": "编译重试次数" },
        "pie": { "type": "integer", "minimum": 0, "description": "PIE 验证重试次数" }
      }
    },
    "user_confirmations": {
      "type": "object",
      "description": "每个步骤的用户确认状态",
      "additionalProperties": {
        "type": "string",
        "enum": ["pending", "approved", "rejected", "skipped"]
      }
    },
    "blockers": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "step": { "type": "integer" },
          "reason": { "type": "string" },
          "timestamp": { "type": "string", "format": "date-time" }
        }
      },
      "description": "阻塞原因列表"
    },
    "modifications_summary": {
      "type": "string",
      "description": "修改内容的文字摘要"
    },
    "cl_number": {
      "type": "string",
      "description": "最终提交的 changelist 编号（完成后填写）"
    }
  }
}
```

## 状态转移图

```
idle ──→ reconnaissance ──→ checkout ──→ loading_context ──→ modifying
                                                              │
                                                              ▼
reviewing ──→ compiling ──→ { fixing_compile ──→ compiling } ─┘
                │
                ▼
              testing ──→ { fixing_pie ──→ testing }
                │
                ▼
        regression_check ──→ submitting ──→ completed

任何状态 ──→ blocked（Hard Gate 触发）
blocked ──→ 任意状态（用户解除阻塞后）
```

## 示例

```json
{
  "task_id": "cpp-20260421-143052",
  "workflow_type": "cpp",
  "current_step": 6,
  "status": "compiling",
  "completed_steps": [1, 2, 3, 4, 5],
  "pending_steps": [6, 7, 8, 9],
  "checked_out_files": [
    "Source/ProjectLungfish/Gameplay/Character/PLCharacter.cpp",
    "Source/ProjectLungfish/Gameplay/Character/PLCharacter.h"
  ],
  "retry_counts": {
    "compile": 0,
    "pie": 0
  },
  "user_confirmations": {
    "step1": "approved",
    "step4": "approved"
  },
  "blockers": [],
  "modifications_summary": "Add Sprint Ability to PLCharacter with Enhanced Input binding and GAS integration"
}
```
