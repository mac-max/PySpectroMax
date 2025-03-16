import numpy as np
import matplotlib.pyplot as plt
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QFileDialog, QTableWidget, QTableWidgetItem, QLineEdit
from PyQt6.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from scipy.signal import find_peaks

class CalibrationDialog(QDialog):
    def __init__(self, parent=None, spectrum=None):
        super().__init__(parent)
        self.setWindowTitle("Spektrometer Kalibration")
        self.setGeometry(400, 200, 1200, 400)
        self.parent = parent  # Zugriff auf das Hauptfenster

        # Falls spectrum nicht übergeben wurde, nutze das Spektrum aus dem Hauptfenster (z. B. spectrum_line)
        self.spectrum = spectrum if spectrum is not None else self.parent.spectrum_line
        self.initUI()

    def initUI(self):
        main_layout  = QHBoxLayout()
        self.bg_color = self.palette().color(self.backgroundRole()).name()

        # Erste Spalte: Tabelle mit Peaks + Button am unteren Rand
        table_layout = QVBoxLayout()
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["#", "Position", "Wellenlänge"])
        table_layout.addWidget(self.table)
        table_layout.addStretch()
        # Erstelle einen horizontalen Layoutbereich für die drei Buttons:
        button_layout = QVBoxLayout()
        self.btn_remove_last = QPushButton("Letzten Punkt entfernen")
        self.btn_remove_last.clicked.connect(self.remove_last_point)
        button_layout.addWidget(self.btn_remove_last)
        self.btn_calculate = QPushButton("Kalibration berechnen")
        self.btn_calculate.clicked.connect(self.calculate_calibration)
        button_layout.addWidget(self.btn_calculate)
        self.btn_save = QPushButton("Kalibration speichern")
        self.btn_save.clicked.connect(self.save_calibration)
        button_layout.addWidget(self.btn_save)
        table_layout.addLayout(button_layout)
        main_layout.addLayout(table_layout, 2)

        # Zweite Spalte: Hauptspektrum
        spectrum_layout = QHBoxLayout()
        self.spectrum_canvas = FigureCanvas(plt.figure(figsize=(5, 4)))
        self.ax = self.spectrum_canvas.figure.add_subplot(111)
        # Setze Hintergrund und Achsen in Weiß:
        self.ax.set_facecolor(self.bg_color)
        self.ax.tick_params(axis='both', colors='white')
        self.ax.xaxis.label.set_color('white')
        self.ax.yaxis.label.set_color('white')
        self.ax.title.set_color('white')
        # Verbinde Mausbewegungen und Klicks
        self.spectrum_canvas.mpl_connect("motion_notify_event", self.on_mouse_move)
        self.spectrum_canvas.mpl_connect("button_press_event", self.on_click)
        spectrum_layout.addWidget(self.spectrum_canvas)
        main_layout.addLayout(spectrum_layout, 4)

        # Dritte Spalte: Detailaufnahme des Spektrums
        detail_layout = QHBoxLayout()
        self.detail_canvas = FigureCanvas(plt.figure(figsize=(4, 4)))
        self.detail_ax = self.detail_canvas.figure.add_subplot(111)
        # Setze auch hier Hintergrund und Achsen in Weiß:
        self.detail_ax.set_facecolor(self.bg_color)
        self.detail_ax.tick_params(axis='both', colors='white')
        self.detail_ax.xaxis.label.set_color('white')
        self.detail_ax.yaxis.label.set_color('white')
        self.detail_ax.title.set_color('white')
        self.detail_ax.get_yaxis().set_visible(False)
        # Optional: Feste Größe (kann auch dynamisch angepasst werden)
        # self.detail_canvas.setFixedSize(50, 50)
        detail_layout.addWidget(self.detail_canvas)
        main_layout.addLayout(detail_layout, 4)

        self.spectrum_canvas.figure.set_facecolor(self.bg_color)
        self.detail_canvas.figure.set_facecolor(self.bg_color)
        self.spectrum_canvas.figure.set_facecolor(self.bg_color)
        self.detail_canvas.figure.set_facecolor(self.bg_color)
        self.setLayout(main_layout)
        self.plot_spectrum()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Hole die aktuelle Höhe des Spektrum-Canvases
        spectrum_height = self.spectrum_canvas.height()
        # Setze die Höhe des Detail-Canvases gleich
        self.detail_canvas.setFixedHeight(spectrum_height)
        # Optional: Passe auch die Figure-Größe des Detail-Canvas an (in Inches)
        dpi = self.detail_canvas.figure.dpi
        current_size = self.detail_canvas.figure.get_size_inches()
        new_height_inches = spectrum_height / dpi
        self.detail_canvas.figure.set_size_inches(current_size[0], new_height_inches, forward=True)
        self.detail_canvas.draw()


    def update_detail_plot(self):
        """ Aktualisiert den Detailplot basierend auf der aktuellen Mausposition, falls vorhanden. """
        # Hier könntest du den aktuell fokussierten Bereich erneut zeichnen.
        pass

    def on_mouse_move(self, event):
        if event.xdata is None or event.ydata is None:
            return
        x_center = int(event.xdata)
        half_width = 25  # Standardwert, kann auch dynamisch sein
        start = max(0, x_center - half_width)
        end = min(len(self.spectrum), x_center + half_width)
        detail_data = self.spectrum[start:end]
        self.detail_ax.clear()
        # Passe hier den x-Bereich an die neue Größe des Detail-Canvas an:
        self.detail_ax.plot(range(start, end), detail_data, color='white')
        self.detail_ax.set_title("Detail")
        self.detail_canvas.draw()

    def add_peak_to_table(self, peak_index):
        row = self.table.rowCount()
        self.table.insertRow(row)
        # Spalte 0: Peak Nummer
        self.table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
        # Spalte 1: QLineEdit für die Pixel-Position (bearbeitbar)
        peak_line_edit = QLineEdit(str(peak_index))
        # Bei Abschluss der Bearbeitung wird der Plot neu gezeichnet.
        peak_line_edit.editingFinished.connect(lambda r=row: self.on_peak_value_changed(r))
        self.table.setCellWidget(row, 1, peak_line_edit)
        # Spalte 2: QLineEdit für den wahren Wert
        self.table.setCellWidget(row, 2, QLineEdit())
        self.plot_peaks()

    def on_peak_value_changed(self, row):
        """ Wird aufgerufen, wenn der Benutzer den Wert in der Pixel-Position bearbeitet. """
        widget = self.table.cellWidget(row, 1)
        if widget:
            try:
                new_value = int(widget.text())
                # Hier könntest du weitere Validierungen einbauen
                print(f"Peak in Zeile {row} wurde auf {new_value} geändert.")
            except ValueError:
                pass
        self.plot_peaks()

    def keyPressEvent(self, event):
        key = event.key()
        if key in (Qt.Key.Key_Up, Qt.Key.Key_Right, Qt.Key.Key_Down, Qt.Key.Key_Left):
            current_row = self.table.currentRow()
            if current_row >= 0:
                widget = self.table.cellWidget(current_row, 1)
                if widget:
                    try:
                        value = int(widget.text())
                    except ValueError:
                        value = 0
                    if key in (Qt.Key.Key_Up, Qt.Key.Key_Right):
                        value += 1
                    elif key in (Qt.Key.Key_Down, Qt.Key.Key_Left):
                        value -= 1
                    widget.setText(str(value))
                    self.on_peak_value_changed(current_row)
                    event.accept()
                    return
        super().keyPressEvent(event)

    def on_click(self, event):
        if event.inaxes is None:
            return
        clicked_pixel = int(event.xdata)
        peaks, _ = find_peaks(self.spectrum, height=0.05 * np.max(self.spectrum))
        if peaks.size > 0:
            distances = np.abs(peaks - clicked_pixel)
            nearest_peak = peaks[np.argmin(distances)]
        else:
            nearest_peak = clicked_pixel

        # Markiere den gefundenen Peak im Plot
        self.ax.plot(nearest_peak, self.spectrum[nearest_peak], 'x', color='red')
        self.ax.text(nearest_peak, self.spectrum[nearest_peak], str(nearest_peak), color='red', fontsize=8)
        self.spectrum_canvas.draw()

        # Füge den Peak der Tabelle hinzu
        self.add_peak_to_table(nearest_peak)

    def on_mouse_move(self, event):
        if event.xdata is None or event.ydata is None:
            return
        x_center = int(event.xdata)
        half_width = 25  # 50 Pixel Gesamtbreite
        start = max(0, x_center - half_width)
        end = min(len(self.spectrum), x_center + half_width)
        detail_data = self.spectrum[start:end]
        self.detail_ax.clear()
        self.detail_ax.plot(range(start, end), detail_data, color='white')
        # Füge eine vertikale, rote Linie in der Mitte des Detailplots ein
        center_value = (start + end) / 2
        self.detail_ax.axvline(x=center_value, color='red', linestyle='--', linewidth=1)
        self.detail_ax.set_title("Detail", color='white')
        self.detail_ax.tick_params(axis='both', colors='white')
        self.detail_canvas.draw()

    def add_peak_to_table(self, peak_index):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
        self.table.setItem(row, 1, QTableWidgetItem(str(peak_index)))
        self.table.setCellWidget(row, 2, QLineEdit())  # Eingabe für den wahren Wert
        self.plot_peaks()

    def plot_spectrum(self):
        self.ax.clear()
        self.ax.plot(self.spectrum, color='white')
        self.ax.set_title("Kalibration - Hauptspektrum", color='white')
        self.ax.set_xlabel("Pixelposition", color='white')
        self.ax.set_ylabel("Intensität", color='white')
        self.ax.tick_params(axis='both', colors='white')
        self.spectrum_canvas.draw()

    def plot_peaks(self):
        """ Zeichnet das Spektrum und markiert alle Peaks aus der Tabelle neu. """
        peaks = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 1)
            if item is not None:
                try:
                    peak_val = float(item.text())
                    peaks.append(int(peak_val))
                except ValueError:
                    continue
        self.ax.clear()
        self.ax.plot(self.spectrum, color='white')
        if peaks:
            self.ax.plot(peaks, self.spectrum[peaks], "x", color='red')
            for i, peak in enumerate(peaks):
                self.ax.text(peak, self.spectrum[peak], f'{i + 1}', color='red', fontsize=8)
        self.ax.set_title("Kalibriertes Spektrum", color='white')
        self.ax.set_xlabel("Pixelposition", color='white')
        self.ax.set_ylabel("Intensität", color='white')
        self.ax.tick_params(axis='both', colors='white')
        self.spectrum_canvas.draw()

    def remove_last_point(self):
        """ Entfernt den zuletzt eingetragenen Punkt aus der Tabelle und aktualisiert den Plot. """
        row_count = self.table.rowCount()
        if row_count > 0:
            self.table.removeRow(row_count - 1)
            self.plot_peaks()

    def calculate_calibration(self):
        """ Berechnet eine neue Kalibration basierend auf den derzeit in der Tabelle eingetragenen Punkten
            und wendet sie direkt auf das angezeigte Spektrum an. """
        peak_positions = []
        known_wavelengths = []
        for row in range(self.table.rowCount()):
            widget = self.table.cellWidget(row, 1)
            if widget:
                text = widget.text().replace(',', '.')
            else:
                item = self.table.item(row, 1)
                text = item.text().replace(',', '.') if item else ""
            try:
                pixel_pos = float(text)
                # Für den wahren Wert:
                true_widget = self.table.cellWidget(row, 2)
                if true_widget:
                    true_text = true_widget.text().replace(',', '.')
                else:
                    true_item = self.table.item(row, 2)
                    true_text = true_item.text().replace(',', '.') if true_item else ""
                true_val = float(true_text)
                peak_positions.append(pixel_pos)
                known_wavelengths.append(true_val)
            except ValueError:
                continue
        if len(peak_positions) < 3:
            print("[WARNUNG] Mindestens 3 Peaks erforderlich für Kalibration!")
            return
        self.pixel_to_wavelength = np.polyfit(peak_positions, known_wavelengths, deg=2)
        print(f"[INFO] Kalibration berechnet: {self.pixel_to_wavelength}")
        self.calibration_support = {
            'pixels': np.array(peak_positions),
            'wavelengths': np.array(known_wavelengths)
        }
        self.plot_calibrated_spectrum(self.pixel_to_wavelength, peak_positions)

    def save_calibration(self):
        """ Speichert die aktuell berechnete Kalibration in eine Datei. """
        if hasattr(self, 'pixel_to_wavelength'):
            np.savetxt("wavelength_calibration.csv", self.pixel_to_wavelength, delimiter=",")
            print("[INFO] Kalibrationsdaten gespeichert!")
        else:
            print("[WARNUNG] Es liegt keine Kalibration vor.")

    def plot_calibrated_spectrum(self, pixel_to_wavelength, peak_positions):
        self.ax.clear()
        self.ax.set_facecolor(self.bg_color)
        # Berechne die kalibrierten x-Werte (Wellenlängen) für das gesamte Spektrum:
        x_values = np.polyval(pixel_to_wavelength, np.arange(len(self.spectrum)))
        self.ax.plot(x_values, self.spectrum, color='white')
        # Markiere die in der Tabelle enthaltenen Peaks:
        for i, pos in enumerate(peak_positions):
            pos_int = int(round(pos))
            # Berechne die kalibrierte Wellenlänge für den Peak
            peak_wavelength = np.polyval(pixel_to_wavelength, pos_int)
            self.ax.plot(peak_wavelength, self.spectrum[pos_int], 'x', color='red')
            self.ax.text(peak_wavelength, self.spectrum[pos_int], f'{i + 1}\n{peak_wavelength:.2f} nm',
                         color='red', fontsize=8)
        # Falls Stützstellen vorhanden sind, zeichne diese in Grün:
        if hasattr(self, 'calibration_support'):
            support_pixels = self.calibration_support['pixels']
            support_values = [self.spectrum[int(round(p))] for p in support_pixels]
            # Berechne für jede Stützstelle die kalibrierte Wellenlänge
            support_wavelengths = np.polyval(pixel_to_wavelength, support_pixels.astype(int))
            self.ax.plot(support_wavelengths, support_values, 'o', color='green', markersize=10, label='Stützstellen')
            self.ax.legend()

        self.ax.set_xlabel("Wellenlänge (nm)", color='white')
        self.ax.set_ylabel("Intensität", color='white')
        self.ax.set_title("Kalibriertes Spektrum", color='white')
        self.ax.tick_params(axis='both', colors='white')

        # Optional: Sekundäre Achse mit Pixelpositionen
        ax2 = self.ax.secondary_xaxis('top')
        ax2.set_xlabel("Pixelposition", color='white')
        ax2.tick_params(axis='x', colors='white')

        self.spectrum_canvas.draw()

