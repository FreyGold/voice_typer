import sys
import os
import threading
import time
import json
import subprocess
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, 
                             QLabel, QProgressBar, QTextEdit, QPushButton, QLineEdit, QStackedWidget, QComboBox)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QTimer, QPoint
from recorder import Recorder
from transcriber import Transcriber
from typer_controller import TyperController

CONFIG_FILE = "config.json"

class WorkerSignals(QObject):
    status = pyqtSignal(str)
    preview = pyqtSignal(str)
    progress = pyqtSignal(int)
    model_loaded = pyqtSignal()
    trigger_press = pyqtSignal()
    trigger_release = pyqtSignal()

class VoiceTyperApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Voice Typer")
        self.setFixedSize(300, 240)
        
        # Standard window flags to allow native Move and "Always on Top" control
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
        
        self.signals = WorkerSignals()
        self.signals.status.connect(self.update_status)
        self.signals.preview.connect(self.update_preview)
        self.signals.progress.connect(self.update_progress)
        self.signals.model_loaded.connect(self.on_model_ready)
        self.signals.trigger_press.connect(self.start_recording_ui)
        self.signals.trigger_release.connect(self.stop_recording_ui)
        
        self.recorder = Recorder()
        self.transcriber = None
        self.config = self.load_config()
        
        self.typer = TyperController(
            on_press_callback=lambda: self.signals.trigger_press.emit(), 
            on_release_callback=lambda: self.signals.trigger_release.emit(),
            hotkey=self.config.get("hotkey", "KEY_RIGHTALT"),
            mode=self.config.get("trigger_mode", "hold")
        )
        
        self.is_recording = False
        self.is_loading_model = False
        
        self.setup_ui()
        self.typer.start_listening()

    def load_config(self):
        defaults = {"mode": None, "api_key": "", "hotkey": "KEY_RIGHTALT", "trigger_mode": "hold"}
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                try: return json.load(f)
                except: return defaults
        return defaults

    def save_config(self):
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f)

    def setup_ui(self):
        self.main_container = QWidget()
        self.setStyleSheet("""
            QMainWindow { background-color: #1a1b26; }
            QLabel { color: #a9b1d6; font-family: 'Segoe UI', sans-serif; }
            QPushButton {
                background-color: #24283b;
                color: #c0caf5;
                border: 1px solid #414868;
                border-radius: 4px;
                padding: 4px;
            }
            QPushButton:hover { background-color: #414868; }
            QLineEdit {
                background-color: #24283b;
                color: #c0caf5;
                border: 1px solid #414868;
                padding: 4px;
            }
            QComboBox {
                background-color: #24283b;
                color: #c0caf5;
                border: 1px solid #414868;
            }
            QProgressBar {
                border: 1px solid #414868;
                background-color: #24283b;
                border-radius: 2px;
                text-align: center;
            }
            QProgressBar::chunk { background-color: #7aa2f7; }
            QTextEdit {
                background-color: #24283b;
                color: #9ece6a;
                border: none;
                font-size: 11px;
            }
        """)
        
        self.setCentralWidget(self.main_container)
        main_layout = QVBoxLayout(self.main_container)
        main_layout.setContentsMargins(10, 10, 10, 10)

        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack)
        
        self.init_selection_screen()
        self.init_main_screen()
        
        if self.config["mode"]: self.start_app_with_mode(self.config["mode"], self.config["api_key"])
        else: self.stack.setCurrentIndex(0)

    def init_selection_screen(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(8)
        
        label = QLabel("SETUP")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-weight: bold; color: #7aa2f7;")
        layout.addWidget(label)
        
        s_layout = QHBoxLayout()
        self.combo_key = QComboBox()
        self.combo_key.addItems(["KEY_RIGHTALT", "KEY_LEFTCTRL", "KEY_RIGHTCTRL", "KEY_LEFTALT", "KEY_SPACE"])
        self.combo_key.setCurrentText(self.config["hotkey"])
        
        self.combo_mode = QComboBox()
        self.combo_mode.addItems(["hold", "toggle"])
        self.combo_mode.setCurrentText(self.config["trigger_mode"])
        
        s_layout.addWidget(self.combo_key)
        s_layout.addWidget(self.combo_mode)
        layout.addLayout(s_layout)
        
        btn_local = QPushButton("LOCAL MODE")
        btn_local.clicked.connect(lambda: self.start_app_with_mode("local"))
        layout.addWidget(btn_local)
        
        self.api_input = QLineEdit()
        self.api_input.setPlaceholderText("Groq API Key...")
        if self.config["api_key"]: self.api_input.setText(self.config["api_key"])
        layout.addWidget(self.api_input)
        
        btn_cloud = QPushButton("CLOUD MODE")
        btn_cloud.setStyleSheet("background-color: #3d59a1; font-weight: bold;")
        btn_cloud.clicked.connect(lambda: self.start_app_with_mode("cloud", self.api_input.text()))
        layout.addWidget(btn_cloud)
        
        self.stack.addWidget(page)

    def init_main_screen(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.label_status = QLabel("READY")
        self.label_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_status.setStyleSheet("font-size: 18px; font-weight: 900; color: #9ece6a; margin: 5px;")
        layout.addWidget(self.label_status)
        
        self.progressbar = QProgressBar()
        self.progressbar.setFixedHeight(4)
        self.progressbar.setTextVisible(False)
        layout.addWidget(self.progressbar)
        
        self.text_preview = QTextEdit()
        self.text_preview.setPlaceholderText("Transcription preview...")
        layout.addWidget(self.text_preview)
        
        footer = QHBoxLayout()
        self.label_hint = QLabel("")
        self.label_hint.setStyleSheet("font-size: 9px; color: #565f89;")
        footer.addWidget(self.label_hint)

        self.btn_play = QPushButton("▶ PLAY")
        self.btn_play.setFixedSize(60, 20)
        self.btn_play.setStyleSheet("font-size: 9px; font-weight: bold; color: #7aa2f7;")
        self.btn_play.clicked.connect(self.recorder.play_last)
        footer.addWidget(self.btn_play)
        
        btn_set = QPushButton("⚙")
        btn_set.setFixedSize(20, 20)
        btn_set.clicked.connect(self.reset_mode)
        footer.addWidget(btn_set)
        layout.addLayout(footer)
        
        self.stack.addWidget(page)

    def start_app_with_mode(self, mode, api_key=""):
        self.config.update({
            "mode": mode, "api_key": api_key,
            "hotkey": self.combo_key.currentText(),
            "trigger_mode": self.combo_mode.currentText()
        })
        self.save_config()
        self.typer.update_settings(self.config["hotkey"], self.config["trigger_mode"])
        self.stack.setCurrentIndex(1)
        self.update_status("LOADING")
        self.update_progress(-1)
        threading.Thread(target=self.load_transcriber, args=(mode, api_key), daemon=True).start()

    def reset_mode(self):
        self.config["mode"] = None
        self.stack.setCurrentIndex(0)

    def load_transcriber(self, mode, api_key):
        try:
            self.transcriber = Transcriber(mode=mode, api_key=api_key)
            self.signals.model_loaded.emit()
        except: self.signals.status.emit("ERROR")

    def on_model_ready(self):
        self.is_loading_model = False
        self.update_status("READY")
        self.label_status.setStyleSheet("font-size: 18px; font-weight: 900; color: #9ece6a; margin: 5px;")
        hint = "HOLD" if self.config["trigger_mode"] == "hold" else "TAP"
        self.label_hint.setText(f"{hint} {self.config['hotkey'].replace('KEY_', '')}")
        self.update_progress(0)

    def update_status(self, text): self.label_status.setText(text)
    def update_preview(self, text): self.text_preview.setText(text)
    def update_progress(self, value):
        if value == -1: self.progressbar.setRange(0, 0)
        else: self.progressbar.setRange(0, 100); self.progressbar.setValue(value)

    def start_recording_ui(self):
        if self.is_loading_model or not self.transcriber: return
        if not self.is_recording:
            self.is_recording = True
            self.recording_start_time = time.time()
            self.update_status("RECORDING")
            self.label_status.setStyleSheet("font-size: 18px; font-weight: 900; color: #f7768e; margin: 5px;")
            self.recorder.start()
            self.update_progress(-1)

    def stop_recording_ui(self):
        if self.is_recording:
            self.is_recording = False
            duration = time.time() - self.recording_start_time
            if duration < 0.7:
                self.recorder.stop()
                self.update_status("TOO SHORT")
                self.update_progress(0)
                return
            self.update_status("WORKING")
            self.label_status.setStyleSheet("font-size: 18px; font-weight: 900; color: #e0af68; margin: 5px;")
            self.update_progress(100)
            threading.Thread(target=self.process_audio, daemon=True).start()

    def process_audio(self):
        try:
            audio_file = self.recorder.stop()
            if audio_file and os.path.exists(audio_file):
                text = self.transcriber.transcribe(audio_file)
                if text.strip(): 
                    self.signals.preview.emit(text)
                    self.typer.type_text(text)
                else: self.signals.status.emit("SILENCE")
        except: self.signals.status.emit("ERROR")
        self.signals.status.emit("READY")
        self.label_status.setStyleSheet("font-size: 18px; font-weight: 900; color: #9ece6a; margin: 5px;")
        self.signals.progress.emit(0)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = VoiceTyperApp()
    window.show()
    sys.exit(app.exec())
