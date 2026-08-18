import sys
import logging
import winreg
from pathlib import Path
from config import APP_NAME

logger = logging.getLogger(__name__)

REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def is_autostart_enabled() -> bool:
    """
    Checks whether the application is registered in Windows CurrentUser Run registry.
    """
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_READ) as key:
            val, _ = winreg.QueryValueEx(key, APP_NAME)
            return bool(val)
    except FileNotFoundError:
        return False
    except Exception as e:
        logger.warning("Failed to query autostart registry key: %s", e)
        return False


def set_autostart_enabled(enabled: bool) -> bool:
    """
    Adds or removes the application from Windows CurrentUser Run registry.
    """
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                # If packaged exe, point directly to exe. Otherwise python runner.
                if getattr(sys, "frozen", False):
                    exe_path = f'"{Path(sys.executable).resolve()}"'
                else:
                    main_py = Path(__file__).resolve().parent.parent / "main.py"
                    exe_path = f'"{Path(sys.executable).resolve()}" "{main_py}"'

                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, exe_path)
                logger.info("Autostart enabled in registry: %s -> %s", APP_NAME, exe_path)
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                    logger.info("Autostart disabled in registry for %s", APP_NAME)
                except FileNotFoundError:
                    pass
        return True
    except Exception as e:
        logger.error("Failed to set autostart registry key: %s", e)
        return False
