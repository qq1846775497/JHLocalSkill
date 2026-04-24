# Active Issues / TODO

_None at the moment — all known active issues have been resolved. If new issues surface, add them here with symptom, root cause, and fix direction._

## Build Notes
- **Engine**: `D:\jiangheng\JiangHengWork\Engine`
- **Project**: `D:\jiangheng\JiangHengWork\Main\ProjectLungfish.uproject`
- **Build command**: `& "D:\jiangheng\JiangHengWork\Engine\Build\BatchFiles\Build.bat" ProjectLungfishEditor Win64 DebugGame "D:\jiangheng\JiangHengWork\Main\ProjectLungfish.uproject" -WaitMutex -NoP4`
- **Live Coding constraint**: If build fails with "Unable to build while Live Coding is active", terminate `UnrealEditor-Win64-DebugGame.exe` via Task Manager or `Stop-Process` and retry.
