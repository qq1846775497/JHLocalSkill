---
name: ue-blueprint-reflection
title: UE Blueprint/C++ Reflection API 参考
description: Unreal Engine C++ 反射系统实战参考，涵盖 Blueprint 类属性访问、TMap/TArray/TSet 运行时操作、FScriptMapHelper、FObjectProperty、FStructProperty 等核心 API 的正确用法和常见陷阱。适用于需要通过反射读写 Blueprint 类属性、操作 Blueprint 结构体字段、遍历容器属性的所有场景。
tags: [C++, Blueprint, Reflection, UE5, Editor-Tools, Data-Driven]
---

# UE Blueprint/C++ Reflection API 参考

> Layer: Tier 3 (Workflow Reference)

## 核心原则

Blueprint 类的属性名在反射系统里存的是**显示名（Display Name）**，不是 C++ 字段名。Blueprint 结构体字段名通常带数字或 GUID 后缀（如 `DataAsset_5_A1B2C3D4`）。永远不要用精确名匹配 Blueprint 属性，用前缀匹配或迭代器。

---

## 属性查找

### 精确查找（仅用于 C++ 原生类）

```cpp
FProperty* Prop = SomeClass->FindPropertyByName(TEXT("MyField"));
```

### Blueprint 类属性 — 用前缀匹配

```cpp
FObjectProperty* DataAssetProp = nullptr;
for (TFieldIterator<FProperty> It(SomeStruct); It; ++It)
{
    if (It->GetName().StartsWith(TEXT("DataAsset")))
    {
        DataAssetProp = CastField<FObjectProperty>(*It);
        break;
    }
}
```

### 打印所有属性名（调试用）

```cpp
for (TFieldIterator<FProperty> It(SomeClass); It; ++It)
{
    UE_LOG(LogTemp, Warning, TEXT("Prop: '%s'"), *It->GetName());
}
```

---

## 属性类型转换

| 目标类型 | API |
|---------|-----|
| 对象引用 | `CastField<FObjectProperty>(Prop)` |
| 结构体 | `CastField<FStructProperty>(Prop)` |
| TMap | `CastField<FMapProperty>(Prop)` |
| TArray | `CastField<FArrayProperty>(Prop)` |
| bool | `CastField<FBoolProperty>(Prop)` |
| int32 | `CastField<FIntProperty>(Prop)` |
| FString | `CastField<FStrProperty>(Prop)` |
| FName | `CastField<FNameProperty>(Prop)` |
| FGameplayTag | `CastField<FStructProperty>(Prop)` → 验证 `Struct == FGameplayTag::StaticStruct()` |

> `GetValueProperty()` / `GetKeyProperty()` 返回 `const FProperty*`，声明时加 `const`，否则编译报"丢失限定符"。

```cpp
// 正确
const FStructProperty* ValueStructProp = CastField<FStructProperty>(MapProp->GetValueProperty());
const FStructProperty* KeyStructProp   = CastField<FStructProperty>(MapProp->GetKeyProperty());
```

---

## 读写对象属性值

```cpp
// 读
UObject* Obj = ObjectProp->GetObjectPropertyValue_InContainer(OwnerPtr);
// 或（已有 ValuePtr）
UObject* Obj = ObjectProp->GetObjectPropertyValue(ObjectProp->ContainerPtrToValuePtr<void>(ValuePtr));

// 写
ObjectProp->SetObjectPropertyValue_InContainer(OwnerPtr, NewObj);
// 或（已有 ValuePtr）
ObjectProp->SetObjectPropertyValue(ObjectProp->ContainerPtrToValuePtr<void>(ValuePtr), NewObj);
```

---

## TMap 运行时操作（FScriptMapHelper）

```cpp
FMapProperty* MapProp = CastField<FMapProperty>(
    SomeClass->FindPropertyByName(TEXT("MyMap")));

FScriptMapHelper MapHelper(MapProp, MapProp->ContainerPtrToValuePtr<void>(OwnerPtr));

for (int32 i = 0; i < MapHelper.Num(); ++i)
{
    if (!MapHelper.IsValidIndex(i)) continue;

    void* KeyPtr   = MapHelper.GetKeyPtr(i);
    void* ValuePtr = MapHelper.GetValuePtr(i);

    // 读 Key（FGameplayTag 示例）
    const FStructProperty* KeyStructProp = CastField<FStructProperty>(MapProp->GetKeyProperty());
    const FGameplayTag* Tag = KeyStructProp->ContainerPtrToValuePtr<FGameplayTag>(KeyPtr);

    // 读/写 Value 内的字段
    const FStructProperty* ValStructProp = CastField<FStructProperty>(MapProp->GetValueProperty());
    FObjectProperty* DataAssetProp = /* 前缀匹配查找 */;

    UObject* Existing = DataAssetProp->GetObjectPropertyValue(
        DataAssetProp->ContainerPtrToValuePtr<void>(ValuePtr));

    DataAssetProp->SetObjectPropertyValue(
        DataAssetProp->ContainerPtrToValuePtr<void>(ValuePtr), NewObj);
}
```

