---
name: ue-software-architecture
description: >
  ProjectLungfish 的 Unreal Engine 项目软件工程规范。涵盖代码结构发现、模块组织、
  C++↔Blueprint 边界、GAS 架构模式、命名约定、目录规范。在编写或修改任何 UE C++/
  Blueprint/配置文件前，先通过本 skill 确认项目结构和规范约束。
trigger_when: >
  用户提到"项目结构"、"代码规范"、"模块"、"命名约定"、"GAS 架构"、
  "C++ Blueprint 边界"、"怎么组织代码"、"Source 目录"、".Build.cs"、
  "uproject"、"插件结构"、"Gameplay Ability System"、"AttributeSet"、
  "Enhanced Input"、"项目架构"、"代码框架"。
  也应在任何 UE C++ 或 Blueprint 修改前被动触发，用于确认规范。
---

# UE 项目软件工程规范（ProjectLungfish）

> **Zero Assumptions Philosophy**：永远不要假设你知道项目结构。先侦察，再规范。

## 项目结构发现（强制第一步）

在提供任何代码建议前，必须先执行以下侦察：

1. **定位 `.uproject` 文件**：
   ```powershell
   Glob: **/*.uproject
   ```
   读取 `.uproject` 的 `Modules` 和 `Plugins` 列表，了解项目模块组成。

2. **扫描 `Source/` 目录**：
   ```powershell
   Glob: Source/**/*.Build.cs
   ```
   提取模块名和依赖关系（`PublicDependencyModuleNames`）。

3. **识别命名约定**：
   - 项目前缀：`PL`（ProjectLungfish）
   - 扫描前 20 个 `.h` 文件的类名，确认前缀模式

---

## 模块组织规范

### 模块层级

| 层级 | 模块名模式 | 内容 | 示例 |
|------|-----------|------|------|
| 游戏核心 | `ProjectLungfish` | GameMode, Character, PlayerState, GameState | `APLGameMode`, `APLCharacter` |
| 编辑器扩展 | `ProjectLungfishEditor` | 自定义编辑器窗口、资源导入器 | `FPLAssetTools` |
| 功能插件 | `PL{Feature}` | 独立可复用功能 | `PLBehaviorTreeSM`, `SoftUEBridge` |
| 第三方 | `External/` 或 `ThirdParty/` | 不直接修改源码 | — |

### 模块依赖规则

```
ProjectLungfishEditor → ProjectLungfish → Engine Modules
       ↑
   PLPlugins (独立，可被两者依赖)
```

- **禁止循环依赖**：如果 A.Build.cs 依赖 B，B 不能反向依赖 A
- **最小暴露原则**：只在 `Public/` 放需要跨模块引用的头文件
- **私有实现放 `Private/`**：内部类、辅助函数不暴露

### .Build.cs 规范

```csharp
PublicDependencyModuleNames.AddRange(new string[] {
    "Core", "CoreUObject", "Engine", "InputCore",
    "GameplayAbilities", "GameplayTags", "GameplayTasks"  // GAS 三件套
});

PrivateDependencyModuleNames.AddRange(new string[] {
    "ProjectSettings",  // 仅在内部使用
});
```

---

## C++ ↔ Blueprint 边界规范

### 决策矩阵

| 场景 | 使用 C++ | 使用 Blueprint |
|------|---------|---------------|
| 核心 gameplay 逻辑（Tick、碰撞、伤害计算）| ✅ | ❌ |
| 网络复制（RPC、 replicated 属性）| ✅ | ⚠️ 仅简单属性 |
| 性能敏感代码（物理、动画、AI 感知）| ✅ | ❌ |
| 视觉/表现层（材质、粒子、UI 布局）| ❌ | ✅ |
| 快速原型/策划调参 | ⚠️ 暴露参数 | ✅ |
| 单次/工具性逻辑（编辑器脚本）| ❌ | ✅ |

### C++ 暴露规范

```cpp
// ✅ 正确：暴露给策划调参
UPROPERTY(EditDefaultsOnly, Category = "PL|Combat")
float AttackDamage = 25.0f;

// ✅ 正确：Blueprint 可调用的 C++ API
UFUNCTION(BlueprintCallable, Category = "PL|Ability")
void ActivateAbilityByTag(FGameplayTag AbilityTag);

// ❌ 错误：所有变量都 BlueprintReadWrite（破坏封装）
UPROPERTY(BlueprintReadWrite)
float InternalCooldownTimer;  // 内部状态不应暴露
```

### Blueprint 约束

- Blueprint 函数节点数 **>100** 时，必须考虑拆分为 C++ 或子 Blueprint
- 禁止在 Blueprint 中做复杂数学计算（浮点精度、性能）
- Blueprint 中的 `Cast` 节点必须处理失败分支（空指针防护）

---

## GAS（Gameplay Ability System）架构模式

### 核心组件放置

| 组件 | 放置位置 | 原因 |
|------|----------|------|
| `AbilitySystemComponent` | `PlayerState` | 多人游戏中跨 Pawn 持久化 |
| `AttributeSet` | `PlayerState`（与 ASC 同持有者）| 属性复制需要 |
| `GameplayAbility` | `Source/Gameplay/Abilities/` | 按功能域组织 |
| `GameplayEffect` | `Source/Gameplay/Effects/` | 按效果类型组织 |

