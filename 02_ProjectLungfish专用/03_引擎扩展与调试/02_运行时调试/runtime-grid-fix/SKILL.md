---
name: runtime-grid-fix
description: |
  批量修复 World Partition Level Instance 中 Actor 的无效 RuntimeGrid 名称。
  当用户提到 RuntimeGrid 错误、BuildingBlock 无效网格、PIE 报 "无效运行时网格 BuildingBlock"、
  需要批量修复关卡 Actor 的 RuntimeGridName 属性时，使用此 skill。
  触发词：无效运行时网格、invalid RuntimeGrid、BuildingBlock RuntimeGrid、RuntimeGridName 修复、
  批量修 Level Instance RuntimeGrid、WP 关卡 RuntimeGrid 报错。
  即使用户只说"帮我把 BuildingBlock 改成 Titan"或"PIE 里有一堆 RuntimeGrid 错误"，也应使用此 skill。
---

# Runtime Grid Fix Skill

## 概述

此 skill 使用 `PLFixRuntimeGridBuilder`（`UWorldPartitionBuilder` 子类）headless commandlet，
批量将 World Partition Level Instance 中 `RuntimeGridName == "BuildingBlock"` 的 Actor 改为 `"Titan"`，
并自动保存修改后的 External Actor 包，再提交到 Perforce。

---

## 关键路径

| 资源 | 路径 |
|------|------|
| Commandlet 头文件 | `Main/Plugins/ProjectLungfishCore/Source/PLCoreEditor/Public/Commandlets/PLFixRuntimeGridBuilder.h` |
| Commandlet 实现 | `Main/Plugins/ProjectLungfishCore/Source/PLCoreEditor/Private/Commandlets/PLFixRuntimeGridBuilder.cpp` |
| 批量运行脚本 | `ClaudeTemp/run_fix_rg_all.ps1` |
| 错误来源文件 | `D:/ChaosCookOfficeMainDepot/PIEErrorList.txt` |
| UE 可执行文件 | `Engine/Binaries/Win64/UnrealEditor-Cmd.exe` |
| 项目文件 | `Main/ProjectLungfish.uproject` |

---

## Step 1：确认需要修复的 Level 列表

从 `PIEErrorList.txt` 或用户描述中提取包含 `BuildingBlock` RuntimeGrid 错误的 Level 路径。

错误格式示例（来自 PIEErrorList.txt）：
```
Actor /Game/012_Levels/.../LI_CombatCamp_M2_WP 拥有一个无效运行时网格 BuildingBlock
```

提取所有不重复的 Level 路径（`/Game/...` 格式）。

---

## Step 2：编写并运行批量处理 PowerShell 脚本

**重要语法规则：** world 路径必须作为第一个**位置参数**（token）传递，不能用 `-Map=` 开关形式。

创建或更新 `ClaudeTemp/run_fix_rg_all.ps1`：

```powershell
$exe      = "D:\ChaosCookOfficeMainDepot\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
$uproject = "D:\ChaosCookOfficeMainDepot\Main\ProjectLungfish.uproject"
$logdir   = "D:\ChaosCookOfficeMainDepot\ClaudeTemp"

$maps = @(
    @{ short="M1"; path="/Game/012_Levels/.../LI_CombatCamp_M1_WP" },
    # ... 其他 Level ...
)

foreach ($m in $maps) {
    $logfile = "$logdir\fix_rg_$($m.short).log"
    Write-Host "Processing: $($m.path)"

    $argList = @(
        $uproject,
        $m.path,                          # <-- 位置参数，必须第一个
        "-run=WorldPartitionBuilderCommandlet",
        "-Builder=PLFixRuntimeGridBuilder",
        "-AllowCommandletRendering",
        "-unattended",
        "-nosplash",
        "-nullrhi",
        "-log=$logfile"
    )

    $proc = Start-Process -FilePath $exe -ArgumentList $argList -Wait -PassThru -NoNewWindow
    Write-Host "Exit code: $($proc.ExitCode)"

    if (Test-Path $logfile) {
        Select-String -Path $logfile -Pattern "PLFixRuntimeGrid|Fixed:|Saving|succeeded|FAILED" |
            ForEach-Object { Write-Host $_.Line }
    }
}
Write-Host "All levels processed."
```

