---
name: unreal-game-sync
title: UnrealGameSync (UGS) Tool Suite
description: C# WinForms desktop app + CLI + MetadataServer for Perforce-based UE5 project management. Covers CL description display, badge system, PreCheckin/PreCheck tag filtering, sync/build workflows, and CL gray-out logic. Use when modifying UGS changelist display, description badges, description parsing, or archive/binary sync behavior.
tags: [C#, UGS, Perforce, WinForms, UE5, Development, Tools, Content-Pipeline]
---

# UnrealGameSync (UGS) Tool Suite

<memory category="core-rules">
- UGS is a .NET 8 WinForms application on Windows only
- Solution: `UnrealGameSync.sln` at the root of this directory
- Four projects: UnrealGameSync (GUI), UnrealGameSyncCmd (CLI), UnrealGameSyncLauncher (bootstrap), MetadataServer (web API)
- Description badges are config-driven via `Badges.DescriptionBadges` in the project config INI — prefer config-based badges for non-critical display; use code-based badges only for tags that need stripping (like PreCheckin force)
- `[PreCheckin:force...]` tags must be stripped from description text AND rendered as a red badge; `[PreCheck:OK hash]` tags must be stripped silently
- Always check out files from P4 before editing (`p4 edit <file>`)
</memory>

<memory category="code-locations">
- Primary edit target: `UnrealGameSync/Controls/WorkspaceControl.cs`
  - `BuildList_DrawSubItem()`: CL row color decision → `allowSync ? baseTextColor : Blend(..., 0.25f)`
  - `CanSyncChange()`: determines if a CL is grayed out; calls `GetSelectedArchiveChannels` + `GetArchiveForChangeNumber`
  - `GetArchiveForChangeNumber()`: archive lookup with caching
  - `GetArchiveForChangeNumberUncached()`: walks `_sortedChangeNumbers`, skips non-code CLs via `TryGetChangeDetails()`, finds nearest archive
  - `GetSelectedArchiveChannels()`: filters available channels by `_settings.Archives[x].Enabled`
  - `UpdateSelectedArchives()`: refreshes UI state, sets `OptionsContextMenu_SyncPrecompiledBinaries.Checked`
  - `OptionsContextMenu_SyncPrecompiledBinaries_Click()`: toggles archive enabled state via `SetSelectedArchive()`
  - `CreateDescriptionBadges()`: force badge detection
  - `StripPreCheckTags()`: strips PreCheck/PreCheckin tags from description text
  - `s_preCheckinForceRegex`, `s_preCheckOkRegex`, `s_preCheckinOkRegex`: static compiled regex fields
  - `s_hashTagBadges`: array of `HashTagBadgeDef` for #hashtag → badge mappings
- Archive data: `UnrealGameSyncShared/ArchiveInfo.cs`
  - `BaseArchiveChannel.ChangeNumberToArchive`: SortedList mapping CL# → IArchive
  - `BaseArchiveChannel.TryGetArchiveForChangeNumber()`: exact match first, then next-higher CL ≤ maxChangeNumber
  - `PerforceArchiveChannel.FindArtifactsAsync()`: populates via `p4 filelog` on depot path, parses `[CL <number>]` descriptions
  - `PerforceArchiveChannel.GetChannelsAsync()`: reads `ZippedBinariesPath` / `Archives` from project INI
- Data model: `UnrealGameSyncShared/Utility.cs` → `PerforceChangeDetails.Description`
- CL fetching: `UnrealGameSync/PerforceMonitor.cs` → `AvailableArchiveChannels`, `TryGetChangeDetails()`
- Badge layout: `WorkspaceControl.cs` → `LayoutBadges()`, `DrawBadge()`
</memory>

## System Overview

UnrealGameSync is the Epic Games tool for managing Perforce-based UE5 project syncing. It provides:

- **GUI client** (`UnrealGameSync/`): WinForms app showing changelist history with badges, sync/build controls
- **CLI** (`UnrealGameSyncCmd/`): Headless sync and build automation
- **MetadataServer** (`MetadataServer/`): ASP.NET web service storing badge/review metadata
- **Launcher** (`UnrealGameSyncLauncher/`): Bootstrap that auto-updates UGS itself from P4

Target runtime: .NET 8, Windows only (WinForms dependency).

## Architecture

```
UnrealGameSync.sln
├── UnrealGameSync/           # Main WinForms GUI
│   ├── Controls/
│   │   └── WorkspaceControl.cs   ← PRIMARY: CL list, badges, description display
│   ├── Forms/
│   ├── PerforceMonitor.cs        ← Fetches CL data from P4
│   └── Program.cs
├── UnrealGameSyncShared/     # Shared data models and utilities
│   ├── Utility.cs                ← PerforceChangeDetails.Description data model
│   └── ArchiveInfo.cs            ← IArchiveChannel, BaseArchiveChannel, PerforceArchiveChannel
├── UnrealGameSyncCmd/        # CLI tool
├── UnrealGameSyncLauncher/   # Self-updater bootstrap
└── MetadataServer/           # Badge/review metadata web API
```

## CL Gray-out Logic (Precompiled Binaries)

A CL row is grayed out when `CanSyncChange()` returns false, meaning no precompiled binary archive exists for that CL.

### Call chain

```
BuildList_DrawSubItem()
  → allowSync = CanSyncChange(changeNumber, false)
    → GetSelectedArchiveChannels(GetArchiveChannels())
    → selectedArchives.All(x => GetArchiveForChangeNumber(x, cl, false) != null)
      → GetArchiveForChangeNumberUncached()
        → walks _sortedChangeNumbers backward skipping !ContainsCode CLs
          (uses TryGetChangeDetails() — fails silently if account lacks P4 permission)
        → TryGetArchiveForChangeNumber(cl, maxCL)  [ArchiveInfo.cs]
          → exact match in ChangeNumberToArchive, or next-higher CL ≤ maxChangeNumber
```

### Why an account sees ALL CLs un-grayed

Two possible causes:

1. **`selectedArchives.Count == 0`** — archive feature disabled in user settings (`_settings.Archives[x].Enabled = false`), or `AvailableArchiveChannels` is empty
2. **`TryGetChangeDetails()` returns false for most CLs** — account lacks P4 `list`/`read` permission on the depot path, so `ContainsCode` check fails, the backward-walk loop exits early at a CL that happens to have an archive → every CL appears to have an archive

### Diagnosing permission issues

```bash
# Check what the account can actually see
p4 -u <username> describe -s <cl_number>

# Check effective permissions on the depot path
p4 -u <username> protects -m //depot/path/...
```

If `p4 describe` returns an empty file list or permission error, add `list` or `read` permission via `p4 protect`.

### Archive population

`PerforceArchiveChannel.FindArtifactsAsync()` runs `p4 filelog` on the configured depot path and parses descriptions of the form `[CL <number>]` to build `ChangeNumberToArchive`. Controlled by `MaxFetchChanges` in project INI (default 128).

## Description Display Pipeline

```
P4 CL description text
  → PerforceMonitor fetches → PerforceChangeDetails.Description (string)
  → BuildList_DrawSubItem(): StripPreCheckTags(change.Description!).Replace('\n', ' ')
  → ListView renders text in Description column
  → CreateDescriptionBadges() called separately for badge column
```

## Badge System

Badges are colored pill-shaped labels rendered to the right of the description text in each CL row.

### Config-Driven Badges

Defined in project config INI under `[Badges]`:
```ini
+DescriptionBadges=(Pattern="...", Name="...", Color="#rrggbb", HoverColor="#rrggbb", Url="...")
```

`WorkspaceControl.CreateDescriptionBadges()` iterates these definitions and regex-matches against the full CL description.

### Code-Driven Badges

Used for special cases that also require text stripping:

| Tag | Action |
|-----|--------|
| `[PreCheckin:force...]` (case-insensitive) | Strip from text + add red **"force!"** badge |
| `[PreCheck:OK <hash>]` (case-insensitive) | Strip silently, no badge |
| `[PreCheckin:OK <hash>]` (case-insensitive) | Strip silently, no badge |
| `#changelist validated` (case-insensitive) | Strip from text + add blue **"validated"** badge (via `s_hashTagBadges`) |

### Adding New `#hashtag` Badges

`#hashtag` → badge mappings are driven by the `HashTagBadgeDef` class and `s_hashTagBadges` array. To add a new one, append an entry to the array:

```csharp
// In WorkspaceControl.cs — s_hashTagBadges array
private static readonly HashTagBadgeDef[] s_hashTagBadges =
{
    new HashTagBadgeDef(@"#changelist\s+validated", "validated",
        Color.FromArgb(80, 140, 200),
        Color.FromArgb(60, 110, 170)),
    // new HashTagBadgeDef(@"#your\s+tag", "label", Color.FromArgb(...), Color.FromArgb(...)),
};
```

## PreCheckin/PreCheck Tag Handling

### Implementation (WorkspaceControl.cs)

**Static regex fields** (in `WorkspaceControl.cs`):
```csharp
private static readonly Regex s_preCheckinForceRegex =
    new Regex(@"\[PreCheckin:force[^\]]*\]", RegexOptions.IgnoreCase | RegexOptions.Compiled);
private static readonly Regex s_preCheckOkRegex =
    new Regex(@"\[PreCheck:OK\s+[^\]]+\]", RegexOptions.IgnoreCase | RegexOptions.Compiled);
private static readonly Regex s_preCheckinOkRegex =
    new Regex(@"\[PreCheckin:OK\s+[^\]]+\]", RegexOptions.IgnoreCase | RegexOptions.Compiled);
```

**Strip helper** (`StripPreCheckTags` in `WorkspaceControl.cs`):
```csharp
private static string StripPreCheckTags(string description)
{
    description = s_preCheckOkRegex.Replace(description, "");
    description = s_preCheckinOkRegex.Replace(description, "");
    description = s_preCheckinForceRegex.Replace(description, "");
    foreach (HashTagBadgeDef def in s_hashTagBadges)
        description = def.Pattern.Replace(description, "");
    return description.Trim();
}
```

## Building

```bash
# From solution root
dotnet build UnrealGameSync.sln -c Debug

# Or open in Visual Studio: UnrealGameSync.sln
```

## Troubleshooting

- **File read-only / can't edit**: Run `p4 edit <file>` first — all source files are under Perforce
- **Badge not appearing**: Check `LayoutBadges()` is called after adding the badge to the list (it computes offsets/widths)
- **Regex not matching**: Tags are case-insensitive (`RegexOptions.IgnoreCase`) — e.g. `[PreCheckin:forcE!]` matches `force` pattern
- **All CLs un-grayed despite archive enabled**: Check P4 `list`/`read` permission on archive depot path — `TryGetChangeDetails()` silently fails when account cannot see CL files, causing `GetArchiveForChangeNumberUncached()` to return a false-positive archive match
