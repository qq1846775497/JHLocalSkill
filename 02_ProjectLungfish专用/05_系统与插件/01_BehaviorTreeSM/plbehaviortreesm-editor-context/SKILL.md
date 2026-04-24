---
name: plbehaviortreesm-editor-context
description: Context and workflow guide for the PLBehaviorTreeSM plugin in ProjectLungfish. Use whenever Kimi is asked to work on the BLBT State Machine Blueprint editor, its custom sidebar panels, graph schemas, compiler, or styling. Contains project paths, completed fixes, and active issues.
---

# PLBehaviorTreeSM Editor Context

## Project Overview
- **Project**: `ProjectLungfish` (`D:\jiangheng\JiangHengWork\Main\ProjectLungfish.uproject`)
- **Engine**: Custom UE5 build at `D:\jiangheng\JiangHengWork\Engine`
- **Plugin**: `PLBehaviorTreeSM` located in `Plugins/PLBehaviorTreeSM`
- **Modules**:
  - `PLBehaviorTreeSM` (Runtime)
  - `PLBehaviorTreeSMEditor` (Editor)
- **Constraint**: Runtime module cannot directly reference `UEdGraphSchema_K2`; schema resolution uses `FSoftClassPath::TryLoadClass`.

## Key Files
See [references/key-files.md](references/key-files.md) for file paths and responsibilities.

## Completed Work
See [references/completed-tasks.md](references/completed-tasks.md) for already-landed fixes (context-pin crash, custom layout, glass styling, compiler crash fix, transition naming, toolbar fix, tab close prevention, interactive sidebar).

## Active Issues
See [references/active-issues.md](references/active-issues.md) for details on:
1. Details panel read-only (custom `IDetailsView` not wired to editor inspector).
2. States/Transitions sidebar not refreshing on add/delete.
3. Sidebar not refreshing after Compile.

## Build Instructions
Run from `D:\jiangheng\JiangHengWork\Main`:
```powershell
& "D:\jiangheng\JiangHengWork\Engine\Build\BatchFiles\Build.bat" ProjectLungfishEditor Win64 DebugGame "D:\jiangheng\JiangHengWork\Main\ProjectLungfish.uproject" -WaitMutex -NoP4
```
If Live Coding is active, terminate `UnrealEditor-Win64-DebugGame.exe` first.
