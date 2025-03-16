import sys
from PyQt5.QtWidgets import QApplication
from gui import SpectrometerApp

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet("""
        QPushButton { 
            background-color: #7e7e7e; 
            color: white; 
            border: none; 
            padding: 5px;
        }
        QPushButton:hover { 
            background-color: #3e3e3e;
        }
        QWidget {
        background-color: #1e1e1e;
        color: white;
        }
    """)
    window = SpectrometerApp()
    window.show()
    sys.exit(app.exec_())
