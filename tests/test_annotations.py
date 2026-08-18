import unittest
from PyQt6.QtCore import QPoint, QRect, Qt
from PyQt6.QtGui import QColor, QPixmap, QImage, QPainter
from PyQt6.QtWidgets import QApplication

from capture.annotations import (
    RectangleAnnotation,
    ArrowAnnotation,
    PenAnnotation,
    BlurAnnotation,
    AnnotationHistory,
)

# Ensure QApplication exists for GUI/Pixmap tests
app = QApplication.instance()
if app is None:
    app = QApplication([])


class TestAnnotations(unittest.TestCase):
    def setUp(self):
        # Create a 200x200 sample canvas
        self.pixmap = QPixmap(200, 200)
        self.pixmap.fill(Qt.GlobalColor.white)
        self.rect = QRect(0, 0, 200, 200)

    def test_rectangle_annotation(self):
        history = AnnotationHistory()
        rect_ann = RectangleAnnotation(
            start=QPoint(10, 10),
            end=QPoint(100, 100),
            color=QColor("#ED4245"),
            stroke_width=2
        )
        history.add(rect_ann)
        self.assertEqual(history.count(), 1)
        self.assertFalse(history.is_empty())

        rendered = history.render_all(self.pixmap, self.rect)
        self.assertIsNotNone(rendered)
        self.assertEqual(rendered.size(), self.rect.size())

    def test_arrow_annotation(self):
        history = AnnotationHistory()
        arrow_ann = ArrowAnnotation(
            start=QPoint(20, 20),
            end=QPoint(150, 150),
            color=QColor("#5865F2"),
            stroke_width=3
        )
        history.add(arrow_ann)
        rendered = history.render_all(self.pixmap, self.rect)
        self.assertIsNotNone(rendered)

    def test_pen_annotation(self):
        history = AnnotationHistory()
        pen_ann = PenAnnotation(
            points=[QPoint(10, 10), QPoint(20, 30), QPoint(40, 50)],
            color=QColor("#23A55A"),
            stroke_width=2
        )
        history.add(pen_ann)
        rendered = history.render_all(self.pixmap, self.rect)
        self.assertIsNotNone(rendered)

    def test_blur_annotation(self):
        history = AnnotationHistory()
        # Draw some colored area on pixmap to blur
        painter = QPainter(self.pixmap)
        painter.fillRect(QRect(50, 50, 60, 60), QColor(0, 0, 255))
        painter.end()

        blur_ann = BlurAnnotation(
            rect=QRect(50, 50, 60, 60),
            pixel_block_size=8
        )
        history.add(blur_ann)
        rendered = history.render_all(self.pixmap, self.rect)
        self.assertIsNotNone(rendered)

    def test_undo_history(self):
        history = AnnotationHistory()
        history.add(RectangleAnnotation(start=QPoint(0, 0), end=QPoint(10, 10)))
        history.add(ArrowAnnotation(start=QPoint(0, 0), end=QPoint(20, 20)))
        self.assertEqual(history.count(), 2)

        popped = history.undo()
        self.assertIsInstance(popped, ArrowAnnotation)
        self.assertEqual(history.count(), 1)

        popped2 = history.undo()
        self.assertIsInstance(popped2, RectangleAnnotation)
        self.assertEqual(history.count(), 0)
        self.assertTrue(history.is_empty())

        popped3 = history.undo()
        self.assertIsNone(popped3)


if __name__ == "__main__":
    unittest.main()
