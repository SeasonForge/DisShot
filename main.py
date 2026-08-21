import sys
import os
import logging
import ctypes
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from PyQt6.QtNetwork import QLocalServer, QLocalSocket

from config import APP_NAME
from app.lifecycle import AppLifecycle

SINGLE_INSTANCE_IPC_NAME = "SeasonForge_DisShot_SingleInstance_IPC"
ERROR_ALREADY_EXISTS = 183
_MUTEX_HANDLE = None


def acquire_single_instance_mutex() -> bool:
    """
    Creates a named Win32 mutex to prevent multiple instances from starting.
    Returns True if this is the primary instance, False if an instance already exists.
    """
    global _MUTEX_HANDLE
    if sys.platform != "win32":
        return True
    try:
        from ctypes import wintypes
        kernel32 = ctypes.windll.kernel32
        kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        _MUTEX_HANDLE = kernel32.CreateMutexW(None, False, "Local\\SeasonForge.DisShot.SingleInstance.Mutex")
        last_error = kernel32.GetLastError()
        if last_error == ERROR_ALREADY_EXISTS:
            return False
        return True
    except Exception as e:
        logging.getLogger("Main").warning("Failed to check single instance mutex: %s", e)
        return True


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

    # 3. Check for existing instance via Win32 Mutex & IPC
    is_primary = acquire_single_instance_mutex()
    ipc_client = QLocalSocket()
    ipc_client.connectToServer(SINGLE_INSTANCE_IPC_NAME)
    if ipc_client.waitForConnected(400) or not is_primary:
        logger.info("Another instance of %s is already running. Activating existing instance...", APP_NAME)
        if ipc_client.state() == QLocalSocket.SocketState.ConnectedState:
            ipc_client.write(b"ACTIVATE\n")
            ipc_client.waitForBytesWritten(500)
            ipc_client.disconnectFromServer()
        sys.exit(0)

    # 4. Set global application window icon for taskbar and dialogs
    from app.tray import create_app_icon
    qapp.setWindowIcon(create_app_icon(connected=True))
    
    # 5. Ensure app keeps running in the system tray when windows are closed
    qapp.setQuitOnLastWindowClosed(False)

    # 6. Start lifecycle
    lifecycle = AppLifecycle(qapp)
    lifecycle.start()

    # 7. Start Single Instance IPC Server
    ipc_server = QLocalServer()
    ipc_server.removeServer(SINGLE_INSTANCE_IPC_NAME)
    if ipc_server.listen(SINGLE_INSTANCE_IPC_NAME):
        def on_new_connection():
            socket = ipc_server.nextPendingConnection()
            if socket:
                socket.waitForReadyRead(400)
                msg = bytes(socket.readAll()).decode("utf-8", errors="ignore").strip()
                if "ACTIVATE" in msg:
                    logger.info("Received activation request from secondary instance.")
                    lifecycle.open_settings()
                socket.disconnectFromServer()
        ipc_server.newConnection.connect(on_new_connection)
    else:
        logger.warning("Failed to start IPC server: %s", ipc_server.errorString())

    logger.info("%s is running.", APP_NAME)
    sys.exit(qapp.exec())


if __name__ == "__main__":
    main()

