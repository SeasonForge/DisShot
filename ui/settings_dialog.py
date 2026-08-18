import logging
from typing import Optional, Callable
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIcon, QColor, QPalette
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QLineEdit,
    QCheckBox,
    QMessageBox,
    QGroupBox,
    QWidget,
    QProgressBar,
)

from config import APP_NAME, APP_VERSION
from settings.manager import SettingsManager, DiscordDestinationConfig
from discord.auth import DiscordAuthFlow
from discord.destination import DiscordDestination
from ui.hotkey_widget import HotkeyRecorderWidget

logger = logging.getLogger(__name__)

MODERN_DARK_STYLESHEET = """
QDialog, QWidget {
    background-color: #1E1F22;
    color: #DBDEE1;
    font-family: "Segoe UI", -apple-system, sans-serif;
    font-size: 13px;
}

QGroupBox {
    border: 1px solid #35363C;
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 14px;
    font-weight: bold;
    color: #F2F3F5;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 4px;
}

QLabel {
    color: #DBDEE1;
}

QLabel#titleLabel {
    font-size: 18px;
    font-weight: bold;
    color: #FFFFFF;
}

QLabel#subtitleLabel {
    font-size: 12px;
    color: #949BA4;
}

QLabel#statusValueLabel {
    font-size: 13px;
    font-weight: 600;
}

QPushButton {
    background-color: #2B2D31;
    color: #FFFFFF;
    border: 1px solid #3F4147;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #35373C;
    border-color: #4E5058;
}

QPushButton:pressed {
    background-color: #1E1F22;
}

QPushButton#primaryButton {
    background-color: #5865F2;
    border: none;
    color: #FFFFFF;
}

QPushButton#primaryButton:hover {
    background-color: #4752C4;
}

QPushButton#primaryButton:pressed {
    background-color: #3C45A5;
}

QPushButton#dangerButton {
    background-color: transparent;
    color: #F23F43;
    border: 1px solid #F23F43;
}

QPushButton#dangerButton:hover {
    background-color: rgba(242, 63, 67, 0.15);
}

QLineEdit {
    background-color: #2B2D31;
    color: #FFFFFF;
    border: 1px solid #3F4147;
    border-radius: 6px;
    padding: 6px 10px;
}

QLineEdit:focus {
    border: 1px solid #5865F2;
}

QCheckBox {
    color: #DBDEE1;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid #4E5058;
    background-color: #2B2D31;
}

QCheckBox::indicator:checked {
    background-color: #5865F2;
    border-color: #5865F2;
}

QProgressBar {
    background-color: #2B2D31;
    border: 1px solid #3F4147;
    border-radius: 4px;
    text-align: center;
    color: #FFFFFF;
}

QProgressBar::chunk {
    background-color: #5865F2;
    border-radius: 3px;
}
"""


