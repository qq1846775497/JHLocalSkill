# FlowGraphExporter/1.0 — JSON Schema Reference

This document describes the full schema of FlowGraph JSON exports produced by `FFlowExporterTool`.

## Root Object

| Field | Type | Description |
|-------|------|-------------|
| `schema` | `string` | Always `"FlowGraphExporter/1.0"` — identifies the export format version |
| `assetName` | `string` | Name of the FlowAsset (e.g. `"FA_TestCangmuyuan202407"`) |
| `assetPath` | `string` | Full UE asset path including package (e.g. `"/Game/Developers/Chaos/TestFlowGraph/FA_TestCangmuyuan202407.FA_TestCangmuyuan202407"`) |
| `exportTimestamp` | `string` | ISO 8601 UTC timestamp of when the export was generated |
| `nodes` | `Node[]` | Array of all nodes in the FlowGraph |

## Node Object

Each element in the `nodes` array represents one FlowNode.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `nodeGuid` | `string` | Yes | 32-character uppercase hex GUID uniquely identifying this node |
| `nodeClass` | `string` | Yes | Full class path. Native C++ classes use `/Script/ModuleName.ClassName` format. Blueprint classes use `/PluginOrGame/Path/ClassName.ClassName_C` format |
| `nodeTitle` | `string` | Yes | Display title in the editor. May be empty `""` for Blueprint-based nodes that derive their title from the class |
| `editorPosition` | `EditorPosition` | Yes | Node position in the graph editor canvas |
| `inputPins` | `Pin[]` | Yes | Array of input pins (may be empty for Start node) |
| `outputPins` | `Pin[]` | Yes | Array of output pins |
| `connections` | `ConnectionMap` | Yes | Object mapping output pin names to their connection targets |
| `properties` | `PropertyMap` | Yes | Object containing all serialized UPROPERTY values for this node |
| `addOns` | `AddOn[]` | No | Optional array of node add-ons (decorators/modifiers). Only present if the node has add-ons |

### Common Node Classes

| Class | Module | Purpose |
|-------|--------|---------|
| `FlowNode_Start` | `Flow` | Entry point — exactly one per FlowAsset |
| `FlowNode_ExecutionSequence` | `Flow` | Fires numbered outputs (0, 1, 2, ...) in order |
| `FlowNode_ExecutionMultiGate` | `Flow` | Fires one output at a time, cycling through them |
| `FlowNode_Timer` | `Flow` | Delays execution for `CompletionTime` seconds |
| `FlowNode_OnActorRegistered` | `Flow` | Fires when an actor with matching IdentityTags registers |
| `FlowNode_OnTriggerEnter` | `PLFlowGraphExtended` | Fires when a trigger volume is entered |
| `FlowNode_OnTriggerExit` | `PLFlowGraphExtended` | Fires when a trigger volume is exited |
| `FlowNode_ListenTagChanged` | `PLFlowGraphExtended` | Fires when GameplayTags are added/removed on an actor |
| `FlowNode_ListenBuildActor` | `PLFlowGraphExtended` | Fires when a building structure is placed |
| `FlowNode_ExecuteCustomEventOnActor` | `PLFlowGraphExtended` | Sends a GameplayEvent to a matched actor |
| `FN_SetGameplayTag` | `PLFlowGraphExtended` | Adds/removes GameplayTags on matched actors |
| `FN_ChangeWeather_C` | `PLFlowGraphExtended` (BP) | Changes the weather system state |
| `FN_PlaySound2D_C` | `PLFlowGraphExtended` (BP) | Plays 2D audio via SoundWave or MetaSound |
| `FlowNode_ModifyPhaseAttribute` | `PLFlowGraphExtended` | Modifies a phase attribute (stamina, hunger, etc.) |

## EditorPosition Object

| Field | Type | Description |
|-------|------|-------------|
| `x` | `number` | Horizontal position in editor canvas (pixels) |
| `y` | `number` | Vertical position in editor canvas (pixels) |

## Pin Object

Represents an input or output pin on a node.

| Field | Type | Description |
|-------|------|-------------|
| `pinName` | `string` | Internal name used in connections (e.g. `"In"`, `"Out"`, `"0"`, `"Start"`, `"Entered"`) |
| `pinType` | `string` | Pin data type. `"Exec"` for execution flow pins, `"Float"` for data pins |
| `pinFriendlyName` | `string` | Display name override. Empty `""` means use `pinName` |
| `pinToolTip` | `string` | Tooltip text. Empty `""` means no tooltip |

### Pin Naming Conventions
- **Start/In:** Standard input execution pin
- **Out:** Standard output execution pin
- **Stop/Stop Listen/Interrupt:** Pins that halt or interrupt the node's operation
- **0, 1, 2, ...:** Numbered outputs on Sequence and MultiGate nodes
- **Success/Completed/Stopped:** Status-based outputs on observer nodes
- **Custom names:** Event-specific names like `"Entered"`, `"Exited"`, `"WeatherStarted"`, `"WeatherRecovered"`, `"AnyActorBuilt"`
- **Dynamic pins:** Created from GameplayTags, e.g. `"GameplayEffect.PhaseStatus.Burn Added"` on ListenTagChanged

