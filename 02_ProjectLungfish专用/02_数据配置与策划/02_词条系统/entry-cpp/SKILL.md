---
name: entry-cpp
description: 装备词条系统程序实现参考。覆盖词条 C++ 类架构、触发器子类、参数系统、事件容器、GAS 集成、网络复制。仅在涉及程序实现时触发。当用户提到"PLEntryInst"、"PLEquipmentEntryInst"、"EquipmentEntryInst"、"词条实现"、"词条代码"、"词条子类"、"词条触发器代码"、"CreateEntryInstance"、"ActivateTriggerLogic" 时注入上下文。
tags:
  - PLEntryInst
  - PLEquipmentEntryInst
  - EquipmentEntryInst
  - 词条实现
  - 词条代码
  - 词条子类
  - CreateEntryInstance
  - ActivateTriggerLogic
  - DeactivateTriggerLogic
  - PLEntryBlueprintFunctionLibrary
  - entry-cpp
---

# 装备词条系统 — 程序实现参考

> Layer: Tier 3 (Plugin / Implementation)
> Plugin: `GASExtendedPL`

<memory category="architecture">
## 核心类关系

```
FPLEquipmentEntryInfoDef  (DataTable 行，词条定义)
    └─ EPLEquipmentEntryTrigger      (触发时机枚举)
    └─ FPLEntryEventContainer        (触发时执行的效果容器)
    └─ FPLEntryParameterWithLevel[]  (分等级参数配置)

UPLEquipmentEntryInst  (基类，运行时词条实例)
    ├─ UPLEquipmentEntryInst_Permanent         (Permanent)
    ├─ UPLEquipmentEntryInst_TagChanged        (OnTagChanged)
    ├─ UPLEquipmentEntryInst_AttributeChanged  (OnAttributeChanged)
    ├─ UPLEquipmentEntryInst_GameplayEvent     (OnGameplayEvent)
    ├─ UPLEquipmentEntryInst_OnAttach          (OnAttachToInstance / OnAttachToActor)
    └─ UPLEquipmentEntryInst_ActorAttachDetach (Actor 生命周期)
```
</memory>

<memory category="code-locations">
## 文件位置

所有词条相关代码在 `GASExtendedPL` 插件下，路径：
`Main/Plugins/GASExtendedPL/Source/GASExtendedPL/Public/Equipment/Entry/`

| 文件 | 用途 |
|------|------|
| `PLEntryInst.h/.cpp` | 词条实例基类、`FPLEntryInstTransferData`、激活状态枚举 |
| `PLEntryEnum.h` | 全部枚举定义 |
| `PLEntryParameter.h/.cpp` | `FPLEntryParameter`、`FPLEntryParameterWithLevel` |
| `PLEntryEventContainer.h/.cpp` | `FPLEquipmentEntryInfoDef`（DataTable行）、`FPLEntryEventContainer`、`FPLEntryEventHandle` |
| `PLEntryBlueprintFunctionLibrary.h/.cpp` | 词条操作入口：创建、随机、查询、通货 |
| `PLDamageFlowCalculation.h/.cpp` | 伤害流自定义计算基类 |
| `PLEquipmentEntryInst_Permanent.h/.cpp` | Permanent 子类 |
| `PLEquipmentEntryInst_TagChanged.h/.cpp` | OnTagChanged 子类 |
| `PLEquipmentEntryInst_AttributeChanged.h/.cpp` | OnAttributeChanged 子类 |
| `PLEquipmentEntryInst_GameplayEvent.h/.cpp` | OnGameplayEvent 子类 |
| `PLEquipmentEntryInst_OnAttach.h/.cpp` | OnAttach 子类 |
| `PLEquipmentEntryInst_ActorAttachDetach.h/.cpp` | Actor 生命周期子类 |
</memory>

<memory category="core-rules">
## 关键实现规则

### 实例创建：必须走工厂方法
不要直接 `NewObject<UPLEquipmentEntryInst>`，工厂方法根据 `EntryTrigger` 自动选择子类：
```cpp
UPLEquipmentEntryInst* Inst = UPLEquipmentEntryBlueprintFunctionLibrary::CreateEntryInstByTag(
    EntryTag, Level, EPLEntrySource::Random, /*RemainTime=*/-1.f);
// 或底层工厂：
UPLEquipmentEntryInst* Inst = UPLEquipmentEntryBlueprintFunctionLibrary::CreateEntryInstance(Outer, EntryDef);
```

