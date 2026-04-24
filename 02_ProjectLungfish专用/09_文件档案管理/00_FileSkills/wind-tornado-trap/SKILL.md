---
id: wind-tornado-trap
file_path: D:\jiangheng\JiangHengWork\Main\Script\Gameplay\Actors\WindTornadoTrap.as
trigger_words:
  - WindTornadoTrap.as
  - AWindTornadoTrap
  - FWhirlwindPhaseDamageEntry
  - PhaseDamageEntries
functions:
  - AWindTornadoTrap
  - FWhirlwindPhaseDamageEntry
  - BeginPlay
  - DeferredBeginPlaySetup
  - EndPlay
  - Tick
  - UpdateMoveDirection
  - RefreshDamageAoe
  - SpawnDamageAoe
  - RemoveDamageAoe
  - ConfigureDamageAoe
  - SyncSpecificDamageAoeToTornadoCapsule
  - OnCurrentDamageAoeDoDamage
  - OnWhirlwindPhaseTagAdded
  - OnWhirlwindPhaseTagRemoved
  - OnMeshWindEntered
  - OnMeshWindExited
  - OnWindStateChanged
  - ApplyWindResponse
  - OnDetectionBeginOverlap
  - OnDetectionEndOverlap
  - TryHandleWindBlade
  - TryHandleProjectile
  - TryHandleCharacter
  - SetDamageAoeCasterActor
  - GetDamageAoeCasterActor
  - SetPhaseShifted
  - AddPhaseShiftStack
  - StartPhaseShiftDisappearCountdown
  - CancelPhaseShiftDisappearCountdown
  - TriggerPhaseShiftDisappearExplosion
  - SpawnPhaseShiftExplosionAoe
  - BuildMergedDamageTypeCollector
  - AddOrAccumulateDamageTypeValue
  - AddPhaseDamageEntry
  - RemovePhaseDamageEntry
  - ClearPhaseDamageEntries
  - OnPhaseShiftStateChanged
  - OnPhaseShiftPrepareDisappearStarted
  - OnPhaseShiftExplosionTriggered
  - OnPhaseShiftBossHit
  - UpdateNiagaraParameterTransition
  - ClearNiagaraParameterTransition
constraints:
  - 相变伤害条目(FWhirlwindPhaseDamageEntry)使用UPROPERTY暴露给编辑器配置，每个条目独立控制一个Niagara参数
  - Niagara参数过渡通过Tick逐帧线性插值实现，不使用Timer
  - 相变清除(SetPhaseShifted(false)/EndPlay)时必须调用ClearNiagaraParameterTransition将参数重置为0
  - 多条目参数名切换时，旧参数先清0再启动新参数过渡
history:
  - date: "2026-04-24"
    requirement: "在相变伤害条目中增加Niagara参数控制，相变时将指定参数从0线性过渡到1，支持配置过渡时间"
    changes: >
      1. FWhirlwindPhaseDamageEntry新增NiagaraFloatParameterName(FName)和NiagaraParameterTransitionTime(float)两个字段
      2. AWindTornadoTrap新增ActiveNiagaraParameterName、NiagaraTransitionElapsed、NiagaraTransitionDuration、bIsNiagaraTransitioning四个运行时状态
      3. Tick末尾增加UpdateNiagaraParameterTransition调用，实现每帧0→1线性插值
      4. OnWhirlwindPhaseTagAdded匹配条目后启动过渡；过渡时间为0时立即设为1
      5. SetPhaseShifted(false)和EndPlay中调用ClearNiagaraParameterTransition清0
      6. 新增UpdateNiagaraParameterTransition和ClearNiagaraParameterTransition两个辅助函数
    functions_affected:
      - FWhirlwindPhaseDamageEntry
      - Tick
      - OnWhirlwindPhaseTagAdded
      - SetPhaseShifted
      - EndPlay
      - UpdateNiagaraParameterTransition
      - ClearNiagaraParameterTransition
    regression_detected: false
---

# WindTornadoTrap.as 档案

## 文件概述
旋风陷阱Actor的AngelScript实现，继承自APLActorGAS。负责旋风的移动、风场交互、玩家击飞、投射物拦截、相变伤害AOE生成与Niagara特效参数控制。

## 关键函数/类

### 结构体
- **FWhirlwindPhaseDamageEntry**：相变伤害条目，包含PhaseTag、DamageDataAsset、Niagara参数名与过渡时间

### 核心生命周期
- **BeginPlay / DeferredBeginPlaySetup**：初始化移动方向、绑定碰撞/风场/相变事件、生成常态伤害AOE
- **EndPlay**：解绑事件、清理AOE、清Niagara参数
- **Tick**：移动更新 + Niagara参数过渡更新

### 移动与风场
- **UpdateMoveDirection**：插值平滑转向
- **ApplyWindResponse**：计算外部风对移动方向的影响
- **OnMeshWindEntered / OnMeshWindExited / OnWindStateChanged**：风场事件回调

### 伤害AOE
- **RefreshDamageAoe**：根据相变状态生成/移除常态或相变伤害AOE
- **SpawnDamageAoe**：创建并配置内部伤害AOE，附加到旋风胶囊体
- **SpawnPhaseShiftExplosionAoe**：相变消失时生成爆炸AOE
- **OnCurrentDamageAoeDoDamage**：命中Boss时触发旋风自毁

### 相变系统
- **OnWhirlwindPhaseTagAdded**：PhaseTag匹配时加载伤害DA、启动Niagara参数过渡、叠加相变层数
- **OnWhirlwindPhaseTagRemoved**：减少激活计数（不移除相变）
- **SetPhaseShifted**：外部控制相变开关，false时清Niagara参数并重置状态
- **AddPhaseShiftStack**：增加相变层数，首次相变触发状态变更事件
- **StartPhaseShiftDisappearCountdown / TriggerPhaseShiftDisappearExplosion**：相变后延迟爆炸自毁

### Niagara参数过渡（新增）
- **UpdateNiagaraParameterTransition**：Tick中每帧更新，线性插值0→1
- **ClearNiagaraParameterTransition**：将相变参数重置为0并清空过渡状态

### 碰撞交互
- **OnDetectionBeginOverlap**：检测风刃/投射物/玩家/可投掷Actor
- **TryHandleWindBlade**：增强穿过的风刃投射物
- **TryHandleProjectile**：延迟销毁进入的投射物
- **TryHandleCharacter**：击飞玩家并发送GameplayEvent

## 设计约束（constraints）
- 相变伤害条目(FWhirlwindPhaseDamageEntry)使用UPROPERTY暴露给编辑器配置，每个条目独立控制一个Niagara参数
- Niagara参数过渡通过Tick逐帧线性插值实现，不使用Timer
- 相变清除(SetPhaseShifted(false)/EndPlay)时必须调用ClearNiagaraParameterTransition将参数重置为0
- 多条目参数名切换时，旧参数先清0再启动新参数过渡

## 修改历史
<!-- 按时间倒序，每次修改后自动追加 -->
