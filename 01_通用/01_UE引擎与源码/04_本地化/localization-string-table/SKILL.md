---
name: localization-string-table
title: UE StringTable 多语言使用指南
description: UE StringTable 资产的加载机制、查询 API 选择与多语言支持文档。涵盖两阶段加载陷阱、EStringTableLoadingPolicy 对比、FText 懒加载问题，以及项目标准 ConvertTextIdToText 模式。适用于一切需要通过 key 查询本地化文本的场景。
tags: [Localization, i18n, String-Table, FText, UE5, C++, Asset-Management]
---

# UE StringTable 多语言使用指南

> Layer: Tier 3 (Module Documentation)

## StringTable 加载的两个阶段

UE 加载 `UStringTable` 资产分两个阶段，这是很多查询失败的根因：

```
阶段1：对象创建
  UStringTable 对象分配内存
  → FStringTableRegistry::RegisterStringTable() 被调用
  → Registry 出现 Shell 条目（FindStringTable().IsValid() == true）
  → 但此时 entries 是空的！

阶段2：PostLoad
  UStringTable::PostLoad() 运行
  → 遍历所有 Key-Value 写入 FStringTableRegistry
  → 此时才能正确查询 key
```

**常见陷阱**：用 `FindStringTable().IsValid()` 判断"是否可以查询"是错的，
Shell 阶段就会返回 true，但 PostLoad 尚未完成。

---

## EStringTableLoadingPolicy 对比

| Policy | 机制 | 等待 PostLoad | entries 可用 |
|--------|------|:---:|:---:|
| `Find` | 仅查 Registry，不加载 | ❌ | - |
| `FindOrLoad` | AsyncLoad，提交后立即返回 | ❌（可能） | ❌ |
| `FindOrFullyLoad` | 同步阻塞，等待完整周期 | ✅ | ✅ |

`FindOrLoad` 会触发阶段1后返回，`FindOrFullyLoad` 保证阶段2完成。

---

## 查询 API 选择

### ❌ 不推荐：Internal_FindLocTableEntry
```cpp
// 内部 API，不稳定；需配合 FindOrFullyLoad 才能保证 entries 已填充
FStringTableRegistry::Get().Internal_FindLocTableEntry(TableId, Key, EStringTableLoadingPolicy::FindOrFullyLoad);
```

### ✅ 推荐：FText::FromStringTable（公开 API，支持多语言）
```cpp
// 注意：FromStringTable 是懒加载引用，不能用 IsEmpty() 判断 key 是否存在
// 正确做法：先用 FindEntry 验证，再调 FromStringTable
FText Result = FText::FromStringTable(TableId, KeyString);
```

### ✅ 推荐：FindEntry + FromStringTable（完整安全模式）
```cpp
FStringTableConstPtr Table = FStringTableRegistry::Get().FindStringTable(TableId);
if (Table.IsValid() && Table->FindEntry(KeyString).IsValid())
{
    return FText::FromStringTable(TableId, KeyString);
}
```

---

## FText::FromStringTable 的懒加载陷阱

```cpp
FText Result = FText::FromStringTable("ST_Text", "100005");

// ❌ 错误：IsEmpty() 检查的是 DisplayString，懒加载前可能为空
if (!Result.IsEmpty()) { ... }

// ✅ 正确：先用 FindEntry 确认 key 存在，再调 FromStringTable
```

---

## 多语言内存模型

StringTable 本身只存储 **Source 语言**文本，翻译存在 `.locres` 文件中：

```
ST_Text.uasset           → Source 文本（常驻内存，~3-8MB）
Localization/zh-CN/*.locres  → 中文翻译（仅加载当前语言）
Localization/en/*.locres     → 英文翻译（不加载）
Localization/ja/*.locres     → 日文翻译（不加载）
```

- **不会多语言同时加载**，只有当前 culture 的 `.locres` 在内存
- `FText::AsCultureInvariant(Entry->GetSourceString())` 会绕过本地化系统，永远返回 Source 语言，**不支持多语言**
- `FText::FromStringTable` 会走 `.locres` 查找，正确支持多语言

---

## 项目标准用法（ConvertTextIdToText 模式）

```cpp
static const TCHAR* TablePath = TEXT("/Game/003_DataTablePipeline/Localization/ST_Text.ST_Text");
static const FName TableId = TablePath;

FStringTableConstPtr Table = FStringTableRegistry::Get().FindStringTable(TableId);
if (!Table.IsValid())
{
    // 表未加载时主动同步加载（LoadObject 保证 PostLoad 完成）
    LoadObject<UStringTable>(nullptr, TablePath);
    Table = FStringTableRegistry::Get().FindStringTable(TableId);
}

if (Table.IsValid() && Table->FindEntry(KeyString).IsValid())
{
    return FText::FromStringTable(TableId, KeyString, EStringTableLoadingPolicy::FindOrFullyLoad);
}
```

**TableId 说明**：可以是资产全路径（`/Game/.../ST_Text.ST_Text`）或
TableNamespace 短名（`ST_Text`），取决于资产的 TableNamespace 属性设置。
两种方式在 Registry 中均可命中，但需保持 `FindStringTable` 与 `FromStringTable` 调用一致。

---

## Troubleshooting

| 现象 | 原因 | 解决 |
|------|------|------|
| `FindStringTable().IsValid()` 为 true 但查 key 为空 | 阶段1完成但 PostLoad 未完成 | 用 `LoadObject` 或 `FindOrFullyLoad` 确保完整加载 |
| `FText::FromStringTable` 返回空 | 懒加载未解析，`IsEmpty()` 误判 | 用 `FindEntry` 验证 key 存在后再调用 |
| 多语言不生效，永远显示中文 | 使用了 `AsCultureInvariant(GetSourceString())` | 改用 `FText::FromStringTable` |
| `FindOrLoad` 后 entries 仍为空 | AsyncLoad 返回时 PostLoad 未完成 | 改用 `FindOrFullyLoad` |
