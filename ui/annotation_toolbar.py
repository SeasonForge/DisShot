import logging
from typing import Optional, Callable
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QRect, QRectF, QPointF
from PyQt6.QtGui import (
    QColor,
    QPainter,
    QBrush,
    QPen,
    QFont,
    QPolygonF,
    QPainterPath,
)
from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QPushButton,
    QFrame,
    QButtonGroup,
)

import i18n
from i18n import t

logger = logging.getLogger(__name__)

TOOLBAR_STYLESHEET = """
QFrame#toolbarContainer {
    background-color: #1E1F22;
    border: 1px solid #383A40;
    border-radius: 10px;
    padding: 3px 6px;
}

QFrame#sectionFrame {
    background-color: #2B2D31;
    border: 1px solid #35373C;
    border-radius: 7px;
    padding: 2px;
}

QPushButton {
    background-color: transparent;
    color: #DBDEE1;
    border: 1px solid transparent;
    border-radius: 5px;
    height: 30px;
    font-size: 12px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #35373C;
    color: #FFFFFF;
}

QPushButton:checked {
    background-color: #5865F2;
    color: #FFFFFF;
    border-color: #5865F2;
}

QPushButton#actionCopy, QPushButton#actionSave {
    background-color: #2B2D31;
    border: 1px solid #383A40;
    color: #DBDEE1;
    padding: 0 12px;
    font-size: 12px;
}

QPushButton#actionCopy:hover, QPushButton#actionSave:hover {
    background-color: #35373C;
    border-color: #4E5058;
    color: #FFFFFF;
}

QPushButton#actionSend {
    background-color: #5865F2;
    border: 1px solid #5865F2;
    color: #FFFFFF;
    padding: 0 14px;
    font-size: 12px;
    font-weight: bold;
}

QPushButton#actionSend:hover {
    background-color: #4752C4;
    border-color: #4752C4;
}

QPushButton#actionCancel {
    color: #949BA4;
    width: 28px;
    padding: 0;
    font-size: 14px;
}

QPushButton#actionCancel:hover {
    background-color: rgba(242, 63, 67, 0.2);
    color: #F23F43;
    border-color: #F23F43;
}

QFrame#separator {
    background-color: #383A40;
    width: 1px;
    max-width: 1px;
    margin: 4px 4px;
}
"""

def get_available_colors():
    return [
        ("#ED4245", t("color_red")),
        ("#FEE75C", t("color_yellow")),
        ("#23A55A", t("color_green")),
        ("#5865F2", t("color_blurple")),
        ("#FFFFFF", t("color_white")),
    ]


