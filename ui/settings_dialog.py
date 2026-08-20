import os
import sys
import logging
import ctypes
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal, QUrl, QByteArray, QRectF
from PyQt6.QtGui import (
    QFont,
    QIcon,
    QColor,
    QPixmap,
    QPainter,
    QPainterPath,
    QPen,
    QBrush,
    QDesktopServices,
)
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QFrame,
    QLineEdit,
    QMessageBox,
    QWidget,
    QProgressBar,
    QFileDialog,
)

import i18n
from i18n import t
from config import APP_NAME, APP_VERSION, DEFAULT_LOCAL_STORAGE_DIR
from settings.manager import SettingsManager, DiscordDestinationConfig
from discord.auth import DiscordAuthFlow
from discord.destination import DiscordDestination
from ui.hotkey_widget import HotkeyRecorderWidget
from ui.toggle_switch import ToggleSwitch
from settings.autostart import is_autostart_enabled, set_autostart_enabled

logger = logging.getLogger(__name__)

# ==========================================
# Pure Vector SVG Definitions
# ==========================================
SVG_GLOBE = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/></svg>"""

SVG_CAMERA = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3z"/><circle cx="12" cy="13" r="3"/></svg>"""

SVG_DISCORD = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="{color}"><path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028 14.09 14.09 0 0 0 1.226-1.994.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.929 1.793 8.18 1.793 12.061 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.893.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.028zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z"/></svg>"""

SVG_FOLDER = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.93a2 2 0 0 1-1.66-.9l-.82-1.2A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13c0 1.1.9 2 2 2Z"/></svg>"""

SVG_KEYBOARD = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="20" height="16" x="2" y="4" rx="2"/><path d="M6 8h.01M10 8h.01M14 8h.01M18 8h.01M6 12h.01M10 12h.01M14 12h.01M18 12h.01M7 16h10"/></svg>"""

SVG_LIGHTNING = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="{color}" stroke="{color}" stroke-width="1" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>"""

SVG_BELL = """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>"""

SVG_VOLUME = """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14"/></svg>"""

SVG_POWER = """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v10"/><path d="M18.4 6.6a9 9 0 1 1-12.77.04"/></svg>"""

SVG_BUILDING = """<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect width="16" height="20" x="4" y="2" rx="2" ry="2"/><path d="M9 22v-4h6v4M8 6h.01M16 6h.01M12 6h.01M12 10h.01M12 14h.01M16 10h.01M16 14h.01M8 10h.01M8 14h.01"/></svg>"""

SVG_HEART = """<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/></svg>"""

SVG_CHECK = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>"""

SVG_CHEVRON_DOWN = """<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>"""


def get_svg_pixmap(svg_template: str, color: str = "#60A5FA", size: int = 20) -> QPixmap:
    """Renders an SVG string into a transparent QPixmap at high DPI."""
    svg_data = svg_template.format(color=color).encode("utf-8")
    renderer = QSvgRenderer(QByteArray(svg_data))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    renderer.render(painter)
    painter.end()
    return pixmap


def get_svg_icon(svg_template: str, color: str = "#60A5FA", size: int = 20) -> QIcon:
    return QIcon(get_svg_pixmap(svg_template, color, size))


class ModernCheckBox(QWidget):
    """
    Sleek custom checkbox widget with smooth border, rounded corners,
    and crisp vector checkmark rendering.
    """
    toggled = pyqtSignal(bool)

    def __init__(self, checked: bool = False, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._checked = checked
        self.setFixedSize(20, 20)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool):
        if self._checked != checked:
            self._checked = checked
            self.update()
            self.toggled.emit(checked)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setChecked(not self._checked)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        rect = QRectF(1.0, 1.0, self.width() - 2.0, self.height() - 2.0)
        if self._checked:
            # Active state: Vibrant Blue #2563EB with soft stroke #3B82F6
            painter.setPen(QPen(QColor("#3B82F6"), 1.2))
            painter.setBrush(QBrush(QColor("#2563EB")))
            painter.drawRoundedRect(rect, 5.0, 5.0)

            # Draw white checkmark
            painter.setPen(QPen(QColor("#FFFFFF"), 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            path = QPainterPath()
            path.moveTo(5.2, 10.0)
            path.lineTo(8.5, 13.5)
            path.lineTo(14.8, 6.2)
            painter.drawPath(path)
        else:
            # Inactive state: Deep navy inset #0A111E with subtle border #1E2D4A
            painter.setPen(QPen(QColor("#1E2D4A"), 1.2))
            painter.setBrush(QBrush(QColor("#0A111E")))
            painter.drawRoundedRect(rect, 5.0, 5.0)

        painter.end()


class BehaviorRowWidget(QWidget):
    """
    Interactive behavior row with leading vector icon, option text,
    and trailing modern checkbox. Clicking anywhere toggles the setting.
    """
    def __init__(self, icon_svg: str, title: str, checked: bool = False, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(30)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(10)

        icon_label = QLabel()
        icon_label.setPixmap(get_svg_pixmap(icon_svg, color="#60A5FA", size=17))
        icon_label.setFixedSize(18, 18)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.text_label = QLabel(title)
        self.text_label.setStyleSheet("color: #CBD5E1; font-size: 12px; font-weight: 500;")

        self.checkbox = ModernCheckBox(checked)

        layout.addWidget(icon_label)
        layout.addWidget(self.text_label, 1)
        layout.addWidget(self.checkbox)

    def setText(self, text: str):
        self.text_label.setText(text)

    def isChecked(self) -> bool:
        return self.checkbox.isChecked()

    def setChecked(self, checked: bool):
        self.checkbox.setChecked(checked)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.checkbox.setChecked(not self.checkbox.isChecked())


MODERN_CARD_STYLESHEET = """
QDialog {
    background-color: #070C16;
    color: #E2E8F0;
    font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, "Roboto", sans-serif;
    font-size: 13px;
}

