import logging
import threading
import datetime
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import QApplication

from config import APP_NAME
from settings.manager import SettingsManager
from app.tray import TrayManager
from app.hotkey import GlobalHotkeyManager
from capture.sniper import ScreenSniperOverlay
from upload.base import UploadResult
from discord.uploader import DiscordUploader
from clipboard.manager import ClipboardManager
from ui.notifications import NotificationManager
from ui.settings_dialog import SettingsDialog

logger = logging.getLogger(__name__)


class UploadWorker(QObject):
    finished = pyqtSignal(UploadResult)

    def __init__(self, uploader: DiscordUploader, image_bytes: bytes):
        super().__init__()
        self.uploader = uploader
        self.image_bytes = image_bytes

    def run(self):
        result = self.uploader.upload_image(self.image_bytes)
        self.finished.emit(result)


class AppLifecycle(QObject):
    """
    Central coordinator managing application state, capture flow,
    hotkeys, tray icon, and background uploads.
    """
    def __init__(self, qapp: QApplication):
        super().__init__()
        self.qapp = qapp
        
        # 1. Load Settings
        self.settings_manager = SettingsManager()

        # 2. Setup System Tray & Notifications
        self.tray_manager = TrayManager(self.settings_manager)
        self.notification_manager = NotificationManager(self.tray_manager.tray_icon)

        # 3. Setup Global Hotkey
        self.hotkey_manager = GlobalHotkeyManager(self.settings_manager.config.hotkey)

        # 4. Dialog references
        self._settings_dialog: Optional[SettingsDialog] = None
        self._current_sniper: Optional[ScreenSniperOverlay] = None

        # 5. Wire signals
        self._connect_signals()

    def _connect_signals(self):
        # Tray signals
        self.tray_manager.take_screenshot_requested.connect(self.trigger_capture)
        self.tray_manager.open_settings_requested.connect(self.open_settings)
        self.tray_manager.connect_discord_requested.connect(self.open_settings)
        self.tray_manager.disconnect_discord_requested.connect(self.disconnect_discord)
        self.tray_manager.quit_requested.connect(self.quit_app)

        # Hotkey trigger
        self.hotkey_manager.emitter.triggered.connect(self.trigger_capture)

    def start(self):
        """
        Starts the background services and displays readiness notification.
        """
        logger.info("Starting %s...", APP_NAME)
        self.hotkey_manager.start(self.settings_manager.config.hotkey)

        status_text = "Discord подключен" if self.settings_manager.is_configured() else "Локальный режим"
        self.notification_manager.show_toast(
            f"{APP_NAME} готов ({status_text})",
            f"Нажмите {self.settings_manager.config.hotkey} для создания скриншота.",
        )

    @pyqtSlot()
    def trigger_capture(self):
        """
        Initiates the region selection overlay capture.
        """
        if self._current_sniper is not None:
            # Capture already in progress
            return

        logger.info("Initiating screen capture overlay...")
        self._current_sniper = ScreenSniperOverlay()
        self._current_sniper.captured.connect(self._on_image_captured)
        self._current_sniper.copied_local.connect(self._on_image_copied_locally)
        self._current_sniper.cancelled.connect(self._on_capture_cancelled)
        self._current_sniper.destroyed.connect(self._on_capture_cancelled)
        self._current_sniper.start_capture()

    def _copy_image_to_clipboard(self, image_bytes: bytes):
        try:
            from PyQt6.QtGui import QGuiApplication, QImage
            image = QImage.fromData(image_bytes, "PNG")
            if not image.isNull():
                cb = QGuiApplication.clipboard()
                if cb:
                    cb.setImage(image)
                    logger.info("Image copied directly to clipboard as bitmap.")
        except Exception as e:
            logger.error("Failed to copy image bitmap to clipboard: %s", e)

    def _save_local_copy_if_enabled(self, image_bytes: bytes) -> Optional[str]:
        cfg = self.settings_manager.config
        if not cfg.save_local_copy or not cfg.local_copy_dir:
            return None

        try:
            target_dir = Path(cfg.local_copy_dir)
            target_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            file_path = target_dir / f"Screenshot_{timestamp}.png"

            counter = 1
            while file_path.exists():
                file_path = target_dir / f"Screenshot_{timestamp}_{counter}.png"
                counter += 1

            file_path.write_bytes(image_bytes)
            logger.info("Local copy saved to: %s", file_path)
            return str(file_path)
        except Exception as e:
            logger.error("Failed to save local screenshot copy: %s", e)
            return None

    @pyqtSlot(bytes)
    def _on_image_copied_locally(self, image_bytes: bytes):
        self._current_sniper = None
        saved_path = self._save_local_copy_if_enabled(image_bytes)
        logger.info("Image copied locally to clipboard.")
        if self.settings_manager.config.notifications_enabled:
            if saved_path:
                self.notification_manager.show_toast(
                    f"{APP_NAME} — Сохранено",
                    "Скриншот скопирован в буфер и сохранён в папку.",
                )
            else:
                self.notification_manager.notify_copied_to_clipboard()

    @pyqtSlot(bytes)
    def _on_image_captured(self, image_bytes: bytes):
        self._current_sniper = None
        saved_path = self._save_local_copy_if_enabled(image_bytes)

        dest = self.settings_manager.config.destination
        if dest and dest.webhook_url:
            logger.info("Image captured (%d bytes), starting Discord upload...", len(image_bytes))
            # Perform upload in a background thread to prevent UI freezing
            uploader = DiscordUploader(dest.webhook_url)
            
            def upload_thread_target():
                result = uploader.upload_image(image_bytes)
                # Route back via QMetaObject / pyqtSlot invocation
                self._handle_upload_result(result)

            threading.Thread(target=upload_thread_target, daemon=True).start()
        else:
            # Local-only mode: copy image bitmap to clipboard and show toast
            logger.info("Image captured in local mode (%d bytes). Copying to clipboard...", len(image_bytes))
            self._copy_image_to_clipboard(image_bytes)
            if self.settings_manager.config.notifications_enabled:
                if saved_path:
                    self.notification_manager.show_toast(
                        f"{APP_NAME} — Сохранено",
                        "Скриншот скопирован в буфер и сохранён в папку.",
                    )
                else:
                    self.notification_manager.notify_copied_to_clipboard()

    def _handle_upload_result(self, result: UploadResult):
        if result.success and result.url:
            logger.info("Upload succeeded. Setting clipboard URL: %s", result.url)
            copied = ClipboardManager.copy_text(result.url)
            
            if self.settings_manager.config.notifications_enabled:
                self.notification_manager.notify_upload_success(result.url)
        else:
            logger.error("Upload failed: %s", result.error_message)
            self.notification_manager.notify_upload_error(
                result.error_message or "Unknown upload error occurred."
            )

    @pyqtSlot()
    def _on_capture_cancelled(self):
        self._current_sniper = None
        logger.info("Capture cancelled by user.")

    @pyqtSlot()
    def open_settings(self):
        if self._settings_dialog is None:
            self._settings_dialog = SettingsDialog(self.settings_manager)
            self._settings_dialog.settings_changed.connect(self._on_settings_changed)
            self._settings_dialog.trigger_capture_requested.connect(self.trigger_capture)
            self._settings_dialog.finished.connect(self._on_settings_dialog_closed)
        
        self._settings_dialog.show()
        self._settings_dialog.activateWindow()
        self._settings_dialog.raise_()

    def _on_settings_dialog_closed(self):
        self._settings_dialog = None

    @pyqtSlot()
    def _on_settings_changed(self):
        logger.info("Settings updated. Refreshing services...")
        self.tray_manager.refresh()
        self.hotkey_manager.start(self.settings_manager.config.hotkey)

    @pyqtSlot()
    def disconnect_discord(self):
        self.settings_manager.clear_destination()
        self._on_settings_changed()
        self.notification_manager.show_toast(
            "Discord Disconnected",
            "Your Discord destination has been removed.",
        )

    @pyqtSlot()
    def quit_app(self):
        logger.info("Shutting down Screenshotter...")
        self.hotkey_manager.stop()
        self.qapp.quit()
