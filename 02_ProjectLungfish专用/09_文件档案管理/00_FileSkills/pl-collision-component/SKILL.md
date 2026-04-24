---
id: pl-collision-component
file_path: D:\jiangheng\JiangHengWork\Main\Plugins\GASExtendedPL\Source\GASExtendedPL\Private\Collision\PLCollisionComponent.cpp
trigger_words:
  - PLCollisionComponent
  - UPLCollisionComponent
  - StartCollision
  - MulticastStartCollision
  - InternalStartCollision
  - DoCollisionTrace
functions:
  - UPLCollisionComponent::StartCollision
  - UPLCollisionComponent::MulticastStartCollision
  - UPLCollisionComponent::InternalStartCollision
  - UPLCollisionComponent::DoCollisionTrace
  - UPLCollisionComponent::EndCollision
history:
  - date: "2026-04-24"
    requirement: "CharacterNPC Collision 网络同步改造：NPC 的碰撞需要广播到所有端，服务器处理全部，客户端只处理本地 player"
    changes: >
      1. 新增 MulticastStartCollision (NetMulticast) 和 InternalStartCollision 私有函数
      2. StartCollision_Implementation 中对 APLCharacterNPC 判断：Authority 时调用 MulticastStartCollision 广播到所有端
      3. DoCollisionTrace 中对 CharacterNPC 做客户端过滤：非 Authority 时只保留 IsLocallyControlled 的 Player
    functions_affected:
      - UPLCollisionComponent::StartCollision
      - UPLCollisionComponent::MulticastStartCollision
      - UPLCollisionComponent::InternalStartCollision
      - UPLCollisionComponent::DoCollisionTrace
  - date: "2026-04-24"
    requirement: "修正 StartCollision RPC 逻辑：Client RPC 的 _Implementation 中无法正确判断 HasAuthority()"
    changes: >
      1. StartCollision 改为普通 BlueprintCallable 函数（去掉 Client RPC 标记）
      2. 新增 ServerStartCollision (Server RPC) 和 ClientStartCollision (Client RPC)
      3. StartCollision 调用时立即本地执行 InternalStartCollision，再根据 Owner 类型分发：
         - NPC + Authority：MulticastStartCollision
         - NPC + Client：ServerStartCollision → 服务器收到后 Multicast
         - Player：ClientStartCollision（保持原有行为）
      4. Multicast/Client 的 _Implementation 中利用 ActivatedCollisionRecords 防重复执行
    functions_affected:
      - UPLCollisionComponent::StartCollision
      - UPLCollisionComponent::ServerStartCollision
      - UPLCollisionComponent::ClientStartCollision
      - UPLCollisionComponent::MulticastStartCollision
      - UPLCollisionComponent::InternalStartCollision
  - date: "2026-04-24"
    requirement: "修复 Multicast 发不到客户端 + StartMultiple/StartAll 一致性 + SimulatedProxy 不发 Server RPC"
    changes: >
      1. 构造函数 SetIsReplicated(false) → true，修复组件 NetMulticast 无法发送到客户端
      2. StartMultipleCollision / StartAllCollision 去掉 Client RPC 标记，改为普通函数
      3. StartCollision 中 ServerStartCollision 调用前增加 GetOwnerRole() == ROLE_AutonomousProxy 判断
         - SimulatedProxy 不发 Server RPC（UE 硬限制），本地已执行 InternalStartCollision
         - 服务器 AnimNotify 触发 Multicast 覆盖所有端，防重复由 ActivatedCollisionRecords 保证
    functions_affected:
      - UPLCollisionComponent::StartCollision
      - UPLCollisionComponent::StartMultipleCollision
      - UPLCollisionComponent::StartAllCollision
      - UPLCollisionComponent::ServerStartCollision
      - UPLCollisionComponent::MulticastStartCollision
  - date: "2026-04-24"
    requirement: "EndCollision / EndMultiple / EndAll / RemoveIgnoreActor 同步改为普通函数 + RPC 分发"
    changes: >
      1. EndCollision / EndMultipleCollision / EndAllCollision / RemoveIgnoreActor 去掉 Client RPC 标记，改为普通函数
      2. 新增 ServerEndCollision / ClientEndCollision / MulticastEndCollision / InternalEndCollision
      3. 新增 ServerRemoveIgnoreActor / ClientRemoveIgnoreActor / MulticastRemoveIgnoreActor / InternalRemoveIgnoreActor
      4. 统一模式：本地执行 InternalXxx → 根据 Owner 类型分发（NPC Authority→Multicast, NPC Autonomous→Server, Player→Client）
    functions_affected:
      - UPLCollisionComponent::EndCollision
      - UPLCollisionComponent::EndMultipleCollision
      - UPLCollisionComponent::EndAllCollision
      - UPLCollisionComponent::RemoveIgnoreActor
      - UPLCollisionComponent::ServerEndCollision
      - UPLCollisionComponent::MulticastEndCollision
      - UPLCollisionComponent::ServerRemoveIgnoreActor
      - UPLCollisionComponent::MulticastRemoveIgnoreActor
---

# PLCollisionComponent.cpp 档案

## 文件概述
碰撞检测核心组件，支持基于 GameplayTag 的碰撞配置、Socket/Capsule 射线检测、预测、伤害结算、以及网络同步。

## 关键函数/类
- `UPLCollisionComponent` - 碰撞组件
- `StartCollision` - 启动碰撞检测（Client RPC）
- `MulticastStartCollision` - NPC 专用广播启动
- `InternalStartCollision` - 公共实现
- `DoCollisionTrace` - 每帧执行射线检测并结算命中

## 修改历史
<!-- 按时间倒序，每次修改后自动追加 -->
