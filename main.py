"""
Shortcut Overlay - Desktop Key & Shortcut Visualizer
----------------------------------------------------
Real-time shortcut and hotkey combination visualizer in a single sleek,
frameless, click-through QLabel with guaranteed glassmorphic background rendering.

Features:
- Exactly 1 sleek QLabel window:
    * Unified glassmorphic dark acrylic pill background (no cyan border).
    * No outer container frames / div wrappers, no individual key box borders.
- Shortcut & Hotkey Focus:
    * Ignores ordinary typing (individual letters, numbers, punctuation, spaces, Enter, Backspace).
    * Activates exclusively on modifier keys (Ctrl, Shift, Alt, Win) and hotkey combinations.
    * Standalone shortcut/function keys (F1-F24, Esc, PrtSc) are also supported.
- Dynamic buffering:
    * Buffers modifier keys sequentially (e.g. "Ctrl", "Ctrl + Shift", "Ctrl + Shift + Alt").
    * Resolves Windows Virtual Key codes and ASCII control codes into a single unified label.
- Positioned smoothly right above the Windows taskbar.
- Click-through (WA_TransparentForMouseEvents) and translucent (WA_TranslucentBackground).
- Always on top, Frameless, and Tool window (no taskbar icon).
- Auto-hide inactivity countdown timer (3.5s).
- Thread-safe pynput hook decoupled from GUI thread via Qt pyqtSignal.

Dependencies:
    PyQt6
    pynput
"""

from __future__ import annotations

import ctypes
import os
import sys
from typing import Any, Dict, List, Optional

from pynput import keyboard
from PyQt6.QtCore import QObject, QPointF, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QGuiApplication,
    QIcon,
    QImage,
    QImageWriter,
    QPainter,
    QPaintEvent,
    QPen,
    QPixmap,
    QPolygonF,
)
from PyQt6.QtWidgets import QApplication, QLabel, QMenu, QSystemTrayIcon


class KeySignalEmitter(QObject):
    """Thread-safe signal emitter bridging background pynput listener to Qt GUI thread."""
    key_event = pyqtSignal(str)


# ---------------------------------------------------------------------------
# Application icon (drawn in code - no external image asset required)
# ---------------------------------------------------------------------------

def _render_icon_image(size: int) -> QImage:
    """Render the app icon (dark keycap with a cyan shortcut chevron) at any size."""
    image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)

    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    # Draw on a virtual 100x100 grid, then scale to the requested pixel size.
    s = size / 100.0
    stroke = max(1.0, 6.0 * s)

    # 1. Keycap body (matches the overlay's glassmorphic dark acrylic look)
    painter.setBrush(QBrush(QColor(15, 20, 32)))
    painter.setPen(QPen(QColor(120, 220, 255, 190), stroke))
    painter.drawRoundedRect(QRectF(8 * s, 8 * s, 84 * s, 84 * s), 24 * s, 24 * s)

    # 2. Shortcut chevron
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(
        QPen(
            QColor(120, 220, 255),
            max(1.5, 11.0 * s),
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
            Qt.PenJoinStyle.RoundJoin,
        )
    )
    painter.drawPolyline(
        QPolygonF(
            [
                QPointF(31 * s, 61 * s),
                QPointF(50 * s, 38 * s),
                QPointF(69 * s, 61 * s),
            ]
        )
    )

    painter.end()
    return image


def create_app_icon() -> QIcon:
    """Build a multi-resolution QIcon for the tray and window."""
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 256):
        icon.addPixmap(QPixmap.fromImage(_render_icon_image(size)))
    return icon


