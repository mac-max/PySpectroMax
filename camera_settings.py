from PyQt6.QtWidgets import QDialog, QSlider, QCheckBox, QFormLayout, QSpinBox, QPushButton, QDoubleSpinBox
import numpy as np
# Weitere Importe, falls notwendig

class CameraSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Kameraeinstellungen")
        self.setGeometry(200, 200, 300, 500)
        self.parent = parent
        self.initUI()


    def initUI(self):
        # layout = QVBoxLayout()
        form_layout = QFormLayout()

        # Belichtungszeit
        self.exposure_input = QSpinBox()
        self.exposure_input.setRange(-20, 1)
        self.exposure_input.setValue(int(self.parent.camera.exposure))
        self.exposure_input.valueChanged.connect(self.update_exposure)
        form_layout.addRow("Belichtungszeit:", self.exposure_input)

        # Gain
        self.gain_input = QSlider()
        self.gain_input.setRange(0, 100)
        self.gain_input.setValue(int(self.parent.camera.gain))
        self.gain_input.valueChanged.connect(self.update_gain)
        form_layout.addRow("Gain:", self.gain_input)

        # Kontrast
        self.contrast_input = QSlider()
        self.contrast_input.setRange(0, 255)
        self.contrast_input.setValue(int(self.parent.camera.contrast))
        self.contrast_input.valueChanged.connect(self.update_contrast)
        form_layout.addRow("Kontrast:", self.contrast_input)

        # Sättigung
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
        self.mirror_checkbox.setChecked(self.parent.mirror)  # Annahme: self.parent besitzt ein Attribut 'mirror'
        self.mirror_checkbox.stateChanged.connect(self.toggle_mirror)
        form_layout.addRow(self.mirror_checkbox)

        # HDR-Einstellungen:
        # HDR Min. Belichtung
        self.hdr_min_exposure_input = QSpinBox()
        self.hdr_min_exposure_input.setRange(-10, 1)
        # Standardwert aus der Hauptanwendung oder Default -10
        self.hdr_min_exposure_input.setValue(getattr(self.parent, "hdr_min_exposure", -10))
        self.hdr_min_exposure_input.valueChanged.connect(self.update_hdr_settings)
        form_layout.addRow("HDR Min. Belichtung:", self.hdr_min_exposure_input)

        # HDR Max. Belichtung
        self.hdr_max_exposure_input = QSpinBox()
        self.hdr_max_exposure_input.setRange(-10, 1)
        self.hdr_max_exposure_input.setValue(getattr(self.parent, "hdr_max_exposure", 1))
        self.hdr_max_exposure_input.valueChanged.connect(self.update_hdr_settings)
        form_layout.addRow("HDR Max. Belichtung:", self.hdr_max_exposure_input)

        # Anzahl Bilder pro Belichtungsstufe für HDR
        self.hdr_num_frames_input = QSpinBox()
        self.hdr_num_frames_input.setRange(1, 20)
        self.hdr_num_frames_input.setValue(getattr(self.parent, "hdr_num_frames", 3))
        self.hdr_num_frames_input.valueChanged.connect(self.update_hdr_settings)
        form_layout.addRow("HDR Bilder/Stufe:", self.hdr_num_frames_input)

        # Auto-Belichtung Button
        self.auto_exposure_button = QPushButton("Auto-Belichtungszeit setzen")
        self.auto_exposure_button.clicked.connect(self.set_auto_exposure)
        form_layout.addRow(self.auto_exposure_button)

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

        form_layout.addRow(self.auto_scale_checkbox)
        form_layout.addRow("Maximale Intensität:", self.intensity_max_input)

        # --- Neue Felder für die Wellenlängen-Limits ---
        # Diese Felder sollen nur relevant sein, wenn eine Kalibration vorliegt.
        # Du kannst hier Standardwerte setzen, z. B. 400 nm und 700 nm.
        self.wavelength_min_input = QDoubleSpinBox()
        self.wavelength_min_input.setRange(0, 10000)
        self.wavelength_min_input.setDecimals(2)
        # Falls die Haupt-GUI schon einen Wert hat, verwende diesen, ansonsten Default:
        self.wavelength_min_input.setValue(getattr(self.parent, 'wavelength_min', 400.0))
        self.wavelength_min_input.valueChanged.connect(self.update_wavelength_limits)
        form_layout.addRow("Min. Wellenlänge (nm):", self.wavelength_min_input)

        self.wavelength_max_input = QDoubleSpinBox()
        self.wavelength_max_input.setRange(0, 10000)
        self.wavelength_max_input.setDecimals(2)
        self.wavelength_max_input.setValue(getattr(self.parent, 'wavelength_max', 700.0))
        self.wavelength_max_input.valueChanged.connect(self.update_wavelength_limits)
        form_layout.addRow("Max. Wellenlänge (nm):", self.wavelength_max_input)
        # -----------------------------------------------------

        self.setLayout(form_layout)

    def update_dark_field_setting(self):
        self.parent.dark_field_enabled = self.dark_field_checkbox.isChecked()

    def capture_dark_field(self):
        """
            Nimmt num_frames Dunkelfeldaufnahmen auf und mittelt diese.
            Das Ergebnis wird in self.parent.dark_field gespeichert.
            """
        frames = []
        for i in range(self.parent.hdr_num_frames):
            frame = self.parent.camera.capture_frame()
            if frame is not None:
                frames.append(frame.astype(np.float32))
        if frames:
            dark_field = np.mean(frames, axis=0)
            self.parent.dark_field = dark_field
            print("[INFO] Dunkelfeld (gemittelt über {} Aufnahmen) aufgenommen!".format(self.parent.hdr_num_frames))
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
        """ Berechnet eine optimale Belichtungszeit und setzt sie """
        """ Startet die automatische Belichtungszeit-Anpassung """
        self.parent.camera.set_auto_exposure()
        self.exposure_input.setValue(int(self.parent.camera.exposure))

    def toggle_auto_scale(self):
        self.parent.auto_scale_intensity = self.auto_scale_checkbox.isChecked()
        self.intensity_max_input.setEnabled(not self.parent.auto_scale_intensity)

    def update_intensity_max(self):
        self.parent.fixed_intensity_max = self.intensity_max_input.value()

    def update_wavelength_limits(self):
        # Speichere die neuen Wellenlängen-Limits in der Haupt-GUI oder im Kamera-Objekt
        self.parent.wavelength_min = self.wavelength_min_input.value()
        self.parent.wavelength_max = self.wavelength_max_input.value()
        # Falls du bereits ein kalibriertes Spektrum plottest, kannst du hier auch das Plot-Update triggern.

    def update_hdr_settings(self):
        # Speichere die HDR-Einstellungen in der Hauptanwendung oder im Kameraobjekt
        self.parent.hdr_min_exposure = self.hdr_min_exposure_input.value()
        self.parent.hdr_max_exposure = self.hdr_max_exposure_input.value()
        self.parent.hdr_num_frames = self.hdr_num_frames_input.value()
