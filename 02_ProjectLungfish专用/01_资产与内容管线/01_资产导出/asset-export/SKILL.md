---
name: asset-export
title: Full AssetExports Pipeline
description: |
  One-click full export of all project asset types (Blueprints, FlowGraphs, DataAssets, DataTables, CurveTables, AnimAssets, BehaviorTrees, Blackboards) to the Main/AssetExports/ directory tree, with automatic P4 changelist creation, reconcile, and unchanged-file cleanup.

  Trigger when user says: "export all assets", "re-export assets", "refresh AssetExports", "full asset export", "update AssetExports", "run export pipeline", "全量导出", "导出所有资产", "刷新 AssetExports".

  Also use proactively when: AssetExports data appears stale, user is about to do Blueprint migration and needs fresh exports, or user mentions that asset JSON files are out of date.
tags: [AssetExports, Automation, Pipeline, P4, Export]
---

# Full AssetExports Pipeline

## What This Does

Exports every project asset type from UE to JSON/CSV under `Main/AssetExports/`, then uses P4 to detect what changed (new, modified, deleted files), creates a changelist with only the actual changes, and reports a summary.

## One-Click Usage

Run the bundled script. It handles everything — no manual steps needed:

```bash
cmd.exe /c ".claude\skills\asset-export\scripts\export_all_assets.bat"
```

Or pass an explicit project root if running from elsewhere:

```bash
cmd.exe /c ".claude\skills\asset-export\scripts\export_all_assets.bat D:\SomeOtherWorkspace"
```

The script auto-detects the project root by walking up from its own location until it finds `Engine/` and `Main/`. All paths are resolved to absolute form before use — no relative `../` paths that break P4.

## What the Script Does

### Step 1: Remove read-only flags
P4-managed files are read-only. The script clears the read-only attribute on all files under `Main/AssetExports/` so the UE commandlets can overwrite them.

### Step 2: Export all 8 asset types (sequential)
UE commandlets run one at a time (single-process limitation). The script runs them in order:

| # | Commandlet | Output Directory | Extra Flags |
|---|-----------|-----------------|-------------|
| 1 | BlueprintExport | AssetExports/Blueprints/ | |
| 2 | FlowGraphExport | AssetExports/FlowGraphs/ | |
| 3 | DataAssetExport | AssetExports/DataAssets/ | |
| 4 | DataTableExport | AssetExports/DataTables/ | -TableOnly |
| 5 | DataTableExport | AssetExports/CurveTables/ | -CurveOnly |
| 6 | AnimAssetExport | AssetExports/AnimAssets/ | |
| 7 | BehaviorTreeExport | AssetExports/BehaviorTrees/ | |
| 8 | BehaviorTreeExport | AssetExports/Blackboards/ | -BBOnly |

Each commandlet uses `-All` and an absolute `-OutputDir` path. The output preserves the content directory tree (mirroring `/Game/` and `/Plugins/` paths).

### Step 3: Create P4 changelist
Creates a numbered changelist with a descriptive message.

### Step 4: P4 reconcile
Runs `p4 reconcile` on each asset subdirectory, which detects:
- **New files** (asset added to the project) → `p4 add`
- **Modified files** (asset content changed) → `p4 edit`
- **Deleted files** (asset removed from project) → `p4 delete`

### Step 5: Revert unchanged
Runs `p4 revert -a` to drop any files that were opened but whose content matches the depot version. Only actual changes remain in the CL.

### Step 6: Report
Prints add/edit/delete counts. If nothing changed, deletes the empty CL.

## Path Resolution

The script resolves all paths to absolute form at startup using `pushd`/`popd`. This avoids the relative-path bug where `Tools\..\Main\AssetExports` causes P4's `MarkForAdd` to reject paths containing `..`.

Auto-detection logic: the script is at `.claude/skills/asset-export/scripts/export_all_assets.bat`, so it walks up 4 levels (`scripts/ → asset-export/ → skills/ → .claude/ → PROJECT_ROOT`) to find the workspace root.

## Running from Claude Code

When a user asks for a full asset export, run:

```bash
cmd.exe /c "D:\ChaosCookOfficeMainDepot\.claude\skills\asset-export\scripts\export_all_assets.bat"
```

This is a long-running operation (typically 20-60 minutes depending on project size). Run it in the background and monitor progress:

```bash
# Background execution
cmd.exe /c ".claude\skills\asset-export\scripts\export_all_assets.bat" &

# Monitor
tail -f /path/to/output
```

## Partial Export

To export only specific asset types, use `Tools/ExportBlueprints.bat` directly:

```bash
cmd.exe /c "Tools\ExportBlueprints.bat bp -All"        # Blueprints only
cmd.exe /c "Tools\ExportBlueprints.bat flow -All"      # FlowGraphs only
cmd.exe /c "Tools\ExportBlueprints.bat da -All"        # DataAssets only
```

Note: `Tools/ExportBlueprints.bat` uses relative paths internally. For P4 compatibility, prefer the bundled `export_all_assets.bat` which resolves everything to absolute paths.

## Troubleshooting

### "Failed to write" errors
The file is still read-only. The script removes read-only flags at startup, but if it was interrupted mid-run, some files may retain the flag. Re-run the script — it always clears flags first.

### P4 "Relative paths not allowed" error
This happens when OutputDir contains `..`. The bundled script avoids this by resolving paths via `pushd`/`popd`. If you see this error, you're probably using `Tools/ExportBlueprints.bat` instead of the bundled script.

### Export takes too long
Each commandlet loads the full UE project, which takes 3-5 minutes per invocation. With 8 types, that's 25-40 minutes of startup overhead alone. The actual export speed depends on asset count (currently ~30,000 total assets).

### Empty CL after reconcile
If all exported files are identical to the depot, the script auto-deletes the empty CL. This is normal — it means nothing has changed since the last export.

## Output Directory Structure

```
Main/AssetExports/
├── Blueprints/         7400+ files  (.json)
│   ├── Game/           mirrors /Game/ content paths
│   └── Plugins/        mirrors plugin content paths
├── FlowGraphs/         190+ files   (.json)
├── DataAssets/         8600+ files  (.json)
├── DataTables/         5000+ files  (.csv)
├── CurveTables/        7+ files     (.csv)
├── AnimAssets/         460+ files   (.json)
├── BehaviorTrees/      13+ files    (.json)
├── Blackboards/        10+ files    (.json)
└── Logs/               export logs  (not tracked in P4)
```
