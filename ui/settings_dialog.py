import os
import sys
import logging
from pathlib import Path
from typing import Optional
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIcon, QColor, QPixmap
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
    QWidget,
    QProgressBar,
    QFileDialog,
)

from config import APP_NAME, APP_VERSION, DEFAULT_LOCAL_STORAGE_DIR
from settings.manager import SettingsManager, DiscordDestinationConfig
from discord.auth import DiscordAuthFlow
from discord.destination import DiscordDestination
from ui.hotkey_widget import HotkeyRecorderWidget
from ui.toggle_switch import ToggleSwitch
from settings.autostart import is_autostart_enabled, set_autostart_enabled

logger = logging.getLogger(__name__)

MODERN_CARD_STYLESHEET = """
QDialog {
    background-color: #111214;
    color: #DBDEE1;
    font-family: "Segoe UI", -apple-system, sans-serif;
    font-size: 13px;
}

QFrame#cardFrame {
    background-color: #1E1F24;
    border: 1px solid #2B2D33;
    border-radius: 12px;
}

QLabel {
    color: #DBDEE1;
    background-color: transparent;
}

QLabel#cardTitle {
    font-size: 14px;
    font-weight: bold;
    color: #FFFFFF;
}

QLabel#cardSubtitle {
    font-size: 12px;
    color: #949BA4;
}

QLabel#titleLabel {
    font-size: 19px;
    font-weight: bold;
    color: #FFFFFF;
}

QLabel#subtitleLabel {
    font-size: 12px;
    color: #949BA4;
}

QLabel#statusLabel {
    font-size: 13px;
    font-weight: 600;
}

QLabel#channelBadge {
    background-color: #2B2D31;
    border: 1px solid #383A40;
    border-radius: 6px;
    padding: 6px 12px;
    color: #FFFFFF;
    font-weight: 600;
    font-size: 13px;
}

QLabel#channelIdLabel {
    font-size: 11px;
    color: #72767D;
}

QPushButton {
    background-color: #2B2D31;
    color: #DBDEE1;
    border: 1px solid #383A40;
    border-radius: 6px;
    padding: 7px 14px;
    font-weight: 600;
    font-size: 12px;
}

QPushButton:hover {
    background-color: #35373C;
    border-color: #4E5058;
    color: #FFFFFF;
}

QPushButton:pressed {
    background-color: #1E1F22;
}

QPushButton#primaryButton {
    background-color: #5865F2;
    border: 1px solid #5865F2;
    color: #FFFFFF;
    font-weight: bold;
    padding: 8px 18px;
}

QPushButton#primaryButton:hover {
    background-color: #4752C4;
    border-color: #4752C4;
}

QPushButton#dangerButton {
    background-color: transparent;
    color: #F23F43;
    border: 1px solid #F23F43;
}

QPushButton#dangerButton:hover {
    background-color: rgba(242, 63, 67, 0.15);
}

QPushButton#linkButton {
    background: transparent;
    border: none;
    color: #949BA4;
    font-size: 11px;
    text-align: left;
    padding: 0;
}

QPushButton#linkButton:hover {
    color: #5865F2;
}

QLineEdit {
    background-color: #2B2D31;
    color: #FFFFFF;
    border: 1px solid #383A40;
    border-radius: 6px;
    padding: 6px 10px;
}

QLineEdit:focus {
    border-color: #5865F2;
}

QCheckBox {
    color: #DBDEE1;
    background-color: transparent;
    spacing: 10px;
    font-size: 13px;
    min-height: 22px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1px solid #4E5058;
    border-radius: 4px;
    background-color: #2B2D31;
}

QCheckBox::indicator:hover {
    border-color: #5865F2;
}

QCheckBox::indicator:checked {
    background-color: #5865F2;
    border-color: #5865F2;
}
"""

MODERN_DARK_STYLESHEET = MODERN_CARD_STYLESHEET


