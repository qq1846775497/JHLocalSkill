# FlowGraph Wiring Patterns

Common wiring patterns found across 177 FlowGraph exports. Use these as templates when building or modifying flow logic.

---

## 1. Start → Sequence → Parallel Listeners

The most common entry pattern. Start fires into a Sequence that fans out to multiple listeners running in parallel.

```
[Start] ──Out──> [Sequence]
                    ├── 0 ──> [ListenPlayerAction] (interaction)
                    ├── 1 ──> [OnTriggerEnter] (area detection)
                    └── 2 ──> [ListenTimeChange] (time-based)
```

Each listener independently watches for its condition. Use `bSavePinExecutionState: true` on the Sequence so branches resume correctly after save/load.

---

## 2. Dialogue Chain (DialogueFInished Chaining)

Sequential dialogue lines connected via `DialogueFInished` pins. Note: the pin name `DialogueFInished` has a capital I — this is the actual pin name in the JSON, not a typo.

```
[DialogueHUD_1] ──DialogueFInished──> [DialogueHUD_2] ──DialogueFInished──> [DialogueHUD_3]
     │                                      │                                      │
     └─AllFinished─> ...              └─AllFinished─> ...                └─AllFinished─> [next]
```

Pin mapping:
- `DialogueFInished` — fires when current line finishes displaying (player pressed continue)
- `AllFinished` — fires when all queued lines complete (use on last node in chain)
- `ProceedToNext` — fires when auto-advancing (for `FN_AutoplayHudTextFixed`)

---

## 3. Dialogue → Selection → Branch

Player dialogue followed by a choice menu. Selection node creates dynamic `Option_` output pins.

```
[DialogueHUD] ──DialogueFInished──> [StartSelectionHUD]
                                        ├── Option_Yes ──> [branch A]
                                        ├── Option_No  ──> [branch B]
                                        └── PlayerSelectedAnything ──> [common followup]
```

The `Option_` pin names are generated from the `Options` NSLOCTEXT array in properties. Each option text becomes a pin name prefixed with `Option_`.

---

## 4. Listener → Action Chain

A listener detects a condition, then triggers a sequence of gameplay actions.

```
[ListenPlayerAction] ──Success──> [Sequence]
                                     ├── 0 ──> [SetGameplayTag] (mark progress)
                                     ├── 1 ──> [ShowEventMsg] (feedback)
                                     └── 2 ──> [PlayMontageAction] (animation)
```

The `Success` pin fires when the listened condition is met. Wire through a Sequence to perform multiple actions in response.

---

## 5. DoN Gating (First-Time vs Repeat)

`FlowNode_DoN` gates execution to fire only N times. Common for first-time tutorials.

```
[trigger] ──> [DoN (N=1)]
                 ├── Execute ──> [first-time tutorial flow]
                 └── Completed ──> [repeat/skip flow]
```

- `Execute` fires on each activation up to N times
- `Completed` fires after the Nth activation
- Wire `Reset` input to allow re-triggering

---

## 6. AI Movement Sequence

Chain of AI commands: move to location → play animation → wait → continue.

```
[AIMoveToByTag] ──Success──> [PlayMontageAction] ──Completed──> [Wait] ──Completed──> [next]
       │                            │
       └── Fail ──> [fallback]      └── Failed ──> [error handling]
```

Key properties:
- `AIMoveToByTag`: Set `DesiredGaitTagAtStart` for walk/run speed, `AcceptanceRadius` for arrival distance
- `PlayMontageAction`: Set `TriggerByEventTag` and `AbilityClass` for the animation
- `Wait`: Set `WaitTime` for pause duration between actions

---

## 7. SubGraph Delegation

Delegate complex logic to a sub-FlowAsset via `FlowNode_PLSubGraph`.

```
[trigger] ──> [PLSubGraph (Asset=FA_SubFlow)]
                 ├── Finish ──> [continue main flow]
                 └── Force Finished ──> [cleanup]
```

Properties:
- `Asset` — path to the sub-FlowAsset
- `IsInEventManager` — whether the subgraph runs in the event manager context
- `bCanInstanceIdenticalAsset` — allow multiple instances of the same sub-asset

Wire `Force Finish` input to abort the subgraph externally.

---

## 8. LogicalOR Convergence

Multiple paths converge into a single continuation using `FlowNode_LogicalOR`.

```
[path A] ──> [LogicalOR] ──Out──> [shared continuation]
[path B] ──>      │
[path C] ──>      │
```

Input pins are numbered (`0`, `1`, `2`, ...). Any input firing triggers `Out`. Use `Enable`/`Disable` inputs to dynamically gate the OR.

Properties:
- `bEnabled` — initial enabled state
- `ExecutionLimit` — max times Out can fire (0 = unlimited)

For AND logic (all paths must fire), use `FlowNode_LogicalAND` instead.

---

## Payload Usage Guide

### What is Payload?

`FPLFlowPayload` is a data bundle passed between nodes at runtime. It carries actors, tags, strings, floats, vectors, and integers.

