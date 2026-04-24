# Common FlowGraph Bug Patterns

Catalogue of known FlowGraph bugs with JSON-level detection queries and fix recipes. Each entry follows the format:

- **Pattern name**
- **Symptoms** — What goes wrong at runtime
- **Detection** — How to find it in the JSON
- **Fix** — How to correct the JSON
- **Example** — Real-world snippet from project FlowGraphs

---

## 1. Orphaned Listener Nodes

**Symptoms:** A listener node (OnTriggerEnter, OnActorRegistered, etc.) exists in the graph but never activates because no upstream node connects to its `Start` pin.

**Detection:**
```
For each node where nodeClass contains "OnTrigger", "OnActor", "Listen":
  Check if any other node's connections map has a target pointing to this node's "Start" pin
  If not → orphaned
```

**Fix:** Either wire an upstream node's output to the listener's `Start` pin, or remove the listener node entirely if it's leftover from a deleted branch.

**Example:**
A `FlowNode_OnTriggerEnter` at position (224, 16) is properly wired — Start receives from Sequence output `"0"`. But if that Sequence connection were removed, the trigger would become orphaned and never begin listening.

---

## 2. SuccessLimit = 0 (Never Fires Success)

**Symptoms:** An observer node listens forever but never triggers its Success/Completed pin. The `AnyActorBuilt`/`Execute` pins may still fire, but the completion pathway is blocked.

**Detection:**
```
For each node with properties.SuccessLimit === 0:
  Flag as potential bug
  Exception: SuccessLimit=0 is intentional when the node should listen indefinitely
  without ever completing (rare — confirm with design)
```

**Fix:**
```json
// Set to 1 for one-shot completion
"SuccessLimit": 1
// Set to 99999 for effectively unlimited (project convention)
"SuccessLimit": 99999
```

**Example from FA_TestCangmuyuan202407:**
- Node `F771B87944DCDCED0327A2B10359B04A` (ListenTagChanged) has `"SuccessLimit": 0`
- Node `880EF17F41EBF843E25F5C86D215303E` (ListenBuildActor) has `"SuccessLimit": 0`
- Both use dynamic output pins (`AnyActorBuilt`, tag-specific pins) which bypass SuccessLimit. In this case SuccessLimit=0 means the "Success" pin pathway is intentionally disabled. **Verify with designer** whether this is intentional.

---

## 3. Trigger Nodes with Empty IdentityTags

**Symptoms:** The node tries to match actors by GameplayTags but has an empty tag container, so it matches nothing.

**Detection:**
```
For nodes with properties containing "IdentityTags":
  If IdentityTags.gameplayTags is an empty array []
  AND the node class is an action node (ExecuteCustomEvent, SetGameplayTag, etc.)
  → Flag as likely bug
```

**Fix:**
```json
"IdentityTags": {
    "gameplayTags": [
        { "tagName": "Character.Player" }
    ]
}
```

**Note:** Some action nodes intentionally leave IdentityTags empty when using `bUsePayloadActors: true` to target actors from the payload instead. Check `bUsePayloadActors` before flagging.

---

## 4. Connections Pointing to Deleted Nodes

**Symptoms:** A connection exists in the JSON but its `targetNodeGuid` doesn't match any node in the `nodes` array. At runtime, the connection is silently ignored.

**Detection:**
```
allGuids = set(node.nodeGuid for node in nodes)
For each node, for each connection:
  if connection.targetNodeGuid not in allGuids → dangling
```

**Fix:** Remove the broken connection entry from the `connections` object:
```json
// Before
"connections": {
    "Out": { "targetNodeGuid": "DEADBEEF...", "targetPinName": "In" },
    "Success": { "targetNodeGuid": "VALID_GUID", "targetPinName": "Start" }
}
// After
"connections": {
    "Success": { "targetNodeGuid": "VALID_GUID", "targetPinName": "Start" }
}
```

---

