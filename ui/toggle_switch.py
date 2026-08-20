from typing import Optional
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPainter, QColor, QBrush
from PyQt6.QtWidgets import QCheckBox, QWidget


class ToggleSwitch(QCheckBox):
    """
    Modern iOS / macOS style toggle switch based on QCheckBox.
    """
    def __init__(self, checked: bool = False, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setChecked(checked)
        self.setFixedSize(46, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setText("")  # No text inside toggle

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        is_on = self.isChecked()

        # Track background
        track_color = QColor("#22C55E") if is_on else QColor("#1E2E4A")
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(track_color))
        painter.drawRoundedRect(QRectF(0, 0, self.width(), self.height()), 12, 12)

        # Thumb (circle)
        thumb_x = self.width() - 21.0 if is_on else 3.0
        thumb_y = 3.0
        thumb_diameter = 18.0

        painter.setBrush(QBrush(QColor("#FFFFFF")))
        painter.drawEllipse(QRectF(thumb_x, thumb_y, thumb_diameter, thumb_diameter))

        painter.end()
