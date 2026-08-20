import logging
from typing import Optional
from PyQt6.QtCore import QObject, pyqtSignal, QRectF
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush, QPen, QAction
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QWidget

import i18n
from i18n import t
from config import APP_NAME
from settings.manager import SettingsManager

logger = logging.getLogger(__name__)


def create_app_icon(connected: bool = True) -> QIcon:
    """
    Procedurally draws a crisp camera / reticle icon for the system tray.
    """
    size = 64
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(0, 0, 0, 0))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

    # Base rounded rectangle background (Discord Blurple: #5865F2)
    bg_color = QColor(88, 101, 242)
    painter.setBrush(QBrush(bg_color))
    painter.setPen(QPen(QColor(255, 255, 255, 40), 2))
    painter.drawRoundedRect(QRectF(4, 4, 56, 56), 14, 14)

    # Camera lens circle
    painter.setBrush(QBrush(QColor(30, 31, 34)))
    painter.setPen(QPen(QColor(255, 255, 255), 3))
    painter.drawEllipse(QRectF(18, 18, 28, 28))

    # Inner aperture reflection
    painter.setBrush(QBrush(QColor(88, 101, 242)))
    painter.setPen(QPen(QColor(0, 0, 0, 0)))
    painter.drawEllipse(QRectF(26, 26, 12, 12))

    # Small flash dot
    painter.setBrush(QBrush(QColor(255, 255, 255)))
    painter.drawEllipse(QRectF(44, 12, 6, 6))

    # Status indicator dot in bottom-right corner (Green for connected, Red for disconnected)
    status_color = QColor(35, 165, 90) if connected else QColor(242, 63, 67)
    painter.setBrush(QBrush(status_color))
    painter.setPen(QPen(QColor(30, 31, 34), 2))
    painter.drawEllipse(QRectF(42, 42, 16, 16))

    painter.end()
    return QIcon(pixmap)


class TrayManager(QObject):
    """
    Manages the system tray icon and its context menu.
    """
    take_screenshot_requested = pyqtSignal()
    open_settings_requested = pyqtSignal()
    connect_discord_requested = pyqtSignal()
    disconnect_discord_requested = pyqtSignal()
    quit_requested = pyqtSignal()

    def __init__(self, settings_manager: SettingsManager, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.settings_manager = settings_manager

        self.tray_icon = QSystemTrayIcon(self)
        self._update_icon()
        self._build_menu()

        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _update_icon(self) -> None:
        is_connected = self.settings_manager.is_configured()
        icon = create_app_icon(connected=is_connected)
        self.tray_icon.setIcon(icon)
        
        status_str = t("tray_status_connected") if is_connected else t("tray_status_local")
        self.tray_icon.setToolTip(f"{APP_NAME} ({status_str})")

    def _build_menu(self) -> None:
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: #2B2D31;
                color: #DBDEE1;
                border: 1px solid #3F4147;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #5865F2;
                color: #FFFFFF;
            }
            QMenu::separator {
                height: 1px;
                background-color: #3F4147;
                margin: 4px 8px;
            }
        """)

        # Take Screenshot
        take_action = QAction(t("tray_take_screenshot"), menu)
        take_action.triggered.connect(self.take_screenshot_requested.emit)
        menu.addAction(take_action)

        menu.addSeparator()

        # Settings
        settings_action = QAction(t("tray_settings"), menu)
        settings_action.triggered.connect(self.open_settings_requested.emit)
        menu.addAction(settings_action)

        # Connect / Disconnect Discord
        if self.settings_manager.is_configured():
            dest_name = self.settings_manager.config.destination.channel_name if self.settings_manager.config.destination else ""
            disconnect_action = QAction(t("tray_disconnect_discord", channel=dest_name), menu)
            disconnect_action.triggered.connect(self.disconnect_discord_requested.emit)
            menu.addAction(disconnect_action)
        else:
            connect_action = QAction(t("tray_connect_discord"), menu)
            connect_action.triggered.connect(self.connect_discord_requested.emit)
            menu.addAction(connect_action)

        menu.addSeparator()

        # Quit
        quit_action = QAction(t("tray_quit"), menu)
        quit_action.triggered.connect(self.quit_requested.emit)
        menu.addAction(quit_action)

        self.tray_icon.setContextMenu(menu)

    def refresh(self) -> None:
        self._update_icon()
        self._build_menu()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.open_settings_requested.emit()
