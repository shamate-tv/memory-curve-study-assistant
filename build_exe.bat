@echo off
cd /d "%~dp0"

echo ========================================
echo Building MemoryCurveStudyAssistant.exe
echo ========================================

python -m pip install --upgrade pyinstaller
if errorlevel 1 (
    echo Failed to install PyInstaller.
    pause
    exit /b 1
)

python -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --onefile ^
    --windowed ^
    --name MemoryCurveStudyAssistant ^
    --add-data "data.json;." ^
    --hidden-import reminder ^
    --hidden-import notifier ^
    --hidden-import task_scheduler ^
    --hidden-import scheduler ^
    --hidden-import storage ^
    main.py

if errorlevel 1 (
    echo Build failed.
    pause
    exit /b 1
)

echo.
echo Build complete:
echo   dist\MemoryCurveStudyAssistant.exe
echo.
pause