## 5. Sequence Nodes with Gaps in Numbered Outputs

**Symptoms:** A Sequence node has outputs `"0"`, `"1"`, `"2"` but only `"0"` and `"2"` are connected. Output `"1"` fires into the void. This may be intentional (the Sequence still fires `"2"` after `"1"` even if `"1"` is unconnected) but can indicate a wiring oversight.

**Detection:**
```
For nodes where nodeClass contains "ExecutionSequence":
  Get list of output pin names: ["0", "1", "2"]
  Get list of connected pins: keys of connections object
  Diff = output pins - connected pins
  If Diff is non-empty → flag
```

**Fix:** Wire the missing output or remove the unused pin from `outputPins` if truly unneeded. Note: removing pins changes the node and may require reimport.

**Example from FA_TestCangmuyuan202407:**
- Node `CBE2516949E97BDD8CC58EAF17504DBA` (Sequence) has outputs `"0"` and `"1"` but only `"0"` is connected. Pin `"1"` is unconnected.

---

## 6. Weather Nodes with PLWeather: None

**Symptoms:** The `FN_ChangeWeather_C` node has `"PLWeather": "None"`. This means the node doesn't reference a weather preset asset directly, relying instead on `WeatherTag` to find the weather.

**Detection:**
```
For nodes where nodeClass contains "ChangeWeather":
  If properties.PLWeather === "None":
    Check if properties.WeatherTag.tagName is a valid tag (not "None")
    If WeatherTag is also "None" → critical: no weather will be applied
```

**Fix:** Either set `PLWeather` to a valid weather asset path, or ensure `WeatherTag` has a valid gameplay tag:
```json
"WeatherTag": { "tagName": "Environment.Weather.StartCave" }
```

**Example from FA_TestCangmuyuan202407:**
All three ChangeWeather nodes have `"PLWeather": "None"` but valid `WeatherTag` values (`StartCave`, `OpenRain`). This is the normal pattern — `WeatherTag` is the primary lookup, `PLWeather` is a legacy direct reference.

---

## 7. Sound Nodes with No Audio Source

**Symptoms:** A `FN_PlaySound2D_C` node has both `"AudioAsset": "None"` and `"MetaSoundAsset": "None"`. No sound will play.

**Detection:**
```
For nodes where nodeClass contains "PlaySound":
  If properties.AudioAsset === "None" AND properties.MetaSoundAsset === "None"
  → No audio source configured
```

**Fix:** Set either `AudioAsset` (for SoundWave) or `MetaSoundAsset` (for MetaSound):
```json
"AudioAsset": "/Script/Engine.SoundWave'/Game/path/to/Sound.Sound'"
// OR
"MetaSoundAsset": "/Script/MetasoundEngine.MetaSoundSource'/Game/path/to/MetaSound.MetaSound'"
```

**Note:** A node with `AudioAsset: "None"` but a valid `MetaSoundAsset` is perfectly fine — the two are alternatives, not both required.

---

## 8. MultiGate with Only One Connected Output

**Symptoms:** A `FlowNode_ExecutionMultiGate` has multiple output pins but only one is connected. With `bLoop: false`, the gate fires once and becomes inert. This effectively makes it a single-use passthrough, which is likely not the designer's intent.

**Detection:**
```
For nodes where nodeClass contains "MultiGate":
  connectedCount = len(connections)
  totalOutputs = len(outputPins)
  If connectedCount === 1 AND totalOutputs > 1 AND bLoop === false
  → Degenerate gate
```

**Fix:** Either connect the remaining outputs or simplify to a direct connection if only one path is needed.

**Example from FA_TestCangmuyuan202407:**
- Node `DF97862445844476693F3B83C7AEEF9D` (MultiGate) has 2 outputs but only `"0"` is connected. `"1"` leads nowhere. With `bLoop: false`, only one path ever fires.
- Node `7E1BD8644B3242CC74878EB8249B0887` (MultiGate) same pattern — 2 outputs, only `"0"` connected.

