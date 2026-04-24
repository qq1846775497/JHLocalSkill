# FlowGraph Node Catalogue

Pin layouts and default property templates for all commonly used FlowGraph node classes.
All pin names verified against actual JSON exports.

> **Class path formats:**
> - C++ native: `/Script/ModuleName.ClassName`
> - Blueprint: `/PluginPath/Nodes/ClassName.ClassName_C`

---

## Table of Contents

- [Control Flow Nodes](#control-flow-nodes)
- [Dialogue & UI Nodes](#dialogue--ui-nodes)
- [Gameplay Action Nodes](#gameplay-action-nodes)
- [Actor Condition Nodes](#actor-condition-nodes)
- [AI & Movement Nodes](#ai--movement-nodes)
- [Listener / Observer Nodes](#listener--observer-nodes)
- [Calendar & Weather Nodes](#calendar--weather-nodes)
- [Spawn & Entity Nodes](#spawn--entity-nodes)
- [SubGraph & Flow Control Nodes](#subgraph--flow-control-nodes)
- [World & Utility Nodes](#world--utility-nodes)
- [Existing Blueprint Nodes](#existing-blueprint-nodes)
- [Observer Mixin (Shared Properties)](#observer-mixin-shared-properties)
- [Empty Payload Template](#empty-payload-template)

---

## Control Flow Nodes

### FlowNode_Start
**Class:** `/Script/Flow.FlowNode_Start`
**Purpose:** Entry point — exactly one per FlowAsset. Fires on graph activation.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Output | `Out` | Exec | Fires when graph starts |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| OutputProperties | — | — | Standard output config |

---

### FlowNode_ExecutionSequence
**Class:** `/Script/Flow.FlowNode_ExecutionSequence`
**Purpose:** Fires numbered outputs in order (0, 1, 2, ...). Use for parallel branches.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `In` | Exec | Trigger |
| Output | `0` | Exec | First branch |
| Output | `1` | Exec | Second branch |
| Output | `2` | Exec | Third branch (add more as needed) |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| bSavePinExecutionState | bool | false | Persist which pins have fired across saves |

> Add more outputPins entries ("2", "3", ...) for additional branches.

---

### FlowNode_ExecutionMultiGate
**Class:** `/Script/Flow.FlowNode_ExecutionMultiGate`
**Purpose:** Routes execution to one of N outputs. Supports random, loop, and sequential modes.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `In` | Exec | Trigger |
| Input | `Reset` | Exec | Reset gate state |
| Output | `0` | Exec | First gate |
| Output | `1` | Exec | Second gate (add more as needed) |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| bRandom | bool | false | Pick random output instead of sequential |
| bLoop | bool | false | Loop back to 0 after last output |
| StartIndex | int | -1 | Starting gate index (-1 = first) |

---

### FlowNode_Timer
**Class:** `/Script/Flow.FlowNode_Timer`
**Purpose:** Countdown timer with step callbacks. Fires Completed when time elapses.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `In` | Exec | Start timer |
| Input | `Skip` | Exec | Skip to completion |
| Input | `Restart` | Exec | Restart timer |
| Input | `CompletionTime` | Float (data) | Override completion time via data pin |
| Output | `Completed` | Exec | Timer finished |
| Output | `Step` | Exec | Fires each step interval |
| Output | `Skipped` | Exec | Timer was skipped |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| CompletionTime | float | 0.0 | Total timer duration (seconds) |
| StepTime | float | 0.0 | Interval between Step fires (seconds) |

---

### FlowNode_Finish
**Class:** `/Script/Flow.FlowNode_Finish`
**Purpose:** Terminates the FlowAsset execution.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `In` | Exec | Trigger to finish graph |

**Properties:** None.

---

### FlowNode_DoN
**Class:** `/Script/PLFlowGraphExtended.FlowNode_DoN`
**Purpose:** Executes up to N times, then fires Completed.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `Start` | Exec | Trigger execution |
| Input | `Reset` | Exec | Reset counter |
| Output | `Execute` | Exec | Fires each time (up to N) |
| Output | `Completed` | Exec | Fires after N executions |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| N | int | 1 | Max execution count |
| IdentityTags | GameplayTagContainer | — | Standard identity tags |
| bUsePayloadActors | bool | false | Standard payload flag |

---

### FlowNode_PLCounter
**Class:** `/Script/PLFlowGraphExtended.FlowNode_PLCounter`
**Purpose:** Counts increments toward a Goal. Fires Execute on each increment, Goal when target reached.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `In` | Exec | Trigger |
| Input | `Increment` | Exec | Add 1 to counter |
| Input | `Reset` | Exec | Reset counter to 0 |
| Output | `Execute` | Exec | Fires on each increment |
| Output | `Goal` | Exec | Counter reached goal value |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| Goal | int32 | 1 | Target count value |
| CurrentCount | int32 | 0 | Current counter (SaveGame) |
| IdentityTags | GameplayTagContainer | — | Standard identity tags |

---

### FlowNode_Queue
**Class:** `/Script/PLFlowGraphExtended.FlowNode_Queue`
**Purpose:** Queues execution requests and fires them sequentially one at a time.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `In` | Exec | Enqueue execution |
| Output | `Out` | Exec | Dequeued execution fires |

**Properties:** None.

---

### FlowNode_LogicalOR
**Class:** `/Script/Flow.FlowNode_LogicalOR`
**Purpose:** Fires output when ANY input fires. Can be enabled/disabled and has execution limit.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `0` | Exec | First input |
| Input | `1` | Exec | Second input |
| Input | `Enable` | Exec | Enable the gate |
| Input | `Disable` | Exec | Disable the gate |
| Output | `Out` | Exec | Fires when any input triggers |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| bEnabled | bool | true | Whether gate is active |
| ExecutionLimit | int | 0 | Max fires (0 = unlimited) |
| ExecutionCount | int | 0 | Current fire count (runtime) |

---

### FlowNode_LogicalAND
**Class:** `/Script/Flow.FlowNode_LogicalAND`
**Purpose:** Fires output only when ALL inputs have fired.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `0` | Exec | First input |
| Input | `1` | Exec | Second input |
| Output | `Out` | Exec | Fires when all inputs triggered |

**Properties:** None.

---

### FlowNode_RandomInteger
**Class:** `/Script/PLFlowGraphExtended.FlowNode_RandomInteger`
**Purpose:** Randomly picks one of N outputs (0 to Range-1).

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `Start` | Exec | Trigger |
| Output | `0` | Exec | First option |
| Output | `1` | Exec | Second option |
| Output | `2` | Exec | Third option (dynamic based on Range) |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| Range | int | 2 | Number of output branches |
| IdentityTags | GameplayTagContainer | — | Standard identity props |

---

### FlowNode_Reroute
**Class:** `/Script/Flow.FlowNode_Reroute`
**Purpose:** Visual passthrough — no logic, just tidies wires in the graph editor.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `In` | Exec | Passthrough input |
| Output | `Out` | Exec | Passthrough output |

**Properties:** None — visual only.

---

### FlowNode_PLSubGraph
**Class:** `/Script/PLFlowGraphExtended.FlowNode_PLSubGraph`
**Purpose:** Runs another FlowAsset as a sub-graph. Essential for modular quest design.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `Start` | Exec | Launch sub-graph |
| Input | `Force Finish` | Exec | Force-terminate sub-graph |
| Output | `Finish` | Exec | Sub-graph completed normally |
| Output | `Force Finished` | Exec | Sub-graph was force-terminated |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| Asset | FlowAsset path | — | Path to the sub-graph FlowAsset |
| IsInEventManager | bool | false | Register in event manager |
| bCanInstanceIdenticalAsset | bool | false | Allow multiple instances of same asset |

<details><summary>JSON Template</summary>

```json
{
  "Class": "/Script/PLFlowGraphExtended.FlowNode_PLSubGraph",
  "NodeGuid": "GENERATE-NEW-GUID",
  "NodePosX": 0,
  "NodePosY": 0,
  "inputPins": [
    { "PinName": "Start", "PinToolTip": "Start" },
    { "PinName": "Force Finish", "PinToolTip": "Force Finish" }
  ],
  "outputPins": [
    { "PinName": "Finish", "PinToolTip": "Finish" },
    { "PinName": "Force Finished", "PinToolTip": "Force Finished" }
  ],
  "Asset": "/Game/Path/To/SubFlowAsset.SubFlowAsset",
  "IsInEventManager": false,
  "bCanInstanceIdenticalAsset": false
}
```

</details>

---

### FlowNode_Counter
**Class:** `/Script/Flow.FlowNode_Counter`
**Purpose:** Counts increments/decrements toward a goal. Fires on zero, each step, and goal reached.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `Increment` | Exec | Add 1 to counter |
| Input | `Decrement` | Exec | Subtract 1 from counter |
| Input | `Skip` | Exec | Skip to goal |
| Output | `Zero` | Exec | Counter reached zero |
| Output | `Step` | Exec | Fires on each increment/decrement |
| Output | `Goal` | Exec | Counter reached goal value |
| Output | `Skipped` | Exec | Counter was skipped |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| Goal | int | 0 | Target count value |

---

## Dialogue & UI Nodes

### FN_StartDialogueHUD_FixedText
**Class:** `/PLFlowGraphExtended/Nodes/FN_StartDialogueHUD_FixedText.FN_StartDialogueHUD_FixedText_C`
**Purpose:** Shows dialogue text in the HUD with player interaction to proceed.
**Usage count:** 598 (most common node in the project)

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `Start` | Exec | Begin dialogue |
| Input | `Interrupt` | Exec | Force-close dialogue |
| Output | `DialogueStarted` | Exec | Dialogue widget opened |
| Output | `DialogueFInished` | Exec | Dialogue completed (**capital I is correct — verified**) |
| Output | `ProceedToNext` | Exec | Player pressed proceed |
| Output | `Interrupted` | Exec | Dialogue was interrupted |
| Output | `AllFinished` | Exec | All dialogue entries done |

> **WARNING:** The pin name is `DialogueFInished` (capital I), NOT `DialogueFinished`. This is the actual pin name in the engine. Using lowercase will silently fail to connect.

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| DialogueText | NSLOCTEXT | — | Localized dialogue string |
| Time | float | 0.0 | Auto-advance time (0 = wait for input) |
| bUseOwner | bool | false | Target the owning actor |
| Entity | GameplayTag | — | Target entity tag (if not using owner) |
| MaxDistance | float | 0.0 | Max distance to show dialogue |
| EnableInputDelay | float | 0.0 | Input delay duration in seconds (0 = no delay) |
| SkipDialogueInteractionTag | GameplayTag | — | Tag to skip this dialogue |
| bShouldPlayAudio | bool | false | Play associated audio |
| IdentityTags | GameplayTagContainer | — | Standard identity tags |

<details><summary>JSON Template</summary>

```json
{
  "Class": "/PLFlowGraphExtended/Nodes/FN_StartDialogueHUD_FixedText.FN_StartDialogueHUD_FixedText_C",
  "NodeGuid": "GENERATE-NEW-GUID",
  "NodePosX": 0,
  "NodePosY": 0,
  "inputPins": [
    { "PinName": "Start", "PinToolTip": "Start" },
    { "PinName": "Interrupt", "PinToolTip": "Interrupt" }
  ],
  "outputPins": [
    { "PinName": "DialogueStarted", "PinToolTip": "DialogueStarted" },
    { "PinName": "DialogueFInished", "PinToolTip": "DialogueFInished" },
    { "PinName": "ProceedToNext", "PinToolTip": "ProceedToNext" },
    { "PinName": "Interrupted", "PinToolTip": "Interrupted" },
    { "PinName": "AllFinished", "PinToolTip": "AllFinished" }
  ],
  "DialogueText": {
    "Namespace": "",
    "Key": "UNIQUE_KEY_HERE",
    "SourceString": "Dialogue text here"
  },
  "Time": 3.0,
  "bUseOwner": false,
  "Entity": "",
  "MaxDistance": 0.0,
  "EnableInputDelay": 0.0,
  "bShouldPlayAudio": false
}
```

</details>

---

### FN_StartDialogueBubble_FixedText
**Class:** `/PLFlowGraphExtended/Nodes/FN_StartDialogueBubble_FixedText.FN_StartDialogueBubble_FixedText_C`
**Purpose:** Shows a speech bubble above an actor's head with text.
**Usage count:** 219

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `Start` | Exec | Begin bubble dialogue |
| Input | `Interrupt` | Exec | Force-close bubble |
| Output | `DialogueStarted` | Exec | Bubble appeared |
| Output | `DialogueFInished` | Exec | Bubble text completed (**capital I — same as HUD variant**) |
| Output | `DialogueBubbleFaded` | Exec | Bubble fade-out finished |
| Output | `Interrupted` | Exec | Bubble was interrupted |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| DialogueText | NSLOCTEXT | — | Localized bubble text |
| Fade Rate Scale | float | 1.0 | Speed of fade animation |
| Override Fade Time | float | 0.0 | Custom fade duration (0 = default) |
| Sound | Name | — | Sound name to play |
| SoundAsset | Asset path | — | Direct sound asset reference |
| SoundAssetDurationOffset | float | 0.0 | Offset into sound asset |
| bShouldPlayAudio | bool | false | Play associated audio |
| IdentityTags | GameplayTagContainer | — | Standard identity tags |

---

### FN_AutoplayHudTextFixed
**Class:** `/PLFlowGraphExtended/Nodes/FN_AutoplayHudTextFixed.FN_AutoplayHudTextFixed_C`
**Purpose:** Auto-advancing HUD dialogue — no player input needed to proceed.
**Usage count:** 36

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `Start` | Exec | Begin auto-play dialogue |
| Input | `Interrupt` | Exec | Force-close |
| Output | `DialogueStarted` | Exec | Dialogue widget opened |
| Output | `DialogueFInished` | Exec | Dialogue completed (**capital I**) |
| Output | `ProceedToNext` | Exec | Auto-advanced to next |
| Output | `Interrupted` | Exec | Was interrupted |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| DialogueText | NSLOCTEXT | — | Localized dialogue string |
| Time | float | 0.0 | Duration before auto-advance |
| IsOpen | bool | false | Whether dialogue starts open |
| IsCleanUp | bool | false | Clean up on finish |
| bUseOwner | bool | false | Target the owning actor |
| Entity | GameplayTag | — | Target entity tag |
| MaxDistance | float | 0.0 | Max distance to show |
| SkipDialogueInteractionTag | GameplayTag | — | Tag to skip |
| bShouldPlayAudio | bool | false | Play associated audio |
| IdentityTags | GameplayTagContainer | — | Standard identity tags |

---

### FN_StartSelectionHUD
**Class:** `/PLFlowGraphExtended/Nodes/FN_StartSelectionHUD.FN_StartSelectionHUD_C`
**Purpose:** Shows a selection menu in the HUD with multiple options. Outputs are dynamic per option.
**Usage count:** 48

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `Start` | Exec | Show selection menu |
| Input | `Interrupt` | Exec | Force-close menu |
| Input | `ResetDoOnce` | Exec | Reset one-shot options |
| Output | `NodeStarted` | Exec | Menu opened |
| Output | `Option_<text>` | Exec | Dynamic: one per option (e.g. `Option_Yes`, `Option_No`) |
| Output | `PlayerSelectedAnything` | Exec | Any option was selected |
| Output | `Interrupted` | Exec | Menu was interrupted |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| LiseningComps | Array | — | Listening components (note: original spelling) |
| bUseOwner | bool | false | Target the owning actor |
| Entity | GameplayTag | — | Target entity tag |
| IdentityTags | GameplayTagContainer | — | Standard identity tags |

---

### FN_ShowEventMsg
**Class:** `/PLFlowGraphExtended/Nodes/FN_ShowEventMsg.FN_ShowEventMsg_C`
**Purpose:** Shows an event message on screen (e.g., quest updates, tutorial tips).
**Usage count:** 94

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `Show` | Exec | Display message |
| Input | `Hide` | Exec | Hide message |
| Output | `Execute` | Exec | Message shown |
| Output | `Success` | Exec | Observer success |
| Output | `Completed` | Exec | Observer completed |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| Text | NSLOCTEXT | — | Localized message text |
| Time | float | 0.0 | Display duration (0 = manual hide) |
| IsHideCurrentMsg | bool | false | Hide any existing message first |
| BShowTurText | bool | false | Show tutorial-style text |
| SuccessLimit | int | 0 | Observer mixin — success limit |
| IdentityTags | GameplayTagContainer | — | Observer mixin — identity tags |

---

### FN_ShowKeyPressTip
**Class:** `/PLFlowGraphExtended/Nodes/FN_ShowKeyPressTip.FN_ShowKeyPressTip_C`
**Purpose:** Shows a key-press tip overlay (e.g., "Press E to interact").
**Usage count:** 40

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `Show` | Exec | Display tip |
| Input | `Hide` | Exec | Hide tip |
| Output | `Execute` | Exec | Tip shown |
| Output | `Success` | Exec | Observer success |
| Output | `Completed` | Exec | Observer completed |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| Text | NSLOCTEXT | — | Localized tip text |
| Time | float | 0.0 | Display duration |
| IsHideCurrentMsg | bool | false | Hide existing tip first |
| BShowTurText | bool | false | Show tutorial-style text |
| SuccessLimit | int | 0 | Observer mixin |
| IdentityTags | GameplayTagContainer | — | Observer mixin |

---
## Gameplay Action Nodes

### FlowNode_ExecuteCustomEventOnActor
**Class:** `/Script/PLFlowGraphExtended.FlowNode_ExecuteCustomEventOnActor`
**Purpose:** Fires a custom GameplayEvent on target actors matched by identity tags.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `In` | Exec | Trigger |
| Output | `Out` | Exec | After event sent |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| EventTag | GameplayTag | — | Event to fire |
| IdentityTags | GameplayTagContainer | — | Target actor filter |
| IdentityMatchType | enum | — | Match type (Any/All/Exact) |
| bUsePayloadActors | bool | false | Use payload actors as targets |
| bBindOnAgentComponent | bool | false | Bind to agent component |
| bBindOnIgnoreFlowComp | bool | false | Bind ignoring flow component |
| CurrentPayload | — | — | Payload data |

---

### FN_SetGameplayTag
**Class:** `/Script/PLFlowGraphExtended.FN_SetGameplayTag`
**Purpose:** Adds or removes GameplayTags on target actors.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `Start` | Exec | Trigger |
| Output | `Execute` | Exec | Tags modified |
| Output | `Success` | Exec | Operation succeeded |
| Output | `Failed` | Exec | Operation failed |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| TagsToAdd | GameplayTagContainer | — | Tags to add |
| TagsToRemove | GameplayTagContainer | — | Tags to remove |
| bRemoveAllChildrenTags | bool | false | Remove child tags too |
| SetterCondition | — | — | Condition for tag operation |

---

### FlowNode_ModifyPhaseAttribute
**Class:** `/Script/PLFlowGraphExtended.FlowNode_ModifyPhaseAttribute`
**Purpose:** Modifies a phase attribute value (add/set/multiply).

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `In` | Exec | Trigger |
| Output | `Out` | Exec | After modification |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| AttributeTag | GameplayTag | — | Which attribute to modify |
| AttributeType | enum | — | Modification type (Add/Set/Multiply) |
| AddValue | float | 0.0 | Value to apply |

---

### FN_SpawnEntity
**Class:** `/Script/PLFlowGraphExtended.FN_SpawnEntity`
**Purpose:** Spawns entities (NPCs, items, etc.) into the world.
**Usage count:** 59

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `Start` | Exec | Begin spawning |
| Output | `Execute` | Exec | Spawn initiated |
| Output | `SpawnFinish` | Exec | Individual spawn completed |
| Output | `AllAdded` | Exec | All entities spawned |
| Output | `Failed` | Exec | Spawn failed |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| EntitySpawnInfos | Array | — | Array of entity spawn configurations |
| SpawnAmount | int | 1 | Number to spawn |
| bGetSpawnParameterFromPython | bool | false | Use Python-generated params |
| bShouldAddToBag | bool | false | Add spawned entity to bag |
| EquipIndex | int | -1 | Equipment slot index |
| EntityTagToEquip | GameplayTag | — | Tag of entity to equip |
| bEquipWhenEmpty | bool | false | Only equip if slot empty |
| bAddDebugSmoke | bool | false | Visual debug smoke effect |
| SpawnLocationForwardExtend | float | 0.0 | Forward offset from spawn point |
| IdentityTags | GameplayTagContainer | — | Standard identity tags |

<details><summary>JSON Template</summary>

```json
{
  "Class": "/Script/PLFlowGraphExtended.FN_SpawnEntity",
  "NodeGuid": "GENERATE-NEW-GUID",
  "NodePosX": 0,
  "NodePosY": 0,
  "inputPins": [
    { "PinName": "Start", "PinToolTip": "Start" }
  ],
  "outputPins": [
    { "PinName": "Execute", "PinToolTip": "Execute" },
    { "PinName": "SpawnFinish", "PinToolTip": "SpawnFinish" },
    { "PinName": "AllAdded", "PinToolTip": "AllAdded" },
    { "PinName": "Failed", "PinToolTip": "Failed" }
  ],
  "EntitySpawnInfos": [],
  "SpawnAmount": 1,
  "bShouldAddToBag": false,
  "bAddDebugSmoke": false,
  "SpawnLocationForwardExtend": 0.0
}
```

</details>

---

### FlowNode_Teleport
**Class:** `/Script/PLFlowGraphExtended.FlowNode_Teleport`
**Purpose:** Teleports target actors to a location defined by actor tag + offset.
**Usage count:** 73

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `Start` | Exec | Trigger teleport |
| Output | `Execute` | Exec | Teleport initiated |
| Output | `Success` | Exec | Teleport succeeded |
| Output | `Failed` | Exec | Teleport failed |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| TargetActorTag | GameplayTag | — | Tag of destination actor |
| TeleportOffset | Vector | (0,0,0) | Offset from target location |
| bDebug | bool | false | Show debug visualization |
| DebugDuration | float | 0.0 | Debug display duration |
| IdentityTags | GameplayTagContainer | — | Standard identity tags |

---

### FlowNode_ConsumeEntityInWorld
**Class:** `/Script/PLFlowGraphExtended.FlowNode_ConsumeEntityInWorld`
**Purpose:** Finds and consumes (optionally destroys) entities in the world matching tags.
**Usage count:** 26

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `Start` | Exec | Begin search and consume |
| Output | `Execute` | Exec | Operation initiated |
| Output | `HasAny` | Exec | Found at least one matching entity |
| Output | `HasAll` | Exec | Found all required entities |
| Output | `Failed` | Exec | No matching entities found |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| EntityTags | GameplayTagContainer | — | Tags to match entities |
| ConsumeAmount | int | 1 | Number to consume |
| bShouldDestroyWhenUse | bool | false | Destroy entity after consuming |
| DetectionRadius | float | 0.0 | Search radius |
| ShowDebug | bool | false | Show debug visualization |
| bAddDebugSmoke | bool | false | Visual debug smoke |
| DestroyLifeSpan | float | 0.0 | Delay before destroy |
| IdentityTags | GameplayTagContainer | — | Standard identity tags |

---

### FlowNode_EnableBehaviorTree
**Class:** `/Script/PLFlowGraphExtended.FlowNode_EnableBehaviorTree`
**Purpose:** Enables or disables a behavior tree on target AI actors.
**Usage count:** 18

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `Start` | Exec | Trigger |
| Output | `Execute` | Exec | Operation initiated |
| Output | `Success` | Exec | BT enabled/disabled |
| Output | `Failed` | Exec | Operation failed |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| BehaviorTreeAsset | Asset path | — | Path to behavior tree asset |
| bEnable | bool | true | true = enable, false = disable |
| IdentityTags | GameplayTagContainer | — | Standard identity tags |

---

## AI & Movement Nodes

### FN_AIMoveToByTag
**Class:** `/Script/PLFlowGraphExtended.FN_AIMoveToByTag`
**Purpose:** Commands AI to move to an actor found by GameplayTag. Most-used AI movement node.
**Usage count:** 108

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `Start` | Exec | Begin movement |
| Output | `Execute` | Exec | Movement started |
| Output | `Success` | Exec | Reached destination |
| Output | `Fail` | Exec | Movement failed |
| Output | `NotFound` | Exec | Target actor not found |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| TargetActorTag | GameplayTag | — | Tag of destination actor |
| AcceptanceRadius | float | 50.0 | How close is "arrived" |
| bStopAllMontages | bool | false | Stop playing montages on start |
| StopBlendOutTime | float | 0.0 | Montage blend-out time |
| SearchRadius | float | 0.0 | Actor search radius |
| SearchActorClass | Class | — | Filter by actor class |
| QueryFilterClass | Class | — | Navigation query filter |
| ActorSearchCollisionChannel | enum | — | Collision channel for search |
| bUseExactLocation | bool | false | Use exact vector instead of tag |
| ExactLocation | Vector | (0,0,0) | Exact target location |
| bDebug | bool | false | Show debug visualization |
| DebugDuration | float | 0.0 | Debug display duration |
| DesiredGaitTagAtStart | GameplayTag | — | Gait tag when movement starts |
| bRevertGaitTagAtEnd | bool | false | Revert gait when done |
| DesiredGaitTagAtEnd | GameplayTag | — | Gait tag when movement ends |
| RetryCount | int | 0 | Number of retries on failure |
| IdentityTags | GameplayTagContainer | — | Standard identity tags |

<details><summary>JSON Template</summary>

```json
{
  "Class": "/Script/PLFlowGraphExtended.FN_AIMoveToByTag",
  "NodeGuid": "GENERATE-NEW-GUID",
  "NodePosX": 0,
  "NodePosY": 0,
  "inputPins": [
    { "PinName": "Start", "PinToolTip": "Start" }
  ],
  "outputPins": [
    { "PinName": "Execute", "PinToolTip": "Execute" },
    { "PinName": "Success", "PinToolTip": "Success" },
    { "PinName": "Fail", "PinToolTip": "Fail" },
    { "PinName": "NotFound", "PinToolTip": "NotFound" }
  ],
  "TargetActorTag": "Entity.NPC.TargetName",
  "AcceptanceRadius": 50.0,
  "bDebug": false,
  "RetryCount": 0
}
```

</details>

---

### FN_PlayMontageAction
**Class:** `/Script/PLFlowGraphExtended.FN_PlayMontageAction`
**Purpose:** Triggers a gameplay ability that plays an animation montage on target actors.
**Usage count:** 104

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `Start` | Exec | Trigger ability |
| Output | `Success` | Exec | Ability activated successfully |
| Output | `Failed` | Exec | Ability failed to activate |
| Output | `AbilityEnded` | Exec | Ability finished |
| Output | `ActorDestroyed` | Exec | Target actor was destroyed |
| Output | `Completed` | Exec | Full sequence completed |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| AIBehaviorToStopTag | GameplayTag | — | Stop this AI behavior first |
| TriggerByEventTag | GameplayTag | — | Event tag to trigger ability |
| AbilityClass | Class | — | Gameplay ability class |
| EventTag | GameplayTag | — | Event tag payload |
| TargetTags | GameplayTagContainer | — | Target actor tags |
| IdentityTags | GameplayTagContainer | — | Standard identity tags |

---

### FN_Wait
**Class:** `/Script/PLFlowGraphExtended.FN_Wait`
**Purpose:** Simple delay node — waits for specified time then continues.
**Usage count:** 74

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `Start` | Exec | Begin waiting |
| Output | `Execute` | Exec | Wait started |
| Output | `Completed` | Exec | Wait finished |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| WaitTime | float | 1.0 | Wait duration in seconds |
| IdentityTags | GameplayTagContainer | — | Standard identity tags |

<details><summary>JSON Template</summary>

```json
{
  "Class": "/Script/PLFlowGraphExtended.FN_Wait",
  "NodeGuid": "GENERATE-NEW-GUID",
  "NodePosX": 0,
  "NodePosY": 0,
  "inputPins": [
    { "PinName": "Start", "PinToolTip": "Start" }
  ],
  "outputPins": [
    { "PinName": "Execute", "PinToolTip": "Execute" },
    { "PinName": "Completed", "PinToolTip": "Completed" }
  ],
  "WaitTime": 2.0
}
```

</details>

---

### FlowNode_PressInputByTag
**Class:** `/Script/PLFlowGraphExtended.FlowNode_PressInputByTag`
**Purpose:** Simulates an input press action on target actors by tag.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `In` | Exec | Trigger |
| Output | `Out` | Exec | After input sent |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| InputTag | GameplayTag | — | Input action tag to simulate |
| IdentityTags | GameplayTagContainer | — | Target actor filter |
| bUsePayloadActors | bool | false | Standard payload flag |

---

### FlowNode_EquipEntity
**Class:** `/Script/PLFlowGraphExtended.FlowNode_EquipEntity`
**Purpose:** Equips an entity on target actors.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `In` | Exec | Trigger |
| Output | `Out` | Exec | Equip succeeded |
| Output | `Failed` | Exec | Equip failed |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| EquipTag | GameplayTag | — | Equipment entity tag |
| IdentityTags | GameplayTagContainer | — | Target actor filter |
| bUsePayloadActors | bool | false | Use payload actors as targets |

---

### FlowNode_ThrowEntity
**Class:** `/Script/PLFlowGraphExtended.FlowNode_ThrowEntity`
**Purpose:** Makes target actors throw an entity.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `In` | Exec | Trigger |
| Output | `Out` | Exec | After throw |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| ThrowTag | GameplayTag | — | Entity tag to throw |
| IdentityTags | GameplayTagContainer | — | Target actor filter |
| bUsePayloadActors | bool | false | Standard payload flag |

---

### FlowNode_ClearPayloadActors
**Class:** `/Script/PLFlowGraphExtended.FlowNode_ClearPayloadActors`
**Purpose:** Clears the current payload actor list.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `In` | Exec | Trigger |
| Output | `Out` | Exec | Payload cleared |

**Properties:** None.

---

### FN_OpenInventory
**Class:** `/Script/PLFlowGraphExtended.FN_OpenInventory`
**Purpose:** Opens the inventory UI for target actors.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `In` | Exec | Open inventory |
| Output | `Out` | Exec | Inventory opened |
| Output | `Closed` | Exec | Inventory was closed |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| IdentityTags | GameplayTagContainer | — | Target actor filter |
| bUsePayloadActors | bool | false | Standard payload flag |

---

## Actor Condition Nodes

### FlowNode_ActorHasTags
**Class:** `/Script/PLFlowGraphExtended.FlowNode_ActorHasTags`
**Purpose:** Condition check — branches based on whether target actors have specific tags.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `In` | Exec | Trigger |
| Output | `True` | Exec | Actor has required tags |
| Output | `False` | Exec | Actor missing required tags |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| RequiredTags | GameplayTagContainer | — | Tags the actor must have |
| MatchType | enum | — | Match type (Any/All/Exact) |
| IdentityTags | GameplayTagContainer | — | Target actor filter |
| bUsePayloadActors | bool | false | Standard payload flag |

---

### FlowNode_HasAchievement
**Class:** `/Script/PLFlowGraphExtended.FlowNode_HasAchievement`
**Purpose:** Condition check — branches based on whether target actor has an achievement.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `In` | Exec | Trigger |
| Output | `Yes` | Exec | Has achievement |
| Output | `No` | Exec | Does not have achievement |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| AchievementTag | GameplayTag | — | Achievement to check |
| IdentityTags | GameplayTagContainer | — | Target actor filter |
| bUsePayloadActors | bool | false | Standard payload flag |

---

### FlowNode_ActorAttributeCondition
**Class:** `/Script/PLFlowGraphExtended.FlowNode_ActorAttributeCondition`
**Purpose:** Condition check — branches based on actor attribute value vs threshold.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `In` | Exec | Trigger |
| Output | `True` | Exec | Condition met |
| Output | `False` | Exec | Condition not met |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| AttributeTag | GameplayTag | — | Attribute to check |
| ComparisonType | enum | — | Comparison operator (GreaterThan, LessThan, Equal, etc.) |
| ThresholdValue | float | 0.0 | Value to compare against |
| IdentityTags | GameplayTagContainer | — | Target actor filter |
| bUsePayloadActors | bool | false | Standard payload flag |

---

### FlowNode_IfTargetActorAlive
**Class:** `/Script/PLFlowGraphExtended.FlowNode_IfTargetActorAlive`
**Purpose:** Condition check — branches based on whether target actor is alive.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `In` | Exec | Trigger |
| Output | `Alive` | Exec | Actor is alive |
| Output | `Dead` | Exec | Actor is dead |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| IdentityTags | GameplayTagContainer | — | Target actor filter |
| bUsePayloadActors | bool | false | Standard payload flag |

---

### FlowNode_IfTargetWeather
**Class:** `/Script/PLFlowGraphExtended.FlowNode_IfTargetWeather`
**Purpose:** Condition check — branches based on whether current weather matches a tag.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `In` | Exec | Trigger |
| Output | `Match` | Exec | Weather matches |
| Output | `NoMatch` | Exec | Weather does not match |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| WeatherTag | GameplayTag | — | Weather tag to check against |

---
## Listener / Observer Nodes

### FlowNode_OnTriggerEnter
**Class:** `/Script/PLFlowGraphExtended.FlowNode_OnTriggerEnter`
**Purpose:** Fires when an actor enters a trigger volume. Core event listener.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `Start` | Exec | Start listening |
| Input | `Stop` | Exec | Stop listening |
| Output | `Entered` | Exec | Actor entered trigger |
| Output | `Completed` | Exec | Observer completed |
| Output | `Stopped` | Exec | Listener stopped |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| bCheckOverlapWhenStart | bool | false | Check existing overlaps on start |
| TriggeredActorTags | GameplayTagContainer | — | Filter by actor tags |
| TriggeredActorMatchType | enum | — | Tag match type |
| bTriggerOnOwningClientOnly | bool | false | Only trigger for owning client |
| SuccessLimit | int | 0 | Observer mixin |
| IdentityTags | GameplayTagContainer | — | Observer mixin |

---

### FlowNode_OnTriggerExit
**Class:** `/Script/PLFlowGraphExtended.FlowNode_OnTriggerExit`
**Purpose:** Fires when an actor exits a trigger volume.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `Start` | Exec | Start listening |
| Input | `Stop` | Exec | Stop listening |
| Output | `Exited` | Exec | Actor exited trigger |
| Output | `Completed` | Exec | Observer completed |
| Output | `Stopped` | Exec | Listener stopped |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| bCheckOverlapWhenStart | bool | false | Check existing overlaps on start |
| TriggeredActorTags | GameplayTagContainer | — | Filter by actor tags |
| TriggeredActorMatchType | enum | — | Tag match type |
| bTriggerOnOwningClientOnly | bool | false | Only trigger for owning client |
| SuccessLimit | int | 0 | Observer mixin |
| IdentityTags | GameplayTagContainer | — | Observer mixin |

---

### FlowNode_OnActorRegistered
**Class:** `/Script/Flow.FlowNode_OnActorRegistered`
**Purpose:** Fires when an actor with matching identity tags registers with the Flow subsystem.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `Start` | Exec | Start listening |
| Input | `Stop` | Exec | Stop listening |
| Output | `Execute` | Exec | Actor registered |
| Output | `Success` | Exec | Observer success |
| Output | `Completed` | Exec | Observer completed |
| Output | `Stopped` | Exec | Listener stopped |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| SuccessLimit | int | 0 | Observer mixin |
| IdentityTags | GameplayTagContainer | — | Observer mixin |

---

### FlowNode_ListenTagChanged
**Class:** `/Script/PLFlowGraphExtended.FlowNode_ListenTagChanged`
**Purpose:** Listens for GameplayTag changes on target actors. Dynamic outputs per tag.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `Start` | Exec | Start listening |
| Input | `Stop Listen` | Exec | Stop listening |
| Output | `Execute` | Exec | Any tag changed |
| Output | `Stop` | Exec | Listener stopped |
| Output | `<TagName> Added` | Exec | Dynamic: fires when specific tag added |
| Output | `<TagName> Removed` | Exec | Dynamic: fires when specific tag removed |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| ListenAddedTags | GameplayTagContainer | — | Tags to listen for addition |
| ListenRemovedTags | GameplayTagContainer | — | Tags to listen for removal |
| bTriggerOutWhenHasOrNot | bool | false | Trigger based on has/not-has state |
| SuccessLimit | int | 0 | Observer mixin |
| IdentityTags | GameplayTagContainer | — | Observer mixin |

---

### FlowNode_ListenBuildActor
**Class:** `/Script/PLFlowGraphExtended.FlowNode_ListenBuildActor`
**Purpose:** Listens for building/construction events matching specific entity tags.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `Start` | Exec | Start listening |
| Input | `Stop Listen` | Exec | Stop listening |
| Output | `Success` | Exec | Required building built |
| Output | `Completed` | Exec | Observer completed |
| Output | `Stopped` | Exec | Listener stopped |
| Output | `AnyActorBuilt` | Exec | Any building placed |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| ListeningBuildingBlockEntityTags | GameplayTagContainer | — | Tags of buildings to listen for |
| ListenNotInBuildTags | GameplayTagContainer | — | Exclude these building tags |
| SuccessLimit | int | 0 | Observer mixin |
| IdentityTags | GameplayTagContainer | — | Observer mixin |

---

### FlowNode_ListenTimeChange
**Class:** `/Script/PLFlowGraphExtended.FlowNode_ListenTimeChange`
**Purpose:** Listens for in-game time changes (zodiac hours). Dynamic outputs per listened hour.
**Usage count:** 31

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `Start` | Exec | Start listening |
| Input | `Stop Listen` | Exec | Stop listening |
| Output | `Execute` | Exec | Any time change |
| Output | `TimeChanged` | Exec | Time changed event |
| Output | `Stop` | Exec | Listener stopped |
| Output | `Environment.Calendar.ZodiacHour.*` | Exec | Dynamic: one per listened zodiac hour |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| ListenHours | Array | — | Array of zodiac hours to listen for |
| CheckedBiomeTag | GameplayTag | — | Filter by biome |
| SuccessLimit | int | 0 | Observer mixin |
| IdentityTags | GameplayTagContainer | — | Observer mixin |

---

### FlowNode_ListenActorBeHit
**Class:** `/Script/PLFlowGraphExtended.FlowNode_ListenActorBeHit`
**Purpose:** Listens for damage/hit events on target actors, filtered by damage type and instigator.
**Usage count:** 31

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `Start` | Exec | Start listening |
| Input | `StopListen` | Exec | Stop listening (no space) |
| Output | `Execute` | Exec | Hit detected |
| Output | `Stop` | Exec | Listener stopped |
| Output | `BeHit` | Exec | Actor was hit |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| ListenDamageConfigTags | GameplayTagContainer | — | Filter by damage type tags |
| ListenInstigatorTags | GameplayTagContainer | — | Filter by who dealt damage |
| SuccessLimit | int | 0 | Observer mixin |
| IdentityTags | GameplayTagContainer | — | Observer mixin |

---

### FN_ListenPlayerAction
**Class:** `/PLFlowGraphExtended/Nodes/FN_ListenPlayerAction.FN_ListenPlayerAction_C`
**Purpose:** Listens for player interaction/action events. Blueprint-based observer.
**Usage count:** 122

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `Start` | Exec | Start listening |
| Input | `Stop` | Exec | Stop listening |
| Output | `Execute` | Exec | Action detected |
| Output | `Success` | Exec | Observer success |
| Output | `Completed` | Exec | Observer completed |
| Output | `Stopped` | Exec | Listener stopped |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| InteractionTag | GameplayTag | — | Tag of the interaction to listen for |
| ListeningDelegate | — | — | Delegate binding |
| bOnly Trigger Once | bool | false | Fire only once (note: space in property name) |
| SuccessLimit | int | 0 | Observer mixin |
| IdentityTags | GameplayTagContainer | — | Observer mixin |

---

### FlowNode_OnNotifyFromActor
**Class:** `/Script/Flow.FlowNode_OnNotifyFromActor`
**Purpose:** Listens for notify events from actors matching identity tags.
**Usage count:** 38

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `Start` | Exec | Start listening |
| Input | `Stop` | Exec | Stop listening |
| Output | `Execute` | Exec | Notify received |
| Output | `Success` | Exec | Observer success |
| Output | `Completed` | Exec | Observer completed |
| Output | `Stopped` | Exec | Listener stopped |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| NotifyTags | GameplayTagContainer | — | Tags to listen for |
| bRetroactive | bool | false | Check for already-sent notifies |
| SuccessLimit | int | 0 | Observer mixin |
| IdentityTags | GameplayTagContainer | — | Observer mixin |

---

### FlowNode_ListenBag
**Class:** `/Script/PLFlowGraphExtended.FlowNode_ListenBag`
**Purpose:** Listens for inventory (bag) changes — items added or removed.
**Usage count:** 27

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `Start` | Exec | Start listening |
| Input | `Stop Listen` | Exec | Stop listening |
| Output | `Execute` | Exec | Any bag change |
| Output | `Stopped` | Exec | Listener stopped |
| Output | `Any Get` | Exec | Any item acquired |
| Output | `Any Remove` | Exec | Any item removed |
| Output | `Any Get (In List)` | Exec | Listed item acquired |
| Output | `Any Remove (In List)` | Exec | Listed item removed |
| Output | `Entity.*` | Exec | Dynamic: per-entity tag outputs |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| ListenGetTags | GameplayTagContainer | — | Entity tags to listen for acquisition |
| ListenRemoveTags | GameplayTagContainer | — | Entity tags to listen for removal |
| FilterFromEntityTags | GameplayTagContainer | — | Additional entity filter |
| SuccessLimit | int | 0 | Observer mixin |
| IdentityTags | GameplayTagContainer | — | Observer mixin |

---

### FlowNode_ActionChain
**Class:** `/Script/PLFlowGraphExtended.FlowNode_ActionChain`
**Purpose:** Observes action chain steps. Creates dynamic output pins from ActionNodeTags for branching per step.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `Start` | Exec | Start observing |
| Input | `Stop` | Exec | Stop observing |
| Output | `Success` | Exec | Chain completed |
| Output | `<ActionTag>` | Exec | Dynamic: one per ActionNodeTag |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| ActionNodeTags | GameplayTagContainer | — | Tags defining chain steps (creates dynamic output pins) |
| SuccessLimit | int | 0 | Observer mixin |
| SuccessCount | int | 0 | Current success count (runtime) |
| IdentityTags | GameplayTagContainer | — | Observer mixin |
| bUsePayloadActors | bool | false | Standard payload flag |

---

### FlowNode_ListenEquip
**Class:** `/Script/PLFlowGraphExtended.FlowNode_ListenEquip`
**Purpose:** Listens for equipment changes on target actors.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `Start` | Exec | Start listening |
| Input | `Stop` | Exec | Stop listening |
| Output | `Success` | Exec | Equipment change detected |
| Output | `Completed` | Exec | Observer completed |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| EquipTag | GameplayTag | — | Equipment tag to listen for |
| SuccessLimit | int | 0 | Observer mixin |
| IdentityTags | GameplayTagContainer | — | Observer mixin |
| bUsePayloadActors | bool | false | Standard payload flag |

---

### FlowNode_ListenAttribute
**Class:** `/Script/PLFlowGraphExtended.FlowNode_ListenAttribute`
**Purpose:** Listens for attribute value changes on target actors, fires when threshold condition met.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `Start` | Exec | Start listening |
| Input | `Stop` | Exec | Stop listening |
| Output | `Success` | Exec | Attribute condition met |
| Output | `Completed` | Exec | Observer completed |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| AttributeTag | GameplayTag | — | Attribute to monitor |
| ComparisonType | enum | — | Comparison operator (GreaterThan, LessThan, Equal, etc.) |
| ThresholdValue | float | 0.0 | Value to compare against |
| SuccessLimit | int | 0 | Observer mixin |
| IdentityTags | GameplayTagContainer | — | Observer mixin |
| bUsePayloadActors | bool | false | Standard payload flag |

---

### FlowNode_ListenAchievement
**Class:** `/Script/PLFlowGraphExtended.FlowNode_ListenAchievement`
**Purpose:** Listens for achievement completion on target actors.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `Start` | Exec | Start listening |
| Input | `Stop` | Exec | Stop listening |
| Output | `Success` | Exec | Achievement completed |
| Output | `Completed` | Exec | Observer completed |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| AchievementTag | GameplayTag | — | Achievement to listen for |
| SuccessLimit | int | 0 | Observer mixin |
| IdentityTags | GameplayTagContainer | — | Observer mixin |
| bUsePayloadActors | bool | false | Standard payload flag |

---

### FlowNode_ListenGameplayAbility
**Class:** `/Script/PLFlowGraphExtended.FlowNode_ListenGameplayAbility`
**Purpose:** Listens for gameplay ability activation on target actors.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `Start` | Exec | Start listening |
| Input | `Stop` | Exec | Stop listening |
| Output | `Success` | Exec | Ability activated |
| Output | `Completed` | Exec | Observer completed |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| AbilityClass | Class | — | Gameplay ability class to listen for |
| SuccessLimit | int | 0 | Observer mixin |
| IdentityTags | GameplayTagContainer | — | Observer mixin |
| bUsePayloadActors | bool | false | Standard payload flag |

---

### FlowNode_ListenWeatherChange
**Class:** `/Script/PLFlowGraphExtended.FlowNode_ListenWeatherChange`
**Purpose:** Listens for weather transitions matching a specific weather tag.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `Start` | Exec | Start listening |
| Input | `Stop` | Exec | Stop listening |
| Output | `Success` | Exec | Weather matched |
| Output | `Completed` | Exec | Observer completed |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| WeatherTag | GameplayTag | — | Weather tag to listen for |
| SuccessLimit | int | 0 | Observer mixin |
| IdentityTags | GameplayTagContainer | — | Observer mixin |

---

### FlowNode_ListenPickUp
**Class:** `/Script/PLFlowGraphExtended.FlowNode_ListenPickUp`
**Purpose:** Listens for item pickup events on target actors.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `Start` | Exec | Start listening |
| Input | `Stop` | Exec | Stop listening |
| Output | `Success` | Exec | Item picked up |
| Output | `Completed` | Exec | Observer completed |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| PickUpTag | GameplayTag | — | Item tag to listen for |
| SuccessLimit | int | 0 | Observer mixin |
| IdentityTags | GameplayTagContainer | — | Observer mixin |
| bUsePayloadActors | bool | false | Standard payload flag |

---

### FlowNode_ListenItemGiven
**Class:** `/Script/PLFlowGraphExtended.FlowNode_ListenItemGiven`
**Purpose:** Listens for items given to target actors (e.g., NPC gift events).

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `Start` | Exec | Start listening |
| Input | `Stop` | Exec | Stop listening |
| Output | `Success` | Exec | Item given |
| Output | `Completed` | Exec | Observer completed |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| ItemTag | GameplayTag | — | Item tag to listen for |
| SuccessLimit | int | 0 | Observer mixin |
| IdentityTags | GameplayTagContainer | — | Observer mixin |
| bUsePayloadActors | bool | false | Standard payload flag |

---

### FlowNode_ListenPersonaChanged
**Class:** `/Script/PLFlowGraphExtended.FlowNode_ListenPersonaChanged`
**Purpose:** Listens for persona/character state changes on target actors.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `Start` | Exec | Start listening |
| Input | `Stop` | Exec | Stop listening |
| Output | `Success` | Exec | Persona changed |
| Output | `Completed` | Exec | Observer completed |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| SuccessLimit | int | 0 | Observer mixin |
| IdentityTags | GameplayTagContainer | — | Observer mixin |
| bUsePayloadActors | bool | false | Standard payload flag |

---

### FlowNode_OnInteractionUsed
**Class:** `/Script/PLFlowGraphExtended.FlowNode_OnInteractionUsed`
**Purpose:** Fires when an interaction is used on observed actors, filtered by interaction tag.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `Start` | Exec | Start listening |
| Input | `Stop` | Exec | Stop listening |
| Output | `Success` | Exec | Interaction used |
| Output | `Completed` | Exec | Observer completed |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| InteractionTag | GameplayTag | — | Interaction tag to listen for |
| SuccessLimit | int | 0 | Observer mixin |
| IdentityTags | GameplayTagContainer | — | Observer mixin |
| bUsePayloadActors | bool | false | Standard payload flag |

---

### FlowNode_OnCharacterDead
**Class:** `/Script/PLFlowGraphExtended.FlowNode_OnCharacterDead`
**Purpose:** Fires when an observed character dies.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `Start` | Exec | Start listening |
| Input | `Stop` | Exec | Stop listening |
| Output | `Success` | Exec | Character died |
| Output | `Completed` | Exec | Observer completed |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| SuccessLimit | int | 0 | Observer mixin |
| IdentityTags | GameplayTagContainer | — | Observer mixin |
| bUsePayloadActors | bool | false | Standard payload flag |

---

## Calendar & Weather Nodes

### FlowNode_AddWeatherEvent
**Class:** `/Script/PLFlowGraphExtended.FlowNode_AddWeatherEvent`
**Purpose:** Adds a weather event to the calendar system.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `In` | Exec | Trigger |
| Output | `Out` | Exec | Event added |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| WeatherTag | GameplayTag | — | Weather type tag |
| Duration | float | 0.0 | Event duration in seconds |

---

### FlowNode_RemoveWeatherEvent
**Class:** `/Script/PLFlowGraphExtended.FlowNode_RemoveWeatherEvent`
**Purpose:** Removes a weather event from the calendar system.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `In` | Exec | Trigger |
| Output | `Out` | Exec | Event removed |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| WeatherTag | GameplayTag | — | Weather type tag to remove |

---

### FlowNode_LockCalendar
**Class:** `/Script/PLFlowGraphExtended.FlowNode_LockCalendar`
**Purpose:** Locks calendar progression — time stops advancing.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `In` | Exec | Trigger |
| Output | `Out` | Exec | Calendar locked |

**Properties:** None.

---

### FlowNode_UnlockCalendar
**Class:** `/Script/PLFlowGraphExtended.FlowNode_UnlockCalendar`
**Purpose:** Unlocks calendar progression — time resumes advancing.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `In` | Exec | Trigger |
| Output | `Out` | Exec | Calendar unlocked |

**Properties:** None.

---

### FlowNode_QuickSwitchZodiacHourByTag
**Class:** `/Script/PLFlowGraphExtended.FlowNode_QuickSwitchZodiacHourByTag`
**Purpose:** Instantly jumps to a specific zodiac hour identified by tag.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `In` | Exec | Trigger |
| Output | `Out` | Exec | Time switched |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| ZodiacHourTag | GameplayTag | — | Target zodiac hour tag |

---

### FlowNode_QuickSwitchZodiacHourByIndex
**Class:** `/Script/PLFlowGraphExtended.FlowNode_QuickSwitchZodiacHourByIndex`
**Purpose:** Instantly jumps to a specific zodiac hour by numeric index.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `In` | Exec | Trigger |
| Output | `Out` | Exec | Time switched |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| ZodiacHourIndex | int32 | 0 | Target zodiac hour index |

---

### FlowNode_WaitForDayTag
**Class:** `/Script/PLFlowGraphExtended.FlowNode_WaitForDayTag`
**Purpose:** Waits until a specific day tag is reached in the calendar.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `In` | Exec | Start waiting |
| Output | `Out` | Exec | Day tag reached |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| DayTag | GameplayTag | — | Day tag to wait for |

---

### FlowNode_WaitForWeatherTag
**Class:** `/Script/PLFlowGraphExtended.FlowNode_WaitForWeatherTag`
**Purpose:** Waits until the current weather matches a specific tag.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `In` | Exec | Start waiting |
| Output | `Out` | Exec | Weather matched |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| WeatherTag | GameplayTag | — | Weather tag to wait for |

---

### FlowNode_WaitForZodiacHourTag
**Class:** `/Script/PLFlowGraphExtended.FlowNode_WaitForZodiacHourTag`
**Purpose:** Waits until a specific zodiac hour is reached.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `In` | Exec | Start waiting |
| Output | `Out` | Exec | Zodiac hour reached |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| ZodiacHourTag | GameplayTag | — | Zodiac hour tag to wait for |

---

### FlowNode_GetCurrentTime
**Class:** `/Script/PLFlowGraphExtended.FlowNode_GetCurrentTime`
**Purpose:** Gets the current calendar time and outputs via data pins.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `In` | Exec | Trigger |
| Output | `Out` | Exec | Time retrieved |

**Properties:** Outputs time data via data pins (day, hour, zodiac hour tag).

---

### FlowNode_GetCurrentWeather
**Class:** `/Script/PLFlowGraphExtended.FlowNode_GetCurrentWeather`
**Purpose:** Gets the current weather state and outputs via data pins.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `In` | Exec | Trigger |
| Output | `Out` | Exec | Weather retrieved |

**Properties:** Outputs weather data via data pins (weather tag, intensity).

---

## Spawn & Entity Nodes

### FN_SpawnEntityOnCleanUp
**Class:** `/Script/PLFlowGraphExtended.FN_SpawnEntityOnCleanUp`
**Purpose:** Spawns entities when the flow graph cleans up (deferred spawn on flow end).

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| *(none)* | — | — | Fires automatically on flow cleanup |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| EntitySpawnInfos | Array | — | Array of entity spawn configurations |

---

### FN_ConsumeEntityInBag
**Class:** `/Script/PLFlowGraphExtended.FN_ConsumeEntityInBag`
**Purpose:** Consumes entities from an actor's bag/inventory.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `In` | Exec | Trigger |
| Output | `Out` | Exec | Consume succeeded |
| Output | `Failed` | Exec | Consume failed (not enough items) |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| EntityTag | GameplayTag | — | Entity tag to consume |
| ConsumeCount | int | 1 | Number of items to consume |
| IdentityTags | GameplayTagContainer | — | Target actor filter |
| bUsePayloadActors | bool | false | Standard payload flag |

---

### FlowNode_SpawnByGameplayTag
**Class:** `/Script/PLFlowGraphExtended.FlowNode_SpawnByGameplayTag`
**Purpose:** Spawns an entity by looking up the spawn configuration from a gameplay tag.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `In` | Exec | Trigger |
| Output | `Out` | Exec | Spawn succeeded |
| Output | `Failed` | Exec | Spawn failed |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| SpawnTag | GameplayTag | — | Gameplay tag for spawn lookup |
| SpawnTransform | Transform | — | Transform for spawn location |

---

### FlowNode_ProcessEquipmentInBag
**Class:** `/Script/PLFlowGraphExtended.FlowNode_ProcessEquipmentInBag`
**Purpose:** Processes equipment items in an actor's bag (e.g., auto-equip, sort, filter).

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `In` | Exec | Trigger |
| Output | `Out` | Exec | Processing completed |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| EquipmentTag | GameplayTag | — | Equipment tag to process |
| IdentityTags | GameplayTagContainer | — | Target actor filter |
| bUsePayloadActors | bool | false | Standard payload flag |

---

## SubGraph & Flow Control Nodes

### FlowNode_StartRootFlow
**Class:** `/Script/PLFlowGraphExtended.FlowNode_StartRootFlow`
**Purpose:** Starts a new root flow from within the current flow. Unlike SubGraph, this creates an independent root-level flow instance.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `In` | Exec | Trigger |
| Output | `Out` | Exec | Flow started |
| Output | `Failed` | Exec | Failed to start flow |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| FlowAsset | FlowAsset path | — | Path to the FlowAsset to start |
| bCanInstanceIdenticalAsset | bool | false | Allow multiple instances of same asset |

---

### FlowNode_FinishAllRootFlows
**Class:** `/Script/PLFlowGraphExtended.FlowNode_FinishAllRootFlows`
**Purpose:** Finishes all currently running root flows.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `In` | Exec | Trigger |
| Output | `Out` | Exec | All flows finished |

**Properties:** None.

---
## World & Utility Nodes

### FlowNode_GuideTask
**Class:** `/Script/PLFlowGraphExtended.FlowNode_GuideTask`
**Purpose:** Registers and tracks guide/quest tasks. Core quest progression node.
**Usage count:** 85

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `Start` | Exec | Register task |
| Output | `Execute` | Exec | Task processing |
| Output | `AfterRegister` | Exec | Task registered in system |
| Output | `AfterCompleted` | Exec | Task completed |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| RegisterTaskTag | GameplayTag | — | Tag to register the task under |
| RegisterTaskInfo | struct | — | Task info structure |
| GroupTagToComplete | GameplayTag | — | Group tag for completion check |
| SubTaskToComplete | GameplayTag | — | Sub-task tag for completion |
| CompleteCount | int | 0 | Required completion count |
| SuccessLimit | int | 0 | Observer mixin |
| IdentityTags | GameplayTagContainer | — | Observer mixin |

<details><summary>JSON Template</summary>

```json
{
  "Class": "/Script/PLFlowGraphExtended.FlowNode_GuideTask",
  "NodeGuid": "GENERATE-NEW-GUID",
  "NodePosX": 0,
  "NodePosY": 0,
  "inputPins": [
    { "PinName": "Start", "PinToolTip": "Start" }
  ],
  "outputPins": [
    { "PinName": "Execute", "PinToolTip": "Execute" },
    { "PinName": "AfterRegister", "PinToolTip": "AfterRegister" },
    { "PinName": "AfterCompleted", "PinToolTip": "AfterCompleted" }
  ],
  "RegisterTaskTag": "Quest.TaskTag.Here",
  "GroupTagToComplete": "",
  "SubTaskToComplete": "",
  "CompleteCount": 1
}
```

</details>

---

### FlowNode_Log
**Class:** `/Script/Flow.FlowNode_Log`
**Purpose:** Logs a message to the output log and optionally to screen. Essential for debugging.
**Usage count:** 207

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `In` | Exec | Trigger |
| Input | `Message` | String (data) | Override message via data pin |
| Output | `Out` | Exec | After logging |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| Message | string | — | Log message text |
| Verbosity | enum | — | Log verbosity level |
| bPrintToScreen | bool | false | Also print to screen |
| Duration | float | 0.0 | Screen display duration |
| TextColor | Color | — | Screen text color |

---

## Existing Blueprint Nodes

### FN_ChangeWeather_C
**Class:** `/PLFlowGraphExtended/Nodes/FN_ChangeWeather.FN_ChangeWeather_C`
**Purpose:** Changes the in-game weather for a specified duration.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `Start` | Exec | Begin weather change |
| Input | `Interrupt` | Exec | Cancel weather change |
| Output | `WeatherStarted` | Exec | Weather transition began |
| Output | `WeatherRecovered` | Exec | Weather returned to normal |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| Duration | float | — | How long the weather lasts |
| PLWeather | — | — | Weather type enum |
| WeatherTag | GameplayTag | — | Weather identification tag |
| Lock Weather | bool | false | Prevent other weather changes |
| Priority | int | 0 | Weather priority (higher wins) |

---

### FN_PlaySound2D_C
**Class:** `/PLFlowGraphExtended/Nodes/FN_PlaySound2D.FN_PlaySound2D_C`
**Purpose:** Plays a 2D (non-spatialized) sound effect or music.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `In` | Exec | Start playing |
| Input | `Interrupt` | Exec | Stop playing |
| Output | `Out` | Exec | After play started |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| AudioAsset | Asset path | — | Sound asset to play |
| MetaSoundAsset | Asset path | — | MetaSound asset to play |
| Fade in Duration | float | 0.0 | Fade-in time |
| Fade Out Duration | float | 0.0 | Fade-out time |
| FloatParams | — | — | MetaSound float parameters |
| SoundComps | — | — | Sound component references |

---

### FN_ShowTaskGuidance_C
**Class:** `/PLFlowGraphExtended/Nodes/FN_ShowTaskGuidance.FN_ShowTaskGuidance_C`
**Purpose:** Displays task guidance UI overlay with instructions for the player.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `Start` | Exec | Show guidance |
| Input | `Stop` | Exec | Hide guidance |
| Output | `Execute` | Exec | Guidance shown |
| Output | `Completed` | Exec | Guidance dismissed |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| GuidanceText | NSLOCTEXT | — | Localized guidance text |
| IdentityTags | GameplayTagContainer | — | Observer mixin |

---

### FN_ShowEventMessageOnCleanUp_C
**Class:** `/PLFlowGraphExtended/Nodes/FN_ShowEventMessageOnCleanUp.FN_ShowEventMessageOnCleanUp_C`
**Purpose:** Shows an event message when the flow graph cleans up (deferred display on flow end).

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| *(none)* | — | — | Fires automatically on flow cleanup |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| Text | NSLOCTEXT | — | Localized message text |
| Time | float | 0.0 | Display duration |

---

### FN_FinishAllNodesWithAssetTags_C
**Class:** `/PLFlowGraphExtended/Nodes/FN_FinishAllNodesWithAssetTags.FN_FinishAllNodesWithAssetTags_C`
**Purpose:** Finishes all running flow nodes whose assets match specified tags.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `In` | Exec | Trigger |
| Output | `Out` | Exec | Nodes finished |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| AssetTags | GameplayTagContainer | — | Tags to match against running nodes |

---

### FN_DestroySelf_C
**Class:** `/PLFlowGraphExtended/Nodes/FN_DestroySelf.FN_DestroySelf_C`
**Purpose:** Destroys the owning actor of this flow graph.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `In` | Exec | Trigger destruction |
| Output | `Out` | Exec | After destroy initiated |

**Properties:** None.

---

### FN_EndWorldEvent_C
**Class:** `/PLFlowGraphExtended/Nodes/FN_EndWorldEvent.FN_EndWorldEvent_C`
**Purpose:** Ends an active world event.

| Direction | Pin Name | Type | Notes |
|-----------|----------|------|-------|
| Input | `In` | Exec | Trigger |
| Output | `Out` | Exec | World event ended |

**Properties:**

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| WorldEventTag | GameplayTag | — | Tag of the world event to end |

---

## Observer Mixin (Shared Properties)

Many listener/observer nodes share a common set of properties called the "observer mixin". These properties control how the node finds and monitors target actors.

| Property | Type | Default | Notes |
|----------|------|---------|-------|
| IdentityTags | GameplayTagContainer | — | Tags to identify target actors |
| IdentityMatchType | enum | — | How to match tags (Any/All/Exact) |
| SuccessLimit | int | 0 | Max success fires (0 = unlimited) |
| bUsePayloadActors | bool | false | Use payload actors instead of tag search |
| bBindOnAgentComponent | bool | false | Bind to agent component |
| bBindOnIgnoreFlowComp | bool | false | Bind ignoring flow component |

Nodes using observer mixin: `FlowNode_OnTriggerEnter`, `FlowNode_OnTriggerExit`, `FlowNode_OnActorRegistered`, `FlowNode_ListenTagChanged`, `FlowNode_ListenBuildActor`, `FlowNode_ListenTimeChange`, `FlowNode_ListenActorBeHit`, `FN_ListenPlayerAction`, `FlowNode_OnNotifyFromActor`, `FlowNode_ListenBag`, `FN_ShowEventMsg`, `FN_ShowKeyPressTip`, `FlowNode_GuideTask`, `FlowNode_ActionChain`, `FlowNode_ListenEquip`, `FlowNode_ListenAttribute`, `FlowNode_ListenAchievement`, `FlowNode_ListenGameplayAbility`, `FlowNode_ListenWeatherChange`, `FlowNode_ListenPickUp`, `FlowNode_ListenItemGiven`, `FlowNode_ListenPersonaChanged`, `FlowNode_OnInteractionUsed`, `FlowNode_OnCharacterDead`.

---

## Empty Payload Template

When creating a new node from scratch, start with this minimal template and add class-specific properties:

```json
{
  "Class": "/Script/ModuleName.ClassName",
  "NodeGuid": "GENERATE-NEW-GUID",
  "NodePosX": 0,
  "NodePosY": 0,
  "inputPins": [
    {
      "PinName": "In",
      "PinToolTip": "In"
    }
  ],
  "outputPins": [
    {
      "PinName": "Out",
      "PinToolTip": "Out"
    }
  ]
}
```

**GUID generation:** Each node needs a unique GUID. Generate using standard UUID v4 format: `XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX` (uppercase hex).

**Pin connection format:** Connections between nodes are stored in the `linkedTo` array on each pin:

```json
"linkedTo": [
  {
    "NodeGuid": "TARGET-NODE-GUID",
    "PinName": "PinNameOnTarget"
  }
]
```

**Node positioning:** `NodePosX` and `NodePosY` control placement in the graph editor. Use increments of ~300 for horizontal spacing and ~200 for vertical spacing to keep the graph readable.