在 PowerShell 中运行（避免 Git Bash 路径扩展问题）：
```powershell
powershell.exe -ExecutionPolicy Bypass -File "D:\ChaosCookOfficeMainDepot\ClaudeTemp\run_fix_rg_all.ps1"
```

每个 Level 约耗时 25-40 秒（引擎启动 + WP Actor 加载 + 保存）。

---

## Step 3：验证输出

**成功标志（在控制台或 log 文件中查看）：**
```
PLFixRuntimeGridBuilder: Will replace RuntimeGrid [BuildingBlock] -> [Titan]
  Fixed: BP_Roof2m45_Rotten  [BuildingBlock] -> [Titan]
PLFixRuntimeGridBuilder: Fixed N actors in this pass.
PLFixRuntimeGridBuilder: Saving N modified package(s)...
PLFixRuntimeGridBuilder: Save succeeded.
Exit code: 0
```

**无匹配 Actor（正常，不是错误）：**
```
PLFixRuntimeGridBuilder: Fixed 0 actors in this pass.
PLFixRuntimeGridBuilder: No packages modified, nothing to save.
Exit code: 0
```

**失败 / 需排查：**
- `Exit code: 1` + `Missing world name` → world 路径传递方式错误，检查是否用了位置参数而不是 `-Map=`
- `Exit code: 1` + `Could not find map` → Level 路径拼写错误，验证 `.umap` 文件是否存在
- `Save FAILED` → P4 Source Control 问题，commandlet 内部已自动 checkout，但可能权限不足

---

## Step 4：将修改文件加入 P4 Changelist

`UWorldPartitionBuilder` 在 save 时会自动通过 Source Control 接口 checkout 修改的 External Actor 文件，
这些文件会出现在 default changelist。将它们移到任务专用 CL：

```bash
# 查看自动 checkout 的文件
p4 status "D:/ChaosCookOfficeMainDepot/Main/Content/__ExternalActors__/012_Levels/..."

# 移到任务 CL
p4 reopen -c <CL号> "D:/ChaosCookOfficeMainDepot/Main/Content/__ExternalActors__/012_Levels/003_LevelInstance/000_CangWuDi/003_POI_Medium/..."

# 验证 default CL 已清空
p4 opened -c default
```

External Actor 文件位于：
```
Main/Content/__ExternalActors__/012_Levels/.../LI_<LevelName>/<hash>/<hash>/<guid>.uasset
```

---

## Step 5：提交

等待用户明确说"submit"后再执行：

```bash
# 最终验证
p4 opened -c default     # 必须为空
p4 opened -c <CL号>      # 只包含本任务相关文件

# 提交
p4 submit -c <CL号>
```

---

## 可选参数

`PLFixRuntimeGridBuilder` 支持自定义 grid 名称（通过命令行参数）：
```
-InvalidGrid=BuildingBlock   (默认值，无需指定)
-TargetGrid=Titan            (默认值，无需指定)
```

如需修复其他 grid 名称对，在 `$argList` 中添加 `-InvalidGrid=XXX -TargetGrid=YYY`。

---

## 根因说明

`BuildingBlock` 是部分 Actor 的 `RuntimeGridName` 遗留值，但该 Level 的 WorldSettings.RuntimePartitions
中并未注册名为 `BuildingBlock` 的 partition，导致 PIE 启动时 UE WP streaming generation 报错。
`Titan` 是项目中已注册的有效 grid，适用于大型建筑/地标级别的 streaming。

---

## 注意事项

- 只对 **World Partition 关卡**（有 `__ExternalActors__` 目录的 `.umap`）有效
- Level Instance（`LI_*_WP`）本身是独立的 WP 世界，可直接作为 `-Builder` 的目标
- 不要用 **Git Bash** 运行命令（`/Game` 路径会被展开为 `C:/Program Files/Git/Game`），始终用 **PowerShell**
- 运行时必须关闭 UE Editor（Live Coding 会阻止构建）