### JSON vs Runtime

In the JSON export, payload fields appear in `CurrentPayload` or `CurrentObservingPayload` properties. These are **default/initial values** — at runtime, the payload is populated dynamically by upstream nodes.

### Key Payload Properties

| Property | Type | Purpose |
|----------|------|---------|
| `assetTag` | GameplayTag | Identifies the payload source asset |
| `payloadTags` | GameplayTagContainer | Primary tag set passed with payload |
| `payloadTags2` | GameplayTagContainer | Secondary tag set |
| `spawnEntities` | Array | Entity spawn info for SpawnEntity nodes |
| `payloadString` | String | Arbitrary string data |
| `payloadFloats` | Float[] | Numeric parameters |
| `payloadVectors` | Vector[] | Location/direction data |
| `payloadIntegers` | Int[] | Integer parameters |
| `payloadNames` | Name[] | UE Name values |
| `payloadBool` | Bool[] | Boolean flags |

### bUsePayloadActors

When `bUsePayloadActors: true` on an action/observer node:
- The node ignores `IdentityTags` for actor matching
- Instead, it operates on actors passed via the runtime payload
- This is how upstream nodes "hand off" specific actors to downstream nodes

### Common Payload Patterns

1. **Trigger → Action with payload**: OnTriggerEnter captures the entering actor in payload → downstream ExecuteCustomEvent uses `bUsePayloadActors: true` to target that specific actor
2. **SpawnEntity → Configure**: SpawnEntity puts spawned actors in payload → downstream SetGameplayTag uses payload actors to tag them
3. **Empty payload in JSON is normal**: Most `CurrentPayload` objects in JSON are empty templates — the actual data flows at runtime

---

## 9. ActionChain Observer

Monitor multi-step action chains with per-step output pins. The `ActionNodeTags` property generates dynamic output pins — one per tag.

```
[trigger] ──> [ActionChain]
                 ├── Start ──> [feedback: chain started]
                 ├── ActionChain.Step1 ──> [SetGameplayTag: mark step 1]
                 ├── ActionChain.Step2 ──> [PlayMontageAction: step 2 anim]
                 ├── ActionChain.Step3 ──> [ShowEventMsg: step 3 feedback]
                 ├── Success ──> [chain complete flow]
                 └── Interrupted ──> [cleanup/retry flow]
```

Key properties:
- `ActionNodeTags`: Each tag in this container generates a dynamic output pin named after the tag
- `IdentityTags`: Which actor to observe for action chain events
- `SuccessLimit`: How many chain completions before the node finishes (0 = unlimited)

Dynamic pin names match the tag names exactly. When the corresponding action node in the chain starts, the matching pin fires.

---

## 10. Calendar-Gated Flow

Gate flow progression on calendar/time conditions. Use `WaitForZodiacHourTag` to pause until a specific time, and `Lock/UnlockCalendar` to freeze/resume time progression during critical sequences.

```
[trigger] ──> [LockCalendar] ──Out──> [Sequence]
                                         ├── 0 ──> [ChangeWeather (OpenRain)]
                                         ├── 1 ──> [dialogue/cutscene]
                                         └── 2 ──> [UnlockCalendar] ──Out──> [WaitForZodiacHourTag (Wu)]
                                                                                  └── Out ──> [next phase]
```

Key patterns:
- **Lock before weather change**: Prevents calendar from advancing while setting up a specific weather/time state
- **WaitForZodiacHourTag**: Pauses until the specified zodiac hour arrives (e.g., `Environment.Calendar.ZodiacHour.Wu` for noon)
- **QuickSwitchZodiacHourByTag**: Instantly jumps to a zodiac hour (use for cutscene time-of-day setup)
- Always `UnlockCalendar` after locking — forgetting to unlock freezes the game calendar permanently

---

## 11. Conditional Branch with AddOn Predicates

Route flow based on runtime conditions using `FlowNode_Branch` with AddOn predicates. Each AddOn defines a condition; the Branch evaluates them and activates the matching output pin.

```
[trigger] ──> [Branch]
                 ├── Condition_HasTag ──> [path A: actor has required tag]
                 ├── Condition_WeatherMatch ──> [path B: weather matches]
                 └── Default ──> [path C: fallback/else]
```

Key mechanics:
- **AddOns define conditions**: `FlowNodeAddOn_PredicateAND`, `FlowNodeAddOn_PredicateOR`, `FlowNodeAddOn_PredicateNOT`
- Each AddOn corresponds to a numbered/named output pin
- The `Default` pin fires when no AddOn condition is met
- AddOns are evaluated in order; first match wins
- A Branch with NO AddOns always fires Default (see Bug Pattern #20)

Properties in AddOns:
- Predicate AddOns check gameplay tags, attribute values, weather state, or custom conditions
- Multiple AddOns can be nested (AND/OR/NOT logic)

> **Tip:** For simple tag checks, prefer `FlowNode_ActorHasTags` (dedicated condition node) over a Branch with AddOns. Use Branch when you need compound conditions or multiple output paths.
