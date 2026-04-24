---
name: blueprint-migration
title: Blueprint到C++迁移工作流（基于AssetExports）
description: |
  Use when migrating Unreal Engine Blueprints to native C++ code. Locates Blueprint JSON exports from the AssetExports directory tree (not the legacy flat BlueprintExports folder), resolves cross-asset references (DataAssets, FlowGraphs, AnimMontages, DataTables, BehaviorTrees) via sibling AssetExports subfolders, and orchestrates the full extraction → migration → verification pipeline.

  Trigger when user says: "migrate [blueprint] to C++", "convert [blueprint] to native code", "translate [function] from Blueprint", gives a UE content path like /Game/XXX/BP_Name or a Blueprint name, or asks about Blueprint function implementation details.

  Also use proactively when: user is working with Blueprint JSON exports under AssetExports/, mentions Blueprint performance issues, needs to understand Blueprint logic before refactoring, or wants to analyze Blueprint dependencies and architecture.
tags: [Blueprint-Migration, C++, Automation, Code-Generation, Asset-Analysis, AssetExports]
---

# Blueprint-to-C++ Migration Workflow

## Overview

Migrate Unreal Engine Blueprints to native C++ using the **AssetExports** directory tree as the single source of truth. This tree mirrors the project's content structure and contains pre-exported JSON/CSV for all asset types, so you never need to launch UE or rely on the legacy flat `BlueprintExports/` folder.

## Locating Blueprint Files

### The AssetExports Directory

```
Main/AssetExports/
├── Blueprints/        ← Blueprint JSON (primary migration source)
│   ├── Game/          ← mirrors /Game/ content path
│   │   ├── 000_GlobalSettings/
│   │   ├── 002_Characters/
│   │   ├── 007_Entities/
│   │   └── ...
│   └── Plugins/       ← mirrors /PluginName/ content paths
│       ├── GASExtendedPL/
│       ├── GASCompanion/
│       └── ...
├── DataAssets/        ← DataAsset JSON (reference lookup)
├── DataTables/        ← DataTable CSV (reference lookup)
├── FlowGraphs/        ← FlowGraph JSON (reference lookup)
├── AnimAssets/        ← AnimMontage JSON (reference lookup)
├── BehaviorTrees/     ← BehaviorTree JSON (reference lookup)
└── Logs/              ← export logs
```

### Path Resolution

Given a Blueprint name or UE content path, resolve the JSON file like this:

| Input | How to find the file |
|-------|---------------------|
| UE content path `/Game/XXX/YYY/BP_Name` | `Main/AssetExports/Blueprints/Game/XXX/YYY/BP_Name_Readable.json` |
| Plugin path `/PluginName/XXX/BP_Name` | `Main/AssetExports/Blueprints/Plugins/PluginName/XXX/BP_Name_Readable.json` |
| Just a name `BP_MyActor` | `find Main/AssetExports/Blueprints/ -name "BP_MyActor_Readable.json"` |

All exported Blueprint files end with `_Readable.json`.

### When the file doesn't exist

If the Blueprint JSON isn't in AssetExports, the user needs to export it first. Tell them to run:

```bash
# Export a single Blueprint by content path
cmd.exe /c "Tools\ExportBlueprints.bat bp /Game/XXX/YYY/BP_Name"

# Export all Blueprints under a content folder
cmd.exe /c "Tools\ExportBlueprints.bat bp -ContentPath=\"/Game/XXX\""

# Export everything (all asset types)
cmd.exe /c "Tools\ExportBlueprints.bat export-all"
```

The CLI writes output to `Main/AssetExports/<AssetType>/` preserving the content directory tree.

## Quick Start

1. **Locate** the Blueprint JSON in `Main/AssetExports/Blueprints/`
2. **Read** it to identify all functions and events
3. **Extract** values (Phase 1) — launch `bp-function-value-extractor` agents
4. **Migrate** control flow (Phase 2) — launch `bp-function-flow-migrator` agents
5. **Verify** (Phase 3) — cross-check with `bp-to-cpp-migration-verifier`

## Phase 0: Context Gathering

Before migration, explore the Blueprint's neighborhood in the AssetExports tree to understand its architectural role.

### 1. List sibling assets

