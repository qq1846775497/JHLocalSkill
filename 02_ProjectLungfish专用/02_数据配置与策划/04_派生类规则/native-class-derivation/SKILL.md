---
name: native-class-derivation
title: PL 派生类规则 —— 组件与 AnimInstance
description: 项目强制规则：禁止直接使用 UE 原生组件类和 AnimInstance，必须使用项目 PL 派生版本。适用于所有 Blueprint SCS 组件添加、C++ AddComponent、AnimBlueprint 父类设置场景。违反此规则会被 AssetNativeClassCheck 扫描器标记。
tags: [NativeClass, Component, AnimInstance, PL, UE5, Blueprint, C++]
---

# PL 派生类规则 —— 组件与 AnimInstance

> 本规则由 AssetScanner 插件的 `AssetNativeClassCheck` 规则强制执行。
> 所有 Blueprint 和 C++ 代码都必须遵守此映射，不得直接使用左侧原生类。

## 组件类映射（Component Class Mappings）

| ❌ 禁止使用（原生类） | ✅ 必须使用（PL 派生类） |
|---|---|
| `UStaticMeshComponent` | `UPLStaticMeshComponent` |
| `USkeletalMeshComponent` | `UPLSkeletalMeshComponent` |
| `UBoxComponent` | `UPLBoxComponent` |
| `UCapsuleComponent` | `UPLCapsuleComponent` |
| `USphereComponent` | `UPLSphereComponent` |
| `UArrowComponent` | `UPLArrowComponent` |
| `UBillboardComponent` | `UPLBillboardComponent` |
| `USceneComponent` | `UPLSceneComponent` |
| `UNiagaraComponent` | `UPLNiagaraComponent` |
| `UPostProcessComponent` | `UPLPostProcessComponent` |
| `UFoliageInstancedStaticMeshComponent` | `UPLFoliageInstancedStaticMeshComponent` |
| `UPhysicsConstraintComponent` | `UPLPhysicsConstraintComponent` |

## ParentClass 映射（AnimBlueprint）

| ❌ 禁止使用（原生父类） | ✅ 必须使用（PL 派生父类） |
|---|---|
| `UAnimInstance` | `UPLAnimInstance` |

---

## 适用场景

### Blueprint SCS（SimpleConstructionScript）
在 Blueprint 编辑器中添加组件时，从组件列表选择 **PL 版本**，不要选择原生版本。

### AnimBlueprint 父类
新建 AnimBlueprint 时，父类必须设置为 `UPLAnimInstance`，不得设置为 `UAnimInstance`。

### C++ AddComponent / CreateDefaultSubobject
```cpp
// ❌ 错误
UStaticMeshComponent* Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));

// ✅ 正确
UPLStaticMeshComponent* Mesh = CreateDefaultSubobject<UPLStaticMeshComponent>(TEXT("Mesh"));
```

---

## 检查工具

违反此规则的资产会被 **AssetScanner 插件** 的 `AssetNativeClassCheck` 规则检出，
输出列：`CheckType`（Component / ParentClass）、`NativeClass`、`SuggestPL`、`Submitter`。
