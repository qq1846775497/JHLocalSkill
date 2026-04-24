@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1

cd /d "%~dp0"
set "SCRIPT_DIR=%~dp0"
set "REPO_ROOT=%SCRIPT_DIR%..\..\.."

echo ========================================
echo    Building Entry Config Tool
echo ========================================
echo.
echo   Automates 4-step DataTable pipeline:
echo     1. DT_AchievementBuildMergeTag
echo     2. AQ_^<Name^> DataAsset
echo     3. DT_BuildingMergeAchievementList
echo     4. DT_BuildingBlockList
echo.
echo   EntityTag format : Entity.FireFlyLamp
echo   Name format      : Chinese display name
echo ========================================
echo.

:: -- Check Python --
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.9+ and add to PATH.
    pause
    exit /b 1
)

:: -- Check dependencies --
python -c "import requests" >nul 2>&1
if errorlevel 1 (
    echo Installing requests...
    python -m pip install requests --quiet
    if errorlevel 1 ( echo [ERROR] Failed to install requests. & pause & exit /b 1 )
)
python -c "import openpyxl" >nul 2>&1
if errorlevel 1 (
    echo Installing openpyxl...
    python -m pip install openpyxl --quiet
    if errorlevel 1 ( echo [ERROR] Failed to install openpyxl. & pause & exit /b 1 )
)

:: -- Pass-through mode (called with arguments) --
if not "%~1"=="" (
    cd /d "%REPO_ROOT%"
    python "%SCRIPT_DIR%add_building_entry.py" %*
    goto :DONE
)

:: -- Interactive mode --
:INPUT_TAG
set "entity_tag="
set /p entity_tag="EntityTag (e.g. Entity.FireFlyLamp): "

if "!entity_tag!"=="" (
    echo Error: EntityTag cannot be empty.
    echo.
    goto :INPUT_TAG
)

if not "!entity_tag:~0,7!"=="Entity." (
    echo Error: EntityTag must start with "Entity."
    echo.
    goto :INPUT_TAG
)

:INPUT_NAME
set "chinese_name="
set /p chinese_name="Chinese name: "

if "!chinese_name!"=="" (
    echo Error: Name cannot be empty.
    echo.
    goto :INPUT_NAME
)

echo.
echo ----------------------------------------
echo   EntityTag : !entity_tag!
echo   Name      : !chinese_name!
echo ----------------------------------------
echo.

cd /d "%REPO_ROOT%"
python "%SCRIPT_DIR%add_building_entry.py" "!entity_tag!" "!chinese_name!"
cd /d "%SCRIPT_DIR%"

echo.
echo ========================================

:ASK_CONTINUE
set "choice="
set /p choice="Add another entry? (Y/N): "

if /i "!choice!"=="Y" (
    echo.
    goto :INPUT_TAG
) else if /i "!choice!"=="N" (
    echo.
    echo Done. Goodbye.
    echo.
    pause
    exit /b 0
) else (
    echo Invalid choice. Please enter Y or N.
    goto :ASK_CONTINUE
)

:DONE
echo.
pause
