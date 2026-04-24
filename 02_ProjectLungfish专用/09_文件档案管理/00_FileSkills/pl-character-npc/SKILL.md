---
id: pl-character-npc
file_path: D:\jiangheng\JiangHengWork\Main\Plugins\GASExtendedPL\Source\GASExtendedPL\Private\Character\PLCharacterNPC.cpp
trigger_words:
  - PLCharacterNPC
  - APLCharacterNPC
  - MonsterOwner
  - SetMonsterOwner
functions:
  - APLCharacterNPC::GetLifetimeReplicatedProps
  - APLCharacterNPC::SetMonsterOwner
  - APLCharacterNPC::OnRep_MonsterOwner
  - APLCharacterNPC::BeginPlay
history:
  - date: "2026-04-24"
    requirement: "NPC GA LocalPredicted 支持：让 NPC 的 Montage GA 能在 Owning Client 本地预测执行"
    changes: >
      1. 新增 ClientPredictActivateAbility(Client, Reliable) RPC，Owning Client 收到后调用 ASC->TryActivateAbilityByClass
      2. SetMonsterOwner 中添加 SetAutonomousProxy(true)，使 Owning Client 上 NPC 的 Role = AutonomousProxy
      3. SetMonsterOwner / OnRep_MonsterOwner 中重新 InitAbilityActorInfo(PC, this)，使 ActorInfo.PlayerController 正确填充
    functions_affected:
      - APLCharacterNPC::SetMonsterOwner
      - APLCharacterNPC::OnRep_MonsterOwner
      - APLCharacterNPC::ClientPredictActivateAbility
  - date: "2026-04-24"
    requirement: "CharacterNPC Collision 网络同步改造：添加 MonsterOwner 复制属性，解决 SetOwner 不同步问题"
    changes: "添加 MonsterOwner (ReplicatedUsing=OnRep_MonsterOwner)，SetMonsterOwner 在 Authority 时同步 SetOwner，OnRep 在客户端也 SetOwner，BeginPlay 默认设置为 LS Host Player"
    functions_affected:
      - APLCharacterNPC::GetLifetimeReplicatedProps
      - APLCharacterNPC::SetMonsterOwner
      - APLCharacterNPC::OnRep_MonsterOwner
      - APLCharacterNPC::BeginPlay
---

# PLCharacterNPC.cpp 档案

## 文件概述
非玩家角色基类（怪物、NPC），管理动画覆盖、出生/死亡逻辑、AI 控制器、以及 MonsterOwner 网络同步。

## 关键函数/类
- `APLCharacterNPC` - NPC 基类
- `SetMonsterOwner` - 服务器设置 MonsterOwner 并 SetOwner
- `OnRep_MonsterOwner` - 客户端收到复制后 SetOwner

## 修改历史
<!-- 按时间倒序，每次修改后自动追加 -->
