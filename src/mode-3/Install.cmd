@echo off
setlocal
cd /d "%~dp0"
set "GUARD_DIR=%USERPROFILE%\PhoneScreenGuard"
set "GUARD_START=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\PhoneScreenGuard.cmd"
set "GUARD_PY=%GUARD_DIR%\venv\Scripts\python.exe"
set "GUARD_PYW=%GUARD_DIR%\venv\Scripts\pythonw.exe"

rem Use Python directly when the Windows launcher is missing.
set "CHECK_PY=import platform, struct, sys; sys.exit(not (sys.version_info[:2] == (3, 12) and struct.calcsize('P') == 8 and platform.machine().upper() == 'AMD64'))"
if exist "%GUARD_PY%" (
    "%GUARD_PY%" -c "%CHECK_PY%" >nul 2>&1
    if not errorlevel 1 goto install
)
python -c "%CHECK_PY%" >nul 2>&1
if not errorlevel 1 (
    python -m venv "%GUARD_DIR%\venv" || goto failed
    goto install
)
py -3.12 -c "%CHECK_PY%" >nul 2>&1
if not errorlevel 1 (
    py -3.12 -m venv "%GUARD_DIR%\venv" || goto failed
    goto install
)
echo Install Python 3.12 x64, then run this installer again.
pause
exit /b 1

:install
if not exist "%GUARD_PYW%" goto failed
"%GUARD_PY%" -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu || goto failed
"%GUARD_PY%" -m pip install "ultralytics==8.3.161" "PySide6==6.8.3" || goto failed
pushd "%GUARD_DIR%" || goto failed
"%GUARD_PY%" -c "import cv2; from PySide6 import QtWidgets; from ultralytics import YOLO; YOLO('yolo11n.pt')" || goto model_failed
popd
copy /y "%~dp0guard.pyw" "%GUARD_DIR%\guard.pyw" >nul || goto failed
> "%GUARD_START%" echo @start "" "%%USERPROFILE%%\PhoneScreenGuard\venv\Scripts\pythonw.exe" "%%USERPROFILE%%\PhoneScreenGuard\guard.pyw"
if errorlevel 1 goto failed
start "" "%GUARD_PYW%" "%GUARD_DIR%\guard.pyw"
echo Setup complete. Look for Phone Screen Guard under the system tray arrow.
pause
exit /b 0

:model_failed
popd
:failed
echo Setup failed. Check the error above.
pause
exit /b 1