### 新触发器子类扩展步骤
1. 继承 `UPLEquipmentEntryInst`
2. 覆写 `ActivateTriggerLogic()` — 注册委托
3. 覆写 `DeactivateTriggerLogic()` — 注销委托
4. 按需覆写 `OnEquipmentEvent()` / `OnActorLifecycleEvent()`
5. 在 `PLEntryBlueprintFunctionLibrary.cpp` 的 `CreateEntryInstance()` 里注册新触发器类型

### bActivateOnce 机制
- 同 `EntryTag` 在角色身上只允许一个实例激活
- 后来的实例进入 `PendingActivation`，前者销毁后自动补位（`TryReactivateEntry()`）

### 事件流 GA 授予
- `UPLEquipmentEntryInst::ActivateEntryInternal()` 会先调用 `FPLEntryEventContainer::GiveEntryAbilities()`，在服务端预先授予装备/角色事件流中的 `GrantAbilities`
- `FPLEntryRowEventContainer::GiveEntryRowAbilities()` 必须检查 `ASC->IsOwnerActorAuthoritative()`，客户端路径只跳过授予
- `TriggerEquipmentEntryInfoDef()` 在服务器触发时会转发到 owner client；服务器继续处理权威 GE/Tag，owner client 负责本地主控 GA 激活
- 触发事件时用 `ClearEntryEvent(false)` 清理临时效果/标签但保留 GA handle，再通过 `ApplyEntryEventToHandle()` 复用已授予能力；客户端本地激活还会按 `GrantAbilities` 的 class 查找已复制的 spec handle

### 参数系统
- 参数通过 `Location`（枚举索引）区分，用 `GetParameterByNameAndLocation()` 取值
- 网络同步：`Parameters` 有 `ReplicatedUsing=OnRep_Parameters`
- `BuildRandomValue(Level)` 按 `FPLEntryParameterWithLevel` 配置随机

### RefuseDamageFromEntry
- 默认 `true`，词条触发的伤害不再触发其他词条（防连锁）
- 需要连锁时显式设为 `false`，注意设计风险

### 持续时间词条
- 调用 `SetDuration(Seconds)` 设置有限持续时间，不调用则无限（`RuntimeEntryDuration = -1.0f`）
- `RuntimeEntryDuration` / `DurationStartTimestamp` 用 `SaveGame` 标记供存档重建

### 网络传输重建
```cpp
// 客户端 → 服务器传输
FPLEntryInstTransferData TransferData;
TransferData.EntryTag = Inst->EntryTag;
TransferData.ParameterValues = ...;  // 从 Parameters 提取

// 服务器重建
UPLEquipmentEntryInst* Rebuilt =
    UPLEquipmentEntryBlueprintFunctionLibrary::CreateEntryInstFromTransferData(TransferData);
```

### Item 宿主绑定的客户端/服务端语义
- `AttachToItemInstance()` 必须显式区分 authority 与 non-authority 路径
- 服务端：直接调用内部主干实现（如 `AttachToResolvedHost()`），不要通过 `ServerAttachToItemInstance()` 再绕回本地
- 客户端：发送 `ServerAttachToItemInstance()` 请求，同时本地仅建立轻量 `HostBinding` 语义；真正容器挂接仍由服务端完成

### CharacterDirect 宿主绑定的客户端/服务端语义
- `AttachToCharacter()` 应与 Item 宿主保持同样的网络语义分层
- 服务端：直接调用 `AttachToResolvedHost(EPLEquipmentEntryHostType::CharacterDirect, EquipmentManagerComponent)`
- 客户端：发送 `ServerAttachToCharacter(Character)` 请求，同时本地只建立轻量 `CharacterDirect` 宿主语义；真正的 direct entry 容器挂接仍由服务端完成

### 宿主查询接口收敛
- 对外统一保留 `GetHostObject()`、`GetOwnerWeapon()`、`GetOwnerCharacter()`、`GetOwnerInstance()`、`GetOwnerASC()`
- `UPLEquipmentEntryInst` 不再额外公开 `ResolveOwnerCharacter()` / `ResolveOwnerInstance()` / `ResolveOwnerEquipmentActor()`
- 对外 getter 内部统一通过 `HostContext + HostType` 做解析，避免暴露两套近义接口
</memory>