def save_icon_file(path: str) -> None:
    """Write a .ico file for the executable (build-time helper, see build_exe.bat)."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    writer = QImageWriter(path, b"ico")
    if not writer.write(_render_icon_image(256)):
        raise RuntimeError(f"Could not write icon file: {writer.errorString()}")


# Mapping for modifier keys to clean display names
MODIFIER_MAP: Dict[keyboard.Key, str] = {
    keyboard.Key.ctrl: "Ctrl",
    keyboard.Key.ctrl_l: "Ctrl",
    keyboard.Key.ctrl_r: "Ctrl",
    keyboard.Key.alt: "Alt",
    keyboard.Key.alt_l: "Alt",
    keyboard.Key.alt_r: "Alt",
    keyboard.Key.alt_gr: "AltGr",
    keyboard.Key.shift: "Shift",
    keyboard.Key.shift_l: "Shift",
    keyboard.Key.shift_r: "Shift",
    keyboard.Key.cmd: "Win",
    keyboard.Key.cmd_l: "Win",
    keyboard.Key.cmd_r: "Win",
}

# Mapping for special shortcut / navigation keys
SPECIAL_KEY_MAP: Dict[keyboard.Key, str] = {
    keyboard.Key.esc: "Esc",
    keyboard.Key.tab: "Tab",
    keyboard.Key.caps_lock: "Caps",
    keyboard.Key.up: "↑",
    keyboard.Key.down: "↓",
    keyboard.Key.left: "←",
    keyboard.Key.right: "→",
    keyboard.Key.delete: "Del",
    keyboard.Key.home: "Home",
    keyboard.Key.end: "End",
    keyboard.Key.page_up: "PgUp",
    keyboard.Key.page_down: "PgDn",
    keyboard.Key.insert: "Ins",
    keyboard.Key.print_screen: "PrtSc",
    keyboard.Key.num_lock: "NumLk",
    keyboard.Key.scroll_lock: "ScrLk",
    keyboard.Key.pause: "Pause",
    keyboard.Key.media_volume_up: "Vol +",
    keyboard.Key.media_volume_down: "Vol -",
    keyboard.Key.media_volume_mute: "Mute",
    keyboard.Key.media_play_pause: "Play",
    keyboard.Key.space: "Space",
    keyboard.Key.enter: "Enter",
    keyboard.Key.backspace: "Back",
}

# Windows virtual key codes for numpad keys (0x60 - 0x69)
NUMPAD_VK_MAP: Dict[int, str] = {
    96: "Num 0",
    97: "Num 1",
    98: "Num 2",
    99: "Num 3",
    100: "Num 4",
    101: "Num 5",
    102: "Num 6",
    103: "Num 7",
    104: "Num 8",
    105: "Num 9",
    106: "Num *",
    107: "Num +",
    109: "Num -",
    110: "Num .",
    111: "Num /",
}


def is_ordinary_typing_key(key: Any) -> bool:
    """Check if the key is an ordinary typing character (letters, numbers, space, enter, backspace)."""
    if isinstance(key, keyboard.KeyCode):
        if key.char is not None and key.char.isprintable():
            return True
        vk = key.vk
        if vk is not None:
            # A-Z (65-90), 0-9 (48-57), Numpad (96-111)
            if (65 <= vk <= 90) or (48 <= vk <= 57) or (96 <= vk <= 111):
                return True
            # Standard keyboard punctuation keys
            if vk in (186, 187, 188, 189, 190, 191, 192, 219, 220, 221, 222):
                return True

    # Standard whitespace and editing keys when typed alone
    if key in (keyboard.Key.space, keyboard.Key.enter, keyboard.Key.backspace):
        return True

    return False


class KeyComboTracker:
    """Tracks active modifier states and composes key combinations dynamically."""

    def __init__(self) -> None:
        self.active_modifiers: List[str] = []

    def resolve_key_name(self, key: Any) -> Optional[str]:
        """
        Convert any non-modifier key event to a clean, human-readable string.
        Robustly resolves Windows Virtual Key codes (VK) and ASCII control codes
        generated when modifiers (Ctrl, Alt, Win) are held down.
        """
        # 1. Special shortcut keys
        if key in SPECIAL_KEY_MAP:
            return SPECIAL_KEY_MAP[key]

        # 2. Function keys (F1 - F24)
        if isinstance(key, keyboard.Key):
            name = key.name.lower()
            if name.startswith("f") and name[1:].isdigit():
                return name.upper()

        # 3. KeyCode handling (with Ctrl/Alt/Win combinations)
        if isinstance(key, keyboard.KeyCode):
            vk = key.vk
            if vk is not None:
                if vk in NUMPAD_VK_MAP:
                    return NUMPAD_VK_MAP[vk]

                # Standard alphanumeric keys by Virtual Key Code (A-Z, 0-9)
                if 65 <= vk <= 90:
                    return chr(vk)
                if 48 <= vk <= 57:
                    return chr(vk)

                # Windows MapVirtualKeyW for punctuation
                try:
                    char_code = ctypes.windll.user32.MapVirtualKeyW(vk, 2)
                    if char_code:
                        c = chr(char_code)
                        if c.isprintable():
                            return c.upper() if c.isalpha() else c
                except Exception:
                    pass

            # Check char attribute (printable or Ctrl ASCII control codes 1-26)
            if key.char is not None:
                if key.char.isprintable():
                    return key.char.upper() if key.char.isalpha() else key.char

                char_ord = ord(key.char)
                if 1 <= char_ord <= 26:
                    return chr(char_ord + 64)

        # 4. Fallback to key name if available
        if isinstance(key, keyboard.Key):
            return key.name.replace("_", " ").title()

        return None

    def on_press(self, key: Any) -> Optional[str]:
        """
        Handle key down event:
        - If modifier: add to active modifiers buffer and return accumulated combo.
        - If regular key:
            * If no modifiers active: ignore ordinary typing keys.
            * If modifiers active: combine them into a single unified combo.
        """
        # 1. Modifier pressed
        if key in MODIFIER_MAP:
            mod_name = MODIFIER_MAP[key]
            if mod_name not in self.active_modifiers:
                self.active_modifiers.append(mod_name)
            return " + ".join(self.active_modifiers)

        # 2. If NO modifier is held: ignore ordinary letters, digits, and typing characters
        if not self.active_modifiers:
            if is_ordinary_typing_key(key):
                return None

        # 3. Resolve key label
        key_label = self.resolve_key_name(key)
        if key_label is not None:
            if self.active_modifiers:
                return " + ".join(self.active_modifiers + [key_label])
            return key_label

        return None

    def on_release(self, key: Any) -> None:
        """Handle key release: update active modifiers buffer."""
        if key in MODIFIER_MAP:
            mod_name = MODIFIER_MAP[key]
            if mod_name in self.active_modifiers:
                self.active_modifiers.remove(mod_name)


class SleekKeyOverlay(QLabel):
    """
    Single sleek, compact QLabel overlay with clean borderless glassmorphic background painting.
    Draws a unified dark acrylic pill close to the bottom taskbar.
    """

    INACTIVITY_TIMEOUT_MS = 3500  # 3.5 seconds
    OVERLAY_HEIGHT = 40
    HORIZONTAL_PADDING = 22  # Padding on left and right
    TASKBAR_GAP = 16         # Distance in pixels above taskbar

    def __init__(self) -> None:
        super().__init__()

        self.combo_text: str = ""
        self.font_obj = QFont("Segoe UI", 12)
        self.font_obj.setWeight(QFont.Weight.Bold)

        self._configure_window_attributes()
        self._setup_inactivity_timer()

    def _configure_window_attributes(self) -> None:
        """Set window flags for always-on-top, frameless tool window, and click-through."""
        self.setWindowTitle("Shortcut Overlay")
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

    def _setup_inactivity_timer(self) -> None:
        """Initialize inactivity timer to auto-hide the label after 3.5s of no input."""
        self.inactivity_timer = QTimer(self)
        self.inactivity_timer.setSingleShot(True)
        self.inactivity_timer.setInterval(self.INACTIVITY_TIMEOUT_MS)
        self.inactivity_timer.timeout.connect(self.hide)

    def _reposition_on_screen(self) -> None:
        """Center the label horizontally right above the primary display's taskbar."""
        screen = QGuiApplication.primaryScreen()
        if screen:
            screen_geo = screen.availableGeometry()
            win_width = self.width()
            win_height = self.height()
            pos_x = screen_geo.x() + (screen_geo.width() - win_width) // 2
            pos_y = screen_geo.y() + screen_geo.height() - win_height - self.TASKBAR_GAP
            self.move(pos_x, pos_y)

    def display_text(self, text: str) -> None:
        """Update combo text, resize pill geometry to fit, center on screen, and reset timer."""
        self.combo_text = text

        # Calculate exact text width with padding for a clean pill shape
        fm = QFontMetrics(self.font_obj)
        text_width = fm.horizontalAdvance(self.combo_text)
        new_width = max(text_width + (self.HORIZONTAL_PADDING * 2), 86)

        self.setFixedSize(new_width, self.OVERLAY_HEIGHT)
        self._reposition_on_screen()
        self.update()  # Trigger paintEvent

        if not self.isVisible():
            self.show()

        self.inactivity_timer.start(self.INACTIVITY_TIMEOUT_MS)

    def paintEvent(self, a0: QPaintEvent | None) -> None:
        """Draw unified glassmorphic dark background with subtle edge (no cyan border)."""
        if not self.combo_text:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        # 1. Black background with 0.7 opacity and subtle, elegant glass edge
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        painter.setBrush(QBrush(QColor(0, 0, 0, int(255 * 0.7))))
        painter.setPen(QPen(QColor(255, 255, 255, 25), 1))
        painter.drawRoundedRect(rect, 10.0, 10.0)

        # 2. Render combo text
        painter.setFont(self.font_obj)
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.combo_text)


