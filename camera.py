import cv2
import numpy as np

class Camera:
    def __init__(self):
        self.cap = cv2.VideoCapture(0)  # Kamera-ID 1 (falls nötig, anpassen)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        self.cap.set(cv2.CAP_PROP_FPS, 1)
        self.calibration_data = None
        self.load_calibration()
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.hdr_min_exposure  = -10
        self.hdr_max_exposure  = 1
        self.hdr_num_frames  = 3

        self.exposure_thr = 0.95

        # Standardmäßig auf False setzen, um Fehler zu vermeiden
        self.supports_high_bitdepth = False

        # Für Belichtungsstufen von -10 bis 1 (Index 0 entspricht -10, Index 11 entspricht 1)
        self.sensitivity_factors = [4.6, 3.2, 4.3, 15.3, 2.7, 4, 1.25, 2, 2, 1.1, 1.1, 1.1]

        # Prüfe, ob die Kamera höhere Bittiefe unterstützt
        self.supports_high_bitdepth = self.check_bitdepth_support()

        if self.supports_high_bitdepth:
            print("[INFO] Kamera unterstützt höhere Bittiefe. Umstellung auf 16-Bit-Modus...")
            self.cap.set(cv2.CAP_PROP_FORMAT, cv2.CV_16U)  # Falls unterstützt
        else:
            print("[WARNUNG] Kamera unterstützt nur 8 Bit!")

       # Standardwerte speichern
        self.exposure = self.cap.get(cv2.CAP_PROP_EXPOSURE)
        self.gain = self.cap.get(cv2.CAP_PROP_GAIN)
        self.brightness = self.cap.get(cv2.CAP_PROP_BRIGHTNESS)
        self.contrast = self.cap.get(cv2.CAP_PROP_CONTRAST)
        self.saturation = self.cap.get(cv2.CAP_PROP_SATURATION)
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)

    def apply_settings(self):
        """ Wendet die gespeicherten Kameraeinstellungen an """
        self.cap.set(cv2.CAP_PROP_EXPOSURE, self.exposure)
        self.cap.set(cv2.CAP_PROP_GAIN, self.gain)
        self.cap.set(cv2.CAP_PROP_BRIGHTNESS, self.brightness)
        self.cap.set(cv2.CAP_PROP_CONTRAST, self.contrast)
        self.cap.set(cv2.CAP_PROP_SATURATION, self.saturation)
        # self.cap.set(cv2.CAP_PROP_FPS, self.fps)

    def set_exposure(self, value):
        self.exposure = value
        self.apply_settings()

    def set_fps(self, fps_value):
        success = True #self.cap.set(cv2.CAP_PROP_FPS, fps_value)

    def set_auto_exposure(self):
        """ Automatische Anpassung der Belichtungszeit basierend auf Bildhelligkeit """
        print("[INFO] Auto-Belichtungszeit wird berechnet...")
        self.exposure = self.hdr_min_exposure

        for _ in range(self.hdr_max_exposure - self.hdr_min_exposure):  # Bis zu 25 Iterationen für die Anpassung
            frame = self.capture_frame()
            if frame is None:
                print("[WARNUNG] Kein Bild empfangen!")
                return

            ## neue routine für automatische belichtung

            exposure_thr_bin = np.int16(np.floor(self.exposure_thr*256))

            # Dynamische Belichtungsreihe basierend auf Histogramm
            if np.max([frame]) < self.exposure_thr*256:
                self.exposure = np.min([self.exposure+1,self.hdr_max_exposure])  # Belichtungszeit erhöhen

            self.apply_settings()

        print(f"[INFO] Neue Belichtungszeit: {self.exposure}")

    def capture_hdr_frame(self, roi=None):
        """
        Adaptive HDR-Aufnahme mit Mittelung mehrerer Bilder pro Belichtungsstufe,
        Noise-Floor-Unterdrückung, Sensitivitätsanpassung und flexibler Belichtungsbereich.

        :param roi: Optionaler ROI als (x, y, w, h)
        :param num_frames: Anzahl der Bilder, die pro Belichtungsstufe gemittelt werden sollen.
        :param exposure_range: Tupel (min_exposure, max_exposure) z. B. (-10, 1)
        :return: HDR-Bild (als float32) oder None, falls kein gültiges Bild aufgenommen wurde.
        """
        min_exposure = self.hdr_min_exposure  # z. B. -10
        max_exposure = self.hdr_max_exposure  # z. B. 1
        num_frames = self.hdr_num_frames  # z. B. 3
        exposures = list(range(min_exposure, max_exposure + 1))

        print("[INFO] Starte adaptive HDR-Aufnahme...")
        valid_exposures = 0
        hdr_image = None

        exposures = list(range(min_exposure, max_exposure + 1))

        for exposure in exposures:
            print(f"[INFO] Aufnahme mit Belichtungszeit: {exposure}")
            self.set_exposure(exposure)
            frames = []
            for _ in range(num_frames):
                frame = self.capture_frame()
                if frame is not None:
                    frames.append(frame.astype(np.float32))
            if not frames:
                print("[WARNUNG] Kein Bild empfangen!")
                continue

            avg_frame = np.mean(frames, axis=0)

            if roi is not None:
                x, y, w, h = roi
                avg_frame = avg_frame[y:y + h, x:x + w]

            noise_threshold = 10  # Beispielwert; anpassen je nach Kamera
            avg_frame = np.where(avg_frame < noise_threshold, 0, avg_frame)

            sensitivity = self.get_sensitivity_factor(exposure)
            avg_frame *= sensitivity

            valid_exposures += 1
            if hdr_image is None:
                hdr_image = avg_frame
            else:
                hdr_image += avg_frame

        if hdr_image is not None and valid_exposures > 0:
            print(f"[INFO] HDR-Aufnahme aus {valid_exposures} gültigen Belichtungsstufen erstellt!")
            return hdr_image

        print("[FEHLER] Alle Bilder waren fehlerhaft!")
        return None


    def get_sensitivity_factor(self, exposure):
        # Berechne den Index: Für exposure = -10 soll index 0 sein, für exposure = 1 index 11
        index = exposure + 10
        return self.sensitivity_factors[index]


    def set_gain(self, value):
        self.gain = value
        self.apply_settings()

    def set_brightness(self, value):
        self.brightness = value
        self.apply_settings()

    def set_contrast(self, value):
        self.contrast = value
        self.apply_settings()

    def set_saturation(self, value):
        self.saturation = value
        self.apply_settings()

    def check_bitdepth_support(self):
        """ Prüft, ob die Kamera eine höhere Bittiefe als 8 Bit unterstützt """
        test_frame = self.capture_frame()
        if test_frame is not None:
            max_value = np.max(test_frame)
            if max_value > 255:
                return True  # Kamera liefert Werte über 8 Bit
        return False  # Kamera ist auf 8 Bit limitiert

    def capture_frame(self):
        """ Nimmt ein Bild auf und gibt es als 16-Bit-Float zurück """
        ret, frame = self.cap.read()
        if not ret:
            return None

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)  # Konvertiere in Graustufen
        frame = frame.astype(np.float32) # / 255.0 * 65535  # Skalieren auf 16-Bit Float

        # print(f"[DEBUG] Live-Bild als float32 geladen (Min: {np.min(frame)}, Max: {np.max(frame)})")
        return frame

    def load_calibration(self):
        """ Lade die Kalibrationsdaten für die Wellenlängenachse """
        try:
            self.calibration_data = np.loadtxt("wavelength_calibration.csv", delimiter=",")
            print("[INFO] Kalibration geladen!")
        except Exception as e:
            print(f"[WARNUNG] Keine Kalibrationsdaten gefunden: {e}")

    def pixel_to_wavelength(self, pixel_positions):
        """ Wendet die Kalibration auf die Pixelpositionen an """
        if self.calibration_data is None:
            print("[WARNUNG] Keine Kalibration vorhanden, gebe Pixelpositionen zurück.")
            return pixel_positions

        return np.polyval(self.calibration_data, pixel_positions)

    def release(self):
        """ Gibt die Kamera frei """
        self.cap.release()
