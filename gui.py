import cv2
import json
import os
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
import datetime
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QTimer, Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from camera import Camera
from roi_dialog import ROIDialog
from intensity_settings import IntensitySettingsDialog
from camera_settings import CameraSettingsDialog
from calibration_dialog import CalibrationDialog
from scipy.signal import find_peaks
from matplotlib.patches import Rectangle

mpl.use("Qt5Agg")
mpl.rcParams['figure.facecolor'] = '#1e1e1e'
mpl.rcParams['axes.facecolor'] = '#1e1e1e'
mpl.rcParams['axes.edgecolor'] = 'white'
mpl.rcParams['axes.labelcolor'] = 'white'
mpl.rcParams['xtick.color'] = 'white'
mpl.rcParams['ytick.color'] = 'white'
mpl.rcParams['text.color'] = 'white'
mpl.rcParams['figure.autolayout'] = True

class SpectrometerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        # Lade Einstellungen, falls vorhanden:
        self.camera = Camera()
        self.initUI()
        self.setStyleSheet("background-color: #1e1e1e; color: white;")
        self.camera = Camera()
        self.integration_time = 30  # Standard-Belichtungszeit in ms
        self.auto_scale_intensity = True
        self.fixed_intensity_max = 255
        self.mirror = True
        self.low_res_mode = False
        self.update_interval = 200  # Standard-Update-Intervall in ms, wenn low_res_mode aktiviert wird
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.live_update = True
        self.update_timer_interval()
        self.hdr_result = None
        self.hdr_num_frames = 5
        self.relative_spectrum_enabled = False  # Quotientenbildung aktiv?
        self.normalize_relative_spectrum = False  # Quotient normieren (max = 1)?
        self.reference_spectrum = None  # Hier wird das aufgenommene Referenzspektrum gespeichert

        self.fps = 1  # Standard-FPS, falls keine Einstellung vorhanden ist
        self.roi = (0, 470, 1920, 150)
        self.setWindowTitle("USB-Spektrometer GUI")
        self.setGeometry(100, 100, 900, 600)
        self.load_settings()

    def initUI(self):
        main_layout = QHBoxLayout()
        self.bg_color = self.palette().color(self.backgroundRole()).name()

        # Linke Seite: Button-Bereich
        button_layout = QVBoxLayout()
        self.btn_capture = QPushButton("CSV speichern")
        self.btn_capture.clicked.connect(self.capture_spectrum)
        button_layout.addWidget(self.btn_capture)
        self.btn_save_image = QPushButton("JPG speichern")
        self.btn_save_image.clicked.connect(self.save_spectrum_as_jpg)
        button_layout.addWidget(self.btn_save_image)
        self.btn_roi = QPushButton("ROI einstellen")
        self.btn_roi.clicked.connect(self.open_roi_dialog)
        button_layout.addWidget(self.btn_roi)
        self.btn_camera_settings = QPushButton("Kameraeinstellungen")
        self.btn_camera_settings.clicked.connect(self.open_camera_settings)
        button_layout.addWidget(self.btn_camera_settings)
        self.btn_hdr = QPushButton("HDR aufnehmen")
        self.btn_hdr.clicked.connect(self.capture_hdr)
        button_layout.addWidget(self.btn_hdr)
        self.btn_live_toggle = QPushButton("Live-Update ein/aus")
        self.btn_live_toggle.clicked.connect(self.toggle_live_update)
        button_layout.addWidget(self.btn_live_toggle)
        self.btn_calibration = QPushButton("Kalibration starten")
        self.btn_calibration.clicked.connect(self.start_calibration)
        button_layout.addWidget(self.btn_calibration)
        self.btn_relative = QPushButton("Relativspektrum")
        self.btn_relative.clicked.connect(self.open_relative_spectrum_dialog)
        button_layout.addWidget(self.btn_relative)
        button_layout.addStretch()
        main_layout.addLayout(button_layout, 1)
        self.btn_save_settings = QPushButton("Einstellungen speichern")
        self.btn_save_settings.clicked.connect(self.save_settings)
        button_layout.addWidget(self.btn_save_settings)

        # Rechte Seite: Spektrum-Anzeige mit Matplotlib
        self.figure, self.ax = plt.subplots()
        self.ax.set_facecolor(self.bg_color)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.figure.set_facecolor(self.bg_color)
        self.canvas.mpl_connect("button_press_event", self.on_mouse_press)
        self.canvas.mpl_connect("motion_notify_event", self.on_mouse_move)
        self.canvas.mpl_connect("button_release_event", self.on_mouse_release)
        spectrum_layout = QVBoxLayout()
        spectrum_layout.addWidget(self.canvas)
        main_layout.addLayout(spectrum_layout, 3)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

    def open_relative_spectrum_dialog(self):
        from relative_spectrum_dialog import RelativeSpectrumDialog
        dialog = RelativeSpectrumDialog(self)
        dialog.exec_()

    def load_settings(self):
        if os.path.exists("settings.json"):
            with open("settings.json", "r") as f:
                settings = json.load(f)
            self.integration_time = settings.get("integration_time", 30)
            self.auto_scale_intensity = settings.get("auto_scale_intensity", True)
            self.fixed_intensity_max = settings.get("fixed_intensity_max", 255)
            self.mirror = settings.get("mirror", True)
            self.hdr_num_frames = settings.get("hdr_num_frames", 5)
            self.roi = tuple(settings.get("roi", [0, 470, 1920, 150]))
            self.low_res_mode = settings.get("low_res_mode", False)
            self.update_interval = settings.get("update_interval", 200)
            # Kameraeinstellungen:
            cam_settings = settings.get("camera", {})
            self.camera.exposure = cam_settings.get("exposure", self.camera.exposure)
            self.camera.fps = cam_settings.get("fps", self.camera.fps)
            self.camera.gain = cam_settings.get("gain", self.camera.gain)
            self.camera.brightness = cam_settings.get("brightness", self.camera.brightness)
            self.camera.contrast = cam_settings.get("contrast", self.camera.contrast)
            self.camera.saturation = cam_settings.get("saturation", self.camera.saturation)
            self.camera.hdr_min_exposure = cam_settings.get("hdr_min_exposure", self.camera.hdr_min_exposure)
            self.camera.hdr_max_exposure = cam_settings.get("hdr_max_exposure", self.camera.hdr_max_exposure)
            self.camera.sensitivity_factors = cam_settings.get("sensitivity_factors", self.camera.sensitivity_factors)
            self.camera.apply_settings()
            print("Einstellungen geladen.")
        else:
            print("Keine gespeicherten Einstellungen gefunden.")
    def save_settings(self):
        settings = {
            "integration_time": self.integration_time,
            "auto_scale_intensity": self.auto_scale_intensity,
            "fixed_intensity_max": self.fixed_intensity_max,
            "mirror": self.mirror,
            "hdr_num_frames": self.hdr_num_frames,
            "roi": self.roi,  # als Tupel oder Liste
            "low_res_mode": self.low_res_mode,
            "update_interval": self.update_interval,
            # Kameraeinstellungen:
            "camera": {
                "exposure": self.camera.exposure,
                "gain": self.camera.gain,
                "brightness": self.camera.brightness,
                "contrast": self.camera.contrast,
                "saturation": self.camera.saturation,
                "hdr_min_exposure": self.camera.hdr_min_exposure,
                "hdr_max_exposure": self.camera.hdr_max_exposure,
                "sensitivity_factors": self.camera.sensitivity_factors,
            },
            # Optional: Falls du Wellenlängen-Limits festlegst:
            "wavelength_min": getattr(self, "wavelength_min", 400),
            "wavelength_max": getattr(self, "wavelength_max", 700),
            "relative_spectrum_enabled": self.relative_spectrum_enabled,
            "normalize_relative_spectrum": self.normalize_relative_spectrum,
            # Referenzspektrum als Liste abspeichern:
            "reference_spectrum": self.reference_spectrum.tolist() if self.reference_spectrum is not None else None,
        }
        with open("settings.json", "w") as f:
            json.dump(settings, f, indent=4)
        print("Einstellungen gespeichert.")
    def update_timer_interval(self):
        if self.live_update:
            self.timer.setInterval(self.integration_time if not self.low_res_mode else self.update_interval)
            self.timer.start()

    def save_spectrum_to_csv(self):
        # Stelle sicher, dass ein Spektrum (self.spectrum_line) vorliegt:
        if not hasattr(self, "spectrum_line") or self.spectrum_line is None:
            print("Kein Spektrum vorhanden!")
            return

        # Falls Kalibrationsdaten vorhanden sind, berechne die Wellenlängen.
        if self.camera.calibration_data is not None:
            x_values = np.polyval(self.camera.calibration_data, np.arange(len(self.spectrum_line)))
        else:
            x_values = np.arange(len(self.spectrum_line))

        intensities = self.spectrum_line

        # Falls der Benutzer einen spezifischen Wellenlängenbereich eingestellt hat, filtere die Daten.
        if hasattr(self, 'wavelength_min') and hasattr(self, 'wavelength_max'):
            mask = (x_values >= self.wavelength_min) & (x_values <= self.wavelength_max)
            x_values = x_values[mask]
            intensities = intensities[mask]

        # Kombiniere die Daten in ein 2D-Array (zwei Spalten: Wellenlänge, Intensität)
        data = np.column_stack((x_values, intensities))

        # Erzeuge einen Default-Dateinamen mit Zeitstempel:
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"spectrum_{timestamp}.csv"

        # Öffne einen Save-Dialog:
        from PyQt5.QtWidgets import QFileDialog
        filename, _ = QFileDialog.getSaveFileName(self, "Spektrum speichern", default_filename, "CSV Files (*.csv)")
        if filename:
            np.savetxt(filename, data, delimiter=",", header="Wavelength,Intensity", comments="")
            print(f"Spektrum gespeichert unter {filename}")

    def save_spectrum_as_jpg(self):
        from PyQt5.QtWidgets import QFileDialog
        # Erzeuge einen Default-Dateinamen mit Zeitstempel
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"spectrum_{timestamp}.jpg"
        filename, _ = QFileDialog.getSaveFileName(self, "Spektrum als JPG speichern", default_filename,
                                                  "JPEG Files (*.jpg)")
        if filename:
            # Speichere die Figure als JPG:
            self.figure.savefig(filename, format="jpg")
            print(f"Spektrum-Bild gespeichert unter {filename}")

    def open_roi_dialog(self):
        dialog = ROIDialog(self)
        dialog.exec()

    def start_calibration(self):
        self.calibration_window = CalibrationDialog(self, self.spectrum_line)
        self.calibration_window.show()

    def capture_hdr(self):
        print("[INFO] HDR-Modus aktiviert. Live-Update wird deaktiviert.")
        self.live_update = False
        hdr_frame = self.camera.capture_hdr_frame(self.roi)
        if hdr_frame is not None:
            self.hdr_result = hdr_frame
            cv2.imshow("Test HDR-Bild", hdr_frame / np.max(hdr_frame))
            cv2.waitKey(0)
            cv2.destroyAllWindows()
            self.original_xlim = self.ax.get_xlim()
            self.original_ylim = self.ax.get_ylim()
            self.update_frame()
            self.canvas.draw()
            print("[INFO] HDR-Bild erfolgreich angezeigt!")
        else:
            print("[FEHLER] HDR-Bild konnte nicht erstellt werden.")

    def capture_spectrum(self):
        self.update_frame()  # Aktualisiere das Spektrum (dabei wird self.spectrum_line gesetzt)
        self.save_spectrum_to_csv()  # Speichere das aktuelle Spektrum in eine CSV-Datei

    def toggle_live_update(self):
        self.live_update = not self.live_update
        if self.live_update:
            self.timer.start(self.integration_time)
        else:
            self.timer.stop()

    def update_frame(self):
        if not self.live_update and self.hdr_result is None:
            return

        self.original_xlim = self.ax.get_xlim()
        self.original_ylim = self.ax.get_ylim()

        if self.hdr_result is not None:
            frame = self.hdr_result
            self.hdr_result = None
            x, y, w, h = 0, 0, frame.shape[1], frame.shape[0]
        else:
            frame = self.camera.capture_frame()
            # Hier ist self.roi in Originalkoordinaten (z. B. 1920×1080)
            x, y, w, h = self.roi

        if frame is not None:
            if self.mirror:
                frame = cv2.flip(frame, 1)
            if getattr(self, "dark_field_enabled", False) and hasattr(self, "dark_field"):
                frame = np.maximum(frame - self.dark_field, 0)
            if len(frame.shape) == 3:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Speichere die Originalgröße
            full_h, full_w = frame.shape[:2]

            # Falls low_res_mode aktiv ist, verkleinere das Bild und skaliere die ROI-Koordinaten:
            if self.low_res_mode:
                low_w, low_h = 640, 360
                frame = cv2.resize(frame, (low_w, low_h), interpolation=cv2.INTER_AREA)
                scale_x = low_w / full_w
                scale_y = low_h / full_h
                # Passe ROI an:
                x = int(x * scale_x)
                y = int(y * scale_y)
                w = int(w * scale_x)
                h = int(h * scale_y)

            h_img, w_img = frame.shape[:2]
            # Prüfe, ob ROI gültig ist:
            if self.hdr_result is None:
                if x + w > w_img or y + h > h_img or x < 0 or y < 0:
                    print("[WARNUNG] ROI außerhalb des gültigen Bereichs!")
                    return

            roi_frame = frame[y:y + h, x:x + w]
            if roi_frame.size == 0:
                print("[FEHLER] ROI ist leer! Überspringe Berechnung.")
                return
            if not self.auto_scale_intensity:
                self.ax.set_ylim(0, self.fixed_intensity_max)

            self.spectrum_line = np.sum(roi_frame, axis=0)

            # Falls Relativspektrum aktiviert und ein Referenzspektrum vorliegt:
            if self.relative_spectrum_enabled and self.reference_spectrum is not None:
                # Berechne den Quotienten – sichere Division (wo self.reference_spectrum != 0)
                quotient = np.divide(self.spectrum_line, self.reference_spectrum,
                                     out=np.zeros_like(self.spectrum_line), where=self.reference_spectrum != 0)
                # Optional: Normalisieren auf einen Maximalwert von 1
                if self.normalize_relative_spectrum:
                    max_val = np.max(quotient)
                    if max_val > 0:
                        quotient = quotient / max_val
                self.spectrum_line = quotient

            self.ax.clear()
            self.figure.set_facecolor("#1e1e1e")  # Setzt den Hintergrund der Figure
            self.ax.set_facecolor("#1e1e1e")  # Setzt den Hintergrund der Achsen
            self.ax.tick_params(axis='both', colors='white')  # Setzt die Tick-Farbe auf Weiß
            self.ax.xaxis.label.set_color('white')
            self.ax.yaxis.label.set_color('white')
            self.ax.title.set_color('white')
            self.ax.tick_params(axis='both', colors='white')
            if self.camera.calibration_data is not None:
                x_values = np.polyval(self.camera.calibration_data, np.arange(len(self.spectrum_line)))
                self.ax.plot(x_values, self.spectrum_line, color='red' if not self.live_update else 'white')
                self.ax.set_xlabel("Wellenlänge (nm)")
                if hasattr(self, 'wavelength_min') and hasattr(self, 'wavelength_max'):
                    self.ax.set_xlim(self.wavelength_min, self.wavelength_max)
            else:
                self.ax.plot(self.spectrum_line, color='red' if not self.live_update else 'white')
                self.ax.set_xlabel("Pixelposition")
            self.ax.tick_params(axis='both', colors='white')
            self.ax.set_ylabel("Intensität")
            if not self.auto_scale_intensity:
                self.ax.set_ylim(0, self.fixed_intensity_max)
            self.canvas.draw()

    def open_intensity_settings(self):
        dialog = IntensitySettingsDialog(self)
        dialog.exec()

    def open_camera_settings(self):
        dialog = CameraSettingsDialog(self)
        dialog.exec()

    def update_timer_interval(self):
        if self.live_update:
            self.timer.setInterval(self.integration_time)
            self.timer.start()

    def detect_peaks(self, spectrum_line):
        peaks, _ = find_peaks(spectrum_line, height=0.05 * np.max(spectrum_line))
        self.ax.plot(peaks, spectrum_line[peaks], "x", color='red')
        for i, peak in enumerate(peaks):
            self.ax.text(peak, spectrum_line[peak], f'{i + 1}', color='red', fontsize=8)
        print(f"[INFO] Erkannte Peaks: {peaks}")

    def update_roi(self, new_roi):
        self.roi = new_roi

    def display_image(self, image):
        if len(image.shape) == 3:
            height, width, _ = image.shape
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            height, width = image.shape
        bytes_per_line = width
        qimg = QImage(image.data, width, height, bytes_per_line, QImage.Format_Indexed8)
        pixmap = QPixmap.fromImage(qimg)
        self.image_label.setPixmap(pixmap)

    def on_mouse_press(self, event):
        if event.inaxes != self.ax:
            return
        if event.dblclick:
            self.ax.set_xlim(self.original_xlim)
            self.ax.set_ylim(self.original_ylim)
            self.canvas.draw()
        elif event.button == 1:
            self.zoom_start = (event.xdata, event.ydata)
            self.zoom_rect = None

    def on_mouse_move(self, event):
        if event.button == 1:
            if event.inaxes != self.ax or not hasattr(self, 'zoom_start') or self.zoom_start is None:
                return
            x0, y0 = self.zoom_start
            x1, y1 = event.xdata, event.ydata
            self.zoom_rect = [min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1)]
            if hasattr(self, 'zoom_patch') and self.zoom_patch is not None:
                try:
                    self.zoom_patch.remove()
                except Exception:
                    if self.zoom_patch in self.ax.patches:
                        self.ax.patches.remove(self.zoom_patch)
                self.zoom_patch = None
            width = self.zoom_rect[1] - self.zoom_rect[0]
            height = self.zoom_rect[3] - self.zoom_rect[2]
            self.zoom_patch = Rectangle((self.zoom_rect[0], self.zoom_rect[2]), width, height,
                                        edgecolor='yellow', facecolor='none', linestyle='--')
            self.ax.add_patch(self.zoom_patch)
        self.canvas.draw()

    def on_mouse_release(self, event):
        if not hasattr(self, 'zoom_start') or self.zoom_start is None or self.zoom_rect is None:
            return
        x_min, x_max, y_min, y_max = self.zoom_rect
        self.ax.set_xlim(x_min, x_max)
        self.ax.set_ylim(y_min, y_max)
        if hasattr(self, 'zoom_patch'):
            try:
                self.zoom_patch.remove()
            except Exception:
                if self.zoom_patch in self.ax.patches:
                    self.ax.patches.remove(self.zoom_patch)
            self.zoom_patch = None
        self.canvas.draw()
        self.zoom_start = None
        self.zoom_rect = None

    def closeEvent(self, event):
        self.camera.release()
        event.accept()
