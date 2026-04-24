# FlowGraph Execution Model — Node Lifecycle Reference

## 1. FlowAsset Lifecycle

A `UFlowAsset` is the top-level container that owns all nodes in a flow graph. Each runtime
instance follows this lifecycle:

```
InitializeInstance(Owner, Template)
        |
        v
  PreStartFlow()
        |
        v
    StartFlow()          -- activates entry node(s)
        |
        v
  [Nodes execute...]     -- nodes move between ActiveNodes / RecordedNodes
        |
        v
  FinishFlow(Policy, bRemoveInstance)
```

### Key Data Structures

| Member | Type | Purpose |
|--------|------|---------|
| `Nodes` | `TMap<FGuid, UPLFlowNode*>` | All nodes in the asset, keyed by GUID |
| `ActiveNodes` | `TArray<UPLFlowNode*>` | Currently executing nodes |
| `RecordedNodes` | `TArray<UPLFlowNode*>` | Finished (completed/aborted) nodes |
| `ActiveSubGraphs` | `TMap<UFlowNode_SubGraph*, UFlowAsset*>` | Running sub-graph instances |
| `NodeOwningThisAssetInstance` | `UFlowNode_SubGraph*` | Back-pointer to parent SubGraph node |

### InitializeInstance

Called once when a flow component spawns a flow. Sets the owning actor/component, clones
nodes from the template asset, and wires up internal references. After this call every node
has a valid `GetFlowAsset()` pointer.

### PreStartFlow / StartFlow

`PreStartFlow()` runs setup logic (e.g. variable initialization) before any node activates.
`StartFlow()` finds the designated entry node(s) and triggers their first input, placing
them into `ActiveNodes`.

### FinishFlow

```cpp
void FinishFlow(EFlowFinishPolicy Policy, bool bRemoveInstance);
```

- **`EFlowFinishPolicy::Keep`** — nodes stay in `RecordedNodes`; the asset instance remains
  alive for save/load or later inspection.
- **`EFlowFinishPolicy::Abort`** — all remaining `ActiveNodes` are force-deactivated, the
  instance can be removed.

`bRemoveInstance` controls whether the owning component destroys the instance after finish.

---

## 2. Node Execution Lifecycle

Each `UPLFlowNode` (extends `UFlowNodeBase`) tracks its own state via `ActivationState`:

```
EFlowNodeState
  NeverActivated ──> Active ──> Completed
                       |
                       └──────> Aborted
```

### State Transitions

```
                  TriggerInput()
NeverActivated ─────────────────> Active
                                    |
                        TriggerOutput(bFinish=true)
                        or Finish()
                                    |
                                    v
                               Completed

Active ───── ForceFinishNode() ──> Aborted
Active ───── Deactivate()  ──────> Aborted
```

### Activation Sequence (detailed)

1. **`TriggerInput(PinName)`** — called by the upstream node or the FlowAsset on start.
2. Asset moves the node into `ActiveNodes`.
3. **`OnActivate(Payload)`** — virtual; node-specific initialization.
4. **`ExecuteInput(PinName, Payload)`** — the main execution entry point.
   - Internally calls `ExecuteInputForSelfAndAddOns()` which dispatches to the node
     itself and all attached `UFlowNodeAddOn` instances.
5. Node performs its work (instant or over time).
6. **`TriggerOutput(PinName, bFinish, ActivationType, CustomPayload)`** — fires an
   output pin, which triggers the connected downstream node's `TriggerInput()`.
   - If `bFinish == true`, the node transitions to `Completed` after triggering.
7. **`Finish()`** — explicit completion without triggering an output.
8. **`Deactivate()`** / **`Cleanup()`** — teardown; node moves to `RecordedNodes`.

### Signal Mode

`EFlowSignalMode` modifies how `TriggerInput` behaves:

| Mode | Behavior |
|------|----------|
| `Enabled` | Normal full execution — `OnActivate` + `ExecuteInput` run |
| `Disabled` | Input is completely ignored; node instantly deactivates without executing |
| `PassThrough` | No internal logic runs; all output pins are immediately triggered |

`PassThrough` is useful for debugging or temporarily bypassing a node without rewiring
the graph.

### Dirty Output Buffering

Nodes that produce multiple outputs over time use the dirty-output system:

```cpp
bool bFinishDirty;                       // finish is pending
TArray<FName> DirtyOutputCaches;         // outputs queued for dispatch
```

