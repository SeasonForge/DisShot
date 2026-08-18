import logging
from typing import Optional
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeyEvent, QKeySequence
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton

logger = logging.getLogger(__name__)


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
        self.record_btn.setFixedHeight(34)
        self.record_btn.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.record_btn.clicked.connect(self._toggle_recording)
        
        # Override keyPressEvent on the button
        self.record_btn.keyPressEvent = self._handle_key_press

        # Reset button
        self.reset_btn = QPushButton("Default")
        self.reset_btn.setFixedHeight(34)
        self.reset_btn.setToolTip("Reset hotkey to default (Print Screen)")
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

    def _start_recording(self):
        self._recording = True
        self.record_btn.setText("⌨️ Press key combination... (Esc to cancel)")
        self.record_btn.setStyleSheet("""
            QPushButton {
                background-color: #4752C4;
                color: #FFFFFF;
                border: 2px solid #5865F2;
                border-radius: 6px;
                font-weight: bold;
            }
        """)
        self.record_btn.setFocus()

    def _stop_recording(self):
        self._recording = False
        self._update_button_style()

    def _update_button_style(self):
        display_text = f"⌨️  {self.current_hotkey}"
        self.record_btn.setText(display_text)
        self.record_btn.setStyleSheet("""
            QPushButton {
                background-color: #2B2D31;
                color: #FFFFFF;
                border: 1px solid #3F4147;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 600;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #35373C;
                border-color: #5865F2;
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