---

## 9. Dead-End Action Nodes

**Symptoms:** An action node (ExecuteCustomEvent, SetGameplayTag, ModifyPhaseAttribute) has output pins but no outgoing connections. Execution flow terminates here.

**Detection:**
```
For each node where connections === {} AND outputPins.length > 0:
  If nodeClass is an action/command node (not a terminal)
  → Dead end
```

**Fix:** Determine if the dead end is intentional (last step in a chain) or if downstream nodes should be connected.

**Example from FA_TestCangmuyuan202407:**
- Node `4A24162D4FCC64DAA4624FA09B3F6BB1` (ModifyPhaseAttribute) — has `"Out"` pin but `connections: {}`. This is the end of a Timer→ModifyPhaseAttribute chain, likely intentional.
- Node `5FEC522945D31E47E1CA34AB63F34D8D` (PlaySound2D) — has `"Out"` pin but `connections: {}`. This is the last sound in a chain, intentional.

---

## 10. GameplayTagQuery with Empty Token Stream

**Symptoms:** A `SetterCondition` or similar GameplayTagQuery property has an empty `queryTokenStream`, meaning the condition is always true (no filter).

**Detection:**
```
For properties containing a GameplayTagQuery object:
  If queryTokenStream === [] AND tagDictionary === []
  → No condition applied (always passes)
```

**Fix:** Usually intentional (meaning "apply unconditionally"). Only flag if the designer expects conditional behavior.

---

## 11. Dialogue Node with Empty DialogueText

**Symptoms:** A `FN_StartDialogueHUD_FixedText` or `FN_StartDialogueBubble_FixedText` node has an empty or default `DialogueText` property. The dialogue HUD appears but shows no text, or the node fires its completion pins immediately.

**Detection:**
```
For nodes where nodeClass contains "Dialogue" or "DialogueHUD" or "DialogueBubble" or "AutoplayHudText":
  If properties.DialogueText is empty string "", "None", or missing
  → Flag as likely bug
```

**Fix:**
```json
// Set DialogueText to a valid NSLOCTEXT string
"DialogueText": "NSLOCTEXT(\"FlowGraph\", \"UniqueKey\", \"Actual dialogue text here\")"
```

**Note:** Some dialogue nodes intentionally have empty text when used as spacers or timing nodes. Check if `Time` is set to a non-zero value — if so, the node may be used purely for timing.

---

## 12. AIMoveToByTag with No Target

**Symptoms:** An `FN_AIMoveToByTag` node has `TargetActorTag` set to `"None"` and `bUseExactLocation` is `false`. The AI has nowhere to move and the node fires `NotFound` immediately.

**Detection:**
```
For nodes where nodeClass contains "AIMoveToByTag":
  If properties.TargetActorTag.tagName === "None"
  AND properties.bUseExactLocation !== true
  → No movement target configured
```

**Fix:** Either set a valid `TargetActorTag` or enable `bUseExactLocation` with coordinates:
```json
// Option A: Move to tagged actor
"TargetActorTag": { "tagName": "Entity.Campfire" }

// Option B: Move to exact location
"bUseExactLocation": true,
"ExactLocation": { "x": 1000, "y": 2000, "z": 0 }
```

---

## 13. SpawnEntity with Empty EntitySpawnInfos

**Symptoms:** An `FN_SpawnEntity` node has an empty `EntitySpawnInfos` array. Nothing spawns and the node fires `Failed`.

**Detection:**
```
For nodes where nodeClass contains "SpawnEntity":
  If properties.EntitySpawnInfos is an empty array []
  AND properties.bGetSpawnParameterFromPython !== true
  → No entities configured to spawn
```

**Fix:**
```json
"EntitySpawnInfos": [
    {
        "EntityTag": { "tagName": "Entity.Campfire" },
        "SpawnTransform": { /* location/rotation */ }
    }
]
```

