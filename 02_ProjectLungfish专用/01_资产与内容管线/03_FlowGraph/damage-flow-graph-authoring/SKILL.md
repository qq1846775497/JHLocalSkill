---
name: damage-flow-graph-authoring
description: Create and modify damage processing nodes for the DamageFlowGraph system in ProjectLungfish. Use when user mentions "damage flow graph", "DamageFlowGraph", "damage flow node", "UPLDamageFlowNode", "伤害流图", "添加伤害节点", "damage processing flow", "ProcessDamageInfo", or needs to add/modify damage calculation steps in the visual node graph. Covers node creation pattern, routing mechanism, output pin naming, and editor integration.
---

# DamageFlowGraph Node Authoring

## System Overview

DamageFlowGraph is a visual node-based editor for configuring damage processing pipelines. Each node modifies `FPLDamageInfo` and routes to the next node via named output pins.

**Runtime files**: `Main/Plugins/GASExtendedPL/Source/GASExtendedPL/Public|Private/Damage/`
**Editor files**: `Main/Plugins/GASExtendedPL/Source/GASExtendedPLEditor/`

---

## Core Architecture

### Routing Mechanism

Each node returns a pin name string → base class looks up the connected node tag:

```cpp
// Node implements this:
FName ProcessDamageInfoInternal(const UObject* WorldContext, FPLDamageInfo& DamageInfo);
// returns "Success", "Failed", or any custom pin name

// Base class wrapper (automatic):
void ProcessDamageInfo(...)
{
    FName PinName = ProcessDamageInfoInternal(WorldContext, DamageInfo);
    NextProcessorTag = GetOutputConnectionTag(PinName);  // looks up TMap
}
```

`OutputConnections` (`TMap<FName, FGameplayTag>`) is populated by the visual editor when wires are drawn.

### Execution Flow

```
PLDamageManagerComponent::DoOffense()
    → start at InputDamageFlowNodeTag
    → find node in DamageFlowNodeMaps
    → ProcessDamageInfo() → get pin name → get next tag
    → repeat loop
    → always runs FinisherDamageFlow at end
```

---

## Creating a Custom Node

### Header Template

```cpp
// GASExtendedPL/Source/GASExtendedPL/Public/Damage/DamageFN_MyNode.h
UCLASS()
class UDamageFN_MyNode : public UPLDamageFlowNode
{
    GENERATED_BODY()
public:
    UDamageFN_MyNode();

protected:
    virtual FName ProcessDamageInfoInternal(
        const UObject* WorldContext, FPLDamageInfo& DamageInfo) override;

public:
    UPROPERTY(EditAnywhere, Category = "Damage")
    float DamageMultiplier = 1.0f;
};
```

### Implementation Template

```cpp
// GASExtendedPL/Source/GASExtendedPL/Private/Damage/DamageFN_MyNode.cpp
UDamageFN_MyNode::UDamageFN_MyNode()
{
    // Declare output pins (editor-only)
#if WITH_EDITORONLY_DATA
    OutputPinNames = { TEXT("Success"), TEXT("Failed") };
#endif
}

FName UDamageFN_MyNode::ProcessDamageInfoInternal(
    const UObject* WorldContext, FPLDamageInfo& DamageInfo)
{
    DamageInfo.Damage *= DamageMultiplier;
    return DamageInfo.Damage > 0.f ? TEXT("Success") : TEXT("Failed");
}
```

---

## Output Pin Patterns

### Two-Output (Condition Branch)
```cpp
OutputPinNames = { TEXT("Success"), TEXT("Failed") };
// return TEXT("Success") or TEXT("Failed")
```

### Multi-Output (Switch/Router)
```cpp
OutputPinNames = { TEXT("Physical"), TEXT("Fire"), TEXT("Ice"), TEXT("Default") };

FName ProcessDamageInfoInternal(...)
{
    switch (DamageInfo.DamageType)
    {
        case EDamageType::Physical: return TEXT("Physical");
        case EDamageType::Fire:     return TEXT("Fire");
        case EDamageType::Ice:      return TEXT("Ice");
        default:                    return TEXT("Default");
    }
}
```

### Single Pass-Through
```cpp
OutputPinNames = { TEXT("Success") };
// Always return TEXT("Success")
```

---

## Common Graph Patterns

```
// Conditional branch
[CheckDefense]
  ├─ Success → [ApplyDefenseReduction]
  └─ Failed  → [ApplyFullDamage]

// Sequential pipeline
[CalculateBase] → [ApplyCritMultiplier] → [ApplyResistance] → [Finisher]

// Type switch
[DamageTypeSwitch]
  ├─ Physical → [ApplyArmor]
  ├─ Fire     → [ApplyFireResistance]
  └─ Default  → [ApplyBaseDamage]
```

---

## Node Tag Naming Convention

Use hierarchy: `AssetTag.FlowNode.Damage.<Category>.<NodeName>`

Examples:
- `AssetTag.FlowNode.Damage.CheckDefense`
- `AssetTag.FlowNode.Damage.ApplyFireResistance`

---

## Using the Visual Editor

1. **Open**: Double-click a `UPLDamageFlowGraph` asset in Content Browser
2. **Add node**: Drag from palette OR right-click graph → select from "Damage Flow Nodes"
3. **Connect**: Drag from output pin (right) → drop on input pin (left)
4. **Edit properties**: Select node → Details panel
5. **Validate**: Click **Validate** button in toolbar — checks disconnected nodes, invalid connections, circular refs
6. **Auto-layout**: Click **Auto Arrange** to hierarchically position nodes

---

## Troubleshooting

| Problem | Check |
|---------|-------|
| Node not in palette | Inherits `UPLDamageFlowNode`? `Abstract` removed from UCLASS? Recompiled + restarted editor? |
| Connections not saving | `SyncPinConnectionsToOutputConnections()` called on schema `TryCreateConnection()`? Asset marked dirty? |
| Runtime routing fails | `OutputConnections` has entry for the pin name returned? Connected node tag exists in `DamageFlowNodeMaps`? |
| Graph not loading | `RebuildGraphFromAsset()` called on asset open? PostLoad serialization OK? |

### Enable Logging

```ini
# DefaultEngine.ini
[Core.Log]
LogDamageFlow=Verbose
```

Log output:
```
LogDamageFlow: Processing node 'DamageFN_CheckDefense' (Tag: AssetTag.FlowNode.Damage.CheckDefense)
LogDamageFlow: Output pin 'Success' -> Next tag: AssetTag.FlowNode.Damage.ApplyDefenseReduction
```

---

## Key Classes Reference

| Class | Location | Purpose |
|-------|----------|---------|
| `UPLDamageFlowNode` | GASExtendedPL/Public/Damage/ | Base runtime node |
| `UPLDamageFlowGraph` | GASExtendedPL/Public/Damage/ | Runtime asset container |
| `UDamageFlowGraph` | GASExtendedPLEditor/ | Editor visual graph |
| `UDamageFlowGraphNode` | GASExtendedPLEditor/ | Editor visual node |
| `UDamageFlowGraphSchema` | GASExtendedPLEditor/ | Graph connection rules |
| `FDamageFlowGraphEditor` | GASExtendedPLEditor/ | Slate asset editor |

---

## Performance Notes

- Typical graphs: 10-20 nodes; max recommended ~50
- Each `ProcessDamageInfo` call is O(1); total is O(N executed nodes)
- Node instance: ~1-2 KB; typical graph: ~50-100 KB
- Graph visualization is editor-only (zero runtime cost)
