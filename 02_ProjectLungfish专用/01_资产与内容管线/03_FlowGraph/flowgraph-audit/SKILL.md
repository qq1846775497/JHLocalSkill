---
name: flowgraph-audit
title: FlowGraph JSON Audit & Fix
description: Audit and fix FlowGraph asset bugs via exported JSON. Use when user mentions "flow graph bug", "flow audit", "fix flow", "FlowAsset", "flow JSON", or when diagnosing broken FlowGraph logic, orphaned nodes, missing connections, or incorrect property values in exported FlowGraphExports/*.json files.
tags: [FlowGraph, JSON, Audit, Bug-Fix, Automation]
---

# FlowGraph JSON Audit & Fix

## Overview

FlowGraph assets (UFlowAsset) drive event-based gameplay logic in ProjectLungfish — triggers, weather changes, sound playback, timers, and more. Bugs in these graphs (orphaned nodes, dangling connections, bad property values) cause silent runtime failures that are hard to diagnose visually in the editor.

This skill uses the **export → audit → fix → reimport** pipeline:
1. **Export** a FlowAsset to JSON via `FFlowExporterTool` (editor utility)
2. **Audit** the JSON programmatically against a checklist of known bug patterns
3. **Fix** issues by editing the JSON directly
4. **Reimport** the corrected JSON via `FFlowImporterTool` to update the asset

## Quick Start

### Step 1 — Export
Export is done from the Unreal Editor via `FFlowExporterTool`. The JSON lands in:
```
Main/FlowGraphExports/<AssetName>.json
```

### Step 2 — Audit
Read the exported JSON and run through the [Audit Checklist](#audit-checklist) below. Report all findings with node GUIDs and property paths.

### Step 3 — Fix & Reimport
Edit the JSON to fix detected issues (see [Fix Patterns](#fix-patterns)). Then reimport via `FFlowImporterTool` in the editor to apply changes back to the FlowAsset.

## Audit Checklist

Run these checks in order. Each check includes the JSON-level detection logic.

### 1. Duplicate GUIDs
- **What:** Two or more nodes share the same `nodeGuid`.
- **Detect:** Collect all `nodeGuid` values; check for duplicates.
- **Severity:** Critical — causes undefined behavior on import.

### 2. Dangling Connections (target node missing)
- **What:** A connection's `targetNodeGuid` references a GUID that doesn't exist in the `nodes` array.
- **Detect:** Build a set of all `nodeGuid` values. For every connection in every node, verify `targetNodeGuid` is in the set.
- **Severity:** Critical — the connection silently does nothing at runtime.

### 3. Invalid Pin References
- **What:** A connection targets a `targetPinName` that doesn't exist in the target node's `inputPins`.
- **Detect:** For each connection, look up the target node and verify `targetPinName` appears in its `inputPins[].pinName`.
- **Severity:** Critical — connection can't deliver its signal.

### 4. Orphaned Nodes (unreachable from Start)
- **What:** A node has no incoming connections and is not the Start node. Listener/observer nodes (`OnTriggerEnter`, `OnActorRegistered`, `ListenTagChanged`, `ListenBuildActor`) are exempt only if they are activated by an upstream node connecting to their `Start` pin.
- **Detect:** Build a reachability graph from `FlowNode_Start` following all connections. Any node not reached and not having any incoming connection is orphaned.
- **Severity:** Warning — node exists but never executes.

### 5. Dead-End Nodes (non-terminal with no outgoing connections)
- **What:** A node has output pins but its `connections` object is empty `{}`. Terminal nodes (nodes with no output pins) are excluded.
- **Detect:** For each node with `outputPins.length > 0`, check if `connections` is empty.
- **Severity:** Warning — execution flow stops unexpectedly. May be intentional for leaf nodes, but flag for review.

### 6. SuccessLimit Set to 0
- **What:** Observer/listener nodes with `SuccessLimit: 0` will never trigger their success/completion path.
- **Detect:** Check `properties.SuccessLimit === 0` on any node whose class includes `OnTriggerEnter`, `OnTriggerExit`, `OnActorRegistered`, `ListenTagChanged`, `ListenBuildActor`, or other observer nodes.
- **Severity:** High — likely unintentional; the node fires but never counts as "successful".

### 7. Empty IdentityTags on Trigger/Observer Nodes
- **What:** Trigger or observer nodes with `IdentityTags.gameplayTags` being an empty array `[]`. These nodes match *nothing*.
- **Detect:** Check `properties.IdentityTags.gameplayTags.length === 0` on nodes whose class contains `OnTrigger`, `OnActor`, `Listen`, `ExecuteCustomEvent`, `SetGameplayTag`, `ModifyPhaseAttribute`.
- **Severity:** High — node can never find a matching actor.

### 8. None/Missing Asset References
- **What:** Property values set to `"None"` where a valid asset path is expected.
- **Detect:** Check for `"None"` in properties like `PLWeather`, `AudioAsset`, `MetaSoundAsset`. Both being `"None"` on a sound node means no sound plays.
- **Severity:** Medium — `PLWeather: "None"` on ChangeWeather means the weather system is told to apply nothing. Sound nodes with both `AudioAsset: "None"` and `MetaSoundAsset: "None"` are silent.

### 9. Sequence Nodes with Unconnected Outputs
- **What:** `FlowNode_ExecutionSequence` has numbered output pins (`"0"`, `"1"`, `"2"`, ...) but one or more are not present in `connections`.
- **Detect:** For Sequence nodes, compare `outputPins` pin names against keys in `connections`. Any output pin without a matching connection key is unconnected.
- **Severity:** Low — may be intentional placeholder, but worth flagging.

### 10. MultiGate with Unconnected Outputs
- **What:** `FlowNode_ExecutionMultiGate` has numbered output pins but only some are connected.
- **Detect:** Same approach as Sequence check. Additionally check if `bLoop: false` and `StartIndex: -1` with only one connected output — likely a degenerate gate.
- **Severity:** Low — may indicate incomplete wiring.

### 11. Empty Dialogue Text
- **What:** Dialogue nodes (`FN_StartDialogueHUD_FixedText`, `FN_StartDialogueBubble_FixedText`, `FN_AutoplayHudTextFixed`) with empty or missing `DialogueText`.
- **Detect:** Check `properties.DialogueText` is empty string, `"None"`, or missing on dialogue node classes.
- **Severity:** High — dialogue HUD appears with no text.

### 12. AIMoveToByTag with No Target
- **What:** `FN_AIMoveToByTag` has `TargetActorTag=None` and `bUseExactLocation=false`. AI has nowhere to move.
- **Detect:** Check `properties.TargetActorTag.tagName === "None"` AND `properties.bUseExactLocation !== true`.
- **Severity:** High — node fires `NotFound` immediately.

### 13. SpawnEntity with Empty EntitySpawnInfos
- **What:** `FN_SpawnEntity` has empty `EntitySpawnInfos` array. Nothing spawns.
- **Detect:** Check `properties.EntitySpawnInfos` is empty array `[]` AND `bGetSpawnParameterFromPython !== true`.
- **Severity:** High — node fires `Failed` immediately.

### 14. Teleport with No Destination
- **What:** `FlowNode_Teleport` has `TargetActorTag=None` and `TeleportOffset=(0,0,0)`. No destination configured.
- **Detect:** Check both `TargetActorTag.tagName === "None"` and all TeleportOffset components are 0.
- **Severity:** High — teleport does nothing meaningful.

### 15. GuideTask with Incomplete Configuration
- **What:** `FlowNode_GuideTask` missing `RegisterTaskTag` or both `RegisterTaskTag` and `GroupTagToComplete`.
- **Detect:** Check `properties.RegisterTaskTag.tagName === "None"` or missing.
- **Severity:** High — task cannot register in guide system.

### 16. Listener No Stop Wired
- **What:** Observer/listener has a `Stop` input pin but nothing connects to it.
- **Detect:** Check if any connection targets this node's `Stop` pin.
- **Severity:** Warning — listener runs forever (may be intentional in short-lived flows).

### 17. DoN MaxCount = 0
- **What:** `FlowNode_DoN` with `MaxCount=0`. Execute pin will never fire.
- **Detect:** Check `properties.MaxCount === 0` on DoN nodes.
- **Severity:** High — node is effectively dead.

### 18. bUsePayloadActors Without Upstream Source
- **What:** Node uses `bUsePayloadActors: true` but no upstream payload-producing node found.
- **Detect:** Walk upstream connections looking for trigger/spawn nodes.
- **Severity:** Warning — payload actors will be empty at runtime.

### 19. SubGraph Asset = None
- **What:** SubGraph node with `Asset=None`. No child flow to execute.
- **Detect:** Check `properties.Asset === "None"` on SubGraph nodes.
- **Severity:** High — node does nothing.

### 20. Branch No AddOns
- **What:** `FlowNode_Branch` with empty `addOns`. Always takes default path.
- **Detect:** Check if `addOns` array is empty or missing.
- **Severity:** High — no conditions defined.

### 21. Timer Zero Times
- **What:** Timer with `CompletionTime=0` and `StepTime=0`. Fires instantly.
- **Detect:** Check both properties are 0 on Timer nodes.
- **Severity:** Warning — likely unintentional instant completion.

### 22. ListenTagChanged Empty Tag Lists
- **What:** Both `ListenAddedTags` and `ListenRemovedTags` are empty. Listens for nothing.
- **Detect:** Check both tag arrays are empty.
- **Severity:** High — node will never trigger.

### 23. Counter Goal ≤ 0
- **What:** `FlowNode_PLCounter` with `Goal ≤ 0`. Already finished or unreachable.
- **Detect:** Check `properties.Goal <= 0`.
- **Severity:** High — counter fires immediately or never.

### 24. Dynamic Pin No Config
- **What:** ActionChain with empty `ActionNodeTags`. No dynamic output pins generated.
- **Detect:** Check `ActionNodeTags.gameplayTags` is empty array.
- **Severity:** Warning — node has no tag-specific outputs.

### 25. StartRootFlow No Asset
- **What:** `FlowNode_StartRootFlow` with no `FlowAsset`. No flow to instantiate.
- **Detect:** Check `properties.FlowAsset === "None"` or missing.
- **Severity:** High — node does nothing.

## Fix Patterns

### Dangling Connection → Remove
```json
// Before: connection targets deleted node
"connections": {
    "Out": { "targetNodeGuid": "DEADBEEF...", "targetPinName": "In" }
}
// After: remove the broken connection
"connections": {}
```

### SuccessLimit 0 → Set to Reasonable Default
```json
// Before
"SuccessLimit": 0
// After — use 1 for one-shot, 99999 for unlimited
"SuccessLimit": 1
```

### Empty IdentityTags → Add Required Tag
```json
// Before
"IdentityTags": { "gameplayTags": [] }
// After — add the appropriate identity tag
"IdentityTags": { "gameplayTags": [{ "tagName": "Character.Player" }] }
```
> **Caution:** The correct tag depends on design intent. Always confirm with the user before auto-filling.

### PLWeather: None → Set WeatherTag
If `PLWeather` is `"None"`, the node relies on `WeatherTag` instead. Verify `WeatherTag.tagName` is a valid weather tag (not `"None"`).

### Orphaned Node → Wire or Delete
- If the node should be connected, add a connection from the appropriate upstream node.
- If the node is leftover debris, remove it from the `nodes` array entirely.

### Sequence Gap → Rewire or Add Connection
If a Sequence node has pin `"0"` and `"2"` connected but `"1"` is missing, either:
- Add the missing connection for pin `"1"`
- Remove pin `"2"` connection and shift down (requires updating the pin names)

## File Locations

| Path | Purpose |
|------|---------|
| `Main/FlowGraphExports/*.json` | Exported FlowGraph JSON files |
| `Main/Plugins/Flow_v1.5_5.3/Source/FlowEditor/` | Exporter/Importer tool source code |
| `Main/Plugins/PLFlowGraphExtended/` | Project-specific FlowGraph node extensions |

## Automated Audit Script

Run the audit script to check a JSON export automatically:
```bash
node .claude/skills/flowgraph-audit/audit-flowgraph.js Main/FlowGraphExports/<AssetName>.json
```

The script implements all 25 checks from the checklist above and outputs a severity-sorted report. Issues are grouped as CRITICAL > HIGH > WARNING > LOW > INFO.

## References

- [JSON Schema Reference](references/json-schema.md) — Full field-level documentation of the `FlowGraphExporter/1.0` format
- [Common Bug Patterns](references/common-bugs.md) — Detailed catalogue of 25 known FlowGraph bugs with detection queries and fix recipes
- [Node Lifecycle](../flowgraph-edit/references/node-lifecycle.md) — FlowAsset/node execution model, observer pattern, payload system, save/load
- [audit-flowgraph.js](audit-flowgraph.js) — Automated audit script (Node.js, 25 checks)
