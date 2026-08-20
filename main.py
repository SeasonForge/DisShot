import sys
import os
import logging
import ctypes
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from config import APP_NAME
from app.lifecycle import AppLifecycle


def enable_windows_app_id_and_dpi():
    """
    Enables Windows AppUserModelID (for taskbar icon association) and
    Per-Monitor V2 DPI awareness.
    """
    if sys.platform == "win32":
        try:
            # Set explicit AppUserModelID so Windows taskbar displays our custom icon
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("SeasonForge.DisShot.App.1_0")
        except Exception:
            pass

        try:
            # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4
            user32 = ctypes.windll.user32
            user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        except Exception:
            try:
                # PROCESS_PER_MONITOR_DPI_AWARE = 2
                shcore = ctypes.windll.shcore
                shcore.SetProcessDpiAwareness(2)
            except Exception:
                try:
                    ctypes.windll.user32.SetProcessDPIAware()
                except Exception:
                    pass


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
        datefmt="%H:%M:%S",
    )


def main():
    setup_logging()
    logger = logging.getLogger("Main")
    logger.info("Initializing %s...", APP_NAME)

    # 1. Enable Windows App ID & High-DPI awareness
    enable_windows_app_id_and_dpi()

    # 2. Create Qt Application
    qapp = QApplication(sys.argv)
    qapp.setApplicationName(APP_NAME)
    
    # 3. Set global application window icon for taskbar and dialogs
    from app.tray import create_app_icon
    qapp.setWindowIcon(create_app_icon(connected=True))
    
    # 4. Ensure app keeps running in the system tray when windows are closed
    qapp.setQuitOnLastWindowClosed(False)

    # 4. Start lifecycle
    lifecycle = AppLifecycle(qapp)
    lifecycle.start()

    logger.info("%s is running.", APP_NAME)
    sys.exit(qapp.exec())


if __name__ == "__main__":
    main()
