import logging
import ctypes
from ctypes import wintypes
import time
from typing import Optional

logger = logging.getLogger(__name__)

GMEM_MOVEABLE = 0x0002
CF_UNICODETEXT = 13

try:
    kernel32 = ctypes.windll.kernel32
    user32 = ctypes.windll.user32

    user32.OpenClipboard.argtypes = [wintypes.HWND]
    user32.OpenClipboard.restype = wintypes.BOOL
    user32.EmptyClipboard.restype = wintypes.BOOL
    user32.SetClipboardData.argtypes = [wintypes.UINT, ctypes.c_void_p]
    user32.SetClipboardData.restype = ctypes.c_void_p
    user32.CloseClipboard.restype = wintypes.BOOL

    kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = ctypes.c_void_p
    kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalUnlock.restype = wintypes.BOOL

    WIN32_CLIPBOARD_AVAILABLE = True
except Exception as e:
    logger.warning("Native Win32 clipboard init failed: %s", e)
    WIN32_CLIPBOARD_AVAILABLE = False


class ClipboardManager:
    @staticmethod
    def copy_text(text: str) -> bool:
        """
        Copies text to the system clipboard using native Win32 API
        with fallback to PyQt6 clipboard.
        """
        if not text:
            return False

        # 1. Native Windows Win32 API (thread-safe, works reliably in background threads)
        if WIN32_CLIPBOARD_AVAILABLE:
            for attempt in range(10):
                if user32.OpenClipboard(None):
                    try:
                        user32.EmptyClipboard()
                        encoded = text.encode("utf-16-le") + b"\x00\x00"
                        h_mem = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(encoded))
                        if h_mem:
                            p_mem = kernel32.GlobalLock(h_mem)
                            if p_mem:
                                ctypes.memmove(p_mem, encoded, len(encoded))
                                kernel32.GlobalUnlock(h_mem)
                                res = user32.SetClipboardData(CF_UNICODETEXT, h_mem)
                                if res:
                                    logger.info("Copied to clipboard via native Win32: %s", text)
                                    return True
                    finally:
                        user32.CloseClipboard()
                time.sleep(0.03)

        # 2. Fallback to PyQt6 QClipboard
        try:
            from PyQt6.QtGui import QGuiApplication, QClipboard
            clipboard = QGuiApplication.clipboard()
            if clipboard is not None:
                clipboard.setText(text, mode=QClipboard.Mode.Clipboard)
                logger.info("Copied to clipboard via QClipboard: %s", text)
                return True
        except Exception as e:
            logger.error("Failed to copy text via QClipboard fallback: %s", e)

        return False

    @staticmethod
    def get_text() -> str:
        """
        Retrieves text from the system clipboard.
        """
        try:
            clipboard = QGuiApplication.clipboard()
            if clipboard is None:
                return ""
            return clipboard.text(mode=QClipboard.Mode.Clipboard)
        except Exception as e:
            logger.error("Failed to read from clipboard: %s", e)
            return ""
