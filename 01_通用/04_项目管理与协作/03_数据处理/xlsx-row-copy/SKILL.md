---
name: xlsx-row-copy
title: Excel 行筛选复制工具
description: 从一个 Excel 文件中筛选第二列包含特定 Tag/字符串的行，按列名映射后复制追加到另一个 Excel 文件，自动跳过目标文件不存在的列，不破坏目标文件格式。当用户说"把 XXX 表格中第二列带有 YYY 的行复制到 ZZZ 表格"，或提到"筛选 Excel 行"、"跨表格复制数据"、"从 xlsx 复制行"、"把某个 tag 的行挪到另一个表"时，立即使用此 skill。
tags: [Excel, Python, Data-Pipeline, DataTables, Configuration]
---

# Excel 行筛选复制工具

## 使用场景

用户说类似：
- "把 BuildingMerge 表第二列含 `Achievement.Show.CraftRecipe` 的行复制到 CraftRecipe 表"
- "把某个 xlsx 里第二列带有 XXX 的所有行复制到另一个 xlsx"
- "筛选并迁移 Excel 行"

## 环境要求

- Python 路径：`/c/Users/admin/AppData/Local/Programs/Python/Python312/python.exe`
- 依赖库：`openpyxl`（如未安装：`/c/Users/admin/AppData/Local/Programs/Python/Python312/python.exe -m pip install openpyxl`）

> 脚本通过 bash heredoc 写入 `/tmp/`，由上述 python.exe 执行。stdout 无法直接捕获，所以**所有输出必须写入 Windows 可访问的文件路径**（如源/目标文件同目录），再用 Read 工具读取，完成后删除。

---

## 执行流程

### Step 1：检查两个文件的列结构

写一个检查脚本，输出两个文件的所有列名及前几行数据，找到列名差异：

```bash
cat > /tmp/inspect_xlsx.py << 'PYEOF'
import openpyxl

src  = r'<源文件 Windows 绝对路径>'
dst  = r'<目标文件 Windows 绝对路径>'
outpath = r'<与源文件同目录的临时输出文件路径，如 RawData\AchievementList\_out.txt>'

with open(outpath, 'w', encoding='utf-8') as out:
    wb = openpyxl.load_workbook(src, data_only=True)
    ws = wb.active
    out.write("=== SRC columns ===\n")
    row1 = [c.value for c in ws[1]]
    row2 = [c.value for c in ws[2]]
    for i in range(len(row1)):
        out.write(f"  Col {i+1}: {row1[i]} | {row2[i]}\n")
    out.write("\n=== SRC sample rows (matching col2) ===\n")
    for row in ws.iter_rows(min_row=1):
        val = row[1].value
        if val and '<筛选关键字>' in str(val):
            out.write(f"  {[c.value for c in row]}\n")

    wb2 = openpyxl.load_workbook(dst)
    ws2 = wb2.active
    out.write("\n=== DST columns ===\n")
    row1d = [c.value for c in ws2[1]]
    row2d = [c.value for c in ws2[2]]
    for i in range(len(row1d)):
        out.write(f"  Col {i+1}: {row1d[i]} | {row2d[i]}\n")
    out.write("\n=== DST non-empty rows ===\n")
    for i, row in enumerate(ws2.iter_rows()):
        vals = [c.value for c in row]
        if any(v is not None for v in vals):
            out.write(f"  Row {i+1}: {vals}\n")
print("done")
PYEOF
/c/Users/admin/AppData/Local/Programs/Python/Python312/python.exe /tmp/inspect_xlsx.py 2>&1
```

读取输出文件后**删除它**。

---

### Step 2：确认列映射，如有差异询问用户

对比两个文件的列名，构建映射关系：

- **列名相同** → 对应复制
- **源文件有、目标文件没有** → 默认跳过（若不确定，先询问用户）
- **目标文件有、源文件没有** → 留空（None）

将映射转换为"源列索引列表"（0-based），顺序对应目标列 1 → N。

**示例**（本次实际案例）：
```
# 源文件16列，跳过 col3(DevComment) 和 col12(AchievementDescriptionFull)
SRC_COL_INDICES = [0, 1, 3, 4, 5, 6, 7, 8, 9, 10, 12, 13, 14, 15]
```

---

### Step 3：执行复制

```bash
cat > /tmp/copy_rows.py << 'PYEOF'
import openpyxl

src  = r'<源文件 Windows 绝对路径>'
dst  = r'<目标文件 Windows 绝对路径>'
KEYWORD    = '<筛选关键字>'              # 在第2列（col index 1）中匹配
SRC_COL_INDICES = [...]                  # 按 Step 2 确定的映射

# 1. 从源文件筛选匹配行
wb_src = openpyxl.load_workbook(src, data_only=True)
ws_src = wb_src.active
matched = []
for row in ws_src.iter_rows(min_row=1):
    val = row[1].value
    if val and KEYWORD in str(val):
        matched.append([row[i].value for i in SRC_COL_INDICES])
print(f"Matched: {len(matched)} rows")

# 2. 找目标文件末尾，追加数据
wb_dst = openpyxl.load_workbook(dst)
ws_dst = wb_dst.active
last_row = 0
for i, row in enumerate(ws_dst.iter_rows(), start=1):
    if any(c.value is not None for c in row):
        last_row = i
next_row = last_row + 1
print(f"Appending from row {next_row}")

for row_data in matched:
    for col_idx, value in enumerate(row_data, start=1):
        ws_dst.cell(row=next_row, column=col_idx, value=value)
    next_row += 1

wb_dst.save(dst)
print("Saved.")
PYEOF
/c/Users/admin/AppData/Local/Programs/Python/Python312/python.exe /tmp/copy_rows.py 2>&1
```

---

### Step 4：验证

写一个小验证脚本（输出写到临时文件），确认：
- 目标文件数据行数量正确
- 第2列值全为预期 keyword
- 原有表头行格式未变（行数 = 原行数 + 新增行数）

验证完后删除临时输出文件。

---

## 注意事项

| 事项 | 说明 |
|------|------|
| 表头行识别 | Row 1 = 列名，Row 2 = 类型，Row 3 = 备注（部分表格）；数据从 Row 4 开始 |
| 只复制值 | openpyxl 默认只写值，不复制单元格格式（颜色/字体/冻结行均保留在目标文件） |
| 空字符串 vs None | 源文件空字符串 `''` 写入后等同于空单元格，与 `None` 行为相同 |
| 文件被 Excel 打开 | 保存会失败；确保目标文件已关闭 |
| stdout 捕获问题 | bash 调用 Windows python.exe 时 stdout 丢失；**所有输出必须写文件** |

---

## 快速参考：本次实际案例

```
源文件：Main/RawData/AchievementList/BuildingMergeAchievementList.xlsx（16列）
目标文件：Main/RawData/AchievementList/CraftRecipeAchievementList.xlsx（14列）
筛选条件：col2 含 'Achievement.Show.CraftRecipe'
跳过列：DevComment (col3), AchievementDescriptionFull (col12)
结果：12行写入目标文件 Row 4 起
SRC_COL_INDICES = [0, 1, 3, 4, 5, 6, 7, 8, 9, 10, 12, 13, 14, 15]
```
