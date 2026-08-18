import io
import logging
from typing import Optional

from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal, QBuffer, QIODevice
from PyQt6.QtGui import (
    QGuiApplication,
    QPainter,
    QColor,
    QPen,
    QBrush,
    QPixmap,
    QCursor,
    QFont,
    QKeySequence,
)
from PyQt6.QtWidgets import QWidget

logger = logging.getLogger(__name__)


class ScreenSniperOverlay(QWidget):
    """
    Full-screen multi-monitor overlay for selecting a region to capture.
    Handles virtual desktop geometry, high DPI scaling, and crosshair rendering.
    """
    captured = pyqtSignal(bytes)   # Emits PNG bytes on successful capture
    cancelled = pyqtSignal()       # Emits when capture is aborted by user

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        # Window flags for smooth overlay
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)

        self._start_pos: Optional[QPoint] = None
        self._current_pos: Optional[QPoint] = None
        self._is_selecting: bool = False
        self._virtual_rect: QRect = QRect()
        self._full_screenshot: Optional[QPixmap] = None

    def start_capture(self) -> None:
        """
        Grabs all screens into a composite virtual desktop pixmap and shows the overlay.
        """
        screens = QGuiApplication.screens()
        if not screens:
            logger.error("No screens detected")
            self.cancelled.emit()
            return

        # Calculate bounding rectangle of all screens (virtual desktop)
        x_min = min(s.geometry().x() for s in screens)
        y_min = min(s.geometry().y() for s in screens)
        x_max = max(s.geometry().x() + s.geometry().width() for s in screens)
        y_max = max(s.geometry().y() + s.geometry().height() for s in screens)

        self._virtual_rect = QRect(x_min, y_min, x_max - x_min, y_max - y_min)

        # Create composite canvas
        composite = QPixmap(self._virtual_rect.size())
        composite.fill(Qt.GlobalColor.black)

        painter = QPainter(composite)
        try:
            for s in screens:
                # Grab each screen and draw into composite at offset
                screen_geom = s.geometry()
                screen_shot = s.grabWindow(0)
                dest_x = screen_geom.x() - x_min
                dest_y = screen_geom.y() - y_min
                painter.drawPixmap(
                    dest_x,
                    dest_y,
                    screen_geom.width(),
                    screen_geom.height(),
                    screen_shot
                )
        finally:
            painter.end()

        self._full_screenshot = composite

        # Position overlay across all monitors
        self.setGeometry(self._virtual_rect)
        self.show()
        self.activateWindow()
        self.raise_()

    def _get_selection_rect(self) -> QRect:
        if not self._start_pos or not self._current_pos:
            return QRect()
        
        top_left_x = min(self._start_pos.x(), self._current_pos.x())
        top_left_y = min(self._start_pos.y(), self._current_pos.y())
        width = abs(self._start_pos.x() - self._current_pos.x())
        height = abs(self._start_pos.y() - self._current_pos.y())
        return QRect(top_left_x, top_left_y, width, height)

    def paintEvent(self, event) -> None:
        if not self._full_screenshot:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        # 1. Draw base screenshot
        painter.drawPixmap(0, 0, self._full_screenshot)

        # 2. Draw semi-transparent dark tint over entire screen
        dim_brush = QBrush(QColor(0, 0, 0, 110))
        painter.fillRect(self.rect(), dim_brush)

        sel_rect = self._get_selection_rect()

        if self._is_selecting and sel_rect.width() > 1 and sel_rect.height() > 1:
            # 3. Draw clear un-dimmed region inside the selection
            painter.drawPixmap(sel_rect, self._full_screenshot, sel_rect)

            # 4. Draw highlight border (Discord Blurple: #5865F2)
            border_pen = QPen(QColor(88, 101, 242), 2, Qt.PenStyle.SolidLine)
            painter.setPen(border_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(sel_rect)

            # 5. Draw size badge (e.g. "800 x 600")
            badge_text = f"{sel_rect.width()} × {sel_rect.height()} px"
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            
            font = QFont("Segoe UI", 9, QFont.Weight.Bold)
            painter.setFont(font)

            badge_w = 110
            badge_h = 24
            badge_x = sel_rect.x() + 5
            badge_y = sel_rect.bottom() + 8
            
            # Keep badge within screen boundary
            if badge_y + badge_h > self.height():
                badge_y = sel_rect.top() - badge_h - 8
            if badge_x + badge_w > self.width():
                badge_x = self.width() - badge_w - 5

            badge_rect = QRect(badge_x, badge_y, badge_w, badge_h)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(30, 31, 34, 220))
            painter.drawRoundedRect(badge_rect, 4, 4)

            painter.setPen(QColor(255, 255, 255))
            painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, badge_text)

        elif self._current_pos:
            # Draw subtle guide crosshairs when moving before click
            guide_pen = QPen(QColor(255, 255, 255, 80), 1, Qt.PenStyle.DashLine)
            painter.setPen(guide_pen)
            painter.drawLine(0, self._current_pos.y(), self.width(), self._current_pos.y())
            painter.drawLine(self._current_pos.x(), 0, self._current_pos.x(), self.height())

        painter.end()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._start_pos = event.pos()
            self._current_pos = event.pos()
            self._is_selecting = True
            self.update()
        elif event.button() == Qt.MouseButton.RightButton:
            # Right click cancels
            self._abort_capture()

    def mouseMoveEvent(self, event) -> None:
        self._current_pos = event.pos()
        self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._is_selecting:
            self._is_selecting = False
            sel_rect = self._get_selection_rect()

            # Ignore tiny accidental clicks (< 4px)
            if sel_rect.width() < 5 or sel_rect.height() < 5:
                self._abort_capture()
                return

            self._finish_capture(sel_rect)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self._abort_capture()
        else:
            super().keyPressEvent(event)

    def _abort_capture(self) -> None:
        logger.info("Screen capture cancelled by user")
        self.close()
        self.cancelled.emit()

    def _finish_capture(self, rect: QRect) -> None:
        if not self._full_screenshot:
            self._abort_capture()
            return

        cropped = self._full_screenshot.copy(rect)
        
        # Convert QPixmap to PNG bytes
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        cropped.save(buffer, "PNG")
        png_bytes = bytes(buffer.data())
        buffer.close()

        logger.info("Captured region %dx%d (%d bytes)", rect.width(), rect.height(), len(png_bytes))
        self.close()
        self.captured.emit(png_bytes)