When `bFinishDirty` is set, the node collects output pin names in `DirtyOutputCaches`
and flushes them in batch. This prevents race conditions when a node fires several
outputs within the same frame.

### AddOn System

`UFlowNodeBase` supports an array of `UFlowNodeAddOn*` objects. When `ExecuteInput` is
called, `ExecuteInputForSelfAndAddOns()` dispatches the call to the node first, then to
every AddOn in order. AddOns can inject pre/post logic without subclassing the node.

### Content Lifecycle Hooks

```
PreloadContent()       -- request async loads before activation
OnActivate()           -- node enters Active state
ExecuteInput()         -- main logic
Finish() / Deactivate()
FlushContent()         -- release loaded assets
DeinitializeInstance() -- final teardown when asset instance is destroyed
```

---

## 3. Observer Pattern

`UFlowNode_ComponentObserver` is the abstract base for nodes that watch the world for
actor/component registration events driven by gameplay tags.

### Properties

| Property | Type | Purpose |
|----------|------|---------|
| `IdentityTags` | `FGameplayTagContainer` | Tags to match against FlowComponents |
| `IdentityMatchType` | `EFlowTagContainerMatchType` | Matching strategy |
| `SuccessLimit` | `int32` | How many events before auto-completing (0 = infinite) |
| `SuccessCount` | `int32` (SaveGame) | Current event counter |
| `bUsePayloadActors` | `bool` | Match only actors from incoming payload |
| `RegisteredActors` | `TMap<AActor*, (FlowComponent, Payload)>` | Tracked actors |

### Tag Match Types

```
EFlowTagContainerMatchType
  HasAny        -- target has at least one of IdentityTags
  HasAnyExact   -- exact match (no parent tag matching)
  HasAll        -- target has all of IdentityTags
  HasAllExact   -- exact match variant
```

### Execution Flow

```
TriggerInput("Start")
      |
      v
  StartObserving()          -- registers with FlowSubsystem for tag events
      |
      v
  [world events arrive]
      |
      ├─ OnComponentRegistered(Tag, Component)
      |      └─ ObserveActor()    -- virtual, subclass hook
      |
      ├─ OnComponentTagAdded(Component, Tag)
      |
      ├─ OnComponentTagRemoved(Component, Tag)
      |
      └─ OnComponentUnregistered(Tag, Component)
             └─ ForgetActor()    -- virtual, subclass hook
      |
      v
  OnEventReceived()
      |  increments SuccessCount
      |  if SuccessCount >= SuccessLimit (and limit > 0):
      |      TriggerOutput(SuccessPin, bFinish=true)
      v
  StopObserving()           -- unregisters from FlowSubsystem
```

`CurrentObservingPayload` carries context about the most recent event.
`ForceUseFlowNodePayload` overrides payload with the node's own `FlowNodePayload`.

---

## 4. ActorAction Pattern

`UFlowNode_ActorAction` executes logic on one or more actors that match tag criteria.
Unlike observers (which wait for events), actor-action nodes run immediately on matching
actors found in the world.

### Properties

| Property | Type | Purpose |
|----------|------|---------|
| `IdentityTags` | `FGameplayTagContainer` | Tags to match |
| `IdentityMatchType` | `EFlowTagContainerMatchType` | Matching strategy |
| `bUsePayloadActors` | `bool` | Use actors from payload instead of world query |
| `bBindOnAgentComponent` | `bool` | Bind to agent's FlowComponent |
| `bBindOnIgnoreFlowComp` | `bool` | Skip FlowComponent binding |
| `FocusedActors` | `TMap<AActor*, UFlowComponent*>` | Resolved actor set |
| `CurrentPayload` | Payload | Active payload for the execution |

### ExecuteInput Pipeline

```
ExecuteInput(PinName, Payload)
      |
      v
  SetupMatchType()
      |
      v
  ValidateRequiredComponents()
      |
      v
  ShouldProcessInput()          -- guard; subclass can reject
      |
      v
  ProcessActorsAndExecuteActions()
      |
      ├─ SetupFocusedActors()       -- if NOT using payload actors
      |      query world for matching FlowComponents
      |
      └─ SetupPayloadActors()       -- if using payload actors
             extract actors from incoming payload
      |
      v
  ExecuteActions()               -- called per resolved actor
      |  subclass implements actual gameplay effect
      v
  [optionally TriggerOutput]
```

