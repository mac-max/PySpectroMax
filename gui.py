import cv2
import numpy as np
import matplotlib.pyplot as plt
matplotlib.use("Qt5Agg")
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

class SpectrometerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.setStyleSheet("background-color: #1e1e1e; color: white;")
        self.camera = Camera()
        self.integration_time = 30  # Standard-Belichtungszeit in ms
        self.auto_scale_intensity = True
        self.fixed_intensity_max = 255
        self.mirror = True
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.live_update = True
        self.update_timer_interval()
        self.hdr_result = None
        self.hdr_num_frames = 5
        self.roi = (0, 470, 1920, 150)
        self.setWindowTitle("USB-Spektrometer GUI")
        self.setGeometry(100, 100, 900, 600)

    def initUI(self):
        main_layout = QHBoxLayout()
        self.bg_color = self.palette().color(self.backgroundRole()).name()

        # Linke Seite: Button-Bereich
        button_layout = QVBoxLayout()
        self.btn_capture = QPushButton("Spektrum aufnehmen")
        self.btn_capture.clicked.connect(self.capture_spectrum)
        button_layout.addWidget(self.btn_capture)
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
        button_layout.addStretch()
        main_layout.addLayout(button_layout, 1)

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
        self.update_frame()

    def toggle_live_update(self):
        self.live_update = not self.live_update
        if self.live_update:
            self.timer.start(self.integration_time)
        else:
            self.timer.stop()

    def update_frame(self):
        if not self.live_update and self.hdr_result is None:
            return

        self.figure.set_facecolor("#1e1e1e")  # Setzt den Hintergrund der Figure
        self.ax.set_facecolor("#1e1e1e")  # Setzt den Hintergrund der Achsen
        self.ax.tick_params(axis='both', colors='white')  # Setzt die Tick-Farbe auf Weiß
        self.ax.xaxis.label.set_color('white')
        self.ax.yaxis.label.set_color('white')
        self.ax.title.set_color('white')
        self.ax.tick_params(axis='both', colors='white')

        self.original_xlim = self.ax.get_xlim()
        self.original_ylim = self.ax.get_ylim()

        if self.hdr_result is not None:
            frame = self.hdr_result
            self.hdr_result = None
            x, y, w, h = 0, 0, frame.shape[1], frame.shape[0]
        else:
            frame = self.camera.capture_frame()
            x, y, w, h = self.roi

        if frame is not None:
            if self.mirror:
                frame = cv2.flip(frame, 1)
            if getattr(self, "dark_field_enabled", False) and hasattr(self, "dark_field"):
                frame = np.maximum(frame - self.dark_field, 0)
            if len(frame.shape) == 3:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            h_img, w_img = frame.shape[:2]
            if self.hdr_result is None:
                if x + w > w_img or y + h > h_img or x < 0 or y < 0:
                    print("[WARNUNG] ROI außerhalb des gültigen Bereichs!")
                    return
            roi_frame = frame[y:y + h, x:x + w]
            if roi_frame.size == 0:
                print("[FEHLER] ROI ist leer! Überspringe Berechnung.")
                return

            self.spectrum_line = np.sum(roi_frame, axis=0)

            self.ax.clear()
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
