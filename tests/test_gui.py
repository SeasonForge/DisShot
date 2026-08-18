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


if __name__ == "__main__":
    unittest.main()