---

## TArray 运行时操作（FScriptArrayHelper）

```cpp
FArrayProperty* ArrProp = CastField<FArrayProperty>(
    SomeClass->FindPropertyByName(TEXT("MyArray")));

FScriptArrayHelper ArrHelper(ArrProp, ArrProp->ContainerPtrToValuePtr<void>(OwnerPtr));

for (int32 i = 0; i < ArrHelper.Num(); ++i)
{
    void* ElemPtr = ArrHelper.GetRawPtr(i);
    // 用 ArrProp->Inner 访问元素属性
    FObjectProperty* ElemObjProp = CastField<FObjectProperty>(ArrProp->Inner);
    UObject* Obj = ElemObjProp->GetObjectPropertyValue(ElemObjProp->ContainerPtrToValuePtr<void>(ElemPtr));
}
```

---

## 结构体内字段访问

```cpp
FStructProperty* StructProp = CastField<FStructProperty>(
    SomeClass->FindPropertyByName(TEXT("MyStruct")));

void* StructPtr = StructProp->ContainerPtrToValuePtr<void>(OwnerPtr);

// 在结构体内查找字段（Blueprint 结构体用前缀匹配）
FObjectProperty* InnerProp = nullptr;
for (TFieldIterator<FProperty> It(StructProp->Struct); It; ++It)
{
    if (It->GetName().StartsWith(TEXT("DataAsset")))
    {
        InnerProp = CastField<FObjectProperty>(*It);
        break;
    }
}

UObject* Val = InnerProp->GetObjectPropertyValue(
    InnerProp->ContainerPtrToValuePtr<void>(StructPtr));
```

---

## 常见陷阱

| 陷阱 | 原因 | 解决 |
|------|------|------|
| `FindPropertyByName` 返回 null | Blueprint 属性名带后缀 | 用 `TFieldIterator` + `StartsWith` |
| `CastField` 返回 null | 属性类型不匹配 | 先打印 `Prop->GetClass()->GetName()` 确认类型 |
| `GetValueProperty()` 编译报"丢失限定符" | 返回 `const FProperty*` 但声明为非 const | 加 `const` |
| 写回 TMap 后数据丢失 | 直接修改 copy 而非原始内存 | 用 `GetValuePtr` 拿到原始指针再写 |
| Blueprint 子类 Cast 失败 | `NotifyStateClass.Get()` 返回的是 CDO | 确认用 `.Get()` 而非 `->GetClass()` |

---

## 实战案例：遍历 Blueprint TMap 并写回 DataAsset

本项目中 `ExtractCollisionConfigFromAnimMontage` 处理 `ANS_PLCollisionByTags_C` 的完整流程：

```cpp
// 1. 找 TMap 属性
FMapProperty* MapProp = CastField<FMapProperty>(
    NotifyClass->FindPropertyByName(TEXT("TagCollisionPackages")));

// 2. 获取 Value 结构体类型
const FStructProperty* ValueStructProp = CastField<FStructProperty>(MapProp->GetValueProperty());

// 3. 在 Value 结构体内找 DataAsset 字段（前缀匹配）
FObjectProperty* DataAssetProp = nullptr;
for (TFieldIterator<FProperty> It(ValueStructProp->Struct); It; ++It)
{
    if (It->GetName().StartsWith(TEXT("DataAsset")))
    {
        DataAssetProp = CastField<FObjectProperty>(*It);
        break;
    }
}

// 4. 获取 Key 类型（C++ 原生结构体可直接用）
const FStructProperty* KeyStructProp = CastField<FStructProperty>(MapProp->GetKeyProperty());

// 5. 遍历 Map
FScriptMapHelper MapHelper(MapProp, MapProp->ContainerPtrToValuePtr<void>(NotifyState));
for (int32 i = 0; i < MapHelper.Num(); ++i)
{
    if (!MapHelper.IsValidIndex(i)) continue;

    void* ValuePtr = MapHelper.GetValuePtr(i);
    const FGameplayTag* Tag = KeyStructProp->ContainerPtrToValuePtr<FGameplayTag>(
        MapHelper.GetKeyPtr(i));

    // 6. 读现有值
    UObject* Existing = DataAssetProp->GetObjectPropertyValue(
        DataAssetProp->ContainerPtrToValuePtr<void>(ValuePtr));
    if (Existing) continue; // 已有则跳过

    // 7. 写回新值
    DataAssetProp->SetObjectPropertyValue(
        DataAssetProp->ContainerPtrToValuePtr<void>(ValuePtr), NewAsset);
}
```

---

## 相关文件

- `Main/Plugins/PLPythonPipeline/Source/PLPythonPipeline/Private/PLPythonAutomationFunctionLibrary.cpp` — `ExtractCollisionConfigFromAnimMontage` 完整实现
