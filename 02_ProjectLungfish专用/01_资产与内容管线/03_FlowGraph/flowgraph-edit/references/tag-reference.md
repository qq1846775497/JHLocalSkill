# FlowGraph GameplayTag Reference

Tag hierarchy and conventions used across FlowGraph nodes. Tags follow UE5 GameplayTag dot-notation (`Parent.Child.Grandchild`).

---

## Root Tag Prefixes

| Prefix | Usage Context | Example |
|--------|--------------|---------|
| `Character` | Actor identity (player, NPCs) | `Character.Player` |
| `NPC` | NPC identity subtypes | `NPC.Wunv`, `NPC.Reminisce` |
| `Monster` | Monster identity | `Monster.Wolf`, `Monster.Bear` |
| `Entity` | World objects, items, structures | `Entity.Campfire`, `Entity.Bed` |
| `Environment` | Weather, geography, calendar | `Environment.Weather.OpenRain` |
| `GameplayEvent` | Event dispatch tags | `GameplayEvent.PlayAction` |
| `GameplayEffect` | Status effects, phases | `GameplayEffect.PhaseStatus.Burn` |
| `PLPhaseType` | Phase attributes | `PLPhaseType.Stamina` |
| `InputTag` | Player input actions | `InputTag.Narrative.Interact` |
| `FlowNode` | FlowGraph task/asset tags | `FlowNode.Task.Guide` |
| `Ability` | GAS ability classes | `Ability.Montage.Attack` |
| `AssetTag` | Asset identification | `AssetTag.FlowNode.Task` |
| `SM` | Static mesh entity tags | `SM.Rock`, `SM.Tree` |
| `Plate` | Plate/container entity tags | `Plate.Wood`, `Plate.Stone` |
| `ActionChain` | Action chain step identification | `ActionChain.Step1`, `ActionChain.Harvest` |
| `Achievement` | Achievement/milestone tags | `Achievement.FirstCampfire`, `Achievement.FirstHunt` |
| `Equipment` | Equipment slot/type tags | `Equipment.Weapon.Sword`, `Equipment.Armor.Chest` |
| `Persona` | Character persona/state | `Persona.Happy`, `Persona.Angry` |
| `Calendar` | Calendar day/season tags | `Calendar.Season.Spring`, `Calendar.Day.1` |

---

## Character Tags

Used in `IdentityTags` to target specific actors.

| Tag | Usage Count | Notes |
|-----|-------------|-------|
| `Character.Player` | ~938 | Most common — targets the player character |
| `NPC.Wunv` | ~637 | Main NPC companion |
| `NPC.Reminisce` | ~99 | Reminisce NPC |
| `NPC.OldHunter` | ~47 | Old Hunter NPC |
| `NPC.Deer` | ~30 | Deer companion |
| `Monster.*` | varies | Monster types for combat encounters |

---

## Entity Tags

Used in `IdentityTags`, `EntityTags`, `TriggeredActorTags` to match world objects.

| Tag | Context |
|-----|---------|
| `Entity.Campfire` | Campfire detection (OnActorRegistered, ConsumeEntity) |
| `Entity.Bed` | Bed/sleeping interactions |
| `Entity.Torch` | Torch/light source |
| `Entity.Wood` | Wood resource |
| `Entity.Stone` | Stone resource |
| `Plate.Wood` | Wooden plate/container |
| `Plate.Stone` | Stone plate/container |
| `SM.Rock` | Static mesh rock |
| `SM.Tree` | Static mesh tree |

---

## Environment Tags

### Weather
Used in `WeatherTag` property on `FN_ChangeWeather_C` nodes.

| Tag | Description |
|-----|-------------|
| `Environment.Weather.StartCave` | Cave starting weather |
| `Environment.Weather.OpenRain` | Open area rain |
| `Environment.Weather.Clear` | Clear weather |
| `Environment.Weather.Fog` | Foggy weather |

### Geography (POI)
Used in `TriggeredActorTags` on trigger nodes.

| Tag | Description |
|-----|-------------|
| `Environment.Geography.POI.*` | Point of interest triggers |
| `Environment.Geography.Biome.*` | Biome region tags |

### Calendar
Used as dynamic output pins on `FlowNode_ListenTimeChange`.

