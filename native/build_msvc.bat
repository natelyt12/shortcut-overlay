@echo off
rem Build with MSVC (Visual Studio Developer Command Prompt)
setlocal
cd /d "%~dp0"

rc.exe resource.rc
cl.exe /O2 /W3 /EHsc /std:c++17 main.cpp resource.res /link /SUBSYSTEM:WINDOWS /OUT:ShortcutOverlay.exe user32.lib gdi32.lib gdiplus.lib shell32.lib
del *.obj *.res 2>nul
echo [OK] Built ShortcutOverlay.exe successfully.

