import logging
import threading
import ctypes
import time
from ctypes import wintypes
from typing import Optional, Tuple
from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class HotkeyEmitter(QObject):
    triggered = pyqtSignal()


# Win32 Constants
WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_SYSKEYDOWN = 0x0104
WM_QUIT = 0x0012

VK_CONTROL = 0x11
VK_SHIFT = 0x10
VK_MENU = 0x12  # Alt
VK_LWIN = 0x5B
VK_RWIN = 0x5C

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008

# Win32 Virtual Key Map
VK_MAP = {
    "print screen": 0x2C,
    "print_screen": 0x2C,
    "printscreen": 0x2C,
    "prntscrn": 0x2C,
    "prtscn": 0x2C,
    "insert": 0x2D,
    "delete": 0x2E,
    "home": 0x24,
    "end": 0x23,
    "pageup": 0x21,
    "pagedown": 0x22,
    "space": 0x20,
    "tab": 0x09,
    "return": 0x0D,
    "enter": 0x0D,
    "escape": 0x1B,
    "esc": 0x1B,
}

# F1 - F24
for i in range(1, 25):
    VK_MAP[f"f{i}"] = 0x70 + (i - 1)

# Letters A-Z
for c in range(ord('a'), ord('z') + 1):
    VK_MAP[chr(c)] = 0x41 + (c - ord('a'))

# Numbers 0-9
for n in range(10):
    VK_MAP[str(n)] = 0x30 + n


def parse_hotkey(hotkey_str: str) -> Tuple[int, int]:
    """
    Parses a hotkey string (e.g. 'Ctrl + Shift + S', 'Print Screen', 'F10')
    into (target_modifiers, target_vk).
    """
    if not hotkey_str:
        return (0, 0x2C)

    raw_low = hotkey_str.strip().lower()
    if raw_low in VK_MAP:
        return (0, VK_MAP[raw_low])

    parts = [p.strip().lower() for p in hotkey_str.replace("+", " ").split() if p.strip()]
    modifiers = 0
    vk_code = 0x2C

    for part in parts:
        if part in ("ctrl", "control"):
            modifiers |= MOD_CONTROL
        elif part in ("alt", "menu"):
            modifiers |= MOD_ALT
        elif part in ("shift",):
            modifiers |= MOD_SHIFT
        elif part in ("win", "cmd", "meta"):
            modifiers |= MOD_WIN
        elif part in VK_MAP:
            vk_code = VK_MAP[part]
        elif len(part) == 1:
            vk_code = ord(part.upper())

    return (modifiers, vk_code)


def convert_to_pynput_combo(hotkey_str: str) -> str:
    """Helper for unit tests."""
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

    for i in range(1, 13):
        special_keys[f"f{i}"] = f"<f{i}>"

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


# Ctypes Hook Function Prototype
HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_longlong, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD]
user32.SetWindowsHookExW.restype = ctypes.c_void_p
user32.CallNextHookEx.argtypes = [ctypes.c_void_p, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
user32.CallNextHookEx.restype = ctypes.c_longlong
user32.UnhookWindowsHookEx.argtypes = [ctypes.c_void_p]
user32.UnhookWindowsHookEx.restype = wintypes.BOOL
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = ctypes.c_short


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ('vkCode', wintypes.DWORD),
        ('scanCode', wintypes.DWORD),
        ('flags', wintypes.DWORD),
        ('time', wintypes.DWORD),
        ('dwExtraInfo', ctypes.c_ulonglong)
    ]


class GlobalHotkeyManager:
    """
    Rock-solid Windows global keyboard hook using SetWindowsHookExW (WH_KEYBOARD_LL)
    with dedicated message pump thread, key suppression and debouncing.
    """
    def __init__(self, hotkey_str: str = "Print Screen"):
        self.hotkey_str = hotkey_str
        self.emitter = HotkeyEmitter()
        self._thread: Optional[threading.Thread] = None
        self._thread_id: Optional[int] = None
        self._hook_handle: Optional[int] = None
        self._c_proc = None  # Hold reference to prevent garbage collection
        self._is_running = False
        self._last_trigger_time = 0.0

        self._target_mods = 0
        self._target_vk = 0x2C

    def start(self, hotkey_str: Optional[str] = None) -> None:
        if hotkey_str:
            self.hotkey_str = hotkey_str

        self.stop()
        self._is_running = True
        self._target_mods, self._target_vk = parse_hotkey(self.hotkey_str)

        self._thread = threading.Thread(target=self._hook_worker, daemon=True)
        self._thread.start()
        logger.info("Global hotkey listener started for %s (mods=0x%X, vk=0x%X)", self.hotkey_str, self._target_mods, self._target_vk)

    def _hook_proc(self, nCode: int, wParam: int, lParam: int) -> int:
        if nCode >= 0 and wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
            try:
                kb = KBDLLHOOKSTRUCT.from_address(lParam)
                if kb.vkCode == self._target_vk:
                    # Verify required modifier keys
                    ctrl_down = bool(user32.GetAsyncKeyState(VK_CONTROL) & 0x8000)
                    shift_down = bool(user32.GetAsyncKeyState(VK_SHIFT) & 0x8000)
                    alt_down = bool(user32.GetAsyncKeyState(VK_MENU) & 0x8000)
                    win_down = bool((user32.GetAsyncKeyState(VK_LWIN) & 0x8000) or (user32.GetAsyncKeyState(VK_RWIN) & 0x8000))

                    req_ctrl = bool(self._target_mods & MOD_CONTROL)
                    req_shift = bool(self._target_mods & MOD_SHIFT)
                    req_alt = bool(self._target_mods & MOD_ALT)
                    req_win = bool(self._target_mods & MOD_WIN)

                    if (ctrl_down == req_ctrl and
                        shift_down == req_shift and
                        alt_down == req_alt and
                        win_down == req_win):

                        now = time.time()
                        if now - self._last_trigger_time >= 0.35:
                            self._last_trigger_time = now
                            logger.info("Global hotkey triggered: %s", self.hotkey_str)
                            self.emitter.triggered.emit()

                        # Return 1 to suppress Windows Snipping Tool from also intercepting PrintScreen
                        return 1
            except Exception as e:
                logger.error("Error in hook_proc: %s", e)

        return user32.CallNextHookEx(self._hook_handle, nCode, wParam, lParam)

    def _hook_worker(self) -> None:
        self._thread_id = kernel32.GetCurrentThreadId()
        self._c_proc = HOOKPROC(self._hook_proc)

        self._hook_handle = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._c_proc, None, 0)
        if not self._hook_handle:
            logger.error("Failed to install SetWindowsHookExW! Error: %d", kernel32.GetLastError())
            return

        logger.debug("SetWindowsHookExW installed successfully (handle=%s)", self._hook_handle)

        msg = wintypes.MSG()
        while self._is_running:
            res = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if res <= 0:  # WM_QUIT or error
                break
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        if self._hook_handle:
            user32.UnhookWindowsHookEx(self._hook_handle)
            self._hook_handle = None

        logger.debug("Hook worker thread ended.")

    def stop(self) -> None:
        self._is_running = False
        if self._thread_id:
            try:
                user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
            except Exception:
                pass
            self._thread_id = None

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.3)
            self._thread = None
