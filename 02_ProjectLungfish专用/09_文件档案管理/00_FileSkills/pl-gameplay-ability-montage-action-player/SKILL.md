---
id: pl-gameplay-ability-montage-action-player
file_path: D:\jiangheng\JiangHengWork\Main\Plugins\GASExtendedPL\Source\GASExtendedPL\Private\AbilitySystem\Abilities\PLGameplayAbility_MontageActionPlayer.cpp
trigger_words:
  - PLGameplayAbility_MontageActionPlayer
  - UPLGameplayAbility_MontageActionPlayer
  - MontageActionPlayer
  - ActivateAbility
functions:
  - UPLGameplayAbility_MontageActionPlayer::ActivateAbility
  - UPLGameplayAbility_MontageActionPlayer::DefaultActionMontageProcess
history:
  - date: "2026-04-24"
    requirement: "NPC GA LocalPredicted 支持：让 NPC 的 Montage GA 能在 Owning Client 本地预测执行"
    changes: >
      1. 重写 ActivateAbility，添加 NPC + LocalPredicted 自动通知逻辑
      2. 服务器 Authority + LocalPredicted + Avatar 是 APLCharacterNPC 时，调用 ClientPredictActivateAbility
      3. Owning Client 收到后 TryActivateAbilityByClass，走 LocalPredicted 预测分支
    functions_affected:
      - UPLGameplayAbility_MontageActionPlayer::ActivateAbility
---

# PLGameplayAbility_MontageActionPlayer.cpp 档案

## 文件概述
Montage 动作 GA 的核心实现类，继承自 UPLGameplayAbility_MontageAction。处理战斗动作的蒙太奇播放、体力恢复阻塞、根运动缩放、跳跃能力、输入缓冲、阶段管理等。

## 关键函数/类
- `UPLGameplayAbility_MontageActionPlayer` - Montage 动作 GA 基类
- `ActivateAbility` - 重写：添加 NPC LocalPredicted 自动通知客户端
- `DefaultActionMontageProcess` - 默认蒙太奇处理流程

## 修改历史
<!-- 按时间倒序，每次修改后自动追加 -->
