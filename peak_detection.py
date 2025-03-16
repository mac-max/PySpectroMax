import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from scipy.signal import find_peaks

mpl.use("Qt5Agg")
mpl.rcParams['figure.facecolor'] = '#1e1e1e'
mpl.rcParams['axes.facecolor'] = '#1e1e1e'
mpl.rcParams['axes.edgecolor'] = 'white'
mpl.rcParams['axes.labelcolor'] = 'white'
mpl.rcParams['xtick.color'] = 'white'
mpl.rcParams['ytick.color'] = 'white'
mpl.rcParams['text.color'] = 'white'
mpl.rcParams['figure.autolayout'] = True

def detect_peaks(spectrum, height=None, distance=5):
    """Findet Peaks im gegebenen Spektrum."""
    peaks, _ = find_peaks(spectrum, height=height, distance=distance)
    return peaks

def plot_spectrum_with_peaks(spectrum):
    """Zeigt das Spektrum mit erkannten Peaks an."""
    peaks = detect_peaks(spectrum, height=0.05 * np.max(spectrum))  # Höhe = 5% vom Maximum

    plt.figure(figsize=(10, 6))
    plt.plot(spectrum, label="Spektrum")
    plt.plot(peaks, spectrum[peaks], "x", label="Peaks", markersize=8, color="red")
    plt.title("Spektrum mit erkannten Peaks")
    plt.xlabel("Pixel Position")
    plt.ylabel("Intensität")
    plt.legend()
    plt.show()

# Test-Daten (kann entfernt werden, wenn es in der GUI verwendet wird)
if __name__ == "__main__":
    x = np.linspace(0, 100, 1000)
    spectrum = np.sin(x) ** 2 + 0.2 * np.random.rand(1000)
    plot_spectrum_with_peaks(spectrum)
