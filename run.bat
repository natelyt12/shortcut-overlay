@echo off
rem ===========================================================================
rem  Shortcut Overlay - Quick Launcher
rem  Starts main.py with pythonw.exe (NO console window) and returns instantly.
rem  This is the FASTEST way to run: no packaging, no extraction to temp dir.
rem ===========================================================================

setlocal
cd /d "%~dp0"

set "PYW=%~dp0.venv\Scripts\pythonw.exe"

if exist "%PYW%" (
    start "" "%PYW%" "%~dp0main.py"
) else (
    echo [!] Khong tim thay .venv - dung pythonw he thong...
    start "" pythonw "%~dp0main.py"
)

endlocal