| Tag | Description |
|-----|-------------|
| `Environment.Calendar.ZodiacHour.Zi` | Midnight hour |
| `Environment.Calendar.ZodiacHour.Chou` | 1-3 AM |
| `Environment.Calendar.ZodiacHour.Yin` | 3-5 AM |
| `Environment.Calendar.ZodiacHour.Mao` | 5-7 AM |
| `Environment.Calendar.ZodiacHour.Chen` | 7-9 AM |
| `Environment.Calendar.ZodiacHour.Si` | 9-11 AM |
| `Environment.Calendar.ZodiacHour.Wu` | 11 AM-1 PM |
| `Environment.Calendar.ZodiacHour.Wei` | 1-3 PM |
| `Environment.Calendar.ZodiacHour.Shen` | 3-5 PM |
| `Environment.Calendar.ZodiacHour.You` | 5-7 PM |
| `Environment.Calendar.ZodiacHour.Xu` | 7-9 PM |
| `Environment.Calendar.ZodiacHour.Hai` | 9-11 PM |

---

## Event Tags

Used in `EventTag` property on action nodes and `TriggerByEventTag` on montage nodes.

| Tag | Context |
|-----|---------|
| `GameplayEvent.PlayAction` | Trigger ability/montage playback |
| `GameplayEvent.StartDialogue` | Start dialogue sequence |
| `GameplayEvent.Dead` | Actor death event |
| `GameplayEvent.Interact` | Interaction event |
| `InputTag.Narrative.Interact` | Player narrative interaction input |
| `InputTag.Narrative.Skip` | Player skip input |

---

## Asset & Task Tags

Used in `RegisterTaskTag`, `GroupTagToComplete`, `assetTag` (payload).

| Tag | Context |
|-----|---------|
| `FlowNode.Task.Guide.*` | Guide/tutorial task registration |
| `FlowNode.Task.Quest.*` | Quest task registration |
| `AssetTag.FlowNode.Task` | Asset identification for flow tasks |
| `Ability.Montage.*` | Montage ability class tags |

---

## Tag-to-Property Mapping

Which tags go in which node properties:

| Property | Expected Tag Prefix | Node Classes |
|----------|-------------------|--------------|
| `IdentityTags` | `Character.*`, `NPC.*`, `Monster.*`, `Entity.*` | All observer/action nodes |
| `EventTag` | `GameplayEvent.*` | ExecuteCustomEventOnActor, PlayMontageAction |
| `TriggerByEventTag` | `GameplayEvent.*` | PlayMontageAction |
| `WeatherTag` | `Environment.Weather.*` | FN_ChangeWeather_C |
| `TriggeredActorTags` | `Environment.Geography.*`, `Entity.*` | OnTriggerEnter/Exit |
| `TagsToAdd` / `TagsToRemove` | Any | FN_SetGameplayTag |
| `AttributeTag` | `PLPhaseType.*` | ModifyPhaseAttribute |
| `ListenAddedTags` / `ListenRemovedTags` | `GameplayEffect.*`, any | ListenTagChanged |
| `RegisterTaskTag` | `FlowNode.Task.*` | FlowNode_GuideTask |
| `GroupTagToComplete` | `FlowNode.Task.*` | FlowNode_GuideTask |
| `InteractionTag` | `InputTag.*`, `GameplayEvent.*` | FN_ListenPlayerAction |
| `NotifyTags` | Any | FlowNode_OnNotifyFromActor |
| `TargetActorTag` | `Entity.*`, `Environment.*` | FN_AIMoveToByTag, FlowNode_Teleport |
| `EntityTags` | `Entity.*` | FlowNode_ConsumeEntityInWorld |
| `SkipDialogueInteractionTag` | `InputTag.Narrative.*` | Dialogue nodes |
| `DesiredGaitTagAtStart/End` | `Ability.Gait.*` | FN_AIMoveToByTag |
| `ActionNodeTags` | `ActionChain.*` | FlowNode_ActionChain |
| `AchievementTag` | `Achievement.*` | FlowNode_ListenAchievement, FlowNode_HasAchievement |
| `EquipTag` | `Equipment.*` | FlowNode_ListenEquip, FlowNode_EquipEntity |
| `AbilityClass` | `Ability.*` | FlowNode_ListenGameplayAbility, FlowNode_TriggerAbility |
| `ZodiacHourTag` | `Environment.Calendar.ZodiacHour.*` | FlowNode_QuickSwitchZodiacHourByTag, FlowNode_WaitForZodiacHourTag |
| `DayTag` | `Calendar.Day.*` | FlowNode_WaitForDayTag |
| `SpawnTag` | `Entity.*` | FlowNode_SpawnByGameplayTag |
| `FlowAsset` (tag) | `AssetTag.FlowNode.*` | FlowNode_StartRootFlow |
| `PickUpTag` | `Entity.*` | FlowNode_ListenPickUp |
| `ItemTag` | `Entity.*` | FlowNode_ListenItemGiven |
