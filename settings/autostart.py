import sys
import logging
import subprocess
import winreg
from pathlib import Path
from config import APP_NAME

logger = logging.getLogger(__name__)

REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
CREATE_NO_WINDOW = 0x08000000


def _clean_registry():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_SET_VALUE) as key:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
    except Exception:
        pass


def is_autostart_enabled() -> bool:
    """
    Checks whether the application is scheduled in Task Scheduler or registered in Run registry.
    """
    # 1. Check Task Scheduler (required for uac_admin=True apps)
    try:
        res = subprocess.run(
            ["schtasks", "/query", "/tn", APP_NAME],
            capture_output=True,
            creationflags=CREATE_NO_WINDOW,
            text=True,
            errors="replace",
        )
        if res.returncode == 0:
            return True
    except Exception as e:
        logger.warning("Failed to query Task Scheduler: %s", e)

    # 2. Fallback check for legacy registry key
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
    Registers or unregisters the application in Windows Task Scheduler (with HIGHEST privileges
    for UAC compatibility) and cleans up legacy registry keys.
    """
    _clean_registry()

    if enabled:
        if getattr(sys, "frozen", False):
            exe_target = f'"{Path(sys.executable).resolve()}"'
        else:
            python_exe = Path(sys.executable).resolve()
            if python_exe.name.lower() == "python.exe":
                pythonw = python_exe.with_name("pythonw.exe")
                if pythonw.exists():
                    python_exe = pythonw
            main_py = Path(__file__).resolve().parent.parent / "main.py"
            exe_target = f'"{python_exe}" "{main_py}"'

        # Attempt 1: Task Scheduler with HIGHEST privileges (works when running as admin)
        created = False
        try:
            cmd_highest = [
                "schtasks",
                "/create",
                "/tn",
                APP_NAME,
                "/tr",
                exe_target,
                "/sc",
                "ONLOGON",
                "/rl",
                "HIGHEST",
                "/f",
            ]
            res = subprocess.run(
                cmd_highest,
                capture_output=True,
                creationflags=CREATE_NO_WINDOW,
                text=True,
                errors="replace",
            )
            if res.returncode == 0:
                logger.info("Autostart task created (HIGHEST) in Task Scheduler for %s: %s", APP_NAME, exe_target)
                created = True
            else:
                # Attempt 2: Task Scheduler without /rl HIGHEST
                cmd_normal = [
                    "schtasks",
                    "/create",
                    "/tn",
                    APP_NAME,
                    "/tr",
                    exe_target,
                    "/sc",
                    "ONLOGON",
                    "/f",
                ]
                res_normal = subprocess.run(
                    cmd_normal,
                    capture_output=True,
                    creationflags=CREATE_NO_WINDOW,
                    text=True,
                    errors="replace",
                )
                if res_normal.returncode == 0:
                    logger.info("Autostart task created in Task Scheduler for %s: %s", APP_NAME, exe_target)
                    created = True
                else:
                    logger.warning("Failed to create Task Scheduler task: %s", res_normal.stderr)
        except Exception as e:
            logger.error("Exception creating task in Task Scheduler: %s", e)

        if created:
            return True

        # Fallback to registry if Task Scheduler failed
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, exe_target)
                logger.info("Fallback autostart registered in registry: %s", APP_NAME)
                return True
        except Exception as e:
            logger.error("Fallback registry autostart also failed: %s", e)
            return False
    else:
        success = True
        try:
            res = subprocess.run(
                ["schtasks", "/delete", "/tn", APP_NAME, "/f"],
                capture_output=True,
                creationflags=CREATE_NO_WINDOW,
                text=True,
                errors="replace",
            )
            if res.returncode == 0:
                logger.info("Autostart task deleted from Task Scheduler for %s", APP_NAME)
            elif "not find" not in res.stderr.lower() and "не найден" not in res.stderr.lower():
                logger.warning("schtasks delete returned code %s: %s", res.returncode, res.stderr)
        except Exception as e:
            logger.error("Exception deleting task from Task Scheduler: %s", e)
            success = False

        return success

