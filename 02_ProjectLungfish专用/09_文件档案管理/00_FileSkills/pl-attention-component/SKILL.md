---
id: pl-attention-component
file_path: D:\jiangheng\JiangHengWork\Main\Plugins\GASExtendedPL\Source\GASExtendedPL\Private\AI\Attention\PLAttentionComponent.cpp
trigger_words:
  - PLAttentionComponent
  - UPLAttentionComponent
  - OnHighestAttentionActorChanged
functions:
  - UPLAttentionComponent::OnHighestAttentionActorChanged
  - UPLAttentionComponent::GetHighestAttentionActor
  - UPLAttentionComponent::RefreshEngageActor
history:
  - date: "2026-04-24"
    requirement: "CharacterNPC Collision 网络同步改造：Attention 组件将仇恨值最高的 player 设为 NPC Owner"
    changes: "在 OnHighestAttentionActorChanged 中，当 Owner 是 APLCharacterNPC 时，调用 SetMonsterOwner 切换 Owner；无仇恨目标时恢复为 LS Host Player"
    functions_affected:
      - UPLAttentionComponent::OnHighestAttentionActorChanged
---

# PLAttentionComponent.cpp 档案

## 文件概述
AI 仇恨/注意力系统，管理 NPC 对周围目标的注意力排序、战斗状态通知、以及 Group Attention 同步。

## 关键函数/类
- `UPLAttentionComponent` - 注意力组件
- `OnHighestAttentionActorChanged` - 最高仇恨目标变化回调

## 修改历史
<!-- 按时间倒序，每次修改后自动追加 -->