```bash
# See related Blueprints in the same directory
ls Main/AssetExports/Blueprints/Game/[same-path]/

# For plugin assets
ls Main/AssetExports/Blueprints/Plugins/[PluginName]/[path]/
```

Example: migrating `GA_Climb`? Check sibling `GA_*.json` files for shared patterns.

### 2. Find cross-references

```bash
grep -r "BlueprintName" Main/AssetExports/Blueprints/ --include="*.json" -l
```

### 3. Check parent class

Blueprint JSON contains a `parentClass` field showing inheritance hierarchy. Read it to understand what the target inherits.

### 4. Resolve referenced assets

During extraction, when you encounter asset references in pin default values, look them up in the appropriate AssetExports subfolder:

| Reference type | Where to look |
|---------------|--------------|
| DataAsset `/Game/XXX/MyDA` | `Main/AssetExports/DataAssets/Game/XXX/MyDA.json` |
| DataTable `/Game/XXX/DT_Foo` | `Main/AssetExports/DataTables/Game/XXX/DT_Foo.csv` |
| AnimMontage `/Game/XXX/AM_Bar` | `Main/AssetExports/AnimAssets/Game/XXX/AM_Bar.json` |
| FlowGraph `/Game/XXX/FG_Baz` | `Main/AssetExports/FlowGraphs/Game/XXX/FG_Baz.json` |
| Another Blueprint `/Game/XXX/BP_Other` | `Main/AssetExports/Blueprints/Game/XXX/BP_Other_Readable.json` |
| Plugin DataAsset `/PluginName/XXX/DA` | `Main/AssetExports/DataAssets/Plugins/PluginName/XXX/DA.json` |

This lets you understand what a referenced asset contains (fields, row structure, montage sections, etc.) without launching UE.

## Phase 1: Value Extraction

Launch `bp-function-value-extractor` agents **in parallel** for all functions/events to:

- Extract default values, asset references, member variables
- Identify constructor vs runtime loading context
- Generate asset path lists for ConstructorHelpers
- Map Blueprint input pins to C++ function parameters

**Parallel launch pattern:**
```
1. Read the Blueprint JSON (from AssetExports/Blueprints/) to list all functions/events
2. In ONE message, launch Task calls for ALL functions:
   - Task 1: Extract Function_A
   - Task 2: Extract Function_B
   - Task 3: Extract Event_X
   ... (all functions/events)
3. Wait for all extractions to complete
```

## Phase 2: Control Flow Migration

Launch `bp-function-flow-migrator` agents **in parallel** (after extractions complete) to:

- Generate C++ implementation with proper control structures
- Preserve exact Blueprint execution order
- Add UID mapping comments for verification
- Convert sequences, branches, loops, switches to C++ equivalents

**Batching strategy:**
- Simple functions: batch 3-5 agents
- Medium complexity: batch 3-5 agents
- Complex functions: handle individually or in pairs
- Maximum: up to 10-15 agents simultaneously for large Blueprints

## Phase 3: Limitation Analysis

Analyze extracted function calls for AS/BP limitations:

- Document unsupported APIs (editor-only, blueprint-only)
- Flag functions with no AngelScript bindings
- Report blocking dependencies that prevent complete migration
- Identify Blueprint-only visual nodes without C++ equivalents

## Phase 4: Verification (Optional)

- Use `bp-to-cpp-migration-verifier` agent if needed
- Cross-reference C++ implementation with Blueprint JSON UIDs
- Validate execution flow matches Blueprint logic

## Output Deliverables

### 1. Value Extraction Report
- Asset paths for ConstructorHelpers
- Default literal values (FName, float, int32, etc.)
- Member variable usage mappings
- Gameplay tag references

### 2. C++ Implementation
- Production-ready function code with UID comments
- Proper control flow translation (if/else, for loops, switch statements)
- Member variable assignments (Blueprint functions use member vars, not parameters/returns)

### 3. Limitation Analysis
- Function calls unavailable in AS/BP
- Editor-only API usage
- Required manual implementations

### 4. Migration Coverage Report
- What was successfully migrated
- What requires manual work
- Verification status

## CLI Reference

The `Tools/ExportBlueprints.bat` script handles all export operations:

