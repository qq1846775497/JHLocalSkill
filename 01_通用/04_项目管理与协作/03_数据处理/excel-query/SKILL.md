---
name: excel-query
title: Excel 数据表查询
description: 根据文件名、查询条件（如 Entity 名称）和目标列名，用 Python + openpyxl 读取 Main/RawData/ 下的 .xlsx 文件，返回匹配行的指定字段值。当用户需要查 Excel、查表、读表，或查询特定 Entity 的某个字段时使用此 skill。
tags: [DataTables, Data-Driven, Python, Content-Pipeline, Assets]
---

# Excel 数据表查询

> Layer: Tier 3 (Workflow Skill)

## System Overview

根据用户提供的 Excel 文件名、查询条件（如 Entity 名称）和目标列名，用 Python 读取 `Main/RawData/` 下的 `.xlsx` 文件，返回匹配行的指定字段值。

**触发场景：**
- 查 Excel、查表、读 Excel、读表
- 查 `<文件名>.xlsx` 的 `<字段名>`
- 输出 `<EntityName>` 的 `<列名>`
- 在 `<文件名>` 里找 `<关键词>`

## Workflows

### 操作步骤

1. 确认目标文件路径（默认在 `Main/RawData/` 及其子目录下）
2. 用 Glob 搜索文件（模式：`**/文件名.xlsx`）
3. 用 Python + openpyxl 读取文件，精确匹配目标行
4. 输出用户要求的字段值

### Python 模板

```python
import openpyxl

wb = openpyxl.load_workbook('<绝对路径>', read_only=True, data_only=True)
ws = wb.active

# 读取表头
rows = ws.iter_rows(values_only=True)
headers = list(next(rows))

# 找目标列索引
target_col = '<列名>'  # 如 OtherTags、EntityTypes 等
col_idx = next((i for i, h in enumerate(headers) if h and h.lower() == target_col.lower()), None)

# 查找匹配行（Name 列精确匹配）
name_col = next((i for i, h in enumerate(headers) if h and h.lower() == 'name'), None)
for row in rows:
    if row[name_col] and '<查询值>'.lower() in str(row[name_col]).lower():
        print(f"{row[name_col]} -> {headers[col_idx]}: {row[col_idx]}")
```

## Code Locations

**数据源目录：**
- `Main/RawData/` — Excel 源数据根目录

## Common Issues

- openpyxl 不在默认环境时，先运行 `python -m pip install openpyxl`
- 查询值大小写不敏感，支持部分匹配
- 如果 `Main/RawData/` 下找不到文件，扩大搜索范围至整个 `Main/`
- 多 Sheet 时默认读取 `ws = wb.active`（第一个 Sheet），如需指定用 `wb['SheetName']`

## Guidelines

**示例：**

> 用户：输出 PLEntityTagMapping.xlsx 中 entity.campfire 的 OtherTags
>
> 输出：`AssetTag.NeedShelter`