QFrame.cardFrame {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #121C30, stop:1 #0A1220);
    border: 1px solid #19273F;
    border-radius: 12px;
}

QFrame.cardFrame:hover {
    border-color: #243B60;
}

QLabel {
    color: #CBD5E1;
    background-color: transparent;
}

QLabel#cardTitle {
    font-size: 14px;
    font-weight: 700;
    color: #FFFFFF;
}

QLabel#cardSubtitle {
    font-size: 11px;
    color: #7889A0;
    line-height: 1.3;
}

QLabel#titleLabel {
    font-size: 20px;
    font-weight: 800;
    color: #FFFFFF;
}

QLabel#subtitleLabel {
    font-size: 12px;
    color: #8E9EB5;
}

QLabel#statusLabel {
    font-size: 12px;
    font-weight: 600;
}

QLabel#channelBadge {
    background-color: #09111E;
    border: 1px solid #1A2840;
    border-radius: 8px;
    padding: 5px 12px;
    color: #FFFFFF;
    font-weight: 600;
    font-size: 13px;
}

QLabel#channelIdLabel {
    font-size: 11px;
    color: #64748B;
}

QLabel.iconBadge {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #182640, stop:1 #111C30);
    border: 1px solid #233658;
    border-radius: 9px;
}

QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #152238, stop:1 #101A2C);
    color: #E2E8F0;
    border: 1px solid #203352;
    border-radius: 8px;
    padding: 7px 16px;
    font-weight: 600;
    font-size: 12px;
}

QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1D2E4C, stop:1 #14223A);
    border-color: #3B82F6;
    color: #FFFFFF;
}

QPushButton:pressed {
    background-color: #0A1220;
}

QPushButton#primaryButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #5865F2, stop:1 #4752C4);
    border: 1px solid #5865F2;
    color: #FFFFFF;
    font-weight: bold;
    padding: 8px 18px;
    border-radius: 8px;
}

QPushButton#primaryButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #6775F4, stop:1 #5865F2);
    border-color: #7986F6;
}

QPushButton#saveButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #15803D, stop:1 #22C55E);
    border: 1px solid #22C55E;
    color: #FFFFFF;
    font-weight: bold;
    font-size: 13px;
    padding: 9px 24px;
    border-radius: 8px;
}

QPushButton#saveButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #16A34A, stop:1 #4ADE80);
    border-color: #4ADE80;
}

QPushButton#saveButton:pressed {
    background-color: #14532D;
}

QPushButton#dangerButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1A1F2C, stop:1 #141722);
    color: #EF4444;
    border: 1px solid #372836;
    border-radius: 8px;
}

