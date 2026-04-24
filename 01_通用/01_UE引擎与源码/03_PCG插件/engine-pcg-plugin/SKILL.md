---
name: engine-pcg-plugin
title: PCG (Procedural Content Generation) Plugin
description: UE5 engine PCG plugin covering graph-based procedural generation, World Partition batch build pipeline, PCGComponent lifecycle, HierarchicalGeneration grids, and PCGWorldPartitionBuilder commandlet usage. Use when working with PCG graphs, PCG components, partition actor generation, or offline bake pipeline automation.
tags: [PCG, Procedural-Content-Generation, World-Partition, C++, Editor-Commandlet, HiGen-Grid, Data-Driven]
---

# PCG (Procedural Content Generation) Plugin

> Layer: Tier 3 (Engine Plugin Documentation)

## System Overview

Epic's PCG plugin provides a graph-based procedural content generation framework tightly integrated with UE5 World Partition. It supports both **runtime** and **editor-time** (baked) generation modes.

Key concepts:

| Concept | Description |
|---------|-------------|
| `UPCGComponent` | Actor component that owns a `UPCGGraph` and drives generation |
| `UPCGGraph` / `UPCGGraphInterface` | The node graph defining generation logic |
| `APCGPartitionActor` (PA) | Auto-created proxy actors that hold local PCG components per World Partition cell |
| `UPCGSubsystem` | World subsystem; graph executor, PA mapping, runtime management |
| `EPCGEditorDirtyMode` | `Normal` / `Preview` / `LoadAsPreview` — controls when component data is persisted |
| `EPCGHiGenGrid` | Hierarchical generation grid level (`Unbounded`, numeric sizes) |

## Module Structure

```
Engine/Plugins/PCG/
├── Source/
│   ├── PCG/            # Runtime module — components, graph execution, data types
│   │   ├── Public/
│   │   │   ├── PCGComponent.h          # Core actor component
│   │   │   ├── PCGGraph.h              # Graph asset
│   │   │   ├── PCGSubsystem.h          # World subsystem
│   │   │   ├── Components/             # Component variants
│   │   │   ├── Elements/               # Built-in graph nodes
│   │   │   ├── Data/                   # PCGData types (points, surfaces, etc.)
│   │   │   ├── Grid/PCGPartitionActor.h
│   │   │   └── Helpers/PCGHelpers.h
│   ├── PCGEditor/      # Editor module — builder commandlet, dialogs, asset tools
│   │   ├── Private/WorldPartitionBuilder/
│   │   │   ├── PCGWorldPartitionBuilder.h   # ← WP batch bake builder
│   │   │   ├── PCGWorldPartitionBuilder.cpp
│   │   │   ├── PCGBuilderSettings.h         # Data asset for builder config
│   │   │   ├── SPCGBuilderDialog.h/cpp       # Editor UI dialog
│   └── PCGCompute/     # GPU compute module
```

## Key Components

### UPCGComponent
- Attaches to any Actor; references a `UPCGGraph`
- **EditingMode** (`EPCGEditorDirtyMode`) determines whether generation results persist to disk:
  - `LoadAsPreview` — results saved/loaded from disk (default for WP bake)
  - `Normal` — not typically baked offline
  - `Preview` — transient preview only
- `bActivated` must be true for builder to process it
- `IsManagedByRuntimeGenSystem()` → skip for offline builder
- Partitioned vs. non-partitioned: partitioned components delegate to PAs per WP cell

### APCGPartitionActor (PA)
- Auto-created per WP cell by `UPCGSubsystem::CreatePartitionActorsWithinBounds`
- Holds "local" `UPCGComponent` instances that correspond to the original component
- Grid size from `UPCGGraph` hierarchy determines PA granularity

### UPCGSubsystem
- `CreatePartitionActorsWithinBounds` — creates PAs for partitioned components
- `UpdateMappingPCGComponentPartitionActor` — syncs component ↔ PA mappings
- `SetDisablePartitionActorCreationForWorld` — used by builder to gate PA creation
- `IsAnyGraphCurrentlyExecuting` — polling check during builder wait loops

## Offline Batch Build: PCGWorldPartitionBuilder

For batch baking of PCG content in large open worlds. See the detailed reference:

**[PCGWorldPartitionBuilder Reference](references/PCGWorldPartitionBuilder.md)**

Quick summary:
- Triggered via `WorldPartitionBuilderCommandlet -Builder=PCGWorldPartitionBuilder`
- Or from Editor: Build menu → "Build PCG" (opens `SPCGBuilderDialog`)
- Or from console: `pcg.BuildComponents [args]`
- Configured via `UPCGBuilderSettings` data asset or commandline switches
- Two loading modes: `EntireWorld` (default) or `IterativeCells2D` (large maps)

## Common Editing Mode Workflow

```
PCGComponent.EditingMode = LoadAsPreview
    ↓
Builder runs → GenerateLocalGetTaskId() → waits for IsGenerating()
    ↓
Dirty packages collected → saved/submitted to SCC
```

## Debugging

- Log category: `LogPCGWorldPartitionBuilder` (Verbose level)
- Console command: `pcg.BuildComponents` — runs builder on current editor world
- Check `UPCGSubsystem::IsAnyGraphCurrentlyExecuting()` to detect stalled execution

## Code Locations

**Primary Files:**
- `Engine/Plugins/PCG/Source/PCGEditor/Private/WorldPartitionBuilder/PCGWorldPartitionBuilder.h`
- `Engine/Plugins/PCG/Source/PCGEditor/Private/WorldPartitionBuilder/PCGWorldPartitionBuilder.cpp`
- `Engine/Plugins/PCG/Source/PCGEditor/Private/WorldPartitionBuilder/PCGBuilderSettings.h`
- `Engine/Plugins/PCG/Source/PCG/Public/PCGComponent.h`
- `Engine/Plugins/PCG/Source/PCG/Public/PCGSubsystem.h`
- `Engine/Plugins/PCG/Source/PCG/Public/Grid/PCGPartitionActor.h`

**References:**
- [`references/PCGWorldPartitionBuilder.md`](references/PCGWorldPartitionBuilder.md) — detailed builder usage & internals