## ConnectionMap Object

An object where each key is an **output pin name** and the value is a connection target.

```json
"connections": {
    "Out": {
        "targetNodeGuid": "9413A47248B05BFB327DDF8A58361206",
        "targetPinName": "In"
    },
    "WeatherStarted": {
        "targetNodeGuid": "80A21E8241D3CA98A4E593B8B25B106E",
        "targetPinName": "In"
    }
}
```

### Connection Target Object

| Field | Type | Description |
|-------|------|-------------|
| `targetNodeGuid` | `string` | GUID of the destination node |
| `targetPinName` | `string` | Name of the input pin on the destination node |

**Notes:**
- An empty `connections: {}` means no output is wired.
- Each output pin can connect to exactly **one** target (unlike Blueprints, FlowGraph uses single-connection outputs).
- Unconnected output pins are simply absent from the `connections` object.

## PropertyMap Object

An untyped object containing all serialized UPROPERTY values for the node. The keys are property names, and the values depend on the property type.

### Property Serialization Rules

| C++ Type | JSON Type | Example |
|----------|-----------|---------|
| `bool` | `boolean` | `"bCheckOverlapWhenStart": false` |
| `int32` | `number` | `"SuccessLimit": 99999` |
| `float` | `number` | `"CompletionTime": 8` |
| `FString` | `string` | `"payloadString": ""` |
| `FName` | `string` | `"IdentityMatchType": "HasAnyExact"` |
| `FGameplayTag` | `object` | `"WeatherTag": { "tagName": "Environment.Weather.StartCave" }` |
| `FGameplayTagContainer` | `object` | `"IdentityTags": { "gameplayTags": [{ "tagName": "Character.Player" }] }` |
| `UObject*` (asset ref) | `string` | `"AudioAsset": "/Script/Engine.SoundWave'/Game/path/to/Asset.Asset'"` |
| `UObject*` (null) | `string` | `"PLWeather": "None"` |
| `FFlowPin` (struct) | `object` | See [FFlowPin Struct](#fflowpin-struct) below |
| `FGameplayTagQuery` | `object` | See [FGameplayTagQuery Struct](#fgameplaytagquery-struct) below |
| `TArray<>` (UE string-serialized) | `string` | `"FloatParams": "((\"Rain Intensity\", 10.000000))"` |
| `Empty struct` | `object` | `"WeatherTimer": {}` |

### FFlowPin Struct

Serialized form of the `FFlowPin` struct, used in `SuccessPin` and similar properties:

```json
{
    "pinName": "Success",
    "pinFriendlyName": "",
    "pinToolTip": "",
    "pinType": "Exec",
    "pinSubCategoryObject": "None",
    "subCategoryClassFilter": "/Script/CoreUObject.Class'/Script/CoreUObject.Class'",
    "subCategoryObjectFilter": "/Script/CoreUObject.Class'/Script/CoreUObject.Object'",
    "subCategoryEnumClass": "None",
    "subCategoryEnumName": ""
}
```

### FGameplayTagQuery Struct

Used for complex tag matching conditions:

```json
{
    "tokenStreamVersion": 0,
    "tagDictionary": [],
    "queryTokenStream": [],
    "userDescription": "",
    "autoDescription": ""
}
```

### FPLFlowPayload Struct

Common payload data structure used by observer/action nodes:

```json
{
    "assetTag": { "tagName": "None" },
    "payloadTags": { "gameplayTags": [] },
    "payloadTags2": { "gameplayTags": [] },
    "spawnEntities": [],
    "payloadString": "",
    "payloadFloats": [],
    "payloadVectors": [],
    "payloadIntegers": [],
    "payloadNames": [],
    "repeatTags": [],
    "payloadBool": []
}
```

## AddOn Object

Optional node add-ons (decorators/modifiers). Structure follows the same pattern as nodes:

| Field | Type | Description |
|-------|------|-------------|
| `addOnClass` | `string` | Full class path of the add-on |
| `properties` | `PropertyMap` | Serialized properties of the add-on |

> **Note:** Add-ons are not present on all nodes. Only nodes that have decorators attached in the editor will include this field.

## Validation Invariants

These invariants must hold for a valid FlowGraph JSON:

1. Exactly one node with `nodeClass` ending in `FlowNode_Start` must exist
2. All `nodeGuid` values must be unique across the `nodes` array
3. All `targetNodeGuid` in connections must reference an existing node's `nodeGuid`
4. All `targetPinName` in connections must match an `inputPins[].pinName` on the target node
5. Connection keys must match one of the node's `outputPins[].pinName`
6. The `schema` field must be `"FlowGraphExporter/1.0"`
