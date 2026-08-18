import os
import sys
import unittest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from settings.manager import SettingsManager, DiscordDestinationConfig
from app.tray import create_app_icon
from ui.settings_dialog import SettingsDialog
from ui.setup_dialog import SetupWizardDialog
from capture.sniper import ScreenSniperOverlay


class TestGUIComponents(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Initialize QApplication once for all GUI tests
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication(sys.argv)

    def test_app_icon_generation(self):
        icon_connected = create_app_icon(connected=True)
        self.assertFalse(icon_connected.isNull())

        icon_disconnected = create_app_icon(connected=False)
        self.assertFalse(icon_disconnected.isNull())

    def test_settings_dialog_instantiation(self):
        mgr = SettingsManager()
        dialog = SettingsDialog(mgr)
        self.assertIsNotNone(dialog)
        # Ensure WindowStaysOnTopHint is NOT set so it does not block Discord / browser
        self.assertFalse(bool(dialog.windowFlags() & Qt.WindowType.WindowStaysOnTopHint))
        dialog.close()

    def test_settings_dialog_disconnect_and_save(self):
        mgr = SettingsManager()
        mgr.set_destination(DiscordDestinationConfig(
            type="discord",
            guild_name="Test Guild",
            channel_name="test-channel",
            webhook_url="https://discord.com/api/webhooks/123/abc"
        ))
        self.assertTrue(mgr.is_configured())

        dialog = SettingsDialog(mgr)
        self.assertEqual(dialog.wh_input.text(), "https://discord.com/api/webhooks/123/abc")

        # Simulate disconnect
        mgr.clear_destination()
        dialog.wh_input.clear()
        dialog._update_destination_ui()
        self.assertEqual(dialog.wh_input.text(), "")

        # Simulate save and close
        dialog._save_and_close()
        self.assertFalse(mgr.is_configured())
        self.assertIsNone(mgr.config.destination)
        dialog.close()

    def test_setup_wizard_instantiation(self):
        mgr = SettingsManager()
        dialog = SetupWizardDialog(mgr)
        self.assertIsNotNone(dialog)
        dialog.close()

    def test_screen_sniper_overlay_geometry(self):
        overlay = ScreenSniperOverlay()
        self.assertIsNotNone(overlay)
        # Verify initial flags
        self.assertTrue(bool(overlay.windowFlags() & Qt.WindowType.FramelessWindowHint))
        overlay.close()

    def test_local_capture_lifecycle(self):
        from app.lifecycle import AppLifecycle
        from PyQt6.QtGui import QImage, QColor
        from PyQt6.QtCore import QBuffer, QIODevice

        lifecycle = AppLifecycle(self.app)
        lifecycle.settings_manager.clear_destination()
        self.assertFalse(lifecycle.settings_manager.is_configured())

        img = QImage(10, 10, QImage.Format.Format_ARGB32)
        img.fill(QColor(255, 0, 0))
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        img.save(buffer, "PNG")
        png_sample = bytes(buffer.data())
        buffer.close()

        lifecycle._on_image_captured(png_sample)


if __name__ == "__main__":
    unittest.main()
