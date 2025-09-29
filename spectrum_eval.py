import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import tkinter as tk
from tkinter import ttk
import os

# --- optional: SciPy für robusten Gauß-Fit ---
try:
    from scipy.optimize import curve_fit
    HAVE_SCIPY = True
except Exception:
    HAVE_SCIPY = False

# ----- Einstellungen -----
FOLDER = "./"   # Ordner mit CSVs
WINDOW_NM = 20          # Fit-Fenster ± nm um Klick
ZOOM_IN  = 1.2          # Mausrad rein
ZOOM_OUT = 1/ZOOM_IN    # Mausrad raus

# ----- CSV einsammeln -----
files = [f for f in os.listdir(FOLDER) if f.lower().endswith(".csv")]
if not files:
    raise FileNotFoundError(f"Keine CSV-Dateien in {FOLDER}")

def load_csv(path):
    df = pd.read_csv(path)
    # Spalten: Wavelength, Intensity
    return df["Wavelength"].to_numpy(), df["Intensity"].to_numpy()

# Start
current_file = os.path.join(FOLDER, files[0])
wavelength, intensity = load_csv(current_file)

# ----- Matplotlib-Plot -----
fig, ax = plt.subplots()
(line,) = ax.plot(wavelength, intensity, label=files[0])
(vline,) = ax.plot([], [], "--", color="gray", alpha=0.6)
(hline,) = ax.plot([], [], "--", color="gray", alpha=0.6)
(click_pt,) = ax.plot([], [], "ro", label="Klick")
(fit_line,) = ax.plot([], [], "g--", label="Fit")
(peak_marker,) = ax.plot([], [], "bx", markersize=10, label="Peak")
info_txt = ax.text(0.02, 0.95, "", transform=ax.transAxes, va="top")

ax.set_xlabel("Wellenlänge [nm]")
ax.set_ylabel("Intensität [a.u.]")
ax.set_title("Spektrum – Klick: Gauß-Fit, Mausrad: Zoom")
ax.legend(loc="best")

# ----- Gauß-Modell + Hilfsfunktionen -----
def gauss(x, A, x0, sigma, C):
    # A*exp(-(x-x0)^2/(2*sigma^2)) + C
    return A * np.exp(-0.5 * ((x - x0) / sigma) ** 2) + C

def fwhm_from_sigma(sigma):
    return 2.354820045 * sigma  # 2*sqrt(2*ln2)

