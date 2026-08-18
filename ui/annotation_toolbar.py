import logging
from typing import Optional, Callable
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QColor, QPainter, QBrush, QPen
from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QPushButton,
    QFrame,
    QButtonGroup,
    QToolTip,
)

logger = logging.getLogger(__name__)

TOOLBAR_STYLESHEET = """
QFrame#toolbarContainer {
    background-color: #2B2D31;
    border: 1px solid #3F4147;
    border-radius: 8px;
    padding: 3px 6px;
}

QPushButton {
    background-color: transparent;
    color: #DBDEE1;
    border: 1px solid transparent;
    border-radius: 5px;
    font-size: 14px;
    min-width: 28px;
    max-width: 32px;
    height: 28px;
    padding: 2px;
}

QPushButton:hover {
    background-color: #35373C;
    border-color: #4E5058;
}

QPushButton:checked {
    background-color: #5865F2;
    color: #FFFFFF;
    border-color: #5865F2;
}

QPushButton#sendBtn {
    background-color: #23A55A;
    color: #FFFFFF;
    font-weight: bold;
    min-width: 32px;
    border-radius: 5px;
}

QPushButton#sendBtn:hover {
    background-color: #1F924E;
}

QPushButton#cancelBtn {
    color: #F23F43;
}

QPushButton#cancelBtn:hover {
    background-color: rgba(242, 63, 67, 0.15);
    border-color: #F23F43;
}

QFrame#separator {
    background-color: #3F4147;
    width: 1px;
    max-width: 1px;
    margin: 4px 2px;
}
"""

AVAILABLE_COLORS = [
    ("#ED4245", "Red"),
    ("#FEE75C", "Yellow"),
    ("#23A55A", "Green"),
    ("#5865F2", "Discord Blurple"),
    ("#FFFFFF", "White"),
]


class ColorButton(QPushButton):
    """Circular color picker button."""
    def __init__(self, hex_color: str, name: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.hex_color = hex_color
        self.setCheckable(True)
        self.setToolTip(f"Color: {name}")
        self.setFixedSize(22, 22)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        color = QColor(self.hex_color)
        painter.setBrush(QBrush(color))
        
        if self.isChecked():
            painter.setPen(QPen(QColor(255, 255, 255), 2))
            painter.drawEllipse(2, 2, 18, 18)
        else:
            painter.setPen(QPen(QColor(60, 60, 60), 1))
            painter.drawEllipse(3, 3, 16, 16)
        
        painter.end()


class AnnotationToolbar(QWidget):
    """
    Floating toolbar for screenshot drawing tools, color selection, and action triggers.
    """
    tool_changed = pyqtSignal(str)          # 'rect', 'arrow', 'pen', 'blur', 'none'
    color_changed = pyqtSignal(QColor)
    undo_requested = pyqtSignal()
    copy_requested = pyqtSignal()
    send_requested = pyqtSignal()
    cancel_requested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.current_tool = "rect"
        self.current_color = QColor("#ED4245")  # Red by default

        self.setStyleSheet(TOOLBAR_STYLESHEET)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._init_ui()

    def _init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        container = QFrame()
        container.setObjectName("toolbarContainer")
        bar_layout = QHBoxLayout(container)
        bar_layout.setContentsMargins(4, 3, 4, 3)
        bar_layout.setSpacing(3)

        # 1. Tool Selection Buttons
        self.tool_group = QButtonGroup(self)
        self.tool_group.setExclusive(True)

        self.btn_rect = QPushButton("🔲")
        self.btn_rect.setToolTip("Rectangle / Box (R)")
        self.btn_rect.setCheckable(True)
        self.btn_rect.setChecked(True)
        self.tool_group.addButton(self.btn_rect)
        bar_layout.addWidget(self.btn_rect)

        self.btn_arrow = QPushButton("➡️")
        self.btn_arrow.setToolTip("Arrow (A)")
        self.btn_arrow.setCheckable(True)
        self.tool_group.addButton(self.btn_arrow)
        bar_layout.addWidget(self.btn_arrow)

        self.btn_pen = QPushButton("✏️")
        self.btn_pen.setToolTip("Freehand Pen (P)")
        self.btn_pen.setCheckable(True)
        self.tool_group.addButton(self.btn_pen)
        bar_layout.addWidget(self.btn_pen)

        self.btn_blur = QPushButton("💧")
        self.btn_blur.setToolTip("Blur / Pixelate Content (B)")
        self.btn_blur.setCheckable(True)
        self.tool_group.addButton(self.btn_blur)
        bar_layout.addWidget(self.btn_blur)

        self.btn_rect.clicked.connect(lambda: self._select_tool("rect"))
        self.btn_arrow.clicked.connect(lambda: self._select_tool("arrow"))
        self.btn_pen.clicked.connect(lambda: self._select_tool("pen"))
        self.btn_blur.clicked.connect(lambda: self._select_tool("blur"))

        # Separator
        sep1 = QFrame()
        sep1.setObjectName("separator")
        bar_layout.addWidget(sep1)

        # 2. Color Palette
        self.color_group = QButtonGroup(self)
        self.color_group.setExclusive(True)

        for i, (hex_c, name) in enumerate(AVAILABLE_COLORS):
            c_btn = ColorButton(hex_c, name)
            if i == 0:
                c_btn.setChecked(True)
            self.color_group.addButton(c_btn)
            c_btn.clicked.connect(lambda _, c=hex_c: self._select_color(c))
            bar_layout.addWidget(c_btn)

        # Separator
        sep2 = QFrame()
        sep2.setObjectName("separator")
        bar_layout.addWidget(sep2)

        # 3. Undo button
        self.btn_undo = QPushButton("↩️")
        self.btn_undo.setToolTip("Undo Last Action (Ctrl+Z)")
        self.btn_undo.clicked.connect(self.undo_requested.emit)
        bar_layout.addWidget(self.btn_undo)

        # 4. Copy to clipboard button
        self.btn_copy = QPushButton("📋")
        self.btn_copy.setToolTip("Copy to Clipboard (Ctrl+C)")
        self.btn_copy.clicked.connect(self.copy_requested.emit)
        bar_layout.addWidget(self.btn_copy)

        # 5. Cancel button
        self.btn_cancel = QPushButton("❌")
        self.btn_cancel.setObjectName("cancelBtn")
        self.btn_cancel.setToolTip("Cancel (Esc)")
        self.btn_cancel.clicked.connect(self.cancel_requested.emit)
        bar_layout.addWidget(self.btn_cancel)

        # 6. Send to Discord button
        self.btn_send = QPushButton("🚀")
        self.btn_send.setObjectName("sendBtn")
        self.btn_send.setToolTip("Send to Discord (Enter)")
        self.btn_send.clicked.connect(self.send_requested.emit)
        bar_layout.addWidget(self.btn_send)

        main_layout.addWidget(container)
        self.adjustSize()

    def _select_tool(self, tool_name: str):
        self.current_tool = tool_name
        self.tool_changed.emit(tool_name)

    def _select_color(self, hex_color: str):
        self.current_color = QColor(hex_color)
        self.color_changed.emit(self.current_color)
