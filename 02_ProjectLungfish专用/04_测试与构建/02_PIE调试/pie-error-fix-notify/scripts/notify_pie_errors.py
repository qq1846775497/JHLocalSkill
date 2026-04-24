"""发送 PIE 错误修复通知到飞书自动化通知群

每个错误类别发一条独立消息，包含完整修复建议和 @mention。
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

import httpx
import yaml

# ====== 配置 ======
CONFIG_PATH = Path.home() / ".feishu-cli" / "config.yaml"
GROUP_CHAT_ID = "oc_afc800ef3a9a65ae7c924795357c5240"  # 自动化通知群
PIE_ERROR_FILE = r"D:\ChaosCookOfficeMainDepot\PIEErrorList.txt"
PY_AUTOMATION_BASE = "http://192.168.2.13:5000"

# ====== 已修复的错误分类 ======
# (keyword1, keyword2, fix_group_key)
FIXED_PATTERNS = [
    ("BP_FruitsComponent", "OnRep_bIsGrowing",       "fix_fruits_onrep"),
    ("BP_FruitsComponent", "RemoveLooseGameplayTag",  "fix_fruits_onrep"),
    ("BP_FruitsComponent", "ResetGrowingStateValue",  "fix_fruits_reset"),
    ("BP_FruitsComponent", "获取属性集",               "fix_fruits_reset"),
    ("BP_FruitsComponent", "按调用者幅度分配标签集",   "fix_fruits_reset"),
    ("GA_Monster_Turn",    "Remove Warp Target",      "fix_monster_turn"),
    ("GA_Monster_Turn",    "移除扭曲目标",             "fix_monster_turn"),
    ("GA_Monster_Turn",    "GA Monster Turn",         "fix_monster_turn"),
    ("AS_Shield_Default",  None,                      "fix_shield"),
]

# ====== 待处理错误分组 ======
# 每个 group = (group_key, match_fn, title, description, owner_hint)
# match_fn(message) -> bool
PENDING_GROUPS = [
    (
        "gsc_attribute",
        lambda m: "GSCAttributeSet" in m and "doesn't seem to be granted" in m,
        "⚠️ [P0] GSCAttributeSet 未授权给 ASC — 27人受影响",
        "GSCAttributeSet（血量/蓝量/体力）在 UI 层读取时返回 0.f，原因是 GAS ASC 初始化时序问题，GSCAttributeSet 尚未 Grant 到 AbilitySystemComponent。\n"
        "修复建议：程序组排查 ASC Grant 调用时机（应在 BeginPlay / OnRep_PlayerState 之后）；"
        "确保 GrantedGameplayAbilities / GrantedAttributes 中正确包含 GSCAttributeSet。\n"
        "负责人：程序组",
        ["yuqirong", "jiangheng"],
    ),
    (
        "bt_ensure",
        lambda m: "ensureAsRuntimeWarning" in m and ("BTComponent" in m or "OwnerComp" in m or "NodeOwner" in m),
        "⚠️ [P0] BT 行为树组件为空 — ensureAsRuntimeWarning 13人触发",
        "AI 角色在销毁时行为树 Task 仍在运行，导致 BTComponent / OwnerComp / NodeOwner 为空。\n"
        "修复建议：在 AI 角色 Destroy 或 EndPlay 时主动调用 BrainComponent->StopLogic()，"
        "或在 AngelScript BT Task 的 ExecuteTask / TickTask 中加防御性判空。\n"
        "负责人：AI 程序/策划",
        ["jiangheng", "yuqirong"],
    ),
    (
        "entityrow_dtag",
        lambda m: "EntityRowToDTTag" in m and "未在" in m,
        "⚠️ [P1] EntityRowToDTTag 缺失映射 — 8种武器/物品",
        "以下 EntityRow 在 EntityRowToDTTag 中没有对应 SourceDTTag，导致本地化文本查询失败（8195次/会话）：\n"
        "  • EntityType.Hand.Axe\n"
        "  • EntityType.Hand.Axe2H\n"
        "  • EntityType.Hand.Hammer2H\n"
        "  • EntityType.Hand.Shield\n"
        "  • EntityType.Hand.Bow\n"
        "  • EntityType.Arrow\n"
        "  • EntityType.Hand.Torch\n"
        "  • EntityType.Hand.FarmHoe\n"
        "  • EntityType.Plant.Mature.Vegetable\n"
        "修复建议：策划在 EntityRowToDTTag 数据表中为以上类型补充 SourceDTTag 条目。\n"
        "负责人：策划组",
        ["liangjiahui", "zhangyichen", "shenshuo", "hanjun", "qiudesheng", "zhaoshuangyin", "yuqirong", "futianle", "hucong", "zhengdaoming"],
    ),
    (
        "ge_humidity",
        lambda m: "GE_Dmg_Humidity" in m and "SetByCaller" in m,
        "⚠️ [P1] GE_Dmg_Humidity SetByCaller 未设置",
        "GE_Dmg_Humidity 在 Apply 时以下 SetByCaller 的 Magnitude 未被上游节点赋值：\n"
        "  • SetByCaller.Liquid.Mud (254次)\n"
        "  • SetByCaller.Liquid.Oil (253次)\n"
        "  • SetByCaller.Liquid.Honey (224次)\n"
        "  • SetByCaller.Liquid.Water (217次)\n"
        "修复建议：找到所有调用 Apply GE（GE_Dmg_Humidity）的节点，在 Apply 前用 AssignSetByCallerMagnitude 赋正确的液体伤害值。\n"
        "负责人：战斗/策划",
        ["shenshuo", "zhengjiajun"],
    ),
    (
        "ge_freeze",
        lambda m: "GE_Freeze_Override" in m and "SetByCaller.Damage" in m,
        "⚠️ [P1] GE_Freeze_Override SetByCaller.Damage 未设置 — 8人",
        "GE_Freeze_Override 在 Apply 时 SetByCaller.Damage 的 Magnitude 未被赋值（101次）。\n"
        "修复建议：找到所有 ApplyGameplayEffect(GE_Freeze_Override) 的调用点，"
        "在 Apply 前用 AssignSetByCallerMagnitude 设置正确的冻结伤害值。\n"
        "负责人：战斗程序",
        ["wuqilong", "weixuanye", "sujiawei", "zhukecheng", "shiyufei", "jiangheng", "linaran", "yuqirong"],
    ),
    (
        "building_block_grid",
        lambda m: "无效运行时网格 BuildingBlock" in m or "invalid runtime grid BuildingBlock" in m,
        "⚠️ [P1] BuildingBlock 无效运行时网格 — 关卡 Actor 配置问题",
        "LI_WuNv_02SC、LI_CombatCamp_M1/M2_WP、LI_HunterShop01_S1_Script_01_WP、Sublevel_OldHunter_M1 等 LevelInstance 中"
        "大量 BP_Roof2m45_Rotten / SM_SacrificialStone / PointLight / Blockout_Box Actor 的 RuntimeGrid 属性设置为 BuildingBlock 但无效。\n"
        "修复建议：美术/关卡组打开对应 LevelInstance，选中这些 Actor，将 RuntimeGrid 清空或设置为正确的分区标签。\n"
        "负责人：关卡/美术组",
        ["zhangyichen", "majiacheng", "zhoudingqian", "sujiawei", "chengyipeng", "jianglei", "zhengjiajun", "murphy", "lvwenwei"],
    ),
    (
        "physics_material",
        lambda m: "PhysicsMaterialTag is invalid" in m,
        "⚠️ [P1] FPLBuildingBlockInfo PhysicsMaterialTag 无效 — 3人",
        "FPLBuildingBlockInfo 中 PhysicsMaterialTag 字段值无效（463次），运行时找不到对应物理材质。\n"
        "修复建议：策划/程序在 BuildingBlock 配置数据中填入正确的 PhysicsMaterialTag 枚举值或标签名。\n"
        "负责人：策划/程序",
        ["jiangheng", "shenshuo", "linaran"],
    ),
    (
        "buoyancy",
        lambda m: "AC_PLBuoyancyComponent" in m or "PLLiquidContainerComponent" in m,
        "⚠️ [P2] AC_PLBuoyancyComponent / BP_PLLiquidContainerComponent None 访问",
        "AC_PLBuoyancyComponent 在 Unbind Event (On Enter/Exit Water Delegate) 时 GetEnvironmentDataComponent 返回 None（20次）。\n"
        "BP_PLLiquidContainerComponent 在 Bind Event to On Zodiac Weather Changed 时 GetWeatherComponent 返回 None（135次）。\n"
        "修复建议：在两处 Bind/Unbind 节点前加 IsValid 保护，检查 EnvironmentDataComponent / WeatherComponent 是否有效。\n"
        "负责人：程序",
        ["wujixiang", "zhaoshuangyin", "zhengdaoming", "qiudesheng", "shiyufei", "linaran", "weixuanye"],
    ),
    (
        "ccs_main",
        lambda m: "CCS_Main" in m and ("Target" in m or "断言True" in m or "Assert True" in m),
        "⚠️ [P2] CCS_Main Target 为 None — Assert True 触发",
        "CCS_Main EventGraph 中 AssertTrue 节点以 None 作为 Target，触发蓝图运行时错误（16次）。\n"
        "修复建议：需排查 CCS_Main 的业务逻辑，确认哪个对象引用为 None；"
        "若断言保护不必要，可用 IsValid 替换；若 None 本身是 bug，需从调用链溯源修复。\n"
        "负责人：程序",
        ["jianglei", "zhangyichen", "sujiawei", "wangshenyi", "linaran", "qiaoyibing"],
    ),
    (
        "flow_component",
        lambda m: "BP_DefaultMonster" in m and "PLFlowComponent" in m,
        "⚠️ [P2] BP_DefaultMonster PLFlowComponent 为 None — 6人",
        "BP_DefaultMonster.EventGraph NotifyGraph 节点调用时 GetPLFlowComponent 返回 None（14次）。\n"
        "修复建议：检查哪些怪物 Actor 派生自 BP_DefaultMonster 但未添加 PLFlowComponent；"
        "在 NotifyGraph 节点前加 IsValid 保护，或确保所有怪物 Actor 正确配置 PLFlowComponent。\n"
        "负责人：AI 策划/程序",
        ["sujiawei", "yuqirong", "renquan", "zhukecheng", "zhangyichen", "jianglei"],
    ),
    (
        "dt_building_block",
        lambda m: "BP_PLBuilder" in m or "W_FacilityCostSider" in m or ("DT_BuildingBlockList" in m and "Row: None" in m),
        "⚠️ [P2] BP_PLBuilder / W_FacilityCostSider DT_BuildingBlockList 行缺失",
        "BP_PLBuilder.K2_OnBuildSomething 和 W_FacilityCostSider.OnChangeBuildBlock 在调用 GetDataTableRowAtName 时找不到对应行（Row: None），共 32+25+4 次。\n"
        "修复建议：策划在 DT_BuildingBlockList 数据表中补充缺失的建筑方块配置行，"
        "并确认 BP_PLBuilder / W_FacilityCostSider 传入的 Row Name 正确。\n"
        "负责人：策划/程序",
        ["wujixiang", "renquan", "wangshenyi", "zhangyichen"],
    ),
    (
        "ga_xiangliu",
        lambda m: "GA_XiangLiu_IntoCombat" in m and ("Async Action" in m or "AIController" in m or "AIPerceptionComponent" in m),
        "⚠️ [P2] GA_XiangLiu_IntoCombat AsyncAction / AIController None — 2人",
        "GA_XiangLiu_IntoCombat 中 Async Action1 / Async Action2 在 EndAbility 时为 None（8+6次），"
        "另 GetAIController / GetAIPerceptionComponent 也可能返回 None（4次）。\n"
        "修复建议：在 EndAbility 节点前检查 Async Action 是否有效（IsValid + Cancel），"
        "并对 GetAIController/GetAIPerceptionComponent 返回值加 IsValid 保护。\n"
        "负责人：AI 程序",
        ["shiyufei", "zhangyichen"],
    ),
    (
        "ga_throw",
        lambda m: "GA_Throw_Base" in m and "GetItemDefinition" in m,
        "⚠️ [P2] GA_Throw_Base GetItemDefinition 返回 None — 3人",
        "GA_Throw_Base.EventGraph 中 GetItemDefinition 节点返回 None，触发后续 Branch 蓝图错误（9次）。\n"
        "修复建议：在 Branch 节点前对 GetItemDefinition 返回值加 IsValid 检查；"
        "同时排查投掷物 Ability 触发时物品定义是否正确传入。\n"
        "负责人：战斗/程序",
        ["zhaoyiming", "jiangheng", "yuqirong"],
    ),
    (
        "ga_scouting",
        lambda m: "GA_ScoutingWraith" in m and "PLProjectileAttachConfig" in m,
        "⚠️ [P3] GA_ScoutingWraith 结构体 PLProjectileAttachConfig 未知",
        "FStructProperty Serialize 时找不到结构体 PLProjectileAttachConfig（2次），"
        "说明该结构体的 C++ 定义已被修改或删除，蓝图中遗留了旧引用。\n"
        "修复建议：若结构体已重命名，在 CoreRedirects 中添加重定向；"
        "若已删除，需要在 GA_ScoutingWraith_KickJump_success 蓝图中重建相关节点。\n"
        "负责人：程序",
        ["sujiawei", "jiangheng"],
    ),
    (
        "edit_condition",
        lambda m: "EditCondition parsing failed" in m,
        "⚠️ [P3] EditCondition 字段不存在 — Niagara / PLGameplayEffectSetByCallerInfo",
        "两处 EditCondition 解析失败：\n"
        "  • NiagaraMeshMaterialOverride 中找不到字段 bOverrideMaterials（3次）\n"
        "  • PLGameplayEffectSetByCallerInfo 中找不到字段 bUseAttributeState（2次）\n"
        "修复建议：若字段已被 C++ 删除，需在 CoreRedirects 中添加属性重定向，"
        "或重新编译并清理使用了旧字段的资产。\n"
        "负责人：程序",
        ["fengguanghao", "caoqianhao", "shenshuo", "binghao.zhao"],
    ),
    (
        "plid_bag",
        lambda m: "PLID_Entity_Bag" in m and "ActorToSpawn" in m,
        "⚠️ [P2] PLID_Entity_Bag ActorToSpawn 未配置 — 待策划确认",
        "ItemDef PLID_Entity_Bag 未设置 ActorToSpawn，Spawner 运行时静默失败（4次）。\n"
        "修复建议：策划确认 Entity Bag 应该生成哪个 Actor Blueprint，"
        "在 /Game/007_Entities/020_Treasure/PLID_Entity_Bag 中设置 ActorToSpawn 字段。\n"
        "负责人：策划",
        ["hucong", "weixuanye", "qiudesheng"],
    ),
    (
        "ge_durability",
        lambda m: "GE_Entry_AddEquipDurability" in m and "SetByCaller.Durability" in m,
        "⚠️ [P2] GE_Entry_AddEquipDurability SetByCaller.Durability 未设置 — 2人",
        "GE_Entry_AddEquipDurability Apply 时 SetByCaller.Durability 未被赋值（6次）。\n"
        "修复建议：找到所有 ApplyGameplayEffect(GE_Entry_AddEquipDurability) 的调用点，"
        "在 Apply 前用 AssignSetByCallerMagnitude 设置正确的耐久度变化值。\n"
        "负责人：装备/程序",
        ["zhaoshuangyin", "zhengdaoming"],
    ),
    (
        "inventory_null",
        lambda m: "InventoryComponent is null" in m and "RefreshInventoryComponent" in m,
        "⚠️ [P2] RefreshInventoryComponent InventoryComponent 为 None — 4人",
        "RefreshInventoryComponent 调用时 InventoryComponent 为空（36次）。\n"
        "修复建议：检查调用 RefreshInventoryComponent 的时机，确保 InventoryComponent 已经初始化；"
        "在调用前加 IsValid 保护或延迟到 BeginPlay 之后。\n"
        "负责人：程序",
        ["sujiawei", "jianglei", "zhangyichen", "shiyufei"],
    ),
    (
        "bp_yu",
        lambda m: "BP_Yu" in m and "GetEquipmentComponent" in m,
        "⚠️ [P3] BP_Yu GetEquipmentComponent 返回 None — 3人",
        "BP_Yu.EventGraph 中 GetEquipmentComponent 返回 None，Branch 节点触发错误（6次）。\n"
        "修复建议：在 Branch 前对 GetEquipmentComponent 返回值加 IsValid 保护，"
        "或排查 BP_Yu Actor 是否正确挂载了 EquipmentComponent。\n"
        "负责人：程序",
        ["zhangyichen", "jianglei", "sujiawei"],
    ),
    (
        "ga_random_move",
        lambda m: "GA_RandomMoveSpawn_yu" in m and "GetAIController" in m,
        "⚠️ [P3] GA_RandomMoveSpawn_yu GetAIController 返回 None — 3人",
        "GA_RandomMoveSpawn_yu.EventGraph '停止运动' 节点处 GetAIController 返回 None（5次）。\n"
        "修复建议：在调用 StopMovement 前加 IsValid 检查，确保 AIController 存在。\n"
        "负责人：AI 程序",
        ["sujiawei", "jianglei", "zhangyichen"],
    ),
    (
        "as_ability_eat",
        lambda m: "ASAbility_Eat" in m or "UASAbility_Eat" in m,
        "⚠️ [P3] ASAbility_Eat AngelScript 脚本错误 — 3人",
        "AngelScript 能力 ASAbility_Eat 运行时出错（IsTargetLiquid Line 246 / ConsumeEatTarget Line 362），"
        "共 5+4 次。\n"
        "修复建议：查看 Main/Saved/Logs/ProjectLungfish.log (AngelScript channel)，"
        "修复 ASAbility_Eat.as 中 IsTargetLiquid 和 ConsumeEatTarget 的逻辑错误。\n"
        "负责人：程序（AngelScript）",
        ["yuqirong", "zhengjiajun", "shenshuo"],
    ),
    (
        "hot_reload",
        lambda m: "Hot reload failed" in m and "script compile errors" in m,
        "⚠️ [P3] Hot reload 脚本编译失败 — 3人本地问题",
        "AngelScript Hot reload 编译失败，这通常是用户本地代码改动引入的错误，非共享 bug（26次）。\n"
        "修复建议：各用户检查自己本地 Main/Script/ 目录下的 .as 文件，"
        "运行编译找到并修复语法或类型错误。\n"
        "负责人：各用户自行排查",
        ["sunyuxiang", "shenshuo", "jiangheng"],
    ),
]


def is_fixed(message: str) -> str | None:
    """返回修复 group key，若未修复返回 None"""
    for keyword1, keyword2, group_key in FIXED_PATTERNS:
        if keyword1 in message:
            if keyword2 is None or keyword2 in message:
                return group_key
    return None


def get_pending_group(message: str) -> str | None:
    """返回待处理 group key，若不匹配返回 None"""
    for group_key, match_fn, *_ in PENDING_GROUPS:
        if match_fn(message):
            return group_key
    return None


def get_feishu_token() -> str:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)["default"]
    resp = httpx.post(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": cfg["app_id"], "app_secret": cfg["app_secret"]},
        timeout=30,
    )
    data = resp.json()
    if data.get("code") != 0:
        raise Exception(f"获取 token 失败: {data}")
    return data["tenant_access_token"]


def get_name_map() -> dict[str, str]:
    """P4小写用户名 → 中文全名"""
    resp = httpx.get(f"{PY_AUTOMATION_BASE}/content_manager/users", timeout=15)
    data = resp.json()
    result = {}
    for u in data.get("result", []):
        result[u["name"].lower()] = u["full_name"]
    return result


def get_feishu_uid(p4_name: str) -> str | None:
    try:
        resp = httpx.get(
            f"{PY_AUTOMATION_BASE}/user/get_feishu_userid",
            params={"users": p4_name},
            timeout=10,
        )
        data = resp.json()
        if data.get("status", {}).get("code") == 0:
            uids = data.get("result", [])
            if uids:
                return uids[0]
    except Exception as e:
        print(f"  [警告] 查询 {p4_name} open_id 失败: {e}", file=sys.stderr)
    return None


def make_at(open_id: str | None, name: str) -> str:
    if open_id:
        return f'<at user_id="{open_id}">{name}</at>'
    return name


def build_at_str(user_lowers: set, name_map: dict, uid_map: dict) -> str:
    parts = []
    for u in sorted(user_lowers):
        cn = name_map.get(u, u)
        uid = uid_map.get(u)
        parts.append(make_at(uid, cn))
    return " ".join(parts)


def send_message(token: str, text: str) -> str:
    content = json.dumps({"text": text}, ensure_ascii=False)
    resp = httpx.post(
        "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        json={
            "receive_id": GROUP_CHAT_ID,
            "msg_type": "text",
            "content": content,
        },
        timeout=30,
    )
    data = resp.json()
    if data.get("code") != 0:
        raise Exception(f"发送失败: {data.get('msg')}")
    return data["data"]["message_id"]


def main():
    print("读取 PIEErrorList.txt ...")
    errors = []
    with open(PIE_ERROR_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                errors.append(json.loads(line))
    print(f"共 {len(errors)} 条错误记录")

    # 收集所有用户
    all_users_lower = set()
    for e in errors:
        for u in e["user_list"]:
            all_users_lower.add(u.lower())

    print(f"涉及用户 {len(all_users_lower)} 人，获取映射中 ...")
    name_map = get_name_map()
    uid_map: dict[str, str | None] = {}
    for u in sorted(all_users_lower):
        uid = get_feishu_uid(u)
        uid_map[u] = uid
        print(f"  {'✓' if uid else '✗'} {u} → {uid or '未找到'}")

    # ====== 分类 ======
    # 已修复：group_key → set of users
    fixed_users: dict[str, set] = defaultdict(set)
    # 待处理：group_key → set of users（从错误数据动态收集）
    pending_users: dict[str, set] = defaultdict(set)

    for e in errors:
        msg = e["message"]
        users = {u.lower() for u in e["user_list"]}

        fix_key = is_fixed(msg)
        if fix_key:
            fixed_users[fix_key].update(users)
            continue

        pg_key = get_pending_group(msg)
        if pg_key:
            pending_users[pg_key].update(users)

    # ====== 构建消息列表 ======
    messages = []

    # --- 开篇总结消息 ---
    messages.append(
        "【PIE 错误修复通知】2026-04-09\n\n"
        "以下将逐条发送本次 PIE 错误的修复状态和建议，共 4 条已修复 + 20 类待处理。\n"
        "CL 87282（待提交）包含已修复的蓝图改动。"
    )

    # --- 已修复：4条，每条一消息 ---
    fixed_meta = {
        "fix_fruits_onrep": (
            "✅ [已修复] BP_FruitsComponent — OnRep_bIsGrowing ASC 空指针 CL 87282",
            "错误：GetPLAbilitySystemComponent() 返回值未加判空，直接连入 RemoveLooseGameplayTag / AddLooseGameplayTag，ASC 为 None 时崩溃（240次）。\n"
            "修复：在 bIsGrowing Branch 节点前插入 KismetSystemLibrary::IsValid 检查 ASC，ASC 为 None 时静默返回。\n"
            "修改文件：Main/Content/Blueprint/Components/BP_FruitsComponent.uasset（CL 87282）"
        ),
        "fix_fruits_reset": (
            "✅ [已修复] BP_FruitsComponent — ResetGrowingStateValue ASC 空指针 CL 87282",
            "错误：GetAbilitySystemComponent() 返回值未加判空，直接作为 self 传入 MakeOutgoingSpec，ASC 为 None 时崩溃（91+76次）。\n"
            "修复：在执行链最前端插入 IsValid 检查 ASC，ASC 为 None 时静默跳过整个函数。\n"
            "修改文件：Main/Content/Blueprint/Components/BP_FruitsComponent.uasset（CL 87282）"
        ),
        "fix_monster_turn": (
            "✅ [已修复] GA_Monster_Turn — RemoveWarpTarget 数组空指针 CL 87282",
            "错误：GET[0](MotionWarpingComponents 数组) 在数组为空时返回 None，直接连入 RemoveWarpTarget，导致 None 访问（269+64次）。\n"
            "修复：在 EndAbility.then → RemoveWarpTarget.execute 之间插入 IsValid 检查 Component，Component 为 None 时跳过。\n"
            "修改文件：Main/Content/013_AI/000_Template/GA/GA_Monster_Turn.uasset（CL 87282）"
        ),
        "fix_shield": (
            "✅ [已修复] AS_Shield_Default — 2条空 Ability 引用已清除 CL 87282",
            "错误：GrantedGameplayAbilities 数组 index 9、10 的 Ability 字段为 None，GAS Grant 时失败（14次）。\n"
            "修复：Python 脚本删除 2 条空条目，数组从 11 → 9 个有效条目。\n"
            "修改文件：Main/Content/007_Entities/011_Weapon/Shield/ShieldConfig/AS_Shield_Default.uasset（CL 87282）"
        ),
    }

    for fix_key, (title, desc) in fixed_meta.items():
        users = fixed_users.get(fix_key, set())
        at_str = build_at_str(users, name_map, uid_map)
        msg = f"{title}\n\n{desc}\n\n影响人员：{at_str}"
        messages.append(msg)

    # --- 待处理：每类一消息 ---
    for group_key, match_fn, title, description, default_users in PENDING_GROUPS:
        # 优先用从错误数据收集到的用户，不足时用 default_users 补充
        data_users = pending_users.get(group_key, set())
        # 合并默认用户（来自 PIEErrorFixes.md 分析）
        all_g_users = data_users | {u.lower() for u in default_users}
        at_str = build_at_str(all_g_users, name_map, uid_map)
        msg = f"{title}\n\n{description}\n\n相关人员：{at_str}"
        messages.append(msg)

    # ====== 预览 ======
    print(f"\n共 {len(messages)} 条消息待发送：")
    for i, m in enumerate(messages):
        print(f"\n--- 消息 {i+1}/{len(messages)} ---")
        print(m[:400])
        if len(m) > 400:
            print("...(截断预览)")
    print("\n" + "="*60)

    confirm = input("\n确认发送全部消息到自动化通知群？(y/n): ").strip().lower()
    if confirm != "y":
        print("已取消")
        return

    print("获取 Feishu token ...")
    token = get_feishu_token()

    print(f"发送 {len(messages)} 条消息 ...")
    for i, text in enumerate(messages):
        msg_id = send_message(token, text)
        print(f"  [{i+1}/{len(messages)}] 发送成功 message_id: {msg_id}")

    print("\n全部发送完成！")


if __name__ == "__main__":
    main()