def fit_gaussian(x, y):
    """Versucht Gauß-Fit; gibt (A,x0,sigma,C), y_fit zurück. Kann ValueError werfen."""
    # Initialschätzer
    i_max = np.argmax(y)
    x0_0 = float(x[i_max])
    A_0  = float(y.max() - y.min())
    C_0  = float(np.median(y[:max(3, len(y)//10)]))  # grober Untergrund
    sigma_0 = max((x.max() - x.min()) / 6.0, 1e-3)

    p0 = [A_0, x0_0, sigma_0, C_0]
    bounds = ([0, x.min(), 1e-6, -np.inf], [np.inf, x.max(), (x.max()-x.min()), np.inf])

    popt, _ = curve_fit(gauss, x, y, p0=p0, bounds=bounds, maxfev=2000)
    x_fit = np.linspace(x.min(), x.max(), 400)
    y_fit = gauss(x_fit, *popt)
    return popt, (x_fit, y_fit)

# ----- Klick-Event: Fit umsetzen -----
def on_click(event):
    global wavelength, intensity
    if event.inaxes is not ax or event.xdata is None:
        return

    x_click = float(event.xdata)
    # y aus Daten (nächstliegender Punkt)
    idx = np.abs(wavelength - x_click).argmin()
    y_click = float(intensity[idx])

    # Fadenkreuz
    xmin, xmax = ax.get_xlim()
    ymin, ymax = ax.get_ylim()
    vline.set_data([x_click, x_click], [ymin, ymax])
    hline.set_data([xmin, xmax], [y_click, y_click])
    click_pt.set_data([x_click], [y_click])

    # Fit-Fenster wählen
    mask = (wavelength >= x_click - WINDOW_NM) & (wavelength <= x_click + WINDOW_NM)
    if np.count_nonzero(mask) < 5:
        info_txt.set_text("⚠️ Zu wenige Punkte im Fenster")
        fit_line.set_data([], [])
        peak_marker.set_data([], [])
        fig.canvas.draw_idle()
        return

    x = wavelength[mask]
    y = intensity[mask]

    # Gauß-Fit (SciPy), Fallback Parabel
    used_gauss = False
    try:
        if HAVE_SCIPY:
            popt, (x_fit, y_fit) = fit_gaussian(x, y)
            A, x0, sigma, C = popt
            used_gauss = True
        else:
            raise RuntimeError("SciPy fehlt, Parabel-Fallback")
    except Exception:
        # Parabel-Fit als Fallback
        a, b, c = np.polyfit(x, y, 2)
        if np.isclose(a, 0.0, atol=1e-14):
            info_txt.set_text("⚠️ Fit instabil (a≈0)")
            fit_line.set_data([], [])
            peak_marker.set_data([], [])
            fig.canvas.draw_idle()
            return
        x_fit = np.linspace(x.min(), x.max(), 400)
        y_fit = a * x_fit**2 + b * x_fit + c
        x0 = -b / (2*a)
        A = y.max() - y.min()
        sigma = np.nan  # unbekannt im Parabel-Fallback
        C = np.min(y)

    # Plot-Update
    fit_line.set_data(x_fit, y_fit)
    y0 = np.interp(x0, x_fit, y_fit)
    peak_marker.set_data([x0], [y0])

    if used_gauss:
        fwhm = fwhm_from_sigma(sigma)
        info_txt.set_text(f"Peak: {x0:.3f} nm  |  FWHM: {fwhm:.3f} nm")
    else:
        info_txt.set_text(f"Peak (Parabel): {x0:.3f} nm")

    fig.canvas.draw_idle()

# ----- Mausrad-Zoom (x um Cursor, y autoscale) -----
def on_scroll(event):
    if event.inaxes is not ax or event.xdata is None:
        return

    xmin, xmax = ax.get_xlim()
    xr = xmax - xmin
    if xr <= 0:
        return

    factor = ZOOM_IN if event.button == "up" else ZOOM_OUT
    new_w = xr / factor
    rel = (event.xdata - xmin) / xr
    new_xmin = event.xdata - new_w * rel
    new_xmax = event.xdata + new_w * (1 - rel)

    ax.set_xlim(new_xmin, new_xmax)
    ax.relim()
    ax.autoscale_view(scaley=True)  # y an sichtbare Daten anpassen
    fig.canvas.draw_idle()

# ----- Dateiwechsel (Dropdown) -----
def on_file_select(event=None):
    global wavelength, intensity, current_file
    fname = combo.get()
    current_file = os.path.join(FOLDER, fname)
    wavelength, intensity = load_csv(current_file)
    line.set_data(wavelength, intensity)
    vline.set_data([], [])
    hline.set_data([], [])
    click_pt.set_data([], [])
    fit_line.set_data([], [])
    peak_marker.set_data([], [])
    info_txt.set_text("")
    ax.set_title(f"Spektrum – {fname}")
    ax.relim(); ax.autoscale_view()
    fig.canvas.draw_idle()

# ----- Tkinter-UI (nur für Datei-Auswahl) -----
root = tk.Tk()
root.title("Spektren auswählen")

combo = ttk.Combobox(root, values=files, state="readonly")
combo.set(files[0])
combo.pack(padx=10, pady=10)
combo.bind("<<ComboboxSelected>>", on_file_select)

ttk.Label(root, text="Klick: Gauß-Fit (Fallback Parabel)\nMausrad: Zoom um Cursor").pack(pady=6)

# Events
fig.canvas.mpl_connect("button_press_event", on_click)
fig.canvas.mpl_connect("scroll_event", on_scroll)

plt.ion()
plt.show()
root.mainloop()