class SettingsDialog(QDialog):
    """
    Settings and Discord connection dialog.
    """
    settings_changed = pyqtSignal()
    trigger_capture_requested = pyqtSignal()

    def __init__(self, settings_manager: SettingsManager, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self._auth_flow: Optional[DiscordAuthFlow] = None

        self.setWindowTitle(f"{APP_NAME} — Settings")
        self.setFixedSize(500, 620)
        self.setStyleSheet(MODERN_DARK_STYLESHEET)
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowCloseButtonHint
            | Qt.WindowType.WindowStaysOnTopHint
        )

        self._init_ui()
        self._center_on_screen()
        self._update_destination_ui()

    def _center_on_screen(self):
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.geometry()
            self.move(
                geo.x() + (geo.width() - self.width()) // 2,
                geo.y() + (geo.height() - self.height()) // 2,
            )

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(16)

        # Header
        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)
        title_label = QLabel(APP_NAME)
        title_label.setObjectName("titleLabel")
        subtitle_label = QLabel(f"Version {APP_VERSION} • Instant screenshots to Discord")
        subtitle_label.setObjectName("subtitleLabel")
        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        main_layout.addLayout(header_layout)

        # --- Discord Destination Group ---
        dest_group = QGroupBox("Discord Destination")
        dest_layout = QVBoxLayout(dest_group)
        dest_layout.setSpacing(12)
        dest_layout.setContentsMargins(16, 16, 16, 16)

        # Status row
        status_row = QHBoxLayout()
        status_title = QLabel("Status:")
        status_title.setStyleSheet("color: #949BA4; font-weight: bold;")
        self.status_label = QLabel("Not connected")
        self.status_label.setObjectName("statusValueLabel")
        status_row.addWidget(status_title)
        status_row.addWidget(self.status_label)
        status_row.addStretch()
        dest_layout.addLayout(status_row)

        # Channel info row
        channel_row = QHBoxLayout()
        channel_title = QLabel("Destination:")
        channel_title.setStyleSheet("color: #949BA4; font-weight: bold;")
        self.channel_label = QLabel("None")
        self.channel_label.setStyleSheet("color: #DBDEE1;")
        channel_row.addWidget(channel_title)
        channel_row.addWidget(self.channel_label)
        channel_row.addStretch()
        dest_layout.addLayout(channel_row)

        # Progress bar (hidden by default)
        self.auth_progress = QProgressBar()
        self.auth_progress.setRange(0, 0)  # Indeterminate spinner
        self.auth_progress.setFixedHeight(4)
        self.auth_progress.hide()
        dest_layout.addWidget(self.auth_progress)

        # Permission notice card
        notice_widget = QWidget()
        notice_widget.setStyleSheet("""
            QWidget {
                background-color: #232428;
                border-left: 3px solid #5865F2;
                border-radius: 6px;
                padding: 8px 12px;
            }
            QLabel {
                font-size: 11px;
                color: #B5BAC1;
                line-height: 1.4;
            }
        """)
        notice_layout = QVBoxLayout(notice_widget)
        notice_layout.setContentsMargins(10, 8, 10, 8)
        notice_label = QLabel(
            "<b>💡 Подсказка:</b> выберите Discord-канал, которым вы управляете (где есть права вебхуков). "
            "Либо используйте свой приватный сервер с отдельным каналом для скриншотов."
        )
        notice_label.setWordWrap(True)
        notice_layout.addWidget(notice_label)
        dest_layout.addWidget(notice_widget)

        # Connect / Disconnect Buttons
        btn_row = QHBoxLayout()
        self.connect_btn = QPushButton("Connect Discord")
        self.connect_btn.setObjectName("primaryButton")
        self.connect_btn.clicked.connect(self._start_discord_connect)

        self.cancel_auth_btn = QPushButton("Cancel")
        self.cancel_auth_btn.clicked.connect(self._cancel_discord_connect)
        self.cancel_auth_btn.hide()

        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.setObjectName("dangerButton")
        self.disconnect_btn.clicked.connect(self._disconnect_discord)

        btn_row.addWidget(self.connect_btn)
        btn_row.addWidget(self.cancel_auth_btn)
        btn_row.addWidget(self.disconnect_btn)
        dest_layout.addLayout(btn_row)

        # Direct Webhook field
        wh_row = QHBoxLayout()
        wh_label = QLabel("Webhook URL:")
        wh_label.setStyleSheet("color: #949BA4; font-size: 11px;")
        self.wh_input = QLineEdit()
        self.wh_input.setPlaceholderText("https://discord.com/api/webhooks/...")
        if self.settings_manager.config.destination and self.settings_manager.config.destination.webhook_url:
            self.wh_input.setText(self.settings_manager.config.destination.webhook_url)
        wh_row.addWidget(wh_label)
        wh_row.addWidget(self.wh_input)
        dest_layout.addLayout(wh_row)

        main_layout.addWidget(dest_group)

        # --- Preferences Group ---
        pref_group = QGroupBox("Preferences")
        pref_layout = QVBoxLayout(pref_group)
        pref_layout.setSpacing(12)
        pref_layout.setContentsMargins(16, 16, 16, 16)

        # Hotkey setting
        hotkey_row = QHBoxLayout()
        hotkey_label = QLabel("Hotkey:")
        self.hotkey_widget = HotkeyRecorderWidget(self.settings_manager.config.hotkey)
        hotkey_row.addWidget(hotkey_label)
        hotkey_row.addWidget(self.hotkey_widget, 1)
        pref_layout.addLayout(hotkey_row)

        # Notifications check
        self.notify_check = QCheckBox("Show tray notification after upload")
        self.notify_check.setChecked(self.settings_manager.config.notifications_enabled)
        pref_layout.addWidget(self.notify_check)

        # Sound check
        self.sound_check = QCheckBox("Play sound effect on upload")
        self.sound_check.setChecked(self.settings_manager.config.play_sound)
        pref_layout.addWidget(self.sound_check)

        main_layout.addWidget(pref_group)

        # Action buttons
        bottom_row = QHBoxLayout()
        
        self.test_capture_btn = QPushButton("Take Test Screenshot")
        self.test_capture_btn.clicked.connect(self._on_test_capture)
        bottom_row.addWidget(self.test_capture_btn)

        bottom_row.addStretch()

        save_btn = QPushButton("Save && Close")
        save_btn.setObjectName("primaryButton")
        save_btn.clicked.connect(self._save_and_close)
        bottom_row.addWidget(save_btn)

        main_layout.addLayout(bottom_row)

    def _update_destination_ui(self):
        cfg = self.settings_manager.config
        self.cancel_auth_btn.hide()
        self.connect_btn.show()
        self.connect_btn.setEnabled(True)
        self.auth_progress.hide()
        self.hotkey_widget.set_hotkey(cfg.hotkey)

        if self.settings_manager.is_configured() and cfg.destination:
            self.status_label.setText("● Connected")
            self.status_label.setStyleSheet("color: #23A55A; font-weight: bold;")
            
            dest_text = f"{cfg.destination.guild_name} ({cfg.destination.channel_name})"
            self.channel_label.setText(dest_text)
            
            self.connect_btn.setText("Change Channel")
            self.disconnect_btn.setEnabled(True)
            self.disconnect_btn.show()
        else:
            self.status_label.setText("● Disconnected")
            self.status_label.setStyleSheet("color: #F23F43; font-weight: bold;")
            self.channel_label.setText("None")
            
            self.connect_btn.setText("Connect Discord")
            self.disconnect_btn.setEnabled(False)
            self.disconnect_btn.hide()

    def _start_discord_connect(self):
        client_id = self.settings_manager.config.discord_client_id
        client_secret = self.settings_manager.config.discord_client_secret

        self.connect_btn.hide()
        self.disconnect_btn.hide()
        self.cancel_auth_btn.show()
        self.auth_progress.show()
        self.status_label.setText("Waiting for authorization in browser...")
        self.status_label.setStyleSheet("color: #FEE75C; font-weight: bold;")

        self._auth_flow = DiscordAuthFlow(client_id=client_id, client_secret=client_secret)
        self._auth_flow.finished.connect(self._on_auth_finished)
        self._auth_flow.start_authorization()

    def _cancel_discord_connect(self):
        if self._auth_flow:
            self._auth_flow.cancel()
            self._auth_flow = None
        self._update_destination_ui()

    def _on_auth_finished(self, success: bool, destination: Optional[DiscordDestination], message: str):
        self.auth_progress.hide()
        self.cancel_auth_btn.hide()
        self.connect_btn.show()
        self.connect_btn.setEnabled(True)

        if success and destination:
            dest_cfg = DiscordDestinationConfig(
                type="discord",
                guild_id=destination.guild_id,
                guild_name=destination.guild_name,
                channel_id=destination.channel_id,
                channel_name=destination.channel_name,
                webhook_id=destination.id,
                webhook_url=destination.webhook_url,
                webhook_token=destination.webhook_token,
            )
            self.settings_manager.set_destination(dest_cfg)
            self._update_destination_ui()
            self.settings_changed.emit()
            QMessageBox.information(self, "Discord Connected", "Successfully linked Discord channel!")
        elif "cancelled" in message.lower():
            self._update_destination_ui()
        else:
            self._update_destination_ui()
            QMessageBox.warning(self, "Connection Failed", f"Could not connect to Discord:\n{message}")

    def _disconnect_discord(self):
        reply = QMessageBox.question(
            self,
            "Disconnect Discord",
            "Are you sure you want to disconnect your Discord destination?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.settings_manager.clear_destination()
            self._update_destination_ui()
            self.settings_changed.emit()

    def _on_test_capture(self):
        self.hide()
        self.trigger_capture_requested.emit()

    def _save_and_close(self):
        cfg = self.settings_manager.config
        cfg.hotkey = self.hotkey_widget.get_hotkey()
        cfg.notifications_enabled = self.notify_check.isChecked()
        cfg.play_sound = self.sound_check.isChecked()

        wh_url = self.wh_input.text().strip()
        if wh_url and (wh_url.startswith("https://discord.com/api/webhooks/") or wh_url.startswith("https://canary.discord.com/api/webhooks/")):
            if not cfg.destination or cfg.destination.webhook_url != wh_url:
                cfg.destination = DiscordDestinationConfig(
                    type="discord",
                    guild_name="Custom Webhook",
                    channel_name="webhook",
                    webhook_url=wh_url
                )

        self.settings_manager.save()
        self.settings_changed.emit()
        self.accept()
