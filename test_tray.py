import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QSystemTrayIcon
app = QApplication(sys.argv)
window = QMainWindow()
tray = QSystemTrayIcon()
tray.show()
window.show()
print("Starting...")
app.exec()
print("Exited!")
