---
name: engine-modifications
title: 引擎源码
description: Custom modifications to Unreal Engine 5 for ProjectLungfish, including bug fixes, performance optimizations, and project-specific features. Coordinated with team before applying changes.
tags: [Engine, UE5, Bug-Fixes, Performance, Custom-Features, Engine-Modification]
---

# Unreal Engine 5 Modifications

> Layer: Tier 2 (Domain Overview)
> Parent: [ProjectLungfish](../SKILL.md)

<memory category="core-rules">
- Always use @CYANCOOK comment blocks for engine modifications
- Full spec and patterns: `.claude/rules/cyancook-annotation.md`
</memory>

## @CYANCOOK 块规范

完整 Pattern 1/2/3 示例及适用范围见 `.claude/rules/cyancook-annotation.md`。

## P4 检出

```bash
p4 edit "Engine/Source/Runtime/Engine/Classes/Engine/DataTable.h"
p4 reopen -c [CL_NUM] "Engine/Source/Runtime/Engine/Classes/Engine/DataTable.h"
```