```bash
# Export types
cmd.exe /c "Tools\ExportBlueprints.bat bp [args]"       # Blueprints
cmd.exe /c "Tools\ExportBlueprints.bat flow [args]"     # FlowGraphs
cmd.exe /c "Tools\ExportBlueprints.bat da [args]"       # DataAssets
cmd.exe /c "Tools\ExportBlueprints.bat dt [args]"       # DataTables
cmd.exe /c "Tools\ExportBlueprints.bat anim [args]"     # AnimMontages
cmd.exe /c "Tools\ExportBlueprints.bat bt [args]"       # BehaviorTrees
cmd.exe /c "Tools\ExportBlueprints.bat export-all"      # Everything

# Common flags
-All                              # Export all assets of this type
-ContentPath="/Game/XXX"          # Export from specific content folder
-OutputDir="path"                 # Override output directory
/Game/XXX/YYY/AssetName           # Export a single asset by path
```

## Complete Workflow Example

User: "Migrate GA_Climb to C++"

**Step 0: Locate the Blueprint**
```bash
find Main/AssetExports/Blueprints/ -name "GA_Climb_Readable.json"
# → Main/AssetExports/Blueprints/Game/002_Characters/01_Template/PlayerTemplate/AbilitySet/GA/GA_Climb_Readable.json
```

**Step 1: Context Gathering**
```bash
# List siblings
ls Main/AssetExports/Blueprints/Game/002_Characters/01_Template/PlayerTemplate/AbilitySet/GA/
# → GA_Glide.json, GA_Swim.json, GA_Jump.json ...

# Cross-references
grep -r "GA_Climb" Main/AssetExports/Blueprints/ --include="*.json" -l
```

**Step 2: Read Blueprint and Identify Functions**
```
Read: Main/AssetExports/Blueprints/Game/.../GA_Climb_Readable.json
→ Found functions: StartClimb, UpdateClimb, StopClimb, CheckCanClimb
```

**Step 3: Launch Value Extraction (Parallel)**
Launch 4 agents in one message:
- Agent 1: Extract StartClimb values
- Agent 2: Extract UpdateClimb values
- Agent 3: Extract StopClimb values
- Agent 4: Extract CheckCanClimb values

**Step 4: Resolve Referenced Assets**
If extraction reveals references like `/Game/002_Characters/.../DA_ClimbSettings`:
```
Read: Main/AssetExports/DataAssets/Game/002_Characters/.../DA_ClimbSettings.json
→ Get fields, default values, struct definitions
```

**Step 5: Launch Control Flow Migration (Parallel)**
After extractions complete, launch 4 migration agents.

**Step 6: Verification**
- Compile C++ code
- Cross-check UIDs with Blueprint JSON
- Document in ClaudeTasks/BlueprintMigration/

## Best Practices

### Workflow Optimization
- **Parallel execution recommended**: launch extraction agents simultaneously, then migration agents — typically 10-15x faster
- **Migration order**: process functions in dependency order (utility functions first, main logic last)
- **Critical**: always run value extraction before control flow migration — flow migrator depends on extraction results

### Documentation and Testing
- **Document manual adjustments** needed post-migration in ClaudeTasks
- **Update ClaudeTasks documentation** after each successful migration
- **Preserve UID comments** in generated C++ code for verification and debugging
- **Test incrementally** — compile and test each migrated function before moving to the next

### Large Blueprint Handling
- **Batch processing**: for large Blueprints (20+ functions), batch into groups of 10-15 agents per phase
- **Monitor agent completion**: use TaskOutput to check status if needed

## Integration with Other Skills

- **P4 Workflow**: for checking out and managing C++ files
- **Unreal Build Commands**: for compiling migrated code
- **Code Quality**: for validating generated C++ code

## Related Documentation

- **Agent Specifications**: `ClaudeTasks/AgentTypes/BlueprintMigration_AgentPrompts.md`
- **Asset Exports**: `Main/AssetExports/` (directory-tree-structured JSON/CSV from ExportBlueprints CLI)
- **Export CLI**: `Tools/ExportBlueprints.bat` (headless UE commandlet runner)
- **Migration Tasks**: `ClaudeTasks/BlueprintMigration/` (completed migration documentation)
