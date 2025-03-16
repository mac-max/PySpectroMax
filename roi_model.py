from PyQt5.QtCore import QRect
from PyQt5.QtGui import QPainter, QColor

class ROI:
    def __init__(self, x: int, y: int, width: int, height: int):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def update(self, x: int, y: int, width: int, height: int):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def as_tuple(self):
        return (self.x, self.y, self.width, self.height)

    def draw_on_pixmap(self, pixmap, scale_x: float = 1.0, scale_y: float = 1.0, offset_x: int = 0, offset_y: int = 0):
        painter = QPainter(pixmap)
        painter.setPen(QColor(0, 255, 0))
        rect = QRect(int(self.x * scale_x + offset_x),
                     int(self.y * scale_y + offset_y),
                     int(self.width * scale_x),
                     int(self.height * scale_y))
        painter.drawRect(rect)
        painter.end()
