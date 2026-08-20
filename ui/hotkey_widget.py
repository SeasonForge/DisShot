import logging
from typing import Optional
from PyQt6.QtCore import Qt, pyqtSignal, QByteArray
from PyQt6.QtGui import QKeyEvent, QKeySequence, QIcon, QPixmap, QPainter, QColor
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton

import i18n
from i18n import t

logger = logging.getLogger(__name__)

SVG_WINDOWS = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="#94A3B8"><path d="M0 3.449L9.75 2.1v9.451H0m10.949-9.602L24 0v11.4H10.949M0 12.6h9.75v9.451L0 20.699M10.949 12.6H24V24l-12.9-1.801"/></svg>"""
SVG_KEYBOARD = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#94A3B8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="20" height="16" x="2" y="4" rx="2"/><path d="M6 8h.01M10 8h.01M14 8h.01M18 8h.01M6 12h.01M10 12h.01M14 12h.01M18 12h.01M7 16h10"/></svg>"""


def render_svg_icon(svg_str: str, size: int = 16) -> QIcon:
    renderer = QSvgRenderer(QByteArray(svg_str.encode("utf-8")))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)


def normalize_hotkey_string(hotkey: str) -> str:
    """
    Normalizes a hotkey string into a consistent display format (e.g. 'Ctrl + Shift + S').
    """
    if not hotkey:
        return "Print Screen"
    
    clean = hotkey.strip()
    low = clean.lower()
    if low in ("print_screen", "printscreen", "prntscrn", "prtscn", "print screen"):
        return "Print Screen"
    
    parts = [p.strip("<> ").capitalize() for p in clean.replace("+", " ").split()]
    return " + ".join(parts)


class HotkeyRecorderWidget(QWidget):
    """
    An interactive Hotkey recorder widget that captures key combinations
    on press without requiring manual text typing.
    """
    hotkey_changed = pyqtSignal(str)

    def __init__(self, current_hotkey: str = "Print Screen", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.current_hotkey = normalize_hotkey_string(current_hotkey)
        self._recording = False
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Record button
        self.record_btn = QPushButton()
        self.record_btn.setFixedHeight(36)
        self.record_btn.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.record_btn.clicked.connect(self._toggle_recording)
        
        # Override keyPressEvent on the button
        self.record_btn.keyPressEvent = self._handle_key_press

        # Reset button
        self.reset_btn = QPushButton(t("btn_default"))
        self.reset_btn.setFixedHeight(36)
        self.reset_btn.setToolTip("Print Screen")
        self.reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #121D30;
                color: #CBD5E1;
                border: 1px solid #1E3150;
                border-radius: 8px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #1A2B47;
                border-color: #38BDF8;
                color: #FFFFFF;
            }
        """)
        self.reset_btn.clicked.connect(self._reset_to_default)

        layout.addWidget(self.record_btn, 1)
        layout.addWidget(self.reset_btn)

        self._update_button_style()

    def get_hotkey(self) -> str:
        return self.current_hotkey

    def set_hotkey(self, hotkey: str):
        self.current_hotkey = normalize_hotkey_string(hotkey)
        self._stop_recording()

    def _toggle_recording(self):
        if self._recording:
            self._stop_recording()
        else:
            self._start_recording()

    def retranslate_ui(self):
        self.reset_btn.setText(t("btn_default"))
        if not self._recording:
            self._update_button_style()

    def _start_recording(self):
        self._recording = True
        self.record_btn.setText(t("hotkey_recording"))
        self.record_btn.setIcon(QIcon())
        self.record_btn.setStyleSheet("""
            QPushButton {
                background-color: #1E3A8A;
                color: #FFFFFF;
                border: 2px solid #3B82F6;
                border-radius: 8px;
                font-weight: bold;
                font-size: 12px;
            }
        """)
        self.record_btn.setFocus()

    def _stop_recording(self):
        self._recording = False
        self._update_button_style()

    def _update_button_style(self):
        self.record_btn.setText(f"  {self.current_hotkey}")
        if "Win" in self.current_hotkey or "Print" in self.current_hotkey:
            self.record_btn.setIcon(render_svg_icon(SVG_WINDOWS, 14))
        else:
            self.record_btn.setIcon(render_svg_icon(SVG_KEYBOARD, 14))

        self.record_btn.setStyleSheet("""
            QPushButton {
                background-color: #0A111E;
                color: #FFFFFF;
                border: 1px solid #1E2E4A;
                border-radius: 8px;
                padding: 6px 14px;
                font-weight: 600;
                font-size: 13px;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #0F1A2E;
                border-color: #3B82F6;
            }
        """)

    def _reset_to_default(self):
        self.current_hotkey = "Print Screen"
        self._stop_recording()
        self.hotkey_changed.emit("Print Screen")

    def _handle_key_press(self, event: QKeyEvent):
        if not self._recording:
            QPushButton.keyPressEvent(self.record_btn, event)
            return

        key = event.key()

        # Ignore standalone modifier keys (wait for combo key)
        if key in (Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta):
            return

        # Esc cancels recording
        if key == Qt.Key.Key_Escape:
            self._stop_recording()
            return

        modifiers = event.modifiers()
        parts = []

        if modifiers & Qt.KeyboardModifier.ControlModifier:
            parts.append("Ctrl")
        if modifiers & Qt.KeyboardModifier.AltModifier:
            parts.append("Alt")
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            parts.append("Shift")
        if modifiers & Qt.KeyboardModifier.MetaModifier:
            parts.append("Win")

        # Determine key name
        key_name = ""
        if key == Qt.Key.Key_Print:
            key_name = "Print Screen"
        elif Qt.Key.Key_F1 <= key <= Qt.Key.Key_F12:
            key_name = f"F{key - Qt.Key.Key_F1 + 1}"
        elif key == Qt.Key.Key_Insert:
            key_name = "Insert"
        elif key == Qt.Key.Key_Delete:
            key_name = "Delete"
        elif key == Qt.Key.Key_Home:
            key_name = "Home"
        elif key == Qt.Key.Key_End:
            key_name = "End"
        elif key == Qt.Key.Key_PageUp:
            key_name = "PageUp"
        elif key == Qt.Key.Key_PageDown:
            key_name = "PageDown"
        elif key == Qt.Key.Key_Space:
            key_name = "Space"
        else:
            # Standard printable or letter key
            text = QKeySequence(key).toString()
            if text:
                key_name = text.upper()

        if key_name:
            if key_name not in parts:
                parts.append(key_name)
            combo = " + ".join(parts)
            logger.info("Recorded hotkey: %s", combo)
            self.current_hotkey = combo
            self._stop_recording()
            self.hotkey_changed.emit(combo)