**Note:** If `bGetSpawnParameterFromPython` is `true`, spawn info comes from Python pipeline at runtime — empty array is expected.

---

## 14. Teleport with No Destination

**Symptoms:** A `FlowNode_Teleport` node has `TargetActorTag` set to `"None"` and `TeleportOffset` is all zeros. The teleport has no destination.

**Detection:**
```
For nodes where nodeClass contains "Teleport":
  If properties.TargetActorTag.tagName === "None"
  AND (properties.TeleportOffset.x === 0 AND properties.TeleportOffset.y === 0 AND properties.TeleportOffset.z === 0)
  → No teleport destination
```

**Fix:** Set either a target actor tag (teleport to actor) or a teleport offset:
```json
// Option A: Teleport to tagged actor
"TargetActorTag": { "tagName": "Environment.Geography.POI.Camp" }

// Option B: Teleport by offset
"TeleportOffset": { "x": 1000, "y": 0, "z": 0 }
```

---

## 15. GuideTask with Incomplete Configuration

**Symptoms:** A `FlowNode_GuideTask` node is missing either `RegisterTaskTag` or `GroupTagToComplete`. Without `RegisterTaskTag`, the task can't register in the guide system. Without `GroupTagToComplete`, the task can't be marked complete.

**Detection:**
```
For nodes where nodeClass contains "GuideTask":
  If properties.RegisterTaskTag.tagName === "None" OR missing
  → Task cannot register
  If properties.GroupTagToComplete.tagName === "None" OR missing
  → Task cannot complete (may be intentional for persistent tasks)
```

**Fix:**
```json
"RegisterTaskTag": { "tagName": "FlowNode.Task.Guide.BuildFirstCampfire" },
"GroupTagToComplete": { "tagName": "FlowNode.Task.Guide.BuildFirstCampfire" }
```

**Note:** `GroupTagToComplete` being `"None"` is valid for tasks that are completed by other means (e.g., a separate FlowGraph completes the group). Only flag if `RegisterTaskTag` is also missing.

---

## 16. Listener No Stop Wired

**Symptoms:** An observer/listener node has a `Stop` input pin but nothing connects to it. The listener runs forever, never explicitly stopped. Problematic in long-lived flows where the listener should be deactivated after a condition is met elsewhere.

**Detection:**
```
For each node where nodeClass inherits ComponentObserver (OnTrigger*, OnActor*, Listen*, ActionChain):
  Check if the node has a "Stop" inputPin
  If yes, check if any other node's connections target this node's "Stop" pin
  If not → flag as warning
```

**Fix:** Wire a downstream node's output to the listener's `Stop` pin when the listener should be deactivated.

**Note:** WARNING severity. Many listeners intentionally run for the lifetime of the flow.

---

## 17. DoN MaxCount = 0

**Symptoms:** A `FlowNode_DoN` node has `MaxCount` set to 0. The `Execute` output will never fire — the node is effectively dead.

**Detection:**
```
For nodes where nodeClass contains "DoN":
  If properties.MaxCount === 0 → Execute pin will never fire
```

**Fix:**
```json
"MaxCount": 1
```

**Note:** Unlike SuccessLimit=0 on observers (infinite), DoN with MaxCount=0 means "never execute".

---

## 18. bUsePayloadActors Without Upstream Payload Source

**Symptoms:** An action/observer node has `bUsePayloadActors: true` but no upstream node populates the payload with actors. The payload actors list will be empty at runtime.

**Detection:**
```
For nodes with properties.bUsePayloadActors === true:
  Walk upstream connections recursively
  Check if any upstream node produces payload actors
  (OnTriggerEnter, SpawnEntity, SpawnByGameplayTag, TriggerOverlapActors)
  If no source found → flag as warning
```

**Fix:** Either wire through a payload-producing node upstream, or set `bUsePayloadActors: false` and use `IdentityTags` instead.

