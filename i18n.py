import locale
import ctypes
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Current active language code ("ru" or "en")
_CURRENT_LANGUAGE = "ru"

TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "ru": {
        # App & Header
        "lang_code": "RU",
        "app_title": "DisShot",
        "app_subtitle": "Версия {version} • Мгновенные скриншоты в Discord",
        
        # Discord Card
        "card_discord_title": "Discord",
        "status_connected": "Подключено",
        "status_disconnected": "Не подключено",
        "status_local": "Локальный режим",
        "channel_prefix": "Канал:",
        "no_channel_selected": "Канал не выбран (выберите в мастере или укажите Webhook)",
        "btn_change_channel": "Сменить канал",
        "btn_connect_discord": "Подключить Discord",
        "btn_disconnect": "Отключить",
        "webhook_advanced_toggle": "Дополнительно (ручная вставка Webhook URL) ▾",
        "webhook_placeholder": "Вставьте Discord Webhook URL (https://discord.com/api/webhooks/...)",
        "btn_apply": "Применить",
        "btn_clear": "Очистить",
        
        # Local Storage Card
        "card_local_title": "Локальная копия",
        "card_local_desc": "Автоматически сохранять копию каждого скрина на ваш компьютер.",
        "btn_select_folder": "Выбрать папку",
        "btn_open_folder": "Открыть папку",
        "dialog_select_folder": "Выберите папку для сохранения скриншотов",
        
        # Hotkey Card
        "card_hotkey_title": "Хоткей",
        "btn_default": "По умолчанию",
        "hotkey_recording": "Нажмите сочетание клавиш...",
        
        # Behavior Card
        "card_behavior_title": "Поведение",
        "opt_notify_tray": "Уведомление в трее после отправки / копирования",
        "opt_sound_signal": "Звуковой сигнал при завершении",
        "opt_start_windows": "Запускать DisShot вместе с Windows",
        
        # Test Capture Card
        "card_test_title": "Тестовый снимок",
        "btn_make_test_capture": "Сделать тестовый снимок",
        
        # Footer
        "footer_brand": "Pupki Industries™",
        "footer_slogan": "Разрабатываем полезные штуки с душой.",
        "footer_donate": "Сказать спасибо (донат)",
        "btn_save_and_close": "Сохранить и закрыть",
        
        # Toasts & Notifications
        "toast_upload_success_title": "DisShot — Загружено",
        "toast_upload_success_msg": "Скриншот отправлен в Discord!\nСсылка скопирована в буфер.",
        "toast_clipboard_title": "DisShot — Буфер обмена",
        "toast_clipboard_msg": "Скриншот скопирован в буфер обмена.",
        "toast_saved_title": "DisShot — Сохранено",
        "toast_saved_msg": "Скриншот скопирован в буфер и сохранён в папку.",
        "toast_error_title": "Ошибка загрузки",
        "toast_error_msg": "Не удалось загрузить скриншот:\n{error}",
        "toast_not_configured_title": "Discord не подключен",
        "toast_not_configured_msg": "Подключите Discord в настройках для автоматической загрузки.",
        
        # Tray Menu
        "tray_take_screenshot": "📸  Сделать снимок",
        "tray_settings": "⚙️  Настройки",
        "tray_disconnect_discord": "🔗  Отключить Discord (#{channel})",
        "tray_connect_discord": "🔗  Подключить Discord",
        "tray_quit": "❌  Выход",
        "tray_status_connected": "Discord подключен",
        "tray_status_local": "Локальный режим",
        
        # Annotation Toolbar & Sniper Hints
        "tool_rect": "Рамка (R)",
        "tool_arrow": "Стрелка (A)",
        "tool_pen": "Карандаш / Маркер (P)",
        "tool_blur": "Размыть / Скрыть (B)",
        "tool_undo": "Отменить действие (Ctrl+Z или ПКМ)",
        "color_tooltip": "Цвет: {name}",
        "color_red": "Красный",
        "color_yellow": "Жёлтый",
        "color_green": "Зелёный",
        "color_blurple": "Blurple",
        "color_white": "Белый",
        "btn_save": "Сохранить",
        "btn_save_tooltip": "Сохранить в файл (Ctrl+S)",
        "btn_copy": "Скопировать",
        "btn_copy_tooltip": "Скопировать в буфер (Ctrl+C)",
        "btn_send": "Отправить",
        "btn_send_tooltip": "Отправить в Discord (Enter или Двойной клик)",
        "btn_cancel_tooltip": "Отмена (Esc)",
        
        # Setup Wizard
        "wizard_title": "Добро пожаловать в {app}",
        "wizard_subtitle": "Быстрые скриншоты прямо в Discord",
        "wizard_step1": "1️⃣  Нажмите <b>Подключить Discord</b> ниже",
        "wizard_step2": "2️⃣  Выберите сервер и канал в браузере",
        "wizard_step3": "3️⃣  Нажмите <b>Print Screen</b> → Выделите область → Готово!",
        "wizard_notice": "<b>💡 Важно:</b> выберите Discord-канал, которым вы управляете (где у вас есть права на отправку файлов/вебхуков).<br><i>Если такого нет — проще всего создать свой приватный сервер с отдельным каналом для скриншотов.</i>",
        "wizard_status_idle": "Нажмите кнопку ниже для привязки канала:",
        "wizard_status_authorizing": "Авторизация в Discord... Проверьте Discord или браузер.",
        "wizard_status_cancelled": "Авторизация отменена. Нажмите кнопку ниже для повтора:",
        "wizard_status_failed": "Не удалось подключиться. Нажмите кнопку ниже для повтора:",
        "wizard_btn_connect": "Подключить Discord",
        "wizard_btn_cancel": "Отменить авторизацию",
        "wizard_webhook_hint": "Или вставьте Discord Webhook URL напрямую:",
        "wizard_webhook_save": "Сохранить",
        "wizard_success_title": "Готово к работе!",
        "wizard_success_msg": "Discord успешно привязан!\n\nНажмите Print Screen в любой момент, чтобы сделать скриншот.",
        "dialog_invalid_url_title": "Некорректный URL",
        "dialog_invalid_url_msg": "Пожалуйста, введите корректный Discord Webhook URL (начинается с https://discord.com/api/webhooks/).",
        "dialog_webhook_linked_title": "Готово к работе!",
        "dialog_webhook_linked_msg": "Discord Webhook успешно привязан!\n\nНажмите Print Screen в любой момент, чтобы сделать скриншот.",
        "dialog_conn_failed_title": "Ошибка подключения",
        "dialog_conn_failed_msg": "Не удалось подключиться к Discord:\n{error}",
    },
    "en": {
        # App & Header
        "lang_code": "EN",
        "app_title": "DisShot",
        "app_subtitle": "Version {version} • Instant Screenshots to Discord",
        
        # Discord Card
        "card_discord_title": "Discord",
        "status_connected": "Connected",
        "status_disconnected": "Disconnected",
        "status_local": "Local Mode",
        "channel_prefix": "Channel:",
        "no_channel_selected": "No channel selected (connect in wizard or specify Webhook)",
        "btn_change_channel": "Change Channel",
        "btn_connect_discord": "Connect Discord",
        "btn_disconnect": "Disconnect",
        "webhook_advanced_toggle": "Advanced (Manual Webhook URL) ▾",
        "webhook_placeholder": "Paste Discord Webhook URL (https://discord.com/api/webhooks/...)",
        "btn_apply": "Apply",
        "btn_clear": "Clear",
        
        # Local Storage Card
        "card_local_title": "Local Copy",
        "card_local_desc": "Automatically save a copy of every screenshot to your PC.",
        "btn_select_folder": "Select Folder",
        "btn_open_folder": "Open Folder",
        "dialog_select_folder": "Select folder to save screenshots",
        
        # Hotkey Card
        "card_hotkey_title": "Hotkey",
        "btn_default": "Default",
        "hotkey_recording": "Press desired key combination...",
        
        # Behavior Card
        "card_behavior_title": "Behavior",
        "opt_notify_tray": "Tray notification after upload / copy",
        "opt_sound_signal": "Sound chime on completion",
        "opt_start_windows": "Launch DisShot on Windows startup",
        
        # Test Capture Card
        "card_test_title": "Test Capture",
        "btn_make_test_capture": "Take Test Screenshot",
        
        # Footer
        "footer_brand": "Pupki Industries™",
        "footer_slogan": "Crafting useful things with soul.",
        "footer_donate": "Say thanks (Donate)",
        "btn_save_and_close": "Save & Close",
        
        # Toasts & Notifications
        "toast_upload_success_title": "DisShot — Uploaded",
        "toast_upload_success_msg": "Screenshot uploaded to Discord!\nLink copied to clipboard.",
        "toast_clipboard_title": "DisShot — Clipboard",
        "toast_clipboard_msg": "Screenshot copied to clipboard.",
        "toast_saved_title": "DisShot — Saved",
        "toast_saved_msg": "Screenshot copied to clipboard and saved to folder.",
        "toast_error_title": "Upload Error",
        "toast_error_msg": "Failed to upload screenshot:\n{error}",
        "toast_not_configured_title": "Discord Not Connected",
        "toast_not_configured_msg": "Connect Discord in settings for automatic uploads.",
        
        # Tray Menu
        "tray_take_screenshot": "📸  Take Screenshot",
        "tray_settings": "⚙️  Settings",
        "tray_disconnect_discord": "🔗  Disconnect Discord (#{channel})",
        "tray_connect_discord": "🔗  Connect Discord",
        "tray_quit": "❌  Quit",
        "tray_status_connected": "Discord Connected",
        "tray_status_local": "Local Mode",
        
        # Annotation Toolbar & Sniper Hints
        "tool_rect": "Rectangle (R)",
        "tool_arrow": "Arrow (A)",
        "tool_pen": "Pen / Marker (P)",
        "tool_blur": "Blur / Pixelate (B)",
        "tool_undo": "Undo action (Ctrl+Z or Right Click)",
        "color_tooltip": "Color: {name}",
        "color_red": "Red",
        "color_yellow": "Yellow",
        "color_green": "Green",
        "color_blurple": "Blurple",
        "color_white": "White",
        "btn_save": "Save",
        "btn_save_tooltip": "Save to file (Ctrl+S)",
        "btn_copy": "Copy",
        "btn_copy_tooltip": "Copy to clipboard (Ctrl+C)",
        "btn_send": "Send",
        "btn_send_tooltip": "Send to Discord (Enter or Double Click)",
        "btn_cancel_tooltip": "Cancel (Esc)",
        
        # Setup Wizard
        "wizard_title": "Welcome to {app}",
        "wizard_subtitle": "Instant screenshots straight to Discord",
        "wizard_step1": "1️⃣  Click <b>Connect Discord</b> below",
        "wizard_step2": "2️⃣  Pick server and channel in your browser",
        "wizard_step3": "3️⃣  Press <b>Print Screen</b> → Select area → Done!",
        "wizard_notice": "<b>💡 Important:</b> select a Discord channel you manage (where you have permission to send files/webhooks).<br><i>If none exists, simply create a private server with a screenshot channel.</i>",
        "wizard_status_idle": "Click the button below to link a channel:",
        "wizard_status_authorizing": "Authorizing with Discord... Check Discord or browser.",
        "wizard_status_cancelled": "Authorization was cancelled. Click below to retry:",
        "wizard_status_failed": "Connection failed. Click below to try again:",
        "wizard_btn_connect": "Connect Discord",
        "wizard_btn_cancel": "Cancel Authorization",
        "wizard_webhook_hint": "Or paste a Discord Webhook URL directly:",
        "wizard_webhook_save": "Save",
        "wizard_success_title": "Ready to use!",
        "wizard_success_msg": "Discord linked successfully!\n\nPress Print Screen anytime to take a screenshot.",
        "dialog_invalid_url_title": "Invalid URL",
        "dialog_invalid_url_msg": "Please enter a valid Discord Webhook URL (starts with https://discord.com/api/webhooks/).",
        "dialog_webhook_linked_title": "Ready to use!",
        "dialog_webhook_linked_msg": "Discord Webhook linked successfully!\n\nPress Print Screen anytime to take a screenshot.",
        "dialog_conn_failed_title": "Connection Failed",
        "dialog_conn_failed_msg": "Could not connect to Discord:\n{error}",
    }
}