class VectorToolButton(QPushButton):
    """
    Crisp, anti-aliased vector icon button for annotation tools.
    """
    def __init__(self, icon_type: str, tooltip: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.icon_type = icon_type  # 'rect', 'arrow', 'pen', 'blur', 'undo'
        self.setToolTip(tooltip)
        self.setFixedSize(30, 30)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self, event):
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        icon_color = QColor("#FFFFFF") if self.isChecked() else (
            QColor("#FFFFFF") if self.underMouse() else QColor("#B5BAC1")
        )

        w = self.width()
        h = self.height()
        cx = w / 2.0
        cy = h / 2.0

        if self.icon_type == "rect":
            pen = QPen(icon_color, 2)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(QRectF(cx - 6.5, cy - 6.5, 13.0, 13.0), 2.0, 2.0)

        elif self.icon_type == "arrow":
            pen = QPen(icon_color, 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            # Shaft from bottom-left to top-right
            p_start = QPointF(cx - 6.0, cy + 6.0)
            p_end = QPointF(cx + 6.0, cy - 6.0)
            painter.drawLine(p_start, p_end)
            # Arrow head
            painter.drawLine(p_end, QPointF(cx + 1.0, cy - 6.0))
            painter.drawLine(p_end, QPointF(cx + 6.0, cy - 1.0))

        elif self.icon_type == "pen":
            pen = QPen(icon_color, 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            # Diagonal pen body
            painter.drawLine(QPointF(cx - 5.5, cy + 5.5), QPointF(cx + 4.5, cy - 4.5))
            painter.drawLine(QPointF(cx - 6.0, cy + 6.0), QPointF(cx - 4.0, cy + 6.0))
            painter.drawLine(QPointF(cx + 3.0, cy - 6.0), QPointF(cx + 6.0, cy - 3.0))

        elif self.icon_type == "blur":
            # 2x2 checkered mosaic block
            painter.setPen(Qt.PenStyle.NoPen)
            sz = 6.0
            # Top-left & bottom-right filled
            painter.setBrush(QBrush(icon_color))
            painter.drawRect(QRectF(cx - sz, cy - sz, sz, sz))
            painter.drawRect(QRectF(cx, cy, sz, sz))
            # Other 2 outlined
            pen = QPen(icon_color, 1)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(QRectF(cx, cy - sz, sz - 1, sz - 1))
            painter.drawRect(QRectF(cx - sz, cy, sz - 1, sz - 1))

        elif self.icon_type == "undo":
            pen = QPen(icon_color, 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            
            # Curved back arrow path
            path = QPainterPath()
            path.moveTo(cx + 5.0, cy + 4.0)
            path.arcTo(QRectF(cx - 4.0, cy - 5.0, 10.0, 10.0), 0, 180)
            painter.drawPath(path)
            
            # Arrowhead pointing down-left
            painter.drawLine(QPointF(cx - 4.0, cy), QPointF(cx - 7.0, cy - 2.0))
            painter.drawLine(QPointF(cx - 4.0, cy), QPointF(cx - 4.0, cy - 6.0))

        painter.end()


class ColorButton(QPushButton):
    """Circular modern color picker button with smooth hover ring."""
    def __init__(self, hex_color: str, name: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.hex_color = hex_color
        self.setCheckable(True)
        self.setToolTip(t("color_tooltip", name=name))
        self.setFixedSize(22, 22)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        color = QColor(self.hex_color)
        painter.setBrush(QBrush(color))
        
        if self.isChecked():
            # Active indicator with outer white glow ring
            painter.setPen(QPen(QColor(255, 255, 255), 2))
            painter.drawEllipse(2, 2, 18, 18)
        else:
            painter.setPen(QPen(QColor(70, 70, 75), 1))
            painter.drawEllipse(3, 3, 16, 16)
        
        painter.end()


class AnnotationToolbar(QWidget):
    """
    CleanShot / macOS style floating toolbar for screenshot annotations.
    """
    tool_changed = pyqtSignal(str)          # 'rect', 'arrow', 'pen', 'blur'
    color_changed = pyqtSignal(QColor)
    undo_requested = pyqtSignal()
    save_requested = pyqtSignal()
    copy_requested = pyqtSignal()
    send_requested = pyqtSignal()
    cancel_requested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.current_tool = "rect"
        self.current_color = QColor("#ED4245")

        self.setStyleSheet(TOOLBAR_STYLESHEET)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setCursor(Qt.CursorShape.ArrowCursor)  # Normal pointer on toolbar container
        self._init_ui()

    def _init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        container = QFrame()
        container.setObjectName("toolbarContainer")
        container.setCursor(Qt.CursorShape.ArrowCursor)
        
        bar_layout = QHBoxLayout(container)
        bar_layout.setContentsMargins(5, 4, 5, 4)
        bar_layout.setSpacing(6)

        # --- Section 1: Drawing Tools ---
        tools_frame = QFrame()
        tools_frame.setObjectName("sectionFrame")
        tools_layout = QHBoxLayout(tools_frame)
        tools_layout.setContentsMargins(2, 2, 2, 2)
        tools_layout.setSpacing(2)

        self.tool_group = QButtonGroup(self)
        self.tool_group.setExclusive(True)

        self.btn_rect = VectorToolButton("rect", t("tool_rect"))
        self.btn_rect.setCheckable(True)
        self.btn_rect.setChecked(True)
        self.tool_group.addButton(self.btn_rect)
        tools_layout.addWidget(self.btn_rect)

        self.btn_arrow = VectorToolButton("arrow", t("tool_arrow"))
        self.btn_arrow.setCheckable(True)
        self.tool_group.addButton(self.btn_arrow)
        tools_layout.addWidget(self.btn_arrow)

        self.btn_pen = VectorToolButton("pen", t("tool_pen"))
        self.btn_pen.setCheckable(True)
        self.tool_group.addButton(self.btn_pen)
        tools_layout.addWidget(self.btn_pen)

        self.btn_blur = VectorToolButton("blur", t("tool_blur"))
        self.btn_blur.setCheckable(True)
        self.tool_group.addButton(self.btn_blur)
        tools_layout.addWidget(self.btn_blur)

        self.btn_rect.clicked.connect(lambda: self._select_tool("rect"))
        self.btn_arrow.clicked.connect(lambda: self._select_tool("arrow"))
        self.btn_pen.clicked.connect(lambda: self._select_tool("pen"))
        self.btn_blur.clicked.connect(lambda: self._select_tool("blur"))

        bar_layout.addWidget(tools_frame)

        # --- Section 2: Color Palette ---
        colors_frame = QFrame()
        colors_frame.setObjectName("sectionFrame")
        colors_layout = QHBoxLayout(colors_frame)
        colors_layout.setContentsMargins(4, 2, 4, 2)
        colors_layout.setSpacing(4)

        self.color_group = QButtonGroup(self)
        self.color_group.setExclusive(True)

        for i, (hex_c, name) in enumerate(get_available_colors()):
            c_btn = ColorButton(hex_c, name)
            if i == 0:
                c_btn.setChecked(True)
            self.color_group.addButton(c_btn)
            c_btn.clicked.connect(lambda _, c=hex_c: self._select_color(c))
            colors_layout.addWidget(c_btn)

        bar_layout.addWidget(colors_frame)

        # --- Section 3: Undo Button ---
        self.btn_undo = VectorToolButton("undo", t("tool_undo"))
        self.btn_undo.clicked.connect(self.undo_requested.emit)
        bar_layout.addWidget(self.btn_undo)

        # Separator
        sep = QFrame()
        sep.setObjectName("separator")
        bar_layout.addWidget(sep)

        # --- Section 4: Actions (Save, Copy, Send, Cancel) ---
        self.btn_save = QPushButton(t("btn_save"))
        self.btn_save.setObjectName("actionSave")
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.setToolTip(t("btn_save_tooltip"))
        self.btn_save.clicked.connect(self.save_requested.emit)
        bar_layout.addWidget(self.btn_save)

        self.btn_copy = QPushButton(t("btn_copy"))
        self.btn_copy.setObjectName("actionCopy")
        self.btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy.setToolTip(t("btn_copy_tooltip"))
        self.btn_copy.clicked.connect(self.copy_requested.emit)
        bar_layout.addWidget(self.btn_copy)

        self.btn_send = QPushButton(t("btn_send"))
        self.btn_send.setObjectName("actionSend")
        self.btn_send.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_send.setToolTip(t("btn_send_tooltip"))
        self.btn_send.clicked.connect(self.send_requested.emit)
        bar_layout.addWidget(self.btn_send)

        self.btn_cancel = QPushButton("✕")
        self.btn_cancel.setObjectName("actionCancel")
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.setToolTip(t("btn_cancel_tooltip"))
        self.btn_cancel.clicked.connect(self.cancel_requested.emit)
        bar_layout.addWidget(self.btn_cancel)

        main_layout.addWidget(container)
        self.adjustSize()

    def _select_tool(self, tool_name: str):
        self.current_tool = tool_name
        self.tool_changed.emit(tool_name)

    def _select_color(self, hex_color: str):
        self.current_color = QColor(hex_color)
        self.color_changed.emit(self.current_color)
