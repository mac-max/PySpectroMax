from PyQt6.QtWidgets import QDialog, QFormLayout, QSpinBox, QCheckBox


class IntensitySettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Intensitätsachsen-Einstellungen")
        self.setGeometry(200, 200, 300, 200)
        self.parent = parent
        self.initUI()

    def initUI(self):
        layout = QFormLayout()

        self.auto_scale_checkbox = QCheckBox("Automatische Skalierung")
        self.auto_scale_checkbox.setChecked(self.parent.auto_scale_intensity)
        self.auto_scale_checkbox.stateChanged.connect(self.toggle_auto_scale)

        self.intensity_max_input = QSpinBox()
        self.intensity_max_input.setRange(1, 65535)
        self.intensity_max_input.setValue(self.parent.fixed_intensity_max)
        self.intensity_max_input.setEnabled(not self.parent.auto_scale_intensity)
        self.intensity_max_input.valueChanged.connect(self.update_intensity_max)

        layout.addRow(self.auto_scale_checkbox)
        layout.addRow("Maximale Intensität:", self.intensity_max_input)

        self.setLayout(layout)

    def toggle_auto_scale(self):
        self.parent.auto_scale_intensity = self.auto_scale_checkbox.isChecked()
        self.intensity_max_input.setEnabled(not self.parent.auto_scale_intensity)

    def update_intensity_max(self):
        self.parent.fixed_intensity_max = self.intensity_max_input.value()
