@echo off
setlocal
echo Exit Phone Screen Guard from its tray menu, then press any key.
pause >nul
set "GUARD_START=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\PhoneScreenGuard.cmd"
if exist "%GUARD_START%" del "%GUARD_START%"
if exist "%GUARD_START%" goto failed
if exist "%USERPROFILE%\PhoneScreenGuard" rmdir /s /q "%USERPROFILE%\PhoneScreenGuard"
if exist "%USERPROFILE%\PhoneScreenGuard" goto failed
echo Phone Screen Guard removed.
pause
exit /b 0
:failed
echo Removal incomplete. Close the app and try again.
pause
exit /b 1