def check_single_instance() -> Any:
    """Ensure only one instance of Shortcut Overlay runs at a time via a Windows Named Mutex."""
    mutex_name = "Global\\ShortcutOverlay_SingleInstance_Mutex"
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
    last_error = ctypes.windll.kernel32.GetLastError()
    ERROR_ALREADY_EXISTS = 183
    if last_error == ERROR_ALREADY_EXISTS:
        return None
    return mutex


def main() -> None:
    # Build-time helper: generate the .ico embedded into the executable.
    if len(sys.argv) >= 3 and sys.argv[1] == "--make-icon":
        save_icon_file(sys.argv[2])
        return

    # Single-instance guard: prevent duplicate running instances
    single_instance_mutex = check_single_instance()
    if single_instance_mutex is None:
        return

    app = QApplication(sys.argv)
    app.setApplicationName("Shortcut Overlay")
    # The overlay label hides/shows constantly, so closing it must NOT quit the app.
    app.setQuitOnLastWindowClosed(False)

    overlay = SleekKeyOverlay()

    # --- System tray icon: right-click -> "Thoát" ---
    tray = QSystemTrayIcon(create_app_icon(), app)
    tray.setToolTip("Shortcut Overlay")

    tray_menu = QMenu()
    quit_action = QAction("Thoát", tray_menu)
    quit_action.triggered.connect(app.quit)
    tray_menu.addAction(quit_action)
    tray.setContextMenu(tray_menu)

    tray.show()

    # Startup notification (slight delay so the tray icon is registered first).
    QTimer.singleShot(
        600,
        lambda: tray.showMessage(
            "Shortcut Overlay",
            "Ứng dụng đã khởi chạy và đang chạy nền.\n"
            "Chuột phải vào biểu tượng ở khay hệ thống để thoát.",
            QSystemTrayIcon.MessageIcon.Information,
            5000,
        ),
    )

    tracker = KeyComboTracker()
    emitter = KeySignalEmitter()
    emitter.key_event.connect(overlay.display_text)

    def on_press(key: Any) -> None:
        combo = tracker.on_press(key)
        if combo:
            emitter.key_event.emit(combo)

    def on_release(key: Any) -> None:
        tracker.on_release(key)

    # Start background pynput listener
    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.daemon = True
    listener.start()

    app.aboutToQuit.connect(listener.stop)
    app.aboutToQuit.connect(tray.hide)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
