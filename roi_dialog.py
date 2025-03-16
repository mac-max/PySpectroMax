import cv2
import numpy as np
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QFormLayout, QSpinBox, QLabel
from PyQt6.QtGui import QPixmap, QImage, QPainter, QColor
from PyQt6.QtCore import Qt, QRect, QTimer
from roi_model import ROI  # Import der neuen ROI-Klasse

class InteractiveLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.start_x = self.start_y = self.end_x = self.end_y = None
        self.selecting = False
        self.callback = None  # Callback-Funktion zur ROI-Aktualisierung

    def set_selection_callback(self, callback):
        self.callback = callback

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_x = event.position().x()
            self.start_y = event.position().y()
            self.selecting = True

    def mouseMoveEvent(self, event):
        if self.selecting:
            self.end_x = event.position().x()
            self.end_y = event.position().y()
            if self.callback:
                self.callback(self.start_x, self.start_y, self.end_x, self.end_y, live=True)
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.selecting:
            self.end_x = event.position().x()
            self.end_y = event.position().y()
            self.selecting = False
            if self.callback:
                self.callback(self.start_x, self.start_y, self.end_x, self.end_y, live=False)
            self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.selecting and self.start_x is not None and self.end_x is not None:
            painter = QPainter(self)
            painter.setPen(QColor(255, 0, 0))  # Roter Stift für die Auswahl
            rect = QRect(int(self.start_x), int(self.start_y),
                         int(self.end_x - self.start_x), int(self.end_y - self.start_y))
            painter.drawRect(rect)

class ROIDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ROI-Einstellungen")
        self.setGeometry(300, 300, 600, 500)
        self.parent = parent

        # Erstelle ein ROI-Objekt aus den aktuellen ROI-Daten des Elternfensters
        # Annahme: parent.roi ist ein Tuple (x, y, width, height)
        self.roi = ROI(*self.parent.roi)

        layout = QVBoxLayout()

        # Verwende den interaktiven Label für die Live-Vorschau
        self.image_label = InteractiveLabel(self)
        self.image_label.set_selection_callback(self.interactive_roi_update)
        layout.addWidget(self.image_label)

        # Timer für periodische Bildupdates
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_live_image)
        self.timer.start(100)

        # Formular für numerische Eingabe
        form_layout = QFormLayout()
        self.x_input = QSpinBox()
        self.x_input.setRange(0, 1920)
        self.x_input.setValue(self.roi.x)
        self.x_input.valueChanged.connect(self.update_roi_from_inputs)

        self.y_input = QSpinBox()
        self.y_input.setRange(0, 1080)
        self.y_input.setValue(self.roi.y)
        self.y_input.valueChanged.connect(self.update_roi_from_inputs)

        self.width_input = QSpinBox()
        self.width_input.setRange(1, 1920)
        self.width_input.setValue(self.roi.width)
        self.width_input.valueChanged.connect(self.update_roi_from_inputs)

        self.height_input = QSpinBox()
        self.height_input.setRange(1, 1080)
        self.height_input.setValue(self.roi.height)
        self.height_input.valueChanged.connect(self.update_roi_from_inputs)

        form_layout.addRow("X:", self.x_input)
        form_layout.addRow("Y:", self.y_input)
        form_layout.addRow("Breite:", self.width_input)
        form_layout.addRow("Höhe:", self.height_input)
        layout.addLayout(form_layout)

        # Übernehmen-Button
        self.apply_button = QPushButton("Übernehmen")
        self.apply_button.clicked.connect(self.apply_roi)
        layout.addWidget(self.apply_button)

        self.setLayout(layout)

        # Variablen zum Speichern der letzten Skalierung und Offsets
        self.last_scale_x = 1.0
        self.last_scale_y = 1.0
        self.last_offset_x = 0
        self.last_offset_y = 0

        self.update_live_image()

    def update_live_image(self):
        frame = self.parent.camera.capture_frame()
        if frame is not None:
            # Konvertiere Bild in RGB für PyQt
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h_label = self.image_label.height()
            w_label = self.image_label.width()
            h_frame, w_frame = frame.shape[:2]
            aspect_ratio = w_frame / h_frame
            new_width = min(w_label, int(h_label * aspect_ratio))
            new_height = min(h_label, int(w_label / aspect_ratio))
            frame_resized = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)
            padded_image = np.zeros((h_label, w_label, 3), dtype=np.uint8)
            y_offset = (h_label - new_height) // 2
            x_offset = (w_label - new_width) // 2
            padded_image[y_offset:y_offset + new_height, x_offset:x_offset + new_width] = frame_resized

            # Speichere die Skalierungsfaktoren und Offsets für die Umrechnung der Mauskoordinaten
            self.last_scale_x = new_width / w_frame
            self.last_scale_y = new_height / h_frame
            self.last_offset_x = x_offset
            self.last_offset_y = y_offset

            h, w, ch = padded_image.shape
            bytes_per_line = ch * w
            qimg = QImage(padded_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(qimg)

            # Zeichne das aktuelle ROI-Rechteck
            self.roi.draw_on_pixmap(pixmap, self.last_scale_x, self.last_scale_y, x_offset, y_offset)
            self.image_label.setPixmap(pixmap)

    def interactive_roi_update(self, start_x, start_y, end_x, end_y, live):
        # Umrechnung der Label-Koordinaten in Bildkoordinaten
        x1 = (start_x - self.last_offset_x) / self.last_scale_x
        y1 = (start_y - self.last_offset_y) / self.last_scale_y
        x2 = (end_x - self.last_offset_x) / self.last_scale_x
        y2 = (end_y - self.last_offset_y) / self.last_scale_y

        new_x = int(min(x1, x2))
        new_y = int(min(y1, y2))
        new_width = int(abs(x2 - x1))
        new_height = int(abs(y2 - y1))

        # Aktualisiere das ROI-Objekt und synchronisiere die numerischen Eingaben
        self.roi.update(new_x, new_y, new_width, new_height)
        self.x_input.blockSignals(True)
        self.y_input.blockSignals(True)
        self.width_input.blockSignals(True)
        self.height_input.blockSignals(True)
        self.x_input.setValue(new_x)
        self.y_input.setValue(new_y)
        self.width_input.setValue(new_width)
        self.height_input.setValue(new_height)
        self.x_input.blockSignals(False)
        self.y_input.blockSignals(False)
        self.width_input.blockSignals(False)
        self.height_input.blockSignals(False)

        self.update_live_image()

    def update_roi_from_inputs(self):
        self.roi.update(self.x_input.value(), self.y_input.value(),
                        self.width_input.value(), self.height_input.value())
        self.update_live_image()

    def apply_roi(self):
        self.parent.roi = self.roi.as_tuple()
        self.accept()

    def closeEvent(self, event):
        self.timer.stop()
        event.accept()
