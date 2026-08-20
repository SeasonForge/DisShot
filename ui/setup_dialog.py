import logging
from typing import Optional
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QProgressBar,
    QMessageBox,
    QWidget,
)

import i18n
from i18n import t
from config import APP_NAME, APP_VERSION
from settings.manager import SettingsManager, DiscordDestinationConfig
from discord.auth import DiscordAuthFlow
from discord.destination import DiscordDestination
from ui.settings_dialog import MODERN_DARK_STYLESHEET

logger = logging.getLogger(__name__)


class SetupWizardDialog(QDialog):
    """
    First-launch onboarding dialog to connect Discord.
    """
    connected = pyqtSignal()

    def __init__(self, settings_manager: SettingsManager, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self._auth_flow: Optional[DiscordAuthFlow] = None

        self.setWindowTitle(t("wizard_title", app=APP_NAME))
        self.setFixedSize(500, 560)
        self.setStyleSheet(MODERN_DARK_STYLESHEET)
        
        # Ensure it has a taskbar button and stays on top when opened
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowCloseButtonHint
            | Qt.WindowType.WindowStaysOnTopHint
        )

        from app.tray import create_app_icon
        self.setWindowIcon(create_app_icon(connected=False))

        self._init_ui()
        self._center_on_screen()

    def _center_on_screen(self):
        screen = self.screen() or self.parent().screen() if self.parent() else None
        if not screen:
            from PyQt6.QtWidgets import QApplication
            screen = QApplication.primaryScreen()
        if screen:
            geo = screen.geometry()
            self.move(
                geo.x() + (geo.width() - self.width()) // 2,
                geo.y() + (geo.height() - self.height()) // 2,
            )

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(20)

        # Title & Subtitle
        header = QVBoxLayout()
        header.setSpacing(6)
        
        title = QLabel(APP_NAME)
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        subtitle = QLabel(t("wizard_subtitle"))
        subtitle.setObjectName("subtitleLabel")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        header.addWidget(title)
        header.addWidget(subtitle)
        layout.addLayout(header)

        # Steps description card
        steps_widget = QWidget()
        steps_widget.setStyleSheet("""
            QWidget {
                background-color: #2B2D31;
                border-radius: 8px;
                padding: 12px;
            }
            QLabel {
                font-size: 13px;
                color: #DBDEE1;
            }
        """)
        steps_layout = QVBoxLayout(steps_widget)
        steps_layout.setSpacing(10)

        s1 = QLabel(t("wizard_step1"))
        s2 = QLabel(t("wizard_step2"))
        s3 = QLabel(t("wizard_step3"))

        steps_layout.addWidget(s1)
        steps_layout.addWidget(s2)
        steps_layout.addWidget(s3)
        layout.addWidget(steps_widget)

        # Permission notice card
        notice_widget = QWidget()
        notice_widget.setStyleSheet("""
            QWidget {
                background-color: #232428;
                border-left: 3px solid #5865F2;
                border-radius: 6px;
                padding: 8px 10px;
            }
            QLabel {
                font-size: 11px;
                color: #B5BAC1;
                line-height: 1.3;
            }
        """)
        notice_layout = QVBoxLayout(notice_widget)
        notice_layout.setContentsMargins(10, 8, 10, 8)
        notice_layout.setSpacing(4)
        
        notice_label = QLabel(t("wizard_notice"))
        notice_label.setWordWrap(True)
        notice_layout.addWidget(notice_label)
        layout.addWidget(notice_widget)

        # Status text
        self.status_label = QLabel(t("wizard_status_idle"))
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #949BA4; font-size: 12px;")
        layout.addWidget(self.status_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        # Connect button & Cancel button
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(8)

        self.connect_btn = QPushButton(t("wizard_btn_connect"))
        self.connect_btn.setObjectName("primaryButton")
        self.connect_btn.setFixedHeight(40)
        self.connect_btn.clicked.connect(self._start_connect)
        btn_layout.addWidget(self.connect_btn)

        self.cancel_btn = QPushButton(t("wizard_btn_cancel"))
        self.cancel_btn.setFixedHeight(36)
        self.cancel_btn.clicked.connect(self._cancel_connect)
        self.cancel_btn.hide()
        btn_layout.addWidget(self.cancel_btn)

        layout.addLayout(btn_layout)

        # Or Paste Webhook section
        webhook_section = QWidget()
        wh_layout = QVBoxLayout(webhook_section)
        wh_layout.setContentsMargins(0, 8, 0, 0)
        wh_layout.setSpacing(6)

        wh_label = QLabel(t("wizard_webhook_hint"))
        wh_label.setStyleSheet("color: #949BA4; font-size: 11px;")
        wh_layout.addWidget(wh_label)

        wh_row = QHBoxLayout()
        wh_row.setSpacing(6)
        self.wh_input = QLineEdit()
        self.wh_input.setPlaceholderText("https://discord.com/api/webhooks/...")
        self.wh_save_btn = QPushButton(t("wizard_webhook_save"))
        self.wh_save_btn.clicked.connect(self._save_direct_webhook)

        wh_row.addWidget(self.wh_input)
        wh_row.addWidget(self.wh_save_btn)
        wh_layout.addLayout(wh_row)

        layout.addWidget(webhook_section)

    def _save_direct_webhook(self):
        url = self.wh_input.text().strip()
        if not url.startswith("https://discord.com/api/webhooks/") and not url.startswith("https://canary.discord.com/api/webhooks/"):
            QMessageBox.warning(self, t("dialog_invalid_url_title"), t("dialog_invalid_url_msg"))
            return

        dest_cfg = DiscordDestinationConfig(
            type="discord",
            guild_name="Custom Webhook",
            channel_name="webhook",
            webhook_url=url,
        )
        self.settings_manager.set_destination(dest_cfg)
        self.connected.emit()
        QMessageBox.information(
            self,
            t("wizard_success_title"),
            t("dialog_webhook_linked_msg")
        )
    def _start_connect(self):
        client_id = self.settings_manager.config.discord_client_id
        client_secret = self.settings_manager.config.discord_client_secret

        self.connect_btn.hide()
        self.cancel_btn.show()
        self.progress_bar.show()
        self.status_label.setText(t("wizard_status_authorizing"))
        self.status_label.setStyleSheet("color: #FEE75C; font-size: 12px;")

        self._auth_flow = DiscordAuthFlow(client_id=client_id, client_secret=client_secret)
        self._auth_flow.finished.connect(self._on_auth_finished)
        self._auth_flow.start_authorization()

    def _cancel_connect(self):
        if self._auth_flow:
            self._auth_flow.cancel()
            self._auth_flow = None

        self.progress_bar.hide()
        self.cancel_btn.hide()
        self.connect_btn.show()
        self.connect_btn.setEnabled(True)
        self.status_label.setText(t("wizard_status_idle"))
        self.status_label.setStyleSheet("color: #949BA4; font-size: 12px;")

    def _on_auth_finished(self, success: bool, destination: Optional[DiscordDestination], message: str):
        self.progress_bar.hide()
        self.cancel_btn.hide()
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
            self.connected.emit()
            QMessageBox.information(
                self,
                t("wizard_success_title"),
                t("wizard_success_msg")
            )
            self.accept()
        elif "cancelled" in message.lower():
            self.status_label.setText(t("wizard_status_cancelled"))
            self.status_label.setStyleSheet("color: #949BA4; font-size: 12px;")
        else:
            self.status_label.setText(t("wizard_status_failed"))
            self.status_label.setStyleSheet("color: #F23F43; font-size: 12px;")
            QMessageBox.warning(self, t("dialog_conn_failed_title"), t("dialog_conn_failed_msg", error=message))
