import math
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
from PyQt6.QtCore import Qt, QRect, QPoint, QPointF
from PyQt6.QtGui import (
    QPainter,
    QColor,
    QPen,
    QBrush,
    QPixmap,
    QImage,
    QPolygonF,
)

logger = logging.getLogger(__name__)


class Annotation(ABC):
    """Abstract base class for all screenshot drawing annotations."""
    @abstractmethod
    def render(self, painter: QPainter) -> None:
        pass


@dataclass
class RectangleAnnotation(Annotation):
    start: QPoint
    end: QPoint
    color: QColor = field(default_factory=lambda: QColor(237, 66, 69))  # Red by default
    stroke_width: int = 3

    def render(self, painter: QPainter) -> None:
        rect = QRect(
            min(self.start.x(), self.end.x()),
            min(self.start.y(), self.end.y()),
            abs(self.start.x() - self.end.x()),
            abs(self.start.y() - self.end.y())
        )
        if rect.width() < 2 or rect.height() < 2:
            return
        
        pen = QPen(self.color, self.stroke_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(rect)


@dataclass
class ArrowAnnotation(Annotation):
    start: QPoint
    end: QPoint
    color: QColor = field(default_factory=lambda: QColor(237, 66, 69))
    stroke_width: int = 3

    def render(self, painter: QPainter) -> None:
        dx = self.end.x() - self.start.x()
        dy = self.end.y() - self.start.y()
        length = math.hypot(dx, dy)
        if length < 5:
            return

        angle = math.atan2(dy, dx)
        head_length = max(14.0, self.stroke_width * 4.0)
        head_angle = math.pi / 6.0  # 30 degrees

        pen = QPen(self.color, self.stroke_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)

        # Draw arrow shaft line
        painter.drawLine(self.start, self.end)

        # Draw arrow head triangle
        p1 = QPointF(float(self.end.x()), float(self.end.y()))
        p2 = QPointF(
            self.end.x() - head_length * math.cos(angle - head_angle),
            self.end.y() - head_length * math.sin(angle - head_angle)
        )
        p3 = QPointF(
            self.end.x() - head_length * math.cos(angle + head_angle),
            self.end.y() - head_length * math.sin(angle + head_angle)
        )

        painter.setBrush(QBrush(self.color))
        painter.drawPolygon(QPolygonF([p1, p2, p3]))


@dataclass
class PenAnnotation(Annotation):
    points: List[QPoint] = field(default_factory=list)
    color: QColor = field(default_factory=lambda: QColor(237, 66, 69))
    stroke_width: int = 3

    def render(self, painter: QPainter) -> None:
        if len(self.points) < 2:
            return

        pen = QPen(self.color, self.stroke_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        for i in range(len(self.points) - 1):
            painter.drawLine(self.points[i], self.points[i + 1])


@dataclass
class BlurAnnotation(Annotation):
    """
    Applies high-speed pixelation effect to hide passwords, tokens, or personal info.
    """
    rect: QRect
    pixel_block_size: int = 10

    def render(self, painter: QPainter) -> None:
        # Note: Blur is applied directly onto the underlying QPixmap/QImage
        pass

    def apply_pixelation(self, image: QImage) -> None:
        norm_rect = self.rect.normalized()
        # Constrain to image boundaries
        target_rect = norm_rect.intersected(image.rect())
        if target_rect.width() < 2 or target_rect.height() < 2:
            return

        block_size = max(4, self.pixel_block_size)
        
        # Sub-image pixelation
        sub_img = image.copy(target_rect)
        small_w = max(1, target_rect.width() // block_size)
        small_h = max(1, target_rect.height() // block_size)

        scaled_down = sub_img.scaled(
            small_w,
            small_h,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.FastTransformation
        )
        pixelated = scaled_down.scaled(
            target_rect.width(),
            target_rect.height(),
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.FastTransformation
        )

        painter = QPainter(image)
        painter.drawImage(target_rect.topLeft(), pixelated)
        painter.end()


class AnnotationHistory:
    """
    Manages annotation actions with full Undo support and composited rendering.
    """
    def __init__(self):
        self._actions: List[Annotation] = []

    def add(self, action: Annotation) -> None:
        self._actions.append(action)

    def undo(self) -> Optional[Annotation]:
        if self._actions:
            return self._actions.pop()
        return None

    def clear(self) -> None:
        self._actions.clear()

    def count(self) -> int:
        return len(self._actions)

    def is_empty(self) -> bool:
        return len(self._actions) == 0

    def render_all(self, base_pixmap: QPixmap, source_rect: QRect) -> QPixmap:
        """
        Takes the cropped base screenshot and bakes all annotations on top of it.
        """
        # Crop region first
        cropped = base_pixmap.copy(source_rect)
        image = cropped.toImage()

        offset_x = source_rect.x()
        offset_y = source_rect.y()

        # 1. Apply pixelation/blur filters first
        for action in self._actions:
            if isinstance(action, BlurAnnotation):
                # Translate rect to cropped local coordinates
                local_rect = QRect(
                    action.rect.x() - offset_x,
                    action.rect.y() - offset_y,
                    action.rect.width(),
                    action.rect.height()
                )
                local_blur = BlurAnnotation(rect=local_rect, pixel_block_size=action.pixel_block_size)
                local_blur.apply_pixelation(image)

        result_pixmap = QPixmap.fromImage(image)

        # 2. Draw vector vector annotations (Pen, Arrow, Rectangle)
        painter = QPainter(result_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        
        # Translate painter to local crop offset
        painter.translate(-offset_x, -offset_y)

        for action in self._actions:
            if not isinstance(action, BlurAnnotation):
                action.render(painter)

        painter.end()
        return result_pixmap