def detect_system_language() -> str:
    """
    Detects the primary system language. Returns 'ru' for Russian/Slavic locales, otherwise 'en'.
    """
    try:
        windll = getattr(ctypes, "windll", None)
        if windll:
            lang_id = windll.kernel32.GetUserDefaultUILanguage() & 0x3FF
            # 0x19 = Russian, 0x22 = Ukrainian, 0x23 = Belarusian, 0x3F = Kazakh
            if lang_id in (0x19, 0x22, 0x23, 0x3F):
                return "ru"
    except Exception as e:
        logger.debug("Win32 UI language check failed: %s", e)

    try:
        loc = locale.getdefaultlocale()[0]
        if loc and any(loc.lower().startswith(prefix) for prefix in ("ru", "uk", "be", "kk")):
            return "ru"
    except Exception as e:
        logger.debug("Locale check failed: %s", e)

    return "en"


def init_language(saved_language: str = "system") -> str:
    """
    Initializes the active language from settings or system locale.
    """
    global _CURRENT_LANGUAGE
    if saved_language in ("ru", "en"):
        _CURRENT_LANGUAGE = saved_language
    else:
        _CURRENT_LANGUAGE = detect_system_language()
    return _CURRENT_LANGUAGE


def set_language(lang: str) -> None:
    global _CURRENT_LANGUAGE
    if lang in ("ru", "en"):
        _CURRENT_LANGUAGE = lang
    elif lang == "system":
        _CURRENT_LANGUAGE = detect_system_language()


def get_current_language() -> str:
    return _CURRENT_LANGUAGE


def t(key: str, **kwargs: Any) -> str:
    """
    Translates a key into the currently active language, with optional format arguments.
    Falls back to Russian if missing in English, or key itself if missing.
    """
    lang_dict = TRANSLATIONS.get(_CURRENT_LANGUAGE, TRANSLATIONS["ru"])
    val = lang_dict.get(key)
    if val is None:
        val = TRANSLATIONS["ru"].get(key, key)
    if kwargs:
        try:
            return val.format(**kwargs)
        except Exception:
            return val
    return val
