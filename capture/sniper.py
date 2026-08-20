import io
import logging
from enum import Enum, auto
from typing import Optional, List

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
    QKeyEvent,
    QMouseEvent,
)
from PyQt6.QtWidgets import QWidget

from capture.annotations import (
    Annotation,
    AnnotationHistory,
    RectangleAnnotation,
    ArrowAnnotation,
    PenAnnotation,
    BlurAnnotation,
)
from ui.annotation_toolbar import AnnotationToolbar
from clipboard.manager import ClipboardManager

logger = logging.getLogger(__name__)


class OverlayState(Enum):
    READY = auto()
    SELECTING = auto()
    EDITING = auto()


class ScreenSniperOverlay(QWidget):
    """
    Full-screen multi-monitor overlay for selecting and annotating screen regions.
    Features:
    - Multi-monitor DPI-aware virtual desktop capture.
    - Seamless in-place annotation toolbar (Rectangle, Arrow, Pen, Blur/Pixelate).
    - Unlimited Undo (Ctrl+Z), Quick Send (Enter), Copy (Ctrl+C), and Cancel (Esc).
    """
    captured = pyqtSignal(bytes)   # Emits PNG bytes on confirmation to upload
    copied_local = pyqtSignal(bytes) # Emits PNG bytes when copied to clipboard locally
    saved_as = pyqtSignal(bytes)   # Emits PNG bytes when Save As file is requested
    cancelled = pyqtSignal()       # Emits when capture is aborted

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)

        self._state: OverlayState = OverlayState.READY
        self._start_pos: Optional[QPoint] = None
        self._current_pos: Optional[QPoint] = None
        self._selected_rect: QRect = QRect()
        self._virtual_rect: QRect = QRect()
        self._full_screenshot: Optional[QPixmap] = None

        # Annotation state
        self._history = AnnotationHistory()
        self._active_annotation: Optional[Annotation] = None
        self._current_tool: str = "rect"
        self._current_color: QColor = QColor("#ED4245")
        self._toolbar: Optional[AnnotationToolbar] = None
        self._is_finished: bool = False

    def start_capture(self) -> None:
        """
        Grabs all screens into a composite virtual desktop pixmap and shows the overlay.
        """
        screens = QGuiApplication.screens()
        if not screens:
            logger.error("No screens detected")
            self.cancelled.emit()
            return

        x_min = min(s.geometry().x() for s in screens)
        y_min = min(s.geometry().y() for s in screens)
        x_max = max(s.geometry().x() + s.geometry().width() for s in screens)
        y_max = max(s.geometry().y() + s.geometry().height() for s in screens)

        self._virtual_rect = QRect(x_min, y_min, x_max - x_min, y_max - y_min)

        # Grab virtual desktop
        composite = QPixmap(self._virtual_rect.size())
        composite.fill(Qt.GlobalColor.black)

        painter = QPainter(composite)
        try:
            for s in screens:
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

    def _init_toolbar(self) -> None:
        if not self._toolbar:
            self._toolbar = AnnotationToolbar(self)
            self._toolbar.tool_changed.connect(self._on_tool_changed)
            self._toolbar.color_changed.connect(self._on_color_changed)
            self._toolbar.undo_requested.connect(self._on_undo)
            self._toolbar.save_requested.connect(self._on_save_as)
            self._toolbar.copy_requested.connect(self._on_copy_local)
            self._toolbar.cancel_requested.connect(self._abort_capture)
            self._toolbar.send_requested.connect(self._on_send)

        self._position_toolbar()
        self._toolbar.show()
        self._toolbar.raise_()

    def _position_toolbar(self) -> None:
        if not self._toolbar or self._selected_rect.isEmpty():
            return

        tb_size = self._toolbar.sizeHint()
        sel = self._selected_rect

        # Position below the selection by default, aligned to bottom-right or center
        margin = 8
        tb_x = sel.right() - tb_size.width()
        tb_y = sel.bottom() + margin

        # If it overflows screen bottom, place it above selection
        if tb_y + tb_size.height() > self.height():
            tb_y = sel.top() - tb_size.height() - margin

        # Clamp horizontal boundaries
        if tb_x < 5:
            tb_x = 5
        if tb_x + tb_size.width() > self.width() - 5:
            tb_x = self.width() - tb_size.width() - 5

        # If it still overflows top boundary (e.g. selection fills entire screen), place inside bottom
        if tb_y < 5:
            tb_y = sel.top() + margin

        self._toolbar.move(tb_x, tb_y)

    def _on_tool_changed(self, tool_name: str) -> None:
        self._current_tool = tool_name

    def _on_color_changed(self, color: QColor) -> None:
        self._current_color = color

    def _on_undo(self) -> None:
        self._history.undo()
        self.update()

    def _on_save_as(self) -> None:
        """Renders the annotated image and emits saved_as signal to prompt file saving."""
        if not self._full_screenshot or self._selected_rect.isEmpty():
            self._abort_capture()
            return

        self._is_finished = True
        final_pixmap = self._history.render_all(self._full_screenshot, self._selected_rect)

        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        final_pixmap.save(buffer, "PNG")
        png_bytes = bytes(buffer.data())
        buffer.close()

        logger.info("Save As requested for annotated screenshot (%d bytes)", len(png_bytes))
        self.close()
        self.saved_as.emit(png_bytes)

    def _on_copy_local(self) -> None:
        """Renders the annotated image and copies PNG/image directly to clipboard."""
        if not self._full_screenshot or self._selected_rect.isEmpty():
            self._abort_capture()
            return

        self._is_finished = True
        final_pixmap = self._history.render_all(self._full_screenshot, self._selected_rect)
        
        # Copy to QClipboard
        from PyQt6.QtGui import QGuiApplication
        cb = QGuiApplication.clipboard()
        if cb:
            cb.setPixmap(final_pixmap)

        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        final_pixmap.save(buffer, "PNG")
        png_bytes = bytes(buffer.data())
        buffer.close()

        logger.info("Copied annotated screenshot directly to clipboard")
        self.close()
        self.copied_local.emit(png_bytes)

    def _on_send(self) -> None:
        """Renders final annotated image and emits captured signal for Discord upload."""
        if not self._full_screenshot or self._selected_rect.isEmpty():
            self._abort_capture()
            return

        self._is_finished = True
        final_pixmap = self._history.render_all(self._full_screenshot, self._selected_rect)

        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        final_pixmap.save(buffer, "PNG")
        png_bytes = bytes(buffer.data())
        buffer.close()

        logger.info("Final image rendered with %d annotations (%d bytes)", self._history.count(), len(png_bytes))
        self.close()
        self.captured.emit(png_bytes)

    def paintEvent(self, event) -> None:
        if not self._full_screenshot:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        # 1. Base full screenshot
        painter.drawPixmap(0, 0, self._full_screenshot)

        # 2. Dimmed overlay mask
        dim_brush = QBrush(QColor(0, 0, 0, 120))
        painter.fillRect(self.rect(), dim_brush)

        active_rect = self._selected_rect if self._state == OverlayState.EDITING else self._get_selection_rect()

        if not active_rect.isEmpty() and active_rect.width() > 1 and active_rect.height() > 1:
            # 3. Clear un-dimmed region
            if self._state == OverlayState.EDITING and not self._history.is_empty():
                # Render baked history inside the crop area
                baked_crop = self._history.render_all(self._full_screenshot, active_rect)
                painter.drawPixmap(active_rect.topLeft(), baked_crop)
            else:
                painter.drawPixmap(active_rect, self._full_screenshot, active_rect)

            # 4. In-progress active annotation preview
            if self._active_annotation:
                painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
                self._active_annotation.render(painter)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

            # 5. Selection border (Discord Blurple: #5865F2)
            border_pen = QPen(QColor(88, 101, 242), 2, Qt.PenStyle.SolidLine)
            painter.setPen(border_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(active_rect)

            # 6. Size badge & Helpful hotkey hints
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            badge_text = f"{active_rect.width()} × {active_rect.height()} px"
            
            font_size = QFont("Segoe UI", 9, QFont.Weight.Bold)
            painter.setFont(font_size)

            badge_w = 110
            badge_h = 24
            badge_x = active_rect.x() + 4
            badge_y = active_rect.top() - badge_h - 6

            # If top overflows, place inside top
            if badge_y < 5:
                badge_y = active_rect.top() + 6
            if badge_x + badge_w > self.width() - 5:
                badge_x = self.width() - badge_w - 5

            badge_rect = QRect(badge_x, badge_y, badge_w, badge_h)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(30, 31, 34, 230))
            painter.drawRoundedRect(badge_rect, 5, 5)

            painter.setPen(QColor(255, 255, 255))
            painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, badge_text)

        elif self._current_pos and self._state == OverlayState.READY:
            # Guide crosshairs
            guide_pen = QPen(QColor(255, 255, 255, 80), 1, Qt.PenStyle.DashLine)
            painter.setPen(guide_pen)
            painter.drawLine(0, self._current_pos.y(), self.width(), self._current_pos.y())
            painter.drawLine(self._current_pos.x(), 0, self._current_pos.x(), self.height())

        painter.end()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.RightButton:
            if self._state == OverlayState.EDITING and not self._history.is_empty():
                self._on_undo()
            elif self._state == OverlayState.EDITING:
                # Clear selection and return to ready
                if self._toolbar:
                    self._toolbar.hide()
                self._state = OverlayState.READY
                self._selected_rect = QRect()
                self.update()
            else:
                self._abort_capture()
            return

        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.pos()

            # Ignore clicks on child toolbar (it handles its own events)
            if self._toolbar and self._toolbar.isVisible() and self._toolbar.geometry().contains(pos):
                return

            if self._state in (OverlayState.READY, OverlayState.SELECTING):
                self._start_pos = pos
                self._current_pos = pos
                self._state = OverlayState.SELECTING
                self.update()

            elif self._state == OverlayState.EDITING:
                if self._selected_rect.contains(pos):
                    # Start drawing an annotation inside selection
                    self._start_pos = pos
                    self._current_pos = pos

                    if self._current_tool == "rect":
                        self._active_annotation = RectangleAnnotation(
                            start=pos,
                            end=pos,
                            color=self._current_color,
                            stroke_width=3
                        )
                    elif self._current_tool == "arrow":
                        self._active_annotation = ArrowAnnotation(
                            start=pos,
                            end=pos,
                            color=self._current_color,
                            stroke_width=3
                        )
                    elif self._current_tool == "pen":
                        self._active_annotation = PenAnnotation(
                            points=[pos],
                            color=self._current_color,
                            stroke_width=3
                        )
                    elif self._current_tool == "blur":
                        self._active_annotation = RectangleAnnotation(
                            start=pos,
                            end=pos,
                            color=QColor(88, 101, 242, 180),
                            stroke_width=1
                        )
                    self.update()
                else:
                    # Clicked outside selection -> start new selection immediately!
                    if self._toolbar:
                        self._toolbar.hide()
                    self._history.clear()
                    self._selected_rect = QRect()
                    self._start_pos = pos
                    self._current_pos = pos
                    self._state = OverlayState.SELECTING
                    self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        self._current_pos = event.pos()

        # Update cursor when hovering over toolbar vs canvas
        if self._toolbar and self._toolbar.isVisible() and self._toolbar.geometry().contains(self._current_pos):
            self.setCursor(Qt.CursorShape.ArrowCursor)
        else:
            self.setCursor(Qt.CursorShape.CrossCursor)

        if self._state == OverlayState.SELECTING:
            self.update()

        elif self._state == OverlayState.EDITING and self._active_annotation:
            pos = event.pos()
            # Constrain drawing inside selected rect
            bounded_pos = QPoint(
                max(self._selected_rect.left(), min(pos.x(), self._selected_rect.right())),
                max(self._selected_rect.top(), min(pos.y(), self._selected_rect.bottom())),
            )

            if isinstance(self._active_annotation, (RectangleAnnotation, ArrowAnnotation)):
                self._active_annotation.end = bounded_pos
            elif isinstance(self._active_annotation, PenAnnotation):
                self._active_annotation.points.append(bounded_pos)

            self.update()
        else:
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return

        if self._state == OverlayState.SELECTING:
            sel_rect = self._get_selection_rect()
            if sel_rect.width() < 6 or sel_rect.height() < 6:
                # User simply clicked without dragging -> stay in READY state (do not abort)
                self._state = OverlayState.READY
                self._start_pos = None
                self._current_pos = None
                self.update()
                return

            self._selected_rect = sel_rect
            self._state = OverlayState.EDITING
            self._start_pos = None
            self._current_pos = None
            self._init_toolbar()
            self.update()

        elif self._state == OverlayState.EDITING and self._active_annotation:
            pos = event.pos()
            bounded_pos = QPoint(
                max(self._selected_rect.left(), min(pos.x(), self._selected_rect.right())),
                max(self._selected_rect.top(), min(pos.y(), self._selected_rect.bottom())),
            )

            if self._current_tool == "blur":
                blur_rect = QRect(
                    min(self._active_annotation.start.x(), bounded_pos.x()),
                    min(self._active_annotation.start.y(), bounded_pos.y()),
                    abs(self._active_annotation.start.x() - bounded_pos.x()),
                    abs(self._active_annotation.start.y() - bounded_pos.y())
                )
                if blur_rect.width() >= 4 and blur_rect.height() >= 4:
                    self._history.add(BlurAnnotation(rect=blur_rect, pixel_block_size=10))
            else:
                if isinstance(self._active_annotation, (RectangleAnnotation, ArrowAnnotation)):
                    self._active_annotation.end = bounded_pos
                self._history.add(self._active_annotation)

            self._active_annotation = None
            self.update()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        # Double-click inside selection sends immediately
        if self._state == OverlayState.EDITING and self._selected_rect.contains(event.pos()):
            self._on_send()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()
        modifiers = event.modifiers()

        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            if self._state == OverlayState.EDITING:
                self._on_send()
        elif key == Qt.Key.Key_Escape:
            self._abort_capture()
        elif modifiers & Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_Z:
            self._on_undo()
        elif modifiers & Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_C:
            self._on_copy_local()
        elif modifiers & Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_S:
            self._on_save_as()
        elif key == Qt.Key.Key_R:
            if self._toolbar:
                self._toolbar.btn_rect.click()
        elif key == Qt.Key.Key_A:
            if self._toolbar:
                self._toolbar.btn_arrow.click()
        elif key == Qt.Key.Key_P:
            if self._toolbar:
                self._toolbar.btn_pen.click()
        elif key == Qt.Key.Key_B:
            if self._toolbar:
                self._toolbar.btn_blur.click()
        else:
            super().keyPressEvent(event)

    def _abort_capture(self) -> None:
        if self._is_finished:
            return
        self._is_finished = True
        logger.info("Screen capture cancelled by user")
        self.close()
        self.cancelled.emit()

    def closeEvent(self, event) -> None:
        if not self._is_finished:
            self._is_finished = True
            self.cancelled.emit()
        super().closeEvent(event)

