import os
import unittest
from pathlib import Path
import tempfile

import i18n
from i18n import t, set_language, get_current_language, init_language, TRANSLATIONS, detect_system_language
from settings.manager import SettingsManager


class TestI18n(unittest.TestCase):
    def setUp(self):
        self.orig_lang = get_current_language()

    def tearDown(self):
        set_language(self.orig_lang)

    def test_key_parity_between_languages(self):
        ru_keys = set(TRANSLATIONS["ru"].keys())
        en_keys = set(TRANSLATIONS["en"].keys())
        self.assertEqual(ru_keys, en_keys, f"Mismatch in keys: RU-only: {ru_keys - en_keys}, EN-only: {en_keys - ru_keys}")

    def test_language_switch_and_translation(self):
        set_language("ru")
        self.assertEqual(get_current_language(), "ru")
        self.assertEqual(t("status_connected"), "Подключено")

        set_language("en")
        self.assertEqual(get_current_language(), "en")
        self.assertEqual(t("status_connected"), "Connected")

    def test_translation_formatting(self):
        set_language("ru")
        self.assertIn("1.0.0", t("app_subtitle", version="1.0.0"))
        
        set_language("en")
        self.assertIn("1.0.0", t("app_subtitle", version="1.0.0"))

    def test_detect_system_language(self):
        lang = detect_system_language()
        self.assertIn(lang, ("ru", "en"))

    def test_settings_manager_persists_language(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
            temp_path = Path(f.name)
        
        try:
            mgr = SettingsManager(config_path=temp_path)
            self.assertEqual(mgr.config.language, "system")
            mgr.config.language = "en"
            mgr.save()

            mgr2 = SettingsManager(config_path=temp_path)
            self.assertEqual(mgr2.config.language, "en")
        finally:
            if temp_path.exists():
                os.remove(temp_path)


if __name__ == "__main__":
    unittest.main()
