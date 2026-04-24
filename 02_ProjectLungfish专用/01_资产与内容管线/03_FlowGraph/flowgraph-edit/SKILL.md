---
name: flowgraph-edit
title: FlowGraph JSON Design Modification
description: Modify FlowGraph assets via exported JSON to fulfill designer requests. Use when user says "add node to flow", "rewire flow", "modify flowgraph", "insert timer", "change weather tag", "connect flow nodes", "design flow change", or needs to add/remove/rewire nodes, change properties, or restructure execution flow in FlowGraphExports/*.json files.
tags: [FlowGraph, JSON, Design, Modification, Node-Editing]
---

# FlowGraph JSON Design Modification

## Overview

This skill modifies FlowGraph JSON exports to implement designer requests — adding nodes, rewiring connections, changing properties, inserting control flow. The workflow:

1. **Read** the exported JSON from `Main/FlowGraphExports/<AssetName>.json`
2. **Understand** the designer's intent (what should change in the gameplay flow)
3. **Modify** the JSON — add/remove nodes, rewire connections, update properties
4. **Validate** the result (run `audit-flowgraph.js` from the audit skill)
5. **Reimport** via `FFlowImporterTool` in the editor

> **Schema reference:** See [flowgraph-audit/references/json-schema.md](../flowgraph-audit/references/json-schema.md) for full field documentation.

## GUID Generation

Every new node needs a unique 32-character uppercase hex GUID. Generate one:
```bash
node -e "const c='0123456789ABCDEF';let g='';for(let i=0;i<32;i++)g+=c[Math.floor(Math.random()*16)];console.log(g)"
```

## Core Operations

### 1. Add a Node

Insert a new node object into the `nodes` array. Minimum required fields:

```json
{
    "nodeGuid": "<NEW_GUID>",
    "nodeClass": "<class path>",
    "nodeTitle": "",
    "editorPosition": { "x": <X>, "y": <Y> },
    "inputPins": [ /* pins matching the class */ ],
    "outputPins": [ /* pins matching the class */ ],
    "connections": {},
    "properties": { /* default properties for the class */ }
}
```

**Position rule:** Place new nodes ~300px to the right of the upstream node. Use the same Y as the upstream node for linear chains; offset Y by +240 for branches.

### 2. Wire a Connection

Add an entry to the source node's `connections` object:
```json
"connections": {
    "<outputPinName>": {
        "targetNodeGuid": "<target GUID>",
        "targetPinName": "<target input pin name>"
    }
}
```

**Constraint:** Each output pin can connect to exactly one target. To fan out, use a Sequence node.

### 3. Insert a Node Between Two Existing Nodes

To insert node B between A and C (where A→C exists):
1. Remove A's connection to C
2. Add A→B connection
3. Add B→C connection
4. Position B between A and C (average their X, same Y)

### 4. Remove a Node

1. Remove the node object from the `nodes` array
2. Remove all connections targeting this node from other nodes
3. If the removed node had downstream connections, decide whether to rewire upstream→downstream or leave disconnected

### 5. Change a Property

Directly edit the `properties` object on the target node. See the [Node Catalogue](references/node-catalogue.md) for property names and types per node class.

### 6. Add a Branch (Sequence Fan-Out)

To execute multiple paths from one output:
1. Insert a `FlowNode_ExecutionSequence` node
2. Wire the original output to the Sequence's `"In"` pin
3. Wire Sequence outputs `"0"`, `"1"`, etc. to each branch target
4. Add corresponding output pins for each branch

## Post-Modification Checklist

After any edit, verify:
- [ ] All new GUIDs are unique (no collisions with existing nodes)
- [ ] All new connections reference valid `targetNodeGuid` and `targetPinName`
- [ ] Output pin names in `connections` match `outputPins[].pinName`
- [ ] Target pin names match `inputPins[].pinName` on the target node
- [ ] No orphaned nodes created by rewiring
- [ ] Run audit: `node .claude/skills/flowgraph-audit/audit-flowgraph.js <json>`

## Common Designer Requests → JSON Operations

| Designer Request | JSON Operation |
|-----------------|----------------|
| "Add a 5-second delay before X" | Insert Timer node (CompletionTime=5) between upstream and X |
| "Change the weather to rain" | Set `WeatherTag.tagName` to `"Environment.Weather.OpenRain"` on ChangeWeather node |
| "Play a sound when player enters" | Add PlaySound2D node, wire from OnTriggerEnter's Entered pin |
| "Make it only trigger once" | Set `SuccessLimit: 1` on the observer node |
| "Add a campfire detection" | Add OnActorRegistered node with `IdentityTags: [{tagName: "Entity.Campfire"}]` |
| "Run A and B in parallel" | Insert Sequence node, wire both A and B from its numbered outputs |
| "Remove the sound effect" | Delete the PlaySound2D node, rewire upstream→downstream |
| "Gate this to only fire 3 times" | Replace direct connection with MultiGate (3 outputs) or set SuccessLimit=3 |

## File Locations

| Path | Purpose |
|------|---------|
| `Main/FlowGraphExports/*.json` | Exported FlowGraph JSON files |
| `.claude/skills/flowgraph-audit/audit-flowgraph.js` | Post-edit validation script |
| `.claude/skills/flowgraph-audit/references/json-schema.md` | Full JSON schema docs |

## References

- [Node Catalogue](references/node-catalogue.md) — Pin layouts and default properties for 90+ node classes
- [Node Lifecycle](references/node-lifecycle.md) — FlowAsset/node execution model, observer pattern, payload system, save/load, dynamic pins
- [Tag Reference](references/tag-reference.md) — GameplayTag hierarchy and tag-to-property mapping
- [Wiring Patterns](references/patterns.md) — 11 common wiring patterns with ASCII diagrams and payload usage guide
- [JSON Schema](../flowgraph-audit/references/json-schema.md) — Field-level schema reference (shared with audit skill)
