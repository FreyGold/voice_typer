import sys
import os
import threading
import time
import json
import subprocess
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, 
                             QLabel, QProgressBar, QTextEdit, QPushButton, QLineEdit, QStackedWidget, QComboBox, QSystemTrayIcon, QMenu, QCheckBox)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QTimer, QPoint
from PyQt6.QtGui import QIcon, QAction
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
        self.setFixedSize(300, 310) # Slightly taller to fit Save button
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
        
        # Try to load custom icon
        self.icon_path = os.path.expanduser("~/.local/share/icons/voice-typer.svg")
        if os.path.exists(self.icon_path):
            self.setWindowIcon(QIcon(self.icon_path))
        
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
        self.setup_tray()
        self.typer.start_listening()

    def load_config(self):
        defaults = {"mode": None, "api_key": "", "hotkey": "KEY_RIGHTALT", "trigger_mode": "hold", "language": "auto", "refine": True}
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                try: 
                    d = json.load(f)
                    defaults.update(d)
                except: pass
        return defaults

    def save_config(self):
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f)

    def setup_ui(self):
        self.main_container = QWidget()
        self.setStyleSheet("""
            QMainWindow { background-color: #1a1b26; }
            QLabel { color: #a9b1d6; font-family: 'Segoe UI', sans-serif; font-size: 11px; }
            QPushButton { background-color: #24283b; color: #c0caf5; border: 1px solid #414868; border-radius: 4px; padding: 5px; }
            QPushButton:hover { background-color: #414868; }
            QLineEdit, QComboBox, QTextEdit { background-color: #24283b; color: #c0caf5; border: 1px solid #414868; padding: 4px; }
            QComboBox QAbstractItemView { background-color: #1a1b26; color: #c0caf5; selection-background-color: #3d59a1; }
            QProgressBar { border: 1px solid #414868; background-color: #24283b; border-radius: 2px; text-align: center; }
            QProgressBar::chunk { background-color: #7aa2f7; }
            QCheckBox { color: #a9b1d6; font-size: 10px; }
        """)
        self.setCentralWidget(self.main_container)
        layout = QVBoxLayout(self.main_container)
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)
        self.init_selection_screen(); self.init_main_screen()
        if self.config["mode"]: self.start_app_with_mode(self.config["mode"], self.config["api_key"])
        else: self.stack.setCurrentIndex(0)

    def init_selection_screen(self):
        page = QWidget(); layout = QVBoxLayout(page)
        title = QLabel("SETTINGS"); title.setAlignment(Qt.AlignmentFlag.AlignCenter); title.setStyleSheet("font-weight:bold; color:#7aa2f7; font-size:14px"); layout.addWidget(title)
        
        row1 = QHBoxLayout(); self.combo_key = QComboBox(); self.combo_key.addItems(["KEY_RIGHTALT", "KEY_LEFTCTRL", "KEY_RIGHTCTRL", "KEY_SPACE", "KEY_CAPSLOCK", "KEY_F10"])
        self.combo_key.setCurrentText(self.config["hotkey"]); self.combo_mode = QComboBox(); self.combo_mode.addItems(["hold", "toggle"])
        self.combo_mode.setCurrentText(self.config["trigger_mode"]); row1.addWidget(self.combo_key); row1.addWidget(self.combo_mode); layout.addLayout(row1)
        
        row2 = QHBoxLayout(); self.combo_lang = QComboBox(); self.combo_lang.addItems(["auto", "en", "ar", "fr", "es"])
        self.combo_lang.setCurrentText(self.config["language"]); row2.addWidget(QLabel("Language:")); row2.addWidget(self.combo_lang); layout.addLayout(row2)
        
        self.check_refine = QCheckBox("Smart Punctuation (Cloud only)"); self.check_refine.setChecked(self.config["refine"]); layout.addWidget(self.check_refine)
        
        layout.addWidget(QLabel("--- API KEY (Only for Cloud Mode) ---"))
        self.api_input = QLineEdit(); self.api_input.setPlaceholderText("Groq API Key..."); self.api_input.setText(self.config["api_key"]); layout.addWidget(self.api_input)

        btn_apply = QPushButton("APPLY & SAVE"); btn_apply.setStyleSheet("background-color: #3d59a1; font-weight: bold; margin-top: 5px;"); btn_apply.clicked.connect(self.apply_changes); layout.addWidget(btn_apply)

        layout.addWidget(QLabel("--- Switch Modes ---"))
        mode_layout = QHBoxLayout()
        btn_local = QPushButton("USE LOCAL"); btn_local.clicked.connect(lambda: self.start_app_with_mode("local")); mode_layout.addWidget(btn_local)
        btn_cloud = QPushButton("USE CLOUD"); btn_cloud.clicked.connect(lambda: self.start_app_with_mode("cloud", self.api_input.text())); mode_layout.addWidget(btn_cloud)
        layout.addLayout(mode_layout)
        
        self.stack.addWidget(page)

    def init_main_screen(self):
        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(0, 0, 0, 0)
        self.label_status = QLabel("READY"); self.label_status.setAlignment(Qt.AlignmentFlag.AlignCenter); self.label_status.setStyleSheet("font-size:18px; font-weight:900; color:#9ece6a; margin:5px"); layout.addWidget(self.label_status)
        self.progressbar = QProgressBar(); self.progressbar.setFixedHeight(4); self.progressbar.setTextVisible(False); layout.addWidget(self.progressbar)
        self.text_preview = QTextEdit(); self.text_preview.setReadOnly(True); self.text_preview.setStyleSheet("color:#9ece6a; font-size:10px"); layout.addWidget(self.text_preview)
        footer = QHBoxLayout(); self.label_hint = QLabel(""); self.label_hint.setStyleSheet("font-size:9px; color:#565f89"); footer.addWidget(self.label_hint)
        btn_play = QPushButton("▶ PLAY"); btn_play.setFixedSize(50, 20); btn_play.clicked.connect(self.recorder.play_last); footer.addWidget(btn_play)
        btn_set = QPushButton("⚙"); btn_set.setFixedSize(25, 20); btn_set.clicked.connect(self.reset_mode); footer.addWidget(btn_set)
        layout.addLayout(footer); self.stack.addWidget(page)

    def setup_tray(self):
        self.tray = QSystemTrayIcon(self)
        if os.path.exists(self.icon_path):
            self.tray.setIcon(QIcon(self.icon_path))
        else:
            from PyQt6.QtWidgets import QStyle
            self.tray.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DriveHDIcon))
        
        menu = QMenu(); show_act = QAction("Show", self); show_act.triggered.connect(self.show); quit_act = QAction("Quit", self); quit_act.triggered.connect(QApplication.instance().quit)
        menu.addActions([show_act, quit_act]); self.tray.setContextMenu(menu); self.tray.show()

    def apply_changes(self):
        # Update config from UI
        self.config.update({
            "api_key": self.api_input.text(),
            "hotkey": self.combo_key.currentText(),
            "trigger_mode": self.combo_mode.currentText(),
            "language": self.combo_lang.currentText(),
            "refine": self.check_refine.isChecked()
        })
        self.save_config()
        self.typer.update_settings(self.config["hotkey"], self.config["trigger_mode"])
        
        # If we already have a transcriber, just go back. Otherwise, it must be first run.
        if self.transcriber:
            self.on_model_ready() # Reset hint text
            self.stack.setCurrentIndex(1)
        else:
            # First run behavior: Default to Local if nothing selected yet
            mode = self.config.get("mode", "local")
            self.start_app_with_mode(mode, self.config["api_key"])

    def start_app_with_mode(self, mode, api_key=""):
        self.config.update({"mode": mode, "api_key": api_key})
        self.config.update({
            "hotkey": self.combo_key.currentText(),
            "trigger_mode": self.combo_mode.currentText(),
            "language": self.combo_lang.currentText(),
            "refine": self.check_refine.isChecked()
        })
        self.save_config()
        self.typer.update_settings(self.config["hotkey"], self.config["trigger_mode"])
        self.stack.setCurrentIndex(1); self.update_status("LOADING"); self.update_progress(-1)
        threading.Thread(target=self.load_transcriber, args=(mode, api_key), daemon=True).start()

    def reset_mode(self): self.stack.setCurrentIndex(0)
    def load_transcriber(self, mode, api_key):
        try: self.transcriber = Transcriber(mode=mode, api_key=api_key); self.signals.model_loaded.emit()
        except: self.signals.status.emit("ERROR")
    def on_model_ready(self):
        self.is_loading_model = False; self.update_status("READY")
        self.label_hint.setText(f"{self.config['trigger_mode'].upper()} {self.config['hotkey'].replace('KEY_', '')} ({self.config['language'].upper()})")
        self.update_progress(0)
    def update_status(self, text): 
        self.label_status.setText(text)
    def update_preview(self, text): self.text_preview.setText(text)
    def update_progress(self, v):
        if v == -1: self.progressbar.setRange(0, 0)
        else: self.progressbar.setRange(0, 100); self.progressbar.setValue(v)

    def start_recording_ui(self):
        if self.is_loading_model or not self.transcriber: return
        if not self.is_recording:
            self.is_recording = True; self.recording_start_time = time.time()
            self.update_status("RECORDING"); self.recorder.start(); self.update_progress(-1)

    def stop_recording_ui(self):
        if self.is_recording:
            # We don't set self.is_recording = False here immediately to prevent re-triggering 
            # while the recorder is still closing its stream.
            duration = time.time() - self.recording_start_time
            if duration < 0.6: 
                self.recorder.stop()
                self.is_recording = False
                self.update_status("READY"); self.update_progress(0)
                return
            
            self.update_status("WORKING"); self.update_progress(100)
            threading.Thread(target=self.process_audio, daemon=True).start()

    def process_audio(self):
        try:
            audio_file = self.recorder.stop()
            # Reset recording flag AFTER the stream is definitely closed
            self.is_recording = False
            
            if audio_file and os.path.exists(audio_file):
                text = self.transcriber.transcribe(audio_file, language=self.config["language"], refine=self.config["refine"])
                if text.strip(): self.signals.preview.emit(text); self.typer.type_text(text)
        except Exception as e:
            print(f"Process Audio Error: {e}")
            self.is_recording = False
            self.signals.status.emit("ERROR")
        
        self.signals.status.emit("READY"); self.signals.progress.emit(0)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Voice Typer")
    app.setDesktopFileName("voice-typer") # Matches voice-typer.desktop
    
    # Set global app icon
    icon_path = os.path.expanduser("~/.local/share/icons/voice-typer.svg")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
        
    window = VoiceTyperApp()
    window.show()
    sys.exit(app.exec())