The two-path resolution (`FocusedActors` vs `PayloadActors`) lets designers choose
between "affect all tagged actors in the world" and "affect only the actors that
triggered this flow branch."

---

## 5. Payload System

Payloads carry contextual data through the flow graph. Each node has:

```cpp
FPLFlowNodePayload FlowNodePayload;       // node-local payload data
EPLFlowPayloadSource PayloadSource;        // where to read payload from
```

### Payload Sources

| Source | Behavior |
|--------|----------|
| `FlowNodeCustom` | Use this node's own `FlowNodePayload` |
| `ActionChainPayload` | Inherit payload from the parent ActionChain |
| `TaggedPayload` | Resolve payload by gameplay tag lookup |
| `PayloadFromLastNode` | Use the payload output of the previous node in the chain |

### Payload Flow Through the Graph

When `TriggerOutput` fires:

```cpp
void TriggerOutput(FName PinName, bool bFinish,
                   EFlowPinActivationType ActivationType,
                   FPLFlowNodePayload* CustomPayload);
```

If `CustomPayload` is provided it overrides the default. Otherwise the downstream node
resolves its payload via its own `PayloadSource` setting. This creates a flexible
data-passing mechanism:

```
[NodeA] ──payload──> [NodeB: PayloadFromLastNode] ──payload──> [NodeC: FlowNodeCustom]
                      uses A's output                           uses its own data
```

Observer nodes populate `CurrentObservingPayload` from the triggering event, making
event context (actor, component, tags) available to downstream nodes.

---

## 6. Save/Load

The FlowGraph system supports full serialization for game saves.

### Data Structures

```
FFlowNodeSaveData
  ├─ NodeGuid      : FGuid           -- identifies the node in the asset
  └─ NodeData      : TArray<uint8>   -- serialized via FFlowArchive

FFlowAssetSaveData
  ├─ WorldName     : FString
  ├─ InstanceName  : FString
  ├─ AssetData     : TArray<uint8>   -- asset-level serialized state
  └─ NodeRecords   : TArray<FFlowNodeSaveData>

FFlowComponentSaveData
  ├─ WorldName         : FString
  ├─ ActorInstanceName : FString
  └─ ComponentData     : TArray<uint8>
```

### Node Save/Load Cycle

```
Save:
  FlowAsset iterates ActiveNodes + RecordedNodes
      |
      v
  node->SaveInstance(NodeRecord)
      |  serializes ActivationState + any UPROPERTY(SaveGame) fields
      |  via FFlowArchive into NodeData byte array
      v
  node->OnSave()                    -- virtual; custom save logic

Load:
  FlowAsset recreates nodes from template
      |
      v
  node->LoadInstance(NodeRecord)
      |  deserializes NodeData back into UPROPERTYs
      v
  node->OnLoad()                    -- virtual; custom restore logic
      |
      v
  nodes with ActivationState==Active are re-added to ActiveNodes
```

Properties marked `UPROPERTY(SaveGame)` are automatically serialized. Key saved fields
include:
- `ActivationState` on `UPLFlowNode`
- `SuccessCount` on `UFlowNode_ComponentObserver`

### What Gets Saved

| Scope | Saved Data |
|-------|-----------|
| Per-node | GUID + all `SaveGame` UPROPERTYs (activation state, counters, custom data) |
| Per-asset | World context, instance name, all node records |
| Per-component | World name, actor instance name, component state |

SubGraph instances are saved recursively — the parent asset saves its `ActiveSubGraphs`
entries, each of which saves its own child FlowAsset state.

---

## 7. Dynamic Pin System

### ActionChain Dynamic Outputs

`UFlowNode_ActionChain` extends `ComponentObserver` and generates output pins dynamically
from `ActionNodeTags`:

```cpp
FGameplayTagContainer ActionNodeTags;    // each tag becomes an output pin
```

`RefreshOutputPins()` rebuilds the `OutputPins` array from the tag container. Each tag
maps to a named output pin, enabling data-driven branching where designers add/remove
outputs by editing tags rather than code.

### ActionChain Delegates

The ActionChain fires delegates at each stage:

