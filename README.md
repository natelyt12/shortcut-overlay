# Shortcut Overlay

A sleek, lightweight desktop hotkey visualizer for Windows that displays your shortcut key combinations in real time.

Ideal for presentations, video recording, screencasts, live streams, and tutorials.

---

## What You Can Do With This App

- **Display Active Shortcuts**: Automatically detects and shows combinations like `Ctrl + Shift + S`, `Win + D`, or `Alt + Tab` right above your taskbar.
- **Noise-Free Typing**: Intelligently ignores normal typing (regular letters, numbers, spaces, Enter) so your screen stays clean.
- **Seamless Workflow**: 100% click-through (`WA_TransparentForMouseEvents`) — mouse clicks pass right through the overlay without disrupting your work or games.
- **Clean Glassmorphic Design**: Translucent dark acrylic style with smooth auto-hide after 3.5 seconds of inactivity.
- **Single Instance**: Runs quietly in the background; prevents duplicate instances from opening.

---

## Quick Start

### 1. Run the Application
- **Option A (Instant, Recommended):** Double-click `run.bat` (runs in the background via `pythonw`, no console window).
- **Option B (Standalone Executable):** Run `dist\ShortcutOverlay.exe`.

### 2. Exit
Right-click the **Shortcut Overlay** icon in the Windows System Tray (near the clock) and select **Thoát (Exit)**.

---

## Development

```bash
# Setup virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run
python main.py

# Build standalone executable (Python)
build_exe.bat
```

---

## ⚡ Native C++ Version (`native/`)

An ultra-lightweight, zero-dependency native C++ / Win32 edition is located in [`native/`](native/):
- **Binary Size:** ~100 KB (vs ~38 MB in Python).
- **RAM Usage:** ~3 MB (vs ~40 MB in Python).
- **Automated Builds:** Automatically compiled by **GitHub Actions** on every push. Download the latest pre-built `.exe` anytime from the **Actions** tab on GitHub!

---

## License

MIT License
