from PyQt5.QtWidgets import QDialog, QSlider, QCheckBox, QFormLayout, QSpinBox, QPushButton, QDoubleSpinBox
import numpy as np

class CameraSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #1e1e1e; color: white;")
        self.setWindowTitle("Kameraeinstellungen")
        self.setGeometry(200, 200, 300, 600)
        self.parent = parent
        self.initUI()

    def initUI(self):
        form_layout = QFormLayout()

        # Belichtung
        self.exposure_input = QSpinBox()
        self.exposure_input.setRange(-20, 1)
        self.exposure_input.setValue(int(self.parent.camera.exposure))
        self.exposure_input.valueChanged.connect(self.update_exposure)
        form_layout.addRow("Belichtungszeit:", self.exposure_input)

        self.auto_exposure_button = QPushButton("Auto-Belichtungszeit setzen")
        self.auto_exposure_button.clicked.connect(self.set_auto_exposure)
        form_layout.addRow(self.auto_exposure_button)

        self.fps_input = QSpinBox()
        self.fps_input.setRange(-10, 30000)
        self.fps_input.setValue(1)  # Standardwert
        self.fps_input.valueChanged.connect(self.update_fps)
        form_layout.addRow("FPS:", self.fps_input)

        self.gain_input = QSlider()
        self.gain_input.setRange(0, 100)
        self.gain_input.setValue(int(self.parent.camera.gain))
        self.gain_input.valueChanged.connect(self.update_gain)
        form_layout.addRow("Gain:", self.gain_input)

        self.contrast_input = QSlider()
        self.contrast_input.setRange(0, 255)
        self.contrast_input.setValue(int(self.parent.camera.contrast))
        self.contrast_input.valueChanged.connect(self.update_contrast)
        form_layout.addRow("Kontrast:", self.contrast_input)

        self.saturation_input = QSlider()
        self.saturation_input.setRange(0, 255)
        self.saturation_input.setValue(int(self.parent.camera.saturation))
        self.saturation_input.valueChanged.connect(self.update_saturation)
        form_layout.addRow("Sättigung:", self.saturation_input)

        # Dunkelfeldaufnahme
        self.dark_field_checkbox = QCheckBox("Dunkelfeldkorrektur aktivieren")
        self.dark_field_checkbox.setChecked(getattr(self.parent, "dark_field_enabled", False))
        self.dark_field_checkbox.stateChanged.connect(self.update_dark_field_setting)
        form_layout.addRow(self.dark_field_checkbox)

        self.btn_capture_dark_field = QPushButton("Dunkelfeld aufnehmen")
        self.btn_capture_dark_field.clicked.connect(self.capture_dark_field)
        form_layout.addRow(self.btn_capture_dark_field)

        # Bild spiegeln
        self.mirror_checkbox = QCheckBox("Horizontal spiegeln")
        self.mirror_checkbox.setChecked(self.parent.mirror)
        self.mirror_checkbox.stateChanged.connect(self.toggle_mirror)
        form_layout.addRow(self.mirror_checkbox)

        # HDR-Einstellungen:
        self.hdr_min_exposure_input = QSpinBox()
        self.hdr_min_exposure_input.setRange(-10, 1)
        self.hdr_min_exposure_input.setValue(getattr(self.parent, "hdr_min_exposure", -10))
        self.hdr_min_exposure_input.valueChanged.connect(self.update_hdr_settings)
        form_layout.addRow("HDR Min. Belichtung:", self.hdr_min_exposure_input)

        self.hdr_max_exposure_input = QSpinBox()
        self.hdr_max_exposure_input.setRange(-10, 1)
        self.hdr_max_exposure_input.setValue(getattr(self.parent, "hdr_max_exposure", 1))
        self.hdr_max_exposure_input.valueChanged.connect(self.update_hdr_settings)
        form_layout.addRow("HDR Max. Belichtung:", self.hdr_max_exposure_input)

        self.hdr_num_frames_input = QSpinBox()
        self.hdr_num_frames_input.setRange(1, 20)
        self.hdr_num_frames_input.setValue(getattr(self.parent, "hdr_num_frames", 3))
        self.hdr_num_frames_input.valueChanged.connect(self.update_hdr_settings)
        form_layout.addRow("HDR Bilder/Stufe:", self.hdr_num_frames_input)

        # Neue Performance-Optionen:
        self.low_res_checkbox = QCheckBox("Niedrigere Live-Auflösung verwenden")
        # Standard: deaktiviert
        self.low_res_checkbox.setChecked(getattr(self.parent, "low_res_mode", False))
        self.low_res_checkbox.stateChanged.connect(self.update_performance_settings)
        form_layout.addRow(self.low_res_checkbox)

        self.update_interval_input = QSpinBox()
        self.update_interval_input.setRange(50, 1000)  # in ms
        # Standardwert z.B. 200ms, falls im Performance-Modus aktiv:
        self.update_interval_input.setValue(getattr(self.parent, "update_interval", 200))
        self.update_interval_input.valueChanged.connect(self.update_performance_settings)
        form_layout.addRow("Update-Intervall (ms):", self.update_interval_input)

        # Automatische Intensitätsskala
        self.auto_scale_checkbox = QCheckBox("Automatische Skalierung")
        self.auto_scale_checkbox.setChecked(self.parent.auto_scale_intensity)
        self.auto_scale_checkbox.stateChanged.connect(self.toggle_auto_scale)
        form_layout.addRow(self.auto_scale_checkbox)

        self.intensity_max_input = QSpinBox()
        self.intensity_max_input.setRange(1, 65535)
        self.intensity_max_input.setValue(self.parent.fixed_intensity_max)
        self.intensity_max_input.setEnabled(not self.parent.auto_scale_intensity)
        self.intensity_max_input.valueChanged.connect(self.update_intensity_max)
        form_layout.addRow("Maximale Intensität:", self.intensity_max_input)

        # Neue Felder für Wellenlängen-Limits
        self.wavelength_min_input = QDoubleSpinBox()
        self.wavelength_min_input.setRange(0, 10000)
        self.wavelength_min_input.setDecimals(2)
        self.wavelength_min_input.setValue(getattr(self.parent, 'wavelength_min', 400.0))
        self.wavelength_min_input.valueChanged.connect(self.update_wavelength_limits)
        form_layout.addRow("Min. Wellenlänge (nm):", self.wavelength_min_input)

        self.wavelength_max_input = QDoubleSpinBox()
        self.wavelength_max_input.setRange(0, 10000)
        self.wavelength_max_input.setDecimals(2)
        self.wavelength_max_input.setValue(getattr(self.parent, 'wavelength_max', 700.0))
        self.wavelength_max_input.valueChanged.connect(self.update_wavelength_limits)
        form_layout.addRow("Max. Wellenlänge (nm):", self.wavelength_max_input)

        self.setLayout(form_layout)

    def update_dark_field_setting(self):
        self.parent.dark_field_enabled = self.dark_field_checkbox.isChecked()

    def update_fps(self):
        new_fps = self.fps_input.value()
        self.parent.fps = new_fps
        # Setze auch die FPS in der Kamera, falls unterstützt:
        self.parent.camera.set_fps(new_fps)

    def capture_dark_field(self):
        frames = []
        for i in range(self.parent.hdr_num_frames):
            frame = self.parent.camera.capture_frame()
            if frame is not None:
                frames.append(frame.astype(np.float32))
        if frames:
            dark_field = np.mean(frames, axis=0)
            self.parent.dark_field = dark_field
            print("[INFO] Dunkelfeld (gemittelt) aufgenommen!")
        else:
            print("[WARNUNG] Dunkelfeldaufnahme fehlgeschlagen!")

    def toggle_mirror(self):
        self.parent.mirror = self.mirror_checkbox.isChecked()

    def update_exposure(self):
        self.parent.camera.set_exposure(self.exposure_input.value())

    def update_gain(self):
        self.parent.camera.set_gain(self.gain_input.value())

    def update_brightness(self):
        self.parent.camera.set_brightness(self.brightness_input.value())

    def update_contrast(self):
        self.parent.camera.set_contrast(self.contrast_input.value())

    def update_saturation(self):
        self.parent.camera.set_saturation(self.saturation_input.value())

    def set_auto_exposure(self):
        self.parent.camera.set_auto_exposure()
        self.exposure_input.setValue(int(self.parent.camera.exposure))

    def toggle_auto_scale(self):
        self.parent.auto_scale_intensity = self.auto_scale_checkbox.isChecked()
        self.intensity_max_input.setEnabled(not self.parent.auto_scale_intensity)

    def update_intensity_max(self):
        self.parent.fixed_intensity_max = self.intensity_max_input.value()

    def update_wavelength_limits(self):
        self.parent.wavelength_min = self.wavelength_min_input.value()
        self.parent.wavelength_max = self.wavelength_max_input.value()

    def update_hdr_settings(self):
        self.parent.hdr_min_exposure = self.hdr_min_exposure_input.value()
        self.parent.hdr_max_exposure = self.hdr_max_exposure_input.value()
        self.parent.hdr_num_frames = self.hdr_num_frames_input.value()

    def update_performance_settings(self):
        # Diese Methode speichert Performance-Optionen in der Hauptanwendung
        self.parent.low_res_mode = False #self.low_res_checkbox.isChecked()
        self.parent.update_interval = self.update_interval_input.value()