```
OnActionChainStarted
    |
    v
OnActionNodeStarted ──> [node executes] ──> OnActionNodeCompleted
    |                                              |
    v                                              v
  (next node)                              OnActionChainCompleted
    |
    ├─ OnActionChainPaused        (chain suspended)
    ├─ OnActionChainInterrupted   (chain broken externally)
    └─ OnActionChainCleared       (chain reset)
```

### Standard Pin Arrays

All nodes inherit from `UFlowNodeBase`:

```cpp
TArray<FFlowPin> InputPins;     // named input pins
TArray<FFlowPin> OutputPins;    // named output pins
TMap<FName, FConnectedPin> Connections;  // output pin name → connected input pin
```

Connections map an output pin name to the GUID + pin name of the downstream node.
`TriggerOutput(PinName)` looks up `Connections[PinName]` to find and activate the
next node.

---

## 8. SubGraph Relationship

`UFlowNode_PLSubGraph` (extends `UFlowNode_SubGraph`) enables hierarchical flow
composition by embedding one FlowAsset inside another.

### Structure

```
Parent FlowAsset
  ├─ Node A
  ├─ Node B
  └─ SubGraph Node ─────────────> Child FlowAsset (instance)
       │                              ├─ Custom Input Node
       │  CustomInputs/Outputs        ├─ Internal Nodes...
       └──────────────────────────────└─ Custom Output Node
```

### Lifecycle

1. Parent flow triggers the SubGraph node's input.
2. SubGraph node creates a child `UFlowAsset` instance from its referenced asset.
3. Child instance is stored in parent's `ActiveSubGraphs` map.
4. Child's `NodeOwningThisAssetInstance` points back to the SubGraph node.
5. `StartFlow()` on the child begins execution of its internal nodes.
6. When the child finishes (or a custom output fires), control returns to the parent.

### Custom Inputs/Outputs

SubGraphs communicate with their parent through custom I/O:

```cpp
// On the child FlowAsset:
TArray<FName> CustomInputs;
TArray<FName> CustomOutputs;

void TriggerCustomInput(FName InputName);   // called by parent → child
void TriggerCustomOutput(FName OutputName); // called by child → parent
```

- **Custom Inputs**: The parent SubGraph node can trigger named inputs on the child,
  allowing parameterized entry points beyond the default start node.
- **Custom Outputs**: The child triggers a custom output to signal the parent. The
  SubGraph node maps these to its own output pins, allowing the child's result to
  drive branching in the parent graph.

### Nested SubGraphs

SubGraphs can nest arbitrarily. Each level maintains its own `ActiveSubGraphs` map.
Save/load recurses through the hierarchy — the parent saves each active SubGraph's
child FlowAsset, which in turn saves its own nodes and any deeper SubGraphs.

---

## Quick Reference: Key Methods by Class

### UFlowAsset

| Method | Purpose |
|--------|---------|
| `InitializeInstance()` | Clone nodes from template, set owner |
| `PreStartFlow()` | Pre-activation setup |
| `StartFlow()` | Activate entry node(s) |
| `FinishFlow()` | End execution with Keep or Abort policy |
| `TriggerCustomInput()` | Fire named input on child (for SubGraph) |
| `TriggerCustomOutput()` | Signal parent from child (for SubGraph) |

### UPLFlowNode

| Method | Purpose |
|--------|---------|
| `TriggerInput()` | Receive activation from upstream |
| `OnActivate()` | Virtual; node-specific init |
| `ExecuteInput()` | Virtual; main execution logic |
| `TriggerOutput()` | Fire named output pin, optionally finish |
| `TriggerFirstOutput()` | Convenience — triggers first output pin |
| `Finish()` | Complete without triggering output |
| `Deactivate()` | Force-stop and cleanup |
| `SaveInstance()` / `LoadInstance()` | Serialize/deserialize state |

### UFlowNode_ComponentObserver

| Method | Purpose |
|--------|---------|
| `StartObserving()` | Register for world events |
| `StopObserving()` | Unregister |
| `ObserveActor()` | Virtual hook when actor matches |
| `ForgetActor()` | Virtual hook when actor unregisters |
| `OnEventReceived()` | Increment counter, check success limit |

### UFlowNode_ActorAction

| Method | Purpose |
|--------|---------|
| `SetupMatchType()` | Configure tag matching |
| `ValidateRequiredComponents()` | Pre-check |
| `ProcessActorsAndExecuteActions()` | Resolve actors and run |
| `ExecuteActions()` | Virtual; per-actor logic |
