@echo off
REM ============================================================
REM  Full Asset Export + P4 Reconcile
REM
REM  One-click workflow:
REM    1. Resolve absolute paths (no ../ anywhere)
REM    2. Remove read-only flags so exports can overwrite
REM    3. Export all 8 asset types sequentially
REM    4. Create a P4 changelist
REM    5. Reconcile (add/edit/delete) against depot
REM    6. Revert unchanged files
REM    7. Report summary
REM
REM  Usage:
REM    export_all_assets.bat [PROJECT_ROOT]
REM
REM  If PROJECT_ROOT is not given, it is auto-detected by walking
REM  up from this script until Engine/ and Main/ are found.
REM ============================================================
setlocal enabledelayedexpansion

REM --- Resolve PROJECT_ROOT ---
if not "%~1"=="" (
    set "PROJECT_ROOT=%~f1"
) else (
    REM Auto-detect: this script lives under .claude/skills/asset-export/scripts/
    set "PROJECT_ROOT=%~dp0..\..\..\.."
)
REM Resolve to absolute path (remove any ../)
pushd "%PROJECT_ROOT%" 2>nul
if errorlevel 1 (
    echo ERROR: Cannot resolve PROJECT_ROOT: %PROJECT_ROOT%
    exit /b 1
)
set "PROJECT_ROOT=%CD%"
popd

REM --- Validate paths ---
set "UE_CMD=%PROJECT_ROOT%\Engine\Binaries\Win64\UnrealEditor-Cmd.exe"
set "UPROJECT=%PROJECT_ROOT%\Main\ProjectLungfish.uproject"
set "EXPORT_DIR=%PROJECT_ROOT%\Main\AssetExports"
set "COMMON_FLAGS=-unattended -nosplash -nopause"

echo ============================================================
echo  Asset Export Pipeline
echo  PROJECT_ROOT: %PROJECT_ROOT%
echo  EXPORT_DIR:   %EXPORT_DIR%
echo ============================================================
echo.

if not exist "%UE_CMD%" (
    echo ERROR: UnrealEditor-Cmd.exe not found at:
    echo   %UE_CMD%
    echo Please build the Editor target first.
    exit /b 1
)
if not exist "%UPROJECT%" (
    echo ERROR: Project file not found at:
    echo   %UPROJECT%
    exit /b 1
)

REM --- Step 1: Remove read-only flags ---
echo [Step 1/7] Removing read-only flags from AssetExports...
if exist "%EXPORT_DIR%" (
    attrib -R /S /D "%EXPORT_DIR%\*.*" >nul 2>&1
)
echo Done.
echo.

REM --- Step 2: Export all asset types sequentially ---
REM UE can only run one commandlet at a time, so these must be sequential.

set EXPORT_COUNT=0
set EXPORT_FAIL=0

call :export_one "Blueprints"      BlueprintExport     "%EXPORT_DIR%\Blueprints"     ""
call :export_one "FlowGraphs"      FlowGraphExport     "%EXPORT_DIR%\FlowGraphs"     ""
call :export_one "DataAssets"       DataAssetExport     "%EXPORT_DIR%\DataAssets"      ""
call :export_one "DataTables"       DataTableExport     "%EXPORT_DIR%\DataTables"      "-TableOnly"
call :export_one "CurveTables"      DataTableExport     "%EXPORT_DIR%\CurveTables"     "-CurveOnly"
call :export_one "AnimAssets"       AnimAssetExport     "%EXPORT_DIR%\AnimAssets"      ""
call :export_one "BehaviorTrees"    BehaviorTreeExport  "%EXPORT_DIR%\BehaviorTrees"   ""
call :export_one "Blackboards"      BehaviorTreeExport  "%EXPORT_DIR%\Blackboards"     "-BBOnly"

echo.
echo ============================================================
echo  Export complete: %EXPORT_COUNT% succeeded, %EXPORT_FAIL% failed
echo ============================================================
echo.

if %EXPORT_FAIL% GTR 0 (
    echo WARNING: Some exports failed. Check the output above.
    echo Continue with P4 reconcile? Press Ctrl+C to abort.
    pause
)