QPushButton#dangerButton:hover {
    background-color: rgba(239, 68, 68, 0.15);
    border-color: #EF4444;
}

QPushButton#linkButton {
    background: transparent;
    border: none;
    color: #60A5FA;
    font-size: 11px;
    text-align: left;
    padding: 0;
    font-weight: 500;
}

QPushButton#linkButton:hover {
    color: #93C5FD;
    text-decoration: underline;
}

QPushButton#actionButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #142036, stop:1 #0E1728);
    color: #CBD5E1;
    border: 1px solid #1F314F;
    border-radius: 8px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 600;
}

QPushButton#actionButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1B2B47, stop:1 #132138);
    border-color: #38BDF8;
    color: #FFFFFF;
}

QPushButton#langPillBtn {
    background-color: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 14px;
    color: #CBD5E1;
    font-size: 12px;
    font-weight: 700;
    padding: 3px 12px 3px 10px;
}

QPushButton#langPillBtn:hover {
    background-color: rgba(255, 255, 255, 0.10);
    border-color: rgba(255, 255, 255, 0.25);
    color: #FFFFFF;
}

QPushButton#langPillBtn:pressed {
    background-color: rgba(255, 255, 255, 0.15);
}

QLineEdit {
    background-color: #070E1A;
    color: #FFFFFF;
    border: 1px solid #18273F;
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 12px;
}

