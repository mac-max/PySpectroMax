
import numpy as np
import cv2
from PyQt5.QtWidgets import QDialog, QFormLayout, QCheckBox, QPushButton, QMessageBox
from PyQt5.QtCore import Qt

class RelativeSpectrumDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Relativspektrum Einstellungen")
        self.setStyleSheet("background-color: #1e1e1e; color: white;")
        self.parent = parent  # Haupt-GUI
        self.initUI()

    def initUI(self):
        layout = QFormLayout()
        # Checkbox: Quotientenbildung aktivieren
        self.enable_quotient_cb = QCheckBox("Quotientenbildung aktivieren")
        self.enable_quotient_cb.setChecked(getattr(self.parent, "relative_spectrum_enabled", False))
        self.enable_quotient_cb.stateChanged.connect(self.toggle_relative_spectrum)
        layout.addRow(self.enable_quotient_cb)

        # Checkbox: Normiere Quotient auf 1
        self.normalize_cb = QCheckBox("Normiere Quotient auf 1")
        self.normalize_cb.setChecked(getattr(self.parent, "normalize_relative_spectrum", False))
        self.normalize_cb.stateChanged.connect(self.toggle_normalization)
        layout.addRow(self.normalize_cb)

        # Button: Referenzspektrum aufnehmen
        self.btn_capture_ref = QPushButton("Referenzspektrum aufnehmen")
        self.btn_capture_ref.clicked.connect(self.capture_reference_spectrum)
        layout.addRow(self.btn_capture_ref)

        self.setLayout(layout)

    def toggle_relative_spectrum(self):
        self.parent.relative_spectrum_enabled = self.enable_quotient_cb.isChecked()

    def toggle_normalization(self):
        self.parent.normalize_relative_spectrum = self.normalize_cb.isChecked()

    def capture_reference_spectrum(self):
        # Nimm ein Referenzbild auf:
        frame = self.parent.camera.capture_frame()
        if frame is None:
            QMessageBox.warning(self, "Fehler", "Kein Bild empfangen!")
            return
        # Optional: Falls das Referenzspektrum analog zum normalen Spektrum (z.B. über ROI) berechnet wird:
        x, y, w, h = self.parent.roi
        if len(frame.shape) == 3:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        roi_frame = frame[y:y+h, x:x+w]
        if roi_frame.size == 0:
            QMessageBox.warning(self, "Fehler", "ROI ist leer!")
            return
        reference_spectrum = np.sum(roi_frame, axis=0)
        self.parent.reference_spectrum = reference_spectrum
        # Speichere als CSV:
        np.savetxt("reference_spectrum.csv", reference_spectrum, delimiter=",", header="Intensity", comments="")
        QMessageBox.information(self, "Erfolg", "Referenzspektrum aufgenommen und gespeichert!")
