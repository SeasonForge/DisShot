import logging
import sys
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRectF, pyqtSlot
from PyQt6.QtGui import (
    QPainter,
    QColor,
    QBrush,
    QPen,
    QFont,
    QPainterPath,
    QGuiApplication,
)
from PyQt6.QtWidgets import (
    QWidget,
    QLabel,
    QHBoxLayout,
    QVBoxLayout,
    QSystemTrayIcon,
    QMessageBox,
)

logger = logging.getLogger(__name__)

try:
    import winsound
    WINSOUND_AVAILABLE = True
except ImportError:
    WINSOUND_AVAILABLE = False


class ModernBlurToast(QWidget):
    """
    Sleek, floating notification toast with clean rounded dark glass card,
    vector status icon badge, and smooth fade in/out animation.
    Visible on top of all windows including fullscreen games and Chrome (F11).
    """
    def __init__(
        self,
        title: str,
        message: str,
        icon_type: str = "success",  # 'success', 'info', 'error'
        duration_ms: int = 2500,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.icon_type = icon_type
        self.duration_ms = duration_ms
        self._is_closing = False

        self.setWindowFlags(
            Qt.WindowType.ToolTip
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        self._init_ui(title, message)
        self._setup_animation()

    def _init_ui(self, title: str, message: str):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 12, 16, 12)
        layout.setSpacing(12)

        # 1. Vector Icon Placeholder
        self.icon_label = QLabel(self)
        self.icon_label.setFixedSize(30, 30)
        self.icon_label.setStyleSheet("background: transparent;")
        layout.addWidget(self.icon_label, 0, Qt.AlignmentFlag.AlignVCenter)

        # 2. Text column (Title + Message)
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        text_layout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel(title, self)
        title_label.setStyleSheet("color: #FFFFFF; font-size: 13px; font-weight: 700; background: transparent;")
        
        msg_label = QLabel(message, self)
        msg_label.setStyleSheet("color: #DBDEE1; font-size: 12px; line-height: 1.3; background: transparent;")
        msg_label.setWordWrap(True)

        text_layout.addWidget(title_label)
        text_layout.addWidget(msg_label)
        layout.addLayout(text_layout, 1)

        # Set sizing and calculate position
        self.adjustSize()
        self.setFixedWidth(max(270, min(self.sizeHint().width() + 16, 360)))
        self._reposition_bottom_right()

    def _reposition_bottom_right(self):
        screen = QGuiApplication.primaryScreen()
        if screen:
            avail_geo = screen.availableGeometry()
            margin_right = 24
            margin_bottom = 24
            x = avail_geo.x() + avail_geo.width() - self.width() - margin_right
            y = avail_geo.y() + avail_geo.height() - self.height() - margin_bottom
            self.move(x, y)

    def _setup_animation(self):
        self.anim = QPropertyAnimation(self, b"windowOpacity")
        self.anim.setDuration(200)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.dismiss_timer = QTimer(self)
        self.dismiss_timer.setSingleShot(True)
        self.dismiss_timer.timeout.connect(self.fade_out)

    def show_animated(self):
        self.setWindowOpacity(0.0)
        self.show()
        self._reposition_bottom_right()

        self.anim.stop()
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.start()

        self.dismiss_timer.start(self.duration_ms)

    def fade_out(self):
        if self._is_closing:
            return
        self._is_closing = True
        self.anim.stop()
        self.anim.setDuration(240)
        self.anim.setStartValue(self.windowOpacity())
        self.anim.setEndValue(0.0)
        self.anim.finished.connect(self.close)
        self.anim.start()

    def enterEvent(self, event):
        # Pause timer on mouse hover
        self.dismiss_timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event):
        # Resume dismiss timer on mouse leave
        if not self._is_closing:
            self.dismiss_timer.start(1200)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        # Click anywhere on toast to dismiss immediately
        self.fade_out()
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # 1. Clean antialiased dark rounded card background (NO gray box)
        card_rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        bg_color = QColor(26, 27, 32, 245)
        border_color = QColor(255, 255, 255, 38)

        painter.setBrush(QBrush(bg_color))
        painter.setPen(QPen(border_color, 1.0))
        painter.drawRoundedRect(card_rect, 10.0, 10.0)

        # 2. Draw crisp vector icon inside icon_label coordinates
        icon_pos = self.icon_label.mapTo(self, self.icon_label.rect().topLeft())
        w = self.icon_label.width()
        h = self.icon_label.height()
        badge_rect = QRectF(icon_pos.x() + 1, icon_pos.y() + 1, w - 2, h - 2)

        if self.icon_type == "success":
            # Green circle with checkmark
            painter.setBrush(QBrush(QColor(35, 165, 90, 45)))
            painter.setPen(QPen(QColor(35, 165, 90), 1.5))
            painter.drawEllipse(badge_rect)

            painter.setPen(QPen(QColor(35, 165, 90), 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            path = QPainterPath()
            path.moveTo(icon_pos.x() + w * 0.30, icon_pos.y() + h * 0.50)
            path.lineTo(icon_pos.x() + w * 0.45, icon_pos.y() + h * 0.66)
            path.lineTo(icon_pos.x() + w * 0.72, icon_pos.y() + h * 0.35)
            painter.drawPath(path)

        elif self.icon_type == "error":
            # Red circle with cross
            painter.setBrush(QBrush(QColor(242, 63, 67, 45)))
            painter.setPen(QPen(QColor(242, 63, 67), 1.5))
            painter.drawEllipse(badge_rect)

            painter.setPen(QPen(QColor(242, 63, 67), 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawLine(int(icon_pos.x() + w * 0.35), int(icon_pos.y() + h * 0.35), int(icon_pos.x() + w * 0.65), int(icon_pos.y() + h * 0.65))
            painter.drawLine(int(icon_pos.x() + w * 0.65), int(icon_pos.y() + h * 0.35), int(icon_pos.x() + w * 0.35), int(icon_pos.y() + h * 0.65))

        else:
            # Blurple circle with info dot
            painter.setBrush(QBrush(QColor(88, 101, 242, 45)))
            painter.setPen(QPen(QColor(88, 101, 242), 1.5))
            painter.drawEllipse(badge_rect)

            painter.setPen(QPen(QColor(88, 101, 242), 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawPoint(int(icon_pos.x() + w * 0.5), int(icon_pos.y() + h * 0.35))
            painter.drawLine(int(icon_pos.x() + w * 0.5), int(icon_pos.y() + h * 0.48), int(icon_pos.x() + w * 0.5), int(icon_pos.y() + h * 0.68))

        painter.end()


class NotificationManager:
    """
    Handles user-facing status notifications with modern floating toasts
    and tray balloons.
    """
    def __init__(self, tray_icon: Optional[QSystemTrayIcon] = None):
        self.tray_icon = tray_icon
        self._active_toast: Optional[ModernBlurToast] = None

    def set_tray_icon(self, tray_icon: QSystemTrayIcon) -> None:
        self.tray_icon = tray_icon

    def play_success_sound(self) -> None:
        if WINSOUND_AVAILABLE:
            try:
                # 1. Standard Windows notification sound
                wav_path = r"C:\Windows\Media\Windows Notify System Generic.wav"
                if Path(wav_path).exists():
                    winsound.PlaySound(wav_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                    return
                winsound.PlaySound("SystemNotification", winsound.SND_ALIAS | winsound.SND_ASYNC)
                return
            except Exception:
                pass
            try:
                winsound.MessageBeep(winsound.MB_OK)
            except Exception:
                pass

    def play_error_sound(self) -> None:
        if WINSOUND_AVAILABLE:
            try:
                wav_path = r"C:\Windows\Media\Windows Foreground.wav"
                if Path(wav_path).exists():
                    winsound.PlaySound(wav_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                    return
                winsound.PlaySound("SystemHand", winsound.SND_ALIAS | winsound.SND_ASYNC)
                return
            except Exception:
                pass
            try:
                winsound.MessageBeep(winsound.MB_ICONHAND)
            except Exception:
                pass

    def show_toast(
        self,
        title: str,
        message: str,
        icon: QSystemTrayIcon.MessageIcon = QSystemTrayIcon.MessageIcon.Information,
        duration_ms: int = 2500,
        icon_type: str = "info"
    ) -> None:
        # Dismiss existing toast cleanly
        if self._active_toast is not None:
            try:
                self._active_toast.close()
            except Exception:
                pass
            self._active_toast = None

        # Display modern on-screen acrylic blur toast
        try:
            self._active_toast = ModernBlurToast(
                title=title,
                message=message,
                icon_type=icon_type,
                duration_ms=duration_ms
            )
            self._active_toast.show_animated()
        except Exception as e:
            logger.warning("Could not show floating blur toast: %s", e)
            # Fallback to system tray balloon if available
            if self.tray_icon and self.tray_icon.isVisible():
                self.tray_icon.showMessage(title, message, icon, duration_ms)

    def notify_upload_success(self, url: str) -> None:
        self.play_success_sound()
        self.show_toast(
            "DisShot — Загружено",
            "Скриншот отправлен в Discord!\nСсылка скопирована в буфер.",
            QSystemTrayIcon.MessageIcon.Information,
            duration_ms=2800,
            icon_type="success"
        )

    def notify_copied_to_clipboard(self) -> None:
        self.play_success_sound()
        self.show_toast(
            "DisShot — Буфер обмена",
            "Скриншот скопирован в буфер обмена.",
            QSystemTrayIcon.MessageIcon.Information,
            duration_ms=2500,
            icon_type="success"
        )

    def notify_saved_locally(self, message: str = "Скриншот скопирован в буфер и сохранён в папку.") -> None:
        self.play_success_sound()
        self.show_toast(
            "DisShot — Сохранено",
            message,
            QSystemTrayIcon.MessageIcon.Information,
            duration_ms=2600,
            icon_type="success"
        )

    def notify_upload_error(self, error_message: str) -> None:
        self.play_error_sound()
        self.show_toast(
            "Ошибка загрузки",
            f"Не удалось загрузить скриншот:\n{error_message}",
            QSystemTrayIcon.MessageIcon.Warning,
            duration_ms=3500,
            icon_type="error"
        )

    def notify_not_configured(self) -> None:
        self.play_error_sound()
        self.show_toast(
            "Discord не подключен",
            "Подключите Discord в настройках для автоматической загрузки.",
            QSystemTrayIcon.MessageIcon.Warning,
            duration_ms=3000,
            icon_type="info"
        )

    def show_error_dialog(self, title: str, message: str, parent: Optional[QWidget] = None) -> None:
        QMessageBox.critical(parent, title, message)

    def show_info_dialog(self, title: str, message: str, parent: Optional[QWidget] = None) -> None:
        QMessageBox.information(parent, title, message)