QLineEdit:focus {
    border-color: #3B82F6;
}
"""

MODERN_DARK_STYLESHEET = MODERN_CARD_STYLESHEET


def apply_windows_dark_titlebar(window: QDialog):
    """Enables Windows 11 immersive dark mode for dialog titlebar."""
    if sys.platform == "win32":
        try:
            hwnd = int(window.winId())
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            set_attribute = ctypes.windll.dwmapi.DwmSetWindowAttribute
            value = ctypes.c_int(1)
            set_attribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(value), ctypes.sizeof(value))
        except Exception:
            pass


class SettingsDialog(QDialog):
    """
    Modern 2-column DisShot configuration dialog with crisp vector SVG icons,
    depth gradients, and aligned interactive controls.
    """
    settings_changed = pyqtSignal()
    trigger_capture_requested = pyqtSignal()

    def __init__(self, settings_manager: SettingsManager, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self._auth_flow: Optional[DiscordAuthFlow] = None

        self.setWindowTitle(f"{APP_NAME} — Настройки")
        self.setFixedSize(830, 580)
        self.setStyleSheet(MODERN_CARD_STYLESHEET)
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowCloseButtonHint
            | Qt.WindowType.WindowMinimizeButtonHint
        )

        self._init_ui()
        self._center_on_screen()
        self._update_destination_ui()
        apply_windows_dark_titlebar(self)

    def _center_on_screen(self):
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.geometry()
            self.move(
                geo.x() + (geo.width() - self.width()) // 2,
                geo.y() + (geo.height() - self.height()) // 2,
            )

    def _create_badge_icon(self, svg_template: str, color: str = "#60A5FA", size: int = 36, icon_size: int = 18) -> QLabel:
        badge = QLabel()
        badge.setProperty("class", "iconBadge")
        badge.setFixedSize(size, size)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setPixmap(get_svg_pixmap(svg_template, color=color, size=icon_size))
        return badge

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 18, 24, 18)
        main_layout.setSpacing(14)

        # ==========================================
        # 1. Header (Logo, Title, Version)
        # ==========================================
        header_layout = QHBoxLayout()
        header_layout.setSpacing(14)

        header_icon = QLabel()
        header_icon.setProperty("class", "iconBadge")
        header_icon.setFixedSize(46, 46)
        header_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if Path("icon.ico").exists():
            pix = QPixmap("icon.ico").scaled(28, 28, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            header_icon.setPixmap(pix)
        else:
            header_icon.setPixmap(get_svg_pixmap(SVG_CAMERA, "#60A5FA", 24))
        header_layout.addWidget(header_icon)

        titles_layout = QVBoxLayout()
        titles_layout.setSpacing(2)
        self.title_label = QLabel(APP_NAME)
        self.title_label.setObjectName("titleLabel")
        self.subtitle_label = QLabel(t("app_subtitle", version=APP_VERSION))
        self.subtitle_label.setObjectName("subtitleLabel")
        titles_layout.addWidget(self.title_label)
        titles_layout.addWidget(self.subtitle_label)
        header_layout.addLayout(titles_layout)
        header_layout.addStretch()

        # Language Capsule Toggle Button (🌐 EN / 🌐 RU)
        self.lang_btn = QPushButton()
        self.lang_btn.setObjectName("langPillBtn")
        self.lang_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lang_btn.setFixedHeight(28)
        self.lang_btn.clicked.connect(self._toggle_language)
        self._update_lang_button()
        header_layout.addWidget(self.lang_btn)

        main_layout.addLayout(header_layout)

        # ==========================================
        # 2. Card 1: Discord Destination
        # ==========================================
        self.discord_card = QFrame()
        self.discord_card.setProperty("class", "cardFrame")
        discord_layout = QVBoxLayout(self.discord_card)
        discord_layout.setSpacing(10)
        discord_layout.setContentsMargins(18, 14, 18, 14)

        discord_top_row = QHBoxLayout()
        discord_top_row.setSpacing(14)

        # Discord blurple badge
        discord_logo = QLabel()
        discord_logo.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #5865F2, stop:1 #4752C4);
            border: 1px solid #6775F4;
            border-radius: 10px;
        """)
        discord_logo.setFixedSize(42, 42)
        discord_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        discord_logo.setPixmap(get_svg_pixmap(SVG_DISCORD, "#FFFFFF", 24))
        discord_top_row.addWidget(discord_logo)

        # Discord info
        discord_info_col = QVBoxLayout()
        discord_info_col.setSpacing(3)

        discord_title_row = QHBoxLayout()
        discord_title_row.setSpacing(8)
        self.discord_title = QLabel(t("card_discord_title"))
        self.discord_title.setObjectName("cardTitle")
        self.status_label = QLabel("● " + t("status_connected"))
        self.status_label.setObjectName("statusLabel")
        discord_title_row.addWidget(self.discord_title)
        discord_title_row.addWidget(self.status_label)
        discord_title_row.addStretch()
        discord_info_col.addLayout(discord_title_row)

        # Channel info row
        self.channel_info_widget = QWidget()
        channel_info_layout = QHBoxLayout(self.channel_info_widget)
        channel_info_layout.setContentsMargins(0, 0, 0, 0)
        channel_info_layout.setSpacing(8)

        self.channel_tag = QLabel(t("channel_prefix"))
        self.channel_tag.setStyleSheet("color: #7889A0; font-weight: 600;")
        self.channel_badge = QLabel("# screenshots")
        self.channel_badge.setObjectName("channelBadge")
        self.channel_id_label = QLabel("(ID: 123491717689622530)")
        self.channel_id_label.setObjectName("channelIdLabel")

        channel_info_layout.addWidget(self.channel_tag)
        channel_info_layout.addWidget(self.channel_badge)
        channel_info_layout.addWidget(self.channel_id_label)
        channel_info_layout.addStretch()
        discord_info_col.addWidget(self.channel_info_widget)

        discord_top_row.addLayout(discord_info_col, 1)

        # Action buttons
        btn_col = QHBoxLayout()
        btn_col.setSpacing(8)

        self.connect_btn = QPushButton(t("btn_change_channel"))
        self.connect_btn.setObjectName("actionButton")
        self.connect_btn.clicked.connect(self._start_discord_connect)

        self.disconnect_btn = QPushButton(t("btn_disconnect"))
        self.disconnect_btn.setObjectName("dangerButton")
        self.disconnect_btn.clicked.connect(self._on_disconnect_clicked)

        self.cancel_auth_btn = QPushButton(t("wizard_btn_cancel"))
        self.cancel_auth_btn.setObjectName("actionButton")
        self.cancel_auth_btn.clicked.connect(self._cancel_discord_connect)
        self.cancel_auth_btn.hide()

        btn_col.addWidget(self.connect_btn)
        btn_col.addWidget(self.disconnect_btn)
        btn_col.addWidget(self.cancel_auth_btn)
        discord_top_row.addLayout(btn_col)

        discord_layout.addLayout(discord_top_row)

        # Progress bar
        self.auth_progress = QProgressBar()
        self.auth_progress.setRange(0, 0)
        self.auth_progress.setFixedHeight(4)
        self.auth_progress.setStyleSheet("""
            QProgressBar {
                background-color: #070E1A;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background-color: #5865F2;
                border-radius: 2px;
            }
        """)
        self.auth_progress.hide()
        discord_layout.addWidget(self.auth_progress)

        # Notice tip (shown when disconnected)
        self.notice_card = QWidget()
        self.notice_card.setStyleSheet("""
            QWidget {
                background-color: #0B1424;
                border-left: 3px solid #5865F2;
                border-radius: 6px;
            }
        """)
        notice_layout = QHBoxLayout(self.notice_card)
        notice_layout.setContentsMargins(12, 6, 12, 6)
        self.tip_label = QLabel(t("toast_not_configured_msg"))
        self.tip_label.setStyleSheet("color: #8E9EB5; font-size: 11px;")
        notice_layout.addWidget(self.tip_label)
        discord_layout.addWidget(self.notice_card)

        # Manual Webhook row
        self.webhook_toggle_btn = QPushButton(t("webhook_advanced_toggle"))
        self.webhook_toggle_btn.setObjectName("linkButton")
        self.webhook_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.webhook_toggle_btn.clicked.connect(self._toggle_webhook_input)
        discord_layout.addWidget(self.webhook_toggle_btn)

        self.webhook_container = QWidget()
        wh_layout = QHBoxLayout(self.webhook_container)
        wh_layout.setContentsMargins(0, 0, 0, 0)
        wh_layout.setSpacing(6)
        self.wh_input = QLineEdit()
        self.wh_input.setPlaceholderText(t("webhook_placeholder"))
        if self.settings_manager.config.destination and self.settings_manager.config.destination.webhook_url:
            self.wh_input.setText(self.settings_manager.config.destination.webhook_url)
        wh_layout.addWidget(self.wh_input)
        self.webhook_container.hide()
        discord_layout.addWidget(self.webhook_container)

        main_layout.addWidget(self.discord_card)

        # ==========================================
        # 3. Middle 2-Column Grid
        # ==========================================
        grid_layout = QGridLayout()
        grid_layout.setSpacing(14)
        grid_layout.setContentsMargins(0, 0, 0, 0)

        # ------------------------------------------
        # 3A. Left Column - Top: Card "Локальная копия"
        # ------------------------------------------
        self.local_card = QFrame()
        self.local_card.setProperty("class", "cardFrame")
        local_layout = QVBoxLayout(self.local_card)
        local_layout.setSpacing(8)
        local_layout.setContentsMargins(16, 14, 16, 14)

        card2_header = QHBoxLayout()
        card2_header.setSpacing(10)
        card2_badge = self._create_badge_icon(SVG_FOLDER, color="#60A5FA", size=36, icon_size=18)
        card2_title_box = QVBoxLayout()
        card2_title_box.setSpacing(1)
        self.card2_title = QLabel(t("card_local_title"))
        self.card2_title.setObjectName("cardTitle")
        self.card2_subtitle = QLabel(t("card_local_desc"))
        self.card2_subtitle.setObjectName("cardSubtitle")
        card2_title_box.addWidget(self.card2_title)
        card2_title_box.addWidget(self.card2_subtitle)

        self.local_toggle = ToggleSwitch(self.settings_manager.config.save_local_copy)
        self.local_toggle.toggled.connect(self._on_local_save_toggled)

        card2_header.addWidget(card2_badge)
        card2_header.addLayout(card2_title_box, 1)
        card2_header.addWidget(self.local_toggle)
        local_layout.addLayout(card2_header)

        # Path input with integrated folder button
        self.local_dir_widget = QWidget()
        local_dir_layout = QVBoxLayout(self.local_dir_widget)
        local_dir_layout.setContentsMargins(0, 4, 0, 0)
        local_dir_layout.setSpacing(8)

        input_row = QHBoxLayout()
        input_row.setSpacing(6)
        self.local_dir_input = QLineEdit()
        self.local_dir_input.setText(self.settings_manager.config.local_copy_dir)
        self.local_dir_input.setPlaceholderText(t("dialog_select_folder"))
        self.folder_icon_btn = QPushButton()
        self.folder_icon_btn.setObjectName("actionButton")
        self.folder_icon_btn.setFixedSize(36, 32)
        self.folder_icon_btn.setIcon(get_svg_icon(SVG_FOLDER, "#94A3B8", 16))
        self.folder_icon_btn.clicked.connect(self._on_browse_directory)
        input_row.addWidget(self.local_dir_input, 1)
        input_row.addWidget(self.folder_icon_btn)
        local_dir_layout.addLayout(input_row)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self.browse_dir_btn = QPushButton(t("btn_select_folder"))
        self.browse_dir_btn.setObjectName("actionButton")
        self.browse_dir_btn.clicked.connect(self._on_browse_directory)
        self.open_dir_btn = QPushButton(f"↗  {t('btn_open_folder')}")
        self.open_dir_btn.setObjectName("actionButton")
        self.open_dir_btn.clicked.connect(self._on_open_directory)
        btn_row.addWidget(self.browse_dir_btn)
        btn_row.addWidget(self.open_dir_btn)
        local_dir_layout.addLayout(btn_row)

        local_layout.addWidget(self.local_dir_widget)
        grid_layout.addWidget(self.local_card, 0, 0)

        # ------------------------------------------
        # 3B. Left Column - Bottom: Card "Хоткей"
        # ------------------------------------------
        self.hotkey_card = QFrame()
        self.hotkey_card.setProperty("class", "cardFrame")
        hotkey_layout = QVBoxLayout(self.hotkey_card)
        hotkey_layout.setSpacing(8)
        hotkey_layout.setContentsMargins(16, 12, 16, 12)

        hotkey_header = QHBoxLayout()
        hotkey_header.setSpacing(10)
        hotkey_badge = self._create_badge_icon(SVG_KEYBOARD, color="#60A5FA", size=36, icon_size=18)
        self.hotkey_title = QLabel(t("card_hotkey_title"))
        self.hotkey_title.setObjectName("cardTitle")
        hotkey_header.addWidget(hotkey_badge)
        hotkey_header.addWidget(self.hotkey_title)
        hotkey_header.addStretch()
        hotkey_layout.addLayout(hotkey_header)

        self.hotkey_widget = HotkeyRecorderWidget(self.settings_manager.config.hotkey)
        hotkey_layout.addWidget(self.hotkey_widget)

        grid_layout.addWidget(self.hotkey_card, 1, 0)

        # ------------------------------------------
        # 3C. Right Column - Top: Card "Поведение"
        # ------------------------------------------
        self.behavior_card = QFrame()
        self.behavior_card.setProperty("class", "cardFrame")
        behavior_layout = QVBoxLayout(self.behavior_card)
        behavior_layout.setSpacing(6)
        behavior_layout.setContentsMargins(16, 14, 16, 14)

        behavior_header = QHBoxLayout()
        behavior_header.setSpacing(10)
        behavior_badge = self._create_badge_icon(SVG_LIGHTNING, color="#60A5FA", size=36, icon_size=18)
        self.behavior_title = QLabel(t("card_behavior_title"))
        self.behavior_title.setObjectName("cardTitle")
        behavior_header.addWidget(behavior_badge)
        behavior_header.addWidget(self.behavior_title)
        behavior_header.addStretch()
        behavior_layout.addLayout(behavior_header)

        # Interactive rows with right-aligned checkboxes
        self.notify_row = BehaviorRowWidget(
            SVG_BELL,
            t("opt_notify_tray"),
            self.settings_manager.config.notifications_enabled,
        )
        behavior_layout.addWidget(self.notify_row)

        self.sound_row = BehaviorRowWidget(
            SVG_VOLUME,
            t("opt_sound_signal"),
            self.settings_manager.config.play_sound,
        )
        behavior_layout.addWidget(self.sound_row)

        is_auto = is_autostart_enabled() or self.settings_manager.config.start_with_windows
        self.autostart_row = BehaviorRowWidget(
            SVG_POWER,
            t("opt_start_windows"),
            is_auto,
        )
        behavior_layout.addWidget(self.autostart_row)

        grid_layout.addWidget(self.behavior_card, 0, 1)

        # ------------------------------------------
        # 3D. Right Column - Bottom: Card "Тестовый снимок"
        # ------------------------------------------
        self.test_card = QFrame()
        self.test_card.setProperty("class", "cardFrame")
        test_layout = QVBoxLayout(self.test_card)
        test_layout.setSpacing(8)
        test_layout.setContentsMargins(16, 12, 16, 12)

        test_header = QHBoxLayout()
        test_header.setSpacing(10)
        test_badge = self._create_badge_icon(SVG_CAMERA, color="#60A5FA", size=36, icon_size=18)
        self.test_title = QLabel(t("card_test_title"))
        self.test_title.setObjectName("cardTitle")
        test_header.addWidget(test_badge)
        test_header.addWidget(self.test_title)
        test_header.addStretch()
        test_layout.addLayout(test_header)

        self.test_capture_btn = QPushButton(f"  {t('btn_make_test_capture')}")
        self.test_capture_btn.setObjectName("actionButton")
        self.test_capture_btn.setIcon(get_svg_icon(SVG_CAMERA, "#94A3B8", 16))
        self.test_capture_btn.setFixedHeight(36)
        self.test_capture_btn.clicked.connect(self._on_test_capture)
        test_layout.addWidget(self.test_capture_btn)

        grid_layout.addWidget(self.test_card, 1, 1)

        main_layout.addLayout(grid_layout)

        # ==========================================
        # 4. Footer (Branding & Save Button)
        # ==========================================
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(0, 4, 0, 0)
        footer_layout.setSpacing(12)

        # Brand building logo
        brand_icon = QLabel()
        brand_icon.setPixmap(get_svg_pixmap(SVG_BUILDING, color="#60A5FA", size=22))
        brand_icon.setFixedSize(24, 24)
        footer_layout.addWidget(brand_icon)

        brand_box = QVBoxLayout()
        brand_box.setSpacing(1)
        brand_title = QLabel("Pupki Industries™")
        brand_title.setStyleSheet("color: #94A3B8; font-weight: 700; font-size: 12px;")
        self.brand_subtitle = QLabel(t("footer_slogan"))
        self.brand_subtitle.setStyleSheet("color: #64748B; font-size: 11px;")

        self.donate_link = QPushButton(f"  {t('footer_donate')}")
        self.donate_link.setObjectName("linkButton")
        self.donate_link.setIcon(get_svg_icon(SVG_HEART, "#60A5FA", 13))
        self.donate_link.setCursor(Qt.CursorShape.PointingHandCursor)
        self.donate_link.clicked.connect(self._open_donation_link)

        brand_box.addWidget(brand_title)
        brand_box.addWidget(self.brand_subtitle)
        brand_box.addWidget(self.donate_link)
        footer_layout.addLayout(brand_box)

        footer_layout.addStretch()

        # Save Button
        self.save_btn = QPushButton(f"  {t('btn_save_and_close')}")
        self.save_btn.setObjectName("saveButton")
        self.save_btn.setIcon(get_svg_icon(SVG_CHECK, "#FFFFFF", 16))
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.clicked.connect(self._save_and_close)
        footer_layout.addWidget(self.save_btn)

        main_layout.addLayout(footer_layout)

    def _update_lang_button(self):
        curr_lang = i18n.get_current_language().upper()
        self.lang_btn.setText(f"  {curr_lang}")
        self.lang_btn.setIcon(get_svg_icon(SVG_GLOBE, "#94A3B8", 15))
        self.lang_btn.setToolTip("Switch language / Сменить язык (RU / EN)")

    def _toggle_language(self):
        new_lang = "en" if i18n.get_current_language() == "ru" else "ru"
        i18n.set_language(new_lang)
        self.settings_manager.config.language = new_lang
        self.settings_manager.save()
        self._update_lang_button()
        self.retranslate_ui()
        self.settings_changed.emit()

    def retranslate_ui(self):
        self.subtitle_label.setText(t("app_subtitle", version=APP_VERSION))
        self.discord_title.setText(t("card_discord_title"))
        self.channel_tag.setText(t("channel_prefix"))
        self.tip_label.setText(t("toast_not_configured_msg"))
        self.webhook_toggle_btn.setText(t("webhook_advanced_toggle"))
        self.wh_input.setPlaceholderText(t("webhook_placeholder"))

        self.card2_title.setText(t("card_local_title"))
        self.card2_subtitle.setText(t("card_local_desc"))
        self.local_dir_input.setPlaceholderText(t("dialog_select_folder"))
        self.browse_dir_btn.setText(t("btn_select_folder"))
        self.open_dir_btn.setText(f"↗  {t('btn_open_folder')}")

        self.hotkey_title.setText(t("card_hotkey_title"))
        self.hotkey_widget.retranslate_ui()

        self.behavior_title.setText(t("card_behavior_title"))
        self.notify_row.setText(t("opt_notify_tray"))
        self.sound_row.setText(t("opt_sound_signal"))
        self.autostart_row.setText(t("opt_start_windows"))

        self.test_title.setText(t("card_test_title"))
        self.test_capture_btn.setText(f"  {t('btn_make_test_capture')}")

        self.brand_subtitle.setText(t("footer_slogan"))
        self.donate_link.setText(f"  {t('footer_donate')}")
        self.save_btn.setText(f"  {t('btn_save_and_close')}")

        self._update_destination_ui()

    def _open_donation_link(self):
        QDesktopServices.openUrl(QUrl("https://boosty.to"))

    def _toggle_webhook_input(self):
        if self.webhook_container.isVisible():
            self.webhook_container.hide()
            self.webhook_toggle_btn.setText(t("webhook_advanced_toggle"))
        else:
            self.webhook_container.show()
            self.webhook_toggle_btn.setText(t("webhook_advanced_toggle").replace("▾", "▴"))

    def _on_browse_directory(self):
        current_dir = self.local_dir_input.text().strip() or str(Path.home() / "Pictures")
        chosen = QFileDialog.getExistingDirectory(self, t("dialog_select_folder"), current_dir)
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
        self.autostart_row.setChecked(is_autostart_enabled() or cfg.start_with_windows)
        self.notify_row.setChecked(cfg.notifications_enabled)
        self.sound_row.setChecked(cfg.play_sound)
        self.local_toggle.setChecked(cfg.save_local_copy)
        self.local_dir_input.setText(cfg.local_copy_dir)
        self._on_local_save_toggled(cfg.save_local_copy)

        if self.settings_manager.is_configured() and cfg.destination:
            self.status_label.setText("● " + t("status_connected"))
            self.status_label.setStyleSheet("color: #22C55E; font-weight: bold; font-size: 12px;")
            
            self.channel_badge.setText(f"# {cfg.destination.channel_name or 'screenshots'}")
            if cfg.destination.channel_id:
                self.channel_id_label.setText(f"(ID: {cfg.destination.channel_id})")
            else:
                self.channel_id_label.setText("")
            self.channel_info_widget.show()

            if cfg.destination.webhook_url:
                self.wh_input.setText(cfg.destination.webhook_url)

            self.connect_btn.setText(t("btn_change_channel"))
            self.connect_btn.setObjectName("actionButton")
            self.disconnect_btn.setText(t("btn_disconnect"))
            self.disconnect_btn.setEnabled(True)
            self.disconnect_btn.show()
            self.notice_card.hide()
        else:
            self.status_label.setText("● " + t("status_disconnected"))
            self.status_label.setStyleSheet("color: #EF4444; font-weight: bold; font-size: 12px;")
            self.channel_info_widget.hide()
            self.wh_input.clear()
            
            self.connect_btn.setText(t("btn_connect_discord"))
            self.connect_btn.setObjectName("primaryButton")
            self.disconnect_btn.setEnabled(False)
            self.disconnect_btn.hide()
            self.notice_card.show()

    def _on_local_save_toggled(self, checked: bool):
        self.local_dir_widget.setEnabled(checked)
        self.local_dir_input.setEnabled(checked)
        self.browse_dir_btn.setEnabled(checked)
        self.open_dir_btn.setEnabled(checked)
        self.folder_icon_btn.setEnabled(checked)

    def _start_discord_connect(self):
        client_id = self.settings_manager.config.discord_client_id
        client_secret = self.settings_manager.config.discord_client_secret

        self.connect_btn.hide()
        self.disconnect_btn.hide()
        self.cancel_auth_btn.show()
        self.auth_progress.show()
        self.notice_card.show()
        self.status_label.setText("Ожидание авторизации...")
        self.status_label.setStyleSheet("color: #FBBF24; font-weight: bold;")

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
        cfg.notifications_enabled = self.notify_row.isChecked()
        cfg.play_sound = self.sound_row.isChecked()

        # Update autostart
        auto_enabled = self.autostart_row.isChecked()
        cfg.start_with_windows = auto_enabled
        set_autostart_enabled(auto_enabled)

        # Update local storage
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
