---
name: equip-entry-pool-config
description: Workflow for updating equipment entry pool configuration in ProjectLungfish. Use when user mentions "equip entry pool", "EquipEntryPoolConfig", "词条池配置", "generate_config", "配置装备词条", "equipment entry", "entry pool", or needs to run the Python config generation pipeline for equipment entry weights. Covers Excel editing → Python script generation → JSON output → game import.
---

# EquipEntryPoolConfig Workflow

## Quick Reference

### Run Script
```bash
# From project root — close EquipEntryPoolConfig.xlsx first!
python ClaudeTasks/EquipEntryPoolConfig/generate_config.py
```

### Output Files
```
Main/RawData/EquipEntryPoolConfig.xlsx       # Excel (human-readable)
Main/RawData/EquipEntryPoolConfig.xlsx.json  # JSON (game reads this)
```

---

## Complete Workflow

### Step 1 — Edit Source Config
Edit `ClaudeTasks/EquipEntryPoolConfig/Entry_Pool.xlsx`:
- Modify entry (词条) Chinese names
- Adjust weight values (must be numeric, keep decimals like `108.0`)
- Add/remove rows — keep prefix/suffix boundary at row 16

### Step 2 — Prepare Environment
⚠️ **Close `Main/RawData/EquipEntryPoolConfig.xlsx` before running the script.**

### Step 3 — Run Generator
```bash
python ClaudeTasks/EquipEntryPoolConfig/generate_config.py
```

Script flow:
1. Load `Entry_Pool.xlsx` (Chinese config)
2. Load `Entry_EquipmentTag.xlsx` (equipment name → Tag mapping)
3. Load `Entry_List.xlsx` (entry name → Tag mapping)
4. Generate JSON data
5. Save Excel (may fail if file is locked — JSON still saves)
6. Save JSON to `Main/RawData/`

### Step 4 — Check Script Output
Look for warnings:
```
⚠ 警告: 以下词条缺少Tag映射 (共N个):
    - 某词条名
```
Missing-mapping entries are **silently skipped** in output. Fix before continuing.

### Step 5 — Verify Output
- Correct equipment type count (currently 14)
- Tag format: `EntityType.Equip.*` / `EntityType.Hand.*`
- Entry tag format: `EquipmentEntry.*`
- Weights are floats (`108.0` not `108`)
- Excel and JSON contents match

### Step 6 — Import & Test
Import `EquipEntryPoolConfig.xlsx.json` in UE editor, verify all equipment types load.

---

## Data Flow

```
Entry_Pool.xlsx (策划编辑)
    ↓
    + Entry_EquipmentTag.xlsx  (中文→ EntityType Tag)
    + Entry_List.xlsx          (中文→ EquipmentEntry Tag)
    ↓
generate_config.py
    ↓
EquipEntryPoolConfig.xlsx.json  ←  game reads
EquipEntryPoolConfig.xlsx       ←  human review
```

---

## JSON Output Structure

```json
[
    {
        "Name": "1",
        "Id": 1,
        "EquipSlot": { "TagName": "EntityType.Equip.Helmet" },
        "PrefixesNumber": [
            { "FGameplayTag_Item1": { "TagName": "EquipmentEntry.AddMaxHealth" }, "Float_Item2": 108.0 }
        ],
        "SuffixesNumber": [
            { "FGameplayTag_Item1": { "TagName": "EquipmentEntry.AddFireResistance" }, "Float_Item2": 93.0 }
        ]
    }
]
```

Note: First entry uses `"Name": "1"`, subsequent entries use `"Name": "1_0"`, `"Name": "1_1"`, etc.

---

## Mapping Tables

### Equipment Types (14 total)
| Chinese | Tag |
|---------|-----|
| 头盔 | EntityType.Equip.Helmet |
| 胸甲 | EntityType.Equip.ChestPlate |
| 裤子 | EntityType.Equip.Leggings |
| 鞋子 | EntityType.Equip.Shoes |
| 手套 | EntityType.Equip.Gloves |
| 饰品 | EntityType.Equip.Charm |
| 盾牌 | EntityType.Hand.Shield |
| 单手斧 | EntityType.Hand.Axe |
| 单手锤 | EntityType.Hand.Hammer |
| 单手矛 | EntityType.Hand.Spear |
| 双手斧 | EntityType.Hand.Axe2H |
| 双手锤 | EntityType.Hand.Hammer2H |
| 笛子 | EntityType.Hand.HornBone |
| 弓箭 | EntityType.Hand.Bow |

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Equipment type missing in output | No Tag mapping in `Entry_EquipmentTag.xlsx` | Add `Chinese name → Tag` row |
| Entry not appearing | No Tag mapping in `Entry_List.xlsx` | Add `Chinese name → EquipmentEntry.Tag` row |
| Excel save fails | File open in Excel | Close Excel, rerun |
| JSON import fails | Float formatted as int | Fix weight column to numeric format |
| Fewer entries than expected | Missing mappings silently skipped | Check script warnings |

---

## Critical Rules

- **Never** modify `sheet_name` parameter in script — game automation requires `Sheet1`
- **Never** hand-edit the generated files; always regenerate via script
- Add new equipment types → update `Entry_EquipmentTag.xlsx`
- Add new entries → update `Entry_List.xlsx`

---

## File Locations

| File | Purpose |
|------|---------|
| `ClaudeTasks/EquipEntryPoolConfig/Entry_Pool.xlsx` | Source config (edit this) |
| `ClaudeTasks/EquipEntryPoolConfig/Entry_EquipmentTag.xlsx` | Equipment type mapping |
| `ClaudeTasks/EquipEntryPoolConfig/Entry_List.xlsx` | Entry template mapping |
| `ClaudeTasks/EquipEntryPoolConfig/generate_config.py` | Generator script |
| `Main/RawData/EquipEntryPoolConfig.xlsx.json` | Output (game reads) |
| `Main/RawData/EquipEntryPoolConfig.xlsx` | Output (human review) |
