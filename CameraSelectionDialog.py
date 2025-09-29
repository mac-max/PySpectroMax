from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QComboBox, QPushButton
class CameraSelectionDialog(QDialog):
    def __init__(self, camera_list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Kamera auswählen")
        self.selected_camera = None

        layout = QVBoxLayout()

        label = QLabel("Bitte wählen Sie eine Kamera aus:")
        layout.addWidget(label)

        self.combo = QComboBox()
        # Füge jeden Kamerainhalt als Eintrag hinzu
        for cam in camera_list:
            self.combo.addItem(f"Kamera {cam}", cam)
        layout.addWidget(self.combo)

        btn_ok = QPushButton("OK")
        btn_ok.clicked.connect(self.accept)
        layout.addWidget(btn_ok)

        self.setLayout(layout)

    def accept(self):
        self.selected_camera = self.combo.currentData()
        super().accept()