**Note:** WARNING — may have false positives if payload is populated by parallel branches.

---

## 19. SubGraph Asset = None

**Symptoms:** A SubGraph node has `Asset` set to `"None"`. No child flow to execute.

**Detection:**
```
For nodes where nodeClass contains "SubGraph":
  If properties.Asset === "None" OR missing → No child flow
```

**Fix:**
```json
"Asset": "/Script/Flow.FlowAsset'/Game/FlowGraphs/FA_SubFlow.FA_SubFlow'"
```

---

## 20. Branch Node with No AddOns

**Symptoms:** A `FlowNode_Branch` has no AddOn predicates. Without conditions, it always takes the default path.

**Detection:**
```
For nodes where nodeClass contains "FlowNode_Branch":
  If addOns is empty [] or missing → always takes default path
```

**Fix:** Add AddOn predicates to the `addOns` array. Each AddOn defines a condition for a corresponding output pin.

---

## 21. Timer with Zero Times

**Symptoms:** A Timer has both `CompletionTime=0` and `StepTime=0`. Completes instantly.

**Detection:**
```
For nodes where nodeClass contains "Timer":
  If properties.CompletionTime === 0 AND properties.StepTime === 0 → instant
```

**Fix:**
```json
"CompletionTime": 5.0,
"StepTime": 1.0
```

**Note:** CompletionTime=0 alone is valid if StepTime>0 (infinite timer with periodic steps).

---

## 22. ListenTagChanged with Empty Tag Lists

**Symptoms:** Both `ListenAddedTags` and `ListenRemovedTags` are empty. The node listens for nothing.

**Detection:**
```
For nodes where nodeClass contains "ListenTagChanged":
  If ListenAddedTags.gameplayTags === [] AND ListenRemovedTags.gameplayTags === []
  → listening for nothing
```

**Fix:**
```json
"ListenAddedTags": { "gameplayTags": [{ "tagName": "GameplayEffect.PhaseStatus.Burn" }] }
```

---

## 23. Counter Goal ≤ 0

**Symptoms:** A `FlowNode_PLCounter` has `Goal ≤ 0`. With Goal=0, the counter fires Goal output immediately. Negative values are unreachable by incrementing.

**Detection:**
```
For nodes where nodeClass contains "PLCounter" or "Counter":
  If properties.Goal <= 0 → already finished or unreachable
```

**Fix:**
```json
"Goal": 5
```

---

## 24. Dynamic Pin Node with Empty Tag Container

**Symptoms:** A node generating dynamic output pins from tags (e.g., ActionChain with `ActionNodeTags`) has an empty tag container. No dynamic pins generated.

**Detection:**
```
For nodes where nodeClass contains "ActionChain":
  If properties.ActionNodeTags.gameplayTags === [] → no dynamic outputs
```

**Fix:**
```json
"ActionNodeTags": { "gameplayTags": [{ "tagName": "ActionChain.Step1" }, { "tagName": "ActionChain.Step2" }] }
```

---

## 25. StartRootFlow with No Asset

**Symptoms:** A `FlowNode_StartRootFlow` has no `FlowAsset` set. No flow to instantiate.

**Detection:**
```
For nodes where nodeClass contains "StartRootFlow":
  If properties.FlowAsset === "None" OR missing → no flow to start
```

**Fix:**
```json
"FlowAsset": "/Script/Flow.FlowAsset'/Game/FlowGraphs/FA_TargetFlow.FA_TargetFlow'"
```

---

## Audit Summary Template

When reporting audit results, use this format:

```
## FlowGraph Audit: <AssetName>

### Critical Issues
- [ ] (list critical findings)

### Warnings
- [ ] (list warnings)

### Info
- [ ] (list informational findings)

### Node Summary
- Total nodes: X
- Start nodes: X
- Orphaned nodes: X
- Dead-end nodes: X
- Observer nodes: X (SuccessLimit=0: X)
```