### GameplayTag 层级

```
Ability.Attack.Melee.Sword
Ability.Attack.Ranged.Bow
Ability.Movement.Dash
Ability.Movement.Jump
State.Buff.Invincible
State.Debuff.Stun
Event.Damage.Taken
Event.Damage.Dealt
```

- 所有 Tag 必须在 `Config/DefaultGameplayTags.ini` 中预注册
- 运行时动态添加 Tag 需经过策划确认

### Ability 实现模板

```cpp
UCLASS()
class PROJECTLUNGFISH_API UPLGA_MyAbility : public UGameplayAbility
{
    GENERATED_BODY()

public:
    UPLGA_MyAbility();

    virtual void ActivateAbility(
        const FGameplayAbilitySpecHandle Handle,
        const FGameplayAbilityActorInfo* ActorInfo,
        const FGameplayAbilityActivationInfo ActivationInfo,
        const FGameplayEventData* TriggerEventData) override;

    virtual void EndAbility(
        const FGameplayAbilitySpecHandle Handle,
        const FGameplayAbilityActorInfo* ActorInfo,
        const FGameplayAbilityActivationInfo ActivationInfo,
        bool bReplicateEndAbility,
        bool bWasCancelled) override;

protected:
    UPROPERTY(EditDefaultsOnly, Category = "PL|Ability")
    FGameplayTagContainer CancelAbilitiesWithTag;

    UFUNCTION()
    void OnMontageEnded(UAnimInstance* AnimInstance, bool bInterrupted);
};
```

---

## 命名与文件规范

### 类前缀

| 基类 | 前缀 | 示例 |
|------|------|------|
| `AActor` | `APL` | `APLCharacter`, `APLMonster` |
| `UObject` | `UPL` | `UPLAbilitySystem`, `UPLInventory` |
| `UActorComponent` | `UPL` | `UPLCombatComponent` |
| `SWidget` / Slate | `SPL` | `SPLDebugWidget` |
| `AGameModeBase` | `APL` | `APLGameMode` |
| `UUserWidget` | `UPL` | `UPLHUDWidget` |
| `UAnimInstance` | `UPL` | `UPLCharacterAnimInstance` |

### 文件规范

- **文件名 = 类名**：`APLCharacter` → `PLCharacter.h` + `PLCharacter.cpp`
- **头文件结构**：
  ```cpp
  // Copyright ...
  #pragma once
  #include "CoreMinimal.h"
  #include "GameFramework/Character.h"
  #include "PLCharacter.generated.h"
  ```
- **目录按功能域组织**：
  ```
  Source/ProjectLungfish/
  ├── Gameplay/
  │   ├── Character/
  │   ├── Ability/
  │   ├── Inventory/
  │   └── Combat/
  ├── AI/
  │   ├── Controller/
  │   ├── BehaviorTree/
  │   └── Perception/
  ├── UI/
  │   ├── HUD/
  │   └── Widget/
  └── Editor/
      └── Tools/
  ```

### 函数/变量命名

- 函数：`PascalCase`，动词开头：`ActivateAbility`, `TakeDamage`, `GetHealth`
- 变量：`camelCase`，布尔以 `b` 开头：`bIsDead`, `bCanJump`
- 常量/宏：`ALL_CAPS`
- 接口：`IPL` 前缀：`IPLInteractable`

---

## Enhanced Input 规范

### 资产组织

```
Content/Input/
├── IMC_Default.uasset      # Mapping Context（默认）
├── IMC_Combat.uasset       # Mapping Context（战斗）
├── IA_Move.uasset          # Input Action
├── IA_Look.uasset
├── IA_Jump.uasset
└── IA_Attack.uasset
```

### C++ 绑定模板

```cpp
void APLCharacter::SetupPlayerInputComponent(UInputComponent* PlayerInputComponent)
{
    Super::SetupPlayerInputComponent(PlayerInputComponent);

    if (UEnhancedInputComponent* EnhancedInput = Cast<UEnhancedInputComponent>(PlayerInputComponent))
    {
        if (APLInputConfig* InputConfig = GetInputConfig())
        {
            EnhancedInput->BindAction(InputConfig->IA_Move, ETriggerEvent::Triggered, this, &APLCharacter::Input_Move);
            EnhancedInput->BindAction(InputConfig->IA_Attack, ETriggerEvent::Started, this, &APLCharacter::Input_Attack);
        }
    }
}
```

---

## 版本控制红线

- **禁止提交**：`Binaries/`, `Intermediate/`, `Saved/`, `.tmp`, `.log`
- **必须提交**：`.uproject`, `Source/`, `Config/`, `Content/`（除自动生成的）
- **Blueprint 合并**：使用 `ue-cli-blueprint` 或编辑器内置 diff，禁止文本合并 `.uasset`

## 参考
- 模块依赖模板：`references/module-dependency-template.md`
- GAS 详细模式：`references/gas-patterns.md`
