import sys
from PyQt5.QtWidgets import QApplication
from gui import SpectrometerApp

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SpectrometerApp()
    window.show()
    sys.exit(app.exec_())