REM --- Step 3: Create P4 changelist ---
echo [Step 5/7] Creating P4 changelist...
set "CL_DESC=Full AssetExports re-export (Blueprints, FlowGraphs, DataAssets, DataTables, CurveTables, AnimAssets, BehaviorTrees, Blackboards)"

REM Create a temp file for the changelist spec
set "TMPSPEC=%TEMP%\p4_asset_export_cl.txt"
(
echo Change: new
echo Client: %P4CLIENT%
echo User: %P4USER%
echo Status: new
echo Description:
echo 	%CL_DESC%
) > "%TMPSPEC%"

for /f "tokens=2" %%i in ('p4 change -i < "%TMPSPEC%" 2^>^&1 ^| findstr /R "^Change"') do set "CL_NUM=%%i"
del "%TMPSPEC%" 2>nul

if "%CL_NUM%"=="" (
    echo ERROR: Failed to create P4 changelist.
    echo You may need to run P4 reconcile manually.
    exit /b 1
)
echo Created CL %CL_NUM%
echo.

REM --- Step 4: Reconcile each asset type ---
echo [Step 6/7] Running P4 reconcile on all asset types...

set RECONCILE_DIRS=Blueprints FlowGraphs DataAssets DataTables CurveTables AnimAssets BehaviorTrees Blackboards
for %%d in (%RECONCILE_DIRS%) do (
    echo   Reconciling %%d...
    p4 reconcile -c %CL_NUM% "%EXPORT_DIR%\%%d\..." >nul 2>&1
)
echo Done.
echo.

REM --- Step 5: Revert unchanged files ---
echo [Step 7/7] Reverting unchanged files...
p4 revert -a -c %CL_NUM% "%EXPORT_DIR%\..." >nul 2>&1
echo Done.
echo.

REM --- Summary ---
echo ============================================================
echo  P4 Summary for CL %CL_NUM%
echo ============================================================
set /a ADD_COUNT=0
set /a EDIT_COUNT=0
set /a DEL_COUNT=0
for /f %%n in ('p4 opened -c %CL_NUM% 2^>^&1 ^| findstr /C:" - add " ^| find /c /v ""') do set ADD_COUNT=%%n
for /f %%n in ('p4 opened -c %CL_NUM% 2^>^&1 ^| findstr /C:" - edit " ^| find /c /v ""') do set EDIT_COUNT=%%n
for /f %%n in ('p4 opened -c %CL_NUM% 2^>^&1 ^| findstr /C:" - delete " ^| find /c /v ""') do set DEL_COUNT=%%n
set /a TOTAL=%ADD_COUNT%+%EDIT_COUNT%+%DEL_COUNT%

echo   Add:    %ADD_COUNT%
echo   Edit:   %EDIT_COUNT%
echo   Delete: %DEL_COUNT%
echo   Total:  %TOTAL%
echo.
if %TOTAL% EQU 0 (
    echo No changes detected. Deleting empty CL %CL_NUM%...
    p4 change -d %CL_NUM% >nul 2>&1
    echo Done.
) else (
    echo CL %CL_NUM% is ready for review and submission.
)
echo ============================================================
exit /b 0

REM ============================================================
REM  Subroutine: export one asset type
REM  Args: %1=Label  %2=Commandlet  %3=OutputDir  %4=ExtraFlags
REM ============================================================
:export_one
set "LABEL=%~1"
set "CMDLET=%~2"
set "OUTDIR=%~3"
set "EXTRA=%~4"

set /a EXPORT_COUNT+=1
set "STEP_NUM=!EXPORT_COUNT!"
echo [Step 2/7] [!STEP_NUM!/8] Exporting %LABEL%...

if not exist "%OUTDIR%" mkdir "%OUTDIR%"

"%UE_CMD%" "%UPROJECT%" -run=%CMDLET% -All -OutputDir="%OUTDIR%" %EXTRA% %COMMON_FLAGS%
if errorlevel 1 (
    echo   WARNING: %LABEL% export returned non-zero exit code.
    set /a EXPORT_FAIL+=1
) else (
    echo   OK.
)
echo.
exit /b 0
