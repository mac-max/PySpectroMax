import cv2
import csv
import concurrent.futures
import time

# Liste der zu testenden Kameraeigenschaften (Name, cv2-Konstante)
camera_properties = [
    ("Pos Msec", cv2.CAP_PROP_POS_MSEC),	
    ("Pos Frames", cv2.CAP_PROP_POS_FRAMES),	
    ("Pos Avi Ratio", cv2.CAP_PROP_POS_AVI_RATIO),	
    ("FourCC", cv2.CAP_PROP_FOURCC),	
    ("Frame Cnt", cv2.CAP_PROP_FRAME_COUNT),	
    ("Hue", cv2.CAP_PROP_HUE),    
    ("Convert RGB", cv2.CAP_PROP_CONVERT_RGB),	
    ("Zoom", cv2.CAP_PROP_ZOOM),	
    ("Focus", cv2.CAP_PROP_FOCUS),	
    ("Frame Width", cv2.CAP_PROP_FRAME_WIDTH),
    ("Frame Height", cv2.CAP_PROP_FRAME_HEIGHT),
    ("FPS", cv2.CAP_PROP_FPS),
    ("Exposure", cv2.CAP_PROP_EXPOSURE),
    ("Gain", cv2.CAP_PROP_GAIN),
    ("Brightness", cv2.CAP_PROP_BRIGHTNESS),
    ("Contrast", cv2.CAP_PROP_CONTRAST),
    ("Saturation", cv2.CAP_PROP_SATURATION),
    ("Format", cv2.CAP_PROP_FORMAT),
    # Hier lassen sich weitere Eigenschaften ergänzen
]

# Timeout-Exception definieren
class TimeoutException(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutException


def get_property_with_timeout(cap, prop, timeout=2):
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(lambda: cap.get(prop))
        try:
            value = future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            return None
    return value

def main():
    # Kamera öffnen (Index 0 – anpassen, falls nötig)
    cap = cv2.VideoCapture(0)
    # Warte etwas, bis die Kamera initialisiert ist
    time.sleep(2)

    results = []
    for name, prop in camera_properties:
        print(f"Abfrage: {name}")
        value = get_property_with_timeout(cap, prop, timeout=2)
        if value is None:
            print(f"  -> {name} konnte nicht abgefragt werden (Timeout)")
        else:
            print(f"  -> {name}: {value}")
        results.append((name, value))

    cap.release()

    # Ergebnisse in CSV-Datei schreiben
    output_filename = "camera_properties.csv"
    with open(output_filename, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Property", "Value"])
        for row in results:
            writer.writerow(row)
    print(f"Ergebnisse wurden in '{output_filename}' gespeichert.")

if __name__ == "__main__":
    main()