class SettingsDialog(QDialog):
    """
    Card-based modern configuration dialog for DisShot.
    """
    settings_changed = pyqtSignal()
    trigger_capture_requested = pyqtSignal()

    def __init__(self, settings_manager: SettingsManager, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self._auth_flow: Optional[DiscordAuthFlow] = None

        self.setWindowTitle(f"{APP_NAME} — Настройки")
        self.setFixedSize(560, 680)
        self.setStyleSheet(MODERN_CARD_STYLESHEET)
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowCloseButtonHint
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
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(12)

        # --- Header ---
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        icon_label = QLabel()
        icon_label.setFixedSize(38, 38)
        if Path("icon.ico").exists():
            pix = QPixmap("icon.ico").scaled(38, 38, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            icon_label.setPixmap(pix)
        else:
            icon_label.setText("📷")
            icon_label.setStyleSheet("font-size: 24px;")
        header_layout.addWidget(icon_label)

        titles_layout = QVBoxLayout()
        titles_layout.setSpacing(2)
        title_label = QLabel(APP_NAME)
        title_label.setObjectName("titleLabel")
        subtitle_label = QLabel(f"Версия {APP_VERSION} • Мгновенные скриншоты в Discord")
        subtitle_label.setObjectName("subtitleLabel")
        titles_layout.addWidget(title_label)
        titles_layout.addWidget(subtitle_label)
        header_layout.addLayout(titles_layout)
        header_layout.addStretch()

        main_layout.addLayout(header_layout)

        # --- Card 1: Discord Destination ---
        self.discord_card = QFrame()
        self.discord_card.setObjectName("cardFrame")
        discord_layout = QVBoxLayout(self.discord_card)
        discord_layout.setSpacing(10)
        discord_layout.setContentsMargins(16, 14, 16, 14)

        card1_title = QLabel("💬  Discord")
        card1_title.setObjectName("cardTitle")
        discord_layout.addWidget(card1_title)

        # Status row
        status_row = QHBoxLayout()
        status_tag = QLabel("Статус:")
        status_tag.setStyleSheet("color: #949BA4; font-weight: 600;")
        self.status_label = QLabel("● Не подключено")
        self.status_label.setObjectName("statusLabel")
        status_row.addWidget(status_tag)
        status_row.addWidget(self.status_label)
        status_row.addStretch()
        discord_layout.addLayout(status_row)

        # Channel info row (Channel tag + ID)
        self.channel_info_widget = QWidget()
        channel_info_layout = QHBoxLayout(self.channel_info_widget)
        channel_info_layout.setContentsMargins(0, 0, 0, 0)
        channel_info_layout.setSpacing(8)

        channel_tag = QLabel("Канал:")
        channel_tag.setStyleSheet("color: #949BA4; font-weight: 600;")
        self.channel_badge = QLabel("# screenshooter")
        self.channel_badge.setObjectName("channelBadge")
        self.channel_id_label = QLabel("")
        self.channel_id_label.setObjectName("channelIdLabel")

        channel_info_layout.addWidget(channel_tag)
        channel_info_layout.addWidget(self.channel_badge)
        channel_info_layout.addWidget(self.channel_id_label)
        channel_info_layout.addStretch()
        discord_layout.addWidget(self.channel_info_widget)

        # Action buttons row
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.setSpacing(8)

        self.connect_btn = QPushButton("Подключить Discord")
        self.connect_btn.setObjectName("primaryButton")
        self.connect_btn.clicked.connect(self._start_discord_connect)

        self.disconnect_btn = QPushButton("Отключить")
        self.disconnect_btn.setObjectName("dangerButton")
        self.disconnect_btn.clicked.connect(self._on_disconnect_clicked)

        self.cancel_auth_btn = QPushButton("Отмена")
        self.cancel_auth_btn.clicked.connect(self._cancel_discord_connect)
        self.cancel_auth_btn.hide()

        btn_row.addWidget(self.connect_btn)
        btn_row.addWidget(self.disconnect_btn)
        btn_row.addWidget(self.cancel_auth_btn)
        btn_row.addStretch()
        discord_layout.addLayout(btn_row)

        # Progress bar
        self.auth_progress = QProgressBar()
        self.auth_progress.setRange(0, 0)
        self.auth_progress.setFixedHeight(4)
        self.auth_progress.hide()
        discord_layout.addWidget(self.auth_progress)

        # Tip notice card (shown only when disconnected/authorizing)
        self.notice_card = QWidget()
        self.notice_card.setStyleSheet("""
            QWidget {
                background-color: #26282E;
                border-left: 3px solid #5865F2;
                border-radius: 6px;
            }
        """)
        notice_layout = QHBoxLayout(self.notice_card)
        notice_layout.setContentsMargins(10, 8, 10, 8)
        notice_layout.setSpacing(8)
        tip_text = (
            "💡 <b>Подсказка:</b> выберите Discord-канал, которым вы управляете (где есть права вебхуков). "
            "Либо используйте свой личный сервер с отдельным каналом для скриншотов."
        )
        tip_label = QLabel(tip_text)
        tip_label.setWordWrap(True)
        tip_label.setStyleSheet("color: #DBDEE1; font-size: 11px; line-height: 1.3;")
        notice_layout.addWidget(tip_label)
        discord_layout.addWidget(self.notice_card)

        # Expandable Manual Webhook row
        self.webhook_toggle_btn = QPushButton("⚙️ Дополнительно (ручная вставка Webhook URL) ▾")
        self.webhook_toggle_btn.setObjectName("linkButton")
        self.webhook_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.webhook_toggle_btn.clicked.connect(self._toggle_webhook_input)
        discord_layout.addWidget(self.webhook_toggle_btn)

        self.webhook_container = QWidget()
        wh_layout = QHBoxLayout(self.webhook_container)
        wh_layout.setContentsMargins(0, 0, 0, 0)
        wh_layout.setSpacing(6)
        self.wh_input = QLineEdit()
        self.wh_input.setPlaceholderText("https://discord.com/api/webhooks/...")
        if self.settings_manager.config.destination and self.settings_manager.config.destination.webhook_url:
            self.wh_input.setText(self.settings_manager.config.destination.webhook_url)
        wh_layout.addWidget(self.wh_input)
        self.webhook_container.hide()
        discord_layout.addWidget(self.webhook_container)

        main_layout.addWidget(self.discord_card)

        # --- Card 2: Local Copy ---
        self.local_card = QFrame()
        self.local_card.setObjectName("cardFrame")
        local_layout = QVBoxLayout(self.local_card)
        local_layout.setSpacing(8)
        local_layout.setContentsMargins(16, 14, 16, 14)

        card2_header = QHBoxLayout()
        card2_title = QLabel("📁  Локальная копия")
        card2_title.setObjectName("cardTitle")
        self.local_toggle = ToggleSwitch(self.settings_manager.config.save_local_copy)
        self.local_toggle.toggled.connect(self._on_local_save_toggled)

        card2_header.addWidget(card2_title)
        card2_header.addStretch()
        card2_header.addWidget(self.local_toggle)
        local_layout.addLayout(card2_header)

        card2_subtitle = QLabel("Автоматически сохранять копию каждого скриншота на ваш компьютер.")
        card2_subtitle.setObjectName("cardSubtitle")
        local_layout.addWidget(card2_subtitle)

        # Path & Buttons row
        self.local_dir_widget = QWidget()
        local_dir_layout = QHBoxLayout(self.local_dir_widget)
        local_dir_layout.setContentsMargins(0, 4, 0, 0)
        local_dir_layout.setSpacing(6)

        self.local_dir_input = QLineEdit()
        self.local_dir_input.setText(self.settings_manager.config.local_copy_dir)
        self.local_dir_input.setPlaceholderText("Папка для сохранения...")
        local_dir_layout.addWidget(self.local_dir_input, 1)

        self.browse_dir_btn = QPushButton("Выбрать папку")
        self.browse_dir_btn.clicked.connect(self._on_browse_directory)
        local_dir_layout.addWidget(self.browse_dir_btn)

        self.open_dir_btn = QPushButton("↗ Открыть")
        self.open_dir_btn.setToolTip("Открыть папку в Проводнике Windows")
        self.open_dir_btn.clicked.connect(self._on_open_directory)
        local_dir_layout.addWidget(self.open_dir_btn)

        local_layout.addWidget(self.local_dir_widget)
        self._on_local_save_toggled(self.local_toggle.isChecked())

        main_layout.addWidget(self.local_card)

        # --- Card 3: Behavior ---
        self.behavior_card = QFrame()
        self.behavior_card.setObjectName("cardFrame")
        behavior_layout = QVBoxLayout(self.behavior_card)
        behavior_layout.setSpacing(8)
        behavior_layout.setContentsMargins(16, 14, 16, 14)

        card3_title = QLabel("⚙️  Поведение")
        card3_title.setObjectName("cardTitle")
        behavior_layout.addWidget(card3_title)

        # Hotkey row
        hotkey_row = QHBoxLayout()
        hotkey_label = QLabel("Хоткей:")
        hotkey_label.setStyleSheet("color: #949BA4; font-weight: 600;")
        self.hotkey_widget = HotkeyRecorderWidget(self.settings_manager.config.hotkey)
        hotkey_row.addWidget(hotkey_label)
        hotkey_row.addWidget(self.hotkey_widget, 1)
        behavior_layout.addLayout(hotkey_row)

        # Checkboxes
        self.notify_check = QCheckBox("Уведомление в трее после отправки / копирования")
        self.notify_check.setChecked(self.settings_manager.config.notifications_enabled)
        behavior_layout.addWidget(self.notify_check)

        self.sound_check = QCheckBox("Звуковой сигнал при завершении")
        self.sound_check.setChecked(self.settings_manager.config.play_sound)
        behavior_layout.addWidget(self.sound_check)

        self.autostart_check = QCheckBox("Запускать DisShot вместе с Windows")
        is_auto = is_autostart_enabled() or self.settings_manager.config.start_with_windows
        self.autostart_check.setChecked(is_auto)
        behavior_layout.addWidget(self.autostart_check)

        main_layout.addWidget(self.behavior_card)

        # --- Footer Actions ---
        bottom_row = QHBoxLayout()
        bottom_row.setContentsMargins(0, 4, 0, 0)
        
        self.test_capture_btn = QPushButton("📷  Сделать тестовый снимок")
        self.test_capture_btn.clicked.connect(self._on_test_capture)
        bottom_row.addWidget(self.test_capture_btn)

        bottom_row.addStretch()

        save_btn = QPushButton("✓  Сохранить и закрыть")
        save_btn.setObjectName("primaryButton")
        save_btn.clicked.connect(self._save_and_close)
        bottom_row.addWidget(save_btn)

        main_layout.addLayout(bottom_row)

    def _toggle_webhook_input(self):
        if self.webhook_container.isVisible():
            self.webhook_container.hide()
            self.webhook_toggle_btn.setText("⚙️ Дополнительно (ручная вставка Webhook URL) ▾")
        else:
            self.webhook_container.show()
            self.webhook_toggle_btn.setText("⚙️ Скрыть ручную настройку Webhook ▴")

    def _on_browse_directory(self):
        current_dir = self.local_dir_input.text().strip() or str(Path.home() / "Pictures")
        chosen = QFileDialog.getExistingDirectory(self, "Выберите папку для сохранения скриншотов", current_dir)
        if chosen:
            self.local_dir_input.setText(chosen)

    def _on_open_directory(self):
        current_dir = self.local_dir_input.text().strip() or str(Path.home() / "Pictures" / APP_NAME)
        p = Path(current_dir)
        p.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(str(p))
        except Exception as e:
            logger.warning("Could not open directory %s: %s", current_dir, e)

    def _update_destination_ui(self):
        cfg = self.settings_manager.config
        self.cancel_auth_btn.hide()
        self.connect_btn.show()
        self.connect_btn.setEnabled(True)
        self.auth_progress.hide()
        self.hotkey_widget.set_hotkey(cfg.hotkey)
        self.autostart_check.setChecked(is_autostart_enabled() or cfg.start_with_windows)
        self.local_toggle.setChecked(cfg.save_local_copy)
        self.local_dir_input.setText(cfg.local_copy_dir)
        self._on_local_save_toggled(cfg.save_local_copy)

        if self.settings_manager.is_configured() and cfg.destination:
            self.status_label.setText("● Подключено")
            self.status_label.setStyleSheet("color: #23A55A; font-weight: bold;")
            
            self.channel_badge.setText(f"# {cfg.destination.channel_name or 'канал'}")
            if cfg.destination.channel_id:
                self.channel_id_label.setText(f"(ID: {cfg.destination.channel_id})")
            else:
                self.channel_id_label.setText("")
            self.channel_info_widget.show()

            if cfg.destination.webhook_url:
                self.wh_input.setText(cfg.destination.webhook_url)

            self.connect_btn.setText("Сменить канал")
            self.connect_btn.setObjectName("")  # Normal button style
            self.connect_btn.setStyleSheet("")
            self.disconnect_btn.setEnabled(True)
            self.disconnect_btn.show()
            self.notice_card.hide()  # Clean look when connected
        else:
            self.status_label.setText("● Не подключено")
            self.status_label.setStyleSheet("color: #F23F43; font-weight: bold;")
            self.channel_info_widget.hide()
            self.wh_input.clear()
            
            self.connect_btn.setText("Подключить Discord")
            self.connect_btn.setObjectName("primaryButton")
            self.disconnect_btn.setEnabled(False)
            self.disconnect_btn.hide()
            self.notice_card.show()

    def _on_local_save_toggled(self, checked: bool):
        self.local_dir_widget.setEnabled(checked)
        self.local_dir_input.setEnabled(checked)
        self.browse_dir_btn.setEnabled(checked)
        self.open_dir_btn.setEnabled(checked)

    def _start_discord_connect(self):
        client_id = self.settings_manager.config.discord_client_id
        client_secret = self.settings_manager.config.discord_client_secret

        self.connect_btn.hide()
        self.disconnect_btn.hide()
        self.cancel_auth_btn.show()
        self.auth_progress.show()
        self.notice_card.show()
        self.status_label.setText("Ожидание авторизации...")
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
        self._auth_flow = None
        if success and destination:
            logger.info("OAuth success: %s (#%s)", destination.guild_name, destination.channel_name)
            dest_config = DiscordDestinationConfig(
                type="discord",
                guild_id=destination.guild_id,
                guild_name=destination.guild_name,
                channel_id=destination.channel_id,
                channel_name=destination.channel_name,
                webhook_id=destination.id,
                webhook_url=destination.webhook_url,
                webhook_token=destination.webhook_token,
            )
            self.settings_manager.set_destination(dest_config)
            self.wh_input.setText(destination.webhook_url or "")
            self._update_destination_ui()
            self.settings_changed.emit()
            QMessageBox.information(
                self,
                "Discord подключен!",
                f"Канал #{destination.channel_name} успешно привязан."
            )
        elif "cancelled" in message.lower():
            self._update_destination_ui()
        else:
            self._update_destination_ui()
            QMessageBox.warning(
                self,
                "Ошибка авторизации",
                f"Не удалось подключить Discord:\n{message}"
            )

    def _on_disconnect_clicked(self):
        reply = QMessageBox.question(
            self,
            "Отключение Discord",
            "Вы уверены, что хотите отключить текущий канал Discord?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.settings_manager.clear_destination()
            self.wh_input.clear()
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

        # Update and save autostart with Windows
        auto_enabled = self.autostart_check.isChecked()
        cfg.start_with_windows = auto_enabled
        set_autostart_enabled(auto_enabled)

        # Update and save local storage duplication
        cfg.save_local_copy = self.local_toggle.isChecked()
        cfg.local_copy_dir = self.local_dir_input.text().strip() or DEFAULT_LOCAL_STORAGE_DIR

        wh_url = self.wh_input.text().strip()
        if wh_url and (wh_url.startswith("https://discord.com/api/webhooks/") or wh_url.startswith("https://canary.discord.com/api/webhooks/")):
            if not cfg.destination or cfg.destination.webhook_url != wh_url:
                cfg.destination = DiscordDestinationConfig(
                    type="discord",
                    guild_name="Custom Webhook",
                    channel_name="webhook",
                    webhook_url=wh_url
                )
        elif not wh_url and cfg.destination and cfg.destination.guild_name == "Custom Webhook":
            cfg.destination = None

        self.settings_manager.save()
        self.settings_changed.emit()
        self.accept()
