@echo off
rem ===========================================================================
rem  Shortcut Overlay - Build standalone executable with PyInstaller
rem
rem  Usage:
rem      build_exe.bat            -> onefile : 1 file dist\ShortcutOverlay.exe
rem                                             (cham khoi dong ~1-3s vi giai nen)
rem      build_exe.bat onedir     -> onedir  : dist\ShortcutOverlay\ShortcutOverlay.exe
rem                                             (KHOI DONG NHANH, khuyen dung)
rem ===========================================================================

setlocal EnableDelayedExpansion
cd /d "%~dp0"

set "MODE=onefile"
if /i "%~1"=="onedir" set "MODE=onedir"

set "PY=%~dp0.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

echo [1/4] Kiem tra / cai dat PyInstaller...
"%PY%" -m pip install --upgrade pyinstaller
if errorlevel 1 goto :error

echo.
echo [2/4] Tao icon ung dung...
"%PY%" "%~dp0main.py" --make-icon "assets\icon.ico"
if errorlevel 1 goto :error

echo.
echo [3/4] Don dep build cu...
if exist "build" rmdir /s /q "build"

if /i "%MODE%"=="onefile" (set "LAYOUT=--onefile") else (set "LAYOUT=--onedir")

echo.
echo [4/4] Build che do %MODE% ...
"%PY%" -m PyInstaller ^
    --noconfirm ^
    --clean ^
    !LAYOUT! ^
    --noconsole ^
    --name "ShortcutOverlay" ^
    --icon "assets\icon.ico" ^
    --hidden-import "pynput.keyboard._win32" ^
    --hidden-import "pynput.mouse._win32" ^
    --collect-submodules "pynput" ^
    "main.py"
if errorlevel 1 goto :error

echo.
echo [OK] Hoan tat! Ket qua trong thu muc dist\
goto :eof

:error
echo.
echo [X] Build that bai. Xem thong bao loi phia tren.
exit /b 1
