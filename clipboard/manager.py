import logging
import ctypes
from ctypes import wintypes
import time
from typing import Optional

logger = logging.getLogger(__name__)

GMEM_MOVEABLE = 0x0002
CF_DIB = 8
CF_UNICODETEXT = 13

try:
    kernel32 = ctypes.windll.kernel32
    user32 = ctypes.windll.user32

    user32.OpenClipboard.argtypes = [wintypes.HWND]
    user32.OpenClipboard.restype = wintypes.BOOL
    user32.EmptyClipboard.restype = wintypes.BOOL
    user32.SetClipboardData.argtypes = [wintypes.UINT, ctypes.c_void_p]
    user32.SetClipboardData.restype = ctypes.c_void_p
    user32.GetClipboardData.argtypes = [wintypes.UINT]
    user32.GetClipboardData.restype = ctypes.c_void_p
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
    def copy_image(image_bytes: bytes) -> bool:
        """
        Copies image bytes (PNG/JPEG) to the system clipboard using native Win32 CF_DIB
        with fallback to PyQt6 QClipboard.
        """
        if not image_bytes:
            return False

        # 1. Native Windows Win32 API (CF_DIB)
        if WIN32_CLIPBOARD_AVAILABLE:
            try:
                from PyQt6.QtGui import QImage
                from PyQt6.QtCore import QBuffer, QIODevice

                qimg = QImage.fromData(image_bytes, "PNG")
                if not qimg.isNull():
                    buffer = QBuffer()
                    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
                    qimg.save(buffer, "BMP")
                    bmp_data = bytes(buffer.data())
                    buffer.close()

                    # CF_DIB payload is BMP file without the 14-byte BITMAPFILEHEADER
                    if len(bmp_data) > 14:
                        dib_data = bmp_data[14:]
                        for attempt in range(10):
                            if user32.OpenClipboard(None):
                                try:
                                    user32.EmptyClipboard()
                                    h_mem = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(dib_data))
                                    if h_mem:
                                        p_mem = kernel32.GlobalLock(h_mem)
                                        if p_mem:
                                            ctypes.memmove(p_mem, dib_data, len(dib_data))
                                            kernel32.GlobalUnlock(h_mem)
                                            res = user32.SetClipboardData(CF_DIB, h_mem)
                                            if res:
                                                logger.info("Image copied to clipboard via native Win32 CF_DIB (%d bytes)", len(dib_data))
                                                return True
                                finally:
                                    user32.CloseClipboard()
                            time.sleep(0.03)
            except Exception as e:
                logger.error("Native Win32 image copy failed: %s", e)

        # 2. Fallback to PyQt6 QClipboard
        try:
            from PyQt6.QtGui import QGuiApplication, QImage
            image = QImage.fromData(image_bytes, "PNG")
            if not image.isNull():
                cb = QGuiApplication.clipboard()
                if cb is not None:
                    cb.setImage(image)
                    logger.info("Image copied to clipboard via QClipboard fallback.")
                    return True
        except Exception as e:
            logger.error("Failed to copy image via QClipboard fallback: %s", e)

        return False

    @staticmethod
    def get_text() -> str:
        """
        Retrieves text from the system clipboard.
        """
        if WIN32_CLIPBOARD_AVAILABLE:
            for attempt in range(5):
                if user32.OpenClipboard(None):
                    try:
                        h_mem = user32.GetClipboardData(CF_UNICODETEXT)
                        if h_mem:
                            p_mem = kernel32.GlobalLock(h_mem)
                            if p_mem:
                                text = ctypes.wstring_at(p_mem)
                                kernel32.GlobalUnlock(h_mem)
                                return text
                    finally:
                        user32.CloseClipboard()
                time.sleep(0.02)

        try:
            from PyQt6.QtGui import QGuiApplication, QClipboard
            clipboard = QGuiApplication.clipboard()
            if clipboard is None:
                return ""
            return clipboard.text(mode=QClipboard.Mode.Clipboard)
        except Exception as e:
            logger.error("Failed to read from clipboard: %s", e)
            return ""

