import logging
import threading
from typing import Optional, Callable
from PyQt6.QtCore import QObject, pyqtSignal
from pynput import keyboard

logger = logging.getLogger(__name__)


class HotkeyEmitter(QObject):
    triggered = pyqtSignal()


def convert_to_pynput_combo(hotkey_str: str) -> str:
    """
    Converts user-friendly hotkey format (e.g. 'Ctrl + Shift + S')
    into pynput GlobalHotKeys pattern (e.g. '<ctrl>+<shift>+s').
    """
    if not hotkey_str:
        return "<print_screen>"

    parts = [p.strip().lower() for p in hotkey_str.replace("+", " ").split() if p.strip()]
    formatted_parts = []
    
    special_keys = {
        "ctrl": "<ctrl>",
        "control": "<ctrl>",
        "alt": "<alt>",
        "shift": "<shift>",
        "win": "<cmd>",
        "cmd": "<cmd>",
        "print screen": "<print_screen>",
        "print_screen": "<print_screen>",
        "printscreen": "<print_screen>",
        "prntscrn": "<print_screen>",
        "prtscn": "<print_screen>",
        "insert": "<insert>",
        "delete": "<delete>",
        "home": "<home>",
        "end": "<end>",
        "pageup": "<page_up>",
        "pagedown": "<page_down>",
        "space": "<space>",
    }

    # Add F1-F12
    for i in range(1, 13):
        special_keys[f"f{i}"] = f"<f{i}>"

    # Handle single 'print screen'
    lowered_raw = hotkey_str.strip().lower()
    if lowered_raw in special_keys:
        return special_keys[lowered_raw]

    for p in parts:
        if p in special_keys:
            formatted_parts.append(special_keys[p])
        elif len(p) == 1:
            formatted_parts.append(p)
        else:
            formatted_parts.append(f"<{p}>")

    return "+".join(formatted_parts)


class GlobalHotkeyManager:
    """
    Manages global keyboard listening using pynput and delivers
    thread-safe signals to Qt main thread.
    """
    def __init__(self, hotkey_str: str = "Print Screen"):
        self.hotkey_str = hotkey_str
        self.emitter = HotkeyEmitter()
        self._listener: Optional[keyboard.Listener] = None
        self._global_hotkeys: Optional[keyboard.GlobalHotKeys] = None
        self._is_running = False
        self._last_trigger_time = 0.0

    def start(self, hotkey_str: Optional[str] = None) -> None:
        if hotkey_str:
            self.hotkey_str = hotkey_str

        self.stop()
        self._is_running = True

        normalized = self.hotkey_str.strip().lower()

        if normalized in ("print_screen", "printscreen", "prntscrn", "prtscn", "print screen"):
            self._start_printscreen_listener()
        else:
            self._start_combo_listener(self.hotkey_str)

    def _on_trigger(self) -> None:
        import time
        now = time.time()
        # Debounce: prevent auto-repeat spam when key is held down
        if now - self._last_trigger_time < 0.4:
            return
        self._last_trigger_time = now

        logger.info("Global hotkey triggered: %s", self.hotkey_str)
        self.emitter.triggered.emit()

    def _start_printscreen_listener(self) -> None:
        def on_press(key):
            try:
                if key == keyboard.Key.print_screen:
                    self._on_trigger()
            except Exception as e:
                logger.error("Error in hotkey on_press: %s", e)

        self._listener = keyboard.Listener(on_press=on_press)
        self._listener.daemon = True
        self._listener.start()
        logger.info("Global hotkey registered: Print Screen")

    def _start_combo_listener(self, combo_str: str) -> None:
        try:
            pynput_combo = convert_to_pynput_combo(combo_str)
            self._global_hotkeys = keyboard.GlobalHotKeys({
                pynput_combo: self._on_trigger
            })
            self._global_hotkeys.daemon = True
            self._global_hotkeys.start()
            logger.info("Global hotkey registered: %s (pattern: %s)", combo_str, pynput_combo)
        except Exception as e:
            logger.warning("Failed to register combo %s, falling back to PrintScreen listener: %s", combo_str, e)
            self._start_printscreen_listener()

    def stop(self) -> None:
        self._is_running = False
        if self._listener:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None

        if self._global_hotkeys:
            try:
                self._global_hotkeys.stop()
            except Exception:
                pass
            self._global_hotkeys = None
