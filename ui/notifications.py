import logging
import sys
from typing import Optional
from PyQt6.QtWidgets import QSystemTrayIcon, QMessageBox, QWidget

logger = logging.getLogger(__name__)

try:
    import winsound
    WINSOUND_AVAILABLE = True
except ImportError:
    WINSOUND_AVAILABLE = False


class NotificationManager:
    """
    Handles user-facing status notifications, tray balloons, and error dialogues.
    """
    def __init__(self, tray_icon: Optional[QSystemTrayIcon] = None):
        self.tray_icon = tray_icon

    def set_tray_icon(self, tray_icon: QSystemTrayIcon) -> None:
        self.tray_icon = tray_icon

    def play_success_sound(self) -> None:
        if WINSOUND_AVAILABLE:
            try:
                # Standard pleasant Windows notification sound
                winsound.MessageBeep(winsound.MB_OK)
            except Exception:
                pass

    def play_error_sound(self) -> None:
        if WINSOUND_AVAILABLE:
            try:
                winsound.MessageBeep(winsound.MB_ICONHAND)
            except Exception:
                pass

    def show_toast(
        self,
        title: str,
        message: str,
        icon: QSystemTrayIcon.MessageIcon = QSystemTrayIcon.MessageIcon.Information,
        duration_ms: int = 3000
    ) -> None:
        if self.tray_icon and self.tray_icon.isVisible():
            self.tray_icon.showMessage(title, message, icon, duration_ms)
        else:
            logger.info("[Toast] %s: %s", title, message)

    def notify_upload_success(self, url: str) -> None:
        self.play_success_sound()
        self.show_toast(
            "Screenshot Uploaded",
            "Image uploaded to Discord! Link copied to clipboard.",
            QSystemTrayIcon.MessageIcon.Information
        )

    def notify_upload_error(self, error_message: str) -> None:
        self.play_error_sound()
        self.show_toast(
            "Upload Failed",
            f"Could not upload screenshot: {error_message}",
            QSystemTrayIcon.MessageIcon.Warning
        )

    def notify_not_configured(self) -> None:
        self.play_error_sound()
        self.show_toast(
            "Discord Not Connected",
            "Please connect Discord in Settings before taking screenshots.",
            QSystemTrayIcon.MessageIcon.Warning
        )

    def show_error_dialog(self, title: str, message: str, parent: Optional[QWidget] = None) -> None:
        QMessageBox.critical(parent, title, message)

    def show_info_dialog(self, title: str, message: str, parent: Optional[QWidget] = None) -> None:
        QMessageBox.information(parent, title, message)
