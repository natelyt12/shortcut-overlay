# Shortcut Overlay

An ultra-lightweight (**~78 KB**), zero-dependency, glassmorphic desktop shortcut and hotkey visualizer for Windows, built natively in C++ using the Win32 API and GDI+.

Ideal for presentations, tutorials, video recording, screencasts, and live streams.

---

## ✨ Features

- **🎯 Smart Shortcut Detection**: Automatically captures and displays combinations like `Ctrl + Shift + S`, `Win + D`, `Alt + Tab`, and function keys (`F1`–`F24`).
- **🔇 Noise-Free Typing**: Intelligently ignores regular typing (letters, numbers, spaces, Enter, Backspace) so your screen stays clean.
- **🖱️ 100% Click-Through**: Built with `WS_EX_TRANSPARENT` — mouse clicks pass right through the overlay without interrupting your workflow or games.
- **💎 Glassmorphic Dark UI**: Translucent dark acrylic style with smooth auto-hide after 3.5 seconds of inactivity.
- **🔒 Single Instance Guard**: Protected by a Windows Named Mutex to prevent duplicate instances from opening.
- **⚡ Minimal Resource Footprint**:
  - Binary size: **~78 KB** (no Python runtime or heavy frameworks needed).
  - RAM usage: **~3 MB**.
  - Startup time: **Instant (<5 ms)**.
  - Zero external dependencies: uses native Windows system libraries (`user32`, `gdi32`, `gdiplus`, `shell32`).

---

## 🚀 Download & Usage

### 1. Download
Grab the latest pre-compiled `ShortcutOverlay.exe` from the **[GitHub Actions](https://github.com/natelyt12/shortcut-overlay/actions)** tab (under Artifacts of the latest run) or Releases.

### 2. Run
Double-click `ShortcutOverlay.exe`. It will launch quietly in the background and show a notification in the Windows System Tray.

### 3. Exit
Right-click the **Shortcut Overlay** icon in the Windows System Tray (near the clock) and select **Exit**.

---

## 🛠️ Building from Source

This project has zero external dependencies and compiles with standard Microsoft Visual C++ (MSVC).

### Using MSVC
Open a **Developer Command Prompt for Visual Studio** and run:
```bat
cd native
build_msvc.bat
```

### Automated GitHub Actions Build
Every push to `main` automatically triggers a build via GitHub Actions and uploads the latest compiled binary as an artifact.

---

## 📄 License

MIT License
