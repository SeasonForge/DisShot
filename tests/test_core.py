import os
import unittest
from pathlib import Path
import tempfile
import json

import base64
from unittest.mock import patch
from settings.secure_store import encrypt_string, decrypt_string, DPAPIError
from settings.manager import SettingsManager, DiscordDestinationConfig, AppConfig
from discord.auth import generate_pkce_pair
from discord.destination import DiscordDestination
from upload.base import UploadResult, Destination
from discord.uploader import DiscordUploader

class TestSecureStore(unittest.TestCase):
    def test_dpapi_roundtrip(self):
        secret = "https://discord.com/api/webhooks/1234567890/abcdefg_hijklmnop_token"
        encrypted = encrypt_string(secret)
        self.assertNotEqual(secret, encrypted)
        self.assertTrue(len(encrypted) > 0)
        decrypted = decrypt_string(encrypted)
        self.assertEqual(secret, decrypted)

    def test_empty_string(self):
        self.assertEqual(encrypt_string(""), "")
        self.assertEqual(decrypt_string(""), "")

    def test_unicode_string(self):
        text = "Скриншоты и секретный ключ 🔑 123"
        encrypted = encrypt_string(text)
        decrypted = decrypt_string(encrypted)
        self.assertEqual(text, decrypted)

    def test_legacy_unencrypted_base64_migration(self):
        legacy_secret = "https://discord.com/api/webhooks/999/legacy_token"
        legacy_b64 = base64.b64encode(legacy_secret.encode("utf-8")).decode("ascii")
        decrypted = decrypt_string(legacy_b64)
        self.assertEqual(legacy_secret, decrypted)

    def test_encrypt_raises_when_dpapi_fails(self):
        with patch("settings.secure_store._CryptProtectData", return_value=False):
            with self.assertRaises(DPAPIError):
                encrypt_string("my_secret_token")

    def test_encrypt_raises_when_dpapi_unavailable(self):
        with patch("settings.secure_store.DPAPI_AVAILABLE", False):
            with self.assertRaises(DPAPIError):
                encrypt_string("my_secret_token")


class TestSettingsManager(unittest.TestCase):
    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        self.temp_file.close()
        self.config_path = Path(self.temp_file.name)

    def tearDown(self):
        if self.config_path.exists():
            os.remove(self.config_path)

    def test_save_and_load_destination(self):
        mgr = SettingsManager(config_path=self.config_path)
        self.assertFalse(mgr.is_configured())

        dest = DiscordDestinationConfig(
            type="discord",
            guild_id="111",
            guild_name="My Guild",
            channel_id="222",
            channel_name="screenshots",
            webhook_id="333",
            webhook_url="https://discord.com/api/webhooks/333/token444",
            webhook_token="token444",
        )
        mgr.set_destination(dest)
        self.assertTrue(mgr.is_configured())

        # Load in new manager instance from file
        mgr2 = SettingsManager(config_path=self.config_path)
        self.assertTrue(mgr2.is_configured())
        self.assertIsNotNone(mgr2.config.destination)
        self.assertEqual(mgr2.config.destination.guild_name, "My Guild")
        self.assertEqual(mgr2.config.destination.channel_name, "screenshots")
        self.assertEqual(mgr2.config.destination.webhook_url, "https://discord.com/api/webhooks/333/token444")

        # Verify that on disk, the webhook_url is encrypted, not plaintext
        with open(self.config_path, "r", encoding="utf-8") as f:
            disk_content = f.read()
        self.assertNotIn("https://discord.com/api/webhooks/333/token444", disk_content)

    def test_clear_destination(self):
        mgr = SettingsManager(config_path=self.config_path)
        dest = DiscordDestinationConfig(
            type="discord",
            webhook_url="https://discord.com/api/webhooks/333/token444",
        )
        mgr.set_destination(dest)
        self.assertTrue(mgr.is_configured())

        mgr.clear_destination()
        self.assertFalse(mgr.is_configured())
        self.assertIsNone(mgr.config.destination)


class TestPKCE(unittest.TestCase):
    def test_generate_pkce(self):
        verifier, challenge = generate_pkce_pair()
        self.assertTrue(len(verifier) >= 43)
        self.assertTrue(len(challenge) > 20)
        self.assertNotIn("=", challenge)  # Base64url without padding
        self.assertNotIn("+", challenge)
        self.assertNotIn("/", challenge)


class TestHotkeyConversion(unittest.TestCase):
    def test_pynput_combo_conversion(self):
        from app.hotkey import convert_to_pynput_combo
        self.assertEqual(convert_to_pynput_combo("Print Screen"), "<print_screen>")
        self.assertEqual(convert_to_pynput_combo("print_screen"), "<print_screen>")
        self.assertEqual(convert_to_pynput_combo("Ctrl + Shift + S"), "<ctrl>+<shift>+s")
        self.assertEqual(convert_to_pynput_combo("Alt + F10"), "<alt>+<f10>")
class TestLocalStorageDuplication(unittest.TestCase):
    def test_local_storage_persistence(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tf:
            cfg_path = Path(tf.name)
        try:
            mgr = SettingsManager(config_path=cfg_path)
            self.assertFalse(mgr.config.save_local_copy)
            
            mgr.config.save_local_copy = True
            mgr.config.local_copy_dir = "C:/Test/DisShotScreenshots"
            mgr.save()

            mgr2 = SettingsManager(config_path=cfg_path)
            self.assertTrue(mgr2.config.save_local_copy)
            self.assertEqual(mgr2.config.local_copy_dir, "C:/Test/DisShotScreenshots")
        finally:
            if cfg_path.exists():
                os.remove(cfg_path)


if __name__ == "__main__":
    unittest.main()
